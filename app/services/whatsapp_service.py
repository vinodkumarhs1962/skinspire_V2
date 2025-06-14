"""
WhatsApp service for sending messages
"""
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

def send_whatsapp_message(phone_number, message):
    """
    Send a WhatsApp message to the specified phone number.
    
    Args:
        phone_number: Phone number with country code (e.g., +1234567890)
        message: Message text to send
        
    Returns:
        Boolean indicating success
    """
    try:
        # Get WhatsApp API settings from config
        api_key = current_app.config.get('WHATSAPP_API_KEY')
        api_url = current_app.config.get('WHATSAPP_API_URL')
        
        if not api_key or not api_url:
            logger.warning("WhatsApp API settings not configured")
            return False
        
        # Clean phone number
        # Remove any spaces, dashes, or parentheses
        clean_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # Ensure it starts with +
        if not clean_phone.startswith('+'):
            clean_phone = '+' + clean_phone
        
        # Prepare API request
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'phone': clean_phone,
            'message': message,
            'type': 'text'
        }
        
        # Send request to WhatsApp API
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Check response
        if response.status_code == 200:
            logger.info(f"WhatsApp message sent to {clean_phone}")
            return True
        else:
            logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}", exc_info=True)
        return False