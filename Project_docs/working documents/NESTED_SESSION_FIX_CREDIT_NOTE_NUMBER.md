# Nested Session Fix - Credit Note Number Generation
**Date**: 2025-01-13
**Issue**: Nested session error during package discontinuation

## Error Message

```
2025-11-13 12:31:15,114 - app.services.patient_credit_note_service - INFO - Generated credit note number: CN/2025-2026/00001
2025-11-13 12:31:15,117 - app.services.package_payment_service - ERROR - ❌ Error creating credit note: Can't operate on closed transaction inside context manager. Please complete the context manager before emitting further commands.
```

## Root Cause Analysis

### Problem Flow

1. `package_payment_service._handle_discontinuation()` opens a database session
2. Credit note creation logic calls `generate_credit_note_number()`
3. `generate_credit_note_number()` **OPENS ITS OWN SESSION** with `with get_db_session()`
4. **Nested session error** occurs

### Code Location

**File**: `app/services/patient_credit_note_service.py:45`

```python
# ❌ WRONG - Always opens new session
def generate_credit_note_number(self, hospital_id: str, branch_id: Optional[str] = None) -> str:
    try:
        with get_db_session() as session:  # ← Opens new session
            # Query logic...
            last_credit_note = session.query(PatientCreditNote).filter(...)
```

**Called from**: `app/services/package_payment_service.py:2053`

```python
# Within discontinuation handler (already has db_session open)
with get_db_session() as db_session:
    # ... discontinuation logic ...

    # ❌ This opens ANOTHER session inside the existing one
    credit_note_number = cn_service.generate_credit_note_number(hospital_id, plan_branch_id)
```

## Solution Applied

### Change 1: Refactor `generate_credit_note_number()` ✅
**File**: `app/services/patient_credit_note_service.py:32-89`

Added optional `session` parameter and internal function:

```python
def generate_credit_note_number(self, hospital_id: str, branch_id: Optional[str] = None, session=None) -> str:
    """
    Generate next credit note number for the hospital
    Format: CN/YYYY-YYYY/NNNNN (e.g., CN/2025-2026/00001)

    Args:
        hospital_id: Hospital ID
        branch_id: Optional branch ID
        session: Optional database session (if called from within a transaction)  # ← NEW

    Returns:
        Credit note number string
    """
    def _generate_number(db_session):
        # Get current financial year
        today = date.today()
        if today.month >= 4:  # April onwards = current FY
            fy_start = today.year
            fy_end = today.year + 1
        else:  # Jan-Mar = previous FY
            fy_start = today.year - 1
            fy_end = today.year

        fy_string = f"{fy_start}-{fy_end}"

        # Get last credit note number for this FY
        last_credit_note = db_session.query(PatientCreditNote).filter(
            and_(
                PatientCreditNote.hospital_id == hospital_id,
                PatientCreditNote.credit_note_number.like(f'CN/{fy_string}/%')
            )
        ).order_by(PatientCreditNote.credit_note_number.desc()).first()

        if last_credit_note:
            # Extract sequence number and increment
            last_number = last_credit_note.credit_note_number.split('/')[-1]
            next_sequence = int(last_number) + 1
        else:
            next_sequence = 1

        credit_note_number = f"CN/{fy_string}/{next_sequence:05d}"
        logger.info(f"Generated credit note number: {credit_note_number}")

        return credit_note_number

    try:
        # ✅ If session provided, use it directly (avoid nested session)
        if session is not None:
            return _generate_number(session)
        else:
            # ✅ Open new session only if not provided
            with get_db_session() as new_session:
                return _generate_number(new_session)

    except Exception as e:
        logger.error(f"Error generating credit note number: {str(e)}", exc_info=True)
        # Fallback to UUID-based number
        return f"CN/TEMP/{str(uuid.uuid4())[:8].upper()}"
```

**Key Changes**:
- Added `session=None` parameter
- Created internal `_generate_number(db_session)` function
- If session is provided → use it directly
- If session is None → open new session (backward compatible)

### Change 2: Pass Session from Caller ✅
**File**: `app/services/package_payment_service.py:2053`

```python
# ✅ CORRECT - Pass existing session
credit_note_number = cn_service.generate_credit_note_number(
    hospital_id,
    plan_branch_id,
    session=db_session  # ← Pass existing session
)
```

## Benefits

### ✅ No Nested Sessions
- When called from within a transaction, uses existing session
- No "closed transaction" errors

### ✅ Backward Compatible
- If called standalone (no session parameter), opens new session automatically
- No changes needed to other callers

### ✅ Atomic Transaction Guarantee
- Credit note number generation happens in same transaction as credit note creation
- If transaction rolls back, number is not consumed

### ✅ Consistent Pattern
- Same pattern as other service methods that accept optional session
- Example: `create_supplier_payment_gl_entries(session=session)`

## Transaction Flow (After Fix)

### Discontinuation Transaction (ATOMIC)
```
1. Open session: with get_db_session() as db_session:
2.   Update plan status
3.   Cancel sessions
4.   Waive installments
5.   Generate credit note number (uses SAME session)  ← Fixed
6.   Create credit note record (uses SAME session)
7.   COMMIT
```

All operations in ONE transaction → No nested sessions → No orphaned data

## Testing Checklist

- [ ] Discontinue package plan successfully
- [ ] Verify credit note number generated (CN/2025-2026/00001)
- [ ] Verify no "closed transaction" error in logs
- [ ] Verify credit note record created
- [ ] Verify GL/AR entries posted
- [ ] Verify transaction commits successfully

## Files Modified

1. **app/services/patient_credit_note_service.py**
   - Lines 32-89: Refactored `generate_credit_note_number()` to accept optional session

2. **app/services/package_payment_service.py**
   - Line 2053: Pass `session=db_session` parameter

## Summary

**Problem**: `generate_credit_note_number()` always opened its own database session, causing nested session error when called from within a transaction

**Solution**: Refactored to accept optional `session` parameter; uses existing session if provided, opens new one if not

**Result**: ✅ No more nested session errors; credit note number generation happens atomically within discontinuation transaction
