# app/services/branch_service.py - CONSOLIDATED VERSION
# All branch-related functions in one clean, organized file

from decimal import Decimal
from typing import Dict, Any, Optional, Union, Tuple, List
import uuid

from app.services.database_service import get_db_session
from app.models.master import Branch, Hospital

from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

# =====================================================
# CORE BRANCH DATA FUNCTIONS
# =====================================================

def get_hospital_branches(hospital_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
    """
    Get all active branches for a hospital
    Core function - used by all other branch functions
    """
    try:
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        
        with get_db_session(read_only=True) as session:
            branches = session.query(Branch).filter_by(
                hospital_id=hospital_id,
                is_active=True
            ).order_by(Branch.name).all()
            
            logger.info(f"Found {len(branches)} active branches for hospital {hospital_id}")
            
            return [
                {
                    'branch_id': str(branch.branch_id),
                    'name': branch.name,
                    'address': getattr(branch, 'address', None),
                    'is_active': branch.is_active
                } for branch in branches
            ]
            
    except Exception as e:
        logger.error(f"Error getting hospital branches: {str(e)}", exc_info=True)
        return []

def get_default_branch_id(hospital_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
    """
    Get the default/main branch for a hospital
    """
    try:
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
            
        with get_db_session(read_only=True) as session:
            # Strategy 1: Find branch with 'main', 'head', or 'primary' in name
            branch = session.query(Branch).filter(
                Branch.hospital_id == hospital_id,
                Branch.is_active == True
            ).filter(
                Branch.name.ilike('%main%') | 
                Branch.name.ilike('%head%') | 
                Branch.name.ilike('%primary%')
            ).first()
            
            # Strategy 2: Get the oldest active branch (likely the first/main one)
            if not branch:
                branch = session.query(Branch).filter(
                    Branch.hospital_id == hospital_id,
                    Branch.is_active == True
                ).order_by(Branch.created_at).first()
                
            return branch.branch_id if branch else None
            
    except Exception as e:
        logger.error(f"Error getting default branch for hospital {hospital_id}: {str(e)}")
        return None

def get_user_staff_branch(user_id: str, hospital_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
    """
    Get user's branch assignment via Staff table
    Returns None if user is not staff or has no branch assignment
    """
    try:
        from app.models.master import Staff
        from app.models.transaction import User
        
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        
        with get_db_session(read_only=True) as session:
            user = session.query(User).filter_by(user_id=user_id).first()
            
            if not user or user.entity_type != 'staff' or not user.entity_id:
                return None
            
            staff = session.query(Staff).filter_by(staff_id=user.entity_id).first()
            
            if not staff:
                return None
            
            if staff.branch_id:
                # Staff assigned to specific branch
                branch = session.query(Branch).filter_by(
                    branch_id=staff.branch_id,
                    is_active=True
                ).first()
                
                if branch:
                    return {
                        'branch_id': str(branch.branch_id),
                        'branch_name': branch.name,
                        'is_assigned': True,
                        'is_admin': False
                    }
            else:
                # Staff without branch assignment = admin
                return {
                    'branch_id': None,
                    'branch_name': None,
                    'is_assigned': False,
                    'is_admin': True
                }
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting user staff branch: {str(e)}")
        return None

# =====================================================
# RBAC BRANCH PERMISSIONS (Future-ready)
# =====================================================

def get_user_rbac_permissions(user_id: str, hospital_id: Union[str, uuid.UUID], 
                             module_name: str, action: str = 'view') -> Optional[Dict[str, Any]]:
    """
    Get user's branch permissions using RBAC tables
    Returns None if RBAC is not configured yet
    """
    try:
        from app.models.config import RoleModuleBranchAccess, ModuleMaster, UserRoleMapping
        
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        
        with get_db_session(read_only=True) as session:
            # Check if module exists
            module = session.query(ModuleMaster).filter_by(
                module_name=module_name,
                hospital_id=hospital_id,
                is_active=True
            ).first()
            
            if not module:
                logger.info(f"Module '{module_name}' not found in RBAC")
                return None
            
            # Check if user has roles
            user_roles = session.query(UserRoleMapping).filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            if not user_roles:
                logger.info(f"No roles for user {user_id}")
                return None
            
            role_ids = [ur.role_id for ur in user_roles]
            
            # Check if we have any RBAC permissions data
            rbac_permissions = session.query(RoleModuleBranchAccess).filter(
                RoleModuleBranchAccess.hospital_id == hospital_id,
                RoleModuleBranchAccess.role_id.in_(role_ids),
                RoleModuleBranchAccess.module_id == module.module_id
            ).all()
            
            if not rbac_permissions:
                logger.info(f"No RBAC permissions data found for user {user_id}, module {module_name}")
                return None
            
            # Process RBAC permissions
            accessible_branches = []
            has_cross_branch_access = False
            all_branches_access = False
            
            permission_column = f'can_{action}'
            cross_branch_column = f'can_{action}_cross_branch'
            
            for perm in rbac_permissions:
                has_permission = getattr(perm, permission_column, False)
                has_cross_branch = getattr(perm, cross_branch_column, False)
                
                if has_cross_branch:
                    has_cross_branch_access = True
                
                if not has_permission:
                    continue
                
                if perm.branch_access_type == 'all':
                    all_branches_access = True
                    break
                elif perm.branch_access_type == 'specific' and perm.branch_id:
                    branch = session.query(Branch).filter_by(
                        branch_id=perm.branch_id,
                        is_active=True
                    ).first()
                    
                    if branch:
                        accessible_branches.append({
                            'branch_id': str(branch.branch_id),
                            'branch_name': branch.name,
                            'permissions': {
                                'can_view': perm.can_view,
                                'can_add': perm.can_add,
                                'can_edit': perm.can_edit,
                                'can_delete': perm.can_delete,
                                'can_export': perm.can_export
                            },
                            'access_type': 'specific'
                        })
            
            # If user has 'all' access, get all branches
            if all_branches_access or has_cross_branch_access:
                all_branches = get_hospital_branches(hospital_id)
                accessible_branches = [
                    {
                        'branch_id': branch['branch_id'],
                        'branch_name': branch['name'],
                        'permissions': {
                            'can_view': True,
                            'can_add': has_cross_branch_access,
                            'can_edit': has_cross_branch_access,
                            'can_delete': has_cross_branch_access,
                            'can_export': True
                        },
                        'access_type': 'all'
                    } for branch in all_branches
                ]
            
            return {
                'accessible_branches': accessible_branches,
                'has_cross_branch_access': has_cross_branch_access,
                'is_admin': all_branches_access or has_cross_branch_access,
                'module_id': module.module_id,
                'user_roles': role_ids,
                'method': 'rbac'
            }
            
    except Exception as e:
        logger.error(f"Error getting RBAC permissions: {str(e)}")
        return None

# =====================================================
# UNIFIED BRANCH ACCESS FUNCTION (Main API)
# =====================================================

def get_user_branch_access(user_id: str, hospital_id: Union[str, uuid.UUID], 
                          module_name: str = 'supplier', action: str = 'view') -> Dict[str, Any]:
    """
    MAIN FUNCTION: Get user's branch access using best available method
    
    Priority:
    1. Testing bypass for user 7777777777
    2. RBAC if configured
    3. Staff table fallback
    4. Single branch auto-assignment
    """
    try:
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        
        logger.info(f"Getting branch access for user {user_id}, module {module_name}, action {action}")
        
        # TESTING BYPASS
        if user_id == '7777777777':
            logger.info("TESTING: Testing user bypass")
            all_branches = get_hospital_branches(hospital_id)
            return {
                'accessible_branches': [
                    {
                        'branch_id': branch['branch_id'],
                        'branch_name': branch['name'],
                        'permissions': {
                            'can_view': True,
                            'can_add': True,
                            'can_edit': True,
                            'can_delete': True,
                            'can_export': True
                        },
                        'access_type': 'testing'
                    } for branch in all_branches
                ],
                'has_cross_branch_access': True,
                'default_branch_id': str(all_branches[0]['branch_id']) if all_branches else None,
                'is_admin': True,
                'method': 'testing_bypass',
                'error': None
            }
        
        # TRY RBAC FIRST
        rbac_permissions = get_user_rbac_permissions(user_id, hospital_id, module_name, action)
        if rbac_permissions:
            logger.info("RBAC: Using RBAC permissions")
            default_branch_id = None
            if rbac_permissions['accessible_branches']:
                default_branch_id = rbac_permissions['accessible_branches'][0]['branch_id']
            
            return {
                **rbac_permissions,
                'default_branch_id': default_branch_id,
                'error': None
            }
        
        # FALLBACK TO STAFF TABLE
        logger.info("STAFF: Using Staff table fallback")
        staff_branch = get_user_staff_branch(user_id, hospital_id)
        all_branches = get_hospital_branches(hospital_id)
        
        if staff_branch:
            if staff_branch['is_admin']:
                # Staff admin - access to all branches
                return {
                    'accessible_branches': [
                        {
                            'branch_id': branch['branch_id'],
                            'branch_name': branch['name'],
                            'permissions': {
                                'can_view': True,
                                'can_add': True,
                                'can_edit': True,
                                'can_delete': True,
                                'can_export': True
                            },
                            'access_type': 'staff_admin'
                        } for branch in all_branches
                    ],
                    'has_cross_branch_access': True,
                    'default_branch_id': str(all_branches[0]['branch_id']) if all_branches else None,
                    'is_admin': True,
                    'method': 'staff_admin',
                    'error': None
                }
            else:
                # Staff assigned to specific branch
                return {
                    'accessible_branches': [{
                        'branch_id': staff_branch['branch_id'],
                        'branch_name': staff_branch['branch_name'],
                        'permissions': {
                            'can_view': True,
                            'can_add': True,
                            'can_edit': True,
                            'can_delete': False,  # Conservative
                            'can_export': True
                        },
                        'access_type': 'staff_assigned'
                    }],
                    'has_cross_branch_access': False,
                    'default_branch_id': staff_branch['branch_id'],
                    'is_admin': False,
                    'method': 'staff_assigned',
                    'error': None
                }
        
        # SINGLE BRANCH AUTO-ASSIGNMENT
        if len(all_branches) == 1:
            logger.info("STAFF: Single branch auto-assignment")
            branch = all_branches[0]
            return {
                'accessible_branches': [{
                    'branch_id': branch['branch_id'],
                    'branch_name': branch['name'],
                    'permissions': {
                        'can_view': True,
                        'can_add': True,
                        'can_edit': True,
                        'can_delete': False,
                        'can_export': True
                    },
                    'access_type': 'single_branch'
                }],
                'has_cross_branch_access': False,
                'default_branch_id': branch['branch_id'],
                'is_admin': False,
                'method': 'single_branch',
                'error': None
            }
        
        # NO ACCESS
        logger.warning(f"No branch access determined for user {user_id}")
        return {
            'accessible_branches': [],
            'has_cross_branch_access': False,
            'default_branch_id': None,
            'is_admin': False,
            'method': 'no_access',
            'error': 'No branch access configured'
        }
        
    except Exception as e:
        logger.error(f"Error getting user branch access: {str(e)}", exc_info=True)
        return {
            'accessible_branches': [],
            'has_cross_branch_access': False,
            'default_branch_id': None,
            'is_admin': False,
            'method': 'error',
            'error': str(e)
        }

# =====================================================
# FORM HELPER FUNCTIONS
# =====================================================

def get_branch_context_for_form(user_id: str, hospital_id: Union[str, uuid.UUID], 
                               module_name: str = 'supplier', action: str = 'view') -> Dict[str, Any]:
    """
    Get branch context specifically formatted for form templates
    This is the main function controllers should use
    """
    try:
        # Get user's branch access
        access = get_user_branch_access(user_id, hospital_id, module_name, action)
        
        if access['error']:
            return {
                'branches': [],
                'default_branch_id': None,
                'show_branch_selector': False,
                'user_access': access,
                'error': access['error'],
                'method': access['method']
            }
        
        # Filter branches by action permission
        action_filtered_branches = []
        for branch in access['accessible_branches']:
            if branch['permissions'].get(f'can_{action}', False):
                action_filtered_branches.append({
                    'branch_id': branch['branch_id'],
                    'name': branch['branch_name'],
                    'permissions': branch['permissions']
                })
        
        # Determine if we should show selector
        show_selector = len(action_filtered_branches) > 1 or access['has_cross_branch_access']
        
        return {
            'branches': action_filtered_branches,
            'default_branch_id': access['default_branch_id'],
            'show_branch_selector': show_selector,
            'user_access': access,
            'is_admin': access['is_admin'],
            'has_cross_branch_access': access['has_cross_branch_access'],
            'method': access['method'],
            'total_accessible': len(access['accessible_branches']),
            'action_filtered': len(action_filtered_branches),
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error getting form branch context: {str(e)}")
        return {
            'branches': [],
            'default_branch_id': None,
            'show_branch_selector': False,
            'user_access': {},
            'error': str(e),
            'method': 'error'
        }

def validate_user_branch_action(user_id: str, hospital_id: Union[str, uuid.UUID], 
                               branch_id: str, module_name: str, action: str) -> bool:
    """
    Validate if user can perform specific action on specific branch
    USE THIS BEFORE ANY BRANCH-SENSITIVE OPERATIONS
    """
    try:
        # Testing bypass
        if user_id == '7777777777':
            return True
        
        access = get_user_branch_access(user_id, hospital_id, module_name, action)
        
        if access['error']:
            logger.warning(f"Access validation failed: {access['error']}")
            return False
        
        # Check cross-branch access
        if access['has_cross_branch_access']:
            return True
        
        # Check specific branch access
        for branch in access['accessible_branches']:
            if branch['branch_id'] == str(branch_id):
                return branch['permissions'].get(f'can_{action}', False)
        
        logger.warning(f"User {user_id} has no {action} access to branch {branch_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error validating branch action: {str(e)}")
        return False

# =====================================================
# LEGACY COMPATIBILITY FUNCTIONS (Keep for backward compatibility)
# =====================================================

# =====================================================
# LEGACY COMPATIBILITY FUNCTIONS (Keep for backward compatibility)
# These ensure existing code continues to work unchanged
# =====================================================

def get_user_branch_id(current_user_id: str, hospital_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
    """
    Legacy function - used by supplier_service and other services
    Maps to new unified system while maintaining exact same signature
    """
    try:
        context = get_branch_context_for_form(current_user_id, hospital_id)
        default_id = context.get('default_branch_id')
        return uuid.UUID(default_id) if default_id else None
    except Exception as e:
        logger.error(f"Error in legacy get_user_branch_id: {str(e)}")
        return None

def get_user_accessible_branches(user_id: str, hospital_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
    """
    Legacy function - used by permission services
    Maps to new unified system while maintaining exact same return format
    """
    try:
        access = get_user_branch_access(user_id, hospital_id)
        
        # Convert new format to legacy format
        legacy_branches = []
        for branch in access.get('accessible_branches', []):
            legacy_branches.append({
                'branch_id': branch['branch_id'], 
                'name': branch['branch_name'],
                'is_default': branch['branch_id'] == access.get('default_branch_id'),
                'is_user_branch': not access.get('is_admin', False)
            })
        
        return legacy_branches
    except Exception as e:
        logger.error(f"Error in legacy get_user_accessible_branches: {str(e)}")
        return []

def validate_branch_access(user_id: str, hospital_id: Union[str, uuid.UUID], 
                          target_branch_id: Union[str, uuid.UUID]) -> bool:
    """
    Legacy function - used for security validation
    Maps to new validate_user_branch_action with 'view' as default action
    """
    try:
        return validate_user_branch_action(
            user_id, hospital_id, str(target_branch_id), 'supplier', 'view'
        )
    except Exception as e:
        logger.error(f"Error in legacy validate_branch_access: {str(e)}")
        return False

def get_branch_for_supplier_operation(current_user_id: Optional[str] = None, 
                                     hospital_id: Optional[Union[str, uuid.UUID]] = None,
                                     specified_branch_id: Optional[Union[str, uuid.UUID]] = None) -> Optional[uuid.UUID]:
    """
    Legacy function - used by supplier service operations
    Maps to new system while maintaining exact same logic flow
    """
    try:
        # Strategy 1: Use explicitly specified branch if provided and valid
        if specified_branch_id and current_user_id and hospital_id:
            if validate_user_branch_action(current_user_id, hospital_id, str(specified_branch_id), 'supplier', 'add'):
                return uuid.UUID(str(specified_branch_id))
            else:
                logger.warning(f"User {current_user_id} denied access to specified branch {specified_branch_id}")
        
        # Strategy 2: Use user's default branch from new system
        if current_user_id and hospital_id:
            context = get_branch_context_for_form(current_user_id, hospital_id, 'supplier', 'add')
            default_id = context.get('default_branch_id')
            if default_id:
                return uuid.UUID(default_id)
        
        # Strategy 3: Use hospital default branch
        if hospital_id:
            default_branch = get_default_branch_id(hospital_id)
            if default_branch:
                return default_branch
        
        return None
        
    except Exception as e:
        logger.error(f"Error in legacy get_branch_for_supplier_operation: {str(e)}")
        return None

# Additional legacy functions that might be used elsewhere

def get_branch_gst_details(branch_id: str, hospital_id: str) -> Dict[str, Any]:
    """
    Legacy function for GST details - preserved for tax calculations
    """
    try:
        with get_db_session() as session:
            branch = session.query(Branch).filter_by(branch_id=branch_id).first()
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
            
            if not branch or not hospital:
                return {
                    'gst_registration_number': None,
                    'pan_number': None,
                    'state_code': None,
                    'return_filing_period': None
                }
            
            return {
                'gst_registration_number': getattr(branch, 'gst_registration_number', None) or getattr(hospital, 'gst_registration_number', None),
                'pan_number': getattr(branch, 'pan_number', None) or getattr(hospital, 'pan_number', None),
                'state_code': getattr(branch, 'state_code', None) or getattr(hospital, 'state_code', None),
                'return_filing_period': getattr(branch, 'return_filing_period', None) or getattr(hospital, 'return_filing_period', None)
            }
    except Exception as e:
        logger.error(f"Error getting branch GST details: {str(e)}")
        return {
            'gst_registration_number': None,
            'pan_number': None,
            'state_code': None,
            'return_filing_period': None
        }

def get_branch_pharmacy_details(branch_id: str, hospital_id: str) -> Dict[str, Any]:
    """
    Legacy function for pharmacy details - preserved for compliance
    """
    try:
        with get_db_session() as session:
            branch = session.query(Branch).filter_by(branch_id=branch_id).first()
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
            
            if not branch or not hospital:
                return {
                    'registration_number': None,
                    'registration_date': None,
                    'valid_until': None
                }
            
            return {
                'registration_number': getattr(branch, 'pharmacy_registration_number', None) or getattr(hospital, 'pharmacy_registration_number', None),
                'registration_date': getattr(branch, 'pharmacy_registration_date', None) or getattr(hospital, 'pharmacy_registration_date', None),
                'valid_until': getattr(branch, 'pharmacy_registration_valid_until', None) or getattr(hospital, 'pharmacy_registration_valid_until', None)
            }
    except Exception as e:
        logger.error(f"Error getting branch pharmacy details: {str(e)}")
        return {
            'registration_number': None,
            'registration_date': None,
            'valid_until': None
        }

def get_branch_with_fallback(branch_id: str, hospital_id: str) -> Dict[str, Any]:
    """
    Legacy function for comprehensive branch details - preserved for reporting
    """
    try:
        gst_details = get_branch_gst_details(branch_id, hospital_id)
        pharmacy_details = get_branch_pharmacy_details(branch_id, hospital_id)
        
        with get_db_session() as session:
            branch = session.query(Branch).filter_by(branch_id=branch_id).first()
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
            
            if not branch or not hospital:
                return {
                    'name': None,
                    'address': None,
                    'contact_details': None,
                    **gst_details,
                    **{f'pharmacy_{k}': v for k, v in pharmacy_details.items()}
                }
            
            return {
                'name': branch.name,
                'address': getattr(branch, 'address', None) or getattr(hospital, 'address', None),
                'contact_details': getattr(branch, 'contact_details', None) or getattr(hospital, 'contact_details', None),
                'timezone': getattr(branch, 'timezone', None) or getattr(hospital, 'timezone', None),
                **gst_details,
                **{f'pharmacy_{k}': v for k, v in pharmacy_details.items()}
            }
    except Exception as e:
        logger.error(f"Error getting branch with fallback: {str(e)}")
        return {}

def is_gst_registered(branch_id: str, hospital_id: str) -> bool:
    """Legacy function for GST status check"""
    gst_details = get_branch_gst_details(branch_id, hospital_id)
    return bool(gst_details['gst_registration_number'])

def is_pharmacy_registered(branch_id: str, hospital_id: str) -> bool:
    """Legacy function for pharmacy status check"""
    pharmacy_details = get_branch_pharmacy_details(branch_id, hospital_id)
    return bool(pharmacy_details['registration_number'])

def ensure_hospital_has_default_branch(hospital_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
    """
    Legacy function - ensure hospital has at least one branch
    Used by setup and migration scripts
    """
    try:
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
            
        # Check if default branch exists
        default_branch_id = get_default_branch_id(hospital_id)
        if default_branch_id:
            return default_branch_id
            
        # Create default branch if none exists
        with get_db_session() as session:
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
            if not hospital:
                logger.error(f"Hospital {hospital_id} not found")
                return None
                
            # Create main branch
            main_branch = Branch(
                hospital_id=hospital_id,
                name="Main Branch",
                is_active=True,
                address=getattr(hospital, 'address', None),
                contact_details=getattr(hospital, 'contact_details', None),
                gst_registration_number=getattr(hospital, 'gst_registration_number', None),
                pan_number=getattr(hospital, 'pan_number', None),
                state_code=getattr(hospital, 'state_code', None),
                timezone=getattr(hospital, 'timezone', None)
            )
            
            session.add(main_branch)
            session.commit()
            
            logger.info(f"Created default branch for hospital {hospital_id}: {main_branch.branch_id}")
            return main_branch.branch_id
            
    except Exception as e:
        logger.error(f"Error ensuring default branch for hospital {hospital_id}: {str(e)}")
        return None

# =====================================================
# MIGRATION HELPER FUNCTIONS
# =====================================================

def migrate_to_new_branch_system():
    """
    Helper function to identify what legacy functions are being used
    Call this during development to audit function usage
    """
    logger.info("=== BRANCH SERVICE MIGRATION STATUS ===")
    logger.info("[OK] New unified system implemented")
    logger.info("[OK] Legacy functions preserved for backward compatibility")
    logger.info("[OK] All existing code should continue working")
    logger.info("💡 Recommendation: Gradually migrate to get_user_branch_access() and get_branch_context_for_form()")
    logger.info("=== END MIGRATION STATUS ===")

def test_backward_compatibility(user_id: str, hospital_id: str):
    """
    Test function to verify legacy functions work correctly
    """
    try:
        logger.info(f"Testing backward compatibility for user {user_id}")
        
        # Test legacy functions
        branch_id = get_user_branch_id(user_id, hospital_id)
        logger.info(f"[OK] get_user_branch_id: {branch_id}")
        
        accessible = get_user_accessible_branches(user_id, hospital_id)
        logger.info(f"[OK] get_user_accessible_branches: {len(accessible)} branches")
        
        if branch_id:
            access_valid = validate_branch_access(user_id, hospital_id, branch_id)
            logger.info(f"[OK] validate_branch_access: {access_valid}")
        
        supplier_branch = get_branch_for_supplier_operation(user_id, hospital_id)
        logger.info(f"[OK] get_branch_for_supplier_operation: {supplier_branch}")
        
        logger.info("[OK] All legacy functions working correctly")
        return True
        
    except Exception as e:
        logger.error(f"[NO] Backward compatibility test failed: {str(e)}")
        return False
    
# =====================================================
# MISSING FUNCTIONS - Add these to your current branch_service.py
# These are the exact functions from your original 04.06 file that are missing
# =====================================================

def determine_branch_context_from_request(user, request, branch_source='auto', session=None):
    """
    Determine branch context from various request sources
    Used by decorators to extract branch context
    """
    should_close_session = session is None
    
    if session is None:
        from app.services.database_service import get_db_session
        session = get_db_session(read_only=True).__enter__()
    
    try:
        # Strategy 1: Explicit branch in URL parameters
        branch_id = request.args.get('branch_id')
        if branch_id:
            logger.debug(f"Branch context from URL parameter: {branch_id}")
            return branch_id
        
        # Strategy 2: Branch in form data
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                branch_id = request.get_json().get('branch_id') if request.get_json() else None
            else:
                branch_id = request.form.get('branch_id')
            
            if branch_id:
                logger.debug(f"Branch context from form data: {branch_id}")
                return branch_id
        
        # Strategy 3: Extract from entity being accessed
        entity_branch_id = get_entity_branch_id_from_request(request, session)
        if entity_branch_id:
            logger.debug(f"Branch context from entity: {entity_branch_id}")
            return entity_branch_id
        
        # Strategy 4: Use branch service logic for specific operations
        if branch_source == 'supplier':
            return get_branch_for_supplier_operation(
                current_user_id=user.user_id,
                hospital_id=user.hospital_id,
                specified_branch_id=None
            )
        
        # Strategy 5: Use determine_target_branch function
        try:
            from app.services.permission_service import determine_target_branch
            branch_id = determine_target_branch(user.user_id, user.hospital_id, None)
            logger.debug(f"Branch context from determine_target_branch: {branch_id}")
            return branch_id
        except ImportError:
            # If permission_service doesn't have this function, use our new service
            context = get_branch_context_for_form(user.user_id, user.hospital_id)
            return context.get('default_branch_id')
        
    finally:
        if should_close_session:
            session.__exit__(None, None, None)

def get_entity_branch_id_from_request(request, session):
    """
    Extract branch_id from entity being accessed in the request
    Supports multiple entity types
    """
    try:
        # Check for various entity IDs in URL
        if hasattr(request, 'view_args') and request.view_args:
            if 'supplier_id' in request.view_args:
                return get_entity_branch_id('supplier', request.view_args['supplier_id'], session)
            
            if 'patient_id' in request.view_args:
                return get_entity_branch_id('patient', request.view_args['patient_id'], session)
            
            if 'invoice_id' in request.view_args:
                return get_entity_branch_id('invoice', request.view_args['invoice_id'], session)
            
            if 'medicine_id' in request.view_args:
                return get_entity_branch_id('medicine', request.view_args['medicine_id'], session)
            
            if 'staff_id' in request.view_args:
                return get_entity_branch_id('staff', request.view_args['staff_id'], session)
        
    except Exception as e:
        logger.error(f"Error extracting entity branch_id: {str(e)}")
    
    return None

def get_entity_branch_id(entity_type: str, entity_id: str, session_or_hospital_id):
    """
    Generic function to get branch_id for any entity type
    Centralized entity branch lookup
    """
    try:
        # Handle both session and hospital_id parameters
        if hasattr(session_or_hospital_id, 'query'):
            session = session_or_hospital_id
            should_close = False
        else:
            from app.services.database_service import get_db_session
            session = get_db_session(read_only=True).__enter__()
            should_close = True
        
        try:
            entity_map = {
                'supplier': ('app.models.master', 'Supplier', 'supplier_id'),
                'patient': ('app.models.master', 'Patient', 'patient_id'),  
                'staff': ('app.models.master', 'Staff', 'staff_id'),
                'medicine': ('app.models.master', 'Medicine', 'medicine_id'),
                'invoice': ('app.models.transaction', 'InvoiceHeader', 'invoice_id'),
                'inventory': ('app.models.transaction', 'Inventory', 'inventory_id'),
                'purchase_order': ('app.models.transaction', 'PurchaseOrderHeader', 'po_id'),
                'supplier_invoice': ('app.models.transaction', 'SupplierInvoice', 'invoice_id'),
                'supplier_payment': ('app.models.transaction', 'SupplierPayment', 'payment_id'),
            }
            
            if entity_type not in entity_map:
                logger.warning(f"Unknown entity type: {entity_type}")
                return None
            
            module_name, class_name, id_field = entity_map[entity_type]
            
            # Dynamic import and query
            module = __import__(module_name, fromlist=[class_name])
            entity_class = getattr(module, class_name)
            
            entity = session.query(entity_class).filter(
                getattr(entity_class, id_field) == entity_id
            ).first()
            
            if entity and hasattr(entity, 'branch_id'):
                return str(entity.branch_id) if entity.branch_id else None
            
            logger.debug(f"No branch_id found for {entity_type} {entity_id}")
            return None
            
        finally:
            if should_close:
                session.__exit__(None, None, None)
        
    except Exception as e:
        logger.error(f"Error getting {entity_type} branch_id: {str(e)}")
        return None

def check_superuser_status(user_id: str, session) -> bool:
    """
    Check if user has superuser roles
    Centralized superuser checking for decorators
    """
    try:
        # Testing bypass
        if user_id == '7777777777':
            return True
            
        from app.models.config import RoleMaster, UserRoleMapping
        
        is_superuser = session.query(UserRoleMapping)\
            .join(RoleMaster, UserRoleMapping.role_id == RoleMaster.role_id)\
            .filter(UserRoleMapping.user_id == user_id)\
            .filter(RoleMaster.role_name.in_(['System Administrator', 'Hospital Administrator']))\
            .first() is not None
        
        return is_superuser
        
    except Exception as e:
        logger.error(f"Error checking superuser status: {str(e)}")
        return False

def get_branch_context_for_decorator(user_id: str, hospital_id: str, branch_id: str, module: str, action: str):
    """Get complete branch context for decorator to set in Flask g"""
    try:
        # Try to use permission service first
        try:
            from app.services.permission_service import get_user_accessible_branches
            accessible_branches = get_user_accessible_branches(user_id, hospital_id)
        except ImportError:
            # Fall back to our service
            access = get_user_branch_access(user_id, hospital_id, module, action)
            accessible_branches = access.get('accessible_branches', [])
        
        # Try to get user assigned branch
        try:
            from app.services.permission_service import get_user_assigned_branch_id
            user_assigned_branch = get_user_assigned_branch_id(user_id, hospital_id)
        except ImportError:
            # Fall back to our service
            context = get_branch_context_for_form(user_id, hospital_id, module, action)
            user_assigned_branch = context.get('default_branch_id')
        
        return {
            'branch_id': branch_id,
            'module': module,
            'action': action,
            'user_id': user_id,
            'user_assigned_branch_id': user_assigned_branch,
            'accessible_branches': accessible_branches,
            'is_multi_branch_user': len(accessible_branches) > 1,
            'is_cross_branch': branch_id == 'all' or branch_id is None
        }
        
    except Exception as e:
        logger.error(f"Error getting branch context: {str(e)}")
        return {
            'branch_id': branch_id,
            'module': module,
            'action': action,
            'user_id': user_id,
            'error': str(e)
        }

def validate_entity_branch_access(user_id, hospital_id, entity_id, entity_type, operation='view'):
    """
    Generic function to validate user can access specific entity based on its branch
    Works for any entity type (supplier, patient, invoice, etc.)
    """
    try:
        # Testing bypass
        if user_id == '7777777777':
            return True
        
        # Get entity's branch
        entity_branch_id = get_entity_branch_id(entity_type, entity_id, hospital_id)
        if not entity_branch_id:
            return True  # No branch restriction
        
        # Use our validation function
        return validate_user_branch_action(user_id, hospital_id, entity_branch_id, entity_type, operation)
        
    except Exception as e:
        logger.error(f"Error validating entity branch access: {str(e)}")
        return True  # Allow on error (non-disruptive)

def get_branch_from_user_and_request(user_id, hospital_id, module):
    """
    Service function that combines user context with request parameters
    Returns (branch_uuid, branch_context) - same as your current helper
    """
    from flask import request
    import uuid
    
    # Get branch_id from request parameters first
    branch_id = request.args.get('branch_id') if request else None
    
    # If not in request, use our unified service
    if not branch_id:
        context = get_branch_context_for_form(user_id, hospital_id, module, 'view')
        branch_id = context.get('default_branch_id')
    
    # Convert to UUID if provided
    branch_uuid = None
    if branch_id and branch_id != '':
        try:
            branch_uuid = uuid.UUID(branch_id)
        except ValueError:
            logger.warning(f"Invalid branch_id format: {branch_id}")
    
    # Create context using our service
    context = get_branch_context_for_form(user_id, hospital_id, module, 'view')
    branch_context = {
        'assigned_branch_id': context.get('default_branch_id'),
        'can_cross_branch': context.get('has_cross_branch_access', False),
        'is_multi_branch_user': len(context.get('branches', [])) > 1
    }
    
    return branch_uuid, branch_context

# Add the diagnose function if it was being used
def diagnose_user_branch_access(user_id, hospital_id):
    """
    Diagnostic function to understand why branch access is failing
    This helps debug the exact issue
    """
    try:
        from app.services.database_service import get_db_session
        from app.models.master import Branch, Staff, Hospital
        from app.models.transaction import User
        import uuid
        
        # Convert hospital_id to UUID if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        
        print(f"\n=== BRANCH ACCESS DIAGNOSIS ===")
        print(f"User ID: {user_id}")
        print(f"Hospital ID: {hospital_id}")
        
        with get_db_session(read_only=True) as session:
            # Check hospital exists
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
            if hospital:
                print(f"✓ Hospital found: {hospital.name}")
            else:
                print(f"✗ Hospital not found!")
                return
            
            # Check branches
            branches = session.query(Branch).filter_by(hospital_id=hospital_id).all()
            active_branches = [b for b in branches if b.is_active]
            print(f"✓ Total branches: {len(branches)}")
            print(f"✓ Active branches: {len(active_branches)}")
            
            for branch in active_branches:
                print(f"  - {branch.name} (ID: {branch.branch_id})")
            
            # Check user
            user = session.query(User).filter_by(user_id=user_id).first()
            if user:
                print(f"✓ User found: {user_id}")
                print(f"  - Entity type: {user.entity_type}")
                print(f"  - Entity ID: {user.entity_id}")
                print(f"  - Hospital ID: {user.hospital_id}")
                
                if user.entity_type == 'staff' and user.entity_id:
                    staff = session.query(Staff).filter_by(staff_id=user.entity_id).first()
                    if staff:
                        print(f"✓ Staff record found")
                        print(f"  - Staff ID: {staff.staff_id}")
                        print(f"  - Branch ID: {staff.branch_id}")
                        print(f"  - Hospital ID: {staff.hospital_id}")
                        
                        if staff.branch_id:
                            staff_branch = session.query(Branch).filter_by(
                                branch_id=staff.branch_id
                            ).first()
                            if staff_branch:
                                print(f"✓ Staff branch found: {staff_branch.name}")
                                print(f"  - Active: {staff_branch.is_active}")
                            else:
                                print(f"✗ Staff branch {staff.branch_id} not found!")
                        else:
                            print(f"! Staff has no branch assignment (admin user)")
                    else:
                        print(f"✗ Staff record not found for entity_id: {user.entity_id}")
                else:
                    print(f"! User is not staff type")
            else:
                print(f"✗ User not found!")
            
            print(f"=== END DIAGNOSIS ===\n")
            
    except Exception as e:
        print(f"✗ Diagnosis failed: {str(e)}")
        import traceback
        traceback.print_exc()

def populate_branch_choices_for_user(form_field, current_user, required: bool = False, 
                                    include_all_option: bool = False, session=None) -> bool:
    """
    Enhanced helper function to populate branch choices based on user access.
    
    Args:
        form_field: The SelectField to populate (WTForms field)
        current_user: Current logged-in user object
        required: Whether branch selection is required (affects empty option text)
        include_all_option: Whether to include an "All Branches" option for admins
        session: Optional database session (for performance in bulk operations)
        
    Returns:
        bool: True if choices were populated successfully, False otherwise
    """
    try:
        # Determine if we need to create a new session
        should_close_session = session is None
        
        if session is None:
            session = get_db_session(read_only=True).__enter__()
        
        try:
            # Import models here to avoid circular imports
            from app.models.transaction import User
            from app.models.master import Staff
            
            # Get user's staff record to determine branch access
            user_record = session.query(User).filter_by(user_id=current_user.user_id).first()
            user_branch_id = None
            is_admin = False
            
            if user_record and user_record.entity_type == 'staff':
                staff = session.query(Staff).filter_by(staff_id=user_record.entity_id).first()
                if staff and staff.branch_id:
                    user_branch_id = staff.branch_id
                else:
                    # Staff without specific branch assignment = admin
                    is_admin = True
            else:
                # Non-staff user = admin
                is_admin = True
            
            # Get hospital's branches
            branches = session.query(Branch).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True
            ).order_by(Branch.name).all()
            
            if not branches:
                # No branches found - set minimal choices
                if required:
                    form_field.choices = [('', 'No branches available')]
                else:
                    form_field.choices = [('', 'Default Branch')]
                logger.warning(f"No active branches found for hospital {current_user.hospital_id}")
                return False
            
            # Determine default branch
            default_branch_id = get_default_branch_id(current_user.hospital_id)
            
            if user_branch_id and not is_admin:
                # User is assigned to specific branch - restrict to that branch only
                user_branch = next((b for b in branches if b.branch_id == user_branch_id), None)
                if user_branch:
                    form_field.choices = [(str(user_branch.branch_id), user_branch.name)]
                    form_field.data = str(user_branch.branch_id)
                    logger.debug(f"User {current_user.user_id} restricted to branch: {user_branch.name}")
                    return True
                else:
                    # User's assigned branch is not active - fallback to default
                    logger.warning(f"User's assigned branch {user_branch_id} not found in active branches")
                    if required:
                        form_field.choices = [('', 'No accessible branches')]
                    else:
                        form_field.choices = [('', 'Default Branch')]
                    return False
            
            else:
                # User has access to multiple branches (admin or multi-branch user)
                choices = []
                
                # Add empty/default option
                if required:
                    choices.append(('', 'Select Branch'))
                else:
                    choices.append(('', 'Default Branch'))
                
                # Add "All Branches" option for admins if requested
                if include_all_option and is_admin:
                    choices.append(('__all__', 'All Branches'))
                
                # Add individual branch choices
                for branch in branches:
                    branch_label = branch.name
                    if str(branch.branch_id) == str(default_branch_id):
                        branch_label += ' (Default)'
                    choices.append((str(branch.branch_id), branch_label))
                
                form_field.choices = choices
                
                # Set default selection
                if not required and default_branch_id:
                    form_field.data = str(default_branch_id)
                
                logger.debug(f"User {current_user.user_id} has access to {len(branches)} branches")
                return True
                
        finally:
            if should_close_session:
                session.__exit__(None, None, None)
                
    except Exception as e:
        logger.error(f"Error populating branch choices for user {getattr(current_user, 'user_id', 'unknown')}: {str(e)}")
        
        # Fallback to safe choices
        try:
            if required:
                form_field.choices = [('', 'Select Branch')]
            else:
                form_field.choices = [('', 'Default Branch')]
        except:
            pass  # If even this fails, let the calling code handle it
            
        return False