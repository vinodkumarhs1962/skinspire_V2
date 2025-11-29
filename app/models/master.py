# app/models/master.py

from sqlalchemy import Column, String, ForeignKey, Boolean, Text, Numeric, Date, Integer, DateTime, func, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from .base import Base, TimestampMixin, TenantMixin, SoftDeleteMixin, ApprovalMixin, generate_uuid

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

    # Bulk discount policy
    bulk_discount_enabled = Column(Boolean, default=False)  # Whether hospital offers bulk service discounts
    bulk_discount_min_service_count = Column(Integer, default=5)  # Minimum services to trigger bulk discount
    bulk_discount_effective_from = Column(Date)  # Date when bulk discount policy became effective

    # Loyalty discount policy (multi-discount system - 21-Nov-2025)
    loyalty_discount_mode = Column(String(20), default='absolute')  # 'absolute' = max(loyalty, other), 'additional' = loyalty% + other%

    # Discount Stacking Configuration (Comprehensive - 28-Nov-2025)
    # Configures how different discount types interact with each other
    # Default config allows full stacking with campaign having highest priority
    discount_stacking_config = Column(JSONB, default={
        'campaign': {
            'mode': 'exclusive',           # 'exclusive' = only campaign, 'incremental' = stacks with others
            'buy_x_get_y_exclusive': True  # X items always at list price
        },
        'loyalty': {
            'mode': 'incremental'          # 'incremental' = always adds, 'absolute' = competes
        },
        'bulk': {
            'mode': 'incremental',         # 'incremental' = adds, 'absolute' = competes
            'exclude_with_campaign': True  # No bulk if campaign applies
        },
        'vip': {
            'mode': 'absolute'             # 'incremental' = adds, 'absolute' = competes
        },
        'max_total_discount': None         # Optional cap on total discount % (e.g., 50)
    })

    # Relationships
    branches = relationship("Branch", back_populates="hospital", cascade="all, delete-orphan")
    staff = relationship("Staff", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
    users = relationship("User", back_populates="hospital")
    roles = relationship("RoleMaster", back_populates="hospital")
    settings_records = relationship("HospitalSettings", back_populates="hospital")
    roles = relationship("RoleMaster", back_populates="hospital")

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
    role_permissions = relationship("RoleModuleBranchAccess", back_populates="branch", cascade="all, delete-orphan")

    # NEW supplier-related relationships
    suppliers = relationship("Supplier", back_populates="branch")
    purchase_orders = relationship("PurchaseOrderHeader", back_populates="branch")
    supplier_invoices = relationship("SupplierInvoice", back_populates="branch")
    supplier_payments = relationship("SupplierPayment", back_populates="branch")

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

    def get_accessible_branches(self):
        """Get branches this staff member can access - uses permission service"""
        try:
            # Get user record for this staff
            from app.services.database_service import get_db_session
            from app.models.transaction import User
            
            with get_db_session(read_only=True) as session:
                user = session.query(User).filter_by(
                    entity_type='staff',
                    entity_id=self.staff_id
                ).first()
                
                if user:
                    from app.services.permission_service import get_user_accessible_branches
                    return get_user_accessible_branches(user.user_id, self.hospital_id)
                
        except Exception:
            pass
        
        # Fallback to assigned branch only
        if self.branch_id:
            return [{
                'branch_id': str(self.branch_id),
                'name': self.branch.name if self.branch else 'Unknown',
                'is_default': False,
                'is_user_branch': True,
                'has_all_access': False
            }]
        return []

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

    # Special Group Flag (Added 2025-11-27)
    # VIP/Special customers eligible for exclusive campaigns, Email/WhatsApp targeting, and special app features
    is_special_group = Column(Boolean, default=False)

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

    def can_be_accessed_by_user(self, user):
        """Check if user can access this patient - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'patient', 'view', str(self.branch_id))
        except Exception:
            return False

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

class PackageFamily(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
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

class Package(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Treatment or service packages"""
    __tablename__ = 'packages'

    package_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_family_id = Column(UUID(as_uuid=True), ForeignKey('package_families.package_family_id'))
    package_name = Column(String(100), nullable=False)
    package_code = Column(String(50))  # Unique code for search/autocomplete

    # Pricing and GST
    price = Column(Numeric(10, 2), nullable=False)  # Base price excluding GST
    selling_price = Column(Numeric(10, 2))  # Actual selling price (can differ from base)
    currency_code = Column(String(3), default='INR')
    hsn_code = Column(String(10))  # HSN/SAC code for GST compliance
    gst_rate = Column(Numeric(5, 2))  # Overall GST rate (%)
    cgst_rate = Column(Numeric(5, 2))  # Central GST rate (%)
    sgst_rate = Column(Numeric(5, 2))  # State GST rate (%)
    igst_rate = Column(Numeric(5, 2))  # Integrated GST rate (%)
    is_gst_exempt = Column(Boolean, default=False)

    # Business rules
    service_owner = Column(String(100))  # Responsible staff/department

    # Discount fields (multi-discount system - 21-Nov-2025)
    # Note: NO bulk_discount for packages (business rule)
    standard_discount_percent = Column(Numeric(5, 2), default=0)  # Fallback discount
    loyalty_discount_percent = Column(Numeric(5, 2), default=0)  # Loyalty card discount
    max_discount = Column(Numeric(5, 2))  # Maximum allowed discount cap

    status = Column(String(20), default='active')  # active/discontinued
    
    # Relationships
    hospital = relationship("Hospital")
    family = relationship("PackageFamily", back_populates="packages")
    services = relationship("PackageServiceMapping", back_populates="package")
    bom_items = relationship("PackageBOMItem", back_populates="package")
    session_plan = relationship("PackageSessionPlan", back_populates="package")
    payment_plans = relationship("PackagePaymentPlan", back_populates="package")

class PackageBOMItem(Base, TimestampMixin, TenantMixin, SoftDeleteMixin, ApprovalMixin):
    """
    Package Bill of Materials - Polymorphic item reference
    Supports services, medicines, consumables, products in a single table

    Workflow: draft → pending_approval → approved/rejected
    """
    __tablename__ = 'package_bom_items'

    bom_item_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'), nullable=False)

    # Polymorphic Item Reference - THE KEY DESIGN
    item_type = Column(String(20), nullable=False)  # 'service', 'medicine', 'product', 'consumable'
    item_id = Column(UUID(as_uuid=True), nullable=False)  # Points to services, medicines, etc.
    item_name = Column(String(200))  # Denormalized for quick display

    # Quantity & Specifications
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_of_measure = Column(String(50))

    # Delivery Method
    supply_method = Column(String(20), default='per_package')
    # Values: 'per_package' (upfront), 'per_session', 'session_1', 'session_2', etc.

    # Pricing (captured at BOM creation time)
    current_price = Column(Numeric(10, 2))
    line_total = Column(Numeric(10, 2))

    # Workflow Status - NEW
    status = Column(String(20), default='draft', nullable=False)
    # Values: 'draft', 'pending_approval', 'approved', 'rejected'
    rejection_reason = Column(Text)  # Reason for rejection

    # Display & Ordering
    display_sequence = Column(Integer)
    is_optional = Column(Boolean, default=False)
    conditional_logic = Column(JSONB)  # Conditions for when this item is needed
    notes = Column(Text)

    # Relationships
    hospital = relationship("Hospital")
    package = relationship("Package", back_populates="bom_items")

    def __repr__(self):
        return f"<PackageBOMItem(package={self.package_id}, item={self.item_type}:{self.item_name}, qty={self.quantity})>"

class PackageSessionPlan(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """
    Package Session Delivery Plan
    Defines how package is delivered across sessions with resource requirements
    """
    __tablename__ = 'package_session_plan'

    session_plan_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'), nullable=False)

    # Session Identification
    session_number = Column(Integer, nullable=False)
    session_name = Column(String(100))
    session_description = Column(Text)

    # Duration
    estimated_duration_minutes = Column(Integer)

    # Resource Requirements (JSON Array)
    # Format: [{"resource_type": "doctor", "role": "dermatologist", "duration_minutes": 30, "quantity": 1}]
    resource_requirements = Column(JSONB)

    # Scheduling
    recommended_gap_days = Column(Integer)  # Gap from previous session
    is_mandatory = Column(Boolean, default=True)
    scheduling_notes = Column(Text)
    prerequisites = Column(Text)  # What must be done before this session

    # Display
    display_sequence = Column(Integer)

    # Relationships
    hospital = relationship("Hospital")
    package = relationship("Package", back_populates="session_plan")

    def __repr__(self):
        return f"<PackageSessionPlan(package={self.package_id}, session={self.session_number}:{self.session_name})>"

class Service(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
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

    # Discount fields (multi-discount system - 21-Nov-2025)
    standard_discount_percent = Column(Numeric(5, 2), default=0)  # Fallback discount
    bulk_discount_percent = Column(Numeric(5, 2), default=0)  # Quantity-based discount
    loyalty_discount_percent = Column(Numeric(5, 2), default=0)  # Loyalty card discount
    max_discount = Column(Numeric(5, 2))  # Maximum allowed discount cap

    # Bulk Discount Eligibility (Added 2025-11-27)
    # Checkbox to enable/disable bulk discount for this service
    bulk_discount_eligible = Column(Boolean, default=False)

    default_gl_account = Column(UUID(as_uuid=True), ForeignKey('chart_of_accounts.account_id'))
    service_type = Column(String(50), nullable=True)  # e.g., 'Skin Treatment', 'Laser Procedure', 'Consultation', 'Cosmetic Procedure'
    duration_minutes = Column(Integer, nullable=True)  # Expected duration of the service
    is_active = Column(Boolean, default=True, nullable=False)  # Indicates if service is currently available

    # Relationships
    hospital = relationship("Hospital")
    package_mappings = relationship("PackageServiceMapping", back_populates="service")
    consumable_standards = relationship("ConsumableStandard", back_populates="service")
    gl_account = relationship("ChartOfAccounts")

class PackageServiceMapping(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
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

class MedicineCategory(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
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

class Manufacturer(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
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

class Supplier(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Medicine and equipment suppliers"""
    __tablename__ = 'suppliers'
    
    supplier_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)  # ADDED
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
    
    # Tax default fields for invoice transactions
    reverse_charge_applicable = Column(Boolean, default=False)  # RCM applicable by default
    default_itc_eligible = Column(Boolean, default=True)  # Default ITC eligibility

    bank_details = Column(JSONB)
    remarks = Column(String(255))
    status = Column(String(20), default='active')
    
    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")  # ADDED
    medicines = relationship("Medicine", back_populates="preferred_supplier")
    purchase_orders = relationship("PurchaseOrderHeader", back_populates="supplier")
    supplier_invoices = relationship("SupplierInvoice", back_populates="supplier")
    supplier_payments = relationship("SupplierPayment", back_populates="supplier")

    def can_be_accessed_by_user(self, user):
        """Check if user can access this supplier - uses permission service"""
        if not self.branch_id:
            return True  # Suppliers without branch can be accessed by all
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'supplier', 'view', str(self.branch_id))
        except Exception:
            return False
    
    def can_be_modified_by_user(self, user, action='edit'):
        """Check if user can modify this supplier - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'supplier', action, str(self.branch_id))
        except Exception:
            return False

class Medicine(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Medicine master data"""
    __tablename__ = 'medicines'
    
    medicine_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
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
    mrp = Column(Numeric(10, 2))  # Maximum Retail Price (new from previous migration)
    selling_price = Column(Numeric(10, 2))  # Actual selling price (new from previous migration)
    last_purchase_price = Column(Numeric(10, 2))  # Last purchase price (new from previous migration)

    # Currency field - just store it, no complex logic
    currency_code = Column(String(3), default='INR')  # Simple field, no constraints

    # MRP tracking fields
    mrp_effective_date = Column(Date)  # When MRP was last updated
    previous_mrp = Column(Numeric(10, 2))  # Previous MRP for tracking

    # Discount Information (multi-discount system - 21-Nov-2025)
    standard_discount_percent = Column(Numeric(5, 2), default=0)  # Fallback discount
    bulk_discount_percent = Column(Numeric(5, 2), default=0)  # Quantity-based discount
    loyalty_discount_percent = Column(Numeric(5, 2), default=0)  # Loyalty card discount
    max_discount = Column(Numeric(5, 2))  # Maximum allowed discount cap

    # Bulk Discount Eligibility (Added 2025-11-27)
    # Checkbox to enable/disable bulk discount for this medicine
    bulk_discount_eligible = Column(Boolean, default=False)

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
    branch = relationship("Branch")
    manufacturer = relationship("Manufacturer", back_populates="medicines")
    preferred_supplier = relationship("Supplier", back_populates="medicines")
    category = relationship("MedicineCategory", back_populates="medicines")
    consumable_standards = relationship("ConsumableStandard", back_populates="medicine")
    gl_account = relationship("ChartOfAccounts")
    inventory_entries = relationship("Inventory", back_populates="medicine")

    @property
    def branch_name(self):
        """Get branch name for display"""
        return self.branch.name if self.branch else 'Main Branch'
    
    @property
    def is_multi_branch_medicine(self):
        """Check if medicine is available across multiple branches (future feature)"""
        # For now, each medicine belongs to one branch
        return False
    
    def __repr__(self):
        return f"<Medicine(name='{self.medicine_name}', status='{self.status}')>"

    def can_be_accessed_by_user(self, user):
        """Check if user can access this medicine - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'inventory', 'view', str(self.branch_id))
        except Exception:
            return False

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


# ===================================================================
# DISCOUNT SYSTEM MODELS
# ===================================================================

class LoyaltyCardType(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Defines different types of loyalty cards with associated discounts"""
    __tablename__ = 'loyalty_card_types'

    card_type_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)

    # Card type details
    card_type_code = Column(String(20), nullable=False)  # e.g., 'SILVER', 'GOLD', 'PLATINUM'
    card_type_name = Column(String(50), nullable=False)  # Display name
    description = Column(Text)

    # Discount configuration
    discount_percent = Column(Numeric(5, 2), default=0)  # Default discount for this card type

    # Card benefits (flexible JSON for additional perks)
    benefits = Column(JSONB)  # {priority_booking: true, free_consultation: true, etc.}

    # Eligibility criteria
    min_lifetime_spend = Column(Numeric(12, 2))  # Minimum spend to qualify
    min_visits = Column(Integer)  # Minimum visit count to qualify

    # Visual styling
    card_color = Column(String(7))  # Hex color code for UI display
    icon_url = Column(String(255))
    display_sequence = Column(Integer)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    hospital = relationship("Hospital")
    patient_cards = relationship("PatientLoyaltyCard", back_populates="card_type")


class PatientLoyaltyCard(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Links patients to their loyalty card types"""
    __tablename__ = 'patient_loyalty_cards'

    patient_card_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    card_type_id = Column(UUID(as_uuid=True), ForeignKey('loyalty_card_types.card_type_id'), nullable=False)

    # Card details
    card_number = Column(String(50), unique=True)  # Physical/digital card number
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    hospital = relationship("Hospital")
    patient = relationship("Patient")
    card_type = relationship("LoyaltyCardType", back_populates="patient_cards")


class DiscountApplicationLog(Base):
    """Audit trail of all discount applications in invoices"""
    __tablename__ = 'discount_application_log'

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)

    # Invoice reference
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
    line_item_id = Column(UUID(as_uuid=True), ForeignKey('invoice_line_item.line_item_id'))

    # Discount details
    discount_type = Column(String(20), nullable=False)  # bulk, loyalty, campaign, manual, none
    card_type_id = Column(UUID(as_uuid=True), ForeignKey('loyalty_card_types.card_type_id'))  # If type = 'loyalty'
    campaign_hook_id = Column(UUID(as_uuid=True), ForeignKey('campaign_hook_config.hook_id'))  # If type = 'campaign'

    # Discount amounts
    original_price = Column(Numeric(12, 2), nullable=False)
    discount_percent = Column(Numeric(5, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), nullable=False)
    final_price = Column(Numeric(12, 2), nullable=False)

    # Context
    applied_at = Column(Date, nullable=False)
    applied_by = Column(UUID(as_uuid=True))
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'))
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'))

    # Metadata
    calculation_metadata = Column(JSONB)  # Store competing discounts and why this one was chosen
    service_count_in_invoice = Column(Integer)  # Total service count that triggered bulk discount

    # Relationships
    hospital = relationship("Hospital")
    patient = relationship("Patient")
    service = relationship("Service")
    card_type = relationship("LoyaltyCardType")
class PromotionCampaign(Base, TimestampMixin, TenantMixin, SoftDeleteMixin, ApprovalMixin):
    """Promotion/Campaign discount configuration"""
    __tablename__ = 'promotion_campaigns'

    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)

    # Campaign Details
    campaign_name = Column(String(100), nullable=False)
    campaign_code = Column(String(50), unique=True)  # For manual application
    description = Column(Text)

    # Campaign Period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)

    # Approval Workflow (Added 2025-11-28)
    # Status: draft (new), pending_approval (submitted), approved, rejected
    status = Column(String(20), default='draft')
    approval_notes = Column(Text)  # Rejection reason or approval comments

    # Promotion Type (Complex Promotions - 21-Nov-2025)
    promotion_type = Column(String(20), default='simple_discount')  # 'simple_discount', 'buy_x_get_y', 'tiered_discount', 'bundle'
    promotion_rules = Column(JSONB)  # Complex promotion rules in JSON format

    # Discount Configuration (for simple_discount type)
    discount_type = Column(String(20), nullable=False)  # 'percentage' or 'fixed_amount'
    discount_value = Column(Numeric(10, 2), nullable=False)

    # Applicability
    applies_to = Column(String(20), nullable=False)  # 'all', 'services', 'medicines', 'packages'
    specific_items = Column(JSONB)  # Array of item_ids if not 'all'

    # Constraints
    min_purchase_amount = Column(Numeric(10, 2))
    max_discount_amount = Column(Numeric(10, 2))
    max_uses_per_patient = Column(Integer)
    max_total_uses = Column(Integer)
    current_uses = Column(Integer, default=0)

    # Terms & Conditions
    terms_and_conditions = Column(Text)

    # Auto-application
    auto_apply = Column(Boolean, default=False)

    # Personalized Campaign Flag (Added 2025-11-25)
    # TRUE = Sent via Email/WhatsApp to specific patients, requires manual code entry
    # FALSE = Public promotion, auto-applied to all eligible patients
    is_personalized = Column(Boolean, default=False)

    # Special Group Targeting (Added 2025-11-27)
    # TRUE = Campaign only applies to patients where is_special_group = TRUE
    # FALSE = Campaign applies to all patients (default)
    target_special_group = Column(Boolean, default=False)

    # Campaign Group Targeting (Added 2025-11-28)
    # JSONB format: {"group_ids": ["uuid1", "uuid2"]}
    # NULL = use applies_to/specific_items logic (backward compatible)
    target_groups = Column(JSONB)

    # Relationships
    hospital = relationship("Hospital")
    usage_logs = relationship("PromotionUsageLog", back_populates="campaign")


class PromotionUsageLog(Base):
    """Tracks promotion campaign usage"""
    __tablename__ = 'promotion_usage_log'

    usage_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('promotion_campaigns.campaign_id'), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'))
    invoice_id = Column(UUID(as_uuid=True))  # Reference to invoice

    # Usage Details
    usage_date = Column(DateTime(timezone=True), server_default=func.now())
    discount_amount = Column(Numeric(10, 2), nullable=False)
    invoice_amount = Column(Numeric(10, 2))

    # Applied By
    applied_by = Column(String(15))
    applied_manually = Column(Boolean, default=False)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("PromotionCampaign", back_populates="usage_logs")
    hospital = relationship("Hospital")
    patient = relationship("Patient")


class PromotionCampaignGroup(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Campaign groups for organizing services, medicines, and packages into targetable collections"""
    __tablename__ = 'promotion_campaign_groups'

    group_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)

    # Group Details
    group_code = Column(String(50), nullable=False)
    group_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # Unique constraint on (hospital_id, group_code)
    __table_args__ = (
        UniqueConstraint('hospital_id', 'group_code', name='uq_campaign_group_code'),
    )

    # Relationships
    hospital = relationship("Hospital")
    items = relationship("PromotionGroupItem", back_populates="group", cascade="all, delete-orphan")


class PromotionGroupItem(Base):
    """Junction table linking campaign groups to services, medicines, and packages"""
    __tablename__ = 'promotion_group_items'

    group_item_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    group_id = Column(UUID(as_uuid=True), ForeignKey('promotion_campaign_groups.group_id', ondelete='CASCADE'), nullable=False)
    item_type = Column(String(20), nullable=False)  # 'service', 'medicine', 'package'
    item_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))

    # Unique constraint: same item cannot be in same group twice
    __table_args__ = (
        UniqueConstraint('group_id', 'item_type', 'item_id', name='uq_group_item'),
        CheckConstraint("item_type IN ('service', 'medicine', 'package')", name='chk_item_type'),
    )

    # Relationships
    group = relationship("PromotionCampaignGroup", back_populates="items")
