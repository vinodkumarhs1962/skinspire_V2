# app/controllers/supplier_controller.py

from flask import current_app, flash, jsonify, request
import uuid
from datetime import datetime
import json
from app.controllers.form_controller import FormController
from app.services.database_service import get_db_session
from app.models.master import Medicine, Supplier, Branch
from app.models.transaction import PurchaseOrderHeader
from app.services.permission_service import (
    get_user_branch_context,
    has_branch_permission
)
from app.services.branch_service import (
    validate_entity_branch_access  # Use centralized function instead of local helper
)
import logging

logger = logging.getLogger(__name__)

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
        """Get form instance with initial data for editing"""
        form = super().get_form(*args, **kwargs)
        
        if self.is_edit:
            try:
                from flask_login import current_user
                with get_db_session(read_only=True) as session:
                    supplier = session.query(Supplier).filter_by(
                        supplier_id=self.supplier_id,
                        hospital_id=current_user.hospital_id
                    ).first()
                    
                    if supplier:
                        # Populate form with existing data
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
        """Get success URL using local import to avoid circular reference"""
        from flask import url_for
        return url_for('supplier_views.view_supplier_invoice', invoice_id=result['invoice_id'])
    
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
                
                # EXISTING: Get purchase orders and other data (unchanged)
                pos = session.query(PurchaseOrderHeader).filter_by(
                    hospital_id=current_user.hospital_id,
                    status='approved'
                ).all()
                
                # Get supplier information for each PO
                po_details = []
                po_suppliers = {}  # To store supplier_id for each PO
                
                for po in pos:
                    po_copy = get_detached_copy(po)
                    
                    # Get supplier name for display in dropdown
                    supplier = session.query(Supplier).filter_by(
                        supplier_id=po.supplier_id
                    ).first()
                    
                    if supplier:
                        po_copy.supplier_name = supplier.supplier_name
                        
                    # Add to mapping
                    po_suppliers[str(po_copy.po_id)] = str(po.supplier_id)
                    
                    po_details.append(po_copy)
                    
                context['purchase_orders'] = po_details
                context['po_suppliers'] = po_suppliers  # Add mapping to context
                
                # EXISTING: Get medicines for dropdown (unchanged)
                from app.models.master import Medicine
                medicines = session.query(Medicine).filter_by(
                    hospital_id=current_user.hospital_id
                ).order_by(Medicine.medicine_name).limit(100).all()
                
                context['medicines'] = [get_detached_copy(medicine) for medicine in medicines]

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
        
        # EXISTING: Add flag to indicate if we have pre-populated PO data (unchanged)
        context['has_po_data'] = self.po_id is not None
        
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
            from flask import request
            
            # Get additional context (which includes suppliers and POs)
            context = self.get_additional_context(*args, **kwargs)
            
            # Set choices for supplier dropdown
            suppliers = context.get('suppliers', [])
            form.supplier_id.choices = [('', 'Select Supplier')] + [
                (str(supplier['supplier_id']), supplier['supplier_name']) 
                for supplier in suppliers
            ]
            
            # Set choices for purchase order dropdown
            purchase_orders = context.get('purchase_orders', [])
            
            # Create list of choices
            po_choices = [('', 'Select Purchase Order')]
            for po in purchase_orders:
                po_text = f"{po.po_number} - {po.supplier_name if hasattr(po, 'supplier_name') else ''}"
                po_choices.append((str(po.po_id), po_text))
                
            form.po_id.choices = po_choices

            # Set initial values from request parameters (for PO selection)
            po_id = request.args.get('po_id') or self.po_id
            if po_id:
                try:
                    # Validate PO ID format
                    import uuid
                    valid_po_id = str(uuid.UUID(po_id))
                    form.po_id.data = valid_po_id
                    
                    # Get supplier_id for this PO from our mapping
                    po_suppliers = context.get('po_suppliers', {})
                    supplier_id = po_suppliers.get(valid_po_id)
                    
                    if supplier_id:
                        form.supplier_id.data = supplier_id
                        current_app.logger.info(f"Set initial supplier_id to {supplier_id} from PO {valid_po_id}")
                except ValueError:
                    current_app.logger.warning(f"Invalid PO ID in URL: {po_id}")

            # If we have a PO ID for pre-population, do it now - but not if we're coming from an edit
            if self.po_id and request.args.get('edited') != '1':
                self.pre_populate_from_po(form, context)
                
        except Exception as e:
            current_app.logger.error(f"Error initializing form: {str(e)}", exc_info=True)
        
        return form
    
    def pre_populate_from_po(self, form, context=None):
        """Pre-populate form data from a purchase order"""
        try:
            from flask_login import current_user
            from app.services.supplier_service import get_purchase_order_by_id
            import uuid
            from datetime import datetime, timedelta
            from app.services.database_service import get_db_session
            from app.models.master import Supplier
            from flask import session, flash
            
            current_app.logger.info(f"Pre-populating form from PO ID: {self.po_id}")
            
            # CRITICAL FIX: Check if we already have edited line items in the session
            # The key check is to not overwrite any existing session data with PO data
            session_key = f'supplier_invoice_line_items_{current_user.user_id}'
            
            # Check if there are already edited items in the session - if so, skip pre-population completely
            if session_key in session and len(session.get(session_key, [])) > 0:
                # Check if any line items have batch numbers other than placeholder
                has_edited_items = False
                for item in session[session_key]:
                    if item.get('batch_number') != '[ENTER BATCH #]' or item.get('expiry_date') != 'YYYY-MM-DD':
                        has_edited_items = True
                        break
                        
                if has_edited_items:
                    current_app.logger.info(f"Preserving existing {len(session[session_key])} edited line items in session")
                    return
                    
            # Check for PO invoices to avoid creating duplicates
            try:
                from app.services.supplier_service import search_supplier_invoices
                
                # Check if this PO already has invoices
                invoices_result = search_supplier_invoices(
                    hospital_id=current_user.hospital_id,
                    po_id=uuid.UUID(self.po_id),
                    page=1,
                    per_page=1
                )
                
                if invoices_result.get('invoices', []):
                    current_app.logger.info(f"PO already has invoices - checking if more items can be invoiced")
                    # We could add logic here to check remaining quantities, but for now just warn
                
            except Exception as e:
                current_app.logger.error(f"Error checking PO invoices: {str(e)}")
        

            # Get PO details
            po = get_purchase_order_by_id(
                po_id=uuid.UUID(self.po_id),
                hospital_id=current_user.hospital_id
            )
            
            if not po:
                current_app.logger.warning(f"PO {self.po_id} not found for pre-population")
                flash("Purchase order not found", "error")
                return
            
            current_app.logger.info(f"Found PO {po.get('po_number')} for pre-population")
            
            # Set supplier and PO reference
            form.po_id.data = self.po_id
            
            supplier_id = str(po.get('supplier_id', ''))
            if supplier_id:
                form.supplier_id.data = supplier_id
                
                # Get supplier details
                try:
                    with get_db_session(read_only=True) as db_session:
                        supplier = db_session.query(Supplier).filter_by(
                            supplier_id=supplier_id,
                            hospital_id=current_user.hospital_id
                        ).first()
                        
                        if supplier:
                            # Set GST information
                            if supplier.gst_registration_number:
                                form.supplier_gstin.data = supplier.gst_registration_number
                                
                            # Set place of supply if available
                            if supplier.state_code:
                                form.place_of_supply.data = supplier.state_code
                                
                            # Set interstate flag
                            if supplier.state_code:
                                if not context:
                                    context = self.get_additional_context()
                                hospital_state_code = context.get('hospital_state_code', '')
                                form.is_interstate.data = supplier.state_code != hospital_state_code
                except Exception as supplier_error:
                    current_app.logger.error(f"Error getting supplier details: {str(supplier_error)}")
            
            # Set currency and exchange rate
            if po.get('currency_code'):
                form.currency_code.data = po.get('currency_code')
                form.exchange_rate.data = po.get('exchange_rate', 1.0)
            
            # Set default invoice date to today
            form.invoice_date.data = datetime.now().date()
            
            # Copy notes
            if po.get('notes'):
                form.notes.data = po.get('notes')
            
            # Get line items from PO
            po_line_items = po.get('line_items', [])
            current_app.logger.info(f"Found {len(po_line_items)} line items in PO")
            
            if not po_line_items:
                current_app.logger.warning("No items found in PO for pre-population")
                return
            
            # ENHANCEMENT: Check if PO has already been fully invoiced
            from app.services.supplier_service import search_supplier_invoices
            try:
                # Get existing invoices for this PO
                invoices_result = search_supplier_invoices(
                    hospital_id=current_user.hospital_id,
                    po_id=uuid.UUID(self.po_id),
                    page=1,
                    per_page=1000  # Get all invoices for this PO
                )
                
                existing_invoices = invoices_result.get('invoices', [])
                if existing_invoices:
                    current_app.logger.info(f"Found {len(existing_invoices)} existing invoices for PO {po.get('po_number')}")
                    
                    # Check if all quantities have been invoiced
                    # For simplicity in this implementation, we'll just show a warning
                    flash(f"Warning: This PO already has {len(existing_invoices)} invoice(s). Please ensure you're not creating duplicate invoices.", "warning")
            except Exception as inv_error:
                current_app.logger.error(f"Error checking existing invoices: {str(inv_error)}")

            # Process line items
            line_items = []
            today = datetime.now()
            # Create clearly marked placeholder values
            batch_placeholder = "[ENTER BATCH #]"  # Clearly indicates action needed
            expiry_placeholder = "YYYY-MM-DD"     # Shows format but clearly not a real date

            # # Generate a default batch number as a placeholder
            # default_batch = f"PO-{po.get('po_number', '').replace('/', '-')}"
            # # Default expiry date one year from now as a placeholder
            # default_expiry = (today + timedelta(days=365)).strftime('%Y-%m-%d')
            
            for po_line in po_line_items:
                try:
                    # Extract data with safe conversions
                    medicine_id = str(po_line.get('medicine_id', ''))
                    medicine_name = po_line.get('medicine_name', 'Unknown Medicine')
                    
                    try:
                        units = float(po_line.get('units', 0))
                    except (ValueError, TypeError):
                        units = 1
                        
                    try:
                        pack_purchase_price = float(po_line.get('pack_purchase_price', 0))
                    except (ValueError, TypeError):
                        pack_purchase_price = 0
                        
                    try:
                        pack_mrp = float(po_line.get('pack_mrp', 0))
                    except (ValueError, TypeError):
                        pack_mrp = 0
                        
                    try:
                        units_per_pack = float(po_line.get('units_per_pack', 1))
                    except (ValueError, TypeError):
                        units_per_pack = 1
                    
                    # Create line item with all needed fields
                    line_item = {
                        'medicine_id': medicine_id,
                        'medicine_name': medicine_name,
                        'units': units,
                        'pack_purchase_price': pack_purchase_price,
                        'pack_mrp': pack_mrp,
                        'units_per_pack': units_per_pack,
                        'hsn_code': po_line.get('hsn_code', ''),
                        'gst_rate': float(po_line.get('gst_rate', 0)),
                        'cgst_rate': float(po_line.get('cgst_rate', 0)),
                        'sgst_rate': float(po_line.get('sgst_rate', 0)),
                        'igst_rate': float(po_line.get('igst_rate', 0)),
                        'batch_number': batch_placeholder,  # Clear placeholder
                        'expiry_date': expiry_placeholder,  # Clear placeholder
                        'is_free_item': False,
                        'discount_percent': 0,
                        # Include calculated values
                        'cgst': float(po_line.get('cgst', 0)),
                        'sgst': float(po_line.get('sgst', 0)),
                        'igst': float(po_line.get('igst', 0)),
                        'total_gst': float(po_line.get('total_gst', 0)),
                        'line_total': float(po_line.get('line_total', 0)),
                        'taxable_amount': float(po_line.get('taxable_amount', 0)),
                        'unit_price': float(po_line.get('unit_price', 0))
                    }
                    
                    line_items.append(line_item)
                    
                except Exception as item_error:
                    current_app.logger.error(f"Error processing PO line item: {str(item_error)}")
                    continue
            
            # Store line items in session
            session_key = f'supplier_invoice_line_items_{current_user.user_id}'
            session[session_key] = line_items
            current_app.logger.info(f"Saved {len(line_items)} items to session for pre-population")
            
            # Create a default invoice number based on PO number
            if not form.supplier_invoice_number.data:
                form.supplier_invoice_number.data = f"INV-{po.get('po_number', '').replace('PO/', '')}"
            
            # Show message
            flash(f"Form pre-populated from Purchase Order with {len(line_items)} items. Please review all fields, especially Batch Numbers and Expiry Dates.", "info")
            
        except Exception as e:
            current_app.logger.error(f"Error pre-populating from PO: {str(e)}", exc_info=True)
            flash(f"Error loading data from purchase order: {str(e)}", "error")
    
    def process_form(self, form, line_items=None, *args, **kwargs):
        """
        Process the invoice form data - ENHANCED with centralized branch validation
        """
        try:
            # NEW: Add permission validation using centralized functions
            from app.services.supplier_service import create_supplier_invoice
            from flask_login import current_user
            from app.services.branch_service import get_user_branch_id, validate_entity_branch_access
            from app.services.permission_service import has_branch_permission
            
            # PRESERVE: Testing bypass
            if current_user.user_id != '7777777777':
                try:
                    # Validate user can create invoices
                    user_obj = {'user_id': current_user.user_id, 'hospital_id': current_user.hospital_id}
                    if not has_branch_permission(user_obj, 'supplier_invoice', 'add'):
                        raise PermissionError("Insufficient permissions to create supplier invoices")
                    
                    # Validate supplier access if supplier is selected
                    if form.supplier_id.data:
                        if not validate_entity_branch_access(
                            current_user.user_id,
                            current_user.hospital_id,
                            form.supplier_id.data,
                            'supplier',
                            'view'
                        ):
                            raise PermissionError("Cannot create invoice for supplier from different branch")
                    
                    # Validate PO access if PO is selected
                    if form.po_id.data and form.po_id.data.strip():
                        if not validate_entity_branch_access(
                            current_user.user_id,
                            current_user.hospital_id,
                            form.po_id.data,
                            'purchase_order',
                            'view'
                        ):
                            raise PermissionError("Cannot create invoice for PO from different branch")
                            
                except PermissionError:
                    raise  # Re-raise permission errors
                except Exception as e:
                    current_app.logger.warning(f"Permission validation failed, proceeding: {str(e)}")
            
            # EXISTING: All the original logic unchanged

          
            # Log what's being processed
            current_app.logger.info(f"Processing form with supplier_id: {form.supplier_id.data}, po_id: {form.po_id.data}")
            
            # Convert UUIDs to strings to avoid type mismatch
            supplier_id = str(form.supplier_id.data) if form.supplier_id.data else None
            # Handle empty PO ID - make it explicitly None
            po_id = None
            if form.po_id.data and form.po_id.data.strip():
                po_id = str(form.po_id.data)
            
            current_app.logger.info(f"Processing form with supplier_id: {supplier_id}, po_id: {po_id}")
            
            # Get branch_id from form or use default
            branch_id = None
            if hasattr(form, 'branch_id') and form.branch_id.data:
                branch_id = uuid.UUID(form.branch_id.data)
            else:
                # Fallback to user's default branch
                from app.services.branch_service import get_user_branch_id
                user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
                if user_branch_id:
                    branch_id = user_branch_id
            
            # Get is_interstate for line item processing
            is_interstate = form.is_interstate.data if hasattr(form, 'is_interstate') else False

            # Prepare invoice data
            invoice_data = {
                'supplier_id': form.supplier_id.data,
                'po_id': po_id,  # Use our preprocessed PO ID
                'supplier_invoice_number': form.supplier_invoice_number.data,
                'invoice_date': form.invoice_date.data,
                'supplier_gstin': form.supplier_gstin.data,
                'place_of_supply': form.place_of_supply.data,
                'reverse_charge': form.reverse_charge.data,
                'currency_code': form.currency_code.data,
                'exchange_rate': form.exchange_rate.data,
                'payment_status': form.payment_status.data,
                'due_date': form.due_date.data,
                'itc_eligible': form.itc_eligible.data,
                'branch_id': branch_id,
                'notes': form.notes.data,
                'is_interstate': form.is_interstate.data,
                'line_items': line_items or []
            }
            
            # Apply interstate flag and validate free items
            if line_items:
                for idx, item in enumerate(line_items):
                    item['is_interstate'] = is_interstate
                    
                    # Validate free item business rules
                    if item.get('is_free_item', False):
                        # Free items: ensure zero rate and positive quantity
                        if float(item.get('pack_purchase_price', 0)) > 0:
                            current_app.logger.warning(f"Line {idx + 1}: Adjusting free item rate to zero")
                            item['pack_purchase_price'] = 0.0
                        if float(item.get('units', 0)) <= 0:
                            raise ValueError(f"Line {idx + 1}: Free items must have positive quantity")
                    else:
                        # Regular items: ensure positive rate and quantity
                        if float(item.get('pack_purchase_price', 0)) <= 0:
                            raise ValueError(f"Line {idx + 1}: Non-free items must have positive price")
                        if float(item.get('units', 0)) <= 0:
                            raise ValueError(f"Line {idx + 1}: Non-free items must have positive quantity")
            
            current_app.logger.info(f"Creating invoice with {len(line_items)} line items. Interstate: {is_interstate}")

            # Process dynamic line items from form hidden fields (backward compatibility)
            if form.medicine_ids.data:
                medicine_ids = form.medicine_ids.data.split(',')
                medicine_names = form.medicine_names.data.split(',')
                quantities = form.quantities.data.split(',')
                pack_purchase_prices = form.pack_purchase_prices.data.split(',')
                pack_mrps = form.pack_mrps.data.split(',')
                units_per_packs = form.units_per_packs.data.split(',')
                hsn_codes = form.hsn_codes.data.split(',')
                gst_rates = form.gst_rates.data.split(',')
                cgst_rates = form.cgst_rates.data.split(',')
                sgst_rates = form.sgst_rates.data.split(',')
                igst_rates = form.igst_rates.data.split(',')
                batch_numbers = form.batch_numbers.data.split(',')
                expiry_dates = form.expiry_dates.data.split(',')
                
                # Optional fields with defaults
                is_free_items = form.is_free_items.data.split(',') if form.is_free_items.data else ['false'] * len(medicine_ids)
                referenced_line_ids = form.referenced_line_ids.data.split(',') if form.referenced_line_ids.data else [''] * len(medicine_ids)
                discount_percents = form.discount_percents.data.split(',') if form.discount_percents.data else ['0'] * len(medicine_ids)
                pre_gst_discounts = form.pre_gst_discounts.data.split(',') if form.pre_gst_discounts.data else ['true'] * len(medicine_ids)
                manufacturing_dates = form.manufacturing_dates.data.split(',') if form.manufacturing_dates.data else [''] * len(medicine_ids)
                item_itc_eligibles = form.item_itc_eligibles.data.split(',') if form.item_itc_eligibles.data else ['true'] * len(medicine_ids)
                
                for i in range(len(medicine_ids)):
                    is_free = is_free_items[i].lower() == 'true'
                    
                    line_item = {
                        'medicine_id': medicine_ids[i],
                        'medicine_name': medicine_names[i],
                        'units': float(quantities[i]),
                        'pack_purchase_price': 0.0 if is_free else float(pack_purchase_prices[i]),  # Force zero for free items
                        'pack_mrp': float(pack_mrps[i]),
                        'units_per_pack': float(units_per_packs[i]),
                        'is_free_item': is_free,
                        'referenced_line_id': referenced_line_ids[i] if referenced_line_ids[i] else None,
                        'discount_percent': 0.0 if is_free else float(discount_percents[i]),  # No discount for free items
                        'pre_gst_discount': pre_gst_discounts[i].lower() == 'true',
                        'hsn_code': hsn_codes[i],
                        'gst_rate': float(gst_rates[i]),
                        'cgst_rate': float(cgst_rates[i]),
                        'sgst_rate': float(sgst_rates[i]),
                        'igst_rate': float(igst_rates[i]),
                        'batch_number': batch_numbers[i],
                        'manufacturing_date': manufacturing_dates[i] if manufacturing_dates[i] else None,
                        'expiry_date': expiry_dates[i],
                        'itc_eligible': item_itc_eligibles[i].lower() == 'true',
                        'is_interstate': is_interstate
                    }
                    
                    # Validate free item rules
                    if is_free and float(quantities[i]) <= 0:
                        raise ValueError(f"Line {i + 1}: Free items must have positive quantity")
                    
                    invoice_data['line_items'].append(line_item)
            
            branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)

            # Create invoice using centralized service with GST calculations
            return create_supplier_invoice(
                hospital_id=current_user.hospital_id,
                branch_id=branch_id,
                invoice_data=invoice_data,
                create_stock_entries=True,
                create_gl_entries=True,
                current_user_id=current_user.user_id
            )
        
        except PermissionError as pe:
            current_app.logger.warning(f"Permission denied: {str(pe)}")
            raise  # Re-raise to be handled by form framework
        except Exception as e:
            current_app.logger.error(f"Error processing invoice form: {str(e)}", exc_info=True)
            raise

    
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
        """Handle GET/POST request with direct line item management"""
        # Import necessary modules
        from flask import request, flash, redirect, url_for, session
        from flask_login import current_user
        from app.forms.supplier_forms import SupplierInvoiceLineForm
        import uuid
        
        # Add logging for request type
        current_app.logger.info(f"==== HANDLE REQUEST: {request.method} ====")
        
        # Add this clear line items functionality
        # Clear line items if requested via URL parameter
        if request.args.get('clear_items') == '1':
            session_key = f'supplier_invoice_line_items_{current_user.user_id}'
            if session_key in session:
                session.pop(session_key)
                flash("Line items cleared successfully", "success")
                # Redirect to remove the query parameter
                return redirect(request.path)

        # Get the main invoice form
        form = self.get_form(*args, **kwargs)
        
        # Create a form for line items
        line_item_form = SupplierInvoiceLineForm()
        
        # Set medicine choices from additional context
        context = self.get_additional_context(*args, **kwargs)
        medicines = context.get('medicines', [])
        medicine_choices = [('', 'Select Medicine')] + [
            (str(med.medicine_id), med.medicine_name) for med in medicines
        ]
        line_item_form.medicine_id.choices = medicine_choices
        
        # Prepare line items list
        session_key = f'supplier_invoice_line_items_{current_user.user_id}'
        if session_key not in session:
            session[session_key] = []
        
        line_items = session.get(session_key, [])
        
        # Add logging for session data
        current_app.logger.info(f"Loaded {len(line_items)} line items from session")
        
        # Handle EDIT LINE ITEM submission - this will override the add line item if edit_line_index is present
        if request.method == 'POST' and 'add_line_item' in request.form:
            # Add debugging for form submission detection
            current_app.logger.info("===== ADD/EDIT LINE ITEM DETECTED =====")
            current_app.logger.info(f"Form data keys: {list(request.form.keys())}")
            current_app.logger.info(f"Medicine ID: {line_item_form.medicine_id.data}")
            current_app.logger.info(f"Quantity: {line_item_form.quantity.data}")
            
            if line_item_form.validate_on_submit():
                # Add logging for form validation success
                current_app.logger.info("Form validation successful")
                
                try:
                    # Check if we're editing an existing item
                    edit_index = request.form.get('edit_line_index', '')
                    current_app.logger.info(f"Edit index from form: '{edit_index}'")
                    
                    if edit_index and edit_index.isdigit():
                        # Process editing existing item
                        edit_index = int(edit_index)
                        current_app.logger.info(f"Editing line item at index {edit_index}")
                        
                        # Make sure index is valid
                        if 0 <= edit_index < len(line_items):
                            # Get hospital state code
                            hospital_state_code = context.get('hospital_state_code', '')
                            
                            # Process the line item form
                            updated_line_item = self.process_line_item_form(
                                line_item_form, 
                                hospital_state_code=hospital_state_code,
                                *args, **kwargs
                            )
                            
                            if updated_line_item:
                                # Update the line item in the session
                                line_items[edit_index] = updated_line_item
                                session[session_key] = line_items
                                flash("Line item updated successfully", "success")
                                current_app.logger.info("Line item updated successfully")
                            else:
                                flash("Failed to update line item", "error")
                                current_app.logger.error("Failed to update line item - process_line_item_form returned None")
                        else:
                            flash("Invalid line item index", "error")
                            current_app.logger.error(f"Invalid edit index: {edit_index}, valid range: 0-{len(line_items)-1}")
                    else:
                        # Process adding new item
                        current_app.logger.info("Adding new line item")
                        
                        # Get hospital state code
                        hospital_state_code = context.get('hospital_state_code', '')
                        current_app.logger.info(f"Hospital state code: {hospital_state_code}")
                        
                        # Process the line item form
                        new_line_item = self.process_line_item_form(
                            line_item_form, 
                            hospital_state_code=hospital_state_code,
                            *args, **kwargs
                        )
                        
                        if new_line_item:
                            # Add the new line item to the session
                            line_items.append(new_line_item)
                            session[session_key] = line_items
                            flash("Line item added successfully", "success")
                            current_app.logger.info("Line item added successfully, new count: " + str(len(line_items)))
                            current_app.logger.info(f"New line item: {new_line_item}")
                        else:
                            flash("Failed to add line item", "error")
                            current_app.logger.error("Failed to add line item - process_line_item_form returned None")
                    
                    # Reset line item form
                    line_item_form = SupplierInvoiceLineForm()
                    line_item_form.medicine_id.choices = medicine_choices
                    
                except Exception as e:
                    current_app.logger.error(f"Error processing line item: {str(e)}", exc_info=True)
                    flash(f"Error processing line item: {str(e)}", "error")
                
                # Add anchor to redirect to line item section
                from flask import url_for
                po_param = f"?po_id={form.po_id.data}" if form.po_id.data else ""
                # return redirect(f"{request.path}{po_param}#line-items-section")
                return self.render_form(form, line_item_form=line_item_form, line_items=line_items, *args, **kwargs)
            else:
                # Log validation errors
                current_app.logger.error(f"Form validation failed: {line_item_form.errors}")
                for field_name, errors in line_item_form.errors.items():
                    current_app.logger.error(f"Field '{field_name}' errors: {errors}")
                    
                flash("Please correct the errors in the form", "error")
        
        # Handle REMOVE LINE ITEM submission
        if request.method == 'POST' and 'remove_line_item' in request.form:
            current_app.logger.info("===== REMOVE LINE ITEM DETECTED =====")
            try:
                index = int(request.form.get('remove_line_item', 0))
                current_app.logger.info(f"Attempting to remove item at index: {index}")
                
                if 0 <= index < len(line_items):
                    removed_item = line_items.pop(index)
                    session[session_key] = line_items
                    flash(f"Removed line item: {removed_item['medicine_name']}", "success")
                    current_app.logger.info(f"Successfully removed line item {removed_item['medicine_name']}")
                else:
                    current_app.logger.error(f"Invalid index: {index}, valid range: 0-{len(line_items)-1}")
                    
                # Return the form with updated line items
                return self.render_form(form, line_item_form=line_item_form, line_items=line_items, *args, **kwargs)
            except Exception as e:
                current_app.logger.error(f"Error removing line item: {str(e)}", exc_info=True)
                flash(f"Error removing line item: {str(e)}", "error")
        
        # Handle MAIN FORM SUBMISSION
        if request.method == 'POST' and 'submit_invoice' in request.form:
            current_app.logger.info(f"===== SUBMIT INVOICE DETECTED =====")
            current_app.logger.info(f"Supplier ID: {form.supplier_id.data}")
            current_app.logger.info(f"PO ID: {form.po_id.data}")
            
            # CRITICAL FIX: Explicitly set a flag to prevent PO pre-population during form submission
            request.skip_po_prepopulation = True
            # Check for missing fields before validation
            missing_fields = []

            # Check if invoice number needs attention
            invoice_number = form.supplier_invoice_number.data
            po_number = None
            
            # If we have a PO ID, get the PO number to check if invoice number is default
            if form.po_id.data:
                try:
                    import uuid
                    from app.services.supplier_service import get_purchase_order_by_id
                    from flask_login import current_user
                    
                    po = get_purchase_order_by_id(
                        po_id=uuid.UUID(form.po_id.data),
                        hospital_id=current_user.hospital_id
                    )
                    
                    if po:
                        po_number = po.get('po_number')
                except Exception as e:
                    current_app.logger.error(f"Error getting PO details: {str(e)}")
            
            # Check if invoice number matches default pattern
            is_default_invoice_number = False
            if po_number and invoice_number:
                default_pattern = f"INV-{po_number.replace('PO/', '')}"
                if invoice_number == default_pattern:
                    is_default_invoice_number = True
                    current_app.logger.warning(f"Invoice number ({invoice_number}) matches default pattern")
            
            # Add warning about default invoice number
            if is_default_invoice_number:
                flash("You are using the default invoice number. Please verify this matches the actual supplier invoice number.", "warning")
                # Don't add to missing_fields to allow submission, just warn

            if not form.supplier_invoice_number.data:
                missing_fields.append("Invoice Number")
            if not form.invoice_date.data:
                missing_fields.append("Invoice Date")
            if not form.place_of_supply.data:
                missing_fields.append("Place of Supply")
            
            # Check line items for missing required fields
            has_missing_batch_expiry = False
            for idx, item in enumerate(line_items):
                medicine_name = item.get('medicine_name', f'Item {idx+1}')
                batch_number = item.get('batch_number', '')
                expiry_date = item.get('expiry_date', '')
                
                # Check if batch number is missing or is a placeholder
                if not batch_number or batch_number == '[ENTER BATCH #]':
                    has_missing_batch_expiry = True
                    missing_fields.append(f"Batch Number for {medicine_name}")
                    
                # Check if expiry date is missing or is a placeholder
                if not expiry_date or expiry_date == 'YYYY-MM-DD':
                    has_missing_batch_expiry = True
                    missing_fields.append(f"Expiry Date for {medicine_name}")
            
            # Show error if mandatory fields are missing
            if missing_fields:
                flash(f"Please fill in the following required fields: {', '.join(missing_fields)}", "error")
                return self.render_form(form, line_item_form=line_item_form, line_items=line_items, *args, **kwargs)
            
            # Log PO supplier mapping for debugging
            po_suppliers = context.get('po_suppliers', {})
            current_app.logger.info(f"PO suppliers mapping: {po_suppliers}")
            
            # Check if PO is in the mapping
            if form.po_id.data in po_suppliers:
                po_supplier_id = po_suppliers[form.po_id.data]
                current_app.logger.info(f"Expected supplier for PO: {po_supplier_id}")

            if form.validate_on_submit():
                try:
                    # Validate line items
                    if not line_items:
                        flash("At least one line item is required", "error")
                        return self.render_form(form, line_item_form=line_item_form, line_items=line_items, *args, **kwargs)
                    
                    # Only check PO-supplier matching if a PO is actually selected
                    po_id = form.po_id.data
                    if po_id and po_id.strip():  # Check if po_id is not empty
                        # Get the PO supplier from context
                        po_suppliers = context.get('po_suppliers', {})
                        po_supplier_id = po_suppliers.get(po_id)
                        
                        # Make sure the supplier in the form matches the PO's supplier
                        if po_supplier_id and form.supplier_id.data != po_supplier_id:
                            current_app.logger.info(f"Setting supplier_id to match PO supplier: {po_supplier_id}")
                            form.supplier_id.data = po_supplier_id
                    
                    # Process main form with line items from session
                    result = self.process_form(form, line_items=line_items, *args, **kwargs)
                    
                    # Clear session line items
                    session.pop(session_key, None)
                    
                    # Success message
                    flash(self.success_message, "success")
                    
                    # Redirect to success URL
                    if callable(self.success_url):
                        return redirect(self.success_url(result))
                    return redirect(self.success_url)
                    
                except Exception as e:
                    current_app.logger.error(f"Error processing form: {str(e)}", exc_info=True)
                    flash(f"Error: {str(e)}", "error")
            else:
                # Log validation errors
                for field, errors in form.errors.items():
                    current_app.logger.warning(f"Validation error in {field}: {errors}")
            
            # CRITICAL FIX: Redirect to the same page with fragment to prevent re-populating from PO
            # We'll add a flag in the URL to indicate we're coming back from an edit
            po_param = f"?po_id={form.po_id.data}&edited=1" if form.po_id.data else ""
            return redirect(f"{request.path}{po_param}#line-items-section")
        
        # GET request
        return self.render_form(form, line_item_form=line_item_form, line_items=line_items, *args, **kwargs)
    
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
        context['menu_items'] = get_menu_items(current_user) if 'menu_items' not in context else context['menu_items']
        
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
        """Generate success URL"""
        from flask import url_for
        return url_for('supplier_views.view_supplier_invoice', invoice_id=self.invoice_id)
    
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
                    hospital_id=current_user.hospital_id
                ).all()
                context['medicines'] = medicines
                
        except Exception as e:
            current_app.logger.error(f"Error getting context: {str(e)}")
            context.update({
                'suppliers': [],
                'medicines': [],
                'branch_context': {'accessible_branches': [], 'can_cross_branch': False}
            })
        
        return context
    
    def get_form(self, *args, **kwargs):
        """Get form with populated data - FIXED choices initialization"""
        form = super().get_form(*args, **kwargs)
        
        # CRITICAL FIX: Always set choices before any other operations
        self._set_form_choices(form)
        
        # Populate with existing invoice data
        self._populate_form_with_invoice_data(form)
        
        return form
    
    def _set_form_choices(self, form):
        """Set form choices - centralized method"""
        try:
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
            
            # Set PO choices (optional field)
            form.po_id.choices = [('', 'Select Purchase Order (Optional)')]
            
            current_app.logger.debug(f"Set {len(suppliers)} supplier choices and currency choices")
            
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
            form.po_id.data = str(invoice.get('po_id')) if invoice.get('po_id') else ''
            form.supplier_gstin.data = invoice.get('supplier_gstin')
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
            
            # Extract line items directly from request (bypass WTForms validation)
            line_items_data = self._extract_line_items_from_request(request.form)
            
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
                        redirect_url = url_for('supplier_views.supplier_invoice_list')
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
                            return redirect(url_for('supplier_views.supplier_invoice_list'))
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
                return redirect(url_for('supplier_views.supplier_invoice_list'))
            except Exception:
                return redirect('/')
        except Exception as e:
            # EXISTING: Handle errors in form setup
            current_app.logger.error(f"Error in handle_request: {str(e)}")
            flash(f"Error: {str(e)}", "error")
            try:
                from flask import url_for
                return redirect(url_for('supplier_views.supplier_invoice_list'))
            except Exception:
                return redirect('/')
    
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
        from flask import url_for
        return url_for('supplier_views.view_purchase_order', po_id=result['po_id'])
    
    def get_additional_context(self, *args, **kwargs):
        """Get suppliers, medicines, and purchase orders for dropdowns - ENHANCED with branch filtering"""
        context = {}
        try:
            from app.services.database_service import get_db_session
            from app.models.master import Supplier, Medicine, Branch
            from flask_login import current_user
            
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
                # ENHANCED: Get suppliers with branch filtering
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
                
                # EXISTING: Get medicines (unchanged)
                medicines = session.query(Medicine).filter_by(
                    hospital_id=current_user.hospital_id
                ).all()
                context['medicines'] = medicines
                
                # ENHANCED: Get branches with filtering
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
                'medicines': [],
                'branches': [],
                'branch_context': {'accessible_branches': [], 'can_cross_branch': False}
            })
        
        return context
    
    def get_form(self, *args, **kwargs):
        """Get form instance for creation only"""
        form = super().get_form(*args, **kwargs)
        
        # Set supplier choices
        context = self.get_additional_context()
        if 'suppliers' in context:
            form.supplier_id.choices = [('', 'Select Supplier')] + [(str(s.supplier_id), s.supplier_name) 
                                    for s in context['suppliers']]
        else:
            form.supplier_id.choices = [('', 'Select Supplier')]
        
        # Set PO number for new POs
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
        """Process the form data for creation - ENHANCED with centralized branch validation"""
        try:
            # NEW: Add permission validation using centralized functions
            from flask_login import current_user  # [OK] Import first
            from app.services.supplier_service import create_purchase_order_with_validation
            from app.services.branch_service import validate_entity_branch_access
            from app.services.permission_service import has_branch_permission

            # PRESERVE: Testing bypass
            if current_user.user_id != '7777777777':
                try:
                    # Validate user can create POs
                    user_obj = {'user_id': current_user.user_id, 'hospital_id': current_user.hospital_id}
                    if not has_branch_permission(user_obj, 'purchase_order', 'add'):
                        raise PermissionError("Insufficient permissions to create purchase orders")
                    
                    # Validate supplier access if supplier is selected
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
                    raise  # Re-raise permission errors
                except Exception as e:
                    current_app.logger.warning(f"Permission validation failed, proceeding: {str(e)}")
            
           
            # Determine if it's save as draft or save and submit
            is_draft = 'save_draft' in request.form
            is_approved = 'save_approved' in request.form
            
            # SAFETY CHECK: Validate hidden fields before processing
            if not form.medicine_ids.data or not form.medicine_ids.data.strip():
                current_app.logger.error("No medicine IDs found in form data")
                raise ValueError("No line items found. Please add at least one item to the purchase order.")

            # Extract line items from hidden fields
            line_items = []
            if form.medicine_ids.data:
                medicine_ids = form.medicine_ids.data.split(',')
                medicine_ids = [mid.strip() for mid in medicine_ids if mid.strip()]  # Remove empty values

                if not medicine_ids:
                    current_app.logger.error("Medicine IDs list is empty after cleaning")
                    raise ValueError("No valid line items found. Please add at least one item to the purchase order.")
                
                quantities = form.quantities.data.split(',')
                pack_prices = form.pack_purchase_prices.data.split(',')
                pack_mrps = form.pack_mrps.data.split(',')
                units_per_packs = form.units_per_packs.data.split(',')
                hsn_codes = form.hsn_codes.data.split(',')
                gst_rates = form.gst_rates.data.split(',')
                
                # Handle NEW fields with validation
                discount_percents = []
                is_free_items = []
                
                if hasattr(form, 'discount_percents') and form.discount_percents.data:
                    discount_percents = form.discount_percents.data.split(',')
                else:
                    discount_percents = ['0'] * len(medicine_ids)
                    
                if hasattr(form, 'is_free_items') and form.is_free_items.data:
                    is_free_items = form.is_free_items.data.split(',')
                else:
                    is_free_items = ['false'] * len(medicine_ids)

                for i in range(len(medicine_ids)):
                    if medicine_ids[i]:  # Skip empty entries
                        try:
                            # Fix boolean conversion
                            is_free = False
                            if i < len(is_free_items):
                                is_free = is_free_items[i].lower() == 'true'
                            
                            line_item = {
                                'medicine_id': uuid.UUID(medicine_ids[i]),
                                'units': float(quantities[i]),
                                'pack_purchase_price': float(pack_prices[i]),
                                'pack_mrp': float(pack_mrps[i]),
                                'units_per_pack': float(units_per_packs[i]),
                                'hsn_code': hsn_codes[i],
                                'gst_rate': float(gst_rates[i]),
                                'discount_percent': float(discount_percents[i]) if i < len(discount_percents) else 0.0,
                                'is_free_item': is_free
                            }
                            line_items.append(line_item)
                        except (ValueError, IndexError) as e:
                            current_app.logger.error(f"Error processing line item {i + 1}: {str(e)}")
                            raise ValueError(f"Invalid data in line item {i + 1}")
            
            # Get branch_id from form or use default
            branch_id = None
            if hasattr(form, 'branch_id') and form.branch_id.data:
                branch_id = uuid.UUID(form.branch_id.data)
            else:
                # Fallback to user's default branch
                from app.services.branch_service import get_user_branch_id
                user_branch_id = get_user_branch_id(current_user.user_id, current_user.hospital_id)
                if user_branch_id:
                    branch_id = user_branch_id

            # Create PO data with validation fields
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
                'line_items': line_items
            }
            
            current_app.logger.info(f"Creating PO with {len(line_items)} line items using validation")
            
            # Use validation-enabled service function
            result = create_purchase_order_with_validation(
                hospital_id=current_user.hospital_id,
                po_data=po_data,
                current_user_id=current_user.user_id
            )
            
            current_app.logger.info(f"Successfully created validated PO: {result.get('po_number')}")
            
            return result
        
        except PermissionError as pe:
            current_app.logger.warning(f"Permission denied: {str(pe)}")
            raise  # Re-raise to be handled by form framework
        except ValueError as ve:
            # Handle validation errors specifically
            current_app.logger.error(f"Validation error in PO creation: {str(ve)}")
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
            from app.services.database_service import get_db_session
            from app.models.master import Supplier, Medicine, Branch
            from flask_login import current_user
            
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
                
        except Exception as e:
            current_app.logger.error(f"Error getting context: {str(e)}")
            context['suppliers'] = []
        
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
