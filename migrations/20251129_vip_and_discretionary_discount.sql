-- Migration: VIP Auto-Apply and Staff Discretionary Discount
-- Date: 2025-11-29
-- Description:
--   1. Add VIP configuration to hospital settings
--   2. Add Staff Discretionary Discount configuration

-- Note: We use existing is_special_group column in patients table for VIP eligibility
-- No need for new column

-- Check if billing settings exist for this hospital
DO $$
DECLARE
    existing_id UUID;
BEGIN
    SELECT setting_id INTO existing_id
    FROM hospital_settings
    WHERE hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'
    AND category = 'billing';

    IF existing_id IS NOT NULL THEN
        -- Update existing
        UPDATE hospital_settings
        SET settings = settings || '{
            "vip_discount": {
                "enabled": true,
                "campaign_code": "VIP2025",
                "auto_apply_default": false,
                "description": "VIP customers get special discount"
            },
            "staff_discretionary_discount": {
                "enabled": true,
                "code": "SKINSPIRESPECIAL",
                "name": "Staff Discretionary Discount",
                "max_percent": 5,
                "default_percent": 1,
                "options": [1, 2, 3, 4, 5],
                "requires_note": false,
                "stacking_mode": "incremental"
            }
        }'::jsonb,
        updated_at = NOW()
        WHERE setting_id = existing_id;
        RAISE NOTICE 'Updated existing billing settings';
    ELSE
        -- Insert new
        INSERT INTO hospital_settings (setting_id, hospital_id, category, settings, is_active, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            '4ef72e18-e65d-4766-b9eb-0308c42485ca',
            'billing',
            '{
                "vip_discount": {
                    "enabled": true,
                    "campaign_code": "VIP2025",
                    "auto_apply_default": false,
                    "description": "VIP customers get special discount"
                },
                "staff_discretionary_discount": {
                    "enabled": true,
                    "code": "SKINSPIRESPECIAL",
                    "name": "Staff Discretionary Discount",
                    "max_percent": 5,
                    "default_percent": 1,
                    "options": [1, 2, 3, 4, 5],
                    "requires_note": false,
                    "stacking_mode": "incremental"
                }
            }'::jsonb,
            true,
            NOW(),
            NOW()
        );
        RAISE NOTICE 'Inserted new billing settings';
    END IF;
END $$;

-- Verify the settings
SELECT hospital_id, category, settings->'vip_discount' as vip_discount,
       settings->'staff_discretionary_discount' as staff_discretionary
FROM hospital_settings
WHERE hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'
AND category = 'billing';
