# tests/test_redis_connection.py

import pytest
import redis
from datetime import datetime, timezone
import json
from app.config.settings import settings
from app.security.authentication.session_manager import SessionManager
from app.security.config import SecurityConfig

def test_basic_redis_connection():
    """Test basic Redis connectivity"""
    # Connect to Redis
    redis_client = redis.from_url('redis://localhost:6379/0')
    
    # Test connection with ping
    assert redis_client.ping() == True, "Redis ping failed"
    
    # Test basic operations
    redis_client.set('test_key', 'test_value')
    value = redis_client.get('test_key')
    assert value.decode('utf-8') == 'test_value', "Redis get/set failed"
    
    # Clean up
    redis_client.delete('test_key')

def test_session_management():
    """Test session management with Redis"""
    # Initialize components
    redis_client = redis.from_url('redis://localhost:6379/0')
    security_config = SecurityConfig()
    session_manager = SessionManager(security_config, redis_client)
    
    # Test session creation
    test_data = {
        'user_id': 'test_user',
        'hospital_id': 'test_hospital',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Create session
    session_id = session_manager.create_session(
        user_id=test_data['user_id'],
        hospital_id=test_data['hospital_id'],
        additional_data={'test': True}
    )
    
    assert session_id is not None, "Session creation failed"
    
    # Validate session
    session_data = session_manager.validate_session(session_id)
    assert session_data is not None, "Session validation failed"
    assert session_data['user_id'] == test_data['user_id'], "User ID mismatch"
    
    # Test session termination
    success = session_manager.end_session(session_id)
    assert success is True, "Session termination failed"
    
    # Verify session is terminated
    invalid_session = session_manager.validate_session(session_id)
    assert invalid_session is None, "Session should be invalid after termination"

@pytest.mark.integration
def test_multiple_sessions():
    """Test handling multiple sessions"""
    redis_client = redis.from_url('redis://localhost:6379/0')
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
    
    # Validate all sessions
    for i, session_id in enumerate(sessions):
        session_data = session_manager.validate_session(session_id)
        assert session_data is not None, f"Session {i} validation failed"
        assert session_data['user_id'] == f'test_user_{i}', f"User ID mismatch in session {i}"
    
    # End all sessions
    for session_id in sessions:
        success = session_manager.end_session(session_id)
        assert success is True, f"Failed to end session {session_id}"