# =============================================================================
# File: app/utils/context_helpers.py
# =============================================================================

"""
Context helpers for Universal View Engine template integration
Provides the missing functions that universal_views.py needs for template context
"""

from flask import g, current_app, request
from flask_login import current_user
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

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