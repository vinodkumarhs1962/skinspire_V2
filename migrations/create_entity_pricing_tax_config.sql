-- Migration: Create Entity Pricing and Tax Configuration Table
-- Date: 2025-11-17
-- Purpose: Date-based versioning of pricing (MRP, selling price) and GST rates
--          for medicines, services, and packages
-- Priority: HIGH - Required for tax compliance

-- =====================================================================
-- TABLE: entity_pricing_tax_config
-- =====================================================================

CREATE TABLE IF NOT EXISTS entity_pricing_tax_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(branch_id) ON DELETE SET NULL,

    -- === ENTITY REFERENCE (Exactly ONE must be populated) ===
    medicine_id UUID REFERENCES medicines(medicine_id) ON DELETE CASCADE,
    service_id UUID REFERENCES services(service_id) ON DELETE CASCADE,
    package_id UUID REFERENCES packages(package_id) ON DELETE CASCADE,

    -- === EFFECTIVE PERIOD ===
    effective_from DATE NOT NULL,
    effective_to DATE,  -- NULL = currently effective

    -- === PRICING INFORMATION ===
    -- For Medicines
    mrp NUMERIC(12, 2),                    -- Maximum Retail Price
    pack_mrp NUMERIC(12, 2),               -- MRP per pack
    pack_purchase_price NUMERIC(12, 2),   -- Purchase price per pack
    units_per_pack NUMERIC(10, 2),        -- Units in a pack
    unit_price NUMERIC(12, 2),            -- Price per unit (derived or explicit)
    selling_price NUMERIC(12, 2),         -- Actual selling price
    cost_price NUMERIC(12, 2),            -- Cost price for profit calculation

    -- For Services/Packages
    service_price NUMERIC(12, 2),         -- Service base price
    package_price NUMERIC(12, 2),         -- Package base price

    -- === GST INFORMATION ===
    gst_rate NUMERIC(5, 2),               -- Overall GST rate (%)
    cgst_rate NUMERIC(5, 2),              -- Central GST (%)
    sgst_rate NUMERIC(5, 2),              -- State GST (%)
    igst_rate NUMERIC(5, 2),              -- Integrated GST (%)
    is_gst_exempt BOOLEAN DEFAULT false,
    gst_inclusive BOOLEAN DEFAULT false,  -- Whether price includes GST

    -- === REFERENCE DOCUMENTATION ===
    -- For GST changes
    gst_notification_number VARCHAR(100),
    gst_notification_date DATE,
    gst_notification_url VARCHAR(500),

    -- For price changes
    manufacturer_notification VARCHAR(100),  -- Manufacturer price revision reference
    manufacturer_notification_date DATE,
    price_revision_reason TEXT,

    -- === METADATA ===
    change_type VARCHAR(50),               -- 'gst_change', 'price_change', 'both', 'initial'
    change_reason TEXT,
    remarks TEXT,

    -- === AUDIT FIELDS ===
    created_by VARCHAR(15) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15) REFERENCES users(user_id),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT false,

    -- === CONSTRAINTS ===
    -- Exactly one entity must be specified
    CONSTRAINT chk_entity_reference CHECK (
        (medicine_id IS NOT NULL AND service_id IS NULL AND package_id IS NULL) OR
        (medicine_id IS NULL AND service_id IS NOT NULL AND package_id IS NULL) OR
        (medicine_id IS NULL AND service_id IS NULL AND package_id IS NOT NULL)
    ),

    -- Effective dates must be valid
    CONSTRAINT chk_effective_dates CHECK (
        effective_to IS NULL OR effective_to > effective_from
    ),

    -- GST rate must equal sum of components
    CONSTRAINT chk_gst_rate_sum CHECK (
        gst_rate IS NULL OR
        gst_rate = COALESCE(cgst_rate, 0) + COALESCE(sgst_rate, 0) + COALESCE(igst_rate, 0)
    ),

    -- Medicine must have at least one price field
    CONSTRAINT chk_medicine_pricing CHECK (
        medicine_id IS NULL OR
        (mrp IS NOT NULL OR pack_mrp IS NOT NULL OR selling_price IS NOT NULL)
    ),

    -- Service must have price
    CONSTRAINT chk_service_pricing CHECK (
        service_id IS NULL OR service_price IS NOT NULL
    ),

    -- Package must have price
    CONSTRAINT chk_package_pricing CHECK (
        package_id IS NULL OR package_price IS NOT NULL
    )
);

-- =====================================================================
-- INDEXES for Performance
-- =====================================================================

-- Medicine lookups (most common)
CREATE INDEX idx_pricing_tax_config_medicine
    ON entity_pricing_tax_config(medicine_id, effective_from, effective_to)
    WHERE medicine_id IS NOT NULL AND is_deleted = false;

-- Service lookups
CREATE INDEX idx_pricing_tax_config_service
    ON entity_pricing_tax_config(service_id, effective_from, effective_to)
    WHERE service_id IS NOT NULL AND is_deleted = false;

-- Package lookups
CREATE INDEX idx_pricing_tax_config_package
    ON entity_pricing_tax_config(package_id, effective_from, effective_to)
    WHERE package_id IS NOT NULL AND is_deleted = false;

-- Date range queries
CREATE INDEX idx_pricing_tax_config_dates
    ON entity_pricing_tax_config(effective_from, effective_to)
    WHERE is_deleted = false;

-- Hospital-wide queries
CREATE INDEX idx_pricing_tax_config_hospital
    ON entity_pricing_tax_config(hospital_id, effective_from)
    WHERE is_deleted = false;

-- =====================================================================
-- UNIQUE CONSTRAINTS: Prevent overlapping periods
-- =====================================================================

-- Ensure no overlapping effective periods for same medicine
CREATE UNIQUE INDEX idx_pricing_tax_config_no_overlap_medicine
    ON entity_pricing_tax_config(hospital_id, medicine_id, effective_from)
    WHERE medicine_id IS NOT NULL AND is_deleted = false;

-- Ensure no overlapping effective periods for same service
CREATE UNIQUE INDEX idx_pricing_tax_config_no_overlap_service
    ON entity_pricing_tax_config(hospital_id, service_id, effective_from)
    WHERE service_id IS NOT NULL AND is_deleted = false;

-- Ensure no overlapping effective periods for same package
CREATE UNIQUE INDEX idx_pricing_tax_config_no_overlap_package
    ON entity_pricing_tax_config(hospital_id, package_id, effective_from)
    WHERE package_id IS NOT NULL AND is_deleted = false;

-- =====================================================================
-- COMMENTS
-- =====================================================================

COMMENT ON TABLE entity_pricing_tax_config IS 'Date-based versioning of pricing and GST rates for medicines, services, and packages. Enables historical accuracy for tax compliance and price change tracking.';

COMMENT ON COLUMN entity_pricing_tax_config.effective_from IS 'Date from which this pricing/GST configuration is effective';
COMMENT ON COLUMN entity_pricing_tax_config.effective_to IS 'Date until which this configuration is effective. NULL means currently effective (open-ended)';
COMMENT ON COLUMN entity_pricing_tax_config.gst_notification_number IS 'Government notification reference for GST rate changes';
COMMENT ON COLUMN entity_pricing_tax_config.manufacturer_notification IS 'Manufacturer notification reference for price revisions';
COMMENT ON COLUMN entity_pricing_tax_config.change_type IS 'Type of change: gst_change, price_change, both, or initial';

-- =====================================================================
-- GRANT PERMISSIONS
-- =====================================================================

-- Grant appropriate permissions (adjust role names as needed)
-- GRANT SELECT, INSERT, UPDATE ON entity_pricing_tax_config TO app_user;
-- GRANT USAGE ON SEQUENCE ... TO app_user;  -- If using sequences

-- =====================================================================
-- VERIFICATION QUERIES
-- =====================================================================

-- Verify table created
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'entity_pricing_tax_config'
ORDER BY ordinal_position;

-- Verify indexes created
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'entity_pricing_tax_config';

-- Verify constraints
SELECT
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'entity_pricing_tax_config'::regclass;

-- =====================================================================
-- ROLLBACK (if needed)
-- =====================================================================

-- To rollback this migration:
/*
DROP INDEX IF EXISTS idx_pricing_tax_config_no_overlap_package;
DROP INDEX IF EXISTS idx_pricing_tax_config_no_overlap_service;
DROP INDEX IF EXISTS idx_pricing_tax_config_no_overlap_medicine;
DROP INDEX IF EXISTS idx_pricing_tax_config_hospital;
DROP INDEX IF EXISTS idx_pricing_tax_config_dates;
DROP INDEX IF EXISTS idx_pricing_tax_config_package;
DROP INDEX IF EXISTS idx_pricing_tax_config_service;
DROP INDEX IF EXISTS idx_pricing_tax_config_medicine;
DROP TABLE IF EXISTS entity_pricing_tax_config CASCADE;
*/
