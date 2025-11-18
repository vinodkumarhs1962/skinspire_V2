-- =====================================================================
-- Make payment_details.invoice_id NULLABLE for multi-invoice payments
-- Date: 2025-11-15
-- =====================================================================

-- For multi-invoice payments, invoice_id should be NULL
-- The payment-to-invoice relationship is tracked in ar_subledger table

BEGIN;

-- Make invoice_id nullable
ALTER TABLE payment_details
ALTER COLUMN invoice_id DROP NOT NULL;

-- Add comment
COMMENT ON COLUMN payment_details.invoice_id IS
'Invoice ID for single-invoice payments. NULL for multi-invoice payments (tracked in ar_subledger).';

COMMIT;

-- Verify
SELECT
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'payment_details'
  AND column_name = 'invoice_id';
