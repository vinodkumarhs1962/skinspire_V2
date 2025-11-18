-- ============================================================================
-- Migration: Add Supplier Advance Adjustment Subledger (Simple Version)
-- Date: 2025-11-02
-- Database: PostgreSQL
-- Description: Add advance_amount field and create subledger table
-- ============================================================================

-- STEP 1: Add advance_amount column to supplier_payment table
-- ============================================================================
ALTER TABLE supplier_payment
ADD COLUMN IF NOT EXISTS advance_amount NUMERIC(12, 2) DEFAULT 0 NOT NULL;

UPDATE supplier_payment
SET advance_amount = 0
WHERE advance_amount IS NULL;

COMMENT ON COLUMN supplier_payment.advance_amount IS 'Amount allocated from advance/unallocated payments';

-- STEP 2: Create supplier_advance_adjustments table
-- ============================================================================
CREATE TABLE IF NOT EXISTS supplier_advance_adjustments (
    adjustment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL,
    branch_id UUID NOT NULL,
    source_payment_id UUID NOT NULL,
    target_payment_id UUID,
    invoice_id UUID,
    supplier_id UUID NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    adjustment_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    adjustment_type VARCHAR(20) DEFAULT 'allocation' CHECK (adjustment_type IN ('allocation', 'reversal', 'refund')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by VARCHAR(50),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_by VARCHAR(50),
    CONSTRAINT fk_supplier_advance_adj_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_source FOREIGN KEY (source_payment_id) REFERENCES supplier_payment(payment_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_target FOREIGN KEY (target_payment_id) REFERENCES supplier_payment(payment_id) ON DELETE CASCADE,
    CONSTRAINT fk_supplier_advance_adj_invoice FOREIGN KEY (invoice_id) REFERENCES supplier_invoice(invoice_id) ON DELETE SET NULL,
    CONSTRAINT fk_supplier_advance_adj_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE CASCADE
);

-- STEP 3: Create indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_source_payment ON supplier_advance_adjustments(source_payment_id);
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_target_payment ON supplier_advance_adjustments(target_payment_id);
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_invoice ON supplier_advance_adjustments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_supplier ON supplier_advance_adjustments(supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_hospital ON supplier_advance_adjustments(hospital_id);
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_branch ON supplier_advance_adjustments(branch_id);
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_date ON supplier_advance_adjustments(adjustment_date DESC);
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_type ON supplier_advance_adjustments(adjustment_type);

-- STEP 4: Add comments
-- ============================================================================
COMMENT ON TABLE supplier_advance_adjustments IS 'Subledger for tracking supplier advance payment allocations';
COMMENT ON COLUMN supplier_advance_adjustments.source_payment_id IS 'The unallocated/advance payment being used';
COMMENT ON COLUMN supplier_advance_adjustments.target_payment_id IS 'The new payment record that includes this advance allocation';
COMMENT ON COLUMN supplier_advance_adjustments.adjustment_type IS 'Type: allocation, reversal, refund';

-- STEP 5: Create trigger for updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_supplier_advance_adj_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_supplier_advance_adj_update_timestamp ON supplier_advance_adjustments;

CREATE TRIGGER trg_supplier_advance_adj_update_timestamp
    BEFORE UPDATE ON supplier_advance_adjustments
    FOR EACH ROW
    EXECUTE FUNCTION update_supplier_advance_adj_timestamp();

-- STEP 6: Create view for advance balance
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
    LEFT JOIN supplier_advance_adjustments saa ON sp.payment_id = saa.source_payment_id AND saa.adjustment_type = 'allocation'
WHERE
    sp.invoice_id IS NULL
    AND sp.workflow_status = 'approved'
    AND sp.is_deleted = FALSE
GROUP BY
    sp.supplier_id, sp.hospital_id, sp.branch_id, sp.payment_id, sp.payment_date, sp.amount, sp.reference_no
HAVING
    sp.amount - COALESCE(SUM(saa.amount), 0) > 0.01
ORDER BY
    sp.payment_date ASC;

COMMENT ON VIEW v_supplier_advance_balance IS 'View showing available advance balance for each supplier by payment (FIFO order)';

-- STEP 7: Verification
-- ============================================================================
SELECT 'Migration completed successfully!' AS status;

SELECT
    COUNT(*) AS advance_amount_column_exists
FROM information_schema.columns
WHERE table_name = 'supplier_payment' AND column_name = 'advance_amount';

SELECT
    COUNT(*) AS supplier_advance_adjustments_table_exists
FROM information_schema.tables
WHERE table_name = 'supplier_advance_adjustments';

SELECT
    COUNT(*) AS v_supplier_advance_balance_view_exists
FROM information_schema.views
WHERE table_name = 'v_supplier_advance_balance';
