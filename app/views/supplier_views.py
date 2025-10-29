# app/views/supplier_views.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, g
from flask_login import login_required, current_user
from datetime import datetime
import uuid

from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

from app.services.database_service import get_db_session
from app.security.authorization.permission_validator import has_permission
from app.models.master import Supplier, Medicine, Branch
from app.models.transaction import SupplierInvoice, PurchaseOrderHeader, SupplierPayment
from app.utils.menu_utils import generate_menu_for_role

from app.security.authorization.decorators import (
    require_web_branch_permission, 
    require_web_cross_branch_permission
)
from app.services.supplier_service import (
    search_supplier_payments,
    get_supplier_payment_by_id,
    add_payment_document,
    get_payment_document,
    log_document_access,
    approve_supplier_payment,
    reject_supplier_payment
)
from app.services.credit_note_service import create_credit_note_for_paid_invoice

from app.controllers.supplier_controller import SupplierPaymentController, PaymentApprovalController
from app.config import PAYMENT_CONFIG, DOCUMENT_CONFIG, POSTING_CONFIG

from app.services.branch_service import populate_branch_choices_for_user
from app.utils.form_helpers import populate_supplier_choices, populate_invoice_choices_for_supplier


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
        logger.info("TESTING OVERRIDE: Setting branch_uuid to None for complete bypass")
        
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
    logger.info(f"=== BRANCH DEBUG START ===")
    logger.info(f"User ID: {current_user.user_id} (type: {type(current_user.user_id)})")
    logger.info(f"Branch UUID FINAL: {branch_uuid} (type: {type(branch_uuid)})")
    logger.info(f"Branch context method FINAL: {branch_context.get('method') if branch_context else 'None'}")
    logger.info(f"Is testing user: {str(current_user.user_id) == '7777777777'}")
    logger.info(f"=== BRANCH DEBUG END ===")

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
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))
        return render_template(
            'supplier/supplier_list.html',
            suppliers=suppliers,
            form=form,
            page=page,
            per_page=per_page,
            total=total,
            branch_context=getattr(g, 'branch_context', None),
            menu_items=menu_items 
        )
    except Exception as e:
        current_app.logger.error(f"Error in supplier_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving suppliers: {str(e)}", "error")
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))
        return render_template(
            'supplier/supplier_list.html', 
            form=form, 
            suppliers=[], 
            total=0, 
            page=1, 
            per_page=per_page,
            branch_context=getattr(g, 'branch_context', None),
            menu_items=menu_items 
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
@require_web_branch_permission('supplier_invoice', 'view')
def supplier_invoice_list():
    """
    Display list of supplier invoices - USES AUTHORITATIVE CALCULATIONS ONLY
    REMOVED: All embedded calculation logic - now handled in service layer
    """
    
    # Get branch context (unchanged)
    branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
    
    # Import form locally (unchanged)
    from app.forms.supplier_forms import SupplierInvoiceFilterForm
    form = SupplierInvoiceFilterForm()
    
    # Filter parameters (unchanged)
    invoice_number = request.args.get('invoice_number')
    supplier_id = request.args.get('supplier_id')
    po_id = request.args.get('po_id')
    payment_status = request.args.get('payment_status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Pagination (unchanged)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        from app.services.supplier_service import search_supplier_invoices, search_suppliers
        
        # Get suppliers for dropdown (unchanged)
        supplier_result = search_suppliers(
            hospital_id=current_user.hospital_id,
            status='active',
            branch_id=branch_uuid,
            current_user_id=current_user.user_id,
            page=1,
            per_page=1000
        )
        suppliers = supplier_result.get('suppliers', [])
        
        # Parse dates (unchanged)
        start_date_obj = None
        end_date_obj = None
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        # SEARCH INVOICES WITH AUTHORITATIVE CALCULATIONS
        # No flags needed - authoritative calculations are now always applied
        result = search_supplier_invoices(
            hospital_id=current_user.hospital_id,
            supplier_id=uuid.UUID(supplier_id) if supplier_id else None,
            invoice_number=invoice_number,
            po_id=uuid.UUID(po_id) if po_id else None,
            payment_status=payment_status,
            start_date=start_date_obj,
            end_date=end_date_obj,
            branch_id=branch_uuid,
            current_user_id=current_user.user_id,
            page=page,
            per_page=per_page
        )
        
        invoices = result.get('invoices', [])
        total = result.get('total', 0)
        
        # 🎯 REMOVED: All embedded payment calculation logic
        # Each invoice in the list now contains authoritative calculations:
        # - payment_total (net effective payment)
        # - balance_due (remaining balance)
        # - payment_status (recalculated)
        # - gross_payments, credit_adjustments, has_credit_notes
        
        # Calculate summary statistics using authoritative values
        total_invoices = len(invoices)
        unpaid_amount = sum(float(inv.get('balance_due', 0)) for inv in invoices)
        paid_amount = sum(float(inv.get('payment_total', 0)) for inv in invoices)
        listed_total = sum(float(inv.get('total_amount', 0)) for inv in invoices)
        
        # Log summary of calculations used
        logger.info(f"Invoice list using authoritative calculations: "
                               f"Total invoices={total_invoices}, "
                               f"Total unpaid=₹{unpaid_amount:.2f}, "
                               f"Total paid=₹{paid_amount:.2f}")
        
        if len(invoices) > 0:
            logger.info(f"First invoice calculation method: {invoices[0].get('calculation_method', 'unknown')}")

        summary = {
            'total_invoices': total_invoices,
            'unpaid_amount': round(unpaid_amount, 2),
            'paid_amount': round(paid_amount, 2),
            'listed_total': round(listed_total, 2)
        }

        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))

        return render_template(
            'supplier/supplier_invoice_list.html',
            invoices=invoices,  # Now contains authoritative calculations
            suppliers=suppliers,
            form=form,
            page=page,
            per_page=per_page,
            total=total,
            summary=summary,
            branch_context=getattr(g, 'branch_context', None),
            menu_items=menu_items 
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in supplier_invoice_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving supplier invoices: {str(e)}", "error")
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))
        return render_template(
            'supplier/supplier_invoice_list.html', 
            form=form, 
            invoices=[], 
            suppliers=[],
            summary={'total_invoices': 0, 'unpaid_amount': 0, 'paid_amount': 0, 'listed_total': 0},
            branch_context=getattr(g, 'branch_context', None),
            menu_items=menu_items 
        )

@supplier_views_bp.route('/invoice/add', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'add')
def add_supplier_invoice():
    """Create new supplier invoice with branch awareness"""
    from flask import current_app, request
    
    try:
        current_app.logger.info(f"========== ADD_SUPPLIER_INVOICE ROUTE HIT ==========")
        current_app.logger.info(f"Method: {request.method}")
        current_app.logger.info(f"Form keys: {list(request.form.keys())}")
        current_app.logger.info(f"Has submit_invoice: {'submit_invoice' in request.form}")
        
        po_id = request.args.get('po_id')
        
        # Check if PO is fully invoiced before proceeding
        if po_id:
            from app.services.supplier_service import get_purchase_order_by_id
            from app.models.transaction import SupplierInvoice
            from sqlalchemy import func
            from app.services.database_service import get_db_session
            import uuid
            
            try:
                po = get_purchase_order_by_id(
                    po_id=uuid.UUID(po_id),
                    hospital_id=current_user.hospital_id
                )
                
                if po:
                    po_total = float(po.get('total_amount', 0))
                    po_number = po.get('po_number', 'N/A')
                    
                    # Check if fully invoiced
                    with get_db_session() as session:
                        invoiced_total = session.query(func.sum(SupplierInvoice.total_amount))\
                            .filter(
                                SupplierInvoice.po_id == uuid.UUID(po_id),
                                SupplierInvoice.hospital_id == current_user.hospital_id,
                                SupplierInvoice.payment_status != 'cancelled'
                            ).scalar() or 0
                        
                        remaining = po_total - float(invoiced_total)
                        
                        if remaining <= 0.01:
                            flash(f"Purchase Order {po_number} is already fully invoiced. No balance remaining.", "warning")
                            return redirect(url_for('universal_views.universal_list_view', entity_type='purchase_orders'))
            except Exception as e:
                current_app.logger.error(f"Error checking PO invoice status: {str(e)}")
                # Continue anyway if check fails
        
        from app.controllers.supplier_controller import SupplierInvoiceFormController
        
        if po_id:
            controller = SupplierInvoiceFormController(po_id=po_id)
        else:
            controller = SupplierInvoiceFormController()
        
        current_app.logger.info(f"Controller created, calling handle_request...")
        return controller.handle_request()
        
    except Exception as e:
        current_app.logger.error(f"Error in add_supplier_invoice: {str(e)}", exc_info=True)
        flash(f"Error loading invoice form: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_invoice_list'))


@supplier_views_bp.route('/invoice/view/<invoice_id>', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_invoice', 'view', branch_source='entity')
def view_supplier_invoice(invoice_id):
    """
    View supplier invoice details - USES AUTHORITATIVE CALCULATIONS ONLY
    REMOVED: All embedded calculation logic - now handled in service layer
    """
    
    try:
        from app.services.supplier_service import get_supplier_invoice_by_id, get_purchase_order_by_id
        
        # GET INVOICE WITH AUTHORITATIVE CALCULATIONS
        # No flags needed - authoritative calculations are now always applied
        invoice = get_supplier_invoice_by_id(
            invoice_id=uuid.UUID(invoice_id),
            hospital_id=current_user.hospital_id,
            include_payments=True
        )
        
        if not invoice:
            flash("Supplier invoice not found", "error")
            return redirect(url_for('supplier_views.supplier_invoice_list'))
        
        # 🎯 REMOVED: All the complex embedded credit note calculation logic
        # The invoice dict now contains authoritative calculations:
        # - payment_total (net effective payment)
        # - balance_due (remaining balance)
        # - payment_status (recalculated)
        # - gross_payments (total positive payments)
        # - credit_adjustments (total credit note adjustments)
        # - has_credit_notes (boolean indicator)
        
        # Log the authoritative calculation for verification
        logger.info(f"Using authoritative calculation for invoice {invoice_id}: "
                               f"Method={invoice.get('calculation_method')}, "
                               f"Gross Payments={invoice.get('gross_payments')}, "
                               f"Credit Adjustments={invoice.get('credit_adjustments')}, "
                               f"Net Payment={invoice.get('payment_total')}, "
                               f"Balance Due={invoice.get('balance_due')}, "
                               f"Status={invoice.get('payment_status')}")
        
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
                            logger.info(f"Added PO number {po_header.po_number} to invoice")
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
                rate = float(line.get('rate', 0))
                subtotal_sum += units * rate
                taxable_value_sum += float(line.get('taxable_value', 0))
        
        # Create GST summary (UNCHANGED)
        gst_summary = []
        if 'line_items' in invoice:
            gstin_groups = {}
            for line in invoice['line_items']:
                key = line.get('supplier_gstin', 'No GSTIN')
                if key not in gstin_groups:
                    gstin_groups[key] = {
                        'supplier_gstin': key,
                        'taxable_value': 0,
                        'cgst': 0,        # ✅ CORRECT - Template expects this
                        'sgst': 0,        # ✅ CORRECT - Template expects this
                        'igst': 0,        # ✅ CORRECT - Template expects this
                        'total_gst': 0
                    }
                
                gstin_groups[key]['taxable_value'] += float(line.get('taxable_amount', 0))
                gstin_groups[key]['cgst'] += float(line.get('cgst', 0))      # ✅ CORRECT
                gstin_groups[key]['sgst'] += float(line.get('sgst', 0))      # ✅ CORRECT
                gstin_groups[key]['igst'] += float(line.get('igst', 0))      # ✅ CORRECT
                gstin_groups[key]['total_gst'] += float(line.get('total_gst', 0))
            
            gst_summary = list(gstin_groups.values())
        
        attachments = []
            
        enhanced_context = {
            'invoice': invoice,  # Now contains authoritative payment calculations
            'supplier': supplier,
            'payments': payments,
            'gst_summary': gst_summary,
            'attachments': attachments,
            'subtotal_sum': subtotal_sum,
            'taxable_value_sum': taxable_value_sum,
            'po_data': po_data,
            'branch_context': getattr(g, 'branch_context', None),
            
            # Payment integration context (uses authoritative values)
            'can_create_payment': invoice.get('payment_status') != 'paid',
            'payment_url': url_for('supplier_views.record_payment', invoice_id=invoice.get('invoice_id')),
            'payment_config': PAYMENT_CONFIG,
            'pending_amount': float(invoice.get('balance_due', 0))
        }
        
        return render_template('supplier/view_supplier_invoice.html', **enhanced_context)
        
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

        # Generate menu items
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))

        return render_template(
            'supplier/purchase_order_list.html',
            purchase_orders=purchase_orders,
            form=form,
            page=page,
            per_page=per_page,
            total=total,
            branch_context=getattr(g, 'branch_context', None),  # Get branch context from decorator
            menu_items=menu_items
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
        
        # ✅ Cache invalidation
        from flask import Response, request
        if request.method == 'POST' and isinstance(result, Response) and result.status_code == 302:
            try:
                from app.engine.universal_service_cache import get_service_cache_manager
                cache_manager = get_service_cache_manager()
                if cache_manager:
                    invalidated = cache_manager.invalidate_entity_cache('purchase_orders', cascade=True)
                    current_app.logger.info(f"✅ Cache invalidated: {invalidated} entries")
            except Exception as e:
                current_app.logger.warning(f"⚠️ Cache failed: {e}")

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
        
        logger.info(f"Attempting to view PO with ID: {po_id}")
        
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
        
        logger.info(f"PO {po.get('po_number')} totals: "
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
        return redirect(url_for('universal_views.universal_detail_view', 
                       entity_type='purchase_orders', item_id=po_id))
        
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

@supplier_views_bp.route('/payment/print/<payment_id>', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view', branch_source='entity')
def print_supplier_payment(payment_id):
    """Print supplier payment receipt"""
    try:
        # Import necessary services
        from app.services.supplier_service import get_supplier_payment_by_id, get_supplier_by_id
        
        # Get the payment data
        payment = get_supplier_payment_by_id(
            payment_id=uuid.UUID(payment_id),
            hospital_id=current_user.hospital_id,
            include_documents=True,
            include_approvals=True
        )
        
        if not payment:
            flash("Payment not found", "error")
            return redirect(url_for('supplier_views.payment_list'))
        
        # Get supplier details
        supplier = None
        if payment.get('supplier_id'):
            try:
                supplier = get_supplier_by_id(
                    supplier_id=payment.get('supplier_id'),
                    hospital_id=current_user.hospital_id
                )
            except Exception as supplier_error:
                current_app.logger.error(f"Error getting supplier for print: {str(supplier_error)}")
        
        # Get invoice details if payment is linked to an invoice
        invoice = None
        if payment.get('invoice_id'):
            try:
                from app.services.supplier_service import get_supplier_invoice_by_id
                invoice = get_supplier_invoice_by_id(
                    invoice_id=payment.get('invoice_id'),
                    hospital_id=current_user.hospital_id
                )
            except Exception as invoice_error:
                current_app.logger.error(f"Error getting invoice for print: {str(invoice_error)}")
        
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
        
        # Get branch info
        branch = None
        if payment.get('branch_id'):
            try:
                with get_db_session(read_only=True) as session:
                    from app.models.master import Branch
                    branch = session.query(Branch).filter_by(
                        branch_id=payment.get('branch_id')
                    ).first()
            except Exception as branch_error:
                current_app.logger.error(f"Error getting branch info: {str(branch_error)}")
        
        return render_template(
            'supplier/print_payment.html',
            payment=payment,
            supplier=supplier,
            invoice=invoice,
            hospital=hospital,
            branch=branch,
            logo_url=None
        )
        
    except Exception as e:
        current_app.logger.error(f"Error printing supplier payment: {str(e)}", exc_info=True)
        flash(f"Error printing payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))


@supplier_views_bp.route('/purchase-order/email/<po_id>', methods=['GET'])
@login_required
def email_purchase_order(po_id):
    """Email purchase order."""
    flash("Email functionality is coming soon", "info")
    return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))

# Payment Management
# @supplier_views_bp.route('/invoice/payment/<invoice_id>', methods=['GET', 'POST'])
# @login_required
# @require_web_branch_permission('supplier_payment', 'add', branch_source='entity')
# def record_payment(invoice_id):
#     """Record payment for supplier invoice - FIXED UUID CONVERSION"""
    
#     from app.forms.supplier_forms import SupplierPaymentForm
#     form = SupplierPaymentForm()
    
#     try:
#         from app.services.supplier_service import get_supplier_invoice_by_id, record_supplier_payment
        
#         invoice = get_supplier_invoice_by_id(
#             invoice_id=uuid.UUID(invoice_id),
#             hospital_id=current_user.hospital_id
#         )
        
#         if not invoice:
#             flash("Supplier invoice not found", "error")
#             return redirect(url_for('supplier_views.supplier_invoice_list'))
        
#         # Set up form choices (unchanged)
#         try:
#             from app.services.database_service import get_db_session
#             from app.models.master import Supplier, Branch
            
#             with get_db_session(read_only=True) as session:
#                 # Get suppliers for dropdown
#                 suppliers = session.query(Supplier).filter_by(
#                     hospital_id=current_user.hospital_id,
#                     status='active'
#                 ).all()
                
#                 form.supplier_id.choices = [('', 'Select Supplier')] + [
#                     (str(s.supplier_id), s.supplier_name) for s in suppliers
#                 ]
                
#                 # Get branches for dropdown
#                 branches = session.query(Branch).filter_by(
#                     hospital_id=current_user.hospital_id,
#                     is_active=True
#                 ).all()
                
#                 form.branch_id.choices = [('', 'Select Branch')] + [
#                     (str(b.branch_id), b.name) for b in branches
#                 ]
                
#                 # Set invoice choices
#                 invoice_number = invoice.get('supplier_invoice_number', 'Unknown')
#                 balance_due = invoice.get('balance_due', 0) or invoice.get('total_amount', 0)
#                 invoice_display = f"{invoice_number} (Balance:  Rs.{balance_due:.2f})"
                
#                 form.invoice_id.choices = [
#                     ('', 'Select Invoice (Optional)'),
#                     (str(invoice_id), invoice_display)
#                 ]
            
#             # Set other choices
#             form.currency_code.choices = [
#                 ('INR', 'INR'),
#                 ('USD', 'USD'),
#                 ('EUR', 'EUR')
#             ]
            
#             form.payment_method.choices = [
#                 ('', 'Select Payment Method'),
#                 ('cash', 'Cash'),
#                 ('cheque', 'Cheque'),
#                 ('bank_transfer', 'Bank Transfer'),
#                 ('upi', 'UPI'),
#                 ('mixed', 'Multiple Methods')
#             ]
                
#         except Exception as e:
#             current_app.logger.error(f"Error setting up form choices: {str(e)}")
#             flash("Error setting up form", "error")
#             return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
        
#         # Pre-populate form (unchanged)
#         if request.method == 'GET':
#             balance_due = invoice.get('balance_due', 0)
#             total_amount = invoice.get('total_amount', 0)
#             amount_to_pay = balance_due if balance_due and balance_due > 0 else total_amount
            
#             # Set supplier
#             supplier_id = invoice.get('supplier_id')
#             supplier_id_str = str(supplier_id) if supplier_id else None
            
#             supplier_choices_dict = dict(form.supplier_id.choices)
#             if supplier_id_str and supplier_id_str in supplier_choices_dict:
#                 form.supplier_id.data = supplier_id_str
#                 logger.info(f"SUCCESS: Set supplier: {supplier_choices_dict[supplier_id_str]}")
            
#             # Set invoice
#             form.invoice_id.data = str(invoice_id)
#             logger.info(f"SUCCESS: Set invoice: {invoice.get('supplier_invoice_number', invoice_id)}")
            
#             # Set amount
#             form.amount.data = float(amount_to_pay) if amount_to_pay else 0.0
            
#             # Set branch
#             if invoice.get('branch_id'):
#                 branch_id_str = str(invoice.get('branch_id'))
#                 branch_choices_dict = dict(form.branch_id.choices)
#                 if branch_id_str in branch_choices_dict:
#                     form.branch_id.data = branch_id_str
#                     logger.info(f"SUCCESS: Set branch: {branch_choices_dict[branch_id_str]}")
            
#             # Set date and currency
#             from datetime import date
#             form.payment_date.data = date.today()
#             form.currency_code.data = invoice.get('currency_code', 'INR')
#             form.exchange_rate.data = float(invoice.get('exchange_rate', 1.0))
            
#             # Generate reference and notes
#             invoice_number = invoice.get('supplier_invoice_number', '')
#             form.reference_no.data = f"PAY-{invoice_number}-{date.today().strftime('%Y%m%d')}"
#             form.notes.data = f"Payment for invoice {invoice_number}"
            
#             # Set default payment method
#             form.payment_method.data = 'cash'
            
#             logger.info(f"FORM PRE-POPULATED SUCCESSFULLY")
        
#         # 🔧 ENHANCED FORM SUBMISSION WITH UUID CONVERSION
#         if form.validate_on_submit():
#             try:
#                 # 🔧 CRITICAL: Convert all UUID objects to strings
#                 supplier_id_str = str(invoice.get('supplier_id')) if invoice.get('supplier_id') else None
#                 invoice_id_str = str(invoice_id)
#                 branch_id_str = str(form.branch_id.data) if form.branch_id.data else str(invoice.get('branch_id'))
                
#                 # Validate required fields
#                 if not supplier_id_str:
#                     raise ValueError("Supplier ID is required")
#                 if not invoice_id_str:
#                     raise ValueError("Invoice ID is required")
#                 if not branch_id_str:
#                     raise ValueError("Branch ID is required")
                
#                 # Build payment data with string IDs
#                 payment_data = {
#                     'supplier_id': supplier_id_str,
#                     'invoice_id': invoice_id_str,
#                     'branch_id': branch_id_str,
#                     'payment_date': form.payment_date.data,
#                     'amount': float(form.amount.data),
#                     'currency_code': form.currency_code.data,
#                     'exchange_rate': float(form.exchange_rate.data),
#                     'reference_no': form.reference_no.data,
#                     'notes': form.notes.data,
#                     'payment_method': form.payment_method.data if form.payment_method.data else 'cash',
                    
#                     # Multi-method amounts
#                     'cash_amount': float(form.cash_amount.data or 0),
#                     'cheque_amount': float(form.cheque_amount.data or 0),
#                     'bank_transfer_amount': float(form.bank_transfer_amount.data or 0),
#                     'upi_amount': float(form.upi_amount.data or 0),
                    
#                     # Method-specific details (only if relevant amounts > 0)
#                     'cheque_number': form.cheque_number.data if (form.cheque_amount.data or 0) > 0 else None,
#                     'cheque_date': form.cheque_date.data if (form.cheque_amount.data or 0) > 0 else None,
#                     'cheque_bank': form.cheque_bank.data if (form.cheque_amount.data or 0) > 0 else None,
#                     'bank_reference_number': form.bank_reference_number.data if (form.bank_transfer_amount.data or 0) > 0 else None,
#                     'ifsc_code': form.ifsc_code.data if (form.bank_transfer_amount.data or 0) > 0 else None,
#                     'upi_transaction_id': form.upi_transaction_id.data if (form.upi_amount.data or 0) > 0 else None,
#                     'upi_app_name': form.upi_app_name.data if (form.upi_amount.data or 0) > 0 else None,
#                 }
                
#                 # Enhanced logging for debugging
#                 logger.info(f"PAYMENT DATA READY:")
#                 logger.info(f"  supplier_id: {type(payment_data['supplier_id'])} = {payment_data['supplier_id']}")
#                 logger.info(f"  invoice_id: {type(payment_data['invoice_id'])} = {payment_data['invoice_id']}")
#                 logger.info(f"  branch_id: {type(payment_data['branch_id'])} = {payment_data['branch_id']}")
#                 logger.info(f"  amount: {payment_data['amount']}")
#                 logger.info(f"  payment_method: {payment_data['payment_method']}")
                
#                 payment = record_supplier_payment(
#                     hospital_id=current_user.hospital_id,
#                     payment_data=payment_data,
#                     create_gl_entries=True,
#                     current_user_id=current_user.user_id
#                 )
                
#                 flash("Payment recorded successfully", "success")
#                 return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
                
#             except Exception as payment_error:
#                 current_app.logger.error(f"ERROR in payment submission: {str(payment_error)}", exc_info=True)
#                 flash(f"Error recording payment: {str(payment_error)}", "error")
#         else:
#             # Log form validation errors
#             if request.method == 'POST':
#                 current_app.logger.error(f"FORM VALIDATION ERRORS: {form.errors}")
#                 for field_name, errors in form.errors.items():
#                     for error in errors:
#                         flash(f"{field_name}: {error}", "error")
        
#         # Template data
#         supplier_name = invoice.get('supplier_name', 'Unknown Supplier')
#         invoice_number = invoice.get('supplier_invoice_number', 'N/A')
        
#         return render_template(
#             'supplier/payment_form.html',
#             form=form,
#             invoice=invoice,
#             title=f"Payment for Invoice {invoice_number}",
#             payment_config=PAYMENT_CONFIG,
#             supplier_name=supplier_name,
#             invoice_number=invoice_number
#         )
        
#     except Exception as e:
#         current_app.logger.error(f"ERROR in record_payment: {str(e)}", exc_info=True)
#         flash(f"Error recording payment: {str(e)}", "error")
#         return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))

@supplier_views_bp.route('/invoice/payment/<invoice_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_payment', 'add', branch_source='entity')
def record_payment(invoice_id):
    """Record payment for supplier invoice - FIXED CONTROLLER WITH INVOICE CONTEXT"""
    
    try:
        # Use enhanced controller with invoice context
        from app.controllers.supplier_controller import SupplierPaymentController
        
        # Create controller with invoice context
        controller = SupplierPaymentController(invoice_id=invoice_id)
        
        return controller.handle_request()
        
    except Exception as e:
        current_app.logger.error(f"Error in invoice payment controller: {str(e)}")
        flash(f"Error recording payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
        
    except Exception as e:
        current_app.logger.error(f"Error with payment controller: {str(e)}")
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
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))
        return render_template(
            'supplier/pending_invoices.html',
            invoices=invoices,
            supplier_id=supplier_id,
            branch_context=branch_context,  # NEW: Pass branch context to template
            menu_items=menu_items
        )
    except Exception as e:
        current_app.logger.error(f"Error in pending_invoices: {str(e)}", exc_info=True)
        flash(f"Error retrieving pending invoices: {str(e)}", "error")
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))
        return render_template(
            'supplier/pending_invoices.html', 
            invoices=[], 
            branch_context=branch_context,
            menu_items=menu_items
        )
    
# === PAYMENT MANAGEMENT ROUTES ===

@supplier_views_bp.route('/payment/record', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('payment', 'add')
def create_payment():
    """Record new supplier payment with multi-method support"""
    try:
        controller = SupplierPaymentController()
        return controller.handle_request()
    except Exception as e:
        current_app.logger.error(f"Error in record_payment: {str(e)}", exc_info=True)
        flash(f"Error recording payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_list'))


@supplier_views_bp.route('/payment/edit/<payment_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('payment', 'edit', branch_source='entity')
def edit_payment(payment_id):
    """Edit existing payment"""
    try:
        controller = SupplierPaymentController(payment_id=payment_id)
        return controller.handle_request()
    except Exception as e:
        current_app.logger.error(f"Error in edit_payment: {str(e)}", exc_info=True)
        flash(f"Error editing payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.payment_list'))


@supplier_views_bp.route('/payment/list', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view')
def payment_list():
    """List supplier payments with enhanced filtering and supplier dropdown"""
    try:
        from app.forms.supplier_forms import PaymentSearchForm
        
        # Get search form
        form = PaymentSearchForm()
        
        # Populate form choices
        try:
            from app.services.branch_service import populate_branch_choices_for_user
            from app.utils.form_helpers import populate_supplier_choices
            
            # Use existing branch service
            populate_branch_choices_for_user(
                form.branch_id, 
                current_user, 
                required=False,
                include_all_option=True
            )
            
            # Populate supplier choices
            populate_supplier_choices(form, current_user)
            
        except Exception as e:
            current_app.logger.warning(f"Error populating form choices: {str(e)}")
        
        # ===========================================
        # NEW: GET SUPPLIERS FOR DROPDOWN
        # ===========================================
        suppliers = []
        try:
            from app.services.supplier_service import search_suppliers
            
            # Get branch context
            branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
            
            # Get all suppliers for dropdown
            supplier_result = search_suppliers(
                hospital_id=current_user.hospital_id,
                branch_id=branch_uuid,
                current_user_id=current_user.user_id,
                page=1,
                per_page=1000  # Get all suppliers for dropdown
            )
            
            suppliers = supplier_result.get('suppliers', [])
            logger.info(f"Loaded {len(suppliers)} suppliers for dropdown")
            
        except Exception as e:
            current_app.logger.error(f"Error loading suppliers for dropdown: {str(e)}")
            suppliers = []
        
        # ===========================================
        # EXISTING FILTER LOGIC (keep as-is but enhance for dropdown)
        # ===========================================
        filters = {}
        
        # Enhanced supplier filtering - UPDATE to use supplier_id from dropdown
        supplier_id = request.args.get('supplier_id')  # NEW: from dropdown
        supplier_text = request.args.get('supplier')   # OLD: from text input (fallback)
        supplier_search = request.args.get('supplier_search')  # OLD: fallback

        if supplier_id and supplier_id.strip():
            # NEW: Use supplier_id from dropdown
            filters['supplier_id'] = supplier_id
            logger.info(f"Using supplier_id filter: {supplier_id}")
        elif supplier_search and supplier_search.strip():
            # OLD: Fallback to text search
            filters['supplier_name_search'] = supplier_search.strip()
        elif supplier_text and supplier_text.strip():
            # OLD: Fallback to text search
            filters['supplier_name_search'] = supplier_text.strip()

        # Enhanced payment method filtering - support multiple selections
        payment_methods = request.args.getlist('payment_method')
        payment_methods = [method.strip() for method in payment_methods if method.strip()]
        if payment_methods:
            filters['payment_methods'] = payment_methods  # Note: plural for multiple values
        
        # Enhanced status filtering - support multiple selections
        statuses = request.args.getlist('status')
        statuses = [status.strip() for status in statuses if status.strip()]
        if statuses:
            filters['statuses'] = statuses  # Note: plural for multiple values
        
        # Fallback to single value parameters for backward compatibility
        if not payment_methods:
            payment_method = request.args.get('payment_method')
            if payment_method and payment_method.strip():
                filters['payment_methods'] = [payment_method.strip()]
        
        if not statuses:
            status = request.args.get('status')
            workflow_status = request.args.get('workflow_status')
            
            if status and status.strip():
                filters['statuses'] = [status.strip()]
            elif workflow_status and workflow_status.strip():
                filters['statuses'] = [workflow_status.strip()]
        
        # Status filtering - support both parameter name formats
        workflow_status = request.args.get('workflow_status')
        status = request.args.get('status')
        
        if workflow_status and workflow_status.strip():
            filters['workflow_status'] = workflow_status
        elif status and status.strip():
            filters['workflow_status'] = status
        
        # Amount filtering - support both parameter name formats
        min_amount = request.args.get('min_amount')
        amount_min = request.args.get('amount_min')
        
        if min_amount and min_amount.strip():
            try:
                filters['min_amount'] = float(min_amount)
            except ValueError:
                pass
        elif amount_min and amount_min.strip():
            try:
                filters['min_amount'] = float(amount_min)
            except ValueError:
                pass
        
        # Other parameters (keep as-is)
        branch_id = request.args.get('branch_id')
        if branch_id and branch_id.strip():
            filters['branch_id'] = branch_id
        
        start_date = request.args.get('start_date')
        if start_date and start_date.strip():
            filters['start_date'] = start_date
        
        end_date = request.args.get('end_date')
        if end_date and end_date.strip():
            filters['end_date'] = end_date
        
        max_amount = request.args.get('max_amount')
        if max_amount and max_amount.strip():
            try:
                filters['max_amount'] = float(max_amount)
            except ValueError:
                pass
        
        # REMOVED: reference_no (since field is hidden)
        # reference_no = request.args.get('reference_no')
        # if reference_no and reference_no.strip():
        #     filters['reference_no'] = reference_no.strip()
        
        invoice_id = request.args.get('invoice_id')
        if invoice_id and invoice_id.strip():
            filters['invoice_id'] = invoice_id.strip()
        
        # Clean filters
        filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        logger.info(f"Export filters: {filters}")
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get branch context using existing helper
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
        
        # Search payments using service
        try:
            from app.services.universal_supplier_service import EnhancedUniversalSupplierService
            # ===========================================
            # ADD DEBUG LOGGING BEFORE SEARCH
            # ===========================================
            logger.info(f"🔍 PAYMENT LIST DEBUG: Starting search")
            logger.info(f"🔍 Hospital ID: {current_user.hospital_id}")
            logger.info(f"🔍 Filters: {filters}")
            logger.info(f"🔍 Branch UUID: {branch_uuid}")
            logger.info(f"🔍 User ID: {current_user.user_id}")
            enhanced_service = EnhancedUniversalSupplierService()
            result = enhanced_service._search_supplier_payments_universal(
                hospital_id=current_user.hospital_id,
                filters=filters,
                branch_id=branch_uuid,
                current_user_id=current_user.user_id,
                page=page,
                per_page=per_page
            )
            logger.info(f"🔍 SEARCH RESULT TYPE: {type(result)}")
            logger.info(f"🔍 SEARCH RESULT KEYS: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            
            payments = result.get('payments', [])
            total = result.get('pagination', {}).get('total_count', 0)
            
            # ✅ FIX: Use summary from search results instead of empty dict
            summary = result.get('summary', {})
            # ===========================================
            # ADD DEBUG LOGGING FOR SUMMARY
            # ===========================================
            logger.info(f"🔍 SUMMARY TYPE: {type(summary)}")
            logger.info(f"🔍 SUMMARY CONTENT: {summary}")
            logger.info(f"🔍 PAYMENTS COUNT: {len(payments)}")
            logger.info(f"🔍 TOTAL COUNT: {total}")
            
            # Log each summary field specifically
            if isinstance(summary, dict):
                logger.info(f"🔍 summary.total_count: {summary.get('total_count', 'MISSING')}")
                logger.info(f"🔍 summary.total_amount: {summary.get('total_amount', 'MISSING')}")
                logger.info(f"🔍 summary.pending_count: {summary.get('pending_count', 'MISSING')}")
                logger.info(f"🔍 summary.this_month_count: {summary.get('this_month_count', 'MISSING')}")
        except Exception as e:
            current_app.logger.error(f"Error searching payments: {str(e)}")
            payments = []
            total = 0
            summary = {}
        
        # NEW: Prepare active filters for template
        active_filters = {}
        for key, value in request.args.items():
            if key not in ['page', 'per_page'] and value and value.strip():
                active_filters[key] = value.strip()
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))

        return render_template(
            'supplier/payment_list.html',
            payments=payments,
            suppliers=suppliers,  # NEW: Add suppliers for dropdown
            form=form,
            page=page,
            per_page=per_page,
            total=total,
            summary=summary,
            branch_context=branch_context,
            filters=filters,
            payment_config=PAYMENT_CONFIG,
            # NEW: Pass filter state for form preservation
            active_filters=active_filters,
            request_args=request.args.to_dict(),
            menu_items=menu_items
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in payment_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving payments: {str(e)}", "error")
        # ✅ FIX: Provide default summary instead of empty dict
        default_summary = {
            'total_count': 0,
            'total_amount': 0.0,
            'pending_count': 0,
            'this_month_count': 0
        }
        menu_items = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff'))
        return render_template('supplier/payment_list.html', 
            payments=[], 
            suppliers=[],  # NEW: Empty suppliers list on error
            total=0, 
            filters={},
            summary=default_summary,  # ✅ Use default instead of empty 
            payment_config=PAYMENT_CONFIG,
            menu_items=menu_items)


@supplier_views_bp.route('/payment/view/<payment_id>', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view', branch_source='entity')
def view_payment(payment_id):
    """View payment details with documents, approval history, and credit notes"""
    try:
        from app.services.supplier_service import get_supplier_payment_by_id
        
        payment = get_supplier_payment_by_id(
            payment_id=uuid.UUID(payment_id),
            hospital_id=current_user.hospital_id,
            include_documents=True,
            include_approvals=True
        )
        
        if not payment:
            flash("Payment not found", "error")
            return redirect(url_for('supplier_views.payment_list'))

        # ✅ ADD THIS ENHANCEMENT FOR CREDIT NOTES:
        try:
            from app.controllers.supplier_controller import enhance_payment_view_with_credits
            
            # Get enhanced payment data with credit note information
            enhanced_payment = enhance_payment_view_with_credits(
                payment_id=payment_id,
                current_user_id=current_user.user_id,
                hospital_id=current_user.hospital_id
            )
            
            if enhanced_payment:
                # Use enhanced payment data that includes credit note context
                payment.update({
                    'can_create_credit_note': enhanced_payment.get('can_create_credit_note', False),
                    'existing_credit_notes': enhanced_payment.get('existing_credit_notes', []),
                    'net_payment_amount': enhanced_payment.get('net_payment_amount', payment.get('amount', 0)),
                    'total_credited': enhanced_payment.get('total_credited', 0),
                    'create_credit_note_url': enhanced_payment.get('create_credit_note_url')
                })
        except Exception as e:
            current_app.logger.warning(f"Could not load credit note data: {str(e)}")
            # Continue with normal payment view if credit note enhancement fails
            payment.update({
                'can_create_credit_note': False,
                'existing_credit_notes': [],
                'net_payment_amount': payment.get('amount', 0),
                'total_credited': 0
            })
        
        # Get payment summary
        summary = {
            'total_amount': float(payment.get('amount', 0)),
            'method_breakdown': {
                'cash': float(payment.get('cash_amount', 0)),
                'cheque': float(payment.get('cheque_amount', 0)),
                'bank_transfer': float(payment.get('bank_transfer_amount', 0)),
                'upi': float(payment.get('upi_amount', 0))
            },
            'document_summary': payment.get('document_summary', {}),
            'approval_required': payment.get('requires_approval', False),
            'approval_status': payment.get('workflow_status', 'unknown')
        }
        
        documents = payment.get('documents', [])
        if not documents:
            # Try to fetch documents separately if not included
            try:
                from app.services.supplier_service import get_payment_documents
                documents = get_payment_documents(uuid.UUID(payment_id), current_user.hospital_id)
            except Exception as doc_error:
                current_app.logger.warning(f"Could not fetch payment documents: {str(doc_error)}")
                documents = []
        
        return render_template(
            'supplier/payment_view.html',
            payment=payment,
            summary=summary,
            title=f'Payment {payment.get("reference_no", payment_id[:8])}',
            can_approve=_can_user_approve_payment(payment, current_user),
            payment_config=PAYMENT_CONFIG,
            documents=documents
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in view_payment: {str(e)}", exc_info=True)
        flash(f"Error retrieving payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.payment_list'))

@supplier_views_bp.route('/payment/document/download/<payment_id>/<document_id>')
@login_required
@require_web_branch_permission('payment_document', 'view', branch_source='entity')
def download_payment_document(payment_id, document_id):
    """Download payment document - FIXED VERSION"""
    try:
        from app.services.supplier_service import get_payment_document
        from flask import Response
        
        # Get the document using CORRECT function signature
        document_data = get_payment_document(
            payment_id=uuid.UUID(payment_id),
            document_id=uuid.UUID(document_id),
            hospital_id=current_user.hospital_id
        )
        
        if not document_data:
            flash("Document not found", "error")
            return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))
        
        # Check if file content is available
        if not document_data.get('content'):
            flash("Document file not found on disk", "error")
            return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))
        
        # FIX: Use original_filename instead of filename
        filename = document_data.get('original_filename', 'document')
        if not filename:
            filename = document_data.get('stored_filename', 'document')
        
        # Return file response
        response = Response(
            document_data.get('content'),
            mimetype=document_data.get('mime_type', 'application/octet-stream'),
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
        
        # Log document access
        try:
            from app.services.supplier_service import log_document_access
            log_document_access(
                document_id=uuid.UUID(document_id),
                user_id=current_user.user_id,
                access_type='download',
                hospital_id=current_user.hospital_id
            )
        except Exception as log_error:
            current_app.logger.warning(f"Could not log document access: {str(log_error)}")
        
        return response
        
    except Exception as e:
        current_app.logger.error(f"Error downloading payment document: {str(e)}")
        flash("Error downloading document", "error")
        return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))


@supplier_views_bp.route('/payment/approve/<payment_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('payment', 'approve', branch_source='entity')
def approve_payment(payment_id):
    """Approve or reject pending payment"""
    try:
        controller = PaymentApprovalController(payment_id)
        return controller.handle_approval()
    except Exception as e:
        current_app.logger.error(f"Error in approve_payment: {str(e)}", exc_info=True)
        flash(f"Error processing approval: {str(e)}", "error")
        return redirect(url_for('supplier_views.payment_list'))

@supplier_views_bp.route('/payment/export', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view')
def export_payments():
    """Export supplier payments to CSV/Excel"""
    try:
        # Get filter parameters from request
        filters = {
            'supplier_id': request.args.get('supplier_id'),
            'branch_id': request.args.get('branch_id'),
            'workflow_status': request.args.get('workflow_status'),
            'payment_method': request.args.get('payment_method'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'min_amount': request.args.get('min_amount'),
            'max_amount': request.args.get('max_amount')
        }
        
        # Get branch context
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
        
        try:
            from app.services.supplier_service import export_supplier_payments
            
            # Export payments
            export_data = export_supplier_payments(
                hospital_id=current_user.hospital_id,
                filters=filters,
                format='csv',
                branch_id=branch_uuid,
                current_user_id=current_user.user_id
            )
            
            # Return CSV response
            from flask import Response
            
            response = Response(
                export_data,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=supplier_payments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
            
            return response
            
        except Exception as e:
            current_app.logger.error(f"Error exporting payments: {str(e)}")
            flash(f"Error exporting payments: {str(e)}", "error")
            return redirect(url_for('supplier_views.payment_list'))
            
    except Exception as e:
        current_app.logger.error(f"Error in export_payments: {str(e)}", exc_info=True)
        flash("Error exporting payments", "error")
        return redirect(url_for('supplier_views.payment_list'))


# === DOCUMENT MANAGEMENT ROUTES ===

@supplier_views_bp.route('/payment/document/upload', methods=['POST'])
@login_required
@require_web_branch_permission('payment_document', 'add')
def upload_payment_document():
    """Upload document for payment"""
    try:
        from app.forms.supplier_forms import DocumentUploadForm
        form = DocumentUploadForm()
        
        if form.validate_on_submit():
            payment_id = request.form.get('payment_id')
            if not payment_id:
                return jsonify({'success': False, 'error': 'Payment ID required'}), 400
            
            # Process document upload (will need to be implemented in supplier_service.py)
            from app.services.supplier_service import add_payment_document
            
            result = add_payment_document(
                payment_id=uuid.UUID(payment_id),
                document_data={
                    'file': form.file.data,
                    'document_type': form.document_type.data,
                    'description': form.description.data,
                    'required_for_approval': form.required_for_approval.data
                },
                current_user_id=current_user.user_id
            )
            
            return jsonify({
                'success': True,
                'document_id': str(result.get('document_id')),
                'message': 'Document uploaded successfully'
            })
        else:
            return jsonify({
                'success': False,
                'errors': form.errors
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error uploading document: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@supplier_views_bp.route('/payment/document/view/<document_id>')
@login_required
@require_web_branch_permission('payment_document', 'view', branch_source='entity')
def view_payment_document(document_id):
    """View/download payment document"""
    try:
        from app.services.supplier_service import get_payment_document, log_document_access
        
        # Get document details
        document = get_payment_document(
            document_id=uuid.UUID(document_id),
            hospital_id=current_user.hospital_id
        )
        
        if not document:
            flash("Document not found", "error")
            return redirect(url_for('supplier_views.payment_list'))
        
        # Log access
        log_document_access(
            document_id=uuid.UUID(document_id),
            user_id=current_user.user_id,
            access_type='view'
        )
        
        # Serve file
        from flask import send_file
        return send_file(
            document['file_path'],
            as_attachment=False,
            download_name=document['original_filename']
        )
        
    except Exception as e:
        current_app.logger.error(f"Error viewing document: {str(e)}")
        flash(f"Error accessing document: {str(e)}", "error")
        return redirect(url_for('supplier_views.payment_list'))


# Payment related helper functions
def _can_user_approve_payment(payment, user):
    """Check if user can approve the given payment"""
    try:
        from app.services.permission_service import has_permission
        
        # Check basic approval permission
        user_obj = {'user_id': user.user_id}
        if not has_permission(user_obj, 'payment', 'approve'):
            return False
        
        # Check amount-based approval levels
        amount = float(payment.get('amount', 0))
        approval_level = payment.get('approval_level', 'level_1')
        
        if approval_level == 'level_2' and amount >= PAYMENT_CONFIG.get('APPROVAL_THRESHOLD_L2', 200000):
            return has_permission(user_obj, 'payment', 'approve_high_value')
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error checking approval permission: {str(e)}")
        return False


def _get_payment_summary_stats(payments):
    """Get summary statistics for payment list"""
    try:
        stats = {
            'total_count': len(payments),
            'total_amount': sum(float(p.get('amount', 0)) for p in payments),
            'pending_approval_count': len([p for p in payments if p.get('workflow_status') == 'pending_approval']),
            'approved_count': len([p for p in payments if p.get('workflow_status') == 'approved']),
            'by_method': {
                'cash': sum(float(p.get('cash_amount', 0)) for p in payments),
                'cheque': sum(float(p.get('cheque_amount', 0)) for p in payments),
                'bank_transfer': sum(float(p.get('bank_transfer_amount', 0)) for p in payments),
                'upi': sum(float(p.get('upi_amount', 0)) for p in payments)
            }
        }
        return stats
    except Exception as e:
        current_app.logger.error(f"Error calculating payment stats: {str(e)}")
        return {'total_count': 0, 'total_amount': 0}


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
@require_web_branch_permission('medicine', 'view')
def search_medicines_api():
    """API endpoint to search medicines with branch awareness"""
    try:
        term = request.args.get('term', '')
        
        if len(term) < 2:
            return jsonify({'medicines': []})
        
        branch_uuid, branch_context = get_branch_uuid_from_context_or_request()
        
        with get_db_session(read_only=True) as session:
            query = session.query(Medicine).filter(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.medicine_name.ilike(f'%{term}%')
            )
            
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
                    # UPDATED: Use new MRP field instead of cost_price
                    'mrp': float(medicine.mrp or 0),  # <-- NEW MRP FIELD
                    'purchase_price': float(medicine.last_purchase_price or medicine.cost_price or 0),  # <-- BETTER FIELD
                    'selling_price': float(medicine.selling_price or medicine.mrp or 0),  # <-- NEW
                    'currency_code': medicine.currency_code or 'INR',  # <-- NEW
                    'branch_id': str(medicine.branch_id) if hasattr(medicine, 'branch_id') and medicine.branch_id else None
                })
            
            return jsonify({'medicines': results})
    
    except Exception as e:
        current_app.logger.error(f"Error searching medicines: {str(e)}")
        return jsonify({'error': str(e)}), 500


@supplier_views_bp.route('/api/medicines/<medicine_id>', methods=['GET'])
@login_required
@require_web_branch_permission('medicine', 'view', branch_source='entity')
def get_medicine_api(medicine_id):
    """API endpoint to get medicine details by ID"""
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
                
                # UPDATED: Use new price fields properly
                medicine_dict['mrp'] = float(medicine.mrp) if medicine.mrp else 0.0  # <-- NEW MRP FIELD
                medicine_dict['selling_price'] = float(medicine.selling_price) if medicine.selling_price else float(medicine.mrp or 0)  # <-- NEW
                medicine_dict['purchase_price'] = float(medicine.last_purchase_price or medicine.cost_price or 0)  # <-- BETTER
                medicine_dict['last_purchase_price'] = float(medicine.last_purchase_price or 0)  # <-- NEW
                medicine_dict['cost_price'] = float(medicine.cost_price or 0)
                medicine_dict['currency_code'] = medicine.currency_code or 'INR'  # <-- NEW
                medicine_dict['mrp_effective_date'] = medicine.mrp_effective_date.isoformat() if medicine.mrp_effective_date else None  # <-- NEW
                
                # Add formatted prices using medicine service
                from app.services.medicine_service import MedicineService
                medicine_dict['formatted_mrp'] = MedicineService.format_medicine_price(medicine, 'mrp')  # <-- NEW
                medicine_dict['formatted_selling_price'] = MedicineService.format_medicine_price(medicine, 'selling_price')  # <-- NEW
                
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
                    'currency_code': 'INR',  # <-- NEW
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
        
        line_items = []
        if 'line_items' in po:
            for line in po['line_items']:
                line_items.append({
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
            'success': True,  # ← Add success flag
            'line_items': line_items,  # ← Correct key name
            'po_number': po.get('po_number'),
            'po_branch_id': str(po.get('branch_id')) if po.get('branch_id') else None
        })
    
    except Exception as e:
        current_app.logger.error(f"Error getting PO items: {str(e)}")
        return jsonify({'error': str(e)}), 500
    

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
@require_web_branch_permission('supplier_invoice', 'view')
def load_po_items(po_id):
    """
    THIN API ENDPOINT: Load items from a purchase order for an invoice
    
    This endpoint delegates to the controller's business logic method.
    Following Universal Engine architecture: Views route, Controllers orchestrate.
    
    Returns:
        JSON response with PO items (balance quantities) and GST fields
    """
    from flask import jsonify, current_app
    from app.controllers.supplier_controller import SupplierInvoiceFormController
    
    try:
        current_app.logger.info(f"API: load-po-items for PO {po_id}")
        
        # Create controller instance and delegate to business logic
        controller = SupplierInvoiceFormController(po_id=po_id)
        result = controller.get_po_items_with_balance(
            po_id=po_id,
            include_gst_fields=True
        )
        
        if result.get('success'):
            return jsonify(result)
        else:
            error_msg = result.get('error', 'Unknown error')
            current_app.logger.error(f"Controller error: {error_msg}")
            return jsonify(result), 500
    
    except Exception as e:
        current_app.logger.error(f"API endpoint error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@supplier_views_bp.route('/invoice/cancel/<invoice_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'delete', branch_source='entity')
def cancel_supplier_invoice(invoice_id):
    """Enhanced cancellation with payment validation"""
    
    from app.forms.supplier_forms import SupplierInvoiceCancelForm
    from app.services.supplier_service import get_supplier_invoice_by_id, cancel_supplier_invoice as service_cancel_invoice
    
    return_to = request.args.get('return_to', 'list')
    
    if request.method == 'GET':
        form = SupplierInvoiceCancelForm()
        invoice = get_supplier_invoice_by_id(
            invoice_id=uuid.UUID(invoice_id),
            hospital_id=current_user.hospital_id
        )
        if not invoice:
            flash("Invoice not found", "error")
            return redirect(url_for('supplier_views.supplier_invoice_list'))
        
        # ✅ NEW: Pre-check for payment status
        if invoice.get('payment_status') in ['paid', 'partial']:
            flash(f"Cannot cancel {invoice.get('payment_status')} invoice {invoice.get('supplier_invoice_number')}. Credit note process required.", "error")
            if return_to == 'view':
                return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
            else:
                return redirect(url_for('supplier_views.supplier_invoice_list'))
            
        return render_template(
            'supplier/cancel_invoice.html',
            form=form,
            invoice=invoice,
            return_to=return_to
        )
    
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
                
                flash(f"Invoice {result.get('supplier_invoice_number', '')} has been successfully cancelled", "success")
                
                if return_to == 'view':
                    return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice_id))
                else:
                    return redirect(url_for('supplier_views.supplier_invoice_list'))
                
            except ValueError as ve:
                # ✅ Enhanced error messaging
                error_msg = str(ve)
                if "fully paid" in error_msg:
                    flash(f"❌ {error_msg}", "error")
                    flash("💡 Solution: Contact your manager to initiate credit note process for paid invoices.", "info")
                elif "partially paid" in error_msg:
                    flash(f"❌ {error_msg}", "error") 
                    flash("💡 Solution: Contact your manager to reverse payments or create credit note.", "info")
                else:
                    flash(f"Cannot cancel invoice: {error_msg}", "error")
                    
            except Exception as e:
                current_app.logger.error(f"Unexpected error cancelling invoice {invoice_id}: {str(e)}", exc_info=True)
                flash(f"System error while cancelling invoice. Please try again.", "error")
        else:
            flash("Please provide a cancellation reason", "error")
        
        # Show form again with errors
        invoice = get_supplier_invoice_by_id(
            invoice_id=uuid.UUID(invoice_id),
            hospital_id=current_user.hospital_id
        )
        
        return render_template(
            'supplier/cancel_invoice.html',
            form=form,
            invoice=invoice,
            return_to=return_to
        )
    

    
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
    

@supplier_views_bp.route('/api/payment/quick-info/<payment_id>', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view', branch_source='entity')
def get_payment_quick_info(payment_id):
    """Get quick payment information for AJAX calls"""
    try:
        from app.services.supplier_service import get_supplier_payment_by_id
        
        payment = get_supplier_payment_by_id(
            payment_id=uuid.UUID(payment_id),
            hospital_id=current_user.hospital_id
        )
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        quick_info = {
            'payment_id': str(payment.get('payment_id')),
            'amount': float(payment.get('amount', 0)),
            'supplier_name': payment.get('supplier_name', ''),
            'payment_date': payment.get('payment_date').isoformat() if payment.get('payment_date') else None,
            'status': payment.get('workflow_status', 'unknown'),
            'requires_approval': payment.get('requires_approval', False),
            'method_breakdown': {
                'cash': float(payment.get('cash_amount', 0)),
                'cheque': float(payment.get('cheque_amount', 0)),
                'bank_transfer': float(payment.get('bank_transfer_amount', 0)),
                'upi': float(payment.get('upi_amount', 0))
            }
        }
        
        return jsonify({'success': True, 'payment': quick_info})
        
    except Exception as e:
        current_app.logger.error(f"Error getting payment quick info: {str(e)}")
        return jsonify({'error': str(e)}), 500


@supplier_views_bp.route('/api/payment/validate-amount', methods=['POST'])
@login_required
def validate_payment_amount():
    """Validate payment amount and method distribution"""
    try:
        data = request.json
        
        total_amount = float(data.get('total_amount', 0))
        method_amounts = {
            'cash': float(data.get('cash_amount', 0)),
            'cheque': float(data.get('cheque_amount', 0)),
            'bank_transfer': float(data.get('bank_transfer_amount', 0)),
            'upi': float(data.get('upi_amount', 0))
        }
        
        method_total = sum(method_amounts.values())
        
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'requires_approval': False
        }
        
        # Check amount distribution
        if method_total > 0:
            if abs(total_amount - method_total) > 0.01:
                validation['valid'] = False
                validation['errors'].append(f'Method total ({method_total}) does not match total amount ({total_amount})')
        
        # Check approval requirements
        if total_amount >= PAYMENT_CONFIG.get('APPROVAL_THRESHOLD_L1', 50000):
            validation['requires_approval'] = True
            validation['warnings'].append('This payment will require approval')
        
        # Check if above auto-approve limit
        if total_amount <= PAYMENT_CONFIG.get('AUTO_APPROVE_LIMIT', 5000):
            validation['warnings'].append('This payment will be auto-approved')
        
        return jsonify(validation)
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [f'Validation error: {str(e)}']
        }), 400


@supplier_views_bp.route('/api/payment/invoice-choices/<supplier_id>', methods=['GET'])
@login_required
@require_web_branch_permission('payment', 'view')
def get_invoice_choices_for_supplier(supplier_id):
    """Get invoice choices for a specific supplier (ENHANCED with balance info)"""
    try:
        from app.services.database_service import get_db_session
        from app.models.transaction import SupplierInvoice
        
        with get_db_session(read_only=True) as session:
            # Get unpaid/partially paid invoices for supplier
            invoices = session.query(SupplierInvoice).filter_by(
                hospital_id=current_user.hospital_id,
                supplier_id=uuid.UUID(supplier_id)
            ).filter(
                SupplierInvoice.payment_status.in_(['unpaid', 'partial'])
            ).order_by(SupplierInvoice.invoice_date.desc()).all()
            
            # Build choices with balance information
            choices = [{'value': '', 'text': 'Select Invoice (Optional)'}]
            
            for invoice in invoices:
                balance_due = float(invoice.total_amount or 0) - float(invoice.payment_total or 0)
                invoice_display = f"{invoice.supplier_invoice_number} -  Rs.{balance_due:.2f} (Due: {invoice.invoice_date})"
                choices.append({
                    'value': str(invoice.invoice_id),
                    'text': invoice_display,
                    'balance': balance_due,
                    'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None
                })
        
        return jsonify({
            'success': True,
            'choices': choices
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting invoice choices: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@supplier_views_bp.route('/invoice/<original_invoice_id>/credit-note', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'credit_note', branch_source='entity')
def create_invoice_credit_note(original_invoice_id):  # ← RENAMED FUNCTION
    """Create credit note for paid invoice"""
    
    if request.method == 'POST':
        try:
            credit_note_data = {
                'supplier_invoice_number': request.form.get('credit_note_number'),
                'invoice_date': request.form.get('credit_note_date'),
                'notes': request.form.get('credit_note_reason')
            }
            
            requires_approval = POSTING_CONFIG.get('REQUIRE_APPROVAL_FOR_CREDIT_NOTES', True)
            
            result = create_credit_note_for_paid_invoice(
                original_invoice_id=uuid.UUID(original_invoice_id),
                credit_note_data=credit_note_data,
                current_user_id=current_user.user_id,
                requires_approval=requires_approval
            )
            
            flash(f"Credit note {result['supplier_invoice_number']} created successfully", 'success')
            if requires_approval:
                flash('Credit note sent for approval', 'info')
            
            return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=result['invoice_id']))
            
        except Exception as e:
            flash(f'Error creating credit note: {str(e)}', 'error')
    
    # GET request - show form (you can create a simple template)
    return render_template('supplier/credit_note_create.html', 
                         original_invoice_id=original_invoice_id)

# ===============================================================================
# TESTING AND DEBUGGING ROUTES
# ===============================================================================

@supplier_views_bp.route('/test/payment-status/<payment_id>', methods=['GET'])
@login_required
def test_payment_status(payment_id):
    """Check payment status and related GL entries"""
    try:
        logger.info(f"🧪 STATUS TEST: Checking payment status for {payment_id}")
        
        payment_info = {}
        gl_entries = []
        gl_transactions = []
        
        with get_db_session(read_only=True) as session:
            # Get payment details
            payment = session.query(SupplierPayment).filter_by(
                payment_id=uuid.UUID(payment_id),
                hospital_id=current_user.hospital_id
            ).first()
            
            if payment:
                payment_info = {
                    'payment_id': str(payment.payment_id),
                    'amount': float(payment.amount),
                    'payment_method': payment.payment_method,
                    'workflow_status': payment.workflow_status,
                    'created_at': payment.created_at.isoformat() if payment.created_at else None,
                    'gl_posted': getattr(payment, 'gl_posted', None),
                    'posting_reference': getattr(payment, 'posting_reference', None)
                }
            
            # Get GL entries
            from app.models.transaction import GLEntry, GLTransaction
            
            entries = session.query(GLEntry).filter_by(
                source_document_id=uuid.UUID(payment_id)
            ).all()
            
            for entry in entries:
                gl_entries.append({
                    'entry_id': str(entry.entry_id),
                    'account_id': str(entry.account_id),
                    'debit_amount': float(entry.debit_amount or 0),
                    'credit_amount': float(entry.credit_amount or 0),
                    'description': entry.description,
                    'source_document_type': entry.source_document_type,
                    'posting_reference': entry.posting_reference
                })
            
            # Get GL transactions
            transactions = session.query(GLTransaction).filter_by(
                source_document_id=uuid.UUID(payment_id)
            ).all()
            
            for transaction in transactions:
                gl_transactions.append({
                    'transaction_id': str(transaction.transaction_id),
                    'transaction_type': transaction.transaction_type,
                    'total_debit': float(transaction.total_debit or 0),
                    'total_credit': float(transaction.total_credit or 0),
                    'reference_id': transaction.reference_id
                })
        
        return jsonify({
            'status': 'success',
            'payment_id': payment_id,
            'payment_info': payment_info,
            'gl_entries_count': len(gl_entries),
            'gl_entries': gl_entries,
            'gl_transactions_count': len(gl_transactions),
            'gl_transactions': gl_transactions
        })
        
    except Exception as e:
        current_app.logger.error(f"🧪 STATUS TEST: Error: {str(e)}", exc_info=True)
        import traceback
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
    

@supplier_views_bp.route('/payment/<payment_id>/credit-note', methods=['GET', 'POST'])
@login_required
def create_credit_note(payment_id):
    """
    Phase 1: Create credit note from supplier payment
    Following your existing route patterns
    UPDATED: Uses centralized creditnote_service
    """
    try:
        # Check if credit note feature is enabled
        from app.utils.credit_note_utils import is_credit_note_enabled, get_credit_note_permission
        if not is_credit_note_enabled():
            flash('Credit note functionality is not enabled', 'warning')
            return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))
        
        # Check basic permissions using your permission service
        from app.services.permission_service import has_permission
        
        required_permission = get_credit_note_permission('CREATE')
        if not has_permission(current_user, 'supplier', 'edit'):
            flash('You do not have permission to create credit notes', 'error')
            return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))
        
        # Validate payment exists and user has access (your existing pattern)
        # UPDATED: Import from creditnote_service
        from app.services.credit_note_service import get_supplier_payment_by_id_with_credits
        
        payment = get_supplier_payment_by_id_with_credits(
            payment_id=uuid.UUID(payment_id),
            hospital_id=current_user.hospital_id,
            current_user_id=current_user.user_id
        )
        
        if not payment:
            flash('Payment not found', 'error')
            return redirect(url_for('supplier_views.payment_list'))
        
        # Check if user can access this payment's branch (your existing pattern)
        from app.services.permission_service import has_branch_permission
        if payment.get('branch_id') and not has_branch_permission(
            current_user, 'supplier', 'edit', str(payment['branch_id'])
        ):
            flash('Access denied: You do not have permission for this branch', 'error')
            return redirect(url_for('supplier_views.payment_list'))
        
        # Use credit note controller (following your controller delegation pattern)
        from app.controllers.supplier_controller import SimpleCreditNoteController
        
        controller = SimpleCreditNoteController(payment_id)
        return controller.handle_request()
        
    except ValueError as ve:
        current_app.logger.warning(f"Validation error creating credit note: {str(ve)}")
        flash(f"Error: {str(ve)}", 'error')
        return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))
    except Exception as e:
        current_app.logger.error(f"Error creating credit note for payment {payment_id}: {str(e)}")
        flash(f"Error creating credit note: {str(e)}", 'error')
        return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))

# SIMPLE HELPER ROUTE: Check if credit note can be created (AJAX endpoint)
@supplier_views_bp.route('/payment/<payment_id>/can-create-credit-note')
@login_required
def can_create_credit_note(payment_id):
    """
    Simple AJAX endpoint to check if credit note can be created
    Returns JSON response for dynamic UI updates - following your AJAX patterns
    UPDATED: Uses centralized creditnote_service
    """
    try:
        from flask import jsonify
        from app.controllers.supplier_controller import can_user_create_credit_note
        
        can_create = can_user_create_credit_note(current_user, payment_id)
        
        # Get payment details if credit note can be created
        if can_create:
            # UPDATED: Import from creditnote_service
            from app.services.credit_note_service import get_supplier_payment_by_id_with_credits
            payment = get_supplier_payment_by_id_with_credits(
                payment_id=uuid.UUID(payment_id),
                hospital_id=current_user.hospital_id,
                current_user_id=current_user.user_id
            )
            
            return jsonify({
                'can_create': True,
                'available_amount': payment.get('net_payment_amount', 0) if payment else 0,
                'create_url': url_for('supplier_views.create_credit_note', payment_id=payment_id)
            })
        else:
            return jsonify({
                'can_create': False,
                'reason': 'Credit note cannot be created for this payment'
            })
            
    except Exception as e:
        current_app.logger.error(f"Error checking credit note availability: {str(e)}")
        return jsonify({
            'can_create': False,
            'reason': 'Error checking credit note availability'
        }), 500

# ENHANCED: Credit note list route using centralized service
@supplier_views_bp.route('/credit-notes')
@login_required
def credit_note_list():
    """
    Phase 1: Credit notes list with support for both types
    Enhanced to show both invoice reversal and payment adjustment credit notes
    UPDATED: Uses centralized creditnote_service
    """
    try:
        from app.utils.credit_note_utils import is_credit_note_enabled, get_credit_note_permission
        from app.services.permission_service import has_permission
        
        # Check if feature is enabled
        if not is_credit_note_enabled():
            flash('Credit note functionality is not enabled', 'warning')
            return redirect(url_for('supplier_views.payment_list'))
        
        # Check permissions
        view_permission = get_credit_note_permission('VIEW')
        if not has_permission(current_user, view_permission):
            flash('You do not have permission to view credit notes', 'error')
            return redirect(url_for('supplier_views.payment_list'))
        
        # UPDATED: Import from creditnote_service
        from app.services.credit_note_service import get_credit_notes_list, get_credit_note_summary
        
        # Get credit notes using centralized service
        credit_notes = get_credit_notes_list(
            hospital_id=current_user.hospital_id,
            credit_note_type='all',  # Show both types
            limit=50,
            current_user_id=current_user.user_id
        )
        
        # Get summary statistics
        summary = get_credit_note_summary(
            hospital_id=current_user.hospital_id,
            current_user_id=current_user.user_id
        )
        
        # Get menu items for navigation (following your menu pattern)
        from app.utils.menu_utils import get_menu_items
        
        context = {
            'credit_notes': credit_notes,
            'total_count': summary.get('total_credit_notes', 0),
            'total_amount': summary.get('total_credit_amount', 0),
            'invoice_reversal_count': summary.get('invoice_reversal_count', 0),
            'payment_adjustment_count': summary.get('payment_adjustment_count', 0),
            'menu_items': get_menu_items(current_user)
        }
        
        return render_template('supplier/credit_note_list_enhanced.html', **context)
        
    except Exception as e:
        current_app.logger.error(f"Error loading credit notes list: {str(e)}")
        flash(f"Error loading credit notes: {str(e)}", 'error')
        return redirect(url_for('supplier_views.payment_list'))

@supplier_views_bp.route('/api/medicine/<medicine_id>/gst-info', methods=['GET'])
@login_required
def get_medicine_gst_info(medicine_id):
    """Get GST info for a medicine"""
    try:
        from app.models.master import Medicine
        from app.services.database_service import get_db_session
        from flask_login import current_user
        import uuid
        
        medicine_uuid = uuid.UUID(medicine_id)
        
        with get_db_session(read_only=True) as session:
            medicine = session.query(Medicine).filter_by(
                medicine_id=medicine_uuid,
                hospital_id=current_user.hospital_id
            ).first()
            
            if medicine:
                return jsonify({
                    'success': True,
                    'gst_rate': float(medicine.gst_rate) if medicine.gst_rate else 12.0,
                    'hsn_code': str(medicine.hsn_code) if medicine.hsn_code else '30049099',
                    'mrp': float(medicine.mrp or 0),  # ✅ ADDED
                    'last_purchase_price': float(medicine.last_purchase_price or 0)  # ✅ ADDED
                })
            
        return jsonify({'success': False, 'gst_rate': 12.0, 'hsn_code': '30049099'})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching medicine GST: {str(e)}")
        return jsonify({'success': False, 'gst_rate': 12.0, 'hsn_code': '30049099'})


@supplier_views_bp.route('/payment/approve_universal/<payment_id>', methods=['POST'])
@login_required
@require_web_branch_permission('payment', 'approve', branch_source='entity')
def approve_payment_universal(payment_id):
    """Approve payment - universal engine version"""
    # Use existing approve_supplier_payment service
    # Redirect to universal_views.universal_detail_view

@supplier_views_bp.route('/payment/reject_universal/<payment_id>', methods=['POST'])  
@login_required
@require_web_branch_permission('payment', 'approve', branch_source='entity')
def reject_payment_universal(payment_id):
    """Reject payment - universal engine version"""
    # Use existing reject_supplier_payment service
    # Redirect to universal_views.universal_detail_view

@supplier_views_bp.route('/payment/reject/<payment_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('payment', 'approve', branch_source='entity')
def reject_payment(payment_id):
    """Reject payment"""
    try:
        controller = PaymentApprovalController(payment_id=payment_id, action='reject')
        return controller.handle_request()
    except Exception as e:
        current_app.logger.error(f"Error in reject_payment: {str(e)}", exc_info=True)
        flash(f"Error rejecting payment: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_payment', payment_id=payment_id))


@supplier_views_bp.route('/payment/universal_test')
@login_required
@require_web_branch_permission('payment', 'view')
def payment_list_universal_test():
    """Test universal engine payment list"""
    return redirect(url_for('universal_views.universal_list_view', 
                           entity_type='supplier_payments'))


# ===================================================================
# API ENDPOINTS FOR MRP AND PRICE MANAGEMENT
# ===================================================================

@supplier_views_bp.route('/api/supplier/<supplier_id>/medicine/<medicine_id>/last-price', methods=['GET'])
@login_required
@require_web_branch_permission('medicine', 'view')
def api_get_last_purchase_price(supplier_id, medicine_id):
    """
    Get last purchase price for a medicine from a specific supplier
    Used in PO creation for price hints
    """
    try:
        from app.services.supplier_service import get_supplier_last_purchase_price
        
        price_info = get_supplier_last_purchase_price(
            session=get_db_session(),
            hospital_id=current_user.hospital_id,
            supplier_id=uuid.UUID(supplier_id),
            medicine_id=uuid.UUID(medicine_id)
        )
        
        if price_info:
            return jsonify(price_info), 200
        else:
            return jsonify({
                'message': 'No price history found',
                'supplier_id': supplier_id,
                'medicine_id': medicine_id
            }), 404
            
    except ValueError as e:
        current_app.logger.error(f"Invalid UUID format: {str(e)}")
        return jsonify({'error': 'Invalid ID format'}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching last price: {str(e)}")
        return jsonify({'error': 'Failed to fetch price history'}), 500


@supplier_views_bp.route('/api/supplier/<supplier_id>/metrics', methods=['GET'])
@login_required
@require_web_branch_permission('supplier', 'view')
def api_get_supplier_metrics(supplier_id):
    """
    Get supplier metrics including average discount and price trends
    """
    try:
        from app.services.supplier_service import get_supplier_average_metrics
        
        medicine_id = request.args.get('medicine_id')
        months = request.args.get('months', 6, type=int)
        
        if months < 1 or months > 24:
            return jsonify({'error': 'Months must be between 1 and 24'}), 400
        
        with get_db_session() as session:
            metrics = get_supplier_average_metrics(
                session=session,
                hospital_id=current_user.hospital_id,
                supplier_id=uuid.UUID(supplier_id),
                medicine_id=uuid.UUID(medicine_id) if medicine_id else None,
                months=months
            )
            
            return jsonify(metrics), 200
            
    except ValueError as e:
        current_app.logger.error(f"Invalid UUID format: {str(e)}")
        return jsonify({'error': 'Invalid ID format'}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching supplier metrics: {str(e)}")
        return jsonify({'error': 'Failed to fetch metrics'}), 500


@supplier_views_bp.route('/api/medicines/<medicine_id>/prices', methods=['GET'])
@login_required
@require_web_branch_permission('medicine', 'view', branch_source='entity')
def api_get_medicine_with_prices(medicine_id):
    """
    Get medicine with all price information including MRP, selling price, margins
    Enhanced version of existing get_medicine_api
    """
    try:
        from app.services.medicine_service import MedicineService
        
        with get_db_session(read_only=True) as session:
            medicine_data = MedicineService.get_medicine_with_prices(
                session=session,
                medicine_id=uuid.UUID(medicine_id)
            )
            
            if not medicine_data:
                return jsonify({'error': 'Medicine not found'}), 404
            
            # Add branch info if needed
            medicine = session.query(Medicine).filter_by(
                medicine_id=uuid.UUID(medicine_id),
                hospital_id=current_user.hospital_id
            ).first()
            
            if medicine and hasattr(medicine, 'branch_id'):
                medicine_data['branch_id'] = str(medicine.branch_id) if medicine.branch_id else None
            
            return jsonify(medicine_data), 200
            
    except ValueError as e:
        current_app.logger.error(f"Invalid UUID format: {str(e)}")
        return jsonify({'error': 'Invalid medicine ID'}), 400
    except Exception as e:
        current_app.logger.error(f"Error fetching medicine prices: {str(e)}")
        return jsonify({'error': 'Failed to fetch medicine prices'}), 500


@supplier_views_bp.route('/api/medicines/validate-price', methods=['POST'])
@login_required
@require_web_branch_permission('purchase_order', 'create')
def api_validate_purchase_price():
    """
    Validate purchase price against MRP
    Used in PO/Invoice creation for real-time validation
    """
    try:
        from app.services.medicine_service import MedicineService
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        medicine_id = data.get('medicine_id')
        purchase_price = float(data.get('purchase_price', 0))
        gst_rate = float(data.get('gst_rate', 0))
        
        if not medicine_id or purchase_price <= 0:
            return jsonify({'error': 'Invalid input data'}), 400
        
        with get_db_session(read_only=True) as session:
            medicine = session.query(Medicine).filter_by(
                medicine_id=uuid.UUID(medicine_id),
                hospital_id=current_user.hospital_id
            ).first()
            
            if not medicine:
                return jsonify({'error': 'Medicine not found'}), 404
            
            validation_result = MedicineService.validate_purchase_price(
                medicine=medicine,
                purchase_price=purchase_price,
                gst_rate=gst_rate
            )
            
            return jsonify(validation_result), 200
            
    except ValueError as e:
        current_app.logger.error(f"Invalid value: {str(e)}")
        return jsonify({'error': 'Invalid numeric values'}), 400
    except Exception as e:
        current_app.logger.error(f"Error validating price: {str(e)}")
        return jsonify({'error': 'Validation failed'}), 500

@supplier_views_bp.route('/purchase-order/delete/<po_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('purchase_order', 'delete', branch_source='entity')
def delete_purchase_order(po_id):
    """Soft delete a purchase order using SoftDeleteMixin (only draft status allowed)"""
    try:
        # Import service locally
        from app.services.supplier_service import get_purchase_order_by_id
        from app.services.database_service import get_db_session
        from app.models.transaction import PurchaseOrderHeader
        
        # Get PO details first for validation
        po_data = get_purchase_order_by_id(
            po_id=uuid.UUID(po_id),
            hospital_id=current_user.hospital_id
        )
        
        if not po_data:
            flash("Purchase order not found", "error")
            return redirect(url_for('universal_views.universal_list_view', 
                                  entity_type='purchase_orders'))
        
        # Check if PO is in draft status
        if po_data.get('status') != 'draft':
            flash('Only draft purchase orders can be deleted', 'error')
            return redirect(url_for('universal_views.universal_detail_view', 
                                  entity_type='purchase_orders', item_id=po_id))
        
        # ✅ NEW: Use SoftDeleteMixin for consistent deletion
        with get_db_session() as session:
            po_uuid = uuid.UUID(po_id)
            
            # Get the PO object
            po = session.query(PurchaseOrderHeader).filter_by(
                po_id=po_uuid,
                hospital_id=current_user.hospital_id
            ).first()
            
            if not po:
                flash("Purchase order not found", "error")
                return redirect(url_for('universal_views.universal_list_view', 
                                    entity_type='purchase_orders'))
            
            # Store PO number before deletion
            po_number = po.po_number
            
            # ✅ USE SOFTDELETEMIXIN: Replaces manual status/flag setting
            po.soft_delete(
                user_id=current_user.user_id,
                reason=f"User requested deletion of draft PO {po_number}",
                cascade_to_children=True  # Will automatically delete PO lines
            )
            
            # Commit MUST happen before any other operations
            session.commit()
            
            # Now we can show flash message
            flash(f'Purchase order {po_number} deleted successfully', 'success')

        # Outside the with block - cache invalidation
        try:
            from app.engine.universal_services import get_universal_service
            po_service = get_universal_service('purchase_orders')
            if hasattr(po_service, 'invalidate_cache'):
                po_service.invalidate_cache(str(po_id))
            logger.info(f"Cache invalidated for deleted PO {po_id}")
        except Exception as cache_error:
            logger.warning(f"Could not invalidate cache: {cache_error}")

        return redirect(url_for('universal_views.universal_list_view', 
                            entity_type='purchase_orders'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting PO: {str(e)}", exc_info=True)
        flash(f"Error deleting purchase order: {str(e)}", "error")
        return redirect(url_for('universal_views.universal_detail_view', 
                              entity_type='purchase_orders', item_id=po_id))

@supplier_views_bp.route('/purchase-order/restore/<po_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('purchase_order', 'delete', branch_source='entity')
def restore_purchase_order(po_id):
    """Restore a soft-deleted purchase order using SoftDeleteMixin"""
    try:
        from app.services.database_service import get_db_session
        from app.models.transaction import PurchaseOrderHeader
        
        with get_db_session() as session:
            po_uuid = uuid.UUID(po_id)
            
            # Get the deleted PO (must be deleted)
            po = session.query(PurchaseOrderHeader).filter_by(
                po_id=po_uuid,
                hospital_id=current_user.hospital_id
            ).filter(
                PurchaseOrderHeader.is_deleted == True  # Only deleted POs
            ).first()
            
            if not po:
                flash("Deleted purchase order not found", "error")
                return redirect(url_for('universal_views.universal_list_view', 
                                      entity_type='purchase_orders'))
            
            # Store PO details for message
            po_number = po.po_number
            
            # ✅ USE SOFTDELETEMIXIN undelete method
            po.undelete(
                user_id=current_user.user_id,
                reason=f"User requested restoration of PO {po_number}",
                cascade_to_children=True  # Will restore PO lines too
            )
            
            session.commit()
            
        flash(f'Purchase order {po_number} restored successfully', 'success')
        
        # Invalidate cache after restoration
        try:
            from app.engine.universal_services import get_universal_service
            po_service = get_universal_service('purchase_orders')
            if hasattr(po_service, 'invalidate_cache'):
                po_service.invalidate_cache(str(po_id))
            logger.info(f"Cache invalidated for restored PO {po_id}")
        except Exception as cache_error:
            logger.warning(f"Could not invalidate cache: {cache_error}")
        
        return redirect(url_for('universal_views.universal_detail_view', 
                              entity_type='purchase_orders', item_id=po_id))
        
    except Exception as e:
        current_app.logger.error(f"Error restoring PO: {str(e)}", exc_info=True)
        flash(f"Error restoring purchase order: {str(e)}", "error")
        return redirect(url_for('universal_views.universal_list_view', 
                              entity_type='purchase_orders'))

@supplier_views_bp.route('/purchase-order/approve/<po_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('purchase_order', 'approve', branch_source='entity')
def approve_purchase_order(po_id):
    """Approve a purchase order using ApprovalMixin"""
    try:
        from app.services.database_service import get_db_session
        from app.models.transaction import PurchaseOrderHeader
        
        with get_db_session() as session:
            po = session.query(PurchaseOrderHeader).filter_by(
                po_id=uuid.UUID(po_id),
                hospital_id=current_user.hospital_id
            ).first()
            
            if not po:
                flash("Purchase order not found", "error")
                return redirect(url_for('universal_views.universal_list_view', 
                                      entity_type='purchase_orders'))
            
            if po.status != 'draft':
                flash("Only draft purchase orders can be approved", "error")
                # Check if request came from list view
                if request.referrer and '/list' in request.referrer:
                    return redirect(url_for('universal_views.universal_list_view', 
                                        entity_type='purchase_orders'))
                else:
                    return redirect(url_for('universal_views.universal_detail_view', 
                                        entity_type='purchase_orders', item_id=po_id))
            
            # ✅ USE APPROVALMIXIN: Replaces manual approval tracking
            po.approve(
                approver_id=current_user.user_id,
                notes=f"Purchase order approved via web interface"
            )
            # This automatically sets: approved_by, approved_at, status='approved', updated audit fields
            
            session.commit()
            flash('Purchase order approved successfully', 'success')

            # Invalidate cache after approval - ENHANCED
            try:
                # Method 1: Try service-level cache invalidation
                from app.engine.universal_services import get_universal_service
                po_service = get_universal_service('purchase_orders')
                if hasattr(po_service, 'after_status_change'):
                    po_service.after_status_change(str(po_id), 'approved')
                    logger.info(f"Called after_status_change for PO {po_id}")
                elif hasattr(po_service, 'invalidate_cache'):
                    po_service.invalidate_cache(str(po_id))
                    logger.info(f"Called invalidate_cache for PO {po_id}")
                
                # Method 2: Direct cache manager invalidation (more thorough)
                from app.engine.universal_service_cache import get_service_cache_manager
                cache_manager = get_service_cache_manager()
                if cache_manager:
                    # Invalidate all purchase_orders cache entries
                    invalidated = cache_manager.invalidate_entity_cache('purchase_orders', cascade=True)
                    logger.info(f"Invalidated {invalidated} cache entries for purchase_orders")
                
                logger.info(f"✅ Cache successfully invalidated for approved PO {po_id}")
            except Exception as cache_error:
                logger.error(f"Cache invalidation error: {cache_error}", exc_info=True)
                # Fallback: Try alternative methods
                try:
                    from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                    invalidate_service_cache_for_entity('purchase_orders', cascade=True)
                    logger.info(f"Used fallback cache invalidation for PO {po_id}")
                except:
                    pass
            
        return redirect(url_for('universal_views.universal_detail_view', 
                              entity_type='purchase_orders', item_id=po_id))
                              
    except Exception as e:
        current_app.logger.error(f"Error approving PO: {str(e)}", exc_info=True)
        flash(f"Error approving purchase order: {str(e)}", "error")
        return redirect(url_for('universal_views.universal_detail_view', 
                              entity_type='purchase_orders', item_id=po_id))


# ✅ Unapprove route using ApprovalMixin
@supplier_views_bp.route('/purchase-order/unapprove/<po_id>', methods=['GET', 'POST'])
@login_required
@require_web_branch_permission('purchase_order', 'approve', branch_source='entity')
def unapprove_purchase_order(po_id):
    """Unapprove a purchase order using ApprovalMixin (only if no invoices exist)"""
    try:
        from app.services.database_service import get_db_session
        from app.models.transaction import PurchaseOrderHeader, SupplierInvoice
        
        with get_db_session() as session:
            po = session.query(PurchaseOrderHeader).filter_by(
                po_id=uuid.UUID(po_id),
                hospital_id=current_user.hospital_id
            ).first()
            
            if not po:
                flash("Purchase order not found", "error")
                return redirect(url_for('universal_views.universal_list_view', 
                                      entity_type='purchase_orders'))
            
            if po.status != 'approved':
                flash("Only approved purchase orders can be unapproved", "error")
                return redirect(url_for('universal_views.universal_detail_view', 
                                      entity_type='purchase_orders', item_id=po_id))
            
            # Check if invoices exist
            invoice_count = session.query(SupplierInvoice).filter_by(
                po_id=uuid.UUID(po_id)
            ).count()
            
            if invoice_count > 0:
                flash('Cannot unapprove purchase order: Invoices have been raised against this PO', 'error')
                return redirect(url_for('universal_views.universal_detail_view', 
                                      entity_type='purchase_orders', item_id=po_id))
            
            # ✅ USE APPROVALMIXIN: Consistent unapproval
            po.unapprove(
                user_id=current_user.user_id,
                reason="User requested unapproval via web interface"
            )
            # This automatically clears: approved_by, approved_at, sets status='draft'
            
            session.commit()
            flash('Purchase order unapproved successfully', 'success')

            # Invalidate cache after unapproval
            try:
                from app.engine.universal_services import get_universal_service
                po_service = get_universal_service('purchase_orders')
                if hasattr(po_service, 'after_status_change'):
                    po_service.after_status_change(str(po_id), 'draft')  # FIXED - correct status
                elif hasattr(po_service, 'invalidate_cache'):
                    po_service.invalidate_cache(str(po_id))
                logger.info(f"Cache invalidated for unapproved PO {po_id}")  # FIXED message
            except Exception as cache_error:
                logger.warning(f"Could not invalidate cache: {cache_error}")
            
        return redirect(url_for('universal_views.universal_detail_view', 
                              entity_type='purchase_orders', item_id=po_id))
                              
    except Exception as e:
        current_app.logger.error(f"Error unapproving PO: {str(e)}", exc_info=True)
        flash(f"Error unapproving purchase order: {str(e)}", "error")
        return redirect(url_for('universal_views.universal_detail_view', 
                              entity_type='purchase_orders', item_id=po_id))
    
@supplier_views_bp.route('/invoice/debug-session', methods=['GET'])
@login_required
def debug_invoice_session():
    """Debug endpoint to check session line items"""
    from flask import jsonify, session
    from flask_login import current_user
    
    session_key = f'supplier_invoice_line_items_{current_user.user_id}'
    line_items = session.get(session_key, [])
    
    return jsonify({
        'session_key': session_key,
        'line_items_count': len(line_items),
        'line_items': line_items,
        'all_session_keys': list(session.keys())
    })

@supplier_views_bp.route('/api/get-supplier-currency', methods=['POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'add')
def get_supplier_currency():
    """API endpoint to get supplier's currency and exchange rate"""
    try:
        from app.services.database_service import get_db_session
        from app.models.master import Supplier, CurrencyMaster, Hospital, Branch
        from app.config.core_definitions import INDIAN_STATES
        import uuid
        
        data = request.json
        supplier_id = data.get('supplier_id')
        
        if not supplier_id:
            return jsonify({'success': False, 'error': 'Supplier ID required'}), 400
        
        # CRITICAL FIX: Get user branch BEFORE opening session
        from app.services.branch_service import get_user_branch_id
        user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
        
        # Single session for all queries
        with get_db_session(read_only=True) as session:
            # Get supplier
            supplier = session.query(Supplier).filter_by(
                supplier_id=uuid.UUID(supplier_id),
                hospital_id=current_user.hospital_id
            ).first()
            
            if not supplier:
                return jsonify({'success': False, 'error': 'Supplier not found'}), 404
            
            # Get currency code (default to INR)
            currency_code = getattr(supplier, 'currency_code', 'INR') or 'INR'
            supplier_state_code = supplier.state_code
            supplier_gstin = supplier.gst_registration_number or ''
            
            # Extract tax defaults from supplier master
            reverse_charge_default = False  # Safe default
            itc_eligible_default = True     # Safe default
            
            # Try to get actual values from database if columns exist
            if hasattr(supplier, 'reverse_charge_applicable'):
                db_value = supplier.reverse_charge_applicable
                if db_value is not None:
                    reverse_charge_default = bool(db_value)
            
            if hasattr(supplier, 'default_itc_eligible'):
                db_value = supplier.default_itc_eligible
                if db_value is not None:
                    itc_eligible_default = bool(db_value)
            
            # Extract tax type
            tax_type = supplier.tax_type or 'regular'
            
            # Log for debugging
            current_app.logger.info(
                f"Supplier '{supplier.supplier_name}' tax defaults: "
                f"RCM={reverse_charge_default}, ITC={itc_eligible_default}, "
                f"type={tax_type}, GSTIN={'Yes' if supplier_gstin else 'No'}"
            )
            
            # Business Logic: Override ONLY for unregistered suppliers without GSTIN
            if tax_type == 'unregistered' or not supplier_gstin:
                current_app.logger.info(f"Overriding: Unregistered supplier or no GSTIN")
                reverse_charge_default = True
                itc_eligible_default = False
            
            # Get exchange rate
            exchange_rate = 1.0
            currency_master = session.query(CurrencyMaster).filter_by(
                hospital_id=current_user.hospital_id,
                currency_code=currency_code,
                is_active=True
            ).first()
            
            if currency_master:
                exchange_rate = float(currency_master.exchange_rate)
            
            # Get hospital state
            hospital = session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()
            
            # Get branch state (using pre-fetched user_branch_id)
            branch_state_code = None
            if user_branch_id:
                branch = session.query(Branch).filter_by(
                    branch_id=user_branch_id,
                    hospital_id=current_user.hospital_id
                ).first()
                if branch:
                    branch_state_code = branch.state_code
            
            # Fallback to hospital state
            if not branch_state_code and hospital:
                branch_state_code = hospital.state_code
            
            # Get state name from code
            supplier_state_name = supplier_state_code
            if supplier_state_code:
                for state in INDIAN_STATES:
                    if state.get('value') == supplier_state_code:
                        supplier_state_name = state.get('label', supplier_state_code)
                        break
            
            # Calculate interstate flag
            is_interstate = False
            if supplier_state_code and branch_state_code:
                is_interstate = (supplier_state_code != branch_state_code)
            
            current_app.logger.info(f"Supplier currency data: currency={currency_code}, rate={exchange_rate}, "
                                  f"supplier_state={supplier_state_code}, branch_state={branch_state_code}, "
                                  f"interstate={is_interstate}")
        
        # END OF SESSION CONTEXT - All data extracted
        
        # Return the data (all simple Python types now)
        return jsonify({
            'success': True,
            'currency_code': currency_code,
            'exchange_rate': exchange_rate,
            'place_of_supply': supplier_state_code or '',
            'supplier_state_name': supplier_state_name or '',
            'supplier_gstin': supplier_gstin,
            'is_interstate': is_interstate,
            'branch_state': branch_state_code or '',
            'supplier_state': supplier_state_code or '',
            'reverse_charge_default': reverse_charge_default,
            'itc_eligible_default': itc_eligible_default,
            'tax_type': tax_type
        })
            
    except Exception as e:
        current_app.logger.error(f"Error getting supplier currency: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    
@supplier_views_bp.route('/api/get-supplier-pos', methods=['POST'])
@login_required
@require_web_branch_permission('supplier_invoice', 'add')
def get_supplier_pos():
    """API endpoint to get available POs for a supplier"""
    try:
        from app.services.supplier_service import search_purchase_orders
        from app.services.branch_service import get_user_branch_id
        from app.services.database_service import get_db_session
        from app.models.transaction import SupplierInvoice
        from sqlalchemy import func
        import uuid
        
        data = request.json
        supplier_id = data.get('supplier_id')
        
        if not supplier_id:
            return jsonify({'success': False, 'error': 'Supplier ID required'}), 400
        
        # Get user's branch
        user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
        
        # Search for approved POs for this supplier
        po_results = search_purchase_orders(
            hospital_id=current_user.hospital_id,
            supplier_id=uuid.UUID(supplier_id),
            status='approved',
            branch_id=user_branch_id,
            page=1,
            per_page=100
        )
        
        purchase_orders = []
        
        # Filter out fully invoiced POs
        with get_db_session() as session:
            for po in po_results.get('purchase_orders', []):
                po_id = po.get('po_id')
                po_total = float(po.get('total_amount', 0))
                
                # Calculate invoiced amount
                invoiced_total = session.query(func.sum(SupplierInvoice.total_amount))\
                    .filter(
                        SupplierInvoice.po_id == po_id,
                        SupplierInvoice.hospital_id == current_user.hospital_id,
                        SupplierInvoice.payment_status != 'cancelled'
                    ).scalar() or 0
                
                invoiced_total = float(invoiced_total)
                remaining = po_total - invoiced_total
                
                # Only include if remaining amount > 0
                if remaining > 0.01:
                    po_number = po.get('po_number', 'Unknown')
                    po_date = po.get('po_date')
                    
                    po_date_str = ''
                    if po_date:
                        po_date_str = po_date.strftime('%Y-%m-%d') if hasattr(po_date, 'strftime') else str(po_date)[:10]
                    
                    purchase_orders.append({
                        'po_id': str(po_id),
                        'po_display': f"{po_number} - {po_date_str} (₹{remaining:,.2f} remaining)"
                    })
        
        return jsonify({
            'success': True,
            'purchase_orders': purchase_orders
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting supplier POs: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500