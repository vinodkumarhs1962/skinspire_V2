# tests/test_security/test_triggers.py
# pytest tests/test_security/test_triggers.py -v

# =================================================================
# MIGRATION STATUS:
# This file has been fully migrated to use the database service layer.
# It uses get_db_session for all database access following project standards.
#
# Completed:
# - All test methods use get_db_session with context manager
# - Database operations follow the established transaction pattern
# - Removed all legacy direct session code
# - Enhanced error handling and logging
# - Maintained CLI command for deployment checks
# =================================================================

# Import test environment configuration first 
from tests.test_environment import setup_test_environment

import pytest
import logging
from sqlalchemy import text
from werkzeug.security import check_password_hash
# Import the database service
from app.services.database_service import get_db_session
from app.models import User
from tests.test_environment import integration_flag

# Set up logging for tests
logger = logging.getLogger(__name__)

class TestDatabaseTriggers:
    """
    Test database triggers
    
    This class verifies database triggers work correctly with the database
    service pattern, focusing on password hashing and timestamp updates.
    """
    
    def test_password_hashing_trigger(self, test_hospital):
        """
        Test password hashing database trigger
        
        Verifies:
        - Password is automatically hashed when stored in database
        - Hashed password matches expected format
        - Hashed password can be verified
        
        Args:
            test_hospital: Test hospital fixture
        """
        logger.info("Testing password hashing trigger with database service")
        
        # Skip in unit test mode - this requires actual database triggers
        if not integration_flag():
            pytest.skip("Password hashing trigger test skipped in unit test mode")
        
        # Create a test user with a plain password
        test_user_id = f"test_trigger_{pytest.get_random_string(4)}"
        plain_password = "Password123!"
        
        with get_db_session() as session:
            # Create user entry
            session.execute(
                text("""
                    INSERT INTO users (user_id, hospital_id, entity_type, entity_id, password_hash, is_active)
                    VALUES (:user_id, :hospital_id, 'staff', uuid_generate_v4(), :password, true)
                """),
                {
                    "user_id": test_user_id,
                    "hospital_id": str(test_hospital.hospital_id),
                    "password": plain_password  # Plain password should be hashed by trigger
                }
            )
            session.flush()
            
            # Retrieve user to verify password was hashed
            user = session.query(User).filter_by(user_id=test_user_id).first()
            assert user is not None, "User not found"
            
            # Verify password was hashed and not stored in plain text
            assert user.password_hash != plain_password, "Password was not hashed"
            assert (user.password_hash.startswith('$pbkdf2') or 
                    user.password_hash.startswith('$2') or 
                    user.password_hash.startswith('scrypt:')), "Password hash format incorrect"
            
            # Verify password hash is valid and verifiable
            assert check_password_hash(user.password_hash, plain_password), "Password hash verification failed"
        
        logger.info("Password hashing trigger test passed")
    
    def test_timestamp_update_trigger(self, test_user):
        """
        Test automatic timestamp update trigger
        
        Verifies:
        - created_at timestamp is set on record creation
        - updated_at timestamp is updated on record modification
        
        Args:
            test_user: Test user fixture
        """
        logger.info("Testing timestamp update trigger with database service")
        
        # Skip in unit test mode - this requires actual database triggers
        if not integration_flag():
            pytest.skip("Timestamp update trigger test skipped in unit test mode")
        
        with get_db_session() as session:
            # Refresh user to ensure it's attached to our session
            user = session.query(User).filter_by(user_id=test_user.user_id).first()
            if not user:
                pytest.skip(f"User {test_user.user_id} not found in database")
            
            # First, verify that existing user has created_at timestamp
            assert user.created_at is not None, "created_at timestamp not set"
            original_updated_at = user.updated_at
            
            # Make a change to the user record and check if updated_at changes
            user.is_active = not user.is_active  # Toggle active status
            session.flush()
            
            # Re-fetch the user to get the latest timestamp
            session.refresh(user)
            
            # Verify updated_at timestamp has changed
            assert user.updated_at != original_updated_at, "updated_at timestamp not updated"
        
        logger.info("Timestamp update trigger test passed")

# Flask CLI command for deployment verification
import click
from flask.cli import with_appcontext

@click.group()
def cli():
    """Trigger verification commands for deployment checks"""
    pass

@cli.command()
@with_appcontext
def verify_all():
    """
    Quick verification of all triggers for deployment
    
    This command can be run from the Flask CLI to verify all database
    triggers are functioning correctly in a deployment environment.
    """
    logger.info("Verifying all database triggers")
    
    # Using database service for verification
    with get_db_session() as session:
        # Verify password hashing trigger
        logger.info("Verifying password hashing trigger")
        try:
            # Create a test user with a plain password
            test_user_id = f"trigger_verify_{click.get_random_string(4)}"
            plain_password = "Verify123!"
            
            # Insert user with plain password
            session.execute(
                text("""
                    INSERT INTO users (user_id, hospital_id, entity_type, entity_id, password_hash, is_active)
                    VALUES (:user_id, (SELECT hospital_id FROM hospitals LIMIT 1), 'staff', uuid_generate_v4(), :password, true)
                """),
                {
                    "user_id": test_user_id,
                    "password": plain_password
                }
            )
            session.flush()
            
            # Retrieve and verify
            user = session.query(User).filter_by(user_id=test_user_id).first()
            if not user:
                logger.error("Password trigger verification failed: User not created")
                return
                
            if user.password_hash == plain_password:
                logger.error("Password trigger verification failed: Password not hashed")
                return
                
            if not (user.password_hash.startswith('$pbkdf2') or 
                    user.password_hash.startswith('$2') or 
                    user.password_hash.startswith('scrypt:')):
                logger.error("Password trigger verification failed: Invalid hash format")
                return
                
            logger.info("Password hashing trigger verified successfully")
            
            # Clean up test user
            session.delete(user)
            
        except Exception as e:
            logger.error(f"Error verifying password trigger: {str(e)}")
        
        # Verify timestamp update trigger
        logger.info("Verifying timestamp update trigger")
        try:
            # Find an existing user
            user = session.query(User).first()
            if not user:
                logger.error("Timestamp trigger verification failed: No users found")
                return
                
            original_updated_at = user.updated_at
            
            # Update something trivial
            user.is_active = user.is_active  # This should still trigger an update
            session.flush()
            
            # Refresh
            session.refresh(user)
            
            if user.updated_at == original_updated_at:
                logger.error("Timestamp trigger verification failed: updated_at not changed")
                return
                
            logger.info("Timestamp update trigger verified successfully")
            
        except Exception as e:
            logger.error(f"Error verifying timestamp trigger: {str(e)}")
        
    logger.info("All trigger verifications completed")