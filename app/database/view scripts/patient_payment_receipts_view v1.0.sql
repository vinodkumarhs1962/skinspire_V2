-- =====================================================================
-- Patient Payment Receipts View v1.0
-- Comprehensive view of patient payment receipts with workflow status and approval tracking
-- Joins payment_details, invoice_header, patients, hospitals, and branches
-- Used for: Payment receipt list, search, filtering, reporting, workflow management
-- =====================================================================

-- Drop view if exists
DROP VIEW IF EXISTS v_patient_payment_receipts CASCADE;

-- Create comprehensive patient payment receipts view
CREATE OR REPLACE VIEW v_patient_payment_receipts AS
SELECT
    -- === PRIMARY IDENTIFICATION ===
    pd.payment_id,
    pd.hospital_id,
    h.name AS hospital_name,

    -- === INVOICE REFERENCE ===
    pd.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    ih.invoice_type,

    -- === PATIENT INFORMATION ===
    ih.patient_id,
    p.mrn AS patient_mrn,
    TRIM(CONCAT_WS(' ',
        COALESCE(p.first_name, p.personal_info->>'first_name'),
        COALESCE(p.last_name, p.personal_info->>'last_name')
    )) AS patient_name,  -- First name + Last name only (no title)
    p.contact_info->>'phone' AS patient_phone,
    p.contact_info->>'email' AS patient_email,
    p.is_active AS patient_status,

    -- === PAYMENT DETAILS ===
    pd.payment_date,
    pd.total_amount,
    COALESCE(pd.refunded_amount, 0) AS refunded_amount,
    (pd.total_amount - COALESCE(pd.refunded_amount, 0)) AS net_amount,

    -- === PAYMENT METHOD BREAKDOWN ===
    COALESCE(pd.cash_amount, 0) AS cash_amount,
    COALESCE(pd.credit_card_amount, 0) AS credit_card_amount,
    COALESCE(pd.debit_card_amount, 0) AS debit_card_amount,
    COALESCE(pd.upi_amount, 0) AS upi_amount,

    -- === PAYMENT METHOD DETAILS ===
    pd.card_number_last4,
    pd.card_type,
    pd.upi_id,
    pd.reference_number,

    -- === CURRENCY ===
    pd.currency_code,
    pd.exchange_rate,

    -- === ADVANCE ADJUSTMENT TRACKING ===
    pd.advance_adjustment_id,
    CASE WHEN pd.advance_adjustment_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_advance_adjustment,

    -- === WORKFLOW STATUS ===
    pd.workflow_status,
    pd.requires_approval,

    -- === SUBMISSION TRACKING ===
    pd.submitted_by,
    pd.submitted_at,

    -- === APPROVAL TRACKING ===
    pd.approved_by,
    pd.approved_at,

    -- === REJECTION TRACKING ===
    pd.rejected_by,
    pd.rejected_at,
    pd.rejection_reason,

    -- === GL POSTING STATUS ===
    pd.gl_posted,
    pd.posting_date,
    pd.gl_entry_id,

    -- === REVERSAL STATUS ===
    CASE
        WHEN pd.workflow_status = 'reversed' THEN TRUE
        ELSE FALSE
    END AS is_reversed,
    CASE
        WHEN pd.workflow_status = 'reversed' THEN pd.updated_at
        ELSE NULL
    END AS reversed_at,
    CASE
        WHEN pd.workflow_status = 'reversed' THEN pd.updated_by
        ELSE NULL
    END AS reversed_by,
    pd.notes AS reversal_reason,
    CASE
        WHEN pd.workflow_status = 'reversed' THEN pd.gl_entry_id
        ELSE NULL
    END AS reversal_gl_entry_id,

    -- === SOFT DELETE STATUS ===
    pd.is_deleted,
    pd.deleted_at,
    pd.deleted_by,
    pd.deletion_reason,

    -- === RECONCILIATION STATUS ===
    pd.reconciliation_status,
    pd.reconciliation_date,

    -- === NOTES ===
    pd.notes,

    -- === AUDIT FIELDS ===
    pd.created_at,
    pd.created_by,
    pd.updated_at,
    pd.updated_by,

    -- === BRANCH INFORMATION ===
    ih.branch_id,
    b.name AS branch_name,

    -- === INVOICE FINANCIAL SUMMARY ===
    ih.total_amount AS invoice_total,
    COALESCE(ih.paid_amount, 0) AS invoice_paid_amount,
    (ih.total_amount - COALESCE(ih.paid_amount, 0)) AS invoice_balance_due,
    CASE
        WHEN COALESCE(ih.paid_amount, 0) = 0 THEN 'Unpaid'
        WHEN COALESCE(ih.paid_amount, 0) >= ih.total_amount THEN 'Paid'
        ELSE 'Partial'
    END AS invoice_payment_status,

    -- === AGING INFORMATION ===
    CASE
        WHEN pd.payment_date IS NOT NULL
        THEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - pd.payment_date))::INTEGER
        ELSE NULL
    END AS payment_age_days,
    CASE
        WHEN pd.payment_date IS NULL THEN 'N/A'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - pd.payment_date)) <= 30 THEN '0-30 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - pd.payment_date)) <= 60 THEN '31-60 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - pd.payment_date)) <= 90 THEN '61-90 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - pd.payment_date)) <= 180 THEN '91-180 days'
        ELSE '180+ days'
    END AS aging_bucket,

    -- === DATE EXTRACTION FOR REPORTING ===
    EXTRACT(YEAR FROM pd.payment_date) AS payment_year,
    EXTRACT(MONTH FROM pd.payment_date) AS payment_month,
    TO_CHAR(pd.payment_date, 'YYYY-MM') AS payment_month_year,
    TO_CHAR(pd.payment_date, 'Q') AS payment_quarter,
    TO_CHAR(pd.payment_date, 'Day') AS payment_day_name,

    -- === PAYMENT METHOD GROUPING ===
    CASE
        WHEN pd.cash_amount > 0 AND pd.credit_card_amount = 0 AND pd.debit_card_amount = 0 AND pd.upi_amount = 0 THEN 'Cash'
        WHEN pd.credit_card_amount > 0 AND pd.cash_amount = 0 AND pd.debit_card_amount = 0 AND pd.upi_amount = 0 THEN 'Credit Card'
        WHEN pd.debit_card_amount > 0 AND pd.cash_amount = 0 AND pd.credit_card_amount = 0 AND pd.upi_amount = 0 THEN 'Debit Card'
        WHEN pd.upi_amount > 0 AND pd.cash_amount = 0 AND pd.credit_card_amount = 0 AND pd.debit_card_amount = 0 THEN 'UPI'
        WHEN pd.advance_adjustment_id IS NOT NULL THEN 'Advance Adjustment'
        ELSE 'Multiple'
    END AS payment_method_primary,

    -- === REFUND INFORMATION ===
    pd.refund_date,
    pd.refund_reason,
    CASE WHEN pd.refunded_amount > 0 THEN TRUE ELSE FALSE END AS has_refund,

    -- === SEARCH HELPER FIELD ===
    LOWER(
        COALESCE(ih.invoice_number, '') || ' ' ||
        COALESCE(p.mrn, '') || ' ' ||
        COALESCE(p.personal_info->>'first_name', '') || ' ' ||
        COALESCE(p.personal_info->>'last_name', '') || ' ' ||
        COALESCE(p.contact_info->>'phone', '') || ' ' ||
        COALESCE(pd.reference_number, '') || ' ' ||
        COALESCE(pd.card_number_last4, '') || ' ' ||
        COALESCE(pd.upi_id, '')
    ) AS search_text

FROM
    payment_details pd
    INNER JOIN invoice_header ih ON pd.invoice_id = ih.invoice_id
    LEFT JOIN patients p ON ih.patient_id = p.patient_id
    LEFT JOIN hospitals h ON pd.hospital_id = h.hospital_id
    LEFT JOIN branches b ON ih.branch_id = b.branch_id
WHERE
    pd.is_deleted = FALSE;  -- Only show non-deleted payments by default

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_pp_view_hospital_id ON payment_details(hospital_id);
CREATE INDEX IF NOT EXISTS idx_pp_view_invoice_id ON payment_details(invoice_id);
CREATE INDEX IF NOT EXISTS idx_pp_view_payment_date ON payment_details(payment_date);
CREATE INDEX IF NOT EXISTS idx_pp_view_workflow_status ON payment_details(workflow_status);
CREATE INDEX IF NOT EXISTS idx_pp_view_is_deleted ON payment_details(is_deleted);

-- Grant permissions
GRANT SELECT ON v_patient_payment_receipts TO PUBLIC;

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================

-- 1. Verify view columns match Python model:
/*
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'v_patient_payment_receipts'
ORDER BY ordinal_position;
*/

-- 2. Test the view with sample data:
/*
SELECT
    payment_id,
    patient_name,
    invoice_number,
    payment_date,
    total_amount,
    workflow_status,
    payment_method_primary
FROM v_patient_payment_receipts
WHERE is_deleted = FALSE
ORDER BY payment_date DESC
LIMIT 10;
*/

-- 3. Verify workflow status distribution:
/*
SELECT
    workflow_status,
    COUNT(*) AS count,
    SUM(total_amount) AS total_amount
FROM v_patient_payment_receipts
GROUP BY workflow_status
ORDER BY count DESC;
*/

-- 4. Verify payment method breakdown:
/*
SELECT
    payment_method_primary,
    COUNT(*) AS payment_count,
    SUM(total_amount) AS total_amount,
    SUM(cash_amount) AS total_cash,
    SUM(credit_card_amount) AS total_credit_card,
    SUM(debit_card_amount) AS total_debit_card,
    SUM(upi_amount) AS total_upi
FROM v_patient_payment_receipts
GROUP BY payment_method_primary
ORDER BY payment_count DESC;
*/
