-- Add Approval Workflow to Package BOM Items
-- Date: 2025-11-19
-- Description: Add status, approval fields, and rejection reason to package_bom_items

-- Add status column (workflow status)
ALTER TABLE package_bom_items
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft' NOT NULL;

-- Add approval tracking fields (from ApprovalMixin)
ALTER TABLE package_bom_items
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(50);

ALTER TABLE package_bom_items
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;

-- Add rejection reason
ALTER TABLE package_bom_items
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- Add comments for documentation
COMMENT ON COLUMN package_bom_items.status IS 'Workflow status: draft, pending_approval, approved, rejected';
COMMENT ON COLUMN package_bom_items.approved_by IS 'User ID who approved the BOM item';
COMMENT ON COLUMN package_bom_items.approved_at IS 'Timestamp when BOM item was approved';
COMMENT ON COLUMN package_bom_items.rejection_reason IS 'Reason for rejection if status is rejected';

-- Create index on status for faster filtering
CREATE INDEX IF NOT EXISTS idx_package_bom_items_status ON package_bom_items(status) WHERE deleted_at IS NULL;

-- Update existing records to have 'approved' status (assuming they were already in use)
UPDATE package_bom_items
SET status = 'approved'
WHERE status = 'draft' AND deleted_at IS NULL;

COMMIT;
