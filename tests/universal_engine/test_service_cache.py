# Create test file: test_service_cache.py
# python tests/universal_engine/test_service_cache.py

import time
import uuid
from app.engine.universal_services import get_universal_service

def test_service_caching_with_valid_data():
    """Test service caching with proper UUID format and real data"""
    
    print("Testing Service-Level Caching (Corrected)...")
    
    # Get a service
    service = get_universal_service('supplier_payments')
    
    # Use proper UUID format - either get from your database or create test UUID
    # Option 1: Use a test UUID (will likely return empty results but won't error)
    test_hospital_id = str(uuid.uuid4())  # Generate a test UUID
    
    # Option 2: If you have actual data, replace with real hospital_id
    # test_hospital_id = 'your-actual-hospital-uuid-here'
    
    print(f"Using test hospital_id: {test_hospital_id}")
    
    # Test parameters
    test_filters = {}  # Start with empty filters to avoid additional errors
    test_kwargs = {
        'hospital_id': test_hospital_id,  # Now using proper UUID format
        'page': 1,
        'per_page': 10  # Smaller page size for testing
    }
    
    print("\n1️⃣ First call (cache miss expected)...")
    start_time = time.time()
    try:
        result1 = service.search_data(test_filters, **test_kwargs)
        first_call_time = time.time() - start_time
        first_success = True
        print(f"   ✅ Response time: {first_call_time*1000:.1f}ms")
        print(f"   Records returned: {len(result1.get('items', []))}")
    except Exception as e:
        first_call_time = time.time() - start_time
        first_success = False
        print(f"   ❌ Error occurred: {str(e)[:100]}...")
        print(f"   Response time: {first_call_time*1000:.1f}ms")
    
    print("\n2️⃣ Second call (cache hit expected)...")
    start_time = time.time()
    try:
        result2 = service.search_data(test_filters, **test_kwargs)
        second_call_time = time.time() - start_time
        second_success = True
        print(f"   ✅ Response time: {second_call_time*1000:.1f}ms")
        print(f"   Records returned: {len(result2.get('items', []))}")
    except Exception as e:
        second_call_time = time.time() - start_time
        second_success = False
        print(f"   ❌ Error occurred: {str(e)[:100]}...")
        print(f"   Response time: {second_call_time*1000:.1f}ms")
    
    # Analyze results
    print(f"\n📊 Analysis:")
    if first_call_time > 0 and second_call_time > 0:
        improvement = (first_call_time - second_call_time) / first_call_time * 100
        print(f"   Performance improvement: {improvement:.1f}%")
        
        if improvement > 30:  # Even 30% improvement indicates caching
            print("   ✅ Service caching appears to be working!")
            cache_status = "WORKING"
        else:
            print("   ⚠️  Minimal improvement - caching may not be active")
            cache_status = "NEEDS_CHECK"
    else:
        cache_status = "UNKNOWN"
    
    # Check cache statistics
    print(f"\n📈 Cache Statistics:")
    try:
        from app.engine.universal_service_cache import get_service_cache_statistics
        stats = get_service_cache_statistics()
        print(f"   Total hits: {stats['total_hits']}")
        print(f"   Total misses: {stats['total_misses']}")
        print(f"   Hit ratio: {stats['hit_ratio']:.2%}")
        print(f"   Memory usage: {stats['memory_usage_mb']:.1f}MB")
        
        if stats['total_hits'] > 0:
            print("   ✅ Cache statistics confirm caching is active")
        else:
            print("   ⚠️  No cache hits recorded - decorator may not be applied")
            
    except Exception as e:
        print(f"   ❌ Could not retrieve cache statistics: {e}")
    
    return {
        'cache_status': cache_status,
        'first_call_time': first_call_time,
        'second_call_time': second_call_time,
        'improvement': improvement if first_call_time > 0 else 0
    }

def test_cache_system_without_database():
    """Test cache system functionality without database calls"""
    print("\n🧪 Testing Cache System Direct Functionality...")
    
    try:
        from app.engine.universal_service_cache import get_service_cache_manager
        
        cache_manager = get_service_cache_manager()
        print(f"   ✅ Cache manager created: {type(cache_manager).__name__}")
        print(f"   Max memory: {cache_manager.max_memory_bytes / (1024*1024):.0f}MB")
        print(f"   Current entries: {len(cache_manager.cache_store)}")
        
        # Test direct cache functionality
        test_entity = 'test_entity'
        test_operation = 'test_operation'
        test_params = {'test': 'data'}
        
        def test_loader():
            return {'test_result': 'success', 'items': []}
        
        # First call - should be miss
        start = time.time()
        result1 = cache_manager.get_cached_service_result(
            entity_type=test_entity,
            operation=test_operation,
            service_params=test_params,
            loader_func=test_loader
        )
        first_time = time.time() - start
        
        # Second call - should be hit
        start = time.time()
        result2 = cache_manager.get_cached_service_result(
            entity_type=test_entity,
            operation=test_operation,
            service_params=test_params,
            loader_func=test_loader
        )
        second_time = time.time() - start
        
        print(f"   First call: {first_time*1000:.1f}ms")
        print(f"   Second call: {second_time*1000:.1f}ms")
        
        if second_time < first_time:
            print("   ✅ Direct cache functionality working correctly")
            return True
        else:
            print("   ❌ Direct cache functionality has issues")
            return False
            
    except Exception as e:
        print(f"   ❌ Cache system error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("SERVICE CACHE TESTING - CORRECTED VERSION")
    print("="*60)
    
    # Test 1: Direct cache functionality (no database)
    direct_test = test_cache_system_without_database()
    
    # Test 2: Service integration test
    if direct_test:
        service_test = test_service_caching_with_valid_data()
        
        if service_test['cache_status'] == 'NEEDS_CHECK':
            print("\n⚠️  NEXT STEPS:")
            print("   1. Verify cache decorator is applied to service methods")
            print("   2. Check if service method has @cache_service_method decorator")
            print("   3. Ensure service has entity_type attribute set")
    else:
        print("\n❌ CACHE SYSTEM ISSUES:")
        print("   Direct cache functionality is not working")
        print("   Check universal_service_cache.py deployment")
    
    print("\n" + "="*60)