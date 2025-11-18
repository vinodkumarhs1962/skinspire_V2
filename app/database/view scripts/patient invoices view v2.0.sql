-- =====================================================================
-- Patient Invoices View v2.0
-- Comprehensive view for patient billing invoices with denormalized data
-- NEW in v2.0: Split invoice tracking for batch allocation and GST splitting
-- Used for: List views, search, filtering, aging reports, payment tracking
-- Created: 2025-01-06
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
    COALESCE(p.mrn, '') AS patient_mrn,
    -- FIXED: first_name + last_name (NO TITLE) - check both regular columns and JSONB
    COALESCE(
        NULLIF(TRIM(CONCAT(
            COALESCE(p.first_name, p.personal_info->>'first_name', ''),
            CASE WHEN COALESCE(p.first_name, p.personal_info->>'first_name') IS NOT NULL
                  AND COALESCE(p.last_name, p.personal_info->>'last_name') IS NOT NULL
                  THEN ' ' ELSE '' END,
            COALESCE(p.last_name, p.personal_info->>'last_name', '')
        )), ''),
        p.full_name,
        'Unknown'
    ) AS patient_name,
    COALESCE(p.title, p.personal_info->>'title') AS patient_title,
    COALESCE(p.first_name, p.personal_info->>'first_name') AS patient_first_name,
    COALESCE(p.last_name, p.personal_info->>'last_name') AS patient_last_name,
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

    -- ===================================================================
    -- NEW IN V2.0: Split Invoice Tracking
    -- ===================================================================

    -- Split invoice fields from current invoice
    ih.parent_transaction_id,
    ih.split_sequence,
    ih.is_split_invoice,
    ih.split_reason,

    -- Parent invoice information (if this is a split invoice)
    parent_ih.invoice_number AS parent_invoice_number,
    parent_ih.invoice_date AS parent_invoice_date,
    parent_ih.grand_total AS parent_grand_total,

    -- Child invoice aggregation (if this is a parent invoice)
    (
        SELECT COUNT(*)
        FROM invoice_header child_ih
        WHERE child_ih.parent_transaction_id = ih.invoice_id
    ) AS split_invoice_count,

    (
        SELECT SUM(child_ih.grand_total)
        FROM invoice_header child_ih
        WHERE child_ih.parent_transaction_id = ih.invoice_id
    ) AS split_invoices_total,

    -- ===================================================================
    -- END: Split Invoice Tracking
    -- ===================================================================

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
        COALESCE(ih.notes, '') || ' ' ||
        COALESCE(parent_ih.invoice_number, '')  -- Include parent invoice number in search
    ) AS search_text

FROM
    invoice_header ih
    LEFT JOIN patients p ON ih.patient_id = p.patient_id
    LEFT JOIN branches b ON ih.branch_id = b.branch_id
    LEFT JOIN hospitals h ON ih.hospital_id = h.hospital_id
    -- NEW: Join to parent invoice for split invoice tracking
    LEFT JOIN invoice_header parent_ih ON ih.parent_transaction_id = parent_ih.invoice_id;

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

-- NEW: Indexes for split invoice tracking (created by migration script)
-- CREATE INDEX IF NOT EXISTS idx_invoice_parent_transaction ON invoice_header(parent_transaction_id) WHERE parent_transaction_id IS NOT NULL;
-- CREATE INDEX IF NOT EXISTS idx_invoice_is_split ON invoice_header(is_split_invoice) WHERE is_split_invoice = TRUE;

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

-- 2. Verify split invoice tracking fields:
/*
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'patient_invoices_view'
AND column_name IN (
    'parent_transaction_id', 'split_sequence', 'is_split_invoice', 'split_reason',
    'parent_invoice_number', 'split_invoice_count', 'split_invoices_total'
)
ORDER BY column_name;
*/

-- 3. Test split invoice relationships:
/*
-- Show all split invoices with their parent
SELECT
    ih.invoice_number,
    ih.is_split_invoice,
    ih.split_sequence,
    ih.split_reason,
    parent.invoice_number AS parent_number,
    ih.grand_total
FROM invoice_header ih
LEFT JOIN invoice_header parent ON ih.parent_transaction_id = parent.invoice_id
WHERE ih.is_split_invoice = TRUE
ORDER BY parent.invoice_number, ih.split_sequence;
*/

-- 4. Test consolidated view (parent with all children):
/*
SELECT
    parent.invoice_number AS parent_invoice,
    parent.invoice_date,
    parent.grand_total AS parent_total,
    COUNT(child.invoice_id) AS child_count,
    SUM(child.grand_total) AS children_total
FROM invoice_header parent
LEFT JOIN invoice_header child ON child.parent_transaction_id = parent.invoice_id
WHERE parent.is_split_invoice = FALSE
GROUP BY parent.invoice_id, parent.invoice_number, parent.invoice_date, parent.grand_total
HAVING COUNT(child.invoice_id) > 0;
*/

-- =====================================================================
-- MIGRATION NOTES
-- =====================================================================
/*
VERSION 2.0 CHANGES:
1. Added split invoice tracking fields:
   - parent_transaction_id: Links to parent invoice when split
   - split_sequence: Order of split invoices (1, 2, 3...)
   - is_split_invoice: Flag indicating this is part of a split
   - split_reason: Reason for split (BATCH_ALLOCATION, GST_SPLIT, etc.)

2. Added parent invoice information for context:
   - parent_invoice_number: Display parent invoice number
   - parent_invoice_date: Date of parent invoice
   - parent_grand_total: Total amount of parent invoice

3. Added child invoice aggregation:
   - split_invoice_count: Number of child invoices
   - split_invoices_total: Sum of all child invoice amounts

4. Updated search_text to include parent invoice number

5. Prerequisites:
   - Run migrations/add_split_invoice_tracking.sql FIRST
   - Update app/models/transaction.py InvoiceHeader model with new fields
   - Update app/models/views.py PatientInvoiceView model with new columns

USAGE SCENARIOS:
- Single invoice: is_split_invoice=FALSE, parent_transaction_id=NULL, split_invoice_count=0
- Parent of split invoices: is_split_invoice=FALSE, parent_transaction_id=NULL, split_invoice_count>0
- Child split invoice: is_split_invoice=TRUE, parent_transaction_id=<parent_id>, split_sequence=1,2,3...
*/
