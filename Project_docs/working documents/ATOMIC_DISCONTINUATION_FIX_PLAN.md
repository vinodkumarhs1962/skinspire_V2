# Atomic Discontinuation Fix Plan
**Date**: 2025-11-13
**Issue**: Discontinuation commits before GL posting, causing orphaned data on GL failure

## Problem Analysis

### Current Broken Flow
```python
# app/services/package_payment_service.py:2293-2473 (process_discontinuation)

with get_db_session() as session:  # ← Session A (PARENT)
    # Get plan
    plan = query...

    # Call _handle_discontinuation (GOOD - uses same session)
    discontinuation_result = _handle_discontinuation(plan, ..., db_session=session)

    # Adjustment path (line 2389) - PROBLEM!
    cn_service.create_credit_note(auto_post=True)  # ← Opens Session B (NESTED!)
        with get_db_session() as session:  # ← New session
            create credit note
            post AR/GL
            session.commit()  # ← Session B commits
        # Session B CLOSED

    # Back to Session A
    session.commit()  # ← Line 2431: Commits Session A

# AFTER commit (line 2434) - SEPARATE Session C!
if credit_note_info.get('needs_gl_posting'):
    create_patient_credit_note_gl_entries()  # ← Opens Session C
        with get_db_session() as session:  # ← New session
            if AR/GL posting fails:  # ← TOO LATE!
                # Discontinuation already committed!
```

### Root Causes

**1. Nested Session in Adjustment Path (Line 2389)**
- `create_credit_note()` opens its own session (Line 132 in patient_credit_note_service.py)
- With `auto_post=True`, it posts AR/GL in nested session
- Nested session commits separately from parent

**2. GL Posting After Commit (Line 2434)**
- Main session commits at line 2431
- GL posting happens AFTER (line 2441)
- If GL fails, discontinuation is already saved

**3. No Automatic Rollback**
- SQLAlchemy WOULD rollback on exception
- BUT commit happens before GL posting
- So there's nothing to roll back

## Required Fixes

### Fix 1: Remove Nested Session in Adjustment Path

**Current (Line 2387-2401)**:
```python
# Create new credit note with adjusted amount
cn_service = PatientCreditNoteService()
credit_note_result = cn_service.create_credit_note(
    hospital_id=hospital_id,
    branch_id=plan_branch_id,
    original_invoice_id=str(plan_invoice_id),
    patient_id=str(plan_patient_id),
    total_amount=adjustment_amount,
    reason_code='plan_discontinued',
    reason_description=discontinuation_reason,
    plan_id=str(plan_plan_id),
    user_id=user_id,
    credit_note_date=date.today(),
    auto_post=True  # ← Causes nested GL posting
)
```

**Fixed (Create credit note directly in same session)**:
```python
# Delete old credit note
old_credit_note_id = discontinuation_result['credit_note']['credit_note_id']
from app.models.transaction import PatientCreditNote
old_cn = session.query(PatientCreditNote).filter(
    PatientCreditNote.credit_note_id == old_credit_note_id
).first()
if old_cn:
    session.delete(old_cn)

# Generate credit note number
cn_service = PatientCreditNoteService()
credit_note_number = cn_service.generate_credit_note_number(
    hospital_id, plan_branch_id, session=session  # ← Pass session
)

# Create new credit note directly in same session
import uuid
new_credit_note = PatientCreditNote(
    credit_note_id=uuid.uuid4(),
    hospital_id=hospital_id,
    branch_id=plan_branch_id,
    credit_note_number=credit_note_number,
    original_invoice_id=plan_invoice_id,
    plan_id=plan_plan_id,
    patient_id=plan_patient_id,
    credit_note_date=date.today(),
    total_amount=adjustment_amount,
    reason_code='plan_discontinued',
    reason_description=discontinuation_reason,
    status='draft',
    created_at=datetime.utcnow(),
    created_by=user_id
)

session.add(new_credit_note)
session.flush()  # Get credit_note_id
plan.credit_note_id = new_credit_note.credit_note_id

# Store for GL posting (before commit)
credit_note_info = {
    'credit_note_id': str(new_credit_note.credit_note_id),
    'credit_note_number': credit_note_number,
    'needs_gl_posting': True
}
```

### Fix 2: Move GL Posting Before Commit

**Current (Line 2429-2460)**:
```python
# Commit changes (credit note already created in same transaction)
logger.info(f"🔄 About to commit discontinuation changes for plan {plan_id}")
session.commit()  # ← COMMITS HERE
logger.info(f"✅ Discontinuation changes committed successfully for plan {plan_id}")

# Post GL entries for credit note AFTER commit (separate transaction for GL)
if discontinuation_result.get('credit_note_info') and discontinuation_result['credit_note_info'].get('needs_gl_posting'):
    cn_info = discontinuation_result['credit_note_info']
    logger.info(f"📊 Posting GL entries for credit note {cn_info['credit_note_number']}")

    try:
        from app.services.gl_service import create_patient_credit_note_gl_entries
        gl_result = create_patient_credit_note_gl_entries(
            credit_note_id=cn_info['credit_note_id'],
            hospital_id=hospital_id
            # ❌ No session passed - opens new transaction
        )
```

**Fixed (GL posting BEFORE commit)**:
```python
# Post GL entries for credit note BEFORE commit (atomic transaction)
if discontinuation_result.get('credit_note_info') and discontinuation_result['credit_note_info'].get('needs_gl_posting'):
    cn_info = discontinuation_result['credit_note_info']
    logger.info(f"📊 Posting GL entries for credit note {cn_info['credit_note_number']}")

    from app.services.gl_service import create_patient_credit_note_gl_entries
    gl_result = create_patient_credit_note_gl_entries(
        credit_note_id=cn_info['credit_note_id'],
        hospital_id=hospital_id,
        current_user_id=user_id,
        session=session  # ← Pass session - stays in same transaction!
    )

    if not gl_result.get('success'):
        # GL failed - raise exception to trigger rollback
        error_msg = f"GL posting failed: {gl_result.get('error')}"
        logger.error(f"❌ {error_msg}")
        raise Exception(error_msg)  # ← Automatic rollback!

    # Update result with GL info
    result['credit_note'] = {
        'credit_note_id': cn_info['credit_note_id'],
        'credit_note_number': cn_info['credit_note_number'],
        'ar_entry_id': gl_result.get('ar_entry_id'),
        'gl_transaction_id': gl_result.get('gl_transaction_id')
    }
    logger.info(f"✅ GL entries posted: AR={gl_result.get('ar_entry_id')}, GL={gl_result.get('gl_transaction_id')}")

# Commit ONLY after GL succeeds
logger.info(f"🔄 About to commit discontinuation changes for plan {plan_id}")
session.commit()  # ← Commits only if GL succeeded!
logger.info(f"✅ Discontinuation changes committed successfully for plan {plan_id}")
```

### Fix 3: Exception Handling for Automatic Rollback

**Current (Line 2470-2473)**:
```python
except Exception as e:
    logger.error(f"❌ Error processing discontinuation: {str(e)}", exc_info=True)
    result['error'] = f'Processing error: {str(e)}'
    return result
```

**Fixed (Let exception propagate for rollback)**:
```python
except Exception as e:
    logger.error(f"❌ Error processing discontinuation: {str(e)}", exc_info=True)
    logger.error(f"🔄 Transaction will be rolled back automatically")
    # SQLAlchemy automatically rolls back on exception in `with get_db_session()`
    result['error'] = f'Processing error: {str(e)}'
    return result
```

## Benefits of This Fix

### ✅ Atomic Transaction
```python
# Single atomic transaction
with get_db_session() as session:
    try:
        1. Set plan status = 'discontinued'
        2. Cancel sessions
        3. Waive installments
        4. Create credit note
        5. Post AR entries
        6. Post GL entries
        7. Update credit note as 'posted'

        session.commit()  # ← All or nothing!

    except Exception:
        # Automatic rollback by SQLAlchemy
        # Everything reverted!
```

### ✅ Automatic Rollback on Any Failure
- If GL posting fails → Exception raised
- Exception triggers automatic rollback
- ALL changes reverted:
  - Plan status restored to 'active'
  - Sessions restored to 'scheduled'
  - Installments restored to 'pending'
  - Credit note deleted
  - No orphaned data!

### ✅ No Manual Rollback Needed
User asked: "Will same type of roll back is built into transaction submit?"

Answer: **YES** - with this fix:
- SQLAlchemy's `with get_db_session()` automatically rolls back on exception
- No manual cleanup needed
- No orphaned credit notes
- No partially-completed discontinuations

### ✅ No Nested Sessions
- All operations in single session
- No session B or C
- No premature commits
- Clean transaction boundary

## Files to Modify

### 1. app/services/package_payment_service.py

**Lines to change**: 2387-2473

**Changes**:
1. Replace `create_credit_note()` service call with direct credit note creation
2. Move GL posting before `session.commit()`
3. Pass `session` parameter to `create_patient_credit_note_gl_entries()`
4. Raise exception if GL posting fails (triggers rollback)
5. Remove the "after commit" GL posting block (lines 2434-2460)

### 2. app/services/gl_service.py

**Lines to check**: 2220-2432 (`create_patient_credit_note_gl_entries`)

**Verification needed**:
- ✅ Already has `session` parameter (line 2224)
- ✅ Uses provided session if not None
- ✅ Has idempotent retry logic
- ✅ Has branch_id fallback from invoice

**No changes needed** - function is already correct!

## Testing After Fix

### Test 1: Normal Discontinuation
```
1. Create package plan
2. Complete 1 session
3. Pay 1 installment
4. Discontinue plan
✅ Expected: All succeeds, GL posted, plan=discontinued
```

### Test 2: GL Posting Failure (Automatic Rollback)
```
1. Create package plan with no branch_id
2. Create invoice with no branch_id (simulate bad data)
3. Complete 1 session
4. Pay 1 installment
5. Discontinue plan
❌ GL posting will fail (no branch_id)
✅ Expected: Exception raised, automatic rollback:
   - Plan status = 'active' (restored)
   - Sessions = 'scheduled' (restored)
   - Installments = 'pending' (restored)
   - Credit note deleted (rolled back)
   - Error returned to user
```

### Test 3: Partial Payment + Discontinuation
```
1. Create package plan (₹10,000, 5 sessions)
2. Complete 2 sessions
3. Pay ₹4,000 (partial)
4. Discontinue plan
✅ Expected:
   - Credit note: ₹6,000 (unused 3 sessions)
   - AR/GL posted
   - Plan=discontinued
   - All atomic
```

## Summary

**Problem**: Discontinuation commits before GL posting → Orphaned data on failure

**Solution**: Move GL posting before commit → Atomic transaction with automatic rollback

**Result**:
- ✅ Single atomic transaction
- ✅ Automatic rollback on GL failure
- ✅ No nested sessions
- ✅ No orphaned data
- ✅ No manual cleanup needed

**User's Question**: "Will same type of roll back is built into transaction submit?"

**Answer**: YES - with this fix, SQLAlchemy automatically rolls back on any exception within the `with get_db_session()` block!

## Next Steps

**Confirm approach with user, then**:
1. Modify `process_discontinuation` in package_payment_service.py
2. Test normal discontinuation
3. Test GL failure → verify automatic rollback
4. Document the atomic transaction pattern
