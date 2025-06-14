# app/services/branch_service.py - ENHANCED VERSION
# Backward compatible additions to existing branch service

from decimal import Decimal
from typing import Dict, Any, Optional, Union, Tuple, List
import uuid
import logging

from app.services.database_service import get_db_session
from app.models.master import Branch, Hospital

logger = logging.getLogger(__name__)

# =====================================================
# EXISTING FUNCTIONS (keep unchanged for backward compatibility)
# =====================================================

def get_branch_gst_details(branch_id: str, hospital_id: str) -> Dict[str, Any]:
    """
    Get GST details with branch priority and hospital fallback.
    
    Args:
        branch_id: UUID of the branch
        hospital_id: UUID of the hospital
    
    Returns:
        Dictionary with GST registration details
    """
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
        
        gst_details = {
            'gst_registration_number': branch.gst_registration_number or hospital.gst_registration_number,
            'pan_number': branch.pan_number or hospital.pan_number,
            'state_code': branch.state_code or hospital.state_code,
            'return_filing_period': branch.return_filing_period or hospital.return_filing_period
        }
        return gst_details

def get_branch_pharmacy_details(branch_id: str, hospital_id: str) -> Dict[str, Any]:
    """
    Get pharmacy registration details with branch priority and hospital fallback.
    
    Args:
        branch_id: UUID of the branch
        hospital_id: UUID of the hospital
    
    Returns:
        Dictionary with pharmacy registration information
    """
    with get_db_session() as session:
        branch = session.query(Branch).filter_by(branch_id=branch_id).first()
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        
        if not branch or not hospital:
            return {
                'registration_number': None,
                'registration_date': None,
                'valid_until': None
            }
        
        pharmacy_details = {
            'registration_number': branch.pharmacy_registration_number or hospital.pharmacy_registration_number,
            'registration_date': branch.pharmacy_registration_date or hospital.pharmacy_registration_date,
            'valid_until': branch.pharmacy_registration_valid_until or hospital.pharmacy_registration_valid_until
        }
        return pharmacy_details

def get_branch_with_fallback(branch_id: str, hospital_id: str) -> Dict[str, Any]:
    """
    Get comprehensive branch details with hospital fallback for all fields.
    
    Args:
        branch_id: UUID of the branch
        hospital_id: UUID of the hospital
    
    Returns:
        Dictionary with all branch details, falling back to hospital values where needed
    """
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
        
        # Get branch details with hospital fallbacks
        branch_details = {
            'name': branch.name,
            'address': branch.address or hospital.address,
            'contact_details': branch.contact_details or hospital.contact_details,
            'timezone': branch.timezone or hospital.timezone,
            **gst_details,
            **{f'pharmacy_{k}': v for k, v in pharmacy_details.items()}
        }
        
        return branch_details

def is_gst_registered(branch_id: str, hospital_id: str) -> bool:
    """
    Check if either branch or hospital has GST registration.
    
    Args:
        branch_id: UUID of the branch
        hospital_id: UUID of the hospital
    
    Returns:
        True if either branch or hospital has GST registration, False otherwise
    """
    gst_details = get_branch_gst_details(branch_id, hospital_id)
    return bool(gst_details['gst_registration_number'])

def is_pharmacy_registered(branch_id: str, hospital_id: str) -> bool:
    """
    Check if either branch or hospital has pharmacy registration.
    
    Args:
        branch_id: UUID of the branch
        hospital_id: UUID of the hospital
    
    Returns:
        True if either branch or hospital has pharmacy registration, False otherwise
    """
    pharmacy_details = get_branch_pharmacy_details(branch_id, hospital_id)
    return bool(pharmacy_details['registration_number'])

def get_branch_model_with_fallback(branch_id: str, hospital_id: str) -> Optional[Tuple[Branch, Hospital]]:
    """
    Get Branch and Hospital model objects for advanced operations.
    
    Args:
        branch_id: UUID of the branch
        hospital_id: UUID of the hospital
    
    Returns:
        Tuple of (Branch, Hospital) model objects or None if not found
    """
    with get_db_session() as session:
        branch = session.query(Branch).filter_by(branch_id=branch_id).first()
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        
        if not branch or not hospital:
            return None
        
        return (branch, hospital)

# =====================================================
# NEW ADDITIONS FOR SUPPLIER INTEGRATION
# All functions are backward compatible and don't break existing code
# =====================================================

def get_default_branch_id(hospital_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
    """
    Get the default/main branch for a hospital.
    Used for backward compatibility when branch is not specified.
    
    Args:
        hospital_id: Hospital UUID (accepts both str and UUID)
        
    Returns:
        Branch UUID or None if no branch found
    """
    try:
        # Convert to UUID if string
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
            
            # Strategy 2: Find branch marked as primary (if such field exists)
            if not branch:
                # Check if Branch model has is_primary field
                if hasattr(Branch, 'is_primary'):
                    branch = session.query(Branch).filter(
                        Branch.hospital_id == hospital_id,
                        Branch.is_active == True,
                        Branch.is_primary == True
                    ).first()
            
            # Strategy 3: Get the oldest active branch (likely the first/main one)
            if not branch:
                branch = session.query(Branch).filter(
                    Branch.hospital_id == hospital_id,
                    Branch.is_active == True
                ).order_by(Branch.created_at).first()
                
            return branch.branch_id if branch else None
            
    except Exception as e:
        logger.error(f"Error getting default branch for hospital {hospital_id}: {str(e)}")
        return None

def get_user_branch_id(current_user_id: Optional[str] = None, hospital_id: Optional[Union[str, uuid.UUID]] = None) -> Optional[uuid.UUID]:
    """
    Get branch ID for current user, with fallback to main branch.
    Essential for determining which branch a user should work with.
    
    Args:
        current_user_id: User ID
        hospital_id: Hospital UUID (for fallback)
        
    Returns:
        Branch UUID or None
    """
    try:
        if current_user_id:
            # Import here to avoid circular imports
            from app.models.transaction import User
            from app.models.master import Staff
            
            with get_db_session(read_only=True) as session:
                # Get user entity (staff)
                user = session.query(User).filter_by(user_id=current_user_id).first()
                if user and user.entity_type == 'staff':
                    staff = session.query(Staff).filter_by(staff_id=user.entity_id).first()
                    if staff and staff.branch_id:
                        return staff.branch_id
        
        # Fallback to main branch
        if hospital_id:
            return get_default_branch_id(hospital_id)
            
        return None
        
    except Exception as e:
        logger.warning(f"Could not determine user branch, using main branch: {str(e)}")
        if hospital_id:
            return get_default_branch_id(hospital_id)
        return None

def validate_branch_access(user_id: str, hospital_id: Union[str, uuid.UUID], target_branch_id: Union[str, uuid.UUID]) -> bool:
    """
    Validate if user has access to the specified branch.
    Critical for security - ensures users can only access their assigned branch data.
    
    Args:
        user_id: User ID
        hospital_id: Hospital UUID
        target_branch_id: Branch UUID to validate access to
        
    Returns:
        True if access is allowed, False otherwise
    """
    try:
        # Convert to UUID if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        if isinstance(target_branch_id, str):
            target_branch_id = uuid.UUID(target_branch_id)
            
        # Get user's assigned branch
        user_branch_id = get_user_branch_id(user_id, hospital_id)
        
        # If user has no specific branch assignment, they can access all branches (admin)
        if not user_branch_id:
            logger.info(f"User {user_id} has admin access to all branches")
            return True
            
        # If user is assigned to a specific branch, they can only access that branch
        access_granted = str(user_branch_id) == str(target_branch_id)
        
        if not access_granted:
            logger.warning(f"User {user_id} denied access to branch {target_branch_id}, assigned to {user_branch_id}")
            
        return access_granted
        
    except Exception as e:
        logger.error(f"Error validating branch access: {str(e)}")
        return False  # Deny access on error

def get_user_accessible_branches(user_id: str, hospital_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
    """
    Get list of branches accessible to user.
    Useful for populating branch selection dropdowns.
    
    Args:
        user_id: User ID
        hospital_id: Hospital UUID
        
    Returns:
        List of branch dictionaries with branch_id, name, and is_default fields
    """
    try:
        # Convert to UUID if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
            
        with get_db_session(read_only=True) as session:
            user_branch_id = get_user_branch_id(user_id, hospital_id)
            default_branch_id = get_default_branch_id(hospital_id)
            
            if user_branch_id:
                # User has specific branch - return only that branch
                branch = session.query(Branch).filter_by(
                    branch_id=user_branch_id,
                    is_active=True
                ).first()
                
                if branch:
                    return [{
                        'branch_id': str(branch.branch_id), 
                        'name': branch.name,
                        'is_default': str(branch.branch_id) == str(default_branch_id),
                        'is_user_branch': True
                    }]
                else:
                    return []
            else:
                # User can access all branches (admin)
                branches = session.query(Branch).filter_by(
                    hospital_id=hospital_id,
                    is_active=True
                ).order_by(Branch.name).all()
                
                return [{
                    'branch_id': str(branch.branch_id), 
                    'name': branch.name,
                    'is_default': str(branch.branch_id) == str(default_branch_id),
                    'is_user_branch': False
                } for branch in branches]
                
    except Exception as e:
        logger.error(f"Error getting accessible branches: {str(e)}")
        return []

def get_branch_summary(hospital_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
    """
    Get summary information about all branches in a hospital.
    Useful for dashboard and reporting.
    
    Args:
        hospital_id: Hospital UUID
        
    Returns:
        Dictionary with branch summary information
    """
    try:
        # Convert to UUID if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
            
        with get_db_session(read_only=True) as session:
            # Get all branches
            branches = session.query(Branch).filter_by(hospital_id=hospital_id).all()
            
            active_branches = [b for b in branches if b.is_active]
            inactive_branches = [b for b in branches if not b.is_active]
            
            default_branch_id = get_default_branch_id(hospital_id)
            
            return {
                'total_branches': len(branches),
                'active_branches': len(active_branches),
                'inactive_branches': len(inactive_branches),
                'default_branch_id': str(default_branch_id) if default_branch_id else None,
                'branch_list': [{
                    'branch_id': str(branch.branch_id),
                    'name': branch.name,
                    'is_active': branch.is_active,
                    'is_default': str(branch.branch_id) == str(default_branch_id) if default_branch_id else False,
                    'created_at': branch.created_at.isoformat() if hasattr(branch, 'created_at') and branch.created_at else None
                } for branch in branches]
            }
            
    except Exception as e:
        logger.error(f"Error getting branch summary: {str(e)}")
        return {
            'total_branches': 0,
            'active_branches': 0,
            'inactive_branches': 0,
            'default_branch_id': None,
            'branch_list': []
        }

def ensure_hospital_has_default_branch(hospital_id: Union[str, uuid.UUID]) -> Optional[uuid.UUID]:
    """
    Ensure hospital has at least one branch, create default if needed.
    Useful for hospital setup and data migration.
    
    Args:
        hospital_id: Hospital UUID
        
    Returns:
        Branch UUID of default branch or None if creation failed
    """
    try:
        # Convert to UUID if needed
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
            
        # Check if default branch exists
        default_branch_id = get_default_branch_id(hospital_id)
        if default_branch_id:
            return default_branch_id
            
        # Create default branch
        with get_db_session() as session:
            # Get hospital details
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
            if not hospital:
                logger.error(f"Hospital {hospital_id} not found")
                return None
                
            # Create main branch
            main_branch = Branch(
                hospital_id=hospital_id,
                name="Main Branch",
                is_active=True,
                # Copy relevant details from hospital
                address=hospital.address,
                contact_details=hospital.contact_details,
                gst_registration_number=hospital.gst_registration_number,
                pan_number=hospital.pan_number,
                state_code=hospital.state_code,
                timezone=hospital.timezone if hasattr(hospital, 'timezone') else None
            )
            
            session.add(main_branch)
            session.commit()
            
            logger.info(f"Created default branch for hospital {hospital_id}: {main_branch.branch_id}")
            return main_branch.branch_id
            
    except Exception as e:
        logger.error(f"Error ensuring default branch for hospital {hospital_id}: {str(e)}")
        return None

# =====================================================
# INTEGRATION HELPERS FOR SUPPLIER SERVICE
# =====================================================

def get_branch_for_supplier_operation(current_user_id: Optional[str] = None, 
                                     hospital_id: Optional[Union[str, uuid.UUID]] = None,
                                     specified_branch_id: Optional[Union[str, uuid.UUID]] = None) -> Optional[uuid.UUID]:
    """
    Determine branch for supplier operations with multiple fallback strategies.
    This is the main function supplier service should use.
    
    Args:
        current_user_id: User ID
        hospital_id: Hospital UUID
        specified_branch_id: Explicitly specified branch ID
        
    Returns:
        Branch UUID to use for the operation
    """
    try:
        # Strategy 1: Use explicitly specified branch if provided and valid
        if specified_branch_id:
            if isinstance(specified_branch_id, str):
                specified_branch_id = uuid.UUID(specified_branch_id)
                
            # Validate user has access to this branch
            if current_user_id and hospital_id:
                if validate_branch_access(current_user_id, hospital_id, specified_branch_id):
                    return specified_branch_id
                else:
                    logger.warning(f"User {current_user_id} denied access to specified branch {specified_branch_id}")
        
        # Strategy 2: Use user's assigned branch
        if current_user_id and hospital_id:
            user_branch = get_user_branch_id(current_user_id, hospital_id)
            if user_branch:
                return user_branch
        
        # Strategy 3: Use hospital default branch
        if hospital_id:
            default_branch = get_default_branch_id(hospital_id)
            if default_branch:
                return default_branch
        
        # Strategy 4: Ensure default branch exists and return it
        if hospital_id:
            return ensure_hospital_has_default_branch(hospital_id)
            
        return None
        
    except Exception as e:
        logger.error(f"Error determining branch for supplier operation: {str(e)}")
        return None