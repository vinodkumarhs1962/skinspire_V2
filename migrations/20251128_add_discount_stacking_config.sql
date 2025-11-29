-- Migration: Add discount_stacking_config to hospitals table
-- Date: 2025-11-28
-- Description: Adds comprehensive discount stacking configuration for flexible discount rules

-- Add the discount_stacking_config column with default configuration
ALTER TABLE hospitals
ADD COLUMN IF NOT EXISTS discount_stacking_config JSONB DEFAULT '{
    "campaign": {
        "mode": "exclusive",
        "buy_x_get_y_exclusive": true
    },
    "loyalty": {
        "mode": "incremental"
    },
    "bulk": {
        "mode": "incremental",
        "exclude_with_campaign": true
    },
    "vip": {
        "mode": "absolute"
    },
    "max_total_discount": null
}'::jsonb;

-- Add comment explaining the configuration
COMMENT ON COLUMN hospitals.discount_stacking_config IS 'Configures how different discount types interact:
- campaign.mode: "exclusive" (only campaign applies) or "incremental" (stacks with others)
- campaign.buy_x_get_y_exclusive: If true, qualifying items have no other discounts
- loyalty.mode: "incremental" (always adds) or "absolute" (competes with others)
- bulk.mode: "incremental" (adds) or "absolute" (competes)
- bulk.exclude_with_campaign: If true, no bulk discount when campaign applies
- vip.mode: "incremental" (adds) or "absolute" (competes)
- max_total_discount: Optional cap on total discount percentage (e.g., 50)';

-- Migrate existing loyalty_discount_mode to new config where applicable
UPDATE hospitals
SET discount_stacking_config = jsonb_set(
    discount_stacking_config,
    '{loyalty,mode}',
    CASE
        WHEN loyalty_discount_mode = 'additional' THEN '"incremental"'::jsonb
        ELSE '"absolute"'::jsonb
    END
)
WHERE discount_stacking_config IS NOT NULL;
