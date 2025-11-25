-- Migration: Add Discount Fields to Medicine Table
-- Date: 21-Nov-2025
-- Description: Extends medicine table to support bulk and standard discounts like services

-- ============================================================================
-- 1. ADD DISCOUNT COLUMNS TO MEDICINE TABLE
-- ============================================================================

-- Add standard discount percentage (fallback when no other discounts apply)
ALTER TABLE medicines
ADD COLUMN IF NOT EXISTS standard_discount_percent NUMERIC(5,2) DEFAULT 0
CHECK (standard_discount_percent >= 0 AND standard_discount_percent <= 100);

-- Add bulk discount percentage (when quantity >= threshold)
ALTER TABLE medicines
ADD COLUMN IF NOT EXISTS bulk_discount_percent NUMERIC(5,2) DEFAULT 0
CHECK (bulk_discount_percent >= 0 AND bulk_discount_percent <= 100);

-- Add maximum discount cap (ensures discounts don't exceed this limit)
ALTER TABLE medicines
ADD COLUMN IF NOT EXISTS max_discount NUMERIC(5,2)
CHECK (max_discount IS NULL OR (max_discount >= 0 AND max_discount <= 100));

-- ============================================================================
-- 2. COLUMN COMMENTS (for documentation)
-- ============================================================================

COMMENT ON COLUMN medicines.standard_discount_percent IS 'Default discount percentage for this medicine (fallback when no other discounts)';
COMMENT ON COLUMN medicines.bulk_discount_percent IS 'Bulk purchase discount percentage (applies when total medicine quantity >= hospital threshold)';
COMMENT ON COLUMN medicines.max_discount IS 'Maximum allowed discount percentage (cap for all discount types). NULL means no cap.';

-- ============================================================================
-- 3. SAMPLE DATA (optional - for testing)
-- ============================================================================

-- Example 1: Medicine with standard discount only
-- UPDATE medicines
-- SET standard_discount_percent = 5.00,
--     max_discount = 10.00
-- WHERE medicine_name = 'Paracetamol 500mg';

-- Example 2: Medicine with bulk discount
-- UPDATE medicines
-- SET bulk_discount_percent = 15.00,
--     max_discount = 20.00
-- WHERE medicine_name = 'Vitamin D3';

-- Example 3: Medicine with no discounts allowed
-- UPDATE medicines
-- SET standard_discount_percent = 0,
--     bulk_discount_percent = 0,
--     max_discount = 0
-- WHERE medicine_name = 'Prescription Antibiotic';

-- ============================================================================
-- 4. VERIFICATION QUERIES
-- ============================================================================

-- Check that columns were added
SELECT
    column_name,
    data_type,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'medicines'
  AND column_name IN ('standard_discount_percent', 'bulk_discount_percent', 'max_discount')
ORDER BY ordinal_position;

-- Sample: View medicines with discount fields
SELECT
    medicine_id,
    medicine_name,
    standard_discount_percent,
    bulk_discount_percent,
    max_discount,
    selling_price
FROM medicines
WHERE is_active = TRUE
LIMIT 10;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Next steps:
-- 1. Execute migration: psql -U <user> -d <database> -f 20251121_add_medicine_discount_fields.sql
-- 2. Verify columns: \d medicines
-- 3. Update discount_service.py to handle medicine discounts
-- 4. Update frontend to display medicine discounts

-- Rollback (if needed):
-- ALTER TABLE medicines DROP COLUMN IF EXISTS standard_discount_percent;
-- ALTER TABLE medicines DROP COLUMN IF EXISTS bulk_discount_percent;
-- ALTER TABLE medicines DROP COLUMN IF EXISTS max_discount;
