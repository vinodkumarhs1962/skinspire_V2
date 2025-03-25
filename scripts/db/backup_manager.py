# scripts/db/backup_manager.py
"""
DEPRECATED: This module is deprecated and will be removed in a future version.
The functionality has been moved to app.core.db_operations.backup and
app.core.db_operations.restore

This module is kept temporarily for backward compatibility. Please update your
imports to use the new modules.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import warnings

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import from core modules
from app.core.db_operations.backup import backup_database as _backup_database, list_backups as _list_backups
from app.core.db_operations.restore import restore_database as _restore_database

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_backup(env, output_file=None):
    """
    DEPRECATED: Use app.core.db_operations.backup.backup_database instead.
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.backup.backup_database instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _backup_database(env, output_file)

def restore_backup(backup_file, env):
    """
    DEPRECATED: Use app.core.db_operations.restore.restore_database instead.
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.restore.restore_database instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return _restore_database(env, backup_file)

def list_backups():
    """
    DEPRECATED: Use app.core.db_operations.backup.list_backups instead.
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.backup.list_backups instead.",
        DeprecationWarning,
        stacklevel=2
    )
    backups = _list_backups()
    
    if not backups:
        logger.info("No database backups found")
        return
    
    print("\nAvailable Database Backups:")
    print("===========================")
    print(f"{'Filename':<50} {'Size':<10} {'Date':<20}")
    print("-" * 80)
    
    for backup in backups:
        print(f"{backup['name']:<50} {backup['size_kb']:<10} KB {backup['modified']:<20}")
    
    return backups

if __name__ == "__main__":
    warnings.warn(
        "This script is deprecated. Please use 'python scripts/manage_db.py' instead.",
        DeprecationWarning
    )
    
    parser = argparse.ArgumentParser(description="Database Backup Manager")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create backup command
    backup_parser = subparsers.add_parser('backup', help='Create database backup')
    backup_parser.add_argument('--env', default=None, choices=['dev', 'test', 'prod'], 
                             help='Environment to backup (default: current environment)')
    backup_parser.add_argument('--output', help='Output filename')
    
    # Restore backup command
    restore_parser = subparsers.add_parser('restore', help='Restore database from backup')
    restore_parser.add_argument('file', help='Backup file to restore from')
    restore_parser.add_argument('--env', default=None, choices=['dev', 'test', 'prod'],
                              help='Target environment (default: current environment)')
    
    # List backups command
    list_parser = subparsers.add_parser('list', help='List available backups')
    
    args = parser.parse_args()
    
    # Get current environment if not specified
    if hasattr(args, 'env') and args.env is None:
        from app.core.db_operations.utils import get_db_config, get_short_env_name
        
        db_config = get_db_config()
        full_env = db_config.get_active_env()
        args.env = get_short_env_name(full_env)
    
    if args.command == 'backup':
        success, backup_path = create_backup(args.env, args.output)
        sys.exit(0 if success else 1)
    elif args.command == 'restore':
        success = restore_backup(args.file, args.env)
        sys.exit(0 if success else 1)
    elif args.command == 'list':
        list_backups()
    else:
        parser.print_help()