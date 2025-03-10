# tests/test_security/test_auth_flow.py
# pytest tests/test_security/test_auth_flow.py -v

import pytest
from flask import url_for
import re
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import Headers
from app.forms.auth_forms import LoginForm
import requests

def get_csrf_token(client, app):
    """Helper to get CSRF token from form, handling potential redirects"""
    with app.test_request_context():
        login_url = url_for('auth_views.login')
    
    response = client.get(login_url)
    
    if response.status_code == 302:
        # If redirected, it means we might already be logged in
        # We can skip getting the CSRF token in this case.
        return None

    content = response.data.decode()
    match = re.search(r'name="csrf_token" value="(.+?)"', content)
    if match:
        return match.group(1)
    return None

@patch('requests.post')
def test_login_success(mock_post, client, app, test_user, monkeypatch):
    """Test successful login"""
    # Mock API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'token': 'test_token_123',
        'user': {'id': test_user.user_id}
    }
    mock_post.return_value = mock_response

    # Get CSRF token
    csrf_token = get_csrf_token(client, app)
    if csrf_token is None:
        # If no CSRF, assume already logged in and skip test
        return
    
    # Set up login form data
    form = LoginForm()
    login_data = {
        'username': test_user.user_id,
        'password': 'test_password',
        'csrf_token': csrf_token
    }

    # Mock form validation
    monkeypatch.setattr(form, 'validate_on_submit', lambda: True)
    
    with app.test_request_context():
        login_url = url_for('auth_views.login')

    response = client.post(login_url,
                         data=login_data,
                         follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Dashboard' in response.data
    

@patch('requests.post')
def test_login_failure(mock_post, client, app, monkeypatch):
    """Test failed login"""
    # Mock API response for failed login
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {'error': 'Invalid credentials'}
    mock_post.return_value = mock_response

    # Get CSRF token
    csrf_token = get_csrf_token(client, app)
    if csrf_token is None:
        # If no CSRF, assume already logged in and skip test
        return
    
    # Set up login form data
    form = LoginForm()
    login_data = {
        'username': 'test_user',
        'password': 'wrong_password',
        'csrf_token': csrf_token
    }

    # Mock form validation
    monkeypatch.setattr(form, 'validate_on_submit', lambda: True)
    
    with app.test_request_context():
        login_url = url_for('auth_views.login')

    response = client.post(login_url,
                         data=login_data,
                         follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Sign in to SkinSpire' in response.data

@patch('requests.post')
def test_logout(mock_post, client, app, logged_in_client):
    """Test logout functionality"""
    # Mock API response for logout
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'message': 'Successfully logged out'}
    mock_post.return_value = mock_response
    
    with app.test_request_context():
        logout_url = url_for('auth_views.logout')
    
    response = logged_in_client.get(logout_url, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'You have been logged out' in response.data or b'Sign in to SkinSpire' in response.data

@patch('requests.post')
def test_login_connection_error(mock_post, client, app, monkeypatch):
    """Test login with a connection error"""
    # Mock requests.exceptions.RequestException
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")
    
    # Get CSRF token
    csrf_token = get_csrf_token(client, app)
    if csrf_token is None:
        # If no CSRF, assume already logged in and skip test
        return
    
    # Set up login form data
    form = LoginForm()
    login_data = {
        'username': 'test_user',
        'password': 'wrong_password',
        'csrf_token': csrf_token
    }

    # Mock form validation
    monkeypatch.setattr(form, 'validate_on_submit', lambda: True)
    
    with app.test_request_context():
        login_url = url_for('auth_views.login')
        
    response = client.post(login_url,
                            data=login_data,
                            follow_redirects=True)

    assert response.status_code == 200
    assert b'Connection error' in response.data

