# Skinspire User Management and Authorization Documentation

## Architecture Overview

Skinspire implements a comprehensive role-based access control (RBAC) system with a multi-tenant architecture designed for healthcare environments that require rigorous security and data partitioning.

### Core Components

1. **User Management System**
   - Multi-tenant user storage (hospital-specific)
   - Entity-based user identification (staff or patient)
   - Session management with JWT tokens
   - Password security with hashing and policy enforcement

2. **Authorization Framework**
   - Role-based permissions
   - Module-based access control
   - Granular action permissions (view/add/edit/delete/export)
   - Hospital-specific role configuration

3. **Security Infrastructure**
   - Encrypted sensitive data
   - Audit logging of security events
   - Rate limiting and account lockout mechanisms
   - Token-based API security

## Database Schema

The authorization system relies on several interconnected tables:

- **User**: Stores user credentials and basic information
- **RoleMaster**: Defines roles available in the system
- **ModuleMaster**: Defines system modules/features
- **RoleModuleAccess**: Maps roles to modules with specific permissions
- **UserRoleMapping**: Associates users with roles
- **LoginHistory**: Tracks authentication attempts
- **UserSession**: Manages active sessions

## Implementation Details

### User Authentication Flow

1. User submits credentials via `/api/auth/login`
2. System verifies credentials and account status
3. Upon success, a JWT token is generated and returned
4. Token contains user ID and session information
5. Subsequent requests use this token for authentication

### Permission Validation Process

1. Request arrives with JWT token
2. Token is validated via `token_required` decorator
3. The endpoint is protected with `require_permission` decorator
4. Permission validator checks if user has required permissions:
   - Retrieves user's roles
   - Checks role permissions for the requested module/action
   - Returns boolean result

### Code Structure

Key files:
- `app/security/authentication/auth_manager.py`: Handles authentication
- `app/security/authorization/permission_validator.py`: Validates permissions
- `app/security/authorization/decorators.py`: Provides route protection
- `app/models/master.py`: Contains Hospital, Branch, Staff, Patient models
- `app/models/transaction.py`: Contains User, LoginHistory, UserSession models
- `app/models/config.py`: Contains RoleMaster, ModuleMaster, RoleModuleAccess models

## Lessons Learned

### SQLAlchemy Session Management

1. **Detached Objects Issue**: SQLAlchemy objects become detached from their session after the session is closed or committed, making attribute access problematic.

   **Solution**: When working with objects across multiple operations:
   - Store primitive IDs rather than entire objects
   - Re-query the database using IDs when needed
   - Access attributes only when objects are attached to an active session

2. **Transaction Isolation**: Test code often opens and closes multiple sessions, making object tracking complex.

   **Solution**:
   - Use explicit session handling with context managers
   - Capture necessary IDs immediately after object creation
   - Apply transaction boundary patterns to isolate database operations

### Permission System Design

1. **Caching Considerations**: Permission checks can be expensive with frequent database queries.

   **Solution**: Implement permission caching at appropriate levels:
   - Session-level caching
   - Time-based cache invalidation
   - Using Redis for distributed systems

2. **Granular vs. Coarse Permissions**: Very fine-grained permissions can become unwieldy.

   **Solution**: Group related permissions logically and evaluate permission design based on actual usage patterns.

### Testing Strategies

1. **Fixture Independence**: Tests should be isolated and not depend on database state from other tests.

   **Solution**:
   - Create and clean up test data within the same test
   - Use unique identifiers for test entities
   - Apply proper transaction management

2. **Mocking vs. Integration Testing**: Deciding between mocked components and end-to-end tests.

   **Solution**: Use a combination approach:
   - Unit tests with mocked components for fast feedback
   - Integration tests with database access for completeness

## Next Steps

### 1. Performance Optimization

- **Permission Caching**: Implement a caching layer for permission checks to reduce database load.
- **Query Optimization**: Optimize role and permission queries with proper indexes and join strategies.
- **Session Management**: Optimize token validation and consider Redis for session storage.

### 2. Enhanced Security Features

- **Two-Factor Authentication**: Implement 2FA for sensitive operations.
- **Advanced Threat Protection**: Add IP-based restrictions and anomaly detection.
- **Token Refresh Mechanism**: Implement token refresh for longer sessions without compromising security.
- **Fine-Grained Audit Logging**: Expand audit logs to cover all authorization decisions.

### 3. Administrative Interface

- **Role Management UI**: Develop an interface for administrators to manage roles and permissions.
- **Permission Report**: Create a visualization of user permissions for auditing purposes.
- **User Activity Dashboard**: Build a dashboard to monitor authentication events and permission use.

### 4. Extended Testing

- **Performance Benchmarks**: Establish benchmarks for authorization operations.
- **Security Testing**: Perform penetration testing on the authentication system.
- **Load Testing**: Verify system behavior under high user load.

### 5. Documentation and Standards

- **API Documentation**: Complete OpenAPI/Swagger documentation for auth endpoints.
- **Coding Standards**: Establish consistent patterns for permission checks.
- **Security Requirements**: Formalize security requirements for new features.

## Implementation Reference 

### Permission Validator

```python
def has_permission(user, module_name: str, permission_type: str) -> bool:
    """
    Check if a user has permission to perform an action on a module
    
    Args:
        user: The user to check permissions for (User object or user_id)
        module_name: The name of the module to check access for
        permission_type: The action to check (view, add, edit, delete, export)
        
    Returns:
        bool: True if user has permission, False otherwise
    """
    # Extract user_id if full user object provided
    user_id = user.user_id if hasattr(user, 'user_id') else user
    
    db_manager = get_db()
    with db_manager.get_session() as session:
        # First check if user is active by querying the database
        user_record = session.query(User).filter_by(user_id=user_id).first()
        if not user_record or not user_record.is_active:
            return False
            
        # Special case for admin users
        if user_record.entity_type == 'admin':
            return True
            
        # Get module ID
        module = session.query(ModuleMaster).filter_by(module_name=module_name).first()
        if not module:
            return False
            
        # Get user's roles
        role_mappings = session.query(UserRoleMapping).filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        role_ids = [mapping.role_id for mapping in role_mappings]
        if not role_ids:
            return False
            
        # Check permissions for all roles
        permissions = session.query(RoleModuleAccess).filter(
            RoleModuleAccess.role_id.in_(role_ids),
            RoleModuleAccess.module_id == module.module_id
        ).all()
        
        if not permissions:
            return False
        
        # Check if any role has the requested permission
        permission_field = f"can_{permission_type}"
        for permission in permissions:
            if getattr(permission, permission_field, False):
                return True
                
        return False
```

### Route Protection Decorator

```python
def require_permission(module, action):
    """
    Decorator to require a specific permission for an endpoint
    Must be used after @token_required
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(current_user, *args, **kwargs):
            if not has_permission(current_user, module, action):
                return jsonify({'error': 'Permission denied'}), 403
            return f(current_user, *args, **kwargs)
        return decorated_function
    return decorator
```

### Usage Example

```python
@app.route('/api/patients', methods=['GET'])
@token_required
@require_permission('patients', 'view')
def get_patients(current_user):
    # Only users with 'view' permission on 'patients' module can access this
    return jsonify({'patients': get_patient_list()})

@app.route('/api/patients', methods=['POST'])
@token_required
@require_permission('patients', 'add')
def add_patient(current_user):
    # Only users with 'add' permission on 'patients' module can access this
    return jsonify({'success': True, 'patient_id': create_patient(request.json)})
```
