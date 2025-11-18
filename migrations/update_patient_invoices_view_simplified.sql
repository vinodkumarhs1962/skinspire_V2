-- Migration: Simplify patient_invoices_view - Remove title, use only first_name + last_name
-- Date: 2025-11-05
-- Description: Update patient_invoices_view to show patient names without title

-- Drop existing view
DROP VIEW IF EXISTS patient_invoices_view CASCADE;

-- Recreate view with simplified patient name (no title)
CREATE OR REPLACE VIEW patient_invoices_view AS
SELECT
    -- Invoice header
    ih.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    ih.invoice_type,
    ih.is_gst_invoice,

    -- Patient info - SIMPLIFIED: Just first_name + last_name (NO TITLE)
    ih.patient_id,
    COALESCE(p.mrn, 'Unknown') AS patient_mrn,
    COALESCE(
        NULLIF(TRIM(CONCAT(
            COALESCE(p.first_name, ''),
            CASE WHEN p.first_name IS NOT NULL AND p.last_name IS NOT NULL THEN ' ' ELSE '' END,
            COALESCE(p.last_name, '')
        )), ''),
        p.full_name,
        'Unknown Patient'
    ) AS patient_name,
    p.title AS patient_title,
    p.first_name AS patient_first_name,
    p.last_name AS patient_last_name,
    p.blood_group AS patient_blood_group,

    -- Amounts
    ih.subtotal_amount,
    ih.gst_amount,
    ih.total_amount,
    ih.paid_amount,
    ih.outstanding_amount,

    -- Status
    ih.payment_status,
    ih.invoice_status,

    -- Metadata
    ih.hospital_id,
    ih.branch_id,
    ih.created_at,
    ih.created_by,
    ih.updated_at,
    ih.updated_by

FROM invoice_header ih
LEFT JOIN patients p ON ih.patient_id = p.patient_id;
LEFT JOIN branches b ON ih.branch_id = b.branch_id;
LEFT JOIN hospitals h ON ih.hospital_id = h.hospital_id;

-- Verify the update
SELECT 'Migration completed successfully. Sample data:' AS status;
SELECT invoice_number, patient_name FROM patient_invoices_view LIMIT 5;
