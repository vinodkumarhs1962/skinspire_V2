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

### 2.2 Session Management in Flask-SQLAlchemy 3.x

#### Session Creation and Management
In Flask-SQLAlchemy 3.x, use `db.session.registry()` to create thread-local sessions:

```python
# Correct session creation
session = db.session.registry()
```

#### Transaction Handling
Leverage `session.begin_nested()` for granular transaction control:

```python
def perform_database_operation():
    with get_db_session() as session:
        try:
            # Begin a nested transaction (savepoint)
            with session.begin_nested():
                # Perform database operations
                user = User(name='John Doe')
                session.add(user)
        except SQLAlchemyError:
            # Automatic rollback to savepoint
            raise
```

### 2.3 Environment Detection

The database service automatically detects:

- Which environment is active (development, testing, production)
- Whether a Flask application context is available
- The appropriate database URL for the current environment

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

```python
def transfer_funds(from_account, to_account, amount):
    with get_db_session() as session:
        try:
            # Use nested transaction for granular error handling
            with session.begin_nested():
                # Debit from source account
                from_account.balance -= amount
                
                with session.begin_nested():
                    # Credit to destination account
                    to_account.balance += amount
                
            # Outer transaction commits if no exceptions occur
        except Exception as e:
            # Comprehensive error handling
            logger.error(f"Fund transfer failed: {e}")
            raise
```

### 3.3 Read-Only Operations

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
        result = conn.execute("SELECT version()")
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

### 5.2 Nested Transactions and Error Handling

Use `begin_nested()` for complex operations with granular error control:

```python
def complex_user_registration(user_data, profile_data):
    with get_db_session() as session:
        try:
            # Outer transaction
            with session.begin_nested():
                # Create user
                user = User(**user_data)
                session.add(user)
                
                # Nested transaction for profile
                with session.begin_nested():
                    profile = UserProfile(user=user, **profile_data)
                    session.add(profile)
            
            # Automatic commit if no exceptions
        except ValueError as e:
            # Handle specific validation errors
            logger.warning(f"Registration failed: {e}")
            raise
        except Exception as e:
            # Unexpected error handling
            logger.error(f"Unexpected registration error: {e}")
            raise
```

### 5.3 Bulk Operations

For bulk operations, process data in chunks:

```python
def process_large_dataset(items):
    CHUNK_SIZE = 1000
    
    for i in range(0, len(items), CHUNK_SIZE):
        chunk = items[i:i+CHUNK_SIZE]
        
        with get_db_session() as session:
            with session.begin_nested():
                for item in chunk:
                    session.add(Item(**item))
                # Commit happens automatically at end of nested transaction
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

### 5.5 Testing Considerations

In tests, use the database service exactly as you would in application code:

```python
def test_user_creation():
    with get_db_session() as session:
        with session.begin_nested():
            # Create test user
            user = User(name='Test User', email='test@example.com')
            session.add(user)
            session.flush()  # Get ID without committing
            
            # Test assertions
            assert user.id is not None
            assert user.name == 'Test User'
        
        # Transaction is rolled back automatically in tests
```

## 6. Implementation Details

### 6.1 Connection Management

The database service maintains:

- A global engine for standalone connections
- A session factory for creating new sessions
- Internal tracking of initialization status

### 6.2 Transaction Boundaries

Transaction boundaries are managed through context managers:

- `_get_flask_session()` for Flask contexts
- `_get_standalone_session()` for non-Flask contexts

Both provide identical interfaces despite different implementations.

### 6.3 Environment Detection

Environment detection uses:

1. The `FLASK_ENV` environment variable
2. A `.flask_env_type` file if present
3. Default fallback to 'development'

## 7. Performance and Optimization

### 7.1 Connection Pooling

The database service leverages SQLAlchemy's built-in connection pooling:

- Automatically manages database connections
- Reuses connections to reduce overhead
- Configurable pool size and timeout

### 7.2 Session Management Overhead

- `db.session.registry()` provides minimal overhead
- Thread-local sessions ensure safe concurrent access
- Nested transactions (`begin_nested()`) offer lightweight savepoint mechanics

## 8. Troubleshooting

### 8.1 Common Errors

- **Transaction Already Begun**: Use `session.begin_nested()` to create savepoints
- **Session Closed Errors**: Always use context managers
- **Connection Leaks**: Ensure proper session closure

### 8.2 Debugging Techniques

- Enable debug mode with `set_debug_mode(True)`
- Log detailed transaction information
- Monitor session lifecycle in complex applications

## 9. Conclusion

The `database_service.py` module provides a robust, consistent interface for all database operations across your application. By centralizing database access through this service, you ensure:

- Proper connection management
- Consistent transaction handling
- Comprehensive error processing
- Flexibility across different execution contexts

**Always use `get_db_session()` for database operations, and let the database service handle the complexities of different environments and connection methods.**