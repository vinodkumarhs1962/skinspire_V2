# Package Discontinuation Trigger Bug Fix
**Date**: 2025-11-13
**Issue**: Database trigger overwrote 'discontinued' status to 'completed'

## Problem Summary

### What Happened
When discontinuing package payment plan `8dcec648-4228-4046-8e62-9e105efd9d7b`:
1. ✅ Discontinuation logic ran correctly in Python
2. ✅ Credit note created: CN/2025-2026/00001 (₹7,552)
3. ✅ Sessions cancelled (4 sessions)
4. ✅ Installments waived (2 installments)
5. ✅ Status set to 'discontinued'
6. ❌ GL posting failed (branch_id NULL constraint - already fixed in previous session)
7. ❌ **Database trigger overwrote status to 'completed'**

### Root Cause
Database had a trigger `trg_update_package_status` that automatically set plan status to 'completed' when all installments were marked as 'paid' or 'waived'.

**Trigger Logic**:
```sql
CREATE TRIGGER trg_update_package_status
AFTER UPDATE OF status ON installment_payments
FOR EACH ROW
WHEN (NEW.status IN ('paid', 'waived'))
EXECUTE FUNCTION update_package_plan_status();

-- Function checked: if all installments paid/waived → set plan status to 'completed'
```

**The Bug**:
During discontinuation, we waive pending installments. This triggered the function, which saw all installments as 'paid' or 'waived', and automatically changed status from 'discontinued' → 'completed'.

## Timeline

**12:35:48** - Discontinuation started
- Python code set `plan.status = 'discontinued'`
- Credit note created
- 4 sessions cancelled
- 2 installments set to `status = 'waived'`

**12:35:48** - Trigger fired (AFTER UPDATE on installments)
- Detected all installments are 'paid' or 'waived'
- Overwrote `plan.status = 'completed'`

**12:35:48** - Transaction committed
- Plan status saved as 'completed' (wrong!)
- Credit note saved as 'draft', gl_posted=false

**12:35:48** - GL posting attempted (separate transaction)
- Failed with branch_id NULL constraint
- This is why credit note exists but GL not posted

## Fix Applied

### Step 1: Removed Database Trigger (Following User Policy)
User policy: **No database triggers or stored procedures - keep logic in Python only**

```sql
DROP TRIGGER IF EXISTS trg_update_package_status ON installment_payments;
DROP FUNCTION IF EXISTS update_package_plan_status();
```

**Result**: ✅ Trigger and function removed from database

### Step 2: Fixed Data
Corrected the payment plan status:

```sql
UPDATE package_payment_plans
SET status = 'discontinued', updated_at = CURRENT_TIMESTAMP
WHERE plan_id = '8dcec648-4228-4046-8e62-9e105efd9d7b'
AND discontinued_at IS NOT NULL;
```

**Result**: ✅ Status changed from 'completed' to 'discontinued'

### Step 3: Current State
```
Package Payment Plan: 8dcec648-4228-4046-8e62-9e105efd9d7b
├─ Status: discontinued ✅ (FIXED)
├─ Discontinued At: 2025-11-13 07:05:48
├─ Discontinuation Reason: "nony 2"
├─ Credit Note ID: e1b95018-5874-45a1-9369-abf001b27287
│
Credit Note: CN/2025-2026/00001
├─ Total Amount: ₹7,552
├─ Status: draft
├─ GL Posted: false ❌ (Needs retry)
│
Sessions: 5 total, 1 completed, 4 cancelled ✅
Installments: 3 total, 1 paid, 2 waived ✅
```

## Outstanding Issue: GL Posting

The credit note `CN/2025-2026/00001` exists but GL posting failed due to branch_id NULL constraint (this was fixed in earlier session with idempotent retry pattern).

**To Retry GL Posting**:
The idempotent retry pattern in `gl_service.py` will handle this safely:

```python
from app.services.gl_service import create_patient_credit_note_gl_entries

# Safe to call multiple times (idempotent)
result = create_patient_credit_note_gl_entries(
    credit_note_id='e1b95018-5874-45a1-9369-abf001b27287',
    hospital_id='4ef72e18-e65d-4766-b9eb-0308c42485ca'
)

# Will:
# 1. Check if already posted → skip if yes
# 2. Check if AR/GL exist but flag not set → just set flag
# 3. Create missing AR/GL entries → uses branch_id from invoice (fixed)
```

**Note**: The branch_id NULL constraint fix we did in `gl_service.py:2293-2362` will now fetch branch_id from the original invoice, so retry will succeed.

## Python Code Status Updates (No Trigger Needed)

Since we removed the trigger, status updates must be handled in Python code. Here are the locations:

### 1. Discontinuation → 'discontinued'
**File**: `app/services/package_payment_service.py:2018`
```python
plan.status = 'discontinued'
plan.discontinued_at = datetime.utcnow()
plan.discontinued_by = user_id
plan.discontinuation_reason = discontinuation_reason
```
✅ Already implemented correctly

### 2. Manual Completion (if needed in future)
If you need to manually mark a plan as 'completed' when all sessions are done and all payments received:
```python
# Check conditions
all_sessions_completed = plan.completed_sessions == plan.total_sessions
all_payments_received = plan.paid_amount >= plan.total_amount

if all_sessions_completed and all_payments_received:
    plan.status = 'completed'
```
⚠️ This is NOT currently implemented - add if business logic requires auto-completion

### 3. Cancellation → 'cancelled'
**Current**: Not implemented
**If needed**: Add explicit status update in cancellation handler

### 4. Suspension → 'suspended'
**Current**: Not implemented
**If needed**: Add explicit status update in suspension handler

## Benefits of Removing Trigger

✅ **Policy Compliance**: No database triggers - all logic in Python
✅ **Explicit Control**: Status changes are visible in Python code
✅ **Easier Debugging**: No hidden database logic
✅ **Transaction Safety**: Status updates happen in same transaction as other changes
✅ **No Side Effects**: Waiving installments doesn't auto-complete plans

## Testing Recommendations

### Test 1: Discontinuation
1. Create a package plan
2. Make some payments
3. Complete 1 session
4. Discontinue the plan
5. ✅ Verify status = 'discontinued' (not 'completed')

### Test 2: Normal Completion
1. Create a package plan
2. Complete all sessions
3. Pay all installments
4. ⚠️ Status will NOT auto-change to 'completed'
5. If business requires auto-completion, add Python logic

### Test 3: GL Posting Retry
1. Call `create_patient_credit_note_gl_entries()` for credit note `CN/2025-2026/00001`
2. ✅ Should succeed (branch_id fetched from invoice)
3. ✅ AR and GL entries created
4. ✅ Credit note status changes to 'posted'

## Files Modified

### Database
- ❌ Removed: `trg_update_package_status` trigger
- ❌ Removed: `update_package_plan_status()` function

### Python Code
- ✅ No changes needed (already correct)

### Data Fix
- ✅ Fixed: Plan `8dcec648-4228-4046-8e62-9e105efd9d7b` status → 'discontinued'

## Summary

**Problem**: Database trigger overwrote 'discontinued' status to 'completed'
**Root Cause**: Trigger fired when installments were waived during discontinuation
**Solution**: Removed trigger, keep all logic in Python (user policy)
**Status**: ✅ FIXED - Plan now shows 'discontinued' correctly
**Next Step**: Retry GL posting for credit note CN/2025-2026/00001

**User Policy Confirmed**: ✅ No database triggers or stored procedures - Python only
