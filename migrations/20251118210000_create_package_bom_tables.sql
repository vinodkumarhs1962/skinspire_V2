-- Migration: Create Package BOM and Session Plan Tables
-- Created: 2025-11-18
-- Description: Creates tables for package bill of materials and session delivery planning

-- ============================================
-- Package BOM Items Table
-- ============================================
CREATE TABLE IF NOT EXISTS package_bom_items (
    bom_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES packages(package_id) ON DELETE CASCADE,

    -- Polymorphic item reference
    item_type VARCHAR(20) NOT NULL CHECK (item_type IN ('service', 'medicine', 'consumable', 'equipment')),
    item_id UUID NOT NULL,
    item_name VARCHAR(200),  -- Denormalized for display

    -- Quantity and supply details
    quantity NUMERIC(10, 2) NOT NULL DEFAULT 1,
    unit_of_measure VARCHAR(20),
    supply_method VARCHAR(20) DEFAULT 'per_package' CHECK (supply_method IN ('per_package', 'per_session', 'on_demand', 'conditional')),

    -- Pricing (captured at time of BOM creation)
    current_price NUMERIC(10, 2),
    line_total NUMERIC(10, 2),

    -- Optional/conditional items
    is_optional BOOLEAN DEFAULT FALSE,
    conditional_logic JSONB,  -- Conditions for when this item is needed

    -- Additional details
    notes TEXT,
    display_sequence INTEGER,

    -- Standard fields
    hospital_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(50),

    -- Indexes
    CONSTRAINT fk_package_bom_package FOREIGN KEY (package_id) REFERENCES packages(package_id)
);

-- Indexes for package_bom_items
CREATE INDEX IF NOT EXISTS idx_package_bom_package_id ON package_bom_items(package_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_package_bom_item_type ON package_bom_items(item_type, item_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_package_bom_hospital_id ON package_bom_items(hospital_id) WHERE is_deleted = FALSE;

-- ============================================
-- Package Session Plan Table
-- ============================================
CREATE TABLE IF NOT EXISTS package_session_plan (
    session_plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES packages(package_id) ON DELETE CASCADE,

    -- Session details
    session_number INTEGER NOT NULL,
    session_name VARCHAR(100),
    session_description TEXT,

    -- Timing
    estimated_duration_minutes INTEGER,
    recommended_gap_days INTEGER,  -- Days between this and previous session

    -- Resource requirements (JSONB array)
    resource_requirements JSONB,  -- [{resource_type: 'doctor', role: 'Dermatologist', duration_minutes: 30, quantity: 1}, ...]

    -- Session properties
    is_mandatory BOOLEAN DEFAULT TRUE,
    display_sequence INTEGER,

    -- Scheduling notes
    scheduling_notes TEXT,
    prerequisites TEXT,  -- What must be done before this session

    -- Standard fields
    hospital_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(50),

    CONSTRAINT fk_package_session_package FOREIGN KEY (package_id) REFERENCES packages(package_id)
);

-- Indexes for package_session_plan
CREATE INDEX IF NOT EXISTS idx_package_session_package_id ON package_session_plan(package_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_package_session_number ON package_session_plan(package_id, session_number) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_package_session_hospital_id ON package_session_plan(hospital_id) WHERE is_deleted = FALSE;

-- Update timestamp triggers
CREATE OR REPLACE FUNCTION update_package_bom_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_package_session_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_package_bom_updated_at ON package_bom_items;
CREATE TRIGGER trigger_package_bom_updated_at
    BEFORE UPDATE ON package_bom_items
    FOR EACH ROW
    EXECUTE FUNCTION update_package_bom_updated_at();

DROP TRIGGER IF EXISTS trigger_package_session_updated_at ON package_session_plan;
CREATE TRIGGER trigger_package_session_updated_at
    BEFORE UPDATE ON package_session_plan
    FOR EACH ROW
    EXECUTE FUNCTION update_package_session_updated_at();

-- Add comments
COMMENT ON TABLE package_bom_items IS 'Bill of Materials for packages - defines what services/medicines are included';
COMMENT ON TABLE package_session_plan IS 'Session delivery plan for packages - defines how the package is delivered over multiple sessions';
COMMENT ON COLUMN package_bom_items.item_type IS 'Type of item: service, medicine, consumable, equipment';
COMMENT ON COLUMN package_bom_items.supply_method IS 'How item is supplied: per_package, per_session, on_demand, conditional';
COMMENT ON COLUMN package_session_plan.resource_requirements IS 'JSONB array of required resources per session';
