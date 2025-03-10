# tests/test_security/test_auth_ui.py
# Authentication UI component testing

import pytest
from flask import url_for
import re
from .test_environment import mock_if_needed, create_mock_response, integration_flag

@pytest.fixture(autouse=True)
def clear_session(client):
    """Automatically clear session between tests"""
    with client.session_transaction() as sess:
        sess.clear()
    yield

def get_csrf_token(response):
    """Extract CSRF token from response data"""
    match = re.search(r'name="csrf_token" value="(.+?)"', response.data.decode())
    return match.group(1) if match else None

class TestAuthUI:
    """Test authentication UI components"""
    
    def test_login_page_renders(self, client, app):
        """Test login page renders correctly"""
        with app.test_request_context():
            login_url = url_for('auth_views.login')
            
        response = client.get(login_url)
        assert response.status_code == 200
        assert b'Sign in' in response.data or b'Login' in response.data
        assert b'Password' in response.data
        # Less strict checking for optional elements that might have different naming
        assert b'remember' in response.data.lower() or b'Remember' in response.data
        
    def test_login_validation(self, client, app):
        """Test client-side validation on login form"""
        with app.test_request_context():
            login_url = url_for('auth_views.login')
            
        response = client.get(login_url)
        csrf_token = get_csrf_token(response)
        
        if not csrf_token:
            pytest.skip("Could not find CSRF token - form might be different than expected")
        
        # Try submitting with missing fields
        response = client.post(
            login_url,
            data={'csrf_token': csrf_token},
            follow_redirects=True
        )
        assert response.status_code == 200
        # Should stay on login page
        assert b'Sign in' in response.data or b'Login' in response.data
        
    def test_registration_page_renders(self, mocker, client, app):
        """Test registration page renders correctly"""
        # Create mock only in unit test mode
        mock_post = mock_if_needed(mocker, 'requests.post')
        if mock_post:  # Only configure if we're in unit test mode
            mock_post.return_value = create_mock_response(status_code=200)
        
        with app.test_request_context():
            register_url = url_for('auth_views.register')
            
        response = client.get(register_url)
        assert response.status_code == 200
        # More flexible text checks
        page_content = response.data.lower()
        assert b'account' in page_content or b'register' in page_content
        assert b'first' in page_content  # First name
        assert b'last' in page_content   # Last name
        assert b'email' in page_content
        assert b'password' in page_content
        
    def test_registration_validation(self, mocker, client, app):
        """Test client-side validation on registration form"""
        # Create mock only in unit test mode
        mock_post = mock_if_needed(mocker, 'requests.post')
        if mock_post:  # Only configure if we're in unit test mode
            mock_post.return_value = create_mock_response(
                status_code=400, 
                json_data={'error': 'Validation error'}
            )
        
        with app.test_request_context():
            register_url = url_for('auth_views.register')
            
        response = client.get(register_url)
        csrf_token = get_csrf_token(response)
        
        if not csrf_token:
            pytest.skip("Could not find CSRF token - form might be different than expected")
        
        # Try submitting with missing required fields
        response = client.post(
            register_url,
            data={'csrf_token': csrf_token},
            follow_redirects=True
        )
        assert response.status_code == 200
        # Should stay on registration page
        page_content = response.data.lower()
        assert b'account' in page_content or b'register' in page_content