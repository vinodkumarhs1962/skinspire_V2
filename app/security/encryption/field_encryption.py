# app/security/encryption/field_encryption.py

from typing import Any, Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
import json
from datetime import datetime, timezone
from base64 import b64encode, b64decode
import hashlib
from ..config import SecurityConfig

class FieldEncryption:
    """Handles field-level encryption for sensitive data"""
    
    def __init__(self, security_config: SecurityConfig):
        self.config = security_config
        self._encryption_keys: Dict[str, bytes] = {}
    
    def set_encryption_key(self, hospital_id: str, key: bytes) -> None:
        """Set encryption key for a hospital"""
        try:
            # Validate key format
            Fernet(key)
            # Store key
            self._encryption_keys[hospital_id] = key
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {str(e)}")
    
    def _get_key(self, hospital_id: str) -> Optional[bytes]:  # Changed method name here
        """Get encryption key for hospital"""
        return self._encryption_keys.get(hospital_id)
    
    def remove_encryption_key(self, hospital_id: str) -> None:
        """Remove encryption key for a hospital"""
        self._encryption_keys.pop(hospital_id, None)
    
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
    
 # app/security/encryption/field_encryption.py

def rotate_field_keys(self, hospital_id: str, new_key: bytes,
                     data_iterator: Any) -> Dict:
    """Rotate encryption keys for all encrypted fields"""
    try:
        old_key = self._get_key(hospital_id)
        if not old_key:
            raise ValueError("Old encryption key not found")
            
        # Validate new key
        Fernet(new_key)
        
        updated_count = 0
        failed_ids = []
        
        for item in data_iterator:
            try:
                # Re-encrypt each encrypted field
                for field_name in self.config.encrypted_fields:
                    if hasattr(item, field_name):
                        encrypted_value = getattr(item, field_name)
                        if encrypted_value:
                            # Decrypt with old key
                            decrypted = self.decrypt_field(
                                hospital_id,
                                field_name,
                                encrypted_value
                            )
                            # Encrypt with new key
                            self._encryption_keys[hospital_id] = new_key
                            new_encrypted = self.encrypt_field(
                                hospital_id,
                                field_name,
                                decrypted
                            )
                            setattr(item, field_name, new_encrypted)
                            
                updated_count += 1
                
            except Exception as e:
                # Use patient_id if available, otherwise use str(item)
                failed_id = getattr(item, 'patient_id', str(item))
                failed_ids.append(str(failed_id))
        
        # Update stored key
        self._encryption_keys[hospital_id] = new_key
        
        return {
            'status': 'success',
            'updated_count': updated_count,
            'failed_count': len(failed_ids),
            'failed_ids': failed_ids
        }
        
    except Exception as e:
        raise ValueError(f"Key rotation failed: {str(e)}")
    
    def verify_encryption(self, hospital_id: str, 
                         field_name: str) -> Dict:
        """Verify encryption for a field"""
        try:
            # Create test data
            test_value = {
                'test_data': 'verification',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Try encryption
            encrypted = self.encrypt_field(hospital_id, field_name, test_value)
            
            # Try decryption
            decrypted = self.decrypt_field(hospital_id, field_name, encrypted)
            
            # Verify
            verification_passed = (
                decrypted['test_data'] == test_value['test_data']
            )
            
            return {
                'status': 'success' if verification_passed else 'failed',
                'field_name': field_name,
                'encryption_enabled': self.config.encryption_enabled,
                'field_encrypted': self.config.is_field_encrypted(field_name)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'field_name': field_name,
                'error': str(e)
            }
    
  
    def _encode_value(self, value: Any) -> str:
        """Encode non-encrypted value"""
        return b64encode(json.dumps(value).encode()).decode()
    
    def _decode_value(self, encoded_value: str) -> Any:
        """Decode non-encrypted value"""
        return json.loads(b64decode(encoded_value).decode())