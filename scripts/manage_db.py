#!/usr/bin/env python
# skinspire_v2/scripts/manage_db.py
# python scripts/manage_db.py --help

#  INDIVIDUAL COMMANDS
# python scripts/manage_db.py apply-all-db-schema-triggers
# python scripts/manage_db.py apply-base-db-triggers
# python scripts/manage_db.py apply-db-triggers
# python scripts/manage_db.py check-database
# python scripts/manage_db.py copy-db
# python scripts/manage_db.py copy-db dev test
# python scripts/manage_db.py create-backup
# python scripts/manage_db.py create-backup --env dev
# python scripts/manage_db.py create-db-migration
# python scripts/manage_db.py create-db-migration -m "Your migration message"
# python scripts/manage_db.py drop-all-db-tables
# python scripts/manage_db.py initialize-db
# python scripts/manage_db.py inspect-db
# python scripts/manage_db.py list-all-backups
# python scripts/manage_db.py reset-and-initialize
# python scripts/manage_db.py reset-database
# python scripts/manage_db.py restore-backup
# python scripts/manage_db.py rollback-db-migration
# python scripts/manage_db.py show-all-migrations
# python scripts/manage_db.py show-db-config
# python scripts/manage_db.py switch-env
# python scripts/manage_db.py test-db-triggers
# python scripts/manage_db.py verify-db-triggers
# python scripts/manage_db.py reset-migration-tracking
# python scripts/manage_db.py reset-migration-tracking --mode trace-reset
# python scripts/manage_db.py clean-migration-files   # not working  use another command below
# python scripts/manage_db.py clean-migration-files --force    # not working use another command below

# 
# MIGRATION STEPS  
# python scripts/manage_db.py detect-schema-changes
# python scripts/manage_db.py create-model-migration -m "Your message here"
# python scripts/manage_db.py create-model-migration -m "Your message" --apply
# python scripts/manage_db.py apply-db-migration   # Apply to current environment
# python scripts/manage_db.py init-migrations
# set FLASK_APP=app:create_app  flask db init   # for initializing database direct flask command
# python scripts/manage_db.py apply-db-migration --env dev   # Apply to dev database
# python scripts/manage_db.py apply-db-migration --env test  # Apply to test database
# python scripts/manage_db.py debug-migration-config

# python scripts/manage_db.py sync-models-to-db
# python scripts/manage_db.py execute-sql path/to/sql_file.sql
# python scripts/manage_db.py verify-db-structure

# ALEMBIC MIGRATION TRACKING RESET or STAMP COMMANDS
# python scripts/manage_db.py stamp-migrations  # Stamp to latest migration (head) 
# python scripts/manage_db.py stamp-migrations base  # Stamp to base (no migrations):  
# python scripts/manage_db.py stamp-migrations <revision_hash>  # Stamp to a specific revision:   
# python scripts/manage_db.py stamp-migrations --force  # Force stamp without confirmation: 
# python scripts/manage_db.py merge-migration-heads
# python scripts/manage_db.py merge-migration-heads -m "Resolving multiple migration branches"
# python scripts/manage_db.py reset-migrations-completely   # With confirmation prompt:
# python scripts/manage_db.py reset-migrations-completely --force  # Skip confirmation (for scripts):

# Setup imports for manage_db.py
import os
import sys
import click
from pathlib import Path
import subprocess
from datetime import datetime
from functools import wraps
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to Python path - using absolute paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Try to import centralized environment module first
try:
    from app.core.environment import Environment, current_env
    ENVIRONMENT_MODULE_AVAILABLE = True
    
    # Set up environment using centralized approach
    def setup_environment():
        """Set up environment variables for database operations using centralized Environment"""
        logger.debug(f"Setting up environment for: {current_env}")
        
        # Set database URLs if not already set
        if current_env == 'testing' and not os.environ.get('TEST_DATABASE_URL'):
            os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        elif current_env == 'development' and not os.environ.get('DEV_DATABASE_URL'):
            os.environ['DEV_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
        elif current_env == 'production' and not os.environ.get('PROD_DATABASE_URL'):
            os.environ['PROD_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod'
        
        logger.debug(f"Environment variables set for {current_env}")
except ImportError:
    ENVIRONMENT_MODULE_AVAILABLE = False
    
    # Fall back to legacy environment setup
    def setup_environment():
        """Set up environment variables for database operations"""
        if os.environ.get('FLASK_ENV') == 'testing' and not os.environ.get('TEST_DATABASE_URL'):
            os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        elif os.environ.get('FLASK_ENV') == 'development' and not os.environ.get('DEV_DATABASE_URL'):
            os.environ['DEV_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
        elif os.environ.get('FLASK_ENV') == 'production' and not os.environ.get('PROD_DATABASE_URL'):
            os.environ['PROD_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod'

# Set up environment before imports
setup_environment()

# Import core database operations
try:
    from app.core.db_operations import (
        # Utility functions
        normalize_env_name,
        get_db_config,
        
        # Backup operations
        backup_database,
        list_backups,
        
        # Restore operations
        restore_database,
        
        # Migration operations
        create_migration,
        apply_migration,
        rollback_migration,
        show_migrations,
        
        # Copy operations
        copy_database,
        
        # Trigger operations
        apply_base_triggers, 
        apply_triggers,
        apply_all_schema_triggers,
        verify_triggers,
        
        # Maintenance operations
        check_db,
        reset_db,
        init_db,
        drop_all_tables
    )
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    # This fallback allows the file to be run even before core modules are set up
    click.echo(f"Warning: Could not import core modules: {e}")
    click.echo("Some commands may not work. Ensure app/core/db_operations is set up correctly.")
    # Set up placeholders to prevent errors
    backup_database = apply_base_triggers = apply_triggers = apply_all_schema_triggers = None
    verify_triggers = check_db = reset_db = init_db = drop_all_tables = None
    list_backups = restore_database = create_migration = apply_migration = None
    rollback_migration = show_migrations = copy_database = None
    normalize_env_name = lambda x: x
    get_db_config = None
    CORE_MODULES_AVAILABLE = False

# Global variables for lazy loading
_app = None
_db = None
_db_config = None

def get_app():
    """Get Flask app instance, initializing it only when needed"""
    global _app
    if _app is None:
        try:
            from app import create_app
            _app = create_app()
        except Exception as e:
            click.echo(f"Error initializing Flask app: {str(e)}")
            click.echo("If this command requires database connectivity, ensure your environment is set correctly.")
            click.echo("You may need to run: set FLASK_ENV=testing")
            sys.exit(1)
    return _app

def get_db():
    """Get database instance, initializing it only when needed"""
    global _db
    if _db is None:
        try:
            from app import db
            _db = db
        except Exception as e:
            click.echo(f"Error accessing database module: {str(e)}")
            sys.exit(1)
    return _db

def get_database_config():
    """Get DatabaseConfig, initializing it only when needed"""
    global _db_config
    if _db_config is None:
        try:
            from app.config.db_config import DatabaseConfig
            _db_config = DatabaseConfig
        except Exception as e:
            click.echo(f"Error accessing database configuration: {str(e)}")
            sys.exit(1)
    return _db_config

def safe_with_appcontext(f):
    """Safely provide app context, with better error handling than Flask's version"""
    @wraps(f)
    def decorated(*args, **kwargs):
        app = get_app()
        try:
            with app.app_context():
                return f(*args, **kwargs)
        except Exception as e:
            click.echo(f"Error in app context: {str(e)}")
            sys.exit(1)
    return decorated

def mask_db_url(url):
    """Mask password in database URL for display"""
    if url and '://' in url and '@' in url:
        parts = url.split('@')
        credentials = parts[0].split('://')
        if len(credentials) > 1 and ':' in credentials[1]:
            user_pass = credentials[1].split(':')
            return f"{credentials[0]}://{user_pass[0]}:****@{parts[1]}"
    return url

@click.group()
def cli():
    """Database management commands"""
    pass


# Trigger Operations Commands

@cli.command()
def apply_base_db_triggers():
    """Apply only base database trigger functionality (without table-specific triggers)"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    click.echo('Starting to apply base trigger functions...')
    success = apply_base_triggers()
    
    if success:
        click.echo('SUCCESS: Base trigger functions applied successfully')
    else:
        click.echo('FAILED: Failed to apply base trigger functions')
        sys.exit(1)

@cli.command()
def apply_db_triggers():
    """Apply all database triggers and functions with progressive fallbacks"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    click.echo('Starting to apply database triggers and functions...')
    success = apply_triggers()
    
    if success:
        click.echo('SUCCESS: Database triggers applied successfully')
    else:
        click.echo('FAILED: Failed to apply database triggers')
        sys.exit(1)

@cli.command()
def apply_all_db_schema_triggers():
    """Apply base database trigger functionality to all schemas"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    click.echo('Starting to apply triggers to all schemas...')
    success = apply_all_schema_triggers()
    
    if success:
        click.echo('SUCCESS: Applied triggers to all schemas successfully')
    else:
        click.echo('FAILED: Failed to apply triggers to all schemas')
        sys.exit(1)

@cli.command()
def verify_db_triggers():
    """Verify trigger installation"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    click.echo('Verifying trigger installation...')
    results = verify_triggers()
    
    # Display results
    if 'functions' in results:
        for line in results['functions']:
            click.echo(line)
    
    if 'critical_triggers' in results and results['critical_triggers']:
        for line in results['critical_triggers']:
            click.echo(line)
            
    if 'tables' in results and results['tables']:
        for line in results['tables']:
            click.echo(line)
    
    if not results.get('success', False):
        if 'errors' in results and results['errors']:
            for error in results['errors']:
                click.echo(f"Error: {error}")
        click.echo('FAILED: Trigger verification failed')
        sys.exit(1)


# Maintenance Commands

@cli.command()
def drop_all_db_tables():
    """Drop all tables in correct order"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    if not click.confirm('Warning! This will DROP ALL TABLES. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
        
    click.echo('Dropping all tables...')
    success = drop_all_tables()
    
    if success:
        click.echo('SUCCESS: All tables dropped successfully')
    else:
        click.echo('FAILED: Failed to drop all tables')
        sys.exit(1)

@cli.command()
def check_database():
    """Comprehensive database connection check"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    click.echo('Checking database connection...')
    results = check_db()
    
    click.echo(f'\nActive environment: {results.get("environment")}')
    click.echo(f'Database URL: {results.get("database_url")}')
    
    if results.get('flask_config'):
        click.echo('\nFlask App Configuration:')
        click.echo('-' * 50)
        for key, value in results.get('flask_config', {}).items():
            click.echo(f'{key}: {value}')
    
    click.echo('\nConnection Tests:')
    click.echo('-' * 50)
    click.echo(f'Database connection: {"SUCCESS" if results.get("connection_test") else "FAILED"}')
    click.echo(f'Test query: {"SUCCESS" if results.get("query_test") else "FAILED"}')
    click.echo(f'Table creation: {"SUCCESS" if results.get("table_creation_test") else "FAILED"}')
    
    if results.get('errors'):
        click.echo('\nErrors:')
        click.echo('-' * 50)
        for error in results.get('errors', []):
            click.echo(f'- {error}')
    
    if results.get('success'):
        click.echo('\nAll database checks passed successfully!')
    else:
        click.echo('\nFAILED: Database checks failed')
        sys.exit(1)

@cli.command()
def reset_database():
    """Remove existing migrations and reinitialize"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    if not click.confirm('Warning! This will reset the database and migrations. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
        
    click.echo('Starting database reset...')
    success = reset_db()
    
    if success:
        click.echo('SUCCESS: Database reset completed successfully')
    else:
        click.echo('FAILED: Database reset failed')
        sys.exit(1)

@cli.command()
def initialize_db():
    """Initialize database tables without migrations"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    click.echo('Starting database initialization...')
    success = init_db()
    
    if success:
        click.echo('SUCCESS: Database initialization completed successfully')
    else:
        click.echo('FAILED: Database initialization failed')
        sys.exit(1)

@cli.command()
def show_db_config():
    """Show current database configuration"""
    try:
        from app.config.db_config import DatabaseConfig
        
        env = DatabaseConfig.get_active_env()
        config = DatabaseConfig.get_config(env)
        
        # Mask password in URL
        db_url = config.get('url', '')
        if db_url and '://' in db_url and '@' in db_url:
            parts = db_url.split('@')
            credentials = parts[0].split('://')
            if len(credentials) > 1 and ':' in credentials[1]:
                user_pass = credentials[1].split(':')
                masked_url = f"{credentials[0]}://{user_pass[0]}:****@{parts[1]}"
                config['url'] = masked_url
        
        click.echo('\nDatabase Configuration:')
        click.echo('-' * 50)
        click.echo(f'Active Environment: {env}')
        
        for key, value in config.items():
            click.echo(f'{key}: {value}')
            
        click.echo('-' * 50)
    except Exception as e:
        click.echo(f"Error accessing configuration: {str(e)}")
        sys.exit(1)

@cli.command()
def reset_and_initialize():
    """Reset database (drop all tables) and reinitialize with create_database.py"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    if not click.confirm('Warning! This will reset the database and reinitialize it. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
        
    click.echo('Starting database reset and initialization...')
    
    # First drop all tables
    drop_success = drop_all_tables()
    if not drop_success:
        click.echo('FAILED: Failed to drop all tables')
        sys.exit(1)
    
    # Then initialize database
    init_success = init_db()
    if not init_success:
        click.echo('FAILED: Failed to initialize database')
        sys.exit(1)
    
    # Apply triggers
    click.echo('Applying database triggers...')
    trigger_success = apply_triggers()
    if not trigger_success:
        click.echo('Warning: Failed to apply triggers, but continuing')
    
    # Run create_database.py script to initialize data
    click.echo('Initializing database with data...')
    create_db_script = Path(__file__).parent / "create_database.py"
    
    try:
        # Use subprocess to run the create_database.py script
        result = subprocess.run(
            [sys.executable, str(create_db_script)],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Output from create_database.py
        click.echo("Output from create_database.py:")
        for line in result.stdout.splitlines():
            click.echo(f"  {line}")
        
        click.echo('SUCCESS: Database reset and initialization completed successfully!')
        
    except subprocess.CalledProcessError as e:
        click.echo(f'FAILED: Error running create_database.py: {e.stderr}')
        sys.exit(1)

@cli.command()
def test_db_triggers():
    """Run trigger tests to verify functionality"""
    try:
        # Check if the test script exists
        test_script = Path(__file__).parent / 'test_triggers.py'
        if not test_script.exists():
            # Try in tests directory
            test_script = Path(__file__).parent.parent / 'tests' / 'test_security' / 'test_database_triggers.py'
            if not test_script.exists():
                click.echo("Warning: Could not find trigger test script")
                return
        
        click.echo("Running trigger functionality tests...")
        
        # Run the tests using pytest
        result = subprocess.run(
            ["pytest", str(test_script), "-v"],
            check=False,  # Don't raise exception on test failure
            capture_output=True,
            text=True
        )
        
        # Display test output
        for line in result.stdout.splitlines():
            click.echo(line)
        
        if result.returncode == 0:
            click.echo("SUCCESS: All trigger tests passed!")
        else:
            click.echo("Warning: Some trigger tests failed. Please check the output for details.")
            
    except Exception as e:
        click.echo(f"Error running trigger tests: {e}")


# Backup Operations Commands

@cli.command()
@click.option('--env', default=None, help='Environment to backup (default: current environment)')
@click.option('--output', help='Output filename')
def create_backup(env, output):
    """Create database backup"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # If env not specified, use current environment
    if env is None:
        try:
            from app.config.db_config import DatabaseConfig
            env = DatabaseConfig.get_active_env()
            # Convert to short form
            env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
            env = env_map.get(env, env)
        except Exception as e:
            click.echo(f"Failed to determine environment: {e}")
            sys.exit(1)
    
    click.echo(f"Creating backup of {env} database...")
    success, backup_path = backup_database(env, output)
    
    if success:
        click.echo(f"SUCCESS: Backup created successfully: {backup_path}")
    else:
        click.echo("FAILED: Backup failed")
        sys.exit(1)

@cli.command()
def list_all_backups():
    """List available database backups"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    backups = list_backups()
    
    if not backups:
        click.echo("No database backups found")
        return
    
    click.echo("\nAvailable Database Backups:")
    click.echo("===========================")
    click.echo(f"{'#':<3} {'Filename':<50} {'Size':<10} {'Date':<20}")
    click.echo("-" * 85)
    
    for backup in backups:
        click.echo(f"{backup['id']:<3} {backup['name']:<50} {backup['size_kb']:<10} KB {backup['modified']:<20}")

@cli.command()
@click.argument('file', required=False)
def restore_backup(file):
    """Restore database from backup"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # If no file specified, list backups and ask user to choose
    if not file:
        backups = list_backups()
        if not backups:
            click.echo("No database backups found")
            return
        
        click.echo("\nAvailable Backups:")
        for backup in backups:
            click.echo(f"{backup['id']}. {backup['name']} ({backup['size_kb']} KB, {backup['modified']})")
        
        # Ask user to select a backup
        backup_num = click.prompt("Enter backup number to restore", type=int, default=1)
        if backup_num < 1 or backup_num > len(backups):
            click.echo(f"Invalid backup number. Please choose 1-{len(backups)}")
            return
        
        file = backups[backup_num-1]['path']
    
    # Import Environment module
    try:
        from app.core.environment import Environment, current_env
        
        # Get short name for the current environment
        env = Environment.get_short_name(current_env)
        click.echo(f"Using environment from centralized configuration: {env} ({current_env})")
    except ImportError:
        # Fall back to old method if Environment module is not available
        try:
            from app.config.db_config import DatabaseConfig
            db_env = DatabaseConfig.get_active_env()
            # Convert to short form
            env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
            env = env_map.get(db_env, 'dev')
        except Exception as e:
            click.echo(f"Failed to determine environment: {e}")
            # Check FLASK_ENV as last resort
            if 'FLASK_ENV' in os.environ:
                flask_env = os.environ['FLASK_ENV']
                if flask_env == 'development':
                    env = 'dev'
                elif flask_env == 'testing':
                    env = 'test'
                elif flask_env == 'production':
                    env = 'prod'
                else:
                    env = 'dev'
            else:
                env = 'dev'  # Default as last resort
    
    if not click.confirm(f'Warning! This will restore the {env} database from {file}. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo(f"Restoring {env} database from {file}...")
    success = restore_database(env, file)
    
    if success:
        click.echo("SUCCESS: Database restored successfully")
    else:
        click.echo("FAILED: Database restore failed")
        sys.exit(1)

# Migration Operations Commands

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
@click.option('--backup/--no-backup', default=True, help='Create backup before migration')
@click.option('--apply', is_flag=True, help='Automatically apply migration')
def create_db_migration(message, backup, apply):
    """Create database migration"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    try:
        from app.config.db_config import DatabaseConfig
        env = DatabaseConfig.get_active_env()
        # Convert to short form
        env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
        env = env_map.get(env, env)
    except Exception as e:
        click.echo(f"Failed to determine environment: {e}")
        sys.exit(1)
    
    # Create migration
    click.echo(f"Creating migration: {message}")
    success, migration_file = create_migration(message, env, backup)
    
    if not success:
        click.echo("FAILED: Failed to create migration")
        sys.exit(1)
    
    # Ask to review migration if not auto-applying
    if migration_file and not apply:
        if click.confirm("Would you like to review the migration file?", default=True):
            # Open file with default program
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
        
        # Apply migration if requested
        if click.confirm("Apply migration now?", default=False):
            apply = True
    
    # Apply migration if requested
    if apply:
        click.echo("Applying migration...")
        apply_success = apply_migration(env)
        
        if apply_success:
            click.echo("SUCCESS: Migration applied successfully")
        else:
            click.echo("FAILED: Failed to apply migration")
            sys.exit(1)
    else:
        click.echo("Migration created but not applied")

@cli.command()
@click.option('--steps', type=int, default=1, help='Number of migrations to roll back')
@click.option('--backup/--no-backup', default=True, help='Create backup before rollback')
def rollback_db_migration(steps, backup):
    """Roll back migrations"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    try:
        from app.config.db_config import DatabaseConfig
        env = DatabaseConfig.get_active_env()
        # Convert to short form
        env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
        env = env_map.get(env, env)
    except Exception as e:
        click.echo(f"Failed to determine environment: {e}")
        sys.exit(1)
    
    # Get current migration history to confirm
    migrations = show_migrations()
    
    if len(migrations) < steps:
        click.echo(f"Cannot roll back {steps} migrations - only {len(migrations)} migrations exist")
        return
    
    # Show migrations to be rolled back
    target_migrations = migrations[:steps] if steps > 0 else []
    click.echo(f"Will roll back the following {steps} migration(s):")
    for migration in target_migrations:
        click.echo(f"{migration['id']}. {migration['description']} ({migration['filename']})")
    
    # Confirm rollback
    if not click.confirm(f"Roll back {steps} migration(s)?", default=False):
        click.echo("Rollback cancelled")
        return
    
    # Roll back migrations
    click.echo(f"Rolling back {steps} migration(s)")
    success = rollback_migration(env, steps)
    
    if success:
        click.echo("SUCCESS: Migration rollback completed successfully")
    else:
        click.echo("FAILED: Migration rollback failed")
        sys.exit(1)

@cli.command()
def show_all_migrations():
    """Show migration history"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    migrations = show_migrations()
    
    if not migrations:
        click.echo("No migrations found")
        return
    
    click.echo("\nMigration History:")
    click.echo("=====================================")
    click.echo(f"{'#':<3} {'Revision':<10} {'Description':<40} {'Created At':<20}")
    click.echo("-" * 80)
    
    for migration in migrations:
        click.echo(f"{migration['id']:<3} {migration['short_revision']:<10} {migration['description']:<40} {migration['created_at']:<20}")


# Database Copy Command

@cli.command()
@click.argument('source', type=click.Choice(['dev', 'test', 'prod']))
@click.argument('target', type=click.Choice(['dev', 'test', 'prod']))
@click.option('--schema-only', is_flag=True, help='Copy only schema (no data)')
@click.option('--data-only', is_flag=True, help='Copy only data (preserve schema)')
def copy_db(source, target, schema_only, data_only):
    """Copy database between environments"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    if source == target:
        click.echo("Source and target environments cannot be the same")
        return
    
    if schema_only and data_only:
        click.echo("Cannot use both --schema-only and --data-only")
        return
    
    if not click.confirm(f'Warning! This will copy database from {source} to {target}. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo(f'Starting database copy from {source} to {target}...')
    
    copy_options = []
    if schema_only:
        copy_options.append('schema only')
    elif data_only:
        copy_options.append('data only')
    
    if copy_options:
        click.echo(f'Copy options: {", ".join(copy_options)}')
    
    success = copy_database(source, target, schema_only, data_only)
    
    if success:
        click.echo(f"SUCCESS: Database copied successfully from {source} to {target}")
    else:
        click.echo(f"FAILED: Database copy from {source} to {target} failed")
        sys.exit(1)


# New Commands: switch-env and inspect-db
# These commands provide functionality from the deprecated switch_env.py and db_inspector.py modules

@cli.command()
@click.argument('env', type=click.Choice(['dev', 'test', 'prod']), required=False)
@click.option('--status', is_flag=True, help='Show current environment status')
def switch_env(env, status):
    """
    Switch application environment or show status
    
    This command replaces the functionality in the deprecated switch_env.py module.
    """
    # Try to import Environment module
    try:
        from app.core.environment import Environment, current_env
        
        # If --status flag is set, show current status
        if status:
            click.echo(f"Current environment: {current_env}")
            click.echo(f"Short name: {Environment.get_short_name(current_env)}")
            
            # Check environment file
            env_type_file = os.path.join(project_root, '.flask_env_type')
            if os.path.exists(env_type_file):
                with open(env_type_file, 'r') as f:
                    env_type = f.read().strip()
                click.echo(f"Environment type file (.flask_env_type): {env_type}")
            else:
                click.echo("Environment type file (.flask_env_type) not found")
            
            # Check .env file
            env_file = os.path.join(project_root, '.env')
            if os.path.exists(env_file):
                flask_env = None
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('FLASK_ENV='):
                            flask_env = line.strip().split('=', 1)[1]
                            break
                if flask_env:
                    click.echo(f"FLASK_ENV in .env file: {flask_env}")
                else:
                    click.echo("FLASK_ENV not found in .env file")
            else:
                click.echo(".env file not found")
            
            # Check environment variables
            click.echo(f"FLASK_ENV environment variable: {os.environ.get('FLASK_ENV', 'Not set')}")
            click.echo(f"SKINSPIRE_ENV environment variable: {os.environ.get('SKINSPIRE_ENV', 'Not set')}")
            
            # Display database URLs
            click.echo("\nDatabase URLs:")
            for env_name in ['development', 'testing', 'production']:
                try:
                    url = Environment.get_database_url_for_env(env_name)
                    # Mask password
                    url = mask_db_url(url)
                    click.echo(f"  {env_name}: {url}")
                except:
                    # Fall back to direct method if get_database_url_for_env is not available
                    try:
                        from app.config.db_config import DatabaseConfig
                        url = DatabaseConfig.get_database_url_for_env(env_name)
                        # Mask password
                        url = mask_db_url(url)
                        click.echo(f"  {env_name}: {url}")
                    except Exception as e:
                        click.echo(f"  {env_name}: Error accessing database URL: {e}")
                        
            return
            
        # Require env argument if not in status mode
        if not env:
            click.echo("Error: Missing required argument 'ENV'")
            click.echo("Usage: python scripts/manage_db.py switch-env [dev|test|prod]")
            click.echo("       python scripts/manage_db.py switch-env --status")
            sys.exit(1)
        
        # Switch environment using centralized Environment class
        new_env = Environment.set_environment(env)
        click.echo(f"Environment switched to: {new_env}")
        
        # Display database URL for new environment
        try:
            url = Environment.get_database_url()
            # Mask password
            url = mask_db_url(url)
            click.echo(f"Database URL: {url}")
        except:
            # Fall back to direct method if get_database_url is not available
            try:
                from app.config.db_config import DatabaseConfig
                url = DatabaseConfig.get_database_url()
                # Mask password
                url = mask_db_url(url)
                click.echo(f"Database URL: {url}")
            except Exception as e:
                click.echo(f"Error accessing database URL: {e}")
                
    except ImportError:
        # Fall back to old implementation if Environment module is not available
        # Map short environment names to full names
        env_map = {
            'dev': 'development',
            'test': 'testing',
            'prod': 'production'
        }
        
        # If --status flag is set, show current status
        if status:
            # Show current environment status
            logger.info("Current environment status:")
            
            # Check environment type file
            env_type_file = os.path.join(project_root, '.flask_env_type')
            if os.path.exists(env_type_file):
                with open(env_type_file, 'r') as f:
                    env_type = f.read().strip()
                click.echo(f"Environment type file (.flask_env_type): {env_type}")
            else:
                click.echo("Environment type file (.flask_env_type) not found")
            
            # Check FLASK_ENV in .env file
            env_file = os.path.join(project_root, '.env')
            if os.path.exists(env_file):
                flask_env = None
                with open(env_file, 'r') as f:
                    for line in f:
                        if line.startswith('FLASK_ENV='):
                            flask_env = line.strip().split('=', 1)[1]
                            break
                if flask_env:
                    click.echo(f"FLASK_ENV in .env file: {flask_env}")
                else:
                    click.echo("FLASK_ENV not found in .env file")
            else:
                click.echo(".env file not found")
            
            # Check environment variables
            click.echo(f"FLASK_ENV environment variable: {os.environ.get('FLASK_ENV', 'Not set')}")
            
            # Check centralized configuration if available
            try:
                from app.config.db_config import DatabaseConfig
                click.echo(f"Centralized configuration active environment: {DatabaseConfig.get_active_env()}")
                
                # Display database URLs
                click.echo("Database URLs:")
                for env_name in ['development', 'testing', 'production']:
                    url = DatabaseConfig.get_database_url_for_env(env_name)
                    # Mask password
                    url = mask_db_url(url)
                    click.echo(f"  {env_name}: {url}")
            except Exception as e:
                click.echo(f"Warning: Could not access centralized configuration: {e}")
            
            # Return without requiring env argument
            return
        
        # Require env argument if not in status mode
        if not env:
            click.echo("Error: Missing required argument 'ENV'")
            click.echo("Usage: python scripts/manage_db.py switch-env [dev|test|prod]")
            click.echo("       python scripts/manage_db.py switch-env --status")
            sys.exit(1)
        
        # Switch environment logic
        click.echo(f"Switching environment to: {env}")
        
        # Get the full environment name
        full_env = env_map.get(env, env)

        # Create or update the environment type file
        env_type_file = os.path.join(project_root, '.flask_env_type')
        with open(env_type_file, 'w') as f:
            f.write(env)
        
        click.echo(f"Environment switched to: {env}")
        
        # Update .env file to match - this is optional
        env_file = os.path.join(project_root, '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            updated_lines = []
            for line in lines:
                if line.startswith('FLASK_ENV='):
                    updated_lines.append(f'FLASK_ENV={full_env}\n')
                else:
                    updated_lines.append(line)
            
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            click.echo(f".env file updated with FLASK_ENV={full_env}")
        
        # Also set environment variable (for current process)
        os.environ['FLASK_ENV'] = full_env
        
        # Notify about the change to the centralized configuration
        try:
            from app.config.db_config import DatabaseConfig
            click.echo(f"Using centralized database configuration from db_config.py")
            click.echo(f"Active environment: {DatabaseConfig.get_active_env()}")
            db_url = DatabaseConfig.get_database_url()
            masked_url = mask_db_url(db_url)
            click.echo(f"Database URL: {masked_url}")
        except Exception as e:
            click.echo(f"Warning: Could not access database configuration: {e}")

@cli.command()
@click.argument('env', type=click.Choice(['dev', 'test', 'prod']), required=False)
@click.option('--tables', is_flag=True, help='List all tables')
@click.option('--schema', help='Filter by schema')
@click.option('--table', help='Show details for specific table')
@click.option('--triggers', is_flag=True, help='List all triggers')
@click.option('--functions', is_flag=True, help='List all functions')
def inspect_db(env, tables, schema, table, triggers, functions):
    """
    Inspect database structure in detail
    
    This command replaces the functionality in the deprecated db_inspector.py module.
    It provides comprehensive database inspection capabilities.
    """
    from sqlalchemy import create_engine, text, inspect
    import traceback
    
    # Determine environment
    if not env:
        try:
            from app.config.db_config import DatabaseConfig
            active_env = DatabaseConfig.get_active_env()
            # Convert to short form
            env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
            for short_env, full_env in env_map.items():
                if full_env == active_env:
                    env = short_env
                    break
            if not env:
                env = 'test'  # Default to test if mapping failed
        except Exception as e:
            click.echo(f"Failed to determine environment: {e}")
            env = 'test'  # Default to test environment
    
    # Get database URL
    try:
        # Try to use core functions first
        if get_db_config:
            db_config = get_db_config()
            full_env = {'dev': 'development', 'test': 'testing', 'prod': 'production'}.get(env, env)
            database_url = db_config.get_database_url_for_env(full_env)
        else:
            # Try to use DatabaseConfig directly
            try:
                from app.config.db_config import DatabaseConfig
                full_env = {'dev': 'development', 'test': 'testing', 'prod': 'production'}.get(env, env)
                database_url = DatabaseConfig.get_database_url_for_env(full_env)
            except Exception:
                # Fallback to environment variables
                if env == 'dev':
                    database_url = os.environ.get('DEV_DATABASE_URL')
                elif env == 'test':
                    database_url = os.environ.get('TEST_DATABASE_URL')
                elif env == 'prod':
                    database_url = os.environ.get('PROD_DATABASE_URL')
                else:
                    database_url = os.environ.get('DATABASE_URL')
                
                if not database_url:
                    click.echo(f"Error: Could not determine database URL for {env} environment")
                    sys.exit(1)
    except Exception as e:
        click.echo(f"Error getting database URL: {e}")
        sys.exit(1)
    
    # Mask password for display
    masked_url = mask_db_url(database_url)
    click.echo(f"Connecting to database: {masked_url}")
    
    try:
        click.echo("\n=== CONNECTING TO DATABASE ===")
        # Create engine and connect
        engine = create_engine(database_url)
        connection = engine.connect()
        inspector = inspect(engine)
        
        # General database overview
        if not any([tables, table, triggers, functions]):
            click.echo("\n=== DATABASE OVERVIEW ===")
            
            # Get schema information
            schemas = connection.execute(text(
                "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'"
            )).fetchall()
            
            click.echo(f"Found {len(schemas)} user-defined schemas:")
            for schema_row in schemas:
                schema_name = schema_row[0]
                # Get tables in this schema
                tables_in_schema = inspector.get_table_names(schema=schema_name)
                click.echo(f"  - {schema_name}: {len(tables_in_schema)} tables")
            
            # Get database version and size
            try:
                version = connection.execute(text("SELECT version()")).scalar()
                db_name = connection.execute(text("SELECT current_database()")).scalar()
                size_query = text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                           pg_database_size(current_database()) as raw_size
                """)
                size_result = connection.execute(size_query).fetchone()
                
                click.echo(f"\nDatabase: {db_name}")
                click.echo(f"Version: {version}")
                click.echo(f"Size: {size_result.size} ({size_result.raw_size} bytes)")
                
                # Get table count
                table_count = connection.execute(text("""
                    SELECT count(*) FROM pg_tables 
                    WHERE schemaname NOT LIKE 'pg_%' AND schemaname != 'information_schema'
                """)).scalar()
                
                click.echo(f"Total tables: {table_count}")
                
                # Get function count
                func_count = connection.execute(text("""
                    SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname != 'information_schema'
                """)).scalar()
                
                click.echo(f"Total functions: {func_count}")
                
                # Get trigger count
                trigger_count = connection.execute(text("""
                    SELECT count(*) FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname != 'information_schema'
                """)).scalar()
                
                click.echo(f"Total triggers: {trigger_count}")
                
            except Exception as e:
                click.echo(f"Error getting database details: {e}")
        
        # List all tables
        if tables:
            click.echo("\n=== TABLES ===")
            
            # If schema specified, limit to that schema
            if schema:
                schemas_to_check = [schema]
            else:
                # Get all user-defined schemas
                schemas_to_check = [row[0] for row in connection.execute(text(
                    "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'"
                )).fetchall()]
            
            # Iterate through schemas
            for schema_name in schemas_to_check:
                tables_in_schema = inspector.get_table_names(schema=schema_name)
                if tables_in_schema:
                    click.echo(f"\nSchema '{schema_name}' contains {len(tables_in_schema)} tables:")
                    
                    # Get approximate row counts for each table
                    for table_name in sorted(tables_in_schema):
                        try:
                            row_count = connection.execute(text(
                                f"SELECT count(*) FROM {schema_name}.{table_name}"
                            )).scalar()
                            
                            # Get table size
                            size_query = text(f"""
                                SELECT pg_size_pretty(pg_total_relation_size('{schema_name}.{table_name}')) as size
                            """)
                            size = connection.execute(size_query).scalar()
                            
                            click.echo(f"  - {table_name} ({row_count} rows, {size})")
                        except Exception:
                            click.echo(f"  - {table_name} (row count unavailable)")
        
        # Show detailed table information
        if table:
            table_to_find = table
            
            # If schema not specified, search for table in all schemas
            if not schema:
                # Find schema for the table
                schema_query = text("""
                    SELECT table_schema FROM information_schema.tables 
                    WHERE table_name = :table_name
                """)
                schema_result = connection.execute(schema_query, {"table_name": table_to_find}).fetchone()
                
                if schema_result:
                    schema = schema_result[0]
                else:
                    # Try case-insensitive search
                    schema_query = text("""
                        SELECT table_schema FROM information_schema.tables 
                        WHERE LOWER(table_name) = LOWER(:table_name)
                    """)
                    schema_result = connection.execute(schema_query, {"table_name": table_to_find}).fetchone()
                    
                    if schema_result:
                        schema = schema_result[0]
                        # Get the exact table name with correct case
                        table_name_query = text("""
                            SELECT table_name FROM information_schema.tables 
                            WHERE LOWER(table_name) = LOWER(:table_name) AND table_schema = :schema
                        """)
                        table_name_result = connection.execute(
                            table_name_query, 
                            {"table_name": table_to_find, "schema": schema}
                        ).fetchone()
                        table_to_find = table_name_result[0]
                    else:
                        click.echo(f"Error: Table '{table_to_find}' not found in any schema")
                        sys.exit(1)
            
            click.echo(f"\n=== TABLE DETAILS: {schema}.{table_to_find} ===")
            
            # Get column information
            columns = inspector.get_columns(table_to_find, schema=schema)
            click.echo(f"\nColumns ({len(columns)}):")
            for col in columns:
                nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                default = f" DEFAULT {col.get('default')}" if col.get('default') is not None else ""
                click.echo(f"  {col['name']} {col['type']} {nullable}{default}")
            
            # Get primary key
            pk = inspector.get_pk_constraint(table_to_find, schema=schema)
            if pk and pk.get('constrained_columns'):
                click.echo(f"\nPrimary Key: {', '.join(pk['constrained_columns'])}")
            
            # Get indexes
            indexes = inspector.get_indexes(table_to_find, schema=schema)
            if indexes:
                click.echo(f"\nIndexes ({len(indexes)}):")
                for idx in indexes:
                    unique = "UNIQUE " if idx.get('unique', False) else ""
                    click.echo(f"  {idx['name']}: {unique}({', '.join(idx['column_names'])})")
            
            # Get foreign keys
            fks = inspector.get_foreign_keys(table_to_find, schema=schema)
            if fks:
                click.echo(f"\nForeign Keys ({len(fks)}):")
                for fk in fks:
                    click.echo(f"  {fk.get('name')}: ({', '.join(fk['constrained_columns'])}) -> "
                             f"{fk.get('referred_schema', schema)}.{fk['referred_table']}({', '.join(fk['referred_columns'])})")
            
            # Get triggers
            triggers_query = text("""
                SELECT trigger_name, action_statement, event_manipulation, action_timing
                FROM information_schema.triggers
                WHERE event_object_schema = :schema AND event_object_table = :table
                ORDER BY action_timing, event_manipulation
            """)
            triggers = connection.execute(triggers_query, {"schema": schema, "table": table_to_find}).fetchall()
            
            if triggers:
                click.echo(f"\nTriggers ({len(triggers)}):")
                for trigger in triggers:
                    click.echo(f"  {trigger.trigger_name}: {trigger.action_timing} {trigger.event_manipulation}")
            
            # Get approximate row count
            try:
                row_count = connection.execute(text(
                    f"SELECT count(*) FROM {schema}.{table_to_find}"
                )).scalar()
                
                # Get table size
                size_query = text(f"""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('{schema}.{table_to_find}')) as total_size,
                        pg_size_pretty(pg_relation_size('{schema}.{table_to_find}')) as table_size,
                        pg_size_pretty(pg_indexes_size('{schema}.{table_to_find}')) as index_size
                """)
                size_result = connection.execute(size_query).fetchone()
                
                click.echo(f"\nStatistics:")
                click.echo(f"  Row count: {row_count}")
                click.echo(f"  Total size: {size_result.total_size}")
                click.echo(f"  Table size: {size_result.table_size}")
                click.echo(f"  Index size: {size_result.index_size}")
                
            except Exception as e:
                click.echo(f"Error getting table statistics: {e}")
        
        # List all triggers
        if triggers:
            click.echo("\n=== TRIGGERS ===")
            trigger_query = text("""
                SELECT 
                    trigger_schema, 
                    event_object_table, 
                    trigger_name,
                    event_manipulation,
                    action_timing
                FROM information_schema.triggers
                ORDER BY trigger_schema, event_object_table, trigger_name
            """)
            
            # Apply schema filter if specified
            if schema:
                trigger_query = text("""
                    SELECT 
                        trigger_schema, 
                        event_object_table, 
                        trigger_name,
                        event_manipulation,
                        action_timing
                    FROM information_schema.triggers
                    WHERE trigger_schema = :schema
                    ORDER BY trigger_schema, event_object_table, trigger_name
                """)
                trigger_results = connection.execute(trigger_query, {"schema": schema}).fetchall()
            else:
                trigger_results = connection.execute(trigger_query).fetchall()
            
            if not trigger_results:
                click.echo("No triggers found")
            else:
                click.echo(f"Found {len(trigger_results)} triggers:")
                
                # Group by schema.table
                table_triggers = {}
                for trigger_schema, table, trigger, event, timing in trigger_results:
                    key = f"{trigger_schema}.{table}"
                    if key not in table_triggers:
                        table_triggers[key] = []
                    table_triggers[key].append((trigger, event, timing))
                
                for table, trigger_list in sorted(table_triggers.items()):
                    click.echo(f"\n  {table} has {len(trigger_list)} triggers:")
                    for trigger, event, timing in sorted(trigger_list):
                        click.echo(f"    - {trigger} ({timing} {event})")
        
        # List all functions
        if functions:
            click.echo("\n=== FUNCTIONS ===")
            function_query = text("""
                SELECT n.nspname AS schema, p.proname AS function_name, 
                       pg_get_function_result(p.oid) AS result_type,
                       pg_get_function_arguments(p.oid) AS argument_types
                FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname != 'information_schema'
                ORDER BY n.nspname, p.proname
            """)
            
            # Apply schema filter if specified
            if schema:
                function_query = text("""
                    SELECT n.nspname AS schema, p.proname AS function_name, 
                           pg_get_function_result(p.oid) AS result_type,
                           pg_get_function_arguments(p.oid) AS argument_types
                    FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid
                    WHERE n.nspname = :schema
                    ORDER BY n.nspname, p.proname
                """)
                function_results = connection.execute(function_query, {"schema": schema}).fetchall()
            else:
                function_results = connection.execute(function_query).fetchall()
            
            if not function_results:
                click.echo("No functions found")
            else:
                click.echo(f"Found {len(function_results)} functions:")
                
                # Group by schema
                schema_funcs = {}
                for schema_name, func_name, result_type, arg_types in function_results:
                    if schema_name not in schema_funcs:
                        schema_funcs[schema_name] = []
                    schema_funcs[schema_name].append((func_name, result_type, arg_types))
                
                for schema_name, funcs in sorted(schema_funcs.items()):
                    click.echo(f"\nSchema '{schema_name}' contains {len(funcs)} functions:")
                    for func_name, result_type, arg_types in sorted(funcs):
                        click.echo(f"  - {func_name}({arg_types}) RETURNS {result_type}")
    
    except Exception as e:
        click.echo(f"Error inspecting database: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'connection' in locals():
            connection.close()

# Add the new commands

@cli.command()
@click.option('--force', is_flag=True, help='Force sync without confirmation')
def sync_dev_schema(force):
    """
    Sync models directly to database schema (DEVELOPMENT ONLY)
    
    WARNING: This command is for development use only and may result in data loss.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # Ensure we're in development environment
    try:
        from app.core.environment import Environment
        # Use the imported current_env variable directly instead of trying to call a method
        if current_env != 'development':
            click.echo(f"Current environment is {current_env}. Schema sync only allowed in development.")
            if not click.confirm("Do you want to switch to development environment?"):
                click.echo("Operation cancelled")
                return
            Environment.set_environment('dev')
    except ImportError:
        # Fallback check
        if os.environ.get('FLASK_ENV') not in (None, 'development'):
            click.echo("ERROR: Cannot use sync-dev-schema outside development environment")
            sys.exit(1)
    
    if not force and not click.confirm('Warning! This will modify your database schema to match models. Continue?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo('Syncing database schema with models...')
    from app.core.db_operations import sync_models_to_schema
    success = sync_models_to_schema('dev')
    
    if success:
        click.echo('SUCCESS: Database schema synced with models')
    else:
        click.echo('FAILED: Database schema sync failed')
        sys.exit(1)

@cli.command()
def detect_schema_changes():
    """Detect changes between models and database schema"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
        
    try:
        from app.core.db_operations.schema_sync import detect_model_changes
        
        click.echo('Detecting schema changes...')
        changes = detect_model_changes()
        
        if changes.get('has_changes', False):
            click.echo(f"\nDetected {len(changes['changes'])} changes:")
            
            # Handle both old and new format changes
            changes_list = changes.get('changes', [])
            if changes_list and isinstance(changes_list[0], dict):
                # New format - more detailed output
                for change in changes_list:
                    change_type = change['type'].replace('_', ' ').title()
                    auto_apply_note = "" if change.get('auto_apply', True) else " (will not be auto-applied)"
                    
                    if 'column' in change:
                        click.echo(f"- {change_type}: {change['table']}.{change['column']} - {change['details']}{auto_apply_note}")
                    else:
                        click.echo(f"- {change_type}: {change['table']} - {change['details']}{auto_apply_note}")
            else:
                # Old format - simple output
                for change in changes_list:
                    click.echo(f"- {change}")
            
            click.echo("\nTo create a migration with these changes:")
            click.echo("  python scripts/manage_db.py create-model-migration -m \"Your message here\"")
            
            click.echo("\nTo directly apply these changes in development:")
            click.echo("  python scripts/manage_db.py sync-models-to-db")
        else:
            if 'error' in changes:
                click.echo(f"Error: {changes['error']}")
                sys.exit(1)
            else:
                click.echo("No schema changes detected")
    except Exception as e:
        click.echo(f"Error detecting schema changes: {e}")
        sys.exit(1)

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
def prepare_migration(message):
    """
    Prepare migration files from development model changes
    
    This command detects changes made to models during development
    and creates proper migration files.
    """
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    # Detect model changes first
    click.echo("Detecting model changes...")
    from app.core.db_operations import detect_model_changes
    changes = detect_model_changes()
    
    if not changes['has_changes']:
        click.echo("No model changes detected")
        return
    
    # Show detected changes
    click.echo("\nDetected changes:")
    for change in changes['changes']:
        click.echo(f"- {change}")
    
    # Create migration
    if click.confirm("Create migration file with these changes?"):
        try:
            from app.core.db_operations import create_migration
            success, migration_file = create_migration(message, 'dev', backup=True)
            
            if success:
                click.echo(f"SUCCESS: Migration created at {migration_file}")
                
                if click.confirm("Apply migration to development database?"):
                    from app.core.db_operations import apply_migration
                    apply_success = apply_migration('dev')
                    if apply_success:
                        click.echo("SUCCESS: Migration applied to development database")
                    else:
                        click.echo("FAILED: Migration application failed")
            else:
                click.echo("FAILED: Migration creation failed")
                sys.exit(1)
        except Exception as e:
            if "Target database is not up to date" in str(e):
                click.echo("ERROR: Target database is not up to date. You need to apply existing migrations first.")
                click.echo("Run: python scripts/manage_db.py apply-db-migration")
            else:
                click.echo(f"ERROR: {str(e)}")
            sys.exit(1)

@cli.command()
@click.option('--mode', type=click.Choice(['stamp', 'trace-reset']), default='stamp', 
              help='stamp: Mark all migrations as applied, trace-reset: Clear migration tracking')
def reset_migration_tracking(mode):
    """
    Reset Alembic migration tracking

    - stamp: Marks all migrations as applied without changing database
    - trace-reset: Clears migration tracking table (alembic_version)
    """
    try:
        from alembic.config import Config
        from alembic import command
        from sqlalchemy import create_engine, text
        from app.config.db_config import DatabaseConfig

        # Get current database URL
        db_url = DatabaseConfig.get_database_url()
        
        # Find migrations directory
        project_root = Path(__file__).parent.parent
        migrations_dir = project_root / 'migrations'
        alembic_ini = migrations_dir / 'alembic.ini'

        # Validate paths
        if not alembic_ini.exists():
            click.echo(f"Error: Alembic configuration not found at {alembic_ini}")
            sys.exit(1)

        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini))

        # Manually set script location if not in config
        if not alembic_cfg.get_main_option('script_location'):
            alembic_cfg.set_main_option('script_location', str(migrations_dir))

        if mode == 'stamp':
            # Stamp migrations to base
            click.echo("Performing stamp reset - marking all migrations as applied...")
            command.stamp(alembic_cfg, "head")
            click.echo("Stamp reset completed: All migrations marked as applied")

        elif mode == 'trace-reset':
            # Reset migration tracking table
            click.echo("Performing migration trace reset - clearing migration tracking...")
            
            # Create engine directly
            engine = create_engine(db_url)
            
            with engine.connect() as connection:
                # Disable foreign key constraints
                connection.execute(text('SET session_replication_role = replica;'))
                
                # Delete alembic_version table
                connection.execute(text('DELETE FROM alembic_version;'))
                
                # Re-enable foreign key constraints
                connection.execute(text('SET session_replication_role = default;'))
                
                click.echo("Migration trace reset completed: Tracking table cleared")

    except Exception as e:
        click.echo(f"Error during migration tracking reset: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.option('--force', is_flag=True, help='Force cleanup even with only one migration file')
def clean_migration_files(force):
    """
    Clean up old migration files
    
    By default, does not clean if only one migration file exists.
    Use --force to override.
    """
    # Find migrations directory
    project_root = Path(__file__).parent.parent
    migrations_dir = project_root / 'migrations' / 'versions'
    
    if not migrations_dir.exists():
        click.echo(f"Migration versions directory not found: {migrations_dir}")
        sys.exit(1)
    
    # Find migration Python files, excluding __init__.py and __pycache__
    migration_files = [
        f for f in migrations_dir.glob('*.py') 
        if f.stem != '__init__' and 
           not f.stem.startswith('__') and 
           f.is_file()
    ]
    
    # If only one migration file and no force flag
    if len(migration_files) <= 1 and not force:
        click.echo("Only one migration file exists. Use --force to clean.")
        for file in migration_files:
            click.echo(f"Current migration file: {file.name}")
        return
    
    # Sort by modification time
    migration_files.sort(key=os.path.getmtime)
    
    # Keep the latest file if multiple exist
    if len(migration_files) > 1:
        latest_file = migration_files[-1]
        migration_files = migration_files[:-1]
    else:
        latest_file = None
    
    # Remove old migration files
    click.echo("Cleaning migration files:")
    for file_path in migration_files:
        click.echo(f"  Deleting: {file_path}")
        os.unlink(file_path)
    
    if latest_file:
        click.echo(f"Kept latest migration: {latest_file}")
    else:
        click.echo("No migration files to clean")
    
    click.echo("Migration file cleanup completed")

@cli.command()
@click.argument('revision', default='head')
@click.option('--force', is_flag=True, help='Force stamp without confirmation')
def stamp_migrations(revision, force):
    """
    Stamp Alembic migrations to a specific revision

    REVISION: Revision to stamp to (default: 'head')
    Use 'base' to reset all migrations
    Use a specific revision hash to stamp to that point
    """
    try:
        from alembic.config import Config
        from alembic import command
        
        # Get the app and ensure we're in the app context
        app = get_app()
        with app.app_context():
            from app.config.db_config import DatabaseConfig

            # Get current database URL
            db_url = DatabaseConfig.get_database_url()
            
            # Find migrations directory
            project_root = Path(__file__).parent.parent
            migrations_dir = project_root / 'migrations'
            alembic_ini = migrations_dir / 'alembic.ini'

            # Validate paths
            if not alembic_ini.exists():
                click.echo(f"Error: Alembic configuration not found at {alembic_ini}")
                sys.exit(1)

            # Create Alembic config
            alembic_cfg = Config(str(alembic_ini))

            # Manually set script location if not in config
            if not alembic_cfg.get_main_option('script_location'):
                alembic_cfg.set_main_option('script_location', str(migrations_dir))

            # Confirmation for potentially destructive operations
            if not force:
                if revision == 'base':
                    confirm = click.confirm("WARNING: This will mark ALL migrations as not applied. Are you sure?")
                elif revision == 'head':
                    confirm = click.confirm("This will mark ALL migrations as applied. Proceed?")
                else:
                    confirm = click.confirm(f"Stamp migrations to revision {revision}. Proceed?")
                
                if not confirm:
                    click.echo("Operation cancelled")
                    return

            # Perform stamp operation
            click.echo(f"Stamping migrations to: {revision}")
            command.stamp(alembic_cfg, revision)
            
            click.echo(f"SUCCESS: Migrations stamped to {revision}")

    except Exception as e:
        click.echo(f"Error during migration stamping: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
@click.option('--apply', is_flag=True, help='Apply migration immediately')
@click.option('--backup/--no-backup', default=True, help='Create backup before generating')
def create_model_migration(message, apply, backup):
    """Create migration based on model changes"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    try:
        from app.core.db_operations.schema_sync import create_model_based_migration
        from app.core.db_operations.migration import apply_migration
        
        # Determine environment
        try:
            from app.config.db_config import DatabaseConfig
            env = DatabaseConfig.get_active_env()
            short_env = {'development': 'dev', 'testing': 'test', 'production': 'prod'}.get(env, 'dev')
        except:
            short_env = 'dev'
        
        click.echo(f'Creating model-based migration: {message}')
        success, file_path = create_model_based_migration(message, short_env)
        
        if success:
            if file_path:
                click.echo(f"SUCCESS: Migration created at {file_path}")
                
                # Offer to open the file
                if not apply and click.confirm("Would you like to review the migration file?", default=True):
                    # Open file with default program
                    try:
                        import os
                        os.startfile(file_path)
                    except AttributeError:
                        # On non-Windows platforms
                        if sys.platform.startswith('darwin'):
                            import subprocess
                            subprocess.run(['open', str(file_path)])
                        else:
                            import subprocess
                            subprocess.run(['xdg-open', str(file_path)])
                
                if apply:
                    click.echo("Applying migration...")
                    apply_success = apply_migration(short_env)
                    
                    if apply_success:
                        click.echo("SUCCESS: Migration applied")
                    else:
                        click.echo("FAILED: Could not apply migration")
                        sys.exit(1)
            else:
                click.echo("No schema changes detected, no migration created")
        else:
            click.echo("FAILED: Could not create migration")
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error creating migration: {e}")
        sys.exit(1)

@cli.command()
@click.option('--env', type=click.Choice(['dev', 'test', 'prod']), default=None, 
              help='Target environment (default: current environment)')
def apply_db_migration(env):
    """Apply pending database migrations"""
    # If environment specified, switch to it
    if env:
        try:
            from app.core.environment import Environment
            Environment.set_environment(env)
            click.echo(f"Switched to environment: {env}")
        except ImportError:
            # Fall back to manual environment setting
            env_map = {'dev': 'development', 'test': 'testing', 'prod': 'production'}
            full_env = env_map.get(env, env)
            os.environ['FLASK_ENV'] = full_env
            click.echo(f"Manually set environment to: {full_env}")
    
    try:
        # Set environment variables
        os.environ['FLASK_APP'] = 'app:create_app'
        
        app = get_app()
        with app.app_context():
            # Check for multiple heads
            from flask_migrate import Migrate
            from alembic.script import ScriptDirectory
            
            # Initialize Migrate
            migrate = Migrate(app, get_db())
            config = migrate.get_config()
            script = ScriptDirectory.from_config(config)
            
            if len(script.get_heads()) > 1:
                click.echo("Multiple migration heads detected. Attempting to merge...")
                
                # Execute merge command
                result = subprocess.run(
                    [sys.executable, '-m', 'flask', 'db', 'merge', 'heads', '-m', 'Merge migration heads'],
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                click.echo("Heads merged successfully, now upgrading...")
            
            # Run the upgrade command
            result = subprocess.run(
                [sys.executable, '-m', 'flask', 'db', 'upgrade'],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Display output
            for line in result.stdout.splitlines():
                click.echo(line)
                
            click.echo("Migrations applied successfully")
            return True
            
    except subprocess.CalledProcessError as e:
        click.echo(f"Error applying migrations: {e}")
        if e.stdout:
            click.echo(f"Output: {e.stdout}")
        if e.stderr:
            click.echo(f"Error: {e.stderr}")
        return False
    except Exception as e:
        click.echo(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

@cli.command()
@click.option('--force', is_flag=True, help='Skip confirmation')
@click.option('--allow-drops', is_flag=True, help='Allow dropping columns/tables not in models')
def sync_models_to_db(force, allow_drops):
    """Synchronize database with models (DEVELOPMENT ONLY)"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not properly imported")
        sys.exit(1)
    
    try:
        from app.core.db_operations.schema_sync import sync_models_to_schema
        
        # Ensure we're in development environment
        try:
            from app.core.environment import Environment, current_env
            if current_env != 'development':
                click.echo(f"Current environment is {current_env}. Schema sync only allowed in development.")
                if not force and not click.confirm("Continue anyway?", default=False):
                    click.echo("Operation cancelled")
                    return
        except ImportError:
            # Fallback check
            if os.environ.get('FLASK_ENV') not in (None, 'development'):
                click.echo("WARNING: Not in development environment. Schema sync is intended for development only.")
                if not force and not click.confirm("Continue anyway?", default=False):
                    click.echo("Operation cancelled")
                    return
        
        # Warn about potential data loss if allowing drops
        if allow_drops:
            click.echo("WARNING: --allow-drops flag is set. This may result in DATA LOSS!")
            click.echo("Tables and columns not present in your models will be DROPPED!")
            
            if not force and not click.confirm("Are you ABSOLUTELY SURE you want to continue?", default=False):
                click.echo("Operation cancelled")
                return
        
        if not force:
            click.echo("WARNING: This will modify your database schema directly.")
            click.echo("This should only be used in development.")
            if not click.confirm("Continue?", default=False):
                click.echo("Operation cancelled")
                return
        
        click.echo("Synchronizing models to database...")
        success = sync_models_to_schema('dev', backup=True, allow_drops=allow_drops)
        
        if success:
            click.echo("SUCCESS: Database schema synced with models")
        else:
            click.echo("FAILED: Database schema sync failed")
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error syncing models to database: {e}")
        sys.exit(1)

@cli.command()
@click.option('--message', '-m', default='Merge migration heads', help='Merge message')
def merge_migration_heads(message):
    """
    Merge multiple migration heads
    
    This command helps resolve situations where multiple migration heads exist
    """
    try:
        from alembic.config import Config
        from alembic import command
        from sqlalchemy import create_engine, text
        from app.config.db_config import DatabaseConfig

        # Get current database URL
        db_url = DatabaseConfig.get_database_url()
        
        # Find migrations directory
        project_root = Path(__file__).parent.parent
        migrations_dir = project_root / 'migrations'
        alembic_ini = migrations_dir / 'alembic.ini'

        # Validate paths
        if not alembic_ini.exists():
            click.echo(f"Error: Alembic configuration not found at {alembic_ini}")
            sys.exit(1)

        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini))

        # Manually set script location if not in config
        if not alembic_cfg.get_main_option('script_location'):
            alembic_cfg.set_main_option('script_location', str(migrations_dir))

        # Get current heads
        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)
        heads = list(script.get_heads())

        click.echo(f"Detected {len(heads)} migration heads:")
        for head in heads:
            click.echo(f"  - {head}")

        if len(heads) <= 1:
            click.echo("No merge needed. Only one head exists.")
            return

        # Prepare revision flags
        revision_flags = heads

        # Perform merge
        click.echo(f"Merging migration heads with message: {message}")
        
        # Use Alembic's merge command
        command.merge(
            alembic_cfg, 
            revision_flags, 
            message=message
        )

        click.echo("SUCCESS: Migration heads merged successfully")

    except Exception as e:
        click.echo(f"Error during migration head merge: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

@cli.command()
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
def reset_migrations_completely(force):
    """
    Complete reset of all migrations - both files and tracking
    
    This performs a more thorough reset than reset-migration-tracking:
    1. Removes all migration files (except __init__.py)
    2. Directly deletes alembic_version table records
    3. Doesn't require app context
    
    USE WITH CAUTION - ensure you have database backups
    """
    if not force:
        click.echo("WARNING: This will completely remove ALL migration history!")
        click.echo("This includes deleting migration files and clearing the tracking table.")
        if not click.confirm("Are you ABSOLUTELY sure you want to continue?", default=False):
            click.echo("Operation cancelled")
            return
    
    # Step 1: Delete migration files
    migrations_dir = Path(__file__).parent.parent / 'migrations' / 'versions'
    if migrations_dir.exists():
        click.echo("Removing migration files...")
        count = 0
        for file in migrations_dir.glob('*.py'):
            # Keep __init__.py
            if file.name != '__init__.py':
                file.unlink()
                count += 1
        click.echo(f"Removed {count} migration files")
    else:
        click.echo("No migrations directory found at: " + str(migrations_dir))
    
    # Step 2: Clear alembic_version table
    try:
        # Get database URL directly - not using application context
        try:
            from app.config.db_config import DatabaseConfig
            db_url = DatabaseConfig.get_database_url()
        except ImportError:
            # Fallback if config module not available
            if ENVIRONMENT_MODULE_AVAILABLE:
                from app.core.environment import Environment
                db_url = Environment.get_database_url()
            else:
                # Last resort - use environment variable
                env = os.environ.get('FLASK_ENV', 'development')
                if env == 'development':
                    db_url = os.environ.get('DEV_DATABASE_URL')
                elif env == 'testing':
                    db_url = os.environ.get('TEST_DATABASE_URL')
                elif env == 'production':
                    db_url = os.environ.get('PROD_DATABASE_URL')
                else:
                    db_url = os.environ.get('DATABASE_URL')
        
        if not db_url:
            click.echo("Error: Could not determine database URL")
            return
        
        # Clear alembic_version table directly with SQLAlchemy
        from sqlalchemy import create_engine, text
        click.echo("Clearing migration tracking table...")
        engine = create_engine(db_url)
        with engine.connect() as connection:
            # Check if table exists first
            try:
                connection.execute(text("DELETE FROM alembic_version"))
                connection.commit()
                click.echo("Successfully cleared migration tracking table")
            except Exception as e:
                click.echo(f"Note: Could not clear alembic_version table: {e}")
                click.echo("This is normal if the table doesn't exist yet.")
    
    except Exception as e:
        click.echo(f"Error during database operation: {e}")
        import traceback
        traceback.print_exc()
    
    click.echo("\nMigration system has been completely reset.")
    click.echo("You can now add new migration files and apply them.")

@cli.command()
def debug_migration_config():
    """
    Debug migration and database configuration
    
    Provides detailed information about current migration setup,
    database configuration, and potential issues.
    """
    try:
        # Utilize existing environment and configuration modules
        from app.config.db_config import DatabaseConfig
        
        # Reuse existing mask_db_url function for sensitive information
        click.echo("Database Configuration:")
        click.echo(f"Active Environment: {DatabaseConfig.get_active_env()}")
        
        # Mask database URL to protect sensitive information
        db_url = DatabaseConfig.get_database_url()
        masked_url = mask_db_url(db_url)
        click.echo(f"Database URL: {masked_url}")
        
        # Get the app with existing get_app() method
        app = get_app()
        
        with app.app_context():
            # Import existing migrate and SQLAlchemy db 
            from flask_migrate import Migrate
            from alembic.script import ScriptDirectory
            from alembic.config import Config
            
            # Reuse existing database instance
            db = get_db()
            
            # Set up migration using existing methods
            migrate = Migrate(app, db)
            config = migrate.get_config()
            script = ScriptDirectory.from_config(config)

            # Check migration heads
            heads = list(script.get_heads())
            click.echo(f"\nMigration Heads: {len(heads)}")
            for head in heads:
                click.echo(f"  - {head}")

            # Find migrations directory using existing project structure
            migrations_dir = Path(__file__).parent.parent / 'migrations'
            
            # Check migration files
            click.echo("\nMigration Files:")
            migration_files = list(migrations_dir.glob('versions/*.py'))
            if not migration_files:
                click.echo("  No migration files found!")
            else:
                for file in migration_files:
                    click.echo(f"  - {file.name}")

            # Additional checks for alembic_version table
            try:
                from sqlalchemy import text
                engine = get_db().engine
                with engine.connect() as connection:
                    result = connection.execute(text("SELECT * FROM alembic_version")).fetchall()
                    click.echo(f"\nAlembic Version Table:")
                    if not result:
                        click.echo("  No tracked migrations")
                    else:
                        for row in result:
                            click.echo(f"  Tracked Version: {row[0]}")
            except Exception as e:
                click.echo(f"  Error checking alembic_version table: {e}")

    except Exception as e:
        # Comprehensive error handling
        click.echo(f"Error during migration configuration debug: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

@cli.command()
def init_migrations():
    """Initialize database migrations"""
    try:
        import subprocess
        import sys
        
        # Run db init using subprocess
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'init'],
            check=True,
            capture_output=True,
            text=True
        )
        
        click.echo("SUCCESS: Migration environment initialized")
    except subprocess.CalledProcessError as e:
        click.echo(f"FAILED: Migration initialization failed")
        click.echo(f"Error: {e.stderr}")
        sys.exit(1)

if __name__ == '__main__':
    cli()
