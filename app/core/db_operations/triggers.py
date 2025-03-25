# app/core/db_operations/triggers.py
"""
Database trigger operations.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union, Callable

from .utils import (
    get_db_config, normalize_env_name, get_short_env_name,
    logger, project_root
)

def _get_app_db():
    """Helper to get app and db objects with lazy loading"""
    # Global variables for lazy loading
    _app = None
    _db = None
    
    try:
        # First try to get app
        from app import create_app
        _app = create_app()
        
        # Then get db
        from app import db
        _db = db
        
        return _app, _db
    except Exception as e:
        logger.error(f"Error initializing Flask app: {str(e)}")
        return None, None

def _with_app_context(func: Callable) -> Any:
    """
    Execute a function within Flask app context.
    
    Args:
        func: Function to execute
        
    Returns:
        Result of the function
    """
    app, db = _get_app_db()
    if not app or not db:
        return False
    
    try:
        with app.app_context():
            return func(db)
    except Exception as e:
        logger.error(f"Error in app context: {str(e)}")
        return False

def apply_base_triggers(env: Optional[str] = None) -> bool:
    """
    Apply only base database trigger functionality (without table-specific triggers).
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    logger.info('Starting to apply base trigger functions...')
    
    def _apply_base_triggers(db):
        try:
            # Read functions.sql
            sql_path = project_root / 'app' / 'database' / 'functions.sql'
            if not sql_path.exists():
                # Try fallback location
                sql_path = project_root / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    # Try triggers directory
                    sql_path = project_root / 'app' / 'database' / 'triggers' / 'functions.sql'
                    if not sql_path.exists():
                        logger.error('functions.sql not found')
                        return False
                    
            logger.info(f'Found functions.sql at {sql_path}')
            with open(sql_path, 'r') as f:
                sql_content = f.read()
            
            # Extract only base functions (before Authentication Triggers section)
            current_section = []
            for line in sql_content.split('\n'):
                if "Authentication Triggers" in line:
                    break
                current_section.append(line)
            
            base_sql = '\n'.join(current_section)
            
            # Apply only base functions
            from sqlalchemy import text
            logger.info('Creating base database functions...')
            db.session.execute(text(base_sql))
            db.session.commit()
            
            # Apply basic trigger functions to all tables
            logger.info('Applying triggers to existing tables...')
            db.session.execute(text("SELECT create_audit_triggers('public')"))
            db.session.commit()
            
            logger.info('Base trigger functions applied successfully')
            return True
                
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error applying base database functions: {str(e)}')
            return False
    
    return _with_app_context(_apply_base_triggers)

def apply_triggers(env: Optional[str] = None) -> bool:
    """
    Apply all database triggers and functions with progressive fallbacks.
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    logger.info('Starting to apply database triggers and functions...')
    
    def _apply_triggers(db):
        try:
            from sqlalchemy import text
            
            # Step 1: Try to find functions.sql (original approach)
            sql_path = project_root / 'app' / 'database' / 'functions.sql'
            if not sql_path.exists():
                # Try fallback location
                sql_path = project_root / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    # Try triggers directory
                    sql_path = project_root / 'app' / 'database' / 'triggers' / 'functions.sql'
                    if not sql_path.exists():
                        logger.error('functions.sql not found')
                        return False
                
            logger.info(f'Found functions.sql at {sql_path}')
            with open(sql_path, 'r') as f:
                sql = f.read()
            
            # Step 2: Try applying full SQL script (original approach)
            logger.info('Attempting to apply full functions.sql...')
            success = False
            try:
                # Split SQL into statements and execute each separately
                statements = []
                current_statement = []
                
                # Simple SQL parser to split on semicolons that aren't in functions
                in_function = False
                in_do_block = False
                nesting_level = 0
                
                for line in sql.split('\n'):
                    # Track function and DO block boundaries
                    if 'DO $$' in line:
                        in_do_block = True
                        nesting_level += 1
                    elif '$$' in line and not in_function:
                        if in_do_block:
                            nesting_level -= 1
                            if nesting_level == 0:
                                in_do_block = False
                        else:
                            in_function = not in_function
                    
                    # Add line to current statement
                    current_statement.append(line)
                    
                    # If semicolon outside function/block, end statement
                    if ';' in line and not in_function and not in_do_block:
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                
                # Add any remaining statement
                if current_statement:
                    statements.append('\n'.join(current_statement))
                
                # Execute each statement separately
                error_count = 0
                for i, stmt in enumerate(statements):
                    if not stmt.strip():
                        continue
                    
                    try:
                        db.session.execute(text(stmt))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        logger.warning(f"Error in statement {i+1}: {str(e)}")
                        error_count += 1
                
                if error_count == 0:
                    logger.info('Applied all database functions and triggers successfully')
                    success = True
                else:
                    logger.warning(f'Applied with {error_count} errors - may need fallback approach')
            except Exception as e:
                db.session.rollback()
                logger.warning(f'Error applying full SQL: {str(e)}')
            
            # Step 3: If full script failed, try just the base functions from functions.sql
            if not success:
                logger.info('Attempting to apply only base trigger functions from functions.sql...')
                try:
                    # Extract only base functions (before Authentication Triggers section)
                    current_section = []
                    for line in sql.split('\n'):
                        if "Authentication Triggers" in line:
                            break
                        current_section.append(line)
                    
                    base_sql = '\n'.join(current_section)
                    
                    # Apply only base functions
                    db.session.execute(text(base_sql))
                    db.session.commit()
                    
                    # Apply basic trigger functions to all tables
                    db.session.execute(text("SELECT create_audit_triggers('public')"))
                    db.session.commit()
                    
                    logger.info('Base trigger functions applied successfully')
                    success = True
                except Exception as e:
                    db.session.rollback()
                    logger.warning(f'Error applying base functions: {str(e)}')
            
            # Step 4: Final fallback - try core_trigger_functions.sql if it exists
            if not success:
                logger.info('Attempting to use core_trigger_functions.sql as fallback...')
                core_sql_path = project_root / 'app' / 'database' / 'core_trigger_functions.sql'
                
                if not core_sql_path.exists():
                    # Try triggers directory
                    core_sql_path = project_root / 'app' / 'database' / 'triggers' / 'core_triggers.sql'
                
                if core_sql_path.exists():
                    try:
                        with open(core_sql_path, 'r') as f:
                            core_sql = f.read()
                        
                        # Split and execute each statement separately for better error handling
                        statements = []
                        current_statement = []
                        in_block = False
                        
                        for line in core_sql.split('\n'):
                            if line.strip().startswith('--'):
                                continue
                                
                            if '$$' in line:
                                in_block = not in_block
                                
                            current_statement.append(line)
                            
                            if ';' in line and not in_block:
                                statements.append('\n'.join(current_statement))
                                current_statement = []
                        
                        # Execute each statement
                        for stmt in statements:
                            if not stmt.strip():
                                continue
                                
                            try:
                                db.session.execute(text(stmt))
                                db.session.commit()
                            except Exception as e:
                                db.session.rollback()
                                logger.warning(f'Error in core function: {str(e)}')
                        
                        # Apply core triggers to all tables
                        try:
                            db.session.execute(text("SELECT create_audit_triggers_all_schemas()"))
                            db.session.commit()
                            logger.info('Applied core audit triggers to all tables')
                        except Exception as e:
                            db.session.rollback()
                            logger.warning(f'Error applying core audit triggers: {str(e)}')
                        
                        logger.info('Core trigger functions applied successfully')
                        success = True
                    except Exception as e:
                        db.session.rollback()
                        logger.warning(f'Error applying core trigger functions: {str(e)}')
                else:
                    logger.warning('core_trigger_functions.sql not found - cannot use fallback')
            
            # Step 5: Apply hash_password trigger to users table specifically if needed
            try:
                # Check if users table exists
                users_exist = db.session.execute(text(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users')"
                )).scalar()
                
                if users_exist:
                    # Check if hash_password function exists
                    hash_func_exists = db.session.execute(text(
                        "SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
                        "WHERE n.nspname = 'public' AND p.proname = 'hash_password')"
                    )).scalar()
                    
                    if hash_func_exists:
                        # Check if trigger already exists
                        trigger_exists = db.session.execute(text(
                            "SELECT EXISTS(SELECT 1 FROM information_schema.triggers "
                            "WHERE trigger_schema = 'public' AND event_object_table = 'users' AND trigger_name = 'hash_password')"
                        )).scalar()
                        
                        if not trigger_exists:
                            logger.info('Applying hash_password trigger to users table...')
                            db.session.execute(text("""
                                DROP TRIGGER IF EXISTS hash_password ON users;
                                CREATE TRIGGER hash_password
                                BEFORE INSERT OR UPDATE ON users
                                FOR EACH ROW
                                EXECUTE FUNCTION hash_password();
                            """))
                            db.session.commit()
                            logger.info('Applied hash_password trigger to users table')
            except Exception as e:
                db.session.rollback()
                logger.warning(f'Error applying hash_password trigger: {str(e)}')
            
            # Final status report
            if success:
                logger.info('Database triggers applied successfully via one of the available methods')
                return True
            else:
                logger.warning('All methods to apply triggers failed')
                logger.warning('Try running: python scripts/install_triggers.py')
                return False
                    
        except Exception as e:
            logger.error(f'Error applying database functions: {str(e)}')
            return False
    
    return _with_app_context(_apply_triggers)

def apply_all_schema_triggers(env: Optional[str] = None) -> bool:
    """
    Apply base database trigger functionality to all schemas.
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    logger.info('Starting to apply triggers to all schemas...')
    
    def _apply_all_schema_triggers(db):
        try:
            from sqlalchemy import text
            
            # First, make sure the base trigger functions are created
            logger.info('Ensuring base trigger functions exist...')
            
            # Read functions.sql to ensure functions exist
            sql_path = project_root / 'app' / 'database' / 'functions.sql'
            if not sql_path.exists():
                # Try fallback location
                sql_path = project_root / 'app' / 'db' / 'functions.sql'
                if not sql_path.exists():
                    # Try triggers directory
                    sql_path = project_root / 'app' / 'database' / 'triggers' / 'functions.sql'
                    if not sql_path.exists():
                        logger.error('functions.sql not found')
                        return False
                    
            logger.info(f'Found functions.sql at {sql_path}')
            
            # Read the file and extract just the base functions
            with open(sql_path, 'r') as f:
                sql_content = f.read()
            
            # Extract only base functions (before Authentication Triggers section)
            current_section = []
            for line in sql_content.split('\n'):
                if "Authentication Triggers" in line:
                    break
                current_section.append(line)
            
            base_sql = '\n'.join(current_section)
            
            # Apply base functions first
            logger.info('Creating base database functions...')
            db.session.execute(text(base_sql))
            db.session.commit()
            
            # Then define the multi-schema function
            logger.info('Creating multi-schema function...')
            
            multi_schema_function = """
            -- Function to apply triggers to all schemas
            CREATE OR REPLACE FUNCTION create_audit_triggers_all_schemas()
            RETURNS void AS $$
            DECLARE
                schema_record RECORD;
                schema_count INTEGER := 0;
                table_count INTEGER := 0;
                trigger_count INTEGER := 0;
            BEGIN
                -- Loop through all schemas (excluding system schemas)
                FOR schema_record IN 
                    SELECT nspname AS schema_name
                    FROM pg_namespace
                    WHERE nspname NOT LIKE 'pg_%' 
                      AND nspname != 'information_schema'
                LOOP
                    -- Log which schema we're processing
                    RAISE NOTICE 'Processing schema: %', schema_record.schema_name;
                    schema_count := schema_count + 1;
                    
                    -- Count tables in this schema before processing
                    SELECT COUNT(*) INTO table_count 
                    FROM pg_tables 
                    WHERE schemaname = schema_record.schema_name;
                    
                    RAISE NOTICE 'Found % tables in schema %', table_count, schema_record.schema_name;
                    
                    -- Apply triggers to all tables in this schema
                    PERFORM create_audit_triggers(schema_record.schema_name);
                    
                    -- Count triggers created (just the base audit triggers)
                    SELECT COUNT(*) INTO trigger_count
                    FROM information_schema.triggers
                    WHERE trigger_schema = schema_record.schema_name
                      AND (trigger_name = 'update_timestamp' OR trigger_name = 'track_user_changes');
                    
                    RAISE NOTICE 'Created/verified % triggers in schema %', trigger_count, schema_record.schema_name;
                END LOOP;
                
                RAISE NOTICE 'Processed % schemas in total', schema_count;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # Setting message level to NOTICE to see the detailed logs
            db.session.execute(text("SET client_min_messages TO NOTICE"))
            
            # Create the function in the database
            db.session.execute(text(multi_schema_function))
            db.session.commit()
            
            logger.info('Function created successfully')
            
            # Now call the function to apply triggers to all schemas
            logger.info('Applying triggers to all schemas...')
            db.session.execute(text("SELECT create_audit_triggers_all_schemas()"))
            db.session.commit()
            
            logger.info('Applied triggers to all schemas successfully')
            return True
                
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error applying triggers to all schemas: {str(e)}')
            return False
    
    return _with_app_context(_apply_all_schema_triggers)

def verify_triggers(env: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify trigger installation.
    
    Args:
        env: Target environment
        
    Returns:
        Dictionary with verification results
    """
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    # First try dedicated verification script
    verify_script = project_root / 'scripts' / 'verify_triggers.py'
    
    if verify_script.exists():
        # Use dedicated verification script if available
        logger.info("Using dedicated verification script...")
        results = {
            'success': True,
            'functions': [],
            'critical_triggers': [],
            'tables': [],
            'errors': []
        }
        
        try:
            # Check functions first
            proc_result = subprocess.run(
                [sys.executable, str(verify_script), "verify-functions"],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Parse function verification results
            results['functions'] = proc_result.stdout.splitlines()
            
            # Check critical triggers
            proc_result = subprocess.run(
                [sys.executable, str(verify_script), "verify-critical-triggers"],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Parse trigger verification results
            results['critical_triggers'] = proc_result.stdout.splitlines()
            
            return results
                
        except subprocess.CalledProcessError as e:
            logger.error(f'Error in verification: {e.stderr}')
            results['success'] = False
            results['errors'].append(str(e.stderr))
            return results
    else:
        # Legacy verification if verify_triggers.py is not available
        def _legacy_verify(db):
            from sqlalchemy import text
            logger.info('Verifying trigger installation (legacy method)...')
            
            results = {
                'success': True,
                'functions': [],
                'tables': [],
                'errors': []
            }
            
            try:
                # Check for core trigger functions
                core_functions = ['update_timestamp', 'track_user_changes', 'hash_password']
                for func in core_functions:
                    result = db.session.execute(text(
                        f"SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
                        f"WHERE n.nspname = 'public' AND p.proname = '{func}')"
                    )).scalar()
                    
                    if result:
                        results['functions'].append(f"Function '{func}' exists")
                    else:
                        results['functions'].append(f"Function '{func}' is missing")
                
                # Check triggers on key tables
                tables = ['users', 'login_history', 'user_sessions']
                for table in tables:
                    # First check if table exists
                    table_exists = db.session.execute(text(
                        f"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                        f"WHERE table_schema = 'public' AND table_name = '{table}')"
                    )).scalar()
                    
                    if not table_exists:
                        results['tables'].append(f"Table '{table}' does not exist - skipping trigger check")
                        continue
                    
                    # Count triggers on this table
                    trigger_count = db.session.execute(text(
                        f"SELECT COUNT(*) FROM information_schema.triggers "
                        f"WHERE trigger_schema = 'public' AND event_object_table = '{table}'"
                    )).scalar()
                    
                    results['tables'].append(f"Table '{table}' has {trigger_count} triggers")
                
                return results
            except Exception as e:
                logger.error(f"Error verifying triggers: {e}")
                results['success'] = False
                results['errors'].append(str(e))
                return results
        
        # Execute the legacy verification
        return _with_app_context(_legacy_verify)    