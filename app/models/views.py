# File: app/models/views.py
"""
Database View Models for Transaction Entities
These are read-only models that map to database views, not tables
Used for search, filtering, reporting, and analysis
"""

from sqlalchemy import Column, String, UUID, DateTime, Date, Numeric, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from app.models.base import Base

class PurchaseOrderView(Base):
    """
    Comprehensive view of purchase orders with denormalized supplier and branch data
    Used for: List views, search, filtering, reporting, analysis
    """
    __tablename__ = 'purchase_orders_view'
    __table_args__ = {'info': {'is_view': True}}  # Mark as view
    
    # Primary identifiers
    po_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))
    po_number = Column(String(20), nullable=False)
    
    # Dates
    po_date = Column(DateTime(timezone=True))
    quotation_date = Column(Date)
    expected_delivery_date = Column(Date)
    po_year = Column(Numeric)  # Actually returns decimal from EXTRACT
    po_month = Column(Numeric)
    po_month_year = Column(String(7))
    po_quarter = Column(String(1))
    
    # Supplier information (denormalized)
    supplier_id = Column(PostgresUUID(as_uuid=True))
    supplier_name = Column(String(200))
    supplier_category = Column(String(50))
    supplier_contact_person = Column(String(100))
    supplier_mobile = Column(String(15))
    supplier_phone = Column(String(20))
    supplier_email = Column(String(100))
    supplier_gst = Column(String(15))
    supplier_pan = Column(String(10))
    supplier_payment_terms = Column(String(100))
    supplier_black_listed = Column(Boolean)
    supplier_status = Column(String(20))
    
    # Branch information
    branch_name = Column(String(100))
    branch_state_code = Column(String(2))
    branch_is_active = Column(Boolean)
    
    # Hospital information
    hospital_name = Column(String(100))
    hospital_license_no = Column(String(50))
    
    # Financial information
    currency_code = Column(String(3))
    exchange_rate = Column(Numeric(10, 6))
    total_amount = Column(Numeric(12, 2))
    total_amount_base_currency = Column(Numeric(12, 2))
    
    # Status and workflow
    po_status = Column(String(20))
    status_order = Column(Integer)
    approved_by = Column(String(50))
    
    # Reference information
    quotation_id = Column(String(50))
    
    # Calculated fields
    days_since_po = Column(Integer)
    days_until_delivery = Column(Integer)
    delivery_status = Column(String(20))
    
    # Audit fields
    created_at = Column(DateTime(timezone=True))
    created_by = Column(String(50))
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(50))
    deleted_flag = Column(Boolean)
    
    # Search helper
    search_text = Column(Text)


class SupplierInvoiceView(Base):
    """
    Comprehensive view of supplier invoices with related data
    Used for: List views, search, filtering, aging reports, payment tracking
    """
    __tablename__ = 'supplier_invoices_view'
    __table_args__ = {'info': {'is_view': True}}
    
    # Primary identifiers
    invoice_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))
    supplier_invoice_number = Column(String(50))
    
    # Dates
    invoice_date = Column(DateTime(timezone=True))
    due_date = Column(Date)
    invoice_year = Column(Numeric)
    invoice_month = Column(Numeric)
    invoice_month_year = Column(String(7))
    invoice_quarter = Column(String(1))
    
    # Purchase Order relationship
    po_id = Column(PostgresUUID(as_uuid=True))
    po_number = Column(String(20))
    po_date = Column(DateTime(timezone=True))
    quotation_id = Column(String(50))
    
    # Supplier information (denormalized)
    supplier_id = Column(PostgresUUID(as_uuid=True))
    supplier_name = Column(String(200))
    supplier_category = Column(String(50))
    supplier_contact_person = Column(String(100))
    supplier_mobile = Column(String(15))
    supplier_phone = Column(String(20))
    supplier_email = Column(String(100))
    supplier_gst = Column(String(15))
    supplier_payment_terms = Column(String(100))
    supplier_status = Column(String(20))
    
    # Branch and Hospital
    branch_name = Column(String(100))
    branch_state_code = Column(String(2))
    branch_is_active = Column(Boolean)
    hospital_name = Column(String(100))
    hospital_license_no = Column(String(50))
    
    # Financial information
    invoice_total_amount = Column(Numeric(12, 2))
    paid_amount = Column(Numeric(12, 2))
    balance_amount = Column(Numeric(12, 2))
    cgst_amount = Column(Numeric(12, 2))
    sgst_amount = Column(Numeric(12, 2))
    igst_amount = Column(Numeric(12, 2))
    total_gst_amount = Column(Numeric(12, 2))
    
    # GST Information
    supplier_gstin = Column(String(15))
    place_of_supply = Column(String(2))
    reverse_charge = Column(Boolean)
    itc_eligible = Column(Boolean)
    
    # Currency
    currency_code = Column(String(3))
    exchange_rate = Column(Numeric(10, 6))
    
    # Payment and posting status
    payment_status = Column(String(20))
    gl_posted = Column(Boolean)
    inventory_posted = Column(Boolean)
    posting_date = Column(DateTime(timezone=True))
    posting_reference = Column(String(50))
    
    # Reversal information
    is_reversed = Column(Boolean)
    is_credit_note = Column(Boolean)
    original_invoice_id = Column(PostgresUUID(as_uuid=True))
    reversed_by_invoice_id = Column(PostgresUUID(as_uuid=True))
    reversal_reason = Column(String(200))
    
    # Notes
    notes = Column(String(500))
    
    # Aging analysis
    invoice_age_days = Column(Integer)
    days_overdue = Column(Integer)
    aging_status = Column(String(20))
    aging_bucket = Column(String(20))
    
    # Audit fields
    created_at = Column(DateTime(timezone=True))
    created_by = Column(String(50))
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(50))
    
    # Search helper
    search_text = Column(Text)


class SupplierPaymentView(Base):
    """
    Comprehensive view of supplier payments with related invoice and supplier data
    Used for: Payment tracking, reconciliation, cash flow analysis
    """
    __tablename__ = 'supplier_payments_view'
    __table_args__ = {'info': {'is_view': True}}
    
    # Primary identifiers
    payment_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))
    reference_no = Column(String(50))
    
    # Dates
    payment_date = Column(DateTime(timezone=True))
    payment_year = Column(Numeric)
    payment_month = Column(Numeric)
    payment_month_year = Column(String(7))
    payment_quarter = Column(String(1))
    payment_day_name = Column(String(10))
    
    # Invoice relationship
    invoice_id = Column(PostgresUUID(as_uuid=True))
    supplier_invoice_number = Column(String(50))
    invoice_date = Column(DateTime(timezone=True))
    invoice_amount = Column(Numeric(12, 2))
    po_id = Column(PostgresUUID(as_uuid=True))
    po_number = Column(String(20))
    
    # Supplier information (denormalized)
    supplier_id = Column(PostgresUUID(as_uuid=True))
    supplier_name = Column(String(200))
    supplier_category = Column(String(50))
    supplier_contact_person = Column(String(100))
    supplier_mobile = Column(String(15))
    supplier_phone = Column(String(20))
    supplier_email = Column(String(100))
    supplier_gst = Column(String(15))
    supplier_payment_terms = Column(String(100))
    supplier_bank_name = Column(String(100))
    supplier_account_number = Column(String(50))
    supplier_ifsc_code = Column(String(11))
    supplier_status = Column(String(20))
    
    # Branch and Hospital
    branch_name = Column(String(100))
    branch_state_code = Column(String(2))
    branch_is_active = Column(Boolean)
    hospital_name = Column(String(100))
    hospital_license_no = Column(String(50))
    
    # Payment details
    payment_amount = Column(Numeric(12, 2))
    payment_method = Column(String(50))
    payment_category = Column(String(20))
    payment_source = Column(String(30))
    payment_status_old = Column(String(20))  # Original status field
    
    # Amounts breakdown
    cash_amount = Column(Numeric(12, 2))
    cheque_amount = Column(Numeric(12, 2))
    bank_transfer_amount = Column(Numeric(12, 2))
    upi_amount = Column(Numeric(12, 2))
    
    # Cheque details
    cheque_number = Column(String(20))
    cheque_date = Column(Date)
    cheque_bank = Column(String(100))
    cheque_status = Column(String(20))
    cheque_clearance_date = Column(Date)
    
    # Bank transfer details
    payment_bank_name = Column(String(100))
    bank_reference_number = Column(String(50))
    payment_ifsc_code = Column(String(11))
    transfer_mode = Column(String(20))
    
    # UPI details
    upi_transaction_id = Column(String(50))
    upi_reference_id = Column(String(50))
    upi_id = Column(String(100))
    upi_app_name = Column(String(50))
    
    # Notes
    notes = Column(String(255))
    
    # Currency
    currency_code = Column(String(3))
    exchange_rate = Column(Numeric(10, 6))
    
    # Status and workflow
    workflow_status = Column(String(20))  # Standardized field name
    payment_status = Column(String(20))  # workflow_status renamed
    approved_by = Column(String(15))
    approval_date = Column(DateTime(timezone=True))
    rejected_by = Column(String(15))
    rejected_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    requires_approval = Column(Boolean)
    approval_level = Column(String(20))
    
    # Payment method grouping
    payment_method_group = Column(String(20))
    
    # Reconciliation
    reconciliation_status = Column(String(20))
    reconciliation_date = Column(DateTime(timezone=True))
    
    # GL Posting
    gl_posted = Column(Boolean)
    posting_date = Column(DateTime(timezone=True))
    posting_reference = Column(String(50))
    
    # Time-based analysis
    days_to_payment = Column(Integer)
    days_from_due_date = Column(Integer)
    payment_timeliness = Column(String(20))
    
    # Audit fields
    created_at = Column(DateTime(timezone=True))
    created_by = Column(String(50))
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(50))
    
    # Search helper
    search_text = Column(Text)


# Helper functions for working with views
def get_view_model(entity_type: str):
    """
    Get the appropriate view model for an entity type
    
    Args:
        entity_type: The entity type (e.g., 'purchase_orders', 'supplier_invoices', 'supplier_payments')
    
    Returns:
        The corresponding view model class
    """
    view_models = {
        'purchase_orders': PurchaseOrderView,
        'supplier_invoices': SupplierInvoiceView,
        'supplier_payments': SupplierPaymentView
    }
    return view_models.get(entity_type)


def is_view_model(model_class):
    """
    Check if a model class is a view (not a table)
    
    Args:
        model_class: The SQLAlchemy model class
    
    Returns:
        Boolean indicating if it's a view
    """
    return hasattr(model_class, '__table_args__') and \
           isinstance(model_class.__table_args__, dict) and \
           model_class.__table_args__.get('info', {}).get('is_view', False)