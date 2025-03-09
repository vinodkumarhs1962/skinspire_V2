-- skinspire_V2/app/database/functions.sql
-- FIXED VERSION: Addresses trigger application issues and improves reliability

-----------------------------------------
-- PostgreSQL Extension Setup
-----------------------------------------

-- Ensure pgcrypto extension is available
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
        CREATE EXTENSION pgcrypto;
        RAISE NOTICE 'Created pgcrypto extension';
    END IF;
EXCEPTION WHEN insufficient_privilege THEN
    RAISE WARNING 'Insufficient privileges to create pgcrypto extension - password hashing will be limited';
END $$;

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

-- Create user tracking trigger function with more robust handling
CREATE OR REPLACE FUNCTION track_user_changes()
RETURNS TRIGGER AS $$
DECLARE
    current_user_value text;
BEGIN
    -- Try different ways to get the current user ID
    BEGIN
        -- Try using the app.current_user setting first
        current_user_value := current_setting('app.current_user', TRUE);
    EXCEPTION WHEN OTHERS THEN
        BEGIN
            -- Fall back to application.app_user setting
            current_user_value := current_setting('application.app_user', TRUE);
        EXCEPTION WHEN OTHERS THEN
            BEGIN
                -- Fall back to session_user if no application variable is set
                current_user_value := session_user;
            EXCEPTION WHEN OTHERS THEN
                -- Finally, use a default value if all else fails
                current_user_value := 'system';
            END;
        END;
    END;

    -- For INSERT operations
    IF TG_OP = 'INSERT' THEN
        -- Check and set created_by if column exists
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
                  AND column_name = 'created_by') THEN
            NEW.created_by = current_user_value;
        END IF;
        
        -- Check and set updated_by if column exists
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
                  AND column_name = 'updated_by') THEN
            NEW.updated_by = current_user_value;
        END IF;
    
    -- For UPDATE operations
    ELSIF TG_OP = 'UPDATE' THEN
        -- Check and set updated_by if column exists
        IF EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_schema = TG_TABLE_SCHEMA AND table_name = TG_TABLE_NAME 
                  AND column_name = 'updated_by') THEN
            NEW.updated_by = current_user_value;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Helper function to safely drop existing triggers
CREATE OR REPLACE FUNCTION drop_existing_triggers(schema_name text, table_name text)
RETURNS void AS $$
DECLARE
    trigger_rec RECORD;
BEGIN
    -- Find all triggers on this table and drop them one by one
    FOR trigger_rec IN
        SELECT trigger_name
        FROM information_schema.triggers
        WHERE event_object_schema = schema_name
          AND event_object_table = table_name
    LOOP
        BEGIN
            EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I.%I',
                trigger_rec.trigger_name,
                schema_name,
                table_name
            );
            RAISE NOTICE 'Dropped trigger % on %.%', 
                trigger_rec.trigger_name, schema_name, table_name;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Failed to drop trigger % on %.%: %', 
                trigger_rec.trigger_name, schema_name, table_name, SQLERRM;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to apply triggers to all tables in a schema
CREATE OR REPLACE FUNCTION create_audit_triggers(schema_name text)
RETURNS void AS $$
DECLARE
    table_rec RECORD;
    has_updated_at BOOLEAN;
    has_user_tracking BOOLEAN;
BEGIN
    -- Get all tables in the schema
    FOR table_rec IN 
        SELECT tablename AS table_name
        FROM pg_tables 
        WHERE schemaname = schema_name
    LOOP
        -- Check if table has updated_at column
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = schema_name 
              AND table_name = table_rec.table_name 
              AND column_name = 'updated_at'
        ) INTO has_updated_at;
        
        -- Check if table has user tracking columns
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = schema_name 
              AND table_name = table_rec.table_name 
              AND column_name = 'created_by'
        ) AND EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = schema_name 
              AND table_name = table_rec.table_name 
              AND column_name = 'updated_by'
        ) INTO has_user_tracking;
        
        -- First, safely remove any existing triggers
        PERFORM drop_existing_triggers(schema_name, table_rec.table_name);
        
        -- Create timestamp trigger if needed
        IF has_updated_at THEN
            BEGIN
                EXECUTE format(
                    'CREATE TRIGGER update_timestamp
                     BEFORE UPDATE ON %I.%I
                     FOR EACH ROW
                     EXECUTE FUNCTION update_timestamp()',
                    schema_name,
                    table_rec.table_name
                );
                RAISE NOTICE 'Created update_timestamp trigger on %.%', 
                    schema_name, table_rec.table_name;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to create update_timestamp trigger on %.%: %', 
                    schema_name, table_rec.table_name, SQLERRM;
            END;
        END IF;
        
        -- Create user tracking trigger if needed
        IF has_user_tracking THEN
            BEGIN
                EXECUTE format(
                    'CREATE TRIGGER track_user_changes
                     BEFORE INSERT OR UPDATE ON %I.%I
                     FOR EACH ROW
                     EXECUTE FUNCTION track_user_changes()',
                    schema_name,
                    table_rec.table_name
                );
                RAISE NOTICE 'Created track_user_changes trigger on %.%', 
                    schema_name, table_rec.table_name;
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to create track_user_changes trigger on %.%: %', 
                    schema_name, table_rec.table_name, SQLERRM;
            END;
        END IF;
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
        -- Update the users table only if it exists and has the right columns
        IF EXISTS (
            SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
        ) AND EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'failed_login_attempts'
        ) THEN
            -- Increment the failed login attempts counter for the user
            UPDATE users
            SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1
            WHERE user_id = NEW.user_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Reset failed attempts on successful login
CREATE OR REPLACE FUNCTION update_on_successful_login()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update users table if it exists and has the right columns
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'failed_login_attempts'
    ) THEN
        -- Reset failed attempts counter and update last login time
        UPDATE users
        SET failed_login_attempts = 0,
            last_login = CASE 
                WHEN EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'last_login'
                ) THEN NEW.login_time
                ELSE last_login
            END
        WHERE user_id = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Account lockout enforcement
CREATE OR REPLACE FUNCTION check_account_lockout()
RETURNS TRIGGER AS $$
DECLARE
    max_attempts INTEGER := 5; -- Default value
    config_value TEXT;
BEGIN
    -- Try to get max_attempts from parameter_settings if table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'parameter_settings'
    ) THEN
        BEGIN
            SELECT param_value INTO config_value
            FROM parameter_settings 
            WHERE param_code = 'MAX_LOGIN_ATTEMPTS';
            
            IF config_value IS NOT NULL THEN
                max_attempts := config_value::INTEGER;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- Use default on any error
            NULL;
        END;
    END IF;
    
    -- If failed attempts exceed threshold, lock the account if lockable
    IF NEW.failed_login_attempts >= max_attempts THEN
        -- Check if account_status column exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'account_status'
        ) THEN
            NEW.account_status = 'LOCKED';
        END IF;
        
        -- Check if locked_until column exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'locked_until'
        ) THEN
            NEW.locked_until = CURRENT_TIMESTAMP + INTERVAL '30 minutes';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 4. Update login history on logout
CREATE OR REPLACE FUNCTION update_login_history_on_logout()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if login_history table exists and has the right columns
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'login_history'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'login_history' AND column_name = 'logout_time'
    ) THEN
        -- Update the corresponding login history record
        UPDATE login_history
        SET logout_time = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        WHERE user_id = NEW.user_id
        AND logout_time IS NULL
        ORDER BY login_time DESC
        LIMIT 1;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-----------------------------------------
-- Password Management Triggers
-----------------------------------------

-- Password hashing function with improved robustness
CREATE OR REPLACE FUNCTION hash_password()
RETURNS TRIGGER AS $$
DECLARE
    password_field TEXT;
BEGIN
    -- Determine which password field to use (password_hash or password)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = TG_TABLE_NAME AND column_name = 'password_hash'
    ) THEN
        password_field := 'password_hash';
    ELSE
        password_field := 'password';
    END IF;
    
    -- Check if this is a password change and if it needs hashing
    IF (TG_OP = 'INSERT') OR 
       (TG_OP = 'UPDATE' AND 
        CASE 
            WHEN password_field = 'password_hash' THEN 
                NEW.password_hash IS DISTINCT FROM OLD.password_hash
            ELSE 
                NEW.password IS DISTINCT FROM OLD.password
        END) THEN
        
        -- Only hash if the password doesn't already look like a bcrypt hash
        IF (password_field = 'password_hash' AND 
            NEW.password_hash IS NOT NULL AND 
            NOT NEW.password_hash LIKE '$2%$%') OR
           (password_field = 'password' AND 
            NEW.password IS NOT NULL AND 
            NOT NEW.password LIKE '$2%$%') THEN
            
            -- Check if pgcrypto is available
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgcrypto') THEN
                -- Use pgcrypto for hashing
                IF password_field = 'password_hash' THEN
                    NEW.password_hash = crypt(NEW.password_hash, gen_salt('bf', 10));
                ELSE
                    NEW.password = crypt(NEW.password, gen_salt('bf', 10));
                END IF;
                
                RAISE NOTICE 'Password hashed for user_id: %', NEW.user_id;
            ELSE
                RAISE WARNING 'pgcrypto extension not available - password not hashed for user_id: %', NEW.user_id;
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-----------------------------------------
-- Session Management Triggers
-----------------------------------------

-- Manage session limits per user with improved reliability
CREATE OR REPLACE FUNCTION manage_session_limits()
RETURNS TRIGGER AS $$
DECLARE
    max_sessions INTEGER := 5; -- Default value
    config_value TEXT;
    active_count INTEGER;
    oldest_session_id TEXT;
BEGIN
    -- Try to get max_sessions from parameter_settings if table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'parameter_settings'
    ) THEN
        BEGIN
            SELECT param_value INTO config_value
            FROM parameter_settings 
            WHERE param_code = 'MAX_ACTIVE_SESSIONS';
            
            IF config_value IS NOT NULL THEN
                max_sessions := config_value::INTEGER;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- Use default on any error
            NULL;
        END;
    END IF;
    
    -- Get the session ID column name (could be session_id or just id)
    -- This makes the trigger more flexible
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_sessions' AND column_name = 'session_id'
    ) THEN
        -- Count active sessions for this user
        SELECT COUNT(*) INTO active_count
        FROM user_sessions
        WHERE user_id = NEW.user_id 
        AND is_active = TRUE;
        
        -- If too many active sessions, deactivate the oldest one(s)
        IF active_count > max_sessions THEN
            -- Find the oldest active sessions to deactivate (one at a time to be safe)
            FOR i IN 1..(active_count - max_sessions) LOOP
                SELECT session_id INTO oldest_session_id
                FROM user_sessions
                WHERE user_id = NEW.user_id 
                  AND is_active = TRUE
                  AND session_id != NEW.session_id
                ORDER BY created_at ASC
                LIMIT 1;
                
                IF oldest_session_id IS NOT NULL THEN
                    -- Deactivate oldest session
                    UPDATE user_sessions
                    SET is_active = FALSE
                    WHERE session_id = oldest_session_id;
                    
                    RAISE NOTICE 'Deactivated old session % for user %', 
                        oldest_session_id, NEW.user_id;
                END IF;
            END LOOP;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-----------------------------------------
-- Role Management Triggers
-----------------------------------------

-- Validate role assignments before insertion with more robust handling
CREATE OR REPLACE FUNCTION validate_role_assignment()
RETURNS TRIGGER AS $$
BEGIN
    -- Only perform validation if both tables exist
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'role_master'
    ) THEN
        -- Verify user exists
        IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = NEW.user_id) THEN
            RAISE EXCEPTION 'Cannot assign role to non-existent user %', NEW.user_id;
        END IF;
        
        -- Verify role exists
        IF NOT EXISTS (SELECT 1 FROM role_master WHERE role_id = NEW.role_id) THEN
            RAISE EXCEPTION 'Cannot assign non-existent role %', NEW.role_id;
        END IF;
    END IF;
    
    -- All verifications passed (or skipped if tables don't exist)
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Automatically clean up role assignments when user is deleted
CREATE OR REPLACE FUNCTION cleanup_user_roles()
RETURNS TRIGGER AS $$
BEGIN
    -- Only attempt cleanup if the mapping table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_role_mapping'
    ) THEN
        -- Remove all role mappings for this user
        DELETE FROM user_role_mapping
        WHERE user_id = OLD.user_id;
        
        RAISE NOTICE 'Removed role mappings for deleted user %', OLD.user_id;
    END IF;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-----------------------------------------
-- Encryption Flag Triggers
-----------------------------------------

-- Flag records that need encryption (actual encryption happens in application)
CREATE OR REPLACE FUNCTION flag_fields_for_encryption()
RETURNS TRIGGER AS $$
DECLARE
    hospital_encryption_enabled BOOLEAN := TRUE; -- Default to TRUE
BEGIN
    -- For patient records, check hospital encryption setting if hospitals table exists
    IF TG_TABLE_NAME = 'patients' AND EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'hospitals'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'hospitals' AND column_name = 'encryption_enabled'
    ) THEN
        -- Check if encryption is enabled for this hospital
        BEGIN
            SELECT encryption_enabled INTO hospital_encryption_enabled
            FROM hospitals
            WHERE hospital_id = NEW.hospital_id;
        EXCEPTION WHEN OTHERS THEN
            -- On any error, default to TRUE for security
            hospital_encryption_enabled := TRUE;
        END;
    END IF;
    
    -- Flag fields needing encryption if enabled
    IF hospital_encryption_enabled = TRUE THEN
        -- We'll use a metadata column to indicate encryption needed
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'patients' AND column_name = 'needs_encryption'
        ) THEN
            NEW.needs_encryption = TRUE;
            RAISE NOTICE 'Flagged patient % for encryption', NEW.patient_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

-----------------------------------------
-- TRIGGER APPLICATION SECTION
-----------------------------------------

-- Apply basic audit triggers to all schemas
SELECT create_audit_triggers_all_schemas();

-- Apply specific triggers for tables that might exist
DO $
BEGIN
    -- 1. Apply authentication triggers to login_history table if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'login_history'
    ) THEN
        -- Apply failed login tracking
        DROP TRIGGER IF EXISTS track_failed_logins ON login_history;
        CREATE TRIGGER track_failed_logins
        AFTER INSERT ON login_history
        FOR EACH ROW
        WHEN (NEW.status = 'failed')
        EXECUTE FUNCTION update_failed_login_attempts();
        
        -- Apply successful login tracking
        DROP TRIGGER IF EXISTS track_successful_logins ON login_history;
        CREATE TRIGGER track_successful_logins
        AFTER INSERT ON login_history
        FOR EACH ROW
        WHEN (NEW.status = 'success')
        EXECUTE FUNCTION update_on_successful_login();
        
        RAISE NOTICE 'Applied authentication triggers to login_history table';
    ELSE
        RAISE NOTICE 'login_history table does not exist - skipping related triggers';
    END IF;
    
    -- 2. Apply user account triggers to users table if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users'
    ) THEN
        -- Apply account lockout trigger
        DROP TRIGGER IF EXISTS check_account_lockout ON users;
        CREATE TRIGGER check_account_lockout
        BEFORE UPDATE ON users
        FOR EACH ROW
        WHEN (NEW.failed_login_attempts IS DISTINCT FROM OLD.failed_login_attempts)
        EXECUTE FUNCTION check_account_lockout();
        
        -- Apply password hashing trigger
        DROP TRIGGER IF EXISTS hash_password ON users;
        CREATE TRIGGER hash_password
        BEFORE INSERT OR UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION hash_password();
        
        -- Add cascade delete trigger for user roles
        IF EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'user_role_mapping'
        ) THEN
            DROP TRIGGER IF EXISTS cleanup_user_roles ON users;
            CREATE TRIGGER cleanup_user_roles
            AFTER DELETE ON users
            FOR EACH ROW
            EXECUTE FUNCTION cleanup_user_roles();
            
            RAISE NOTICE 'Added cascade delete trigger for user roles';
        END IF;
        
        RAISE NOTICE 'Applied user account triggers to users table';
    ELSE
        RAISE NOTICE 'users table does not exist - skipping related triggers';
    END IF;
    
    -- 3. Apply session management triggers to user_sessions table if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_sessions'
    ) THEN
        -- Apply session expiration check
        DROP TRIGGER IF EXISTS check_session_expiration ON user_sessions;
        CREATE TRIGGER check_session_expiration
        BEFORE UPDATE ON user_sessions
        FOR EACH ROW
        EXECUTE FUNCTION check_session_expiration();
        
        -- Apply logout tracking
        DROP TRIGGER IF EXISTS track_logout ON user_sessions;
        CREATE TRIGGER track_logout
        AFTER UPDATE ON user_sessions
        FOR EACH ROW
        WHEN (OLD.is_active = TRUE AND NEW.is_active = FALSE)
        EXECUTE FUNCTION update_login_history_on_logout();
        
        -- Apply session limits
        DROP TRIGGER IF EXISTS manage_session_limits ON user_sessions;
        CREATE TRIGGER manage_session_limits
        AFTER INSERT ON user_sessions
        FOR EACH ROW
        EXECUTE FUNCTION manage_session_limits();
        
        RAISE NOTICE 'Applied session management triggers to user_sessions table';
    ELSE
        RAISE NOTICE 'user_sessions table does not exist - skipping related triggers';
    END IF;
    
    -- 4. Apply role validation triggers to user_role_mapping table if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_role_mapping'
    ) THEN
        -- Apply role validation
        DROP TRIGGER IF EXISTS validate_role_assignment ON user_role_mapping;
        CREATE TRIGGER validate_role_assignment
        BEFORE INSERT OR UPDATE ON user_role_mapping
        FOR EACH ROW
        EXECUTE FUNCTION validate_role_assignment();
        
        RAISE NOTICE 'Applied role validation triggers to user_role_mapping table';
    ELSE
        RAISE NOTICE 'user_role_mapping table does not exist - skipping related triggers';
    END IF;
    
    -- 5. Apply encryption triggers to patients table if it exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'patients'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'patients' AND column_name = 'needs_encryption'
    ) THEN
        -- Apply encryption flagging
        DROP TRIGGER IF EXISTS flag_patient_encryption ON patients;
        CREATE TRIGGER flag_patient_encryption
        BEFORE INSERT OR UPDATE ON patients
        FOR EACH ROW
        EXECUTE FUNCTION flag_fields_for_encryption();
        
        RAISE NOTICE 'Applied encryption triggers to patients table';
    ELSE
        RAISE NOTICE 'patients table or needs_encryption column does not exist - skipping related triggers';
    END IF;
END $;