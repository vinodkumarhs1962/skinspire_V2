-- =====================================================================
-- Patient Invoices View v1.0
-- Comprehensive view for patient billing invoices with denormalized data
-- Used for: List views, search, filtering, aging reports, payment tracking
-- Created: 2025-01-04
-- =====================================================================

-- Drop view if exists
DROP VIEW IF EXISTS patient_invoices_view CASCADE;

-- Create comprehensive patient invoices view
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
    -- SIMPLIFIED: Just first_name + last_name (NO TITLE)
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
    -- When adding SoftDeleteMixin, uncomment these lines:
    -- ih.is_deleted,
    -- ih.deleted_at,
    -- ih.deleted_by,
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

-- Create indexes for better query performance
-- Note: Indexes are created on base tables, not views
CREATE INDEX IF NOT EXISTS idx_ih_hospital_id ON invoice_header(hospital_id);
CREATE INDEX IF NOT EXISTS idx_ih_branch_id ON invoice_header(branch_id);
CREATE INDEX IF NOT EXISTS idx_ih_patient_id ON invoice_header(patient_id);
CREATE INDEX IF NOT EXISTS idx_ih_invoice_date ON invoice_header(invoice_date);
CREATE INDEX IF NOT EXISTS idx_ih_invoice_number ON invoice_header(invoice_number);
CREATE INDEX IF NOT EXISTS idx_ih_invoice_type ON invoice_header(invoice_type);
CREATE INDEX IF NOT EXISTS idx_ih_is_cancelled ON invoice_header(is_cancelled);
CREATE INDEX IF NOT EXISTS idx_ih_balance_due ON invoice_header(balance_due);
CREATE INDEX IF NOT EXISTS idx_ih_created_at ON invoice_header(created_at);

-- Patient table indexes (if not already exist)
CREATE INDEX IF NOT EXISTS idx_patients_mrn ON patients(mrn);
CREATE INDEX IF NOT EXISTS idx_patients_hospital_id ON patients(hospital_id);
CREATE INDEX IF NOT EXISTS idx_patients_branch_id ON patients(branch_id);

-- Grant permissions
GRANT SELECT ON patient_invoices_view TO PUBLIC;

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================

-- 1. Verify view columns exist:
/*
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'patient_invoices_view'
ORDER BY ordinal_position;
*/

-- 2. Verify critical fields:
/*
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'patient_invoices_view'
AND column_name IN (
    'invoice_id', 'invoice_number', 'patient_name', 'patient_mrn',
    'payment_status', 'aging_bucket', 'search_text'
)
ORDER BY column_name;
*/

-- 3. Test the view with sample data:
/*
SELECT
    invoice_id,
    invoice_number,
    invoice_date,
    patient_name,
    patient_mrn,
    grand_total,
    paid_amount,
    balance_due,
    payment_status,
    aging_bucket,
    invoice_age_days
FROM patient_invoices_view
WHERE hospital_id IS NOT NULL
ORDER BY invoice_date DESC
LIMIT 10;
*/

-- 4. Test payment status distribution:
/*
SELECT
    payment_status,
    COUNT(*) AS invoice_count,
    SUM(grand_total) AS total_amount,
    SUM(balance_due) AS total_outstanding
FROM patient_invoices_view
GROUP BY payment_status
ORDER BY payment_status;
*/

-- 5. Test aging analysis:
/*
SELECT
    aging_bucket,
    COUNT(*) AS invoice_count,
    SUM(balance_due) AS outstanding_amount
FROM patient_invoices_view
WHERE payment_status != 'paid' AND is_cancelled = FALSE
GROUP BY aging_bucket
ORDER BY
    CASE aging_bucket
        WHEN '0-30 days' THEN 1
        WHEN '31-60 days' THEN 2
        WHEN '61-90 days' THEN 3
        WHEN '90+ days' THEN 4
        ELSE 5
    END;
*/

-- =====================================================================
-- MIGRATION NOTES
-- =====================================================================
/*
1. This view assumes invoice_header table has the following structure:
   - Primary keys: invoice_id, hospital_id, branch_id
   - Foreign keys: patient_id
   - Financial fields: total_amount, grand_total, paid_amount, balance_due
   - GST fields: cgst_amount, sgst_amount, igst_amount (optional)
   - Status fields: is_cancelled, cancellation_reason, cancelled_at, cancelled_by
   - Audit fields: created_at, created_by, updated_at, updated_by
   - Soft delete fields: is_deleted, deleted_at, deleted_by (to be added)

2. If invoice_header doesn't have certain fields (like cgst_amount, last_payment_date, etc.),
   you may need to adjust the SELECT statement to remove those columns or add them to the table.

3. Soft delete fields (is_deleted, deleted_at, deleted_by) will be NULL until SoftDeleteMixin
   is added to the InvoiceHeader model.

4. After creating this view, update app/models/views.py to add the PatientInvoiceView model class.

5. Register the entity in app/config/entity_registry.py as 'patient_invoices'.
*/
