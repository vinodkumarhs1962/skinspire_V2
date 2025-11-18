-- Migration: Add split invoice tracking fields to invoice_header
-- Purpose: Enable tracking of related invoices created from batch/GST splitting
-- Author: Claude Code
-- Date: 2025-01-06

-- Add parent_transaction_id to link related split invoices
ALTER TABLE invoice_header
ADD COLUMN parent_transaction_id UUID NULL;

-- Add split_sequence to track order of split invoices (1, 2, 3...)
ALTER TABLE invoice_header
ADD COLUMN split_sequence INTEGER NULL DEFAULT 1;

-- Add is_split_invoice flag to identify split invoices
ALTER TABLE invoice_header
ADD COLUMN is_split_invoice BOOLEAN DEFAULT FALSE;

-- Add split_reason to document why invoice was split
ALTER TABLE invoice_header
ADD COLUMN split_reason VARCHAR(100) NULL;

-- Add foreign key constraint for parent_transaction_id (self-referencing)
ALTER TABLE invoice_header
ADD CONSTRAINT fk_invoice_parent_transaction
FOREIGN KEY (parent_transaction_id)
REFERENCES invoice_header(invoice_id)
ON DELETE SET NULL;

-- Create index for efficient querying of related split invoices
CREATE INDEX idx_invoice_parent_transaction
ON invoice_header(parent_transaction_id)
WHERE parent_transaction_id IS NOT NULL;

-- Create index for querying all split invoices
CREATE INDEX idx_invoice_is_split
ON invoice_header(is_split_invoice)
WHERE is_split_invoice = TRUE;

-- Add comment to explain the parent_transaction_id field
COMMENT ON COLUMN invoice_header.parent_transaction_id IS
'Links to parent invoice_id when this invoice was created as part of a split (batch allocation, GST separation, etc.)';

COMMENT ON COLUMN invoice_header.split_sequence IS
'Order of this invoice in the split sequence (1 = first, 2 = second, etc.)';

COMMENT ON COLUMN invoice_header.split_reason IS
'Reason for splitting: BATCH_ALLOCATION, GST_SPLIT, PRESCRIPTION_CONSOLIDATION, etc.';

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'invoice_header'
  AND column_name IN ('parent_transaction_id', 'split_sequence', 'is_split_invoice', 'split_reason')
ORDER BY column_name;
