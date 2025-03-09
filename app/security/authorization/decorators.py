# app/security/authorization/decorators.py

from functools import wraps
from flask import jsonify, request
from .permission_validator import has_permission
from app.security.authentication.auth_manager import token_required

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