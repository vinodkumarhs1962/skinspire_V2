-- Migration: Extend promotion_campaigns for Complex Promotions
-- Date: 21-Nov-2025
-- Description: Add promotion_type and promotion_rules for Buy X Get Y, Tiered, Bundle discounts
--              Add campaign tracking to invoices for effectiveness measurement
--              Remove CampaignHookConfig dependencies

-- ============================================================================
-- 1. EXTEND PROMOTION_CAMPAIGNS TABLE
-- ============================================================================

-- Add promotion_type column
ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS promotion_type VARCHAR(20) DEFAULT 'simple_discount'
CHECK (promotion_type IN ('simple_discount', 'buy_x_get_y', 'tiered_discount', 'bundle'));

COMMENT ON COLUMN promotion_campaigns.promotion_type IS
'Type of promotion: simple_discount (current), buy_x_get_y (Buy X Get Y Free), tiered_discount (spend tiers), bundle (package deals)';

-- Add promotion_rules JSONB column for complex promotion logic
ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS promotion_rules JSONB;

COMMENT ON COLUMN promotion_campaigns.promotion_rules IS
'Complex promotion rules in JSON format. Structure varies by promotion_type.
Example for buy_x_get_y:
{
  "trigger": {
    "type": "item_purchase",
    "conditions": {
      "item_ids": ["service-id-1"],
      "item_type": "Service",
      "min_amount": 5000,
      "min_quantity": 1
    }
  },
  "reward": {
    "type": "free_item",
    "items": [
      {"item_id": "consultation-id", "item_type": "Service", "quantity": 1, "discount_percent": 100}
    ],
    "auto_add": true,
    "max_free_items": 1
  }
}';

-- ============================================================================
-- 2. ADD CAMPAIGN TRACKING TO INVOICES
-- ============================================================================

-- Add campaigns_applied column to invoice_header for effectiveness tracking
ALTER TABLE invoice_header
ADD COLUMN IF NOT EXISTS campaigns_applied JSONB;

COMMENT ON COLUMN invoice_header.campaigns_applied IS
'Array of campaigns applied to this invoice for effectiveness measurement.
Format: [
  {
    "campaign_id": "uuid",
    "campaign_name": "Holiday Special",
    "campaign_code": "HOLIDAY2025",
    "promotion_type": "buy_x_get_y",
    "total_discount": 500.00,
    "items_affected": ["item-id-1", "item-id-2"]
  }
]';

-- ============================================================================
-- 3. RENAME campaign_hook_id TO promotion_id (Cleanup)
-- ============================================================================

-- Rename in discount_application_log table
ALTER TABLE discount_application_log
RENAME COLUMN campaign_hook_id TO promotion_id;

COMMENT ON COLUMN discount_application_log.promotion_id IS
'Reference to promotion_campaigns.campaign_id (formerly campaign_hook_id)';

-- ============================================================================
-- 4. ADD INDEXES FOR PERFORMANCE
-- ============================================================================

-- Index on promotion_type for faster filtering
CREATE INDEX IF NOT EXISTS idx_promotion_campaigns_type
ON promotion_campaigns(promotion_type, is_active)
WHERE is_deleted = FALSE;

-- Index on campaigns_applied for reporting queries
CREATE INDEX IF NOT EXISTS idx_invoice_header_campaigns
ON invoice_header USING GIN (campaigns_applied)
WHERE campaigns_applied IS NOT NULL;

-- ============================================================================
-- 5. UPDATE EXISTING PROMOTIONS (Set Defaults)
-- ============================================================================

-- Set promotion_type to 'simple_discount' for all existing promotions
UPDATE promotion_campaigns
SET promotion_type = 'simple_discount'
WHERE promotion_type IS NULL;

-- ============================================================================
-- 6. VERIFICATION QUERIES
-- ============================================================================

-- Check promotion_campaigns has new columns
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'promotion_campaigns'
  AND column_name IN ('promotion_type', 'promotion_rules')
ORDER BY column_name;

-- Check invoice_header has campaigns_applied
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'invoice_header'
  AND column_name = 'campaigns_applied';

-- Check discount_application_log has promotion_id (renamed)
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'discount_application_log'
  AND column_name = 'promotion_id';

-- Check indexes created
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('promotion_campaigns', 'patient_invoices')
  AND indexname LIKE '%promotion%' OR indexname LIKE '%campaign%'
ORDER BY tablename, indexname;

-- ============================================================================
-- 7. SAMPLE DATA - BUY X GET Y PROMOTION
-- ============================================================================

-- Example 1: Buy High-Value Service (≥ Rs.5000) → Free Consultation
/*
INSERT INTO promotion_campaigns (
    hospital_id,
    campaign_name,
    campaign_code,
    description,
    start_date,
    end_date,
    is_active,
    promotion_type,
    discount_type,
    discount_value,
    applies_to,
    promotion_rules,
    auto_apply
) VALUES (
    'your-hospital-id',
    'Premium Service - Free Consultation',
    'PREMIUM_CONSULT',
    'Purchase any service worth Rs.5000 or more and get consultation absolutely free',
    '2025-11-01',
    '2025-12-31',
    TRUE,
    'buy_x_get_y',
    'percentage',  -- Not used for buy_x_get_y, but required
    0,
    'services',
    '{
        "trigger": {
            "type": "item_purchase",
            "conditions": {
                "item_type": "Service",
                "min_amount": 5000
            }
        },
        "reward": {
            "type": "free_item",
            "items": [
                {
                    "item_id": "your-consultation-service-id",
                    "item_type": "Service",
                    "quantity": 1,
                    "discount_percent": 100
                }
            ],
            "auto_add": true,
            "max_free_items": 1
        }
    }'::jsonb,
    TRUE
);
*/

-- Example 2: Buy Medi Facial → Free Sunscreen Product
/*
INSERT INTO promotion_campaigns (
    hospital_id,
    campaign_name,
    campaign_code,
    description,
    start_date,
    end_date,
    is_active,
    promotion_type,
    discount_type,
    discount_value,
    applies_to,
    promotion_rules,
    auto_apply
) VALUES (
    'your-hospital-id',
    'Medi Facial - Free Sunscreen',
    'FACIAL_SUNSCREEN',
    'Book Medi Facial and get Sunscreen 50ml free',
    '2025-11-01',
    '2025-12-31',
    TRUE,
    'buy_x_get_y',
    'percentage',
    0,
    'all',
    '{
        "trigger": {
            "type": "item_purchase",
            "conditions": {
                "item_ids": ["your-medi-facial-service-id"],
                "item_type": "Service",
                "min_quantity": 1
            }
        },
        "reward": {
            "type": "free_item",
            "items": [
                {
                    "item_id": "your-sunscreen-medicine-id",
                    "item_type": "Medicine",
                    "quantity": 1,
                    "discount_percent": 100
                }
            ],
            "auto_add": true,
            "max_free_items": 1
        }
    }'::jsonb,
    TRUE
);
*/

-- ============================================================================
-- 8. CAMPAIGN EFFECTIVENESS QUERIES (For Reporting)
-- ============================================================================

-- Query: Campaign effectiveness summary
/*
SELECT
    c.campaign_name,
    c.campaign_code,
    c.promotion_type,
    COUNT(DISTINCT i.invoice_id) as invoices_count,
    SUM((campaign_data->>'total_discount')::numeric) as total_discount_given,
    AVG((campaign_data->>'total_discount')::numeric) as avg_discount_per_invoice,
    c.current_uses as times_used
FROM promotion_campaigns c
LEFT JOIN invoice_header i ON i.campaigns_applied @> jsonb_build_array(
    jsonb_build_object('campaign_id', c.campaign_id::text)
)
CROSS JOIN LATERAL jsonb_array_elements(i.campaigns_applied) as campaign_data
WHERE c.is_active = TRUE
  AND c.is_deleted = FALSE
  AND i.invoice_date BETWEEN '2025-11-01' AND '2025-11-30'
GROUP BY c.campaign_id, c.campaign_name, c.campaign_code, c.promotion_type, c.current_uses
ORDER BY total_discount_given DESC;
*/

-- Query: Top campaigns by usage
/*
SELECT
    campaign_name,
    campaign_code,
    promotion_type,
    current_uses as total_uses,
    max_total_uses,
    CASE
        WHEN max_total_uses IS NOT NULL
        THEN ROUND((current_uses::numeric / max_total_uses * 100), 2)
        ELSE NULL
    END as usage_percentage
FROM promotion_campaigns
WHERE is_active = TRUE
  AND is_deleted = FALSE
ORDER BY current_uses DESC
LIMIT 10;
*/

-- Query: Invoices with campaign details
/*
SELECT
    i.invoice_number,
    i.invoice_date,
    p.first_name || ' ' || p.last_name as patient_name,
    i.total_amount,
    i.discount_amount,
    jsonb_pretty(i.campaigns_applied) as campaigns_detail
FROM invoice_header i
JOIN patients p ON i.patient_id = p.patient_id
WHERE i.campaigns_applied IS NOT NULL
  AND i.invoice_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY i.invoice_date DESC
LIMIT 20;
*/

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Expected result:
-- 1. promotion_campaigns has promotion_type and promotion_rules columns
-- 2. patient_invoices has campaigns_applied column
-- 3. discount_application_log.campaign_hook_id renamed to promotion_id
-- 4. Indexes created for performance
-- 5. Existing promotions set to 'simple_discount'

-- Rollback (if needed):
/*
ALTER TABLE promotion_campaigns DROP COLUMN IF EXISTS promotion_type;
ALTER TABLE promotion_campaigns DROP COLUMN IF EXISTS promotion_rules;
ALTER TABLE invoice_header DROP COLUMN IF EXISTS campaigns_applied;
ALTER TABLE discount_application_log RENAME COLUMN promotion_id TO campaign_hook_id;
DROP INDEX IF EXISTS idx_promotion_campaigns_type;
DROP INDEX IF EXISTS idx_invoice_header_campaigns;
*/
