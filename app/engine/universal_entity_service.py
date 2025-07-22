"""
Universal Entity Service - Base class for ALL entity services
This is the TRUE universal layer - zero entity-specific code
"""

from typing import Dict, Any, Optional, List, Type
import uuid
from datetime import datetime
from sqlalchemy import desc, asc, func
from sqlalchemy.orm import Session
from abc import ABC, abstractmethod

from app.services.database_service import get_db_session, get_entity_dict
from app.config.entity_configurations import get_entity_config
from app.engine.categorized_filter_processor import get_categorized_filter_processor
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalEntityService(ABC):
    """
    Base class for all entity services
    Provides generic search/filter/pagination functionality
    Entity-specific services override only what they need
    """
    
    def __init__(self, entity_type: str, model_class: Type):
        self.entity_type = entity_type
        self.model_class = model_class
        self.config = get_entity_config(entity_type)
        self.filter_processor = get_categorized_filter_processor()
    
    def search_data(self, filters: dict, **kwargs) -> dict:
        """
        Universal search interface - SAME signature as existing
        This is the ONLY public method services need
        """
        try:
            # Extract standard parameters
            hospital_id = kwargs.get('hospital_id')
            branch_id = kwargs.get('branch_id')
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            
            if not hospital_id:
                return self._get_error_result("Hospital ID required")
            
            with get_db_session() as session:
                # Get base query
                query = self._get_base_query(session, hospital_id, branch_id)
                
                # Apply filters using categorized processor
                query, applied_filters, filter_count = self.filter_processor.process_entity_filters(
                    self.entity_type, filters, query, session, self.config
                )
                
                # Get total count
                total_count = query.count()
                
                # Apply sorting
                query = self._apply_sorting(query, filters)
                
                # Apply pagination
                items = self._apply_pagination(query, page, per_page)
                
                # Convert to dictionaries
                items_dict = self._convert_items_to_dict(items, session)
                
                # Calculate summary
                summary = self._calculate_summary(
                    session, hospital_id, branch_id, filters, total_count
                )
                
                # Build result
                return self._build_success_result(
                    items_dict, total_count, page, per_page, 
                    summary, applied_filters, filter_count
                )
                
        except Exception as e:
            logger.error(f"Error in {self.entity_type} search: {str(e)}")
            return self._get_error_result(str(e))
    
    def _get_base_query(self, session: Session, hospital_id: uuid.UUID, 
                       branch_id: Optional[uuid.UUID] = None):
        """Get base query with hospital/branch filtering"""
        query = session.query(self.model_class)
        
        # Hospital filtering
        if hasattr(self.model_class, 'hospital_id'):
            query = query.filter(self.model_class.hospital_id == hospital_id)
        
        # Branch filtering
        if branch_id and hasattr(self.model_class, 'branch_id'):
            query = query.filter(self.model_class.branch_id == branch_id)
        
        return query
    
    def _apply_sorting(self, query, filters: Dict):
        """Apply sorting based on filters or config"""
        sort_field = filters.get('sort', self.config.default_sort_field if self.config else None)
        if sort_field and hasattr(self.model_class, sort_field):
            sort_dir = filters.get('direction', 'asc')
            if sort_dir == 'desc':
                query = query.order_by(desc(getattr(self.model_class, sort_field)))
            else:
                query = query.order_by(asc(getattr(self.model_class, sort_field)))
        return query
    
    def _apply_pagination(self, query, page: int, per_page: int):
        """Apply pagination to query"""
        offset = (page - 1) * per_page
        return query.offset(offset).limit(per_page).all()
    
    def _convert_items_to_dict(self, items: List, session: Session) -> List[Dict]:
        """Convert SQLAlchemy objects to dictionaries"""
        items_dict = []
        for item in items:
            item_dict = get_entity_dict(item)
            # Allow subclasses to add relationships
            self._add_relationships(item_dict, item, session)
            items_dict.append(item_dict)
        return items_dict
    
    def _calculate_summary(self, session: Session, hospital_id: uuid.UUID,
                          branch_id: Optional[uuid.UUID], filters: Dict,
                          total_count: int) -> Dict:
        """
        Calculate summary - OVERRIDE in entity-specific service
        Base implementation provides generic summary
        """
        summary = {'total_count': total_count}
        
        # Generic status counting if available
        if hasattr(self.model_class, 'status'):
            status_counts = session.query(
                self.model_class.status,
                func.count(self.model_class.status)
            ).filter(
                self.model_class.hospital_id == hospital_id
            ).group_by(self.model_class.status).all()
            
            for status, count in status_counts:
                if status:
                    summary[f'{status}_count'] = count
        
        return summary
    
    def _add_relationships(self, item_dict: Dict, item: Any, session: Session):
        """Override to add entity-specific relationships"""
        pass
    
    def _build_success_result(self, items: List[Dict], total_count: int,
                            page: int, per_page: int, summary: Dict,
                            applied_filters: List, filter_count: int) -> Dict:
        """Build standardized success result"""
        total_pages = (total_count + per_page - 1) // per_page
        
        return {
            'items': items,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'pagination': {
                'total_count': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'summary': summary,
            'applied_filters': list(applied_filters),
            'filter_count': filter_count,
            'success': True,
            'entity_type': self.entity_type
        }
    
    def _get_error_result(self, error_message: str) -> Dict:
        """Build standardized error result"""
        return {
            'items': [],
            'total': 0,
            'page': 1,
            'per_page': 20,
            'total_pages': 0,
            'pagination': {'total_count': 0, 'page': 1, 'per_page': 20},
            'summary': {'total_count': 0},
            'success': False,
            'error': error_message,
            'entity_type': self.entity_type
        }