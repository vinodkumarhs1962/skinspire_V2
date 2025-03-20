# tests/test_security/test_setup_verification.py

# =================================================================
# MIGRATION STATUS:
# This file has been fully migrated to use the database service layer.
# It uses get_db_session for all database access following project standards.
#
# Completed:
# - All tests use get_db_session with context manager
# - Database operations follow the established transaction pattern
# - Removed all legacy direct session code
# - Enhanced logging for better debugging
# =================================================================

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import logging
from app.models import Hospital, Staff, User, RoleMaster, ModuleMaster, RoleModuleAccess
from app.config.settings import settings
# Import the database service
from app.services.database_service import get_db_session

# Set up logging for tests
logger = logging.getLogger(__name__)

def test_verify_test_environment():
    """
    Verify that our test environment is properly configured
    
    This test verifies all required test configurations are in place:
    - Hospital configuration
    - Admin user setup
    - Role configuration
    - Module access permissions
    - Staff records
    """
    logger.info("Verifying test environment using database service")
    
    with get_db_session() as session:
        # 1. Hospital Configuration
        hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
        assert hospital is not None, "Test hospital not found"
        assert hospital.encryption_enabled, "Hospital encryption should be enabled"
        assert hospital.settings is not None, "Hospital settings should be configured"
        logger.info(f"Hospital verification passed: {hospital.name}")

        # 2. User Setup
        admin_user = session.query(User).filter_by(user_id="9876543210").first()
        assert admin_user is not None, "Admin user not found"
        assert admin_user.is_active, "Admin user should be active"
        assert admin_user.entity_type == "staff", "Admin should be staff type"
        logger.info(f"Admin user verification passed: {admin_user.user_id}")

        # 3. Role Configuration
        roles = session.query(RoleMaster).all()
        role_names = [role.role_name for role in roles]
        required_roles = [
            'System Administrator',
            'Hospital Administrator',
            'Doctor',
            'Patient'
        ]
        for required_role in required_roles:
            assert required_role in role_names, f"Required role {required_role} not found"
        logger.info(f"Found {len(roles)} roles, all required roles present")

        # 4. Module Access Setup
        admin_role = session.query(RoleMaster).filter_by(
            role_name='Hospital Administrator'
        ).first()
        
        role_permissions = session.query(RoleModuleAccess).filter_by(
            role_id=admin_role.role_id
        ).all()
        assert len(role_permissions) > 0, "Admin role should have permissions"
        logger.info(f"Admin role has {len(role_permissions)} module permissions")

        # 5. Staff Records
        staff_count = session.query(Staff).count()
        assert staff_count > 0, "No staff records found"
        logger.info(f"Found {staff_count} staff records")

def test_verify_security_configuration():
    """
    Verify security-specific configurations
    
    This test verifies security settings are correctly configured:
    - Encryption settings
    - Security policies
    - Password requirements
    """
    logger.info("Verifying security configuration using database service")
    
    with get_db_session() as session:
        hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
        
        # Check encryption settings
        assert hospital.encryption_enabled, "Encryption should be enabled"
        assert settings.MASTER_ENCRYPTION_KEY is not None, "Encryption key should be set"
        
        # Check security settings
        security_settings = settings.get_hospital_security_settings(hospital.hospital_id)
        assert security_settings['audit_enabled'] is not None, "Audit setting should be defined"
        assert security_settings['password_min_length'] >= 8, "Password minimum length should be set"

        logger.info("Security configuration verification passed")