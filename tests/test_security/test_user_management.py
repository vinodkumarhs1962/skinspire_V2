# tests/test_security/test_user_management.py
# pytest tests/test_security/test_user_management.py

from sqlalchemy import text
import pytest
from app.models import User, UserRoleMapping, RoleMaster, UserSession
import uuid
import time
import random
from sqlalchemy import text
from werkzeug.security import check_password_hash

def is_valid_password_hash(hash_string):
    """Check if a string is a valid password hash in any of the recognized formats"""
    if not hash_string or not isinstance(hash_string, str):
        return False
    
    # Check all supported hash formats
    return (hash_string.startswith('$pbkdf2') or  # Werkzeug older versions
            hash_string.startswith('$2') or       # bcrypt
            hash_string.startswith('scrypt:'))    # Werkzeug newer versions
            
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

def check_hashed_password(session, hashed_password, plain_password):
    """
    Check a hashed password directly using the database
    """
    if not hashed_password or not plain_password:
        return False
        
    # Use bcrypt directly
    if hashed_password.startswith('$2'):
        try:
            from werkzeug.security import check_password_hash
            return check_password_hash(hashed_password, plain_password)
        except Exception:
            pass
    
    # Not a hashed password
    return hashed_password == plain_password

def generate_unique_user_id():
    """Generate a unique user ID that fits within the 15-character limit"""
    # Use microseconds and a random number to ensure uniqueness
    timestamp = int(time.time() * 1000) % 10000000  # Keep only 7 digits
    random_part = random.randint(100, 999)  # 3 digits
    return f"t{timestamp}{random_part}"  # 1 + 7 + 3 = 11 characters

class TestUserManagement:
    """Test suite for user management functionality"""
    def test_create_user(self, session, test_hospital):
        """Test user creation"""
        # Create a unique user ID that's short enough for your database constraints
        user_id = generate_unique_user_id()
        entity_id = str(uuid.uuid4())
        
        # First check if this user_id already exists and delete it if so
        existing_user = session.query(User).filter_by(user_id=user_id).first()
        if existing_user:
            session.delete(existing_user)
            session.commit()
        
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=entity_id,
            is_active=True
        )
        
        # Use explicit set_password method instead of relying on triggers
        user.set_password("secure_password")
        print(f"DEBUG: Password hash: {user.password_hash}")

        session.add(user)
        session.commit()
        session.refresh(user)  # Make sure we get the hashed password
        
        # Verify user was created
        created_user = session.query(User).filter_by(user_id=user_id).first()
        print(f"DEBUG: Retrieved hash: {created_user.password_hash}")
        assert created_user is not None
        assert created_user.user_id == user_id
        assert created_user.entity_type == "staff"
        assert created_user.is_active == True
        
        # Verify password was hashed correctly
        assert created_user.password_hash is not None
        assert created_user.password_hash != "secure_password", "Password was not hashed"
        #assert created_user.password_hash.startswith('$pbkdf2') or created_user.password_hash.startswith('$2'), "Password does not have expected hash format"
        assert (created_user.password_hash.startswith('$pbkdf2') or 
        created_user.password_hash.startswith('$2') or 
        created_user.password_hash.startswith('scrypt:')), "Password does not have expected hash format"

        # Use the check_password method
        assert created_user.check_password("secure_password"), "Password hash verification failed"
        
        # Cleanup
        session.delete(created_user)
        session.commit()
    
    def test_update_user(self, session, test_hospital):
        """Test user update"""
        # Create a test user first
        user_id = generate_unique_user_id()
        entity_id = str(uuid.uuid4())
        
        # First check if this user_id already exists and delete it if so
        existing_user = session.query(User).filter_by(user_id=user_id).first()
        if existing_user:
            session.delete(existing_user)
            session.commit()
        
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=entity_id,
            is_active=True
        )
        
        # Use set_password
        user.set_password("initial_password")
        
        session.add(user)
        session.commit()
        session.refresh(user)  # Get the hashed password
        
        # Save initial hashed password
        initial_hashed_password = user.password_hash
        
        # Now update the user
        user.is_active = False
        user.set_password("new_password")  # Use set_password instead of direct assignment
        session.commit()
        session.refresh(user)  # Get the newly hashed password
        
        # Verify updates were applied
        updated_user = session.query(User).filter_by(user_id=user_id).first()
        assert updated_user.is_active == False
        assert updated_user.password_hash != "new_password", "Password was not hashed on update"
        assert updated_user.password_hash != initial_hashed_password, "Password was not changed"
        assert updated_user.check_password("new_password"), "New password verification failed"
        
        # Cleanup
        session.delete(updated_user)
        session.commit()
    
    def test_role_assignment(self, session, test_hospital):
        """Test role assignment to users"""
        # Create a test user
        user_id = generate_unique_user_id()
        entity_id = str(uuid.uuid4())
        
        # First check if this user_id already exists and delete it if so
        existing_user = session.query(User).filter_by(user_id=user_id).first()
        if existing_user:
            session.delete(existing_user)
            session.commit()
        
        user = User(
            user_id=user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=entity_id,
            is_active=True
        )
        
        # Use set_password
        user.set_password("test_password")
        
        session.add(user)
        session.commit()
        
        # Rest of the method remains the same
