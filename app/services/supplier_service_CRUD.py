# Example: How to structure entity-specific services
# app/services/supplier_service.py

"""
Entity-specific service following Universal CRUD conventions
Functions MUST follow naming pattern: {operation}_{entity_singular}
"""

from typing import Dict, Optional
import uuid
from app.services.branch_service import get_branch_for_supplier_operation

def create_supplier(
    hospital_id: uuid.UUID,
    supplier_data: Dict,
    current_user_id: Optional[str] = None,
    **kwargs  # Accept extra kwargs for flexibility
) -> Dict:
    """
    Create supplier with business logic
    MUST accept these standard parameters
    """
    # Get branch using your existing logic
    branch_id = get_branch_for_supplier_operation(
        current_user_id=current_user_id,
        hospital_id=hospital_id,
        specified_branch_id=supplier_data.get('branch_id')
    )
    
    if not branch_id:
        raise ValueError("Could not determine branch for supplier")
    
    supplier_data['branch_id'] = branch_id
    
    # Add business logic
    if not supplier_data.get('status'):
        supplier_data['status'] = 'pending_approval'  # Different from generic default
    
    # Validate GST if provided
    if supplier_data.get('gst_number'):
        if not validate_gst_number(supplier_data['gst_number']):
            raise ValueError("Invalid GST number format")
    
    # Your existing create logic...
    with get_db_session() as session:
        # ... create supplier ...
        return created_supplier

def update_supplier(
    supplier_id: str,
    supplier_data: Dict,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    **kwargs
) -> Dict:
    """
    Update supplier with business logic
    MUST accept these standard parameters
    """
    # Business logic for updates
    # Don't allow status changes without approval
    if 'status' in supplier_data:
        del supplier_data['status']  # Remove, handle via approval workflow
    
    # Your existing update logic...
    with get_db_session() as session:
        # ... update supplier ...
        return updated_supplier

def delete_supplier(
    supplier_id: str,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    **kwargs
) -> Dict:
    """
    Delete supplier (soft delete with validations)
    MUST accept these standard parameters
    """
    # Check for active invoices
    with get_db_session() as session:
        active_invoices = session.query(SupplierInvoice).filter_by(
            supplier_id=supplier_id,
            status='pending'
        ).count()
        
        if active_invoices > 0:
            raise ValueError(f"Cannot delete supplier with {active_invoices} pending invoices")
        
        # Soft delete
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError("Supplier not found")
        
        supplier.is_deleted = True
        supplier.status = 'inactive'
        supplier.updated_by = current_user_id
        session.commit()
        
        return {'success': True, 'message': 'Supplier deactivated successfully'}

# Additional functions that aren't part of CRUD convention
def approve_supplier(supplier_id: str, approver_id: str):
    """Not called by Universal CRUD - separate business function"""
    pass

def get_supplier_balance(supplier_id: str):
    """Not called by Universal CRUD - separate business function"""
    pass