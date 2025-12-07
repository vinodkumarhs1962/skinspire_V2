# app/views/appointment_views.py
"""
Appointment Views
Phase 1 of Patient Lifecycle System

Provides web views for:
- Appointment booking interface
- Today's queue/dashboard
- Doctor schedule management
- Calendar view
"""

import json
import uuid
import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, List, Optional

from flask import (
    Blueprint, render_template, request, jsonify, redirect,
    url_for, flash, current_app, session as flask_session
)
from flask_login import login_required, current_user

from app.services.database_service import get_db_session
from app.services.appointment_service import appointment_service
from app.services.slot_generator_service import slot_generator_service
from app.models.appointment import (
    AppointmentType, DoctorSchedule, AppointmentSlot, Appointment,
    DoctorScheduleException
)
from app.models.transaction import User
from app.models.master import Staff, Patient, Branch, Hospital
from app.security.authorization.permission_validator import has_permission
from app.services.branch_service import get_user_branch_id as get_branch_id_from_service

# Configure logger
logger = logging.getLogger(__name__)


def get_user_branch_id_safe(user):
    """
    Get the branch_id for a user using the centralized branch service.
    IMPORTANT: Call this BEFORE entering a get_db_session() context to avoid nested sessions.
    """
    try:
        if hasattr(user, 'user_id') and hasattr(user, 'hospital_id') and user.hospital_id:
            return get_branch_id_from_service(user.user_id, user.hospital_id)
    except Exception as e:
        logger.warning(f"Error getting branch from service: {e}")

    return None

# Create blueprint
appointment_views_bp = Blueprint('appointment_views', __name__, url_prefix='/appointment')


# =============================================================================
# DASHBOARD / QUEUE VIEW
# =============================================================================

@appointment_views_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Main appointment dashboard showing today's queue and summary.
    """
    try:
        # Get branch_id BEFORE entering session context to avoid nested sessions
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        # Get selected date from query param, default to today
        selected_date_str = request.args.get('date')
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = date.today()
        else:
            selected_date = date.today()

        with get_db_session() as session:

            # Get today's date for reference
            today = date.today()

            # Get branches for filter
            branches = session.query(Branch).filter(
                Branch.hospital_id == hospital_id,
                Branch.is_active == True,
                Branch.is_deleted == False
            ).all()

            # Get doctors for filter
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            # Get appointment types (global, not per-hospital)
            appointment_types = session.query(AppointmentType).filter(
                AppointmentType.is_active == True,
                AppointmentType.is_deleted == False
            ).order_by(AppointmentType.display_order).all()

            # If branch_id is None, try to get the first branch for this hospital
            if not branch_id and branches:
                branch_id = branches[0].branch_id

            # Get queue for selected date
            queue = appointment_service.get_queue_by_date(
                session=session,
                branch_id=branch_id,
                target_date=selected_date
            )

            # Calculate summary
            summary = {
                'total': len(queue),
                'waiting': len([a for a in queue if a.status == 'checked_in']),
                'in_progress': len([a for a in queue if a.status == 'in_progress']),
                'completed': len([a for a in queue if a.status == 'completed']),
                'pending': len([a for a in queue if a.status in ['requested', 'confirmed']]),
                'cancelled': 0,
                'no_show': 0
            }

            # Get cancelled and no-show counts for selected date
            cancelled_count = session.query(Appointment).filter(
                Appointment.branch_id == branch_id,
                Appointment.appointment_date == selected_date,
                Appointment.status == 'cancelled',
                Appointment.is_deleted == False
            ).count()
            summary['cancelled'] = cancelled_count

            no_show_count = session.query(Appointment).filter(
                Appointment.branch_id == branch_id,
                Appointment.appointment_date == selected_date,
                Appointment.status == 'no_show',
                Appointment.is_deleted == False
            ).count()
            summary['no_show'] = no_show_count

            # Prepare queue data with patient info
            queue_data = []
            for appt in queue:
                patient = session.query(Patient).filter_by(patient_id=appt.patient_id).first()
                doctor = session.query(Staff).filter_by(staff_id=appt.staff_id).first() if appt.staff_id else None

                waiting_minutes = None
                if appt.status == 'checked_in' and appt.checked_in_at:
                    waiting_minutes = int((datetime.now(timezone.utc) - appt.checked_in_at).total_seconds() / 60)

                # Safely get patient phone from contact_info (can be dict or JSON string)
                patient_phone = None
                if patient and patient.contact_info:
                    contact_info = patient.contact_info
                    # Handle case where contact_info is stored as JSON string
                    if isinstance(contact_info, str):
                        try:
                            contact_info = json.loads(contact_info)
                        except (json.JSONDecodeError, TypeError):
                            contact_info = {}
                    if isinstance(contact_info, dict):
                        patient_phone = contact_info.get('mobile') or contact_info.get('phone')

                # Get room and therapist names if allocated
                room_name = None
                therapist_name = None
                if hasattr(appt, 'room_id') and appt.room_id:
                    from app.models.master import Room
                    room = session.query(Room).filter_by(room_id=appt.room_id).first()
                    room_name = room.room_name if room else None
                if hasattr(appt, 'therapist_id') and appt.therapist_id:
                    therapist = session.query(Staff).filter_by(staff_id=appt.therapist_id).first()
                    therapist_name = f"{therapist.first_name} {therapist.last_name or ''}".strip() if therapist else None

                # Get service/package info
                service_name = None
                package_name = None
                if hasattr(appt, 'service_id') and appt.service_id:
                    from app.models.master import Service
                    service = session.query(Service).filter_by(service_id=appt.service_id).first()
                    service_name = service.service_name if service else None
                if hasattr(appt, 'package_id') and appt.package_id:
                    from app.models.master import Package
                    package = session.query(Package).filter_by(package_id=appt.package_id).first()
                    package_name = package.package_name if package else None

                queue_data.append({
                    'appointment_id': str(appt.appointment_id),
                    'appointment_number': appt.appointment_number,
                    'token_number': appt.token_number,
                    'patient_id': str(appt.patient_id),
                    'patient_name': patient.full_name if patient else 'Unknown',
                    'patient_mrn': patient.mrn if patient else None,
                    'patient_phone': patient_phone,
                    'doctor_name': f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else 'Not Assigned',
                    'appointment_time': appt.start_time.strftime('%H:%M') if appt.start_time else None,
                    'status': appt.status,
                    'priority': appt.priority,
                    'chief_complaint': appt.chief_complaint,
                    'waiting_minutes': waiting_minutes,
                    'is_walk_in': appt.booking_source == 'walk_in',
                    'is_follow_up': appt.is_follow_up,
                    'checked_in_at': appt.checked_in_at.strftime('%H:%M') if appt.checked_in_at else None,
                    # Resource allocation info
                    'resource_allocation_status': getattr(appt, 'resource_allocation_status', 'pending'),
                    'room_name': room_name,
                    'therapist_name': therapist_name,
                    'requires_approval': getattr(appt, 'requires_approval', False),
                    # Service/Package info
                    'appointment_purpose': getattr(appt, 'appointment_purpose', 'consultation'),
                    'service_name': service_name,
                    'package_name': package_name
                })

            return render_template(
                'appointment/dashboard.html',
                today=today,
                selected_date=selected_date,
                queue=queue_data,
                summary=summary,
                branches=branches,
                doctors=doctors,
                appointment_types=appointment_types,
                current_branch_id=str(branch_id) if branch_id else None
            )

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}", exc_info=True)
        flash('Error loading appointment dashboard', 'error')
        return redirect(url_for('auth_views.dashboard'))


@appointment_views_bp.route('/queue')
@login_required
def queue_view():
    """
    Dedicated queue management view with real-time updates.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get doctors for this branch
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            doctor_list = [{
                'staff_id': str(d.staff_id),
                'name': f"{d.first_name} {d.last_name or ''}".strip()
            } for d in doctors]

            return render_template(
                'appointment/queue.html',
                doctors=doctor_list,
                branch_id=str(branch_id) if branch_id else None
            )

    except Exception as e:
        logger.error(f"Error loading queue view: {str(e)}", exc_info=True)
        flash('Error loading queue view', 'error')
        return redirect(url_for('appointment_views.dashboard'))


# =============================================================================
# BOOKING VIEWS
# =============================================================================

@appointment_views_bp.route('/book')
@login_required
def book_appointment():
    """
    Appointment booking wizard interface.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get patient_id from query param if provided
            patient_id = request.args.get('patient_id')

            # Get branches
            branches = session.query(Branch).filter(
                Branch.hospital_id == hospital_id,
                Branch.is_active == True,
                Branch.is_deleted == False
            ).all()

            # Get doctors
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            # Get appointment types (global, not per-hospital)
            appointment_types = session.query(AppointmentType).filter(
                AppointmentType.is_active == True,
                AppointmentType.is_deleted == False
            ).order_by(AppointmentType.display_order).all()

            # If patient_id provided, get patient details
            patient_data = None
            if patient_id:
                patient = session.query(Patient).filter_by(
                    patient_id=uuid.UUID(patient_id)
                ).first()
                if patient:
                    # Safely get phone from contact_info
                    patient_phone = None
                    if patient.contact_info:
                        contact_info = patient.contact_info
                        if isinstance(contact_info, str):
                            try:
                                contact_info = json.loads(contact_info)
                            except (json.JSONDecodeError, TypeError):
                                contact_info = {}
                        if isinstance(contact_info, dict):
                            patient_phone = contact_info.get('mobile') or contact_info.get('phone')

                    patient_data = {
                        'patient_id': str(patient.patient_id),
                        'name': patient.full_name,
                        'mrn': patient.mrn,
                        'phone': patient_phone
                    }

            return render_template(
                'appointment/book.html',
                branches=branches,
                doctors=doctors,
                appointment_types=appointment_types,
                patient=patient_data,
                current_branch_id=str(branch_id) if branch_id else None
            )

    except Exception as e:
        logger.error(f"Error loading booking page: {str(e)}", exc_info=True)
        flash('Error loading booking page', 'error')
        return redirect(url_for('appointment_views.dashboard'))


@appointment_views_bp.route('/walk-in')
@login_required
def walk_in_booking():
    """
    Quick walk-in appointment booking interface.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get doctors available today
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            # Get appointment types that allow walk-in
            appointment_types = session.query(AppointmentType).filter(
                AppointmentType.is_active == True,
                AppointmentType.is_deleted == False,
                AppointmentType.allow_walk_in == True
            ).order_by(AppointmentType.display_order).all()

            return render_template(
                'appointment/walk_in.html',
                doctors=doctors,
                appointment_types=appointment_types,
                branch_id=str(branch_id) if branch_id else None
            )

    except Exception as e:
        logger.error(f"Error loading walk-in page: {str(e)}", exc_info=True)
        flash('Error loading walk-in booking page', 'error')
        return redirect(url_for('appointment_views.dashboard'))


# =============================================================================
# CALENDAR VIEWS
# =============================================================================

@appointment_views_bp.route('/calendar')
@login_required
def calendar_view():
    """
    Calendar view showing appointments across days/weeks.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get view type from query params
            view_type = request.args.get('view', 'week')  # day, week, month

            # Get target date
            date_str = request.args.get('date')
            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()

            # Get doctors for filter
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            # Get branches for filter
            branches = session.query(Branch).filter(
                Branch.hospital_id == hospital_id,
                Branch.is_active == True,
                Branch.is_deleted == False
            ).all()

            return render_template(
                'appointment/calendar.html',
                view_type=view_type,
                target_date=target_date,
                doctors=doctors,
                branches=branches,
                current_branch_id=str(branch_id) if branch_id else None
            )

    except Exception as e:
        logger.error(f"Error loading calendar: {str(e)}", exc_info=True)
        flash('Error loading calendar view', 'error')
        return redirect(url_for('appointment_views.dashboard'))


@appointment_views_bp.route('/slots')
@login_required
def slot_picker():
    """
    Slot picker view for selecting available appointment slots.
    Usually opened in a modal or popup.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get parameters
            staff_id = request.args.get('staff_id')
            date_str = request.args.get('date')
            service_id = request.args.get('service_id')

            target_date = date.today()
            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Get service name if service_id provided
            service_name = None
            if service_id:
                from app.models.master import Service
                service = session.query(Service).filter_by(service_id=service_id).first()
                if service:
                    service_name = service.service_name

            # Get package name if package_id provided
            package_id = request.args.get('package_id')
            package_name = None
            if package_id:
                from app.models.master import Package
                package = session.query(Package).filter_by(package_id=package_id).first()
                if package:
                    package_name = package.package_name

            # Get doctors
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            return render_template(
                'appointment/slot_picker.html',
                doctors=doctors,
                selected_staff_id=staff_id,
                selected_date=target_date,
                selected_date_str=target_date.strftime('%Y-%m-%d') if target_date else '',
                branch_id=str(branch_id) if branch_id else None,
                service_name=service_name,
                service_id=service_id,
                package_name=package_name,
                package_id=package_id
            )

    except Exception as e:
        logger.error(f"Error loading slot picker: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# =============================================================================
# SCHEDULE MANAGEMENT VIEWS
# =============================================================================

@appointment_views_bp.route('/schedules')
@login_required
def schedule_list():
    """
    View and manage doctor schedules.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get all schedules for this branch
            schedules = session.query(DoctorSchedule).filter(
                DoctorSchedule.branch_id == branch_id,
                DoctorSchedule.is_active == True,
                DoctorSchedule.is_deleted == False
            ).order_by(
                DoctorSchedule.staff_id,
                DoctorSchedule.day_of_week
            ).all()

            # Get doctors
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            doctor_map = {str(d.staff_id): f"{d.first_name} {d.last_name or ''}".strip() for d in doctors}

            # Group schedules by doctor
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            schedule_data = {}

            for schedule in schedules:
                staff_id = str(schedule.staff_id)
                if staff_id not in schedule_data:
                    schedule_data[staff_id] = {
                        'doctor_name': doctor_map.get(staff_id, 'Unknown'),
                        'schedules': []
                    }

                schedule_data[staff_id]['schedules'].append({
                    'schedule_id': str(schedule.schedule_id),
                    'day_of_week': schedule.day_of_week,
                    'day_name': day_names[schedule.day_of_week],
                    'start_time': schedule.start_time.strftime('%H:%M'),
                    'end_time': schedule.end_time.strftime('%H:%M'),
                    'slot_duration': schedule.slot_duration_minutes,
                    'max_patients': schedule.max_patients_per_slot,
                    'break_start': schedule.break_start_time.strftime('%H:%M') if schedule.break_start_time else None,
                    'break_end': schedule.break_end_time.strftime('%H:%M') if schedule.break_end_time else None
                })

            # Get branches for navigation
            branches = session.query(Branch).filter(
                Branch.hospital_id == hospital_id,
                Branch.is_active == True,
                Branch.is_deleted == False
            ).all()

            return render_template(
                'appointment/schedules.html',
                schedule_data=schedule_data,
                doctors=doctors,
                branches=branches,
                day_names=day_names,
                current_branch_id=str(branch_id) if branch_id else None
            )

    except Exception as e:
        logger.error(f"Error loading schedules: {str(e)}", exc_info=True)
        flash('Error loading schedule list', 'error')
        return redirect(url_for('appointment_views.dashboard'))


@appointment_views_bp.route('/schedules/create')
@login_required
def create_schedule():
    """
    Form to create a new doctor schedule.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get doctors
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            # Get branches
            branches = session.query(Branch).filter(
                Branch.hospital_id == hospital_id,
                Branch.is_active == True,
                Branch.is_deleted == False
            ).all()

            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

            return render_template(
                'appointment/schedule_form.html',
                doctors=doctors,
                branches=branches,
                day_names=day_names,
                current_branch_id=str(branch_id) if branch_id else None,
                is_edit=False
            )

    except Exception as e:
        logger.error(f"Error loading schedule form: {str(e)}", exc_info=True)
        flash('Error loading schedule form', 'error')
        return redirect(url_for('appointment_views.schedule_list'))


@appointment_views_bp.route('/exceptions')
@login_required
def exception_list():
    """
    View and manage schedule exceptions (leaves, holidays).
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get upcoming exceptions
            today = date.today()
            exceptions = session.query(DoctorScheduleException).filter(
                DoctorScheduleException.exception_date >= today,
                DoctorScheduleException.is_active == True,
                DoctorScheduleException.is_deleted == False,
                or_(
                    DoctorScheduleException.branch_id == branch_id,
                    DoctorScheduleException.branch_id.is_(None)
                )
            ).order_by(DoctorScheduleException.exception_date).all()

            # Get doctor info for each exception
            exception_data = []
            for exc in exceptions:
                doctor = session.query(Staff).filter_by(staff_id=exc.staff_id).first()
                exception_data.append({
                    'exception_id': str(exc.exception_id),
                    'doctor_name': f"{doctor.first_name} {doctor.last_name or ''}".strip() if doctor else 'Unknown',
                    'exception_date': exc.exception_date,
                    'exception_type': exc.exception_type,
                    'reason': exc.reason,
                    'start_time': exc.start_time.strftime('%H:%M') if exc.start_time else None,
                    'end_time': exc.end_time.strftime('%H:%M') if exc.end_time else None,
                    'is_full_day': exc.start_time is None
                })

            # Get doctors for filter
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            return render_template(
                'appointment/exceptions.html',
                exceptions=exception_data,
                doctors=doctors
            )

    except Exception as e:
        logger.error(f"Error loading exceptions: {str(e)}", exc_info=True)
        flash('Error loading schedule exceptions', 'error')
        return redirect(url_for('appointment_views.dashboard'))


# =============================================================================
# APPOINTMENT DETAIL VIEW
# =============================================================================

@appointment_views_bp.route('/<appointment_id>')
@login_required
def appointment_detail(appointment_id):
    """
    View detailed appointment information.
    """
    try:
        with get_db_session() as session:
            appt_uuid = uuid.UUID(appointment_id)

            appointment = session.query(Appointment).filter_by(
                appointment_id=appt_uuid,
                is_deleted=False
            ).first()

            if not appointment:
                flash('Appointment not found', 'error')
                return redirect(url_for('appointment_views.dashboard'))

            # Get related entities
            patient = session.query(Patient).filter_by(patient_id=appointment.patient_id).first()
            doctor = session.query(Staff).filter_by(staff_id=appointment.staff_id).first() if appointment.staff_id else None
            appt_type = session.query(AppointmentType).filter_by(type_id=appointment.appointment_type_id).first() if appointment.appointment_type_id else None
            branch = session.query(Branch).filter_by(branch_id=appointment.branch_id).first()

            # Get status history
            from app.models.appointment import AppointmentStatusHistory
            status_history = session.query(AppointmentStatusHistory).filter_by(
                appointment_id=appt_uuid
            ).order_by(AppointmentStatusHistory.changed_at).all()

            history_data = []
            for h in status_history:
                history_data.append({
                    'from_status': h.from_status,
                    'to_status': h.to_status,
                    'changed_at': h.changed_at,
                    'notes': h.notes
                })

            # Get service and package info
            from app.models.master import Service, Package
            service = None
            package = None

            if hasattr(appointment, 'service_id') and appointment.service_id:
                service = session.query(Service).filter_by(service_id=appointment.service_id).first()

            if hasattr(appointment, 'package_id') and appointment.package_id:
                package = session.query(Package).filter_by(package_id=appointment.package_id).first()

            # Get resource allocation info
            from app.models.master import Room, AppointmentResource
            room = None
            therapist = None
            resources = []

            if hasattr(appointment, 'room_id') and appointment.room_id:
                room = session.query(Room).filter_by(room_id=appointment.room_id).first()

            if hasattr(appointment, 'therapist_id') and appointment.therapist_id:
                therapist = session.query(Staff).filter_by(staff_id=appointment.therapist_id).first()

            # Get all allocated resources
            allocations = session.query(AppointmentResource).filter(
                AppointmentResource.appointment_id == appt_uuid,
                AppointmentResource.status.in_(['allocated', 'in_use'])
            ).all()

            for alloc in allocations:
                if alloc.resource_type == 'room':
                    alloc_room = session.query(Room).filter_by(room_id=alloc.resource_id).first()
                    if alloc_room:
                        resources.append({
                            'type': 'room',
                            'name': alloc_room.room_name,
                            'code': alloc_room.room_code,
                            'room_type': alloc_room.room_type,
                            'status': alloc.status
                        })
                elif alloc.resource_type == 'staff':
                    alloc_staff = session.query(Staff).filter_by(staff_id=alloc.resource_id).first()
                    if alloc_staff:
                        resources.append({
                            'type': 'staff',
                            'name': f"{alloc_staff.first_name} {alloc_staff.last_name or ''}".strip(),
                            'staff_type': alloc_staff.staff_type,
                            'role': alloc.role,
                            'status': alloc.status
                        })

            return render_template(
                'appointment/detail.html',
                appointment=appointment,
                patient=patient,
                doctor=doctor,
                appointment_type=appt_type,
                branch=branch,
                status_history=history_data,
                room=room,
                therapist=therapist,
                resources=resources,
                service=service,
                package=package
            )

    except Exception as e:
        logger.error(f"Error loading appointment detail: {str(e)}", exc_info=True)
        flash('Error loading appointment details', 'error')
        return redirect(url_for('appointment_views.dashboard'))


# =============================================================================
# REPORTS
# =============================================================================

@appointment_views_bp.route('/reports')
@login_required
def reports():
    """
    Appointment reports and analytics.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        with get_db_session() as session:

            # Get date range from params
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')

            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            else:
                start_date = date.today() - timedelta(days=30)

            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            else:
                end_date = date.today()

            # Get doctors for filter
            doctors = session.query(Staff).filter(
                Staff.hospital_id == hospital_id,
                Staff.staff_type == 'doctor',
                Staff.is_active == True,
                Staff.is_deleted == False
            ).all()

            # Get branches for filter
            branches = session.query(Branch).filter(
                Branch.hospital_id == hospital_id,
                Branch.is_active == True,
                Branch.is_deleted == False
            ).all()

            return render_template(
                'appointment/reports.html',
                start_date=start_date,
                end_date=end_date,
                doctors=doctors,
                branches=branches,
                current_branch_id=str(branch_id) if branch_id else None
            )

    except Exception as e:
        logger.error(f"Error loading reports: {str(e)}", exc_info=True)
        flash('Error loading appointment reports', 'error')
        return redirect(url_for('appointment_views.dashboard'))


# Import or_ for exception query
from sqlalchemy import or_


# =============================================================================
# RESOURCE CALENDAR VIEW
# =============================================================================

@appointment_views_bp.route('/resources')
@login_required
def resource_calendar():
    """
    Resource calendar view showing rooms, doctors, and therapists allocations.
    """
    try:
        hospital_id = current_user.hospital_id
        branch_id = get_user_branch_id_safe(current_user)

        # Get selected date from query param, default to today
        selected_date_str = request.args.get('date')
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = date.today()
        else:
            selected_date = date.today()

        return render_template(
            'appointment/resource_calendar.html',
            selected_date=selected_date,
            today=date.today()
        )

    except Exception as e:
        logger.error(f"Error loading resource calendar: {str(e)}", exc_info=True)
        flash('Error loading resource calendar', 'error')
        return redirect(url_for('appointment_views.dashboard'))
