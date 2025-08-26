# fix_supplier_fields.py
import sys
import os

# Add your project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.modules.master_entities import SUPPLIER_FIELDS

# Section to Tab mapping
SECTION_TO_TAB_MAP = {
    # Profile tab sections
    'basic_info': 'profile',
    'contact_info': 'profile',
    'address_info': 'profile',
    
    # Business Info tab sections
    'manager_info': 'business_info',
    'banking_info': 'business_info',
    'tax_info': 'business_info',
    'business_rules': 'business_info',
    
    # System Info tab sections
    'audit_info': 'system_info',
    'technical_info': 'system_info',
}

def update_field_tab_groups():
    """Update tab_group for all fields based on their section"""
    
    updates_made = []
    
    for field in SUPPLIER_FIELDS:
        if hasattr(field, 'section') and field.section in SECTION_TO_TAB_MAP:
            old_tab_group = getattr(field, 'tab_group', None)
            new_tab_group = SECTION_TO_TAB_MAP[field.section]
            
            if old_tab_group != new_tab_group:
                field.tab_group = new_tab_group
                updates_made.append(f"  {field.name}: '{old_tab_group}' -> '{new_tab_group}' (section: {field.section})")
                
    if updates_made:
        print(f"✅ Updated {len(updates_made)} fields:")
        for update in updates_made:
            print(update)
    else:
        print("ℹ️ No updates needed - all fields already have correct tab_group")
    
    # Print summary
    print("\n📊 Field Distribution Summary:")
    tab_counts = {}
    for field in SUPPLIER_FIELDS:
        tab = getattr(field, 'tab_group', 'unknown')
        tab_counts[tab] = tab_counts.get(tab, 0) + 1
    
    for tab, count in sorted(tab_counts.items()):
        print(f"  {tab}: {count} fields")

if __name__ == "__main__":
    update_field_tab_groups()
    print("\n✅ Fields updated in memory. Now you need to update master_entities.py file.")
    print("   See the generated code below to copy into your file.")