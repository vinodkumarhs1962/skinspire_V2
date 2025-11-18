# app/api/routes/supplier.py
from flask import Blueprint, jsonify, request, current_app
from app.security.authorization.permission_validator import has_permission
from app.security.authorization.decorators import token_required

supplier_api_bp = Blueprint('supplier_api', __name__, url_prefix='/api')

@supplier_api_bp.route('/suppliers', methods=['GET'])
@token_required
def get_suppliers(current_user, session):
    """Get suppliers with filtering and pagination"""
    # Check permissions manually to maintain compatibility
    if not has_permission(current_user, 'supplier', 'view'):
        return jsonify({'error': 'Permission denied'}), 403
        
    try:
        from app.services.supplier_service import search_suppliers
        
        # Get filter parameters
        name = request.args.get('name')
        category = request.args.get('category')
        gst_number = request.args.get('gst_number')
        status = request.args.get('status')
        blacklisted = request.args.get('blacklisted')
        
        if blacklisted is not None:
            blacklisted = blacklisted.lower() == 'true'
            
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Call service with session
        result = search_suppliers(
            hospital_id=current_user.hospital_id,
            name=name,
            category=category,
            gst_number=gst_number,
            status=status,
            blacklisted=blacklisted,
            page=page,
            per_page=per_page,
            session=session
        )
        
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error searching suppliers: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@supplier_api_bp.route('/supplier/<supplier_id>/invoices', methods=['GET'])
def get_supplier_invoices(supplier_id):
    """Get invoices for a specific supplier - for payment form dropdown filtering"""
    # Use session-based authentication for web forms
    from flask_login import login_required, current_user

    # Check if user is logged in
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401

    # Check permissions
    if not has_permission(current_user, 'supplier_invoice', 'view'):
        return jsonify({'error': 'Permission denied'}), 403

    try:
        from app.services.database_service import get_db_session
        from app.models.transaction import SupplierInvoice
        from sqlalchemy import or_
        import uuid

        # Get status filter (default: unpaid and partial)
        status_param = request.args.get('status', 'unpaid,partial')
        statuses = [s.strip() for s in status_param.split(',')]

        current_app.logger.info(f"Fetching invoices for supplier {supplier_id}, statuses: {statuses}")

        # Query invoices - calculate balance_due from payments
        with get_db_session(read_only=True) as db_session:
            from app.models.transaction import SupplierPayment
            from sqlalchemy import func

            query = db_session.query(SupplierInvoice).filter(
                SupplierInvoice.supplier_id == uuid.UUID(supplier_id),
                SupplierInvoice.hospital_id == current_user.hospital_id,
                SupplierInvoice.payment_status.in_(statuses)
            ).order_by(SupplierInvoice.invoice_date.desc())

            invoices = query.all()

            # Convert to dict format
            invoice_list = []
            for inv in invoices:
                # Calculate balance_due: total_amount - sum of approved payments
                paid_sum = db_session.query(func.sum(SupplierPayment.amount)).filter(
                    SupplierPayment.invoice_id == inv.invoice_id,
                    SupplierPayment.workflow_status == 'approved'
                ).scalar() or 0

                total_amount = float(inv.total_amount) if inv.total_amount else 0
                balance_due = total_amount - float(paid_sum)

                # Skip invoices with zero or negative balance
                # Only show invoices that have an outstanding balance to pay
                if balance_due <= 0.01:
                    continue

                invoice_list.append({
                    'invoice_id': str(inv.invoice_id),
                    'supplier_invoice_number': inv.supplier_invoice_number,
                    'invoice_date': inv.invoice_date.isoformat() if inv.invoice_date else None,
                    'due_date': inv.due_date.isoformat() if inv.due_date else None,
                    'total_amount': total_amount,
                    'balance_due': balance_due,
                    'payment_status': inv.payment_status,
                    'currency_code': inv.currency_code or 'INR'
                })

            current_app.logger.info(f"Found {len(invoice_list)} invoices for supplier {supplier_id}")

            return jsonify({
                'success': True,
                'invoices': invoice_list,
                'count': len(invoice_list)
            }), 200

    except ValueError as e:
        current_app.logger.error(f"Invalid supplier_id format: {str(e)}")
        return jsonify({'error': 'Invalid supplier ID format'}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching supplier invoices: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@supplier_api_bp.route('/supplier/<supplier_id>/advance-balance', methods=['GET'])
def get_supplier_advance_balance_api(supplier_id):
    """Get advance balance (unallocated payments) for a supplier"""
    # Use session-based authentication for web forms
    from flask_login import current_user

    # Check if user is logged in
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401

    # Check permissions
    if not has_permission(current_user, 'supplier_payment', 'view'):
        return jsonify({'error': 'Permission denied'}), 403

    try:
        from app.services.supplier_payment_service import SupplierPaymentService

        payment_service = SupplierPaymentService()
        result = payment_service.get_supplier_advance_balance(
            supplier_id=supplier_id,
            hospital_id=current_user.hospital_id
        )

        current_app.logger.info(f"Advance balance for supplier {supplier_id}: ₹{result.get('advance_balance', 0):.2f}")

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching supplier advance balance: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred', 'success': False}), 500

@supplier_api_bp.route('/supplier-invoice/<invoice_id>/items', methods=['GET'])
def get_supplier_invoice_items(invoice_id):
    """Get line items for a specific invoice"""
    from flask_login import current_user

    # Check if user is logged in
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401

    # Check permissions
    if not has_permission(current_user, 'supplier_invoice', 'view'):
        return jsonify({'error': 'Permission denied'}), 403

    try:
        from app.services.database_service import get_db_session
        from app.models.transaction import SupplierInvoice, SupplierInvoiceLine
        import uuid

        with get_db_session(read_only=True) as session:
            # Get invoice
            invoice = session.query(SupplierInvoice).filter_by(
                invoice_id=uuid.UUID(invoice_id),
                hospital_id=current_user.hospital_id
            ).first()

            if not invoice:
                return jsonify({'error': 'Invoice not found', 'success': False}), 404

            # Get line items
            items = session.query(SupplierInvoiceLine).filter_by(
                invoice_id=uuid.UUID(invoice_id)
            ).all()

            item_list = []
            for item in items:
                item_list.append({
                    'medicine_name': item.medicine_name,
                    'units': float(item.units or 0),
                    'pack_purchase_price': float(item.pack_purchase_price or 0),
                    'total_gst': float(item.total_gst or 0),
                    'line_total': float(item.line_total or 0)
                })

            return jsonify({
                'success': True,
                'items': item_list,
                'summary': {
                    'total_amount': float(invoice.total_amount or 0),
                    'item_count': len(item_list)
                }
            }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching invoice items: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred', 'success': False}), 500

# Add more endpoints as needed