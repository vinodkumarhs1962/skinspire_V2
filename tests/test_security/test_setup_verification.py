# tests/test_security/test_setup_verification.py

import pytest
from app.models import Hospital, Staff, User, RoleMaster, ModuleMaster, RoleModuleAccess
from app.database import init_db
from app.config.settings import settings

def test_verify_test_environment():
    """Verify that our test environment is properly configured"""
    db_manager = init_db(settings.get_database_url_for_env('testing'))
    
    with db_manager.get_session() as session:
        # 1. Hospital Configuration
        hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
        assert hospital is not None, "Test hospital not found"
        assert hospital.encryption_enabled, "Hospital encryption should be enabled"
        assert hospital.settings is not None, "Hospital settings should be configured"
        print(f"Hospital verification passed: {hospital.name}")  # Helpful debug info

        # 2. User Setup
        admin_user = session.query(User).filter_by(user_id="9876543210").first()
        assert admin_user is not None, "Admin user not found"
        assert admin_user.is_active, "Admin user should be active"
        assert admin_user.entity_type == "staff", "Admin should be staff type"
        print(f"Admin user verification passed: {admin_user.user_id}")

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
        print(f"Found {len(roles)} roles, all required roles present")

        # 4. Module Access Setup
        admin_role = session.query(RoleMaster).filter_by(
            role_name='Hospital Administrator'
        ).first()
        
        role_permissions = session.query(RoleModuleAccess).filter_by(
            role_id=admin_role.role_id
        ).all()
        assert len(role_permissions) > 0, "Admin role should have permissions"
        print(f"Admin role has {len(role_permissions)} module permissions")

        # 5. Staff Records
        staff_count = session.query(Staff).count()
        assert staff_count > 0, "No staff records found"
        print(f"Found {staff_count} staff records")

def test_verify_security_configuration():
    """Verify security-specific configurations"""
    db_manager = init_db(settings.get_database_url_for_env('testing'))
    
    with db_manager.get_session() as session:
        hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
        
        # Check encryption settings
        assert hospital.encryption_enabled, "Encryption should be enabled"
        assert settings.MASTER_ENCRYPTION_KEY is not None, "Encryption key should be set"
        
        # Check security settings
        security_settings = settings.get_hospital_security_settings(hospital.hospital_id)
        assert security_settings['audit_enabled'] is not None, "Audit setting should be defined"
        assert security_settings['password_min_length'] >= 8, "Password minimum length should be set"

        print("Security configuration verification passed")