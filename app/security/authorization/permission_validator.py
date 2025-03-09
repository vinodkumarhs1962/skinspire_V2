# app/security/authorization/permission_validator.py

from typing import Optional, List, Dict, Any
from app.models import User, UserRoleMapping, RoleMaster, RoleModuleAccess, ModuleMaster
from sqlalchemy.orm import joinedload
from app.database import get_db

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
    
    # Get active status if available via user_id if it's an object
    # Do NOT try to access any lazy-loaded attributes on a potentially detached object
    
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

def get_user_permissions(user) -> Dict[str, List[str]]:
    """
    Get all permissions for a user across all modules
    
    Args:
        user: The user to get permissions for (User object or user_id)
        
    Returns:
        Dict[str, List[str]]: Dictionary mapping module names to lists of allowed actions
    """
    # Extract user_id if full user object provided
    user_id = user.user_id if hasattr(user, 'user_id') else user
    
    db_manager = get_db()
    with db_manager.get_session() as session:
        # First check if user is active
        user_record = session.query(User).filter_by(user_id=user_id).first()
        if not user_record or not user_record.is_active:
            return {}
            
        # Find all roles for this user
        role_mappings = session.query(UserRoleMapping).filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        if not role_mappings:
            return {}
        
        # Get role IDs
        role_ids = [mapping.role_id for mapping in role_mappings]
        
        # Get all permissions for these roles
        permissions = session.query(RoleModuleAccess, ModuleMaster).join(
            ModuleMaster, RoleModuleAccess.module_id == ModuleMaster.module_id
        ).filter(
            RoleModuleAccess.role_id.in_(role_ids)
        ).all()
        
        # Build permissions dictionary
        result = {}
        for perm, module in permissions:
            if module.module_name not in result:
                result[module.module_name] = []
            
            actions = []
            if perm.can_view:
                actions.append('view')
            if perm.can_add:
                actions.append('add')
            if perm.can_edit:
                actions.append('edit')
            if perm.can_delete:
                actions.append('delete')
            if perm.can_export:
                actions.append('export')
            
            # Add any new actions to the list
            for action in actions:
                if action not in result[module.module_name]:
                    result[module.module_name].append(action)
        
        return result