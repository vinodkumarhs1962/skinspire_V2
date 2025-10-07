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
    Enhanced Mixin for soft delete functionality with both flag and timestamp
    Ensures atomic updates of all soft delete fields
    ✅ NEW: Added cascading support for transaction entities
    """
    
    # Boolean flag for easy filtering (indexed for performance)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    
    # Audit trail - when and who deleted
    deleted_at = Column(DateTime(timezone=True))
    deleted_by = Column(String(50))
    
    def soft_delete(self, user_id=None, reason=None, cascade_to_children=True):
        """
        Mark record as deleted - ATOMIC operation
        All three fields are updated together in a single transaction
        
        Args:
            user_id: User performing the deletion
            reason: Optional reason for deletion
            cascade_to_children: Whether to cascade delete to child records
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
            
            # ✅ NEW: Cascade to child records for transaction entities
            if cascade_to_children:
                self._cascade_soft_delete_to_children(user_id, reason)
                
            logger.info(f"Soft deleted {self.__class__.__name__} by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error soft deleting {self.__class__.__name__}: {e}")
            raise
    
    def undelete(self, user_id=None, reason=None, cascade_to_children=True):
        """
        Restore a soft-deleted record - ATOMIC operation
        
        Args:
            user_id: User performing the restoration
            reason: Optional reason for restoration  
            cascade_to_children: Whether to restore child records
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
            
            # Set status back to active if applicable (for master entities)
            if hasattr(self, 'status') and self.__class__.__name__ in ['Supplier', 'Medicine', 'Service']:
                self.status = 'active'
            
            # ✅ NEW: Cascade restoration to child records
            if cascade_to_children:
                self._cascade_undelete_to_children(user_id, reason)
                
            logger.info(f"Restored {self.__class__.__name__} by {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring {self.__class__.__name__}: {e}")
            raise
    
    # ✅ NEW: Cascading support methods
    def _cascade_soft_delete_to_children(self, user_id, reason):
        """
        Cascade soft delete to child records for transaction entities
        Override this method in specific models to define cascading behavior
        """
        # Default implementation - check for common child relationships
        cascade_reason = f"Parent {self.__class__.__name__} deleted"
        if reason:
            cascade_reason += f": {reason}"
            
        # Handle Purchase Order -> Lines cascading
        if hasattr(self, 'po_lines') and self.po_lines:
            for line in self.po_lines:
                if hasattr(line, 'soft_delete') and not line.is_deleted:
                    line.soft_delete(user_id, cascade_reason, cascade_to_children=False)
                    
        # Handle Invoice -> Lines cascading  
        if hasattr(self, 'invoice_lines') and self.invoice_lines:
            for line in self.invoice_lines:
                if hasattr(line, 'soft_delete') and not line.is_deleted:
                    line.soft_delete(user_id, cascade_reason, cascade_to_children=False)
                    
        # Handle Invoice -> Payments cascading (mark as cancelled, not deleted)
        if hasattr(self, 'payments') and self.payments:
            for payment in self.payments:
                if hasattr(payment, 'workflow_status') and payment.workflow_status in ['draft', 'pending_approval']:
                    payment.workflow_status = 'cancelled'
                    payment.rejection_reason = cascade_reason
                    if hasattr(payment, 'rejected_at'):
                        payment.rejected_at = datetime.now(timezone.utc)
                    if hasattr(payment, 'rejected_by'):
                        payment.rejected_by = user_id
    
    def _cascade_undelete_to_children(self, user_id, reason):
        """
        Cascade restoration to child records
        Override this method in specific models to define restoration behavior
        """
        restore_reason = f"Parent {self.__class__.__name__} restored"
        if reason:
            restore_reason += f": {reason}"
            
        # Handle Purchase Order -> Lines restoration
        if hasattr(self, 'po_lines'):
            for line in self.po_lines:
                if hasattr(line, 'undelete') and line.is_deleted:
                    # Only restore if deleted by parent deletion
                    if line.deleted_by == self.deleted_by:
                        line.undelete(user_id, restore_reason, cascade_to_children=False)
                        
        # Handle Invoice -> Lines restoration
        if hasattr(self, 'invoice_lines'):
            for line in self.invoice_lines:
                if hasattr(line, 'undelete') and line.is_deleted:
                    if line.deleted_by == self.deleted_by:
                        line.undelete(user_id, restore_reason, cascade_to_children=False)
    
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


# ✅ NEW: Approval tracking mixin for consistent approval handling
class ApprovalMixin:
    """
    Mixin for consistent approval tracking across transaction entities
    """
    
    # Approval tracking fields
    approved_by = Column(String(50))
    approved_at = Column(DateTime(timezone=True))
    
    def approve(self, approver_id, notes=None):
        """
        Standard approval method for transaction entities
        """
        self.approved_by = approver_id
        self.approved_at = datetime.now(timezone.utc)
        
        # Update audit fields
        if hasattr(self, 'updated_at'):
            self.updated_at = datetime.now(timezone.utc)
        if hasattr(self, 'updated_by'):
            self.updated_by = approver_id
            
        # Update status for different entity types
        if hasattr(self, 'status'):
            self.status = 'approved'
        elif hasattr(self, 'workflow_status'):
            self.workflow_status = 'approved'
            
        # Store approval notes if the model supports it
        if hasattr(self, 'approval_notes') and notes:
            self.approval_notes = notes
            
        logger.info(f"Approved {self.__class__.__name__} by {approver_id}")
        
    def unapprove(self, user_id, reason=None):
        """
        Reverse approval for transaction entities
        """
        previous_approver = self.approved_by
        
        # Clear approval fields
        self.approved_by = None
        self.approved_at = None
        
        # Update audit fields
        if hasattr(self, 'updated_at'):
            self.updated_at = datetime.now(timezone.utc)
        if hasattr(self, 'updated_by'):
            self.updated_by = user_id
            
        # Update status back to draft/pending
        if hasattr(self, 'status'):
            self.status = 'draft'
        elif hasattr(self, 'workflow_status'):
            self.workflow_status = 'draft'
            
        # Store unapproval reason if the model supports it
        if hasattr(self, 'approval_notes') and reason:
            self.approval_notes = f"Unapproved by {user_id}: {reason}"
            
        logger.info(f"Unapproved {self.__class__.__name__} by {user_id} (previously approved by {previous_approver})")


# SQLAlchemy Event Listeners for Data Consistency (EXISTING - unchanged)
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