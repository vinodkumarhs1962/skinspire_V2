-- ============================================================================
-- Patient Payment Receipts View
-- Version: 1.1 (CORRECTED)
-- Date: 2025-01-10
-- Description: Create comprehensive view for patient payment receipts
-- ============================================================================

-- Drop existing view if it exists
DROP VIEW IF EXISTS v_patient_payment_receipts CASCADE;

-- Create view
CREATE OR REPLACE VIEW v_patient_payment_receipts AS
SELECT
    -- Primary identification
    pd.payment_id,
    pd.hospital_id,
    h.name as hospital_name,

    -- Invoice reference
    pd.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    ih.invoice_type,

    -- Patient information
    ih.patient_id,
    p.mrn as patient_mrn,
    COALESCE(
        NULLIF(CONCAT(COALESCE(p.first_name, ''), ' ', COALESCE(p.last_name, '')), ' '),
        p.full_name,
        'Unknown'
    ) as patient_name,
    p.contact_info->>'phone' as patient_phone,
    p.contact_info->>'email' as patient_email,
    p.is_active as patient_status,

    -- Payment details
    pd.payment_date,
    pd.total_amount,
    pd.refunded_amount,
    (pd.total_amount - COALESCE(pd.refunded_amount, 0)) as net_amount,

    -- Payment method breakdown
    pd.cash_amount,
    pd.credit_card_amount,
    pd.debit_card_amount,
    pd.upi_amount,
    COALESCE(pd.wallet_points_amount, 0) as wallet_points_amount,
    pd.wallet_transaction_id,

    -- Payment method details
    pd.card_number_last4,
    pd.card_type,
    pd.upi_id,
    pd.reference_number,

    -- Currency
    pd.currency_code,
    pd.exchange_rate,

    -- Advance adjustment tracking
    pd.advance_adjustment_id,
    CASE
        WHEN pd.advance_adjustment_id IS NOT NULL THEN TRUE
        ELSE FALSE
    END as has_advance_adjustment,

    -- Workflow status
    pd.workflow_status,
    pd.requires_approval,

    -- Submission tracking
    pd.submitted_by,
    pd.submitted_at,

    -- Approval tracking
    pd.approved_by,
    pd.approved_at,

    -- Rejection tracking
    pd.rejected_by,
    pd.rejected_at,
    pd.rejection_reason,

    -- GL posting status
    pd.gl_posted,
    pd.posting_date,
    pd.gl_entry_id,

    -- Reversal status
    pd.is_reversed,
    pd.reversed_at,
    pd.reversed_by,
    pd.reversal_reason,
    pd.reversal_gl_entry_id,

    -- Soft delete status
    pd.is_deleted,
    pd.deleted_at,
    pd.deleted_by,
    pd.deletion_reason,

    -- Reconciliation status
    pd.reconciliation_status,
    pd.reconciliation_date,

    -- Notes
    pd.notes,

    -- Audit fields
    pd.created_at,
    pd.created_by,
    pd.updated_at,
    pd.updated_by,

    -- Branch information (if applicable)
    ih.branch_id,
    b.name as branch_name,

    -- Invoice financial summary
    ih.total_amount as invoice_total,
    ih.paid_amount as invoice_paid_amount,
    ih.balance_due as invoice_balance_due,

    -- Payment status (derived from balance)
    CASE
        WHEN ih.balance_due = 0 THEN 'Paid'
        WHEN ih.paid_amount > 0 AND ih.balance_due > 0 THEN 'Partial'
        ELSE 'Unpaid'
    END as invoice_payment_status,

    -- Aging information
    (CURRENT_DATE - DATE(pd.payment_date)) as payment_age_days,
    CASE
        WHEN (CURRENT_DATE - DATE(pd.payment_date)) <= 30 THEN '0-30 days'
        WHEN (CURRENT_DATE - DATE(pd.payment_date)) <= 60 THEN '31-60 days'
        WHEN (CURRENT_DATE - DATE(pd.payment_date)) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END as aging_bucket

FROM payment_details pd

-- Join invoice header
INNER JOIN invoice_header ih ON pd.invoice_id = ih.invoice_id

-- Join patient
INNER JOIN patients p ON ih.patient_id = p.patient_id

-- Join hospital
INNER JOIN hospitals h ON pd.hospital_id = h.hospital_id

-- Left join branch (optional)
LEFT JOIN branches b ON ih.branch_id = b.branch_id

-- Filter: Only include non-deleted payments
WHERE pd.is_deleted = FALSE;

-- Add comment to view
COMMENT ON VIEW v_patient_payment_receipts IS 'Comprehensive view of patient payment receipts with workflow status, approval tracking, and GL posting information';

-- Create indexes on underlying table for view performance
-- (These may already exist, IF NOT EXISTS prevents errors)
CREATE INDEX IF NOT EXISTS idx_payment_details_payment_date
    ON payment_details(payment_date DESC);

CREATE INDEX IF NOT EXISTS idx_payment_details_created_at
    ON payment_details(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payment_details_hospital_patient
    ON payment_details(hospital_id, invoice_id);

-- Grant permissions (adjust as needed)
-- GRANT SELECT ON v_patient_payment_receipts TO billing_users;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Count total payment receipts by status
-- SELECT workflow_status, COUNT(*) as count
-- FROM v_patient_payment_receipts
-- GROUP BY workflow_status
-- ORDER BY count DESC;

-- Count payment receipts requiring approval
-- SELECT
--     COUNT(*) FILTER (WHERE requires_approval = TRUE AND workflow_status = 'pending_approval') as pending_approval,
--     COUNT(*) FILTER (WHERE workflow_status = 'approved') as approved,
--     COUNT(*) FILTER (WHERE workflow_status = 'rejected') as rejected,
--     COUNT(*) FILTER (WHERE workflow_status = 'draft') as draft,
--     COUNT(*) FILTER (WHERE is_reversed = TRUE) as reversed
-- FROM v_patient_payment_receipts;

-- Sample records from view
-- SELECT
--     payment_id,
--     invoice_number,
--     patient_name,
--     payment_date,
--     total_amount,
--     workflow_status,
--     gl_posted
-- FROM v_patient_payment_receipts
-- ORDER BY payment_date DESC
-- LIMIT 10;
