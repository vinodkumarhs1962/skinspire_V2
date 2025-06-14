# app/utils/phone_utils.py

import re
import logging

logger = logging.getLogger(__name__)

def normalize_phone_number(phone, default_country_code='+91'):
    """
    Normalize phone number to E.164 international format
    - 10-digit Indian numbers get +91 prefix
    - International numbers keep their format
    - Removes spaces and non-essential characters
    
    Args:
        phone: Raw phone number input
        default_country_code: Country code to add for local numbers
        
    Returns:
        Normalized phone number in E.164 format
    """
    try:
        # Strip all whitespace and non-essential characters
        phone = ''.join(filter(lambda c: c.isdigit() or c == '+', str(phone).strip()))
        
        # If already in international format, return as is
        if phone.startswith('+'):
            return phone
        
        # If it's a 10-digit Indian number, add country code
        if len(phone) == 10 and phone.isdigit():
            return default_country_code + phone
        
        # For other formats, just ensure it has a + prefix
        if phone.isdigit():
            return '+' + phone
            
        # If it contains invalid characters, log a warning
        logger.warning(f"Phone number contains invalid characters: {phone}")
        # Try to salvage by extracting digits and adding +
        digits_only = ''.join(filter(str.isdigit, phone))
        if digits_only:
            if len(digits_only) == 10:  # Likely Indian number
                return default_country_code + digits_only
            return '+' + digits_only
            
        # Last resort, return original
        return phone
    except Exception as e:
        logger.error(f"Error normalizing phone number: {str(e)}")
        return phone

def get_verification_number(phone):
    """
    Extract the appropriate number for verification purposes.
    For Indian SMS gateways, this is typically the last 10 digits.
    """
    try:
        # Strip to digits only
        digits_only = ''.join(filter(str.isdigit, str(phone)))
        
        # For Indian verification, use last 10 digits if available
        if len(digits_only) >= 10:
            return digits_only[-10:]
        
        # Otherwise return all available digits
        return digits_only
    except Exception as e:
        logger.error(f"Error extracting verification number: {str(e)}")
        return phone