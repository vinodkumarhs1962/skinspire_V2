# =============================================================================
# File: app/config/filter_categories.py
# Filter Categories Integration with Existing Field Definitions
# =============================================================================

"""
Filter Category System integrated with existing FieldDefinition structure
Backward compatible - enhances existing system without breaking changes
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from app.config.core_definitions import FieldDefinition, FieldType

class FilterCategory(Enum):
    """
    Core filter categories for universal entity filtering
    Each category has specialized processing logic and UI behavior
    """
    DATE = "date"
    AMOUNT = "amount"
    SEARCH = "search"
    SELECTION = "selection"
    RELATIONSHIP = "relationship"

@dataclass
class FilterCategoryConfig:
    """
    Configuration for how each filter category behaves
    Defines processing rules, validation, and UI characteristics
    """
    category: FilterCategory
    requires_parsing: bool = False
    supports_presets: bool = False
    supports_range: bool = False
    validation_rules: List[str] = None
    ui_grouping: bool = False
    auto_submit: bool = False
    default_behavior: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validation_rules is None:
            self.validation_rules = []
        if self.default_behavior is None:
            self.default_behavior = {}

# =============================================================================
# CATEGORY-SPECIFIC CONFIGURATION
# =============================================================================

FILTER_CATEGORY_CONFIG = {
    FilterCategory.DATE: FilterCategoryConfig(
        category=FilterCategory.DATE,
        requires_parsing=True,
        supports_presets=True,
        supports_range=True,
        validation_rules=['valid_date_format', 'logical_date_range'],
        ui_grouping=True,
        auto_submit=True,
        default_behavior={
            'default_preset': 'current_financial_year',
            'date_format': '%Y-%m-%d',
            'range_validation': True,
            'preset_options': [
                'current_financial_year',
                'last_financial_year', 
                'current_month',
                'last_month',
                'last_7_days',
                'last_30_days'
            ]
        }
    ),
    
    FilterCategory.AMOUNT: FilterCategoryConfig(
        category=FilterCategory.AMOUNT,
        requires_parsing=True,
        supports_range=True,
        validation_rules=['positive_numbers', 'valid_decimal_format'],
        ui_grouping=True,
        auto_submit=True,
        default_behavior={
            'decimal_places': 2,
            'currency_symbol': '₹',
            'range_validation': True,
            'allow_zero': True,
            'max_digits': 10
        }
    ),
    
    FilterCategory.SEARCH: FilterCategoryConfig(
        category=FilterCategory.SEARCH,
        requires_parsing=False,
        validation_rules=['min_length_2', 'safe_sql_chars'],
        ui_grouping=False,
        auto_submit=False,  # Manual search to avoid too many requests
        default_behavior={
            'min_search_length': 2,
            'search_type': 'partial_match',  # or 'exact_match', 'wildcard'
            'case_sensitive': False,
            'trim_whitespace': True
        }
    ),
    
    FilterCategory.SELECTION: FilterCategoryConfig(
        category=FilterCategory.SELECTION,
        requires_parsing=False,
        supports_presets=False,
        validation_rules=['valid_choice'],
        ui_grouping=True,
        auto_submit=True,
        default_behavior={
            'allow_multiple': False,
            'include_empty_option': True,
            'empty_option_label': 'All',
            'sort_choices': True
        }
    ),
    
    FilterCategory.RELATIONSHIP: FilterCategoryConfig(
        category=FilterCategory.RELATIONSHIP,
        requires_parsing=False,
        validation_rules=['valid_entity_id', 'entity_exists'],
        ui_grouping=True,
        auto_submit=True,
        default_behavior={
            'lazy_loading': True,
            'search_threshold': 10,  # Show search if more than 10 options
            'display_format': 'name_with_id',
            'cache_duration': 300  # 5 minutes
        }
    )
}

# =============================================================================
# FIELD CATEGORY DETECTION - INTEGRATED WITH EXISTING FIELDTYPE
# =============================================================================

def get_field_category_from_existing_field(field: FieldDefinition) -> FilterCategory:
    """
    Determine filter category based on existing FieldDefinition
    Works with your current FieldType enum and field properties
    """
    field_name = field.name.lower()
    field_type = field.field_type
    
    # Check explicit category assignment first
    if hasattr(field, 'filter_category') and field.filter_category:
        return field.filter_category
    
    # Date category - based on FieldType and field names
    if field_type in [FieldType.DATE, FieldType.DATETIME]:
        return FilterCategory.DATE
    
    date_patterns = ['date', 'created_at', 'updated_at', 'start_date', 'end_date']
    if any(pattern in field_name for pattern in date_patterns):
        return FilterCategory.DATE
    
    # Amount category - based on FieldType and field names
    if field_type in [FieldType.AMOUNT, FieldType.NUMBER, FieldType.CURRENCY]:
        return FilterCategory.AMOUNT
    
    amount_patterns = ['amount', 'price', 'cost', 'fee', 'min_', 'max_']
    if any(pattern in field_name for pattern in amount_patterns):
        return FilterCategory.AMOUNT
    
    # Search category - based on field properties and names
    search_patterns = ['search', 'name_search', 'reference_no', 'invoice_id']
    if any(pattern in field_name for pattern in search_patterns):
        return FilterCategory.SEARCH
    
    # If field is searchable but not explicitly a select field
    if getattr(field, 'searchable', False) and field_type == FieldType.TEXT:
        return FilterCategory.SEARCH
    
    # Selection category - based on FieldType
    if field_type in [FieldType.SELECT, FieldType.MULTI_SELECT, FieldType.STATUS_BADGE]:
        return FilterCategory.SELECTION
    
    # Relationship category - based on FieldType and field names  
    if field_type in [FieldType.ENTITY_SEARCH, FieldType.MULTI_ENTITY_SEARCH, FieldType.UUID, FieldType.REFERENCE]:
        return FilterCategory.RELATIONSHIP
    
    relationship_patterns = ['_id', 'supplier_id', 'patient_id', 'branch_id']
    if any(pattern in field_name for pattern in relationship_patterns):
        return FilterCategory.RELATIONSHIP
    
    # Default fallback
    return FilterCategory.SEARCH

def get_filterable_fields_by_category(entity_config, category: FilterCategory) -> List[FieldDefinition]:
    """
    Get filterable fields for a specific category from existing entity configuration
    Works with your current SUPPLIER_PAYMENT_CONFIG structure
    """
    if not entity_config or not hasattr(entity_config, 'fields'):
        return []
    
    filterable_fields = [field for field in entity_config.fields if getattr(field, 'filterable', False)]
    return [field for field in filterable_fields if get_field_category_from_existing_field(field) == category]

# =============================================================================
# FIELD ENHANCEMENT - BACKWARD COMPATIBLE
# =============================================================================

def enhance_field_with_category_info(field: FieldDefinition) -> FieldDefinition:
    """
    Enhance existing FieldDefinition with category information
    Modifies field in-place, maintains backward compatibility
    """
    if not hasattr(field, 'filter_category'):
        field.filter_category = get_field_category_from_existing_field(field)
    
    if not hasattr(field, 'category_config'):
        category_config = FILTER_CATEGORY_CONFIG.get(field.filter_category)
        if category_config:
            field.category_config = category_config.default_behavior.copy()
        else:
            field.category_config = {}
    
    return field

def enhance_entity_config_with_categories(entity_config) -> None:
    """
    Enhance existing entity configuration with category support
    Modifies in-place, maintains all existing functionality
    """
    if hasattr(entity_config, 'fields'):
        for field in entity_config.fields:
            enhance_field_with_category_info(field)
    
    # Add category-specific configurations if not present
    if not hasattr(entity_config, 'category_configs'):
        entity_config.category_configs = {}
    
    # Add default filters if not present
    if not hasattr(entity_config, 'default_filters'):
        entity_config.default_filters = {}

# =============================================================================
# FILTER ORGANIZATION - WORKS WITH CURRENT REQUEST STRUCTURE
# =============================================================================

def organize_current_filters_by_category(filters: Dict[str, Any], entity_config) -> Dict[FilterCategory, Dict]:
    """
    Organize current filters (from request.args or form data) by category
    Works with your existing filter extraction logic
    """
    if not entity_config or not hasattr(entity_config, 'fields'):
        return {}
    
    # Enhance fields with category info if needed
    for field in entity_config.fields:
        enhance_field_with_category_info(field)
    
    categorized = {category: {} for category in FilterCategory}
    
    for filter_name, filter_value in filters.items():
        if filter_value is not None and filter_value != '':
            # Find matching field definition
            field_def = None
            for field in entity_config.fields:
                if field.name == filter_name:
                    field_def = field
                    break
                # Check filter aliases (like supplier_name_search -> supplier_name)
                if hasattr(field, 'filter_aliases') and filter_name in field.filter_aliases:
                    field_def = field
                    break
            
            if field_def:
                category = get_field_category_from_existing_field(field_def)
                categorized[category][filter_name] = filter_value
            else:
                # Fallback category detection for fields not in config
                category = _detect_category_from_name(filter_name)
                categorized[category][filter_name] = filter_value
    
    # Remove empty categories
    return {cat: filters for cat, filters in categorized.items() if filters}

def _detect_category_from_name(field_name: str) -> FilterCategory:
    """Fallback category detection for fields not in configuration"""
    field_lower = field_name.lower()
    
    if any(pattern in field_lower for pattern in ['date', 'start_', 'end_']):
        return FilterCategory.DATE
    elif any(pattern in field_lower for pattern in ['amount', 'min_', 'max_', 'price']):
        return FilterCategory.AMOUNT
    elif any(pattern in field_lower for pattern in ['search', 'name', 'reference', 'invoice']):
        return FilterCategory.SEARCH
    elif any(pattern in field_lower for pattern in ['status', 'method', 'type', 'category']):
        return FilterCategory.SELECTION
    elif any(pattern in field_lower for pattern in ['_id', 'supplier', 'patient', 'branch']):
        return FilterCategory.RELATIONSHIP
    else:
        return FilterCategory.SEARCH

# =============================================================================
# CATEGORY PROCESSING ORDER - FOR DATABASE QUERY BUILDING
# =============================================================================

def get_category_processing_order() -> List[FilterCategory]:
    """
    Order for processing categories in database queries
    Some categories may depend on others or have performance implications
    """
    return [
        FilterCategory.DATE,        # Process date filters first (often indexed)
        FilterCategory.SELECTION,   # Then simple equality filters (fast)
        FilterCategory.AMOUNT,      # Then range filters
        FilterCategory.RELATIONSHIP, # Then joins (may be expensive)
        FilterCategory.SEARCH       # Finally text searches (potentially slow)
    ]

# =============================================================================
# INTEGRATION HELPERS FOR EXISTING CODE
# =============================================================================

def get_date_fields_from_config(entity_config) -> List[FieldDefinition]:
    """Get date fields using existing configuration structure"""
    return get_filterable_fields_by_category(entity_config, FilterCategory.DATE)

def get_amount_fields_from_config(entity_config) -> List[FieldDefinition]:
    """Get amount fields using existing configuration structure"""
    return get_filterable_fields_by_category(entity_config, FilterCategory.AMOUNT)

def get_search_fields_from_config(entity_config) -> List[FieldDefinition]:
    """Get search fields using existing configuration structure"""
    return get_filterable_fields_by_category(entity_config, FilterCategory.SEARCH)

def get_selection_fields_from_config(entity_config) -> List[FieldDefinition]:
    """Get selection fields using existing configuration structure"""
    return get_filterable_fields_by_category(entity_config, FilterCategory.SELECTION)

def get_relationship_fields_from_config(entity_config) -> List[FieldDefinition]:
    """Get relationship fields using existing configuration structure"""
    return get_filterable_fields_by_category(entity_config, FilterCategory.RELATIONSHIP)

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_date_format(value: str) -> bool:
    """Validate date string format"""
    try:
        from datetime import datetime
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except:
        return False

def validate_positive_number(value: str) -> bool:
    """Validate positive number"""
    try:
        num = float(value)
        return num >= 0
    except:
        return False

def validate_min_search_length(value: str, min_length: int = 2) -> bool:
    """Validate minimum search length"""
    return len(value.strip()) >= min_length

# Validation registry
VALIDATION_FUNCTIONS = {
    'valid_date_format': validate_date_format,
    'positive_numbers': validate_positive_number,
    'min_length_2': lambda v: validate_min_search_length(v, 2),
    'safe_sql_chars': lambda v: "'" not in v and '"' not in v
}

# =============================================================================
# COMPATIBILITY LAYER FOR EXISTING CODE
# =============================================================================

def migrate_existing_supplier_payment_config():
    """
    Enhance existing SUPPLIER_PAYMENT_CONFIG with category support
    Call this to upgrade your current configuration
    """
    try:
        from app.config.entity_configurations import SUPPLIER_PAYMENT_CONFIG
        enhance_entity_config_with_categories(SUPPLIER_PAYMENT_CONFIG)
        return SUPPLIER_PAYMENT_CONFIG
    except ImportError:
        return None

# =============================================================================
# UI CATEGORY CONFIGURATION
# =============================================================================

CATEGORY_UI_CONFIG = {
    FilterCategory.DATE: {
        'display_name': 'Date Filters',
        'icon': 'calendar',
        'order': 1,
        'collapsible': True,
        'default_expanded': True
    },
    FilterCategory.SELECTION: {
        'display_name': 'Filter Options',
        'icon': 'filter',
        'order': 2,
        'collapsible': True,
        'default_expanded': True
    },
    FilterCategory.AMOUNT: {
        'display_name': 'Amount Range',
        'icon': 'dollar-sign',
        'order': 3,
        'collapsible': True,
        'default_expanded': False
    },
    FilterCategory.RELATIONSHIP: {
        'display_name': 'Related Records',
        'icon': 'link',
        'order': 4,
        'collapsible': True,
        'default_expanded': False
    },
    FilterCategory.SEARCH: {
        'display_name': 'Search',
        'icon': 'search',
        'order': 5,
        'collapsible': False,
        'default_expanded': True
    }
}