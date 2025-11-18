-- Migration: Create patient_credit_notes table
-- Date: 2025-11-12
-- Purpose: Track credit notes issued against patient invoices (for plan discontinuations, refunds, etc.)

CREATE TABLE IF NOT EXISTS patient_credit_notes (
    credit_note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID REFERENCES branches(branch_id),

    -- References
    credit_note_number VARCHAR(50) NOT NULL,
    original_invoice_id UUID NOT NULL REFERENCES invoice_header(invoice_id),
    plan_id UUID REFERENCES package_payment_plans(plan_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),

    -- Amounts
    credit_note_date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_amount NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),

    -- Reason
    reason_code VARCHAR(20),  -- 'plan_discontinued', 'service_not_provided', 'overcharge', 'goodwill', etc.
    reason_description TEXT,

    -- GL Posting
    gl_posted BOOLEAN DEFAULT FALSE,
    gl_transaction_id UUID REFERENCES gl_transaction(transaction_id),
    posted_at TIMESTAMP WITH TIME ZONE,
    posted_by VARCHAR(15),

    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- draft, approved, posted, cancelled
    approved_by VARCHAR(15) REFERENCES users(user_id),
    approved_at TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(15),

    CONSTRAINT valid_credit_note_status CHECK (status IN ('draft', 'approved', 'posted', 'cancelled')),
    CONSTRAINT unique_credit_note_number UNIQUE (hospital_id, credit_note_number)
);

-- Indexes for performance
CREATE INDEX idx_credit_note_invoice ON patient_credit_notes(original_invoice_id);
CREATE INDEX idx_credit_note_plan ON patient_credit_notes(plan_id) WHERE plan_id IS NOT NULL;
CREATE INDEX idx_credit_note_patient ON patient_credit_notes(patient_id);
CREATE INDEX idx_credit_note_number ON patient_credit_notes(hospital_id, credit_note_number);
CREATE INDEX idx_credit_note_date ON patient_credit_notes(hospital_id, credit_note_date);
CREATE INDEX idx_credit_note_status ON patient_credit_notes(status) WHERE status != 'cancelled';

-- Comments
COMMENT ON TABLE patient_credit_notes IS 'Credit notes issued against patient invoices for refunds, adjustments, and plan discontinuations';
COMMENT ON COLUMN patient_credit_notes.reason_code IS 'plan_discontinued, service_not_provided, overcharge, goodwill, billing_error';
COMMENT ON COLUMN patient_credit_notes.status IS 'draft (created), approved (awaiting posting), posted (GL posted), cancelled';

-- Add credit_note_id reference to package_payment_plans
ALTER TABLE package_payment_plans
ADD COLUMN IF NOT EXISTS credit_note_id UUID REFERENCES patient_credit_notes(credit_note_id);

-- Create index
CREATE INDEX IF NOT EXISTS idx_package_plan_credit_note ON package_payment_plans(credit_note_id) WHERE credit_note_id IS NOT NULL;

-- Verify table creation
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'patient_credit_notes'
ORDER BY ordinal_position;
