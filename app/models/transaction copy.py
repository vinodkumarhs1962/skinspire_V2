# app/models/transaction.py

    
from werkzeug.security import generate_password_hash, check_password_hash    
from sqlalchemy import text
from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, DateTime   
from sqlalchemy.types import Text  # Alternative import
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid
from .base import TenantMixin  # Explicitly import TenantMixin
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

# Add VerificationCode model
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

# Add StaffApprovalRequest model
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