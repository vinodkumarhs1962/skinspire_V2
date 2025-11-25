-- Migration: Create Loyalty Wallet Prepaid Points System
-- Date: 21-Nov-2025
-- Description: Implements prepaid wallet system where patients load points and redeem for services/medicines

-- ============================================================================
-- 1. PATIENT LOYALTY WALLET TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS patient_loyalty_wallet (
    wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL REFERENCES patient(patient_id) ON DELETE CASCADE,
    hospital_id UUID NOT NULL REFERENCES hospital(hospital_id),
    branch_id UUID REFERENCES branch(branch_id),
    card_type_id UUID REFERENCES loyalty_card_type(card_type_id),

    -- Balance tracking
    points_balance INTEGER DEFAULT 0 NOT NULL,
    points_value NUMERIC(12,2) DEFAULT 0 NOT NULL,  -- Current redemption value (1:1 ratio)

    -- Lifetime tracking
    total_amount_loaded NUMERIC(12,2) DEFAULT 0 NOT NULL,  -- Total ₹ paid by patient
    total_points_loaded INTEGER DEFAULT 0 NOT NULL,         -- Total points received (base + bonus)
    total_points_redeemed INTEGER DEFAULT 0 NOT NULL,       -- Total points used
    total_bonus_points INTEGER DEFAULT 0 NOT NULL,          -- Total bonus points received

    -- Status
    wallet_status VARCHAR(20) DEFAULT 'active' NOT NULL,  -- 'active', 'suspended', 'closed'
    is_active BOOLEAN DEFAULT TRUE NOT NULL,

    -- Audit fields
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_by UUID REFERENCES users(user_id),
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    closed_at TIMESTAMP,
    closed_by UUID REFERENCES users(user_id),

    -- Constraints
    CONSTRAINT check_wallet_balance_positive CHECK (points_balance >= 0),
    CONSTRAINT check_wallet_value_positive CHECK (points_value >= 0),
    CONSTRAINT check_wallet_status CHECK (wallet_status IN ('active', 'suspended', 'closed')),
    CONSTRAINT unique_wallet_per_patient UNIQUE (patient_id, hospital_id)
);

COMMENT ON TABLE patient_loyalty_wallet IS 'Prepaid loyalty wallet for patients to load points and redeem for services/medicines';
COMMENT ON COLUMN patient_loyalty_wallet.points_balance IS 'Current available points (after redemptions and expiry)';
COMMENT ON COLUMN patient_loyalty_wallet.points_value IS 'Redemption value in rupees (1 point = 1 rupee)';
COMMENT ON COLUMN patient_loyalty_wallet.total_amount_loaded IS 'Total cash paid by patient to load points';
COMMENT ON COLUMN patient_loyalty_wallet.total_bonus_points IS 'Total bonus points received (e.g., pay ₹11K get 15K points = 4K bonus)';

CREATE INDEX idx_wallet_patient ON patient_loyalty_wallet(patient_id);
CREATE INDEX idx_wallet_hospital ON patient_loyalty_wallet(hospital_id);
CREATE INDEX idx_wallet_status ON patient_loyalty_wallet(is_active, wallet_status);

-- ============================================================================
-- 2. WALLET TRANSACTION LOG TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS wallet_transaction (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES patient_loyalty_wallet(wallet_id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL,  -- 'load', 'redeem', 'refund_service', 'refund_wallet', 'expire', 'adjustment'
    transaction_date TIMESTAMP DEFAULT NOW() NOT NULL,

    -- For 'load' transactions (patient loads points)
    amount_paid NUMERIC(12,2),              -- Actual cash received
    base_points INTEGER,                     -- Points equivalent to amount paid
    bonus_points INTEGER DEFAULT 0,          -- Extra points (promotional bonus)
    total_points_loaded INTEGER,             -- base_points + bonus_points
    expiry_date DATE,                        -- When these points expire (12 months from load)

    -- For 'redeem' transactions (patient uses points)
    points_redeemed INTEGER,                 -- Points deducted
    redemption_value NUMERIC(12,2),          -- ₹ value of redeemed points
    invoice_id UUID REFERENCES invoice(invoice_id),
    invoice_number VARCHAR(50),

    -- For 'refund_service' transactions (service canceled, points credited back)
    points_credited_back INTEGER,            -- Points returned to wallet
    refund_reason TEXT,
    original_transaction_id UUID REFERENCES wallet_transaction(transaction_id),

    -- For 'refund_wallet' transactions (close wallet, refund cash)
    wallet_closure_amount NUMERIC(12,2),     -- Cash refunded to patient
    points_forfeited INTEGER,                -- Bonus points lost on closure

    -- Balance tracking
    balance_before INTEGER,
    balance_after INTEGER,

    -- Payment tracking (for load transactions)
    payment_mode VARCHAR(50),  -- 'cash', 'card', 'upi', 'netbanking'
    payment_reference VARCHAR(100),

    -- Accounting link
    journal_entry_id UUID,

    -- Audit fields
    created_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    notes TEXT,

    -- Constraints
    CONSTRAINT check_wallet_txn_type CHECK (
        transaction_type IN ('load', 'redeem', 'refund_service', 'refund_wallet', 'expire', 'adjustment')
    ),
    CONSTRAINT check_wallet_balance_after CHECK (balance_after >= 0)
);

COMMENT ON TABLE wallet_transaction IS 'Complete audit log of all wallet transactions (loads, redemptions, refunds, expiries)';
COMMENT ON COLUMN wallet_transaction.transaction_type IS 'Type: load (add points), redeem (use points), refund_service (credit back), refund_wallet (close & refund), expire (auto-expire), adjustment (manual correction)';
COMMENT ON COLUMN wallet_transaction.bonus_points IS 'Promotional bonus (e.g., pay ₹11,000 get 4,000 extra points)';

CREATE INDEX idx_wallet_txn_wallet ON wallet_transaction(wallet_id, transaction_date DESC);
CREATE INDEX idx_wallet_txn_type ON wallet_transaction(transaction_type);
CREATE INDEX idx_wallet_txn_invoice ON wallet_transaction(invoice_id);
CREATE INDEX idx_wallet_txn_date ON wallet_transaction(transaction_date DESC);

-- ============================================================================
-- 3. WALLET POINTS BATCH TABLE (FIFO Tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS wallet_points_batch (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID NOT NULL REFERENCES patient_loyalty_wallet(wallet_id) ON DELETE CASCADE,
    load_transaction_id UUID NOT NULL REFERENCES wallet_transaction(transaction_id),

    -- Points tracking
    points_loaded INTEGER NOT NULL,          -- Original points in this batch
    points_remaining INTEGER NOT NULL,       -- Current balance of this batch
    points_redeemed INTEGER DEFAULT 0 NOT NULL,       -- Points used from this batch
    points_expired INTEGER DEFAULT 0 NOT NULL,        -- Points that expired

    -- Expiry management
    load_date DATE NOT NULL,
    expiry_date DATE NOT NULL,               -- 12 months from load_date
    is_expired BOOLEAN DEFAULT FALSE NOT NULL,
    expired_at TIMESTAMP,

    -- FIFO tracking
    batch_sequence INTEGER NOT NULL,         -- For FIFO order (lower = older)

    created_at TIMESTAMP DEFAULT NOW() NOT NULL,

    -- Constraints
    CONSTRAINT check_batch_points_remaining CHECK (points_remaining >= 0),
    CONSTRAINT check_batch_points_balance CHECK (
        points_loaded = points_remaining + points_redeemed + points_expired
    )
);

COMMENT ON TABLE wallet_points_batch IS 'Tracks points by load batch for FIFO redemption and expiry management';
COMMENT ON COLUMN wallet_points_batch.batch_sequence IS 'Sequence number for FIFO (lower number = loaded earlier = redeemed first)';
COMMENT ON COLUMN wallet_points_batch.expiry_date IS 'Points expire 12 months after load date';

CREATE INDEX idx_points_batch_wallet ON wallet_points_batch(wallet_id, batch_sequence);
CREATE INDEX idx_points_batch_expiry ON wallet_points_batch(wallet_id, expiry_date, is_expired);
CREATE INDEX idx_points_batch_fifo ON wallet_points_batch(wallet_id, is_expired, points_remaining, batch_sequence);

-- ============================================================================
-- 4. INVOICE TABLE ENHANCEMENTS
-- ============================================================================
-- Add wallet payment support to existing invoice table
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS payment_split JSONB;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS points_redeemed INTEGER DEFAULT 0;
ALTER TABLE invoice ADD COLUMN IF NOT EXISTS wallet_transaction_id UUID REFERENCES wallet_transaction(transaction_id);

COMMENT ON COLUMN invoice.payment_split IS 'JSON: {"points": 10000, "cash": 5000, "card": 3000} for partial payments';
COMMENT ON COLUMN invoice.points_redeemed IS 'Total loyalty points used for this invoice';
COMMENT ON COLUMN invoice.wallet_transaction_id IS 'Link to wallet redemption transaction';

CREATE INDEX IF NOT EXISTS idx_invoice_wallet_txn ON invoice(wallet_transaction_id);
CREATE INDEX IF NOT EXISTS idx_invoice_points_redeemed ON invoice(points_redeemed) WHERE points_redeemed > 0;

-- ============================================================================
-- 5. SAMPLE DATA (Optional - for testing)
-- ============================================================================
-- Uncomment to insert sample loyalty card types if not exists
/*
INSERT INTO loyalty_card_type (card_type_id, card_type_code, card_type_name, discount_percent, card_color, min_lifetime_spend, min_visits, is_active)
VALUES
    (gen_random_uuid(), 'SILVER', 'Silver Member', 5.00, '#C0C0C0', 10000, 5, true),
    (gen_random_uuid(), 'GOLD', 'Gold Member', 10.00, '#FFD700', 50000, 20, true),
    (gen_random_uuid(), 'PLATINUM', 'Platinum Member', 15.00, '#E5E4E2', 100000, 50, true)
ON CONFLICT (card_type_code) DO NOTHING;
*/

-- ============================================================================
-- 6. TRIGGERS FOR AUTO-UPDATE
-- ============================================================================

-- Trigger to update wallet updated_at timestamp
CREATE OR REPLACE FUNCTION update_wallet_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_wallet_updated_at
    BEFORE UPDATE ON patient_loyalty_wallet
    FOR EACH ROW
    EXECUTE FUNCTION update_wallet_timestamp();

-- ============================================================================
-- 7. HELPFUL VIEWS
-- ============================================================================

-- View: Active wallets with expiring points
CREATE OR REPLACE VIEW v_wallet_expiring_soon AS
SELECT
    w.wallet_id,
    w.patient_id,
    p.patient_name,
    p.mobile,
    w.points_balance as total_points,
    SUM(b.points_remaining) as points_expiring_30days,
    MIN(b.expiry_date) as nearest_expiry_date
FROM patient_loyalty_wallet w
JOIN patient p ON w.patient_id = p.patient_id
LEFT JOIN wallet_points_batch b ON w.wallet_id = b.wallet_id
WHERE w.is_active = TRUE
  AND b.is_expired = FALSE
  AND b.points_remaining > 0
  AND b.expiry_date <= CURRENT_DATE + INTERVAL '30 days'
GROUP BY w.wallet_id, w.patient_id, p.patient_name, p.mobile, w.points_balance
HAVING SUM(b.points_remaining) > 0;

COMMENT ON VIEW v_wallet_expiring_soon IS 'Patients with points expiring in next 30 days (for notification)';

-- View: Wallet liability summary (for accounts)
CREATE OR REPLACE VIEW v_wallet_liability_summary AS
SELECT
    h.hospital_id,
    h.hospital_name,
    COUNT(DISTINCT w.wallet_id) as active_wallets,
    SUM(w.points_balance) as total_points_outstanding,
    SUM(w.points_value) as total_liability_rupees,
    SUM(w.total_amount_loaded) as total_cash_collected,
    SUM(w.total_points_redeemed) as total_points_redeemed,
    SUM(w.total_bonus_points) as total_bonus_issued
FROM hospital h
LEFT JOIN patient_loyalty_wallet w ON h.hospital_id = w.hospital_id AND w.is_active = TRUE
GROUP BY h.hospital_id, h.hospital_name;

COMMENT ON VIEW v_wallet_liability_summary IS 'Hospital-wise wallet liability for accounting and reporting';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Next steps:
-- 1. Run this migration: psql -h localhost -U postgres -d skinspire_dev -f 20251121_create_loyalty_wallet_system.sql
-- 2. Verify tables: \dt patient_loyalty_wallet wallet_transaction wallet_points_batch
-- 3. Check views: \dv v_wallet_*
-- 4. Proceed with backend service implementation (WalletService class)
