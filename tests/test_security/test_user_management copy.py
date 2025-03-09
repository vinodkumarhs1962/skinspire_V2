# tests/test_security/test_user_management.py
# pytest tests/test_security/test_user_management.py

import pytest
from app.models import User, UserRoleMapping, RoleMaster, UserSession
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

@pytest.fixture
def admin_token(client):
    """Get admin auth token for testing"""
    response = client.post('/api/auth/login', json={
        'username': '9876543210',  # Admin from create_database.py
        'password': 'admin123'
    })
    return response.json['token']

@pytest.fixture
def user_token(client, test_user):
    """Get regular user auth token for testing"""
    # Create a session for test_user
    response = client.post('/api/auth/login', json={
        'username': test_user.user_id,
        'password': 'test_password'  # Matches password in conftest.py
    })
    if response.status_code == 200:
        return response.json['token']
    return None

class TestUserManagement:
    """Test suite for user management functionality"""
    
    def test_create_user(self, session, test_hospital):
        """Test user creation"""
        # Create a new test user
        # user_id = f"testuser_{uuid.uuid4().hex[:8]}"
        user_id = f"test_{uuid.uuid4().hex[:4]}"
        entity_id = str(uuid.uuid4())
        
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=entity_id,
            is_active=True
        )
        user.set_password("secure_password")
        
        session.add(user)
        session.commit()
        
        # Verify user was created
        created_user = session.query(User).filter_by(user_id=user_id).first()
        assert created_user is not None
        assert created_user.user_id == user_id
        assert created_user.entity_type == "staff"
        assert created_user.is_active == True
        
        # Verify password was hashed correctly
        assert created_user.password_hash is not None
        assert check_password_hash(created_user.password_hash, "secure_password")
        
        # Cleanup
        session.delete(created_user)
        session.commit()
    
    def test_update_user(self, session, test_hospital):
        """Test user update"""
        # Create a test user first
        # user_id = f"testuser_{uuid.uuid4().hex[:8]}"
        user_id = f"test_{uuid.uuid4().hex[:4]}"
        entity_id = str(uuid.uuid4())
        
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=entity_id,
            is_active=True
        )
        user.set_password("initial_password")
        
        session.add(user)
        session.commit()
        
        # Now update the user
        user.is_active = False
        user.set_password("new_password")
        session.commit()
        
        # Verify updates were applied
        updated_user = session.query(User).filter_by(user_id=user_id).first()
        assert updated_user.is_active == False
        assert check_password_hash(updated_user.password_hash, "new_password")
        assert not check_password_hash(updated_user.password_hash, "initial_password")
        
        # Cleanup
        session.delete(updated_user)
        session.commit()
    
    def test_role_assignment(self, session, test_hospital):
        """Test role assignment to users"""
        # Create a test user
        # user_id = f"testuser_{uuid.uuid4().hex[:8]}"
        user_id = f"test_{uuid.uuid4().hex[:4]}"
        entity_id = str(uuid.uuid4())
        
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=entity_id,
            is_active=True
        )
        session.add(user)
        
        # Get a role to assign
        role = session.query(RoleMaster).first()
        assert role is not None, "No roles found in test database"
        
        # Assign the role
        role_mapping = UserRoleMapping(
            user_id=user_id,
            role_id=role.role_id,
            is_active=True
        )
        session.add(role_mapping)
        session.commit()
        
        # Verify role assignment
        mappings = session.query(UserRoleMapping).filter_by(user_id=user_id).all()
        assert len(mappings) == 1
        assert mappings[0].role_id == role.role_id
        
        # Cleanup
        session.delete(role_mapping)
        session.delete(user)
        session.commit()