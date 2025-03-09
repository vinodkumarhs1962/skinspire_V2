DROP TRIGGER IF EXISTS user_password_hash ON users;     

-- Lists triggers on the users table
SELECT 
    trigger_name,
    event_manipulation AS event,
    action_statement AS function_called
FROM 
    information_schema.triggers
WHERE 
    event_object_table = 'users'
ORDER BY 
    trigger_name;

----
SELECT * FROM pg_extension WHERE extname = 'pgcrypto';

----
-- Check if any tables are missing standard audit triggers
SELECT 
    t.table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = t.table_name AND column_name = 'updated_at'
    ) THEN 'Yes' ELSE 'No' END AS has_updated_at_column,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.triggers 
        WHERE event_object_schema = 'public' AND event_object_table = t.table_name AND trigger_name = 'update_timestamp'
    ) THEN 'Yes' ELSE 'No' END AS has_timestamp_trigger
FROM 
    information_schema.tables t
WHERE 
    table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = t.table_name AND column_name = 'updated_at'
    )
ORDER BY 
    table_name;

------


-- Check structure of key tables
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public' 
    AND table_name = 'users'
ORDER BY 
    ordinal_position;

----
-- Lists all trigger functions in the database
SELECT 
    n.nspname AS schema,
    p.proname AS function_name,
    pg_get_function_arguments(p.oid) AS arguments,
    CASE WHEN p.prorettype::regtype::text = 'trigger' THEN 'Is Trigger' ELSE 'Not Trigger' END AS is_trigger
FROM 
    pg_proc p
JOIN 
    pg_namespace n ON p.pronamespace = n.oid
WHERE 
    n.nspname = 'public'
    AND pg_get_function_result(p.oid) = 'trigger'
ORDER BY 
    function_name;

-------
-- Lists triggers on the users table
SELECT 
    trigger_name,
    event_manipulation AS event,
    action_statement AS function_called
FROM 
    information_schema.triggers
WHERE 
    event_object_table = 'users'
ORDER BY 
    trigger_name;

------
-- Lists all triggers and the functions they use
SELECT 
    event_object_schema AS schema,
    event_object_table AS table_name,
    trigger_name,
    action_statement AS trigger_function
FROM 
    information_schema.triggers
ORDER BY 
    schema, table_name, trigger_name;

-----
-- Lists all tables in the public schema
SELECT 
    table_name, 
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) AS column_count
FROM 
    information_schema.tables t
WHERE 
    table_schema = 'public' 
    AND table_type = 'BASE TABLE'
ORDER BY 
    table_name;

------
--list all triggers
SELECT * FROM pg_trigger;
-----

-- Insert a test user with all required fields
INSERT INTO users (
    user_id, 
    hospital_id, 
    entity_type, 
    entity_id, 
    is_active, 
    password_hash, 
    created_at,            -- Add the required timestamp field
    updated_at             -- Add this if also required
) 
VALUES (
    'test_trigger',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca',  -- Replace with actual hospital_id
    'staff', 
    '11111111-1111-1111-1111-111111111111',  -- Proper UUID format for entity_id
    true, 
    'password',
    CURRENT_TIMESTAMP,     -- Current timestamp for created_at
    CURRENT_TIMESTAMP      -- Current timestamp for updated_at
);

-----

