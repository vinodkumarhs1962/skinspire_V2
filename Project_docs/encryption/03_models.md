# Method Documentation for Skinspire Encryption System

## Introduction
This document provides comprehensive documentation for all methods in the Skinspire encryption system. Each method is documented with its purpose, parameters, return values, exceptions, and usage examples.

## Field Encryption Methods

### set_encryption_key
This method establishes or updates the encryption key for a specific hospital.

```python
def set_encryption_key(self, hospital_id: str, key: bytes) -> None:

Parameters:

hospital_id (str): Unique identifier for the hospital
key (bytes): Fernet-compatible encryption key

Exceptions:

ValueError: Raised if the key format is invalid
SecurityException: Raised if key storage fails

Usage Example:
pythonCopyencryption_handler = FieldEncryption(security_config)
new_key = Fernet.generate_key()
encryption_handler.set_encryption_key(
    hospital_id="hospital_123",
    key=new_key
)

Security Considerations:

Key validation occurs before storage
Previous key is securely overwritten
Operation is logged in security audit

encrypt_field
This method encrypts sensitive field data using hospital-specific encryption.
pythonCopydef encrypt_field(
    self, 
    hospital_id: str, 
    field_name: str,
    value: Any,
    additional_context: Dict = None
) -> str:
Parameters:

hospital_id (str): Unique identifier for the hospital
field_name (str): Name of the field being encrypted
value (Any): Data to encrypt
additional_context (Dict, optional): Additional metadata

Returns:

str: Base64 encoded encrypted value

Exceptions:

ValueError: If encryption key is not found
EncryptionError: If encryption operation fails

Usage Example:
pythonCopymedical_data = {
    "diagnosis": "Patient diagnosis",
    "treatment": "Treatment plan"
}

encrypted_data = encryption_handler.encrypt_field(
    hospital_id="hospital_123",
    field_name="medical_info",
    value=medical_data
)
decrypt_field
This method decrypts previously encrypted field data.
pythonCopydef decrypt_field(
    self,
    hospital_id: str,
    field_name: str,
    encrypted_value: str
) -> Any:
Parameters:

hospital_id (str): Unique identifier for the hospital
field_name (str): Name of the field being decrypted
encrypted_value (str): Base64 encoded encrypted data

Returns:

Any: Original decrypted value

Exceptions:

ValueError: If encryption key is not found
InvalidToken: If encrypted value is corrupted
DecryptionError: If decryption operation fails

Usage Example:
pythonCopydecrypted_data = encryption_handler.decrypt_field(
    hospital_id="hospital_123",
    field_name="medical_info",
    encrypted_value=encrypted_medical_data
)
Security Configuration Methods
from_dict
Creates a security configuration instance from a dictionary.
pythonCopy@classmethod
def from_dict(cls, config_dict: Dict) -> SecurityConfig:
Parameters:

config_dict (Dict): Configuration settings dictionary

Returns:

SecurityConfig: Configured instance

Usage Example:
pythonCopyconfig = SecurityConfig.from_dict({
    'encryption_enabled': True,
    'encrypted_fields': {
        'medical_info': True,
        'personal_info': True
    }
})
is_field_encrypted
Determines if a specific field should be encrypted.
pythonCopydef is_field_encrypted(self, field_name: str) -> bool:
Parameters:

field_name (str): Name of the field to check

Returns:

bool: True if field should be encrypted

Usage Example:
pythonCopyif security_config.is_field_encrypted('medical_info'):
    # Handle encrypted field
Audit Logging Methods
log_security_event
Records security-related events in the audit log.
pythonCopydef log_security_event(
    self,
    hospital_id: str,
    event_type: str,
    details: Dict,
    user_id: Optional[str] = None
) -> None:
Parameters:

hospital_id (str): Hospital identifier
event_type (str): Type of security event
details (Dict): Event details
user_id (Optional[str]): Associated user identifier

Usage Example:
pythonCopyaudit_logger.log_security_event(
    hospital_id="hospital_123",
    event_type="key_rotation",
    details={
        "previous_key_id": "key_123",
        "new_key_id": "key_124"
    }
)
Error Handling Methods
handle_security_error
Centralized security error handling method.
pythonCopydef handle_security_error(
    e: Exception,
    context: Dict
) -> None:
Parameters:

e (Exception): The caught exception
context (Dict): Error context information

Usage Example:
pythonCopytry:
    encryption_handler.encrypt_field(...)
except Exception as e:
    handle_security_error(e, {
        'operation': 'encrypt',
        'hospital_id': hospital_id
    })
Integration Methods
create_session
Creates a new secure session with encrypted data.
pythonCopydef create_session(
    self,
    user_id: str,
    hospital_id: str
) -> str:
Parameters:

user_id (str): User identifier
hospital_id (str): Hospital identifier

Returns:

str: Encrypted session token

Usage Example:
pythonCopysession_manager = SecureSessionManager(security_config)
session_token = session_manager.create_session(
    user_id="user_123",
    hospital_id="hospital_123"
)
Best Practices
When using these methods, consider the following practices:

Error Handling

Always wrap encryption operations in try-except blocks
Use appropriate error types for different failures
Log security events appropriately


Data Validation

Validate input data before encryption
Verify field names against configuration
Check hospital ID validity


Performance Considerations

Cache encryption handlers when possible
Use batch operations for multiple items
Monitor operation timing


Security

Never log sensitive data
Rotate keys regularly
Validate all inputs


Maintenance

Keep configuration updated
Monitor audit logs
Review security events regularly



Next Steps
For implementation details of specific scenarios, refer to 04_testing.md which contains comprehensive testing examples.
Copy