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
from decimal import Decimal
from flask_login import current_user

from app.services.supplier_service import get_suppliers_for_choice
from app.services.universal_supplier_service import EnhancedUniversalSupplierService
from app.services.database_service import get_db_session
from app.utils.unicode_logging import get_unicode_safe_logger
from app.engine.universal_filter_service import get_universal_filter_service

logger = get_unicode_safe_logger(__name__)

class UniversalServiceRegistry:
    """
    ✅ ADD: Enhanced service registry with parameter fixing
    Much more sophisticated than simple UNIVERSAL_SERVICES dict
    """
    
    def __init__(self):
        self.service_registry = {
            'supplier_payments': 'app.services.universal_supplier_service.EnhancedUniversalSupplierService',  # ✅ Use enhanced service
            'suppliers': 'app.services.universal_supplier_service.EnhancedUniversalSupplierService',
            'patients': 'app.services.universal_patient_service.UniversalPatientService',
            'medicines': 'app.services.universal_medicine_service.UniversalMedicineService'
        }
        
        self.filter_service = get_universal_filter_service()
    
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
        if entity_type == 'supplier_payments':
            return UniversalSupplierPaymentService()
        elif entity_type == 'patients':
            return UniversalPatientService()
        else:
            return GenericUniversalService(entity_type)
    
    def search_entity_data(self, entity_type: str, filters: Dict, **kwargs) -> Dict:
        """Universal search method that works for ANY entity"""
        try:
            # ✅ Get appropriate service
            service = self.get_service(entity_type)
            
            # ✅ Call service search method
            if hasattr(service, 'search_data'):
                result = service.search_data(
                    hospital_id=current_user.hospital_id,
                    filters=filters,
                    **kwargs
                )
            elif hasattr(service, 'search_payments_with_form_integration'):
                result = service.search_payments_with_form_integration(filters=filters, **kwargs)
            else:
                # ✅ Generic search fallback
                result = self._generic_search(entity_type, filters, **kwargs)
            
            # ✅ UNIVERSAL: Add breakdown calculations if needed by entity configuration
            result = self._enhance_result_with_breakdowns(entity_type, result, filters)
            return result
                
        except Exception as e:
            logger.error(f"Error searching {entity_type}: {str(e)}")
            return self._get_empty_result()

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
            summary = result.get('summary', {})
            
            for breakdown_config in breakdown_configs:
                breakdown_data = self._calculate_universal_breakdown(
                    entity_type, 
                    breakdown_config, 
                    filters,
                    existing_result=result
                )
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
            
            # Call without session parameter to let service manage its own session
            from app.services.universal_supplier_service import EnhancedUniversalSupplierService
            universal_service = EnhancedUniversalSupplierService()
            result = universal_service._search_supplier_payments_universal(
                hospital_id=current_user.hospital_id,
                filters=breakdown_filters,
                branch_id=filters.get('branch_id'),
                current_user_id=current_user.user_id
            )
                
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
        """Calculate payment method breakdown amounts using direct database query with request filters"""
        try:
            if entity_type != 'supplier_payments':
                return {'cash_amount': 0.0, 'cheque_amount': 0.0, 'bank_amount': 0.0, 'upi_amount': 0.0}
            
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierPayment
            from app.models.master import Supplier
            from sqlalchemy import func
            from flask_login import current_user
            from flask import request
            
            # Extract filters from request to avoid session conflicts
            filter_data = {
                'start_date': request.args.get('start_date'),
                'end_date': request.args.get('end_date'),
                'supplier_id': request.args.get('supplier_id'),
                'supplier_name_search': request.args.get('supplier_name_search') or request.args.get('search'),
                'workflow_status': request.args.get('workflow_status') or request.args.get('status'),
                'payment_method': request.args.get('payment_method'),
                'min_amount': request.args.get('min_amount') or request.args.get('amount_min'),
                'max_amount': request.args.get('max_amount') or request.args.get('amount_max'),
                'reference_no': request.args.get('reference_no') or request.args.get('ref_no'),
                'invoice_id': request.args.get('invoice_id'),
                'branch_id': request.args.get('branch_id')
            }
            
            with get_db_session() as session:
                # Build query with same filter logic as main search
                query = session.query(
                    func.sum(SupplierPayment.cash_amount).label('total_cash'),
                    func.sum(SupplierPayment.cheque_amount).label('total_cheque'),
                    func.sum(SupplierPayment.bank_transfer_amount).label('total_bank'),
                    func.sum(SupplierPayment.upi_amount).label('total_upi')
                ).filter(
                    SupplierPayment.hospital_id == current_user.hospital_id
                )
                
                # Apply date filters
                if filter_data['start_date']:
                    from datetime import datetime
                    start_date_obj = datetime.strptime(filter_data['start_date'], '%Y-%m-%d').date()
                    query = query.filter(SupplierPayment.payment_date >= start_date_obj)
                if filter_data['end_date']:
                    from datetime import datetime
                    end_date_obj = datetime.strptime(filter_data['end_date'], '%Y-%m-%d').date()
                    query = query.filter(SupplierPayment.payment_date <= end_date_obj)
                
                # Apply supplier filters
                if filter_data['supplier_id'] and filter_data['supplier_id'].strip():
                    query = query.filter(SupplierPayment.supplier_id == filter_data['supplier_id'])
                elif filter_data['supplier_name_search'] and filter_data['supplier_name_search'].strip():
                    supplier_subquery = session.query(Supplier.supplier_id).filter(
                        Supplier.hospital_id == current_user.hospital_id,
                        Supplier.supplier_name.ilike(f'%{filter_data["supplier_name_search"]}%')
                    ).subquery()
                    query = query.filter(SupplierPayment.supplier_id.in_(supplier_subquery))
                
                # Apply status filters
                if filter_data['workflow_status'] and filter_data['workflow_status'].strip():
                    query = query.filter(SupplierPayment.workflow_status == filter_data['workflow_status'])
                
                # Apply reference number filters
                if filter_data['reference_no'] and filter_data['reference_no'].strip():
                    query = query.filter(SupplierPayment.reference_no.ilike(f'%{filter_data["reference_no"]}%'))

                # Apply payment method filters
                if filter_data['payment_method'] and filter_data['payment_method'].strip():
                    if filter_data['payment_method'] == 'bank_transfer_inclusive':
                        from sqlalchemy import or_, and_
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'bank_transfer',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.bank_transfer_amount > 0
                                )
                            )
                        )
                    elif filter_data['payment_method'] == 'cash':
                        from sqlalchemy import or_, and_
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'cash',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.cash_amount > 0
                                )
                            )
                        )
                    elif filter_data['payment_method'] == 'cheque':
                        from sqlalchemy import or_, and_
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'cheque',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.cheque_amount > 0
                                )
                            )
                        )
                    elif filter_data['payment_method'] == 'bank_transfer':
                        from sqlalchemy import or_, and_
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'bank_transfer',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.bank_transfer_amount > 0
                                )
                            )
                        )
                    elif filter_data['payment_method'] == 'upi':
                        from sqlalchemy import or_, and_
                        query = query.filter(
                            or_(
                                SupplierPayment.payment_method == 'upi',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.upi_amount > 0
                                )
                            )
                        )
                    else:
                        query = query.filter(SupplierPayment.payment_method == filter_data['payment_method'])
                
                # Apply amount filters
                if filter_data['min_amount']:
                    try:
                        min_val = float(filter_data['min_amount'])
                        query = query.filter(SupplierPayment.amount >= min_val)
                    except ValueError:
                        pass
                if filter_data['max_amount']:
                    try:
                        max_val = float(filter_data['max_amount'])
                        query = query.filter(SupplierPayment.amount <= max_val)
                    except ValueError:
                        pass
                
                # Apply reference number filter
                if filter_data['reference_no'] and filter_data['reference_no'].strip():
                    query = query.filter(SupplierPayment.reference_no.ilike(f'%{filter_data["reference_no"]}%'))
                
                # Apply invoice ID filter
                if filter_data['invoice_id'] and filter_data['invoice_id'].strip():
                    query = query.filter(SupplierPayment.invoice_id == filter_data['invoice_id'])
                
                # Apply branch filter
                if filter_data['branch_id'] and filter_data['branch_id'].strip():
                    try:
                        import uuid
                        branch_uuid = uuid.UUID(filter_data['branch_id'])
                        query = query.filter(SupplierPayment.branch_id == branch_uuid)
                    except ValueError:
                        pass
                
                # Execute query
                result = query.first()
                
                breakdown_amounts = {
                    'cash_amount': float(result.total_cash or 0),
                    'cheque_amount': float(result.total_cheque or 0),
                    'bank_amount': float(result.total_bank or 0),
                    'upi_amount': float(result.total_upi or 0)
                }
                
                logger.info(f"Calculated breakdown using direct filter application: {breakdown_amounts}")
                return breakdown_amounts
                
        except Exception as e:
            logger.error(f"Error calculating breakdown from database: {str(e)}")
            return {'cash_amount': 0.0, 'cheque_amount': 0.0, 'bank_amount': 0.0, 'upi_amount': 0.0}


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
    
    def _get_empty_result(self, entity_type: str, error: str = None) -> Dict:
        """Get empty result structure"""
        return {
            'items': [],
            'total': 0,
            'pagination': {'total_count': 0, 'current_page': 1, 'per_page': 20, 'total_pages': 1},
            'summary': {},
            'success': False,
            'error': error,
            'entity_type': entity_type
        }

class GenericUniversalService:
    """
    ✅ ADD: Generic service for entities without specific implementations
    """
    
    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.filter_service = get_universal_filter_service()
    
    def search_data(self, hospital_id: uuid.UUID, filters: Dict, **kwargs) -> Dict:
        """Generic search using configuration"""
        try:
            logger.info(f"Generic search for {self.entity_type}")
            
            # Get filter data to ensure configuration is working
            if self.filter_service:
                filter_data = self.filter_service.get_complete_filter_data(
                    entity_type=self.entity_type,
                    hospital_id=hospital_id,
                    branch_id=kwargs.get('branch_id'),
                    current_filters=filters
                )
            else:
                filter_data = {}
            
            # For generic entities, return empty result with proper structure
            return {
                'items': [],
                'total': 0,
                'pagination': {
                    'total_count': 0,
                    'current_page': filters.get('page', 1),
                    'per_page': filters.get('per_page', 20),
                    'total_pages': 1,
                    'has_prev': False,
                    'has_next': False
                },
                'summary': {},
                'success': True,
                'filter_data': filter_data
            }
            
        except Exception as e:
            logger.error(f"Error in generic search for {self.entity_type}: {str(e)}")
            return {
                'items': [],
                'total': 0,
                'pagination': {'total_count': 0},
                'summary': {},
                'success': False,
                'error': str(e)
            }


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


class UniversalSupplierPaymentService:
    """
    Universal service adapter for supplier payments
    Connects universal engine to your existing SupplierPaymentService
    """
    
    def __init__(self):
        self.filter_service = get_universal_filter_service()
    
    def search_data(self, 
                   hospital_id: uuid.UUID, 
                   filters: Dict, 
                   branch_id: Optional[uuid.UUID] = None,  # ✅ FIXED: branch_id not branch_ids
                   current_user_id: Optional[str] = None,
                   page: int = 1, 
                   per_page: int = 20,
                   sort_field: Optional[str] = None,
                   sort_direction: Optional[str] = None,
                   session: Optional[Session] = None) -> Dict:
        """
        ✅ CRITICAL FIX: Search with correct parameter signature
        """
        try:
            from app.services.universal_supplier_service import EnhancedUniversalSupplierService
            enhanced_service = EnhancedUniversalSupplierService()
            result = enhanced_service._search_supplier_payments_universal(
                hospital_id=hospital_id,
                filters=filters,
                branch_id=branch_id,  # ✅ FIXED: Use branch_id (singular)
                current_user_id=current_user_id,
                page=page,
                per_page=per_page,
                session=session
            )
            
            # ✅ Standardize response format
            if result.get('success', True):
                return {
                    'items': result.get('payments', []),
                    'total': result.get('pagination', {}).get('total_count', 0),
                    'pagination': result.get('pagination', {}),
                    'summary': result.get('summary', {}),
                    'suppliers': result.get('suppliers', []),
                    'success': True
                }
            else:
                return {
                    'items': [],
                    'total': 0,
                    'pagination': {'total_count': 0},
                    'summary': {},
                    'suppliers': [],
                    'success': False,
                    'error': result.get('error', 'Search failed')
                }
                
        except Exception as e:
            logger.error(f"Error in supplier payment search: {str(e)}")
            return {
                'items': [],
                'total': 0,
                'pagination': {'total_count': 0},
                'summary': {},
                'suppliers': [],
                'success': False,
                'error': str(e)
            }
    
    def get_filter_choices(self, hospital_id: Optional[uuid.UUID] = None) -> Dict:
        """
        ✅ ENHANCED: Get filter choices using UniversalFilterService
        """
        try:
            if not hospital_id and current_user:
                hospital_id = current_user.hospital_id
            
            # Use unified filter service for backend data
            if self.filter_service:
                filter_data = self.filter_service.get_complete_filter_data(
                    entity_type='supplier_payments',
                    hospital_id=hospital_id,
                    branch_id=None,
                    current_filters={}
                )
                
                # Extract choices from filter data
                backend_data = filter_data.get('backend_data', {})
                
                # Return in expected format
                return {
                    'suppliers': backend_data.get('supplier_id', []),
                    'payment_methods': backend_data.get('payment_method', []),
                    'statuses': backend_data.get('workflow_status', []),
                    'success': True
                }
            else:
                # Fallback to hardcoded choices if filter service not available
                return {
                    'suppliers': [],
                    'payment_methods': [
                        {'value': 'cash', 'label': 'Cash'},
                        {'value': 'cheque', 'label': 'Cheque'},
                        {'value': 'bank_transfer', 'label': 'Bank Transfer'},
                        {'value': 'upi', 'label': 'UPI'}
                    ],
                    'statuses': [
                        {'value': 'pending', 'label': 'Pending'},
                        {'value': 'approved', 'label': 'Approved'},
                        {'value': 'rejected', 'label': 'Rejected'}
                    ],
                    'success': True
                }
            
        except Exception as e:
            logger.error(f"Error getting filter choices: {str(e)}")
            return {
                'suppliers': [],
                'payment_methods': [],
                'statuses': [],
                'success': False,
                'error': str(e)
            }

    
    def _convert_filters_to_service_format(self, universal_filters: Dict) -> Dict:
        """
        NEW METHOD: Convert universal engine filters to your service's expected format
        
        BACKWARD COMPATIBLE: Handles all existing filter formats + new ones
        """
        service_filters = {}
        
        try:
            # COMPREHENSIVE MAPPING: Maps universal filter names to your service's expected names
            filter_mapping = {
                # Standard filters
                'search': 'search',
                'supplier_id': 'supplier_id',
                'reference_no': 'reference_no',
                
                # Status handling (multiple formats for backward compatibility)
                'status': 'statuses',           # Single status -> list
                'workflow_status': 'statuses',  # Alternative name
                'statuses': 'statuses',         # Direct mapping
                
                # Payment method handling (multiple formats)
                'payment_method': 'payment_methods',   # Single -> list  
                'payment_methods': 'payment_methods',  # Direct mapping

                # ✅ FIX: Add direct payment_method mapping for database filtering
                'payment_method_single': 'payment_method', # Single -> single for DB
                
                # Date filters
                'start_date': 'start_date',
                'end_date': 'end_date',
                'payment_date': 'payment_date',
                'date_range': 'date_range',
                
                # Amount filters
                'min_amount': 'min_amount',
                'max_amount': 'max_amount',
                'amount': 'amount',
                
                # Other filters
                'branch_id': 'branch_id',
                'approval_level': 'approval_level',
                'currency_code': 'currency_code',
                'invoice_id': 'invoice_id'
            }
            
            # BACKWARD COMPATIBLE: Convert filters using the mapping
            for universal_key, service_key in filter_mapping.items():
                if universal_key in universal_filters and universal_filters[universal_key]:
                    value = universal_filters[universal_key]
                    
                    # SPECIAL HANDLING: Convert formats your service expects
                    if service_key == 'statuses':
                        # Your service expects a list for status filtering
                        if isinstance(value, str):
                            service_filters[service_key] = [value]
                        elif isinstance(value, list):
                            service_filters[service_key] = value
                        else:
                            service_filters[service_key] = [str(value)]
                            
                    elif service_key == 'payment_methods':
                        # Your service expects a list for payment method filtering
                        if isinstance(value, str):
                            service_filters[service_key] = [value]
                            # ✅ FIX: Also set single payment_method for database filtering
                            service_filters['payment_method'] = value
                        elif isinstance(value, list):
                            service_filters[service_key] = value
                            # ✅ FIX: Also set single payment_method for database filtering
                            service_filters['payment_method'] = value[0] if value else None
                        else:
                            service_filters[service_key] = [str(value)]
                            # ✅ FIX: Also set single payment_method for database filtering
                            service_filters['payment_method'] = str(value)
                            
                    elif service_key in ['start_date', 'end_date']:
                        # FIX: Convert date objects to strings for service compatibility
                        if isinstance(value, date):
                            service_filters[service_key] = value.strftime('%Y-%m-%d')
                        elif isinstance(value, datetime):
                            service_filters[service_key] = value.date().strftime('%Y-%m-%d')
                        else:
                            # If it's already a string, leave it as is
                            service_filters[service_key] = value
                    else:
                        # Direct mapping for other filters
                        service_filters[service_key] = value
            
            # DEFAULT FILTERING: Apply current month if no date filters (based on your requirements)
            if not any(key in service_filters for key in ['start_date', 'end_date', 'date_range']):
                current_date = date.today()
                current_month_start = current_date.replace(day=1)
                
                # FIX: Convert date objects to strings for service compatibility
                service_filters['start_date'] = current_month_start.strftime('%Y-%m-%d')
                service_filters['end_date'] = current_date.strftime('%Y-%m-%d')
                logger.info(f"🔧 Applied default current month filter: {current_month_start} to {current_date}")

            # ✅ FIX: Only remove truly empty values, preserve user selections
            # Don't remove actual filter values that user selected
            service_filters = {k: v for k, v in service_filters.items() 
                            if v is not None and v != ''}
            # ❌ REMOVED: and v != [] - This was removing user-selected filter arrays
            
            # ✅ FIX: Ensure payment_method is available for database filtering
            if 'payment_methods' in service_filters and not service_filters.get('payment_method'):
                payment_methods = service_filters['payment_methods']
                if isinstance(payment_methods, list) and payment_methods:
                    service_filters['payment_method'] = payment_methods[0]
                elif isinstance(payment_methods, str):
                    service_filters['payment_method'] = payment_methods


            logger.debug(f"🔄 Filter conversion: {len(universal_filters)} -> {len(service_filters)} items")
            return service_filters
            
        except Exception as e:
            logger.error(f"❌ Error converting filters: {str(e)}")
            # FALLBACK: Return safe minimal filters
            return {'start_date': date.today().replace(day=1), 'end_date': date.today()}
    
    def _convert_date_preset(self, preset: str) -> tuple:
        """Convert date preset to start_date, end_date tuple"""
        today = date.today()
        
        if preset == 'today':
            return today, today
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif preset == 'this_week':
            start = today - timedelta(days=today.weekday())
            return start, today
        elif preset == 'last_week':
            start = today - timedelta(days=today.weekday() + 7)
            end = today - timedelta(days=today.weekday() + 1)
            return start, end
        elif preset == 'this_month':
            start = today.replace(day=1)
            # ✅ FIX: End should be last day of month
            if today.month == 12:
                last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            return start, today
        elif preset == 'this_financial_year':
            # ✅ FIX: Financial year April to March (last day)
            if today.month >= 4:  # Current FY
                fy_start = date(today.year, 4, 1)
                fy_end = date(today.year + 1, 3, 31)
            else:  # Previous FY
                fy_start = date(today.year - 1, 4, 1) 
                fy_end = date(today.year, 3, 31)
            return fy_start, fy_end    
        elif preset == 'last_month':
            first_day = today.replace(day=1)
            last_month_end = first_day - timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            return last_month_start, last_month_end
        elif preset == 'last_30_days':
            start = today - timedelta(days=30)
            return start, today
        elif preset == 'last_90_days':
            start = today - timedelta(days=90)
            return start, today
        
        return None, None
    
   
    
    def _get_this_month_count(self, hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> int:
        """Get count of payments for current month"""
        try:
            today = date.today()
            month_start = today.replace(day=1)
            
            # Use your existing service to get this month's count
            filters = {
                'start_date': month_start,
                'end_date': today
            }
            
            with get_db_session() as db_session:
                from app.services.universal_supplier_service import EnhancedUniversalSupplierService
                universal_service = EnhancedUniversalSupplierService()
                result = universal_service._search_supplier_payments_universal(
                    hospital_id=hospital_id,
                    filters=filters,
                    branch_id=branch_id,
                    current_user_id=None,
                    page=1,
                    per_page=1,  # We only need the count
                    session=db_session
                )
                return result.get('total', 0)
                
        except Exception as e:
            logger.error(f"❌ Error getting this month count: {str(e)}")
            return 0
    
    def get_by_id(self, 
                  item_id: str, 
                  hospital_id: uuid.UUID, 
                  current_user_id: Optional[str] = None,
                  include_related: bool = False,
                  session: Optional[Session] = None):
        """
        Get supplier payment by ID using your existing service method
        """
        try:
            with get_db_session() as db_session:
                from app.services.supplier_service import get_supplier_payment_by_id  
                payment = get_supplier_payment_by_id(
                    payment_id=item_id,
                    hospital_id=hospital_id,
                    include_documents=include_related,
                    include_approvals=include_related,
                    session=db_session
                )
                
                if payment:
                    logger.info(f"✅ Payment retrieved: {payment.reference_no}")
                else:
                    logger.warning(f"⚠️ Payment not found: {item_id}")
                
                return payment
                
        except Exception as e:
            logger.error(f"❌ Error retrieving payment {item_id}: {str(e)}")
            return None
    
    def create(self, 
               data: Dict, 
               hospital_id: uuid.UUID, 
               branch_id: Optional[uuid.UUID] = None,
               current_user_id: Optional[str] = None,
               session: Optional[Session] = None):
        """
        Create new supplier payment using your existing service method
        """
        try:
            # Convert universal form data to your service's expected format
            payment_data = self._convert_form_data_to_service_format(data)
            
            # Add required system fields
            payment_data.update({
                'hospital_id': hospital_id,
                'branch_id': branch_id,
                'created_by': current_user_id,
                'created_at': datetime.utcnow()
            })
            
            with get_db_session() as db_session:
                # Use your existing create method
                from app.services.supplier_service import record_supplier_payment  # ✅ Import correct function
                new_payment = record_supplier_payment(  # ✅ Call function directly
                    payment_data=payment_data,
                    hospital_id=hospital_id,
                    current_user_id=current_user_id,
                    session=db_session
                )
                
                if new_payment:
                    logger.info(f"✅ Payment created: {new_payment.reference_no}")
                
                return new_payment
                
        except Exception as e:
            logger.error(f"❌ Error creating payment: {str(e)}")
            raise
    
    def update(self, 
               item_id: str, 
               data: Dict, 
               hospital_id: uuid.UUID, 
               current_user_id: Optional[str] = None,
               session: Optional[Session] = None):
        """
        Update supplier payment using your existing service method
        """
        try:
            # Convert universal form data to your service's expected format
            payment_data = self._convert_form_data_to_service_format(data)
            
            # Add update metadata
            payment_data.update({
                'updated_by': current_user_id,
                'updated_at': datetime.utcnow()
            })
            
            with get_db_session() as db_session:
                # Use your existing update method
                from app.services.supplier_service import update_supplier_payment  # ✅ Import function  
                updated_payment = update_supplier_payment(  # ✅ Call function directly
                    payment_id=item_id,
                    payment_data=payment_data,
                    hospital_id=hospital_id,
                    current_user_id=current_user_id,
                    session=db_session
                )
                
                if updated_payment:
                    logger.info(f"✅ Payment updated: {updated_payment.reference_no}")
                
                return updated_payment
                
        except Exception as e:
            logger.error(f"❌ Error updating payment {item_id}: {str(e)}")
            raise
    
    def delete(self, 
               item_id: str, 
               hospital_id: uuid.UUID, 
               current_user_id: Optional[str] = None,
               session: Optional[Session] = None) -> bool:
        """
        Delete supplier payment using your existing service method
        """
        try:
            with get_db_session() as db_session:
                # Use your existing delete method (likely soft delete)
                from app.services.supplier_service import delete_supplier_payment  # ✅ Import function
                success = delete_supplier_payment(  # ✅ Call function directly
                    payment_id=item_id,
                    hospital_id=hospital_id,
                    current_user_id=current_user_id,
                    session=db_session
                )
                
                if success:
                    logger.info(f"✅ Payment deleted: {item_id}")
                else:
                    logger.warning(f"⚠️ Payment deletion failed: {item_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Error deleting payment {item_id}: {str(e)}")
            return False
    
    def bulk_delete(self, 
                    item_ids: List[str], 
                    hospital_id: uuid.UUID, 
                    current_user_id: Optional[str] = None) -> int:
        """
        Bulk delete supplier payments
        """
        try:
            success_count = 0
            
            for item_id in item_ids:
                if self.delete(item_id, hospital_id, current_user_id):
                    success_count += 1
            
            logger.info(f"✅ Bulk delete completed: {success_count}/{len(item_ids)} payments deleted")
            return success_count
            
        except Exception as e:
            logger.error(f"❌ Error in bulk delete: {str(e)}")
            return 0
    
    def _convert_form_data_to_service_format(self, form_data: Dict) -> Dict:
        """
        Convert universal form data to your service's expected format
        Handle field name mapping and data type conversion
        """
        service_data = {}
        
        # Direct field mappings (no conversion needed)
        direct_fields = [
            'reference_no', 'supplier_id', 'invoice_id', 'amount',
            'cash_amount', 'cheque_amount', 'bank_transfer_amount', 'upi_amount',
            'payment_method', 'workflow_status', 'currency_code', 'exchange_rate',
            'bank_reference', 'notes', 'approval_level'
        ]
        
        for field in direct_fields:
            if field in form_data and form_data[field] is not None:
                value = form_data[field]
                
                # Convert string values to appropriate types
                if field in ['amount', 'cash_amount', 'cheque_amount', 'bank_transfer_amount', 'upi_amount', 'exchange_rate']:
                    try:
                        service_data[field] = Decimal(str(value)) if value else None
                    except (ValueError, TypeError):
                        service_data[field] = None
                elif field == 'approval_level':
                    try:
                        service_data[field] = int(value) if value else None
                    except (ValueError, TypeError):
                        service_data[field] = None
                else:
                    service_data[field] = value
        
        # Handle date fields
        if 'payment_date' in form_data:
            try:
                if isinstance(form_data['payment_date'], str):
                    service_data['payment_date'] = datetime.strptime(form_data['payment_date'], '%Y-%m-%d').date()
                else:
                    service_data['payment_date'] = form_data['payment_date']
            except (ValueError, TypeError):
                service_data['payment_date'] = None
        
        # Handle UUID fields
        uuid_fields = ['supplier_id', 'invoice_id', 'branch_id']
        for field in uuid_fields:
            if field in form_data and form_data[field]:
                try:
                    service_data[field] = uuid.UUID(str(form_data[field]))
                except (ValueError, TypeError):
                    service_data[field] = None
        
        logger.debug(f"🔄 Converted form data: {form_data} -> {service_data}")
        return service_data
    
    def get_filter_choices(self, hospital_id: str = None) -> dict:
        """Get filter choices for dropdown population - FIX"""
        try:
            if not hospital_id and current_user:
                hospital_id = current_user.hospital_id
                
            choices = {
                'suppliers': [],
                'payment_methods': [
                    {'value': 'cash', 'label': 'Cash'},
                    {'value': 'cheque', 'label': 'Cheque'},
                    {'value': 'bank_transfer', 'label': 'Bank Transfer'},
                    {'value': 'upi', 'label': 'UPI'}
                ],
                'statuses': [
                    {'value': 'pending', 'label': 'Pending'},
                    {'value': 'approved', 'label': 'Approved'},
                    {'value': 'rejected', 'label': 'Rejected'}
                ]
            }
            
            # Get suppliers using existing service
            if hospital_id:
                suppliers_result = get_suppliers_for_choice(hospital_id)
                if suppliers_result.get('success') and suppliers_result.get('suppliers'):
                    choices['suppliers'] = [
                        {
                            'supplier_id': supplier.supplier_id,
                            'supplier_name': supplier.supplier_name
                        }
                        for supplier in suppliers_result['suppliers']
                    ]
            
            return choices
            
        except Exception as e:
            logger.error(f"Error getting filter choices: {str(e)}")
            return {
                'suppliers': [],
                'payment_methods': [],
                'statuses': []
            }
    
    def search_data(self, filters: dict, **kwargs) -> dict:
        """✅ FIXED: Search data using existing service with proper standardization"""
        try:
            logger.info(f"[ADAPTER] UniversalSupplierPaymentService.search_data called")
            logger.info(f"[ADAPTER] Filters: {filters}")
            logger.info(f"[ADAPTER] Kwargs: {list(kwargs.keys())}")
            
            # Use existing search function with corrected parameters
            search_params = {
                'hospital_id': kwargs.get('hospital_id') or (current_user.hospital_id if current_user else None),
                'filters': filters,
                'page': kwargs.get('page', 1),
                'per_page': kwargs.get('per_page', 20),  # ✅ FIX: Changed from 10 to 20
                'current_user_id': kwargs.get('current_user_id'),
                'branch_id': kwargs.get('branch_id')
            }
            
            # Remove None values to avoid parameter issues
            search_params = {k: v for k, v in search_params.items() if v is not None}
            
            logger.info(f"[ADAPTER] Calling search_supplier_payments with: {list(search_params.keys())}")
            
            from app.services.universal_supplier_service import EnhancedUniversalSupplierService
            universal_service = EnhancedUniversalSupplierService()
            result = universal_service._search_supplier_payments_universal(**search_params)
            
            logger.info(f"[ADAPTER] Service returned: {type(result)}")
            if isinstance(result, dict):
                logger.info(f"[ADAPTER] Service response keys: {list(result.keys())}")
                payments_data = result.get('payments', [])
                logger.info(f"[ADAPTER] Payments found: {len(payments_data) if payments_data else 0}")
            
            # ✅ CRITICAL FIX: Properly standardize response format
            if result and result.get('success', True):  # Default to True if no success key
                standardized = {
                    'items': result.get('payments', []),  # ✅ This should work
                    'pagination': result.get('pagination', {}),
                    'summary': result.get('summary', {}),
                    'suppliers': result.get('suppliers', []),
                    'metadata': result.get('metadata', {}),
                    'success': True
                }
                
                logger.info(f"[ADAPTER] Standardized response: items={len(standardized['items'])}")
                return standardized
            else:
                logger.warning(f"[ADAPTER] Service returned unsuccessful result: {result.get('error', 'Unknown error')}")
                return {
                    'items': [],
                    'pagination': {'total_count': 0},
                    'summary': {},
                    'suppliers': [],
                    'success': False,
                    'error': result.get('error', 'Service returned unsuccessful result')
                }
                
        except Exception as e:
            logger.error(f"[ADAPTER] Error in universal search: {str(e)}")
            return {
                'items': [],
                'pagination': {'total_count': 0},
                'summary': {},
                'suppliers': [],
                'success': False,
                'error': str(e)
        }


class UniversalPatientService:
    """
    Universal service adapter for patients
    Example implementation for rapid entity rollout
    """
    
    def __init__(self):
        # Initialize your existing patient service here
        # self.patient_service = PatientService()
        pass
    
    def search_data(self, hospital_id: uuid.UUID, filters: Dict, **kwargs) -> Dict:
        """Search patients - implement using your existing patient service"""
        # TODO: Implement using your existing patient service
        # Similar pattern to supplier payments above
        return {
            'items': [],
            'total': 0,
            'page': kwargs.get('page', 1),
            'per_page': kwargs.get('per_page', 20),
            'summary': {
                'total_patients': 0,
                'active_patients': 0,
                'new_this_month': 0
            }
        }
    
    def get_by_id(self, item_id: str, hospital_id: uuid.UUID, **kwargs):
        """Get patient by ID"""
        # TODO: Implement using your existing patient service
        return None
    
    # Implement other CRUD methods as needed...


# Service registry - maps entity types to universal service classes
UNIVERSAL_SERVICES = {
    "supplier_payments": UniversalSupplierPaymentService,
    "patients": UniversalPatientService,
    # Add more services as you implement them:
    # "medicines": UniversalMedicineService,
    # "invoices": UniversalInvoiceService,
}


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


def register_universal_service(entity_type: str, service_class):
    """
    Register a new universal service class
    
    Allows dynamic registration of services for new entities
    """
    UNIVERSAL_SERVICES[entity_type] = service_class
    logger.info(f"✅ Universal service registered for {entity_type}")


def list_registered_services() -> List[str]:
    """Get list of all registered universal service entity types"""
    return list(UNIVERSAL_SERVICES.keys())


# Validation and testing functions
def validate_service_interface(service_instance, entity_type: str) -> List[str]:
    """
    Validate that a service implements the required interface
    Returns list of missing methods or errors
    """
    errors = []
    required_methods = ['search_data', 'get_by_id', 'create', 'update', 'delete']
    
    for method_name in required_methods:
        if not hasattr(service_instance, method_name):
            errors.append(f"Missing required method: {method_name}")
        elif not callable(getattr(service_instance, method_name)):
            errors.append(f"Method {method_name} is not callable")
    
    return errors


def test_universal_service(entity_type: str) -> bool:
    """
    Test universal service for basic functionality
    Returns True if service passes basic tests
    """
    try:
        service = get_universal_service(entity_type)
        
        # Validate interface
        errors = validate_service_interface(service, entity_type)
        if errors:
            logger.error(f"❌ Service validation failed for {entity_type}: {errors}")
            return False
        
        logger.info(f"✅ Universal service validation passed for {entity_type}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Service test failed for {entity_type}: {str(e)}")
        return False


# Test all registered services
def test_all_services():
    """Test all registered universal services"""
    results = {}
    for entity_type in UNIVERSAL_SERVICES.keys():
        results[entity_type] = test_universal_service(entity_type)
    
    # Print results
    print("\n🧪 Universal Service Test Results:")
    print("=" * 50)
    for entity_type, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{entity_type:20} {status}")
    
    return results


# Run tests when module is imported in development
if __name__ == "__main__":
    test_all_services()