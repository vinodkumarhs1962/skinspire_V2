# app/models/transaction.py

    
from werkzeug.security import generate_password_hash, check_password_hash    
from sqlalchemy import text
from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid
from flask import current_app
from flask_login import UserMixin


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


    # def set_password(self, password):
    #     """
    #     Explicitly hash password using werkzeug
    #     Use this method when creating or updating user passwords in application code.
    #     This provides a reliable alternative to the database trigger-based approach.
        
    #     """
    #     from werkzeug.security import generate_password_hash
    #     self.password_hash = generate_password_hash(password)
    # # Keep trigger-based solution as a commented option
    # # Setting password_hash directly will still work with database triggers if properly configured
    # # Example: user.password_hash = 'plaintext_password'  # Will be hashed by trigger

    # def check_password(self, password):
    #     """
    #     Verify user password - simplified approach that works both in and outside of app context
    #     """
    #     if not self.password_hash or not password:
    #         return False
            
    #     # First try with werkzeug's check_password_hash which doesn't need app context
    #     try:
    #         from werkzeug.security import check_password_hash
    #         return check_password_hash(self.password_hash, password)
    #     except Exception as e:
    #         # If werkzeug fails, try fallback methods
    #         pass
        
    #     # Try direct comparison for plaintext passwords (in test environments)
    #     if self.password_hash == password:
    #         return True
        
    #     # Last resort for test environments - mock hashes
    #     if '$mock_hash_' in self.password_hash and self.password_hash.endswith(password):
    #         return True
        
    #     return False

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