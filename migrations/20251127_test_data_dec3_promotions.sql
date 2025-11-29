-- Test Data: Promotions and Loyalty Card starting Dec 3rd, 2025
-- For patient: Ram second Kumar (a6a8cbd7-17b1-42c2-b8a8-3ec1c4e894a6)
-- NOTE: Using correct table names (hospitals, patients, promotion_campaigns, loyalty_card_types)

DO $$
DECLARE
    v_hospital_id UUID;
    v_patient_id UUID := 'a6a8cbd7-17b1-42c2-b8a8-3ec1c4e894a6';
    v_gold_card_id UUID;
    v_silver_card_id UUID;
BEGIN
    -- Get hospital ID
    SELECT hospital_id INTO v_hospital_id FROM hospitals LIMIT 1;

    IF v_hospital_id IS NULL THEN
        RAISE EXCEPTION 'No hospital found in database';
    END IF;

    RAISE NOTICE 'Using hospital_id: %', v_hospital_id;

    -- =========================================================================
    -- CREATE LOYALTY CARD TYPES (if not exist)
    -- =========================================================================

    -- Check if Gold card type exists
    SELECT card_type_id INTO v_gold_card_id
    FROM loyalty_card_types
    WHERE hospital_id = v_hospital_id AND card_type_name = 'Gold Card' AND is_deleted = FALSE
    LIMIT 1;

    IF v_gold_card_id IS NULL THEN
        INSERT INTO loyalty_card_types (
            hospital_id, card_type_name, card_type_code, description,
            discount_percent, min_lifetime_spend, min_visits, card_color,
            is_active, is_deleted, created_at
        ) VALUES (
            v_hospital_id, 'Gold Card', 'GOLD', 'Gold loyalty card - 15% discount',
            15.00, 50000.00, 10, '#FFD700',
            TRUE, FALSE, NOW()
        )
        RETURNING card_type_id INTO v_gold_card_id;
        RAISE NOTICE 'Created Gold Card type with ID: %', v_gold_card_id;
    ELSE
        RAISE NOTICE 'Gold Card already exists with ID: %', v_gold_card_id;
    END IF;

    -- Check if Silver card type exists
    SELECT card_type_id INTO v_silver_card_id
    FROM loyalty_card_types
    WHERE hospital_id = v_hospital_id AND card_type_name = 'Silver Card' AND is_deleted = FALSE
    LIMIT 1;

    IF v_silver_card_id IS NULL THEN
        INSERT INTO loyalty_card_types (
            hospital_id, card_type_name, card_type_code, description,
            discount_percent, min_lifetime_spend, min_visits, card_color,
            is_active, is_deleted, created_at
        ) VALUES (
            v_hospital_id, 'Silver Card', 'SILVER', 'Silver loyalty card - 10% discount',
            10.00, 25000.00, 5, '#C0C0C0',
            TRUE, FALSE, NOW()
        )
        RETURNING card_type_id INTO v_silver_card_id;
        RAISE NOTICE 'Created Silver Card type with ID: %', v_silver_card_id;
    ELSE
        RAISE NOTICE 'Silver Card already exists with ID: %', v_silver_card_id;
    END IF;

    -- =========================================================================
    -- ASSIGN GOLD LOYALTY CARD TO RAM SECOND KUMAR (Starting Dec 3rd)
    -- =========================================================================

    -- Remove any existing loyalty wallet for this patient
    DELETE FROM patient_loyalty_wallet WHERE patient_id = v_patient_id;

    -- Create new loyalty wallet with Gold card starting Dec 3rd
    INSERT INTO patient_loyalty_wallet (
        patient_id, hospital_id, card_type_id, wallet_status,
        valid_from, valid_to, is_active, created_at
    ) VALUES (
        v_patient_id,
        v_hospital_id,
        v_gold_card_id,
        'active',
        '2025-12-03'::DATE,  -- Starts Dec 3rd
        '2026-12-03'::DATE,  -- Valid for 1 year
        TRUE,
        NOW()
    );

    RAISE NOTICE 'Created Gold loyalty card for Ram Second Kumar (valid from Dec 3, 2025)';

    -- =========================================================================
    -- CREATE PROMOTION CAMPAIGNS (Starting Dec 3rd)
    -- =========================================================================

    -- Campaign 1: Winter Special - 20% off all services (Dec 3 - Dec 31)
    INSERT INTO promotion_campaigns (
        hospital_id, campaign_code, campaign_name, description,
        promotion_type, discount_type, discount_value,
        start_date, end_date,
        is_active, is_personalized, auto_apply, applies_to,
        target_special_group, current_uses, is_deleted, created_at
    ) VALUES (
        v_hospital_id,
        'WINTER2025',
        'Winter Special 2025',
        'Get 20% off on all services this winter season',
        'simple_discount',
        'percentage',
        20.00,
        '2025-12-03'::DATE,
        '2025-12-31'::DATE,
        TRUE, FALSE, TRUE, 'services',
        FALSE, 0, FALSE, NOW()
    )
    ON CONFLICT (campaign_code) WHERE is_deleted = FALSE
    DO UPDATE SET
        start_date = '2025-12-03'::DATE,
        end_date = '2025-12-31'::DATE,
        is_active = TRUE;

    RAISE NOTICE 'Created/Updated WINTER2025 campaign (Dec 3-31)';

    -- Campaign 2: VIP Exclusive - 25% off for special group (Dec 3 - Jan 31)
    INSERT INTO promotion_campaigns (
        hospital_id, campaign_code, campaign_name, description,
        promotion_type, discount_type, discount_value,
        start_date, end_date,
        is_active, is_personalized, auto_apply, applies_to,
        target_special_group, current_uses, is_deleted, created_at
    ) VALUES (
        v_hospital_id,
        'VIP2025',
        'VIP Exclusive Offer',
        'Exclusive 25% discount for our VIP members',
        'simple_discount',
        'percentage',
        25.00,
        '2025-12-03'::DATE,
        '2026-01-31'::DATE,
        TRUE, FALSE, TRUE, 'all',
        TRUE, 0, FALSE, NOW()
    )
    ON CONFLICT (campaign_code) WHERE is_deleted = FALSE
    DO UPDATE SET
        start_date = '2025-12-03'::DATE,
        end_date = '2026-01-31'::DATE,
        is_active = TRUE,
        target_special_group = TRUE;

    RAISE NOTICE 'Created/Updated VIP2025 campaign (Dec 3 - Jan 31)';

    -- Campaign 3: New Year Medicine Discount (Dec 15 - Jan 15)
    INSERT INTO promotion_campaigns (
        hospital_id, campaign_code, campaign_name, description,
        promotion_type, discount_type, discount_value,
        start_date, end_date,
        is_active, is_personalized, auto_apply, applies_to,
        target_special_group, current_uses, is_deleted, created_at
    ) VALUES (
        v_hospital_id,
        'NEWYEAR2026',
        'New Year Medicine Sale',
        '15% off on all medicines for the new year',
        'simple_discount',
        'percentage',
        15.00,
        '2025-12-15'::DATE,
        '2026-01-15'::DATE,
        TRUE, FALSE, TRUE, 'medicines',
        FALSE, 0, FALSE, NOW()
    )
    ON CONFLICT (campaign_code) WHERE is_deleted = FALSE
    DO UPDATE SET
        start_date = '2025-12-15'::DATE,
        end_date = '2026-01-15'::DATE,
        is_active = TRUE;

    RAISE NOTICE 'Created/Updated NEWYEAR2026 campaign (Dec 15 - Jan 15)';

    -- Campaign 4: Package Promo (Dec 3 - Dec 20)
    INSERT INTO promotion_campaigns (
        hospital_id, campaign_code, campaign_name, description,
        promotion_type, discount_type, discount_value,
        start_date, end_date,
        is_active, is_personalized, auto_apply, applies_to,
        target_special_group, current_uses, is_deleted, created_at
    ) VALUES (
        v_hospital_id,
        'PKG2025',
        'Package Deal December',
        '10% off on all packages this December',
        'simple_discount',
        'percentage',
        10.00,
        '2025-12-03'::DATE,
        '2025-12-20'::DATE,
        TRUE, FALSE, TRUE, 'packages',
        FALSE, 0, FALSE, NOW()
    )
    ON CONFLICT (campaign_code) WHERE is_deleted = FALSE
    DO UPDATE SET
        start_date = '2025-12-03'::DATE,
        end_date = '2025-12-20'::DATE,
        is_active = TRUE;

    RAISE NOTICE 'Created/Updated PKG2025 campaign (Dec 3-20)';

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Test data created successfully!';
    RAISE NOTICE 'Patient: Ram Second Kumar';
    RAISE NOTICE 'Loyalty Card: Gold (15%%) - Valid from Dec 3, 2025';
    RAISE NOTICE 'Campaigns: WINTER2025, VIP2025, NEWYEAR2026, PKG2025';
    RAISE NOTICE '========================================';

END $$;

-- Verify the data
SELECT 'Loyalty Card Types' as section, card_type_name, discount_percent, is_active
FROM loyalty_card_types WHERE is_deleted = FALSE;

SELECT 'Patient Loyalty Wallet' as section, p.first_name, p.last_name, lct.card_type_name, plw.valid_from, plw.valid_to
FROM patient_loyalty_wallet plw
JOIN patients p ON p.patient_id = plw.patient_id
JOIN loyalty_card_types lct ON lct.card_type_id = plw.card_type_id
WHERE plw.patient_id = 'a6a8cbd7-17b1-42c2-b8a8-3ec1c4e894a6';

SELECT 'Promotion Campaigns' as section, campaign_code, campaign_name, start_date, end_date, target_special_group, is_active
FROM promotion_campaigns
WHERE is_deleted = FALSE
ORDER BY start_date;
