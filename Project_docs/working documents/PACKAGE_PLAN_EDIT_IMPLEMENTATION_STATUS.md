# Package Payment Plan Edit - Implementation Status

**Last Updated**: 2025-11-12
**Module**: Package Payment Plans
**Service**: `app/services/package_payment_service.py`

---

## Implementation Status Summary

### ✅ COMPLETED FEATURES

#### 1. Edit Form Infrastructure
- ✅ Edit form configuration with proper field definitions
- ✅ Virtual fields for display (`patient_display`, `package_display`)
- ✅ Computed fields (`balance_amount`, `remaining_sessions`)
- ✅ Status dropdown with all 5 options including "Discontinued"
- ✅ Database constraint updated to allow "Discontinued" status
- ✅ Field filtering (virtual/readonly fields excluded from save)
- ✅ Primary key detection fixed for update operations

**Files**:
- `app/config/modules/package_payment_plan_config.py`
- `app/templates/engine/universal_edit.html`
- `app/views/universal_views.py`
- `app/engine/universal_crud_service.py`
- `migrations/add_discontinued_status_to_package_plans.sql`

---

#### 2. Session Replanning Logic
- ✅ Increase sessions: Adds new scheduled sessions
- ✅ Decrease sessions: Removes scheduled sessions beyond new count
- ✅ Validation: Cannot reduce below completed sessions
- ✅ Session numbering maintained correctly
- ✅ Auto-update `completed_sessions` counter on session completion

**Files**:
- `app/services/package_payment_service.py::update_package_payment_plan()`
- `app/services/package_payment_service.py::_replan_sessions()`
- `app/services/package_payment_service.py::complete_session()` (updated)
- `migrations/sync_completed_sessions_count.sql`

**Example**:
```
User changes total_sessions: 5 → 7
System validates: 7 >= completed_sessions (2) ✓
System creates: Session #6 and #7 with status='scheduled'
Result: "Plan updated. Added 2 sessions."
```

---

#### 3. Installment Replanning Logic
- ✅ Increase installments: Adds new pending installments
- ✅ Decrease installments: Removes pending installments
- ✅ Recalculate amounts: Distributes balance across remaining installments
- ✅ Validation: Cannot reduce below paid installments
- ✅ Due date calculation based on frequency (weekly/biweekly/monthly)

**Files**:
- `app/services/package_payment_service.py::_replan_installments()`
- `app/services/package_payment_service.py::_calculate_next_due_date()`

**Example**:
```
User changes installment_count: 3 → 5
Paid installments: 1
Balance: ₹40,000
System creates: 2 new installments
New amount per installment: ₹40,000 / 4 = ₹10,000
```

---

#### 4. Supporting Features
- ✅ Staff dropdown populated from `/api/staff/active` endpoint
- ✅ Modal popup widths reduced for better UX
- ✅ Help text added to guide users on replanning
- ✅ Cache invalidation after updates
- ✅ Audit trail (created_by, updated_by, timestamps)

**Files**:
- `app/api/routes/staff.py` (NEW)
- `app/__init__.py` (blueprint registration)
- `app/templates/engine/business/package_sessions_table.html`

---

## ✅ NEWLY COMPLETED IMPLEMENTATION

### 1. Discontinued Status Handler (COMPLETED 2025-11-12)

**Status**: ✅ Implemented and ready for testing
**Complexity**: Medium
**Time Taken**: ~4 hours

**Implementation Summary**:
The discontinued status handler is now fully functional with automatic refund calculation and workflow management:

**✅ Completed Components**:
1. **Database Schema** - Added discontinuation tracking fields (`migrations/add_discontinuation_tracking_to_package_plans.sql`):
   - `discontinued_at`, `discontinued_by`, `discontinuation_reason`
   - `refund_amount`, `refund_status` (none/pending/approved/processed/failed)
   - Executed successfully on skinspire_dev database

2. **Model Updated** (`app/models/transaction.py:1862-1867`):
   - Added discontinuation fields to PackagePaymentPlan model
   - Added `discontinued_by_user` relationship

3. **Configuration Updated** (`app/config/modules/package_payment_plan_config.py`):
   - Added 5 discontinuation field definitions (lines 430-491)
   - Added 'discontinuation' section with conditional display
   - Added 'discontinuation_reason' to edit_fields list
   - Integrated into Audit & History tab

4. **Service Implementation** (`app/services/package_payment_service.py`):
   - New method: `_handle_discontinuation()` (lines 1701-1841) - Complete discontinuation workflow
   - Updated: `update_package_payment_plan()` (lines 1465-1502) - Status change detection
   - Automatic refund calculation based on unused sessions
   - Smart refund status: auto-approve < ₹10K, require approval ≥ ₹10K
   - Cancels all scheduled sessions and pending installments

**Business Logic Implemented**:
When user changes status to "Discontinued", the system:

1. **Validate Discontinuation**
   - Check if status is changing TO 'discontinued'
   - Verify plan is in 'active' or 'suspended' status (cannot discontinue 'completed' or 'cancelled' plans)
   - Require discontinuation reason from user

2. **Calculate Refund Amount**
   ```python
   remaining_sessions = total_sessions - completed_sessions
   session_value = total_amount / total_sessions
   refund_amount = remaining_sessions * session_value

   # Cannot refund more than paid
   refund_amount = min(refund_amount, paid_amount)
   ```

3. **Cancel Scheduled Sessions**
   - Update all sessions with `session_status = 'scheduled'` to `session_status = 'cancelled'`
   - Add cancellation note: "Cancelled due to plan discontinuation"

4. **Cancel Pending Installments**
   - Update all installments with `status = 'pending'` to `status = 'cancelled'`
   - Add cancellation note: "Cancelled due to plan discontinuation"

5. **Update Plan Fields**
   - Set `status = 'discontinued'`
   - Set `discontinued_at = datetime.now()`
   - Set `discontinued_by = current_user_id`
   - Set `discontinuation_reason = user_provided_reason`
   - Set `refund_amount = calculated_amount`
   - Set `refund_status = 'pending'` (for approval workflow)

**Implementation Location**:
- `app/services/package_payment_service.py::update_package_payment_plan()` - Add status change detection
- `app/services/package_payment_service.py::_handle_discontinuation()` - NEW METHOD

**Database Schema Required**:
```sql
-- Add to package_payment_plans table
ALTER TABLE package_payment_plans
ADD COLUMN IF NOT EXISTS discontinued_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS discontinued_by VARCHAR(15) REFERENCES users(user_id),
ADD COLUMN IF NOT EXISTS discontinuation_reason TEXT,
ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS refund_status VARCHAR(20) DEFAULT 'none';
-- Values: 'none', 'pending', 'approved', 'processed', 'failed'
```

**UI Flow**:
```
1. User selects Status = "Discontinued" in edit form
2. User enters required field: "Discontinuation Reason" (text area)
3. User clicks "Save"
4. System shows confirmation modal:
   - "Are you sure you want to discontinue this plan?"
   - Shows calculated refund: ₹15,000 (3 unused sessions)
   - Shows sessions to cancel: 3
   - Shows installments to cancel: 2
   - [Confirm Discontinuation] [Cancel]
5. User confirms
6. System processes discontinuation
7. Success message: "Plan discontinued. Refund of ₹15,000 marked for processing."
```

---

### 2. Refund Transaction Creation (MEDIUM PRIORITY)

**Status**: Not implemented
**Complexity**: Medium
**Estimated Effort**: 3-4 hours

**Requirements**:
After plan is discontinued, create a refund transaction record.

**Integration Points**:
- Patient payments system
- GL posting system (if applicable)
- Approval workflow (if refund > threshold amount)

**Implementation**:
```python
def _create_refund_transaction(
    plan_id: str,
    patient_id: str,
    refund_amount: Decimal,
    reason: str,
    hospital_id: str,
    branch_id: str,
    user_id: str
) -> Dict:
    """
    Create refund transaction for discontinued plan

    Returns:
        {'success': bool, 'refund_id': str, 'approval_required': bool}
    """
    # Check if approval required (e.g., refund > ₹10,000)
    approval_required = refund_amount > Decimal('10000.00')

    refund = PatientRefund(
        refund_id=uuid.uuid4(),
        patient_id=patient_id,
        plan_id=plan_id,
        refund_amount=refund_amount,
        refund_reason=reason,
        refund_status='pending_approval' if approval_required else 'approved',
        refund_method='pending',  # Cash/Bank/Cheque - to be decided by accounts
        hospital_id=hospital_id,
        branch_id=branch_id,
        created_by=user_id,
        created_at=datetime.utcnow()
    )

    session.add(refund)
    session.commit()

    return {
        'success': True,
        'refund_id': str(refund.refund_id),
        'approval_required': approval_required
    }
```

**Table Required**:
```sql
CREATE TABLE patient_refunds (
    refund_id UUID PRIMARY KEY,
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    plan_id UUID REFERENCES package_payment_plans(plan_id),
    invoice_id UUID REFERENCES invoice_header(invoice_id),  -- If refund from invoice
    refund_amount NUMERIC(12,2) NOT NULL,
    refund_reason TEXT NOT NULL,
    refund_status VARCHAR(20) DEFAULT 'pending',  -- pending, pending_approval, approved, processed, failed
    refund_method VARCHAR(20),  -- cash, bank_transfer, cheque
    refund_date DATE,
    processed_by VARCHAR(15) REFERENCES users(user_id),
    processed_at TIMESTAMP WITH TIME ZONE,
    approval_notes TEXT,
    hospital_id UUID NOT NULL,
    branch_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE,
    updated_by VARCHAR(15)
);
```

---

### 3. Refund Approval Workflow (LOW PRIORITY)

**Status**: Not implemented
**Complexity**: Medium
**Estimated Effort**: 4-5 hours

**Requirements**:
Refunds above threshold (e.g., ₹10,000) require manager approval.

**UI Components Needed**:
1. **Refund Approval List Page**
   - Shows all pending refunds
   - Filters: date range, amount range, patient
   - Columns: Patient, Plan, Amount, Reason, Requested By, Date

2. **Refund Approval Detail/Action Page**
   - Show plan details
   - Show patient details
   - Show refund calculation breakdown
   - Actions: [Approve] [Reject] [Request More Info]

**Implementation**:
- Create `app/views/refund_views.py`
- Create `app/templates/refund/approval_list.html`
- Create `app/templates/refund/approval_detail.html`
- Add routes: `/refunds/pending`, `/refunds/approve/<refund_id>`, `/refunds/reject/<refund_id>`

---

### 4. Discontinuation Notifications (LOW PRIORITY)

**Status**: Not implemented
**Complexity**: Low
**Estimated Effort**: 2-3 hours

**Requirements**:
Send notifications when plan is discontinued:
1. Patient notification (SMS/Email)
2. Staff notification (in-app)
3. Accounts team notification (refund processing required)

**Implementation**:
```python
def _send_discontinuation_notifications(
    patient_id: str,
    plan_id: str,
    refund_amount: Decimal,
    reason: str
):
    """Send notifications after plan discontinuation"""

    # Patient notification
    send_sms(
        patient_id=patient_id,
        message=f"Your treatment plan has been discontinued. "
                f"Refund of ₹{refund_amount} will be processed. "
                f"Contact clinic for details."
    )

    # Staff notification
    notify_staff(
        notification_type='plan_discontinued',
        plan_id=plan_id,
        message=f"Plan {plan_id} discontinued. Refund: ₹{refund_amount}"
    )

    # Accounts notification
    notify_accounts(
        notification_type='refund_required',
        refund_amount=refund_amount,
        plan_id=plan_id
    )
```

---

### 5. Enhanced Edit Form Confirmations (LOW PRIORITY)

**Status**: Not implemented
**Complexity**: Low
**Estimated Effort**: 2-3 hours

**Requirements**:
Add JavaScript confirmation dialogs for critical changes:

1. **Session Count Reduction Confirmation**
   ```
   "You are reducing sessions from 5 to 3. This will delete 2 scheduled sessions. Continue?"
   ```

2. **Installment Count Reduction Confirmation**
   ```
   "You are reducing installments from 5 to 3. This will delete 2 pending installments and recalculate amounts. Continue?"
   ```

3. **Large Amount Change Confirmation**
   ```
   "You are changing the total amount by ₹5,000. This will recalculate installment amounts. Continue?"
   ```

**Implementation**:
- Add JavaScript to `app/templates/engine/universal_edit.html`
- Hook into form submit event
- Show confirmation modal before submission

---

## Implementation Priority

### Phase 1 (HIGH PRIORITY - Completed & In Progress)
1. ✅ ~~Edit form infrastructure~~
2. ✅ ~~Session replanning~~
3. ✅ ~~Installment replanning~~
4. ✅ ~~**Discontinued status handler**~~ ← ✅ COMPLETED 2025-11-12
5. ❌ **Refund transaction creation** ← IMPLEMENT NEXT (Optional - for complete refund workflow)

### Phase 2 (MEDIUM PRIORITY - Following Sprint)
6. ❌ Refund approval workflow
7. ❌ Enhanced edit form confirmations

### Phase 3 (LOW PRIORITY - Future Enhancement)
8. ❌ Discontinuation notifications
9. ❌ Refund payment processing integration
10. ❌ Analytics/reporting for discontinued plans

---

## Testing Checklist

### Completed Tests
- ✅ Edit form loads with correct data
- ✅ Virtual fields display properly
- ✅ Computed fields calculate correctly
- ✅ Status dropdown shows all 5 options
- ✅ Save operation works without errors
- ✅ Increase sessions adds new sessions
- ✅ Decrease sessions removes scheduled sessions
- ✅ Cannot reduce sessions below completed count
- ✅ Increase installments adds new installments
- ✅ Decrease installments removes pending installments
- ✅ Cannot reduce installments below paid count
- ✅ Installment amounts recalculated correctly
- ✅ Completed_sessions auto-updates on session completion

### Pending Tests (Ready for Testing)
- 🧪 **Discontinue plan with scheduled sessions** - Implementation complete, ready to test
- 🧪 **Discontinue plan with pending installments** - Implementation complete, ready to test
- 🧪 **Refund calculation accuracy** - Formula implemented: (remaining_sessions / total_sessions) * paid_amount
- 🧪 **Refund status auto-assignment** - < ₹10K auto-approved, ≥ ₹10K requires approval
- 🧪 **Cannot discontinue already completed plan** - Validation implemented
- 🧪 **Cannot discontinue already cancelled plan** - Validation implemented
- 🧪 **Discontinuation reason required** - Validation implemented
- 🧪 **Sessions cancellation** - All scheduled sessions marked 'cancelled'
- 🧪 **Installments cancellation** - All pending installments marked 'cancelled'
- ❌ Refund transaction creation - Not yet implemented (Phase 1, item 5)
- ❌ Approval workflow for large refunds - Not yet implemented (Phase 2)

---

## Known Issues / Technical Debt

1. **No validation for status transitions**
   - Currently allows any status → any status
   - Should enforce valid transitions (e.g., active → discontinued OK, completed → discontinued NOT OK)

2. **No audit log for replanning actions**
   - Replanning changes are logged but not in a user-friendly audit format
   - Consider creating `package_plan_changes` table for detailed audit

3. **Installment date calculation is approximate**
   - Monthly frequency uses +30 days instead of proper month calculation
   - Should handle month-end dates properly (e.g., Jan 31 → Feb 28)

4. **No reversal mechanism**
   - Once discontinued, cannot easily reverse
   - Consider adding "Reactivate" action for discontinued plans

---

## API Endpoints Status

### Existing Endpoints
- ✅ `GET /universal/package_payment_plans/list` - List all plans
- ✅ `GET /universal/package_payment_plans/detail/<id>` - View plan details
- ✅ `GET /universal/package_payment_plans/edit/<id>` - Edit form (GET)
- ✅ `POST /universal/package_payment_plans/edit/<id>` - Save changes (POST)
- ✅ `POST /api/package/session/<session_id>/complete` - Complete session
- ✅ `PATCH /api/package/session/<session_id>/date` - Update session date
- ✅ `GET /api/staff/active` - Get active staff for dropdown

### Pending Endpoints
- ❌ `POST /api/package/plan/<id>/discontinue` - Discontinue with refund
- ❌ `GET /api/package/refunds/pending` - List pending refunds
- ❌ `POST /api/package/refund/<id>/approve` - Approve refund
- ❌ `POST /api/package/refund/<id>/reject` - Reject refund
- ❌ `POST /api/package/refund/<id>/process` - Process refund payment

---

## Database Migrations Status

### Completed Migrations
- ✅ `add_discontinued_status_to_package_plans.sql` - Status constraint (2025-11-12)
- ✅ `sync_completed_sessions_count.sql` - Fix completed_sessions counts (2025-11-12)
- ✅ `add_discontinuation_tracking_to_package_plans.sql` - Discontinuation tracking fields (2025-11-12)
  - Added: discontinued_at, discontinued_by, discontinuation_reason, refund_amount, refund_status
  - Added: refund_status CHECK constraint (none/pending/approved/processed/failed)

### Pending Migrations
- ❌ Create patient_refunds table (Phase 1, item 5 - Optional for complete workflow)
- ❌ Create package_plan_changes audit table (Future enhancement - optional)
- ❌ Add indexes for refund queries (Performance optimization - optional)

---

## Documentation Status

- ✅ Business logic documented
- ✅ Replanning logic documented with examples
- ✅ Implementation status tracked (this document)
- ❌ User guide for staff/doctors
- ❌ API documentation for refund endpoints
- ❌ Troubleshooting guide

---

**Next Action**: Test discontinued status handler implementation (all validations and refund calculations)

**Optional Next Implementation**: Create patient_refunds table and refund transaction workflow (Phase 1, Item 5)

**Document Version**: 3.0
**Last Updated**: 2025-11-12 (Discontinued status handler completed)
**Maintained By**: Development Team
