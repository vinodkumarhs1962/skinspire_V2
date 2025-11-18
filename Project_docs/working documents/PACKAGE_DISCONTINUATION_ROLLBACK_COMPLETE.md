# Package Discontinuation Rollback - Complete
**Date**: 2025-11-13
**Plan ID**: 8dcec648-4228-4046-8e62-9e105efd9d7b

## Why Rollback Was Needed

The discontinuation transaction was **incomplete** because:
1. ❌ GL entries failed to post (branch_id NULL constraint)
2. ❌ Credit note created but not posted (status='draft', gl_posted=false)
3. ❌ Invoice line items not updated to reflect discontinuation

**User Decision**: Since GL posting failed, the entire discontinuation should be rolled back to maintain data integrity.

## Rollback Actions Performed

### 1. Payment Plan Restored to Active ✅
```sql
UPDATE package_payment_plans
SET status = 'active',
    discontinued_at = NULL,
    discontinued_by = NULL,
    discontinuation_reason = NULL,
    refund_amount = NULL,
    refund_status = 'none',
    credit_note_id = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE plan_id = '8dcec648-4228-4046-8e62-9e105efd9d7b';
```

**Result**: 1 row updated

### 2. Sessions Restored to Scheduled ✅
```sql
UPDATE package_sessions
SET session_status = 'scheduled',
    service_notes = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE plan_id = '8dcec648-4228-4046-8e62-9e105efd9d7b'
  AND session_status = 'cancelled';
```

**Result**: 4 sessions restored (sessions 2, 3, 4, 5)

### 3. Installments Restored to Pending ✅
```sql
UPDATE installment_payments
SET status = 'pending',
    notes = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE plan_id = '8dcec648-4228-4046-8e62-9e105efd9d7b'
  AND status = 'waived';
```

**Result**: 2 installments restored (installments 2, 3)

### 4. Draft Credit Note Deleted ✅
```sql
DELETE FROM patient_credit_notes
WHERE credit_note_id = 'e1b95018-5874-45a1-9369-abf001b27287'
  AND status = 'draft'
  AND gl_posted = false;
```

**Result**: 1 credit note deleted (CN/2025-2026/00001)

## Current State After Rollback

### Payment Plan: 8dcec648-4228-4046-8e62-9e105efd9d7b
```
Package: Weight Loss Program
Status: active ✅ (RESTORED)
Total Sessions: 5
Completed Sessions: 1
Remaining Sessions: 4
Total Amount: ₹9,440.00
Paid Amount: ₹3,146.67
Balance: ₹6,293.33

Discontinuation Fields (ALL CLEARED):
├─ discontinued_at: NULL ✅
├─ discontinued_by: NULL ✅
├─ discontinuation_reason: NULL ✅
├─ refund_amount: NULL ✅
├─ refund_status: 'none' ✅
└─ credit_note_id: NULL ✅
```

### Sessions: 5 Total
```
Session 1: completed (procedure done) ✅
Session 2: scheduled ✅ (RESTORED)
Session 3: scheduled ✅ (RESTORED)
Session 4: scheduled ✅ (RESTORED)
Session 5: scheduled ✅ (RESTORED)
```

### Installments: 3 Total
```
Installment 1: ₹3,146.67 - paid ✅
Installment 2: ₹3,146.67 - pending ✅ (RESTORED)
Installment 3: ₹3,146.66 - pending ✅ (RESTORED)
```

### Credit Note: DELETED
```
Credit Note CN/2025-2026/00001: DELETED ✅
(Was: draft, not posted, ₹7,552)
```

## Database Trigger Removed

As per user policy (no database triggers), the trigger that was causing status overwrites has been removed:
```sql
DROP TRIGGER IF EXISTS trg_update_package_status ON installment_payments;
DROP FUNCTION IF EXISTS update_package_plan_status();
```

**Policy**: ✅ All business logic in Python only - no database triggers or stored procedures

## What Happens Next Time

When you attempt discontinuation again, the following must succeed **atomically**:

1. ✅ Python code sets status to 'discontinued'
2. ✅ Sessions cancelled
3. ✅ Installments waived
4. ✅ Credit note created
5. ✅ **AR/GL entries posted** (THIS MUST SUCCEED)
6. ✅ Credit note marked as 'posted'
7. ✅ Transaction committed

If ANY step fails → entire transaction should ROLLBACK automatically.

## Fixes Already in Place for Next Attempt

### Fix 1: branch_id Fallback ✅
**File**: `app/services/gl_service.py:2293-2362`

GL posting now fetches branch_id from original invoice if not on credit note:
```python
ar_branch_id = credit_note.branch_id
if not ar_branch_id and credit_note.original_invoice_id:
    invoice = session.query(InvoiceHeader).filter(...).first()
    if invoice:
        ar_branch_id = invoice.branch_id
```

This fixes the "branch_id NULL constraint" error.

### Fix 2: Idempotent Retry Pattern ✅
**File**: `app/services/gl_service.py:2280-2432`

GL posting is now retry-safe:
- Level 1: Already posted? → Skip
- Level 2: AR and GL exist but flag not set? → Just set flag
- Level 3: AR exists? → Skip AR, create GL
- Level 3: GL exists? → Skip GL, just link
- Level 4: Nothing exists? → Create both

### Fix 3: No Database Trigger ✅
Removed trigger that was overwriting 'discontinued' status to 'completed'.

## Recommendation: Atomic Discontinuation

The discontinuation should be handled in a **single atomic transaction**:

### Current Implementation (Two Transactions - PROBLEMATIC)
```python
# Transaction 1: Discontinuation
with get_db_session() as session:
    plan.status = 'discontinued'
    credit_note = create_credit_note()
    session.commit()  # ← Commits even if GL fails

# Transaction 2: GL Posting (SEPARATE - CAN FAIL)
gl_result = create_patient_credit_note_gl_entries()  # ← Can fail
```

**Problem**: If GL posting fails, discontinuation is already committed!

### Recommended Implementation (Single Transaction)
```python
# Single atomic transaction
with get_db_session() as session:
    # 1. Discontinuation
    plan.status = 'discontinued'
    credit_note = create_credit_note_in_same_session(session)

    # 2. GL posting in SAME session
    create_ar_entry(session)
    create_gl_entries(session)

    # 3. Mark as posted
    credit_note.gl_posted = True

    # 4. Commit ONLY if everything succeeds
    session.commit()  # ← Atomic - all or nothing
```

**File to Update**: `app/services/package_payment_service.py:2293-2473` (process_discontinuation)

## Testing Checklist Before Next Discontinuation

Before attempting discontinuation again, verify:

1. ✅ Plan has branch_id OR invoice has branch_id
2. ✅ Database trigger removed (verified above)
3. ✅ GL service has branch_id fallback logic
4. ✅ Credit note service accepts session parameter (nested session fix)
5. ⚠️ Consider: Make GL posting part of same transaction (atomic)

## Summary

**Before Rollback**:
- Status: discontinued (but GL failed)
- Sessions: 1 completed, 4 cancelled
- Installments: 1 paid, 2 waived
- Credit Note: CN/2025-2026/00001 (draft, not posted)

**After Rollback** ✅:
- Status: **active** (RESTORED)
- Sessions: 1 completed, 4 **scheduled** (RESTORED)
- Installments: 1 paid, 2 **pending** (RESTORED)
- Credit Note: **DELETED**

**Plan is now in original state** - ready for correct discontinuation attempt.

**Key Lesson**: GL posting must succeed before committing discontinuation. Consider atomic transaction approach.
