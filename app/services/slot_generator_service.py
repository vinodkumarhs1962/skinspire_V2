# app/services/slot_generator_service.py
"""
Slot Generator Service
Phase 1 of Patient Lifecycle System

Generates appointment slots from doctor schedules.
Handles:
- Batch slot generation for date ranges
- Schedule exception handling (leaves, holidays)
- Slot cleanup for past dates
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from app.models.appointment import (
    AppointmentSlot, DoctorSchedule, DoctorScheduleException
)
from app.models.master import Staff, Branch

logger = logging.getLogger(__name__)


class SlotGeneratorService:
    """
    Service for generating appointment slots from doctor schedules.

    Slots are generated based on:
    - Doctor's weekly schedule templates
    - Schedule exceptions (leaves, holidays)
    - Hospital settings
    """

    def generate_slots_for_doctor(
        self,
        session: Session,
        staff_id: UUID,
        branch_id: UUID,
        start_date: date,
        end_date: date,
        regenerate: bool = False
    ) -> List[AppointmentSlot]:
        """
        Generate slots for a doctor within a date range.

        Args:
            session: Database session
            staff_id: Doctor's UUID
            branch_id: Branch UUID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            regenerate: If True, delete existing unbooked slots and regenerate

        Returns:
            List of created slots
        """
        # Get doctor's schedules
        schedules = session.query(DoctorSchedule).filter(
            DoctorSchedule.staff_id == staff_id,
            DoctorSchedule.branch_id == branch_id,
            DoctorSchedule.is_active == True,
            DoctorSchedule.is_deleted == False
        ).all()

        if not schedules:
            logger.warning(f"No schedules found for doctor {staff_id} at branch {branch_id}")
            return []

        # Get exceptions for this period
        exceptions = self._get_exceptions(session, staff_id, branch_id, start_date, end_date)

        # Delete existing unbooked slots if regenerating
        if regenerate:
            self._delete_unbooked_slots(session, staff_id, branch_id, start_date, end_date)

        # Generate slots for each day
        created_slots = []
        current_date = start_date

        while current_date <= end_date:
            # Convert weekday to our format (0=Sunday)
            day_of_week = (current_date.weekday() + 1) % 7

            # Find applicable schedules for this day
            day_schedules = [s for s in schedules if s.day_of_week == day_of_week]

            for schedule in day_schedules:
                # Check effective dates
                if schedule.effective_from and current_date < schedule.effective_from:
                    continue
                if schedule.effective_until and current_date > schedule.effective_until:
                    continue

                # Generate slots for this schedule
                slots = self._generate_slots_for_schedule(
                    session, schedule, current_date, exceptions
                )
                created_slots.extend(slots)

            current_date += timedelta(days=1)

        session.flush()
        logger.info(f"Generated {len(created_slots)} slots for doctor {staff_id}")

        return created_slots

    def generate_slots_for_branch(
        self,
        session: Session,
        branch_id: UUID,
        start_date: date,
        end_date: date,
        regenerate: bool = False
    ) -> Dict[UUID, List[AppointmentSlot]]:
        """
        Generate slots for all doctors in a branch.

        Returns:
            Dictionary mapping staff_id to list of created slots
        """
        # Get all doctors with schedules in this branch
        doctor_ids = session.query(DoctorSchedule.staff_id).filter(
            DoctorSchedule.branch_id == branch_id,
            DoctorSchedule.is_active == True,
            DoctorSchedule.is_deleted == False
        ).distinct().all()

        results = {}
        for (staff_id,) in doctor_ids:
            slots = self.generate_slots_for_doctor(
                session, staff_id, branch_id, start_date, end_date, regenerate
            )
            results[staff_id] = slots

        return results

    def generate_next_week_slots(
        self,
        session: Session,
        branch_id: Optional[UUID] = None
    ) -> int:
        """
        Generate slots for the next 7 days.
        Typically run as a daily scheduled job.

        Returns:
            Total number of slots created
        """
        today = date.today()
        end_date = today + timedelta(days=7)

        total_slots = 0

        if branch_id:
            results = self.generate_slots_for_branch(session, branch_id, today, end_date)
            total_slots = sum(len(slots) for slots in results.values())
        else:
            # Generate for all branches
            branches = session.query(Branch).filter(
                Branch.is_active == True,
                Branch.is_deleted == False
            ).all()

            for branch in branches:
                results = self.generate_slots_for_branch(
                    session, branch.branch_id, today, end_date
                )
                total_slots += sum(len(slots) for slots in results.values())

        logger.info(f"Generated {total_slots} slots for next 7 days")
        return total_slots

    def block_slots(
        self,
        session: Session,
        staff_id: UUID,
        branch_id: UUID,
        target_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        reason: str = "",
        blocked_by: Optional[UUID] = None
    ) -> int:
        """
        Block slots for a doctor on a specific date.

        If start_time and end_time are None, blocks all slots for the day.

        Returns:
            Number of slots blocked
        """
        query = session.query(AppointmentSlot).filter(
            AppointmentSlot.staff_id == staff_id,
            AppointmentSlot.branch_id == branch_id,
            AppointmentSlot.slot_date == target_date,
            AppointmentSlot.is_blocked == False,
            AppointmentSlot.current_bookings == 0  # Only block empty slots
        )

        if start_time and end_time:
            query = query.filter(
                AppointmentSlot.start_time >= start_time,
                AppointmentSlot.start_time < end_time
            )

        slots = query.all()

        for slot in slots:
            slot.block(reason, blocked_by)

        logger.info(f"Blocked {len(slots)} slots for doctor {staff_id} on {target_date}")
        return len(slots)

    def unblock_slots(
        self,
        session: Session,
        staff_id: UUID,
        branch_id: UUID,
        target_date: date,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None
    ) -> int:
        """
        Unblock slots for a doctor.

        Returns:
            Number of slots unblocked
        """
        query = session.query(AppointmentSlot).filter(
            AppointmentSlot.staff_id == staff_id,
            AppointmentSlot.branch_id == branch_id,
            AppointmentSlot.slot_date == target_date,
            AppointmentSlot.is_blocked == True
        )

        if start_time and end_time:
            query = query.filter(
                AppointmentSlot.start_time >= start_time,
                AppointmentSlot.start_time < end_time
            )

        slots = query.all()

        for slot in slots:
            slot.unblock()

        logger.info(f"Unblocked {len(slots)} slots for doctor {staff_id} on {target_date}")
        return len(slots)

    def cleanup_past_slots(
        self,
        session: Session,
        days_to_keep: int = 30
    ) -> int:
        """
        Delete slots older than specified days that have no bookings.

        Returns:
            Number of slots deleted
        """
        cutoff_date = date.today() - timedelta(days=days_to_keep)

        result = session.query(AppointmentSlot).filter(
            AppointmentSlot.slot_date < cutoff_date,
            AppointmentSlot.current_bookings == 0
        ).delete(synchronize_session=False)

        logger.info(f"Cleaned up {result} old slots before {cutoff_date}")
        return result

    def get_slot_availability_summary(
        self,
        session: Session,
        branch_id: UUID,
        start_date: date,
        end_date: date,
        staff_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get daily slot availability summary.

        Returns:
            List of daily summaries with total, available, booked counts
        """
        query = session.query(
            AppointmentSlot.slot_date,
            func.count(AppointmentSlot.slot_id).label('total_slots'),
            func.sum(
                func.case((
                    and_(
                        AppointmentSlot.is_available == True,
                        AppointmentSlot.is_blocked == False,
                        AppointmentSlot.current_bookings < AppointmentSlot.max_bookings
                    ), 1
                ), else_=0)
            ).label('available_slots'),
            func.sum(AppointmentSlot.current_bookings).label('booked_slots')
        ).filter(
            AppointmentSlot.branch_id == branch_id,
            AppointmentSlot.slot_date >= start_date,
            AppointmentSlot.slot_date <= end_date
        )

        if staff_id:
            query = query.filter(AppointmentSlot.staff_id == staff_id)

        query = query.group_by(AppointmentSlot.slot_date)
        query = query.order_by(AppointmentSlot.slot_date)

        results = query.all()

        return [
            {
                'date': r.slot_date.isoformat(),
                'total_slots': r.total_slots,
                'available_slots': r.available_slots or 0,
                'booked_slots': r.booked_slots or 0,
                'availability_percentage': round(
                    ((r.available_slots or 0) / r.total_slots * 100) if r.total_slots > 0 else 0, 1
                )
            }
            for r in results
        ]

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    def _generate_slots_for_schedule(
        self,
        session: Session,
        schedule: DoctorSchedule,
        target_date: date,
        exceptions: List[DoctorScheduleException]
    ) -> List[AppointmentSlot]:
        """Generate slots for a single schedule on a specific date."""
        # Check if this date has a full-day exception
        for exc in exceptions:
            if exc.exception_date == target_date:
                if exc.start_time is None or exc.end_time is None:
                    # Full day blocked
                    return []

        created_slots = []
        duration = timedelta(minutes=schedule.slot_duration_minutes)

        current = datetime.combine(target_date, schedule.start_time)
        end = datetime.combine(target_date, schedule.end_time)

        while current + duration <= end:
            slot_start = current.time()
            slot_end = (current + duration).time()

            # Check if slot overlaps with break
            if schedule.break_start_time and schedule.break_end_time:
                break_start = datetime.combine(target_date, schedule.break_start_time)
                break_end = datetime.combine(target_date, schedule.break_end_time)
                if current < break_end and current + duration > break_start:
                    current = break_end
                    continue

            # Check if slot overlaps with any exception
            is_blocked = False
            block_reason = None
            for exc in exceptions:
                if exc.exception_date == target_date and exc.start_time and exc.end_time:
                    if slot_start >= exc.start_time and slot_start < exc.end_time:
                        is_blocked = True
                        block_reason = exc.reason or exc.exception_type
                        break

            # Check if slot already exists
            existing = session.query(AppointmentSlot).filter(
                AppointmentSlot.staff_id == schedule.staff_id,
                AppointmentSlot.branch_id == schedule.branch_id,
                AppointmentSlot.slot_date == target_date,
                AppointmentSlot.start_time == slot_start
            ).first()

            if not existing:
                slot = AppointmentSlot(
                    staff_id=schedule.staff_id,
                    branch_id=schedule.branch_id,
                    schedule_id=schedule.schedule_id,
                    slot_date=target_date,
                    start_time=slot_start,
                    end_time=slot_end,
                    max_bookings=schedule.max_patients_per_slot,
                    is_blocked=is_blocked,
                    block_reason=block_reason
                )
                session.add(slot)
                created_slots.append(slot)

            current += duration

        return created_slots

    def _get_exceptions(
        self,
        session: Session,
        staff_id: UUID,
        branch_id: UUID,
        start_date: date,
        end_date: date
    ) -> List[DoctorScheduleException]:
        """Get schedule exceptions for a date range."""
        return session.query(DoctorScheduleException).filter(
            DoctorScheduleException.staff_id == staff_id,
            DoctorScheduleException.exception_date >= start_date,
            DoctorScheduleException.exception_date <= end_date,
            DoctorScheduleException.is_active == True,
            DoctorScheduleException.is_deleted == False,
            or_(
                DoctorScheduleException.branch_id == branch_id,
                DoctorScheduleException.branch_id.is_(None)
            )
        ).all()

    def _delete_unbooked_slots(
        self,
        session: Session,
        staff_id: UUID,
        branch_id: UUID,
        start_date: date,
        end_date: date
    ) -> int:
        """Delete unbooked slots for regeneration."""
        result = session.query(AppointmentSlot).filter(
            AppointmentSlot.staff_id == staff_id,
            AppointmentSlot.branch_id == branch_id,
            AppointmentSlot.slot_date >= start_date,
            AppointmentSlot.slot_date <= end_date,
            AppointmentSlot.current_bookings == 0
        ).delete(synchronize_session=False)

        logger.info(f"Deleted {result} unbooked slots for regeneration")
        return result


# Create singleton instance
slot_generator_service = SlotGeneratorService()
