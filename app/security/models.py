# app/security/models.py

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..extensions import db

class AuditLog(db.Model):
    """Audit trail for security events"""
    __tablename__ = 'security_audit_logs'
    
    id = Column(Integer, primary_key=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.id'))
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    event_type = Column(String(50), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    status = Column(String(20))
    
    hospital = relationship("Hospital", backref="audit_logs")
    user = relationship("User", backref="audit_logs")

class SecurityConfiguration(db.Model):
    """Hospital-specific security configuration"""
    __tablename__ = 'security_configurations'
    
    id = Column(Integer, primary_key=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.id'), unique=True)
    settings = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    
    hospital = relationship("Hospital", backref="security_config")

class PasswordHistory(db.Model):
    """Track password history for password reuse prevention"""
    __tablename__ = 'password_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    password_hash = Column(String(255), nullable=False)
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", backref="password_history")

class UserSession(db.Model):
    """Active user sessions"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.id'))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_activity = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", backref="sessions")
    hospital = relationship("Hospital", backref="user_sessions")

class SecurityEvent(db.Model):
    """Security-related events (login attempts, password changes, etc.)"""
    __tablename__ = 'security_events'
    
    id = Column(Integer, primary_key=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    details = Column(JSON)
    ip_address = Column(String(45))
    status = Column(String(20))
    
    user = relationship("User", backref="security_events")
    hospital = relationship("Hospital", backref="security_events")