# tests/test_redis_connection.py

# =================================================================
# MIGRATION STATUS:
# This file has been fully migrated to use the database service layer.
# It uses get_db_session for all database access following project standards.
#
# Completed:
# - All database operations use get_db_session with context manager
# - Removed direct session access and warnings
# - Enhanced error handling and logging
# - Added integration flag for tests requiring Redis
# =================================================================

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import redis
import logging
from datetime import datetime, timezone
import json
import time
from app.config.settings import settings
from app.security.authentication.session_manager import SessionManager
from app.security.config import SecurityConfig
# Import the database service
from app.services.database_service import get_db_session
from app.models import User
import uuid
from werkzeug.security import generate_password_hash
from tests.test_environment import integration_flag

# Set up logging for tests
logger = logging.getLogger(__name__)

# Helper function to get Redis client
def get_redis_client():
    """
    Get Redis client using settings
    
    Returns:
        redis.Redis: Redis client instance
    """
    redis_url = settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else 'redis://localhost:6379/0'
    logger.info(f"Connecting to Redis at: {redis_url}")
    return redis.from_url(redis_url)

def test_basic_redis_connection():
    """
    Test basic Redis connectivity
    
    Verifies:
    - Connection to Redis server
    - Basic operations (get/set)
    """
    # Skip in unit test mode - requires actual Redis server
    if not integration_flag():
        pytest.skip("Redis connection test skipped in unit test mode")
        
    logger.info("Testing basic Redis connectivity")
    
    try:
        # Connect to Redis
        redis_client = get_redis_client()
        
        # Test connection with ping
        assert redis_client.ping() == True, "Redis ping failed"
        logger.info("Redis ping successful")
        
        # Test basic operations
        test_key = f"test_key_{uuid.uuid4().hex[:8]}"
        test_value = f"test_value_{uuid.uuid4().hex[:8]}"
        
        redis_client.set(test_key, test_value)
        value = redis_client.get(test_key)
        assert value.decode('utf-8') == test_value, "Redis get/set failed"
        logger.info("Redis get/set operations successful")
        
        # Clean up
        redis_client.delete(test_key)
        logger.info("Redis test key deleted")
    except redis.exceptions.ConnectionError as e:
        pytest.skip(f"Redis server not available: {str(e)}")
    except Exception as e:
        logger.error(f"Redis test error: {str(e)}")
        raise
    
    logger.info("Basic Redis connectivity test passed")

def test_session_management():
    """
    Test session management with Redis
    
    Verifies:
    - Session creation
    - Session validation
    - Session termination
    """
    # Skip in unit test mode - requires actual Redis server
    if not integration_flag():
        pytest.skip("Redis session management test skipped in unit test mode")
        
    logger.info("Testing session management with Redis")
    
    try:
        # Initialize components
        redis_client = get_redis_client()
        security_config = SecurityConfig()
        session_manager = SessionManager(security_config, redis_client)
        
        # Test session creation
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        test_hospital_id = str(uuid.uuid4())
        logger.info(f"Creating test session for user: {test_user_id}")
        
        # Create session
        session_id = session_manager.create_session(
            user_id=test_user_id,
            hospital_id=test_hospital_id,
            additional_data={'test': True}
        )
        
        assert session_id is not None, "Session creation failed"
        logger.info(f"Session created with ID: {session_id}")
        
        # Validate session
        session_data = session_manager.validate_session(session_id)
        assert session_data is not None, "Session validation failed"
        assert session_data['user_id'] == test_user_id, "User ID mismatch"
        logger.info("Session validation successful")
        
        # Test session termination
        success = session_manager.end_session(session_id)
        assert success is True, "Session termination failed"
        logger.info("Session termination successful")
        
        # Verify session is terminated
        invalid_session = session_manager.validate_session(session_id)
        assert invalid_session is None, "Session should be invalid after termination"
        logger.info("Session verification after termination successful")
    except redis.exceptions.ConnectionError as e:
        pytest.skip(f"Redis server not available: {str(e)}")
    except Exception as e:
        logger.error(f"Redis session test error: {str(e)}")
        raise
    
    logger.info("Session management test passed")

def test_session_and_database_integration():
    """
    Test integration between Redis sessions and database using database service
    
    Verifies:
    - User record in database
    - Session creation in Redis
    - Ability to retrieve user from database using session info
    """
    # Skip in unit test mode - requires actual Redis server
    if not integration_flag():
        pytest.skip("Redis/database integration test skipped in unit test mode")
        
    logger.info("Testing integration between Redis sessions and database")
    
    try:
        # Generate a unique user ID for testing
        test_user_id = f"redis_test_{uuid.uuid4().hex[:8]}"
        logger.info(f"Creating test user with ID: {test_user_id}")
        
        # First, create a test user in the database
        with get_db_session() as session:
            # Create a test user in the database
            test_user = User(
                user_id=test_user_id,
                entity_type="staff",
                entity_id=str(uuid.uuid4()),
                is_active=True,
                password_hash=generate_password_hash("test_password")
            )
            
            # Add to database session
            session.add(test_user)
            session.flush()
            logger.info("Test user created in database")
            
            # Get the hospital_id from the user if available, or create a mock one
            hospital_id = getattr(test_user, 'hospital_id', str(uuid.uuid4()))
        
        # Now create a Redis session for this user
        redis_client = get_redis_client()
        security_config = SecurityConfig()
        session_manager = SessionManager(security_config, redis_client)
        
        # Create session
        session_id = session_manager.create_session(
            user_id=test_user_id,
            hospital_id=hospital_id,
            additional_data={'test_type': 'integration'}
        )
        logger.info(f"Redis session created with ID: {session_id}")
        
        # Verify session created successfully
        assert session_id is not None, "Failed to create Redis session"
        
        # Verify session data contains correct user ID
        session_data = session_manager.validate_session(session_id)
        assert session_data is not None, "Failed to validate session"
        assert session_data['user_id'] == test_user_id, "User ID mismatch in session data"
        logger.info("Session validation successful")
        
        # Verify we can query the user from database using the user ID in the session
        with get_db_session() as session:
            user_from_db = session.query(User).filter_by(user_id=session_data['user_id']).first()
            assert user_from_db is not None, "Failed to find user in database"
            assert user_from_db.user_id == test_user_id, "User ID mismatch between database and session"
            logger.info("Successfully retrieved user from database using session data")
        
        # Clean up Redis session
        session_manager.end_session(session_id)
        logger.info("Redis session terminated")
        
        # No need to clean up database records since db_service_session will roll back
    except redis.exceptions.ConnectionError as e:
        pytest.skip(f"Redis server not available: {str(e)}")
    except Exception as e:
        logger.error(f"Redis/database integration test error: {str(e)}")
        raise
    
    logger.info("Session and database integration test passed")

def test_multiple_sessions():
    """
    Test handling multiple sessions
    
    Verifies:
    - Multiple sessions can be created for the same user
    - All sessions can be validated
    - All sessions can be terminated
    """
    # Skip in unit test mode - requires actual Redis server
    if not integration_flag():
        pytest.skip("Multiple sessions test skipped in unit test mode")
    
    logger.info("Testing multiple Redis sessions")
    
    try:
        redis_client = get_redis_client()
        security_config = SecurityConfig()
        session_manager = SessionManager(security_config, redis_client)
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session_id = session_manager.create_session(
                user_id=f'test_user_{i}',
                hospital_id='test_hospital',
                additional_data={'session_number': i}
            )
            sessions.append(session_id)
            logger.info(f"Created session {i+1} with ID: {session_id}")
        
        # Validate all sessions
        for i, session_id in enumerate(sessions):
            session_data = session_manager.validate_session(session_id)
            assert session_data is not None, f"Session {i} validation failed"
            assert session_data['user_id'] == f'test_user_{i}', f"User ID mismatch in session {i}"
            logger.info(f"Session {i+1} validated successfully")
        
        # End all sessions
        for i, session_id in enumerate(sessions):
            success = session_manager.end_session(session_id)
            assert success is True, f"Failed to end session {session_id}"
            logger.info(f"Session {i+1} terminated successfully")
    except redis.exceptions.ConnectionError as e:
        pytest.skip(f"Redis server not available: {str(e)}")
    except Exception as e:
        logger.error(f"Multiple sessions test error: {str(e)}")
        raise
    
    logger.info("Multiple sessions test passed")

def test_session_expiry():
    """
    Test session expiration
    
    Verifies:
    - Sessions expire after their expiration time
    - Expired sessions cannot be validated
    """
    # Skip in unit test mode - requires actual Redis server
    if not integration_flag():
        pytest.skip("Session expiry test skipped in unit test mode")
    
    logger.info("Testing session expiration")
    
    try:
        redis_client = get_redis_client()
        security_config = SecurityConfig()
        # Override expiry for testing to be very short
        security_config.BASE_SECURITY_SETTINGS['session_expiry_seconds'] = 1
        
        session_manager = SessionManager(security_config, redis_client)
        
        # Create session
        session_id = session_manager.create_session(
            user_id='expiry_test_user',
            hospital_id='test_hospital'
        )
        logger.info(f"Created session with 1-second expiry, ID: {session_id}")
        
        # Verify session is valid immediately
        initial_validation = session_manager.validate_session(session_id)
        assert initial_validation is not None, "Session should be valid immediately"
        logger.info("Session validated successfully after creation")
        
        # Wait for expiry
        logger.info("Waiting for session to expire (2 seconds)...")
        time.sleep(2)  # Wait 2 seconds (longer than our 1 second expiry)
        
        # Verify session has expired
        expired_validation = session_manager.validate_session(session_id)
        assert expired_validation is None, "Session should have expired"
        logger.info("Session expiry confirmed")
    except redis.exceptions.ConnectionError as e:
        pytest.skip(f"Redis server not available: {str(e)}")
    except Exception as e:
        logger.error(f"Session expiry test error: {str(e)}")
        raise
    
    logger.info("Session expiry test passed")