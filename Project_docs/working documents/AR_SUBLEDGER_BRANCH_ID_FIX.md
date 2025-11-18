# AR Subledger branch_id NOT NULL Constraint Fix
**Date**: 2025-01-13
**Issue**: GL posting failing due to NULL branch_id in AR subledger entry

## Error Message

```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.NotNullViolation) null value in column "branch_id" of relation "ar_subledger" violates not-null constraint
DETAIL:  Failing row contains (..., branch_id=null, ...)
```

## Root Cause Analysis

### Problem Flow

1. Package payment plan created with `branch_id=None`
2. Credit note created with `branch_id=plan.branch_id` → `branch_id=None`
3. GL posting attempts to create AR entry with `branch_id=credit_note.branch_id` → `branch_id=None`
4. **Database constraint violation**: `ar_subledger.branch_id` has `NOT NULL` constraint

### Why Plan Has branch_id=None

From the logs:
```
[DEBUG] Record EXISTS in DB: plan_id=..., hospital_id=..., branch_id=None, is_deleted=False
```

The package payment plan was created without a branch_id (likely from an older version or data migration issue).

### Database Constraint

**Table**: `ar_subledger`
**Column**: `branch_id UUID NOT NULL`

The AR subledger table requires `branch_id` to be NOT NULL for proper branch-level accounting segregation.

## Solution Applied

### Fetch branch_id from Original Invoice ✅
**File**: `app/services/gl_service.py:2293-2309`

```python
# 1. CREATE AR SUBLEDGER ENTRY (Credit entry to reduce AR balance)
ar_entry_id = None

# Get branch_id from original invoice (credit_note.branch_id might be None)
ar_branch_id = credit_note.branch_id
if not ar_branch_id and credit_note.original_invoice_id:
    # Fetch branch_id from original invoice
    invoice = session.query(InvoiceHeader).filter(
        InvoiceHeader.invoice_id == credit_note.original_invoice_id
    ).first()
    if invoice:
        ar_branch_id = invoice.branch_id
        logger.info(f"Using invoice branch_id: {ar_branch_id}")

if not ar_branch_id:
    logger.error("Cannot create AR entry: branch_id is required but not found")
    return {
        'success': False,
        'error': 'branch_id is required for AR entry but not found in credit note or invoice'
    }

# ... rest of AR entry creation ...

ar_entry = ARSubledger(
    entry_id=uuid.uuid4(),
    hospital_id=credit_note.hospital_id,
    branch_id=ar_branch_id,  # ✅ Use fetched branch_id
    transaction_date=credit_note.credit_note_date,
    entry_type='credit_note',
    reference_id=str(credit_note.credit_note_id),
    reference_type='credit_note',
    reference_number=credit_note.credit_note_number,
    patient_id=credit_note.patient_id,
    debit_amount=Decimal('0.00'),
    credit_amount=credit_note.total_amount,
    current_balance=new_balance,
    gl_transaction_id=None,
    created_at=datetime.utcnow(),
    created_by=current_user_id
)
```

### Fallback Chain

**Priority Order**:
1. **Credit Note branch_id** (if available)
2. **Original Invoice branch_id** (fallback)
3. **Error** (if neither available)

This ensures:
- ✅ Uses credit note's branch if set
- ✅ Falls back to invoice's branch (correct accounting context)
- ✅ Fails gracefully with clear error if no branch_id found

## Why This Fix is Correct

### 1. Accounting Accuracy ✅
The AR entry should be recorded against the same branch as the original invoice:
- Invoice created in Branch A → AR debit in Branch A
- Credit note for that invoice → AR credit in Branch A

### 2. Data Integrity ✅
Fetching from the invoice ensures:
- The branch_id is valid (invoice already exists)
- The branch_id matches where revenue was originally recorded
- Branch-level P&L remains accurate

### 3. Backward Compatibility ✅
- If credit note has branch_id → uses it directly
- If credit note has NO branch_id → fetches from invoice
- Works with both old and new data

## Long-Term Fix Recommendation

### Update Package Plan Creation

Future package plans should always capture branch_id:

```python
# In package plan creation
plan = PackagePaymentPlan(
    ...
    branch_id=branch_id,  # ✅ Always set branch_id
    ...
)
```

This will prevent the issue at the source.

## Testing Checklist

### Test 1: Plan with branch_id
- [ ] Create package plan WITH branch_id
- [ ] Discontinue plan
- [ ] Verify AR entry created with correct branch_id

### Test 2: Plan without branch_id (Legacy data)
- [ ] Use existing plan WITHOUT branch_id
- [ ] Discontinue plan
- [ ] Verify AR entry created with invoice's branch_id
- [ ] Check logs for "Using invoice branch_id" message

### Test 3: Error Handling
- [ ] Create credit note with no branch_id and no invoice
- [ ] Attempt GL posting
- [ ] Verify clear error message returned

### Verification Queries

```sql
-- Check AR entry created with correct branch_id
SELECT
    entry_id,
    branch_id,
    patient_id,
    entry_type,
    reference_number,
    credit_amount
FROM ar_subledger
WHERE reference_type = 'credit_note'
    AND reference_number = 'CN/2025-2026/00001';

-- Expected: branch_id should match the invoice's branch_id

-- Verify against original invoice
SELECT
    i.invoice_id,
    i.invoice_number,
    i.branch_id AS invoice_branch_id,
    ar.branch_id AS ar_branch_id,
    ar.reference_number AS credit_note_number
FROM invoice_header i
JOIN patient_credit_notes cn ON cn.original_invoice_id = i.invoice_id
JOIN ar_subledger ar ON ar.reference_id = cn.credit_note_id::text
WHERE cn.credit_note_number = 'CN/2025-2026/00001';

-- Expected: invoice_branch_id = ar_branch_id
```

## Files Modified

1. **app/services/gl_service.py**
   - Lines 2293-2309: Added branch_id fetching logic from invoice
   - Line 2328: Use fetched `ar_branch_id` instead of `credit_note.branch_id`

## Summary

**Problem**: AR subledger entry failed due to NULL branch_id violating NOT NULL constraint

**Root Cause**: Package payment plan had NULL branch_id, which propagated to credit note and then to AR entry

**Solution**: Fetch branch_id from original invoice as fallback when credit note's branch_id is NULL

**Result**: ✅ AR entries can now be created even for plans/credit notes with NULL branch_id by using the invoice's branch_id
