-- Bulk Discount Configuration Diagnostic Query
-- Run this to check why bulk discount isn't firing for Advanced Facial

-- 1. Check Hospital Configuration
SELECT
    hospital_name,
    bulk_discount_enabled,
    bulk_discount_min_service_count,
    bulk_discount_effective_from,
    loyalty_discount_mode
FROM hospitals
WHERE is_active = TRUE;

-- 2. Check Service Configuration (Advanced Facial)
SELECT
    service_name,
    base_price,
    bulk_discount_percent,
    loyalty_discount_percent,
    standard_discount_percent,
    max_discount,
    is_active
FROM services
WHERE service_name ILIKE '%facial%'
AND is_active = TRUE
ORDER BY service_name;

-- 3. Check if Advanced Facial has bulk discount configured
SELECT
    service_id,
    service_name,
    CASE
        WHEN bulk_discount_percent IS NULL THEN '❌ NOT CONFIGURED'
        WHEN bulk_discount_percent = 0 THEN '❌ SET TO ZERO'
        ELSE '✅ CONFIGURED: ' || bulk_discount_percent || '%'
    END as bulk_discount_status
FROM services
WHERE service_name ILIKE '%advanced%facial%'
AND is_active = TRUE;

-- 4. Expected Behavior Check
WITH config AS (
    SELECT
        bulk_discount_enabled,
        bulk_discount_min_service_count
    FROM hospitals
    WHERE is_active = TRUE
    LIMIT 1
),
service AS (
    SELECT
        service_name,
        bulk_discount_percent
    FROM services
    WHERE service_name ILIKE '%advanced%facial%'
    AND is_active = TRUE
    LIMIT 1
)
SELECT
    CASE
        WHEN c.bulk_discount_enabled = FALSE THEN
            '❌ ISSUE: Bulk discount disabled at hospital level'
        WHEN s.bulk_discount_percent IS NULL OR s.bulk_discount_percent = 0 THEN
            '❌ ISSUE: Service does not have bulk_discount_percent configured'
        WHEN c.bulk_discount_min_service_count > 5 THEN
            '⚠️ ISSUE: Threshold too high (' || c.bulk_discount_min_service_count || ' services required)'
        ELSE
            '✅ Configuration OK - Bulk discount should fire for qty 5+'
    END as diagnosis,
    c.bulk_discount_enabled as hospital_enabled,
    c.bulk_discount_min_service_count as min_threshold,
    s.bulk_discount_percent as service_discount_percent
FROM config c
CROSS JOIN service s;
