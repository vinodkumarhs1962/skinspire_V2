# app/core/db_operations/maintenance.py
"""
Database maintenance operations.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union, Callable

from .utils import (
    get_db_config, normalize_env_name, get_short_env_name,
    get_db_url_components, setup_env_vars, logger, project_root
)
from .triggers import apply_triggers, _with_app_context, _get_app_db

def check_db(env: Optional[str] = None) -> Dict[str, Any]:
    """
    Check database connection and status.
    
    Args:
        env: Target environment
        
    Returns:
        Dictionary with check results
    """
    results = {
        'success': True,
        'environment': None,
        'database_url': None,
        'flask_config': {},
        'connection_test': False,
        'query_test': False,
        'table_creation_test': False,
        'errors': []
    }
    
    try:
        # Get DatabaseConfig
        db_config = get_db_config()
        
        # Normalize environment if provided
        if env:
            full_env = normalize_env_name(env)
            os.environ['FLASK_ENV'] = full_env
        else:
            full_env = db_config.get_active_env()
        
        # Get database URL
        db_url = db_config.get_database_url_for_env(full_env)
        
        # Store info in results
        results['environment'] = full_env
        
        # Mask password in the URL for security
        if db_url and '://' in db_url and '@' in db_url:
            parts = db_url.split('@')
            credentials = parts[0].split('://')
            if len(credentials) > 1 and ':' in credentials[1]:
                user_pass = credentials[1].split(':')
                masked_url = f"{credentials[0]}://{user_pass[0]}:****@{parts[1]}"
                results['database_url'] = masked_url
            else:
                results['database_url'] = db_url
        else:
            results['database_url'] = db_url
        
        # Try to get app and db for detailed checks
        app, db = _get_app_db()
        
        if not app or not db:
            results['success'] = False
            results['errors'].append("Failed to initialize Flask app and db")
            return results
        
        # Get Flask config details
        for key, value in app.config.items():
            if 'DATABASE' in key or 'SQL' in key:
                # Mask password in connection strings
                if isinstance(value, str) and '://' in value and '@' in value:
                    parts = value.split('@')
                    credentials = parts[0].split('://')
                    if len(credentials) > 1 and ':' in credentials[1]:
                        user_pass = credentials[1].split(':')
                        masked_value = f"{credentials[0]}://{user_pass[0]}:****@{parts[1]}"
                        results['flask_config'][key] = masked_value
                    else:
                        results['flask_config'][key] = value
                else:
                    results['flask_config'][key] = value
        
        # Test database connection and functionality
        def _test_db_connection(db):
            try:
                from sqlalchemy import text
                
                # Test connection
                conn = db.engine.connect()
                results['connection_test'] = True
                
                # Test query
                result = db.session.execute(text('SELECT 1'))
                value = result.scalar()
                results['query_test'] = True
                
                # Check if we can create a test table
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS _test_table (
                        id SERIAL PRIMARY KEY,
                        test_column VARCHAR(50)
                    )
                '''))
                results['table_creation_test'] = True
                
                # Clean up test table
                db.session.execute(text('DROP TABLE IF EXISTS _test_table'))
                db.session.commit()
                
                conn.close()
                return results
            except Exception as e:
                db.session.rollback()
                results['success'] = False
                results['errors'].append(f"Database check failed: {str(e)}")
                return results
        
        return _with_app_context(_test_db_connection)
    except Exception as e:
        results['success'] = False
        results['errors'].append(f"Initial database configuration check failed: {str(e)}")
        return results

def drop_all_tables(env: Optional[str] = None) -> bool:
    """
    Drop all tables in correct order.
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    def _drop_all_tables(db):
        try:
            from sqlalchemy import text
            
            # Drop tables in correct order
            sql = """
            DO $ 
            BEGIN
                -- Disable triggers temporarily
                SET CONSTRAINTS ALL DEFERRED;
                
                -- Drop tables in order
                DROP TABLE IF EXISTS staff CASCADE;
                DROP TABLE IF EXISTS branches CASCADE;
                DROP TABLE IF EXISTS login_history CASCADE;
                DROP TABLE IF EXISTS user_sessions CASCADE;
                DROP TABLE IF EXISTS user_role_mapping CASCADE;
                DROP TABLE IF EXISTS users CASCADE;
                DROP TABLE IF EXISTS hospitals CASCADE;
                DROP TABLE IF EXISTS role_master CASCADE;
                DROP TABLE IF EXISTS module_master CASCADE;
                DROP TABLE IF EXISTS parameter_settings CASCADE;
                DROP TABLE IF EXISTS role_module_access CASCADE;
                DROP TABLE IF EXISTS patients CASCADE;
                
                -- Add any other tables that need to be dropped
                
                -- Re-enable triggers
                SET CONSTRAINTS ALL IMMEDIATE;
            END $;
            """
            db.session.execute(text(sql))
            db.session.commit()
            logger.info('All tables dropped successfully')
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error dropping tables: {str(e)}')
            return False
    
    return _with_app_context(_drop_all_tables)

def reset_db(env: Optional[str] = None) -> bool:
    """
    Remove existing migrations and reinitialize.
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    logger.info('Starting database reset...')
    
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    # First check database connection
    check_results = check_db(env)
    if not check_results['success']:
        logger.error("Database connection check failed, aborting reset")
        return False
    
    # Drop all tables first
    if not drop_all_tables(env):
        logger.error("Failed to drop all tables, aborting reset")
        return False
    
    # Remove existing migrations
    migrations_dir = project_root / 'migrations'
    if migrations_dir.exists():
        shutil.rmtree(migrations_dir)
        logger.info('Removed existing migrations directory')
    
    try:
        # Initialize migrations
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'init'],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info('Initialized new migrations directory')
        
        # Create migration
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'migrate', '-m', "initial migration"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info('Created initial migration')
        
        # Apply migration
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'upgrade'],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info('Applied migrations to database')
        
        logger.info('Database reset completed successfully!')
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration command failed: {e}")
        if e.stdout:
            logger.debug(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        return False

def init_db(env: Optional[str] = None) -> bool:
    """
    Initialize database tables without migrations.
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    logger.info('Starting database initialization...')
    
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    # First check database connection
    check_results = check_db(env)
    if not check_results['success']:
        logger.error("Database connection check failed, aborting initialization")
        return False
    
    def _init_db(db):
        try:
            db.create_all()
            logger.info('Created all database tables')
            return True
        except Exception as e:
            logger.error(f'Database initialization failed: {str(e)}')
            return False
    
    success = _with_app_context(_init_db)
    
    if success:
        logger.info('Database initialization completed successfully!')
    
    return success

def reset_and_init(env: Optional[str] = None) -> bool:
    """
    Reset database (drop all tables) and reinitialize with create_database.py.
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    logger.info('Starting database reset and initialization...')
    
    # Normalize environment if provided
    if env:
        full_env = normalize_env_name(env)
        os.environ['FLASK_ENV'] = full_env
    
    # First check database connection
    check_results = check_db(env)
    if not check_results['success']:
        logger.error("Database connection check failed, aborting reset and initialization")
        return False
    
    # Drop all tables first
    if not drop_all_tables(env):
        logger.error("Failed to drop all tables, aborting reset and initialization")
        return False
    
    # Initialize empty tables using SQLAlchemy models
    logger.info('Creating empty tables from models...')
    if not init_db(env):
        logger.error("Failed to initialize database tables, aborting reset and initialization")
        return False
    
    # Apply triggers
    logger.info('Applying database triggers...')
    if not apply_triggers(env):
        logger.warning("Failed to apply database triggers, continuing with initialization")
    
    # Run create_database.py script to initialize data
    logger.info('Initializing database with data...')
    create_db_script = project_root / "scripts" / "create_database.py"
    
    if not create_db_script.exists():
        logger.warning("create_database.py script not found, skipping data initialization")
        return True
    
    try:
        # Use subprocess to run the create_database.py script
        result = subprocess.run(
            [sys.executable, str(create_db_script)],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Output from create_database.py
        logger.info("Output from create_database.py:")
        for line in result.stdout.splitlines():
            logger.info(f"  {line}")
        
        logger.info('Database reset and initialization completed successfully!')
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f'Error running create_database.py: {e.stderr}')
        return False