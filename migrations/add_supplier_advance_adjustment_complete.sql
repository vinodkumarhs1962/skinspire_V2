-- ============================================================================
-- Migration: Add Supplier Advance Adjustment Subledger
-- Date: 2025-11-02
-- Database: PostgreSQL
-- Description: Implement subledger for supplier advance allocations
-- ============================================================================

-- STEP 1: Add advance_amount column to supplier_payment table
-- ============================================================================
DO $$
BEGIN
    -- Add advance_amount column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'supplier_payment'
        AND column_name = 'advance_amount'
    ) THEN
        ALTER TABLE supplier_payment
        ADD COLUMN advance_amount NUMERIC(12, 2) DEFAULT 0 NOT NULL;

        RAISE NOTICE 'Added advance_amount column to supplier_payment table';
    ELSE
        RAISE NOTICE 'advance_amount column already exists in supplier_payment table';
    END IF;
END $$;

-- Update existing NULL values to 0
UPDATE supplier_payment
SET advance_amount = 0
WHERE advance_amount IS NULL;

-- Add comment
COMMENT ON COLUMN supplier_payment.advance_amount IS 'Amount allocated from advance/unallocated payments';

-- STEP 2: Create supplier_advance_adjustments table
-- ============================================================================
CREATE TABLE IF NOT EXISTS supplier_advance_adjustments (
    -- Primary key
    adjustment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Hospital and Branch (for multi-tenancy)
    hospital_id UUID NOT NULL,
    branch_id UUID NOT NULL,

    -- Source advance payment (the unallocated payment being used)
    source_payment_id UUID NOT NULL,

    -- Target references (what the advance is being applied to)
    target_payment_id UUID,  -- The new payment record that includes this advance allocation
    invoice_id UUID,         -- The invoice being paid
    supplier_id UUID NOT NULL,

    -- Adjustment details
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    adjustment_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    adjustment_type VARCHAR(20) DEFAULT 'allocation' CHECK (adjustment_type IN ('allocation', 'reversal', 'refund')),
    notes TEXT,

    -- Timestamp fields (matching TimestampMixin)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(50),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_by VARCHAR(50),

    -- Foreign key constraints
    CONSTRAINT fk_supplier_advance_adj_hospital
        FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_branch
        FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_source
        FOREIGN KEY (source_payment_id) REFERENCES supplier_payment(payment_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_target
        FOREIGN KEY (target_payment_id) REFERENCES supplier_payment(payment_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_invoice
        FOREIGN KEY (invoice_id) REFERENCES supplier_invoice(invoice_id) ON DELETE SET NULL,
    CONSTRAINT fk_supplier_advance_adj_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE CASCADE
);

-- STEP 3: Create indexes for performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_source_payment
    ON supplier_advance_adjustments(source_payment_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_target_payment
    ON supplier_advance_adjustments(target_payment_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_invoice
    ON supplier_advance_adjustments(invoice_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_supplier
    ON supplier_advance_adjustments(supplier_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_hospital
    ON supplier_advance_adjustments(hospital_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_branch
    ON supplier_advance_adjustments(branch_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_date
    ON supplier_advance_adjustments(adjustment_date DESC);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_type
    ON supplier_advance_adjustments(adjustment_type);

-- STEP 4: Add table and column comments
-- ============================================================================
COMMENT ON TABLE supplier_advance_adjustments IS
    'Subledger for tracking supplier advance payment allocations. Provides audit trail for advance usage.';

COMMENT ON COLUMN supplier_advance_adjustments.adjustment_id IS
    'Unique identifier for the adjustment record';

COMMENT ON COLUMN supplier_advance_adjustments.source_payment_id IS
    'The unallocated/advance payment being used (invoice_id = NULL in source payment)';

COMMENT ON COLUMN supplier_advance_adjustments.target_payment_id IS
    'The new payment record that includes this advance allocation';

COMMENT ON COLUMN supplier_advance_adjustments.invoice_id IS
    'The invoice to which the advance is being applied';

COMMENT ON COLUMN supplier_advance_adjustments.amount IS
    'Amount being allocated from the advance payment';

COMMENT ON COLUMN supplier_advance_adjustments.adjustment_type IS
    'Type of adjustment: allocation (using advance), reversal (canceling allocation), refund (returning advance to supplier)';

COMMENT ON COLUMN supplier_advance_adjustments.notes IS
    'Optional notes about the adjustment';

-- STEP 5: Create trigger to update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_supplier_advance_adj_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_supplier_advance_adj_update_timestamp
    ON supplier_advance_adjustments;

CREATE TRIGGER trg_supplier_advance_adj_update_timestamp
    BEFORE UPDATE ON supplier_advance_adjustments
    FOR EACH ROW
    EXECUTE FUNCTION update_supplier_advance_adj_timestamp();

-- STEP 6: Create view for advance balance tracking
-- ============================================================================
CREATE OR REPLACE VIEW v_supplier_advance_balance AS
SELECT
    sp.supplier_id,
    sp.hospital_id,
    sp.branch_id,
    sp.payment_id AS advance_payment_id,
    sp.payment_date AS advance_date,
    sp.amount AS original_advance_amount,
    sp.reference_no,
    COALESCE(SUM(saa.amount), 0) AS allocated_amount,
    sp.amount - COALESCE(SUM(saa.amount), 0) AS remaining_balance,
    COUNT(saa.adjustment_id) AS allocation_count
FROM
    supplier_payment sp
    LEFT JOIN supplier_advance_adjustments saa
        ON sp.payment_id = saa.source_payment_id
        AND saa.adjustment_type = 'allocation'
WHERE
    sp.invoice_id IS NULL  -- Only unallocated payments (advances)
    AND sp.workflow_status = 'approved'  -- Only approved payments
    AND sp.is_deleted = FALSE  -- Not deleted
GROUP BY
    sp.supplier_id,
    sp.hospital_id,
    sp.branch_id,
    sp.payment_id,
    sp.payment_date,
    sp.amount,
    sp.reference_no
HAVING
    sp.amount - COALESCE(SUM(saa.amount), 0) > 0.01  -- Has remaining balance
ORDER BY
    sp.payment_date ASC;  -- FIFO order

COMMENT ON VIEW v_supplier_advance_balance IS
    'View showing available advance balance for each supplier by payment (FIFO order)';

-- STEP 7: Grant permissions (adjust as needed for your setup)
-- ============================================================================
-- Grant permissions to your application user (replace 'your_app_user' with actual user)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON supplier_advance_adjustments TO your_app_user;
-- GRANT SELECT ON v_supplier_advance_balance TO your_app_user;

-- STEP 8: Verification queries
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Migration completed successfully!';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Created objects:';
    RAISE NOTICE '  1. Added advance_amount column to supplier_payment';
    RAISE NOTICE '  2. Created supplier_advance_adjustments table';
    RAISE NOTICE '  3. Created 8 indexes for performance';
    RAISE NOTICE '  4. Created update timestamp trigger';
    RAISE NOTICE '  5. Created v_supplier_advance_balance view';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Run these queries to verify:';
    RAISE NOTICE '  SELECT * FROM supplier_advance_adjustments LIMIT 5;';
    RAISE NOTICE '  SELECT * FROM v_supplier_advance_balance;';
    RAISE NOTICE '  \d supplier_payment  -- Check advance_amount column';
    RAISE NOTICE '  \d supplier_advance_adjustments  -- Check table structure';
    RAISE NOTICE '============================================================================';
END $$;

-- Verification: Check if advance_amount column was added
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'supplier_payment' AND column_name = 'advance_amount'
        ) THEN '✓ advance_amount column added to supplier_payment'
        ELSE '✗ ERROR: advance_amount column NOT added'
    END AS status;

-- Verification: Check if supplier_advance_adjustments table was created
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'supplier_advance_adjustments'
        ) THEN '✓ supplier_advance_adjustments table created'
        ELSE '✗ ERROR: supplier_advance_adjustments table NOT created'
    END AS status;

-- Verification: Check if view was created
SELECT
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.views
            WHERE table_name = 'v_supplier_advance_balance'
        ) THEN '✓ v_supplier_advance_balance view created'
        ELSE '✗ ERROR: v_supplier_advance_balance view NOT created'
    END AS status;
