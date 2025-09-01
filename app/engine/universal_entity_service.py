# File: app/engine/universal_entity_service.py (ENHANCED)

"""
Universal Entity Service - Base class for ALL entity services
Enhanced with complete search/filter/pagination functionality
This is the TRUE universal layer - zero entity-specific code
"""

from typing import Dict, Any, Optional, List, Type, Tuple
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import desc, asc, func, and_, or_
from sqlalchemy.orm import Session
from abc import ABC, abstractmethod

from app.config.core_definitions import FieldType
#from app.utils.filters import format_currency, format_number, format_date, dateformat, datetimeformat, timeago, register_filters
from app.services.database_service import get_db_session, get_entity_dict
from app.config.entity_configurations import get_entity_config
from app.engine.categorized_filter_processor import get_categorized_filter_processor
from app.engine.universal_service_cache import cache_service_method
from app.utils import filters
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
    
    @cache_service_method() 
    def search_data(self, filters: dict, **kwargs) -> dict:
        """
        Universal search interface - complete implementation
        This is the ONLY public method services need
        """
        try:
            # Extract standard parameters
            hospital_id = kwargs.get('hospital_id')
            branch_id = kwargs.get('branch_id')
            user = kwargs.get('current_user') 
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            sort_by = kwargs.get('sort_by')
            sort_order = kwargs.get('sort_order', 'desc')
            
            if not hospital_id:
                return self._get_error_result("Hospital ID required")
            
            with get_db_session() as session:
                # Get base query
                query = self._get_base_query(session, hospital_id, branch_id, user=user)
                
                # Apply search terms if configured
                search_term = filters.get('search_term') or filters.get('search')
                if search_term and hasattr(self.config, 'searchable_fields'):
                    query = self._apply_search_filter(query, self.model_class, self.config, search_term)
                
                # Apply filters using categorized processor
                query, applied_filters, filter_count = self.filter_processor.process_entity_filters(
                    self.entity_type,    # entity_type: str
                    filters,             # ✅ FIXED: filters parameter
                    query,               # ✅ FIXED: query parameter  
                    self.model_class,    # model_class: Type
                    session,             # session: Session
                    hospital_id,         # hospital_id: Optional[uuid.UUID] = None
                    branch_id,           # branch_id: Optional[uuid.UUID] = None  
                    self.config          # config=None
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
               branch_id: Optional[uuid.UUID],
               user: Optional[Any] = None): 
        """Get base query with hospital/branch filtering - ENTITY AGNOSTIC"""
        query = session.query(self.model_class)
        
        # Apply hospital filter
        if hasattr(self.model_class, 'hospital_id'):
            query = query.filter(self.model_class.hospital_id == hospital_id)
        
        # Apply branch filter if provided
        if branch_id and hasattr(self.model_class, 'branch_id'):
            query = query.filter(self.model_class.branch_id == branch_id)
        
        # ✅ ENHANCED: Universal soft delete filter supporting multiple field names
        show_deleted = self._get_user_show_deleted_preference(user)
        
        if not show_deleted:
            # Check for multiple possible soft delete fields (entity-agnostic)
            if hasattr(self.model_class, 'is_deleted'):
                query = query.filter(self.model_class.is_deleted == False)
            elif hasattr(self.model_class, 'deleted_flag'):
                query = query.filter(self.model_class.deleted_flag == False)
            elif hasattr(self.model_class, 'deleted'):
                query = query.filter(self.model_class.deleted == False)
        
        return query

    def _get_user_show_deleted_preference(self, user: Optional[Any] = None) -> bool:
        """
        ✅ NEW: Universal method to get user's show_deleted preference
        Entity-agnostic with multiple fallback strategies
        """
        show_deleted = False
        
        try:
            # Strategy 1: Use passed user parameter
            if user:
                if hasattr(user, 'ui_preferences') and user.ui_preferences:
                    show_deleted = user.ui_preferences.get('show_deleted_records', False)
                elif hasattr(user, 'show_deleted_records'):
                    show_deleted = user.show_deleted_records
            
            # Strategy 2: Fallback to current_user
            if not user:
                try:
                    from flask_login import current_user
                    if current_user and hasattr(current_user, 'ui_preferences') and current_user.ui_preferences:
                        show_deleted = current_user.ui_preferences.get('show_deleted_records', False)
                    elif current_user and hasattr(current_user, 'show_deleted_records'):
                        show_deleted = current_user.show_deleted_records
                except Exception as e:
                    logger.debug(f"Could not access current_user: {e}")
            
            return show_deleted
            
        except Exception as e:
            logger.warning(f"Error getting show_deleted preference: {e}")
            return False  # Safe default: don't show deleted
    
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
        """Convert model instances to dictionaries - ENTITY AGNOSTIC"""
        items_dict = []
        
        for item in items:
            # Get base dictionary
            item_dict = get_entity_dict(item)
            
            # ✅ UNIVERSAL: Ensure all possible deleted flags are included
            if hasattr(item, 'is_deleted'):
                item_dict['is_deleted'] = item.is_deleted
            if hasattr(item, 'deleted_flag'):
                item_dict['deleted_flag'] = item.deleted_flag
            if hasattr(item, 'deleted'):
                item_dict['deleted'] = item.deleted
                
            # ✅ UNIVERSAL: Add deleted timestamp fields for additional context
            if hasattr(item, 'deleted_at'):
                item_dict['deleted_at'] = item.deleted_at
            if hasattr(item, 'deleted_by'):
                item_dict['deleted_by'] = item.deleted_by
            
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
    
    def get_by_id(self, item_id: str, **kwargs) -> Optional[Dict]:
        """Get single item by ID with virtual field extraction"""
        try:
            hospital_id = kwargs.get('hospital_id')
            user = kwargs.get('current_user') 

            if not hospital_id or not item_id:
                return None
            
            with get_db_session() as session:
                # First try with user preference
                query = self._get_base_query(session, hospital_id, 
                                            kwargs.get('branch_id'),
                                            user=user)  # PASS USER
                
                # Find ID field dynamically
                id_field = self._get_id_field()
                logger.info(f"[{self.entity_type}] get_by_id: Looking for {id_field}={item_id}")
                if not id_field:
                    return None
                
                item = query.filter(getattr(self.model_class, id_field) == item_id).first()
                # If not found and user doesn't show deleted, try including deleted
                # This allows viewing a specific deleted record via direct link
                if not item and hasattr(self.model_class, 'is_deleted'):
                    query_with_deleted = session.query(self.model_class)
                    if hasattr(self.model_class, 'hospital_id'):
                        query_with_deleted = query_with_deleted.filter(
                            self.model_class.hospital_id == hospital_id
                        )
                    item = query_with_deleted.filter(
                        getattr(self.model_class, id_field) == item_id
                    ).first()

                if item:
                    item_dict = get_entity_dict(item)
                    self._add_relationships(item_dict, item, session)
                    
                    # CRITICAL FIX: Extract virtual fields from JSONB
                    if self.config:
                        item_dict = self._extract_virtual_fields_for_single_item(item_dict)
                    
                    return item_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting {self.entity_type} by id: {str(e)}")
            return None

    def _extract_virtual_fields_for_single_item(self, item_dict: Dict) -> Dict:
        """
        Extract virtual fields from JSONB columns for a single item
        Uses configuration to determine which fields are virtual
        """
        from app.engine.virtual_field_transformer import VirtualFieldTransformer
        
        # Use VirtualFieldTransformer to extract fields
        virtual_data = VirtualFieldTransformer.extract_virtual_fields_for_display(
            item_dict, self.config
        )
        
        # Merge virtual data into item dict
        item_dict.update(virtual_data)
        
        logger.info(f"[{self.entity_type}] Extracted {len(virtual_data)} virtual fields for item")
        
        return item_dict
    
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
    
    # =========================================================================
    # ENHANCEMENT 1: Automatic Type Conversion Based on Field Type
    # =========================================================================
    def _entity_to_dict(self, entity) -> Dict:
        """
        REPLACE/ENHANCE EXISTING METHOD
        Purpose: Convert entity to dict with automatic type conversion based on field configuration
        Backward Compatible: Yes - handles all existing field types
        """
        # Get base dict
        from app.services.database_service import get_entity_dict
        result = get_entity_dict(entity)
        
        # Get entity configuration
        config = self._get_entity_config()
        if not config or not config.fields:
            return result
        
        # Apply type conversions based on field configuration
        for field in config.fields:
            if field.name in result:
                value = result[field.name]
                
                # Handle CURRENCY and DECIMAL types (existing in FieldType enum)
                if field.field_type == FieldType.CURRENCY:
                    if value is not None:
                        if isinstance(value, Decimal):
                            result[field.name] = float(value)
                        elif value == '':
                            result[field.name] = 0.0
                    else:
                        result[field.name] = 0.0
                
                elif field.field_type == FieldType.DECIMAL:
                    if value is not None:
                        if isinstance(value, Decimal):
                            result[field.name] = float(value)
                    else:
                        result[field.name] = 0.0
                
                # Handle PERCENTAGE type (existing)
                elif field.field_type == FieldType.PERCENTAGE:
                    if value is not None:
                        if isinstance(value, Decimal):
                            result[field.name] = float(value)
                        else:
                            result[field.name] = float(value) if value else 0.0
                
                # Handle DATE/DATETIME formatting (existing)
                elif field.field_type in [FieldType.DATE, FieldType.DATETIME]:
                    if value:
                        if isinstance(value, (datetime, date)):
                            result[field.name] = value.isoformat()
                
                # Handle BOOLEAN (existing)
                elif field.field_type == FieldType.BOOLEAN:
                    result[field.name] = bool(value) if value is not None else False
        
        return result


    # =========================================================================
    # ENHANCEMENT 2: Automatic Relationship Loading Based on Field Type
    # =========================================================================
    def _add_relationships(self, item_dict: Dict, item: Any, session: Session):
        """
        REPLACE/ENHANCE EXISTING METHOD
        Purpose: Automatically load foreign key relationships based on field configuration
        Backward Compatible: Yes - uses existing ENTITY_SEARCH, UUID, REFERENCE types
        """
        try:
            config = self._get_entity_config()
            if not config or not config.fields:
                return item_dict
            
            # Process each field that's a foreign key
            for field in config.fields:
                # Check for foreign key field types (using EXISTING types)
                if field.field_type in [FieldType.ENTITY_SEARCH, FieldType.UUID, FieldType.REFERENCE]:
                    # Check if it has relationship configuration
                    if (hasattr(field, 'entity_search_config') or  # Existing property
                        hasattr(field, 'related_field') or  # Existing property
                        field.name.endswith('_id')):  # Convention
                        
                        self._load_foreign_key_relationship(
                            item_dict, item, session, field
                        )
            
            # Also process any virtual fields that need calculation
            for field in config.fields:
                if field.virtual and hasattr(field, 'custom_renderer') and field.custom_renderer:
                    # Skip virtual field calculation for now (can be added later)
                    pass
            
        except Exception as e:
            logger.error(f"Error adding relationships: {str(e)}")
        
        return item_dict

    def add_relationships(self, entity_dict: Dict, entity, session) -> Dict:
        """
        Public wrapper for categorized processor compatibility
        Child classes should override this method
        """
        return self._add_relationships(entity_dict, entity, session)

    def get_calculated_fields(self, item: Any, config: Any = None) -> Dict:
        """
        Calculate virtual/computed fields for display
        Child classes should override this method
        """
        return {}

    def _load_foreign_key_relationship(self, item_dict: Dict, item: Any, 
                                    session: Session, field):
        """
        NEW HELPER METHOD
        Purpose: Load a specific foreign key relationship using existing config
        """
        try:
            # Get the foreign key value
            fk_value = getattr(item, field.name, None)
            if not fk_value:
                return
            
            # Determine the related entity
            related_entity = None
            display_field = 'name'  # default
            
            # Check entity_search_config (existing property)
            if hasattr(field, 'entity_search_config') and field.entity_search_config:
                config = field.entity_search_config
                if hasattr(config, 'target_entity'):
                    related_entity = config.target_entity
                elif isinstance(config, dict):
                    related_entity = config.get('target_entity')
                
                # Get display field
                if hasattr(config, 'display_template'):
                    # Extract field name from template like "{supplier_name}"
                    template = config.display_template
                    if '{' in template and '}' in template:
                        display_field = template.replace('{', '').replace('}', '')
            
            # Check related_display_field (existing property)
            if hasattr(field, 'related_display_field') and field.related_display_field:
                display_field = field.related_display_field
            
            # Derive entity from field name convention
            if not related_entity and field.name.endswith('_id'):
                # supplier_id -> suppliers
                entity_name = field.name[:-3]  # Remove _id
                related_entity = f"{entity_name}s"  # Pluralize (simple)
            
            if not related_entity:
                return
            
            # Try to get from eager-loaded relationship first
            relationship_name = field.name.replace('_id', '')  # supplier_id -> supplier
            if hasattr(item, relationship_name):
                related_obj = getattr(item, relationship_name)
                if related_obj:
                    # Add the display name
                    if hasattr(related_obj, display_field):
                        item_dict[f"{relationship_name}_name"] = getattr(related_obj, display_field)
                        # Also add supplier_name for compatibility
                        if relationship_name == 'supplier':
                            item_dict['supplier_name'] = getattr(related_obj, display_field)
                    return
            
            # Fallback: Query the related entity
            from app.config.entity_registry import ENTITY_REGISTRY
            
            if related_entity in ENTITY_REGISTRY:
                registration = ENTITY_REGISTRY[related_entity]
                
                if registration.model_class:
                    # Import and query the model
                    module_path, class_name = registration.model_class.rsplit('.', 1)
                    module = __import__(module_path, fromlist=[class_name])
                    model_class = getattr(module, class_name)
                    
                    # Query for the related object
                    related_obj = session.query(model_class).filter(
                        getattr(model_class, f"{relationship_name}_id") == fk_value
                    ).first()
                    
                    if related_obj:
                        # Try common name fields
                        for name_field in [display_field, f"{relationship_name}_name", 'name', 'title']:
                            if hasattr(related_obj, name_field):
                                value = getattr(related_obj, name_field)
                                item_dict[f"{relationship_name}_name"] = value
                                # Also add supplier_name for compatibility
                                if relationship_name == 'supplier':
                                    item_dict['supplier_name'] = value
                                break
            
        except Exception as e:
            logger.warning(f"Could not load relationship for {field.name}: {e}")


    # =========================================================================
    # ENHANCEMENT 3: Automatic Filter Application Based on Field Configuration
    # =========================================================================
    def _apply_filters(self, query, filters: Dict, session: Session) -> Tuple:
        """
        NEW METHOD (doesn't exist in parent currently)
        Purpose: Apply filters automatically based on field configuration
        Backward Compatible: Yes - uses existing filterable property
        """
        applied_filters = set()
        filter_count = 0
        
        try:
            config = self._get_entity_config()
            if not config or not config.fields:
                return query, applied_filters, filter_count
            
            model_class = self.model_class
            
            for field in config.fields:
                # Skip non-filterable fields (using existing property)
                if not field.filterable:
                    continue
                
                # Check for filter value (including aliases - existing property)
                filter_value = self._get_filter_value(filters, field)
                if not filter_value:
                    continue
                
                # Apply filter based on field type
                query = self._apply_field_filter(
                    query, model_class, field, filter_value
                )
                applied_filters.add(field.name)
                filter_count += 1
            
            # Also handle search across searchable fields (existing property)
            search_term = filters.get('search') or filters.get('q')
            if search_term:
                query = self._apply_search_filter(
                    query, model_class, config, search_term
                )
                applied_filters.add('search')
                filter_count += 1
            
            logger.info(f"Applied {filter_count} filters: {applied_filters}")
            
        except Exception as e:
            logger.error(f"Error applying filters: {str(e)}")
        
        return query, applied_filters, filter_count


    def _get_filter_value(self, filters: Dict, field):
        """
        NEW HELPER METHOD
        Purpose: Get filter value checking field name and aliases
        Uses: filter_aliases (existing property)
        """
        # Check main field name
        if field.name in filters and filters[field.name]:
            value = filters[field.name]
            if str(value).strip():
                return value
        
        # Check filter aliases (existing property)
        if hasattr(field, 'filter_aliases') and field.filter_aliases:
            for alias in field.filter_aliases:
                if alias in filters and filters[alias]:
                    value = filters[alias]
                    if str(value).strip():
                        return value
        
        return None


    def _apply_field_filter(self, query, model_class, field, filter_value):
        """
        NEW HELPER METHOD
        Purpose: Apply filter based on field type
        Uses: Existing FieldType enum values
        """
        if not hasattr(model_class, field.name):
            return query
        
        model_attr = getattr(model_class, field.name)
        
        # Handle different field types (using EXISTING FieldType values)
        if field.field_type == FieldType.TEXT:
            # Text fields use LIKE
            query = query.filter(model_attr.ilike(f'%{filter_value}%'))
        
        elif field.field_type == FieldType.SELECT:
            # Select fields use exact match
            if filter_value and filter_value != 'all':
                query = query.filter(model_attr == filter_value)
        
        elif field.field_type in [FieldType.UUID, FieldType.ENTITY_SEARCH, FieldType.REFERENCE]:
            # UUID fields need conversion
            try:
                if isinstance(filter_value, str) and len(filter_value) == 36:
                    filter_uuid = uuid.UUID(filter_value)
                else:
                    filter_uuid = filter_value
                query = query.filter(model_attr == filter_uuid)
            except ValueError:
                logger.warning(f"Invalid UUID for {field.name}: {filter_value}")
        
        elif field.field_type in [FieldType.DATE, FieldType.DATETIME]:
            # Date fields - check for range filters using filter_aliases
            handled = False
            
            # Check if this field has date range aliases
            if hasattr(field, 'filter_aliases') and field.filter_aliases:
                for alias in field.filter_aliases:
                    if 'start_date' in alias or 'date_from' in alias:
                        if alias in filters:
                            start_date = self._parse_date(filters[alias])
                            if start_date:
                                query = query.filter(model_attr >= start_date)
                                handled = True
                    elif 'end_date' in alias or 'date_to' in alias:
                        if alias in filters:
                            end_date = self._parse_date(filters[alias])
                            if end_date:
                                query = query.filter(model_attr <= end_date)
                                handled = True
            
            # Single date filter
            if not handled and filter_value:
                date_value = self._parse_date(filter_value)
                if date_value:
                    query = query.filter(model_attr == date_value)
        
        elif field.field_type in [FieldType.INTEGER, FieldType.DECIMAL, FieldType.CURRENCY]:
            # Numeric fields - check for range filters
            handled = False
            
            # Check if this field has range aliases
            if hasattr(field, 'filter_aliases') and field.filter_aliases:
                for alias in field.filter_aliases:
                    if 'min' in alias:
                        if alias in filters:
                            try:
                                min_val = float(filters[alias])
                                query = query.filter(model_attr >= min_val)
                                handled = True
                            except ValueError:
                                pass
                    elif 'max' in alias:
                        if alias in filters:
                            try:
                                max_val = float(filters[alias])
                                query = query.filter(model_attr <= max_val)
                                handled = True
                            except ValueError:
                                pass
            
            # Exact match
            if not handled and filter_value:
                try:
                    num_val = float(filter_value)
                    query = query.filter(model_attr == num_val)
                except ValueError:
                    pass
        
        elif field.field_type == FieldType.BOOLEAN:
            # Boolean fields
            bool_val = str(filter_value).lower() in ['true', '1', 'yes']
            query = query.filter(model_attr == bool_val)
        
        return query


    def _apply_search_filter(self, query, model_class, config, search_term):
        """
        NEW HELPER METHOD
        Purpose: Apply search across all searchable fields
        Uses: searchable (existing property)
        """
        from sqlalchemy import or_
        
        search_conditions = []
        for field in config.fields:
            # Use existing searchable property
            if field.searchable and hasattr(model_class, field.name):
                model_attr = getattr(model_class, field.name)
                
                # Text fields use ILIKE
                if field.field_type in [FieldType.TEXT, FieldType.TEXTAREA]:
                    search_conditions.append(
                        model_attr.ilike(f'%{search_term}%')
                    )
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
        
        return query


    # =========================================================================
    # ENHANCEMENT 4: Automatic Filter Data Generation
    # =========================================================================
    def get_complete_filter_data(self, **kwargs) -> dict:
        """
        REPLACE/ENHANCE EXISTING METHOD
        Purpose: Generate filter data automatically from field configuration
        Backward Compatible: Yes - returns same structure
        """
        try:
            config = self._get_entity_config()
            if not config:
                return {'backend_data': {}, 'success': False}
            
            hospital_id = kwargs.get('hospital_id')
            branch_id = kwargs.get('branch_id')
            
            filter_data = {}
            
            with get_db_session() as session:
                for field in config.fields:
                    # Skip non-filterable fields (existing property)
                    if not field.filterable:
                        continue
                    
                    # Generate filter options based on field type
                    if field.field_type == FieldType.SELECT and field.options:
                        # Use configured options (existing property)
                        filter_data[field.name] = field.options
                    
                    elif field.field_type in [FieldType.ENTITY_SEARCH, FieldType.UUID, FieldType.REFERENCE]:
                        # Check if it's a relationship field
                        if (hasattr(field, 'entity_search_config') or 
                            field.name.endswith('_id')):
                            # Load options from related entity
                            options = self._load_foreign_key_options(
                                session, field, hospital_id, branch_id
                            )
                            filter_data[field.name] = options
                            # Also add with '_options' suffix for compatibility
                            filter_data[f"{field.name}_options"] = options
            
            return {
                'backend_data': filter_data,
                'success': True,
                'error_messages': []
            }
            
        except Exception as e:
            logger.error(f"Error generating filter data: {str(e)}")
            return {
                'backend_data': {},
                'success': False,
                'error_messages': [str(e)]
            }


    def _load_foreign_key_options(self, session, field, hospital_id, branch_id):
        """
        NEW HELPER METHOD
        Purpose: Load options for a foreign key field for filter dropdowns
        """
        try:
            # Determine the related entity
            related_entity = None
            
            # Check entity_search_config (existing property)
            if hasattr(field, 'entity_search_config') and field.entity_search_config:
                config = field.entity_search_config
                if hasattr(config, 'target_entity'):
                    related_entity = config.target_entity
                elif isinstance(config, dict):
                    related_entity = config.get('target_entity')
            
            # Derive from field name
            if not related_entity and field.name.endswith('_id'):
                entity_name = field.name[:-3]
                related_entity = f"{entity_name}s"
            
            if not related_entity:
                return []
            
            from app.config.entity_registry import ENTITY_REGISTRY
            
            if related_entity not in ENTITY_REGISTRY:
                return []
            
            registration = ENTITY_REGISTRY[related_entity]
            
            if not registration.model_class:
                return []
            
            # Import the model
            module_path, class_name = registration.model_class.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            model_class = getattr(module, class_name)
            
            # Build query
            query = session.query(model_class)
            
            # Apply standard filters
            if hasattr(model_class, 'hospital_id'):
                query = query.filter(model_class.hospital_id == hospital_id)
            
            if branch_id and hasattr(model_class, 'branch_id'):
                query = query.filter(model_class.branch_id == branch_id)
            
            # Filter active only
            if hasattr(model_class, 'status'):
                query = query.filter(model_class.status == 'active')
            elif hasattr(model_class, 'is_active'):
                query = query.filter(model_class.is_active == True)
            
            # Get display field
            display_field = field.related_display_field or 'name'
            
            # Order by display field
            if hasattr(model_class, display_field):
                query = query.order_by(getattr(model_class, display_field))
            
            # Execute and format
            items = query.all()
            options = []
            
            for item in items:
                # Get ID field
                id_field = f"{field.name[:-3]}_id" if field.name.endswith('_id') else 'id'
                if hasattr(item, field.name):
                    id_field = field.name
                elif hasattr(item, f"{related_entity[:-1]}_id"):
                    id_field = f"{related_entity[:-1]}_id"
                
                if hasattr(item, id_field):
                    item_id = getattr(item, id_field)
                    
                    # Get display value
                    display_value = "Unknown"
                    for name_field in [display_field, f"{related_entity[:-1]}_name", 'name', 'title']:
                        if hasattr(item, name_field):
                            display_value = getattr(item, name_field)
                            break
                    
                    options.append({
                        'value': str(item_id),
                        'label': display_value,
                        'text': display_value  # For compatibility
                    })
            
            # Add "All" option at the beginning
            label = field.label or field.name.replace('_', ' ').title()
            return [{'value': '', 'label': f'All {label}', 'text': f'All {label}'}] + options
            
        except Exception as e:
            logger.error(f"Error loading options for {field.name}: {e}")
            return []


    # =========================================================================
    # HELPER: Get entity configuration
    # =========================================================================
    def _get_entity_config(self):
        """
        NEW HELPER METHOD
        Purpose: Get configuration for current entity
        """
        from app.config.entity_configurations import get_entity_config
        return get_entity_config(self.entity_type)


    def _parse_date(self, date_str):
        """
        NEW HELPER METHOD
        Purpose: Parse date string to datetime
        """
        if not date_str:
            return None
        
        from datetime import datetime
        
        # Try common formats
        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None


    # =========================================================================
    # For backward compatibility, add public wrapper if needed
    # =========================================================================
    def add_relationships(self, entity_dict: Dict, entity, session) -> Dict:
        """
        PUBLIC WRAPPER (for categorized processor compatibility)
        Purpose: Public wrapper for relationship addition
        """
        return self._add_relationships(entity_dict, entity, session)