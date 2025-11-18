-- Migration: Add discontinuation tracking fields to package_payment_plans
-- Date: 2025-11-12
-- Purpose: Track plan discontinuation with refund processing workflow

-- Add discontinuation tracking fields
ALTER TABLE package_payment_plans
ADD COLUMN IF NOT EXISTS discontinued_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS discontinued_by VARCHAR(15) REFERENCES users(user_id),
ADD COLUMN IF NOT EXISTS discontinuation_reason TEXT,
ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS refund_status VARCHAR(20) DEFAULT 'none';

-- Add comment for refund_status values
COMMENT ON COLUMN package_payment_plans.refund_status IS 'Values: none, pending, approved, processed, failed';

-- Add check constraint for refund_status
ALTER TABLE package_payment_plans
DROP CONSTRAINT IF EXISTS package_payment_plans_refund_status_check;

ALTER TABLE package_payment_plans
ADD CONSTRAINT package_payment_plans_refund_status_check
CHECK (refund_status IN ('none', 'pending', 'approved', 'processed', 'failed'));

-- Verify the columns were added
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'package_payment_plans'
  AND column_name IN ('discontinued_at', 'discontinued_by', 'discontinuation_reason', 'refund_amount', 'refund_status')
ORDER BY column_name;
