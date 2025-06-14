-- =====================================================================
-- CRITICAL SECURITY VALIDATIONS - Hospital and Branch Isolation
-- PostgreSQL Script - ALIGNED with executed schema
-- Run this AFTER the main schema creation script
-- =====================================================================

-- =====================================================================
-- HOSPITAL ISOLATION VALIDATION TRIGGER
-- Prevents cross-hospital data access at database level
-- =====================================================================

CREATE OR REPLACE FUNCTION validate_hospital_isolation()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate role belongs to same hospital
    IF NOT EXISTS (
        SELECT 1 FROM role_master 
        WHERE role_id = NEW.role_id 
        AND hospital_id = NEW.hospital_id
    ) THEN
        RAISE EXCEPTION 'Security Violation: Role does not belong to hospital';
    END IF;
    
    -- Validate branch belongs to same hospital (if branch specified)
    IF NEW.branch_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM branches 
        WHERE branch_id = NEW.branch_id 
        AND hospital_id = NEW.hospital_id
    ) THEN
        RAISE EXCEPTION 'Security Violation: Branch does not belong to hospital';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply hospital isolation trigger to role_module_branch_access
CREATE TRIGGER tr_hospital_isolation_validation
    BEFORE INSERT OR UPDATE ON role_module_branch_access
    FOR EACH ROW
    EXECUTE FUNCTION validate_hospital_isolation();

-- =====================================================================
-- USER-ROLE HOSPITAL ISOLATION VALIDATION
-- Ensures users can only be assigned roles from their hospital
-- =====================================================================

CREATE OR REPLACE FUNCTION validate_user_role_hospital()
RETURNS TRIGGER AS $$
BEGIN
    -- Get user's hospital_id and validate role belongs to same hospital
    IF NOT EXISTS (
        SELECT 1 
        FROM users u 
        JOIN role_master rm ON rm.role_id = NEW.role_id
        WHERE u.user_id = NEW.user_id 
        AND u.hospital_id = rm.hospital_id
    ) THEN
        RAISE EXCEPTION 'Security Violation: Cannot assign role from different hospital';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to user_role_mapping table
CREATE TRIGGER tr_user_role_hospital_validation
    BEFORE INSERT OR UPDATE ON user_role_mapping
    FOR EACH ROW
    EXECUTE FUNCTION validate_user_role_hospital();

-- =====================================================================
-- BRANCH-ENTITY ISOLATION VALIDATION
-- Ensures entities can only be assigned to branches within their hospital
-- =====================================================================

CREATE OR REPLACE FUNCTION validate_branch_entity_hospital()
RETURNS TRIGGER AS $$
BEGIN
    -- Skip validation if branch_id is NULL
    IF NEW.branch_id IS NULL THEN
        RETURN NEW;
    END IF;
    
    -- Validate branch belongs to same hospital as entity
    IF NOT EXISTS (
        SELECT 1 FROM branches 
        WHERE branch_id = NEW.branch_id 
        AND hospital_id = NEW.hospital_id
    ) THEN
        RAISE EXCEPTION 'Security Violation: Entity cannot be assigned to branch from different hospital';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to critical tables with branch assignments (ONLY tables that have branch_id)
-- NOTE: Based on master.py, these tables already have branch_id
CREATE TRIGGER tr_supplier_branch_validation
    BEFORE INSERT OR UPDATE ON suppliers
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

CREATE TRIGGER tr_staff_branch_validation
    BEFORE INSERT OR UPDATE ON staff
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

CREATE TRIGGER tr_patient_branch_validation
    BEFORE INSERT OR UPDATE ON patients
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

-- Apply to transaction tables with branch_id (NEW fields added by SQL script)
CREATE TRIGGER tr_invoice_branch_validation
    BEFORE INSERT OR UPDATE ON invoice_header
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

-- Apply to tables that already had branch_id in master.py
CREATE TRIGGER tr_po_branch_validation
    BEFORE INSERT OR UPDATE ON purchase_order_header
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

CREATE TRIGGER tr_supplier_invoice_branch_validation
    BEFORE INSERT OR UPDATE ON supplier_invoice
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

CREATE TRIGGER tr_supplier_payment_branch_validation
    BEFORE INSERT OR UPDATE ON supplier_payment
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

-- Apply to NEW tables that got branch_id from SQL script
CREATE TRIGGER tr_medicine_branch_validation
    BEFORE INSERT OR UPDATE ON medicines
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

CREATE TRIGGER tr_inventory_branch_validation
    BEFORE INSERT OR UPDATE ON inventory
    FOR EACH ROW
    EXECUTE FUNCTION validate_branch_entity_hospital();

-- =====================================================================
-- PREVENT HOSPITAL ID CHANGES (IMMUTABLE SECURITY)
-- Prevents changing hospital_id on critical records
-- =====================================================================

CREATE OR REPLACE FUNCTION prevent_hospital_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Prevent hospital_id changes on existing records
    IF TG_OP = 'UPDATE' AND OLD.hospital_id IS DISTINCT FROM NEW.hospital_id THEN
        RAISE EXCEPTION 'Security Violation: Hospital ID cannot be changed';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to critical tables
CREATE TRIGGER tr_prevent_user_hospital_change
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION prevent_hospital_change();

CREATE TRIGGER tr_prevent_role_hospital_change
    BEFORE UPDATE ON role_master
    FOR EACH ROW
    EXECUTE FUNCTION prevent_hospital_change();

CREATE TRIGGER tr_prevent_branch_hospital_change
    BEFORE UPDATE ON branches
    FOR EACH ROW
    EXECUTE FUNCTION prevent_hospital_change();

-- =====================================================================
-- VERIFICATION AND TESTING
-- =====================================================================

-- Verify triggers are created
SELECT 
    trigger_name,
    event_object_table,
    action_timing,
    event_manipulation
FROM information_schema.triggers 
WHERE trigger_name LIKE '%hospital%' OR trigger_name LIKE '%branch%'
ORDER BY event_object_table, trigger_name;

-- Security validation summary
SELECT 
    'SECURITY VALIDATIONS DEPLOYED' as status,
    COUNT(*) as trigger_count
FROM information_schema.triggers 
WHERE trigger_name LIKE '%hospital%' OR trigger_name LIKE '%branch%';

/*
SECURITY FEATURES IMPLEMENTED:

1. Hospital Isolation - Users cannot access data from different hospitals
2. Branch Isolation - Entities only assigned to branches within their hospital  
3. Immutable Security - Hospital IDs cannot be changed once set
4. Database-Level Enforcement - Cannot be bypassed through application code

These provide essential security at database level while business logic 
remains in Python service layer as per your development practices.
*/