-- Migration: Add 'discontinued' status to package_payment_plans
-- Date: 2025-11-12
-- Purpose: Allow package plans to be marked as discontinued (triggers refund process)

-- Drop existing status check constraint
ALTER TABLE package_payment_plans
DROP CONSTRAINT IF EXISTS package_payment_plans_status_check;

-- Add updated status check constraint including 'discontinued'
ALTER TABLE package_payment_plans
ADD CONSTRAINT package_payment_plans_status_check
CHECK (status IN ('active', 'completed', 'cancelled', 'suspended', 'discontinued'));

-- Verify the constraint
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'package_payment_plans_status_check'
  AND conrelid = 'package_payment_plans'::regclass;
