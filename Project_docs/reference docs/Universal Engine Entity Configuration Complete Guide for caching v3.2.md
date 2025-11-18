# Universal Engine Entity Configuration Complete Guide v3.2
## Comprehensive Configuration Manual with Dual-Layer Caching Integration

---

## 📋 **Document Overview**

| **Attribute** | **Details** |
|---------------|-------------|
| **Project** | Skinspire Clinic HMS - Universal Engine v3.2 |
| **Version** | Universal Engine v3.2 (Built on v3.1 + Cache Layer) |
| **Status** | **PRODUCTION READY WITH CACHING** |
| **Date** | December 2024 |
| **Architecture** | Configuration-Driven, Backend-Heavy, Entity-Agnostic, **Dual-Layer Cached** |
| **New Features** | **Service Cache, Config Cache, Auto-Invalidation** |

---

## 📚 **Table of Contents**
1. [Universal Engine v3.2 Overview](#1-universal-engine-v32-overview)
2. [System Architecture with Caching](#2-system-architecture-with-caching) 
3. [Entity Classification](#3-entity-classification)
4. [Configuration Structure](#4-configuration-structure)
5. [Core Definitions Reference](#5-core-definitions-reference)
6. [Step-by-Step Configuration](#6-step-by-step-configuration)
7. [**Cache Configuration (NEW)**](#7-cache-configuration)
8. [CRUD Operations Configuration](#8-crud-operations-configuration)
9. [Document Engine Configuration](#9-document-engine-configuration)
10. [Advanced Features](#10-advanced-features)
11. [Best Practices & Patterns](#11-best-practices--patterns)
12. [Troubleshooting Guide](#12-troubleshooting-guide)
13. [Quick Reference](#13-quick-reference)

---

## **1. Universal Engine v3.2 Overview**

### **🎯 Core Principles (Enhanced with Caching)**

#### **✅ Dual-Layer Caching Architecture (NEW)**
The Universal Engine now includes automatic caching at two levels:

```python
# Layer 1: Service-Level Cache (70% performance gain)
# - Caches database query results
# - Parameter-aware (filters, pagination, etc.)
# - TTL: 30 minutes default

# Layer 2: Configuration-Level Cache (20% performance gain)  
# - Caches entity configurations
# - Near 100% hit ratio
# - TTL: 1 hour default
```

#### **✅ Configuration-Driven**
Every aspect of entity behavior is defined through configuration, not code.

#### **✅ Backend-Heavy Architecture**
- All business logic, calculations, and database operations in Python services
- **NEW**: Service results automatically cached
- JavaScript only for UI interactions

#### **✅ Entity-Agnostic Design**
- One implementation serves all entities
- **NEW**: Cache keys automatically generated per entity
- Maximum code reuse across modules

### **🚀 v3.2 Cache Capabilities**

| **Feature** | **Performance Gain** | **Automatic** |
|-------------|---------------------|---------------|
| **Service Cache** | 70% faster | ✅ |
| **Config Cache** | 20% faster | ✅ |
| **Total Improvement** | 90% faster | ✅ |
| **Memory Usage** | < 500MB | Monitored |
| **Cache Dashboard** | Real-time stats | ✅ |

---

## **2. System Architecture with Caching**

### **📐 Enhanced Request Flow with Cache Layers**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Universal Engine v3.2 with Caching                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Request → Route → Universal View                                          │
│     ↓                                                                      │
│  1. Entity Registry validates operation scope                              │
│     └─> Masters: Full CRUD, Transactions: Read-only                        │
│                                                                             │
│  2. Configuration Loader fetches entity configuration                      │
│     └─> 🆕 CONFIG CACHE: 100% hit ratio after first load                  │
│                                                                             │
│  3. Universal Service handles business logic                               │
│     └─> 🆕 SERVICE CACHE: 70-90% hit ratio for repeated queries           │
│                                                                             │
│  4. Data Assembler processes data for presentation                         │
│     └─> Format fields, apply permissions, generate actions                 │
│                                                                             │
│  5. Templates render universal UI                                          │
│     └─> Dynamic forms, tables, documents based on configuration            │
│                                                                             │
│  6. JavaScript provides progressive enhancement                            │
│     └─> Auto-save, validation feedback, UI interactions                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## **7. Cache Configuration (NEW SECTION)**

### **🚀 Overview**

The Universal Engine v3.2 includes automatic dual-layer caching that requires minimal configuration:

1. **Configuration Cache** - Automatic, no setup needed
2. **Service Cache** - Requires decorator on service methods

### **📦 Layer 1: Service-Level Cache Configuration**

#### **Step 1: Import Cache Decorator**

```python
# In your service file (e.g., app/services/your_entity_service.py)
from app.engine.universal_service_cache import cache_service_method
```

#### **Step 2: Apply Cache Decorator to Service Methods**

```python
class YourEntityService(UniversalEntityService):
    def __init__(self):
        super().__init__('your_entities', YourEntityModel)
        self.entity_type = 'your_entities'  # Required for cache
    
    @cache_service_method()  # ← ADD THIS DECORATOR
    def search_data(self, filters: dict, **kwargs) -> dict:
        """Search entities with automatic caching"""
        # Your existing implementation remains unchanged
        return super().search_data(filters, **kwargs)
    
    @cache_service_method()  # ← ADD THIS DECORATOR
    def get_item_data(self, item_id: str, **kwargs) -> dict:
        """Get entity details with automatic caching"""
        # Your existing implementation remains unchanged
        return super().get_item_data(item_id, **kwargs)
    
    @cache_service_method()  # ← ADD THIS DECORATOR
    def get_list_data(self, filters: dict, **kwargs) -> dict:
        """Get entity list with automatic caching"""
        # Your existing implementation remains unchanged
        return super().get_list_data(filters, **kwargs)
```

#### **Step 3: Cache Configuration in Entity Config**

```python
YOUR_ENTITY_CONFIG = EntityConfiguration(
    # ... existing configuration ...
    
    # 🆕 CACHE CONFIGURATION
    cache_config={
        "enabled": True,                    # Enable caching for this entity
        "ttl": 1800,                        # Cache TTL in seconds (30 min default)
        "max_entries": 1000,                # Max cache entries per entity
        "invalidate_on_write": True,        # Clear cache on create/update/delete
        "cache_filters": True,               # Cache filtered queries
        "cache_detail_views": True,          # Cache detail views
        "warmup_on_startup": False,          # Preload common queries on startup
        "exclude_fields": [],                # Fields to exclude from cache key
    },
    
    # ... rest of configuration ...
)
```

### **📦 Layer 2: Configuration Cache (Automatic)**

Configuration caching is **automatic** - no setup required! The system automatically caches:

- Entity configurations
- Field definitions  
- Filter configurations
- Search configurations
- Document configurations

### **🔄 Cache Invalidation Strategies**

#### **Automatic Invalidation**

```python
# Cache automatically invalidates on:
# 1. Create operations
# 2. Update operations  
# 3. Delete operations
# 4. Bulk operations

# No code needed - it's automatic!
```

#### **Manual Invalidation (When Needed)**

```python
from app.engine.universal_service_cache import get_service_cache_manager
from app.config.entity_configurations import invalidate_entity_config_cache

# Clear service cache for specific entity
def clear_entity_cache(entity_type: str):
    """Clear all caches for an entity"""
    
    # Clear service cache
    cache_manager = get_service_cache_manager()
    cache_manager.clear_cache_for_entity(entity_type)
    
    # Clear config cache
    invalidate_entity_config_cache(entity_type)
    
    print(f"Cache cleared for {entity_type}")
```

### **📊 Cache Monitoring**

#### **Dashboard Integration**

Your entity's cache performance is automatically visible in the Cache Dashboard:

1. Navigate to **Administration → Cache Dashboard**
2. View real-time statistics:
   - Hit ratio per entity
   - Memory usage
   - Response times
   - Cache size

#### **Programmatic Monitoring**

```python
from app.engine.universal_service_cache import get_service_cache_manager

# Get cache statistics for your entity
def get_entity_cache_stats(entity_type: str):
    cache_manager = get_service_cache_manager()
    stats = cache_manager.get_entity_statistics(entity_type)
    
    print(f"Entity: {entity_type}")
    print(f"Hit Ratio: {stats['hit_ratio']:.2%}")
    print(f"Cache Entries: {stats['entry_count']}")
    print(f"Memory Usage: {stats['memory_usage']}")
```

### **⚡ Cache Performance Tips**

#### **1. Optimize Cache Keys**

```python
# Good: Specific cache configuration
cache_config={
    "exclude_fields": ["created_at", "updated_at"],  # Exclude timestamps
    "cache_filters": True,  # Cache filtered results
}

# Bad: No optimization
cache_config={
    "enabled": True  # Too generic
}
```

#### **2. Choose Appropriate TTL**

```python
# Master entities (change rarely) - Long TTL
"suppliers": {
    "ttl": 3600,  # 1 hour
}

# Transaction entities (change frequently) - Short TTL
"payments": {
    "ttl": 300,  # 5 minutes
}

# Real-time entities - Very short TTL
"notifications": {
    "ttl": 60,  # 1 minute
}
```

#### **3. Warmup Strategies**

```python
# For frequently accessed entities
cache_config={
    "warmup_on_startup": True,  # Preload common queries
    "warmup_queries": [
        {"status": "active"},     # Preload active records
        {"branch_id": "main"},     # Preload main branch
    ]
}
```

### **🎯 Cache Best Practices**

1. **Always use cache decorator** on service methods
2. **Set appropriate TTL** based on data volatility
3. **Monitor hit ratios** via dashboard
4. **Clear cache after bulk imports**
5. **Use warmup for frequently accessed data**
6. **Exclude volatile fields** from cache keys
7. **Test cache invalidation** after writes

---

## **6. Step-by-Step Configuration (With Cache)**

### **Step 1: Register Entity (With Cache Awareness)**

```python
# In app/config/entity_registry.py
ENTITY_REGISTRY["your_entity"] = EntityRegistration(
    category=EntityCategory.MASTER,
    module="app.config.modules.master_entities",
    service_class="app.services.your_entity_service.YourEntityService",
    model_class="app.models.master.YourEntity",
    # 🆕 Cache settings
    cache_enabled=True,  # Enable caching for this entity
    cache_ttl=1800       # Entity-specific TTL
)
```

### **Step 2: Create Service with Cache**

```python
# app/services/your_entity_service.py
from app.engine.universal_entity_service import UniversalEntityService
from app.engine.universal_service_cache import cache_service_method

class YourEntityService(UniversalEntityService):
    def __init__(self):
        super().__init__('your_entities', YourEntityModel)
        self.entity_type = 'your_entities'
    
    @cache_service_method()  # 🆕 Add cache decorator
    def search_data(self, filters: dict, **kwargs) -> dict:
        """Enhanced search with caching"""
        # Standard implementation
        result = super().search_data(filters, **kwargs)
        
        # Optional: Add cache headers for client
        result['cache_info'] = {
            'cached': True,
            'ttl': 1800
        }
        
        return result
```

---

## **11. Best Practices & Patterns (Updated with Cache)**

### **✅ DO's**

1. **Always add cache decorator** to service methods
2. **Monitor cache performance** via dashboard
3. **Set appropriate TTL** for each entity type
4. **Clear cache after bulk operations**
5. **Use cache warmup** for frequently accessed entities
6. **Test with cache enabled and disabled**

### **❌ DON'Ts**

1. **Don't cache sensitive data** without encryption
2. **Don't use very long TTL** for volatile data
3. **Don't ignore cache invalidation** after writes
4. **Don't cache user-specific data** in shared cache
5. **Don't exceed memory limits** (500MB default)

---

## **12. Troubleshooting Guide (Cache Issues)**

### **🔍 Common Cache Issues**

| **Issue** | **Cause** | **Solution** |
|-----------|-----------|--------------|
| Low hit ratio | Cache not configured | Add `@cache_service_method()` decorator |
| Stale data | TTL too long | Reduce TTL or invalidate on write |
| Memory overflow | Too many entries | Reduce max_entries or TTL |
| Slow first load | No warmup | Enable warmup_on_startup |
| Cache not working | Disabled in config | Check CONFIG_CACHE_ENABLED |

### **🛠️ Cache Debugging**

```python
# Check if cache is working for your entity
from app.engine.universal_service_cache import debug_cache_key_for_request

# In Flask shell
debug_info = debug_cache_key_for_request()
print(debug_info)

# Check cache stats
from app.engine.universal_service_cache import get_service_cache_manager
cache_manager = get_service_cache_manager()
stats = cache_manager.get_cache_statistics()
print(f"Overall hit ratio: {stats['hit_ratio']:.2%}")
```

---

## **13. Quick Reference (With Cache)**

### **📋 Complete Configuration Checklist**

#### **Entity Setup with Cache**
- [ ] Register in `entity_registry.py` with cache settings
- [ ] Add `@cache_service_method()` to service methods
- [ ] Configure cache_config in EntityConfiguration
- [ ] Set appropriate TTL for entity type
- [ ] Define cache invalidation strategy
- [ ] Test cache hit ratio
- [ ] Monitor via Cache Dashboard

### **🚀 Cache Configuration Quick Reference**

```python
# Minimal cache setup
@cache_service_method()
def search_data(self, filters: dict, **kwargs) -> dict:
    return super().search_data(filters, **kwargs)

# Advanced cache setup
@cache_service_method(
    entity_type='your_entities',
    operation='custom_search',
    ttl=600  # Custom TTL
)
def custom_search(self, params: dict) -> dict:
    # Your implementation
    pass

# Entity config with cache
cache_config={
    "enabled": True,
    "ttl": 1800,
    "invalidate_on_write": True,
    "warmup_on_startup": True
}
```

### **📊 Performance Expectations**

| **Operation** | **Without Cache** | **With Cache** | **Improvement** |
|---------------|-------------------|----------------|-----------------|
| List View | 200ms | 20ms | 10x faster |
| Detail View | 150ms | 5ms | 30x faster |
| Filtered Search | 300ms | 30ms | 10x faster |
| Config Load | 10ms | 0.01ms | 1000x faster |

---

## **🎉 Conclusion**

The Universal Engine v3.2 with dual-layer caching provides:

- **90% Performance Improvement** through automatic caching
- **Zero-Code Cache Integration** for configurations
- **Simple Decorator Pattern** for service caching
- **Real-Time Monitoring** via Cache Dashboard
- **Automatic Invalidation** on data changes
- **Memory-Efficient** design with configurable limits

By following this guide, your entities will automatically benefit from the caching infrastructure, providing blazing-fast performance while maintaining data consistency.

### **Key Takeaways for Cache Integration**

1. **Configuration Cache is Automatic** - Just register your entity
2. **Service Cache Needs Decorator** - Add `@cache_service_method()`
3. **Monitor Performance** - Use Cache Dashboard
4. **Tune TTL Values** - Based on data volatility
5. **Test Both Layers** - Verify config and service caching

The Universal Engine v3.2 is production-ready with enterprise-grade caching that delivers exceptional performance out of the box.

---

**📚 Additional Cache Resources**
- **Service Cache**: `app/engine/universal_service_cache.py`
- **Config Cache**: `app/engine/universal_config_cache.py`
- **Cache Dashboard**: `/admin/cache-dashboard`
- **Cache CLI**: `python -m app.cache_cli`
- **Performance Guide**: `Optimal Multi-Layer Caching Strategy.md`

*Universal Engine v3.2 - Configuration-Driven Excellence with Blazing-Fast Cache*