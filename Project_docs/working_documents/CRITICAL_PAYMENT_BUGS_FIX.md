# CRITICAL PAYMENT BUGS - Fix Documentation

## Date: 2025-11-15
## File: `app/services/billing_service.py`
## Function: `_record_multi_invoice_payment()`

---

## Bug #1: AR Subledger Entries Only Created When GL Posting Enabled

### Location: Line 2731
```python
if should_post_gl:  # ❌ WRONG - AR should ALWAYS be created!
    try:
        from app.services.subledger_service import create_ar_subledger_entry
        # ... AR creation code ...
```

### Impact:
- **CRITICAL**: When payments are in "draft" or "pending_approval" status (should_post_gl=False), NO AR entries are created
- This causes:
  - Invoice balances remain unchanged
  - Payments appear in payment_details but have no AR allocations
  - Reports show incorrect outstanding amounts
  - Payment-to-invoice linkage is missing

### Root Cause:
AR subledger entries are fundamental to accounts receivable tracking and should be created REGARDLESS of GL posting status. GL posting can be deferred until approval, but AR must be tracked immediately.

### Fix:
Remove the `if should_post_gl:` wrapper from AR creation. AR entries should ALWAYS be created. Only GL posting should be conditional.

```python
# ❌ BEFORE (Wrong):
if should_post_gl:
    # Create AR entries...

# ✅ AFTER (Correct):
# ALWAYS create AR entries regardless of GL posting
try:
    from app.services.subledger_service import create_ar_subledger_entry
    # ... AR creation code ...
```

---

## Bug #2: Undefined Variable in GL Posting

### Location: Line 2709
```python
gl_result = create_multi_invoice_payment_gl_entries(
    payment_id=payment.payment_id,
    invoice_count=len(invoice_allocations),
    current_user_id=created_by,  # ❌ WRONG - 'created_by' is undefined!
    session=session
)
```

### Impact:
- NameError: name 'created_by' is not defined
- GL posting fails silently (wrapped in try-except)
- No GL transaction/entries created
- Financial reports incorrect

### Root Cause:
Copy-paste error - the variable is `recorded_by` not `created_by`

### Fix:
```python
# ❌ BEFORE (Wrong):
current_user_id=created_by,

# ✅ AFTER (Correct):
current_user_id=recorded_by,
```

---

## Bug #3: Missing Traceability Fields Population

### Location: Lines 2661-2681 (PaymentDetail creation)

### Impact:
- `patient_id` not populated (requires join to get)
- `branch_id` not populated (requires join to get)
- `payment_source` not set
- `invoice_count` not set
- `recorded_by` not set

### Fix:
Add after line 2692 (after session.add(payment)):
```python
# ✅ Populate new traceability fields (added 2025-11-15)
payment.patient_id = patient_id
payment.branch_id = first_invoice.branch_id
payment.payment_source = 'multi_invoice'
payment.invoice_count = len(invoice_allocations)
payment.recorded_by = recorded_by
```

---

## Testing the Fixes:

### Test Case 1: Draft Payment
```python
# Create draft payment (should_post_gl = False)
result = record_multi_invoice_payment(
    hospital_id=hospital_id,
    invoice_allocations=[...],
    payment_date=date.today(),
    cash_amount=Decimal('1000'),
    save_as_draft=True  # This sets should_post_gl = False
)

# Expected Results:
# ✅ Payment created
# ✅ AR entries created (5 entries matching invoice allocations)
# ✅ Invoice balances updated
# ❌ GL transaction NOT created (correct - draft shouldn't post to GL)
```

### Test Case 2: Auto-Approved Payment
```python
# Create approved payment (should_post_gl = True)
result = record_multi_invoice_payment(
    hospital_id=hospital_id,
    invoice_allocations=[...],
    payment_date=date.today(),
    cash_amount=Decimal('1000'),
    save_as_draft=False,
    approval_threshold=Decimal('100000')  # Payment < threshold = auto-approved
)

# Expected Results:
# ✅ Payment created with workflow_status='approved'
# ✅ AR entries created (matching total payment amount)
# ✅ Invoice balances updated
# ✅ GL transaction created
# ✅ GL entries created (Cash debit + AR credit)
```

---

## Migration/Backfill Required:

For the existing payment (PMT-2025-000104):
1. Missing AR entries: ₹3,146.67 (₹10,646.67 total - ₹7,500 recorded)
2. Missing GL transaction
3. Missing GL entries
4. Missing traceability fields (patient_id, branch_id already backfilled by migration)

---

## Files to Modify:

1. `app/services/billing_service.py` - Fix the bugs
2. `backfill_payment_PMT-2025-000104.py` - Script to fix the broken payment
3. `app/models/transaction.py` - Add new traceability fields to model (already attempted, pending file lock resolution)
4. `app/config/modules/patient_payment_config.py` - Add new fields to config

---

## Priority: CRITICAL

These bugs affect the fundamental integrity of the payment system. Every multi-invoice payment currently has incorrect AR and GL entries.
