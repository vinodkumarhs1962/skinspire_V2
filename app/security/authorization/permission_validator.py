# app/security/authorization/permission_validator.py

from typing import Optional, List, Dict, Any
from app.models import User, UserRoleMapping, RoleMaster, RoleModuleAccess, ModuleMaster
from sqlalchemy.orm import joinedload
from app.services.database_service import get_db_session

from app.services.permission_service import (
    has_permission as service_has_permission,
    has_branch_permission as service_has_branch_permission,
    get_user_permissions as service_get_user_permissions
)

def has_permission(user, module_name: str, permission_type: str) -> bool:
    """Delegate to centralized permission service"""
    return service_has_permission(user, module_name, permission_type)

def has_branch_permission(user, module_name: str, permission_type: str, branch_id: str = None) -> bool:
    """Delegate to centralized permission service"""
    return service_has_branch_permission(user, module_name, permission_type, branch_id)

def get_user_permissions(user):
    """Delegate to centralized permission service"""
    return service_get_user_permissions(user)

def permission_required(module_name, permission_type):
    """
    Decorator to check if a user has permission to perform an action on a module
    
    Args:
        module_name: The name of the module to check access for
        permission_type: The action to check (view, add, edit, delete, export)
        
    Returns:
        Decorator function
    """
    from functools import wraps
    from flask import flash, redirect, url_for
    from flask_login import current_user
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if has_permission(current_user, module_name, permission_type):
                return f(*args, **kwargs)
            else:
                flash('You do not have permission to access this resource', 'error')
                return redirect(url_for('auth_views.dashboard'))
        return wrapped
    return decorator