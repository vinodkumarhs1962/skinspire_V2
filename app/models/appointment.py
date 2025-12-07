# app/models/appointment.py
"""
Appointment System Models
Phase 1 of Patient Lifecycle System

Models for managing:
- Appointment types (master data)
- Doctor schedules (weekly templates)
- Appointment slots (generated time slots)
- Appointments (booked appointments)
- Status history (audit trail)
- Schedule exceptions (leaves, holidays)
- Reminders (notification tracking)
"""

from sqlalchemy import (
    Column, String, ForeignKey, Boolean, Text, Integer, DateTime, Date, Time,
    Numeric, CheckConstraint, UniqueConstraint, Index, func, event
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone, time, date, timedelta

from .base import Base, TimestampMixin, SoftDeleteMixin, generate_uuid


class AppointmentType(Base, TimestampMixin, SoftDeleteMixin):
    """
    Master data for appointment categories.
    Defines different types of appointments with their default configurations.
    """
    __tablename__ = 'appointment_types'

    type_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    type_code = Column(String(20), nullable=False, unique=True)
    type_name = Column(String(100), nullable=False)
    description = Column(Text)

    # Configuration
    default_duration_minutes = Column(Integer, nullable=False, default=30)
    requires_doctor = Column(Boolean, default=True)
    allow_self_booking = Column(Boolean, default=True)
    allow_walk_in = Column(Boolean, default=True)
    requires_consent = Column(Boolean, default=False)

    # Pricing (optional)
    base_fee = Column(Numeric(10, 2))

    # Display
    color_code = Column(String(7))  # Hex color for calendar
    icon_name = Column(String(50))
    display_order = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    appointments = relationship("Appointment", back_populates="appointment_type")

    def __repr__(self):
        return f"<AppointmentType {self.type_code}: {self.type_name}>"

    @classmethod
    def get_by_code(cls, session, code: str):
        """Get appointment type by code."""
        return session.query(cls).filter(
            cls.type_code == code,
            cls.is_deleted == False,
            cls.is_active == True
        ).first()


class DoctorSchedule(Base, TimestampMixin, SoftDeleteMixin):
    """
    Weekly schedule template for doctors.
    Defines recurring availability patterns.
    """
    __tablename__ = 'doctor_schedules'

    schedule_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)

    # Schedule definition
    day_of_week = Column(Integer, nullable=False)  # 0=Sunday, 6=Saturday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Slot configuration
    slot_duration_minutes = Column(Integer, nullable=False, default=30)
    max_patients_per_slot = Column(Integer, default=1)

    # Break time (optional)
    break_start_time = Column(Time)
    break_end_time = Column(Time)

    # Room/Resource
    room_id = Column(UUID(as_uuid=True))
    room_name = Column(String(100))

    # Status
    is_active = Column(Boolean, default=True)
    effective_from = Column(Date)
    effective_until = Column(Date)

    # Relationships
    staff = relationship("Staff", backref="schedules")
    branch = relationship("Branch", backref="doctor_schedules")
    slots = relationship("AppointmentSlot", back_populates="schedule")

    __table_args__ = (
        CheckConstraint('day_of_week BETWEEN 0 AND 6', name='valid_day_of_week'),
        CheckConstraint('start_time < end_time', name='valid_time_range'),
        CheckConstraint('slot_duration_minutes > 0', name='positive_duration'),
        CheckConstraint('max_patients_per_slot > 0', name='positive_max_patients'),
        UniqueConstraint('staff_id', 'branch_id', 'day_of_week', 'start_time',
                        name='unique_schedule_slot'),
    )

    def __repr__(self):
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        return f"<DoctorSchedule {days[self.day_of_week]} {self.start_time}-{self.end_time}>"

    @property
    def day_name(self) -> str:
        """Get the name of the day."""
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        return days[self.day_of_week]

    def get_slots_for_date(self, target_date: date) -> list:
        """
        Generate time slots for a specific date based on this schedule.
        Returns list of (start_time, end_time) tuples.
        """
        if target_date.weekday() != (self.day_of_week - 1) % 7:
            # weekday() returns 0=Monday, but our day_of_week is 0=Sunday
            return []

        slots = []
        current = datetime.combine(target_date, self.start_time)
        end = datetime.combine(target_date, self.end_time)
        duration = timedelta(minutes=self.slot_duration_minutes)

        while current + duration <= end:
            slot_end = current + duration

            # Skip if slot overlaps with break time
            if self.break_start_time and self.break_end_time:
                break_start = datetime.combine(target_date, self.break_start_time)
                break_end = datetime.combine(target_date, self.break_end_time)
                if current < break_end and slot_end > break_start:
                    current = break_end
                    continue

            slots.append((current.time(), slot_end.time()))
            current = slot_end

        return slots


class AppointmentSlot(Base):
    """
    Generated time slots for appointment booking.
    Created from DoctorSchedule templates for specific dates.
    """
    __tablename__ = 'appointment_slots'

    slot_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    # References
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey('doctor_schedules.schedule_id'))

    # Slot timing
    slot_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Capacity
    max_bookings = Column(Integer, default=1)
    current_bookings = Column(Integer, default=0)

    # Availability
    is_available = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    block_reason = Column(String(255))
    blocked_by = Column(UUID(as_uuid=True))
    blocked_at = Column(DateTime(timezone=True))

    # Audit
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    staff = relationship("Staff", backref="appointment_slots")
    branch = relationship("Branch", backref="appointment_slots")
    schedule = relationship("DoctorSchedule", back_populates="slots")
    appointments = relationship("Appointment", back_populates="slot")

    __table_args__ = (
        CheckConstraint('start_time < end_time', name='slot_valid_time'),
        CheckConstraint('current_bookings <= max_bookings', name='valid_bookings'),
        CheckConstraint('max_bookings > 0', name='positive_max'),
        CheckConstraint('current_bookings >= 0', name='non_negative_bookings'),
        UniqueConstraint('staff_id', 'branch_id', 'slot_date', 'start_time',
                        name='unique_slot'),
        Index('idx_slots_date', 'slot_date'),
        Index('idx_slots_available', 'slot_date', 'staff_id', 'is_available', 'is_blocked'),
    )

    def __repr__(self):
        return f"<AppointmentSlot {self.slot_date} {self.start_time}-{self.end_time}>"

    @hybrid_property
    def available_spots(self) -> int:
        """Number of spots still available for booking."""
        return self.max_bookings - self.current_bookings

    @hybrid_property
    def is_bookable(self) -> bool:
        """Check if this slot can accept more bookings."""
        return (
            self.is_available and
            not self.is_blocked and
            self.current_bookings < self.max_bookings
        )

    def book(self) -> bool:
        """
        Increment booking count. Returns True if successful.
        """
        if not self.is_bookable:
            return False

        self.current_bookings += 1
        if self.current_bookings >= self.max_bookings:
            self.is_available = False
        self.updated_at = datetime.now(timezone.utc)
        return True

    def cancel_booking(self) -> bool:
        """
        Decrement booking count on cancellation.
        """
        if self.current_bookings > 0:
            self.current_bookings -= 1
            self.is_available = True
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False

    def block(self, reason: str, blocked_by=None):
        """Block this slot from booking."""
        self.is_blocked = True
        self.block_reason = reason
        self.blocked_by = blocked_by
        self.blocked_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def unblock(self):
        """Unblock this slot."""
        self.is_blocked = False
        self.block_reason = None
        self.blocked_by = None
        self.blocked_at = None
        self.updated_at = datetime.now(timezone.utc)


class Appointment(Base, TimestampMixin, SoftDeleteMixin):
    """
    Main appointments table for scheduling patient visits.
    Tracks the complete lifecycle of an appointment from booking to completion.
    """
    __tablename__ = 'appointments'

    appointment_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    appointment_number = Column(String(20), nullable=False, unique=True)

    # References
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'))  # Doctor
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    slot_id = Column(UUID(as_uuid=True), ForeignKey('appointment_slots.slot_id'))
    appointment_type_id = Column(UUID(as_uuid=True), ForeignKey('appointment_types.type_id'))

    # Service/Package reference (determines duration)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'))
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'))
    package_plan_id = Column(UUID(as_uuid=True), ForeignKey('package_payment_plans.plan_id'))  # Patient's package enrollment
    procedure_order_id = Column(UUID(as_uuid=True))  # Will reference procedure_orders in Phase 4

    # Appointment purpose (what the appointment is for)
    appointment_purpose = Column(String(30))  # consultation, follow_up, procedure, service, package_session

    # Scheduling
    appointment_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time)
    estimated_duration_minutes = Column(Integer, default=30)

    # Actual timing
    actual_start_time = Column(DateTime(timezone=True))
    actual_end_time = Column(DateTime(timezone=True))
    wait_time_minutes = Column(Integer)

    # Status workflow
    status = Column(String(20), nullable=False, default='requested')
    # Values: requested, confirmed, checked_in, in_progress, completed, cancelled, no_show, rescheduled

    # Booking info
    booking_source = Column(String(20), nullable=False, default='front_desk')
    # Values: front_desk, self_service, whatsapp, phone, walk_in, referral
    booking_channel = Column(String(50))

    # Clinical info
    chief_complaint = Column(Text)
    priority = Column(String(10), default='normal')  # normal, urgent, emergency

    # Follow-up tracking
    parent_appointment_id = Column(UUID(as_uuid=True), ForeignKey('appointments.appointment_id'))
    is_follow_up = Column(Boolean, default=False)
    follow_up_of_consultation_id = Column(UUID(as_uuid=True))

    # Reschedule tracking
    rescheduled_from_id = Column(UUID(as_uuid=True), ForeignKey('appointments.appointment_id'))
    reschedule_count = Column(Integer, default=0)

    # Notes
    patient_notes = Column(Text)
    internal_notes = Column(Text)
    cancellation_reason = Column(Text)
    no_show_reason = Column(Text)

    # Reminders
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime(timezone=True))
    reminder_type = Column(String(20))
    confirmation_sent = Column(Boolean, default=False)
    confirmation_sent_at = Column(DateTime(timezone=True))

    # Check-in
    checked_in_at = Column(DateTime(timezone=True))
    checked_in_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    token_number = Column(Integer)

    # Confirmation
    confirmed_at = Column(DateTime(timezone=True))
    confirmed_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))

    # Completion
    completed_at = Column(DateTime(timezone=True))
    completed_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    consultation_id = Column(UUID(as_uuid=True))  # Link to consultation record

    # Cancellation
    cancelled_at = Column(DateTime(timezone=True))
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))

    # Resource Allocation (Added 2025-12-05)
    room_id = Column(UUID(as_uuid=True), ForeignKey('rooms.room_id'))  # Primary room for appointment
    therapist_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'))  # Therapist/nurse assigned
    resource_allocation_status = Column(String(20), default='pending')  # pending, partial, complete, not_required

    # Approval workflow
    requires_approval = Column(Boolean, default=True)  # Most appointments need front desk approval
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(String(100))  # User who approved

    # External integrations data (Google Calendar event ID, etc.)
    external_refs = Column(JSONB, default={})

    # Relationships
    patient = relationship("Patient", backref="appointments")
    staff = relationship("Staff", foreign_keys=[staff_id], backref="doctor_appointments")
    therapist = relationship("Staff", foreign_keys=[therapist_id], backref="therapist_appointments")
    room = relationship("Room", backref="appointments")
    branch = relationship("Branch", backref="appointments")
    hospital = relationship("Hospital", backref="appointments")
    slot = relationship("AppointmentSlot", back_populates="appointments")
    appointment_type = relationship("AppointmentType", back_populates="appointments")
    service = relationship("Service", backref="appointments")
    package = relationship("Package", backref="appointments")
    package_plan = relationship("PackagePaymentPlan", backref="appointments")
    allocated_resources = relationship("AppointmentResource", backref="appointment")

    # Self-referential relationships
    parent_appointment = relationship("Appointment", foreign_keys=[parent_appointment_id],
                                      remote_side=[appointment_id], backref="follow_up_appointments")
    rescheduled_from = relationship("Appointment", foreign_keys=[rescheduled_from_id],
                                   remote_side=[appointment_id], backref="rescheduled_appointments")

    # Status history
    status_history = relationship("AppointmentStatusHistory", back_populates="appointment",
                                 order_by="AppointmentStatusHistory.changed_at")
    reminders = relationship("AppointmentReminder", back_populates="appointment",
                            order_by="AppointmentReminder.created_at")

    __table_args__ = (
        Index('idx_appointments_patient', 'patient_id'),
        Index('idx_appointments_staff', 'staff_id'),
        Index('idx_appointments_date', 'appointment_date'),
        Index('idx_appointments_status', 'status'),
        Index('idx_appointments_date_status', 'appointment_date', 'status'),
        Index('idx_appointments_date_staff', 'appointment_date', 'staff_id'),
    )

    # Status constants
    STATUS_REQUESTED = 'requested'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CHECKED_IN = 'checked_in'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_NO_SHOW = 'no_show'
    STATUS_RESCHEDULED = 'rescheduled'

    ACTIVE_STATUSES = [STATUS_REQUESTED, STATUS_CONFIRMED, STATUS_CHECKED_IN, STATUS_IN_PROGRESS]
    TERMINAL_STATUSES = [STATUS_COMPLETED, STATUS_CANCELLED, STATUS_NO_SHOW, STATUS_RESCHEDULED]

    BOOKING_SOURCES = ['front_desk', 'scheduled', 'online', 'phone', 'walk_in', 'app', 'kiosk']
    APPOINTMENT_PURPOSES = ['consultation', 'follow_up', 'procedure', 'service', 'package_session']
    PRIORITIES = ['normal', 'urgent', 'emergency']

    def __repr__(self):
        return f"<Appointment {self.appointment_number} - {self.status}>"

    @hybrid_property
    def is_active(self) -> bool:
        """Check if appointment is in an active (non-terminal) state."""
        return self.status in self.ACTIVE_STATUSES

    @hybrid_property
    def is_terminal(self) -> bool:
        """Check if appointment is in a terminal state."""
        return self.status in self.TERMINAL_STATUSES

    @hybrid_property
    def datetime_scheduled(self) -> datetime:
        """Get scheduled datetime as a single datetime object."""
        return datetime.combine(self.appointment_date, self.start_time)

    def confirm(self, user_id=None):
        """Confirm the appointment."""
        if self.status != self.STATUS_REQUESTED:
            raise ValueError(f"Cannot confirm appointment in status: {self.status}")

        self.status = self.STATUS_CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)
        self.confirmed_by = user_id

    def check_in(self, user_id=None, token_number=None):
        """Check in the patient."""
        if self.status not in [self.STATUS_REQUESTED, self.STATUS_CONFIRMED]:
            raise ValueError(f"Cannot check in appointment in status: {self.status}")

        self.status = self.STATUS_CHECKED_IN
        self.checked_in_at = datetime.now(timezone.utc)
        self.checked_in_by = user_id
        if token_number:
            self.token_number = token_number

    def start(self, user_id=None):
        """Start the appointment (patient with doctor)."""
        if self.status != self.STATUS_CHECKED_IN:
            raise ValueError(f"Cannot start appointment in status: {self.status}")

        self.status = self.STATUS_IN_PROGRESS
        self.actual_start_time = datetime.now(timezone.utc)

        # Calculate wait time
        if self.checked_in_at:
            wait_delta = self.actual_start_time - self.checked_in_at
            self.wait_time_minutes = int(wait_delta.total_seconds() / 60)

    def complete(self, user_id=None, consultation_id=None):
        """Mark appointment as completed."""
        if self.status != self.STATUS_IN_PROGRESS:
            raise ValueError(f"Cannot complete appointment in status: {self.status}")

        self.status = self.STATUS_COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.completed_by = user_id
        self.actual_end_time = datetime.now(timezone.utc)
        if consultation_id:
            self.consultation_id = consultation_id

    def cancel(self, user_id=None, reason=None):
        """Cancel the appointment."""
        if self.status in self.TERMINAL_STATUSES:
            raise ValueError(f"Cannot cancel appointment in status: {self.status}")

        # Release the slot if booked
        if self.slot:
            self.slot.cancel_booking()

        self.status = self.STATUS_CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        self.cancelled_by = user_id
        self.cancellation_reason = reason

    def mark_no_show(self, user_id=None, reason=None):
        """Mark appointment as no-show."""
        if self.status in self.TERMINAL_STATUSES:
            raise ValueError(f"Cannot mark no-show for appointment in status: {self.status}")

        # Release the slot if booked
        if self.slot:
            self.slot.cancel_booking()

        self.status = self.STATUS_NO_SHOW
        self.no_show_reason = reason

    def can_reschedule(self) -> bool:
        """Check if appointment can be rescheduled."""
        return self.status in [self.STATUS_REQUESTED, self.STATUS_CONFIRMED]


class AppointmentStatusHistory(Base):
    """
    Audit trail for appointment status changes.
    Automatically populated by database trigger.
    """
    __tablename__ = 'appointment_status_history'

    history_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey('appointments.appointment_id'), nullable=False)

    # Status change
    old_status = Column(String(20))
    new_status = Column(String(20), nullable=False)

    # Change info
    changed_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    change_reason = Column(Text)
    change_source = Column(String(50))  # user, system, automation

    # Additional context
    additional_data = Column(JSONB)

    # Timestamp
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    appointment = relationship("Appointment", back_populates="status_history")

    __table_args__ = (
        Index('idx_status_history_appointment', 'appointment_id'),
        Index('idx_status_history_date', 'changed_at'),
    )

    def __repr__(self):
        return f"<StatusHistory {self.old_status} -> {self.new_status}>"


class DoctorScheduleException(Base, TimestampMixin, SoftDeleteMixin):
    """
    Exceptions to doctor schedules: leaves, holidays, meeting blocks.
    """
    __tablename__ = 'doctor_schedule_exceptions'

    exception_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    staff_id = Column(UUID(as_uuid=True), ForeignKey('staff.staff_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))  # NULL = all branches

    # Exception period
    exception_date = Column(Date, nullable=False)
    start_time = Column(Time)  # NULL = whole day
    end_time = Column(Time)

    # Exception type
    exception_type = Column(String(30), nullable=False)
    # Types: leave, holiday, meeting, training, block, other

    # Details
    reason = Column(Text)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(JSONB)  # For recurring exceptions

    # Status
    is_active = Column(Boolean, default=True)

    # Approval (for leave requests)
    requires_approval = Column(Boolean, default=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    approved_at = Column(DateTime(timezone=True))
    approval_status = Column(String(20), default='approved')  # pending, approved, rejected

    # Relationships
    staff = relationship("Staff", backref="schedule_exceptions")
    branch = relationship("Branch", backref="schedule_exceptions")

    EXCEPTION_TYPES = ['leave', 'holiday', 'meeting', 'training', 'block', 'other']

    def __repr__(self):
        return f"<ScheduleException {self.exception_type} on {self.exception_date}>"

    @hybrid_property
    def is_full_day(self) -> bool:
        """Check if this is a full-day exception."""
        return self.start_time is None or self.end_time is None


class AppointmentReminder(Base):
    """
    Log of appointment reminders and notifications sent to patients.
    """
    __tablename__ = 'appointment_reminders'

    reminder_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey('appointments.appointment_id'), nullable=False)

    # Reminder details
    reminder_type = Column(String(20), nullable=False)  # confirmation, reminder_24h, reminder_1h, follow_up
    channel = Column(String(20), nullable=False)  # sms, whatsapp, email, push

    # Recipient
    recipient_phone = Column(String(15))
    recipient_email = Column(String(255))

    # Message
    message_template = Column(String(100))
    message_content = Column(Text)

    # Status
    status = Column(String(20), default='pending')  # pending, sent, delivered, failed, cancelled
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))

    # Response (for WhatsApp confirmations)
    response_received = Column(Boolean, default=False)
    response_text = Column(Text)
    response_at = Column(DateTime(timezone=True))

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Audit
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    appointment = relationship("Appointment", back_populates="reminders")

    REMINDER_TYPES = ['confirmation', 'reminder_24h', 'reminder_1h', 'follow_up', 'reschedule']
    CHANNELS = ['sms', 'whatsapp', 'email', 'push']
    STATUSES = ['pending', 'sent', 'delivered', 'failed', 'cancelled']

    __table_args__ = (
        Index('idx_reminders_appointment', 'appointment_id'),
        Index('idx_reminders_status', 'status'),
    )

    def __repr__(self):
        return f"<Reminder {self.reminder_type} via {self.channel} - {self.status}>"

    def mark_sent(self):
        """Mark reminder as sent."""
        self.status = 'sent'
        self.sent_at = datetime.now(timezone.utc)

    def mark_delivered(self):
        """Mark reminder as delivered."""
        self.status = 'delivered'
        self.delivered_at = datetime.now(timezone.utc)

    def mark_failed(self, error_message: str):
        """Mark reminder as failed."""
        self.status = 'failed'
        self.error_message = error_message
        self.retry_count += 1

    def record_response(self, response_text: str):
        """Record patient's response to reminder."""
        self.response_received = True
        self.response_text = response_text
        self.response_at = datetime.now(timezone.utc)
