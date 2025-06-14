# app/models/master.py

from sqlalchemy import Column, String, ForeignKey, Boolean, Text, Numeric, Date, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .base import Base, TimestampMixin, TenantMixin, SoftDeleteMixin, generate_uuid

class Hospital(Base, TimestampMixin, SoftDeleteMixin):
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
    pharmacy_registration_number = Column(String(50))  # Pharmacy license number
    pharmacy_registration_date = Column(Date)  # Registration date
    pharmacy_registration_valid_until = Column(Date)  # Validity date
    
    # Added fields for business processes
    gst_registration_number = Column(String(15))  # GSTIN
    pan_number = Column(String(10))  # PAN
    state_code = Column(String(2))  # GST state code
    timezone = Column(String(50), default='Asia/Kolkata')  # For international operations
    default_currency = Column(String(3), default='INR')  # Default currency
    return_filing_period = Column(String(10))  # Monthly/Quarterly
    bank_account_details = Column(JSONB)  # Banking information for payments
    logo = Column(JSONB, nullable=True) # Logo to be stored at hospital level

    # Relationships
    branches = relationship("Branch", back_populates="hospital", cascade="all, delete-orphan")
    staff = relationship("Staff", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
    users = relationship("User", back_populates="hospital")
    roles = relationship("RoleMaster", back_populates="hospital")
    settings_records = relationship("HospitalSettings", back_populates="hospital")

class Branch(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Branch level configuration"""
    __tablename__ = 'branches'

    branch_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    name = Column(String(100), nullable=False)
    address = Column(JSONB)
    contact_details = Column(JSONB)
    settings = Column(JSONB)
    is_active = Column(Boolean, default=True)
    
    # Added fields for business processes
    gst_registration_number = Column(String(15))  # If different from hospital
    state_code = Column(String(2))  # Branch state code
    timezone = Column(String(50))  # Branch timezone, defaults to hospital

    # Added pharmacy registration fields (mirroring Hospital)
    pharmacy_registration_number = Column(String(50))  
    pharmacy_registration_date = Column(Date)  
    pharmacy_registration_valid_until = Column(Date)  
    pan_number = Column(String(10))  # PAN for branch if different
    return_filing_period = Column(String(10))  # Monthly/Quarterly if different from hospital

    # Relationships
    hospital = relationship("Hospital", back_populates="branches")
    staff = relationship("Staff", back_populates="branch")
    patients = relationship("Patient", back_populates="branch")

class Staff(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Staff member information"""
    __tablename__ = 'staff'

    staff_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    employee_code = Column(String(20), unique=True)
    title = Column(String(10))
    specialization = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))
    personal_info = Column(JSONB, nullable=False)  # name, dob, gender, etc.
    contact_info = Column(JSONB, nullable=False)   # email, phone, address
    professional_info = Column(JSONB)  # qualifications, certifications
    employment_info = Column(JSONB)    # join date, designation, etc.
    documents = Column(JSONB)          # ID proofs, certificates
    is_active = Column(Boolean, default=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="staff")
    branch = relationship("Branch", back_populates="staff")

    @hybrid_property
    def full_name(self):
        """Get full name from personal_info or dedicated fields"""
        # First try to use dedicated fields
        if self.first_name or self.last_name:
            name_parts = []
            if self.title:
                name_parts.append(self.title)
            if self.first_name:
                name_parts.append(self.first_name)
            if self.last_name:
                name_parts.append(self.last_name)
            return " ".join(name_parts)
        
        # Fall back to personal_info
        if isinstance(self.personal_info, dict):
            return f"{self.personal_info.get('first_name', '')} {self.personal_info.get('last_name', '')}"
        elif isinstance(self.personal_info, str):
            try:
                import json
                info = json.loads(self.personal_info)
                return f"{info.get('first_name', '')} {info.get('last_name', '')}"
            except:
                return ""
        return ""

    @full_name.expression
    def full_name(cls):
        """SQL expression for full name"""
        from sqlalchemy import func
        # For PostgreSQL, use the string concatenation with appropriate JSON extraction
        first_name = func.jsonb_extract_path_text(cls.personal_info, 'first_name')
        last_name = func.jsonb_extract_path_text(cls.personal_info, 'last_name')
        return func.concat(first_name, ' ', last_name)

class Patient(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Patient information"""
    __tablename__ = 'patients'

    patient_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    mrn = Column(String(20), unique=True)

    title = Column(String(10))
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))

    blood_group = Column(String(5))
    personal_info = Column(JSONB, nullable=False)  # name, dob, gender, marital status
    contact_info = Column(JSONB, nullable=False)   # email, phone, address
    medical_info = Column(Text)                    # Encrypted medical history
    emergency_contact = Column(JSONB)              # name, relation, contact
    documents = Column(JSONB)                      # ID proofs, previous records
    preferences = Column(JSONB)                    # language, communication preferences
    is_active = Column(Boolean, default=True)

    # Relationships
    hospital = relationship("Hospital", back_populates="patients")
    branch = relationship("Branch", back_populates="patients")

    @hybrid_property
    def full_name(self):
        """Get full name from personal_info"""
        if isinstance(self.personal_info, dict):
            return f"{self.personal_info.get('first_name', '')} {self.personal_info.get('last_name', '')}"
        elif isinstance(self.personal_info, str):
            try:
                import json
                info = json.loads(self.personal_info)
                return f"{info.get('first_name', '')} {info.get('last_name', '')}"
            except:
                return ""
        return ""

    @full_name.expression
    def full_name(cls):
        """SQL expression for full name"""
        from sqlalchemy import func
        # For PostgreSQL, use the string concatenation with appropriate JSON extraction
        first_name = func.jsonb_extract_path_text(cls.personal_info, 'first_name')
        last_name = func.jsonb_extract_path_text(cls.personal_info, 'last_name')
        return func.concat(first_name, ' ', last_name)

    @hybrid_property
    def full_name_computed(self):
        """Get full name prioritizing dedicated fields"""
        # First try to use dedicated fields
        if self.first_name or self.last_name:
            name_parts = []
            if self.title:
                name_parts.append(self.title)
            if self.first_name:
                name_parts.append(self.first_name)
            if self.last_name:
                name_parts.append(self.last_name)
            return " ".join(name_parts)
        
        # Fall back to personal_info
        return self.full_name_from_json
        
    @hybrid_property
    def full_name_from_json(self):
        """Legacy method to get name from JSON (for backward compatibility)"""
        if hasattr(self, 'personal_info') and self.personal_info:
            info = self.personal_info
            if isinstance(info, str):
                try:
                    import json
                    info = json.loads(info)
                except:
                    return "Unknown"
            
            first_name = info.get('first_name', '')
            last_name = info.get('last_name', '')
            return f"{first_name} {last_name}".strip() or "Unknown"
        
        return "Unknown"

class HospitalSettings(Base, TimestampMixin):
    """Hospital-specific settings and configuration"""
    __tablename__ = 'hospital_settings'

    setting_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    category = Column(String(50), nullable=False)  # 'verification', 'security', etc.
    settings = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationship
    hospital = relationship("Hospital", back_populates="settings_records")

# New master data models for business processes

class CurrencyMaster(Base, TimestampMixin, TenantMixin):
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
    
    # Relationship
    hospital = relationship("Hospital")

class PackageFamily(Base, TimestampMixin, TenantMixin):
    """Package families for grouping related packages"""
    __tablename__ = 'package_families'
    
    package_family_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_family = Column(String(100), nullable=False)
    description = Column(String(255))
    status = Column(String(20), default='active')
    
    # Relationships
    hospital = relationship("Hospital")
    packages = relationship("Package", back_populates="family")

class Package(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    family = relationship("PackageFamily", back_populates="packages")
    services = relationship("PackageServiceMapping", back_populates="package")

class Service(Base, TimestampMixin, TenantMixin):
    """Individual services offered"""
    __tablename__ = 'services'
    
    service_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    code = Column(String(20), nullable=False)
    service_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)  # Detailed description of the service

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
    service_type = Column(String(50), nullable=True)  # e.g., 'Skin Treatment', 'Laser Procedure', 'Consultation', 'Cosmetic Procedure'
    duration_minutes = Column(Integer, nullable=True)  # Expected duration of the service
    is_active = Column(Boolean, default=True, nullable=False)  # Indicates if service is currently available

    # Relationships
    hospital = relationship("Hospital")
    package_mappings = relationship("PackageServiceMapping", back_populates="service")
    consumable_standards = relationship("ConsumableStandard", back_populates="service")
    gl_account = relationship("ChartOfAccounts")

class PackageServiceMapping(Base, TimestampMixin, TenantMixin):
    """Maps services to packages"""
    __tablename__ = 'package_service_mapping'
    
    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'), nullable=False)
    sessions = Column(Integer, default=1)  # Number of sessions included
    is_optional = Column(Boolean, default=False)
    
    # Relationships
    hospital = relationship("Hospital")
    package = relationship("Package", back_populates="services")
    service = relationship("Service", back_populates="package_mappings")

class MedicineCategory(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    medicines = relationship("Medicine", back_populates="category")

class Manufacturer(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    medicines = relationship("Medicine", back_populates="manufacturer")

class Supplier(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    medicines = relationship("Medicine", back_populates="preferred_supplier")
    purchase_orders = relationship("PurchaseOrderHeader", back_populates="supplier")
    supplier_invoices = relationship("SupplierInvoice", back_populates="supplier")
    supplier_payments = relationship("SupplierPayment", back_populates="supplier")

class Medicine(Base, TimestampMixin, TenantMixin):
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
    
    # Pricing Information
    cost_price = Column(Numeric(10, 2))  # Cost price for profit calculation

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
    
    # Relationships
    hospital = relationship("Hospital")
    manufacturer = relationship("Manufacturer", back_populates="medicines")
    preferred_supplier = relationship("Supplier", back_populates="medicines")
    category = relationship("MedicineCategory", back_populates="medicines")
    consumable_standards = relationship("ConsumableStandard", back_populates="medicine")
    gl_account = relationship("ChartOfAccounts")
    inventory_entries = relationship("Inventory", back_populates="medicine")

class ConsumableStandard(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    service = relationship("Service", back_populates="consumable_standards")
    medicine = relationship("Medicine", back_populates="consumable_standards")

class ChartOfAccounts(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    parent_account = relationship("ChartOfAccounts", 
                             remote_side=[account_id],
                             backref="sub_accounts")
    # parent_account = relationship("ChartOfAccounts", remote_side=[account_id])
    # sub_accounts = relationship("ChartOfAccounts", 
    #                             backref="parent_account_ref",
    #                             remote_side=[parent_account_id])
    services = relationship("Service", back_populates="gl_account")
    medicines = relationship("Medicine", back_populates="gl_account")
    gl_entries = relationship("GLEntry", back_populates="account")