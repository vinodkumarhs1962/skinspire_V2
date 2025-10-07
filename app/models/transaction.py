# app/models/transaction.py

from werkzeug.security import generate_password_hash, check_password_hash    
from sqlalchemy import text
from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, DateTime, Date, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timezone
from .base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid, ApprovalMixin, TenantMixin
from flask import current_app
from flask_login import UserMixin
import json


class User(Base, TimestampMixin, SoftDeleteMixin, UserMixin):
    """User authentication and base user information"""
    __tablename__ = 'users'

    user_id = Column(String(15), primary_key=True)  # Phone number
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'))
    entity_type = Column(String(10), nullable=False)  # 'staff' or 'patient'
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    password_hash = Column(String(255))
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    verification_status = Column(JSONB, default={})
    
    # UI preferences (added for business processes)
    ui_preferences = Column(JSONB, default={"theme": "light"})  # UI preferences including theme
    last_currency = Column(String(3))  # Last used currency

    # Relationships
    hospital = relationship("Hospital", back_populates="users")
    roles = relationship("UserRoleMapping", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")  # Add this line

    # def set_password(self, password): # can remove this method as using trigger to set password
    #     self.password_hash = generate_password_hash(password)

    # Add these properties to the User class in app/models/transaction.py
    @property
    def entity_data(self):
        """Get the related Staff or Patient entity"""
        if hasattr(self, '_entity_data'):
            return self._entity_data
            
        try:
            from app.services.database_service import get_db_session
            with get_db_session(read_only=True) as session:
                if self.entity_type == 'staff':
                    from app.models.master import Staff
                    entity = session.query(Staff).filter_by(staff_id=self.entity_id).first()
                elif self.entity_type == 'patient':
                    from app.models.master import Patient
                    entity = session.query(Patient).filter_by(patient_id=self.entity_id).first()
                else:
                    entity = None
                    
                self._entity_data = entity
                return entity
        except Exception as e:
            current_app.logger.error(f"Error loading entity data: {str(e)}")
            return None

    @property
    def personal_info_dict(self):
        """Get personal_info as dictionary"""
        entity = self.entity_data
        if not entity or not hasattr(entity, 'personal_info'):
            return {}
            
        try:
            if isinstance(entity.personal_info, str):
                import json
                return json.loads(entity.personal_info)
            return entity.personal_info
        except Exception as e:
            current_app.logger.error(f"Error parsing personal_info: {str(e)}")
            return {}

    @property
    def contact_info_dict(self):
        """Get contact_info as dictionary"""
        entity = self.entity_data
        if not entity or not hasattr(entity, 'contact_info'):
            return {}
            
        try:
            if isinstance(entity.contact_info, str):
                import json
                return json.loads(entity.contact_info)
            return entity.contact_info
        except Exception as e:
            current_app.logger.error(f"Error parsing contact_info: {str(e)}")
            return {}

    @property
    def first_name(self):
        """Get first name from personal info"""
        return self.personal_info_dict.get('first_name', '')

    @property
    def last_name(self):
        """Get last name from personal info"""
        return self.personal_info_dict.get('last_name', '')

    @property
    def email(self):
        """Get email from contact info"""
        return self.contact_info_dict.get('email', '')

    @property
    def phone(self):
        """Get phone from contact info or user_id"""
        return self.contact_info_dict.get('phone', self.user_id)

    @property
    def full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}".strip()



# Add the set_password method to the User class in transaction.py

    def get_id(self):
        """Return the user_id as a string"""
        return str(self.user_id)

    def set_password(self, password):
        """Set password hash using werkzeug"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash using werkzeug"""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    # phone and email verification methods
    @property
    def is_phone_verified(self):
        """Check if user's phone number is verified"""
        if not hasattr(self, 'verification_status') or not self.verification_status:
            return False
            
        # Handle string or dict
        status = self.verification_status
        if isinstance(status, str):
            try:
                status = json.loads(status)
            except:
                return False
                
        phone_status = status.get('phone', {})
        return phone_status.get('verified', False)

    @property
    def is_email_verified(self):
        """Check if user's email is verified"""
        if not hasattr(self, 'verification_status') or not self.verification_status:
            return False
            
        # Handle string or dict
        status = self.verification_status
        if isinstance(status, str):
            try:
                status = json.loads(status)
            except:
                return False
                
        email_status = status.get('email', {})
        return email_status.get('verified', False)

    @property
    def verification_info(self):
        """Get full verification information"""
        if not hasattr(self, 'verification_status') or not self.verification_status:
            return {
                'phone': {'verified': False},
                'email': {'verified': False}
            }
            
        # Handle string or dict
        status = self.verification_status
        if isinstance(status, str):
            try:
                status = json.loads(status)
            except:
                return {
                    'phone': {'verified': False},
                    'email': {'verified': False}
                }
                
        return {
            'phone': status.get('phone', {'verified': False}),
            'email': status.get('email', {'verified': False})
        }

    @property
    def assigned_branch_id(self):
        """Get user's assigned branch ID - delegates to permission service"""
        try:
            from app.services.permission_service import get_user_assigned_branch_id
            return get_user_assigned_branch_id(self.user_id, self.hospital_id)
        except Exception:
            return None
    
    @property
    def accessible_branch_ids(self):
        """Get list of branch IDs user can access - delegates to permission service"""
        try:
            from app.services.permission_service import get_user_accessible_branches
            branches = get_user_accessible_branches(self.user_id, self.hospital_id)
            return [b['branch_id'] for b in branches]
        except Exception:
            return []
    
    @property
    def accessible_branches(self):
        """Get full branch details user can access - direct service call"""
        try:
            from app.services.permission_service import get_user_accessible_branches
            return get_user_accessible_branches(self.user_id, self.hospital_id)
        except Exception:
            return []
    
    @property
    def is_multi_branch_user(self):
        """Check if user can access multiple branches"""
        return len(self.accessible_branch_ids) > 1
    
    def has_permission(self, module_name: str, permission_type: str) -> bool:
        """Check basic permission - delegates to permission service"""
        try:
            from app.services.permission_service import has_permission
            return has_permission(self, module_name, permission_type)
        except Exception:
            return False
    
    def has_branch_permission(self, module_name: str, permission_type: str, branch_id: str = None) -> bool:
        """Check branch-specific permission - delegates to permission service"""
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(self, module_name, permission_type, branch_id)
        except Exception:
            return False
    
    def has_cross_branch_permission(self, module_name: str, action: str = 'view') -> bool:
        """Check cross-branch permission - delegates to permission service"""
        try:
            from app.services.permission_service import has_cross_branch_permission
            return has_cross_branch_permission(self, module_name, action)
        except Exception:
            return False
    
    def get_branch_context_for_module(self, module_name: str):
        """Get complete branch context for module - delegates to permission service"""
        try:
            from app.services.permission_service import get_user_branch_context_for_module
            return get_user_branch_context_for_module(self, module_name)
        except Exception:
            return {
                'assigned_branch_id': None,
                'accessible_branches': [],
                'is_multi_branch': False,
                'can_access_all_branches': False,
                'can_cross_branch_report': False
            }
    
    def update_last_accessed_branch(self, branch_id: str):
        """Update the last accessed branch for this user"""
        try:
            from app.services.database_service import get_db_session
            
            with get_db_session() as session:
                user = session.query(User).filter_by(user_id=self.user_id).first()
                if user and hasattr(user, 'last_accessed_branch_id'):
                    user.last_accessed_branch_id = branch_id
                    if hasattr(user, 'branch_switch_count'):
                        user.branch_switch_count = (user.branch_switch_count or 0) + 1
                    session.commit()
        except Exception:
            pass
    
    def validate_permissions(self) -> dict:
        """Validate user's permission system - delegates to permission service"""
        try:
            from app.services.permission_service import validate_permission_system
            return validate_permission_system(self.user_id, self.hospital_id)
        except Exception:
            return {'errors': ['Permission validation failed']}
        
    @property
    def show_deleted_records(self):
        """Check if user wants to see deleted records"""
        if not self.ui_preferences:
            return False
        return self.ui_preferences.get('show_deleted_records', False)
    
    @show_deleted_records.setter
    def show_deleted_records(self, value: bool):
        """Set preference for showing deleted records"""
        if not self.ui_preferences:
            self.ui_preferences = {}
        self.ui_preferences['show_deleted_records'] = value
    
class LoginHistory(Base, TimestampMixin):
    """Track user login attempts and sessions"""
    __tablename__ = 'login_history'

    history_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(String(15), ForeignKey('users.user_id'), nullable=False)
    login_time = Column(DateTime(timezone=True), nullable=False)
    logout_time = Column(DateTime(timezone=True))
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    status = Column(String(20))  # success, failed, locked
    failure_reason = Column(String(100))

class UserSession(Base, TimestampMixin):
    """Active user sessions"""
    __tablename__ = 'user_sessions'

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(String(15), ForeignKey('users.user_id'), nullable=False)
    token = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession {self.session_id}>"

class VerificationCode(Base, TimestampMixin):
    """Stores verification codes for phone and email verification"""
    __tablename__ = 'verification_codes'

    user_id = Column(String(15), ForeignKey('users.user_id'), primary_key=True)
    code_type = Column(String(10), primary_key=True)  # 'phone' or 'email'
    code = Column(String(10), nullable=False)
    target = Column(String(255), nullable=False)  # phone number or email address
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0)

    # Relationship
    user = relationship("User", foreign_keys=[user_id])

class StaffApprovalRequest(Base, TimestampMixin, TenantMixin):
    """Staff registration approval workflow"""
    __tablename__ = 'staff_approval_requests'

    request_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id = Column(String(15), ForeignKey('users.user_id'), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'), nullable=False)
    
    # Request details
    request_data = Column(JSONB)  # Qualifications, experience, etc.
    document_refs = Column(JSONB)  # References to uploaded documents
    
    # Approval workflow
    status = Column(String(20), default='pending')  # pending, approved, rejected
    notes = Column(Text)  # Admin notes on approval/rejection
    
    # Approval info
    approved_by = Column(String(15), ForeignKey('users.user_id'))
    approved_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    staff = relationship("Staff")
    
    @property
    def is_pending(self):
        """Check if request is pending"""
        return self.status == 'pending'
        
    @property
    def is_approved(self):
        """Check if request is approved"""
        return self.status == 'approved'
        
    @property
    def is_rejected(self):
        """Check if request is rejected"""
        return self.status == 'rejected'
        
    def approve(self, approver_id, notes=None):
        """Approve the request"""
        self.status = 'approved'
        self.approved_by = approver_id
        self.approved_at = datetime.now(timezone.utc)
        if notes:
            self.notes = notes
            
    def reject(self, approver_id, notes=None):
        """Reject the request"""
        self.status = 'rejected'
        self.approved_by = approver_id
        self.approved_at = datetime.now(timezone.utc)
        if notes:
            self.notes = notes

# New transaction models for business processes

class InvoiceHeader(Base, TimestampMixin, TenantMixin):
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
    
    # Invoice cancellation flag
    is_cancelled = Column(Boolean, default=False)
    cancellation_reason = Column(String(255))
    cancelled_at = Column(DateTime(timezone=True))  
    

    # Default GL Account (Business Rule #9)
    gl_account_id = Column(UUID(as_uuid=True), ForeignKey('chart_of_accounts.account_id'))
    
    # Additional Information
    notes = Column(Text)
    
    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    patient = relationship("Patient")
    gl_account = relationship("ChartOfAccounts")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("PaymentDetail", back_populates="invoice", cascade="all, delete-orphan")
    gl_transaction = relationship("GLTransaction", back_populates="invoice_ref", uselist=False)

    @property
    def branch_name(self):
        """Get branch name for display"""
        return self.branch.name if self.branch else 'Main Branch'
    
    def can_be_accessed_by_user(self, user):
        """Check if user can access this invoice - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'billing', 'view', str(self.branch_id))
        except Exception:
            return False

class InvoiceLineItem(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    invoice = relationship("InvoiceHeader", back_populates="line_items")
    package = relationship("Package")
    service = relationship("Service")
    medicine = relationship("Medicine")
    
class PaymentDetail(Base, TimestampMixin, TenantMixin):
    """Payment details for invoices"""
    __tablename__ = 'payment_details'
    
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'), nullable=False)
    
    # Payment Information
    payment_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    
    # Payment type Information
    advance_adjustment_id = Column(UUID(as_uuid=True), ForeignKey('advance_adjustments.adjustment_id'))
    loyalty_redemption_id = Column(UUID(as_uuid=True), ForeignKey('loyalty_redemptions.redemption_id'))
    

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
    
    # Add notes column here
    notes = Column(Text)  # Add this line to include notes

    # Relationships
    hospital = relationship("Hospital")
    invoice = relationship("InvoiceHeader", back_populates="payments")
    gl_transaction = relationship("GLTransaction", foreign_keys=[gl_entry_id])
    advance_adjustment = relationship("AdvanceAdjustment", foreign_keys=[advance_adjustment_id], backref="related_payments")
    loyalty_redemption = relationship("LoyaltyRedemption", foreign_keys=[loyalty_redemption_id], backref="related_payment")

class PurchaseOrderHeader(Base, TimestampMixin, TenantMixin, SoftDeleteMixin, ApprovalMixin):
    """Purchase order header - Enhanced with soft delete and approval tracking"""
    __tablename__ = 'purchase_order_header'
    
    po_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)
    po_number = Column(String(20), nullable=False, unique=True)
    po_date = Column(DateTime(timezone=True), nullable=False)
    
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
    deleted_flag = Column(Boolean, default=False)  # ✅ KEEP for backward compatibility
    
    # ✅ REMOVED: approved_by = Column(String(50))  # Now inherited from ApprovalMixin
    # ✅ NEW: approved_at field now available via ApprovalMixin
    
    # Amounts
    total_amount = Column(Numeric(12, 2))
    
    # ✅ NEW FIELDS (inherited from mixins):
    # From SoftDeleteMixin:
    # - is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    # - deleted_at = Column(DateTime(timezone=True))
    # - deleted_by = Column(String(50))
    
    # From ApprovalMixin:
    # - approved_by = Column(String(50))
    # - approved_at = Column(DateTime(timezone=True))
    
    # Relationships (unchanged)
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    supplier = relationship("Supplier", back_populates="purchase_orders")
    po_lines = relationship("PurchaseOrderLine", back_populates="po_header", cascade="all, delete-orphan")
    supplier_invoices = relationship("SupplierInvoice", back_populates="po_header")

    def can_be_accessed_by_user(self, user):
        """Check if user can access this PO - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'supplier', 'view', str(self.branch_id))
        except Exception:
            return False


class PurchaseOrderLine(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
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

    # ===== DISCOUNT FIELDS (matching supplier_invoice_line) =====
    discount_percent = Column(Numeric(5, 2), default=0)  # Discount percentage
    discount_amount = Column(Numeric(12, 2), default=0)  # Calculated discount amount
    taxable_amount = Column(Numeric(12, 2))  # Amount after discount, before GST
    
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
    
    # ✅ NEW FIELDS (inherited from SoftDeleteMixin):
    # - is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    # - deleted_at = Column(DateTime(timezone=True))
    # - deleted_by = Column(String(50))

    # Relationships
    hospital = relationship("Hospital")
    po_header = relationship("PurchaseOrderHeader", back_populates="po_lines")
    medicine = relationship("Medicine")

    # Business Logic Aliases for Clarity
    @property
    def purchase_quantity(self):
        """Quantity purchased in saleable units"""
        return self.units
    
    @property
    def unit_rate(self):
        """Vendor's offered rate per saleable unit (before discount)"""
        return self.pack_purchase_price
    
    @property
    def unit_mrp(self):
        """MRP per saleable unit"""
        return self.pack_mrp
    
    @property
    def conversion_factor(self):
        """Number of sub-units per saleable unit (for inventory)"""
        return self.units_per_pack
    
    @property
    def discounted_rate(self):
        """Rate after discount (before GST)"""
        return self.taxable_amount
    
    @property
    def sub_unit_price(self):
        """Price per smallest selling unit (for inventory pricing)"""
        return self.unit_price
    
    @property
    def total_sub_units(self):
        """Total sub-units for inventory (purchase_qty × conversion_factor)"""
        if self.units and self.units_per_pack:
            return float(self.units) * float(self.units_per_pack)
        return 0
    
    @property
    def base_amount(self):
        """Total amount before discount and GST"""
        if self.units and self.pack_purchase_price:
            return float(self.units) * float(self.pack_purchase_price)
        return 0
    
    @property
    def effective_rate(self):
        """Rate after discount per unit"""
        if self.pack_purchase_price and self.discount_percent:
            return float(self.pack_purchase_price) * (1 - float(self.discount_percent) / 100)
        return float(self.pack_purchase_price or 0)
    
    @property
    def discounted_amount(self):
        """Taxable amount (after discount, before GST)"""
        if self.taxable_amount:
            return float(self.taxable_amount)
        # Calculate if not set
        base = self.base_amount
        if self.discount_amount:
            return base - float(self.discount_amount)
        elif self.discount_percent:
            return base * (1 - float(self.discount_percent) / 100)
        return base

class SupplierInvoice(Base, TimestampMixin, TenantMixin, SoftDeleteMixin, ApprovalMixin):
    """Supplier invoice information"""
    __tablename__ = 'supplier_invoice'
    
    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)  # ADDED
    po_id = Column(UUID(as_uuid=True), ForeignKey('purchase_order_header.po_id'))
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    
    # Invoice Details
    supplier_invoice_number = Column(String(50), nullable=False)
    invoice_date = Column(DateTime(timezone=True), nullable=False)  # With timezone
    notes = Column(String(500))
    
    # GST Information
    supplier_gstin = Column(String(15))
    place_of_supply = Column(String(2))  # State code
    reverse_charge = Column(Boolean, default=False)
    
    # Currency Information
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    
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
    
    # Posting control fields
    gl_posted = Column(Boolean, default=False, nullable=False)
    inventory_posted = Column(Boolean, default=False, nullable=False)
    posting_date = Column(DateTime(timezone=True))
    posting_reference = Column(String(50))
    posting_errors = Column(Text)
    
    # Reversal tracking fields
    is_reversed = Column(Boolean, default=False, nullable=False)
    reversed_by_invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'))
    original_invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'))
    reversal_reason = Column(String(200))
    reversed_at = Column(DateTime(timezone=True))
    reversed_by = Column(String(50))
    
    # Credit note support
    credited_by_invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'))
    is_credit_note = Column(Boolean, default=False, nullable=False)

    # ✅ NEW FIELDS (inherited from mixins):
    # From SoftDeleteMixin:
    # - is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    # - deleted_at = Column(DateTime(timezone=True))
    # - deleted_by = Column(String(50))
    
    # From ApprovalMixin:
    # - approved_by = Column(String(50))
    # - approved_at = Column(DateTime(timezone=True))


    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")  # ADDED
    po_header = relationship("PurchaseOrderHeader", back_populates="supplier_invoices")
    supplier = relationship("Supplier", back_populates="supplier_invoices")
    invoice_lines = relationship("SupplierInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("SupplierPayment", back_populates="invoice")
    gl_transaction = relationship("GLTransaction", back_populates="supplier_invoice_ref", uselist=False)

    # Self-referential relationships for reversals and credit notes
    original_invoice = relationship("SupplierInvoice", 
                                   foreign_keys=[original_invoice_id], 
                                   remote_side=[invoice_id],
                                   backref="credit_notes")
    
    reversed_by_invoice = relationship("SupplierInvoice", 
                                      foreign_keys=[reversed_by_invoice_id], 
                                      remote_side=[invoice_id])
    
    credited_by_invoice = relationship("SupplierInvoice", 
                                      foreign_keys=[credited_by_invoice_id], 
                                      remote_side=[invoice_id])

    def can_be_accessed_by_user(self, user):
        """Check if user can access this supplier invoice - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'supplier', 'view', str(self.branch_id))
        except Exception:
            return False    


class SupplierInvoiceLine(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
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
    
    # ✅ NEW FIELDS (inherited from SoftDeleteMixin):
    # - is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    # - deleted_at = Column(DateTime(timezone=True))
    # - deleted_by = Column(String(50))

    # Relationships
    hospital = relationship("Hospital")
    invoice = relationship("SupplierInvoice", back_populates="invoice_lines")
    medicine = relationship("Medicine")

class SupplierPayment(Base, TimestampMixin, TenantMixin, SoftDeleteMixin):
    """Enhanced Payments to suppliers with Branch Support"""
    __tablename__ = 'supplier_payment'
    
    # === EXISTING CORE FIELDS ===
    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    
    # === BRANCH SUPPORT (CRITICAL ADDITION) ===
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)
    
    # === EXISTING FIELDS ===
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'))
    
    # Payment Details
    payment_date = Column(DateTime(timezone=True), nullable=False)
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
    
    # Bank Reconciliation
    reconciliation_status = Column(String(20), default='pending')
    reconciliation_date = Column(DateTime(timezone=True))
    
    # === ENHANCED FIELDS ===
    
    # Payment categorization
    payment_category = Column(String(20), default='manual')  # manual, gateway, upi, bank_transfer
    payment_source = Column(String(30), default='internal')  # internal, razorpay, payu, upi, bank_api
    
    # Multi-method payment amounts
    cash_amount = Column(Numeric(12, 2), default=0)
    cheque_amount = Column(Numeric(12, 2), default=0)
    bank_transfer_amount = Column(Numeric(12, 2), default=0)
    upi_amount = Column(Numeric(12, 2), default=0)
    
    # Cheque Details
    cheque_number = Column(String(20))
    cheque_date = Column(Date)
    cheque_bank = Column(String(100))
    cheque_branch = Column(String(100))
    cheque_status = Column(String(20))  # pending, cleared, bounced, cancelled
    cheque_clearance_date = Column(Date)
    
    # Bank Transfer Details
    bank_name = Column(String(100))
    bank_branch = Column(String(100))
    bank_account_name = Column(String(100))
    account_number_last4 = Column(String(4))  # For security
    bank_reference_number = Column(String(50))
    ifsc_code = Column(String(11))
    transfer_mode = Column(String(20))  # neft, rtgs, imps, swift
    
    # UPI Details
    upi_id = Column(String(100))
    upi_app_name = Column(String(50))
    upi_transaction_id = Column(String(50))
    upi_reference_id = Column(String(50))
    
    # Posting control fields
    gl_posted = Column(Boolean, default=False, nullable=False)
    posting_date = Column(DateTime(timezone=True))
    posting_reference = Column(String(50))
    posting_errors = Column(Text)

    # ✅ NEW FIELDS ONLY (inherited from SoftDeleteMixin):
    # - is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    # - deleted_at = Column(DateTime(timezone=True))
    # - deleted_by = Column(String(50))

    # Workflow & Approval
    workflow_status = Column(String(20), default='draft')  # draft, pending_approval, approved, rejected, processed
    requires_approval = Column(Boolean, default=False)
    approval_level = Column(String(20), default='none')
    next_approver_id = Column(String(15), ForeignKey('users.user_id'))
    approval_threshold = Column(Numeric(12, 2))
    submitted_for_approval_at = Column(DateTime(timezone=True))
    submitted_by = Column(String(15), ForeignKey('users.user_id'))
    approved_by = Column(String(15), ForeignKey('users.user_id'))
    approved_at = Column(DateTime(timezone=True))
    approval_notes = Column(Text)
    rejected_by = Column(String(15), ForeignKey('users.user_id'))
    rejected_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    
    # Document Management
    receipt_document_path = Column(String(500))
    bank_statement_path = Column(String(500))
    authorization_document_path = Column(String(500))
    document_upload_status = Column(String(20), default='none')  # none, pending, uploaded, verified
    total_documents_count = Column(Integer, default=0)
    documents_verified_count = Column(Integer, default=0)
    document_verified_by = Column(String(15), ForeignKey('users.user_id'))
    document_verified_at = Column(DateTime(timezone=True))
    
    # Enhanced Reconciliation
    bank_statement_date = Column(Date)
    bank_statement_reference = Column(String(100))
    reconciliation_notes = Column(Text)
    reconciled_by = Column(String(15), ForeignKey('users.user_id'))
    auto_reconciliation_attempted = Column(Boolean, default=False)
    auto_reconciliation_status = Column(String(20))  # matched, partial_match, no_match, manual_required
    auto_reconciliation_confidence = Column(Numeric(5, 2))  # Confidence score 0-100
    
    # Payment Reversals & Refunds
    is_reversed = Column(Boolean, default=False)
    reversal_reason = Column(String(255))
    reversed_by = Column(String(15), ForeignKey('users.user_id'))
    reversed_at = Column(DateTime(timezone=True))
    reversal_reference = Column(String(100))
    original_payment_id = Column(UUID(as_uuid=True), ForeignKey('supplier_payment.payment_id'))
    refund_amount = Column(Numeric(12, 2), default=0)
    refund_date = Column(DateTime(timezone=True))
    refund_reference = Column(String(100))
    refund_reason = Column(String(255))
    refund_method = Column(String(30))  # same_method, bank_transfer, cheque
    
    # TDS (Tax Deducted at Source)
    tds_applicable = Column(Boolean, default=False)
    tds_rate = Column(Numeric(5, 2), default=0)
    tds_amount = Column(Numeric(12, 2), default=0)
    tds_reference = Column(String(50))
    
    # Notification & Communication
    supplier_notified = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True))
    notification_method = Column(String(20))  # email, sms, whatsapp, portal
    notification_reference = Column(String(100))
    
    # Integration Fields
    erp_payment_id = Column(String(100))
    erp_sync_status = Column(String(20))  # pending, synced, failed, not_required
    erp_sync_at = Column(DateTime(timezone=True))
    erp_error_message = Column(Text)
    accounting_reference = Column(String(100))
    
    # === GATEWAY FIELDS (Future Ready) ===
    gateway_payment_id = Column(String(100))
    gateway_order_id = Column(String(100))
    gateway_transaction_id = Column(String(100))
    gateway_response_code = Column(String(10))
    gateway_response_message = Column(String(255))
    gateway_fee = Column(Numeric(12, 2), default=0)
    gateway_tax = Column(Numeric(12, 2), default=0)
    gateway_initiated_at = Column(DateTime(timezone=True))
    gateway_completed_at = Column(DateTime(timezone=True))
    gateway_failed_at = Column(DateTime(timezone=True))
    gateway_metadata = Column(JSONB)
    
    # Payment Link Details
    payment_link_id = Column(String(100))
    payment_link_url = Column(String(500))
    payment_link_expires_at = Column(DateTime(timezone=True))
    payment_link_status = Column(String(20))  # created, sent, expired, paid
    
    # Processing Fees
    processing_fee = Column(Numeric(12, 2), default=0)
    processing_status = Column(String(20), default='completed') 

    # Audit Fields
    payment_source_ip = Column(String(45))
    user_agent = Column(String(255))
    
    # === RELATIONSHIPS ===
    hospital = relationship("Hospital")
    branch = relationship("Branch")  # NEW: Branch relationship
    supplier = relationship("Supplier", back_populates="supplier_payments")
    invoice = relationship("SupplierInvoice", back_populates="payments")
    gl_transaction = relationship("GLTransaction", foreign_keys=[gl_entry_id])
    
    # User relationships
    submitted_by_user = relationship("User", foreign_keys=[submitted_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    rejected_by_user = relationship("User", foreign_keys=[rejected_by])
    document_verified_by_user = relationship("User", foreign_keys=[document_verified_by])
    reconciled_by_user = relationship("User", foreign_keys=[reconciled_by])
    reversed_by_user = relationship("User", foreign_keys=[reversed_by])
    
    # Self-reference for reversals
    original_payment = relationship("SupplierPayment", foreign_keys=[original_payment_id], remote_side=[payment_id])
    reversal_payments = relationship("SupplierPayment", foreign_keys=[original_payment_id], overlaps="original_payment")
    
    documents = relationship("PaymentDocument", back_populates="payment", cascade="all, delete-orphan")
    next_approver = relationship("User", foreign_keys=[next_approver_id])

    # === COMPUTED PROPERTIES ===
    @property
    def total_manual_amount(self):
        """Total amount from manual payment methods"""
        return (self.cash_amount or 0) + (self.cheque_amount or 0) + (self.bank_transfer_amount or 0) + (self.upi_amount or 0)
    
    @property
    def net_payment_amount(self):
        """Net payment amount after gateway fees and TDS"""
        return self.amount - (self.gateway_fee or 0) - (self.gateway_tax or 0) - (self.tds_amount or 0)
    
    @property
    def is_pending_approval(self):
        """Check if payment requires and is pending approval"""
        return self.requires_approval and self.workflow_status == 'pending_approval'
    
    @property
    def is_gateway_payment(self):
        """Check if this is a gateway payment"""
        return self.payment_category in ['gateway', 'upi'] and self.gateway_payment_id is not None
    
    @property
    def days_since_payment(self):
        """Days since payment was made"""
        if self.payment_date:
            return (datetime.now(timezone.utc) - self.payment_date).days
        return None
    
    @property
    def reconciliation_pending_days(self):
        """Days since payment is pending reconciliation"""
        if self.reconciliation_status == 'pending' and self.payment_date:
            return (datetime.now(timezone.utc) - self.payment_date).days
        return None
    
    @property 
    def branch_name(self):
        """Get branch name for display"""
        return self.branch.branch_name if self.branch else 'Unknown Branch'
    
    @property
    def branch_code(self):
        """Get branch code for display"""
        return self.branch.branch_code if self.branch else 'N/A'
    
    @property
    def payment_location(self):
        """Get full payment location for display"""
        if self.branch:
            return f"{self.branch.branch_name} ({self.branch.branch_code})"
        return "Unknown Location"
    
    # === BRANCH-AWARE METHODS ===
    @classmethod
    def get_by_branch(cls, session, branch_id, **filters):
        """Get payments filtered by branch"""
        query = session.query(cls).filter_by(branch_id=branch_id)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query
    
    @classmethod
    def get_branch_summary(cls, session, branch_id, start_date=None, end_date=None):
        """Get payment summary for a specific branch"""
        query = session.query(cls).filter_by(branch_id=branch_id, is_reversed=False)
        
        if start_date:
            query = query.filter(cls.payment_date >= start_date)
        if end_date:
            query = query.filter(cls.payment_date <= end_date)
            
        payments = query.all()
        
        return {
            'total_payments': len(payments),
            'total_amount': sum(p.amount for p in payments),
            'cash_total': sum(p.cash_amount or 0 for p in payments),
            'cheque_total': sum(p.cheque_amount or 0 for p in payments),
            'bank_transfer_total': sum(p.bank_transfer_amount or 0 for p in payments),
            'upi_total': sum(p.upi_amount or 0 for p in payments),
            'pending_reconciliation': len([p for p in payments if p.reconciliation_status == 'pending']),
            'pending_approval': len([p for p in payments if p.workflow_status == 'pending_approval'])
        }
    
    # === ADDITIONAL METHODS ===
    @property
    def document_summary(self):
        """Get summary of attached documents"""
        if not self.documents:
            return {
                'total': 0,
                'verified': 0,
                'pending': 0,
                'completion_percentage': 0
            }
        
        total = len(self.documents)
        verified = len([doc for doc in self.documents if doc.verification_status == 'verified'])
        pending = len([doc for doc in self.documents if doc.verification_status == 'pending'])
        
        return {
            'total': total,
            'verified': verified,
            'pending': pending,
            'completion_percentage': (verified / total * 100) if total > 0 else 0
        }

    @property
    def has_required_documents(self):
        """Check if all required documents are present and verified"""
        required_docs = [doc for doc in self.documents if doc.required_for_approval]
        if not required_docs:
            return True  # No documents required
        
        verified_required = [doc for doc in required_docs if doc.verification_status == 'verified']
        return len(verified_required) == len(required_docs)

    @property
    def primary_receipt_document(self):
        """Get the primary receipt document"""
        receipt_docs = [doc for doc in self.documents if doc.document_type == 'receipt' and doc.is_original]
        return receipt_docs[0] if receipt_docs else None

    @property
    def effective_payment_amount(self):
        """Get effective payment amount after TDS and fees"""
        base_amount = self.amount or 0
        tds_amount = self.tds_amount or 0
        processing_fee = self.processing_fee or 0
        return float(base_amount) - float(tds_amount) - float(processing_fee)

    @property
    def total_manual_amount(self):
        """Total amount from manual payment methods"""
        return (
            (self.cash_amount or 0) + 
            (self.cheque_amount or 0) + 
            (self.bank_transfer_amount or 0) + 
            (self.upi_amount or 0)
        )

    @property
    def is_pending_approval(self):
        """Check if payment requires and is pending approval"""
        return self.requires_approval and self.workflow_status == 'pending_approval'

    @property
    def approval_hierarchy_level(self):
        """Get numeric approval level for sorting/comparison"""
        level_map = {
            'auto_approved': 0,
            'level_1': 1,
            'level_2': 2,
            'none': 99
        }
        return level_map.get(self.approval_level, 99)

    def validate_multi_method_amounts(self):
        """Validate that sum of method amounts equals total amount"""
        method_total = (
            (self.cash_amount or 0) + 
            (self.cheque_amount or 0) + 
            (self.bank_transfer_amount or 0) + 
            (self.upi_amount or 0)
        )
        
        # Allow small rounding differences
        return abs(float(self.amount) - float(method_total)) <= 0.01

    def get_primary_payment_method(self):
        """Get the primary payment method based on highest amount"""
        amounts = {
            'cash': self.cash_amount or 0,
            'cheque': self.cheque_amount or 0,
            'bank_transfer': self.bank_transfer_amount or 0,
            'upi': self.upi_amount or 0
        }
        
        return max(amounts, key=amounts.get) if any(amounts.values()) else 'unknown'

    def get_documents_by_type(self, document_type: str):
        """Get all documents of a specific type"""
        return [doc for doc in self.documents if doc.document_type == document_type]

    def __repr__(self):
        return f"<SupplierPayment {self.payment_id} - {self.amount} - {self.branch_name}>"

    def can_be_accessed_by_user(self, user):
        """Check if user can access this supplier payment - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'supplier', 'view', str(self.branch_id))
        except Exception:
            return False
        
    

class Inventory(Base, TimestampMixin, TenantMixin):
    """Inventory movement tracking"""
    __tablename__ = 'inventory'
    
    stock_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))

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
    
    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    medicine = relationship("Medicine", back_populates="inventory_entries")
    purchase_order = relationship("PurchaseOrderHeader")
    invoice = relationship("InvoiceHeader")
    patient = relationship("Patient")

    @property
    def branch_name(self):
        """Get branch name for display"""
        return self.branch.name if self.branch else 'Main Branch'
    
    def can_be_accessed_by_user(self, user):
        """Check if user can access this inventory record - uses permission service"""
        if not self.branch_id:
            return True
        
        try:
            from app.services.permission_service import has_branch_permission
            return has_branch_permission(user, 'inventory', 'view', str(self.branch_id))
        except Exception:
            return False

class GLTransaction(Base, TimestampMixin, TenantMixin):
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
    
    # Reference to source transactions
    invoice_header_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
    supplier_invoice_id = Column(UUID(as_uuid=True), ForeignKey('supplier_invoice.invoice_id'))
    
    # Source document tracking
    source_document_type = Column(String(30))  # 'SUPPLIER_INVOICE', 'SUPPLIER_PAYMENT', etc.
    source_document_id = Column(UUID(as_uuid=True))
    
    # Reversal tracking
    is_reversal = Column(Boolean, default=False)
    original_entry_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))

    # Relationships
    hospital = relationship("Hospital")
    gl_entries = relationship("GLEntry", back_populates="transaction", cascade="all, delete-orphan")
    invoice_ref = relationship("InvoiceHeader", foreign_keys=[invoice_header_id], back_populates="gl_transaction")
    supplier_invoice_ref = relationship("SupplierInvoice", foreign_keys=[supplier_invoice_id], back_populates="gl_transaction")
    gst_ledger_entries = relationship("GSTLedger", back_populates="gl_transaction")
    original_entry = relationship("GLTransaction", 
                                 foreign_keys=[original_entry_id], 
                                 remote_side=[transaction_id],
                                 backref="reversal_entries")

class GLEntry(Base, TimestampMixin, TenantMixin):
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
    posting_reference = Column(String(100))

    # For profitability analysis (Business Rule #11)
    profit_center = Column(String(50))  # Service, department, etc.
    cost_center = Column(String(50))  # Cost allocation
    
    # Source document tracking
    source_document_type = Column(String(30))  # 'SUPPLIER_INVOICE', 'SUPPLIER_PAYMENT', etc.
    source_document_id = Column(UUID(as_uuid=True))
    
    # Reversal tracking
    is_reversal = Column(Boolean, default=False)
    original_entry_id = Column(UUID(as_uuid=True), ForeignKey('gl_entry.entry_id'))

    # Relationships
    hospital = relationship("Hospital")
    transaction = relationship("GLTransaction", back_populates="gl_entries")
    account = relationship("ChartOfAccounts", back_populates="gl_entries")
    original_entry = relationship("GLEntry", 
                                 foreign_keys=[original_entry_id], 
                                 remote_side=[entry_id],
                                 backref="reversal_entries")

class GSTLedger(Base, TimestampMixin, TenantMixin):
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
    
    # Relationships
    hospital = relationship("Hospital")
    gl_transaction = relationship("GLTransaction", foreign_keys=[gl_reference], back_populates="gst_ledger_entries")


class PrescriptionInvoiceMap(Base, TimestampMixin, TenantMixin):
    """Maps prescription items to invoices for internal reference"""
    __tablename__ = 'prescription_invoice_maps'
    
    map_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    # Fix the table name in the foreign key reference
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'), nullable=False)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'), nullable=False)
    medicine_name = Column(String(100))
    batch = Column(String(50))
    expiry_date = Column(Date)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    invoice = relationship("InvoiceHeader", backref=backref("prescription_maps", lazy="dynamic"))
    medicine = relationship("Medicine")

class PatientAdvancePayment(Base, TimestampMixin, TenantMixin):
    """Tracks advance payments made by patients"""
    __tablename__ = 'patient_advance_payments'
    
    advance_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    
    # Payment details
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(DateTime(timezone=True), nullable=False)
    
    # Payment methods (matching PaymentDetail model structure)
    cash_amount = Column(Numeric(12, 2), default=0)
    credit_card_amount = Column(Numeric(12, 2), default=0)
    debit_card_amount = Column(Numeric(12, 2), default=0)
    upi_amount = Column(Numeric(12, 2), default=0)
    
    # Currency information (matching InvoiceHeader)
    currency_code = Column(String(3), default='INR')
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    
    # Payment details (matching PaymentDetail)
    card_number_last4 = Column(String(4))
    card_type = Column(String(20))
    upi_id = Column(String(50))
    reference_number = Column(String(50))
    
    # Status information
    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    
    # GL Reference (matching PaymentDetail)
    gl_entry_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # Available balance (tracked for quick reference)
    available_balance = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital")
    patient = relationship("Patient")
    gl_transaction = relationship("GLTransaction", foreign_keys=[gl_entry_id])
    adjustments = relationship("AdvanceAdjustment", back_populates="advance_payment")

class AdvanceAdjustment(Base, TimestampMixin, TenantMixin):
    """Tracks adjustments to patient advance payments"""
    __tablename__ = 'advance_adjustments'
    
    adjustment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    advance_id = Column(UUID(as_uuid=True), ForeignKey('patient_advance_payments.advance_id'), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payment_details.payment_id'))
    
    # Adjustment details
    amount = Column(Numeric(12, 2), nullable=False)
    adjustment_date = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text)
    
    # Relationships
    hospital = relationship("Hospital")
    advance_payment = relationship("PatientAdvancePayment", back_populates="adjustments")
    invoice = relationship("InvoiceHeader")
    # Specify which foreign key to use for this relationship
    payment = relationship("PaymentDetail", foreign_keys=[payment_id])

class LoyaltyPoint(Base, TimestampMixin, TenantMixin):
    """Tracks loyalty points earned by patients"""
    __tablename__ = 'loyalty_points'
    
    point_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    
    # Point details
    points = Column(Integer, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # earned, expired, redeemed
    reference_id = Column(String(50))  # Can be invoice_id, payment_id, etc.
    points_value = Column(Numeric(12, 2))  # Monetary value of points
    expiry_date = Column(Date)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    hospital = relationship("Hospital")
    patient = relationship("Patient")
    redemptions = relationship("LoyaltyRedemption", back_populates="loyalty_point")

class LoyaltyRedemption(Base, TimestampMixin, TenantMixin):
    """Tracks redemption of loyalty points"""
    __tablename__ = 'loyalty_redemptions'
    
    redemption_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    point_id = Column(UUID(as_uuid=True), ForeignKey('loyalty_points.point_id'))
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payment_details.payment_id'))
    
    # Redemption details
    points_redeemed = Column(Integer, nullable=False)
    amount_credited = Column(Numeric(12, 2), nullable=False)
    redemption_date = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital")
    patient = relationship("Patient")
    loyalty_point = relationship("LoyaltyPoint", back_populates="redemptions")
    # Specify which foreign key to use for this relationship
    payment = relationship("PaymentDetail", foreign_keys=[payment_id])


class ARSubledger(Base, TimestampMixin, TenantMixin):
    """Accounts Receivable Subledger"""
    __tablename__ = 'ar_subledger'
    
    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)  # Added branch_id
    
    # Transaction Identification
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    entry_type = Column(String(20), nullable=False)  # 'invoice', 'payment', 'adjustment', 'refund', 'advance'
    
    # Reference Information
    reference_id = Column(UUID(as_uuid=True), nullable=False)  # invoice_id, payment_id, or advance_id
    reference_type = Column(String(20), nullable=False)  # 'invoice', 'payment', or 'advance'
    reference_number = Column(String(50))  # Invoice number, payment reference, etc.
    
    # Patient Information
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    
    # Amount Information
    debit_amount = Column(Numeric(12, 2), default=0)
    credit_amount = Column(Numeric(12, 2), default=0)
    
    # Balance tracking
    current_balance = Column(Numeric(12, 2))  # Running balance for this patient
    
    # GL Reference
    gl_transaction_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")  # Added branch relationship
    patient = relationship("Patient")
    gl_transaction = relationship("GLTransaction")


class APSubledger(Base, TimestampMixin, TenantMixin):
    """Accounts Payable Subledger"""
    __tablename__ = 'ap_subledger'
    
    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)  # Added branch_id
    
    # Transaction Identification
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    entry_type = Column(String(20), nullable=False)  # 'invoice', 'payment', 'adjustment', 'advance'
    
    # Reference Information
    reference_id = Column(UUID(as_uuid=True), nullable=False)  # supplier_invoice_id, payment_id, or advance_id
    reference_type = Column(String(50), nullable=False)  # 'invoice', 'payment', or 'advance'
    reference_number = Column(String(50))  # Invoice number, payment reference, etc.
    
    # Supplier Information
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.supplier_id'), nullable=False)
    
    # Amount Information
    debit_amount = Column(Numeric(12, 2), default=0)
    credit_amount = Column(Numeric(12, 2), default=0)
    
    # Balance tracking
    current_balance = Column(Numeric(12, 2))  # Running balance for this supplier
    
    # GL Reference
    gl_transaction_id = Column(UUID(as_uuid=True), ForeignKey('gl_transaction.transaction_id'))
    
    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")  # Added branch relationship
    supplier = relationship("Supplier")
    gl_transaction = relationship("GLTransaction")

class PaymentDocument(Base, TimestampMixin, TenantMixin):
    """
    Document management for supplier payments
    EMR-compliant foundation for hospital-wide document management
    """
    __tablename__ = 'payment_documents'
    
    # === PRIMARY KEYS & RELATIONSHIPS ===
    document_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))
    payment_id = Column(UUID(as_uuid=True), ForeignKey('supplier_payment.payment_id'), nullable=False)
    
    # === DOCUMENT CLASSIFICATION ===
    document_type = Column(String(50), nullable=False)  # receipt, bank_statement, authorization, invoice_copy, cheque_image
    document_category = Column(String(30), default='payment')  # payment, approval, compliance, audit
    document_status = Column(String(20), default='uploaded')  # uploaded, verified, rejected, archived
    
    # === FILE INFORMATION ===
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)  # UUID-based secure filename
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    mime_type = Column(String(100))
    file_extension = Column(String(10))
    
    # === VERSION CONTROL ===
    is_original = Column(Boolean, default=True)
    parent_document_id = Column(UUID(as_uuid=True), ForeignKey('payment_documents.document_id'))
    version_number = Column(Integer, default=1)
    
    # === VERIFICATION & APPROVAL ===
    verified_by = Column(String(15), ForeignKey('users.user_id'))
    verified_at = Column(DateTime(timezone=True))
    verification_status = Column(String(20), default='pending')  # pending, verified, rejected
    verification_notes = Column(Text)
    
    # === BUSINESS METADATA ===
    description = Column(Text)
    required_for_approval = Column(Boolean, default=False)
    tags = Column(JSONB, default=list)  # For categorization and search
    
    # === ACCESS TRACKING ===
    last_accessed_at = Column(DateTime(timezone=True))
    last_accessed_by = Column(String(15), ForeignKey('users.user_id'))
    access_count = Column(Integer, default=0)
    
    # === RELATIONSHIPS ===
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    payment = relationship("SupplierPayment", back_populates="documents")
    verified_by_user = relationship("User", foreign_keys=[verified_by])
    last_accessed_by_user = relationship("User", foreign_keys=[last_accessed_by])
    
    # Self-referential for versions
    parent_document = relationship("PaymentDocument", foreign_keys=[parent_document_id], remote_side=[document_id])
    versions = relationship("PaymentDocument", foreign_keys=[parent_document_id], overlaps="parent_document")
    
    # === COMPUTED PROPERTIES ===
    @property
    def file_size_mb(self):
        """File size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    @property
    def is_current_version(self):
        """Check if this is the latest version"""
        return self.parent_document_id is None or not self.versions
    
    @property
    def age_days(self):
        """Days since document was created"""
        if self.created_at:
            return (datetime.now(timezone.utc) - self.created_at).days
        return 0
    
    @property
    def access_summary(self):
        """Summary of document access"""
        return {
            'total_accesses': self.access_count or 0,
            'last_access': self.last_accessed_at,
            'days_since_access': (datetime.now(timezone.utc) - self.last_accessed_at).days if self.last_accessed_at else None
        }
    
    # === BUSINESS METHODS ===
    def record_access(self, user_id: str):
        """Record document access for audit trail"""
        self.last_accessed_at = datetime.now(timezone.utc)
        self.last_accessed_by = user_id
        self.access_count = (self.access_count or 0) + 1
    
    def verify_document(self, verifier_id: str, status: str, notes: str = None):
        """Mark document as verified"""
        self.verification_status = status
        self.verified_by = verifier_id
        self.verified_at = datetime.now(timezone.utc)
        if notes:
            self.verification_notes = notes
    
    def create_version(self, new_file_path: str, reason: str, user_id: str):
        """Create a new version of this document"""
        # Mark current as non-original
        self.is_original = False
        
        # Create new version
        new_version = PaymentDocument(
            hospital_id=self.hospital_id,
            branch_id=self.branch_id,
            payment_id=self.payment_id,
            document_type=self.document_type,
            document_category=self.document_category,
            file_path=new_file_path,
            parent_document_id=self.document_id,
            version_number=(self.version_number or 0) + 1,
            created_by=user_id,
            is_original=True
        )
        return new_version
    
    def can_be_accessed_by_user(self, user):
        """Check if user can access this document - uses permission service"""
        if self.branch_id:
            try:
                from app.services.permission_service import has_branch_permission
                return has_branch_permission(user, 'payment_documents', 'view', str(self.branch_id))
            except Exception:
                return False
        return True
    
    def __repr__(self):
        return f"<PaymentDocument {self.document_id} - {self.document_type} - {self.original_filename}>"
    
class PaymentDocumentAccessLog(Base, TimestampMixin):
    """
    Audit trail for document access - EMR compliance requirement
    Tracks who accessed which documents when and how
    """
    __tablename__ = 'payment_document_access_log'
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    document_id = Column(UUID(as_uuid=True), ForeignKey('payment_documents.document_id'), nullable=False)
    user_id = Column(String(15), ForeignKey('users.user_id'), nullable=False)
    
    # Access details
    access_type = Column(String(20), nullable=False)  # view, download, print, email, delete
    access_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ip_address = Column(String(45))
    session_id = Column(String(100))
    
    # Relationships
    document = relationship("PaymentDocument")
    user = relationship("User")
    
    def __repr__(self):
        return f"<DocumentAccess {self.user_id} -> {self.document_id} ({self.access_type})>"
