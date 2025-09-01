#!/usr/bin/env python
"""
Fixed Config Cache Test Script - Matches actual implementation
"""

from app import create_app
from app.config.entity_configurations import (
    get_entity_config, 
    get_entity_filter_config,
    get_entity_search_config
)
from app.engine.universal_config_cache import get_cached_configuration_loader
import time

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_basic_caching():
    """Test basic config caching functionality"""
    print_header("TEST 1: Basic Config Caching")
    
    # Test entity
    entity_type = 'supplier_payments'
    
    print(f"\n🔍 Testing config cache for {entity_type}...")
    
    # Get the cached loader
    cached_loader = get_cached_configuration_loader()
    
    # Clear cache using the correct method
    if hasattr(cached_loader, 'clear_cache'):
        cached_loader.clear_cache()
        print("   Cache cleared for testing")
    
    # First call - should be a MISS (loads from module)
    start = time.time()
    config1 = get_entity_config(entity_type)
    time1 = time.time() - start
    print(f"   First call (MISS): {time1:.4f} seconds")
    
    # Second call - should be a HIT (from cache)
    start = time.time()
    config2 = get_entity_config(entity_type)
    time2 = time.time() - start
    print(f"   Second call (HIT): {time2:.4f} seconds")
    
    # Verify they're the same object (cached)
    if config1 is config2:
        print("   ✅ Same object returned - caching confirmed!")
    else:
        print("   ❌ Different objects - cache not working")
        return False
    
    # Calculate improvement
    if time1 > 0 and time2 > 0:
        improvement = ((time1 - time2) / time1) * 100
        speedup = time1 / time2
        print(f"   ⚡ Speed improvement: {improvement:.1f}% ({speedup:.1f}x faster)")
    
    return True

def test_cache_statistics():
    """Test cache statistics and monitoring"""
    print_header("TEST 2: Cache Statistics")
    
    cached_loader = get_cached_configuration_loader()
    stats = cached_loader.get_cache_statistics()
    
    print("\n📊 Current Cache Statistics:")
    print(f"   Total Hits:    {stats.get('total_hits', 0)}")
    print(f"   Total Misses:  {stats.get('total_misses', 0)}")
    print(f"   Hit Ratio:     {stats.get('hit_ratio', 0):.2%}")
    
    # Additional stats if available
    if 'cache_entries' in stats:
        print(f"   Cache Entries: {stats['cache_entries']}")
    if 'memory_usage' in stats:
        print(f"   Memory Usage:  {stats['memory_usage']}")
    
    # Check cache health
    hit_ratio = stats.get('hit_ratio', 0)
    if hit_ratio > 0:
        print(f"\n   ✅ Cache is working! Hit ratio: {hit_ratio:.1%}")
    else:
        print("   ⚠️  No cache hits yet - cache may be warming up")
    
    return True

def test_config_types():
    """Test all config types (entity, filter, search)"""
    print_header("TEST 3: All Config Types")
    
    entity_type = 'supplier_payments'
    
    print(f"\n🔍 Testing all config types for {entity_type}...")
    
    # Test entity config
    start = time.time()
    entity_config = get_entity_config(entity_type)
    print(f"   Entity config: {entity_config.name if entity_config else 'None'} ({time.time()-start:.4f}s)")
    
    # Test filter config
    start = time.time()
    filter_config = get_entity_filter_config(entity_type)
    print(f"   Filter config: {'Found' if filter_config else 'None'} ({time.time()-start:.4f}s)")
    
    # Test search config
    start = time.time()
    search_config = get_entity_search_config(entity_type)
    print(f"   Search config: {'Found' if search_config else 'None'} ({time.time()-start:.4f}s)")
    
    # Load again to test caching
    print("\n🔄 Re-loading same configs (should be cached)...")
    
    start = time.time()
    entity_config2 = get_entity_config(entity_type)
    time_cached = time.time() - start
    
    if time_cached < 0.001:
        print(f"   ✅ Entity config cached: {time_cached:.5f}s")
    else:
        print(f"   ⚠️  Entity config slow: {time_cached:.4f}s")
    
    start = time.time()
    filter_config2 = get_entity_filter_config(entity_type)
    time_cached = time.time() - start
    
    if time_cached < 0.001:
        print(f"   ✅ Filter config cached: {time_cached:.5f}s")
    else:
        print(f"   ⚠️  Filter config slow: {time_cached:.4f}s")
    
    start = time.time()
    search_config2 = get_entity_search_config(entity_type)
    time_cached = time.time() - start
    
    if time_cached < 0.001:
        print(f"   ✅ Search config cached: {time_cached:.5f}s")
    else:
        print(f"   ⚠️  Search config slow: {time_cached:.4f}s")
    
    return True

def test_multiple_entities():
    """Test caching for multiple entities"""
    print_header("TEST 4: Multiple Entities")
    
    entities_to_test = [
        'suppliers',
        'supplier_payments',
        'patients',
        'medicines',
        'users'
    ]
    
    print("\n📦 Loading multiple entity configurations...")
    load_times = {}
    configs = {}
    
    for entity in entities_to_test:
        try:
            start = time.time()
            config = get_entity_config(entity)
            elapsed = time.time() - start
            load_times[entity] = elapsed
            
            if config:
                configs[entity] = config
                print(f"   ✅ {entity:<20} loaded in {elapsed:.4f}s")
            else:
                print(f"   ⚠️  {entity:<20} no configuration found")
        except Exception as e:
            print(f"   ❌ {entity:<20} error: {str(e)}")
    
    print("\n🔄 Re-loading same entities (should be cached)...")
    
    for entity in configs.keys():
        start = time.time()
        config = get_entity_config(entity)
        elapsed = time.time() - start
        
        if elapsed < load_times[entity] / 10:  # Should be at least 10x faster
            print(f"   ✅ {entity:<20} cached ({elapsed:.5f}s)")
        else:
            print(f"   ⚠️  {entity:<20} slow ({elapsed:.4f}s)")
    
    return len(configs) > 0

def main():
    """Run all tests"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("  CONFIG CACHE TEST SUITE (FIXED)")
        print("="*60)
        
        # Check if caching is enabled
        if not app.config.get('CONFIG_CACHE_ENABLED', False):
            print("\n❌ CONFIG_CACHE_ENABLED is False!")
            print("Please ensure initialize_cache_system() is called in app/__init__.py")
            return
        else:
            print("\n✅ Config cache is ENABLED")
        
        # Run tests
        tests = [
            ("Basic Caching", test_basic_caching),
            ("Cache Statistics", test_cache_statistics),
            ("All Config Types", test_config_types),
            ("Multiple Entities", test_multiple_entities)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"\n❌ Test '{test_name}' error: {e}")
                results.append((test_name, False))
        
        # Print summary
        print_header("TEST SUMMARY")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"\n📊 Test Results: {passed}/{total} passed")
        print()
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name:<30} {status}")
        
        # Get final stats
        cached_loader = get_cached_configuration_loader()
        final_stats = cached_loader.get_cache_statistics()
        
        print(f"\n📊 Final Cache Performance:")
        print(f"   Total Hits:   {final_stats.get('total_hits', 0)}")
        print(f"   Total Misses: {final_stats.get('total_misses', 0)}")
        print(f"   Hit Ratio:    {final_stats.get('hit_ratio', 0):.1%}")
        
        # Final verdict
        print()
        if final_stats.get('hit_ratio', 0) > 0:
            print("🎉 CONFIG CACHE IS WORKING!")
            print(f"   Your configurations are being cached successfully.")
            print(f"   Hit ratio: {final_stats.get('hit_ratio', 0):.1%}")
        else:
            print("⚠️  Config cache initialized but no hits yet.")
            print("   Navigate through your app to build up the cache.")

if __name__ == "__main__":
    main()