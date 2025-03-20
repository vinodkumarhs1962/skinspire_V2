# scripts/verify_db_service.py
# python scripts/verify_db_service.py -v
# Simple script to verify the database service is working correctly

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

import logging
from sqlalchemy import text, inspect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_database_service():
    """Verify that the database service can connect to the test database"""
    try:
        # Import the database service - initialization should happen automatically now
        from app.services.database_service import get_db_session, DatabaseService
        
        # Get active environment
        env = DatabaseService.get_active_environment()
        logger.info(f"Active environment: {env}")
        
        # Get database URL
        db_url = DatabaseService.get_database_url()
        logger.info(f"Database URL: {db_url}")
        
        # Now use the database service
        logger.info("Testing database service")
        with get_db_session() as session:
            # Basic connectivity test
            result = session.execute(text("SELECT 1")).scalar()
            logger.info(f"Database connection test: {'SUCCESS' if result == 1 else 'FAILED'}")
            
            # Get schema name
            schema_result = session.execute(text("SELECT current_schema()")).scalar()
            logger.info(f"Current schema: {schema_result}")
            
            # Get database name
            db_name_result = session.execute(text("SELECT current_database()")).scalar()
            logger.info(f"Current database: {db_name_result}")
            
            # Check for key tables
            inspector = inspect(session.bind)
            tables = inspector.get_table_names()
            logger.info(f"Found {len(tables)} tables in database")
            
            # Check key tables
            key_tables = ['users', 'hospitals', 'staff', 'patients']
            missing_tables = [table for table in key_tables if table not in tables]
            
            if missing_tables:
                logger.warning(f"Missing key tables: {', '.join(missing_tables)}")
            else:
                logger.info("All key tables found in database")
            
            # Try to run a transaction
            try:
                # Get the current timestamp for created_at/updated_at fields
                current_time = datetime.now(timezone.utc).isoformat()
                
                # Generate a unique hospital ID for testing
                test_hospital_id = uuid.uuid4()
                
                # Start a nested transaction that we'll roll back
                with session.begin_nested():
                    # Insert a test record with a UNIQUE hospital_id and timestamps
                    insert_query = """
                    INSERT INTO hospitals 
                        (hospital_id, name, license_no, created_at, updated_at) 
                    VALUES 
                        (:hospital_id, 'TEST_DB_SERVICE', 'TEST1234', :created_at, :updated_at)
                    """
                    
                    params = {
                        "hospital_id": test_hospital_id,
                        "created_at": current_time,
                        "updated_at": current_time
                    }
                    
                    session.execute(text(insert_query), params)
                    
                    # Verify it was inserted
                    result = session.execute(text(
                        "SELECT COUNT(*) FROM hospitals WHERE name = 'TEST_DB_SERVICE'"
                    )).scalar()
                    
                    logger.info(f"Transaction test - record inserted: {'YES' if result > 0 else 'NO'}")
                    
                    # Roll back the transaction
                    raise Exception("Intentional rollback")
            except Exception as e:
                if str(e) == "Intentional rollback":
                    # This is expected
                    pass
                else:
                    logger.error(f"Transaction test failed: {e}")
            
            # Verify the record was rolled back
            result = session.execute(text(
                "SELECT COUNT(*) FROM hospitals WHERE name = 'TEST_DB_SERVICE'"
            )).scalar()
            
            logger.info(f"Transaction rollback test: {'SUCCESS' if result == 0 else 'FAILED'}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database service verification failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting database service verification")
    success = verify_database_service()
    
    if success:
        logger.info("Database service verification completed successfully")
        sys.exit(0)
    else:
        logger.error("Database service verification failed")
        sys.exit(1)