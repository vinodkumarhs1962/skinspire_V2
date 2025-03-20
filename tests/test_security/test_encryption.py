# tests/test_security/test_encryption.py
# pytest tests/test_security/test_encryption.py

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import logging
import os
import traceback
from unittest import mock
from datetime import datetime
from app.models.master import Patient, Hospital
from app.security.encryption.field_encryption import FieldEncryption
from app.security.config import SecurityConfig
from cryptography.fernet import Fernet
from app.services.database_service import get_db_session, set_debug_mode

# Set up logging for tests
logger = logging.getLogger(__name__)

# Check if running in integration or unit test mode
INTEGRATION_MODE = os.environ.get('INTEGRATION_TEST', '1') == '1'

class TestEncryption:
    """Test suite for data encryption functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        logger.info(f"Starting encryption test in {'INTEGRATION' if INTEGRATION_MODE else 'UNIT TEST'} mode")
        
        # Enable SQL query logging in integration mode
        if INTEGRATION_MODE:
            set_debug_mode(True)
            
        # Store test entities for cleanup
        self.test_entities = []
    
    def teardown_method(self):
        """Teardown after each test method"""
        # Disable SQL query logging
        if INTEGRATION_MODE:
            set_debug_mode(False)
            
            # Clean up any test entities
            logger.info("Cleaning up test data")
            try:
                with get_db_session() as session:
                    for entity in self.test_entities:
                        try:
                            if isinstance(entity, Patient):
                                db_entity = session.query(Patient).filter_by(
                                    hospital_id=entity.hospital_id,
                                    mrn=entity.mrn
                                ).first()
                                if db_entity:
                                    session.delete(db_entity)
                            else:
                                logger.warning(f"Unknown entity type for cleanup: {type(entity)}")
                        except Exception as e:
                            logger.warning(f"Cleanup error: {str(e)}")
            except Exception as e:
                logger.error(f"Failed to clean up test data: {str(e)}")
        
        logger.info("Test completed")
    
    def debug_entity(self, entity, prefix=""):
        """Print all attributes of an entity"""
        if entity is None:
            logger.debug(f"{prefix} Entity is None")
            return
        
        logger.debug(f"{prefix} Entity of type {type(entity).__name__}:")
        for attr in dir(entity):
            if not attr.startswith("_") and not callable(getattr(entity, attr)):
                try:
                    value = getattr(entity, attr)
                    logger.debug(f"{prefix}  - {attr}: {value}")
                except Exception as e:
                    logger.debug(f"{prefix}  - {attr}: <Error accessing: {str(e)}>")

    def test_encryption_configuration(self, test_hospital):
        """Test encryption configuration"""
        logger.info("Testing encryption configuration")
        
        try:
            if INTEGRATION_MODE:
                # Integration test - use real database
                with get_db_session() as session:
                    logger.debug(f"Querying hospital with ID: {test_hospital.hospital_id}")
                    # Get hospital using SQLAlchemy 2.0 style query
                    hospital = session.get(Hospital, test_hospital.hospital_id)
                    assert hospital is not None, "Hospital not found"
                    logger.debug(f"Retrieved hospital: {hospital.name}")
                    
                    # Create security config for testing
                    logger.debug("Creating security configuration")
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
                    logger.debug("Setting encryption key")
                    encryption_handler.set_encryption_key(str(hospital.hospital_id), test_key)
                    
                    # Test basic configuration
                    logger.debug("Verifying security configuration")
                    assert security_config.encryption_enabled, "Encryption should be enabled"
                    assert security_config.is_field_encrypted('medical_info'), "Medical info should be marked for encryption"
                    logger.info("Encryption configuration test passed")
            else:
                # Unit test - mock database operations
                with mock.patch('app.services.database_service.get_db_session') as mock_db_session:
                    logger.debug("Setting up mocks for database session")
                    # Mock hospital object
                    mock_hospital = mock.MagicMock(spec=Hospital)
                    mock_hospital.hospital_id = test_hospital.hospital_id
                    mock_hospital.name = "Test Hospital"
                    
                    # Setup mock session
                    mock_session = mock.MagicMock()
                    mock_db_session.return_value.__enter__.return_value = mock_session
                    mock_session.get.return_value = mock_hospital
                    
                    logger.debug("Testing with mock session")
                    with get_db_session() as session:
                        hospital = session.get(Hospital, test_hospital.hospital_id)
                        logger.debug(f"Retrieved mock hospital: {hospital.name}")
                    
                    # Create security config for testing
                    logger.debug("Creating security configuration")
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
                    logger.debug("Setting encryption key")
                    encryption_handler.set_encryption_key(str(mock_hospital.hospital_id), test_key)
                    
                    # Test basic configuration
                    logger.debug("Verifying security configuration")
                    assert security_config.encryption_enabled, "Encryption should be enabled"
                    assert security_config.is_field_encrypted('medical_info'), "Medical info should be marked for encryption"
                    logger.info("Encryption configuration test passed (mock mode)")
                    
                    # Verify mock calls
                    logger.debug("Verifying mock calls")
                    mock_session.get.assert_called_with(Hospital, test_hospital.hospital_id)
        except Exception as e:
            logger.error(f"Error in test_encryption_configuration: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def test_patient_data_encryption(self, test_hospital):
        """Test patient data encryption"""
        logger.info("Testing patient data encryption")
        
        # Setup encryption
        logger.debug("Creating security configuration")
        security_config = SecurityConfig.from_dict({
            'encryption_enabled': True,
            'encrypted_fields': {
                'medical_info': True,
                'personal_info': True
            }
        })
        encryption_handler = FieldEncryption(security_config)
        test_key = Fernet.generate_key()
        logger.debug("Setting encryption key")
        encryption_handler.set_encryption_key(str(test_hospital.hospital_id), test_key)

        # Test data
        test_medical_info = {
            "diagnosis": "Test diagnosis",
            "treatment": "Test treatment plan",
            "notes": "Test medical information - needs encryption"
        }
        
        logger.debug(f"Test medical info: {test_medical_info}")

        try:
            if INTEGRATION_MODE:
                # Integration test - use real database
                # For patient data tests we need to persist changes
                with get_db_session() as session:
                    logger.debug("Ensuring test patient doesn't already exist")
                    # Delete existing test patient if exists
                    existing = session.query(Patient).filter_by(
                        hospital_id=test_hospital.hospital_id,
                        mrn="TEST001"
                    ).first()
                    
                    if existing:
                        logger.debug(f"Found existing test patient, deleting: {existing.mrn}")
                        session.delete(existing)
                        session.flush()

                    # First encrypt the medical info
                    logger.debug("Encrypting medical information")
                    encrypted_info = encryption_handler.encrypt_field(
                        str(test_hospital.hospital_id),
                        'medical_info',
                        test_medical_info
                    )
                    logger.debug(f"Encrypted info type: {type(encrypted_info)}")

                    logger.debug("Creating test patient")
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
                    session.flush()
                    session.refresh(patient)
                    
                    # Add to tracked entities for cleanup
                    self.test_entities.append(patient)
                    
                    logger.debug(f"Created patient with encrypted medical info: MRN={patient.mrn}")

                    # Test decryption
                    logger.debug("Decrypting medical information")
                    decrypted_info = encryption_handler.decrypt_field(
                        str(test_hospital.hospital_id),
                        'medical_info',
                        patient.medical_info
                    )
                    logger.debug(f"Decrypted info: {decrypted_info}")

                    # Verify decrypted data
                    assert isinstance(decrypted_info, dict), "Decrypted data should be a dictionary"
                    assert "diagnosis" in decrypted_info, "Should contain medical information"
                    assert decrypted_info["diagnosis"] == test_medical_info["diagnosis"], "Original and decrypted data should match"
                    logger.info("Patient data encryption/decryption test passed")
            else:
                # Unit test - mock database operations
                logger.debug("Running unit test with mocked database")
                with mock.patch('app.services.database_service.get_db_session') as mock_db_session:
                    # Setup mock session
                    mock_session = mock.MagicMock()
                    mock_db_session.return_value.__enter__.return_value = mock_session
                    
                    # Configure mock query results
                    mock_session.query.return_value.filter_by.return_value.first.return_value = None
                    
                    # Test encryption directly - this doesn't need DB access
                    logger.debug("Encrypting medical information")
                    encrypted_info = encryption_handler.encrypt_field(
                        str(test_hospital.hospital_id),
                        'medical_info',
                        test_medical_info
                    )
                    
                    logger.debug("Testing decryption")
                    decrypted_info = encryption_handler.decrypt_field(
                        str(test_hospital.hospital_id),
                        'medical_info',
                        encrypted_info
                    )
                    
                    logger.debug(f"Decrypted info: {decrypted_info}")
                    
                    # Verify decrypted data
                    assert isinstance(decrypted_info, dict), "Decrypted data should be a dictionary"
                    assert "diagnosis" in decrypted_info, "Should contain medical information"
                    assert decrypted_info["diagnosis"] == test_medical_info["diagnosis"], "Original and decrypted data should match"
                    logger.info("Encryption/decryption unit test passed")
        except Exception as e:
            logger.error(f"Error in test_patient_data_encryption: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            if INTEGRATION_MODE:
                # Try to get diagnostic information
                try:
                    with get_db_session(read_only=True) as debug_session:
                        logger.debug("Checking test patient existence for diagnostics:")
                        patient = debug_session.query(Patient).filter_by(
                            hospital_id=test_hospital.hospital_id,
                            mrn="TEST001"
                        ).first()
                        if patient:
                            logger.debug(f"Test patient exists: {patient.mrn}")
                        else:
                            logger.debug("Test patient does not exist")
                except Exception as debug_error:
                    logger.error(f"Error during diagnostics: {str(debug_error)}")
            
            raise

    def test_encryption_key_rotation(self, test_hospital):
        """Test encryption key rotation"""
        logger.info("Testing encryption key rotation")
        
        try:
            # Setup encryption
            logger.debug("Creating security configuration")
            security_config = SecurityConfig.from_dict({
                'encryption_enabled': True,
                'encrypted_fields': {
                    'medical_info': True,
                    'personal_info': True
                }
            })
            encryption_handler = FieldEncryption(security_config)
            
            # Generate and set initial key
            logger.debug("Generating initial encryption key")
            initial_key = Fernet.generate_key()
            encryption_handler.set_encryption_key(str(test_hospital.hospital_id), initial_key)
            
            # Test data
            test_data = {
                "test": "Sensitive medical information",
                "timestamp": datetime.now().isoformat()
            }
            logger.debug(f"Test data: {test_data}")
            
            # First encryption
            logger.debug("Encrypting with initial key")
            encrypted_data = encryption_handler.encrypt_field(
                str(test_hospital.hospital_id),
                'medical_info',
                test_data
            )
            logger.debug(f"Initial encrypted data length: {len(encrypted_data) if encrypted_data else 'N/A'}")
            
            # Verify first encryption
            logger.debug("Verifying initial encryption")
            decrypted_data = encryption_handler.decrypt_field(
                str(test_hospital.hospital_id),
                'medical_info',
                encrypted_data
            )
            logger.debug(f"Initial decryption result: {decrypted_data}")
            assert decrypted_data["test"] == test_data["test"], "Initial encryption/decryption should work"
            
            # New key
            logger.debug("Generating new encryption key")
            new_key = Fernet.generate_key()
            
            # Use the existing rotate or re-encrypt method from your class
            logger.debug("Setting new encryption key")
            encryption_handler.set_encryption_key(str(test_hospital.hospital_id), new_key)
            
            # Test encryption with new key
            logger.debug("Encrypting with new key")
            new_encrypted_data = encryption_handler.encrypt_field(
                str(test_hospital.hospital_id),
                'medical_info',
                test_data
            )
            logger.debug(f"New encrypted data length: {len(new_encrypted_data) if new_encrypted_data else 'N/A'}")
            
            # Verify new encryption
            logger.debug("Verifying encryption with new key")
            new_decrypted_data = encryption_handler.decrypt_field(
                str(test_hospital.hospital_id),
                'medical_info',
                new_encrypted_data
            )
            logger.debug(f"New decryption result: {new_decrypted_data}")
            assert new_decrypted_data["test"] == test_data["test"], "Encryption should work with rotated key"
            
            logger.info("Encryption key rotation test passed successfully")
        except Exception as e:
            logger.error(f"Error in test_encryption_key_rotation: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise