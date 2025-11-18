-- ============================================================================
-- Package Payment Plans View v1.0
-- Comprehensive view with patient, package, and invoice details
-- Created: 2025-01-11
-- ============================================================================

CREATE OR REPLACE VIEW package_payment_plans_view AS
SELECT
    -- Primary Keys
    ppp.plan_id,
    ppp.hospital_id,
    ppp.branch_id,

    -- Patient Information
    ppp.patient_id,
    p.full_name AS patient_name,
    p.first_name AS patient_first_name,
    p.last_name AS patient_last_name,
    p.mrn,
    (p.contact_info->>'phone')::VARCHAR AS patient_phone,
    (p.contact_info->>'email')::VARCHAR AS patient_email,
    (p.personal_info->>'date_of_birth')::DATE AS patient_dob,
    (p.personal_info->>'gender')::VARCHAR AS patient_gender,

    -- Invoice Information
    ppp.invoice_id,
    ih.invoice_number,
    ih.invoice_date,
    CASE
        WHEN ih.is_cancelled THEN 'cancelled'
        WHEN ih.balance_due = 0 THEN 'paid'
        WHEN ih.paid_amount > 0 THEN 'partial'
        ELSE 'pending'
    END AS invoice_status,
    ih.grand_total AS invoice_total,
    ih.paid_amount AS invoice_paid,
    ih.balance_due AS invoice_balance,

    -- Package Information
    ppp.package_id,
    pkg.package_name,
    pkg.price AS package_price,
    ppp.package_code,
    ppp.package_description,

    -- Session Information
    ppp.total_sessions,
    ppp.completed_sessions,
    ppp.remaining_sessions,
    CASE
        WHEN ppp.total_sessions > 0 THEN
            ROUND((ppp.completed_sessions::NUMERIC / ppp.total_sessions::NUMERIC) * 100, 2)
        ELSE 0
    END AS session_completion_percentage,

    -- Financial Information
    ppp.total_amount,
    ppp.paid_amount,
    ppp.balance_amount,
    CASE
        WHEN ppp.total_amount > 0 THEN
            ROUND((ppp.paid_amount::NUMERIC / ppp.total_amount::NUMERIC) * 100, 2)
        ELSE 0
    END AS payment_percentage,

    -- Installment Configuration
    ppp.installment_count,
    ppp.installment_frequency,
    ppp.first_installment_date,

    -- Status Information
    ppp.status,
    CASE
        WHEN ppp.status = 'active' THEN 'success'
        WHEN ppp.status = 'completed' THEN 'info'
        WHEN ppp.status = 'cancelled' THEN 'danger'
        WHEN ppp.status = 'suspended' THEN 'warning'
        ELSE 'secondary'
    END AS status_badge_color,

    -- Cancellation Information
    ppp.cancelled_at,
    ppp.cancelled_by,
    ppp.cancellation_reason,

    -- Suspension Information
    ppp.suspended_at,
    ppp.suspended_by,
    ppp.suspension_reason,

    -- Notes
    ppp.notes,

    -- Audit Information
    ppp.created_at,
    ppp.created_by,
    ppp.updated_at,
    ppp.updated_by,

    -- Soft Delete Information
    ppp.is_deleted,
    ppp.deleted_at,
    ppp.deleted_by,

    -- Branch Information
    b.name AS branch_name,

    -- Hospital Information
    h.name AS hospital_name,

    -- Computed Display Fields
    p.full_name || ' (' || p.mrn || ')' AS patient_display,
    pkg.package_name || ' - ₹' || TO_CHAR(pkg.price, 'FM999,999,990.00') AS package_display,
    'Plan #' || ppp.plan_id AS plan_display,

    -- Age Calculation
    DATE_PART('day', CURRENT_DATE - ppp.created_at) AS plan_age_days,

    -- Next Due Date (earliest unpaid installment)
    (
        SELECT MIN(ip.due_date)
        FROM installment_payments ip
        WHERE ip.plan_id = ppp.plan_id
        AND ip.status IN ('pending', 'partial')
        AND ip.hospital_id = ppp.hospital_id
    ) AS next_due_date,

    -- Next Session Date (earliest scheduled session)
    (
        SELECT MIN(ps.session_date)
        FROM package_sessions ps
        WHERE ps.plan_id = ppp.plan_id
        AND ps.session_status = 'scheduled'
        AND ps.hospital_id = ppp.hospital_id
    ) AS next_session_date,

    -- Overdue Status
    CASE
        WHEN EXISTS (
            SELECT 1 FROM installment_payments ip
            WHERE ip.plan_id = ppp.plan_id
            AND ip.status = 'overdue'
            AND ip.hospital_id = ppp.hospital_id
        ) THEN true
        ELSE false
    END AS has_overdue_installments

FROM package_payment_plans ppp

-- Join Patient
INNER JOIN patients p ON ppp.patient_id = p.patient_id
    AND p.hospital_id = ppp.hospital_id

-- Join Package (LEFT JOIN as it may be null during transition)
LEFT JOIN packages pkg ON ppp.package_id = pkg.package_id
    AND pkg.hospital_id = ppp.hospital_id

-- Join Invoice (LEFT JOIN as may be null)
LEFT JOIN invoice_header ih ON ppp.invoice_id = ih.invoice_id
    AND ih.hospital_id = ppp.hospital_id

-- Join Branch (LEFT JOIN as branch_id may be null)
LEFT JOIN branches b ON ppp.branch_id = b.branch_id
    AND b.hospital_id = ppp.hospital_id

-- Join Hospital
INNER JOIN hospitals h ON ppp.hospital_id = h.hospital_id

WHERE ppp.is_deleted = false;  -- Exclude soft-deleted records by default

-- ============================================================================
-- Create Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_package_plans_view_hospital
ON package_payment_plans(hospital_id) WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_package_plans_view_patient
ON package_payment_plans(patient_id) WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_package_plans_view_status
ON package_payment_plans(status) WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_package_plans_view_created_at
ON package_payment_plans(created_at DESC) WHERE is_deleted = false;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON VIEW package_payment_plans_view IS 'Comprehensive view of package payment plans with patient, package, invoice, and computed fields';

-- ============================================================================
-- Sample Queries
-- ============================================================================

-- Query 1: Get all active plans for a patient
-- SELECT * FROM package_payment_plans_view
-- WHERE patient_id = '<patient_uuid>'
-- AND hospital_id = '<hospital_uuid>'
-- AND status = 'active'
-- ORDER BY created_at DESC;

-- Query 2: Get plans with overdue installments
-- SELECT * FROM package_payment_plans_view
-- WHERE hospital_id = '<hospital_uuid>'
-- AND has_overdue_installments = true
-- ORDER BY next_due_date ASC;

-- Query 3: Get plans by package
-- SELECT * FROM package_payment_plans_view
-- WHERE package_id = '<package_uuid>'
-- AND hospital_id = '<hospital_uuid>'
-- ORDER BY created_at DESC;

-- Query 4: Get plans created in date range
-- SELECT * FROM package_payment_plans_view
-- WHERE hospital_id = '<hospital_uuid>'
-- AND created_at BETWEEN '2025-01-01' AND '2025-12-31'
-- ORDER BY created_at DESC;
