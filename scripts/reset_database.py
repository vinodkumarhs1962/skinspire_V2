# scripts/reset_database.py
# not tested 3.3.25

import sys
from pathlib import Path
import logging
import subprocess
from sqlalchemy import text

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.config.settings import settings
from app.db import init_db

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_and_initialize_database():
    """Reset database (drop all tables) and initialize with proper schema"""
    try:
        # Get database URL for the current environment
        database_url = settings.DATABASE_URL
        logger.info(f"Using database URL: {database_url}")
        
        # 1. Initialize database connection
        db_manager = init_db(database_url)
        
        # 2. Drop all existing tables
        logger.info("Dropping all existing tables...")
        with db_manager.get_session() as session:
            # Drop tables in correct order to avoid constraint violations
            drop_sql = """
            DO $$ 
            BEGIN
                -- Disable triggers temporarily
                SET CONSTRAINTS ALL DEFERRED;
                
                -- Drop tables in order
                DROP TABLE IF EXISTS staff CASCADE;
                DROP TABLE IF EXISTS branches CASCADE;
                DROP TABLE IF EXISTS login_history CASCADE;
                DROP TABLE IF EXISTS user_sessions CASCADE;
                DROP TABLE IF EXISTS user_role_mapping CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
                DROP TABLE IF EXISTS hospitals CASCADE;
                DROP TABLE IF EXISTS role_master CASCADE;
                DROP TABLE IF EXISTS module_master CASCADE;
                DROP TABLE IF EXISTS parameter_settings CASCADE;
                DROP TABLE IF EXISTS role_module_access CASCADE;
                DROP TABLE IF EXISTS patients CASCADE;
                
                -- Re-enable triggers
                SET CONSTRAINTS ALL IMMEDIATE;
            END $$;
            """
            session.execute(text(drop_sql))
            session.commit()
            logger.info("✓ Successfully dropped all tables")
        
        # 3. Create tables from SQLAlchemy models with all required columns
        logger.info("Creating tables from SQLAlchemy models...")
        db_manager.create_tables()
        logger.info("✓ Tables created successfully!")
        
        # 4. Run create_database.py to initialize data
        logger.info("Initializing database with data...")
        create_db_script = Path(__file__).parent / "create_database.py"
        
        try:
            # Use subprocess to run the create_database.py script
            result = subprocess.run(
                [sys.executable, str(create_db_script)],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Log output from create_database.py
            for line in result.stdout.splitlines():
                logger.info(f"  {line}")
            
            logger.info("✓ Database initialization completed successfully!")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running create_database.py: {e.stderr}")
            raise
            
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting database reset and initialization...")
    reset_and_initialize_database()
    logger.info("Database reset and initialization completed successfully!")
    logger.info("You can now run populate_test_data.py to add test data.")
