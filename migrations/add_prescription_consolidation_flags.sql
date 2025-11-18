-- Migration: Add Prescription Consolidation Flags to invoice_line_item
-- Purpose: Enable storage of individual prescription items while supporting
--          conditional consolidated printing based on hospital drug license
-- Date: 2025-11-08
-- Author: Claude Code

-- Add new columns to invoice_line_item table
ALTER TABLE invoice_line_item
ADD COLUMN IF NOT EXISTS is_prescription_item BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS consolidation_group_id UUID,
ADD COLUMN IF NOT EXISTS print_as_consolidated BOOLEAN DEFAULT FALSE;

-- Add index for faster querying of prescription items
CREATE INDEX IF NOT EXISTS idx_invoice_line_item_prescription
ON invoice_line_item(is_prescription_item)
WHERE is_prescription_item = TRUE;

-- Add index for consolidation group queries
CREATE INDEX IF NOT EXISTS idx_invoice_line_item_consolidation_group
ON invoice_line_item(consolidation_group_id)
WHERE consolidation_group_id IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN invoice_line_item.is_prescription_item IS
'Marks items that are prescription medicines (PRESCRIPTION_COMPOSITE category). Used to identify items that may need consolidated printing.';

COMMENT ON COLUMN invoice_line_item.consolidation_group_id IS
'Groups multiple line items that should be printed as a single consolidated line (e.g., "Doctor''s Examination and Treatment"). All prescription items in one invoice share the same consolidation_group_id.';

COMMENT ON COLUMN invoice_line_item.print_as_consolidated IS
'Snapshot flag indicating if these items should print as consolidated service. Set based on hospital drug registration status at invoice creation time. TRUE = hospital has no drug license, print consolidated. FALSE = hospital has license, print individual items.';

-- Migration verification query
-- Run this to verify the migration was successful
-- SELECT
--     column_name,
--     data_type,
--     is_nullable,
--     column_default
-- FROM information_schema.columns
-- WHERE table_name = 'invoice_line_item'
-- AND column_name IN ('is_prescription_item', 'consolidation_group_id', 'print_as_consolidated')
-- ORDER BY column_name;
