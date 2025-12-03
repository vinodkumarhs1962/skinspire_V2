-- Migration: Add Sample/Trial Item Support to Invoice Line Items
-- Date: 2025-12-02
-- Purpose: Track free samples (products/services) given to patients
--          - No GST impact (unlike promotional free items)
--          - Inventory still tracked for products
--          - Service usage still tracked
--          - Doctor authorization required

-- Add sample-related columns to invoice_line_item table
ALTER TABLE invoice_line_item
ADD COLUMN IF NOT EXISTS is_sample BOOLEAN DEFAULT FALSE;

-- Note: sample_authorized_by is VARCHAR(15) to match users.user_id type
ALTER TABLE invoice_line_item
ADD COLUMN IF NOT EXISTS sample_authorized_by VARCHAR(15) REFERENCES users(user_id);

ALTER TABLE invoice_line_item
ADD COLUMN IF NOT EXISTS sample_reason VARCHAR(200);

-- Add comment for documentation
COMMENT ON COLUMN invoice_line_item.is_sample IS 'True if this is a sample/trial item - no GST charged';
COMMENT ON COLUMN invoice_line_item.sample_authorized_by IS 'Doctor/user who authorized the sample';
COMMENT ON COLUMN invoice_line_item.sample_reason IS 'Reason for sample e.g. Trial for new treatment, Product sample';

-- Create index for sample item queries and reporting
CREATE INDEX IF NOT EXISTS idx_invoice_line_item_is_sample
ON invoice_line_item(is_sample) WHERE is_sample = TRUE;

CREATE INDEX IF NOT EXISTS idx_invoice_line_item_sample_authorized_by
ON invoice_line_item(sample_authorized_by) WHERE sample_authorized_by IS NOT NULL;

-- Verification query
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'invoice_line_item'
AND column_name IN ('is_sample', 'sample_authorized_by', 'sample_reason')
ORDER BY ordinal_position;
