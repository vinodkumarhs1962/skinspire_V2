# app/api/routes/billing.py

import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from sqlalchemy.orm import Session

from app.services.database_service import get_db_session, get_entity_dict
from app.services.billing_service import (
    create_invoice as create_invoice_service,
    get_invoice_by_id as get_invoice_service,
    search_invoices as search_invoices_service,
    record_payment as record_payment_service,
    void_invoice as void_invoice_service,
    issue_refund as issue_refund_service,
    get_batch_selection_for_invoice
)
from app.models.transaction import User, InvoiceHeader
from app.models.master import Service, Package, Medicine, Hospital, Patient
from app.security.authorization.decorators import token_required

# Configure logger
logger = logging.getLogger(__name__)

# Create API blueprint
billing_api_bp = Blueprint('billing_api', __name__, url_prefix='/api')

# Original endpoints with token_required

@billing_api_bp.route('/invoice/create', methods=['POST'])
@token_required
def create_invoice_api(user_id, session):
    """API endpoint to create invoices with support for multiple invoice generation"""
    try:
        # Get request data
        data = request.json if request.is_json else request.form
        
        # Extract required parameters
        hospital_id = uuid.UUID(data.get('hospital_id'))
        
        # Get current user and verify hospital access
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if str(user.hospital_id) != str(hospital_id):
            return jsonify({'error': 'Access denied to specified hospital'}), 403
        
        branch_id = uuid.UUID(data.get('branch_id')) if data.get('branch_id') else None
        patient_id = uuid.UUID(data.get('patient_id'))
        invoice_date_str = data.get('invoice_date')
        invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        notes = data.get('notes')
        
        # Process line items
        line_items = []
        for item_data in data.get('line_items', []):
            line_item = {
                'item_type': item_data.get('item_type'),
                'item_id': uuid.UUID(item_data.get('item_id')),
                'item_name': item_data.get('item_name'),
                'quantity': Decimal(str(item_data.get('quantity', 1))),
                'unit_price': Decimal(str(item_data.get('unit_price', 0))),
                'discount_percent': Decimal(str(item_data.get('discount_percent', 0))),
                'included_in_consultation': item_data.get('included_in_consultation', False)
            }
            
            # Add batch and expiry for medicines
            if item_data.get('item_type') in ['Medicine', 'Prescription'] and item_data.get('batch'):
                line_item['batch'] = item_data.get('batch')
                if item_data.get('expiry_date'):
                    line_item['expiry_date'] = item_data.get('expiry_date')
            
            line_items.append(line_item)
        
        # Create invoices based on business rules
        result = create_invoice_service(
            hospital_id=hospital_id,
            branch_id=branch_id,
            patient_id=patient_id,
            invoice_date=invoice_date,
            line_items=line_items,
            notes=notes,
            current_user_id=user_id,
            session=session
        )
        
        # Return appropriate response based on number of invoices created
        invoice_count = result.get('count', 0)
        if invoice_count == 1:
            # Single invoice
            invoice = result['invoices'][0]
            return jsonify({
                'success': True,
                'invoice_id': invoice['invoice_id'],
                'invoice_number': invoice['invoice_number'],
                'message': 'Invoice created successfully'
            }), 201
        elif invoice_count > 1:
            # Multiple invoices
            invoice_ids = [inv['invoice_id'] for inv in result['invoices']]
            invoice_numbers = [inv['invoice_number'] for inv in result['invoices']]
            return jsonify({
                'success': True,
                'invoice_count': invoice_count,
                'invoice_ids': invoice_ids,
                'invoice_numbers': invoice_numbers,
                'message': f'{invoice_count} invoices created successfully based on item types'
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'No invoices created. Please check your line items.'
            }), 400
           
    except Exception as e:
        current_app.logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@billing_api_bp.route('/patient/search', methods=['GET'])
@token_required
def api_patient_search(user_id, session):
    """API endpoint to search for patients"""
    try:
        # Get query parameter
        query = request.args.get('q', '')
        if len(query) < 1:
            return jsonify([])
        
        # Get user's hospital ID
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        hospital_id = user.hospital_id
        
        # Search patients by name, MRN, or phone
        patients = session.query(Patient).filter(
            Patient.hospital_id == hospital_id,
            Patient.is_active == True
        ).filter(
            # Search by full name (case insensitive)
            Patient.full_name.ilike(f'%{query}%') |
            # Search by MRN
            Patient.mrn.ilike(f'%{query}%') |
            # Search by phone number
            Patient.contact_info['phone'].astext.ilike(f'%{query}%')
        ).limit(10).all()
        
        # Format results
        results = []
        for patient in patients:
            # Create a safe subset of patient data
            patient_dict = {
                'id': str(patient.patient_id),
                'name': patient.full_name,
                'mrn': patient.mrn,
                'contact': patient.contact_info.get('phone') if patient.contact_info else None
            }
            results.append(patient_dict)
        
        return jsonify(results)
       
    except Exception as e:
        current_app.logger.error(f"Error searching patients: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error searching patients'}), 500

@billing_api_bp.route('/item/search', methods=['GET'])
@token_required
def api_item_search(user_id, session):
    """API endpoint to search for billable items (services, packages, medicines)"""
    try:
        # Get query parameters
        query = request.args.get('q', '')
        item_type = request.args.get('type', '')
        
        if len(query) < 2 or not item_type:
            return jsonify([])
        
        # Get user's hospital ID
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        hospital_id = user.hospital_id
        
        # Search based on item type
        results = []
        
        if item_type == 'Package':
            packages = session.query(Package).filter(
                Package.hospital_id == hospital_id,
                Package.is_active == True,
                Package.package_name.ilike(f'%{query}%')
            ).limit(10).all()
            
            for package in packages:
                results.append({
                    'id': str(package.package_id),
                    'name': package.package_name,
                    'type': 'Package',
                    'price': float(package.price) if package.price else 0.0,
                    'gst_rate': float(package.gst_rate) if package.gst_rate else 0.0,
                    'is_gst_exempt': package.is_gst_exempt
                })
        
        elif item_type == 'Service':
            services = session.query(Service).filter(
                Service.hospital_id == hospital_id,
                Service.is_active == True,
                Service.service_name.ilike(f'%{query}%')
            ).limit(10).all()
            
            for service in services:
                results.append({
                    'id': str(service.service_id),
                    'name': service.service_name,
                    'type': 'Service',
                    'price': float(service.price) if service.price else 0.0,
                    'gst_rate': float(service.gst_rate) if service.gst_rate else 0.0,
                    'is_gst_exempt': service.is_gst_exempt,
                    'sac_code': service.sac_code
                })
        
        elif item_type in ['Medicine', 'Prescription']:
            medicines = session.query(Medicine).filter(
                Medicine.hospital_id == hospital_id,
                Medicine.is_active == True,
                Medicine.name.ilike(f'%{query}%')
            ).limit(10).all()
            
            for medicine in medicines:
                results.append({
                    'id': str(medicine.medicine_id),
                    'name': medicine.name,
                    'type': 'Medicine',
                    'gst_rate': float(medicine.gst_rate) if medicine.gst_rate else 0.0,
                    'is_gst_exempt': medicine.is_gst_exempt,
                    'hsn_code': medicine.hsn_code
                })
        
        return jsonify(results)
       
    except Exception as e:
        current_app.logger.error(f"Error searching items: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error searching items'}), 500

@billing_api_bp.route('/medicine/<uuid:medicine_id>/batches', methods=['GET'])
@token_required
def api_medicine_batches(user_id, session, medicine_id):
    """API endpoint to get available batches for a medicine"""
    try:
        # Get query parameters
        quantity = Decimal(request.args.get('quantity', '1'))
        
        # Get user's hospital ID
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        hospital_id = user.hospital_id
        
        # Get medicine details
        medicine = session.query(Medicine).filter_by(
            hospital_id=hospital_id,
            medicine_id=medicine_id,
            is_active=True
        ).first()
        
        if not medicine:
            return jsonify({'error': 'Medicine not found'}), 404
        
        # Get batch selection for invoice
        batches = get_batch_selection_for_invoice(hospital_id, medicine_id, quantity)
        
        return jsonify(batches)
       
    except Exception as e:
        current_app.logger.error(f"Error getting medicine batches: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error getting medicine batches'}), 500

@billing_api_bp.route('/invoice/<uuid:invoice_id>', methods=['GET'])
@token_required
def get_invoice_api(user_id, session, invoice_id):
    """API endpoint to get invoice details"""
    try:
        # Get user's hospital ID
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        hospital_id = user.hospital_id
        
        # Get invoice details
        invoice = get_invoice_service(
            hospital_id=hospital_id,
            invoice_id=invoice_id,
            session=session
        )
        
        return jsonify(invoice)
       
    except Exception as e:
        current_app.logger.error(f"Error getting invoice: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error getting invoice'}), 500

@billing_api_bp.route('/invoices', methods=['GET'])
@token_required
def search_invoices_api(user_id, session):
    """API endpoint to search invoices with filters and pagination"""
    try:
        # Get user's hospital ID
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        hospital_id = user.hospital_id
        
        # Get filter parameters
        filters = {}
        
        if request.args.get('invoice_number'):
            filters['invoice_number'] = request.args.get('invoice_number')
            
        if request.args.get('patient_id'):
            filters['patient_id'] = uuid.UUID(request.args.get('patient_id'))
            
        if request.args.get('invoice_type'):
            filters['invoice_type'] = request.args.get('invoice_type')
            
        if request.args.get('is_gst_invoice') is not None:
            filters['is_gst_invoice'] = request.args.get('is_gst_invoice') == 'true'
            
        if request.args.get('date_from'):
            date_from = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
            filters['date_from'] = date_from.replace(tzinfo=timezone.utc)
            
        if request.args.get('date_to'):
            date_to = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
            # Set time to end of day
            date_to = date_to.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            filters['date_to'] = date_to
            
        if request.args.get('payment_status'):
            filters['payment_status'] = request.args.get('payment_status')
        
        # Get page and page size
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        
        # Search invoices
        result = search_invoices_service(
            hospital_id=hospital_id,
            filters=filters,
            page=page,
            page_size=page_size,
            session=session
        )
        
        return jsonify(result)
       
    except Exception as e:
        current_app.logger.error(f"Error searching invoices: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error searching invoices'}), 500

# Login-required adapter endpoints

# Keep the token-based methods as they are (for mobile/API access)
@billing_api_bp.route('/patient/search_web', methods=['GET'])
@login_required
def api_patient_search_web():
    """DEPRECATED: Web-friendly adapter for patient search
    
    This endpoint is deprecated - use /invoice/web_api/patient/search directly instead.
    Kept for backward compatibility.
    """
    current_app.logger.warning("Using deprecated endpoint: /api/patient/search_web. Use /invoice/web_api/patient/search instead.")
    # Redirect to the actual endpoint
    return redirect(url_for('billing_views.web_api_patient_search', **request.args))

@billing_api_bp.route('/item/search_web', methods=['GET'])
@login_required
def api_item_search_web():
    """DEPRECATED: Web-friendly adapter for item search
    
    This endpoint is deprecated - use /invoice/web_api/item/search directly instead.
    Kept for backward compatibility.
    """
    current_app.logger.warning("Using deprecated endpoint: /api/item/search_web. Use /invoice/web_api/item/search instead.")
    return redirect(url_for('billing_views.web_api_item_search', **request.args))

@billing_api_bp.route('/medicine/<uuid:medicine_id>/batches_web', methods=['GET'])
@login_required
def api_medicine_batches_web(medicine_id):
    """DEPRECATED: Web-friendly adapter for medicine batches
    
    This endpoint is deprecated - use /invoice/web_api/medicine/<id>/batches directly instead.
    Kept for backward compatibility.
    """
    current_app.logger.warning("Using deprecated endpoint: /api/medicine/<id>/batches_web. Use /invoice/web_api/medicine/<id>/batches instead.")
    return redirect(url_for('billing_views.web_api_medicine_batches', medicine_id=medicine_id, **request.args))
@billing_api_bp.route('/invoice/create_web', methods=['POST'])
@login_required
def create_invoice_api_web():
    """Web-friendly adapter for invoice creation that uses Flask-Login"""
    try:
        with get_db_session() as session:
            # Get request data
            data = request.json if request.is_json else request.form

            # DEBUG: Log received data
            logger.info(f"DEBUG - Received patient_id: {data.get('patient_id')}")
            logger.info(f"DEBUG - Received patient_name: {data.get('patient_name')}")

            # Extract required parameters
            hospital_id = current_user.hospital_id
            branch_id = uuid.UUID(data.get('branch_id')) if data.get('branch_id') else None

            # FIX: Ensure we're getting patient_id (UUID), not patient_name
            patient_id_raw = data.get('patient_id')

            # Check if patient_id is actually a name (contains spaces, not a UUID format)
            if patient_id_raw and (' ' in patient_id_raw or not '-' in patient_id_raw):
                # This looks like a patient name, not a UUID - need to look up by name
                logger.error(f"❌ Received patient NAME instead of UUID: '{patient_id_raw}'")
                raise ValueError(f"Invalid patient_id format. Received: '{patient_id_raw}'. Expected UUID format.")

            patient_id = uuid.UUID(patient_id_raw)
            invoice_date_str = data.get('invoice_date')
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            notes = data.get('notes')
            
            # Process line items
            line_items = []
            for item_data in data.get('line_items', []):
                line_item = {
                    'item_type': item_data.get('item_type'),
                    'item_id': uuid.UUID(item_data.get('item_id')),
                    'item_name': item_data.get('item_name'),
                    'quantity': Decimal(str(item_data.get('quantity', 1))),
                    'unit_price': Decimal(str(item_data.get('unit_price', 0))),
                    'discount_percent': Decimal(str(item_data.get('discount_percent', 0))),
                    'included_in_consultation': item_data.get('included_in_consultation', False)
                }
                
                # Add batch and expiry for medicines
                if item_data.get('item_type') in ['Medicine', 'Prescription'] and item_data.get('batch'):
                    line_item['batch'] = item_data.get('batch')
                    if item_data.get('expiry_date'):
                        line_item['expiry_date'] = item_data.get('expiry_date')
                
                line_items.append(line_item)
            
            # Create invoices based on business rules
            result = create_invoice_service(
                hospital_id=hospital_id,
                branch_id=branch_id,
                patient_id=patient_id,
                invoice_date=invoice_date,
                line_items=line_items,
                notes=notes,
                current_user_id=current_user.user_id,
                session=session
            )
            
            # Return appropriate response based on number of invoices created
            invoice_count = result.get('count', 0)
            if invoice_count == 1:
                # Single invoice
                invoice = result['invoices'][0]
                return jsonify({
                    'success': True,
                    'invoice_id': invoice['invoice_id'],
                    'invoice_number': invoice['invoice_number'],
                    'message': 'Invoice created successfully'
                }), 201
            elif invoice_count > 1:
                # Multiple invoices
                invoice_ids = [inv['invoice_id'] for inv in result['invoices']]
                invoice_numbers = [inv['invoice_number'] for inv in result['invoices']]
                return jsonify({
                    'success': True,
                    'invoice_count': invoice_count,
                    'invoice_ids': invoice_ids,
                    'invoice_numbers': invoice_numbers,
                    'message': f'{invoice_count} invoices created successfully based on item types'
                }), 201
            else:
                return jsonify({
                    'success': False,
                    'message': 'No invoices created. Please check your line items.'
                }), 400
    except ValueError as e:
        # Business logic errors (validation, inventory, etc.)
        current_app.logger.error(f"Validation error creating invoice: {str(e)}", exc_info=True)

        # Store form data in session to preserve on redirect
        from flask import session as flask_session
        flask_session['invoice_error_data'] = {
            'branch_id': str(branch_id) if branch_id else None,
            'patient_id': str(patient_id),
            'invoice_date': invoice_date_str,
            'notes': notes,
            'line_items': data.get('line_items', [])  # Keep original line items data
        }
        flask_session['invoice_error_message'] = str(e)

        return jsonify({
            'success': False,
            'error': str(e),
            'preserveData': True  # Signal to frontend to preserve data
        }), 400
    except Exception as e:
        # Unexpected errors
        current_app.logger.error(f"Unexpected error creating invoice: {str(e)}", exc_info=True)

        # Still preserve data for unexpected errors
        from flask import session as flask_session
        flask_session['invoice_error_data'] = {
            'branch_id': str(branch_id) if branch_id else None,
            'patient_id': str(patient_id),
            'invoice_date': invoice_date_str,
            'notes': notes,
            'line_items': data.get('line_items', [])
        }
        flask_session['invoice_error_message'] = f"System Error: {str(e)}"

        return jsonify({
            'success': False,
            'error': f"An unexpected error occurred: {str(e)}",
            'preserveData': True
        }), 500

@billing_api_bp.route('/invoice/<uuid:invoice_id>_web', methods=['GET'])
@login_required
def get_invoice_api_web(invoice_id):
    """Web-friendly adapter for getting invoice details that uses Flask-Login"""
    try:
        with get_db_session() as session:
            hospital_id = current_user.hospital_id
            
            # Get invoice details
            invoice = get_invoice_service(
                hospital_id=hospital_id,
                invoice_id=invoice_id,
                session=session
            )
            
            return jsonify(invoice)
    except Exception as e:
        current_app.logger.error(f"Error getting invoice: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error getting invoice'}), 500

@billing_api_bp.route('/invoices_web', methods=['GET'])
@login_required
def search_invoices_api_web():
    """Web-friendly adapter for searching invoices that uses Flask-Login"""
    try:
        with get_db_session() as session:
            hospital_id = current_user.hospital_id
            
            # Get filter parameters
            filters = {}
            
            if request.args.get('invoice_number'):
                filters['invoice_number'] = request.args.get('invoice_number')
                
            if request.args.get('patient_id'):
                filters['patient_id'] = uuid.UUID(request.args.get('patient_id'))
                
            if request.args.get('invoice_type'):
                filters['invoice_type'] = request.args.get('invoice_type')
                
            if request.args.get('is_gst_invoice') is not None:
                filters['is_gst_invoice'] = request.args.get('is_gst_invoice') == 'true'
                
            if request.args.get('date_from'):
                date_from = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
                filters['date_from'] = date_from.replace(tzinfo=timezone.utc)
                
            if request.args.get('date_to'):
                date_to = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
                # Set time to end of day
                date_to = date_to.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
                filters['date_to'] = date_to
                
            if request.args.get('payment_status'):
                filters['payment_status'] = request.args.get('payment_status')
            
            # Get page and page size
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))
            
            # Search invoices
            result = search_invoices_service(
                hospital_id=hospital_id,
                filters=filters,
                page=page,
                page_size=page_size,
                session=session
            )
            
            return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Error searching invoices: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error searching invoices'}), 500


# ============================================================================
# ENHANCED PAYMENT FORM API ENDPOINTS
# ============================================================================

@billing_api_bp.route('/billing/patient/<patient_id>/outstanding-invoices', methods=['GET'])
@login_required
def get_patient_outstanding_invoices(patient_id):
    """
    Get all outstanding (unpaid and partially paid) invoices for a patient
    WITH line items and associated package installments for unified payment view

    Used by enhanced payment form
    """
    try:
        from app.models.transaction import InvoiceLineItem, PackagePaymentPlan, InstallmentPayment
        from app.services.subledger_service import get_line_item_ar_balance

        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            # Get sort parameter (default: latest first)
            sort_order = request.args.get('sort', 'desc')  # 'asc' or 'desc'

            # Query all invoices with balance due > 0
            invoices_query = session.query(InvoiceHeader).filter(
                InvoiceHeader.hospital_id == hospital_id,
                InvoiceHeader.patient_id == patient_id,
                InvoiceHeader.is_cancelled == False,
                InvoiceHeader.balance_due > 0
            )

            # ✅ Sort by invoice date (default: latest first)
            if sort_order == 'asc':
                invoices = invoices_query.order_by(InvoiceHeader.invoice_date.asc()).all()
            else:
                invoices = invoices_query.order_by(InvoiceHeader.invoice_date.desc()).all()

            # Convert to dictionaries with line items and installments
            invoice_list = []
            for invoice in invoices:
                invoice_dict = get_entity_dict(invoice)

                # Get line items for this invoice
                line_items = session.query(InvoiceLineItem).filter(
                    InvoiceLineItem.invoice_id == invoice.invoice_id
                ).order_by(InvoiceLineItem.line_item_id).all()

                line_items_data = []
                for line_item in line_items:
                    line_dict = get_entity_dict(line_item)

                    # Get AR balance for this line item
                    try:
                        line_balance = get_line_item_ar_balance(
                            hospital_id=hospital_id,
                            patient_id=patient_id,
                            line_item_id=line_item.line_item_id,
                            session=session
                        )
                    except:
                        line_balance = line_dict['line_total']

                    # Check if this line item is a package with installments
                    installments_data = []
                    if line_dict['item_type'] == 'Package' and line_item.package_id:
                        # Find package plan linked to THIS SPECIFIC package (not just any package in the invoice)
                        package_plan = session.query(PackagePaymentPlan).filter(
                            PackagePaymentPlan.invoice_id == invoice.invoice_id,
                            PackagePaymentPlan.package_id == line_item.package_id,  # ✅ FIX: Filter by specific package
                            PackagePaymentPlan.status == 'active'
                        ).first()

                        if package_plan:
                            # Get pending installments for this package
                            installments = session.query(InstallmentPayment).filter(
                                InstallmentPayment.plan_id == package_plan.plan_id,
                                InstallmentPayment.status.in_(['pending', 'partial', 'overdue'])
                            ).order_by(InstallmentPayment.due_date.asc()).all()

                            for inst in installments:
                                inst_dict = get_entity_dict(inst)
                                inst_balance = float(inst_dict['amount']) - float(inst_dict.get('paid_amount', 0))

                                # Payable amount is limited by invoice balance
                                payable_amount = min(inst_balance, float(invoice.balance_due))

                                installments_data.append({
                                    'installment_id': str(inst_dict['installment_id']),
                                    'installment_number': inst_dict['installment_number'],
                                    'due_date': inst_dict['due_date'].isoformat() if inst_dict.get('due_date') else None,
                                    'amount': float(inst_dict['amount']),
                                    'paid_amount': float(inst_dict.get('paid_amount', 0)),
                                    'balance_amount': inst_balance,
                                    'payable_amount': payable_amount if payable_amount > 0 else 0,
                                    'status': inst_dict['status']
                                })

                    line_items_data.append({
                        'line_item_id': str(line_dict['line_item_id']),
                        'item_type': line_dict['item_type'],
                        'item_name': line_dict['item_name'],
                        'line_total': float(line_dict['line_total']),
                        'line_balance': float(line_balance),
                        'has_installments': len(installments_data) > 0,
                        'installments': installments_data
                    })

                invoice_list.append({
                    'invoice_id': str(invoice_dict['invoice_id']),
                    'invoice_number': invoice_dict['invoice_number'],
                    'invoice_date': invoice_dict['invoice_date'].isoformat() if invoice_dict.get('invoice_date') else None,
                    'invoice_type': invoice_dict.get('invoice_type', ''),
                    'is_gst_invoice': invoice_dict.get('is_gst_invoice', False),
                    'grand_total': float(invoice_dict['grand_total']),
                    'paid_amount': float(invoice_dict.get('paid_amount', 0)),
                    'balance_due': float(invoice_dict['balance_due']),
                    'currency_code': invoice_dict.get('currency_code', 'INR'),
                    'line_items': line_items_data
                })

            return jsonify({
                'success': True,
                'invoices': invoice_list,
                'count': len(invoice_list)
            })

    except Exception as e:
        logger.error(f"Error fetching outstanding invoices for patient {patient_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch outstanding invoices',
            'message': str(e)
        }), 500


@billing_api_bp.route('/billing/patient/<patient_id>/advance-balance', methods=['GET'])
@login_required
def get_patient_advance_balance_api(patient_id):
    """
    Get current advance balance for a patient
    Used by enhanced payment form
    """
    try:
        from app.services.billing_service import get_patient_advance_balance

        hospital_id = current_user.hospital_id

        # Get advance balance using existing service
        balance = get_patient_advance_balance(
            hospital_id=hospital_id,
            patient_id=patient_id
        )

        return jsonify({
            'success': True,
            'balance': float(balance),
            'patient_id': str(patient_id)
        })

    except Exception as e:
        logger.error(f"Error fetching advance balance for patient {patient_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch advance balance',
            'message': str(e)
        }), 500


@billing_api_bp.route('/billing/patient/<patient_id>/pending-installments', methods=['GET'])
@login_required
def get_patient_pending_installments(patient_id):
    """
    Get all pending package installments for a patient
    Used by enhanced payment form
    """
    try:
        from app.models.transaction import PackagePaymentPlan, InstallmentPayment

        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            # Query pending installments from active packages with invoice balance
            from app.models.master import InvoiceHeader

            installments = session.query(
                InstallmentPayment,
                PackagePaymentPlan.package_name,
                InvoiceHeader.balance_due.label('invoice_balance')
            ).join(
                PackagePaymentPlan,
                InstallmentPayment.plan_id == PackagePaymentPlan.plan_id
            ).outerjoin(
                InvoiceHeader,
                PackagePaymentPlan.invoice_id == InvoiceHeader.invoice_id
            ).filter(
                InstallmentPayment.hospital_id == hospital_id,
                PackagePaymentPlan.patient_id == patient_id,
                PackagePaymentPlan.status == 'active',
                InstallmentPayment.status.in_(['pending', 'partial', 'overdue'])
            ).order_by(InstallmentPayment.due_date.asc()).all()

            # Convert to dictionaries and filter based on invoice balance
            installment_list = []
            for installment, package_name, invoice_balance in installments:
                installment_dict = get_entity_dict(installment)

                # Calculate installment balance
                installment_balance = float(installment_dict['amount']) - float(installment_dict.get('paid_amount', 0))

                # If linked to an invoice, check invoice balance
                if invoice_balance is not None:
                    invoice_balance_float = float(invoice_balance)

                    # Skip if invoice is fully paid
                    if invoice_balance_float <= 0:
                        logger.debug(f"Skipping installment {installment_dict['installment_id']} - invoice fully paid")
                        continue

                    # Payable amount is minimum of installment balance and invoice balance
                    payable_amount = min(installment_balance, invoice_balance_float)
                else:
                    # No invoice link - use full installment balance
                    payable_amount = installment_balance

                installment_list.append({
                    'installment_id': str(installment_dict['installment_id']),
                    'plan_id': str(installment_dict['plan_id']),
                    'package_name': package_name,
                    'installment_number': installment_dict['installment_number'],
                    'due_date': installment_dict['due_date'].isoformat() if installment_dict.get('due_date') else None,
                    'amount': float(installment_dict['amount']),
                    'paid_amount': float(installment_dict.get('paid_amount', 0)),
                    'balance_amount': installment_balance,
                    'payable_amount': payable_amount,  # ✅ NEW: Actual amount that can be paid
                    'invoice_balance': invoice_balance_float if invoice_balance is not None else None,  # ✅ NEW: Invoice balance for reference
                    'status': installment_dict['status']
                })

            return jsonify({
                'success': True,
                'installments': installment_list,
                'count': len(installment_list)
            })

    except Exception as e:
        logger.error(f"Error fetching pending installments for patient {patient_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch pending installments',
            'message': str(e)
        }), 500


@billing_api_bp.route('/ar-statement/<patient_id>', methods=['GET'])
@login_required
def get_ar_statement(patient_id):
    """
    Get patient AR statement with complete transaction history

    Query Parameters:
        highlight_id (optional): Transaction ID to highlight (invoice_id, payment_id, credit_note_id, or plan_id)

    Returns:
        JSON with patient info, transactions list, and summary totals
    """
    try:
        hospital_id = current_user.hospital_id
        highlight_id = request.args.get('highlight_id')

        from app.services.ar_statement_service import ARStatementService

        service = ARStatementService()
        result = service.get_patient_ar_statement(
            patient_id=patient_id,
            hospital_id=hospital_id,
            highlight_reference_id=highlight_id
        )

        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 404

    except Exception as e:
        logger.error(f"Error fetching AR statement for patient {patient_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch AR statement',
            'message': str(e)
        }), 500


@billing_api_bp.route('/patient-balance/<patient_id>', methods=['GET'])
@login_required
def get_patient_balance(patient_id):
    """
    Get current balance for a patient (quick query)

    Returns:
        JSON with current balance and balance type
    """
    try:
        hospital_id = current_user.hospital_id

        from app.services.ar_statement_service import ARStatementService

        service = ARStatementService()
        result = service.get_patient_balance(
            patient_id=patient_id,
            hospital_id=hospital_id
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error fetching patient balance: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch patient balance',
            'message': str(e)
        }), 500