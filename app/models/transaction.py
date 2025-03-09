# app/models/transaction.py

    
from werkzeug.security import generate_password_hash, check_password_hash    
from sqlalchemy import text
from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid
from flask import current_app


class User(Base, TimestampMixin, SoftDeleteMixin):
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

# Add the set_password method to the User class in transaction.py

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