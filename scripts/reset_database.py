# scripts/reset_database.py
"""
DEPRECATED: This module is deprecated and will be removed in a future version.
The functionality has been moved to app.core.db_operations.maintenance

This module is kept temporarily for backward compatibility. Please use:
'python scripts/manage_db.py reset-database' or
'python scripts/manage_db.py reset-and-initialize' instead.
"""

import sys
import logging
import warnings
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import from core modules
from app.core.db_operations.maintenance import reset_db, reset_and_init

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_and_initialize_database(env=None, init=True):
    """
    DEPRECATED: Use app.core.db_operations.maintenance.reset_db or
    app.core.db_operations.maintenance.reset_and_init instead.
    
    Reset database (drop all tables) and initialize with proper schema
    """
    warnings.warn(
        "This function is deprecated. Use core modules through manage_db.py instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if init:
        logger.info("Resetting and initializing database...")
        success = reset_and_init(env)
    else:
        logger.info("Resetting database (without initialization)...")
        success = reset_db(env)
    
    if success:
        logger.info("Database reset and initialization completed successfully!")
    else:
        logger.error("Database reset and initialization failed!")
    
    return success

if __name__ == "__main__":
    warnings.warn(
        "This script is deprecated. Please use 'python scripts/manage_db.py reset-database' or "
        "'python scripts/manage_db.py reset-and-initialize' instead.",
        DeprecationWarning
    )
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Reset and initialize database')
    parser.add_argument('--env', choices=['dev', 'test', 'prod'], help='Environment to reset')
    parser.add_argument('--no-init', action='store_true', help='Skip initialization')
    args = parser.parse_args()
    
    logger.info("Starting database reset and initialization...")
    success = reset_and_initialize_database(args.env, not args.no_init)
    
    if success:
        logger.info("Database reset completed successfully!")
        sys.exit(0)
    else:
        logger.error("Database reset failed!")
        sys.exit(1)