# scripts/test_db_service_with_test.py
# python scripts/test_db_service_with_test.py -v
# Script to run a single test function with the database service

import os
import sys
from pathlib import Path
import uuid
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set environment for testing
os.environ['FLASK_ENV'] = 'testing'

import pytest
import logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_db_service_basic():
    """Verify basic database service functionality"""
    try:
        # Import the database service - initialization should happen automatically now
        from app.services.database_service import get_db_session, set_debug_mode
        
        # Enable debug mode for detailed logging
        set_debug_mode(True)
        
        logger.info("Testing database service functionality")
        
        # Test 1: Basic query
        with get_db_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1, "Basic query failed"
            logger.info("Basic query test: SUCCESS")
        
        # Test 2: Table existence check
        with get_db_session(read_only=True) as session:
            table_exists = session.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users')"
            )).scalar()
            
            assert table_exists, "Users table not found"
            logger.info("Table existence test: SUCCESS")
        
        # Test 3: Insert and verify in the SAME transaction
        with get_db_session() as session:
            # Generate a unique hospital ID for testing
            hospital_id = str(uuid.uuid4())
            logger.info(f"Using generated hospital_id: {hospital_id} for test")
            current_time = datetime.now(timezone.utc)
            
            # Insert test record
            insert_query = text("""
            INSERT INTO hospitals 
                (hospital_id, name, license_no, created_at, updated_at) 
            VALUES 
                (:hospital_id, 'TEMP_TEST', 'TEMP1234', :created_at, :updated_at)
            """)
            
            session.execute(insert_query, {
                "hospital_id": hospital_id,
                "created_at": current_time,
                "updated_at": current_time
            })
            # Flush to make sure the changes are visible within this session
            session.flush()
            logger.info("Transaction insert test: SUCCESS")
            
            # Verify record exists WITHIN SAME SESSION
            count = session.execute(text(
                "SELECT COUNT(*) FROM hospitals WHERE name = 'TEMP_TEST'"
            )).scalar()
            
            assert count > 0, "Record not inserted"
            logger.info("Record verification test: SUCCESS")
            
            # Delete test record for cleanup (still in same session)
            delete_query = text("DELETE FROM hospitals WHERE name = 'TEMP_TEST'")
            session.execute(delete_query)
            logger.info("Cleanup test: SUCCESS")
        
        # Final check in a separate session (for confirmation only)
        with get_db_session(read_only=True) as session:
            # Check that record was properly deleted
            count = session.execute(text(
                "SELECT COUNT(*) FROM hospitals WHERE name = 'TEMP_TEST'"
            )).scalar()
            
            assert count == 0, "Record not deleted properly"
            logger.info("Deletion verification test: SUCCESS")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_transaction_rollback():
    """Test explicit transaction rollback functionality"""
    try:
        from app.services.database_service import get_db_session, set_debug_mode
        
        logger.info("Testing transaction rollback functionality")
        
        # Generate unique test data
        hospital_id = str(uuid.uuid4())
        current_time = datetime.now(timezone.utc)
        test_name = f"ROLLBACK_TEST_{uuid.uuid4().hex[:8]}"
        
        # First session: Insert data and verify within the same session
        with get_db_session() as session:
            # Start a nested transaction
            with session.begin_nested() as nested_tx:
                insert_query = text("""
                INSERT INTO hospitals 
                    (hospital_id, name, license_no, created_at, updated_at) 
                VALUES 
                    (:hospital_id, :name, 'ROLLBACK_TEST', :created_at, :updated_at)
                """)
                
                session.execute(insert_query, {
                    "hospital_id": hospital_id,
                    "name": test_name,
                    "created_at": current_time,
                    "updated_at": current_time
                })
                
                # Verify record exists within this transaction
                count = session.execute(text(
                    "SELECT COUNT(*) FROM hospitals WHERE name = :name"
                ), {"name": test_name}).scalar()
                
                assert count > 0, "Record not inserted within transaction"
                logger.info("Record inserted in nested transaction: SUCCESS")
                
                # Explicitly roll back the nested transaction
                nested_tx.rollback()
                logger.info("Nested transaction rolled back: SUCCESS")
            
            # Verify record doesn't exist after rollback (still within outer session)
            count = session.execute(text(
                "SELECT COUNT(*) FROM hospitals WHERE name = :name"
            ), {"name": test_name}).scalar()
            
            assert count == 0, "Nested transaction rollback failed"
            logger.info("Transaction rollback verification (within session): SUCCESS")
                
        # Second session: Verify record doesn't exist in a fresh session
        with get_db_session(read_only=True) as session:
            count = session.execute(text(
                "SELECT COUNT(*) FROM hospitals WHERE name = :name"
            ), {"name": test_name}).scalar()
            
            assert count == 0, "Transaction rollback not persisted"
            logger.info("Transaction rollback verification (new session): SUCCESS")
            
        return True
        
    except Exception as e:
        logger.error(f"Rollback test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Running database service test function")
    
    try:
        # Run the test functions
        basic_success = test_db_service_basic()
        if basic_success:
            logger.info("Basic database service tests passed successfully")
            
            # Run transaction rollback test
            rollback_success = test_transaction_rollback()
            if rollback_success:
                logger.info("Transaction rollback tests passed successfully")
                logger.info("All tests passed successfully")
                sys.exit(0)
            else:
                logger.error("Transaction rollback tests failed")
                sys.exit(1)
        else:
            logger.error("Basic database service tests failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)