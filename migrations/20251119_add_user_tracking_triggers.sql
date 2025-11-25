-- Migration: Add User Tracking Triggers to Package Tables
-- Created: 2025-11-19
-- Description: Add track_user_changes trigger to automatically set created_by and updated_by

-- Add trigger to package_bom_items
DROP TRIGGER IF EXISTS track_user_changes ON package_bom_items;
CREATE TRIGGER track_user_changes
    BEFORE INSERT OR UPDATE ON package_bom_items
    FOR EACH ROW
    EXECUTE FUNCTION track_user_changes();

-- Add trigger to package_session_plan
DROP TRIGGER IF EXISTS track_user_changes ON package_session_plan;
CREATE TRIGGER track_user_changes
    BEFORE INSERT OR UPDATE ON package_session_plan
    FOR EACH ROW
    EXECUTE FUNCTION track_user_changes();

-- Add comments
COMMENT ON TRIGGER track_user_changes ON package_bom_items IS 'Automatically tracks created_by and updated_by from app.current_user session variable';
COMMENT ON TRIGGER track_user_changes ON package_session_plan IS 'Automatically tracks created_by and updated_by from app.current_user session variable';
