# =============================================================================
# File: app/utils/context_helpers.py
# =============================================================================

"""
Context helpers for Universal View Engine template integration
Provides the missing functions that universal_views.py needs for template context
Enhanced with hospital and branch context methods for document service
"""

from flask import g, current_app, request, session as flask_session
from flask_login import current_user
from typing import Dict, Any, Optional, Tuple
import uuid
from datetime import datetime, timedelta

from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

# =============================================================================
# EXISTING FUNCTIONS (Keep as-is)
# =============================================================================

def get_branch_uuid_from_context_or_request():
    """
    Helper function to get branch UUID - delegates to your service layer
    RESOLVES: Import error in universal supplier service
    """
    try:
        from app.services.branch_service import get_branch_from_user_and_request
        return get_branch_from_user_and_request(
            current_user.user_id, 
            current_user.hospital_id, 
            'universal'
        )
    except Exception as e:
        logger.error(f"Error getting branch context: {str(e)}")
        return None, None

def get_user_branch_context():
    """
    Helper function to get branch context - delegates to service layer
    """
    try:
        from app.services.permission_service import get_user_branch_context
        return get_user_branch_context(
            current_user.user_id, 
            current_user.hospital_id, 
            'universal'
        )
    except Exception as e:
        logger.error(f"Error getting user branch context: {str(e)}")
        return None

def ensure_request_context():
    """
    Ensure we have proper Flask request context for template helpers
    """
    if not hasattr(g, 'universal_context_initialized'):
        g.universal_context_initialized = True
        g.current_filters = getattr(request, 'args', {}).to_dict() if request else {}
        g.current_user_permissions = {}

# =============================================================================
# NEW HOSPITAL AND BRANCH CONTEXT FUNCTIONS
# =============================================================================

def get_current_hospital() -> Dict[str, Any]:
    """
    Get current hospital context from logged in user
    Returns dict with hospital_id and hospital_name
    Required by document service
    """
    if not current_user or not current_user.is_authenticated:
        return {
            'hospital_id': None,
            'hospital_name': 'Hospital'
        }
    
    try:
        from app.services.database_service import get_db_session
        from app.models.master import Hospital
        
        # Check if we have cached hospital name in session
        cache_key = f'hospital_name_{current_user.hospital_id}'
        if flask_session and cache_key in flask_session:
            cached_name = flask_session.get(cache_key)
            if cached_name:
                return {
                    'hospital_id': current_user.hospital_id,
                    'hospital_name': cached_name
                }
        
        # Fetch from database
        with get_db_session(read_only=True) as db_session:
            hospital = db_session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()
            
            hospital_name = hospital.name if hospital else 'Hospital'
            
            # Cache in session
            if flask_session:
                flask_session[cache_key] = hospital_name
            
            return {
                'hospital_id': current_user.hospital_id,
                'hospital_name': hospital_name
            }
            
    except Exception as e:
        logger.error(f"Error getting current hospital: {str(e)}")
        return {
            'hospital_id': getattr(current_user, 'hospital_id', None),
            'hospital_name': 'Hospital'
        }

def get_hospital_context() -> Dict[str, Any]:
    """
    Alias for get_current_hospital for backward compatibility
    """
    return get_current_hospital()

def get_current_branch() -> Dict[str, Any]:
    """
    Get current branch context
    Priority: Flask session > User's staff branch > Default branch
    """
    if not current_user or not current_user.is_authenticated:
        return {
            'branch_id': None,
            'branch_name': 'Branch'
        }
    
    try:
        # Check Flask session first (user's current selection)
        if flask_session:
            session_branch_id = flask_session.get('branch_uuid')
            session_branch_name = flask_session.get('branch_name')
            
            if session_branch_id and session_branch_name:
                return {
                    'branch_id': session_branch_id,
                    'branch_name': session_branch_name
                }
        
        # Get from staff branch service
        from app.services.branch_service import get_user_staff_branch
        
        staff_branch = get_user_staff_branch(
            current_user.user_id, 
            current_user.hospital_id
        )
        
        if staff_branch:
            if isinstance(staff_branch, dict):
                branch_name = staff_branch.get('branch_name')
                branch_id = staff_branch.get('branch_id')
                
                if staff_branch.get('is_admin'):
                    return {
                        'branch_id': None,
                        'branch_name': 'All Branches'
                    }
                elif staff_branch.get('is_multi_branch_user'):
                    return {
                        'branch_id': branch_id,
                        'branch_name': 'Multi-Branch Access'
                    }
                elif branch_name:
                    return {
                        'branch_id': branch_id,
                        'branch_name': branch_name
                    }
        
        # Fallback to default branch
        from app.services.database_service import get_db_session
        from app.models.master import Branch, Staff
        
        with get_db_session(read_only=True) as db_session:
            # Try to get from Staff table
            staff = db_session.query(Staff).filter_by(
                user_id=current_user.user_id,
                hospital_id=current_user.hospital_id,
                is_active=True
            ).first()
            
            if staff and staff.branch_id:
                branch = db_session.query(Branch).filter_by(
                    branch_id=staff.branch_id,
                    is_active=True
                ).first()
                
                if branch:
                    return {
                        'branch_id': str(branch.branch_id),
                        'branch_name': branch.name
                    }
            
            # Get primary or first active branch
            default_branch = db_session.query(Branch).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True
            ).order_by(
                Branch.is_primary.desc(),
                Branch.created_at
            ).first()
            
            if default_branch:
                return {
                    'branch_id': str(default_branch.branch_id),
                    'branch_name': default_branch.name
                }
        
        return {
            'branch_id': None,
            'branch_name': 'Main Branch'
        }
        
    except Exception as e:
        logger.error(f"Error getting current branch: {str(e)}")
        return {
            'branch_id': None,
            'branch_name': 'Branch'
        }

def get_complete_context() -> Dict[str, Any]:
    """
    Get complete context for documents and views
    Single source of truth for hospital, branch, and user information
    """
    if not current_user or not current_user.is_authenticated:
        return {
            'hospital_id': None,
            'hospital_name': 'Hospital',
            'branch_id': None,
            'branch_name': 'Branch',
            'user_id': None,
            'username': 'Guest',
            'full_name': 'Guest User'
        }
    
    try:
        # Get hospital context
        hospital_context = get_current_hospital()
        
        # Get branch context
        branch_context = get_current_branch()
        
        # Combine all context
        return {
            'hospital_id': hospital_context['hospital_id'],
            'hospital_name': hospital_context['hospital_name'],
            'branch_id': branch_context['branch_id'],
            'branch_name': branch_context['branch_name'],
            'user_id': current_user.user_id,
            'username': current_user.username,
            'full_name': getattr(current_user, 'full_name', current_user.username),
            'email': getattr(current_user, 'email', None),
            'role': getattr(current_user, 'role', None)
        }
        
    except Exception as e:
        logger.error(f"Error getting complete context: {str(e)}")
        return {
            'hospital_id': getattr(current_user, 'hospital_id', None),
            'hospital_name': 'Hospital',
            'branch_id': None,
            'branch_name': 'Branch',
            'user_id': getattr(current_user, 'user_id', None),
            'username': getattr(current_user, 'username', 'Guest'),
            'full_name': getattr(current_user, 'full_name', 'Guest User')
        }

def get_hospital_and_branch_for_display() -> Tuple[str, str]:
    """
    Get hospital and branch names for display purposes
    Returns tuple of (hospital_name, branch_name)
    This is a cleaner alternative to the method in universal_views.py
    """
    if not current_user or not current_user.is_authenticated:
        return "Hospital", "Branch"
    
    try:
        # Use the centralized context methods
        hospital_context = get_current_hospital()
        branch_context = get_current_branch()
        
        return (
            hospital_context.get('hospital_name', 'Hospital'),
            branch_context.get('branch_name', 'Branch')
        )
        
    except Exception as e:
        logger.error(f"Error getting display names: {str(e)}")
        return "Hospital", "Branch"

def refresh_context_cache():
    """
    Clear cached context data to force refresh
    Useful after branch switching or permission changes
    """
    if flask_session:
        # Clear hospital cache
        hospital_cache_key = f'hospital_name_{current_user.hospital_id}' if current_user else None
        if hospital_cache_key and hospital_cache_key in flask_session:
            flask_session.pop(hospital_cache_key, None)
        
        # Clear any other cached context
        keys_to_clear = [k for k in flask_session.keys() if k.startswith('context_')]
        for key in keys_to_clear:
            flask_session.pop(key, None)
    
    # Clear g context
    if hasattr(g, 'universal_context_initialized'):
        delattr(g, 'universal_context_initialized')
    
    logger.debug("Context cache refreshed")

def set_branch_context(branch_id: str, branch_name: str):
    """
    Set the current branch context in session
    Used when user switches branches
    """
    if flask_session:
        flask_session['branch_uuid'] = branch_id
        flask_session['branch_name'] = branch_name
        logger.info(f"Branch context set: {branch_name} ({branch_id})")
        
        # Refresh context cache
        refresh_context_cache()
        
        # Update user's last accessed branch if applicable
        if current_user and current_user.is_authenticated:
            try:
                if hasattr(current_user, 'update_last_accessed_branch'):
                    current_user.update_last_accessed_branch(branch_id)
            except Exception as e:
                logger.debug(f"Could not update last accessed branch: {e}")

def clear_branch_context():
    """
    Clear the current branch context from session
    Used when user logs out or needs to reset
    """
    if flask_session:
        flask_session.pop('branch_uuid', None)
        flask_session.pop('branch_name', None)
        logger.debug("Branch context cleared")
        
        # Refresh context cache
        refresh_context_cache()

def get_hospital_full_details() -> Dict[str, Any]:
    """
    Get complete hospital details including logo, address, etc.
    Extends get_current_hospital() with full details for documents
    """
    from datetime import datetime, timedelta 
    # First get basic info from existing function
    basic_info = get_current_hospital()
    
    if not basic_info.get('hospital_id'):
        return {
            'hospital_id': None,
            'name': 'Healthcare Facility',
            'address': '',
            'city': '',
            'state': '',
            'pincode': '',
            'phone': '',
            'email': '',
            'gst_number': '',
            'registration_number': '',
            'logo_path': None,
            'logo_url': None
        }
    
    try:
        from app.services.database_service import get_db_session, get_entity_dict
        from app.models.master import Hospital
        import os
        
        # Check if we have cached full details
        cache_key = f'hospital_full_{basic_info["hospital_id"]}'
        if flask_session and cache_key in flask_session:
            cached_details = flask_session.get(cache_key)
            if cached_details and isinstance(cached_details, dict):
                # Check if cache is recent (within 30 minutes)
                cache_time = cached_details.get('_cache_time')
                if cache_time:
                    from datetime import datetime, timedelta
                    if datetime.now() - datetime.fromisoformat(cache_time) < timedelta(minutes=30):
                        return cached_details
        
        # Fetch full details from database
        with get_db_session(read_only=True) as db_session:
            hospital = db_session.query(Hospital).filter_by(
                hospital_id=basic_info['hospital_id'],
                is_active=True
            ).first()
            
            if hospital:
                # Convert to dict to avoid detached entity issues
                hospital_dict = get_entity_dict(hospital)
                
                # Extract from JSONB fields
                address_json = hospital_dict.get('address') or {}
                contact_json = hospital_dict.get('contact_details') or {}
                logo_json = hospital_dict.get('logo') or {}
                
                hospital_data = {
                    'hospital_id': str(hospital_dict.get('hospital_id', '')),
                    'name': hospital_dict.get('name', basic_info['hospital_name']),
                    # Address fields
                    'address': address_json.get('street', ''),
                    'city': address_json.get('city', ''),
                    'state': address_json.get('state', ''),
                    'pincode': address_json.get('pincode', ''),
                    'country': address_json.get('country', 'India'),
                    # Contact fields
                    'phone': contact_json.get('phone', ''),
                    'email': contact_json.get('email', ''),
                    'website': contact_json.get('website', ''),
                    'fax': contact_json.get('fax', ''),
                    # Registration fields
                    'gst_number': hospital_dict.get('gst_registration_number', ''),
                    'registration_number': hospital_dict.get('license_no', ''),
                    'pan_number': hospital_dict.get('pan_number', ''),
                    # Logo fields - initially empty
                    'logo_path': None,
                    'logo_url': None
                }
                
                # Extract logo information from JSONB
                if logo_json:
                    # Check different possible keys in logo JSONB
                    logo_filename = (
                        logo_json.get('filename') or 
                        logo_json.get('file_name') or
                        logo_json.get('path') or
                        logo_json.get('name')
                    )
                    
                    if logo_filename:
                        # Extract just the filename if it includes path
                        if '/' in logo_filename:
                            logo_filename = logo_filename.split('/')[-1]
                        if '\\' in logo_filename:
                            logo_filename = logo_filename.split('\\')[-1]
                        
                        hospital_data['logo_path'] = logo_filename
                        logger.info(f"Found logo filename in DB: {logo_filename}")
                
                # If no logo in DB, check file system for actual file
                if not hospital_data['logo_path']:
                    logo_dir = os.path.join('app', 'static', 'uploads', 'hospital_logos', 
                                           str(hospital_data['hospital_id']))
                    
                    if os.path.exists(logo_dir):
                        # Get the first image file in the directory
                        for file in os.listdir(logo_dir):
                            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                                hospital_data['logo_path'] = file
                                logger.info(f"Found logo file in directory: {file}")
                                break
                
                # Add cache timestamp
                hospital_data['_cache_time'] = datetime.now().isoformat()
                
                # Cache in session
                if flask_session:
                    flask_session[cache_key] = hospital_data
                
                return hospital_data
        
        # Fallback using basic info
        return {
            'hospital_id': str(basic_info['hospital_id']),
            'name': basic_info['hospital_name'],
            'address': '',
            'city': '',
            'state': '',
            'pincode': '',
            'phone': '',
            'email': '',
            'gst_number': '',
            'registration_number': '',
            'logo_path': None,
            'logo_url': None
        }
            
    except Exception as e:
        logger.error(f"Error getting hospital full details: {str(e)}")
        # Return with basic info at least
        return {
            'hospital_id': str(basic_info['hospital_id']),
            'name': basic_info['hospital_name'],
            'address': '',
            'city': '',
            'state': '',
            'pincode': '',
            'phone': '',
            'email': '',
            'gst_number': '',
            'registration_number': '',
            'logo_path': None,
            'logo_url': None
        }

def get_branch_full_details() -> Dict[str, Any]:
    """
    Get complete branch details including address
    Extends get_current_branch() with full details for documents
    """
    from datetime import datetime, timedelta 
    # First get basic info from existing function
    basic_info = get_current_branch()
    
    if not basic_info.get('branch_id'):
        return {
            'branch_id': None,
            'name': basic_info.get('branch_name', 'Main Branch'),
            'address': '',
            'city': '',
            'state': '',
            'pincode': '',
            'phone': '',
            'email': ''
        }
    
    try:
        from app.services.database_service import get_db_session, get_entity_dict
        from app.models.master import Branch
        
        # Check cache first
        cache_key = f'branch_full_{basic_info["branch_id"]}'
        if flask_session and cache_key in flask_session:
            cached_details = flask_session.get(cache_key)
            if cached_details and isinstance(cached_details, dict):
                # Check cache freshness
                cache_time = cached_details.get('_cache_time')
                if cache_time:
                    from datetime import datetime, timedelta
                    if datetime.now() - datetime.fromisoformat(cache_time) < timedelta(minutes=30):
                        return cached_details
        
        with get_db_session(read_only=True) as db_session:
            branch = db_session.query(Branch).filter_by(
                branch_id=basic_info['branch_id'],
                is_active=True
            ).first()
            
            if branch:
                branch_dict = get_entity_dict(branch)
                address_json = branch_dict.get('address') or {}
                contact_json = branch_dict.get('contact_details') or {}
                
                branch_data = {
                    'branch_id': str(branch_dict.get('branch_id', '')),
                    'name': branch_dict.get('name', basic_info['branch_name']),
                    'address': address_json.get('street', ''),
                    'city': address_json.get('city', ''),
                    'state': address_json.get('state', ''),
                    'pincode': address_json.get('pincode', ''),
                    'phone': contact_json.get('phone', ''),
                    'email': contact_json.get('email', ''),
                    '_cache_time': datetime.now().isoformat()
                }
                
                # Cache in session
                if flask_session:
                    flask_session[cache_key] = branch_data
                
                return branch_data
        
        # Fallback using basic info
        return {
            'branch_id': str(basic_info['branch_id']) if basic_info['branch_id'] else None,
            'name': basic_info['branch_name'],
            'address': '',
            'city': '',
            'state': '',
            'pincode': '',
            'phone': '',
            'email': ''
        }
        
    except Exception as e:
        logger.error(f"Error getting branch full details: {str(e)}")
        # Return with basic info at least
        return {
            'branch_id': str(basic_info['branch_id']) if basic_info['branch_id'] else None,
            'name': basic_info['branch_name'],
            'address': '',
            'city': '',
            'state': '',
            'pincode': '',
            'phone': '',
            'email': ''
        }

def get_document_organization_context() -> Dict[str, Any]:
    """
    Get complete organization context specifically for documents
    Combines hospital and branch full details
    """
    hospital_data = get_hospital_full_details()
    branch_data = get_branch_full_details()
    
    return {
        'organization_name': hospital_data.get('name', 'Healthcare Facility'),
        'organization_address': hospital_data.get('address', ''),
        'organization_city': hospital_data.get('city', ''),
        'organization_state': hospital_data.get('state', ''),
        'organization_pincode': hospital_data.get('pincode', ''),
        'organization_phone': hospital_data.get('phone', ''),
        'organization_email': hospital_data.get('email', ''),
        'organization_gst': hospital_data.get('gst_number', ''),
        'organization_registration': hospital_data.get('registration_number', ''),
        'organization_logo_path': hospital_data.get('logo_path'),
        'organization_logo_url': hospital_data.get('logo_url'),
        'branch_name': branch_data.get('name', 'Main Branch'),
        'hospital': hospital_data,
        'branch': branch_data
    }

# =============================================================================
# DOCUMENT SERVICE SPECIFIC HELPERS
# =============================================================================

def get_document_context(entity_type: str = None, entity_id: str = None) -> Dict[str, Any]:
    """
    Get context specifically formatted for document generation
    Includes all necessary information for headers, footers, etc.
    """
    base_context = get_complete_context()
    
    # Add document-specific fields
    base_context.update({
        'current_datetime': datetime.now(),
        'entity_type': entity_type,
        'entity_id': entity_id,
        'print_requested_by': base_context.get('full_name', 'User'),
        'print_requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    return base_context

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_valid_uuid(value: str) -> bool:
    """
    Check if a string is a valid UUID
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False

def safe_get_context_value(context_dict: Dict, key: str, default: Any = None) -> Any:
    """
    Safely get value from context dictionary
    Handles nested keys with dot notation
    """
    try:
        keys = key.split('.')
        value = context_dict
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    except Exception:
        return default