# Developer Guide: Using database_service.py

## 1. Introduction

The `database_service.py` module provides a unified, centralized approach to database access throughout the application. It serves as the single entry point for all database operations, abstracting away the complexities of different connection methods and environments.

## 2. Core Concepts

### 2.1 Single Point of Entry

All database access should flow through the database service. This ensures:

- Consistent transaction management
- Proper connection pooling
- Centralized error handling
- Environment-appropriate connections

### 2.2 Transaction Strategy

The database service supports two transaction strategies:

#### 2.2.1 Nested Transactions (Default for Production)
In production environments, the service uses nested transactions by default:

```python
# This behavior happens automatically in production
with get_db_session() as session:
    # The outer transaction is managed by get_db_session()
    
    # You can create nested transactions (savepoints) for finer control
    with session.begin_nested():
        user = User(name='John Doe')
        session.add(user)
        # This savepoint can be rolled back without affecting the outer transaction
```

#### 2.2.2 Simple Transactions (Default for Testing)
In testing environments, the service uses simple transactions:

```python
# This behavior happens automatically in testing
with get_db_session() as session:
    # A single transaction is managed by get_db_session()
    user = User(name='John Doe')
    session.add(user)
    # Changes are visible within this session
    # The transaction is committed or rolled back when exiting the context
```

You can explicitly control this behavior using:

```python
from app.services.database_service import use_nested_transactions

# Enable nested transactions (default in production)
use_nested_transactions(True)

# Disable nested transactions (default in testing)
use_nested_transactions(False)
```

### 2.3 Environment Detection

The database service automatically detects:

- Which environment is active (development, testing, production)
- Whether a Flask application context is available
- The appropriate database URL for the current environment
- Which transaction strategy to use based on the environment

### 2.4 Context-Appropriate Connections

Based on the execution context, the database service selects the appropriate connection method:

- **With Flask context**: Uses Flask-SQLAlchemy for web routes
- **Without Flask context**: Uses direct SQLAlchemy connections for background tasks

This decision is completely transparent to user code—the same API works in all contexts.

## 3. Basic Usage

### 3.1 Standard Database Operations

```python
from app.services.database_service import get_db_session

def get_users_by_status(status):
    with get_db_session() as session:
        return session.query(User).filter_by(status=status).all()

def create_new_user(user_data):
    with get_db_session() as session:
        user = User(**user_data)
        session.add(user)
        # No need for explicit commit - handled by context manager
        return user
```

### 3.2 Transaction Management

Transactions are automatically managed by the context manager:

- Transaction begins when entering the `with` block
- Successful completion commits the transaction
- Exceptions cause automatic rollback
- Connection resources are properly closed

For finer control in production environments, you can use nested transactions:

```python
def transfer_funds(from_account, to_account, amount):
    with get_db_session() as session:
        try:
            # Use nested transaction for granular error handling
            with session.begin_nested():
                # Debit from source account
                from_account.balance -= amount
                session.flush()  # Make changes visible within this transaction
                
                with session.begin_nested():
                    # Credit to destination account
                    to_account.balance += amount
                    session.flush()  # Make changes visible within this transaction
                
            # Outer transaction commits if no exceptions occur
        except Exception as e:
            # Comprehensive error handling
            logger.error(f"Fund transfer failed: {e}")
            raise
```

### 3.3 Use session.flush() vs session.commit()

For operations within the database service context:

- Use `session.flush()` to make changes visible within the current transaction
- Never use `session.commit()` directly - let the context manager handle it
- Never use `session.rollback()` directly - let the context manager handle it

```python
# CORRECT
with get_db_session() as session:
    user = User(name='John Doe')
    session.add(user)
    session.flush()  # Make changes visible within the transaction
    print(f"User ID: {user.id}")  # The ID is now available

# INCORRECT - don't call commit() or rollback() directly
with get_db_session() as session:
    user = User(name='John Doe')
    session.add(user)
    session.commit()  # DON'T DO THIS
```

### 3.4 Read-Only Operations

For operations that don't modify data, use the `read_only` parameter:

```python
def generate_report():
    with get_db_session(read_only=True) as session:
        # Queries for report generation
        data = session.query(SalesData).filter(SalesData.date >= last_month).all()
        # Process data...
```

This optimizes database performance and prevents accidental data modifications.

## 4. Advanced Usage

### 4.1 Debugging Database Operations

Enable debug mode to see detailed logging:

```python
from app.services.database_service import set_debug_mode

# Enable debug mode
set_debug_mode(True)

# Perform database operations
with get_db_session() as session:
    # All operations will be logged in detail
    users = session.query(User).all()
```

### 4.2 Explicit Connection Type

While auto-detection works for most cases, you can explicitly specify the connection type:

```python
# Force Flask-SQLAlchemy connection
with get_db_session(connection_type='flask') as session:
    # Operations...

# Force direct SQLAlchemy connection
with get_db_session(connection_type='standalone') as session:
    # Operations...
```

### 4.3 Accessing the Database Engine

In rare cases where you need direct access to the SQLAlchemy engine:

```python
from app.services.database_service import get_db_engine

def execute_raw_sql():
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        return result.scalar()
```

### 4.4 Environment Information

Access information about the database environment:

```python
from app.services.database_service import get_active_env, get_database_url

def log_environment_info():
    env = get_active_env()
    url = get_database_url()
    logger.info(f"Current environment: {env}")
    logger.info(f"Database URL: {url}")
```

### 4.5 Controlling Transaction Strategy

You can explicitly control the transaction strategy:

```python
from app.services.database_service import use_nested_transactions

# For complex operations that need savepoints
use_nested_transactions(True)

# For simpler operations or testing
use_nested_transactions(False)
```

## 5. Best Practices

### 5.1 Session Lifecycle

- Always use the `with` statement to ensure proper resource cleanup
- Keep session usage to the minimum scope needed
- Don't store session objects for later use outside the `with` block

```python
# GOOD: Limited scope
def get_user(user_id):
    with get_db_session() as session:
        return session.query(User).get(user_id)

# BAD: Session escaping scope
def get_user_bad(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
    # Session is closed here!
    user.name = "New Name"  # This will fail
    return user
```

### 5.2 Visualizing Changes with session.flush()

Use `session.flush()` to make changes visible within a transaction:

```python
def create_user_with_profile(username, email, profile_data):
    with get_db_session() as session:
        # Create user
        user = User(username=username, email=email)
        session.add(user)
        
        # Flush to get the generated user ID
        session.flush()
        
        # Now we can use the user ID
        profile = UserProfile(user_id=user.id, **profile_data)
        session.add(profile)
        
        # No need for commit - handled by context manager
        return user, profile
```

### 5.3 Bulk Operations

For bulk operations, process data in chunks:

```python
def process_large_dataset(items):
    CHUNK_SIZE = 1000
    
    for i in range(0, len(items), CHUNK_SIZE):
        chunk = items[i:i+CHUNK_SIZE]
        
        with get_db_session() as session:
            for item in chunk:
                session.add(Item(**item))
            # Commit happens automatically at end of context
```

### 5.4 Common Pitfalls to Avoid

```python
# INCORRECT: Manual session creation
session = SessionLocal()  # Do not do this

# INCORRECT: Manual transaction control
session.begin()  # Avoid direct transaction management

# INCORRECT: Global session storage
global_session = None  # Never maintain global sessions

# CORRECT: Always use context manager
with get_db_session() as session:
    # Perform database operations safely
```

## 6. Testing Guidelines

### 6.1 Basic Test Structure

For testing, the database service automatically disables nested transactions. Use a standard structure:

```python
def test_some_function():
    # Use the db_session fixture provided by conftest.py
    with get_db_session() as session:
        # Create test data
        user = User(name='Test User')
        session.add(user)
        session.flush()  # Make changes visible
        
        # Perform test actions
        result = some_function_under_test(user.id)
        
        # Assert results
        assert result.is_valid
        
    # Session automatically rolls back after the test
```

### 6.2 Test Fixtures

In your `conftest.py`, implement a `db_session` fixture that works with the database service:

```python
@pytest.fixture(scope='function')
def db_session():
    """Create a fresh database session for testing."""
    from app.services.database_service import get_db_session
    
    with get_db_session() as session:
        try:
            yield session
            # The session will be automatically handled
            # by the context manager
        except Exception as e:
            logger.error(f"Test session error: {str(e)}")
            raise
```

### 6.3 Test Database Environment

Ensure that tests run in the testing environment:

```python
# In conftest.py
import os

# Set environment for testing
os.environ['FLASK_ENV'] = 'testing'

# Ensure nested transactions are disabled for testing
from app.services.database_service import use_nested_transactions
use_nested_transactions(False)
```

## 7. Integration with Other Services

### 7.1 User Session Management

When integrating with `SessionManager` or other services:

```python
def login_user(username, password):
    with get_db_session() as session:
        # Get the authentication manager
        auth_manager = get_auth_manager()
        
        # Provide the current database session
        auth_manager.set_db_session(session)
        
        # Perform authentication - this uses our session
        result = auth_manager.authenticate_user(username, password)
        if result['success']:
            return True
            
    return False
```

### 7.2 Ensuring Service Compatibility

Services that interact with the database should:

1. Accept a database session as a parameter
2. Use `session.flush()` instead of `session.commit()`
3. Not call `session.rollback()` directly
4. Raise exceptions instead of handling transactions

Example service:
```python
class UserService:
    def __init__(self, session=None):
        self._session = session
    
    def set_db_session(self, session):
        self._session = session
    
    def create_user(self, username, email):
        if not self._session:
            raise ValueError("Database session required")
            
        user = User(username=username, email=email)
        self._session.add(user)
        self._session.flush()  # Make visible without committing
        return user
```

## 8. Implementation Details

### 8.1 Connection Management

The database service maintains:

- A global engine for standalone connections
- A session factory for creating new sessions
- Internal tracking of initialization status
- Configuration for transaction strategy

### 8.2 Transaction Boundaries

Transaction boundaries are managed through context managers:

- `_get_flask_session()` for Flask contexts
- `_get_standalone_session()` for non-Flask contexts

Both provide identical interfaces despite different implementations.

### 8.3 Environment Detection

Environment detection uses:

1. The `FLASK_ENV` environment variable
2. A `.flask_env_type` file if present
3. Default fallback to 'development'

## 9. Migrating Existing Code

### 9.1 From Direct SQLAlchemy

If you're currently using SQLAlchemy directly:

```python
# Old code
from app import db

def get_user(user_id):
    user = db.session.query(User).get(user_id)
    return user
    
# New code
from app.services.database_service import get_db_session

def get_user(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        return user
```

### 9.2 From Service-Managed Transactions

If your services currently manage their own transactions:

```python
# Old service code
def create_user(username, email):
    user = User(username=username, email=email)
    db.session.add(user)
    db.session.commit()
    return user
    
# New service code
def create_user(username, email, session=None):
    if not session:
        # If no session provided, create one
        with get_db_session() as session:
            return create_user(username, email, session)
    
    user = User(username=username, email=email)
    session.add(user)
    session.flush()  # Make visible within transaction
    return user
```

### 9.3 From Custom Transaction Management

If you're manually managing transactions:

```python
# Old code
def complex_operation():
    session = db.session
    try:
        # Do work...
        session.commit()
    except Exception as e:
        session.rollback()
        raise
        
# New code
def complex_operation():
    with get_db_session() as session:
        # Do work...
        # No explicit commit/rollback needed
```

## 10. Troubleshooting

### 10.1 Common Errors

- **Transaction Already Begun**: Use `session.begin_nested()` for savepoints
- **Session Closed Errors**: Always use context managers
- **Connection Leaks**: Ensure proper session closure
- **This Transaction is Closed**: Don't use a session after its context manager exits

### 10.2 Debugging Techniques

- Enable debug mode with `set_debug_mode(True)`
- Log detailed transaction information
- Monitor session lifecycle in complex applications
- Check session state with `session.is_active`

## 11. Conclusion

The `database_service.py` module provides a robust, consistent interface for all database operations across your application. By centralizing database access through this service, you ensure:

- Proper connection management
- Consistent transaction handling
- Comprehensive error processing
- Flexibility across different execution contexts

When developing services that interact with the database:
1. Always use `get_db_session()` for database operations
2. Use `session.flush()` rather than `session.commit()` within services
3. Let the database service handle transaction boundaries
4. Accept sessions as parameters in your service methods

For test fixtures:
1. Disable nested transactions with `use_nested_transactions(False)`
2. Use simple session operations in tests
3. Let the database service handle commits and rollbacks

**Always use `get_db_session()` for database operations, and let the database service handle the complexities of different environments and connection methods.**


Implementation Notes
When implementing these changes across your codebase:

Start by updating database_service.py with our new version that supports toggling nested transactions
Next, update the core test fixtures in conftest.py to disable nested transactions
Then, update authentication-related services to accept session parameters
Finally, gradually update other services and routes to follow the patterns in the guide

The most important pattern to establish is:

Services should accept database sessions as parameters
Services should use session.flush() instead of session.commit()
Services should not manage transactions directly
Routes and controllers should use get_db_session() to provide sessions to services