-- Migration: Deprecate Campaign Hook System
-- Date: 2025-11-21
-- Author: Claude Code
--
-- CONTEXT:
-- Campaign hooks were a plugin-based promotion system that allowed Python/API/SQL
-- functions to modify prices. This has been superseded by the promotion_campaigns
-- table with database-driven rules (Buy X Get Y, tiered discounts, etc.).
--
-- VERIFICATION BEFORE RUNNING:
-- 1. Confirmed campaign_hook_config table has 0 records
-- 2. Confirmed no code calls pricing_tax_service with apply_campaigns=True
-- 3. Confirmed discount_service now uses promotion_campaigns exclusively
--
-- SAFETY:
-- - This migration is safe to run because the table is empty
-- - The campaign hook service is not being actively used
-- - All promotion logic has been migrated to promotion_campaigns table

-- ============================================================================
-- BACKUP CURRENT STATE (Optional - only if table has data)
-- ============================================================================

-- If you want to backup before dropping (though table is empty):
-- CREATE TABLE campaign_hook_config_backup_20251121 AS
-- SELECT * FROM campaign_hook_config;

-- ============================================================================
-- DROP CAMPAIGN HOOK SYSTEM
-- ============================================================================

-- Drop indexes first
DROP INDEX IF EXISTS idx_campaign_hook_active;
DROP INDEX IF EXISTS idx_campaign_hook_effective_period;
DROP INDEX IF EXISTS idx_campaign_hook_hospital;
DROP INDEX IF EXISTS idx_campaign_hook_medicines;
DROP INDEX IF EXISTS idx_campaign_hook_packages;
DROP INDEX IF EXISTS idx_campaign_hook_services;

-- Drop unique constraint
ALTER TABLE campaign_hook_config
DROP CONSTRAINT IF EXISTS campaign_hook_config_hospital_hook_unique;

-- Drop the table
DROP TABLE IF EXISTS campaign_hook_config CASCADE;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify table is dropped
SELECT 'campaign_hook_config table dropped successfully' AS status
WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema='public'
    AND table_name='campaign_hook_config'
);

-- List remaining promotion-related tables (should show promotion_campaigns, etc.)
SELECT table_name
FROM information_schema.tables
WHERE table_schema='public'
AND table_name LIKE '%campaign%' OR table_name LIKE '%promotion%'
ORDER BY table_name;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

COMMENT ON SCHEMA public IS 'Campaign hook system removed on 2025-11-21. Use promotion_campaigns table for all promotions.';

-- Success message
SELECT
    'MIGRATION COMPLETE' AS status,
    'Campaign hook system deprecated' AS action,
    'Use promotion_campaigns for all promotions (simple_discount, buy_x_get_y, tiered_discount, bundle)' AS note;
