# Technical Implementation

## Table of Contents
1. [Core Components Implementation](#core-components)
2. [Database Schema](#database-schema)
3. [Security Layer](#security-layer)
4. [Integration Points](#integration-points)
5. [Error Handling](#error-handling)

## Core Components

### Field Encryption Implementation
```python
from cryptography.fernet import Fernet, InvalidToken
from base64 import b64encode, b64decode
import json
from typing import Any, Dict, Optional
from datetime import datetime, timezone

class FieldEncryption:
    """Core encryption handler for field-level encryption"""
    
    def __init__(self, security_config: SecurityConfig):
        self.config = security_config
        self._encryption_keys: Dict[str, bytes] = {}
    
    def set_encryption_key(self, hospital_id: str, key: bytes) -> None:
        """Set encryption key for a hospital"""
        try:
            # Validate key format
            Fernet(key)
            self._encryption_keys[hospital_id] = key
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {str(e)}")
    
    def _get_key(self, hospital_id: str) -> Optional[bytes]:
        """Get encryption key for hospital"""
        return self._encryption_keys.get(hospital_id)
    
    def encrypt_field(self, hospital_id: str, field_name: str, 
                     value: Any, additional_context: Dict = None) -> str:
        """Encrypt a field value"""
        if not self.config.encryption_enabled:
            return self._encode_value(value)
            
        if not self.config.is_field_encrypted(field_name):
            return self._encode_value(value)
            
        try:
            key = self._get_key(hospital_id)
            if not key:
                raise ValueError("Encryption key not found")
                
            f = Fernet(key)
            
            # Prepare value for encryption
            value_data = {
                'value': value,
                'field': field_name,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'context': additional_context
            }
            
            # Encrypt
            encrypted = f.encrypt(json.dumps(value_data).encode())
            return b64encode(encrypted).decode()
            
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt_field(self, hospital_id: str, field_name: str,
                     encrypted_value: str) -> Any:
        """Decrypt a field value"""
        if not self.config.encryption_enabled:
            return self._decode_value(encrypted_value)
            
        if not self.config.is_field_encrypted(field_name):
            return self._decode_value(encrypted_value)
            
        try:
            key = self._get_key(hospital_id)
            if not key:
                raise ValueError("Encryption key not found")
                
            f = Fernet(key)
            
            # Decrypt
            decrypted_data = json.loads(
                f.decrypt(b64decode(encrypted_value)).decode()
            )
            
            # Verify field name
            if decrypted_data['field'] != field_name:
                raise ValueError("Field name mismatch")
                
            return decrypted_data['value']
            
        except InvalidToken:
            raise ValueError("Invalid or corrupted encrypted value")
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    def _encode_value(self, value: Any) -> str:
        """Encode non-encrypted value"""
        return b64encode(json.dumps(value).encode()).decode()
    
    def _decode_value(self, encoded_value: str) -> Any:
        """Decode non-encrypted value"""
        return json.loads(b64decode(encoded_value).decode())

Security Configuration Implementation
class SecurityConfig:
    """Security configuration management"""
    
    def __init__(self):
        self.encryption_enabled = True
        self.encrypted_fields = {
            'medical_info': True,
            'personal_info': True
        }
        self.encryption_algorithm = 'AES-256'
        self.key_rotation_days = 90
        self.audit_enabled = True
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'SecurityConfig':
        """Create instance from dictionary"""
        instance = cls()
        for key, value in config_dict.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    def is_field_encrypted(self, field_name: str) -> bool:
        """Check if field should be encrypted"""
        return self.encrypted_fields.get(field_name, False)
    
    def get_encryption_settings(self) -> Dict:
        """Get encryption-specific settings"""
        return {
            'algorithm': self.encryption_algorithm,
            'enabled': self.encryption_enabled,
            'fields': self.encrypted_fields.copy()
        }

Database Schema
Base Models
from sqlalchemy import Column, String, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Base:
    """Base model for all database models"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)

class Hospital(Base):
    """Hospital model with encryption settings"""
    __tablename__ = 'hospitals'
    
    name = Column(String, nullable=False)
    encryption_enabled = Column(Boolean, default=True)
    encryption_config = Column(JSON)
    security_settings = Column(JSON)

class EncryptionKey(Base):
    """Encryption key management"""
    __tablename__ = 'encryption_keys'
    
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.id'))
    key_version = Column(Integer)
    active = Column(Boolean, default=True)
    rotated_at = Column(DateTime(timezone=True))

Security Models
class SecurityAudit(Base):
    """Security audit logging"""
    __tablename__ = 'security_audits'
    
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.id'))
    event_type = Column(String)
    details = Column(JSON)
    user_id = Column(UUID(as_uuid=True))
    ip_address = Column(String)

class SecurityEvent(Base):
    """Security event tracking"""
    __tablename__ = 'security_events'
    
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.id'))
    event_type = Column(String)
    severity = Column(String)
    details = Column(JSON)

Security Layer
Audit Logging
class AuditLogger:
    """Security audit logging implementation"""
    
    def __init__(self, session):
        self.session = session
    
    def log_security_event(self, 
                          hospital_id: str,
                          event_type: str,
                          details: Dict,
                          user_id: Optional[str] = None):
        """Log security event"""
        audit_entry = SecurityAudit(
            hospital_id=hospital_id,
            event_type=event_type,
            details=details,
            user_id=user_id,
            ip_address=request.remote_addr
        )
        self.session.add(audit_entry)
        self.session.commit()

Error Handling
class SecurityException(Exception):
    """Base security exception"""
    pass

class EncryptionError(SecurityException):
    """Encryption-specific errors"""
    pass

class KeyManagementError(SecurityException):
    """Key management errors"""
    pass

def handle_security_error(e: Exception, context: Dict):
    """Central security error handler"""
    logger.error(f"Security error: {str(e)}", extra={
        'context': context,
        'error_type': type(e).__name__
    })
    
    if isinstance(e, EncryptionError):
        handle_encryption_error(e, context)
    elif isinstance(e, KeyManagementError):
        handle_key_error(e, context)
    else:
        handle_general_security_error(e, context)

Integration Points
Application Integration
class SecurityMiddleware:
    """Security middleware for request handling"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        """Process each request"""
        try:
            self.setup_security_context(environ)
            return self.app(environ, start_response)
        finally:
            self.cleanup_security_context()

Session Integration
class SecureSessionManager:
    """Secure session management"""
    
    def __init__(self, security_config):
        self.config = security_config
        self.encryption = FieldEncryption(security_config)
    
    def create_session(self, user_id: str, hospital_id: str) -> str:
        """Create new secure session"""
        session_data = {
            'user_id': user_id,
            'hospital_id': hospital_id,
            'created_at': datetime.utcnow().isoformat()
        }
        return self.encryption.encrypt_field(
            hospital_id,
            'session_data',
            session_data
        )

