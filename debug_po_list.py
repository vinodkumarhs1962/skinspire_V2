#!/usr/bin/env python
"""
Debug script for Purchase Order List Issues - V2
Run from project root: python debug_po_list.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.database_service import get_db_session
from app.models.transaction import PurchaseOrderHeader
from app.models.master import Supplier
import uuid

def debug_purchase_orders():
    """Debug purchase order list issues"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*80)
        print("PURCHASE ORDER DEBUG SCRIPT V2")
        print("="*80)
        
        with get_db_session() as session:
            # Get first PO with non-zero amount for testing
            pos = session.query(PurchaseOrderHeader).filter(
                PurchaseOrderHeader.total_amount > 0
            ).limit(1).all()
            
            if not pos:
                pos = session.query(PurchaseOrderHeader).limit(1).all()
            
            if not pos:
                print("No purchase orders found!")
                return
                
            test_po = pos[0]
            test_hospital_id = test_po.hospital_id
            
            print(f"\n1. TEST PO DATA:")
            print("-" * 40)
            print(f"PO Number: {test_po.po_number}")
            print(f"Total Amount: {test_po.total_amount}")
            print(f"Supplier: {test_po.supplier.supplier_name if test_po.supplier else 'None'}")
            print(f"Status: {test_po.status}")
            
            # Test the complete data flow
            print(f"\n2. TESTING COMPLETE DATA FLOW:")
            print("-" * 40)
            
            # Import the actual search function used by list view
            from app.engine.universal_services import search_universal_entity_data
            
            result = search_universal_entity_data(
                entity_type='purchase_orders',
                filters={},
                hospital_id=test_hospital_id,
                page=1,
                per_page=5
            )
            
            print(f"\nSearch result keys: {list(result.keys())}")
            print(f"Total items: {result.get('total', 0)}")
            
            if result.get('items'):
                print(f"\n3. FIRST ITEM IN LIST:")
                print("-" * 40)
                first_item = result['items'][0]
                print(f"PO Number: {first_item.get('po_number')}")
                print(f"Supplier Name: {first_item.get('supplier_name', 'KEY NOT FOUND')}")
                print(f"Supplier Name (repr): {repr(first_item.get('supplier_name', 'KEY NOT FOUND'))}")
                print(f"Total Amount: {first_item.get('total_amount')}")
                print(f"Status: {first_item.get('status')}")
                
                # Check all keys
                print(f"\nAll keys in first item:")
                for key in sorted(first_item.keys()):
                    if 'supplier' in key.lower() or 'amount' in key.lower():
                        print(f"  {key}: {first_item[key]}")
            
            # Test data assembler for list view
            print(f"\n4. TESTING DATA ASSEMBLER FOR LIST VIEW:")
            print("-" * 40)
            
            from app.engine.data_assembler import EnhancedUniversalDataAssembler
            from flask_login import current_user
            
            assembler = EnhancedUniversalDataAssembler()
            
            # Mock a user if needed
            class MockUser:
                def __init__(self):
                    self.hospital_id = test_hospital_id
                    self.branch_id = None
                    self.is_authenticated = True
            
            # Test list data assembly
            list_data = assembler.assemble_list_data(
                entity_type='purchase_orders',
                hospital_id=test_hospital_id,
                branch_id=None,
                filters={},
                page=1,
                per_page=5,
                user=MockUser()
            )
            
            print(f"\nList data keys: {list(list_data.keys())}")
            
            if list_data.get('items'):
                print(f"\n5. FIRST ITEM FROM ASSEMBLER:")
                print("-" * 40)
                first_item = list_data['items'][0]
                print(f"PO Number: {first_item.get('po_number')}")
                print(f"Supplier Name: {first_item.get('supplier_name', 'KEY NOT FOUND')}")
                print(f"Total Amount: {first_item.get('total_amount')}")
                print(f"Status: {first_item.get('status')}")
            
            # Check field configuration
            print(f"\n6. CHECKING FIELD CONFIGURATION:")
            print("-" * 40)
            
            from app.config.modules.purchase_orders_config import PURCHASE_ORDER_FIELDS
            
            # Find supplier_name field
            supplier_field = None
            total_field = None
            
            for field in PURCHASE_ORDER_FIELDS:
                if field.name == 'supplier_name':
                    supplier_field = field
                elif field.name == 'total_amount':
                    total_field = field
            
            if supplier_field:
                print(f"\nSupplier name field config:")
                print(f"  show_in_list: {supplier_field.show_in_list}")
                print(f"  virtual: {getattr(supplier_field, 'virtual', False)}")
                print(f"  default_value: {getattr(supplier_field, 'default_value', 'NO DEFAULT')}")
            
            if total_field:
                print(f"\nTotal amount field config:")
                print(f"  show_in_list: {total_field.show_in_list}")
                print(f"  field_type: {total_field.field_type}")
                print(f"  default_value: {getattr(total_field, 'default_value', 'NO DEFAULT')}")
            
            # Check if there's a default value being set
            print(f"\n7. CHECKING FOR DEFAULT VALUES:")
            print("-" * 40)
            
            # Check if "—" is set anywhere
            em_dash = "—"
            em_dash_encoded = em_dash.encode('utf-8')
            print(f"Em dash character: {repr(em_dash)}")
            print(f"Em dash encoded: {em_dash_encoded}")
            print(f"Em dash in hex: {em_dash_encoded.hex()}")
            
            # The "â€"" is the UTF-8 bytes of em dash being incorrectly interpreted as Windows-1252
            incorrect_display = em_dash_encoded.decode('windows-1252', errors='ignore')
            print(f"Em dash incorrectly decoded as Windows-1252: {repr(incorrect_display)}")
            
            # Check filter options
            print(f"\n8. CHECKING STATUS FILTER OPTIONS:")
            print("-" * 40)
            
            filter_data = assembler.assemble_filter_data(
                'purchase_orders',
                test_hospital_id,
                None
            )
            
            if filter_data and filter_data.get('universal_filters'):
                for f in filter_data['universal_filters']:
                    if f.get('name') == 'status':
                        print(f"Status filter type: {f.get('type')}")
                        print(f"Status filter options: {f.get('options')}")
                        break

if __name__ == '__main__':
    debug_purchase_orders()