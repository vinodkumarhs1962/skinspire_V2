# app/api/routes/gl.py
from flask import Blueprint, jsonify, request, current_app
from app.security.authorization.permission_validator import has_permission, permission_required
from app.security.authorization.decorators import token_required
from flask_login import current_user

gl_api_bp = Blueprint('gl_api', __name__)

@gl_api_bp.route('/transactions', methods=['GET'])
@token_required
def get_transactions(current_user, session):
    """Get GL transactions with filtering options"""
    # Check permissions manually to maintain compatibility
    if not has_permission(current_user, 'gl', 'view'):
        return jsonify({'error': 'Permission denied'}), 403
        
    try:
        from app.services.gl_service import search_gl_transactions
        
        # Get filter parameters from query string
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        transaction_type = request.args.get('type')
        reference_id = request.args.get('reference_id')
        account_id = request.args.get('account_id')
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Call service with session
        result = search_gl_transactions(
            hospital_id=current_user.hospital_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            reference_id=reference_id,
            account_id=account_id,
            page=page,
            per_page=per_page,
            session=session
        )
        
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting GL transactions: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Add more endpoints as needed
