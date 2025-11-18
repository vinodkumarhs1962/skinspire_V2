-- =====================================================================
-- Patient Master View v1.0
-- =====================================================================
-- Purpose: Flatten JSONB fields for easy access across the application
-- Created: 2025-01-07
-- Dependencies: patients table
-- =====================================================================

DROP VIEW IF EXISTS patient_master_view CASCADE;

CREATE VIEW patient_master_view AS
SELECT
    -- === PRIMARY KEY ===
    p.patient_id,

    -- === BASIC INFO ===
    p.mrn,
    p.title,
    p.first_name,
    p.last_name,
    p.full_name,

    -- Computed full name (without title)
    COALESCE(
        NULLIF(TRIM(CONCAT(
            COALESCE(p.first_name, p.personal_info->>'first_name', ''),
            CASE WHEN COALESCE(p.first_name, p.personal_info->>'first_name') IS NOT NULL
                  AND COALESCE(p.last_name, p.personal_info->>'last_name') IS NOT NULL
                  THEN ' ' ELSE '' END,
            COALESCE(p.last_name, p.personal_info->>'last_name', '')
        )), ''),
        p.full_name,
        'Unknown'
    ) AS display_name,

    p.blood_group,
    -- Extract from personal_info JSONB
    p.personal_info->>'gender' AS gender,
    p.personal_info->>'date_of_birth' AS date_of_birth,
    p.personal_info->>'age' AS age,

    -- === CONTACT INFORMATION (Flattened from JSONB) ===
    -- Try extracting as JSON first, if that fails, parse as text
    COALESCE(
        CASE
            WHEN jsonb_typeof(p.contact_info) = 'object' THEN p.contact_info->>'phone'
            WHEN jsonb_typeof(p.contact_info) = 'string' THEN (p.contact_info#>>'{}'::text[])::jsonb->>'phone'
            ELSE NULL
        END,
        ''
    ) AS phone,

    COALESCE(
        CASE
            WHEN jsonb_typeof(p.contact_info) = 'object' THEN p.contact_info->>'mobile'
            WHEN jsonb_typeof(p.contact_info) = 'string' THEN (p.contact_info#>>'{}'::text[])::jsonb->>'mobile'
            ELSE NULL
        END,
        ''
    ) AS mobile,

    COALESCE(
        CASE
            WHEN jsonb_typeof(p.contact_info) = 'object' THEN p.contact_info->>'email'
            WHEN jsonb_typeof(p.contact_info) = 'string' THEN (p.contact_info#>>'{}'::text[])::jsonb->>'email'
            ELSE NULL
        END,
        ''
    ) AS email,

    -- Format address
    CASE
        WHEN jsonb_typeof(p.contact_info) = 'object' AND p.contact_info->'address' IS NOT NULL THEN
            CASE
                WHEN jsonb_typeof(p.contact_info->'address') = 'object' THEN
                    TRIM(CONCAT_WS(', ',
                        NULLIF(p.contact_info->'address'->>'street', ''),
                        NULLIF(p.contact_info->'address'->>'city', ''),
                        NULLIF(p.contact_info->'address'->>'zip', '')
                    ))
                ELSE p.contact_info->>'address'
            END
        WHEN jsonb_typeof(p.contact_info) = 'string' THEN
            CASE
                WHEN (p.contact_info#>>'{}'::text[])::jsonb->'address' IS NOT NULL THEN
                    CASE
                        WHEN jsonb_typeof((p.contact_info#>>'{}'::text[])::jsonb->'address') = 'object' THEN
                            TRIM(CONCAT_WS(', ',
                                NULLIF((p.contact_info#>>'{}'::text[])::jsonb->'address'->>'street', ''),
                                NULLIF((p.contact_info#>>'{}'::text[])::jsonb->'address'->>'city', ''),
                                NULLIF((p.contact_info#>>'{}'::text[])::jsonb->'address'->>'zip', '')
                            ))
                        ELSE (p.contact_info#>>'{}'::text[])::jsonb->>'address'
                    END
                ELSE ''
            END
        ELSE ''
    END AS address,

    -- === MEDICAL INFO (Flattened from JSONB) ===
    p.personal_info->>'allergies' AS allergies,
    p.personal_info->>'chronic_conditions' AS chronic_conditions,

    -- === TENANT INFO ===
    p.hospital_id,
    p.is_active,

    -- === AUDIT TRAIL ===
    p.created_at,
    p.created_by,
    p.updated_at,
    p.updated_by

FROM patients p
WHERE p.is_active = TRUE;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_patient_master_view_hospital ON patients(hospital_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_patient_master_view_mrn ON patients(mrn) WHERE is_active = TRUE;

COMMENT ON VIEW patient_master_view IS 'Patient master view with flattened JSONB fields for easy access';
