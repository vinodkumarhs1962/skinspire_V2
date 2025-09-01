# Testing Guide for Skinspire Encryption System

## Introduction

The testing framework for the Skinspire encryption system ensures the security, reliability, and correctness of all encryption operations. This document provides comprehensive guidance on testing the encryption system, including setup procedures, test cases, and validation methods.

## Test Environment Setup

The testing environment requires proper configuration to ensure consistent and reliable test execution. Initialize the test environment with the following setup:

```python
# tests/conftest.py
import pytest
from app.models import Hospital
from app.security.encryption.field_encryption import FieldEncryption
from app.security.config import SecurityConfig

@pytest.fixture(scope='session')
def app():
    """Create test application instance"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.get_database_url_for_env('testing')
    return app

@pytest.fixture(scope='session')
def security_config():
    """Provide test security configuration"""
    return SecurityConfig.from_dict({
        'encryption_enabled': True,
        'encrypted_fields': {
            'medical_info': True,
            'personal_info': True
        }
    })

@pytest.fixture(scope='session')
def test_hospital(session):
    """Provide test hospital instance"""
    hospital = session.query(Hospital).filter_by(
        license_no="TEST123"
    ).first()
    if not hospital:
        raise ValueError("Test hospital not found")
    return hospital
Comprehensive Test Cases
Basic Encryption Tests
The following test cases verify the fundamental encryption operations:
pythonCopyclass TestEncryption:
    """Test suite for encryption functionality"""
    
    def test_encryption_configuration(self, session, test_hospital):
        """Verify encryption configuration"""
        hospital = session.query(Hospital).get(test_hospital.hospital_id)
        assert hospital is not None
        
        security_config = SecurityConfig.from_dict({
            'encryption_enabled': True,
            'encryption_algorithm': 'AES-256',
            'encrypted_fields': {
                'medical_info': True,
                'personal_info': True
            }
        })
        
        encryption_handler = FieldEncryption(security_config)
        test_key = Fernet.generate_key()
        encryption_handler.set_encryption_key(str(hospital.hospital_id), test_key)
        
        assert security_config.encryption_enabled
        assert security_config.is_field_encrypted('medical_info')

    def test_patient_data_encryption(self, session, test_hospital):
        """Test patient data encryption process"""
        security_config = SecurityConfig.from_dict({
            'encryption_enabled': True,
            'encrypted_fields': {
                'medical_info': True,
                'personal_info': True
            }
        })
        encryption_handler = FieldEncryption(security_config)
        test_key = Fernet.generate_key()
        encryption_handler.set_encryption_key(str(test_hospital.hospital_id), test_key)

        test_data = {
            "diagnosis": "Test diagnosis",
            "treatment": "Test treatment plan",
            "notes": "Confidential medical information"
        }

        encrypted_data = encryption_handler.encrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            test_data
        )

        decrypted_data = encryption_handler.decrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            encrypted_data
        )

        assert isinstance(decrypted_data, dict)
        assert decrypted_data["diagnosis"] == test_data["diagnosis"]
Key Management Tests
Tests for encryption key management ensure proper handling of cryptographic keys:
pythonCopydef test_key_rotation(self, session, test_hospital):
    """Test encryption key rotation process"""
    security_config = SecurityConfig.from_dict({
        'encryption_enabled': True,
        'encrypted_fields': {
            'medical_info': True,
            'personal_info': True
        }
    })
    encryption_handler = FieldEncryption(security_config)
    
    initial_key = Fernet.generate_key()
    encryption_handler.set_encryption_key(str(test_hospital.hospital_id), initial_key)
    
    test_data = {
        "test": "Sensitive medical information",
        "timestamp": datetime.now().isoformat()
    }
    
    encrypted_data = encryption_handler.encrypt_field(
        str(test_hospital.hospital_id),
        'medical_info',
        test_data
    )
    
    new_key = Fernet.generate_key()
    encryption_handler.set_encryption_key(str(test_hospital.hospital_id), new_key)
    
    new_encrypted_data = encryption_handler.encrypt_field(
        str(test_hospital.hospital_id),
        'medical_info',
        test_data
    )
    
    assert encrypted_data != new_encrypted_data
Error Handling Tests
Tests that verify proper handling of error conditions:
pythonCopydef test_encryption_error_handling(self, session, test_hospital):
    """Test error handling in encryption operations"""
    security_config = SecurityConfig.from_dict({
        'encryption_enabled': True,
        'encrypted_fields': {
            'medical_info': True
        }
    })
    encryption_handler = FieldEncryption(security_config)
    
    with pytest.raises(ValueError):
        encryption_handler.encrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            "test data"
        )

    with pytest.raises(ValueError):
        encryption_handler.decrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            "invalid_encrypted_data"
        )
Test Data Management
The testing framework requires careful management of test data. Consider these principles:

Data Isolation: Each test should work with its own data set to prevent interference between tests.
Data Cleanup: Tests should clean up their data after execution to maintain a consistent test environment.
Test Data Generation: Use fixtures to generate consistent test data across test runs.

Validation Procedures
When validating encryption operations, verify the following aspects:

Data Integrity: Ensure decrypted data matches the original input exactly.
Key Management: Verify proper handling of encryption keys throughout their lifecycle.
Error Conditions: Confirm appropriate error handling for invalid inputs and error conditions.
Performance Impact: Monitor encryption/decryption operation timing to ensure acceptable performance.

Integration Testing
Test the encryption system's integration with other components:
pythonCopydef test_patient_record_integration(self, session, test_hospital):
    """Test integration with patient records"""
    security_config = SecurityConfig.from_dict({
        'encryption_enabled': True,
        'encrypted_fields': {
            'medical_info': True,
            'personal_info': True
        }
    })
    encryption_handler = FieldEncryption(security_config)
    test_key = Fernet.generate_key()
    encryption_handler.set_encryption_key(str(test_hospital.hospital_id), test_key)

    patient = Patient(
        hospital_id=test_hospital.hospital_id,
        medical_info=encryption_handler.encrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            {"diagnosis": "Test condition"}
        )
    )
    
    session.add(patient)
    session.commit()
    
    retrieved_patient = session.query(Patient).get(patient.id)
    decrypted_info = encryption_handler.decrypt_field(
        str(test_hospital.hospital_id),
        'medical_info',
        retrieved_patient.medical_info
    )
    
    assert decrypted_info["diagnosis"] == "Test condition"
Performance Testing
Monitor the performance impact of encryption operations:
pythonCopydef test_encryption_performance(self, session, test_hospital):
    """Test encryption performance metrics"""
    security_config = SecurityConfig.from_dict({
        'encryption_enabled': True,
        'encrypted_fields': {
            'medical_info': True
        }
    })
    encryption_handler = FieldEncryption(security_config)
    test_key = Fernet.generate_key()
    encryption_handler.set_encryption_key(str(test_hospital.hospital_id), test_key)

    start_time = time.time()
    for _ in range(100):
        encrypted_data = encryption_handler.encrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            {"test": "data"}
        )
    end_time = time.time()
    
    average_time = (end_time - start_time) / 100
    assert average_time < 0.01  # Encryption should take less than 10ms on average
Next Steps
For detailed information about key rotation implementation and testing, refer to 05_key_rotation.md.