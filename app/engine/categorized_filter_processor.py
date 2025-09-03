
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

from typing import Dict, Any, List, Optional, Set, Tuple, Type
import uuid
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from flask import request 
from sqlalchemy.orm import Session, Query
from sqlalchemy import and_, or_, func, desc, asc
from flask_login import current_user
from flask import current_app
import importlib

from app.config.filter_categories import (
    FilterCategory, 
    organize_current_filters_by_category,
    get_category_processing_order,
    enhance_entity_config_with_categories,
    FILTER_CATEGORY_CONFIG
)
from app.config.entity_configurations import get_entity_config, get_entity_filter_config
from app.config.core_definitions import FieldType, FieldDefinition, FilterOperator
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class CategorizedFilterProcessor:
    """
    Single source of truth for all entity filtering
    Replaces complex cascading filter logic with clean category-based processing
    """
    
    def __init__(self):
        self.session = None
    

    def get_template_filter_fields(self, entity_type: str, 
                               hospital_id: uuid.UUID,
                               branch_id: Optional[uuid.UUID] = None) -> List[Dict]:
        """
        TEMPLATE WRAPPER: Orchestrates existing methods to prepare template-ready fields
        
        Architecture:
        - This method: Template formatting layer (NEW)
        - get_backend_dropdown_data(): Backend data provider (KEEP - we use it)
        - get_choices_for_field(): Field-specific choices (KEEP - fallback)
        - get_selection_choices(): Enum/select choices (KEEP - used by above)
        - get_relationship_choices(): FK choices (KEEP - used by above)
        
        DO NOT DELETE the above methods - they form the data pipeline!
        
        Future cleanup opportunity:
        - Once all entities use views, some entity-specific logic can be removed
        - But the core pipeline should remain
        """
        try:
            from app.config.core_definitions import FilterOperator
            
            config = get_entity_config(entity_type)
            if not config:
                logger.warning(f"No configuration found for entity: {entity_type}")
                return []
            
            filter_config = get_entity_filter_config(entity_type)
            backend_data = self.get_backend_dropdown_data(entity_type, hospital_id, branch_id)
            current_filters = request.args.to_dict() if request else {}
            filter_fields = []
            
            # Add search field with simple label
            if config.searchable_fields:
                filter_fields.append({
                    'name': 'search',
                    'label': 'Text Search',  # Simple, consistent
                    'type': 'text',
                    'value': current_filters.get('search', ''),
                    'placeholder': f"Search in {', '.join(config.searchable_fields[:2])}...",
                    'required': False,
                    'options': []
                })
            
            # Process filterable fields
            for field in config.fields:
                if not getattr(field, 'filterable', False):
                    continue
                
                field_name = field.name
                base_label = getattr(field, 'label', field_name.replace('_', ' ').title())
                
                # Get filter operator (default to EQUALS if not specified)
                filter_operator = getattr(field, 'filter_operator', FilterOperator.EQUALS)
                
                # Enhance label based on operator
                enhanced_label = self._enhance_label_with_operator(base_label, filter_operator, field.field_type)
                
                # Get the field type
                field_type = self._map_field_to_input_type(field)
                field_options = []
                
                # Get options for select fields
                if field_type == 'select':
                    # Use universal method for options
                    field_options = self.get_field_options_universal(
                        entity_type,
                        field_name,
                        context='filter',
                        hospital_id=hospital_id,
                        branch_id=branch_id
                    )
                
                # Get placeholder based on operator
                placeholder = self._get_operator_placeholder(field, filter_operator)
                
                field_data = {
                    'name': field_name,
                    'label': enhanced_label,
                    'type': field_type,
                    'value': current_filters.get(field_name, ''),
                    'placeholder': placeholder,
                    'required': False,
                    'options': self._normalize_options(field_options, base_label) if field_options else [],
                    'operator': filter_operator.value if isinstance(filter_operator, FilterOperator) else 'equals'
                }
                
                filter_fields.append(field_data)
            
            return filter_fields
            
        except Exception as e:
            logger.error(f"Error getting template filter fields for {entity_type}: {str(e)}")
            return []


    def _normalize_options(self, options: Any, field_label: str) -> List[Dict]:
        """
        NEW METHOD: Normalize options to consistent template format
        Handles tuples, dicts, and lists
        """
        normalized = [{'value': '', 'label': f'All {field_label}'}]
        
        if not options:
            return normalized
        
        for option in options:
            if isinstance(option, tuple) and len(option) >= 2:
                normalized.append({'value': str(option[0]), 'label': str(option[1])})
            elif isinstance(option, dict):
                normalized.append({
                    'value': str(option.get('value', '')),
                    'label': str(option.get('label', option.get('value', '')))
                })
            else:
                normalized.append({'value': str(option), 'label': str(option)})
        
        return normalized

    def _map_field_to_input_type(self, field) -> str:
        """
        Map field type to HTML input type
        """
        from app.config.core_definitions import FieldType
        
        # ✅ FIX: Handle STATUS_BADGE and STATUS as select
        if field.field_type in [FieldType.SELECT, FieldType.STATUS_BADGE, FieldType.STATUS]:
            return 'select'
        elif field.field_type in [FieldType.DATE, FieldType.DATETIME]:
            # Check for date range
            if hasattr(field, 'filter_aliases'):
                for alias in field.filter_aliases:
                    if 'start' in alias or 'end' in alias:
                        return 'date_range'
            return 'date'
        elif field.field_type in [FieldType.NUMBER, FieldType.DECIMAL, FieldType.CURRENCY, FieldType.AMOUNT]:
            return 'number'
        elif field.field_type == FieldType.EMAIL:
            return 'email'
        elif field.field_type == FieldType.BOOLEAN:
            return 'select'  # Boolean as select with Yes/No options
        else:
            return 'text'

    
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
                return or_(
                    model_attr == filter_value,
                    and_(model_attr == 'mixed', amount_attr > 0)
                )
            else:
                # For payment methods without amount fields, use exact match
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
                return conventional_field_name
            
            # Strategy 2: Search in field definitions with payment method in name
            for field in config.fields:
                field_name = field.name
                # Check if field name contains payment method and ends with amount
                if (payment_method.lower() in field_name.lower() and 
                    'amount' in field_name.lower() and 
                    hasattr(model_class, field_name)):
                    return field_name
            
            # Strategy 3: Look for explicit mapping in field configuration (future enhancement)
            for field in config.fields:
                if (hasattr(field, 'payment_method_mapping') and 
                    field.payment_method_mapping and 
                    payment_method in field.payment_method_mapping):
                    mapped_field = field.payment_method_mapping[payment_method]
                    if hasattr(model_class, mapped_field):
                        return mapped_field
            
            logger.warning(f"⚠️ [CONFIG_MAPPING] No amount field found for payment method: {payment_method}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding amount field for {payment_method}: {str(e)}")
            return None

    def _apply_field_with_operator(self, query: Query, field_name: str, value: Any, 
                               operator, model_class, field_def=None) -> Query:
        """
        Apply filter with specific operator - UNIVERSAL method for all categories
        This is the central method that handles all filter operators
        """
        from app.config.core_definitions import FilterOperator

        # ✅ Use db_column if specified, otherwise use field_name
        actual_column = field_name
        if field_def and hasattr(field_def, 'db_column') and field_def.db_column:
            actual_column = field_def.db_column
        
        if not hasattr(model_class, actual_column):
            logger.warning(f"Model {model_class.__name__} doesn't have field {actual_column}")
            return query
        
        model_field = getattr(model_class, actual_column)
        
        # Handle None or empty values
        if value is None or value == '':
            return query
        
        # Apply operator-based filtering
        if operator == FilterOperator.EQUALS:
            return query.filter(model_field == value)
            
        elif operator == FilterOperator.CONTAINS:
            return query.filter(model_field.ilike(f'%{value}%'))
            
        elif operator == FilterOperator.LESS_THAN:
            return query.filter(model_field < value)
            
        elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return query.filter(model_field <= value)
            
        elif operator == FilterOperator.GREATER_THAN:
            return query.filter(model_field > value)
            
        elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return query.filter(model_field >= value)
            
        elif operator == FilterOperator.DATE_ON_OR_BEFORE:
            return query.filter(model_field <= value)
            
        elif operator == FilterOperator.DATE_ON_OR_AFTER:
            return query.filter(model_field >= value)
            
        elif operator == FilterOperator.BETWEEN:
            # Expects value to be a tuple/list (min, max)
            if isinstance(value, (list, tuple)) and len(value) == 2:
                return query.filter(model_field.between(value[0], value[1]))
            else:
                logger.warning(f"BETWEEN operator requires tuple/list with 2 values, got {value}")
                return query
                
        elif operator == FilterOperator.IN:
            if isinstance(value, (list, tuple)):
                return query.filter(model_field.in_(value))
            else:
                return query.filter(model_field == value)
                
        elif operator == FilterOperator.NOT_IN:
            if isinstance(value, (list, tuple)):
                return query.filter(~model_field.in_(value))
            else:
                return query.filter(model_field != value)
                
        else:
            # Default to EQUALS if operator unknown
            logger.warning(f"Unknown operator {operator}, defaulting to EQUALS")
            return query.filter(model_field == value)

    def process_entity_filters(self, entity_type: str, filters: Dict[str, Any], 
                         query: Query, model_class: Type, session: Session,
                         hospital_id: uuid.UUID = None, branch_id: uuid.UUID = None,
                         config=None) -> Tuple[Query, Set[str], int]:
        """
        Main entry point - processes ALL filters by category
        
        Args:
            entity_type: Entity type ('supplier_payments', etc.)
            filters: Filter values from request
            query: SQLAlchemy Query object
            model_class: SQLAlchemy model class for the entity
            session: Database session
            hospital_id: Hospital ID for filtering (optional)
            branch_id: Branch ID for filtering (optional)
            config: Entity configuration (optional)
        """
        # DEFENSIVE CHECK: Ensure model_class is provided
        if model_class is None:
            logger.error(f"model_class parameter is required for entity_type: {entity_type}")
            model_class = self._get_model_class(entity_type)
            if not model_class:
                logger.error(f"Could not resolve model_class for entity_type: {entity_type}")
                return query, set(), 0
            logger.warning(f"Recovered model_class for {entity_type}: {model_class.__name__}")

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

            # Check filter_category_mapping availability
            if not hasattr(config, 'filter_category_mapping') or not config.filter_category_mapping:
                logger.warning(f"No filter_category_mapping found for {entity_type}")

            # Organize filters by category using the smart function from filter_categories
            from app.config.filter_categories import organize_current_filters_by_category

            # This function already has fallback detection for date filters!
            categorized_filters = organize_current_filters_by_category(filters, config)
            
            if not categorized_filters:
                logger.debug(f"No filters provided for {entity_type}")
                return query, set(), 0
            
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
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing {category.value} filters: {str(e)}")
                        # Continue with other categories on error
                        continue
            
            logger.debug(f"Applied {total_filter_count} categorized filters to {entity_type}")
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
            
            # ✅ Process individual date fields with operators FIRST
            from app.config.core_definitions import FilterOperator, FieldType
            if config and hasattr(config, 'fields'):
                for field in config.fields:
                    if not getattr(field, 'filterable', False):
                        continue
                    
                    # Check if this field is in the date category and has a value
                    if (hasattr(config, 'filter_category_mapping') and 
                        field.name in config.filter_category_mapping and
                        config.filter_category_mapping[field.name] == FilterCategory.DATE and
                        field.name in filters):
                        
                        field_value = filters.get(field.name)
                        if field_value:
                            # Get operator (default to EQUALS)
                            operator = getattr(field, 'filter_operator', FilterOperator.EQUALS)
                            
                            # Apply field with operator
                            query = self._apply_field_with_operator(
                                query, field.name, field_value, operator, model_class, field
                            )
                            applied_filters.add(field.name)
                            filter_count += 1

            # Handle date range filters
            start_date = filters.get('start_date')
            end_date = filters.get('end_date')
            
            # Apply default financial year if no explicit dates provided
            if not start_date and not end_date:
                # ✅ PHASE 1A: Configuration-driven default financial year application
                if config and hasattr(config, 'default_filters') and config.default_filters.get('financial_year'):
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

            if start_date or end_date:
                date_field = self._get_primary_date_field(model_class, config)
                
                if start_date:
                    try:
                        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                        query = query.filter(date_field >= start_date_obj)
                        applied_filters.add('start_date')
                        filter_count += 1
                    except ValueError:
                        logger.warning(f"Invalid start_date format: {start_date}")
                
                if end_date:
                    try:
                        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                        query = query.filter(date_field <= end_date_obj)
                        applied_filters.add('end_date')
                        filter_count += 1
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
                return getattr(model_class, primary_field)
            else:
                logger.warning(f"⚠️ Configured primary date field '{primary_field}' not found in model {model_class.__name__}")
        
        # ✅ FALLBACK: Original hardcoded logic (preserved for backward compatibility)
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

            # ✅ Process individual amount fields with operators FIRST
            from app.config.core_definitions import FilterOperator
            if config and hasattr(config, 'fields'):
                for field in config.fields:
                    if not getattr(field, 'filterable', False):
                        continue
                    
                    # Check if this field is in the amount category and has a value
                    if (hasattr(config, 'filter_category_mapping') and 
                        field.name in config.filter_category_mapping and
                        config.filter_category_mapping[field.name] == FilterCategory.AMOUNT and
                        field.name in filters):
                        
                        field_value = filters.get(field.name)
                        if field_value:
                            try:
                                # Convert to float for amount fields
                                numeric_value = float(field_value)
                                operator = getattr(field, 'filter_operator', FilterOperator.EQUALS)
                                
                                # Apply field with operator
                                query = self._apply_field_with_operator(
                                    query, field.name, numeric_value, operator, model_class, field
                                )
                                applied_filters.add(field.name)
                                filter_count += 1
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid amount value for {field.name}: {field_value}")

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
                return getattr(model_class, primary_field)
            else:
                logger.warning(f"⚠️ Configured primary amount field '{primary_field}' not found in model {model_class.__name__}")
        
        # ✅ FALLBACK: Original hardcoded logic (preserved for backward compatibility)
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
        """Process search-related filters - Standard processing only"""
        applied_filters = set()
        filter_count = 0
        
        try:
            model_class = self._get_model_class(entity_type)
            if not model_class:
                return query, applied_filters, filter_count
            
            # ✅ Process individual search fields with operators
            from app.config.core_definitions import FilterOperator
            if config and hasattr(config, 'fields'):
                for field in config.fields:
                    if not getattr(field, 'filterable', False):
                        continue
                    
                    # Check if this field is in search category and has a value
                    if (hasattr(config, 'filter_category_mapping') and 
                        field.name in config.filter_category_mapping and
                        config.filter_category_mapping[field.name] == FilterCategory.SEARCH and
                        field.name in filters):
                        
                        field_value = filters.get(field.name)
                        if field_value and str(field_value).strip():
                            search_term = str(field_value).strip()
                            operator = getattr(field, 'filter_operator', FilterOperator.CONTAINS)
                            
                            # Apply field with operator
                            query = self._apply_field_with_operator(
                                query, field.name, search_term, operator, model_class, field
                            )
                            applied_filters.add(field.name)
                            filter_count += 1
            
            # Handle generic search field (for searchable_fields)
            searchable_fields = getattr(config, 'searchable_fields', [])
            if searchable_fields and 'search' in filters and filters['search']:
                search_term = str(filters['search']).strip()
                if search_term and 'search' not in applied_filters:
                    # Apply search across searchable fields
                    from sqlalchemy import or_
                    search_conditions = []
                    
                    for field_name in searchable_fields:
                        if hasattr(model_class, field_name):
                            field = getattr(model_class, field_name)
                            search_conditions.append(field.ilike(f'%{search_term}%'))
                    
                    if search_conditions:
                        query = query.filter(or_(*search_conditions))
                        applied_filters.add('search')
                        filter_count += 1
            
            return query, applied_filters, filter_count
            
        except Exception as e:
            logger.error(f"Error processing search filters: {str(e)}")
            return query, applied_filters, filter_count

    
    def _query_has_join(self, query: Query, model_class) -> bool:
        """Check if query already has a join for the specified model"""
        try:
            for desc in query.column_descriptions:
                if desc['entity'] == model_class:
                    return True
            return False
        except:
            return False
    
    def _enhance_label_with_operator(self, base_label: str, operator, field_type) -> str:
        """
        Enhance label based on filter operator
        """
        from app.config.core_definitions import FilterOperator, FieldType
        
        # If no operator or default equals, return base label
        if not operator or operator == FilterOperator.EQUALS:
            return base_label
        
        # Add operator context to label
        operator_labels = {
            FilterOperator.LESS_THAN: f"{base_label} (Less Than)",
            FilterOperator.LESS_THAN_OR_EQUAL: f"Max {base_label}",
            FilterOperator.GREATER_THAN: f"{base_label} (Greater Than)",
            FilterOperator.GREATER_THAN_OR_EQUAL: f"Min {base_label}",
            FilterOperator.DATE_ON_OR_BEFORE: f"{base_label} (On/Before)",
            FilterOperator.DATE_ON_OR_AFTER: f"{base_label} (On/After)",
            FilterOperator.CONTAINS: base_label,  # No change for contains
            FilterOperator.BETWEEN: f"{base_label} Range",
            FilterOperator.IN: f"{base_label} (Any Of)",
            FilterOperator.NOT_IN: f"{base_label} (Exclude)"
        }
        
        return operator_labels.get(operator, base_label)

    def _get_operator_placeholder(self, field, operator) -> str:
        """
        Get appropriate placeholder based on operator
        """
        from app.config.core_definitions import FilterOperator
        
        base_placeholder = getattr(field, 'placeholder', f"Filter by {field.label}...")
        
        if not operator or operator == FilterOperator.EQUALS:
            return base_placeholder
        
        operator_placeholders = {
            FilterOperator.LESS_THAN_OR_EQUAL: f"Maximum value...",
            FilterOperator.GREATER_THAN_OR_EQUAL: f"Minimum value...",
            FilterOperator.DATE_ON_OR_BEFORE: "On or before this date...",
            FilterOperator.DATE_ON_OR_AFTER: "On or after this date...",
            FilterOperator.CONTAINS: f"Search in {field.label}...",
        }
        
        return operator_placeholders.get(operator, base_placeholder)

    def _get_search_field_label(self, entity_type: str, searchable_fields: List[str]) -> str:
        """
        Simple, consistent label for all entities
        """
        return "Text Search"

    def _get_field_options(self, field, filter_config, backend_data, 
                       entity_type, hospital_id, branch_id):
        """
        Consolidated option retrieval logic
        """
        field_options = []
        field_name = field.name
        
        # Priority 1: Filter configuration
        if filter_config and hasattr(filter_config, 'filter_mappings'):
            if field_name in filter_config.filter_mappings:
                field_mapping = filter_config.filter_mappings[field_name]
                if 'options' in field_mapping:
                    field_options = field_mapping['options']
        
        # Priority 2: Field options
        if not field_options and hasattr(field, 'options'):
            field_options = field.options
        
        # Priority 3: Backend data
        if not field_options:
            field_options = backend_data.get(field_name, [])
        
        # Priority 4: Dynamic lookup
        if not field_options:
            try:
                choices = self.get_choices_for_field(
                    field_name, entity_type, hospital_id, branch_id
                )
                if choices:
                    field_options = choices
            except:
                pass
        
        return field_options

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
                            
                            # ✅ FIX: Use db_column if specified
                            actual_column = field.name
                            if hasattr(field, 'db_column') and field.db_column:
                                actual_column = field.db_column
                            
                            # Apply filter if model has the field
                            if hasattr(model_class, actual_column):  # ✅ Use actual_column
                                db_field = getattr(model_class, actual_column)  # ✅ Use actual_column
                                
                                # ✅ FIX: Use mixed payment logic for payment_method field
                                if field.name == 'payment_method' and entity_type == 'supplier_payments':
                                    mixed_payment_condition = self._apply_mixed_payment_logic(
                                        model_class, db_field, filter_value, config
                                    )
                                    if mixed_payment_condition is not None:
                                        query = query.filter(mixed_payment_condition)
                                    else:
                                        # Fallback to exact match if mixed logic fails
                                        query = query.filter(db_field == filter_value)
                                else:
                                    # For non-payment_method fields, use exact match
                                    operator = getattr(field, 'filter_operator', FilterOperator.EQUALS)
                                    query = self._apply_field_with_operator(
                                        query, field.name, filter_value, operator, model_class, field
                                    )
                                
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
                        else:
                            # Fallback to exact match only if config-driven logic fails
                            query = query.filter(model_attr == filters['payment_method'])
                        
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
            
            # ✅ FALLBACK: Original hardcoded logic for backward compatibility
            if not config_processed:
                
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

    def get_selection_choices(self, field_name: str, entity_type: str) -> List[Tuple]:
        """
        Get selection choices for a field
        UPDATED: Now uses universal method as single source of truth
        
        Returns:
            List of tuples (value, label) for backward compatibility
        """
        try:
            # Use the new universal method
            options = self.get_field_options_universal(
                entity_type, 
                field_name, 
                context='filter'  # This context adds "All" option
            )
            
            # Convert to tuple format for backward compatibility
            return [(opt['value'], opt['label']) for opt in options]
            
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
            
            return dropdown_data
            
        except Exception as e:
            logger.error(f"Error getting backend dropdown data: {str(e)}")
            return {}


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
        """Get model class for entity type - configuration driven with fallback"""
        # First, try configuration (new way)
        config = get_entity_config(entity_type)
        if config and hasattr(config, 'model_class') and config.model_class:
            try:
                module_path, class_name = config.model_class.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                model = getattr(module, class_name)
                return model
            except Exception as e:
                logger.warning(f"Config model import failed: {str(e)}")
        
        # Second, try self.entity_models mapping (backward compatible)
        if entity_type in self.entity_models:
            try:
                module_path = self.entity_models[entity_type]
                module_path, class_name = module_path.rsplit('.', 1)
                module = __import__(module_path, fromlist=[class_name])
                model = getattr(module, class_name)
                return model
            except Exception as e:
                logger.warning(f"Entity models import failed: {str(e)}")
        
        logger.warning(f"No model class found for {entity_type}")
        return None


    def _is_using_view_model(self, config) -> bool:
        """
        Check if entity is using a view model
        Returns True if using a view (has direct supplier_name field)
        """
        # Check table name
        table_name = getattr(config, 'table_name', '')
        if table_name.endswith('_view'):
            logger.debug(f"✅ Entity using view: {table_name}")
            return True
        
        # Check model class path
        model_class = getattr(config, 'model_class', '')
        if 'views' in model_class.lower():
            logger.debug(f"✅ Entity using view model: {model_class}")
            return True
        
        return False
    
    def get_field_options_universal(self, entity_type: str, field_name: str, 
                                context: str = 'all', 
                                hospital_id: Optional[uuid.UUID] = None,
                                branch_id: Optional[uuid.UUID] = None) -> List[Dict]:
        """
        Universal method to get field options - single source of truth
        Used by: filters, universal forms, validators, APIs
        
        Args:
            entity_type: Entity type (e.g., 'supplier_payments', 'purchase_orders')
            field_name: Field name (e.g., 'status', 'payment_method')
            context: 'filter', 'create', 'edit', 'api', 'all'
            hospital_id: Optional hospital context for dynamic options
            branch_id: Optional branch context for dynamic options
        
        Returns:
            List of {'value': x, 'label': y} dictionaries
        """
        try:
            # Get configuration
            config = get_entity_config(entity_type)
            if not config:
                logger.warning(f"No configuration for entity: {entity_type}")
                return []
            
            # Find field by name OR aliases (backward compatibility)
            field_def = None
            for field in config.fields:
                # Direct name match
                if field.name == field_name:
                    field_def = field
                    break
                # Check filter aliases for backward compatibility
                if hasattr(field, 'filter_aliases') and field.filter_aliases:
                    if field_name in field.filter_aliases:
                        field_def = field
                        break
            
            if not field_def:
                logger.debug(f"Field {field_name} not found in {entity_type} config")
                
                # Check filter mappings as fallback (for backward compatibility)
                filter_config = get_entity_filter_config(entity_type)
                if filter_config and hasattr(filter_config, 'filter_mappings'):
                    if field_name in filter_config.filter_mappings:
                        mapping = filter_config.filter_mappings[field_name]
                        if 'options' in mapping:
                            options = mapping['options']
                            if options and isinstance(options[0], dict):
                                return options
                            # Convert tuples to dict format
                            return [{'value': opt[0], 'label': opt[1]} for opt in options]
                return []
            
            # Get options from field definition (single source of truth)
            options = []
            if hasattr(field_def, 'options') and field_def.options:
                # Ensure correct format
                if isinstance(field_def.options[0], dict):
                    options = field_def.options.copy()  # Copy to avoid modifying original
                else:
                    # Convert from tuples or lists
                    options = [{'value': opt[0], 'label': opt[1]} 
                            for opt in field_def.options]
            else:
                # No static options - might need dynamic loading
                # (e.g., suppliers, branches, etc.)
                if field_def.field_type in ['entity_search', 'relationship']:
                    # These would load dynamically - return empty for now
                    # Could implement dynamic loading here if needed
                    logger.debug(f"Field {field_name} requires dynamic loading")
                return []
            
            # Apply context-specific filtering
            if context == 'create':
                # Filter options for create context
                if field_def.name == 'status':  # Standardized field name
                    # Universal logic for ALL status fields
                    if entity_type in ['supplier_payments', 'purchase_orders', 'supplier_invoices']:
                        # Transaction entities: limited initial statuses
                        allowed_values = ['draft', 'pending']
                        options = [opt for opt in options 
                                if opt['value'] in allowed_values]
                    elif entity_type in ['suppliers', 'medicines', 'patients']:
                        # Master entities: default to active
                        allowed_values = ['active', 'pending']
                        options = [opt for opt in options 
                                if opt['value'] in allowed_values]
                
                elif field_name == 'payment_method':
                    # For create, maybe exclude 'mixed' as it's set automatically
                    if entity_type == 'supplier_payments':
                        options = [opt for opt in options 
                                if opt['value'] != 'mixed']
            
            elif context == 'edit':
                # All options available for edit (unless business rules apply)
                if field_def.name == 'status':
                    # Some statuses might not be directly settable
                    if entity_type in ['supplier_payments', 'purchase_orders']:
                        # Can't directly set to completed (requires workflow)
                        excluded = ['completed']
                        options = [opt for opt in options 
                                if opt['value'] not in excluded]
            
            elif context == 'filter':
                # Add "All" option at the beginning for filters
                all_label = f"All {field_def.label}" if hasattr(field_def, 'label') else "All"
                options = [{'value': '', 'label': all_label}] + options
            
            elif context == 'api':
                # Return all valid options for API validation
                pass
            
            # 'all' context returns everything unfiltered
            
            return options
            
        except Exception as e:
            logger.error(f"Error getting field options for {entity_type}.{field_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def get_field_definition(self, entity_type: str, field_name: str) -> Optional[FieldDefinition]:
        """
        Get field definition by name or alias
        Helper method for other functions
        """
        config = get_entity_config(entity_type)
        if not config:
            return None
        
        for field in config.fields:
            # Check direct name
            if field.name == field_name:
                return field
            # Check aliases
            if hasattr(field, 'filter_aliases') and field.filter_aliases:
                if field_name in field.filter_aliases:
                    return field
        
        return None

    def validate_field_value(self, entity_type: str, field_name: str, 
                            value: Any, context: str = 'api') -> bool:
        """
        Validate if a value is valid for a field
        Uses universal options as source of truth
        """
        try:
            # Get valid options for this context
            options = self.get_field_options_universal(
                entity_type, field_name, context
            )
            
            # Extract valid values
            valid_values = [opt['value'] for opt in options]
            
            # Handle empty value for filters
            if context == 'filter' and (value == '' or value is None):
                return True
            
            return value in valid_values
            
        except Exception as e:
            logger.error(f"Error validating field value: {str(e)}")
            return False

# =============================================================================
# GLOBAL INSTANCE AND CONVENIENCE FUNCTIONS
# =============================================================================

# Global processor instance
_categorized_processor = CategorizedFilterProcessor()

def get_categorized_filter_processor() -> CategorizedFilterProcessor:
    """Get the global categorized filter processor instance"""
    return _categorized_processor

def process_filters_for_entity(entity_type: str, filters: Dict[str, Any], 
                             query: Query, session: Session, config=None, 
                             model_class: Optional[Type] = None) -> Tuple[Query, Set[str], int]:
    """
    Convenience function for processing filters
    Direct replacement for existing filter processing methods
    Enhanced with optional model_class parameter for consistency
    """
    processor = get_categorized_filter_processor()
    
    # Use provided model_class or get from processor
    if not model_class:
        model_class = processor._get_model_class(entity_type)
        
    if not model_class:
        logger.error(f"Could not get model class for entity type: {entity_type}")
        return query, set(), 0
        
    try:
        return processor.process_entity_filters(
            entity_type=entity_type,
            filters=filters,
            query=query,
            model_class=model_class,    # FIXED: Always provide model_class
            session=session,
            config=config
        )
    except Exception as e:
        logger.error(f"Error in process_filters_for_entity: {str(e)}")
        return query, set(), 0

def organize_filters_by_category(filters: Dict[str, Any], entity_type: str) -> Dict[FilterCategory, Dict]:
    """
    Convenience function for organizing filters by category
    """
    config = get_entity_config(entity_type)
    if not config:
        return {}
    
    return organize_current_filters_by_category(filters, config)