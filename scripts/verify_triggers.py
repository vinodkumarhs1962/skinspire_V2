#!/usr/bin/env python
# scripts/verify_triggers.py
# Lightweight verification script for production deployment
#
# Usage:
#   python scripts/verify_triggers.py verify-functions
#   python scripts/verify_triggers.py verify-trigger-count
#   python scripts/verify_triggers.py verify-critical-triggers

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

def check_function_exists(db, function_name, schema='public'):
    """Check if a function exists in the database"""
    result = db.session.execute(text(
        f"SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid WHERE n.nspname = '{schema}' AND p.proname = '{function_name}')"
    )).scalar()
    return result

def check_trigger_exists(db, trigger_name, table_name, schema='public'):
    """Check if a trigger exists on a table"""
    result = db.session.execute(text(
        f"SELECT EXISTS(SELECT 1 FROM information_schema.triggers WHERE trigger_schema = '{schema}' AND event_object_table = '{table_name}' AND trigger_name = '{trigger_name}')"
    )).scalar()
    return result

def check_table_exists(db, table_name, schema='public'):
    """Check if a table exists in the database"""
    result = db.session.execute(text(
        f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = '{schema}' AND table_name = '{table_name}')"
    )).scalar()
    return result

@click.group()
def cli():
    """Trigger verification commands for deployment"""
    pass

@cli.command()
@with_appcontext
def verify_functions():
    """Verify all required trigger functions exist"""
    app = get_app()
    click.echo('Verifying trigger functions...')
    
    with app.app_context():
        db = get_db()
        
        # List of expected core trigger functions
        expected_functions = [
            'update_timestamp',
            'track_user_changes',
            'create_audit_triggers',
            'create_audit_triggers_all_schemas',
            'drop_existing_triggers'
        ]
        
        # List of expected auth trigger functions
        auth_functions = [
            'update_failed_login_attempts',
            'update_on_successful_login',
            'check_account_lockout',
            'update_login_history_on_logout',
            'check_session_expiration'
        ]
        
        # List of other specialized functions
        specialized_functions = [
            'hash_password',
            'manage_session_limits',
            'validate_role_assignment',
            'cleanup_user_roles',
            'flag_fields_for_encryption'
        ]
        
        # Check core functions
        missing_core = []
        for func in expected_functions:
            if not check_function_exists(db, func):
                missing_core.append(func)
        
        # Check auth functions
        missing_auth = []
        for func in auth_functions:
            if not check_function_exists(db, func):
                missing_auth.append(func)
        
        # Check specialized functions
        missing_specialized = []
        for func in specialized_functions:
            if not check_function_exists(db, func):
                missing_specialized.append(func)
        
        # Output results
        click.echo(f"\nCore Trigger Functions: {len(expected_functions) - len(missing_core)}/{len(expected_functions)} exist")
        if missing_core:
            click.echo("  Missing core functions: " + ", ".join(missing_core))
        else:
            click.echo("  + All core functions exist")
        
        click.echo(f"\nAuthentication Functions: {len(auth_functions) - len(missing_auth)}/{len(auth_functions)} exist")
        if missing_auth:
            click.echo("  Missing auth functions: " + ", ".join(missing_auth))
        else:
            click.echo("  + All authentication functions exist")
        
        click.echo(f"\nSpecialized Functions: {len(specialized_functions) - len(missing_specialized)}/{len(specialized_functions)} exist")
        if missing_specialized:
            click.echo("  Missing specialized functions: " + ", ".join(missing_specialized))
        else:
            click.echo("  + All specialized functions exist")
        
        # Overall assessment
        total_missing = len(missing_core) + len(missing_auth) + len(missing_specialized)
        total_functions = len(expected_functions) + len(auth_functions) + len(specialized_functions)
        
        click.echo(f"\nOverall Function Status: {total_functions - total_missing}/{total_functions} exist")
        
        if total_missing > 0:
            click.echo("\nTo fix missing functions, run:")
            click.echo("  python scripts/manage_db.py apply-triggers")
        else:
            click.echo("\n+ All required trigger functions exist!")

@cli.command()
@with_appcontext
def verify_trigger_count():
    """Count triggers by table and type"""
    app = get_app()
    click.echo('Counting triggers by table...')
    
    with app.app_context():
        db = get_db()
        
        # Get all triggers grouped by table
        triggers = db.session.execute(text("""
            SELECT 
                event_object_table AS table_name,
                COUNT(*) AS trigger_count,
                STRING_AGG(trigger_name, ', ' ORDER BY trigger_name) AS trigger_names
            FROM information_schema.triggers
            WHERE trigger_schema = 'public'
            GROUP BY event_object_table
            ORDER BY event_object_table
        """)).fetchall()
        
        if not triggers:
            click.echo("No triggers found in the database!")
            return
        
        # Display as table
        headers = ["Table", "Trigger Count", "Trigger Names"]
        click.echo("\nTriggers by Table:")
        click.echo(tabulate(triggers, headers=headers, tablefmt="grid"))
        
        # Count total triggers
        total = sum(t[1] for t in triggers)
        click.echo(f"\nTotal triggers in database: {total}")
        
        # Count triggers by type
        audit_triggers = db.session.execute(text("""
            SELECT COUNT(*) FROM information_schema.triggers
            WHERE trigger_schema = 'public'
            AND trigger_name IN ('update_timestamp', 'track_user_changes')
        """)).scalar()
        
        auth_triggers = db.session.execute(text("""
            SELECT COUNT(*) FROM information_schema.triggers
            WHERE trigger_schema = 'public'
            AND trigger_name IN (
                'track_failed_logins', 'track_successful_logins', 
                'check_account_lockout', 'track_logout', 
                'check_session_expiration'
            )
        """)).scalar()
        
        other_triggers = total - audit_triggers - auth_triggers
        
        click.echo("\nTriggers by Type:")
        click.echo(f"  Audit Triggers: {audit_triggers}")
        click.echo(f"  Authentication Triggers: {auth_triggers}")
        click.echo(f"  Other Specialized Triggers: {other_triggers}")

@cli.command()
@with_appcontext
def verify_critical_triggers():
    """Verify critical triggers exist on key tables"""
    app = get_app()
    click.echo('Verifying critical triggers on key tables...')
    
    with app.app_context():
        db = get_db()
        
        # Define critical tables and their expected triggers
        critical_tables = {
            'users': [
                'update_timestamp', 
                'track_user_changes', 
                'hash_password', 
                'check_account_lockout'
            ],
            'login_history': [
                'update_timestamp', 
                'track_user_changes', 
                'track_failed_logins', 
                'track_successful_logins'
            ],
            'user_sessions': [
                'update_timestamp', 
                'track_user_changes', 
                'check_session_expiration', 
                'track_logout', 
                'manage_session_limits'
            ],
            'user_role_mapping': [
                'update_timestamp', 
                'track_user_changes', 
                'validate_role_assignment'
            ]
        }
        
        # Check each table
        results = []
        for table, expected_triggers in critical_tables.items():
            # Check if table exists
            table_exists = check_table_exists(db, table)
            
            if not table_exists:
                results.append([table, "Table does not exist", "N/A", "N/A"])
                continue
            
            # Get actual triggers on this table
            actual_triggers = db.session.execute(text(f"""
                SELECT trigger_name
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
                AND event_object_table = '{table}'
            """)).fetchall()
            
            actual_trigger_names = [t[0] for t in actual_triggers]
            missing = [t for t in expected_triggers if t not in actual_trigger_names]
            
            # Add to results
            status = "+ All triggers present" if not missing else f"Missing {len(missing)} triggers"
            missing_str = ", ".join(missing) if missing else "None"
            results.append([
                table, 
                status, 
                f"{len(actual_trigger_names)}/{len(expected_triggers)}", 
                missing_str
            ])
        
        # Display results
        headers = ["Table", "Status", "Triggers", "Missing"]
        click.echo("\nCritical Table Trigger Status:")
        click.echo(tabulate(results, headers=headers, tablefmt="grid"))
        
        # Summary
        all_ok = all(row[1].startswith("+") for row in results)
        if all_ok:
            click.echo("\n+ All critical tables have required triggers!")
        else:
            click.echo("\n! Some critical tables are missing required triggers.")
            click.echo("Run the following command to fix:")
            click.echo("  python scripts/manage_db.py apply-triggers")

if __name__ == '__main__':
    cli()
    sys.exit(0)