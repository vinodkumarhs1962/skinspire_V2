-- Migration: Add is_resource column to staff table
-- Date: 2025-12-06
-- Description: Adds a flag to identify staff members who can be allocated as resources
--              to appointments (e.g., therapists, nurses, technicians)

-- Add is_resource column to staff table
ALTER TABLE staff
ADD COLUMN IF NOT EXISTS is_resource BOOLEAN DEFAULT false;

-- Add comment
COMMENT ON COLUMN staff.is_resource IS 'Indicates if this staff member can be allocated as a resource to appointments';

-- Set default for existing staff based on staff_type
-- Exclude admin, doctor, receptionist, pharmacist - they are not typically resources
UPDATE staff
SET is_resource = true
WHERE staff_type IN ('therapist', 'nurse', 'technician', 'staff')
  AND is_resource IS NOT true;

-- Ensure doctors and admins are not resources by default
UPDATE staff
SET is_resource = false
WHERE staff_type IN ('admin', 'doctor', 'receptionist', 'pharmacist')
  AND is_resource IS NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_staff_is_resource ON staff(is_resource) WHERE is_resource = true;

-- Verification
SELECT staff_type, is_resource, COUNT(*)
FROM staff
WHERE is_deleted = false
GROUP BY staff_type, is_resource
ORDER BY staff_type, is_resource;
