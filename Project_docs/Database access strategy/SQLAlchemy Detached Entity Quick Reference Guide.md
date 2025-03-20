# SQLAlchemy Detached Entity Quick Reference Guide

## Identifying Detached Entity Errors

### Common Error Patterns
- `DetachedInstanceError: Instance <Model at 0x...> is not bound to a Session`
- Accessing lazy-loaded attributes after a session closes
- Errors occurring in assertions after `with get_db_session()` blocks

### Root Causes
- Accessing entity attributes after its session is closed
- Returning entities from functions where sessions are locally scoped
- Using entities across requests or transactions
- Storing entity objects for later use

## Quick Solutions

### 1. Entity Lifecycle Helper Functions

```python
# In database_service.py
def get_detached_copy(entity):
    """Create safe detached copy of entity"""
    if entity is None:
        return None
    EntityClass = entity.__class__
    detached = EntityClass()
    for key, value in entity.__dict__.items():
        if not key.startswith('_'):
            setattr(detached, key, value)
    return detached

def get_entity_dict(entity):
    """Convert entity to dictionary"""
    if entity is None:
        return None
    return {
        key: value for key, value in entity.__dict__.items()
        if not key.startswith('_')
    }
```

### 2. Test Fixture Pattern

```python
@pytest.fixture
def test_entity(db_session):
    entity = Entity(...)
    db_session.add(entity)
    db_session.flush()
    
    # Safe copy for use after session closes
    detached_copy = get_detached_copy(entity)
    
    yield detached_copy
```

### 3. Primitive Value Extraction

```python
def get_user_info(user_id):
    with get_db_session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        # Extract primitives within session
        return {
            "id": user.id,
            "name": user.name,
            "status": user.status
        }
```

### 4. Eager Loading

```python
from sqlalchemy.orm import joinedload

with get_db_session() as session:
    user = session.query(User).options(
        joinedload(User.profile),
        joinedload(User.roles)
    ).filter_by(id=user_id).first()
    
    # Use data while session is active
```

## When to Use Each Approach

- **Detached Copy**: Test fixtures, simple entity snapshot needs
- **Entity Dictionary**: API responses, serialization cases
- **Primitive Extraction**: When only specific attributes are needed
- **Eager Loading**: Complex entity relationships that must be traversed

## Best Practices

1. Never access entities after session closure without proper handling
2. Use `get_detached_copy()` for test fixtures
3. Use `get_entity_dict()` for API responses
4. Extract needed values within the session context
5. For service functions that may be called with or without an active session:
   ```python
   def process_user(user_id, session=None):
       if session is not None:
           return _do_work(session, user_id)
       with get_db_session() as new_session:
           return _do_work(new_session, user_id)
   ```

## Common Patterns by Context

### Web Routes
```python
@app.route('/api/user/<user_id>')
def get_user(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        return jsonify(get_entity_dict(user))
```

### Test Fixtures
```python
@pytest.fixture
def test_user():
    with get_db_session() as session:
        user = create_user(session)
        return get_detached_copy(user)
```

### Service Functions
```python
def get_user_details(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        # Process within session context
        return process_user_data(user)
```

This guide provides a quick reference for identifying and fixing detached entity errors while maintaining your centralized database access philosophy.