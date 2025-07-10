"""
Tests for universal view engine foundation
"""
# python -m pytest tests/test_universal_view_engine.py -v
import unittest
from app.config.entity_configurations import get_entity_config, list_entity_types
from app.config.field_definitions import FieldType
from app.engine.data_assembler import DataAssembler

class TestUniversalViewEngineFoundation(unittest.TestCase):
    """Test universal view engine foundation components"""
    
    def test_universal_view_engine_configuration_loading(self):
        """Test that entity configurations can be loaded"""
        # Test supplier payment configuration
        config = get_entity_config('supplier_payments')
        
        self.assertEqual(config.entity_type, 'supplier_payments')
        self.assertEqual(config.name, 'Supplier Payment')
        self.assertEqual(config.plural_name, 'Supplier Payments')
        self.assertTrue(len(config.fields) > 0)
        self.assertTrue(len(config.actions) > 0)
    
    def test_field_definitions(self):
        """Test field definitions"""
        config = get_entity_config('supplier_payments')
        
        # Check that payment_reference field exists and is configured correctly
        payment_ref_field = next((f for f in config.fields if f.name == 'payment_reference'), None)
        self.assertIsNotNone(payment_ref_field)
        self.assertEqual(payment_ref_field.field_type, FieldType.TEXT)
        self.assertTrue(payment_ref_field.show_in_list)
        self.assertTrue(payment_ref_field.searchable)
    
    def test_data_assembler(self):
        """Test data assembler functionality"""
        config = get_entity_config('supplier_payments')
        assembler = DataAssembler()
        
        # Test table column assembly
        columns = assembler.assemble_table_columns(config)
        self.assertIsInstance(columns, list)
        self.assertTrue(len(columns) > 0)
        
        # Check that columns have required properties
        for column in columns:
            self.assertIn('name', column)
            self.assertIn('label', column)
            self.assertIn('type', column)
    
    def test_entity_registry(self):
        """Test entity registry functionality"""
        entity_types = list_entity_types()
        self.assertIn('supplier_payments', entity_types)
    
    def test_search_form_assembly(self):
        """Test search form assembly"""
        config = get_entity_config('supplier_payments')
        assembler = DataAssembler()
        
        filters = {'search': 'test', 'payment_status': 'pending'}
        search_form = assembler.assemble_search_form(config, filters)
        
        self.assertIn('quick_search', search_form)
        self.assertIn('fields', search_form)
        self.assertEqual(search_form['quick_search']['value'], 'test')

if __name__ == '__main__':
    unittest.main()