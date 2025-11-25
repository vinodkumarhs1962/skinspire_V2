-- Add Essential Package Fields
-- Migration: 20251118164500_add_package_essential_fields
-- Created: 2025-11-18

-- Add package_code column
ALTER TABLE packages
ADD COLUMN IF NOT EXISTS package_code VARCHAR(50);

COMMENT ON COLUMN packages.package_code IS 'Unique code for search and autocomplete';

-- Add selling_price column
ALTER TABLE packages
ADD COLUMN IF NOT EXISTS selling_price NUMERIC(10, 2);

COMMENT ON COLUMN packages.selling_price IS 'Actual selling price (can differ from base price)';

-- Add hsn_code column
ALTER TABLE packages
ADD COLUMN IF NOT EXISTS hsn_code VARCHAR(10);

COMMENT ON COLUMN packages.hsn_code IS 'HSN/SAC code for GST compliance';

-- Create index on package_code for faster searches
CREATE INDEX IF NOT EXISTS idx_packages_package_code ON packages(package_code);

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 20251118164500 applied successfully - Added package_code, selling_price, hsn_code';
END $$;
