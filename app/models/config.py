# app/models/config.py

from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, generate_uuid

class ModuleMaster(Base, TimestampMixin):
    """Module configuration for authorization"""
    __tablename__ = 'module_master'

    module_id = Column(Integer, primary_key=True, autoincrement=True)
    module_name = Column(String(50), nullable=False)
    description = Column(String(200))
    parent_module = Column(Integer, ForeignKey('module_master.module_id'))
    sequence = Column(Integer)
    icon = Column(String(50))
    route = Column(String(100))
    status = Column(String(20), default='active')

    # Relationships
    role_access = relationship("RoleModuleAccess", back_populates="module")
    sub_modules = relationship("ModuleMaster", 
                             backref="parent", 
                             remote_side=[module_id])

class RoleMaster(Base, TimestampMixin):
    """Role definitions for authorization"""
    __tablename__ = 'role_master'

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'))
    role_name = Column(String(50), nullable=False)
    description = Column(String(200))
    is_system_role = Column(Boolean, default=False)  # For system-defined roles
    status = Column(String(20), default='active')

    # Relationships
    hospital = relationship("Hospital", back_populates="roles")
    module_access = relationship("RoleModuleAccess", back_populates="role")
    users = relationship("UserRoleMapping", back_populates="role")

class RoleModuleAccess(Base, TimestampMixin):
    """Role-based module access configuration"""
    __tablename__ = 'role_module_access'

    role_id = Column(Integer, ForeignKey('role_master.role_id'), primary_key=True)
    module_id = Column(Integer, ForeignKey('module_master.module_id'), primary_key=True)
    can_view = Column(Boolean, default=False)
    can_add = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_export = Column(Boolean, default=False)

    # Relationships
    role = relationship("RoleMaster", back_populates="module_access")
    module = relationship("ModuleMaster", back_populates="role_access")

class UserRoleMapping(Base, TimestampMixin):
    """Mapping between users and their roles"""
    __tablename__ = 'user_role_mapping'

    user_id = Column(String(15), ForeignKey('users.user_id'), primary_key=True)
    role_id = Column(Integer, ForeignKey('role_master.role_id'), primary_key=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="roles")
    role = relationship("RoleMaster", back_populates="users")

class ParameterSettings(Base, TimestampMixin):
    """System parameters and configuration"""
    __tablename__ = 'parameter_settings'

    param_code = Column(String(50), primary_key=True)
    param_value = Column(String(500))
    data_type = Column(String(20))
    module = Column(String(50))
    is_editable = Column(Boolean, default=True)
    description = Column(Text)