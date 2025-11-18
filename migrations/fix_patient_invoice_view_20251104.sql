-- =====================================================================
-- Fix Patient Invoice View - Patient Name Construction
-- Date: 2025-11-04
-- Issue: Patient names showing only title (Mr./Mrs.) or encoding symbols
-- Fix: Construct name from title + first_name + last_name parts
-- =====================================================================

-- Drop and recreate the view with fixed patient name logic
DROP VIEW IF EXISTS patient_invoices_view CASCADE;

CREATE OR REPLACE VIEW patient_invoices_view AS
SELECT
    -- Primary identifiers
    ih.invoice_id,
    ih.hospital_id,
    ih.branch_id,
    ih.invoice_number,

    -- Dates
    ih.invoice_date,
    EXTRACT(YEAR FROM ih.invoice_date) AS invoice_year,
    EXTRACT(MONTH FROM ih.invoice_date) AS invoice_month,
    TO_CHAR(ih.invoice_date, 'YYYY-MM') AS invoice_month_year,
    TO_CHAR(ih.invoice_date, 'Q') AS invoice_quarter,
    TO_CHAR(ih.invoice_date, 'Day') AS invoice_day_name,

    -- Invoice classification
    ih.invoice_type,  -- Service, Product, Prescription, Misc
    ih.is_gst_invoice,

    -- Patient information (denormalized)
    ih.patient_id,
    COALESCE(p.mrn, 'Unknown') AS patient_mrn,
    -- FIXED: Construct name from parts (title + first_name + last_name), fallback to full_name
    COALESCE(
        NULLIF(TRIM(CONCAT(
            COALESCE(p.title, ''),
            CASE WHEN p.title IS NOT NULL THEN ' ' ELSE '' END,
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
    COALESCE(p.personal_info->>'gender', '') AS patient_gender,
    COALESCE(p.personal_info->>'date_of_birth', '') AS patient_dob,
    COALESCE(p.contact_info->>'phone', '') AS patient_phone,
    COALESCE(p.contact_info->>'mobile', '') AS patient_mobile,
    COALESCE(p.contact_info->>'email', '') AS patient_email,
    p.is_active AS patient_is_active,

    -- Branch information
    b.name AS branch_name,
    b.state_code AS branch_state_code,
    b.is_active AS branch_is_active,

    -- Hospital information
    h.name AS hospital_name,
    h.license_no AS hospital_license_no,
    h.gst_registration_number AS hospital_gst,

    -- Financial information
    ih.total_amount,
    ih.total_discount,
    ih.total_taxable_value,
    ih.grand_total,
    ih.paid_amount,
    ih.balance_due,

    -- GST breakdown
    ih.total_cgst_amount,
    ih.total_sgst_amount,
    ih.total_igst_amount,
    COALESCE(ih.total_cgst_amount, 0) + COALESCE(ih.total_sgst_amount, 0) + COALESCE(ih.total_igst_amount, 0) AS total_gst_amount,

    -- GST Information
    ih.place_of_supply,
    ih.reverse_charge,
    ih.e_invoice_irn,
    ih.is_interstate,

    -- Currency
    ih.currency_code,
    ih.exchange_rate,

    -- Payment status calculation
    CASE
        WHEN ih.is_cancelled = TRUE THEN 'cancelled'
        WHEN COALESCE(ih.balance_due, ih.grand_total) <= 0 THEN 'paid'
        WHEN COALESCE(ih.paid_amount, 0) > 0 THEN 'partial'
        ELSE 'unpaid'
    END AS payment_status,

    -- Status order for sorting
    CASE
        WHEN ih.is_cancelled = TRUE THEN 4
        WHEN COALESCE(ih.balance_due, ih.grand_total) <= 0 THEN 3
        WHEN COALESCE(ih.paid_amount, 0) > 0 THEN 2
        ELSE 1
    END AS status_order,

    -- Cancellation information
    ih.is_cancelled,
    ih.cancellation_reason,
    ih.cancelled_at,

    -- Invoice age calculation
    CASE
        WHEN ih.invoice_date IS NOT NULL
        THEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - ih.invoice_date))::INTEGER
        ELSE 0
    END AS invoice_age_days,

    -- Aging bucket for reports
    CASE
        WHEN ih.is_cancelled = TRUE THEN 'Cancelled'
        WHEN COALESCE(ih.balance_due, ih.grand_total) <= 0 THEN 'Paid'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - ih.invoice_date)) <= 30 THEN '0-30 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - ih.invoice_date)) <= 60 THEN '31-60 days'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - ih.invoice_date)) <= 90 THEN '61-90 days'
        ELSE '90+ days'
    END AS aging_bucket,

    -- Aging status
    CASE
        WHEN ih.is_cancelled = TRUE THEN 'Cancelled'
        WHEN COALESCE(ih.balance_due, ih.grand_total) <= 0 THEN 'Paid'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - ih.invoice_date)) <= 30 THEN 'Current'
        WHEN EXTRACT(DAY FROM (CURRENT_TIMESTAMP - ih.invoice_date)) <= 60 THEN 'Overdue'
        ELSE 'Severely Overdue'
    END AS aging_status,

    -- GL Account
    ih.gl_account_id,

    -- Notes
    ih.notes,

    -- Audit fields
    ih.created_at,
    ih.created_by,
    ih.updated_at,
    ih.updated_by,

    -- Soft delete fields
    -- Note: InvoiceHeader does NOT have SoftDeleteMixin yet
    -- These fields will be NULL until SoftDeleteMixin is added to InvoiceHeader model
    NULL::BOOLEAN AS is_deleted,
    NULL::TIMESTAMP WITH TIME ZONE AS deleted_at,
    NULL::VARCHAR(50) AS deleted_by,

    -- Search helper field for text search
    LOWER(
        COALESCE(ih.invoice_number, '') || ' ' ||
        COALESCE(p.mrn, '') || ' ' ||
        COALESCE(p.full_name, '') || ' ' ||
        COALESCE(p.first_name, '') || ' ' ||
        COALESCE(p.last_name, '') || ' ' ||
        COALESCE(p.personal_info->>'first_name', '') || ' ' ||
        COALESCE(p.personal_info->>'last_name', '') || ' ' ||
        COALESCE(p.contact_info->>'phone', '') || ' ' ||
        COALESCE(p.contact_info->>'mobile', '') || ' ' ||
        COALESCE(ih.notes, '')
    ) AS search_text

FROM
    invoice_header ih
    LEFT JOIN patients p ON ih.patient_id = p.patient_id
    LEFT JOIN branches b ON ih.branch_id = b.branch_id
    LEFT JOIN hospitals h ON ih.hospital_id = h.hospital_id;

-- Grant permissions
GRANT SELECT ON patient_invoices_view TO PUBLIC;

-- =====================================================================
-- VERIFICATION QUERY
-- =====================================================================
-- Run this to verify patient names are displaying correctly:
/*
SELECT
    invoice_number,
    patient_mrn,
    patient_title,
    patient_first_name,
    patient_last_name,
    patient_name,
    payment_status
FROM patient_invoices_view
ORDER BY created_at DESC
LIMIT 10;
*/
