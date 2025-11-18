-- ============================================================================
-- COMPLETE Expiry Year Update Script - All Inward Inventory Tables
-- ============================================================================
-- Purpose: Update expiry dates in ALL tables related to inward inventory
--
-- Tables Updated:
--   1. supplier_invoice_line - Supplier invoice line items (PRIMARY - INWARD)
--   2. inventory - Inventory movements (PRIMARY - INWARD)
--   3. invoice_line_item - Patient invoice line items (REFERENCE - OUTWARD)
--   4. prescription_invoice_maps - Prescription mappings (REFERENCE)
--
-- IMPORTANT: Take database backup before running UPDATE!
-- ============================================================================

\echo '============================================================================'
\echo 'COMPLETE Expiry Year Update - Preview Mode'
\echo '============================================================================'

-- ============================================================================
-- STEP 1: PREVIEW CHANGES - supplier_invoice_line (PRIMARY - INWARD INVENTORY)
-- ============================================================================
\echo ''
\echo '🔴 PRIMARY TABLE 1: supplier_invoice_line (Supplier Invoices - INWARD)'
\echo '----------------------------------------------------------------------------'

SELECT
    'supplier_invoice_line' AS table_name,
    medicine_name,
    batch_number AS batch,
    expiry_date AS old_expiry,
    (expiry_date + INTERVAL '1 year')::date AS new_expiry,
    COUNT(*) AS line_count
FROM supplier_invoice_line
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND (is_deleted IS NULL OR is_deleted = FALSE)
GROUP BY medicine_name, batch_number, expiry_date
ORDER BY medicine_name, batch_number;

-- Count
SELECT COUNT(*) AS total_supplier_invoice_lines
FROM supplier_invoice_line
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND (is_deleted IS NULL OR is_deleted = FALSE);

-- ============================================================================
-- STEP 2: PREVIEW CHANGES - inventory (PRIMARY - INVENTORY MOVEMENTS)
-- ============================================================================
\echo ''
\echo '🔴 PRIMARY TABLE 2: inventory (Inventory Movements)'
\echo '----------------------------------------------------------------------------'

SELECT
    'inventory' AS table_name,
    medicine_name,
    batch,
    expiry AS old_expiry,
    (expiry + INTERVAL '1 year')::date AS new_expiry,
    COUNT(*) AS transaction_count,
    SUM(current_stock) AS total_stock
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025
GROUP BY medicine_name, batch, expiry
ORDER BY medicine_name, batch;

-- Count
SELECT COUNT(*) AS total_inventory_records
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- ============================================================================
-- STEP 3: PREVIEW CHANGES - invoice_line_item (REFERENCE - PATIENT INVOICES)
-- ============================================================================
\echo ''
\echo '🔵 REFERENCE TABLE 1: invoice_line_item (Patient Invoices - OUTWARD)'
\echo '----------------------------------------------------------------------------'

SELECT
    'invoice_line_item' AS table_name,
    item_name,
    batch AS batch,
    expiry_date AS old_expiry,
    (expiry_date + INTERVAL '1 year')::date AS new_expiry,
    COUNT(*) AS line_count
FROM invoice_line_item
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND expiry_date IS NOT NULL
GROUP BY item_name, batch, expiry_date
ORDER BY item_name, batch;

-- Count
SELECT COUNT(*) AS total_invoice_line_items
FROM invoice_line_item
WHERE EXTRACT(YEAR FROM expiry_date) = 2025;

-- ============================================================================
-- STEP 4: PREVIEW CHANGES - prescription_invoice_maps (REFERENCE)
-- ============================================================================
\echo ''
\echo '🔵 REFERENCE TABLE 2: prescription_invoice_maps (Prescription Maps)'
\echo '----------------------------------------------------------------------------'

SELECT
    'prescription_invoice_maps' AS table_name,
    medicine_name,
    batch,
    expiry_date AS old_expiry,
    (expiry_date + INTERVAL '1 year')::date AS new_expiry,
    COUNT(*) AS map_count
FROM prescription_invoice_maps
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND expiry_date IS NOT NULL
GROUP BY medicine_name, batch, expiry_date
ORDER BY medicine_name, batch;

-- Count
SELECT COUNT(*) AS total_prescription_maps
FROM prescription_invoice_maps
WHERE EXTRACT(YEAR FROM expiry_date) = 2025;

-- ============================================================================
-- SUMMARY OF ALL TABLES
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'SUMMARY - Total records to update across all tables'
\echo '============================================================================'

SELECT
    '🔴 supplier_invoice_line' AS table_name,
    COUNT(*) AS record_count,
    'PRIMARY - Inward Inventory' AS note
FROM supplier_invoice_line
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND (is_deleted IS NULL OR is_deleted = FALSE)

UNION ALL

SELECT
    '🔴 inventory' AS table_name,
    COUNT(*) AS record_count,
    'PRIMARY - Inventory Movements' AS note
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025

UNION ALL

SELECT
    '🔵 invoice_line_item' AS table_name,
    COUNT(*) AS record_count,
    'REFERENCE - Patient Invoices' AS note
FROM invoice_line_item
WHERE EXTRACT(YEAR FROM expiry_date) = 2025

UNION ALL

SELECT
    '🔵 prescription_invoice_maps' AS table_name,
    COUNT(*) AS record_count,
    'REFERENCE - Prescription Maps' AS note
FROM prescription_invoice_maps
WHERE EXTRACT(YEAR FROM expiry_date) = 2025;

-- ============================================================================
-- STEP 5: CREATE BACKUP TABLES
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'Creating backup tables...'
\echo '============================================================================'

-- Backup supplier_invoice_line
DROP TABLE IF EXISTS supplier_invoice_line_backup_20250109;
CREATE TABLE supplier_invoice_line_backup_20250109 AS
SELECT * FROM supplier_invoice_line
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND (is_deleted IS NULL OR is_deleted = FALSE);

-- Backup inventory
DROP TABLE IF EXISTS inventory_backup_20250109;
CREATE TABLE inventory_backup_20250109 AS
SELECT * FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- Backup invoice_line_item
DROP TABLE IF EXISTS invoice_line_item_backup_20250109;
CREATE TABLE invoice_line_item_backup_20250109 AS
SELECT * FROM invoice_line_item
WHERE EXTRACT(YEAR FROM expiry_date) = 2025;

-- Backup prescription_invoice_maps
DROP TABLE IF EXISTS prescription_invoice_maps_backup_20250109;
CREATE TABLE prescription_invoice_maps_backup_20250109 AS
SELECT * FROM prescription_invoice_maps
WHERE EXTRACT(YEAR FROM expiry_date) = 2025;

-- Verify backups
SELECT 'supplier_invoice_line_backup' AS backup_table, COUNT(*) FROM supplier_invoice_line_backup_20250109
UNION ALL
SELECT 'inventory_backup', COUNT(*) FROM inventory_backup_20250109
UNION ALL
SELECT 'invoice_line_item_backup', COUNT(*) FROM invoice_line_item_backup_20250109
UNION ALL
SELECT 'prescription_invoice_maps_backup', COUNT(*) FROM prescription_invoice_maps_backup_20250109;

-- ============================================================================
-- STEP 6: APPLY UPDATES (Uncomment to run)
-- ============================================================================
\echo ''
\echo '============================================================================'
\echo 'Ready to apply updates. Review above and then run UPDATE statements.'
\echo '============================================================================'

-- IMPORTANT: Review all preview results above before uncommenting!

BEGIN;

-- Update 1: supplier_invoice_line (PRIMARY - INWARD INVENTORY)
UPDATE supplier_invoice_line
SET
    expiry_date = (expiry_date + INTERVAL '1 year')::date,
    updated_at = CURRENT_TIMESTAMP
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND (is_deleted IS NULL OR is_deleted = FALSE);

-- Update 2: inventory (PRIMARY - INVENTORY MOVEMENTS)
UPDATE inventory
SET
    expiry = (expiry + INTERVAL '1 year')::date,
    updated_at = CURRENT_TIMESTAMP
WHERE EXTRACT(YEAR FROM expiry) = 2025;

-- Update 3: invoice_line_item (REFERENCE - PATIENT INVOICES)
UPDATE invoice_line_item
SET
    expiry_date = (expiry_date + INTERVAL '1 year')::date,
    updated_at = CURRENT_TIMESTAMP
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND expiry_date IS NOT NULL;

-- Update 4: prescription_invoice_maps (REFERENCE - PRESCRIPTION MAPS)
UPDATE prescription_invoice_maps
SET
    expiry_date = (expiry_date + INTERVAL '1 year')::date,
    updated_at = CURRENT_TIMESTAMP
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
  AND expiry_date IS NOT NULL;

-- Verify updates
\echo ''
\echo 'Verification - Updated records:'
SELECT
    '🔴 supplier_invoice_line' AS table_name,
    COUNT(*) AS updated_count
FROM supplier_invoice_line
WHERE EXTRACT(YEAR FROM expiry_date) = 2026
  AND updated_at > (CURRENT_TIMESTAMP - INTERVAL '1 minute')

UNION ALL

SELECT
    '🔴 inventory',
    COUNT(*)
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2026
  AND updated_at > (CURRENT_TIMESTAMP - INTERVAL '1 minute')

UNION ALL

SELECT
    '🔵 invoice_line_item',
    COUNT(*)
FROM invoice_line_item
WHERE EXTRACT(YEAR FROM expiry_date) = 2026
  AND updated_at > (CURRENT_TIMESTAMP - INTERVAL '1 minute')

UNION ALL

SELECT
    '🔵 prescription_invoice_maps',
    COUNT(*)
FROM prescription_invoice_maps
WHERE EXTRACT(YEAR FROM expiry_date) = 2026
  AND updated_at > (CURRENT_TIMESTAMP - INTERVAL '1 minute');

-- If everything looks good, commit:
-- COMMIT;

-- If something went wrong, rollback:
-- ROLLBACK;

-- ============================================================================
-- POST-UPDATE VERIFICATION
-- ============================================================================
-- Run after COMMIT to verify

-- Should return 0 for all tables
SELECT '2025 check - should be 0' AS check_name,
       'supplier_invoice_line' AS table_name,
       COUNT(*) AS remaining_2025_records
FROM supplier_invoice_line
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
UNION ALL
SELECT '2025 check - should be 0', 'inventory', COUNT(*)
FROM inventory
WHERE EXTRACT(YEAR FROM expiry) = 2025
UNION ALL
SELECT '2025 check - should be 0', 'invoice_line_item', COUNT(*)
FROM invoice_line_item
WHERE EXTRACT(YEAR FROM expiry_date) = 2025
UNION ALL
SELECT '2025 check - should be 0', 'prescription_invoice_maps', COUNT(*)
FROM prescription_invoice_maps
WHERE EXTRACT(YEAR FROM expiry_date) = 2025;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 🔴 PRIMARY tables are critical for inward inventory tracking
-- 🔵 REFERENCE tables updated for consistency
-- Always verify results before COMMIT
-- Keep backup tables until you're certain updates are correct
-- ============================================================================
