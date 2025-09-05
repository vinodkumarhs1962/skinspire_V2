"""
Entity Configuration Manager - ALL HELPER FUNCTIONS
Handles configuration processing and enhancement logic
"""

from typing import Dict, Any, List, Optional
from app.config.entity_configurations import get_entity_config, ENTITY_CONFIGS
from app.config.filter_categories import FilterCategory, enhance_entity_config_with_categories
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class EntityConfigManager:
    """
    Manages entity configuration processing and enhancement
    All helper functions moved here from entity_configurations.py
    """
    
    @staticmethod
    def enhance_entity_config_with_categories(entity_config):
        """Enhanced configuration with category support"""
        return enhance_entity_config_with_categories(entity_config)
    
    @staticmethod
    def get_filterable_fields_by_category_for_entity(entity_type: str, category: FilterCategory) -> List:
        """Get filterable fields for a specific category"""
        try:
            config = get_entity_config(entity_type)
            if not config:
                return []
            
            from app.config.filter_categories import get_filterable_fields_by_category
            return get_filterable_fields_by_category(config, category)
            
        except Exception as e:
            logger.error(f"Error getting filterable fields for {entity_type}/{category}: {str(e)}")
            return []

    @staticmethod
    def get_filter_categories_for_entity(entity_type: str) -> Dict[str, List]:
        """Get organized filter fields by category for template use"""
        try:
            config = get_entity_config(entity_type)
            if not config:
                return {}
            
            from app.config.filter_categories import FilterCategory, get_filterable_fields_by_category
            
            categorized_fields = {}
            for category in FilterCategory:
                fields = get_filterable_fields_by_category(config, category)
                if fields:
                    categorized_fields[category.value] = fields
            
            return categorized_fields
            
        except Exception as e:
            logger.error(f"Error organizing filter categories for {entity_type}: {str(e)}")
            return {}

    @staticmethod
    def organize_request_filters_by_category(request_filters: Dict, entity_type: str) -> Dict:
        """Organize request filters by category"""
        try:
            config = get_entity_config(entity_type)
            if not config:
                return {}
            
            from app.config.filter_categories import organize_current_filters_by_category
            categorized = organize_current_filters_by_category(request_filters, config)
            
            # Convert FilterCategory enum to string keys for template use
            return {category.value: filters for category, filters in categorized.items()}
            
        except Exception as e:
            logger.error(f"Error organizing request filters: {str(e)}")
            return {}

    @staticmethod
    def validate_and_enhance_all_configurations():
        """Validate and enhance all entity configurations"""
        enhanced_configs = []
        
        try:
            # Import ENTITY_REGISTRY to get all entity types
            from app.config.entity_registry import ENTITY_REGISTRY
            
            # Enhance all registered configurations
            for entity_type in ENTITY_REGISTRY.keys():
                try:
                    # Get the config using the get_entity_config function
                    config = get_entity_config(entity_type)
                    if config:
                        EntityConfigManager.enhance_entity_config_with_categories(config)
                        enhanced_configs.append(entity_type)
                except Exception as e:
                    logger.warning(f"Could not enhance {entity_type} config: {str(e)}")
            
            logger.info(f"✅ Enhanced {len(enhanced_configs)} entity configurations: {enhanced_configs}")
            return enhanced_configs
            
        except Exception as e:
            logger.error(f"❌ Error validating and enhancing configurations: {str(e)}")
            return []