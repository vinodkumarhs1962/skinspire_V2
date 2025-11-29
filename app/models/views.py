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

    # Approval tracking fields (from ApprovalMixin in PurchaseOrderHeader)
    approved_by = Column(String(50))
    approved_at = Column(DateTime(timezone=True))
    
    # Soft delete fields (from SoftDeleteMixin in PurchaseOrderHeader)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(50))

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

    # Soft delete fields (from SoftDeleteMixin in SupplierInvoice)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(50))

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
    advance_amount = Column(Numeric(12, 2))

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

    # Soft delete fields - CRITICAL for delete functionality
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(50))

    # Search helper
    search_text = Column(Text)


class SupplierAdvanceBalanceView(Base):
    """
    View showing available advance balance for each supplier advance payment
    Calculated using double-entry subledger (Debits - Credits)
    Used for: FIFO advance allocation, balance tracking
    """
    __tablename__ = 'v_supplier_advance_balance'
    __table_args__ = {'info': {'is_view': True}}

    # Primary identifiers
    supplier_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))
    advance_payment_id = Column(PostgresUUID(as_uuid=True), primary_key=True)

    # Payment details
    advance_date = Column(DateTime(timezone=True))
    original_advance_amount = Column(Numeric(12, 2))
    reference_no = Column(String(50))

    # Balance information (from double-entry subledger)
    allocated_amount = Column(Numeric(12, 2))  # Total credits (allocations)
    remaining_balance = Column(Numeric(12, 2))  # Debits - Credits
    allocation_count = Column(Integer)  # Number of allocations


class SupplierAdvanceTransactionView(Base):
    """
    Audit trail view of all supplier advance transactions
    Shows both debit (receipt) and credit (allocation) entries
    Used for: Transaction history, reconciliation, audit
    """
    __tablename__ = 'v_supplier_advance_transactions'
    __table_args__ = {'info': {'is_view': True}}

    # Primary identifier
    adjustment_id = Column(PostgresUUID(as_uuid=True), primary_key=True)

    # Entity identifiers
    supplier_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    supplier_name = Column(String(200))
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))

    # Transaction details
    adjustment_date = Column(DateTime(timezone=True))
    adjustment_type = Column(String(20))  # advance_receipt, allocation, reversal, refund

    # Source payment (the advance)
    source_payment_id = Column(PostgresUUID(as_uuid=True))
    source_reference = Column(String(50))
    source_payment_date = Column(DateTime(timezone=True))

    # Target payment (invoice payment using advance)
    target_payment_id = Column(PostgresUUID(as_uuid=True))
    target_reference = Column(String(50))
    target_payment_date = Column(DateTime(timezone=True))

    # Invoice (if applicable)
    invoice_id = Column(PostgresUUID(as_uuid=True))
    supplier_invoice_number = Column(String(50))

    # Amounts (double-entry)
    debit_amount = Column(Numeric(12, 2))  # When type = 'advance_receipt'
    credit_amount = Column(Numeric(12, 2))  # When type = 'allocation'
    amount = Column(Numeric(12, 2))  # Total amount

    # Notes and audit
    notes = Column(Text)
    created_by = Column(String(50))
    created_at = Column(DateTime(timezone=True))


class PatientInvoiceView(Base):
    """
    Comprehensive view of patient billing invoices with denormalized data
    Used for: List views, search, filtering, aging reports, payment tracking
    """
    __tablename__ = 'patient_invoices_view'
    __table_args__ = {'info': {'is_view': True}}

    # Primary identifiers
    invoice_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))
    invoice_number = Column(String(50), nullable=False)

    # Dates
    invoice_date = Column(DateTime(timezone=True))
    invoice_year = Column(Numeric)
    invoice_month = Column(Numeric)
    invoice_month_year = Column(String(7))
    invoice_quarter = Column(String(1))
    invoice_day_name = Column(String(10))

    # Invoice classification
    invoice_type = Column(String(50))  # Service, Product, Prescription, Misc
    is_gst_invoice = Column(Boolean)

    # Patient information (denormalized)
    patient_id = Column(PostgresUUID(as_uuid=True))
    patient_mrn = Column(String(20))
    patient_name = Column(Text)  # TEXT type to match view (COALESCE with JSONB extraction)
    patient_title = Column(String(10))
    patient_first_name = Column(String(100))
    patient_last_name = Column(String(100))
    patient_blood_group = Column(String(5))
    patient_gender = Column(Text)  # TEXT type from JSONB extraction
    patient_dob = Column(Text)  # TEXT type from JSONB extraction
    patient_phone = Column(Text)  # TEXT type from JSONB extraction
    patient_mobile = Column(Text)  # TEXT type from JSONB extraction
    patient_email = Column(Text)  # TEXT type from JSONB extraction
    patient_is_active = Column(Boolean)

    # Branch information
    branch_name = Column(String(100))
    branch_state_code = Column(String(2))
    branch_is_active = Column(Boolean)

    # Hospital information
    hospital_name = Column(String(100))
    hospital_license_no = Column(String(50))
    hospital_gst = Column(String(15))

    # Financial information
    total_amount = Column(Numeric(12, 2))
    total_discount = Column(Numeric(12, 2))
    total_taxable_value = Column(Numeric(12, 2))
    grand_total = Column(Numeric(12, 2))
    paid_amount = Column(Numeric(12, 2))
    balance_due = Column(Numeric(12, 2))

    # GST breakdown
    total_cgst_amount = Column(Numeric(12, 2))
    total_sgst_amount = Column(Numeric(12, 2))
    total_igst_amount = Column(Numeric(12, 2))
    total_gst_amount = Column(Numeric(12, 2))

    # GST Information
    place_of_supply = Column(String(2))
    reverse_charge = Column(Boolean)
    e_invoice_irn = Column(String(100))
    is_interstate = Column(Boolean)

    # Currency
    currency_code = Column(String(3))
    exchange_rate = Column(Numeric(10, 6))

    # Status fields
    payment_status = Column(String(20))  # paid, partial, unpaid, cancelled
    status_order = Column(Integer)

    # Cancellation information
    is_cancelled = Column(Boolean)
    cancellation_reason = Column(String(255))
    cancelled_at = Column(DateTime(timezone=True))

    # Age and aging analysis
    invoice_age_days = Column(Integer)
    aging_bucket = Column(String(20))
    aging_status = Column(String(20))

    # GL Account
    gl_account_id = Column(PostgresUUID(as_uuid=True))

    # Notes
    notes = Column(Text)

    # Split Invoice Tracking (NEW in v2.0)
    parent_transaction_id = Column(PostgresUUID(as_uuid=True))
    split_sequence = Column(Integer)
    is_split_invoice = Column(Boolean)
    split_reason = Column(String(100))

    # Parent invoice information (for context when viewing split invoices)
    parent_invoice_number = Column(String(50))
    parent_invoice_date = Column(DateTime(timezone=True))
    parent_grand_total = Column(Numeric(12, 2))

    # Child invoice aggregation (for parent invoices)
    split_invoice_count = Column(Integer)
    split_invoices_total = Column(Numeric(12, 2))

    # Audit fields
    created_at = Column(DateTime(timezone=True))
    created_by = Column(String(50))
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(50))

    # Soft delete fields (will be NULL until SoftDeleteMixin added to InvoiceHeader)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(50))

    # Search helper
    search_text = Column(Text)


class ConsolidatedPatientInvoiceView(Base):
    """
    Optimized view for Phase 3 consolidated invoices (parent invoices with children)
    Shows only parent invoices that have split children with aggregated totals
    Used for: Consolidated invoice list, reporting, analysis
    """
    __tablename__ = 'v_consolidated_patient_invoices'
    __table_args__ = {'info': {'is_view': True}}  # Mark as view

    # === PRIMARY IDENTIFICATION ===
    invoice_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(DateTime(timezone=True))
    invoice_type = Column(String(50))

    # === TENANT & BRANCH ===
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))
    hospital_name = Column(String(200))
    branch_name = Column(String(100))

    # === PATIENT INFORMATION ===
    patient_id = Column(PostgresUUID(as_uuid=True))
    patient_name = Column(Text)  # TEXT type to match database view (contains COALESCE expression)
    patient_mrn = Column(String(50))
    patient_phone = Column(Text)  # TEXT type from JSONB extraction
    patient_email = Column(Text)  # TEXT type from JSONB extraction
    patient_address = Column(Text)  # TEXT type from JSONB extraction (contact_info->>'address')
    patient_blood_group = Column(String(5))  # Blood group from patient_master_view

    # === SPLIT INVOICE TRACKING ===
    child_invoice_count = Column(Integer)  # Number of child invoices
    total_invoice_count = Column(Integer)  # Parent + children
    service_invoice_count = Column(Integer)  # Count of SVC/ invoices
    medicine_invoice_count = Column(Integer)  # Count of MED/ invoices
    exempt_invoice_count = Column(Integer)  # Count of EXM/ invoices
    prescription_invoice_count = Column(Integer)  # Count of RX/ invoices

    # === CONSOLIDATED AMOUNTS (parent + all children) ===
    consolidated_grand_total = Column(Numeric(15, 2))
    consolidated_paid_amount = Column(Numeric(15, 2))
    consolidated_balance_due = Column(Numeric(15, 2))

    # === PARENT INVOICE AMOUNTS (for reference) ===
    parent_total_amount = Column(Numeric(15, 2))
    parent_discount = Column(Numeric(15, 2))
    parent_taxable = Column(Numeric(15, 2))
    parent_cgst = Column(Numeric(15, 2))
    parent_sgst = Column(Numeric(15, 2))
    parent_igst = Column(Numeric(15, 2))
    parent_grand_total = Column(Numeric(15, 2))
    parent_paid_amount = Column(Numeric(15, 2))
    parent_balance_due = Column(Numeric(15, 2))

    # === PAYMENT STATUS ===
    payment_status = Column(String(20))  # paid, partial, unpaid

    # === AGING ===
    invoice_age_days = Column(Integer)
    aging_bucket = Column(String(20))  # 0-30 days, 31-60 days, etc.

    # === GST INFORMATION ===
    is_gst_invoice = Column(Boolean)

    # === AUDIT TRAIL ===
    created_at = Column(DateTime(timezone=True))
    created_by = Column(String(50))
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(50))


class PatientPaymentReceiptView(Base):
    """
    Comprehensive view of patient payment receipts with workflow status and approval tracking
    Joins payment_details, invoice_header, patients, hospitals, and branches
    Used for: Payment receipt list, search, filtering, reporting, workflow management
    """
    __tablename__ = 'v_patient_payment_receipts'
    __table_args__ = {'info': {'is_view': True}}  # Mark as view

    # === PRIMARY IDENTIFICATION ===
    payment_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    hospital_name = Column(String(200))

    # === INVOICE REFERENCE ===
    invoice_id = Column(PostgresUUID(as_uuid=True))
    invoice_number = Column(String(50))
    invoice_date = Column(DateTime(timezone=True))
    invoice_type = Column(String(50))

    # NOTE: Removed invoice_count and is_multi_invoice_payment - these columns don't exist in v_patient_payment_receipts view
    # Multi-invoice payments are identified by invoice_id = NULL
    # To get invoice count, query ar_subledger where reference_id = payment_id

    # === PATIENT INFORMATION ===
    patient_id = Column(PostgresUUID(as_uuid=True))
    patient_mrn = Column(String(20))
    patient_name = Column(Text)  # Computed from first_name + last_name
    patient_phone = Column(Text)  # From contact_info->>'phone'
    patient_email = Column(Text)  # From contact_info->>'email'
    patient_status = Column(Boolean)  # is_active

    # === PAYMENT DETAILS ===
    payment_date = Column(DateTime(timezone=True))
    total_amount = Column(Numeric(12, 2))
    refunded_amount = Column(Numeric(12, 2))
    net_amount = Column(Numeric(12, 2))  # total_amount - refunded_amount

    # === DATE GROUPING FIELDS ===
    payment_year = Column(Numeric)
    payment_month = Column(Numeric)
    payment_month_year = Column(String(7))  # YYYY-MM
    payment_quarter = Column(String(1))
    payment_day_name = Column(String(10))

    # === PAYMENT METHOD BREAKDOWN ===
    cash_amount = Column(Numeric(12, 2))
    credit_card_amount = Column(Numeric(12, 2))
    debit_card_amount = Column(Numeric(12, 2))
    upi_amount = Column(Numeric(12, 2))
    wallet_points_amount = Column(Numeric(12, 2))  # Loyalty points redeemed
    wallet_transaction_id = Column(PostgresUUID(as_uuid=True))  # Reference to wallet_transaction
    advance_adjustment_amount = Column(Numeric(12, 2))  # Advance adjustment amount
    advance_adjustment_id = Column(PostgresUUID(as_uuid=True))  # Reference to advance_adjustment
    payment_method_total = Column(Numeric(12, 2))  # Total of all payment methods
    # Alias columns for detail sections
    wallet_points_detail_amount = Column(Numeric(12, 2))  # Same as wallet_points_amount
    advance_amount_applied = Column(Numeric(12, 2))  # Same as advance_adjustment_amount

    # === PAYMENT METHOD GROUPING ===
    payment_method_primary = Column(String(30))  # Cash, Credit Card, Debit Card, UPI, Wallet Points, Advance, Multiple

    # === PAYMENT METHOD DETAILS ===
    card_number_last4 = Column(String(4))
    card_type = Column(String(20))
    upi_id = Column(String(50))
    reference_number = Column(String(50))

    # === CURRENCY ===
    currency_code = Column(String(3))
    exchange_rate = Column(Numeric(10, 6))

    # NOTE: Removed advance_adjustment_id and has_advance_adjustment - these columns don't exist in v_patient_payment_receipts view

    # === WORKFLOW STATUS ===
    workflow_status = Column(String(20))  # draft, pending_approval, approved, rejected, reversed
    requires_approval = Column(Boolean)

    # === SUBMISSION TRACKING ===
    submitted_by = Column(String(15))
    submitted_at = Column(DateTime(timezone=True))

    # === APPROVAL TRACKING ===
    approved_by = Column(String(15))
    approved_at = Column(DateTime(timezone=True))

    # === REJECTION TRACKING ===
    rejected_by = Column(String(15))
    rejected_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)

    # === GL POSTING STATUS ===
    gl_posted = Column(Boolean)
    posting_date = Column(DateTime(timezone=True))
    gl_entry_id = Column(PostgresUUID(as_uuid=True))

    # === REVERSAL STATUS ===
    is_reversed = Column(Boolean)
    reversed_at = Column(DateTime(timezone=True))
    reversed_by = Column(String(15))
    reversal_reason = Column(Text)

    # === REFUND INFORMATION ===
    refund_date = Column(DateTime(timezone=True))
    refund_reason = Column(Text)
    has_refund = Column(Boolean)

    # === SOFT DELETE STATUS ===
    is_deleted = Column(Boolean)

    # === RECONCILIATION STATUS ===
    reconciliation_status = Column(String(20))
    reconciliation_date = Column(DateTime(timezone=True))

    # === NOTES ===
    notes = Column(Text)

    # === AUDIT FIELDS ===
    created_at = Column(DateTime(timezone=True))
    created_by = Column(String(50))
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(50))

    # === BRANCH INFORMATION ===
    branch_id = Column(PostgresUUID(as_uuid=True))
    branch_name = Column(String(100))

    # === AGING INFORMATION ===
    payment_age_days = Column(Integer)
    aging_bucket = Column(String(20))  # 0-30 days, 31-60 days, etc.


class PackagePaymentPlanView(Base):
    """
    Comprehensive view of package payment plans with patient, package, invoice, and installment details
    Joins package_payment_plans, patients, packages, invoice_header, branches, and hospitals
    Used for: Payment plan list, search, filtering, reporting, session tracking
    """
    __tablename__ = 'package_payment_plans_view'
    __table_args__ = {'info': {'is_view': True}}  # Mark as view

    # === PRIMARY IDENTIFICATION ===
    plan_id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    hospital_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    branch_id = Column(PostgresUUID(as_uuid=True))

    # === PATIENT INFORMATION ===
    patient_id = Column(PostgresUUID(as_uuid=True))
    patient_name = Column(String(200))
    patient_first_name = Column(String(100))
    patient_last_name = Column(String(100))
    mrn = Column(String(20))
    patient_phone = Column(String(15))
    patient_email = Column(String(100))
    patient_dob = Column(Date)
    patient_gender = Column(String(20))

    # === INVOICE INFORMATION ===
    invoice_id = Column(PostgresUUID(as_uuid=True))
    invoice_number = Column(String(50))
    invoice_date = Column(Date)
    invoice_status = Column(String(20))
    invoice_total = Column(Numeric(12, 2))
    invoice_paid = Column(Numeric(12, 2))
    invoice_balance = Column(Numeric(12, 2))

    # === PACKAGE INFORMATION ===
    package_id = Column(PostgresUUID(as_uuid=True))
    package_name = Column(String(255))
    package_price = Column(Numeric(12, 2))
    package_code = Column(String(50))
    package_description = Column(Text)

    # === SESSION INFORMATION ===
    total_sessions = Column(Integer)
    completed_sessions = Column(Integer)
    remaining_sessions = Column(Integer)
    session_completion_percentage = Column(Numeric(5, 2))

    # === FINANCIAL INFORMATION ===
    total_amount = Column(Numeric(12, 2))
    paid_amount = Column(Numeric(12, 2))
    balance_amount = Column(Numeric(12, 2))
    payment_percentage = Column(Numeric(5, 2))

    # === INSTALLMENT CONFIGURATION ===
    installment_count = Column(Integer)
    installment_frequency = Column(String(20))
    first_installment_date = Column(Date)

    # === STATUS INFORMATION ===
    status = Column(String(20))
    status_badge_color = Column(String(20))

    # === CANCELLATION INFORMATION ===
    cancelled_at = Column(DateTime(timezone=True))
    cancelled_by = Column(String(15))
    cancellation_reason = Column(Text)

    # === SUSPENSION INFORMATION ===
    suspended_at = Column(DateTime(timezone=True))
    suspended_by = Column(String(15))
    suspension_reason = Column(Text)

    # === NOTES ===
    notes = Column(Text)

    # === AUDIT INFORMATION ===
    created_at = Column(DateTime(timezone=True))
    created_by = Column(String(15))
    updated_at = Column(DateTime(timezone=True))
    updated_by = Column(String(15))

    # === SOFT DELETE INFORMATION ===
    is_deleted = Column(Boolean)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(15))

    # === BRANCH INFORMATION ===
    branch_name = Column(String(100))

    # === HOSPITAL INFORMATION ===
    hospital_name = Column(String(100))

    # === COMPUTED DISPLAY FIELDS ===
    patient_display = Column(Text)
    package_display = Column(Text)
    plan_display = Column(Text)

    # === COMPUTED DATE FIELDS ===
    plan_age_days = Column(Numeric)
    next_due_date = Column(Date)
    next_session_date = Column(Date)
    has_overdue_installments = Column(Boolean)


# Helper functions for working with views
def get_view_model(entity_type: str):
    """
    Get the appropriate view model for an entity type

    Args:
        entity_type: The entity type (e.g., 'purchase_orders', 'supplier_invoices', 'supplier_payments',
                     'patient_invoices', 'consolidated_patient_invoices', 'patient_payment_receipts')

    Returns:
        The corresponding view model class
    """
    view_models = {
        'purchase_orders': PurchaseOrderView,
        'supplier_invoices': SupplierInvoiceView,
        'supplier_payments': SupplierPaymentView,
        'supplier_advance_balance': SupplierAdvanceBalanceView,
        'supplier_advance_transactions': SupplierAdvanceTransactionView,
        'patient_invoices': PatientInvoiceView,
        'consolidated_patient_invoices': ConsolidatedPatientInvoiceView,
        'patient_payment_receipts': PatientPaymentReceiptView,
        'package_payment_plans': PackagePaymentPlanView
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