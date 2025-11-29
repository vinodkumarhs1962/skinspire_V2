-- Migration: Add approval workflow columns to promotion_campaigns
-- Date: 2025-11-28
-- Description: Add status, approval_notes, approved_by, approved_at columns for approval workflow

-- Add status column for approval workflow
ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'draft';

-- Add approval_notes column for rejection reason or approval comments
ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS approval_notes TEXT;

-- Add approved_by column (from ApprovalMixin)
ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(50);

-- Add approved_at column (from ApprovalMixin)
ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;

-- Create index for filtering by status
CREATE INDEX IF NOT EXISTS idx_promotion_campaigns_status
ON promotion_campaigns(status);

-- Update existing records to have status = 'approved' (backward compatibility for existing campaigns)
UPDATE promotion_campaigns
SET status = 'approved'
WHERE status IS NULL OR status = '';

-- Set status to NOT NULL after setting defaults
ALTER TABLE promotion_campaigns
ALTER COLUMN status SET NOT NULL;

-- Add check constraint for valid status values
ALTER TABLE promotion_campaigns
ADD CONSTRAINT chk_campaign_status
CHECK (status IN ('draft', 'pending_approval', 'approved', 'rejected'));

-- Add comments
COMMENT ON COLUMN promotion_campaigns.status IS 'Approval workflow status: draft, pending_approval, approved, rejected';
COMMENT ON COLUMN promotion_campaigns.approval_notes IS 'Rejection reason or approval comments';
COMMENT ON COLUMN promotion_campaigns.approved_by IS 'User ID who approved the campaign';
COMMENT ON COLUMN promotion_campaigns.approved_at IS 'Timestamp when campaign was approved';
