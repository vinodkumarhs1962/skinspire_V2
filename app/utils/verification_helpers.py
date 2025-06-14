# app/utils/verification_helpers.py
import json
import logging

logger = logging.getLogger(__name__)

def get_user_verification_status(user):
    """
    Get verification status for a user
    
    Args:
        user: User object
        
    Returns:
        Dict with verification status details
    """
    try:
        # Default status
        result = {
            'phone_verified': False,
            'email_verified': False
        }
        
        # Check if user has verification_status attribute
        if user and hasattr(user, 'verification_status') and user.verification_status:
            verification_status = user.verification_status
            
            # Handle both string and dict types for verification_status
            if isinstance(verification_status, str):
                try:
                    verification_status = json.loads(verification_status)
                except (json.JSONDecodeError, TypeError):
                    verification_status = {}
            
            # Extract verification status
            phone_status = verification_status.get('phone', {})
            email_status = verification_status.get('email', {})
            
            # Check if verified, handling different formats
            if isinstance(phone_status, dict):
                result['phone_verified'] = phone_status.get('verified', False)
            
            if isinstance(email_status, dict):
                result['email_verified'] = email_status.get('verified', False)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting verification status: {str(e)}")
        return {
            'phone_verified': False,
            'email_verified': False,
            'error': str(e)
        }
