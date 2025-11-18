-- Migration: Add supplier advance adjustment table and advance_amount field
-- Date: 2025-11-02
-- Description: Implement subledger for supplier advance allocations

-- Step 1: Add advance_amount column to supplier_payment table
ALTER TABLE supplier_payment
ADD COLUMN IF NOT EXISTS advance_amount NUMERIC(12, 2) DEFAULT 0;

-- Step 2: Create supplier_advance_adjustments table
CREATE TABLE IF NOT EXISTS supplier_advance_adjustments (
    adjustment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Source advance payment (the unallocated payment being used)
    source_payment_id UUID NOT NULL REFERENCES supplier_payment(payment_id),

    -- Target references (what the advance is being applied to)
    target_payment_id UUID REFERENCES supplier_payment(payment_id),
    invoice_id UUID REFERENCES supplier_invoice(invoice_id),
    supplier_id UUID NOT NULL REFERENCES suppliers(supplier_id),

    -- Adjustment details
    amount NUMERIC(12, 2) NOT NULL,
    adjustment_date TIMESTAMP WITH TIME ZONE NOT NULL,
    adjustment_type VARCHAR(20) DEFAULT 'allocation',  -- allocation, reversal, refund
    notes TEXT,

    -- Timestamp fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),

    -- Constraints
    CONSTRAINT check_adjustment_amount CHECK (amount > 0),
    CONSTRAINT check_adjustment_type CHECK (adjustment_type IN ('allocation', 'reversal', 'refund'))
);

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_source
    ON supplier_advance_adjustments(source_payment_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_target
    ON supplier_advance_adjustments(target_payment_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_invoice
    ON supplier_advance_adjustments(invoice_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_supplier
    ON supplier_advance_adjustments(supplier_id);

CREATE INDEX IF NOT EXISTS idx_supplier_advance_adj_hospital
    ON supplier_advance_adjustments(hospital_id);

-- Step 4: Add comments
COMMENT ON TABLE supplier_advance_adjustments IS 'Subledger for tracking supplier advance payment allocations';
COMMENT ON COLUMN supplier_advance_adjustments.source_payment_id IS 'The unallocated/advance payment being used';
COMMENT ON COLUMN supplier_advance_adjustments.target_payment_id IS 'The new payment record that includes this advance allocation';
COMMENT ON COLUMN supplier_advance_adjustments.adjustment_type IS 'Type: allocation (using advance), reversal (canceling allocation), refund (returning advance)';

-- Step 5: Update existing data (if needed)
-- Set advance_amount to 0 for existing records
UPDATE supplier_payment
SET advance_amount = 0
WHERE advance_amount IS NULL;
