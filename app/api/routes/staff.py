"""
Staff API Routes
Provides endpoints for staff-related operations
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.master import Staff
from app.models.transaction import User
from app.services.database_service import get_db_session
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
staff_api_bp = Blueprint('staff_api', __name__, url_prefix='/api/staff')


@staff_api_bp.route('/active', methods=['GET'])
@login_required
def get_active_staff():
    """
    Get list of active staff members for the current hospital
    Used for dropdowns in forms (e.g., package session completion)

    Returns:
        JSON: {
            'success': bool,
            'staff': [
                {
                    'user_id': str,
                    'staff_id': str,
                    'full_name': str,
                    'first_name': str,
                    'last_name': str,
                    'title': str,
                    'specialization': str
                },
                ...
            ]
        }
    """
    try:
        hospital_id = current_user.hospital_id
        logger.info(f"[Staff API] Fetching active staff for hospital: {hospital_id}")

        with get_db_session() as session:
            # Query staff joined with users to get active staff members
            query = session.query(Staff, User).join(
                User,
                User.entity_id == Staff.staff_id
            ).filter(
                Staff.hospital_id == hospital_id,
                Staff.is_active == True,
                Staff.is_deleted == False,
                User.is_active == True,
                User.entity_type == 'staff'
            ).order_by(Staff.first_name, Staff.last_name)

            results = query.all()

            staff_list = []
            for staff, user in results:
                staff_list.append({
                    'user_id': user.user_id,
                    'staff_id': str(staff.staff_id),
                    'full_name': staff.full_name or f"{staff.first_name} {staff.last_name}",
                    'first_name': staff.first_name,
                    'last_name': staff.last_name,
                    'title': staff.title,
                    'specialization': staff.specialization
                })

            logger.info(f"[Staff API] Found {len(staff_list)} active staff members")

            return jsonify({
                'success': True,
                'staff': staff_list
            })

    except Exception as e:
        logger.error(f"[Staff API] Error fetching active staff: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch staff list',
            'message': str(e)
        }), 500


@staff_api_bp.route('/<staff_id>', methods=['GET'])
@login_required
def get_staff_by_id(staff_id):
    """
    Get a single staff member by ID

    Args:
        staff_id: UUID of the staff member

    Returns:
        JSON: Staff details
    """
    try:
        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            staff = session.query(Staff).filter(
                Staff.staff_id == staff_id,
                Staff.hospital_id == hospital_id,
                Staff.is_deleted == False
            ).first()

            if not staff:
                return jsonify({
                    'success': False,
                    'error': 'Staff member not found'
                }), 404

            # Get associated user
            user = session.query(User).filter(
                User.entity_id == staff.staff_id,
                User.entity_type == 'staff'
            ).first()

            return jsonify({
                'success': True,
                'staff': {
                    'user_id': user.user_id if user else None,
                    'staff_id': str(staff.staff_id),
                    'full_name': staff.full_name,
                    'first_name': staff.first_name,
                    'last_name': staff.last_name,
                    'title': staff.title,
                    'specialization': staff.specialization,
                    'is_active': staff.is_active
                }
            })

    except Exception as e:
        logger.error(f"[Staff API] Error fetching staff {staff_id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch staff details',
            'message': str(e)
        }), 500
