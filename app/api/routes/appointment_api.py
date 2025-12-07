# app/api/routes/appointment_api.py
"""
Appointment API Routes
Phase 1 of Patient Lifecycle System

Provides REST API endpoints for:
- Appointment booking (walk-in and scheduled)
- Appointment management (confirm, check-in, complete, cancel)
- Slot availability queries
- Queue management
- Doctor schedule management
"""

import uuid
import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, List, Optional

from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user, login_required
from sqlalchemy import func

from app.services.database_service import get_db_session
from app.services.appointment_service import appointment_service
from app.services.slot_generator_service import slot_generator_service
from app.models.appointment import (
    AppointmentType, DoctorSchedule, AppointmentSlot, Appointment,
    DoctorScheduleException
)
from app.models.transaction import User
from app.models.master import Staff, Patient, Branch, StaffSpecialization
from app.security.authorization.decorators import token_required
from app.services.branch_service import get_user_branch_id as get_branch_id_from_service

# Configure logger
logger = logging.getLogger(__name__)

# Create API blueprint
appointment_api_bp = Blueprint('appointment_api', __name__, url_prefix='/api/appointment')


def get_user_branch_id_safe(user_id, hospital_id):
    """
    Get the branch_id for a user using the centralized branch service.
    IMPORTANT: Call this BEFORE using the session for other DB operations
    to avoid nested session conflicts.
    """
    try:
        if user_id and hospital_id:
            return get_branch_id_from_service(user_id, hospital_id)
    except Exception as e:
        logger.warning(f"Error getting branch from service: {e}")
    return None


# =============================================================================
# SLOT AVAILABILITY ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/slots/available', methods=['GET'])
@token_required
def get_available_slots(user_id, session):
    """
    Get available appointment slots for a specific date and optional filters.

    Query params:
        - date: Required (YYYY-MM-DD)
        - branch_id: Optional
        - staff_id: Optional (doctor)
        - appointment_type_id: Optional
    """
    try:
        # Parse date
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'Date is required'}), 400

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Get user's hospital
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        hospital_id = user.hospital_id
        branch_id = request.args.get('branch_id')
        staff_id = request.args.get('staff_id')

        if branch_id:
            branch_id = uuid.UUID(branch_id)
        else:
            branch_id = get_user_branch_id_safe(user.user_id, user.hospital_id)

        if staff_id:
            staff_id = uuid.UUID(staff_id)

        # Get available slots
        slots = appointment_service.get_available_slots(
            session=session,
            branch_id=branch_id,
            target_date=target_date,
            staff_id=staff_id
        )

        # Format response
        slot_list = []
        for slot in slots:
            # Get doctor name
            doctor = session.query(Staff).filter_by(staff_id=slot.staff_id).first()
            doctor_name = f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else "Unknown"

            slot_list.append({
                'slot_id': str(slot.slot_id),
                'staff_id': str(slot.staff_id),
                'doctor_name': doctor_name,
                'slot_date': slot.slot_date.isoformat(),
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'available_capacity': slot.max_bookings - slot.current_bookings,
                'max_bookings': slot.max_bookings,
                'current_bookings': slot.current_bookings
            })

        return jsonify({
            'success': True,
            'date': target_date.isoformat(),
            'slots': slot_list,
            'total_available': len(slot_list)
        }), 200

    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/slots/summary', methods=['GET'])
@token_required
def get_slot_summary(user_id, session):
    """
    Get slot availability summary for a date range.

    Query params:
        - start_date: Required (YYYY-MM-DD)
        - end_date: Required (YYYY-MM-DD)
        - branch_id: Optional
        - staff_id: Optional
    """
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Get user context
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        branch_id = request.args.get('branch_id')
        if branch_id:
            branch_id = uuid.UUID(branch_id)
        else:
            branch_id = get_user_branch_id_safe(user.user_id, user.hospital_id)

        staff_id = request.args.get('staff_id')
        if staff_id:
            staff_id = uuid.UUID(staff_id)

        # Get summary
        summary = slot_generator_service.get_slot_availability_summary(
            session=session,
            branch_id=branch_id,
            start_date=start_date,
            end_date=end_date,
            staff_id=staff_id
        )

        return jsonify({
            'success': True,
            'summary': summary
        }), 200

    except Exception as e:
        logger.error(f"Error getting slot summary: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# APPOINTMENT BOOKING ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/book', methods=['POST'])
@token_required
def book_appointment(user_id, session):
    """
    Book a new appointment.

    Request body:
        - patient_id: Required
        - branch_id: Required
        - staff_id: Required (doctor)
        - slot_id: Required
        - appointment_type_id: Optional
        - chief_complaint: Optional
        - notes: Optional
        - service_id: Optional (for duration calculation)
        - package_id: Optional (for duration calculation)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate required fields
        required_fields = ['patient_id', 'branch_id', 'staff_id', 'slot_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Get user context
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Parse UUIDs
        patient_id = uuid.UUID(data['patient_id'])
        branch_id = uuid.UUID(data['branch_id'])
        staff_id = uuid.UUID(data['staff_id'])
        slot_id = uuid.UUID(data['slot_id'])

        appointment_type_id = None
        if data.get('appointment_type_id'):
            appointment_type_id = uuid.UUID(data['appointment_type_id'])

        service_id = None
        if data.get('service_id'):
            service_id = uuid.UUID(data['service_id'])

        package_id = None
        if data.get('package_id'):
            package_id = uuid.UUID(data['package_id'])

        # Book appointment
        appointment = appointment_service.book_appointment(
            session=session,
            patient_id=patient_id,
            hospital_id=user.hospital_id,
            branch_id=branch_id,
            staff_id=staff_id,
            slot_id=slot_id,
            appointment_type_id=appointment_type_id,
            chief_complaint=data.get('chief_complaint'),
            notes=data.get('notes'),
            service_id=service_id,
            package_id=package_id,
            booked_by=user_id,
            booking_source='front_desk'
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Appointment booked successfully',
            'appointment_id': str(appointment.appointment_id),
            'appointment_number': appointment.appointment_number,
            'status': appointment.status
        }), 201

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error booking appointment: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/walk-in', methods=['POST'])
@token_required
def book_walk_in(user_id, session):
    """
    Book a walk-in appointment with automatic slot assignment.

    Request body:
        - patient_id: Required
        - branch_id: Required
        - staff_id: Optional (will assign next available if not provided)
        - appointment_type_id: Optional
        - chief_complaint: Optional
        - priority: Optional (normal, urgent, emergency)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate required fields
        if not data.get('patient_id'):
            return jsonify({'error': 'patient_id is required'}), 400

        # Get user context
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Parse parameters
        patient_id = uuid.UUID(data['patient_id'])
        branch_id = uuid.UUID(data['branch_id']) if data.get('branch_id') else get_user_branch_id_safe(user.user_id, user.hospital_id)
        staff_id = uuid.UUID(data['staff_id']) if data.get('staff_id') else None

        appointment_type_id = None
        if data.get('appointment_type_id'):
            appointment_type_id = uuid.UUID(data['appointment_type_id'])

        priority = data.get('priority', 'normal')

        # Book walk-in
        appointment = appointment_service.book_walk_in(
            session=session,
            patient_id=patient_id,
            hospital_id=user.hospital_id,
            branch_id=branch_id,
            staff_id=staff_id,
            appointment_type_id=appointment_type_id,
            chief_complaint=data.get('chief_complaint'),
            priority=priority,
            booked_by=user_id
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Walk-in appointment created',
            'appointment_id': str(appointment.appointment_id),
            'appointment_number': appointment.appointment_number,
            'token_number': appointment.token_number,
            'status': appointment.status
        }), 201

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error booking walk-in: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# APPOINTMENT STATUS MANAGEMENT ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/<appointment_id>/confirm', methods=['POST'])
@token_required
def confirm_appointment(user_id, session, appointment_id):
    """Confirm a requested appointment."""
    try:
        appt_uuid = uuid.UUID(appointment_id)

        appointment = appointment_service.confirm(
            session=session,
            appointment_id=appt_uuid,
            confirmed_by=user_id
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Appointment confirmed',
            'status': appointment.status
        }), 200

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error confirming appointment: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/<appointment_id>/check-in', methods=['POST'])
@token_required
def check_in_appointment(user_id, session, appointment_id):
    """Check in a patient for their appointment."""
    try:
        appt_uuid = uuid.UUID(appointment_id)

        appointment = appointment_service.check_in(
            session=session,
            appointment_id=appt_uuid,
            checked_in_by=user_id
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Patient checked in',
            'status': appointment.status,
            'token_number': appointment.token_number,
            'checked_in_at': appointment.checked_in_at.isoformat() if appointment.checked_in_at else None
        }), 200

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error checking in: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/<appointment_id>/start', methods=['POST'])
@token_required
def start_consultation(user_id, session, appointment_id):
    """Start the consultation (doctor begins seeing the patient)."""
    try:
        appt_uuid = uuid.UUID(appointment_id)

        appointment = appointment_service.start_consultation(
            session=session,
            appointment_id=appt_uuid
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Consultation started',
            'status': appointment.status,
            'actual_start_time': appointment.actual_start_time.isoformat() if appointment.actual_start_time else None
        }), 200

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error starting consultation: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/<appointment_id>/complete', methods=['POST'])
@token_required
def complete_appointment(user_id, session, appointment_id):
    """
    Complete an appointment.

    Request body (optional):
        - notes: Completion notes
        - next_appointment_date: For follow-up scheduling
    """
    try:
        appt_uuid = uuid.UUID(appointment_id)
        data = request.get_json() or {}

        next_date = None
        if data.get('next_appointment_date'):
            next_date = datetime.strptime(data['next_appointment_date'], '%Y-%m-%d').date()

        appointment = appointment_service.complete(
            session=session,
            appointment_id=appt_uuid,
            completed_by=user_id,
            notes=data.get('notes'),
            next_appointment_date=next_date
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Appointment completed',
            'status': appointment.status,
            'actual_end_time': appointment.actual_end_time.isoformat() if appointment.actual_end_time else None
        }), 200

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error completing appointment: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/<appointment_id>/cancel', methods=['POST'])
@token_required
def cancel_appointment(user_id, session, appointment_id):
    """
    Cancel an appointment.

    Request body:
        - reason: Required - cancellation reason
    """
    try:
        appt_uuid = uuid.UUID(appointment_id)
        data = request.get_json() or {}

        reason = data.get('reason')
        if not reason:
            return jsonify({'error': 'Cancellation reason is required'}), 400

        appointment = appointment_service.cancel(
            session=session,
            appointment_id=appt_uuid,
            cancelled_by=user_id,
            reason=reason
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Appointment cancelled',
            'status': appointment.status
        }), 200

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error cancelling appointment: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/<appointment_id>/no-show', methods=['POST'])
@token_required
def mark_no_show(user_id, session, appointment_id):
    """Mark an appointment as no-show."""
    try:
        appt_uuid = uuid.UUID(appointment_id)

        appointment = appointment_service.mark_no_show(
            session=session,
            appointment_id=appt_uuid,
            marked_by=user_id
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Appointment marked as no-show',
            'status': appointment.status
        }), 200

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error marking no-show: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/<appointment_id>/reschedule', methods=['POST'])
@token_required
def reschedule_appointment(user_id, session, appointment_id):
    """
    Reschedule an appointment to a new slot.

    Request body (Option 1 - by slot ID):
        - new_slot_id: UUID of the slot to reschedule to
        - reason: Optional reason for rescheduling

    Request body (Option 2 - by date/time):
        - new_date: Date in YYYY-MM-DD format
        - new_time: Time in HH:MM format
        - staff_id: Optional - doctor UUID (keeps current if not provided)
        - reason: Optional reason for rescheduling
    """
    try:
        appt_uuid = uuid.UUID(appointment_id)
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Get current appointment
        from app.models.appointment import Appointment
        current_appointment = session.query(Appointment).filter_by(
            appointment_id=appt_uuid,
            is_deleted=False
        ).first()

        if not current_appointment:
            return jsonify({'error': 'Appointment not found'}), 404

        # Check if rescheduling is allowed
        if current_appointment.status not in ['requested', 'confirmed']:
            return jsonify({'error': f'Cannot reschedule appointment in status: {current_appointment.status}'}), 400

        # Option 1: Reschedule by slot_id
        if data.get('new_slot_id'):
            new_slot_id = uuid.UUID(data['new_slot_id'])
            appointment = appointment_service.reschedule(
                session=session,
                appointment_id=appt_uuid,
                new_slot_id=new_slot_id,
                rescheduled_by=user_id,
                reason=data.get('reason')
            )
        # Option 2: Reschedule by date/time
        elif data.get('new_date') and data.get('new_time'):
            new_date_str = data['new_date']
            new_time_str = data['new_time']

            # Parse date and time
            try:
                new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
                # Handle both HH:MM and HH:MM:SS formats
                time_format = '%H:%M:%S' if len(new_time_str) > 5 else '%H:%M'
                new_time = datetime.strptime(new_time_str, time_format).time()
            except ValueError as e:
                return jsonify({'error': f'Invalid date/time format: {str(e)}'}), 400

            # Get staff_id (use provided or keep current)
            new_staff_id = None
            if data.get('staff_id'):
                new_staff_id = uuid.UUID(data['staff_id'])
            else:
                new_staff_id = current_appointment.staff_id

            # Use the appointment service reschedule method with date/time
            new_appointment = appointment_service.reschedule(
                session=session,
                appointment_id=appt_uuid,
                new_date=new_date,
                new_time=new_time,
                new_staff_id=new_staff_id,
                reason=data.get('reason'),
                user_id=user_id
            )

            session.commit()

            return jsonify({
                'success': True,
                'message': 'Appointment rescheduled successfully',
                'new_appointment_id': str(new_appointment.appointment_id),
                'new_appointment_number': new_appointment.appointment_number,
                'new_date': new_appointment.appointment_date.isoformat(),
                'new_time': new_appointment.start_time.strftime('%H:%M')
            }), 200
        else:
            return jsonify({'error': 'Either new_slot_id OR (new_date and new_time) is required'}), 400

        session.commit()

        return jsonify({
            'success': True,
            'message': 'Appointment rescheduled',
            'new_date': appointment.appointment_date.isoformat(),
            'new_time': appointment.start_time.strftime('%H:%M')
        }), 200

    except ValueError as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        session.rollback()
        logger.error(f"Error rescheduling: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# QUEUE MANAGEMENT ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/queue/today', methods=['GET'])
@token_required
def get_todays_queue(user_id, session):
    """
    Get today's appointment queue.

    Query params:
        - branch_id: Optional
        - staff_id: Optional (filter by doctor)
        - status: Optional (filter by status)
    """
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        branch_id = request.args.get('branch_id')
        if branch_id:
            branch_id = uuid.UUID(branch_id)
        else:
            branch_id = get_user_branch_id_safe(user.user_id, user.hospital_id)

        staff_id = request.args.get('staff_id')
        if staff_id:
            staff_id = uuid.UUID(staff_id)

        status_filter = request.args.get('status')

        # Get queue
        queue = appointment_service.get_todays_queue(
            session=session,
            branch_id=branch_id,
            staff_id=staff_id
        )

        # Filter by status if specified
        if status_filter:
            queue = [a for a in queue if a.status == status_filter]

        # Format response
        queue_list = []
        for appt in queue:
            # Get patient info
            patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()
            patient_name = patient.full_name if patient else "Unknown"
            patient_phone = patient.contact_info.get('mobile') if patient and patient.contact_info else None

            # Get doctor info
            doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first() if appt.staff_id else None
            doctor_name = f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else None

            # Calculate waiting time
            waiting_minutes = None
            if appt.status == 'checked_in' and appt.checked_in_at:
                waiting_minutes = int((datetime.now(timezone.utc) - appt.checked_in_at).total_seconds() / 60)

            queue_list.append({
                'appointment_id': str(appt.appointment_id),
                'appointment_number': appt.appointment_number,
                'token_number': appt.token_number,
                'patient_id': str(appt.patient_id),
                'patient_name': patient_name,
                'patient_phone': patient_phone,
                'doctor_id': str(appt.staff_id) if appt.staff_id else None,
                'doctor_name': doctor_name,
                'appointment_time': appt.start_time.strftime('%H:%M') if appt.start_time else None,
                'status': appt.status,
                'priority': appt.priority,
                'chief_complaint': appt.chief_complaint,
                'checked_in_at': appt.checked_in_at.isoformat() if appt.checked_in_at else None,
                'waiting_minutes': waiting_minutes,
                'is_walk_in': appt.booking_source == 'walk_in',
                'is_follow_up': appt.is_follow_up
            })

        return jsonify({
            'success': True,
            'date': date.today().isoformat(),
            'queue': queue_list,
            'total': len(queue_list),
            'summary': {
                'waiting': len([a for a in queue if a.status == 'checked_in']),
                'in_progress': len([a for a in queue if a.status == 'in_progress']),
                'completed': len([a for a in queue if a.status == 'completed']),
                'pending': len([a for a in queue if a.status in ['requested', 'confirmed']])
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting queue: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/queue/waiting', methods=['GET'])
@token_required
def get_waiting_patients(user_id, session):
    """Get list of patients currently waiting (checked in but not yet seen)."""
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        branch_id = request.args.get('branch_id')
        if branch_id:
            branch_id = uuid.UUID(branch_id)
        else:
            branch_id = get_user_branch_id_safe(user.user_id, user.hospital_id)

        staff_id = request.args.get('staff_id')
        if staff_id:
            staff_id = uuid.UUID(staff_id)

        waiting = appointment_service.get_waiting_patients(
            session=session,
            branch_id=branch_id,
            staff_id=staff_id
        )

        # Format response
        waiting_list = []
        for appt in waiting:
            patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()

            waiting_minutes = 0
            if appt.checked_in_at:
                waiting_minutes = int((datetime.now(timezone.utc) - appt.checked_in_at).total_seconds() / 60)

            waiting_list.append({
                'appointment_id': str(appt.appointment_id),
                'token_number': appt.token_number,
                'patient_name': patient.full_name if patient else "Unknown",
                'priority': appt.priority,
                'checked_in_at': appt.checked_in_at.isoformat() if appt.checked_in_at else None,
                'waiting_minutes': waiting_minutes
            })

        return jsonify({
            'success': True,
            'waiting': waiting_list,
            'count': len(waiting_list)
        }), 200

    except Exception as e:
        logger.error(f"Error getting waiting patients: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/queue/next', methods=['GET'])
@token_required
def get_next_patient(user_id, session):
    """Get the next patient to be seen by a doctor."""
    try:
        staff_id = request.args.get('staff_id')
        if not staff_id:
            return jsonify({'error': 'staff_id is required'}), 400

        staff_id = uuid.UUID(staff_id)

        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        branch_id = request.args.get('branch_id')
        if branch_id:
            branch_id = uuid.UUID(branch_id)
        else:
            branch_id = get_user_branch_id_safe(user.user_id, user.hospital_id)

        next_appt = appointment_service.get_next_patient(
            session=session,
            staff_id=staff_id,
            branch_id=branch_id
        )

        if not next_appt:
            return jsonify({
                'success': True,
                'next_patient': None,
                'message': 'No patients waiting'
            }), 200

        patient = session.query(Patient).filter_by(patient_id=next_appt.patient_id).first()

        return jsonify({
            'success': True,
            'next_patient': {
                'appointment_id': str(next_appt.appointment_id),
                'token_number': next_appt.token_number,
                'patient_id': str(next_appt.patient_id),
                'patient_name': patient.full_name if patient else "Unknown",
                'chief_complaint': next_appt.chief_complaint,
                'priority': next_appt.priority,
                'checked_in_at': next_appt.checked_in_at.isoformat() if next_appt.checked_in_at else None
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting next patient: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# APPOINTMENT RETRIEVAL ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/<appointment_id>', methods=['GET'])
@token_required
def get_appointment(user_id, session, appointment_id):
    """Get appointment details by ID."""
    try:
        appt_uuid = uuid.UUID(appointment_id)

        appointment = session.query(Appointment).filter_by(
            appointment_id=appt_uuid,
            is_deleted=False
        ).first()

        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404

        # Get related entities
        patient = session.query(Patient).filter_by(patient_id=appointment.patient_id).first()
        doctor = session.query(Staff).filter_by(staff_id=appointment.staff_id).first() if appointment.staff_id else None
        appt_type = session.query(AppointmentType).filter_by(type_id=appointment.appointment_type_id).first() if appointment.appointment_type_id else None

        return jsonify({
            'success': True,
            'appointment': {
                'appointment_id': str(appointment.appointment_id),
                'appointment_number': appointment.appointment_number,
                'patient_id': str(appointment.patient_id),
                'patient_name': patient.full_name if patient else None,
                'doctor_id': str(appointment.staff_id) if appointment.staff_id else None,
                'doctor_name': f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else None,
                'appointment_type': appt_type.type_name if appt_type else None,
                'appointment_date': appointment.appointment_date.isoformat(),
                'start_time': appointment.start_time.strftime('%H:%M') if appointment.start_time else None,
                'end_time': appointment.end_time.strftime('%H:%M') if appointment.end_time else None,
                'status': appointment.status,
                'priority': appointment.priority,
                'token_number': appointment.token_number,
                'chief_complaint': appointment.chief_complaint,
                'patient_notes': appointment.patient_notes,
                'internal_notes': appointment.internal_notes,
                'is_walk_in': appointment.booking_source == 'walk_in',
                'is_follow_up': appointment.is_follow_up,
                'booking_source': appointment.booking_source,
                'checked_in_at': appointment.checked_in_at.isoformat() if appointment.checked_in_at else None,
                'actual_start_time': appointment.actual_start_time.isoformat() if appointment.actual_start_time else None,
                'actual_end_time': appointment.actual_end_time.isoformat() if appointment.actual_end_time else None,
                'created_at': appointment.created_at.isoformat() if appointment.created_at else None
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting appointment: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/patient/<patient_id>', methods=['GET'])
@token_required
def get_patient_appointments(user_id, session, patient_id):
    """Get appointments for a specific patient."""
    try:
        patient_uuid = uuid.UUID(patient_id)

        # Get optional filters
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        limit = request.args.get('limit', 50, type=int)

        query = session.query(Appointment).filter(
            Appointment.patient_id == patient_uuid,
            Appointment.is_deleted == False
        )

        if status:
            query = query.filter(Appointment.status == status)

        if from_date:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date >= from_date)

        if to_date:
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date <= to_date)

        appointments = query.order_by(
            Appointment.appointment_date.desc(),
            Appointment.start_time.desc()
        ).limit(limit).all()

        # Format response
        appt_list = []
        for appt in appointments:
            doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first() if appt.staff_id else None

            appt_list.append({
                'appointment_id': str(appt.appointment_id),
                'appointment_number': appt.appointment_number,
                'appointment_date': appt.appointment_date.isoformat(),
                'start_time': appt.start_time.strftime('%H:%M') if appt.start_time else None,
                'doctor_name': f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else None,
                'status': appt.status,
                'chief_complaint': appt.chief_complaint
            })

        return jsonify({
            'success': True,
            'patient_id': patient_id,
            'appointments': appt_list,
            'count': len(appt_list)
        }), 200

    except Exception as e:
        logger.error(f"Error getting patient appointments: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SLOT GENERATION ENDPOINTS (Admin)
# =============================================================================

@appointment_api_bp.route('/slots/generate', methods=['POST'])
@token_required
def generate_slots(user_id, session):
    """
    Generate appointment slots for doctors.

    Request body:
        - branch_id: Optional (generate for all if not specified)
        - staff_id: Optional (generate for specific doctor)
        - start_date: Optional (defaults to today)
        - end_date: Optional (defaults to 7 days from start)
        - regenerate: Optional (delete and regenerate unbooked slots)
    """
    try:
        data = request.get_json() or {}

        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Parse dates
        start_date = date.today()
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()

        end_date = start_date + timedelta(days=7)
        if data.get('end_date'):
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()

        regenerate = data.get('regenerate', False)

        branch_id = uuid.UUID(data['branch_id']) if data.get('branch_id') else get_user_branch_id_safe(user.user_id, user.hospital_id)
        staff_id = uuid.UUID(data['staff_id']) if data.get('staff_id') else None

        total_slots = 0

        if staff_id:
            # Generate for specific doctor
            slots = slot_generator_service.generate_slots_for_doctor(
                session=session,
                staff_id=staff_id,
                branch_id=branch_id,
                start_date=start_date,
                end_date=end_date,
                regenerate=regenerate
            )
            total_slots = len(slots)
        else:
            # Generate for all doctors in branch
            results = slot_generator_service.generate_slots_for_branch(
                session=session,
                branch_id=branch_id,
                start_date=start_date,
                end_date=end_date,
                regenerate=regenerate
            )
            total_slots = sum(len(slots) for slots in results.values())

        session.commit()

        return jsonify({
            'success': True,
            'message': f'Generated {total_slots} slots',
            'slots_created': total_slots,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error generating slots: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/slots/block', methods=['POST'])
@token_required
def block_slots(user_id, session):
    """
    Block slots for a doctor (e.g., for leaves or meetings).

    Request body:
        - staff_id: Required
        - branch_id: Required
        - date: Required (YYYY-MM-DD)
        - start_time: Optional (HH:MM) - if not provided, blocks all day
        - end_time: Optional (HH:MM)
        - reason: Optional
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        required = ['staff_id', 'branch_id', 'date']
        for field in required:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        staff_id = uuid.UUID(data['staff_id'])
        branch_id = uuid.UUID(data['branch_id'])
        target_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        start_time = None
        end_time = None
        if data.get('start_time') and data.get('end_time'):
            start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            end_time = datetime.strptime(data['end_time'], '%H:%M').time()

        blocked_count = slot_generator_service.block_slots(
            session=session,
            staff_id=staff_id,
            branch_id=branch_id,
            target_date=target_date,
            start_time=start_time,
            end_time=end_time,
            reason=data.get('reason', ''),
            blocked_by=uuid.UUID(user_id) if user_id else None
        )

        session.commit()

        return jsonify({
            'success': True,
            'message': f'Blocked {blocked_count} slots',
            'slots_blocked': blocked_count
        }), 200

    except Exception as e:
        session.rollback()
        logger.error(f"Error blocking slots: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# APPOINTMENT TYPE ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/types', methods=['GET'])
@token_required
def get_appointment_types(user_id, session):
    """Get list of appointment types for the hospital."""
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        types = session.query(AppointmentType).filter(
            AppointmentType.is_active == True,
            AppointmentType.is_deleted == False
        ).order_by(AppointmentType.display_order, AppointmentType.type_name).all()

        type_list = [{
            'type_id': str(t.type_id),
            'type_name': t.type_name,
            'type_code': t.type_code,
            'description': t.description,
            'default_duration_minutes': t.default_duration_minutes,
            'color_code': t.color_code,
            'requires_doctor': t.requires_doctor,
            'allow_walk_in': t.allow_walk_in,
            'allow_online_booking': t.allow_online_booking
        } for t in types]

        return jsonify({
            'success': True,
            'appointment_types': type_list
        }), 200

    except Exception as e:
        logger.error(f"Error getting appointment types: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# DOCTOR SCHEDULE ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/schedules', methods=['GET'])
@token_required
def get_doctor_schedules(user_id, session):
    """
    Get doctor schedules.

    Query params:
        - branch_id: Optional
        - staff_id: Optional (filter by specific doctor)
    """
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        branch_id = request.args.get('branch_id')
        if branch_id:
            branch_id = uuid.UUID(branch_id)
        else:
            branch_id = get_user_branch_id_safe(user.user_id, user.hospital_id)

        staff_id = request.args.get('staff_id')

        query = session.query(DoctorSchedule).filter(
            DoctorSchedule.branch_id == branch_id,
            DoctorSchedule.is_active == True,
            DoctorSchedule.is_deleted == False
        )

        if staff_id:
            query = query.filter(DoctorSchedule.staff_id == uuid.UUID(staff_id))

        schedules = query.order_by(
            DoctorSchedule.staff_id,
            DoctorSchedule.day_of_week,
            DoctorSchedule.start_time
        ).all()

        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        schedule_list = []
        for s in schedules:
            doctor = session.query(Staff).filter_by(staff_id=s.staff_id).first()

            schedule_list.append({
                'schedule_id': str(s.schedule_id),
                'staff_id': str(s.staff_id),
                'doctor_name': f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else "Unknown",
                'day_of_week': s.day_of_week,
                'day_name': day_names[s.day_of_week],
                'start_time': s.start_time.strftime('%H:%M'),
                'end_time': s.end_time.strftime('%H:%M'),
                'slot_duration_minutes': s.slot_duration_minutes,
                'max_patients_per_slot': s.max_patients_per_slot,
                'break_start': s.break_start_time.strftime('%H:%M') if s.break_start_time else None,
                'break_end': s.break_end_time.strftime('%H:%M') if s.break_end_time else None
            })

        return jsonify({
            'success': True,
            'schedules': schedule_list
        }), 200

    except Exception as e:
        logger.error(f"Error getting schedules: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/schedules', methods=['POST'])
@token_required
def create_doctor_schedule(user_id, session):
    """
    Create a new doctor schedule.

    Request body:
        - staff_id: Required
        - branch_id: Required
        - day_of_week: Required (0=Sunday to 6=Saturday)
        - start_time: Required (HH:MM)
        - end_time: Required (HH:MM)
        - slot_duration_minutes: Optional (default 15)
        - max_patients_per_slot: Optional (default 1)
        - break_start_time: Optional (HH:MM)
        - break_end_time: Optional (HH:MM)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        required = ['staff_id', 'branch_id', 'day_of_week', 'start_time', 'end_time']
        for field in required:
            if data.get(field) is None:
                return jsonify({'error': f'{field} is required'}), 400

        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Parse times
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()

        break_start = None
        break_end = None
        if data.get('break_start_time') and data.get('break_end_time'):
            break_start = datetime.strptime(data['break_start_time'], '%H:%M').time()
            break_end = datetime.strptime(data['break_end_time'], '%H:%M').time()

        schedule = DoctorSchedule(
            hospital_id=user.hospital_id,
            staff_id=uuid.UUID(data['staff_id']),
            branch_id=uuid.UUID(data['branch_id']),
            day_of_week=int(data['day_of_week']),
            start_time=start_time,
            end_time=end_time,
            slot_duration_minutes=data.get('slot_duration_minutes', 15),
            max_patients_per_slot=data.get('max_patients_per_slot', 1),
            break_start_time=break_start,
            break_end_time=break_end,
            is_active=True
        )

        session.add(schedule)
        session.commit()

        return jsonify({
            'success': True,
            'message': 'Schedule created successfully',
            'schedule_id': str(schedule.schedule_id)
        }), 201

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating schedule: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# CALENDAR EVENTS (for FullCalendar integration)
# =============================================================================

@appointment_api_bp.route('/calendar-events', methods=['GET'])
@login_required
def get_calendar_events():
    """
    Get appointments formatted for FullCalendar.

    Query params:
    - start: Start date (ISO format)
    - end: End date (ISO format)
    - staff_id: Optional filter by doctor
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user.user_id, hospital_id)

        # Parse date range
        start_str = request.args.get('start', '')
        end_str = request.args.get('end', '')
        staff_id = request.args.get('staff_id')

        # Parse dates - extract date part from ISO format strings
        # FullCalendar sends: 2025-12-15T00:00:00+05:30
        def parse_date_from_iso(date_str, default_date):
            if not date_str:
                return default_date
            try:
                # First try: split on 'T' to get just the date part
                date_part = date_str.split('T')[0]
                return datetime.strptime(date_part, '%Y-%m-%d').date()
            except (ValueError, IndexError):
                try:
                    # Fallback: try full ISO parsing
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                except ValueError:
                    return default_date

        start_date = parse_date_from_iso(start_str, date.today())
        end_date = parse_date_from_iso(end_str, date.today() + timedelta(days=7))


        with get_db_session() as session:
            # Build query
            query = session.query(Appointment).filter(
                Appointment.hospital_id == hospital_id,
                Appointment.appointment_date >= start_date,
                Appointment.appointment_date <= end_date,
                Appointment.is_deleted == False
            )

            # Apply branch filter
            if branch_id:
                query = query.filter(Appointment.branch_id == branch_id)

            # Apply staff filter
            if staff_id:
                try:
                    query = query.filter(Appointment.staff_id == uuid.UUID(staff_id))
                except ValueError:
                    pass

            # Exclude cancelled/no-show by default (optional)
            # query = query.filter(Appointment.status.notin_(['cancelled', 'no_show']))

            appointments = query.all()
            logger.info(f"[CALENDAR-EVENTS] Found {len(appointments)} appointments")

            # Format for FullCalendar
            events = []
            for appt in appointments:
                # Get patient name
                patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()
                patient_name = patient.full_name if patient else 'Unknown'

                # Get doctor name
                doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first() if appt.staff_id else None
                doctor_name = f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else 'Unassigned'

                # Create start/end datetime
                start_datetime = datetime.combine(appt.appointment_date, appt.start_time) if appt.start_time else datetime.combine(appt.appointment_date, time(9, 0))
                if appt.end_time:
                    end_datetime = datetime.combine(appt.appointment_date, appt.end_time)
                else:
                    # Default 30 min duration
                    end_datetime = start_datetime + timedelta(minutes=appt.estimated_duration_minutes or 30)

                # Determine color based on status
                color_map = {
                    'requested': '#fbbf24',
                    'confirmed': '#3b82f6',
                    'checked_in': '#a855f7',
                    'in_progress': '#f97316',
                    'completed': '#22c55e',
                    'cancelled': '#ef4444',
                    'no_show': '#6b7280',
                    'rescheduled': '#64748b'
                }

                events.append({
                    'id': str(appt.appointment_id),
                    'title': f"{patient_name} - {doctor_name}",
                    'start': start_datetime.isoformat(),
                    'end': end_datetime.isoformat(),
                    'backgroundColor': color_map.get(appt.status, '#3b82f6'),
                    'borderColor': color_map.get(appt.status, '#3b82f6'),
                    'extendedProps': {
                        'patient_id': str(appt.patient_id),
                        'patient_name': patient_name,
                        'doctor_id': str(appt.staff_id) if appt.staff_id else None,
                        'doctor_name': doctor_name,
                        'status': appt.status,
                        'priority': appt.priority,
                        'appointment_number': appt.appointment_number,
                        'token_number': appt.token_number,
                        'chief_complaint': appt.chief_complaint,
                        'is_walk_in': appt.booking_source == 'walk_in',
                        'is_follow_up': appt.is_follow_up
                    }
                })

            return jsonify({
                'success': True,
                'events': events,
                'count': len(events)
            }), 200

    except Exception as e:
        logger.error(f"Error fetching calendar events: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'events': []
        }), 500


# =============================================================================
# RESOURCE CALENDAR (Rooms, Doctors, Therapists)
# =============================================================================

@appointment_api_bp.route('/resource-calendar', methods=['GET'])
@login_required
def get_resource_calendar():
    """
    Get resources and their bookings for the resource calendar view.

    Query params:
    - date: Target date (YYYY-MM-DD)
    - type: Resource type ('room', 'doctor', 'therapist')
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user.user_id, hospital_id)

        # Parse parameters
        date_str = request.args.get('date', date.today().isoformat())
        resource_type = request.args.get('type', 'room')

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = date.today()

        with get_db_session() as session:
            from app.models.master import Room, Staff as MasterStaff, AppointmentResource

            resources = []
            bookings = []

            if resource_type == 'room':
                # Get all active rooms in branch
                rooms = session.query(Room).filter(
                    Room.branch_id == branch_id,
                    Room.is_active == True
                ).order_by(Room.room_code).all()

                for room in rooms:
                    resources.append({
                        'id': str(room.room_id),
                        'name': f"Room {room.room_code}",
                        'subtitle': room.room_type or '',
                        'type': 'room'
                    })

                # Get room bookings for this date
                room_allocations = session.query(AppointmentResource).filter(
                    AppointmentResource.resource_type == 'room',
                    AppointmentResource.allocation_date == target_date,
                    AppointmentResource.status.in_(['allocated', 'in_use'])
                ).all()

                # Helper to format time (handles both time objects and strings)
                def format_time(t, default='09:00'):
                    if t is None:
                        return default
                    if hasattr(t, 'strftime'):
                        return t.strftime('%H:%M')
                    if isinstance(t, str):
                        return t[:5]
                    return default

                for alloc in room_allocations:
                    # Get appointment details
                    appt = session.query(Appointment).filter_by(
                        appointment_id=alloc.appointment_id
                    ).first()
                    if not appt:
                        continue

                    patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()
                    doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first() if appt.staff_id else None

                    bookings.append({
                        'resource_id': str(alloc.resource_id),
                        'appointment_id': str(appt.appointment_id),
                        'patient_name': patient.full_name if patient else 'Unknown',
                        'doctor_name': f"Dr. {doctor.first_name}" if doctor else None,
                        'service_name': None,  # Could fetch if needed
                        'start_time': format_time(alloc.start_time, '09:00'),
                        'end_time': format_time(alloc.end_time, '09:30'),
                        'status': appt.status
                    })

            elif resource_type == 'doctor':
                # Get all active doctors in branch
                doctors = session.query(Staff).filter(
                    Staff.branch_id == branch_id,
                    Staff.staff_type == 'doctor',
                    Staff.is_active == True,
                    Staff.is_deleted == False
                ).order_by(Staff.first_name).all()

                for doc in doctors:
                    resources.append({
                        'id': str(doc.staff_id),
                        'name': f"Dr. {doc.first_name} {doc.last_name or ''}".strip(),
                        'subtitle': doc.specialization or '',
                        'type': 'doctor'
                    })

                # Get doctor appointments for this date
                doctor_ids = [d.staff_id for d in doctors]
                appointments = session.query(Appointment).filter(
                    Appointment.staff_id.in_(doctor_ids),
                    Appointment.appointment_date == target_date,
                    Appointment.is_deleted == False,
                    Appointment.status.notin_(['cancelled', 'no_show'])
                ).all()

                for appt in appointments:
                    patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()

                    start_time = appt.start_time.strftime('%H:%M') if appt.start_time else '09:00'
                    end_time = appt.end_time.strftime('%H:%M') if appt.end_time else '09:30'

                    bookings.append({
                        'resource_id': str(appt.staff_id),
                        'appointment_id': str(appt.appointment_id),
                        'patient_name': patient.full_name if patient else 'Unknown',
                        'doctor_name': None,
                        'service_name': None,
                        'start_time': start_time,
                        'end_time': end_time,
                        'status': appt.status
                    })

            elif resource_type == 'therapist':
                # Get all active therapists/nurses in branch
                therapists = session.query(MasterStaff).filter(
                    MasterStaff.branch_id == branch_id,
                    MasterStaff.staff_type.in_(['therapist', 'nurse', 'technician']),
                    MasterStaff.is_active == True,
                    MasterStaff.is_deleted == False
                ).order_by(MasterStaff.first_name).all()

                for ther in therapists:
                    resources.append({
                        'id': str(ther.staff_id),
                        'name': f"{ther.first_name} {ther.last_name or ''}".strip(),
                        'subtitle': ther.staff_type.title() if ther.staff_type else '',
                        'type': 'therapist'
                    })

                # Get staff allocations for this date
                staff_allocations = session.query(AppointmentResource).filter(
                    AppointmentResource.resource_type == 'staff',
                    AppointmentResource.allocation_date == target_date,
                    AppointmentResource.status.in_(['allocated', 'in_use'])
                ).all()

                for alloc in staff_allocations:
                    # Check if this staff is in our therapist list
                    if alloc.resource_id not in [t.staff_id for t in therapists]:
                        continue

                    appt = session.query(Appointment).filter_by(
                        appointment_id=alloc.appointment_id
                    ).first()
                    if not appt:
                        continue

                    patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()
                    doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first() if appt.staff_id else None

                    # Helper to format time (handles both time objects and strings)
                    def format_time_val(t, default='09:00'):
                        if t is None:
                            return default
                        if hasattr(t, 'strftime'):
                            return t.strftime('%H:%M')
                        if isinstance(t, str):
                            return t[:5]
                        return default

                    bookings.append({
                        'resource_id': str(alloc.resource_id),
                        'appointment_id': str(appt.appointment_id),
                        'patient_name': patient.full_name if patient else 'Unknown',
                        'doctor_name': f"Dr. {doctor.first_name}" if doctor else None,
                        'service_name': None,
                        'start_time': format_time_val(alloc.start_time, '09:00'),
                        'end_time': format_time_val(alloc.end_time, '09:30'),
                        'status': appt.status
                    })

            return jsonify({
                'success': True,
                'date': target_date.isoformat(),
                'resource_type': resource_type,
                'resources': resources,
                'bookings': bookings
            }), 200

    except Exception as e:
        logger.error(f"Error fetching resource calendar: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'resources': [],
            'bookings': []
        }), 500


# =============================================================================
# WEB ENDPOINTS (Session-based authentication for browser use)
# =============================================================================

@appointment_api_bp.route('/web/slots/available', methods=['GET'])
@login_required
def get_available_slots_web():
    """
    Get available appointment slots for web booking (session-based auth).

    Query params:
        - date: Required (YYYY-MM-DD)
        - staff_id: Optional (doctor) - for consultation bookings
        - service_id: Optional - for direct service bookings
        - package_plan_id: Optional - for package session bookings
        - booking_type: Optional ('consultation', 'service', 'package_session')

    Slot duration is determined by:
        - Consultation: Doctor's default slot duration
        - Service: Service's duration_minutes
        - Package: Package service's duration_minutes
    """
    logger.info(f"[SLOTS API] Request: date={request.args.get('date')}, booking_type={request.args.get('booking_type')}, service_id={request.args.get('service_id')}, staff_id={request.args.get('staff_id')}")
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user.user_id, hospital_id)

        # Parse date
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'Date is required'}), 400

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        staff_id = request.args.get('staff_id')
        service_id = request.args.get('service_id')
        package_plan_id = request.args.get('package_plan_id')
        booking_type = request.args.get('booking_type', 'consultation')

        staff_uuid = None
        if staff_id:
            try:
                staff_uuid = uuid.UUID(staff_id)
            except ValueError:
                return jsonify({'error': 'Invalid staff_id format'}), 400

        with get_db_session() as session:
            # Determine required slot duration based on booking type
            required_duration = 30  # Default for consultation

            if booking_type == 'service' and service_id:
                # Get service duration
                from app.models.master import Service
                try:
                    service_uuid = uuid.UUID(service_id)
                    service = session.query(Service).filter_by(service_id=service_uuid).first()
                    if service and service.duration_minutes:
                        required_duration = service.duration_minutes
                        logger.info(f"Service {service.service_name} requires {required_duration} minutes")
                except ValueError:
                    pass

            elif booking_type == 'package_session' and package_plan_id:
                # Get package's service duration
                from app.models.transaction import PackagePaymentPlan
                from app.models.master import Package, PackageServiceMapping, Service
                try:
                    plan_uuid = uuid.UUID(package_plan_id)
                    plan = session.query(PackagePaymentPlan).filter_by(plan_id=plan_uuid).first()
                    if plan and plan.package_id:
                        # Get first service from package to determine duration
                        mapping = session.query(PackageServiceMapping).filter_by(
                            package_id=plan.package_id
                        ).first()
                        if mapping and mapping.service_id:
                            service = session.query(Service).filter_by(service_id=mapping.service_id).first()
                            if service and service.duration_minutes:
                                required_duration = service.duration_minutes
                                logger.info(f"Package session requires {required_duration} minutes")
                except ValueError:
                    pass

            # Query available slots
            query = session.query(AppointmentSlot).filter(
                AppointmentSlot.slot_date == target_date,
                AppointmentSlot.is_available == True,
                AppointmentSlot.is_blocked == False,
                AppointmentSlot.current_bookings < AppointmentSlot.max_bookings
            )

            # Filter by branch if available
            if branch_id:
                query = query.filter(AppointmentSlot.branch_id == branch_id)

            # Filter by staff if specified (for doctor consultations)
            if staff_uuid:
                query = query.filter(AppointmentSlot.staff_id == staff_uuid)

            slots = query.order_by(AppointmentSlot.start_time).all()

            # For service/package bookings, we need to find slots that can accommodate
            # the required duration (possibly spanning multiple consecutive slots)
            slot_list = []

            if booking_type in ['service', 'package_session'] and required_duration > 15:
                # Group slots by staff to find consecutive available time blocks
                slots_by_staff = {}
                for slot in slots:
                    if slot.staff_id not in slots_by_staff:
                        slots_by_staff[slot.staff_id] = []
                    slots_by_staff[slot.staff_id].append(slot)

                # Find time blocks that can accommodate the required duration
                for staff_id_key, staff_slots in slots_by_staff.items():
                    # Sort by start time
                    staff_slots.sort(key=lambda s: s.start_time)

                    # Check for contiguous slots that add up to required duration
                    for i, slot in enumerate(staff_slots):
                        slot_start = datetime.combine(target_date, slot.start_time)
                        slot_end = datetime.combine(target_date, slot.end_time)
                        slot_duration = (slot_end - slot_start).seconds // 60

                        # Check if single slot is sufficient
                        if slot_duration >= required_duration:
                            doctor = session.query(Staff).filter_by(staff_id=slot.staff_id).first()
                            doctor_name = f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else "Therapist"

                            slot_list.append({
                                'slot_id': str(slot.slot_id),
                                'staff_id': str(slot.staff_id),
                                'doctor_name': doctor_name,
                                'slot_date': slot.slot_date.isoformat(),
                                'start_time': slot.start_time.strftime('%H:%M'),
                                'end_time': (slot_start + timedelta(minutes=required_duration)).time().strftime('%H:%M'),
                                'duration_minutes': required_duration,
                                'available_capacity': slot.max_bookings - slot.current_bookings,
                                'max_bookings': slot.max_bookings,
                                'current_bookings': slot.current_bookings
                            })
                        else:
                            # Check if we can combine with next consecutive slots
                            combined_duration = slot_duration
                            combined_slots = [slot]
                            last_end = slot_end

                            for j in range(i + 1, len(staff_slots)):
                                next_slot = staff_slots[j]
                                next_start = datetime.combine(target_date, next_slot.start_time)
                                next_end = datetime.combine(target_date, next_slot.end_time)

                                # Check if slots are consecutive (within 5 minutes)
                                if (next_start - last_end).seconds <= 300:
                                    combined_slots.append(next_slot)
                                    combined_duration += (next_end - next_start).seconds // 60
                                    last_end = next_end

                                    if combined_duration >= required_duration:
                                        break
                                else:
                                    break

                            if combined_duration >= required_duration:
                                doctor = session.query(Staff).filter_by(staff_id=slot.staff_id).first()
                                doctor_name = f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else "Therapist"

                                # Use first slot's ID but show the combined time block
                                slot_list.append({
                                    'slot_id': str(slot.slot_id),
                                    'slot_ids': [str(s.slot_id) for s in combined_slots],
                                    'staff_id': str(slot.staff_id),
                                    'doctor_name': doctor_name,
                                    'slot_date': slot.slot_date.isoformat(),
                                    'start_time': slot.start_time.strftime('%H:%M'),
                                    'end_time': (slot_start + timedelta(minutes=required_duration)).time().strftime('%H:%M'),
                                    'duration_minutes': required_duration,
                                    'available_capacity': min(s.max_bookings - s.current_bookings for s in combined_slots),
                                    'is_combined': True
                                })
            else:
                # Standard slot listing for consultations
                for slot in slots:
                    doctor = session.query(Staff).filter_by(staff_id=slot.staff_id).first()
                    doctor_name = f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else "Unknown"

                    slot_list.append({
                        'slot_id': str(slot.slot_id),
                        'staff_id': str(slot.staff_id),
                        'doctor_name': doctor_name,
                        'slot_date': slot.slot_date.isoformat(),
                        'start_time': slot.start_time.strftime('%H:%M'),
                        'end_time': slot.end_time.strftime('%H:%M'),
                        'available_capacity': slot.max_bookings - slot.current_bookings,
                        'max_bookings': slot.max_bookings,
                        'current_bookings': slot.current_bookings
                    })

            # Build response with helpful messaging
            response = {
                'success': True,
                'date': target_date.isoformat(),
                'booking_type': booking_type,
                'required_duration': required_duration,
                'slots': slot_list,
                'total_available': len(slot_list)
            }

            # Add helpful message when no slots available
            if len(slot_list) == 0:
                day_of_week = target_date.weekday()  # 0=Monday, 6=Sunday
                day_name = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week]

                # Check if it's a weekend
                if day_of_week >= 5:  # Saturday or Sunday
                    response['no_slots_reason'] = f'{day_name} - No clinic schedule on weekends'
                else:
                    # Check if any doctor has schedule on this day
                    doctor_schedules = session.query(DoctorSchedule).filter(
                        DoctorSchedule.day_of_week == day_of_week,
                        DoctorSchedule.is_active == True
                    ).count()

                    if doctor_schedules == 0:
                        response['no_slots_reason'] = f'No doctor schedule configured for {day_name}'
                    elif staff_uuid:
                        # Check if specific doctor works on this day
                        doctor_has_schedule = session.query(DoctorSchedule).filter(
                            DoctorSchedule.staff_id == staff_uuid,
                            DoctorSchedule.day_of_week == day_of_week,
                            DoctorSchedule.is_active == True
                        ).count() > 0

                        if not doctor_has_schedule:
                            response['no_slots_reason'] = f'Selected doctor does not work on {day_name}'
                        else:
                            response['no_slots_reason'] = f'All slots are booked for {day_name}'
                    else:
                        response['no_slots_reason'] = f'No available slots for {day_name}'

                logger.info(f"[SLOTS API] No slots found: {response.get('no_slots_reason')}")
            else:
                logger.info(f"[SLOTS API] Found {len(slot_list)} available slots for {target_date}")

            return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error getting available slots (web): {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/web/book', methods=['POST'])
@login_required
def book_appointment_web():
    """
    Book a new appointment (session-based auth for web booking).

    Request body:
        - patient_id: Required
        - staff_id: Required (consulting doctor)
        - slot_id: Required
        - appointment_purpose: Optional ('consultation', 'service', 'package_session')
        - service_id: Optional (for service bookings)
        - package_plan_id: Optional (for package session bookings)
        - appointment_type_id: Optional
        - chief_complaint: Optional
        - notes: Optional

    Slot Blocking Logic:
        - For 'consultation': Always block doctor's slot
        - For 'service'/'package_session': Block doctor's slot ONLY if service
          has a 'doctor' in resource requirements (e.g., surgical procedures)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        # Validate required fields
        required_fields = ['patient_id', 'staff_id', 'slot_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        hospital_id = current_user.hospital_id

        # Parse UUIDs
        patient_id = uuid.UUID(data['patient_id'])
        staff_id = uuid.UUID(data['staff_id'])
        slot_id = uuid.UUID(data['slot_id'])

        # Parse optional fields
        appointment_purpose = data.get('appointment_purpose', 'consultation')
        service_id = None
        package_plan_id = None
        package_id = None

        if data.get('service_id'):
            service_id = uuid.UUID(data['service_id'])
        if data.get('package_plan_id'):
            package_plan_id = uuid.UUID(data['package_plan_id'])

        appointment_type_id = None
        if data.get('appointment_type_id'):
            appointment_type_id = uuid.UUID(data['appointment_type_id'])

        with get_db_session() as session:
            # Get slot details - use slot's branch_id to avoid nested session from branch service
            slot = session.query(AppointmentSlot).filter_by(slot_id=slot_id).first()
            if not slot:
                return jsonify({'error': 'Slot not found'}), 404

            if slot.current_bookings >= slot.max_bookings:
                return jsonify({'error': 'Slot is no longer available'}), 400

            # Use slot's branch_id directly
            branch_id = slot.branch_id

            # Calculate duration based on appointment purpose
            duration = 30  # Default for consultation
            effective_service_id = service_id  # For resource requirement check

            if appointment_purpose == 'service' and service_id:
                # Get service duration
                from app.models.master import Service
                service = session.query(Service).filter_by(service_id=service_id).first()
                if service and service.duration_minutes:
                    duration = service.duration_minutes

            elif appointment_purpose == 'package_session' and package_plan_id:
                # Get package's service duration
                from app.models.transaction import PackagePaymentPlan
                from app.models.master import Package, PackageServiceMapping, Service
                plan = session.query(PackagePaymentPlan).filter_by(plan_id=package_plan_id).first()
                if plan:
                    package_id = plan.package_id
                    # Get first service from package to determine duration
                    mapping = session.query(PackageServiceMapping).filter_by(
                        package_id=plan.package_id
                    ).first()
                    if mapping and mapping.service_id:
                        effective_service_id = mapping.service_id
                        service = session.query(Service).filter_by(service_id=mapping.service_id).first()
                        if service and service.duration_minutes:
                            duration = service.duration_minutes

            elif appointment_type_id:
                appt_type = session.query(AppointmentType).filter_by(type_id=appointment_type_id).first()
                if appt_type and appt_type.default_duration_minutes:
                    duration = appt_type.default_duration_minutes

            end_time = (datetime.combine(slot.slot_date, slot.start_time) + timedelta(minutes=duration)).time()

            # Determine if we should block doctor's slot
            should_block_doctor_slot = True  # Default for consultations

            if appointment_purpose in ('service', 'package_session') and effective_service_id:
                # Check if service requires a doctor in resource requirements
                from app.models.master import ServiceResourceRequirement
                doctor_requirement = session.query(ServiceResourceRequirement).filter(
                    ServiceResourceRequirement.service_id == effective_service_id,
                    ServiceResourceRequirement.resource_type == 'staff',
                    ServiceResourceRequirement.staff_type == 'doctor',
                    ServiceResourceRequirement.is_active == True
                ).first()

                # Only block doctor's slot if service explicitly requires a doctor
                should_block_doctor_slot = doctor_requirement is not None
                logger.info(f"Service {effective_service_id} requires doctor: {should_block_doctor_slot}")

            # Create appointment
            appointment = Appointment(
                patient_id=patient_id,
                staff_id=staff_id,
                branch_id=branch_id,
                hospital_id=hospital_id,
                slot_id=slot_id if should_block_doctor_slot else None,  # Only link to slot if blocking
                appointment_type_id=appointment_type_id,
                service_id=service_id,
                package_id=package_id,
                package_plan_id=package_plan_id,
                appointment_purpose=appointment_purpose,
                appointment_date=slot.slot_date,
                start_time=slot.start_time,
                end_time=end_time,
                estimated_duration_minutes=duration,
                status='confirmed',  # Auto-confirm front desk bookings
                booking_source='front_desk',
                chief_complaint=data.get('chief_complaint'),
                patient_notes=data.get('notes'),
                created_by=str(current_user.user_id),
                updated_by=str(current_user.user_id)
            )

            session.add(appointment)
            session.flush()  # Get appointment_id and appointment_number

            # Update slot booking count only if we're blocking the doctor's slot
            if should_block_doctor_slot:
                slot.current_bookings += 1
                logger.info(f"Blocked doctor's slot {slot_id} for appointment {appointment.appointment_id}")
            else:
                logger.info(f"Doctor's slot NOT blocked for service appointment {appointment.appointment_id}")

            # Store values before commit
            appt_id = str(appointment.appointment_id)
            appt_number = appointment.appointment_number
            appt_status = appointment.status
            appt_date = appointment.appointment_date.isoformat() if appointment.appointment_date else None
            appt_time = appointment.start_time.strftime('%H:%M') if appointment.start_time else None

            # Explicit commit to ensure data is saved
            session.commit()
            logger.info(f"Appointment {appt_id} committed to database successfully")

        # Return after commit
        return jsonify({
            'success': True,
            'message': 'Appointment booked successfully',
            'appointment_id': appt_id,
            'appointment_number': appt_number,
            'appointment_date': appt_date,
            'appointment_time': appt_time,
            'status': appt_status,
            'doctor_slot_blocked': should_block_doctor_slot
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error booking appointment (web): {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/web/types', methods=['GET'])
@login_required
def get_appointment_types_web():
    """Get list of appointment types (session-based auth)."""
    try:
        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            types = session.query(AppointmentType).filter(
                AppointmentType.is_active == True,
                AppointmentType.is_deleted == False
            ).order_by(AppointmentType.display_order, AppointmentType.type_name).all()

            type_list = [{
                'type_id': str(t.type_id),
                'type_name': t.type_name,
                'type_code': t.type_code,
                'description': t.description,
                'default_duration_minutes': t.default_duration_minutes,
                'color_code': t.color_code,
                'requires_doctor': t.requires_doctor,
                'allow_walk_in': t.allow_walk_in,
                'allow_online_booking': t.allow_online_booking
            } for t in types]

            return jsonify({
                'success': True,
                'appointment_types': type_list
            }), 200

    except Exception as e:
        logger.error(f"Error getting appointment types (web): {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/web/<appointment_id>', methods=['GET'])
@login_required
def get_appointment_web(appointment_id):
    """Get appointment details by ID (session-based auth)."""
    try:
        appt_uuid = uuid.UUID(appointment_id)

        with get_db_session() as session:
            appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not appointment:
                return jsonify({'error': 'Appointment not found'}), 404

            # Get related entities
            patient = session.query(Patient).filter_by(patient_id=appointment.patient_id).first()
            doctor = session.query(Staff).filter_by(staff_id=appointment.staff_id).first() if appointment.staff_id else None
            appt_type = session.query(AppointmentType).filter_by(type_id=appointment.appointment_type_id).first() if appointment.appointment_type_id else None
            patient_mrn = patient.mrn if patient else None

            # Get service and package info
            from app.models.master import Service, Package
            service = None
            package = None
            service_name = None
            package_name = None
            service_duration = None

            if hasattr(appointment, 'service_id') and appointment.service_id:
                service = session.query(Service).filter_by(service_id=appointment.service_id).first()
                if service:
                    service_name = service.service_name
                    service_duration = service.duration_minutes

            if hasattr(appointment, 'package_id') and appointment.package_id:
                package = session.query(Package).filter_by(package_id=appointment.package_id).first()
                if package:
                    package_name = package.package_name

            # Get room and therapist info
            from app.models.master import Room
            room = None
            room_name = None
            therapist = None
            therapist_name = None

            if appointment.room_id:
                room = session.query(Room).filter_by(room_id=appointment.room_id).first()
                if room:
                    room_name = room.room_name

            if appointment.therapist_id:
                therapist = session.query(Staff).filter_by(staff_id=appointment.therapist_id).first()
                if therapist:
                    therapist_name = f"{therapist.first_name} {therapist.last_name or ''}".strip()

            return jsonify({
                'success': True,
                'appointment': {
                    'appointment_id': str(appointment.appointment_id),
                    'appointment_number': appointment.appointment_number,
                    'patient_id': str(appointment.patient_id),
                    'patient_name': patient.full_name if patient else None,
                    'patient_mrn': patient_mrn,
                    # Staff/Doctor info
                    'staff_id': str(appointment.staff_id) if appointment.staff_id else None,
                    'doctor_id': str(appointment.staff_id) if appointment.staff_id else None,  # Alias for compatibility
                    'doctor_name': f"Dr. {doctor.first_name} {doctor.last_name or ''}".strip() if doctor else None,
                    'doctor_specialization': doctor.specialization if doctor else None,
                    # Room info
                    'room_id': str(appointment.room_id) if appointment.room_id else None,
                    'room_name': room_name,
                    # Therapist info
                    'therapist_id': str(appointment.therapist_id) if appointment.therapist_id else None,
                    'therapist_name': therapist_name,
                    # Appointment details
                    'appointment_type': appt_type.type_name if appt_type else None,
                    'appointment_date': appointment.appointment_date.isoformat(),
                    'start_time': appointment.start_time.strftime('%H:%M') if appointment.start_time else None,
                    'end_time': appointment.end_time.strftime('%H:%M') if appointment.end_time else None,
                    'status': appointment.status,
                    'priority': appointment.priority,
                    'token_number': appointment.token_number,
                    'chief_complaint': appointment.chief_complaint,
                    'patient_notes': appointment.patient_notes,
                    'internal_notes': appointment.internal_notes,
                    'is_walk_in': appointment.booking_source == 'walk_in',
                    'is_follow_up': appointment.is_follow_up,
                    'booking_source': appointment.booking_source,
                    # Service/Package info
                    'service_id': str(appointment.service_id) if appointment.service_id else None,
                    'service_name': service_name,
                    'service_duration': service_duration,
                    'package_id': str(appointment.package_id) if appointment.package_id else None,
                    'package_name': package_name,
                    'appointment_purpose': getattr(appointment, 'appointment_purpose', 'consultation')
                }
            }), 200

    except Exception as e:
        logger.error(f"Error getting appointment (web): {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _handle_reschedule_web(appointment_id):
    """
    Internal helper function to handle reschedule action.
    Called from update_appointment_status_web when action='reschedule'.

    Checks:
    1. Doctor/Staff availability at the new time
    2. Room availability if room is allocated
    3. Staff resource availability for allocated staff
    """
    try:
        appt_uuid = uuid.UUID(appointment_id)
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        if not data.get('new_date') or not data.get('new_time'):
            return jsonify({'success': False, 'error': 'new_date and new_time are required'}), 400

        # Parse date and time outside context manager
        try:
            new_date_str = data['new_date']
            new_time_str = data['new_time']
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            time_format = '%H:%M:%S' if len(new_time_str) > 5 else '%H:%M'
            new_time = datetime.strptime(new_time_str, time_format).time()
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid date/time format: {str(e)}'}), 400

        # Result variables to be set inside context manager
        result_data = None
        result_status = None
        gcal_push_needed = False  # Flag to trigger Google Calendar push after session closes
        gcal_appt_id = None

        with get_db_session() as session:
            from app.models.master import AppointmentResource, Room, Staff as MasterStaff
            from sqlalchemy import not_, or_

            # Get current appointment
            current_appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not current_appointment:
                result_data = {'success': False, 'error': 'Appointment not found'}
                result_status = 404
            elif current_appointment.status not in ['requested', 'confirmed', 'checked_in']:
                result_data = {'success': False, 'error': f'Cannot reschedule appointment in status: {current_appointment.status}'}
                result_status = 400
            else:
                # Get staff_id (use provided or keep current)
                new_staff_id = current_appointment.staff_id
                if data.get('staff_id'):
                    new_staff_id = uuid.UUID(data['staff_id'])

                # Calculate end time based on duration
                duration = current_appointment.estimated_duration_minutes or 30
                end_time = (datetime.combine(new_date, new_time) + timedelta(minutes=duration)).time()

                # Format times for comparison
                new_start_str = new_time.strftime('%H:%M:%S')
                new_end_str = end_time.strftime('%H:%M:%S')

                # =====================================================
                # AVAILABILITY CHECKS (skip if requires_reallocation)
                # =====================================================
                unavailable_resources = []
                requires_reallocation = data.get('requires_reallocation', False)

                if not requires_reallocation:
                    # 1. Check doctor/staff availability at new time
                    if new_staff_id:
                        conflicting_appt = session.query(Appointment).filter(
                            Appointment.staff_id == new_staff_id,
                            Appointment.appointment_date == new_date,
                            Appointment.appointment_id != appt_uuid,
                            Appointment.status.notin_(['cancelled', 'no_show', 'completed']),
                            Appointment.is_deleted == False,
                            not_(
                                or_(
                                    Appointment.end_time <= new_time,
                                    Appointment.start_time >= end_time
                                )
                            )
                        ).first()

                        if conflicting_appt:
                            staff = session.query(Staff).filter_by(staff_id=new_staff_id).first()
                            staff_name = f"Dr. {staff.first_name} {staff.last_name or ''}".strip() if staff else "Selected doctor"
                            unavailable_resources.append(f"{staff_name} has another appointment at this time")

                    # 2. Get current resource allocations and check their availability
                    current_allocations = session.query(AppointmentResource).filter(
                        AppointmentResource.appointment_id == appt_uuid,
                        AppointmentResource.status.in_(['allocated', 'in_use'])
                    ).all()

                    for allocation in current_allocations:
                        conflict = session.query(AppointmentResource).filter(
                            AppointmentResource.resource_type == allocation.resource_type,
                            AppointmentResource.resource_id == allocation.resource_id,
                            AppointmentResource.allocation_date == new_date,
                            AppointmentResource.appointment_id != appt_uuid,
                            AppointmentResource.status.in_(['allocated', 'in_use']),
                            not_(
                                or_(
                                    AppointmentResource.start_time >= new_end_str,
                                    AppointmentResource.end_time <= new_start_str
                                )
                            )
                        ).first()

                        if conflict:
                            if allocation.resource_type == 'room':
                                room = session.query(Room).filter_by(room_id=allocation.resource_id).first()
                                resource_name = f"Room {room.room_code}" if room else "Allocated room"
                            else:
                                staff = session.query(MasterStaff).filter_by(staff_id=allocation.resource_id).first()
                                resource_name = f"{staff.first_name} {staff.last_name or ''}".strip() if staff else "Allocated staff"
                            unavailable_resources.append(f"{resource_name} is not available at this time")

                # If any resources are unavailable and not forcing reallocation, reject
                if unavailable_resources and not requires_reallocation:
                    result_data = {
                        'success': False,
                        'error': 'Resource availability conflict',
                        'conflicts': unavailable_resources,
                        'message': 'The following resources are not available at the requested time:\n' + '\n'.join(unavailable_resources)
                    }
                    result_status = 409
                else:
                    # =====================================================
                    # PERFORM RESCHEDULE
                    # =====================================================

                    # Get current allocations for updating
                    current_allocations = session.query(AppointmentResource).filter(
                        AppointmentResource.appointment_id == appt_uuid,
                        AppointmentResource.status.in_(['allocated', 'in_use'])
                    ).all()

                    # Find slot for the new time
                    new_slot = session.query(AppointmentSlot).filter(
                        AppointmentSlot.staff_id == new_staff_id,
                        AppointmentSlot.slot_date == new_date,
                        AppointmentSlot.start_time == new_time,
                        AppointmentSlot.is_available == True
                    ).first()

                    # Store old values for history
                    old_date = current_appointment.appointment_date
                    old_time = current_appointment.start_time
                    old_slot_id = current_appointment.slot_id

                    # Release old slot if exists
                    if old_slot_id:
                        old_slot = session.query(AppointmentSlot).filter_by(slot_id=old_slot_id).first()
                        if old_slot and old_slot.current_bookings > 0:
                            old_slot.current_bookings -= 1

                    # Update appointment
                    current_appointment.appointment_date = new_date
                    current_appointment.start_time = new_time
                    current_appointment.end_time = end_time
                    current_appointment.staff_id = new_staff_id
                    current_appointment.slot_id = new_slot.slot_id if new_slot else None
                    current_appointment.updated_by = str(current_user.user_id)

                    # Mark for reallocation if alternative slot was chosen
                    if requires_reallocation:
                        current_appointment.resource_allocation_status = 'pending'
                        # Clear current allocations for alternative slots
                        for allocation in current_allocations:
                            allocation.status = 'released'

                    # Update new slot booking count
                    if new_slot:
                        new_slot.current_bookings += 1

                    # Update resource allocations with new times (only if not requiring reallocation)
                    if not requires_reallocation:
                        for allocation in current_allocations:
                            allocation.allocation_date = new_date
                            allocation.start_time = new_start_str
                            allocation.end_time = new_end_str

                    # Add reschedule note
                    reason = data.get('reason', '')
                    reschedule_note = f"Rescheduled from {old_date} {old_time.strftime('%H:%M') if old_time else 'N/A'} to {new_date} {new_time.strftime('%H:%M')}"
                    if requires_reallocation:
                        reschedule_note += " (requires resource reallocation)"
                    if reason:
                        reschedule_note += f". Reason: {reason}"

                    if current_appointment.internal_notes:
                        current_appointment.internal_notes += f"\n{reschedule_note}"
                    else:
                        current_appointment.internal_notes = reschedule_note

                    # Store appointment_id before commit
                    appt_id_str = str(current_appointment.appointment_id)

                    session.commit()

                    logger.info(f"Appointment {appointment_id} rescheduled to {new_date} {new_time}")

                    result_data = {
                        'success': True,
                        'message': 'Appointment rescheduled successfully',
                        'appointment_id': appt_id_str,
                        'new_date': new_date.isoformat(),
                        'new_time': new_time.strftime('%H:%M'),
                        'requires_reallocation': requires_reallocation
                    }
                    result_status = 200

                    # Set flag for Google Calendar push (done after session closes)
                    gcal_push_needed = True
                    gcal_appt_id = appt_id_str

        # Push to Google Calendar AFTER session context closes
        if gcal_push_needed and gcal_appt_id:
            try:
                from app.services.google_calendar_service import google_calendar_service
                google_calendar_service.push_appointment_event(gcal_appt_id, action='update')
            except Exception as gcal_error:
                logger.warning(f"Google Calendar sync failed (non-critical): {gcal_error}")

        # Return response AFTER context manager closes
        return jsonify(result_data), result_status

    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid ID format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error rescheduling appointment (web): {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/<appointment_id>/reschedule-check', methods=['POST'])
@login_required
def reschedule_check_web(appointment_id):
    """
    Perform a simulation check for rescheduling an appointment.
    This checks availability without actually performing the reschedule.
    Also finds alternative resources when conflicts exist.

    Returns:
        - success: True/False
        - availability: {
            status: 'preferred' | 'alternative' | 'unavailable',
            conflicts: [list of conflict details with alternatives]
        }
    """
    try:
        appt_uuid = uuid.UUID(appointment_id)
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        new_date_str = data.get('new_date')
        new_time_str = data.get('new_time')

        if not new_date_str or not new_time_str:
            return jsonify({'success': False, 'error': 'new_date and new_time are required'}), 400

        # Parse date and time
        try:
            new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            time_format = '%H:%M:%S' if len(new_time_str) > 5 else '%H:%M'
            new_time = datetime.strptime(new_time_str, time_format).time()
        except ValueError as e:
            return jsonify({'success': False, 'error': f'Invalid date/time format: {str(e)}'}), 400

        with get_db_session() as session:
            from app.models.master import AppointmentResource, Room, Staff as MasterStaff, Service
            from sqlalchemy import not_, or_

            # Get current appointment
            appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not appointment:
                return jsonify({'success': False, 'error': 'Appointment not found'}), 404

            if appointment.status not in ['requested', 'confirmed', 'checked_in']:
                return jsonify({
                    'success': False,
                    'error': f'Cannot reschedule appointment in status: {appointment.status}'
                }), 400

            # Calculate end time based on duration
            duration = appointment.estimated_duration_minutes or 30
            end_time = (datetime.combine(new_date, new_time) + timedelta(minutes=duration)).time()

            # Format times for comparison
            new_start_str = new_time.strftime('%H:%M:%S')
            new_end_str = end_time.strftime('%H:%M:%S')

            branch_id = appointment.branch_id

            # Track conflicts with alternatives
            conflicts = []
            doctor_conflict = None
            room_conflicts = []
            staff_conflicts = []

            # Helper function to find busy resource IDs at a time slot
            def get_busy_resource_ids(resource_type, target_date, start_str, end_str):
                busy = session.query(AppointmentResource.resource_id).filter(
                    AppointmentResource.resource_type == resource_type,
                    AppointmentResource.allocation_date == target_date,
                    AppointmentResource.status.in_(['allocated', 'in_use']),
                    not_(
                        or_(
                            AppointmentResource.start_time >= end_str,
                            AppointmentResource.end_time <= start_str
                        )
                    )
                ).all()
                return [r[0] for r in busy]

            # Helper function to get busy doctor IDs
            def get_busy_doctor_ids(target_date, start_time, end_time):
                busy = session.query(Appointment.staff_id).filter(
                    Appointment.appointment_date == target_date,
                    Appointment.status.notin_(['cancelled', 'no_show', 'completed']),
                    Appointment.is_deleted == False,
                    Appointment.staff_id.isnot(None),
                    not_(
                        or_(
                            Appointment.end_time <= start_time,
                            Appointment.start_time >= end_time
                        )
                    )
                ).all()
                return [r[0] for r in busy]

            # 1. Check doctor/staff availability at new time
            staff_id = appointment.staff_id
            available_doctors = []
            if staff_id:
                conflicting_appt = session.query(Appointment).filter(
                    Appointment.staff_id == staff_id,
                    Appointment.appointment_date == new_date,
                    Appointment.appointment_id != appt_uuid,
                    Appointment.status.notin_(['cancelled', 'no_show', 'completed']),
                    Appointment.is_deleted == False,
                    not_(
                        or_(
                            Appointment.end_time <= new_time,
                            Appointment.start_time >= end_time
                        )
                    )
                ).first()

                if conflicting_appt:
                    current_doctor = session.query(Staff).filter_by(staff_id=staff_id).first()
                    doctor_name = f"Dr. {current_doctor.first_name} {current_doctor.last_name or ''}".strip() if current_doctor else "Doctor"

                    # Find alternative doctors available at this time
                    busy_doctor_ids = get_busy_doctor_ids(new_date, new_time, end_time)

                    # Get all active doctors in this branch
                    all_doctors = session.query(Staff).filter(
                        Staff.branch_id == branch_id,
                        Staff.staff_type == 'doctor',
                        Staff.is_active == True
                    ).all()

                    for doc in all_doctors:
                        if doc.staff_id not in busy_doctor_ids and doc.staff_id != staff_id:
                            available_doctors.append({
                                'id': str(doc.staff_id),
                                'name': f"Dr. {doc.first_name} {doc.last_name or ''}".strip(),
                                'specialization': doc.specialization
                            })

                    doctor_conflict = {
                        'type': 'doctor',
                        'current': {
                            'id': str(staff_id),
                            'name': doctor_name
                        },
                        'message': f"{doctor_name} has another appointment at this time",
                        'alternatives': available_doctors
                    }
                    conflicts.append(doctor_conflict)

            # 2. Check current resource allocations availability
            current_allocations = session.query(AppointmentResource).filter(
                AppointmentResource.appointment_id == appt_uuid,
                AppointmentResource.status.in_(['allocated', 'in_use'])
            ).all()

            for allocation in current_allocations:
                conflict_exists = session.query(AppointmentResource).filter(
                    AppointmentResource.resource_type == allocation.resource_type,
                    AppointmentResource.resource_id == allocation.resource_id,
                    AppointmentResource.allocation_date == new_date,
                    AppointmentResource.appointment_id != appt_uuid,
                    AppointmentResource.status.in_(['allocated', 'in_use']),
                    not_(
                        or_(
                            AppointmentResource.start_time >= new_end_str,
                            AppointmentResource.end_time <= new_start_str
                        )
                    )
                ).first()

                if conflict_exists:
                    if allocation.resource_type == 'room':
                        current_room = session.query(Room).filter_by(room_id=allocation.resource_id).first()
                        room_name = f"Room {current_room.room_code}" if current_room else "Allocated room"

                        # Find alternative rooms
                        busy_room_ids = get_busy_resource_ids('room', new_date, new_start_str, new_end_str)

                        # Get all active rooms in branch
                        all_rooms = session.query(Room).filter(
                            Room.branch_id == branch_id,
                            Room.is_active == True
                        ).all()

                        available_rooms = []
                        for room in all_rooms:
                            if room.room_id not in busy_room_ids:
                                available_rooms.append({
                                    'id': str(room.room_id),
                                    'name': f"Room {room.room_code}",
                                    'type': room.room_type
                                })

                        room_conflict = {
                            'type': 'room',
                            'current': {
                                'id': str(allocation.resource_id),
                                'name': room_name
                            },
                            'message': f"{room_name} is not available at this time",
                            'alternatives': available_rooms
                        }
                        conflicts.append(room_conflict)
                        room_conflicts.append(room_conflict)

                    else:  # staff resource (therapist, nurse, etc.)
                        current_staff = session.query(MasterStaff).filter_by(staff_id=allocation.resource_id).first()
                        staff_name = f"{current_staff.first_name} {current_staff.last_name or ''}".strip() if current_staff else "Staff"
                        staff_type = current_staff.staff_type if current_staff else 'therapist'

                        # Find alternative staff of same type
                        busy_staff_ids = get_busy_resource_ids('staff', new_date, new_start_str, new_end_str)

                        # Get all active staff of this type in branch
                        all_staff = session.query(MasterStaff).filter(
                            MasterStaff.branch_id == branch_id,
                            MasterStaff.staff_type == staff_type,
                            MasterStaff.is_active == True
                        ).all()

                        available_staff = []
                        for s in all_staff:
                            if s.staff_id not in busy_staff_ids and s.staff_id != allocation.resource_id:
                                available_staff.append({
                                    'id': str(s.staff_id),
                                    'name': f"{s.first_name} {s.last_name or ''}".strip(),
                                    'type': s.staff_type
                                })

                        staff_conflict = {
                            'type': 'staff',
                            'staff_type': staff_type,
                            'current': {
                                'id': str(allocation.resource_id),
                                'name': staff_name
                            },
                            'message': f"{staff_name} ({staff_type}) is not available at this time",
                            'alternatives': available_staff
                        }
                        conflicts.append(staff_conflict)
                        staff_conflicts.append(staff_conflict)

            # Determine availability status
            has_doctor_conflict = doctor_conflict is not None
            has_resource_conflicts = len(room_conflicts) > 0 or len(staff_conflicts) > 0

            # Check if alternatives exist for all conflicts
            all_have_alternatives = True
            if has_doctor_conflict and len(doctor_conflict.get('alternatives', [])) == 0:
                all_have_alternatives = False
            for rc in room_conflicts:
                if len(rc.get('alternatives', [])) == 0:
                    all_have_alternatives = False
            for sc in staff_conflicts:
                if len(sc.get('alternatives', [])) == 0:
                    all_have_alternatives = False

            if has_doctor_conflict:
                if len(available_doctors) > 0:
                    status = 'alternative'  # Can swap doctor
                else:
                    status = 'unavailable'  # No alternative doctors
            elif has_resource_conflicts:
                if all_have_alternatives:
                    status = 'alternative'  # Can reallocate resources
                else:
                    status = 'unavailable'  # No alternatives available
            else:
                status = 'preferred'  # All resources available

            # Build simple conflict messages for UI display
            conflict_messages = [c.get('message', '') for c in conflicts]

            return jsonify({
                'success': True,
                'availability': {
                    'status': status,
                    'conflicts': conflict_messages,
                    'conflict_details': conflicts  # Detailed info with alternatives
                },
                'appointment': {
                    'id': str(appointment.appointment_id),
                    'patient_name': getattr(appointment, 'patient_name', None),
                    'service_name': None,
                    'current_date': appointment.appointment_date.isoformat() if appointment.appointment_date else None,
                    'current_time': appointment.start_time.strftime('%H:%M') if appointment.start_time else None,
                    'new_date': new_date_str,
                    'new_time': new_time_str
                }
            }), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid ID format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error checking reschedule availability: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/<appointment_id>/<action>', methods=['POST'])
@login_required
def update_appointment_status_web(appointment_id, action):
    """
    Update appointment status (session-based auth).

    Actions: confirm, check_in, start, complete, cancel, no_show, reschedule
    """
    try:
        appt_uuid = uuid.UUID(appointment_id)
        valid_actions = ['confirm', 'check_in', 'start', 'complete', 'cancel', 'no_show', 'reschedule']

        if action not in valid_actions:
            return jsonify({'error': f'Invalid action. Must be one of: {valid_actions}'}), 400

        # Handle reschedule action separately - it has different parameters
        if action == 'reschedule':
            return _handle_reschedule_web(appointment_id)

        with get_db_session() as session:
            appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not appointment:
                return jsonify({'error': 'Appointment not found'}), 404

            # Status transitions
            status_map = {
                'confirm': 'confirmed',
                'check_in': 'checked_in',
                'start': 'in_progress',
                'complete': 'completed',
                'cancel': 'cancelled',
                'no_show': 'no_show'
            }

            new_status = status_map[action]
            old_status = appointment.status

            # Update status
            appointment.status = new_status
            appointment.updated_by = str(current_user.user_id)

            # Set timestamps based on action
            now = datetime.now(timezone.utc)
            if action == 'check_in':
                appointment.check_in_time = now
                # Generate token number if not exists
                if not appointment.token_number:
                    # Get max token for today
                    max_token = session.query(func.max(Appointment.token_number)).filter(
                        Appointment.branch_id == appointment.branch_id,
                        Appointment.appointment_date == appointment.appointment_date
                    ).scalar() or 0
                    appointment.token_number = max_token + 1
            elif action == 'start':
                appointment.actual_start_time = now
            elif action == 'complete':
                appointment.actual_end_time = now

            # Update slot if cancelling
            if action == 'cancel' and appointment.slot_id:
                slot = session.query(AppointmentSlot).filter_by(slot_id=appointment.slot_id).first()
                if slot and slot.current_bookings > 0:
                    slot.current_bookings -= 1

            session.flush()

            result = {
                'success': True,
                'message': f'Appointment {action.replace("_", " ")}ed successfully',
                'appointment_id': str(appointment.appointment_id),
                'old_status': old_status,
                'new_status': new_status,
                'token_number': appointment.token_number
            }

            # Determine Google Calendar action for after session closes
            gcal_action = None
            if action in ['cancel', 'no_show']:
                gcal_action = 'delete'
            elif action == 'confirm':
                gcal_action = 'create'
            else:
                gcal_action = 'update'

        # Push to Google Calendar AFTER session context closes
        if gcal_action:
            try:
                from app.services.google_calendar_service import google_calendar_service
                google_calendar_service.push_appointment_event(appointment_id, action=gcal_action)
            except Exception as gcal_error:
                logger.warning(f"Google Calendar sync failed (non-critical): {gcal_error}")

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error updating appointment status (web): {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/web/<appointment_id>/reschedule-slots', methods=['GET'])
@login_required
def get_reschedule_slots(appointment_id):
    """
    Get available time slots for rescheduling an appointment.
    Checks availability of:
    1. Doctor/Staff at new time
    2. Rooms required by service
    3. Staff resources required by service
    4. Currently allocated resources

    Query params:
        - date: Date in YYYY-MM-DD format (required)
        - staff_id: Optional - specific doctor/staff to check
    """
    try:
        appt_uuid = uuid.UUID(appointment_id)
        target_date_str = request.args.get('date')

        if not target_date_str:
            return jsonify({'success': False, 'error': 'date parameter is required'}), 400

        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        staff_id_param = request.args.get('staff_id')

        with get_db_session() as session:
            from app.models.master import AppointmentResource, Room, ServiceResourceRequirement, Service, Package, Branch
            from app.services.resource_allocation_service import resource_allocation_service
            from sqlalchemy import not_, or_

            # Get the appointment
            appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not appointment:
                return jsonify({'success': False, 'error': 'Appointment not found'}), 404

            # Determine staff to check
            check_staff_id = uuid.UUID(staff_id_param) if staff_id_param else appointment.staff_id

            # Get service info and duration
            duration = appointment.estimated_duration_minutes or 30
            service_name = None
            package_name = None
            service_requirements = {'room': [], 'staff': []}

            if appointment.service_id:
                service = session.query(Service).filter_by(service_id=appointment.service_id).first()
                if service:
                    service_name = service.service_name
                    duration = service.duration_minutes or duration
                    # Get service resource requirements
                    service_requirements = resource_allocation_service.get_service_requirements(
                        session, appointment.service_id
                    )

            if appointment.package_id:
                package = session.query(Package).filter_by(package_id=appointment.package_id).first()
                if package:
                    package_name = package.package_name

            # Get current resource allocations for this appointment
            current_allocations = session.query(AppointmentResource).filter(
                AppointmentResource.appointment_id == appt_uuid,
                AppointmentResource.status.in_(['allocated', 'in_use'])
            ).all()

            # Generate time slots for the day (e.g., 9 AM to 6 PM, every 30 mins)
            branch_start = time(9, 0)  # Default start
            branch_end = time(18, 0)   # Default end

            # Get branch operating hours from settings if available
            if appointment.branch_id:
                branch = session.query(Branch).filter_by(branch_id=appointment.branch_id).first()
                if branch and branch.settings:
                    # Operating hours might be stored in settings JSONB
                    if isinstance(branch.settings, dict):
                        opening = branch.settings.get('opening_time')
                        closing = branch.settings.get('closing_time')
                        if opening:
                            try:
                                branch_start = datetime.strptime(opening, '%H:%M').time()
                            except:
                                pass
                        if closing:
                            try:
                                branch_end = datetime.strptime(closing, '%H:%M').time()
                            except:
                                pass

            # Get staff info
            staff = session.query(Staff).filter_by(staff_id=check_staff_id).first() if check_staff_id else None
            staff_name = f"Dr. {staff.first_name} {staff.last_name or ''}".strip() if staff else None

            # Generate potential slots
            available_slots = []
            # Use service duration for slot intervals, minimum 15 mins
            slot_interval = max(15, duration) if duration else 30
            current_slot_time = datetime.combine(target_date, branch_start)
            end_datetime = datetime.combine(target_date, branch_end)

            while current_slot_time + timedelta(minutes=duration) <= end_datetime:
                slot_start = current_slot_time.time()
                slot_end = (current_slot_time + timedelta(minutes=duration)).time()
                slot_start_str = slot_start.strftime('%H:%M:%S')
                slot_end_str = slot_end.strftime('%H:%M:%S')

                # Slot status: 'preferred' (green), 'alternative' (yellow), 'unavailable' (gray)
                slot_status = 'preferred'
                unavailable_reasons = []
                resource_conflicts = []
                doctor_available = True

                # 1. Check doctor/staff availability
                if check_staff_id:
                    conflicting_appt = session.query(Appointment).filter(
                        Appointment.staff_id == check_staff_id,
                        Appointment.appointment_date == target_date,
                        Appointment.appointment_id != appt_uuid,
                        Appointment.status.notin_(['cancelled', 'no_show', 'completed']),
                        Appointment.is_deleted == False,
                        not_(
                            or_(
                                Appointment.end_time <= slot_start,
                                Appointment.start_time >= slot_end
                            )
                        )
                    ).first()

                    if conflicting_appt:
                        doctor_available = False
                        unavailable_reasons.append('Doctor busy')

                # 2. Check currently allocated resources
                for allocation in current_allocations:
                    conflict = session.query(AppointmentResource).filter(
                        AppointmentResource.resource_type == allocation.resource_type,
                        AppointmentResource.resource_id == allocation.resource_id,
                        AppointmentResource.allocation_date == target_date,
                        AppointmentResource.appointment_id != appt_uuid,
                        AppointmentResource.status.in_(['allocated', 'in_use']),
                        not_(
                            or_(
                                AppointmentResource.start_time >= slot_end_str,
                                AppointmentResource.end_time <= slot_start_str
                            )
                        )
                    ).first()

                    if conflict:
                        resource_conflicts.append(allocation.resource_type)
                        if allocation.resource_type == 'room':
                            unavailable_reasons.append('Room busy')
                        else:
                            unavailable_reasons.append('Allocated staff busy')

                # 3. Check if alternative resources are available (for service requirements)
                has_alternative_resources = False
                alternative_info = []

                if appointment.service_id and (resource_conflicts or not doctor_available):
                    # Check for alternative rooms
                    if 'room' in resource_conflicts or not current_allocations:
                        for room_req in service_requirements.get('room', []):
                            room_type = room_req.get('room_type')
                            alt_rooms = resource_allocation_service.get_available_rooms(
                                session=session,
                                branch_id=appointment.branch_id,
                                target_date=target_date,
                                start_time=slot_start,
                                end_time=slot_end,
                                room_type=room_type
                            )
                            if alt_rooms:
                                has_alternative_resources = True
                                alternative_info.append(f"{len(alt_rooms)} {room_type or 'room'}(s)")

                    # Check for alternative staff
                    if 'staff' in resource_conflicts or not current_allocations:
                        for staff_req in service_requirements.get('staff', []):
                            staff_type = staff_req.get('staff_type')
                            alt_staff = resource_allocation_service.get_available_staff(
                                session=session,
                                branch_id=appointment.branch_id,
                                hospital_id=appointment.hospital_id,
                                target_date=target_date,
                                start_time=slot_start,
                                end_time=slot_end,
                                staff_type=staff_type
                            )
                            if alt_staff:
                                has_alternative_resources = True
                                alternative_info.append(f"{len(alt_staff)} {staff_type or 'staff'}")

                    # Check for alternative doctors if current doctor is busy
                    if not doctor_available:
                        alt_doctors = session.query(Staff).filter(
                            Staff.hospital_id == appointment.hospital_id,
                            Staff.staff_type == 'doctor',
                            Staff.is_active == True,
                            Staff.is_deleted == False,
                            Staff.staff_id != check_staff_id
                        ).all()

                        available_alt_doctors = []
                        for doc in alt_doctors:
                            doc_conflict = session.query(Appointment).filter(
                                Appointment.staff_id == doc.staff_id,
                                Appointment.appointment_date == target_date,
                                Appointment.status.notin_(['cancelled', 'no_show', 'completed']),
                                Appointment.is_deleted == False,
                                not_(
                                    or_(
                                        Appointment.end_time <= slot_start,
                                        Appointment.start_time >= slot_end
                                    )
                                )
                            ).first()
                            if not doc_conflict:
                                available_alt_doctors.append(doc)

                        if available_alt_doctors:
                            has_alternative_resources = True
                            alternative_info.append(f"{len(available_alt_doctors)} other doctor(s)")

                # Determine slot status
                if doctor_available and not resource_conflicts:
                    slot_status = 'preferred'  # Green - same resources available
                elif has_alternative_resources:
                    slot_status = 'alternative'  # Yellow - needs reallocation
                else:
                    slot_status = 'unavailable'  # Gray - no options

                available_slots.append({
                    'start_time': slot_start.strftime('%H:%M'),
                    'end_time': slot_end.strftime('%H:%M'),
                    'status': slot_status,
                    'is_available': slot_status != 'unavailable',
                    'is_preferred': slot_status == 'preferred',
                    'unavailable_reasons': unavailable_reasons,
                    'alternative_info': alternative_info if slot_status == 'alternative' else []
                })

                current_slot_time += timedelta(minutes=slot_interval)

            return jsonify({
                'success': True,
                'date': target_date.isoformat(),
                'staff_id': str(check_staff_id) if check_staff_id else None,
                'staff_name': staff_name,
                'service_name': service_name,
                'package_name': package_name,
                'duration_minutes': duration,
                'slots': available_slots,
                'resource_requirements': {
                    'rooms': len(service_requirements.get('room', [])),
                    'staff': len(service_requirements.get('staff', []))
                }
            }), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error getting reschedule slots: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/doctors', methods=['GET'])
@login_required
def get_doctors_with_availability():
    """
    Get doctors with specialization and availability info for booking.

    Query params:
        - specialization: Optional filter by specialization name
        - staff_type: Optional filter for staff type (default: 'doctor')
    """
    try:
        hospital_id = current_user.hospital_id
        specialization_filter = request.args.get('specialization')
        staff_type_filter = request.args.get('staff_type', 'doctor')

        with get_db_session() as session:
            # Get all active staff of the specified type
            query = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == staff_type_filter,
                Staff.is_active == True,
                Staff.is_deleted == False
            )

            # Filter by specialization (match against staff.specialization field or linked specialization)
            if specialization_filter:
                # Join with specialization table if staff has specialization_id
                query = query.outerjoin(
                    StaffSpecialization,
                    Staff.specialization_id == StaffSpecialization.specialization_id
                ).filter(
                    (Staff.specialization == specialization_filter) |
                    (StaffSpecialization.name == specialization_filter)
                )

            doctors = query.order_by(Staff.specialization, Staff.first_name).all()

            # Get date range for availability check (today + 7 days)
            today = date.today()
            week_ahead = today + timedelta(days=7)

            # Check availability for each doctor
            doctor_list = []
            for doc in doctors:
                # Get specialization name - prefer linked specialization, fallback to staff.specialization field
                spec_name = doc.specialization or 'General'
                if doc.specialization_id:
                    linked_spec = session.query(StaffSpecialization).filter_by(
                        specialization_id=doc.specialization_id
                    ).first()
                    if linked_spec:
                        spec_name = linked_spec.name

                # Count available slots for this doctor in the next 7 days
                available_slots = session.query(func.count(AppointmentSlot.slot_id)).filter(
                    AppointmentSlot.staff_id == doc.staff_id,
                    AppointmentSlot.slot_date >= today,
                    AppointmentSlot.slot_date <= week_ahead,
                    AppointmentSlot.is_available == True,
                    AppointmentSlot.is_blocked == False,
                    AppointmentSlot.current_bookings < AppointmentSlot.max_bookings
                ).scalar() or 0

                # Check if has slots today
                slots_today = session.query(func.count(AppointmentSlot.slot_id)).filter(
                    AppointmentSlot.staff_id == doc.staff_id,
                    AppointmentSlot.slot_date == today,
                    AppointmentSlot.is_available == True,
                    AppointmentSlot.is_blocked == False,
                    AppointmentSlot.current_bookings < AppointmentSlot.max_bookings
                ).scalar() or 0

                doctor_list.append({
                    'staff_id': str(doc.staff_id),
                    'name': f"Dr. {doc.first_name} {doc.last_name or ''}".strip(),
                    'first_name': doc.first_name,
                    'last_name': doc.last_name,
                    'specialization': spec_name,
                    'specialization_id': str(doc.specialization_id) if doc.specialization_id else None,
                    'available_slots_week': available_slots,
                    'available_slots_today': slots_today,
                    'is_available_today': slots_today > 0,
                    'is_available_week': available_slots > 0
                })

            # Get specializations from lookup table for filter dropdown
            specializations = session.query(StaffSpecialization).filter(
                StaffSpecialization.hospital_id == hospital_id,
                StaffSpecialization.staff_type == staff_type_filter,
                StaffSpecialization.is_active == True,
                StaffSpecialization.is_deleted == False
            ).order_by(StaffSpecialization.display_order, StaffSpecialization.name).all()

            spec_list = [{
                'specialization_id': str(s.specialization_id),
                'code': s.code,
                'name': s.name,
                'description': s.description
            } for s in specializations]

            # Also include any unique specializations from staff records (for backward compatibility)
            staff_specs = list(set(d['specialization'] for d in doctor_list if d['specialization'] and d['specialization'] != 'General'))
            lookup_names = [s['name'] for s in spec_list]
            for spec in staff_specs:
                if spec not in lookup_names:
                    spec_list.append({
                        'specialization_id': None,
                        'code': None,
                        'name': spec,
                        'description': None
                    })

            return jsonify({
                'success': True,
                'doctors': doctor_list,
                'specializations': spec_list,
                'total': len(doctor_list)
            }), 200

    except Exception as e:
        logger.error(f"Error getting doctors with availability: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@appointment_api_bp.route('/web/patient/<patient_id>/booking-context', methods=['GET'])
@login_required
def get_patient_booking_context(patient_id):
    """
    Get comprehensive patient context for appointment booking.

    Returns:
        - Patient summary (name, phone, allergies, notes)
        - Financial summary (outstanding dues, wallet balance, loyalty points)
        - Active packages with sessions remaining
        - Follow-ups due from past consultations
        - Recent visit history (last 10)
        - Alerts (overdue payments, expiring packages, etc.)
    """
    try:
        hospital_id = current_user.hospital_id
        today = date.today()

        with get_db_session() as session:
            # 1. Get patient details
            patient = session.query(Patient).filter(
                Patient.patient_id == patient_id,
                Patient.hospital_id == hospital_id,
                Patient.is_deleted == False
            ).first()

            if not patient:
                return jsonify({'success': False, 'error': 'Patient not found'}), 404

            # Parse patient info from JSONB fields
            personal_info = patient.personal_info or {}
            contact_info = patient.contact_info or {}

            # Handle if personal_info is a string (JSON)
            if isinstance(personal_info, str):
                import json
                try:
                    personal_info = json.loads(personal_info)
                except:
                    personal_info = {}

            if isinstance(contact_info, str):
                import json
                try:
                    contact_info = json.loads(contact_info)
                except:
                    contact_info = {}

            # Get name - prefer dedicated fields, fallback to personal_info
            first_name = patient.first_name or personal_info.get('first_name', '')
            last_name = patient.last_name or personal_info.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()

            # Get contact info
            phone = contact_info.get('phone') or contact_info.get('mobile', '')
            email = contact_info.get('email', '')

            # Get date of birth
            dob_str = personal_info.get('date_of_birth') or personal_info.get('dob')
            date_of_birth = None
            if dob_str:
                try:
                    from datetime import datetime
                    if isinstance(dob_str, str):
                        date_of_birth = datetime.strptime(dob_str[:10], '%Y-%m-%d').date()
                    else:
                        date_of_birth = dob_str
                except:
                    pass

            # Get gender
            gender = personal_info.get('gender', '')

            patient_summary = {
                'patient_id': str(patient.patient_id),
                'mrn': patient.mrn,
                'full_name': full_name,
                'first_name': first_name,
                'last_name': last_name,
                'gender': gender,
                'date_of_birth': str(date_of_birth) if date_of_birth else None,
                'age': None,
                'phone': phone,
                'email': email,
                'allergies': personal_info.get('allergies') or patient.medical_info if hasattr(patient, 'medical_info') else None,
                'medical_notes': patient.medical_info if hasattr(patient, 'medical_info') else None,
                'member_since': str(patient.created_at.date()) if patient.created_at else None
            }

            # Calculate age
            if date_of_birth:
                age = today.year - date_of_birth.year
                if today.month < date_of_birth.month or (today.month == date_of_birth.month and today.day < date_of_birth.day):
                    age -= 1
                patient_summary['age'] = age

            # 2. Financial Summary
            # Get outstanding invoices
            from app.models.transaction import InvoiceHeader
            outstanding_result = session.query(
                func.coalesce(func.sum(InvoiceHeader.balance_due), 0)
            ).filter(
                InvoiceHeader.patient_id == patient_id,
                InvoiceHeader.balance_due > 0,
                InvoiceHeader.is_cancelled == False
            ).scalar()

            outstanding_amount = float(outstanding_result) if outstanding_result else 0.0

            # Get wallet balance and loyalty points from PatientLoyaltyWallet
            wallet_balance = 0.0
            loyalty_points = 0
            loyalty_tier = None
            try:
                from app.models.transaction import PatientLoyaltyWallet
                wallet = session.query(PatientLoyaltyWallet).filter(
                    PatientLoyaltyWallet.patient_id == patient_id,
                    PatientLoyaltyWallet.is_active == True
                ).first()
                if wallet:
                    # points_value is the wallet balance (1:1 ratio with points)
                    wallet_balance = float(wallet.points_value or 0)
                    loyalty_points = int(wallet.points_balance or 0)
                    # Get tier from card_type relationship if available
                    if wallet.card_type:
                        loyalty_tier = wallet.card_type.card_type_name if hasattr(wallet.card_type, 'card_type_name') else None
            except Exception as e:
                logger.debug(f"Wallet/Loyalty lookup skipped: {e}")

            financial_summary = {
                'outstanding_amount': outstanding_amount,
                'wallet_balance': wallet_balance,
                'loyalty_points': loyalty_points,
                'loyalty_tier': loyalty_tier
            }

            # 3. Active Packages with sessions remaining
            from app.models.transaction import PackagePaymentPlan
            # Note: remaining_sessions is a computed property, not a column
            # Use total_sessions > completed_sessions instead
            active_packages_query = session.query(PackagePaymentPlan).filter(
                PackagePaymentPlan.patient_id == patient_id,
                PackagePaymentPlan.status == 'active',
                PackagePaymentPlan.total_sessions > func.coalesce(PackagePaymentPlan.completed_sessions, 0)
            ).all()

            active_packages = []
            for pkg in active_packages_query:
                # Get last completed session date
                last_session_date = None
                try:
                    from app.models.transaction import PackageSession
                    last_session = session.query(PackageSession).filter(
                        PackageSession.plan_id == pkg.plan_id,
                        PackageSession.session_status == 'completed'
                    ).order_by(PackageSession.actual_completion_date.desc()).first()
                    if last_session and last_session.actual_completion_date:
                        last_session_date = last_session.actual_completion_date
                    elif last_session and last_session.session_date:
                        last_session_date = last_session.session_date
                except Exception as e:
                    logger.debug(f"Session lookup skipped: {e}")

                active_packages.append({
                    'plan_id': str(pkg.plan_id),
                    'package_name': pkg.package_name or 'Unnamed Package',
                    'package_code': pkg.package_code,
                    'total_sessions': pkg.total_sessions or 0,
                    'completed_sessions': pkg.completed_sessions or 0,
                    'remaining_sessions': pkg.remaining_sessions or 0,
                    'last_session_date': str(last_session_date) if last_session_date else None,
                    'status': pkg.status
                })

            # 4. Follow-ups Due
            # Get recent completed consultations that may need follow-up
            followups_due = []
            past_appointments = session.query(Appointment).filter(
                Appointment.patient_id == patient_id,
                Appointment.hospital_id == hospital_id,
                Appointment.status == 'completed',
                Appointment.appointment_purpose.in_(['consultation', 'procedure']),
                Appointment.is_deleted == False,
                Appointment.appointment_date >= today - timedelta(days=90)  # Last 90 days
            ).order_by(Appointment.appointment_date.desc()).limit(10).all()

            for appt in past_appointments:
                # Check if there's already a follow-up scheduled
                existing_followup = session.query(Appointment).filter(
                    Appointment.follow_up_of_consultation_id == appt.appointment_id,
                    Appointment.is_deleted == False,
                    Appointment.status.notin_(['cancelled', 'no_show'])
                ).first()

                if not existing_followup:
                    # Estimate follow-up due date (typically 2-4 weeks after)
                    followup_due_date = appt.appointment_date + timedelta(days=14)
                    is_overdue = followup_due_date < today

                    # Get doctor name
                    doctor_name = None
                    if appt.staff_id:
                        doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first()
                        if doctor:
                            doctor_name = f"Dr. {doctor.first_name} {doctor.last_name or ''}".strip()

                    followups_due.append({
                        'appointment_id': str(appt.appointment_id),
                        'appointment_date': str(appt.appointment_date),
                        'purpose': appt.appointment_purpose,
                        'chief_complaint': appt.chief_complaint,
                        'doctor_id': str(appt.staff_id) if appt.staff_id else None,
                        'doctor_name': doctor_name,
                        'followup_due_date': str(followup_due_date),
                        'is_overdue': is_overdue,
                        'days_overdue': (today - followup_due_date).days if is_overdue else 0
                    })

            # 5. Visit History (last 10)
            visit_history = []
            recent_visits = session.query(Appointment).filter(
                Appointment.patient_id == patient_id,
                Appointment.hospital_id == hospital_id,
                Appointment.status.in_(['completed', 'cancelled', 'no_show']),
                Appointment.is_deleted == False
            ).order_by(Appointment.appointment_date.desc()).limit(10).all()

            for visit in recent_visits:
                doctor_name = None
                if visit.staff_id:
                    doctor = session.query(Staff).filter_by(staff_id=visit.staff_id).first()
                    if doctor:
                        doctor_name = f"Dr. {doctor.first_name} {doctor.last_name or ''}".strip()

                # Get service/package name
                service_name = None
                if visit.service_id:
                    from app.models.master import Service
                    service = session.query(Service).filter_by(service_id=visit.service_id).first()
                    if service:
                        service_name = service.service_name
                elif visit.package_id:
                    from app.models.master import Package
                    package = session.query(Package).filter_by(package_id=visit.package_id).first()
                    if package:
                        service_name = package.package_name

                visit_history.append({
                    'appointment_id': str(visit.appointment_id),
                    'appointment_number': visit.appointment_number,
                    'date': str(visit.appointment_date),
                    'time': str(visit.start_time) if visit.start_time else None,
                    'purpose': visit.appointment_purpose or 'consultation',
                    'status': visit.status,
                    'doctor_name': doctor_name,
                    'service_name': service_name or visit.chief_complaint or 'General Consultation',
                    'booking_source': visit.booking_source
                })

            # 6. Alerts
            alerts = []

            # Outstanding payment alert
            if outstanding_amount > 0:
                alerts.append({
                    'type': 'payment_due',
                    'severity': 'warning' if outstanding_amount < 5000 else 'error',
                    'message': f'Outstanding payment: ₹{outstanding_amount:,.0f}',
                    'action': 'collect_payment'
                })

            # Overdue follow-ups
            overdue_followups = [f for f in followups_due if f['is_overdue']]
            if overdue_followups:
                alerts.append({
                    'type': 'followup_overdue',
                    'severity': 'warning',
                    'message': f'{len(overdue_followups)} follow-up(s) overdue',
                    'action': 'schedule_followup'
                })

            # Expiring packages
            expiring_packages = [p for p in active_packages if p.get('is_expiring_soon')]
            if expiring_packages:
                alerts.append({
                    'type': 'package_expiring',
                    'severity': 'info',
                    'message': f'{len(expiring_packages)} package(s) expiring soon',
                    'action': 'schedule_session'
                })

            return jsonify({
                'success': True,
                'patient': patient_summary,
                'financial': financial_summary,
                'active_packages': active_packages,
                'followups_due': followups_due,
                'visit_history': visit_history,
                'alerts': alerts
            }), 200

    except Exception as e:
        logger.error(f"Error getting patient booking context: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/services/bookable', methods=['GET'])
@login_required
def get_bookable_services():
    """
    Get services available for direct booking (no doctor consultation required).

    Query params:
        - category: Optional filter by service type/category
    """
    try:
        hospital_id = current_user.hospital_id
        category_filter = request.args.get('category')

        with get_db_session() as session:
            from app.models.master import Service

            # Note: allow_online_booking column doesn't exist yet
            # For now, return all active services. Can filter by service_type if needed.
            query = session.query(Service).filter(
                Service.hospital_id == hospital_id,
                Service.is_active == True,
                Service.is_deleted == False
            )

            if category_filter:
                query = query.filter(Service.service_type == category_filter)

            services = query.order_by(Service.service_type, Service.service_name).all()

            service_list = []
            for svc in services:
                service_list.append({
                    'service_id': str(svc.service_id),
                    'code': svc.code,
                    'name': svc.service_name,
                    'description': svc.description,
                    'category': svc.service_type,
                    'duration_minutes': svc.duration_minutes or 30,
                    'price': float(svc.price) if svc.price else 0,
                    'requires_doctor': False  # These are direct services
                })

            # Get unique categories for filter
            categories = list(set(s['category'] for s in service_list if s['category']))
            categories.sort()

            return jsonify({
                'success': True,
                'services': service_list,
                'categories': categories,
                'total': len(service_list)
            }), 200

    except Exception as e:
        logger.error(f"Error getting bookable services: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/queue', methods=['GET'])
@login_required
def get_queue_web():
    """
    Get appointment queue with optional date range (session-based auth).

    Query params:
        - range: 'today' or 'week' (default: today)
        - date: Specific date to query (YYYY-MM-DD), defaults to today
        - staff_id: Optional doctor filter
        - status: Optional status filter
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = None  # Will be determined from user if needed

        date_range = request.args.get('range', 'today')
        date_str = request.args.get('date')  # Specific date from dashboard
        staff_id = request.args.get('staff_id')
        status_filter = request.args.get('status')

        with get_db_session() as session:
            # Determine the target date - use specified date if provided
            if date_str:
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    target_date = date.today()
            else:
                target_date = date.today()

            # Calculate date range based on target date
            if date_range == 'week':
                end_date = target_date + timedelta(days=7)
            else:
                end_date = target_date

            # Build query - filter from target_date to end_date
            query = session.query(Appointment).filter(
                Appointment.hospital_id == hospital_id,
                Appointment.is_deleted == False,
                Appointment.appointment_date >= target_date,
                Appointment.appointment_date <= end_date
            )

            if staff_id:
                query = query.filter(Appointment.staff_id == uuid.UUID(staff_id))

            if status_filter:
                query = query.filter(Appointment.status == status_filter)

            # Order by date, then time
            appointments = query.order_by(
                Appointment.appointment_date,
                Appointment.start_time
            ).all()

            # Format queue items
            queue = []
            for appt in appointments:
                # Get patient info
                patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()
                patient_name = patient.full_name if patient else 'Unknown'
                patient_phone = ''
                if patient and patient.contact_info:
                    contact = patient.contact_info if isinstance(patient.contact_info, dict) else {}
                    patient_phone = contact.get('phone', '')

                # Get doctor info
                doctor_name = ''
                if appt.staff_id:
                    doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first()
                    if doctor:
                        doctor_name = f"Dr. {doctor.first_name} {doctor.last_name or ''}".strip()

                # Calculate waiting time
                waiting_minutes = None
                if appt.status == 'checked_in' and appt.check_in_time:
                    waiting_minutes = int((datetime.now(timezone.utc) - appt.check_in_time).total_seconds() / 60)

                queue.append({
                    'appointment_id': str(appt.appointment_id),
                    'appointment_number': appt.appointment_number,
                    'patient_name': patient_name,
                    'patient_phone': patient_phone,
                    'patient_mrn': patient.mrn if patient else None,
                    'doctor_name': doctor_name,
                    'appointment_date': appt.appointment_date.strftime('%Y-%m-%d'),
                    'appointment_time': appt.start_time.strftime('%H:%M') if appt.start_time else None,
                    'status': appt.status,
                    'priority': appt.priority or 'normal',
                    'token_number': appt.token_number,
                    'chief_complaint': appt.chief_complaint,
                    'is_walk_in': appt.booking_source == 'walk_in',
                    'is_follow_up': appt.is_follow_up,
                    'waiting_minutes': waiting_minutes
                })

            # Calculate summary
            summary = {
                'total': len(queue),
                'waiting': sum(1 for q in queue if q['status'] == 'checked_in'),
                'in_progress': sum(1 for q in queue if q['status'] == 'in_progress'),
                'completed': sum(1 for q in queue if q['status'] == 'completed'),
                'confirmed': sum(1 for q in queue if q['status'] == 'confirmed')
            }

            return jsonify({
                'success': True,
                'queue': queue,
                'summary': summary,
                'date_range': date_range
            }), 200

    except Exception as e:
        logger.error(f"Error getting queue (web): {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# RESOURCE MANAGEMENT ENDPOINTS
# =============================================================================

@appointment_api_bp.route('/web/rooms/available', methods=['GET'])
@login_required
def get_available_rooms():
    """
    Get available rooms for appointment booking.

    Query params:
        - date: Required (YYYY-MM-DD)
        - start_time: Required (HH:MM)
        - end_time: Required (HH:MM)
        - room_type: Optional filter by room type (procedure, ot, laser, etc.)
        - service_id: Optional - auto-detect required room type from service
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user.user_id, hospital_id)

        date_str = request.args.get('date')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        room_type_filter = request.args.get('room_type')
        service_id = request.args.get('service_id')

        with get_db_session() as session:
            from app.models.master import Room, ServiceResourceRequirement

            # If service_id provided, get required room type
            required_room_type = room_type_filter
            if service_id and not room_type_filter:
                try:
                    service_uuid = uuid.UUID(service_id)
                    room_req = session.query(ServiceResourceRequirement).filter(
                        ServiceResourceRequirement.service_id == service_uuid,
                        ServiceResourceRequirement.resource_type == 'room',
                        ServiceResourceRequirement.is_active == True
                    ).first()
                    if room_req:
                        required_room_type = room_req.room_type
                except ValueError:
                    pass

            # Query rooms
            query = session.query(Room).filter(
                Room.hospital_id == hospital_id,
                Room.is_active == True,
                Room.is_deleted == False
            )

            if branch_id:
                query = query.filter(Room.branch_id == branch_id)

            if required_room_type:
                query = query.filter(Room.room_type == required_room_type)

            rooms = query.order_by(Room.room_type, Room.room_code).all()

            # Check availability if date/time provided
            room_list = []
            for room in rooms:
                room_data = {
                    'room_id': str(room.room_id),
                    'room_code': room.room_code,
                    'room_name': room.room_name,
                    'room_type': room.room_type,
                    'capacity': room.capacity,
                    'is_available': True,  # Default to available
                    'conflict_reason': None
                }

                # Check for conflicts if date/time provided
                if date_str and start_time and end_time:
                    from app.models.master import AppointmentResource
                    from app.models.appointment import Appointment

                    try:
                        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                        # Check appointment_resources for conflicts
                        conflict = session.query(AppointmentResource).join(
                            Appointment, AppointmentResource.appointment_id == Appointment.appointment_id
                        ).filter(
                            AppointmentResource.resource_type == 'room',
                            AppointmentResource.resource_id == room.room_id,
                            AppointmentResource.allocation_date == target_date,
                            AppointmentResource.status.in_(['allocated', 'in_use']),
                            Appointment.status.notin_(['cancelled', 'no_show']),
                            # Time overlap check
                            AppointmentResource.start_time < end_time,
                            AppointmentResource.end_time > start_time
                        ).first()

                        if conflict:
                            room_data['is_available'] = False
                            room_data['conflict_reason'] = f"Booked {conflict.start_time}-{conflict.end_time}"
                    except ValueError:
                        pass

                room_list.append(room_data)

            return jsonify({
                'success': True,
                'rooms': room_list,
                'required_room_type': required_room_type,
                'total': len(room_list)
            }), 200

    except Exception as e:
        logger.error(f"Error getting available rooms: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/therapists/available', methods=['GET'])
@login_required
def get_available_therapists():
    """
    Get available therapists/nurses for appointment booking.

    Query params:
        - date: Required (YYYY-MM-DD)
        - start_time: Required (HH:MM)
        - end_time: Required (HH:MM)
        - staff_type: Optional filter (therapist, nurse)
        - service_id: Optional - auto-detect required staff type from service
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user.user_id, hospital_id)

        date_str = request.args.get('date')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        staff_type_filter = request.args.get('staff_type')
        service_id = request.args.get('service_id')

        with get_db_session() as session:
            from app.models.master import ServiceResourceRequirement

            # If service_id provided, get required staff types (excluding doctor - doctors are selected separately)
            required_staff_types = []
            if service_id and not staff_type_filter:
                try:
                    service_uuid = uuid.UUID(service_id)
                    staff_reqs = session.query(ServiceResourceRequirement).filter(
                        ServiceResourceRequirement.service_id == service_uuid,
                        ServiceResourceRequirement.resource_type == 'staff',
                        ServiceResourceRequirement.is_active == True,
                        # Exclude doctor type - doctors are selected separately in the booking form
                        ServiceResourceRequirement.staff_type != 'doctor'
                    ).all()
                    required_staff_types = [r.staff_type for r in staff_reqs if r.staff_type]
                except ValueError:
                    pass
            elif staff_type_filter:
                required_staff_types = [staff_type_filter]

            # Query ALL staff marked as resources (is_resource=True)
            # No filtering by staff_type - show all resource staff
            query = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.is_active == True,
                Staff.is_deleted == False,
                Staff.is_resource == True
            )

            therapists = query.order_by(Staff.staff_type, Staff.first_name).all()
            logger.info(f"Found {len(therapists)} staff members with is_resource=True")

            # Check availability
            therapist_list = []
            for therapist in therapists:
                therapist_data = {
                    'staff_id': str(therapist.staff_id),
                    'name': f"{therapist.first_name} {therapist.last_name or ''}".strip(),
                    'staff_type': therapist.staff_type,
                    'specialization': therapist.specialization,
                    'is_available': True,
                    'conflict_reason': None
                }

                # Check for conflicts if date/time provided
                if date_str and start_time and end_time:
                    from app.models.master import AppointmentResource
                    from app.models.appointment import Appointment

                    try:
                        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

                        # Check appointment_resources for conflicts
                        conflict = session.query(AppointmentResource).join(
                            Appointment, AppointmentResource.appointment_id == Appointment.appointment_id
                        ).filter(
                            AppointmentResource.resource_type == 'staff',
                            AppointmentResource.resource_id == therapist.staff_id,
                            AppointmentResource.allocation_date == target_date,
                            AppointmentResource.status.in_(['allocated', 'in_use']),
                            Appointment.status.notin_(['cancelled', 'no_show']),
                            # Time overlap check
                            AppointmentResource.start_time < end_time,
                            AppointmentResource.end_time > start_time
                        ).first()

                        if conflict:
                            therapist_data['is_available'] = False
                            therapist_data['conflict_reason'] = f"Assigned {conflict.start_time}-{conflict.end_time}"
                    except ValueError:
                        pass

                therapist_list.append(therapist_data)

            return jsonify({
                'success': True,
                'therapists': therapist_list,
                'required_staff_types': required_staff_types,
                'total': len(therapist_list)
            }), 200

    except Exception as e:
        logger.error(f"Error getting available therapists: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/service/<service_id>/requirements', methods=['GET'])
@login_required
def get_service_requirements(service_id):
    """
    Get resource requirements for a specific service.
    Used to show what resources need to be allocated for booking.
    """
    try:
        with get_db_session() as session:
            from app.models.master import Service, ServiceResourceRequirement

            service_uuid = uuid.UUID(service_id)
            service = session.query(Service).filter_by(service_id=service_uuid).first()

            if not service:
                return jsonify({'success': False, 'error': 'Service not found'}), 404

            requirements = session.query(ServiceResourceRequirement).filter(
                ServiceResourceRequirement.service_id == service_uuid,
                ServiceResourceRequirement.is_active == True
            ).all()

            req_list = []
            for req in requirements:
                req_list.append({
                    'requirement_id': str(req.requirement_id),
                    'resource_type': req.resource_type,
                    'room_type': req.room_type,
                    'staff_type': req.staff_type,
                    'staff_role': req.staff_role,
                    'quantity_required': req.quantity_required,
                    'is_mandatory': req.is_mandatory,
                    'duration_minutes': req.duration_minutes,
                    'notes': req.notes
                })

            return jsonify({
                'success': True,
                'service': {
                    'service_id': str(service.service_id),
                    'name': service.service_name,
                    'duration_minutes': service.duration_minutes,
                    'requires_room_allocation': service.requires_room_allocation if hasattr(service, 'requires_room_allocation') else False,
                    'requires_staff_allocation': service.requires_staff_allocation if hasattr(service, 'requires_staff_allocation') else True,
                    'auto_approval_eligible': service.auto_approval_eligible if hasattr(service, 'auto_approval_eligible') else False
                },
                'requirements': req_list,
                'total': len(req_list)
            }), 200

    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid service ID format'}), 400
    except Exception as e:
        logger.error(f"Error getting service requirements: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/appointment/<appointment_id>/allocate-resources', methods=['POST'])
@login_required
def allocate_appointment_resources(appointment_id):
    """
    Allocate room and staff resources to an appointment.
    Called by front desk after selecting resources.

    Request body:
        - room_id: Optional UUID
        - therapist_id: Optional UUID (single therapist/nurse - backward compatible)
        - staff_ids: Optional list of UUIDs (multiple staff members)
        - approve: Optional boolean - also approve the appointment
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body required'}), 400

        room_id = data.get('room_id')
        therapist_id = data.get('therapist_id')  # Backward compatibility
        staff_ids = data.get('staff_ids', [])  # New: array of staff IDs
        approve = data.get('approve', False)

        # If only therapist_id provided (backward compatibility), convert to list
        if therapist_id and not staff_ids:
            staff_ids = [therapist_id]

        with get_db_session() as session:
            from app.models.appointment import Appointment
            from app.models.master import Room, AppointmentResource

            appointment_uuid = uuid.UUID(appointment_id)
            appointment = session.query(Appointment).filter_by(
                appointment_id=appointment_uuid
            ).first()

            if not appointment:
                return jsonify({'success': False, 'error': 'Appointment not found'}), 404

            allocation_date = appointment.appointment_date
            start_time_str = appointment.start_time.strftime('%H:%M:%S') if appointment.start_time else None
            end_time_str = appointment.end_time.strftime('%H:%M:%S') if appointment.end_time else None

            if not start_time_str:
                return jsonify({'success': False, 'error': 'Appointment time not set'}), 400

            # Calculate end time if not set
            if not end_time_str:
                duration = appointment.estimated_duration_minutes or 30
                end_dt = datetime.combine(allocation_date, appointment.start_time) + timedelta(minutes=duration)
                end_time_str = end_dt.time().strftime('%H:%M:%S')

            resources_allocated = []

            # Allocate room if provided
            if room_id:
                room_uuid = uuid.UUID(room_id)
                room = session.query(Room).filter_by(room_id=room_uuid).first()
                if not room:
                    return jsonify({'success': False, 'error': 'Room not found'}), 404

                # Check for conflicts
                existing = session.query(AppointmentResource).filter(
                    AppointmentResource.resource_type == 'room',
                    AppointmentResource.resource_id == room_uuid,
                    AppointmentResource.allocation_date == allocation_date,
                    AppointmentResource.status.in_(['allocated', 'in_use']),
                    AppointmentResource.start_time < end_time_str,
                    AppointmentResource.end_time > start_time_str
                ).first()

                if existing and str(existing.appointment_id) != appointment_id:
                    return jsonify({
                        'success': False,
                        'error': f'Room {room.room_name} is already booked for this time'
                    }), 409

                # Create or update room allocation
                room_allocation = session.query(AppointmentResource).filter_by(
                    appointment_id=appointment_uuid,
                    resource_type='room'
                ).first()

                if room_allocation:
                    room_allocation.resource_id = room_uuid
                    room_allocation.start_time = start_time_str
                    room_allocation.end_time = end_time_str
                    room_allocation.allocation_date = allocation_date
                else:
                    room_allocation = AppointmentResource(
                        appointment_id=appointment_uuid,
                        resource_type='room',
                        resource_id=room_uuid,
                        start_time=start_time_str,
                        end_time=end_time_str,
                        allocation_date=allocation_date,
                        status='allocated',
                        allocated_by=current_user.user_id
                    )
                    session.add(room_allocation)

                appointment.room_id = room_uuid
                resources_allocated.append({'type': 'room', 'name': room.room_name})

            # Allocate staff members if provided (supports multiple)
            staff_allocated_count = 0
            first_therapist_id = None  # For backward compatibility - store first one as therapist_id

            for staff_id in staff_ids:
                if not staff_id:
                    continue

                staff_uuid = uuid.UUID(staff_id) if isinstance(staff_id, str) else staff_id
                staff_member = session.query(Staff).filter_by(staff_id=staff_uuid).first()
                if not staff_member:
                    logger.warning(f"Staff member {staff_id} not found, skipping")
                    continue

                # Check for conflicts
                existing = session.query(AppointmentResource).filter(
                    AppointmentResource.resource_type == 'staff',
                    AppointmentResource.resource_id == staff_uuid,
                    AppointmentResource.allocation_date == allocation_date,
                    AppointmentResource.status.in_(['allocated', 'in_use']),
                    AppointmentResource.start_time < end_time_str,
                    AppointmentResource.end_time > start_time_str
                ).first()

                if existing and str(existing.appointment_id) != appointment_id:
                    logger.warning(f"{staff_member.first_name} is already assigned for this time, skipping")
                    continue

                # Check if this staff member is already allocated to this appointment
                existing_allocation = session.query(AppointmentResource).filter_by(
                    appointment_id=appointment_uuid,
                    resource_type='staff',
                    resource_id=staff_uuid
                ).first()

                if existing_allocation:
                    # Update existing allocation
                    existing_allocation.start_time = start_time_str
                    existing_allocation.end_time = end_time_str
                    existing_allocation.allocation_date = allocation_date
                else:
                    # Create new allocation
                    staff_type = staff_member.staff_type or 'staff'
                    staff_allocation = AppointmentResource(
                        appointment_id=appointment_uuid,
                        resource_type='staff',
                        resource_id=staff_uuid,
                        start_time=start_time_str,
                        end_time=end_time_str,
                        allocation_date=allocation_date,
                        status='allocated',
                        role=staff_type,  # Use staff_type as role
                        allocated_by=current_user.user_id
                    )
                    session.add(staff_allocation)

                # Store first therapist for backward compatibility
                if first_therapist_id is None:
                    first_therapist_id = staff_uuid

                staff_allocated_count += 1
                resources_allocated.append({
                    'type': 'staff',
                    'staff_type': staff_member.staff_type,
                    'name': f"{staff_member.first_name} {staff_member.last_name or ''}"
                })

            # For backward compatibility, set therapist_id to first allocated staff
            if first_therapist_id:
                appointment.therapist_id = first_therapist_id

            # Update allocation status
            if room_id and staff_allocated_count > 0:
                appointment.resource_allocation_status = 'complete'
            elif room_id or staff_allocated_count > 0:
                appointment.resource_allocation_status = 'partial'

            # Approve if requested
            if approve:
                appointment.requires_approval = False
                appointment.approved_at = datetime.now(timezone.utc)
                appointment.approved_by = current_user.user_id
                if appointment.status == 'requested':
                    appointment.status = 'confirmed'

            session.commit()

            return jsonify({
                'success': True,
                'message': 'Resources allocated successfully',
                'resources_allocated': resources_allocated,
                'allocation_status': appointment.resource_allocation_status,
                'approved': approve
            }), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid ID format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error allocating resources: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# EDIT APPOINTMENT
# =============================================================================

@appointment_api_bp.route('/web/<appointment_id>/edit', methods=['PUT'])
@login_required
def edit_appointment_web(appointment_id):
    """
    Edit appointment details (date, time, doctor, room, therapist, notes).
    Service/Package cannot be changed - must cancel and rebook.

    Request body:
        - appointment_date: YYYY-MM-DD
        - start_time: HH:MM
        - staff_id: Doctor UUID (optional)
        - room_id: Room UUID (optional)
        - therapist_id: Therapist UUID (optional)
        - priority: normal/urgent/emergency
        - internal_notes: text
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body required'}), 400

        appt_uuid = uuid.UUID(appointment_id)

        with get_db_session() as session:
            from app.models.master import Staff, Room

            appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not appointment:
                return jsonify({'success': False, 'error': 'Appointment not found'}), 404

            # Check if appointment can be edited (not completed or cancelled)
            if appointment.status in ['completed', 'cancelled', 'no_show']:
                return jsonify({
                    'success': False,
                    'error': f'Cannot edit {appointment.status} appointment'
                }), 400

            # Track what changed for Google Calendar
            date_time_changed = False
            old_date = appointment.appointment_date
            old_time = appointment.start_time

            # Update appointment date
            if data.get('appointment_date'):
                new_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
                if new_date != appointment.appointment_date:
                    appointment.appointment_date = new_date
                    date_time_changed = True

            # Update start time
            if data.get('start_time'):
                new_time_str = data['start_time']
                new_time = datetime.strptime(new_time_str, '%H:%M').time()
                if new_time != appointment.start_time:
                    appointment.start_time = new_time
                    # Calculate end time based on duration
                    duration = appointment.estimated_duration_minutes or 30
                    start_dt = datetime.combine(date.today(), new_time)
                    end_dt = start_dt + timedelta(minutes=duration)
                    appointment.end_time = end_dt.time()
                    date_time_changed = True

            # Update doctor/staff
            if 'staff_id' in data:
                if data['staff_id']:
                    staff_uuid = uuid.UUID(data['staff_id'])
                    staff = session.query(Staff).filter_by(staff_id=staff_uuid).first()
                    if staff:
                        appointment.staff_id = staff_uuid
                else:
                    appointment.staff_id = None

            # Update room
            if 'room_id' in data:
                if data['room_id']:
                    room_uuid = uuid.UUID(data['room_id'])
                    room = session.query(Room).filter_by(room_id=room_uuid).first()
                    if room:
                        appointment.room_id = room_uuid
                else:
                    appointment.room_id = None

            # Update therapist
            if 'therapist_id' in data:
                if data['therapist_id']:
                    therapist_uuid = uuid.UUID(data['therapist_id'])
                    therapist = session.query(Staff).filter_by(staff_id=therapist_uuid).first()
                    if therapist:
                        appointment.therapist_id = therapist_uuid
                else:
                    appointment.therapist_id = None

            # Update priority
            if data.get('priority'):
                appointment.priority = data['priority']

            # Update notes
            if 'internal_notes' in data:
                appointment.internal_notes = data['internal_notes']

            session.flush()

            result = {
                'success': True,
                'message': 'Appointment updated successfully',
                'appointment_id': str(appointment.appointment_id),
                'date_time_changed': date_time_changed
            }

            # Determine Google Calendar action
            gcal_action = 'update' if date_time_changed else None

        # Push to Google Calendar AFTER session closes
        if gcal_action:
            try:
                from app.services.google_calendar_service import google_calendar_service
                google_calendar_service.push_appointment_event(appointment_id, action=gcal_action)
            except Exception as gcal_error:
                logger.warning(f"Google Calendar sync failed (non-critical): {gcal_error}")

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error editing appointment: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/<appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment_web(appointment_id):
    """
    Cancel an appointment (session-based auth).

    Request body:
        - reason: Required - cancellation reason
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason')

        if not reason:
            return jsonify({'success': False, 'error': 'Cancellation reason is required'}), 400

        appt_uuid = uuid.UUID(appointment_id)

        with get_db_session() as session:
            appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not appointment:
                return jsonify({'success': False, 'error': 'Appointment not found'}), 404

            # Check if already cancelled
            if appointment.status == 'cancelled':
                return jsonify({'success': False, 'error': 'Appointment is already cancelled'}), 400

            # Cancel the appointment
            old_status = appointment.status
            appointment.status = 'cancelled'
            appointment.cancellation_reason = reason
            appointment.cancelled_at = datetime.now(timezone.utc)
            appointment.cancelled_by = current_user.user_id

            session.flush()

            result = {
                'success': True,
                'message': 'Appointment cancelled',
                'appointment_id': str(appointment.appointment_id),
                'old_status': old_status
            }

        # Push to Google Calendar AFTER session closes - delete event
        try:
            from app.services.google_calendar_service import google_calendar_service
            google_calendar_service.push_appointment_event(appointment_id, action='delete')
        except Exception as gcal_error:
            logger.warning(f"Google Calendar sync failed (non-critical): {gcal_error}")

        return jsonify(result), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': f'Invalid format: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error cancelling appointment: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/rooms', methods=['GET'])
@login_required
def get_all_rooms():
    """
    Get all rooms for the current hospital (for dropdowns).
    """
    try:
        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            from app.models.master import Room

            rooms = session.query(Room).filter(
                Room.hospital_id == hospital_id,
                Room.is_active == True,
                Room.is_deleted == False
            ).order_by(Room.room_name).all()

            room_list = [{
                'room_id': str(r.room_id),
                'room_name': r.room_name,
                'room_type': r.room_type or 'General',
                'capacity': r.capacity
            } for r in rooms]

            return jsonify({
                'success': True,
                'rooms': room_list
            }), 200

    except Exception as e:
        logger.error(f"Error getting rooms: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@appointment_api_bp.route('/web/therapists', methods=['GET'])
@login_required
def get_all_therapists():
    """
    Get all therapists/nurses for the current hospital (for dropdowns).
    """
    try:
        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            # Get staff marked as resources
            therapists = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.is_active == True,
                Staff.is_deleted == False,
                Staff.is_resource == True
            ).order_by(Staff.first_name).all()

            therapist_list = [{
                'staff_id': str(t.staff_id),
                'name': f"{t.first_name} {t.last_name or ''}".strip(),
                'staff_type': t.staff_type
            } for t in therapists]

            return jsonify({
                'success': True,
                'therapists': therapist_list
            }), 200

    except Exception as e:
        logger.error(f"Error getting therapists: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# HEALTH CHECK
# =============================================================================

@appointment_api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for appointment API."""
    return jsonify({
        'status': 'healthy',
        'service': 'appointment_api',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200
