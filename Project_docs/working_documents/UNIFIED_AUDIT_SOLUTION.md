# Unified Audit Trail Solution

## Problem Statement

Currently we have **redundant and conflicting** mechanisms:
- TimestampMixin handles `created_at` and `updated_at`
- Database triggers also handle `updated_at` (redundant!)
- Database triggers handle `created_by` and `updated_by` (but we never set session variable)
- Application code tries to set `created_by` and `updated_by` (but triggers overwrite it)

**Result:** Messy, inefficient, and audit fields are not populated correctly.

---

## Proposed Solution: Enhanced TimestampMixin with SQLAlchemy Event Listeners

### Why This Approach?

✅ **Single mechanism** for all four fields
✅ **Centralized** in one place (base.py)
✅ **Automatic** - no manual intervention needed
✅ **Works for all models** using TimestampMixin
✅ **Access to Flask context** (current_user)
✅ **No database triggers needed**

---

## Implementation

### Step 1: Enhance TimestampMixin in base.py

```python
# app/models/base.py

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, event
from sqlalchemy.ext.declarative import declarative_base

class TimestampMixin:
    """
    Mixin for automatic timestamp and user tracking

    Automatically manages:
    - created_at: Set on INSERT
    - updated_at: Set on INSERT and UPDATE
    - created_by: Set on INSERT (from current_user)
    - updated_by: Set on INSERT and UPDATE (from current_user)
    """
    created_at = Column(DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc),
                       nullable=False)
    updated_at = Column(DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       nullable=False)
    created_by = Column(String(50))
    updated_by = Column(String(50))


def get_current_user_id():
    """
    Get current user ID from Flask-Login context
    Falls back to 'system' if no user context available
    """
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            # Assuming your User model has user_id or id
            return str(getattr(current_user, 'user_id', None) or
                      getattr(current_user, 'id', 'system'))
        return 'system'
    except:
        # Outside Flask context (migrations, scripts, etc.)
        return 'system'


# SQLAlchemy Event Listeners
@event.listens_for(TimestampMixin, 'before_insert', propagate=True)
def timestamp_before_insert(mapper, connection, target):
    """Set created_by and updated_by on INSERT"""
    user_id = get_current_user_id()
    target.created_by = user_id
    target.updated_by = user_id


@event.listens_for(TimestampMixin, 'before_update', propagate=True)
def timestamp_before_update(mapper, connection, target):
    """Set updated_by on UPDATE"""
    user_id = get_current_user_id()
    target.updated_by = user_id
```

---

### Step 2: Remove Database Triggers

**SQL to run:**

```sql
-- Drop track_user_changes trigger from all tables
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT DISTINCT event_object_table
        FROM information_schema.triggers
        WHERE trigger_name = 'track_user_changes'
    ) LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS track_user_changes ON %I', r.event_object_table);
    END LOOP;
END $$;

-- Drop update_timestamp trigger from all tables
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT DISTINCT event_object_table
        FROM information_schema.triggers
        WHERE trigger_name = 'update_timestamp'
    ) LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS update_timestamp ON %I', r.event_object_table);
    END LOOP;
END $$;

-- Drop the trigger functions
DROP FUNCTION IF EXISTS track_user_changes();
DROP FUNCTION IF EXISTS update_timestamp();
```

---

### Step 3: Remove Application-Level Audit Field Setting

Remove all manual setting of audit fields from service files:

**Files to update:**
- `app/services/subledger_service.py`
- `app/services/billing_service.py`
- `app/services/supplier_invoice_service.py`
- `app/services/supplier_payment_service.py`
- `app/services/package_payment_service.py`
- Any other service files

**What to remove:**
```python
# REMOVE THIS CODE:
if current_user_id:
    ar_entry.created_by = current_user_id
    ar_entry.updated_by = current_user_id
```

The event listeners will handle this automatically!

---

## How It Works

### On INSERT:
1. TimestampMixin's `default` sets `created_at`
2. TimestampMixin's `default` sets `updated_at`
3. `before_insert` event listener sets `created_by` (from Flask-Login)
4. `before_insert` event listener sets `updated_by` (from Flask-Login)

### On UPDATE:
1. TimestampMixin's `onupdate` sets `updated_at`
2. `before_update` event listener sets `updated_by` (from Flask-Login)

### User Context:
- Web requests: Uses Flask-Login's `current_user`
- Background jobs/migrations: Defaults to `'system'`

---

## Benefits

1. **Single Source of Truth**: All audit logic in TimestampMixin
2. **Automatic**: No manual intervention needed
3. **Consistent**: Same behavior for all models
4. **Maintainable**: Changes in one place affect all models
5. **Testable**: Easy to test and mock
6. **Clean**: No redundant code in services

---

## Migration Plan

1. ✅ Add event listeners to TimestampMixin
2. ✅ Test with one model (ARSubledger)
3. ✅ Remove database triggers
4. ✅ Remove manual audit code from services
5. ✅ Backfill existing records with 'system' for empty audit fields
6. ✅ Verify all tables work correctly

---

## Edge Cases

### Scripts and Migrations
- No Flask context available
- Event listener defaults to `'system'`
- This is correct behavior!

### Background Jobs
- May or may not have Flask context
- Can set a custom user via thread-local variable if needed
- Defaults to `'system'` if no context

### Direct SQL
- Event listeners don't fire (SQLAlchemy only)
- Should avoid direct SQL for data manipulation
- Use ORM for all CRUD operations

---

## Testing

```python
# Test INSERT
with get_db_session() as session:
    # Assuming Flask-Login context with user_id='7777777777'
    ar_entry = ARSubledger(...)
    session.add(ar_entry)
    session.commit()

    # Check audit fields
    assert ar_entry.created_at is not None
    assert ar_entry.updated_at is not None
    assert ar_entry.created_by == '7777777777'
    assert ar_entry.updated_by == '7777777777'

# Test UPDATE
with get_db_session() as session:
    ar_entry = session.query(ARSubledger).first()
    ar_entry.debit_amount = Decimal('100')
    session.commit()

    # Check updated_by changed
    assert ar_entry.updated_by == '7777777777'  # Current user
```

---

## Recommendation

**Implement this solution** - it's clean, maintainable, and follows SQLAlchemy best practices.

All four audit fields (created_at, updated_at, created_by, updated_by) will be managed by ONE mechanism: **TimestampMixin with event listeners**.
