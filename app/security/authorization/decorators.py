# app/security/authorization/decorators.py

from functools import wraps
from flask import jsonify, request
from .permission_validator import has_permission
import logging

# Set up logging
logger = logging.getLogger(__name__)

def token_required(f):
    """
    Decorator to check valid token for protected routes
    
    This decorator:
    1. Extracts the token from the Authorization header
    2. Validates the token using the auth manager
    3. Passes both the user ID and session to the decorated function
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        from app.services.database_service import get_db_session
        from app.security.authentication.auth_manager import validate_token_function
        
        try:
            # Extract token from header
            token = None
            auth_header = request.headers.get('Authorization')
            
            if auth_header:
                try:
                    token = auth_header.split(" ")[1]
                except IndexError:
                    return jsonify({'error': 'Invalid token format'}), 401
            
            if not token:
                return jsonify({'error': 'Token is required'}), 401
            
            # Get database session and validate token
            with get_db_session() as session:
                # Get token authentication result
                user = validate_token_function(token, session)
                
                if not user:
                    return jsonify({'error': 'Invalid or expired token'}), 401
                
                # Store user_id instead of user object
                user_id = user.user_id
                
                # Function now receives user_id instead of user object
                return f(user_id, session, *args, **kwargs)
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return jsonify({'error': 'Authentication error'}), 500
    
    return decorated

def require_permission(module, action):
    """
    Decorator to require a specific permission for an endpoint
    Must be used after @token_required
    
    Args:
        module: Module name to check permission for
        action: Action type (view, add, edit, delete, export)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(user_id, session, *args, **kwargs):
            try:
                # Import the correct models from their actual locations
                from app.models.transaction import User
                from app.models.config import RoleMaster, UserRoleMapping
                
                # Get a fresh user instance
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                # Check for superuser roles - both System Administrator and Hospital Administrator
                try:
                    is_superuser = session.query(UserRoleMapping)\
                        .join(RoleMaster, UserRoleMapping.role_id == RoleMaster.role_id)\
                        .filter(UserRoleMapping.user_id == user_id)\
                        .filter(RoleMaster.role_name.in_(['System Administrator', 'Hospital Administrator']))\
                        .first() is not None
                    
                    # If user is a superuser, allow access immediately
                    if is_superuser:
                        logger.info(f"Superuser access granted: {user_id} for {action} on {module}")
                        return f(user_id, session, *args, **kwargs)
                except Exception as role_error:
                    # Log the error but continue with normal permission check
                    logger.warning(f"Superuser check failed: {str(role_error)}")
                
                # For non-superusers, check specific permissions
                if not has_permission(user, module, action):
                    logger.warning(f"Permission denied: {user_id} attempted {action} on {module}")
                    return jsonify({'error': 'Permission denied'}), 403
                
                # Call the decorated function with user_id and session
                return f(user_id, session, *args, **kwargs)
            except Exception as e:
                logger.error(f"Permission check error: {str(e)}")
                return jsonify({'error': 'Permission check failed'}), 500
                
        return decorated_function
    return decorator