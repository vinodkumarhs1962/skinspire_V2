-- Sample Data: Hair Restoration Package BOM and Session Plan
-- Created: 2025-11-18
-- Description: Comprehensive sample data for Hair Restoration Package with advanced BOM and session planning

-- Package: Hair Restoration Package
-- Package ID: 1b92889e-6dce-4ce0-8146-d0e288b9e894
-- Hospital ID: 4ef72e18-e65d-4766-b9eb-0308c42485ca

-- ============================================
-- PACKAGE BOM ITEMS - Hair Restoration Package
-- ============================================

-- Service Items
INSERT INTO package_bom_items (
    bom_item_id, package_id, item_type, item_id, item_name,
    quantity, unit_of_measure, supply_method, current_price, line_total,
    is_optional, notes, display_sequence, hospital_id
) VALUES
-- 1. Laser Hair Removal (per session item)
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    'service',
    '950de02b-c36f-4af4-9260-7c9688615fc4',
    'Laser Hair Removal',
    6.00,  -- 6 sessions
    'session',
    'per_session',
    2500.00,
    15000.00,
    FALSE,
    'Six laser sessions required for optimal results - one per session',
    1,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
-- 2. Botox Injection (optional upgrade)
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    'service',
    '6b308d3a-7233-4396-8da1-c6d0391acb1c',
    'Botox Injection',
    1.00,
    'session',
    'conditional',
    4500.00,
    4500.00,
    TRUE,
    'Optional - for scalp relaxation if recommended by doctor',
    2,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Medicine/Supplement Items
INSERT INTO package_bom_items (
    bom_item_id, package_id, item_type, item_id, item_name,
    quantity, unit_of_measure, supply_method, current_price, line_total,
    is_optional, notes, display_sequence, hospital_id
) VALUES
-- 3. Multivitamin (monthly supply)
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    'medicine',
    '427f7800-6253-4065-bb01-1988f860bf41',
    'Multivitamin Tablets',
    180.00,  -- 6 months supply (30 per month)
    'tablets',
    'per_package',
    900.00,
    900.00,
    FALSE,
    'Complete 6-month supply - one tablet daily for hair health',
    3,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
-- 4. Amoxicillin (on demand - post procedure)
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    'medicine',
    '6ddf27d5-e733-470d-9449-b594030959b2',
    'Amoxicillin 500mg',
    15.00,
    'tablets',
    'on_demand',
    150.00,
    150.00,
    TRUE,
    'Prescribed if needed post-procedure to prevent infection',
    4,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
-- 5. Ibuprofen (on demand - pain management)
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    'medicine',
    '9a044a7e-71b3-4dd8-9d57-ebe9cffe1490',
    'Ibuprofen 400mg',
    20.00,
    'tablets',
    'on_demand',
    80.00,
    80.00,
    TRUE,
    'Available for discomfort management post-treatment',
    5,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- ============================================
-- PACKAGE SESSION PLAN - Hair Restoration Package
-- ============================================

-- Session 1: Comprehensive Assessment
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES (
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    1,
    'Comprehensive Hair & Scalp Assessment',
    'Detailed consultation, scalp analysis, hair density measurement, and treatment plan customization',
    60,
    NULL,
    '[
        {
            "resource_type": "doctor",
            "role": "Trichologist / Dermatologist",
            "duration_minutes": 40,
            "quantity": 1
        },
        {
            "resource_type": "nurse",
            "role": "Trichology Nurse",
            "duration_minutes": 20,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    1,
    'Initial assessment requires specialized trichology equipment. Book consultation slot.',
    'Patient must complete detailed medical history and medication questionnaire',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Session 2-7: Laser Treatment Sessions (6 sessions)
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    2,
    'Laser Treatment Session 1',
    'First laser therapy session for hair restoration and scalp stimulation',
    45,
    7,
    '[
        {
            "resource_type": "doctor",
            "role": "Laser Specialist",
            "duration_minutes": 10,
            "quantity": 1
        },
        {
            "resource_type": "therapist",
            "role": "Laser Technician",
            "duration_minutes": 45,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    2,
    'Minimum 7 days gap after initial consultation. Patient should wash hair before session.',
    'Initial assessment completed. No active scalp infection.',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    3,
    'Laser Treatment Session 2',
    'Second laser therapy session - monitoring initial response',
    45,
    14,
    '[
        {
            "resource_type": "therapist",
            "role": "Laser Technician",
            "duration_minutes": 45,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    3,
    'Maintain 14-21 day gaps between laser sessions for optimal results',
    'Previous laser session completed. No adverse reactions.',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    4,
    'Laser Treatment Session 3',
    'Third laser therapy session with intensity adjustment based on response',
    45,
    14,
    '[
        {
            "resource_type": "therapist",
            "role": "Laser Technician",
            "duration_minutes": 45,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    4,
    'Continue 14-21 day interval. Document any changes in hair growth.',
    'Previous laser session completed.',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    5,
    'Laser Treatment Session 4',
    'Fourth laser therapy session - mid-treatment assessment',
    60,
    14,
    '[
        {
            "resource_type": "doctor",
            "role": "Laser Specialist",
            "duration_minutes": 15,
            "quantity": 1
        },
        {
            "resource_type": "therapist",
            "role": "Laser Technician",
            "duration_minutes": 45,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    5,
    'Mid-treatment review by doctor. Adjust protocol if needed.',
    'Three laser sessions completed. Progress photos required.',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    6,
    'Laser Treatment Session 5',
    'Fifth laser therapy session',
    45,
    14,
    '[
        {
            "resource_type": "therapist",
            "role": "Laser Technician",
            "duration_minutes": 45,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    6,
    'Continue consistent treatment schedule',
    'Previous laser session completed.',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
(
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    7,
    'Laser Treatment Session 6 (Final)',
    'Final laser therapy session with comprehensive before/after assessment',
    60,
    14,
    '[
        {
            "resource_type": "doctor",
            "role": "Trichologist / Dermatologist",
            "duration_minutes": 20,
            "quantity": 1
        },
        {
            "resource_type": "therapist",
            "role": "Laser Technician",
            "duration_minutes": 45,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    7,
    'Final session with complete assessment. Schedule follow-up review.',
    'Five laser sessions completed. Final progress photos required.',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Session 8: Final Review & Maintenance Plan
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES (
    gen_random_uuid(),
    '1b92889e-6dce-4ce0-8146-d0e288b9e894',
    8,
    'Final Review & Long-term Maintenance Plan',
    'Results evaluation, scalp health assessment, and customized maintenance protocol',
    45,
    30,
    '[
        {
            "resource_type": "doctor",
            "role": "Trichologist / Dermatologist",
            "duration_minutes": 30,
            "quantity": 1
        },
        {
            "resource_type": "nurse",
            "role": "Trichology Nurse",
            "duration_minutes": 15,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    8,
    'Schedule 30 days after final laser session to assess sustained results',
    'All treatment sessions completed. Before/after documentation ready.',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);
