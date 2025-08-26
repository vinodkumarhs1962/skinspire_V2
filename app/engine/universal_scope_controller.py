# app/engine/universal_scope_controller.py
"""
Improved Universal Scope Controller - Registry-Based
No hardcoding, uses central entity registry
"""

import importlib
from typing import Optional, Dict, Any
from flask import url_for

from app.config.entity_registry import (
    get_entity_registration, 
    is_master_entity,
    is_transaction_entity,
    get_custom_url,
    EntityCategory
)
from app.config.core_definitions import CRUDOperation
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalScopeController:
    """
    Registry-based scope controller - no hardcoding!
    Controls operation scope and routing for entities
    """
    
    def __init__(self):
        self.config_cache = {}
        self.module_cache = {}
    
    def _get_entity_config(self, entity_type: str):
        """Get entity configuration using registry"""
        if entity_type in self.config_cache:
            return self.config_cache[entity_type]
        
        try:
            # Get registration from registry
            registration = get_entity_registration(entity_type)
            if not registration:
                logger.error(f"Entity {entity_type} not registered")
                return None
            
            # Load configuration module dynamically
            module_path = registration.module
            if module_path not in self.module_cache:
                module = importlib.import_module(module_path)
                self.module_cache[module_path] = module
            else:
                module = self.module_cache[module_path]
            
            # Get entity config from module
            if hasattr(module, 'get_entity_config'):
                config = module.get_entity_config(entity_type)
            elif hasattr(module, f'{entity_type.upper()}_CONFIG'):
                config = getattr(module, f'{entity_type.upper()}_CONFIG')
            else:
                # Try to find config by iterating module attributes
                for attr_name in dir(module):
                    if attr_name.endswith('_CONFIG'):
                        attr = getattr(module, attr_name)
                        if hasattr(attr, 'entity_type') and attr.entity_type == entity_type:
                            config = attr
                            break
                else:
                    logger.error(f"No configuration found for {entity_type} in {module_path}")
                    return None
            
            # Inject category from registry if not set
            if config and not hasattr(config, 'entity_category'):
                config.entity_category = registration.category
            
            self.config_cache[entity_type] = config
            return config
            
        except Exception as e:
            logger.error(f"Failed to get config for {entity_type}: {e}")
            return None
    
    def validate_operation(self, entity_type: str, operation: CRUDOperation) -> bool:
        """
        Validate if an operation is allowed for an entity type
        Uses registry to determine entity category
        """
        # Check if entity is registered
        registration = get_entity_registration(entity_type)
        if not registration:
            logger.warning(f"Entity {entity_type} not registered")
            return False
        
        # Check if entity is enabled
        if not registration.enabled:
            logger.debug(f"Entity {entity_type} is disabled")
            return False
        
        # Get entity configuration
        config = self._get_entity_config(entity_type)
        if not config:
            return False
        
        # Check category-based restrictions
        if registration.category == EntityCategory.TRANSACTION:
            # Transaction entities only allow read operations
            if operation in [CRUDOperation.CREATE, CRUDOperation.UPDATE, CRUDOperation.DELETE]:
                logger.debug(f"Blocking {operation.value} for transaction entity {entity_type}")
                return False
        
        # Check if operation is explicitly allowed in config
        if hasattr(config, 'allowed_operations'):
            if operation not in config.allowed_operations:
                logger.debug(f"Operation {operation.value} not allowed for {entity_type}")
                return False
        
        # Check CRUD enablement for write operations
        if operation in [CRUDOperation.CREATE, CRUDOperation.UPDATE, CRUDOperation.DELETE]:
            if hasattr(config, 'universal_crud_enabled'):
                if not config.universal_crud_enabled:
                    logger.debug(f"Universal CRUD disabled for {entity_type}")
                    return False
        
        return True
    
    def get_operation_url(self, entity_type: str, operation: CRUDOperation, 
                         item_id: Optional[str] = None, **kwargs) -> str:
        """
        Get appropriate URL for an operation
        Uses registry for custom URLs
        """
        # Check if operation is allowed
        if not self.validate_operation(entity_type, operation):
            # Check for custom URLs from registry
            custom_url = get_custom_url(entity_type, operation.value.lower())
            if custom_url:
                if item_id and '{' in custom_url:
                    # Format with item_id
                    param_name = entity_type.rstrip('s') + '_id'
                    return custom_url.format(**{param_name: item_id, 'item_id': item_id})
                return custom_url
            return '#'  # Operation not allowed
        
        # Use universal routes for allowed operations
        try:
            if operation == CRUDOperation.LIST:
                return url_for('universal_views.universal_list_view', 
                             entity_type=entity_type, **kwargs)
            elif operation == CRUDOperation.VIEW and item_id:
                return url_for('universal_views.universal_detail_view', 
                             entity_type=entity_type, item_id=item_id, **kwargs)
            elif operation == CRUDOperation.CREATE:
                return url_for('universal_views.universal_create_view', 
                             entity_type=entity_type, **kwargs)
            elif operation == CRUDOperation.UPDATE and item_id:
                return url_for('universal_views.universal_edit_view', 
                             entity_type=entity_type, item_id=item_id, **kwargs)
            elif operation == CRUDOperation.DELETE and item_id:
                return url_for('universal_views.universal_delete_view', 
                             entity_type=entity_type, item_id=item_id, **kwargs)
            elif operation == CRUDOperation.DOCUMENT:
                return url_for('universal_views.universal_document_view', 
                             entity_type=entity_type, item_id=item_id, **kwargs)
            else:
                return '#'
        except Exception as e:
            logger.error(f"Error generating URL for {entity_type}/{operation.value}: {e}")
            return '#'
    
    def get_available_actions(self, entity_type: str, context: Dict[str, Any]) -> Dict[str, bool]:
        """Get available actions for an entity type"""
        registration = get_entity_registration(entity_type)
        if not registration:
            return {}
        
        # Base actions from category
        if registration.category == EntityCategory.MASTER:
            actions = {
                'can_create': True,
                'can_edit': True,
                'can_delete': True,
                'can_view': True,
                'can_list': True,
                'can_export': True,
            }
        elif registration.category == EntityCategory.TRANSACTION:
            actions = {
                'can_create': False,  # Use custom implementation
                'can_edit': False,    # Use custom implementation
                'can_delete': False,  # Usually not allowed
                'can_view': True,
                'can_list': True,
                'can_export': True,
            }
        else:
            actions = {
                'can_create': False,
                'can_edit': False,
                'can_delete': False,
                'can_view': True,
                'can_list': True,
                'can_export': False,
            }
        
        # Override with specific validations
        for op_name, crud_op in [
            ('can_create', CRUDOperation.CREATE),
            ('can_edit', CRUDOperation.UPDATE),
            ('can_delete', CRUDOperation.DELETE),
            ('can_view', CRUDOperation.VIEW),
            ('can_list', CRUDOperation.LIST),
        ]:
            actions[op_name] = actions[op_name] and self.validate_operation(entity_type, crud_op)
        
        # Add permission checks if provided
        config = self._get_entity_config(entity_type)
        if config and 'user_permissions' in context:
            permissions = context['user_permissions']
            if hasattr(config, 'create_permission') and config.create_permission:
                actions['can_create'] = actions['can_create'] and config.create_permission in permissions
            if hasattr(config, 'edit_permission') and config.edit_permission:
                actions['can_edit'] = actions['can_edit'] and config.edit_permission in permissions
            if hasattr(config, 'delete_permission') and config.delete_permission:
                actions['can_delete'] = actions['can_delete'] and config.delete_permission in permissions
        
        return actions
    
    def get_entity_category(self, entity_type: str) -> Optional[EntityCategory]:
        """Get entity category from registry"""
        registration = get_entity_registration(entity_type)
        return registration.category if registration else None
    
    def is_master_entity(self, entity_type: str) -> bool:
        """Check if entity is master using registry"""
        return is_master_entity(entity_type)
    
    def is_transaction_entity(self, entity_type: str) -> bool:
        """Check if entity is transaction using registry"""
        return is_transaction_entity(entity_type)

# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_scope_controller = None

def get_universal_scope_controller() -> UniversalScopeController:
    """Get singleton instance of Universal Scope Controller"""
    global _scope_controller
    if _scope_controller is None:
        _scope_controller = UniversalScopeController()
    return _scope_controller