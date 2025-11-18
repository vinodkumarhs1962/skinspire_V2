-- =====================================================================
-- Fix Patient Payment Receipts View - Payment-Centric (One Row Per Payment)
-- Based on payment_details table with LEFT JOIN to invoice_header
-- Supports payments without invoice_id (multi-invoice payments via ar_subledger)
-- =====================================================================

-- Drop existing view
DROP VIEW IF EXISTS v_patient_payment_receipts CASCADE;

-- Create payment-centric view (one row per payment)
CREATE OR REPLACE VIEW v_patient_payment_receipts AS
SELECT
    -- === PRIMARY IDENTIFICATION ===
    pd.payment_id,
    pd.hospital_id,
    h.name AS hospital_name,

    -- === INVOICE REFERENCE (May be NULL for multi-invoice payments) ===
    pd.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    ih.invoice_type,

    -- === PATIENT INFORMATION ===
    -- For multi-invoice payments (invoice_id NULL), get patient from ar_subledger
    COALESCE(
        ih.patient_id,
        (SELECT ar.patient_id
         FROM ar_subledger ar
         WHERE ar.gl_transaction_id IN (
             SELECT gl_transaction_id
             FROM ar_subledger
             WHERE reference_id = pd.payment_id AND reference_type = 'payment'
         )
         AND ar.reference_type = 'invoice'
         LIMIT 1)
    ) AS patient_id,
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
    pd.receipt_number,

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

    -- === RECONCILIATION STATUS ===
    pd.reconciliation_status,
    pd.reconciliation_date,
    pd.reconciliation_reference,

    -- === REFUND INFORMATION ===
    pd.refund_date,
    pd.refund_reason,
    CASE WHEN pd.refunded_amount > 0 THEN TRUE ELSE FALSE END AS has_refund,

    -- === BRANCH INFORMATION ===
    COALESCE(ih.branch_id, pd.branch_id) AS branch_id,
    b.name AS branch_name,

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

    -- === SEARCH HELPER FIELD ===
    LOWER(
        COALESCE(ih.invoice_number, '') || ' ' ||
        COALESCE(p.mrn, '') || ' ' ||
        COALESCE(p.personal_info->>'first_name', '') || ' ' ||
        COALESCE(p.personal_info->>'last_name', '') || ' ' ||
        COALESCE(p.contact_info->>'phone', '') || ' ' ||
        COALESCE(pd.reference_number, '') || ' ' ||
        COALESCE(pd.notes, '')
    ) AS search_vector,

    -- === AUDIT FIELDS ===
    pd.created_by,
    pd.created_at,
    pd.updated_by,
    pd.updated_at,
    pd.is_deleted,

    -- === NOTES ===
    pd.notes

FROM
    payment_details pd
    LEFT JOIN invoice_header ih ON pd.invoice_id = ih.invoice_id  -- ✅ LEFT JOIN - invoice_id may be NULL
    LEFT JOIN patients p ON COALESCE(
        ih.patient_id,
        (SELECT ar.patient_id FROM ar_subledger ar
         WHERE ar.gl_transaction_id IN (
             SELECT gl_transaction_id FROM ar_subledger
             WHERE reference_id = pd.payment_id AND reference_type = 'payment'
         )
         AND ar.reference_type = 'invoice'
         LIMIT 1)
    ) = p.patient_id
    LEFT JOIN hospitals h ON pd.hospital_id = h.hospital_id
    LEFT JOIN branches b ON COALESCE(ih.branch_id, pd.branch_id) = b.branch_id
WHERE
    pd.is_deleted = FALSE;

-- Add comment
COMMENT ON VIEW v_patient_payment_receipts IS
'Payment-centric view: ONE row per payment. Uses LEFT JOIN to invoice_header - supports multi-invoice payments (payment → multiple invoices tracked in ar_subledger). For multi-invoice payments, invoice_number will be NULL - use detail view to see all invoices.';
