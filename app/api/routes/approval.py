# app/api/routes/approval.py

from flask import Blueprint, request, jsonify, current_app
from app.security.authorization.decorators import token_required, require_permission
from app.services.approval_service import ApprovalService
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
approval_api = Blueprint('approval_api', __name__)

@approval_api.route('/submit-approval-request', methods=['POST'])
@token_required
def submit_approval_request(user_id, session):
    """
    Submit staff approval request
    
    Request body:
    {
        "qualifications": "string",
        "experience": "string",
        "specialization": "string",
        "reference": "string",
        "comments": "string",
        "document_refs": {}
    }
    """
    try:
        data = request.get_json()
        
        result = ApprovalService.submit_approval_request(user_id, data)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error submitting approval request: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@approval_api.route('/pending-requests', methods=['GET'])
@token_required
@require_permission("staff_approval", "view")
def get_pending_requests(user_id, session):
    """Get all pending approval requests"""
    try:
        # Get hospital_id from query params
        hospital_id = request.args.get('hospital_id')
        
        result = ApprovalService.get_pending_requests(hospital_id)
        return jsonify({
            "success": True,
            "requests": result
        })
    
    except Exception as e:
        logger.error(f"Error getting pending requests: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@approval_api.route('/request-details/<request_id>', methods=['GET'])
@token_required
@require_permission("staff_approval", "view")
def get_request_details(user_id, session, request_id):
    """Get details of a specific approval request"""
    try:
        result = ApprovalService.get_request_details(request_id)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting request details: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@approval_api.route('/approve-request/<request_id>', methods=['POST'])
@token_required
@require_permission("staff_approval", "edit")
def approve_request(user_id, session, request_id):
    """
    Approve a staff approval request
    
    Request body:
    {
        "notes": "string"  // Optional
    }
    """
    try:
        data = request.get_json() or {}
        notes = data.get('notes')
        
        result = ApprovalService.approve_request(request_id, user_id, notes)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error approving request: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@approval_api.route('/reject-request/<request_id>', methods=['POST'])
@token_required
@require_permission("staff_approval", "edit")
def reject_request(user_id, session, request_id):
    """
    Reject a staff approval request
    
    Request body:
    {
        "notes": "string"  // Optional but recommended
    }
    """
    try:
        data = request.get_json() or {}
        notes = data.get('notes')
        
        result = ApprovalService.reject_request(request_id, user_id, notes)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error rejecting request: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500

@approval_api.route('/request-status', methods=['GET'])
@token_required
def get_request_status(user_id, session):
    """Get approval status for current user"""
    try:
        result = ApprovalService.get_request_status(user_id)
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error getting request status: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Internal server error"}), 500