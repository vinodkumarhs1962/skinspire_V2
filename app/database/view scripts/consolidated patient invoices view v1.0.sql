-- ============================================================================
-- CONSOLIDATED PATIENT INVOICES VIEW v1.0
-- ============================================================================
-- Purpose: Provides optimized view of parent invoices with split children
--
-- Use Case: Phase 3 Tax Compliance - Multi-invoice transactions
--
-- Scope: Shows ONLY parent invoices that have child invoices
--        (Filters out single invoices and child invoices)
--
-- Author: Claude Code
-- Created: 2025-01-07
-- Version: 1.0
-- ============================================================================

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
    -- Use display_name from patient_master_view (already handles JSONB extraction)
    COALESCE(p.display_name, 'Unknown') AS patient_name,
    COALESCE(p.mrn, '') AS patient_mrn,
    -- Use pre-flattened fields from patient_master_view
    p.phone AS patient_phone,
    p.email AS patient_email,
    p.address AS patient_address,
    p.blood_group AS patient_blood_group,

    -- === SPLIT INVOICE TRACKING ===
    -- Count of child invoices for this parent
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

    -- Aggregated amounts from ALL invoices (parent + children)
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
    -- Count of invoices by category
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

    -- === AUDIT TRAIL ===
    ih.created_at,
    ih.created_by,
    ih.updated_at,
    ih.updated_by

FROM invoice_header ih

-- Join hospital for name
LEFT JOIN hospitals h ON ih.hospital_id = h.hospital_id

-- Join branch for name
LEFT JOIN branches b ON ih.branch_id = b.branch_id

-- Join patient for details (using flattened view)
LEFT JOIN patient_master_view p ON ih.patient_id = p.patient_id

-- === CRITICAL FILTER ===
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

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
-- Note: Indexes are on base tables (invoice_header), not on the view

-- Index on parent_transaction_id for child lookups (if not already exists)
CREATE INDEX IF NOT EXISTS idx_invoice_header_parent_transaction_id
ON invoice_header(parent_transaction_id)
WHERE parent_transaction_id IS NOT NULL;

-- Index for consolidated invoice queries
CREATE INDEX IF NOT EXISTS idx_invoice_header_consolidated
ON invoice_header(hospital_id, parent_transaction_id, invoice_date DESC)
WHERE parent_transaction_id IS NULL;

-- ============================================================================
-- PERMISSIONS
-- ============================================================================
-- Grant select permission to application user
-- GRANT SELECT ON v_consolidated_patient_invoices TO skinspire_app_user;

-- ============================================================================
-- DOCUMENTATION
-- ============================================================================

COMMENT ON VIEW v_consolidated_patient_invoices IS
'Optimized view for Phase 3 tax compliance consolidated invoices. Shows only parent invoices that have child invoices, with aggregated totals across all invoices in the group.';

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Get all consolidated invoices for a hospital
-- SELECT * FROM v_consolidated_patient_invoices
-- WHERE hospital_id = 'your-hospital-uuid';

-- Example 2: Get unpaid consolidated invoices
-- SELECT * FROM v_consolidated_patient_invoices
-- WHERE payment_status = 'unpaid';

-- Example 3: Get consolidated invoices with aging
-- SELECT invoice_number, patient_name, consolidated_balance_due, aging_bucket
-- FROM v_consolidated_patient_invoices
-- WHERE payment_status != 'paid'
-- ORDER BY invoice_age_days DESC;

-- ============================================================================
-- FIELD DESCRIPTIONS
-- ============================================================================
/*
PRIMARY FIELDS:
- invoice_id: Parent invoice UUID
- invoice_number: Parent invoice number
- invoice_date: Date of parent invoice
- patient_name: Full name of patient

CONSOLIDATED COUNTS:
- child_invoice_count: Number of child invoices (excludes parent)
- total_invoice_count: Total invoices in group (parent + children)
- service_invoice_count: Count of SVC/ invoices
- medicine_invoice_count: Count of MED/ invoices
- exempt_invoice_count: Count of EXM/ invoices
- prescription_invoice_count: Count of RX/ invoices

CONSOLIDATED AMOUNTS:
- consolidated_grand_total: Sum of all invoices (parent + children)
- consolidated_paid_amount: Total paid across all invoices
- consolidated_balance_due: Total balance remaining

PARENT AMOUNTS:
- parent_*: Original amounts from parent invoice only

PAYMENT STATUS:
- paid: All invoices fully paid (balance <= 0.01)
- partial: Some payments received
- unpaid: No payments received

AGING:
- invoice_age_days: Days since invoice date
- aging_bucket: Categorized age (0-30, 31-60, 61-90, 90+)
*/
