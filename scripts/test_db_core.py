# scripts/test_db_core.py
# python scripts/test_db_core.py
import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import test environment setup
try:
    from tests.test_environment import setup_test_environment
    
    # Run setup to configure the environment correctly
    setup_test_environment()
    logger.info("Test environment configured successfully")
except ImportError as e:
    logger.error(f"Could not import test environment: {e}")
    logger.info("Using fallback environment setup")
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'

# Create necessary directories (if needed)
core_path = project_root / "app" / "core" / "db_operations"
os.makedirs(core_path, exist_ok=True)

# Import utilities from correct path
try:
    from app.core.db_operations.utils import normalize_env_name, get_short_env_name, get_db_config
    logger.info("Successfully imported utils module")
    
    # Test environment normalization
    logger.info(f"Normalized 'dev' to: {normalize_env_name('dev')}")
    logger.info(f"Normalized 'test' to: {normalize_env_name('test')}")
    logger.info(f"Short name for 'development': {get_short_env_name('development')}")
    
    # Test database configuration
    db_config = get_db_config()
    active_env = db_config.get_active_env()
    db_url = db_config.get_database_url_for_env(active_env)
    logger.info(f"Active environment: {active_env}")
    
    # Mask password in URL for security
    import re
    if db_url:
        masked_url = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', db_url)
        logger.info(f"Database URL: {masked_url}")
    else:
        logger.info("Database URL: None")
        
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Continue with script even if this part fails

# Test database service integration
try:
    from app.services.database_service import get_db_session, get_active_env
    logger.info("\nTesting database service integration:")
    
    env = get_active_env()
    logger.info(f"Active environment from database_service: {env}")
    
    # Try to create a session
    with get_db_session() as session:
        from sqlalchemy import text
        result = session.execute(text("SELECT current_database()")).scalar()
        logger.info(f"Connected to database: {result}")
        
        # List tables
        tables = session.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )).fetchall()
        logger.info(f"Found {len(tables)} tables in database")
        
except ImportError as e:
    logger.error(f"Import error with database service: {e}")
except Exception as e:
    logger.error(f"Error testing database service: {e}")

# Test backup functionality if module exists
try:
    from app.core.db_operations.backup import backup_database, list_backups
    logger.info("\nTesting backup operations:")
    
    # List existing backups first
    backups = list_backups()
    logger.info(f"Found {len(backups)} existing backups")
    
    # Create a test backup
    logger.info("Creating test backup...")
    success, backup_path = backup_database('test')
    if success:
        logger.info(f"Backup created successfully at: {backup_path}")
    else:
        logger.error("Failed to create backup")
    
except ImportError as e:
    logger.error(f"Import error with backup module: {e}")
except Exception as e:
    logger.error(f"Error testing backup functionality: {e}")

# Test manage_db.py
try:
    import subprocess
    logger.info("\nTesting manage_db.py CLI interface:")
    
    # Run a simple command
    result = subprocess.run(
        [sys.executable, 'scripts/manage_db.py', 'check-db'],
        check=False,
        capture_output=True,
        text=True
    )
    
    logger.info("check-db command output:")
    for line in result.stdout.splitlines():
        logger.info(f"  {line}")
    
    if result.returncode != 0:
        logger.error(f"Command failed with error: {result.stderr}")
    
except Exception as e:
    logger.error(f"Error testing manage_db.py: {e}")

logger.info("\nTest script completed")