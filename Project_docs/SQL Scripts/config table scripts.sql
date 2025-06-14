-- =====================================================================
-- Role-Based Branch Access Implementation - CLEAN DATABASE SCHEMA
-- PostgreSQL Script - No Complex Functions, Simple DDL Only
-- UUID-based Schema, Backward Compatible, Zero Disruption
-- CORRECTED: All is_default references removed
-- =====================================================================

-- =====================================================================
-- PHASE 1: CREATE CORE ENHANCED PERMISSION TABLE
-- =====================================================================

CREATE TABLE role_module_branch_access (
    access_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES role_master(role_id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES module_master(module_id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(branch_id) ON DELETE CASCADE,
    
    -- Branch access configuration
    branch_access_type VARCHAR(20) DEFAULT 'specific' NOT NULL,
    
    -- Standard permissions
    can_view BOOLEAN DEFAULT FALSE NOT NULL,
    can_add BOOLEAN DEFAULT FALSE NOT NULL,
    can_edit BOOLEAN DEFAULT FALSE NOT NULL,
    can_delete BOOLEAN DEFAULT FALSE NOT NULL,
    can_export BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Enhanced cross-branch permissions for executives
    can_view_cross_branch BOOLEAN DEFAULT FALSE NOT NULL,
    can_export_cross_branch BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Basic constraints only
    CONSTRAINT chk_branch_access_type CHECK (branch_access_type IN ('specific', 'all', 'reporting')),
    CONSTRAINT chk_cross_branch_logic CHECK (
        (branch_id IS NULL AND branch_access_type IN ('all', 'reporting')) OR
        (branch_id IS NOT NULL AND branch_access_type = 'specific')
    ),
    CONSTRAINT uq_role_module_branch UNIQUE (role_id, module_id, branch_id)
);

-- Create performance indexes
CREATE INDEX idx_role_module_branch_lookup ON role_module_branch_access (role_id, module_id, branch_id);
CREATE INDEX idx_branch_permissions ON role_module_branch_access (branch_id) WHERE branch_id IS NOT NULL;
CREATE INDEX idx_hospital_role_permissions ON role_module_branch_access (hospital_id, role_id);
CREATE INDEX idx_permission_search ON role_module_branch_access (hospital_id, role_id, module_id, can_view, can_edit);
CREATE INDEX idx_cross_branch_permissions ON role_module_branch_access (hospital_id, can_view_cross_branch, can_export_cross_branch) WHERE can_view_cross_branch = TRUE OR can_export_cross_branch = TRUE;

-- =====================================================================
-- PHASE 2: ADD MISSING COLUMNS TO EXISTING TABLES (SAFE ADDITIONS)
-- =====================================================================

-- Add hospital_id to module_master if not exists
ALTER TABLE module_master ADD COLUMN IF NOT EXISTS hospital_id UUID REFERENCES hospitals(hospital_id);
ALTER TABLE module_master ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- Add is_active to role_master if not exists  
ALTER TABLE role_master ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE NOT NULL;

-- Add hospital_id to role_module_access if not exists
ALTER TABLE role_module_access ADD COLUMN IF NOT EXISTS hospital_id UUID REFERENCES hospitals(hospital_id);

-- NOTE: The following tables ALREADY HAVE branch_id in master.py:
-- - suppliers (branch_id exists)
-- - staff (branch_id exists) 
-- - purchase_order_header (branch_id exists)
-- - supplier_invoice (branch_id exists)
-- - supplier_payment (branch_id exists)

-- Add branch_id ONLY to tables that don't have it in master.py:
ALTER TABLE invoice_header ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(branch_id);
ALTER TABLE medicines ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(branch_id);
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS branch_id UUID REFERENCES branches(branch_id);

-- =====================================================================
-- PHASE 3: CREATE PERFORMANCE INDEXES FOR EXISTING TABLES
-- =====================================================================

-- Module master indexes
CREATE INDEX IF NOT EXISTS idx_module_master_hospital ON module_master (hospital_id) WHERE hospital_id IS NOT NULL;

-- Role master indexes
CREATE INDEX IF NOT EXISTS idx_role_master_hospital_active ON role_master (hospital_id, is_active) WHERE is_active = TRUE;

-- Role module access indexes
CREATE INDEX IF NOT EXISTS idx_role_module_access_hospital ON role_module_access (hospital_id, role_id);

-- Invoice header indexes (NEW field)
CREATE INDEX IF NOT EXISTS idx_invoice_header_branch ON invoice_header (hospital_id, branch_id) WHERE branch_id IS NOT NULL;

-- Medicine indexes (NEW field)  
CREATE INDEX IF NOT EXISTS idx_medicines_branch ON medicines (hospital_id, branch_id, status) WHERE branch_id IS NOT NULL;

-- Inventory indexes (NEW field)
CREATE INDEX IF NOT EXISTS idx_inventory_branch ON inventory (hospital_id, branch_id, transaction_date) WHERE branch_id IS NOT NULL;

-- Users table optimization
CREATE INDEX IF NOT EXISTS idx_users_hospital_entity ON users (hospital_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_users_hospital_active ON users (hospital_id, is_active) WHERE is_active = TRUE;

-- Staff table optimization (branch_id ALREADY EXISTS in master.py)
CREATE INDEX IF NOT EXISTS idx_staff_hospital_branch_active ON staff (hospital_id, branch_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_staff_branch_lookup ON staff (branch_id, staff_id) WHERE branch_id IS NOT NULL;

-- Suppliers optimization (branch_id ALREADY EXISTS in master.py)
CREATE INDEX IF NOT EXISTS idx_suppliers_hospital_branch_status ON suppliers (hospital_id, branch_id, status);
CREATE INDEX IF NOT EXISTS idx_suppliers_search_optimized ON suppliers (hospital_id, status, supplier_name) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_suppliers_branch_status ON suppliers (branch_id, status) WHERE branch_id IS NOT NULL;

-- Patients optimization (branch_id ALREADY EXISTS in master.py)
CREATE INDEX IF NOT EXISTS idx_patients_hospital_branch ON patients (hospital_id, branch_id) WHERE branch_id IS NOT NULL;

-- Purchase Order Header optimization (branch_id ALREADY EXISTS in master.py)
CREATE INDEX IF NOT EXISTS idx_po_header_hospital_branch ON purchase_order_header (hospital_id, branch_id, status);
CREATE INDEX IF NOT EXISTS idx_po_header_branch_date ON purchase_order_header (branch_id, po_date) WHERE branch_id IS NOT NULL;

-- Supplier Invoice optimization (branch_id ALREADY EXISTS in master.py)
CREATE INDEX IF NOT EXISTS idx_supplier_invoice_hospital_branch ON supplier_invoice (hospital_id, branch_id, payment_status);
CREATE INDEX IF NOT EXISTS idx_supplier_invoice_branch_date ON supplier_invoice (branch_id, invoice_date) WHERE branch_id IS NOT NULL;

-- Supplier Payment optimization (branch_id ALREADY EXISTS in master.py)  
CREATE INDEX IF NOT EXISTS idx_supplier_payment_hospital_branch ON supplier_payment (hospital_id, branch_id, status);
CREATE INDEX IF NOT EXISTS idx_supplier_payment_branch_date ON supplier_payment (branch_id, payment_date) WHERE branch_id IS NOT NULL;

-- User Role Mapping optimization
CREATE INDEX IF NOT EXISTS idx_user_role_mapping_active ON user_role_mapping (user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_role_mapping_role ON user_role_mapping (role_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_role_mapping_lookup ON user_role_mapping (user_id, role_id, is_active);

-- Enhanced branch table indexes
CREATE INDEX IF NOT EXISTS idx_branches_hospital_active ON branches (hospital_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_branches_name_search ON branches (hospital_id, name) WHERE is_active = TRUE;

-- =====================================================================
-- PHASE 4: CREATE DEFAULT BRANCHES FOR HOSPITALS
-- =====================================================================

-- Create default branches for hospitals that don't have any
INSERT INTO branches (branch_id, hospital_id, name, is_active, created_at, updated_at)
SELECT 
    gen_random_uuid(),
    h.hospital_id,
    'Main Branch',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
FROM hospitals h
WHERE NOT EXISTS (
    SELECT 1 FROM branches b WHERE b.hospital_id = h.hospital_id
)
AND h.is_active = true;

-- =====================================================================
-- PHASE 5: POPULATE HOSPITAL_ID IN ROLE_MODULE_ACCESS (IF NEEDED)
-- =====================================================================

-- Update role_module_access with hospital_id from role_master (where null)
UPDATE role_module_access 
SET hospital_id = (
    SELECT rm.hospital_id 
    FROM role_master rm 
    WHERE rm.role_id = role_module_access.role_id
)
WHERE hospital_id IS NULL;

-- =====================================================================
-- PHASE 6: UPDATE EXISTING RECORDS WITH DEFAULT BRANCH ASSIGNMENTS
-- =====================================================================

-- Update invoice_header with default branch (NEW field)
UPDATE invoice_header 
SET branch_id = (
    SELECT b.branch_id 
    FROM branches b 
    WHERE b.hospital_id = invoice_header.hospital_id 
    AND b.name ILIKE '%main%'
    ORDER BY b.created_at ASC
    LIMIT 1
)
WHERE branch_id IS NULL;

-- Update medicines with default branch (NEW field)
UPDATE medicines 
SET branch_id = (
    SELECT b.branch_id 
    FROM branches b 
    WHERE b.hospital_id = medicines.hospital_id 
    AND b.name ILIKE '%main%'
    ORDER BY b.created_at ASC
    LIMIT 1
)
WHERE branch_id IS NULL;

-- Update inventory with default branch (NEW field)
UPDATE inventory 
SET branch_id = (
    SELECT b.branch_id 
    FROM branches b 
    WHERE b.hospital_id = inventory.hospital_id 
    AND b.name ILIKE '%main%'
    ORDER BY b.created_at ASC
    LIMIT 1
)
WHERE branch_id IS NULL;

-- =====================================================================
-- PHASE 7: ADD TABLE COMMENTS FOR DOCUMENTATION
-- =====================================================================

COMMENT ON TABLE role_module_branch_access IS 'Enhanced permission table supporting branch-level access control';
COMMENT ON COLUMN role_module_branch_access.branch_access_type IS 'Branch access type: specific, all, reporting';
COMMENT ON COLUMN role_module_branch_access.can_view_cross_branch IS 'Executive permission to view data across all branches';
COMMENT ON COLUMN role_module_branch_access.can_export_cross_branch IS 'Executive permission to export data across all branches';

-- =====================================================================
-- PHASE 8: VERIFICATION QUERIES
-- =====================================================================

-- Verify table creation
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'role_module_branch_access' 
ORDER BY ordinal_position;

-- Check default branches created
SELECT 
    h.name as hospital_name,
    COUNT(b.branch_id) as branch_count,
    STRING_AGG(b.name, ', ') as branch_names
FROM hospitals h
LEFT JOIN branches b ON h.hospital_id = b.hospital_id
WHERE h.is_active = true
GROUP BY h.hospital_id, h.name
ORDER BY h.name;

-- Final deployment summary
SELECT 
    'BRANCH ACCESS SCHEMA DEPLOYMENT' as status,
    'SUCCESS - CLEAN VERSION' as result,
    NOW() as completed_at;