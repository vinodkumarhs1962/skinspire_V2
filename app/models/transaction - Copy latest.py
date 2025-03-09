    # app/models/transaction.py

from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from .base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid

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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

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




