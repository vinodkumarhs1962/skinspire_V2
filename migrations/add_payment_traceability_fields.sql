-- Migration: Add Traceability Fields to payment_details table
-- Date: 2025-11-15
-- Purpose: Improve payment tracking, reporting, and audit trail

-- ============================================================================
-- 1. Add patient_id for direct patient reference
-- ============================================================================
-- Currently requires join through invoice_header or AR subledger
-- Improves query performance and simplifies reporting

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS patient_id UUID REFERENCES patients(patient_id);

CREATE INDEX IF NOT EXISTS idx_payment_details_patient
ON payment_details(patient_id)
WHERE patient_id IS NOT NULL;

COMMENT ON COLUMN payment_details.patient_id IS
'Direct reference to patient - improves query performance for multi-invoice payments';


-- ============================================================================
-- 2. Add branch_id for branch-level tracking
-- ============================================================================
-- Currently gets it from invoice which is NULL for multi-invoice payments
-- Essential for branch-level payment reporting

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(branch_id);

CREATE INDEX IF NOT EXISTS idx_payment_details_branch
ON payment_details(branch_id)
WHERE branch_id IS NOT NULL;

COMMENT ON COLUMN payment_details.branch_id IS
'Branch where payment was recorded - critical for multi-invoice payments';


-- ============================================================================
-- 3. Add payment_number for human-readable reference
-- ============================================================================
-- Auto-generated sequence like 'PMT-2025-0001'
-- Easier for staff to reference than UUID

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS payment_number VARCHAR(50) UNIQUE;

CREATE INDEX IF NOT EXISTS idx_payment_details_payment_number
ON payment_details(payment_number);

COMMENT ON COLUMN payment_details.payment_number IS
'Human-readable payment reference number (e.g., PMT-2025-0001)';


-- ============================================================================
-- 4. Add recorded_by for cash handling accountability
-- ============================================================================
-- Track who physically recorded the payment vs created_by (system user)

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS recorded_by VARCHAR(15) REFERENCES users(user_id);

COMMENT ON COLUMN payment_details.recorded_by IS
'User who physically recorded the payment (for cash handling accountability)';


-- ============================================================================
-- 5. Add payment_source to track entry method
-- ============================================================================
-- Helps understand payment entry patterns and identify process issues

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS payment_source VARCHAR(20)
CHECK (payment_source IN ('invoice_screen', 'multi_invoice', 'advance', 'api', 'manual'));

CREATE INDEX IF NOT EXISTS idx_payment_details_source
ON payment_details(payment_source);

COMMENT ON COLUMN payment_details.payment_source IS
'Source of payment entry: invoice_screen, multi_invoice, advance, api, manual';


-- ============================================================================
-- 6. Add advance_adjustment_amount for advance payment tracking
-- ============================================================================
-- Track when advance payments are adjusted against invoices

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS advance_adjustment_amount NUMERIC(12, 2) DEFAULT 0;

COMMENT ON COLUMN payment_details.advance_adjustment_amount IS
'Amount adjusted from patient advance balance';


-- ============================================================================
-- 7. Add invoice_count for multi-invoice payment tracking
-- ============================================================================
-- Denormalized count - useful for reporting without counting AR entries

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS invoice_count INTEGER DEFAULT 1;

COMMENT ON COLUMN payment_details.invoice_count IS
'Number of invoices in this payment (1 for single, >1 for multi-invoice)';


-- ============================================================================
-- 8. Add last_modified_by and last_modified_at for change tracking
-- ============================================================================
-- Track who made the last change beyond created_by

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS last_modified_by VARCHAR(15) REFERENCES users(user_id);

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS last_modified_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN payment_details.last_modified_by IS
'User who last modified this payment record';

COMMENT ON COLUMN payment_details.last_modified_at IS
'Timestamp of last modification';


-- ============================================================================
-- 9. Fix created_by to ensure it's always populated
-- ============================================================================
-- Note: We can't add NOT NULL constraint to existing column with NULL values
-- But we can set a default for future inserts

ALTER TABLE payment_details
ALTER COLUMN created_by SET DEFAULT CURRENT_USER;

COMMENT ON COLUMN payment_details.created_by IS
'System user who created the payment record';


-- ============================================================================
-- 10. Add reconciliation tracking fields
-- ============================================================================
-- For bank reconciliation and payment verification

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS bank_reconciled BOOLEAN DEFAULT FALSE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS bank_reconciled_date TIMESTAMP WITH TIME ZONE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS bank_reconciled_by VARCHAR(15) REFERENCES users(user_id);

COMMENT ON COLUMN payment_details.bank_reconciled IS
'Whether this payment has been reconciled with bank statement';


-- ============================================================================
-- 11. Populate patient_id and branch_id for existing records
-- ============================================================================

-- Populate patient_id from invoice_header for single invoice payments
UPDATE payment_details pd
SET patient_id = ih.patient_id
FROM invoice_header ih
WHERE pd.invoice_id = ih.invoice_id
  AND pd.invoice_id IS NOT NULL
  AND pd.patient_id IS NULL;

-- Populate patient_id from AR subledger for multi-invoice payments
UPDATE payment_details pd
SET patient_id = (
    SELECT DISTINCT ar.patient_id
    FROM ar_subledger ar
    WHERE ar.reference_id = pd.payment_id
      AND ar.reference_type = 'payment'
    LIMIT 1
)
WHERE pd.invoice_id IS NULL
  AND pd.patient_id IS NULL;

-- Populate branch_id from invoice_header for single invoice payments
UPDATE payment_details pd
SET branch_id = ih.branch_id
FROM invoice_header ih
WHERE pd.invoice_id = ih.invoice_id
  AND pd.invoice_id IS NOT NULL
  AND pd.branch_id IS NULL;

-- Populate branch_id from AR subledger for multi-invoice payments
UPDATE payment_details pd
SET branch_id = (
    SELECT DISTINCT ar.branch_id
    FROM ar_subledger ar
    WHERE ar.reference_id = pd.payment_id
      AND ar.reference_type = 'payment'
    LIMIT 1
)
WHERE pd.invoice_id IS NULL
  AND pd.branch_id IS NULL;

-- Populate invoice_count for multi-invoice payments
UPDATE payment_details pd
SET invoice_count = (
    SELECT COUNT(DISTINCT ili.invoice_id)
    FROM ar_subledger ar
    JOIN invoice_line_item ili ON ar.reference_line_item_id = ili.line_item_id
    WHERE ar.reference_id = pd.payment_id
      AND ar.reference_type = 'payment'
)
WHERE pd.invoice_id IS NULL;

-- Set payment_source based on existing data
UPDATE payment_details pd
SET payment_source = CASE
    WHEN pd.invoice_id IS NULL THEN 'multi_invoice'
    WHEN pd.advance_adjustment_id IS NOT NULL THEN 'advance'
    ELSE 'invoice_screen'
END
WHERE pd.payment_source IS NULL;


-- ============================================================================
-- 12. Create function to auto-generate payment number
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_payment_number()
RETURNS TRIGGER AS $$
DECLARE
    year_part VARCHAR(4);
    seq_num VARCHAR(6);
    new_number VARCHAR(50);
BEGIN
    -- Only generate if payment_number is NULL
    IF NEW.payment_number IS NULL THEN
        year_part := TO_CHAR(NEW.payment_date, 'YYYY');

        -- Get next sequence number for this year
        SELECT LPAD(
            (COUNT(*) + 1)::TEXT,
            6,
            '0'
        ) INTO seq_num
        FROM payment_details
        WHERE EXTRACT(YEAR FROM payment_date) = EXTRACT(YEAR FROM NEW.payment_date);

        new_number := 'PMT-' || year_part || '-' || seq_num;
        NEW.payment_number := new_number;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_generate_payment_number ON payment_details;
CREATE TRIGGER trg_generate_payment_number
    BEFORE INSERT ON payment_details
    FOR EACH ROW
    EXECUTE FUNCTION generate_payment_number();


-- ============================================================================
-- 13. Create function to track last modification
-- ============================================================================

CREATE OR REPLACE FUNCTION update_payment_modification_tracking()
RETURNS TRIGGER AS $$
BEGIN
    -- Set last_modified timestamp
    NEW.last_modified_at := CURRENT_TIMESTAMP;

    -- If last_modified_by is not set, use created_by
    IF NEW.last_modified_by IS NULL THEN
        NEW.last_modified_by := NEW.created_by;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trg_payment_modification_tracking ON payment_details;
CREATE TRIGGER trg_payment_modification_tracking
    BEFORE UPDATE ON payment_details
    FOR EACH ROW
    EXECUTE FUNCTION update_payment_modification_tracking();


-- ============================================================================
-- 14. Generate payment numbers for existing records
-- ============================================================================

DO $$
DECLARE
    payment_rec RECORD;
    year_part VARCHAR(4);
    seq_num INTEGER;
    new_number VARCHAR(50);
BEGIN
    seq_num := 0;
    year_part := '';

    FOR payment_rec IN
        SELECT payment_id, payment_date
        FROM payment_details
        WHERE payment_number IS NULL
        ORDER BY payment_date, created_at
    LOOP
        -- Reset sequence for new year
        IF year_part != TO_CHAR(payment_rec.payment_date, 'YYYY') THEN
            year_part := TO_CHAR(payment_rec.payment_date, 'YYYY');
            seq_num := 0;
        END IF;

        seq_num := seq_num + 1;
        new_number := 'PMT-' || year_part || '-' || LPAD(seq_num::TEXT, 6, '0');

        UPDATE payment_details
        SET payment_number = new_number
        WHERE payment_id = payment_rec.payment_id;
    END LOOP;
END $$;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check if all payments now have patient_id and branch_id
SELECT
    COUNT(*) AS total_payments,
    COUNT(patient_id) AS with_patient_id,
    COUNT(branch_id) AS with_branch_id,
    COUNT(payment_number) AS with_payment_number
FROM payment_details;

-- Check multi-invoice payments
SELECT
    COUNT(*) AS multi_invoice_payments,
    AVG(invoice_count) AS avg_invoices_per_payment
FROM payment_details
WHERE invoice_id IS NULL;

-- Check payment sources
SELECT
    payment_source,
    COUNT(*) AS count
FROM payment_details
GROUP BY payment_source
ORDER BY count DESC;
