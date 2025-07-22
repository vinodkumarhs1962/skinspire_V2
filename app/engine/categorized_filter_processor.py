
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
from app.config.core_definitions import FieldType
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

            # Organize filters by category using the smart function from filter_categories
            from app.config.filter_categories import organize_current_filters_by_category

            # This function already has fallback detection for date filters!
            categorized_filters = organize_current_filters_by_category(filters, config)

            # Log the categorization results
            for category, category_filters in categorized_filters.items():
                for filter_key in category_filters:
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
            
            # ✅ PHASE 1A: Log configuration status
            if config and hasattr(config, 'primary_date_field'):
                logger.info(f"✅ Using configured primary date field for {entity_type}: {config.primary_date_field}")
            else:
                logger.info(f"⚠️ No primary date field configured for {entity_type}, using fallback logic")

            # Handle date range filters
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            
            # Apply default financial year if no explicit dates provided
            if not start_date and not end_date:
                # ✅ PHASE 1A: Configuration-driven default financial year application
                if config and hasattr(config, 'default_filters') and config.default_filters.get('financial_year'):
                    logger.info(f"[DATE_DEFAULT] No explicit dates - applying financial year default for {entity_type}")
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
                        logger.info(f"✅ Applied default financial year for {entity_type}: {fy_start} to {fy_end}")

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
        """Get the primary date field for an entity - Configuration-driven"""
        
        # ✅ PHASE 1A: Use configuration first
        if config and hasattr(config, 'primary_date_field'):
            primary_field = config.primary_date_field
            if hasattr(model_class, primary_field):
                logger.info(f"✅ Using configured primary date field: {primary_field}")
                return getattr(model_class, primary_field)
            else:
                logger.warning(f"⚠️ Configured primary date field '{primary_field}' not found in model {model_class.__name__}")
        
        # ✅ FALLBACK: Original hardcoded logic (preserved for backward compatibility)
        common_date_fields = ['payment_date', 'created_at', 'date', 'transaction_date']
        
        for field_name in common_date_fields:
            if hasattr(model_class, field_name):
                logger.info(f"✅ Using fallback date field: {field_name}")
                return getattr(model_class, field_name)
        
        # Fallback to first date field found in config
        if config and hasattr(config, 'fields'):
            for field in config.fields:
                if field.field_type.value in ['date', 'datetime'] and hasattr(model_class, field.name):
                    logger.info(f"✅ Using config-defined date field: {field.name}")
                    return getattr(model_class, field.name)
        
        # Final fallback
        if hasattr(model_class, 'created_at'):
            logger.info(f"✅ Using final fallback date field: created_at")
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
            
            # ✅ PHASE 1B: Log configuration status
            if config and hasattr(config, 'primary_amount_field'):
                logger.info(f"✅ Using configured primary amount field for {entity_type}: {config.primary_amount_field}")
            else:
                logger.info(f"⚠️ No primary amount field configured for {entity_type}, using fallback logic")

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
                        # ✅ PHASE 1B: Enhanced logging with field info
                        amount_field_name = getattr(amount_field.property, 'key', 'unknown_field')
                        logger.info(f"✅ Applied min_amount filter on {amount_field_name}: >= {min_val}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid min_amount value: {min_amount}")

                if max_amount:
                    try:
                        max_val = float(max_amount)
                        query = query.filter(amount_field <= max_val)
                        applied_filters.add('max_amount')
                        filter_count += 1
                        # ✅ PHASE 1B: Enhanced logging with field info
                        amount_field_name = getattr(amount_field.property, 'key', 'unknown_field')
                        logger.info(f"✅ Applied max_amount filter on {amount_field_name}: <= {max_val}")
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid max_amount value: {max_amount}")
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing amount filters: {str(e)}")
            return query, applied_filters, filter_count
    
    def _get_primary_amount_field(self, model_class, config):
        """Get the primary amount field for an entity - Configuration-driven"""
        
        # ✅ PHASE 1B: Use configuration first
        if config and hasattr(config, 'primary_amount_field'):
            primary_field = config.primary_amount_field
            if hasattr(model_class, primary_field):
                logger.info(f"✅ Using configured primary amount field: {primary_field}")
                return getattr(model_class, primary_field)
            else:
                logger.warning(f"⚠️ Configured primary amount field '{primary_field}' not found in model {model_class.__name__}")
        
        # ✅ FALLBACK: Original hardcoded logic (preserved for backward compatibility)
        common_amount_fields = ['amount', 'total_amount', 'price', 'cost']
        
        for field_name in common_amount_fields:
            if hasattr(model_class, field_name):
                logger.info(f"✅ Using fallback amount field: {field_name}")
                return getattr(model_class, field_name)
        
        # Fallback to config
        if config and hasattr(config, 'fields'):
            for field in config.fields:
                if field.field_type.value in ['amount', 'currency', 'number'] and hasattr(model_class, field.name):
                    logger.info(f"✅ Using config-defined amount field: {field.name}")
                    return getattr(model_class, field.name)
        
        raise ValueError(f"No amount field found for {model_class.__name__}")
    
    # ==========================================================================
    # SEARCH CATEGORY PROCESSING
    # ==========================================================================
    
    def _process_search_filters(self, filters: Dict[str, Any], query: Query, 
                      config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """Process text search filters - Using existing ENTITY_SEARCH_CONFIGS where available"""
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class:
                return query, applied_filters, filter_count
            
            # ✅ PHASE 1C CORRECTED: Use existing ENTITY_SEARCH_CONFIGS first
            from app.config.entity_configurations import ENTITY_SEARCH_CONFIGS
            
            # ✅ FIXED: Skip general search config for supplier_payments if we have supplier-specific search
            # Check if we have existing search configuration for this entity
            if entity_type in ENTITY_SEARCH_CONFIGS and entity_type != 'supplier_payments':
                search_config = ENTITY_SEARCH_CONFIGS[entity_type]
                logger.info(f"✅ Using existing search config for {entity_type}")
                
                # Look for search terms in filters
                search_term = None
                search_param_used = None
                
                # Check various search parameter names - skip if already processed as supplier search
                for param_name in ['search', 'reference_no', 'ref_no']:
                    if (param_name in filters and filters[param_name] and str(filters[param_name]).strip() 
                        and param_name not in applied_filters):
                        search_term = str(filters[param_name]).strip()
                        search_param_used = param_name
                        break
                
                # Apply search using existing configuration
                if search_term and len(search_term) >= search_config.min_chars:
                    query = self._apply_search_using_existing_config(query, search_term, search_config, model_class)
                    applied_filters.add(search_param_used)
                    filter_count += 1
                    logger.info(f"✅ Applied search using existing config for {entity_type}: {search_term}")

            # ✅ FIXED: Handle reference_no and invoice_id for supplier_payments only if not handled by supplier search
            elif entity_type == 'supplier_payments':
                # Process reference_no search only if not already processed
                if 'reference_no' not in applied_filters and 'ref_no' not in applied_filters:
                    reference_no = filters.get('reference_no') or filters.get('ref_no')
                    if reference_no and str(reference_no).strip():
                        if hasattr(model_class, 'reference_no'):
                            query = query.filter(model_class.reference_no.ilike(f'%{reference_no.strip()}%'))
                            applied_filters.add('reference_no')
                            filter_count += 1
                            logger.info(f"✅ Applied reference_no filter: {reference_no}")
                
                # Process invoice_id search
                invoice_id = filters.get('invoice_id')
                if invoice_id and str(invoice_id).strip():
                    if hasattr(model_class, 'invoice_id'):
                        query = query.filter(model_class.invoice_id == invoice_id.strip())
                        applied_filters.add('invoice_id')
                        filter_count += 1
                        logger.info(f"✅ Applied invoice_id filter: {invoice_id}")
            
            
            # ✅ FIXED: Handle supplier name search (entity-specific) with existing config - avoid double processing
            if entity_type == 'supplier_payments':
                # Check if we already processed this search term to avoid double joins
                supplier_search = None
                search_filter_used = None
                
                # Priority order: supplier_name_search > search > supplier_search
                if filters.get('supplier_name_search') and str(filters.get('supplier_name_search')).strip():
                    supplier_search = str(filters.get('supplier_name_search')).strip()
                    search_filter_used = 'supplier_name_search'
                elif filters.get('search') and str(filters.get('search')).strip() and 'search' not in applied_filters:
                    supplier_search = str(filters.get('search')).strip()
                    search_filter_used = 'search'
                elif filters.get('supplier_search') and str(filters.get('supplier_search')).strip():
                    supplier_search = str(filters.get('supplier_search')).strip()
                    search_filter_used = 'supplier_search'
                
                if supplier_search and search_filter_used:
                    # Try to use existing supplier configuration
                    if 'suppliers' in ENTITY_SEARCH_CONFIGS:
                        supplier_config = ENTITY_SEARCH_CONFIGS['suppliers']
                        query = self._apply_supplier_search_with_join(query, supplier_search, supplier_config)
                        logger.info(f"✅ Applied supplier search using existing config: {supplier_search}")
                    else:
                        # Fallback to existing hardcoded logic
                        query = self._apply_supplier_name_search(query, supplier_search)
                        logger.info(f"✅ Applied supplier search using fallback logic: {supplier_search}")
                    
                    applied_filters.add(search_filter_used)
                    filter_count += 1
                       
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing search filters: {str(e)}")
            return query, applied_filters, filter_count

    def _apply_search_using_existing_config(self, query: Query, search_term: str, 
                                        search_config, model_class) -> Query:
        """Apply search using existing EntitySearchConfiguration"""
        try:
            search_conditions = []
            
            for field_name in search_config.search_fields:
                if hasattr(model_class, field_name):
                    field_attr = getattr(model_class, field_name)
                    search_conditions.append(field_attr.ilike(f'%{search_term}%'))
            
            if search_conditions:
                from sqlalchemy import or_
                query = query.filter(or_(*search_conditions))
            
            return query
            
        except Exception as e:
            logger.error(f"❌ Error applying search with existing config: {str(e)}")
            return query

    def _apply_supplier_search_with_join(self, query: Query, search_term: str, supplier_config) -> Query:
        """Apply supplier search with join using existing configuration"""
        try:
            if supplier_config.model_path:
                module_path, class_name = supplier_config.model_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                supplier_model = getattr(module, class_name)
                
                # Apply join if not already present
                if not self._query_has_join(query, supplier_model):
                    query = query.join(supplier_model)
                
                # Apply search across configured fields
                search_conditions = []
                for field_name in supplier_config.search_fields:
                    if hasattr(supplier_model, field_name):
                        field_attr = getattr(supplier_model, field_name)
                        search_conditions.append(field_attr.ilike(f'%{search_term}%'))
                
                if search_conditions:
                    from sqlalchemy import or_
                    query = query.filter(or_(*search_conditions))
            
            return query
            
        except Exception as e:
            logger.error(f"❌ Error applying supplier search with join: {str(e)}")
            return query
    
    def _apply_search_with_join(self, query: Query, search_term: str, search_config: Dict, entity_type: str) -> Query:
        """Apply search with join using configuration"""
        try:
            join_model_path = search_config.get('join_model')
            if not join_model_path:
                logger.warning(f"No join_model specified in search config")
                return query
            
            # Import join model dynamically
            module_path, class_name = join_model_path.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            join_model = getattr(module, class_name)
            
            # Check if we need to join or if already joined
            if not self._query_has_join(query, join_model):
                # For now, use simple join (can be enhanced with join_condition later)
                query = query.join(join_model)
            
            # Apply search across configured fields
            search_fields = search_config.get('search_fields', [])
            search_type = search_config.get('search_type', 'ilike')
            
            if search_fields:
                search_conditions = []
                for field_name in search_fields:
                    if hasattr(join_model, field_name):
                        field_attr = getattr(join_model, field_name)
                        if search_type == 'ilike':
                            search_conditions.append(field_attr.ilike(f'%{search_term}%'))
                        elif search_type == 'exact':
                            search_conditions.append(field_attr == search_term)
                
                if search_conditions:
                    from sqlalchemy import or_
                    query = query.filter(or_(*search_conditions))
            
            logger.info(f"✅ Applied search with join on {join_model.__name__}")
            return query
            
        except Exception as e:
            logger.error(f"❌ Error applying search with join: {str(e)}")
            return query

    def _apply_direct_search(self, query: Query, search_term: str, search_config: Dict, model_class) -> Query:
        """Apply direct search without join using configuration"""
        try:
            search_fields = search_config.get('search_fields', [])
            search_type = search_config.get('search_type', 'ilike')
            
            if search_fields:
                search_conditions = []
                for field_name in search_fields:
                    if hasattr(model_class, field_name):
                        field_attr = getattr(model_class, field_name)
                        if search_type == 'ilike':
                            search_conditions.append(field_attr.ilike(f'%{search_term}%'))
                        elif search_type == 'exact':
                            search_conditions.append(field_attr == search_term)
                
                if search_conditions:
                    from sqlalchemy import or_
                    query = query.filter(or_(*search_conditions))
            
            logger.info(f"✅ Applied direct search on {model_class.__name__}")
            return query
            
        except Exception as e:
            logger.error(f"❌ Error applying direct search: {str(e)}")
            return query

    # ✅ PRESERVE EXISTING METHOD for backward compatibility
    def _apply_supplier_name_search(self, query: Query, search_term: str) -> Query:
        """Apply supplier name search with proper join - PRESERVED for fallback"""
        try:
            from app.models.master import Supplier
            
            # Check if we need to join or if already joined
            if not self._query_has_join(query, Supplier):
                query = query.join(Supplier, query.column_descriptions[0]['type'].supplier_id == Supplier.supplier_id)
            
            # Apply search filter
            query = query.filter(Supplier.supplier_name.ilike(f'%{search_term}%'))
            logger.info(f"✅ Applied fallback supplier name search")
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
        """✅ Use existing field definitions and filter_aliases"""
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class or not config:
                return query, applied_filters, filter_count
            
            # ✅ Try configuration-driven approach first
            if hasattr(config, 'fields') and hasattr(config, 'filter_category_mapping'):
                # Process using existing field definitions
                for field in config.fields:
                    if not getattr(field, 'filterable', False):
                        continue
                        
                    # Check if this field is mapped to SELECTION category
                    if (field.name in config.filter_category_mapping and 
                        config.filter_category_mapping[field.name] == FilterCategory.SELECTION):
                        
                        # ✅ Use existing filter_aliases
                        field_names_to_check = [field.name]
                        if hasattr(field, 'filter_aliases') and field.filter_aliases:
                            field_names_to_check.extend(field.filter_aliases)
                        
                        # Find matching filter value
                        filter_value = None
                        matched_filter_key = None
                        
                        for possible_name in field_names_to_check:
                            if possible_name in filters and filters[possible_name]:
                                filter_value = filters[possible_name]
                                matched_filter_key = possible_name
                                break
                        
                        if filter_value is not None:
                            # Handle array format (existing logic)
                            if isinstance(filter_value, list) and len(filter_value) > 0:
                                filter_value = filter_value[0]
                            
                            # Apply filter if model has the field
                            if hasattr(model_class, field.name):
                                db_field = getattr(model_class, field.name)
                                
                                # ✅ FIX: Use mixed payment logic for payment_method field
                                if field.name == 'payment_method' and entity_type == 'supplier_payments':
                                    mixed_payment_condition = self._apply_mixed_payment_logic(
                                        model_class, db_field, filter_value, config
                                    )
                                    if mixed_payment_condition is not None:
                                        query = query.filter(mixed_payment_condition)
                                        logger.info(f"✅ Applied selection filter with mixed logic: {field.name} = {filter_value}")
                                    else:
                                        # Fallback to exact match if mixed logic fails
                                        query = query.filter(db_field == filter_value)
                                        logger.info(f"✅ Applied selection filter (exact fallback): {field.name} = {filter_value}")
                                else:
                                    # For non-payment_method fields, use exact match
                                    query = query.filter(db_field == filter_value)
                                    logger.info(f"✅ Applied selection filter: {field.name} = {filter_value}")
                                
                                applied_filters.add(matched_filter_key)
                                filter_count += 1
                
                # Return if configuration processing succeeded
                if filter_count > 0 or not hasattr(config, 'fields'):
                    return query, applied_filters, filter_count
            
            # ✅ FIX: Use configuration-driven logic instead of hardcoded fallback
            if entity_type == 'supplier_payments':
                # Handle workflow_status using mixed logic
                if 'workflow_status' in filters and filters['workflow_status']:
                    if hasattr(model_class, 'workflow_status'):
                        model_attr = getattr(model_class, 'workflow_status')
                        query = query.filter(model_attr == filters['workflow_status'])
                        applied_filters.add('workflow_status')
                        filter_count += 1
                
                # ✅ FIX: Handle payment_method using configuration-driven mixed payment logic
                if 'payment_method' in filters and filters['payment_method']:
                    if hasattr(model_class, 'payment_method'):
                        model_attr = getattr(model_class, 'payment_method')
                        
                        # Use configuration-driven mixed payment logic
                        mixed_payment_condition = self._apply_mixed_payment_logic(
                            model_class, model_attr, filters['payment_method'], config
                        )
                        if mixed_payment_condition is not None:
                            query = query.filter(mixed_payment_condition)
                            logger.info(f"✅ Applied payment_method with config-driven mixed logic: {filters['payment_method']}")
                        else:
                            # Fallback to exact match only if config-driven logic fails
                            query = query.filter(model_attr == filters['payment_method'])
                            logger.info(f"✅ Applied payment_method with exact match fallback: {filters['payment_method']}")
                        
                        applied_filters.add('payment_method')
                        filter_count += 1
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"Error in selection filter processing: {str(e)}")
            return query, applied_filters, filter_count
    
    # ==========================================================================
    # RELATIONSHIP CATEGORY PROCESSING
    # ==========================================================================
    
    def _process_relationship_filters(self, filters: Dict[str, Any], query: Query, 
                                config, entity_type: str) -> Tuple[Query, Set[str], int]:
        """Process relationship/foreign key filters - Using existing field configurations"""
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class:
                return query, applied_filters, filter_count
            
            # ✅ PHASE 1D CORRECTED: Use existing field definitions with filter_aliases
            config_processed = False
            
            if config and hasattr(config, 'fields'):
                logger.info(f"✅ Using existing field configurations for {entity_type} relationship filters")
                
                for field in config.fields:
                    # Check if this is a relationship field (UUID, ENTITY_SEARCH, REFERENCE)
                    if (field.field_type in [FieldType.UUID, FieldType.ENTITY_SEARCH, FieldType.REFERENCE] and 
                        getattr(field, 'filterable', False)):
                        
                        # Check field name and existing filter_aliases
                        field_names_to_check = [field.name]
                        if hasattr(field, 'filter_aliases') and field.filter_aliases:
                            field_names_to_check.extend(field.filter_aliases)
                        
                        # Find matching filter value
                        filter_value = None
                        matched_filter_key = None
                        
                        for possible_name in field_names_to_check:
                            if possible_name in filters and filters[possible_name] and str(filters[possible_name]).strip():
                                filter_value = str(filters[possible_name]).strip()
                                matched_filter_key = possible_name
                                break
                        
                        if filter_value:
                            success = self._apply_relationship_filter_using_field_config(
                                query, model_class, field, filter_value
                            )
                            
                            if success:
                                applied_filters.add(matched_filter_key)
                                filter_count += 1
                                config_processed = True
                                logger.info(f"✅ Applied relationship filter using field config {field.name}: {filter_value}")
            
            # ✅ FALLBACK: Original hardcoded logic for backward compatibility
            if not config_processed:
                logger.info(f"⚠️ No field configurations found for {entity_type}, using fallback relationship logic")
                
                # Process entity ID filters with hardcoded list
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
                                logger.info(f"✅ Applied fallback {field_name} filter: {filter_value}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Invalid {field_name} value: {filter_value} - {str(e)}")
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"❌ Error processing relationship filters: {str(e)}")
            return query, applied_filters, filter_count

    def _apply_relationship_filter_using_field_config(self, query: Query, model_class, 
                                                    field, filter_value: str) -> bool:
        """Apply relationship filter using existing field configuration"""
        try:
            if not hasattr(model_class, field.name):
                logger.warning(f"Field {field.name} not found in model {model_class.__name__}")
                return False
            
            model_attr = getattr(model_class, field.name)
            
            # ✅ UNIVERSAL LOGIC: UUID conversion and validation (hardcoded)
            if field.field_type in [FieldType.UUID, FieldType.REFERENCE]:
                if isinstance(filter_value, str) and len(filter_value) == 36:
                    try:
                        filter_value = uuid.UUID(filter_value)
                        logger.debug(f"Converted {filter_value} to UUID for field {field.name}")
                    except ValueError:
                        # Not a valid UUID, use as string
                        logger.debug(f"Using {filter_value} as string for field {field.name}")
                        pass
            
            # Apply the filter
            query = query.filter(model_attr == filter_value)
            
            # Enhanced logging with field info
            logger.info(f"✅ Applied relationship filter on {model_class.__name__}.{field.name}: {filter_value}")
            return True
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid relationship filter value for {field.name}: {filter_value} - {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error applying relationship filter for {field.name}: {str(e)}")
            return False

# =============================================================================
#  FORM PREPARATION HELPERS
# =============================================================================

    def get_choices_for_field(self, field_name: str, entity_type: str, hospital_id: uuid.UUID, 
                         branch_id: Optional[uuid.UUID] = None) -> List[Tuple]:
        """
        ADDED: Universal helper for form preparation
        Single method to get choices for any field type using filter categories
        """
        try:
            # Get field configuration
            config = get_entity_config(entity_type)
            if not config:
                logger.warning(f"No configuration found for entity: {entity_type}")
                return []
            
            # Find field in configuration
            field_config = None
            for field in config.fields:
                if field.name == field_name:
                    field_config = field
                    break
            
            if not field_config:
                logger.warning(f"Field {field_name} not found in {entity_type} configuration")
                return []
            
            # Get field category
            field_category = self._get_field_category(field_config, entity_type)
            
            # Route to appropriate helper based on category
            if field_category == FilterCategory.RELATIONSHIP:
                return self.get_relationship_choices(field_config, hospital_id, branch_id)
            elif field_category == FilterCategory.SELECTION:
                return self.get_selection_choices(field_config, entity_type)
            elif field_category == FilterCategory.DATE:
                return self.get_date_preset_choices()
            else:
                logger.warning(f"Category {field_category} doesn't need dropdown choices")
                return []
            
        except Exception as e:
            logger.error(f"Error getting choices for field {field_name}: {str(e)}")
            return []

    def get_relationship_choices(self, field_config, hospital_id: uuid.UUID, 
                                branch_id: Optional[uuid.UUID] = None) -> List[Tuple]:
        """
        ADDED: Get choices for relationship fields (entity dropdowns)
        """
        try:
            field_name = field_config.name
            
            # Use existing service patterns for consistency
            if field_name == 'supplier_id':
                from app.services.supplier_service import get_suppliers_for_choice
                return get_suppliers_for_choice(hospital_id, branch_id)
            elif field_name == 'branch_id':
                # Future: Add branch service call
                return self._get_branch_choices(hospital_id)
            elif field_name == 'patient_id':
                # Future: Add patient service call
                return []
            elif field_name == 'medicine_id':
                # Future: Add medicine service call
                return []
            else:
                logger.info(f"No relationship choices handler for {field_name}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting relationship choices: {str(e)}")
            return []

    def get_selection_choices(self, field_config, entity_type: str) -> List[Tuple]:
        """
        ADDED: Get choices for selection fields (enum dropdowns)
        """
        try:
            field_name = field_config.name
            
            # Handle known selection fields
            if field_name == 'payment_method':
                return [
                    ('cash', 'Cash'),
                    ('cheque', 'Cheque'), 
                    ('bank_transfer', 'Bank Transfer'),
                    ('online', 'Online Payment'),
                    ('credit_card', 'Credit Card'),
                    ('debit_card', 'Debit Card')
                ]
            elif field_name == 'workflow_status':
                return [
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                    ('paid', 'Paid'),
                    ('cancelled', 'Cancelled')
                ]
            elif field_name == 'status':
                return [
                    ('active', 'Active'),
                    ('inactive', 'Inactive'),
                    ('pending', 'Pending'),
                    ('cancelled', 'Cancelled')
                ]
            else:
                # Try to get from field configuration
                if hasattr(field_config, 'choices') and field_config.choices:
                    return field_config.choices
                
                logger.warning(f"No selection choices defined for {field_name}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting selection choices for {field_name}: {str(e)}")
            return []

    def get_date_preset_choices(self) -> List[Tuple]:
        """
        ADDED: Get date preset choices for date fields
        """
        return [
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('this_week', 'This Week'),
            ('last_week', 'Last Week'),
            ('this_month', 'This Month'),
            ('last_month', 'Last Month'),
            ('this_quarter', 'This Quarter'),
            ('last_quarter', 'Last Quarter'),
            ('this_year', 'This Year'),
            ('last_year', 'Last Year'),
            ('current_financial_year', 'Current Financial Year'),
            ('last_financial_year', 'Last Financial Year')
        ]

    def get_backend_dropdown_data(self, entity_type: str, hospital_id: uuid.UUID, 
                            branch_id: Optional[uuid.UUID] = None) -> Dict:
        """✅ Enhanced to use existing field definitions and configuration"""
        try:
            # Get entity configuration
            config = get_entity_config(entity_type)
            if not config:
                logger.warning(f"No configuration found for entity: {entity_type}")
                return {}
            
            dropdown_data = {}
            
            # ✅ Use existing field definitions with configuration
            if hasattr(config, 'fields'):
                for field in config.fields:
                    if not getattr(field, 'filterable', False):
                        continue
                    
                    field_name = field.name
                    
                    # Handle SELECT fields
                    if field.field_type == FieldType.SELECT:
                        if hasattr(field, 'options') and field.options:
                            # ✅ Use existing static options from configuration
                            dropdown_data[field_name] = field.options
                        elif hasattr(field, 'related_field') and field.related_field:
                            # ✅ Use existing related_field mappings
                            choices = self.get_choices_for_field(field_name, entity_type, hospital_id, branch_id)
                            if choices:
                                dropdown_data[field_name] = choices
                    
                    # Handle ENTITY_SEARCH fields
                    elif field.field_type == FieldType.ENTITY_SEARCH:
                        if hasattr(field, 'entity_search_config') and field.entity_search_config:
                            # ✅ Use existing entity_search_config
                            try:
                                from app.engine.universal_entity_search_service import UniversalEntitySearchService
                                search_service = UniversalEntitySearchService()
                                search_data = search_service.search_entities(
                                    config=field.entity_search_config,
                                    search_term='',  # Empty to get common results
                                    hospital_id=hospital_id,
                                    branch_id=branch_id
                                )
                                dropdown_data[f"{field_name}_search"] = search_data[:5]  # Limit for dropdown
                            except Exception as e:
                                logger.error(f"Error getting entity search data for {field_name}: {str(e)}")
            
            # ✅ Fallback to existing logic if no configuration data
            if not dropdown_data:
                # Use existing get_choices_for_field method for backward compatibility
                field_category = self._get_field_category(field, entity_type) if 'field' in locals() else None
                
                if field_category in [FilterCategory.RELATIONSHIP, FilterCategory.SELECTION]:
                    choices = self.get_choices_for_field(field.name, entity_type, hospital_id, branch_id)
                    if choices:
                        dropdown_data[field.name] = choices
            
            # Add date presets if entity has date fields
            if self._has_date_fields(config):
                dropdown_data['date_presets'] = self.get_date_preset_choices()
            
            logger.info(f"✅ Generated dropdown data for {entity_type}: {list(dropdown_data.keys())}")
            return dropdown_data
            
        except Exception as e:
            logger.error(f"Error getting backend dropdown data: {str(e)}")
            return {}

    def _get_supplier_dropdown_options(self, hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> List[Dict]:
        """Get supplier options for dropdown"""
        try:
            from app.services.database_service import get_db_session
            from app.models.master import Supplier
            
            with get_db_session() as session:
                query = session.query(Supplier).filter_by(hospital_id=hospital_id)
                if branch_id:
                    query = query.filter_by(branch_id=branch_id)
                
                suppliers = query.filter_by(status='active').order_by(Supplier.supplier_name).all()
                
                return [
                    {'value': str(supplier.supplier_id), 'label': supplier.supplier_name}
                    for supplier in suppliers
                ]
        except Exception as e:
            logger.error(f"Error getting supplier options: {str(e)}")
            return []

    def _get_invoice_dropdown_options(self, hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> List[Dict]:
        """Get invoice options for dropdown"""
        try:
            from app.services.database_service import get_db_session
            from app.models.transaction import SupplierInvoice
            
            with get_db_session() as session:
                query = session.query(SupplierInvoice).filter_by(hospital_id=hospital_id)
                if branch_id:
                    query = query.filter_by(branch_id=branch_id)
                
                invoices = query.filter_by(status='active').order_by(SupplierInvoice.invoice_number).limit(20).all()
                
                return [
                    {'value': str(invoice.invoice_id), 'label': invoice.invoice_number}
                    for invoice in invoices
                ]
        except Exception as e:
            logger.error(f"Error getting invoice options: {str(e)}")
            return []


    def _get_field_category(self, field_config, entity_type: str) -> FilterCategory:
        """
        ADDED: Get filter category for field using existing logic
        """
        try:
            # Use existing category mapping if available
            config = get_entity_config(entity_type)
            if config and hasattr(config, 'filter_category_mapping'):
                mapping = config.filter_category_mapping
                if field_config.name in mapping:
                    return mapping[field_config.name]
            
            # Fallback to field type detection
            from app.config.filter_categories import get_field_category_from_existing_field
            return get_field_category_from_existing_field(field_config)
            
        except Exception as e:
            logger.error(f"Error getting field category: {str(e)}")
            return FilterCategory.SEARCH  # Safe default

    def _has_date_fields(self, config) -> bool:
        """
        ADDED: Check if entity has date fields
        """
        return any(
            self._get_field_category(field, config.entity_type) == FilterCategory.DATE
            for field in config.fields
        )

    def _get_branch_choices(self, hospital_id: uuid.UUID) -> List[Tuple]:
        """
        ADDED: Get branch choices (placeholder for future implementation)
        """
        try:
            # Future: Add actual branch service call
            return [('all', 'All Branches')]
        except Exception as e:
            logger.error(f"Error getting branch choices: {str(e)}")
            return []


    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def _get_model_class(self, entity_type: str):
        """✅ Use existing configuration structure"""
        config = get_entity_config(entity_type)
        if config and hasattr(config, 'model_class'):
            try:
                module_path, class_name = config.model_class.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                return getattr(module, class_name)
            except Exception as e:
                logger.warning(f"Config model import failed: {str(e)}")
        
        # ✅ Keep existing fallback for backward compatibility
        if entity_type == 'supplier_payments':
            from app.models.transaction import SupplierPayment
            return SupplierPayment
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

    def execute_complete_search(self, entity_type: str, filters: Dict, filter_data: Dict,
                          hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID] = None,
                          page: int = 1, per_page: int = 20) -> Optional[Dict]:
        """
        ✅ COMPLETE SEARCH: Execute complete search using existing categorized filtering
        Proper place for database query logic
        """
        try:
            from app.services.database_service import get_db_session, get_entity_dict
            from app.config.entity_configurations import get_entity_config
            from sqlalchemy import desc
            
            # Get configuration and model
            config = get_entity_config(entity_type)
            if not config:
                logger.warning(f"No configuration found for {entity_type}")
                return None
            
            model_class = self._get_model_class(entity_type)
            if not model_class:
                logger.warning(f"No model class found for {entity_type}")
                return None
            
            with get_db_session() as session:
                # Base query
                query = session.query(model_class).filter_by(hospital_id=hospital_id)
                
                # Branch filter if supported
                if branch_id and hasattr(model_class, 'branch_id'):
                    query = query.filter(model_class.branch_id == branch_id)
                    logger.info(f"Applied branch filter for {entity_type}: {branch_id}")
                
                # Apply existing categorized filters
                query, applied_filters, filter_count = self.process_entity_filters(
                    entity_type=entity_type,
                    filters=filters,
                    query=query,
                    session=session,
                    config=config
                )
                
                logger.info(f"✅ [EXISTING_PROCESSOR] Applied {filter_count} filters for {entity_type}: {applied_filters}")
                
                # Apply sorting from configuration
                sort_field = filters.get('sort_field', getattr(config, 'default_sort_field', 'created_at'))
                sort_direction = filters.get('sort_direction', getattr(config, 'default_sort_order', 'desc'))
                
                if hasattr(model_class, sort_field):
                    sort_attr = getattr(model_class, sort_field)
                    if sort_direction.lower() == 'desc':
                        query = query.order_by(desc(sort_attr))
                    else:
                        query = query.order_by(sort_attr)
                
                # Pagination
                total_count = query.count()
                offset = (page - 1) * per_page
                entities = query.offset(offset).limit(per_page).all()
                
                # Convert to dictionaries
                entity_dicts = []
                for entity in entities:
                    entity_dict = get_entity_dict(entity)
                    
                    # Add basic relationships (can be enhanced with configuration later)
                    entity_dict = self._add_basic_relationships(entity_dict, entity, entity_type, session)
                    
                    entity_dicts.append(entity_dict)
                
                # Use summary from filter_data (already calculated with same filters)
                summary = filter_data.get('summary_data', {})
                if summary:
                    # Update with actual query count (may differ from summary due to pagination)
                    summary['total_count'] = total_count
                    logger.info(f"✅ [REUSED_SUMMARY] Using pre-calculated summary, updated count: {total_count}")
                else:
                    # Fallback if no summary available
                    summary = {'total_count': total_count}
                    logger.info(f"✅ [BASIC_SUMMARY] Created basic summary: {total_count}")
                
                # Build pagination
                pagination = {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': (total_count + per_page - 1) // per_page,
                    'has_prev': page > 1,
                    'has_next': page < ((total_count + per_page - 1) // per_page)
                }
                
                return {
                    'items': entity_dicts,
                    'total': total_count,
                    'pagination': pagination,
                    'summary': summary,
                    'success': True,
                    'applied_filters': list(applied_filters),
                    'filter_count': filter_count,
                    'metadata': {
                        'categorized_filtering': True,
                        'orchestrated_by': 'categorized_processor',
                        'entity_agnostic': True,
                        'routing_method': 'complete_system_primary'
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ Error in complete search execution for {entity_type}: {str(e)}")
            return None

    def _add_basic_relationships(self, entity_dict: Dict, entity, entity_type: str, session) -> Dict:
        """
        ✅ BASIC RELATIONSHIPS: Add entity relationships
        Future: Will use configuration-driven approach
        """
        try:
            # For supplier_payments - preserve existing relationship logic
            if entity_type == 'supplier_payments':
                from app.models.master import Supplier, Branch
                from app.models.transaction import SupplierInvoice
                
                # Add supplier info
                if hasattr(entity, 'supplier_id') and entity.supplier_id:
                    supplier = session.query(Supplier).filter_by(supplier_id=entity.supplier_id).first()
                    if supplier:
                        entity_dict['supplier_name'] = supplier.supplier_name
                        entity_dict['supplier_code'] = str(supplier.supplier_id)
                    else:
                        entity_dict['supplier_name'] = 'N/A'
                        entity_dict['supplier_code'] = 'N/A'
                
                # Add branch info
                if hasattr(entity, 'branch_id') and entity.branch_id:
                    branch = session.query(Branch).filter_by(branch_id=entity.branch_id).first()
                    if branch:
                        entity_dict['branch_name'] = branch.name
                
                # Add invoice info
                if hasattr(entity, 'invoice_id') and entity.invoice_id:
                    invoice = session.query(SupplierInvoice).filter_by(invoice_id=entity.invoice_id).first()
                    if invoice:
                        entity_dict['invoice_number'] = invoice.supplier_invoice_number
                        entity_dict['invoice_amount'] = float(invoice.total_amount)
            
            # For other entities - add relationships as needed
            # Future: Use configuration-driven relationships
            
            return entity_dict
            
        except Exception as e:
            logger.warning(f"Error adding basic relationships for {entity_type}: {str(e)}")
            return entity_dict


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