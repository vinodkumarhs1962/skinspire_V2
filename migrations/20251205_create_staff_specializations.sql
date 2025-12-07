-- Migration: Create staff_specializations lookup table
-- Date: 2025-12-05
-- Description: Adds a hospital-level lookup table for staff specializations
--              Supports different specializations per staff type (doctor, nurse, therapist, etc.)

-- Create the staff_specializations table
CREATE TABLE IF NOT EXISTS staff_specializations (
    specialization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Which staff type this specialization applies to
    staff_type VARCHAR(20) NOT NULL,  -- 'doctor', 'nurse', 'therapist', 'technician', 'all'

    -- Specialization details
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Display order for UI
    display_order INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),

    -- Soft delete fields (for SoftDeleteMixin)
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(100),

    -- Unique constraint
    CONSTRAINT uq_specialization_code UNIQUE (hospital_id, staff_type, code)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_staff_specializations_hospital ON staff_specializations(hospital_id);
CREATE INDEX IF NOT EXISTS idx_staff_specializations_staff_type ON staff_specializations(hospital_id, staff_type);
CREATE INDEX IF NOT EXISTS idx_staff_specializations_active ON staff_specializations(hospital_id, is_active) WHERE is_deleted = FALSE;

-- Add specialization_id column to staff table if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'staff' AND column_name = 'specialization_id'
    ) THEN
        ALTER TABLE staff ADD COLUMN specialization_id UUID REFERENCES staff_specializations(specialization_id);
    END IF;
END $$;

-- Create index on staff.specialization_id
CREATE INDEX IF NOT EXISTS idx_staff_specialization_id ON staff(specialization_id);

-- Insert default specializations for doctors (common medical specializations)
-- These will be added to the first hospital found (you may need to adjust)
INSERT INTO staff_specializations (hospital_id, staff_type, code, name, description, display_order, is_active)
SELECT
    h.hospital_id,
    'doctor',
    spec.code,
    spec.name,
    spec.description,
    spec.display_order,
    TRUE
FROM hospitals h
CROSS JOIN (VALUES
    ('GEN_MED', 'General Medicine', 'General medical practice', 1),
    ('DERM', 'Dermatology', 'Skin and cosmetic treatments', 2),
    ('CARDIO', 'Cardiology', 'Heart and cardiovascular system', 3),
    ('ORTHO', 'Orthopedics', 'Bone and joint treatments', 4),
    ('PEDIA', 'Pediatrics', 'Child healthcare', 5),
    ('GYNEC', 'Gynecology', 'Women health', 6),
    ('NEURO', 'Neurology', 'Nervous system disorders', 7),
    ('ENT', 'ENT', 'Ear, Nose and Throat', 8),
    ('OPHTH', 'Ophthalmology', 'Eye care', 9),
    ('DENTAL', 'Dental', 'Dental care and treatments', 10),
    ('PLASTIC', 'Plastic Surgery', 'Cosmetic and reconstructive surgery', 11),
    ('AESTH', 'Aesthetic Medicine', 'Non-surgical cosmetic procedures', 12)
) AS spec(code, name, description, display_order)
WHERE NOT EXISTS (
    SELECT 1 FROM staff_specializations ss
    WHERE ss.hospital_id = h.hospital_id
    AND ss.staff_type = 'doctor'
    AND ss.code = spec.code
)
LIMIT 12;  -- One hospital

-- Insert default specializations for nurses
INSERT INTO staff_specializations (hospital_id, staff_type, code, name, description, display_order, is_active)
SELECT
    h.hospital_id,
    'nurse',
    spec.code,
    spec.name,
    spec.description,
    spec.display_order,
    TRUE
FROM hospitals h
CROSS JOIN (VALUES
    ('GEN', 'General Nursing', 'General patient care', 1),
    ('ICU', 'ICU Nursing', 'Intensive care unit', 2),
    ('OT', 'OT Nursing', 'Operation theatre', 3),
    ('PEDIA', 'Pediatric Nursing', 'Child care', 4),
    ('AESTH', 'Aesthetic Nursing', 'Cosmetic procedure assistance', 5)
) AS spec(code, name, description, display_order)
WHERE NOT EXISTS (
    SELECT 1 FROM staff_specializations ss
    WHERE ss.hospital_id = h.hospital_id
    AND ss.staff_type = 'nurse'
    AND ss.code = spec.code
)
LIMIT 5;  -- One hospital

-- Insert default specializations for therapists
INSERT INTO staff_specializations (hospital_id, staff_type, code, name, description, display_order, is_active)
SELECT
    h.hospital_id,
    'therapist',
    spec.code,
    spec.name,
    spec.description,
    spec.display_order,
    TRUE
FROM hospitals h
CROSS JOIN (VALUES
    ('PHYSIO', 'Physiotherapy', 'Physical rehabilitation', 1),
    ('OCCUP', 'Occupational Therapy', 'Daily activity rehabilitation', 2),
    ('SPEECH', 'Speech Therapy', 'Speech and communication', 3),
    ('MASSAGE', 'Massage Therapy', 'Therapeutic massage', 4),
    ('SKIN', 'Skin Therapist', 'Skin treatments and facials', 5)
) AS spec(code, name, description, display_order)
WHERE NOT EXISTS (
    SELECT 1 FROM staff_specializations ss
    WHERE ss.hospital_id = h.hospital_id
    AND ss.staff_type = 'therapist'
    AND ss.code = spec.code
)
LIMIT 5;  -- One hospital

-- Add comment to table
COMMENT ON TABLE staff_specializations IS 'Hospital-level lookup table for staff specializations grouped by staff type';
COMMENT ON COLUMN staff_specializations.staff_type IS 'Staff type: doctor, nurse, therapist, technician, or all';
COMMENT ON COLUMN staff_specializations.code IS 'Short code for the specialization (unique per hospital+staff_type)';
