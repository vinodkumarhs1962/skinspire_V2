-- Configuration Script: Set Bulk Discount Percentages for Services
-- Created: 2025-11-20
-- Description: Configure service-specific bulk discount rates
--
-- Instructions:
-- 1. Review and modify the discount percentages below based on your business rules
-- 2. Run this script after 20251120_create_bulk_discount_system.sql
-- 3. Discount percentages should not exceed the service's max_discount

-- ============================================
-- LASER TREATMENTS (10% bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 10.00
WHERE service_name LIKE '%Laser%'
  AND (max_discount IS NULL OR max_discount >= 10.00);

-- ============================================
-- FACIAL TREATMENTS (15% bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 15.00
WHERE service_name LIKE '%Facial%'
  AND (max_discount IS NULL OR max_discount >= 15.00);

-- If service has max_discount < 15%, cap at max_discount
UPDATE services
SET bulk_discount_percent = max_discount
WHERE service_name LIKE '%Facial%'
  AND max_discount IS NOT NULL
  AND max_discount < 15.00;

-- ============================================
-- MEDIFACIAL TREATMENTS (15% bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 15.00
WHERE service_name LIKE '%Medifacial%'
  AND (max_discount IS NULL OR max_discount >= 15.00);

-- ============================================
-- CHEMICAL PEELS (12% bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 12.00
WHERE service_name LIKE '%Chemical Peel%'
  AND (max_discount IS NULL OR max_discount >= 12.00);

-- ============================================
-- BOTOX/FILLER TREATMENTS (8% bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 8.00
WHERE (service_name LIKE '%Botox%' OR service_name LIKE '%Filler%')
  AND (max_discount IS NULL OR max_discount >= 8.00);

-- ============================================
-- HAIR TREATMENTS (10% bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 10.00
WHERE service_name LIKE '%Hair%'
  AND (max_discount IS NULL OR max_discount >= 10.00);

-- ============================================
-- BODY TREATMENTS (12% bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 12.00
WHERE (service_name LIKE '%Body%' OR service_name LIKE '%Massage%')
  AND (max_discount IS NULL OR max_discount >= 12.00);

-- ============================================
-- CONSULTATIONS (0% - typically no bulk discount)
-- ============================================
UPDATE services
SET bulk_discount_percent = 0.00
WHERE service_name LIKE '%Consultation%' OR service_name LIKE '%Examination%';

-- ============================================
-- VERIFICATION QUERY
-- ============================================
-- Run this to verify the changes:
-- SELECT
--     service_name,
--     max_discount,
--     bulk_discount_percent,
--     CASE
--         WHEN bulk_discount_percent > 0 THEN 'Discount Enabled'
--         ELSE 'No Discount'
--     END as status
-- FROM services
-- WHERE bulk_discount_percent > 0
-- ORDER BY bulk_discount_percent DESC, service_name;

-- Show summary by discount tier
SELECT
    bulk_discount_percent as discount_rate,
    COUNT(*) as service_count,
    STRING_AGG(service_name, ', ') as services
FROM services
WHERE bulk_discount_percent > 0
GROUP BY bulk_discount_percent
ORDER BY bulk_discount_percent DESC;

-- Show services without bulk discount
SELECT
    COUNT(*) as services_without_discount
FROM services
WHERE bulk_discount_percent = 0 OR bulk_discount_percent IS NULL;
