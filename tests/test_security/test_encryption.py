# tests/test_security/test_encryption.py
# pytest tests/test_security/test_encryption.py
#   working test 3.3.25

import pytest
import json
from datetime import datetime
from app.models.master import Patient, Hospital
from app.security.encryption.field_encryption import FieldEncryption
from app.security.config import SecurityConfig
from app.config.settings import settings
from cryptography.fernet import Fernet

class TestEncryption:
    """Test suite for data encryption functionality"""

    def test_encryption_configuration(self, session, test_hospital):
        """Test encryption configuration"""
        # hospital = session.query(Hospital).get(test_hospital.hospital_id)
        hospital = session.get(Hospital, test_hospital.hospital_id)
        assert hospital is not None, "Hospital not found"
        
        # Create security config for testing
        security_config = SecurityConfig.from_dict({
            'encryption_enabled': True,
            'encryption_algorithm': 'AES-256',
            'encrypted_fields': {
                'medical_info': True,
                'personal_info': True
            }
        })
        
        encryption_handler = FieldEncryption(security_config)
        # Generate and set a test key
        test_key = Fernet.generate_key()
        encryption_handler.set_encryption_key(str(hospital.hospital_id), test_key)
        
        # Test basic configuration
        assert security_config.encryption_enabled, "Encryption should be enabled"
        assert security_config.is_field_encrypted('medical_info'), "Medical info should be marked for encryption"

    def test_patient_data_encryption(self, session, test_hospital):
        """Test patient data encryption"""
        # Setup encryption
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

        # Delete existing test patient if exists
        session.query(Patient).filter_by(
            hospital_id=test_hospital.hospital_id,
            mrn="TEST001"
        ).delete()
        session.commit()

        # Create test data
        test_medical_info = {
            "diagnosis": "Test diagnosis",
            "treatment": "Test treatment plan",
            "notes": "Test medical information - needs encryption"
        }

        # First encrypt the medical info
        encrypted_info = encryption_handler.encrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            test_medical_info  # Pass the dict directly, let encrypt_field handle serialization
        )

        # Create new patient with encrypted data
        patient = Patient(
            hospital_id=test_hospital.hospital_id,
            mrn="TEST001",
            personal_info={
                "first_name": "Test",
                "last_name": "Patient",
                "dob": "1990-01-01",
                "gender": "M"
            },
            medical_info=encrypted_info,
            contact_info={
                "email": "test@example.com",
                "phone": "1234567890"
            }
        )
        session.add(patient)
        session.commit()
        session.refresh(patient)

        # Test decryption
        decrypted_info = encryption_handler.decrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            patient.medical_info
        )

        # Verify decrypted data
        assert isinstance(decrypted_info, dict), "Decrypted data should be a dictionary"
        assert "diagnosis" in decrypted_info, "Should contain medical information"
        assert decrypted_info["diagnosis"] == test_medical_info["diagnosis"], "Original and decrypted data should match"

    def test_encryption_key_rotation(self, session, test_hospital):
        """Test encryption key rotation"""
        # Setup encryption
        security_config = SecurityConfig.from_dict({
            'encryption_enabled': True,
            'encrypted_fields': {
                'medical_info': True,
                'personal_info': True
            }
        })
        encryption_handler = FieldEncryption(security_config)
        
        # Generate and set initial key
        initial_key = Fernet.generate_key()
        encryption_handler.set_encryption_key(str(test_hospital.hospital_id), initial_key)
        
        # Test data
        test_data = {
            "test": "Sensitive medical information",
            "timestamp": datetime.now().isoformat()
        }
        
        # First encryption
        encrypted_data = encryption_handler.encrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            test_data
        )
        
        # Verify first encryption
        decrypted_data = encryption_handler.decrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            encrypted_data
        )
        assert decrypted_data["test"] == test_data["test"], "Initial encryption/decryption should work"
        
        # New key
        new_key = Fernet.generate_key()
        
        # Use the existing rotate or re-encrypt method from your class
        encryption_handler.set_encryption_key(str(test_hospital.hospital_id), new_key)
        
        # Test encryption with new key
        new_encrypted_data = encryption_handler.encrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            test_data
        )
        
        # Verify new encryption
        new_decrypted_data = encryption_handler.decrypt_field(
            str(test_hospital.hospital_id),
            'medical_info',
            new_encrypted_data
        )
        assert new_decrypted_data["test"] == test_data["test"], "Encryption should work with rotated key"