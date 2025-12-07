"""
Staff API Routes
Provides endpoints for staff-related operations
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.master import Staff, StaffSpecialization
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
                    'staff_type': str,
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
                    'staff_type': staff.staff_type or 'staff',
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
                    'staff_type': staff.staff_type or 'staff',
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


@staff_api_bp.route('/specializations', methods=['GET'])
@login_required
def get_specializations():
    """
    Get specializations for a given staff type.

    Query params:
        - staff_type: Optional filter by staff type (doctor, nurse, therapist, etc.)
                     If not provided, returns all specializations

    Returns:
        JSON: {
            'success': bool,
            'specializations': [
                {
                    'specialization_id': str,
                    'code': str,
                    'name': str,
                    'description': str,
                    'staff_type': str
                },
                ...
            ]
        }
    """
    try:
        hospital_id = current_user.hospital_id
        staff_type = request.args.get('staff_type', None)

        logger.info(f"[Staff API] Fetching specializations for hospital: {hospital_id}, staff_type: {staff_type}")

        with get_db_session() as session:
            query = session.query(StaffSpecialization).filter(
                StaffSpecialization.hospital_id == hospital_id,
                StaffSpecialization.is_active == True,
                StaffSpecialization.is_deleted == False
            )

            # Filter by staff type if provided
            if staff_type:
                query = query.filter(
                    (StaffSpecialization.staff_type == staff_type) |
                    (StaffSpecialization.staff_type == 'all')
                )

            specializations = query.order_by(
                StaffSpecialization.display_order,
                StaffSpecialization.name
            ).all()

            spec_list = []
            for spec in specializations:
                spec_list.append({
                    'specialization_id': str(spec.specialization_id),
                    'code': spec.code,
                    'name': spec.name,
                    'description': spec.description,
                    'staff_type': spec.staff_type
                })

            logger.info(f"[Staff API] Found {len(spec_list)} specializations")

            return jsonify({
                'success': True,
                'specializations': spec_list
            })

    except Exception as e:
        logger.error(f"[Staff API] Error fetching specializations: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch specializations',
            'message': str(e)
        }), 500


@staff_api_bp.route('/specializations', methods=['POST'])
@login_required
def create_specialization():
    """
    Create a new specialization.

    Request body:
        - staff_type: Required (doctor, nurse, therapist, technician, all)
        - code: Required (unique short code)
        - name: Required (display name)
        - description: Optional
        - display_order: Optional (default 0)

    Returns:
        JSON: {
            'success': bool,
            'specialization_id': str,
            'message': str
        }
    """
    try:
        hospital_id = current_user.hospital_id
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        # Validate required fields
        if not data.get('staff_type'):
            return jsonify({'success': False, 'error': 'staff_type is required'}), 400
        if not data.get('code'):
            return jsonify({'success': False, 'error': 'code is required'}), 400
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'name is required'}), 400

        with get_db_session() as session:
            # Check for duplicate code
            existing = session.query(StaffSpecialization).filter(
                StaffSpecialization.hospital_id == hospital_id,
                StaffSpecialization.staff_type == data['staff_type'],
                StaffSpecialization.code == data['code'],
                StaffSpecialization.is_deleted == False
            ).first()

            if existing:
                return jsonify({
                    'success': False,
                    'error': f"Specialization code '{data['code']}' already exists for {data['staff_type']}"
                }), 400

            spec = StaffSpecialization(
                hospital_id=hospital_id,
                staff_type=data['staff_type'],
                code=data['code'].upper(),
                name=data['name'],
                description=data.get('description'),
                display_order=data.get('display_order', 0),
                is_active=True
            )

            session.add(spec)
            session.flush()

            spec_id = str(spec.specialization_id)

        logger.info(f"[Staff API] Created specialization: {spec_id}")

        return jsonify({
            'success': True,
            'specialization_id': spec_id,
            'message': 'Specialization created successfully'
        }), 201

    except Exception as e:
        logger.error(f"[Staff API] Error creating specialization: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to create specialization',
            'message': str(e)
        }), 500
