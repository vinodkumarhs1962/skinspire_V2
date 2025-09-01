# =============================================================================
# FIXED: Universal Service Cache - Properly Handles Filters
# File: app/engine/universal_service_cache.py (DIRECT REPLACEMENT)
# =============================================================================

"""
Service-Level Cache System - PRIMARY CACHING LAYER
✅ FIXED: Properly handles filter parameters from request.args
✅ ENHANCED: Better cache key generation for filter scenarios  
✅ ENHANCED: Support for standalone functions
✅ DEBUG: Comprehensive logging for filter cache debugging

ISSUE FIXED: 
- Cache now properly captures filter parameters from Flask request.args
- Different filter combinations create different cache keys
- Initial load (no filters) vs filtered results are cached separately
"""

import hashlib
import json
import time
import pickle
import threading
import inspect
from typing import Dict, Any, List, Optional, Callable, Union, Set
from datetime import datetime, timedelta
from collections import OrderedDict
from functools import wraps
from flask import g, current_app, request
from flask_login import current_user

from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

# =============================================================================
# SERVICE CACHE ENTRY CLASS (UNCHANGED)
# =============================================================================

class ServiceCacheEntry:
    """Service-level cache entry with metadata and access tracking"""
    
    def __init__(self, data: Any, entity_type: str, operation: str, 
                 cache_key: str, ttl_seconds: int = 3600):
        self.data = data
        self.entity_type = entity_type
        self.operation = operation
        self.cache_key = cache_key
        self.created_at = time.time()
        self.accessed_at = time.time()
        self.access_count = 1
        self.ttl_seconds = ttl_seconds
        self.size_bytes = len(str(data))
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return (time.time() - self.created_at) > self.ttl_seconds
    
    def get_age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return time.time() - self.created_at
    
    def access(self):
        """Record access to this cache entry"""
        self.accessed_at = time.time()
        self.access_count += 1

class ServiceCacheStatistics:
    """Service cache statistics tracking"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.invalidations = 0
        self.start_time = time.time()
        self.entity_stats = {}
        self.total_response_time = 0.0
    
    def record_hit(self, entity_type: str, response_time: float = 0):
        """Record cache hit"""
        self.hits += 1
        self.total_response_time += response_time
        if entity_type not in self.entity_stats:
            self.entity_stats[entity_type] = {'hits': 0, 'misses': 0}
        self.entity_stats[entity_type]['hits'] += 1
    
    def record_miss(self, entity_type: str):
        """Record cache miss"""
        self.misses += 1
        if entity_type not in self.entity_stats:
            self.entity_stats[entity_type] = {'hits': 0, 'misses': 0}
        self.entity_stats[entity_type]['misses'] += 1
    
    def get_hit_ratio(self) -> float:
        """Calculate hit ratio"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def get_avg_response_time(self) -> float:
        """Calculate average response time"""
        return self.total_response_time / self.hits if self.hits > 0 else 0.0

# =============================================================================
# ✅ ENHANCED UNIVERSAL SERVICE CACHE - FIXED FILTER HANDLING
# =============================================================================

class UniversalServiceCache:
    """
    Universal Service Cache with FIXED filter handling
    ✅ FIXED: Properly captures filters from request.args
    ✅ ENHANCED: Support for both class methods and standalone functions
    """
    
    def __init__(self, max_memory_mb: int = 500, max_entries: int = 10000):
        self.cache_store = OrderedDict()  # LRU cache
        self.statistics = ServiceCacheStatistics()
        self._lock = threading.Lock()
        
        # Memory management
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_usage = 0
        self.max_entries = max_entries
        
        # TTL configuration by entity type
        self.default_ttl = {
            'master_entities': 3600,      # 1 hour for masters (suppliers, etc.)
            'transaction_entities': 1800, # 30 minutes for transactions
            'configuration_entities': 7200, # 2 hours for configurations
            'filter_data': 1800,          # 30 minutes for filter results
            'default': 1800
        }
        
        # Entity dependency mapping for cascade invalidation
        self.dependency_map = {
            'suppliers': ['supplier_payments', 'supplier_invoices', 'purchase_orders'],
            'patients': ['patient_appointments', 'prescriptions', 'patient_billing'],
            'medicines': ['prescriptions', 'inventory', 'purchase_orders'],
            'users': ['audit_logs', 'user_sessions']
        }
        
        # Start background cleanup
        self._start_cleanup_timer()
        
        logger.info("✅ Universal Service Cache initialized with FIXED filter handling")
    
    def _generate_cache_key(self, entity_type: str, operation: str, 
                       service_params: Dict[str, Any]) -> str:
        """
        ✅ FIXED: Generate cache key using actual entity_type parameter
        FIXES: Uses the entity_type passed to the method, not from service class
        """
        # ✅ CRITICAL: Start with the ACTUAL entity type passed to this method
        key_components = {
            'entity_type': entity_type,  # This is the actual entity being processed
            'operation': operation
        }
        
        # ✅ ADDITIONAL SAFETY: Use actual_entity_type if provided
        if 'actual_entity_type' in service_params:
            key_components['actual_entity_type'] = service_params['actual_entity_type']
        
        # ✅ URL CONTEXT: Add URL path for extra distinction
        try:
            if request and hasattr(request, 'path'):
                request_path = request.path
                key_components['request_path'] = request_path
                
                # Extract URL entity for verification
                if '/universal/' in request_path:
                    path_parts = request_path.split('/')
                    if len(path_parts) >= 3:
                        url_entity = path_parts[2]
                        key_components['url_entity'] = url_entity
                        
                        # ✅ VERIFICATION: Log if URL entity differs from parameter entity
                        if url_entity != entity_type:
                            logger.debug(f"🔍 Entity mismatch: URL={url_entity}, Parameter={entity_type}")
                
        except Exception as e:
            logger.debug(f"Could not extract URL context: {str(e)}")
        
        # ✅ ENHANCED: Capture filters from multiple sources
        self._capture_all_filter_parameters(service_params)
        
        # Add all parameters that affect query results
        cache_relevant_params = [
            'filters', 'hospital_id', 'branch_id', 'user_id', 
            'page', 'per_page', 'sort_by', 'sort_order',
            'search_params', 'current_user_id',
            'entity_type_param', 'request_args', 'filter_state',
            'search_term', 'date_range', 'status_filter',
            'url_entity', 'request_path', 'actual_entity_type'
        ]
        
        for param in cache_relevant_params:
            if param in service_params and service_params[param] is not None:
                value = service_params[param]
                if isinstance(value, dict):
                    if value:  # Only include non-empty dicts
                        # Remove None values and empty strings before hashing
                        cleaned_dict = {k: v for k, v in value.items() 
                                    if v is not None and v != '' and v != []}
                        if cleaned_dict:
                            key_components[param] = json.dumps(cleaned_dict, sort_keys=True, default=str)
                elif isinstance(value, (list, tuple)):
                    if value:  # Only include non-empty lists
                        key_components[param] = json.dumps(list(value), sort_keys=True, default=str)
                else:
                    key_components[param] = str(value)
        
        # ✅ ADDITIONAL CONTEXT: Include request args with entity context
        try:
            if request and hasattr(request, 'args') and request.args:
                request_dict = request.args.to_dict()
                if request_dict:
                    key_components['_request_args'] = json.dumps(request_dict, sort_keys=True)
        except:
            pass
            
        # Generate final cache key
        key_string = json.dumps(key_components, sort_keys=True)
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        # ✅ ENHANCED: Debug logging with actual entity info
        try:
            logger.debug(f"🔑 CACHE KEY GENERATED")
            logger.debug(f"   Passed Entity Type: {entity_type}")
            logger.debug(f"   Actual Entity Type: {service_params.get('actual_entity_type', 'None')}")
            logger.debug(f"   URL Entity: {key_components.get('url_entity', 'None')}")
            logger.debug(f"   Request Path: {key_components.get('request_path', 'None')}")
            logger.debug(f"   Operation: {operation}")
            logger.debug(f"   Filters: {service_params.get('filters', 'None')}")
            logger.debug(f"   Final Cache Key: {cache_key}")
        except:
            pass
        
        return cache_key
    
    def _capture_all_filter_parameters(self, service_params: Dict[str, Any]):
        """
        ✅ ENHANCED: Capture filter parameters with entity context
        FIXES: Ensures entity-specific filter capture
        """
        try:
            # ✅ CRITICAL FIX: Capture filters from Flask request.args
            if request and hasattr(request, 'args'):
                request_args = request.args.to_dict()
                if request_args:
                    # Store request args separately for cache key
                    service_params['request_args'] = request_args
                    
                    # ✅ MERGE: If filters param exists, merge with request args
                    existing_filters = service_params.get('filters', {})
                    if isinstance(existing_filters, dict):
                        # Merge request args into filters for comprehensive caching
                        merged_filters = {**existing_filters, **request_args}
                        service_params['filters'] = merged_filters
                    elif not existing_filters:
                        # If no filters provided, use request args as filters
                        service_params['filters'] = request_args
                    
                    logger.debug(f"🔍 FILTER CAPTURE: Request args captured: {request_args}")
            
            # ✅ ENHANCED: Capture URL-specific context
            if request and hasattr(request, 'path'):
                request_path = request.path
                service_params['request_path'] = request_path
                
                # Extract entity from URL path for better cache key distinction
                if '/universal/' in request_path:
                    path_parts = request_path.split('/')
                    if len(path_parts) >= 3:
                        url_entity = path_parts[2]
                        service_params['url_entity'] = url_entity
                        logger.debug(f"🔗 URL Entity captured: {url_entity} from path: {request_path}")
            
            # ✅ ADDITIONAL: Capture other filter-related parameters
            if current_user and hasattr(current_user, 'hospital_id'):
                service_params['hospital_id'] = str(current_user.hospital_id)
            
            # ✅ CAPTURE: Additional context that affects filtering
            if hasattr(request, 'form') and request.form:
                form_data = request.form.to_dict()
                if form_data:
                    service_params['form_data'] = form_data
                    
        except Exception as e:
            logger.warning(f"⚠️ Error capturing filter parameters: {str(e)}")
            # Don't let filter capture errors break caching
            pass
    
    def _get_ttl_for_entity(self, entity_type: str) -> int:
        """Get TTL seconds for entity type"""
        if entity_type in ['suppliers', 'medicines', 'users', 'departments']:
            return self.default_ttl['master_entities']
        elif entity_type in ['supplier_payments', 'patient_appointments', 'prescriptions']:
            return self.default_ttl['transaction_entities'] 
        elif entity_type in ['configurations', 'settings']:
            return self.default_ttl['configuration_entities']
        elif entity_type in ['filters', 'filter_data']:
            return self.default_ttl['filter_data']
        else:
            return self.default_ttl['default']
    
    def get_cached_service_result(self, entity_type: str, operation: str,
                                 service_params: Dict[str, Any],
                                 loader_func: Callable = None) -> Any:
        """
        ✅ ENHANCED: Get cached service result with FIXED filter handling
        """
        start_time = time.time()
        
        # Generate cache key (now properly captures filters)
        cache_key = self._generate_cache_key(entity_type, operation, service_params)
        
        # Try to get from cache
        with self._lock:
            entry = self.cache_store.get(cache_key)
            
            if entry and not entry.is_expired():
                # Cache hit
                entry.access()
                data = entry.data
                response_time = time.time() - start_time
                self.statistics.record_hit(entity_type, response_time)
                
                # Move to end for LRU
                self.cache_store.move_to_end(cache_key)
                
                # ✅ ENHANCED: Better logging for filter scenarios
                filter_info = service_params.get('filters', {})
                filter_count = len(filter_info) if isinstance(filter_info, dict) else 0
                logger.info(f"🚀 SERVICE CACHE HIT: {entity_type}.{operation} "
                           f"({response_time*1000:.1f}ms, {filter_count} filters, "
                           f"age: {entry.get_age_seconds():.0f}s)")
                return data
            
            elif entry:
                # Remove expired entry
                self._remove_cache_entry(cache_key)
        
        # Cache miss - execute loader function
        self.statistics.record_miss(entity_type)
        
        if not loader_func:
            logger.debug(f"SERVICE CACHE MISS: No loader function for {entity_type}.{operation}")
            return None
        
        # Execute loader function and cache result
        try:
            fresh_data = loader_func()
            
            # Cache the result
            ttl = self._get_ttl_for_entity(entity_type)
            self._set_cache_entry(
                cache_key=cache_key,
                data=fresh_data,
                entity_type=entity_type,
                operation=operation,
                ttl_seconds=ttl
            )
            
            response_time = time.time() - start_time
            filter_info = service_params.get('filters', {})
            filter_count = len(filter_info) if isinstance(filter_info, dict) else 0
            logger.info(f"🔥 SERVICE CACHE MISS: {entity_type}.{operation} loaded and cached "
                       f"({response_time*1000:.1f}ms, {filter_count} filters)")
            
            return fresh_data
            
        except Exception as e:
            logger.error(f"Error executing loader function: {str(e)}")
            raise
    
    def _set_cache_entry(self, cache_key: str, data: Any, entity_type: str,
                        operation: str, ttl_seconds: int):
        """Set cache entry with memory management"""
        with self._lock:
            # Calculate entry size
            entry_size = len(str(data))
            
            # Check if we need to evict entries
            if (len(self.cache_store) >= self.max_entries or 
                (self.current_memory_usage + entry_size) > self.max_memory_bytes):
                self._evict_lru_entries(entry_size)
            
            # Create new entry
            entry = ServiceCacheEntry(data, entity_type, operation, cache_key, ttl_seconds)
            self.cache_store[cache_key] = entry
            self.current_memory_usage += entry_size
            
            # Move to end (most recently used)
            self.cache_store.move_to_end(cache_key)
    
    def _evict_lru_entries(self, needed_bytes: int):
        """Evict least recently used entries"""
        evicted_count = 0
        
        while (len(self.cache_store) > 0 and 
               (len(self.cache_store) >= self.max_entries or 
                self.current_memory_usage + needed_bytes > self.max_memory_bytes)):
            
            # Remove least recently used (first item)
            lru_key, lru_entry = self.cache_store.popitem(last=False)
            self.current_memory_usage -= lru_entry.size_bytes
            evicted_count += 1
            
            if evicted_count >= 100:  # Prevent infinite loop
                break
        
        if evicted_count > 0:
            self.statistics.evictions += evicted_count
            logger.debug(f"🗑️ Evicted {evicted_count} LRU cache entries")
    
    def _remove_cache_entry(self, cache_key: str):
        """Remove cache entry and update memory usage"""
        if cache_key in self.cache_store:
            entry = self.cache_store.pop(cache_key)
            self.current_memory_usage -= entry.size_bytes
    
    def invalidate_entity_cache(self, entity_type: str, cascade: bool = False) -> int:
        """
        Invalidate cache entries for specific entity type
        Returns number of entries invalidated
        """
        invalidated_count = 0
        
        with self._lock:
            keys_to_remove = []
            
            # Find entries to invalidate
            for key, entry in self.cache_store.items():
                if entry.entity_type == entity_type:
                    keys_to_remove.append(key)
            
            # Remove found entries
            for key in keys_to_remove:
                self._remove_cache_entry(key)
                invalidated_count += 1
            
            # Cascade invalidation if requested
            if cascade and entity_type in self.dependency_map:
                for dependent_entity in self.dependency_map[entity_type]:
                    cascade_count = self.invalidate_entity_cache(dependent_entity, False)
                    invalidated_count += cascade_count
                    logger.debug(f"↳ Cascade invalidated: {dependent_entity} ({cascade_count} entries)")
        
        if invalidated_count > 0:
            self.statistics.invalidations += invalidated_count
            logger.info(f"🗑️ Invalidated {invalidated_count} service cache entries for {entity_type}")
        
        return invalidated_count
    
    def clear_all_service_cache(self):
        """Clear all service cache entries"""
        with self._lock:
            entry_count = len(self.cache_store)
            self.cache_store.clear()
            self.current_memory_usage = 0
            logger.info(f"🧹 Cleared all service cache entries ({entry_count} removed)")
    
    def _start_cleanup_timer(self):
        """Start background cleanup of expired entries"""
        def cleanup():
            expired_keys = []
            
            with self._lock:
                for key, entry in list(self.cache_store.items()):
                    if entry.is_expired():
                        expired_keys.append(key)
            
            # Remove expired entries
            for key in expired_keys:
                with self._lock:
                    self._remove_cache_entry(key)
            
            if expired_keys:
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired service cache entries")
            
            # Schedule next cleanup in 5 minutes
            timer = threading.Timer(300.0, cleanup)
            timer.daemon = True
            timer.start()
        
        # Start initial cleanup
        timer = threading.Timer(60.0, cleanup)  # First cleanup after 1 minute
        timer.daemon = True
        timer.start()
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        uptime = time.time() - self.statistics.start_time
        
        # Calculate entity-specific hit ratios
        entity_stats_enhanced = {}
        for entity_type, stats in self.statistics.entity_stats.items():
            total = stats['hits'] + stats['misses']
            hit_ratio = stats['hits'] / total if total > 0 else 0.0
            entity_stats_enhanced[entity_type] = {
                'hits': stats['hits'],
                'misses': stats['misses'],
                'hit_ratio': hit_ratio,
                'total_requests': total
            }
        
        return {
            'hit_ratio': self.statistics.get_hit_ratio(),
            'total_hits': self.statistics.hits,
            'total_misses': self.statistics.misses,
            'total_evictions': self.statistics.evictions,
            'total_invalidations': self.statistics.invalidations,
            'total_entries': len(self.cache_store),
            'memory_usage_mb': self.current_memory_usage / (1024 * 1024),
            'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
            'avg_response_time_ms': self.statistics.get_avg_response_time() * 1000,
            'uptime_hours': uptime / 3600,
            'entity_stats': entity_stats_enhanced,
            'requests_per_minute': (self.statistics.hits + self.statistics.misses) / (uptime / 60) if uptime > 0 else 0
        }

# =============================================================================
# ✅ ENHANCED SERVICE CACHING DECORATORS
# =============================================================================

def cache_service_method(entity_type: str = None, operation: str = None):
    """
    ✅ FIXED: Cache decorator that uses actual method parameters for entity type
    FIXES: Uses entity_type from method parameters, not service class property
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                # ✅ CRITICAL FIX: Get entity type from method parameters first
                determined_entity_type = None
                
                # Method 1: If entity_type is the first parameter (most common)
                if args and len(args) > 0 and isinstance(args[0], str):
                    # Check if first arg looks like an entity type
                    potential_entity = args[0]
                    if potential_entity and '_' in potential_entity or potential_entity in ['suppliers', 'patients', 'medicines', 'users']:
                        determined_entity_type = potential_entity
                        logger.debug(f"📋 Entity type from args[0]: {determined_entity_type}")
                
                # Method 2: From kwargs
                if not determined_entity_type and 'entity_type' in kwargs:
                    determined_entity_type = kwargs['entity_type']
                    logger.debug(f"📋 Entity type from kwargs: {determined_entity_type}")
                
                # Method 3: From decorator parameter (fallback)
                if not determined_entity_type and entity_type:
                    determined_entity_type = entity_type
                    logger.debug(f"📋 Entity type from decorator: {determined_entity_type}")
                
                # Method 4: From service instance (last resort)
                if not determined_entity_type and hasattr(self, 'entity_type'):
                    determined_entity_type = self.entity_type
                    logger.debug(f"📋 Entity type from service: {determined_entity_type}")
                
                # If we still don't have entity type, execute without caching
                if not determined_entity_type:
                    logger.debug(f"❌ No entity type determined for {func.__name__}, executing directly")
                    return func(self, *args, **kwargs)
                
                # Determine operation
                determined_operation = operation or func.__name__
                
                # Get cache manager
                cache_manager = get_service_cache_manager()
                
                # ✅ ENHANCED: Prepare service parameters for cache key
                service_params = kwargs.copy()
                
                # ✅ CRITICAL: Include the actual entity type in cache parameters
                service_params['actual_entity_type'] = determined_entity_type
                
                if args:
                    # Map positional args to parameter names
                    if len(args) > 0:
                        # If first arg is entity_type, use it; otherwise it's probably filters
                        if isinstance(args[0], str) and args[0] == determined_entity_type:
                            # First arg is entity_type, second might be filters
                            if len(args) > 1:
                                service_params['filters'] = args[1]
                        else:
                            # First arg is probably filters
                            service_params['filters'] = args[0]
                
                # Create loader function
                def loader():
                    return func(self, *args, **kwargs)
                
                # Get cached result or execute loader
                return cache_manager.get_cached_service_result(
                    entity_type=determined_entity_type,  # ✅ Use actual entity type
                    operation=determined_operation,
                    service_params=service_params,
                    loader_func=loader
                )
                
            except Exception as e:
                # ✅ SAFETY NET: If ANYTHING goes wrong with caching, execute directly
                logger.error(f"Cache decorator error for {func.__name__}: {str(e)}")
                logger.info(f"🔄 Falling back to direct execution")
                return func(self, *args, **kwargs)
        
        return wrapper
    return decorator

def cache_service_method_bypass(entity_type: str = None, operation: str = None):
    """Temporary bypass - just pass through"""
    def decorator(func):
        return func  # Just return the original function, no caching
    return decorator

def cache_service_method_park(entity_type: str = None, operation: str = None):
    """
    ✅ ORIGINAL decorator with FIXED filter handling
    Now properly captures filters from request.args
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Determine entity type if not specified
            determined_entity_type = entity_type
            if not determined_entity_type:
                # Try to get from self or kwargs
                if hasattr(self, 'entity_type'):
                    determined_entity_type = self.entity_type
                elif 'entity_type' in kwargs:
                    determined_entity_type = kwargs['entity_type']
                else:
                    # Fall back to executing without cache
                    logger.debug(f"No entity type for caching, executing directly: {func.__name__}")
                    return func(self, *args, **kwargs)
            
            # Determine operation if not specified  
            determined_operation = operation or func.__name__
            
            # Get service cache manager
            cache_manager = get_service_cache_manager()
            
            # ✅ ENHANCED: Prepare service parameters for cache key
            service_params = kwargs.copy()
            if args:
                # Map positional args to parameter names (assuming first arg is filters)
                if len(args) > 0:
                    service_params['filters'] = args[0]
            
            # Create loader function
            def loader():
                return func(self, *args, **kwargs)
            
            # Get cached result or execute loader
            return cache_manager.get_cached_service_result(
                entity_type=determined_entity_type,
                operation=determined_operation,
                service_params=service_params,
                loader_func=loader
            )
        
        return wrapper
    return decorator

def cache_universal(entity_type: str = None, operation: str = None):
    """
    ✅ NEW: Enhanced decorator for both class methods AND standalone functions
    With FIXED filter handling
    """
    def decorator(func: Callable):
        # Smart detection of function type
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        is_class_method = len(params) > 0 and params[0] == 'self'
        
        if is_class_method:
            # Use existing fixed decorator for class methods
            return cache_service_method(entity_type, operation)(func)
        else:
            # Handle standalone functions
            @wraps(func)
            def standalone_wrapper(*args, **kwargs):
                try:
                    if not entity_type:
                        logger.debug(f"No entity type for standalone function {func.__name__}, executing directly")
                        return func(*args, **kwargs)
                    
                    determined_operation = operation or func.__name__
                    cache_manager = get_service_cache_manager()
                    
                    # ✅ ENHANCED: Build service parameters for standalone functions
                    sig = inspect.signature(func)
                    param_names = list(sig.parameters.keys())
                    
                    service_params = kwargs.copy()
                    for i, arg_value in enumerate(args):
                        if i < len(param_names):
                            service_params[param_names[i]] = arg_value
                    
                    # Add context for standalone functions
                    if current_user and hasattr(current_user, 'hospital_id'):
                        service_params['_context_hospital_id'] = str(current_user.hospital_id)
                    
                    def loader():
                        return func(*args, **kwargs)
                    
                    return cache_manager.get_cached_service_result(
                        entity_type=entity_type,
                        operation=determined_operation,
                        service_params=service_params,
                        loader_func=loader
                    )
                    
                except Exception as e:
                    logger.error(f"Error in standalone function caching for {func.__name__}: {str(e)}")
                    return func(*args, **kwargs)
            
            return standalone_wrapper
    
    return decorator

# =============================================================================
# CACHE MANAGEMENT FUNCTIONS (UNCHANGED)
# =============================================================================

_service_cache_manager = None
_cache_manager_lock = threading.Lock()

def get_service_cache_manager() -> UniversalServiceCache:
    """Get global service cache manager instance"""
    global _service_cache_manager
    
    if _service_cache_manager is None:
        with _cache_manager_lock:
            if _service_cache_manager is None:
                # Get configuration from Flask app
                max_memory = 500  # default
                max_entries = 10000  # default
                
                if current_app:
                    max_memory = current_app.config.get('SERVICE_CACHE_MAX_MEMORY_MB', 500)
                    max_entries = current_app.config.get('SERVICE_CACHE_MAX_ENTRIES', 10000)
                
                _service_cache_manager = UniversalServiceCache(max_memory, max_entries)
                logger.info("✅ Global Service Cache Manager initialized with FIXED filter handling")
    
    return _service_cache_manager

def invalidate_service_cache_for_entity(entity_type: str, cascade: bool = False) -> int:
    """Invalidate service cache for entity type"""
    cache_manager = get_service_cache_manager()
    return cache_manager.invalidate_entity_cache(entity_type, cascade)

def clear_all_service_cache():
    """Clear all service cache"""
    cache_manager = get_service_cache_manager()
    cache_manager.clear_all_service_cache()

def get_service_cache_statistics() -> Dict[str, Any]:
    """Get service cache statistics"""
    cache_manager = get_service_cache_manager()
    return cache_manager.get_cache_statistics()

# =============================================================================
# INITIALIZATION
# =============================================================================

def init_service_cache(app):
    """Initialize service cache with Flask app"""
    try:
        # Set cache configuration
        app.config.setdefault('SERVICE_CACHE_ENABLED', True)
        app.config.setdefault('SERVICE_CACHE_MAX_MEMORY_MB', 500)
        app.config.setdefault('SERVICE_CACHE_MAX_ENTRIES', 10000)
        app.config.setdefault('SERVICE_CACHE_DEFAULT_TTL', 1800)
        
        if app.config.get('SERVICE_CACHE_ENABLED'):
            # Initialize cache manager
            cache_manager = get_service_cache_manager()
            
            # Store in app for access
            app._service_cache_manager = cache_manager
            
            logger.info("✅ Service Cache initialized with FIXED filter handling")
            logger.info("   ✅ Filters from request.args properly captured")
            logger.info("   ✅ Different filter combinations cached separately")
            logger.info("   ✅ Support for both class methods and standalone functions")
            
        else:
            logger.info("⚠️ Service Cache disabled by configuration")
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize service cache: {str(e)}")
        app.config['SERVICE_CACHE_ENABLED'] = False

# =============================================================================
# 🐛 DEBUG UTILITIES FOR FILTER ISSUES
# =============================================================================

def debug_cache_key_for_request():
    """
    ✅ DEBUG UTILITY: Show what cache key would be generated for current request
    Use this to debug filter caching issues
    """
    if not request:
        return "No active request"
    
    try:
        # Simulate what the cache would capture
        service_params = {}
        if request.args:
            service_params['request_args'] = request.args.to_dict()
            service_params['filters'] = request.args.to_dict()
        
        if current_user and hasattr(current_user, 'hospital_id'):
            service_params['hospital_id'] = str(current_user.hospital_id)
        
        # Generate cache key
        cache_manager = get_service_cache_manager()
        cache_key = cache_manager._generate_cache_key('debug', 'test', service_params)
        
        debug_info = {
            'request_method': request.method,
            'request_args': request.args.to_dict() if request.args else {},
            'request_form': request.form.to_dict() if hasattr(request, 'form') and request.form else {},
            'captured_filters': service_params.get('filters', {}),
            'hospital_id': service_params.get('hospital_id', 'None'),
            'generated_cache_key': cache_key
        }
        
        return debug_info
        
    except Exception as e:
        return f"Debug error: {str(e)}"

logger.info("✅ Enhanced Universal Service Cache loaded with FIXED filter handling")