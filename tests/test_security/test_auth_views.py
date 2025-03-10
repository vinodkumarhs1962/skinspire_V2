# tests/test_security/test_auth_views.py

import pytest
from flask import url_for, session
from flask_login import current_user
from app.models.transaction import User
import re
import requests
from .test_environment import mock_if_needed, create_mock_response, integration_flag

class TestAuthViews:
    """Test suite for authentication views"""
    
    def test_index_redirects_to_login(self, client, app):
        """Test that index redirects to login page"""
        with app.test_request_context():
            index_url = url_for('auth_views.index')
            login_url = url_for('auth_views.login')
            
        response = client.get(index_url)
        assert response.status_code == 302
        assert login_url in response.location
    
    def test_login_page_loads(self, client, app):
        """Test that login page loads correctly"""
        with app.test_request_context():
            login_url = url_for('auth_views.login')
            
        response = client.get(login_url)
        assert response.status_code == 200
        assert b'Sign in' in response.data or b'Login' in response.data
    
    def test_login_form_validation(self, client, app):
        """Test login form validation"""
        with app.test_request_context():
            login_url = url_for('auth_views.login')
            
        # Get CSRF token for valid submission
        login_page = client.get(login_url)
        html = login_page.data.decode()
        csrf_match = re.search('name="csrf_token" value="(.+?)"', html)
        
        if not csrf_match:
            pytest.skip("Could not find CSRF token in login page")
            
        csrf_token = csrf_match.group(1)
        
        # Test with empty form data
        response = client.post(
            login_url,
            data={'csrf_token': csrf_token},
            follow_redirects=True
        )
        assert response.status_code == 200
        # Should stay on login page
        assert b'Sign in' in response.data or b'Login' in response.data
    
    def test_login_success(self, mocker, client, app, admin_user):
        """Test successful login"""
        # Create mock only in unit test mode
        mock_post = mock_if_needed(mocker, 'requests.post')
        if mock_post:  # Only configure if we're in unit test mode
            mock_post.return_value = create_mock_response(
                status_code=200,
                json_data={'token': 'test_token_123', 'user': {'id': admin_user.user_id}}
            )
        
        with app.test_request_context():
            login_url = url_for('auth_views.login')
            
        # Get CSRF token
        login_page = client.get(login_url)
        html = login_page.data.decode()
        csrf_match = re.search('name="csrf_token" value="(.+?)"', html)
        
        if not csrf_match:
            pytest.skip("Could not find CSRF token in login page")
            
        csrf_token = csrf_match.group(1)
        
        # Test login
        response = client.post(
            login_url,
            data={
                'username': admin_user.user_id,
                'password': 'admin123',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'Dashboard' in response.data
        
        # Verify session contains token
        with client.session_transaction() as sess:
            assert 'auth_token' in sess
            if not integration_flag():
                # In unit test mode, we know the expected token
                assert sess['auth_token'] == 'test_token_123'
    
    def test_dashboard_requires_login(self, client, app):
        """Test that dashboard requires login"""
        with app.test_request_context():
            dashboard_url = url_for('auth_views.dashboard')
            
        response = client.get(dashboard_url)
        # Could be either 302 (redirect) or 401 (unauthorized) depending on implementation
        assert response.status_code in (302, 401)
        if response.status_code == 302:
            assert 'login' in response.location
    
    def test_logout(self, mocker, client, app):
        """Test logout functionality"""
        # Create mock only in unit test mode
        mock_post = mock_if_needed(mocker, 'requests.post')
        if mock_post:  # Only configure if we're in unit test mode
            mock_post.return_value = create_mock_response(
                status_code=200,
                json_data={'message': 'Successfully logged out'}
            )
        
        with app.test_request_context():
            logout_url = url_for('auth_views.logout')
            
        # Setup session with auth token
        with client.session_transaction() as sess:
            sess['auth_token'] = 'test_token_123'
        
        # Test logout
        response = client.get(
            logout_url,
            follow_redirects=True
        )
        assert response.status_code == 200
        # Check for either "logged out" or "sign in" text
        page_text = response.data.lower()
        assert b'logged out' in page_text or b'sign in' in page_text or b'login' in page_text
        
        # Verify token is removed from session
        with client.session_transaction() as sess:
            assert 'auth_token' not in sess