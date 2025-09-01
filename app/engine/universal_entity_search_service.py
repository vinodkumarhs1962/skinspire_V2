# =============================================================================
# Universal Entity Search Service - Backend-Heavy, Configuration-Driven
# =============================================================================

import importlib
from typing import Dict, List, Any, Optional
import uuid
from flask_login import current_user
from app.services.database_service import get_db_session
from app.config.entity_configurations import get_entity_config, get_entity_filter_config
from app.config.core_definitions import FieldDefinition, FieldType, EntitySearchConfiguration
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalEntitySearchService:
    """
    Universal backend service for entity search fields
    ARCHITECTURE: Configuration-driven, entity-agnostic, backend-heavy
    """
    
    def __init__(self):
        self.model_mappings = {...}  # Model mappings
        self.entity_type = 'entity_search'  # ✅ ADD: For cache identification
    
    @cache_service_method('entity_search', 'search_entities')  # ✅ ADD: Cache entity searches
    def search_entities(self, config: EntitySearchConfiguration, search_term: str,
                       hospital_id: uuid.UUID, branch_id: uuid.UUID = None) -> List[Dict]:
        """Universal search - works for ANY entity via configuration"""
        try:
            if len(search_term) < config.min_chars:
                return []
            
            # ✅ Get model class from configuration (not hardcoded)
            model_class = self._get_model_class_from_config(config)
            if not model_class:
                logger.error(f"No model class found for {config.target_entity}")
                return []
            
            with get_db_session() as session:
                # ✅ Build query (entity-agnostic)
                query = session.query(model_class).filter_by(hospital_id=hospital_id)
                
                # Apply branch filter if applicable
                if branch_id and hasattr(model_class, 'branch_id'):
                    query = query.filter_by(branch_id=branch_id)
                
                # ✅ Build search conditions from configuration
                search_conditions = []
                for field_name in config.search_fields:
                    if hasattr(model_class, field_name):
                        field = getattr(model_class, field_name)
                        search_conditions.append(field.ilike(f"%{search_term}%"))
                
                if search_conditions:
                    from sqlalchemy import or_
                    query = query.filter(or_(*search_conditions))
                
                # ✅ Apply additional filters from configuration
                for filter_key, filter_value in config.additional_filters.items():
                    if hasattr(model_class, filter_key):
                        query = query.filter(getattr(model_class, filter_key) == filter_value)
                
                # ✅ Apply sorting from configuration
                if hasattr(model_class, config.sort_field):
                    query = query.order_by(getattr(model_class, config.sort_field))
                
                results = query.limit(config.max_results).all()
                
                # ✅ Format results using configuration
                return self._format_search_results(results, config)
                
        except Exception as e:
            logger.error(f"Error in universal search: {str(e)}")
            return []
    
        
    def _search_generic_entity(self, config: EntitySearchConfiguration, search_term: str,
                              hospital_id: uuid.UUID, branch_id: uuid.UUID = None) -> List[Dict]:
        """Generic entity search using configuration"""
        try:
            # ✅ Get model class dynamically
            model_class = self._get_model_class(config.target_entity)
            if not model_class:
                return []
            
            with get_db_session() as session:
                query = session.query(model_class).filter_by(hospital_id=hospital_id)
                
                # Build search conditions from configuration
                search_conditions = []
                for field in config.search_fields:
                    if hasattr(model_class, field):
                        search_conditions.append(
                            getattr(model_class, field).ilike(f"%{search_term}%")
                        )
                
                if search_conditions:
                    from sqlalchemy import or_
                    query = query.filter(or_(*search_conditions))
                
                results = query.limit(config.max_results).all()
                return self._format_search_results(results, config)
                
        except Exception as e:
            logger.error(f"Error in generic entity search: {str(e)}")
            return []
    
    def _format_search_results(self, results: List, config: EntitySearchConfiguration) -> List[Dict]:
        """Format search results using configuration template"""
        formatted_results = []
        
        for result in results:
            try:
                # ✅ Extract primary key (entity-agnostic)
                primary_key = getattr(result, 'id', None) or getattr(result, f'{config.target_entity[:-1]}_id', None)
                
                # ✅ Build display text using template
                display_text = self._build_display_text(result, config.display_template)
                
                # ✅ Build search metadata
                search_metadata = {
                    'value': str(primary_key),
                    'label': display_text,
                    'entity_type': config.target_entity,
                    'search_text': display_text.lower()
                }
                
                # ✅ Add extra fields for enhanced display
                for field in config.search_fields:
                    if hasattr(result, field):
                        search_metadata[field] = getattr(result, field)
                
                formatted_results.append(search_metadata)
                
            except Exception as e:
                logger.error(f"Error formatting result: {str(e)}")
                continue
        
        return formatted_results
    
    def _build_display_text(self, result, template: str) -> str:
        """Build display text using template"""
        try:
            # ✅ Replace template variables with actual values
            display_text = template
            import re
            
            # Find all {field_name} patterns
            fields = re.findall(r'\{(\w+)\}', template)
            
            for field in fields:
                if hasattr(result, field):
                    value = getattr(result, field) or ''
                    display_text = display_text.replace(f'{{{field}}}', str(value))
                else:
                    display_text = display_text.replace(f'{{{field}}}', '')
            
            # Clean up extra spaces
            display_text = ' '.join(display_text.split())
            return display_text
            
        except Exception as e:
            logger.error(f"Error building display text: {str(e)}")
            return str(getattr(result, 'name', result))
    
    def _get_model_class(self, entity_type: str):
        """Get SQLAlchemy model class for entity type"""
        model_mapping = {
            'suppliers': 'app.models.master.Supplier',
            'patients': 'app.models.master.Patient', 
            'medicines': 'app.models.master.Medicine',
            'users': 'app.models.transaction.User'
        }
        
        if entity_type not in model_mapping:
            return None
        
        try:
            module_path, class_name = model_mapping[entity_type].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
        except Exception as e:
            logger.error(f"Error importing model for {entity_type}: {str(e)}")
            return None

    @cache_service_method('entity_search', 'get_filter_backend_data')    
    def get_filter_backend_data(self, entity_type: str, hospital_id: uuid.UUID,
                               branch_id: uuid.UUID = None, current_filters: Dict = None) -> Dict:
        """Universal filter data - works for ANY entity via configuration"""
        try:
            backend_data = {}
            
            # ✅ Get filter configuration (not hardcoded)
            filter_config = get_entity_filter_config(entity_type)
            if filter_config:
                # Add configured filter options
                for field_name, field_config in filter_config.filter_mappings.items():
                    backend_data[field_name] = field_config.get('options', [])
            
            # ✅ Get entity configuration for dynamic fields
            entity_config = get_entity_config(entity_type)
            if entity_config:
                for field in entity_config.fields:
                    if field.filterable and field.field_type == FieldType.ENTITY_SEARCH:
                        # Get entity search data if needed
                        search_data = self._get_entity_search_filter_data(
                            field, entity_type, hospital_id, branch_id
                        )
                        backend_data[f"{field.name}_search"] = search_data
            
            return backend_data
            
        except Exception as e:
            logger.error(f"Error getting filter backend data: {str(e)}")
            return {}

    def _get_entity_search_filter_data(self, 
                                      field, 
                                      current_value: str, 
                                      hospital_id: uuid.UUID, 
                                      branch_id: uuid.UUID = None) -> List[Dict]:
        """
        Get entity search data for filter fields
        
        REUSES: Existing search infrastructure from search_entities method
        """
        try:
            if not current_value:
                return []
                
            # Use existing search infrastructure
            results = self.search_entities(
                config=field.entity_search_config,
                search_term=current_value,
                hospital_id=hospital_id,
                branch_id=branch_id
            )
            
            return results[:5]  # Limit for filter dropdown
            
        except Exception as e:
            logger.error(f"Error getting entity search filter data: {str(e)}")
            return []

    def _get_entity_specific_filter_data(self, 
                                       entity_type: str, 
                                       hospital_id: uuid.UUID, 
                                       branch_id: uuid.UUID = None) -> Dict:
        """
        Get entity-specific filter data (e.g., suppliers for supplier_payments)
        
        DELEGATES: To entity-specific methods when available
        """
        try:
            if entity_type == 'supplier_payments':
                return self._get_supplier_payment_filter_data(hospital_id, branch_id)
            elif entity_type == 'suppliers':
                return self._get_supplier_filter_data(hospital_id, branch_id)
            # Add other entities as needed
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting entity-specific filter data for {entity_type}: {str(e)}")
            return {}

    # ========================================================================
    # UNIVERSAL HELPER METHODS (Entity-Agnostic)
    # ========================================================================
    
    def _get_model_class_from_config(self, config: EntitySearchConfiguration):
        """Get model class from configuration"""
        if config.model_path:
            try:
                module_path, class_name = config.model_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                return getattr(module, class_name)
            except Exception as e:
                logger.error(f"Error importing model {config.model_path}: {str(e)}")
        
        # Fallback to existing mapping
        return self._get_model_class(config.target_entity)
    
    def _get_entity_search_filter_data(self, field: FieldDefinition, entity_type: str,
                                     hospital_id: uuid.UUID, branch_id: uuid.UUID) -> List[Dict]:
        """Get entity search data for filter dropdowns"""
        try:
            if not hasattr(field, 'entity_search_config'):
                return []
            
            # Use existing search method with empty term to get common results
            results = self.search_entities(
                config=field.entity_search_config,
                search_term='',  # Empty to get common results
                hospital_id=hospital_id,
                branch_id=branch_id
            )
            
            return results[:5]  # Limit for dropdown
            
        except Exception as e:
            logger.error(f"Error getting entity search filter data: {str(e)}")
            return []
    