#!/usr/bin/env python
# scripts/enhanced_trigger_installer.py
# python scripts/enhanced_trigger_installer.py install-all-triggers

import os
import sys
import click
from flask.cli import with_appcontext
from sqlalchemy import text
from pathlib import Path
import re

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app import create_app, db
    print("Successfully imported app module")
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

# Helper for better SQL statement extraction
def split_sql_statements(sql_content):
    """Split SQL content into individual statements more reliably"""
    statements = []
    current_statement = []
    in_function_body = False
    in_transaction_block = False
    in_do_block = False
    nesting_level = 0
    
    for line in sql_content.split('\n'):
        # Track if we're in a function body
        if '$$' in line:
            in_function_body = not in_function_body
        
        # Track nesting level of DO blocks
        if re.search(r'\bDO\s*\$\$', line, re.IGNORECASE):
            in_do_block = True
            nesting_level += 1
        
        if in_do_block and '$$' in line and not line.strip().startswith('DO'):
            nesting_level -= 1
            if nesting_level == 0:
                in_do_block = False
        
        # Track BEGIN/END blocks
        if re.search(r'\bBEGIN\b', line, re.IGNORECASE) and not in_function_body:
            in_transaction_block = True
            nesting_level += 1
        
        if in_transaction_block and re.search(r'\bEND\b', line, re.IGNORECASE):
            nesting_level -= 1
            if nesting_level == 0:
                in_transaction_block = False
        
        # Add the current line to the statement
        current_statement.append(line)
        
        # Only split on semicolons outside of function bodies and transaction blocks
        if ';' in line and not in_function_body and not in_transaction_block and not in_do_block:
            statements.append('\n'.join(current_statement))
            current_statement = []
    
    # Add any remaining statement
    if current_statement:
        statements.append('\n'.join(current_statement))
    
    # Remove empty statements
    statements = [s for s in statements if s.strip()]
    
    return statements

def extract_function_definitions(sql_content):
    """Extract function definitions for easier processing"""
    # Regular expression to find CREATE OR REPLACE FUNCTION statements
    pattern = r'CREATE\s+OR\s+REPLACE\s+FUNCTION\s+([a-zA-Z0-9_]+)\s*\('
    
    # Find all matches
    matches = re.finditer(pattern, sql_content, re.IGNORECASE)
    
    # Extract function names
    function_names = [match.group(1) for match in matches]
    
    return function_names

def check_extension_exists(db, extension_name):
    """Check if a PostgreSQL extension exists"""
    result = db.session.execute(text(
        f"SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = '{extension_name}')"
    )).scalar()
    return result

def ensure_extension_exists(db, extension_name):
    """Ensure a PostgreSQL extension exists, creating it if needed"""
    if not check_extension_exists(db, extension_name):
        try:
            db.session.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension_name}"))
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating extension {extension_name}: {e}")
            return False
    return True

def check_table_exists(db, table_name, schema='public'):
    """Check if a table exists in the database"""
    result = db.session.execute(text(
        f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = '{schema}' AND table_name = '{table_name}')"
    )).scalar()
    return result

def check_column_exists(db, table_name, column_name, schema='public'):
    """Check if a column exists in a table"""
    result = db.session.execute(text(
        f"SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{table_name}' AND column_name = '{column_name}')"
    )).scalar()
    return result

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

@click.group()
def cli():
    """Enhanced trigger management commands"""
    pass

@cli.command()
@with_appcontext
def install_all_triggers():
    """Install all triggers with improved handling of dependencies"""
    app = get_app()
    click.echo('Starting enhanced trigger installation...')
    
    with app.app_context():
        db = get_db()
        
        # Step 1: Ensure pgcrypto extension is installed (critical for password hashing)
        click.echo('Checking pgcrypto extension...')
        pgcrypto_status = ensure_extension_exists(db, 'pgcrypto')
        if pgcrypto_status:
            click.echo('✓ pgcrypto extension is available')
        else:
            click.echo('⚠️ pgcrypto extension could not be installed - password hashing will be limited')
        
        # Step 2: Read the SQL file
        sql_path = Path(__file__).parent.parent / 'app' / 'database' / 'functions.sql'
        if not sql_path.exists():
            # Try fallback location
            sql_path = Path(__file__).parent.parent / 'app' / 'db' / 'functions.sql'
            if not sql_path.exists():
                click.echo(f'✗ functions.sql not found at any expected location')
                sys.exit(1)
        
        click.echo(f'✓ Found functions.sql at {sql_path}')
        with open(sql_path, 'r') as f:
            sql_content = f.read()
        
        # Step 3: Extract all function names for verification
        function_names = extract_function_definitions(sql_content)
        click.echo(f'Found {len(function_names)} function definitions')
        
        # Step 4: Split the SQL content into statements
        statements = split_sql_statements(sql_content)
        click.echo(f'Split SQL into {len(statements)} statements')
        
        # Step 5: Process statements in groups
        # First, create base functions
        base_functions = [
            'update_timestamp',
            'track_user_changes',
            'drop_existing_triggers',
            'create_audit_triggers',
            'create_audit_triggers_all_schemas'
        ]
        
        # Authentication functions
        auth_functions = [
            'update_failed_login_attempts',
            'update_on_successful_login',
            'check_account_lockout',
            'update_login_history_on_logout',
            'check_session_expiration'
        ]
        
        # Password management functions
        password_functions = [
            'hash_password'
        ]
        
        # Session management functions
        session_functions = [
            'manage_session_limits'
        ]
        
        # Role management functions
        role_functions = [
            'validate_role_assignment',
            'cleanup_user_roles'
        ]
        
        # Encryption functions
        encryption_functions = [
            'flag_fields_for_encryption'
        ]
        
        # Create all functions first
        click.echo('Installing base functions...')
        
        # Process each statement
        success_count = 0
        error_count = 0
        
        for i, stmt in enumerate(statements):
            if not stmt.strip():
                continue
                
            try:
                # Execute the statement
                db.session.execute(text(stmt))
                db.session.commit()
                success_count += 1
            except Exception as e:
                db.session.rollback()
                error_count += 1
                click.echo(f"⚠️ Error in statement {i+1}: {str(e)}")
                
                # Continue with other statements
                continue
        
        click.echo(f'✓ Processed {success_count} statements successfully ({error_count} errors)')
        
        # Verify functions were created
        missing_functions = []
        for func_name in function_names:
            if not check_function_exists(db, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            click.echo(f'⚠️ Missing functions after installation: {", ".join(missing_functions)}')
        else:
            click.echo('✓ All functions created successfully')
        
        # Apply audit triggers to all tables in all schemas
        click.echo('Applying audit triggers to all tables...')
        try:
            db.session.execute(text("SELECT create_audit_triggers_all_schemas()"))
            db.session.commit()
            click.echo('✓ Applied audit triggers to all tables')
        except Exception as e:
            db.session.rollback()
            click.echo(f'⚠️ Error applying audit triggers: {str(e)}')
        
        # Verify critical table existence for specific triggers
        required_tables = {
            'users': ['hash_password', 'cleanup_user_roles', 'check_account_lockout'],
            'login_history': ['track_failed_logins', 'track_successful_logins'],
            'user_sessions': ['check_session_expiration', 'track_logout', 'manage_session_limits'],
            'user_role_mapping': ['validate_role_assignment'],
            'patients': ['flag_patient_encryption']
        }
        
        click.echo('\nVerifying tables for specific triggers:')
        
        for table, triggers in required_tables.items():
            if check_table_exists(db, table):
                click.echo(f'✓ Table {table} exists - can apply specific triggers')
                
                # Apply manual trigger creation for tables that exist
                if table == 'users':
                    if not check_trigger_exists(db, 'hash_password', table):
                        try:
                            db.session.execute(text("""
                                DROP TRIGGER IF EXISTS hash_password ON users;
                                CREATE TRIGGER hash_password
                                BEFORE INSERT OR UPDATE ON users
                                FOR EACH ROW
                                EXECUTE FUNCTION hash_password();
                            """))
                            db.session.commit()
                            click.echo('  ✓ Created hash_password trigger on users table')
                        except Exception as e:
                            db.session.rollback()
                            click.echo(f'  ⚠️ Error creating hash_password trigger: {str(e)}')
                
                # Add other specific trigger creation as needed
            else:
                click.echo(f'⚠️ Table {table} does not exist - skipping specific triggers')
        
        # Final verification
        click.echo('\nPerforming final verification...')
        
        # Check for base audit triggers
        audit_trigger_count = db.session.execute(text("""
            SELECT COUNT(*) FROM information_schema.triggers 
            WHERE trigger_name IN ('update_timestamp', 'track_user_changes')
        """)).scalar()
        
        click.echo(f'Total audit triggers in database: {audit_trigger_count}')
        
        # Check if password hashing is working
        if check_table_exists(db, 'users'):
            click.echo('\nTesting password hashing functionality:')
            try:
                # Test insert a user with a plain password
                test_user_id = 'test_trigger_user_999'
                
                # Check if user exists and delete if it does
                user_exists = db.session.execute(text(
                    f"SELECT EXISTS(SELECT 1 FROM users WHERE user_id = '{test_user_id}')"
                )).scalar()
                
                if user_exists:
                    db.session.execute(text(f"DELETE FROM users WHERE user_id = '{test_user_id}'"))
                    db.session.commit()
                
                # Insert test user
                password_column = 'password_hash' if check_column_exists(db, 'users', 'password_hash') else 'password'
                
                # Build appropriate INSERT statement based on available columns
                cols = db.session.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
                )).fetchall()
                col_names = [c[0] for c in cols]
                
                # Build a minimal insert statement with required fields
                insert_cols = ['user_id']
                insert_vals = [f"'{test_user_id}'"]
                
                # Add password column
                if password_column in col_names:
                    insert_cols.append(password_column)
                    insert_vals.append("'test_password'")
                
                # Add other required columns with default values
                for col in col_names:
                    if col not in insert_cols and col not in ('created_at', 'updated_at', 'created_by', 'updated_by'):
                        if col in ('is_active', 'is_superuser', 'encryption_enabled'):
                            insert_cols.append(col)
                            insert_vals.append('FALSE')
                        elif col in ('failed_login_attempts'):
                            insert_cols.append(col)
                            insert_vals.append('0')
                        elif col == 'hospital_id' and check_table_exists(db, 'hospitals'):
                            # Get first hospital_id
                            hospital_id = db.session.execute(text(
                                "SELECT hospital_id FROM hospitals LIMIT 1"
                            )).scalar()
                            if hospital_id:
                                insert_cols.append(col)
                                insert_vals.append(f"'{hospital_id}'")
                
                # Execute insert
                insert_sql = f"INSERT INTO users ({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})"
                db.session.execute(text(insert_sql))
                db.session.commit()
                
                # Check if password was hashed
                password_value = db.session.execute(text(
                    f"SELECT {password_column} FROM users WHERE user_id = '{test_user_id}'"
                )).scalar()
                
                # Clean up
                db.session.execute(text(f"DELETE FROM users WHERE user_id = '{test_user_id}'"))
                db.session.commit()
                
                # Verify password hashing
                is_hashed = password_value != 'test_password' and (
                    password_value.startswith('$2') or len(password_value) > 30
                )
                
                if is_hashed:
                    click.echo('  ✓ Password hashing trigger is working!')
                    click.echo(f'  Original: "test_password"')
                    click.echo(f'  Hashed: "{password_value}"')
                else:
                    click.echo('  ⚠️ Password hashing trigger is NOT working')
                    click.echo(f'  Password remained: "{password_value}"')
            except Exception as e:
                db.session.rollback()
                click.echo(f'  ⚠️ Error testing password hashing: {str(e)}')
        
        click.echo('\nTrigger installation and verification complete')

if __name__ == '__main__':
    cli()