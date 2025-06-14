-- SQL Script to grant full access to user 7777777777

-- First, set the hospital_id for our operations
-- Replace 'YOUR-HOSPITAL-UUID' with your actual hospital UUID
DO $$ 
DECLARE
    hospital_uuid UUID;
    super_admin_role_id INTEGER;
    module_count INTEGER;
BEGIN
    -- Get the hospital_id for user 7777777777
    SELECT hospital_id INTO hospital_uuid 
    FROM users 
    WHERE user_id = '7777777777';
    
    IF hospital_uuid IS NULL THEN
        RAISE EXCEPTION 'User 7777777777 not found or has no hospital_id';
    END IF;
    
    -- 1. Create a Super Admin role if it doesn't exist
    SELECT role_id INTO super_admin_role_id 
    FROM role_master 
    WHERE role_name = 'Super Admin' AND hospital_id = hospital_uuid;
    
    IF super_admin_role_id IS NULL THEN
        -- Find the next available role_id
        SELECT COALESCE(MAX(role_id), 0) + 1 INTO super_admin_role_id FROM role_master;
        
        INSERT INTO role_master (
            role_id,
            hospital_id, 
            role_name, 
            description, 
            is_system_role, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            super_admin_role_id,
            hospital_uuid,
            'Super Admin',
            'Role with full system access',
            TRUE,
            'active',
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'Created Super Admin role with ID: %', super_admin_role_id;
    ELSE
        RAISE NOTICE 'Super Admin role already exists with ID: %', super_admin_role_id;
    END IF;
    
    -- 2. Assign the role to user 7777777777 if not already assigned
    IF NOT EXISTS (
        SELECT 1 FROM user_role_mapping 
        WHERE user_id = '7777777777' AND role_id = super_admin_role_id
    ) THEN
        INSERT INTO user_role_mapping (
            user_id,
            role_id,
            is_active,
            created_at,
            updated_at
        ) VALUES (
            '7777777777',
            super_admin_role_id,
            TRUE,
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'Assigned Super Admin role to user 7777777777';
    ELSE
        RAISE NOTICE 'User 7777777777 already has Super Admin role';
    END IF;
    
    -- 3. Count how many modules exist
    SELECT COUNT(*) INTO module_count FROM module_master;
    
    -- 4. Give the Super Admin role access to all modules
    IF module_count > 0 THEN
        -- First, delete any existing access records to avoid duplicates
        DELETE FROM role_module_access 
        WHERE role_id = super_admin_role_id;
        
        -- Insert new access records for all modules
        INSERT INTO role_module_access (
            role_id,
            module_id,
            can_view,
            can_add,
            can_edit,
            can_delete,
            can_export,
            created_at,
            updated_at
        )
        SELECT 
            super_admin_role_id,
            module_id,
            TRUE,  -- can_view
            TRUE,  -- can_add
            TRUE,  -- can_edit
            TRUE,  -- can_delete
            TRUE,  -- can_export
            NOW(), -- created_at
            NOW()  -- updated_at
        FROM module_master;
        
        RAISE NOTICE 'Granted full access to all % modules for Super Admin role', module_count;
    ELSE
        RAISE NOTICE 'No modules found in the system';
        
        -- If no modules exist yet, let's create some basic ones
        
        -- Start with a clean module_id sequence
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            1,
            'Dashboard',
            'Main dashboard',
            1,
            'home',
            'auth_views.dashboard',
            'active',
            NOW(),
            NOW()
        );
        
        -- Administration parent module
        WITH inserted_module AS (
            INSERT INTO module_master (
                module_id,
                module_name, 
                description, 
                sequence, 
                icon, 
                route, 
                status, 
                created_at, 
                updated_at
            ) VALUES (
                2,
                'Administration',
                'System administration',
                2,
                'cog',
                '#',
                'active',
                NOW(),
                NOW()
            )
            RETURNING module_id
        )
        -- User Management sub-module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            parent_module,
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) 
        SELECT
            3,
            'User Management',
            'Manage users',
            module_id,
            1,
            'users',
            'admin_views.users',
            'active',
            NOW(),
            NOW()
        FROM inserted_module;

        -- Now insert other main modules
        
        -- Billing module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            4,
            'Billing & Finance',
            'Billing and financial management',
            3,
            'document-text',
            '#',
            'active',
            NOW(),
            NOW()
        );
        
        -- Inventory module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            5,
            'Inventory',
            'Inventory management',
            4,
            'cube',
            '#',
            'active',
            NOW(),
            NOW()
        );
        
        -- Suppliers module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            6,
            'Suppliers',
            'Supplier management',
            5,
            'truck',
            '#',
            'active',
            NOW(),
            NOW()
        );
        
        -- Financial Reports module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            7,
            'Financial Reports',
            'Financial reporting',
            6,
            'cash',
            '#',
            'active',
            NOW(),
            NOW()
        );
        
        -- Patients module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            8,
            'Patients',
            'Patient management',
            7,
            'users',
            '#',
            'active',
            NOW(),
            NOW()
        );
        
        -- Appointments module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            9,
            'Appointments',
            'Appointment scheduling',
            8,
            'calendar',
            '#',
            'active',
            NOW(),
            NOW()
        );
        
        -- Settings module
        INSERT INTO module_master (
            module_id,
            module_name, 
            description, 
            sequence, 
            icon, 
            route, 
            status, 
            created_at, 
            updated_at
        ) VALUES (
            10,
            'Settings',
            'User settings',
            9,
            'settings',
            'auth_views.settings',
            'active',
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'Created basic module structure';
        
        -- Now assign permissions for all these new modules
        INSERT INTO role_module_access (
            role_id,
            module_id,
            can_view,
            can_add,
            can_edit,
            can_delete,
            can_export,
            created_at,
            updated_at
        )
        SELECT 
            super_admin_role_id,
            module_id,
            TRUE,  -- can_view
            TRUE,  -- can_add
            TRUE,  -- can_edit
            TRUE,  -- can_delete
            TRUE,  -- can_export
            NOW(), -- created_at
            NOW()  -- updated_at
        FROM module_master;
        
        RAISE NOTICE 'Granted full access to all newly created modules for Super Admin role';
    END IF;
    
END $$;

-- Verify the setup
SELECT 'User Role Assignment' AS check_type, 
       u.user_id, 
       r.role_name, 
       urm.is_active
FROM users u
JOIN user_role_mapping urm ON u.user_id = urm.user_id
JOIN role_master r ON urm.role_id = r.role_id
WHERE u.user_id = '7777777777';

SELECT 'Module Access' AS check_type,
       m.module_name,
       rma.can_view,
       rma.can_add,
       rma.can_edit,
       rma.can_delete,
       rma.can_export
FROM role_module_access rma
JOIN module_master m ON rma.module_id = m.module_id
JOIN role_master r ON rma.role_id = r.role_id
JOIN user_role_mapping urm ON r.role_id = urm.role_id
WHERE urm.user_id = '7777777777'
ORDER BY m.sequence;