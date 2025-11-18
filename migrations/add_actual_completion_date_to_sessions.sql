-- Migration: Add actual_completion_date to package_sessions table
-- Purpose: Distinguish between scheduled date (can be rescheduled) and actual completion date
-- Date: 2025-11-12

-- Add actual_completion_date field to package_sessions
ALTER TABLE package_sessions
ADD COLUMN actual_completion_date DATE;

-- Comment explaining the fields
COMMENT ON COLUMN package_sessions.session_date IS 'Scheduled session date (can be rescheduled by patient/clinic request)';
COMMENT ON COLUMN package_sessions.actual_completion_date IS 'Actual date when session was completed';

-- Update existing completed sessions to set actual_completion_date = session_date
UPDATE package_sessions
SET actual_completion_date = session_date
WHERE session_status = 'completed' AND actual_completion_date IS NULL;

-- Verification query
SELECT
    session_id,
    session_number,
    session_date as scheduled_date,
    actual_completion_date,
    session_status
FROM package_sessions
ORDER BY plan_id, session_number;
