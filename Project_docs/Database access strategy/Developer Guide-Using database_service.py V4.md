# Developer Guide: Using database_service.py

## 1. Introduction

The `database_service.py` module provides a unified, centralized approach to database access throughout the application. It serves as the single entry point for all database operations, abstracting away the complexities of different connection methods and environments.

This guide explains our standardized approach to database session management, which balances performance, reliability, and clean architecture. By following these patterns consistently, you'll ensure database operations are efficient, testable, and maintainable across the entire application.

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

## 3. Session Management Approaches

Our application uses two complementary session management approaches depending on the context:

### 3.1 Decorator-Based Session Management (For Web Routes)

In web routes, especially those protected by authentication, we use a decorator-based approach where:

1. The `token_required` decorator creates a session
2. It validates the user's token using this session
3. It passes both the authenticated user and the active session to the route handler
4. The route handler uses this session for all database operations
5. When the route handler completes, the session is automatically committed or rolled back

```python
@app.route('/users/me')
@token_required
def get_user_profile(current_user, session):
    # Use the session provided by the decorator
    # The user is already attached to this session
    
    # Get additional data using the same session
    settings = session.query(UserSettings).filter_by(user_id=current_user.user_id).first()
    
    return jsonify({
        'user': current_user.to_dict(),
        'settings': settings.to_dict() if settings else None
    })
```

This approach:
- Eliminates detached entity errors by keeping entities attached to their sessions
- Reduces database queries by reusing the same session across the authentication and handler
- Maintains clear transaction boundaries defined by the HTTP request lifecycle

### 3.2 Context Manager Approach (For Services and Background Tasks)

For services and background tasks, we use the context manager approach:

```python
from app.services.database_service import get_db_session

def process_data_batch(items):
    with get_db_session() as session:
        for item in items:
            # Process each item
            record = DataRecord(data=item)
            session.add(record)
            
        # All changes are committed when the context manager exits
```

This approach:
- Creates clear, explicit session boundaries
- Ensures proper resource cleanup even if exceptions occur
- Works consistently in both web and non-web contexts

## 4. Basic Usage

### 4.1 Standard Database Operations

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

### 4.2 Using a Provided Session

When working with session-passing decorators like `token_required`, use the provided session:

```python
@app.route('/profile')
@token_required
def get_profile(current_user, session):
    # Use the session that was passed by the decorator
    profile = session.query(Profile).filter_by(user_id=current_user.user_id).first()
    return jsonify(profile.to_dict())
```

### 4.3 Service Functions with Optional Session Parameters

Design service functions to accept an optional session parameter:

```python
def update_user_profile(user_id, profile_data, session=None):
    # If session is provided, use it
    if session is not None:
        return _perform_update(session, user_id, profile_data)
    
    # Otherwise, create a new session
    with get_db_session() as new_session:
        return _perform_update(new_session, user_id, profile_data)
        
def _perform_update(session, user_id, profile_data):
    profile = session.query(Profile).filter_by(user_id=user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        session.add(profile)
    
    # Update profile attributes
    for key, value in profile_data.items():
        setattr(profile, key, value)
    
    session.flush()
    return profile
```

This pattern allows the function to be used both in routes with decorator-provided sessions and in standalone contexts.

### 4.4 Use session.flush() vs session.commit()

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

### 4.5 Read-Only Operations

For operations that don't modify data, use the `read_only` parameter:

```python
def generate_report():
    with get_db_session(read_only=True) as session:
        # Queries for report generation
        data = session.query(SalesData).filter(SalesData.date >= last_month).all()
        # Process data...
```

This optimizes database performance and prevents accidental data modifications.

## 5. Advanced Usage

### 5.1 Special Considerations for Different Request Types

#### 5.1.1 Long-Running Requests

For endpoints that process data for extended periods (more than a few seconds):

```python
@app.route('/generate-large-report')
@token_required
def generate_large_report(current_user, session):
    # For long-running operations, periodically execute a simple query
    # to keep the connection alive and prevent timeouts
    for i in range(large_number_of_items):
        process_item(i)
        
        # Every 100 items, keep the connection alive
        if i % 100 == 0:
            # Simple ping query to prevent timeout
            session.execute("SELECT 1").fetchone()
            
            # Optionally flush to reduce memory usage
            session.flush()
    
    return jsonify({'status': 'complete'})
```

#### 5.1.2 Batch Processing

For operations that process large datasets:

```python
@app.route('/import-data')
@token_required
def import_data(current_user, session):
    data = request.get_json()
    
    # Process in chunks to avoid memory issues
    CHUNK_SIZE = 100
    for i in range(0, len(data), CHUNK_SIZE):
        chunk = data[i:i+CHUNK_SIZE]
        
        for item in chunk:
            record = DataRecord(**item)
            session.add(record)
        
        # Flush each chunk to release memory
        session.flush()
    
    return jsonify({'status': 'imported'})
```

#### 5.1.3 Background Tasks

For tasks that run outside the HTTP request lifecycle:

```python
def scheduled_cleanup_job():
    with get_db_session() as session:
        # Find expired records
        expired = session.query(TemporaryData).filter(
            TemporaryData.expires_at < datetime.now()
        ).all()
        
        # Delete in batches
        for i in range(0, len(expired), 100):
            batch = expired[i:i+100]
            for record in batch:
                session.delete(record)
            session.flush()
```

For more complex background tasks, consider using a task queue like Celery, but maintain the same session management pattern within each task.

### 5.2 Debugging Database Operations

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

### 5.3 Explicit Connection Type

While auto-detection works for most cases, you can explicitly specify the connection type:

```python
# Force Flask-SQLAlchemy connection
with get_db_session(connection_type='flask') as session:
    # Operations...

# Force direct SQLAlchemy connection
with get_db_session(connection_type='standalone') as session:
    # Operations...
```

### 5.4 Accessing the Database Engine

In rare cases where you need direct access to the SQLAlchemy engine:

```python
from app.services.database_service import get_db_engine

def execute_raw_sql():
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        return result.scalar()
```

### 5.5 Environment Information

Access information about the database environment:

```python
from app.services.database_service import get_active_env, get_database_url

def log_environment_info():
    env = get_active_env()
    url = get_database_url()
    logger.info(f"Current environment: {env}")
    logger.info(f"Database URL: {url}")
```

### 5.6 Controlling Transaction Strategy

You can explicitly control the transaction strategy:

```python
from app.services.database_service import use_nested_transactions

# For complex operations that need savepoints
use_nested_transactions(True)

# For simpler operations or testing
use_nested_transactions(False)
```

## 6. Best Practices

### 6.1 Session Lifecycle

- In web routes with `@token_required`, use the provided session
- In standalone functions, use the context manager pattern
- Keep session usage to the minimum scope needed
- Don't store session objects for later use outside the `with` block

```python
# GOOD: Using provided session
@token_required
def endpoint(current_user, session):
    data = session.query(Data).first()
    return jsonify(data.to_dict())

# GOOD: Limited scope with context manager
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

### 6.2 Visualizing Changes with session.flush()

Use `session.flush()` to make changes visible within a transaction:

```python
def create_user_with_profile(username, email, profile_data, session=None):
    # Handle optional session parameter
    if session is not None:
        return _create_user_with_profile(session, username, email, profile_data)
        
    with get_db_session() as new_session:
        return _create_user_with_profile(new_session, username, email, profile_data)
        
def _create_user_with_profile(session, username, email, profile_data):
    # Create user
    user = User(username=username, email=email)
    session.add(user)
    
    # Flush to get the generated user ID
    session.flush()
    
    # Now we can use the user ID
    profile = UserProfile(user_id=user.id, **profile_data)
    session.add(profile)
    
    # Final flush to ensure all changes are visible
    session.flush()
    
    return user, profile
```

### 6.3 Bulk Operations

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

### 6.4 Common Pitfalls to Avoid

```python
# INCORRECT: Manual session creation
session = SessionLocal()  # Do not do this

# INCORRECT: Manual transaction control
session.begin()  # Avoid direct transaction management

# INCORRECT: Global session storage
global_session = None  # Never maintain global sessions

# CORRECT: Always use context manager or decorator-provided sessions
with get_db_session() as session:
    # Perform database operations safely
```

## 7. Testing Guidelines

### 7.1 Basic Test Structure

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

### 7.2 Test Fixtures

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

### 7.3 Test Database Environment

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

## 8. Integration with Other Services

### 8.1 User Session Management

When integrating with `SessionManager` or other services:

```python
# In a route that receives its session from @token_required
@token_required
def login_user(current_user, session):
    # Get the authentication manager, providing the session
    auth_manager = get_auth_manager(session)
    
    # Perform operations with the auth manager
    # The auth manager uses the provided session
    result = auth_manager.do_something()
    
    return jsonify(result)
```

### 8.2 Ensuring Service Compatibility

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
        # If no session was provided, create a new one
        if not self._session:
            with get_db_session() as session:
                self._session = session
                return self.create_user(username, email)
            
        user = User(username=username, email=email)
        self._session.add(user)
        self._session.flush()  # Make visible without committing
        return user
```

## 9. Benefits of Our Approach

### 9.1 Performance Benefits

1. **Connection Pooling Efficiency**: Sessions are managed for the exact duration needed, optimizing connection pool usage.

2. **Reduced Query Overhead**: By sharing sessions between authentication and endpoint logic, we eliminate duplicate database queries.

3. **Controlled Transaction Boundaries**: Clear transaction scope reduces the chance of long-lived transactions that could impact database performance.

4. **Memory Optimization**: Explicit flush operations and chunked processing prevent memory buildup during large operations.

### 9.2 Architectural Benefits

1. **Separation of Concerns**: Database access is centralized, making it easier to maintain and optimize.

2. **Uniform Access Patterns**: Both web routes and background tasks follow the same database access patterns.

3. **Environment Adaptability**: The same code works across development, testing, and production environments.

4. **Testability**: Clear session boundaries make functions easier to test in isolation.

### 9.3 Standardization Benefits

1. **Consistent Patterns**: All developers follow the same database access patterns, reducing code variability.

2. **Clear Guidelines**: Explicit rules about session management reduce mistakes and misunderstandings.

3. **Maintainability**: New developers can quickly understand how database access works across the application.

4. **Centralized Optimization**: Performance improvements can be made in one place and benefit the entire application.

## 10. Implementation Steps for Consumer Programs

When writing code that needs database access, follow these steps:

### 10.1 For Protected Routes (Using @token_required)

1. Apply the `@token_required` decorator to your route function
2. Ensure your function accepts both `current_user` and `session` parameters
3. Use the provided `session` for all database operations
4. Do not create new sessions within the route handler
5. Do not call `session.commit()` or `session.rollback()`

```python
@app.route('/profile')
@token_required
def update_profile(current_user, session):
    data = request.get_json()
    
    # Use the provided session
    profile = session.query(Profile).filter_by(user_id=current_user.user_id).first()
    if not profile:
        profile = Profile(user_id=current_user.user_id)
        session.add(profile)
    
    # Update profile with data
    for key, value in data.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    
    # No need to commit - handled by decorator
    return jsonify({'status': 'success'})
```

### 10.2 For Service Functions

1. Design functions to accept an optional `session` parameter
2. If a session is provided, use it; otherwise, create a new one
3. Use `session.flush()` to make changes visible, not `session.commit()`
4. Return the results, not the session

```python
def get_user_data(user_id, include_profile=False, session=None):
    # Handle session management
    if session is not None:
        return _get_user_data(session, user_id, include_profile)
        
    # Create a new session if none was provided
    with get_db_session() as new_session:
        return _get_user_data(new_session, user_id, include_profile)
        
def _get_user_data(session, user_id, include_profile):
    # Core logic using the provided session
    user = session.query(User).get(user_id)
    if not user:
        return None
        
    result = {
        'id': user.id,
        'username': user.username,
        'email': user.email
    }
    
    if include_profile:
        profile = session.query(Profile).filter_by(user_id=user.id).first()
        if profile:
            result['profile'] = {
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                # Other profile fields
            }
    
    return result
```

### 10.3 For Background Tasks

1. Always use the context manager pattern
2. Create a new session for each logical operation
3. Process data in chunks for large operations
4. Handle exceptions appropriately

```python
def scheduled_cleanup_job():
    logger.info("Starting scheduled cleanup job")
    
    try:
        # Get list of records to process
        with get_db_session(read_only=True) as session:
            to_process = session.query(Record.id).filter(
                Record.status == 'pending',
                Record.created_at < datetime.now() - timedelta(days=30)
            ).all()
            record_ids = [r.id for r in to_process]
        
        # Process in chunks
        for chunk in chunks(record_ids, 100):
            process_chunk(chunk)
            
        logger.info(f"Cleanup job completed. Processed {len(record_ids)} records.")
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")
        # Handle error notification if needed

def process_chunk(record_ids):
    with get_db_session() as session:
        # Process this chunk of records
        records = session.query(Record).filter(Record.id.in_(record_ids)).all()
        for record in records:
            record.status = 'archived'
        
        # Changes will be committed when the context manager exits
```

## 11. Migrating from Old Code

### 11.1 From Direct SQLAlchemy

If you're currently using SQLAlchemy directly:

```python
# Old code
from app import db

def get_user(user_id):
    user = db.session.query(User).get(user_id)
    return user
    
# New code - Context Manager Approach
from app.services.database_service import get_db_session

def get_user(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        return user

# New code - For Protected Routes
@app.route('/user/<user_id>')
@token_required
def get_user_route(current_user, session, user_id):
    user = session.query(User).get(user_id)
    return jsonify(user.to_dict())
```

### 11.2 From Service-Managed Transactions

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
    if session is not None:
        # Use provided session
        return _create_user(session, username, email)
    
    # Create a new session if none was provided
    with get_db_session() as new_session:
        return _create_user(new_session, username, email)
        
def _create_user(session, username, email):
    user = User(username=username, email=email)
    session.add(user)
    session.flush()  # Make visible within transaction
    return user
```

## 12. Conclusion

The `database_service.py` module, combined with our decorator-based session management for web routes, provides a robust, consistent interface for all database operations across your application. By centralizing database access through this service, you ensure:

- Proper connection management
- Consistent transaction handling
- Comprehensive error processing
- Flexibility across different execution contexts

When developing services and routes:
1. For protected routes, use the session provided by the `@token_required` decorator
2. For services, accept an optional session parameter and handle both cases
3. Always use `session.flush()` rather than `session.commit()` within services
4. Let the database service handle transaction boundaries

This comprehensive approach combines performance efficiency with clean architecture, creating a maintainable and robust foundation for your application's database access.