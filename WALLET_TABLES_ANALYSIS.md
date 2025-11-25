# Wallet & Loyalty Tables - Duplication Analysis

**Date**: November 24, 2025
**Analysis**: Comparing old vs new loyalty/wallet table structures

---

## Executive Summary

**VERDICT**: YES, there is significant duplication. We have TWO separate systems:

1. **OLD SYSTEM** (loyalty_points, loyalty_redemptions, patient_loyalty_cards) - Simple point tracking
2. **NEW SYSTEM** (patient_loyalty_wallet, wallet_points_batch, wallet_transaction) - Advanced wallet with FIFO, tiers, expiry

**RECOMMENDATION**: Keep NEW system, deprecate OLD system (or migrate data if it exists).

---

## Table Comparison

### 1. OLD SYSTEM - Simple Loyalty Points

#### `loyalty_points`
**Purpose**: Track individual point transactions (loads)
**Key Fields**:
- `point_id` (UUID)
- `patient_id`, `hospital_id`
- `points` (integer)
- `transaction_type` (varchar)
- `points_value` (numeric)
- `expiry_date`
- `reference_id`

**Design**: Each row = one point load transaction

#### `loyalty_redemptions`
**Purpose**: Track point redemptions separately
**Key Fields**:
- `redemption_id` (UUID)
- `patient_id`, `hospital_id`
- `point_id` (FK to loyalty_points)
- `payment_id` (FK to payment_details)
- `points_redeemed`
- `amount_credited`
- `redemption_date`

**Design**: Each row = one redemption transaction

#### `patient_loyalty_cards`
**Purpose**: Track issued loyalty cards (physical/virtual cards)
**Key Fields**:
- `patient_card_id` (UUID)
- `patient_id`, `hospital_id`
- `card_type_id` (FK to loyalty_card_types)
- `card_number` (varchar - unique)
- `issue_date`, `expiry_date`
- `is_active`

**Design**: One card per patient per tier (UK constraint)

---

### 2. NEW SYSTEM - Advanced Wallet with FIFO

#### `patient_loyalty_wallet`
**Purpose**: Single wallet per patient with balance tracking
**Key Fields**:
- `wallet_id` (UUID)
- `patient_id`, `hospital_id`
- `card_type_id` (current tier)
- `points_balance` (current available)
- `total_points_loaded` (lifetime loaded)
- `total_points_redeemed` (lifetime redeemed)
- `total_points_expired` (lifetime expired)
- `total_amount_loaded` (₹ paid)
- `wallet_status` (active/suspended/closed)
- `tier_discount_percent` (service discount)

**Design**: ONE wallet per patient (UK constraint)

#### `wallet_points_batch`
**Purpose**: FIFO batch tracking for point expiry
**Key Fields**:
- `batch_id` (UUID)
- `wallet_id` (FK to patient_loyalty_wallet)
- `load_transaction_id` (FK to wallet_transaction)
- `points_loaded` (initial)
- `points_remaining` (current)
- `points_redeemed` (consumed)
- `points_expired` (expired)
- `load_date`, `expiry_date`
- `batch_sequence` (FIFO order)
- `is_expired`

**Design**: One batch per load transaction
**Check Constraint**: `points_loaded = points_remaining + points_redeemed + points_expired`

#### `wallet_transaction`
**Purpose**: Complete transaction log (load/redeem/refund/expire/adjust)
**Key Fields**:
- `transaction_id` (UUID)
- `wallet_id` (FK to patient_loyalty_wallet)
- `transaction_type` (load/redeem/refund_service/refund_wallet/expire/adjustment)
- `transaction_date`
- `total_points_loaded` (for loads)
- `base_points` (from payment)
- `bonus_points` (from tier bonus)
- `points_redeemed` (for redemptions)
- `balance_before`, `balance_after`
- `invoice_id`, `payment_id`, `payment_reference`
- `payment_mode`, `payment_amount`
- `notes`

**Design**: Complete audit trail of all wallet activity

---

### 3. SHARED TABLES

#### `loyalty_card_types`
**Purpose**: Define available tiers (Silver/Gold/Platinum)
**Used By**: BOTH systems
**Key Fields**:
- `card_type_id` (UUID)
- `card_type_code` (SILVER/GOLD/PLATINUM)
- `min_payment_amount` (₹22000/45000/92000)
- `total_points_credited` (25000/50000/100000)
- `bonus_percentage` (13.64%/11.11%/8.70%)
- `discount_percent` (2%/3%/5% service discount)
- `validity_months` (12)

**Design**: One set of tiers per hospital

#### `loyalty_card_tier_history`
**Purpose**: Track tier upgrades/downgrades
**Used By**: BOTH systems
**Key Fields**:
- `patient_id`, `hospital_id`
- `card_type_id` (new tier)
- `previous_card_type_id`
- `change_type` (upgrade/downgrade/new/renewal)
- `change_date`
- `reason`

---

## Functional Overlap

| Functionality | OLD System | NEW System | Winner |
|---------------|-----------|------------|--------|
| **Point Loads** | loyalty_points | wallet_transaction (type='load') | NEW (more detailed) |
| **Point Redemptions** | loyalty_redemptions | wallet_transaction (type='redeem') | NEW (more detailed) |
| **Point Balance** | SUM(loyalty_points) - SUM(loyalty_redemptions) | patient_loyalty_wallet.points_balance | NEW (denormalized, faster) |
| **FIFO Expiry** | ❌ NOT SUPPORTED | wallet_points_batch ✅ | NEW |
| **Refunds** | ❌ NOT SUPPORTED | wallet_transaction (type='refund_*') ✅ | NEW |
| **Adjustments** | ❌ NOT SUPPORTED | wallet_transaction (type='adjustment') ✅ | NEW |
| **Batch Tracking** | ❌ NOT SUPPORTED | wallet_points_batch ✅ | NEW |
| **Tier Assignment** | patient_loyalty_cards | patient_loyalty_wallet.card_type_id | BOTH (redundant) |
| **Transaction Log** | loyalty_points + loyalty_redemptions | wallet_transaction | NEW (unified) |
| **Balance Tracking** | Calculated on-the-fly | Denormalized in wallet | NEW (performance) |

---

## Data Integrity Issues

### OLD System Issues:
1. **No FIFO tracking** - Cannot determine which points expire first
2. **No batch concept** - All points treated equally
3. **Split tables** - Loads in one table, redemptions in another (complexity)
4. **No refund support** - Cannot reverse transactions
5. **No adjustment support** - Cannot fix errors
6. **Performance** - Must SUM() multiple tables to get balance
7. **No wallet status** - Cannot suspend/close wallet
8. **No tier discount tracking** - Discount stored separately

### NEW System Advantages:
1. ✅ **FIFO batches** - Points expire in order loaded
2. ✅ **Unified transactions** - All activity in one table
3. ✅ **Denormalized balance** - Fast balance queries
4. ✅ **Check constraints** - Data integrity enforced at DB level
5. ✅ **Complete audit trail** - All transactions logged
6. ✅ **Refund support** - Service and wallet refunds
7. ✅ **Wallet lifecycle** - active/suspended/closed status
8. ✅ **Tier integration** - Discount stored in wallet record

---

## Redundancy Analysis

### `patient_loyalty_cards` vs `patient_loyalty_wallet`

**REDUNDANT**: Both tables store:
- Patient's current tier (`card_type_id`)
- Activation status (`is_active` vs `wallet_status`)

**Difference**:
- `patient_loyalty_cards`: Focuses on "card" concept (card_number, issue_date)
- `patient_loyalty_wallet`: Focuses on "wallet" concept (balance, transactions)

**Which to Keep?**
- **Keep**: `patient_loyalty_wallet` (more comprehensive)
- **Deprecate**: `patient_loyalty_cards` (redundant if wallet exists)
- **Exception**: If you issue physical cards with printed card numbers, keep both

---

## Migration Strategy

### Option 1: Complete Migration (RECOMMENDED)
**Migrate all data from OLD to NEW system:**

```sql
-- Step 1: Migrate active loyalty cards to wallets
INSERT INTO patient_loyalty_wallet (
    wallet_id, hospital_id, patient_id, card_type_id,
    points_balance, total_points_loaded, total_points_redeemed,
    total_points_expired, total_amount_loaded,
    wallet_status, tier_discount_percent,
    created_at, updated_at
)
SELECT
    gen_random_uuid(),
    plc.hospital_id,
    plc.patient_id,
    plc.card_type_id,
    COALESCE(points.total_points, 0) - COALESCE(redemptions.total_redeemed, 0) as points_balance,
    COALESCE(points.total_points, 0),
    COALESCE(redemptions.total_redeemed, 0),
    0, -- expired points (not tracked in old system)
    0, -- amount loaded (not tracked in old system)
    CASE WHEN plc.is_active THEN 'active' ELSE 'suspended' END,
    lct.discount_percent,
    plc.created_at,
    CURRENT_TIMESTAMP
FROM patient_loyalty_cards plc
LEFT JOIN (
    SELECT patient_id, SUM(points) as total_points
    FROM loyalty_points
    WHERE is_active = true
    GROUP BY patient_id
) points ON plc.patient_id = points.patient_id
LEFT JOIN (
    SELECT patient_id, SUM(points_redeemed) as total_redeemed
    FROM loyalty_redemptions
    GROUP BY patient_id
) redemptions ON plc.patient_id = redemptions.patient_id
LEFT JOIN loyalty_card_types lct ON plc.card_type_id = lct.card_type_id
WHERE plc.is_active = true
  AND plc.is_deleted = false;

-- Step 2: Migrate load transactions
INSERT INTO wallet_transaction (
    transaction_id, wallet_id, transaction_type,
    transaction_date, total_points_loaded,
    base_points, bonus_points, balance_after,
    notes, created_at
)
SELECT
    gen_random_uuid(),
    plw.wallet_id,
    'load',
    lp.created_at,
    lp.points,
    lp.points,
    0,
    0, -- will need to recalculate
    'Migrated from old loyalty_points system',
    lp.created_at
FROM loyalty_points lp
JOIN patient_loyalty_wallet plw ON lp.patient_id = plw.patient_id
WHERE lp.is_active = true;

-- Step 3: Migrate redemption transactions
INSERT INTO wallet_transaction (
    transaction_id, wallet_id, transaction_type,
    transaction_date, points_redeemed, balance_after,
    payment_id, notes, created_at
)
SELECT
    gen_random_uuid(),
    plw.wallet_id,
    'redeem',
    lr.redemption_date,
    lr.points_redeemed,
    0, -- will need to recalculate
    lr.payment_id,
    'Migrated from old loyalty_redemptions system',
    lr.created_at
FROM loyalty_redemptions lr
JOIN patient_loyalty_wallet plw ON lr.patient_id = plw.patient_id;

-- Step 4: Deprecate old tables (soft delete)
ALTER TABLE loyalty_points RENAME TO loyalty_points_deprecated;
ALTER TABLE loyalty_redemptions RENAME TO loyalty_redemptions_deprecated;
ALTER TABLE patient_loyalty_cards RENAME TO patient_loyalty_cards_deprecated;

-- Step 5: Create batches for migrated points (all in one batch per patient)
-- NOTE: This loses FIFO granularity - all old points in one batch
INSERT INTO wallet_points_batch (
    batch_id, wallet_id, load_transaction_id,
    points_loaded, points_remaining,
    points_redeemed, points_expired,
    load_date, expiry_date,
    batch_sequence, is_expired
)
SELECT
    gen_random_uuid(),
    plw.wallet_id,
    (SELECT transaction_id FROM wallet_transaction wt
     WHERE wt.wallet_id = plw.wallet_id
     AND wt.transaction_type = 'load'
     ORDER BY wt.transaction_date LIMIT 1), -- first load transaction
    plw.total_points_loaded,
    plw.points_balance,
    plw.total_points_redeemed,
    0,
    CURRENT_DATE - INTERVAL '1 month', -- load date (estimate)
    CURRENT_DATE + INTERVAL '11 months', -- expiry date (12 months validity)
    1,
    false
FROM patient_loyalty_wallet plw
WHERE plw.points_balance > 0;
```

### Option 2: Dual System (NOT RECOMMENDED)
- Keep both systems running
- Use NEW system for all new transactions
- OLD system read-only for historical reference
- **Problem**: Complexity, data inconsistency risk

### Option 3: Fresh Start (SIMPLEST)
- Mark old tables as deprecated (rename with _deprecated suffix)
- Start NEW system from scratch
- No migration (clean slate)
- **Best for**: If old data is minimal or test data only

---

## Recommendation

### Immediate Actions:

1. **Check if OLD system has real data:**
```sql
SELECT
    (SELECT COUNT(*) FROM loyalty_points) as old_points,
    (SELECT COUNT(*) FROM loyalty_redemptions) as old_redemptions,
    (SELECT COUNT(*) FROM patient_loyalty_cards) as old_cards,
    (SELECT COUNT(*) FROM patient_loyalty_wallet) as new_wallets,
    (SELECT COUNT(*) FROM wallet_transaction) as new_transactions;
```

2. **If OLD system is empty or test data only:**
   - **Action**: Drop old tables (after backup)
   - **Benefit**: Clean database, no confusion

3. **If OLD system has production data:**
   - **Action**: Run migration script (Option 1)
   - **Benefit**: Preserve history, upgrade to better system

4. **Deprecate `patient_loyalty_cards`** (unless physical cards needed):
   - Already tracked in `patient_loyalty_wallet.card_type_id`
   - If card numbers needed, keep table but mark as reference only

---

## Tables to Keep

### ✅ KEEP (NEW SYSTEM - PRODUCTION READY):
1. `patient_loyalty_wallet` - Core wallet entity
2. `wallet_points_batch` - FIFO batch tracking
3. `wallet_transaction` - Complete transaction log
4. `loyalty_card_types` - Tier definitions (shared)
5. `loyalty_card_tier_history` - Tier change history (shared)

### ❓ CONDITIONAL:
6. `patient_loyalty_cards` - Only if physical card numbers needed

### ❌ DEPRECATE (OLD SYSTEM - REDUNDANT):
7. `loyalty_points` - Replaced by wallet_transaction (type='load')
8. `loyalty_redemptions` - Replaced by wallet_transaction (type='redeem')

---

## Database Cleanup Script

```sql
-- Check data counts first
SELECT
    'loyalty_points' as table_name, COUNT(*) as row_count FROM loyalty_points
UNION ALL
SELECT 'loyalty_redemptions', COUNT(*) FROM loyalty_redemptions
UNION ALL
SELECT 'patient_loyalty_cards', COUNT(*) FROM patient_loyalty_cards
UNION ALL
SELECT 'patient_loyalty_wallet', COUNT(*) FROM patient_loyalty_wallet
UNION ALL
SELECT 'wallet_transaction', COUNT(*) FROM wallet_transaction
UNION ALL
SELECT 'wallet_points_batch', COUNT(*) FROM wallet_points_batch;

-- If old tables are empty, drop them
-- BACKUP FIRST!

-- Step 1: Drop foreign key constraints
ALTER TABLE loyalty_redemptions DROP CONSTRAINT loyalty_redemptions_point_id_fkey;
ALTER TABLE payment_details DROP CONSTRAINT payment_details_loyalty_redemption_id_fkey;

-- Step 2: Drop old tables
DROP TABLE IF EXISTS loyalty_redemptions;
DROP TABLE IF EXISTS loyalty_points;

-- Step 3: Optionally drop patient_loyalty_cards if not using physical cards
-- DROP TABLE IF EXISTS patient_loyalty_cards;
```

---

## Summary

**YES, there is duplication.** You have TWO loyalty systems:

1. **OLD**: loyalty_points + loyalty_redemptions + patient_loyalty_cards (basic point tracking)
2. **NEW**: patient_loyalty_wallet + wallet_points_batch + wallet_transaction (advanced wallet with FIFO)

**The NEW system is superior** because it supports:
- FIFO point expiry with batch tracking
- Unified transaction log
- Fast balance queries (denormalized)
- Refunds and adjustments
- Wallet lifecycle management
- Integrated tier discounts

**Recommendation**:
- Check if OLD system has production data
- If yes: Migrate to NEW system
- If no: Drop OLD tables
- Keep NEW system as the single source of truth
- Optionally keep patient_loyalty_cards if physical card numbers are needed

---

**Next Step**: Let me know if you want me to:
1. Check data counts in old vs new tables
2. Generate migration script
3. Drop old tables (if empty)
4. Keep both (not recommended)
