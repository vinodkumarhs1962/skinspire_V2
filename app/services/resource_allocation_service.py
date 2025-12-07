# app/services/resource_allocation_service.py
"""
Resource Allocation Service
Part of the Resource Management System

Handles resource (rooms, staff) allocation for appointments:
- Finding available rooms and staff for time slots
- Allocating resources to appointments
- Checking for conflicts
- Auto-suggesting resources based on service requirements
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy import and_, or_, func, not_
from sqlalchemy.orm import Session, joinedload

from app.models.master import (
    Room, RoomSlot, ServiceResourceRequirement, AppointmentResource,
    Staff, Service, Branch
)
from app.models.appointment import Appointment

logger = logging.getLogger(__name__)


class ResourceAllocationError(Exception):
    """Base exception for resource allocation errors."""
    pass


class ResourceNotAvailableError(ResourceAllocationError):
    """Raised when a requested resource is not available."""
    pass


class ResourceConflictError(ResourceAllocationError):
    """Raised when there's a resource conflict."""
    pass


class ResourceAllocationService:
    """
    Service for managing resource allocation in appointments.

    Provides methods for:
    - Finding available rooms and staff
    - Allocating resources to appointments
    - Checking resource requirements
    - Validating allocations
    """

    def __init__(self):
        """Initialize the resource allocation service."""
        pass

    # =========================================================================
    # ROOM AVAILABILITY
    # =========================================================================

    def get_available_rooms(
        self,
        session: Session,
        branch_id: UUID,
        target_date: date,
        start_time: time,
        end_time: time,
        room_type: Optional[str] = None
    ) -> List[Room]:
        """
        Get available rooms for a specific time slot.

        Args:
            session: Database session
            branch_id: Branch UUID
            target_date: Date to check
            start_time: Start time of slot
            end_time: End time of slot
            room_type: Optional room type filter

        Returns:
            List of available Room objects
        """
        # Get all active rooms for the branch
        query = session.query(Room).filter(
            Room.branch_id == branch_id,
            Room.is_active == True,
            Room.is_deleted == False
        )

        if room_type:
            query = query.filter(Room.room_type == room_type)

        all_rooms = query.all()

        # Filter out rooms that have conflicting allocations
        available_rooms = []
        start_str = start_time.strftime('%H:%M:%S') if isinstance(start_time, time) else start_time
        end_str = end_time.strftime('%H:%M:%S') if isinstance(end_time, time) else end_time

        for room in all_rooms:
            if self._is_room_available(session, room.room_id, target_date, start_str, end_str):
                available_rooms.append(room)

        return available_rooms

    def _is_room_available(
        self,
        session: Session,
        room_id: UUID,
        target_date: date,
        start_time: str,
        end_time: str
    ) -> bool:
        """Check if a specific room is available for the given time slot."""
        # Check for conflicting room allocations
        conflict = session.query(AppointmentResource).filter(
            AppointmentResource.resource_type == 'room',
            AppointmentResource.resource_id == room_id,
            AppointmentResource.allocation_date == target_date,
            AppointmentResource.status.in_(['allocated', 'in_use']),
            # Time overlap check: NOT (new_end <= existing_start OR new_start >= existing_end)
            not_(
                or_(
                    AppointmentResource.start_time >= end_time,
                    AppointmentResource.end_time <= start_time
                )
            )
        ).first()

        return conflict is None

    def get_room_schedule(
        self,
        session: Session,
        room_id: UUID,
        target_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get the schedule of a room for a specific date.
        Shows all allocations and available slots.
        """
        room = session.query(Room).filter_by(room_id=room_id).first()
        if not room:
            return []

        # Get all allocations for the day
        allocations = session.query(AppointmentResource).filter(
            AppointmentResource.resource_type == 'room',
            AppointmentResource.resource_id == room_id,
            AppointmentResource.allocation_date == target_date,
            AppointmentResource.status.in_(['allocated', 'in_use'])
        ).order_by(AppointmentResource.start_time).all()

        schedule = []
        for alloc in allocations:
            # Get appointment details
            appointment = session.query(Appointment).filter_by(
                appointment_id=alloc.appointment_id
            ).first()

            schedule.append({
                'allocation_id': str(alloc.allocation_id),
                'appointment_id': str(alloc.appointment_id),
                'appointment_number': appointment.appointment_number if appointment else None,
                'start_time': alloc.start_time,
                'end_time': alloc.end_time,
                'status': alloc.status,
                'patient_id': str(appointment.patient_id) if appointment else None
            })

        return schedule

    # =========================================================================
    # STAFF AVAILABILITY
    # =========================================================================

    def get_available_staff(
        self,
        session: Session,
        branch_id: UUID,
        hospital_id: UUID,
        target_date: date,
        start_time: time,
        end_time: time,
        staff_type: Optional[str] = None,
        exclude_doctors: bool = True
    ) -> List[Staff]:
        """
        Get available staff (therapists, nurses) for a specific time slot.

        Args:
            session: Database session
            branch_id: Branch UUID
            hospital_id: Hospital UUID
            target_date: Date to check
            start_time: Start time of slot
            end_time: End time of slot
            staff_type: Optional staff type filter ('therapist', 'nurse', etc.)
            exclude_doctors: If True, exclude doctors (they're assigned separately)

        Returns:
            List of available Staff objects
        """
        # Get all active staff for the hospital
        query = session.query(Staff).filter(
            Staff.hospital_id == hospital_id,
            Staff.is_active == True,
            Staff.is_deleted == False
        )

        if staff_type:
            query = query.filter(Staff.staff_type == staff_type)
        elif exclude_doctors:
            query = query.filter(Staff.staff_type != 'doctor')

        all_staff = query.all()

        # Filter out staff that have conflicting allocations
        available_staff = []
        start_str = start_time.strftime('%H:%M:%S') if isinstance(start_time, time) else start_time
        end_str = end_time.strftime('%H:%M:%S') if isinstance(end_time, time) else end_time

        for staff in all_staff:
            if self._is_staff_available(session, staff.staff_id, target_date, start_str, end_str):
                available_staff.append(staff)

        return available_staff

    def _is_staff_available(
        self,
        session: Session,
        staff_id: UUID,
        target_date: date,
        start_time: str,
        end_time: str
    ) -> bool:
        """Check if a specific staff member is available for the given time slot."""
        # Check for conflicting staff allocations
        conflict = session.query(AppointmentResource).filter(
            AppointmentResource.resource_type == 'staff',
            AppointmentResource.resource_id == staff_id,
            AppointmentResource.allocation_date == target_date,
            AppointmentResource.status.in_(['allocated', 'in_use']),
            # Time overlap check
            not_(
                or_(
                    AppointmentResource.start_time >= end_time,
                    AppointmentResource.end_time <= start_time
                )
            )
        ).first()

        return conflict is None

    def get_staff_schedule(
        self,
        session: Session,
        staff_id: UUID,
        target_date: date
    ) -> List[Dict[str, Any]]:
        """Get the schedule of a staff member for a specific date."""
        allocations = session.query(AppointmentResource).filter(
            AppointmentResource.resource_type == 'staff',
            AppointmentResource.resource_id == staff_id,
            AppointmentResource.allocation_date == target_date,
            AppointmentResource.status.in_(['allocated', 'in_use'])
        ).order_by(AppointmentResource.start_time).all()

        schedule = []
        for alloc in allocations:
            appointment = session.query(Appointment).filter_by(
                appointment_id=alloc.appointment_id
            ).first()

            schedule.append({
                'allocation_id': str(alloc.allocation_id),
                'appointment_id': str(alloc.appointment_id),
                'appointment_number': appointment.appointment_number if appointment else None,
                'start_time': alloc.start_time,
                'end_time': alloc.end_time,
                'status': alloc.status,
                'role': alloc.role
            })

        return schedule

    # =========================================================================
    # SERVICE RESOURCE REQUIREMENTS
    # =========================================================================

    def get_service_requirements(
        self,
        session: Session,
        service_id: UUID
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get resource requirements for a service.

        Returns:
            Dict with 'room' and 'staff' lists of requirements
        """
        requirements = session.query(ServiceResourceRequirement).filter(
            ServiceResourceRequirement.service_id == service_id,
            ServiceResourceRequirement.is_active == True
        ).all()

        result = {'room': [], 'staff': []}

        for req in requirements:
            req_data = {
                'requirement_id': str(req.requirement_id),
                'is_mandatory': req.is_mandatory,
                'quantity_required': req.quantity_required,
                'duration_minutes': req.duration_minutes,
                'notes': req.notes
            }

            if req.resource_type == 'room':
                req_data['room_type'] = req.room_type
                result['room'].append(req_data)
            elif req.resource_type == 'staff':
                req_data['staff_type'] = req.staff_type
                req_data['staff_role'] = req.staff_role
                result['staff'].append(req_data)

        return result

    def suggest_resources(
        self,
        session: Session,
        appointment_id: UUID
    ) -> Dict[str, Any]:
        """
        Auto-suggest resources for an appointment based on service requirements.

        Returns dict with suggested room and staff, or None if not available.
        """
        appointment = session.query(Appointment).filter_by(
            appointment_id=appointment_id
        ).first()

        if not appointment:
            raise ResourceAllocationError(f"Appointment not found: {appointment_id}")

        if not appointment.service_id:
            return {'room': None, 'staff': [], 'message': 'No service linked to appointment'}

        # Get service requirements
        requirements = self.get_service_requirements(session, appointment.service_id)

        suggestions = {'room': None, 'staff': [], 'warnings': []}

        # Get appointment timing
        appt_date = appointment.appointment_date
        start_time = appointment.start_time
        end_time = appointment.end_time or (
            datetime.combine(appt_date, start_time) +
            timedelta(minutes=appointment.estimated_duration_minutes or 30)
        ).time()

        # Suggest room
        if requirements['room']:
            for room_req in requirements['room']:
                available_rooms = self.get_available_rooms(
                    session=session,
                    branch_id=appointment.branch_id,
                    target_date=appt_date,
                    start_time=start_time,
                    end_time=end_time,
                    room_type=room_req.get('room_type')
                )

                if available_rooms:
                    room = available_rooms[0]
                    suggestions['room'] = {
                        'room_id': str(room.room_id),
                        'room_code': room.room_code,
                        'room_name': room.room_name,
                        'room_type': room.room_type
                    }
                elif room_req.get('is_mandatory'):
                    suggestions['warnings'].append(
                        f"No {room_req.get('room_type')} room available for this time slot"
                    )

        # Suggest staff
        if requirements['staff']:
            for staff_req in requirements['staff']:
                available_staff = self.get_available_staff(
                    session=session,
                    branch_id=appointment.branch_id,
                    hospital_id=appointment.hospital_id,
                    target_date=appt_date,
                    start_time=start_time,
                    end_time=end_time,
                    staff_type=staff_req.get('staff_type')
                )

                if available_staff:
                    staff = available_staff[0]
                    suggestions['staff'].append({
                        'staff_id': str(staff.staff_id),
                        'staff_name': f"{staff.first_name} {staff.last_name or ''}".strip(),
                        'staff_type': staff.staff_type,
                        'role': staff_req.get('staff_role')
                    })
                elif staff_req.get('is_mandatory'):
                    suggestions['warnings'].append(
                        f"No {staff_req.get('staff_type')} available for this time slot"
                    )

        return suggestions

    # =========================================================================
    # RESOURCE ALLOCATION
    # =========================================================================

    def allocate_room(
        self,
        session: Session,
        appointment_id: UUID,
        room_id: UUID,
        user_id: Optional[str] = None
    ) -> AppointmentResource:
        """
        Allocate a room to an appointment.

        Args:
            session: Database session
            appointment_id: Appointment UUID
            room_id: Room UUID to allocate
            user_id: User making the allocation

        Returns:
            Created AppointmentResource object

        Raises:
            ResourceNotAvailableError: If room is not available
        """
        appointment = session.query(Appointment).filter_by(
            appointment_id=appointment_id
        ).first()

        if not appointment:
            raise ResourceAllocationError(f"Appointment not found: {appointment_id}")

        room = session.query(Room).filter_by(room_id=room_id).first()
        if not room:
            raise ResourceAllocationError(f"Room not found: {room_id}")

        # Get timing
        appt_date = appointment.appointment_date
        start_time = appointment.start_time.strftime('%H:%M:%S')
        end_time = appointment.end_time.strftime('%H:%M:%S') if appointment.end_time else (
            datetime.combine(appt_date, appointment.start_time) +
            timedelta(minutes=appointment.estimated_duration_minutes or 30)
        ).time().strftime('%H:%M:%S')

        # Check availability
        if not self._is_room_available(session, room_id, appt_date, start_time, end_time):
            raise ResourceNotAvailableError(
                f"Room {room.room_code} is not available for this time slot"
            )

        # Create allocation
        allocation = AppointmentResource(
            appointment_id=appointment_id,
            resource_type='room',
            resource_id=room_id,
            allocation_date=appt_date,
            start_time=start_time,
            end_time=end_time,
            status='allocated',
            allocated_by=user_id
        )

        session.add(allocation)

        # Update appointment room_id
        appointment.room_id = room_id
        self._update_allocation_status(session, appointment)

        session.flush()

        logger.info(f"Room {room.room_code} allocated to appointment {appointment.appointment_number}")
        return allocation

    def allocate_staff(
        self,
        session: Session,
        appointment_id: UUID,
        staff_id: UUID,
        role: str = 'primary_therapist',
        user_id: Optional[str] = None
    ) -> AppointmentResource:
        """
        Allocate a staff member to an appointment.

        Args:
            session: Database session
            appointment_id: Appointment UUID
            staff_id: Staff UUID to allocate
            role: Role of the staff in this appointment
            user_id: User making the allocation

        Returns:
            Created AppointmentResource object

        Raises:
            ResourceNotAvailableError: If staff is not available
        """
        appointment = session.query(Appointment).filter_by(
            appointment_id=appointment_id
        ).first()

        if not appointment:
            raise ResourceAllocationError(f"Appointment not found: {appointment_id}")

        staff = session.query(Staff).filter_by(staff_id=staff_id).first()
        if not staff:
            raise ResourceAllocationError(f"Staff not found: {staff_id}")

        # Get timing
        appt_date = appointment.appointment_date
        start_time = appointment.start_time.strftime('%H:%M:%S')
        end_time = appointment.end_time.strftime('%H:%M:%S') if appointment.end_time else (
            datetime.combine(appt_date, appointment.start_time) +
            timedelta(minutes=appointment.estimated_duration_minutes or 30)
        ).time().strftime('%H:%M:%S')

        # Check availability
        if not self._is_staff_available(session, staff_id, appt_date, start_time, end_time):
            raise ResourceNotAvailableError(
                f"Staff {staff.first_name} is not available for this time slot"
            )

        # Create allocation
        allocation = AppointmentResource(
            appointment_id=appointment_id,
            resource_type='staff',
            resource_id=staff_id,
            allocation_date=appt_date,
            start_time=start_time,
            end_time=end_time,
            status='allocated',
            role=role,
            allocated_by=user_id
        )

        session.add(allocation)

        # Update appointment therapist_id if this is the primary therapist
        if role == 'primary_therapist' and staff.staff_type in ['therapist', 'nurse']:
            appointment.therapist_id = staff_id

        self._update_allocation_status(session, appointment)

        session.flush()

        logger.info(f"Staff {staff.first_name} allocated to appointment {appointment.appointment_number}")
        return allocation

    def deallocate_resource(
        self,
        session: Session,
        allocation_id: UUID,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Remove a resource allocation from an appointment.

        Args:
            session: Database session
            allocation_id: AppointmentResource UUID
            user_id: User making the change

        Returns:
            True if successful
        """
        allocation = session.query(AppointmentResource).filter_by(
            allocation_id=allocation_id
        ).first()

        if not allocation:
            raise ResourceAllocationError(f"Allocation not found: {allocation_id}")

        # Get appointment to update
        appointment = session.query(Appointment).filter_by(
            appointment_id=allocation.appointment_id
        ).first()

        # Update allocation status
        allocation.status = 'cancelled'

        # Update appointment fields
        if appointment:
            if allocation.resource_type == 'room' and appointment.room_id == allocation.resource_id:
                appointment.room_id = None
            elif allocation.resource_type == 'staff' and appointment.therapist_id == allocation.resource_id:
                appointment.therapist_id = None

            self._update_allocation_status(session, appointment)

        logger.info(f"Resource allocation {allocation_id} cancelled")
        return True

    def get_appointment_resources(
        self,
        session: Session,
        appointment_id: UUID
    ) -> Dict[str, Any]:
        """
        Get all resources allocated to an appointment.

        Returns dict with 'room' and 'staff' allocations.
        """
        allocations = session.query(AppointmentResource).filter(
            AppointmentResource.appointment_id == appointment_id,
            AppointmentResource.status.in_(['allocated', 'in_use'])
        ).all()

        result = {'room': None, 'staff': []}

        for alloc in allocations:
            if alloc.resource_type == 'room':
                room = session.query(Room).filter_by(room_id=alloc.resource_id).first()
                if room:
                    result['room'] = {
                        'allocation_id': str(alloc.allocation_id),
                        'room_id': str(room.room_id),
                        'room_code': room.room_code,
                        'room_name': room.room_name,
                        'room_type': room.room_type,
                        'status': alloc.status
                    }
            elif alloc.resource_type == 'staff':
                staff = session.query(Staff).filter_by(staff_id=alloc.resource_id).first()
                if staff:
                    result['staff'].append({
                        'allocation_id': str(alloc.allocation_id),
                        'staff_id': str(staff.staff_id),
                        'staff_name': f"{staff.first_name} {staff.last_name or ''}".strip(),
                        'staff_type': staff.staff_type,
                        'role': alloc.role,
                        'status': alloc.status
                    })

        return result

    def _update_allocation_status(self, session: Session, appointment: Appointment):
        """Update the resource_allocation_status field on an appointment."""
        if not appointment.service_id:
            appointment.resource_allocation_status = 'not_required'
            return

        # Get requirements
        requirements = self.get_service_requirements(session, appointment.service_id)

        # Get current allocations
        allocations = self.get_appointment_resources(session, appointment.appointment_id)

        # Check if all mandatory requirements are met
        room_required = any(r.get('is_mandatory') for r in requirements.get('room', []))
        staff_required = any(r.get('is_mandatory') for r in requirements.get('staff', []))

        has_room = allocations.get('room') is not None
        has_staff = len(allocations.get('staff', [])) > 0

        if not room_required and not staff_required:
            appointment.resource_allocation_status = 'not_required'
        elif (not room_required or has_room) and (not staff_required or has_staff):
            appointment.resource_allocation_status = 'complete'
        elif has_room or has_staff:
            appointment.resource_allocation_status = 'partial'
        else:
            appointment.resource_allocation_status = 'pending'

    # =========================================================================
    # ROOM CRUD OPERATIONS
    # =========================================================================

    def get_rooms(
        self,
        session: Session,
        branch_id: UUID,
        room_type: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[Room]:
        """Get all rooms for a branch."""
        query = session.query(Room).filter(
            Room.branch_id == branch_id,
            Room.is_deleted == False
        )

        if not include_inactive:
            query = query.filter(Room.is_active == True)

        if room_type:
            query = query.filter(Room.room_type == room_type)

        return query.order_by(Room.room_type, Room.room_code).all()

    def create_room(
        self,
        session: Session,
        branch_id: UUID,
        hospital_id: UUID,
        room_code: str,
        room_name: str,
        room_type: str,
        capacity: int = 1,
        default_slot_duration_minutes: int = 30,
        buffer_minutes: int = 10,
        features: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> Room:
        """Create a new room."""
        # Validate room type
        if room_type not in Room.ROOM_TYPES:
            raise ResourceAllocationError(f"Invalid room type: {room_type}")

        # Check for duplicate code
        existing = session.query(Room).filter(
            Room.branch_id == branch_id,
            Room.room_code == room_code,
            Room.is_deleted == False
        ).first()

        if existing:
            raise ResourceAllocationError(f"Room code {room_code} already exists")

        room = Room(
            hospital_id=hospital_id,
            branch_id=branch_id,
            room_code=room_code,
            room_name=room_name,
            room_type=room_type,
            capacity=capacity,
            default_slot_duration_minutes=default_slot_duration_minutes,
            buffer_minutes=buffer_minutes,
            features=features,
            is_active=True,
            created_by=user_id,
            updated_by=user_id
        )

        session.add(room)
        session.flush()

        logger.info(f"Room created: {room_code} - {room_name}")
        return room

    def update_room(
        self,
        session: Session,
        room_id: UUID,
        updates: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Room:
        """Update room details."""
        room = session.query(Room).filter_by(room_id=room_id).first()

        if not room:
            raise ResourceAllocationError(f"Room not found: {room_id}")

        allowed_fields = [
            'room_name', 'room_type', 'capacity', 'features',
            'default_slot_duration_minutes', 'buffer_minutes',
            'operating_start_time', 'operating_end_time', 'is_active'
        ]

        for field, value in updates.items():
            if field in allowed_fields:
                setattr(room, field, value)

        room.updated_by = user_id

        logger.info(f"Room updated: {room.room_code}")
        return room

    def delete_room(
        self,
        session: Session,
        room_id: UUID,
        user_id: Optional[str] = None
    ) -> bool:
        """Soft delete a room."""
        room = session.query(Room).filter_by(room_id=room_id).first()

        if not room:
            raise ResourceAllocationError(f"Room not found: {room_id}")

        room.is_deleted = True
        room.is_active = False
        room.deleted_at = datetime.now(timezone.utc)
        room.deleted_by = user_id

        logger.info(f"Room deleted: {room.room_code}")
        return True


# Create singleton instance
resource_allocation_service = ResourceAllocationService()
