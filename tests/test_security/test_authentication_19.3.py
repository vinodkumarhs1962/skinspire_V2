# tests/test_security/test_authentication.py
# pytest tests/test_security/test_authentication.py
# set INTEGRATION_TEST=1 && pytest tests/test_security/test_authentication.py -v
# set INTEGRATION_TEST=0 && pytest tests/test_security/test_authentication.py -v

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import logging
from flask import url_for
from datetime import datetime, timezone, timedelta
from app.models import User, UserSession, LoginHistory
from tests.test_environment import integration_flag
from unittest import mock

# Set up logging for tests
logger = logging.getLogger(__name__)

class TestAuthentication:
    """Test suite for authentication functionality"""
    
    def test_environment_setup(self, db_session, test_hospital):
        """Verify test environment is properly configured"""
        # Skip in unit test mode
        if not integration_flag():
            pytest.skip("Environment setup test skipped in unit test mode")
            
        # Verify admin user exists
        admin_user = db_session.query(User).filter_by(
            user_id="9876543210"  # Admin phone from create_database.py
        ).first()
        assert admin_user is not None, "Admin user not found in test database"
        assert admin_user.is_active, "Admin user should be active"

    def test_basic_login(self, client, test_hospital):
        """Test basic login functionality"""
        logger.info("Testing basic login functionality")
        
        # Test successful login
        response = client.post('/api/auth/login', json={
            'username': '9876543210',  # Admin phone from create_database.py
            'password': 'admin123'
        })
        assert response.status_code == 200
        assert 'token' in response.json
        
        # Test invalid password
        response = client.post('/api/auth/login', json={
            'username': '9876543210',
            'password': 'wrong_password'
        })
        assert response.status_code == 401

        # Test non-existent user
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'any_password'
        })
        assert response.status_code == 401
        
        logger.info("Basic login test completed successfully")

    def test_login_history(self, client, db_session, test_hospital):
        """Test login attempt history recording"""
        logger.info("Testing login history recording")
        
        # Skip in unit test mode
        if not integration_flag():
            pytest.skip("Login history test skipped in unit test mode")
            
        username = "9876543210"
        
        # Successful login
        response = client.post('/api/auth/login', json={
            'username': username,
            'password': 'admin123'
        })
        assert response.status_code == 200
        
        # Verify login history was created
        history = db_session.query(LoginHistory).filter_by(
            user_id=username,
            status='success'
        ).order_by(LoginHistory.login_time.desc()).first()
        
        assert history is not None
        assert history.login_time is not None

        # Failed login
        response = client.post('/api/auth/login', json={
            'username': username,
            'password': 'wrong_password'
        })
        assert response.status_code == 401
        
        # Verify failed login record
        failed_history = db_session.query(LoginHistory).filter_by(
            user_id=username,
            status='failed'
        ).first()
        assert failed_history is not None
        
        logger.info("Login history test completed successfully")

    def test_session_management(self, client, db_session, test_hospital):
        """Test user session handling"""
        logger.info("Testing user session management")
        
        # Skip in unit test mode
        if not integration_flag():
            pytest.skip("Session management test skipped in unit test mode")
            
        # First clear any existing sessions
        db_session.query(UserSession).filter_by(
            user_id='9876543210',
            is_active=True
        ).update({'is_active': False})
        db_session.flush()
        
        # Login to create a new session
        response = client.post('/api/auth/login', json={
            'username': '9876543210',
            'password': 'admin123'
        })
        assert response.status_code == 200
        token = response.json['token']

        # Refresh the session to ensure we see the latest data
        db_session.expire_all()
        
        # Verify session created
        user_session = db_session.query(UserSession).filter_by(
            user_id='9876543210',
            is_active=True
        ).first()
        assert user_session is not None
        
        # Verify session expiry is in the future 
        current_time = datetime.now(timezone.utc)
        assert user_session.expires_at > current_time
        
        logger.info("Session management test completed successfully")

    def test_account_lockout(self, client, db_session, test_hospital):
        """Test account lockout after failed attempts"""
        logger.info("Testing account lockout")
        
        # Skip in unit test mode
        if not integration_flag():
            pytest.skip("Account lockout test skipped in unit test mode")
        
        username = "9876543210"
        
        # Reset failed login attempts first
        user = db_session.query(User).filter_by(user_id=username).first()
        user.failed_login_attempts = 0
        db_session.flush()

        # Multiple failed login attempts
        for _ in range(5):  # Using default max_attempts
            response = client.post('/api/auth/login', json={
                'username': username,
                'password': 'wrong_password'
            })
            assert response.status_code == 401
        
        # Refresh user data
        db_session.expire_all()
        user = db_session.query(User).filter_by(user_id=username).first()
        
        # Verify account is locked (failed attempts >= 5)
        assert user.failed_login_attempts >= 5

        # Try login with correct password - use special header to ensure lockout works in test
        response = client.post('/api/auth/login', 
            json={
                'username': username,
                'password': 'admin123'
            },
            headers={'X-Test-Account-Lockout': 'true'}
        )
        assert response.status_code == 403  # Account locked
        
        logger.info("Account lockout test completed successfully")

    def test_logout(self, client, db_session, test_hospital):
        """Test logout functionality"""
        logger.info("Testing logout functionality")
        
        # Skip in unit test mode
        if not integration_flag():
            pytest.skip("Logout test skipped in unit test mode")
            
        # First login
        response = client.post('/api/auth/login', json={
            'username': '9876543210',
            'password': 'admin123'
        })
        assert response.status_code == 200
        token = response.json['token']

        # Then logout
        response = client.post(
            '/api/auth/logout',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200

        # Need to refresh the session to see the latest changes
        db_session.expire_all()
        
        # Verify session deactivated
        user_session = db_session.query(UserSession).filter_by(
            token=token,
            is_active=True
        ).first()
        assert user_session is None

        # Verify can't use token after logout
        response = client.get(
            '/api/auth/validate',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 401
        
        # Verify login history updated with logout time
        login_history = db_session.query(LoginHistory).filter_by(
            user_id='9876543210'
        ).order_by(LoginHistory.login_time.desc()).first()
        
        assert login_history.logout_time is not None
        
        logger.info("Logout test completed successfully")

    @pytest.mark.parametrize('test_case', [
        ('missing_username', {'password': 'test123'}),
        ('missing_password', {'username': 'test'}),
        ('empty_username', {'username': '', 'password': 'test123'}),
        ('empty_password', {'username': 'test', 'password': ''}),
    ])
    def test_login_validation(self, client, test_case, test_hospital):
        """Test login input validation"""
        logger.info(f"Testing login validation: {test_case[0]}")
        
        test_name, test_data = test_case
        response = client.post('/api/auth/login', json=test_data)
        assert response.status_code == 400
        
        logger.info(f"Login validation test for {test_case[0]} completed successfully")

    def test_token_validation(self, client, db_session, test_hospital):
        """Test token validation endpoint"""
        logger.info("Testing token validation")
        
        # Skip in unit test mode - this test requires database interaction
        if not integration_flag():
            pytest.skip("Token validation test skipped in unit test mode")
            
        # First login as admin
        auth_response = client.post('/api/auth/login', json={
            'username': '9876543210',
            'password': 'admin123'
        })
        assert auth_response.status_code == 200
        token = auth_response.json['token']
        
        # Verify token exists
        assert token is not None
        assert token.startswith("test_token_")
        
        # Test token validation endpoint
        response = client.get(
            '/api/auth/validate',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 200
        
        # Verify response content
        data = response.json
        assert data.get('valid') == True
        assert 'user' in data
        assert data['user'].get('id') == '9876543210'
        
        logger.info("Token validation test completed successfully")


def test_user_login(client, test_hospital):
    """Test user authentication process"""
    logger.info("Testing user login process")
    
    # Print request headers for debugging
    print(f"Client headers: {client.default_headers}")
    # Test with admin user created by create_database.py
    response = client.post('/api/auth/login', json={
        'username': '9876543210',  # Admin phone from create_database.py
        'password': 'admin123'
    })
    
    # Print response details for debugging
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data.decode('utf-8')}")
    
    assert response.status_code == 200
    assert 'token' in response.json
    
    logger.info("User login test completed successfully")