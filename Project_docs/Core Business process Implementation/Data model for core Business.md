Revised Data Model for SkinSpire Clinic HMS
Table Categories
Based on your existing model structure and best practices, I'll organize the tables into three categories:

Base Tables: Core entities and reusable components (base.py)
Master Data Tables: Reference data and configuration (master.py)
Transaction Tables: Operational data capturing business events (transaction.py)

Database Design Considerations
Looking at your existing models (config.py, master.py, transaction.py), I notice:

You're using SQLAlchemy ORM with proper inheritance
You have mixins for common functionality (TimestampMixin, TenantMixin, SoftDeleteMixin)
You're using PostgreSQL-specific types (UUID, JSONB)
You have a multi-tenant design with hospital_id as the tenant identifier

Refined Table Structure
Base Tables (base.py)
These already exist in your system:
python# Base class providing common attributes
class Base
# Common timestamp fields (created_at, updated_at)
class TimestampMixin
# Tenant identification for multi-tenant architecture
class TenantMixin
# Soft delete functionality
class SoftDeleteMixin
Master Data Tables (master.py)
Hospital (Existing)
pythonclass Hospital(Base, TimestampMixin, SoftDeleteMixin):
    """Hospital (Tenant) level configuration"""
    __tablename__ = 'hospitals'

    hospital_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    license_no = Column(String(50), unique=True)
    address = Column(JSONB)
    contact_details = Column(JSONB)
    settings = Column(JSONB)
    encryption_enabled = Column(Boolean, default=False)
    encryption_key = Column(String(255))
    encryption_config = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    # Add GST related fields
    gst_registration_number = Column(String(15))
    pan_number = Column(String(10))
    state_code = Column(String(2))
    return_filing_period = Column(String(10))  # Monthly/Quarterly
    bank_account_details = Column(JSONB)
Branch (Existing)
pythonclass Branch(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Branch level configuration"""
    __tablename__ = 'branches'

    branch_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(JSONB)
    contact_details = Column(JSONB)
    settings = Column(JSONB)
    is_active = Column(Boolean, default=True)
    # Add GST related fields
    gst_registration_number = Column(String(15))  # If different from hospital
    state_code = Column(String(2))
Staff (Existing with Enhancements)
pythonclass Staff(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Staff member information"""
    __tablename__ = 'staff'

    staff_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    employee_code = Column(String(20), unique=True)
    title = Column(String(10))
    specialization = Column(String(100))
    personal_info = Column(JSONB, nullable=False)  # Structured: first_name, last_name, dob, gender, etc.
    contact_info = Column(JSONB, nullable=False)   # Structured: email, phone, address, etc.
    professional_info = Column(JSONB)  # Structured: qualifications, certifications
    employment_info = Column(JSONB)    # Structured: join date, designation, employee type
    documents = Column(JSONB)          # ID proofs, certificates
    is_active = Column(Boolean, default=True)
    # Additional fields from consolidated doc
    role = Column(String(50), ForeignKey('role_master.role_id'))
    is_employee = Column(Boolean, default=True)
    age = Column(Integer) # Derived from DOB
    preferred_language = Column(String(20))
    city = Column(String(50))
    pin_code = Column(String(10))
    blood_group = Column(String(10))
    marital_status = Column(String(20))
    date_of_joining = Column(DateTime(timezone=True))
    profile_picture = Column(String(255)) # Path to image
Patient (Enhanced from consolidated doc)
pythonclass Patient(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Patient information"""
    __tablename__ = 'patients'

    patient_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    mrn = Column(String(20), unique=True)  # Medical Record Number
    
    # Basic information
    title = Column(String(10))  # Mr. Mrs. Ms. Dr. Prof. etc.
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    gender = Column(String(15))  # Male, Female, Transgender, Not disclosed
    dob = Column(DateTime(timezone=True))
    age = Column(Integer)  # Derived from DOB
    blood_group = Column(String(5))  # O+ve, AB+ve, etc.
    marital_status = Column(String(20))  # Married, Single, Not disclosed
    
    # Contact information
    phone_number = Column(String(15), nullable=False)  # Primary contact
    alternate_phone_number = Column(String(15))  # Secondary contact
    email = Column(String(100))
    preferred_language = Column(String(20))  # English, Hindi, Kannada, Tamil
    city = Column(String(50))
    address = Column(JSONB)  # Structured address
    pin_code = Column(String(10))
    
    # Emergency contact
    attender_name = Column(String(100))
    relationship_with_patient = Column(String(50))
    emergency_contact = Column(JSONB)  # name, relation, contact
    
    # Source information
    referred_by = Column(String(100))
    referral_source = Column(String(50))  # Walk In, Google search, Reference, Social media
    
    # Medical information
    medical_info = Column(Text)  # Encrypted medical history
    known_allergies = Column(JSONB)  # List of allergies with details
    
    # Additional information
    preferences = Column(JSONB)  # language, communication preferences
    documents = Column(JSONB)  # ID proofs, previous records
    profile_picture = Column(String(255))  # Path to profile image
    notes = Column(JSONB)  # Additional notes
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="patients")
    branch = relationship("Branch", back_populates="patients")
    appointments = relationship("Appointment", back_populates="patient")

    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
Package Family
pythonclass PackageFamily(Base, TimestampMixin, TenantMixin):
    """Package families for grouping related packages"""
    __tablename__ = 'package_families'
    
    package_family_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_family = Column(String(100), nullable=False)
    description = Column(String(255))
    status = Column(String(20), default='active')
    
    # Relationships
    packages = relationship("Package", back_populates="family")
Package
pythonclass Package(Base, TimestampMixin, TenantMixin):
    """Treatment or service packages"""
    __tablename__ = 'packages'
    
    package_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_family_id = Column(UUID(as_uuid=True), ForeignKey('package_families.package_family_id'))
    package_name = Column(String(100), nullable=False)
    description = Column(String(255))
    
    # Pricing and GST
    price = Column(Integer, nullable=False)  # Base price excluding GST
    gst_rate = Column(Numeric(5, 2))  # Overall GST rate (%)
    cgst_rate = Column(Numeric(5, 2))  # Central GST rate (%)
    sgst_rate = Column(Numeric(5, 2))  # State GST rate (%)
    igst_rate = Column(Numeric(5, 2))  # Integrated GST rate (%)
    is_gst_exempt = Column(Boolean, default=False)
    
    # Business rules
    service_owner = Column(String(100))  # Responsible staff/department
    max_discount = Column(Integer)  # Maximum allowed discount percentage
    status = Column(String(20), default='active')  # active/discontinued
    
    # Relationships
    family = relationship("PackageFamily", back_populates="packages")
    services = relationship("PackageServiceMapping", back_populates="package")
Service
pythonclass Service(Base, TimestampMixin, TenantMixin):
    """Individual services offered"""
    __tablename__ = 'services'
    
    service_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    code = Column(String(20), unique=True)
    service_name = Column(String(100), nullable=False)
    description = Column(String(255))
    duration = Column(Integer)  # Duration in minutes
    
    # Pricing and GST
    price_per_session = Column(Integer, nullable=False)  # Base price excluding GST
    sac_code = Column(String(10))  # Service Accounting Code for GST
    gst_rate = Column(Numeric(5, 2))  # Overall GST rate (%)
    cgst_rate = Column(Numeric(5, 2))  # Central GST rate (%)
    sgst_rate = Column(Numeric(5, 2))  # State GST rate (%)
    igst_rate = Column(Numeric(5, 2))  # Integrated GST rate (%)
    is_gst_exempt = Column(Boolean, default=False)
    
    # Business rules
    priority = Column(String(20))  # Priority level
    service_owner = Column(String(100))  # Responsible staff/department
    max_discount = Column(Integer)  # Maximum allowed discount percentage
    resources_required = Column(JSONB)  # Equipment/materials needed
    department = Column(String(50))  # Department offering this service
    status = Column(String(20), default='active')
    
    # Relationships
    package_mappings = relationship("PackageServiceMapping", back_populates="service")
Package Service Mapping
pythonclass PackageServiceMapping(Base, TimestampMixin, TenantMixin):
    """Maps services to packages"""
    __tablename__ = 'package_service_mapping'
    
    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'), nullable=False)
    sessions = Column(Integer, default=1)  # Number of sessions included
    is_optional = Column(Boolean, default=False)
    
    # Relationships
    package = relationship("Package", back_populates="services")
    service = relationship("Service", back_populates="package_mappings")
Medicine Category
pythonclass MedicineCategory(Base, TimestampMixin, TenantMixin):
    """Categories of medicines"""
    __tablename__ = 'medicine_categories'
    
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    gst_rate = Column(Numeric(5, 2))  # Standard GST rate for this category
    requires_prescription = Column(Boolean, default=False)
    status = Column(String(20), default='active')
    
    # Relationships
    medicines = relationship("Medicine", back_populates="category")
Manufacturer
pythonclass Manufacturer(Base, TimestampMixin, TenantMixin):
    """Medicine manufacturers"""
    __tablename__ = 'manufacturers'
    
    manufacturer_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    manufacturer_name = Column(String(100), nullable=False)
    manufacturer_address = Column(JSONB)
    specialization = Column(String(100))
    contact_info = Column(JSONB)  # Structured contact details
    
    # GST Information
    gst_registration_number = Column(String(15))
    pan_number = Column(String(10))
    tax_type = Column(String(20))  # Regular/Composition/Unregistered
    state_code = Column(String(2))
    
    remarks = Column(String(255))
    status = Column(String(20), default='active')
    
    # Relationships
    medicines = relationship("Medicine", back_populates="manufacturer")
Supplier
pythonclass Supplier(Base, TimestampMixin, TenantMixin):
    """Medicine and equipment suppliers"""
    __tablename__ = 'suppliers'
    
    supplier_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    supplier_name = Column(String(100), nullable=False)
    supplier_address = Column(JSONB)
    supplier_category = Column(String(50))  # Retail supplier, Distributor, Equipment dealer, Trader
    
    # Contact Information
    contact_person_name = Column(String(100))
    contact_no = Column(String(15))
    manager_name = Column(String(100))
    manager_contact_no = Column(String(15))
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
    
    # Relationships
    purchase_orders = relationship("PurchaseOrderHeader", back_populates="supplier")
    invoices = relationship("SupplierInvoice", back_populates="supplier")
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
    storage_condition = Column(String(100))
    
    # GST Information
    hsn_code = Column(String(10))  # HSN code for GST
    gst_rate = Column(Numeric(5, 2))  # Overall GST rate (%)
    cgst_rate = Column(Numeric(5, 2))  # Central GST rate (%)
    sgst_rate = Column(Numeric(5, 2))  # State GST rate (%)
    igst_rate = Column(Numeric(5, 2))  # Integrated GST rate (%)
    is_gst_exempt = Column(Boolean, default=False)
    gst_inclusive = Column(Boolean, default=False)  # Whether MRP includes GST
    
    # Inventory Management
    safety_stock = Column(Integer)  # Minimum stock level
    priority = Column(String(20))  # Priority level for reordering
    current_stock = Column(Integer)  # Current available stock (derived)
    
    prescription_required = Column(Boolean, default=False)
    status = Column(String(20), default='active')
    
    # Relationships
    manufacturer = relationship("Manufacturer", back_populates="medicines")
    preferred_supplier = relationship("Supplier", foreign_keys=[preferred_supplier_id])
    category = relationship("MedicineCategory", back_populates="medicines")
    inventory_entries = relationship("Inventory", back_populates="medicine")
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
    opening_balance = Column(Integer)
    opening_balance_date = Column(DateTime(timezone=True))
    
    # Configuration
    is_posting_account = Column(Boolean, default=True)  # Can post to this account
    is_active = Column(Boolean, default=True)
    
    # GST Configuration
    gst_related = Column(Boolean, default=False)
    gst_component = Column(String(10))  # CGST, SGST, IGST if applicable
    
    # Relationships
    parent = relationship("ChartOfAccounts", remote_side=[account_id], backref="children")
    gl_entries = relationship("GLEntry", back_populates="account")
Transaction Tables (transaction.py)
Appointment
pythonclass Appointment(Base, TimestampMixin, TenantMixin):
    """Patient appointments"""
    __tablename__ = 'appointments'
    
    appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'))
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'))  # Other staff if applicable
    
    # Appointment Details
    appointment_date = Column(DateTime(timezone=True), nullable=False)
    appointment_time = Column(Time, nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'))
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'))
    department = Column(String(50))
    
    # Status Information
    booking_status = Column(String(20), default='booked')  # Booked, Cancelled, Visited
    appointment_type = Column(String(20))  # In Person, Video Call, Walk-in
    skip_billing = Column(Boolean, default=False)
    
    # Billing Reference
    price = Column(Integer)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Staff", foreign_keys=[doctor_id])
    staff = relationship("Staff", foreign_keys=[staff_id])
    service = relationship("Service")
    package = relationship("Package")
    consultation = relationship("Consultation", back_populates="appointment", uselist=False)
    invoice = relationship("InvoiceHeader")
Consultation
pythonclass Consultation(Base, TimestampMixin, TenantMixin):
    """Doctor consultation details"""
    __tablename__ = 'consultations'
    
    consultation_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey('appointments.appointment_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'), nullable=False)
    
    # Consultation Details
    consultation_date = Column(DateTime(timezone=True), nullable=False)
    consultation_time = Column(Time, nullable=False)
    consultation_type = Column(String(20))  # Online, In person
    
    # Vital Signs
    bp = Column(String(10))
    pulse = Column(Integer)
    height = Column(Numeric(5, 2))
    weight = Column(Numeric(5, 2))
    temperature = Column(Numeric(4, 1))
    bmi = Column(Numeric(4, 1))
    waist_hip = Column(String(10))
    spo2 = Column(Integer)
    
    # Consultation Notes
    complaints = Column(Text)
    diagnosis = Column(Text)
    treatment_advise = Column(Text)
    tests_requested = Column(Text)
    next_visit_days = Column(Integer)
    next_visit_date = Column(Date)
    investigations = Column(Text)
    
    # Referral Information
    referred_to_doctor = Column(String(100))
    referred_speciality = Column(String(50))
    referred_phone_no = Column(String(15))
    
    # Follow-up History
    follow_up = Column(JSONB)
    
    # Relationships
    appointment = relationship("Appointment", back_populates="consultation")
    patient = relationship("Patient")
    doctor = relationship("Staff", foreign_keys=[doctor_id])
    prescribed_medicines = relationship("PrescribedMedicine", back_populates="consultation")
PrescribedMedicine
pythonclass PrescribedMedicine(Base, TimestampMixin, TenantMixin):
    """Medicines prescribed during consultation"""
    __tablename__ = 'prescribed_medicines'
    
    prescription_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    consultation_id = Column(UUID(as_uuid=True), ForeignKey('consultations.consultation_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'), nullable=False)
    
    # Dosage Information
    frequency = Column(String(50))
    dosage = Column(String(20))
    morning = Column(Boolean, default=False)
    afternoon = Column(Boolean, default=False)
    evening = Column(Boolean, default=False)
    every = Column(String(20))  # Every X hours
    duration = Column(Integer)  # Number of days
    instruction = Column(Text)
    
    # Relationships
    consultation = relationship("Consultation", back_populates="prescribed_medicines")
    patient = relationship("Patient")
    medicine = relationship("Medicine")
InvoiceHeader
pythonclass InvoiceHeader(Base, TimestampMixin, TenantMixin):
    """Invoice header information"""
    __tablename__ = 'invoice_header'
    
    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    
    # Invoice Details
    invoice_number = Column(String(50), nullable=False, unique=True)  # Formatted tax invoice number
    invoice_date = Column(Date, nullable=False)
    invoice_type = Column(String(50), nullable=False)  # Service, Cosmetic Products, Prescription, Misc
    
    # Customer Information
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey('appointments.appointment_id'))
    
    # GST Information
    place_of_supply = Column(String(2))  # State code
    reverse_charge = Column(Boolean, default=False)
    e_invoice_irn = Column(String(100))  # E-invoice reference number
    is_interstate = Column(Boolean, default=False)
    
    # Amounts
    total_amount = Column(Numeric(10, 2), nullable=False)  # Gross total
    total_discount = Column(Numeric(10, 2), default=0)  # Total discount
    total_taxable_value = Column(Numeric(10, 2))  # Pre-tax amount
    total_cgst_amount = Column(Numeric(10, 2), default=0)
    total_sgst_amount = Column(Numeric(10, 2), default=0)
    total_igst_amount = Column(Numeric(10, 2), default=0)
    grand_total = Column(Numeric(10, 2), nullable=False)  # Final amount with tax
    
    # Payment Status
    paid_amount = Column(Numeric(10, 2), default=0)
    balance_due = Column(Numeric(10, 2))  # Calculated
    
    # Additional Information
    reference_invoice = Column(String(50))  # For debit/credit notes
    notes = Column(Text)
    created_by = Column(String(50))
    
    # Relationships
    patient = relationship("Patient")
    appointment = relationship("Appointment")
    line_items = relationship("InvoiceLineItem", back_populates="invoice")
    payments = relationship("PaymentDetail", back_populates="invoice")
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
    batch = Column(String(20))  # For medicines
    expiry_date = Column(Date)  # For medicines
    
    # Quantities and Amounts
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_percent = Column(Numeric(5, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    taxable_amount = Column(Numeric(10, 2))  # Amount before tax
    
    # GST Details
    gst_rate = Column(Numeric(5, 2))
    cgst_rate = Column(Numeric(5, 2))
    sgst_rate = Column(Numeric(5, 2))
    igst_rate = Column(Numeric(5, 2))
    cgst_amount = Column(Numeric(10, 2), default=0)
    sgst_amount = Column(Numeric(10, 2), default=0)
    igst_amount = Column(Numeric(10, 2), default=0)
    total_gst_amount = Column(Numeric(10, 2), default=0)
    
    # Line Total
    line_total = Column(Numeric(10, 2), nullable=False)  # Including tax
    
    # Relationships
    invoice = relationship("InvoiceHeader", back_populates="line_items")
    package = relationship("Package")
    service = relationship("Service")
    medicine = relationship("Medicine")
PaymentDetail
pythonclass PaymentDetail(Base, TimestampMixin, TenantMixin):
    """Payment details for invoices"""
    __tablename__ = 'payment_details'
    
    payment_id = Column(UUID(as_uuid=True),RetryClaude hit the max length for a message and has paused its response. You can write Continue to keep the chat going.VKcontinueEditLet me continue with the transaction tables:
PaymentDetail (continued)
pythonclass PaymentDetail(Base, TimestampMixin, TenantMixin):
    """Payment details for invoices"""
    __tablename__ = 'payment_details'
    
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'), nullable=False)
    
    # Payment Information
    payment_date = Column(DateTime(timezone=True), nullable=False)
    
    # Payment Methods
    cash_amount = Column(Numeric(10, 2), default=0)
    credit_card_amount = Column(Numeric(10, 2), default=0)
    debit_card_amount = Column(Numeric(10, 2), default=0)
    upi_amount = Column(Numeric(10, 2), default=0)
    
    # Payment Details
    card_number_last4 = Column(String(4))
    card_type = Column(String(20))
    upi_id = Column(String(50))
    reference_number = Column(String(50))
    
    # Totals
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Refund Information
    refunded_amount = Column(Numeric(10, 2), default=0)
    refund_date = Column(DateTime(timezone=True))
    refund_reason = Column(String(255))
    
    # GL Reference
    gl_entry_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # Relationships
    invoice = relationship("InvoiceHeader", back_populates="payments")
    gl_entry = relationship("GLTransaction")
PurchaseOrderHeader
pythonclass PurchaseOrderHeader(Base, TimestampMixin, TenantMixin):
    """Purchase order header"""
    __tablename__ = 'purchase_order_header'
    
    po_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    po_number = Column(String(20), nullable=False, unique=True)
    po_date = Column(Date, nullable=False)
    
    # Supplier Information
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    
    # Reference Information
    quotation_id = Column(String(50))
    quotation_date = Column(Date)
    
    # Delivery Information
    expected_delivery_date = Column(Date)
    
    # Status
    status = Column(String(20), default='draft')  # draft, approved, received, cancelled
    deleted_flag = Column(Boolean, default=False)
    
    # Approval Information
    approved_by = Column(String(50))
    created_by = Column(String(50))
    
    # Amounts
    total_amount = Column(Numeric(10, 2))
    
    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    line_items = relationship("PurchaseOrderLine", back_populates="po_header")
    supplier_invoices = relationship("SupplierInvoice", back_populates="po_header")
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
    units = Column(Integer, nullable=False)  # Quantity ordered
    pack_purchase_price = Column(Numeric(10, 2), nullable=False)  # Price per pack
    pack_mrp = Column(Numeric(10, 2), nullable=False)  # MRP per pack
    units_per_pack = Column(Integer, nullable=False)  # Units in each pack
    unit_price = Column(Numeric(10, 2))  # Derived unit price
    
    # GST Information
    hsn_code = Column(String(10))
    gst_rate = Column(Numeric(5, 2))
    cgst_rate = Column(Numeric(5, 2))
    sgst_rate = Column(Numeric(5, 2))
    igst_rate = Column(Numeric(5, 2))
    cgst = Column(Numeric(10, 2), default=0)
    sgst = Column(Numeric(10, 2), default=0)
    igst = Column(Numeric(10, 2), default=0)
    total_gst = Column(Numeric(10, 2), default=0)
    
    # Delivery
    expected_delivery_date = Column(Date)
    
    # Relationships
    po_header = relationship("PurchaseOrderHeader", back_populates="line_items")
    medicine = relationship("Medicine")
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
    invoice_date = Column(Date, nullable=False)
    
    # GST Information
    supplier_gstin = Column(String(15))
    place_of_supply = Column(String(2))  # State code
    reverse_charge = Column(Boolean, default=False)
    
    # GST Amounts
    cgst_amount = Column(Numeric(10, 2), default=0)
    sgst_amount = Column(Numeric(10, 2), default=0)
    igst_amount = Column(Numeric(10, 2), default=0)
    total_gst_amount = Column(Numeric(10, 2), default=0)
    
    # Invoice Amounts
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # ITC Eligibility
    itc_eligible = Column(Boolean, default=True)
    
    # Payment Information
    payment_status = Column(String(20), default='unpaid')  # unpaid, partial, paid
    due_date = Column(Date)
    
    # Creation Info
    created_by = Column(String(50))
    
    # Relationships
    po_header = relationship("PurchaseOrderHeader", back_populates="supplier_invoices")
    supplier = relationship("Supplier", back_populates="invoices")
    line_items = relationship("SupplierInvoiceLine", back_populates="invoice")
    payments = relationship("SupplierPayment", back_populates="invoice")
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
    units = Column(Integer, nullable=False)  # Quantity received
    pack_purchase_price = Column(Numeric(10, 2), nullable=False)  # Price per pack
    pack_mrp = Column(Numeric(10, 2), nullable=False)  # MRP per pack
    units_per_pack = Column(Integer, nullable=False)  # Units in each pack
    unit_price = Column(Numeric(10, 2))  # Derived unit price
    
    # Taxable Amount
    taxable_amount = Column(Numeric(10, 2))
    
    # GST Information
    hsn_code = Column(String(10))
    gst_rate = Column(Numeric(5, 2))
    cgst_rate = Column(Numeric(5, 2))
    sgst_rate = Column(Numeric(5, 2))
    igst_rate = Column(Numeric(5, 2))
    cgst = Column(Numeric(10, 2), default=0)
    sgst = Column(Numeric(10, 2), default=0)
    igst = Column(Numeric(10, 2), default=0)
    total_gst = Column(Numeric(10, 2), default=0)
    
    # Batch Information
    batch_number = Column(String(20))
    manufacturing_date = Column(Date)
    expiry_date = Column(Date)
    
    # ITC Eligibility
    itc_eligible = Column(Boolean, default=True)
    
    # Relationships
    invoice = relationship("SupplierInvoice", back_populates="line_items")
    medicine = relationship("Medicine")
SupplierPayment
pythonclass SupplierPayment(Base, TimestampMixin, TenantMixin):
    """Payments to suppliers"""
    __tablename__ = 'supplier_payment'
    
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'))
    
    # Payment Details
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String(20))
    amount = Column(Numeric(10, 2), nullable=False)
    reference_no = Column(String(50))
    status = Column(String(20), default='completed')
    notes = Column(String(255))
    
    # GL Reference
    gl_entry_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # Creation Info
    created_by = Column(String(50))
    
    # Relationships
    supplier = relationship("Supplier")
    invoice = relationship("SupplierInvoice", back_populates="payments")
    gl_entry = relationship("GLTransaction")
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
    po_no = Column(UUID(as_uuid=True), ForeignKey('purchase_order_header.po_id'))
    bill_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'))
    
    # Item Details
    medicine_name = Column(String(100), nullable=False)
    medicine_category = Column(String(50))
    batch = Column(String(20), nullable=False)
    expiry = Column(Date, nullable=False)
    
    # Pricing Information
    pack_purchase_price = Column(Numeric(10, 2))
    pack_mrp = Column(Numeric(10, 2))
    units_per_pack = Column(Integer)
    unit_price = Column(Numeric(10, 2))  # Derived
    sale_price = Column(Numeric(10, 2))
    
    # Transaction Details
    units = Column(Integer, nullable=False)  # Quantity in/out
    percent_discount = Column(Numeric(5, 2), default=0)
    
    # GST Information
    cgst = Column(Numeric(10, 2), default=0)
    sgst = Column(Numeric(10, 2), default=0)
    igst = Column(Numeric(10, 2), default=0)
    total_gst = Column(Numeric(10, 2), default=0)
    
    # Additional Information
    reason = Column(String(255))  # For adjustments
    current_stock = Column(Integer)  # Running balance
    location = Column(String(50))
    stock_status = Column(String(20))
    
    # Dates
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    medicine = relationship("Medicine", back_populates="inventory_entries")
    purchase_order = relationship("PurchaseOrderHeader")
    invoice = relationship("InvoiceHeader")
    patient = relationship("Patient")
GLTransaction
pythonclass GLTransaction(Base, TimestampMixin, TenantMixin):
    """General Ledger Transactions"""
    __tablename__ = 'gl_transaction'
    
    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    
    # Transaction Details
    transaction_date = Column(Date, nullable=False)
    transaction_type = Column(String(50), nullable=False)
    reference_id = Column(String(50))  # Invoice ID, PO ID, etc.
    description = Column(String(255))
    
    # Transaction Totals
    total_debit = Column(Numeric(12, 2), nullable=False)
    total_credit = Column(Numeric(12, 2), nullable=False)
    
    # Creation Info
    created_by = Column(String(50))
    
    # Relationships
    entries = relationship("GLEntry", back_populates="transaction")
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
    entry_date = Column(Date, nullable=False)
    description = Column(String(255))
    
    # Creation Info
    created_by = Column(String(50))
    
    # Relationships
    transaction = relationship("GLTransaction", back_populates="entries")
    account = relationship("ChartOfAccounts", back_populates="gl_entries")
GSTLedger
pythonclass GSTLedger(Base, TimestampMixin, TenantMixin):
    """GST Input/Output Tracking"""
    __tablename__ = 'gst_ledger'
    
    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    
    # Transaction Details
    transaction_date = Column(Date, nullable=False)
    transaction_type = Column(String(30), nullable=False)  # Sales/Purchase/Adjustment
    transaction_reference = Column(String(50))  # Invoice/Bill reference
    
    # GST Amounts
    cgst_output = Column(Numeric(10, 2), default=0)  # CGST collected on sales
    sgst_output = Column(Numeric(10, 2), default=0)  # SGST collected on sales
    igst_output = Column(Numeric(10, 2), default=0)  # IGST collected on sales
    cgst_input = Column(Numeric(10, 2), default=0)   # CGST paid on purchases
    sgst_input = Column(Numeric(10, 2), default=0)   # SGST paid on purchases
    igst_input = Column(Numeric(10, 2), default=0)   # IGST paid on purchases
    
    # GL Reference
    gl_reference = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # Reporting Period
    entry_month = Column(Integer)  # Month for reporting
    entry_year = Column(Integer)   # Year for reporting
    
    # Relationships
    gl_transaction = relationship("GLTransaction")
Business Rules
Here are the key business rules for implementing the data model and processes:
1. GST Calculation and Management

Interstate vs Intrastate GST Application:
pythondef calculate_gst(base_amount, gst_rate, is_interstate):
    """Calculate GST components based on supply type"""
    if is_interstate:
        # Interstate: Apply full rate to IGST only
        return {
            'cgst_amount': 0,
            'sgst_amount': 0,
            'igst_amount': base_amount * (gst_rate / 100),
            'total_gst': base_amount * (gst_rate / 100)
        }
    else:
        # Intrastate: Split rate between CGST and SGST
        half_rate = gst_rate / 2
        cgst = base_amount * (half_rate / 100)
        sgst = base_amount * (half_rate / 100)
        return {
            'cgst_amount': cgst,
            'sgst_amount': sgst,
            'igst_amount': 0,
            'total_gst': cgst + sgst
        }

Invoice Numbering Format:
pythondef generate_invoice_number(hospital_id, financial_year):
    """Generate GST-compliant invoice number"""
    # Get the last invoice number for this FY
    with get_db_session() as session:
        last_invoice = session.query(InvoiceHeader)\
            .filter(InvoiceHeader.hospital_id == hospital_id)\
            .filter(InvoiceHeader.invoice_number.like(f"INV/{financial_year}/%"))\
            .order_by(InvoiceHeader.invoice_number.desc())\
            .first()
        
    if last_invoice:
        # Extract the sequence number and increment
        last_seq = int(last_invoice.invoice_number.split('/')[-1])
        next_seq = last_seq + 1
    else:
        # First invoice of the FY
        next_seq = 1
        
    return f"INV/{financial_year}/{next_seq:04d}"

Input Tax Credit Eligibility:
pythondef determine_itc_eligibility(supplier_invoice):
    """Determine if invoice is eligible for ITC"""
    # Check if supplier is GST registered
    if not supplier_invoice.supplier_gstin:
        return False
        
    # Check if our hospital is GST registered
    with get_db_session() as session:
        hospital = session.query(Hospital).get(supplier_invoice.hospital_id)
        if not hospital.gst_registration_number:
            return False
            
    # Check for valid tax invoice
    if not supplier_invoice.supplier_invoice_number:
        return False
        
    # Return true if all conditions met
    return True


2. Inventory Management

Stock Updating on Purchase Receipt:
pythondef receive_inventory(supplier_invoice_id):
    """Update inventory based on supplier invoice"""
    with get_db_session() as session:
        # Get invoice and line items
        invoice = session.query(SupplierInvoice).get(supplier_invoice_id)
        line_items = session.query(SupplierInvoiceLine)\
            .filter_by(invoice_id=supplier_invoice_id)\
            .all()
            
        for item in line_items:
            # Create inventory entry
            inventory_entry = Inventory(
                hospital_id=invoice.hospital_id,
                stock_type='Purchase',
                medicine_id=item.medicine_id,
                medicine_name=item.medicine_name,
                distributor_invoice_no=invoice.supplier_invoice_number,
                po_no=invoice.po_id,
                batch=item.batch_number,
                expiry=item.expiry_date,
                pack_purchase_price=item.pack_purchase_price,
                pack_mrp=item.pack_mrp,
                units_per_pack=item.units_per_pack,
                unit_price=item.unit_price,
                units=item.units,
                cgst=item.cgst,
                sgst=item.sgst,
                igst=item.igst,
                total_gst=item.total_gst,
                transaction_date=datetime.now(timezone.utc)
            )
            session.add(inventory_entry)
            
            # Update medicine current stock (aggregate query)
            medicine = session.query(Medicine).get(item.medicine_id)
            if medicine:
                # Update current stock with a query to get accurate aggregate
                current_stock = session.query(func.sum(Inventory.units))\
                    .filter(Inventory.medicine_id == item.medicine_id)\
                    .scalar() or 0
                medicine.current_stock = current_stock

Stock Deduction on Sales:
pythondef process_sale(invoice_id):
    """Update inventory based on sales invoice"""
    with get_db_session() as session:
        # Get invoice and line items
        invoice = session.query(InvoiceHeader).get(invoice_id)
        line_items = session.query(InvoiceLineItem)\
            .filter_by(invoice_id=invoice_id)\
            .filter_by(item_type='Medicine')\
            .all()
            
        for item in line_items:
            if item.medicine_id:
                # Find best batch to use (FIFO)
                batch = get_oldest_valid_batch(item.medicine_id, item.quantity)
                
                # Create inventory entry
                inventory_entry = Inventory(
                    hospital_id=invoice.hospital_id,
                    stock_type='Sale',
                    medicine_id=item.medicine_id,
                    medicine_name=item.item_name,
                    bill_id=invoice.invoice_id,
                    patient_id=invoice.patient_id,
                    batch=batch.batch,
                    expiry=batch.expiry,
                    sale_price=item.unit_price,
                    units=-item.quantity,  # Negative for outgoing
                    cgst=item.cgst_amount,
                    sgst=item.sgst_amount,
                    igst=item.igst_amount,
                    total_gst=item.total_gst_amount,
                    transaction_date=datetime.now(timezone.utc)
                )
                session.add(inventory_entry)
                
                # Update medicine current stock
                medicine = session.query(Medicine).get(item.medicine_id)
                if medicine:
                    # Update with aggregate query
                    current_stock = session.query(func.sum(Inventory.units))\
                        .filter(Inventory.medicine_id == item.medicine_id)\
                        .scalar() or 0
                    medicine.current_stock = current_stock


3. Accounting Integration

GL Entries for Sales:
pythondef create_sales_gl_entries(invoice_id):
    """Create GL entries for sales invoice"""
    with get_db_session() as session:
        invoice = session.query(InvoiceHeader).get(invoice_id)
        
        # Create GL Transaction
        gl_tx = GLTransaction(
            hospital_id=invoice.hospital_id,
            transaction_date=invoice.invoice_date,
            transaction_type='Sales',
            reference_id=invoice.invoice_number,
            description=f"Sales Invoice {invoice.invoice_number}",
            total_debit=invoice.grand_total,
            total_credit=invoice.grand_total,
            created_by=invoice.created_by
        )
        session.add(gl_tx)
        session.flush()
        
        # Create GL Entries
        
        # 1. Debit Patient/Accounts Receivable
        debit_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_accounts_receivable_id(),  # Function to get the right account
            debit_amount=invoice.grand_total,
            credit_amount=0,
            entry_date=invoice.invoice_date,
            description=f"Sales Invoice {invoice.invoice_number}",
            created_by=invoice.created_by
        )
        session.add(debit_entry)
        
        # 2. Credit Sales/Income accounts
        sales_credit = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_sales_income_id(),  # Function to get the right account
            debit_amount=0,
            credit_amount=invoice.total_taxable_value,
            entry_date=invoice.invoice_date,
            description=f"Sales Invoice {invoice.invoice_number}",
            created_by=invoice.created_by
        )
        session.add(sales_credit)
        
        # 3. Credit GST Liability accounts
        if invoice.total_cgst_amount > 0:
            cgst_credit = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_tx.transaction_id,
                account_id=get_cgst_output_id(),  # Function to get CGST account
                debit_amount=0,
                credit_amount=invoice.total_cgst_amount,
                entry_date=invoice.invoice_date,
                description=f"CGST on Invoice {invoice.invoice_number}",
                created_by=invoice.created_by
            )
            session.add(cgst_credit)
            
        if invoice.total_sgst_amount > 0:
            sgst_credit = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_tx.transaction_id,
                account_id=get_sgst_output_id(),  # Function to get SGST account
                debit_amount=0,
                credit_amount=invoice.total_sgst_amount,
                entry_date=invoice.invoice_date,
                description=f"SGST on Invoice {invoice.invoice_number}",
                created_by=invoice.created_by
            )
            session.add(sgst_credit)
            
        if invoice.total_igst_amount > 0:
            igst_credit = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_tx.transaction_id,
                account_id=get_igst_output_id(),  # Function to get IGST account
                debit_amount=0,
                credit_amount=invoice.total_igst_amount,
                entry_date=invoice.invoice_date,
                description=f"IGST on Invoice {invoice.invoice_number}",
                created_by=invoice.created_by
            )
            session.add(igst_credit)
            
        # Create GST Ledger entry
        gst_entry = GSTLedger(
            hospital_id=invoice.hospital_id,
            transaction_date=invoice.invoice_date,
            transaction_type='Sales',
            transaction_reference=invoice.invoice_number,
            cgst_output=invoice.total_cgst_amount,
            sgst_output=invoice.total_sgst_amount,
            igst_output=invoice.total_igst_amount,
            gl_reference=gl_tx.transaction_id,
            entry_month=invoice.invoice_date.month,
            entry_year=invoice.invoice_date.year
        )
        session.add(gst_entry)

Purchase Invoice Accounting:
pythondef create_purchase_gl_entries(supplier_invoice_id):
    """Create GL entries for purchase invoice"""
    with get_db_session() as session:
        invoice = session.query(SupplierInvoice).get(supplier_invoice_id)
        
        # Create GL Transaction
        gl_tx = GLTransaction(
            hospital_id=invoice.hospital_id,
            transaction_date=invoice.invoice_date,
            transaction_type='Purchase',
            reference_id=invoice.supplier_invoice_number,
            description=f"Purchase Invoice {invoice.supplier_invoice_number}",
            total_debit=invoice.total_amount,
            total_credit=invoice.total_amount,
            created_by=invoice.created_by
        )
        session.add(gl_tx)
        session.flush()
        
        # Calculate taxable amount (total - GST)
        taxable_amount = invoice.total_amount - invoice.total_gst_amount
        
        # Create GL Entries
        
        # 1. Debit Purchases/Inventory
        debit_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_purchases_account_id(),  # Function to get the right account
            debit_amount=taxable_amount,
            credit_amount=0,
            entry_date=invoice.invoice_date,
            description=f"Purchase Invoice {invoice.supplier_invoice_number}",
            created_by=invoice.created_by
        )
        session.add(debit_entry)
        
        # 2. Debit GST Input accounts (if ITC eligible)
        if invoice.itc_eligible:
            if invoice.cgst_amount > 0:

RetryClaude hit the max length for a message and has paused its response. You can write Continue to keep the chat going.VKcontinueEditLet me continue with the business rules for accounting integration:
python# 2. Debit GST Input accounts (if ITC eligible)
if invoice.itc_eligible:
    if invoice.cgst_amount > 0:
        cgst_debit = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_cgst_input_id(),  # Function to get CGST input account
            debit_amount=invoice.cgst_amount,
            credit_amount=0,
            entry_date=invoice.invoice_date,
            description=f"CGST on Purchase Invoice {invoice.supplier_invoice_number}",
            created_by=invoice.created_by
        )
        session.add(cgst_debit)
        
    if invoice.sgst_amount > 0:
        sgst_debit = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_sgst_input_id(),  # Function to get SGST input account
            debit_amount=invoice.sgst_amount,
            credit_amount=0,
            entry_date=invoice.invoice_date,
            description=f"SGST on Purchase Invoice {invoice.supplier_invoice_number}",
            created_by=invoice.created_by
        )
        session.add(sgst_debit)
        
    if invoice.igst_amount > 0:
        igst_debit = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_igst_input_id(),  # Function to get IGST input account
            debit_amount=invoice.igst_amount,
            credit_amount=0,
            entry_date=invoice.invoice_date,
            description=f"IGST on Purchase Invoice {invoice.supplier_invoice_number}",
            created_by=invoice.created_by
        )
        session.add(igst_debit)
        
# 3. Credit Supplier/Accounts Payable
credit_entry = GLEntry(
    hospital_id=invoice.hospital_id,
    transaction_id=gl_tx.transaction_id,
    account_id=get_accounts_payable_id(),  # Function to get AP account
    debit_amount=0,
    credit_amount=invoice.total_amount,
    entry_date=invoice.invoice_date,
    description=f"Purchase Invoice {invoice.supplier_invoice_number}",
    created_by=invoice.created_by
)
session.add(credit_entry)

# Create GST Ledger entry
gst_entry = GSTLedger(
    hospital_id=invoice.hospital_id,
    transaction_date=invoice.invoice_date,
    transaction_type='Purchase',
    transaction_reference=invoice.supplier_invoice_number,
    cgst_input=invoice.cgst_amount if invoice.itc_eligible else 0,
    sgst_input=invoice.sgst_amount if invoice.itc_eligible else 0,
    igst_input=invoice.igst_amount if invoice.itc_eligible else 0,
    gl_reference=gl_tx.transaction_id,
    entry_month=invoice.invoice_date.month,
    entry_year=invoice.invoice_date.year
)
session.add(gst_entry)
4. Payment Processing Rules

Customer Payment Processing:

pythondef process_customer_payment(invoice_id, payment_details):
    """Process customer payment for invoice"""
    with get_db_session() as session:
        invoice = session.query(InvoiceHeader).get(invoice_id)
        
        # Calculate payment amount
        total_payment = (
            payment_details.get('cash_amount', 0) +
            payment_details.get('credit_card_amount', 0) +
            payment_details.get('debit_card_amount', 0) +
            payment_details.get('upi_amount', 0)
        )
        
        # Verify payment doesn't exceed remaining balance
        if total_payment > invoice.balance_due:
            raise ValueError(f"Payment amount {total_payment} exceeds remaining balance {invoice.balance_due}")
        
        # Create payment record
        payment = PaymentDetail(
            hospital_id=invoice.hospital_id,
            invoice_id=invoice_id,
            payment_date=datetime.now(timezone.utc),
            cash_amount=payment_details.get('cash_amount', 0),
            credit_card_amount=payment_details.get('credit_card_amount', 0),
            debit_card_amount=payment_details.get('debit_card_amount', 0),
            upi_amount=payment_details.get('upi_amount', 0),
            card_number_last4=payment_details.get('card_number_last4'),
            card_type=payment_details.get('card_type'),
            upi_id=payment_details.get('upi_id'),
            reference_number=payment_details.get('reference_number'),
            total_amount=total_payment,
            created_by=payment_details.get('created_by')
        )
        session.add(payment)
        session.flush()
        
        # Update invoice paid amount and balance
        invoice.paid_amount += total_payment
        invoice.balance_due -= total_payment
        
        # Create GL Entry for payment
        gl_tx = GLTransaction(
            hospital_id=invoice.hospital_id,
            transaction_date=payment.payment_date.date(),
            transaction_type='Receipt',
            reference_id=payment.payment_id,
            description=f"Payment for Invoice {invoice.invoice_number}",
            total_debit=total_payment,
            total_credit=total_payment,
            created_by=payment_details.get('created_by')
        )
        session.add(gl_tx)
        session.flush()
        
        # Set GL reference in payment
        payment.gl_entry_id = gl_tx.transaction_id
        
        # Create GL entries
        
        # 1. Debit Cash/Bank account
        debit_account_id = None
        if payment.cash_amount > 0:
            debit_account_id = get_cash_account_id()
        elif payment.credit_card_amount > 0 or payment.debit_card_amount > 0:
            debit_account_id = get_bank_account_id()
        elif payment.upi_amount > 0:
            debit_account_id = get_digital_wallet_account_id()
        
        if debit_account_id:
            debit_entry = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_tx.transaction_id,
                account_id=debit_account_id,
                debit_amount=total_payment,
                credit_amount=0,
                entry_date=payment.payment_date.date(),
                description=f"Payment for Invoice {invoice.invoice_number}",
                created_by=payment_details.get('created_by')
            )
            session.add(debit_entry)
        
        # 2. Credit Accounts Receivable
        credit_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_accounts_receivable_id(),
            debit_amount=0,
            credit_amount=total_payment,
            entry_date=payment.payment_date.date(),
            description=f"Payment for Invoice {invoice.invoice_number}",
            created_by=payment_details.get('created_by')
        )
        session.add(credit_entry)
        
        return payment

Supplier Payment Processing:

pythondef process_supplier_payment(supplier_invoice_id, payment_details):
    """Process payment to supplier for invoice"""
    with get_db_session() as session:
        invoice = session.query(SupplierInvoice).get(supplier_invoice_id)
        
        # Calculate payment amount
        payment_amount = payment_details.get('amount', 0)
        
        # Create supplier payment record
        payment = SupplierPayment(
            hospital_id=invoice.hospital_id,
            supplier_id=invoice.supplier_id,
            invoice_id=supplier_invoice_id,
            payment_date=datetime.now(timezone.utc).date(),
            payment_method=payment_details.get('payment_method'),
            amount=payment_amount,
            reference_no=payment_details.get('reference_no'),
            notes=payment_details.get('notes'),
            created_by=payment_details.get('created_by')
        )
        session.add(payment)
        session.flush()
        
        # Update invoice payment status
        paid_total = session.query(func.sum(SupplierPayment.amount))\
            .filter_by(invoice_id=supplier_invoice_id)\
            .scalar() or 0
            
        if paid_total >= invoice.total_amount:
            invoice.payment_status = 'paid'
        elif paid_total > 0:
            invoice.payment_status = 'partial'
        
        # Create GL Entry
        gl_tx = GLTransaction(
            hospital_id=invoice.hospital_id,
            transaction_date=payment.payment_date,
            transaction_type='Payment',
            reference_id=payment.payment_id,
            description=f"Payment to {invoice.supplier.supplier_name} for Invoice {invoice.supplier_invoice_number}",
            total_debit=payment_amount,
            total_credit=payment_amount,
            created_by=payment_details.get('created_by')
        )
        session.add(gl_tx)
        session.flush()
        
        # Set GL reference in payment
        payment.gl_entry_id = gl_tx.transaction_id
        
        # Create GL entries
        
        # 1. Debit Accounts Payable
        debit_entry = GLEntry(
            hospital_id=invoice.hospital_id,
            transaction_id=gl_tx.transaction_id,
            account_id=get_accounts_payable_id(),
            debit_amount=payment_amount,
            credit_amount=0,
            entry_date=payment.payment_date,
            description=f"Payment for Invoice {invoice.supplier_invoice_number}",
            created_by=payment_details.get('created_by')
        )
        session.add(debit_entry)
        
        # 2. Credit Cash/Bank account based on payment method
        credit_account_id = None
        if payment.payment_method == 'Cash':
            credit_account_id = get_cash_account_id()
        elif payment.payment_method in ['Bank Transfer', 'Check']:
            credit_account_id = get_bank_account_id()
        elif payment.payment_method == 'UPI':
            credit_account_id = get_digital_wallet_account_id()
        
        if credit_account_id:
            credit_entry = GLEntry(
                hospital_id=invoice.hospital_id,
                transaction_id=gl_tx.transaction_id,
                account_id=credit_account_id,
                debit_amount=0,
                credit_amount=payment_amount,
                entry_date=payment.payment_date,
                description=f"Payment for Invoice {invoice.supplier_invoice_number}",
                created_by=payment_details.get('created_by')
            )
            session.add(credit_entry)
        
        return payment
5. GST Return Preparation
pythondef prepare_gstr1_data(hospital_id, month, year):
    """Prepare data for GSTR-1 filing"""
    with get_db_session(read_only=True) as session:
        # Get hospital details
        hospital = session.query(Hospital).get(hospital_id)
        
        # Get all sales invoices for the period
        invoices = session.query(InvoiceHeader)\
            .filter(InvoiceHeader.hospital_id == hospital_id)\
            .filter(extract('month', InvoiceHeader.invoice_date) == month)\
            .filter(extract('year', InvoiceHeader.invoice_date) == year)\
            .all()
            
        # Initialize return data
        return_data = {
            'gstin': hospital.gst_registration_number,
            'return_period': f"{month}-{year}",
            'b2b_invoices': [],
            'b2c_invoices': [],
            'hsn_summary': {}
        }
        
        for invoice in invoices:
            # Check if B2B or B2C
            # For a clinic, most transactions would be B2C unless the patient provides a GSTIN
            # This would require having a GSTIN field in Patient model or InvoiceHeader
            
            # For demonstration, assuming all are B2C
            invoice_data = {
                'invoice_number': invoice.invoice_number,
                'invoice_date': invoice.invoice_date.strftime('%d-%m-%Y'),
                'invoice_value': float(invoice.grand_total),
                'place_of_supply': invoice.place_of_supply,
                'rate': 0,  # Will be updated from line items
                'taxable_value': float(invoice.total_taxable_value),
                'igst': float(invoice.total_igst_amount),
                'cgst': float(invoice.total_cgst_amount),
                'sgst': float(invoice.total_sgst_amount)
            }
            
            return_data['b2c_invoices'].append(invoice_data)
            
            # Process HSN summary
            line_items = session.query(InvoiceLineItem)\
                .filter_by(invoice_id=invoice.invoice_id)\
                .all()
                
            for item in line_items:
                hsn_code = item.hsn_sac_code or 'NA'
                
                if hsn_code not in return_data['hsn_summary']:
                    return_data['hsn_summary'][hsn_code] = {
                        'hsn_code': hsn_code,
                        'description': '',
                        'uqc': 'NOS',  # Unit of Quantity Code
                        'total_quantity': 0,
                        'total_value': 0,
                        'taxable_value': 0,
                        'igst': 0,
                        'cgst': 0,
                        'sgst': 0
                    }
                    
                # Update HSN summary
                return_data['hsn_summary'][hsn_code]['total_quantity'] += item.quantity
                return_data['hsn_summary'][hsn_code]['total_value'] += float(item.line_total)
                return_data['hsn_summary'][hsn_code]['taxable_value'] += float(item.taxable_amount)
                return_data['hsn_summary'][hsn_code]['igst'] += float(item.igst_amount)
                return_data['hsn_summary'][hsn_code]['cgst'] += float(item.cgst_amount)
                return_data['hsn_summary'][hsn_code]['sgst'] += float(item.sgst_amount)
        
        # Convert HSN summary to list
        return_data['hsn_summary'] = list(return_data['hsn_summary'].values())
        
        return return_data
6. Maximum Discount Enforcement
pythondef validate_discount(item_id, item_type, discount_percent):
    """Validate that discount doesn't exceed maximum allowed"""
    with get_db_session(read_only=True) as session:
        max_discount = None
        
        if item_type == 'Service':
            service = session.query(Service).get(item_id)
            if service:
                max_discount = service.max_discount
        elif item_type == 'Package':
            package = session.query(Package).get(item_id)
            if package:
                max_discount = package.max_discount
        elif item_type == 'Medicine':
            # Medicines may not have max_discount field, so this is optional
            medicine = session.query(Medicine).get(item_id)
            if medicine and hasattr(medicine, 'max_discount'):
                max_discount = medicine.max_discount
        
        # If max_discount is defined and discount exceeds it, return error
        if max_discount is not None and discount_percent > max_discount:
            return False, f"Discount {discount_percent}% exceeds maximum allowed {max_discount}%"
            
        return True, "Discount is valid"
Conclusion
This comprehensive data model has been designed to efficiently handle the core business processes of SkinSpire Clinic HMS, with special attention to:

GST Compliance: Proper separation of CGST, SGST, and IGST for accurate tax handling and reporting
Inventory Management: Detailed batch tracking, expiry monitoring, and correct stock movement records
Service & Package Management: Flexible service and package hierarchy with proper owner assignment and discount controls
Financial Integration: Complete double-entry accounting with proper GL entries for all transactions
Multi-Tenant Architecture: All tables include hospital_id for proper tenant isolation

The implementation follows best practices from your existing models, including:

Using appropriate SQLAlchemy features and PostgreSQL-specific types
Incorporating mixins for common functionality (TimestampMixin, TenantMixin, SoftDeleteMixin)
Organizing tables into appropriate categories (base, master, transaction)
Maintaining proper relationships between tables

The enhanced Patient model captures all the details from your consolidated structure document, plus additional fields needed for proper operation. The business rules provide a solid foundation for implementing the logic around GST calculations, inventory management, accounting integration, and more.
To begin implementation, I recommend starting with the master data tables, particularly focusing on Hospital, Branch, Patient, Service, Package, and Medicine models, as these form the foundation for all the transaction processes.