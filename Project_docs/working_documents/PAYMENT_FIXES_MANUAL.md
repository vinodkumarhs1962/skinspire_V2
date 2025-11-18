# Manual Fixes for billing_service.py

## Critical Bugs to Fix

### File: `app/services/billing_service.py`

---

## FIX #1: Line 2709 - Change `created_by` to `recorded_by`

**Location**: Line 2709
**Current (WRONG)**:
```python
                gl_result = create_multi_invoice_payment_gl_entries(
                    payment_id=payment.payment_id,
                    invoice_count=len(invoice_allocations),
                    current_user_id=created_by,  # ❌ WRONG - undefined variable
                    session=session
                )
```

**Change to (CORRECT)**:
```python
                gl_result = create_multi_invoice_payment_gl_entries(
                    payment_id=payment.payment_id,
                    invoice_count=len(invoice_allocations),
                    current_user_id=recorded_by,  # ✅ Fixed
                    session=session
                )
```

---

## FIX #2: Line 2731 - Remove `if should_post_gl:` wrapper

**Location**: Line 2731
**Current (WRONG)**:
```python
        allocation_results = []

        if should_post_gl:  # ❌ WRONG - AR should ALWAYS be created!
            try:
                from app.services.subledger_service import create_ar_subledger_entry
```

**Change to (CORRECT)**:
```python
        allocation_results = []

        # ✅ CRITICAL: AR entries must ALWAYS be created regardless of GL posting
        try:
            from app.services.subledger_service import create_ar_subledger_entry
```

**Then adjust indentation**: All lines from 2733 to 2846 need to move LEFT by 4 spaces (remove one indent level)

---

## FIX #3: After line 2692 - Add traceability fields

**Location**: After `session.flush()` at line 2693
**Add these lines**:
```python
        session.flush()  # Get payment_id

        # ✅ Populate new traceability fields (Added: 2025-11-15)
        payment.patient_id = patient_id
        payment.branch_id = first_invoice.branch_id
        payment.payment_source = 'multi_invoice'
        payment.invoice_count = len(invoice_allocations)
        payment.recorded_by = recorded_by

        logger.info(f"✓ Created payment {payment.payment_id} for ₹{total_payment} across {len(invoice_allocations)} invoices")
```

---

## Verification After Changes:

Run this to verify the fixes work:
```bash
python -c "from app.services.billing_service import record_multi_invoice_payment; print('Import successful')"
```

Then test with a new payment to ensure:
1. AR entries are created even for draft payments
2. GL entries are created for approved payments
3. All traceability fields are populated
