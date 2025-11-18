-- Migration: Add missing audit fields to installment_payments table
-- Date: 2025-11-12
-- Description: Adds created_by, updated_at, and updated_by to match TimestampMixin pattern

-- Add missing audit columns
ALTER TABLE installment_payments
ADD COLUMN IF NOT EXISTS created_by VARCHAR(15) REFERENCES users(user_id),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(15) REFERENCES users(user_id);

-- Create trigger function for auto-updating timestamps
CREATE OR REPLACE FUNCTION update_installment_payment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at on UPDATE
DROP TRIGGER IF EXISTS trigger_update_installment_payment_timestamp ON installment_payments;
CREATE TRIGGER trigger_update_installment_payment_timestamp
    BEFORE UPDATE ON installment_payments
    FOR EACH ROW
    EXECUTE FUNCTION update_installment_payment_timestamp();

-- Add helpful comment
COMMENT ON COLUMN installment_payments.created_by IS 'User ID of who created this installment';
COMMENT ON COLUMN installment_payments.updated_at IS 'Timestamp of last update';
COMMENT ON COLUMN installment_payments.updated_by IS 'User ID of who last updated this installment';
