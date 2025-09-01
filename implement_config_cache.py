#!/usr/bin/env python
"""
Config Cache Implementation Helper Script - Fixed for UTF-8
Run this to help implement config cache in your project
"""

import os
import re

def update_entity_configurations():
    """Update entity_configurations.py to use cached loader"""
    
    file_path = 'app/config/entity_configurations.py'
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📝 Updating {file_path}...")
    
    # Read with UTF-8 encoding
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already updated
    if 'get_cached_configuration_loader' in content:
        print("✅ File already updated with cached loader")
        return True
    
    # Save backup first
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"📦 Backup saved to {backup_path}")
    
    # Add import after the last import from app.config
    import_line = "from app.engine.universal_config_cache import get_cached_configuration_loader\n"
    
    # Find the imports section and add our import
    if 'from app.config.filter_categories import FilterCategory' in content:
        content = content.replace(
            'from app.config.filter_categories import FilterCategory',
            'from app.config.filter_categories import FilterCategory\n' + import_line
        )
    else:
        # Add after logger import as fallback
        content = content.replace(
            'logger = logging.getLogger(__name__)',
            'logger = logging.getLogger(__name__)\n\n' + import_line
        )
    
    # Replace _loader initialization
    if '_loader = ConfigurationLoader()' in content:
        old_loader = "_loader = ConfigurationLoader()"
        new_loader = """_loader = None  # Will be initialized with cached loader

def _get_loader():
    \"\"\"Get the cached configuration loader (lazy initialization)\"\"\"
    global _loader
    if _loader is None:
        from app.engine.universal_config_cache import get_cached_configuration_loader
        _loader = get_cached_configuration_loader()
    return _loader"""
        
        content = content.replace(old_loader, new_loader)
        print("✅ Replaced loader initialization")
    else:
        print("⚠️  Could not find '_loader = ConfigurationLoader()' - manual update needed")
    
    # Update get_entity_config function
    old_patterns = [
        (r'def get_entity_config\(entity_type: str\).*?\n.*?return _loader\.get_config\(entity_type\)',
         '''def get_entity_config(entity_type: str) -> Optional[EntityConfiguration]:
    """Get entity configuration by type with caching"""
    loader = _get_loader()
    return loader.get_config(entity_type)'''),
    ]
    
    for pattern, replacement in old_patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Simple replacements for other functions
    replacements = [
        ('return _loader.get_filter_config(entity_type)',
         'loader = _get_loader()\n    return loader.get_filter_config(entity_type)'),
        ('return _loader.get_search_config(entity_type)',
         'loader = _get_loader()\n    return loader.get_search_config(entity_type)'),
    ]
    
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Updated function using: {old[:30]}...")
    
    # Write updated content with UTF-8 encoding
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Successfully updated {file_path}")
    return True

def add_cache_initialization():
    """Add cache initialization to app/__init__.py"""
    
    file_path = 'app/__init__.py'
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📝 Checking {file_path}...")
    
    # Read with UTF-8 encoding
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already has cache initialization
    if 'initialize_cache_system' in content or 'init_config_cache' in content:
        print("✅ Cache initialization already present")
        return True
    
    print("\n⚠️  Please manually add cache initialization to app/__init__.py")
    print("\n" + "="*60)
    print("Add this function to app/__init__.py:")
    print("="*60)
    print("""
def initialize_cache_system(app):
    \"\"\"Initialize both service and config cache layers\"\"\"
    
    # Config Cache Settings
    app.config.setdefault('CONFIG_CACHE_ENABLED', True)
    app.config.setdefault('CONFIG_CACHE_PRELOAD', True)
    app.config.setdefault('CONFIG_CACHE_TTL', 3600)  # 1 hour
    
    # Initialize Config Cache
    if app.config.get('CONFIG_CACHE_ENABLED'):
        try:
            from app.engine.universal_config_cache import init_config_cache
            init_config_cache(app)
            app.logger.info("✅ Config cache initialized")
        except Exception as e:
            app.logger.error(f"Config cache init failed: {e}")
    """)
    
    print("\n" + "="*60)
    print("And call it in create_app() after init_db(app):")
    print("="*60)
    print("    initialize_cache_system(app)")
    print("")
    
    return True

def verify_files_exist():
    """Check that required cache files exist"""
    
    required_files = [
        'app/engine/universal_config_cache.py',
        'app/config/entity_configurations.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ Found: {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
            all_exist = False
    
    return all_exist

def create_test_script():
    """Create a test script to verify config cache"""
    
    test_script = '''#!/usr/bin/env python
"""Test script to verify config cache is working"""

from app import create_app
from app.config.entity_configurations import get_entity_config
from app.engine.universal_config_cache import get_cached_configuration_loader
import time

def test_config_cache():
    """Test that configuration caching is working"""
    app = create_app()
    
    with app.app_context():
        print("\\n" + "="*60)
        print("CONFIG CACHE TEST")
        print("="*60)
        
        # Get cache manager
        cached_loader = get_cached_configuration_loader()
        
        # Test entity
        entity_type = 'supplier_payments'
        
        print(f"\\n🔍 Testing config cache for {entity_type}...")
        
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
        
        # Calculate improvement
        if time1 > 0:
            improvement = ((time1 - time2) / time1) * 100
            print(f"   ⚡ Speed improvement: {improvement:.1f}%")
        
        # Show cache statistics
        stats = cached_loader.get_cache_statistics()
        print(f"\\n📊 Config Cache Statistics:")
        print(f"   Total Hits: {stats['total_hits']}")
        print(f"   Total Misses: {stats['total_misses']}")
        print(f"   Hit Ratio: {stats['hit_ratio']:.2%}")
        print(f"   Cache Size: {stats['cache_size']} entries")
        
        if stats['total_hits'] > 0:
            print("\\n✅ CONFIG CACHE IS WORKING!")
        else:
            print("\\n❌ Config cache not working - check implementation")

if __name__ == "__main__":
    test_config_cache()
'''
    
    test_file = 'test_config_cache.py'
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_script)
    
    print(f"✅ Created test script: {test_file}")
    return test_file

def main():
    """Main implementation helper"""
    
    print("=" * 60)
    print("CONFIG CACHE IMPLEMENTATION HELPER (UTF-8 Fixed)")
    print("=" * 60)
    
    # Step 1: Verify files
    print("\n📋 Step 1: Verifying required files...")
    if not verify_files_exist():
        print("\n❌ Please ensure all required files are present")
        return
    
    # Step 2: Update entity_configurations.py
    print("\n📋 Step 2: Updating entity_configurations.py...")
    try:
        if not update_entity_configurations():
            print("\n❌ Failed to update entity_configurations.py")
            return
    except Exception as e:
        print(f"\n❌ Error updating file: {e}")
        print("Please check the backup file and update manually if needed")
        return
    
    # Step 3: Instructions for app/__init__.py
    print("\n📋 Step 3: App initialization...")
    add_cache_initialization()
    
    # Step 4: Create test script
    print("\n📋 Step 4: Creating test script...")
    test_file = create_test_script()
    
    # Step 5: Final instructions
    print("\n" + "=" * 60)
    print("✅ IMPLEMENTATION COMPLETE!")
    print("=" * 60)
    
    print("\n📋 Next Steps:")
    print("1. Review the changes in app/config/entity_configurations.py")
    print("2. Add cache initialization to app/__init__.py (see instructions above)")
    print("3. Restart your Flask application")
    print(f"4. Run the test script: python {test_file}")
    
    print("\n5. Check Cache Dashboard:")
    print("   - Config cache should show entries")
    print("   - Hit ratio should reach 95-100%")
    
    print("\n💡 Tips:")
    print("   - If you see errors, check the .backup file")
    print("   - The config cache will significantly speed up page loads")
    print("   - Monitor the cache dashboard to see the improvement")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the backup files and update manually if needed")