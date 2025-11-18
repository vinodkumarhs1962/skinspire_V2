# Package Payment Plan - Database Structure Fix

## Date: 2025-11-12

## Problem Identified

User correctly identified that the current database structure cannot properly handle rescheduling of installments and sessions.

### Use Cases:
1. **Installment Rescheduling**: Patient requests to extend installment due date from Nov 11 → Nov 18
2. **Session Rescheduling**: Patient or clinic reschedules session from Nov 11 → Nov 14

### Root Cause:
- **Sessions table** only had ONE date field (`session_date`) - ambiguous usage
- No field to store actual completion date separately from scheduled date

## Solution: Add ONE Field

### Installments Table ✅ Already Correct
```sql
CREATE TABLE installment_payments (
    installment_id UUID PRIMARY KEY,
    installment_number INTEGER,
    due_date DATE,              -- ✅ Scheduled due date (can be rescheduled)
    amount NUMERIC(12,2),
    paid_date DATE,             -- ✅ Actual payment date
    paid_amount NUMERIC(12,2),
    status VARCHAR(20)          -- pending, paid, overdue
);
```

**No changes needed!** The structure already supports:
- `due_date` = scheduled date (editable when patient requests extension)
- `paid_date` = actual payment date

### Sessions Table - Add One Field

**BEFORE:**
```sql
CREATE TABLE package_sessions (
    session_id UUID PRIMARY KEY,
    session_number INTEGER,
    session_date DATE,           -- ❌ Ambiguous: scheduled or actual?
    session_status VARCHAR(20),
    performed_by VARCHAR(15),
    service_notes TEXT
);
```

**AFTER:**
```sql
CREATE TABLE package_sessions (
    session_id UUID PRIMARY KEY,
    session_number INTEGER,
    session_date DATE,           -- ✅ Scheduled date (can be rescheduled)
    actual_completion_date DATE, -- ✅ NEW: When session was actually completed
    session_status VARCHAR(20),
    performed_by VARCHAR(15),
    service_notes TEXT
);
```

## Implementation

### 1. Migration Script
**File:** `migrations/add_actual_completion_date_to_sessions.sql`
- Adds `actual_completion_date` field
- Migrates existing completed sessions
- Adds comments for clarity

### 2. Model Update
**File:** `app/models/transaction.py`
- Added `actual_completion_date = Column(Date)` to PackageSession class
- Added comments to clarify field usage

### 3. Service Update
**File:** `app/services/package_payment_service.py`
- Updated `get_plan_sessions()` to include `actual_completion_date` in response

### 4. Template Updates Needed
**Files:**
- `app/templates/engine/business/package_sessions_table.html`
  - Show `session_date` in "Scheduled Date" column
  - Show `actual_completion_date` in "Actual Date" column
  - Capture `actual_completion_date` in Complete Session modal

## Field Usage Guide

### Installments
| Field | Purpose | When Set | Can Be Modified |
|-------|---------|----------|-----------------|
| `due_date` | Scheduled due date | At plan creation | ✅ Yes (reschedule) |
| `paid_date` | Actual payment date | When paid | ❌ No |
| `paid_amount` | Amount paid | When paid | ❌ No |

**Workflow:**
1. Plan created → `due_date` = Nov 11, 2025
2. Patient requests extension → Edit `due_date` to Nov 18, 2025
3. Patient pays → `paid_date` = Nov 18, 2025, `paid_amount` = ₹10,000

### Sessions
| Field | Purpose | When Set | Can Be Modified |
|-------|---------|----------|-----------------|
| `session_date` | Scheduled session date | At plan creation | ✅ Yes (reschedule) |
| `actual_completion_date` | Actual completion date | When completed | ❌ No |
| `session_status` | Status | Always | System updates |
| `performed_by` | Staff who performed | When completed | ❌ No |

**Workflow:**
1. Plan created → `session_date` = Nov 11, 2025, `status` = 'scheduled'
2. Patient reschedules → Edit `session_date` to Nov 14, 2025
3. Session completed → `actual_completion_date` = Nov 14, 2025, `status` = 'completed'

## Benefits

1. ✅ **Operational Flexibility**: Can reschedule without losing data
2. ✅ **Clear Follow-up**: Know when next session is actually scheduled
3. ✅ **Due Date Tracking**: Installments don't show overdue until revised date
4. ✅ **Completion Tracking**: Know when sessions were actually completed vs scheduled
5. ✅ **Minimal Change**: Only ONE new field added

## Next Steps

1. Run migration script to add `actual_completion_date` field
2. Update session Complete modal to save to `actual_completion_date`
3. Update session table template to show both dates correctly
4. Fix CSS to match invoice line items exactly
5. Test rescheduling workflows

## SQL to Run

```sql
-- Add the new field
ALTER TABLE package_sessions
ADD COLUMN actual_completion_date DATE;

-- Add comments
COMMENT ON COLUMN package_sessions.session_date IS 'Scheduled session date (can be rescheduled)';
COMMENT ON COLUMN package_sessions.actual_completion_date IS 'Actual date when session was completed';

-- Migrate existing data
UPDATE package_sessions
SET actual_completion_date = session_date
WHERE session_status = 'completed' AND actual_completion_date IS NULL;
```
