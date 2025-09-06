#!/usr/bin/env python
"""
Debug script to trace supplier_name field through Universal Engine
Run this from Flask shell:
    flask shell
    exec(open('debug_supplier_name.py').read())
"""

import uuid
from pprint import pprint
from app.services.database_service import get_db_session, get_entity_dict
from app.config.entity_configurations import get_entity_config
from app.engine.universal_services import get_universal_service
from app.engine.data_assembler import EnhancedUniversalDataAssembler
from app.models.views import SupplierPaymentView, PurchaseOrderView
from flask_login import current_user

def debug_supplier_name(entity_type='supplier_payments', item_id=None):
    """
    Debug the supplier_name field flow through the Universal Engine
    
    Args:
        entity_type: 'supplier_payments' or 'purchase_orders'
        item_id: Optional specific item ID to test, otherwise uses first available
    """
    print("\n" + "="*80)
    print(f"DEBUGGING SUPPLIER NAME FOR: {entity_type}")
    print("="*80)
    
    # Step 1: Check the database view directly
    print("\n1. DATABASE VIEW CHECK")
    print("-"*40)
    
    with get_db_session() as session:
        if entity_type == 'supplier_payments':
            model_class = SupplierPaymentView
        elif entity_type == 'purchase_orders':
            model_class = PurchaseOrderView
        else:
            print(f"Unknown entity type: {entity_type}")
            return
        
        # Get a sample record
        if item_id:
            if isinstance(item_id, str):
                item_id = uuid.UUID(item_id)
            item = session.query(model_class).filter(
                model_class.payment_id == item_id if entity_type == 'supplier_payments' 
                else model_class.po_id == item_id
            ).first()
        else:
            # Get first available item
            item = session.query(model_class).first()
        
        if not item:
            print("❌ No items found in database")
            return
        
        # Check what fields the view has
        print(f"✅ Found item in {model_class.__tablename__}")
        print(f"   Primary key: {item.payment_id if entity_type == 'supplier_payments' else item.po_id}")
        
        # Check supplier_name specifically
        if hasattr(item, 'supplier_name'):
            print(f"   ✅ supplier_name field exists: '{item.supplier_name}'")
        else:
            print(f"   ❌ supplier_name field NOT in model")
            print(f"   Available columns: {[c.name for c in model_class.__table__.columns]}")
        
        item_id = item.payment_id if entity_type == 'supplier_payments' else item.po_id
    
    # Step 2: Check entity configuration
    print("\n2. ENTITY CONFIGURATION CHECK")
    print("-"*40)
    
    config = get_entity_config(entity_type)
    if not config:
        print(f"❌ No configuration found for {entity_type}")
        return
    
    print(f"✅ Configuration loaded")
    print(f"   title_field: {config.title_field}")
    print(f"   subtitle_field: {config.subtitle_field}")
    
    # Check header_config
    if config.view_layout and config.view_layout.header_config:
        header_config = config.view_layout.header_config
        print(f"\n   Header Configuration:")
        print(f"   - title_field: {header_config.get('title_field')}")
        print(f"   - title_label: {header_config.get('title_label')}")
        print(f"   - primary_field: {header_config.get('primary_field')}")
        print(f"   - status_field: {header_config.get('status_field')}")
    
    # Check if supplier_name is in fields
    supplier_name_field = None
    for field in config.fields:
        if field.name == 'supplier_name':
            supplier_name_field = field
            break
    
    if supplier_name_field:
        print(f"\n   ✅ supplier_name field in configuration:")
        print(f"   - label: {supplier_name_field.label}")
        print(f"   - field_type: {supplier_name_field.field_type}")
        print(f"   - virtual: {getattr(supplier_name_field, 'virtual', False)}")
        print(f"   - show_in_detail: {supplier_name_field.show_in_detail}")
    else:
        print(f"   ⚠️  supplier_name NOT in field definitions")
    
    # Step 3: Check Universal Service
    print("\n3. UNIVERSAL SERVICE CHECK")
    print("-"*40)
    
    service = get_universal_service(entity_type)
    print(f"✅ Service loaded: {service.__class__.__name__}")
    
    # Test get_by_id through service
    try:
        result = service.get_by_id(str(item_id), hospital_id=current_user.hospital_id if current_user else None)
        
        if result:
            print(f"✅ Service returned data")
            print(f"   Result keys: {result.keys()}")
            
            if 'item' in result:
                item_dict = result['item']
                print(f"   Item type: {type(item_dict)}")
                print(f"   Item keys (first 10): {list(item_dict.keys())[:10]}")
                
                if 'supplier_name' in item_dict:
                    print(f"   ✅ supplier_name in item: '{item_dict['supplier_name']}'")
                else:
                    print(f"   ❌ supplier_name NOT in item dict")
                    print(f"   Available keys with 'supplier': {[k for k in item_dict.keys() if 'supplier' in k.lower()]}")
        else:
            print(f"❌ Service returned None")
    except Exception as e:
        print(f"❌ Error calling service: {e}")
    
    # Step 4: Check Data Assembler
    print("\n4. DATA ASSEMBLER CHECK")
    print("-"*40)
    
    assembler = EnhancedUniversalDataAssembler()
    
    if result:
        try:
            assembled = assembler.assemble_universal_view_data(
                config=config,
                raw_item_data=result,
                hospital_id=current_user.hospital_id if current_user else None
            )
            
            print(f"✅ Data assembled")
            print(f"   Assembled keys: {assembled.keys()}")
            
            if 'item' in assembled:
                item = assembled['item']
                if 'supplier_name' in item:
                    print(f"   ✅ supplier_name in assembled item: '{item['supplier_name']}'")
                else:
                    print(f"   ❌ supplier_name NOT in assembled item")
            
            if 'header_config' in assembled:
                hc = assembled['header_config']
                print(f"\n   Header config in assembled data:")
                print(f"   - title_field: {hc.get('title_field')}")
                print(f"   - Value would be: {assembled.get('item', {}).get(hc.get('title_field'), 'NOT FOUND')}")
                
        except Exception as e:
            print(f"❌ Error assembling data: {e}")
    
    # Step 5: Direct database to dict conversion check
    print("\n5. DATABASE TO DICT CONVERSION CHECK")
    print("-"*40)
    
    with get_db_session() as session:
        if entity_type == 'supplier_payments':
            item = session.query(SupplierPaymentView).filter(
                SupplierPaymentView.payment_id == item_id
            ).first()
        else:
            item = session.query(PurchaseOrderView).filter(
                PurchaseOrderView.po_id == item_id
            ).first()
        
        if item:
            # Test get_entity_dict function
            item_dict = get_entity_dict(item)
            print(f"✅ Used get_entity_dict")
            print(f"   Dict keys (first 10): {list(item_dict.keys())[:10]}")
            
            if 'supplier_name' in item_dict:
                print(f"   ✅ supplier_name in dict: '{item_dict['supplier_name']}'")
            else:
                print(f"   ❌ supplier_name NOT in dict")
                
                # Try manual extraction
                if hasattr(item, 'supplier_name'):
                    print(f"   ⚠️  But item.supplier_name exists: '{item.supplier_name}'")
                    print(f"   This means get_entity_dict is not extracting it properly")
    
    print("\n" + "="*80)
    print("DIAGNOSIS SUMMARY")
    print("="*80)
    
    # Provide diagnosis
    if 'supplier_name' not in item_dict:
        print("❌ PROBLEM: supplier_name is not being extracted from database model to dict")
        print("   SOLUTION: Check get_entity_dict function in database_service.py")
    elif result and 'supplier_name' not in result.get('item', {}):
        print("❌ PROBLEM: Service is not returning supplier_name")
        print("   SOLUTION: Check service's get_by_id method")
    elif assembled and 'supplier_name' not in assembled.get('item', {}):
        print("❌ PROBLEM: Data assembler is not preserving supplier_name")
        print("   SOLUTION: Check data_assembler.py")
    else:
        print("✅ supplier_name is flowing through the system correctly")
        print("   The issue might be in the template rendering")

# Function to test both entities
def test_all():
    """Test both supplier payments and purchase orders"""
    print("\n" + "#"*80)
    print("TESTING SUPPLIER PAYMENTS")
    print("#"*80)
    debug_supplier_name('supplier_payments')
    
    print("\n" + "#"*80)
    print("TESTING PURCHASE ORDERS")
    print("#"*80)
    debug_supplier_name('purchase_orders')

# Function to test specific item
def test_specific(entity_type, item_id):
    """Test a specific item by ID"""
    debug_supplier_name(entity_type, item_id)

# Print usage instructions
print("""
Debug Script Loaded! Usage:
---------------------------
1. Test supplier payments (first available):
   >>> debug_supplier_name('supplier_payments')

2. Test purchase orders (first available):
   >>> debug_supplier_name('purchase_orders')

3. Test specific item by ID:
   >>> test_specific('supplier_payments', 'your-payment-id-here')
   >>> test_specific('purchase_orders', 'your-po-id-here')

4. Test both entities:
   >>> test_all()
""")