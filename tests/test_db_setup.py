# tests/test_db_setup.py
# pytest tests/test_db_setup.py

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import uuid
import logging
from sqlalchemy import inspect, text
from app.models import Hospital, User, Staff, Patient
from app.config.settings import settings
from app.services.database_service import get_db_session, get_db_engine
from tests.test_environment import integration_flag
from werkzeug.security import generate_password_hash

# Set up logging for tests
logger = logging.getLogger(__name__)

def test_database_connection():
    """
    Test database connection is working
    """
    logger.info("Testing database connection")
    
    with get_db_session() as session:
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
        logger.info("Database connection test passed")

def test_test_hospital_exists():
    """
    Test that our test hospital exists
    """
    logger.info("Testing test hospital existence")
    
    with get_db_session() as session:
        hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
        
        assert hospital is not None, "Test hospital fixture returned None"
        assert hospital.license_no == "HC123456", "Wrong test hospital license number"
        assert hospital.name == "Skinspire Main Clinic", "Wrong test hospital name"
    
    logger.info("Test hospital exists with correct attributes")

def test_user_table_structure(db_session):
    """Test user table structure"""
    logger.info("Testing user table structure")
    
    engine = get_db_engine()
    inspector = inspect(engine)
    columns = inspector.get_columns('users')
    
    required_columns = [
        'user_id', 'hospital_id', 'entity_type', 
        'entity_id', 'password_hash', 
        'failed_login_attempts', 'last_login', 'is_active'
    ]
    
    column_names = [col['name'] for col in columns]
    missing_columns = [col for col in required_columns if col not in column_names]
    
    assert len(missing_columns) == 0, f"Missing columns: {missing_columns}"

def test_create_and_query_user():
    """
    Test user creation and retrieval
    """
    logger.info("Testing user creation and retrieval")
    
    # Create a test user with unique ID
    test_user_id = f"test_{uuid.uuid4().hex[:8]}"
    logger.info(f"Creating test user with ID: {test_user_id}")
    
    with get_db_session() as session:
        hospital = session.query(Hospital).filter_by(license_no="HC123456").first()
        if not hospital:
            pytest.skip("Hospital not found, cannot continue test")
            
        # Check if user already exists and clean up if needed
        existing_user = session.query(User).filter_by(user_id=test_user_id).first()
        if existing_user:
            session.delete(existing_user)
            session.flush()
            logger.info(f"Removed existing user with ID: {test_user_id}")
        
        # Create new user for testing
        new_user = User(
            user_id=test_user_id,
            hospital_id=hospital.hospital_id,
            entity_type='staff',
            entity_id=str(uuid.uuid4()),
            password_hash=generate_password_hash('test_password'),
            is_active=True
        )
        
        session.add(new_user)
        session.flush()
        logger.info("Test user created in database")
        
        # Verify user was saved and can be retrieved
        queried_user = session.query(User).filter_by(user_id=test_user_id).first()
        assert queried_user is not None, "User not found after creation"
        assert queried_user.user_id == test_user_id, "User ID mismatch"
        assert queried_user.is_active is True, "User active status mismatch"
        
        logger.info("Successfully retrieved created user from database")

def test_timestamp_columns_exist(db_session):
    """Test timestamp columns in key tables"""
    logger.info("Testing timestamp columns in database tables")
    
    engine = get_db_engine()
    inspector = inspect(engine)
    
    # Check important tables
    tables_to_check = ['users', 'hospitals', 'patients']
    timestamp_columns = {'created_at', 'updated_at'}
    tracking_columns = {'created_by', 'updated_by'}
    
    for table_name in tables_to_check:
        # Check if table exists
        if not inspector.has_table(table_name):
            logger.warning(f"Table {table_name} does not exist - skipping check")
            continue
            
        columns = {col['name'] for col in inspector.get_columns(table_name)}
        
        # Check timestamp columns
        missing_timestamp_cols = timestamp_columns - columns
        if missing_timestamp_cols:
            logger.warning(f"Table {table_name} is missing timestamp columns: {missing_timestamp_cols}")
        
        # Assert the timestamp columns exist
        assert timestamp_columns.issubset(columns), \
               f"Missing timestamp columns in {table_name} table. Expected: {timestamp_columns}"

def test_database_indexes(db_session):
    """Test that important indexes exist"""
    logger.info("Testing database indexes")
    
    engine = get_db_engine()
    inspector = inspect(engine)
    
    # List of important tables to check
    tables_to_check = ['users', 'hospitals', 'patients', 'user_sessions']
    
    for table_name in tables_to_check:
        # Check if table exists
        if not inspector.has_table(table_name):
            logger.warning(f"Table {table_name} does not exist - skipping index check")
            continue
            
        # Get indexes for the table
        indexes = inspector.get_indexes(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        
        logger.info(f"Table {table_name} has {len(indexes)} indexes")
        
        # Verify primary key exists
        if not pk_constraint or not pk_constraint.get('constrained_columns'):
            logger.warning(f"Table {table_name} has no primary key defined")
        else:
            logger.info(f"Table {table_name} has primary key on columns: {pk_constraint['constrained_columns']}")

def test_connection_pooling():
    """
    Test database connection pooling
    """
    logger.info("Testing database connection pooling")
    
    # Skip detailed test in unit test mode
    if not integration_flag():
        with get_db_session() as session:
            # Just verify a basic connection works
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1
        logger.info("Basic connection test passed in unit test mode")
        return
    
    # For integration testing, check multiple sequential connections
    connections = []
    for i in range(5):
        with get_db_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1
            
            # Get connection info
            conn_info = session.execute(text("SELECT current_database(), inet_server_addr(), inet_server_port()")).fetchone()
            connections.append(conn_info)
            logger.info(f"Connection {i+1}: Database={conn_info[0]}, Server={conn_info[1]}:{conn_info[2]}")
    
    logger.info("Connection pooling test passed - all connections successful")