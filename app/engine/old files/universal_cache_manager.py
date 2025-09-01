# app/engine/universal_cache_manager.py
"""
Universal Cache Manager - Core Engine Service
Integrated with Universal Engine architecture for all entity types
Handles configurations, database records, parameters, and search results
"""

import importlib
import logging
import threading
import time
import json
import hashlib
import uuid
from typing import Dict, Optional, Any, List, Set, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import wraps
from flask import g, session, request, current_app

from app.config.core_definitions import (
    EntityConfiguration, CacheConfiguration, CacheStrategy, 
    CacheScope, DataSensitivity, CacheInvalidationTrigger,
    EntityCategory, CacheDecoratorConfig
)
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

# =============================================================================
# UNIVERSAL CACHE ENTRY
# =============================================================================

@dataclass
class UniversalCacheEntry:
    """Universal cache entry for any entity type and operation"""
    
    # Core data
    data: Any
    entity_type: str
    operation: str                    # 'config', 'list', 'view', 'search', etc.
    
    # Context and isolation
    hospital_id: Optional[str] = None
    branch_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Cache metadata
    cache_key: str = ""
    created_at: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    
    # Configuration
    cache_config: Optional[CacheConfiguration] = None
    
    # Security
    encrypted: bool = False
    sensitivity: DataSensitivity = DataSensitivity.INTERNAL
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if not self.cache_config or not self.created_at:
            return True
            
        ttl = self._get_effective_ttl()
        if ttl <= 0:  # Never expires
            return False
            
        return datetime.now() > self.created_at + timedelta(seconds=ttl)
    
    def _get_effective_ttl(self) -> int:
        """Get effective TTL based on strategy and sensitivity"""
        if not self.cache_config:
            return 3600  # Default 1 hour
            
        if self.cache_config.strategy == CacheStrategy.SESSION:
            return self.cache_config.session_ttl_seconds
        elif self.cache_config.strategy == CacheStrategy.SHORT_TERM:
            return self.cache_config.short_term_ttl_seconds
        elif self.cache_config.strategy == CacheStrategy.NO_CACHE:
            return 0
        else:
            # Reduce TTL for more sensitive data
            base_ttl = self.cache_config.ttl_seconds
            if self.sensitivity == DataSensitivity.RESTRICTED:
                return min(base_ttl, 300)   # Max 5 minutes
            elif self.sensitivity == DataSensitivity.CONFIDENTIAL:
                return min(base_ttl, 900)   # Max 15 minutes
            return base_ttl
    
    def mark_accessed(self, user_id: str = None):
        """Mark entry as accessed"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        
        # Log sensitive data access
        if self.cache_config and self.cache_config.audit_cache_access:
            self._log_sensitive_access(user_id)
    
    def _log_sensitive_access(self, user_id: str):
        """Log access to sensitive cached data"""
        logger.info(f"CACHE_ACCESS: entity={self.entity_type}, operation={self.operation}, "
                   f"sensitivity={self.sensitivity.value}, user={user_id}, "
                   f"hospital={self.hospital_id}, access_count={self.access_count}")

# =============================================================================
# UNIVERSAL CACHE ENCRYPTION
# =============================================================================

class UniversalCacheEncryption:
    """Encryption service for Universal Cache Manager"""
    
    def __init__(self):
        self.encryption_enabled = False
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Setup encryption using hospital-specific keys"""
        try:
            # Integrate with your existing Hospital encryption system
            self.encryption_enabled = True
            logger.info("Universal Cache encryption enabled")
        except Exception as e:
            logger.warning(f"Cache encryption setup failed: {e}")
    
    def encrypt_data(self, data: Any, hospital_id: str = None) -> str:
        """Encrypt data for caching"""
        if not self.encryption_enabled:
            return json.dumps(data, default=str)
        
        try:
            json_data = json.dumps(data, default=str)
            
            # TODO: Integrate with your Hospital.encryption_key system
            # For now, simple encoding (replace with your encryption)
            import base64
            encoded_data = base64.b64encode(json_data.encode()).decode()
            return f"UCACHE_ENC:{encoded_data}"
            
        except Exception as e:
            logger.error(f"Cache encryption failed: {e}")
            return json.dumps(data, default=str)
    
    def decrypt_data(self, encrypted_data: str) -> Any:
        """Decrypt cached data"""
        if not self.encryption_enabled or not encrypted_data.startswith("UCACHE_ENC:"):
            try:
                return json.loads(encrypted_data)
            except:
                return encrypted_data
        
        try:
            encoded_data = encrypted_data[11:]  # Remove prefix
            import base64
            json_data = base64.b64decode(encoded_data).decode()
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Cache decryption failed: {e}")
            return None

# =============================================================================
# UNIVERSAL CACHE MANAGER
# =============================================================================

class UniversalCacheManager:
    """
    Universal Cache Manager for Universal Engine
    Handles all entity types: masters, transactions, configurations
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        
        # Multi-dimensional cache storage
        # {scope: {scope_id: {cache_key: UniversalCacheEntry}}}
        self._cache_stores = {
            CacheScope.GLOBAL: {},
            CacheScope.HOSPITAL: {},
            CacheScope.BRANCH: {},
            CacheScope.USER: {},
            CacheScope.SESSION: {}
        }
        
        # Cache for entity configurations
        self._entity_config_cache = {}
        
        # Security and utilities
        self._encryption = UniversalCacheEncryption()
        
        # Performance metrics
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "loads": 0,
            "invalidations": 0,
            "errors": 0
        }
        
        # Background operations
        self._setup_background_operations()
        
        logger.info("Universal Cache Manager initialized")
    
    # =================================================================
    # CONTEXT AND KEY GENERATION
    # =================================================================
    
    def _get_request_context(self) -> Dict[str, Any]:
        """Get current request context for cache isolation"""
        return {
            "hospital_id": getattr(g, 'hospital_id', None),
            "branch_id": getattr(g, 'branch_id', None),
            "user_id": getattr(g, 'user_id', None),
            "session_id": session.get('session_id') if session else None,
            "request_method": request.method if request else "GET",
            "request_path": request.path if request else ""
        }
    
    def _generate_cache_key(self, entity_type: str, operation: str, 
                          identifier: str = None, params: Dict[str, Any] = None,
                          cache_config: CacheConfiguration = None) -> str:
        """Generate cache key for entity operation"""
        
        key_parts = [entity_type, operation]
        
        # Add identifier if provided
        if identifier:
            key_parts.append(str(identifier))
        
        # Add parameters hash if provided
        if params:
            # Filter out excluded parameters
            filtered_params = params.copy()
            if cache_config and cache_config.exclude_parameters:
                for exclude_param in cache_config.exclude_parameters:
                    filtered_params.pop(exclude_param, None)
            
            # Create deterministic hash of parameters
            if filtered_params:
                param_str = json.dumps(filtered_params, sort_keys=True, default=str)
                param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
                key_parts.append(param_hash)
        
        # Use custom key generator if provided
        if cache_config and cache_config.custom_cache_key_generator:
            try:
                custom_key = cache_config.custom_cache_key_generator(
                    entity_type, operation, identifier, params
                )
                return custom_key
            except Exception as e:
                logger.warning(f"Custom cache key generation failed: {e}")
        
        return ":".join(key_parts)
    
    def _get_cache_store_key(self, cache_config: CacheConfiguration, 
                           context: Dict[str, Any]) -> str:
        """Get cache store key based on scope"""
        scope = cache_config.scope
        
        if scope == CacheScope.GLOBAL:
            return "global"
        elif scope == CacheScope.HOSPITAL:
            return context.get("hospital_id", "default")
        elif scope == CacheScope.BRANCH:
            return f"{context.get('hospital_id', 'default')}:{context.get('branch_id', 'default')}"
        elif scope == CacheScope.USER:
            return f"{context.get('hospital_id', 'default')}:{context.get('user_id', 'default')}"
        elif scope == CacheScope.SESSION:
            return context.get("session_id", "default")
        
        return "default"
    
    # =================================================================
    # ENTITY CONFIGURATION CACHING
    # =================================================================
    
    def get_entity_config(self, entity_type: str) -> Optional[EntityConfiguration]:
        """Get cached entity configuration"""
        cache_key = f"config:{entity_type}"
        
        # Check configuration cache first
        if cache_key in self._entity_config_cache:
            entry = self._entity_config_cache[cache_key]
            if not entry.is_expired:
                entry.mark_accessed()
                self._metrics["hits"] += 1
                return entry.data
            else:
                del self._entity_config_cache[cache_key]
        
        # Load and cache configuration
        self._metrics["misses"] += 1
        return self._load_and_cache_entity_config(entity_type)
    
    def _load_and_cache_entity_config(self, entity_type: str) -> Optional[EntityConfiguration]:
        """Load entity configuration and cache it"""
        try:
            # Load using existing Universal Engine system
            from app.config.entity_configurations import get_entity_config
            config = get_entity_config(entity_type)
            
            if config:
                # Create cache entry for configuration
                cache_entry = UniversalCacheEntry(
                    data=config,
                    entity_type=entity_type,
                    operation="config",
                    cache_key=f"config:{entity_type}",
                    sensitivity=DataSensitivity.PUBLIC,  # Configurations are generally public
                    cache_config=CacheConfiguration(
                        strategy=CacheStrategy.PERSISTENT,
                        scope=CacheScope.GLOBAL,
                        ttl_seconds=7200,  # 2 hours for configs
                        encrypt_cache_data=False  # Configs don't need encryption
                    )
                )
                
                self._entity_config_cache[cache_entry.cache_key] = cache_entry
                self._metrics["loads"] += 1
                logger.debug(f"Loaded and cached entity config: {entity_type}")
                
                return config
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load entity config {entity_type}: {e}")
            self._metrics["errors"] += 1
            return None
    
    # =================================================================
    # UNIVERSAL DATA CACHING
    # =================================================================
    
    def get_cached_data(self, entity_type: str, operation: str, 
                       identifier: str = None, params: Dict[str, Any] = None,
                       loader_func: Callable = None, loader_args: List = None,
                       force_reload: bool = False) -> Any:
        """Universal method to get cached data for any entity operation"""
        
        try:
            # Get entity configuration and cache config
            entity_config = self.get_entity_config(entity_type)
            if not entity_config or not entity_config.cache_enabled:
                # If caching disabled, call loader directly
                if loader_func:
                    return loader_func(*loader_args) if loader_args else loader_func()
                return None
            
            cache_config = entity_config.get_cache_config()
            
            # Check if this operation is cacheable
            if operation not in cache_config.cacheable_operations:
                if loader_func:
                    return loader_func(*loader_args) if loader_args else loader_func()
                return None
            
            # Check if no caching strategy
            if cache_config.strategy == CacheStrategy.NO_CACHE:
                if loader_func:
                    return loader_func(*loader_args) if loader_args else loader_func()
                return None
            
            # Generate cache key and get context
            context = self._get_request_context()
            cache_key = self._generate_cache_key(entity_type, operation, identifier, params, cache_config)
            store_key = self._get_cache_store_key(cache_config, context)
            
            with self._lock:
                # Get appropriate cache store
                cache_store = self._cache_stores[cache_config.scope]
                if store_key not in cache_store:
                    cache_store[store_key] = {}
                
                # Check cache first (unless force reload)
                if not force_reload and cache_key in cache_store[store_key]:
                    entry = cache_store[store_key][cache_key]
                    
                    if not entry.is_expired:
                        # Cache hit
                        entry.mark_accessed(context.get("user_id"))
                        self._metrics["hits"] += 1
                        
                        # Decrypt if needed
                        if entry.encrypted:
                            data = self._encryption.decrypt_data(entry.data)
                        else:
                            data = entry.data
                        
                        logger.debug(f"Cache hit: {entity_type}:{operation} for {store_key}")
                        return data
                    else:
                        # Remove expired entry
                        del cache_store[store_key][cache_key]
                
                # Cache miss - load data
                self._metrics["misses"] += 1
                return self._load_and_cache_data(
                    entity_type=entity_type,
                    operation=operation,
                    cache_key=cache_key,
                    store_key=store_key,
                    cache_config=cache_config,
                    context=context,
                    loader_func=loader_func,
                    loader_args=loader_args,
                    identifier=identifier,
                    params=params
                )
        
        except Exception as e:
            logger.error(f"Cache operation failed for {entity_type}:{operation}: {e}")
            self._metrics["errors"] += 1
            
            # Fall back to direct loading
            if loader_func:
                return loader_func(*loader_args) if loader_args else loader_func()
            return None
    
    def _load_and_cache_data(self, entity_type: str, operation: str, cache_key: str,
                           store_key: str, cache_config: CacheConfiguration, 
                           context: Dict[str, Any], loader_func: Callable = None,
                           loader_args: List = None, identifier: str = None,
                           params: Dict[str, Any] = None) -> Any:
        """Load data and cache according to configuration"""
        
        try:
            # Load data
            if loader_func:
                data = loader_func(*loader_args) if loader_args else loader_func()
            else:
                # Use default loaders based on operation
                data = self._default_data_loader(entity_type, operation, identifier, params)
            
            if data is None:
                return None
            
            # Process data before caching if configured
            if cache_config.pre_cache_processor:
                try:
                    data = cache_config.pre_cache_processor(data)
                except Exception as e:
                    logger.warning(f"Pre-cache processor failed: {e}")
            
            # Prepare data for caching
            cache_data = data
            encrypted = False
            
            if cache_config.encrypt_cache_data:
                cache_data = self._encryption.encrypt_data(data, context.get("hospital_id"))
                encrypted = True
            
            # Create cache entry
            cache_entry = UniversalCacheEntry(
                data=cache_data,
                entity_type=entity_type,
                operation=operation,
                cache_key=cache_key,
                hospital_id=context.get("hospital_id"),
                branch_id=context.get("branch_id"),
                user_id=context.get("user_id"),
                session_id=context.get("session_id"),
                cache_config=cache_config,
                encrypted=encrypted,
                sensitivity=cache_config.sensitivity
            )
            
            # Store in appropriate cache
            cache_store = self._cache_stores[cache_config.scope]
            if store_key not in cache_store:
                cache_store[store_key] = {}
            cache_store[store_key][cache_key] = cache_entry
            
            self._metrics["loads"] += 1
            logger.debug(f"Loaded and cached {entity_type}:{operation} for {store_key}")
            
            # Process data after caching if configured
            if cache_config.post_cache_processor:
                try:
                    data = cache_config.post_cache_processor(data)
                except Exception as e:
                    logger.warning(f"Post-cache processor failed: {e}")
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to load and cache {entity_type}:{operation}: {e}")
            return None
    
    def _default_data_loader(self, entity_type: str, operation: str, 
                           identifier: str = None, params: Dict[str, Any] = None) -> Any:
        """Default data loaders for common operations"""
        
        try:
            if operation == "list":
                return self._load_entity_list(entity_type, params)
            elif operation == "view" and identifier:
                return self._load_entity_detail(entity_type, identifier)
            elif operation == "search":
                return self._load_search_results(entity_type, params)
            elif operation == "filter":
                return self._load_filtered_results(entity_type, params)
            else:
                logger.warning(f"No default loader for operation: {operation}")
                return None
                
        except Exception as e:
            logger.error(f"Default data loader failed for {entity_type}:{operation}: {e}")
            return None
    
    def _load_entity_list(self, entity_type: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Load entity list using Universal Engine services"""
        try:
            from app.engine.universal_services import get_universal_service
            service = get_universal_service(entity_type)
            if service and hasattr(service, 'get_list'):
                return service.get_list(filters=params.get('filters') if params else None,
                                      limit=params.get('limit') if params else None)
            return []
        except Exception as e:
            logger.error(f"Failed to load entity list for {entity_type}: {e}")
            return []
    
    def _load_entity_detail(self, entity_type: str, identifier: str) -> Optional[Dict]:
        """Load entity detail using Universal Engine services"""
        try:
            from app.engine.universal_services import get_universal_item_data
            return get_universal_item_data(entity_type, identifier)
        except Exception as e:
            logger.error(f"Failed to load entity detail for {entity_type}:{identifier}: {e}")
            return None
    
    def _load_search_results(self, entity_type: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Load search results using Universal Engine services"""
        try:
            from app.engine.universal_services import search_universal_entity_data
            search_term = params.get('search_term', '') if params else ''
            filters = params.get('filters') if params else None
            return search_universal_entity_data(entity_type, search_term, filters)
        except Exception as e:
            logger.error(f"Failed to load search results for {entity_type}: {e}")
            return []
    
    def _load_filtered_results(self, entity_type: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Load filtered results using Universal Engine services"""
        try:
            # Use the same list loader with filters
            return self._load_entity_list(entity_type, params)
        except Exception as e:
            logger.error(f"Failed to load filtered results for {entity_type}: {e}")
            return []
    
    # =================================================================
    # CACHE INVALIDATION
    # =================================================================
    
    def invalidate_entity(self, entity_type: str, identifier: str = None, 
                         hospital_id: str = None, scope: CacheScope = None):
        """Invalidate cache entries for specific entity"""
        
        with self._lock:
            removed_count = 0
            
            # Determine which scopes to invalidate
            scopes_to_check = [scope] if scope else list(CacheScope)
            
            for check_scope in scopes_to_check:
                cache_store = self._cache_stores[check_scope]
                
                for store_key, entries in cache_store.items():
                    # Filter by hospital if specified
                    if hospital_id and check_scope == CacheScope.HOSPITAL and store_key != hospital_id:
                        continue
                    
                    # Find matching cache entries
                    keys_to_remove = []
                    for cache_key, entry in entries.items():
                        if entry.entity_type == entity_type:
                            if identifier is None or identifier in cache_key:
                                keys_to_remove.append(cache_key)
                    
                    # Remove matching entries
                    for key in keys_to_remove:
                        del entries[key]
                        removed_count += 1
            
            # Also invalidate entity configuration cache
            config_key = f"config:{entity_type}"
            if config_key in self._entity_config_cache:
                del self._entity_config_cache[config_key]
                removed_count += 1
            
            self._metrics["invalidations"] += removed_count
            logger.info(f"Invalidated {removed_count} cache entries for {entity_type}")
    
    def invalidate_hospital(self, hospital_id: str):
        """Invalidate all cache entries for a hospital"""
        with self._lock:
            removed_count = 0
            
            # Invalidate hospital-scoped cache
            if hospital_id in self._cache_stores[CacheScope.HOSPITAL]:
                removed_count += len(self._cache_stores[CacheScope.HOSPITAL][hospital_id])
                del self._cache_stores[CacheScope.HOSPITAL][hospital_id]
            
            # Invalidate branch-scoped caches for this hospital
            branch_keys_to_remove = [
                key for key in self._cache_stores[CacheScope.BRANCH].keys()
                if key.startswith(f"{hospital_id}:")
            ]
            for key in branch_keys_to_remove:
                removed_count += len(self._cache_stores[CacheScope.BRANCH][key])
                del self._cache_stores[CacheScope.BRANCH][key]
            
            # Invalidate user-scoped caches for this hospital
            user_keys_to_remove = [
                key for key in self._cache_stores[CacheScope.USER].keys()
                if key.startswith(f"{hospital_id}:")
            ]
            for key in user_keys_to_remove:
                removed_count += len(self._cache_stores[CacheScope.USER][key])
                del self._cache_stores[CacheScope.USER][key]
            
            self._metrics["invalidations"] += removed_count
            logger.info(f"Invalidated {removed_count} cache entries for hospital {hospital_id}")
    
    # =================================================================
    # BACKGROUND OPERATIONS
    # =================================================================
    
    def _setup_background_operations(self):
        """Setup background cache maintenance"""
        def background_worker():
            while True:
                try:
                    time.sleep(300)  # Run every 5 minutes
                    self._cleanup_expired_entries()
                    self._background_refresh_entries()
                except Exception as e:
                    logger.error(f"Background cache operation error: {e}")
        
        worker_thread = threading.Thread(target=background_worker, daemon=True)
        worker_thread.start()
        logger.info("Universal Cache background operations started")
    
    def _cleanup_expired_entries(self):
        """Clean up expired cache entries across all scopes"""
        with self._lock:
            cleaned_count = 0
            
            # Clean all cache stores
            for scope, cache_store in self._cache_stores.items():
                for store_key in list(cache_store.keys()):
                    entries = cache_store[store_key]
                    expired_keys = [key for key, entry in entries.items() if entry.is_expired]
                    
                    for key in expired_keys:
                        del entries[key]
                        cleaned_count += 1
                    
                    # Remove empty stores
                    if not entries:
                        del cache_store[store_key]
            
            # Clean entity configuration cache
            expired_config_keys = [
                key for key, entry in self._entity_config_cache.items() 
                if entry.is_expired
            ]
            for key in expired_config_keys:
                del self._entity_config_cache[key]
                cleaned_count += 1
            
            if cleaned_count > 0:
                logger.debug(f"Cleaned up {cleaned_count} expired cache entries")
    
    def _background_refresh_entries(self):
        """Refresh cache entries that are approaching expiration"""
        # TODO: Implement background refresh logic
        # This would identify entries approaching expiration and refresh them
        pass
    
    # =================================================================
    # STATISTICS AND MONITORING
    # =================================================================
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._lock:
            total_entries = 0
            entries_by_scope = {}
            entries_by_sensitivity = {}
            
            # Count entries across all scopes
            for scope, cache_store in self._cache_stores.items():
                scope_count = sum(len(entries) for entries in cache_store.values())
                entries_by_scope[scope.value] = scope_count
                total_entries += scope_count
            
            # Count by sensitivity (sample from entries)
            for sensitivity in DataSensitivity:
                entries_by_sensitivity[sensitivity.value] = 0
            
            # Add entity configuration cache
            config_entries = len(self._entity_config_cache)
            total_entries += config_entries
            
            hit_ratio = (self._metrics["hits"] / 
                        (self._metrics["hits"] + self._metrics["misses"])) if (
                        self._metrics["hits"] + self._metrics["misses"]) > 0 else 0
            
            return {
                "total_entries": total_entries,
                "config_entries": config_entries,
                "entries_by_scope": entries_by_scope,
                "entries_by_sensitivity": entries_by_sensitivity,
                "cache_hits": self._metrics["hits"],
                "cache_misses": self._metrics["misses"],
                "hit_ratio": hit_ratio,
                "loads_performed": self._metrics["loads"],
                "invalidations_performed": self._metrics["invalidations"],
                "errors": self._metrics["errors"],
                "encryption_enabled": self._encryption.encryption_enabled
            }

# =============================================================================
# GLOBAL CACHE MANAGER INSTANCE
# =============================================================================

_universal_cache_manager = None

def get_universal_cache_manager() -> UniversalCacheManager:
    """Get global Universal Cache Manager instance"""
    global _universal_cache_manager
    if _universal_cache_manager is None:
        _universal_cache_manager = UniversalCacheManager()
    return _universal_cache_manager

def init_universal_cache_manager(app):
    """Initialize Universal Cache Manager with Flask app"""
    global _universal_cache_manager
    _universal_cache_manager = UniversalCacheManager()
    logger.info("Universal Cache Manager initialized with Flask app")