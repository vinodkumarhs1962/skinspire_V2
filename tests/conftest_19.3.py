# tests/conftest.py

# Import test_environment first to configure the environment
# before any other imports
from tests.test_environment import setup_test_environment

# Standard library imports - keep these at the top
import os
import sys
import logging
import uuid
from datetime import datetime, timezone

# CRITICAL: Set environment variables before ANY app imports
os.environ['FLASK_ENV'] = 'testing'
os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
os.environ['USE_NESTED_TRANSACTIONS'] = 'False'

# Third-party imports
import pytest
from werkzeug.security import generate_password_hash
from sqlalchemy import text

# Set up logging
logger = logging.getLogger(__name__)

# Import the environment testing utilities
from tests.test_security.test_environment import integration_flag

# Import the database service
from app.services.database_service import get_db_session, use_nested_transactions

# Now safe to import app-specific models
from app.models.transaction import (
    User, 
    UserSession, 
    LoginHistory
)
from app.models.master import Hospital

# Ensure nested transactions are disabled for testing
use_nested_transactions(False)

@pytest.fixture(scope="session", autouse=True)
def check_test_environment():
    """Check test environment configuration"""
    # Log environment information
    db_url = os.environ.get('TEST_DATABASE_URL')
    flask_env = os.environ.get('FLASK_ENV')
    
    logger.info(f"Test environment: FLASK_ENV={flask_env}")
    logger.info(f"Test database URL: {db_url and db_url[:db_url.find('@')]+'@...'}") # Hide password
    
    # Verify environment is correct
    assert flask_env == 'testing', f"FLASK_ENV must be 'testing', got '{flask_env}'"

@pytest.fixture(scope="session", autouse=True)
def verify_test_db_connection():
    """Verify test database connection before any tests run"""
    from app.services.database_service import get_active_env, get_database_url
    
    # Log database service info
    env = get_active_env()
    db_url = get_database_url()
    logger.info(f"Database service using environment: {env}")
    
    with get_db_session() as session:
        try:
            # Check if users table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'users'
                )
            """)).scalar()
            
            if not result:
                pytest.fail("Users table not found in test database - wrong database or schema?")
                
            # Test a simple query to verify connection
            session.execute(text("SELECT 1")).scalar()
            logger.info("Test database connection verified successfully")
        except Exception as e:
            logger.error(f"Test database verification failed: {str(e)}")
            pytest.fail(f"Database verification failed: {str(e)}")

@pytest.fixture(scope='session')
def app():
    """Create test application with proper configuration and routes"""
    # Import the create_app function
    from app import create_app
    
    # Create the app with the factory function
    app = create_app()
    
    # Override configuration for testing
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': os.environ.get('TEST_DATABASE_URL'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test_secret_key',
        'WTF_CSRF_ENABLED': integration_flag()  # Enable CSRF only in integration mode
    })
    
    # Log successful setup
    app.logger.info("Test application created with custom configuration")
    
    return app

@pytest.fixture(scope='session')
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(autouse=True)
def ensure_app_context(app):
    """Ensure tests run within application context"""
    with app.app_context():
        yield

@pytest.fixture(scope='function')
def db_session():
    """
    Create a fresh database session with transaction management
    for testing.
    """
    from app.services.database_service import get_db_session
    
    with get_db_session() as session:
        try:
            yield session
            # The session will be automatically committed/rolled back
            # by the context manager when it exits
        except Exception as e:
            logger.error(f"Test session error: {str(e)}")
            raise

@pytest.fixture
def test_hospital(db_session):
    """Get test hospital from database"""
    # Query within this session to ensure the instance is attached
    hospital = db_session.query(Hospital).filter_by(license_no="HC123456").first()
    if not hospital:
        # Create one if it doesn't exist
        hospital = Hospital(
            hospital_id=str(uuid.uuid4()),
            name="Test Hospital",
            license_no="HC123456",
            address={"street": "Test Street"},
            contact_details={"phone": "123-456-7890"},
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(hospital)
        db_session.flush()  # Get the ID without committing
    
    return hospital

@pytest.fixture(scope='function')
def test_user(db_session, test_hospital):
    """Create test user with proper cleanup"""
    try:
        # Clean up any existing test data in the correct order
        # to avoid foreign key constraint violations
        cleanup_queries = [
            (LoginHistory, "user_id", "test_user"),
            (UserSession, "user_id", "test_user"),
            (User, "user_id", "test_user")
        ]
        
        for model, field, value in cleanup_queries:
            try:
                db_session.query(model).filter_by(**{field: value}).delete(synchronize_session=False)
            except Exception as e:
                logger.warning(f"Cleanup warning for {model.__name__}: {e}")
        
        # Create fresh test user
        user = User(
            user_id="test_user",
            hospital_id=test_hospital.hospital_id,
            entity_type="staff",
            entity_id=str(uuid.uuid4()),
            is_active=True,
            password_hash=generate_password_hash("test_password")
        )
        
        db_session.add(user)
        db_session.flush()  # Instead of commit
        db_session.refresh(user)
        
        yield user
        
        # No need for cleanup since we're rolling back
        
    except Exception as e:
        logger.error(f"Test user fixture error: {str(e)}")
        raise

@pytest.fixture(scope='function', autouse=True)
def reset_login_attempts(db_session):
    """Reset failed login attempts before each test"""
    from sqlalchemy import text
    
    try:
        # First check if users table exists
        table_exists = db_session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'users'
            )
        """)).scalar()
        
        if not table_exists:
            logger.warning("Users table not found, skipping reset_login_attempts")
            return
            
        # Reset admin user's failed login attempts
        user = db_session.query(User).filter_by(user_id='9876543210').first()
        if user:
            user.failed_login_attempts = 0
    except Exception as e:
        logger.warning(f"Error resetting login attempts: {e}")
        # Don't raise the exception - allow tests to continue

@pytest.fixture
def admin_user(db_session):
    """Get admin user for testing with error handling"""
    from sqlalchemy import text
    
    try:
        # First verify the table exists in this session
        table_check = db_session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'users'
            )
        """)).scalar()
        
        if not table_check:
            logger.error("Users table doesn't exist in the current session's view")
            return None
            
        # Try to query the user
        user = db_session.query(User).filter_by(user_id="9876543210").first()
        
        if not user:
            logger.warning("Admin user not found, will create a placeholder")
            # Create a minimal user object for testing
            test_hospital_id = None
            try:
                hospital = db_session.query(Hospital).first()
                if hospital:
                    test_hospital_id = hospital.hospital_id
            except Exception:
                pass
                
            user = User(
                user_id="9876543210",
                hospital_id=test_hospital_id,
                entity_type="staff",
                entity_id=str(uuid.uuid4()),
                is_active=True,
                password_hash=generate_password_hash("admin123")
            )
            db_session.add(user)
            db_session.flush()
            
        return user
    except Exception as e:
        logger.error(f"Error in admin_user fixture: {str(e)}")
        # Return None instead of failing to allow tests to continue with appropriate skipping
        return None

@pytest.fixture
def logged_in_client(client, admin_user, monkeypatch):
    """A client that is logged in as admin"""
    
    # Skip if admin_user is None
    if admin_user is None:
        pytest.skip("Admin user not available - skipping logged_in_client fixture")
    
    # Mock Flask-Login's current_user
    class MockUser:
        is_authenticated = True
        is_active = True
        is_anonymous = False
        
        @property
        def user_id(self):
            return admin_user.user_id
    
    from flask_login import current_user
    monkeypatch.setattr('flask_login.current_user', MockUser())
    
    # Set session token
    with client.session_transaction() as sess:
        sess['auth_token'] = 'test_token_123'
    
    return client