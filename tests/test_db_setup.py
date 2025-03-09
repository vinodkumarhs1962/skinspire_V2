# tests/test_db_setup.py
# pytest tests/test_db_setup.py

import pytest
import uuid
from sqlalchemy import inspect, text
from app.models import Hospital, User, Staff, Patient
from app.config.settings import settings

@pytest.fixture(scope='function')  # Changed to function scope
def db_session(db_manager):
    """Get database session for testing with proper error handling"""
    session = db_manager.Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@pytest.fixture(scope='function')  # Changed to function scope
def test_hospital(db_session):
    """Get test hospital"""
    hospital = db_session.query(Hospital).filter_by(
        license_no="HC123456"
    ).first()
    
    if not hospital:
        # If you need to create a test hospital, do it here
        hospital = Hospital(
            name="SkinSpire Main Clinic",  # Match actual name in database
            license_no="HC123456",
            address={
                "street": "123 Test Ave",
                "city": "Test City",
                "zip": "12345"
            },
            contact_details={
                "phone": "1234567890",
                "email": "test@skinspire.com"
            },
            settings={
                "timezone": "UTC",
                "currency": "USD"
            },
            encryption_enabled=True
        )
        db_session.add(hospital)
        db_session.commit()
        db_session.refresh(hospital)
    
    return hospital

# Add the session fixture that references db_session
@pytest.fixture
def session(db_session):
    """Alias for db_session for backward compatibility"""
    return db_session

def test_database_connection(session):
    """Test database connection is working"""
    # Use text() to properly format SQL query
    result = session.execute(text("SELECT 1")).scalar()
    assert result == 1

def test_test_hospital_exists(test_hospital):
    """Test that our test hospital exists"""
    assert test_hospital is not None
    assert test_hospital.license_no == "HC123456"
    assert test_hospital.name == "SkinSpire Main Clinic"  # Match actual name

def test_user_table_structure(session, test_hospital):
    """Test the user table structure is correct"""
    # Get metadata about the User table using reflection
    inspector = inspect(session.bind)
    columns = {col['name'] for col in inspector.get_columns('users')}
    
    # Verify essential columns exist
    essential_columns = {'user_id', 'hospital_id', 'entity_type', 'entity_id', 
                         'password_hash', 'is_active', 'last_login'}
    
    assert essential_columns.issubset(columns), \
           f"Missing columns in users table. Expected at least: {essential_columns}"

def test_create_and_query_user(session, test_hospital):
    """Test user creation and retrieval"""
    from werkzeug.security import generate_password_hash
    import uuid
    
    # Create a test user with shorter ID (max 15 chars)
    test_user_id = f"test_{uuid.uuid4().hex[:8]}"
    
    try:
        # Check if user already exists
        existing_user = session.query(User).filter_by(user_id=test_user_id).first()
        if existing_user:
            session.delete(existing_user)
            session.commit()
        
        # Create new user for testing
        new_user = User(
            user_id=test_user_id,
            hospital_id=test_hospital.hospital_id,
            entity_type='staff',
            entity_id=str(uuid.uuid4()),
            password_hash=generate_password_hash('test_password'),
            is_active=True
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)  # Refresh to ensure we get the latest data
        
        # Verify user was saved and can be retrieved
        queried_user = session.query(User).filter_by(user_id=test_user_id).first()
        assert queried_user is not None
        assert queried_user.user_id == test_user_id
        assert queried_user.is_active is True
        
        # Clean up - use a direct SQL query instead of ORM to avoid relationship checks
        session.execute(text(f"DELETE FROM users WHERE user_id = :user_id"), 
                       {"user_id": test_user_id})
        session.commit()
        
    except Exception as e:
        # Ensure we don't leave the test in a bad state
        session.rollback()
        # Clean up - try direct SQL if there was an ORM error
        try:
            session.execute(text(f"DELETE FROM users WHERE user_id = :user_id"), 
                           {"user_id": test_user_id})
            session.commit()
        except:
            session.rollback()
        raise

def test_timestamp_columns_exist(session):
    """Test that timestamp columns exist in key tables"""
    inspector = inspect(session.bind)
    
    # Check a few important tables
    for table_name in ['users', 'hospitals', 'patients']:
        columns = {col['name'] for col in inspector.get_columns(table_name)}
        timestamp_columns = {'created_at', 'updated_at', 'created_by', 'updated_by'}
        
        assert timestamp_columns.issubset(columns), \
               f"Missing timestamp columns in {table_name} table. Expected: {timestamp_columns}"