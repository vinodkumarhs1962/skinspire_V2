-- Sample Data: Package BOM and Session Plan
-- Created: 2025-11-18
-- Description: Comprehensive sample data for Basic Facial Package with BOM items and session delivery plan

-- Package: Basic Facial Package
-- Package ID: 2867d1b3-a59b-4360-8e41-91d99bd31aa4
-- Hospital ID: 4ef72e18-e65d-4766-b9eb-0308c42485ca

-- ============================================
-- PACKAGE BOM ITEMS - Basic Facial Package
-- ============================================

-- Service Items
INSERT INTO package_bom_items (
    bom_item_id, package_id, item_type, item_id, item_name,
    quantity, unit_of_measure, supply_method, current_price, line_total,
    is_optional, notes, display_sequence, hospital_id
) VALUES
-- 1. Basic Facial Service (Main service)
(
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    'service',
    '894b033f-64f7-42a4-b052-6a9d2a14e13a',
    'Basic Facial',
    1.00,
    'session',
    'per_package',
    800.00,
    800.00,
    FALSE,
    'Core facial treatment - mandatory',
    1,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
-- 2. Chemical Peel (Optional upgrade)
(
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    'service',
    '0d0e0459-402b-4519-848b-e47cb500ef93',
    'Chemical Peel',
    1.00,
    'session',
    'conditional',
    1200.00,
    1200.00,
    TRUE,
    'Optional - can be added based on skin assessment',
    2,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Medicine/Consumable Items
INSERT INTO package_bom_items (
    bom_item_id, package_id, item_type, item_id, item_name,
    quantity, unit_of_measure, supply_method, current_price, line_total,
    is_optional, notes, display_sequence, hospital_id
) VALUES
-- 3. Clotrimazole Cream (per session)
(
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    'medicine',
    '97344f81-ce11-4f7d-85b0-2ec852129a5d',
    'Clotrimazole Cream 1% 20g',
    1.00,
    'tube',
    'per_session',
    45.00,
    45.00,
    FALSE,
    'Applied during each facial session',
    3,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
-- 4. Multivitamin Tablets (for entire package)
(
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    'medicine',
    '427f7800-6253-4065-bb01-1988f860bf41',
    'Multivitamin Tablets',
    30.00,
    'tablets',
    'per_package',
    150.00,
    150.00,
    FALSE,
    'One month supply - one tablet daily',
    4,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
),
-- 5. Paracetamol (on demand)
(
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    'medicine',
    '7056349f-b3fe-4ade-97ff-bdafe663088d',
    'Paracetamol 500mg',
    10.00,
    'tablets',
    'on_demand',
    5.00,
    50.00,
    TRUE,
    'Available if patient experiences discomfort',
    5,
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- ============================================
-- PACKAGE SESSION PLAN - Basic Facial Package
-- ============================================

-- Session 1: Initial Consultation & Assessment
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES (
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    1,
    'Initial Consultation & Skin Assessment',
    'Comprehensive skin analysis, medical history review, and treatment plan discussion',
    45,
    NULL,  -- First session, no gap
    '[
        {
            "resource_type": "doctor",
            "role": "Dermatologist",
            "duration_minutes": 30,
            "quantity": 1
        },
        {
            "resource_type": "nurse",
            "role": "Aesthetic Nurse",
            "duration_minutes": 15,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    1,
    'Book appointment during consultation hours (9 AM - 5 PM)',
    'Patient must complete registration and provide medical history',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Session 2: First Facial Treatment
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES (
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    2,
    'First Facial Treatment Session',
    'Deep cleansing, exfoliation, extraction, mask application, and moisturizing',
    60,
    3,  -- 3 days after initial consultation
    '[
        {
            "resource_type": "therapist",
            "role": "Facial Therapist",
            "duration_minutes": 60,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    2,
    'Allow 3-7 days gap after consultation for skin to stabilize',
    'Initial consultation must be completed',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Session 3: Second Facial Treatment
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES (
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    3,
    'Second Facial Treatment Session',
    'Follow-up treatment with focus on problem areas identified in first session',
    60,
    7,  -- 7 days gap
    '[
        {
            "resource_type": "therapist",
            "role": "Facial Therapist",
            "duration_minutes": 60,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    3,
    'Maintain 7-14 day gap between facial treatments',
    'First facial treatment must be completed',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Session 4: Third Facial Treatment
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES (
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    4,
    'Third Facial Treatment Session',
    'Advanced treatment with specialized serums and techniques',
    60,
    7,  -- 7 days gap
    '[
        {
            "resource_type": "therapist",
            "role": "Senior Facial Therapist",
            "duration_minutes": 60,
            "quantity": 1
        }
    ]'::jsonb,
    TRUE,
    4,
    'Maintain consistent 7-14 day gaps for optimal results',
    'Second facial treatment must be completed',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Session 5: Final Review & Maintenance Plan (Optional)
INSERT INTO package_session_plan (
    session_plan_id, package_id, session_number, session_name, session_description,
    estimated_duration_minutes, recommended_gap_days,
    resource_requirements,
    is_mandatory, sequence_order, scheduling_notes, prerequisites, hospital_id
) VALUES (
    gen_random_uuid(),
    '2867d1b3-a59b-4360-8e41-91d99bd31aa4',
    5,
    'Final Review & Maintenance Consultation',
    'Results assessment, before/after comparison, and ongoing care plan discussion',
    30,
    7,  -- 7 days after last treatment
    '[
        {
            "resource_type": "doctor",
            "role": "Dermatologist",
            "duration_minutes": 20,
            "quantity": 1
        },
        {
            "resource_type": "therapist",
            "role": "Facial Therapist",
            "duration_minutes": 10,
            "quantity": 1
        }
    ]'::jsonb,
    FALSE,  -- Optional session
    5,
    'Can be scheduled 7-14 days after final treatment. Optional but recommended.',
    'All treatment sessions must be completed',
    '4ef72e18-e65d-4766-b9eb-0308c42485ca'
);

-- Add comments for tracking
COMMENT ON TABLE package_bom_items IS 'Sample data added for Basic Facial Package - demonstrates service + medicine BOM';
COMMENT ON TABLE package_session_plan IS 'Sample data added for Basic Facial Package - demonstrates 5-session delivery plan with resource scheduling';
