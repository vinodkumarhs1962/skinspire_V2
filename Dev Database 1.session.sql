-- =====================================================================
-- Role-Based Branch Access Implementation - REVISED DATABASE SCHEMA
-- PostgreSQL Script - FULLY ALIGNED WITH IMPLEMENTATION DOCUMENT
-- UUID-based Schema, Backward Compatible, Zero Disruption
-- =====================================================================

-- =====================================================================
-- PHASE 0: FOUNDATION - CORE ENHANCED PERMISSION TABLE
-- Exactly as specified in Branch Implementation Document
-- =====================================================================

-- Create the enhanced role-module-branch access table
-- ALIGNED: UUID usage, exact constraint names from implementation document
CREATE TABLE role_module_branch_access (
    access_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES role_master(role_id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES module_master(module_id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(branch_id) ON DELETE CASCADE,
    
    -- Branch access configuration (as per implementation document)
    branch_access_type VARCHAR(20) DEFAULT 'specific' NOT NULL,
    
    -- Standard permissions (matching existing RoleModuleAccess structure)
    can_view BOOLEAN DEFAULT FALSE NOT NULL,
    can_add BOOLEAN DEFAULT FALSE NOT NULL,
    can_edit BOOLEAN DEFAULT FALSE NOT NULL,
    can_delete BOOLEAN DEFAULT FALSE NOT NULL,
    can_export BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Enhanced cross-branch permissions for CEO/CFO roles (implementation document requirement)
    can_view_cross_branch BOOLEAN DEFAULT FALSE NOT NULL,
    can_export_cross_branch BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Audit fields (implementation document standard)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- IMPLEMENTATION DOCUMENT CONSTRAINTS: Hospital isolation and validation
    CONSTRAINT chk_branch_access_type CHECK (branch_access_type IN ('specific', 'all', 'reporting')),
    CONSTRAINT chk_cross_branch_logic CHECK (
        (branch_id IS NULL AND branch_access_type IN ('all', 'reporting')) OR
        (branch_id IS NOT NULL AND branch_access_type = 'specific')
    ),
    CONSTRAINT uq_role_module_branch UNIQUE (role_id, module_id, branch_id)
    
    -- NOTE: Hospital validation implemented via triggers instead of CHECK constraints
    -- PostgreSQL doesn't allow subqueries in CHECK constraints
);

-- IMPLEMENTATION DOCUMENT: Performance indexes for permission checks
CREATE INDEX idx_role_module_branch_lookup ON role_module_branch_access (role_id, module_id, branch_id);
CREATE INDEX idx_branch_permissions ON role_module_branch_access (branch_id) WHERE branch_id IS NOT NULL;
CREATE INDEX idx_hospital_role_permissions ON role_module_branch_access (hospital_id, role_id);
CREATE INDEX idx_permission_search ON role_module_branch_access (hospital_id, role_id, module_id, can_view, can_edit);
CREATE INDEX idx_cross_branch_permissions ON role_module_branch_access (hospital_id, can_view_cross_branch, can_export_cross_branch) WHERE can_view_cross_branch = TRUE OR can_export_cross_branch = TRUE;

-- SECURITY: Hospital validation triggers (replaces CHECK constraints with subqueries)
-- These provide the same security validation as CHECK constraints but work with PostgreSQL
CREATE OR REPLACE FUNCTION validate_hospital_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate role belongs to same hospital
    IF NOT EXISTS (
        SELECT 1 FROM role_master 
        WHERE role_id = NEW.role_id 
        AND hospital_id = NEW.hospital_id
    ) THEN
        RAISE EXCEPTION 'Role % does not belong to hospital %', NEW.role_id, NEW.hospital_id;
    END IF;
    
    -- Validate module belongs to same hospital (or is global)
    IF NEW.module_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM module_master 
        WHERE module_id = NEW.module_id 
        AND (hospital_id = NEW.hospital_id OR hospital_id IS NULL)
    ) THEN
        RAISE EXCEPTION 'Module % does not belong to hospital %', NEW.module_id, NEW.hospital_id;
    END IF;
    
    -- Validate branch belongs to same hospital
    IF NEW.branch_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM branches 
        WHERE branch_id = NEW.branch_id 
        AND hospital_id = NEW.hospital_id
    ) THEN
        RAISE EXCEPTION 'Branch % does not belong to hospital %', NEW.branch_id, NEW.hospital_id;
    END IF;
    
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- Create triggers for hospital validation
CREATE TRIGGER tr_role_module_branch_access_hospital_validation
    BEFORE INSERT OR UPDATE ON role_module_branch_access
    FOR EACH ROW
    EXECUTE FUNCTION validate_hospital_consistency();

-- =====================================================================
-- PHASE 1: BACKWARD COMPATIBLE ENHANCEMENTS TO EXISTING TABLES
-- Add hospital_id to existing config tables for proper scoping
-- =====================================================================

-- Enhance module_master with hospital scoping (BACKWARD COMPATIBLE)
DO $$ 
BEGIN
    -- Add hospital_id if not exists (for proper scoping)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'module_master' AND column_name = 'hospital_id') THEN
        ALTER TABLE module_master 
        ADD COLUMN hospital_id UUID REFERENCES hospitals(hospital_id);
        
        -- Create index for performance
        CREATE INDEX idx_module_master_hospital ON module_master (hospital_id) WHERE hospital_id IS NOT NULL;
    END IF;
    
    -- Add is_active if not exists (standardization)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'module_master' AND column_name = 'is_active') THEN
        ALTER TABLE module_master 
        ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
END $$;

-- Enhance role_master with hospital scoping validation (BACKWARD COMPATIBLE)
DO $$ 
BEGIN
    -- Ensure hospital_id exists and is NOT NULL
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'role_master' AND column_name = 'hospital_id' AND is_nullable = 'YES') THEN
        -- Make hospital_id NOT NULL if it exists but is nullable
        ALTER TABLE role_master ALTER COLUMN hospital_id SET NOT NULL;
    END IF;
    
    -- Add is_active if not exists (standardization)  
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'role_master' AND column_name = 'is_active') THEN
        ALTER TABLE role_master 
        ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL;
    END IF;
END $$;

-- Enhance role_module_access with hospital scoping (BACKWARD COMPATIBLE)
DO $$ 
BEGIN
    -- Add hospital_id for proper scoping if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'role_module_access' AND column_name = 'hospital_id') THEN
        ALTER TABLE role_module_access 
        ADD COLUMN hospital_id UUID REFERENCES hospitals(hospital_id);
        
        -- Populate hospital_id from role_master
        UPDATE role_module_access 
        SET hospital_id = (
            SELECT rm.hospital_id 
            FROM role_master rm 
            WHERE rm.role_id = role_module_access.role_id
        );
        
        -- Make it NOT NULL after population
        ALTER TABLE role_module_access ALTER COLUMN hospital_id SET NOT NULL;
        
        -- Create index for performance
        CREATE INDEX idx_role_module_access_hospital ON role_module_access (hospital_id, role_id);
    END IF;
END $$;

-- =====================================================================
-- PHASE 2: ADD MISSING BRANCH_ID FIELDS (AS PER IMPLEMENTATION DOCUMENT)
-- Only add where specified in implementation document
-- =====================================================================

-- Add branch_id to invoice_header (if not already exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'invoice_header' AND column_name = 'branch_id') THEN
        ALTER TABLE invoice_header 
        ADD COLUMN branch_id UUID REFERENCES branches(branch_id);
        
        -- Add index for performance
        CREATE INDEX idx_invoice_header_branch ON invoice_header (hospital_id, branch_id) WHERE branch_id IS NOT NULL;
    END IF;
END $$;

-- Add branch_id to medicines (if not already exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'medicines' AND column_name = 'branch_id') THEN
        ALTER TABLE medicines 
        ADD COLUMN branch_id UUID REFERENCES branches(branch_id);
        
        -- Add index for performance
        CREATE INDEX idx_medicines_branch ON medicines (hospital_id, branch_id, status) WHERE branch_id IS NOT NULL;
    END IF;
END $$;

-- Add branch_id to inventory (if not already exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'inventory' AND column_name = 'branch_id') THEN
        ALTER TABLE inventory 
        ADD COLUMN branch_id UUID REFERENCES branches(branch_id);
        
        -- Add index for performance
        CREATE INDEX idx_inventory_branch ON inventory (hospital_id, branch_id, transaction_date) WHERE branch_id IS NOT NULL;
    END IF;
END $$;

-- =====================================================================
-- PHASE 3: CREATE DEFAULT BRANCHES (IMPLEMENTATION DOCUMENT REQUIREMENT)
-- Ensure all hospitals have at least one branch
-- =====================================================================

-- Create default branches for hospitals that don't have any
INSERT INTO branches (branch_id, hospital_id, name, is_active, is_default, branch_type)
SELECT 
    gen_random_uuid(),
    h.hospital_id,
    'Main Branch',
    true,
    true,
    'main'
FROM hospitals h
WHERE NOT EXISTS (
    SELECT 1 FROM branches b WHERE b.hospital_id = h.hospital_id
)
AND h.is_active = true;

-- Update existing records with default branch assignments
-- Invoice Header
UPDATE invoice_header 
SET branch_id = (
    SELECT b.branch_id 
    FROM branches b 
    WHERE b.hospital_id = invoice_header.hospital_id 
    AND (b.is_default = true OR b.name ILIKE '%main%')
    ORDER BY b.is_default DESC, b.created_at ASC
    LIMIT 1
)
WHERE branch_id IS NULL;

-- Medicines  
UPDATE medicines 
SET branch_id = (
    SELECT b.branch_id 
    FROM branches b 
    WHERE b.hospital_id = medicines.hospital_id 
    AND (b.is_default = true OR b.name ILIKE '%main%')
    ORDER BY b.is_default DESC, b.created_at ASC
    LIMIT 1
)
WHERE branch_id IS NULL;

-- Inventory
UPDATE inventory 
SET branch_id = (
    SELECT b.branch_id 
    FROM branches b 
    WHERE b.hospital_id = inventory.hospital_id 
    AND (b.is_default = true OR b.name ILIKE '%main%')
    ORDER BY b.is_default DESC, b.created_at ASC
    LIMIT 1
)
WHERE branch_id IS NULL;

-- =====================================================================
-- PHASE 4: ENHANCED INDEXES FOR EXISTING TABLES (PERFORMANCE OPTIMIZATION)
-- Implementation document specified performance indexes
-- =====================================================================

-- Users table optimization for branch access
CREATE INDEX IF NOT EXISTS idx_users_hospital_entity ON users (hospital_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_users_hospital_active ON users (hospital_id, is_active) WHERE is_active = TRUE;

-- Staff table optimization for branch assignment
CREATE INDEX IF NOT EXISTS idx_staff_hospital_branch_active ON staff (hospital_id, branch_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_staff_branch_lookup ON staff (branch_id, staff_id) WHERE branch_id IS NOT NULL;

-- Suppliers optimization (already has branch_id based on supplier_views.py)
CREATE INDEX IF NOT EXISTS idx_suppliers_hospital_branch_status ON suppliers (hospital_id, branch_id, status);
CREATE INDEX IF NOT EXISTS idx_suppliers_search_optimized ON suppliers (hospital_id, status, supplier_name) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_suppliers_branch_active ON suppliers (branch_id, is_active) WHERE branch_id IS NOT NULL AND is_active = TRUE;

-- Patients optimization
CREATE INDEX IF NOT EXISTS idx_patients_hospital_branch_active ON patients (hospital_id, branch_id, is_active) WHERE is_active = TRUE;

-- Purchase Order Header optimization (already has branch_id)
CREATE INDEX IF NOT EXISTS idx_po_header_hospital_branch ON purchase_order_header (hospital_id, branch_id, status);
CREATE INDEX IF NOT EXISTS idx_po_header_branch_date ON purchase_order_header (branch_id, po_date) WHERE branch_id IS NOT NULL;

-- Supplier Invoice optimization (already has branch_id)
CREATE INDEX IF NOT EXISTS idx_supplier_invoice_hospital_branch ON supplier_invoice (hospital_id, branch_id, payment_status);
CREATE INDEX IF NOT EXISTS idx_supplier_invoice_branch_date ON supplier_invoice (branch_id, invoice_date) WHERE branch_id IS NOT NULL;

-- Supplier Payment optimization (already has branch_id)
CREATE INDEX IF NOT EXISTS idx_supplier_payment_hospital_branch ON supplier_payment (hospital_id, branch_id, status);
CREATE INDEX IF NOT EXISTS idx_supplier_payment_branch_date ON supplier_payment (branch_id, payment_date) WHERE branch_id IS NOT NULL;

-- =====================================================================
-- PHASE 5: ROLE AND USER MANAGEMENT OPTIMIZATION
-- Implementation document performance requirements
-- =====================================================================

-- User Role Mapping optimization
CREATE INDEX IF NOT EXISTS idx_user_role_mapping_active ON user_role_mapping (user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_role_mapping_role ON user_role_mapping (role_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_role_mapping_lookup ON user_role_mapping (user_id, role_id, is_active);

-- Role Master optimization
CREATE INDEX IF NOT EXISTS idx_role_master_hospital_active ON role_master (hospital_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_role_master_name_search ON role_master (hospital_id, role_name) WHERE is_active = TRUE;

-- =====================================================================
-- PHASE 6: BRANCH MANAGEMENT OPTIMIZATION
-- Implementation document branch access requirements
-- =====================================================================

-- Enhanced branch table indexes
CREATE INDEX IF NOT EXISTS idx_branches_hospital_active ON branches (hospital_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_branches_name_search ON branches (hospital_id, name) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_branches_default ON branches (hospital_id, is_default) WHERE is_default = TRUE;
CREATE INDEX IF NOT EXISTS idx_branches_type ON branches (hospital_id, branch_type, is_active);

-- =====================================================================
-- PHASE 7: UTILITY FUNCTIONS (IMPLEMENTATION DOCUMENT REQUIREMENTS)
-- Testing bypass preservation and permission checking functions
-- =====================================================================

-- Function to get user's accessible branches (implementation document requirement)
CREATE OR REPLACE FUNCTION get_user_accessible_branches(
    p_user_id VARCHAR(15),
    p_hospital_id UUID
) RETURNS TABLE (
    branch_id UUID,
    branch_name VARCHAR(100),
    has_all_access BOOLEAN,
    is_default BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        b.branch_id,
        b.name as branch_name,
        (rmba.branch_id IS NULL) as has_all_access,
        COALESCE(b.is_default, FALSE) as is_default
    FROM branches b
    LEFT JOIN role_module_branch_access rmba ON (
        rmba.branch_id = b.branch_id OR rmba.branch_id IS NULL
    )
    LEFT JOIN user_role_mapping urm ON rmba.role_id = urm.role_id
    WHERE b.hospital_id = p_hospital_id
    AND b.is_active = TRUE
    AND urm.user_id = p_user_id
    AND urm.is_active = TRUE
    AND rmba.can_view = TRUE
    ORDER BY is_default DESC, has_all_access DESC, branch_name;
END;
$$ LANGUAGE plpgsql;

-- Function to check branch permission (implementation document requirement)
-- CRITICAL: Preserves user 77777777 testing bypass
CREATE OR REPLACE FUNCTION has_branch_permission(
    p_user_id VARCHAR(15),
    p_hospital_id UUID,
    p_module_name VARCHAR(50),
    p_permission_type VARCHAR(20),
    p_branch_id UUID DEFAULT NULL
) RETURNS BOOLEAN AS $$
DECLARE
    v_has_permission BOOLEAN := FALSE;
    v_permission_column VARCHAR(50);
BEGIN
    -- IMPLEMENTATION DOCUMENT REQUIREMENT: Testing bypass for user 77777777
    IF p_user_id = '7777777777' THEN
        RETURN TRUE;
    END IF;
    
    -- Construct permission column name
    v_permission_column := 'can_' || p_permission_type;
    
    -- Check permission using role_module_branch_access
    EXECUTE format('
        SELECT COALESCE(bool_or(rmba.%I), FALSE)
        FROM role_module_branch_access rmba
        JOIN user_role_mapping urm ON rmba.role_id = urm.role_id
        JOIN module_master mm ON rmba.module_id = mm.module_id
        WHERE urm.user_id = $1
        AND urm.is_active = TRUE
        AND rmba.hospital_id = $2
        AND mm.module_name = $3
        AND (rmba.branch_id = $4 OR rmba.branch_id IS NULL)
    ', v_permission_column)
    INTO v_has_permission
    USING p_user_id, p_hospital_id, p_module_name, p_branch_id;
    
    RETURN COALESCE(v_has_permission, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Function to migrate legacy permissions (implementation document migration)
CREATE OR REPLACE FUNCTION migrate_legacy_permissions_to_branch_aware(
    p_hospital_id UUID
) RETURNS INTEGER AS $$
DECLARE
    v_migrated_count INTEGER := 0;
    v_legacy_perm RECORD;
    v_default_branch_id UUID;
BEGIN
    -- Get default branch for hospital
    SELECT branch_id INTO v_default_branch_id
    FROM branches 
    WHERE hospital_id = p_hospital_id 
    AND (is_default = TRUE OR name ILIKE '%main%')
    ORDER BY is_default DESC, created_at ASC
    LIMIT 1;
    
    -- Migrate each legacy permission
    FOR v_legacy_perm IN 
        SELECT rma.*, rm.role_name
        FROM role_module_access rma
        JOIN role_master rm ON rma.role_id = rm.role_id
        WHERE rma.hospital_id = p_hospital_id
    LOOP
        -- Check if already migrated
        IF NOT EXISTS (
            SELECT 1 FROM role_module_branch_access 
            WHERE role_id = v_legacy_perm.role_id 
            AND module_id = v_legacy_perm.module_id
            AND hospital_id = p_hospital_id
        ) THEN
            -- Create branch-aware permission (all-branch for admin roles, specific for others)
            INSERT INTO role_module_branch_access (
                hospital_id, role_id, module_id, branch_id, branch_access_type,
                can_view, can_add, can_edit, can_delete, can_export,
                can_view_cross_branch, can_export_cross_branch
            ) VALUES (
                p_hospital_id,
                v_legacy_perm.role_id,
                v_legacy_perm.module_id,
                CASE 
                    WHEN v_legacy_perm.role_name ILIKE '%admin%' OR v_legacy_perm.role_name ILIKE '%owner%' 
                    THEN NULL  -- All branches
                    ELSE v_default_branch_id  -- Specific branch
                END,
                CASE 
                    WHEN v_legacy_perm.role_name ILIKE '%admin%' OR v_legacy_perm.role_name ILIKE '%owner%' 
                    THEN 'all'  -- All branch access
                    ELSE 'specific'  -- Specific branch access
                END,
                v_legacy_perm.can_view,
                v_legacy_perm.can_add,
                v_legacy_perm.can_edit,
                v_legacy_perm.can_delete,
                v_legacy_perm.can_export,
                CASE 
                    WHEN v_legacy_perm.role_name ILIKE '%admin%' OR v_legacy_perm.role_name ILIKE '%owner%' 
                    THEN v_legacy_perm.can_view  -- Cross-branch view for admins
                    ELSE FALSE
                END,
                CASE 
                    WHEN v_legacy_perm.role_name ILIKE '%admin%' OR v_legacy_perm.role_name ILIKE '%owner%' 
                    THEN v_legacy_perm.can_export  -- Cross-branch export for admins
                    ELSE FALSE
                END
            );
            
            v_migrated_count := v_migrated_count + 1;
        END IF;
    END LOOP;
    
    RETURN v_migrated_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- PHASE 8: VALIDATION AND VERIFICATION QUERIES
-- Implementation document verification requirements
-- =====================================================================

-- Verify table creation and structure
DO $$
DECLARE
    v_table_exists BOOLEAN;
    v_constraint_count INTEGER;
    v_index_count INTEGER;
BEGIN
    -- Check if main table exists
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'role_module_branch_access'
    ) INTO v_table_exists;
    
    IF NOT v_table_exists THEN
        RAISE EXCEPTION 'role_module_branch_access table was not created successfully';
    END IF;
    
    -- Check constraints
    SELECT COUNT(*) INTO v_constraint_count
    FROM information_schema.table_constraints 
    WHERE table_name = 'role_module_branch_access';
    
    IF v_constraint_count < 5 THEN
        RAISE EXCEPTION 'Required constraints not created. Found: %, Expected: >= 5', v_constraint_count;
    END IF;
    
    -- Check indexes
    SELECT COUNT(*) INTO v_index_count
    FROM pg_indexes 
    WHERE tablename = 'role_module_branch_access';
    
    IF v_index_count < 5 THEN
        RAISE EXCEPTION 'Required indexes not created. Found: %, Expected: >= 5', v_index_count;
    END IF;
    
    RAISE NOTICE 'Implementation Document Schema Creation: SUCCESS';
    RAISE NOTICE 'Table: role_module_branch_access created with % constraints and % indexes', v_constraint_count, v_index_count;
END $$;

-- =====================================================================
-- PHASE 9: COMMENTS AND DOCUMENTATION
-- Implementation document compliance documentation
-- =====================================================================

-- Table comments
COMMENT ON TABLE role_module_branch_access IS 'Enhanced permission table supporting branch-level access control - Implementation Document Compliant';
COMMENT ON COLUMN role_module_branch_access.branch_access_type IS 'Branch access type: specific (single branch), all (all branches), reporting (view-only all branches)';
COMMENT ON COLUMN role_module_branch_access.can_view_cross_branch IS 'Executive permission to view data across all branches (CEO/CFO roles)';
COMMENT ON COLUMN role_module_branch_access.can_export_cross_branch IS 'Executive permission to export data across all branches (CEO/CFO roles)';

-- Index comments
COMMENT ON INDEX idx_role_module_branch_lookup IS 'Primary lookup index for permission checks - Implementation Document Performance Requirement';
COMMENT ON INDEX idx_cross_branch_permissions IS 'Index for cross-branch reporting queries by executives - Implementation Document Executive Access';

-- Function comments
COMMENT ON FUNCTION has_branch_permission IS 'Branch permission check with user 77777777 testing bypass - Implementation Document Requirement';
COMMENT ON FUNCTION get_user_accessible_branches IS 'Get user accessible branches - Implementation Document Service Layer Support';
COMMENT ON FUNCTION migrate_legacy_permissions_to_branch_aware IS 'Migration utility for existing permissions - Implementation Document Migration Support';

-- =====================================================================
-- FINAL VERIFICATION AND SUMMARY
-- =====================================================================

-- Summary report
SELECT 
    'IMPLEMENTATION DOCUMENT SCHEMA DEPLOYMENT' as status,
    'SUCCESS' as result,
    NOW() as completed_at;

-- Verification checklist
SELECT 
    'role_module_branch_access' as component,
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'role_module_branch_access') 
         THEN 'CREATED' ELSE 'MISSING' END as status
UNION ALL
SELECT 
    'Testing Bypass Function',
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_name = 'has_branch_permission') 
         THEN 'CREATED' ELSE 'MISSING' END
UNION ALL
SELECT 
    'Migration Function',
    CASE WHEN EXISTS (SELECT 1 FROM information_schema.routines WHERE routine_name = 'migrate_legacy_permissions_to_branch_aware') 
         THEN 'CREATED' ELSE 'MISSING' END
UNION ALL
SELECT 
    'Performance Indexes',
    CASE WHEN (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'role_module_branch_access') >= 5 
         THEN 'CREATED' ELSE 'INSUFFICIENT' END;

-- Display next steps
SELECT 
    'NEXT STEPS' as phase,
    'Run migration function for each hospital' as step_1,
    'Enable SUPPLIER_BRANCH_ROLES=true for Phase 1' as step_2,
    'Update service layer with branch permission functions' as step_3,
    'Test with user 77777777 bypass verification' as step_4;