-- Migration: Add soft delete columns to promotion_campaign_groups
-- Date: 2025-11-28
-- Description: Add is_deleted, deleted_at, deleted_by columns for soft delete support

-- Add soft delete columns
ALTER TABLE promotion_campaign_groups
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

ALTER TABLE promotion_campaign_groups
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE promotion_campaign_groups
ADD COLUMN IF NOT EXISTS deleted_by VARCHAR(15);

-- Create index for filtering non-deleted records
CREATE INDEX IF NOT EXISTS idx_campaign_groups_is_deleted
ON promotion_campaign_groups(is_deleted)
WHERE is_deleted = FALSE;

-- Update existing records to have is_deleted = false
UPDATE promotion_campaign_groups
SET is_deleted = FALSE
WHERE is_deleted IS NULL;

-- Make is_deleted NOT NULL after setting defaults
ALTER TABLE promotion_campaign_groups
ALTER COLUMN is_deleted SET NOT NULL;

-- Add comment
COMMENT ON COLUMN promotion_campaign_groups.is_deleted IS 'Soft delete flag - true means record is deleted';
COMMENT ON COLUMN promotion_campaign_groups.deleted_at IS 'Timestamp when record was soft deleted';
COMMENT ON COLUMN promotion_campaign_groups.deleted_by IS 'User ID who deleted the record';
