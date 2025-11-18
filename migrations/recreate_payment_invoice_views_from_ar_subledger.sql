-- =====================================================================
-- Recreate Payment and Invoice Views Based on AR Subledger
-- Properly supports many-to-many relationship between payments and invoices
-- =====================================================================

-- =====================================================================
-- 1. PAYMENT-CENTRIC VIEW (v_patient_payment_receipts)
--    One row per payment_id
--    Aggregates data from ar_subledger
-- =====================================================================

DROP VIEW IF EXISTS v_patient_payment_receipts CASCADE;

CREATE OR REPLACE VIEW v_patient_payment_receipts AS
WITH payment_ar_summary AS (
    -- Get payment allocations from ar_subledger
    SELECT
        ar_payment.reference_id AS payment_id,
        ar_payment.hospital_id,
        ar_payment.patient_id,
        COUNT(DISTINCT ar_invoice.reference_id) AS invoice_count,
        -- Get first invoice for display (for backward compatibility)
        (ARRAY_AGG(ar_invoice.reference_id ORDER BY ar_invoice.transaction_date))[1] AS first_invoice_id,
        (ARRAY_AGG(ar_invoice.reference_number ORDER BY ar_invoice.transaction_date))[1] AS first_invoice_number
    FROM ar_subledger ar_payment
    INNER JOIN ar_subledger ar_invoice ON ar_payment.gl_transaction_id = ar_invoice.gl_transaction_id
    WHERE ar_payment.reference_type = 'payment'
      AND ar_invoice.reference_type = 'invoice'
      AND ar_payment.entry_type = 'payment'
    GROUP BY ar_payment.reference_id, ar_payment.hospital_id, ar_payment.patient_id
)
SELECT
    -- === PRIMARY IDENTIFICATION ===
    pd.payment_id,
    pd.hospital_id,
    h.name AS hospital_name,

    -- === INVOICE REFERENCE (First invoice for backward compatibility) ===
    COALESCE(pd.invoice_id, ar_summary.first_invoice_id) AS invoice_id,
    COALESCE(ih.invoice_number, ar_summary.first_invoice_number) AS invoice_number,
    ih.invoice_date,
    ih.invoice_type,

    -- === MULTI-INVOICE INDICATOR ===
    COALESCE(ar_summary.invoice_count, CASE WHEN pd.invoice_id IS NOT NULL THEN 1 ELSE 0 END) AS invoice_count,
    CASE WHEN COALESCE(ar_summary.invoice_count, 0) > 1 THEN TRUE ELSE FALSE END AS is_multi_invoice_payment,

    -- === PATIENT INFORMATION ===
    COALESCE(ih.patient_id, ar_summary.patient_id) AS patient_id,
    p.mrn AS patient_mrn,
    TRIM(CONCAT_WS(' ',
        COALESCE(p.first_name, p.personal_info->>'first_name'),
        COALESCE(p.last_name, p.personal_info->>'last_name')
    )) AS patient_name,
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

    -- === ADVANCE ADJUSTMENT ===
    pd.advance_adjustment_id,
    CASE WHEN pd.advance_adjustment_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_advance_adjustment,

    -- === WORKFLOW STATUS ===
    pd.workflow_status,
    pd.requires_approval,
    pd.submitted_by,
    pd.submitted_at,
    pd.approved_by,
    pd.approved_at,
    pd.rejected_by,
    pd.rejected_at,
    pd.rejection_reason,

    -- === GL POSTING ===
    pd.gl_posted,
    pd.posting_date,
    pd.gl_entry_id,

    -- === REVERSAL STATUS ===
    CASE WHEN pd.workflow_status = 'reversed' THEN TRUE ELSE FALSE END AS is_reversed,
    CASE WHEN pd.workflow_status = 'reversed' THEN pd.updated_at ELSE NULL END AS reversed_at,
    CASE WHEN pd.workflow_status = 'reversed' THEN pd.updated_by ELSE NULL END AS reversed_by,
    pd.notes AS reversal_reason,

    -- === RECONCILIATION ===
    pd.reconciliation_status,
    pd.reconciliation_date,

    -- === REFUND ===
    pd.refund_date,
    pd.refund_reason,
    CASE WHEN pd.refunded_amount > 0 THEN TRUE ELSE FALSE END AS has_refund,

    -- === BRANCH ===
    ih.branch_id AS branch_id,
    b.name AS branch_name,

    -- === AGING ===
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

    -- === DATE EXTRACTION ===
    EXTRACT(YEAR FROM pd.payment_date) AS payment_year,
    EXTRACT(MONTH FROM pd.payment_date) AS payment_month,
    TO_CHAR(pd.payment_date, 'YYYY-MM') AS payment_month_year,
    TO_CHAR(pd.payment_date, 'Q') AS payment_quarter,
    TO_CHAR(pd.payment_date, 'Day') AS payment_day_name,

    -- === PAYMENT METHOD PRIMARY ===
    CASE
        WHEN pd.cash_amount > 0 AND pd.credit_card_amount = 0 AND pd.debit_card_amount = 0 AND pd.upi_amount = 0 THEN 'Cash'
        WHEN pd.credit_card_amount > 0 AND pd.cash_amount = 0 AND pd.debit_card_amount = 0 AND pd.upi_amount = 0 THEN 'Credit Card'
        WHEN pd.debit_card_amount > 0 AND pd.cash_amount = 0 AND pd.credit_card_amount = 0 AND pd.upi_amount = 0 THEN 'Debit Card'
        WHEN pd.upi_amount > 0 AND pd.cash_amount = 0 AND pd.credit_card_amount = 0 AND pd.debit_card_amount = 0 THEN 'UPI'
        WHEN pd.advance_adjustment_id IS NOT NULL THEN 'Advance Adjustment'
        ELSE 'Multiple'
    END AS payment_method_primary,

    -- === SEARCH VECTOR ===
    LOWER(
        COALESCE(ih.invoice_number, ar_summary.first_invoice_number, '') || ' ' ||
        COALESCE(p.mrn, '') || ' ' ||
        COALESCE(p.personal_info->>'first_name', '') || ' ' ||
        COALESCE(p.personal_info->>'last_name', '') || ' ' ||
        COALESCE(p.contact_info->>'phone', '') || ' ' ||
        COALESCE(pd.reference_number, '') || ' ' ||
        COALESCE(pd.notes, '')
    ) AS search_vector,

    -- === AUDIT ===
    pd.created_by,
    pd.created_at,
    pd.updated_by,
    pd.updated_at,
    pd.is_deleted,
    pd.notes

FROM payment_details pd
LEFT JOIN payment_ar_summary ar_summary ON pd.payment_id = ar_summary.payment_id
LEFT JOIN invoice_header ih ON COALESCE(pd.invoice_id, ar_summary.first_invoice_id) = ih.invoice_id
LEFT JOIN patients p ON COALESCE(ih.patient_id, ar_summary.patient_id) = p.patient_id
LEFT JOIN hospitals h ON pd.hospital_id = h.hospital_id
LEFT JOIN branches b ON ih.branch_id = b.branch_id
WHERE pd.is_deleted = FALSE;

COMMENT ON VIEW v_patient_payment_receipts IS
'Payment-centric view based on ar_subledger: ONE row per payment_id. Shows invoice_count and is_multi_invoice_payment flag. For multi-invoice payments, first invoice shown for compatibility - use detail view to see all allocations.';


-- =====================================================================
-- 2. INVOICE-CENTRIC VIEW (v_patient_invoices) - To be updated
--    One row per invoice_id
--    Aggregates payment data from ar_subledger
-- =====================================================================

-- NOTE: The patient invoice view should also be updated similarly
-- to aggregate payment data from ar_subledger
-- This will be done in a separate migration to keep changes focused

