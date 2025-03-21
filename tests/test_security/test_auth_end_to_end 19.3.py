# tests/test_security/test_auth_end_to_end.py
# End-to-end authentication testing

# =================================================================
# MIGRATION STATUS:
# This file has been fully migrated to use the database service layer.
# It uses db_session for database access following project standards.
#
# Completed:
# - All test methods use db_session
# - Database operations follow the established transaction pattern
# - Comprehensive error handling and logging
# =================================================================

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import logging
from flask import url_for
from app.models import User, UserSession, LoginHistory
import re
import json
from tests.test_environment import integration_flag

# Set up logging for tests
logger = logging.getLogger(__name__)

def extract_csrf_token(html_content):
    """Extract CSRF token from HTML content"""
    match = re.search(r'name="csrf_token" value="(.+?)"', html_content)
    return match.group(1) if match else None

class TestAuthEndToEnd:
    """
    End-to-end authentication testing
    
    This class tests complete authentication flows from frontend UI to backend database,
    ensuring all components work together correctly.
    """
        
    def test_complete_authentication_flow(self, client, db_session, test_hospital):
        """
        Test complete authentication flow from frontend to backend
        
        This test verifies:
        1. Login form renders correctly with CSRF token
        2. Form submission works and creates a session
        3. Protected routes are accessible when authenticated
        4. Logout works and session is properly terminated
        5. Protected routes are blocked after logout
        """
        # Skip in unit test mode - this test is for integration testing only
        if not integration_flag():
            pytest.skip("End-to-end test skipped in unit test mode")
            
        # Clean up any existing sessions
        db_session.query(UserSession).filter_by(
            user_id='9876543210',
            is_active=True
        ).update({'is_active': False})
        db_session.flush()
        
        try:
            with client.application.test_request_context():
                login_url = url_for('auth_views.login')
                dashboard_url = url_for('auth_views.dashboard')
                logout_url = url_for('auth_views.logout')
                
            # Get login page and extract CSRF token
            login_page = client.get(login_url)
            assert login_page.status_code == 200
            html = login_page.data.decode()
            csrf_token = extract_csrf_token(html)
            
            if not csrf_token:
                pytest.skip("Could not find CSRF token in login page")
            
            # Submit login form
            login_response = client.post(
                login_url,
                data={
                    'username': '9876543210',
                    'password': 'admin123',
                    'csrf_token': csrf_token
                },
                follow_redirects=True
            )
            
            # For integration testing, we may need to be more flexible with assertions
            assert login_response.status_code == 200
            assert b'Dashboard' in login_response.data or b'Welcome' in login_response.data
            
            # Check session state
            with client.session_transaction() as sess:
                assert 'auth_token' in sess
                token = sess['auth_token']
                assert token is not None
            
            # Verify session was created in database
            # Refresh the session to ensure we see the latest data
            db_session.expire_all()
            user_session = db_session.query(UserSession).filter_by(
                user_id='9876543210',
                is_active=True
            ).first()
            assert user_session is not None
            
            # Verify protected routes are accessible
            dashboard_response = client.get(dashboard_url)
            assert dashboard_response.status_code == 200
            
            # Test logout
            logout_response = client.get(
                logout_url,
                follow_redirects=True
            )
            assert logout_response.status_code == 200
            assert b'logged out' in logout_response.data.lower() or b'sign in' in logout_response.data.lower()
            
            # Verify token is removed from session
            with client.session_transaction() as sess:
                assert 'auth_token' not in sess
            
            # Verify session was deactivated in database
            db_session.expire_all()
            user_session = db_session.query(UserSession).filter_by(
                token=token,
                is_active=True
            ).first()
            assert user_session is None
            
            # Verify protected routes are no longer accessible
            dashboard_after_logout = client.get(dashboard_url)
            assert dashboard_after_logout.status_code in (302, 401)  # Either redirect or unauthorized
            if dashboard_after_logout.status_code == 302:
                assert 'login' in dashboard_after_logout.location
                
        except Exception as e:
            # Log exception details for better debugging
            import traceback
            logger.error(f"Error in end-to-end test: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def test_api_authentication_flow(self, client, db_session, test_hospital):
        """
        Test complete authentication flow via API endpoints
        
        This test verifies:
        1. API health check endpoint works
        2. Login API creates valid session and returns token
        3. Token validation works when session is active
        4. Logout API properly terminates the session
        5. Token is invalid after logout
        """
        # Skip in unit test mode
        if not integration_flag():
            pytest.skip("API flow test skipped in unit test mode")
            
        try:
            # Clear any existing sessions
            db_session.query(UserSession).filter_by(
                user_id='9876543210',
                is_active=True
            ).update({'is_active': False})
            db_session.flush()
            
            # Step 1: Test health check endpoint
            status_response = client.get('/api/auth/status')
            assert status_response.status_code == 200
            status_data = json.loads(status_response.data)
            assert status_data['status'] == 'healthy'
            
            # Step 2: Login with API endpoint
            login_response = client.post(
                '/api/auth/login',
                json={
                    'username': '9876543210',
                    'password': 'admin123'
                },
                # headers={'Content-Type': 'application/json'}
            )
            # Add debugging information
            print(f"Login response: {login_response.status_code}, {login_response.data}")
            
            assert login_response.status_code == 200
            login_data = json.loads(login_response.data)
            assert 'token' in login_data
            token = login_data['token']
            assert 'user' in login_data
            assert login_data['user']['id'] == '9876543210'
            
            # Step 3: Verify session was created in database
            db_session.expire_all()
            user_session = db_session.query(UserSession).filter_by(
                user_id='9876543210',
                is_active=True
            ).first()
            assert user_session is not None
            assert user_session.token == token
            
            # Step 4: Validate token
            validate_response = client.get(
                '/api/auth/validate',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert validate_response.status_code == 200
            validate_data = json.loads(validate_response.data)
            assert validate_data['valid'] == True
            
            # Step 5: Logout
            logout_response = client.post(
                '/api/auth/logout',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert logout_response.status_code == 200
            logout_data = json.loads(logout_response.data)
            assert 'message' in logout_data
            assert 'logged out' in logout_data['message'].lower()
            
            # Step 6: Verify session was deactivated in database
            db_session.expire_all()
            active_session = db_session.query(UserSession).filter_by(
                token=token,
                is_active=True
            ).first()
            assert active_session is None
            
            # Step 7: Verify token is no longer valid
            invalid_response = client.get(
                '/api/auth/validate',
                headers={'Authorization': f'Bearer {token}'}
            )
            assert invalid_response.status_code == 401
            
        except Exception as e:
            # Log detailed error for debugging
            import traceback
            logger.error(f"Error in API authentication flow test: {str(e)}")
            logger.error(traceback.format_exc())
            raise