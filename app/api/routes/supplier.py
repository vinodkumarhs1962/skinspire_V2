# app/api/routes/supplier.py
from flask import Blueprint, jsonify, request, current_app
from app.security.authorization.permission_validator import has_permission
from app.security.authorization.decorators import token_required

supplier_api_bp = Blueprint('supplier_api', __name__)

@supplier_api_bp.route('/suppliers', methods=['GET'])
@token_required
def get_suppliers(current_user, session):
    """Get suppliers with filtering and pagination"""
    # Check permissions manually to maintain compatibility
    if not has_permission(current_user, 'supplier', 'view'):
        return jsonify({'error': 'Permission denied'}), 403
        
    try:
        from app.services.supplier_service import search_suppliers
        
        # Get filter parameters
        name = request.args.get('name')
        category = request.args.get('category')
        gst_number = request.args.get('gst_number')
        status = request.args.get('status')
        blacklisted = request.args.get('blacklisted')
        
        if blacklisted is not None:
            blacklisted = blacklisted.lower() == 'true'
            
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Call service with session
        result = search_suppliers(
            hospital_id=current_user.hospital_id,
            name=name,
            category=category,
            gst_number=gst_number,
            status=status,
            blacklisted=blacklisted,
            page=page,
            per_page=per_page,
            session=session
        )
        
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error searching suppliers: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Add more endpoints as needed