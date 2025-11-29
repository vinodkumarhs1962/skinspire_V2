-- Migration: Add Special Group and Bulk Discount Eligibility Flags
-- Date: 2025-11-27
-- Purpose:
--   1. Add is_special_group flag to patients for targeted campaigns
--   2. Add target_special_group flag to campaigns to target special patient group
--   3. Add bulk_discount_eligible flag to services and medicines

-- =============================================================================
-- 1. PATIENT SPECIAL GROUP FLAG
-- =============================================================================
-- This flag identifies VIP/Special customers who can receive:
--   - Personalized campaign codes via Email/WhatsApp
--   - Special app features
--   - Exclusive promotions

ALTER TABLE patients
ADD COLUMN IF NOT EXISTS is_special_group BOOLEAN DEFAULT FALSE;

-- Add index for filtering special group patients
CREATE INDEX IF NOT EXISTS idx_patients_special_group
ON patients(hospital_id, is_special_group)
WHERE is_special_group = TRUE AND is_deleted = FALSE;

COMMENT ON COLUMN patients.is_special_group IS
'VIP/Special customer flag - eligible for exclusive campaigns and features';

-- =============================================================================
-- 2. CAMPAIGN TARGET SPECIAL GROUP FLAG
-- =============================================================================
-- When TRUE, campaign only applies to patients where is_special_group = TRUE

ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS target_special_group BOOLEAN DEFAULT FALSE;

-- Add index for filtering campaigns targeting special group
CREATE INDEX IF NOT EXISTS idx_campaigns_special_group
ON promotion_campaigns(hospital_id, target_special_group, is_active)
WHERE is_deleted = FALSE;

COMMENT ON COLUMN promotion_campaigns.target_special_group IS
'When TRUE, campaign only applies to patients marked as is_special_group';

-- =============================================================================
-- 3. BULK DISCOUNT ELIGIBILITY FLAGS
-- =============================================================================
-- Instead of checking bulk_discount_percent > 0, we have an explicit flag
-- This allows setting bulk_discount_percent = 0 temporarily while keeping eligibility

-- Services
ALTER TABLE services
ADD COLUMN IF NOT EXISTS bulk_discount_eligible BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_services_bulk_eligible
ON services(hospital_id, bulk_discount_eligible)
WHERE bulk_discount_eligible = TRUE AND is_deleted = FALSE;

COMMENT ON COLUMN services.bulk_discount_eligible IS
'Checkbox to enable bulk discount for this service';

-- Medicines
ALTER TABLE medicines
ADD COLUMN IF NOT EXISTS bulk_discount_eligible BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_medicines_bulk_eligible
ON medicines(hospital_id, bulk_discount_eligible)
WHERE bulk_discount_eligible = TRUE AND is_deleted = FALSE;

COMMENT ON COLUMN medicines.bulk_discount_eligible IS
'Checkbox to enable bulk discount for this medicine';

-- =============================================================================
-- 4. MIGRATE EXISTING DATA
-- =============================================================================
-- Set bulk_discount_eligible = TRUE for items that already have bulk_discount_percent > 0

UPDATE services
SET bulk_discount_eligible = TRUE
WHERE bulk_discount_percent > 0 AND is_deleted = FALSE;

UPDATE medicines
SET bulk_discount_eligible = TRUE
WHERE bulk_discount_percent > 0 AND is_deleted = FALSE;

-- =============================================================================
-- 5. ANALYTICS VIEW UPDATE
-- =============================================================================
-- Add special group info to promotion effectiveness view

DROP VIEW IF EXISTS v_promotion_effectiveness;

CREATE OR REPLACE VIEW v_promotion_effectiveness AS
SELECT
    pc.hospital_id,
    pc.campaign_id,
    pc.campaign_code,
    pc.campaign_name,
    pc.promotion_type,
    pc.discount_type,
    pc.discount_value,
    pc.start_date,
    pc.end_date,
    pc.is_active,
    pc.is_personalized,
    pc.target_special_group,
    pc.applies_to,
    pc.auto_apply,
    COUNT(pul.usage_id) AS total_uses,
    COUNT(DISTINCT pul.patient_id) AS unique_patients,
    COALESCE(SUM(pul.discount_amount), 0) AS total_discount_given,
    CASE
        WHEN pc.max_total_uses IS NOT NULL AND pc.max_total_uses > 0
        THEN ROUND((COUNT(pul.usage_id)::numeric / pc.max_total_uses) * 100, 2)
        ELSE NULL
    END AS usage_percent
FROM promotion_campaigns pc
LEFT JOIN promotion_usage_log pul ON pc.campaign_id = pul.campaign_id
WHERE pc.is_deleted = FALSE
GROUP BY
    pc.hospital_id, pc.campaign_id, pc.campaign_code, pc.campaign_name,
    pc.promotion_type, pc.discount_type, pc.discount_value,
    pc.start_date, pc.end_date, pc.is_active, pc.is_personalized,
    pc.target_special_group, pc.applies_to, pc.auto_apply, pc.max_total_uses;

-- =============================================================================
-- 6. SPECIAL GROUP PATIENT LIST VIEW
-- =============================================================================
-- Useful for Email/WhatsApp campaigns
-- Uses patient_loyalty_wallet (not patient_loyalty_cards which doesn't exist)

CREATE OR REPLACE VIEW v_special_group_patients AS
SELECT
    p.hospital_id,
    p.patient_id,
    p.mrn,
    p.first_name,
    p.last_name,
    p.full_name,
    p.contact_info->>'email' AS email,
    p.contact_info->>'phone' AS phone,
    p.contact_info->>'mobile' AS mobile,
    plw.card_type_id,
    lct.card_type_name AS loyalty_card_type,
    lct.discount_percent AS loyalty_discount_percent,
    plw.points_balance AS wallet_points_balance,
    p.created_at AS registered_date
FROM patients p
LEFT JOIN patient_loyalty_wallet plw ON p.patient_id = plw.patient_id AND plw.is_active = TRUE
LEFT JOIN loyalty_card_types lct ON plw.card_type_id = lct.card_type_id AND lct.is_active = TRUE
WHERE p.is_special_group = TRUE
  AND p.is_deleted = FALSE
  AND p.is_active = TRUE;

COMMENT ON VIEW v_special_group_patients IS
'List of special group patients with contact info for targeted campaigns';
