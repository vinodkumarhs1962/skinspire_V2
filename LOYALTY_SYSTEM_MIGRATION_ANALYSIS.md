# Loyalty System Migration Analysis - OLD vs NEW

**Date**: November 24, 2025
**Critical Finding**: Discount system currently uses OLD loyalty tables
**Action Required**: Update discount logic to use NEW wallet system

---

## Executive Summary

**CRITICAL ISSUE FOUND**: Your discount system (`discount_service.py`) currently queries the **OLD** `patient_loyalty_cards` table to determine if a patient has a loyalty card and what tier/discount they get.

**Impact**: If we deprecate the OLD system without updating the discount logic, **loyalty discounts will stop working entirely**.

**Solution**: Update `discount_service.py` to query the **NEW** `patient_loyalty_wallet` table instead of `patient_loyalty_cards`.

---

## Current Discount System Usage

### Files Using OLD Loyalty System:

1. **`app/services/discount_service.py`** (Lines 306-452)
   - `calculate_loyalty_percentage_discount()` - Lines 306-384
   - `calculate_loyalty_discount()` - Lines 387-452

2. **`app/api/routes/discount_api.py`** (Line 449-451)
   - Loyalty card check in API endpoint

### Specific Code Using OLD System:

```python
# FROM: discount_service.py lines 306-321
patient_card = session.query(PatientLoyaltyCard).join(
    LoyaltyCardType
).filter(
    and_(
        PatientLoyaltyCard.patient_id == patient_id,
        PatientLoyaltyCard.hospital_id == hospital_id,
        PatientLoyaltyCard.is_active == True,
        PatientLoyaltyCard.is_deleted == False,
        LoyaltyCardType.is_active == True,
        LoyaltyCardType.is_deleted == False,
        or_(
            PatientLoyaltyCard.expiry_date.is_(None),
            PatientLoyaltyCard.expiry_date >= date.today()
        )
    )
).first()

if not patient_card or not patient_card.card_type:
    return None

card_type = patient_card.card_type
discount_percent = card_type.discount_percent  # ← Uses card_type.discount_percent
```

**Problem**: This queries `patient_loyalty_cards` table which we want to deprecate!

---

## NEW System Equivalent

In the NEW wallet system, the same information is stored in `patient_loyalty_wallet`:

```sql
-- OLD way (current)
SELECT plc.card_type_id, lct.discount_percent
FROM patient_loyalty_cards plc
JOIN loyalty_card_types lct ON plc.card_type_id = lct.card_type_id
WHERE plc.patient_id = ?
  AND plc.is_active = true
  AND plc.is_deleted = false;

-- NEW way (should be)
SELECT wallet_id, card_type_id, tier_discount_percent
FROM patient_loyalty_wallet
WHERE patient_id = ?
  AND wallet_status = 'active'
  AND is_deleted = false;
```

**Advantage of NEW system**:
- Discount percent stored directly in wallet (`tier_discount_percent`)
- No need to join to `loyalty_card_types` table
- Single source of truth for patient's current tier and discount

---

## Required Code Changes

### 1. Update `discount_service.py` - Two Functions

#### Function 1: `calculate_loyalty_percentage_discount()` (Lines 273-384)

**BEFORE** (current - uses OLD system):
```python
# Check if patient has active loyalty card
patient_card = session.query(PatientLoyaltyCard).join(
    LoyaltyCardType
).filter(
    and_(
        PatientLoyaltyCard.patient_id == patient_id,
        PatientLoyaltyCard.hospital_id == hospital_id,
        PatientLoyaltyCard.is_active == True,
        PatientLoyaltyCard.is_deleted == False,
        LoyaltyCardType.is_active == True,
        LoyaltyCardType.is_deleted == False,
        or_(
            PatientLoyaltyCard.expiry_date.is_(None),
            PatientLoyaltyCard.expiry_date >= date.today()
        )
    )
).first()

if not patient_card or not patient_card.card_type:
    return None

# ... discount calculation using card_type.discount_percent
```

**AFTER** (updated - uses NEW system):
```python
from app.models.transaction import PatientLoyaltyWallet

# Check if patient has active wallet
patient_wallet = session.query(PatientLoyaltyWallet).join(
    LoyaltyCardType, PatientLoyaltyWallet.card_type_id == LoyaltyCardType.card_type_id
).filter(
    and_(
        PatientLoyaltyWallet.patient_id == patient_id,
        PatientLoyaltyWallet.hospital_id == hospital_id,
        PatientLoyaltyWallet.wallet_status == 'active',
        PatientLoyaltyWallet.is_deleted == False,
        LoyaltyCardType.is_active == True,
        LoyaltyCardType.is_deleted == False
    )
).first()

if not patient_wallet or not patient_wallet.card_type:
    return None

# Use wallet's tier_discount_percent (already denormalized)
card_type = patient_wallet.card_type
discount_percent = patient_wallet.tier_discount_percent  # ← Use wallet column directly

# ... rest of discount calculation
```

#### Function 2: `calculate_loyalty_discount()` (Lines 387-452)

**Same change**: Replace `PatientLoyaltyCard` query with `PatientLoyaltyWallet` query.

**BEFORE**:
```python
patient_card = session.query(PatientLoyaltyCard).join(...)
if not patient_card or not patient_card.card_type:
    return None
card_type = patient_card.card_type
discount_percent = float(card_type.discount_percent)
```

**AFTER**:
```python
patient_wallet = session.query(PatientLoyaltyWallet).join(...)
if not patient_wallet or not patient_wallet.card_type:
    return None
# Use tier_discount_percent from wallet
discount_percent = float(patient_wallet.tier_discount_percent)
```

---

### 2. Update `discount_api.py`

**File**: `app/api/routes/discount_api.py`

**Find and replace**: Same pattern as above - change `PatientLoyaltyCard` to `PatientLoyaltyWallet`.

---

### 3. Update Model Imports

**In `discount_service.py` (Line 16)**:

**BEFORE**:
```python
from app.models.master import (
    Service, Hospital, Medicine, Package, LoyaltyCardType, PatientLoyaltyCard,
    DiscountApplicationLog, PromotionCampaign, PromotionUsageLog
)
```

**AFTER**:
```python
from app.models.master import (
    Service, Hospital, Medicine, Package, LoyaltyCardType,
    DiscountApplicationLog, PromotionCampaign, PromotionUsageLog
)
from app.models.transaction import PatientLoyaltyWallet  # NEW import
```

---

## Benefits of Migration

### 1. **Single Source of Truth**
- Patient's tier stored in ONE place (`patient_loyalty_wallet.card_type_id`)
- No need to sync between `patient_loyalty_cards` and `patient_loyalty_wallet`

### 2. **Denormalized Discount Percent**
- `patient_loyalty_wallet.tier_discount_percent` already cached
- No need to join to `loyalty_card_types` for every discount calculation
- **Performance improvement**: One less table join

### 3. **Better Business Logic**
- Wallet status (`active/suspended/closed`) controls all wallet features
- If wallet is closed, no discounts apply (automatic)
- Expiry logic built into wallet status

### 4. **Cleaner Database**
- Remove redundant `patient_loyalty_cards` table
- Remove redundant `loyalty_points` and `loyalty_redemptions` tables
- All loyalty tracking in ONE cohesive system

---

## Testing Requirements

After updating the discount logic, test these scenarios:

### Test 1: Loyalty Discount on Service Invoice
1. Create patient with active wallet (Silver tier - 2% discount)
2. Create service invoice
3. Verify discount_service.calculate_loyalty_discount() returns 2%
4. Verify discount applied correctly on invoice

### Test 2: Loyalty + Bulk Discount (Absolute Mode)
1. Patient with Gold tier (3% loyalty)
2. Invoice with 5 services (bulk discount eligible - 5%)
3. Hospital.loyalty_discount_mode = 'absolute'
4. Expected: 5% bulk discount (higher wins)

### Test 3: Loyalty + Bulk Discount (Additional Mode)
1. Patient with Platinum tier (5% loyalty)
2. Invoice with 5 services (bulk discount - 5%)
3. Hospital.loyalty_discount_mode = 'additional'
4. Expected: 10% combined (5% + 5%)

### Test 4: No Wallet = No Loyalty Discount
1. Patient without wallet
2. Create service invoice
3. Expected: No loyalty discount, only bulk/standard/promotion

### Test 5: Suspended Wallet = No Discount
1. Patient with wallet_status = 'suspended'
2. Create service invoice
3. Expected: No loyalty discount (wallet not active)

### Test 6: Closed Wallet = No Discount
1. Patient with wallet_status = 'closed'
2. Create service invoice
3. Expected: No loyalty discount

---

## Database Cleanup After Migration

Once discount logic is updated and tested:

### Step 1: Verify no code references OLD tables
```bash
# Search codebase for old table references
grep -r "PatientLoyaltyCard" app/
grep -r "LoyaltyPoint" app/
grep -r "LoyaltyRedemption" app/
```

### Step 2: Backup old tables
```sql
-- Create backup schema
CREATE SCHEMA IF NOT EXISTS deprecated_loyalty;

-- Move old tables to backup schema
ALTER TABLE patient_loyalty_cards SET SCHEMA deprecated_loyalty;
ALTER TABLE loyalty_points SET SCHEMA deprecated_loyalty;
ALTER TABLE loyalty_redemptions SET SCHEMA deprecated_loyalty;
```

### Step 3: Drop foreign key constraints
```sql
-- Drop constraints referencing old tables
ALTER TABLE discount_application_log
DROP CONSTRAINT IF EXISTS discount_application_log_card_type_id_fkey;

-- Add new constraint to wallet if needed
-- (discount_application_log should store card_type_id, not patient_card_id)
```

### Step 4: Optional - Drop old tables (after 30 days backup period)
```sql
-- Only after confirming NEW system works in production
DROP TABLE IF EXISTS deprecated_loyalty.loyalty_redemptions;
DROP TABLE IF EXISTS deprecated_loyalty.loyalty_points;
DROP TABLE IF EXISTS deprecated_loyalty.patient_loyalty_cards;
DROP SCHEMA IF EXISTS deprecated_loyalty;
```

---

## Implementation Checklist

- [ ] **Update discount_service.py**
  - [ ] Change `calculate_loyalty_percentage_discount()` to use `PatientLoyaltyWallet`
  - [ ] Change `calculate_loyalty_discount()` to use `PatientLoyaltyWallet`
  - [ ] Update model imports
  - [ ] Use `tier_discount_percent` instead of `card_type.discount_percent`

- [ ] **Update discount_api.py**
  - [ ] Change loyalty card check to query `PatientLoyaltyWallet`

- [ ] **Test discount logic**
  - [ ] Test 1: Basic loyalty discount (pass)
  - [ ] Test 2: Loyalty + Bulk absolute mode (pass)
  - [ ] Test 3: Loyalty + Bulk additional mode (pass)
  - [ ] Test 4: No wallet scenario (pass)
  - [ ] Test 5: Suspended wallet scenario (pass)
  - [ ] Test 6: Closed wallet scenario (pass)

- [ ] **Database cleanup** (after testing passes)
  - [ ] Backup old tables to deprecated schema
  - [ ] Verify no code references old tables
  - [ ] Drop old tables (after 30 days)

---

## Migration Script

Here's a complete SQL script to migrate Ram Kumar's data to NEW system:

```sql
-- MIGRATION: OLD loyalty system → NEW wallet system
-- Date: 2025-11-24
-- Affected: 1 patient (Ram Kumar)

BEGIN;

-- Step 1: Migrate Ram Kumar to NEW wallet system
INSERT INTO patient_loyalty_wallet (
    wallet_id,
    hospital_id,
    patient_id,
    card_type_id,
    points_balance,
    total_points_loaded,
    total_points_redeemed,
    total_points_expired,
    total_amount_loaded,
    wallet_status,
    tier_discount_percent,
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
    COALESCE(lp.points, 0) as total_points_loaded,
    0 as total_points_redeemed,  -- No redemptions yet
    0 as total_points_expired,
    lp.points_value as total_amount_loaded,  -- ₹5000 paid
    'active' as wallet_status,
    lct.discount_percent as tier_discount_percent,  -- Silver = 2%
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
AND plc.is_deleted = false;

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
    payment_amount,
    payment_reference,
    notes,
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
    lp.points_value as payment_amount,
    'MIGRATED_FROM_OLD_SYSTEM' as payment_reference,
    'Migrated from loyalty_points table (Nov 22, 2025)' as notes,
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

-- Step 4: Mark old tables as deprecated (don't delete yet)
COMMENT ON TABLE patient_loyalty_cards IS 'DEPRECATED - Use patient_loyalty_wallet instead';
COMMENT ON TABLE loyalty_points IS 'DEPRECATED - Use wallet_transaction instead';
COMMENT ON TABLE loyalty_redemptions IS 'DEPRECATED - Use wallet_transaction instead';

-- Verify migration
SELECT
    'NEW Wallet' as system,
    p.full_name,
    plw.points_balance,
    plw.total_amount_loaded,
    lct.card_type_name as tier,
    plw.tier_discount_percent as discount,
    plw.wallet_status as status
FROM patient_loyalty_wallet plw
JOIN patients p ON plw.patient_id = p.patient_id
JOIN loyalty_card_types lct ON plw.card_type_id = lct.card_type_id
WHERE p.full_name = 'Ram Kumar'

UNION ALL

SELECT
    'OLD Cards' as system,
    p.full_name,
    lp.points as points_balance,
    lp.points_value as amount_loaded,
    lct.card_type_name as tier,
    lct.discount_percent as discount,
    CASE WHEN plc.is_active THEN 'active' ELSE 'inactive' END as status
FROM patient_loyalty_cards plc
JOIN patients p ON plc.patient_id = p.patient_id
JOIN loyalty_points lp ON plc.patient_id = lp.patient_id
JOIN loyalty_card_types lct ON plc.card_type_id = lct.card_type_id
WHERE p.full_name = 'Ram Kumar';

-- If verification looks good, COMMIT. Otherwise, ROLLBACK.
COMMIT;
-- ROLLBACK;
```

---

## Summary

**Current State**:
- Discount system uses OLD `patient_loyalty_cards` table ❌
- NEW wallet system exists but not integrated with discounts ❌

**Required Action**:
1. Update `discount_service.py` to query `patient_loyalty_wallet` instead of `patient_loyalty_cards`
2. Update `discount_api.py` with same change
3. Test all discount scenarios
4. Migrate Ram Kumar's data to NEW system
5. Deprecate OLD tables

**After Migration**:
- Discount system uses NEW `patient_loyalty_wallet` table ✅
- Single source of truth for patient tiers ✅
- Better performance (denormalized discount_percent) ✅
- Can safely deprecate OLD tables ✅

---

**Next Steps**: Let me know if you want me to:
1. Update the discount service code now
2. Run the migration script for Ram Kumar
3. Both 1 and 2

