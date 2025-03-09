-- skinspire_V2/app/database/functions.sql
-- python scripts/manage_db.py apply-triggers
-----------------------------------------
-- Base Audit Functionality
-----------------------------------------

-- Create timestamp trigger function
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create user tracking trigger function with column existence check
CREATE OR REPLACE FUNCTION track_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Get user from either old or new location
    DECLARE
        current_user_value text;
    BEGIN
        -- Try new location first, fall back to old location
        BEGIN
            current_user_value := current_setting('application.app_user', TRUE);
        EXCEPTION WHEN UNDEFINED_OBJECT THEN
            current_user_value := current_setting('app.current_user', TRUE);
        END;

        -- For INSERT operations
        IF TG_OP = 'INSERT' THEN
            -- Check and set created_by if column exists
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = TG_TABLE_NAME AND column_name = 'created_by') THEN
                NEW.created_by = current_user_value;
            END IF;
            
            -- Check and set updated_by if column exists
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = TG_TABLE_NAME AND column_name = 'updated_by') THEN
                NEW.updated_by = current_user_value;
            END IF;
        
        -- For UPDATE operations
        ELSIF TG_OP = 'UPDATE' THEN
            -- Check and set updated_by if column exists
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = TG_TABLE_NAME AND column_name = 'updated_by') THEN
                NEW.updated_by = current_user_value;
            END IF;
            
            -- Check and set updated_at if column exists
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = TG_TABLE_NAME AND column_name = 'updated_at') THEN
                NEW.updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC';
            END IF;
        END IF;
        
        RETURN NEW;
    END;
END;
$$ language 'plpgsql';

-- Helper function to safely drop existing triggers
CREATE OR REPLACE FUNCTION drop_existing_triggers(schema_name text, table_name text)
RETURNS void AS $$
BEGIN
    -- Drop triggers if they exist, suppress any errors
    BEGIN
        EXECUTE format(
            'DROP TRIGGER IF EXISTS update_timestamp ON %I.%I',
            schema_name,
            table_name
        );
    EXCEPTION WHEN OTHERS THEN
        -- Ignore errors when dropping triggers
        NULL;
    END;
    
    BEGIN
        EXECUTE format(
            'DROP TRIGGER IF EXISTS track_user_changes ON %I.%I',
            schema_name,
            table_name
        );
    EXCEPTION WHEN OTHERS THEN
        -- Ignore errors when dropping triggers
        NULL;
    END;
END;
$$ LANGUAGE plpgsql;

-- Function to apply triggers to all tables
CREATE OR REPLACE FUNCTION create_audit_triggers(schema_name text)
RETURNS void AS $$
DECLARE
    table_name text;
BEGIN
    FOR table_name IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = schema_name
    LOOP
        -- First, safely remove any existing triggers
        PERFORM drop_existing_triggers(schema_name, table_name);
        
        -- Then create timestamp trigger
        BEGIN
            EXECUTE format(
                'CREATE TRIGGER update_timestamp
                 BEFORE UPDATE ON %I.%I
                 FOR EACH ROW
                 EXECUTE FUNCTION update_timestamp()',
                schema_name,
                table_name
            );
        EXCEPTION WHEN duplicate_object THEN
            -- If trigger already exists, continue to next one
            NULL;
        END;
        
        -- Create user tracking trigger
        BEGIN
            EXECUTE format(
                'CREATE TRIGGER track_user_changes
                 BEFORE INSERT OR UPDATE ON %I.%I
                 FOR EACH ROW
                 EXECUTE FUNCTION track_user_changes()',
                schema_name,
                table_name
            );
        EXCEPTION WHEN duplicate_object THEN
            -- If trigger already exists, continue to next one
            NULL;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-----------------------------------------
-- Authentication Triggers
-----------------------------------------

-- 1. Track failed login attempts
CREATE OR REPLACE FUNCTION update_failed_login_attempts()
RETURNS TRIGGER AS $$
BEGIN
    -- If a login history entry is created with status 'failed'
    IF NEW.status = 'failed' THEN
        -- Increment the failed login attempts counter for the user
        UPDATE users
        SET failed_login_attempts = failed_login_attempts + 1
        WHERE user_id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER track_failed_logins
AFTER INSERT ON login_history
FOR EACH ROW
WHEN (NEW.status = 'failed')
EXECUTE FUNCTION update_failed_login_attempts();

-- 2. Reset failed attempts on successful login
CREATE OR REPLACE FUNCTION update_on_successful_login()
RETURNS TRIGGER AS $$
BEGIN
    -- Reset failed attempts counter and update last login time
    UPDATE users
    SET failed_login_attempts = 0,
        last_login = NEW.login_time
    WHERE user_id = NEW.user_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER track_successful_logins
AFTER INSERT ON login_history
FOR EACH ROW
WHEN (NEW.status = 'success')
EXECUTE FUNCTION update_on_successful_login();

-- 3. Account lockout enforcement
CREATE OR REPLACE FUNCTION check_account_lockout()
RETURNS TRIGGER AS $$
DECLARE
    max_attempts INTEGER := 5; -- Default value
    config_value TEXT;
BEGIN
    -- Try to get max_attempts from parameter_settings if table exists
    BEGIN
        SELECT param_value INTO config_value
        FROM parameter_settings 
        WHERE param_code = 'MAX_LOGIN_ATTEMPTS';
        
        IF config_value IS NOT NULL THEN
            max_attempts := config_value::INTEGER;
        END IF;
    EXCEPTION 
        WHEN undefined_table THEN
            -- Table doesn't exist, use default
            NULL;
        WHEN others THEN
            -- Other errors, use default
            NULL;
    END;
    
    -- If failed attempts exceed threshold, consider account locked
    -- Note: We don't actually set a 'locked' field, just use the count as a flag
    -- Testing code will need to check failed_login_attempts to determine lock status
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_account_lockout
AFTER UPDATE OF failed_login_attempts ON users
FOR EACH ROW
EXECUTE FUNCTION check_account_lockout();

-- 4. Update login history on logout
CREATE OR REPLACE FUNCTION update_login_history_on_logout()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the corresponding login history record
    UPDATE login_history
    SET logout_time = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    WHERE user_id = NEW.user_id
    AND logout_time IS NULL
    ORDER BY login_time DESC
    LIMIT 1;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER track_session_logout
AFTER UPDATE ON user_sessions
FOR EACH ROW
WHEN (OLD.is_active = TRUE AND NEW.is_active = FALSE)
EXECUTE FUNCTION update_login_history_on_logout();

-- 5. Automatic session expiration check
CREATE OR REPLACE FUNCTION check_session_expiration()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if session has expired
    IF NEW.expires_at < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' THEN
        NEW.is_active = FALSE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_session_expiration
BEFORE UPDATE ON user_sessions
FOR EACH ROW
EXECUTE FUNCTION check_session_expiration();

-----------------------------------------
-- Password Management Triggers
-----------------------------------------

-- Check if pgcrypto extension is available for password hashing
DO $$
BEGIN
    -- Try to create the extension if not exists
    BEGIN
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    EXCEPTION WHEN OTHERS THEN
        -- If we can't create it, just continue
        -- The trigger will use application-provided hashes
        NULL;
    END;
END$$;

-- Password hashing function (only used if pgcrypto is available)
CREATE OR REPLACE FUNCTION hash_password()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if this is a password change and if it needs hashing
    -- We only hash if the password doesn't already look like a bcrypt hash
    -- This is a simple check to see if the password starts with $2b$ (bcrypt)
    IF (TG_OP = 'INSERT' OR NEW.password_hash <> OLD.password_hash) AND 
       NEW.password_hash IS NOT NULL AND
       NOT NEW.password_hash LIKE '$2%$%' THEN
        
        -- Check if pgcrypto is available
        IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
            -- Use pgcrypto for hashing
            NEW.password_hash = crypt(NEW.password_hash, gen_salt('bf', 10));
        END IF;
        -- If pgcrypto is not available, we assume the application will handle hashing
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only create the trigger if users table exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'users'
    ) THEN
        -- Safe drop if exists
        DROP TRIGGER IF EXISTS hash_password ON users;
        
        -- Create new trigger
        CREATE TRIGGER hash_password
        BEFORE INSERT OR UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION hash_password();
    END IF;
END$$;

-----------------------------------------
-- Session Management Triggers
-----------------------------------------

-- Manage session limits per user
CREATE OR REPLACE FUNCTION manage_session_limits()
RETURNS TRIGGER AS $$
DECLARE
    max_sessions INTEGER := 5; -- Default value
    config_value TEXT;
    active_count INTEGER;
    oldest_session UUID;
BEGIN
    -- Try to get max_sessions from parameter_settings if table exists
    BEGIN
        SELECT param_value INTO config_value
        FROM parameter_settings 
        WHERE param_code = 'MAX_ACTIVE_SESSIONS';
        
        IF config_value IS NOT NULL THEN
            max_sessions := config_value::INTEGER;
        END IF;
    EXCEPTION 
        WHEN undefined_table THEN
            -- Table doesn't exist, use default
            NULL;
        WHEN others THEN
            -- Other errors, use default
            NULL;
    END;
    
    -- Count active sessions for this user
    SELECT COUNT(*) INTO active_count
    FROM user_sessions
    WHERE user_id = NEW.user_id 
    AND is_active = TRUE;
    
    -- If too many active sessions, deactivate the oldest one(s)
    IF active_count > max_sessions THEN
        -- Find the oldest active sessions to deactivate
        FOR oldest_session IN
            SELECT session_id FROM user_sessions
            WHERE user_id = NEW.user_id AND is_active = TRUE
            ORDER BY created_at ASC
            LIMIT (active_count - max_sessions)
        LOOP
            -- Deactivate oldest session
            UPDATE user_sessions
            SET is_active = FALSE
            WHERE session_id = oldest_session;
        END LOOP;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only create the trigger if user_sessions table exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_sessions'
    ) THEN
        -- Safe drop if exists
        DROP TRIGGER IF EXISTS manage_session_limits ON user_sessions;
        
        -- Create new trigger
        CREATE TRIGGER manage_session_limits
        AFTER INSERT ON user_sessions
        FOR EACH ROW
        EXECUTE FUNCTION manage_session_limits();
    END IF;
END$$;

-----------------------------------------
-- Role Management Triggers
-----------------------------------------

-- Validate role assignments before insertion
CREATE OR REPLACE FUNCTION validate_role_assignment()
RETURNS TRIGGER AS $$
BEGIN
    -- Verify user exists
    IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = NEW.user_id) THEN
        RAISE EXCEPTION 'Cannot assign role to non-existent user %', NEW.user_id;
    END IF;
    
    -- Verify role exists
    IF NOT EXISTS (SELECT 1 FROM role_master WHERE role_id = NEW.role_id) THEN
        RAISE EXCEPTION 'Cannot assign non-existent role %', NEW.role_id;
    END IF;
    
    -- All verifications passed
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only create the trigger if user_role_mapping table exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_role_mapping'
    ) THEN
        -- Safe drop if exists
        DROP TRIGGER IF EXISTS validate_role_assignment ON user_role_mapping;
        
        -- Create new trigger
        CREATE TRIGGER validate_role_assignment
        BEFORE INSERT OR UPDATE ON user_role_mapping
        FOR EACH ROW
        EXECUTE FUNCTION validate_role_assignment();
    END IF;
END$$;

-- Automatically clean up role assignments when user is deleted
CREATE OR REPLACE FUNCTION cleanup_user_roles()
RETURNS TRIGGER AS $$
BEGIN
    -- Remove all role mappings for this user
    DELETE FROM user_role_mapping
    WHERE user_id = OLD.user_id;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Only create the trigger if users and user_role_mapping tables exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'user_role_mapping'
    ) THEN
        -- Safe drop if exists
        DROP TRIGGER IF EXISTS cleanup_user_roles ON users;
        
        -- Create new trigger
        CREATE TRIGGER cleanup_user_roles
        BEFORE DELETE ON users
        FOR EACH ROW
        EXECUTE FUNCTION cleanup_user_roles();
    END IF;
END$$;

-----------------------------------------
-- Encryption Flag Triggers
-----------------------------------------

-- Flag records that need encryption (actual encryption happens in application)
CREATE OR REPLACE FUNCTION flag_fields_for_encryption()
RETURNS TRIGGER AS $$
DECLARE
    hospital_encryption_enabled BOOLEAN;
BEGIN
    -- For patient records, check hospital encryption setting
    IF TG_TABLE_NAME = 'patients' THEN
        -- Check if encryption is enabled for this hospital
        SELECT encryption_enabled INTO hospital_encryption_enabled
        FROM hospitals
        WHERE hospital_id = NEW.hospital_id;
        
        -- Flag fields needing encryption if enabled
        IF hospital_encryption_enabled = TRUE THEN
            -- We'll use a metadata column to indicate encryption needed
            -- This requires adding a needs_encryption column to the patients table
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'patients' AND column_name = 'needs_encryption'
            ) THEN
                NEW.needs_encryption = TRUE;
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Only create the trigger if patients and hospitals tables exist
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'patients'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'hospitals'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'patients' AND column_name = 'needs_encryption'
    ) THEN
        -- Safe drop if exists
        DROP TRIGGER IF EXISTS flag_patient_encryption ON patients;
        
        -- Create new trigger
        CREATE TRIGGER flag_patient_encryption
        BEFORE INSERT OR UPDATE ON patients
        FOR EACH ROW
        EXECUTE FUNCTION flag_fields_for_encryption();
    END IF;
END$$;

-----------------------------------------
-- Multi-Schema Support
-----------------------------------------

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