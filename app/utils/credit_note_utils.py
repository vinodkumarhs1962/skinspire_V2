# app/utils/credit_note_utils.py
"""
Credit Note Utility Functions
Phase 1: Helper functions for credit note functionality
"""

from typing import Dict, List, Optional, Tuple
from datetime import date

def get_credit_note_config(key: str, default=None):
    """
    Helper function to get credit note configuration values
    Usage: get_credit_note_config('ENABLED', False)
    """
    from app.config import CREDIT_NOTE_CONFIG
    return CREDIT_NOTE_CONFIG.get(key, default)

def is_credit_note_enabled() -> bool:
    """Check if credit note functionality is enabled"""
    return get_credit_note_config('ENABLED', False)

def get_credit_note_reasons() -> List[Tuple[str, str]]:
    """Get list of available credit note reasons"""
    from app.config import CREDIT_NOTE_REASONS
    return CREDIT_NOTE_REASONS

def generate_credit_note_number(payment_reference: str) -> Optional[str]:
    """
    Generate credit note number from payment reference
    No database lookup required
    
    Args:
        payment_reference: Reference number of the payment
        
    Returns:
        Generated credit note number or None if auto-generation disabled
    """
    if not get_credit_note_config('AUTO_GENERATE_CREDIT_NUMBER', True):
        return None
    
    prefix = get_credit_note_config('CREDIT_NUMBER_PREFIX', 'CN')
    date_str = date.today().strftime('%Y%m%d')
    
    return f"{prefix}-{payment_reference}-{date_str}"

def validate_credit_note_config() -> bool:
    """
    Basic configuration validation
    
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    if not isinstance(get_credit_note_config('ENABLED'), bool):
        raise ValueError("CREDIT_NOTE_CONFIG.ENABLED must be boolean")
    
    if get_credit_note_config('MIN_REASON_LENGTH', 0) < 5:
        raise ValueError("MIN_REASON_LENGTH should be at least 5")
    
    max_percentage = get_credit_note_config('MAX_CREDIT_PERCENTAGE', 100)
    if not (0 < max_percentage <= 100):
        raise ValueError("MAX_CREDIT_PERCENTAGE must be between 1 and 100")
    
    return True

def get_credit_note_permission(action: str = 'CREATE') -> str:
    """
    Get required permission for credit note action
    
    Args:
        action: Action type ('CREATE', 'VIEW')
        
    Returns:
        Required permission string
    """
    permission_map = {
        'CREATE': get_credit_note_config('CREATE_PERMISSION', 'supplier.edit'),
        'VIEW': get_credit_note_config('VIEW_PERMISSION', 'supplier.view'),
    }
    return permission_map.get(action.upper(), 'supplier.view')

def format_credit_note_amount(amount: float) -> str:
    """
    Format credit note amount for display
    
    Args:
        amount: Credit note amount
        
    Returns:
        Formatted amount string
    """
    return f"₹{amount:,.2f}"

def validate_credit_amount(credit_amount: float, available_amount: float) -> Dict[str, any]:
    """
    Validate credit amount against available amount
    
    Args:
        credit_amount: Requested credit amount
        available_amount: Available amount for credit
        
    Returns:
        Dict with validation result
    """
    if credit_amount <= 0:
        return {
            'valid': False,
            'error': 'Credit amount must be greater than zero',
            'error_code': 'INVALID_AMOUNT'
        }
    
    if credit_amount > available_amount:
        return {
            'valid': False,
            'error': f'Credit amount (₹{credit_amount:.2f}) exceeds available amount (₹{available_amount:.2f})',
            'error_code': 'AMOUNT_EXCEEDS_AVAILABLE'
        }
    
    max_percentage = get_credit_note_config('MAX_CREDIT_PERCENTAGE', 100)
    if credit_amount > (available_amount * max_percentage / 100):
        return {
            'valid': False,
            'error': f'Credit amount exceeds {max_percentage}% of available amount',
            'error_code': 'EXCEEDS_MAX_PERCENTAGE'
        }
    
    return {
        'valid': True,
        'validated_amount': credit_amount
    }

def get_credit_note_description(reason_code: str, custom_reason: str = '') -> str:
    """
    Generate appropriate description for credit note
    
    Args:
        reason_code: Selected reason code
        custom_reason: Custom reason text
        
    Returns:
        Generated description
    """
    default_description = get_credit_note_config('DEFAULT_CREDIT_DESCRIPTION', 'Payment Adjustment - Credit Note')
    
    if reason_code and reason_code != 'other':
        # Convert reason code to readable format
        reason_text = reason_code.replace('_', ' ').title()
        return f"Credit Note - {reason_text}"
    elif custom_reason:
        return f"Credit Note - {custom_reason[:50]}"  # Limit length
    else:
        return default_description

def can_create_multiple_credits() -> bool:
    """Check if multiple credit notes are allowed per payment"""
    return get_credit_note_config('ALLOW_MULTIPLE_CREDITS_PER_PAYMENT', True)

def is_reason_required() -> bool:
    """Check if detailed reason is required for credit notes"""
    return get_credit_note_config('REQUIRE_REASON', True)

def get_min_reason_length() -> int:
    """Get minimum required length for credit note reason"""
    return get_credit_note_config('MIN_REASON_LENGTH', 10)

def should_show_in_payment_view() -> bool:
    """Check if credit notes should be shown in payment view"""
    return get_credit_note_config('SHOW_IN_PAYMENT_VIEW', True)

def are_partial_credits_enabled() -> bool:
    """Check if partial credit notes are enabled"""
    return get_credit_note_config('ENABLE_PARTIAL_CREDITS', True)

# Auto-validate configuration on import
try:
    validate_credit_note_config()
except Exception as e:
    import logging
    logging.warning(f"Credit note configuration warning: {e}")

# Export commonly used functions
__all__ = [
    'get_credit_note_config',
    'is_credit_note_enabled',
    'get_credit_note_reasons',
    'generate_credit_note_number',
    'validate_credit_note_config',
    'get_credit_note_permission',
    'format_credit_note_amount',
    'validate_credit_amount',
    'get_credit_note_description',
    'can_create_multiple_credits',
    'is_reason_required',
    'get_min_reason_length',
    'should_show_in_payment_view',
    'are_partial_credits_enabled'
]