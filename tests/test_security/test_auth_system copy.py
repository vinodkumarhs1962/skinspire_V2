# tests/test_security/test_auth_system.py
# python -m pytest tests/test_security/test_auth_system.py -v
import pytest
import uuid
import logging
from tests.conftest import db_session
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone
from app.models import User, UserSession, LoginHistory
from app.security.authentication.auth_manager import AuthManager
from app.security.config import SecurityConfig

# Set up logging for tests
logger = logging.getLogger(__name__)

@pytest.fixture(scope='function')
def test_user(db_session, test_hospital):
    """Create test user with proper session management"""
    # We'll use this to track our transaction state
    transaction_successful = False
    
    try:
        # First, define our cleanup order - this order matters due to foreign keys
        cleanup_queries = [
            (LoginHistory, "user_id", "test_user"),  # Child table first
            (UserSession, "user_id", "test_user"),   # Then session records
            (User, "user_id", "test_user")           # Finally the user record
        ]
        
        # Clean up any existing test data with error handling
        for model, field, value in cleanup_queries:
            try:
                # Use synchronize_session=False for better performance in deletion
                db_session.query(model).filter_by(
                    **{field: value}
                ).delete(synchronize_session=False)
            except Exception as e:
                logger.warning(f"Initial cleanup warning for {model.__name__}: {e}")
        
        # Commit our cleanup - if this fails, we'll catch it
        db_session.commit()
        
        # Create our test user
        user = User(
            user_id="test_user",
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=str(uuid.uuid4()),
            is_active=True,
            password_hash=generate_password_hash("test_password")
        )
        
        # Add and flush to detect any immediate database errors
        db_session.add(user)
        db_session.flush()
        
        # If we got here, we can commit
        db_session.commit()
        
        # Refresh to ensure we have the latest state
        db_session.refresh(user)
        
        # Mark our transaction as successful
        transaction_successful = True
        
        # Yield our user for the test
        yield user
        
    except Exception as e:
        # Log any errors we encountered
        logger.error(f"Test user fixture error: {str(e)}")
        db_session.rollback()
        raise
        
    finally:
        # Always try to clean up, but only if our main transaction succeeded
        if transaction_successful:
            try:
                for model, field, value in cleanup_queries:
                    try:
                        db_session.query(model).filter_by(
                            **{field: value}
                        ).delete(synchronize_session=False)
                    except Exception as e:
                        logger.warning(f"Cleanup warning for {model.__name__}: {e}")
                
                db_session.commit()
            except Exception as e:
                logger.warning(f"Final cleanup warning: {e}")
                db_session.rollback()   
@pytest.fixture(scope='function')
def session(db_session):
    """Compatibility alias for db_session"""
    return db_session

@pytest.fixture(scope='function')
def auth_manager(db_session):
    """Create auth manager instance"""
    return AuthManager(db_session)

class TestAuthentication:
    def test_login_success(self, client, test_user, db_session):
        """Test successful login with proper session handling"""
        response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'test_password'
        })
        
        assert response.status_code == 200
        data = response.json
        assert 'token' in data
        assert 'user' in data
        assert data['user']['id'] == test_user.user_id

    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid credentials"""
        response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'wrong_password'
        })
        
        assert response.status_code == 401
        assert 'error' in response.json

    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        response = client.post('/api/auth/login', json={})
        assert response.status_code == 400
        assert 'error' in response.json

    def test_session_validation(self, client, test_user):
        """Test session validation"""
        # First login to get token
        login_response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'test_password'
        })
        assert login_response.status_code == 200
        token = login_response.json['token']
        
        # Test validation endpoint
        response = client.get('/api/auth/validate', headers={
            'Authorization': f'Bearer {token}'
        })
        
        assert response.status_code == 200
        data = response.json
        assert data['valid'] is True
        assert data['user']['id'] == test_user.user_id

    def test_logout(self, client, test_user):
        """Test logout functionality"""
        # First login
        login_response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'test_password'
        })
        token = login_response.json['token']
        
        # Then logout
        response = client.post('/api/auth/logout', headers={
            'Authorization': f'Bearer {token}'
        })
        
        assert response.status_code == 200

        # Verify session is invalidated
        validate_response = client.get('/api/auth/validate', headers={
            'Authorization': f'Bearer {token}'
        })
        assert validate_response.status_code == 401

    def test_login_attempt_tracking(self, client, test_user, session):
        """Test tracking of login attempts"""
        # Make multiple failed attempts
        for _ in range(3):
            client.post('/api/auth/login', json={
                'username': 'test_user',
                'password': 'wrong_password'
            })
        
        # Verify login attempts are recorded
        login_history = session.query(LoginHistory).filter_by(
            user_id=test_user.user_id
        ).order_by(LoginHistory.login_time.desc()).all()
        
        assert len(login_history) >= 3
        assert all(h.status == 'failed' for h in login_history[:3])

    def test_account_lockout(self, client, test_user, session):
        """Test account lockout after multiple failed attempts"""
        security_config = SecurityConfig()
        max_attempts = security_config.BASE_SECURITY_SETTINGS['max_login_attempts']
        
        # Make max_attempts + 1 failed login attempts
        for _ in range(max_attempts + 1):
            response = client.post('/api/auth/login', json={
                'username': 'test_user',
                'password': 'wrong_password'
            })
        
        # Verify account is locked
        response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'test_password'  # Correct password
        })
        
        assert response.status_code == 401
        assert 'locked' in response.json['error'].lower()

        # Verify user record shows lockout
        session.refresh(test_user)
        assert test_user.failed_login_attempts >= max_attempts

    def test_concurrent_sessions(self, client, test_user, session):
        """Test handling of concurrent sessions"""
        security_config = SecurityConfig()
        max_sessions = security_config.BASE_SECURITY_SETTINGS['max_active_sessions']
        
        # Create multiple sessions
        tokens = []
        for _ in range(max_sessions):
            response = client.post('/api/auth/login', json={
                'username': 'test_user',
                'password': 'test_password'
            })
            assert response.status_code == 200
            tokens.append(response.json['token'])
        
        # Verify all sessions are valid
        for token in tokens:
            response = client.get('/api/auth/validate', headers={
                'Authorization': f'Bearer {token}'
            })
            assert response.status_code == 200

        # Try to create one more session beyond the limit
        response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'test_password'
        })
        # Should still succeed but oldest session should be invalidated
        assert response.status_code == 200

        # Verify oldest session is invalidated
        response = client.get('/api/auth/validate', headers={
            'Authorization': f'Bearer {tokens[0]}'
        })
        assert response.status_code == 401

    def test_session_expiry(self, client, test_user, session):
        """Test session expiration"""
        # Create a session
        response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'test_password'
        })
        assert response.status_code == 200
        token = response.json['token']
        
        # Manually expire the session in database
        user_session = db_session.query(UserSession).filter_by(
            token=token
        ).first()
        assert user_session is not None
        user_session.expires_at = datetime.now(timezone.utc)
        db_session.commit()
        
        # Verify session is invalid
        response = client.get('/api/auth/validate', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 401

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/api/auth/status')
        assert response.status_code == 200
        assert response.json['status'] == 'healthy'

    def test_login_rate_limiting(self, client, test_user):
        """Test rate limiting of login attempts"""
        # Make rapid login attempts
        responses = []
        for _ in range(10):
            response = client.post('/api/auth/login', json={
                'username': 'test_user',
                'password': 'wrong_password'
            })
            responses.append(response)

        # At least some of the rapid requests should be rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Rate limiting not active"

    def test_session_refresh(self, client, test_user):
        """Test session refresh functionality"""
        # First login
        login_response = client.post('/api/auth/login', json={
            'username': 'test_user',
            'password': 'test_password'
        })
        token = login_response.json['token']
        
        # Use session multiple times
        for _ in range(3):
            response = client.get('/api/auth/validate', headers={
                'Authorization': f'Bearer {token}'
            })
            assert response.status_code == 200

        # Session should still be valid due to refresh
        response = client.get('/api/auth/validate', headers={
            'Authorization': f'Bearer {token}'
        })
        assert response.status_code == 200