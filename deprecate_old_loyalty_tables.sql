-- DEPRECATE OLD LOYALTY SYSTEM TABLES
-- Date: November 24, 2025
-- Purpose: Move old loyalty tables to deprecated schema for safe removal

BEGIN;

-- Step 1: Create deprecated schema if not exists
CREATE SCHEMA IF NOT EXISTS deprecated_loyalty;

-- Step 2: Add comments to identify why these are being moved
COMMENT ON TABLE patient_loyalty_cards IS 'DEPRECATED Nov 24 2025 - Replaced by patient_loyalty_wallet';
COMMENT ON TABLE loyalty_points IS 'DEPRECATED Nov 24 2025 - Replaced by wallet_transaction';
COMMENT ON TABLE loyalty_redemptions IS 'DEPRECATED Nov 24 2025 - Replaced by wallet_transaction';

-- Step 3: Move tables to deprecated schema (keeping data for 30 days backup)
ALTER TABLE patient_loyalty_cards SET SCHEMA deprecated_loyalty;
ALTER TABLE loyalty_points SET SCHEMA deprecated_loyalty;
ALTER TABLE loyalty_redemptions SET SCHEMA deprecated_loyalty;

-- Step 4: Verification - show what's in deprecated schema
SELECT
    'MOVED TO DEPRECATED SCHEMA' as status,
    tablename,
    schemaname
FROM pg_tables
WHERE schemaname = 'deprecated_loyalty'
ORDER BY tablename;

-- Step 5: Show active wallet tables
SELECT
    'ACTIVE WALLET SYSTEM' as status,
    tablename,
    schemaname
FROM pg_tables
WHERE tablename IN ('patient_loyalty_wallet', 'wallet_transaction', 'wallet_points_batch')
ORDER BY tablename;

COMMIT;

-- Instructions for future cleanup (run after 30 days):
/*
-- After verifying NEW system works in production for 30 days, run this:

BEGIN;

-- Drop old tables from deprecated schema
DROP TABLE IF EXISTS deprecated_loyalty.loyalty_redemptions CASCADE;
DROP TABLE IF EXISTS deprecated_loyalty.loyalty_points CASCADE;
DROP TABLE IF EXISTS deprecated_loyalty.patient_loyalty_cards CASCADE;

-- Drop the schema
DROP SCHEMA IF EXISTS deprecated_loyalty CASCADE;

COMMIT;
*/
