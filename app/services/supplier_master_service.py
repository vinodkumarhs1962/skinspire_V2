# In app/services/supplier_master_service.py:

"""
Supplier Master Service - Entity-specific service for Supplier entity
Clean implementation using universal base
"""

from typing import Dict, Any, List, Optional
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.master import Supplier
from app.engine.universal_entity_service import UniversalEntityService
from app.services.database_service import get_entity_dict
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class SupplierMasterService(UniversalEntityService):
    """
    Supplier-specific service extending universal base
    Only implements what's specific to suppliers
    """
    
    def __init__(self):
        super().__init__('suppliers', Supplier)
    
    def _convert_items_to_dict(self, items: List, session: Session) -> List[Dict]:
        """Override to extract phone from contact_info JSONB and ensure all fields"""
        items_dict = []
        
        for item in items:
            # Get base dictionary
            item_dict = get_entity_dict(item)
            
            # ✅ Extract phone from contact_info JSONB
            if hasattr(item, 'contact_info') and item.contact_info:
                contact_info = item.contact_info
                if isinstance(contact_info, dict):
                    # Try to get phone in order of preference
                    phone = contact_info.get('phone') or contact_info.get('mobile') or contact_info.get('telephone', '')
                    item_dict['phone'] = phone
                else:
                    item_dict['phone'] = ''
            else:
                item_dict['phone'] = ''
            
            # ✅ Ensure all required fields are present
            # Some fields might be None, but we need them as empty strings for display
            if item_dict.get('supplier_category') is None:
                item_dict['supplier_category'] = ''
            if item_dict.get('contact_person_name') is None:
                item_dict['contact_person_name'] = ''
            if item_dict.get('email') is None:
                item_dict['email'] = ''
            if item_dict.get('gst_registration_number') is None:
                item_dict['gst_registration_number'] = ''
            
            # Add any relationships if needed
            self._add_relationships(item_dict, item, session)
            
            items_dict.append(item_dict)
            
        logger.info(f"✅ Converted {len(items_dict)} supplier items with phone extraction")
        return items_dict
    
    def _calculate_summary(self, session: Session, hospital_id: uuid.UUID,
                          branch_id: Optional[uuid.UUID], filters: Dict,
                          total_count: int) -> Dict:
        """
        Calculate supplier-specific summary - BRANCH AWARE
        """
        summary = {'total_count': total_count}
        
        # ✅ Base query with branch awareness (matching main query logic)
        base_query = session.query(Supplier).filter(Supplier.hospital_id == hospital_id)
        
        # ✅ CRITICAL: Apply branch filter consistently
        if branch_id:
            base_query = base_query.filter(Supplier.branch_id == branch_id)
            logger.info(f"📊 Summary calculation for branch: {branch_id}")
        
        # ✅ Apply any active filters to match the list
        if filters.get('status'):
            base_query = base_query.filter(Supplier.status == filters['status'])
        if filters.get('supplier_category'):
            base_query = base_query.filter(Supplier.supplier_category == filters['supplier_category'])
        
        # Active/Inactive counts (branch-aware)
        summary['active_count'] = base_query.filter(
            Supplier.status == 'active'
        ).count()
        summary['inactive_count'] = base_query.filter(
            Supplier.status == 'inactive'
        ).count()
        
        # Medicine suppliers count (branch-aware)
        summary['medicine_suppliers'] = base_query.filter(
            Supplier.supplier_category == 'medicine'
        ).count()
        
        # Blacklisted count (branch-aware)
        summary['blacklisted_count'] = base_query.filter(
            Supplier.black_listed == True
        ).count()
        
        # Category breakdown (branch-aware)
        category_counts = base_query.with_entities(
            Supplier.supplier_category,
            func.count(Supplier.supplier_id)
        ).group_by(Supplier.supplier_category).all()
        
        for category, count in category_counts:
            if category:
                summary[f'{category.lower()}_suppliers'] = count
        
        logger.info(f"📊 [SUPPLIER_SUMMARY] Branch: {branch_id}, Total: {total_count}, "
                   f"Active: {summary['active_count']}, Medicine: {summary['medicine_suppliers']}, "
                   f"Blacklisted: {summary['blacklisted_count']}")
        
        return summary
    
    def _add_relationships(self, item_dict: Dict, item: Supplier, session: Session):
        """Add supplier-specific relationships if needed"""
        # For now, suppliers don't need additional relationships
        # But this is where you'd add branch name, etc. if needed
        pass