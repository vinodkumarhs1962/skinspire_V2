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

### 2.2 Environment Detection

The database service automatically detects:

- Which environment is active (development, testing, production)
- Whether a Flask application context is available
- The appropriate database URL for the current environment

### 2.3 Context-Appropriate Connections

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
        # No need for commit - handled by context manager
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
            # Debit from source account
            from_account.balance -= amount
            # Credit to destination account
            to_account.balance += amount
            
            # Transaction automatically committed if no exceptions
        except Exception as e:
            # Transaction automatically rolled back
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

### 5.2 Bulk Operations

For bulk operations, process data in chunks:

```python
def process_large_dataset(items):
    CHUNK_SIZE = 1000
    
    for i in range(0, len(items), CHUNK_SIZE):
        chunk = items[i:i+CHUNK_SIZE]
        
        with get_db_session() as session:
            # Process this chunk
            for item in chunk:
                session.add(Item(**item))
            # Commit happens automatically at end of with block
```

### 5.3 Error Handling

While basic error handling is built in, add specific handling for domain logic:

```python
def update_user_profile(user_id, data):
    try:
        with get_db_session() as session:
            user = session.query(User).get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
                
            # Update user fields
            for key, value in data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
                    
            # Will be automatically committed if no exceptions
            return user
            
    except ValueError as e:
        # Handle specific domain error
        logger.warning(f"User update failed: {e}")
        raise
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error updating user: {e}")
        raise
```

### 5.4 Testing

In tests, use the database service exactly as you would in application code:

```python
def test_user_creation():
    # Setup
    user_data = {
        'name': 'Test User',
        'email': 'test@example.com'
    }
    
    # Use database service just like in application code
    with get_db_session() as session:
        # Create user
        user = User(**user_data)
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

## 7. Conclusion

The database_service.py module provides a robust, consistent interface for all database operations across your application. By centralizing database access through this service, you ensure proper connection management, transaction handling, and error processing regardless of the execution context.

Always use `get_db_session()` for database operations, and let the database service handle the complexities of different environments and connection methods.