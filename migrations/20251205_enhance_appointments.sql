-- Migration: Enhance appointments table for better booking workflow
-- Date: 2025-12-05
-- Description: Adds appointment_purpose and patient_package_id columns
--              Standardizes booking_source values

-- Add appointment_purpose column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'appointment_purpose'
    ) THEN
        ALTER TABLE appointments ADD COLUMN appointment_purpose VARCHAR(30);
        COMMENT ON COLUMN appointments.appointment_purpose IS 'Purpose: consultation, follow_up, procedure, service, package_session';
    END IF;
END $$;

-- Add package_plan_id column if not exists (links to package_payment_plans for patient's package enrollment)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'appointments' AND column_name = 'package_plan_id'
    ) THEN
        ALTER TABLE appointments ADD COLUMN package_plan_id UUID REFERENCES package_payment_plans(plan_id);
        COMMENT ON COLUMN appointments.package_plan_id IS 'Links to package_payment_plans for patient package session bookings';
    END IF;
END $$;

-- Create index on appointment_purpose for filtering
CREATE INDEX IF NOT EXISTS idx_appointments_purpose ON appointments(appointment_purpose) WHERE is_deleted = FALSE;

-- Create index on package_plan_id
CREATE INDEX IF NOT EXISTS idx_appointments_package_plan ON appointments(package_plan_id) WHERE package_plan_id IS NOT NULL;

-- Standardize booking_source values (update old values to new standard)
UPDATE appointments SET booking_source = 'front_desk' WHERE booking_source = 'receptionist';

-- Add comment on booking_source
COMMENT ON COLUMN appointments.booking_source IS 'Booking channel: walk_in, scheduled, online, phone, front_desk, app, kiosk';

-- Update existing appointments with purpose based on current data
-- Package sessions (have package_id)
UPDATE appointments
SET appointment_purpose = 'package_session'
WHERE package_id IS NOT NULL AND appointment_purpose IS NULL;

-- Service appointments (have service_id but no package)
UPDATE appointments
SET appointment_purpose = 'service'
WHERE service_id IS NOT NULL AND package_id IS NULL AND appointment_purpose IS NULL;

-- Follow-ups (have follow_up reference)
UPDATE appointments
SET appointment_purpose = 'follow_up'
WHERE (is_follow_up = TRUE OR follow_up_of_consultation_id IS NOT NULL) AND appointment_purpose IS NULL;

-- Remaining as consultations
UPDATE appointments
SET appointment_purpose = 'consultation'
WHERE appointment_purpose IS NULL;

-- Verify the migration
SELECT
    'appointment_purpose distribution' as check_type,
    appointment_purpose,
    COUNT(*) as count
FROM appointments
WHERE is_deleted = FALSE
GROUP BY appointment_purpose
ORDER BY count DESC;
