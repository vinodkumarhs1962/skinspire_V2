# scripts/setup_test_db.py

import sys
import os
from pathlib import Path
import logging
from sqlalchemy import text
from app.config.settings import settings
from app.database import init_db
from manage_db import apply_triggers

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)

def setup_test_database():
    """Initialize test database with required tables and initial data"""
    try:    
        # Get test database URL
        test_db_url = settings.get_database_url_for_env('testing')
        if not test_db_url:
            logger.error("TEST_DATABASE_URL not found in environment variables")
            logger.info("Available database URLs:")
            for env in ['development', 'testing', 'production']:
                url = settings.get_database_url_for_env(env)
                logger.info(f"  {env}: {'Set' if url else 'Not set'}")
            raise ValueError("TEST_DATABASE_URL must be set in .env file")
        
        logger.info(f"Using test database URL: {test_db_url}")
        db_manager = init_db(test_db_url)
        
        with db_manager.get_session() as session:
            # First, verify database exists
            try:
                session.execute(text("SELECT 1"))
                logger.info("Test database connection successful")
            except Exception as e:
                logger.error(f"Test database connection failed: {str(e)}")
                raise

            # Drop existing triggers before creating tables
            logger.info("Dropping existing triggers...")
            try:
                session.execute(text("""
                    DO $$ 
                    BEGIN
                        -- Drop existing triggers and functions
                        DROP TRIGGER IF EXISTS update_timestamp ON parameter_settings CASCADE;
                        DROP TRIGGER IF EXISTS track_user_changes ON parameter_settings CASCADE;
                    EXCEPTION WHEN OTHERS THEN
                        -- Ignore errors if triggers don't exist
                        NULL;
                    END $$;
                """))
                session.commit()
            except Exception as e:
                logger.warning(f"Warning while dropping triggers: {str(e)}")
                session.rollback()

            # Apply new triggers
            logger.info("Creating and applying new triggers...")
            try:
                # Read functions.sql
                sql_path = Path(project_root) / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    raise ValueError(f'functions.sql not found at {sql_path}')
                    
                logger.info('✓ Found functions.sql')
                with open(sql_path, 'r') as f:
                    sql = f.read()
                
                # Execute functions
                logger.info('Creating database functions...')
                session.execute(text(sql))
                
                # Apply triggers to all tables
                logger.info('Applying triggers to tables...')
                session.execute(text("SELECT create_audit_triggers('public')"))
                
                session.commit()
                logger.info('✓ Database functions and triggers applied successfully')
                
                # Verify triggers
                logger.info("Verifying triggers...")
                result = session.execute(text("""
                    SELECT trigger_name, event_object_table 
                    FROM information_schema.triggers 
                    WHERE trigger_schema = 'public'
                """))
                triggers = result.fetchall()
                logger.info(f"Found {len(triggers)} triggers:")
                for trigger in triggers:
                    logger.info(f"  - {trigger.trigger_name} on {trigger.event_object_table}")
                
            except Exception as e:
                session.rollback()
                logger.error(f"Error applying triggers: {str(e)}")
                raise
            
            logger.info("Test database setup completed successfully!")
            
    except Exception as e:
        logger.error(f"Error setting up test database: {str(e)}")
        raise    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Set environment for testing
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FLASK_APP'] = 'wsgi.py'
    setup_test_database()