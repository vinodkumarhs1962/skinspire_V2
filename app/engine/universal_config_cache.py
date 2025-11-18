# =============================================================================
# Configuration-Level Cache Enhancement
# File: app/engine/universal_config_cache.py
# =============================================================================

"""
Configuration-Level Cache Enhancement - Secondary Caching Layer
Enhances existing lazy loading infrastructure with intelligent caching

KEY FEATURES:
- Builds on existing LazyConfigProxy and LazyConfigDict infrastructure
- Caches entity configuration objects (get_entity_config calls)
- Near 100% cache hit ratio (configs rarely change)
- Memory-efficient (configs are relatively small)
- Automatic invalidation on config changes (rare)
- Thread-safe for concurrent access
"""

import threading
import time
from typing import Dict, Any, Optional, Set
from datetime import datetime

from app.config.core_definitions import EntityConfiguration, EntityFilterConfiguration, EntitySearchConfiguration
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

# =============================================================================
# CONFIGURATION CACHE ENTRY
# =============================================================================

class ConfigCacheEntry:
    """Configuration cache entry with access tracking"""
    
    def __init__(self, config: Any, config_type: str, entity_type: str):
        self.config = config
        self.config_type = config_type  # 'entity', 'filter', 'search'
        self.entity_type = entity_type
        self.created_at = time.time()
        self.accessed_at = time.time()
        self.access_count = 1
    
    def access(self):
        """Record access to this configuration"""
        self.accessed_at = time.time()
        self.access_count += 1
    
    def get_age_seconds(self) -> float:
        """Get age of configuration in seconds"""
        return time.time() - self.created_at

# =============================================================================
# CONFIGURATION CACHE STATISTICS  
# =============================================================================

class ConfigCacheStatistics:
    """Track configuration cache performance"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.invalidations = 0
        self.config_type_stats = {}  # Stats by config type
        self.entity_stats = {}       # Stats by entity type
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def record_hit(self, config_type: str, entity_type: str):
        """Record configuration cache hit"""
        with self._lock:
            self.hits += 1
            
            # Track by config type
            if config_type not in self.config_type_stats:
                self.config_type_stats[config_type] = {'hits': 0, 'misses': 0}
            self.config_type_stats[config_type]['hits'] += 1
            
            # Track by entity type
            if entity_type not in self.entity_stats:
                self.entity_stats[entity_type] = {'hits': 0, 'misses': 0}
            self.entity_stats[entity_type]['hits'] += 1
    
    def record_miss(self, config_type: str, entity_type: str):
        """Record configuration cache miss"""
        with self._lock:
            self.misses += 1
            
            # Track by config type
            if config_type not in self.config_type_stats:
                self.config_type_stats[config_type] = {'hits': 0, 'misses': 0}
            self.config_type_stats[config_type]['misses'] += 1
            
            # Track by entity type
            if entity_type not in self.entity_stats:
                self.entity_stats[entity_type] = {'hits': 0, 'misses': 0}
            self.entity_stats[entity_type]['misses'] += 1
    
    def record_invalidation(self, entity_type: str):
        """Record configuration invalidation"""
        with self._lock:
            self.invalidations += 1
    
    def get_hit_ratio(self) -> float:
        """Get overall cache hit ratio"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def get_config_type_hit_ratio(self, config_type: str) -> float:
        """Get hit ratio for specific config type"""
        if config_type not in self.config_type_stats:
            return 0.0
        stats = self.config_type_stats[config_type]
        total = stats['hits'] + stats['misses']
        return stats['hits'] / total if total > 0 else 0.0

# =============================================================================
# UNIVERSAL CONFIGURATION CACHE
# =============================================================================

class UniversalConfigurationCache:
    """
    Universal Configuration Cache Manager - Secondary caching layer
    Enhances existing lazy loading with intelligent caching
    """
    
    def __init__(self):
        self.entity_configs: Dict[str, ConfigCacheEntry] = {}
        self.filter_configs: Dict[str, ConfigCacheEntry] = {}
        self.search_configs: Dict[str, ConfigCacheEntry] = {}
        self.statistics = ConfigCacheStatistics()
        self._lock = threading.Lock()
        
        # Configuration dependencies (when one config changes, invalidate related)
        self.config_dependencies = {
            'entity': ['filter', 'search'],  # When entity config changes, clear filter/search
            'filter': [],
            'search': []
        }
        
        logger.info("🔧 Universal Configuration Cache initialized")
    
    def get_cached_entity_config(self, entity_type: str, 
                                loader_func: callable) -> Optional[EntityConfiguration]:
        """
        Get cached entity configuration or load using loader function
        Main interface for entity configuration caching
        """
        start_time = time.time()
        
        # Try to get from cache
        with self._lock:
            entry = self.entity_configs.get(entity_type)
            
            if entry:
                # Cache hit
                entry.access()
                config = entry.config
                response_time = time.time() - start_time
                self.statistics.record_hit('entity', entity_type)
                
                logger.debug(f"🚀 CONFIG CACHE HIT: {entity_type} entity config "
                           f"({response_time*1000:.1f}ms, age: {entry.get_age_seconds():.0f}s)")
                return config
        
        # Cache miss - load configuration
        self.statistics.record_miss('entity', entity_type)
        
        try:
            # Execute loader function
            fresh_config = loader_func()
            
            if fresh_config:
                # Cache the configuration
                self._set_entity_config_cache(entity_type, fresh_config)
                
                response_time = time.time() - start_time
                logger.info(f"📥 CONFIG CACHE MISS: {entity_type} entity config loaded and cached "
                           f"({response_time*1000:.1f}ms)")
            
            return fresh_config
            
        except Exception as e:
            logger.error(f"Error loading entity config for {entity_type}: {e}")
            return None
    
    def get_cached_filter_config(self, entity_type: str,
                               loader_func: callable) -> Optional[EntityFilterConfiguration]:
        """Get cached filter configuration"""
        start_time = time.time()
        
        # Try to get from cache
        with self._lock:
            entry = self.filter_configs.get(entity_type)
            
            if entry:
                # Cache hit
                entry.access()
                config = entry.config
                response_time = time.time() - start_time
                self.statistics.record_hit('filter', entity_type)
                
                logger.debug(f"🚀 CONFIG CACHE HIT: {entity_type} filter config "
                           f"({response_time*1000:.1f}ms)")
                return config
        
        # Cache miss - load configuration
        self.statistics.record_miss('filter', entity_type)
        
        try:
            fresh_config = loader_func()
            
            if fresh_config:
                self._set_filter_config_cache(entity_type, fresh_config)
                
                response_time = time.time() - start_time
                logger.info(f"📥 CONFIG CACHE MISS: {entity_type} filter config loaded "
                           f"({response_time*1000:.1f}ms)")
            
            return fresh_config
            
        except Exception as e:
            logger.error(f"Error loading filter config for {entity_type}: {e}")
            return None
    
    def get_cached_search_config(self, entity_type: str,
                               loader_func: callable) -> Optional[EntitySearchConfiguration]:
        """Get cached search configuration"""
        start_time = time.time()
        
        # Try to get from cache
        with self._lock:
            entry = self.search_configs.get(entity_type)
            
            if entry:
                # Cache hit
                entry.access()
                config = entry.config
                response_time = time.time() - start_time
                self.statistics.record_hit('search', entity_type)
                
                logger.debug(f"🚀 CONFIG CACHE HIT: {entity_type} search config "
                           f"({response_time*1000:.1f}ms)")
                return config
        
        # Cache miss - load configuration
        self.statistics.record_miss('search', entity_type)
        
        try:
            fresh_config = loader_func()
            
            if fresh_config:
                self._set_search_config_cache(entity_type, fresh_config)
                
                response_time = time.time() - start_time
                logger.info(f"📥 CONFIG CACHE MISS: {entity_type} search config loaded "
                           f"({response_time*1000:.1f}ms)")
            
            return fresh_config
            
        except Exception as e:
            logger.error(f"Error loading search config for {entity_type}: {e}")
            return None
    
    def _set_entity_config_cache(self, entity_type: str, config: EntityConfiguration):
        """Set entity configuration in cache"""
        with self._lock:
            entry = ConfigCacheEntry(config, 'entity', entity_type)
            self.entity_configs[entity_type] = entry
    
    def _set_filter_config_cache(self, entity_type: str, config: EntityFilterConfiguration):
        """Set filter configuration in cache"""
        with self._lock:
            entry = ConfigCacheEntry(config, 'filter', entity_type)
            self.filter_configs[entity_type] = entry
    
    def _set_search_config_cache(self, entity_type: str, config: EntitySearchConfiguration):
        """Set search configuration in cache"""
        with self._lock:
            entry = ConfigCacheEntry(config, 'search', entity_type)
            self.search_configs[entity_type] = entry
    
    def invalidate_config_cache(self, entity_type: str, config_type: str = None):
        """
        Invalidate configuration cache for entity
        Called when configuration changes (rare)
        """
        invalidated_count = 0
        
        with self._lock:
            if config_type is None or config_type == 'entity':
                if entity_type in self.entity_configs:
                    del self.entity_configs[entity_type]
                    invalidated_count += 1
            
            if config_type is None or config_type == 'filter':
                if entity_type in self.filter_configs:
                    del self.filter_configs[entity_type]
                    invalidated_count += 1
            
            if config_type is None or config_type == 'search':
                if entity_type in self.search_configs:
                    del self.search_configs[entity_type]
                    invalidated_count += 1
        
        if invalidated_count > 0:
            self.statistics.record_invalidation(entity_type)
            logger.info(f"🗑️ Invalidated {invalidated_count} config cache entries for {entity_type}")
        
        # Handle dependencies
        if config_type == 'entity':
            # When entity config changes, invalidate related configs
            dependent_types = self.config_dependencies.get('entity', [])
            for dep_type in dependent_types:
                self.invalidate_config_cache(entity_type, dep_type)
    
    def clear_all_config_cache(self):
        """Clear entire configuration cache"""
        with self._lock:
            total_count = len(self.entity_configs) + len(self.filter_configs) + len(self.search_configs)
            self.entity_configs.clear()
            self.filter_configs.clear()
            self.search_configs.clear()
            
            logger.info(f"🗑️ Cleared entire configuration cache ({total_count} entries)")
    
    def get_config_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive configuration cache statistics"""
        uptime = time.time() - self.statistics.start_time
        
        total_configs = len(self.entity_configs) + len(self.filter_configs) + len(self.search_configs)
        
        return {
            'hit_ratio': self.statistics.get_hit_ratio(),
            'total_hits': self.statistics.hits,
            'total_misses': self.statistics.misses,
            'total_invalidations': self.statistics.invalidations,
            'total_cached_configs': total_configs,
            'entity_configs_cached': len(self.entity_configs),
            'filter_configs_cached': len(self.filter_configs),
            'search_configs_cached': len(self.search_configs),
            'uptime_hours': uptime / 3600,
            'config_type_stats': self.statistics.config_type_stats,
            'entity_stats': self.statistics.entity_stats,
            'most_accessed_configs': self._get_most_accessed_configs()
        }
    
    def _get_most_accessed_configs(self) -> Dict[str, Any]:
        """Get most frequently accessed configurations"""
        all_configs = []
        
        # Collect all configs with access counts
        for entity_type, entry in self.entity_configs.items():
            all_configs.append({
                'entity_type': entity_type,
                'config_type': 'entity',
                'access_count': entry.access_count,
                'age_seconds': entry.get_age_seconds()
            })
        
        for entity_type, entry in self.filter_configs.items():
            all_configs.append({
                'entity_type': entity_type,
                'config_type': 'filter',
                'access_count': entry.access_count,
                'age_seconds': entry.get_age_seconds()
            })
        
        for entity_type, entry in self.search_configs.items():
            all_configs.append({
                'entity_type': entity_type,
                'config_type': 'search',
                'access_count': entry.access_count,
                'age_seconds': entry.get_age_seconds()
            })
        
        # Sort by access count and return top 10
        all_configs.sort(key=lambda x: x['access_count'], reverse=True)
        return all_configs[:10]

# =============================================================================
# ENHANCED CONFIGURATION LOADER
# =============================================================================

class CachedConfigurationLoader:
    """
    Enhanced Configuration Loader with Caching
    Drop-in replacement for existing ConfigurationLoader
    """
    
    def __init__(self):
        # Keep existing functionality
        from app.config.entity_configurations import ConfigurationLoader
        self._base_loader = ConfigurationLoader()
        
        # Add cache layer
        self._config_cache = UniversalConfigurationCache()
        
        logger.info("🔧 Cached Configuration Loader initialized")
    
    def get_config(self, entity_type: str) -> Optional[EntityConfiguration]:
        """Get entity configuration with caching"""
        def loader():
            return self._base_loader.get_config(entity_type)
        
        return self._config_cache.get_cached_entity_config(entity_type, loader)
    
    def get_filter_config(self, entity_type: str) -> Optional[EntityFilterConfiguration]:
        """Get filter configuration with caching"""
        def loader():
            return self._base_loader.get_filter_config(entity_type)
        
        return self._config_cache.get_cached_filter_config(entity_type, loader)
    
    def get_search_config(self, entity_type: str) -> Optional[EntitySearchConfiguration]:
        """Get search configuration with caching"""
        def loader():
            return self._base_loader.get_search_config(entity_type)
        
        return self._config_cache.get_cached_search_config(entity_type, loader)
    
    def invalidate_cache(self, entity_type: str, config_type: str = None):
        """Invalidate cache for entity (when config changes)"""
        self._config_cache.invalidate_config_cache(entity_type, config_type)
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self._config_cache.get_config_cache_statistics()

# =============================================================================
# GLOBAL CONFIGURATION CACHE MANAGER
# =============================================================================

_cached_config_loader = None
_config_cache_lock = threading.Lock()

def get_cached_configuration_loader() -> CachedConfigurationLoader:
    """Get global cached configuration loader instance"""
    global _cached_config_loader
    
    if _cached_config_loader is None:
        with _config_cache_lock:
            if _cached_config_loader is None:
                _cached_config_loader = CachedConfigurationLoader()
                logger.info("🔧 Global Cached Configuration Loader initialized")
    
    return _cached_config_loader

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def invalidate_config_cache_for_entity(entity_type: str, config_type: str = None):
    """Utility function to invalidate config cache for entity"""
    cached_loader = get_cached_configuration_loader()
    cached_loader.invalidate_cache(entity_type, config_type)

def get_config_cache_statistics() -> Dict[str, Any]:
    """Utility function to get config cache statistics"""
    cached_loader = get_cached_configuration_loader()
    return cached_loader.get_cache_statistics()

def preload_common_configurations():
    """Preload frequently used configurations"""
    common_entities = [
        'suppliers', 'supplier_payments', 'patient_payments', 'medicines', 'patients',
        'users', 'configurations', 'settings', 'package_payment_plans'
    ]
    
    cached_loader = get_cached_configuration_loader()
    
    for entity_type in common_entities:
        try:
            # This will load and cache the configuration
            cached_loader.get_config(entity_type)
            logger.debug(f"Preloaded config for {entity_type}")
        except Exception as e:
            logger.warning(f"Failed to preload config for {entity_type}: {e}")
    
    logger.info(f"🔧 Preloaded configurations for {len(common_entities)} entities")

# =============================================================================
# FLASK APP INTEGRATION
# =============================================================================

def init_config_cache(app):
    """Initialize configuration cache with Flask app"""
    with app.app_context():
        # Initialize cached configuration loader
        cached_loader = get_cached_configuration_loader()
        
        # Set configuration
        app.config.setdefault('CONFIG_CACHE_ENABLED', True)
        app.config.setdefault('CONFIG_CACHE_PRELOAD', True)
        
        # Preload common configurations if enabled
        if app.config.get('CONFIG_CACHE_PRELOAD', True):
            preload_common_configurations()
        
        logger.info("🔧 Universal Configuration Cache initialized successfully")

# Export main classes and functions
__all__ = [
    'UniversalConfigurationCache',
    'CachedConfigurationLoader',
    'get_cached_configuration_loader',
    'invalidate_config_cache_for_entity',
    'get_config_cache_statistics',
    'preload_common_configurations',
    'init_config_cache'
]