-- core_trigger_functions.sql
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

-- Password hashing function - DISABLED in favor of Werkzeug hashing in Python
-- Keeping the function definition for backward compatibility
CREATE OR REPLACE FUNCTION hash_password()
RETURNS TRIGGER AS $$
BEGIN
    -- This function is now disabled as password hashing is handled by the Python application
    -- using Werkzeug's password hashing functions instead of database triggers
    RAISE NOTICE 'Password hash trigger called but disabled - using Werkzeug hashing instead';
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    -- Fail gracefully
    RAISE WARNING 'Error in hash_password trigger: %', SQLERRM;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;