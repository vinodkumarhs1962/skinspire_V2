-- Migration: Fix Package BOM and Session Plan Audit Fields
-- Created: 2025-11-19
-- Description: Change created_by and updated_by from UUID to VARCHAR(50) to match TimestampMixin

-- Fix package_bom_items
ALTER TABLE package_bom_items
    ALTER COLUMN created_by TYPE VARCHAR(50) USING created_by::VARCHAR,
    ALTER COLUMN updated_by TYPE VARCHAR(50) USING updated_by::VARCHAR;

-- Fix package_session_plan
ALTER TABLE package_session_plan
    ALTER COLUMN created_by TYPE VARCHAR(50) USING created_by::VARCHAR,
    ALTER COLUMN updated_by TYPE VARCHAR(50) USING updated_by::VARCHAR;

-- Add comments
COMMENT ON COLUMN package_bom_items.created_by IS 'User ID who created the record (phone number or identifier)';
COMMENT ON COLUMN package_bom_items.updated_by IS 'User ID who last updated the record (phone number or identifier)';
COMMENT ON COLUMN package_session_plan.created_by IS 'User ID who created the record (phone number or identifier)';
COMMENT ON COLUMN package_session_plan.updated_by IS 'User ID who last updated the record (phone number or identifier)';
