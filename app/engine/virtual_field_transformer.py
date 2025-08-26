# Enhanced app/engine/virtual_field_transformer.py
# Handles type conversion for boolean, numeric, and other fields

"""
Virtual Field Transformer for Universal Engine
Handles transformation of virtual fields to actual database fields
Following Universal Engine principles: Entity-agnostic, Configuration-driven
"""

from typing import Dict, Any, Optional
from app.config.core_definitions import EntityConfiguration, FieldType
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class VirtualFieldTransformer:
    """
    Generic virtual field transformer that uses field configuration
    to automatically handle virtual fields for any entity.
    
    This is the ultimate universal solution - no entity-specific code needed!
    """
    
    @staticmethod
    def convert_field_value(value: Any, field_def: Any) -> Any:
        """
        Convert form value to appropriate type based on field definition.
        Handles empty strings, None values, and type conversions.
        """
        if field_def is None:
            return value
            
        field_type = getattr(field_def, 'field_type', None)
        
        # Handle None or empty string values
        if value is None or value == '':
            # Boolean fields should default to False
            if field_type == FieldType.BOOLEAN:
                return False
            # Numeric fields should be None if empty
            elif field_type in [FieldType.NUMBER, FieldType.INTEGER, FieldType.DECIMAL, FieldType.CURRENCY]:
                return None
            # For other types, empty string becomes None
            elif value == '':
                return None
            else:
                return value
        
        # Type conversions for non-empty values
        try:
            if field_type == FieldType.BOOLEAN:
                # Handle various boolean representations
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1', 'on', 'checked')
                return bool(value)
                
            elif field_type == FieldType.NUMBER or field_type == FieldType.INTEGER:
                # Convert to integer
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, str) and value.strip():
                    return int(float(value.strip()))
                return None
                
            elif field_type in [FieldType.DECIMAL, FieldType.CURRENCY]:
                # Convert to float
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str) and value.strip():
                    # Remove currency symbols if present
                    cleaned = value.strip().replace('₹', '').replace('$', '').replace(',', '')
                    return float(cleaned) if cleaned else None
                return None
                
            # No conversion needed for text fields
            return value
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Type conversion failed for field {getattr(field_def, 'name', 'unknown')}: {e}")
            # Return None for failed numeric conversions
            if field_type in [FieldType.NUMBER, FieldType.INTEGER, FieldType.DECIMAL, FieldType.CURRENCY]:
                return None
            return value
    
    @staticmethod
    def transform_for_create(form_data: dict, config: EntityConfiguration) -> dict:
        """
        Transform form data with virtual fields into entity data for creation.
        Uses field definitions to determine how to map virtual fields.
        Now includes type conversion for all fields.
        """
        entity_data = {}
        jsonb_accumulator = {}  # Accumulate JSONB fields
        
        # Get field definitions map
        field_definitions = {field.name: field for field in config.fields}
        
        # Process each form field
        for field_name, value in form_data.items():
            field_def = field_definitions.get(field_name)
            
            # Convert value to appropriate type
            converted_value = VirtualFieldTransformer.convert_field_value(value, field_def)
            
            if not field_def:
                # Unknown field - could be a system field, add it with converted value
                if field_name not in ['hospital_id', 'branch_id', 'created_at', 'created_by']:
                    entity_data[field_name] = converted_value
                continue
            
            if getattr(field_def, 'virtual', False):
                # Virtual field - check mapping configuration
                target = getattr(field_def, 'virtual_target', None)
                key = getattr(field_def, 'virtual_key', field_name)
                
                if target:
                    # Accumulate in JSONB field
                    if target not in jsonb_accumulator:
                        jsonb_accumulator[target] = {}
                    # Only add non-None values to JSONB
                    if converted_value is not None and converted_value != '':
                        jsonb_accumulator[target][key] = converted_value
                else:
                    # No target specified - try common patterns
                    entity_data = VirtualFieldTransformer._apply_common_patterns(
                        entity_data, field_name, converted_value, config, jsonb_accumulator
                    )
            else:
                # Regular field - add directly with converted value
                entity_data[field_name] = converted_value
        
        # Add accumulated JSONB fields to entity data
        for jsonb_field, jsonb_data in jsonb_accumulator.items():
            if jsonb_data:  # Only add if has data
                entity_data[jsonb_field] = jsonb_data
            else:
                entity_data[jsonb_field] = None  # Set to None if empty
        
        logger.info(f"✅ Transformed {len(form_data)} form fields into {len(entity_data)} entity fields")
        return entity_data
    
    @staticmethod
    def transform_for_update(form_data: dict, existing_entity: Any, config: EntityConfiguration) -> dict:
        """
        Transform form data with virtual fields for update.
        CRITICAL: Preserves existing JSONB data and merges with updates.
        """
        entity_data = {}
        jsonb_accumulator = {}
        
        # Get field definitions
        field_definitions = {field.name: field for field in config.fields}
        
        # Helper to get existing value from entity
        def get_entity_value(entity, attr_name):
            if isinstance(entity, dict):
                return entity.get(attr_name)
            elif hasattr(entity, attr_name):
                return getattr(entity, attr_name)
            return None
        
        # CRITICAL FIX: Pre-populate accumulators with existing JSONB data
        for jsonb_field in ['contact_info', 'supplier_address', 'bank_details', 'manager_contact_info']:
            existing_value = get_entity_value(existing_entity, jsonb_field)
            if existing_value:
                # Deep copy existing data
                if isinstance(existing_value, dict):
                    jsonb_accumulator[jsonb_field] = existing_value.copy()
                elif isinstance(existing_value, str):
                    try:
                        import json
                        jsonb_accumulator[jsonb_field] = json.loads(existing_value)
                    except:
                        jsonb_accumulator[jsonb_field] = {}
                else:
                    jsonb_accumulator[jsonb_field] = {}
        
        # Process each form field
        for field_name, value in form_data.items():
            field_def = field_definitions.get(field_name)
            
            # Convert value to appropriate type
            converted_value = VirtualFieldTransformer.convert_field_value(value, field_def)
            
            if not field_def:
                # Unknown field - could be a system field
                if field_name not in ['hospital_id', 'branch_id', 'created_at', 'created_by']:
                    entity_data[field_name] = converted_value
                continue
            
            if getattr(field_def, 'virtual', False):
                # Virtual field - update JSONB
                target = getattr(field_def, 'virtual_target', None)
                key = getattr(field_def, 'virtual_key', field_name)
                
                if target:
                    # Ensure accumulator exists
                    if target not in jsonb_accumulator:
                        jsonb_accumulator[target] = {}
                    
                    # Update or remove value
                    if converted_value is not None and converted_value != '':
                        jsonb_accumulator[target][key] = converted_value
                    elif key in jsonb_accumulator[target]:
                        # Remove empty values
                        del jsonb_accumulator[target][key]
                else:
                    # Apply common patterns
                    entity_data = VirtualFieldTransformer._apply_common_patterns(
                        entity_data, field_name, converted_value, config, jsonb_accumulator
                    )
            else:
                # Regular field
                entity_data[field_name] = converted_value
        
        # Add all JSONB fields to entity data (even if unchanged)
        for jsonb_field, jsonb_data in jsonb_accumulator.items():
            entity_data[jsonb_field] = jsonb_data if jsonb_data else None
        
        # CRITICAL: Log what we're updating
        logger.info(f"✅ Transform complete - JSONB fields being updated:")
        for field in ['contact_info', 'supplier_address', 'bank_details', 'manager_contact_info']:
            if field in entity_data:
                logger.info(f"  {field}: {len(entity_data[field])} keys" if entity_data[field] else f"  {field}: empty")
        
        return entity_data
    
    @staticmethod
    def extract_virtual_fields_for_display(entity: Any, config: EntityConfiguration) -> dict:
        """
        Extract virtual fields from JSONB columns for display in edit form.
        Handles both dict and object entities.
        """
        virtual_data = {}
        field_definitions = {field.name: field for field in config.fields}
        
        # Helper function to get value from entity (dict or object)
        def get_entity_value(entity, attr_name):
            if isinstance(entity, dict):
                return entity.get(attr_name)
            elif hasattr(entity, attr_name):
                return getattr(entity, attr_name)
            return None
        
        for field_name, field_def in field_definitions.items():
            if getattr(field_def, 'virtual', False):
                # Get the target JSONB field and key
                target = getattr(field_def, 'virtual_target', None)
                key = getattr(field_def, 'virtual_key', field_name)
                
                if target:
                    jsonb_value = get_entity_value(entity, target)
                    if jsonb_value:
                        # Handle both dict and JSON string
                        if isinstance(jsonb_value, str):
                            try:
                                import json
                                jsonb_value = json.loads(jsonb_value)
                            except:
                                continue
                        
                        if isinstance(jsonb_value, dict):
                            virtual_data[field_name] = jsonb_value.get(key, '')
                else:
                    # Try common patterns based on field name
                    if field_name in ['phone', 'mobile', 'fax']:
                        contact_info = get_entity_value(entity, 'contact_info')
                        if contact_info and isinstance(contact_info, dict):
                            virtual_data[field_name] = contact_info.get(field_name, '')
                    
                    elif field_name in ['address', 'city', 'state', 'country', 'pincode']:
                        # For suppliers, it's supplier_address
                        address_field = f"{config.entity_type.rstrip('s')}_address"
                        address_info = get_entity_value(entity, address_field)
                        if address_info and isinstance(address_info, dict):
                            virtual_data[field_name] = address_info.get(field_name, '')
                    
                    elif field_name in ['bank_name', 'bank_account_number', 'bank_account_name', 
                                    'ifsc_code', 'bank_branch']:
                        bank_info = get_entity_value(entity, 'bank_details')
                        if bank_info and isinstance(bank_info, dict):
                            # Map field names to JSONB keys
                            key_map = {
                                'bank_name': 'bank_name',
                                'bank_account_number': 'account_number',
                                'bank_account_name': 'account_name',
                                'ifsc_code': 'ifsc_code',
                                'bank_branch': 'branch'
                            }
                            mapped_key = key_map.get(field_name, field_name)
                            virtual_data[field_name] = bank_info.get(mapped_key, '')
                    
                    elif field_name.startswith('manager_'):
                        # Manager contact fields
                        manager_info = get_entity_value(entity, 'manager_contact_info')
                        if manager_info and isinstance(manager_info, dict):
                            # Remove 'manager_' prefix to get the key
                            key = field_name.replace('manager_', '')
                            virtual_data[field_name] = manager_info.get(key, '')
        
        logger.info(f"✅ Extracted {len(virtual_data)} virtual fields for display")
        return virtual_data

    @staticmethod
    def _apply_common_patterns(entity_data: dict, field_name: str, value: Any, 
                              config: EntityConfiguration, jsonb_accumulator: dict) -> dict:
        """
        Apply common virtual field patterns when no explicit mapping is configured.
        This handles common cases like phone->contact_info, city->address, etc.
        
        Enhanced to handle supplier-specific patterns.
        """
        
        # Common patterns for virtual fields
        patterns = {
            # Contact fields -> contact_info
            'phone': ('contact_info', 'phone'),
            'mobile': ('contact_info', 'mobile'),
            'fax': ('contact_info', 'fax'),
            'telephone': ('contact_info', 'telephone'),
            
            # Manager contact fields -> manager_contact_info
            'manager_phone': ('manager_contact_info', 'phone'),
            'manager_mobile': ('manager_contact_info', 'mobile'),
            'manager_email': ('manager_contact_info', 'email'),
            'manager_fax': ('manager_contact_info', 'fax'),
            
            # Address fields -> entity-specific address JSONB
            'address': (f'{config.entity_type.rstrip("s")}_address', 'address'),
            'city': (f'{config.entity_type.rstrip("s")}_address', 'city'),
            'state': (f'{config.entity_type.rstrip("s")}_address', 'state'),
            'country': (f'{config.entity_type.rstrip("s")}_address', 'country'),
            'pincode': (f'{config.entity_type.rstrip("s")}_address', 'pincode'),
            'zip': (f'{config.entity_type.rstrip("s")}_address', 'zip'),
            
            # Bank fields -> bank_details (with alternate key names)
            'bank_name': ('bank_details', 'bank_name'),
            'bank_account_number': ('bank_details', 'account_number'),
            'bank_account_name': ('bank_details', 'account_name'),
            'account_number': ('bank_details', 'account_number'),
            'account_name': ('bank_details', 'account_name'),
            'ifsc_code': ('bank_details', 'ifsc_code'),
            'bank_ifsc_code': ('bank_details', 'ifsc_code'),
            'bank_branch': ('bank_details', 'branch'),
            'branch': ('bank_details', 'branch'),
            
            # GST/Tax fields (direct mapping with name change)
            'gst_number': ('gst_registration_number', None),
            'gstin': ('gst_registration_number', None),
            'pan': ('pan_number', None),
        }
        
        if field_name in patterns:
            target, key = patterns[field_name]
            
            if key:  # JSONB field
                if target not in jsonb_accumulator:
                    jsonb_accumulator[target] = {}
                if value is not None and value != '':
                    jsonb_accumulator[target][key] = value
            else:  # Direct field with different name
                entity_data[target] = value
        
        return entity_data