# app/engine/universal_cache_decorators.py
"""
Universal Cache Decorators for View-Level Cache Integration
Provides decorator-based caching that integrates with Universal Engine views
"""

import functools
import json
from typing import Optional, Dict, Any, List, Callable, Union
from flask import request, g, session, jsonify, current_app

from app.config.core_definitions import CacheDecoratorConfig
from app.engine.universal_cache_manager import get_universal_cache_manager
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

# =============================================================================
# MAIN CACHE DECORATORS
# =============================================================================

def universal_cache(entity_type: str, operation: str = None, 
                   config: CacheDecoratorConfig = None, **kwargs):
    """
    Universal cache decorator for view functions
    Automatically caches view results based on entity configuration
    
    Args:
        entity_type: The entity type being cached (e.g., 'suppliers')
        operation: Cache operation type ('list', 'view', 'search', etc.)
        config: Optional cache decorator configuration
        **kwargs: Additional configuration options
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **view_kwargs):
            try:
                # Determine operation if not specified
                determined_operation = operation or _determine_operation_from_request()
                
                # Get cache manager
                cache_manager = get_universal_cache_manager()
                
                # Generate cache parameters
                cache_params = _extract_cache_parameters(
                    entity_type=entity_type,
                    operation=determined_operation,
                    config=config,
                    view_kwargs=view_kwargs,
                    decorator_kwargs=kwargs
                )
                
                # Check if should use cache
                if not _should_use_cache(entity_type, determined_operation, config):
                    return func(*args, **view_kwargs)
                
                # Try to get cached result
                cached_result = cache_manager.get_cached_data(
                    entity_type=entity_type,
                    operation=determined_operation,
                    identifier=cache_params.get('identifier'),
                    params=cache_params.get('params'),
                    loader_func=func,
                    loader_args=args,
                    loader_kwargs=view_kwargs
                )
                
                return cached_result
                
            except Exception as e:
                logger.error(f"Cache decorator error for {entity_type}:{operation}: {e}")
                # Fall back to original function
                return func(*args, **view_kwargs)
        
        return wrapper
    return decorator

def cache_config(entity_type: str, operation: str = "list"):
    """
    Cache configuration decorator - caches Universal Engine configurations only
    Lightweight decorator for configuration caching
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                cache_manager = get_universal_cache_manager()
                
                if operation == "config":
                    # Cache entity configuration
                    config = cache_manager.get_entity_config(entity_type)
                    if config:
                        # Call function with cached config
                        return func(config, *args, **kwargs)
                
                # Fall back to original function
                return func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Config cache decorator error: {e}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def cache_list(entity_type: str, cache_by_filters: bool = True, 
               cache_by_search: bool = True, ttl_override: int = None):
    """
    Specialized decorator for list views
    Caches entity lists with filtering and search support
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                cache_manager = get_universal_cache_manager()
                
                # Extract list parameters
                params = {}
                if cache_by_filters:
                    params['filters'] = _extract_filters_from_request()
                if cache_by_search:
                    params['search_term'] = request.args.get('search', '')
                
                params['page'] = request.args.get('page', 1, type=int)
                params['limit'] = request.args.get('limit', 50, type=int)
                
                # Get cached data
                cached_data = cache_manager.get_cached_data(
                    entity_type=entity_type,
                    operation="list",
                    params=params,
                    loader_func=func,
                    loader_args=args,
                    loader_kwargs=kwargs
                )
                
                return cached_data
                
            except Exception as e:
                logger.error(f"List cache decorator error for {entity_type}: {e}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def cache_detail(entity_type: str, identifier_param: str = "id", 
                ttl_override: int = None):
    """
    Specialized decorator for detail/view pages
    Caches individual entity details
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                cache_manager = get_universal_cache_manager()
                
                # Get identifier from kwargs or args
                identifier = kwargs.get(identifier_param)
                if not identifier and args:
                    # Try to get from URL path
                    identifier = _extract_identifier_from_path(identifier_param)
                
                if identifier:
                    cached_data = cache_manager.get_cached_data(
                        entity_type=entity_type,
                        operation="view",
                        identifier=str(identifier),
                        loader_func=func,
                        loader_args=args,
                        loader_kwargs=kwargs
                    )
                    return cached_data
                
                # No identifier, call function directly
                return func(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Detail cache decorator error for {entity_type}: {e}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def cache_search(entity_type: str, search_param: str = "search",
                cache_by_filters: bool = True):
    """
    Specialized decorator for search operations
    Caches search results with optional filtering
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                cache_manager = get_universal_cache_manager()
                
                # Extract search parameters
                search_term = request.args.get(search_param, '')
                if not search_term:
                    # No search term, don't cache
                    return func(*args, **kwargs)
                
                params = {'search_term': search_term}
                if cache_by_filters:
                    params['filters'] = _extract_filters_from_request()
                
                cached_data = cache_manager.get_cached_data(
                    entity_type=entity_type,
                    operation="search",
                    params=params,
                    loader_func=func,
                    loader_args=args,
                    loader_kwargs=kwargs
                )
                
                return cached_data
                
            except Exception as e:
                logger.error(f"Search cache decorator error for {entity_type}: {e}")
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

def cache_invalidate(entity_type: str, on_methods: List[str] = None, 
                    identifier_from: str = None):
    """
    Cache invalidation decorator
    Automatically invalidates cache when data is modified
    """
    if on_methods is None:
        on_methods = ['POST', 'PUT', 'DELETE', 'PATCH']
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the function first
            result = func(*args, **kwargs)
            
            # Invalidate cache if method matches
            if request.method in on_methods:
                try:
                    cache_manager = get_universal_cache_manager()
                    
                    # Get identifier if specified
                    identifier = None
                    if identifier_from:
                        identifier = kwargs.get(identifier_from) or request.view_args.get(identifier_from)
                    
                    # Invalidate cache
                    cache_manager.invalidate_entity(
                        entity_type=entity_type,
                        identifier=identifier,
                        hospital_id=getattr(g, 'hospital_id', None)
                    )
                    
                    logger.debug(f"Cache invalidated for {entity_type} after {request.method}")
                    
                except Exception as e:
                    logger.error(f"Cache invalidation error: {e}")
            
            return result
        
        return wrapper
    return decorator

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _determine_operation_from_request() -> str:
    """Determine cache operation from request context"""
    if request.method == 'GET':
        if request.endpoint and 'list' in request.endpoint:
            return "list"
        elif request.endpoint and ('detail' in request.endpoint or 'view' in request.endpoint):
            return "view"
        elif request.args.get('search'):
            return "search"
        else:
            return "list"  # Default for GET requests
    else:
        return "modify"  # Non-GET operations

def _extract_cache_parameters(entity_type: str, operation: str, 
                            config: CacheDecoratorConfig = None,
                            view_kwargs: Dict[str, Any] = None,
                            decorator_kwargs: Dict[str, Any] = None) -> Dict[str, Any]:
    """Extract parameters for cache key generation"""
    params = {}
    
    # Include request parameters if configured
    if not config or config.include_request_params:
        params.update(dict(request.args))
    
    # Include hospital context if configured
    if not config or config.include_hospital_context:
        params['hospital_id'] = getattr(g, 'hospital_id', None)
        params['branch_id'] = getattr(g, 'branch_id', None)
    
    # Include user context if configured
    if not config or config.include_user_context:
        params['user_id'] = getattr(g, 'user_id', None)
    
    # Include permissions if configured
    if config and config.vary_by_permissions:
        params['permissions'] = _get_user_permissions_hash()
    
    # Get identifier from view kwargs
    identifier = None
    if view_kwargs:
        identifier = (view_kwargs.get('id') or 
                     view_kwargs.get('item_id') or 
                     view_kwargs.get('entity_id'))
    
    return {
        'params': params,
        'identifier': identifier
    }

def _should_use_cache(entity_type: str, operation: str, 
                     config: CacheDecoratorConfig = None) -> bool:
    """Determine if cache should be used for this request"""
    
    # Don't cache non-GET requests unless specifically configured
    if request.method != 'GET':
        return False
    
    # Check cache condition if provided
    if config and config.cache_condition:
        try:
            return config.cache_condition()
        except Exception as e:
            logger.warning(f"Cache condition check failed: {e}")
            return False
    
    # Default: cache GET requests
    return True

def _extract_filters_from_request() -> Dict[str, Any]:
    """Extract filter parameters from request"""
    filters = {}
    
    # Common filter parameters
    filter_params = [
        'status', 'category', 'type', 'active', 'branch_id', 
        'created_after', 'created_before', 'updated_after', 'updated_before'
    ]
    
    for param in filter_params:
        value = request.args.get(param)
        if value:
            filters[param] = value
    
    return filters

def _extract_identifier_from_path(identifier_param: str) -> Optional[str]:
    """Extract identifier from URL path"""
    if request.view_args:
        return request.view_args.get(identifier_param)
    return None

def _get_user_permissions_hash() -> str:
    """Generate hash of user permissions for cache key"""
    try:
        # Get user permissions (integrate with your permission system)
        user_id = getattr(g, 'user_id', None)
        if user_id:
            # TODO: Integrate with your permission system
            # permissions = get_user_permissions(user_id)
            # return hashlib.md5(json.dumps(permissions, sort_keys=True).encode()).hexdigest()[:8]
            return str(user_id)  # Simplified for now
        return "anonymous"
    except Exception:
        return "unknown"

# =============================================================================
# COMPOSITE DECORATORS
# =============================================================================

def universal_entity_cache(entity_type: str, **kwargs):
    """
    Composite decorator that applies appropriate caching based on request
    Automatically determines operation type and applies optimal caching strategy
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **view_kwargs):
            operation = _determine_operation_from_request()
            
            # Apply appropriate specialized decorator based on operation
            if operation == "list":
                return cache_list(entity_type, **kwargs)(func)(*args, **view_kwargs)
            elif operation == "view":
                return cache_detail(entity_type, **kwargs)(func)(*args, **view_kwargs)
            elif operation == "search":
                return cache_search(entity_type, **kwargs)(func)(*args, **view_kwargs)
            else:
                # Use general universal cache
                return universal_cache(entity_type, operation, **kwargs)(func)(*args, **view_kwargs)
        
        return wrapper
    return decorator

def universal_crud_cache(entity_type: str, **kwargs):
    """
    CRUD-aware decorator that caches reads and invalidates on writes
    Perfect for Universal Engine CRUD views
    """
    def decorator(func):
        # Apply both caching and invalidation
        cached_func = universal_entity_cache(entity_type, **kwargs)(func)
        invalidated_func = cache_invalidate(entity_type, **kwargs)(cached_func)
        return invalidated_func
    
    return decorator

# =============================================================================
# INTEGRATION WITH UNIVERSAL ENGINE VIEWS
# =============================================================================

def enhance_universal_view_with_cache(entity_type: str):
    """
    Helper function to enhance existing Universal Engine views with caching
    Can be used to wrap existing view functions
    """
    def decorator(func):
        return universal_crud_cache(entity_type)(func)
    return decorator

# Example usage for Universal Engine views:
"""
from app.engine.universal_cache_decorators import (
    universal_cache, cache_list, cache_detail, universal_crud_cache
)

# Method 1: Apply to specific operations
@cache_list('suppliers')
def universal_list_view(entity_type):
    # Your existing Universal Engine list view
    pass

@cache_detail('suppliers')
def universal_detail_view(entity_type, item_id):
    # Your existing Universal Engine detail view
    pass

# Method 2: Apply CRUD-aware caching
@universal_crud_cache('suppliers')
def supplier_crud_view():
    # Handles caching for reads, invalidation for writes
    pass

# Method 3: Apply to all Universal Engine views
@universal_entity_cache('suppliers')
def universal_view(entity_type):
    # Automatically determines operation and applies appropriate caching
    pass
"""