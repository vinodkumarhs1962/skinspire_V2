-- Migration: Add package_id reference to package_payment_plans
-- Date: 2025-01-11
-- Purpose: Fix fundamental architecture - reference packages table instead of duplicating data

-- ============================================================================
-- STEP 1: Add package_id column
-- ============================================================================

ALTER TABLE package_payment_plans
ADD COLUMN package_id UUID;

-- Add foreign key constraint
ALTER TABLE package_payment_plans
ADD CONSTRAINT package_payment_plans_package_id_fkey
FOREIGN KEY (package_id) REFERENCES packages(package_id) ON DELETE RESTRICT;

-- Add index for performance
CREATE INDEX idx_package_plans_package ON package_payment_plans(package_id);

-- ============================================================================
-- STEP 2: Make duplicate fields nullable (for transition period)
-- ============================================================================

-- These fields should eventually be removed after data migration
ALTER TABLE package_payment_plans
ALTER COLUMN package_name DROP NOT NULL;

COMMENT ON COLUMN package_payment_plans.package_id IS 'Foreign key to packages table - PRIMARY reference';
COMMENT ON COLUMN package_payment_plans.package_name IS 'DEPRECATED: Use package_id to lookup package details from packages table';
COMMENT ON COLUMN package_payment_plans.package_description IS 'DEPRECATED: Use package_id to lookup package details from packages table';
COMMENT ON COLUMN package_payment_plans.package_code IS 'DEPRECATED: Use package_id to lookup package details from packages table';

-- ============================================================================
-- STEP 3: Data Migration (if any existing records exist)
-- ============================================================================

-- For existing records, you would need to:
-- 1. Match package_name to packages.package_name
-- 2. Update package_id based on match
-- Example (customize based on your data):
-- UPDATE package_payment_plans ppp
-- SET package_id = p.package_id
-- FROM packages p
-- WHERE ppp.package_name = p.package_name
-- AND ppp.hospital_id = p.hospital_id
-- AND ppp.package_id IS NULL;

-- ============================================================================
-- STEP 4: Make package_id required (after data migration)
-- ============================================================================

-- IMPORTANT: Only run this after ensuring all existing records have package_id populated
-- ALTER TABLE package_payment_plans
-- ALTER COLUMN package_id SET NOT NULL;

-- ============================================================================
-- STEP 5: (Optional - Future) Remove deprecated fields
-- ============================================================================

-- After sufficient transition period and confirming all code uses package_id:
-- ALTER TABLE package_payment_plans DROP COLUMN package_name;
-- ALTER TABLE package_payment_plans DROP COLUMN package_description;
-- ALTER TABLE package_payment_plans DROP COLUMN package_code;

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check structure
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'package_payment_plans'
AND column_name IN ('package_id', 'package_name', 'package_description', 'package_code')
ORDER BY ordinal_position;

-- Check foreign key constraint
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_name = 'package_payment_plans'
AND tc.constraint_type = 'FOREIGN KEY'
AND kcu.column_name = 'package_id';

-- Check index
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'package_payment_plans'
AND indexname LIKE '%package%';
