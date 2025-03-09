#!/usr/bin/env python
# skinspire_v2/scripts/verify_triggers.py
# python scripts/verify_triggers.py
# python scripts/verify_triggers.py verify-all-triggers
# python scripts/verify_triggers.py verify-trigger-functions
# python scripts/manage_db.py apply-triggers

import os
import sys
import click
from flask.cli import with_appcontext
from sqlalchemy import text
from pathlib import Path
from tabulate import tabulate

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app import create_app, db
except ImportError as e:
    print(f"Error importing app module: {e}")
    sys.exit(1)

# Global app instance
_app = None

def get_app():
    global _app
    if _app is None:
        _app = create_app()
    return _app

def get_db():
    return db

@click.group()
def cli():
    """Trigger verification commands"""
    pass

@cli.command()
@with_appcontext
def verify_all_triggers():
    """Verify all expected triggers exist on tables"""
    app = get_app()
    click.echo('Starting trigger verification...')
    
    with app.app_context():
        db = get_db()
        
        # Get all schemas
        schemas = db.session.execute(text(
            "SELECT nspname FROM pg_namespace "
            "WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'"
        )).fetchall()
        
        all_tables = []
        
        # Get all tables for each schema
        for schema in schemas:
            schema_name = schema[0]
            tables = db.session.execute(text(
                f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema_name}'"
            )).fetchall()
            
            for table in tables:
                table_name = table[0]
                all_tables.append((schema_name, table_name))
        
        click.echo(f"Found {len(all_tables)} tables across {len(schemas)} schemas")
        
        # Required triggers to check for
        required_triggers = ['update_timestamp', 'track_user_changes']
        
        # Track missing triggers
        missing_triggers = []
        
        # Check each table for required triggers
        for schema, table in all_tables:
            triggers = db.session.execute(text(
                f"SELECT trigger_name FROM information_schema.triggers "
                f"WHERE event_object_schema = '{schema}' AND event_object_table = '{table}'"
            )).fetchall()
            
            trigger_names = [t[0] for t in triggers]
            missing = []
            
            for expected in required_triggers:
                if expected not in trigger_names:
                    missing.append(expected)
            
            if missing:
                missing_triggers.append((schema, table, ', '.join(missing)))
        
        # Display results
        if missing_triggers:
            click.echo(f"\n⚠️ Found {len(missing_triggers)} tables with missing triggers:\n")
            
            # Format as table
            headers = ["Schema", "Table", "Missing Triggers"]
            click.echo(tabulate(missing_triggers, headers=headers, tablefmt="grid"))
            
            # Suggestions for fixing
            click.echo("\nTo fix these missing triggers, run:\n")
            click.echo("  python scripts/manage_db.py apply-all-schema-triggers")
        else:
            click.echo("\n✓ All tables have the required triggers!")
        
        # Count total triggers
        trigger_count = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.triggers"
        )).scalar()
        
        click.echo(f"\nTotal triggers in database: {trigger_count}")

@cli.command()
@with_appcontext
def verify_trigger_functions():
    """Verify all required trigger functions exist"""
    app = get_app()
    click.echo('Verifying trigger functions...')
    
    with app.app_context():
        db = get_db()
        
        # List of expected trigger functions
        expected_functions = [
            'update_timestamp',
            'track_user_changes',
            'drop_existing_triggers',
            'create_audit_triggers',
            'update_failed_login_attempts',
            'update_on_successful_login',
            'check_account_lockout',
            'update_login_history_on_logout',
            'check_session_expiration',
            'hash_password',
            'manage_session_limits',
            'validate_role_assignment',
            'cleanup_user_roles',
            'flag_fields_for_encryption',
            'create_audit_triggers_all_schemas'
        ]
        
        # Get actual functions
        functions = db.session.execute(text(
            "SELECT n.nspname AS schema_name, p.proname AS function_name "
            "FROM pg_proc p "
            "JOIN pg_namespace n ON p.pronamespace = n.oid "
            "WHERE p.proname IN ('" + "','".join(expected_functions) + "')"
        )).fetchall()
        
        found_functions = [f[1] for f in functions]
        
        # Check for missing functions
        missing = [f for f in expected_functions if f not in found_functions]
        
        if missing:
            click.echo(f"\n⚠️ Missing {len(missing)} trigger functions:\n")
            for func in missing:
                click.echo(f"  - {func}")
            
            # Suggestions for fixing
            click.echo("\nTo fix these missing functions, run:\n")
            click.echo("  python scripts/manage_db.py apply-triggers")
        else:
            click.echo("\n✓ All required trigger functions exist!")
            
            # Display found functions
            click.echo("\nFound trigger functions:")
            headers = ["Schema", "Function"]
            click.echo(tabulate(functions, headers=headers, tablefmt="grid"))

if __name__ == '__main__':
    cli()