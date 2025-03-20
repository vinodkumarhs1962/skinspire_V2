# tests/test_environment.py
# set INTEGRATION_TEST=0 && pytest tests/test_environment.py -v
# set INTEGRATION_TEST=1 && pytest tests/test_environment.py -v
import os
import pytest
import logging
from unittest.mock import MagicMock

# Set up logging for tests
logger = logging.getLogger(__name__)

# ==== ENVIRONMENT SETUP FUNCTION ====
def setup_test_environment():
    """
    Set up the test environment variables
    This function should be called before any application imports
    """
    # Set critical environment variables for testing if not already set
    if os.environ.get('FLASK_ENV') != 'testing':
        os.environ['FLASK_ENV'] = 'testing'
        logger.info("Set FLASK_ENV=testing")
        
    if not os.environ.get('TEST_DATABASE_URL'):
        os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        logger.info("Set TEST_DATABASE_URL for testing database")
        
    os.environ['USE_NESTED_TRANSACTIONS'] = 'False'
    
    # Add CSRF bypass configuration
    os.environ['BYPASS_CSRF'] = os.environ.get('BYPASS_CSRF', 'True')
    logger.info(f"CSRF Bypass configured: {os.environ['BYPASS_CSRF']}")
    

    return True

# Call setup automatically when this module is imported
# This ensures the environment is configured regardless of how the module is used
environment_configured = setup_test_environment()
logger.info(f"Test environment configured: {environment_configured}")

# Add CSRF bypass function
def get_csrf_bypass_flag():
    """
    Return the current CSRF bypass mode flag
    
    Returns:
        bool: True if CSRF should be bypassed, False otherwise
    """
    return os.environ.get('BYPASS_CSRF', 'True').lower() in ('true', '1', 'yes')

# Add a pytest fixture for CSRF bypass
@pytest.fixture
def test_client(client):
    """
    Create a test client with configurable CSRF settings
    
    Uses the centralized CSRF bypass configuration
    """
    # Determine CSRF bypass status
    bypass_csrf = get_csrf_bypass_flag()
    
    if bypass_csrf:
        logger.info("CSRF protection disabled for tests")
        client.application.config['WTF_CSRF_ENABLED'] = False
    else:
        logger.info("CSRF protection enabled for tests")
        
    yield client
    
    # Reset after the test
    if bypass_csrf:
        client.application.config['WTF_CSRF_ENABLED'] = True

# Optionally, add a test to verify CSRF bypass configuration
def test_csrf_bypass_configuration():
    """
    Verify the CSRF bypass configuration mechanism
    """
    bypass_flag = get_csrf_bypass_flag()
    assert isinstance(bypass_flag, bool), "CSRF bypass flag should be a boolean"

def verify_database_connection():
    """Verify correct database connection for testing"""
    from sqlalchemy import text
    from app.services.database_service import get_db_session, get_active_env
    
    env = get_active_env()
    if env != 'testing':
        logger.warning(f"Wrong environment: {env} (should be 'testing')")
        return False
    
    try:
        with get_db_session() as session:
            db_name = session.execute(text("SELECT current_database()")).scalar()
            
            if 'test' not in db_name.lower():
                logger.warning(f"Connected to wrong database: {db_name}")
                return False
                
            logger.info(f"Verified correct test database connection: {db_name}")
            return True
    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}")
        return False    

# Global flags to determine testing modes
# Default to integration mode off, but can be enabled via environment variable
INTEGRATION_MODE = os.environ.get("INTEGRATION_TEST", "0") == "1"

def integration_flag():
    """
    Return the current integration test mode flag
    
    This function dynamically checks the environment variable each time
    it's called, with a default of False (unit test mode) if not specified.
    
    Returns:
        bool: True if running in integration test mode, False otherwise
    """
    # Explicitly check for "1" to ensure we only enter integration mode when requested
    return os.environ.get("INTEGRATION_TEST", "0") == "1"

def mock_if_needed(mocker, target, integration_mode=None):
    """
    Create a mock only if we're in unit test mode
    """
    if integration_mode is None:
        integration_mode = integration_flag()
        
    if not integration_mode:
        logger.debug(f"Creating mock for {target} (unit test mode)")
        return mocker.patch(target)
        
    logger.debug(f"Skipping mock for {target} (integration test mode)")
    return None

def create_mock_response(status_code=200, json_data=None, text=None, headers=None):
    """
    Create a mock response object that mimics requests.Response
    """
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    
    if json_data is not None:
        mock_resp.json = lambda: json_data
    
    if text is not None:
        type(mock_resp).text = text
        
    if headers is not None:
        mock_resp.headers = headers
    
    return mock_resp

def mock_db_session(mocker, results=None, integration_mode=None):
    """
    Create a mock database session with pre-configured results
    """
    if integration_mode is None:
        integration_mode = integration_flag()
        
    if integration_mode:
        logger.debug("Skipping database session mock in integration mode")
        return None
    
    # Create mock session
    mock_session = MagicMock()
    
    # Configure mock with results if provided
    if results:
        for query_desc, result in results.items():
            parts = query_desc.split('.')
            current = mock_session
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    if callable(getattr(current, part, None)):
                        getattr(current, part).return_value = result
                    else:
                        setattr(current, part, result)
                else:
                    if not hasattr(current, part) or getattr(current, part) is None:
                        setattr(current, part, MagicMock())
                    current = getattr(current, part)
    
    return mock_session

def get_test_data_helper(db_session, model_class, identifier, identifier_field='id'):
    """
    Helper to get test data consistently across test modules
    """
    try:
        filter_kwargs = {identifier_field: identifier}
        return db_session.query(model_class).filter_by(**filter_kwargs).first()
    except Exception as e:
        logger.error(f"Error fetching test data: {str(e)}")
        return None

# Existing tests remain the same
def test_integration_mode_detection():
    """
    Verify the integration mode detection mechanism
    """
    expected = os.environ.get("INTEGRATION_TEST", "0") == "1"
    assert INTEGRATION_MODE == expected, "INTEGRATION_MODE should match INTEGRATION_TEST environment variable"

def test_integration_flag():
    """
    Test the integration flag functionality
    """
    result = integration_flag()
    assert isinstance(result, bool), "Integration flag should be a boolean"

def test_mock_creation(mocker):
    """
    Test mock creation based on integration mode
    """
    if not INTEGRATION_MODE:
        try:
            mock = mocker.patch('os.path.exists')
            mock.return_value = True
            
            assert os.path.exists('some/path') is True, "Mock should return predefined value"
        except Exception as e:
            pytest.fail(f"Failed to create mock in unit test mode: {str(e)}")
    else:
        with pytest.raises(Exception):
            mocker.patch('os.path.exists')

def test_mock_response_creation():
    """
    Test creating a mock response
    """
    mock_resp = create_mock_response(status_code=200)
    assert mock_resp.status_code == 200, "Mock response should have default status code"

def test_database_session_mocking(mocker):
    """
    Test database session mocking behavior
    """
    from app.services.database_service import get_db_session
    
    if not INTEGRATION_MODE:
        mock_session = mocker.Mock()
        mocker.patch('app.services.database_service.get_db_session', return_value=mock_session)
        
        with get_db_session() as session:
            assert session is not None, "Should create a mock session in unit test mode"
    else:
        with get_db_session() as session:
            assert session is not None, "Should create a real database session in integration mode"

def test_error_handling():
    """
    Test basic error handling mechanism
    """
    try:
        if not INTEGRATION_MODE:
            raise ValueError("Simulated error in unit test mode")
    except ValueError as e:
        assert str(e) == "Simulated error in unit test mode", "Error message should match"

def setup_module(module):
    """
    Module level setup function
    """
    logger.info("Starting test module for environment")
    logger.info(f"Current Integration Mode: {INTEGRATION_MODE}")
    logger.info(f"INTEGRATION_TEST Environment Variable: {os.environ.get('INTEGRATION_TEST', 'Not Set')}")