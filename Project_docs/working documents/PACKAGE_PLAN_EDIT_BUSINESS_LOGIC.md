# Package Payment Plan Edit - Business Logic Implementation Guide

**Date**: 2025-11-12
**Module**: Package Payment Plans
**Service**: `app/services/package_payment_service.py`

## Overview

This document outlines the business logic that needs to be implemented when editing package payment plans. The edit functionality allows changing:
1. Total amount
2. Number of sessions (triggers replanning)
3. Number of installments (triggers replanning)
4. Status (discontinued triggers refund)

---

## 1. Edit Form Fields

### Read-Only Fields (Display Only)
- **Package ID**: Shows package name via entity_search_config
- **Patient ID**: Shows patient name via entity_search_config
- **Paid Amount**: Auto-calculated from installment payments
- **Balance Amount**: Computed as `Total Amount - Paid Amount`

### Editable Fields
- **Total Amount**: Can be adjusted if package price changes
- **Total Sessions**: Number of service sessions (triggers replanning)
- **Installment Count**: Number of payment installments (triggers replanning)
- **Installment Frequency**: Payment schedule (weekly, monthly, etc.)
- **First Installment Date**: Starting date for installment schedule
- **Status**: Active, Completed, Cancelled, Suspended, **Discontinued** (new)
- **Notes**: Additional information

---

## 2. Replanning Logic - Session Changes

### Scenario: User Changes `total_sessions` Field

**Trigger**: When `total_sessions` is changed from original value

### Business Rules

#### Case A: Increase Sessions (e.g., 5 → 8)
```python
# Example: Plan originally had 5 sessions, now changed to 8
original_sessions = 5
new_sessions = 8
completed_sessions = 2  # Already completed

# Action: Add 3 new sessions (8 - 5)
sessions_to_add = new_sessions - original_sessions

# Implementation:
for i in range(sessions_to_add):
    new_session_number = original_sessions + i + 1
    create_package_session(
        plan_id=plan_id,
        session_number=new_session_number,
        session_date=None,  # To be scheduled
        session_status='scheduled',
        hospital_id=hospital_id,
        branch_id=branch_id
    )
```

#### Case B: Decrease Sessions (e.g., 5 → 3)
```python
# Example: Plan had 5 sessions, now reduced to 3
original_sessions = 5
new_sessions = 3
completed_sessions = 2  # Already completed
remaining_sessions = original_sessions - completed_sessions  # 3

# Validation: Cannot reduce below completed sessions
if new_sessions < completed_sessions:
    raise ValueError(f"Cannot reduce to {new_sessions} sessions. Already completed {completed_sessions} sessions.")

# Action: Delete scheduled (not completed) sessions beyond new count
# Keep sessions 1-3, delete sessions 4-5 (if they are not completed)
sessions_to_delete = get_sessions(
    plan_id=plan_id,
    session_number__gt=new_sessions,
    session_status='scheduled'  # Only delete scheduled sessions
)

for session in sessions_to_delete:
    soft_delete_session(session.session_id)
```

---

## 3. Replanning Logic - Installment Changes

### Scenario: User Changes `installment_count` Field

**Trigger**: When `installment_count` is changed from original value

### Business Rules

#### Case A: Increase Installments (e.g., 3 → 5)
```python
# Example: Plan had 3 installments, now increased to 5
original_installments = 3
new_installments = 5
paid_installments = 1  # Already paid

# Recalculate installment amounts
balance_amount = total_amount - paid_amount
remaining_installments = new_installments - paid_installments  # 4

# New installment amount (distribute balance equally)
new_installment_amount = balance_amount / remaining_installments

# Implementation:
# 1. Update existing unpaid installments
unpaid_installments = get_installments(
    plan_id=plan_id,
    status__in=['pending', 'partial']
)

for installment in unpaid_installments:
    installment.amount = new_installment_amount
    installment.save()

# 2. Create new installments (2 additional)
last_installment = get_last_installment(plan_id)
for i in range(new_installments - original_installments):
    new_due_date = calculate_next_due_date(
        last_due_date=last_installment.due_date,
        frequency=installment_frequency
    )

    create_installment_payment(
        plan_id=plan_id,
        installment_number=original_installments + i + 1,
        due_date=new_due_date,
        amount=new_installment_amount,
        status='pending',
        hospital_id=hospital_id
    )
```

#### Case B: Decrease Installments (e.g., 5 → 3)
```python
# Example: Plan had 5 installments, reduced to 3
original_installments = 5
new_installments = 3
paid_installments = 1  # Already paid
partially_paid_installments = 1  # One has partial payment

# Validation: Cannot reduce below paid/partial count
paid_or_partial_count = paid_installments + partially_paid_installments
if new_installments < paid_or_partial_count:
    raise ValueError(f"Cannot reduce to {new_installments} installments. {paid_or_partial_count} are already paid/partially paid.")

# Action:
# 1. Delete pending installments beyond new count
installments_to_delete = get_installments(
    plan_id=plan_id,
    installment_number__gt=new_installments,
    status='pending'
)

for installment in installments_to_delete:
    soft_delete_installment(installment.installment_id)

# 2. Recalculate remaining installment amounts
balance_amount = total_amount - paid_amount
remaining_installments = new_installments - paid_installments  # 2

if remaining_installments > 0:
    new_installment_amount = balance_amount / remaining_installments

    unpaid_installments = get_installments(
        plan_id=plan_id,
        status__in=['pending', 'partial']
    )

    for installment in unpaid_installments:
        installment.amount = new_installment_amount
        installment.save()
```

---

## 4. Discontinued Status - Refund Process

### Scenario: User Changes `status` to 'discontinued'

**Trigger**: When status field is changed to 'discontinued'

### Business Rules

```python
def handle_discontinued_status(plan_id, hospital_id, branch_id, user_id, reason):
    """
    Handles the refund process when a package plan is discontinued

    Business Logic:
    1. Calculate refund amount based on unused services
    2. Cancel all pending/scheduled sessions
    3. Cancel all pending installments
    4. Create refund transaction
    5. Update plan status and timestamp
    """

    plan = get_plan_by_id(plan_id, hospital_id)

    # Step 1: Calculate refund amount
    # Refund = (Remaining Sessions / Total Sessions) * Total Paid Amount
    remaining_sessions = plan.total_sessions - plan.completed_sessions
    session_value = plan.total_amount / plan.total_sessions
    refund_amount = remaining_sessions * session_value

    # Cannot refund more than already paid
    refund_amount = min(refund_amount, plan.paid_amount)

    # Step 2: Cancel all scheduled sessions
    scheduled_sessions = get_sessions(
        plan_id=plan_id,
        session_status='scheduled'
    )

    for session in scheduled_sessions:
        session.session_status = 'cancelled'
        session.service_notes = f"Cancelled due to plan discontinuation by {user_id}"
        session.save()

    # Step 3: Cancel all pending installments
    pending_installments = get_installments(
        plan_id=plan_id,
        status='pending'
    )

    for installment in pending_installments:
        installment.status = 'cancelled'
        installment.notes = f"Cancelled due to plan discontinuation"
        installment.save()

    # Step 4: Create refund transaction
    # This should integrate with your payment system
    refund_transaction = create_patient_refund(
        patient_id=plan.patient_id,
        plan_id=plan_id,
        refund_amount=refund_amount,
        refund_reason=f"Package plan discontinued - {remaining_sessions} unused sessions",
        refund_method='pending',  # To be processed by accounts
        hospital_id=hospital_id,
        branch_id=branch_id,
        created_by=user_id
    )

    # Step 5: Update plan
    plan.status = 'discontinued'
    plan.discontinued_at = datetime.now(timezone.utc)
    plan.discontinued_by = user_id
    plan.discontinuation_reason = reason
    plan.refund_amount = refund_amount
    plan.refund_status = 'pending'
    plan.save()

    # Step 6: Send notifications (optional)
    send_discontinuation_notification(
        patient_id=plan.patient_id,
        plan_id=plan_id,
        refund_amount=refund_amount
    )

    return {
        'success': True,
        'refund_amount': refund_amount,
        'cancelled_sessions': len(scheduled_sessions),
        'cancelled_installments': len(pending_installments),
        'refund_transaction_id': refund_transaction.transaction_id
    }
```

---

## 5. Implementation Checklist

### Backend Service (`package_payment_service.py`)

- [ ] **update_package_plan()** method enhancement
  - [ ] Detect changes in `total_sessions`
  - [ ] Detect changes in `installment_count`
  - [ ] Detect status change to 'discontinued'
  - [ ] Call appropriate replanning functions

- [ ] **replan_sessions()** method
  - [ ] Handle session increase (add new sessions)
  - [ ] Handle session decrease (delete scheduled sessions)
  - [ ] Validation: cannot reduce below completed count

- [ ] **replan_installments()** method
  - [ ] Handle installment increase (add new installments)
  - [ ] Handle installment decrease (delete pending installments)
  - [ ] Recalculate installment amounts for unpaid installments
  - [ ] Validation: cannot reduce below paid/partial count

- [ ] **process_discontinuation()** method
  - [ ] Calculate refund amount
  - [ ] Cancel scheduled sessions
  - [ ] Cancel pending installments
  - [ ] Create refund transaction
  - [ ] Update plan status and fields
  - [ ] Send notifications

### Database Fields to Add

```sql
-- Add to package_payment_plans table
ALTER TABLE package_payment_plans
ADD COLUMN IF NOT EXISTS discontinued_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS discontinued_by VARCHAR(15) REFERENCES users(user_id),
ADD COLUMN IF NOT EXISTS discontinuation_reason TEXT,
ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS refund_status VARCHAR(20) DEFAULT 'none'; -- none, pending, processed, failed
```

### Validation Rules

1. **Session Changes**:
   - Cannot reduce `total_sessions` below `completed_sessions`
   - Cannot increase beyond package maximum (if defined)

2. **Installment Changes**:
   - Cannot reduce `installment_count` below paid/partially-paid count
   - Must recalculate amounts to ensure sum equals balance

3. **Discontinued Status**:
   - Requires discontinuation reason
   - Can only discontinue if status is 'active' or 'suspended'
   - Cannot discontinue if plan is 'completed' or 'cancelled'

---

## 6. User Experience Flow

### Editing Package Plan

```
1. User clicks "Edit Package Plan" button
2. Edit form opens with:
   - Package name (read-only, shows name not ID)
   - Patient name (read-only, shows name not ID)
   - Total Amount (editable)
   - Paid Amount (read-only, computed)
   - Balance Amount (read-only, computed)
   - Total Sessions (editable)
   - Installment Count (editable)
   - Status (dropdown with options)
   - Notes (editable)

3. User makes changes and clicks "Save"

4. Backend detects changes and:
   a. If sessions changed → Triggers replanning
   b. If installments changed → Triggers replanning
   c. If status = discontinued → Triggers refund process

5. Success message shown with details:
   "Package plan updated successfully.
    - Sessions replanned: 3 new sessions added
    - Installments recalculated: 2 installments updated
    - Refund initiated: ₹15,000 (pending approval)"
```

### Discontinuing a Plan

```
1. User changes Status to "Discontinued" and clicks Save

2. First Modal: "Discontinue Package Plan?"
   - Reason for discontinuation: [text area - required]
   - Estimated refund: ₹15,000 (calculated automatically)
   - Sessions to cancel: 3
   - Installments to cancel: 2
   - [Continue] [Cancel]

3. User clicks "Continue"

4. Second Modal: "Process Refund?"
   - Refund amount: ₹15,000
   - Refund method: [dropdown - Cash/Bank Transfer/Cheque]
   - Do you want to process refund now?
     ○ Yes - Process refund immediately
     ○ No - Mark for manual processing later
   - [Confirm] [Cancel]

5. User selects option and confirms

6. Backend processes:
   - Cancels sessions/installments
   - Updates plan status to discontinued
   - If "Yes": Creates refund transaction with status 'pending_approval'
   - If "No": Updates plan with refund_status = 'marked_for_processing'

7. Success message:
   If refund processed:
   "Package plan discontinued.
    Refund of ₹15,000 initiated and sent for approval."

   If marked for later:
   "Package plan discontinued.
    Refund of ₹15,000 marked for manual processing."
```

---

## 7. Error Handling

### Common Errors

```python
# Error 1: Reducing sessions below completed
{
    "error": "Cannot reduce total sessions to 2. Already completed 3 sessions.",
    "error_code": "INVALID_SESSION_REDUCTION"
}

# Error 2: Reducing installments below paid
{
    "error": "Cannot reduce installments to 2. Already paid 3 installments.",
    "error_code": "INVALID_INSTALLMENT_REDUCTION"
}

# Error 3: Invalid status transition
{
    "error": "Cannot discontinue a completed plan. Use cancel instead.",
    "error_code": "INVALID_STATUS_TRANSITION"
}

# Error 4: Missing discontinuation reason
{
    "error": "Discontinuation reason is required when changing status to discontinued.",
    "error_code": "MISSING_DISCONTINUATION_REASON"
}
```

---

## 8. Testing Scenarios

### Test Case 1: Increase Sessions
- **Given**: Plan with 5 sessions, 2 completed
- **When**: Change total_sessions to 8
- **Then**: 3 new scheduled sessions created

### Test Case 2: Decrease Sessions (Valid)
- **Given**: Plan with 5 sessions, 2 completed
- **When**: Change total_sessions to 3
- **Then**: 2 scheduled sessions deleted, 3 sessions remain

### Test Case 3: Decrease Sessions (Invalid)
- **Given**: Plan with 5 sessions, 3 completed
- **When**: Try to change total_sessions to 2
- **Then**: Error - cannot reduce below completed

### Test Case 4: Increase Installments
- **Given**: Plan with 3 installments, 1 paid
- **When**: Change installment_count to 5
- **Then**: 2 new installments created, amounts recalculated

### Test Case 5: Decrease Installments (Valid)
- **Given**: Plan with 5 installments, 2 paid
- **When**: Change installment_count to 3
- **Then**: 2 pending installments deleted, remaining amounts recalculated

### Test Case 6: Discontinue Plan
- **Given**: Active plan, 5 sessions (2 completed), ₹50,000 paid
- **When**: Change status to discontinued
- **Then**:
  - 3 sessions cancelled
  - Pending installments cancelled
  - Refund of ₹30,000 initiated (60% unused)

---

## 9. Integration Points

### Services to Update
1. **PackagePaymentService** - Main business logic
2. **PaymentService** - Refund transaction creation
3. **NotificationService** - Send discontinuation notifications
4. **AuditService** - Log all replanning actions

### API Endpoints Needed
```python
# Edit package plan (existing, needs enhancement)
PUT /api/package/plan/{plan_id}

# Manual refund approval (new)
POST /api/package/plan/{plan_id}/refund/approve

# Replanning preview (optional, for validation)
POST /api/package/plan/{plan_id}/replan/preview
```

---

## 10. Next Steps

1. **Add database fields** for discontinuation tracking (run migration)
2. **Implement replanning logic** in `PackagePaymentService`
3. **Implement refund process** (integrate with payment system)
4. **Add validation** for session/installment changes
5. **Create unit tests** for all scenarios
6. **Update UI** to show confirmation modals for critical changes
7. **Add audit logging** for all replanning actions

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Author**: Claude Code Assistant
