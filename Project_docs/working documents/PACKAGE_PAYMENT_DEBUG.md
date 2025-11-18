# Package Payment Allocation - Debug Guide

**Issue**: Package plan shows paid_amount = 0 even though payment was allocated
**Status**: 🔍 DEBUGGING

---

## 🔍 Diagnostic Steps

### Step 1: Check Application Logs

**Look for these log entries** when creating package plan:

```
🔍 Calculating package allocated payment: invoice_id=..., package_id=...
✓ Found package line item: ..., amount=₹...
📊 Found X AR entries for line item ... (UUID comparison)
```

**Enhanced Diagnostic Logs (v2.0)**:

If no AR entries found with UUID comparison:
```
⚠️ No AR entries with UUID comparison, trying string cast...
📊 Found X AR entries with string cast
```

If still no AR entries:
```
⚠️ No AR entries for line item, but found X AR entries for invoice ...
⚠️ X of X AR entries have NULL reference_line_item_id
❌ AR entries for this invoice don't have line item references! Invoice was created with OLD AR posting logic.
```

**Check Log File**:
```bash
tail -200 logs/app.log | grep "package allocated\|AR entries\|AR calculation\|reference_line_item_id"
```

---

### Step 2: Verify AR Entries in Database

**Query 1: Check if AR entries exist for the invoice**

```sql
-- Replace with your actual invoice_id
SELECT
    il.item_type,
    il.item_name,
    il.line_total,
    il.line_item_id,
    COUNT(ar.entry_id) as ar_entry_count,
    SUM(CASE WHEN ar.entry_type = 'invoice' THEN ar.debit_amount ELSE 0 END) as total_debits,
    SUM(CASE WHEN ar.entry_type = 'payment' THEN ar.credit_amount ELSE 0 END) as total_credits
FROM invoice_line_item il
LEFT JOIN ar_subledger ar ON ar.reference_line_item_id = il.line_item_id
WHERE il.invoice_id = '<your_invoice_id>'
GROUP BY il.item_type, il.item_name, il.line_total, il.line_item_id
ORDER BY
    CASE il.item_type
        WHEN 'Service' THEN 1
        WHEN 'Medicine' THEN 2
        WHEN 'Package' THEN 3
        ELSE 4
    END;
```

**Expected Result**:
```
item_type | item_name        | line_total | ar_entry_count | total_debits | total_credits
----------|------------------|------------|----------------|--------------|---------------
Service   | Consultation     | 2000.00    | 2              | 2000.00      | 2000.00
Service   | Blood Test       | 1500.00    | 2              | 1500.00      | 1500.00
Medicine  | Paracetamol      | 300.00     | 2              | 300.00       | 300.00
Package   | Hair Restoration | 5900.00    | 1 or 2         | 5900.00      | XXX.XX
```

**If `ar_entry_count = 0` for Package**: AR entries not created → Invoice AR posting issue
**If `total_credits = 0` for Package**: No payment allocated → Payment allocation issue

---

### Step 3: Check Specific Package Line Item

**Query 2: Get package line item ID**

```sql
-- Replace with your invoice_id and package_id
SELECT
    line_item_id,
    item_name,
    line_total,
    package_id
FROM invoice_line_item
WHERE invoice_id = '<your_invoice_id>'
  AND item_type = 'Package'
  AND package_id = '<your_package_id>';
```

**Copy the `line_item_id` from result**

---

### Step 4: Check AR Entries for Package Line Item

**Query 3: AR entries for specific line item**

```sql
-- Replace with line_item_id from Step 3
SELECT
    entry_id,
    entry_type,
    reference_type,
    reference_id,
    debit_amount,
    credit_amount,
    transaction_date,
    created_at
FROM ar_subledger
WHERE reference_line_item_id = '<line_item_id_from_step3>'
ORDER BY created_at;
```

**Expected Result**:
```
entry_type | reference_type | debit_amount | credit_amount | transaction_date
-----------|----------------|--------------|---------------|------------------
invoice    | invoice        | 5900.00      | 0.00          | 2025-11-12
payment    | payment        | 0.00         | XXX.XX        | 2025-11-12
```

**If no rows returned**: AR entries not linked to line item (check `reference_line_item_id`)

---

### Step 5: Check Package Plan

**Query 4: Check package plan paid_amount**

```sql
-- Check recently created package plan
SELECT
    plan_id,
    invoice_id,
    package_id,
    total_amount,
    paid_amount,
    balance_amount,
    created_at
FROM package_payment_plans
ORDER BY created_at DESC
LIMIT 1;
```

---

## 🐛 Common Issues & Fixes

### Issue 0: Invoice Created with OLD AR Posting Logic ⚠️ MOST COMMON

**Symptom**:
- Logs show "Found 0 AR entries for line item (UUID comparison)"
- Logs show "Found X AR entries for invoice" but "X of X have NULL reference_line_item_id"
- Error: "AR entries for this invoice don't have line item references!"

**Cause**: Invoice was created BEFORE we implemented line-item AR splitting (before 2025-11-12)

**What Happened**:
- Old AR posting logic created ONE AR entry per invoice
- `reference_line_item_id` was NULL (column didn't exist yet)
- Payment allocation can't work without line-item AR entries

**Fix Options**:

**Option A: Create NEW test invoice** (Recommended for testing):
```sql
-- Just create a fresh invoice with the new system
-- It will automatically have line-item AR entries
```

**Option B: Backfill AR entries for existing invoice** (For production data):
```sql
-- WARNING: This is complex and requires careful testing!
-- Step 1: Delete old AR entries
DELETE FROM ar_subledger WHERE reference_id = '<invoice_id>' AND reference_type = 'invoice';

-- Step 2: Recreate with line-item references
-- (Requires manual SQL or running the updated invoice posting code)
```

**Recommendation**: For now, create a NEW invoice to test the system. This is the safest approach.

---

### Issue 1: No AR Entries Found (ar_entry_count = 0)

**Symptom**: Query 1 shows `ar_entry_count = 0` for package

**Cause**: Invoice AR posting didn't create entries for line items

**Check**:
```sql
-- Check if ANY AR entries exist for this invoice
SELECT COUNT(*) FROM ar_subledger WHERE reference_id = '<invoice_id>';
```

**If count = 0**: Invoice not posted to AR at all
**If count > 0 but no reference_line_item_id**: Old AR posting logic (Issue 0 above)

**Fix**: Recreate invoice with new AR posting logic

---

### Issue 2: Payment Not Allocated to Package

**Symptom**: Query 1 shows `total_credits = 0` for package

**Cause**: Payment amount not enough to reach package (services/medicines consumed all payment)

**Example**:
```
Invoice:
- Service: ₹2,000
- Medicine: ₹300
- Package: ₹5,900
Total: ₹8,200

Payment: ₹2,200

Allocation (Services → Medicines → Packages):
- Service: ₹2,000 ✅
- Medicine: ₹200 (partial)
- Package: ₹0 ❌ (no payment left)
```

**This is CORRECT behavior** - package gets nothing because payment was consumed by higher priority items.

**Solution**: Record additional payment or adjust invoice amounts

---

### Issue 3: UUID Mismatch

**Symptom**: Logs show "Found package line item" but "Found 0 AR entries"

**Cause**: `reference_line_item_id` in AR entries doesn't match `line_item_id` (UUID type mismatch)

**Check**:
```sql
-- Check data types
SELECT
    il.line_item_id,
    pg_typeof(il.line_item_id) as line_item_type,
    ar.reference_line_item_id,
    pg_typeof(ar.reference_line_item_id) as reference_type
FROM invoice_line_item il
LEFT JOIN ar_subledger ar ON CAST(ar.reference_line_item_id AS TEXT) = CAST(il.line_item_id AS TEXT)
WHERE il.invoice_id = '<invoice_id>'
  AND il.item_type = 'Package'
LIMIT 1;
```

**If types differ**: UUID comparison failing

**Fix**: Update query to cast both to text for comparison

---

### Issue 4: Method Not Being Called

**Symptom**: No log entries for "Calculating package allocated payment"

**Cause**: Method not invoked OR logging not working

**Check Application Logs**:
```bash
# Check if method is called at all
grep "Calculating package allocated payment" logs/app.log

# Check if package plan creation logs exist
grep "Package.*allocated payment from invoice" logs/app.log
```

**If no logs**: Method might not be called OR exception occurring

**Solution**: Check for exceptions in logs

---

## 📋 Checklist for User

Please run these checks and report back:

- [ ] **Step 1**: Check application logs for package allocation messages
- [ ] **Step 2**: Run Query 1 - Check AR entries exist for all line items
- [ ] **Step 3**: Run Query 2 - Get package line_item_id
- [ ] **Step 4**: Run Query 3 - Check AR entries for package line item
- [ ] **Step 5**: Run Query 4 - Check package plan paid_amount

**Report**:
1. What do the logs show? (Step 1)
2. What are the ar_entry_count and total_credits for package? (Step 2)
3. How many AR entries for package line item? (Step 4)
4. What is the payment amount vs invoice total? (to check if enough for package)

---

## 🔧 Quick Fix SQL (If Needed)

**If AR entries exist but package plan shows ₹0**:

```sql
-- Update package plan with correct paid_amount
UPDATE package_payment_plans
SET paid_amount = (
    SELECT COALESCE(SUM(ar.credit_amount), 0)
    FROM ar_subledger ar
    JOIN invoice_line_item il ON il.line_item_id = ar.reference_line_item_id
    WHERE il.invoice_id = package_payment_plans.invoice_id
      AND il.package_id = package_payment_plans.package_id
      AND ar.entry_type = 'payment'
),
updated_at = NOW()
WHERE plan_id = '<your_plan_id>';
```

---

**Please run the diagnostic queries and share the results so we can pinpoint the exact issue!**
