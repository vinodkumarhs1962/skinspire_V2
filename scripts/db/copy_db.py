# scripts/db/copy_db.py
"""
DEPRECATED: This module is deprecated and will be removed in a future version.
The functionality has been moved to app.core.db_operations.copy

This module is kept temporarily for backward compatibility. Please update your
imports to use the new module.
"""

import os
import sys
import argparse
import logging
import warnings
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import from core modules
from app.core.db_operations.copy import copy_database as _copy_database

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def copy_database(source_env, target_env, schema_only=False, data_only=False, tables=None):
    """
    DEPRECATED: Use app.core.db_operations.copy.copy_database instead.
    
    Copy database from source environment to target environment.
    
    Args:
        source_env: Source environment ('dev', 'test', 'prod')
        target_env: Target environment ('dev', 'test', 'prod')
        schema_only: Copy only schema without data
        data_only: Copy only data without altering schema
        tables: Optional list of specific tables to copy
        
    Returns:
        True if successful, False otherwise
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.copy.copy_database instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # The core module doesn't support tables parameter yet, so show a warning
    if tables:
        logger.warning("The 'tables' parameter is not supported in the new implementation and will be ignored.")
    
    return _copy_database(source_env, target_env, schema_only, data_only)

def copy_test_to_dev():
    """
    DEPRECATED: Use app.core.db_operations.copy.copy_database instead.
    
    Backward-compatible wrapper for copy_test_to_dev.py
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.copy.copy_database('test', 'dev') instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    logger.info("Running copy_test_to_dev using enhanced copy functionality")
    return _copy_database('test', 'dev')

if __name__ == "__main__":
    warnings.warn(
        "This script is deprecated. Please use 'python scripts/manage_db.py copy-db' instead.",
        DeprecationWarning
    )
    
    # Check if this script is being run as copy_test_to_dev.py
    if 'copy_test_to_dev.py' in sys.argv[0]:
        # Run in backward-compatible mode
        success = copy_test_to_dev()
        sys.exit(0 if success else 1)
    
    # Regular CLI arguments
    parser = argparse.ArgumentParser(description="Copy database between environments")
    parser.add_argument("source", choices=["dev", "test", "prod"], help="Source environment")
    parser.add_argument("target", choices=["dev", "test", "prod"], help="Target environment")
    parser.add_argument("--schema-only", action="store_true", help="Copy only schema (no data)")
    parser.add_argument("--data-only", action="store_true", help="Copy only data (preserve schema)")
    parser.add_argument("--tables", nargs="+", help="Specific tables to copy")
    
    args = parser.parse_args()
    
    if args.schema_only and args.data_only:
        logger.error("Cannot use both --schema-only and --data-only options")
        sys.exit(1)
    
    success = copy_database(args.source, args.target, args.schema_only, args.data_only, args.tables)
    sys.exit(0 if success else 1)