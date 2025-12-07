# app/services/appointment_service.py
"""
Appointment Service Layer
Phase 1 of Patient Lifecycle System

Handles all appointment-related business logic including:
- Booking appointments
- Managing appointment status
- Check-in workflow
- Cancellation and rescheduling
- Reminder management
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy import and_, or_, func, case
from sqlalchemy.orm import Session, joinedload

from app.models.appointment import (
    Appointment, AppointmentSlot, DoctorSchedule,
    AppointmentType, AppointmentStatusHistory, AppointmentReminder,
    DoctorScheduleException
)
from app.models.master import Patient, Staff, Branch, Hospital

logger = logging.getLogger(__name__)


class AppointmentError(Exception):
    """Base exception for appointment-related errors."""
    pass


class SlotNotAvailableError(AppointmentError):
    """Raised when the requested slot is not available."""
    pass


class InvalidStatusTransitionError(AppointmentError):
    """Raised when attempting an invalid status transition."""
    pass


class AppointmentService:
    """
    Service class for appointment management.

    Provides methods for:
    - Booking and managing appointments
    - Status transitions (confirm, check-in, complete, cancel)
    - Queue management
    - Slot availability checking
    """

    def __init__(self):
        """Initialize the appointment service."""
        pass

    # =========================================================================
    # APPOINTMENT BOOKING
    # =========================================================================

    def book_appointment(
        self,
        session: Session,
        patient_id: UUID,
        branch_id: UUID,
        hospital_id: UUID,
        appointment_date: date,
        start_time: time,
        staff_id: Optional[UUID] = None,
        appointment_type_id: Optional[UUID] = None,
        service_id: Optional[UUID] = None,
        package_id: Optional[UUID] = None,
        chief_complaint: Optional[str] = None,
        priority: str = 'normal',
        booking_source: str = 'front_desk',
        patient_notes: Optional[str] = None,
        is_follow_up: bool = False,
        parent_appointment_id: Optional[UUID] = None,
        user_id: Optional[str] = None
    ) -> Appointment:
        """
        Book a new appointment.

        Args:
            session: Database session
            patient_id: Patient's UUID
            branch_id: Branch UUID
            hospital_id: Hospital UUID
            appointment_date: Date of appointment
            start_time: Start time
            staff_id: Optional doctor UUID
            appointment_type_id: Optional appointment type UUID
            service_id: Optional service UUID (for duration calculation)
            package_id: Optional package UUID (for duration calculation)
            chief_complaint: Reason for visit
            priority: normal, urgent, or emergency
            booking_source: front_desk, self_service, whatsapp, phone, walk_in
            patient_notes: Notes from patient
            is_follow_up: Whether this is a follow-up appointment
            parent_appointment_id: Previous appointment if follow-up
            user_id: User making the booking

        Returns:
            Created Appointment object

        Raises:
            SlotNotAvailableError: If the requested slot is not available
        """
        # Calculate duration
        duration = self._get_appointment_duration(
            session, hospital_id, service_id, package_id, appointment_type_id
        )

        # Calculate end time
        start_datetime = datetime.combine(appointment_date, start_time)
        end_datetime = start_datetime + timedelta(minutes=duration)
        end_time = end_datetime.time()

        # Check if slot exists and is available
        slot = self._find_available_slot(
            session, staff_id, branch_id, appointment_date, start_time
        )

        if staff_id and not slot:
            # Try to create slot if doctor has a schedule for this day
            slot = self._create_slot_from_schedule(
                session, staff_id, branch_id, appointment_date, start_time, duration
            )

        # Create the appointment
        appointment = Appointment(
            patient_id=patient_id,
            staff_id=staff_id,
            branch_id=branch_id,
            hospital_id=hospital_id,
            slot_id=slot.slot_id if slot else None,
            appointment_type_id=appointment_type_id,
            service_id=service_id,
            package_id=package_id,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            estimated_duration_minutes=duration,
            status='requested',
            booking_source=booking_source,
            chief_complaint=chief_complaint,
            priority=priority,
            patient_notes=patient_notes,
            is_follow_up=is_follow_up,
            parent_appointment_id=parent_appointment_id,
            created_by=user_id,
            updated_by=user_id
        )

        session.add(appointment)
        session.flush()  # Get the appointment_id

        # Book the slot if available
        if slot:
            slot.book()

        logger.info(f"Appointment booked: {appointment.appointment_number} for patient {patient_id}")

        return appointment

    def book_walk_in(
        self,
        session: Session,
        patient_id: UUID,
        branch_id: UUID,
        hospital_id: UUID,
        staff_id: Optional[UUID] = None,
        appointment_type_id: Optional[UUID] = None,
        chief_complaint: Optional[str] = None,
        priority: str = 'normal',
        user_id: Optional[str] = None
    ) -> Appointment:
        """
        Book a walk-in appointment for current time.

        Walk-ins are immediately checked in and given a token.
        """
        now = datetime.now()

        appointment = self.book_appointment(
            session=session,
            patient_id=patient_id,
            branch_id=branch_id,
            hospital_id=hospital_id,
            appointment_date=now.date(),
            start_time=now.time(),
            staff_id=staff_id,
            appointment_type_id=appointment_type_id,
            chief_complaint=chief_complaint,
            priority=priority,
            booking_source='walk_in',
            user_id=user_id
        )

        # Automatically check in walk-ins
        self.check_in(session, appointment.appointment_id, user_id)

        return appointment

    # =========================================================================
    # STATUS TRANSITIONS
    # =========================================================================

    def confirm(
        self,
        session: Session,
        appointment_id: UUID,
        user_id: Optional[str] = None
    ) -> Appointment:
        """Confirm an appointment."""
        appointment = self._get_appointment(session, appointment_id)

        if appointment.status != Appointment.STATUS_REQUESTED:
            raise InvalidStatusTransitionError(
                f"Cannot confirm appointment in status: {appointment.status}"
            )

        appointment.confirm(user_id)
        appointment.updated_by = user_id

        # Send confirmation notification
        self._queue_notification(session, appointment, 'confirmation')

        logger.info(f"Appointment confirmed: {appointment.appointment_number}")
        return appointment

    def check_in(
        self,
        session: Session,
        appointment_id: UUID,
        user_id: Optional[str] = None
    ) -> Appointment:
        """Check in a patient for their appointment."""
        appointment = self._get_appointment(session, appointment_id)

        if appointment.status not in [Appointment.STATUS_REQUESTED, Appointment.STATUS_CONFIRMED]:
            raise InvalidStatusTransitionError(
                f"Cannot check in appointment in status: {appointment.status}"
            )

        # Get next token number for the branch today
        token = self._get_next_token(session, appointment.branch_id, appointment.appointment_date)

        appointment.check_in(user_id, token)
        appointment.updated_by = user_id

        logger.info(f"Patient checked in: {appointment.appointment_number}, Token: {token}")
        return appointment

    def start_consultation(
        self,
        session: Session,
        appointment_id: UUID,
        user_id: Optional[str] = None
    ) -> Appointment:
        """Start the consultation (patient with doctor)."""
        appointment = self._get_appointment(session, appointment_id)

        if appointment.status != Appointment.STATUS_CHECKED_IN:
            raise InvalidStatusTransitionError(
                f"Cannot start consultation for appointment in status: {appointment.status}"
            )

        appointment.start(user_id)
        appointment.updated_by = user_id

        logger.info(f"Consultation started: {appointment.appointment_number}")
        return appointment

    def complete(
        self,
        session: Session,
        appointment_id: UUID,
        consultation_id: Optional[UUID] = None,
        user_id: Optional[str] = None
    ) -> Appointment:
        """Mark appointment as completed."""
        appointment = self._get_appointment(session, appointment_id)

        if appointment.status != Appointment.STATUS_IN_PROGRESS:
            raise InvalidStatusTransitionError(
                f"Cannot complete appointment in status: {appointment.status}"
            )

        appointment.complete(user_id, consultation_id)
        appointment.updated_by = user_id

        # Queue follow-up reminder if needed
        self._queue_notification(session, appointment, 'follow_up')

        logger.info(f"Appointment completed: {appointment.appointment_number}")
        return appointment

    def cancel(
        self,
        session: Session,
        appointment_id: UUID,
        reason: str,
        user_id: Optional[str] = None
    ) -> Appointment:
        """Cancel an appointment."""
        appointment = self._get_appointment(session, appointment_id)

        if appointment.status in Appointment.TERMINAL_STATUSES:
            raise InvalidStatusTransitionError(
                f"Cannot cancel appointment in status: {appointment.status}"
            )

        appointment.cancel(user_id, reason)
        appointment.updated_by = user_id

        logger.info(f"Appointment cancelled: {appointment.appointment_number}, Reason: {reason}")
        return appointment

    def mark_no_show(
        self,
        session: Session,
        appointment_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Appointment:
        """Mark appointment as no-show."""
        appointment = self._get_appointment(session, appointment_id)

        if appointment.status in Appointment.TERMINAL_STATUSES:
            raise InvalidStatusTransitionError(
                f"Cannot mark no-show for appointment in status: {appointment.status}"
            )

        appointment.mark_no_show(user_id, reason)
        appointment.updated_by = user_id

        logger.info(f"Appointment marked no-show: {appointment.appointment_number}")
        return appointment

    def reschedule(
        self,
        session: Session,
        appointment_id: UUID,
        new_date: date,
        new_time: time,
        new_staff_id: Optional[UUID] = None,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Appointment:
        """
        Reschedule an appointment.

        Creates a new appointment and marks the old one as rescheduled.
        """
        old_appointment = self._get_appointment(session, appointment_id)

        if not old_appointment.can_reschedule():
            raise InvalidStatusTransitionError(
                f"Cannot reschedule appointment in status: {old_appointment.status}"
            )

        # Create new appointment
        new_appointment = self.book_appointment(
            session=session,
            patient_id=old_appointment.patient_id,
            branch_id=old_appointment.branch_id,
            hospital_id=old_appointment.hospital_id,
            appointment_date=new_date,
            start_time=new_time,
            staff_id=new_staff_id or old_appointment.staff_id,
            appointment_type_id=old_appointment.appointment_type_id,
            service_id=old_appointment.service_id,
            package_id=old_appointment.package_id,
            chief_complaint=old_appointment.chief_complaint,
            priority=old_appointment.priority,
            booking_source=old_appointment.booking_source,
            patient_notes=old_appointment.patient_notes,
            is_follow_up=old_appointment.is_follow_up,
            parent_appointment_id=old_appointment.parent_appointment_id,
            user_id=user_id
        )

        # Link the appointments
        new_appointment.rescheduled_from_id = old_appointment.appointment_id
        new_appointment.reschedule_count = old_appointment.reschedule_count + 1

        # Mark old appointment as rescheduled
        old_appointment.status = Appointment.STATUS_RESCHEDULED
        old_appointment.internal_notes = (
            f"{old_appointment.internal_notes or ''}\n"
            f"Rescheduled to {new_appointment.appointment_number}: {reason or 'No reason provided'}"
        ).strip()
        old_appointment.updated_by = user_id

        # Release old slot
        if old_appointment.slot:
            old_appointment.slot.cancel_booking()

        logger.info(
            f"Appointment rescheduled: {old_appointment.appointment_number} -> "
            f"{new_appointment.appointment_number}"
        )

        return new_appointment

    # =========================================================================
    # QUEUE MANAGEMENT
    # =========================================================================

    def get_todays_queue(
        self,
        session: Session,
        branch_id: UUID,
        staff_id: Optional[UUID] = None,
        include_completed: bool = False
    ) -> List[Appointment]:
        """
        Get today's appointment queue for a branch/doctor.

        Ordered by priority (emergency first) then by start time.
        """
        today = date.today()

        query = session.query(Appointment).filter(
            Appointment.branch_id == branch_id,
            Appointment.appointment_date == today,
            Appointment.is_deleted == False
        )

        if staff_id:
            query = query.filter(Appointment.staff_id == staff_id)

        if not include_completed:
            query = query.filter(
                Appointment.status.notin_([
                    Appointment.STATUS_COMPLETED,
                    Appointment.STATUS_CANCELLED,
                    Appointment.STATUS_NO_SHOW
                ])
            )

        # Eager load relationships
        query = query.options(
            joinedload(Appointment.patient),
            joinedload(Appointment.staff),
            joinedload(Appointment.appointment_type)
        )

        # Order by priority then time
        query = query.order_by(
            # Priority order: emergency=1, urgent=2, normal=3
            case(
                (Appointment.priority == 'emergency', 1),
                (Appointment.priority == 'urgent', 2),
                else_=3
            ),
            Appointment.start_time
        )

        return query.all()

    def get_queue_by_date(
        self,
        session: Session,
        branch_id: UUID,
        target_date: date,
        staff_id: Optional[UUID] = None,
        include_completed: bool = False
    ) -> List[Appointment]:
        """
        Get appointment queue for a specific date.

        Ordered by priority (emergency first) then by start time.
        """
        query = session.query(Appointment).filter(
            Appointment.branch_id == branch_id,
            Appointment.appointment_date == target_date,
            Appointment.is_deleted == False
        )

        if staff_id:
            query = query.filter(Appointment.staff_id == staff_id)

        if not include_completed:
            query = query.filter(
                Appointment.status.notin_([
                    Appointment.STATUS_COMPLETED,
                    Appointment.STATUS_CANCELLED,
                    Appointment.STATUS_NO_SHOW
                ])
            )

        # Eager load relationships
        query = query.options(
            joinedload(Appointment.patient),
            joinedload(Appointment.staff),
            joinedload(Appointment.appointment_type)
        )

        # Order by priority then time
        query = query.order_by(
            case(
                (Appointment.priority == 'emergency', 1),
                (Appointment.priority == 'urgent', 2),
                else_=3
            ),
            Appointment.start_time
        )

        return query.all()

    def get_waiting_patients(
        self,
        session: Session,
        branch_id: UUID,
        staff_id: Optional[UUID] = None
    ) -> List[Appointment]:
        """Get patients currently waiting (checked in but not in progress)."""
        today = date.today()

        query = session.query(Appointment).filter(
            Appointment.branch_id == branch_id,
            Appointment.appointment_date == today,
            Appointment.status == Appointment.STATUS_CHECKED_IN,
            Appointment.is_deleted == False
        )

        if staff_id:
            query = query.filter(Appointment.staff_id == staff_id)

        query = query.options(joinedload(Appointment.patient))
        query = query.order_by(Appointment.checked_in_at)

        return query.all()

    def get_next_patient(
        self,
        session: Session,
        branch_id: UUID,
        staff_id: UUID
    ) -> Optional[Appointment]:
        """Get the next patient in queue for a doctor."""
        waiting = self.get_waiting_patients(session, branch_id, staff_id)
        return waiting[0] if waiting else None

    # =========================================================================
    # AVAILABILITY & SLOTS
    # =========================================================================

    def get_available_slots(
        self,
        session: Session,
        branch_id: UUID,
        target_date: date,
        staff_id: Optional[UUID] = None,
        service_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available appointment slots for a date.

        Returns list of slot dictionaries with availability info.
        """
        query = session.query(AppointmentSlot).filter(
            AppointmentSlot.branch_id == branch_id,
            AppointmentSlot.slot_date == target_date,
            AppointmentSlot.is_available == True,
            AppointmentSlot.is_blocked == False,
            AppointmentSlot.current_bookings < AppointmentSlot.max_bookings
        )

        if staff_id:
            query = query.filter(AppointmentSlot.staff_id == staff_id)

        query = query.options(joinedload(AppointmentSlot.staff))
        query = query.order_by(AppointmentSlot.start_time)

        slots = query.all()

        return [
            {
                'slot_id': str(slot.slot_id),
                'staff_id': str(slot.staff_id),
                'doctor_name': f"Dr. {slot.staff.first_name} {slot.staff.last_name or ''}".strip() if slot.staff else None,
                'date': slot.slot_date.isoformat(),
                'start_time': slot.start_time.isoformat(),
                'end_time': slot.end_time.isoformat(),
                'available_spots': slot.available_spots,
                'max_bookings': slot.max_bookings
            }
            for slot in slots
        ]

    def check_slot_availability(
        self,
        session: Session,
        staff_id: UUID,
        branch_id: UUID,
        target_date: date,
        start_time: time
    ) -> bool:
        """Check if a specific slot is available."""
        slot = self._find_available_slot(session, staff_id, branch_id, target_date, start_time)
        return slot is not None and slot.is_bookable

    # =========================================================================
    # QUERY METHODS
    # =========================================================================

    def get_appointment_by_id(
        self,
        session: Session,
        appointment_id: UUID
    ) -> Optional[Appointment]:
        """Get appointment by ID with all relationships loaded."""
        return session.query(Appointment).filter(
            Appointment.appointment_id == appointment_id,
            Appointment.is_deleted == False
        ).options(
            joinedload(Appointment.patient),
            joinedload(Appointment.staff),
            joinedload(Appointment.appointment_type),
            joinedload(Appointment.branch),
            joinedload(Appointment.service),
            joinedload(Appointment.package)
        ).first()

    def get_patient_appointments(
        self,
        session: Session,
        patient_id: UUID,
        include_past: bool = True,
        limit: int = 50
    ) -> List[Appointment]:
        """Get appointments for a patient."""
        query = session.query(Appointment).filter(
            Appointment.patient_id == patient_id,
            Appointment.is_deleted == False
        )

        if not include_past:
            query = query.filter(Appointment.appointment_date >= date.today())

        query = query.options(
            joinedload(Appointment.staff),
            joinedload(Appointment.appointment_type)
        )

        query = query.order_by(
            Appointment.appointment_date.desc(),
            Appointment.start_time.desc()
        )

        return query.limit(limit).all()

    def get_appointments_by_date_range(
        self,
        session: Session,
        branch_id: UUID,
        start_date: date,
        end_date: date,
        staff_id: Optional[UUID] = None,
        status: Optional[List[str]] = None
    ) -> List[Appointment]:
        """Get appointments within a date range."""
        query = session.query(Appointment).filter(
            Appointment.branch_id == branch_id,
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date,
            Appointment.is_deleted == False
        )

        if staff_id:
            query = query.filter(Appointment.staff_id == staff_id)

        if status:
            query = query.filter(Appointment.status.in_(status))

        query = query.options(
            joinedload(Appointment.patient),
            joinedload(Appointment.staff)
        )

        query = query.order_by(
            Appointment.appointment_date,
            Appointment.start_time
        )

        return query.all()

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_daily_stats(
        self,
        session: Session,
        branch_id: UUID,
        target_date: date,
        staff_id: Optional[UUID] = None
    ) -> Dict[str, int]:
        """Get appointment statistics for a day."""
        query = session.query(Appointment).filter(
            Appointment.branch_id == branch_id,
            Appointment.appointment_date == target_date,
            Appointment.is_deleted == False
        )

        if staff_id:
            query = query.filter(Appointment.staff_id == staff_id)

        appointments = query.all()

        stats = {
            'total': len(appointments),
            'requested': 0,
            'confirmed': 0,
            'checked_in': 0,
            'in_progress': 0,
            'completed': 0,
            'cancelled': 0,
            'no_show': 0,
            'avg_wait_time': 0
        }

        wait_times = []

        for apt in appointments:
            if apt.status in stats:
                stats[apt.status] += 1
            if apt.wait_time_minutes:
                wait_times.append(apt.wait_time_minutes)

        if wait_times:
            stats['avg_wait_time'] = sum(wait_times) // len(wait_times)

        return stats

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    def _get_appointment(self, session: Session, appointment_id: UUID) -> Appointment:
        """Get appointment by ID or raise error."""
        appointment = session.query(Appointment).filter(
            Appointment.appointment_id == appointment_id,
            Appointment.is_deleted == False
        ).first()

        if not appointment:
            raise AppointmentError(f"Appointment not found: {appointment_id}")

        return appointment

    def _find_available_slot(
        self,
        session: Session,
        staff_id: Optional[UUID],
        branch_id: UUID,
        target_date: date,
        start_time: time
    ) -> Optional[AppointmentSlot]:
        """Find an available slot matching the criteria."""
        if not staff_id:
            return None

        return session.query(AppointmentSlot).filter(
            AppointmentSlot.staff_id == staff_id,
            AppointmentSlot.branch_id == branch_id,
            AppointmentSlot.slot_date == target_date,
            AppointmentSlot.start_time == start_time,
            AppointmentSlot.is_available == True,
            AppointmentSlot.is_blocked == False,
            AppointmentSlot.current_bookings < AppointmentSlot.max_bookings
        ).first()

    def _create_slot_from_schedule(
        self,
        session: Session,
        staff_id: UUID,
        branch_id: UUID,
        target_date: date,
        start_time: time,
        duration: int
    ) -> Optional[AppointmentSlot]:
        """Create a slot if the doctor has a schedule for this time."""
        # Check if doctor has a schedule for this day/time
        day_of_week = (target_date.weekday() + 1) % 7  # Convert to our 0=Sunday format

        schedule = session.query(DoctorSchedule).filter(
            DoctorSchedule.staff_id == staff_id,
            DoctorSchedule.branch_id == branch_id,
            DoctorSchedule.day_of_week == day_of_week,
            DoctorSchedule.start_time <= start_time,
            DoctorSchedule.end_time > start_time,
            DoctorSchedule.is_active == True,
            DoctorSchedule.is_deleted == False
        ).first()

        if not schedule:
            return None

        # Check for exceptions
        exception = session.query(DoctorScheduleException).filter(
            DoctorScheduleException.staff_id == staff_id,
            DoctorScheduleException.exception_date == target_date,
            DoctorScheduleException.is_active == True,
            DoctorScheduleException.is_deleted == False,
            or_(
                DoctorScheduleException.branch_id == branch_id,
                DoctorScheduleException.branch_id.is_(None)
            )
        ).first()

        if exception:
            # Check if this specific time is blocked
            if exception.start_time is None or exception.end_time is None:
                # Full day exception
                return None
            if exception.start_time <= start_time < exception.end_time:
                return None

        # Calculate end time
        start_datetime = datetime.combine(target_date, start_time)
        end_datetime = start_datetime + timedelta(minutes=duration)

        # Create the slot
        slot = AppointmentSlot(
            staff_id=staff_id,
            branch_id=branch_id,
            schedule_id=schedule.schedule_id,
            slot_date=target_date,
            start_time=start_time,
            end_time=end_datetime.time(),
            max_bookings=schedule.max_patients_per_slot
        )

        session.add(slot)
        session.flush()

        return slot

    def _get_appointment_duration(
        self,
        session: Session,
        hospital_id: UUID,
        service_id: Optional[UUID],
        package_id: Optional[UUID],
        appointment_type_id: Optional[UUID]
    ) -> int:
        """
        Get appointment duration based on priority hierarchy.
        Priority: service > package > appointment_type > hospital default
        """
        # 1. Check service duration
        if service_id:
            from app.models.master import Service
            service = session.query(Service).filter(
                Service.service_id == service_id
            ).first()
            if service and hasattr(service, 'duration_minutes') and service.duration_minutes:
                return service.duration_minutes

        # 2. Check package session duration
        if package_id:
            from app.models.master import Package
            package = session.query(Package).filter(
                Package.package_id == package_id
            ).first()
            if package and hasattr(package, 'session_duration_minutes') and package.session_duration_minutes:
                return package.session_duration_minutes

        # 3. Check appointment type default
        if appointment_type_id:
            apt_type = session.query(AppointmentType).filter(
                AppointmentType.type_id == appointment_type_id
            ).first()
            if apt_type and apt_type.default_duration_minutes:
                return apt_type.default_duration_minutes

        # 4. Hospital default
        hospital = session.query(Hospital).filter(
            Hospital.hospital_id == hospital_id
        ).first()

        if hospital and hasattr(hospital, 'appointment_settings') and hospital.appointment_settings:
            return hospital.appointment_settings.get('default_slot_duration_minutes', 30)

        return 30  # Ultimate fallback

    def _get_next_token(
        self,
        session: Session,
        branch_id: UUID,
        target_date: date
    ) -> int:
        """Get the next token number for a branch on a given date."""
        max_token = session.query(func.max(Appointment.token_number)).filter(
            Appointment.branch_id == branch_id,
            Appointment.appointment_date == target_date,
            Appointment.token_number.isnot(None)
        ).scalar()

        return (max_token or 0) + 1

    def _queue_notification(
        self,
        session: Session,
        appointment: Appointment,
        notification_type: str
    ):
        """Queue a notification for an appointment."""
        # Get patient phone
        patient = session.query(Patient).filter(
            Patient.patient_id == appointment.patient_id
        ).first()

        if not patient or not patient.phone_number:
            logger.warning(f"Cannot send {notification_type}: No phone for patient {appointment.patient_id}")
            return

        reminder = AppointmentReminder(
            appointment_id=appointment.appointment_id,
            reminder_type=notification_type,
            channel='whatsapp',  # Default to WhatsApp
            recipient_phone=patient.phone_number,
            status='pending'
        )

        session.add(reminder)
        logger.info(f"Queued {notification_type} notification for {appointment.appointment_number}")


# Create singleton instance
appointment_service = AppointmentService()
