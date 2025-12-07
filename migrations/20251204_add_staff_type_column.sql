-- Migration: Add staff_type column to staff table
-- Date: 2025-12-04
-- Description: Adds a proper staff_type column to identify doctors, nurses, etc.

-- Step 1: Add the staff_type column
ALTER TABLE staff ADD COLUMN IF NOT EXISTS staff_type VARCHAR(20) DEFAULT 'staff';

-- Step 2: Populate staff_type based on existing title
-- Doctors have title = 'Dr'
UPDATE staff
SET staff_type = 'doctor'
WHERE title = 'Dr' AND (staff_type IS NULL OR staff_type = 'staff');

-- Staff with role_name containing 'Receptionist' in professional_info
UPDATE staff
SET staff_type = 'receptionist'
WHERE professional_info->>'role_name' ILIKE '%receptionist%'
  AND staff_type = 'staff';

-- Staff with role_name containing 'Administrator' in professional_info
UPDATE staff
SET staff_type = 'admin'
WHERE (professional_info->>'role_name' ILIKE '%administrator%'
   OR professional_info->>'role' ILIKE '%administrator%')
  AND staff_type = 'staff';

-- Step 3: Create an index for faster queries
CREATE INDEX IF NOT EXISTS idx_staff_staff_type ON staff(staff_type);

-- Step 4: Add a comment to document the column
COMMENT ON COLUMN staff.staff_type IS 'Type of staff: doctor, nurse, therapist, receptionist, admin, staff';

-- Verification query (run manually to check results)
-- SELECT staff_type, COUNT(*) FROM staff WHERE is_deleted = false GROUP BY staff_type;
