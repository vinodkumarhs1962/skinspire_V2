# Layout Detection Logic Verification Guide
# File: verification_tests.py (create this for testing)

"""
Complete verification tests for layout detection logic
Run these tests to ensure layout detection works correctly
"""

def test_layout_detection():
    """
    Test that layout detection works correctly
    """
    from app.config.entity_configurations import SUPPLIER_PAYMENT_CONFIG, switch_layout_type
    from app.engine.data_assembler import EnhancedUniversalDataAssembler
    
    print("🧪 Testing Layout Detection Logic...")
    
    # Test 1: Verify layout switching works
    print("\n1. Testing Layout Switching:")
    
    # Test Simple Layout
    switch_layout_type('simple')
    layout_type = SUPPLIER_PAYMENT_CONFIG.view_layout.type.value
    print(f"   Simple Layout: {layout_type} ✅" if layout_type == 'simple' else f"   ❌ Failed: {layout_type}")
    
    # Test Tabbed Layout  
    switch_layout_type('tabbed')
    layout_type = SUPPLIER_PAYMENT_CONFIG.view_layout.type.value
    print(f"   Tabbed Layout: {layout_type} ✅" if layout_type == 'tabbed' else f"   ❌ Failed: {layout_type}")
    
    # Test Accordion Layout
    switch_layout_type('accordion') 
    layout_type = SUPPLIER_PAYMENT_CONFIG.view_layout.type.value
    print(f"   Accordion Layout: {layout_type} ✅" if layout_type == 'accordion' else f"   ❌ Failed: {layout_type}")
    
    # Test 2: Verify data assembler reads layout correctly
    print("\n2. Testing Data Assembler Layout Detection:")
    
    assembler = EnhancedUniversalDataAssembler()
    
    # Test each layout type
    for layout_name in ['simple', 'tabbed', 'accordion']:
        switch_layout_type(layout_name)
        detected_type = assembler._get_layout_type(SUPPLIER_PAYMENT_CONFIG)
        
        if detected_type == layout_name:
            print(f"   {layout_name.title()} Detection: ✅ Correctly detected as '{detected_type}'")
        else:
            print(f"   {layout_name.title()} Detection: ❌ Expected '{layout_name}', got '{detected_type}'")
    
    # Test 3: Verify field organization works
    print("\n3. Testing Field Organization by Layout:")
    
    # Create mock item data
    class MockItem:
        def __init__(self):
            self.payment_id = "PAY-001"
            self.reference_no = "REF-001"
            self.amount = 5000.00
            self.cash_amount = 2000.00
            self.cheque_amount = 3000.00
            self.supplier_name = "Test Supplier"
            self.created_at = "2024-01-01"
    
    mock_item = MockItem()
    
    for layout_name in ['simple', 'tabbed', 'accordion']:
        switch_layout_type(layout_name)
        
        try:
            sections = assembler._assemble_view_sections_from_fields(SUPPLIER_PAYMENT_CONFIG, mock_item)
            
            if sections and isinstance(sections, list):
                print(f"   {layout_name.title()} Organization: ✅ Generated {len(sections)} section(s)")
                
                # Check if sections have proper structure
                first_section = sections[0]
                if 'sections' in first_section and first_section['sections']:
                    print(f"      - Found {len(first_section['sections'])} subsections")
                    
                    # Check if fields are properly organized
                    total_fields = sum(len(section.get('fields', [])) for section in first_section['sections'])
                    print(f"      - Organized {total_fields} fields")
                else:
                    print(f"      - ❌ No subsections found")
                    
            else:
                print(f"   {layout_name.title()} Organization: ❌ Failed to generate sections")
                
        except Exception as e:
            print(f"   {layout_name.title()} Organization: ❌ Error: {str(e)}")
    
    # Test 4: Verify tab/section assignment works
    print("\n4. Testing Tab/Section Assignment:")
    
    switch_layout_type('tabbed')
    
    # Check if fields have proper tab_group and section assignments
    fields_with_tabs = [f for f in SUPPLIER_PAYMENT_CONFIG.fields if hasattr(f, 'tab_group') and f.tab_group]
    fields_with_sections = [f for f in SUPPLIER_PAYMENT_CONFIG.fields if hasattr(f, 'section') and f.section]
    
    print(f"   Fields with tab_group: {len(fields_with_tabs)} ✅")
    print(f"   Fields with section: {len(fields_with_sections)} ✅")
    
    # Show some examples
    if fields_with_tabs:
        example_field = fields_with_tabs[0]
        print(f"   Example: {example_field.name} -> tab:{example_field.tab_group}, section:{example_field.section}")
    
    print("\n🎯 Layout Detection Verification Complete!")

def test_conditional_display():
    """
    Test conditional display logic
    """
    print("\n🧪 Testing Conditional Display Logic...")
    
    from app.engine.data_assembler import EnhancedUniversalDataAssembler
    from app.config.entity_configurations import SUPPLIER_PAYMENT_CONFIG
    
    assembler = EnhancedUniversalDataAssembler()
    
    # Create test items with different conditions
    class MockItemWithCash:
        def __init__(self):
            self.cash_amount = 1000.00
            self.cheque_amount = 0
            self.cheque_number = None
    
    class MockItemWithoutCash:
        def __init__(self):
            self.cash_amount = 0
            self.cheque_amount = 0
            self.cheque_number = None
    
    # Test conditional display
    cash_item = MockItemWithCash()
    no_cash_item = MockItemWithoutCash()
    
    # Find field with conditional display
    conditional_fields = [f for f in SUPPLIER_PAYMENT_CONFIG.fields 
                         if hasattr(f, 'conditional_display') and f.conditional_display]
    
    if conditional_fields:
        test_field = conditional_fields[0]
        print(f"   Testing field: {test_field.name}")
        print(f"   Condition: {test_field.conditional_display}")
        
        # Test with cash item
        should_show_cash = assembler._should_display_field(test_field, cash_item)
        print(f"   With cash amount: {'✅ Shows' if should_show_cash else '❌ Hides'}")
        
        # Test without cash item  
        should_show_no_cash = assembler._should_display_field(test_field, no_cash_item)
        print(f"   Without cash amount: {'✅ Hides' if not should_show_no_cash else '❌ Shows'}")
    else:
        print("   ⚠️ No conditional fields found to test")

def run_all_verification_tests():
    """
    Run all verification tests
    """
    print("=" * 60)
    print("🚀 UNIVERSAL VIEW LAYOUT VERIFICATION TESTS")
    print("=" * 60)
    
    try:
        test_layout_detection()
        test_conditional_display()
        
        print("\n" + "=" * 60)
        print("✅ ALL VERIFICATION TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()

# Run verification if this file is executed directly
if __name__ == "__main__":
    run_all_verification_tests()