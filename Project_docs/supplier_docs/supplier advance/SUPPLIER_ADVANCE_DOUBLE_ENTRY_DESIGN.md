# Supplier Advance Payment - Double-Entry Subledger Design

## Overview

The supplier advance payment system uses a **proper double-entry subledger** to track advance payments and their allocations.

---

## Double-Entry Concept

Like a bank account, the subledger tracks:
- **DEBITS** (increases advance balance) - When advance is received from supplier
- **CREDITS** (decreases advance balance) - When advance is allocated to an invoice

**Balance = Sum(Debits) - Sum(Credits)**

---

## Subledger Table: `supplier_advance_adjustments`

### Key Fields:

| Field | Description |
|-------|-------------|
| `adjustment_id` | Primary key (UUID) |
| `adjustment_type` | **advance_receipt**, allocation, reversal, refund |
| `source_payment_id` | The advance payment (always populated) |
| `target_payment_id` | The invoice payment (NULL for receipts, populated for allocations) |
| `invoice_id` | Invoice ID (NULL for receipts, populated for allocations) |
| `amount` | Transaction amount |
| `adjustment_date` | Transaction timestamp |

### Adjustment Types:

| Type | Debit/Credit | When Created | Description |
|------|--------------|--------------|-------------|
| **advance_receipt** | DEBIT (+) | Advance payment created (no invoice) | Increases advance balance |
| **allocation** | CREDIT (-) | Advance allocated to invoice | Decreases advance balance |
| **reversal** | DEBIT (+) | Allocation reversed | Restores advance balance |
| **refund** | CREDIT (-) | Advance refunded to supplier | Decreases advance balance |

---

## Transaction Flows

### Flow 1: Create Advance Payment (No Invoice)

**User Action:** Record payment to supplier without selecting an invoice

**System Actions:**
1. Create `supplier_payment` record:
   ```
   payment_id: UUID
   invoice_id: NULL
   amount: ₹5000
   workflow_status: 'approved' (if < threshold)
   ```

2. Create subledger DEBIT entry:
   ```
   adjustment_type: 'advance_receipt'
   source_payment_id: [payment_id]
   target_payment_id: NULL
   invoice_id: NULL
   amount: ₹5000
   ```

**Result:**
- Main table: 1 payment record
- Subledger: 1 DEBIT entry
- Advance balance: ₹5000

---

### Flow 2: Allocate Advance to Invoice

**User Action:** Pay invoice using ₹2000 from advance + ₹3000 cash

**System Actions:**
1. Find oldest unallocated advance (FIFO from view)
2. Create new `supplier_payment` record:
   ```
   payment_id: UUID-NEW
   invoice_id: [invoice_id]
   amount: ₹5000 (total)
   cash_amount: ₹3000
   advance_amount: ₹2000
   ```

3. Create subledger CREDIT entry:
   ```
   adjustment_type: 'allocation'
   source_payment_id: [original advance payment_id]
   target_payment_id: [UUID-NEW]
   invoice_id: [invoice_id]
   amount: ₹2000
   ```

**Result:**
- Main table: 2 payment records (advance + invoice payment)
- Subledger: 2 entries (1 DEBIT ₹5000, 1 CREDIT ₹2000)
- Advance balance: ₹5000 - ₹2000 = ₹3000

---

### Flow 3: Full Advance Allocation

**User Action:** Pay ₹70 invoice using ₹70 from advance (no other payment methods)

**System Actions:**
1. Find advance balance (₹3000 available)
2. Allocate ₹70 from advance
3. Link advance payment to invoice:
   ```
   UPDATE supplier_payment
   SET invoice_id = [invoice_id]
   WHERE payment_id = [advance payment_id]
   ```

4. Create subledger CREDIT entry:
   ```
   adjustment_type: 'allocation'
   source_payment_id: [advance payment_id]
   target_payment_id: [advance payment_id] (same - no new payment created)
   invoice_id: [invoice_id]
   amount: ₹70
   ```

**Result:**
- Advance balance: ₹3000 - ₹70 = ₹2930

---

### Flow 4: Partial Advance Allocation (Payment Splitting)

**User Action:** Pay invoice using ₹4000 from ₹3000 advance (requires split)

**System Actions:**
1. Detect: allocation amount (₹4000) > remaining balance (₹3000)
2. Split original advance payment:
   - **Allocated portion**: Create new payment record with invoice_id
   - **Remaining portion**: Update original payment, reduce amount

3. Create subledger entries for EACH split:
   ```
   Entry 1 (allocated):
   adjustment_type: 'allocation'
   source_payment_id: [original advance payment_id]
   target_payment_id: [new split payment_id]
   amount: ₹3000

   Entry 2 (remaining):
   adjustment_type: 'allocation'
   source_payment_id: [next oldest advance]
   target_payment_id: [invoice payment_id]
   amount: ₹1000
   ```

---

## Balance Calculation View

### `v_supplier_advance_balance`

**SQL Logic:**
```sql
SELECT
    source_payment_id AS payment_id,
    SUM(CASE WHEN adjustment_type = 'advance_receipt' THEN amount ELSE 0 END) AS debit_total,
    SUM(CASE WHEN adjustment_type = 'allocation' THEN amount ELSE 0 END) AS credit_total,
    (debit_total - credit_total) AS remaining_balance
FROM supplier_advance_adjustments
WHERE remaining_balance > 0.01
GROUP BY source_payment_id
ORDER BY MIN(adjustment_date) ASC  -- FIFO
```

**Key Points:**
- Balance is calculated ONLY from subledger (not main table)
- FIFO order ensures oldest advances are used first
- Excludes fully allocated advances (balance ≤ 0.01)

---

## Audit Trail View

### `v_supplier_advance_transactions`

Shows complete transaction history with debit/credit columns:

| Date | Type | Debit | Credit | Balance | Description |
|------|------|-------|--------|---------|-------------|
| 2025-11-01 | advance_receipt | ₹5000 | - | ₹5000 | Advance payment received |
| 2025-11-02 | allocation | - | ₹2000 | ₹3000 | Allocated to INV-001 |
| 2025-11-03 | allocation | - | ₹1000 | ₹2000 | Allocated to INV-002 |

---

## Key Benefits of Double-Entry Design

1. **Accurate Balance**: Balance is always sum of debits minus credits
2. **Complete Audit Trail**: Every advance transaction is recorded
3. **Reconciliation**: Easy to verify balance = receipts - allocations
4. **History Tracking**: Full transaction history for each advance
5. **Proper Accounting**: Matches accounting principles (debit/credit)
6. **No Dynamic Calculation**: Balance is derived from subledger entries only

---

## Migration Steps

1. **Run migration SQL:**
   ```bash
   psql -U postgres -d skinspire_dev -f migrations/update_supplier_advance_double_entry.sql
   ```

2. **Verify constraint update:**
   ```sql
   SELECT constraint_name, constraint_definition
   FROM information_schema.check_constraints
   WHERE constraint_name LIKE '%adjustment_type%';
   ```

3. **Test advance payment:**
   - Create advance payment (no invoice)
   - Verify subledger DEBIT entry created
   - Check balance view shows correct amount

4. **Test advance allocation:**
   - Pay invoice using advance
   - Verify subledger CREDIT entry created
   - Check balance view shows reduced amount

---

## Verification Queries

### Check Advance Balance
```sql
SELECT * FROM v_supplier_advance_balance
WHERE supplier_id = 'your-supplier-id';
```

### Check Transaction History
```sql
SELECT * FROM v_supplier_advance_transactions
WHERE supplier_id = 'your-supplier-id'
ORDER BY adjustment_date DESC;
```

### Reconcile Balance
```sql
SELECT
    source_payment_id,
    SUM(CASE WHEN adjustment_type = 'advance_receipt' THEN amount ELSE 0 END) AS debits,
    SUM(CASE WHEN adjustment_type = 'allocation' THEN amount ELSE 0 END) AS credits,
    SUM(CASE WHEN adjustment_type = 'advance_receipt' THEN amount ELSE 0 END) -
    SUM(CASE WHEN adjustment_type = 'allocation' THEN amount ELSE 0 END) AS balance
FROM supplier_advance_adjustments
GROUP BY source_payment_id;
```

---

## Example Scenario

**Day 1:** Supplier sends shipment, we pay ₹10,000 advance
```
supplier_payment: payment_id=P1, amount=₹10000, invoice_id=NULL
subledger: advance_receipt, P1, ₹10000 (DEBIT)
Balance: ₹10000
```

**Day 2:** Invoice INV-001 arrives for ₹7000, pay using ₹5000 advance + ₹2000 cash
```
supplier_payment: payment_id=P2, amount=₹7000, invoice_id=INV-001, cash=₹2000, advance=₹5000
subledger: allocation, P1→P2, ₹5000 (CREDIT)
Balance: ₹10000 - ₹5000 = ₹5000
```

**Day 3:** Invoice INV-002 arrives for ₹3000, pay using ₹3000 advance only
```
subledger: allocation, P1→P1, ₹3000 (CREDIT)
Balance: ₹5000 - ₹3000 = ₹2000
```

**Day 4:** Check remaining advance
```sql
SELECT * FROM v_supplier_advance_balance WHERE source_payment_id = 'P1';
-- Returns: remaining_balance = ₹2000
```

---

## Status: ✅ READY FOR TESTING

**Date:** 2025-11-02
**Files Modified:**
- `app/services/supplier_payment_service.py` (Added DEBIT entry creation)
- `migrations/update_supplier_advance_double_entry.sql` (NEW - proper double-entry views)

**Next Steps:**
1. Run the migration SQL
2. Test advance payment creation
3. Test advance allocation
4. Verify balance calculations
