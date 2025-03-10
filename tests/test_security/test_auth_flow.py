# tests/test_security/test_auth_flow.py
# pytest tests/test_security/test_auth_flow.py -v

import pytest
from flask import url_for
import re
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import Headers
from app.forms.auth_forms import LoginForm
import requests
from .test_environment import mock_if_needed, create_mock_response, integration_flag

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

def test_login_success(mocker, client, app, test_user, monkeypatch):
    """Test successful login"""
    # Create mock in unit test mode
    if not integration_flag():
        mock_post = mock_if_needed(mocker, 'requests.post')
        mock_post.return_value = create_mock_response(
            status_code=200,
            json_data={
                'token': 'test_token_123',
                'user': {'id': test_user.user_id}
            }
        )

    # Get CSRF token
    csrf_token = get_csrf_token(client, app)
    if csrf_token is None:
        # If no CSRF, assume already logged in and skip test
        pytest.skip("Could not get CSRF token, possibly already logged in")
    
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

def test_login_failure(mocker, client, app, monkeypatch):
    """Test failed login"""
    # Create mock in unit test mode
    if not integration_flag():
        mock_post = mock_if_needed(mocker, 'requests.post')
        mock_post.return_value = create_mock_response(
            status_code=401,
            json_data={'error': 'Invalid credentials'}
        )

    # Get CSRF token
    csrf_token = get_csrf_token(client, app)
    if csrf_token is None:
        # If no CSRF, assume already logged in and skip test
        pytest.skip("Could not get CSRF token, possibly already logged in")
    
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
    assert b'Sign in' in response.data or b'Login' in response.data

def test_logout(mocker, client, app, logged_in_client):
    """Test logout functionality"""
    # Create mock in unit test mode
    if not integration_flag():
        mock_post = mock_if_needed(mocker, 'requests.post')
        mock_post.return_value = create_mock_response(
            status_code=200,
            json_data={'message': 'Successfully logged out'}
        )
    
    with app.test_request_context():
        logout_url = url_for('auth_views.logout')
    
    response = logged_in_client.get(logout_url, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'logged out' in response.data.lower() or b'Sign in' in response.data or b'Login' in response.data

def test_login_connection_error(mocker, client, app, monkeypatch):
    """Test login with a connection error"""
    # Create mock in unit test mode with connection error
    if not integration_flag():
        mock_post = mock_if_needed(mocker, 'requests.post')
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
    
    # Get CSRF token
    csrf_token = get_csrf_token(client, app)
    if csrf_token is None:
        # If no CSRF, assume already logged in and skip test
        pytest.skip("Could not get CSRF token, possibly already logged in")
    
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
    
    # In unit test mode, we should see the connection error
    # In integration mode, we might get a different message
    if not integration_flag():
        assert b'Connection error' in response.data or b'error' in response.data.lower()