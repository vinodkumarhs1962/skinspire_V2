-- Migration: Add invoice_id reference to package_payment_plans
-- Date: 2025-01-11
-- Purpose: Link payment plan to originating invoice for proper data flow

-- ============================================================================
-- Add invoice_id column and foreign key
-- ============================================================================

ALTER TABLE package_payment_plans
ADD COLUMN invoice_id UUID;

-- Add foreign key constraint
ALTER TABLE package_payment_plans
ADD CONSTRAINT package_payment_plans_invoice_id_fkey
FOREIGN KEY (invoice_id) REFERENCES invoice_headers(invoice_id) ON DELETE RESTRICT;

-- Add index for performance
CREATE INDEX idx_package_plans_invoice ON package_payment_plans(invoice_id);

-- Add comment
COMMENT ON COLUMN package_payment_plans.invoice_id IS 'Reference to invoice that triggered this payment plan';

-- ============================================================================
-- Verification
-- ============================================================================

SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'package_payment_plans'
AND column_name IN ('invoice_id', 'package_id', 'patient_id')
ORDER BY ordinal_position;
