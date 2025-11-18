# Package Installment Payment - Corrected Design

**Date:** 2025-11-16
**Issue:** Package installment payments were treated separately from invoice payments
**Resolution:** Treat package installment payments as regular invoice payments

---

## Key Insight

**Package Payment Plans are ALWAYS linked to invoices!**

When a patient purchases a package:
1. An invoice is created with the package as a line item
2. `PackagePaymentPlan` is created with `invoice_id` linking to that invoice
3. Installment schedule is generated

**Therefore:** Package installment payments are simply **partial payments against an existing invoice**.

---

## Database Structure

```sql
-- Invoice created when package is purchased
INSERT INTO invoice_header (invoice_id, patient_id, total_amount, ...)
VALUES ('23be7c9c-3348-4da9-b8c0-54cf0307c02f', ..., 1770.00, ...);

-- Package line item in the invoice
INSERT INTO invoice_line_item (line_item_id, invoice_id, item_type, item_name, amount, ...)
VALUES ('3b7acedf-9f82-4d63-929d-0183bf1738ab', '23be7c9c...', 'Package', 'Basic Facial Package', 1770.00, ...);

-- Package payment plan linked to the invoice
INSERT INTO package_payment_plans (plan_id, invoice_id, package_name, total_amount, ...)
VALUES ('089c2103-8447-4bb5-a1d9-ef9c88351777', '23be7c9c...', 'Basic Facial Package', 1770.00, ...);

-- Installment schedule for the plan
INSERT INTO installment_payments (installment_id, plan_id, installment_number, amount, ...)
VALUES ('inst1...', '089c2103...', 1, 885.00, ...);
```

---

## Payment Flow - Corrected Approach

### Scenario: Patient Pays Installment #1 (₹885)

**OLD (Wrong) Approach:**
```
User pays ₹885 for installment
  ↓
Create payment with invoice_id = NULL
  ↓
Create AR entry: entry_type='package_installment', reference_line_item_id=NULL
  ↓
Problem: Invoice not updated, separate AR tracking needed
```

**NEW (Correct) Approach:**
```
User pays ₹885 for installment
  ↓
Get plan.invoice_id ('23be7c9c...')
  ↓
Create payment as invoice payment (invoice_id = '23be7c9c...')
  ↓
record_multi_invoice_payment() creates AR entry at line-item level:
  - entry_type='payment'
  - reference_line_item_id='3b7acedf...' (package line item)
  - Updates invoice paid_amount and balance_due
  ↓
record_installment_payment() updates installment:
  - installment.paid_amount += 885
  - installment.status = 'paid'
  - NO separate AR entry created
```

---

## Code Changes

### 1. `billing_views.py` - Payment Flow

**Before (Wrong):**
```python
if invoice_alloc_list:
    # Record invoice payment
    result = record_multi_invoice_payment(...)
    last_payment_id = result['payment_id']

# ❌ If ONLY installment (no invoices), last_payment_id = None
if installment_allocations:
    package_service.record_installment_payment(
        payment_id=last_payment_id,  # ← None!
        ...
    )
```

**After (Correct):**
```python
if invoice_alloc_list:
    # SCENARIO 1: Has invoice allocations
    result = record_multi_invoice_payment(...)
    last_payment_id = result['payment_id']

elif installment_allocations:
    # SCENARIO 2: ONLY installment allocations
    # ✅ Get the plan's invoice_id
    plan = get_plan_for_installment(installment_id)

    if not plan.invoice_id:
        raise ValueError("Plan not linked to invoice")

    # ✅ Treat as invoice payment
    invoice_alloc_list = [{
        'invoice_id': str(plan.invoice_id),
        'allocated_amount': total_payment
    }]

    result = record_multi_invoice_payment(
        invoice_allocations=invoice_alloc_list,
        ...
    )
    last_payment_id = result['payment_id']

# Update installment records (no AR creation)
if installment_allocations:
    for installment_id, amount in installment_allocations.items():
        package_service.record_installment_payment(
            installment_id=installment_id,
            paid_amount=amount,
            payment_id=last_payment_id,  # ✅ Now always set
            session=session  # ✅ Shared session
        )
```

### 2. `package_payment_service.py` - Installment Payment

**Before (Wrong):**
```python
def _record_installment_payment_internal(...):
    # Update installment
    installment.paid_amount += paid_amount
    installment.status = 'paid'

    # ❌ Create separate AR entry
    create_ar_subledger_entry(
        entry_type='package_installment',
        reference_line_item_id=None,  # NULL
        ...
    )
```

**After (Correct):**
```python
def _record_installment_payment_internal(...):
    # Update installment
    installment.paid_amount += paid_amount
    installment.status = 'paid'

    # ✅ NO AR entry created here
    # AR entries are created by invoice payment flow
    # since plan is linked to invoice

    logger.info(f"✓ Updated installment: paid ₹{paid_amount}")
```

---

## AR Subledger Entries

### For Package Installment Payment of ₹885

**Before (Wrong Design):**
```sql
-- Separate AR entry with no line item
INSERT INTO ar_subledger (
    entry_type,              -- 'package_installment'
    reference_id,            -- payment_id
    reference_type,          -- 'payment'
    reference_line_item_id,  -- NULL ❌
    credit_amount            -- 885.00
);
```

**After (Correct Design):**
```sql
-- Regular invoice payment AR entry
INSERT INTO ar_subledger (
    entry_type,              -- 'payment'
    reference_id,            -- payment_id
    reference_type,          -- 'payment'
    reference_line_item_id,  -- '3b7acedf...' (package line item) ✅
    credit_amount,           -- 885.00
    item_type,               -- 'Package' ✅
    item_name                -- 'Basic Facial Package' ✅
);
```

**Benefits:**
- ✅ Same AR structure as any invoice payment
- ✅ `item_type` and `item_name` populated from invoice line item
- ✅ No special handling needed in reports
- ✅ Invoice `paid_amount` and `balance_due` automatically updated

---

## Invoice Update

When installment payment is recorded:

```sql
-- Before payment
SELECT invoice_id, total_amount, paid_amount, balance_due
FROM invoice_header
WHERE invoice_id = '23be7c9c...';
-- Result: 1770.00, 0.00, 1770.00

-- After ₹885 installment payment
-- Result: 1770.00, 885.00, 885.00
```

The invoice is automatically updated by `record_multi_invoice_payment()`.

---

## Payment Record

```sql
SELECT
    payment_id,
    invoice_id,
    total_amount,
    payment_source
FROM payment_details
WHERE payment_id = 'xyz...';
```

**Result:**
```
payment_id                            | invoice_id                            | total_amount | payment_source
--------------------------------------|---------------------------------------|--------------|---------------
abc-123-...                          | 23be7c9c-3348-4da9-b8c0-54cf0307c02f  | 885.00       | multi_invoice
```

Even though it's a single invoice, we use `record_multi_invoice_payment()` because:
1. It handles line-item level AR creation
2. It updates invoice balances
3. It's the standard payment recording mechanism

---

## Multi-Invoice + Installment Payment

When user pays for **multiple invoices AND installments** in one payment:

```python
# User enters:
# - Invoice 1: ₹1,770
# - Invoice 2: ₹2,000
# - Installment: ₹885
# Total: ₹4,655

# The flow:
invoice_alloc_list = [
    {'invoice_id': 'invoice1', 'allocated_amount': 1770},
    {'invoice_id': 'invoice2', 'allocated_amount': 2000}
]

# ❌ PROBLEM: Installment payment NOT included in invoice_alloc_list!
# ✅ SOLUTION: Add the plan's invoice to the allocation list

plan = get_plan_for_installment(installment_id)
invoice_alloc_list.append({
    'invoice_id': str(plan.invoice_id),
    'allocated_amount': 885  # installment amount
})

# Now record_multi_invoice_payment handles ALL three:
result = record_multi_invoice_payment(
    invoice_allocations=invoice_alloc_list,  # 3 invoices now
    total_payment=4655,
    ...
)
```

**AR Entries Created:**
1. Invoice 1, line item X: ₹1,770 credit
2. Invoice 2, line item Y: ₹2,000 credit
3. Package invoice (plan.invoice_id), package line item: ₹885 credit

**Installment Update:**
```python
# Then update the installment record
record_installment_payment(
    installment_id=installment_id,
    paid_amount=885,
    payment_id=result['payment_id']
)
# This ONLY updates installment.paid_amount and status
# NO AR entry created
```

---

## Database Consistency

### Single Transaction Guarantee

All operations use **one database session**:

```python
with get_db_session() as session:
    # Create payment + AR entries for all invoices (including package)
    result = record_multi_invoice_payment(..., session=session)

    # Update installment records
    for installment_id, amount in installment_allocations.items():
        record_installment_payment(..., session=session)

    # ✅ Commit ALL or rollback ALL
    session.commit()
```

**Atomicity Guaranteed:**
- If installment update fails → payment and AR entries rolled back
- If payment creation fails → nothing committed
- No partial state possible

---

## Reporting

### AR Aging Report

```sql
SELECT
    patient_id,
    item_type,
    item_name,
    SUM(debit_amount) as charges,
    SUM(credit_amount) as payments,
    SUM(debit_amount - credit_amount) as balance
FROM ar_subledger
WHERE entry_type = 'payment'  -- ✅ Includes package installments now
GROUP BY patient_id, item_type, item_name;
```

**No special handling needed** - package installments appear as regular payments.

### Package Payment Status

```sql
SELECT
    ppp.plan_id,
    ppp.package_name,
    ppp.total_amount,
    ppp.paid_amount,
    ppp.total_amount - ppp.paid_amount as balance,
    COUNT(ip.installment_id) as total_installments,
    SUM(CASE WHEN ip.status = 'paid' THEN 1 ELSE 0 END) as paid_installments
FROM package_payment_plans ppp
JOIN installment_payments ip ON ppp.plan_id = ip.plan_id
WHERE ppp.patient_id = :patient_id
GROUP BY ppp.plan_id, ppp.package_name, ppp.total_amount, ppp.paid_amount;
```

Package payment status comes from `package_payment_plans.paid_amount`, which is updated by triggers when AR entries are created.

---

## Summary

### The Design Principle

**Package installment payments are NOT a special case - they're just invoice payments.**

### Why This Works

1. **Package plans are linked to invoices** → Always have `invoice_id`
2. **Installments are payments toward that invoice** → Use standard invoice payment flow
3. **AR entries at line-item level** → Package line item, just like services/medicines
4. **Installment table tracks payment schedule** → Separate concern from AR tracking

### What Changed

| Aspect | Before | After |
|--------|--------|-------|
| Payment `invoice_id` | NULL | Plan's `invoice_id` |
| AR `entry_type` | 'package_installment' | 'payment' |
| AR `reference_line_item_id` | NULL | Package line item ID |
| AR `item_type` | NULL | 'Package' |
| AR `item_name` | NULL | Package name |
| Invoice updates | Manual/None | Automatic |
| Special reporting | Required | Not needed |

### User Impact

Users can now:
- Make payments toward package installments
- See package payments in regular invoice payment reports
- Track AR aging for packages same as services/medicines
- No confusion between "package payments" and "invoice payments" - they're the same!

---

**Status:** ✅ DESIGN CORRECTED - Ready for Testing

