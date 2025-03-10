# tests/test_security/test_auth_views.py

import pytest
from flask import url_for, session
from flask_login import current_user
from app.models.transaction import User

class TestAuthViews:
    """Test suite for authentication views"""
    
    def test_index_redirects_to_login(self, client):
        """Test that index redirects to login page"""
        response = client.get(url_for('auth_views.index'))
        assert response.status_code == 302
        assert url_for('auth_views.login') in response.location
    
    def test_login_page_loads(self, client):
        """Test that login page loads correctly"""
        response = client.get(url_for('auth_views.login'))
        assert response.status_code == 200
        assert b'Login' in response.data
    
    def test_login_form_validation(self, client):
        """Test login form validation"""
        # Test with empty form data
        response = client.post(
            url_for('auth_views.login'),
            data={},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'This field is required' in response.data
        
        # Get CSRF token for valid submission
        login_page = client.get(url_for('auth_views.login'))
        html = login_page.data.decode()
        import re
        csrf_token = re.search('name="csrf_token" value="(.+?)"', html).group(1)
        
        # Test with invalid credentials
        response = client.post(
            url_for('auth_views.login'),
            data={
                'username': 'nonexistent',
                'password': 'wrongpassword',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'Invalid credentials' in response.data
    
    def test_login_success(self, client, monkeypatch, admin_user):
        """Test successful login"""
        # Get CSRF token
        login_page = client.get(url_for('auth_views.login'))
        html = login_page.data.decode()
        import re
        csrf_token = re.search('name="csrf_token" value="(.+?)"', html).group(1)
        
        # Mock the API response
        class MockResponse:
            status_code = 200
            def json(self):
                return {'token': 'test_token_123', 'user': {'id': admin_user.user_id}}
                
        def mock_post(*args, **kwargs):
            return MockResponse()
            
        import requests
        monkeypatch.setattr(requests, "post", mock_post)
        
        # Test login
        response = client.post(
            url_for('auth_views.login'),
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
            assert sess['auth_token'] == 'test_token_123'
    
    def test_dashboard_requires_login(self, client):
        """Test that dashboard requires login"""
        response = client.get(url_for('auth_views.dashboard'))
        assert response.status_code == 302
        assert 'login' in response.location
    
    def test_logout(self, client, monkeypatch):
        """Test logout functionality"""
        # Setup session with auth token
        with client.session_transaction() as sess:
            sess['auth_token'] = 'test_token_123'
            
        # Mock the API response for logout
        class MockResponse:
            status_code = 200
            def json(self):
                return {'message': 'Successfully logged out'}
                
        def mock_post(*args, **kwargs):
            return MockResponse()
            
        import requests
        monkeypatch.setattr(requests, "post", mock_post)
        
        # Test logout
        response = client.get(
            url_for('auth_views.logout'),
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b'You have been logged out' in response.data
        
        # Verify token is removed from session
        with client.session_transaction() as sess:
            assert 'auth_token' not in sess