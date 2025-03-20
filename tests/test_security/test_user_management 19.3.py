# tests/test_security/test_user_management.py
# pytest tests/test_security/test_user_management.py
# set "INTEGRATION_TEST=1" && pytest tests/test_security/test_user_management.py -v

# =================================================================
# MIGRATION STATUS:
# This file has been fully migrated to use the database service layer.
# It uses get_db_session for all database access following project standards.
#
# Completed:
# - All test methods use get_db_session with context manager
# - Database operations follow the established transaction pattern
# - Removed all legacy direct session code
# - Enhanced error handling and logging
# - Migrated all helper functions
# =================================================================

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

from sqlalchemy import text
import pytest
import logging
import uuid
import time
import random
from app.models import User, UserRoleMapping, RoleMaster, UserSession
from werkzeug.security import check_password_hash
# Import the database service
from app.services.database_service import get_db_session
from tests.test_environment import integration_flag
# def check_integration():
#     """Enhanced integration check for this test file"""
#     import os
#     return (os.environ.get("INTEGRATION_TEST") == "1" or 
#             os.environ.get("INTEGRATION_TESTS") == "True")

# Set up logging for tests
logger = logging.getLogger(__name__)

def is_valid_password_hash(hash_string):
    """
    Check if a string is a valid password hash in any of the recognized formats
    
    Args:
        hash_string: The string to check
        
    Returns:
        bool: True if the string is a valid password hash, False otherwise
    """
    if not hash_string or not isinstance(hash_string, str):
        return False
    
    # Check all supported hash formats
    return (hash_string.startswith('$pbkdf2') or  # Werkzeug older versions
            hash_string.startswith('$2') or       # bcrypt
            hash_string.startswith('scrypt:'))    # Werkzeug newer versions
            
@pytest.fixture
def admin_token(client):
    """
    Get admin auth token for testing
    
    Args:
        client: Flask test client
        
    Returns:
        str: Authentication token for admin user
    """
    response = client.post('/api/auth/login', json={
        'username': '9876543210',  # Admin from create_database.py
        'password': 'admin123'
    })
    return response.json['token']

@pytest.fixture
def user_token(client, test_user):
    """
    Get regular user auth token for testing
    
    Args:
        client: Flask test client
        test_user: Test user fixture
        
    Returns:
        str: Authentication token for test user or None if login fails
    """
    # Create a session for test_user
    response = client.post('/api/auth/login', json={
        'username': test_user.user_id,
        'password': 'test_password'  # Matches password in conftest.py
    })
    if response.status_code == 200:
        return response.json['token']
    return None

def check_hashed_password(hashed_password, plain_password):
    """
    Check a hashed password directly
    
    Args:
        hashed_password: The hashed password
        plain_password: The plain text password
        
    Returns:
        bool: True if passwords match, False otherwise
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
    """
    Generate a unique user ID that fits within the 15-character limit
    
    Returns:
        str: A unique user ID
    """
    # Use microseconds and a random number to ensure uniqueness
    timestamp = int(time.time() * 1000) % 10000000  # Keep only 7 digits
    random_part = random.randint(100, 999)  # 3 digits
    return f"t{timestamp}{random_part}"  # 1 + 7 + 3 = 11 characters

class TestUserManagement:
    """Test suite for user management functionality using database service"""
    
    def test_create_user(self, test_hospital):
        """
        Test user creation
        
        Verifies:
        - User can be created with correct attributes
        - Password is properly hashed
        - User can be retrieved from database
        """
        logger.info("Testing user creation with database service")
        # Create a unique user ID that's short enough for your database constraints
        user_id = generate_unique_user_id()
        entity_id = str(uuid.uuid4())
        
        with get_db_session() as session:
            # Create user with the new service pattern
            user = User(
                user_id=user_id,
                hospital_id=test_hospital.hospital_id,
                entity_type="staff",
                entity_id=entity_id,
                is_active=True
            )
            
            # Use explicit set_password method
            user.set_password("secure_password")
            logger.debug(f"Password hash: {user.password_hash}")

            session.add(user)
            session.flush()
            
            # Verify user was created
            created_user = session.query(User).filter_by(user_id=user_id).first()
            logger.debug(f"Retrieved hash: {created_user.password_hash}")
            assert created_user is not None
            assert created_user.user_id == user_id
            assert created_user.entity_type == "staff"
            assert created_user.is_active == True
            
            # Verify password was hashed correctly
            assert created_user.password_hash is not None
            assert created_user.password_hash != "secure_password", "Password was not hashed"
            assert is_valid_password_hash(created_user.password_hash), "Password does not have expected hash format"

            # Use the check_password method
            assert created_user.check_password("secure_password"), "Password hash verification failed"
        
        # No explicit cleanup needed - session will roll back automatically
        logger.info("User creation test passed")
    
    def test_update_user(self, test_hospital):
        """
        Test user update
        
        Verifies:
        - User attributes can be updated
        - Password can be changed and is properly hashed
        """
        logger.info("Testing user update with database service")
        # Create a test user first
        user_id = generate_unique_user_id()
        entity_id = str(uuid.uuid4())
        
        with get_db_session() as session:
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
            session.flush()
            
            # Save initial hashed password
            initial_hashed_password = user.password_hash
            
            # Now update the user
            user.is_active = False
            user.set_password("new_password")  # Use set_password instead of direct assignment
            session.flush()
            
            # Verify updates were applied
            updated_user = session.query(User).filter_by(user_id=user_id).first()
            assert updated_user.is_active == False
            assert updated_user.password_hash != "new_password", "Password was not hashed on update"
            assert updated_user.password_hash != initial_hashed_password, "Password was not changed"
            assert updated_user.check_password("new_password"), "New password verification failed"
        
        # No explicit cleanup needed - session will roll back automatically
        logger.info("User update test passed")
    
    def test_role_assignment(self, test_hospital):
        """
        Test role assignment to users
        
        Verifies:
        - Roles can be created
        - Roles can be assigned to users
        - Role assignments can be retrieved
        """
        logger.info("Testing role assignment with database service")
        
        with get_db_session() as session:
            # Create a test user
            user_id = generate_unique_user_id()
            entity_id = str(uuid.uuid4())
            
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
            session.flush()
            
            # Create a test role
            role_name = f"test_role_{uuid.uuid4().hex[:8]}"
            
            role = RoleMaster(
                hospital_id=test_hospital.hospital_id,
                role_name=role_name,
                description="Test role",
                is_system_role=False
            )
            
            session.add(role)
            session.flush()
            
            # Assign role to user
            role_mapping = UserRoleMapping(
                user_id=user_id,
                role_id=role.role_id,
                is_active=True
            )
            
            session.add(role_mapping)
            session.flush()
            
            # Verify role assignment
            assigned_roles = (
                session.query(RoleMaster)
                .join(UserRoleMapping, RoleMaster.role_id == UserRoleMapping.role_id)
                .filter(UserRoleMapping.user_id == user_id)
                .all()
            )
            
            assert len(assigned_roles) == 1
            assert assigned_roles[0].role_name == role_name
        
        # No explicit cleanup needed - session will roll back automatically
        logger.info("Role assignment test passed")
    
    def test_api_user_management(self, client, test_hospital, admin_token):
        """
        Test user management via API
        
        Verifies:
        - Users can be created via API
        - Users can be retrieved via API
        - Users can be updated via API
        """
            # Add debugging
        import os
        # print(f"Inside test method: INTEGRATION_TEST value = {os.environ.get('INTEGRATION_TEST')}")
        # print(f"Inside test method: integration_flag() returns = {integration_flag()}")
        
        # Skip in unit test mode
        if not integration_flag():
            pytest.skip("API user management test skipped in unit test mode")
            
        logger.info("Testing user management via API")
        
        # Generate unique user details
        user_id = generate_unique_user_id()
        
        try:
            # Step 1: Create user via API
            create_response = client.post(
                '/api/auth/users',
                json={
                    'user_id': user_id,
                    'entity_type': 'staff',
                    'password': 'Api123!',
                    'is_active': True
                },
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert create_response.status_code in (200, 201), f"User creation failed: {create_response.data}"
            
            # Step 2: Get user details via API
            get_response = client.get(
                f'/api/auth/users/{user_id}',
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert get_response.status_code == 200
            user_data = get_response.json
            assert user_data['user_id'] == user_id
            assert user_data['is_active'] is True
            
            # Step 3: Update user via API
            update_response = client.put(
                f'/api/auth/users/{user_id}', 
                json={
                    'is_active': False
                },
                headers={'Authorization': f'Bearer {admin_token}'}
            )
            
            assert update_response.status_code == 200
            
            # Verify update in database
            with get_db_session() as session:
                updated_user = session.query(User).filter_by(user_id=user_id).first()
                assert updated_user is not None
                assert updated_user.is_active is False
            
        except Exception as e:
            # Log detailed error for debugging
            import traceback
            logger.error(f"Error in API user management test: {str(e)}")
            logger.error(traceback.format_exc())
            raise
            
        logger.info("API user management test passed")