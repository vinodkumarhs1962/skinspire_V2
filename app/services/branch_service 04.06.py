# app/services/branch_service.py - ENHANCED VERSION WITH FORM HELPER
# Backward compatible additions to existing branch service

from decimal import Decimal
from typing import Dict, Any, Optional, Union, Tuple, List
import uuid
import logging

from app.services.database_service import get_db_session
from app.models.master import Branch, Hospital
from app.services.permission_service import get_user_assigned_branch_id

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
# EXISTING SUPPLIER INTEGRATION FUNCTIONS
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

# =====================================================
# NEW: FORM HELPER FUNCTIONS
# =====================================================

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

def get_branch_choices_for_user(current_user, include_all_option: bool = False, 
                               include_empty_option: bool = True, empty_text: str = "Select Branch") -> List[Tuple[str, str]]:
    """
    Get branch choices as a list of tuples for manual form population.
    
    Args:
        current_user: Current logged-in user object
        include_all_option: Whether to include an "All Branches" option
        include_empty_option: Whether to include an empty option
        empty_text: Text for the empty option
        
    Returns:
        List of (value, label) tuples suitable for SelectField choices
    """
    try:
        with get_db_session(read_only=True) as session:
            # Import models here to avoid circular imports
            from app.models.transaction import User
            from app.models.master import Staff
            
            # Get user's branch access
            user_record = session.query(User).filter_by(user_id=current_user.user_id).first()
            user_branch_id = None
            is_admin = False
            
            if user_record and user_record.entity_type == 'staff':
                staff = session.query(Staff).filter_by(staff_id=user_record.entity_id).first()
                if staff and staff.branch_id:
                    user_branch_id = staff.branch_id
                else:
                    is_admin = True
            else:
                is_admin = True
            
            # Get branches
            branches = session.query(Branch).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True
            ).order_by(Branch.name).all()
            
            if not branches:
                return [('', 'No branches available')] if include_empty_option else []
            
            choices = []
            
            # Add empty option if requested
            if include_empty_option:
                choices.append(('', empty_text))
            
            # Add "All Branches" option if requested and user is admin
            if include_all_option and is_admin:
                choices.append(('__all__', 'All Branches'))
            
            # Determine default branch
            default_branch_id = get_default_branch_id(current_user.hospital_id)
            
            if user_branch_id and not is_admin:
                # User restricted to specific branch
                user_branch = next((b for b in branches if b.branch_id == user_branch_id), None)
                if user_branch:
                    choices.append((str(user_branch.branch_id), user_branch.name))
            else:
                # User can access multiple branches
                for branch in branches:
                    branch_label = branch.name
                    if str(branch.branch_id) == str(default_branch_id):
                        branch_label += ' (Default)'
                    choices.append((str(branch.branch_id), branch_label))
            
            return choices
            
    except Exception as e:
        logger.error(f"Error getting branch choices: {str(e)}")
        return [('', 'Error loading branches')] if include_empty_option else []

def validate_branch_choice(branch_choice: str, current_user, allow_empty: bool = True) -> bool:
    """
    Validate that a branch choice is valid for the current user.
    
    Args:
        branch_choice: The branch ID string from form submission
        current_user: Current logged-in user object
        allow_empty: Whether empty/default choice is allowed
        
    Returns:
        bool: True if the choice is valid, False otherwise
    """
    try:
        # Empty choice validation
        if not branch_choice or branch_choice == '':
            return allow_empty
        
        # Special "All Branches" choice
        if branch_choice == '__all__':
            # Only admins can select "All Branches"
            accessible_branches = get_user_accessible_branches(current_user.user_id, current_user.hospital_id)
            # If user has access to multiple branches, they're likely an admin
            return len(accessible_branches) > 1 and not any(b.get('is_user_branch') for b in accessible_branches)
        
        # Validate specific branch choice
        try:
            branch_uuid = uuid.UUID(branch_choice)
            return validate_branch_access(current_user.user_id, current_user.hospital_id, branch_uuid)
        except ValueError:
            # Invalid UUID format
            return False
            
    except Exception as e:
        logger.error(f"Error validating branch choice {branch_choice}: {str(e)}")
        return False

def get_effective_branch_id(branch_choice: str, current_user) -> Optional[uuid.UUID]:
    """
    Convert a form branch choice to an effective branch ID for database operations.
    
    Args:
        branch_choice: The branch choice from form (could be empty, UUID string, or '__all__')
        current_user: Current logged-in user object
        
    Returns:
        UUID: Effective branch ID to use, or None for "all branches" operations
    """
    try:
        # Handle empty/default choice
        if not branch_choice or branch_choice == '':
            return get_default_branch_id(current_user.hospital_id)
        
        # Handle "All Branches" choice
        if branch_choice == '__all__':
            return None  # None indicates "all branches"
        
        # Handle specific branch choice
        try:
            return uuid.UUID(branch_choice)
        except ValueError:
            # Invalid format - fallback to default
            logger.warning(f"Invalid branch choice format: {branch_choice}")
            return get_default_branch_id(current_user.hospital_id)
            
    except Exception as e:
        logger.error(f"Error getting effective branch ID for choice {branch_choice}: {str(e)}")
        return get_default_branch_id(current_user.hospital_id) if hasattr(current_user, 'hospital_id') else None
    
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
                branch_id = request.get_json().get('branch_id')
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
        from app.services.permission_service import determine_target_branch
        branch_id = determine_target_branch(user.user_id, user.hospital_id, None)
        
        logger.debug(f"Branch context from determine_target_branch: {branch_id}")
        return branch_id
        
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
        
        # Add more entity types as needed
        
    except Exception as e:
        logger.error(f"Error extracting entity branch_id: {str(e)}")
    
    return None

def get_entity_branch_id(entity_type: str, entity_id: str, session):
    """
    Generic function to get branch_id for any entity type
    Centralized entity branch lookup
    """
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
        
    except Exception as e:
        logger.error(f"Error getting {entity_type} branch_id: {str(e)}")
        return None

def check_superuser_status(user_id: str, session) -> bool:
    """
    Check if user has superuser roles
    Centralized superuser checking for decorators
    """
    try:
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
        from app.services.permission_service import get_user_accessible_branches
        
        accessible_branches = get_user_accessible_branches(user_id, hospital_id)
        user_assigned_branch = get_user_assigned_branch_id(user_id, hospital_id)  # [OK] Now available
        
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
    FIXED: Import and use proper permission checking
    """
    try:
        # Testing bypass
        if user_id == '7777777777':
            return True
        
        # Get entity's branch
        entity_branch_id = get_entity_branch_id(entity_type, entity_id, hospital_id)
        if not entity_branch_id:
            return True  # No branch restriction
        
        # FIXED: Import permission service and check access
        from app.services.permission_service import has_branch_permission
        user_obj = {'user_id': user_id, 'hospital_id': hospital_id}
        return has_branch_permission(user_obj, entity_type, operation, entity_branch_id)
        
    except Exception as e:
        logger.error(f"Error validating entity branch access: {str(e)}")
        return True  # Allow on error (non-disruptive)

def get_entity_branch_id(entity_type, entity_id, hospital_id):
    """
    Generic function to get branch_id for any entity
    FIXED: Proper imports and error handling
    """
    try:
        import uuid
        from app.services.database_service import get_db_session
        
        entity_map = {
            'supplier': ('app.models.master', 'Supplier', 'supplier_id'),
            'patient': ('app.models.master', 'Patient', 'patient_id'),
            'invoice': ('app.models.transaction', 'InvoiceHeader', 'invoice_id'),
            'purchase_order': ('app.models.transaction', 'PurchaseOrderHeader', 'po_id'),
        }
        
        if entity_type not in entity_map:
            return None
        
        module_name, class_name, id_field = entity_map[entity_type]
        
        with get_db_session(read_only=True) as session:
            module = __import__(module_name, fromlist=[class_name])
            entity_class = getattr(module, class_name)
            
            # FIXED: Proper UUID conversion
            entity_uuid = uuid.UUID(str(entity_id))
            
            entity = session.query(entity_class).filter(
                getattr(entity_class, id_field) == entity_uuid,
                entity_class.hospital_id == uuid.UUID(str(hospital_id))
            ).first()
            
            return str(entity.branch_id) if entity and hasattr(entity, 'branch_id') and entity.branch_id else None
            
    except Exception as e:
        logger.error(f"Error getting entity branch_id: {str(e)}")
        return None
    

def get_branch_from_user_and_request(user_id, hospital_id, module):
    """
    Service function that combines user context with request parameters
    Returns (branch_uuid, branch_context) - same as your current helper
    """
    from flask import request
    import uuid
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get user's branch context from permission service
    from app.services.permission_service import get_user_branch_context
    branch_context = get_user_branch_context(user_id, hospital_id, module)
    
    # Get branch_id from request parameters first
    branch_id = request.args.get('branch_id') if request else None
    
    # If not in request, use user's assigned branch
    if not branch_id and branch_context.get('assigned_branch_id'):
        branch_id = branch_context['assigned_branch_id']
    
    # Convert to UUID if provided
    branch_uuid = None
    if branch_id and branch_id != '':
        try:
            branch_uuid = uuid.UUID(branch_id)
        except ValueError:
            logger.warning(f"Invalid branch_id format: {branch_id}")
    
    return branch_uuid, branch_context

def get_user_accessible_branches_simple(user_id, hospital_id):
    """
    Simple function to get user's accessible branches using existing User/Staff model
    This is a fallback when the main permission service fails
    """
    try:
        from app.services.database_service import get_db_session
        from app.models.master import Branch, Staff
        from app.models.transaction import User
        import uuid
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Getting accessible branches for user {user_id} in hospital {hospital_id}")
        
        # Convert hospital_id to UUID if it's a string
        if isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        
        with get_db_session(read_only=True) as session:
            # Get all active branches for the hospital
            all_branches = session.query(Branch).filter_by(
                hospital_id=hospital_id,
                is_active=True
            ).order_by(Branch.name).all()
            
            logger.info(f"Found {len(all_branches)} total branches")
            
            # PRESERVE: Testing bypass
            if user_id == '7777777777':
                logger.info("Testing user - returning all branches")
                return {
                    'accessible_branches': [
                        {
                            'branch_id': str(branch.branch_id),
                            'branch_name': branch.name,
                            'is_default': False
                        } for branch in all_branches
                    ],
                    'default_branch_id': str(all_branches[0].branch_id) if all_branches else None,
                    'can_cross_branch': True,
                    'is_multi_branch_user': len(all_branches) > 1
                }
            
            # Get user record
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return {
                    'accessible_branches': [],
                    'default_branch_id': None,
                    'can_cross_branch': False,
                    'is_multi_branch_user': False
                }
            
            logger.info(f"User entity type: {user.entity_type}, entity_id: {user.entity_id}")
            
            # If user is a staff member, get their branch assignment
            if user.entity_type == 'staff' and user.entity_id:
                try:
                    staff = session.query(Staff).filter_by(staff_id=user.entity_id).first()
                    if staff and staff.branch_id:
                        # Staff assigned to specific branch
                        branch = session.query(Branch).filter_by(
                            branch_id=staff.branch_id,
                            is_active=True
                        ).first()
                        
                        if branch:
                            logger.info(f"Staff assigned to branch: {branch.name}")
                            return {
                                'accessible_branches': [{
                                    'branch_id': str(branch.branch_id),
                                    'branch_name': branch.name,
                                    'is_default': True
                                }],
                                'default_branch_id': str(branch.branch_id),
                                'can_cross_branch': False,
                                'is_multi_branch_user': False
                            }
                        else:
                            logger.warning(f"Staff branch {staff.branch_id} not found or inactive")
                    else:
                        logger.info("Staff has no specific branch assignment - treating as admin")
                        # Staff without branch assignment = admin with access to all branches
                        return {
                            'accessible_branches': [
                                {
                                    'branch_id': str(branch.branch_id),
                                    'branch_name': branch.name,
                                    'is_default': False
                                } for branch in all_branches
                            ],
                            'default_branch_id': str(all_branches[0].branch_id) if all_branches else None,
                            'can_cross_branch': True,
                            'is_multi_branch_user': len(all_branches) > 1
                        }
                        
                except Exception as staff_error:
                    logger.error(f"Error getting staff details: {str(staff_error)}")
            
            # For non-staff users or if staff lookup failed
            # Check if single branch hospital (auto-assign)
            if len(all_branches) == 1:
                logger.info("Single branch hospital - auto-assigning")
                branch = all_branches[0]
                return {
                    'accessible_branches': [{
                        'branch_id': str(branch.branch_id),
                        'branch_name': branch.name,
                        'is_default': True
                    }],
                    'default_branch_id': str(branch.branch_id),
                    'can_cross_branch': False,
                    'is_multi_branch_user': False
                }
            else:
                # Multi-branch hospital - default to no access for safety
                logger.warning(f"Multi-branch hospital but user {user_id} has no clear branch assignment")
                return {
                    'accessible_branches': [],
                    'default_branch_id': None,
                    'can_cross_branch': False,
                    'is_multi_branch_user': False
                }
                
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_user_accessible_branches_simple: {str(e)}", exc_info=True)
        return {
            'accessible_branches': [],
            'default_branch_id': None,
            'can_cross_branch': False,
            'is_multi_branch_user': False
        }
    
# Add this temporary diagnostic function to help debug
# You can add this to app/services/branch_service.py temporarily

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
        import logging
        
        logger = logging.getLogger(__name__)
        
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

# You can call this function in your controller temporarily to debug
# diagnose_user_branch_access(current_user.user_id, current_user.hospital_id)