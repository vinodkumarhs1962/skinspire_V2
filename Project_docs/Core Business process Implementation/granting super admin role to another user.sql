DO $$ 
DECLARE
    hospital_uuid UUID;
    super_admin_role_id INTEGER;
BEGIN
    -- Get the hospital_id for the reference user
    SELECT hospital_id INTO hospital_uuid 
    FROM users 
    WHERE user_id = '7777777777';
    
    -- Find the Super Admin role ID
    SELECT role_id INTO super_admin_role_id 
    FROM role_master 
    WHERE role_name = 'Super Admin' AND hospital_id = hospital_uuid;
    
    IF super_admin_role_id IS NULL THEN
        RAISE EXCEPTION 'Super Admin role not found';
    END IF;
    
    -- Assign the role to the new user (replace '8888888888' with the actual user ID)
    IF NOT EXISTS (
        SELECT 1 FROM user_role_mapping 
        WHERE user_id = '8888888888' AND role_id = super_admin_role_id
    ) THEN
        INSERT INTO user_role_mapping (
            user_id,
            role_id,
            is_active,
            created_at,
            updated_at
        ) VALUES (
            '8888888888',
            super_admin_role_id,
            TRUE,
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'Assigned Super Admin role to user 8888888888';
    ELSE
        RAISE NOTICE 'User 8888888888 already has Super Admin role';
    END IF;
END $$;