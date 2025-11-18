-- Verify UUID storage in critical tables
-- This checks if UUIDs are properly stored as UUID type in PostgreSQL

-- 1. Check payment_details table
SELECT
    'payment_details' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN pg_typeof(payment_id) = 'uuid'::regtype THEN 1 END) as uuid_type,
    COUNT(CASE WHEN pg_typeof(payment_id) != 'uuid'::regtype THEN 1 END) as non_uuid_type
FROM payment_details;

-- 2. Check invoice_header table
SELECT
    'invoice_header' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN pg_typeof(invoice_id) = 'uuid'::regtype THEN 1 END) as uuid_type,
    COUNT(CASE WHEN pg_typeof(invoice_id) != 'uuid'::regtype THEN 1 END) as non_uuid_type
FROM invoice_header;

-- 3. Check ar_subledger table
SELECT
    'ar_subledger' as table_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN pg_typeof(entry_id) = 'uuid'::regtype THEN 1 END) as uuid_type,
    COUNT(CASE WHEN pg_typeof(entry_id) != 'uuid'::regtype THEN 1 END) as non_uuid_type
FROM ar_subledger;

-- 4. Sample payment IDs to check actual storage
SELECT
    payment_id,
    pg_typeof(payment_id) as payment_id_type,
    invoice_id,
    pg_typeof(invoice_id) as invoice_id_type,
    total_amount,
    created_at
FROM payment_details
ORDER BY created_at DESC
LIMIT 5;

-- 5. Check if any UUIDs have invalid format (shouldn't happen with uuid type)
SELECT COUNT(*) as invalid_uuids
FROM payment_details
WHERE payment_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
