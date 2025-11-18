-- Migration: Sync completed_sessions count in package_payment_plans
-- Date: 2025-11-12
-- Purpose: Update all plans with correct completed_sessions count from package_sessions table

-- Update all package payment plans to reflect actual completed sessions count
UPDATE package_payment_plans ppp
SET completed_sessions = (
    SELECT COUNT(*)
    FROM package_sessions ps
    WHERE ps.plan_id = ppp.plan_id
      AND ps.session_status = 'completed'
      AND ps.hospital_id = ppp.hospital_id
);

-- Verify the update
SELECT
    ppp.plan_id,
    ppp.total_sessions,
    ppp.completed_sessions AS plan_completed_sessions,
    (SELECT COUNT(*) FROM package_sessions ps WHERE ps.plan_id = ppp.plan_id AND ps.session_status = 'completed') AS actual_completed_sessions
FROM package_payment_plans ppp
ORDER BY ppp.created_at DESC
LIMIT 10;
