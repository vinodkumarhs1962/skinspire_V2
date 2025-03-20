# Migration Guide: Updating Test Framework to Use Database Service

## Overview

This guide outlines the changes required to update the test framework to use the new database service layer. The approach allows for a phased migration, maintaining backward compatibility while gradually transitioning each test file.

## Key Changes

1. Added a new `db_service_session` fixture in `conftest.py`
2. Modified existing test files to use the database service
3. Created examples showing both old and new patterns for reference

## Migration Steps for Each Test File

### Step 1: Import the Database Service

Add the following import at the top of each test file:

```python
from app.services.database_service import get_db_session
```

### Step 2: Replace Session Fixture Usage

For new tests, use the `db_service_session` fixture instead of `session`:

```python
# Old pattern
def test_something(client, session, test_hospital):
    # Use session directly
    users = session.query(User).all()
    
# New pattern
def test_something_new(client, db_service_session, test_hospital):
    # Use db_service_session directly
    users = db_service_session.query(User).all()
```

### Step 3: Use Context Manager for Non-Fixture Database Access

If you need to access the database outside a fixture:

```python
# Old pattern
from app.database import get_db
db_manager = get_db()
with db_manager.get_session() as session:
    # Use session

# New pattern
from app.services.database_service import get_db_session
with get_db_session() as session:
    # Use session
```

### Step 4: Update Explicit Transaction Management

The new `db_service_session` fixture handles transactions automatically:

```python
# Old pattern
session.begin()
try:
    # Operations
    session.commit()
except:
    session.rollback()
    raise

# New pattern - no explicit transaction management needed
# The session context manager handles it
with get_db_session() as session:
    # Operations - commit happens automatically
```

## Examples

### Example 1: Simple Query Test

```python
def test_user_exists(db_service_session):
    """Test that admin user exists in database"""
    user = db_service_session.query(User).filter_by(user_id='9876543210').first()
    assert user is not None
    assert user.is_active
```

### Example 2: Creating and Querying Test Data

```python
def test_create_and_query(db_service_session):
    """Test creating and querying data"""
    # Create test data
    test_user = User(
        user_id="test_db_service",
        entity_type="staff",
        entity_id=str(uuid.uuid4()),
        is_active=True
    )
    db_service_session.add(test_user)
    db_service_session.flush()  # Get ID without commit
    
    # Query the data
    fetched_user = db_service_session.query(User).filter_by(
        user_id="test_db_service"
    ).first()
    
    assert fetched_user is not None
    assert fetched_user.user_id == "test_db_service"
    
    # No need to delete - the transaction will be rolled back automatically
```

### Example 3: Using Database Service in Helper Functions

```python
def refresh_entity(entity, id_field='id', id_value=None):
    """Refresh an entity from the database"""
    with get_db_session() as session:
        if id_value is None and hasattr(entity, id_field):
            id_value = getattr(entity, id_field)
        
        entity_class = entity.__class__
        refreshed = session.query(entity_class).filter_by(**{id_field: id_value}).first()
        return refreshed

# Usage
user = refresh_entity(user, id_field='user_id')
```

### Example 4: Data Setup and Teardown

```python
def setup_test_data():
    """Create test data that will persist across tests"""
    with get_db_session() as session:
        # Create test hospital
        hospital = Hospital(
            name="Test Hospital",
            license_no="TEST-123",
            address={"street": "Test St"},
            contact_details={"phone": "555-1234"}
        )
        session.add(hospital)
        session.flush()
        
        # Create test user
        user = User(
            user_id="setup_test_user",
            hospital_id=hospital.hospital_id,
            entity_type="staff",
            entity_id=str(uuid.uuid4()),
            is_active=True
        )
        session.add(user)
        # Commit will be automatic at the end of the context

def teardown_test_data():
    """Clean up persistent test data"""
    with get_db_session() as session:
        session.query(User).filter_by(user_id="setup_test_user").delete()
        session.query(Hospital).filter_by(license_no="TEST-123").delete()
        # Commit will be automatic
```

## Handling Database Environment

The database service automatically determines the correct environment (dev, test, prod). You can still explicitly specify the environment when needed:

```python
from app.services.database_service import DatabaseService

# Get the current environment
env = DatabaseService.get_active_environment()
print(f"Current environment: {env}")

# Get the database URL for the current environment
db_url = DatabaseService.get_database_url()
print(f"Database URL: {db_url}")
```

## Best Practices

1. **Use Fixtures for Common Database Operations**:
   ```python
   @pytest.fixture
   def test_entities(db_service_session):
       """Create common test entities"""
       # Create test entities
       # No need to worry about cleanup - session is rolled back automatically
       return created_entities
   ```

2. **Isolate Test Data**:
   - Use unique identifiers for test data to avoid conflicts
   - Add test prefixes to ensure you don't modify production data
   - Leverage the automatic transaction rollback in `db_service_session`

3. **Optimize Database Access**:
   - Minimize database calls in tests
   - Use bulk operations where possible
   - Consider caching test data that's used across multiple tests

4. **Error Handling**:
   - Always check assertions before continuing with tests
   - Handle errors gracefully in fixtures
   - Add detailed error messages to help with debugging

## Phased Migration Approach

To ensure a smooth transition, follow this phased approach:

1. **Phase 1: Infrastructure Update**
   - Add `db_service_session` fixture to `conftest.py`
   - Create new helper functions that use the database service

2. **Phase 2: New Test Development**
   - Write all new tests using the database service
   - Add example tests to serve as templates

3. **Phase 3: Gradual Migration**
   - Convert one test file at a time, starting with simpler tests
   - Update high-value tests that run frequently
   - Add new `_with_db_service` versions of critical tests before replacing the originals

4. **Phase 4: Complete Migration**
   - Once all tests are migrated, remove the old session fixture
   - Update any remaining helper functions
   - Standardize on the new pattern throughout the codebase

## How to Validate Migration

After migrating a test file, verify it works correctly:

1. Run individual tests to ensure they pass:
   ```
   python -m pytest path/to/test_file.py::TestClass::test_method -v
   ```

2. Run the entire test file:
   ```
   python -m pytest path/to/test_file.py -v
   ```

3. Ensure the `verify_core.py` script still works:
   ```
   python tests/test_security/verify_core.py
   ```

4. Check for proper transaction isolation by adding assertions that would fail if data persisted between tests

## Example Verification Test

```python
def test_transaction_isolation_1(db_service_session):
    """First test to verify transaction isolation"""
    # Create test entity with known ID
    test_user = User(
        user_id="isolation_test_user",
        entity_type="staff",
        entity_id=str(uuid.uuid4()),
        is_active=True
    )
    db_service_session.add(test_user)
    
    # Verify it exists in this transaction
    fetched = db_service_session.query(User).filter_by(user_id="isolation_test_user").first()
    assert fetched is not None

def test_transaction_isolation_2(db_service_session):
    """Second test to verify the transaction from test_transaction_isolation_1 was rolled back"""
    # This entity should not exist if proper isolation is working
    fetched = db_service_session.query(User).filter_by(user_id="isolation_test_user").first()
    assert fetched is None
```

## Troubleshooting Common Issues

1. **Session Disconnected/Expired** 
   - Symptom: "DetachedInstanceError" or "Instance not attached to Session"
   - Solution: Refresh entities or query anew, don't reuse entities across tests

2. **Transaction Not Rolling Back**
   - Symptom: Test data from previous tests is visible
   - Solution: Check if you're bypassing the db_service_session or manually committing

3. **Missing Tables/Relations**  
   - Symptom: "relation does not exist" errors
   - Solution: Ensure you're connecting to the test database and all migrations have run

4. **Connection Pool Exhaustion**
   - Symptom: "TimeoutError" or "Cannot acquire connection"
   - Solution: Ensure sessions are properly closed with context managers

Remember, the goal is to make a smooth transition while ensuring test stability. If unsure about migrating a particular test, create a duplicate version using the new pattern and run both until confident the new version works correctly.