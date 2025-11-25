# app/engine/universal_crud_service.py
"""
Universal CRUD Service - Convention-Based Approach
Uses simple service_module configuration with naming conventions
"""

import importlib
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config.core_definitions import (
    EntityConfiguration, EntityCategory, CRUDOperation
)
from app.engine.virtual_field_transformer import VirtualFieldTransformer
from app.services.database_service import get_db_session
from app.engine.universal_service_cache import invalidate_service_cache_for_entity
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalCRUDService:
    """
    Convention-based CRUD service
    Expects service functions named: create_{entity_type}, update_{entity_type}, delete_{entity_type}
    """
    
    def __init__(self):
        self.model_cache = {}
        self.service_cache = {}
        
    def _get_entity_config(self, entity_type: str) -> EntityConfiguration:
        """Get entity configuration"""
        try:
            from app.config.entity_configurations import get_entity_config
            return get_entity_config(entity_type)
        except Exception as e:
            logger.error(f"Failed to get config for {entity_type}: {e}")
            raise ValueError(f"Entity type '{entity_type}' not configured")
    
    def _validate_entity_category(self, config: EntityConfiguration, operation: CRUDOperation):
        """Validate if operation is allowed"""
        if config.entity_category != EntityCategory.MASTER:
            raise ValueError(f"Entity {config.entity_type} is not a master entity")
        
        if not getattr(config, 'universal_crud_enabled', False):
            raise ValueError(f"Universal CRUD not enabled for {config.entity_type}")
        
        allowed_ops = getattr(config, 'allowed_operations', [])
        if allowed_ops and operation not in allowed_ops:
            raise ValueError(f"Operation {operation.value} not allowed for {config.entity_type}")
    
    def _get_service_function(self, config: EntityConfiguration, operation: str) -> Optional[Callable]:
        """
        Get entity-specific service function using conventions
        Expects: create_{entity_type}, update_{entity_type}, delete_{entity_type}
        """
        cache_key = f"{config.entity_type}_{operation}"
        if cache_key in self.service_cache:
            return self.service_cache[cache_key]
        
        # Check if service module is configured
        service_module_path = getattr(config, 'service_module', None)
        if not service_module_path:
            logger.debug(f"No service module configured for {config.entity_type}")
            return None
        
        try:
            # Build function name using convention
            # entity_type is plural (e.g., 'suppliers'), need singular for function
            entity_singular = config.entity_type.rstrip('s')  # Simple singularization
            function_name = f"{operation}_{entity_singular}"
            
            logger.info(f"Looking for {service_module_path}.{function_name}")
            
            # Import module and get function
            module = importlib.import_module(service_module_path)
            function = getattr(module, function_name)
            
            # Cache for future use
            self.service_cache[cache_key] = function
            logger.info(f"Found and cached service function: {function_name}")
            return function
            
        except (ImportError, AttributeError) as e:
            logger.debug(f"No service function {function_name} in {service_module_path}: {e}")
            return None
    
    def _get_branch_id(self, context: Dict) -> uuid.UUID:
        """Get branch_id from context"""
        try:
            # Try provided branch_id first
            branch_id = context.get('branch_id')
            if branch_id:
                return branch_id
            
            # Use branch service
            from app.services.branch_service import get_branch_for_supplier_operation
            
            determined_branch_id = get_branch_for_supplier_operation(
                current_user_id=context.get('user_id'),
                hospital_id=context.get('hospital_id'),
                specified_branch_id=None
            )
            
            if not determined_branch_id:
                # Fallback to user's staff branch
                from app.models.master import Staff
                from app.models.transaction import User
                
                with get_db_session() as session:
                    user = session.query(User).filter_by(
                        user_id=context.get('user_id'),
                        hospital_id=context.get('hospital_id')
                    ).first()
                    
                    if user and user.entity_type == 'staff' and user.entity_id:
                        staff = session.query(Staff).filter_by(
                            staff_id=user.entity_id,
                            hospital_id=context.get('hospital_id')
                        ).first()
                        if staff and staff.branch_id:
                            determined_branch_id = staff.branch_id
            
            if not determined_branch_id:
                raise ValueError("Could not determine branch_id")
            
            logger.info(f"Determined branch_id: {determined_branch_id}")
            return determined_branch_id
            
        except Exception as e:
            logger.error(f"Error getting branch_id: {str(e)}")
            raise ValueError(f"Failed to determine branch: {str(e)}")
    
    def _load_model_class(self, config: EntityConfiguration):
        """Dynamically load model class from entity registry"""
        from app.config.entity_registry import get_entity_registration

        # Get model path from registry (not config)
        registration = get_entity_registration(config.entity_type)
        if not registration or not registration.model_class:
            raise ValueError(f"No model class configured for {config.entity_type}")

        model_path = registration.model_class

        if model_path in self.model_cache:
            return self.model_cache[model_path]

        try:
            parts = model_path.rsplit('.', 1)
            module = importlib.import_module(parts[0])
            model_class = getattr(module, parts[1])
            self.model_cache[model_path] = model_class
            logger.info(f"Loaded model class for {config.entity_type}: {model_path}")
            return model_class
        except Exception as e:
            logger.error(f"Failed to load model {model_path}: {e}")
            raise ValueError(f"Could not load model class: {model_path}")
    
    def create_entity(self, entity_type: str, data: dict, context: dict):
        """
        Create new entity
        Tries entity-specific service first, falls back to generic CRUD
        """
        try:
            logger.info(f"Creating {entity_type} with Universal CRUD Service")
            
            # Get configuration
            config = self._get_entity_config(entity_type)
            
            # Validate operation
            self._validate_entity_category(config, CRUDOperation.CREATE)
            
            # Try entity-specific service using convention
            service_function = self._get_service_function(config, 'create')
            if service_function:
                logger.info(f"Using entity-specific service for {entity_type}")
                
                # Prepare standardized arguments for service
                # Entity services should accept these standard parameters
                service_args = {
                    'hospital_id': context['hospital_id'],
                    'current_user_id': context.get('user_id')
                }
                
                # Add data with entity-specific key
                entity_singular = config.entity_type.rstrip('s')
                service_args[f'{entity_singular}_data'] = data
                
                # Call service function
                return service_function(**service_args)
            
            # Generic CRUD implementation
            logger.info(f"Using generic CRUD for {entity_type}")

            # Load model class first to check if branch_id is needed
            model_class = self._load_model_class(config)

            # Get branch_id only if the model has this field
            branch_id = None
            if hasattr(model_class, 'branch_id'):
                branch_id = self._get_branch_id(context)

            with get_db_session() as session:
                # Transform form data using VirtualFieldTransformer
                transformer = VirtualFieldTransformer()
                transformed_data = transformer.transform_for_create(data, config)

                # Prepare entity data
                entity_data = {}

                # Set primary key
                pk_field = getattr(config, 'primary_key', None) or getattr(config, 'primary_key_field', 'id')
                entity_data[pk_field] = uuid.uuid4()

                # Set required system fields
                entity_data['hospital_id'] = context['hospital_id']

                # Only set branch_id if the model has this field
                if hasattr(model_class, 'branch_id') and branch_id:
                    entity_data['branch_id'] = branch_id
                
                # Process transformed fields (now handles virtual fields properly)
                create_fields = getattr(config, 'create_fields', None)
                if not create_fields:
                    create_fields = [f.name for f in config.fields if f.show_in_form]
                field_definitions = {field.name: field for field in config.fields}

                for field_name in create_fields:
                    # Check if field is virtual
                    field_def = field_definitions.get(field_name)
                    is_virtual = getattr(field_def, 'virtual', False) if field_def else False

                    if not is_virtual and field_name in transformed_data:
                        # Regular field from transformed data
                        entity_data[field_name] = transformed_data[field_name]
                    elif not is_virtual and field_name in data:
                        # Regular field from original data (fallback)
                        entity_data[field_name] = data[field_name]
                    # Virtual fields are already handled in transformed_data as JSONB

                # Also check for hidden required fields from form data (e.g., package_id from query params)
                # These fields have show_in_form=False but are required and passed as hidden fields
                for field_name in data.keys():
                    if field_name not in entity_data and field_name in field_definitions:
                        field_def = field_definitions[field_name]
                        is_virtual = getattr(field_def, 'virtual', False)
                        if not is_virtual and field_def.required and not field_def.show_in_form:
                            entity_data[field_name] = data[field_name]
                            logger.info(f"Added hidden required field: {field_name}={data[field_name]}")

                # Add JSONB fields from transformation
                jsonb_fields = ['contact_info', 'supplier_address', 'bank_details', 'manager_contact_info']
                for jsonb_field in jsonb_fields:
                    if jsonb_field in transformed_data:
                        entity_data[jsonb_field] = transformed_data[jsonb_field]
                
                # Apply default values from configuration
                default_values = getattr(config, 'default_field_values', {})
                for field_name, default_value in default_values.items():
                    if field_name not in entity_data:
                        entity_data[field_name] = default_value
                
                # ========== SPECIAL HANDLING FOR PACKAGE BOM ITEMS ==========
                if config.entity_type == 'package_bom_items':
                    # 1. Calculate line_total
                    quantity = float(entity_data.get('quantity', 0))
                    current_price = float(entity_data.get('current_price', 0))
                    entity_data['line_total'] = quantity * current_price

                    # 2. Set default item_id if not provided (temporary workaround)
                    # TODO: Look up actual item by item_name and item_type
                    if 'item_id' not in entity_data or not entity_data['item_id']:
                        # Use a fixed UUID for now (should be looked up from services/medicines/etc)
                        entity_data['item_id'] = uuid.UUID('00000000-0000-0000-0000-000000000001')
                        logger.warning(f"⚠️ Using dummy item_id for BOM item - needs proper item lookup")

                # Add audit fields
                entity_data['created_at'] = datetime.now(timezone.utc)
                entity_data['created_by'] = context.get('user_id')
                entity_data['updated_at'] = datetime.now(timezone.utc)

                # Create entity
                entity = model_class(**entity_data)
                session.add(entity)
                session.commit()
                
                logger.info(f"Created {entity_type} with ID {entity_data[pk_field]}")
                invalidate_service_cache_for_entity(entity_type, cascade=True)
                return entity
                
        except IntegrityError as e:
            logger.error(f"Integrity error creating {entity_type}: {e}")
            if 'duplicate' in str(e).lower():
                raise ValueError("Duplicate record exists")
            elif 'not-null' in str(e).lower():
                raise ValueError(f"Missing required field: {str(e.orig)}")
            else:
                raise ValueError(f"Data integrity error: {str(e.orig)}")
        except Exception as e:
            logger.error(f"Error creating {entity_type}: {e}")
            raise
    
    def update_entity(self, entity_type: str, item_id: str, data: dict, context: dict):
        """
        Update entity
        Tries entity-specific service first, falls back to generic CRUD
        """
        try:
            logger.info(f"Updating {entity_type}/{item_id}")
            
            config = self._get_entity_config(entity_type)
            self._validate_entity_category(config, CRUDOperation.UPDATE)
            
            # Try entity-specific service
            service_function = self._get_service_function(config, 'update')
            if service_function:
                logger.info(f"Using entity-specific service for {entity_type}")
                
                # Prepare standardized arguments
                entity_singular = config.entity_type.rstrip('s')
                service_args = {
                    f'{entity_singular}_id': item_id,
                    f'{entity_singular}_data': data,
                    'hospital_id': context['hospital_id'],
                    'current_user_id': context.get('user_id')
                }
                
                return service_function(**service_args)
            
            # Generic update
            logger.info(f"Using generic CRUD update for {entity_type}")
            model_class = self._load_model_class(config)
            # Try primary_key first (main config param), then primary_key_field (fallback), then 'id'
            pk_field = getattr(config, 'primary_key', None) or getattr(config, 'primary_key_field', 'id')
            logger.info(f"Using primary key field: {pk_field}")
            
            with get_db_session() as session:
                entity = session.query(model_class).filter_by(**{
                    pk_field: item_id,
                    'hospital_id': context['hospital_id']
                }).first()
                
                if not entity:
                    raise ValueError(f"{config.name} not found")
                
                # Transform form data using VirtualFieldTransformer
                transformer = VirtualFieldTransformer()
                transformed_data = transformer.transform_for_update(data, entity, config)
                
                # CRITICAL DEBUG: Log what's being updated
                logger.info(f"🔍 Updating {entity_type} with transformed data keys: {list(transformed_data.keys())}")
                for jsonb_field in ['contact_info', 'supplier_address', 'bank_details', 'manager_contact_info']:
                    if jsonb_field in transformed_data:
                        logger.info(f"  JSONB {jsonb_field}: {transformed_data[jsonb_field]}")

                # Update fields
                edit_fields = getattr(config, 'edit_fields', None)
                if not edit_fields:
                    edit_fields = [f.name for f in config.fields if f.show_in_form and not getattr(f, 'readonly', False)]
                field_definitions = {field.name: field for field in config.fields}

                for field_name in edit_fields:
                    # Check if field is virtual
                    field_def = field_definitions.get(field_name)
                    is_virtual = getattr(field_def, 'virtual', False) if field_def else False
                    
                    if not is_virtual and field_name in transformed_data:
                        # Regular field
                        setattr(entity, field_name, transformed_data[field_name])
                    elif not is_virtual and field_name in data:
                        # Fallback to original data
                        setattr(entity, field_name, data[field_name])
                    # Virtual fields are handled via JSONB updates
                
                # Update JSONB fields from transformation
                jsonb_fields = ['contact_info', 'supplier_address', 'bank_details', 'manager_contact_info']
                for jsonb_field in jsonb_fields:
                    if jsonb_field in transformed_data:
                        setattr(entity, jsonb_field, transformed_data[jsonb_field])
                
                # Update audit fields
                entity.updated_at = datetime.now(timezone.utc)
                entity.updated_by = context.get('user_id')
                
                session.commit()
                logger.info(f"Updated {entity_type}/{item_id}")
                invalidate_service_cache_for_entity(entity_type, cascade=True)
                return entity
                
        except Exception as e:
            logger.error(f"Error updating {entity_type}/{item_id}: {e}")
            raise
    
    def delete_entity(self, entity_type: str, item_id: str, context: dict):
        """
        Delete entity
        Tries entity-specific service first, falls back to generic CRUD
        """
        try:
            logger.info(f"Deleting {entity_type}/{item_id}")
            
            config = self._get_entity_config(entity_type)
            self._validate_entity_category(config, CRUDOperation.DELETE)
            
            # Try entity-specific service
            service_function = self._get_service_function(config, 'delete')
            if service_function:
                logger.info(f"Using entity-specific service for {entity_type}")
                
                # Prepare standardized arguments
                entity_singular = config.entity_type.rstrip('s')
                service_args = {
                    f'{entity_singular}_id': item_id,
                    'hospital_id': context['hospital_id'],
                    'current_user_id': context.get('user_id')
                }
                
                return service_function(**service_args)
            
            # Generic delete
            logger.info(f"Using generic CRUD delete for {entity_type}")
            model_class = self._load_model_class(config)
            pk_field = getattr(config, 'primary_key', None) or getattr(config, 'primary_key_field', 'id')
            
            with get_db_session() as session:
                entity = session.query(model_class).filter_by(**{
                    pk_field: item_id,
                    'hospital_id': context['hospital_id']
                }).first()
                
                if not entity:
                    raise ValueError(f"{config.name} not found")
                
                # Soft or hard delete based on config
                if getattr(config, 'enable_soft_delete', False):
                    # Check if entity has SoftDeleteMixin
                    if hasattr(entity, 'soft_delete'):
                        # Use the mixin's method (handles all fields atomically)
                        entity.soft_delete(context.get('user_id'))
                    else:
                        # Fallback for entities without the mixin
                        logger.warning(f"Entity {entity_type} doesn't have soft_delete method, using field setting")
                        soft_delete_field = getattr(config, 'soft_delete_field', 'is_deleted')
                        if hasattr(entity, soft_delete_field):
                            setattr(entity, soft_delete_field, True)
                        if hasattr(entity, 'deleted_at'):
                            entity.deleted_at = datetime.now(timezone.utc)
                        if hasattr(entity, 'deleted_by'):
                            entity.deleted_by = context.get('user_id')
                    
                    # Update audit fields (if not already updated by soft_delete)
                    if hasattr(entity, 'updated_at'):
                        entity.updated_at = datetime.now(timezone.utc)
                    if hasattr(entity, 'updated_by'):
                        entity.updated_by = context.get('user_id')
                    
                    # Update status if applicable (business requirement)
                    if hasattr(entity, 'status'):
                        entity.status = 'inactive'
                else:
                    session.delete(entity)
                
                session.commit()
                logger.info(f"Deleted {entity_type}/{item_id}")
                invalidate_service_cache_for_entity(entity_type, cascade=True)
                return {'success': True, 'message': f'{config.name} deleted successfully'}
                
        except Exception as e:
            logger.error(f"Error deleting {entity_type}/{item_id}: {e}")
            raise

    def undelete_entity(self, entity_type: str, item_id: str, context: dict):
        """
        Restore a soft-deleted entity
        """
        try:
            logger.info(f"Restoring {entity_type}/{item_id}")
            
            config = self._get_entity_config(entity_type)
            
            if not getattr(config, 'enable_soft_delete', False):
                raise ValueError(f"Soft delete not enabled for {entity_type}")

            model_class = self._load_model_class(config)
            pk_field = getattr(config, 'primary_key', None) or getattr(config, 'primary_key_field', 'id')
            
            with get_db_session() as session:
                # Get the deleted entity
                entity = session.query(model_class).filter_by(**{
                    pk_field: item_id,
                    'hospital_id': context['hospital_id'],
                    'is_deleted': True  # Only get deleted records
                }).first()
                
                if not entity:
                    raise ValueError(f"Deleted {config.name} not found")
                
                # Check if it can be restored (business rules)
                if hasattr(entity, 'can_be_restored'):
                    can_restore, reason = entity.can_be_restored()
                    if not can_restore:
                        raise ValueError(f"Cannot restore: {reason}")
                
                # Restore using mixin method
                if hasattr(entity, 'undelete'):
                    entity.undelete(context.get('user_id'))
                else:
                    # Manual restoration
                    entity.is_deleted = False
                    entity.deleted_at = None
                    entity.deleted_by = None
                    if hasattr(entity, 'status'):
                        entity.status = 'active'
                
                session.commit()
                logger.info(f"Restored {entity_type}/{item_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error restoring {entity_type}/{item_id}: {e}")
            raise



# Singleton
_crud_service = None

def get_universal_crud_service() -> UniversalCRUDService:
    global _crud_service
    if _crud_service is None:
        _crud_service = UniversalCRUDService()
    return _crud_service