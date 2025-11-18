-- ============================================================================
-- Package Payment Plans and Installments
-- Version: 1.0
-- Date: 2025-01-10
-- Description: Create tables for tracking package payment plans and installments
-- ============================================================================

-- Purpose:
-- Supports tracking of service packages sold to patients (e.g., Laser Hair Reduction - 5 sessions)
-- with flexible payment installment schedules.

BEGIN;

-- ============================================================================
-- TABLE 1: package_payment_plans
-- ============================================================================

CREATE TABLE IF NOT EXISTS package_payment_plans (
    -- Primary Key
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Multi-tenant & Branch Support
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(branch_id) ON DELETE SET NULL,

    -- Patient Reference
    patient_id UUID NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,

    -- Package Information
    package_name VARCHAR(255) NOT NULL,
    package_description TEXT,
    package_code VARCHAR(50),

    -- Session Tracking
    total_sessions INTEGER NOT NULL CHECK (total_sessions > 0),
    completed_sessions INTEGER DEFAULT 0 CHECK (completed_sessions >= 0),
    remaining_sessions INTEGER GENERATED ALWAYS AS (total_sessions - completed_sessions) STORED,

    -- Financial Information
    total_amount NUMERIC(12,2) NOT NULL CHECK (total_amount > 0),
    paid_amount NUMERIC(12,2) DEFAULT 0 CHECK (paid_amount >= 0),
    balance_amount NUMERIC(12,2) GENERATED ALWAYS AS (total_amount - paid_amount) STORED,

    -- Installment Configuration
    installment_count INTEGER NOT NULL CHECK (installment_count > 0),
    installment_frequency VARCHAR(20) DEFAULT 'monthly' CHECK (installment_frequency IN ('weekly', 'biweekly', 'monthly', 'custom')),
    first_installment_date DATE NOT NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'suspended')),

    -- Cancellation/Suspension Information
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by VARCHAR(15) REFERENCES users(user_id),
    cancellation_reason TEXT,

    suspended_at TIMESTAMP WITH TIME ZONE,
    suspended_by VARCHAR(15) REFERENCES users(user_id),
    suspension_reason TEXT,

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) NOT NULL REFERENCES users(user_id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15) REFERENCES users(user_id),

    -- Metadata
    notes TEXT,

    -- Indexes for performance
    CONSTRAINT chk_paid_not_exceed_total CHECK (paid_amount <= total_amount),
    CONSTRAINT chk_sessions_valid CHECK (completed_sessions <= total_sessions)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_package_plans_hospital_patient
    ON package_payment_plans(hospital_id, patient_id);

CREATE INDEX IF NOT EXISTS idx_package_plans_status
    ON package_payment_plans(status)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_package_plans_branch
    ON package_payment_plans(branch_id)
    WHERE branch_id IS NOT NULL;

-- Add comment
COMMENT ON TABLE package_payment_plans IS 'Tracks service packages sold to patients with installment payment schedules';

-- ============================================================================
-- TABLE 2: installment_payments
-- ============================================================================

CREATE TABLE IF NOT EXISTS installment_payments (
    -- Primary Key
    installment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Multi-tenant Support
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,

    -- Plan Reference
    plan_id UUID NOT NULL REFERENCES package_payment_plans(plan_id) ON DELETE CASCADE,

    -- Installment Information
    installment_number INTEGER NOT NULL CHECK (installment_number > 0),
    due_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),

    -- Payment Information
    paid_date DATE,
    paid_amount NUMERIC(12,2) DEFAULT 0 CHECK (paid_amount >= 0),
    payment_id UUID REFERENCES payment_details(payment_id) ON DELETE SET NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'partial', 'paid', 'overdue', 'waived')),

    -- Waiver Information
    waived_at TIMESTAMP WITH TIME ZONE,
    waived_by VARCHAR(15) REFERENCES users(user_id),
    waiver_reason TEXT,
    waived_amount NUMERIC(12,2) DEFAULT 0,

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    -- Constraints
    CONSTRAINT chk_paid_not_exceed_installment CHECK (paid_amount <= amount),
    CONSTRAINT uq_plan_installment_number UNIQUE (plan_id, installment_number)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_installment_payments_plan
    ON installment_payments(plan_id, installment_number);

CREATE INDEX IF NOT EXISTS idx_installment_payments_status
    ON installment_payments(status);

CREATE INDEX IF NOT EXISTS idx_installment_payments_due_date
    ON installment_payments(due_date)
    WHERE status IN ('pending', 'partial', 'overdue');

CREATE INDEX IF NOT EXISTS idx_installment_payments_payment
    ON installment_payments(payment_id)
    WHERE payment_id IS NOT NULL;

-- Add comment
COMMENT ON TABLE installment_payments IS 'Tracks individual installment payments for package payment plans';

-- ============================================================================
-- TABLE 3: package_sessions
-- ============================================================================
-- Optional: Track individual service sessions separately from installments

CREATE TABLE IF NOT EXISTS package_sessions (
    -- Primary Key
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Multi-tenant Support
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,

    -- Plan Reference
    plan_id UUID NOT NULL REFERENCES package_payment_plans(plan_id) ON DELETE CASCADE,

    -- Session Information
    session_number INTEGER NOT NULL CHECK (session_number > 0),
    session_date DATE,
    session_status VARCHAR(20) DEFAULT 'scheduled' CHECK (session_status IN ('scheduled', 'completed', 'cancelled', 'no_show')),

    -- Service Details
    service_name VARCHAR(255),
    service_notes TEXT,
    performed_by VARCHAR(15) REFERENCES users(user_id),

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) NOT NULL REFERENCES users(user_id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15) REFERENCES users(user_id),

    CONSTRAINT uq_plan_session_number UNIQUE (plan_id, session_number)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_package_sessions_plan
    ON package_sessions(plan_id, session_number);

CREATE INDEX IF NOT EXISTS idx_package_sessions_status
    ON package_sessions(session_status);

CREATE INDEX IF NOT EXISTS idx_package_sessions_date
    ON package_sessions(session_date)
    WHERE session_date IS NOT NULL;

-- Add comment
COMMENT ON TABLE package_sessions IS 'Tracks individual service sessions for packages (optional, separate from payment installments)';

COMMIT;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Update package status when fully paid
CREATE OR REPLACE FUNCTION update_package_plan_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if all installments are paid
    IF (SELECT COUNT(*) FROM installment_payments
        WHERE plan_id = NEW.plan_id
        AND status NOT IN ('paid', 'waived')) = 0 THEN

        UPDATE package_payment_plans
        SET status = 'completed',
            updated_at = CURRENT_TIMESTAMP
        WHERE plan_id = NEW.plan_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_package_status ON installment_payments;
CREATE TRIGGER trg_update_package_status
    AFTER UPDATE OF status ON installment_payments
    FOR EACH ROW
    WHEN (NEW.status IN ('paid', 'waived'))
    EXECUTE FUNCTION update_package_plan_status();

-- Trigger: Update paid_amount in package_payment_plans
CREATE OR REPLACE FUNCTION update_package_paid_amount()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE package_payment_plans
    SET paid_amount = (
            SELECT COALESCE(SUM(paid_amount), 0)
            FROM installment_payments
            WHERE plan_id = NEW.plan_id
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE plan_id = NEW.plan_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_package_paid_amount ON installment_payments;
CREATE TRIGGER trg_update_package_paid_amount
    AFTER INSERT OR UPDATE OF paid_amount ON installment_payments
    FOR EACH ROW
    EXECUTE FUNCTION update_package_paid_amount();

-- Trigger: Mark overdue installments
CREATE OR REPLACE FUNCTION mark_overdue_installments()
RETURNS void AS $$
BEGIN
    UPDATE installment_payments
    SET status = 'overdue'
    WHERE status = 'pending'
      AND due_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Note: Schedule this to run daily via cron or application scheduler

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify tables created
-- SELECT table_name FROM information_schema.tables
-- WHERE table_name IN ('package_payment_plans', 'installment_payments', 'package_sessions');

-- Verify indexes created
-- SELECT indexname FROM pg_indexes
-- WHERE tablename IN ('package_payment_plans', 'installment_payments', 'package_sessions');

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Example: Create a package plan for testing
-- INSERT INTO package_payment_plans (
--     hospital_id, patient_id, package_name, package_description,
--     total_sessions, total_amount, installment_count,
--     first_installment_date, created_by
-- ) VALUES (
--     'YOUR_HOSPITAL_ID',
--     'YOUR_PATIENT_ID',
--     'Laser Hair Reduction - 5 Sessions',
--     'Full body laser hair reduction package',
--     5,
--     50000.00,
--     3,
--     CURRENT_DATE + INTERVAL '1 week',
--     'ADMIN'
-- );
