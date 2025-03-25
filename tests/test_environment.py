# tests/test_environment.py
# set INTEGRATION_TEST=0 && pytest tests/test_environment.py -v
# set INTEGRATION_TEST=1 && pytest tests/test_environment.py -v
import os
import sys
import pytest
import logging
from unittest.mock import MagicMock

# Import the centralized environment handling
from app.core.environment import Environment, current_env

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== ENVIRONMENT SETUP FUNCTION ====
def setup_test_environment():
    """
    Set up the test environment variables
    This function should be called before any application imports
    """
    # Log initial environment state
    logger.debug(f"Initial environment: {current_env}")
    
    # Use the centralized environment system to set testing environment
    Environment.set_environment('testing')
    logger.info(f"Environment set to: {current_env}")
    
    # Set critical environment variables for testing if not already set
    if not os.environ.get('TEST_DATABASE_URL'):
        os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        logger.info("Set TEST_DATABASE_URL for testing database")
        
    os.environ['USE_NESTED_TRANSACTIONS'] = 'False'
    logger.info("Disabled nested transactions for testing")
    
    # Ensure INTEGRATION_TEST is set
    if 'INTEGRATION_TEST' not in os.environ:
        os.environ['INTEGRATION_TEST'] = '1'  # Default to integration mode
        logger.info("Default INTEGRATION_TEST=1 (integration mode)")
    
    # Add CSRF bypass configuration - default to True for testing
    if 'BYPASS_CSRF' not in os.environ:
        os.environ['BYPASS_CSRF'] = 'True'
    logger.info(f"CSRF Bypass configured: {os.environ['BYPASS_CSRF']}")
    
    # Log final state after setup
    logger.debug(f"Final environment: {current_env}")
    logger.debug(f"Final INTEGRATION_TEST: {os.environ.get('INTEGRATION_TEST')}")
    logger.debug(f"Final BYPASS_CSRF: {os.environ.get('BYPASS_CSRF')}")
    
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

# Enhanced database verification function
def verify_database_connection():
    """
    Verify correct database connection for testing
    
    Returns:
        bool: True if connected to the test database, False otherwise
    """
    try:
        from sqlalchemy import text
        from app.services.database_service import get_db_session
        
        # Check environment
        if not Environment.is_testing():
            logger.warning(f"Wrong environment: {current_env} (should be 'testing')")
            return False
        
        try:
            with get_db_session() as session:
                # Check that we're connected to the test database
                db_name = session.execute(text("SELECT current_database()")).scalar()
                
                if 'test' not in db_name.lower():
                    logger.warning(f"Connected to wrong database: {db_name}")
                    return False
                    
                # Log success
                logger.info(f"Verified correct test database connection: {db_name}")
                
                # Additional verification - check if we can query a table
                try:
                    tables = session.execute(text(
                        "SELECT table_name FROM information_schema.tables " +
                        "WHERE table_schema = 'public'"
                    )).fetchall()
                    logger.debug(f"Database contains {len(tables)} tables")
                except Exception as e:
                    logger.warning(f"Could not query tables: {str(e)}")
                
                return True
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            return False
    except ImportError as e:
        logger.error(f"Import error during database verification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Database verification failed: {str(e)}")
        return False    

# Global flag to determine testing mode
# Default to integration mode on, but can be disabled via environment variable
def integration_flag():
    """
    Return the current integration test mode flag
    
    This function dynamically checks the environment variable each time
    it's called, with a default of True (integration mode) if not specified.
    
    Returns:
        bool: True if running in integration test mode, False otherwise
    """
    # Convert to lowercase string first to handle various formats
    int_test_val = os.environ.get("INTEGRATION_TEST", "1").lower()
    
    # Return False only for explicit "0", "false", or "no"
    return int_test_val not in ("0", "false", "no")

# Global constant for initial state - but prefer the function for dynamic checking
INTEGRATION_MODE = integration_flag()

# Document the integration mode at module import time
logger.info(f"Integration mode is {'ENABLED' if INTEGRATION_MODE else 'DISABLED'}")

def mock_if_needed(mocker, target, integration_mode=None):
    """
    Create a mock only if we're in unit test mode
    
    Args:
        mocker: pytest-mock fixture
        target: Target to patch
        integration_mode: Override for integration mode flag
        
    Returns:
        Mock object or None
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
    
    Args:
        status_code: HTTP status code
        json_data: Data to return from .json() method
        text: Text content for the response
        headers: Response headers dictionary
        
    Returns:
        MagicMock configured to behave like a requests.Response object
    """
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    
    if json_data is not None:
        mock_resp.json = lambda: json_data
    
    if text is not None:
        mock_resp.text = text
        
    if headers is not None:
        mock_resp.headers = headers
    
    return mock_resp

def mock_db_session(mocker, results=None, integration_mode=None):
    """
    Create a mock database session with pre-configured results
    
    Args:
        mocker: pytest-mock fixture
        results: Dictionary of query path to result mappings
        integration_mode: Override for integration mode flag
        
    Returns:
        MagicMock configured to behave like a SQLAlchemy session
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
    
    Args:
        db_session: SQLAlchemy session
        model_class: Model class to query
        identifier: Value to search for
        identifier_field: Field name to filter by
        
    Returns:
        Model instance or None
    """
    try:
        filter_kwargs = {identifier_field: identifier}
        return db_session.query(model_class).filter_by(**filter_kwargs).first()
    except Exception as e:
        logger.error(f"Error fetching test data: {str(e)}")
        return None

# Diagnostics - functions for troubleshooting test environment
def diagnose_environment():
    """Print diagnostic information about the test environment"""
    logger.info("=== Test Environment Diagnostic ===")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Application Environment: {current_env}")
    logger.info(f"Integration Mode: {integration_flag()}")
    logger.info(f"CSRF Bypass: {get_csrf_bypass_flag()}")
    logger.info(f"Environment Variables:")
    for key in sorted(['FLASK_ENV', 'FLASK_APP', 'PYTHONPATH', 'INTEGRATION_TEST', 'BYPASS_CSRF', 'SKINSPIRE_ENV']):
        logger.info(f"  {key}: {os.environ.get(key, 'Not set')}")
    logger.info("=================================")

# Add a new test for the centralized environment
def test_environment_system():
    """Test the centralized environment system"""
    # Test that we're in testing mode
    assert current_env == 'testing', f"Current environment should be 'testing', found '{current_env}'"
    
    # Test environment normalization
    assert Environment.normalize_env('test') == 'testing'
    assert Environment.normalize_env('dev') == 'development'
    assert Environment.normalize_env('prod') == 'production'
    
    # Test short name conversion
    assert Environment.get_short_name('testing') == 'test'
    assert Environment.get_short_name('development') == 'dev'
    assert Environment.get_short_name('production') == 'prod'
    
    # Test environment checks
    assert Environment.is_testing() == True
    assert Environment.is_development() == False
    assert Environment.is_production() == False

# Existing tests remain the same
def test_integration_mode_detection():
    """
    Verify the integration mode detection mechanism
    """
    # Get current environment setting for comparison
    expected = os.environ.get("INTEGRATION_TEST", "1").lower() not in ("0", "false", "no")
    actual = integration_flag()
    assert actual == expected, f"Integration flag returned {actual}, expected {expected}"

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
    if not integration_flag():
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
    if not integration_flag():
        mock_session = mocker.Mock()
        mocker.patch('app.services.database_service.get_db_session', return_value=mock_session)
    
        import contextlib
        # Mock a context manager for the session
        class MockSessionContext:
            def __enter__(self):
                return mock_session
            def __exit__(self, *args):
                pass
            
        from app.services.database_service import get_db_session
        mocker.patch('app.services.database_service.get_db_session', return_value=MockSessionContext())
        
        with get_db_session() as session:
            assert session is not None, "Should create a mock session in unit test mode"
    else:
        try:
            from app.services.database_service import get_db_session
            with get_db_session() as session:
                assert session is not None, "Should create a real database session in integration mode"
        except ImportError:
            pytest.skip("Database service not available - skipping test")

def test_error_handling():
    """
    Test basic error handling mechanism
    """
    try:
        if not integration_flag():
            raise ValueError("Simulated error in unit test mode")
    except ValueError as e:
        assert str(e) == "Simulated error in unit test mode", "Error message should match"

def test_csrf_bypass_configuration():
    """
    Verify the CSRF bypass configuration mechanism
    """
    bypass_flag = get_csrf_bypass_flag()
    assert isinstance(bypass_flag, bool), "CSRF bypass flag should be a boolean"
    # Default value should be True for testing
    if 'BYPASS_CSRF' not in os.environ:
        assert bypass_flag is True, "Default CSRF bypass setting should be True"

def setup_module(module):
    """
    Module level setup function
    """
    diagnose_environment()