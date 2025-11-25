# app/models/config.py - ENHANCED with Branch Access Support
# ALIGNED with executed SQL script - INTEGER for role_id/module_id

from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, Text, CheckConstraint, UniqueConstraint, Index, DateTime, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone, date
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

    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'))
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    role_access = relationship("RoleModuleAccess", back_populates="module")
    sub_modules = relationship("ModuleMaster", 
                             backref="parent", 
                             remote_side=[module_id])
    branch_permissions = relationship("RoleModuleBranchAccess", back_populates="module", cascade="all, delete-orphan")
    hospital = relationship("Hospital")

class RoleMaster(Base, TimestampMixin):
    """Role definitions for authorization"""
    __tablename__ = 'role_master'

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'))
    role_name = Column(String(50), nullable=False)
    description = Column(String(200))
    is_system_role = Column(Boolean, default=False)  # For system-defined roles
    status = Column(String(20), default='active')

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    hospital = relationship("Hospital", back_populates="roles")
    module_access = relationship("RoleModuleAccess", back_populates="role")
    users = relationship("UserRoleMapping", back_populates="role")
    branch_permissions = relationship("RoleModuleBranchAccess", back_populates="role", cascade="all, delete-orphan")

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
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)

    # Relationships
    role = relationship("RoleMaster", back_populates="module_access")
    module = relationship("ModuleMaster", back_populates="role_access")
    hospital = relationship("Hospital")

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

class RoleModuleBranchAccess(Base, TimestampMixin):
    """
    Enhanced role permissions with branch-level granularity
    EXACT MATCH with executed SQL script structure
    """
    __tablename__ = 'role_module_branch_access'
    
    access_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    role_id = Column(Integer, ForeignKey('role_master.role_id'), nullable=False)  # INTEGER to match SQL
    module_id = Column(Integer, ForeignKey('module_master.module_id'), nullable=False)  # INTEGER to match SQL
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'), nullable=True)
    
    # Branch access configuration
    branch_access_type = Column(String(20), default='specific', nullable=False)
    
    # Standard permissions
    can_view = Column(Boolean, default=False, nullable=False)
    can_add = Column(Boolean, default=False, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_export = Column(Boolean, default=False, nullable=False)
    
    # Enhanced cross-branch permissions for executives
    can_view_cross_branch = Column(Boolean, default=False, nullable=False)
    can_export_cross_branch = Column(Boolean, default=False, nullable=False)
    
    # Audit fields - EXACT MATCH with SQL script
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    hospital = relationship("Hospital")
    role = relationship("RoleMaster", back_populates="branch_permissions")
    module = relationship("ModuleMaster", back_populates="branch_permissions")
    branch = relationship("Branch", back_populates="role_permissions")
    
    # Constraints and indexes - EXACT MATCH with SQL script
    __table_args__ = (
        UniqueConstraint('role_id', 'module_id', 'branch_id', name='uq_role_module_branch'),
        CheckConstraint(
            "branch_access_type IN ('specific', 'all', 'reporting')",
            name='chk_branch_access_type'
        ),
        CheckConstraint(
            "(branch_id IS NULL AND branch_access_type IN ('all', 'reporting')) OR "
            "(branch_id IS NOT NULL AND branch_access_type = 'specific')",
            name='chk_cross_branch_logic'
        ),
        Index('idx_role_module_branch_lookup', 'role_id', 'module_id', 'branch_id'),
        Index('idx_branch_permissions', 'branch_id'),
        Index('idx_hospital_role_permissions', 'hospital_id', 'role_id'),
        Index('idx_permission_search', 'hospital_id', 'role_id', 'module_id', 'can_view', 'can_edit'),
        Index('idx_cross_branch_permissions', 'hospital_id', 'can_view_cross_branch', 'can_export_cross_branch'),
    )
    
    def has_permission(self, permission_type: str, is_cross_branch: bool = False) -> bool:
        """Check if this role-module-branch combination has specific permission"""
        if hasattr(self, f"can_{permission_type}") and getattr(self, f"can_{permission_type}"):
            return True
        
        if is_cross_branch and permission_type in ['view', 'export']:
            cross_branch_attr = f"can_{permission_type}_cross_branch"
            if hasattr(self, cross_branch_attr) and getattr(self, cross_branch_attr):
                return True
        
        return False

    @property
    def is_all_branch_access(self):
        """Check if this permission grants access to all branches"""
        return self.branch_id is None and self.branch_access_type in ['all', 'reporting']
    
    @property
    def is_cross_branch_user(self):
        """Check if this permission allows cross-branch operations"""
        return self.can_view_cross_branch or self.can_export_cross_branch

    def __repr__(self):
        return f"<RoleModuleBranchAccess {self.role_id} - {self.module_id} - {self.branch_id or 'All Branches'}>"


class InvoiceSequence(Base, TimestampMixin):
    """
    Thread-safe invoice sequence tracking for split invoices
    Prevents duplicate invoice numbers under concurrent load
    """
    __tablename__ = 'invoice_sequences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    prefix = Column(String(10), nullable=False)  # SVC, MED, EXM, RX
    financial_year = Column(String(10), nullable=False)  # 2024-2025, 2025-2026
    current_sequence = Column(Integer, default=0, nullable=False)

    # Relationships
    hospital = relationship("Hospital")

    # Composite unique constraint - one sequence per hospital/prefix/year
    __table_args__ = (
        UniqueConstraint('hospital_id', 'prefix', 'financial_year', name='uq_invoice_sequence'),
        Index('idx_invoice_sequence_lookup', 'hospital_id', 'prefix', 'financial_year')
    )

    def __repr__(self):
        return f"<InvoiceSequence {self.prefix}/{self.financial_year}: {self.current_sequence}>"


class EntityPricingTaxConfig(Base, TimestampMixin):
    """
    Date-based versioning of pricing and GST rates for medicines, services, and packages.
    Supports:
    - MRP/price change tracking with manufacturer notifications
    - GST rate change tracking with government notifications
    - Complete historical accuracy for invoicing and tax compliance
    """
    __tablename__ = 'entity_pricing_tax_config'

    config_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))

    # Entity Reference (exactly ONE must be populated)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'))
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'))
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'))

    # Effective Period
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)  # NULL = currently effective

    # === PRICING INFORMATION ===
    # For Medicines
    mrp = Column(Numeric(12, 2))                    # Maximum Retail Price
    pack_mrp = Column(Numeric(12, 2))               # MRP per pack
    pack_purchase_price = Column(Numeric(12, 2))   # Purchase price per pack
    units_per_pack = Column(Numeric(10, 2))        # Units in a pack
    unit_price = Column(Numeric(12, 2))            # Price per unit
    selling_price = Column(Numeric(12, 2))         # Actual selling price
    cost_price = Column(Numeric(12, 2))            # Cost for profit calculation

    # For Services/Packages
    service_price = Column(Numeric(12, 2))         # Service base price
    package_price = Column(Numeric(12, 2))         # Package base price

    # === GST INFORMATION ===
    gst_rate = Column(Numeric(5, 2))               # Overall GST (%)
    cgst_rate = Column(Numeric(5, 2))              # Central GST (%)
    sgst_rate = Column(Numeric(5, 2))              # State GST (%)
    igst_rate = Column(Numeric(5, 2))              # Integrated GST (%)
    is_gst_exempt = Column(Boolean, default=False)
    gst_inclusive = Column(Boolean, default=False)

    # === REFERENCE DOCUMENTATION ===
    # For GST changes
    gst_notification_number = Column(String(100))
    gst_notification_date = Column(Date)
    gst_notification_url = Column(String(500))

    # For price changes
    manufacturer_notification = Column(String(100))
    manufacturer_notification_date = Column(Date)
    price_revision_reason = Column(Text)

    # === METADATA ===
    change_type = Column(String(50))  # 'gst_change', 'price_change', 'both', 'initial'
    change_reason = Column(Text)
    remarks = Column(Text)

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    medicine = relationship("Medicine", foreign_keys=[medicine_id])
    service = relationship("Service", foreign_keys=[service_id])
    package = relationship("Package", foreign_keys=[package_id])

    __table_args__ = (
        CheckConstraint(
            """
            (medicine_id IS NOT NULL AND service_id IS NULL AND package_id IS NULL) OR
            (medicine_id IS NULL AND service_id IS NOT NULL AND package_id IS NULL) OR
            (medicine_id IS NULL AND service_id IS NULL AND package_id IS NOT NULL)
            """,
            name='chk_entity_reference'
        ),
        CheckConstraint(
            'effective_to IS NULL OR effective_to > effective_from',
            name='chk_effective_dates'
        ),
        CheckConstraint(
            'gst_rate IS NULL OR gst_rate = COALESCE(cgst_rate, 0) + COALESCE(sgst_rate, 0) + COALESCE(igst_rate, 0)',
            name='chk_gst_rate_sum'
        ),
    )

    @property
    def entity_type(self):
        """Return the type of entity this config applies to"""
        if self.medicine_id:
            return 'medicine'
        elif self.service_id:
            return 'service'
        elif self.package_id:
            return 'package'
        return None

    @property
    def entity_id(self):
        """Return the ID of the entity this config applies to"""
        if self.medicine_id:
            return self.medicine_id
        elif self.service_id:
            return self.service_id
        elif self.package_id:
            return self.package_id
        return None

    @property
    def is_currently_effective(self):
        """Check if this config is currently in effect"""
        today = date.today()
        return (self.effective_from <= today and
                (self.effective_to is None or self.effective_to >= today))

    @property
    def applicable_price(self):
        """Get the applicable price based on entity type"""
        if self.medicine_id:
            return self.mrp or self.selling_price or self.pack_mrp
        elif self.service_id:
            return self.service_price
        elif self.package_id:
            return self.package_price
        return None

    def __repr__(self):
        entity_info = f"{self.entity_type}_{self.entity_id}"
        period = f"{self.effective_from} to {self.effective_to or 'current'}"
        return f"<EntityPricingTaxConfig {entity_info} {period} price={self.applicable_price} gst={self.gst_rate}%>"


# ============================================================================
# DEPRECATED: Campaign Hook System (Removed 2025-11-21)
# ============================================================================
# The CampaignHookConfig model and campaign_hook_config table have been deprecated
# and removed in favor of the promotion_campaigns system in master.py.
#
# OLD SYSTEM (Removed):
# - campaign_hook_config table → Plugin-based promotions (Python/API/SQL hooks)
# - Used by pricing_tax_service with apply_campaigns flag
#
# NEW SYSTEM (Active):
# - promotion_campaigns table → Database-driven business rules
# - Supports: simple_discount, buy_x_get_y, tiered_discount, bundle
# - Used by discount_service.py for all invoice-level promotions
#
# Migration: migrations/20251121_deprecate_campaign_hooks.sql
# ============================================================================