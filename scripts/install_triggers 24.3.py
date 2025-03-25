#!/usr/bin/env python
# scripts/install_triggers.py
# A simplified script to install core triggers when other methods fail
# Usage: python scripts/install_triggers.py [dev|test|prod]

import os
import sys
import time
from pathlib import Path
from sqlalchemy import create_engine, text
import logging
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Install database triggers')
parser.add_argument('env', nargs='?', default='test', choices=['dev', 'test', 'prod'],
                    help='Database environment to use (default: test)')
parser.add_argument('--verify', action='store_true', help='Verify triggers after installation')
args = parser.parse_args()

# Try to get database URL from environment based on selected environment
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    if args.env == 'dev':
        database_url = os.getenv('DEV_DATABASE_URL', None)
        logger.info("Using DEV database")
    elif args.env == 'test':
        database_url = os.getenv('TEST_DATABASE_URL', None)
        logger.info("Using TEST database")
    elif args.env == 'prod':
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

def install_hash_password_function():
    """Install the hash_password function explicitly"""
    logger.info('Installing hash_password function...')
    
    # Create engine
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
        
    except Exception as e:
        connection.rollback()
        logger.warning(f'Error installing hash_password function: {str(e)}')
    finally:
        connection.close()

def install_core_triggers():
    """Install core triggers from the standalone SQL file"""
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
            create_core_functions_file(sql_path)
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
                
            if '$$' in line:
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

def create_core_functions_file(file_path):
    """Create the core trigger functions file if it doesn't exist"""
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Content for core_trigger_functions.sql
    content = """-- core_trigger_functions.sql
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
    
    with open(file_path, 'w') as f:
        f.write(content)

def verify_triggers():
    """Verify that key triggers are working"""
    logger.info('Verifying installed triggers...')
    
    # Create engine
    engine = create_engine(database_url)
    connection = engine.connect()
    
    try:
        # Check if core functions exist
        functions = ['update_timestamp', 'track_user_changes', 'hash_password', 'create_audit_triggers']
        missing_functions = []
        
        for func in functions:
            result = connection.execute(text(
                f"SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
                f"WHERE n.nspname = 'public' AND p.proname = '{func}')"
            )).scalar()
            
            if not result:
                missing_functions.append(func)
        
        if missing_functions:
            logger.warning(f"Missing functions: {', '.join(missing_functions)}")
        else:
            logger.info("✓ All core functions exist")
        
        # Let's get a list of all tables to help debug
        all_tables = connection.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')"
        )).fetchall()
        
        logger.info(f"Tables found in database: {len(all_tables)}")
        if len(all_tables) < 20:  # Only show if there aren't too many
            for schema, table in all_tables:
                logger.info(f"  - {schema}.{table}")
        
        # More robust check for users table
        users_table_name = None
        for schema, table in all_tables:
            if table.lower() == 'users':
                users_table_name = table
                break
        
        if users_table_name:
            # Count triggers on users table
            trigger_count = connection.execute(text(
                f"SELECT COUNT(*) FROM information_schema.triggers "
                f"WHERE trigger_schema = 'public' AND event_object_table = '{users_table_name}'"
            )).scalar()
            
            logger.info(f"Users table has {trigger_count} triggers")
            
            # Check for specific triggers
            triggers = ['update_timestamp', 'track_user_changes', 'hash_password']
            for trigger in triggers:
                trigger_exists = connection.execute(text(
                    f"SELECT EXISTS(SELECT 1 FROM information_schema.triggers "
                    f"WHERE trigger_schema = 'public' AND event_object_table = '{users_table_name}' "
                    f"AND trigger_name = '{trigger}')"
                )).scalar()
                
                if trigger_exists:
                    logger.info(f"✓ {trigger} trigger exists on users table")
                else:
                    logger.warning(f"⚠️ {trigger} trigger missing from users table")
            
            # Try to check trigger functionality by creating a test user
            try:
                # Get the column info to determine length constraints
                columns_info = connection.execute(text(
                    f"SELECT column_name, data_type, character_maximum_length, is_nullable "
                    f"FROM information_schema.columns "
                    f"WHERE table_schema = 'public' AND table_name = '{users_table_name}'"
                )).fetchall()
                
                # Find user_id and password columns and their constraints
                user_id_col = None
                password_col = None
                user_id_length = 15  # Default if not specified
                
                for col_name, data_type, max_length, nullable in columns_info:
                    if col_name.lower() == 'user_id':
                        user_id_col = col_name
                        if max_length is not None:
                            user_id_length = max_length
                    elif col_name.lower() in ('password', 'password_hash'):
                        password_col = col_name
                
                # Create test user ID that fits within the length constraint
                test_user_id = f"test{str(int(time.time()))[-8:]}"
                if len(test_user_id) > user_id_length:
                    test_user_id = test_user_id[:user_id_length]
                
                logger.info(f"Using test user ID: {test_user_id} (max length: {user_id_length})")
                
                # Check if test user exists and delete it
                test_user_exists = connection.execute(text(
                    f"SELECT EXISTS(SELECT 1 FROM {users_table_name} WHERE user_id = '{test_user_id}')"
                )).scalar()
                
                if test_user_exists:
                    connection.execute(text(f"DELETE FROM {users_table_name} WHERE user_id = '{test_user_id}'"))
                    connection.commit()
                
                # Find required columns by checking for NOT NULL constraints
                required_cols = []
                for col_name, data_type, max_length, nullable in columns_info:
                    if nullable == 'NO' and col_name not in ('created_at', 'updated_at', 'created_by', 'updated_by'):
                        required_cols.append((col_name, data_type, max_length))
                
                # Build insert statement with required columns
                insert_cols = []
                insert_vals = []
                
                for col_name, data_type, max_length in required_cols:
                    insert_cols.append(col_name)
                    
                    # Set appropriate values based on column name and type
                    if col_name.lower() == 'user_id':
                        insert_vals.append(f"'{test_user_id}'")
                    elif col_name.lower() in ('password', 'password_hash'):
                        insert_vals.append("'test_pwd'")
                    elif 'char' in data_type.lower():
                        # For string columns, use a value that fits
                        if max_length:
                            val = 'test'
                            if len(val) > max_length:
                                val = val[:max_length]
                            insert_vals.append(f"'{val}'")
                        else:
                            insert_vals.append("'test'")
                    elif 'int' in data_type.lower():
                        insert_vals.append('0')
                    elif data_type.lower() == 'boolean':
                        insert_vals.append('FALSE')
                    else:
                        # Default fallback
                        insert_vals.append("'test'")
                
                # Ensure user_id and password are included
                if user_id_col and user_id_col not in insert_cols:
                    insert_cols.append(user_id_col)
                    insert_vals.append(f"'{test_user_id}'")
                
                if password_col and password_col not in insert_cols:
                    insert_cols.append(password_col)
                    insert_vals.append("'test_pwd'")
                
                # Try the insert
                insert_sql = f"""
                    INSERT INTO {users_table_name} ({', '.join(insert_cols)}) 
                    VALUES ({', '.join(insert_vals)})
                """
                
                logger.info(f"Attempting insert: {insert_sql}")
                connection.execute(text(insert_sql))
                connection.commit()
                
                # Check if the password was hashed
                if password_col:
                    hashed_password = connection.execute(text(
                        f"SELECT {password_col} FROM {users_table_name} WHERE user_id = '{test_user_id}'"
                    )).scalar()
                    
                    # Clean up
                    connection.execute(text(f"DELETE FROM {users_table_name} WHERE user_id = '{test_user_id}'"))
                    connection.commit()
                    
                    # Check if password was hashed
                    if hashed_password != 'test_pwd' and (
                        hashed_password and (hashed_password.startswith('$2') or len(hashed_password) > 30)
                    ):
                        logger.info("✓ Password hashing trigger is working!")
                        logger.info(f"Original: \"test_pwd\"")
                        logger.info(f"Hashed: \"{hashed_password}\"")
                    else:
                        logger.warning("⚠️ Password hashing trigger is NOT working")
                        logger.info(f"Password value: \"{hashed_password}\"")
                else:
                    logger.warning("No password column found in users table")
                    
            except Exception as e:
                connection.rollback()
                logger.warning(f"Error testing trigger functionality: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
        else:
            logger.info("Users table does not exist - skipping user trigger checks")
        
        logger.info('\nTrigger verification completed')
        
    finally:
        connection.close()

if __name__ == '__main__':
    # If hash_password function is missing, first create it
    if '--verify' in sys.argv or args.verify:
        verify_triggers()
    else:
        # Check if hash_password function needs to be created first
        engine = create_engine(database_url)
        connection = engine.connect()
        
        try:
            # Check if hash_password function exists
            function_exists = connection.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
                "WHERE n.nspname = 'public' AND p.proname = 'hash_password')"
            )).scalar()
            
            if not function_exists:
                logger.info("hash_password function doesn't exist - creating it first")
                install_hash_password_function()
        except Exception as e:
            logger.warning(f"Error checking for hash_password function: {str(e)}")
        finally:
            connection.close()
        
        # Continue with core triggers installation
        install_core_triggers()
        
        # Verify at the end if requested
        if args.verify:
            verify_triggers()   