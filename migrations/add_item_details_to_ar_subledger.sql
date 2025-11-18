-- Migration: Add item_type and item_name to ar_subledger for better traceability
-- Date: 2025-11-16
-- Purpose: Denormalize item details in AR for faster reporting and historical accuracy

-- Add new columns
ALTER TABLE ar_subledger
ADD COLUMN IF NOT EXISTS item_type VARCHAR(20),
ADD COLUMN IF NOT EXISTS item_name VARCHAR(255);

-- Create index for reporting queries
CREATE INDEX IF NOT EXISTS idx_ar_subledger_item_type ON ar_subledger(item_type);

-- Update existing records by joining with invoice_line_item
UPDATE ar_subledger ar
SET
    item_type = ili.item_type,
    item_name = ili.item_name
FROM invoice_line_item ili
WHERE ar.reference_line_item_id = ili.line_item_id
  AND ar.reference_line_item_id IS NOT NULL
  AND ar.item_type IS NULL;

-- Update package installment entries with descriptive text
UPDATE ar_subledger
SET
    item_type = 'Package',
    item_name = 'Package Installment Payment'
WHERE entry_type = 'package_installment'
  AND reference_line_item_id IS NULL
  AND item_type IS NULL;

-- Add comment
COMMENT ON COLUMN ar_subledger.item_type IS 'Denormalized item type from line item (Service/Medicine/Package) for faster reporting';
COMMENT ON COLUMN ar_subledger.item_name IS 'Denormalized item name from line item for historical accuracy and audit trail';
