# =============================================================================
# File: app/services/universal_supplier_service.py
# COMPLETE: Universal Supplier Service with ALL Entity-Specific Code
# Hospital and Branch Aware | Contains ALL Supplier-Specific Rendering
# =============================================================================

"""
Enhanced Universal Supplier Service - ALL Entity-Specific Code Moved Here
Contains ALL supplier-specific rendering, form integration, and business logic
Hospital and branch aware with configuration-driven behavior
"""

from typing import Dict, Any, Optional, List, Union
import uuid
from datetime import datetime, date, timedelta
from flask import request, url_for, current_app
from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc, func
from decimal import Decimal

from app.services.database_service import get_db_session, get_entity_dict
from app.models.transaction import SupplierPayment
from app.models.master import Supplier, Branch
from app.models.transaction import SupplierInvoice, SupplierPayment
from app.config.entity_configurations import get_entity_config, get_service_filter_mapping
from app.config.core_definitions import FieldDefinition, FieldType, ComplexDisplayType
from app.engine.categorized_filter_processor import get_categorized_filter_processor
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger
# from app.engine.universal_services import GenericEntitySearchService

logger = get_unicode_safe_logger(__name__)

class EnhancedUniversalSupplierService:
    """
    Enhanced universal service with ALL supplier-specific business logic
    Hospital and branch aware with complete form integration
    """
    
    def __init__(self):
        self.form_instance = None
        self.filter_processor = get_categorized_filter_processor()

    @cache_service_method('supplier_payments', 'search_data') 
    def search_data(self, filters: dict, **kwargs) -> dict:
        """
        ✅ UNIVERSAL INTERFACE: Simple wrapper that calls enhanced method
        This keeps universal service registry entity-agnostic while using enhanced logic
        """
        try:
            # Get the form class for supplier payments
            from flask_wtf import FlaskForm
            from wtforms import StringField, SelectField, SubmitField
            
            class SimpleFilterForm(FlaskForm):
                supplier_id = SelectField('Supplier', choices=[])
                submit = SubmitField('Filter')
            
            # Call the existing enhanced method with required parameters
            logger.info("🔄 Universal interface calling enhanced search")
            result = self.search_payments_with_form_integration(
                form_class=SimpleFilterForm,
                filters=filters,
                **kwargs
            )
            
            logger.info(f"✅ Universal interface completed: {len(result.get('items', []))} items")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in universal interface: {str(e)}")
            return {
                'items': [],
                'total': 0,
                'pagination': {'total_count': 0},
                'summary': {},
                'suppliers': [],
                'success': False,
                'error': str(e)
            }


    def search_payments_with_form_integration(self, form_class, **kwargs) -> Dict:
        """
        ✅ ENHANCED: Uses categorized filter processor while preserving all existing functionality
        Same signature and return structure, cleaner internal implementation
        """
        try:
            start_time = datetime.now()
            logger.info("🔄 Enhanced search with categorized filtering started")
            
            # ✅ PRESERVE: Form validation and population (same as before)
            if form_class is None:
                from flask_wtf import FlaskForm
                form_instance = FlaskForm()
                logger.warning("Using empty form instance")
            else:
                form_instance = form_class()
            
            # ✅ PRESERVE: Supplier-specific form population (same as before)
            self._populate_form_with_suppliers(form_instance)
            logger.debug("✅ Form population completed for supplier fields")
            
            # ✅ PRESERVE: Extract filters (same as before)
            filters = self._extract_complex_filters()
            
            # ✅ PRESERVE: Parameter handling (same as before)
            branch_id = kwargs.pop('branch_id', None)
            current_user_id = kwargs.pop('current_user_id', None)
            
            # Extract standard parameters
            hospital_id = kwargs.get('hospital_id') or (current_user.hospital_id if current_user else None)
            page = kwargs.get('page', 1)
            per_page = kwargs.get('per_page', 20)
            
            if not hospital_id:
                return self._get_error_fallback_result(form_class, "Hospital ID required")
            
            logger.info(f"🔍 Extracted filters: {list(filters.keys())}")
            
            # ✅ NEW: Call categorized filtering method instead of old complex method
            result = self._search_supplier_payments_with_categorized_filtering(
                hospital_id=hospital_id,
                filters=filters,
                branch_id=branch_id or request.args.get('branch_id'),
                current_user_id=current_user_id or (current_user.user_id if current_user else None),
                page=page,
                per_page=per_page
            )
            
            # ✅ PRESERVE: Enhance result with complete template data (same as before)
            enhanced_result = result.copy()
            enhanced_result.update({
                'form_instance': form_instance,
                'branch_context': {
                    'branch_id': branch_id,
                    'branch_name': request.args.get('branch_name', 'All Branches')
                },
                'request_args': request.args.to_dict(),
                'active_filters': self._build_active_filters(),
                'filtered_args': {k: v for k, v in request.args.items() if k != 'page'},
                'filters_applied': filters,
                'additional_context': {
                    'entity_type': 'supplier_payments',
                    'view_mode': 'list',
                    'user_permissions': self._get_user_permissions(),
                    'suppliers': self._get_suppliers_for_dropdown(),
                    'payment_config': self._get_payment_config_object()
                }
            })
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Enhanced search with categorized filtering completed in {elapsed_time:.3f}s")
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced search: {str(e)}")
            return self._get_error_fallback_result(form_class, str(e))
    
    def _search_supplier_payments_with_categorized_filtering(self, hospital_id: uuid.UUID, 
                                                       filters: Dict, 
                                                       branch_id: Optional[uuid.UUID] = None,
                                                       current_user_id: Optional[str] = None,
                                                       page: int = 1, per_page: int = 20) -> Dict:
        """
        ✅ NEW METHOD: Clean search using categorized filter processor
        Same return structure, much cleaner implementation
        """
        try:
            logger.info(f"🔍 Categorized filtering search started")
            logger.info(f"🔍 Hospital: {hospital_id}, Branch: {branch_id}")
            logger.info(f"🔍 Filters: {filters}")
            
            with get_db_session() as session:
                # STEP 1: Base query - same as before
                query = session.query(SupplierPayment).filter_by(hospital_id=hospital_id)
                
                # STEP 2: Branch filtering - same as before
                if branch_id:
                    query = query.filter(SupplierPayment.branch_id == branch_id)
                    logger.info(f"Applied branch filter: {branch_id}")
                
                # STEP 3: Apply categorized filters - ✅ NEW CLEAN IMPLEMENTATION
                config = get_entity_config('supplier_payments')
                
                query, applied_filters, filter_count = self.filter_processor.process_entity_filters(
                    entity_type='supplier_payments',
                    filters=filters,
                    query=query,
                    model_class=SupplierPayment,  # ✅ FIXED: Add model_class parameter
                    session=session,
                    config=config
                )
                
                logger.info(f"✅ Categorized processor applied {filter_count} filters: {applied_filters}")
                
                # STEP 4: Sorting - preserve existing logic
                sort_field = filters.get('sort_field', 'payment_date')
                sort_direction = filters.get('sort_direction', 'desc')
                
                if hasattr(SupplierPayment, sort_field):
                    sort_attr = getattr(SupplierPayment, sort_field)
                    if sort_direction.lower() == 'desc':
                        query = query.order_by(desc(sort_attr))
                    else:
                        query = query.order_by(asc(sort_attr))
                else:
                    query = query.order_by(desc(SupplierPayment.payment_date))
                
                # STEP 5: Get total count before pagination - same as before
                total_count = query.count()
                
                # STEP 6: Apply pagination - same as before
                offset = (page - 1) * per_page
                paginated_query = query.offset(offset).limit(per_page)
                
                # STEP 7: Execute query and get results
                payments = paginated_query.all()
                
                logger.info(f"✅ Query executed: {len(payments)} payments found")
                
                # STEP 8: Convert to dictionaries - preserve existing logic
                payment_dicts = []
                for payment in payments:
                    payment_dict = get_entity_dict(payment)
                    
                    # Add supplier information if available - same logic as before
                    if hasattr(payment, 'supplier') and payment.supplier:
                        payment_dict['supplier_name'] = payment.supplier.supplier_name
                        payment_dict['supplier_id'] = payment.supplier.supplier_id
                    
                    payment_dicts.append(payment_dict)
                
                # STEP 9: Calculate summary - preserve existing logic
                summary = self._calculate_basic_summary_from_filtered_results()
                
                # STEP 10: Build pagination info - same as before
                pagination = {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page,
                    'has_prev': page > 1,
                    'has_next': page < ((total_count + per_page - 1) // per_page)
                }
                
                # STEP 11: Get suppliers for dropdown - preserve existing logic
                suppliers = self._get_suppliers_for_dropdown()
                
                return {
                    'items': payment_dicts,
                    'total': total_count,
                    'pagination': pagination,
                    'summary': summary,
                    'suppliers': suppliers,
                    'success': True,
                    'metadata': {
                        'applied_filters': list(applied_filters),
                        'filter_count': filter_count,
                        'search_executed': True,
                        'processing_method': 'categorized_filtering'
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error in categorized filtering search: {str(e)}")
            return self._get_error_result(str(e))

    def _extract_complex_filters(self) -> Dict:
        """Extract filters matching EXACT existing payment_list filter logic"""
        try:
            filters = {}
            
            # SUPPLIER FILTERING (exact match to existing - multiple parameter names)
            supplier_id = request.args.get('supplier_id')
            supplier_search = request.args.get('supplier_search')
            supplier_text = request.args.get('supplier_text')
            supplier_name = request.args.get('supplier_name')
            search = request.args.get('search')
            
            if supplier_id and supplier_id.strip():
                filters['supplier_id'] = supplier_id
            elif supplier_search and supplier_search.strip():
                filters['supplier_name_search'] = supplier_search.strip()
            elif supplier_text and supplier_text.strip():
                filters['supplier_name_search'] = supplier_text.strip()
            elif supplier_name and supplier_name.strip():
                filters['supplier_name_search'] = supplier_name.strip()
            elif search and search.strip():
                filters['supplier_name_search'] = search.strip()
            
            # REFERENCE NO FILTERING (new field)
            reference_no = request.args.get('reference_no')
            if reference_no and reference_no.strip():
                filters['reference_no_search'] = reference_no.strip()

                        
            # ✅ NEW: SPECIAL BANK TRANSFER INCLUSIVE FILTERING
            payment_method = request.args.get('payment_method')
            if payment_method == 'bank_transfer_inclusive':
                # Special handling for bank transfers that includes mixed payments
                filters['bank_transfer_inclusive'] = True
                logger.info("🔍 [SPECIAL_FILTER] Applied bank_transfer_inclusive filter")
            else:
                # ✅ EXISTING: Standard payment method filtering (unchanged)
                payment_methods = request.args.getlist('payment_method')
                payment_methods = [method.strip() for method in payment_methods if method.strip()]
                if payment_methods:
                    filters['payment_methods'] = payment_methods
                    # ✅ FIX: Also set single payment_method for table query compatibility
                    filters['payment_method'] = payment_methods[0]
                    logger.info(f"🔍 [TABLE_FIX] Set payment_method='{payment_methods[0]}' for table query")
                elif request.args.get('payment_method'):
                    single_method = request.args.get('payment_method').strip()
                    filters['payment_methods'] = [single_method]
                    # ✅ FIX: Also set single payment_method for table query compatibility  
                    filters['payment_method'] = single_method
                    logger.info(f"🔍 [TABLE_FIX] Set payment_method='{single_method}' for table query")

            # STATUS FILTERING (exact match - supports multiple)
            statuses = request.args.getlist('status')
            statuses = [status.strip() for status in statuses if status.strip()]
            if statuses:
                filters['statuses'] = statuses
                # ✅ FIX: Also set single status for table query compatibility
                filters['status'] = statuses[0]
                filters['workflow_status'] = statuses[0]
                logger.info(f"🔍 [TABLE_FIX] Set status='{statuses[0]}' for table query")
            elif request.args.get('status'):
                single_status = request.args.get('status').strip()
                filters['statuses'] = [single_status]
                filters['status'] = single_status
                filters['workflow_status'] = single_status
                logger.info(f"🔍 [TABLE_FIX] Set status='{single_status}' for table query")
            elif request.args.get('workflow_status'):
                workflow_status = request.args.get('workflow_status').strip()
                filters['statuses'] = [workflow_status]
                filters['status'] = workflow_status
                filters['workflow_status'] = workflow_status
                logger.info(f"🔍 [TABLE_FIX] Set workflow_status='{workflow_status}' for table query")
            
            # DATE FILTERING with financial year default
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # If no dates provided, default to financial year
            if start_date:
                filters['start_date'] = start_date
            if end_date:
                filters['end_date'] = end_date

            
            # AMOUNT FILTERING (exact match - multiple parameter names)
            min_amount = request.args.get('min_amount') or request.args.get('amount_min')
            max_amount = request.args.get('max_amount') or request.args.get('amount_max')
            
            if min_amount and min_amount.strip():
                try:
                    filters['min_amount'] = float(min_amount)
                except ValueError:
                    pass
            
            if max_amount and max_amount.strip():
                try:
                    filters['max_amount'] = float(max_amount)
                except ValueError:
                    pass
            
            # ADDITIONAL FILTERS (exact match)
            search_term = request.args.get('search') or request.args.get('q')
            if search_term and search_term.strip():
                filters['search'] = search_term.strip()
            
            reference_no = request.args.get('reference_no') or request.args.get('ref_no')
            if reference_no and reference_no.strip():
                filters['reference_no'] = reference_no.strip()
            
            invoice_id = request.args.get('invoice_id')
            if invoice_id and invoice_id.strip():
                filters['invoice_id'] = invoice_id.strip()
            
            branch_id = request.args.get('branch_id')
            if branch_id and branch_id.strip():
                filters['branch_id'] = branch_id.strip()
            
            # PAGINATION
            page = request.args.get('page', 1)
            per_page = request.args.get('per_page', 20)
            
            try:
                filters['page'] = int(page)
            except ValueError:
                filters['page'] = 1
            
            try:
                filters['per_page'] = int(per_page)
            except ValueError:
                filters['per_page'] = 20
            
            # SORTING
            sort_field = request.args.get('sort') or request.args.get('sort_field')
            sort_direction = request.args.get('direction') or request.args.get('sort_direction')
            
            if sort_field:
                filters['sort_field'] = sort_field
            if sort_direction:
                filters['sort_direction'] = sort_direction
            
            # Clean empty values
            filters = {k: v for k, v in filters.items() if v is not None and v != ''}
            
            logger.debug(f"Extracted filters: {filters}")
            return filters
            
        except Exception as e:
            logger.error(f"Error extracting filters: {str(e)}")
            return {}
    
    def _search_supplier_payments_universal(self, hospital_id: uuid.UUID, filters: Dict, 
                                       branch_id: Optional[uuid.UUID] = None,
                                       current_user_id: Optional[str] = None,
                                       page: int = 1, per_page: int = 20,
                                       session: Optional[Session] = None) -> Dict:
        """
        ✅ UNIVERSAL ENGINE: Complete supplier payments search implementation
        Self-contained version that reads from filters parameter first, then request.args fallback
        """
        from app.services.database_service import get_db_session, get_entity_dict
        from app.models.transaction import SupplierPayment, SupplierInvoice
        from app.models.master import Supplier, Branch
        from flask import request
        from sqlalchemy import or_, and_, desc, func
        from datetime import datetime, date
        import time
        
        start_time = time.time()
        
        try:
            # Use provided session or create new one
            if session:
                session_scope = session
                should_close = False
            else:
                session_scope = get_db_session().__enter__()
                should_close = True
            
            try:
                # STEP 1: Base query
                step_start = time.time()
                query = session_scope.query(SupplierPayment).filter_by(hospital_id=hospital_id)
                logger.info(f"✅ [UNIVERSAL] STEP 1 - Base query: {time.time() - step_start:.3f}s")
                
                # STEP 2: Branch filtering
                step_start = time.time()
                if branch_id:
                    query = query.filter(SupplierPayment.branch_id == branch_id)
                    logger.info(f"Applied direct branch filter: {branch_id}")
                logger.info(f"✅ [UNIVERSAL] STEP 2 - Branch filter: {time.time() - step_start:.3f}s")
                
                
                # STEP 3: Apply categorized filters
                step_start = time.time()
                config = get_entity_config('supplier_payments')
                
                query, applied_filters, filter_count = self.filter_processor.process_entity_filters(
                    entity_type='supplier_payments',
                    filters=filters,
                    query=query,
                    model_class=SupplierPayment,  # ✅ FIXED: Add model_class parameter
                    session=session_scope,
                    config=config
                )

                
                # 4a: Ordering
                step_start = time.time()
                query = query.order_by(SupplierPayment.payment_date.desc())
                
                # 4b: Count query
                step_start = time.time()
                total_count = query.count()
                
                # 4c: Main query execution
                step_start = time.time()
                offset = (page - 1) * per_page
                payments = query.offset(offset).limit(per_page).all()
                
                # STEP 5: Result processing
                step_start = time.time()
                payment_dicts = []
                
                for payment in payments:
                    payment_dict = get_entity_dict(payment)
                    
                    # Add supplier information
                    supplier = session_scope.query(Supplier).filter_by(supplier_id=payment.supplier_id).first()
                    if supplier:
                        payment_dict['supplier_name'] = supplier.supplier_name
                        payment_dict['supplier_code'] = getattr(supplier, 'supplier_code', '')
                    else:
                        payment_dict['supplier_name'] = 'N/A'
                        payment_dict['supplier_code'] = 'N/A'
                    
                    # Add branch information
                    if payment.branch_id:
                        branch = session_scope.query(Branch).filter_by(branch_id=payment.branch_id).first()
                        if branch:
                            payment_dict['branch_name'] = branch.name
                    
                    # Add invoice information
                    if payment.invoice_id:
                        invoice = session_scope.query(SupplierInvoice).filter_by(invoice_id=payment.invoice_id).first()
                        if invoice:
                            payment_dict['invoice_number'] = invoice.supplier_invoice_number
                            payment_dict['invoice_amount'] = float(invoice.total_amount)
                    
                    payment_dicts.append(payment_dict)
                
                
                # STEP 6: Summary calculation using existing Universal Engine methods
                step_start = time.time()
                try:
                    summary = self._calculate_basic_summary_from_filtered_results()
                except Exception as e:
                    logger.error(f"Error calculating summary: {str(e)}")
                    summary = {
                        'total_count': total_count,
                        'total_amount': 0.0,
                        'pending_count': 0,
                        'this_month_count': 0
                    }
                
                # Final result
                total_time = time.time() - start_time
                
                # Get suppliers for dropdown
                suppliers = []
                try:
                    from app.services.supplier_service import get_suppliers_for_choice
                    suppliers = get_suppliers_for_choice(hospital_id, session_scope)
                except Exception as e:
                    logger.warning(f"Could not get suppliers: {str(e)}")
                
                return {
                    'success': True,
                    'payments': payment_dicts,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total_count': total_count,
                        'total_pages': max(1, (total_count + per_page - 1) // per_page)
                    },
                    'summary': summary,
                    'suppliers': suppliers,
                    'metadata': {
                        'search_time': total_time,
                        'filters_applied': len([f for f in filters.values() if f]),
                        'universal_engine': True
                    }
                }
                
            finally:
                if should_close and session_scope:
                    session_scope.__exit__(None, None, None)
                    
        except Exception as e:
            logger.error(f"❌ [UNIVERSAL] Error in supplier payment search: {str(e)}")
            return {
                'success': False,
                'payments': [],
                'pagination': {'total_count': 0, 'page': page, 'per_page': per_page, 'total_pages': 1},
                'summary': {'total_count': 0, 'total_amount': 0.0},
                'suppliers': [],
                'error': str(e)
            }

    @cache_service_method('supplier_payments', 'search_payments_enhanced')
    def _search_payments_enhanced(self, filters: Dict, branch_id=None, current_user_id=None, **kwargs) -> Dict:
        """
        FIXED: Enhanced search with clean parameter handling
        No longer accepts filters in kwargs to prevent conflicts
        """
        try:
            # Call existing supplier payment service using exact signature
            # from app.services.supplier_service import search_supplier_payments
            
            # Prepare parameters for existing service (exact signature match)
            search_params = {
                'hospital_id': current_user.hospital_id,
                'filters': filters,
                'current_user_id': current_user_id or current_user.user_id,
                'page': filters.get('page', 1),
                'per_page': filters.get('per_page', 20)
            }
            
            # Add branch context if available
            branch_uuid = None
            if branch_id:
                if isinstance(branch_id, str):
                    try:
                        branch_uuid = uuid.UUID(branch_id)
                    except ValueError:
                        logger.warning(f"Invalid branch_id format: {branch_id}")
                else:
                    branch_uuid = branch_id
            
            # Clean additional parameters (no filters to prevent conflict)
            additional_params = {k: v for k, v in kwargs.items() 
                            if k not in ['filters', 'hospital_id', 'current_user_id', 'page', 'per_page']}
            search_params.update(additional_params)
            
            logger.debug(f"Calling search_supplier_payments with params: {list(search_params.keys())}")
            
            # Call existing service
            result = self._search_supplier_payments_universal(
                hospital_id=current_user.hospital_id,
                filters=filters,
                branch_id=branch_uuid,
                current_user_id=current_user_id or current_user.user_id,
                page=filters.get('page', 1),
                per_page=filters.get('per_page', 20),
                session=None
            )
            
            # Standardize response format for universal engine
            if result and result.get('success', True):

                payments = result.get('payments', []) or result.get('items', []) or result.get('data', [])
                if not payments and 'results' in result:
                    payments = result['results']
                    
                existing_summary = result.get('summary', {})

                # Also ensure total count is properly set
                if 'total' not in result and payments:
                    result['total'] = len(payments)
                
                # Apply enhanced summary calculation
                enhanced_summary = self._calculate_enhanced_summary(payments, existing_summary)

                if filters.get('bank_transfer_inclusive'):
                    
                    # Filter the already-fetched records for bank transfers
                    filtered_payments = []
                    for payment in payments:
                        payment_method = payment.get('payment_method', '')
                        bank_amount = payment.get('bank_transfer_amount', 0)
                        
                        # Convert bank_amount to float for comparison
                        try:
                            bank_amount_float = float(bank_amount) if bank_amount not in [None, '', 'None'] else 0.0
                        except (ValueError, TypeError):
                            bank_amount_float = 0.0
                        
                        # Include if pure bank transfer OR mixed with bank amount
                        if payment_method == 'bank_transfer' or bank_amount_float > 0:
                            filtered_payments.append(payment)
                    
                    
                    # Return filtered results with original pagination context
                    return {
                        'items': filtered_payments,
                        'total': result.get('pagination', {}).get('total_count', 0),  # Keep original total
                        'pagination': result.get('pagination', {}),  # Keep original pagination
                        'summary': enhanced_summary,
                        'suppliers': result.get('suppliers', []),
                        'success': True,
                        'metadata': result.get('metadata', {}),
                        'search_executed': True
                    }
                else:
                    # ✅ EXISTING: Standard return (unchanged)
                    return {
                        'items': payments,
                        'total': result.get('pagination', {}).get('total_count', 0),
                        'pagination': result.get('pagination', {}),
                        'summary': enhanced_summary,  # ✅ Use enhanced summary instead of original
                        'suppliers': result.get('suppliers', []),
                        'success': True,
                        'metadata': result.get('metadata', {}),
                        'search_executed': True
                    }
            else:
                return self._get_empty_result_with_metadata()
                
        except Exception as e:
            logger.error(f"Error in enhanced payment search: {str(e)}")
            return self._get_error_result(str(e))
    
    def _calculate_enhanced_summary(self, payments: List[Dict], existing_summary: Dict = None) -> Dict:
        """
        ✅ CONFIGURATION-DRIVEN: Add missing fields to existing summary
        Respects card configuration for filterable vs static cards
        Handles basic field recalculation for filtered results
        """
        try:
            if existing_summary and isinstance(existing_summary, dict):
                
                # ✅ Start with existing summary (4 fields)
                enhanced_summary = existing_summary.copy()
                
                # ✅ CONFIGURATION-DRIVEN: Get card configurations
                from app.config.entity_configurations import get_entity_config
                config = get_entity_config('supplier_payments')
                
                # ✅ NEW: Build filterable/static field mapping from configuration
                filterable_fields = set()
                static_fields = set()
                
                if config and hasattr(config, 'summary_cards'):
                    for card_config in config.summary_cards:
                        field_name = card_config.get('field', '')
                        is_filterable = card_config.get('filterable', False)
                        
                        if field_name:
                            if is_filterable:
                                filterable_fields.add(field_name)
                            else:
                                static_fields.add(field_name)
                                
                
                # ✅ NEW: Recalculate basic summary fields if they are filterable and filters are applied
                basic_filterable_fields = [f for f in ['total_count', 'total_amount'] 
                                        if f in filterable_fields]

                if basic_filterable_fields and self._has_active_filters():
                    
                    # Get filtered totals from the actual filtered results
                    filtered_totals = self._calculate_basic_summary_from_filtered_results()
                    
                    for field in basic_filterable_fields:
                        if field in filtered_totals:
                            old_value = enhanced_summary.get(field, 0)
                            enhanced_summary[field] = filtered_totals[field]
                
                # ✅ ENHANCED: Get database counts with configuration-aware filtering
                status_fields = ['approved_count', 'completed_count', 'bank_transfer_count', 'pending_count']

                # Separate fields that need filtering vs static calculation
                filterable_status_fields = [f for f in status_fields if f in filterable_fields]
                static_status_fields = [f for f in status_fields if f in static_fields]

                # Get filterable card counts (respect current filters) - RECALCULATE ALL when filters applied
                if filterable_status_fields and self._has_active_filters():
                    filtered_counts = self._get_actual_database_counts(respect_current_filters=True)
                    
                    for field in filterable_status_fields:
                        old_value = enhanced_summary.get(field, 0)
                        enhanced_summary[field] = filtered_counts.get(field, 0)

                # Get filterable counts without filters if no active filters
                elif filterable_status_fields and not self._has_active_filters():
                    missing_filterable_fields = [f for f in filterable_status_fields if f not in enhanced_summary]
                    if missing_filterable_fields:
                        unfiltered_counts = self._get_actual_database_counts(respect_current_filters=True)
                        
                        for field in missing_filterable_fields:
                            enhanced_summary[field] = unfiltered_counts.get(field, 0)

                # Get static card counts (always use "this month" regardless of filters)  
                if static_status_fields:
                    missing_static_fields = [f for f in static_status_fields if f not in enhanced_summary]
                    if missing_static_fields:
                        static_counts = self._get_actual_database_counts(respect_current_filters=False)
                        
                        for field in missing_static_fields:
                            enhanced_summary[field] = static_counts.get(field, 0)
                
                # ✅ BACKWARD COMPATIBLE: Handle fields not in configuration (use existing logic)
                remaining_fields = [f for f in ['approved_count', 'completed_count', 'bank_transfer_count'] 
                                if f not in enhanced_summary]
                if remaining_fields:
                    fallback_counts = self._get_actual_database_counts()
                    
                    for field in remaining_fields:
                        enhanced_summary[field] = fallback_counts.get(field, 0)
                
                # ✅ SPECIAL HANDLING: this_month_amount (configuration-driven static calculation)
                if 'this_month_amount' not in enhanced_summary:
                    if 'this_month_amount' in static_fields:
                        # Static field - always use actual this month amount regardless of filters
                        enhanced_summary['this_month_amount'] = self._calculate_this_month_amount_from_database(enhanced_summary)
                    else:
                        # Existing logic for backward compatibility
                        this_month_count = enhanced_summary.get('this_month_count', 0)
                        total_count = enhanced_summary.get('total_count', 0)
                        total_amount = enhanced_summary.get('total_amount', 0)
                        
                        if this_month_count == total_count and total_count > 0:
                            enhanced_summary['this_month_amount'] = total_amount
                        else:
                            if total_count > 0:
                                ratio = this_month_count / total_count
                                enhanced_summary['this_month_amount'] = total_amount * ratio
                            else:
                                enhanced_summary['this_month_amount'] = 0
                
                return enhanced_summary
            
            # ✅ Fallback: If no existing summary, calculate everything from page items
            else:
                logger.warning("🔄 No existing summary provided, calculating from page items")
                return self._calculate_fallback_summary_from_items(payments)
            
        except Exception as e:
            logger.error(f"❌ Error in enhanced summary calculation: {str(e)}")
            # Return existing summary as fallback
            return existing_summary if existing_summary else {}

    def _has_active_filters(self) -> bool:
        """Check if there are any active filters applied"""
        from flask import request
        
        # Check for all possible filter types
        filter_params = [
            'start_date', 'end_date',  # Date filters
            'supplier_id', 'supplier_search', 'supplier_name_search', 'search',  # Supplier filters
            'workflow_status', 'payment_method',  # Status filters
            'approved_by', 'created_by'  # User filters
        ]
        
        for param in filter_params:
            value = request.args.get(param)
            if value and str(value).strip():
                return True
        
        # If no explicit filters, we always have financial year default filters, so always return True
        # This ensures summary cards are always properly calculated
        return True

    def get_filter_state_for_frontend(self) -> Dict:
        """Get filter state information for frontend synchronization"""
        from flask import request
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # If no dates in URL, we're using FY default
        if not start_date and not end_date:
            from datetime import date
            today = date.today()
            if today.month >= 4:  # April onwards - current FY
                fy_start = date(today.year, 4, 1)
                fy_end = date(today.year + 1, 3, 31)
            else:  # January to March - previous FY
                fy_start = date(today.year - 1, 4, 1)
                fy_end = date(today.year, 3, 31)
            
            return {
                'default_preset': 'financial_year',
                'start_date': fy_start.strftime('%Y-%m-%d'),
                'end_date': fy_end.strftime('%Y-%m-%d'),
                'is_default_state': True
            }
        
        return {
            'default_preset': 'none',
            'start_date': start_date,
            'end_date': end_date,
            'is_default_state': False
        }

    def _calculate_basic_summary_from_filtered_results(self) -> Dict:
        """Calculate total_count and total_amount from filtered database query"""
        try:
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierPayment
            from app.models.master import Supplier
            from sqlalchemy import func
            from flask_login import current_user
            from flask import request
            from datetime import datetime
            
            with get_db_session() as session:
                # Same base query as _get_actual_database_counts but for totals
                base_query = session.query(SupplierPayment).filter_by(
                    hospital_id=current_user.hospital_id
                )
                
                # Apply same date filters as current request
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                
                if start_date:
                    try:
                        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                        base_query = base_query.filter(SupplierPayment.payment_date >= start_date_obj)
                    except ValueError:
                        pass
                        
                if end_date:
                    try:
                        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                        base_query = base_query.filter(SupplierPayment.payment_date <= end_date_obj)
                    except ValueError:
                        pass
                

                # Apply supplier filters (same logic as main query)
                supplier_name_search = request.args.get('supplier_name_search')
                search = request.args.get('search')
                supplier_id = request.args.get('supplier_id')
                
                if supplier_id and supplier_id.strip():
                    base_query = base_query.filter(SupplierPayment.supplier_id == supplier_id)
                elif supplier_name_search and supplier_name_search.strip():
                    # Apply same supplier name search logic as main query
                    supplier_subquery = session.query(Supplier.supplier_id).filter(
                        Supplier.hospital_id == current_user.hospital_id,
                        Supplier.supplier_name.ilike(f'%{supplier_name_search}%')
                    ).subquery()
                    base_query = base_query.filter(SupplierPayment.supplier_id.in_(supplier_subquery))
                elif search and search.strip():
                    # Apply same general search logic as main query
                    supplier_subquery = session.query(Supplier.supplier_id).filter(
                        Supplier.hospital_id == current_user.hospital_id,
                        Supplier.supplier_name.ilike(f'%{search}%')
                    ).subquery()
                    base_query = base_query.filter(SupplierPayment.supplier_id.in_(supplier_subquery))

                # Apply status filters
                workflow_status = request.args.get('workflow_status')
                status = request.args.get('status')
                if workflow_status and workflow_status.strip():
                    base_query = base_query.filter(SupplierPayment.workflow_status == workflow_status)
                elif status and status.strip():
                    base_query = base_query.filter(SupplierPayment.workflow_status == status)
                
                # Apply payment method filters
                payment_method = request.args.get('payment_method')
                if payment_method and payment_method.strip():
                    if payment_method == 'bank_transfer_inclusive':
                        # Special handling for bank transfer inclusive
                        base_query = base_query.filter(
                            or_(
                                SupplierPayment.payment_method == 'bank_transfer',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.bank_transfer_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'cash':
                        base_query = base_query.filter(
                            or_(
                                SupplierPayment.payment_method == 'cash',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.cash_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'cheque':
                        base_query = base_query.filter(
                            or_(
                                SupplierPayment.payment_method == 'cheque',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.cheque_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'bank_transfer':
                        base_query = base_query.filter(
                            or_(
                                SupplierPayment.payment_method == 'bank_transfer',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.bank_transfer_amount > 0
                                )
                            )
                        )
                    elif payment_method == 'upi':
                        base_query = base_query.filter(
                            or_(
                                SupplierPayment.payment_method == 'upi',
                                and_(
                                    SupplierPayment.payment_method == 'mixed',
                                    SupplierPayment.upi_amount > 0
                                )
                            )
                        )
                    else:
                        base_query = base_query.filter(SupplierPayment.payment_method == payment_method)
                
                # Apply amount range filters
                min_amount = request.args.get('min_amount') or request.args.get('amount_min')
                max_amount = request.args.get('max_amount') or request.args.get('amount_max')
                
                if min_amount:
                    try:
                        min_val = float(min_amount)
                        base_query = base_query.filter(SupplierPayment.amount >= min_val)
                    except ValueError:
                        pass
                
                if max_amount:
                    try:
                        max_val = float(max_amount)
                        base_query = base_query.filter(SupplierPayment.amount <= max_val)
                    except ValueError:
                        pass
                
                # Apply reference number filter
                reference_no = request.args.get('reference_no') or request.args.get('ref_no')
                if reference_no and reference_no.strip():
                    base_query = base_query.filter(SupplierPayment.reference_no.ilike(f'%{reference_no}%'))
                
                # Apply invoice ID filter
                invoice_id = request.args.get('invoice_id')
                if invoice_id and invoice_id.strip():
                    base_query = base_query.filter(SupplierPayment.invoice_id == invoice_id)

                # If no date filters specified, use financial year default
                if not start_date and not end_date:
                    from datetime import date
                    today = date.today()
                    if today.month >= 4:  # April onwards - current FY
                        fy_start = date(today.year, 4, 1)
                        fy_end = date(today.year + 1, 3, 31)
                    else:  # January to March - previous FY
                        fy_start = date(today.year - 1, 4, 1)
                        fy_end = date(today.year, 3, 31)
                    
                    base_query = base_query.filter(
                        SupplierPayment.payment_date >= fy_start,
                        SupplierPayment.payment_date <= fy_end
                    )
                
                # Calculate filtered totals
                total_count = base_query.count()
                total_amount = base_query.with_entities(func.sum(SupplierPayment.amount)).scalar() or 0
                
                logger.info(f"🎯 [FILTERED] Calculated from database - Count: {total_count}, Amount: {total_amount}")
                
                return {
                    'total_count': total_count,
                    'total_amount': float(total_amount)
                }
                
        except Exception as e:
            logger.error(f"❌ Error calculating filtered basic summary: {str(e)}")
            return {}

    def _calculate_this_month_amount_from_database(self, existing_summary: Dict) -> float:
        """Calculate this month amount using database query with same filters"""
        try:
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierPayment
            from sqlalchemy import func
            from flask_login import current_user
            from datetime import datetime, date
            
            # Get current month start date
            current_month = datetime.now().month
            current_year = datetime.now().year
            this_month_start = date(current_year, current_month, 1)
            
            with get_db_session() as session:
                # Build same query as supplier_service but with this_month filter
                query = session.query(SupplierPayment).filter_by(
                    hospital_id=current_user.hospital_id
                ).filter(
                    SupplierPayment.payment_date >= this_month_start
                )
                
                # Apply same default filters as supplier_service (current month date range)
                today = date.today()
                default_start = today.replace(day=1)
                query = query.filter(
                    SupplierPayment.payment_date >= default_start,
                    SupplierPayment.payment_date <= today
                )
                
                this_month_amount = query.with_entities(
                    func.sum(SupplierPayment.amount)
                ).scalar() or 0
                
                logger.info(f"🎯 Calculated this month amount from database: {this_month_amount}")
                return float(this_month_amount)
                
        except Exception as e:
            logger.error(f"Error calculating this month amount from database: {str(e)}")
            return 0.0

    def _calculate_fallback_summary_from_items(self, payments: List[Dict]) -> Dict:
        """Calculate complete summary from page items when no existing summary"""
        from decimal import Decimal
        from datetime import datetime
        
        try:
            total_count = len(payments)
            total_amount = sum(Decimal(str(p.get('amount', 0))) for p in payments)
            
            # Count by status
            pending_count = len([p for p in payments if p.get('workflow_status') == 'pending'])
            approved_count = len([p for p in payments if p.get('workflow_status') == 'approved'])
            completed_count = len([p for p in payments if p.get('workflow_status') == 'completed'])
            # ✅ COMPREHENSIVE bank transfer counting in fallback
            bank_transfer_count = 0
            for payment in payments:
                payment_method = payment.get('payment_method', '')
                bank_amount = payment.get('bank_transfer_amount', 0)
                
                # Convert bank_amount to float for comparison
                try:
                    bank_amount_float = float(bank_amount) if bank_amount not in [None, '', 'None'] else 0.0
                except (ValueError, TypeError):
                    bank_amount_float = 0.0
                
                # Count as bank transfer if pure bank transfer OR mixed with bank amount
                if payment_method == 'bank_transfer' or bank_amount_float > 0:
                    bank_transfer_count += 1

            logger.info(f"🔍 [FALLBACK] Calculated bank_transfer_count: {bank_transfer_count}")
            
            # Calculate this month data
            current_month = datetime.now().month
            current_year = datetime.now().year
            this_month_count = 0
            this_month_amount = Decimal('0.00')
            
            for payment in payments:
                payment_date = payment.get('payment_date')
                if payment_date:
                    if isinstance(payment_date, str):
                        try:
                            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    if hasattr(payment_date, 'month') and hasattr(payment_date, 'year'):
                        if payment_date.month == current_month and payment_date.year == current_year:
                            this_month_count += 1
                            this_month_amount += Decimal(str(payment.get('amount', 0)))
            
            return {
                'total_count': total_count,
                'total_amount': float(total_amount),
                'pending_count': pending_count,
                'approved_count': approved_count,
                'completed_count': completed_count,
                'this_month_count': this_month_count,
                'this_month_amount': float(this_month_amount),
                'bank_transfer_count': bank_transfer_count,
                'calculation_method': 'fallback_from_page_items'
            }
            
        except Exception as e:
            logger.error(f"❌ Error in fallback summary calculation: {str(e)}")
            return {
                'total_count': 0, 'total_amount': 0.0, 'pending_count': 0, 'approved_count': 0,
                'completed_count': 0, 'this_month_amount': 0.0, 'bank_transfer_count': 0, 'this_month_count': 0
            }


    def _calculate_this_month_amount_from_page_items(self, payments: List[Dict]) -> float:
        """Helper method to calculate this month amount from page items"""
        try:
            current_month = datetime.now().month
            current_year = datetime.now().year
            this_month_amount = Decimal('0.00')
            
            for payment in payments:
                payment_date = payment.get('payment_date')
                if payment_date:
                    if isinstance(payment_date, str):
                        try:
                            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                        except ValueError:
                            continue
                    if hasattr(payment_date, 'month') and hasattr(payment_date, 'year'):
                        if payment_date.month == current_month and payment_date.year == current_year:
                            this_month_amount += Decimal(str(payment.get('amount', 0)))
            
            return float(this_month_amount)
        except Exception as e:
            logger.error(f"Error calculating this month amount: {str(e)}")
            return 0.0
    
    def _get_actual_database_counts(self, respect_current_filters: bool = True) -> Dict:
        """Get actual counts from database for enhanced summary fields"""
        try:
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierPayment
            from sqlalchemy import func, or_, and_
            from flask_login import current_user
            from flask import request
            from datetime import datetime, date
            
            with get_db_session() as session:
                # Base query matching the same filters as the main search
                base_query = session.query(SupplierPayment).filter_by(
                    hospital_id=current_user.hospital_id
                )
                
                # Apply date filters based on card configuration
                if respect_current_filters:
                    # For filterable cards - apply current user filters
                    start_date = request.args.get('start_date')
                    end_date = request.args.get('end_date')
                    
                    if start_date:
                        try:
                            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                            base_query = base_query.filter(SupplierPayment.payment_date >= start_date_obj)
                        except ValueError:
                            pass
                            
                    if end_date:
                        try:
                            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                            base_query = base_query.filter(SupplierPayment.payment_date <= end_date_obj)
                        except ValueError:
                            pass

                    # Apply supplier filters (same logic as main query)
                    from app.models.master import Supplier
                    supplier_name_search = request.args.get('supplier_name_search')
                    search = request.args.get('search')
                    supplier_id = request.args.get('supplier_id')
                    
                    if supplier_id and supplier_id.strip():
                        base_query = base_query.filter(SupplierPayment.supplier_id == supplier_id)
                    elif supplier_name_search and supplier_name_search.strip():
                        # Apply same supplier name search logic as main query
                        supplier_subquery = session.query(Supplier.supplier_id).filter(
                            Supplier.hospital_id == current_user.hospital_id,
                            Supplier.supplier_name.ilike(f'%{supplier_name_search}%')
                        ).subquery()
                        base_query = base_query.filter(SupplierPayment.supplier_id.in_(supplier_subquery))
                    elif search and search.strip():
                        # Apply same general search logic as main query
                        supplier_subquery = session.query(Supplier.supplier_id).filter(
                            Supplier.hospital_id == current_user.hospital_id,
                            Supplier.supplier_name.ilike(f'%{search}%')
                        ).subquery()
                        base_query = base_query.filter(SupplierPayment.supplier_id.in_(supplier_subquery))

                    # Apply status filters
                    workflow_status = request.args.get('workflow_status')
                    status = request.args.get('status')
                    if workflow_status and workflow_status.strip():
                        base_query = base_query.filter(SupplierPayment.workflow_status == workflow_status)
                    elif status and status.strip():
                        base_query = base_query.filter(SupplierPayment.workflow_status == status)
                    
                    # Apply payment method filters
                    payment_method = request.args.get('payment_method')
                    if payment_method and payment_method.strip():
                        if payment_method == 'bank_transfer_inclusive':
                            # Special handling for bank transfer inclusive
                            base_query = base_query.filter(
                                or_(
                                    SupplierPayment.payment_method == 'bank_transfer',
                                    and_(
                                        SupplierPayment.payment_method == 'mixed',
                                        SupplierPayment.bank_transfer_amount > 0
                                    )
                                )
                            )
                        else:
                            base_query = base_query.filter(SupplierPayment.payment_method == payment_method)
                    
                    # Apply amount range filters
                    min_amount = request.args.get('min_amount') or request.args.get('amount_min')
                    max_amount = request.args.get('max_amount') or request.args.get('amount_max')
                    
                    if min_amount:
                        try:
                            min_val = float(min_amount)
                            base_query = base_query.filter(SupplierPayment.amount >= min_val)
                        except ValueError:
                            pass
                    
                    if max_amount:
                        try:
                            max_val = float(max_amount)
                            base_query = base_query.filter(SupplierPayment.amount <= max_val)
                        except ValueError:
                            pass
                    
                    # Apply reference number filter
                    reference_no = request.args.get('reference_no') or request.args.get('ref_no')
                    if reference_no and reference_no.strip():
                        base_query = base_query.filter(SupplierPayment.reference_no.ilike(f'%{reference_no}%'))
                    
                    # Apply invoice ID filter
                    invoice_id = request.args.get('invoice_id')
                    if invoice_id and invoice_id.strip():
                        base_query = base_query.filter(SupplierPayment.invoice_id == invoice_id)


                    # If no date filters specified, use financial year default
                    if not start_date and not end_date:
                        from datetime import date
                        today = date.today()
                        if today.month >= 4:  # April onwards - current FY
                            fy_start = date(today.year, 4, 1)
                            fy_end = date(today.year + 1, 3, 31)
                        else:  # January to March - previous FY
                            fy_start = date(today.year - 1, 4, 1)
                            fy_end = date(today.year, 3, 31)
                        
                        base_query = base_query.filter(
                            SupplierPayment.payment_date >= fy_start,
                            SupplierPayment.payment_date <= fy_end
                        )
                else:
                    # For non-filterable cards - always use "this month" regardless of filters
                    today = date.today()
                    default_start = today.replace(day=1)
                    base_query = base_query.filter(
                        SupplierPayment.payment_date >= default_start,
                        SupplierPayment.payment_date <= today
                    )
                
                # Count by workflow status
                approved_count = base_query.filter(
                    SupplierPayment.workflow_status == 'approved'
                ).count()

                completed_count = base_query.filter(
                    SupplierPayment.workflow_status == 'completed'
                ).count()

                pending_count = base_query.filter(
                    SupplierPayment.workflow_status == 'pending'
                ).count()
                
                # Count bank transfers (both pure and mixed)
                bank_transfer_count = base_query.filter(
                    or_(
                        SupplierPayment.payment_method == 'bank_transfer',
                        and_(
                            SupplierPayment.payment_method == 'mixed',
                            SupplierPayment.bank_transfer_amount > 0
                        )
                    )
                ).count()
                
                logger.info(f"🎯 [DATABASE] Actual counts - Approved: {approved_count}, Completed: {completed_count}, Bank Transfers: {bank_transfer_count}")
                
                return {
                    'approved_count': approved_count,
                    'completed_count': completed_count,
                    'pending_count': pending_count,
                    'bank_transfer_count': bank_transfer_count
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting database counts: {str(e)}")
            return {
                'approved_count': 0,
                'completed_count': 0,
                'bank_transfer_count': 0
            }

    

    # ========================================================================
    # SUPPLIER-SPECIFIC RENDERING METHODS (Moved from data_assembler.py)
    # ========================================================================
    
    def _populate_form_with_suppliers(self, form_instance: FlaskForm):
        """
        ✅ FIX: Fixed form population with proper supplier choice handling
        """
        try:
            # ✅ TRY CONFIGURATION-DRIVEN APPROACH FIRST
            config_populated = False
            
            config_success, config = self._get_validated_entity_config('supplier_payments')
            
            if config_success and hasattr(config, 'fields'):
                logger.debug("🔧 Attempting configuration-driven form population")
                
                for field in config.fields:
                    if (hasattr(field, 'autocomplete_enabled') and 
                        field.autocomplete_enabled and 
                        hasattr(form_instance, field.name)):
                        
                        autocomplete_source = getattr(field, 'autocomplete_source', None)
                        form_field = getattr(form_instance, field.name)
                        
                        if autocomplete_source == 'suppliers':
                            try:
                                from app.utils.form_helpers import populate_supplier_choices
                                # ✅ FIX: Pass the form field correctly
                                populate_supplier_choices(form_field, current_user)
                                config_populated = True
                                logger.debug(f"✅ Config-driven population: {field.name}")
                            except Exception as e:
                                logger.debug(f"❌ Config population failed for {field.name}: {str(e)}")

                        # ✅ FALLBACK TO EXISTING LOGIC - Fix the hasattr check
                        if not config_populated:
                            logger.debug("🔧 Using fallback form population logic")
                            if hasattr(form_instance, 'supplier_id'):
                                try:
                                    from app.utils.form_helpers import populate_supplier_choices
                                    # ✅ FIX: Pass the form_instance, not the field directly
                                    populate_supplier_choices(form_instance.supplier_id, current_user)
                                    logger.debug("✅ Fallback population: supplier_id")
                                except Exception as e:
                                    logger.error(f"Error populating supplier choices: {str(e)}")
                                    logger.debug("✅ Fallback population: supplier_id")
                            else:
                                logger.debug("❌ No supplier_id field found")
                
                logger.debug("✅ Form population completed")
                
        except Exception as e:
            logger.warning(f"❌ Error populating form choices: {str(e)}")
    
    def _populate_backend_autocomplete(self, form_field, field_config, current_user):
        """Helper method for backend-driven autocomplete population"""
        # Implementation depends on your specific backend autocomplete needs
        # This can be expanded as needed
        pass

    def _get_suppliers_for_dropdown(self) -> List[Dict]:
        """
        ✅ FIX: Fixed supplier dropdown function with proper error handling
        """
        try:
            from app.services.supplier_service import get_suppliers_for_choice
            
            # ✅ FIX: Try with hospital_id first, fallback to no parameters
            try:
                # New signature: get_suppliers_for_choice(hospital_id)
                return get_suppliers_for_choice(current_user.hospital_id)
            except TypeError:
                # Old signature: get_suppliers_for_choice()
                logger.info("✅ [FALLBACK] Using get_suppliers_for_choice() without parameters")
                return get_suppliers_for_choice()
            except Exception as e:
                logger.warning(f"❌ Error calling get_suppliers_for_choice with hospital_id: {str(e)}")
                # Try without parameters as fallback
                try:
                    return get_suppliers_for_choice()
                except Exception as e2:
                    logger.error(f"❌ Error calling get_suppliers_for_choice without parameters: {str(e2)}")
                    return []
                    
        except ImportError:
            logger.warning("❌ Could not import get_suppliers_for_choice")
            return []
        except Exception as e:
            logger.warning(f"❌ Error getting suppliers for dropdown: {str(e)}")
            return []
    
    def _get_payment_config_object(self):
        """Get payment configuration object for template compatibility"""
        try:
            from app.config import PAYMENT_CONFIG
            return PAYMENT_CONFIG
        except ImportError:
            logger.warning("Could not import PAYMENT_CONFIG")
            return None
    
    def _get_user_permissions(self) -> Dict:
        """Get user permissions for template"""
        
        try:
            from app.services.permission_service import has_branch_permission
            
            return {
                'can_view': has_branch_permission(current_user, 'payment', 'view'),
                'can_create': has_branch_permission(current_user, 'payment', 'create'),
                'can_edit': has_branch_permission(current_user, 'payment', 'edit'),
                'can_approve': has_branch_permission(current_user, 'payment', 'approve'),
                'can_delete': has_branch_permission(current_user, 'payment', 'delete'),
                'can_export': has_branch_permission(current_user, 'payment', 'export')
            }
        except Exception as e:
            logger.warning(f"Error getting user permissions: {str(e)}")
            return {
                'can_view': True,
                'can_create': False,
                'can_edit': False,
                'can_approve': False,
                'can_delete': False,
                'can_export': False
            }
    
    def _build_active_filters(self) -> Dict:
        """Build active filters for template"""
        
        active_filters = {}
        
        try:
            for key, value in request.args.items():
                if key not in ['page', 'per_page'] and value and value.strip():
                    active_filters[key] = {
                        'value': value.strip(),
                        'label': key.replace('_', ' ').title(),
                        'remove_url': self._get_filter_remove_url(key)
                    }
        except Exception as e:
            logger.warning(f"Error building active filters: {str(e)}")
        
        return active_filters
    
    def _get_filter_remove_url(self, filter_key: str) -> str:
        """Generate URL to remove specific filter"""
        
        try:
            current_args = dict(request.args)
            if filter_key in current_args:
                del current_args[filter_key]
            if 'page' in current_args:
                del current_args['page']  # Reset pagination
            
            return url_for(request.endpoint, **current_args)
        except Exception:
            return '#'
    
    def _get_error_fallback_result(self, form_class, error: str) -> Dict:
        """Error fallback matching existing error handling"""
        
        return {
            'payments': [],
            'total': 0,
            'page': 1,
            'per_page': 20,
            'summary': {
                'total_count': 0, 
                'total_amount': Decimal('0.00'), 
                'pending_count': 0, 
                'this_month_count': 0
            },
            'form_instance': form_class(request.args) if form_class else None,
            'branch_context': {},
            'request_args': {},
            'active_filters': {},
            'filtered_args': {},
            'error': error,
            'error_timestamp': datetime.now().isoformat()
        }
    
    """
    MINIMAL CHANGES: Update existing _apply_configuration_filters_if_available method
    to use universal database filtering with entity-specific fallback
    """

        
    def _get_validated_entity_config(self, entity_type: str = 'supplier_payments') -> tuple[bool, Any]:
        """
        ✅ HELPER: Get and validate entity configuration
        Returns (success: bool, config: EntityConfiguration)
        """
        try:
            from app.config.entity_configurations import get_entity_config
            config = get_entity_config(entity_type)
            
            if not config:
                logger.debug(f"No configuration found for {entity_type}")
                return False, None
            
            # Validate required attributes exist
            required_attrs = ['fields']
            for attr in required_attrs:
                if not hasattr(config, attr):
                    logger.debug(f"Configuration missing {attr} for {entity_type}")
                    return False, None
            
            return True, config
            
        except Exception as e:
            logger.debug(f"Configuration validation failed for {entity_type}: {str(e)}")
            return False, None

    def _get_error_result(self, error_message: str, form_class=None) -> dict:
        """Error result structure - local implementation to avoid circular import"""
        return {
            'items': [],
            'payments': [],  # backward compatibility
            'total': 0,
            'page': 1,
            'per_page': 20,
            'summary': {
                'total_count': 0,
                'total_amount': Decimal('0.00'),
                'pending_count': 0,
                'this_month_count': 0
            },
            'form_instance': form_class() if form_class else None,
            'branch_context': {},
            'error': error_message,
            'error_timestamp': datetime.now().isoformat(),
            'success': False
        }
# =============================================================================
# SUPPLIER PAYMENT RENDERER (Entity-Specific Rendering for Data Assembler)
# =============================================================================

class SupplierPaymentRenderer:
    """
    Supplier-specific rendering methods for universal data assembler
    Contains ALL supplier payment-specific display logic
    """
    
    def render_field(self, field: FieldDefinition, value: Any, item: Dict) -> Optional[Dict]:
        """Render supplier-specific fields"""
        
        try:
            # Multi-method payment rendering
            if hasattr(field, 'complex_display_type') and field.complex_display_type == ComplexDisplayType.MULTI_METHOD_PAYMENT:
                return self._render_multi_method_payment(item, field)
            
            # Supplier column rendering
            elif field.name == 'supplier_name':
                return self._render_supplier_column(item, field)
            
            # Status badge rendering
            elif field.field_type == FieldType.STATUS_BADGE:
                return self._render_status_badge(field, value)
            
            # Amount field rendering
            elif field.field_type == FieldType.AMOUNT:
                return self._render_amount_field(value, field, item)
            
            # No supplier-specific rendering needed
            return None
            
        except Exception as e:
            logger.error(f"Error rendering supplier field {field.name}: {str(e)}")
            return None
    
    def _render_multi_method_payment(self, item: Dict, field: FieldDefinition) -> Dict:
        """SUPPLIER-SPECIFIC: Multi-method payment breakdown (exact from existing payment_list)"""
        
        # Check if this is a multi-method payment
        cash_amount = item.get("cash_amount", 0)
        cheque_amount = item.get("cheque_amount", 0)
        bank_amount = item.get("bank_transfer_amount", 0)
        upi_amount = item.get("upi_amount", 0)
        
        # Count methods present (same logic as existing)
        methods_present = sum([
            1 if cash_amount and float(cash_amount) > 0 else 0,
            1 if cheque_amount and float(cheque_amount) > 0 else 0,
            1 if bank_amount and float(bank_amount) > 0 else 0,
            1 if upi_amount and float(upi_amount) > 0 else 0
        ])
        
        if methods_present > 1:
            # Multi-method display with breakdown (exact HTML structure as existing)
            breakdown_html = '<div class="payment-method-breakdown">'
            
            if cash_amount and float(cash_amount) > 0:
                breakdown_html += f'''
                    <div class="payment-method-item">
                        <i class="fas fa-money-bill text-green-600"></i>
                        <span>Cash: ₹{float(cash_amount):,.2f}</span>
                    </div>
                '''
            if cheque_amount and float(cheque_amount) > 0:
                breakdown_html += f'''
                    <div class="payment-method-item">
                        <i class="fas fa-money-check text-blue-600"></i>
                        <span>Cheque: ₹{float(cheque_amount):,.2f}</span>
                    </div>
                '''
            if bank_amount and float(bank_amount) > 0:
                breakdown_html += f'''
                    <div class="payment-method-item">
                        <i class="fas fa-university text-blue-600"></i>
                        <span>Bank: ₹{float(bank_amount):,.2f}</span>
                    </div>
                '''
            if upi_amount and float(upi_amount) > 0:
                breakdown_html += f'''
                    <div class="payment-method-item">
                        <i class="fas fa-mobile-alt text-purple-600"></i>
                        <span>UPI: ₹{float(upi_amount):,.2f}</span>
                    </div>
                '''
            
            breakdown_html += '</div>'
            
            return {
                'field_name': field.name,
                'raw_value': 'Mixed',
                'field_type': field.field_type.value,
                'css_class': getattr(field, 'css_classes', ''),
                'align': getattr(field, 'align', 'left'),
                'formatted_value': breakdown_html,
                'component': 'multi_method_payment',
                'is_multi_method': True,
                'display_method': 'Mixed'
            }
        else:
            # Single method display (exact logic as existing)
            method = item.get('display_payment_method', item.get('payment_method', ''))
            method_icons = {
                'cash': 'fas fa-money-bill text-green-600',
                'cheque': 'fas fa-money-check text-blue-600', 
                'bank_transfer': 'fas fa-university text-blue-600',
                'upi': 'fas fa-mobile-alt text-purple-600'
            }
            
            icon = method_icons.get(item.get('payment_method', ''), 'fas fa-credit-card')
            
            return {
                'field_name': field.name,
                'raw_value': method,
                'field_type': field.field_type.value,
                'css_class': getattr(field, 'css_classes', ''),
                'align': getattr(field, 'align', 'left'),
                'formatted_value': f'<i class="{icon}"></i> {method}',
                'component': 'single_method_payment',
                'is_multi_method': False,
                'display_method': method
            }
    
    def _render_supplier_column(self, item: Dict, field: FieldDefinition) -> Dict:
        """SUPPLIER-SPECIFIC: Supplier column rendering (exact from existing payment_list)"""
        
        supplier_name = item.get('supplier_name', '')
        supplier_id = item.get('supplier_id', '')
        reference_no = item.get('reference_no', '')
        
        # Build supplier column HTML (exact structure as existing payment_list)
        supplier_html = f'<div class="supplier-name">{supplier_name}</div>'
        if reference_no:
            supplier_html += f'<div class="supplier-secondary">Ref: {reference_no}</div>'
        elif supplier_id:
            supplier_html += f'<div class="supplier-secondary">Code: {supplier_id}</div>'
        
        return {
            'field_name': field.name,
            'raw_value': supplier_name,
            'field_type': field.field_type.value,
            'css_class': 'supplier-column',
            'align': getattr(field, 'align', 'left'),
            'formatted_value': supplier_html,
            'component': 'supplier_column',
            'supplier_name': supplier_name,
            'reference_no': reference_no
        }
    
    def _render_status_badge(self, field: FieldDefinition, value: Any) -> Dict:
        """SUPPLIER-SPECIFIC: Status badge rendering with CSS classes"""
        
        status_option = self._get_status_option(field, value)
        
        return {
            'field_name': field.name,
            'raw_value': value,
            'field_type': field.field_type.value,
            'css_class': getattr(field, 'css_classes', ''),
            'align': getattr(field, 'align', 'left'),
            'formatted_value': str(value).title(),
            'component': 'status_badge',
            'status_css_class': status_option.get('css_class', 'status-default'),
            'badge_html': f'<span class="status-badge {status_option.get("css_class", "status-default")}">{str(value).title()}</span>'
        }
    
    def _render_amount_field(self, value: Any, field: FieldDefinition, item: Dict = None) -> Dict:
        """SUPPLIER-SPECIFIC: Amount field with enhanced payment method filtering display"""
        
        from flask import request
        
        if isinstance(value, (int, float, Decimal)):
            formatted = f"₹{float(value):,.2f}"
            
            # Check for active payment method filter and mixed payment
            active_payment_filter = request.args.get('payment_method') if request else None
            payment_method = item.get('payment_method') if item else None
            
            # If payment method filter is active and this is a mixed payment, show component amount
            if (active_payment_filter and 
                active_payment_filter not in ['bank_transfer_inclusive'] and 
                payment_method == 'mixed' and 
                item):
                
                # Get the component amount for the filtered payment method
                component_amount = None
                component_label = None
                
                if active_payment_filter == 'cash' and item.get('cash_amount', 0) > 0:
                    component_amount = item.get('cash_amount')
                    component_label = 'Cash'
                elif active_payment_filter == 'cheque' and item.get('cheque_amount', 0) > 0:
                    component_amount = item.get('cheque_amount')  
                    component_label = 'Cheque'
                elif active_payment_filter == 'bank_transfer' and item.get('bank_transfer_amount', 0) > 0:
                    component_amount = item.get('bank_transfer_amount')
                    component_label = 'Bank Transfer'
                elif active_payment_filter == 'upi' and item.get('upi_amount', 0) > 0:
                    component_amount = item.get('upi_amount')
                    component_label = 'UPI'
                
                # If we found a component amount, add it to the formatted display
                if component_amount and float(component_amount) > 0:
                    component_formatted = f"₹{float(component_amount):,.2f}"
                    formatted += f'<br><small style="font-size: 0.75em; color: #666; font-weight: normal;">({component_label})<br>{component_formatted}</small>'
        else:
            formatted = str(value) if value is not None else "₹0.00"
        
        return {
            'field_name': field.name,
            'raw_value': value,
            'field_type': field.field_type.value,
            'css_class': getattr(field, 'css_classes', ''),
            'align': getattr(field, 'align', 'right'),
            'formatted_value': formatted,
            'component': 'amount_field'
        }
    
    def _get_status_option(self, field: FieldDefinition, value: Any) -> Dict:
        """Get status option configuration"""
        
        if not hasattr(field, 'options') or not field.options:
            return {'css_class': 'status-default', 'label': str(value).title()}
        
        for option in field.options:
            if option.get('value') == value:
                return option
        
        return {'css_class': 'status-default', 'label': str(value).title()}
    
    def get_template_data(self, additional_context: Dict, form_instance: FlaskForm) -> Dict:
        """Get supplier-specific template data"""
        
        return {
            'suppliers': additional_context.get('suppliers', []),
            'payment_config': additional_context.get('payment_config')
        }
    
    def get_dropdown_choices(self) -> Dict:
        """Get supplier-specific dropdown choices"""
        
        try:
            from app.services.supplier_service import get_suppliers_for_choice
            try:
                suppliers = get_suppliers_for_choice(current_user.hospital_id)
            except TypeError:
                suppliers = get_suppliers_for_choice()
            return {
                'suppliers': suppliers
            }
        except Exception as e:
            logger.warning(f"Error getting supplier dropdown choices: {str(e)}")
            return {'suppliers': []}
    
    def get_config_object(self):
        """Get supplier-specific configuration object"""
        
        try:
            from app.config import PAYMENT_CONFIG
            return PAYMENT_CONFIG
        except ImportError:
            logger.warning("Could not import PAYMENT_CONFIG")
            return None

