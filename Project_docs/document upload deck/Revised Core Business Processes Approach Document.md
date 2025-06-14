Revised Core Business Processes Approach Document
Overview
Based on your requirements, this document focuses solely on the following core business processes:

Billing & Collection for Services and Pharmacy
Inventory Management
Supplier Invoice & Payment Processing
Basic GL Framework for Financial Transactions
Required Master Data Management

Design Considerations
Timezone Handling

All timestamp fields will use DateTime(timezone=True) to store timezone information
Hospital and Branch settings will include timezone configuration for international consultations
All date/time operations will respect the configured timezone

Currency Management

Price and amount fields will include associated currency information
A currency master table will maintain exchange rates
Transaction records will include currency code for international payments

Record Tracking

Existing TimestampMixin will be used for all tables to track creation and modification
Additional fields for tracking who created, modified, or deleted each record

Address Structure

Address stored as JSONB but frontend will capture components separately
City, Country, and Pincode will be captured as distinct fields in the UI
Address validation will be implemented based on country/region

UI Design

Light/dark mode preference stored at user level
Theme setting persisted across the application
Toggle controls accessible from main screens

Current Database Structure
The following key models already exist in the database:
Base Structures

Base: SQLAlchemy base class
TimestampMixin: Common timestamp fields (created_at, updated_at)
TenantMixin: Hospital identification for multi-tenant architecture
SoftDeleteMixin: Soft delete functionality

Existing Master Data Tables

Hospital: Tenant-level configuration
Branch: Branch-level settings
Staff: Staff member information
Patient: Patient information
RoleMaster: Role definitions
ModuleMaster: Module configuration
RoleModuleAccess: Access control settings
UserRoleMapping: User-role assignments
ParameterSettings: System parameters

Existing Transaction Tables

User: User authentication
LoginHistory: Login tracking
UserSession: Session management
VerificationCode: Code verification
StaffApprovalRequest: Staff onboarding workflow

Enhancements to Existing Tables
These modifications will be applied to existing tables to support the new business processes:
Hospital (Enhancements)
python# Add to Hospital model
gst_registration_number = Column(String(15))  # GSTIN
pan_number = Column(String(10))  # PAN
state_code = Column(String(2))  # GST state code
timezone = Column(String(50), default='Asia/Kolkata')  # For international operations
default_currency = Column(String(3), default='INR')  # Default currency
return_filing_period = Column(String(10))  # Monthly/Quarterly
bank_account_details = Column(JSONB)  # Banking information for payments
Branch (Enhancements)
python# Add to Branch model
gst_registration_number = Column(String(15))  # If different from hospital
state_code = Column(String(2))  # Branch state code
timezone = Column(String(50))  # Branch timezone, defaults to hospital
User (Enhancements)
python# Add to User model
ui_preferences = Column(JSONB, default={"theme": "light"})  # UI preferences including theme
last_currency = Column(String(3))  # Last used currency
New Tables for Core Business Processes
Master Data Tables
CurrencyMaster
pythonclass CurrencyMaster(Base, TimestampMixin, TenantMixin):
    """Currency configuration"""
    __tablename__ = 'currency_master'
    
    currency_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    currency_code = Column(String(3), nullable=False)  # ISO 4217 code (e.g., INR, USD)
    currency_name = Column(String(50), nullable=False)
    currency_symbol = Column(String(5), nullable=False)
    exchange_rate = Column(Numeric(10, 6), nullable=False)  # Against base currency
    is_base_currency = Column(Boolean, default=False)  # Hospital's base currency
    decimal_places = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
PackageFamily
pythonclass PackageFamily(Base, TimestampMixin, TenantMixin):
    """Package families for grouping related packages"""
    __tablename__ = 'package_families'
    
    package_family_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_family = Column(String(100), nullable=False)
    description = Column(String(255))
    status = Column(String(20), default='active')
Package
pythonclass Package(Base, TimestampMixin, TenantMixin):
    """Treatment or service packages"""
    __tablename__ = 'packages'
    
    package_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_family_id = Column(UUID(as_uuid=True), ForeignKey('package_families.package_family_id'))
    package_name = Column(String(100), nullable=False)
    
    # Pricing and GST
    price = Column(Numeric(10, 2), nullable=False)  # Base price excluding GST
    currency_code = Column(String(3), default='INR')
    gst_rate = Column(Numeric(5, 2))  # Overall GST rate (%)
    cgst_rate = Column(Numeric(5, 2))  # Central GST rate (%)
    sgst_rate = Column(Numeric(5, 2))  # State GST rate (%)
    igst_rate = Column(Numeric(5, 2))  # Integrated GST rate (%)
    is_gst_exempt = Column(Boolean, default=False)
    
    # Business rules
    service_owner = Column(String(100))  # Responsible staff/department
    max_discount = Column(Numeric(5, 2))  # Maximum allowed discount percentage
    status = Column(String(20), default='active')  # active/discontinued
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
Service
pythonclass Service(Base, TimestampMixin, TenantMixin):
    """Individual services offered"""
    __tablename__ = 'services'
    
    service_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    code = Column(String(20), nullable=False)
    service_name = Column(String(100), nullable=False)
    
    # Pricing and GST
    price = Column(Numeric(10, 2), nullable=False)  # Base price excluding GST
    currency_code = Column(String(3), default='INR')
    sac_code = Column(String(10))  # Service Accounting Code for GST
    gst_rate = Column(Numeric(5, 2))  # Overall GST rate (%)
    cgst_rate = Column(Numeric(5, 2))  # Central GST rate (%)
    sgst_rate = Column(Numeric(5, 2))  # State GST rate (%)
    igst_rate = Column(Numeric(5, 2))  # Integrated GST rate (%)
    is_gst_exempt = Column(Boolean, default=False)
    
    # Business rules
    priority = Column(String(20))  # Priority level
    service_owner = Column(String(100))  # Responsible staff/department
    max_discount = Column(Numeric(5, 2))  # Maximum allowed discount percentage
    default_gl_account = Column(UUID(as_uuid=True), ForeignKey('chart_of_accounts.account_id'))
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
PackageServiceMapping
pythonclass PackageServiceMapping(Base, TimestampMixin, TenantMixin):
    """Maps services to packages"""
    __tablename__ = 'package_service_mapping'
    
    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'), nullable=False)
    sessions = Column(Integer, default=1)  # Number of sessions included
    is_optional = Column(Boolean, default=False)
MedicineCategory
pythonclass MedicineCategory(Base, TimestampMixin, TenantMixin):
    """Categories of medicines"""
    __tablename__ = 'medicine_categories'
    
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    
    # GST Information
    gst_rate = Column(Numeric(5, 2))  # Standard GST rate for this category
    
    # Business rules
    requires_prescription = Column(Boolean, default=False)
    category_type = Column(String(20))  # OTC/Prescription/Product/Consumable/Misc
    
    # For consumables
    procedure_linked = Column(Boolean, default=False)  # If used in procedures
    
    status = Column(String(20), default='active')
Manufacturer
pythonclass Manufacturer(Base, TimestampMixin, TenantMixin):
    """Medicine manufacturers"""
    __tablename__ = 'manufacturers'
    
    manufacturer_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    manufacturer_name = Column(String(100), nullable=False)
    manufacturer_address = Column(JSONB)
    specialization = Column(String(100))
    
    # GST Information
    gst_registration_number = Column(String(15))
    pan_number = Column(String(10))
    tax_type = Column(String(20))  # Regular/Composition/Unregistered
    state_code = Column(String(2))
    
    remarks = Column(String(255))
    status = Column(String(20), default='active')
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
Supplier
pythonclass Supplier(Base, TimestampMixin, TenantMixin):
    """Medicine and equipment suppliers"""
    __tablename__ = 'suppliers'
    
    supplier_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    supplier_name = Column(String(100), nullable=False)
    supplier_category = Column(String(50))  # Retail supplier, Distributor, etc.
    
    # Address as JSONB but UI will capture components separately
    supplier_address = Column(JSONB)  # Will include city, country, pincode separately
    
    # Contact Information
    contact_person_name = Column(String(100))
    contact_info = Column(JSONB)  # Can include phone, mobile, fax, etc.
    manager_name = Column(String(100))
    manager_contact_info = Column(JSONB)  # Can include phone, mobile, fax, etc.
    email = Column(String(100))
        
    # Business Rules
    black_listed = Column(Boolean, default=False)
    performance_rating = Column(Integer)  # 1-5 scale
    payment_terms = Column(String(100))
    
    # GST Information
    gst_registration_number = Column(String(15))
    pan_number = Column(String(10))
    tax_type = Column(String(20))  # Regular/Composition/Unregistered
    state_code = Column(String(2))
    
    bank_details = Column(JSONB)
    remarks = Column(String(255))
    status = Column(String(20), default='active')
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
Medicine
pythonclass Medicine(Base, TimestampMixin, TenantMixin):
    """Medicine master data"""
    __tablename__ = 'medicines'
    
    medicine_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    medicine_name = Column(String(100), nullable=False)
    manufacturer_id = Column(UUID(as_uuid=True), ForeignKey('manufacturers.manufacturer_id'))
    preferred_supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'))
    category_id = Column(UUID(as_uuid=True), ForeignKey('medicine_categories.category_id'))
    
    # Medicine Details
    generic_name = Column(String(100))
    dosage_form = Column(String(50))  # Tablet, Syrup, Injection, etc.
    unit_of_measure = Column(String(20))  # Strips, Bottles
    
    # Medicine Type (Business Rule #2)
    medicine_type = Column(String(20), nullable=False)  # OTC/Prescription/Product/Consumable/Misc
    
    # GST Information
    hsn_code = Column(String(10))  # HSN code for GST
    gst_rate = Column(Numeric(5, 2))  # Overall GST rate (%)
    cgst_rate = Column(Numeric(5, 2))  # Central GST rate (%)
    sgst_rate = Column(Numeric(5, 2))  # State GST rate (%)
    igst_rate = Column(Numeric(5, 2))  # Integrated GST rate (%)
    is_gst_exempt = Column(Boolean, default=False)  # Business Rule #1
    gst_inclusive = Column(Boolean, default=False)  # Whether MRP includes GST
    
    # Inventory Management
    safety_stock = Column(Integer)  # Minimum stock level
    priority = Column(String(20))  # Priority level for reordering
    current_stock = Column(Integer)  # Current available stock (derived)
    
    # Business Rules
    prescription_required = Column(Boolean, default=False)  # For prescription drugs
    is_consumable = Column(Boolean, default=False)  # For consumables in procedures
    
    # GL Account Mapping
    default_gl_account = Column(UUID(as_uuid=True), ForeignKey('chart_of_accounts.account_id'))
    
    # Status
    status = Column(String(20), default='active')
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
ConsumableStandard
pythonclass ConsumableStandard(Base, TimestampMixin, TenantMixin):
    """Standard consumable usage for procedures (Business Rule #7)"""
    __tablename__ = 'consumable_standards'
    
    standard_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'), nullable=False)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'), nullable=False)
    
    # Consumption details
    standard_quantity = Column(Numeric(10, 2), nullable=False)  # Standard quantity used
    unit_of_measure = Column(String(20))  # Unit of measurement
    
    # Status and audit
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50))
    updated_by = Column(String(50))
ChartOfAccounts
pythonclass ChartOfAccounts(Base, TimestampMixin, TenantMixin):
    """Chart of accounts for financial entries"""
    __tablename__ = 'chart_of_accounts'
    
    account_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    account_group = Column(String(20), nullable=False)  # Assets, Liabilities, Income, Expense
    gl_account_no = Column(String(20), nullable=False)
    account_name = Column(String(100), nullable=False)
    parent_account_id = Column(UUID(as_uuid=True), ForeignKey('chart_of_accounts.account_id'))
    
    # Financial Data
    opening_balance = Column(Numeric(12, 2))
    opening_balance_date = Column(Date)
    
    # Configuration
    is_posting_account = Column(Boolean, default=True)  # Can post to this account
    invoice_type_mapping = Column(String(50))  # For default account by invoice type (Business Rule #9)
    
    # GST Configuration
    gst_related = Column(Boolean, default=False)
    gst_component = Column(String(10))  # CGST, SGST, IGST if applicable
    
    # Status and audit
    is_active = Column(Boolean, default=True)
    created_by = Column(String(50))
    updated_by = Column(String(50))
Transaction Tables
InvoiceHeader
pythonclass InvoiceHeader(Base, TimestampMixin, TenantMixin):
    """Invoice header information"""
    __tablename__ = 'invoice_header'
    
    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    
    # Invoice Details
    invoice_number = Column(String(50), nullable=False, unique=True)  # Formatted tax invoice number
    invoice_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    invoice_type = Column(String(50), nullable=False)  # Service, Product, Prescription, Misc
    is_gst_invoice = Column(Boolean, default=True)  # Business Rule #4 - GST or non-GST bill
    
    # Customer Information
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    
    # GST Information
    place_of_supply = Column(String(2))  # State code
    reverse_charge = Column(Boolean, default=False)
    e_invoice_irn = Column(String(100))  # E-invoice reference number
    is_interstate = Column(Boolean, default=False)
    
    # Currency Information
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)  # For international payments
    
    # Amounts
    total_amount = Column(Numeric(12, 2), nullable=False)  # Gross total
    total_discount = Column(Numeric(12, 2), default=0)  # Total discount
    total_taxable_value = Column(Numeric(12, 2))  # Pre-tax amount
    total_cgst_amount = Column(Numeric(12, 2), default=0)
    total_sgst_amount = Column(Numeric(12, 2), default=0)
    total_igst_amount = Column(Numeric(12, 2), default=0)
    grand_total = Column(Numeric(12, 2), nullable=False)  # Final amount with tax
    
    # Payment Status
    paid_amount = Column(Numeric(12, 2), default=0)
    balance_due = Column(Numeric(12, 2))  # Calculated
    
    # Default GL Account (Business Rule #9)
    gl_account_id = Column(UUID(as_uuid=True), ForeignKey('chart_of_accounts.account_id'))
    
    # Additional Information
    notes = Column(Text)
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
InvoiceLineItem
pythonclass InvoiceLineItem(Base, TimestampMixin, TenantMixin):
    """Invoice line items"""
    __tablename__ = 'invoice_line_item'
    
    line_item_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'), nullable=False)
    
    # Item Reference - one of these must be populated
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'))
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'))
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'))
    
    # Item Details
    item_type = Column(String(20), nullable=False)  # Package, Service, Medicine
    item_name = Column(String(100), nullable=False)
    hsn_sac_code = Column(String(10))
    
    # For medicines
    batch = Column(String(20))  # Batch number (Business Rule #6)
    expiry_date = Column(Date)  # Expiry date
    
    # For Prescription Drugs included in consultation (Business Rule #5)
    included_in_consultation = Column(Boolean, default=False)
    
    # Quantities and Amounts
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(12, 2), nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    taxable_amount = Column(Numeric(12, 2))  # Amount before tax
    
    # GST Details
    gst_rate = Column(Numeric(5, 2))
    cgst_rate = Column(Numeric(5, 2))
    sgst_rate = Column(Numeric(5, 2))
    igst_rate = Column(Numeric(5, 2))
    cgst_amount = Column(Numeric(12, 2), default=0)
    sgst_amount = Column(Numeric(12, 2), default=0)
    igst_amount = Column(Numeric(12, 2), default=0)
    total_gst_amount = Column(Numeric(12, 2), default=0)
    
    # Line Total
    line_total = Column(Numeric(12, 2), nullable=False)  # Including tax
    
    # For profitability tracking (Business Rule #11)
    cost_price = Column(Numeric(12, 2))  # Cost of medicine or service
    profit_margin = Column(Numeric(12, 2))  # Calculated profit
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
PaymentDetail
pythonclass PaymentDetail(Base, TimestampMixin, TenantMixin):
    """Payment details for invoices"""
    __tablename__ = 'payment_details'
    
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'), nullable=False)
    
    # Payment Information
    payment_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    
    # Payment Methods
    cash_amount = Column(Numeric(12, 2), default=0)
    credit_card_amount = Column(Numeric(12, 2), default=0)
    debit_card_amount = Column(Numeric(12, 2), default=0)
    upi_amount = Column(Numeric(12, 2), default=0)
    
    # Currency Information
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)  # For international payments
    
    # Payment Details
    card_number_last4 = Column(String(4))
    card_type = Column(String(20))
    upi_id = Column(String(50))
    reference_number = Column(String(50))
    
    # Totals
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # Refund Information
    refunded_amount = Column(Numeric(12, 2), default=0)
    refund_date = Column(DateTime(timezone=True))
    refund_reason = Column(String(255))
    
    # GL Reference
    gl_entry_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # For Bank Reconciliation (Business Rule #8)
    reconciliation_status = Column(String(20), default='pending')  # pending, reconciled, disputed
    reconciliation_date = Column(DateTime(timezone=True))
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
PurchaseOrderHeader
pythonclass PurchaseOrderHeader(Base, TimestampMixin, TenantMixin):
    """Purchase order header"""
    __tablename__ = 'purchase_order_header'
    
    po_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    po_number = Column(String(20), nullable=False, unique=True)
    po_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    
    # Supplier Information
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    
    # Reference Information
    quotation_id = Column(String(50))
    quotation_date = Column(Date)
    
    # Delivery Information
    expected_delivery_date = Column(Date)
    
    # Currency Information
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    
    # Status
    status = Column(String(20), default='draft')  # draft, approved, received, cancelled
    deleted_flag = Column(Boolean, default=False)
    
    # Approval Information
    approved_by = Column(String(50))
    
    # Amounts
    total_amount = Column(Numeric(12, 2))
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
PurchaseOrderLine
pythonclass PurchaseOrderLine(Base, TimestampMixin, TenantMixin):
    """Purchase order line items"""
    __tablename__ = 'purchase_order_line'
    
    line_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    po_id = Column(UUID(as_uuid=True), ForeignKey('purchase_order_header.po_id'), nullable=False)
    
    # Item Information
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'), nullable=False)
    medicine_name = Column(String(100), nullable=False)
    
    # Quantity and Price
    units = Column(Numeric(10, 2), nullable=False)  # Quantity ordered
    pack_purchase_price = Column(Numeric(12, 2), nullable=False)  # Price per pack
    pack_mrp = Column(Numeric(12, 2), nullable=False)  # MRP per pack
    units_per_pack = Column(Numeric(10, 2), nullable=False)  # Units in each pack
    unit_price = Column(Numeric(12, 2))  # Derived unit price
    
    # GST Information
    hsn_code = Column(String(10))
    gst_rate = Column(Numeric(5, 2))
    cgst_rate = Column(Numeric(5, 2))
    sgst_rate = Column(Numeric(5, 2))
    igst_rate = Column(Numeric(5, 2))
    cgst = Column(Numeric(12, 2), default=0)
    sgst = Column(Numeric(12, 2), default=0)
    igst = Column(Numeric(12, 2), default=0)
    total_gst = Column(Numeric(12, 2), default=0)
    
    # Line Total
    line_total = Column(Numeric(12, 2))
    
    # Delivery
    expected_delivery_date = Column(Date)
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
SupplierInvoice
pythonclass SupplierInvoice(Base, TimestampMixin, TenantMixin):
    """Supplier invoice information"""
    __tablename__ = 'supplier_invoice'
    
    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    po_id = Column(UUID(as_uuid=True), ForeignKey('purchase_order_header.po_id'))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    
    # Invoice Details
    supplier_invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    
    # GST Information
    supplier_gstin = Column(String(15))
    place_of_supply = Column(String(2))  # State code
    reverse_charge = Column(Boolean, default=False)
    
    # Currency Information
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    
    # GST Amounts
    cgst_amount = ColumnRetryClaude hit the max length for a message and has paused its response. You can write Continue to keep the chat going.VKcontinueEditLet me continue with the supplier invoice and remaining transaction tables:
SupplierInvoice (continued)
pythonclass SupplierInvoice(Base, TimestampMixin, TenantMixin):
    """Supplier invoice information"""
    __tablename__ = 'supplier_invoice'
    
    # GST Amounts
    cgst_amount = Column(Numeric(12, 2), default=0)
    sgst_amount = Column(Numeric(12, 2), default=0)
    igst_amount = Column(Numeric(12, 2), default=0)
    total_gst_amount = Column(Numeric(12, 2), default=0)
    
    # Invoice Amounts
    total_amount = Column(Numeric(12, 2), nullable=False)
    
    # ITC Eligibility
    itc_eligible = Column(Boolean, default=True)
    
    # Payment Information
    payment_status = Column(String(20), default='unpaid')  # unpaid, partial, paid
    due_date = Column(Date)
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
SupplierInvoiceLine
pythonclass SupplierInvoiceLine(Base, TimestampMixin, TenantMixin):
    """Supplier invoice line items"""
    __tablename__ = 'supplier_invoice_line'
    
    line_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'), nullable=False)
    
    # Item Information
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'), nullable=False)
    medicine_name = Column(String(100), nullable=False)
    
    # Quantity and Price
    units = Column(Numeric(10, 2), nullable=False)  # Quantity received
    pack_purchase_price = Column(Numeric(12, 2), nullable=False)  # Price per pack
    pack_mrp = Column(Numeric(12, 2), nullable=False)  # MRP per pack
    units_per_pack = Column(Numeric(10, 2), nullable=False)  # Units in each pack
    unit_price = Column(Numeric(12, 2))  # Derived unit price
    
    # Free items handling (Business Rule #3)
    is_free_item = Column(Boolean, default=False)
    referenced_line_id = Column(UUID(as_uuid=True))  # Reference to paid item for free items
    
    # Discount handling (Business Rule #3)
    discount_percent = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(12, 2), default=0)
    pre_gst_discount = Column(Boolean, default=True)  # Whether discount applied before GST
    
    # Taxable Amount
    taxable_amount = Column(Numeric(12, 2))
    
    # GST Information
    hsn_code = Column(String(10))
    gst_rate = Column(Numeric(5, 2))
    cgst_rate = Column(Numeric(5, 2))
    sgst_rate = Column(Numeric(5, 2))
    igst_rate = Column(Numeric(5, 2))
    cgst = Column(Numeric(12, 2), default=0)
    sgst = Column(Numeric(12, 2), default=0)
    igst = Column(Numeric(12, 2), default=0)
    total_gst = Column(Numeric(12, 2), default=0)
    
    # Line Total
    line_total = Column(Numeric(12, 2))
    
    # Batch Information
    batch_number = Column(String(20))
    manufacturing_date = Column(Date)
    expiry_date = Column(Date)
    
    # ITC Eligibility
    itc_eligible = Column(Boolean, default=True)
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
SupplierPayment
pythonclass SupplierPayment(Base, TimestampMixin, TenantMixin):
    """Payments to suppliers"""
    __tablename__ = 'supplier_payment'
    
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'))
    
    # Payment Details
    payment_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    payment_method = Column(String(20))
    
    # Currency Information
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    
    # Payment Amount
    amount = Column(Numeric(12, 2), nullable=False)
    reference_no = Column(String(50))
    status = Column(String(20), default='completed')
    notes = Column(String(255))
    
    # GL Reference
    gl_entry_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # For Bank Reconciliation (Business Rule #8)
    reconciliation_status = Column(String(20), default='pending')  # pending, reconciled, disputed
    reconciliation_date = Column(DateTime(timezone=True))
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
Inventory
pythonclass Inventory(Base, TimestampMixin, TenantMixin):
    """Inventory movement tracking"""
    __tablename__ = 'inventory'
    
    stock_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    
    # Transaction Type
    stock_type = Column(String(30), nullable=False)  # Opening Stock, Stock Adjustment, Purchase, etc.
    
    # References
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'), nullable=False)
    distributor_invoice_no = Column(String(50))
    po_id = Column(UUID(as_uuid=True), ForeignKey('purchase_order_header.po_id'))
    bill_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'))
    
    # Item Details
    medicine_name = Column(String(100), nullable=False)
    medicine_category = Column(String(50))
    
    # Batch Information (Business Rule #6)
    batch = Column(String(20), nullable=False)
    expiry = Column(Date, nullable=False)
    
    # Pricing Information
    pack_purchase_price = Column(Numeric(12, 2))
    pack_mrp = Column(Numeric(12, 2))
    units_per_pack = Column(Numeric(10, 2))
    unit_price = Column(Numeric(12, 2))  # Derived
    sale_price = Column(Numeric(12, 2))
    
    # Transaction Details
    units = Column(Numeric(10, 2), nullable=False)  # Quantity in/out
    percent_discount = Column(Numeric(5, 2), default=0)
    
    # GST Information
    cgst = Column(Numeric(12, 2), default=0)
    sgst = Column(Numeric(12, 2), default=0)
    igst = Column(Numeric(12, 2), default=0)
    total_gst = Column(Numeric(12, 2), default=0)
    
    # For Consumables Used In Procedures (Business Rule #7)
    procedure_id = Column(UUID(as_uuid=True))  # Service ID for procedure
    
    # Additional Information
    reason = Column(String(255))  # For adjustments
    current_stock = Column(Integer)  # Running balance
    location = Column(String(50))
    
    # Timestamps with timezone
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
GLTransaction
pythonclass GLTransaction(Base, TimestampMixin, TenantMixin):
    """General Ledger Transactions"""
    __tablename__ = 'gl_transaction'
    
    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    
    # Transaction Details
    transaction_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    transaction_type = Column(String(50), nullable=False)
    reference_id = Column(String(50))  # Invoice ID, PO ID, etc.
    description = Column(String(255))
    
    # Currency Information
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    
    # Transaction Totals
    total_debit = Column(Numeric(12, 2), nullable=False)
    total_credit = Column(Numeric(12, 2), nullable=False)
    
    # For Account Reconciliation (Business Rule #8)
    reconciliation_status = Column(String(20), default='none')  # none, pending, reconciled
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
GLEntry
pythonclass GLEntry(Base, TimestampMixin, TenantMixin):
    """General Ledger Entry Lines"""
    __tablename__ = 'gl_entry'
    
    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey('chart_of_accounts.account_id'), nullable=False)
    
    # Entry Details
    debit_amount = Column(Numeric(12, 2), default=0)
    credit_amount = Column(Numeric(12, 2), default=0)
    entry_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    description = Column(String(255))
    
    # For profitability analysis (Business Rule #11)
    profit_center = Column(String(50))  # Service, department, etc.
    cost_center = Column(String(50))  # Cost allocation
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
GSTLedger
pythonclass GSTLedger(Base, TimestampMixin, TenantMixin):
    """GST Input/Output Tracking"""
    __tablename__ = 'gst_ledger'
    
    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    
    # Transaction Details
    transaction_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    transaction_type = Column(String(30), nullable=False)  # Sales/Purchase/Adjustment
    transaction_reference = Column(String(50))  # Invoice/Bill reference
    
    # GST Amounts
    cgst_output = Column(Numeric(12, 2), default=0)  # CGST collected on sales
    sgst_output = Column(Numeric(12, 2), default=0)  # SGST collected on sales
    igst_output = Column(Numeric(12, 2), default=0)  # IGST collected on sales
    cgst_input = Column(Numeric(12, 2), default=0)   # CGST paid on purchases
    sgst_input = Column(Numeric(12, 2), default=0)   # SGST paid on purchases
    igst_input = Column(Numeric(12, 2), default=0)   # IGST paid on purchases
    
    # ITC Claims
    itc_claimed = Column(Boolean, default=False)
    claim_reference = Column(String(50))  # Reference to GST return
    
    # GL Reference
    gl_reference = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # Reporting Period
    entry_month = Column(Integer)  # Month for reporting
    entry_year = Column(Integer)   # Year for reporting
    
    # Audit fields
    created_by = Column(String(50))
    updated_by = Column(String(50))
Business Rules Implementation in Data Model
1. GST Applicability for Medicines

Added is_gst_exempt flag in the Medicine model
This allows marking specific medicines as GST exempt

2. Medicine Types

Implemented medicine_type field in the Medicine model with values:

OTC medicine
Prescription drugs
Products
Consumables
Misc items


Medicine category model includes a category_type field
prescription_required and is_consumable flags for additional control

3. Discount Handling in Vendor Invoices

Added fields to handle GST discount scenarios in SupplierInvoiceLine:

pre_gst_discount flag to indicate if discount is applied before GST
is_free_item flag for free products
referenced_line_id to connect free items to their corresponding paid items



4. GST vs Non-GST Bills

Added is_gst_invoice flag in InvoiceHeader to distinguish between GST and non-GST bills
Invoice numbering can be handled through separate sequences for each type

5. Prescription Drugs in Consultation

Added included_in_consultation flag in InvoiceLineItem to mark medicines included in consultation fee

6. Batch and Expiry-Based Inventory Management

Implemented batch tracking in Inventory and InvoiceLineItem
Expiry dates tracked at batch level
Query support for FIFO dispensing can be built using this structure

7. Consumables for Procedures

Added ConsumableStandard table to define standard consumable usage for services/procedures
Linked consumables to procedures through procedure_id in the Inventory model

8. Bank Account Reconciliation

Added reconciliation fields to payment-related tables:

reconciliation_status and reconciliation_date in PaymentDetail and SupplierPayment
Fields in GLTransaction to support reconciliation process



9. Account Head for Invoice Types

Added invoice_type_mapping in ChartOfAccounts to map GL accounts to invoice types
Added gl_account_id in InvoiceHeader for default accounting assignment
Added default_gl_account fields in Service and Medicine models

10. Payment Gateway Integration

Payment tables include fields needed for future payment gateway integration:

Reference numbers
Card details
UPI information



11. Product/Service Profitability

Added profitability tracking fields:

cost_price and profit_margin in InvoiceLineItem
profit_center and cost_center in GLEntry



Data Model Considerations

Timezone Support

All DateTime fields use DateTime(timezone=True) to store timezone information
This ensures proper handling of international consultations
Hospital and Branch models include timezone settings


Currency Management

Added CurrencyMaster table for currency configuration
Currency fields in all transaction tables
Exchange rates included for international payments


Record Tracking

Leveraging existing TimestampMixin for creation/modification timestamps
Added created_by and updated_by fields to all tables


Address Handling

Address stored as JSONB for flexibility
UI will present separate fields for city, country, pincode


UI Preferences

Added ui_preferences JSONB field in User model to store theme preferences



Implementation Approach
The implementation should proceed in phases:
Phase 1: Master Data Foundation

Implement currency, package, service, and medicine-related tables
Set up account chart structure
Establish hospital/branch GST settings

Phase 2: Core Transaction Framework

Implement invoice and payment modules
Set up purchase and supplier invoice modules
Establish inventory tracking

Phase 3: Financial Integration

Implement GL integration
Set up GST tracking
Establish profitability analysis framework

Conclusion
This data model provides a comprehensive structure to support the specified core business processes while incorporating all the business rules you outlined. The design:

Maintains clear separation between existing and new tables
Follows SQLAlchemy and PostgreSQL best practices
Supports timezone and currency requirements for international operations
Incorporates GST compliance requirements
Enables profitability tracking
Provides foundation for future enhancements

The model can now serve as the foundation for implementing the core business processes of billing, inventory, supplier management, and basic financial tracking for the SkinSpire Clinic HMS.