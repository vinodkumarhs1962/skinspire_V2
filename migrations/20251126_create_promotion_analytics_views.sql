-- Promotion Analytics Views
-- Created: 2025-11-26
-- Purpose: Views for Promotions Dashboard analytics and reporting

-- ============================================================================
-- View: Promotion Campaign Effectiveness Summary
-- Shows usage statistics and ROI for each campaign
-- ============================================================================
DROP VIEW IF EXISTS v_promotion_effectiveness CASCADE;

CREATE OR REPLACE VIEW v_promotion_effectiveness AS
SELECT
    pc.campaign_id,
    pc.hospital_id,
    pc.campaign_code,
    pc.campaign_name,
    pc.promotion_type,
    pc.discount_type,
    pc.discount_value,
    pc.start_date,
    pc.end_date,
    pc.is_active,
    pc.is_personalized,
    pc.applies_to,
    pc.max_total_uses,
    pc.current_uses,
    COUNT(pul.usage_id) as total_uses,
    COALESCE(SUM(pul.discount_amount), 0) as total_discount_given,
    COALESCE(SUM(pul.invoice_amount), 0) as total_revenue_generated,
    CASE
        WHEN COALESCE(SUM(pul.invoice_amount), 0) > 0
        THEN ROUND((COALESCE(SUM(pul.discount_amount), 0) / SUM(pul.invoice_amount)) * 100, 2)
        ELSE 0
    END as discount_to_revenue_ratio,
    CASE
        WHEN pc.end_date < CURRENT_DATE THEN 'expired'
        WHEN pc.start_date > CURRENT_DATE THEN 'upcoming'
        WHEN pc.is_active = true THEN 'active'
        ELSE 'inactive'
    END as campaign_status,
    -- Days remaining or days since end
    CASE
        WHEN pc.end_date >= CURRENT_DATE THEN (pc.end_date - CURRENT_DATE)
        ELSE -(CURRENT_DATE - pc.end_date)
    END as days_remaining
FROM promotion_campaigns pc
LEFT JOIN promotion_usage_log pul ON pc.campaign_id = pul.campaign_id
WHERE pc.is_deleted = false
GROUP BY
    pc.campaign_id, pc.hospital_id, pc.campaign_code, pc.campaign_name,
    pc.promotion_type, pc.discount_type, pc.discount_value,
    pc.start_date, pc.end_date, pc.is_active, pc.is_personalized,
    pc.applies_to, pc.max_total_uses, pc.current_uses;

COMMENT ON VIEW v_promotion_effectiveness IS 'Campaign effectiveness metrics with usage statistics and ROI';


-- ============================================================================
-- View: Daily Discount Breakdown by Type
-- Aggregates discount applications by day and type
-- ============================================================================
DROP VIEW IF EXISTS v_daily_discount_breakdown CASCADE;

CREATE OR REPLACE VIEW v_daily_discount_breakdown AS
SELECT
    dal.hospital_id,
    DATE(dal.applied_at) as discount_date,
    dal.discount_type,
    COUNT(*) as application_count,
    COALESCE(SUM(dal.discount_amount), 0) as total_discount,
    COALESCE(AVG(dal.discount_amount), 0) as avg_discount,
    COALESCE(SUM(dal.original_price), 0) as total_original_value,
    COALESCE(SUM(dal.final_price), 0) as total_final_value
FROM discount_application_log dal
GROUP BY dal.hospital_id, DATE(dal.applied_at), dal.discount_type
ORDER BY discount_date DESC, discount_type;

COMMENT ON VIEW v_daily_discount_breakdown IS 'Daily discount metrics grouped by discount type';


-- ============================================================================
-- View: Active Promotions Timeline
-- Union of all promotion types for timeline visualization
-- ============================================================================
DROP VIEW IF EXISTS v_active_promotions_timeline CASCADE;

CREATE OR REPLACE VIEW v_active_promotions_timeline AS
-- Campaign promotions
SELECT
    'campaign' as promotion_category,
    pc.campaign_id::text as id,
    pc.hospital_id,
    pc.campaign_code as code,
    pc.campaign_name as name,
    pc.promotion_type as subtype,
    pc.discount_type,
    pc.discount_value,
    pc.start_date,
    pc.end_date,
    pc.is_active,
    pc.is_personalized,
    pc.applies_to,
    pc.current_uses,
    pc.max_total_uses,
    CASE
        WHEN pc.end_date < CURRENT_DATE THEN 'expired'
        WHEN pc.start_date > CURRENT_DATE THEN 'upcoming'
        WHEN pc.is_active = true THEN 'active'
        ELSE 'inactive'
    END as status
FROM promotion_campaigns pc
WHERE pc.is_deleted = false

UNION ALL

-- Bulk discount (per hospital - shows as continuous line)
SELECT
    'bulk' as promotion_category,
    h.hospital_id::text as id,
    h.hospital_id,
    'BULK' as code,
    'Bulk Discount Policy' as name,
    NULL as subtype,
    'percentage' as discount_type,
    NULL as discount_value,
    h.bulk_discount_effective_from as start_date,
    NULL as end_date,
    h.bulk_discount_enabled as is_active,
    false as is_personalized,
    'services' as applies_to,
    NULL as current_uses,
    NULL as max_total_uses,
    CASE WHEN h.bulk_discount_enabled THEN 'active' ELSE 'inactive' END as status
FROM hospitals h
WHERE h.bulk_discount_effective_from IS NOT NULL;

COMMENT ON VIEW v_active_promotions_timeline IS 'Unified view of all promotion types for timeline display';


-- ============================================================================
-- View: Monthly Promotion Usage Summary
-- Monthly aggregation of promotion usage
-- ============================================================================
DROP VIEW IF EXISTS v_monthly_promotion_usage CASCADE;

CREATE OR REPLACE VIEW v_monthly_promotion_usage AS
SELECT
    pul.hospital_id,
    DATE_TRUNC('month', pul.usage_date) as month,
    pc.campaign_code,
    pc.campaign_name,
    COUNT(pul.usage_id) as usage_count,
    COALESCE(SUM(pul.discount_amount), 0) as total_discount,
    COALESCE(SUM(pul.invoice_amount), 0) as total_revenue,
    COUNT(DISTINCT pul.patient_id) as unique_patients
FROM promotion_usage_log pul
JOIN promotion_campaigns pc ON pul.campaign_id = pc.campaign_id
GROUP BY
    pul.hospital_id,
    DATE_TRUNC('month', pul.usage_date),
    pc.campaign_code,
    pc.campaign_name
ORDER BY month DESC, usage_count DESC;

COMMENT ON VIEW v_monthly_promotion_usage IS 'Monthly promotion usage aggregation';


-- ============================================================================
-- View: Top Performing Campaigns
-- Ranked campaigns by usage within a rolling 30-day window
-- ============================================================================
DROP VIEW IF EXISTS v_top_campaigns_30d CASCADE;

CREATE OR REPLACE VIEW v_top_campaigns_30d AS
SELECT
    pul.hospital_id,
    pc.campaign_id,
    pc.campaign_code,
    pc.campaign_name,
    pc.promotion_type,
    COUNT(pul.usage_id) as usage_count,
    COALESCE(SUM(pul.discount_amount), 0) as total_discount,
    COALESCE(SUM(pul.invoice_amount), 0) as total_revenue,
    COUNT(DISTINCT pul.patient_id) as unique_patients,
    RANK() OVER (PARTITION BY pul.hospital_id ORDER BY COUNT(pul.usage_id) DESC) as usage_rank,
    RANK() OVER (PARTITION BY pul.hospital_id ORDER BY SUM(pul.invoice_amount) DESC) as revenue_rank
FROM promotion_usage_log pul
JOIN promotion_campaigns pc ON pul.campaign_id = pc.campaign_id
WHERE pul.usage_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY
    pul.hospital_id,
    pc.campaign_id,
    pc.campaign_code,
    pc.campaign_name,
    pc.promotion_type
ORDER BY usage_count DESC;

COMMENT ON VIEW v_top_campaigns_30d IS 'Top performing campaigns in last 30 days';


-- ============================================================================
-- View: Overlapping Campaigns Detection
-- Identifies campaigns that overlap in time and target the same items
-- ============================================================================
DROP VIEW IF EXISTS v_campaign_overlaps CASCADE;

CREATE OR REPLACE VIEW v_campaign_overlaps AS
SELECT DISTINCT
    c1.hospital_id,
    c1.campaign_id as campaign_1_id,
    c1.campaign_code as campaign_1_code,
    c1.campaign_name as campaign_1_name,
    c2.campaign_id as campaign_2_id,
    c2.campaign_code as campaign_2_code,
    c2.campaign_name as campaign_2_name,
    GREATEST(c1.start_date, c2.start_date) as overlap_start,
    LEAST(c1.end_date, c2.end_date) as overlap_end,
    (LEAST(c1.end_date, c2.end_date) - GREATEST(c1.start_date, c2.start_date)) as overlap_days,
    CASE
        WHEN c1.applies_to = 'all' OR c2.applies_to = 'all' THEN 'high'
        WHEN c1.applies_to = c2.applies_to THEN 'high'
        ELSE 'low'
    END as severity
FROM promotion_campaigns c1
JOIN promotion_campaigns c2 ON
    c1.hospital_id = c2.hospital_id
    AND c1.campaign_id < c2.campaign_id  -- Prevent duplicate pairs
    AND c1.is_deleted = false
    AND c2.is_deleted = false
    AND c1.is_active = true
    AND c2.is_active = true
    -- Check date overlap
    AND c1.start_date <= c2.end_date
    AND c2.start_date <= c1.end_date
    -- Check target overlap
    AND (
        c1.applies_to = 'all'
        OR c2.applies_to = 'all'
        OR c1.applies_to = c2.applies_to
    );

COMMENT ON VIEW v_campaign_overlaps IS 'Detects overlapping campaigns that may conflict';


-- ============================================================================
-- View: Discount Summary by Type and Service
-- Shows discount statistics grouped by discount type
-- ============================================================================
DROP VIEW IF EXISTS v_discount_by_type CASCADE;

CREATE OR REPLACE VIEW v_discount_by_type AS
SELECT
    dal.hospital_id,
    dal.discount_type,
    COUNT(*) as application_count,
    COALESCE(SUM(dal.discount_amount), 0) as total_discount,
    COALESCE(AVG(dal.discount_percent), 0) as avg_discount_percent,
    COALESCE(SUM(dal.original_price), 0) as total_original_value,
    COUNT(DISTINCT dal.patient_id) as unique_patients,
    COUNT(DISTINCT dal.service_id) as unique_services
FROM discount_application_log dal
GROUP BY dal.hospital_id, dal.discount_type
ORDER BY total_discount DESC;

COMMENT ON VIEW v_discount_by_type IS 'Discount statistics grouped by discount type';


-- ============================================================================
-- Indexes for Performance (if tables don't have them)
-- ============================================================================

-- Index on promotion_usage_log for date-based queries
CREATE INDEX IF NOT EXISTS idx_promotion_usage_log_date
ON promotion_usage_log(hospital_id, usage_date);

-- Index on promotion_campaigns for timeline queries
CREATE INDEX IF NOT EXISTS idx_promotion_campaigns_dates
ON promotion_campaigns(hospital_id, start_date, end_date)
WHERE is_deleted = false;

-- Index on discount_application_log for analytics
CREATE INDEX IF NOT EXISTS idx_discount_app_log_date
ON discount_application_log(hospital_id, applied_at);


-- ============================================================================
-- Grant permissions (adjust as needed for your environment)
-- ============================================================================
-- GRANT SELECT ON v_promotion_effectiveness TO skinspire_app;
-- GRANT SELECT ON v_daily_discount_breakdown TO skinspire_app;
-- GRANT SELECT ON v_active_promotions_timeline TO skinspire_app;
-- GRANT SELECT ON v_monthly_promotion_usage TO skinspire_app;
-- GRANT SELECT ON v_top_campaigns_30d TO skinspire_app;
-- GRANT SELECT ON v_campaign_overlaps TO skinspire_app;
-- GRANT SELECT ON v_discount_by_type TO skinspire_app;

SELECT 'Promotion Analytics Views created successfully' as status;
