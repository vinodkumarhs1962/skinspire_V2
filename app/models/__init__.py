# app/models/__init__.py

from .base import Base, TimestampMixin, TenantMixin, SoftDeleteMixin, generate_uuid
from .master import *
from .transaction import *
from .config import *
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
    
    # Transactions
    'User', 'LoginHistory', 'UserSession'
]
# Temporary test model
from .test_migration_model import TestMigrationTable
