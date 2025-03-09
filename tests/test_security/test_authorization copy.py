# tests/test_security/test_authorization.py
# pytest tests/test_security/test_authorization.py

import pytest
from app.models import User, UserRoleMapping, RoleMaster, RoleModuleAccess, ModuleMaster
from app.security.authorization.permission_validator import has_permission
import uuid

class TestAuthorization:
    """Test suite for authorization and permission functionality"""
    
    def test_module_creation(self, session):
        """Test module creation for permissions"""
        # Create a test module
        module_name = f"test_module_{uuid.uuid4().hex[:8]}"
        
        module = ModuleMaster(
            module_name=module_name,
            description="Test module for permissions",
            route=f"/test/{module_name}",
            sequence=999  # High sequence to avoid conflicts
        )
        
        session.add(module)
        session.commit()
        
        # Verify module creation
        created_module = session.query(ModuleMaster).filter_by(module_name=module_name).first()
        assert created_module is not None
        assert created_module.module_name == module_name
        
        # Cleanup
        session.delete(created_module)
        session.commit()
    
    def test_role_permissions(self, session, test_hospital):
        """Test role permissions assignment and checking"""
        # Create a test module
        module_name = f"test_module_{uuid.uuid4().hex[:8]}"
        module = ModuleMaster(
            module_name=module_name,
            description="Test module for permissions",
            route=f"/test/{module_name}",
            sequence=999
        )
        session.add(module)
        session.commit()
        
        # Store the module ID right after creation
        module_id = module.module_id
        
        # Create a test role
        role_name = f"test_role_{uuid.uuid4().hex[:8]}"
        role = RoleMaster(
            hospital_id=test_hospital.hospital_id,
            role_name=role_name,
            description="Test role for permissions",
            is_system_role=False
        )
        session.add(role)
        session.commit()
        
        # Store the role ID right after creation
        role_id = role.role_id
        
        # Assign permissions
        module_access = RoleModuleAccess(
            role_id=role_id,
            module_id=module_id,
            can_view=True,
            can_add=True,
            can_edit=False,
            can_delete=False,
            can_export=True
        )
        session.add(module_access)
        session.commit()
        
        # Create a test user with short ID (max 15 chars)
        user_id = f"test_{uuid.uuid4().hex[:4]}"
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=str(uuid.uuid4()),
            is_active=True
        )
        session.add(user)
        session.commit()
        
        # Assign role to user
        role_mapping = UserRoleMapping(
            user_id=user_id,
            role_id=role.role_id,
            is_active=True
        )
        session.add(role_mapping)
        session.commit()
        
        # Test permission validation - pass the user_id string, not the detached user object
        assert has_permission(user_id, module_name, 'view') == True
        assert has_permission(user_id, module_name, 'add') == True
        assert has_permission(user_id, module_name, 'edit') == False
        assert has_permission(user_id, module_name, 'delete') == False
        assert has_permission(user_id, module_name, 'export') == True
        
        # IDs already captured earlier
        
        # Cleanup
        session.query(UserRoleMapping).filter_by(user_id=user_id).delete()
        session.query(User).filter_by(user_id=user_id).delete()
        session.query(RoleModuleAccess).filter_by(
            role_id=role_id, module_id=module_id
        ).delete()
        session.query(RoleMaster).filter_by(role_id=role_id).delete()
        session.query(ModuleMaster).filter_by(module_id=module_id).delete()
        session.commit()
    
    def test_permission_checking(self, session, test_hospital):
        """Test permission checking with existing data"""
        # Get an existing module
        module = session.query(ModuleMaster).first()
        assert module is not None, "No modules found in test database"
        
        # Get an existing role
        role = session.query(RoleMaster).filter_by(
            hospital_id=test_hospital.hospital_id
        ).first()
        assert role is not None, "No roles found for test hospital"
        
        # Check if we already have permissions set up
        permission = session.query(RoleModuleAccess).filter_by(
            role_id=role.role_id,
            module_id=module.module_id
        ).first()
        
        if not permission:
            # Create a permission if none exists
            permission = RoleModuleAccess(
                role_id=role.role_id,
                module_id=module.module_id,
                can_view=True,
                can_add=False,
                can_edit=False,
                can_delete=False,
                can_export=False
            )
            session.add(permission)
            session.commit()
        
        # Capture expected permissions
        can_view = permission.can_view
        can_add = permission.can_add
        can_edit = permission.can_edit
        can_delete = permission.can_delete
        can_export = permission.can_export
        module_name = module.module_name
        
        # Create a test user with short ID (max 15 chars)
        user_id = f"test_{uuid.uuid4().hex[:4]}"
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=str(uuid.uuid4()),
            is_active=True
        )
        session.add(user)
        session.commit()
        
        # Assign role to user
        role_mapping = UserRoleMapping(
            user_id=user_id,
            role_id=role.role_id,
            is_active=True
        )
        session.add(role_mapping)
        session.commit()
        
        # Test permission validation - pass the user_id string, not the user object
        assert has_permission(user_id, module_name, 'view') == can_view
        assert has_permission(user_id, module_name, 'add') == can_add
        assert has_permission(user_id, module_name, 'edit') == can_edit
        assert has_permission(user_id, module_name, 'delete') == can_delete
        assert has_permission(user_id, module_name, 'export') == can_export
        
        # Test permission for nonexistent module
        assert has_permission(user_id, 'nonexistent_module', 'view') == False
        
        # Cleanup
        session.query(UserRoleMapping).filter_by(user_id=user_id).delete()
        session.query(User).filter_by(user_id=user_id).delete()
        session.commit()