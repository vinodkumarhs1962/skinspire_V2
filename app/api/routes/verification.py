# app/api/routes/verification.py

from flask import Blueprint, request, jsonify, current_app
from app.security.authorization.decorators import token_required
from app.services.verification_service import VerificationService
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
verification_api = Blueprint('verification_api', __name__)

@verification_api.route('/initiate-phone-verification', methods=['POST'])
@token_required
def initiate_phone_verification(user_id, session):
    """
    Initiate phone verification process
    
    Request body:
    {
        "phone_number": "1234567890"  # Optional, defaults to user_id
    }
    """
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        result = VerificationService.initiate_phone_verification(user_id, phone_number)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error initiating phone verification: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@verification_api.route('/initiate-email-verification', methods=['POST'])
@token_required
def initiate_email_verification(user_id, session):
    """
    Initiate email verification process
    
    Request body:
    {
        "email": "user@example.com"  # Optional, defaults to user's email
    }
    """
    try:
        data = request.get_json()
        email = data.get('email')
        
        result = VerificationService.initiate_email_verification(user_id, email)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error initiating email verification: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@verification_api.route('/verify-code', methods=['POST'])
@token_required
def verify_code(user_id, session):
    """
    Verify a verification code
    
    Request body:
    {
        "code_type": "phone|email",
        "code": "123456"
    }
    """
    try:
        data = request.get_json()
        code_type = data.get('code_type')
        code = data.get('code')
        
        if not code_type or not code:
            return jsonify({"success": False, "message": "Missing required fields"}), 400
            
        if code_type not in ['phone', 'email']:
            return jsonify({"success": False, "message": "Invalid code type"}), 400
        
        result = VerificationService.verify_code(user_id, code_type, code)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error verifying code: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@verification_api.route('/resend-verification', methods=['POST'])
@token_required
def resend_verification(user_id, session):
    """
    Resend verification code
    
    Request body:
    {
        "code_type": "phone|email"
    }
    """
    try:
        data = request.get_json()
        code_type = data.get('code_type')
        
        if not code_type:
            return jsonify({"success": False, "message": "Missing code type"}), 400
            
        if code_type not in ['phone', 'email']:
            return jsonify({"success": False, "message": "Invalid code type"}), 400
        
        result = VerificationService.resend_verification_code(user_id, code_type)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error resending verification: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@verification_api.route('/verification-status', methods=['GET'])
@token_required
def verification_status(user_id, session):
    """Get verification status for the current user"""
    try:
        result = VerificationService.get_verification_status(user_id)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting verification status: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500