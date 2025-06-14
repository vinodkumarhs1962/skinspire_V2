# app/utils/form_helpers.py - FINAL MINIMAL VERSION

"""
Minimal form helpers - only what's not available in existing services
Uses existing branch_service.py for branch functionality
"""

from flask import current_app


def populate_supplier_choices(form, current_user, branch_id=None, active_only=True):
    """
    Populate supplier choices - only function we actually need
    """
    try:
        from app.services.supplier_service import search_suppliers
        
        result = search_suppliers(
            hospital_id=current_user.hospital_id,
            branch_id=branch_id,
            status='active' if active_only else None,
            current_user_id=current_user.user_id,
            page=1,
            per_page=1000
        )
        
        suppliers = result.get('suppliers', [])
        choices = [('', 'Select Supplier')]
        
        for supplier in suppliers:
            display_name = supplier['supplier_name']
            if supplier.get('supplier_code'):
                display_name = f"{supplier['supplier_name']} ({supplier['supplier_code']})"
            
            choices.append((str(supplier['supplier_id']), display_name))
        
        form.supplier_id.choices = choices
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error populating supplier choices: {str(e)}")
        form.supplier_id.choices = [('', 'Error loading suppliers')]
        return False


def populate_invoice_choices_for_supplier(form, current_user, supplier_id):
    """
    Populate invoice choices for payment forms - specific business need
    """
    try:
        if not supplier_id:
            form.invoice_id.choices = [('', 'Select Supplier First')]
            return True
            
        from app.services.supplier_service import search_supplier_invoices
        
        result = search_supplier_invoices(
            hospital_id=current_user.hospital_id,
            supplier_id=supplier_id,
            payment_status=['unpaid', 'partial'],
            current_user_id=current_user.user_id,
            page=1,
            per_page=100
        )
        
        invoices = result.get('invoices', [])
        choices = [('', 'Select Invoice (Optional)')]
        
        for invoice in invoices:
            balance_due = invoice.get('balance_due', 0)
            display_name = f"{invoice['supplier_invoice_number']} -  Rs.{balance_due}"
            choices.append((str(invoice['invoice_id']), display_name))
        
        form.invoice_id.choices = choices
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error populating invoice choices: {str(e)}")
        form.invoice_id.choices = [('', 'Error loading invoices')]
        return False


# =====================================================================
# RECOMMENDED USAGE IN CONTROLLERS
# =====================================================================

"""
USAGE EXAMPLE in app/controllers/supplier_controller.py:

# Import existing branch service + minimal helpers
from app.services.branch_service import populate_branch_choices_for_user
from app.utils.form_helpers import populate_supplier_choices, populate_invoice_choices_for_supplier

class SupplierPaymentController(FormController):
    
    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        
        try:
            from flask_login import current_user
            
            # Use existing branch service (no custom code needed)
            populate_branch_choices_for_user(
                form.branch_id, 
                current_user, 
                required=True,
                module_name='payment'
            )
            
            # Use minimal supplier helper
            populate_supplier_choices(form, current_user)
            
            # Optional: populate invoices if supplier already selected
            if self.is_edit and hasattr(form, 'supplier_id') and form.supplier_id.data:
                populate_invoice_choices_for_supplier(form, current_user, form.supplier_id.data)
                
        except Exception as e:
            current_app.logger.error(f"Error setting up form: {str(e)}")
        
        return form

class SupplierFormController(FormController):
    
    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        
        # Just use existing branch service - that's it!
        from app.services.branch_service import populate_branch_choices_for_user
        populate_branch_choices_for_user(
            form.branch_id, 
            current_user, 
            required=True,
            module_name='supplier'
        )
        
        return form
"""