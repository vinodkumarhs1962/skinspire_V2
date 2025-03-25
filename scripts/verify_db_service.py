# scripts/verify_db_service.py
"""
DEPRECATED: This module is deprecated and will be removed in a future version.
The functionality has been moved to app.core.db_operations.maintenance.check_db

This module is kept temporarily for backward compatibility. Please use:
'python scripts/manage_db.py check-database' instead.
"""

import os
import sys
import logging
import warnings
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import from core module
from app.core.db_operations.maintenance import check_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DB_VERIFY")

def verify_database_service(env=None, verbose=False):
    """
    DEPRECATED: Use app.core.db_operations.maintenance.check_db instead.
    
    Verify that the database service can connect to the database.
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.maintenance.check_db instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Check the database using the core module
    results = check_db(env)
    
    # Print the results
    logger.info(f"Active environment: {results.get('environment')}")
    logger.info(f"Database URL: {results.get('database_url')}")
    
    if verbose and results.get('flask_config'):
        logger.info('\nFlask App Configuration:')
        logger.info('-' * 50)
        for key, value in results.get('flask_config', {}).items():
            logger.info(f'{key}: {value}')
    
    logger.info('\nConnection Tests:')
    logger.info('-' * 50)
    logger.info(f'Database connection: {"SUCCESS" if results.get("connection_test") else "FAILED"}')
    logger.info(f'Test query: {"SUCCESS" if results.get("query_test") else "FAILED"}')
    logger.info(f'Table creation: {"SUCCESS" if results.get("table_creation_test") else "FAILED"}')
    
    if results.get('errors'):
        logger.info('\nErrors:')
        logger.info('-' * 50)
        for error in results.get('errors', []):
            logger.info(f'- {error}')
    
    if results.get('success'):
        logger.info('\nAll database checks passed successfully!')
    else:
        logger.error('\nDatabase checks failed')
    
    return results.get('success', False)

if __name__ == "__main__":
    warnings.warn(
        "This script is deprecated. Please use 'python scripts/manage_db.py check-database' instead.",
        DeprecationWarning
    )
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Verify database service')
    parser.add_argument('--env', choices=['dev', 'test', 'prod'], help='Environment to check')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')
    args = parser.parse_args()
    
    logger.info("Starting database service verification")
    success = verify_database_service(args.env, args.verbose)
    
    if success:
        logger.info("Database service verification completed successfully")
        sys.exit(0)
    else:
        logger.error("Database service verification failed")
        sys.exit(1) 