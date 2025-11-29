-- Test Data: Promotions and Discounts
-- Date: 2025-11-27
-- Purpose: Create sample data to demonstrate various discount types and rules
--
-- IMPORTANT: This is test data. Modify the hospital_id to match your installation.
-- Run this AFTER the main migrations have been applied.

-- =============================================================================
-- Get the default hospital ID (modify if needed)
-- =============================================================================
-- In a real scenario, replace this with your actual hospital_id
-- For now, we'll use a subquery to get the first hospital

-- =============================================================================
-- 1. SAMPLE PROMOTION CAMPAIGNS
-- =============================================================================

-- Insert test campaigns if they don't exist
INSERT INTO promotion_campaigns (
    campaign_id, hospital_id, campaign_code, campaign_name, description,
    promotion_type, discount_type, discount_value,
    start_date, end_date, is_active, is_personalized, target_special_group,
    auto_apply, applies_to, min_purchase_amount, max_discount_amount,
    max_uses_per_patient, max_total_uses, current_uses,
    terms_and_conditions
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'WINTER25',
    'Winter Season Sale',
    'Special discounts on all skin treatments during winter season',
    'simple_discount',
    'percentage',
    15.00,
    '2025-11-15'::date,
    '2025-12-31'::date,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    'services',
    500.00,
    2000.00,
    3,
    500,
    12,
    'Valid on services above Rs. 500. Max discount Rs. 2000.'
WHERE NOT EXISTS (
    SELECT 1 FROM promotion_campaigns WHERE campaign_code = 'WINTER25'
);

INSERT INTO promotion_campaigns (
    campaign_id, hospital_id, campaign_code, campaign_name, description,
    promotion_type, discount_type, discount_value,
    start_date, end_date, is_active, is_personalized, target_special_group,
    auto_apply, applies_to, min_purchase_amount, max_discount_amount,
    max_uses_per_patient, max_total_uses, current_uses,
    terms_and_conditions
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'DIWALI2025',
    'Diwali Festive Offer',
    'Exclusive festive discount for all our valued customers',
    'simple_discount',
    'percentage',
    20.00,
    '2025-10-25'::date,
    '2025-11-05'::date,
    FALSE,  -- Past campaign (inactive)
    FALSE,
    FALSE,
    TRUE,
    'all',
    1000.00,
    5000.00,
    2,
    1000,
    847,
    'Festive offer valid on purchases above Rs. 1000.'
WHERE NOT EXISTS (
    SELECT 1 FROM promotion_campaigns WHERE campaign_code = 'DIWALI2025'
);

INSERT INTO promotion_campaigns (
    campaign_id, hospital_id, campaign_code, campaign_name, description,
    promotion_type, discount_type, discount_value,
    start_date, end_date, is_active, is_personalized, target_special_group,
    auto_apply, applies_to, min_purchase_amount, max_discount_amount,
    max_uses_per_patient, max_total_uses, current_uses,
    terms_and_conditions
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'VIP25OFF',
    'VIP Exclusive 25%',
    'Special discount only for our VIP (Special Group) customers',
    'simple_discount',
    'percentage',
    25.00,
    '2025-11-01'::date,
    '2025-12-31'::date,
    TRUE,
    TRUE,   -- Personalized - requires code entry
    TRUE,   -- Only for special group patients
    FALSE,  -- Manual application
    'all',
    0,
    NULL,  -- No max discount
    5,
    100,
    23,
    'Exclusive for VIP customers. Must enter code at checkout.'
WHERE NOT EXISTS (
    SELECT 1 FROM promotion_campaigns WHERE campaign_code = 'VIP25OFF'
);

INSERT INTO promotion_campaigns (
    campaign_id, hospital_id, campaign_code, campaign_name, description,
    promotion_type, discount_type, discount_value,
    start_date, end_date, is_active, is_personalized, target_special_group,
    auto_apply, applies_to, min_purchase_amount, max_discount_amount,
    max_uses_per_patient, max_total_uses, current_uses,
    terms_and_conditions
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'FLASHSALE',
    '3-Day Flash Sale',
    'Limited time flash sale on medicines',
    'simple_discount',
    'percentage',
    10.00,
    CURRENT_DATE,
    CURRENT_DATE + 3,  -- 3 day promotion
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    'medicines',
    200.00,
    1000.00,
    2,
    200,
    5,
    'Valid for 3 days only on medicine purchases above Rs. 200.'
WHERE NOT EXISTS (
    SELECT 1 FROM promotion_campaigns WHERE campaign_code = 'FLASHSALE'
);

INSERT INTO promotion_campaigns (
    campaign_id, hospital_id, campaign_code, campaign_name, description,
    promotion_type, discount_type, discount_value,
    start_date, end_date, is_active, is_personalized, target_special_group,
    auto_apply, applies_to, min_purchase_amount, max_discount_amount,
    max_uses_per_patient, max_total_uses, current_uses,
    terms_and_conditions
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'NEWYEAR26',
    'New Year 2026 Celebration',
    'Ring in the new year with special discounts',
    'simple_discount',
    'percentage',
    18.00,
    '2025-12-28'::date,
    '2026-01-05'::date,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    'all',
    0,
    3000.00,
    NULL,  -- Unlimited per patient
    NULL,  -- Unlimited total
    0,
    'New Year special - available to all customers.'
WHERE NOT EXISTS (
    SELECT 1 FROM promotion_campaigns WHERE campaign_code = 'NEWYEAR26'
);

INSERT INTO promotion_campaigns (
    campaign_id, hospital_id, campaign_code, campaign_name, description,
    promotion_type, discount_type, discount_value,
    start_date, end_date, is_active, is_personalized, target_special_group,
    auto_apply, applies_to, min_purchase_amount, max_discount_amount,
    max_uses_per_patient, max_total_uses, current_uses,
    terms_and_conditions
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'FLAT500',
    'Flat Rs. 500 Off',
    'Flat Rs. 500 discount on purchases above Rs. 3000',
    'simple_discount',
    'fixed_amount',
    500.00,
    '2025-11-20'::date,
    '2025-12-15'::date,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    'services',
    3000.00,
    500.00,
    1,
    50,
    8,
    'Flat Rs. 500 off on service bills above Rs. 3000. One time use.'
WHERE NOT EXISTS (
    SELECT 1 FROM promotion_campaigns WHERE campaign_code = 'FLAT500'
);

-- =============================================================================
-- 2. ENABLE BULK DISCOUNT FOR HOSPITAL (if not already configured)
-- =============================================================================

UPDATE hospitals
SET
    bulk_discount_enabled = TRUE,
    bulk_discount_min_service_count = 5,
    bulk_discount_effective_from = '2025-01-01'::date
WHERE bulk_discount_enabled IS NULL OR bulk_discount_enabled = FALSE;

-- =============================================================================
-- 3. SET BULK DISCOUNT ELIGIBLE ON SOME SERVICES (if services exist)
-- =============================================================================

-- Mark some services as bulk eligible with discount percentages
UPDATE services
SET
    bulk_discount_eligible = TRUE,
    bulk_discount_percent =
        CASE
            WHEN service_name ILIKE '%facial%' THEN 12.5
            WHEN service_name ILIKE '%laser%' THEN 10.0
            WHEN service_name ILIKE '%treatment%' THEN 8.0
            WHEN service_name ILIKE '%consultation%' THEN 5.0
            ELSE 7.5
        END
WHERE is_deleted = FALSE
AND service_name ILIKE ANY(ARRAY['%facial%', '%laser%', '%treatment%', '%consultation%', '%skin%'])
LIMIT 10;

-- =============================================================================
-- 4. SET BULK DISCOUNT ELIGIBLE ON SOME MEDICINES (if medicines exist)
-- =============================================================================

UPDATE medicines
SET
    bulk_discount_eligible = TRUE,
    bulk_discount_percent =
        CASE
            WHEN medicine_name ILIKE '%cream%' THEN 8.0
            WHEN medicine_name ILIKE '%gel%' THEN 7.0
            WHEN medicine_name ILIKE '%serum%' THEN 10.0
            WHEN medicine_name ILIKE '%lotion%' THEN 6.0
            ELSE 5.0
        END
WHERE is_deleted = FALSE
AND medicine_name ILIKE ANY(ARRAY['%cream%', '%gel%', '%serum%', '%lotion%', '%ointment%'])
LIMIT 10;

-- =============================================================================
-- 5. CREATE SAMPLE LOYALTY CARD TYPES (if not already exist)
-- =============================================================================

INSERT INTO loyalty_card_types (
    card_type_id, hospital_id, card_type_name, card_type_code, description,
    discount_percent, min_lifetime_spend, min_visits, card_color,
    is_active, is_deleted
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'Silver Card',
    'SILVER',
    'Entry level loyalty card with 5% discount on all purchases',
    5.00,
    10000.00,
    5,
    '#C0C0C0',
    TRUE,
    FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM loyalty_card_types WHERE card_type_code = 'SILVER'
);

INSERT INTO loyalty_card_types (
    card_type_id, hospital_id, card_type_name, card_type_code, description,
    discount_percent, min_lifetime_spend, min_visits, card_color,
    is_active, is_deleted
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'Gold Card',
    'GOLD',
    'Premium loyalty card with 10% discount on all purchases',
    10.00,
    50000.00,
    15,
    '#FFD700',
    TRUE,
    FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM loyalty_card_types WHERE card_type_code = 'GOLD'
);

INSERT INTO loyalty_card_types (
    card_type_id, hospital_id, card_type_name, card_type_code, description,
    discount_percent, min_lifetime_spend, min_visits, card_color,
    is_active, is_deleted
)
SELECT
    gen_random_uuid(),
    (SELECT hospital_id FROM hospitals LIMIT 1),
    'Platinum Card',
    'PLATINUM',
    'Elite loyalty card with 15% discount on all purchases plus priority booking',
    15.00,
    100000.00,
    30,
    '#E5E4E2',
    TRUE,
    FALSE
WHERE NOT EXISTS (
    SELECT 1 FROM loyalty_card_types WHERE card_type_code = 'PLATINUM'
);

-- =============================================================================
-- 6. MARK SOME PATIENTS AS SPECIAL GROUP (VIP)
-- =============================================================================

-- Mark top 3 patients (by created_at) as special group for testing
UPDATE patients
SET is_special_group = TRUE
WHERE patient_id IN (
    SELECT patient_id
    FROM patients
    WHERE is_deleted = FALSE AND is_active = TRUE
    ORDER BY created_at
    LIMIT 3
)
AND is_special_group IS NOT TRUE;

-- =============================================================================
-- 7. SET STANDARD DISCOUNT ON SOME SERVICES (fallback discount)
-- =============================================================================

-- Set standard discount (priority 4 - fallback) on some services
UPDATE services
SET standard_discount_percent = 3.0
WHERE is_deleted = FALSE
AND standard_discount_percent IS NULL OR standard_discount_percent = 0
LIMIT 5;

-- =============================================================================
-- SUMMARY OF TEST DATA CREATED
-- =============================================================================
--
-- Campaigns Created:
-- 1. WINTER25 - 15% off services (Nov 15 - Dec 31, 2025)
-- 2. DIWALI2025 - 20% off all (Oct 25 - Nov 5, 2025) - PAST/INACTIVE
-- 3. VIP25OFF - 25% off for VIP only (Nov 1 - Dec 31, 2025) - PERSONALIZED
-- 4. FLASHSALE - 10% off medicines (3 day sale) - ACTIVE
-- 5. NEWYEAR26 - 18% off all (Dec 28, 2025 - Jan 5, 2026) - UPCOMING
-- 6. FLAT500 - Rs. 500 flat off on services > Rs. 3000
--
-- Bulk Discount:
-- - Hospital configured with min 5 items
-- - Some services marked as bulk eligible (5-12.5%)
-- - Some medicines marked as bulk eligible (5-10%)
--
-- Loyalty Cards:
-- - Silver (5%), Gold (10%), Platinum (15%)
--
-- Special Group:
-- - Top 3 patients marked as VIP
--
-- Standard Discount:
-- - 3% fallback discount on some services
-- =============================================================================
