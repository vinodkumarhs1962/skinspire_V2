# Supplier Advance Payment - Complete Testing Guide

## ✅ Changes Implemented

### 1. **Database Changes** (Completed)
- ✅ Added `advance_amount` column to `supplier_payment` table
- ✅ Created `supplier_advance_adjustments` subledger table
- ✅ Created `v_supplier_advance_balance` view for real-time balance
- ✅ Created 8 indexes for performance
- ✅ Added triggers for timestamp management

### 2. **Model Changes** (Completed)
**File:** `app/models/transaction.py`
- ✅ Added `advance_amount` field to SupplierPayment model (line 999)
- ✅ Created SupplierAdvanceAdjustment model (lines 1634-1661)
- ✅ Added relationship comments

### 3. **Service Layer Changes** (Completed)
**File:** `app/services/supplier_payment_service.py`

#### Fixed Payment Amount Calculation (Line 657)
- ❌ **OLD:** `amount=net_new_payment` (excluded advance)
- ✅ **NEW:** `amount=total_amount` (includes advance + all methods)

#### Added advance_amount Field (Line 670)
```python
advance_amount=advance_allocation  # NEW field populated
```

#### Created Subledger Entries (Lines 711-738)
- Creates SupplierAdvanceAdjustment records for each advance allocation
- Links source payment (advance) to target payment (invoice payment)
- Tracks amount, type, and notes

### 4. **GL Service Changes** (Completed)
**File:** `app/services/gl_service.py`

#### Multi-Method Payment Support (Lines 1195-1277)
- ✅ Cash payment entries
- ✅ Cheque payment entries
- ✅ Bank transfer entries
- ✅ UPI payment entries
- ✅ **Advance allocation entries** (NEW)

#### Advance Payment vs Invoice Payment Logic (Lines 1180-1203)
- **Advance Payment** (no invoice):
  ```
  Dr. Supplier Advance (Asset)  ₹1000
      Cr. Cash/Bank              ₹1000
  ```

- **Invoice Payment with Advance** (₹70 total: ₹20 advance + ₹50 cash):
  ```
  Dr. Accounts Payable           ₹70
      Cr. Cash                    ₹50
      Cr. Supplier Advance        ₹20
  ```

#### Added Supplier Advance Account Lookup (Lines 1342-1360)
- Searches for "Supplier Advance" or "Advance to Suppliers" account
- Raises error if not found (must be created in Chart of Accounts)

---

## 🧪 Testing Scenarios

### **PREREQUISITE: Create Supplier Advance GL Account**

Before testing, ensure the GL account exists:

**Option 1: SQL Insert**
```sql
INSERT INTO chart_of_accounts (
    account_id, hospital_id, account_code, account_name,
    account_type, parent_account_id, is_active,
    created_at, created_by
) VALUES (
    gen_random_uuid(),
    '<your_hospital_id>',
    '1250',  -- Asset account code
    'Supplier Advance',
    'asset',
    NULL,
    TRUE,
    CURRENT_TIMESTAMP,
    '<user_id>'
);
```

**Option 2: Via UI**
Create a new GL account:
- **Name:** Supplier Advance
- **Type:** Asset
- **Code:** 1250
- **Category:** Current Assets

---

### **Test Case 1: Create Advance Payment (No Invoice)**

**Scenario:** Pay ₹5000 to supplier without an invoice

**Steps:**
1. Go to Supplier → Record Payment
2. Select supplier
3. Leave "Invoice" field empty
4. Enter amount: ₹5000
5. Select payment method: Cash
6. Save

**Expected Results:**
✅ Payment record created with:
- `amount = 5000`
- `cash_amount = 5000`
- `advance_amount = 0` (this IS the advance)
- `invoice_id = NULL`

✅ GL Entries created:
```
Dr. Supplier Advance  ₹5000
    Cr. Cash           ₹5000
```

✅ View advance balance:
```sql
SELECT * FROM v_supplier_advance_balance
WHERE supplier_id = '<supplier_id>';
-- Should show: original_advance_amount = 5000, remaining_balance = 5000
```

---

### **Test Case 2: Advance-Only Payment to Invoice**

**Scenario:** Pay ₹500 invoice using ONLY advance (no new cash)

**Steps:**
1. Go to Supplier → Record Payment
2. Select supplier
3. Select invoice (₹500 total)
4. Enter total amount: ₹500
5. Enter advance allocation: ₹500
6. All other methods: ₹0
7. Save

**Expected Results:**
✅ Payment record created with:
- `amount = 500`
- `advance_amount = 500`
- `cash_amount = 0`
- `invoice_id = <invoice_id>`

✅ Subledger entry created:
```sql
SELECT * FROM supplier_advance_adjustments
WHERE target_payment_id = '<new_payment_id>';
-- Should show: amount = 500, source_payment_id = <advance_payment_id>
```

✅ GL Entries created:
```
Dr. Accounts Payable    ₹500
    Cr. Supplier Advance ₹500
```

✅ Advance balance reduced:
```sql
SELECT * FROM v_supplier_advance_balance
WHERE supplier_id = '<supplier_id>';
-- Should show: original_advance_amount = 5000, allocated_amount = 500, remaining_balance = 4500
```

---

### **Test Case 3: Mixed Payment (Advance + Cash)**

**Scenario:** Pay ₹1000 invoice using ₹300 advance + ₹700 cash

**Steps:**
1. Go to Supplier → Record Payment
2. Select supplier
3. Select invoice (₹1000 total)
4. Enter total amount: ₹1000
5. Enter advance allocation: ₹300
6. Enter cash amount: ₹700
7. Save

**Expected Results:**
✅ Payment record created with:
- `amount = 1000` ✅ **CRITICAL FIX**
- `advance_amount = 300`
- `cash_amount = 700`
- `invoice_id = <invoice_id>`

✅ Subledger entry created:
```sql
SELECT * FROM supplier_advance_adjustments
WHERE target_payment_id = '<new_payment_id>';
-- Should show: amount = 300
```

✅ GL Entries created:
```
Dr. Accounts Payable    ₹1000
    Cr. Cash             ₹700
    Cr. Supplier Advance ₹300
```

✅ Advance balance reduced:
```sql
SELECT * FROM v_supplier_advance_balance
WHERE supplier_id = '<supplier_id>';
-- Should show: allocated_amount = 800 (500 + 300), remaining_balance = 4200 (5000 - 800)
```

---

### **Test Case 4: Multi-Method Payment with Advance**

**Scenario:** Pay ₹2000 invoice using ₹500 advance + ₹800 cash + ₹400 cheque + ₹300 UPI

**Steps:**
1. Go to Supplier → Record Payment
2. Select supplier
3. Select invoice (₹2000 total)
4. Enter total amount: ₹2000
5. Enter advance allocation: ₹500
6. Enter cash amount: ₹800
7. Enter cheque amount: ₹400 (+ cheque details)
8. Enter UPI amount: ₹300 (+ UPI details)
9. Save

**Expected Results:**
✅ Payment record created with:
- `amount = 2000` ✅ **CRITICAL FIX**
- `advance_amount = 500`
- `cash_amount = 800`
- `cheque_amount = 400`
- `upi_amount = 300`

**Validation Check:**
```
500 + 800 + 400 + 300 = 2000 ✅
```

✅ GL Entries created (5 credit entries + 1 debit):
```
Dr. Accounts Payable     ₹2000
    Cr. Cash              ₹800
    Cr. Bank (Cheque)     ₹400
    Cr. Bank (UPI)        ₹300
    Cr. Supplier Advance  ₹500
```

✅ Subledger entry created for ₹500 advance allocation

---

### **Test Case 5: Partial Advance Allocation (Split)**

**Scenario:** Advance payment is ₹5000, but invoice is ₹7000. Use ₹5000 from advance + ₹2000 cash.

**Steps:**
1. Ensure you have an advance payment of ₹5000
2. Create invoice for ₹7000
3. Record payment:
   - Total: ₹7000
   - Advance: ₹5000
   - Cash: ₹2000

**Expected Results:**
✅ Original advance payment is FULLY allocated (remaining_balance = 0)
✅ Payment record shows full ₹7000
✅ GL entries show both ₹5000 advance and ₹2000 cash

---

## 🔍 Verification Queries

### 1. Check Payment Record
```sql
SELECT
    payment_id,
    amount AS total_amount,
    advance_amount,
    cash_amount,
    cheque_amount,
    bank_transfer_amount,
    upi_amount,
    -- Verify sum
    (advance_amount + cash_amount + cheque_amount + bank_transfer_amount + upi_amount) AS calculated_sum,
    -- Should match
    amount = (advance_amount + cash_amount + cheque_amount + bank_transfer_amount + upi_amount) AS amounts_match
FROM supplier_payment
WHERE payment_id = '<payment_id>';
```

### 2. Check Subledger Entries
```sql
SELECT
    adjustment_id,
    source_payment_id,
    target_payment_id,
    invoice_id,
    amount,
    adjustment_type,
    adjustment_date,
    notes
FROM supplier_advance_adjustments
WHERE target_payment_id = '<payment_id>'
ORDER BY adjustment_date;
```

### 3. Check Advance Balance
```sql
SELECT * FROM v_supplier_advance_balance
WHERE supplier_id = '<supplier_id>'
ORDER BY advance_date;
```

### 4. Check GL Entries
```sql
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
    CASE WHEN ge.debit_amount > 0 THEN 1 ELSE 2 END,
    ge.entry_date;
```

**Expected Output (for ₹70 total: ₹20 advance + ₹50 cash):**
```
account_name          | debit | credit
---------------------|-------|-------
Accounts Payable     |  70.00|   0.00
Cash                 |   0.00|  50.00
Supplier Advance     |   0.00|  20.00
```

### 5. Verify GL Balance
```sql
-- Debits should equal credits
SELECT
    gt.transaction_id,
    gt.description,
    gt.total_debit,
    gt.total_credit,
    (gt.total_debit - gt.total_credit) AS balance
FROM gl_transaction gt
WHERE gt.reference_id = '<payment_id>'::text
AND gt.transaction_type = 'SUPPLIER_PAYMENT';

-- Should show balance = 0.00
```

---

## ⚠️ Common Issues & Troubleshooting

### Issue 1: "Supplier Advance GL account not found"
**Solution:** Create the GL account as shown in Prerequisites section

### Issue 2: Payment amount doesn't include advance
**Solution:** Check that you're using the updated code (line 657 should use `total_amount`)

### Issue 3: No subledger entries created
**Solution:** Check that `allocation_result.get('payments')` is not empty in logs

### Issue 4: GL entries don't balance
**Solution:** Check that all payment method amounts sum to total amount

### Issue 5: Advance balance not reducing
**Solution:** Check that subledger entries were created and view is querying correctly

---

## 📊 Success Criteria

After all tests:

✅ **Payment Records:**
- Total amount includes ALL payment methods (advance + cash + cheque + UPI + bank)
- Each method amount is stored in correct field
- Sum of all method amounts equals total amount

✅ **Subledger Entries:**
- One entry per advance allocation
- Source and target payment IDs linked correctly
- Amount matches advance_amount in payment

✅ **GL Entries:**
- All payment methods have separate GL credit entries
- Advance allocations credit "Supplier Advance" account
- Debits and credits balance
- Advance payments (no invoice) debit "Supplier Advance"

✅ **Advance Balance View:**
- Shows accurate remaining balance
- Tracks all allocations
- FIFO order maintained

---

## 🎯 Benefits Achieved

1. ✅ **Complete Audit Trail** - Every advance allocation is tracked
2. ✅ **Accurate GL Posting** - Multi-method payments properly posted
3. ✅ **Real-time Balance** - View shows current advance balance
4. ✅ **Performance** - Indexed subledger queries (no dynamic calculation)
5. ✅ **Data Integrity** - Payment amounts fully captured
6. ✅ **Reporting Ready** - Easy advance utilization reports

---

## 📝 Notes

- Always test in development environment first
- Verify GL account exists before recording payments
- Check logs for any errors during subledger creation
- Use verification queries after each test case
- Compare actual vs expected GL entries

---

**Document Version:** 1.0
**Last Updated:** 2025-11-02
**Author:** Claude Code Implementation
