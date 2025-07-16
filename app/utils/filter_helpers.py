"""
Filter Helper Utilities
Template and view helper functions for filter management
"""

from app.engine.entity_config_manager import EntityConfigManager
from typing import Dict, Any, Optional, List, Protocol

def get_entity_filter_categories(entity_type: str):
    """Template helper: Get filter categories for entity"""
    return EntityConfigManager.get_filter_categories_for_entity(entity_type)

def organize_filters_for_template(request_filters: Dict, entity_type: str):
    """Template helper: Organize filters by category"""
    return EntityConfigManager.organize_request_filters_by_category(request_filters, entity_type)

def get_category_fields_for_entity(entity_type: str, category_name: str):
    """Template helper: Get fields for specific category"""
    from app.config.filter_categories import FilterCategory
    try:
        category = FilterCategory(category_name)
        return EntityConfigManager.get_filterable_fields_by_category_for_entity(entity_type, category)
    except ValueError:
        return []