-- ============================================================================
-- CONSOLIDATED PATIENT INVOICES VIEW - CLEAN VERSION (Pure SQL)
-- ============================================================================
-- Run this script in pgAdmin, DBeaver, or any PostgreSQL client
-- ============================================================================

-- Drop existing view if it exists
DROP VIEW IF EXISTS v_consolidated_patient_invoices CASCADE;

-- Create the consolidated invoices view
CREATE OR REPLACE VIEW v_consolidated_patient_invoices AS
SELECT
    -- === PRIMARY IDENTIFICATION ===
    ih.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    ih.invoice_type,

    -- === TENANT & BRANCH ===
    ih.hospital_id,
    ih.branch_id,
    h.name AS hospital_name,
    b.name AS branch_name,

    -- === PATIENT INFORMATION ===
    ih.patient_id,
    p.full_name AS patient_name,
    p.mrn AS patient_mrn,
    p.contact_info->>'mobile' AS patient_phone,
    p.contact_info->>'email' AS patient_email,

    -- === SPLIT INVOICE TRACKING ===
    -- Count of child invoices
    (
        SELECT COUNT(*)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    ) AS child_invoice_count,

    -- Total invoices in group (parent + children)
    (
        SELECT COUNT(*) + 1
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    ) AS total_invoice_count,

    -- === CONSOLIDATED AMOUNTS (parent + all children) ===
    (
        SELECT COALESCE(SUM(child.grand_total), 0)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    ) + COALESCE(ih.grand_total, 0) AS consolidated_grand_total,

    (
        SELECT COALESCE(SUM(child.paid_amount), 0)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    ) + COALESCE(ih.paid_amount, 0) AS consolidated_paid_amount,

    (
        SELECT COALESCE(SUM(child.balance_due), 0)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    ) + COALESCE(ih.balance_due, 0) AS consolidated_balance_due,

    -- === PARENT INVOICE AMOUNTS (for reference) ===
    ih.total_amount AS parent_total_amount,
    ih.total_discount AS parent_discount,
    ih.total_taxable_value AS parent_taxable,
    ih.total_cgst_amount AS parent_cgst,
    ih.total_sgst_amount AS parent_sgst,
    ih.total_igst_amount AS parent_igst,
    ih.grand_total AS parent_grand_total,
    ih.paid_amount AS parent_paid_amount,
    ih.balance_due AS parent_balance_due,

    -- === PAYMENT STATUS ===
    CASE
        WHEN (
            SELECT COALESCE(SUM(child.balance_due), 0)
            FROM invoice_header child
            WHERE child.parent_transaction_id = ih.invoice_id
        ) + COALESCE(ih.balance_due, 0) <= 0.01 THEN 'paid'
        WHEN (
            SELECT COALESCE(SUM(child.paid_amount), 0)
            FROM invoice_header child
            WHERE child.parent_transaction_id = ih.invoice_id
        ) + COALESCE(ih.paid_amount, 0) > 0 THEN 'partial'
        ELSE 'unpaid'
    END AS payment_status,

    -- === CATEGORY BREAKDOWN ===
    (
        SELECT COUNT(*)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.invoice_number LIKE 'SVC/%'
    ) AS service_invoice_count,

    (
        SELECT COUNT(*)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.invoice_number LIKE 'MED/%'
    ) AS medicine_invoice_count,

    (
        SELECT COUNT(*)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.invoice_number LIKE 'EXM/%'
    ) AS exempt_invoice_count,

    (
        SELECT COUNT(*)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.invoice_number LIKE 'RX/%'
    ) AS prescription_invoice_count,

    -- === AGING ===
    CURRENT_DATE - ih.invoice_date::date AS invoice_age_days,
    CASE
        WHEN CURRENT_DATE - ih.invoice_date::date <= 30 THEN '0-30 days'
        WHEN CURRENT_DATE - ih.invoice_date::date <= 60 THEN '31-60 days'
        WHEN CURRENT_DATE - ih.invoice_date::date <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END AS aging_bucket,

    -- === GST & STATUS ===
    ih.is_gst_invoice,
    ih.is_cancelled,

    -- === AUDIT TRAIL ===
    ih.created_at,
    ih.created_by,
    ih.updated_at,
    ih.updated_by

FROM invoice_header ih
LEFT JOIN hospitals h ON ih.hospital_id = h.hospital_id
LEFT JOIN branches b ON ih.branch_id = b.branch_id
LEFT JOIN patients p ON ih.patient_id = p.patient_id

WHERE
    -- Parent invoices only (no parent_transaction_id)
    ih.parent_transaction_id IS NULL

    -- Must have at least one child invoice
    AND EXISTS (
        SELECT 1
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    )

ORDER BY ih.invoice_date DESC, ih.invoice_number DESC;

-- Create performance indexes (if they don't already exist)
CREATE INDEX IF NOT EXISTS idx_invoice_header_parent_transaction_id
ON invoice_header(parent_transaction_id)
WHERE parent_transaction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_invoice_header_consolidated
ON invoice_header(hospital_id, parent_transaction_id, invoice_date DESC)
WHERE parent_transaction_id IS NULL;

-- Add view comment
COMMENT ON VIEW v_consolidated_patient_invoices IS
'Phase 3 consolidated invoices view - shows only parent invoices with children and aggregated totals';

-- Verification query (run separately if needed)
-- SELECT
--     invoice_number,
--     patient_name,
--     child_invoice_count,
--     total_invoice_count,
--     consolidated_grand_total,
--     payment_status
-- FROM v_consolidated_patient_invoices
-- LIMIT 5;
