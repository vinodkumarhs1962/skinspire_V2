# app/models/base.py

from sqlalchemy import Column, DateTime, String, Boolean, event
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base  # Updated import
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone
import uuid

from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

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
    """
    Mixin for soft delete functionality with both flag and timestamp
    Ensures atomic updates of all soft delete fields
    """
    
    # Boolean flag for easy filtering (indexed for performance)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    
    # Audit trail - when and who deleted
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(50))
    
    def soft_delete(self, user_id=None, reason=None):
        """
        Mark record as deleted - ATOMIC operation
        All three fields are updated together in a single transaction
        """
        try:
            # Set all fields atomically
            self.is_deleted = True
            self.deleted_at = datetime.now(timezone.utc)
            self.deleted_by = user_id
            
            # Optional: Store deletion reason if your model has this field
            if hasattr(self, 'deletion_reason') and reason:
                self.deletion_reason = reason
            
            # Update audit fields if they exist
            if hasattr(self, 'updated_at'):
                self.updated_at = datetime.now(timezone.utc)
            if hasattr(self, 'updated_by'):
                self.updated_by = user_id
                
            logger.info(f"Soft deleted {self.__class__.__name__} by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error soft deleting {self.__class__.__name__}: {e}")
            raise
    
    def undelete(self, user_id=None, reason=None):
        """
        Restore a soft-deleted record - ATOMIC operation
        """
        try:
            if not self.is_deleted:
                logger.warning(f"Attempting to undelete non-deleted {self.__class__.__name__}")
                return False
            
            # Store restoration history before clearing
            if hasattr(self, 'restoration_history'):
                if not self.restoration_history:
                    self.restoration_history = []
                self.restoration_history.append({
                    'deleted_at': self.deleted_at,
                    'deleted_by': self.deleted_by,
                    'restored_at': datetime.now(timezone.utc),
                    'restored_by': user_id,
                    'reason': reason
                })
            
            # Clear all deletion fields atomically
            self.is_deleted = False
            self.deleted_at = None
            self.deleted_by = None
            
            # Clear deletion reason if it exists
            if hasattr(self, 'deletion_reason'):
                self.deletion_reason = None
            
            # Update audit fields
            if hasattr(self, 'updated_at'):
                self.updated_at = datetime.now(timezone.utc)
            if hasattr(self, 'updated_by'):
                self.updated_by = user_id
            
            # Set status back to active if applicable
            if hasattr(self, 'status'):
                self.status = 'active'
                
            logger.info(f"Restored {self.__class__.__name__} by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring {self.__class__.__name__}: {e}")
            raise
    
    @hybrid_property
    def is_active(self):
        """Convenience property - inverse of is_deleted"""
        return not self.is_deleted
    
    @classmethod
    def active_records(cls):
        """Class method to get only active records"""
        return cls.query.filter(cls.is_deleted == False)
    
    @classmethod
    def deleted_records(cls):
        """Class method to get only deleted records"""
        return cls.query.filter(cls.is_deleted == True)


# SQLAlchemy Event Listeners for Data Consistency
@event.listens_for(SoftDeleteMixin, 'before_update', propagate=True)
def enforce_soft_delete_consistency(mapper, connection, target):
    """
    Ensure data consistency before any update
    This runs AUTOMATICALLY on any update to ensure fields stay in sync
    """
    if hasattr(target, 'is_deleted'):
        # If setting is_deleted to True but deleted_at is not set
        if target.is_deleted and not target.deleted_at:
            target.deleted_at = datetime.now(timezone.utc)
            if not target.deleted_by and hasattr(target, 'updated_by'):
                target.deleted_by = target.updated_by
        
        # If setting is_deleted to False, clear timestamp fields
        elif not target.is_deleted and target.deleted_at:
            target.deleted_at = None
            target.deleted_by = None

def generate_uuid():
    """Generate a UUID for primary keys"""
    return str(uuid.uuid4())