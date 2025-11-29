-- Migration: Campaign Groups for Promotion Targeting
-- Date: 2025-11-28
-- Description: Adds Campaign Group entity to allow grouping of services, medicines,
--              and packages for easier campaign targeting. Items can belong to multiple groups.

-- =============================================================================
-- 1. CREATE CAMPAIGN GROUPS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS promotion_campaign_groups (
    group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    group_code VARCHAR(50) NOT NULL,
    group_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) REFERENCES users(user_id),
    updated_by VARCHAR(15) REFERENCES users(user_id),

    -- Unique constraint: group_code must be unique within a hospital
    CONSTRAINT uq_campaign_group_code UNIQUE (hospital_id, group_code)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_campaign_groups_hospital ON promotion_campaign_groups(hospital_id);
CREATE INDEX IF NOT EXISTS idx_campaign_groups_active ON promotion_campaign_groups(hospital_id, is_active);

-- Comment on table
COMMENT ON TABLE promotion_campaign_groups IS 'Campaign groups for organizing services, medicines, and packages into targetable collections';

-- =============================================================================
-- 2. CREATE GROUP ITEMS JUNCTION TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS promotion_group_items (
    group_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES promotion_campaign_groups(group_id) ON DELETE CASCADE,
    item_type VARCHAR(20) NOT NULL CHECK (item_type IN ('service', 'medicine', 'package')),
    item_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) REFERENCES users(user_id),

    -- Unique constraint: same item cannot be in same group twice
    CONSTRAINT uq_group_item UNIQUE (group_id, item_type, item_id)
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_group_items_group ON promotion_group_items(group_id);
CREATE INDEX IF NOT EXISTS idx_group_items_item ON promotion_group_items(item_type, item_id);

-- Comment on table
COMMENT ON TABLE promotion_group_items IS 'Junction table linking campaign groups to services, medicines, and packages';

-- =============================================================================
-- 3. ADD TARGET_GROUPS TO PROMOTION_CAMPAIGNS TABLE
-- =============================================================================
-- Add target_groups column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'promotion_campaigns'
        AND column_name = 'target_groups'
    ) THEN
        ALTER TABLE promotion_campaigns
        ADD COLUMN target_groups JSONB DEFAULT NULL;

        COMMENT ON COLUMN promotion_campaigns.target_groups IS
            'Array of group_ids that this campaign targets. Format: {"group_ids": ["uuid1", "uuid2"]}. NULL means use applies_to/specific_items logic.';
    END IF;
END $$;

-- Index for JSONB queries on target_groups
CREATE INDEX IF NOT EXISTS idx_campaigns_target_groups ON promotion_campaigns USING GIN (target_groups);

-- =============================================================================
-- 4. CREATE VIEW FOR EASY GROUP ITEM LOOKUP
-- =============================================================================
CREATE OR REPLACE VIEW v_campaign_group_items_detail AS
SELECT
    pgi.group_item_id,
    pgi.group_id,
    pcg.group_code,
    pcg.group_name,
    pcg.hospital_id,
    pgi.item_type,
    pgi.item_id,
    CASE
        WHEN pgi.item_type = 'service' THEN s.service_name
        WHEN pgi.item_type = 'medicine' THEN m.medicine_name
        WHEN pgi.item_type = 'package' THEN p.package_name
    END AS item_name,
    CASE
        WHEN pgi.item_type = 'service' THEN s.price
        WHEN pgi.item_type = 'medicine' THEN m.selling_price
        WHEN pgi.item_type = 'package' THEN p.price
    END AS item_price,
    CASE
        WHEN pgi.item_type = 'service' THEN s.is_active
        WHEN pgi.item_type = 'medicine' THEN (m.status = 'active')
        WHEN pgi.item_type = 'package' THEN (p.status = 'active')
    END AS item_is_active,
    pgi.created_at
FROM promotion_group_items pgi
JOIN promotion_campaign_groups pcg ON pgi.group_id = pcg.group_id
LEFT JOIN services s ON pgi.item_type = 'service' AND pgi.item_id = s.service_id
LEFT JOIN medicines m ON pgi.item_type = 'medicine' AND pgi.item_id = m.medicine_id
LEFT JOIN packages p ON pgi.item_type = 'package' AND pgi.item_id = p.package_id;

COMMENT ON VIEW v_campaign_group_items_detail IS 'Detailed view of campaign group items with item names and prices';

-- =============================================================================
-- 5. CREATE VIEW FOR ITEM'S GROUP MEMBERSHIPS
-- =============================================================================
CREATE OR REPLACE VIEW v_item_campaign_groups AS
SELECT
    pgi.item_type,
    pgi.item_id,
    pcg.hospital_id,
    array_agg(pcg.group_id) AS group_ids,
    array_agg(pcg.group_code) AS group_codes,
    array_agg(pcg.group_name) AS group_names,
    count(*) AS group_count
FROM promotion_group_items pgi
JOIN promotion_campaign_groups pcg ON pgi.group_id = pcg.group_id
WHERE pcg.is_active = TRUE
GROUP BY pgi.item_type, pgi.item_id, pcg.hospital_id;

COMMENT ON VIEW v_item_campaign_groups IS 'Shows all campaign groups an item belongs to';

-- =============================================================================
-- 6. CREATE FUNCTION TO CHECK IF ITEM IS IN TARGET GROUPS
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_item_in_campaign_groups(
    p_item_type VARCHAR(20),
    p_item_id UUID,
    p_target_groups JSONB
) RETURNS BOOLEAN AS $$
DECLARE
    v_group_ids UUID[];
    v_item_group_ids UUID[];
BEGIN
    -- If no target groups specified, return TRUE (campaign applies to all)
    IF p_target_groups IS NULL OR p_target_groups = '{}' OR p_target_groups = 'null' THEN
        RETURN TRUE;
    END IF;

    -- Extract group_ids array from JSONB
    SELECT ARRAY(
        SELECT (jsonb_array_elements_text(p_target_groups->'group_ids'))::UUID
    ) INTO v_group_ids;

    -- If empty array, return TRUE
    IF array_length(v_group_ids, 1) IS NULL THEN
        RETURN TRUE;
    END IF;

    -- Get groups this item belongs to
    SELECT ARRAY(
        SELECT pgi.group_id
        FROM promotion_group_items pgi
        JOIN promotion_campaign_groups pcg ON pgi.group_id = pcg.group_id
        WHERE pgi.item_type = p_item_type
        AND pgi.item_id = p_item_id
        AND pcg.is_active = TRUE
    ) INTO v_item_group_ids;

    -- Check if any of item's groups match target groups
    RETURN v_item_group_ids && v_group_ids;  -- && is array overlap operator
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fn_item_in_campaign_groups IS 'Returns TRUE if item belongs to any of the specified target groups';

-- =============================================================================
-- 7. CREATE DEFAULT "GENERAL" GROUP FOR EACH HOSPITAL (Optional)
-- =============================================================================
-- This creates a default "General" group for hospitals that don't have one
-- Uncomment if you want automatic default groups

-- INSERT INTO promotion_campaign_groups (hospital_id, group_code, group_name, description)
-- SELECT
--     h.hospital_id,
--     'GENERAL',
--     'General',
--     'Default group for items not assigned to specific groups'
-- FROM hospitals h
-- WHERE NOT EXISTS (
--     SELECT 1 FROM promotion_campaign_groups pcg
--     WHERE pcg.hospital_id = h.hospital_id AND pcg.group_code = 'GENERAL'
-- );

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================
