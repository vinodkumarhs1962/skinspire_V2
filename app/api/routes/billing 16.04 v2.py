# app/api/routes/billing.py

import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import Session

from flask_login import login_required, current_user  # Add this import
from app.services.database_service import get_db_session, get_entity_dict
from app.services.billing_service import create_invoice as create_invoice_service
from app.models.transaction import User, InvoiceHeader
from app.models.master import Service, Package, Medicine, Hospital, Patient
from app.security.authorization.decorators import token_required
from app.security.authorization.permission_validator import has_permission
from app.services.billing_service import get_batch_selection_for_invoice



# Configure logger
logger = logging.getLogger(__name__)

# Create API blueprint
billing_api_bp = Blueprint('billing_api', __name__, url_prefix='/api')

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
@login_required
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
@login_required
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
@login_required
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
       
       # Get available batches
       from app.models.transaction import Inventory
       from sqlalchemy import func
       
       # Get the latest inventory entry for each batch
       latest_entries = session.query(
           Inventory.batch,
           Inventory.expiry,
           Inventory.current_stock,
           Inventory.sale_price,
           func.max(Inventory.created_at).label('latest_date')
       ).filter(
           Inventory.hospital_id == hospital_id,
           Inventory.medicine_id == medicine_id,
           Inventory.current_stock >= quantity
       ).group_by(
           Inventory.batch,
           Inventory.expiry,
           Inventory.current_stock,
           Inventory.sale_price
       ).order_by(
           Inventory.expiry.asc()  # Order by expiry date (oldest first)
       ).all()
       
       # Format results
       batches = []
       for entry in latest_entries:
           batch_info = {
               'batch': entry.batch,
               'expiry': entry.expiry.isoformat() if entry.expiry else None,
               'available_quantity': float(entry.current_stock),
               'sale_price': float(entry.sale_price) if entry.sale_price else None
           }
           batches.append(batch_info)
       
       return jsonify({
           'medicine_id': str(medicine_id),
           'medicine_name': medicine.name,
           'batches': batches
       })
       
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
       invoice = session.query(InvoiceHeader).filter_by(
           hospital_id=hospital_id,
           invoice_id=invoice_id
       ).first()
       
       if not invoice:
           return jsonify({'error': 'Invoice not found'}), 404
       
       # Get line items
       from app.models.transaction import InvoiceLineItem
       line_items = session.query(InvoiceLineItem).filter_by(
           hospital_id=hospital_id,
           invoice_id=invoice_id
       ).all()
       
       # Create response
       invoice_dict = get_entity_dict(invoice)
       line_items_dict = [get_entity_dict(item) for item in line_items]
       
       # Add line items to invoice dictionary
       invoice_dict['line_items'] = line_items_dict
       
       # Check for consolidated prescription
       invoice_dict['is_consolidated_prescription'] = False
       if invoice.invoice_type == 'Service':
           for item in line_items:
               if item.item_name == "Doctor's Examination and Treatment":
                   invoice_dict['is_consolidated_prescription'] = True
                   break
       
       return jsonify(invoice_dict)
       
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
       
       # Start with base query
       query = session.query(InvoiceHeader).filter_by(hospital_id=hospital_id)
       
       # Apply filters
       if 'invoice_number' in filters and filters['invoice_number']:
           query = query.filter(InvoiceHeader.invoice_number.ilike(f"%{filters['invoice_number']}%"))
           
       if 'patient_id' in filters and filters['patient_id']:
           query = query.filter(InvoiceHeader.patient_id == filters['patient_id'])
           
       if 'invoice_type' in filters and filters['invoice_type']:
           query = query.filter(InvoiceHeader.invoice_type == filters['invoice_type'])
           
       if 'is_gst_invoice' in filters:
           query = query.filter(InvoiceHeader.is_gst_invoice == filters['is_gst_invoice'])
           
       if 'date_from' in filters and filters['date_from']:
           query = query.filter(InvoiceHeader.invoice_date >= filters['date_from'])
           
       if 'date_to' in filters and filters['date_to']:
           query = query.filter(InvoiceHeader.invoice_date <= filters['date_to'])
           
       if 'payment_status' in filters and filters['payment_status']:
           if filters['payment_status'] == 'paid':
               query = query.filter(InvoiceHeader.balance_due == 0)
           elif filters['payment_status'] == 'partial':
               query = query.filter(InvoiceHeader.paid_amount > 0, InvoiceHeader.balance_due > 0)
           elif filters['payment_status'] == 'unpaid':
               query = query.filter(InvoiceHeader.paid_amount == 0)
       
       # Get total count
       total_count = query.count()
       
       # Apply pagination
       query = query.order_by(InvoiceHeader.created_at.desc())
       query = query.offset((page - 1) * page_size).limit(page_size)
       
       # Get results
       invoices = query.all()
       
       # Format results
       invoice_dicts = []
       for invoice in invoices:
           invoice_dict = get_entity_dict(invoice)
           
           # Get patient name
           patient = session.query(Patient).filter_by(patient_id=invoice.patient_id).first()
           if patient:
               invoice_dict['patient_name'] = patient.full_name
               invoice_dict['patient_mrn'] = patient.mrn
           
           invoice_dicts.append(invoice_dict)
       
       # Calculate pagination info
       total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
       
       return jsonify({
           'items': invoice_dicts,
           'total': total_count,
           'page': page,
           'page_size': page_size,
           'pages': total_pages
       })
       
   except Exception as e:
       current_app.logger.error(f"Error searching invoices: {str(e)}", exc_info=True)
       return jsonify({'error': 'Error searching invoices'}), 500
