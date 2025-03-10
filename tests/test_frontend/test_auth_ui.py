# tests/test_frontend/test_auth_ui.py
# pytest tests/test_frontend/test_auth_ui.py -v
import pytest
from flask import url_for
import re

def get_csrf_token(response):
    """Extract CSRF token from response data"""
    match = re.search(r'name="csrf_token" value="(.+?)"', response.data.decode())
    return match.group(1) if match else None

class TestAuthUI:
    """Test authentication UI flows"""
    
    def test_login_page_renders(self, client, app):
        """Test login page loads correctly"""
        with app.test_request_context():
            login_url = url_for('auth_views.login')
        
        # Set _anonymous=True to bypass login check
        response = client.get(login_url, environ_base={'_anonymous': True})
        assert response.status_code == 200
        assert b'password' in response.data.lower()
        
    def test_registration_page_renders(self, client, app):
        """Test registration page loads correctly"""
        with app.test_request_context():
            register_url = url_for('auth_views.register')
        
        response = client.get(register_url)
        assert response.status_code == 200
        assert b'Register' in response.data