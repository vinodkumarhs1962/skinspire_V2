# Technical Guide: Managing Database Environments in Flask Testing

## Root Cause Analysis

The issue we encountered was a classic environment initialization sequence problem. The application attempted to connect to a database before the correct environment variables were set, resulting in the wrong database URL being used.

### Detailed Issue:
1. Flask environment was set to 'development' by default in `.env`
2. The database connection was being established during application import
3. Test files set the environment to 'testing' *after* imports occurred
4. Result: Tests were running against the development database instead of the test database

## Best Practice Solution: Centralized Test Environment Configuration

The recommended approach is to use a central `test_environment.py` module that handles all environment setup and provides testing utilities. This module should be placed in the main `tests/` directory (not a subdirectory) for easy access by all test files.

### Implementation Steps:

1. **Create or Update `tests/test_environment.py`**:

```python
# tests/test_environment.py
import os
import sys
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
    
    return True

# Call setup automatically when this module is imported
# This ensures the environment is configured regardless of how the module is used
environment_configured = setup_test_environment()
logger.info(f"Test environment configured: {environment_configured}")

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

# Additional testing utilities...
```

2. **Update `conftest.py` to Import Test Environment**:

```python
# tests/conftest.py
# Import test_environment first to configure the environment
# before any other imports
from tests.test_environment import setup_test_environment

# Now it's safe to import other modules
import logging
import uuid
from datetime import datetime, timezone
import pytest
from werkzeug.security import generate_password_hash

# Rest of your imports and fixtures...
```

3. **For Standalone Test Modules**:

```python
# At the top of any standalone test file
from tests.test_environment import setup_test_environment

# Now safe to import app modules
import pytest
from app import create_app
# Other imports...
```

## Benefits of This Approach

1. **Centralized Configuration**: All environment setup logic is in one place
2. **Works with pytest and direct Python execution**: Ensures consistent environment regardless of how tests are run
3. **Automatic Setup**: Environment is configured upon import of the module
4. **Integration/Unit Test Mode Support**: Provides utilities for conditional test behavior
5. **DRY (Don't Repeat Yourself)**: Eliminates the need to duplicate environment setup code

## Database Verification

Add a verification function to `test_environment.py` to check for correct database connections:

```python
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
```

## Handling Detached Entity Errors

When working with SQLAlchemy in tests:

1. Use `get_detached_copy()` or `get_entity_dict()` when you need entity data outside a session
2. Use Flask-Login's `AnonymousUserMixin` for unauthenticated user testing
3. Create fresh test clients with cleared sessions for authentication tests:
   ```python
   with app.test_client() as test_client:
       with test_client.session_transaction() as sess:
           sess.clear()
       # Run tests with this client...
   ```

## Commands for Environment Switching

The centralized `test_environment.py` approach should handle environment switching automatically. For manual testing or debugging, you can use:

```bash
# Windows
set FLASK_ENV=testing
set INTEGRATION_TEST=1
python -m tests.test_module

# Unix/Linux/Mac
export FLASK_ENV=testing
export INTEGRATION_TEST=1
python -m tests.test_module
```

## Checklist for New Test Programs

When creating new test files, ensure you:

1. Import `test_environment.py` at the top before any application imports:
   ```python
   # tests/new_test.py
   from tests.test_environment import setup_test_environment
   
   # Now safe to import app modules
   import pytest
   from app import create_app
   # rest of imports...
   ```

2. Add verification at the start of critical tests:
   ```python
   from tests.test_environment import verify_database_connection
   
   def test_something():
       # Verify database connection
       assert verify_database_connection(), "Wrong database connection"
       # Rest of test...
   ```

## Troubleshooting Common Issues

1. **Wrong Database Connection**: Ensure `test_environment.py` is imported before any application modules
2. **ModuleNotFoundError**: Check that `tests` directory is in the Python path
3. **Detached Entity Errors**: Entity being accessed outside its session - use detached copies
4. **Environment Not Recognized**: Verify that `.env` file isn't overriding environment variables set by `test_environment.py`

Following these guidelines ensures your tests consistently connect to the correct database, regardless of how they're executed.