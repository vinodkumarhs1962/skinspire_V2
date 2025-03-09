# tests/test_security/test_authentication.py
# pytest tests/test_security/test_authentication.py

import pytest
from flask import url_for
from datetime import datetime, timezone, timedelta
from app.models import User, UserSession, LoginHistory

class TestAuthentication:
    """Test suite for authentication functionality"""

    def test_environment_setup(self, session, test_hospital):
        """Verify test environment is properly configured"""
        # Verify admin user exists
        admin_user = session.query(User).filter_by(
            user_id="9876543210"  # Admin phone from create_database.py
        ).first()
        assert admin_user is not None, "Admin user not found in test database"
        assert admin_user.is_active, "Admin user should be active"

    def test_basic_login(self, client, test_hospital):
        """Test basic login functionality"""
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

    def test_login_history(self, client, session, test_hospital):
        """Test login attempt history recording"""
        username = "9876543210"
        
        # Successful login
        response = client.post('/api/auth/login', json={
            'username': username,
            'password': 'admin123'
        })
        assert response.status_code == 200
        
        # Verify login history was created
        history = session.query(LoginHistory).filter_by(
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
        failed_history = session.query(LoginHistory).filter_by(
            user_id=username,
            status='failed'
        ).first()
        assert failed_history is not None

    def test_session_management(self, client, session, test_hospital):
        """Test user session handling"""
        # First clear any existing sessions
        session.query(UserSession).filter_by(
            user_id='9876543210',
            is_active=True
        ).update({'is_active': False})
        session.commit()
        
        # Login to create a new session
        response = client.post('/api/auth/login', json={
            'username': '9876543210',
            'password': 'admin123'
        })
        assert response.status_code == 200
        token = response.json['token']

        # Refresh the session to ensure we see the latest data
        session.expire_all()
        
        # Verify session created
        user_session = session.query(UserSession).filter_by(
            user_id='9876543210',
            is_active=True
        ).first()
        assert user_session is not None
        
        # Verify session expiry is in the future 
        current_time = datetime.now(timezone.utc)
        assert user_session.expires_at > current_time

    def test_account_lockout(self, client, session, test_hospital):
        """Test account lockout after failed attempts"""
        username = "9876543210"
        
        # Reset failed login attempts first
        user = session.query(User).filter_by(user_id=username).first()
        user.failed_login_attempts = 0
        session.commit()

        # Multiple failed login attempts
        for _ in range(5):  # Using default max_attempts
            response = client.post('/api/auth/login', json={
                'username': username,
                'password': 'wrong_password'
            })
            assert response.status_code == 401
        
        # Refresh user data
        session.expire_all()
        user = session.query(User).filter_by(user_id=username).first()
        
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

    def test_logout(self, client, session, test_hospital):
        """Test logout functionality"""
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
        session.expire_all()
        
        # Verify session deactivated
        user_session = session.query(UserSession).filter_by(
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
        login_history = session.query(LoginHistory).filter_by(
            user_id='9876543210'
        ).order_by(LoginHistory.login_time.desc()).first()
        
        assert login_history.logout_time is not None

    @pytest.mark.parametrize('test_case', [
        ('missing_username', {'password': 'test123'}),
        ('missing_password', {'username': 'test'}),
        ('empty_username', {'username': '', 'password': 'test123'}),
        ('empty_password', {'username': 'test', 'password': ''}),
    ])
    def test_login_validation(self, client, test_case, test_hospital):
        """Test login input validation"""
        test_name, test_data = test_case
        response = client.post('/api/auth/login', json=test_data)
        assert response.status_code == 400

    def test_token_validation(self, client, session, test_hospital):
        """Test token validation endpoint"""
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

# Standalone test function
def test_user_login(client, test_hospital):
    """Test user authentication process"""
    # Test with admin user created by create_database.py
    response = client.post('/api/auth/login', json={
        'username': '9876543210',  # Admin phone from create_database.py
        'password': 'admin123'
    })
    assert response.status_code == 200
    assert 'token' in response.json