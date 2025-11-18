-- ============================================================================
-- MIGRATION: Create Consolidated Patient Invoices View
-- ============================================================================
-- Purpose: Deploy v_consolidated_patient_invoices view for Phase 3
-- Author: Claude Code
-- Date: 2025-01-07
-- Version: 1.0
--
-- Instructions:
--   Run this script against the Skinspire database to create the view
--   psql -U skinspire_user -d skinspire_dev -f create_consolidated_patient_invoices_view.sql
-- ============================================================================

\echo '=== Creating Consolidated Patient Invoices View ==='

-- Source: app/database/view scripts/consolidated patient invoices view v1.0.sql

DROP VIEW IF EXISTS v_consolidated_patient_invoices CASCADE;

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
    (
        SELECT COUNT(*)
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    ) AS child_invoice_count,

    (
        SELECT COUNT(*) + 1
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    ) AS total_invoice_count,

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

    -- === PARENT INVOICE AMOUNTS ===
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

    -- === GST INFORMATION ===
    ih.is_gst_invoice,

    -- === CANCELLATION ===
    ih.is_cancelled,
    ih.cancelled_at,
    ih.cancelled_by,
    ih.cancellation_reason,

    -- === AUDIT TRAIL ===
    ih.created_at,
    ih.created_by,
    ih.updated_at,
    ih.updated_by,

    -- === SOFT DELETE ===
    ih.is_deleted,
    ih.deleted_at,
    ih.deleted_by

FROM invoice_header ih
LEFT JOIN hospitals h ON ih.hospital_id = h.hospital_id
LEFT JOIN branches b ON ih.branch_id = b.branch_id
LEFT JOIN patients p ON ih.patient_id = p.patient_id

WHERE
    ih.parent_transaction_id IS NULL
    AND EXISTS (
        SELECT 1
        FROM invoice_header child
        WHERE child.parent_transaction_id = ih.invoice_id
        AND child.hospital_id = ih.hospital_id
    )
    AND (ih.is_deleted IS NULL OR ih.is_deleted = FALSE)

ORDER BY ih.invoice_date DESC, ih.invoice_number DESC;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoice_header_parent_transaction_id
ON invoice_header(parent_transaction_id)
WHERE parent_transaction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_invoice_header_consolidated
ON invoice_header(hospital_id, parent_transaction_id, invoice_date DESC)
WHERE parent_transaction_id IS NULL;

-- Add comment
COMMENT ON VIEW v_consolidated_patient_invoices IS
'Optimized view for Phase 3 tax compliance consolidated invoices. Shows only parent invoices that have child invoices, with aggregated totals across all invoices in the group.';

\echo '=== View created successfully ==='
\echo ''
\echo 'Verification query:'
\echo 'SELECT invoice_number, patient_name, child_invoice_count, consolidated_grand_total FROM v_consolidated_patient_invoices LIMIT 5;'
