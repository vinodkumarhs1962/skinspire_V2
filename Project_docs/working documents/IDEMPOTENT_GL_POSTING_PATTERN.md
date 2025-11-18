# Idempotent GL Posting Pattern - Best Practice Implementation
**Date**: 2025-01-13
**Topic**: How to handle GL posting retries in accounting systems

## The Question

> "I see credit note posted but failed at GL level. So if we need to post transaction again, it should either overwrite or keep same and change the GL posted flag as true. What is the best practice?"

## Best Practice Answer: **Idempotent Retry Pattern** ✅

**Never delete or overwrite accounting entries. Always check and skip or create missing.**

### Why This Pattern?

In accounting systems, the **audit trail** is sacrosanct. According to accounting standards:

1. **GAAP/IFRS Requirement**: All entries must be traceable
2. **Audit Compliance**: Never delete entries (use reversals instead)
3. **Data Integrity**: Prevent duplicate entries
4. **Idempotency**: Retry operations should be safe

## Implementation Pattern

### 3-Level Check Strategy

```python
def create_patient_credit_note_gl_entries(...):
    """
    Level 1: Check if FULLY posted
    Level 2: Check if PARTIALLY posted (retry scenario)
    Level 3: Create FRESH entries
    """

    # LEVEL 1: Already fully posted ✅
    if credit_note.gl_posted and credit_note.gl_transaction_id:
        # Return existing IDs (idempotent)
        return {
            'success': True,
            'message': 'Already posted',
            'ar_entry_id': existing_ar_id,
            'gl_transaction_id': credit_note.gl_transaction_id
        }

    # LEVEL 2: Check for partial posting (AR or GL exists but flag not set)
    existing_ar = check_ar_entry(credit_note_id)
    existing_gl = check_gl_transaction(credit_note_id)

    if existing_ar and existing_gl:
        # Both exist - just update flag ✅
        credit_note.gl_posted = True
        credit_note.gl_transaction_id = existing_gl.transaction_id
        return success

    # LEVEL 3: Create missing entries
    if not existing_ar:
        create_ar_entry()  # Create AR

    if not existing_gl:
        create_gl_transaction()  # Create GL

    # Update flag
    credit_note.gl_posted = True
    return success
```

### Failure Scenarios Handled

| Scenario | AR Entry | GL Transaction | Flag | Action |
|----------|----------|----------------|------|--------|
| **Fresh** | ❌ | ❌ | False | Create both + set flag |
| **AR Created, GL Failed** | ✅ | ❌ | False | Skip AR, create GL, set flag |
| **GL Created, AR Failed** | ❌ | ✅ | False | Create AR, skip GL, set flag |
| **Both Created, Flag Failed** | ✅ | ✅ | False | Skip both, set flag only |
| **Fully Posted** | ✅ | ✅ | True | Return success immediately |

## Code Implementation

### File: `app/services/gl_service.py`

**Lines 2280-2337: Level 1 & 2 Checks**

```python
# LEVEL 1: Check if already posted (fully completed)
if credit_note.gl_posted and credit_note.gl_transaction_id:
    logger.info(f"✅ Credit note {credit_note.credit_note_number} already posted to GL")

    # Get existing AR entry ID
    existing_ar = session.query(ARSubledger).filter(
        and_(
            ARSubledger.reference_type == 'credit_note',
            ARSubledger.reference_id == str(credit_note.credit_note_id)
        )
    ).first()

    return {
        'success': True,
        'message': 'Credit note already posted',
        'ar_entry_id': str(existing_ar.entry_id) if existing_ar else None,
        'gl_transaction_id': str(credit_note.gl_transaction_id)
    }

# LEVEL 2: Check for partial posting (entries exist but flag not set)
# This handles retry scenarios where posting partially succeeded
existing_ar = session.query(ARSubledger).filter(
    and_(
        ARSubledger.reference_type == 'credit_note',
        ARSubledger.reference_id == str(credit_note.credit_note_id)
    )
).first()

existing_gl = session.query(GLTransaction).filter(
    and_(
        GLTransaction.source_document_type == 'credit_note',
        GLTransaction.source_document_id == credit_note.credit_note_id
    )
).first()

if existing_ar and existing_gl:
    # Both AR and GL exist - just update the flag (idempotent retry)
    logger.info(f"🔄 Found existing GL entries for credit note {credit_note.credit_note_number}, updating status")
    credit_note.gl_posted = True
    credit_note.gl_transaction_id = existing_gl.transaction_id
    credit_note.posted_at = datetime.utcnow()
    credit_note.posted_by = current_user_id
    credit_note.status = 'posted'

    session.flush()

    return {
        'success': True,
        'ar_entry_id': str(existing_ar.entry_id),
        'gl_transaction_id': str(existing_gl.transaction_id),
        'message': f'GL entries found and status updated for credit note {credit_note.credit_note_number}'
    }

# If partial entries exist, log warning (should not happen in normal flow)
if existing_ar or existing_gl:
    logger.warning(f"⚠️ Partial posting detected - AR: {bool(existing_ar)}, GL: {bool(existing_gl)}")
    # Continue to create missing entries below
```

**Lines 2341-2400: Level 3 - Skip or Create AR**

```python
# 1. CREATE AR SUBLEDGER ENTRY (Credit entry to reduce AR balance)
ar_entry_id = None

# Skip AR creation if already exists
if existing_ar:
    logger.info(f"✅ AR entry already exists, skipping creation")
    ar_entry_id = str(existing_ar.entry_id)
else:
    # Get branch_id from original invoice
    ar_branch_id = credit_note.branch_id
    if not ar_branch_id and credit_note.original_invoice_id:
        invoice = session.query(InvoiceHeader).filter(
            InvoiceHeader.invoice_id == credit_note.original_invoice_id
        ).first()
        if invoice:
            ar_branch_id = invoice.branch_id

    if not ar_branch_id:
        return {'success': False, 'error': 'branch_id required'}

    # Create AR entry
    ar_entry = ARSubledger(...)
    session.add(ar_entry)
    session.flush()
    ar_entry_id = str(ar_entry.entry_id)
```

**Lines 2404-2432: Skip or Create GL**

```python
# 2. CREATE GL TRANSACTION AND ENTRIES

# Skip GL creation if already exists
if existing_gl:
    logger.info(f"✅ GL transaction already exists, skipping creation")

    # Link AR entry to existing GL transaction if not already linked
    if ar_entry_id and not existing_ar:
        ar_entry = session.query(ARSubledger).filter(
            ARSubledger.entry_id == ar_entry_id
        ).first()
        if ar_entry:
            ar_entry.gl_transaction_id = existing_gl.transaction_id

    # Update credit note with GL posting info
    credit_note.gl_posted = True
    credit_note.gl_transaction_id = existing_gl.transaction_id
    credit_note.posted_at = datetime.utcnow()
    credit_note.posted_by = current_user_id
    credit_note.status = 'posted'

    session.flush()

    return {
        'success': True,
        'ar_entry_id': ar_entry_id,
        'gl_transaction_id': str(existing_gl.transaction_id),
        'message': f'GL entries already exist, status updated'
    }

# If GL doesn't exist, create it below...
```

## Alternative Patterns (NOT Recommended)

### ❌ Pattern A: Delete and Recreate
```python
# DON'T DO THIS
if existing_entries:
    delete_all_entries()  # ❌ Breaks audit trail
    create_fresh_entries()
```

**Why not?**
- Violates GAAP audit requirements
- Breaks audit trail
- Risk of data loss
- Compliance issues

### ❌ Pattern B: Always Create New
```python
# DON'T DO THIS
create_new_ar_entry()  # ❌ Creates duplicates
create_new_gl_transaction()
```

**Why not?**
- Creates duplicate entries
- Double-counts in financial reports
- Violates double-entry bookkeeping

### ❌ Pattern C: Overwrite Existing
```python
# DON'T DO THIS
UPDATE ar_subledger SET ... WHERE entry_id = existing_id  # ❌ Loses history
```

**Why not?**
- Loses original data
- Can't track what changed
- Audit trail compromised

## Testing Scenarios

### Test 1: Normal Flow (Fresh Creation)
```sql
-- Before: No entries exist
SELECT * FROM ar_subledger WHERE reference_id = '<credit_note_id>';
-- Returns: 0 rows

-- After: Retry call
-- Expected: 1 AR entry, 1 GL transaction, flag = true
```

### Test 2: AR Created, GL Failed (Partial)
```sql
-- Setup: Create AR manually, leave GL empty
INSERT INTO ar_subledger (...) VALUES (...);

-- Call: create_patient_credit_note_gl_entries()
-- Expected: Skips AR creation, creates GL, sets flag
```

### Test 3: Both Exist, Flag Not Set (Flag Failure)
```sql
-- Setup: Both AR and GL exist
INSERT INTO ar_subledger (...);
INSERT INTO gl_transactions (...);
UPDATE patient_credit_notes SET gl_posted = FALSE;

-- Call: create_patient_credit_note_gl_entries()
-- Expected: Skips both, updates flag only
```

### Test 4: Already Fully Posted (Idempotency Check)
```sql
-- Setup: Everything complete
UPDATE patient_credit_notes SET gl_posted = TRUE;

-- Call: create_patient_credit_note_gl_entries() -- 3 times
-- Expected: All 3 calls return success with same IDs
```

## Benefits of This Pattern

### ✅ Idempotency
Calling the function multiple times produces the same result:
- No duplicate entries
- No errors on retry
- Safe to call from async jobs

### ✅ Audit Compliance
- Never deletes accounting entries
- All entries are traceable
- Meets GAAP/IFRS requirements

### ✅ Partial Failure Recovery
Handles all failure scenarios:
- AR created, GL failed → Retry creates GL only
- Both created, flag failed → Retry sets flag only
- Nothing created → Retry creates both

### ✅ Clear Logging
Each scenario is logged distinctly:
- `✅ Already posted` - Fully complete
- `🔄 Found existing entries` - Partial completion
- `⚠️ Partial posting detected` - Unusual state
- `✅ Created new entry` - Fresh creation

## When to Use Other Patterns

### Reversal Pattern (For Corrections)
```python
# USE THIS for correcting WRONG entries
def reverse_credit_note_gl_entries(...):
    """Create reversal entries (not deletion)"""
    # Create opposite entries
    create_ar_entry(debit=-original_credit)
    create_gl_entry(debit=-original_debit, credit=-original_credit)
```

**When**: Need to correct an error AFTER posting
**How**: Create opposite sign entries
**Result**: Original + Reversal = Net zero

### Delete Pattern (Only for DRAFT)
```python
# ONLY for unposted drafts
def delete_draft_credit_note(...):
    if credit_note.gl_posted:
        raise Exception("Cannot delete posted entries")

    # Safe to delete draft
    delete_credit_note()
```

**When**: Credit note still in draft (not posted)
**How**: Hard delete
**Result**: Entry removed completely

## Summary

**Question**: Overwrite or update flag?

**Answer**: **Neither!** Use idempotent check-and-skip pattern:
1. Check if already complete → Return success
2. Check if partially complete → Complete missing parts
3. If nothing exists → Create fresh

**Benefits**:
- ✅ Safe to retry
- ✅ Preserves audit trail
- ✅ Prevents duplicates
- ✅ Handles all failure scenarios

**Files Modified**:
- `app/services/gl_service.py` (Lines 2280-2432)

**Result**: Robust, audit-compliant GL posting that handles retries gracefully! ✅
