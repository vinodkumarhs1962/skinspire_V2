# app/security/authorization/decorators.py

from functools import wraps
from flask import jsonify, request, g
from .permission_validator import has_permission
from flask_login import current_user
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

def require_branch_permission(module, action, branch_source='auto'):
    """
    NEW: Branch-aware permission decorator
    Clean decorator that delegates to service functions
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(user_id, session, *args, **kwargs):
            try:
                from app.models.transaction import User
                from app.services.branch_service import (
                    check_superuser_status,
                    determine_branch_context_from_request,
                    get_branch_context_for_decorator
                )
                from app.services.permission_service import (
                    has_branch_permission,
                    is_branch_role_enabled_for_module,
                    has_permission as service_has_permission
                )
                
                # Get user object
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                # Check for superuser roles
                if check_superuser_status(user_id, session):
                    logger.info(f"Superuser branch access granted: {user_id} for {action} on {module}")
                    return f(user_id, session, *args, **kwargs)
                
                # Check if branch validation is enabled for this module
                if not is_branch_role_enabled_for_module(module):
                    # Fall back to legacy permission system
                    if not service_has_permission(user, module, action):
                        logger.warning(f"Legacy permission denied: {user_id} attempted {action} on {module}")
                        return jsonify({'error': 'Permission denied'}), 403
                    return f(user_id, session, *args, **kwargs)
                
                # Determine branch context using branch_service
                branch_id = determine_branch_context_from_request(user, request, branch_source, session)
                
                # Check branch-specific permission
                if not has_branch_permission(user, module, action, branch_id):
                    logger.warning(f"Branch permission denied: {user_id} attempted {action} on {module} in branch {branch_id}")
                    return jsonify({'error': 'Branch permission denied'}), 403
                
                # Set branch context for view function using branch_service
                g.branch_context = get_branch_context_for_decorator(
                    user_id, user.hospital_id, branch_id, module, action
                )
                
                return f(user_id, session, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Branch permission check error: {str(e)}")
                return jsonify({'error': 'Permission check failed'}), 500
                
        return decorated_function
    return decorator

def require_cross_branch_permission(module, action='view'):
    """
    NEW: Decorator for cross-branch permissions (executives)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(user_id, session, *args, **kwargs):
            try:
                from app.models.transaction import User
                from app.services.permission_service import has_cross_branch_permission
                from app.services.branch_service import get_branch_context_for_decorator
                
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    return jsonify({'error': 'User not found'}), 404
                
                # Testing bypass
                if user_id == '7777777777':
                    logger.info(f"Testing bypass: cross-branch access granted for {user_id}")
                    g.branch_context = get_branch_context_for_decorator(
                        user_id, user.hospital_id, 'all', module, action
                    )
                    return f(user_id, session, *args, **kwargs)
                
                # Check cross-branch permission
                if not has_cross_branch_permission(user, module, action):
                    logger.warning(f"Cross-branch permission denied: {user_id} attempted {action} on {module}")
                    return jsonify({'error': 'Cross-branch permission denied'}), 403
                
                # Set cross-branch context
                g.branch_context = get_branch_context_for_decorator(
                    user_id, user.hospital_id, 'all', module, action
                )
                g.branch_context['is_cross_branch'] = True
                
                return f(user_id, session, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Cross-branch permission check error: {str(e)}")
                return jsonify({'error': 'Permission check failed'}), 500
                
        return decorated_function
    return decorator

def require_web_branch_permission(module_name, permission_type, branch_source='auto'):
    """
    Decorator for Flask-Login based web views with branch awareness
    Compatible with existing @login_required pattern
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                from flask import g, flash, redirect, url_for
                from app.services.permission_service import (
                    has_branch_permission, 
                    is_branch_role_enabled_for_module,
                    has_permission as service_has_permission
                )
                from app.services.branch_service import (
                    determine_branch_context_from_request,
                    get_branch_context_for_decorator
                )
                
                if not current_user.is_authenticated:
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('auth.login'))
                
                # Testing bypass (preserve existing pattern)
                if current_user.user_id == '7777777777':
                    # CRITICAL FIX: Set g.branch_context even for testing bypass
                    # to prevent 'NoneType' subscriptable errors in templates/handlers
                    if not hasattr(g, 'branch_context') or g.branch_context is None:
                        g.branch_context = {
                            'method': 'testing_bypass',
                            'accessible_branches': [],
                            'assigned_branch_id': None,
                            'can_cross_branch': True,
                            'is_multi_branch_user': False,
                            'branch_filter_required': False
                        }
                    return f(*args, **kwargs)
                
                # Check if branch validation is enabled for this module
                if not is_branch_role_enabled_for_module(module_name):
                    # Fall back to legacy permission system (current pattern)
                    if not service_has_permission(current_user, module_name, permission_type):
                        flash(f'You do not have permission to {permission_type} {module_name}', 'danger')
                        return redirect(url_for('auth_views.dashboard'))
                    return f(*args, **kwargs)
                
                # Determine branch context (NEW)
                branch_id = determine_branch_context_from_request(
                    current_user, request, branch_source
                )
                
                # Check branch-specific permission (NEW)
                if not has_branch_permission(current_user, module_name, permission_type, branch_id):
                    flash(f'You do not have permission to {permission_type} {module_name} in this branch', 'danger')
                    return redirect(url_for('auth_views.dashboard'))
                
                # Set branch context for view function (NEW)
                # CRITICAL FIX: Ensure g.branch_context is never None
                branch_context = get_branch_context_for_decorator(
                    current_user.user_id, current_user.hospital_id, 
                    branch_id, module_name, permission_type
                )
                g.branch_context = branch_context if branch_context else {}
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Web branch permission check error: {str(e)}")
                flash('Permission check failed', 'error')
                return redirect(url_for('auth_views.dashboard'))
                
        return decorated_function
    return decorator

def require_web_cross_branch_permission(module_name, action='view'):
    """
    Decorator for cross-branch permissions (executives) - Flask-Login compatible
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                from flask import g, flash, redirect, url_for
                from app.services.permission_service import has_cross_branch_permission
                from app.services.branch_service import get_branch_context_for_decorator
                
                if not current_user.is_authenticated:
                    flash('Please log in to access this page.', 'warning')
                    return redirect(url_for('auth.login'))
                
                # Testing bypass
                if current_user.user_id == '7777777777':
                    # CRITICAL FIX: Set g.branch_context even for testing bypass
                    if not hasattr(g, 'branch_context') or g.branch_context is None:
                        g.branch_context = {
                            'method': 'testing_bypass',
                            'accessible_branches': [],
                            'assigned_branch_id': None,
                            'can_cross_branch': True,
                            'is_multi_branch_user': False,
                            'branch_filter_required': False,
                            'is_cross_branch': True
                        }
                    return f(*args, **kwargs)
                
                # Check cross-branch permission
                if not has_cross_branch_permission(current_user, module_name, action):
                    flash(f'You do not have permission for cross-branch {action} on {module_name}', 'danger')
                    return redirect(url_for('auth_views.dashboard'))
                
                # Set cross-branch context
                # CRITICAL FIX: Ensure g.branch_context is never None
                branch_context = get_branch_context_for_decorator(
                    current_user.user_id, current_user.hospital_id, 
                    'all', module_name, action
                )
                g.branch_context = branch_context if branch_context else {}
                g.branch_context['is_cross_branch'] = True
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Cross-branch permission check error: {str(e)}")
                flash('Permission check failed', 'error')
                return redirect(url_for('auth_views.dashboard'))
                
        return decorated_function
    return decorator