-- MIGRATION: Ram Kumar from OLD loyalty system → NEW wallet system
-- Date: 2025-11-24
-- Purpose: Migrate existing loyalty data to new wallet system

BEGIN;

-- Step 1: Migrate Ram Kumar to NEW wallet system
INSERT INTO patient_loyalty_wallet (
    wallet_id,
    hospital_id,
    patient_id,
    card_type_id,
    points_balance,
    points_value,
    total_points_loaded,
    total_points_redeemed,
    total_bonus_points,
    total_amount_loaded,
    wallet_status,
    is_active,
    created_at,
    updated_at,
    created_by
)
SELECT
    gen_random_uuid() as wallet_id,
    plc.hospital_id,
    plc.patient_id,
    plc.card_type_id,
    COALESCE(lp.points, 0) as points_balance,  -- Current balance from loyalty_points
    lp.points_value as points_value,  -- ₹ value of points
    COALESCE(lp.points, 0) as total_points_loaded,
    0 as total_points_redeemed,  -- No redemptions yet
    lp.points - FLOOR(lp.points_value) as total_bonus_points,  -- 8000 - 5000 = 3000 bonus
    lp.points_value as total_amount_loaded,  -- ₹5000 paid
    'active' as wallet_status,
    true as is_active,
    plc.created_at,
    CURRENT_TIMESTAMP,
    plc.created_by
FROM patient_loyalty_cards plc
JOIN loyalty_points lp ON plc.patient_id = lp.patient_id
JOIN loyalty_card_types lct ON plc.card_type_id = lct.card_type_id
WHERE plc.patient_id = (
    SELECT patient_id FROM patients WHERE full_name = 'Ram Kumar'
)
AND plc.is_active = true
AND plc.is_deleted = false
AND lp.transaction_type = 'CREDIT';

-- Step 2: Create wallet transaction (load)
INSERT INTO wallet_transaction (
    transaction_id,
    wallet_id,
    transaction_type,
    transaction_date,
    total_points_loaded,
    base_points,
    bonus_points,
    balance_before,
    balance_after,
    payment_mode,
    amount_paid,
    payment_reference,
    notes,
    created_by,
    created_at
)
SELECT
    gen_random_uuid(),
    plw.wallet_id,
    'load' as transaction_type,
    lp.created_at as transaction_date,
    lp.points as total_points_loaded,
    FLOOR(lp.points_value) as base_points,  -- ₹5000 = 5000 base points
    lp.points - FLOOR(lp.points_value) as bonus_points,  -- 3000 bonus = 8000 - 5000
    0 as balance_before,
    lp.points as balance_after,
    'CREDIT' as payment_mode,
    lp.points_value as amount_paid,
    'MIGRATED_FROM_OLD_SYSTEM' as payment_reference,
    'Migrated from loyalty_points table (Nov 22, 2025)' as notes,
    COALESCE(lp.created_by, '0000000000') as created_by,
    lp.created_at
FROM patient_loyalty_wallet plw
JOIN loyalty_points lp ON plw.patient_id = lp.patient_id
WHERE plw.patient_id = (
    SELECT patient_id FROM patients WHERE full_name = 'Ram Kumar'
)
AND lp.transaction_type = 'CREDIT';

-- Step 3: Create wallet points batch (for FIFO tracking)
INSERT INTO wallet_points_batch (
    batch_id,
    wallet_id,
    load_transaction_id,
    points_loaded,
    points_remaining,
    points_redeemed,
    points_expired,
    load_date,
    expiry_date,
    batch_sequence,
    is_expired
)
SELECT
    gen_random_uuid(),
    plw.wallet_id,
    wt.transaction_id as load_transaction_id,
    lp.points as points_loaded,
    lp.points as points_remaining,  -- No redemptions yet
    0 as points_redeemed,
    0 as points_expired,
    lp.created_at::date as load_date,
    lp.expiry_date as expiry_date,
    1 as batch_sequence,  -- First batch
    false as is_expired
FROM patient_loyalty_wallet plw
JOIN loyalty_points lp ON plw.patient_id = lp.patient_id
JOIN wallet_transaction wt ON wt.wallet_id = plw.wallet_id
WHERE plw.patient_id = (
    SELECT patient_id FROM patients WHERE full_name = 'Ram Kumar'
)
AND lp.transaction_type = 'CREDIT';

-- Verification query
SELECT
    'Migration Verification' as info,
    p.full_name,
    plw.wallet_id,
    plw.points_balance,
    plw.total_amount_loaded,
    lct.card_type_name as tier,
    lct.discount_percent as tier_discount,
    plw.wallet_status as status,
    wpb.points_loaded as batch_points,
    wpb.expiry_date as batch_expiry,
    wt.transaction_type,
    wt.total_points_loaded as txn_points
FROM patient_loyalty_wallet plw
JOIN patients p ON plw.patient_id = p.patient_id
JOIN loyalty_card_types lct ON plw.card_type_id = lct.card_type_id
LEFT JOIN wallet_points_batch wpb ON wpb.wallet_id = plw.wallet_id
LEFT JOIN wallet_transaction wt ON wt.wallet_id = plw.wallet_id
WHERE p.full_name = 'Ram Kumar';

COMMIT;
