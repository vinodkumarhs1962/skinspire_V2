# =============================================================================
# ADD TO: app/engine/universal_services.py
# Universal Filter Service - Dedicated Class for All Filter Operations
# =============================================================================

import importlib
from typing import Dict, Any, Optional, List, Set, Tuple
import uuid
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from flask_login import current_user

from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)


class UniversalFilterService:
    """
    ✅ ENTITY-AGNOSTIC: Universal filter service for any entity type
    Handles configuration-driven filtering with support for all filter types
    """
    
    def __init__(self):
        """Initialize the universal filter service"""
        self.model_mapping = self._initialize_model_mapping()
        self.filter_type_handlers = self._initialize_filter_handlers()
        
    def _initialize_model_mapping(self) -> Dict[str, str]:
        """
        Initialize entity type to model class mapping
        TODO: This should eventually be moved to entity configurations
        """
        return {
            'supplier_payments': 'app.models.transaction.SupplierPayment',
            'suppliers': 'app.models.master.Supplier',
            'patients': 'app.models.master.Patient',
            'medicines': 'app.models.master.Medicine',
            'invoices': 'app.models.transaction.SupplierInvoice',
            'purchases': 'app.models.transaction.Purchase',
            'sales': 'app.models.transaction.Sale',
            # Add more mappings as needed
        }
    
    def _initialize_filter_handlers(self) -> Dict[str, callable]:
        """Initialize filter type handlers"""
        return {
            'exact': self._apply_exact_filter,
            'search': self._apply_search_filter,
            'range': self._apply_range_filter,
            'in': self._apply_in_filter,
            'date_range': self._apply_date_range_filter,
            'amount_range': self._apply_amount_range_filter,
            'relationship': self._apply_relationship_filter,
            'boolean': self._apply_boolean_filter,
            'null_check': self._apply_null_check_filter
        }
    
    def get_entity_model_class(self, entity_type: str):
        """
        ✅ ENTITY-AGNOSTIC: Get SQLAlchemy model class for any entity type
        """
        try:
            model_path = self.model_mapping.get(entity_type)
            if not model_path:
                raise ValueError(f"No model mapping found for {entity_type}")
            
            module_path, class_name = model_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
            
        except Exception as e:
            logger.error(f"Error getting model class for {entity_type}: {str(e)}")
            return None
    
    def apply_universal_filters(self, entity_type: str, query, filters: Dict, session_scope: Session, config=None) -> Tuple[Any, Set[str], int]:
        """
        ✅ UNIVERSAL ENTRY POINT: Apply configuration-driven filters for any entity
        
        Args:
            entity_type: Entity type (e.g., 'supplier_payments', 'medicines')
            query: Base SQLAlchemy query
            filters: Filters to apply
            session_scope: Database session
            config: Optional pre-loaded configuration
        
        Returns:
            tuple: (filtered_query, applied_filters_set, applied_count)
        """
        try:
            # Get model class for entity
            model_class = self.get_entity_model_class(entity_type)
            if not model_class:
                logger.warning(f"Could not get model class for {entity_type}")
                return query, set(), 0
            
            # Apply configuration-driven filters
            return self.apply_configuration_filters(
                query=query,
                entity_type=entity_type,
                model_class=model_class,
                filters=filters,
                session_scope=session_scope,
                config=config
            )
            
        except Exception as e:
            logger.error(f"Error in universal filter application: {str(e)}")
            return query, set(), 0
    
    def apply_configuration_filters(self, query, entity_type: str, model_class, filters: Dict, session_scope: Session, config=None) -> Tuple[Any, Set[str], int]:
        """
        ✅ ENTITY-AGNOSTIC: Apply filters using configuration for ANY entity
        
        Args:
            query: SQLAlchemy query object
            entity_type: Type of entity
            model_class: SQLAlchemy model class
            filters: Dictionary of filters to apply
            session_scope: Database session
            config: Optional pre-loaded configuration
        
        Returns:
            tuple: (updated_query, applied_filters_set, applied_count)
        """
        try:
            from app.config.entity_configurations import get_entity_config
            
            applied_by_config = 0
            config_applied_filters = set()
            current_query = query  # Track the current query state
            
            # Get configuration if not provided
            if not config:
                config = get_entity_config(entity_type)
                if not config:
                    logger.debug(f"No configuration found for {entity_type}")
                    return query, set(), 0
            
            # Validate configuration has fields
            if not hasattr(config, 'fields') or not config.fields:
                logger.debug(f"No filterable fields in configuration for {entity_type}")
                return query, set(), 0
            
            logger.info(f"🔍 [CONFIG_FILTER] Processing {len(filters)} filters for {entity_type}")
            
            # ✅ ENTITY-AGNOSTIC: Process each filterable field from configuration
            for field in config.fields:
                if not getattr(field, 'filterable', False):
                    continue
                
                # Find filter value for this field
                filter_value, field_name = self._find_filter_value(field, filters)
                
                if filter_value is None or (isinstance(filter_value, str) and not filter_value.strip()):
                    continue
                
                # Apply filter based on field configuration
                current_query, success = self._apply_single_field_filter(
                    query=current_query,
                    field=field,
                    filter_value=filter_value,
                    field_name=field_name,
                    model_class=model_class,
                    session_scope=session_scope
                )
                
                if success:
                    applied_by_config += 1
                    config_applied_filters.add(field_name)
                    logger.debug(f"✅ Applied config filter: {field.name} via {field_name}")
            
            logger.info(f"✅ Configuration applied {applied_by_config} filters: {config_applied_filters}")
            return current_query, config_applied_filters, applied_by_config
            
        except Exception as e:
            logger.error(f"❌ Error in configuration filter application: {str(e)}")
            return query, set(), 0
    
    def _find_filter_value(self, field, filters: Dict) -> Tuple[Any, Optional[str]]:
        """
        Find filter value for a field, checking aliases
        Returns: (filter_value, field_name_used)
        """
        # Primary field name
        if field.name in filters:
            return filters[field.name], field.name
        
        # Check filter aliases
        if hasattr(field, 'filter_aliases') and field.filter_aliases:
            for alias in field.filter_aliases:
                if alias in filters:
                    return filters[alias], alias
        
        return None, None
    
    def _apply_single_field_filter(self, query, field, filter_value, field_name: str, model_class, session_scope: Session) -> Tuple[Any, bool]:
        """
        Apply a single field filter based on field configuration
        Returns: (updated_query, success_flag)
        """
        try:
            # Check if model has this field
            config_field_name = field.name
            if not hasattr(model_class, config_field_name):
                logger.debug(f"Model {model_class.__name__} missing field {config_field_name}")
                return query, False
            
            model_attr = getattr(model_class, config_field_name)
            
            # Get filter type
            filter_type = getattr(field, 'filter_type', 'exact')
            
            # Apply filter based on type
            handler = self.filter_type_handlers.get(filter_type, self._apply_exact_filter)
            return handler(query, model_attr, filter_value, field, field_name, session_scope)
            
        except Exception as e:
            logger.debug(f"❌ Failed to apply filter {field.name}: {str(e)}")
            return query, False
    
    # =============================================================================
    # FILTER TYPE HANDLERS - Each handles a specific type of filtering
    # =============================================================================
    
    def _apply_exact_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply exact match filter"""
        try:
            # ✅ FIXED: Return new query object with filter applied
            filtered_query = query.filter(model_attr == filter_value)
            logger.debug(f"✅ Applied exact filter: {field.name} = {filter_value}")
            return filtered_query, True
        except Exception as e:
            logger.debug(f"❌ Exact filter failed: {str(e)}")
            return query, False
    
    def _apply_search_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply text search filter"""
        try:
            # ✅ FIXED: Return new query object with filter applied
            search_condition = model_attr.ilike(f'%{filter_value}%')
            filtered_query = query.filter(search_condition)
            logger.debug(f"✅ Applied search filter: {field.name} LIKE '%{filter_value}%'")
            return filtered_query, True
        except Exception as e:
            logger.debug(f"❌ Search filter failed: {str(e)}")
            return query, False
    
    def _apply_range_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply range filter (min/max values)"""
        try:
            if isinstance(filter_value, dict):
                filtered_query = query
                
                if 'min' in filter_value and filter_value['min'] is not None:
                    filtered_query = filtered_query.filter(model_attr >= filter_value['min'])
                    logger.debug(f"✅ Applied min range: {field.name} >= {filter_value['min']}")
                
                if 'max' in filter_value and filter_value['max'] is not None:
                    filtered_query = filtered_query.filter(model_attr <= filter_value['max'])
                    logger.debug(f"✅ Applied max range: {field.name} <= {filter_value['max']}")
                
                return filtered_query, True
            
            return query, False
        except Exception as e:
            logger.debug(f"❌ Range filter failed: {str(e)}")
            return query, False
    
    def _apply_in_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply IN filter for multiple values"""
        try:
            if isinstance(filter_value, list) and filter_value:
                in_condition = model_attr.in_(filter_value)
                filtered_query = query.filter(in_condition)
                logger.debug(f"✅ Applied IN filter: {field.name} IN {filter_value}")
                return filtered_query, True
            elif isinstance(filter_value, str):
                # Single value treated as exact match
                exact_condition = model_attr == filter_value
                filtered_query = query.filter(exact_condition)
                logger.debug(f"✅ Applied single value filter: {field.name} = {filter_value}")
                return filtered_query, True
            
            return query, False
        except Exception as e:
            logger.debug(f"❌ IN filter failed: {str(e)}")
            return query, False
    
    def _apply_date_range_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply date range filter"""
        try:
            if isinstance(filter_value, dict):
                filtered_query = query
                
                if 'start_date' in filter_value and filter_value['start_date']:
                    try:
                        start_date = datetime.strptime(filter_value['start_date'], '%Y-%m-%d').date()
                        filtered_query = filtered_query.filter(model_attr >= start_date)
                    except ValueError:
                        pass
                
                if 'end_date' in filter_value and filter_value['end_date']:
                    try:
                        end_date = datetime.strptime(filter_value['end_date'], '%Y-%m-%d').date()
                        filtered_query = filtered_query.filter(model_attr <= end_date)
                    except ValueError:
                        pass
                
                logger.debug(f"✅ Applied date range filter: {field.name}")
                return filtered_query, True
            
            return query, False
        except Exception as e:
            logger.debug(f"❌ Date range filter failed: {str(e)}")
            return query, False
    
    def _apply_amount_range_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply amount range filter with decimal handling"""
        try:
            if isinstance(filter_value, dict):
                filtered_query = query
                
                if 'min_amount' in filter_value and filter_value['min_amount'] is not None:
                    try:
                        min_val = float(filter_value['min_amount'])
                        filtered_query = filtered_query.filter(model_attr >= min_val)
                    except (ValueError, TypeError):
                        pass
                
                if 'max_amount' in filter_value and filter_value['max_amount'] is not None:
                    try:
                        max_val = float(filter_value['max_amount'])
                        filtered_query = filtered_query.filter(model_attr <= max_val)
                    except (ValueError, TypeError):
                        pass
                
                logger.debug(f"✅ Applied amount range filter: {field.name}")
                return filtered_query, True
            
            return query, False
        except Exception as e:
            logger.debug(f"❌ Amount range filter failed: {str(e)}")
            return query, False
    
    def _apply_relationship_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply filter through relationship (e.g., supplier name search)"""
        try:
            # This would need entity-specific implementation
            # For now, fall back to exact match
            return self._apply_exact_filter(query, model_attr, filter_value, field, field_name, session_scope)
        except Exception as e:
            logger.debug(f"❌ Relationship filter failed: {str(e)}")
            return query, False
    
    def _apply_boolean_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply boolean filter"""
        try:
            # Convert string values to boolean
            if isinstance(filter_value, str):
                bool_value = filter_value.lower() in ['true', '1', 'yes', 'on']
            else:
                bool_value = bool(filter_value)
            
            bool_condition = model_attr == bool_value
            filtered_query = query.filter(bool_condition)
            logger.debug(f"✅ Applied boolean filter: {field.name} = {bool_value}")
            return filtered_query, True
        except Exception as e:
            logger.debug(f"❌ Boolean filter failed: {str(e)}")
            return query, False
    
    def _apply_null_check_filter(self, query, model_attr, filter_value, field, field_name: str, session_scope: Session) -> Tuple[Any, bool]:
        """Apply null/not null filter"""
        try:
            if filter_value in ['null', 'is_null', True]:
                null_condition = model_attr.is_(None)
            else:
                null_condition = model_attr.isnot(None)
            
            filtered_query = query.filter(null_condition)
            logger.debug(f"✅ Applied null check filter: {field.name}")
            return filtered_query, True
        except Exception as e:
            logger.debug(f"❌ Null check filter failed: {str(e)}")
            return query, False
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def register_entity_model(self, entity_type: str, model_path: str):
        """Register a new entity type with its model path"""
        self.model_mapping[entity_type] = model_path
        logger.info(f"✅ Registered entity model: {entity_type} -> {model_path}")
    
    def register_filter_handler(self, filter_type: str, handler: callable):
        """Register a new filter type handler"""
        self.filter_type_handlers[filter_type] = handler
        logger.info(f"✅ Registered filter handler: {filter_type}")
    
    def get_supported_filter_types(self) -> List[str]:
        """Get list of supported filter types"""
        return list(self.filter_type_handlers.keys())
    
    def get_registered_entities(self) -> List[str]:
        """Get list of registered entity types"""
        return list(self.model_mapping.keys())
    
    def validate_entity_support(self, entity_type: str) -> bool:
        """Check if entity type is supported"""
        return entity_type in self.model_mapping


# =============================================================================
# GLOBAL INSTANCE AND FACTORY FUNCTIONS
# =============================================================================

# Global instance for easy access
_universal_filter_service = UniversalFilterService()

def get_universal_filter_service() -> UniversalFilterService:
    """Get the global universal filter service instance"""
    return _universal_filter_service

def apply_universal_filters(entity_type: str, query, filters: Dict, session_scope: Session) -> Tuple[Any, Set[str], int]:
    """
    ✅ CONVENIENCE FUNCTION: Apply universal filters using the global service
    This maintains backward compatibility with the original function interface
    """
    return _universal_filter_service.apply_universal_filters(
        entity_type=entity_type,
        query=query,
        filters=filters,
        session_scope=session_scope
    )

# =============================================================================
# INTEGRATION WITH EXISTING UNIVERSAL SERVICES
# =============================================================================

def register_entity_model(entity_type: str, model_path: str):
    """Register a new entity model with the universal filter service"""
    _universal_filter_service.register_entity_model(entity_type, model_path)

def register_filter_handler(filter_type: str, handler: callable):
    """Register a new filter type handler"""
    _universal_filter_service.register_filter_handler(filter_type, handler)