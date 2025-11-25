-- Migration: Loyalty Tier Enhancements
-- Date: 24-Nov-2025
-- Description: Add tier-specific fields and tier history tracking

-- ============================================================================
-- 1. ENHANCE LOYALTY_CARD_TYPES TABLE
-- ============================================================================

-- Add tier configuration fields
ALTER TABLE loyalty_card_types
ADD COLUMN IF NOT EXISTS min_payment_amount NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS total_points_credited INTEGER,
ADD COLUMN IF NOT EXISTS bonus_percentage NUMERIC(5,2),
ADD COLUMN IF NOT EXISTS validity_months INTEGER DEFAULT 12;

COMMENT ON COLUMN loyalty_card_types.min_payment_amount IS 'Minimum payment required to activate this tier (e.g., ₹22,000 for Silver)';
COMMENT ON COLUMN loyalty_card_types.total_points_credited IS 'Total points credited on tier activation (base + bonus, e.g., 25,000 for Silver)';
COMMENT ON COLUMN loyalty_card_types.bonus_percentage IS 'Percentage bonus on payment amount (e.g., 13.64% for Silver)';
COMMENT ON COLUMN loyalty_card_types.validity_months IS 'Validity period in months (default 12 months)';

-- ============================================================================
-- 2. CREATE LOYALTY_CARD_TIER_HISTORY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS loyalty_card_tier_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES patient_loyalty_wallet(wallet_id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    card_type_id UUID NOT NULL REFERENCES loyalty_card_types(card_type_id),
    previous_card_type_id UUID REFERENCES loyalty_card_types(card_type_id),

    change_type VARCHAR(20) NOT NULL, -- 'new', 'upgrade', 'downgrade', 'renewal'
    amount_paid NUMERIC(12,2) NOT NULL,
    points_credited INTEGER NOT NULL,
    bonus_points INTEGER NOT NULL,

    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,

    payment_id UUID,  -- References payment_details if payment exists
    transaction_id UUID REFERENCES wallet_transaction(transaction_id),

    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15) REFERENCES users(user_id),

    CONSTRAINT chk_change_type CHECK (change_type IN ('new', 'upgrade', 'downgrade', 'renewal'))
);

COMMENT ON TABLE loyalty_card_tier_history IS 'Tracks patient tier changes (new, upgrades, renewals)';
COMMENT ON COLUMN loyalty_card_tier_history.change_type IS 'Type: new (first tier), upgrade (higher tier), downgrade (lower tier), renewal (same tier)';
COMMENT ON COLUMN loyalty_card_tier_history.amount_paid IS 'Amount paid for this tier change';
COMMENT ON COLUMN loyalty_card_tier_history.points_credited IS 'Total points credited for this tier change';
COMMENT ON COLUMN loyalty_card_tier_history.bonus_points IS 'Bonus points included in points_credited';

CREATE INDEX idx_tier_history_wallet ON loyalty_card_tier_history(wallet_id);
CREATE INDEX idx_tier_history_patient ON loyalty_card_tier_history(patient_id);
CREATE INDEX idx_tier_history_validity ON loyalty_card_tier_history(valid_from, valid_until);
CREATE INDEX idx_tier_history_card_type ON loyalty_card_tier_history(card_type_id);

-- ============================================================================
-- 3. ENHANCE PAYMENT_DETAILS TABLE
-- ============================================================================

-- Add wallet payment tracking fields
ALTER TABLE payment_details
ADD COLUMN IF NOT EXISTS wallet_points_amount NUMERIC(12,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS wallet_transaction_id UUID REFERENCES wallet_transaction(transaction_id);

-- Add check constraint
ALTER TABLE payment_details
DROP CONSTRAINT IF EXISTS chk_wallet_points_amount;

ALTER TABLE payment_details
ADD CONSTRAINT chk_wallet_points_amount CHECK (wallet_points_amount >= 0);

COMMENT ON COLUMN payment_details.wallet_points_amount IS 'Loyalty wallet points used in this payment (1 point = ₹1)';
COMMENT ON COLUMN payment_details.wallet_transaction_id IS 'Link to wallet redemption transaction';

CREATE INDEX IF NOT EXISTS idx_payment_wallet_txn ON payment_details(wallet_transaction_id);

-- ============================================================================
-- 4. CREATE GL ACCOUNT FOR WALLET
-- ============================================================================

-- Insert Customer Loyalty Wallet account (if not exists)
DO $$
DECLARE
    v_hospital_id UUID;
    v_parent_account_id UUID;
    v_account_exists BOOLEAN;
BEGIN
    -- Get the first active hospital
    SELECT hospital_id INTO v_hospital_id
    FROM hospitals
    WHERE is_active = TRUE
    LIMIT 1;

    IF v_hospital_id IS NULL THEN
        RAISE NOTICE 'No active hospital found. Skipping GL account creation.';
        RETURN;
    END IF;

    -- Check if account already exists
    SELECT EXISTS(
        SELECT 1 FROM chart_of_accounts
        WHERE hospital_id = v_hospital_id
        AND account_code = '2350'
    ) INTO v_account_exists;

    IF v_account_exists THEN
        RAISE NOTICE 'GL Account 2350 already exists. Skipping creation.';
        RETURN;
    END IF;

    -- Get parent account (Current Liabilities - 2000)
    SELECT account_id INTO v_parent_account_id
    FROM chart_of_accounts
    WHERE hospital_id = v_hospital_id
    AND account_code = '2000';

    IF v_parent_account_id IS NULL THEN
        RAISE NOTICE 'Parent account 2000 not found. Creating without parent.';
    END IF;

    -- Insert GL account
    INSERT INTO chart_of_accounts (
        account_id,
        hospital_id,
        account_code,
        account_name,
        account_type,
        parent_account_id,
        is_active,
        created_at,
        updated_at
    ) VALUES (
        gen_random_uuid(),
        v_hospital_id,
        '2350',
        'Customer Loyalty Wallet',
        'LIABILITY',
        v_parent_account_id,
        TRUE,
        NOW(),
        NOW()
    );

    RAISE NOTICE 'GL Account 2350 - Customer Loyalty Wallet created successfully.';
END $$;

-- ============================================================================
-- 5. INSERT TIER DATA (Silver/Gold/Platinum)
-- ============================================================================

-- Update existing or insert tier data
DO $$
DECLARE
    v_hospital_id UUID;
BEGIN
    -- Get the first active hospital
    SELECT hospital_id INTO v_hospital_id
    FROM hospitals
    WHERE is_active = TRUE
    LIMIT 1;

    IF v_hospital_id IS NULL THEN
        RAISE NOTICE 'No active hospital found. Skipping tier data insertion.';
        RETURN;
    END IF;

    -- Silver Tier
    INSERT INTO loyalty_card_types (
        card_type_id,
        hospital_id,
        card_type_code,
        card_type_name,
        discount_percent,
        min_payment_amount,
        total_points_credited,
        bonus_percentage,
        validity_months,
        card_color,
        is_active,
        created_at,
        updated_at
    ) VALUES (
        gen_random_uuid(),
        v_hospital_id,
        'SILVER',
        'Silver Member',
        2.00,  -- 2% discount
        22000.00,  -- Pay ₹22,000
        25000,  -- Get 25,000 points
        13.64,  -- 13.64% bonus (3,000 bonus points)
        12,  -- 12 months validity
        '#C0C0C0',
        TRUE,
        NOW(),
        NOW()
    )
    ON CONFLICT (hospital_id, card_type_code)
    DO UPDATE SET
        discount_percent = 2.00,
        min_payment_amount = 22000.00,
        total_points_credited = 25000,
        bonus_percentage = 13.64,
        validity_months = 12,
        updated_at = NOW();

    -- Gold Tier
    INSERT INTO loyalty_card_types (
        card_type_id,
        hospital_id,
        card_type_code,
        card_type_name,
        discount_percent,
        min_payment_amount,
        total_points_credited,
        bonus_percentage,
        validity_months,
        card_color,
        is_active,
        created_at,
        updated_at
    ) VALUES (
        gen_random_uuid(),
        v_hospital_id,
        'GOLD',
        'Gold Member',
        3.00,  -- 3% discount
        45000.00,  -- Pay ₹45,000
        50000,  -- Get 50,000 points
        11.11,  -- 11.11% bonus (5,000 bonus points)
        12,  -- 12 months validity
        '#FFD700',
        TRUE,
        NOW(),
        NOW()
    )
    ON CONFLICT (hospital_id, card_type_code)
    DO UPDATE SET
        discount_percent = 3.00,
        min_payment_amount = 45000.00,
        total_points_credited = 50000,
        bonus_percentage = 11.11,
        validity_months = 12,
        updated_at = NOW();

    -- Platinum Tier
    INSERT INTO loyalty_card_types (
        card_type_id,
        hospital_id,
        card_type_code,
        card_type_name,
        discount_percent,
        min_payment_amount,
        total_points_credited,
        bonus_percentage,
        validity_months,
        card_color,
        is_active,
        created_at,
        updated_at
    ) VALUES (
        gen_random_uuid(),
        v_hospital_id,
        'PLATINUM',
        'Platinum Member',
        5.00,  -- 5% discount
        92000.00,  -- Pay ₹92,000
        100000,  -- Get 100,000 points
        8.70,  -- 8.70% bonus (8,000 bonus points)
        12,  -- 12 months validity
        '#E5E4E2',
        TRUE,
        NOW(),
        NOW()
    )
    ON CONFLICT (hospital_id, card_type_code)
    DO UPDATE SET
        discount_percent = 5.00,
        min_payment_amount = 92000.00,
        total_points_credited = 100000,
        bonus_percentage = 8.70,
        validity_months = 12,
        updated_at = NOW();

    RAISE NOTICE 'Tier data (Silver/Gold/Platinum) inserted/updated successfully.';
END $$;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Tables created:
-- - loyalty_card_tier_history (tier tracking)
--
-- Tables enhanced:
-- - loyalty_card_types (added tier fields)
-- - payment_details (added wallet payment fields)
--
-- Data inserted:
-- - GL Account 2350 (Customer Loyalty Wallet)
-- - 3 Tier definitions (Silver/Gold/Platinum)
