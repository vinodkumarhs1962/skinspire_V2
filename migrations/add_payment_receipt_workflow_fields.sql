-- ============================================================================
-- Patient Payment Receipts - Database Schema Extensions
-- Version: 1.0
-- Date: 2025-01-10
-- Description: Add workflow and approval fields to existing payment tables
-- ============================================================================

-- IMPORTANT: This script EXTENDS existing tables, does NOT create new ones
-- Existing tables being modified:
--   - payment_details (PaymentDetail model)
--   - patient_advance_payments (PatientAdvancePayment model)
--   - advance_adjustments (AdvanceAdjustment model)

BEGIN;

-- ============================================================================
-- PART 1: EXTEND payment_details TABLE (Workflow & Approval)
-- ============================================================================

-- Add workflow status fields
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(20) DEFAULT 'approved'
    CHECK (workflow_status IN ('draft', 'pending_approval', 'approved', 'rejected', 'reversed'));

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN DEFAULT FALSE;

-- Add submission tracking
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS submitted_by VARCHAR(15) REFERENCES users(user_id);

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP WITH TIME ZONE;

-- Add approval tracking
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(15) REFERENCES users(user_id);

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;

-- Add rejection tracking
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS rejected_by VARCHAR(15) REFERENCES users(user_id);

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- Add GL posting tracking
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS gl_posted BOOLEAN DEFAULT FALSE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS posting_date TIMESTAMP WITH TIME ZONE;

-- Add soft delete support
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(15);

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS deletion_reason TEXT;

-- Add reversal tracking
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS is_reversed BOOLEAN DEFAULT FALSE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS reversed_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS reversed_by VARCHAR(15);

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS reversal_reason TEXT;

ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS reversal_gl_entry_id UUID REFERENCES gl_transaction(transaction_id);

-- ============================================================================
-- PART 2: EXTEND patient_advance_payments TABLE
-- ============================================================================

-- Add workflow status fields
ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(20) DEFAULT 'approved'
    CHECK (workflow_status IN ('draft', 'pending_approval', 'approved', 'rejected'));

ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS requires_approval BOOLEAN DEFAULT FALSE;

-- Add approval tracking
ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(15) REFERENCES users(user_id);

ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;

-- Add rejection tracking
ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS rejected_by VARCHAR(15);

ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- Add GL posting tracking
ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS gl_posted BOOLEAN DEFAULT FALSE;

ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS posting_date TIMESTAMP WITH TIME ZONE;

-- Add branch support (for multi-branch hospitals)
ALTER TABLE patient_advance_payments
ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(branch_id);

-- ============================================================================
-- PART 3: EXTEND advance_adjustments TABLE (GL Tracking & Reversal)
-- ============================================================================

-- Add GL tracking
ALTER TABLE advance_adjustments
ADD COLUMN IF NOT EXISTS gl_entry_id UUID REFERENCES gl_transaction(transaction_id);

-- Add reversal tracking
ALTER TABLE advance_adjustments
ADD COLUMN IF NOT EXISTS is_reversed BOOLEAN DEFAULT FALSE;

ALTER TABLE advance_adjustments
ADD COLUMN IF NOT EXISTS reversed_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE advance_adjustments
ADD COLUMN IF NOT EXISTS reversed_by VARCHAR(15);

-- ============================================================================
-- PART 4: CREATE INDEXES FOR PERFORMANCE
-- ============================================================================

-- payment_details indexes
CREATE INDEX IF NOT EXISTS idx_payment_details_workflow_status
    ON payment_details(workflow_status)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_payment_details_is_deleted
    ON payment_details(is_deleted)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_payment_details_requires_approval
    ON payment_details(requires_approval)
    WHERE requires_approval = TRUE AND workflow_status = 'pending_approval';

CREATE INDEX IF NOT EXISTS idx_payment_details_gl_posted
    ON payment_details(gl_posted)
    WHERE gl_posted = FALSE AND workflow_status = 'approved';

CREATE INDEX IF NOT EXISTS idx_payment_details_is_reversed
    ON payment_details(is_reversed)
    WHERE is_reversed = TRUE;

-- patient_advance_payments indexes
CREATE INDEX IF NOT EXISTS idx_patient_advance_payments_workflow
    ON patient_advance_payments(workflow_status);

CREATE INDEX IF NOT EXISTS idx_patient_advance_payments_branch
    ON patient_advance_payments(branch_id);

-- advance_adjustments indexes
CREATE INDEX IF NOT EXISTS idx_advance_adjustments_gl_entry
    ON advance_adjustments(gl_entry_id);

CREATE INDEX IF NOT EXISTS idx_advance_adjustments_is_reversed
    ON advance_adjustments(is_reversed)
    WHERE is_reversed = TRUE;

-- ============================================================================
-- PART 5: UPDATE EXISTING DATA (Set Defaults)
-- ============================================================================

-- Set existing payments to 'approved' status (they were already processed)
UPDATE payment_details
SET workflow_status = 'approved',
    gl_posted = TRUE
WHERE workflow_status IS NULL;

-- Set existing advance payments to 'approved' status
UPDATE patient_advance_payments
SET workflow_status = 'approved',
    gl_posted = TRUE
WHERE workflow_status IS NULL;

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (Run after migration)
-- ============================================================================

-- Verify payment_details columns added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'payment_details'
  AND column_name IN ('workflow_status', 'requires_approval', 'gl_posted',
                      'is_deleted', 'is_reversed', 'approved_by', 'rejected_by');

-- Verify patient_advance_payments columns added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'patient_advance_payments'
  AND column_name IN ('workflow_status', 'requires_approval', 'gl_posted',
                      'branch_id', 'approved_by');

-- Verify advance_adjustments columns added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'advance_adjustments'
  AND column_name IN ('gl_entry_id', 'is_reversed', 'reversed_at', 'reversed_by');

-- Count payment records by workflow status
SELECT workflow_status, COUNT(*) as count
FROM payment_details
GROUP BY workflow_status
ORDER BY count DESC;

-- Count advance payments by workflow status
SELECT workflow_status, COUNT(*) as count
FROM patient_advance_payments
GROUP BY workflow_status
ORDER BY count DESC;
