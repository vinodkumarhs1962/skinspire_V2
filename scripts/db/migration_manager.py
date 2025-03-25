# scripts/db/migration_manager.py
"""
DEPRECATED: This module is deprecated and will be removed in a future version.
The functionality has been moved to app.core.db_operations.migration

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
from app.core.db_operations.migration import (
    create_migration as _create_migration,
    apply_migration as _apply_migration,
    rollback_migration as _rollback_migration,
    show_migrations as _show_migrations
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_migration(message, env, backup=True, auto_apply=False):
    """
    DEPRECATED: Use app.core.db_operations.migration.create_migration instead.
    
    Create database migration.
    
    Args:
        message: Migration message
        env: Target environment ('dev', 'test', 'prod')
        backup: Create backup before migration
        auto_apply: Automatically apply migration
        
    Returns:
        True if successful, False otherwise
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.migration.create_migration instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    success, migration_file = _create_migration(message, env, backup)
    
    if success and auto_apply:
        return apply_migration(env)
    
    # Ask to review migration if not auto-applying
    if success and not auto_apply and migration_file:
        logger.info(f"Created migration file: {migration_file}")
        
        response = input("Would you like to review the migration file? [Y/n] ")
        if not response.lower().startswith('n'):
            # On Windows, use default program to open file
            try:
                os.startfile(migration_file)
            except AttributeError:
                # On non-Windows platforms
                if sys.platform.startswith('darwin'):
                    import subprocess
                    subprocess.run(['open', migration_file])
                else:
                    import subprocess
                    subprocess.run(['xdg-open', migration_file])
        
        # Ask to apply migration
        if input("Apply migration now? [y/N] ").lower().startswith('y'):
            return apply_migration(env)
    
    return success

def apply_migration(env):
    """
    DEPRECATED: Use app.core.db_operations.migration.apply_migration instead.
    
    Apply pending migrations.
    
    Args:
        env: Target environment ('dev', 'test', 'prod')
        
    Returns:
        True if successful, False otherwise
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.migration.apply_migration instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return _apply_migration(env)

def rollback_migration(env, steps=1, backup=True):
    """
    DEPRECATED: Use app.core.db_operations.migration.rollback_migration instead.
    
    Roll back migrations.
    
    Args:
        env: Target environment ('dev', 'test', 'prod')
        steps: Number of migrations to roll back
        backup: Create backup before rollback
        
    Returns:
        True if successful, False otherwise
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.migration.rollback_migration instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # The backup parameter is not used in the core function since it always creates a backup
    if not backup:
        logger.warning("The 'backup=False' option is not supported in the new implementation. A backup will always be created.")
    
    return _rollback_migration(env, steps)

def show_migrations():
    """
    DEPRECATED: Use app.core.db_operations.migration.show_migrations instead.
    
    Show migration history.
    """
    warnings.warn(
        "This function is deprecated. Use app.core.db_operations.migration.show_migrations instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    migrations = _show_migrations()
    
    if not migrations:
        logger.info("No migrations found")
        return
    
    print("\nMigration History:")
    print("=====================================")
    print(f"{'#':<3} {'Revision':<10} {'Description':<40} {'Created At':<20}")
    print("-" * 80)
    
    for migration in migrations:
        desc = migration.get('description', 'Unknown')
        if len(desc) > 37:
            desc = desc[:34] + "..."
        
        print(f"{migration['id']:<3} {migration.get('short_revision', ''):<10} {desc:<40} {migration.get('created_at'):<20}")
    
    return migrations

if __name__ == "__main__":
    warnings.warn(
        "This script is deprecated. Please use 'python scripts/manage_db.py' for migration operations instead.",
        DeprecationWarning
    )
    
    parser = argparse.ArgumentParser(description="Database Migration Manager")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create migration command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('--message', '-m', required=True, help='Migration message')
    create_parser.add_argument('--env', default=None, help='Target environment (default: current environment)')
    create_parser.add_argument('--backup', action='store_true', default=True, help='Create backup before migration')
    create_parser.add_argument('--no-backup', action='store_true', help='Skip backup')
    create_parser.add_argument('--apply', action='store_true', help='Automatically apply migration')
    
    # Apply migrations command
    apply_parser = subparsers.add_parser('apply', help='Apply pending migrations')
    apply_parser.add_argument('--env', default=None, help='Target environment (default: current environment)')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Roll back migrations')
    rollback_parser.add_argument('--steps', type=int, default=1, help='Number of migrations to roll back')
    rollback_parser.add_argument('--env', default=None, help='Target environment (default: current environment)')
    rollback_parser.add_argument('--backup', action='store_true', default=True, help='Create backup before rollback')
    rollback_parser.add_argument('--no-backup', action='store_true', help='Skip backup')
    
    # Show migrations command
    show_parser = subparsers.add_parser('show', help='Show migration history')
    
    args = parser.parse_args()
    
    # Get current environment if not specified
    if hasattr(args, 'env') and args.env is None:
        from app.core.db_operations.utils import get_db_config, get_short_env_name
        
        db_config = get_db_config()
        full_env = db_config.get_active_env()
        args.env = get_short_env_name(full_env)
    
    if args.command == 'create':
        backup = args.backup and not args.no_backup
        success = create_migration(args.message, args.env, backup, args.apply)
        sys.exit(0 if success else 1)
    elif args.command == 'apply':
        success = apply_migration(args.env)
        sys.exit(0 if success else 1)
    elif args.command == 'rollback':
        backup = args.backup and not args.no_backup
        success = rollback_migration(args.env, args.steps, backup)
        sys.exit(0 if success else 1)
    elif args.command == 'show':
        show_migrations()
    else:
        parser.print_help()