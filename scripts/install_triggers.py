#!/usr/bin/env python
# scripts/install_triggers.py
"""
DEPRECATED: This module is deprecated and will be removed in a future version.
The functionality has been moved to app.core.db_operations.triggers

This module is kept for backward compatibility and for direct PostgreSQL trigger
management when other methods fail. Please use:
'python scripts/manage_db.py apply-db-triggers' instead.
"""

import os
import sys
import time
import argparse
import warnings
import logging
from pathlib import Path
from sqlalchemy import create_engine, text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Show deprecation warning
warnings.warn(
    "This script is deprecated. Please use 'python scripts/manage_db.py apply-db-triggers' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Try to use core modules first
try:
    from app.core.db_operations.triggers import (
        apply_triggers as core_apply_triggers,
        apply_base_triggers as core_apply_base_triggers,
        verify_triggers as core_verify_triggers
    )
    from app.core.db_operations.utils import get_db_config
    
    CORE_MODULES_AVAILABLE = True
except ImportError:
    CORE_MODULES_AVAILABLE = False
    logger.warning("Core modules not available, using legacy implementation")

def get_database_url(env):
    """Get database URL for the specified environment"""
    if CORE_MODULES_AVAILABLE:
        try:
            db_config = get_db_config()
            # Map short names to full names
            env_map = {'dev': 'development', 'test': 'testing', 'prod': 'production'}
            full_env = env_map.get(env, env)
            return db_config.get_database_url_for_env(full_env)
        except Exception as e:
            logger.warning(f"Error accessing centralized configuration: {e}")
    
    # Fallback to environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        if env == 'dev':
            database_url = os.getenv('DEV_DATABASE_URL', None)
            logger.info("Using DEV database")
        elif env == 'test':
            database_url = os.getenv('TEST_DATABASE_URL', None)
            logger.info("Using TEST database")
        elif env == 'prod':
            database_url = os.getenv('PROD_DATABASE_URL', None)
            logger.info("Using PROD database")
        else:
            database_url = os.getenv('TEST_DATABASE_URL', None)
            logger.info("Defaulting to TEST database")
    except ImportError:
        database_url = None
    
    # Default value if not found in environment
    if not database_url:
        database_url = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        logger.info(f"Using default connection string: {database_url}")
    
    return database_url

def install_hash_password_function(database_url):
    """Install the hash_password function explicitly"""
    if CORE_MODULES_AVAILABLE:
        logger.info("Using core modules for hash_password function")
        success = core_apply_base_triggers()
        return success
    
    # Legacy implementation
    logger.info('Installing hash_password function...')
    
    if CORE_MODULES_AVAILABLE:
        logger.info("Using core modules for trigger verification")
        results = core_verify_triggers(env)
        
        # Display results from core module
        if isinstance(results, dict):
            if 'success' in results:
                logger.info(f"Verification result: {'SUCCESS' if results['success'] else 'FAILED'}")
            
            if 'functions' in results and results['functions']:
                logger.info("Function verification:")
                for item in results['functions']:
                    logger.info(f"  {item}")
            
            if 'critical_triggers' in results and results['critical_triggers']:
                logger.info("Critical trigger verification:")
                for item in results['critical_triggers']:
                    logger.info(f"  {item}")
                    
            if 'tables' in results and results['tables']:
                logger.info("Table trigger verification:")
                for item in results['tables']:
                    logger.info(f"  {item}")
                    
            if 'errors' in results and results['errors']:
                logger.warning("Verification errors:")
                for error in results['errors']:
                    logger.warning(f"  {error}")
            
            return results.get('success', False)
        
        return bool(results)
    
    # Legacy implementation
    database_url = get_database_url(env or 'test')
    engine = create_engine(database_url)
    connection = engine.connect()
    
    try:
        # First, try to install pgcrypto extension explicitly
        try:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
            connection.commit()
            logger.info("✓ Installed pgcrypto extension")
        except Exception as e:
            connection.rollback()
            logger.warning(f"Failed to install pgcrypto extension: {e}")

        # Create the hash_password function
        hash_password_function = """
        -- Simple password hashing function that works even without pgcrypto
        CREATE OR REPLACE FUNCTION hash_password()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Determine which column contains the password
            DECLARE
                password_column TEXT := NULL;
            BEGIN
                -- Check for common password column names
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password_hash') THEN
                    password_column := 'password_hash';
                ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password') THEN
                    password_column := 'password';
                END IF;
                
                -- Only proceed if we found a password column
                IF password_column IS NOT NULL THEN
                    -- For password_hash column
                    IF password_column = 'password_hash' THEN
                        -- Only hash if not already hashed
                        IF (TG_OP = 'INSERT' OR NEW.password_hash <> OLD.password_hash) AND 
                           NEW.password_hash IS NOT NULL  THEN 
                            -- Try to use pgcrypto if available
                            BEGIN
                                NEW.password_hash = crypt(NEW.password_hash, gen_salt('bf', 10));
                            EXCEPTION WHEN undefined_function THEN
                                -- Fall back to a marker if pgcrypto is not available
                                NULL; #remove mock hash
                            END;
                        END IF;
                    -- For password column
                    ELSIF password_column = 'password' THEN
                        -- Only hash if not already hashed
                        IF (TG_OP = 'INSERT' OR NEW.password <> OLD.password) AND 
                           NEW.password IS NOT NULL THEN 
                            -- Try to use pgcrypto if available
                            BEGIN
                                NEW.password = crypt(NEW.password, gen_salt('bf', 10));
                            EXCEPTION WHEN undefined_function THEN
                                -- Fall back to a marker if pgcrypto is not available
                                NULL; #remove mock hash
                            END;
                        END IF;
                    END IF;
                END IF;
            END;
            
            RETURN NEW;
        EXCEPTION WHEN OTHERS THEN
            -- Fail gracefully
            RAISE WARNING 'Error in hash_password trigger: %', SQLERRM;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
      
        connection.execute(text(hash_password_function))
        connection.commit()
        logger.info('✓ Installed hash_password function')
        
        # Apply to users table if it exists
        users_table = None
        tables = connection.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )).fetchall()
        
        for table in tables:
            if table[0].lower() == 'users':
                users_table = table[0]
                break
        
        if users_table:
            # Apply the trigger
            connection.execute(text(f"""
                DROP TRIGGER IF EXISTS hash_password ON "{users_table}";
                CREATE TRIGGER hash_password
                BEFORE INSERT OR UPDATE ON "{users_table}"
                FOR EACH ROW
                EXECUTE FUNCTION hash_password();
            """))
            connection.commit()
            logger.info(f'✓ Applied hash_password trigger to {users_table} table')
            return True
        
    except Exception as e:
        connection.rollback()
        logger.warning(f'Error installing hash_password function: {str(e)}')
        return False
    finally:
        connection.close()
    
    return False

def install_core_triggers(database_url):
    """Install core triggers from the standalone SQL file"""
    if CORE_MODULES_AVAILABLE:
        logger.info("Using core modules for trigger installation")
        success = core_apply_triggers()
        return success
    
    # Legacy implementation
    logger.info('Starting core trigger installation...')
    
    # Create engine
    engine = create_engine(database_url)
    connection = engine.connect()
    
    try:
        # Path to core trigger functions
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sql_path = Path(script_dir).parent / 'app' / 'database' / 'core_trigger_functions.sql'
        
        if not sql_path.exists():
            # Create the file if it doesn't exist
            core_content = """-- core_trigger_functions.sql
-- Minimal, robust trigger functions that work regardless of database state
-- This file is used as a fallback when the main functions.sql fails

-- Create pgcrypto extension if available (needed for password hashing)
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Insufficient privileges to create pgcrypto extension. Some password functions may be limited.';
END $$;

-- Basic timestamp update function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Track user changes function
CREATE OR REPLACE FUNCTION track_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Only set created_by on INSERT
    IF (TG_OP = 'INSERT') THEN
        -- Check if created_by column exists in this table
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
            AND column_name = 'created_by'
        ) THEN
            BEGIN
                NEW.created_by = current_setting('app.current_user', true);
            EXCEPTION WHEN OTHERS THEN
                -- Ignore if variable not set
                NULL;
            END;
        END IF;
    END IF;
    
    -- Always set updated_by on INSERT or UPDATE if the column exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
        AND column_name = 'updated_by'
    ) THEN
        BEGIN
            NEW.updated_by = current_setting('app.current_user', true);
        EXCEPTION WHEN OTHERS THEN
            -- Ignore if variable not set
            NULL;
        END;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to safely drop existing triggers
CREATE OR REPLACE FUNCTION drop_existing_triggers(schema_name TEXT, table_name TEXT)
RETURNS void AS $$
DECLARE
    trigger_rec RECORD;
BEGIN
    FOR trigger_rec IN 
        SELECT trigger_name 
        FROM information_schema.triggers
        WHERE trigger_schema = schema_name AND event_object_table = table_name
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I', 
                      trigger_rec.trigger_name, schema_name, table_name);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create audit triggers on a specified table
CREATE OR REPLACE FUNCTION create_audit_triggers(target_schema TEXT, target_table TEXT)
RETURNS void AS $$
DECLARE
    has_updated_at BOOLEAN;
    has_created_at BOOLEAN;
    has_updated_by BOOLEAN;
    has_created_by BOOLEAN;
BEGIN
    -- Check if columns exist in this table
    SELECT 
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'updated_at') AS has_updated_at,
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'created_at') AS has_created_at,
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'updated_by') AS has_updated_by,
        EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = target_schema AND table_name = target_table AND column_name = 'created_by') AS has_created_by
    INTO 
        has_updated_at, has_created_at, has_updated_by, has_created_by;
    
    -- Only create timestamp trigger if column exists
    IF has_updated_at THEN
        EXECUTE format('DROP TRIGGER IF EXISTS update_timestamp ON %I.%I', 
                      target_schema, target_table);
        EXECUTE format('CREATE TRIGGER update_timestamp BEFORE UPDATE ON %I.%I 
                      FOR EACH ROW EXECUTE FUNCTION update_timestamp()', 
                      target_schema, target_table);
    END IF;
    
    -- Only create user tracking trigger if appropriate columns exist
    IF has_updated_by OR has_created_by THEN
        EXECUTE format('DROP TRIGGER IF EXISTS track_user_changes ON %I.%I', 
                      target_schema, target_table);
        EXECUTE format('CREATE TRIGGER track_user_changes BEFORE INSERT OR UPDATE ON %I.%I 
                      FOR EACH ROW EXECUTE FUNCTION track_user_changes()', 
                      target_schema, target_table);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to apply audit triggers to all tables in a schema
CREATE OR REPLACE FUNCTION create_audit_triggers(schema_name TEXT)
RETURNS void AS $$
DECLARE
    table_record RECORD;
BEGIN
    FOR table_record IN 
        SELECT table_name 
        FROM information_schema.tables
        WHERE table_schema = schema_name 
        AND table_type = 'BASE TABLE'
    LOOP
        PERFORM create_audit_triggers(schema_name, table_record.table_name);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to apply audit triggers to all schemas
CREATE OR REPLACE FUNCTION create_audit_triggers_all_schemas()
RETURNS void AS $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN 
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname NOT LIKE 'pg_%' 
          AND nspname != 'information_schema'
    LOOP
        PERFORM create_audit_triggers(schema_record.schema_name);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Simple password hashing function that works even without pgcrypto
CREATE OR REPLACE FUNCTION hash_password()
RETURNS TRIGGER AS $$
BEGIN
    -- Determine which column contains the password
    DECLARE
        password_column TEXT := NULL;
    BEGIN
        -- Check for common password column names
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password_hash') THEN
            password_column := 'password_hash';
        ELSIF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME AND column_name = 'password') THEN
            password_column := 'password';
        END IF;
        
        -- Only proceed if we found a password column
        IF password_column IS NOT NULL THEN
            -- For password_hash column
            IF password_column = 'password_hash' THEN
                -- Only hash if not already hashed
                IF (TG_OP = 'INSERT' OR NEW.password_hash <> OLD.password_hash) AND 
                   NEW.password_hash IS NOT NULL AND 
                   NOT (NEW.password_hash LIKE '$2%' OR length(NEW.password_hash) > 50) THEN
                    -- Try to use pgcrypto if available
                    BEGIN
                        NEW.password_hash = crypt(NEW.password_hash, gen_salt('bf', 10));
                    EXCEPTION WHEN undefined_function THEN
                        -- Fall back to a marker if pgcrypto is not available
                        NEW.password_hash = '$2a$10$mock_hash_' || NEW.password_hash;
                    END;
                END IF;
            -- For password column
            ELSIF password_column = 'password' THEN
                -- Only hash if not already hashed
                IF (TG_OP = 'INSERT' OR NEW.password <> OLD.password) AND 
                   NEW.password IS NOT NULL AND 
                   NOT (NEW.password LIKE '$2%' OR length(NEW.password) > 50) THEN
                    -- Try to use pgcrypto if available
                    BEGIN
                        NEW.password = crypt(NEW.password, gen_salt('bf', 10));
                    EXCEPTION WHEN undefined_function THEN
                        -- Fall back to a marker if pgcrypto is not available
                        NEW.password = '$2a$10$mock_hash_' || NEW.password;
                    END;
                END IF;
            END IF;
        END IF;
    END;
    
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    -- Fail gracefully
    RAISE WARNING 'Error in hash_password trigger: %', SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;"""
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(sql_path), exist_ok=True)
            
            # Write the file
            with open(sql_path, 'w') as f:
                f.write(core_content)
            
            logger.info(f'Created core trigger functions file at {sql_path}')
        
        # Read SQL file
        with open(sql_path, 'r') as f:
            sql = f.read()
        
        # Execute statements one by one for better error handling
        statements = []
        current_statement = []
        
        in_block = False
        for line in sql.split('\n'):
            if line.strip().startswith('--'):
                continue
                
            if '$' in line:
                in_block = not in_block
                
            current_statement.append(line)
            
            if ';' in line and not in_block:
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # Add any remaining statement
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        # Execute each statement
        success_count = 0
        error_count = 0
        for i, stmt in enumerate(statements, 1):
            if not stmt.strip():
                continue
                
            try:
                connection.execute(text(stmt))
                connection.commit()
                success_count += 1
                if i % 5 == 0:  # Log progress in batches
                    logger.info(f'Processed {i}/{len(statements)} statements')
            except Exception as e:
                connection.rollback()
                logger.warning(f'Error in statement {i}: {str(e)}')
                error_count += 1
                # Continue with other statements
                continue
        
        logger.info(f'Executed {success_count} statements successfully ({error_count} errors)')
        
        # Now apply triggers to all tables
        try:
            connection.execute(text("SELECT create_audit_triggers_all_schemas()"))
            connection.commit()
            logger.info('Applied audit triggers to all tables in all schemas')
        except Exception as e:
            connection.rollback()
            logger.warning(f'Error applying audit triggers to schemas: {str(e)}')
        
        # Apply hash_password trigger to users table if it exists
        try:
            # Check both with and without case sensitivity
            users_exist = connection.execute(text(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE "
                "table_schema = 'public' AND (table_name = 'users' OR table_name = 'Users'))"
            )).scalar()
            
            if users_exist:
                # Determine the actual table name (case sensitivity matters in PostgreSQL)
                table_name = connection.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE "
                    "table_schema = 'public' AND (table_name = 'users' OR table_name = 'Users') LIMIT 1"
                )).scalar()
                
                # Apply trigger using the correct case
                connection.execute(text(f"""
                    DROP TRIGGER IF EXISTS hash_password ON "{table_name}";
                    CREATE TRIGGER hash_password
                    BEFORE INSERT OR UPDATE ON "{table_name}"
                    FOR EACH ROW
                    EXECUTE FUNCTION hash_password();
                """))
                connection.commit()
                logger.info(f'Applied hash_password trigger to {table_name} table')
                return True
            else:
                # List all tables to help diagnose the issue
                tables = connection.execute(text(
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )).fetchall()
                
                if tables:
                    logger.info("Tables found in public schema:")
                    for schema, table in tables:
                        logger.info(f"  - {schema}.{table}")
                else:
                    logger.warning("No tables found in public schema")
        except Exception as e:
            connection.rollback()
            logger.warning(f'Error applying hash_password trigger: {str(e)}')
        
        logger.info('\nCore trigger installation completed successfully!')
        
    finally:
        connection.close()
    
    return True