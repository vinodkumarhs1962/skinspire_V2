# app/views/supplier_views.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.services.supplier_service import (
    create_supplier,
    update_supplier,
    get_supplier_by_id,
    search_suppliers,
    create_purchase_order,
    update_purchase_order_status,
    get_purchase_order_by_id,
    search_purchase_orders,
    create_supplier_invoice,
    get_supplier_invoice_by_id,
    search_supplier_invoices,
    record_supplier_payment,
    get_supplier_payment_history,
    get_pending_supplier_invoices
)
from app.services.inventory_service import record_stock_from_supplier_invoice
from app.services.gl_service import create_supplier_invoice_gl_entries, create_supplier_payment_gl_entries
from app.forms.supplier_forms import (
    SupplierForm,
    PurchaseOrderForm,
    PurchaseOrderLineForm,
    SupplierInvoiceForm,
    SupplierInvoiceLineForm,
    SupplierPaymentForm,
    SupplierFilterForm,
    PurchaseOrderFilterForm,
    SupplierInvoiceFilterForm
)
from app.services.database_service import get_db_session
from app.security.authorization.permission_validator import has_permission, permission_required

supplier_views_bp = Blueprint('supplier_views', __name__, url_prefix='/supplier')

# Supplier Management Routes
@supplier_views_bp.route('/', methods=['GET'])
@login_required
@permission_required('supplier', 'view')
def supplier_list():
    """Display list of suppliers with filtering."""
    form = SupplierFilterForm()
    
    name = request.args.get('name')
    # Change from supplier_category to category
    category = request.args.get('supplier_category')
    gst_number = request.args.get('gst_number')
    status = request.args.get('status', 'active')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        # Use the correct parameter name (category instead of supplier_category)
        result = search_suppliers(
            hospital_id=current_user.hospital_id,
            name=name,
            category=category,  # Changed from supplier_category to category
            gst_number=gst_number,
            status=status,
            page=page,
            per_page=per_page
        )
        
        # Since we're getting a dict back, extract the needed values
        suppliers = result.get('suppliers', [])
        total = result.get('total', 0)
            
        return render_template(
            'supplier/supplier_list.html',
            suppliers=suppliers,
            form=form,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        current_app.logger.error(f"Error in supplier_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving suppliers: {str(e)}", "error")
        return render_template('supplier/supplier_list.html', form=form, suppliers=[], total=0, page=1, per_page=per_page)

@supplier_views_bp.route('/add', methods=['GET', 'POST'])
@login_required
@permission_required('supplier', 'add')
def add_supplier():
    """Add a new supplier."""
    form = SupplierForm()
    
    if form.validate_on_submit():
        try:
            current_app.logger.info("Form validated successfully, preparing supplier data")
            supplier_data = {
                'supplier_name': form.supplier_name.data,
                'supplier_category': form.supplier_category.data,
                'supplier_address': {
                    'address_line1': form.address_line1.data,
                    'address_line2': form.address_line2.data,
                    'city': form.city.data,
                    'state': form.state.data,
                    'country': form.country.data,
                    'pincode': form.pincode.data
                },
                'contact_person_name': form.contact_person_name.data,
                'contact_info': {
                    'phone': form.phone.data,
                    'mobile': form.mobile.data,
                    'email': form.email.data
                },
                'manager_name': form.manager_name.data,
                'manager_contact_info': {
                    'phone': form.manager_phone.data,
                    'mobile': form.manager_mobile.data,
                    'email': form.manager_email.data
                },
                'email': form.email.data,
                'payment_terms': form.payment_terms.data,
                'gst_registration_number': form.gst_registration_number.data,
                'pan_number': form.pan_number.data,
                'tax_type': form.tax_type.data,
                'state_code': form.state_code.data,
                'bank_details': {
                    'account_name': form.bank_account_name.data,
                    'account_number': form.bank_account_number.data,
                    'bank_name': form.bank_name.data,
                    'ifsc_code': form.ifsc_code.data,
                    'branch': form.bank_branch.data
                },
                'remarks': form.remarks.data
            }
            
            current_app.logger.info(f"Calling create_supplier with supplier_name: {supplier_data['supplier_name']}")
            from app.services.supplier_service import create_supplier
            
            # Log hospital ID to ensure it's correct
            current_app.logger.info(f"Hospital ID: {current_user.hospital_id}")
            
            # Call the service function
            supplier = create_supplier(
                hospital_id=current_user.hospital_id,
                supplier_data=supplier_data,
                current_user_id=current_user.user_id
            )
            
            current_app.logger.info(f"Supplier creation result: {supplier}")
            
            flash("Supplier created successfully", "success")
            return redirect(url_for('supplier_views.supplier_list'))
        except Exception as e:
            current_app.logger.error(f"Error in add_supplier: {str(e)}", exc_info=True)
            flash(f"Error creating supplier: {str(e)}", "error")
    
    return render_template('supplier/supplier_form.html', form=form, title="Add Supplier")

@supplier_views_bp.route('/edit/<supplier_id>', methods=['GET', 'POST'])
@login_required
@permission_required('supplier', 'edit')
def edit_supplier(supplier_id):
    """Edit an existing supplier."""
    form = SupplierForm()
    
    try:
        with get_db_session() as session:
            supplier = get_supplier_by_id(session, current_user.hospital_id, supplier_id)
            
            if not supplier:
                flash("Supplier not found", "error")
                return redirect(url_for('supplier_views.supplier_list'))
            
            if request.method == 'GET':
                form.supplier_name.data = supplier.supplier_name
                form.supplier_category.data = supplier.supplier_category
                form.address_line1.data = supplier.supplier_address.get('address_line1', '')
                form.address_line2.data = supplier.supplier_address.get('address_line2', '')
                form.city.data = supplier.supplier_address.get('city', '')
                form.state.data = supplier.supplier_address.get('state', '')
                form.country.data = supplier.supplier_address.get('country', '')
                form.pincode.data = supplier.supplier_address.get('pincode', '')
                form.contact_person_name.data = supplier.contact_person_name
                form.phone.data = supplier.contact_info.get('phone', '')
                form.mobile.data = supplier.contact_info.get('mobile', '')
                form.email.data = supplier.email
                form.manager_name.data = supplier.manager_name
                form.manager_phone.data = supplier.manager_contact_info.get('phone', '')
                form.manager_mobile.data = supplier.manager_contact_info.get('mobile', '')
                form.manager_email.data = supplier.manager_contact_info.get('email', '')
                form.payment_terms.data = supplier.payment_terms
                form.gst_registration_number.data = supplier.gst_registration_number
                form.pan_number.data = supplier.pan_number
                form.tax_type.data = supplier.tax_type
                form.state_code.data = supplier.state_code
                form.bank_account_name.data = supplier.bank_details.get('account_name', '')
                form.bank_account_number.data = supplier.bank_details.get('account_number', '')
                form.bank_name.data = supplier.bank_details.get('bank_name', '')
                form.ifsc_code.data = supplier.bank_details.get('ifsc_code', '')
                form.bank_branch.data = supplier.bank_details.get('branch', '')
                form.remarks.data = supplier.remarks
                
            if form.validate_on_submit():
                supplier_data = {
                    'supplier_name': form.supplier_name.data,
                    'supplier_category': form.supplier_category.data,
                    'supplier_address': {
                        'address_line1': form.address_line1.data,
                        'address_line2': form.address_line2.data,
                        'city': form.city.data,
                        'state': form.state.data,
                        'country': form.country.data,
                        'pincode': form.pincode.data
                    },
                    'contact_person_name': form.contact_person_name.data,
                    'contact_info': {
                        'phone': form.phone.data,
                        'mobile': form.mobile.data,
                        'email': form.email.data
                    },
                    'manager_name': form.manager_name.data,
                    'manager_contact_info': {
                        'phone': form.manager_phone.data,
                        'mobile': form.manager_mobile.data,
                        'email': form.manager_email.data
                    },
                    'email': form.email.data,
                    'payment_terms': form.payment_terms.data,
                    'gst_registration_number': form.gst_registration_number.data,
                    'pan_number': form.pan_number.data,
                    'tax_type': form.tax_type.data,
                    'state_code': form.state_code.data,
                    'bank_details': {
                        'account_name': form.bank_account_name.data,
                        'account_number': form.bank_account_number.data,
                        'bank_name': form.bank_name.data,
                        'ifsc_code': form.ifsc_code.data,
                        'branch': form.bank_branch.data
                    },
                    'remarks': form.remarks.data,
                    'updated_by': current_user.user_id
                }
                
                update_supplier(session, current_user.hospital_id, supplier_id, supplier_data)
                flash("Supplier updated successfully", "success")
                return redirect(url_for('supplier_views.supplier_list'))
    except Exception as e:
        current_app.logger.error(f"Error in edit_supplier: {str(e)}", exc_info=True)
        flash(f"Error updating supplier: {str(e)}", "error")
    
    return render_template('supplier/supplier_form.html', form=form, title="Edit Supplier")

@supplier_views_bp.route('/view/<supplier_id>', methods=['GET'])
@login_required
@permission_required('supplier', 'view')
def view_supplier(supplier_id):
    """View supplier details."""
    try:
        with get_db_session() as session:
            supplier = get_supplier_by_id(session, current_user.hospital_id, supplier_id)
            
            if not supplier:
                flash("Supplier not found", "error")
                return redirect(url_for('supplier_views.supplier_list'))
                
            return render_template('supplier/supplier_view.html', supplier=supplier)
    except Exception as e:
        current_app.logger.error(f"Error in view_supplier: {str(e)}", exc_info=True)
        flash(f"Error retrieving supplier details: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_list'))

# Purchase Order Routes
@supplier_views_bp.route('/purchase-orders', methods=['GET'])
@login_required
@permission_required('purchase_order', 'view')
def purchase_order_list():
    """Display list of purchase orders with filtering."""
    form = PurchaseOrderFilterForm()
    
    po_number = request.args.get('po_number')
    supplier_id = request.args.get('supplier_id')
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        with get_db_session() as session:
            purchase_orders, total = search_purchase_orders(
                session, 
                current_user.hospital_id,
                po_number=po_number,
                supplier_id=supplier_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
                page=page,
                per_page=per_page
            )
            
        return render_template(
            'supplier/purchase_order_list.html',
            purchase_orders=purchase_orders,
            form=form,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        current_app.logger.error(f"Error in purchase_order_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving purchase orders: {str(e)}", "error")
        return render_template('supplier/purchase_order_list.html', form=form, purchase_orders=[])

@supplier_views_bp.route('/purchase-order/add', methods=['GET', 'POST'])
@login_required
@permission_required('purchase_order', 'add')
def add_purchase_order():
    """Create a new purchase order."""
    form = PurchaseOrderForm()
    
    if form.validate_on_submit():
        try:
            po_data = {
                'supplier_id': form.supplier_id.data,
                'po_date': form.po_date.data,
                'expected_delivery_date': form.expected_delivery_date.data,
                'quotation_id': form.quotation_id.data,
                'quotation_date': form.quotation_date.data,
                'currency_code': form.currency_code.data,
                'exchange_rate': form.exchange_rate.data,
                'created_by': current_user.user_id
            }
            
            # Parse line items from form data
            line_items = []
            for i in range(len(form.medicine_ids)):
                line_items.append({
                    'medicine_id': form.medicine_ids[i],
                    'medicine_name': form.medicine_names[i],
                    'units': form.quantities[i],
                    'pack_purchase_price': form.pack_purchase_prices[i],
                    'pack_mrp': form.pack_mrps[i],
                    'units_per_pack': form.units_per_packs[i],
                    'hsn_code': form.hsn_codes[i],
                    'gst_rate': form.gst_rates[i],
                    'cgst_rate': form.cgst_rates[i],
                    'sgst_rate': form.sgst_rates[i],
                    'igst_rate': form.igst_rates[i]
                })
            
            with get_db_session() as session:
                po = create_purchase_order(
                    session, 
                    current_user.hospital_id, 
                    po_data, 
                    line_items
                )
                
            flash("Purchase order created successfully", "success")
            return redirect(url_for('supplier_views.view_purchase_order', po_id=po.po_id))
        except Exception as e:
            current_app.logger.error(f"Error in add_purchase_order: {str(e)}", exc_info=True)
            flash(f"Error creating purchase order: {str(e)}", "error")
    
    return render_template('supplier/create_purchase_order.html', form=form)

@supplier_views_bp.route('/purchase-order/view/<po_id>', methods=['GET'])
@login_required
@permission_required('purchase_order', 'view')
def view_purchase_order(po_id):
    """View purchase order details."""
    try:
        with get_db_session() as session:
            po = get_purchase_order_by_id(session, current_user.hospital_id, po_id)
            
            if not po:
                flash("Purchase order not found", "error")
                return redirect(url_for('supplier_views.purchase_order_list'))
                
            return render_template('supplier/view_purchase_order.html', po=po)
    except Exception as e:
        current_app.logger.error(f"Error in view_purchase_order: {str(e)}", exc_info=True)
        flash(f"Error retrieving purchase order details: {str(e)}", "error")
        return redirect(url_for('supplier_views.purchase_order_list'))

@supplier_views_bp.route('/purchase-order/update-status/<po_id>', methods=['POST'])
@login_required
@permission_required('purchase_order', 'edit')
def update_po_status(po_id):
    """Update purchase order status."""
    new_status = request.form.get('status')
    
    if not new_status:
        flash("Status is required", "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
    
    try:
        with get_db_session() as session:
            update_purchase_order_status(
                session,
                current_user.hospital_id,
                po_id,
                new_status,
                updated_by=current_user.user_id
            )
            
        flash(f"Purchase order status updated to {new_status}", "success")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))
    except Exception as e:
        current_app.logger.error(f"Error in update_po_status: {str(e)}", exc_info=True)
        flash(f"Error updating purchase order status: {str(e)}", "error")
        return redirect(url_for('supplier_views.view_purchase_order', po_id=po_id))

# Supplier Invoice Routes
@supplier_views_bp.route('/invoices', methods=['GET'])
@login_required
@permission_required('supplier_invoice', 'view')
def supplier_invoice_list():
    """Display list of supplier invoices with filtering."""
    form = SupplierInvoiceFilterForm()
    
    invoice_number = request.args.get('invoice_number')
    supplier_id = request.args.get('supplier_id')
    po_id = request.args.get('po_id')
    payment_status = request.args.get('payment_status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        with get_db_session() as session:
            invoices, total = search_supplier_invoices(
                session, 
                current_user.hospital_id,
                invoice_number=invoice_number,
                supplier_id=supplier_id,
                po_id=po_id,
                payment_status=payment_status,
                start_date=start_date,
                end_date=end_date,
                page=page,
                per_page=per_page
            )
            
        return render_template(
            'supplier/supplier_invoice_list.html',
            invoices=invoices,
            form=form,
            page=page,
            per_page=per_page,
            total=total
        )
    except Exception as e:
        current_app.logger.error(f"Error in supplier_invoice_list: {str(e)}", exc_info=True)
        flash(f"Error retrieving supplier invoices: {str(e)}", "error")
        return render_template('supplier/supplier_invoice_list.html', form=form, invoices=[])

@supplier_views_bp.route('/invoice/add', methods=['GET', 'POST'])
@login_required
@permission_required('supplier_invoice', 'add')
def add_supplier_invoice():
    """Create a new supplier invoice."""
    form = SupplierInvoiceForm()
    
    if form.validate_on_submit():
        try:
            invoice_data = {
                'supplier_id': form.supplier_id.data,
                'po_id': form.po_id.data,
                'supplier_invoice_number': form.supplier_invoice_number.data,
                'invoice_date': form.invoice_date.data,
                'supplier_gstin': form.supplier_gstin.data,
                'place_of_supply': form.place_of_supply.data,
                'reverse_charge': form.reverse_charge.data,
                'currency_code': form.currency_code.data,
                'exchange_rate': form.exchange_rate.data,
                'due_date': form.due_date.data,
                'itc_eligible': form.itc_eligible.data,
                'created_by': current_user.user_id
            }
            
            # Parse line items from form data
            line_items = []
            for i in range(len(form.medicine_ids)):
                line_items.append({
                    'medicine_id': form.medicine_ids[i],
                    'medicine_name': form.medicine_names[i],
                    'units': form.quantities[i],
                    'pack_purchase_price': form.pack_purchase_prices[i],
                    'pack_mrp': form.pack_mrps[i],
                    'units_per_pack': form.units_per_packs[i],
                    'is_free_item': form.is_free_items[i] if hasattr(form, 'is_free_items') else False,
                    'referenced_line_id': form.referenced_line_ids[i] if hasattr(form, 'referenced_line_ids') else None,
                    'discount_percent': form.discount_percents[i] if hasattr(form, 'discount_percents') else 0,
                    'pre_gst_discount': form.pre_gst_discounts[i] if hasattr(form, 'pre_gst_discounts') else True,
                    'hsn_code': form.hsn_codes[i],
                    'gst_rate': form.gst_rates[i],
                    'cgst_rate': form.cgst_rates[i],
                    'sgst_rate': form.sgst_rates[i],
                    'igst_rate': form.igst_rates[i],
                    'batch_number': form.batch_numbers[i],
                    'manufacturing_date': form.manufacturing_dates[i],
                    'expiry_date': form.expiry_dates[i],
                    'itc_eligible': form.item_itc_eligibles[i] if hasattr(form, 'item_itc_eligibles') else True
                })
            
            with get_db_session() as session:
                # Create the supplier invoice
                invoice = create_supplier_invoice(
                    session, 
                    current_user.hospital_id, 
                    invoice_data, 
                    line_items
                )
                
                # Create inventory entries
                record_stock_from_supplier_invoice(
                    session,
                    current_user.hospital_id,
                    invoice.invoice_id,
                    created_by=current_user.user_id
                )
                
                # Create GL entries
                create_supplier_invoice_gl_entries(
                    session,
                    current_user.hospital_id,
                    invoice.invoice_id,
                    created_by=current_user.user_id
                )
                
            flash("Supplier invoice created successfully", "success")
            return redirect(url_for('supplier_views.view_supplier_invoice', invoice_id=invoice.invoice_id))
        except Exception as e:
            current_app.logger.error(f"Error in add_supplier_invoice: {str(e)}", exc_info=True)
            flash(f"Error creating supplier invoice: {str(e)}", "error")
    
    return render_template('supplier/create_supplier_invoice.html', form=form)

@supplier_views_bp.route('/invoice/view/<invoice_id>', methods=['GET'])
@login_required
@permission_required('supplier_invoice', 'view')
def view_supplier_invoice(invoice_id):
    """View supplier invoice details."""
    try:
        with get_db_session() as session:
            invoice = get_supplier_invoice_by_id(session, current_user.hospital_id, invoice_id, include_payments=True)
            
            if not invoice:
                flash("Supplier invoice not found", "error")
                return redirect(url_for('supplier_views.supplier_invoice_list'))
                
            return render_template('supplier/view_supplier_invoice.html', invoice=invoice)
    except Exception as e:
        current_app.logger.error(f"Error in view_supplier_invoice: {str(e)}", exc_info=True)
        flash(f"Error retrieving supplier invoice details: {str(e)}", "error")
        return redirect(url_for('supplier_views.supplier_invoice_list'))

@supplier_views_bp.route('/invoice/payment/<invoice_id>', methods=['GET', 'POST'])
@login_required
@permission_required('supplier_payment', 'add')
def record_payment(invoice_id):
    """Record payment for supplier invoice."""
    form = SupplierPaymentForm()
    
    try:
        with get_db_session() as session:
            invoice = get_supplier_invoice_by_id(session, current_user.hospital_id, invoice_id)
            
            if not invoice:
                flash("Supplier invoice not found", "error")
                return redirect(url_for('supplier_views.supplier_invoice_list'))
            
            if request.method == 'GET':
                form.amount.data = invoice.total_amount - invoice.paid_amount
                form.supplier_id.data = invoice.supplier_id
            
            if form.validate_on_submit():
                payment_data = {
                    'supplier_id': invoice.supplier_id,
                    'invoice_id': invoice_id,
                    'payment_date': form.payment_date.data,
                    'payment_method': form.payment_method.data,
                    'currency_code': form.currency_code.data,
                    'exchange_rate': form.exchange_rate.data,
                    'amount': form.amount.data,
                    'reference_no': form.reference_no.data,
                    'notes': form.notes.data,
                    'created_by': current_user.user_id
                }
                
                # Record the payment
                payment = record_supplier_payment(
                    session,
                    current_user.hospital_id,
                    payment_data
                )
                
                # Create GL entries
                create_supplier_payment_gl_entries(
                    session,
                    current_user.hospital_id,
                    payment.payment_id,
                    created_by=current_user.user_id
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
@permission_required('supplier_payment', 'view')
def payment_history(supplier_id):
    """View payment history for a supplier."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        with get_db_session() as session:
            supplier = get_supplier_by_id(session, current_user.hospital_id, supplier_id)
            
            if not supplier:
                flash("Supplier not found", "error")
                return redirect(url_for('supplier_views.supplier_list'))
                
            payments = get_supplier_payment_history(
                session,
                current_user.hospital_id,
                supplier_id,
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
@permission_required('supplier_invoice', 'view')
def pending_invoices():
    """View pending supplier invoices."""
    supplier_id = request.args.get('supplier_id')
    
    try:
        with get_db_session() as session:
            invoices = get_pending_supplier_invoices(
                session,
                current_user.hospital_id,
                supplier_id=supplier_id
            )
            
            return render_template(
                'supplier/pending_invoices.html',
                invoices=invoices,
                supplier_id=supplier_id
            )
    except Exception as e:
        current_app.logger.error(f"Error in pending_invoices: {str(e)}", exc_info=True)
        flash(f"Error retrieving pending invoices: {str(e)}", "error")
        return render_template('supplier/pending_invoices.html', invoices=[])