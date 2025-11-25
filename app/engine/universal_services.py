"""
Universal Service Implementation - Connects Existing Services to Universal Engine
File: app/engine/universal_services.py

Adapts your existing service methods to work with the universal engine 
Uses exact method signatures from your supplier_service.py
http://localhost:5000/universal/supplier_payments/list
"""

import importlib
from typing import Dict, Any, Optional, List, Protocol
import uuid
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func
from decimal import Decimal
from flask_login import current_user

from app.services.supplier_service import get_suppliers_for_choice
from app.services.database_service import get_db_session
from app.utils.unicode_logging import get_unicode_safe_logger
from app.engine.universal_filter_service import get_universal_filter_service
from app.engine.categorized_filter_processor import get_categorized_filter_processor
from app.engine.universal_service_cache import cache_service_method, cache_universal

logger = get_unicode_safe_logger(__name__)

class UniversalServiceRegistry:
    """
    ✅ ADD: Enhanced service registry with parameter fixing
    Much more sophisticated than simple UNIVERSAL_SERVICES dict
    """
    """
    ✅ FOCUSED: Pure service routing registry
    No database operations, no data processing - just routing
    """
    
    def __init__(self):
        # Service registry now comes from entity_registry.py only
        # No hardcoded registry needed
        
        # ⭐ Service instance cache to prevent multiple initializations
        self._service_instance_cache = {}

        self.filter_service = get_universal_filter_service()
        self.categorized_processor = get_categorized_filter_processor()
        self.entity_type = 'registry'
        
    

    def get_service(self, entity_type: str):
        """
        Get service for entity type - ONLY from entity_registry.py
        Priority:
        1. Check instance cache
        2. Check entity_registry.py 
        3. Fall back to generic service
        """
        try:
            # ⭐ STEP 1: Check if service instance already cached
            if entity_type in self._service_instance_cache:
                logger.debug(f"✅ Using cached service instance for {entity_type}")
                return self._service_instance_cache[entity_type]
            
            # ⭐ STEP 2: Try to load from entity_registry.py
            service_instance = self._load_from_entity_registry(entity_type)
            if service_instance:
                logger.info(f"[SUCCESS] Loaded from entity_registry: {service_instance.__class__.__name__}")
                # Cache it!
                self._service_instance_cache[entity_type] = service_instance
                return service_instance
            
            # ⭐ STEP 3: Fall back to generic service (was STEP 4)
            logger.info(f"ℹ️ No custom service found for {entity_type}, using generic service")
            from app.engine.universal_entity_service import GenericUniversalService
            generic_service = GenericUniversalService(entity_type)
            
            # Cache even the generic service
            self._service_instance_cache[entity_type] = generic_service
            return generic_service
            
        except Exception as e:
            logger.error(f"❌ Error getting service for {entity_type}: {str(e)}")
            # Return generic on any error
            from app.engine.universal_entity_service import GenericUniversalService
            return GenericUniversalService(entity_type)
    
    def _load_from_entity_registry(self, entity_type: str):
        """
        Helper method to load service from entity_registry.py
        This is the PREFERRED method
        """
        try:
            from app.config.entity_registry import get_entity_registration
            
            registration = get_entity_registration(entity_type)
            
            if not registration:
                logger.debug(f"No registration found for {entity_type}")
                return None
            
            if not registration.service_class:
                logger.debug(f"No service_class defined for {entity_type}")
                return None
            
            # Parse the service class path
            service_path = registration.service_class
            logger.debug(f"Found service_class for {entity_type}: {service_path}")
            
            # Handle both string paths and actual class references
            if isinstance(service_path, str):
                # It's a string path like 'app.services.purchase_order_service.PurchaseOrderService'
                module_path, class_name = service_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                service_class = getattr(module, class_name)
            else:
                # It's already a class reference
                service_class = service_path
            
            # Instantiate the service
            if callable(service_class):
                # ✅ FIX: Only pass entity_type if it's UniversalEntityService (backward compatible)
                try:
                    # Try with entity_type first (for UniversalEntityService)
                    service_instance = service_class(entity_type)
                    logger.debug(f"✅ Successfully instantiated {service_class.__name__} with entity_type")
                except TypeError:
                    # Fallback for services that don't take entity_type (backward compatible)
                    service_instance = service_class()
                    logger.debug(f"✅ Successfully instantiated {service_class.__name__} without entity_type")
                return service_instance
            else:
                # Already an instance (shouldn't happen but handle it)
                return service_class
                
        except Exception as e:
            logger.error(f"Failed to load from entity_registry for {entity_type}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    
    def clear_service_cache(self, entity_type: str = None):
        """
        Clear cached service instances
        Useful for testing or when services are updated
        """
        if entity_type:
            if entity_type in self._service_instance_cache:
                del self._service_instance_cache[entity_type]
                logger.info(f"🧹 Cleared cached service for {entity_type}")
        else:
            self._service_instance_cache.clear()
            logger.info("🧹 Cleared all cached services")
    
    def search_entity_data(self, entity_type: str, filters: Dict, **kwargs) -> Dict:
        """
        Route search to appropriate service
        This method is called by views
        """
        # Get the service (will be cached)
        service = self.get_service(entity_type)
        
        # Call the appropriate method based on what the service has
        if hasattr(service, 'search_entity_data'):
            # Preferred method name
            return service.search_entity_data(filters=filters, **kwargs)
        elif hasattr(service, 'search_data'):
            # Alternative method name
            return service.search_data(filters=filters, **kwargs)
        else:
            logger.error(f"Service for {entity_type} has no search method")
            return {
                'items': [],
                'total': 0,
                'pagination': {'total_count': 0, 'page': 1, 'per_page': 20},
                'summary': {},
                'success': False,
                'error': 'Service has no search method'
            }
    
    def get_item_data(self, entity_type: str, item_id: str, **kwargs) -> Dict:
        """
        âœ… FIXED: Universal get item function with proper wrapping for data assembler
        """
        logger.info(f"ðŸ get_item_data called for {entity_type}: {item_id}")
        
        # Get the service (will be cached)
        service = self.get_service(entity_type)
        
        # Try different method names that services might implement
        result = None
        
        # Try get_by_id first (most common)
        if hasattr(service, 'get_by_id'):
            result = service.get_by_id(item_id, **kwargs)
            if result:
                logger.info(f"âœ… Found item using get_by_id")
        
        # Try get_detail_data if get_by_id didn't work
        if not result and hasattr(service, 'get_detail_data'):
            result = service.get_detail_data(item_id, **kwargs)
            if result:
                logger.info(f"âœ… Found item using get_detail_data")
                # Check if already wrapped
                if isinstance(result, dict) and 'item' in result:
                    # Already wrapped by service, return as is
                    return result
        
        # Try get_item_data if others didn't work
        if not result and hasattr(service, 'get_item_data'):
            result = service.get_item_data(item_id, **kwargs)
            if result:
                logger.info(f"âœ… Found item using get_item_data")
        
        if not result:
            logger.error(f"âŒ No item found for {entity_type}: {item_id}")
            logger.error(f"   Service class: {service.__class__.__name__}")
            logger.error(f"   Available methods: {[m for m in dir(service) if not m.startswith('_')]}")
            return None  # Return None if not found
        
        # âœ… CRITICAL FIX: Wrap the result for data assembler
        # The data assembler expects {'item': data} format
        if isinstance(result, dict):
            # Check if already wrapped
            if 'item' in result:
                # Already wrapped, return as is
                return result
            else:
                # Not wrapped, wrap it now
                wrapped_result = {
                    'item': result,
                    'has_error': False,
                    'entity_type': entity_type,
                    'item_id': item_id
                }
                logger.info(f"âœ… Wrapped result for data assembler")
                return wrapped_result
        else:
            # Non-dict result (shouldn't happen but handle it)
            logger.warning(f"âš ï¸ Non-dict result from service: {type(result)}")
            return {
                'item': result,
                'has_error': False,
                'entity_type': entity_type,
                'item_id': item_id
            }

    def _get_builtin_service(self, entity_type: str):
        """Get built-in service implementations"""
        # Remove supplier_payments special handling since it's in registry
        if entity_type == 'patients':
            return UniversalPatientService()
        else:
            return GenericUniversalService(entity_type)
    


    def _get_error_result(self, error_message: str, entity_type: str = None, **kwargs) -> Dict:
        """Universal error handler for all entities"""
        from datetime import datetime
        return {
            'items': [],
            'total': 0,
            'page': kwargs.get('page', 1),
            'per_page': kwargs.get('per_page', 20),
            'summary': {'total_count': 0, 'total_amount': 0.00, 'pending_count': 0, 'this_month_count': 0},
            'form_instance': None,
            'branch_context': kwargs.get('branch_context', {}),
            'request_args': kwargs.get('filters', {}),
            'active_filters': {},
            'filtered_args': {},
            'error': error_message,
            'error_timestamp': datetime.now(),
            'success': False,
            'metadata': {
                'entity_type': entity_type,
                'service_name': 'universal_service_registry',
                'has_error': True,
                'orchestrated_by': 'universal_service'
            }
        }


    def _fix_parameter_names(self, kwargs: Dict) -> Dict:
        """
        ✅ ADD: CRITICAL parameter fixing method
        Converts branch_ids -> branch_id and other parameter issues
        """
        fixed_kwargs = kwargs.copy()
        
        # Fix branch parameter naming
        if 'branch_ids' in fixed_kwargs:
            branch_ids = fixed_kwargs.pop('branch_ids')
            if isinstance(branch_ids, list) and branch_ids:
                fixed_kwargs['branch_id'] = branch_ids[0]  # Use first branch
            elif branch_ids:
                fixed_kwargs['branch_id'] = branch_ids
        
        # Ensure proper types
        if 'hospital_id' in fixed_kwargs and isinstance(fixed_kwargs['hospital_id'], str):
            try:
                fixed_kwargs['hospital_id'] = uuid.UUID(fixed_kwargs['hospital_id'])
            except:
                pass
        
        if 'branch_id' in fixed_kwargs and isinstance(fixed_kwargs['branch_id'], str):
            try:
                fixed_kwargs['branch_id'] = uuid.UUID(fixed_kwargs['branch_id'])
            except:
                pass
        
        return fixed_kwargs
    
    def _generic_search(self, entity_type: str, filters: Dict, **kwargs) -> Dict:
        """Generic search for entities without specific services"""
        try:
            logger.info(f"Using generic search for {entity_type}")
            
            # This would implement basic database search
            # For now, return empty result
            return {
                'items': [],
                'total': 0,
                'pagination': {'total_count': 0},
                'summary': {},
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error in generic search for {entity_type}: {str(e)}")
            return self._get_empty_result(entity_type, str(e))
    
    def _get_empty_result(self) -> Dict:
        """Standard empty result structure"""
        return {
            'items': [],
            'total': 0,
            'pagination': {'total_count': 0, 'page': 1, 'per_page': 20, 'total_pages': 1},
            'summary': {},
            'success': True,
            'metadata': {'orchestrated_by': 'universal_service'}
        }

# ============================================================================
# Create global instance
# ============================================================================

# Global registry instance that will be used throughout the app
_service_registry = UniversalServiceRegistry()

# ============================================================================
# Convenience functions
# ============================================================================

def get_universal_service(entity_type: str):
    """
    Convenience function to get service for an entity type
    """
    return _service_registry.get_service(entity_type)

def clear_service_cache(entity_type: str = None):
    """
    Convenience function to clear service cache
    """
    _service_registry.clear_service_cache(entity_type)

def search_universal_entity_data(entity_type: str, filters: Dict, **kwargs) -> Dict:
    """
    Convenience function for searching entity data
    """
    return _service_registry.search_entity_data(entity_type, filters, **kwargs)

def get_universal_item_data(entity_type: str, item_id: str, **kwargs) -> Dict:
    """
    Convenience function for getting single item
    """
    return _service_registry.get_item_data(entity_type, item_id, **kwargs)


# ============================================================================
# USAGE EXAMPLE
# ============================================================================
"""
# To use this in your app:

# 1. Import the registry
from app.engine.universal_services import _service_registry

# 2. Get a service
service = _service_registry.get_service('purchase_orders')

# 3. Use the service
result = service.search_entity_data(filters={}, hospital_id=some_id)

# 4. Clear cache if needed
_service_registry.clear_service_cache('purchase_orders')
"""
    

class GenericUniversalService:
    """
    ✅ ENTITY AGNOSTIC: Generic service for entities without specific implementations
    Uses entity configuration to provide basic CRUD operations for ANY entity
    """
    
    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        logger.info(f"✅ Initialized generic service for {entity_type}")

    @cache_service_method()    
    def search_data(self, **kwargs) -> dict:
        """✅ ENTITY AGNOSTIC: Generic search implementation"""
        try:
            logger.info(f"Generic search for entity: {self.entity_type}")
            
            # Get standard parameters
            filters = kwargs.get('filters', {})
            hospital_id = kwargs.get('hospital_id')
            branch_id = kwargs.get('branch_id')
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            
            # Get entity configuration
            from app.config.entity_configurations import get_entity_config
            config = get_entity_config(self.entity_type)
            if not config:
                logger.error(f"No configuration found for {self.entity_type}")
                return self._get_empty_result()
            
            # Get model class from configuration
            if hasattr(config, 'model_class') and config.model_class:
                try:
                    # Import model class dynamically
                    module_path, class_name = config.model_class.rsplit('.', 1)
                    module = importlib.import_module(module_path)
                    model_class = getattr(module, class_name)
                except Exception as e:
                    logger.error(f"Failed to import model class {config.model_class}: {str(e)}")
                    return self._get_empty_result()
            else:
                logger.error(f"No model_class configured for {self.entity_type}")
                return self._get_empty_result()
            
            with get_db_session() as session:
                # Build base query
                query = session.query(model_class)
                
                # Apply hospital filter
                if hasattr(model_class, 'hospital_id') and hospital_id:
                    query = query.filter(model_class.hospital_id == hospital_id)
                
                # Apply branch filter
                if hasattr(model_class, 'branch_id') and branch_id:
                    query = query.filter(model_class.branch_id == branch_id)
                
                # Apply categorized filters (including date filters)
                from app.engine.categorized_filter_processor import get_categorized_filter_processor
                filter_processor = get_categorized_filter_processor()

                query, applied_filters, filter_count = filter_processor.process_entity_filters(
                    entity_type=self.entity_type,
                    filters=filters,
                    query=query,
                    model_class=model_class,    # ✅ FIXED: Add missing model_class parameter
                    session=session,
                    config=config
                )
                
                logger.info(f"✅ Applied {filter_count} filters: {applied_filters}")
                
                # Get total count
                total_count = query.count()
                
                # Apply sorting
                sort_field = filters.get('sort', config.default_sort_field if config else None)
                if sort_field and hasattr(model_class, sort_field):
                    sort_dir = filters.get('direction', 'asc')
                    if sort_dir == 'desc':
                        query = query.order_by(desc(getattr(model_class, sort_field)))
                    else:
                        query = query.order_by(asc(getattr(model_class, sort_field)))
                
                # Apply pagination
                offset = (page - 1) * per_page
                items = query.offset(offset).limit(per_page).all()
                
                # Convert to dictionaries
                from app.services.database_service import get_entity_dict
                items_dict = []
                for item in items:
                    item_dict = get_entity_dict(item)
                    items_dict.append(item_dict)
                
                # Build summary
                summary = {'total_count': total_count}
                if hasattr(model_class, 'status'):
                    status_counts = session.query(
                        model_class.status,
                        func.count(model_class.status)
                    ).filter(
                        model_class.hospital_id == hospital_id
                    ).group_by(model_class.status).all()
                    
                    for status, count in status_counts:
                        if status:
                            summary[f'{status.lower()}_count'] = count
                
                return {
                    'items': items_dict,
                    'total': total_count,
                    'pagination': {
                        'total_count': total_count, 
                        'page': page, 
                        'per_page': per_page, 
                        'total_pages': (total_count + per_page - 1) // per_page,
                        'has_prev': page > 1,
                        'has_next': page < ((total_count + per_page - 1) // per_page)
                    },
                    'summary': summary,
                    'success': True,
                    'applied_filters': list(applied_filters),
                    'filter_count': filter_count
                }
                
        except Exception as e:
            logger.error(f"Error in generic search for {self.entity_type}: {str(e)}")
            return self._get_empty_result()

    def _get_empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            'items': [],
            'total': 0,
            'pagination': {
                'total_count': 0, 
                'page': 1, 
                'per_page': 20, 
                'total_pages': 1
            },
            'summary': {},
            'success': False
        }

    def get_by_id(self, item_id: str, **kwargs):
        """✅ ENTITY AGNOSTIC: Generic get by ID"""
        logger.info(f"Generic get_by_id for {self.entity_type}: {item_id}")
        # TODO: Implement using entity configuration to determine table/model
        return None
    
    def create(self, data: Dict, **kwargs):
        """✅ ENTITY AGNOSTIC: Generic create"""
        logger.info(f"Generic create for {self.entity_type}")
        # TODO: Implement using entity configuration for field mapping
        return None
    
    def update(self, item_id: str, data: Dict, **kwargs):
        """✅ ENTITY AGNOSTIC: Generic update"""
        logger.info(f"Generic update for {self.entity_type}: {item_id}")
        # TODO: Implement using entity configuration for field mapping
        return None
    
    def delete(self, item_id: str, **kwargs) -> bool:
        """✅ ENTITY AGNOSTIC: Generic delete"""
        logger.info(f"Generic delete for {self.entity_type}: {item_id}")
        # TODO: Implement using entity configuration
        return False


class UniversalServiceInterface(Protocol):
    """Protocol defining universal service interface"""
    
    def search_data(self, hospital_id: uuid.UUID, filters: Dict, **kwargs) -> Dict:
        """Search and return paginated data with summary statistics"""
        ...
    
    def get_by_id(self, item_id: str, hospital_id: uuid.UUID, **kwargs):
        """Get single item by ID"""
        ...
    
    def create(self, data: Dict, hospital_id: uuid.UUID, **kwargs):
        """Create new item"""
        ...
    
    def update(self, item_id: str, data: Dict, hospital_id: uuid.UUID, **kwargs):
        """Update existing item"""
        ...
    
    def delete(self, item_id: str, hospital_id: uuid.UUID, **kwargs) -> bool:
        """Delete item (soft or hard delete)"""
        ...


class UniversalPatientService:
    """
    ✅ ENTITY SPECIFIC: Stub implementation for patients
    Move this to app/services/universal_patient_service.py when implementing
    """
    
    def __init__(self):
        logger.info("✅ Initialized UniversalPatientService (stub implementation)")
        self.entity_type = 'patients'
    
    @cache_service_method('patients', 'search_data')
    def search_data(self, **kwargs) -> Dict:
        """✅ STUB: Search patients - implement using your existing patient service"""
        try:
            filters = kwargs.get('filters', {})
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            
            logger.info(f"Patient search called with {len(filters)} filters")
            
            # TODO: Implement using your existing patient service
            return {
                'items': [],
                'total': 0,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': 0,
                    'total_pages': 1
                },
                'summary': {
                    'total_patients': 0,
                    'active_patients': 0,
                    'new_this_month': 0
                },
                'success': True,
                'message': 'Patient service stub - implementation pending'
            }
            
        except Exception as e:
            logger.error(f"Error in patient search: {str(e)}")
            return {
                'items': [],
                'total': 0,
                'pagination': {'total_count': 0},
                'summary': {},
                'success': False,
                'error': str(e)
            }
    
    def get_by_id(self, item_id: str, **kwargs):
        """✅ STUB: Get patient by ID"""
        logger.info(f"Patient get_by_id called: {item_id}")
        return None
    
    def create(self, data: Dict, **kwargs):
        """✅ STUB: Create patient"""
        logger.info("Patient create called")
        return None
    
    def update(self, item_id: str, data: Dict, **kwargs):
        """✅ STUB: Update patient"""
        logger.info(f"Patient update called: {item_id}")
        return None
    
    def delete(self, item_id: str, **kwargs) -> bool:
        """✅ STUB: Delete patient"""
        logger.info(f"Patient delete called: {item_id}")
        return False

# Global registry instance
_service_registry = UniversalServiceRegistry()

def get_universal_service(entity_type: str):
    """
    ✅ REPLACE: Enhanced factory function with better error handling
    """
    try:
        return _service_registry.get_service(entity_type)
    except Exception as e:
        logger.error(f"Error getting universal service for {entity_type}: {str(e)}")
        # Fallback to generic service
        return GenericUniversalService(entity_type)

def search_universal_entity_data(entity_type: str, filters: Dict, **kwargs) -> Dict:
    """
    ✅ ADD: Universal search function with parameter fixing
    """
    return _service_registry.search_entity_data(entity_type, filters, **kwargs)

def get_universal_item_data(entity_type: str, item_id: str, **kwargs) -> Dict:
    """
    Universal single item function - SAME PATTERN as search_universal_entity_data
    """
    return _service_registry.get_item_data(entity_type, item_id, **kwargs)

@cache_universal('filters', 'get_filter_choices') 
def get_universal_filter_choices(entity_type: str, hospital_id: Optional[uuid.UUID] = None) -> Dict:
    """
    ✅ ADD: Universal filter choices function
    """
    try:
        filter_service = get_universal_filter_service()
        
        if filter_service:
            filter_data = filter_service.get_complete_filter_data(
                entity_type=entity_type,
                hospital_id=hospital_id or (current_user.hospital_id if current_user else None),
                branch_id=None,
                current_filters={}
            )
            
            return {
                'backend_data': filter_data.get('backend_data', {}),
                'success': not filter_data.get('has_errors', False),
                'error_messages': filter_data.get('error_messages', [])
            }
        else:
            return {
                'backend_data': {},
                'success': True,
                'error_messages': []
            }
        
    except Exception as e:
        logger.error(f"Error getting universal filter choices for {entity_type}: {str(e)}")
        return {
            'backend_data': {},
            'success': False,
            'error_messages': [str(e)]
        }

logger.info("✅ Universal Services loaded with enhanced registry and parameter fixes")
