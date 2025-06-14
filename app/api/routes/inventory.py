# app/api/routes/inventory.py
from flask import Blueprint, jsonify, request, current_app
from app.security.authorization.permission_validator import has_permission
from app.security.authorization.decorators import token_required

inventory_api_bp = Blueprint('inventory_api', __name__)

@inventory_api_bp.route('/stock', methods=['GET'])
@token_required
def get_stock(current_user, session):
    """Get current stock details with filtering options"""
    # Check permissions manually to maintain compatibility
    if not has_permission(current_user, 'inventory', 'view'):
        return jsonify({'error': 'Permission denied'}), 403
        
    try:
        from app.services.inventory_service import get_stock_details
        
        # Get filter parameters
        medicine_id = request.args.get('medicine_id')
        batch = request.args.get('batch')
        
        # Call service with session
        result = get_stock_details(
            hospital_id=current_user.hospital_id,
            medicine_id=medicine_id,
            batch=batch,
            session=session
        )
        
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting stock details: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Add more endpoints as needed