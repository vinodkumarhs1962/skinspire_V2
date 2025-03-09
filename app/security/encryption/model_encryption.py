# app/security/encryption/model_encryption.py

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session
from sqlalchemy.event import listen
from flask import current_app
from typing import Any, Dict, List

class EncryptedFieldsMixin:
    """Mixin to add encryption capability to SQLAlchemy models"""
    
    # List of fields to encrypt - override in model
    encrypted_fields: List[str] = []
    
    @declared_attr
    def __init__(cls):
        """Initialize encryption events"""
        def encrypt_fields(mapper, connection, target):
            """Encrypt fields before save"""
            if not hasattr(target, 'hospital_id'):
                return
                
            security = current_app.get_security()
            
            for field_name in cls.encrypted_fields:
                value = getattr(target, field_name, None)
                if value is not None:
                    encrypted = security.encrypt_field(
                        target.hospital_id,
                        field_name,
                        value
                    )
                    setattr(target, field_name, encrypted)
        
        def decrypt_fields(target, context):
            """Decrypt fields after load"""
            if not hasattr(target, 'hospital_id'):
                return
                
            security = current_app.get_security()
            
            for field_name in cls.encrypted_fields:
                value = getattr(target, field_name, None)
                if value is not None:
                    decrypted = security.decrypt_field(
                        target.hospital_id,
                        field_name,
                        value
                    )
                    setattr(target, field_name, decrypted)
        
        # Register event listeners
        listen(cls, 'before_insert', encrypt_fields)
        listen(cls, 'before_update', encrypt_fields)
        listen(cls, 'load', decrypt_fields)

class EncryptedModel(EncryptedFieldsMixin):
    """Base class for models with encrypted fields"""
    
    @classmethod
    def bulk_encrypt(cls, session: Session, hospital_id: str) -> Dict:
        """Bulk encrypt all records"""
        security = current_app.get_security()
        
        updated = 0
        failed = []
        
        for record in session.query(cls).filter_by(hospital_id=hospital_id):
            try:
                for field_name in cls.encrypted_fields:
                    value = getattr(record, field_name, None)
                    if value is not None:
                        encrypted = security.encrypt_field(
                            hospital_id,
                            field_name,
                            value
                        )
                        setattr(record, field_name, encrypted)
                updated += 1
            except Exception as e:
                failed.append({
                    'id': str(record.id),
                    'error': str(e)
                })
        
        session.commit()
        
        return {
            'model': cls.__name__,
            'updated': updated,
            'failed': failed
        }
    
    @classmethod
    def bulk_decrypt(cls, session: Session, hospital_id: str) -> Dict:
        """Bulk decrypt all records"""
        security = current_app.get_security()
        
        decrypted = 0
        failed = []
        
        for record in session.query(cls).filter_by(hospital_id=hospital_id):
            try:
                for field_name in cls.encrypted_fields:
                    value = getattr(record, field_name, None)
                    if value is not None:
                        decrypted_value = security.decrypt_field(
                            hospital_id,
                            field_name,
                            value
                        )
                        setattr(record, field_name, decrypted_value)
                decrypted += 1
            except Exception as e:
                failed.append({
                    'id': str(record.id),
                    'error': str(e)
                })
        
        return {
            'model': cls.__name__,
            'decrypted': decrypted,
            'failed': failed
        }

# Example usage:
"""
class Patient(Base, EncryptedModel):
    __tablename__ = 'patients'
    
    encrypted_fields = ['medical_info', 'personal_info']
    
    id = Column(Integer, primary_key=True)
    hospital_id = Column(String, nullable=False)
    medical_info = Column(JSON)
    personal_info = Column(JSON)
"""