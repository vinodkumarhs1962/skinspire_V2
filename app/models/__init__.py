# app/models/__init__.py

from .base import Base, TimestampMixin, TenantMixin, SoftDeleteMixin, generate_uuid
from .master import *
from .transaction import *
from .config import *
from .appointment import (
    AppointmentType, DoctorSchedule, AppointmentSlot, Appointment,
    AppointmentStatusHistory, DoctorScheduleException, AppointmentReminder
)
# from .config import ModuleMaster, RoleMaster, RoleModuleAccess, UserRoleMapping, ParameterSettings
# from .master import Hospital, Branch, Staff, Patient
# from .transaction import User, LoginHistory, UserSession

__all__ = [
    # Base
    'Base', 'TimestampMixin', 'TenantMixin', 'SoftDeleteMixin', 'generate_uuid',

    # Configuration
    'ModuleMaster', 'RoleMaster', 'RoleModuleAccess', 'UserRoleMapping', 'ParameterSettings',

    # Master Data
    'Hospital', 'Branch', 'Staff', 'Patient',

    # Resource Management
    'Room', 'RoomSlot', 'ServiceResourceRequirement', 'AppointmentResource',

    # Transactions
    'User', 'LoginHistory', 'UserSession',

    # Appointments (Phase 1 - Patient Lifecycle)
    'AppointmentType', 'DoctorSchedule', 'AppointmentSlot', 'Appointment',
    'AppointmentStatusHistory', 'DoctorScheduleException', 'AppointmentReminder'
]
# Temporary test model
from .test_migration_model import TestMigrationTable
