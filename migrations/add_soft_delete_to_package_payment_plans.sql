-- Migration: Add soft delete fields to package_payment_plans
-- Date: 2025-01-11
-- Purpose: Enable soft delete functionality

-- Add soft delete columns
ALTER TABLE package_payment_plans
ADD COLUMN is_deleted BOOLEAN DEFAULT false NOT NULL;

ALTER TABLE package_payment_plans
ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE package_payment_plans
ADD COLUMN deleted_by VARCHAR(15) REFERENCES users(user_id);

-- Add index for performance
CREATE INDEX idx_package_plans_not_deleted
ON package_payment_plans(hospital_id, patient_id)
WHERE is_deleted = false;

-- Add comments
COMMENT ON COLUMN package_payment_plans.is_deleted IS 'Soft delete flag';
COMMENT ON COLUMN package_payment_plans.deleted_at IS 'Timestamp when record was soft deleted';
COMMENT ON COLUMN package_payment_plans.deleted_by IS 'User who soft deleted the record';

-- Verification
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'package_payment_plans'
AND column_name IN ('is_deleted', 'deleted_at', 'deleted_by')
ORDER BY ordinal_position;
