# app/models/base.py

from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base  # Updated import
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class TimestampMixin:
    """Mixin for adding timestamp fields to models"""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(50))
    updated_by = Column(String(50))

class TenantMixin:
    """Mixin for adding tenant (hospital/branch) fields to models"""
    @hybrid_property
    def tenant_id(self):
        return self.hospital_id

class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(50))
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self, user_id):
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = user_id

def generate_uuid():
    """Generate a UUID for primary keys"""
    return str(uuid.uuid4())