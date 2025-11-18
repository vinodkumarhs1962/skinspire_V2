"""
Research how TimestampMixin works and how to make it handle user tracking
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 80)
print("RESEARCH: TimestampMixin and SQLAlchemy Event Listeners")
print("=" * 80)

print("""
## How TimestampMixin Currently Works

1. **created_at**: Uses Column(default=lambda: datetime.now())
   - SQLAlchemy calls the lambda function ONCE when creating the object
   - Works automatically

2. **updated_at**: Uses Column(onupdate=lambda: datetime.now())
   - SQLAlchemy calls the lambda function on UPDATE operations
   - Works automatically

3. **created_by and updated_by**: Just Column(String(50))
   - NO default, NO onupdate
   - These are PASSIVE columns - they don't do anything automatically

## Why created_by/updated_by Don't Auto-Update

The `default` and `onupdate` parameters work for timestamp columns because:
- They can generate values WITHOUT external context (just call datetime.now())
- They don't need to know WHO is doing the operation

For user tracking, we need CONTEXT:
- Who is the current user?
- This information is not available to the Column definition

## Solutions for User Tracking with TimestampMixin

### Option 1: SQLAlchemy Event Listeners (RECOMMENDED)

Add event listeners to TimestampMixin that automatically set created_by/updated_by
based on the current Flask-Login user or a session variable.

```python
from sqlalchemy import event
from flask_login import current_user

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(String(50))
    updated_by = Column(String(50))

# Event listener for ALL classes that use TimestampMixin
@event.listens_for(TimestampMixin, 'before_insert', propagate=True)
def set_created_by(mapper, connection, target):
    if hasattr(target, 'created_by'):
        # Try to get user from Flask-Login
        try:
            if current_user and current_user.is_authenticated:
                target.created_by = current_user.user_id
                target.updated_by = current_user.user_id
            else:
                target.created_by = 'system'
                target.updated_by = 'system'
        except:
            target.created_by = 'system'
            target.updated_by = 'system'

@event.listens_for(TimestampMixin, 'before_update', propagate=True)
def set_updated_by(mapper, connection, target):
    if hasattr(target, 'updated_by'):
        try:
            if current_user and current_user.is_authenticated:
                target.updated_by = current_user.user_id
            else:
                target.updated_by = 'system'
        except:
            target.updated_by = 'system'
```

**Pros:**
- Centralized in one place (TimestampMixin)
- Works automatically for ALL models using the mixin
- Application-level control (no database triggers)
- Can access Flask-Login's current_user

**Cons:**
- Only works when using SQLAlchemy ORM (not raw SQL)
- Needs Flask application context to access current_user

---

### Option 2: Database Triggers (CURRENT STATE)

Keep the PostgreSQL triggers but pass user context via session variable.

**Pros:**
- Works for ANY database operation (ORM, raw SQL, migrations)
- Bulletproof - can't be bypassed
- Already implemented

**Cons:**
- Split between TimestampMixin (timestamps) and triggers (users)
- Need to set session variable before operations

---

### Option 3: Hybrid Approach (BEST OF BOTH WORLDS)

1. Use TimestampMixin for timestamps (created_at, updated_at)
2. Use SQLAlchemy event listeners for user tracking (created_by, updated_by)
3. Remove database triggers entirely

This gives us:
- ✅ Everything in Python/SQLAlchemy
- ✅ Single mechanism (TimestampMixin + events)
- ✅ Consistent behavior
- ✅ No database-level magic

---

## Recommendation

**Option 3: Enhance TimestampMixin with Event Listeners**

1. Add SQLAlchemy event listeners to TimestampMixin
2. Remove database triggers (update_timestamp and track_user_changes)
3. Access current_user from Flask-Login context
4. All four fields managed by ONE mechanism

This is the cleanest solution and follows SQLAlchemy best practices.
""")
