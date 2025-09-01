# Complete Entity Configuration Registry with Utilities
# File: app/config/entity_configurations.py

"""
Central Entity Configuration Registry
Routes entity configurations to modules while preserving all utilities
Maintains backward compatibility
"""

import importlib
import logging
from typing import Dict, Optional, Any, List
from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, EntityFilterConfiguration,
    EntitySearchConfiguration, LayoutType
)
from app.config.filter_categories import FilterCategory

logger = logging.getLogger(__name__)

# =============================================================================
# MODULE REGISTRY
# =============================================================================

MODULE_MAPPING = {
    # Financial entities
    "supplier_payments": "app.config.modules.financial_transactions",
    "billing": "app.config.modules.financial_transactions",
    "customer_receipts": "app.config.modules.financial_transactions",
    
    # Master entities
    "suppliers": "app.config.modules.master_entities",
    "patients": "app.config.modules.master_entities", 
    "users": "app.config.modules.master_entities",
    
    # Inventory entities (when implemented)
    "medicines": "app.config.modules.inventory",
    "stock_movements": "app.config.modules.inventory",
    "purchase_orders": "app.config.modules.inventory",
}

# =============================================================================
# CONFIGURATION LOADER
# =============================================================================

class ConfigurationLoader:
    """Loads configurations from modules on demand"""
    
    def __init__(self):
        self._cache = {}
        self._module_cache = {}
        self._filter_configs = {}
        self._search_configs = {}
    
    def get_config(self, entity_type: str) -> Optional[EntityConfiguration]:
        """Get configuration for entity type"""
        if entity_type in self._cache:
            return self._cache[entity_type]
        
        module_path = MODULE_MAPPING.get(entity_type)
        if not module_path:
            logger.warning(f"No module mapping found for entity type: {entity_type}")
            return None
        
        try:
            if module_path not in self._module_cache:
                module = importlib.import_module(module_path)
                self._module_cache[module_path] = module
                
                # Load all configs from module
                if hasattr(module, 'get_module_configs'):
                    configs = module.get_module_configs()
                    self._cache.update(configs)
                
                # Load filter configs if available
                if hasattr(module, 'get_module_filter_configs'):
                    filter_configs = module.get_module_filter_configs()
                    self._filter_configs.update(filter_configs)
                
                # Load search configs if available
                if hasattr(module, 'get_module_search_configs'):
                    search_configs = module.get_module_search_configs()
                    self._search_configs.update(search_configs)
            
            return self._cache.get(entity_type)
            
        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error loading config for {entity_type}: {str(e)}")
            return None
    
    def get_filter_config(self, entity_type: str) -> Optional[EntityFilterConfiguration]:
        """Get filter configuration for entity type"""
        # Try cache first
        if entity_type in self._filter_configs:
            return self._filter_configs[entity_type]
        
        # Load entity config (which loads module)
        self.get_config(entity_type)
        
        return self._filter_configs.get(entity_type)
    
    def get_search_config(self, entity_type: str) -> Optional[EntitySearchConfiguration]:
        """Get search configuration for entity type"""
        # Try cache first
        if entity_type in self._search_configs:
            return self._search_configs[entity_type]
        
        # Load entity config (which loads module)
        self.get_config(entity_type)
        
        return self._search_configs.get(entity_type)

# Global loader instance
_loader = ConfigurationLoader()

# =============================================================================
# BACKWARD COMPATIBLE LAZY LOADING
# =============================================================================

class LazyConfigProxy:
    """Proxy that loads configuration on first access"""
    
    def __init__(self, entity_type: str):
        self._entity_type = entity_type
        self._config = None
    
    def __getattr__(self, name):
        if self._config is None:
            self._config = _loader.get_config(self._entity_type)
            if self._config is None:
                raise AttributeError(f"Configuration not found for {self._entity_type}")
        return getattr(self._config, name)

# Lazy proxies for backward compatibility
SUPPLIER_PAYMENT_CONFIG = LazyConfigProxy("supplier_payments")
SUPPLIER_CONFIG = LazyConfigProxy("suppliers")

# =============================================================================
# ENTITY_CONFIGS DICTIONARY - BACKWARD COMPATIBLE
# =============================================================================

class LazyConfigDict(dict):
    """Dictionary that loads configs on access"""
    
    def __getitem__(self, key):
        if key not in self:
            config = _loader.get_config(key)
            if config:
                self[key] = config
            else:
                raise KeyError(f"No configuration found for entity: {key}")
        return super().__getitem__(key)

ENTITY_CONFIGS = LazyConfigDict()

# =============================================================================
# ENTITY FILTER CONFIGS - BACKWARD COMPATIBLE
# =============================================================================

class LazyFilterConfigDict(dict):
    """Dictionary that loads filter configs on access"""
    
    def __getitem__(self, key):
        if key not in self:
            config = _loader.get_filter_config(key)
            if config:
                self[key] = config
            else:
                raise KeyError(f"No filter configuration found for entity: {key}")
        return super().__getitem__(key)

ENTITY_FILTER_CONFIGS = LazyFilterConfigDict()

# Also add ENTITY_SEARCH_CONFIGS for completeness
class LazySearchConfigDict(dict):
    """Dictionary that loads search configs on access"""
    
    def __getitem__(self, key):
        if key not in self:
            config = _loader.get_search_config(key)
            if config:
                self[key] = config
            else:
                raise KeyError(f"No search configuration found for entity: {key}")
        return super().__getitem__(key)

ENTITY_SEARCH_CONFIGS = LazySearchConfigDict()


# =============================================================================
# UTILITY FUNCTIONS - PRESERVED FROM ORIGINAL
# =============================================================================

def get_entity_config(entity_type: str) -> Optional[EntityConfiguration]:
    """Get entity configuration by type"""
    return _loader.get_config(entity_type)

def is_valid_entity_type(entity_type: str) -> bool:
    """Check if entity type is valid and registered"""
    return entity_type in MODULE_MAPPING

def list_entity_types() -> List[str]:
    """Get list of all registered entity types"""
    return list(MODULE_MAPPING.keys())

def get_entity_permissions(entity_type: str) -> Dict[str, str]:
    """Get permission mapping for entity type"""
    config = get_entity_config(entity_type)
    return config.permissions if config else {}

def get_searchable_fields(entity_type: str) -> List[str]:
    """Get list of searchable fields for entity type"""
    config = get_entity_config(entity_type)
    return config.searchable_fields if config else []

def get_filterable_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of filterable fields for entity type"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.filterable]

def get_list_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of fields to show in list view"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.show_in_list]

def get_form_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of fields to show in forms"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.show_in_form]

def get_detail_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of fields to show in detail view"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.show_in_detail]

def get_field_by_name(entity_type: str, field_name: str) -> Optional[FieldDefinition]:
    """Get specific field definition by name"""
    config = get_entity_config(entity_type)
    if not config:
        return None
    return next((field for field in config.fields if field.name == field_name), None)

def get_required_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of required fields for entity type"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.required]

def get_entity_primary_key(entity_type: str) -> Optional[str]:
    """Get primary key field name for entity type"""
    config = get_entity_config(entity_type)
    return config.primary_key if config else None

def get_entity_title_field(entity_type: str) -> Optional[str]:
    """Get title field name for entity type"""
    config = get_entity_config(entity_type)
    return config.title_field if config else None

# =============================================================================
# ENTITY FILTER CONFIGURATION - CROSS-CUTTING
# =============================================================================

def get_entity_filter_config(entity_type: str) -> Optional[EntityFilterConfiguration]:
    """Get filter configuration for entity type"""
    return _loader.get_filter_config(entity_type)

# =============================================================================
# ENTITY SEARCH CONFIGURATION - CROSS-CUTTING
# =============================================================================

def get_entity_search_config(entity_type: str) -> Optional[EntitySearchConfiguration]:
    """Get search configuration for entity type"""
    return _loader.get_search_config(entity_type)

# =============================================================================
# VALIDATION FUNCTIONS - PRESERVED
# =============================================================================

def validate_entity_config(config: EntityConfiguration) -> List[str]:
    """Validate entity configuration"""
    errors = []
    
    # Basic validations
    if not config.entity_type:
        errors.append("entity_type is required")
    
    if not config.primary_key:
        errors.append("primary_key is required")
    
    if not config.fields:
        errors.append("At least one field must be defined")
    
    # Field validations
    field_names = set()
    for field in config.fields:
        if field.name in field_names:
            errors.append(f"Duplicate field name: {field.name}")
        field_names.add(field.name)
        
        if field.required and field.default_value is None and not field.show_in_form:
            errors.append(f"Required field {field.name} must be shown in form or have default value")
    
    # Primary key validation
    pk_field = next((f for f in config.fields if f.name == config.primary_key), None)
    if not pk_field:
        errors.append(f"Primary key field '{config.primary_key}' not found in fields")
    
    # Title field validation
    if config.title_field:
        title_field = next((f for f in config.fields if f.name == config.title_field), None)
        if not title_field:
            errors.append(f"Title field '{config.title_field}' not found in fields")
    
    return errors

def validate_all_configs() -> bool:
    """Validate all registered entity configurations"""
    all_valid = True
    
    print("\n🔍 Validating all entity configurations...")
    
    for entity_type in MODULE_MAPPING.keys():
        config = get_entity_config(entity_type)
        if not config:
            print(f"❌ {entity_type}: Configuration not found")
            all_valid = False
            continue
        
        errors = validate_entity_config(config)
        if errors:
            print(f"❌ {entity_type}: {len(errors)} errors")
            for error in errors:
                print(f"   - {error}")
            all_valid = False
        else:
            print(f"✅ {entity_type}: Valid")
    
    if all_valid:
        print("\n✅ All configurations are valid!")
    else:
        print("\n⚠️  Some configurations have errors - please fix before proceeding")
    
    return all_valid

# =============================================================================
# LAYOUT SWITCHING - PRESERVED
# =============================================================================

def switch_layout_type(entity_type: str, layout_type: str):
    """Switch layout type for entity"""
    config = get_entity_config(entity_type)
    if not config:
        print(f"❌ Entity type '{entity_type}' not found")
        return
    
    if not hasattr(config, 'view_layout'):
        print(f"❌ Entity '{entity_type}' has no view layout configuration")
        return
    
    if layout_type == 'simple':
        config.view_layout.type = LayoutType.SIMPLE
    elif layout_type == 'tabbed':
        config.view_layout.type = LayoutType.TABBED
    elif layout_type == 'accordion':
        config.view_layout.type = LayoutType.ACCORDION
    else:
        print(f"❌ Unknown layout type: {layout_type}")
        return
    
    print(f"✅ {entity_type}: Switched to {layout_type} layout")

# Convenience function for supplier payments (backward compatible)
def switch_layout_type_legacy(layout_type: str):
    """Legacy function for switching supplier payment layout"""
    switch_layout_type('supplier_payments', layout_type)

# =============================================================================
# FIELD NAME MAPPING FOR SERVICE COMPATIBILITY - PRESERVED
# =============================================================================

FILTER_MAPPING = {
    "supplier_payments": {
        "workflow_status": "statuses",
        "payment_method": "payment_methods",
        "supplier_id": "supplier_id",
        "start_date": "start_date",
        "end_date": "end_date",
        "search": "search",
        "reference_no": "reference_no",
        "amount": "amount",
    },
    "suppliers": {
        "status": "status",
        "supplier_category": "supplier_category",
        "search": "search",
        "black_listed": "black_listed",
    }
}

def get_service_filter_mapping(entity_type: str) -> Dict[str, str]:
    """Get filter name mapping for service compatibility"""
    return FILTER_MAPPING.get(entity_type, {})

# =============================================================================
# HEALTH CHECK
# =============================================================================

def check_configuration_health():
    """Check if all configurations can be loaded"""
    print("🔍 Checking configuration health...")
    
    healthy = True
    for entity_type in MODULE_MAPPING.keys():
        try:
            config = get_entity_config(entity_type)
            if config:
                print(f"✅ {entity_type}: OK")
            else:
                print(f"❌ {entity_type}: Configuration not found")
                healthy = False
        except Exception as e:
            print(f"❌ {entity_type}: Error - {str(e)}")
            healthy = False
    
    if healthy:
        print("✅ All configurations healthy!")
    else:
        print("⚠️  Some configurations have issues")
    
    return healthy

# =============================================================================
# INITIALIZATION HELPERS
# =============================================================================

def initialize_configurations():
    """Initialize all configurations (useful for preloading)"""
    for entity_type in MODULE_MAPPING.keys():
        get_entity_config(entity_type)
    logger.info(f"Initialized {len(MODULE_MAPPING)} entity configurations")

# Log initialization
logger.info(f"Entity configuration registry initialized with {len(MODULE_MAPPING)} entity mappings")