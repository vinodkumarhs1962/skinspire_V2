-- Migration: Multi-Discount System Database Schema
-- Date: 21-Nov-2025
-- Description: Adds support for 4 discount types: Standard, Bulk, Loyalty %, Promotion
--
-- Business Rules:
-- 1. Standard discount = fallback when no other discounts apply
-- 2. Bulk discount = quantity-based (already implemented for services/medicines)
-- 3. Loyalty discount = percentage for loyalty card holders
-- 4. Promotion discount = campaign-based (fixed amount OR percentage)
-- 5. Priority: Promotion (1) > Bulk/Loyalty (2) > Standard (4)

-- ============================================================================
-- 1. ADD STANDARD DISCOUNT TO SERVICES
-- ============================================================================

ALTER TABLE services
ADD COLUMN IF NOT EXISTS standard_discount_percent NUMERIC(5,2) DEFAULT 0
CHECK (standard_discount_percent >= 0 AND standard_discount_percent <= 100);

COMMENT ON COLUMN services.standard_discount_percent IS
'Default fallback discount percentage when no other discounts apply';

-- ============================================================================
-- 2. ADD LOYALTY DISCOUNT TO SERVICES, MEDICINES, PACKAGES
-- ============================================================================

-- Services
ALTER TABLE services
ADD COLUMN IF NOT EXISTS loyalty_discount_percent NUMERIC(5,2) DEFAULT 0
CHECK (loyalty_discount_percent >= 0 AND loyalty_discount_percent <= 100);

COMMENT ON COLUMN services.loyalty_discount_percent IS
'Loyalty card discount percentage for this service';

-- Medicines (standard_discount already added in previous migration)
ALTER TABLE medicines
ADD COLUMN IF NOT EXISTS loyalty_discount_percent NUMERIC(5,2) DEFAULT 0
CHECK (loyalty_discount_percent >= 0 AND loyalty_discount_percent <= 100);

COMMENT ON COLUMN medicines.loyalty_discount_percent IS
'Loyalty card discount percentage for this medicine';

-- Packages (NO bulk discount, only standard/loyalty/promotion)
ALTER TABLE packages
ADD COLUMN IF NOT EXISTS standard_discount_percent NUMERIC(5,2) DEFAULT 0
CHECK (standard_discount_percent >= 0 AND standard_discount_percent <= 100);

ALTER TABLE packages
ADD COLUMN IF NOT EXISTS loyalty_discount_percent NUMERIC(5,2) DEFAULT 0
CHECK (loyalty_discount_percent >= 0 AND loyalty_discount_percent <= 100);

COMMENT ON COLUMN packages.standard_discount_percent IS
'Default fallback discount percentage for packages';

COMMENT ON COLUMN packages.loyalty_discount_percent IS
'Loyalty card discount percentage for packages';

-- ============================================================================
-- 3. ADD LOYALTY DISCOUNT MODE TO HOSPITAL
-- ============================================================================

-- Loyalty mode: 'absolute' = pick higher, 'additional' = add percentages
ALTER TABLE hospitals
ADD COLUMN IF NOT EXISTS loyalty_discount_mode VARCHAR(20) DEFAULT 'absolute'
CHECK (loyalty_discount_mode IN ('absolute', 'additional'));

COMMENT ON COLUMN hospitals.loyalty_discount_mode IS
'Loyalty discount mode: absolute = max(loyalty, other), additional = loyalty% + other%';

-- ============================================================================
-- 4. CREATE PROMOTION/CAMPAIGN DISCOUNT CONFIGURATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS promotion_campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Campaign Details
    campaign_name VARCHAR(100) NOT NULL,
    campaign_code VARCHAR(50) UNIQUE,  -- For manual application
    description TEXT,

    -- Campaign Period
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,

    -- Discount Configuration
    discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('percentage', 'fixed_amount')),
    discount_value NUMERIC(10,2) NOT NULL,  -- Percentage OR fixed amount

    -- Applicability
    applies_to VARCHAR(20) NOT NULL CHECK (applies_to IN ('all', 'services', 'medicines', 'packages')),
    specific_items JSONB,  -- Array of item_ids if not 'all'

    -- Constraints
    min_purchase_amount NUMERIC(10,2),  -- Minimum invoice amount
    max_discount_amount NUMERIC(10,2),  -- Cap on discount amount
    max_uses_per_patient INTEGER,  -- Limit uses per patient
    max_total_uses INTEGER,  -- Limit total uses
    current_uses INTEGER DEFAULT 0,  -- Track usage

    -- Terms & Conditions
    terms_and_conditions TEXT,

    -- Auto-application
    auto_apply BOOLEAN DEFAULT FALSE,  -- Automatically apply if eligible

    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(15)
);

COMMENT ON TABLE promotion_campaigns IS
'Campaign-based promotional discounts with eligibility rules';

-- ============================================================================
-- 5. CREATE PROMOTION USAGE TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS promotion_usage_log (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES promotion_campaigns(campaign_id),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    patient_id UUID REFERENCES patients(patient_id),
    invoice_id UUID,  -- Reference to invoice (after creation)

    -- Usage Details
    usage_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    discount_amount NUMERIC(10,2) NOT NULL,
    invoice_amount NUMERIC(10,2),

    -- Applied By
    applied_by VARCHAR(15),  -- User who applied
    applied_manually BOOLEAN DEFAULT FALSE,  -- Manual vs auto-apply

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE promotion_usage_log IS
'Tracks promotion campaign usage per patient/invoice for limits enforcement';

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_promotion_usage_campaign
ON promotion_usage_log(campaign_id, patient_id);

CREATE INDEX IF NOT EXISTS idx_promotion_usage_patient
ON promotion_usage_log(patient_id, usage_date);

-- ============================================================================
-- 6. UPDATE DISCOUNT APPLICATION LOG (for multi-discount tracking)
-- ============================================================================

-- Check if table exists, create if not
CREATE TABLE IF NOT EXISTS discount_application_log (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    invoice_id UUID NOT NULL,
    line_item_id UUID,

    -- Item Details
    item_type VARCHAR(20) NOT NULL,  -- Service, Medicine, Package
    item_id UUID NOT NULL,
    patient_id UUID REFERENCES patients(patient_id),

    -- Discount Applied
    discount_type VARCHAR(20) NOT NULL,  -- 'standard', 'bulk', 'loyalty', 'promotion'
    discount_percent NUMERIC(5,2),
    discount_amount NUMERIC(10,2) NOT NULL,
    original_amount NUMERIC(10,2) NOT NULL,
    final_amount NUMERIC(10,2) NOT NULL,

    -- Context
    service_count_in_invoice INTEGER,  -- For bulk discount
    medicine_count_in_invoice INTEGER,  -- For bulk discount
    loyalty_card_id UUID,  -- If loyalty discount
    campaign_id UUID REFERENCES promotion_campaigns(campaign_id),  -- If promotion

    -- Priority & Selection
    discount_priority INTEGER,  -- 1=Promotion, 2=Bulk/Loyalty, 4=Standard
    other_eligible_discounts JSONB,  -- Discounts that were eligible but not selected

    -- Metadata
    discount_metadata JSONB,

    -- Audit
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(15)
);

COMMENT ON TABLE discount_application_log IS
'Audit log for all discount applications with priority tracking';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_discount_log_invoice
ON discount_application_log(invoice_id);

CREATE INDEX IF NOT EXISTS idx_discount_log_patient
ON discount_application_log(patient_id, applied_at);

CREATE INDEX IF NOT EXISTS idx_discount_log_campaign
ON discount_application_log(campaign_id, applied_at);

-- ============================================================================
-- 7. ADD DISCOUNT BREAKDOWN TO PATIENT INVOICES
-- ============================================================================

-- Add column to store discount breakdown (for reporting)
ALTER TABLE patient_invoices
ADD COLUMN IF NOT EXISTS discount_breakdown JSONB;

COMMENT ON COLUMN patient_invoices.discount_breakdown IS
'JSON breakdown of all discounts: {standard: X, bulk: Y, loyalty: Z, promotion: W}';

-- ============================================================================
-- 8. VERIFICATION QUERIES
-- ============================================================================

-- Check services have all discount fields
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'services'
  AND column_name LIKE '%discount%'
ORDER BY column_name;

-- Check medicines have all discount fields
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'medicines'
  AND column_name LIKE '%discount%'
ORDER BY column_name;

-- Check packages have discount fields (no bulk)
SELECT
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_name = 'packages'
  AND column_name LIKE '%discount%'
ORDER BY column_name;

-- Check hospital has loyalty_discount_mode
SELECT
    hospital_id,
    loyalty_discount_mode,
    bulk_discount_enabled,
    bulk_discount_min_service_count
FROM hospitals
LIMIT 1;

-- Check promotion_campaigns table created
SELECT COUNT(*) as campaign_count FROM promotion_campaigns;

-- Check promotion_usage_log table created
SELECT COUNT(*) as usage_log_count FROM promotion_usage_log;

-- Check discount_application_log table
SELECT COUNT(*) as discount_log_count FROM discount_application_log;

-- ============================================================================
-- 9. SAMPLE DATA (optional - for testing)
-- ============================================================================

-- Example: Add standard discount to some services
-- UPDATE services
-- SET standard_discount_percent = 5.00,
--     loyalty_discount_percent = 10.00
-- WHERE service_name IN ('Consultation', 'Follow-up')
--   AND is_active = TRUE;

-- Example: Add loyalty discount to medicines
-- UPDATE medicines
-- SET loyalty_discount_percent = 10.00
-- WHERE medicine_type = 'OTC'
--   AND is_active = TRUE;

-- Example: Add discounts to packages
-- UPDATE packages
-- SET standard_discount_percent = 5.00,
--     loyalty_discount_percent = 15.00
-- WHERE status = 'active';

-- Example: Set hospital loyalty mode
-- UPDATE hospitals
-- SET loyalty_discount_mode = 'additional'  -- or 'absolute'
-- WHERE hospital_id = 'your-hospital-id';

-- Example: Create a promotion campaign
-- INSERT INTO promotion_campaigns (
--     hospital_id,
--     campaign_name,
--     campaign_code,
--     description,
--     start_date,
--     end_date,
--     discount_type,
--     discount_value,
--     applies_to,
--     auto_apply
-- ) VALUES (
--     'your-hospital-id',
--     'Festive Offer 2025',
--     'FEST2025',
--     '20% off on all services',
--     '2025-12-01',
--     '2025-12-31',
--     'percentage',
--     20.00,
--     'services',
--     TRUE
-- );

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Expected result:
-- 1. Services: bulk_discount_percent, standard_discount_percent, loyalty_discount_percent, max_discount
-- 2. Medicines: bulk_discount_percent, standard_discount_percent, loyalty_discount_percent, max_discount
-- 3. Packages: standard_discount_percent, loyalty_discount_percent, max_discount (NO bulk)
-- 4. Hospitals: loyalty_discount_mode
-- 5. New tables: promotion_campaigns, promotion_usage_log, discount_application_log
-- 6. patient_invoices: discount_breakdown column

-- Rollback (if needed):
-- ALTER TABLE services DROP COLUMN IF EXISTS standard_discount_percent;
-- ALTER TABLE services DROP COLUMN IF EXISTS loyalty_discount_percent;
-- ALTER TABLE medicines DROP COLUMN IF EXISTS loyalty_discount_percent;
-- ALTER TABLE packages DROP COLUMN IF EXISTS standard_discount_percent;
-- ALTER TABLE packages DROP COLUMN IF EXISTS loyalty_discount_percent;
-- ALTER TABLE hospitals DROP COLUMN IF EXISTS loyalty_discount_mode;
-- ALTER TABLE patient_invoices DROP COLUMN IF EXISTS discount_breakdown;
-- DROP TABLE IF EXISTS promotion_usage_log;
-- DROP TABLE IF EXISTS promotion_campaigns;
-- DROP TABLE IF EXISTS discount_application_log;
