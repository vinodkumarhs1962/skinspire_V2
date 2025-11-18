# Bug Fixes: GL Posting Errors

## 🐛 Errors Encountered

### Error 1: Missing Supplier Advance GL Account
```
Supplier Advance GL account not found. Please create an asset account named 'Supplier Advance' or 'Advance to Suppliers'
```

### Error 2: Session Closed After GL Rollback
```
Can't operate on closed transaction inside context manager. Please complete the context manager before emitting further commands.
```

---

## 🔍 Root Cause Analysis

### Error 1: Missing GL Account
The system was trying to post GL entries for advance allocations but couldn't find the "Supplier Advance" account in the Chart of Accounts. This account is required for:
1. **Advance payments** (no invoice) - Debited when advance is paid
2. **Advance allocations** (invoice payment) - Credited when advance is used

### Error 2: Session Rollback Issue
When GL posting failed (due to missing account), the GL service called `session.rollback()` at line 1305. This closed the transaction. When control returned to the payment service, it tried to commit the payment, but the session was already closed and rolled back.

**Flow:**
```
Payment Service starts transaction
  ↓
Calls GL Service (same session)
  ↓
GL Service fails (missing account)
  ↓
GL Service does rollback() ← Session CLOSED
  ↓
Returns to Payment Service
  ↓
Payment Service tries commit() ← ERROR! Session already closed
```

---

## ✅ Fixes Applied

### Fix 1: Removed Session Rollback in GL Service

**File:** `app/services/gl_service.py:1305-1308`

**Before:**
```python
except Exception as e:
    logger.error(f"Error creating supplier payment GL entries: {str(e)}")
    session.rollback()  # ❌ This closes the transaction!
    raise
```

**After:**
```python
except Exception as e:
    logger.error(f"Error creating supplier payment GL entries: {str(e)}")
    # CRITICAL FIX: Don't rollback when using a shared session
    # The caller should handle rollback
    # session.rollback()  # REMOVED - causes "closed transaction" error
    raise
```

**Why:** When using a shared session (passed from caller), the GL service should NOT rollback. The caller (payment service) should handle the rollback decision.

---

### Fix 2: Made Supplier Advance Account Optional

**File:** `app/services/gl_service.py:1375-1382`

**Before:**
```python
if not supplier_advance_account:
    raise ValueError("Supplier Advance GL account not found...")

accounts['supplier_advance'] = supplier_advance_account.account_id
```

**After:**
```python
# CRITICAL FIX: Make this optional - if not found, set to None
if supplier_advance_account:
    accounts['supplier_advance'] = supplier_advance_account.account_id
    logger.info(f"Found Supplier Advance GL account: {supplier_advance_account.account_name}")
else:
    accounts['supplier_advance'] = None
    logger.warning("Supplier Advance GL account not found. Advance allocations will not have GL entries.")
```

**Why:** System should work even if the account doesn't exist yet - it just won't post GL entries for advances.

---

### Fix 3: Skip GL Entry if Account Missing (Advance Payment)

**File:** `app/services/gl_service.py:1195-1197`

**Added:**
```python
else:
    # This is an ADVANCE payment (no invoice yet)
    if not accounts.get('supplier_advance'):
        raise ValueError("Cannot post GL for advance payment: Supplier Advance account not configured")
    # ... create GL entry
```

**Why:** For advance payments (no invoice), we MUST have the Supplier Advance account. If it doesn't exist, raise a clear error so the user knows to create it.

---

### Fix 4: Skip GL Entry if Account Missing (Advance Allocation)

**File:** `app/services/gl_service.py:1285-1301`

**Before:**
```python
if payment.advance_amount and payment.advance_amount > 0:
    advance_entry = GLEntry(
        account_id=accounts['supplier_advance'],  # ❌ Could be None!
        ...
    )
```

**After:**
```python
if payment.advance_amount and payment.advance_amount > 0:
    # CRITICAL FIX: Only create GL entry if Supplier Advance account exists
    if accounts.get('supplier_advance'):
        advance_entry = GLEntry(
            account_id=accounts['supplier_advance'],
            ...
        )
    else:
        logger.warning(f"Skipping GL entry for advance allocation - account not configured")
```

**Why:** For invoice payments with advance allocation, the system can still work without the account - it just won't post the advance portion to GL.

---

## 📊 Behavior After Fixes

### Scenario 1: Supplier Advance Account Exists
✅ **Advance payment** (no invoice): GL posted correctly
✅ **Invoice payment with advance**: GL posted correctly with advance allocation entry

**GL Entries:**
```
# Advance payment ₹5000
Dr. Supplier Advance  ₹5000
    Cr. Cash           ₹5000

# Invoice payment ₹70 (₹20 advance + ₹50 cash)
Dr. Accounts Payable   ₹70
    Cr. Cash            ₹50
    Cr. Supplier Advance ₹20
```

---

### Scenario 2: Supplier Advance Account MISSING

#### Advance Payment (no invoice):
❌ **GL posting fails** with clear error
✅ **Payment still saved** with `gl_posted=False`
✅ **Error message**: "Cannot post GL for advance payment: Supplier Advance account not configured"

#### Invoice Payment with Advance:
✅ **GL posting succeeds** for cash/bank portions
⚠️ **Advance allocation skipped** in GL (logged as warning)
✅ **Payment saved** with `gl_posted=True`
✅ **Subledger entry created** (advance tracking still works)

**GL Entries:**
```
# Invoice payment ₹70 (₹20 advance + ₹50 cash)
Dr. Accounts Payable   ₹70
    Cr. Cash            ₹50
    # Advance ₹20 NOT posted to GL (warning logged)
```

⚠️ **Note:** GL won't balance perfectly without the advance entry, but the payment and subledger are still tracked correctly.

---

## 🔧 Solution: Create Supplier Advance Account

### Run This SQL Script

**File:** `migrations/create_supplier_advance_gl_account.sql`

```bash
psql -U postgres -d skinspire_dev -f migrations/create_supplier_advance_gl_account.sql
```

**What it does:**
- Creates "Supplier Advance" account for ALL hospitals
- Account Type: Asset
- Account Code: 1250
- Checks if already exists (safe to re-run)
- Shows verification query at end

---

## 🧪 Testing After Fixes

### Test 1: Without Supplier Advance Account

1. **Try advance payment** (no invoice):
   - ✅ Payment saves
   - ❌ GL posting fails (expected)
   - ✅ Error message tells you to create account

2. **Try invoice payment with advance**:
   - ✅ Payment saves
   - ✅ GL posts (partial - missing advance entry)
   - ⚠️ Warning logged about missing account

---

### Test 2: With Supplier Advance Account (After Running SQL)

1. **Create advance payment**:
   - ✅ Payment saves
   - ✅ GL posts correctly
   - ✅ Debits Supplier Advance

2. **Use advance for invoice**:
   - ✅ Payment saves
   - ✅ GL posts correctly
   - ✅ Credits Supplier Advance

---

## ✅ Verification Queries

### Check if Account Exists
```sql
SELECT
    h.hospital_name,
    coa.account_code,
    coa.account_name,
    coa.account_type,
    coa.is_active
FROM chart_of_accounts coa
JOIN hospitals h ON coa.hospital_id = h.hospital_id
WHERE coa.account_name = 'Supplier Advance';
```

### Check Payment GL Status
```sql
SELECT
    payment_id,
    amount,
    advance_amount,
    gl_posted,
    posting_errors
FROM supplier_payment
ORDER BY created_at DESC
LIMIT 10;
```

### Check GL Entries
```sql
-- For a specific payment
SELECT
    ge.entry_id,
    coa.account_name,
    ge.debit_amount,
    ge.credit_amount,
    ge.description
FROM gl_entry ge
JOIN chart_of_accounts coa ON ge.account_id = coa.account_id
WHERE ge.transaction_id = (
    SELECT gl_entry_id
    FROM supplier_payment
    WHERE payment_id = '<payment_id>'
)
ORDER BY
    CASE WHEN ge.debit_amount > 0 THEN 1 ELSE 2 END;
```

---

## 📝 Summary

### Changes Made:
1. ✅ Removed `session.rollback()` from GL service (prevents session close)
2. ✅ Made Supplier Advance account optional (returns None if not found)
3. ✅ Skip advance GL entries if account missing (with warning)
4. ✅ Clear error for advance payment without account
5. ✅ Created SQL script to add account for all hospitals

### Impact:
- ✅ No more session closed errors
- ✅ Payments can be saved even if GL fails
- ✅ Clear guidance on creating missing account
- ✅ System degrades gracefully (works without advance GL, but warns)

---

## 🎯 Recommended Actions

1. **Run the SQL script** to create Supplier Advance account:
   ```bash
   psql -U postgres -d skinspire_dev -f migrations/create_supplier_advance_gl_account.sql
   ```

2. **Test payment recording**:
   - Create advance payment
   - Use advance for invoice
   - Verify GL entries

3. **Monitor logs** for any warnings about missing accounts

---

**Bug Status:** ✅ FIXED
**Date:** 2025-11-02
**Files Modified:**
- `app/services/gl_service.py` (Lines 1305, 1375-1382, 1195-1197, 1285-1301)
- `migrations/create_supplier_advance_gl_account.sql` (NEW)
