-- Migration: Add barcode field to medicines table
-- Date: 2025-12-03
-- Purpose: Store GTIN/barcode for barcode scanner integration
--
-- This migration adds an optional barcode field to the medicines table.
-- The field stores the GTIN (Global Trade Item Number) which is unique per
-- manufacturer + product + pack size combination.
--
-- NOTE: Field is nullable - existing medicines work without barcode
-- NOTE: No unique constraint initially - allows gradual population

-- Add barcode column
ALTER TABLE medicines ADD COLUMN IF NOT EXISTS barcode VARCHAR(50);

-- Create index for fast lookup by barcode
CREATE INDEX IF NOT EXISTS idx_medicines_barcode ON medicines(barcode);

-- Add comment for documentation
COMMENT ON COLUMN medicines.barcode IS 'GTIN/barcode for scanner integration. Unique per manufacturer+product+pack.';

-- Verification query (run manually to verify)
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'medicines' AND column_name = 'barcode';
