# app/api/routes/inventory.py
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.security.authorization.permission_validator import has_permission
from app.security.authorization.decorators import token_required
from app.services.database_service import get_db_session

inventory_api_bp = Blueprint('inventory_api', __name__, url_prefix='/api/inventory')

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

@inventory_api_bp.route('/batches/<item_id>', methods=['GET'])
@login_required
def get_item_batches(item_id):
    """
    Get available batches for an item, sorted by expiry date (FIFO)
    Used for manual batch selection in invoice creation
    """
    # Check permissions manually to maintain compatibility
    if not has_permission(current_user, 'inventory', 'view'):
        return jsonify({'error': 'Permission denied'}), 403

    try:
        from app.services.inventory_service import get_available_batches_for_item
        import uuid

        # Validate item_id format
        try:
            item_uuid = uuid.UUID(item_id)
        except ValueError:
            return jsonify({'error': 'Invalid item ID format'}), 400

        # Get database session
        with get_db_session() as session:
            # Call service with session
            batches = get_available_batches_for_item(
                item_id=item_uuid,
                hospital_id=current_user.hospital_id,
                branch_id=None,  # Future: get from session
                session=session
            )

            return jsonify({
                'success': True,
                'batches': batches
            }), 200

    except ValueError as e:
        return jsonify({'error': str(e), 'success': False}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting item batches: {str(e)}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred', 'success': False}), 500

# Add more endpoints as needed