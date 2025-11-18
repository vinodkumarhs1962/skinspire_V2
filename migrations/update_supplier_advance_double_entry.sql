-- ============================================================================
-- Migration: Update Supplier Advance Adjustment for Double-Entry
-- Date: 2025-11-02
-- Database: PostgreSQL
-- Description: Add 'advance_receipt' type and update view for proper balance
-- ============================================================================

-- STEP 1: Update adjustment_type constraint to include 'advance_receipt'
-- ============================================================================
ALTER TABLE supplier_advance_adjustments
DROP CONSTRAINT IF EXISTS supplier_advance_adjustments_adjustment_type_check;

ALTER TABLE supplier_advance_adjustments
ADD CONSTRAINT supplier_advance_adjustments_adjustment_type_check
CHECK (adjustment_type IN ('advance_receipt', 'allocation', 'reversal', 'refund'));

COMMENT ON COLUMN supplier_advance_adjustments.adjustment_type IS 'Type: advance_receipt (debit), allocation (credit), reversal, refund';

-- STEP 2: Drop and recreate view for proper double-entry balance calculation
-- ============================================================================
DROP VIEW IF EXISTS v_supplier_advance_balance;

CREATE VIEW v_supplier_advance_balance AS
WITH advance_subledger AS (
    -- Get all advance-related transactions from subledger
    SELECT
        supplier_id,
        hospital_id,
        branch_id,
        source_payment_id AS payment_id,
        -- DEBIT (increases balance): advance_receipt
        SUM(CASE WHEN adjustment_type = 'advance_receipt' THEN amount ELSE 0 END) AS debit_total,
        -- CREDIT (decreases balance): allocation
        SUM(CASE WHEN adjustment_type = 'allocation' THEN amount ELSE 0 END) AS credit_total,
        MIN(adjustment_date) AS first_transaction_date,
        MAX(adjustment_date) AS last_transaction_date,
        COUNT(*) AS transaction_count
    FROM supplier_advance_adjustments
    GROUP BY supplier_id, hospital_id, branch_id, source_payment_id
)
SELECT
    sp.supplier_id,
    sp.hospital_id,
    sp.branch_id,
    sp.payment_id AS advance_payment_id,
    sp.payment_date AS advance_date,
    sp.amount AS original_advance_amount,
    sp.reference_no,
    -- Keep existing column names from original view
    COALESCE(asl.credit_total, 0) AS allocated_amount,
    -- Balance calculation from subledger (proper double-entry)
    COALESCE(asl.debit_total, 0) - COALESCE(asl.credit_total, 0) AS remaining_balance,
    COALESCE(asl.transaction_count - 1, 0) AS allocation_count  -- Subtract 1 for the initial debit entry
FROM
    supplier_payment sp
    LEFT JOIN advance_subledger asl ON sp.payment_id = asl.payment_id
WHERE
    sp.invoice_id IS NULL
    AND sp.workflow_status = 'approved'
    AND sp.is_deleted = FALSE
    -- Only show advances with positive balance from subledger
    AND COALESCE(asl.debit_total, 0) - COALESCE(asl.credit_total, 0) > 0.01
ORDER BY
    sp.payment_date ASC;  -- FIFO order

COMMENT ON VIEW v_supplier_advance_balance IS 'Double-entry view: Balance = Debits (advance_receipt) - Credits (allocation)';

-- STEP 3: Create a helper view for all advance transactions (audit trail)
-- ============================================================================
CREATE OR REPLACE VIEW v_supplier_advance_transactions AS
SELECT
    saa.adjustment_id,
    saa.supplier_id,
    s.supplier_name,
    saa.hospital_id,
    saa.branch_id,
    saa.adjustment_date,
    saa.adjustment_type,
    -- Source payment (the advance)
    saa.source_payment_id,
    sp_source.reference_no AS source_reference,
    sp_source.payment_date AS source_payment_date,
    -- Target payment (invoice payment using advance)
    saa.target_payment_id,
    sp_target.reference_no AS target_reference,
    sp_target.payment_date AS target_payment_date,
    -- Invoice (if applicable)
    saa.invoice_id,
    si.supplier_invoice_number,
    -- Amount (debit or credit)
    CASE
        WHEN saa.adjustment_type = 'advance_receipt' THEN saa.amount
        ELSE 0
    END AS debit_amount,
    CASE
        WHEN saa.adjustment_type IN ('allocation', 'refund') THEN saa.amount
        ELSE 0
    END AS credit_amount,
    saa.amount,
    saa.notes,
    saa.created_by,
    saa.created_at
FROM
    supplier_advance_adjustments saa
    LEFT JOIN suppliers s ON saa.supplier_id = s.supplier_id
    LEFT JOIN supplier_payment sp_source ON saa.source_payment_id = sp_source.payment_id
    LEFT JOIN supplier_payment sp_target ON saa.target_payment_id = sp_target.payment_id
    LEFT JOIN supplier_invoice si ON saa.invoice_id = si.invoice_id
ORDER BY
    saa.adjustment_date DESC, saa.created_at DESC;

COMMENT ON VIEW v_supplier_advance_transactions IS 'Audit trail of all supplier advance transactions with debit/credit columns';

-- STEP 4: Verification
-- ============================================================================
SELECT 'Migration completed successfully!' AS status;

-- Show constraint update
SELECT
    con.conname AS constraint_name,
    pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
WHERE rel.relname = 'supplier_advance_adjustments'
AND con.conname LIKE '%adjustment_type%';

-- Show views created
SELECT
    schemaname,
    viewname,
    definition
FROM pg_views
WHERE viewname IN ('v_supplier_advance_balance', 'v_supplier_advance_transactions')
ORDER BY viewname;
