# File: app/engine/universal_entity_service.py (ENHANCED)

"""
Universal Entity Service - Base class for ALL entity services
Enhanced with complete search/filter/pagination functionality
This is the TRUE universal layer - zero entity-specific code
"""

from typing import Dict, Any, Optional, List, Type, Tuple
import uuid
from datetime import datetime
from sqlalchemy import desc, asc, func, and_, or_
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
    Provides complete generic search/filter/pagination functionality
    Entity-specific services override only what they need
    """
    
    def __init__(self, entity_type: str, model_class: Type):
        self.entity_type = entity_type
        self.model_class = model_class
        self.config = get_entity_config(entity_type)
        self.filter_processor = get_categorized_filter_processor()
    
    def search_data(self, filters: dict, **kwargs) -> dict:
        """
        Universal search interface - complete implementation
        This is the ONLY public method services need
        """
        try:
            # Extract standard parameters
            hospital_id = kwargs.get('hospital_id')
            branch_id = kwargs.get('branch_id')
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            sort_by = kwargs.get('sort_by')
            sort_order = kwargs.get('sort_order', 'desc')
            
            if not hospital_id:
                return self._get_error_result("Hospital ID required")
            
            with get_db_session() as session:
                # Get base query
                query = self._get_base_query(session, hospital_id, branch_id)
                
                # Apply search terms if configured
                search_term = filters.get('search_term') or filters.get('search')
                if search_term and hasattr(self.config, 'searchable_fields'):
                    query = self._apply_search_filter(query, search_term)
                
                # Apply filters using categorized processor
                query, applied_filters, filter_count = self.filter_processor.process_entity_filters(
                    self.entity_type,
                    query,
                    filters,
                    self.model_class,
                    session,
                    hospital_id,
                    branch_id
                )
                
                # Get total count before pagination
                total_count = query.count()
                
                # Apply sorting
                query = self._apply_sorting(query, sort_by, sort_order)
                
                # Apply pagination
                query = self._apply_pagination(query, page, per_page)
                
                # Execute query
                items = query.all()
                
                # Convert to dictionaries
                items_dict = self._convert_items_to_dict(items, session)
                
                # Calculate summary
                summary = self._calculate_summary(
                    session, hospital_id, branch_id, 
                    filters, total_count, applied_filters
                )
                
                # Build pagination info
                pagination = self._build_pagination_info(
                    total_count, page, per_page
                )
                
                return self._build_success_result(
                    items_dict, total_count, pagination,
                    summary, applied_filters, filter_count
                )
                
        except Exception as e:
            logger.error(f"Error in {self.entity_type} search: {str(e)}", exc_info=True)
            return self._get_error_result(str(e))
    
    def _get_base_query(self, session: Session, hospital_id: uuid.UUID, 
                       branch_id: Optional[uuid.UUID]):
        """Get base query with hospital/branch filtering"""
        query = session.query(self.model_class)
        
        # Apply hospital filter
        if hasattr(self.model_class, 'hospital_id'):
            query = query.filter(self.model_class.hospital_id == hospital_id)
        
        # Apply branch filter if provided
        if branch_id and hasattr(self.model_class, 'branch_id'):
            query = query.filter(self.model_class.branch_id == branch_id)
        
        # Apply default filters (e.g., exclude deleted)
        if hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        
        return query
    
    def _apply_search_filter(self, query, search_term: str):
        """Apply text search across configured searchable fields"""
        if not search_term or not self.config.searchable_fields:
            return query
        
        search_conditions = []
        search_term_lower = f"%{search_term.lower()}%"
        
        for field_name in self.config.searchable_fields:
            if hasattr(self.model_class, field_name):
                field = getattr(self.model_class, field_name)
                search_conditions.append(
                    func.lower(field).like(search_term_lower)
                )
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
        
        return query
    
    def _apply_sorting(self, query, sort_by: Optional[str], sort_order: str):
        """Apply sorting to query"""
        # Default sort field
        if not sort_by:
            # Try common default fields
            for default_field in ['created_at', 'updated_at', 'id']:
                if hasattr(self.model_class, default_field):
                    sort_by = default_field
                    break
        
        if sort_by and hasattr(self.model_class, sort_by):
            sort_field = getattr(self.model_class, sort_by)
            if sort_order.lower() == 'asc':
                query = query.order_by(asc(sort_field))
            else:
                query = query.order_by(desc(sort_field))
        
        return query
    
    def _apply_pagination(self, query, page: int, per_page: int):
        """Apply pagination to query"""
        # Ensure valid pagination values
        page = max(1, int(page))
        per_page = min(max(1, int(per_page)), 100)  # Cap at 100
        
        offset = (page - 1) * per_page
        return query.limit(per_page).offset(offset)
    
    def _convert_items_to_dict(self, items: List, session: Session) -> List[Dict]:
        """Convert model instances to dictionaries"""
        items_dict = []
        
        for item in items:
            # Get base dictionary
            item_dict = get_entity_dict(item)
            
            # Add any relationships
            self._add_relationships(item_dict, item, session)
            
            items_dict.append(item_dict)
        
        return items_dict
    
    def _calculate_summary(self, session: Session, hospital_id: uuid.UUID,
                          branch_id: Optional[uuid.UUID], filters: Dict,
                          total_count: int, applied_filters: set = None) -> Dict:
        """
        Calculate basic summary statistics
        Entity-specific services should override to add custom metrics
        Note: applied_filters parameter is optional for backward compatibility
        """
        summary = {
            'total_count': total_count,
            'filtered_count': total_count if not applied_filters else None
        }
        
        # Add status counts if model has status field
        if hasattr(self.model_class, 'status'):
            base_query = self._get_base_query(session, hospital_id, branch_id)
            status_counts = base_query.with_entities(
                self.model_class.status,
                func.count(self.model_class.status)
            ).group_by(self.model_class.status).all()
            
            for status, count in status_counts:
                if status:
                    summary[f'{status.lower()}_count'] = count
        
        return summary
    
    def _build_pagination_info(self, total_count: int, page: int, per_page: int) -> Dict:
        """Build pagination metadata"""
        total_pages = (total_count + per_page - 1) // per_page if per_page > 0 else 1
        
        return {
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
    
    def _build_success_result(self, items: List[Dict], total_count: int,
                            pagination: Dict, summary: Dict,
                            applied_filters: set, filter_count: int) -> Dict:
        """Build standardized success response"""
        return {
            'items': items,
            'total': total_count,
            'page': pagination['page'],
            'per_page': pagination['per_page'],
            'total_pages': pagination['total_pages'],
            'pagination': pagination,
            'summary': summary,
            'applied_filters': list(applied_filters),
            'filter_count': filter_count,
            'success': True,
            'entity_type': self.entity_type
        }
    
    def _get_error_result(self, error_message: str) -> Dict:
        """Build standardized error response"""
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
    
    # Hook methods for entity-specific customization
    def _add_relationships(self, item_dict: Dict, item: Any, session: Session):
        """
        Hook for adding entity-specific relationships
        Override in entity-specific services
        """
        pass
    
    def get_by_id(self, item_id: str, **kwargs):
        """Get single item by ID"""
        try:
            hospital_id = kwargs.get('hospital_id')
            if not hospital_id:
                return None
            
            with get_db_session() as session:
                query = self._get_base_query(session, hospital_id, kwargs.get('branch_id'))
                
                # Find ID field dynamically
                id_field = self._get_id_field()
                # ===== ADD THIS DEBUG =====
                logger.info(f"[{self.entity_type}] get_by_id: Looking for {id_field}={item_id}")
                # ===== END DEBUG =====
                if not id_field:
                    return None
                
                item = query.filter(getattr(self.model_class, id_field) == item_id).first()
                
                if item:
                    item_dict = get_entity_dict(item)
                    self._add_relationships(item_dict, item, session)
                    return item_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting {self.entity_type} by id: {str(e)}")
            return None
    
    def _get_id_field(self) -> Optional[str]:
        """Get the primary key field name for the model"""
        # ALWAYS check configuration first - this is the source of truth
        if self.config and hasattr(self.config, 'primary_key') and self.config.primary_key:
            logger.debug(f"Using primary_key '{self.config.primary_key}' from config for {self.entity_type}")
            return self.config.primary_key
        
        # Log warning if no config
        logger.warning(f"No primary_key in config for {self.entity_type}, trying common patterns")
        
        # Common patterns fallback
        common_id_fields = [
            f'{self.entity_type[:-1]}_id',  # e.g., supplier_id for suppliers
            'id'                             # generic id
        ]
        
        for field_name in common_id_fields:
            if hasattr(self.model_class, field_name):
                logger.debug(f"Found ID field by pattern: {field_name}")
                return field_name
        
        logger.error(f"No ID field found for {self.entity_type}")
        return None