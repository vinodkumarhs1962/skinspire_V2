-- ============================================================================
-- Update Inventory Expiry Year Script
-- ============================================================================
-- Purpose: Change all inventory records with expiry year 2025 to 2026
--
-- Usage:
--   1. Review changes (DRY RUN):
--      Run SELECT queries below to see what will change
--
--   2. Apply changes:
--      Uncomment and run UPDATE statement
--
-- IMPORTANT: Take database backup before running UPDATE!
-- ============================================================================

-- ============================================================================
-- STEP 1: PREVIEW CHANGES (DRY RUN)
-- ============================================================================

-- Summary of records to be updated
SELECT
    medicine_name,
    batch,
    expiry AS old_expiry,
    (expiry + INTERVAL '1 year')::date AS new_expiry,
    COUNT(*) AS transaction_count,
    SUM(current_stock) AS total_stock,
    MIN(transaction_date) AS earliest_transaction,
    MAX(transaction_date) AS latest_transaction
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025
GROUP BY medicine_name, batch, expiry
ORDER BY medicine_name, batch;

-- Total count of records to update
SELECT
    COUNT(*) AS total_records_to_update,
    COUNT(DISTINCT medicine_id) AS unique_medicines,
    COUNT(DISTINCT batch) AS unique_batches
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- ============================================================================
-- STEP 2: BACKUP RECOMMENDATION
-- ============================================================================
-- Before running UPDATE, create a backup:
--
-- Option 1: Backup entire database
--   pg_dump -h localhost -U postgres -d skinspire_dev > backup_before_expiry_update.sql
--
-- Option 2: Backup only inventory table
--   pg_dump -h localhost -U postgres -d skinspire_dev -t inventory > inventory_backup.sql
--
-- Option 3: Create backup table
--   CREATE TABLE inventory_backup_20250109 AS SELECT * FROM inventory WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- ============================================================================
-- STEP 3: CREATE BACKUP TABLE (RECOMMENDED)
-- ============================================================================
CREATE TABLE IF NOT EXISTS inventory_backup_20250109 AS
SELECT * FROM inventory WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- Verify backup
SELECT COUNT(*) AS backed_up_records FROM inventory_backup_20250109;

-- ============================================================================
-- STEP 4: APPLY CHANGES
-- ============================================================================
-- IMPORTANT: Review preview results above before uncommenting!

-- BEGIN TRANSACTION for safety
BEGIN;

-- Update expiry year from 2025 to 2026
UPDATE inventory
SET
    expiry = (expiry + INTERVAL '1 year')::date,
    updated_at = CURRENT_TIMESTAMP
WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- Verify changes
SELECT
    COUNT(*) AS updated_records,
    MIN(expiry) AS earliest_new_expiry,
    MAX(expiry) AS latest_new_expiry
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2026
  AND updated_at > (CURRENT_TIMESTAMP - INTERVAL '1 minute');

-- If everything looks good, commit:
-- COMMIT;

-- If something went wrong, rollback:
-- ROLLBACK;

-- ============================================================================
-- STEP 5: VERIFICATION AFTER UPDATE
-- ============================================================================

-- Verify no more 2025 expiry dates exist
SELECT COUNT(*) AS remaining_2025_records
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025;
-- Should return 0

-- Verify 2026 records were created
SELECT
    medicine_name,
    batch,
    expiry,
    COUNT(*) AS transaction_count
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2026
GROUP BY medicine_name, batch, expiry
ORDER BY medicine_name, batch;

-- ============================================================================
-- STEP 6: CLEANUP (OPTIONAL)
-- ============================================================================
-- After verifying update is successful, you can drop the backup table:
-- DROP TABLE IF EXISTS inventory_backup_20250109;

-- ============================================================================
-- ROLLBACK PROCEDURE (If needed)
-- ============================================================================
-- If you need to restore from backup:
/*
BEGIN;

-- Restore from backup table
UPDATE inventory i
SET
    expiry = b.expiry,
    updated_at = b.updated_at
FROM inventory_backup_20250109 b
WHERE i.stock_id = b.stock_id;

COMMIT;
*/

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. This script uses INTERVAL '1 year' to add exactly one year to the date
-- 2. The ::date cast ensures the result is a DATE type
-- 3. Transaction is wrapped in BEGIN/COMMIT for safety
-- 4. Always verify in DRY RUN mode first
-- 5. Keep backup table until you're certain the update is correct
-- ============================================================================
