# How TimestampMixin and Triggers Work Together

## Your Question

> "If I understand correctly, TimestampMixin will provide right data and trigger will apply it. Am I right?"

## Answer: Not Exactly - They Work in Parallel, Not in Sequence

Let me explain the actual flow:

---

## Current State (What Happens Now)

### TimestampMixin WITHOUT Event Listeners (Current Code)

```python
class TimestampMixin:
    created_at = Column(DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc),
                       nullable=False)
    updated_at = Column(DateTime(timezone=True),
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc),
                       nullable=False)
    created_by = Column(String(50))  # ← Just a column definition, NO automatic value
    updated_by = Column(String(50))  # ← Just a column definition, NO automatic value
```

**What TimestampMixin does NOW:**
- ✅ `created_at`: Automatically set by Column `default` parameter
- ✅ `updated_at`: Automatically set by Column `onupdate` parameter
- ❌ `created_by`: NOTHING - just defines the column
- ❌ `updated_by`: NOTHING - just defines the column

**What Triggers do NOW:**
- ✅ `created_at`: NOT touched (already set by TimestampMixin)
- ✅ `updated_at`: OVERWRITES TimestampMixin value (redundant!)
- ✅ `created_by`: Sets value (from session variable or 'system')
- ✅ `updated_by`: Sets value (from session variable or 'system')

---

## The Flow: INSERT Operation

### Step-by-Step for: `ar_entry = ARSubledger(...); session.add(ar_entry); session.commit()`

```
1. Python creates ARSubledger object
   ↓
   TimestampMixin Column defaults kick in:
   - created_at = datetime.now()  ✅ SET
   - updated_at = datetime.now()  ✅ SET
   - created_by = None            ❌ NOT SET (no default)
   - updated_by = None            ❌ NOT SET (no default)

2. session.add(ar_entry)
   ↓
   Object added to session

3. session.flush() or session.commit()
   ↓
   SQLAlchemy generates INSERT statement:
   INSERT INTO ar_subledger (created_at, updated_at, created_by, updated_by, ...)
   VALUES ('2025-11-16 01:00:00', '2025-11-16 01:00:00', NULL, NULL, ...)
   ↓

4. PostgreSQL receives INSERT
   ↓
   BEFORE INSERT trigger fires: track_user_changes()
   ↓
   Trigger modifies the INSERT:
   - created_by = NULL → changed to 'system' (or session_user)
   - updated_by = NULL → changed to 'system' (or session_user)
   ↓

5. Row inserted with:
   - created_at = '2025-11-16 01:00:00'  (from TimestampMixin)
   - updated_at = '2025-11-16 01:00:00'  (from TimestampMixin)
   - created_by = 'system'               (from Trigger)
   - updated_by = 'system'               (from Trigger)
```

**Key Point:** TimestampMixin does NOT set created_by/updated_by at all. Trigger sets them.

---

## The Flow: UPDATE Operation

### Step-by-Step for: `ar_entry.debit_amount = 100; session.commit()`

```
1. Modify object attribute
   ↓
   SQLAlchemy marks object as dirty

2. session.flush() or session.commit()
   ↓
   TimestampMixin onupdate kicks in:
   - updated_at = datetime.now()  ✅ SET
   ↓
   SQLAlchemy generates UPDATE statement:
   UPDATE ar_subledger
   SET debit_amount = 100, updated_at = '2025-11-16 02:00:00'
   WHERE entry_id = '...'
   ↓

3. PostgreSQL receives UPDATE
   ↓
   BEFORE UPDATE trigger fires: track_user_changes()
   ↓
   Trigger modifies the UPDATE:
   - updated_by = (old value) → changed to 'system' (or session_user)
   ↓

4. BEFORE UPDATE trigger fires: update_timestamp()
   ↓
   Trigger OVERWRITES updated_at:
   - updated_at = CURRENT_TIMESTAMP  (redundant with TimestampMixin!)
   ↓

5. Row updated with:
   - debit_amount = 100
   - updated_at = '2025-11-16 02:00:00'  (from trigger, overwriting TimestampMixin)
   - updated_by = 'system'               (from trigger)
```

**Key Point:** Trigger OVERWRITES updated_at (redundant), and sets updated_by.

---

## What We Need: Event Listeners to Bridge the Gap

### Proposed Enhancement

```python
class TimestampMixin:
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
    """Get user from Flask-Login context"""
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return str(current_user.user_id)
        return 'system'
    except:
        return 'system'


# NEW: Event listeners
@event.listens_for(TimestampMixin, 'before_insert', propagate=True)
def set_audit_on_insert(mapper, connection, target):
    """
    Sets created_by and updated_by BEFORE sending to database
    ALSO sets session variable for trigger to use
    """
    user_id = get_current_user_id()

    # Set on Python object
    target.created_by = user_id
    target.updated_by = user_id

    # ALSO set session variable for trigger (safety net)
    try:
        connection.execute(text(f"SET LOCAL app.current_user = '{user_id}'"))
    except:
        pass


@event.listens_for(TimestampMixin, 'before_update', propagate=True)
def set_audit_on_update(mapper, connection, target):
    """
    Sets updated_by BEFORE sending to database
    ALSO sets session variable for trigger to use
    """
    user_id = get_current_user_id()

    # Set on Python object
    target.updated_by = user_id

    # ALSO set session variable for trigger (safety net)
    try:
        connection.execute(text(f"SET LOCAL app.current_user = '{user_id}'"))
    except:
        pass
```

---

## New Flow with Event Listeners: INSERT

```
1. Python creates ARSubledger object
   ↓
   TimestampMixin Column defaults:
   - created_at = datetime.now()  ✅ SET
   - updated_at = datetime.now()  ✅ SET
   - created_by = None            (not set yet)
   - updated_by = None            (not set yet)

2. session.add(ar_entry)
   ↓
   Object added to session

3. session.flush() or session.commit()
   ↓
   EVENT LISTENER fires: before_insert
   ↓
   Event listener:
   - target.created_by = '7777777777'  ✅ SET (from Flask-Login)
   - target.updated_by = '7777777777'  ✅ SET (from Flask-Login)
   - SET LOCAL app.current_user = '7777777777'  ✅ SET (for trigger)
   ↓
   SQLAlchemy generates INSERT:
   INSERT INTO ar_subledger (created_at, updated_at, created_by, updated_by, ...)
   VALUES ('2025-11-16 01:00:00', '2025-11-16 01:00:00', '7777777777', '7777777777', ...)
   ↓

4. PostgreSQL receives INSERT
   ↓
   BEFORE INSERT trigger fires: track_user_changes()
   ↓
   Trigger sees:
   - created_by = '7777777777' (already set!)
   - updated_by = '7777777777' (already set!)
   - Session variable app.current_user = '7777777777' (matches!)
   ↓
   Enhanced trigger logic:
   IF created_by IS NULL THEN
       created_by = current_setting('app.current_user')  -- Would set '7777777777'
   ELSE
       -- Already set, KEEP IT ✅
   END IF
   ↓

5. Row inserted with:
   - created_at = '2025-11-16 01:00:00'  (TimestampMixin)
   - updated_at = '2025-11-16 01:00:00'  (TimestampMixin)
   - created_by = '7777777777'           (Event Listener, validated by Trigger)
   - updated_by = '7777777777'           (Event Listener, validated by Trigger)
```

---

## Correct Understanding

### It's NOT:
❌ "TimestampMixin provides data → Trigger applies it"
❌ "TimestampMixin → Trigger" (sequential)

### It IS:
✅ **TimestampMixin Column defaults** set `created_at` and `updated_at`
✅ **Event Listeners** set `created_by` and `updated_by` (AND session variable)
✅ **Triggers** act as SAFETY NET and VALIDATOR

### Division of Labor:

| Field | TimestampMixin | Event Listener | Trigger | Final Source |
|-------|---------------|----------------|---------|--------------|
| created_at | ✅ Sets value | - | - | **TimestampMixin** |
| updated_at | ✅ Sets value | - | ⚠️ Overwrites (redundant) | **Trigger** (but same value) |
| created_by | ❌ Just defines column | ✅ Sets value | ✅ Validates/fallback | **Event Listener** (primary) |
| updated_by | ❌ Just defines column | ✅ Sets value | ✅ Validates/fallback | **Event Listener** (primary) |

---

## Why This Design is Better

### Defense in Depth (Multiple Layers)

**Layer 1: TimestampMixin (Timestamps)**
- Sets created_at, updated_at automatically
- Pure Python, no context needed

**Layer 2: Event Listeners (User Tracking)**
- Sets created_by, updated_by from Flask-Login
- Has access to application context
- Sets session variable for Layer 3

**Layer 3: Triggers (Safety Net)**
- Validates values set by Event Listener
- Provides fallback if Event Listener fails
- Works even for non-ORM operations (migrations, SQL)

### Example Scenarios:

**Scenario 1: Normal ORM Operation**
```
TimestampMixin → created_at, updated_at ✅
Event Listener → created_by='7777777777', updated_by='7777777777' ✅
Trigger        → Validates, keeps existing values ✅
Result: Perfect ✅✅✅
```

**Scenario 2: Legacy Table (No TimestampMixin)**
```
TimestampMixin → N/A (no mixin)
Event Listener → N/A (no mixin)
Trigger        → Sets all audit fields to 'system' ✅
Result: Still audited ✅ (safety net works!)
```

**Scenario 3: Direct SQL (Migration)**
```
TimestampMixin → N/A (no ORM)
Event Listener → N/A (no ORM)
Trigger        → Sets all audit fields ✅
Result: Audited ✅ (safety net works!)
```

**Scenario 4: Event Listener Fails**
```
TimestampMixin → created_at, updated_at ✅
Event Listener → Exception! ❌
Trigger        → Sets created_by='system', updated_by='system' ✅
Result: Still audited ✅ (safety net works!)
```

---

## Visual Representation

```
┌─────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                     │
│                                                          │
│  TimestampMixin:                                        │
│    created_at = Column(default=datetime.now) ──┐        │
│    updated_at = Column(onupdate=datetime.now)──┼──┐     │
│    created_by = Column(String)                 │  │     │
│    updated_by = Column(String)                 │  │     │
│                                                │  │     │
│  Event Listeners:                              │  │     │
│    @before_insert: set created_by, updated_by──┼──┼──┐  │
│    @before_update: set updated_by             ─┼──┼──┤  │
│    Set session variable app.current_user      ─┼──┼──┤  │
│                                                │  │  │  │
└────────────────────────────────────────────────┼──┼──┼──┘
                                                 │  │  │
                                                 ↓  ↓  ↓
                                            ┌─────────────┐
                                            │  Database   │
                                            │  INSERT/    │
                                            │  UPDATE     │
                                            └──────┬──────┘
                                                   │
                                                   ↓
┌─────────────────────────────────────────────────────────┐
│                    DATABASE LAYER                        │
│                                                          │
│  Triggers (BEFORE INSERT/UPDATE):                       │
│    track_user_changes():                                │
│      IF created_by IS NULL THEN                         │
│        created_by = session var OR 'system'  ←── Safety │
│      ELSE                                               │
│        KEEP existing value  ←──────────────── Validate  │
│      END IF                                             │
│                                                          │
│    update_timestamp():                                  │
│      updated_at = CURRENT_TIMESTAMP  ←────── Redundant  │
│                                              (but safe)  │
└─────────────────────────────────────────────────────────┘
```

---

## Corrected Understanding

**Your statement:**
> "TimestampMixin will provide right data and trigger will apply it"

**Should be:**
> "TimestampMixin + Event Listeners provide the data, and Triggers validate/enforce it as a safety net"

**More accurately:**
- **TimestampMixin** → Provides `created_at`, `updated_at` (via Column defaults)
- **Event Listeners** → Provide `created_by`, `updated_by` (via before_insert/update events)
- **Triggers** → Validate and provide fallback for ALL four fields

**They work in PARALLEL, not in sequence:**
- TimestampMixin and Event Listeners run at Python/SQLAlchemy level
- Triggers run at PostgreSQL level
- Triggers see the values already set by Python layer
- Triggers keep them (if valid) or provide defaults (if missing)

---

## Summary

✅ TimestampMixin handles `created_at`, `updated_at` (automatic)
✅ Event Listeners handle `created_by`, `updated_by` (from Flask-Login)
✅ Triggers are SAFETY NET for all four fields (cannot be bypassed)

**Together:** Complete, bulletproof audit trail for healthcare compliance! 🎯
