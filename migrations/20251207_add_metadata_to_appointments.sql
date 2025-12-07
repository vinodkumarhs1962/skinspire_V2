-- Migration: Add metadata column to appointments table
-- Purpose: Store external integration data like Google Calendar event IDs
-- Date: 2025-12-07

-- Add metadata column to appointments table
ALTER TABLE appointments
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Add comment for documentation
COMMENT ON COLUMN appointments.metadata IS 'External integrations metadata (Google Calendar event ID, etc.)';

-- Create index for efficient JSON queries if needed
CREATE INDEX IF NOT EXISTS idx_appointments_metadata_gcal
ON appointments ((metadata->>'google_calendar_event_id'))
WHERE metadata->>'google_calendar_event_id' IS NOT NULL;
