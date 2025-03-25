#!/usr/bin/env python
# scripts/manage_db_standalone.py

import os
import sys
import click
from pathlib import Path
import subprocess
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set environment variables for testing
if 'FLASK_ENV' not in os.environ:
    os.environ['FLASK_ENV'] = 'testing'
if not os.environ.get('TEST_DATABASE_URL'):
    os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'

# Import core database operations
try:
    from app.core.db_operations import (
        normalize_env_name,
        backup_database,
        list_backups,
        restore_database,
        create_migration,
        apply_migration,
        rollback_migration,
        show_migrations,
        copy_database,
        apply_base_triggers, 
        apply_triggers,
        apply_all_schema_triggers,
        verify_triggers,
        check_db,
        reset_db,
        init_db,
        drop_all_tables
    )
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    click.echo(f"Warning: Could not import core modules: {e}")
    CORE_MODULES_AVAILABLE = False

@click.group()
def cli():
    """Database management commands"""
    pass

# ----- DATABASE CONNECTION COMMANDS -----

@cli.command()
def check_database():
    """Check database connection"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
    
    click.echo("Checking database connection...")
    results = check_db()
    
    if results.get('success'):
        click.echo("✓ Database connection successful")
        click.echo(f"Connected to: {results.get('environment')} environment")
        
        # If there are tables, list them
        if results.get('tables'):
            click.echo(f"Found {len(results.get('tables'))} tables in database:")
            for table in results.get('tables')[:10]:  # Show first 10 tables
                click.echo(f"  - {table}")
            if len(results.get('tables')) > 10:
                click.echo(f"  ... and {len(results.get('tables')) - 10} more tables")
    else:
        click.echo("✗ Database connection failed")
        if results.get('errors'):
            for error in results.get('errors'):
                click.echo(f"  Error: {error}")
        sys.exit(1)

# ----- BACKUP AND RESTORE COMMANDS -----

@cli.command()
def list_all_backups():
    """List available database backups"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
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
@click.option('--env', default='test', help='Environment to backup')
def create_backup(env):
    """Create database backup"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
    
    click.echo(f"Creating backup of {env} database...")
    success, backup_path = backup_database(env)
    
    if success:
        click.echo(f"✓ Backup created successfully: {backup_path}")
    else:
        click.echo("✗ Backup failed")
        sys.exit(1)

@cli.command()
@click.argument('file', required=False)
@click.option('--env', default='test', help='Environment to restore to')
def restore_backup(file, env):
    """Restore database from backup"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
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
    
    if not click.confirm(f'⚠️ This will restore the {env} database from {file}. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
    
    click.echo(f"Restoring {env} database from {file}...")
    success = restore_database(env, file)
    
    if success:
        click.echo("✓ Database restored successfully")
    else:
        click.echo("✗ Database restore failed")
        sys.exit(1)

# ----- DATABASE COPY COMMANDS -----

@cli.command()
@click.argument('source', type=click.Choice(['dev', 'test', 'prod']))
@click.argument('target', type=click.Choice(['dev', 'test', 'prod']))
@click.option('--schema-only', is_flag=True, help='Copy only schema (no data)')
@click.option('--data-only', is_flag=True, help='Copy only data (preserve schema)')
def copy_db(source, target, schema_only, data_only):
    """Copy database between environments"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
    
    if source == target:
        click.echo("Source and target environments cannot be the same")
        return
    
    if schema_only and data_only:
        click.echo("Cannot use both --schema-only and --data-only")
        return
    
    if not click.confirm(f'⚠️ This will copy database from {source} to {target}. Are you sure?', default=False):
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
        click.echo(f"✓ Database copied successfully from {source} to {target}")
    else:
        click.echo(f"✗ Database copy from {source} to {target} failed")
        sys.exit(1)

# ----- TRIGGER MANAGEMENT COMMANDS -----

@cli.command()
def apply_base_db_triggers():
    """Apply only base database trigger functionality"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
        
    click.echo('Starting to apply base trigger functions...')
    success = apply_base_triggers()
    
    if success:
        click.echo('✓ Base trigger functions applied successfully')
    else:
        click.echo('✗ Failed to apply base trigger functions')
        sys.exit(1)

@cli.command()
def apply_db_triggers():
    """Apply all database triggers and functions"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
        
    click.echo('Starting to apply database triggers and functions...')
    success = apply_triggers()
    
    if success:
        click.echo('✓ Database triggers applied successfully')
    else:
        click.echo('✗ Failed to apply database triggers')
        sys.exit(1)

@cli.command()
def apply_all_db_schema_triggers():
    """Apply triggers to all schemas"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
        
    click.echo('Starting to apply triggers to all schemas...')
    success = apply_all_schema_triggers()
    
    if success:
        click.echo('✓ Applied triggers to all schemas successfully')
    else:
        click.echo('✗ Failed to apply triggers to all schemas')
        sys.exit(1)

@cli.command()
def verify_db_triggers():
    """Verify trigger installation"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
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
        click.echo('✗ Trigger verification failed')
        sys.exit(1)

# ----- MIGRATION COMMANDS -----

@cli.command()
def show_db_migrations():
    """Show migration history"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
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

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
@click.option('--backup/--no-backup', default=True, help='Create backup before migration')
@click.option('--apply', is_flag=True, help='Automatically apply migration')
@click.option('--env', default='test', help='Environment to create migration for')
def create_db_migration(message, backup, apply, env):
    """Create database migration"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
    
    # Create migration
    click.echo(f"Creating migration for {env} environment: {message}")
    success, migration_file = create_migration(message, env, backup)
    
    if not success:
        click.echo("✗ Failed to create migration")
        sys.exit(1)
    
    # Ask to review migration if not auto-applying
    if migration_file and not apply:
        if click.confirm("Would you like to review the migration file?", default=True):
            # Open file with default program
            try:
                import os
                os.startfile(migration_file)
            except AttributeError:
                # On non-Windows platforms
                if sys.platform.startswith('darwin'):
                    subprocess.run(['open', migration_file])
                else:
                    subprocess.run(['xdg-open', migration_file])
        
        # Apply migration if requested
        if click.confirm("Apply migration now?", default=False):
            apply = True
    
    # Apply migration if requested
    if apply:
        click.echo("Applying migration...")
        apply_success = apply_migration(env)
        
        if apply_success:
            click.echo("✓ Migration applied successfully")
        else:
            click.echo("✗ Failed to apply migration")
            sys.exit(1)
    else:
        click.echo("Migration created but not applied")

@cli.command()
@click.option('--steps', type=int, default=1, help='Number of migrations to roll back')
@click.option('--backup/--no-backup', default=True, help='Create backup before rollback')
@click.option('--env', default='test', help='Environment to roll back')
def rollback_db_migration(steps, backup, env):
    """Roll back migrations"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
    
    # Get current migration history to confirm
    migrations = show_migrations()
    
    if len(migrations) < steps:
        click.echo(f"Cannot roll back {steps} migrations - only {len(migrations)} migrations exist")
        return
    
    # Show migrations to be rolled back
    target_migrations = migrations[:steps]
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
        click.echo("✓ Migration rollback completed successfully")
    else:
        click.echo("✗ Migration rollback failed")
        sys.exit(1)

# ----- MAINTENANCE COMMANDS -----

@cli.command()
def drop_all_db_tables():
    """Drop all tables in correct order"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
        
    if not click.confirm('⚠️ This will DROP ALL TABLES. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
        
    click.echo('Dropping all tables...')
    success = drop_all_tables()
    
    if success:
        click.echo('✓ All tables dropped successfully')
    else:
        click.echo('✗ Failed to drop all tables')
        sys.exit(1)

@cli.command()
def initialize_db():
    """Initialize database tables without migrations"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
        
    click.echo('Starting database initialization...')
    success = init_db()
    
    if success:
        click.echo('✓ Database initialization completed successfully')
    else:
        click.echo('✗ Database initialization failed')
        sys.exit(1)

@cli.command()
def reset_database():
    """Remove existing migrations and reinitialize"""
    if not CORE_MODULES_AVAILABLE:
        click.echo("Error: Core modules not available")
        sys.exit(1)
        
    if not click.confirm('⚠️ This will reset the database and migrations. Are you sure?', default=False):
        click.echo('Operation cancelled')
        return
        
    click.echo('Starting database reset...')
    success = reset_db()
    
    if success:
        click.echo('✓ Database reset completed successfully')
    else:
        click.echo('✗ Database reset failed')
        sys.exit(1)

if __name__ == '__main__':
    cli()