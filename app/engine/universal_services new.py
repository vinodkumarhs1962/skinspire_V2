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
        self.service_registry = {
            'supplier_payments': 'app.services.supplier_payment_service.SupplierPaymentService',  # NEW
            'suppliers': 'app.services.supplier_master_service.SupplierMasterService',  # NEW
            'patients': 'app.services.patient_service.PatientService',  # Future
            'medicines': 'app.services.medicine_service.MedicineService'  # Future
        }
        
        self.filter_service = get_universal_filter_service()
        self.categorized_processor = get_categorized_filter_processor()
    
    def get_service(self, entity_type: str):
        """Get appropriate service for entity type"""
        try:
            service_path = self.service_registry.get(entity_type)
            
            if not service_path:
                logger.info(f"No specific service for {entity_type}, using generic")
                return GenericUniversalService(entity_type)
            
            # Try to import entity-specific service
            try:
                module_path, class_name = service_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                service_class = getattr(module, class_name)
                return service_class()
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not load service {service_path}: {str(e)}, using fallback")
                # Fallback to built-in services
                return self._get_builtin_service(entity_type)
            
        except Exception as e:
            logger.error(f"Error getting service for {entity_type}: {str(e)}")
            return GenericUniversalService(entity_type)
    
    def _get_builtin_service(self, entity_type: str):
        """Get built-in service implementations"""
        # Remove supplier_payments special handling since it's in registry
        if entity_type == 'patients':
            return UniversalPatientService()
        else:
            return GenericUniversalService(entity_type)
    
    def search_entity_data(self, entity_type: str, filters: Dict, **kwargs) -> Dict:
        """
        ✅ CLEAN ROUTING: Route to existing complete filtering system
        Uses existing infrastructure - no duplicate logic
        ✅ FIXED: Added breakdown enhancement to maintain feature parity
        """
        try:
            logger.info(f"🔄 [CLEAN_ROUTING] Routing {entity_type} to existing complete system")
            
            # ✅ NEW: Extract complete filters from request if available
            import flask
            if flask.has_request_context() and flask.request:
                complete_filters = filters.copy()
                
                # Extract ALL parameters from request.args that aren't already in filters
                for key in flask.request.args.keys():
                    if key not in complete_filters:
                        # Get all values for this key
                        values = flask.request.args.getlist(key)
                        
                        # Skip empty values
                        values = [v for v in values if v and v.strip()]
                        
                        if values:
                            # Single value - store as string
                            if len(values) == 1:
                                complete_filters[key] = values[0]
                            # Multiple values - store as list
                            else:
                                complete_filters[key] = values
                                
                                # For backward compatibility, also set singular version
                                # e.g., 'statuses' -> 'status'
                                if key.endswith('s') and key != 'status':
                                    singular_key = key[:-1]
                                    if singular_key not in complete_filters:
                                        complete_filters[singular_key] = values[0]
                
                logger.info(f"✅ Enhanced filter extraction: {len(filters)} → {len(complete_filters)} parameters")
                filters = complete_filters


            # Extract basic parameters
            hospital_id = kwargs.get('hospital_id') or (current_user.hospital_id if current_user else None)
            branch_id = kwargs.get('branch_id')
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            
            if not hospital_id:
                raise ValueError("Hospital ID is required")
            
            # Route to existing complete filter system
            filter_data = self.filter_service.get_complete_filter_data(
                entity_type=entity_type,
                hospital_id=hospital_id,
                branch_id=branch_id,
                current_filters=filters
            )
            
            logger.info(f"✅ [COMPLETE_SYSTEM] Filter data obtained for {entity_type}")
            
            # Route query execution to categorized processor (where DB logic belongs)
            result = self.categorized_processor.execute_complete_search(
                entity_type=entity_type,
                filters=filters, # Now has ALL parameters from request
                filter_data=filter_data,
                hospital_id=hospital_id,
                branch_id=branch_id,
                page=page,
                per_page=per_page
            )
            
            # ✅ CRITICAL FIX: Enhance result with breakdowns if successful
            # This maintains 100% backward compatibility while fixing the breakdown issue
            if result and result.get('success'):
                logger.info(f"🔍 [BREAKDOWN_FIX] Enhancing {entity_type} result with breakdowns")
                result = self._enhance_result_with_breakdowns(entity_type, result, filters)
                logger.info(f"✅ [BREAKDOWN_FIX] Enhanced {entity_type} result with breakdowns")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in search_entity_data for {entity_type}: {str(e)}")
            # ✅ Maintain backward compatibility with existing error response structure
            return {
                'items': [],
                'total': 0,
                'page': page if 'page' in locals() else 1,
                'per_page': per_page if 'per_page' in locals() else 20,
                'total_pages': 0,
                'pagination': {
                    'total_count': 0,
                    'page': page if 'page' in locals() else 1,
                    'per_page': per_page if 'per_page' in locals() else 20,
                    'total_pages': 0
                },
                'summary': {'total_count': 0},
                'success': False,
                'error': str(e),
                'entity_type': entity_type
            }
        

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

    def _enhance_result_with_breakdowns(self, entity_type: str, result: Dict, filters: Dict) -> Dict:
        """
        ✅ UNIVERSAL: Add breakdown calculations based on entity configuration
        This method is entity-agnostic and uses configuration to determine what breakdowns to calculate
        """
        try:
            from app.config.entity_configurations import get_entity_config
            
            config = get_entity_config(entity_type)
            if not config or not hasattr(config, 'summary_cards'):
                return result
            
            # ✅ Check if entity needs breakdown calculations
            needs_breakdown = False
            breakdown_configs = []
            
            for card_config in config.summary_cards:
                if card_config.get('card_type') == 'detail' and card_config.get('breakdown_fields'):
                    needs_breakdown = True
                    breakdown_configs.append(card_config)
            
            if not needs_breakdown:
                return result
            
            # ✅ Calculate breakdowns for entities that need them
            summary = result.get('summary', {}).copy()  # Make a copy to preserve existing fields

            for breakdown_config in breakdown_configs:
                breakdown_data = self._calculate_universal_breakdown(
                    entity_type, 
                    breakdown_config, 
                    filters,
                    existing_result=result
                )
                # ✅ PRESERVE existing summary fields while adding breakdown data
                summary.update(breakdown_data)
                logger.info(f"✅ Added {breakdown_config['id']} breakdown to {entity_type}: {breakdown_data}")

            result['summary'] = summary
            return result
            
        except Exception as e:
            logger.error(f"Error enhancing result with breakdowns for {entity_type}: {str(e)}")
            return result

    def _calculate_universal_breakdown(self, entity_type: str, breakdown_config: Dict, filters: Dict, existing_result: Dict = None) -> Dict:
        """
        ✅ UNIVERSAL: Calculate breakdown for any entity type
        Currently supports payment method breakdown - can be extended for other breakdown types
        """
        try:
            breakdown_type = breakdown_config.get('id', '')
            
            if breakdown_type == 'payment_breakdown':
                return self._calculate_payment_method_breakdown(entity_type, filters, existing_result)
            elif breakdown_type == 'status_breakdown':
                return self._calculate_status_breakdown(entity_type, filters)
            elif breakdown_type == 'category_breakdown':
                return self._calculate_category_breakdown(entity_type, filters)
            else:
                logger.warning(f"Unknown breakdown type: {breakdown_type}")
                return {}
                
        except Exception as e:
            logger.error(f"Error calculating breakdown {breakdown_config.get('id', 'unknown')}: {str(e)}")
            return {}

    def _calculate_payment_method_breakdown(self, entity_type: str, filters: Dict, existing_result: Dict = None) -> Dict:
        """
        ✅ UNIVERSAL: Calculate payment method breakdown for payment-related entities
        """
        try:
            if entity_type not in ['supplier_payments', 'customer_payments', 'refunds']:
                return {}
            
            # ✅ ALWAYS use existing breakdown data from main service call if available
            if existing_result and 'summary' in existing_result:
                existing_summary = existing_result['summary']
                breakdown_fields = ['cash_amount', 'cheque_amount', 'bank_amount', 'upi_amount']
                
                # Check if breakdown data exists and has meaningful values
                if all(field in existing_summary for field in breakdown_fields):
                    breakdown_data = {
                        'cash_amount': existing_summary.get('cash_amount', 0.0),
                        'cheque_amount': existing_summary.get('cheque_amount', 0.0),
                        'bank_amount': existing_summary.get('bank_amount', 0.0),
                        'upi_amount': existing_summary.get('upi_amount', 0.0)
                    }
                    
                    # If all values are zero, try to calculate from database
                    if all(amount == 0.0 for amount in breakdown_data.values()):
                        logger.info(f"Existing breakdown data is all zeros, calculating from database for {entity_type}")
                        calculated_breakdown = self._calculate_breakdown_from_database(entity_type, filters)
                        if calculated_breakdown and any(amount > 0 for amount in calculated_breakdown.values()):
                            return calculated_breakdown
                    
                    logger.info(f"Using existing breakdown data from main service for {entity_type}")
                    return breakdown_data
            
            # ✅ Calculate from database if no existing data
            logger.info(f"No existing breakdown data found for {entity_type}, calculating from database")
            return self._calculate_breakdown_from_database(entity_type, filters)
            
        except Exception as e:
            logger.error(f"Error calculating payment breakdown for {entity_type}: {str(e)}")
            return {'cash_amount': 0.0, 'cheque_amount': 0.0, 'bank_amount': 0.0, 'upi_amount': 0.0}

    def _get_all_supplier_payments(self, filters: Dict) -> List[Dict]:
        """Get all supplier payments using existing service with detached copies"""
        try:
            from app.services.database_service import get_db_session, get_entity_dict
            
            # Create filters dict with all records for breakdown calculation
            breakdown_filters = {
                'page': 1,
                'per_page': 999999,
                'start_date': filters.get('start_date'),
                'end_date': filters.get('end_date'),
                'supplier_id': filters.get('supplier_id'),
                'status': filters.get('status'),
                'payment_method': filters.get('payment_method'),
                'amount_min': filters.get('amount_min'),
                'amount_max': filters.get('amount_max')
            }
            
            service = self.get_service('supplier_payments')
            if hasattr(service, 'search_data'):
                result = service.search_data(
                    filters=breakdown_filters,
                    hospital_id=current_user.hospital_id,
                    branch_id=filters.get('branch_id'),
                    current_user_id=current_user.user_id
                )
            else:
                logger.error("Supplier payment service doesn't have search_data method")
                return []
                
            if result.get('success') and result.get('payments'):
                # Convert to detached copies to avoid session issues
                detached_payments = []
                for payment in result['payments']:
                    if hasattr(payment, '__dict__'):
                        # Convert entity to safe dictionary
                        detached_payment = get_entity_dict(payment)
                    else:
                        # Already a dictionary, make a copy
                        detached_payment = dict(payment)
                    detached_payments.append(detached_payment)
                
                logger.info(f"✅ Retrieved {len(detached_payments)} detached payment records for breakdown")
                return detached_payments
            else:
                return []
                    
        except Exception as e:
            logger.error(f"Error getting all supplier payments: {str(e)}")
            return []
    
    def _calculate_breakdown_from_database(self, entity_type: str, filters: Dict) -> Dict:
        """Calculate breakdown if entity service supports it"""
        try:
            # Get the service for this entity
            service = self.get_service(entity_type)
            
            # Check if service supports breakdown calculation
            if hasattr(service, 'get_payment_breakdown'):
                # Simply delegate to the service - it will use the same filters
                breakdown = service.get_payment_breakdown(filters)
                logger.info(f"✅ Got payment breakdown from {entity_type} service: {breakdown}")
                return breakdown
            
            # No breakdown support for this entity - return empty dict
            logger.debug(f"Entity {entity_type} does not support payment breakdown")
            return {}
            
        except Exception as e:
            logger.error(f"Error calculating breakdown for {entity_type}: {str(e)}")
            return {}


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

class GenericUniversalService:
    """
    ✅ ENTITY AGNOSTIC: Generic service for entities without specific implementations
    Uses entity configuration to provide basic CRUD operations for ANY entity
    """
    
    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        logger.info(f"✅ Initialized generic service for {entity_type}")
        
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
                    self.entity_type, filters, query, session, config
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


# def register_universal_service(entity_type: str, service_path: str):
#     """
#     ✅ ENTITY AGNOSTIC: Register a new universal service for ANY entity type
    
#     Args:
#         entity_type: The entity type (e.g., 'medicines', 'invoices')
#         service_path: Full path to service class (e.g., 'app.services.medicine_service.UniversalMedicineService')
#     """
#     try:
#         _service_registry.service_registry[entity_type] = service_path
#         logger.info(f"✅ Universal service registered for {entity_type}: {service_path}")
#     except Exception as e:
#         logger.error(f"Error registering service for {entity_type}: {str(e)}")


# def list_registered_services() -> List[str]:
#     """✅ ENTITY AGNOSTIC: Get list of all registered universal service entity types"""
#     return list(_service_registry.service_registry.keys())


# Validation and testing functions
# def validate_service_interface(service_instance, entity_type: str) -> List[str]:
#     """
#     Validate that a service implements the required interface
#     Returns list of missing methods or errors
#     """
#     errors = []
#     required_methods = ['search_data', 'get_by_id', 'create', 'update', 'delete']
    
#     for method_name in required_methods:
#         if not hasattr(service_instance, method_name):
#             errors.append(f"Missing required method: {method_name}")
#         elif not callable(getattr(service_instance, method_name)):
#             errors.append(f"Method {method_name} is not callable")
    
#     return errors


# def test_universal_service(entity_type: str) -> bool:
#     """
#     Test universal service for basic functionality
#     Returns True if service passes basic tests
#     """
#     try:
#         service = get_universal_service(entity_type)
        
#         # Validate interface
#         errors = validate_service_interface(service, entity_type)
#         if errors:
#             logger.error(f"❌ Service validation failed for {entity_type}: {errors}")
#             return False
        
#         logger.info(f"✅ Universal service validation passed for {entity_type}")
#         return True
        
#     except Exception as e:
#         logger.error(f"❌ Service test failed for {entity_type}: {str(e)}")
#         return False


# Test all registered services
# def test_all_services():
#     """Test all registered universal services"""
#     results = {}
#     for entity_type in _service_registry.service_registry.keys():
#         results[entity_type] = test_universal_service(entity_type)
    
#     # Print results
#     print("\n🧪 Universal Service Test Results:")
#     print("=" * 50)
#     for entity_type, passed in results.items():
#         status = "✅ PASSED" if passed else "❌ FAILED"
#         print(f"{entity_type:20} {status}")
    
#     return results


# Run tests when module is imported in development
# if __name__ == "__main__":
#     test_all_services()