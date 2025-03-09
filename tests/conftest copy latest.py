# tests/conftest.py

# Standard library imports
import logging
import uuid
from datetime import datetime, timezone

# Third-party imports
import pytest
from flask import Flask
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

# Application imports - Core functionality
from app.database import init_db
from app.config.settings import settings

# Application imports - Models
from app.models import (
    Hospital,
    User, 
    UserSession,
    LoginHistory
)

# Application imports - Security
from app.security.routes import auth_bp  # Import from __init__.py is preferred

# Set up logging
logger = logging.getLogger(__name__)

@pytest.fixture
def session(db_session):
    """Alias for db_session for backward compatibility"""
    return db_session

@pytest.fixture(scope='session')
def app():
    """Create test application with proper configuration and routes"""
    app = Flask(__name__)
    
    # Configure application
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': settings.get_database_url_for_env('testing'),
        'SECRET_KEY': 'test_secret_key'
    })
    
    # Register required blueprints for testing
    from app.security.routes import auth_bp
    app.register_blueprint(auth_bp)
    
    # Log successful setup
    app.logger.info("Test application created with auth blueprint registered")
    
    return app

@pytest.fixture(scope='session')
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture(scope='session')
def db_manager(app):
    """Get database manager instance"""
    with app.app_context():
        db_manager = init_db(settings.get_database_url_for_env('testing'))
        return db_manager

@pytest.fixture(scope='function')
def db_session(db_manager):
    """Create a fresh database session for each test"""
    session = db_manager.Session()
    try:
        # Initialize schema for test database
        from app.database.context import initialize_schema
        initialize_schema(session)
        
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def test_hospital(session):
    """Get test hospital from database"""
    # Query within this session to ensure the instance is attached
    hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
    if not hospital:
        raise ValueError("Test hospital not found - please run setup_test_db.py first")
    
    # Simply return the instance - it's already attached to the session
    return hospital

# @pytest.fixture(scope='function')
# def test_hospital(db_session):
#     """Get test hospital with proper session handling"""
#     hospital = db_session.query(Hospital).filter_by(
#         license_no="HC123456"
#     ).first()
#     if not hospital:
#         raise ValueError("Test hospital not found - please run setup_test_db.py first")
#     return hospital

@pytest.fixture(scope='function')
def test_user(db_session, test_hospital):
    """Create test user with proper cleanup"""
    try:
        # First, we clean up any existing test data in the correct order
        # to avoid foreign key constraint violations
        cleanup_queries = [
            (LoginHistory, "user_id", "test_user"),
            (UserSession, "user_id", "test_user"),
            (User, "user_id", "test_user")
        ]
        
        for model, field, value in cleanup_queries:
            try:
                db_session.query(model).filter_by(**{field: value}).delete()
            except Exception as e:
                logger.warning(f"Cleanup warning for {model.__name__}: {e}")
        
        db_session.commit()
        
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
        db_session.commit()
        db_session.refresh(user)
        
        yield user
        
        # Cleanup after test, again in the correct order
        for model, field, value in cleanup_queries:
            try:
                db_session.query(model).filter_by(**{field: value}).delete()
            except Exception as e:
                logger.warning(f"Post-test cleanup warning for {model.__name__}: {e}")
        
        db_session.commit()
        
    except Exception as e:
        logger.error(f"Test user fixture error: {str(e)}")
        db_session.rollback()
        raise

# Add to tests/conftest.py

@pytest.fixture(scope='function', autouse=True)
def reset_login_attempts(session):
    """Reset failed login attempts before each test"""
    try:
        # Reset the admin user's failed login attempts
        user = session.query(User).filter_by(user_id='9876543210').first()
        if user:
            user.failed_login_attempts = 0
            session.commit()
    except Exception as e:
        print(f"Error resetting login attempts: {e}")
        session.rollback()