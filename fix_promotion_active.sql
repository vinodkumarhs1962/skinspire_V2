-- Fix: Enable the promotion by setting is_active to TRUE
UPDATE promotion_campaigns
SET
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP
WHERE
    campaign_name = 'Test Promotion 2025'
    AND hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca';

-- Verify the update
SELECT
    campaign_name,
    is_active,
    start_date,
    end_date,
    applies_to,
    discount_type,
    discount_value
FROM promotion_campaigns
WHERE campaign_name = 'Test Promotion 2025';
