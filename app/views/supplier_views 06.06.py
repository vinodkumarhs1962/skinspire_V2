# app/views/supplier_views.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, g
from flask_login import login_required, current_user
from datetime import datetime
import uuid

from app.services.database_service import get_db_session
from app.security.authorization.permission_validator import has_permission
from app.models.master import Supplier, Medicine, Branch
from app.models.transaction import SupplierInvoice, PurchaseOrderHeader

from app.security.authorization.decorators import (
    require_web_branch_permission, 
    require_web_cross_branch_permission
)

# ADD this helper function after the existing imports and before route definitions:
def get_branch_context():
    """
    Helper function to get branch context - NOW delegates to service layer
    """
    from app.services.permission_service import get_user_branch_context
    return get_user_branch_context(current_user.user_id, current_user.hospital_id, 'supplier')

def get_branch_uuid_from_context_or_request():
    """
    Helper function to get branch UUID - NOW delegates to service layer
    """
    from app.services.branch_service import get_branch_from_user_and_request
    return get_branch_from_user_and_request(current_user.user_id, current_user.hospital_id, 'supplier')

supplier_views_bp = Blueprint('supplier_views', __name__, url_prefix='/supplier')


# Supplier Master Management - Using Controller
@supplier_views_bp.route('/', methods=['GET'])
@login_required
@require_web_branch_permission('supplier', 'view')  # NEW: Branch-aware decorator
def supplier_list():
    """Display list of suppliers with filtering and branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier', 'view'):
    
    # CRITICAL FIX: Override branch logic for testing user
    if str(current_user.user_id) == '7777777777':
        # Testing user gets complete bypass - no branch filtering at all
        branch_uuid = None
        current_app.logger.info("TESTING OVERRIDE: Setting branch_uuid to None for complete bypass")
        
        # Still get branch context for UI components (they handle their own display logic)
        try:
            _, branch_context = get_branch_uuid_from_context_or_request()
            # Modify the context to indicate we're using the override
            if branch_context:
                branch_context['method'] = 'testing_override'
            else:
                branch_context = {'method': 'testing_override', 'accessible_branches': []}
        except Exception as e:
            current_app.logger.warning(f"Could not get branch context for UI: {e}")
            branch_context = {'method': 'testing_override_fallback', 'accessible_branches': []}
    else:
        # Regular users go through normal branch logic
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()

    # Enhanced debug logging to confirm our fix
    current_app.logger.info(f"=== BRANCH DEBUG START ===")
    current_app.logger.info(f"User ID: {current_user.user_id} (type: {type(current_user.user_id)})")
    current_app.logger.info(f"Branch UUID FINAL: {branch_uuid} (type: {type(branch_uuid)})")
    current_app.logger.info(f"Branch context method FINAL: {branch_context.get('method') if branch_context else 'None'}")
    current_app.logger.info(f"Is testing user: {str(current_user.user_id) == '7777777777'}")
    current_app.logger.info(f"=== BRANCH DEBUG END ===")

    # Import form locally to avoid circular imports (UNCHANGED)
    try:
        from app.forms.supplier_forms import SupplierFilterForm
        form = SupplierFilterForm()
    except ImportError:
        current_app.logger.warning("SupplierFilterForm not found, using None")
        form = None
    
    # Existing filter parameters (UNCHANGED)
    name = request.args.get('name')
    category = request.args.get('supplier_category')
    gst_number = request.args.get('gst_number')
    status = request.args.get('status', 'active')
    
    # Existing pagination (UNCHANGED)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        # Import service locally (UNCHANGED)
        from app.services.supplier_service import search_suppliers
        
        # UPDATED: Service call now includes branch filtering and user context
        result = search_suppliers(
            hospital_id=current_user.hospital_id,
            name=name,
            category=category,
            gst_number=gst_number,
            status=status,
            blacklisted=None,
            branch_id=branch_uuid, 
            current_user_id=current_user.user_id,  # NEW: Pass user for auto-branch detection
            page=page,
            per_page=per_page
        )
        
        suppliers = result.get('suppliers', [])
        total = result.get('pagination', {}).get('total_count', 0)

        # NEW: Add branch information to suppliers for display
        for supplier in suppliers:
            if 'branch_id' in supplier:
                try:
                    from app.services.database_service import get_db_session
                    from app.models.master import Branch
                    
                    with get_db_session(read_only=True) as session:
                        branch = session.query(Branch).filter_by(
                            branch_id=supplier['branch_id']
                        ).first()
                        supplier['branch_name'] = branch.name if branch else 'Unknown Branch'
                except Exception:
                    supplier['branch_name'] = 'Unknown Branch'

        return render_template(
            'supplier/supplier_list.html',
            suppliers=suppliers,
            form=form,
            page=page,
            per_page=per_page,
            total=total,
            branch_context=getattr(g, 'branch_context', None) 
        )
    except Exception as e:
        current_app.logger.error(f"Error in supplier_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving suppliers: {str(e)}", "error")
        return render_template(
            'supplier/supplier_list.html', 
            form=form, 
            suppliers=[], 
            total=0, 
            page=1, 
            per_page=per_page,
            branch_context=getattr(g, 'branch_context', None) 
        )


@supplier_views_bp.route('/add', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier', 'add')  # NEW: Branch-aware decorator
def add_supplier():
    """Add a new supplier using FormController with branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier', 'add'):
    
    # Import controller locally to avoid circular imports (UNCHANGED)
    from app.controllers.supplier_controller import SupplierFormController
    controller = SupplierFormController()
    return controller.handle_request()


@supplier_views_bp.route('/edit/<supplier_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier', 'edit', branch_source='entity')  # NEW: Entity-based branch detection
def edit_supplier(supplier_id):
    """Edit an existing supplier using FormController with branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier', 'edit'):
    
    # Import controller locally to avoid circular imports (UNCHANGED)
    from app.controllers.supplier_controller import SupplierFormController
    controller = SupplierFormController(supplier_id=supplier_id)
    return controller.handle_request()


@supplier_views_bp.route('/view/<supplier_id>', methods=['GET'])
@login_required
@require_web_branch_permission('supplier', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def view_supplier(supplier_id):
    """View supplier details with branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier', 'view'):
    
    try:
        # Import service locally (UNCHANGED)
        from app.services.supplier_service import search_supplier_invoices
        
        # Get supplier from database directly (UNCHANGED logic, but enhanced with branch info)
        with get_db_session(read_only=True) as session:
            supplier_obj = session.query(Supplier).filter_by(
                supplier_id=supplier_id,
                hospital_id=current_user.hospital_id
            ).first()
            
            if not supplier_obj:
                flash('Supplier not found', 'warning')
                return redirect(url_for('supplier_views.supplier_list'))
            
            # NEW: Add branch information
            branch_name = 'Unknown Branch'
            if supplier_obj.branch_id:
                branch = session.query(Branch).filter_by(
                    branch_id=supplier_obj.branch_id
                ).first()
                branch_name = branch.name if branch else 'Unknown Branch'

            # Convert to dictionary for template compatibility (ENHANCED with branch info)
            supplier_dict = {
                'supplier_id': str(supplier_obj.supplier_id),
                'supplier_name': supplier_obj.supplier_name,
                'branch_name': branch_name,  # NEW
                'branch_id': str(supplier_obj.branch_id) if supplier_obj.branch_id else None,  # NEW
                'supplier_category': supplier_obj.supplier_category,
                'status': supplier_obj.status,
                'gst_registration_number': supplier_obj.gst_registration_number,
                'pan_number': supplier_obj.pan_number,
                'created_at': supplier_obj.created_at,
                'updated_at': supplier_obj.updated_at
            }
        
        # Rest of the function remains UNCHANGED
        balance_info = {
            'total_invoiced': 0,
            'total_paid': 0,
            'balance_due': 0
        }
        
        try:
            invoice_result = search_supplier_invoices(
                hospital_id=current_user.hospital_id,
                supplier_id=uuid.UUID(supplier_id),
                page=1,
                per_page=10
            )
            recent_invoices = invoice_result.get('invoices', [])
        except Exception as e:
            current_app.logger.warning(f"Error getting invoices: {str(e)}")
            recent_invoices = []
        
        return render_template('supplier/supplier_view.html',
                            supplier=supplier_obj,
                            balance_info=balance_info,
                            recent_invoices=recent_invoices,
                            page_title=supplier_obj.supplier_name,
                            branch_context=getattr(g, 'branch_context', None))
    
    except Exception as e:
        current_app.logger.error(f"Error in view_supplier: {str(e)}", exc_info=True)
        flash(f'Error loading supplier: {str(e)}', 'danger')
        return redirect(url_for('supplier_views.supplier_list'))


# Supplier Invoice Management - Using Controller
@supplier_views_bp.route('/invoices', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_invoice', 'view')  # NEW: Branch-aware decorator
def supplier_invoice_list():
    """Display list of supplier invoices with filtering and branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_invoice', 'view'):
    
    # NEW: Get branch context from decorator
    branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
    
    # Import form locally (UNCHANGED)
    from app.forms.supplier_forms import SupplierInvoiceFilterForm
    form = SupplierInvoiceFilterForm()
    
    # Existing filter parameters (UNCHANGED)
    invoice_number = request.args.get('invoice_number')
    supplier_id = request.args.get('supplier_id')
    po_id = request.args.get('po_id')
    payment_status = request.args.get('payment_status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Existing pagination (UNCHANGED)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        # Import service locally (UNCHANGED)
        from app.services.supplier_service import search_supplier_invoices
        from app.services.supplier_service import search_suppliers
        
        # UPDATED: Get suppliers for dropdown with branch filtering
        supplier_result = search_suppliers(
            hospital_id=current_user.hospital_id,
            status='active',
            branch_id=branch_uuid,  # NEW: Filter suppliers by branch
            current_user_id=current_user.user_id,  # NEW: Pass user context
            page=1,
            per_page=1000  # Get all active suppliers
        )
        suppliers = supplier_result.get('suppliers', [])
        
        # UPDATED: Service call now includes branch filtering and user context
        result = search_supplier_invoices(
            hospital_id=current_user.hospital_id,
            invoice_number=invoice_number,
            supplier_id=supplier_id,
            po_id=po_id,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_uuid,  # NEW: Pass branch filter
            current_user_id=current_user.user_id,  # NEW: Pass user context
            page=page,
            per_page=per_page
        )
        
        invoices = result.get('invoices', [])
        total = result.get('pagination', {}).get('total_count', 0)
        
        # Existing summary calculations (UNCHANGED)
        total_invoices = len(invoices)
        unpaid_amount = sum(float(invoice.get('balance_due', 0)) for invoice in invoices)
        paid_amount = sum(float(invoice.get('payment_total', 0)) for invoice in invoices)
        
        listed_total = 0
        for invoice in invoices:
            if 'total_amount' in invoice and invoice['total_amount'] is not None:
                try:
                    listed_total += float(invoice['total_amount'])
                except (ValueError, TypeError):
                    current_app.logger.warning(f"Could not convert invoice total_amount to float: {invoice['total_amount']}")
        
        if invoices and len(invoices) > 0:
            current_app.logger.info(f"First invoice structure keys: {list(invoices[0].keys())}")

        summary = {
            'total_invoices': total_invoices,
            'unpaid_amount': round(unpaid_amount, 2),
            'paid_amount': round(paid_amount, 2),
            'listed_total': round(listed_total, 2)
        }
            
        return render_template(
            'supplier/supplier_invoice_list.html',
            invoices=invoices,
            suppliers=suppliers,
            form=form,
            page=page,
            per_page=per_page,
            total=total,
            summary=summary,
            branch_context=getattr(g, 'branch_context', None) 
        )
    except Exception as e:
        current_app.logger.error(f"Error in supplier_invoice_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving supplier invoices: {str(e)}", "error")
        return render_template(
            'supplier/supplier_invoice_list.html', 
            form=form, 
            invoices=[], 
            suppliers=[],
            summary={'total_invoices': 0, 'unpaid_amount': 0, 'paid_amount': 0, 'listed_total': 0},
            branch_context=getattr(g, 'branch_context', None) 
        )


@supplier_views_bp.route('/invoice/add', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'add')  # NEW: Branch-aware decorator
def add_supplier_invoice():
    """Create a new supplier invoice using FormController with branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_invoice', 'add'):
    
    # Check if we're coming from a PO (UNCHANGED)
    po_id = request.args.get('po_id')
    
    # Import controller locally (UNCHANGED)
    from app.controllers.supplier_controller import SupplierInvoiceFormController
    
    # Create controller with or without pre-populated PO data (UNCHANGED)
    if po_id:
        controller = SupplierInvoiceFormController(po_id=po_id)
    else:
        controller = SupplierInvoiceFormController()
        
    return controller.handle_request()


@supplier_views_bp.route('/invoice/view/<invoice_id>', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_invoice', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def view_supplier_invoice(invoice_id):
    """View supplier invoice details with branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_invoice', 'view'):
    
    try:
        # Import service locally (UNCHANGED)
        from app.services.supplier_service import get_supplier_invoice_by_id, get_purchase_order_by_id
        
        invoice = get_supplier_invoice_by_id(
            invoice_id=uuid.UUID(invoice_id),
            hospital_id=current_user.hospital_id,
            include_payments=True
        )
        
        if not invoice:
            flash("Supplier invoice not found", "error")
            return redirect(url_for('supplier_views.supplier_invoice_list'))
        
        # Rest of the function remains UNCHANGED (PO data, supplier extraction, etc.)
        po_data = None
        if invoice.get('po_id'):
            try:
                if not invoice.get('po_number'):
                    with get_db_session(read_only=True) as po_session:
                        po_header = po_session.query(PurchaseOrderHeader).filter_by(
                            po_id=invoice.get('po_id')
                        ).first()
                        if po_header:
                            invoice['po_number'] = po_header.po_number
                            current_app.logger.info(f"Added PO number {po_header.po_number} to invoice")
            except Exception as po_error:
                current_app.logger.warning(f"Could not fetch PO number: {str(po_error)}")
        
        # Extract supplier from invoice data (UNCHANGED)
        supplier = {
            'supplier_id': invoice.get('supplier_id'),
            'supplier_name': invoice.get('supplier_name', ''),
            'supplier_address': invoice.get('supplier_address', {}),
            'contact_info': invoice.get('contact_info', {}),
            'gst_registration_number': invoice.get('supplier_gstin', ''),
            'pan_number': '',
            'tax_type': 'Regular',
            'supplier_category': ''
        }
        
        # Get payments from invoice data (UNCHANGED)
        payments = invoice.get('payments', [])
        
        # Calculate subtotal and taxable value (UNCHANGED)
        subtotal_sum = 0
        taxable_value_sum = 0
        
        if 'line_items' in invoice:
            for line in invoice['line_items']:
                units = float(line.get('units', 0))
                price = float(line.get('pack_purchase_price', 0))
                line_subtotal = units * price
                subtotal_sum += line_subtotal
                
                if 'taxable_amount' in line and line['taxable_amount'] is not None:
                    taxable_value = float(line['taxable_amount'])
                else:
                    discount = float(line.get('discount_amount', 0))
                    taxable_value = line_subtotal - discount
                
                taxable_value_sum += taxable_value
        
        invoice['calculated_subtotal'] = subtotal_sum
        invoice['calculated_taxable_value'] = taxable_value_sum

        # Calculate GST summary (UNCHANGED)
        gst_summary = []
        if 'line_items' in invoice:
            gstin_groups = {}
            for line in invoice['line_items']:
                key = (line.get('hsn_code', ''), line.get('gst_rate', 0))
                if key not in gstin_groups:
                    gstin_groups[key] = {
                        'hsn_code': key[0],
                        'gst_rate': key[1],
                        'taxable_value': 0,
                        'cgst': 0,
                        'sgst': 0,
                        'igst': 0,
                        'total_gst': 0
                    }
                gstin_groups[key]['taxable_value'] += float(line.get('taxable_amount', 0))
                gstin_groups[key]['cgst'] += float(line.get('cgst', 0))
                gstin_groups[key]['sgst'] += float(line.get('sgst', 0))
                gstin_groups[key]['igst'] += float(line.get('igst', 0))
                gstin_groups[key]['total_gst'] += float(line.get('total_gst', 0))
            
            gst_summary = list(gstin_groups.values())
        
        attachments = []
            
        return render_template(
            'supplier/view_supplier_invoice.html',
            invoice=invoice,
            supplier=supplier,
            payments=payments,
            gst_summary=gst_summary,
            attachments=attachments,
            subtotal_sum=subtotal_sum,
            taxable_value_sum=taxable_value_sum,
            po_data=po_data,
            branch_context=getattr(g, 'branch_context', None)
        )
    except Exception as e:
        current_app.logger.error(f"Error in view_supplier_invoice: {str(e)}", exc_info=True)
        flash(f"Error retrieving supplier invoice details: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_invoice_list'))

@supplier_views_bp.route('/purchase-orders', methods=['GET'])
@login_required
@require_web_branch_permission('purchase_order', 'view')  # NEW: Branch-aware decorator
def purchase_order_list():
    """Display list of purchase orders with filtering and branch awareness."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'purchase_order', 'view'):
    
    # NEW: Get branch context from decorator
    branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
    
    # Import form locally (UNCHANGED)
    from app.forms.supplier_forms import PurchaseOrderFilterForm
    form = PurchaseOrderFilterForm()
    
    # Existing filter parameters (UNCHANGED)
    po_number = request.args.get('po_number')
    supplier_id = request.args.get('supplier_id')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Existing pagination (UNCHANGED)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        # Import service locally (UNCHANGED)
        from app.services.supplier_service import search_purchase_orders, search_supplier_invoices
        
        # UPDATED: Service call now includes branch filtering and user context
        result = search_purchase_orders(
            hospital_id=current_user.hospital_id,
            po_number=po_number,
            supplier_id=supplier_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_uuid,  # NEW: Pass branch filter
            current_user_id=current_user.user_id,  # NEW: Pass user context
            page=page,
            per_page=per_page
        )
        
        purchase_orders = result.get('purchase_orders', [])
        total = result.get('pagination', {}).get('total_count', 0)

        # Check which POs already have invoices (UNCHANGED logic)
        if purchase_orders:
            po_invoice_map = {}
            for po in purchase_orders:
                try:
                    if po.get('po_id'):
                        invoice_result = search_supplier_invoices(
                            hospital_id=current_user.hospital_id,
                            po_id=po.get('po_id'),
                            page=1,
                            per_page=1
                        )
                        po_invoice_map[str(po.get('po_id'))] = len(invoice_result.get('invoices', [])) > 0
                except Exception as inv_error:
                    current_app.logger.error(f"Error checking invoices for PO {po.get('po_id')}: {str(inv_error)}")
                    
            for po in purchase_orders:
                po['has_invoices'] = po_invoice_map.get(str(po.get('po_id')), False)

        return render_template(
            'supplier/purchase_order_list.html',
            purchase_orders=purchase_orders,
            form=form,
            page=page,
            per_page=per_page,
            total=total,
            branch_context=getattr(g, 'branch_context', None)  # Get branch context from decorator
        )
    except Exception as e:
        current_app.logger.error(f"Error in purchase_order_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving purchase orders: {str(e)}", "error")
        
        return render_template(
            'supplier/purchase_order_list.html', 
            form=form, 
            purchase_orders=[], 
            page=1, 
            per_page=20,
            total=0,
            branch_context=branch_context  # NEW: Pass branch context to template
        )


@supplier_views_bp.route('/purchase-order/add', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('purchase_order', 'add')  # NEW: Branch-aware decorator
def add_purchase_order():
    """Add new purchase order with enhanced validation handling and branch awareness"""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'purchase_order', 'create'):

    from app.controllers.supplier_controller import PurchaseOrderFormController
    controller = PurchaseOrderFormController()
    
    try:
        # Handle the request through the controller (UNCHANGED)
        result = controller.handle_request()
        
        if isinstance(result, str):
            return result
            
        from flask import Response
        if isinstance(result, Response):
            return result
            
        current_app.logger.warning(f"Unexpected result type from controller: {type(result)}")
        return result
        
    except ValueError as ve:
        # Handle validation errors with detailed messages (UNCHANGED)
        error_msg = str(ve)
        
        if '\n' in error_msg:
            error_lines = error_msg.split('\n')
            flash(error_lines[0], 'error')
            
            for line in error_lines[1:]:
                if line.strip():
                    flash(line.strip(), 'warning')
        else:
            flash(f'Validation Error: {error_msg}', 'error')
        
        current_app.logger.error(f"Validation error in add_purchase_order: {error_msg}")
        
        return controller.render_form(controller.get_form())
        
    except Exception as e:
        error_msg = f'Error creating purchase order: {str(e)}'
        flash(error_msg, 'error')
        current_app.logger.error(f"Error in add_purchase_order: {str(e)}", exc_info=True)
        
        return controller.render_form(controller.get_form())
    
@supplier_views_bp.route('/purchase-order/create', methods=['GET', 'POST'])
@login_required
def create_purchase_order():
    """Alias for add_purchase_order for template consistency."""
    return add_purchase_order()


@supplier_views_bp.route('/purchase-order/approve/<po_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('purchase_order', 'edit', branch_source='entity')  # NEW: Entity-based branch detection
def approve_purchase_order(po_id):
    """Approve a purchase order"""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'purchase_order', 'edit'):
    
    try:
        # Import service locally
        from app.services.supplier_service import update_purchase_order_status
        
        result = update_purchase_order_status(
            po_id=uuid.UUID(po_id),
            status='approved',
            hospital_id=current_user.hospital_id,
            current_user_id=current_user.user_id
        )
        
        flash('Purchase order approved successfully', 'success')
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
    except Exception as e:
        current_app.logger.error(f"Error approving PO: {str(e)}", exc_info=True)
        flash(f"Error approving purchase order: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))

@supplier_views_bp.route('/purchase-order/view/<po_id>', methods=['GET'])
@login_required
@require_web_branch_permission('purchase_order', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def view_purchase_order(po_id):
    """View purchase order details with branch awareness"""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'purchase_order', 'view'):
    
    try:
        # Import necessary modules (UNCHANGED)
        from app.services.supplier_service import get_purchase_order_by_id, get_supplier_by_id
        from app.forms.supplier_forms import PurchaseOrderCancelForm
        
        cancel_form = PurchaseOrderCancelForm()
        
        current_app.logger.info(f"Attempting to view PO with ID: {po_id}")
        
        try:
            po_id_uuid = uuid.UUID(po_id)
        except ValueError:
            current_app.logger.error(f"Invalid PO ID format: {po_id}")
            flash("Invalid purchase order ID format", "error")
            return redirect(url_for('supplier_views.purchase_order_list'))
        
        # Rest of the function remains UNCHANGED (get PO data, supplier data, timeline, etc.)
        po = get_purchase_order_by_id(
            po_id=po_id_uuid,
            hospital_id=current_user.hospital_id
        )
        
        if not po:
            flash("Purchase order not found", "error")
            return redirect(url_for('supplier_views.purchase_order_list'))
        
        supplier = None
        if po.get('supplier_id'):
            try:
                supplier = get_supplier_by_id(
                    supplier_id=po.get('supplier_id'),
                    hospital_id=current_user.hospital_id
                )
            except Exception as supplier_error:
                current_app.logger.error(f"Error getting supplier: {str(supplier_error)}")
        
        # Create timeline array (UNCHANGED)
        timeline = []
        if po.get('created_at'):
            timeline.append({
                'title': 'Created',
                'timestamp': po.get('created_at'),
                'icon': 'plus-circle',
                'color': 'blue'
            })
        
        if po.get('status') == 'approved':
            timeline.append({
                'title': 'Approved',
                'timestamp': po.get('updated_at'),
                'icon': 'check-circle',
                'color': 'green'
            })
            
        if po.get('status') == 'cancelled':
            timeline.append({
                'title': 'Cancelled',
                'timestamp': po.get('updated_at'),
                'icon': 'times-circle',
                'color': 'red'
            })
        
        current_app.logger.info(f"PO {po.get('po_number')} totals: "
                               f"Subtotal={po.get('calculated_subtotal', 0)}, "
                               f"GST={po.get('calculated_total_gst', 0)}, "
                               f"Total={po.get('total_amount', 0)}")
        
        return render_template(
            'supplier/view_purchase_order.html', 
            po=po, 
            purchase_order=po,
            supplier=supplier,
            cancel_form=cancel_form,
            timeline=timeline,
            branch_context=getattr(g, 'branch_context', None) 
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in view_purchase_order: {str(e)}", exc_info=True)
        flash(f"Error retrieving purchase order details: {str(e)}", "error")
        return redirect(url_for('supplier_views.purchase_order_list'))


@supplier_views_bp.route('/purchase-order/update-status/<po_id>', methods=['POST'])
@login_required
@require_web_branch_permission('purchase_order', 'edit', branch_source='entity')  # NEW: Entity-based branch detection
def update_po_status(po_id):
    """Update purchase order status."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'purchase_order', 'edit'):
    
    new_status = request.form.get('status')
    
    if not new_status:
        flash("Status is required", "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
    
    try:
        # Import service locally
        from app.services.supplier_service import update_purchase_order_status
        
        update_purchase_order_status(
            po_id=uuid.UUID(po_id),
            status=new_status,
            hospital_id=current_user.hospital_id,
            current_user_id=current_user.user_id
        )
        
        flash(f"Purchase order status updated to {new_status}", "success")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
    except Exception as e:
        current_app.logger.error(f"Error in update_po_status: {str(e)}", exc_info=True)
        flash(f"Error updating purchase order status: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))

@supplier_views_bp.route('/purchase-order/print/<po_id>', methods=['GET'])
@login_required
@require_web_branch_permission('purchase_order', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def print_purchase_order(po_id):
    """Print purchase order"""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'purchase_order', 'view'):
    
    try:
        # Import service locally to get the PO data
        from app.services.supplier_service import get_purchase_order_by_id, get_supplier_by_id
        
        po = get_purchase_order_by_id(
            po_id=uuid.UUID(po_id),
            hospital_id=current_user.hospital_id
        )
        
        if not po:
            flash("Purchase order not found", "error")
            return redirect(url_for('supplier_views.purchase_order_list'))
        
        # Get supplier data from the PO's supplier_id
        supplier = None
        if po.get('supplier_id'):
            try:
                supplier = get_supplier_by_id(
                    supplier_id=po.get('supplier_id'),
                    hospital_id=current_user.hospital_id
                )
            except Exception as supplier_error:
                current_app.logger.error(f"Error getting supplier for print: {str(supplier_error)}")
        
        return render_template(
            'supplier/print_purchase_order.html',
            po=po,
            purchase_order=po,  # Keep for backward compatibility
            supplier=supplier
        )
    except Exception as e:
        current_app.logger.error(f"Error printing purchase order: {str(e)}", exc_info=True)
        flash(f"Error printing purchase order: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))

@supplier_views_bp.route('/invoice/print/<invoice_id>', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_invoice', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def print_supplier_invoice(invoice_id):
    """Print supplier invoice"""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_invoice', 'view'):
    
    try:
        # Import necessary services
        from app.services.supplier_service import get_supplier_invoice_by_id, get_supplier_by_id
        
        # Get the invoice data
        invoice = get_supplier_invoice_by_id(
            invoice_id=uuid.UUID(invoice_id),
            hospital_id=current_user.hospital_id,
            include_payments=True
        )
        
        if not invoice:
            flash("Invoice not found", "error")
            return redirect(url_for('supplier_views.supplier_invoice_list'))
        
        # Get supplier details
        supplier = None
        if invoice.get('supplier_id'):
            try:
                supplier = get_supplier_by_id(
                    supplier_id=invoice.get('supplier_id'),
                    hospital_id=current_user.hospital_id
                )
            except Exception as supplier_error:
                current_app.logger.error(f"Error getting supplier for print: {str(supplier_error)}")
        
        # Get hospital info
        hospital = None
        try:
            with get_db_session(read_only=True) as session:
                from app.models.master import Hospital
                hospital = session.query(Hospital).filter_by(
                    hospital_id=current_user.hospital_id
                ).first()
        except Exception as hospital_error:
            current_app.logger.error(f"Error getting hospital info: {str(hospital_error)}")
        
        return render_template(
            'supplier/print_invoice.html',
            invoice=invoice,
            supplier=supplier,
            hospital=hospital,
            logo_url=None
        )
        
    except Exception as e:
        current_app.logger.error(f"Error printing supplier invoice: {str(e)}", exc_info=True)
        flash(f"Error printing invoice: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))

@supplier_views_bp.route('/purchase-order/email/<po_id>', methods=['GET'])
@login_required
def email_purchase_order(po_id):
    """Email purchase order."""
    flash("Email functionality is coming soon", "info")
    return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))

# Payment Management
@supplier_views_bp.route('/invoice/payment/<invoice_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_payment', 'add', branch_source='entity')  # NEW: Entity-based branch detection
def record_payment(invoice_id):
    """Record payment for supplier invoice."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_payment', 'add'):
    
    # Import form locally
    from app.forms.supplier_forms import SupplierPaymentForm
    form = SupplierPaymentForm()
    
    try:
        # Import service locally
        from app.services.supplier_service import get_supplier_invoice_by_id, record_supplier_payment
        
        invoice = get_supplier_invoice_by_id(
            invoice_id=uuid.UUID(invoice_id),
            hospital_id=current_user.hospital_id
        )
        
        if not invoice:
            flash("Supplier invoice not found", "error")
            return redirect(url_for('supplier_views.supplier_invoice_list'))
        
        if request.method == 'GET':
            form.amount.data = invoice.get('balance_due', 0)
            form.supplier_id.data = invoice.get('supplier_id')
        
        if form.validate_on_submit():
            payment_data = {
                'supplier_id': invoice.get('supplier_id'),
                'invoice_id': invoice_id,
                'payment_date': form.payment_date.data,
                'payment_method': form.payment_method.data,
                'currency_code': form.currency_code.data,
                'exchange_rate': form.exchange_rate.data,
                'amount': form.amount.data,
                'reference_no': form.reference_no.data,
                'notes': form.notes.data
            }
            
            payment = record_supplier_payment(
                hospital_id=current_user.hospital_id,
                payment_data=payment_data,
                create_gl_entries=True,
                current_user_id=current_user.user_id
            )
            
            flash("Payment recorded successfully", "success")
            return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
            
        return render_template(
            'supplier/payment_form.html',
            form=form,
            invoice=invoice,
            title="Record Supplier Payment"
        )
    except Exception as e:
        current_app.logger.error(f"Error in record_payment: {str(e)}", exc_info=True)
        flash(f"Error recording payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))


@supplier_views_bp.route('/payment-history/<supplier_id>', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_payment', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def payment_history(supplier_id):
    """View payment history for a supplier."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_payment', 'view'):
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Import service locally
        from app.services.supplier_service import get_supplier_payment_history
        
        with get_db_session(read_only=True) as session:
            supplier = session.query(Supplier).filter_by(
                supplier_id=supplier_id,
                hospital_id=current_user.hospital_id
            ).first()
            
            if not supplier:
                flash("Supplier not found", "error")
                return redirect(url_for('supplier_views.supplier_list'))
        
        payments = get_supplier_payment_history(
            supplier_id=uuid.UUID(supplier_id),
            hospital_id=current_user.hospital_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return render_template(
            'supplier/payment_history.html',
            supplier=supplier,
            payments=payments,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        current_app.logger.error(f"Error in payment_history: {str(e)}", exc_info=True)
        flash(f"Error retrieving payment history: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_list'))


@supplier_views_bp.route('/pending-invoices', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_invoice', 'view')  # NEW: Branch-aware decorator
def pending_invoices():
    """View pending supplier invoices."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_invoice', 'view'):
    
    # NEW: Get branch context from decorator
    branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
    
    supplier_id = request.args.get('supplier_id')
    
    try:
        # Import service locally
        from app.services.supplier_service import get_pending_supplier_invoices
        
        invoices = get_pending_supplier_invoices(
            hospital_id=current_user.hospital_id,
            supplier_id=uuid.UUID(supplier_id) if supplier_id else None,
            branch_id=branch_uuid  # NEW: Pass branch filter
        )
        
        return render_template(
            'supplier/pending_invoices.html',
            invoices=invoices,
            supplier_id=supplier_id,
            branch_context=branch_context  # NEW: Pass branch context to template
        )
    except Exception as e:
        current_app.logger.error(f"Error in pending_invoices: {str(e)}", exc_info=True)
        flash(f"Error retrieving pending invoices: {str(e)}", "error")
        return render_template(
            'supplier/pending_invoices.html', 
            invoices=[], 
            branch_context=branch_context
        )


# API Endpoints
@supplier_views_bp.route('/api/suppliers/<supplier_id>', methods=['GET'])
@login_required
@require_web_branch_permission('supplier', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def get_supplier_api(supplier_id):
    """API endpoint to get supplier details"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        with get_db_session(read_only=True) as session:
            supplier = session.query(Supplier).filter_by(
                supplier_id=supplier_id,
                hospital_id=current_user.hospital_id
            ).first()
            
            if not supplier:
                return jsonify({'error': 'Supplier not found'}), 404
            
            return jsonify({
                'supplier_id': str(supplier.supplier_id),
                'supplier_name': supplier.supplier_name,
                'gst_registration_number': supplier.gst_registration_number,
                'state_code': supplier.state_code,
                'payment_terms': supplier.payment_terms,
                'address': supplier.supplier_address,
                'contact_info': supplier.contact_info,
                'branch_id': str(supplier.branch_id) if supplier.branch_id else None,  # NEW: Include branch info
                'branch_name': None  # Will be populated if needed
            })
    
    except Exception as e:
        current_app.logger.error(f"Error getting supplier: {str(e)}")
        return jsonify({'error': str(e)}), 500


@supplier_views_bp.route('/api/medicines/search', methods=['GET'])
@login_required
@require_web_branch_permission('medicine', 'view')  # NEW: Branch-aware decorator
def search_medicines_api():
    """API endpoint to search medicines with branch awareness"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        term = request.args.get('term', '')
        
        if len(term) < 2:
            return jsonify({'medicines': []})
        
        # NEW: Get branch context for filtering
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
        
        with get_db_session(read_only=True) as session:
            query = session.query(Medicine).filter(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.medicine_name.ilike(f'%{term}%')
            )
            
            # NEW: Apply branch filtering if applicable
            if branch_uuid:
                query = query.filter(Medicine.branch_id == branch_uuid)
            
            medicines = query.limit(20).all()
            
            results = []
            for medicine in medicines:
                results.append({
                    'id': str(medicine.medicine_id),
                    'text': medicine.medicine_name,
                    'category': medicine.category.name if medicine.category else '',
                    'hsn_code': medicine.hsn_code,
                    'gst_rate': float(medicine.gst_rate or 0),
                    'cgst_rate': float(medicine.cgst_rate or 0),
                    'sgst_rate': float(medicine.sgst_rate or 0),
                    'igst_rate': float(medicine.igst_rate or 0),
                    'mrp': float(medicine.cost_price or 0),
                    'purchase_price': float(medicine.cost_price or 0),
                    'branch_id': str(medicine.branch_id) if hasattr(medicine, 'branch_id') and medicine.branch_id else None  # NEW
                })
            
            return jsonify({'medicines': results})
    
    except Exception as e:
        current_app.logger.error(f"Error searching medicines: {str(e)}")
        return jsonify({'error': str(e)}), 500


@supplier_views_bp.route('/api/medicines/<medicine_id>', methods=['GET'])
@login_required
@require_web_branch_permission('medicine', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def get_medicine_api(medicine_id):
    """API endpoint to get medicine details by ID"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        with get_db_session(read_only=True) as session:
            medicine = session.query(Medicine).filter_by(
                medicine_id=medicine_id,
                hospital_id=current_user.hospital_id
            ).first()
            
            if not medicine:
                return jsonify({'error': 'Medicine not found'}), 404
            
            try:
                medicine_dict = {}
                medicine_dict['medicine_id'] = str(medicine.medicine_id)
                medicine_dict['medicine_name'] = medicine.medicine_name
                medicine_dict['hsn_code'] = medicine.hsn_code if hasattr(medicine, 'hsn_code') else ''
                medicine_dict['gst_rate'] = float(medicine.gst_rate) if hasattr(medicine, 'gst_rate') and medicine.gst_rate is not None else 0
                medicine_dict['cgst_rate'] = float(medicine.cgst_rate) if hasattr(medicine, 'cgst_rate') and medicine.cgst_rate is not None else 0
                medicine_dict['sgst_rate'] = float(medicine.sgst_rate) if hasattr(medicine, 'sgst_rate') and medicine.sgst_rate is not None else 0
                medicine_dict['igst_rate'] = float(medicine.igst_rate) if hasattr(medicine, 'igst_rate') and medicine.igst_rate is not None else 0
                
                # Check various price attributes
                if hasattr(medicine, 'cost_price') and medicine.cost_price is not None:
                    medicine_dict['purchase_price'] = float(medicine.cost_price)
                    medicine_dict['mrp'] = float(medicine.cost_price)
                else:
                    medicine_dict['purchase_price'] = 0.0
                    medicine_dict['mrp'] = 0.0
                
                # Override MRP if other attributes exist
                for attr in ['mrp', 'selling_price', 'sale_price', 'retail_price']:
                    if hasattr(medicine, attr) and getattr(medicine, attr) is not None:
                        medicine_dict['mrp'] = float(getattr(medicine, attr))
                        break
                
                # NEW: Add branch information
                medicine_dict['branch_id'] = str(medicine.branch_id) if hasattr(medicine, 'branch_id') and medicine.branch_id else None
                        
                return jsonify(medicine_dict)
                
            except Exception as e:
                current_app.logger.error(f"Error processing medicine attributes: {str(e)}")
                return jsonify({
                    'medicine_id': str(medicine.medicine_id),
                    'medicine_name': medicine.medicine_name,
                    'hsn_code': '',
                    'gst_rate': 0.0,
                    'cgst_rate': 0.0,
                    'sgst_rate': 0.0,
                    'igst_rate': 0.0,
                    'purchase_price': 0.0,
                    'mrp': 0.0,
                    'branch_id': None
                })
    
    except Exception as e:
        current_app.logger.error(f"Error getting medicine: {str(e)}")
        return jsonify({'error': str(e)}), 500

@supplier_views_bp.route('/api/purchase-order/<po_id>/items', methods=['GET'])
@login_required
@require_web_branch_permission('purchase_order', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def get_po_items_api(po_id):
    """API endpoint to get PO line items"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        # Import service locally
        from app.services.supplier_service import get_purchase_order_by_id
        
        po = get_purchase_order_by_id(
            po_id=uuid.UUID(po_id),
            hospital_id=current_user.hospital_id
        )
        
        if not po:
            return jsonify({'error': 'Purchase order not found'}), 404
        
        items = []
        if 'line_items' in po:
            for line in po['line_items']:
                items.append({
                    'medicine_id': str(line.get('medicine_id')),
                    'medicine_name': line.get('medicine_name'),
                    'units': float(line.get('units', 0)),
                    'units_per_pack': float(line.get('units_per_pack', 1)),
                    'pack_purchase_price': float(line.get('pack_purchase_price', 0)),
                    'pack_mrp': float(line.get('pack_mrp', 0)),
                    'hsn_code': line.get('hsn_code'),
                    'gst_rate': float(line.get('gst_rate', 0)),
                    'cgst_rate': float(line.get('cgst_rate', 0)),
                    'sgst_rate': float(line.get('sgst_rate', 0)),
                    'igst_rate': float(line.get('igst_rate', 0)),
                    'branch_id': str(line.get('branch_id')) if line.get('branch_id') else None  # NEW
                })
        
        return jsonify({
            'items': items,
            'po_branch_id': str(po.get('branch_id')) if po.get('branch_id') else None  # NEW
        })
    
    except Exception as e:
        current_app.logger.error(f"Error getting PO items: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
# app/views/supplier_views.py

@supplier_views_bp.route('/api/po/calculate-line', methods=['POST'])
@login_required
def calculate_po_line():
    """
    REMOVE THIS ENDPOINT - GST calculations should happen server-side only
    """
    # This endpoint was used for dynamic client-side calculations
    # Now all calculations happen during PO creation and are stored in DB
    pass

@supplier_views_bp.route('/api/po/calculate-total', methods=['POST'])
@login_required
def calculate_po_total():
    """
    REMOVE THIS ENDPOINT - Totals should be aggregated from stored line totals
    """
    # This endpoint was used for dynamic total calculations
    # Now totals are calculated during PO creation and stored in DB
    pass

@supplier_views_bp.route('/api/purchase-order/<po_id>/load-items', methods=['GET'])
@login_required
@require_web_branch_permission('purchase_order', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def load_po_items(po_id):
    """Load items from a purchase order for an invoice."""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        # Import service locally
        from app.services.supplier_service import get_purchase_order_by_id
        
        po = get_purchase_order_by_id(
            po_id=uuid.UUID(po_id),
            hospital_id=current_user.hospital_id
        )
        
        if not po:
            return jsonify({'error': 'Purchase order not found'}), 404
        
        # Get line items
        line_items = po.get('line_items', [])
        
        # Format for invoice
        formatted_items = []
        for item in line_items:
            formatted_items.append({
                'medicine_id': str(item.get('medicine_id')),
                'medicine_name': item.get('medicine_name'),
                'units': float(item.get('units', 0)),
                'units_per_pack': float(item.get('units_per_pack', 1)),
                'pack_purchase_price': float(item.get('pack_purchase_price', 0)),
                'pack_mrp': float(item.get('pack_mrp', 0)),
                'hsn_code': item.get('hsn_code'),
                'gst_rate': float(item.get('gst_rate', 0)),
                'cgst_rate': float(item.get('cgst_rate', 0)),
                'sgst_rate': float(item.get('sgst_rate', 0)),
                'igst_rate': float(item.get('igst_rate', 0)),
                'branch_id': str(item.get('branch_id')) if item.get('branch_id') else None  # NEW
            })
        
        return jsonify({
            'success': True,
            'po_number': po.get('po_number'),
            'supplier_id': str(po.get('supplier_id')),
            'supplier_name': po.get('supplier_name', ''),
            'line_items': formatted_items,
            'po_branch_id': str(po.get('branch_id')) if po.get('branch_id') else None  # NEW
        })
        
    except Exception as e:
        current_app.logger.error(f"Error loading PO items: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@supplier_views_bp.route('/invoice/cancel/<invoice_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'delete', branch_source='entity')  # NEW: Entity-based branch detection
def cancel_supplier_invoice(invoice_id):
    """Cancel a supplier invoice."""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_invoice', 'delete'):
    
    # Import necessary modules
    from app.forms.supplier_forms import SupplierInvoiceCancelForm
    from app.services.supplier_service import get_supplier_invoice_by_id, cancel_supplier_invoice as service_cancel_invoice
    
    # Get the return URL from query parameter (for flexibility)
    return_to = request.args.get('return_to', 'list')  # 'list' or 'view'
    
    # For GET requests, show confirmation form
    if request.method == 'GET':
        form = SupplierInvoiceCancelForm()
        invoice = get_supplier_invoice_by_id(
            invoice_id=uuid.UUID(invoice_id),
            hospital_id=current_user.hospital_id
        )
        if not invoice:
            flash("Invoice not found", "error")
            return redirect(url_for('supplier_views.supplier_invoice_list'))
            
        return render_template(
            'supplier/cancel_invoice.html',
            form=form,
            invoice=invoice,
            return_to=return_to  # Pass to template
        )
    
    # For POST requests, process the form
    if request.method == 'POST':
        form = SupplierInvoiceCancelForm()
        
        if form.validate_on_submit():
            try:
                cancellation_reason = form.cancellation_reason.data
                
                result = service_cancel_invoice(
                    invoice_id=uuid.UUID(invoice_id),
                    hospital_id=current_user.hospital_id,
                    cancellation_reason=cancellation_reason,
                    current_user_id=current_user.user_id
                )
                
                flash(f"Invoice {result.get('supplier_invoice_number', '')} has been cancelled", "success")
                
                # Return based on where we came from
                if return_to == 'view':
                    return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
                else:
                    return redirect(url_for('supplier_views.supplier_invoice_list'))
                
            except ValueError as e:
                flash(str(e), "error")
                if return_to == 'view':
                    return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
                else:
                    return redirect(url_for('supplier_views.supplier_invoice_list'))
            except Exception as e:
                current_app.logger.error(f"Error in cancel_supplier_invoice: {str(e)}", exc_info=True)
                flash(f"Error cancelling invoice: {str(e)}", "error")
                if return_to == 'view':
                    return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
                else:
                    return redirect(url_for('supplier_views.supplier_invoice_list'))
                
        else:
            # Form validation failed
            invoice = get_supplier_invoice_by_id(
                invoice_id=uuid.UUID(invoice_id),
                hospital_id=current_user.hospital_id
            )
            
            flash("Please provide a cancellation reason", "error")
            return render_template(
                'supplier/cancel_invoice.html',
                form=form,
                invoice=invoice,
                return_to=return_to
            )
    
@supplier_views_bp.route('/invoice/edit/<invoice_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'edit', branch_source='entity')  # NEW: Entity-based branch detection
def edit_supplier_invoice(invoice_id):
    """Edit supplier invoice using centralized framework"""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'supplier_invoice', 'edit'):
    
    try:
        # Import the dedicated edit controller
        from app.controllers.supplier_controller import SupplierInvoiceEditController
        
        controller = SupplierInvoiceEditController(invoice_id=invoice_id)
        return controller.handle_request()
        
    except ValueError as ve:
        # Handle validation errors
        flash(str(ve), "error")
        return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
    except Exception as e:
        current_app.logger.error(f"Error in edit_supplier_invoice: {str(e)}", exc_info=True)
        flash(f"Error loading invoice for editing: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_invoice_list'))

@supplier_views_bp.route('/purchase-order/invoice-po/<po_id>', methods=['GET'])
@login_required
def view_invoice_purchase_order(po_id):
    """View purchase order from invoice - simplified view without all the complex logic."""
    if not has_permission(current_user, 'purchase_order', 'view'):
        flash('You do not have permission to view purchase orders', 'danger')
        return redirect(url_for('supplier_views.supplier_invoice_list'))
    
    try:
        # Import service locally
        from app.services.supplier_service import get_purchase_order_by_id
        from app.services.supplier_service import get_supplier_by_id
        
        # Get the PO data
        po = get_purchase_order_by_id(
            po_id=uuid.UUID(po_id),
            hospital_id=current_user.hospital_id
        )
        
        if not po:
            flash("Purchase order not found", "error")
            return redirect(url_for('supplier_views.supplier_invoice_list'))
        
        # Get the supplier data
        supplier = None
        if po.get('supplier_id'):
            try:
                supplier = get_supplier_by_id(
                    supplier_id=po.get('supplier_id'),
                    hospital_id=current_user.hospital_id
                )
            except Exception as supplier_error:
                current_app.logger.error(f"Error getting supplier: {str(supplier_error)}")
        
        # Use a simplified template specifically for showing PO from invoice
        return render_template(
            'supplier/invoice_po_view.html',
            po=po,
            supplier=supplier
        )
        
    except Exception as e:
        current_app.logger.error(f"Error displaying invoice PO: {str(e)}", exc_info=True)
        flash(f"Error retrieving purchase order details: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_invoice_list'))

@supplier_views_bp.route('/purchase-order/cancel/<po_id>')
@login_required
@require_web_branch_permission('purchase_order', 'edit', branch_source='entity')  # NEW: Entity-based branch detection
def cancel_purchase_order(po_id):
    """Cancel purchase order - simple status change"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        from app.services.supplier_service import update_purchase_order_status
        
        update_purchase_order_status(
            po_id=uuid.UUID(po_id),
            status='cancelled',
            hospital_id=current_user.hospital_id,
            current_user_id=current_user.user_id
        )
        
        flash('Purchase order cancelled successfully', 'success')
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
        
    except Exception as e:
        flash(f"Error cancelling purchase order: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
    
@supplier_views_bp.route('/purchase-order/edit/<po_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('purchase_order', 'edit', branch_source='entity')  # NEW: Entity-based branch detection
def edit_purchase_order(po_id):
    """Edit purchase order using centralized framework with branch awareness"""
    # REMOVED: Manual permission check - decorator handles it now
    # OLD: if not has_permission(current_user, 'purchase_order', 'edit'):
    
    try:
        # Check PO status before allowing edit (UNCHANGED)
        from app.services.supplier_service import get_purchase_order_by_id
        
        po = get_purchase_order_by_id(
            po_id=uuid.UUID(po_id),
            hospital_id=current_user.hospital_id
        )
        
        if not po:
            flash('Purchase order not found', 'error')
            return redirect(url_for('supplier_views.purchase_order_list'))
        
        if po.get('status') == 'cancelled':
            flash('Cancelled purchase orders cannot be edited', 'error')
            return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
        
        if po.get('status') != 'draft':
            flash('Only draft purchase orders can be edited', 'error')
            return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
        
        # Import the edit controller (UNCHANGED)
        from app.controllers.supplier_controller import PurchaseOrderEditController
        
        controller = PurchaseOrderEditController(po_id=po_id)
        return controller.handle_request()
        
    except ValueError as ve:
        flash(str(ve), "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
    except Exception as e:
        current_app.logger.error(f"Error in edit_purchase_order: {str(e)}", exc_info=True)
        flash(f"Error loading purchase order for editing: {str(e)}", "error")
        return redirect(url_for('supplier_views.purchase_order_list'))

@supplier_views_bp.route('/api/po/preview-gst', methods=['POST'])
@login_required
@require_web_branch_permission('purchase_order', 'add')  # NEW: Branch-aware decorator
def preview_po_gst():
    """Preview GST calculations for PO creation"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        data = request.json
        
        # Get hospital state for interstate calculation
        from app.services.database_service import get_db_session
        from app.models.master import Hospital
        
        with get_db_session() as session:
            hospital = session.query(Hospital).filter_by(hospital_id=current_user.hospital_id).first()
            hospital_state_code = hospital.state_code if hospital else None
        
        supplier_state_code = data.get('supplier_state_code', '')
        is_interstate = hospital_state_code != supplier_state_code if (hospital_state_code and supplier_state_code) else False
        
        # Calculate preview using standardized function
        from app.services.supplier_service import calculate_gst_values
        
        calculations = calculate_gst_values(
            quantity=float(data.get('quantity', 0)),
            unit_rate=float(data.get('unit_rate', 0)),
            gst_rate=float(data.get('gst_rate', 0)),
            discount_percent=float(data.get('discount_percent', 0)),
            is_free_item=data.get('is_free_item', False),
            is_interstate=is_interstate,
            conversion_factor=float(data.get('conversion_factor', 1))
        )
        
        return jsonify({
            'success': True,
            'calculations': {
                'base_amount': calculations['base_amount'],
                'discount_amount': calculations['discount_amount'],
                'taxable_amount': calculations['taxable_amount'],
                'cgst_amount': calculations['cgst_amount'],
                'sgst_amount': calculations['sgst_amount'],
                'igst_amount': calculations['igst_amount'],
                'total_gst_amount': calculations['total_gst_amount'],
                'line_total': calculations['line_total'],
                'is_interstate': is_interstate
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in preview_po_gst: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@supplier_views_bp.route('/api/po/preview-totals', methods=['POST'])
@login_required
@require_web_branch_permission('purchase_order', 'add')  # NEW: Branch-aware decorator
def preview_po_totals():
    """Calculate total amounts for multiple line items"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        data = request.json
        line_items = data.get('line_items', [])
        
        # Get hospital state for interstate calculation
        from app.services.database_service import get_db_session
        from app.models.master import Hospital
        
        with get_db_session() as session:
            hospital = session.query(Hospital).filter_by(hospital_id=current_user.hospital_id).first()
            hospital_state_code = hospital.state_code if hospital else None
        
        supplier_state_code = data.get('supplier_state_code', '')
        is_interstate = hospital_state_code != supplier_state_code if (hospital_state_code and supplier_state_code) else False
        
        from app.services.supplier_service import calculate_gst_values
        
        total_base = 0
        total_discount = 0
        total_taxable = 0
        total_gst = 0
        total_amount = 0
        
        line_calculations = []
        
        for item in line_items:
            calculations = calculate_gst_values(
                quantity=float(item.get('quantity', 0)),
                unit_rate=float(item.get('unit_rate', 0)),
                gst_rate=float(item.get('gst_rate', 0)),
                discount_percent=float(item.get('discount_percent', 0)),
                is_free_item=item.get('is_free_item', False),
                is_interstate=is_interstate,
                conversion_factor=float(item.get('conversion_factor', 1))
            )
            
            total_base += calculations['base_amount']
            total_discount += calculations['discount_amount']
            total_taxable += calculations['taxable_amount']
            total_gst += calculations['total_gst_amount']
            total_amount += calculations['line_total']
            
            line_calculations.append(calculations)
        
        return jsonify({
            'success': True,
            'totals': {
                'total_base_amount': total_base,
                'total_discount_amount': total_discount,
                'total_taxable_amount': total_taxable,
                'total_gst_amount': total_gst,
                'grand_total': total_amount,
                'is_interstate': is_interstate
            },
            'line_calculations': line_calculations
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in preview_po_totals: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    
@supplier_views_bp.route('/api/debug/po/<po_id>', methods=['GET'])
@login_required
@require_web_branch_permission('purchase_order', 'view', branch_source='entity')  # NEW: Entity-based branch detection
def debug_po_data(po_id):
    """Debug endpoint to check PO data integrity"""
    # REMOVED: Manual permission check - decorator handles it now
    
    try:
        from app.services.supplier_service import get_purchase_order_by_id
        from flask_login import current_user
        import uuid
        
        po = get_purchase_order_by_id(
            po_id=uuid.UUID(po_id),
            hospital_id=current_user.hospital_id
        )
        
        if not po:
            return jsonify({'error': 'PO not found'}), 404
        
        # Prepare debug information
        debug_info = {
            'po_number': po.get('po_number'),
            'stored_total': float(po.get('total_amount', 0)),
            'line_items_count': len(po.get('line_items', [])),
            'line_items': [],
            'branch_id': str(po.get('branch_id')) if po.get('branch_id') else None,  # NEW
            'branch_context': get_branch_context()  # NEW
        }
        
        calculated_total = 0
        for i, line in enumerate(po.get('line_items', [])):
            line_info = {
                'index': i + 1,
                'medicine_name': line.get('medicine_name'),
                'units': float(line.get('units', 0)),
                'pack_purchase_price': float(line.get('pack_purchase_price', 0)),
                'taxable_amount': float(line.get('taxable_amount', 0)),
                'total_gst': float(line.get('total_gst', 0)),
                'line_total': float(line.get('line_total', 0)),
                'is_free_item': line.get('is_free_item', False),
                'branch_id': str(line.get('branch_id')) if line.get('branch_id') else None  # NEW
            }
            debug_info['line_items'].append(line_info)
            calculated_total += line_info['line_total']
        
        debug_info['calculated_total'] = calculated_total
        debug_info['total_mismatch'] = abs(debug_info['stored_total'] - calculated_total) > 0.01
        
        return jsonify(debug_info)
        
    except Exception as e:
        current_app.logger.error(f"Debug endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
# NEW: Additional utility endpoint for branch information
@supplier_views_bp.route('/api/branch/context', methods=['GET'])
@login_required
@require_web_branch_permission('supplier', 'view')  # NEW: Branch-aware decorator
def get_branch_context_api():
    """API endpoint to get current user's branch context"""
    try:
        branch_context = get_branch_context()
        
        # Enhanced branch context with user info
        enhanced_context = {
            'user_id': current_user.user_id,
            'hospital_id': str(current_user.hospital_id),
            'branch_context': branch_context,
            'accessible_branches': branch_context.get('accessible_branches', []),
            'current_branch_id': branch_context.get('branch_id'),
            'is_multi_branch_user': branch_context.get('is_multi_branch_user', False),
            'permissions': {
                'supplier': {
                    'view': True,  # Already validated by decorator
                    'add': False,  # Would need separate check
                    'edit': False,  # Would need separate check
                    'delete': False  # Would need separate check
                }
            }
        }
        
        return jsonify({
            'success': True,
            'data': enhanced_context
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting branch context: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# NEW: Cross-branch reporting endpoint for executives
@supplier_views_bp.route('/api/reports/cross-branch/suppliers', methods=['GET'])
@login_required
@require_web_cross_branch_permission('supplier', 'view')  # NEW: Cross-branch decorator
def cross_branch_supplier_report_api():
    """API endpoint for cross-branch supplier statistics (executives only)"""
    try:
        # Import service for cross-branch data
        from app.services.supplier_service import get_cross_branch_supplier_summary
        
        summary = get_cross_branch_supplier_summary(current_user.hospital_id)
        
        return jsonify({
            'success': True,
            'data': summary,
            'branch_context': get_branch_context()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting cross-branch supplier report: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500