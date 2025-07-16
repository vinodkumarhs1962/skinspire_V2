
# =============================================================================
# File: app/engine/categorized_filter_processor.py
# Categorized Filter Processor - Single Source of Truth for All Entity Filtering
# =============================================================================

"""
Categorized Filter Processor - Replaces all existing filter logic
- Single database session management
- Category-based processing for clean separation
- Entity-agnostic design with configuration-driven behavior
- Preserves all existing functionality while eliminating conflicts
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import uuid
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, func, desc, asc
from flask_login import current_user
from flask import current_app

from app.config.filter_categories import (
    FilterCategory, 
    organize_current_filters_by_category,
    get_category_processing_order,
    enhance_entity_config_with_categories,
    FILTER_CATEGORY_CONFIG
)
from app.config.entity_configurations import get_entity_config
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class CategorizedFilterProcessor:
    """
    Single source of truth for all entity filtering
    Replaces complex cascading filter logic with clean category-based processing
    """
    
    def __init__(self):
        self.session = None
        self.entity_models = {
            'supplier_payments': 'app.models.transaction.SupplierPayment',
            'suppliers': 'app.models.master.Supplier',
            'patients': 'app.models.patient.Patient',
            'medicines': 'app.models.medicine.Medicine'
        }
    
    def _apply_mixed_payment_logic(self, model_class, model_attr, filter_value, config):
        """
        ✅ UNIVERSAL: Apply mixed payment logic using configuration
        Maps payment method values to their amount fields based on entity config
        """
        try:
            from sqlalchemy import and_, or_
            
            # ✅ UNIVERSAL: Get payment method field configuration
            payment_method_field = None
            for field in config.fields:
                if field.name == 'payment_method' and hasattr(field, 'options'):
                    payment_method_field = field
                    break
            
            if not payment_method_field or not payment_method_field.options:
                return None
            
            # ✅ UNIVERSAL: Check if this filter value exists in options
            valid_option = None
            for option in payment_method_field.options:
                if option.get('value') == filter_value:
                    valid_option = option
                    break
            
            if not valid_option:
                return None
            
            # ✅ UNIVERSAL: Derive amount field mapping from entity configuration
            amount_field_name = self._get_amount_field_for_payment_method(filter_value, config, model_class)
            
            # ✅ UNIVERSAL: Apply mixed payment logic if amount field exists
            if amount_field_name and hasattr(model_class, amount_field_name):
                amount_attr = getattr(model_class, amount_field_name)
                
                # Include both exact matches AND mixed payments with this component
                logger.info(f"✅ [MIXED_PAYMENT] Applying mixed logic: {filter_value} includes mixed with {amount_field_name} > 0")
                return or_(
                    model_attr == filter_value,
                    and_(model_attr == 'mixed', amount_attr > 0)
                )
            else:
                # For payment methods without amount fields, use exact match
                logger.info(f"✅ [EXACT_MATCH] No amount field found, using exact match for: {filter_value}")
                return model_attr == filter_value
                
        except Exception as e:
            logger.error(f"❌ Error applying mixed payment logic: {str(e)}")
            return None

    def _get_amount_field_for_payment_method(self, payment_method, config, model_class):
        """
        ✅ UNIVERSAL: Get amount field name for payment method from configuration
        Uses multiple strategies to find the correct amount field
        """
        try:
            # Strategy 1: Direct naming convention (most common)
            conventional_field_name = f"{payment_method}_amount"
            if hasattr(model_class, conventional_field_name):
                logger.info(f"✅ [CONFIG_MAPPING] Found amount field by convention: {payment_method} → {conventional_field_name}")
                return conventional_field_name
            
            # Strategy 2: Search in field definitions with payment method in name
            for field in config.fields:
                field_name = field.name
                # Check if field name contains payment method and ends with amount
                if (payment_method.lower() in field_name.lower() and 
                    'amount' in field_name.lower() and 
                    hasattr(model_class, field_name)):
                    logger.info(f"✅ [CONFIG_MAPPING] Found amount field by search: {payment_method} → {field_name}")
                    return field_name
            
            # Strategy 3: Look for explicit mapping in field configuration (future enhancement)
            for field in config.fields:
                if (hasattr(field, 'payment_method_mapping') and 
                    field.payment_method_mapping and 
                    payment_method in field.payment_method_mapping):
                    mapped_field = field.payment_method_mapping[payment_method]
                    if hasattr(model_class, mapped_field):
                        logger.info(f"✅ [CONFIG_MAPPING] Found amount field by explicit mapping: {payment_method} → {mapped_field}")
                        return mapped_field
            
            logger.warning(f"⚠️ [CONFIG_MAPPING] No amount field found for payment method: {payment_method}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding amount field for {payment_method}: {str(e)}")
            return None

    def process_entity_filters(self, entity_type: str, filters: Dict[str, Any], 
                             query: Query, session: Session, config=None) -> Tuple[Query, Set[str], int]:
        """
        Main entry point - processes ALL filters by category
        
        Args:
            entity_type: Entity type ('supplier_payments', etc.)
            filters: Dictionary of filter values from request
            query: SQLAlchemy query object to modify
            session: Database session to use
            config: Entity configuration (will auto-load if not provided)
            
        Returns:
            Tuple of (modified_query, applied_filter_names, filter_count)
        """
        try:
            self.session = session
            
            # Get or enhance configuration
            if not config:
                config = get_entity_config(entity_type)
            
            if not config:
                logger.warning(f"No configuration found for entity type: {entity_type}")
                return query, set(), 0
                
            # Enhance config with category information if needed
            enhance_entity_config_with_categories(config)

            # ✅ UNIVERSAL FIX: Ensure filter_category_mapping is available
            if not hasattr(config, 'filter_category_mapping') or not config.filter_category_mapping:
                logger.warning(f"⚠️ No filter_category_mapping found for {entity_type} - filters may be miscategorized")
            else:
                logger.info(f"🔧 [CATEGORIZATION] Using filter_category_mapping: {list(config.filter_category_mapping.keys())}")

            # Organize filters by category
            # ✅ UNIVERSAL FIX: Replace faulty organize_current_filters_by_category with working logic
            categorized_filters = {}
            filter_mapping = getattr(config, 'filter_category_mapping', {})

            for filter_key, filter_value in filters.items():
                # Skip empty values and pagination
                if not filter_value or (isinstance(filter_value, str) and not filter_value.strip()) or filter_key in ['page', 'per_page']:
                    continue
                
                # Get category from mapping
                category = filter_mapping.get(filter_key)
                if category:
                    if category not in categorized_filters:
                        categorized_filters[category] = {}
                    categorized_filters[category][filter_key] = filter_value
                    logger.info(f"✅ [CATEGORIZATION_FIX] {filter_key} → {category.value}")

            # Debug categorization results  
            logger.info(f"🔧 [CATEGORIZATION_DEBUG] Input filters: {list(filters.keys())}")
            logger.info(f"🔧 [CATEGORIZATION_DEBUG] Categorized result: {[(cat.value, list(cat_filters.keys())) for cat, cat_filters in categorized_filters.items()]}")
            
            if not categorized_filters:
                logger.info(f"No filterable data provided for {entity_type}")
                return query, set(), 0
            
            logger.info(f"🔄 Processing {len(categorized_filters)} filter categories for {entity_type}")
            for category, category_filters in categorized_filters.items():
                logger.info(f"  • {category.value}: {list(category_filters.keys())}")
            
            # Process categories in optimal order
            all_applied_filters = set()
            total_filter_count = 0
            
            processing_order = get_category_processing_order()
            
            for category in processing_order:
                if category in categorized_filters:
                    category_filters = categorized_filters[category]
                    
                    try:
                        query, applied_filters, filter_count = self._process_category_filters(
                            category, category_filters, query, config, entity_type
                        )
                        all_applied_filters.update(applied_filters)
                        total_filter_count += filter_count
                        
                        logger.info(f"✅ {category.value}: Applied {filter_count} filters")
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing {category.value} filters: {str(e)}")
                        # Continue with other categories on error
                        continue
            
            logger.info(f"✅ Total filters applied: {total_filter_count}")
            return query, all_applied_filters, total_filter_count
            
        except Exception as e:
            logger.error(f"❌ Error in categorized filter processing: {str(e)}")
            return query, set(), 0
    
    def _process_category_filters(self, category: FilterCategory, filters: Dict[str, Any], 
                                query: Query, config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """Process filters for a specific category"""
        
        if category == FilterCategory.DATE:
            return self._process_date_filters(filters, query, config, entity_type)
        elif category == FilterCategory.AMOUNT:
            return self._process_amount_filters(filters, query, config, entity_type)
        elif category == FilterCategory.SEARCH:
            return self._process_search_filters(filters, query, config, entity_type)
        elif category == FilterCategory.SELECTION:
            return self._process_selection_filters(filters, query, config, entity_type)
        elif category == FilterCategory.RELATIONSHIP:
            return self._process_relationship_filters(filters, query, config, entity_type)
        else:
            logger.warning(f"Unknown filter category: {category}")
            return query, set(), 0
    
    # ==========================================================================
    # DATE CATEGORY PROCESSING
    # ==========================================================================
    
    def _calculate_preset_dates(self, preset_value: str) -> Tuple[Optional[date], Optional[date]]:
        """
        Calculate date range for preset values
        Adapted from universal_forms.js calculatePresetDates method
        """
        from datetime import date, timedelta
        
        today = date.today()
        
        try:
            if preset_value == 'today':
                return today, today
                
            elif preset_value == 'yesterday':
                yesterday = today - timedelta(days=1)
                return yesterday, yesterday
                
            elif preset_value == 'this_week':
                # Start of week (Monday) to today
                start_of_week = today - timedelta(days=today.weekday())
                return start_of_week, today
                
            elif preset_value == 'this_month':
                # First day of current month to today (same as universal_forms.js)
                current_date = date.today()  # Get fresh current date
                first_day_of_month = date(today.year, today.month, 1)  # Explicit date construction
                return first_day_of_month, today
                
            elif preset_value == 'last_30_days':
                thirty_days_ago = today - timedelta(days=30)
                return thirty_days_ago, today
                
            elif preset_value in ['financial_year', 'current']:
                # Use existing financial year logic
                return self._get_financial_year_dates(preset_value)
                
            elif preset_value == 'clear':
                return None, None
                
            else:
                # Default to financial year for unknown presets
                logger.warning(f"Unknown date preset: {preset_value}, defaulting to financial_year")
                return self._get_financial_year_dates('current')
                
        except Exception as e:
            logger.error(f"Error calculating preset dates for {preset_value}: {str(e)}")
            return None, None

    def _process_date_filters(self, filters: Dict[str, Any], query: Query, 
                            config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """Process date-related filters"""
        applied_filters = set()
        filter_count = 0
        
        try:
            # Get the primary model class
            model_class = self._get_model_class(entity_type)
            if not model_class:
                return query, applied_filters, filter_count
            
            # Handle date range filters
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            
            # Apply default financial year if no explicit dates provided
            if not start_date and not end_date:
                # Apply default financial year for supplier_payments
                if entity_type == 'supplier_payments':
                    logger.info("[DATE_DEFAULT] No explicit dates - applying financial year default")
                    fy_start, fy_end = self._get_financial_year_dates('current')
                    if fy_start and fy_end:
                        date_field = self._get_primary_date_field(model_class, config)
                        query = query.filter(
                            and_(
                                date_field >= fy_start,
                                date_field <= fy_end
                            )
                        )
                        applied_filters.add('financial_year_default')
                        filter_count += 1
                        logger.info(f"✅ Applied default financial year: {fy_start} to {fy_end}")

            if start_date or end_date:
                date_field = self._get_primary_date_field(model_class, config)
                
                if start_date:
                    try:
                        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                        query = query.filter(date_field >= start_date_obj)
                        applied_filters.add('start_date')
                        filter_count += 1
                        logger.info(f"✅ Applied start_date filter: {start_date}")
                    except ValueError:
                        logger.warning(f"Invalid start_date format: {start_date}")
                
                if end_date:
                    try:
                        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                        query = query.filter(date_field <= end_date_obj)
                        applied_filters.add('end_date')
                        filter_count += 1
                        logger.info(f"✅ Applied end_date filter: {end_date}")
                    except ValueError:
                        logger.warning(f"Invalid end_date format: {end_date}")
            
            # Handle date presets (if no explicit dates provided)
            if not start_date and not end_date:
                # Check for various date preset parameters (same as universal_forms.js)
                date_preset = (filters.get('date_preset') or 
                            filters.get('financial_year') or 
                            filters.get('preset') or 
                            'current')
                
                if date_preset and date_preset != 'all':
                    start_date_obj, end_date_obj = self._calculate_preset_dates(date_preset)
                    if start_date_obj and end_date_obj:
                        date_field = self._get_primary_date_field(model_class, config)
                        
                        query = query.filter(
                            and_(
                                date_field >= start_date_obj,
                                date_field <= end_date_obj
                            )
                        )
                        applied_filters.add(date_preset)
                        filter_count += 1
                        logger.info(f"✅ Applied {date_preset} filter: {start_date_obj} to {end_date_obj}")
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing date filters: {str(e)}")
            return query, applied_filters, filter_count
    
    def _get_primary_date_field(self, model_class, config):
        """Get the primary date field for an entity"""
        # First try to find payment_date, created_at, or similar
        common_date_fields = ['payment_date', 'created_at', 'date', 'transaction_date']
        
        for field_name in common_date_fields:
            if hasattr(model_class, field_name):
                return getattr(model_class, field_name)
        
        # Fallback to first date field found in config
        if config and hasattr(config, 'fields'):
            for field in config.fields:
                if field.field_type.value in ['date', 'datetime'] and hasattr(model_class, field.name):
                    return getattr(model_class, field.name)
        
        # Final fallback
        if hasattr(model_class, 'created_at'):
            return model_class.created_at
        
        raise ValueError(f"No date field found for {model_class.__name__}")
    
    def _get_financial_year_dates(self, financial_year: str) -> Tuple[date, date]:
        """Get start and end dates for financial year"""
        today = date.today()
        
        if financial_year == 'current':
            # Current financial year (April 1 to March 31)
            if today.month >= 4:
                start_date = date(today.year, 4, 1)
                end_date = date(today.year + 1, 3, 31)
            else:
                start_date = date(today.year - 1, 4, 1)
                end_date = date(today.year, 3, 31)
        elif financial_year == 'last':
            # Last financial year
            if today.month >= 4:
                start_date = date(today.year - 1, 4, 1)
                end_date = date(today.year, 3, 31)
            else:
                start_date = date(today.year - 2, 4, 1)
                end_date = date(today.year - 1, 3, 31)
        else:
            # Default to current financial year
            if today.month >= 4:
                start_date = date(today.year, 4, 1)
                end_date = date(today.year + 1, 3, 31)
            else:
                start_date = date(today.year - 1, 4, 1)
                end_date = date(today.year, 3, 31)
        
        return start_date, end_date
    
    # ==========================================================================
    # AMOUNT CATEGORY PROCESSING
    # ==========================================================================
    
    def _process_amount_filters(self, filters: Dict[str, Any], query: Query, 
                              config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """Process amount-related filters"""
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class:
                return query, applied_filters, filter_count
            
            # Handle min/max amount filters
            min_amount = filters.get('min_amount') or filters.get('amount_min')
            max_amount = filters.get('max_amount') or filters.get('amount_max')
            
            if min_amount or max_amount:
                amount_field = self._get_primary_amount_field(model_class, config)
                
                if min_amount:
                    try:
                        min_val = float(min_amount)
                        query = query.filter(amount_field >= min_val)
                        applied_filters.add('min_amount')
                        filter_count += 1
                        logger.info(f"✅ Applied min_amount filter: {min_val}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid min_amount value: {min_amount}")
                
                if max_amount:
                    try:
                        max_val = float(max_amount)
                        query = query.filter(amount_field <= max_val)
                        applied_filters.add('max_amount')
                        filter_count += 1
                        logger.info(f"✅ Applied max_amount filter: {max_val}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid max_amount value: {max_amount}")
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing amount filters: {str(e)}")
            return query, applied_filters, filter_count
    
    def _get_primary_amount_field(self, model_class, config):
        """Get the primary amount field for an entity"""
        # Common amount field names
        common_amount_fields = ['amount', 'total_amount', 'price', 'cost']
        
        for field_name in common_amount_fields:
            if hasattr(model_class, field_name):
                return getattr(model_class, field_name)
        
        # Fallback to config
        if config and hasattr(config, 'fields'):
            for field in config.fields:
                if field.field_type.value in ['amount', 'currency', 'number'] and hasattr(model_class, field.name):
                    return getattr(model_class, field.name)
        
        raise ValueError(f"No amount field found for {model_class.__name__}")
    
    # ==========================================================================
    # SEARCH CATEGORY PROCESSING
    # ==========================================================================
    
    def _process_search_filters(self, filters: Dict[str, Any], query: Query, 
                          config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """Process text search filters"""
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class:
                return query, applied_filters, filter_count
            
            # ✅ FIX: Handle payment method filters that were miscategorized as search
            if entity_type == 'supplier_payments':
                payment_method = filters.get('payment_method') or filters.get('payment_methods')
                if payment_method:
                    if isinstance(payment_method, list) and len(payment_method) > 0:
                        payment_method = payment_method[0]
                    
                    if (payment_method and 
                        str(payment_method).strip() and 
                        str(payment_method).lower() not in ['all', 'none', '', 'null']):
                        
                        query = query.filter(model_class.payment_method == payment_method)
                        applied_filters.add('payment_method')
                        filter_count += 1
                        logger.info(f"✅ Applied payment_method filter: {payment_method}")
            
            # Handle supplier name search (entity-specific)
            if entity_type == 'supplier_payments':
                supplier_search = (filters.get('supplier_name_search') or 
                                filters.get('search') or 
                                filters.get('supplier_search'))
                
                if supplier_search and str(supplier_search).strip():
                    query = self._apply_supplier_name_search(query, supplier_search.strip())
                    applied_filters.add('supplier_name_search')
                    filter_count += 1
                    logger.info(f"✅ Applied supplier_name_search filter: {supplier_search}")
            
            # Handle reference number search
            reference_no = filters.get('reference_no') or filters.get('ref_no')
            if reference_no and str(reference_no).strip():
                if hasattr(model_class, 'reference_no'):
                    query = query.filter(model_class.reference_no.ilike(f'%{reference_no.strip()}%'))
                    applied_filters.add('reference_no')
                    filter_count += 1
                    logger.info(f"✅ Applied reference_no filter: {reference_no}")
            
            # Handle invoice ID search
            invoice_id = filters.get('invoice_id')
            if invoice_id and str(invoice_id).strip():
                if hasattr(model_class, 'invoice_id'):
                    query = query.filter(model_class.invoice_id == invoice_id.strip())
                    applied_filters.add('invoice_id')
                    filter_count += 1
                    logger.info(f"✅ Applied invoice_id filter: {invoice_id}")
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing search filters: {str(e)}")
            return query, applied_filters, filter_count
    
    def _apply_supplier_name_search(self, query: Query, search_term: str) -> Query:
        """Apply supplier name search with proper join"""
        try:
            from app.models.master import Supplier
            
            # Check if we need to join or if already joined
            if not self._query_has_join(query, Supplier):
                query = query.join(Supplier, query.column_descriptions[0]['type'].supplier_id == Supplier.supplier_id)
            
            # Apply search filter
            query = query.filter(Supplier.supplier_name.ilike(f'%{search_term}%'))
            return query
            
        except Exception as e:
            logger.error(f"❌ Error applying supplier name search: {str(e)}")
            return query
    
    def _query_has_join(self, query: Query, model_class) -> bool:
        """Check if query already has a join for the specified model"""
        try:
            for desc in query.column_descriptions:
                if desc['entity'] == model_class:
                    return True
            return False
        except:
            return False
    
    # ==========================================================================
    # SELECTION CATEGORY PROCESSING
    # ==========================================================================
    
    def _process_selection_filters(self, filters: Dict[str, Any], query: Query, 
                             config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """
        Process selection/dropdown filters using CONFIGURATION-DRIVEN approach
        Uses filter_aliases from field definitions - completely universal!
        """
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class or not config:
                return query, applied_filters, filter_count
            
            logger.info(f"🔍 [SELECTION] Processing filters: {list(filters.keys())}")
            
            # ✅ UNIVERSAL: Get filterable fields from configuration
            filterable_fields = [field for field in config.fields 
                            if getattr(field, 'filterable', False)]
            
            # ✅ UNIVERSAL: Process each filterable field
            for field_config in filterable_fields:
                db_field_name = field_config.name  # Actual database field name
                
                # Skip if model doesn't have this field
                if not hasattr(model_class, db_field_name):
                    continue
                
                # ✅ UNIVERSAL: Check main field name and all aliases
                field_names_to_check = [db_field_name]
                if hasattr(field_config, 'filter_aliases') and field_config.filter_aliases:
                    field_names_to_check.extend(field_config.filter_aliases)
                
                # ✅ UNIVERSAL: Find matching filter value
                filter_value = None
                matched_filter_key = None
                
                for possible_name in field_names_to_check:
                    if possible_name in filters:
                        filter_value = filters[possible_name]
                        matched_filter_key = possible_name
                        break
                
                if filter_value is not None:
                    logger.info(f"🔍 [SELECTION] Found {matched_filter_key} = {filter_value} → {db_field_name}")
                    
                    # ✅ UNIVERSAL: Handle array format (statuses: ['pending'] → 'pending')
                    if isinstance(filter_value, list) and len(filter_value) > 0:
                        filter_value = filter_value[0]
                        logger.info(f"🔍 [SELECTION] Converted array to: {filter_value}")
                    
                    # ✅ UNIVERSAL: Validate and apply filter
                    if (filter_value and 
                        str(filter_value).strip() and 
                        str(filter_value).lower() not in ['all', 'none', '', 'null']):
                        
                        model_attr = getattr(model_class, db_field_name)
                        
                        # ✅ UNIVERSAL FIX: Handle mixed payments using configuration
                        if db_field_name == 'payment_method':
                            mixed_payment_logic = self._apply_mixed_payment_logic(
                                model_class, model_attr, filter_value, config
                            )
                            if mixed_payment_logic is not None:
                                query = query.filter(mixed_payment_logic)
                            else:
                                # Fallback to exact match if no mixed logic found
                                query = query.filter(model_attr == filter_value)
                        else:
                            # For non-payment_method fields, use exact match
                            query = query.filter(model_attr == filter_value)
                        
                        applied_filters.add(matched_filter_key)
                        filter_count += 1
                        logger.info(f"✅ Applied {matched_filter_key} → {db_field_name} filter: {filter_value}")
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing selection filters: {str(e)}")
            return query, applied_filters, filter_count
    
    # ==========================================================================
    # RELATIONSHIP CATEGORY PROCESSING
    # ==========================================================================
    
    def _process_relationship_filters(self, filters: Dict[str, Any], query: Query, 
                                    config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """Process relationship/foreign key filters"""
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class:
                return query, applied_filters, filter_count
            
            # Process entity ID filters
            id_fields = ['supplier_id', 'patient_id', 'doctor_id', 'medicine_id', 'branch_id']
            
            for field_name in id_fields:
                filter_value = filters.get(field_name)
                if filter_value and str(filter_value).strip():
                    if hasattr(model_class, field_name):
                        try:
                            # Convert to UUID if needed
                            if isinstance(filter_value, str):
                                filter_value = uuid.UUID(filter_value) if len(filter_value) == 36 else filter_value
                            
                            model_attr = getattr(model_class, field_name)
                            query = query.filter(model_attr == filter_value)
                            applied_filters.add(field_name)
                            filter_count += 1
                            logger.info(f"✅ Applied {field_name} filter: {filter_value}")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid {field_name} value: {filter_value} - {str(e)}")
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing relationship filters: {str(e)}")
            return query, applied_filters, filter_count
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def _get_model_class(self, entity_type: str):
        """Get SQLAlchemy model class for entity type"""
        try:
            model_path = self.entity_models.get(entity_type)
            if not model_path:
                logger.warning(f"No model mapping found for entity type: {entity_type}")
                return None
            
            # Import the model class
            module_path, class_name = model_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            return getattr(module, class_name)
            
        except Exception as e:
            logger.error(f"❌ Error importing model for {entity_type}: {str(e)}")
            return None
    
    def get_applied_filter_summary(self, applied_filters: Set[str], categorized_filters: Dict) -> Dict:
        """Get summary of applied filters by category"""
        summary = {}
        
        for category, filters in categorized_filters.items():
            applied_in_category = [f for f in filters.keys() if f in applied_filters]
            if applied_in_category:
                summary[category.value] = {
                    'applied_count': len(applied_in_category),
                    'applied_filters': applied_in_category,
                    'total_filters': len(filters)
                }
        
        return summary

# =============================================================================
# GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS
# =============================================================================

# Global processor instance
_categorized_processor = CategorizedFilterProcessor()

def get_categorized_filter_processor() -> CategorizedFilterProcessor:
    """Get the global categorized filter processor instance"""
    return _categorized_processor

def process_filters_for_entity(entity_type: str, filters: Dict[str, Any], 
                             query: Query, session: Session, config=None) -> Tuple[Query, Set[str], int]:
    """
    Convenience function for processing filters
    Direct replacement for existing filter processing methods
    """
    processor = get_categorized_filter_processor()
    return processor.process_entity_filters(entity_type, filters, query, session, config)

def organize_filters_by_category(filters: Dict[str, Any], entity_type: str) -> Dict[FilterCategory, Dict]:
    """
    Convenience function for organizing filters by category
    """
    config = get_entity_config(entity_type)
    if not config:
        return {}
    
    return organize_current_filters_by_category(filters, config)