-- ============================================================
-- Migration: Add Personalized Promotion Flag
-- Date: 2025-11-25
-- Purpose: Support personalized campaigns that require manual code entry
-- ============================================================

-- Add is_personalized flag to promotion_campaigns table
ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS is_personalized BOOLEAN DEFAULT FALSE;

-- Add comment explaining the flag
COMMENT ON COLUMN promotion_campaigns.is_personalized IS
'TRUE = Personalized promotion sent via Email/WhatsApp to specific patients. Requires manual code entry at billing.
 FALSE = Public promotion auto-applied to all eligible patients.';

-- Create index for faster filtering in auto-apply logic
CREATE INDEX IF NOT EXISTS idx_promotion_campaigns_personalized
ON promotion_campaigns(is_personalized, is_active)
WHERE is_deleted = FALSE;

-- ============================================================
-- Update existing promotions (all are public by default)
-- ============================================================
UPDATE promotion_campaigns
SET is_personalized = FALSE
WHERE is_personalized IS NULL;

-- ============================================================
-- Example: Create a personalized promotion (for testing)
-- ============================================================
-- INSERT INTO promotion_campaigns (
--     campaign_id,
--     hospital_id,
--     campaign_name,
--     campaign_code,
--     description,
--     start_date,
--     end_date,
--     is_active,
--     promotion_type,
--     discount_type,
--     discount_value,
--     applies_to,
--     is_personalized,  -- Set to TRUE for personalized
--     auto_apply,
--     created_at
-- ) VALUES (
--     gen_random_uuid(),
--     'your-hospital-uuid',
--     'VIP Customer Special',
--     'VIP2025',
--     'Exclusive 30% discount for VIP customers',
--     '2025-11-25',
--     '2025-12-31',
--     true,
--     'simple_discount',
--     'percentage',
--     30.00,
--     'all',
--     TRUE,  -- Personalized - requires manual entry
--     false, -- Not auto-apply
--     CURRENT_TIMESTAMP
-- );

-- ============================================================
-- Verification
-- ============================================================
-- SELECT campaign_name, campaign_code, is_personalized, is_active
-- FROM promotion_campaigns
-- WHERE is_deleted = FALSE;
