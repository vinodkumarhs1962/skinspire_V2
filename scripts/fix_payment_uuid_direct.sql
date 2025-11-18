-- Fix UUID corruption in payment_details table
-- This deletes payment records that have string-typed UUIDs instead of proper UUID types

BEGIN;

-- First, check how many records will be deleted
SELECT COUNT(*) AS corrupted_count
FROM payment_details
WHERE pg_typeof(payment_id::text) = pg_typeof('text'::text)
   OR payment_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Show the corrupted records before deletion
SELECT payment_id, invoice_id, payment_date, total_amount, workflow_status
FROM payment_details
WHERE pg_typeof(payment_id::text) = pg_typeof('text'::text)
   OR payment_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Delete the corrupted records
DELETE FROM payment_details
WHERE pg_typeof(payment_id::text) = pg_typeof('text'::text)
   OR payment_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

-- Verify deletion
SELECT COUNT(*) AS remaining_corrupted
FROM payment_details
WHERE pg_typeof(payment_id::text) = pg_typeof('text'::text)
   OR payment_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

COMMIT;
