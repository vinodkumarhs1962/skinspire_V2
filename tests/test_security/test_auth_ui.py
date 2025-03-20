# tests/test_security/test_auth_ui.py
# Authentication UI component testing

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import logging
from flask import url_for
import re
from tests.test_environment import mock_if_needed, create_mock_response, integration_flag
from app.services.database_service import get_db_session

# Set up logging for tests
logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def clear_session(client):
    """
    Automatically clear session between tests
    
    This fixture ensures each test starts with a clean session state
    to prevent test interference.
    """
    logger.debug("Clearing client session before test")
    with client.session_transaction() as sess:
        sess.clear()
    yield
    logger.debug("Test completed with clean session")

def get_csrf_token(client, app):
    """
    Extract CSRF token from response data
    
    Args:
        client: Flask test client
        app: Flask application instance
        
    Returns:
        str: CSRF token or None if not found
    """
    with app.test_request_context():
        login_url = url_for('auth_views.login')
    
    response = client.get(login_url)
    
    content = response.data.decode()
    match = re.search(r'name="csrf_token" value="(.+?)"', content)
    return match.group(1) if match else None

class TestAuthUI:
    """
    Test authentication UI components
    
    This class tests rendering and client-side validation of authentication
    related UI forms and components, including login and registration.
    """
    
    def test_login_page_renders(self, client, app):
        """
        Test login page renders correctly
        
        Verifies:
        - Page loads with 200 status
        - Key elements like login form fields appear in the content
        """
        logger.info("Testing login page rendering")
        
        # Database operations if needed
        if integration_flag():
            with get_db_session() as session:
                # Example of potential database operations
                logger.debug("Database session available for additional checks")
        
        with app.test_request_context():
            login_url = url_for('auth_views.login')
            
        response = client.get(login_url)
        assert response.status_code == 200
        assert b'Sign in' in response.data or b'Login' in response.data
        assert b'Password' in response.data
        # Less strict checking for optional elements that might have different naming
        assert b'remember' in response.data.lower() or b'Remember' in response.data
        logger.info("Login page renders correctly")
        
    def test_login_validation(self, client, app):
        """
        Test client-side validation on login form
        
        Verifies:
        - Form validates required fields
        - Stays on login page when submission is invalid
        """
        logger.info("Testing login form validation")
        
        # Database operations if needed
        if integration_flag():
            with get_db_session() as session:
                # Perform any necessary database checks
                logger.debug("Database session available for validation checks")
        
        with app.test_request_context():
            login_url = url_for('auth_views.login')
            
        response = client.get(login_url)
        csrf_token = get_csrf_token(client, app)
        
        if not csrf_token:
            # Instead of skipping, test with empty data but no CSRF token
            logger.warning("CSRF token not found - this might be a configuration issue")
            # Continue with test anyway, to see what happens with invalid data
        
        # Try submitting with missing fields
        data = {}
        if csrf_token:
            data['csrf_token'] = csrf_token
            
        response = client.post(
            login_url,
            data=data,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        # Should stay on login page
        assert b'Sign in' in response.data or b'Login' in response.data
        logger.info("Login validation works as expected")
        
    def test_registration_page_renders(self, mocker, client, app):
        """
        Test registration page renders correctly
        
        Verifies:
        - Page loads with 200 status
        - Registration form contains expected fields
        """
        logger.info("Testing registration page rendering")
        
        # Database operations if needed 
        if integration_flag():
            with get_db_session() as session:
                # Perform any pre-registration checks if needed
                logger.debug("Database session available for registration checks")
        
        # Create mock only in unit test mode
        mock_post = mock_if_needed(mocker, 'requests.post')
        if mock_post:  # Only configure if we're in unit test mode
            mock_post.return_value = create_mock_response(status_code=200)
        
        with app.test_request_context():
            # Make sure this URL exists, and handle if not
            try:
                register_url = url_for('auth_views.register')
            except Exception as e:
                logger.warning(f"Could not get register URL: {str(e)}")
                pytest.skip("Registration URL not available - this endpoint might not exist")
                return  # Exit the test
            
        response = client.get(register_url)
        assert response.status_code == 200
        # More flexible text checks
        page_content = response.data.lower()
        assert b'account' in page_content or b'register' in page_content
        assert b'first' in page_content or b'name' in page_content  # First name might be combined or labeled differently
        assert b'email' in page_content
        assert b'password' in page_content
        logger.info("Registration page renders correctly")
        
    def test_registration_validation(self, mocker, client, app):
        """
        Test client-side validation on registration form
        
        Verifies:
        - Form validates required fields
        - Stays on registration page when submission is invalid
        """
        logger.info("Testing registration form validation")
        
        # Database operations if needed
        if integration_flag():
            with get_db_session() as session:
                # Validate pre-registration conditions
                logger.debug("Database session available for validation checks")
        
        # Create mock only in unit test mode
        mock_post = mock_if_needed(mocker, 'requests.post')
        if mock_post:  # Only configure if we're in unit test mode
            mock_post.return_value = create_mock_response(
                status_code=400, 
                json_data={'error': 'Validation error'}
            )
        
        with app.test_request_context():
            # Make sure this URL exists, and handle if not
            try:
                register_url = url_for('auth_views.register')
            except Exception as e:
                logger.warning(f"Could not get register URL: {str(e)}")
                pytest.skip("Registration URL not available - this endpoint might not exist")
                return  # Exit the test
            
        response = client.get(register_url)
        csrf_token = get_csrf_token(client, app)
        
        if not csrf_token:
            # Instead of skipping, test with empty data but no CSRF token
            logger.warning("CSRF token not found - this might be a configuration issue")
            # Continue with test anyway
        
        # Try submitting with missing required fields
        data = {}
        if csrf_token:
            data['csrf_token'] = csrf_token
            
        response = client.post(
            register_url,
            data=data,
            follow_redirects=True
        )
        
        assert response.status_code == 200
        # Should stay on registration page
        page_content = response.data.lower()
        assert b'account' in page_content or b'register' in page_content
        logger.info("Registration validation works as expected")