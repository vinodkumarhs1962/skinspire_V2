-- Migration: Create Simplified Bulk Service Discount System
-- Created: 2025-11-20
-- Description: Adds bulk discount support via Hospital policy + Service-level rates, loyalty cards, and audit logging

-- ============================================
-- PART 1: Add Bulk Discount Fields to Hospital
-- ============================================
-- Hospital-level bulk discount policy
ALTER TABLE hospitals
ADD COLUMN IF NOT EXISTS bulk_discount_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS bulk_discount_min_service_count INTEGER DEFAULT 5,
ADD COLUMN IF NOT EXISTS bulk_discount_effective_from DATE;

COMMENT ON COLUMN hospitals.bulk_discount_enabled IS 'Whether hospital offers bulk service discounts';
COMMENT ON COLUMN hospitals.bulk_discount_min_service_count IS 'Minimum number of services in invoice to trigger bulk discount (e.g., 5)';
COMMENT ON COLUMN hospitals.bulk_discount_effective_from IS 'Date when bulk discount policy became effective';

-- ============================================
-- PART 2: Add Bulk Discount Field to Services
-- ============================================
-- Service-specific bulk discount percentage
ALTER TABLE services
ADD COLUMN IF NOT EXISTS bulk_discount_percent NUMERIC(5, 2) DEFAULT 0;

COMMENT ON COLUMN services.bulk_discount_percent IS 'Discount percentage applied to this service during bulk purchases (e.g., 10.00 for 10%)';

-- ============================================
-- PART 3: Loyalty Card Types Table
-- ============================================
CREATE TABLE IF NOT EXISTS loyalty_card_types (
    card_type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Card type details
    card_type_code VARCHAR(20) NOT NULL,  -- e.g., 'SILVER', 'GOLD', 'PLATINUM'
    card_type_name VARCHAR(50) NOT NULL,  -- Display name
    description TEXT,

    -- Discount configuration
    discount_percent NUMERIC(5, 2) DEFAULT 0,  -- Default discount for this card type

    -- Card benefits (flexible JSON for additional perks)
    benefits JSONB,  -- {priority_booking: true, free_consultation: true, etc.}

    -- Eligibility criteria
    min_lifetime_spend NUMERIC(12, 2),  -- Minimum spend to qualify
    min_visits INTEGER,  -- Minimum visit count to qualify

    -- Visual styling
    card_color VARCHAR(7),  -- Hex color code for UI display
    icon_url VARCHAR(255),
    display_sequence INTEGER,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Standard fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(50),

    CONSTRAINT uk_loyalty_card_code UNIQUE (hospital_id, card_type_code)
);

-- Indexes for loyalty_card_types
CREATE INDEX IF NOT EXISTS idx_loyalty_card_hospital ON loyalty_card_types(hospital_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_loyalty_card_active ON loyalty_card_types(hospital_id, is_active) WHERE is_deleted = FALSE;

-- ============================================
-- PART 4: Patient Loyalty Cards Table
-- ============================================
CREATE TABLE IF NOT EXISTS patient_loyalty_cards (
    patient_card_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    card_type_id UUID NOT NULL REFERENCES loyalty_card_types(card_type_id),

    -- Card details
    card_number VARCHAR(50) UNIQUE,  -- Physical/digital card number
    issue_date DATE NOT NULL,
    expiry_date DATE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Standard fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    deleted_by VARCHAR(50),

    CONSTRAINT uk_patient_card UNIQUE (patient_id, card_type_id)
);

-- Indexes for patient_loyalty_cards
CREATE INDEX IF NOT EXISTS idx_patient_loyalty_patient ON patient_loyalty_cards(patient_id) WHERE is_deleted = FALSE AND is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_patient_loyalty_card_type ON patient_loyalty_cards(card_type_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_patient_loyalty_hospital ON patient_loyalty_cards(hospital_id) WHERE is_deleted = FALSE;

-- ============================================
-- PART 5: Discount Application Log (Audit Trail)
-- ============================================
CREATE TABLE IF NOT EXISTS discount_application_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Invoice reference
    invoice_id UUID REFERENCES invoice_header(invoice_id),
    line_item_id UUID REFERENCES invoice_line_item(line_item_id),

    -- Discount details
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('bulk', 'loyalty', 'campaign', 'manual', 'none')),
    card_type_id UUID REFERENCES loyalty_card_types(card_type_id),  -- If type = 'loyalty'
    campaign_hook_id UUID REFERENCES campaign_hook_config(hook_id),  -- If type = 'campaign'

    -- Discount amounts
    original_price NUMERIC(12, 2) NOT NULL,
    discount_percent NUMERIC(5, 2) NOT NULL,
    discount_amount NUMERIC(12, 2) NOT NULL,
    final_price NUMERIC(12, 2) NOT NULL,

    -- Context
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by UUID,
    patient_id UUID REFERENCES patients(patient_id),
    service_id UUID REFERENCES services(service_id),

    -- Metadata
    calculation_metadata JSONB,  -- Store competing discounts and why this one was chosen
    service_count_in_invoice INTEGER  -- Total service count that triggered bulk discount

    -- No standard fields needed for log table
);

-- Indexes for discount_application_log
CREATE INDEX IF NOT EXISTS idx_discount_log_invoice ON discount_application_log(invoice_id);
CREATE INDEX IF NOT EXISTS idx_discount_log_line_item ON discount_application_log(line_item_id);
CREATE INDEX IF NOT EXISTS idx_discount_log_type ON discount_application_log(discount_type, applied_at);
CREATE INDEX IF NOT EXISTS idx_discount_log_hospital ON discount_application_log(hospital_id, applied_at);
CREATE INDEX IF NOT EXISTS idx_discount_log_patient ON discount_application_log(patient_id, applied_at);
CREATE INDEX IF NOT EXISTS idx_discount_log_service ON discount_application_log(service_id, applied_at);

-- ============================================
-- PART 6: Update Timestamp Triggers
-- ============================================
CREATE OR REPLACE FUNCTION update_loyalty_card_types_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_patient_loyalty_cards_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers
DROP TRIGGER IF EXISTS trigger_loyalty_card_types_updated ON loyalty_card_types;
CREATE TRIGGER trigger_loyalty_card_types_updated
    BEFORE UPDATE ON loyalty_card_types
    FOR EACH ROW
    EXECUTE FUNCTION update_loyalty_card_types_timestamp();

DROP TRIGGER IF EXISTS trigger_patient_loyalty_cards_updated ON patient_loyalty_cards;
CREATE TRIGGER trigger_patient_loyalty_cards_updated
    BEFORE UPDATE ON patient_loyalty_cards
    FOR EACH ROW
    EXECUTE FUNCTION update_patient_loyalty_cards_timestamp();

-- ============================================
-- PART 7: Table Comments
-- ============================================
COMMENT ON TABLE loyalty_card_types IS 'Defines different types of loyalty cards (Silver, Gold, Platinum) with associated discounts';
COMMENT ON TABLE patient_loyalty_cards IS 'Links patients to their loyalty card types';
COMMENT ON TABLE discount_application_log IS 'Audit trail of all discount applications in invoices';

COMMENT ON COLUMN loyalty_card_types.discount_percent IS 'Standard discount percentage for this loyalty card tier';
COMMENT ON COLUMN discount_application_log.calculation_metadata IS 'JSONB containing all competing discounts and why this one was selected';
COMMENT ON COLUMN discount_application_log.service_count_in_invoice IS 'Number of services in invoice that triggered bulk discount eligibility';

-- ============================================
-- PART 8: Sample Data (for testing/initial setup)
-- ============================================
-- Insert default loyalty card types for existing hospitals
INSERT INTO loyalty_card_types (hospital_id, card_type_code, card_type_name, description, discount_percent, card_color, display_sequence, is_active)
SELECT
    h.hospital_id,
    'STANDARD',
    'Standard Member',
    'Basic membership with standard benefits',
    0.00,
    '#808080',
    1,
    TRUE
FROM hospitals h
WHERE NOT EXISTS (SELECT 1 FROM loyalty_card_types lct WHERE lct.hospital_id = h.hospital_id AND lct.card_type_code = 'STANDARD');

INSERT INTO loyalty_card_types (hospital_id, card_type_code, card_type_name, description, discount_percent, min_lifetime_spend, card_color, display_sequence, is_active)
SELECT
    h.hospital_id,
    'SILVER',
    'Silver Member',
    'Silver tier membership with 5% discount on all services',
    5.00,
    50000.00,
    '#C0C0C0',
    2,
    TRUE
FROM hospitals h
WHERE NOT EXISTS (SELECT 1 FROM loyalty_card_types lct WHERE lct.hospital_id = h.hospital_id AND lct.card_type_code = 'SILVER');

INSERT INTO loyalty_card_types (hospital_id, card_type_code, card_type_name, description, discount_percent, min_lifetime_spend, card_color, display_sequence, is_active)
SELECT
    h.hospital_id,
    'GOLD',
    'Gold Member',
    'Gold tier membership with 10% discount on all services',
    10.00,
    100000.00,
    '#FFD700',
    3,
    TRUE
FROM hospitals h
WHERE NOT EXISTS (SELECT 1 FROM loyalty_card_types lct WHERE lct.hospital_id = h.hospital_id AND lct.card_type_code = 'GOLD');

INSERT INTO loyalty_card_types (hospital_id, card_type_code, card_type_name, description, discount_percent, min_lifetime_spend, card_color, display_sequence, is_active)
SELECT
    h.hospital_id,
    'PLATINUM',
    'Platinum Member',
    'Platinum tier membership with 15% discount on all services',
    15.00,
    250000.00,
    '#E5E4E2',
    4,
    TRUE
FROM hospitals h
WHERE NOT EXISTS (SELECT 1 FROM loyalty_card_types lct WHERE lct.hospital_id = h.hospital_id AND lct.card_type_code = 'PLATINUM');

-- Enable bulk discount for all hospitals by default (can be toggled off via UI)
UPDATE hospitals
SET bulk_discount_enabled = TRUE,
    bulk_discount_min_service_count = 5,
    bulk_discount_effective_from = CURRENT_DATE
WHERE bulk_discount_enabled IS NULL OR bulk_discount_enabled = FALSE;

-- Set sample bulk discount percentages for services (you can customize these)
-- Example: Set 10% bulk discount for all laser treatments
-- UPDATE services
-- SET bulk_discount_percent = 10.00
-- WHERE service_type LIKE '%Laser%' AND bulk_discount_percent = 0;

-- Example: Set 15% bulk discount for all facials
-- UPDATE services
-- SET bulk_discount_percent = 15.00
-- WHERE service_type LIKE '%Facial%' AND bulk_discount_percent = 0;
