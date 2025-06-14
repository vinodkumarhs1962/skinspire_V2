# app/services/permission_service.py
# Enhanced Permission Service with Branch-Level Access Control
# Implementation Document Compliant - Zero Disruption Approach

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.services.database_service import get_db_session
from app.models.config import RoleModuleBranchAccess, ModuleMaster, RoleMaster, UserRoleMapping
from app.models.master import Branch, Staff
from flask import current_app

logger = logging.getLogger(__name__)

# =====================================================================
# CORE PERMISSION FUNCTIONS (Implementation Document Section 7)
# =====================================================================

def has_permission(user, module_name: str, permission_type: str) -> bool:
    """
    BACKWARD COMPATIBLE permission checking
    Maintains existing testing bypass while adding branch awareness
    Implementation Document: Zero Disruption Approach
    """
    
    # PRESERVE EXISTING BYPASS for testing (Implementation Document requirement)
    user_id = user.user_id if hasattr(user, 'user_id') else user
    if user_id == '7777777777':
        logger.info(f"TESTING BYPASS: User {user_id} granted access to {module_name}.{permission_type}")
        return True
    
    # Check if branch validation is enabled for this module
    if is_branch_role_enabled_for_module(module_name):
        # Use new branch-aware permission system
        try:
            return has_branch_permission(user, module_name, permission_type)
        except Exception as e:
            logger.warning(f"Branch permission check failed, falling back to legacy: {str(e)}")
            return has_legacy_permission(user, module_name, permission_type)
    else:
        # Use legacy permission system
        return has_legacy_permission(user, module_name, permission_type)

def determine_target_branch(user_id: str, hospital_id: str, explicit_branch_id: str = None) -> str:
    """
    Implementation Document compliant branch context determination
    Priority: Explicit → User's Assigned → Main Branch
    """
    
    # Priority 1: Explicitly specified branch
    if explicit_branch_id:
        return explicit_branch_id
    
    # Priority 2: User's assigned branch (from Staff/Patient record)
    user_assigned_branch = get_user_assigned_branch_id(user_id, hospital_id)
    if user_assigned_branch:
        logger.debug(f"Using user's assigned branch {user_assigned_branch} for user {user_id}")
        return user_assigned_branch
    
    # Priority 3: Hospital's main/default branch  
    main_branch = get_default_branch_id(hospital_id)
    if main_branch:
        logger.debug(f"Using hospital's main branch {main_branch} for user {user_id}")
        return main_branch
    
    # Priority 4: Any branch in hospital (edge case)
    with get_db_session(read_only=True) as session:
        any_branch = session.query(Branch).filter_by(
            hospital_id=hospital_id,
            is_active=True
        ).first()
        
        if any_branch:
            logger.warning(f"Using fallback branch {any_branch.branch_id} for user {user_id}")
            return str(any_branch.branch_id)
    
    logger.error(f"No branch found for user {user_id} in hospital {hospital_id}")
    return None

def has_branch_permission(user, module_name: str, permission_type: str, branch_id: str = None) -> bool:
    """
    NEW: Branch-aware permission checking using role_module_branch_access table
    Implementation Document Section 7: Enhanced Permission Service
    """
    try:
        user_id = user.user_id if hasattr(user, 'user_id') else user
        hospital_id = user.hospital_id if hasattr(user, 'hospital_id') else None
        
        # CRITICAL: Testing bypass preserved (Implementation Document requirement)
        if user_id == '7777777777':
            logger.info(f"TESTING BYPASS: User {user_id} granted branch access to {module_name}.{permission_type}")
            return True
        
        # ENHANCED: Determine target branch using Implementation Document logic
        target_branch_id = determine_target_branch(user_id, hospital_id, branch_id)

        if not hospital_id:
            logger.error(f"No hospital_id found for user {user_id}")
            return False
        
        # Determine target branch - Implementation Document branch context logic
        target_branch_id = branch_id or get_user_assigned_branch_id(user_id, hospital_id)
        
        with get_db_session(read_only=True) as session:
            # Get module ID
            module = session.query(ModuleMaster).filter_by(
                module_name=module_name,
                hospital_id=hospital_id,
                is_active=True
            ).first()
            
            if not module:
                # Try global module (hospital_id is null)
                module = session.query(ModuleMaster).filter_by(
                    module_name=module_name,
                    hospital_id=None,
                    is_active=True
                ).first()
            
            if not module:
                logger.warning(f"Module {module_name} not found for hospital {hospital_id}")
                return False
            
            # Get user's active roles
            role_mappings = session.query(UserRoleMapping).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            if not role_mappings:
                logger.warning(f"No active roles found for user {user_id}")
                return False
            
            role_ids = [mapping.role_id for mapping in role_mappings]
            
            # Check branch-specific permissions
            permissions = session.query(RoleModuleBranchAccess).filter(
                RoleModuleBranchAccess.role_id.in_(role_ids),
                RoleModuleBranchAccess.module_id == module.module_id,
                RoleModuleBranchAccess.hospital_id == hospital_id
            ).all()
            
            for permission in permissions:
                # Check for specific branch access
                if permission.branch_id and target_branch_id and str(permission.branch_id) == str(target_branch_id):
                    if getattr(permission, f"can_{permission_type}", False):
                        logger.debug(f"User {user_id} granted {permission_type} access to {module_name} in branch {target_branch_id}")
                        return True
                
                # Check for all-branch access (branch_id = NULL)
                elif permission.branch_id is None:
                    if getattr(permission, f"can_{permission_type}", False):
                        logger.debug(f"User {user_id} granted all-branch {permission_type} access to {module_name}")
                        return True
                    
                    # Check cross-branch permission for view/export
                    if permission_type in ['view', 'export']:
                        cross_branch_attr = f"can_{permission_type}_cross_branch"
                        if getattr(permission, cross_branch_attr, False):
                            logger.debug(f"User {user_id} granted cross-branch {permission_type} access to {module_name}")
                            return True
            
            logger.debug(f"User {user_id} denied {permission_type} access to {module_name} in branch {target_branch_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking branch permission: {str(e)}")
        # Fallback to legacy permission system
        return has_legacy_permission(user, module_name, permission_type)

def has_legacy_permission(user, module_name: str, permission_type: str) -> bool:
    """
    Legacy permission checking using existing role_module_access table
    Preserved for backward compatibility
    """
    try:
        # Import here to avoid circular imports
        from app.models.config import RoleModuleAccess
        
        user_id = user.user_id if hasattr(user, 'user_id') else user
        hospital_id = user.hospital_id if hasattr(user, 'hospital_id') else None
        
        with get_db_session(read_only=True) as session:
            # Get module
            module = session.query(ModuleMaster).filter_by(
                module_name=module_name
            ).first()
            
            if not module:
                return False
            
            # Get user's roles
            role_mappings = session.query(UserRoleMapping).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            role_ids = [mapping.role_id for mapping in role_mappings]
            
            # Check legacy permissions
            permissions = session.query(RoleModuleAccess).filter(
                RoleModuleAccess.role_id.in_(role_ids),
                RoleModuleAccess.module_id == module.module_id
            ).all()
            
            for permission in permissions:
                if getattr(permission, f"can_{permission_type}", False):
                    return True
            
            return False
            
    except Exception as e:
        logger.error(f"Error checking legacy permission: {str(e)}")
        return False

# =====================================================================
# BRANCH ACCESS FUNCTIONS (Implementation Document Section 7)
# =====================================================================

def get_user_accessible_branches(user_id: str, hospital_id: str) -> List[Dict[str, Any]]:
    """
    Get list of branches user can access based on role_module_branch_access
    Implementation Document: Service Layer Support for Branch Context
    """
    try:
        with get_db_session(read_only=True) as session:
            # Get user's active roles
            role_mappings = session.query(UserRoleMapping).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            if not role_mappings:
                return []
            
            role_ids = [mapping.role_id for mapping in role_mappings]
            
            # Get all branch permissions for user's roles
            branch_permissions = session.query(RoleModuleBranchAccess).filter(
                RoleModuleBranchAccess.role_id.in_(role_ids),
                RoleModuleBranchAccess.hospital_id == hospital_id
            ).all()
            
            accessible_branch_ids = set()
            has_all_branch_access = False
            
            for permission in branch_permissions:
                if permission.branch_id is None:
                    has_all_branch_access = True
                    break
                else:
                    accessible_branch_ids.add(permission.branch_id)
            
            # Get branch details
            if has_all_branch_access:
                branches = session.query(Branch).filter_by(
                    hospital_id=hospital_id,
                    is_active=True
                ).order_by(Branch.name).all()
            else:
                branches = session.query(Branch).filter(
                    Branch.branch_id.in_(accessible_branch_ids),
                    Branch.is_active == True
                ).order_by(Branch.name).all()
            
            default_branch_id = get_default_branch_id(hospital_id)
            user_assigned_branch_id = get_user_assigned_branch_id(user_id, hospital_id)
            
            result = []
            for branch in branches:
                result.append({
                    'branch_id': str(branch.branch_id),
                    'name': branch.name,
                    'is_default': str(branch.branch_id) == default_branch_id,
                    'is_user_branch': str(branch.branch_id) == user_assigned_branch_id,
                    'has_all_access': has_all_branch_access
                })
            
            return result
            
    except Exception as e:
        logger.error(f"Error getting accessible branches: {str(e)}")
        return []

def get_user_assigned_branch_id(user_id: str, hospital_id: str) -> Optional[str]:
    """
    Get user's assigned branch ID from staff record
    Implementation Document: User Branch Context
    """
    try:
        with get_db_session(read_only=True) as session:
            # Get user record
            from app.models.transaction import User
            user = session.query(User).filter_by(user_id=user_id).first()
            
            if not user or user.entity_type != 'staff':
                return None
            
            # Get staff record
            staff = session.query(Staff).filter_by(
                staff_id=user.entity_id,
                hospital_id=hospital_id,
                is_active=True
            ).first()
            
            return str(staff.branch_id) if staff and staff.branch_id else None
            
    except Exception as e:
        logger.error(f"Error getting user assigned branch: {str(e)}")
        return None

def get_default_branch_id(hospital_id: str) -> Optional[str]:
    """
    Get default branch ID for hospital (first branch with 'main' in name, or first created)
    """
    try:
        with get_db_session(read_only=True) as session:
            # Look for branch with 'main' in name first
            branch = session.query(Branch).filter_by(
                hospital_id=hospital_id,
                is_active=True
            ).filter(Branch.name.ilike('%main%')).order_by(Branch.created_at).first()
            
            # If no main branch, get first created branch
            if not branch:
                branch = session.query(Branch).filter_by(
                    hospital_id=hospital_id,
                    is_active=True
                ).order_by(Branch.created_at).first()
            
            return str(branch.branch_id) if branch else None
            
    except Exception as e:
        logger.error(f"Error getting default branch: {str(e)}")
        return None

# =====================================================================
# CROSS-BRANCH PERMISSION FUNCTIONS (Implementation Document Section 7)
# =====================================================================

def has_cross_branch_permission(user, module_name: str, action: str = 'view') -> bool:
    """
    Check if user has cross-branch permission (for CEO/CFO roles)
    Implementation Document: Executive Cross-Branch Access
    """
    try:
        user_id = user.user_id if hasattr(user, 'user_id') else user
        hospital_id = user.hospital_id if hasattr(user, 'hospital_id') else None
        
        # Testing bypass
        if user_id == '7777777777':
            return True
        
        with get_db_session(read_only=True) as session:
            # Get module
            module = session.query(ModuleMaster).filter_by(
                module_name=module_name,
                hospital_id=hospital_id,
                is_active=True
            ).first()
            
            if not module:
                module = session.query(ModuleMaster).filter_by(
                    module_name=module_name,
                    hospital_id=None,
                    is_active=True
                ).first()
            
            if not module:
                return False
            
            # Get user's roles
            role_mappings = session.query(UserRoleMapping).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            role_ids = [mapping.role_id for mapping in role_mappings]
            
            # Check for cross-branch permissions
            permissions = session.query(RoleModuleBranchAccess).filter(
                RoleModuleBranchAccess.role_id.in_(role_ids),
                RoleModuleBranchAccess.module_id == module.module_id,
                RoleModuleBranchAccess.hospital_id == hospital_id,
                RoleModuleBranchAccess.branch_id.is_(None)  # NULL = all branches
            ).all()
            
            for permission in permissions:
                cross_branch_attr = f"can_{action}_cross_branch"
                if getattr(permission, cross_branch_attr, False):
                    return True
            
            return False
            
    except Exception as e:
        logger.error(f"Error checking cross-branch permission: {str(e)}")
        return False

# =====================================================================
# FEATURE FLAG FUNCTIONS (Implementation Document: Gradual Rollout)
# =====================================================================

def is_branch_role_enabled_for_module(module_name: str) -> bool:
    """
    Check if branch role validation is enabled for specific module
    Implementation Document: Feature Flag Configuration
    """
    try:
        # Global flag overrides all
        if current_app.config.get('ENABLE_BRANCH_ROLE_VALIDATION', False):
            return True
        
        # Module-specific flags
        module_flags = {
            'supplier': current_app.config.get('SUPPLIER_BRANCH_ROLES', False),
            'billing': current_app.config.get('BILLING_BRANCH_ROLES', False),
            'patient': current_app.config.get('PATIENT_BRANCH_ROLES', False),
            'inventory': current_app.config.get('INVENTORY_BRANCH_ROLES', False),
        }
        
        return module_flags.get(module_name, False)
        
    except Exception as e:
        logger.error(f"Error checking feature flag for {module_name}: {str(e)}")
        return False

# =====================================================================
# ROLE CONFIGURATION FUNCTIONS (Implementation Document Section 8)
# =====================================================================

def configure_clinic_roles(hospital_id: str) -> bool:
    """
    Configure standard roles for mid-size clinic
    Implementation Document: Role Configuration Examples
    """
    try:
        with get_db_session() as session:
            # Standard clinic role configurations from Implementation Document
            clinic_roles = {
                'clinic_owner': {
                    'branch_access': 'all',
                    'permissions': ['view', 'add', 'edit', 'delete', 'export'],
                    'modules': 'all',
                    'cross_branch': True
                },
                'operations_manager': {
                    'branch_access': 'all',
                    'permissions': ['view', 'add', 'edit', 'export'],
                    'modules': ['supplier', 'inventory', 'billing', 'reports'],
                    'cross_branch': False
                },
                'finance_head': {
                    'branch_access': 'reporting',
                    'permissions': ['view', 'export'],
                    'modules': ['billing', 'supplier', 'reports'],
                    'cross_branch': True
                },
                'branch_manager': {
                    'branch_access': 'specific',
                    'permissions': ['view', 'add', 'edit', 'delete'],
                    'modules': 'all',
                    'cross_branch_view_only': True
                },
                'staff': {
                    'branch_access': 'specific',
                    'permissions': ['view', 'add', 'edit'],
                    'modules': ['patient', 'appointment', 'billing']
                }
            }
            
            # Create/update roles
            for role_name, config in clinic_roles.items():
                create_or_update_clinic_role(session, hospital_id, role_name, config)
            
            session.commit()
            logger.info(f"Configured clinic roles for hospital {hospital_id}")
            return True
            
    except Exception as e:
        logger.error(f"Error configuring clinic roles: {str(e)}")
        return False

def create_or_update_clinic_role(session: Session, hospital_id: str, role_name: str, config: dict):
    """
    Create or update a specific clinic role with branch permissions
    Implementation Document: Role Configuration Helper
    """
    try:
        # Get or create role
        role = session.query(RoleMaster).filter_by(
            role_name=role_name,
            hospital_id=hospital_id
        ).first()
        
        if not role:
            role = RoleMaster(
                role_name=role_name,
                hospital_id=hospital_id,
                description=f"Auto-configured {role_name} role",
                is_active=True
            )
            session.add(role)
            session.flush()
        
        # Get all modules or specific modules
        if config['modules'] == 'all':
            modules = session.query(ModuleMaster).filter(
                or_(ModuleMaster.hospital_id == hospital_id, ModuleMaster.hospital_id.is_(None))
            ).all()
        else:
            modules = session.query(ModuleMaster).filter(
                ModuleMaster.module_name.in_(config['modules']),
                or_(ModuleMaster.hospital_id == hospital_id, ModuleMaster.hospital_id.is_(None))
            ).all()
        
        # Create branch permissions for each module
        for module in modules:
            # Check if permission already exists
            existing = session.query(RoleModuleBranchAccess).filter_by(
                role_id=role.role_id,
                module_id=module.module_id,
                hospital_id=hospital_id,
                branch_id=None if config['branch_access'] in ['all', 'reporting'] else 'specific'
            ).first()
            
            if not existing:
                permission_data = {
                    'hospital_id': hospital_id,
                    'role_id': role.role_id,
                    'module_id': module.module_id,
                    'branch_id': None if config['branch_access'] in ['all', 'reporting'] else None,
                    'branch_access_type': config['branch_access']
                }
                
                # Set standard permissions
                for perm_type in config['permissions']:
                    permission_data[f'can_{perm_type}'] = True
                
                # Set cross-branch permissions if specified
                if config.get('cross_branch', False):
                    permission_data['can_view_cross_branch'] = True
                    permission_data['can_export_cross_branch'] = True
                
                permission = RoleModuleBranchAccess(**permission_data)
                session.add(permission)
        
        logger.debug(f"Created/updated role {role_name} for hospital {hospital_id}")
        
    except Exception as e:
        logger.error(f"Error creating role {role_name}: {str(e)}")
        raise

# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def get_user_branch_context_for_module(user, module_name: str) -> Dict[str, Any]:
    """
    Get complete branch context for a user and specific module
    Used by decorators and view functions
    """
    try:
        user_id = user.user_id if hasattr(user, 'user_id') else user
        hospital_id = user.hospital_id if hasattr(user, 'hospital_id') else None
        
        if not hospital_id:
            return _empty_branch_context()
        
        accessible_branches = get_user_accessible_branches(user_id, hospital_id)
        assigned_branch_id = get_user_assigned_branch_id(user_id, hospital_id)
        
        # Filter branches where user has access to this module
        module_accessible_branches = []
        for branch in accessible_branches:
            if has_branch_permission(user, module_name, 'view', branch['branch_id']):
                module_accessible_branches.append(branch)
        
        return {
            'assigned_branch_id': assigned_branch_id,
            'accessible_branches': module_accessible_branches,
            'is_multi_branch': len(module_accessible_branches) > 1,
            'can_access_all_branches': any(b.get('has_all_access', False) for b in module_accessible_branches),
            'can_cross_branch_report': has_cross_branch_permission(user, module_name, 'view')
        }
        
    except Exception as e:
        logger.error(f"Error getting branch context: {str(e)}")
        return _empty_branch_context()

def _empty_branch_context() -> Dict[str, Any]:
    """Return empty branch context for error cases"""
    return {
        'assigned_branch_id': None,
        'accessible_branches': [],
        'is_multi_branch': False,
        'can_access_all_branches': False,
        'can_cross_branch_report': False
    }

# =====================================================================
# MIGRATION UTILITIES (Implementation Document Migration Support)
# =====================================================================

def migrate_legacy_permissions_to_branch_aware(hospital_id: str) -> int:
    """
    Migrate existing role_module_access permissions to branch-aware format
    Implementation Document: Migration Utilities
    """
    try:
        from app.models.config import RoleModuleAccess
        
        with get_db_session() as session:
            # Get default branch for hospital
            default_branch_id = get_default_branch_id(hospital_id)
            
            # Get all existing role-module permissions for this hospital
            legacy_permissions = session.query(RoleModuleAccess).join(RoleMaster).filter(
                RoleMaster.hospital_id == hospital_id
            ).all()
            
            migrated_count = 0
            for legacy_perm in legacy_permissions:
                # Check if already migrated
                existing = session.query(RoleModuleBranchAccess).filter_by(
                    role_id=legacy_perm.role_id,
                    module_id=legacy_perm.module_id,
                    hospital_id=hospital_id
                ).first()
                
                if not existing:
                    # Get role to determine branch access type
                    role = session.query(RoleMaster).filter_by(role_id=legacy_perm.role_id).first()
                    
                    # Determine branch access based on role name
                    is_admin_role = any(keyword in role.role_name.lower() 
                                      for keyword in ['admin', 'owner', 'director', 'ceo', 'cfo'])
                    
                    # Create new branch-aware permission
                    new_perm = RoleModuleBranchAccess(
                        hospital_id=hospital_id,
                        role_id=legacy_perm.role_id,
                        module_id=legacy_perm.module_id,
                        branch_id=None if is_admin_role else default_branch_id,
                        branch_access_type='all' if is_admin_role else 'specific',
                        can_view=legacy_perm.can_view,
                        can_add=legacy_perm.can_add,
                        can_edit=legacy_perm.can_edit,
                        can_delete=legacy_perm.can_delete,
                        can_export=legacy_perm.can_export,
                        can_view_cross_branch=legacy_perm.can_view if is_admin_role else False,
                        can_export_cross_branch=legacy_perm.can_export if is_admin_role else False
                    )
                    session.add(new_perm)
                    migrated_count += 1
            
            session.commit()
            logger.info(f"Migrated {migrated_count} permissions for hospital {hospital_id}")
            return migrated_count
            
    except Exception as e:
        logger.error(f"Error migrating permissions: {str(e)}")
        raise

# =====================================================================
# TESTING AND VALIDATION
# =====================================================================

def validate_permission_system(user_id: str, hospital_id: str) -> Dict[str, Any]:
    """
    Comprehensive validation of permission system for a user
    Used for testing and debugging
    """
    validation_results = {
        'user_id': user_id,
        'hospital_id': hospital_id,
        'testing_bypass': user_id == '7777777777',
        'has_roles': False,
        'accessible_branches': [],
        'branch_permissions': {},
        'legacy_permissions': {},
        'errors': []
    }
    
    try:
        # Check if user has roles
        with get_db_session(read_only=True) as session:
            role_mappings = session.query(UserRoleMapping).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            validation_results['has_roles'] = len(role_mappings) > 0
            validation_results['role_count'] = len(role_mappings)
            
            # Get accessible branches
            validation_results['accessible_branches'] = get_user_accessible_branches(user_id, hospital_id)
            
            # Test permissions for common modules
            test_modules = ['supplier', 'billing', 'patient', 'inventory']
            for module in test_modules:
                if is_branch_role_enabled_for_module(module):
                    validation_results['branch_permissions'][module] = {
                        'view': has_branch_permission({'user_id': user_id, 'hospital_id': hospital_id}, module, 'view'),
                        'add': has_branch_permission({'user_id': user_id, 'hospital_id': hospital_id}, module, 'add'),
                        'edit': has_branch_permission({'user_id': user_id, 'hospital_id': hospital_id}, module, 'edit'),
                        'cross_branch': has_cross_branch_permission({'user_id': user_id, 'hospital_id': hospital_id}, module)
                    }
                else:
                    validation_results['legacy_permissions'][module] = {
                        'view': has_legacy_permission({'user_id': user_id, 'hospital_id': hospital_id}, module, 'view'),
                        'add': has_legacy_permission({'user_id': user_id, 'hospital_id': hospital_id}, module, 'add'),
                        'edit': has_legacy_permission({'user_id': user_id, 'hospital_id': hospital_id}, module, 'edit')
                    }
        
    except Exception as e:
        validation_results['errors'].append(str(e))
        logger.error(f"Error validating permission system: {str(e)}")
    
    return validation_results

def get_user_permissions(user_id: str, hospital_id: str, module_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get comprehensive permissions for a user
    MINIMAL IMPLEMENTATION: Uses existing functions to avoid duplication
    
    Args:
        user_id: User ID
        hospital_id: Hospital UUID
        module_name: Optional specific module name to filter permissions
        
    Returns:
        Dictionary with user permissions and context
    """
    try:
        # Testing bypass (reuse existing pattern)
        if user_id == '7777777777':
            return {
                'user_id': user_id,
                'hospital_id': hospital_id,
                'is_testing_user': True,
                'has_all_permissions': True,
                'accessible_branches': [],
                'assigned_branch_id': None,
                'permissions': {'all': True},
                'modules': ['all']
            }
        
        # Use existing functions
        accessible_branches = get_user_accessible_branches(user_id, hospital_id)
        assigned_branch_id = get_user_assigned_branch_id(user_id, hospital_id)
        
        # Create user object for existing has_permission function
        user_obj = {'user_id': user_id, 'hospital_id': hospital_id}
        
        # Get permissions using existing has_permission function
        permissions = {}
        modules = []
        
        # Common modules to check
        common_modules = ['supplier', 'billing', 'patient', 'inventory', 'admin'] if not module_name else [module_name]
        
        for mod in common_modules:
            # Use existing has_permission function
            has_view = has_permission(user_obj, mod, 'view')
            if has_view:
                modules.append(mod)
                permissions[mod] = {
                    'view': has_view,
                    'add': has_permission(user_obj, mod, 'add'),
                    'edit': has_permission(user_obj, mod, 'edit'),
                    'delete': has_permission(user_obj, mod, 'delete'),
                    'export': has_permission(user_obj, mod, 'export')
                }
        
        return {
            'user_id': user_id,
            'hospital_id': hospital_id,
            'has_permissions': len(permissions) > 0,
            'accessible_branches': accessible_branches,
            'assigned_branch_id': assigned_branch_id,
            'permissions': permissions,
            'modules': modules,
            'is_multi_branch_user': len(accessible_branches) > 1
        }
        
    except Exception as e:
        logger.error(f"Error getting user permissions: {str(e)}")
        return _empty_branch_context()  # Use existing function

def get_user_module_permissions(user_id: str, hospital_id: str, module_name: str) -> Dict[str, bool]:
    """
    Get specific module permissions for a user
    MINIMAL IMPLEMENTATION: Wrapper around existing has_permission function
    """
    try:
        # Testing bypass (reuse existing pattern)
        if user_id == '7777777777':
            return {
                'view': True,
                'add': True,
                'edit': True,
                'delete': True,
                'export': True
            }
        
        # Use existing has_permission function
        user_obj = {'user_id': user_id, 'hospital_id': hospital_id}
        
        return {
            'view': has_permission(user_obj, module_name, 'view'),
            'add': has_permission(user_obj, module_name, 'add'),
            'edit': has_permission(user_obj, module_name, 'edit'),
            'delete': has_permission(user_obj, module_name, 'delete'),
            'export': has_permission(user_obj, module_name, 'export')
        }
        
    except Exception as e:
        logger.error(f"Error getting module permissions for {module_name}: {str(e)}")
        return {
            'view': False,
            'add': False,
            'edit': False,
            'delete': False,
            'export': False
        }

def check_user_module_access(user_id: str, hospital_id: str, module_name: str, permission_type: str = 'view') -> bool:
    """
    Quick check if user has specific permission for a module
    MINIMAL IMPLEMENTATION: Direct wrapper around existing has_permission function
    """
    try:
        # Testing bypass (reuse existing pattern)
        if user_id == '7777777777':
            return True
            
        # Use existing has_permission function directly
        user_obj = {'user_id': user_id, 'hospital_id': hospital_id}
        return has_permission(user_obj, module_name, permission_type)
        
    except Exception as e:
        logger.error(f"Error checking module access: {str(e)}")
        return False
    
# =====================================================================
# CORRECTED CLEAN IMPLEMENTATION: Fixed Undefined References
# =====================================================================

# =====================================================================
# 1. ENHANCE PERMISSION SERVICE (app/services/permission_service.py)
# ADD THESE FUNCTIONS - Fixed all undefined references
# =====================================================================

def get_user_branch_context(user_id, hospital_id, module=None):
    """
    Generic function to get user's branch context for any module
    Used by ALL business services
    """
    try:
        # Testing bypass
        if user_id == '7777777777':
            return {
                'accessible_branches': [],
                'assigned_branch_id': None,
                'can_cross_branch': True,
                'is_multi_branch_user': True,
                'branch_filter_required': False
            }
        
        accessible_branches = get_user_accessible_branches(user_id, hospital_id)
        assigned_branch_id = get_user_assigned_branch_id(user_id, hospital_id)
        
        # FIXED: Create user object for permission checking
        user_obj = {'user_id': user_id, 'hospital_id': hospital_id}
        can_cross_branch = False
        if module:
            try:
                can_cross_branch = has_cross_branch_permission(user_obj, module, 'view')
            except Exception as e:
                logger.warning(f"Cross-branch permission check failed: {str(e)}")
                can_cross_branch = False
        
        return {
            'accessible_branches': accessible_branches,
            'assigned_branch_id': assigned_branch_id,
            'can_cross_branch': can_cross_branch,
            'is_multi_branch_user': len(accessible_branches) > 1,
            'branch_filter_required': not can_cross_branch and len(accessible_branches) > 0
        }
        
    except Exception as e:
        logger.error(f"Error getting user branch context: {str(e)}")
        return {
            'accessible_branches': [],
            'assigned_branch_id': None,
            'can_cross_branch': False,
            'is_multi_branch_user': False,
            'branch_filter_required': False
        }

def apply_branch_filter_to_query(query, user_id, hospital_id, module):
    """
    Generic function to apply branch filtering to any SQLAlchemy query
    Works for suppliers, patients, invoices, etc.
    FIXED: Proper query filtering logic
    """
    try:
        # Get user's branch context
        context = get_user_branch_context(user_id, hospital_id, module)
        
        # No filtering needed if user has cross-branch access or bypass
        if not context['branch_filter_required']:
            return query
        
        # Apply branch filtering
        accessible_branch_ids = [b['branch_id'] for b in context['accessible_branches']]
        if accessible_branch_ids:
            # FIXED: Use proper SQLAlchemy filtering
            # Get the model class from the query
            model_class = query.column_descriptions[0]['type']
            if hasattr(model_class, 'branch_id'):
                return query.filter(model_class.branch_id.in_(accessible_branch_ids))
        
        # If no accessible branches, return empty result
        return query.filter(False)
        
    except Exception as e:
        logger.warning(f"Branch filtering failed, proceeding without filter: {str(e)}")
        return query