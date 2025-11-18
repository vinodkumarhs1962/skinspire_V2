-- Migration: Add Line Item Reference to AR Subledger
-- Date: 2025-11-12
-- Purpose: Enable line-item level payment tracking for service-first allocation rule

-- Add reference to invoice line item for detailed payment tracking
ALTER TABLE ar_subledger
ADD COLUMN reference_line_item_id UUID;

-- Add foreign key constraint
ALTER TABLE ar_subledger
ADD CONSTRAINT fk_ar_subledger_line_item
FOREIGN KEY (reference_line_item_id)
REFERENCES invoice_line_item(line_item_id)
ON DELETE SET NULL;

-- Add index for performance (only for non-null values)
CREATE INDEX idx_ar_subledger_line_item
ON ar_subledger(reference_line_item_id)
WHERE reference_line_item_id IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN ar_subledger.reference_line_item_id IS
'Reference to specific invoice line item for payment allocation tracking. Enables service-first payment allocation rule where services are paid before packages in mixed invoices.';

-- Verify the change
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'ar_subledger'
  AND column_name = 'reference_line_item_id';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE 'Added reference_line_item_id column to ar_subledger table';
    RAISE NOTICE 'Created index idx_ar_subledger_line_item';
END $$;
