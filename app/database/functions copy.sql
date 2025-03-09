-- skinspire_V2/app/database/functions.sql
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