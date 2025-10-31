# app/controllers/supplier_controller.py

from flask import current_app, flash, jsonify, request, redirect
import uuid
from datetime import datetime, date
import json
from app.controllers.form_controller import FormController
from app.services.database_service import get_db_session, get_detached_copy
from app.models.master import Medicine, Supplier, Branch, CurrencyMaster, Hospital
from app.models.transaction import PurchaseOrderHeader
from app.config.core_definitions import INDIAN_STATES
from app.services.permission_service import (
    get_user_branch_context,
    has_branch_permission
)
from app.services.branch_service import (
    validate_entity_branch_access  # Use centralized function instead of local helper
)
from app.services.branch_service import populate_branch_choices_for_user
from app.utils.form_helpers import populate_supplier_choices, populate_invoice_choices_for_supplier
from app.config import PAYMENT_CONFIG, DOCUMENT_CONFIG
from app.services.supplier_service import (
    get_supplier_payment_by_id,
    record_supplier_payment,
    update_supplier_payment,
    approve_supplier_payment,
    reject_supplier_payment
)
from app.engine.universal_service_cache import cache_service_method, cache_universal
from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

def get_state_name_from_code(state_code):
    """Convert state code to state name using INDIAN_STATES"""
    if not state_code:
        return ''
    for state in INDIAN_STATES:
        if state['value'] == state_code:
            return state['label']
    return ''

class SupplierFormController(FormController):
    """Controller for supplier master form"""
    
    def __init__(self, supplier_id=None):
        # Import form locally to avoid circular import
        from app.forms.supplier_forms import SupplierForm
        
        self.supplier_id = supplier_id
        self.is_edit = supplier_id is not None
        
        super().__init__(
            form_class=SupplierForm,
            template_path='supplier/supplier_form.html',
            success_url=self._get_success_url,
            success_message="Supplier saved successfully",
            page_title="Edit Supplier" if self.is_edit else "Create Supplier",
            additional_context=self.get_additional_context  # <-- ADD THIS LINE
        )
    
    def _get_success_url(self, result):
        """Get success URL using local import to avoid circular reference"""
        from flask import url_for
        return url_for('supplier_views.view_supplier', supplier_id=result['supplier_id'])
    
    def setup_form_choices(self, form):
        """Setup dynamic choices for supplier forms using optimized helpers"""
        try:
            from flask_login import current_user
            
            # Use existing branch service instead of custom function
            if hasattr(form, 'branch_id'):
                populate_branch_choices_for_user(
                    form.branch_id, 
                    current_user, 
                    required=True,
                    module_name='supplier'
                )
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error setting up supplier form choices: {str(e)}")
            return False

    @cache_universal(entity_type='purchase_order', operation='get_form_context')
    def get_additional_context(self, *args, **kwargs):
        """Get additional context including branch selection - UPDATED with unified branch service"""
        context = super().get_additional_context(*args, **kwargs) if hasattr(super(), 'get_additional_context') else {}
        
        try:
            from flask_login import current_user
            from app.services.branch_service import get_branch_context_for_form
            
            current_app.logger.info(f"Getting branch context for user {current_user.user_id}")
            
            # Determine action
            action = 'edit' if self.is_edit else 'add'
            
            # Use new unified branch service
            branch_context = get_branch_context_for_form(
                current_user.user_id,
                current_user.hospital_id,
                module_name='supplier',
                action=action
            )
            
            # Set context in same format as before
            context.update({
                'branches': branch_context.get('branches', []),
                'default_branch_id': branch_context.get('default_branch_id'),
                'branch_context': {
                    'show_branch_selector': branch_context.get('show_branch_selector', False),
                    'accessible_branches': branch_context.get('branches', []),
                    'is_multi_branch_user': len(branch_context.get('branches', [])) > 1,
                    'can_cross_branch': branch_context.get('has_cross_branch_access', False),
                    'is_admin': branch_context.get('is_admin', False),
                    'method': branch_context.get('method', 'unknown'),
                    'action': action
                }
            })
            
            current_app.logger.info(f"Branch context: Method={branch_context.get('method')}, "
                                  f"Branches={len(context['branches'])}")
            
            if branch_context.get('error'):
                current_app.logger.error(f"Branch context error: {branch_context['error']}")
                
        except Exception as e:
            current_app.logger.error(f"Error getting branch context: {str(e)}", exc_info=True)
            context.update({
                'branches': [],
                'default_branch_id': None,
                'branch_context': {
                    'show_branch_selector': False,
                    'accessible_branches': [],
                    'is_multi_branch_user': False,
                    'can_cross_branch': False,
                    'error': str(e)
                }
            })
            
        return context

    def get_form(self, *args, **kwargs):
        """Get form instance with initial data for editing - ENHANCED"""
        form = super().get_form(*args, **kwargs)
        
        # Setup dynamic choices using optimized helpers
        self.setup_form_choices(form)
        
        if self.is_edit:
            try:
                from flask_login import current_user
                with get_db_session(read_only=True) as session:
                    supplier = session.query(Supplier).filter_by(
                        supplier_id=self.supplier_id,
                        hospital_id=current_user.hospital_id
                    ).first()
                    
                    if supplier:
                        # Populate form with existing data (keep existing logic)
                        self.populate_form(form, supplier)
                        
            except Exception as e:
                current_app.logger.error(f"Error loading supplier: {str(e)}")
        
        return form
    
    def populate_form(self, form, supplier):
        """Populate form with supplier data - aligned with original field names"""
        form.supplier_name.data = supplier.supplier_name
        form.supplier_category.data = supplier.supplier_category
        form.contact_person_name.data = supplier.contact_person_name
        form.email.data = supplier.email
        
        # Contact info
        if supplier.contact_info:
            form.phone.data = supplier.contact_info.get('phone')
            form.mobile.data = supplier.contact_info.get('mobile')
        
        # Address
        if supplier.supplier_address:
            form.address_line1.data = supplier.supplier_address.get('address_line1')
            form.address_line2.data = supplier.supplier_address.get('address_line2')
            form.city.data = supplier.supplier_address.get('city')
            form.state.data = supplier.supplier_address.get('state')
            form.country.data = supplier.supplier_address.get('country')
            form.pincode.data = supplier.supplier_address.get('pincode')
        
        # Manager info (aligned with original fields)
        form.manager_name.data = supplier.manager_name
        if supplier.manager_contact_info:
            form.manager_phone.data = supplier.manager_contact_info.get('phone')
            form.manager_mobile.data = supplier.manager_contact_info.get('mobile')
            form.manager_email.data = supplier.manager_contact_info.get('email')
        
        # Other fields
        form.performance_rating.data = supplier.performance_rating
        form.payment_terms.data = supplier.payment_terms
        form.black_listed.data = supplier.black_listed
        form.gst_registration_number.data = supplier.gst_registration_number
        form.pan_number.data = supplier.pan_number
        form.tax_type.data = supplier.tax_type
        form.state_code.data = supplier.state_code
        
        # Bank details (aligned with original field names)
        if supplier.bank_details:
            form.bank_account_name.data = supplier.bank_details.get('account_name')
            form.bank_account_number.data = supplier.bank_details.get('account_number')
            form.bank_name.data = supplier.bank_details.get('bank_name')
            form.ifsc_code.data = supplier.bank_details.get('ifsc_code')
            form.bank_branch.data = supplier.bank_details.get('branch')
        
        form.remarks.data = supplier.remarks
        # NEW: Set branch if form has branch field
        if hasattr(form, 'branch_id'):
            form.branch_id.data = str(supplier.branch_id) if supplier.branch_id else None


    def process_form(self, form, *args, **kwargs):
        """Process the form data - ENHANCED with centralized branch validation"""
        try:
            # NEW: Add permission validation using centralized functions
            from app.services.supplier_service import create_supplier, update_supplier
            from flask_login import current_user
            from app.services.branch_service import validate_entity_branch_access
            from app.services.permission_service import has_branch_permission
            
            # PRESERVE: Testing bypass
            if current_user.user_id != '7777777777':
                try:
                    # For edit operations, validate access to existing supplier
                    if self.is_edit and self.supplier_id:
                        if not validate_entity_branch_access(
                            current_user.user_id,
                            current_user.hospital_id,
                            self.supplier_id,
                            'supplier',
                            'edit'
                        ):
                            raise PermissionError("Cannot edit supplier from different branch")
                    
                    # For create operations, validate branch access
                    if not self.is_edit:
                        target_branch_id = None
                        if hasattr(form, 'branch_id') and form.branch_id.data:
                            target_branch_id = form.branch_id.data
                        
                        user_obj = {'user_id': current_user.user_id, 'hospital_id': current_user.hospital_id}
                        if not has_branch_permission(user_obj, 'supplier', 'add', target_branch_id):
                            raise PermissionError("Insufficient permissions to create supplier in specified branch")
                            
                except PermissionError:
                    raise  # Re-raise permission errors
                except Exception as e:
                    current_app.logger.warning(f"Permission validation failed, proceeding: {str(e)}")
                    # Continue with operation if permission check fails (non-disruptive)
            
            
            data = {
                'supplier_name': form.supplier_name.data,
                'supplier_category': form.supplier_category.data,
                'contact_person_name': form.contact_person_name.data,
                'email': form.email.data,
                'supplier_address': {
                    'address_line1': form.address_line1.data,
                    'address_line2': form.address_line2.data,
                    'city': form.city.data,
                    'state': form.state.data,
                    'country': form.country.data,
                    'pincode': form.pincode.data
                },
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
                'performance_rating': form.performance_rating.data,
                'payment_terms': form.payment_terms.data,
                'black_listed': form.black_listed.data,
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
            
            branch_id = None
            if hasattr(form, 'branch_id') and form.branch_id.data:
                branch_id = uuid.UUID(form.branch_id.data)
            else:
                # Fallback to user's default branch
                from app.services.branch_service import get_user_branch_id
                user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
                if user_branch_id:
                    branch_id = user_branch_id

            if self.is_edit:
                return update_supplier(
                    supplier_id=self.supplier_id,
                    supplier_data=data,
                    hospital_id=current_user.hospital_id,
                    branch_id=branch_id,
                    current_user_id=current_user.user_id
                )
            else:
                result = create_supplier(
                    hospital_id=current_user.hospital_id,
                    branch_id=branch_id,
                    supplier_data=data,
                    current_user_id=current_user.user_id
                )
                current_app.logger.info(f"Created supplier with ID: {result.get('supplier_id')}")
                return result
        
        except PermissionError as pe:
            current_app.logger.warning(f"Permission denied: {str(pe)}")
            raise  # Re-raise to be handled by form framework
        except Exception as e:
            current_app.logger.error(f"Error processing supplier form: {str(e)}")
            raise


class SupplierInvoiceFormController(FormController):
    """Controller for supplier invoice form"""
    
    def __init__(self, po_id=None):
        # Import form locally to avoid circular import
        from app.forms.supplier_forms import SupplierInvoiceForm
        
        self.po_id = po_id  # Store PO ID for pre-population
        
        super().__init__(
            form_class=SupplierInvoiceForm,
            template_path='supplier/create_supplier_invoice.html',
            success_url=self._get_success_url,
            success_message="Invoice created successfully",
            page_title="Create Supplier Invoice",
            additional_context=self.get_additional_context
        )
    
    def _get_success_url(self, result):
        """Generate success URL after invoice creation - USES UNIVERSAL ENGINE VIEW"""
        from flask import url_for
        invoice_id = result.get('invoice_id')
        return url_for('universal_views.universal_detail_view', 
                      entity_type='supplier_invoices', 
                      item_id=invoice_id)
    
    def process_form(self, form, *args, **kwargs):
        """Process supplier invoice form submission - COMPLETE IMPLEMENTATION"""
        try:
            from flask import current_app, request
            from flask_login import current_user
            import uuid
            from app.services.supplier_service import create_supplier_invoice
            from app.services.branch_service import get_user_branch_id
            
            current_app.logger.info("=== SUPPLIER INVOICE FORM SUBMISSION START ===")
            
            # Validate form has line items
            if not form.medicine_ids.data or not form.medicine_ids.data.strip():
                raise ValueError("No line items found. Please add at least one item to the invoice.")
            
            # Parse line items from hidden fields (SAME AS PO DOES)
            medicine_ids = form.medicine_ids.data.split(',')
            medicine_ids = [mid.strip() for mid in medicine_ids if mid.strip()]
            
            if not medicine_ids:
                raise ValueError("No valid line items found. Please add at least one item to the invoice.")
            
            current_app.logger.info(f"Processing {len(medicine_ids)} line items")

            # Parse all comma-separated fields - ADD NONE PROTECTION
            medicine_names = (form.medicine_names.data or '').split(',')
            quantities = (form.quantities.data or '').split(',')
            batch_numbers = (form.batch_numbers.data or '').split(',')
            expiry_dates = (form.expiry_dates.data or '').split(',')
            pack_purchase_prices = (form.pack_purchase_prices.data or '').split(',')
            pack_mrps = (form.pack_mrps.data or '').split(',')
            units_per_packs = (form.units_per_packs.data or '').split(',')
            hsn_codes = form.hsn_codes.data.split(',') if form.hsn_codes.data else []
            gst_rates = form.gst_rates.data.split(',') if form.gst_rates.data else []
            cgst_rates = form.cgst_rates.data.split(',') if form.cgst_rates.data else []
            sgst_rates = form.sgst_rates.data.split(',') if form.sgst_rates.data else []
            igst_rates = form.igst_rates.data.split(',') if form.igst_rates.data else []
            
            # Optional fields with defaults
            discount_percents = form.discount_percents.data.split(',') if form.discount_percents.data else ['0'] * len(medicine_ids)
            is_free_items = form.is_free_items.data.split(',') if form.is_free_items.data else ['false'] * len(medicine_ids)
            
            # Determine if interstate
            is_interstate = form.is_interstate.data if hasattr(form, 'is_interstate') else False
            
            # Build line items array
            line_items = []
            for i in range(len(medicine_ids)):
                is_free = is_free_items[i].lower() == 'true'
                
                line_item = {
                    'medicine_id': medicine_ids[i],
                    'medicine_name': medicine_names[i],
                    'units': float(quantities[i]),
                    'pack_purchase_price': 0.0 if is_free else float(pack_purchase_prices[i]),
                    'pack_mrp': float(pack_mrps[i]),
                    'units_per_pack': float(units_per_packs[i]),
                    'is_free_item': is_free,
                    'discount_percent': 0.0 if is_free else float(discount_percents[i]),
                    'pre_gst_discount': True,
                    'hsn_code': hsn_codes[i] if i < len(hsn_codes) else '',
                    'gst_rate': float(gst_rates[i]) if i < len(gst_rates) else 0,
                    'cgst_rate': float(cgst_rates[i]) if i < len(cgst_rates) else 0,
                    'sgst_rate': float(sgst_rates[i]) if i < len(sgst_rates) else 0,
                    'igst_rate': float(igst_rates[i]) if i < len(igst_rates) else 0,
                    'batch_number': batch_numbers[i],
                    'expiry_date': expiry_dates[i],
                    'itc_eligible': True,
                    'is_interstate': is_interstate
                }
                
                line_items.append(line_item)
            
            current_app.logger.info(f"Built {len(line_items)} line items for invoice")
            
            # Build invoice data
            invoice_data = {
                'supplier_id': uuid.UUID(form.supplier_id.data),
                'supplier_invoice_number': form.supplier_invoice_number.data,
                'invoice_date': form.invoice_date.data,
                'po_id': uuid.UUID(form.po_id.data) if form.po_id.data else None,
                'supplier_gstin': form.supplier_gstin.data,
                'place_of_supply': form.place_of_supply.data,
                'due_date': form.due_date.data,
                'reverse_charge': form.reverse_charge.data if hasattr(form, 'reverse_charge') else False,
                'is_interstate': is_interstate,
                'itc_eligible': form.itc_eligible.data if hasattr(form, 'itc_eligible') else True,
                'currency_code': form.currency_code.data if hasattr(form, 'currency_code') else 'INR',
                'exchange_rate': float(form.exchange_rate.data) if hasattr(form, 'exchange_rate') and form.exchange_rate.data else 1.0,
                'notes': form.notes.data if hasattr(form, 'notes') else '',
                'line_items': line_items
            }
            
            # Get branch ID
            branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
            
            # Create invoice using service
            result = create_supplier_invoice(
                hospital_id=current_user.hospital_id,
                branch_id=branch_id,
                invoice_data=invoice_data,
                create_stock_entries=True,
                current_user_id=current_user.user_id
            )
            
            current_app.logger.info(f"Invoice created successfully: {result.get('invoice_id')}")
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error processing invoice form: {str(e)}", exc_info=True)
            raise

    def get_additional_context(self, *args, **kwargs):
        """Get additional context for the template - ENHANCED with branch filtering"""
        context = {}
        
        try:
            # Import locally to avoid circular import
            from app.services.supplier_service import search_suppliers
            from flask_login import current_user
            from app.services.database_service import get_db_session, get_detached_copy
            from app.services.branch_service import get_user_branch_id
            from app.models.transaction import User
            from app.models.master import Branch, Supplier
            from app.models.transaction import PurchaseOrderHeader
            from app.config.core_definitions import INDIAN_STATES

            # Add INDIAN_STATES to context for dropdown
            context['INDIAN_STATES'] = INDIAN_STATES
            current_app.logger.info("Added INDIAN_STATES to context for dropdown")

            user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)

            # NEW: Get branch context for filtering
            try:
                from app.services.branch_service import get_branch_context_for_form
                branch_context = get_branch_context_for_form(
                    current_user.user_id,
                    current_user.hospital_id,
                    module_name='supplier',
                    action='add'
                )
                context['branch_context'] = {
                    'method': branch_context.get('method', 'testing_bypass'),
                    'accessible_branches': branch_context.get('branches', []),
                    'show_branch_selector': branch_context.get('show_branch_selector', False),
                    'can_cross_branch': branch_context.get('has_cross_branch_access', False),
                    'is_admin': branch_context.get('is_admin', False)
                }
                context['default_branch_id'] = branch_context.get('default_branch_id')
            except Exception as e:
                current_app.logger.warning(f"Could not get branch context: {str(e)}")
                context['branch_context'] = {'method': 'error', 'accessible_branches': [], 'can_cross_branch': False}
                context['default_branch_id'] = None

            # FIX: Recalculate has_branches based on the actual branches data
            context['has_branches'] = len(context.get('branches', [])) > 0

            # Ensure branch selector template variables are available
            context['branches'] = context.get('branches', [])
            context['default_branch_id'] = context.get('default_branch_id')
            context['has_branches'] = len(context.get('branches', [])) > 0
            
            # Ensure branch_context has required fields
            if not context['branch_context'].get('method'):
                context['branch_context']['method'] = 'unknown'

            # ENHANCED: Get suppliers with branch filtering
            if current_user.user_id == '7777777777':  # PRESERVE: Testing bypass
                # Use existing logic for testing user
                supplier_result = search_suppliers(
                    hospital_id=current_user.hospital_id,
                    branch_id=user_branch_id,
                    status='active',
                    page=1,
                    per_page=1000
                )
            else:
                # NEW: Use branch-aware search for regular users
                try:
                    supplier_result = search_suppliers(
                        hospital_id=current_user.hospital_id,
                        status='active',
                        current_user_id=current_user.user_id,  # This enables branch filtering
                        page=1,
                        per_page=1000
                    )
                except Exception as e:
                    current_app.logger.warning(f"Branch-aware search failed, using fallback: {str(e)}")
                    # FALLBACK: Use original search
                    supplier_result = search_suppliers(
                        hospital_id=current_user.hospital_id,
                        branch_id=user_branch_id,
                        status='active',
                        page=1,
                        per_page=1000
                    )
            
            context['suppliers'] = supplier_result.get('suppliers', [])
            
            # EXISTING: Get hospital state code and other context data (unchanged)
            with get_db_session(read_only=True) as session:
                # Get user with hospital data in a session
                from sqlalchemy.orm import joinedload
                user = session.query(User).options(
                    joinedload(User.hospital)
                ).filter_by(user_id=current_user.user_id).first()
                
                if user and user.hospital:
                    # Extract the needed data while in session
                    context['hospital_state_code'] = user.hospital.state_code
                else:
                    context['hospital_state_code'] = ""
                
                # Get branches - create detached copies
                all_branches = session.query(Branch).filter_by(
                    hospital_id=current_user.hospital_id,
                    is_active=True
                ).all()
                
                # NEW: Filter branches based on permissions
                accessible_branches = []
                if current_user.user_id == '7777777777':  # PRESERVE: Testing bypass
                    accessible_branches = all_branches
                else:
                    accessible_branch_ids = [b['branch_id'] for b in branch_context.get('accessible_branches', [])]
                    for branch in all_branches:
                        if (branch_context.get('can_cross_branch', False) or 
                            str(branch.branch_id) in accessible_branch_ids):
                            accessible_branches.append(branch)
                
                context['branches'] = [get_detached_copy(branch) for branch in accessible_branches]
                
                # ✅ OPTIMIZED: Only load POs in get_additional_context if coming from a specific PO
                # Otherwise, PO dropdown will be populated dynamically in get_form() based on supplier selection
                po_details = []
                po_suppliers = {}

                if self.po_id:
                    # When coming from PO list/view with po_id, fetch ONLY that specific PO
                    try:
                        specific_po = session.query(PurchaseOrderHeader).filter_by(
                            hospital_id=current_user.hospital_id,
                            po_id=uuid.UUID(self.po_id)
                        ).first()
                        
                        if specific_po:
                            po_copy = get_detached_copy(specific_po)
                            
                            # Get supplier name for display
                            supplier = session.query(Supplier).filter_by(
                                supplier_id=specific_po.supplier_id
                            ).first()
                            
                            if supplier:
                                po_copy.supplier_name = supplier.supplier_name
                                
                            po_suppliers[str(po_copy.po_id)] = str(specific_po.supplier_id)
                            po_details.append(po_copy)
                            
                            current_app.logger.info(f"✅ Loaded specific PO: {specific_po.po_number} (ID: {self.po_id})")
                        else:
                            current_app.logger.warning(f"⚠️ PO {self.po_id} not found")
                    except Exception as e:
                        current_app.logger.error(f"Error loading specific PO: {str(e)}")
                else:
                    # ✅ When creating invoice without PO reference:
                    # Don't load all POs here - they will be loaded dynamically in get_form() 
                    # based on supplier selection (see SCENARIO 2 in get_form)
                    current_app.logger.info("✅ No po_id - PO dropdown will be populated dynamically when supplier is selected")

                context['purchase_orders'] = po_details
                context['po_suppliers'] = po_suppliers  # Add mapping to context
                
                # NEW: If we have a specific PO ID, ensure it's loaded regardless of status
                if self.po_id:
                    po_id_str = str(self.po_id)
                    # Check if this PO is already in the list
                    po_exists = any(str(po.po_id) == po_id_str for po in po_details)
                    
                    if not po_exists:
                        current_app.logger.warning(f"Specific PO {po_id_str} not in approved list, loading separately")
                        # Load the specific PO regardless of status
                        specific_po = session.query(PurchaseOrderHeader).filter_by(
                            po_id=self.po_id,
                            hospital_id=current_user.hospital_id
                        ).first()
                        
                        if specific_po:
                            # Add to po_suppliers mapping
                            po_suppliers[po_id_str] = str(specific_po.supplier_id)
                            current_app.logger.info(f"Added specific PO supplier to mapping: {specific_po.supplier_id}")
                            
                            # Add to po_details list
                            po_copy = get_detached_copy(specific_po)
                            supplier = session.query(Supplier).filter_by(
                                supplier_id=specific_po.supplier_id
                            ).first()
                            if supplier:
                                po_copy.supplier_name = supplier.supplier_name
                            po_details.insert(0, po_copy)  # Add at beginning for visibility
                            current_app.logger.info(f"Added specific PO {specific_po.po_number} to dropdown list")
                        else:
                            current_app.logger.error(f"Specific PO {po_id_str} not found in database!")
                    else:
                        current_app.logger.info(f"Specific PO {po_id_str} already in list")
                    
                    # Update context with potentially added PO
                    context['purchase_orders'] = po_details
                    context['po_suppliers'] = po_suppliers
                
                # UPDATED: Get medicines with MRP data for dropdown  
                medicines = session.query(Medicine).filter(
                    Medicine.hospital_id == current_user.hospital_id,
                    Medicine.status == 'active'
                ).order_by(Medicine.medicine_name).all()
                
                # Enhance medicines with MRP data
                medicines_with_prices = []
                for m in medicines:
                    medicine_copy = get_detached_copy(m)
                    # Add price data attributes for template use
                    medicine_copy.last_mrp = float(m.mrp or 0)  # <-- NEW
                    medicine_copy.last_purchase_price = float(m.last_purchase_price or 0)  # <-- NEW
                    medicine_copy.currency_code = m.currency_code or 'INR'  # <-- NEW
                    medicines_with_prices.append(medicine_copy)
                
                context['medicines'] = medicines_with_prices

                # EXISTING: Create line item form (unchanged)
                from app.forms.supplier_forms import SupplierInvoiceLineForm
                line_item_form = SupplierInvoiceLineForm()
                
                # Set medicine choices
                medicine_choices = [('', 'Select Medicine')] + [
                    (str(med.medicine_id), med.medicine_name) for med in medicines
                ]
                line_item_form.medicine_id.choices = medicine_choices
                
                context['line_item_form'] = line_item_form
                
                # EXISTING: Get line items from session (unchanged)
                from flask import session as flask_session
                session_key = f'supplier_invoice_line_items_{current_user.user_id}'
                context['line_items'] = flask_session.get(session_key, [])
                context['user_branch_id'] = user_branch_id

        except Exception as e:
            current_app.logger.error(f"Error getting enhanced context: {str(e)}", exc_info=True)
            # FALLBACK: Ensure basic context is available
            context.update({
                'suppliers': [],
                'branches': [],
                'branch_context': {'accessible_branches': [], 'can_cross_branch': False},
                'purchase_orders': [],
                'medicines': []
            })

        # ADD: Enhanced context with payment integration
        try:
            # Add payment-ready context for invoice forms
            context.update({
                'can_create_payment': True,  # Could be permission-based
                'payment_config': PAYMENT_CONFIG,
                'auto_approve_limit': PAYMENT_CONFIG.get('AUTO_APPROVE_LIMIT', 5000)
            })
            
            # Add quick payment link context if invoice is ready for payment
            if hasattr(self, 'invoice_id') and self.invoice_id:
                from flask import url_for
                context['payment_url'] = url_for('supplier_views.record_payment', invoice_id=self.invoice_id)
                
        except Exception as e:
            current_app.logger.warning(f"Error adding payment context: {str(e)}")
        
        # EXISTING: Add flag to indicate if we have pre-populated PO data (unchanged)
        context['has_po_data'] = self.po_id is not None

        # NEW: If we have a pre-selected PO, add flags for locking supplier and PO
        if self.po_id:
            # Get the supplier_id for this PO from the mapping built earlier
            po_suppliers = context.get('po_suppliers', {})
            locked_supplier_id = po_suppliers.get(str(self.po_id))
            if locked_supplier_id:
                # Only set these flags if we have a valid supplier for the PO
                context['pre_selected_po_id'] = str(self.po_id)
                context['supplier_locked'] = True
                context['locked_supplier_id'] = locked_supplier_id
                current_app.logger.info(f"✅ Locking supplier {locked_supplier_id} for pre-selected PO {self.po_id}")
            else:
                current_app.logger.warning(f"⚠️ No supplier found for PO {self.po_id}, not locking")

        # ADD DEBUG LOGGING HERE (at the end of get_additional_context method):
        current_app.logger.info(f"DEBUG Branch Context Values:")
        current_app.logger.info(f"  branches count: {len(context.get('branches', []))}")
        current_app.logger.info(f"  has_branches: {context.get('has_branches', False)}")
        current_app.logger.info(f"  default_branch_id: {context.get('default_branch_id')}")
        current_app.logger.info(f"  branch_context method: {context.get('branch_context', {}).get('method', 'none')}")
        current_app.logger.info(f"  branch_context accessible_branches: {len(context.get('branch_context', {}).get('accessible_branches', []))}")

        return context

        
    def get_form(self, *args, **kwargs):
        """Get form instance with initial data"""
        form = super().get_form(*args, **kwargs)
        
        # Set currency choices if not already set
        if not form.currency_code.choices:
            form.currency_code.choices = [
                ('INR', 'INR'),
                ('USD', 'USD'),
                ('EUR', 'EUR'),
                # Add other currencies as needed
            ]

        try:
            from flask_login import current_user
            from flask import request, session
            
            # ===== AUTO-SET BRANCH FROM USER CONTEXT =====
            current_app.logger.info("=== BRANCH AUTO-SETUP START ===")
            
            # Get branch from user context
            from app.services.branch_service import get_user_branch_id
            user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
            
            if user_branch_id:
                branch_id_str = str(user_branch_id)
                current_app.logger.info(f"User's branch_id: {branch_id_str}")
                
                # Set as the only choice (hidden from user, auto-selected)
                form.branch_id.choices = [(branch_id_str, 'User Branch')]
                form.branch_id.data = branch_id_str
                
                current_app.logger.info(f"✅ Branch auto-set to: {branch_id_str}")
            else:
                # Fallback: Try to get from context
                context = self.get_additional_context(*args, **kwargs)
                default_branch_id = context.get('default_branch_id')
                
                if default_branch_id:
                    branch_id_str = str(default_branch_id)
                    current_app.logger.info(f"Using default_branch_id from context: {branch_id_str}")
                    
                    form.branch_id.choices = [(branch_id_str, 'Default Branch')]
                    form.branch_id.data = branch_id_str
                    
                    current_app.logger.info(f"✅ Branch set from context: {branch_id_str}")
                else:
                    current_app.logger.error("❌ No branch_id found for user")
                    form.branch_id.choices = [('', 'No Branch')]
            
            current_app.logger.info("=== BRANCH AUTO-SETUP END ===")
            
        except Exception as e:
            current_app.logger.error(f"❌ Error auto-setting branch: {str(e)}", exc_info=True)
            form.branch_id.choices = [('', 'Error')]
        # ===== END BRANCH AUTO-SETUP =====
        
        # ===== NEW: AUTO-POPULATE SUPPLIER-DEPENDENT FIELDS =====
        try:
            from flask import request
            from flask_login import current_user
            
            # Get supplier_id from form data or query params
            supplier_id = request.form.get('supplier_id') or request.args.get('supplier_id')
            
            if supplier_id:
                current_app.logger.info(f"=== AUTO-POPULATING SUPPLIER-DEPENDENT FIELDS for supplier: {supplier_id} ===")
                
                with get_db_session(read_only=True) as session:
                    # Get supplier details
                    supplier = session.query(Supplier).filter_by(
                        supplier_id=uuid.UUID(supplier_id),
                        hospital_id=current_user.hospital_id
                    ).first()
                    
                    if supplier:
                        # REQUIREMENT 3: Default currency from supplier's country
                        supplier_currency = supplier.currency_code or 'INR'
                        form.currency_code.data = supplier_currency
                        current_app.logger.info(f"âœ… Set currency from supplier: {supplier_currency}")
                        
                        # REQUIREMENT 2: Get exchange rate from CurrencyMaster
                        currency_master = session.query(CurrencyMaster).filter_by(
                            hospital_id=current_user.hospital_id,
                            currency_code=supplier_currency,
                            is_active=True
                        ).first()
                        
                        if currency_master:
                            form.exchange_rate.data = float(currency_master.exchange_rate)
                            current_app.logger.info(f"âœ… Set exchange rate from CurrencyMaster: {currency_master.exchange_rate}")
                        else:
                            form.exchange_rate.data = 1.0
                            current_app.logger.warning(f"⚠️ No CurrencyMaster entry found for {supplier_currency}, defaulting to 1.0")
                        
                        # REQUIREMENT 4: Default place of supply from supplier state
                        if supplier.state_code:
                            form.place_of_supply.data = supplier.state_code
                            current_app.logger.info(f"âœ… Set place of supply from supplier state: {supplier.state_code}")
                            
                            # REQUIREMENT 5: Determine if interstate
                            hospital = session.query(Hospital).filter_by(
                                hospital_id=current_user.hospital_id
                            ).first()
                            
                            if hospital and hospital.state_code:
                                # Get branch state code (user's branch)
                                branch = None
                                if form.branch_id.data:
                                    branch = session.query(Branch).filter_by(
                                        branch_id=uuid.UUID(form.branch_id.data),
                                        hospital_id=current_user.hospital_id
                                    ).first()
                                
                                # Use branch state if available, otherwise hospital state
                                branch_state_code = branch.state_code if (branch and branch.state_code) else hospital.state_code
                                
                                is_interstate = supplier.state_code != branch_state_code
                                form.is_interstate.data = is_interstate
                                
                                current_app.logger.info(f"âœ… Interstate check: Branch/Hospital={branch_state_code}, Supplier={supplier.state_code}, Interstate={is_interstate}")
                        
        except Exception as e:
            current_app.logger.error(f"âŒ Error auto-populating supplier fields: {str(e)}", exc_info=True)
        # ===== END AUTO-POPULATE SUPPLIER-DEPENDENT FIELDS =====

        # ===== SET FORM CHOICES FROM CONTEXT =====
        try:
            current_app.logger.info("=== SETTING FORM CHOICES ===")
            
            # Get additional context (which includes suppliers and POs)
            context = self.get_additional_context(*args, **kwargs)
            
            # Set choices for supplier dropdown
            suppliers = context.get('suppliers', [])
            if suppliers:
                form.supplier_id.choices = [('', 'Select Supplier')] + [
                    (str(supplier['supplier_id']), supplier['supplier_name']) 
                    for supplier in suppliers
                ]
                current_app.logger.info(f"✅ Set {len(suppliers)} supplier choices")
            else:
                form.supplier_id.choices = [('', 'No Suppliers Available')]
                current_app.logger.warning("⚠️ No suppliers found in context")
            
            # Set choices for purchase order dropdown
            # Handle three scenarios:
            # 1. Coming from PO (po_id in URL) - fetch that specific PO
            # 2. Supplier selected - fetch available POs for that supplier  
            # 3. Regular form load - start empty, populate via JS

            from flask import request
            po_id_param = request.args.get('po_id') or self.po_id
            current_supplier_id = form.supplier_id.data or request.args.get('supplier_id')

            if po_id_param:
                # ✅ SCENARIO 2: Coming from PO list/view action button - auto-load everything
                try:
                    from app.services.supplier_service import get_purchase_order_by_id, get_supplier_by_id
                    import uuid as uuid_lib
                    
                    po = get_purchase_order_by_id(
                        po_id=uuid_lib.UUID(po_id_param),
                        hospital_id=current_user.hospital_id
                    )
                    
                    if po:
                        po_number = po.get('po_number', 'Unknown PO')
                        
                        # ✅ Set PO dropdown with ONLY this PO (locked)
                        # CRITICAL: Include empty first option because template uses [1:] to skip it
                        form.po_id.choices = [
                            ('', 'Select Purchase Order'),  # Empty first option (skipped by template)
                            (str(po.get('po_id')), po_number)  # The actual PO option
                        ]
                        form.po_id.data = str(po.get('po_id'))
                        
                        # ✅ CRITICAL: Lock supplier dropdown to PO's supplier
                        if po.get('supplier_id'):
                            supplier_id_str = str(po.get('supplier_id'))
                            form.supplier_id.data = supplier_id_str
                            
                            # Fetch supplier details to display in dropdown
                            try:
                                supplier = get_supplier_by_id(
                                    supplier_id=uuid_lib.UUID(supplier_id_str),
                                    hospital_id=current_user.hospital_id
                                )
                                if supplier:
                                    # Lock supplier choices to only this supplier
                                    form.supplier_id.choices = [
                                        ('', 'Select Supplier'),  # Empty first option (skipped by template)
                                        (supplier_id_str, supplier.get('supplier_name', 'Unknown Supplier'))
                                    ]
                                    
                                    # ✅ NEW: Populate supplier GSTIN immediately
                                    if supplier.get('gst_registration_number'):
                                        form.supplier_gstin.data = supplier.get('gst_registration_number')
                                        current_app.logger.info(f"✅ Set supplier GSTIN: {supplier.get('gst_registration_number')}")
                                    
                                    # ✅ NEW: Populate place of supply from supplier state
                                    if supplier.get('state_code'):
                                        form.place_of_supply.data = supplier.get('state_code')
                                        current_app.logger.info(f"✅ Set place of supply: {supplier.get('state_code')}")
                                    
                                    current_app.logger.info(f"✅ Locked supplier to {supplier.get('supplier_name')} from PO")
                            except Exception as supplier_error:
                                current_app.logger.warning(f"Could not fetch supplier: {str(supplier_error)}")
                                # Fallback: still set data but with generic choice
                                # CRITICAL: Include empty first option because template uses [1:] to skip it
                                form.supplier_id.choices = [
                                    ('', 'Select Supplier'),  # Empty first option (skipped by template)
                                    (supplier_id_str, 'Supplier from PO')
                                ]
                        
                        # ✅ Mark context to indicate this is from PO URL (for template)
                        context = context or {}
                        context['is_from_po_url'] = True
                        context['po_number'] = po_number
                        
                        current_app.logger.info(f"✅ SCENARIO 2: Auto-loading from PO {po_number} - dropdown locked, will auto-populate line items")
                    else:
                        form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
                        current_app.logger.warning(f"⚠️ PO {po_id_param} not found")
                        
                except Exception as po_error:
                    current_app.logger.error(f"Error fetching PO from URL: {str(po_error)}")
                    form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
                    
            elif current_supplier_id:
                # ✅ SCENARIO 1: Normal flow - supplier selected, populate filtered POs
                try:
                    from app.services.supplier_service import search_purchase_orders
                    from app.services.branch_service import get_user_branch_id
                    from app.services.database_service import get_db_session
                    from app.models.transaction import SupplierInvoice
                    from sqlalchemy import func
                    import uuid as uuid_lib
                    
                    user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
                    
                    # ✅ Search for APPROVED POs only (not draft, not cancelled)
                    po_results = search_purchase_orders(
                        hospital_id=current_user.hospital_id,
                        supplier_id=uuid_lib.UUID(current_supplier_id),
                        status='approved',  # ✅ Only approved POs
                        branch_id=user_branch_id,
                        page=1,
                        per_page=100
                    )
                    
                    po_choices = [('', 'Select Purchase Order (Optional)')]
                    
                    # ✅ Filter out fully invoiced POs, keep partially invoiced ones
                    with get_db_session() as session:
                        for po in po_results.get('results', []):
                            po_id = po.get('po_id')
                            po_total = float(po.get('total_amount', 0))
                            
                            # Calculate total already invoiced (exclude cancelled invoices)
                            invoiced_total = session.query(func.sum(SupplierInvoice.total_amount))\
                                .filter(
                                    SupplierInvoice.po_id == po_id,
                                    SupplierInvoice.hospital_id == current_user.hospital_id,
                                    SupplierInvoice.payment_status != 'cancelled'
                                ).scalar() or 0
                            
                            invoiced_total = float(invoiced_total)
                            remaining = po_total - invoiced_total
                            
                            # ✅ Include if remaining amount > 0 (includes partially invoiced)
                            if remaining > 0.01:
                                po_number = po.get('po_number', 'Unknown')
                                po_date = po.get('po_date')
                                
                                date_str = ''
                                if po_date:
                                    if isinstance(po_date, str):
                                        date_str = po_date[:10]
                                    else:
                                        date_str = po_date.strftime('%Y-%m-%d')
                                
                                # Show remaining amount for partial invoices
                                po_label = f"{po_number} - {date_str} (₹{remaining:,.2f} remaining)"
                                po_choices.append((str(po_id), po_label))
                    
                    form.po_id.choices = po_choices
                    current_app.logger.info(f"✅ SCENARIO 1: Added {len(po_choices) - 1} approved POs for supplier (includes partially invoiced)")
                    
                except Exception as po_error:
                    current_app.logger.error(f"Error fetching POs for supplier: {str(po_error)}")
                    form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
                    
            elif current_supplier_id:
                # SCENARIO 2: Supplier selected (but no PO in URL) - fetch available POs for that supplier
                try:
                    from app.services.supplier_service import search_purchase_orders
                    from app.services.branch_service import get_user_branch_id
                    from app.services.database_service import get_db_session
                    from app.models.transaction import SupplierInvoice
                    from sqlalchemy import func
                    import uuid as uuid_lib
                    
                    user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
                    
                    # Search for approved POs for this supplier
                    po_results = search_purchase_orders(
                        hospital_id=current_user.hospital_id,
                        supplier_id=uuid_lib.UUID(current_supplier_id),
                        status='approved',
                        branch_id=user_branch_id,
                        page=1,
                        per_page=100
                    )
                    
                    purchase_orders = po_results.get('results', [])
                    po_choices = [('', 'Select Purchase Order (Optional)')]
                    
                    # Filter out fully invoiced POs
                    with get_db_session() as session:
                        for po in purchase_orders:
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
                                
                                po_text = f"{po_number} - {po_date_str} (₹{remaining:,.2f} remaining)"
                                po_choices.append((str(po_id), po_text))
                    
                    form.po_id.choices = po_choices
                    current_app.logger.info(f"✅ Added {len(po_choices) - 1} available PO choices for supplier")
                    
                except Exception as po_error:
                    current_app.logger.error(f"Error fetching POs for supplier: {str(po_error)}")
                    form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
                    
            else:
                # SCENARIO 3: No PO in URL and no supplier selected - start empty
                form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
                current_app.logger.info("PO dropdown initialized empty - will be populated when supplier is selected")

            current_app.logger.info(f"✅ Final PO choices count: {len(form.po_id.choices)}")

            # Set currency choices if not already set
            if not form.currency_code.choices:
                form.currency_code.choices = [
                    ('INR', 'INR'),
                    ('USD', 'USD'),
                    ('EUR', 'EUR')
                ]

            # If we have a PO ID for pre-population, do it now - but not if we're coming from an edit
            if self.po_id and request.args.get('edited') != '1':
                self.pre_populate_from_po(form, context)
                # Force reload line items from session after PO pre-population
                session_key = f'supplier_invoice_line_items_{current_user.user_id}'
                if session_key in session:
                    line_items_from_session = session.get(session_key, [])
                    current_app.logger.info(f"✅ Line items in session after PO pre-population: {len(line_items_from_session)}")

        except Exception as e:
            current_app.logger.error(f"❌ Error setting form choices: {str(e)}", exc_info=True)
            # Set minimal fallback choices
            if form.supplier_id.choices is None:
                form.supplier_id.choices = [('', 'Select Supplier')]
            if form.po_id.choices is None:
                form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
        # ===== END SET FORM CHOICES =====

        # CRITICAL FIX: Ensure choices are NEVER None and log what was set
        try:
            # Log current state
            current_app.logger.info(f"🔍 Final form state check:")
            current_app.logger.info(f"   supplier_id.choices type: {type(form.supplier_id.choices)}")
            current_app.logger.info(f"   supplier_id.choices length: {len(form.supplier_id.choices) if form.supplier_id.choices else 'None'}")
            
            # Safety check: If choices are None, set to empty list
            if form.supplier_id.choices is None:
                current_app.logger.error("❌ supplier_id.choices was None, setting to empty list")
                form.supplier_id.choices = [('', 'Select Supplier')]
            elif len(form.supplier_id.choices) == 0:
                current_app.logger.error("❌ supplier_id.choices was empty list, setting default")
                form.supplier_id.choices = [('', 'Select Supplier')]
            else:
                current_app.logger.info(f"✅ supplier_id has {len(form.supplier_id.choices)} choices")
            
            if form.po_id.choices is None:
                current_app.logger.warning("⚠️ po_id.choices was None, setting to empty list")
                form.po_id.choices = [('', 'Select Purchase Order')]
                
            if form.currency_code.choices is None:
                current_app.logger.warning("⚠️ currency_code.choices was None, setting defaults")
                form.currency_code.choices = [('INR', 'INR'), ('USD', 'USD'), ('EUR', 'EUR')]
                
        except Exception as e:
            current_app.logger.error(f"Error in final choices safety check: {str(e)}", exc_info=True)
        
        return form

    
    def pre_populate_from_po(self, form, context=None):
        """
        Pre-populate form data from a purchase order
        
        CORRECTED VERSION: Includes currency, exchange_rate, and notes
        for full backward compatibility with existing functionality.
        
        Now uses the unified get_po_items_with_balance() method for consistency.
        This ensures both the form pre-population and API endpoint use the same logic.
        """
        from flask_login import current_user
        from flask import current_app, session, flash
        from datetime import datetime
        
        try:
            current_app.logger.info(f"Pre-populating form from PO ID: {self.po_id}")
            
            # STEP 1: Check if we already have edited line items in session
            session_key = f'supplier_invoice_line_items_{current_user.user_id}'
            
            if session_key in session and len(session.get(session_key, [])) > 0:
                has_edited_items = False
                for item in session[session_key]:
                    if (item.get('batch_number') != '[ENTER BATCH #]' or 
                        item.get('expiry_date') != 'YYYY-MM-DD'):
                        has_edited_items = True
                        break
                
                if has_edited_items:
                    current_app.logger.info(f"Preserving {len(session[session_key])} edited items")
                    return
            
            # STEP 2: Use unified method to get PO data with balance quantities
            po_data = self.get_po_items_with_balance(
                po_id=self.po_id,
                include_gst_fields=True
            )
            
            if not po_data.get('success'):
                error_msg = po_data.get('error', 'Unknown error')
                current_app.logger.warning(f"Failed to get PO data: {error_msg}")
                flash(f"Error loading purchase order: {error_msg}", "error")
                return
            
            current_app.logger.info(f"Found PO {po_data.get('po_number')}")
            
            # STEP 3: Populate form fields from PO data
            form.po_id.data = self.po_id
            
            # Supplier
            supplier_id = po_data.get('supplier_id')
            if supplier_id:
                form.supplier_id.data = supplier_id
            
            # GST fields
            if po_data.get('supplier_gstin'):
                form.supplier_gstin.data = po_data.get('supplier_gstin')
            
            if po_data.get('place_of_supply'):
                form.place_of_supply.data = po_data.get('place_of_supply')
            
            if po_data.get('is_interstate') is not None:
                form.is_interstate.data = po_data.get('is_interstate')
            
            # ✅ CRITICAL FOR BACKWARD COMPATIBILITY: Currency fields
            if po_data.get('currency_code'):
                form.currency_code.data = po_data.get('currency_code')
                form.exchange_rate.data = po_data.get('exchange_rate', 1.0)
            
            # ✅ CRITICAL FOR BACKWARD COMPATIBILITY: Notes field
            if po_data.get('notes'):
                form.notes.data = po_data.get('notes')
            
            # Standard fields
            form.invoice_date.data = datetime.now().date()
            form.supplier_invoice_number.data = ""
            
            # STEP 4: Process line items for form
            line_items = []
            batch_placeholder = "[ENTER BATCH #]"
            expiry_placeholder = "YYYY-MM-DD"
            
            po_line_items = po_data.get('line_items', [])
            
            if not po_line_items:
                current_app.logger.warning("No items with balance remaining")
                flash("All items fully invoiced. No balance remaining.", "warning")
                return
            
            from app.services.supplier_service import calculate_gst_values
            
            for item in po_line_items:
                try:
                    is_interstate = form.is_interstate.data if hasattr(
                        form, 'is_interstate'
                    ) and form.is_interstate.data else False
                    
                    gst_calcs = calculate_gst_values(
                        quantity=item['units'],
                        unit_rate=item['pack_purchase_price'],
                        gst_rate=item['gst_rate'],
                        discount_percent=item['discount_percent'],
                        is_free_item=False,
                        is_interstate=is_interstate,
                        conversion_factor=item['units_per_pack']
                    )
                    
                    line_item = {
                        'medicine_id': item['medicine_id'],
                        'medicine_name': item['medicine_name'],
                        'units': item['units'],
                        'pack_purchase_price': item['pack_purchase_price'],
                        'pack_mrp': item['pack_mrp'],
                        'units_per_pack': item['units_per_pack'],
                        'hsn_code': item['hsn_code'],
                        'gst_rate': item['gst_rate'],
                        'cgst_rate': item['cgst_rate'],
                        'sgst_rate': item['sgst_rate'],
                        'igst_rate': item['igst_rate'],
                        'batch_number': batch_placeholder,
                        'expiry_date': expiry_placeholder,
                        'is_free_item': False,
                        'discount_percent': item['discount_percent'],
                        'cgst': float(gst_calcs.get('cgst_amount', 0)),
                        'sgst': float(gst_calcs.get('sgst_amount', 0)),
                        'igst': float(gst_calcs.get('igst_amount', 0)),
                        'total_gst': float(gst_calcs.get('total_gst_amount', 0)),
                        'line_total': float(gst_calcs.get('line_total', 0)),
                        'taxable_amount': float(gst_calcs.get('taxable_amount', 0)),
                        'unit_price': float(gst_calcs.get('sub_unit_price', 0))
                    }
                    
                    line_items.append(line_item)
                
                except Exception as item_error:
                    current_app.logger.error(f"Error processing line item: {str(item_error)}")
                    continue
            
            # STEP 5: Store in session
            session[session_key] = line_items
            current_app.logger.info(f"Saved {len(line_items)} items to session")
            
            flash(
                f"Form pre-populated with {len(line_items)} items (balance quantities). "
                f"Please review Batch Numbers and Expiry Dates.", 
                "info"
            )
        
        except Exception as e:
            current_app.logger.error(f"Error in pre_populate_from_po: {str(e)}", exc_info=True)
            flash(f"Error pre-populating form: {str(e)}", "error")
    

    def get_po_items_with_balance(self, po_id, include_gst_fields=True):
        """
        UNIFIED METHOD: Get PO items with balance quantities and ALL PO fields
        
        CORRECTED VERSION: Includes currency_code, exchange_rate, and notes
        for full backward compatibility with existing functionality.
        
        This method consolidates ALL business logic for loading PO data:
        - Calculates balance quantities (PO qty - invoiced qty)
        - Retrieves supplier GST information
        - Retrieves currency and exchange rate from PO
        - Retrieves notes from PO
        - Skips fully invoiced items
        - Returns properly formatted data for both API and form pre-population
        
        Used by:
        1. API endpoint: /supplier/api/purchase-order/<po_id>/load-items
        2. Form pre-population: When PO is selected from dropdown
        
        Args:
            po_id (str): Purchase Order ID (UUID as string)
            include_gst_fields (bool): Whether to include supplier GST fields
            
        Returns:
            dict: {
                'success': bool,
                'po_number': str,
                'supplier_id': str,
                'supplier_name': str,
                'line_items': list[dict],  # Balance quantities only
                'po_branch_id': str,
                'currency_code': str,  # ✅ ADDED for backward compatibility
                'exchange_rate': float,  # ✅ ADDED for backward compatibility
                'notes': str,  # ✅ ADDED for backward compatibility
                'supplier_gstin': str (if include_gst_fields),
                'place_of_supply': str (if include_gst_fields),
                'is_interstate': bool (if include_gst_fields),
                'error': str (if error occurred)
            }
        """
        from flask_login import current_user
        from flask import current_app
        from app.services.supplier_service import (
            get_purchase_order_by_id, 
            search_supplier_invoices
        )
        from app.models.master import Supplier, Hospital
        from app.services.database_service import get_db_session
        import uuid
        
        try:
            current_app.logger.info(f"=== GET PO ITEMS WITH BALANCE: PO {po_id} ===")
            
            # STEP 1: Get Purchase Order
            po = get_purchase_order_by_id(
                po_id=uuid.UUID(po_id),
                hospital_id=current_user.hospital_id
            )
            
            if not po:
                return {
                    'success': False,
                    'error': 'Purchase order not found'
                }
            
            po_number = po.get('po_number', 'N/A')
            current_app.logger.info(f"Found PO: {po_number}")
            
            # STEP 2: Calculate Balance Quantities
            invoiced_quantities = {}

            try:
                po_uuid = uuid.UUID(po_id) if isinstance(po_id, str) else po_id
                
                # First, get list of invoice IDs for this PO
                invoices_result = search_supplier_invoices(
                    hospital_id=current_user.hospital_id,
                    po_id=po_uuid,
                    page=1,
                    per_page=1000
                )
                
                existing_invoices = invoices_result.get('invoices', [])
                
                if existing_invoices:
                    current_app.logger.info(
                        f"Found {len(existing_invoices)} existing invoice(s) for PO {po_number}"
                    )
                    
                    # ✅ FIX: Fetch FULL invoice details (with line items) for each invoice
                    from app.services.supplier_service import get_supplier_invoice_by_id
                    
                    for invoice_summary in existing_invoices:
                        # Skip cancelled invoices
                        if invoice_summary.get('payment_status') == 'cancelled':
                            current_app.logger.info(
                                f"Skipping cancelled invoice {invoice_summary.get('supplier_invoice_number')}"
                            )
                            continue
                        
                        # ✅ Get FULL invoice with line items
                        invoice_id = invoice_summary.get('invoice_id')
                        if not invoice_id:
                            current_app.logger.warning(
                                f"Invoice {invoice_summary.get('supplier_invoice_number')} has no ID"
                            )
                            continue
                        
                        try:
                            # Fetch full invoice details
                            full_invoice = get_supplier_invoice_by_id(
                                invoice_id=uuid.UUID(invoice_id) if isinstance(invoice_id, str) else invoice_id,
                                hospital_id=current_user.hospital_id
                            )
                            
                            if not full_invoice:
                                current_app.logger.warning(
                                    f"Could not fetch full invoice {invoice_id}"
                                )
                                continue
                            
                            invoice_lines = full_invoice.get('line_items', [])
                            
                            current_app.logger.info(
                                f"Invoice {full_invoice.get('supplier_invoice_number')}: "
                                f"{len(invoice_lines)} line items"
                            )
                            
                            if not invoice_lines:
                                current_app.logger.warning(
                                    f"Invoice {full_invoice.get('supplier_invoice_number')} "
                                    f"has no line_items in database!"
                                )
                                continue
                            
                            # Process line items
                            for line in invoice_lines:
                                med_id = str(line.get('medicine_id'))
                                qty = float(line.get('units', 0))
                                
                                current_app.logger.info(
                                    f"  Line: {line.get('medicine_name', 'Unknown')} - {qty} units"
                                )
                                
                                if med_id in invoiced_quantities:
                                    invoiced_quantities[med_id] += qty
                                else:
                                    invoiced_quantities[med_id] = qty
                        
                        except Exception as invoice_error:
                            current_app.logger.error(
                                f"Error fetching invoice {invoice_id}: {str(invoice_error)}"
                            )
                            continue
                    
                    current_app.logger.info(
                        f"✅ Final invoiced quantities: {invoiced_quantities}"
                    )
                else:
                    current_app.logger.info("No existing invoices found")

            except Exception as inv_error:
                current_app.logger.error(
                    f"Error checking invoices: {str(inv_error)}", 
                    exc_info=True
                )
            
            # STEP 3: Get Supplier GST Information
            supplier_gstin = None
            place_of_supply = None
            is_interstate = False

            if include_gst_fields:
                supplier_id = po.get('supplier_id')
                
                if supplier_id:
                    try:
                        # ✅ FIX: Ensure supplier_id is UUID object (handle both string and UUID)
                        if isinstance(supplier_id, str):
                            supplier_uuid = uuid.UUID(supplier_id)
                        else:
                            supplier_uuid = supplier_id  # Already a UUID object
                        
                        with get_db_session(read_only=True) as db_session:
                            supplier = db_session.query(Supplier).filter_by(
                                supplier_id=supplier_uuid,  # ✅ FIXED: Use converted UUID
                                hospital_id=current_user.hospital_id
                            ).first()
                            
                            if supplier:
                                supplier_gstin = supplier.gst_registration_number
                                place_of_supply = supplier.state_code
                                
                                hospital = db_session.query(Hospital).filter_by(
                                    hospital_id=current_user.hospital_id
                                ).first()
                                
                                if hospital and supplier.state_code and hospital.state_code:
                                    is_interstate = (supplier.state_code != hospital.state_code)
                                    current_app.logger.info(
                                        f"Interstate: Supplier={supplier.state_code}, "
                                        f"Hospital={hospital.state_code}, Result={is_interstate}"
                                    )
                    
                    except Exception as supplier_error:
                        current_app.logger.error(f"Error getting supplier GST: {str(supplier_error)}")
            
            # STEP 4: Process Line Items with Balance
            line_items = po.get('line_items', [])
            formatted_items = []
            
            for item in line_items:
                medicine_id = str(item.get('medicine_id'))
                medicine_name = item.get('medicine_name', 'Unknown')
                po_units = float(item.get('units', 0))
                
                invoiced_qty = invoiced_quantities.get(medicine_id, 0)
                balance_qty = po_units - invoiced_qty
                
                current_app.logger.info(
                    f"{medicine_name}: PO={po_units}, Invoiced={invoiced_qty}, Balance={balance_qty}"
                )
                
                if balance_qty <= 0.001:
                    current_app.logger.info(f"Skipping {medicine_name} - fully invoiced")
                    continue
                
                formatted_items.append({
                    'medicine_id': medicine_id,
                    'medicine_name': medicine_name,
                    'units': balance_qty,
                    'units_per_pack': float(item.get('units_per_pack', 1)),
                    'pack_purchase_price': float(item.get('pack_purchase_price', 0)),
                    'pack_mrp': float(item.get('pack_mrp', 0)),
                    'discount_percent': float(item.get('discount_percent', 0)),
                    'hsn_code': item.get('hsn_code'),
                    'gst_rate': float(item.get('gst_rate', 0)),
                    'cgst_rate': float(item.get('cgst_rate', 0)),
                    'sgst_rate': float(item.get('sgst_rate', 0)),
                    'igst_rate': float(item.get('igst_rate', 0)),
                    'branch_id': str(item.get('branch_id')) if item.get('branch_id') else None
                })
            
            current_app.logger.info(f"Returning {len(formatted_items)} items with balance")
            
            # STEP 5: Build response with ALL PO fields
            result = {
                'success': True,
                'po_number': po_number,
                'supplier_id': str(po.get('supplier_id')),
                'supplier_name': po.get('supplier_name', ''),
                'line_items': formatted_items,
                'po_branch_id': str(po.get('branch_id')) if po.get('branch_id') else None,
                # ✅ CRITICAL FOR BACKWARD COMPATIBILITY
                'currency_code': po.get('currency_code'),
                'exchange_rate': po.get('exchange_rate', 1.0),
                'notes': po.get('notes')
            }
            
            if include_gst_fields:
                result.update({
                    'supplier_gstin': supplier_gstin,
                    'place_of_supply': place_of_supply,
                    'is_interstate': is_interstate
                })
            
            return result
        
        except Exception as e:
            current_app.logger.error(f"Error getting PO items: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }


    def process_line_item_form(self, form, *args, **kwargs):
        """
        Process a line item form submission within the invoice creation form
        UPDATED: Uses centralized GST calculation service
        """
        try:
            # Import necessary modules
            from flask_login import current_user
            from flask import flash, current_app
            
            # Add detailed logging
            current_app.logger.info("===== PROCESS LINE ITEM FORM START =====")
            current_app.logger.info(f"Medicine ID: {form.medicine_id.data}")
            current_app.logger.info(f"Quantity: {form.quantity.data}")
            current_app.logger.info(f"Batch Number: {form.batch_number.data}")
            current_app.logger.info(f"Expiry Date: {form.expiry_date.data}")
            
            # Log kwargs
            current_app.logger.info(f"hospital_state_code from kwargs: {kwargs.get('hospital_state_code')}")
            
            # Get the medicine data
            medicine_id = form.medicine_id.data
            
            with get_db_session(read_only=True) as session:
                # Fetch medicine details
                medicine = session.query(Medicine).filter_by(
                    medicine_id=medicine_id,
                    hospital_id=current_user.hospital_id
                ).first()
                
                if not medicine:
                    current_app.logger.error(f"Medicine not found with ID: {medicine_id}")
                    flash("Medicine not found", "error")
                    return None
                    
                current_app.logger.info(f"Found medicine: {medicine.medicine_name}")
                    
                # Create line item data
                line_item = {
                    'medicine_id': str(medicine.medicine_id),
                    'medicine_name': medicine.medicine_name,
                    'units': float(form.quantity.data),
                    'pack_purchase_price': float(form.pack_purchase_price.data),
                    'pack_mrp': float(form.pack_mrp.data),
                    'units_per_pack': float(form.units_per_pack.data),
                    'is_free_item': form.is_free_item.data if hasattr(form, 'is_free_item') else False,
                    'discount_percent': float(form.discount_percent.data) if form.discount_percent.data else 0,
                    'hsn_code': medicine.hsn_code or '',
                    'gst_rate': float(medicine.gst_rate) if medicine.gst_rate else 0,
                    'batch_number': form.batch_number.data,
                    'expiry_date': form.expiry_date.data.isoformat() if form.expiry_date.data else None,
                }
                
                current_app.logger.info(f"Created basic line item data")
                    
                # Get state codes for interstate calculation
                supplier_state_code = form.place_of_supply.data if hasattr(form, 'place_of_supply') else None
                hospital_state_code = kwargs.get('hospital_state_code', '')
                is_interstate = supplier_state_code != hospital_state_code if (supplier_state_code and hospital_state_code) else False
                
                current_app.logger.info(f"Interstate calculation: supplier={supplier_state_code}, hospital={hospital_state_code}, interstate={is_interstate}")
                
                # Calculate line totals using centralized GST function
                try:
                    from app.services.supplier_service import calculate_gst_values
                    
                    calculations = calculate_gst_values(
                        quantity=line_item['units'],
                        unit_rate=line_item['pack_purchase_price'],
                        gst_rate=line_item['gst_rate'],
                        discount_percent=line_item['discount_percent'],
                        is_free_item=line_item['is_free_item'],
                        is_interstate=is_interstate,
                        conversion_factor=line_item['units_per_pack']
                    )
                    
                    current_app.logger.info(f"GST calculation completed successfully")
                    
                    # Update line item with calculated values using db_mappings
                    line_item.update(calculations.get('db_mappings', {}))
                    
                    # Add additional fields for compatibility
                    line_item['taxable_amount'] = calculations.get('taxable_amount', 0)
                    line_item['cgst'] = calculations.get('cgst_amount', 0)
                    line_item['sgst'] = calculations.get('sgst_amount', 0)
                    line_item['igst'] = calculations.get('igst_amount', 0)
                    line_item['total_gst'] = calculations.get('total_gst_amount', 0)
                    line_item['line_total'] = calculations.get('line_total', 0)
                    line_item['unit_price'] = calculations.get('sub_unit_price', 0)
                    
                    current_app.logger.info("===== PROCESS LINE ITEM FORM SUCCESS =====")
                    return line_item
                    
                except Exception as calc_error:
                    current_app.logger.error(f"Error in GST calculation: {str(calc_error)}", exc_info=True)
                    flash(f"Error calculating GST: {str(calc_error)}", "error")
                    return None
                    
        except Exception as e:
            current_app.logger.error(f"Error in process_line_item_form: {str(e)}", exc_info=True)
            flash(f"Error processing line item: {str(e)}", "error")
            return None
        
    def handle_request(self, *args, **kwargs):
        """Handle GET/POST request - SIMPLIFIED for hidden fields approach"""
        from flask import request, flash, redirect, current_app
        from flask_login import current_user
        
        current_app.logger.info(f"==== SUPPLIER INVOICE HANDLE REQUEST: {request.method} ====")
        
        # Get the main invoice form
        form = self.get_form(*args, **kwargs)
        
        # REMOVE THIS CHECK FOR submit_invoice - it's not in form data when using form.submit()
        if request.method == 'POST':
            current_app.logger.info("===== POST REQUEST DETECTED =====")
            current_app.logger.info(f"Form keys: {list(request.form.keys())}")
            current_app.logger.info(f"medicine_ids from form: {form.medicine_ids.data}")
            
            # CRITICAL FIX: Add selected PO to choices if it exists
            if form.po_id.data and form.po_id.data.strip():
                try:
                    from app.services.supplier_service import get_purchase_order_by_id
                    import uuid as uuid_lib
                    
                    po = get_purchase_order_by_id(
                        po_id=uuid_lib.UUID(form.po_id.data),
                        hospital_id=current_user.hospital_id
                    )
                    
                    if po:
                        # Add this PO to the choices to pass validation
                        po_date_str = ''
                        if po.get('po_date'):
                            po_date = po.get('po_date')
                            po_date_str = po_date.strftime('%Y-%m-%d') if hasattr(po_date, 'strftime') else str(po_date)[:10]
                        
                        po_text = f"{po.get('po_number')} - {po_date_str}"
                        
                        # Check if already in choices
                        existing_choices = [choice[0] for choice in form.po_id.choices]
                        if form.po_id.data not in existing_choices:
                            form.po_id.choices.append((form.po_id.data, po_text))
                            current_app.logger.info(f"✅ Added PO {po.get('po_number')} to choices for validation")
                except Exception as e:
                    current_app.logger.error(f"Error adding PO to choices: {str(e)}")
            
            # Validate form
            if form.validate_on_submit():
                current_app.logger.info("✅ Form validated successfully")
                
                # Check if hidden fields have data
                if not form.medicine_ids.data or not form.medicine_ids.data.strip():
                    flash("No line items found. Please add at least one item to the invoice.", "error")
                    return self.render_form(form, *args, **kwargs)
                
                try:
                    # Process the form - process_form() will parse hidden fields
                    result = self.process_form(form, *args, **kwargs)
                    
                    flash(self.success_message, "success")
                    
                    # Redirect to success URL
                    if callable(self.success_url):
                        return redirect(self.success_url(result))
                    return redirect(self.success_url)
                    
                except Exception as e:
                    current_app.logger.error(f"❌ Error processing invoice: {str(e)}", exc_info=True)
                    flash(f"Error creating invoice: {str(e)}", "error")
                    return self.render_form(form, *args, **kwargs)
            else:
                # Form validation failed
                current_app.logger.error(f"❌ Form validation failed: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        flash(f"{field}: {error}", "error")
                return self.render_form(form, *args, **kwargs)
        
        # GET request
        current_app.logger.info("GET request - rendering form")
        return self.render_form(form, *args, **kwargs)
    
    def get_payment_context_for_invoice(self):
        """Get payment-ready context for invoice that can be paid"""
        try:
            if hasattr(self, 'invoice_id') and self.invoice_id:
                from flask import url_for
                from flask_login import current_user
                
                # Check if invoice is ready for payment
                from app.services.supplier_service import get_supplier_invoice_by_id
                invoice = get_supplier_invoice_by_id(
                    invoice_id=self.invoice_id,
                    hospital_id=current_user.hospital_id
                )
                
                if invoice and invoice.get('payment_status') in ['unpaid', 'partial']:
                    return {
                        'can_create_payment': True,
                        'payment_url': url_for('supplier_views.record_payment', invoice_id=self.invoice_id),
                        'balance_due': float(invoice.get('balance_due', 0)),
                        'supplier_id': str(invoice.get('supplier_id'))
                    }
            
            return {'can_create_payment': False}
            
        except Exception as e:
            current_app.logger.error(f"Error getting payment context for invoice: {str(e)}")
            return {'can_create_payment': False}

    def render_form(self, form, line_item_form=None, line_items=None, *args, **kwargs):
        """Specialized render method for supplier invoice form, including line items"""
        
        # Import necessary modules
        from flask import render_template, current_app
        from app.utils.menu_utils import get_menu_items
        
        # Get base context from parent class's additional_context method
        context = {}
        if self.additional_context:
            try:
                current_app.logger.info("SupplierInvoiceFormController.render_form - Calling additional_context method")
                context = self.additional_context(*args, **kwargs)
                current_app.logger.info(f"SupplierInvoiceFormController.render_form - additional_context returned keys: {context.keys()}")
            except Exception as e:
                current_app.logger.error(f"Error getting additional context: {str(e)}")
        
        # Add form to context
        context['form'] = form
        
        # Add page title if defined
        if self.page_title:
            context['page_title'] = self.page_title

        # Add line item form and items if provided
        if line_item_form is not None:
            context['line_item_form'] = line_item_form
        
        if line_items is not None:
            context['line_items'] = line_items
        
        # Add menu items
        from flask_login import current_user
        from app.utils.menu_utils import generate_menu_for_role
        context['menu_items'] = generate_menu_for_role(getattr(current_user, 'entity_type', 'staff')) if 'menu_items' not in context else context['menu_items']
        
        current_app.logger.info(f"SupplierInvoiceFormController.render_form - Final context keys: {context.keys()}")
        
        # Render the template with context
        return render_template(self.template_path, **context)


class SupplierInvoiceEditController(FormController):
    """Dedicated controller for supplier invoice editing following centralized framework"""
    
    def __init__(self, invoice_id):
        self.invoice_id = invoice_id
        
        from app.forms.supplier_forms import SupplierInvoiceEditForm
        super().__init__(
            form_class=SupplierInvoiceEditForm,
            template_path='supplier/edit_supplier_invoice.html',
            success_url=self._get_success_url,
            success_message="Supplier invoice updated successfully",
            page_title="Edit Supplier Invoice",
            additional_context=self.get_additional_context
        )
    
    def _get_success_url(self, result):
        """Generate success URL - USES UNIVERSAL ENGINE VIEW"""
        from flask import url_for
        return url_for('universal_views.universal_detail_view', 
                      entity_type='supplier_invoices', 
                      item_id=self.invoice_id)
    
    def get_success_message(self, result):
        base_message = "Supplier invoice created successfully"
        from flask import url_for
        # Add payment link if invoice can be paid
        if result and result.get('invoice_id'):
            invoice_id = result.get('invoice_id')
            payment_url = url_for('supplier_views.record_payment', invoice_id=invoice_id)
            return f'{base_message}<br><small><a href="{payment_url}" class="alert-link">Create Payment →</a></small>'
        
        return base_message

    def get_additional_context(self, *args, **kwargs):
        """Get additional context for template - ENHANCED with branch filtering"""
        context = {}
        try:
            from app.services.database_service import get_db_session
            from app.models.master import Supplier, Medicine
            from flask_login import current_user

            # NEW: Get branch context for filtering
            try:
                from app.services.permission_service import get_user_branch_context
                branch_context = get_user_branch_context(
                    current_user.user_id,
                    current_user.hospital_id,
                    'supplier_invoice'
                )
                context['branch_context'] = branch_context
            except Exception as e:
                current_app.logger.warning(f"Could not get branch context: {str(e)}")
                branch_context = {'accessible_branches': [], 'can_cross_branch': False}
                context['branch_context'] = branch_context
            
            with get_db_session(read_only=True) as session:
                # ENHANCED: Get suppliers with branch filtering for dropdown
                all_suppliers = session.query(Supplier).filter_by(
                    hospital_id=current_user.hospital_id,
                    status='active'
                ).all()
                
                # Filter suppliers based on branch access
                accessible_suppliers = []
                if current_user.user_id == '7777777777':  # PRESERVE: Testing bypass
                    accessible_suppliers = all_suppliers
                else:
                    accessible_branch_ids = [b['branch_id'] for b in branch_context.get('accessible_branches', [])]
                    for supplier in all_suppliers:
                        if (branch_context.get('can_cross_branch', False) or 
                            not supplier.branch_id or  # No branch restriction
                            str(supplier.branch_id) in accessible_branch_ids):
                            accessible_suppliers.append(supplier)
                
                context['suppliers'] = accessible_suppliers
                
                # EXISTING: Get medicines for line items (unchanged)
                medicines = session.query(Medicine).filter_by(
                    hospital_id=current_user.hospital_id,
                    status='active'
                ).order_by(Medicine.medicine_name).all()
                
                # Add medicines to context for template
                context['medicines'] = medicines

                # Add INDIAN_STATES for Place of Supply dropdown
                from app.config.core_definitions import INDIAN_STATES
                context['INDIAN_STATES'] = INDIAN_STATES

                # Add hospital state code for interstate calculation
                from app.models.master import Hospital
                hospital = session.query(Hospital).filter_by(
                    hospital_id=current_user.hospital_id
                ).first()
                context['hospital_state_code'] = hospital.state_code if hospital else '29'

                # Add current date for display
                from datetime import date
                context['current_date'] = date.today()
                context['today'] = date.today()

                # Add invoice_id for template
                context['invoice_id'] = self.invoice_id

                # Get invoice status for badge display
                try:
                    from app.services.supplier_service import get_supplier_invoice_by_id
                    invoice = get_supplier_invoice_by_id(
                        invoice_id=uuid.UUID(self.invoice_id),
                        hospital_id=current_user.hospital_id
                    )
                    context['invoice_status'] = invoice.get('payment_status', 'unpaid') if invoice else 'unpaid'
                except Exception as e:
                    current_app.logger.warning(f"Could not get invoice status: {str(e)}")
                    context['invoice_status'] = 'unpaid'

        except Exception as e:
            current_app.logger.error(f"Error getting context: {str(e)}")
            from datetime import date
            context.update({
                'suppliers': [],
                'medicines': [],
                'branch_context': {'accessible_branches': [], 'can_cross_branch': False},
                'INDIAN_STATES': [],
                'hospital_state_code': '29',
                'current_date': date.today(),
                'today': date.today(),
                'invoice_id': self.invoice_id,
                'invoice_status': 'unpaid'
            })

        return context
    
    def get_form(self, *args, **kwargs):
        """Get form with populated data - FIXED choices initialization"""
        form = super().get_form(*args, **kwargs)

        # CRITICAL: For edit, pre-populate supplier_id before setting choices
        # This allows _set_form_choices to filter POs by supplier
        if self.invoice_id:
            try:
                from app.services.supplier_service import get_supplier_invoice_by_id
                from flask_login import current_user
                import uuid

                invoice = get_supplier_invoice_by_id(
                    invoice_id=uuid.UUID(self.invoice_id),
                    hospital_id=current_user.hospital_id,
                    include_payments=False
                )

                if invoice:
                    # Pre-set supplier_id so PO filtering works
                    form.supplier_id.data = str(invoice.get('supplier_id'))
            except Exception as e:
                current_app.logger.warning(f"Could not pre-populate supplier_id: {str(e)}")

        # Set choices (will now filter POs by the pre-populated supplier)
        self._set_form_choices(form)

        # Populate with all invoice data (including line items)
        self._populate_form_with_invoice_data(form)

        return form
    
    def _set_form_choices(self, form):
        """Set form choices - centralized method with PO filtering"""
        try:
            from flask_login import current_user
            from app.services.supplier_service import search_purchase_orders
            from app.services.branch_service import get_user_branch_id
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierInvoice
            from sqlalchemy import func
            import uuid
            
            # Get suppliers
            context = self.get_additional_context()
            suppliers = context.get('suppliers', [])
            form.supplier_id.choices = [('', 'Select Supplier')] + [
                (str(s.supplier_id), s.supplier_name) for s in suppliers
            ]
            
            # Set currency choices
            form.currency_code.choices = [
                ('INR', 'INR'),
                ('USD', 'USD'),
                ('EUR', 'EUR')
            ]
            
            # Set PO choices - filtered by current supplier if selected
            form.po_id.choices = [('', 'Select Purchase Order (Optional)')]

            # Get current supplier from form data
            current_supplier_id = form.supplier_id.data

            # CRITICAL: For edit mode, ensure the linked PO is always included
            linked_po_id = None
            if hasattr(self, 'invoice_id') and self.invoice_id:
                try:
                    from app.services.supplier_service import get_supplier_invoice_by_id
                    invoice = get_supplier_invoice_by_id(
                        invoice_id=uuid.UUID(self.invoice_id),
                        hospital_id=current_user.hospital_id,
                        include_payments=False
                    )
                    if invoice and invoice.get('po_id'):
                        linked_po_id = str(invoice.get('po_id'))
                except Exception as e:
                    current_app.logger.warning(f"Could not fetch linked PO: {str(e)}")

            if current_supplier_id:
                try:
                    # Get user's branch for filtering
                    user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)

                    # Search for approved POs for this supplier
                    po_results = search_purchase_orders(
                        hospital_id=current_user.hospital_id,
                        supplier_id=uuid.UUID(current_supplier_id),
                        status='approved',
                        branch_id=user_branch_id,
                        page=1,
                        per_page=100
                    )

                    # Collect PO choices
                    po_choices_added = set()

                    # Filter out fully invoiced POs
                    with get_db_session() as session:
                        for po in po_results.get('results', []):
                            po_id = po.get('po_id')
                            po_total = float(po.get('total_amount', 0))

                            # Calculate total already invoiced against this PO
                            invoiced_total = session.query(func.sum(SupplierInvoice.total_amount))\
                                .filter(
                                    SupplierInvoice.po_id == po_id,
                                    SupplierInvoice.hospital_id == current_user.hospital_id,
                                    SupplierInvoice.payment_status != 'cancelled'
                                ).scalar() or 0

                            invoiced_total = float(invoiced_total)
                            remaining = po_total - invoiced_total

                            # Include if there's remaining amount OR if it's the linked PO
                            if remaining > 0.01 or str(po_id) == linked_po_id:
                                po_number = po.get('po_number', 'Unknown')
                                po_date = po.get('po_date')

                                # Format date
                                date_str = ''
                                if po_date:
                                    if isinstance(po_date, str):
                                        date_str = po_date[:10]
                                    else:
                                        date_str = po_date.strftime('%Y-%m-%d')

                                # Create label with remaining amount
                                if str(po_id) == linked_po_id:
                                    po_label = f"{po_number} - {date_str} (Linked)"
                                else:
                                    po_label = f"{po_number} - {date_str} (₹{remaining:,.2f} remaining)"

                                form.po_id.choices.append((str(po_id), po_label))
                                po_choices_added.add(str(po_id))

                        # CRITICAL: If linked PO not found in results, fetch it directly
                        if linked_po_id and linked_po_id not in po_choices_added:
                            from app.models.transaction import PurchaseOrderHeader
                            linked_po = session.query(PurchaseOrderHeader).filter_by(
                                po_id=uuid.UUID(linked_po_id),
                                hospital_id=current_user.hospital_id
                            ).first()

                            if linked_po:
                                po_date_str = linked_po.po_date.strftime('%Y-%m-%d') if linked_po.po_date else ''
                                po_label = f"{linked_po.po_number} - {po_date_str} (Linked)"
                                form.po_id.choices.append((linked_po_id, po_label))
                                current_app.logger.info(f"Added linked PO {linked_po.po_number} to choices")

                    current_app.logger.info(f"Set {len(form.po_id.choices) - 1} available PO choices for supplier {current_supplier_id}")

                except Exception as po_error:
                    current_app.logger.warning(f"Error filtering POs: {str(po_error)}")
                    # Fallback - keep empty PO list
                    pass
            
            current_app.logger.debug(f"Set {len(suppliers)} supplier choices and {len(form.po_id.choices)} PO choices")
            
        except Exception as e:
            current_app.logger.error(f"Error setting form choices: {str(e)}")
            # Set minimal choices to prevent None error
            form.supplier_id.choices = [('', 'Select Supplier')]
            form.currency_code.choices = [('INR', 'INR')]
            form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
    
    def _populate_form_with_invoice_data(self, form):
        """Populate form with existing invoice data"""
        try:
            from app.services.supplier_service import get_supplier_invoice_by_id
            from flask_login import current_user
            import uuid
            
            invoice = get_supplier_invoice_by_id(
                invoice_id=uuid.UUID(self.invoice_id),
                hospital_id=current_user.hospital_id,
                include_payments=True
            )
            
            if not invoice:
                raise ValueError(f"Supplier invoice with ID {self.invoice_id} not found")
            
            # Check if invoice can be edited
            self._validate_invoice_edit_eligibility(invoice)
            
            # Populate header fields
            form.supplier_invoice_number.data = invoice.get('supplier_invoice_number')
            form.invoice_date.data = invoice.get('invoice_date')
            form.supplier_id.data = str(invoice.get('supplier_id'))

            # Fetch related data from database (supplier GSTIN and PO number)
            try:
                from app.services.database_service import get_db_session
                from app.models.master import Supplier
                from app.models.transaction import PurchaseOrderHeader

                with get_db_session(read_only=True) as session:
                    # Fetch supplier GSTIN
                    supplier_gstin = invoice.get('supplier_gstin')
                    if not supplier_gstin and invoice.get('supplier_id'):
                        supplier = session.query(Supplier).filter_by(
                            supplier_id=invoice.get('supplier_id'),
                            hospital_id=current_user.hospital_id
                        ).first()
                        if supplier:
                            supplier_gstin = supplier.gst_registration_number

                    form.supplier_gstin.data = supplier_gstin

                    # Set PO ID in form (for form choices to match)
                    form.po_id.data = str(invoice.get('po_id')) if invoice.get('po_id') else ''

            except Exception as e:
                current_app.logger.warning(f"Could not fetch related data: {str(e)}")
                form.supplier_gstin.data = invoice.get('supplier_gstin')
                form.po_id.data = str(invoice.get('po_id')) if invoice.get('po_id') else ''
            form.place_of_supply.data = invoice.get('place_of_supply')
            form.due_date.data = invoice.get('due_date')
            form.reverse_charge.data = invoice.get('reverse_charge', False)
            form.itc_eligible.data = invoice.get('itc_eligible', True)
            form.currency_code.data = invoice.get('currency_code', 'INR')
            form.exchange_rate.data = invoice.get('exchange_rate', 1.0)
            form.notes.data = invoice.get('notes')
            
            # Determine if interstate
            hospital_state = self._get_hospital_state_code()
            supplier_state = invoice.get('place_of_supply')
            form.is_interstate.data = (hospital_state != supplier_state) if (hospital_state and supplier_state) else False
            
            # Clear existing line item entries
            while len(form.line_items.entries) > 0:
                form.line_items.pop_entry()
            
            # Populate line items
            line_items_data = invoice.get('line_items', [])
            
            for line_data in line_items_data:
                form.line_items.append_entry({
                    'medicine_id': str(line_data.get('medicine_id')),
                    'medicine_name': line_data.get('medicine_name'),
                    'batch_number': line_data.get('batch_number'),
                    'expiry_date': line_data.get('expiry_date'),
                    'quantity': float(line_data.get('units', 0)),
                    'pack_purchase_price': float(line_data.get('pack_purchase_price', 0)),
                    'pack_mrp': float(line_data.get('pack_mrp', 0)),
                    'units_per_pack': float(line_data.get('units_per_pack', 1)),
                    'discount_percent': float(line_data.get('discount_percent', 0)),
                    'is_free_item': line_data.get('is_free_item', False),
                    'hsn_code': line_data.get('hsn_code', ''),
                    'gst_rate': float(line_data.get('gst_rate', 0)),
                    'manufacturing_date': line_data.get('manufacturing_date'),
                    'itc_eligible': line_data.get('itc_eligible', True)
                })
            
            current_app.logger.info(f"Populated form with {len(line_items_data)} line items for invoice: {invoice.get('supplier_invoice_number')}")
            
        except Exception as e:
            current_app.logger.error(f"Error populating form: {str(e)}")
            raise
    
    def _validate_invoice_edit_eligibility(self, invoice):
        """Check if invoice can be edited"""
        if invoice.get('payment_status') == 'cancelled':
            raise ValueError('Cancelled invoices cannot be edited')
        
        if invoice.get('payment_status') == 'paid':
            raise ValueError('Paid invoices cannot be edited. Please create a credit note instead.')
        
        # Check if invoice has payments
        payments = invoice.get('payments', [])
        if payments and len(payments) > 0:
            raise ValueError('Invoices with recorded payments cannot be edited. Please create a credit note or adjustment.')
    
    def _get_hospital_state_code(self):
        """Get hospital state code for interstate calculation"""
        try:
            from app.services.database_service import get_db_session
            from app.models.master import Hospital
            from flask_login import current_user
            
            with get_db_session(read_only=True) as session:
                hospital = session.query(Hospital).filter_by(
                    hospital_id=current_user.hospital_id
                ).first()
                return hospital.state_code if hospital else None
        except Exception as e:
            current_app.logger.error(f"Error getting hospital state: {str(e)}")
            return None
    
    def validate_line_items(self, line_items_data):
        """Custom validation for line items"""
        if not line_items_data:
            raise ValueError("At least one line item is required")
        
        for idx, item in enumerate(line_items_data):
            line_num = idx + 1
            
            # Required field validation
            if not item.get('batch_number') or item.get('batch_number').strip() == '':
                raise ValueError(f"Line {line_num}: Batch number is required")
            
            if not item.get('expiry_date'):
                raise ValueError(f"Line {line_num}: Expiry date is required")
            
            quantity = float(item.get('units', 0))
            price = float(item.get('pack_purchase_price', 0))
            is_free = item.get('is_free_item', False)
            
            # Validate quantity
            if quantity <= 0:
                raise ValueError(f"Line {line_num}: Quantity must be greater than 0")
            
            # Validate price based on free item status
            if is_free:
                if price != 0:
                    current_app.logger.warning(f"Line {line_num}: Free item price adjusted to 0")
                    item['pack_purchase_price'] = 0.0
            else:
                if price <= 0:
                    raise ValueError(f"Line {line_num}: Price must be greater than 0 for non-free items")
    
    def process_form(self, form, *args, **kwargs):
        """Process form submission - ENHANCED with centralized branch validation"""
        try:
            # NEW: Add permission validation using centralized functions
            from app.services.supplier_service import update_supplier_invoice
            from flask_login import current_user
            from app.services.branch_service import validate_entity_branch_access
            from app.services.permission_service import has_branch_permission
            
            # PRESERVE: Testing bypass
            if current_user.user_id != '7777777777':
                try:
                    # Validate user can edit this invoice
                    if not validate_entity_branch_access(
                        current_user.user_id,
                        current_user.hospital_id,
                        self.invoice_id,
                        'supplier_invoice',
                        'edit'
                    ):
                        raise PermissionError("Cannot edit invoice from different branch")
                    
                    # Validate supplier access if supplier changed
                    if form.supplier_id.data:
                        if not validate_entity_branch_access(
                            current_user.user_id,
                            current_user.hospital_id,
                            form.supplier_id.data,
                            'supplier',
                            'view'
                        ):
                            raise PermissionError("Cannot change invoice to supplier from different branch")
                    
                    # Validate PO access if PO is linked
                    if form.po_id.data and form.po_id.data.strip():
                        if not validate_entity_branch_access(
                            current_user.user_id,
                            current_user.hospital_id,
                            form.po_id.data,
                            'purchase_order',
                            'view'
                        ):
                            raise PermissionError("Cannot link invoice to PO from different branch")
                            
                except PermissionError:
                    raise  # Re-raise permission errors
                except Exception as e:
                    current_app.logger.warning(f"Permission validation failed, proceeding: {str(e)}")
            
          
            current_app.logger.info(f"=== SUPPLIER INVOICE EDIT FORM PROCESSING START ===")
            
            # CRITICAL FIX: Re-set choices before processing to avoid validation errors
            self._set_form_choices(form)
            
            # Extract header data (basic validation)
            if not form.supplier_id.data:
                raise ValueError("Supplier is required")
            if not form.invoice_date.data:
                raise ValueError("Invoice Date is required")
            if not form.supplier_invoice_number.data:
                raise ValueError("Invoice Number is required")
            if not form.place_of_supply.data:
                raise ValueError("Place of Supply is required")
            
            invoice_data = {
                'supplier_id': uuid.UUID(form.supplier_id.data),
                'supplier_invoice_number': form.supplier_invoice_number.data,
                'invoice_date': form.invoice_date.data,
                'po_id': uuid.UUID(form.po_id.data) if form.po_id.data else None,
                'supplier_gstin': form.supplier_gstin.data,
                'place_of_supply': form.place_of_supply.data,
                'due_date': form.due_date.data,
                'reverse_charge': form.reverse_charge.data,
                'is_interstate': form.is_interstate.data,
                'itc_eligible': form.itc_eligible.data,
                'currency_code': form.currency_code.data,
                'exchange_rate': float(form.exchange_rate.data),
                'notes': form.notes.data,
                'line_items': []
            }
            
            # Extract line items from hidden comma-separated fields
            line_items_data = self._extract_line_items_from_hidden_fields(form)

            # Custom validation
            self.validate_line_items(line_items_data)
            
            invoice_data['line_items'] = line_items_data
            
            current_app.logger.info(f"Processing invoice edit with {len(line_items_data)} line items")
            
            # Update the invoice
            result = update_supplier_invoice(
                invoice_id=uuid.UUID(self.invoice_id),
                invoice_data=invoice_data,
                hospital_id=current_user.hospital_id,
                current_user_id=current_user.user_id
            )
            
            current_app.logger.info(f"Successfully updated invoice: {result.get('supplier_invoice_number')}")
            return result
            
        except PermissionError as pe:
            current_app.logger.warning(f"Permission denied: {str(pe)}")
            raise  # Re-raise to be handled by form framework
        except Exception as e:
            current_app.logger.error(f"Error processing invoice edit: {str(e)}")
            raise
    
    def handle_request(self, *args, **kwargs):
        """
        ENHANCED: Override handle_request to ensure choices are always set
        BACKWARD COMPATIBLE: Preserves existing POST bypass logic
        """
        from flask import request, flash, redirect, current_app
        
        try:
            if request.method == 'POST':
                # EXISTING: For POST requests, bypass WTForms validation and use custom processing
                form = self.get_form(*args, **kwargs)
                try:
                    result = self.process_form(form, *args, **kwargs)
                    flash(self.success_message, "success")
                    if callable(self.success_url):
                        return redirect(self.success_url(result))
                    return redirect(self.success_url)
                except PermissionError as pe:
                    # NEW: Handle permission errors specifically
                    current_app.logger.warning(f"Permission denied: {str(pe)}")
                    if "different branch" in str(pe).lower():
                        flash("You don't have access to edit data from this branch. Please contact your administrator.", "warning")
                    elif "insufficient permissions" in str(pe).lower():
                        flash("You don't have permission to edit this item. Please contact your administrator.", "warning")
                    else:
                        flash(f"Access denied: {str(pe)}", "warning")
                    
                    # Redirect to appropriate list view
                    try:
                        from flask import url_for
                        redirect_url = url_for('universal_views.universal_list_view', entity_type='supplier_invoices')
                    except Exception:
                        redirect_url = '/'
                    return redirect(redirect_url)
                except ValueError as ve:
                    # EXISTING: Handle business logic errors
                    current_app.logger.warning(f"Business logic error: {str(ve)}")
                    if "access denied" in str(ve).lower():
                        flash("Access denied to the requested item.", "warning")
                        try:
                            from flask import url_for
                            return redirect(url_for('universal_views.universal_list_view', entity_type='supplier_invoices'))
                        except Exception:
                            return redirect('/')
                    else:
                        flash(str(ve), "error")
                        return self.render_form(form, *args, **kwargs)
                except Exception as e:
                    # EXISTING: Handle unexpected errors  
                    current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                    flash(str(e), "error")
                    return self.render_form(form, *args, **kwargs)
            else:
                # EXISTING: GET request - render form normally
                form = self.get_form(*args, **kwargs)
                return self.render_form(form, *args, **kwargs)
                
        except PermissionError as pe:
            # NEW: Handle permission errors at form level (e.g., in get_form)
            current_app.logger.warning(f"Permission denied during form setup: {str(pe)}")
            flash(f"Access denied: {str(pe)}", "warning")
            try:
                from flask import url_for
                return redirect(url_for('universal_views.universal_list_view', entity_type='supplier_invoices'))
            except Exception:
                return redirect('/')
        except Exception as e:
            # EXISTING: Handle errors in form setup
            current_app.logger.error(f"Error in handle_request: {str(e)}")
            flash(f"Error: {str(e)}", "error")
            try:
                from flask import url_for
                return redirect(url_for('universal_views.universal_list_view', entity_type='supplier_invoices'))
            except Exception:
                return redirect('/')

    def _extract_line_items_from_hidden_fields(self, form):
        """
        Extract line items from comma-separated hidden fields (JavaScript approach)
        This is used by the edit template where JavaScript populates hidden fields
        """
        from datetime import datetime

        line_items = []

        # Get all the comma-separated values
        medicine_ids = form.medicine_ids.data.split(',') if form.medicine_ids.data else []
        medicine_names = form.medicine_names.data.split(',') if form.medicine_names.data else []
        quantities = form.quantities.data.split(',') if form.quantities.data else []
        batch_numbers = form.batch_numbers.data.split(',') if form.batch_numbers.data else []
        expiry_dates = form.expiry_dates.data.split(',') if form.expiry_dates.data else []
        pack_purchase_prices = form.pack_purchase_prices.data.split(',') if form.pack_purchase_prices.data else []
        pack_mrps = form.pack_mrps.data.split(',') if form.pack_mrps.data else []
        units_per_packs = form.units_per_packs.data.split(',') if form.units_per_packs.data else []
        hsn_codes = form.hsn_codes.data.split(',') if form.hsn_codes.data else []
        gst_rates = form.gst_rates.data.split(',') if form.gst_rates.data else []
        discount_percents = form.discount_percents.data.split(',') if form.discount_percents.data else []
        is_free_items = form.is_free_items.data.split(',') if form.is_free_items.data else []

        # Process each line item
        num_items = len(medicine_ids)
        current_app.logger.info(f"Extracting {num_items} line items from hidden fields")

        for i in range(num_items):
            try:
                medicine_id = medicine_ids[i].strip()
                if not medicine_id:
                    continue

                # Parse expiry date
                expiry_date_str = expiry_dates[i].strip() if i < len(expiry_dates) else ''
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None

                # Check if free item
                is_free = is_free_items[i].strip().lower() == 'true' if i < len(is_free_items) else False

                quantity = float(quantities[i]) if i < len(quantities) else 0
                price = float(pack_purchase_prices[i]) if i < len(pack_purchase_prices) else 0

                # Force price to 0 for free items
                if is_free:
                    price = 0.0

                line_data = {
                    'medicine_id': uuid.UUID(medicine_id),
                    'units': quantity,
                    'batch_number': batch_numbers[i].strip() if i < len(batch_numbers) else '',
                    'expiry_date': expiry_date,
                    'pack_purchase_price': price,
                    'pack_mrp': float(pack_mrps[i]) if i < len(pack_mrps) else 0,
                    'units_per_pack': float(units_per_packs[i]) if i < len(units_per_packs) else 1,
                    'discount_percent': 0.0 if is_free else (float(discount_percents[i]) if i < len(discount_percents) else 0),
                    'is_free_item': is_free,
                    'hsn_code': hsn_codes[i].strip() if i < len(hsn_codes) else '',
                    'gst_rate': float(gst_rates[i]) if i < len(gst_rates) else 0
                }

                line_items.append(line_data)
                current_app.logger.debug(f"Extracted line item {i+1}: {medicine_names[i] if i < len(medicine_names) else 'Unknown'}")

            except Exception as e:
                current_app.logger.error(f"Error parsing line item {i+1}: {str(e)}")
                continue

        current_app.logger.info(f"Successfully extracted {len(line_items)} valid line items")
        return line_items

    def _extract_line_items_from_request(self, form_data):
        """Extract line items directly from request.form data - UPDATED for hybrid approach"""
        line_items = []
        
        # Find the maximum line item index for existing items
        max_index = -1
        for key in form_data.keys():
            if key.startswith('line_items-') and '-' in key:
                try:
                    index = int(key.split('-')[1])
                    max_index = max(max_index, index)
                except (ValueError, IndexError):
                    continue
        
        current_app.logger.info(f"Found existing line items with max index: {max_index}")
        
        # Extract existing line items (modified or deleted)
        for i in range(max_index + 1):
            medicine_id = form_data.get(f'line_items-{i}-medicine_id')
            delete_flag = form_data.get(f'line_items-{i}-delete', 'false')
            
            # Skip deleted items
            if delete_flag.lower() == 'true':
                current_app.logger.info(f"Skipping deleted line item {i}")
                continue
            
            if medicine_id:  # Only process if medicine is selected
                try:
                    is_free = form_data.get(f'line_items-{i}-is_free_item') == 'y'
                    
                    quantity = float(form_data.get(f'line_items-{i}-quantity', 0))
                    price = float(form_data.get(f'line_items-{i}-pack_purchase_price', 0))
                    
                    # BUSINESS RULE: Free items should have 0 price but preserve quantity
                    if is_free:
                        price = 0.0  # Force price to 0 for free items
                    
                    # Get batch and expiry date
                    batch_number = form_data.get(f'line_items-{i}-batch_number', '').strip()
                    expiry_date = form_data.get(f'line_items-{i}-expiry_date')
                    
                    line_data = {
                        'medicine_id': uuid.UUID(medicine_id),
                        'units': quantity,
                        'pack_purchase_price': price,
                        'pack_mrp': float(form_data.get(f'line_items-{i}-pack_mrp', 0)),
                        'units_per_pack': float(form_data.get(f'line_items-{i}-units_per_pack', 1)),
                        'discount_percent': 0.0 if is_free else float(form_data.get(f'line_items-{i}-discount_percent', 0)),
                        'is_free_item': is_free,
                        'hsn_code': form_data.get(f'line_items-{i}-hsn_code', ''),
                        'gst_rate': float(form_data.get(f'line_items-{i}-gst_rate', 0)),
                        'batch_number': batch_number,
                        'expiry_date': expiry_date,
                        'manufacturing_date': form_data.get(f'line_items-{i}-manufacturing_date') or None,
                        'itc_eligible': form_data.get(f'line_items-{i}-itc_eligible') == 'y'
                    }
                    
                    current_app.logger.info(f"Extracted existing line {i + 1}: Qty={quantity}, Price={price}, Free={is_free}, Batch={batch_number}")
                    line_items.append(line_data)
                    
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error extracting existing line item {i}: {str(e)}")
                    continue
        
        # Extract new items (added via hybrid interface)
        new_items_count = int(form_data.get('new_items_count', 0))
        current_app.logger.info(f"Found {new_items_count} new items to add")
        
        for i in range(new_items_count):
            try:
                medicine_id = form_data.get(f'new_item_{i}_medicine_id')
                if medicine_id:
                    is_free = form_data.get(f'new_item_{i}_is_free_item', 'false').lower() == 'true'
                    
                    quantity = float(form_data.get(f'new_item_{i}_quantity', 0))
                    price = float(form_data.get(f'new_item_{i}_pack_purchase_price', 0))
                    
                    # BUSINESS RULE: Free items should have 0 price
                    if is_free:
                        price = 0.0
                    
                    line_data = {
                        'medicine_id': uuid.UUID(medicine_id),
                        'units': quantity,
                        'pack_purchase_price': price,
                        'pack_mrp': float(form_data.get(f'new_item_{i}_pack_mrp', 0)),
                        'units_per_pack': float(form_data.get(f'new_item_{i}_units_per_pack', 1)),
                        'discount_percent': 0.0 if is_free else float(form_data.get(f'new_item_{i}_discount_percent', 0)),
                        'is_free_item': is_free,
                        'hsn_code': form_data.get(f'new_item_{i}_hsn_code', ''),
                        'gst_rate': float(form_data.get(f'new_item_{i}_gst_rate', 0)),
                        'batch_number': form_data.get(f'new_item_{i}_batch_number', ''),
                        'expiry_date': form_data.get(f'new_item_{i}_expiry_date'),
                        'manufacturing_date': None,
                        'itc_eligible': True
                    }
                    
                    current_app.logger.info(f"Extracted new item {i + 1}: Medicine={form_data.get(f'new_item_{i}_medicine_name')}, Qty={quantity}, Price={price}, Free={is_free}")
                    line_items.append(line_data)
                    
            except (ValueError, TypeError) as e:
                current_app.logger.error(f"Error extracting new item {i}: {str(e)}")
                continue
        
        current_app.logger.info(f"Total line items extracted: {len(line_items)}")
        return line_items


class PurchaseOrderFormController(FormController):
    """Controller for purchase order form - CREATE ONLY"""
    
    def __init__(self):
        from app.forms.supplier_forms import PurchaseOrderForm
        
        super().__init__(
            form_class=PurchaseOrderForm,
            template_path='supplier/create_purchase_order.html',
            success_url=self._get_success_url,
            success_message="Purchase order created successfully",
            page_title="Create Purchase Order",
            additional_context=self.get_additional_context
        )

    def _get_success_url(self, result):
        """FIXED: Redirect to Universal Engine view instead of old view"""
        from flask import url_for
        
        # Check if Universal Engine is available
        try:
            # Try to use Universal Engine view
            return url_for('universal_views.universal_detail_view', 
                        entity_type='purchase_orders', 
                        item_id=result['po_id'])
        except:
            # Fallback to old view if Universal Engine not available
            return url_for('supplier_views.view_purchase_order', 
                        po_id=result['po_id'])
    
    def get_additional_context(self, *args, **kwargs):
        """Get suppliers, medicines, and purchase orders for dropdowns - ENHANCED with branch filtering"""
        context = {}
        try:
            from app.services.database_service import get_db_session
            from app.models.master import Supplier, Medicine, Branch, Hospital
            from flask_login import current_user
            
            # Get branch context for filtering
            try:
                from app.services.permission_service import get_user_branch_context
                branch_context = get_user_branch_context(
                    current_user.user_id,
                    current_user.hospital_id,
                    'purchase_order'
                )
                context['branch_context'] = branch_context
            except Exception as e:
                current_app.logger.warning(f"Could not get branch context: {str(e)}")
                branch_context = {'accessible_branches': [], 'can_cross_branch': False}
                context['branch_context'] = branch_context
            
            with get_db_session(read_only=True) as session:
                # Get hospital state code for GST calculation
                try:
                    hospital = session.query(Hospital).filter_by(
                        hospital_id=current_user.hospital_id
                    ).first()
                    
                    if hospital and hospital.state_code:
                        context['hospital_state_code'] = hospital.state_code
                        current_app.logger.info(f"Hospital state code: {hospital.state_code}")
                    else:
                        context['hospital_state_code'] = ''
                        current_app.logger.warning("Hospital state code not found")

                    # NEW: Add hospital currency information
                    if hospital:
                        default_currency = hospital.default_currency or 'INR'
                        
                        # Try to get currency details from CurrencyMaster
                        currency_master = session.query(CurrencyMaster).filter_by(
                            hospital_id=current_user.hospital_id,
                            currency_code=default_currency,
                            is_base_currency=True,
                            is_active=True
                        ).first()
                        
                        if currency_master:
                            context['hospital_currency'] = {
                                'code': currency_master.currency_code,
                                'symbol': currency_master.currency_symbol,
                                'name': currency_master.currency_name,
                                'decimal_places': currency_master.decimal_places
                            }
                        else:
                            # Fallback to MedicineService for symbol lookup
                            from app.services.medicine_service import MedicineService
                            context['hospital_currency'] = {
                                'code': default_currency,
                                'symbol': MedicineService.get_currency_symbol(default_currency),
                                'name': default_currency,
                                'decimal_places': 2
                            }
                    else:
                        # Default fallback
                        context['hospital_currency'] = {
                            'code': 'INR',
                            'symbol': '₹',
                            'name': 'Indian Rupee',
                            'decimal_places': 2
                        }

                except Exception as e:
                    current_app.logger.error(f"Error getting hospital state: {str(e)}")
                    context['hospital_state_code'] = ''

                # Get suppliers with branch filtering
                all_suppliers = session.query(Supplier).filter_by(
                    hospital_id=current_user.hospital_id,
                    status='active'
                ).all()
                
                # Filter suppliers based on branch access
                accessible_suppliers = []
                suppliers_dict = {}  # ADD THIS: Store supplier details by ID
                if current_user.user_id == '7777777777':  # PRESERVE: Testing bypass
                    accessible_suppliers = all_suppliers
                else:
                    accessible_branch_ids = [b['branch_id'] for b in branch_context.get('accessible_branches', [])]
                    for supplier in all_suppliers:
                        if (branch_context.get('can_cross_branch', False) or 
                            not supplier.branch_id or  # No branch restriction
                            str(supplier.branch_id) in accessible_branch_ids):
                            accessible_suppliers.append(supplier)
                
                # Create supplier details dictionary
                for supplier in accessible_suppliers:
                    # Extract state from JSONB field
                    supplier_state = ''
                    supplier_city = ''
                    supplier_pincode = ''
                    supplier_address_str = ''
                    
                    if supplier.supplier_address:
                        # supplier_address is a JSONB field
                        if isinstance(supplier.supplier_address, dict):
                            supplier_state = supplier.supplier_address.get('state', '')
                            supplier_city = supplier.supplier_address.get('city', '')
                            supplier_pincode = supplier.supplier_address.get('pincode', '')
                            supplier_address_str = supplier.supplier_address.get('address', '')
                    
                    state_name = get_state_name_from_code(supplier.state_code)
                    suppliers_dict[str(supplier.supplier_id)] = {
                        'supplier_id': str(supplier.supplier_id),
                        'supplier_name': supplier.supplier_name,
                        'state': state_name,  # <-- FIXED: Derived from state_code
                        'state_code': supplier.state_code or '',
                        'gst_registration_number': supplier.gst_registration_number or '',
                        'address': '',  # These fields don't exist directly
                        'city': '',
                        'pincode': ''
                    }

                context['suppliers'] = accessible_suppliers
                context['suppliers_dict'] = {str(s.supplier_id): s for s in accessible_suppliers}
                
                # Get current PO's selected supplier details if editing
                if hasattr(self, 'po_id') and self.po_id:
                    try:
                        from app.services.supplier_service import get_purchase_order_by_id
                        import uuid
                        
                        po = get_purchase_order_by_id(
                            po_id=uuid.UUID(self.po_id),
                            hospital_id=current_user.hospital_id
                        )
                        
                        if po and po.get('supplier_id'):
                            # Find the selected supplier
                            selected_supplier = next(
                                (s for s in accessible_suppliers if str(s.supplier_id) == str(po['supplier_id'])),
                                None
                            )
                            if selected_supplier:
                                # Extract state from JSONB field
                                supplier_state = ''
                                if selected_supplier.supplier_address:
                                    # supplier_address is a JSONB field containing state
                                    supplier_state = selected_supplier.supplier_address.get('state', '') if isinstance(selected_supplier.supplier_address, dict) else ''
                                
                                state_name = get_state_name_from_code(selected_supplier.state_code)
    
                                context['selected_supplier'] = {
                                    'supplier_id': str(selected_supplier.supplier_id),
                                    'supplier_name': selected_supplier.supplier_name,
                                    'state': state_name,  # <-- FIXED: Derived from state_code
                                    'state_code': selected_supplier.state_code or '',
                                    'gst_registration_number': selected_supplier.gst_registration_number or ''
                                }
                    except Exception as e:
                        current_app.logger.warning(f"Could not get selected supplier details: {str(e)}")

                # Get medicines with MRP data for line items
                medicines = session.query(Medicine).filter_by(
                    hospital_id=current_user.hospital_id,
                    status='active'
                ).order_by(Medicine.medicine_name).all()

                # Enhance medicines with price data
                from app.services.database_service import get_detached_copy
                medicines_with_prices = []
                for m in medicines:
                    medicine_copy = get_detached_copy(m)
                    medicine_copy.mrp_value = float(m.mrp or 0)
                    medicine_copy.last_purchase_price_value = float(m.last_purchase_price or 0)
                    medicines_with_prices.append(medicine_copy)

                context['medicines'] = medicines_with_prices
                
                # Get branches with filtering
                all_branches = session.query(Branch).filter_by(
                    hospital_id=current_user.hospital_id,
                    is_active=True
                ).all()
                
                # Filter branches based on permissions
                accessible_branches = []
                if current_user.user_id == '7777777777':  # PRESERVE: Testing bypass
                    accessible_branches = all_branches
                else:
                    accessible_branch_ids = [b['branch_id'] for b in branch_context.get('accessible_branches', [])]
                    for branch in all_branches:
                        if (branch_context.get('can_cross_branch', False) or 
                            str(branch.branch_id) in accessible_branch_ids):
                            accessible_branches.append(branch)
                
                context['branches'] = accessible_branches
                
        except Exception as e:
            current_app.logger.error(f"Error getting context: {str(e)}")
            # FALLBACK: Ensure basic context
            context.update({
                'suppliers': [],
                'suppliers_dict': {},
                'medicines': [],
                'hospital_state_code': '', 
                'branches': [],
                'hospital_currency': {
                    'code': 'INR',
                    'symbol': '₹', 
                    'name': 'Indian Rupee',
                    'decimal_places': 2
                    },
                'branch_context': {'accessible_branches': [], 'can_cross_branch': False}
            })
        
        return context
    
    def handle_request(self, *args, **kwargs):
        """Handle request with proper validation for Universal Dropdown fields"""
        from flask import request
        
        try:
            if request.method == 'POST':
                # Get the form
                form = self.form_class()
                
                # Get supplier_id from request
                supplier_id_from_request = request.form.get('supplier_id', '').strip()
                
                # CRITICAL: Validate supplier_id - can be UUID or name from Universal Dropdown
                if supplier_id_from_request:
                    import uuid
                    from app.services.database_service import get_db_session
                    from app.models.master import Supplier
                    from flask_login import current_user
                    
                    supplier = None
                    actual_supplier_id = None
                    
                    # First try to treat as UUID
                    try:
                        # Try to parse as UUID
                        supplier_uuid = uuid.UUID(supplier_id_from_request)
                        
                        # Validate supplier exists in database
                        with get_db_session(read_only=True) as session:
                            supplier = session.query(Supplier).filter_by(
                                supplier_id=supplier_uuid,
                                hospital_id=current_user.hospital_id,
                                is_deleted=False
                            ).first()
                            
                            if supplier:
                                actual_supplier_id = supplier_id_from_request
                                
                    except ValueError:
                        # Not a UUID - try searching by name (Universal Dropdown sends name)
                        current_app.logger.info(f"Supplier value is not UUID, searching by name: {supplier_id_from_request}")
                        
                        with get_db_session(read_only=True) as session:
                            supplier = session.query(Supplier).filter_by(
                                supplier_name=supplier_id_from_request,
                                hospital_id=current_user.hospital_id,
                                is_deleted=False
                            ).first()
                            
                            if supplier:
                                # Found by name - use the actual UUID
                                actual_supplier_id = str(supplier.supplier_id)
                                # Update form data to use UUID instead of name
                                form.supplier_id.data = actual_supplier_id
                                current_app.logger.info(f"Found supplier by name '{supplier_id_from_request}', using UUID: {actual_supplier_id}")
                    
                    # Check if supplier was found by either method
                    if supplier and actual_supplier_id:
                        # Add as valid choice with actual supplier name
                        form.supplier_id.choices = [(actual_supplier_id, supplier.supplier_name)]
                    else:
                        # Supplier doesn't exist or not found
                        form.supplier_id.choices = [('', 'Select Supplier')]
                        flash("Selected supplier not found or not accessible", "error")
                        current_app.logger.error(f"Supplier not found: {supplier_id_from_request}")
                        return self.render_form(form, *args, **kwargs)
                        
                else:
                    # No supplier selected
                    form.supplier_id.choices = [('', 'Select Supplier')]
                
                # Generate PO number if not set
                if not form.po_number.data:
                    form.po_number.data = self.generate_po_number()
                
                # Now validate form with proper choices
                if form.validate_on_submit():
                    try:
                        result = self.process_form(form, *args, **kwargs)
                        flash(self.success_message, "success")
                        
                        if callable(self.success_url):
                            return redirect(self.success_url(result))
                        return redirect(self.success_url)
                    except Exception as e:
                        current_app.logger.error(f"Error processing form: {str(e)}", exc_info=True)
                        flash(f"Error: {str(e)}", "error")
                        return self.render_form(form, *args, **kwargs)
                else:
                    # Form validation failed
                    for field, errors in form.errors.items():
                        current_app.logger.error(f"Validation error in {field}: {errors}")
                        for error in errors:
                            flash(f"{field}: {error}", "error")
                    return self.render_form(form, *args, **kwargs)
            else:
                # GET request
                form = self.get_form(*args, **kwargs)
                return self.render_form(form, *args, **kwargs)
                
        except Exception as e:
            current_app.logger.error(f"Error in handle_request: {str(e)}", exc_info=True)
            flash(f"Error: {str(e)}", "error")
            try:
                from flask import url_for
                return redirect(url_for('supplier_views.purchase_order_list'))
            except:
                return redirect('/')
    
    # Keep the get_form for GET requests (when displaying the form)
    def get_form(self, *args, **kwargs):
        """Get form for display"""
        form = super().get_form(*args, **kwargs)
        
        # Set choices to empty array for Universal Dropdown
        form.supplier_id.choices = []
        
        # Generate PO number if new
        if not form.po_number.data:
            form.po_number.data = self.generate_po_number()
            
        return form
    
    def generate_po_number(self):
        """Generate a new PO number"""
        from datetime import datetime
        from flask_login import current_user
        from app.services.database_service import get_db_session
        from app.models.transaction import PurchaseOrderHeader
        
        # Get current financial year
        today = datetime.now()
        if today.month >= 4:  # Financial year starts in April
            fin_year_start = today.year
            fin_year_end = today.year + 1
        else:
            fin_year_start = today.year - 1
            fin_year_end = today.year
            
        fin_year = f"{fin_year_start % 100:02d}-{fin_year_end % 100:02d}"  # e.g., "24-25"
        
        # Get the last PO number for this hospital and financial year
        with get_db_session(read_only=True) as session:
            last_po = session.query(PurchaseOrderHeader).filter(
                PurchaseOrderHeader.hospital_id == current_user.hospital_id,
                PurchaseOrderHeader.po_number.like(f"PO/{fin_year}/%")
            ).order_by(PurchaseOrderHeader.po_number.desc()).first()
            
            if last_po:
                # Extract the sequence number
                try:
                    seq_num = int(last_po.po_number.split('/')[-1])
                    new_seq_num = seq_num + 1
                except:
                    new_seq_num = 1
            else:
                new_seq_num = 1
        
        # Format: PO/YY-YY/00001
        return f"PO/{fin_year}/{new_seq_num:05d}"

    def process_form(self, form, *args, **kwargs):
        """Process the form data for creation - ENHANCED with GST calculations"""
        try:
            # Import all necessary modules
            from flask import request, current_app
            from flask_login import current_user
            import uuid
            
            from app.services.supplier_service import (
                create_purchase_order_with_validation,
                resolve_medicine_identifier,
                process_po_line_items_with_gst
            )
            from app.services.branch_service import validate_entity_branch_access, get_user_branch_id
            from app.services.permission_service import has_branch_permission

            # ===== PERMISSION VALIDATION =====
            if current_user.user_id != '7777777777':  # Testing bypass
                try:
                    user_obj = {'user_id': current_user.user_id, 'hospital_id': current_user.hospital_id}
                    if not has_branch_permission(user_obj, 'purchase_order', 'add'):
                        raise PermissionError("Insufficient permissions to create purchase orders")
                    
                    if form.supplier_id.data:
                        if not validate_entity_branch_access(
                            current_user.user_id,
                            current_user.hospital_id,
                            form.supplier_id.data,
                            'supplier',
                            'view'
                        ):
                            raise PermissionError("Cannot create PO for supplier from different branch")
                            
                except PermissionError:
                    raise
                except Exception as e:
                    current_app.logger.warning(f"Permission validation failed, proceeding: {str(e)}")
            
            # ===== DETERMINE SAVE TYPE =====
            is_draft = 'save_draft' in request.form
            is_approved = 'save_approved' in request.form
            
            # ===== VALIDATE FORM HAS LINE ITEMS =====
            if not form.medicine_ids.data or not form.medicine_ids.data.strip():
                raise ValueError("No line items found. Please add at least one item to the purchase order.")

            # ===== PARSE LINE ITEMS FROM FORM (INLINE - NO SEPARATE METHOD NEEDED) =====
            line_items_raw = []

            medicine_ids = form.medicine_ids.data.split(',')
            medicine_ids = [mid.strip() for mid in medicine_ids if mid.strip()]

            if not medicine_ids:
                raise ValueError("No valid line items found. Please add at least one item to the purchase order.")

            # Parse all the comma-separated fields
            quantities = form.quantities.data.split(',')
            pack_prices = form.pack_purchase_prices.data.split(',')
            pack_mrps = form.pack_mrps.data.split(',')
            units_per_packs = form.units_per_packs.data.split(',')
            hsn_codes = form.hsn_codes.data.split(',') if form.hsn_codes.data else []
            gst_rates = form.gst_rates.data.split(',') if form.gst_rates.data else []

            # Handle optional fields with defaults
            discount_percents = form.discount_percents.data.split(',') if hasattr(form, 'discount_percents') and form.discount_percents.data else ['0'] * len(medicine_ids)
            is_free_items = form.is_free_items.data.split(',') if hasattr(form, 'is_free_items') and form.is_free_items.data else ['false'] * len(medicine_ids)

            # Import required modules for medicine lookup
            from app.services.supplier_service import resolve_medicine_identifier
            from app.models.master import Medicine
            from app.services.database_service import get_db_session

            # Build line items
            for i in range(len(medicine_ids)):
                if not medicine_ids[i]:
                    continue
                
                try:
                    medicine_id_str = medicine_ids[i].strip()
                    if not medicine_id_str or medicine_id_str in ['undefined', 'null']:
                        current_app.logger.warning(f"Skipping line {i+1}: Invalid medicine ID")
                        continue
                    
                    # Resolve medicine ID (handles both UUID and name)
                    actual_medicine_id = resolve_medicine_identifier(
                        medicine_id_str,
                        current_user.hospital_id
                    )
                    
                    # CRITICAL: Always fetch medicine details for GST rate and HSN code
                    medicine_gst_rate = 0.0
                    medicine_hsn_code = ''
                    medicine_name = ''
                    
                    with get_db_session(read_only=True) as session:
                        medicine = session.query(Medicine).filter_by(
                            medicine_id=actual_medicine_id,
                            hospital_id=current_user.hospital_id
                        ).first()
                        
                        if medicine:
                            medicine_name = medicine.medicine_name
                            
                            # Get GST rate from medicine
                            if medicine.gst_rate is not None:
                                medicine_gst_rate = float(medicine.gst_rate)
                                current_app.logger.info(f"Medicine '{medicine_name}' GST from DB: {medicine_gst_rate}%")
                            
                            # Get HSN code from medicine
                            if medicine.hsn_code:
                                medicine_hsn_code = str(medicine.hsn_code)
                                current_app.logger.info(f"Medicine '{medicine_name}' HSN from DB: {medicine_hsn_code}")
                        else:
                            current_app.logger.error(f"Medicine not found in DB: {actual_medicine_id}")
                            raise ValueError(f"Medicine not found for ID: {actual_medicine_id}")
                    
                    # Parse form values with safe defaults
                    form_gst_rate = 0.0
                    if i < len(gst_rates) and gst_rates[i]:
                        try:
                            form_gst_rate = float(gst_rates[i])
                        except (ValueError, TypeError):
                            form_gst_rate = 0.0
                    
                    form_hsn_code = ''
                    if i < len(hsn_codes) and hsn_codes[i]:
                        form_hsn_code = str(hsn_codes[i]).strip()
                    
                    # CRITICAL LOGIC: Prefer form values if valid, otherwise use medicine values
                    final_gst_rate = form_gst_rate if form_gst_rate > 0 else medicine_gst_rate
                    final_hsn_code = form_hsn_code if form_hsn_code else medicine_hsn_code
                    
                    # If still no GST rate, use default based on HSN code
                    if final_gst_rate <= 0:
                        # Default GST rates based on HSN codes
                        if final_hsn_code.startswith('3004'):  # Medicines
                            final_gst_rate = 12.0
                        elif final_hsn_code.startswith('3304'):  # Cosmetics
                            final_gst_rate = 18.0
                        else:
                            final_gst_rate = 18.0  # Default
                        current_app.logger.warning(f"No GST rate found for '{medicine_name}', using default: {final_gst_rate}%")
                    
                    # Convert boolean string
                    is_free = is_free_items[i].lower() == 'true' if i < len(is_free_items) else False
                    
                    # Create line item data with proper GST rate
                    line_item = {
                        'medicine_id': actual_medicine_id,
                        'units': float(quantities[i]),
                        'pack_purchase_price': float(pack_prices[i]),
                        'pack_mrp': float(pack_mrps[i]),
                        'units_per_pack': float(units_per_packs[i]),
                        'hsn_code': final_hsn_code,
                        'gst_rate': final_gst_rate,  # THIS MUST NOT BE 0
                        'discount_percent': float(discount_percents[i]) if i < len(discount_percents) else 0.0,
                        'is_free_item': is_free
                    }
                    
                    # Detailed logging for debugging
                    current_app.logger.info(f"Line {i+1} Final Data:")
                    current_app.logger.info(f"  Medicine: {medicine_name}")
                    current_app.logger.info(f"  Form GST: {form_gst_rate}%, DB GST: {medicine_gst_rate}%, Final GST: {final_gst_rate}%")
                    current_app.logger.info(f"  Form HSN: {form_hsn_code}, DB HSN: {medicine_hsn_code}, Final HSN: {final_hsn_code}")
                    current_app.logger.info(f"  Units: {line_item['units']}, Price: {line_item['pack_purchase_price']}")
                    current_app.logger.info(f"  Discount: {line_item['discount_percent']}%, Free: {line_item['is_free_item']}")
                    
                    line_items_raw.append(line_item)
                    
                except (ValueError, IndexError) as e:
                    current_app.logger.error(f"Error processing line item {i + 1}: {str(e)}")
                    raise ValueError(f"Invalid data in line item {i + 1}: {str(e)}")

            if not line_items_raw:
                raise ValueError("No valid line items found after processing.")

            # Log summary before GST calculation
            current_app.logger.info(f"Prepared {len(line_items_raw)} line items for GST calculation")
            for idx, item in enumerate(line_items_raw):
                current_app.logger.info(f"  Item {idx+1}: GST={item['gst_rate']}%, Price={item['pack_purchase_price']}, Qty={item['units']}")

            # ===== CALCULATE GST FOR ALL LINE ITEMS =====
            line_items = process_po_line_items_with_gst(
                line_items_raw=line_items_raw,
                hospital_id=current_user.hospital_id,
                supplier_id=form.supplier_id.data
            )
            
            # Log totals for debugging
            total_gst = sum(item.get('total_gst', 0) for item in line_items)
            grand_total = sum(item.get('line_total', 0) for item in line_items)
            current_app.logger.info(f"PO Totals: Items={len(line_items)}, GST={total_gst:.2f}, Total={grand_total:.2f}")
            
            # ===== GET BRANCH ID =====
            branch_id = None
            if hasattr(form, 'branch_id') and form.branch_id.data:
                branch_id = uuid.UUID(form.branch_id.data)
            else:
                user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
                if user_branch_id:
                    branch_id = user_branch_id

            # ===== CREATE PO DATA =====
            po_data = {
                'po_number': form.po_number.data,
                'supplier_id': uuid.UUID(form.supplier_id.data),
                'po_date': form.po_date.data,
                'expected_delivery_date': form.expected_delivery_date.data,
                'quotation_id': form.quotation_id.data,
                'quotation_date': form.quotation_date.data,
                'currency_code': form.currency_code.data,
                'exchange_rate': float(form.exchange_rate.data),
                'delivery_instructions': form.delivery_instructions.data,
                'terms_conditions': form.terms_conditions.data,
                'notes': form.notes.data,
                'status': 'approved' if is_approved else 'draft',
                'line_items': line_items  # Now includes GST calculations
            }
            
            current_app.logger.info(f"Creating PO with {len(line_items)} GST-calculated line items")
            
            # ===== CREATE PURCHASE ORDER =====
            result = create_purchase_order_with_validation(
                hospital_id=current_user.hospital_id,
                po_data=po_data,
                current_user_id=current_user.user_id
            )
            
            current_app.logger.info(f"Successfully created PO: {result.get('po_number')}")
            return result
        
        except PermissionError as pe:
            current_app.logger.warning(f"Permission denied: {str(pe)}")
            raise
        except ValueError as ve:
            current_app.logger.error(f"Validation error: {str(ve)}")
            raise
        except Exception as e:
            current_app.logger.error(f"Error processing PO form: {str(e)}")
            raise


class PurchaseOrderEditController(FormController):
    """Dedicated controller for PO editing following centralized framework"""
    
    def __init__(self, po_id):
        self.po_id = po_id
        
        from app.forms.supplier_forms import PurchaseOrderEditForm
        super().__init__(
            form_class=PurchaseOrderEditForm,
            template_path='supplier/edit_purchase_order.html',
            success_url=self._get_success_url,
            success_message="Purchase order updated successfully",
            page_title="Edit Purchase Order",
            additional_context=self.get_additional_context
        )
    
    def _get_success_url(self, result):
        """Generate success URL"""
        from flask import url_for
        return url_for('supplier_views.view_purchase_order', po_id=self.po_id)

    def get_additional_context(self, *args, **kwargs):
        """Get additional context for template - ENHANCED with branch filtering"""
        context = {}
        try:
            from app.services.database_service import get_db_session, get_detached_copy
            from app.models.master import Supplier, Medicine, Branch
            from app.models.transaction import PurchaseOrderHeader
            from flask_login import current_user
            import uuid
            
            # NEW: Get branch context for filtering
            try:
                from app.services.permission_service import get_user_branch_context
                branch_context = get_user_branch_context(
                    current_user.user_id,
                    current_user.hospital_id,
                    'purchase_order'
                )
                context['branch_context'] = branch_context
            except Exception as e:
                current_app.logger.warning(f"Could not get branch context: {str(e)}")
                branch_context = {'accessible_branches': [], 'can_cross_branch': False}
                context['branch_context'] = branch_context
            
            with get_db_session(read_only=True) as session:
                # ENHANCED: Get suppliers with branch filtering for dropdown
                all_suppliers = session.query(Supplier).filter_by(
                    hospital_id=current_user.hospital_id,
                    status='active'
                ).all()
                
                # FIXED: Create detached copies to prevent session errors
                # Filter suppliers based on branch access
                accessible_suppliers = []
                suppliers_dict = {}  # ADD THIS: Store supplier details by ID
                if current_user.user_id == '7777777777':  # PRESERVE: Testing bypass
                    accessible_suppliers = [get_detached_copy(s) for s in all_suppliers]
                else:
                    accessible_branch_ids = [b['branch_id'] for b in branch_context.get('accessible_branches', [])]
                    for supplier in all_suppliers:
                        if (branch_context.get('can_cross_branch', False) or 
                            not supplier.branch_id or  # No branch restriction
                            str(supplier.branch_id) in accessible_branch_ids):
                            accessible_suppliers.append(get_detached_copy(supplier))
                
                # FIX: Build suppliers_dict from detached copies
                for supplier_copy in accessible_suppliers:
                    state_name = get_state_name_from_code(supplier_copy.state_code)
                    suppliers_dict[str(supplier_copy.supplier_id)] = {
                        'supplier_id': str(supplier_copy.supplier_id),
                        'supplier_name': supplier_copy.supplier_name,
                        'state': state_name,  # <-- FIXED: Derived from state_code
                        'state_code': supplier_copy.state_code or '',
                        'gst_registration_number': supplier_copy.gst_registration_number or ''
                    }
                
                # FIXED: Get current PO's selected supplier details if editing - INSIDE session
                selected_supplier_data = None
                if hasattr(self, 'po_id') and self.po_id:
                    try:
                        # Query PO directly instead of calling service function
                        po_header = session.query(PurchaseOrderHeader).filter_by(
                            po_id=uuid.UUID(self.po_id),
                            hospital_id=current_user.hospital_id
                        ).first()
                        
                        if po_header and po_header.supplier_id:
                            # Find the selected supplier in already-fetched list
                            selected_supplier = next(
                                (s for s in all_suppliers if str(s.supplier_id) == str(po_header.supplier_id)),
                                None
                            )
                            if selected_supplier:
                                state_name = get_state_name_from_code(selected_supplier.state_code)
                                
                                selected_supplier_data = {
                                    'supplier_id': str(selected_supplier.supplier_id),
                                    'supplier_name': selected_supplier.supplier_name,
                                    'state': state_name,  # <-- FIXED: Derived from state_code
                                    'state_code': selected_supplier.state_code or '',
                                    'gst_registration_number': selected_supplier.gst_registration_number or ''
                                }
                    except Exception as e:
                        current_app.logger.warning(f"Could not get selected supplier details: {str(e)}")
                
                # EXISTING: Get medicines for line items
                medicines = session.query(Medicine).filter_by(
                    hospital_id=current_user.hospital_id
                ).all()
                
                # FIXED: Create detached copies for medicines
                context['medicines'] = [get_detached_copy(med) for med in medicines]
                
                # Pass the po_id to the template
                context['po_id'] = str(self.po_id) if self.po_id else None
            
            # NOW outside session - safe to use detached copies
            context['suppliers'] = accessible_suppliers
            context['suppliers_dict'] = suppliers_dict  # <-- ADD THIS LINE
            
            # Add selected supplier if found
            if selected_supplier_data:
                context['selected_supplier'] = selected_supplier_data
            
        except Exception as e:
            current_app.logger.error(f"Error getting context: {str(e)}")
            context.update({
                'suppliers': [],
                'suppliers_dict': {},  # <-- ADD THIS to fallback
                'medicines': [],
                'branch_context': {'accessible_branches': [], 'can_cross_branch': False}
            })
        
        return context
    
    def get_form(self, *args, **kwargs):
        """Get form with populated data"""
        form = super().get_form(*args, **kwargs)
        
        # Set supplier choices
        context = self.get_additional_context()
        suppliers = context.get('suppliers', [])
        form.supplier_id.choices = [('', 'Select Supplier')] + [
            (str(s.supplier_id), s.supplier_name) for s in suppliers
        ]
        
        # Populate with existing PO data
        self._populate_form_with_po_data(form)
        
        return form
    
    def _populate_form_with_po_data(self, form):
        """Populate form with existing PO data - FIXED free item handling"""
        try:
            from app.services.supplier_service import get_purchase_order_by_id
            from flask_login import current_user
            import uuid
            
            po = get_purchase_order_by_id(
                po_id=uuid.UUID(self.po_id),
                hospital_id=current_user.hospital_id
            )
            
            if not po:
                raise ValueError(f"Purchase order with ID {self.po_id} not found")
            
            # Check if PO can be cancelled
            if po.get('status') == 'cancelled':
                raise ValueError(f"Cannot edit cancelled purchase order {po.get('po_number')}")

            # Check if PO can be edited
            if po.get('status') != 'draft':
                raise ValueError(f"Cannot edit purchase order in '{po.get('status')}' status")
            
            # Populate header fields
            form.po_number.data = po.get('po_number')
            form.supplier_id.data = str(po.get('supplier_id'))
            form.po_date.data = po.get('po_date')
            form.expected_delivery_date.data = po.get('expected_delivery_date')
            form.quotation_id.data = po.get('quotation_id')
            form.quotation_date.data = po.get('quotation_date')
            form.currency_code.data = po.get('currency_code', 'INR')
            form.exchange_rate.data = po.get('exchange_rate', 1.0)
            form.notes.data = po.get('notes')
            
            # Clear existing line item entries
            while len(form.line_items.entries) > 0:
                form.line_items.pop_entry()
            
            # Populate line items with CORRECTED free item logic
            line_items_data = po.get('line_items', [])
            
            for line_data in line_items_data:
                # CRITICAL FIX: Get the actual stored values
                stored_units = line_data.get('units', 0)
                stored_price = line_data.get('pack_purchase_price', 0)
                stored_is_free = line_data.get('is_free_item', False)
                
                # DEBUG: Log what we're reading from database
                current_app.logger.info(f"DB line item: Medicine={line_data.get('medicine_name')}, "
                                    f"Units={stored_units}, Price={stored_price}, Free={stored_is_free}")
                
                # For display in edit form:
                # - Free items: Show actual quantity, price = 0, checkbox = checked
                # - Regular items: Show actual quantity and price, checkbox = unchecked
                display_quantity = float(stored_units)
                display_price = 0.0 if stored_is_free else float(stored_price)
                
                form.line_items.append_entry({
                    'medicine_id': str(line_data.get('medicine_id')),
                    'medicine_name': line_data.get('medicine_name'),
                    'quantity': display_quantity,
                    'pack_purchase_price': display_price,
                    'pack_mrp': float(line_data.get('pack_mrp', 0)),
                    'units_per_pack': float(line_data.get('units_per_pack', 1)),
                    'discount_percent': float(line_data.get('discount_percent', 0)),
                    'is_free_item': stored_is_free,  # FIXED: Use actual stored value
                    'hsn_code': line_data.get('hsn_code', ''),
                    'gst_rate': float(line_data.get('gst_rate', 0))
                })
                
                current_app.logger.info(f"Populated form item: Qty={display_quantity}, Price={display_price}, Free={stored_is_free}")
            
            current_app.logger.info(f"Populated form with {len(line_items_data)} line items for PO: {po.get('po_number')}")
            
        except Exception as e:
            current_app.logger.error(f"Error populating form: {str(e)}")
            raise

    # =============================================================================
    # CUSTOM VALIDATION TO CONTROLLER
    # =============================================================================

    def validate_line_items(self, line_items_data):
        """Custom validation for line items"""
        if not line_items_data:
            raise ValueError("At least one line item is required")
        
        for idx, item in enumerate(line_items_data):
            line_num = idx + 1
            quantity = item.get('units', 0)
            price = item.get('pack_purchase_price', 0)
            is_free = item.get('is_free_item', False)
            
            # Validate quantity
            if quantity <= 0:
                raise ValueError(f"Line {line_num}: Quantity must be greater than 0")
            
            # Validate price based on free item status
            if is_free:
                # Free items: price should be 0, but quantity should be positive
                if price != 0:
                    current_app.logger.warning(f"Line {line_num}: Free item price adjusted to 0")
                    item['pack_purchase_price'] = 0.0
            else:
                # Regular items: both price and quantity should be positive
                if price <= 0:
                    raise ValueError(f"Line {line_num}: Price must be greater than 0 for non-free items")


    def process_form(self, form, *args, **kwargs):
        """Process form submission - ENHANCED with centralized branch validation"""
        try:
            # NEW: Add permission validation using centralized functions
            from flask_login import current_user
            from app.services.supplier_service import update_purchase_order
            from app.services.branch_service import validate_entity_branch_access
            from app.services.permission_service import has_branch_permission
            
            # PRESERVE: Testing bypass
            if current_user.user_id != '7777777777':
                try:
                    # Validate user can edit this PO
                    if not validate_entity_branch_access(
                        current_user.user_id,
                        current_user.hospital_id,
                        self.po_id,
                        'purchase_order',
                        'edit'
                    ):
                        raise PermissionError("Cannot edit purchase order from different branch")
                    
                    # Validate supplier access if supplier changed
                    if form.supplier_id.data:
                        if not validate_entity_branch_access(
                            current_user.user_id,
                            current_user.hospital_id,
                            form.supplier_id.data,
                            'supplier',
                            'view'
                        ):
                            raise PermissionError("Cannot change PO to supplier from different branch")
                            
                except PermissionError:
                    raise  # Re-raise permission errors
                except Exception as e:
                    current_app.logger.warning(f"Permission validation failed, proceeding: {str(e)}")
            
            # EXISTING: Continue with original PO update logic
                       
            current_app.logger.info(f"=== PO EDIT FORM PROCESSING START ===")
            current_app.logger.info(f"Bypassing WTForms validation, using custom validation")
            
            # Extract header data (basic validation)
            if not form.supplier_id.data:
                raise ValueError("Supplier is required")
            if not form.po_date.data:
                raise ValueError("PO Date is required")
            
            po_data = {
                'supplier_id': uuid.UUID(form.supplier_id.data),
                'po_date': form.po_date.data,
                'expected_delivery_date': form.expected_delivery_date.data,
                'quotation_id': form.quotation_id.data,
                'quotation_date': form.quotation_date.data,
                'currency_code': form.currency_code.data,
                'exchange_rate': float(form.exchange_rate.data),
                'notes': form.notes.data,
                'line_items': []
            }
            
            # Extract line items directly from request
            line_items_data = self._extract_line_items_from_request(request.form)
            
            # Custom validation
            self.validate_line_items(line_items_data)
            
            po_data['line_items'] = line_items_data
            
            current_app.logger.info(f"Processing PO edit with {len(line_items_data)} line items")
            
            # Update the PO
            result = update_purchase_order(
                po_id=uuid.UUID(self.po_id),
                po_data=po_data,
                hospital_id=current_user.hospital_id,
                current_user_id=current_user.user_id
            )
            
            current_app.logger.info(f"Successfully updated PO: {result.get('po_number')}")
            return result
            
        except PermissionError as pe:
            current_app.logger.warning(f"Permission denied: {str(pe)}")
            raise  # Re-raise to be handled by form framework
        except Exception as e:
            current_app.logger.error(f"Error processing PO edit: {str(e)}")
            raise


    def _extract_line_items_from_request(self, form_data):
        """Extract line items directly from request.form data - FIXED free item handling"""
        line_items = []
        
        # Find the maximum line item index
        max_index = -1
        for key in form_data.keys():
            if key.startswith('line_items-') and '-' in key:
                try:
                    index = int(key.split('-')[1])
                    max_index = max(max_index, index)
                except (ValueError, IndexError):
                    continue
        
        current_app.logger.info(f"Found line items with max index: {max_index}")
        
        # Extract each line item
        for i in range(max_index + 1):
            medicine_id = form_data.get(f'line_items-{i}-medicine_id')
            
            if medicine_id:  # Only process if medicine is selected
                try:
                    # Check if it's a free item
                    is_free = form_data.get(f'line_items-{i}-is_free_item') == 'y'
                    
                    # Get the quantities and prices
                    quantity = float(form_data.get(f'line_items-{i}-quantity', 0))
                    price = float(form_data.get(f'line_items-{i}-pack_purchase_price', 0))
                    
                    # BUSINESS RULE: Free items should have 0 price but preserve quantity
                    if is_free:
                        price = 0.0  # Force price to 0 for free items
                        # Keep the actual quantity as entered by user
                    
                    # VALIDATION: Non-free items must have positive price and quantity
                    if not is_free and (price <= 0 or quantity <= 0):
                        current_app.logger.error(f"Line {i + 1}: Non-free items must have positive price and quantity")
                        continue
                    
                    # VALIDATION: Free items must have positive quantity
                    if is_free and quantity <= 0:
                        current_app.logger.error(f"Line {i + 1}: Free items must have positive quantity")
                        continue
                    
                    line_data = {
                        'medicine_id': uuid.UUID(medicine_id),
                        'units': quantity,
                        'pack_purchase_price': price,
                        'pack_mrp': float(form_data.get(f'line_items-{i}-pack_mrp', 0)),
                        'units_per_pack': float(form_data.get(f'line_items-{i}-units_per_pack', 1)),
                        'discount_percent': 0.0 if is_free else float(form_data.get(f'line_items-{i}-discount_percent', 0)),
                        'is_free_item': is_free,
                        'hsn_code': form_data.get(f'line_items-{i}-hsn_code', ''),
                        'gst_rate': float(form_data.get(f'line_items-{i}-gst_rate', 0))
                    }
                    
                    current_app.logger.info(f"Extracted line {i + 1}: Qty={quantity}, Price={price}, Free={is_free}")
                    line_items.append(line_data)
                    
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error extracting line item {i}: {str(e)}")
                    continue
        
        return line_items
    
    def handle_request(self, *args, **kwargs):
        """
        ENHANCED: Override handle_request for PO editing
        BACKWARD COMPATIBLE: Preserves existing POST bypass logic
        """
        from flask import request, flash, redirect, current_app
        
        try:
            if request.method == 'POST':
                # EXISTING: For POST requests, bypass WTForms validation and use custom processing
                form = self.get_form(*args, **kwargs)
                try:
                    result = self.process_form(form, *args, **kwargs)
                    flash(self.success_message, "success")
                    if callable(self.success_url):
                        return redirect(self.success_url(result))
                    return redirect(self.success_url)
                except PermissionError as pe:
                    # NEW: Handle permission errors specifically
                    current_app.logger.warning(f"Permission denied: {str(pe)}")
                    if "different branch" in str(pe).lower():
                        flash("You don't have access to edit purchase orders from this branch. Please contact your administrator.", "warning")
                    elif "insufficient permissions" in str(pe).lower():
                        flash("You don't have permission to edit purchase orders. Please contact your administrator.", "warning")
                    else:
                        flash(f"Access denied: {str(pe)}", "warning")
                    
                    # Redirect to PO list
                    try:
                        from flask import url_for
                        redirect_url = url_for('supplier_views.purchase_order_list')
                    except Exception:
                        redirect_url = '/'
                    return redirect(redirect_url)
                except ValueError as ve:
                    # EXISTING: Handle business logic errors
                    current_app.logger.warning(f"Business logic error: {str(ve)}")
                    if "access denied" in str(ve).lower():
                        flash("Access denied to the requested purchase order.", "warning")
                        try:
                            from flask import url_for
                            return redirect(url_for('supplier_views.purchase_order_list'))
                        except Exception:
                            return redirect('/')
                    else:
                        flash(str(ve), "error")
                        return self.render_form(form, *args, **kwargs)
                except Exception as e:
                    # EXISTING: Handle unexpected errors
                    current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
                    flash(str(e), "error")
                    return self.render_form(form, *args, **kwargs)
            else:
                # EXISTING: GET request - render form normally
                form = self.get_form(*args, **kwargs)
                return self.render_form(form, *args, **kwargs)
                
        except PermissionError as pe:
            # NEW: Handle permission errors at form level (e.g., in get_form)
            current_app.logger.warning(f"Permission denied during form setup: {str(pe)}")
            flash(f"Access denied: {str(pe)}", "warning")
            try:
                from flask import url_for
                return redirect(url_for('supplier_views.purchase_order_list'))
            except Exception:
                return redirect('/')
        except Exception as e:
            # EXISTING: Handle errors in form setup
            current_app.logger.error(f"Error in handle_request: {str(e)}")
            flash(f"Error: {str(e)}", "error")
            try:
                from flask import url_for
                return redirect(url_for('supplier_views.purchase_order_list'))
            except Exception:
                return redirect('/')
            
class SupplierPaymentController(FormController):
    """Enhanced payment controller with multi-method and document support"""
    
    def __init__(self, payment_id=None, invoice_id=None):
        from app.forms.supplier_forms import SupplierPaymentForm
        
        self.payment_id = payment_id
        self.invoice_id = invoice_id  # NEW: Add invoice context
        self.is_edit = payment_id is not None
        self.is_invoice_specific = invoice_id is not None  # NEW: Track invoice context
        
        # Determine page title based on context
        if self.is_invoice_specific:
            page_title = "Payment for Invoice"
        elif self.is_edit:
            page_title = "Edit Payment"
        else:
            page_title = "Record Payment"
        
        super().__init__(
            form_class=SupplierPaymentForm,
            template_path='supplier/payment_form.html',
            success_url=self._get_success_url,
            success_message="Payment recorded successfully" if not self.is_edit else "Payment updated successfully",
            page_title=page_title,
            additional_context=self.get_additional_context
        )

    
    def _get_success_url(self, result):
        """Enhanced success URL for invoice context"""
        from flask import url_for
        
        if self.is_invoice_specific and self.invoice_id:
            # Return to the invoice view
            return url_for('supplier_views.view_supplier_invoice', invoice_id=self.invoice_id)
        elif self.is_edit:
            # Return to payment view
            return url_for('supplier_views.view_payment', payment_id=self.payment_id)
        else:
            # Return to payment list
            return url_for('supplier_views.payment_list')
    
    def get_additional_context(self, *args, **kwargs):
        """Enhanced context with CORRECTED invoice balance calculation for partial payments"""
        context = super().get_additional_context(*args, **kwargs) if hasattr(super(), 'get_additional_context') else {}
        
        try:
            from flask_login import current_user
            
            # EXISTING: Get branch context (keep as-is)
            try:
                from app.services.branch_service import get_branch_context_for_form
                branch_context = get_branch_context_for_form(
                    current_user.user_id,
                    current_user.hospital_id,
                    module_name='payment',
                    action='add' if not self.is_edit else 'edit'
                )
                
                context.update({
                    'branches': branch_context.get('branches', []),
                    'default_branch_id': branch_context.get('default_branch_id'),
                    'branch_context': branch_context,
                    'payment_config': PAYMENT_CONFIG,
                    'is_edit': self.is_edit
                })
            except Exception as e:
                current_app.logger.warning(f"Could not get branch context: {str(e)}")
                context.update({
                    'branches': [],
                    'default_branch_id': None,
                    'branch_context': {'error': str(e)},
                    'payment_config': PAYMENT_CONFIG,
                    'is_edit': self.is_edit
                })
            
            #   CRITICAL FIX: Enhanced invoice context with CORRECT balance calculation
            if self.is_invoice_specific and self.invoice_id:
                try:
                    from app.services.supplier_service import get_supplier_invoice_by_id
                    from app.services.database_service import get_db_session
                    from app.models.transaction import SupplierPayment
                    from sqlalchemy import func
                    import uuid
                    
                    # Get invoice data
                    invoice = get_supplier_invoice_by_id(
                        invoice_id=uuid.UUID(self.invoice_id),
                        hospital_id=current_user.hospital_id
                    )
                    
                    if invoice:
                        #   CRITICAL FIX: Calculate ACTUAL current balance due
                        invoice_total = float(invoice.get('total_amount', 0))
                        
                        # Calculate APPROVED payments only (not pending/rejected)
                        with get_db_session(read_only=True) as session:
                            approved_payment_total = session.query(func.sum(SupplierPayment.amount)).filter_by(
                                invoice_id=uuid.UUID(self.invoice_id),
                                workflow_status='approved'  # Only count approved payments
                            ).scalar() or 0
                            approved_payment_total = float(approved_payment_total)
                        
                        # Calculate CURRENT balance due (this is what user should pay)
                        current_balance_due = invoice_total - approved_payment_total
                        
                        # Ensure balance_due is not negative
                        if current_balance_due < 0:
                            current_balance_due = 0
                        
                        current_app.logger.info(f"BALANCE CALCULATION - Invoice: {invoice.get('supplier_invoice_number')}")
                        current_app.logger.info(f"  Invoice Total: {invoice_total}")
                        current_app.logger.info(f"  Approved Payments: {approved_payment_total}")
                        current_app.logger.info(f"  CURRENT Balance Due: {current_balance_due}")
                        
                        #   UPDATED: Use CORRECTED balance in context
                        context.update({
                            'invoice': invoice,
                            'is_invoice_specific': True,
                            'invoice_balance': float(current_balance_due),  # FIXED: Use CURRENT balance
                            'supplier_name': invoice.get('supplier_name', ''),
                            'invoice_number': invoice.get('supplier_invoice_number', ''),
                            'invoice_date': invoice.get('invoice_date'),
                            'payment_due_date': invoice.get('due_date'),
                            
                            #   READONLY FIELD CONFIGURATION
                            'readonly_fields': [
                                'supplier_id',      # Can't change supplier from invoice
                                'invoice_id',       # Can't change selected invoice  
                                'branch_id',        # Can't change branch (comes from invoice)
                                'currency_code',    # Can't change currency (comes from invoice)
                                'exchange_rate'     # Can't change rate (comes from invoice)
                            ],
                            
                            #   EDITABLE FIELDS
                            'editable_fields': [
                                'amount',           # EDITABLE: User can pay partial amount
                                'payment_method',   # EDITABLE: User chooses payment method
                                'payment_date',     # EDITABLE: User chooses payment date
                                'reference_no',     # EDITABLE: User can modify reference
                                'notes',            # EDITABLE: User can add notes
                                'cash_amount',      # EDITABLE: For multi-method payments
                                'cheque_amount',    # EDITABLE: For multi-method payments
                                'bank_transfer_amount',  # EDITABLE: For multi-method payments
                                'upi_amount'        # EDITABLE: For multi-method payments
                            ],
                            
                            #   FIELD MESSAGES
                            'field_messages': {
                                'supplier_id': 'Supplier is set from invoice',
                                'invoice_id': 'Invoice is pre-selected',
                                'amount': f'Current balance due:  Rs.{current_balance_due:.2f}',
                                'branch_id': 'Branch is set from invoice',
                                'currency_code': 'Currency is set from invoice',
                                'exchange_rate': 'Exchange rate is set from invoice'
                            },
                            
                            #   UI CONFIGURATION
                            'ui_config': {
                                'show_readonly_messages': True,
                                'focus_first_editable': True,
                                'readonly_style': 'grayed_out',
                                'highlight_editable': True
                            }
                        })
                        
                        current_app.logger.info(f"Added enhanced invoice context for {invoice.get('supplier_invoice_number')}")
                        
                except Exception as e:
                    current_app.logger.error(f"Error getting invoice context: {str(e)}")
                    # Fallback for invoice-specific context
                    context.update({
                        'is_invoice_specific': True,
                        'readonly_fields': ['supplier_id', 'invoice_id'],
                        'editable_fields': ['amount', 'payment_method', 'payment_date', 'notes'],
                        'field_messages': {
                            'supplier_id': 'Supplier is set from invoice',
                            'invoice_id': 'Invoice is pre-selected',
                            'amount': 'Enter payment amount'
                        }
                    })
            else:
                #   NON-INVOICE PAYMENT: All fields editable
                context.update({
                    'is_invoice_specific': False,
                    'readonly_fields': [],
                    'editable_fields': 'all',
                    'field_messages': {},
                    'ui_config': {
                        'show_readonly_messages': False,
                        'focus_first_editable': True
                    }
                })
            
            current_app.logger.info(f"FormController.get_additional_context - Context keys: {list(context.keys())}")
            
            return context
            
        except Exception as e:
            current_app.logger.error(f"Error in get_additional_context: {str(e)}")
            return context
    
    def get_form(self, *args, **kwargs):
        """Get form instance with correct invoice balance pre-population"""
        form = super().get_form(*args, **kwargs)
        
        try:
            from flask_login import current_user
            from flask import request
            
            # Setup form choices
            try:
                from app.services.branch_service import populate_branch_choices_for_user
                populate_branch_choices_for_user(
                    form.branch_id, 
                    current_user, 
                    required=True
                )
            except Exception as branch_error:
                current_app.logger.warning(f"Branch choice setup failed: {str(branch_error)}")
                self._setup_branch_choices_manually(form, current_user)
            
            # Setup supplier choices
            from app.utils.form_helpers import populate_supplier_choices
            populate_supplier_choices(form, current_user)
            
            # Setup other choices
            try:
                self._setup_other_choices(form)
            except Exception as other_error:
                current_app.logger.warning(f"Other choices setup failed: {str(other_error)}")
            
            #   CRITICAL FIX: For invoice-specific payments, pre-populate with CORRECT balance
            if self.is_invoice_specific and self.invoice_id and request.method == 'GET':
                current_app.logger.info(f"Pre-populating form for invoice {self.invoice_id}")
                
                # Get invoice and calculate CURRENT balance
                invoice, current_balance_due = self._ensure_invoice_data_in_form(form, current_user)
                
                #   FORCE the form amount to use the correctly calculated balance
                form.amount.data = float(current_balance_due) if current_balance_due else 0.0
                form.cash_amount.data = float(current_balance_due) if current_balance_due else 0.0
                form.cheque_amount.data = 0.0
                form.bank_transfer_amount.data = 0.0
                form.upi_amount.data = 0.0
                
                current_app.logger.info(f"  FIXED: Set form amount to current balance: {current_balance_due}")
                
        except Exception as e:
            current_app.logger.error(f"Error in get_form: {str(e)}")
        
        return form
    
    def _populate_form_for_invoice(self, form):
        """Pre-populate form with invoice data - FIXED VALIDATION"""
        try:
            from app.services.supplier_service import get_supplier_invoice_by_id
            from flask_login import current_user
            from datetime import date
            import uuid
            
            current_app.logger.info(f"Pre-populating form for invoice: {self.invoice_id}")
            
            invoice = get_supplier_invoice_by_id(
                invoice_id=uuid.UUID(self.invoice_id),
                hospital_id=current_user.hospital_id
            )
            
            if invoice:
                balance_due = invoice.get('balance_due', 0) or invoice.get('total_amount', 0)
                invoice_number = invoice.get('supplier_invoice_number', 'Unknown')
                
                #   CRITICAL: Set invoice choices ALWAYS (both GET and POST)
                if hasattr(form, 'invoice_id'):
                    invoice_display = f"{invoice_number} (Balance: Rs.{balance_due:.2f})"
                    form.invoice_id.choices = [
                        ('', 'Select Invoice (Optional)'),
                        (str(self.invoice_id), invoice_display)
                    ]
                    # Set the data
                    form.invoice_id.data = str(self.invoice_id)
                
                # Only set other form data on GET request (not POST)
                if request.method == 'GET':
                    # Pre-populate form fields
                    form.supplier_id.data = str(invoice.get('supplier_id'))
                    form.amount.data = float(balance_due) if balance_due else 0.0
                    form.payment_date.data = date.today()
                    form.currency_code.data = invoice.get('currency_code', 'INR')
                    form.exchange_rate.data = float(invoice.get('exchange_rate', 1.0))
                    
                    # Set branch
                    if invoice.get('branch_id'):
                        invoice_branch_id = str(invoice.get('branch_id'))
                        
                        # Check if invoice branch is in current choices
                        current_choices = dict(form.branch_id.choices) if form.branch_id.choices else {}
                        
                        # If invoice branch is missing from choices, add it
                        if invoice_branch_id not in current_choices:
                            try:
                                from app.services.database_service import get_db_session
                                from app.models.master import Branch
                                
                                with get_db_session(read_only=True) as session:
                                    branch = session.query(Branch).filter_by(
                                        branch_id=uuid.UUID(invoice_branch_id),
                                        hospital_id=current_user.hospital_id
                                    ).first()
                                    
                                    if branch:
                                        # Add the invoice branch to choices
                                        form.branch_id.choices.append((invoice_branch_id, f"{branch.name} (Invoice Branch)"))
                                        current_app.logger.info(f"Added invoice branch '{branch.name}' to payment form choices")
                                    
                            except Exception as e:
                                current_app.logger.warning(f"Could not add invoice branch to choices: {str(e)}")
                        
                        # Now set the branch data (it should be in choices)
                        form.branch_id.data = invoice_branch_id
                        current_app.logger.info(f"Set branch_id to: {invoice_branch_id} from invoice")
                    
                    # Generate reference and notes
                    form.reference_no.data = f"PAY-{invoice_number}-{date.today().strftime('%Y%m%d')}"
                    form.notes.data = f"Payment for invoice {invoice_number}"
                    
                    # Set default payment method
                    if hasattr(form, 'payment_method'):
                        form.payment_method.data = 'cash'
                    
                    current_app.logger.info(f"SUCCESS: Form pre-populated for invoice {invoice_number}")
                    current_app.logger.info(f"  Supplier: {invoice.get('supplier_name')}")
                    current_app.logger.info(f"  Amount: Rs.{balance_due}")  #   Fixed unicode
                    current_app.logger.info(f"  Branch: {invoice.get('branch_id')}")
                else:
                    current_app.logger.info(f"Choices set for POST validation: {invoice_number}")
            else:
                current_app.logger.warning(f"Invoice {self.invoice_id} not found")
            
        except Exception as e:
            current_app.logger.error(f"Error pre-populating form for invoice: {str(e)}", exc_info=True)

    def _populate_form_for_edit(self, form):
        """Populate form with existing payment data for editing"""
        try:
            from app.services.supplier_service import get_supplier_payment_by_id
            from flask_login import current_user
            import uuid
            
            payment = get_supplier_payment_by_id(
                payment_id=uuid.UUID(self.payment_id),
                hospital_id=current_user.hospital_id
            )
            
            if payment:
                # Populate basic fields
                form.supplier_id.data = str(payment.get('supplier_id'))
                form.amount.data = payment.get('amount')
                form.payment_date.data = payment.get('payment_date')
                form.branch_id.data = str(payment.get('branch_id'))
                
                # Populate multi-method amounts
                form.cash_amount.data = payment.get('cash_amount', 0)
                form.cheque_amount.data = payment.get('cheque_amount', 0)
                form.bank_transfer_amount.data = payment.get('bank_transfer_amount', 0)
                form.upi_amount.data = payment.get('upi_amount', 0)
                
                # Populate method-specific details
                form.cheque_number.data = payment.get('cheque_number')
                form.cheque_date.data = payment.get('cheque_date')
                form.cheque_bank.data = payment.get('cheque_bank')
                form.bank_account_name.data = payment.get('bank_account_name')
                form.bank_reference_number.data = payment.get('bank_reference_number')
                form.upi_transaction_id.data = payment.get('upi_transaction_id')
                form.upi_app_name.data = payment.get('upi_app_name')
                
                # Other fields
                form.reference_no.data = payment.get('reference_no')
                form.notes.data = payment.get('notes')
                form.currency_code.data = payment.get('currency_code', 'INR')
                form.exchange_rate.data = payment.get('exchange_rate', 1.0)
                
                # TDS fields
                form.tds_applicable.data = payment.get('tds_applicable', False)
                form.tds_rate.data = payment.get('tds_rate', 0)
                form.tds_amount.data = payment.get('tds_amount', 0)
                form.tds_reference.data = payment.get('tds_reference')
                
        except Exception as e:
            current_app.logger.error(f"Error populating payment form for edit: {str(e)}")
    
    def handle_post(self, form, *args, **kwargs):
        """Enhanced POST handling with better error messages for payment validation"""
        try:
            from flask_login import current_user
            from flask import flash, current_app
            
            current_app.logger.info("Starting form validation for payment submission")
            
            # CRITICAL FIX: Ensure invoice data is populated before processing
            if self.is_invoice_specific and self.invoice_id:
                current_app.logger.info(f"Invoice-specific payment detected - ensuring form data for invoice {self.invoice_id}")
                try:
                    invoice, current_balance_due = self._ensure_invoice_data_in_form(form, current_user)
                except Exception as e:
                    current_app.logger.error(f"Error loading invoice data: {str(e)}")
                    flash("Error loading invoice information. Please try again.", "error")
                    return self.render_form(form, *args, **kwargs)
            
            if form.validate_on_submit():
                current_app.logger.info("Form validation passed - processing payment")
                try:
                    result = self.process_form(form, *args, **kwargs)
                    flash(self.success_message, "success")
                    
                    if callable(self.success_url):
                        return redirect(self.success_url(result))
                    return redirect(self.success_url)
                    
                except ValueError as ve:
                    # ENHANCED: Better error handling for validation failures
                    error_message = str(ve)
                    current_app.logger.error(f"Payment validation error: {error_message}")
                    
                    # NEW: Parse and enhance overpayment error messages
                    if "exceeds remaining balance" in error_message:
                        try:
                            # Extract overpayment amount from error message - handle both Rs. and ₹
                            import re
                            overpay_match = re.search(r'(?:Rs\.|₹)(\d+\.?\d*)', error_message)
                            if overpay_match:
                                overpayment = float(overpay_match.group(1))
                                
                                # Get current invoice details for better context
                                if self.is_invoice_specific and self.invoice_id:
                                    invoice, current_balance = self._ensure_invoice_data_in_form(form, current_user)
                                    invoice_total = float(invoice.get('total_amount', 0))
                                    invoice_number = invoice.get('supplier_invoice_number', 'Unknown')
                                    payment_amount = float(form.amount.data or 0)
                                    
                                    # ENHANCED: Show comprehensive payment context (user-friendly message with ₹)
                                    enhanced_message = (
                                        f"Payment amount of ₹{payment_amount:.2f} exceeds the remaining balance by ₹{overpayment:.2f}. "
                                        f"Invoice {invoice_number} (Total: ₹{invoice_total:.2f}) has only ₹{current_balance:.2f} remaining to be paid. "
                                        f"Please enter an amount up to ₹{current_balance:.2f}."
                                    )
                                    flash(enhanced_message, "error")
                                else:
                                    flash(f"Payment amount exceeds remaining balance by ₹{overpayment:.2f}. Please reduce the payment amount.", "error")
                            else:
                                # Fallback if we can't parse the amount
                                flash("Payment amount exceeds the remaining invoice balance. Please check the amount and try again.", "error")
                        except Exception as parse_error:
                            current_app.logger.warning(f"Could not parse overpayment error: {parse_error}")
                            flash("Payment amount exceeds the remaining invoice balance. Please check the amount and try again.", "error")
                            
                    elif "already fully paid" in error_message:
                        flash("This invoice is already fully paid. No additional payments can be made.", "error")
                    elif "validation failed" in error_message.lower():
                        # Extract the actual validation errors from the message
                        validation_errors = error_message.replace("Payment validation failed: ", "")
                        # Clean up any Rs. symbols for display (replace with ₹)
                        clean_errors = validation_errors.replace("Rs.", "₹")
                        flash(f"Payment validation failed: {clean_errors}", "error")
                    else:
                        # Generic error handling - clean up Rs. for display
                        clean_error = error_message.replace("Rs.", "₹")
                        flash(f"Payment error: {clean_error}", "error")
                        
                except Exception as e:
                    current_app.logger.error(f"Error processing payment form: {str(e)}", exc_info=True)
                    flash(f"Error processing payment: {str(e)}", "error")
            else:
                # ENHANCED: Show form validation errors with context
                current_app.logger.error(f"Form validation failed: {form.errors}")
                
                # Show field-specific errors
                for field_name, errors in form.errors.items():
                    for error in errors:
                        flash(f"{field_name.replace('_', ' ').title()}: {error}", "error")
                
                # NEW: Add helpful context for payment amount errors
                if hasattr(form, 'amount') and form.amount.errors and self.is_invoice_specific:
                    try:
                        invoice, current_balance = self._ensure_invoice_data_in_form(form, current_user)
                        invoice_number = invoice.get('supplier_invoice_number', 'Unknown')
                        flash(f"For reference: Invoice {invoice_number} has ₹{current_balance:.2f} remaining to be paid.", "info")
                    except Exception:
                        pass  # Silently ignore if we can't get invoice data
            
            # If we get here, validation failed or there was an error - return to form
            return self.render_form(form, *args, **kwargs)
            
        except Exception as e:
            current_app.logger.error(f"Error processing payment form: {str(e)}", exc_info=True)
            flash(f"An unexpected error occurred while processing the payment: {str(e)}", "error")
            return self.render_form(form, *args, **kwargs)

    def process_form(self, form, *args, **kwargs):
        """
        Process payment form with ENHANCED support for invoice-specific payments
        CRITICAL FIX: Handle case where readonly fields don't submit properly
        """
        try:
            from app.services.supplier_service import record_supplier_payment, update_supplier_payment
            from flask_login import current_user
            
            # CRITICAL FIX: For invoice-specific payments, ensure required fields are populated
            # even if they didn't come through in the form submission
            if self.is_invoice_specific and self.invoice_id:
                self._ensure_invoice_data_in_form(form, current_user)
            
            # Prepare payment data
            payment_data = {
                'supplier_id': form.supplier_id.data,
                'invoice_id': form.invoice_id.data if hasattr(form, 'invoice_id') and form.invoice_id.data else None,
                'amount': float(form.amount.data),
                'payment_date': form.payment_date.data,
                'branch_id': form.branch_id.data,
                
                # FIXED: Add payment_method field that was missing
                'payment_method': form.payment_method.data if hasattr(form, 'payment_method') and form.payment_method.data else 'mixed',
                
                # Multi-method amounts
                'cash_amount': float(form.cash_amount.data or 0),
                'cheque_amount': float(form.cheque_amount.data or 0),
                'bank_transfer_amount': float(form.bank_transfer_amount.data or 0),
                'upi_amount': float(form.upi_amount.data or 0),
                
                # Method-specific details
                'cheque_number': form.cheque_number.data,
                'cheque_date': form.cheque_date.data,
                'cheque_bank': form.cheque_bank.data,
                'bank_account_name': form.bank_account_name.data,
                'bank_reference_number': form.bank_reference_number.data,
                'upi_transaction_id': form.upi_transaction_id.data,
                'upi_app_name': form.upi_app_name.data,
                
                # Additional fields
                'reference_no': form.reference_no.data,
                'notes': form.notes.data,
                'currency_code': form.currency_code.data if hasattr(form, 'currency_code') else 'INR',
                'exchange_rate': float(form.exchange_rate.data) if hasattr(form, 'exchange_rate') else 1.0,
                
                # TDS fields (if present)
                'tds_applicable': form.tds_applicable.data if hasattr(form, 'tds_applicable') else False,
                'tds_rate': float(form.tds_rate.data or 0) if hasattr(form, 'tds_rate') else 0,
                'tds_amount': float(form.tds_amount.data or 0) if hasattr(form, 'tds_amount') else 0,
                'tds_reference': form.tds_reference.data if hasattr(form, 'tds_reference') else None
            }
            
            # Handle document uploads
            documents = []
            for field_name, document_type in [
                ('receipt_document', 'receipt'),
                ('bank_statement', 'bank_statement'),
                ('authorization_document', 'authorization')
            ]:
                if hasattr(form, field_name):
                    file_field = getattr(form, field_name)
                    if file_field.data:
                        documents.append({
                            'file': file_field.data,
                            'document_type': document_type,
                            'description': f'{document_type.replace("_", " ").title()} for payment'
                        })
            
            if documents:
                payment_data['documents'] = documents
            
            # DEBUGGING: Log payment data
            current_app.logger.info(f"Payment data prepared for submission:")
            current_app.logger.info(f"  supplier_id: {payment_data.get('supplier_id')}")
            current_app.logger.info(f"  amount: {payment_data.get('amount')}")
            current_app.logger.info(f"  payment_method: {payment_data.get('payment_method')}")
            current_app.logger.info(f"  branch_id: {payment_data.get('branch_id')}")
            
            # Record or update payment
            if self.is_edit:
                result = update_supplier_payment(
                    payment_id=uuid.UUID(self.payment_id),
                    payment_data=payment_data,
                    hospital_id=current_user.hospital_id,
                    current_user_id=current_user.user_id
                )
            else:
                result = record_supplier_payment(
                    hospital_id=current_user.hospital_id,
                    payment_data=payment_data,
                    current_user_id=current_user.user_id
                )
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error processing payment form: {str(e)}", exc_info=True)
            raise

    def _ensure_invoice_data_in_form(self, form, current_user):
        """
        ENHANCED: Calculate and return current balance due for invoice
        """
        try:
            from app.services.supplier_service import get_supplier_invoice_by_id
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierPayment
            from sqlalchemy import func
            import uuid
            from flask import request
            
            current_app.logger.info(f"Calculating balance for invoice {self.invoice_id}")
            
            # Get invoice data from database
            invoice = get_supplier_invoice_by_id(
                invoice_id=uuid.UUID(self.invoice_id),
                hospital_id=current_user.hospital_id
            )
            
            if not invoice:
                raise ValueError(f"Invoice {self.invoice_id} not found")
            
            #   CRITICAL FIX: Calculate current balance due from APPROVED payments only
            invoice_total = float(invoice.get('total_amount', 0))
            
            # Calculate actual payment total from APPROVED payments only
            with get_db_session(read_only=True) as session:
                approved_payment_total = session.query(func.sum(SupplierPayment.amount)).filter_by(
                    invoice_id=uuid.UUID(self.invoice_id),
                    workflow_status='approved'  #   CRITICAL: Only approved payments
                ).scalar() or 0
                approved_payment_total = float(approved_payment_total)
            
            # Calculate current balance due
            balance_due = invoice_total - approved_payment_total
            
            # Ensure balance_due is not negative
            if balance_due < 0:
                balance_due = 0
            
            invoice_number = invoice.get('supplier_invoice_number', 'INV')
            
            current_app.logger.info(f"  BALANCE CALC: Invoice {invoice_number}: Total={invoice_total}, Approved={approved_payment_total}, Balance={balance_due}")
            
            # ===================================================================
            # Set critical form fields
            # ===================================================================
            
            # 1. Supplier ID
            if not form.supplier_id.data or form.supplier_id.data.strip() == '':
                form.supplier_id.data = str(invoice.get('supplier_id'))
                current_app.logger.info(f"Set supplier_id to '{form.supplier_id.data}'")
            
            # 2. Invoice ID
            if hasattr(form, 'invoice_id'):
                if not form.invoice_id.data or form.invoice_id.data.strip() == '':
                    form.invoice_id.data = str(self.invoice_id)
                    current_app.logger.info(f"Set invoice_id to '{form.invoice_id.data}'")
            
            # 3. Branch ID - FIXED: Always use branch from invoice for invoice-specific payments
            if invoice.get('branch_id'):
                invoice_branch_id = str(invoice.get('branch_id'))
                
                # DEBUG: Log current choices
                current_choices = dict(form.branch_id.choices) if form.branch_id.choices else {}
                current_app.logger.info(f"DEBUG: Current branch choices: {list(current_choices.keys())}")
                current_app.logger.info(f"DEBUG: Invoice branch needed: {invoice_branch_id}")
                current_app.logger.info(f"DEBUG: Invoice branch in choices: {invoice_branch_id in current_choices}")
                
                # Ensure the invoice branch is in form choices
                if invoice_branch_id not in current_choices:
                    current_app.logger.info(f"DEBUG: Invoice branch NOT in choices, adding it")
                    try:
                        from app.services.database_service import get_db_session
                        from app.models.master import Branch
                        
                        with get_db_session(read_only=True) as session:
                            branch = session.query(Branch).filter_by(
                                branch_id=uuid.UUID(invoice_branch_id),
                                hospital_id=current_user.hospital_id
                            ).first()
                            
                            if branch:
                                # Add the invoice branch to choices
                                form.branch_id.choices.append((invoice_branch_id, f"{branch.name} (Invoice Branch)"))
                                current_app.logger.info(f"Added invoice branch '{branch.name}' to choices")
                                
                                # DEBUG: Log updated choices
                                updated_choices = dict(form.branch_id.choices)
                                current_app.logger.info(f"DEBUG: Updated branch choices: {list(updated_choices.keys())}")
                            else:
                                current_app.logger.error(f"DEBUG: Branch {invoice_branch_id} not found in database!")
                            
                    except Exception as e:
                        current_app.logger.error(f"Could not add invoice branch to choices: {str(e)}", exc_info=True)
                else:
                    current_app.logger.info(f"DEBUG: Invoice branch already in choices")
                
                # Always set branch from invoice for invoice-specific payments
                form.branch_id.data = invoice_branch_id
                current_app.logger.info(f"Set branch_id to '{invoice_branch_id}' from invoice")
                
                # DEBUG: Final verification
                final_choices = dict(form.branch_id.choices) if form.branch_id.choices else {}
                current_app.logger.info(f"DEBUG: Final branch data: {form.branch_id.data}")
                current_app.logger.info(f"DEBUG: Final choices contain branch: {form.branch_id.data in final_choices}")
                if form.branch_id.data in final_choices:
                    current_app.logger.info(f"DEBUG: Branch will display as: {final_choices[form.branch_id.data]}")
            
            # 4. Set other fields only on GET request
            if request.method == 'GET':
                # Set other default fields
                form.payment_date.data = date.today()
                form.reference_no.data = f"PAY-{invoice_number}-{date.today().strftime('%Y%m%d')}"
                form.notes.data = f"Payment for invoice {invoice_number}"
                
                # Set payment method
                if hasattr(form, 'payment_method'):
                    form.payment_method.data = 'cash'
                
                # Set currency fields if they exist
                if hasattr(form, 'currency_code'):
                    form.currency_code.data = invoice.get('currency_code', 'INR')
                if hasattr(form, 'exchange_rate'):
                    form.exchange_rate.data = float(invoice.get('exchange_rate', 1.0))
            
            return invoice, balance_due
            
        except Exception as e:
            current_app.logger.error(f"Error calculating invoice balance: {str(e)}", exc_info=True)
            raise

    def _debug_form_state(self, form, stage):
        """Debug method to track form state"""
        current_app.logger.info(f"=== FORM STATE: {stage} ===")
        current_app.logger.info(f"Amount: {form.amount.data}")
        current_app.logger.info(f"Cash Amount: {getattr(form, 'cash_amount', {}).data if hasattr(form, 'cash_amount') else 'N/A'}")
        current_app.logger.info(f"Supplier ID: {form.supplier_id.data}")
        current_app.logger.info(f"Invoice ID: {getattr(form, 'invoice_id', {}).data if hasattr(form, 'invoice_id') else 'N/A'}")
        current_app.logger.info("==========================")

    def _setup_other_choices(self, form):
        """Setup currency and payment method choices"""
        try:
            # Set currency choices if not already set
            if not form.currency_code.choices or form.currency_code.choices == []:
                form.currency_code.choices = [
                    ('INR', 'INR'),
                    ('USD', 'USD'),
                    ('EUR', 'EUR')
                ]
            
            # Set payment method choices if field exists and not already set
            if hasattr(form, 'payment_method'):
                if not form.payment_method.choices or form.payment_method.choices == []:
                    form.payment_method.choices = [
                        ('', 'Select Payment Method'),
                        ('cash', 'Cash'),
                        ('cheque', 'Cheque'),
                        ('bank_transfer', 'Bank Transfer'),
                        ('upi', 'UPI'),
                        ('mixed', 'Multiple Methods')
                    ]
            
            # Set UPI app choices if field exists
            if hasattr(form, 'upi_app_name'):
                if not form.upi_app_name.choices or form.upi_app_name.choices == []:
                    form.upi_app_name.choices = [
                        ('', 'Select UPI App'),
                        ('gpay', 'Google Pay'),
                        ('phonepe', 'PhonePe'),
                        ('paytm', 'Paytm'),
                        ('bhim', 'BHIM UPI'),
                        ('other', 'Other')
                    ]
            
        except Exception as e:
            current_app.logger.error(f"Error setting up other choices: {str(e)}")

    def _apply_readonly_fields_for_invoice(self, form, current_user):
        """
        TARGETED FIX: Apply readonly enforcement to form fields for invoice payments
        """
        try:
            from app.services.supplier_service import get_supplier_invoice_by_id
            from flask import request
            import uuid
            
            # Get invoice data
            invoice = get_supplier_invoice_by_id(
                invoice_id=uuid.UUID(self.invoice_id),
                hospital_id=current_user.hospital_id
            )
            
            if not invoice:
                current_app.logger.warning(f"Invoice {self.invoice_id} not found for readonly setup")
                return
            
            balance_due = invoice.get('balance_due', 0) or invoice.get('total_amount', 0)
            
            # CRITICAL FIX: Set form field properties to readonly/disabled
            # Only on GET requests to avoid interfering with form submission
            if request.method == 'GET':
                
                # READONLY FIELDS: Disable these fields completely
                if hasattr(form.supplier_id, 'render_kw'):
                    form.supplier_id.render_kw = form.supplier_id.render_kw or {}
                    form.supplier_id.render_kw.update({'readonly': True, 'class': 'readonly-field'})
                
                if hasattr(form.amount, 'render_kw'):
                    form.amount.render_kw = form.amount.render_kw or {}
                    form.amount.render_kw.update({'readonly': True, 'disabled': True})
                
                if hasattr(form.branch_id, 'render_kw'):
                    form.branch_id.render_kw = form.branch_id.render_kw or {}
                    form.branch_id.render_kw.update({'readonly': True, 'onclick': 'return false;', 'style': 'pointer-events: none; background-color: #f3f4f6;'})
                
                # Set invoice dropdown to readonly (only show selected invoice)
                if hasattr(form, 'invoice_id'):
                    invoice_display = f"{invoice.get('supplier_invoice_number', 'N/A')} - Rs.{balance_due:.2f}"
                    form.invoice_id.choices = [
                        (str(self.invoice_id), invoice_display)
                    ]
                    form.invoice_id.data = str(self.invoice_id)
                    if hasattr(form.invoice_id, 'render_kw'):
                        form.invoice_id.render_kw = form.invoice_id.render_kw or {}
                        form.invoice_id.render_kw.update({'disabled': True})
                
                # Pre-populate readonly fields with invoice data
                form.supplier_id.data = str(invoice.get('supplier_id'))
                form.amount.data = float(balance_due) if balance_due else 0.0
                form.payment_date.data = date.today()
                
                # Set branch from invoice
                if invoice.get('branch_id'):
                    form.branch_id.data = str(invoice.get('branch_id'))
                
                # Set currency fields if they exist
                if hasattr(form, 'currency_code'):
                    form.currency_code.data = invoice.get('currency_code', 'INR')
                    if hasattr(form.currency_code, 'render_kw'):
                        form.currency_code.render_kw = form.currency_code.render_kw or {}
                        form.currency_code.render_kw.update({'readonly': True, 'disabled': True})
                
                if hasattr(form, 'exchange_rate'):
                    form.exchange_rate.data = float(invoice.get('exchange_rate', 1.0))
                    if hasattr(form.exchange_rate, 'render_kw'):
                        form.exchange_rate.render_kw = form.exchange_rate.render_kw or {}
                        form.exchange_rate.render_kw.update({'readonly': True, 'disabled': True})
                
                # Generate reference and notes
                invoice_number = invoice.get('supplier_invoice_number', 'INV')
                form.reference_no.data = f"PAY-{invoice_number}-{date.today().strftime('%Y%m%d')}"
                form.notes.data = f"Payment for invoice {invoice_number}"
                
                # Set default payment method to cash if field exists
                if hasattr(form, 'payment_method'):
                    form.payment_method.data = 'cash'
                
                current_app.logger.info(f"SUCCESS: Applied readonly fields for invoice {invoice_number}")
                current_app.logger.info(f"  Supplier: {invoice.get('supplier_name')}")
                current_app.logger.info(f"  Amount: Rs.{balance_due:.2f}")
                current_app.logger.info(f"  Branch: {invoice.get('branch_id')}")
            
        except Exception as e:
            current_app.logger.error(f"Error applying readonly fields: {str(e)}", exc_info=True)


class PaymentApprovalController:
    """Controller for payment approval workflow"""
    
    def __init__(self, payment_id):
        self.payment_id = payment_id
    
    def handle_approval(self):
        """Handle payment approval/rejection"""
        from app.forms.supplier_forms import PaymentApprovalForm
        from flask import render_template, request, flash, redirect, url_for
        from flask_login import current_user
        
        form = PaymentApprovalForm()
        
        # Get payment details
        try:
            from app.services.supplier_service import get_supplier_payment_by_id
            import uuid
            
            payment = get_supplier_payment_by_id(
                uuid.UUID(self.payment_id), 
                current_user.hospital_id
            )
            if not payment:
                flash('Payment not found', 'error')
                return redirect(url_for('supplier_views.payment_list'))
        except Exception as e:
            flash(f'Error loading payment: {str(e)}', 'error')
            return redirect(url_for('supplier_views.payment_list'))
        
        if request.method == 'POST' and form.validate_on_submit():
            try:
                if form.action.data == 'approve':
                    from app.services.supplier_service import approve_supplier_payment
                    result = approve_supplier_payment(
                        payment_id=uuid.UUID(self.payment_id),
                        hospital_id=current_user.hospital_id,
                        current_user_id=current_user.user_id,
                        approval_notes=form.approval_notes.data
                    )
                    flash('Payment approved successfully', 'success')
                elif form.action.data == 'reject':
                    from app.services.supplier_service import reject_supplier_payment
                    result = reject_supplier_payment(
                        payment_id=uuid.UUID(self.payment_id),
                        hospital_id=current_user.hospital_id,
                        current_user_id=current_user.user_id,
                        rejection_reason=form.approval_notes.data
                    )
                    flash('Payment rejected', 'warning')
                else:
                    flash('More information requested from submitter', 'info')
                
                return redirect(url_for('supplier_views.view_payment', payment_id=self.payment_id))
                
            except Exception as e:
                flash(f'Error processing approval: {str(e)}', 'error')
        
        return render_template(
            'supplier/payment_approval.html',
            form=form,
            payment=payment,
            title='Payment Approval'
        )
    
class SimpleCreditNoteController(FormController):
    """
    Phase 1: Simple credit note controller
    Following your existing FormController patterns
    UPDATED: Uses centralized creditnote_service
    """
    
    def __init__(self, payment_id):
        # Import form locally to avoid circular import (your pattern)
        from app.forms.supplier_forms import SupplierCreditNoteForm
        
        self.payment_id = payment_id
        
        super().__init__(
            form_class=SupplierCreditNoteForm,
            template_path='supplier/credit_note_form.html',
            success_url=self._get_success_url,
            success_message="Credit note created successfully",
            page_title="Create Credit Note",
            additional_context=self.get_additional_context
        )
    
    def _get_success_url(self, result):
        """Return to payment view after creation - following your pattern"""
        from flask import url_for
        return url_for('supplier_views.view_payment', payment_id=self.payment_id)
    
    def get_additional_context(self, *args, **kwargs):
        """
        Get context data for credit note form
        Following your existing additional_context pattern
        UPDATED: Uses creditnote_service
        """
        context = super().get_additional_context(*args, **kwargs) if hasattr(super(), 'get_additional_context') else {}
        
        try:
            from flask_login import current_user
            # UPDATED: Import from creditnote_service
            from app.services.credit_note_service import get_supplier_payment_by_id_with_credits
            
            # Get payment details with credit info using centralized service
            payment = get_supplier_payment_by_id_with_credits(
                payment_id=uuid.UUID(self.payment_id),
                hospital_id=current_user.hospital_id,
                current_user_id=current_user.user_id
            )
            
            if payment:
                context.update({
                    'payment': payment,
                    'can_create_credit_note': payment.get('can_create_credit_note', False),
                    'available_amount': payment.get('net_payment_amount', 0),
                    'existing_credits': payment.get('existing_credit_notes', [])
                })
            else:
                context['error'] = 'Payment not found'
            
        except Exception as e:
            current_app.logger.error(f"Error getting credit note context: {str(e)}")
            context['error'] = f"Error loading payment details: {str(e)}"
        
        return context
    
    def get_form(self, *args, **kwargs):
        """
        Setup form with payment data
        Following your existing get_form pattern
        UPDATED: Uses creditnote_service
        """
        form = super().get_form(*args, **kwargs)
        
        if request.method == 'GET':
            try:
                self._setup_form_defaults(form)
            except Exception as e:
                current_app.logger.error(f"Error setting up form: {str(e)}")
                flash(f"Error loading form: {str(e)}", 'error')
        
        return form
    
    def _setup_form_defaults(self, form):
        """
        Pre-populate form fields with payment data
        Following your existing form population patterns
        UPDATED: Uses creditnote_service
        """
        try:
            from flask_login import current_user
            # UPDATED: Import from creditnote_service
            from app.services.credit_note_service import get_supplier_payment_by_id_with_credits
            
            # Get payment details
            payment = get_supplier_payment_by_id_with_credits(
                payment_id=uuid.UUID(self.payment_id),
                hospital_id=current_user.hospital_id,
                current_user_id=current_user.user_id
            )
            
            if not payment:
                raise ValueError("Payment not found")
            
            if not payment.get('can_create_credit_note', False):
                raise ValueError("Credit note cannot be created for this payment")
            
            # Set hidden fields
            form.payment_id.data = str(payment['payment_id'])
            form.supplier_id.data = str(payment['supplier_id'])
            form.branch_id.data = str(payment['branch_id'])
            
            # Set credit note details using utility functions
            from app.utils.credit_note_utils import generate_credit_note_number
            credit_note_number = generate_credit_note_number(payment['reference_no'])
            form.credit_note_number.data = credit_note_number
            form.credit_note_date.data = date.today()
            form.credit_amount.data = float(payment.get('net_payment_amount', 0))
            
            # Set reference fields (readonly)
            form.payment_reference.data = payment['reference_no']
            form.supplier_name.data = payment['supplier_name']
            
            current_app.logger.info(f"Form setup completed for payment {self.payment_id}")
            
        except Exception as e:
            current_app.logger.error(f"Error setting up form defaults: {str(e)}")
            raise
    
    def process_form(self, form, *args, **kwargs):
        """
        Process credit note creation
        Following your existing process_form pattern
        UPDATED: Uses creditnote_service
        """
        try:
            from flask_login import current_user
            # UPDATED: Import from creditnote_service
            from app.services.credit_note_service import (
                validate_credit_note_creation_simple,
                create_simple_credit_note
            )
            
            # Validate before processing (your validation pattern)
            validation_result = validate_credit_note_creation_simple(
                payment_id=uuid.UUID(form.payment_id.data),
                credit_amount=float(form.credit_amount.data),
                hospital_id=current_user.hospital_id,
                current_user_id=current_user.user_id
            )
            
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])
            
            # Prepare credit note data
            credit_note_data = {
                'payment_id': uuid.UUID(form.payment_id.data),
                'credit_note_number': form.credit_note_number.data,
                'credit_note_date': form.credit_note_date.data,
                'credit_amount': float(form.credit_amount.data),
                'reason_code': form.reason_code.data,
                'credit_reason': form.credit_reason.data,
                'branch_id': uuid.UUID(form.branch_id.data) if form.branch_id.data else None
            }
            
            # Create credit note using centralized service
            result = create_simple_credit_note(
                hospital_id=current_user.hospital_id,
                credit_note_data=credit_note_data,
                current_user_id=current_user.user_id
            )
            
            current_app.logger.info(f"Credit note created: {result.get('credit_note_number')}")
            
            return result
            
        except ValueError as ve:
            current_app.logger.warning(f"Validation error: {str(ve)}")
            flash(f"Error: {str(ve)}", 'error')
            raise
        except Exception as e:
            current_app.logger.error(f"Error processing credit note: {str(e)}")
            flash(f"Error creating credit note: {str(e)}", 'error')
            raise

# ENHANCEMENT: Helper function to update existing payment view controller
def enhance_payment_view_with_credits(payment_id, current_user_id, hospital_id):
    """
    Helper function to get enhanced payment view data
    Can be used in existing payment view controller
    Following your existing helper function patterns
    UPDATED: Uses creditnote_service
    """
    try:
        # UPDATED: Import from creditnote_service
        from app.services.credit_note_service import get_supplier_payment_by_id_with_credits
        
        # Get payment with credit information
        payment = get_supplier_payment_by_id_with_credits(
            payment_id=uuid.UUID(payment_id),
            hospital_id=hospital_id,
            current_user_id=current_user_id
        )
        
        if not payment:
            return None
        
        # Add credit note creation URL if allowed
        if payment.get('can_create_credit_note', False):
            from flask import url_for
            payment['create_credit_note_url'] = url_for(
                'supplier_views.create_credit_note', 
                payment_id=payment_id
            )
        
        return payment
        
    except Exception as e:
        current_app.logger.error(f"Error enhancing payment view: {str(e)}")
        return None

# ENHANCEMENT: Simple permission check function
def can_user_create_credit_note(user, payment_id):
    """
    Simple permission check for credit note creation
    Following your existing permission checking patterns
    UPDATED: Uses creditnote_service
    """
    try:
        from app.services.permission_service import has_permission
        from app.utils.credit_note_utils import get_credit_note_permission
        # UPDATED: Import from creditnote_service
        from app.services.credit_note_service import get_supplier_payment_by_id_with_credits
        
        # Check basic permission
        required_permission = get_credit_note_permission('CREATE')
        if not has_permission(user, 'supplier', 'edit'):
            return False
        
        # Check if payment allows credit notes
        payment = get_supplier_payment_by_id_with_credits(
            payment_id=uuid.UUID(payment_id),
            hospital_id=user.hospital_id,
            current_user_id=user.user_id
        )
        
        return payment and payment.get('can_create_credit_note', False)
        
    except Exception as e:
        current_app.logger.error(f"Error checking credit note permission: {str(e)}")
        return False
