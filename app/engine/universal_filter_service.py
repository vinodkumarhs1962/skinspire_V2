# =============================================================================
# PART 2: UNIFIED FILTER BACKEND SERVICE - COMPLETE SOLUTION
# File: app/services/universal_filter_service.py (NEW FILE)
# =============================================================================

"""
Unified Universal Filter Service - Single Source of Truth
Backend-Heavy Architecture | Configuration-Driven | Entity-Agnostic

CONSOLIDATES:
- Filter dropdown population logic
- Date preset detection and metadata
- Active filter analysis
- Backend data assembly
- Field type handling

REPLACES scattered logic in:
- data_assembler.py (multiple filter methods)
- universal_services.py (hardcoded filter choices)
- universal_entity_search_service.py (incomplete integration)
"""

from typing import Dict, Any, Optional, List, Union
import uuid
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from flask import request, current_app
from flask_login import current_user
from sqlalchemy.orm import Session

from app.services.database_service import get_db_session
from app.config.entity_configurations import get_entity_config, get_entity_filter_config
from app.config.core_definitions import FieldType, EntitySearchConfiguration
from app.engine.categorized_filter_processor import get_categorized_filter_processor
from app.engine.entity_config_manager import EntityConfigManager
from app.models.master import Supplier
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalFilterService:
    """
    Single source of truth for all filter-related backend logic
    Entity-agnostic, configuration-driven, backend-heavy

    Enhanced Universal Filter Service - Integrated with Categorized Filtering
    
    INTEGRATION POINTS:
    1. Provides frontend dropdown data (same as before)
    2. Gets summary card data using categorized filtering (NEW - unified logic)
    3. Organizes filters by category for UI (NEW)
    4. Maintains same public API (backward compatible)
    """
    
    def __init__(self):
        self.cache = {}
        self.categorized_processor = get_categorized_filter_processor()
        self.entity_type = 'filters'
        self.entity_service_registry = {
            'supplier_payments': 'app.services.supplier_service',
            'suppliers': 'app.services.supplier_service',
            'patients': 'app.services.patient_service',
            'medicines': 'app.services.medicine_service'
        }

    # =============================================================================
    # MAIN PUBLIC API - SINGLE ENTRY POINT
    # =============================================================================

    @cache_service_method()
    def get_complete_filter_data(self, entity_type: str, hospital_id: uuid.UUID, 
                                branch_id: Optional[uuid.UUID] = None, 
                                current_filters: Optional[Dict] = None) -> Dict:
        """
        ENHANCED: Get complete filter data using categorized filtering
        
        SAME SIGNATURE as before but now integrates with categorized processor
        This method is called by data_assembler.py for filter forms and summary cards
        """
        try:
            current_filters = current_filters or {}
            config = get_entity_config(entity_type)
            
            if not config:
                return self._get_empty_filter_data()
            
            
            # 1. Get dropdown options for filter forms (same as before)
            backend_data = self.categorized_processor.get_backend_dropdown_data(
                entity_type, hospital_id, branch_id
            )
            
            # 2. Get summary data using categorized filtering (NEW - unified logic)
            summary_data = self._get_unified_summary_data(
                entity_type, current_filters, hospital_id, branch_id, config
            )
            
            # 3. Organize filters by category for UI (NEW)
            categorized_filters = EntityConfigManager.organize_request_filters_by_category(
                current_filters, entity_type
            )
            
            # 4. Get filter metadata
            filter_metadata = self._get_filter_metadata(
                entity_type, current_filters, config
            )
            
            result = {
                'backend_data': backend_data,           # Dropdown options
                'summary_data': summary_data,           # Summary card counts (using unified filtering)
                'categorized_filters': categorized_filters,  # Organized by category
                'filter_metadata': filter_metadata,    # Field configurations
                'active_filter_count': len([k for k, v in current_filters.items() if v]),
                'has_errors': False,
                'error_messages': []
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting filter data for {entity_type}: {str(e)}")
            return self._get_error_filter_data(str(e))

    # =============================================================================
    # UNIFIED SUMMARY DATA - USES CATEGORIZED FILTERING
    # =============================================================================

    def _get_unified_summary_data(self, entity_type: str, filters: Dict, 
                                 hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID], 
                                 config) -> Dict:
        """
        NEW: Get summary data using the same categorized filtering as the main list
        
        This replaces separate summary card filtering logic and ensures:
        ✅ Summary card counts match pagination totals exactly
        ✅ No conflicts between summary and list filtering  
        ✅ Single source of truth for all filtering
        """
        try:          
            if entity_type == 'supplier_payments':
                return self._get_supplier_payment_unified_summary(
                    filters, hospital_id, branch_id, config
                )
            elif entity_type == 'suppliers':
                return self._get_supplier_unified_summary(
                    filters, hospital_id, branch_id, config
                )
            else:
                # Generic implementation for other entities
                return self._get_generic_unified_summary(
                    entity_type, filters, hospital_id, branch_id, config
                )
                
        except Exception as e:
            logger.error(f"❌ Error getting unified summary for {entity_type}: {str(e)}")
            return {}

    def _get_supplier_payment_unified_summary(self, filters: Dict, hospital_id: uuid.UUID, 
                                            branch_id: Optional[uuid.UUID], config) -> Dict:
        """
        ENHANCED: Supplier payment summary using SAME categorized filtering logic as main list
        
        This is the KEY INTEGRATION - uses the same filter processor as the main search
        to ensure summary cards show accurate counts for the filtered data
        """
        try:
            from app.models.transaction import SupplierPayment
            from sqlalchemy import or_, and_, func
            
            # ✅ CONFIGURATION-DRIVEN: Get model class from config
            model_class = self.categorized_processor._get_model_class('supplier_payments')
            if not model_class:
                from app.models.transaction import SupplierPayment  # Fallback
                model_class = SupplierPayment

            # ✅ FIX: Use the same filter extraction as main service
            from app.engine.universal_services import get_universal_service
            service = get_universal_service('supplier_payments')
            
            # Get the processed filters using the same logic as main query
            if hasattr(service, '_extract_filters'):
                processed_filters = service._extract_filters()
            else:
                processed_filters = filters

            with get_db_session() as session:
                # Start with base query (same as main search)
                base_query = session.query(model_class).filter_by(hospital_id=hospital_id)
                
                # Apply branch filter (same as main search)
                if branch_id:
                    base_query = base_query.filter(model_class.branch_id == branch_id)
                
                # Apply categorized filters - SAME LOGIC AS MAIN SEARCH
                filtered_query, applied_filters, filter_count = self.categorized_processor.process_entity_filters(
                    entity_type='supplier_payments',
                    filters=filters,
                    query=base_query,
                    model_class=model_class,      # ✅ FIXED: Add model_class parameter
                    session=session,
                    config=config
                )
                
                # Calculate summary statistics from the SAME filtered query
                total_count = filtered_query.count()
                
                # ✅ CONFIGURATION-DRIVEN: Using existing helper methods
                # Extract status field and values from config using existing pattern
                status_field_name = 'workflow_status'  # Default
                status_mappings = {}

                # Use existing pattern to extract from config 
                if hasattr(config, 'summary_cards') and config.summary_cards:
                    for card in config.summary_cards:
                        card_field = card.get('field')
                        filter_field = card.get('filter_field') 
                        filter_value = card.get('filter_value')
                        
                        # Extract status mappings same way as existing code
                        if (filter_field == 'workflow_status' and 
                            card_field and filter_value and 
                            card_field.endswith('_count')):
                            status_mappings[card_field] = filter_value

                # Use extracted values or fallback to hardcoded (same as existing error handling pattern)
                approved_status = status_mappings.get('approved_count', 'approved')
                pending_status = status_mappings.get('pending_count', 'pending')  
                completed_status = status_mappings.get('completed_count', 'completed')

                # Same calculation logic, just using config values
                approved_count = filtered_query.filter(
                    getattr(model_class, status_field_name) == approved_status
                ).count()

                completed_count = filtered_query.filter(
                    getattr(model_class, status_field_name) == completed_status
                ).count()

                pending_count = filtered_query.filter(
                    getattr(model_class, status_field_name) == pending_status
                ).count()

                # ✅ KEEP EXISTING: Bank transfer logic unchanged for now (can be Step 2)
                bank_transfer_count = filtered_query.filter(
                    or_(
                        SupplierPayment.payment_method == 'bank_transfer',
                        and_(
                            SupplierPayment.payment_method == 'mixed',
                            SupplierPayment.bank_transfer_amount > 0
                        )
                    )
                ).count()
                
                # Calculate total amount from filtered results
                total_amount_result = filtered_query.with_entities(
                    func.sum(getattr(model_class, 'amount'))
                ).scalar()
                total_amount = float(total_amount_result or 0)
                
                # ✅ FINAL FIX: Calculate this month data separately (truly unfiltered for non-filterable cards)
                current_month = date.today().month
                current_year = date.today().year

                # For non-filterable cards, use PURE base query with ONLY date filter
                this_month_query = base_query.filter(
                    func.extract('month', getattr(model_class, 'payment_date')) == current_month,
                    func.extract('year', getattr(model_class, 'payment_date')) == current_year
                )

                # ✅ NO OTHER FILTERS: Since these cards are configured as filterable=False
                # They should show ALL this month data regardless of status, supplier, reference, etc.

                this_month_count = this_month_query.count()
                this_month_amount_result = this_month_query.with_entities(func.sum(SupplierPayment.amount)).scalar()
                this_month_amount = float(this_month_amount_result or 0)

                summary = {
                    'total_count': total_count,
                    'total_amount': total_amount,
                    'pending_count': pending_count,
                    'approved_count': approved_count,
                    'completed_count': completed_count,
                    'bank_transfer_count': bank_transfer_count,
                    'this_month_count': this_month_count,     
                    'this_month_amount': this_month_amount,    
                    'applied_filters': list(applied_filters),
                    'filter_count': filter_count,
                    'filtering_method': 'categorized_unified'
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"❌ Error calculating unified supplier payment summary: {str(e)}")
            # ✅ CONFIGURATION-DRIVEN: Use same config extraction for error case
            error_defaults = {'approved_count': 0, 'completed_count': 0, 'pending_count': 0}

            # Extract from config for consistency (reuse same pattern)
            if hasattr(config, 'summary_cards') and config.summary_cards:
                for card in config.summary_cards:
                    card_field = card.get('field')
                    if card_field and card_field.endswith('_count'):
                        error_defaults[card_field] = 0

            # Build error response using config
            error_response = {
                'total_count': 0,
                'total_amount': 0,
                'bank_transfer_count': 0
            }
            error_response.update(error_defaults)

            return error_response

    def _get_supplier_unified_summary(self, filters: Dict, hospital_id: uuid.UUID, 
                                    branch_id: Optional[uuid.UUID], config) -> Dict:
        """
        TEMPLATE: Unified summary for suppliers (extensible pattern)
        """
        try:
            from app.models.master import Supplier
            
            with get_db_session() as session:
                base_query = session.query(Supplier).filter_by(hospital_id=hospital_id)
                
                # ✅ FIX: Apply branch filter if provided (same as main query)
                if branch_id:
                    base_query = base_query.filter(Supplier.branch_id == branch_id)

                # Apply categorized filters
                filtered_query, applied_filters, filter_count = self.categorized_processor.process_entity_filters(
                    entity_type='suppliers',
                    filters=filters,
                    query=base_query,
                    model_class=Supplier,         # ✅ FIXED: Add model_class parameter
                    session=session,
                    config=config
                )
                
                total_count = filtered_query.count()
                active_count = filtered_query.filter(Supplier.status == 'active').count()
                
                return {
                    'total_count': total_count,
                    'active_count': active_count,
                    'applied_filters': list(applied_filters),
                    'filter_count': filter_count
                }
                
        except Exception as e:
            logger.error(f"❌ Error calculating supplier summary: {str(e)}")
            return {'total_count': 0, 'active_count': 0}

    def _get_generic_unified_summary(self, entity_type: str, filters: Dict, 
                                   hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID], 
                                   config) -> Dict:
        """
        GENERIC: Unified summary for any entity type (extensible pattern)
        """
        try:
            # This would use the categorized processor for any entity
            # For now, return basic count
            return {
                'total_count': 0,
                'applied_filters': [],
                'filter_count': 0,
                'message': f'Generic summary for {entity_type} - implement specific logic'
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating generic summary for {entity_type}: {str(e)}")
            return {'total_count': 0}

    
    def _get_filter_metadata(self, entity_type: str, current_filters: Dict, config) -> Dict:
        """
        NEW: Get filter metadata for enhanced UI functionality
        """
        try:
            metadata = {
                'date_presets': [
                    {'value': 'current_financial_year', 'label': 'Current Financial Year'},
                    {'value': 'last_financial_year', 'label': 'Last Financial Year'},
                    {'value': 'current_month', 'label': 'Current Month'},
                    {'value': 'last_month', 'label': 'Last Month'},
                    {'value': 'last_7_days', 'label': 'Last 7 Days'},
                    {'value': 'last_30_days', 'label': 'Last 30 Days'}
                ],
                'currency_symbol': '₹',
                'default_financial_year': 'current'
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Error getting filter metadata: {str(e)}")
            return {}

    # =============================================================================
    # HELPER METHODS - PRESERVED
    # =============================================================================

    def _get_empty_filter_data(self) -> Dict:
        """Empty filter data structure"""
        return {
            'backend_data': {},
            'summary_data': {},
            'categorized_filters': {},
            'filter_metadata': {},
            'active_filter_count': 0,
            'has_errors': False,
            'error_messages': []
        }

    def _get_error_filter_data(self, error_message: str) -> Dict:
        """Error filter data structure"""
        return {
            'backend_data': {},
            'summary_data': {},
            'categorized_filters': {},
            'filter_metadata': {},
            'active_filter_count': 0,
            'has_errors': True,
            'error_messages': [error_message]
        }


    # =============================================================================
    # FILTER GROUP BUILDING - ENTITY AGNOSTIC
    # =============================================================================

    def _build_filter_groups(self, config, current_filters: Dict, 
                           hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> List[Dict]:
        """Build filter groups from configuration"""
        try:
            filterable_fields = [f for f in config.fields if getattr(f, 'filterable', False)]
            
            if not filterable_fields:
                return []
            
            # Get backend data for all fields
            backend_data = self.categorized_processor.get_backend_dropdown_data(
                config.entity_type, hospital_id, branch_id
            )
            
            # Separate date fields from others
            date_fields = [f for f in filterable_fields if self._get_field_type_safe(f) == 'date']
            other_fields = [f for f in filterable_fields if self._get_field_type_safe(f) != 'date']
            
            groups = []
            
            # Date fields group (if any)
            if date_fields:
                date_group = {
                    'label': 'Date Range',
                    'type': 'date_range',
                    'fields': [self._build_field_data(field, current_filters, backend_data) 
                              for field in date_fields]
                }
                groups.append(date_group)
            
            # Other fields in groups of 3
            if other_fields:
                current_group = {'label': 'Filters', 'type': 'standard', 'fields': []}
                
                for field in other_fields:
                    field_data = self._build_field_data(field, current_filters, backend_data)
                    current_group['fields'].append(field_data)
                    
                    # Start new group every 3 fields
                    if len(current_group['fields']) >= 3:
                        groups.append(current_group)
                        current_group = {'label': 'Filters', 'type': 'standard', 'fields': []}
                
                # Add remaining fields
                if current_group['fields']:
                    groups.append(current_group)
            
            return groups
            
        except Exception as e:
            logger.error(f"Error building filter groups: {str(e)}")
            return []

    def _build_field_data(self, field, current_filters: Dict, backend_data: Dict) -> Dict:
        """Build comprehensive field data for frontend"""
        try:
            field_type = self._get_field_type_safe(field)
            current_value = current_filters.get(field.name, '')
            
            # Base field data
            field_data = {
                'name': field.name,
                'label': field.label,
                'type': field_type,
                'value': current_value,
                'placeholder': getattr(field, 'placeholder', '') or f"Filter by {field.label}...",
                'required': getattr(field, 'required', False),
                'has_value': bool(current_value),
                'css_classes': 'universal-filter-auto-submit'
            }
            
            # Type-specific enhancements
            if field_type == 'date':
                field_data.update(self._enhance_date_field(field, current_value))
                
            elif field_type == 'select':
                field_data.update(self._enhance_select_field(field, current_value, backend_data))
                
            elif field_type == 'entity_search':
                field_data.update(self._enhance_entity_search_field(field, current_value, backend_data))
            
            return field_data
            
        except Exception as e:
            logger.error(f"Error building field data for {field.name}: {str(e)}")
            return self._get_fallback_field_data(field)

    # =============================================================================
    # FIELD TYPE SPECIFIC ENHANCEMENTS
    # =============================================================================

    def _enhance_date_field(self, field, current_value: str) -> Dict:
        """Enhance date field with preset support"""
        # DIRECT CALL: Use categorized processor directly
        preset_choices = self.categorized_processor.get_date_preset_choices()
        
        # Convert to dict format for compatibility
        preset_options = [
            {'value': value, 'label': label, 'icon': 'fas fa-calendar'}
            for value, label in preset_choices
        ]
        
        return {
            'supports_presets': True,
            'preset_options': preset_options,  # Direct use
            'active_preset': self._detect_single_field_preset(field.name, current_value),
            'financial_year_aware': True
        }

    def _enhance_select_field(self, field, current_value: str, backend_data: Dict) -> Dict:
        """Enhance select field with options"""
        options = backend_data.get(field.name, [])
        
        # Fallback to field configuration
        if not options and hasattr(field, 'options'):
            options = field.options
        
        # Ensure proper format
        formatted_options = self._format_select_options(options)
        
        return {
            'options': [{'value': '', 'label': f'All {field.label}'}] + formatted_options,
            'selected_text': self._get_selected_option_text(formatted_options, current_value),
            'has_options': len(formatted_options) > 0
        }

    def _enhance_entity_search_field(self, field, current_value: str, backend_data: Dict) -> Dict:
        """Enhance entity search field"""
        return {
            'entity_type': getattr(field, 'entity_search_config', {}).get('target_entity', 'suppliers'),
            'search_url': '/universal/api/entity-search',
            'min_chars': 2,
            'display_value': self._get_entity_display_value(field, current_value, backend_data)
        }

    
    def _get_entity_specific_backend_data(self, entity_type: str, 
                                    hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> Dict:
        """Get entity-specific backend data using service delegation"""
        try:
            if entity_type == 'supplier_payments':
                # DIRECT CALL: Use categorized processor directly
                return self.categorized_processor.get_backend_dropdown_data(
                    entity_type, hospital_id, branch_id
                )
            elif entity_type == 'suppliers':
                return self._get_supplier_backend_data(hospital_id, branch_id)
            # Add more entities as needed
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting entity-specific data for {entity_type}: {str(e)}")
            return {}

    

    # =============================================================================
    # DATE PRESET ANALYSIS
    # =============================================================================

    def _analyze_date_presets(self, current_filters: Dict) -> Dict:
        """Analyze current date filters and detect active presets"""
        try:
            start_date = current_filters.get('start_date')
            end_date = current_filters.get('end_date')
            
            # DIRECT CALL: Use categorized processor directly
            preset_options = self.categorized_processor.get_date_preset_choices()
            
            # Convert to dict format for compatibility
            formatted_options = [
                {'value': value, 'label': label, 'icon': 'fas fa-calendar'}
                for value, label in preset_options
            ]
            
            preset_data = {
                'active_preset': 'none',
                'preset_options': formatted_options,  # Direct use
                'start_date': start_date,
                'end_date': end_date,
                'has_dates': bool(start_date or end_date),
                'is_date_range': bool(start_date and end_date),
                'financial_year_info': self._get_financial_year_info()
            }
            
            if start_date and end_date:
                preset_data['active_preset'] = self._detect_active_preset(start_date, end_date)
            
            return preset_data
            
        except Exception as e:
            logger.error(f"Error analyzing date presets: {str(e)}")
            return {'active_preset': 'none', 'has_dates': False}

    def _detect_active_preset(self, start_date: str, end_date: str) -> str:
        """Detect which preset matches the current date range"""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            today = date.today()
            
            # Today
            if start == end == today:
                return 'today'
            
            # This month
            month_start = date(today.year, today.month, 1)
            if start == month_start and end == today:
                return 'this_month'
            
            # Financial year
            fy_start, fy_end = self._get_financial_year_dates(today)
            if start == fy_start and end <= fy_end:
                return 'financial_year'
            
            # Last 30 days
            thirty_days_ago = today - timedelta(days=30)
            if start == thirty_days_ago and end == today:
                return 'last_30_days'
            
            return 'custom'
            
        except Exception as e:
            logger.error(f"Error detecting active preset: {str(e)}")
            return 'custom'

    def _get_financial_year_dates(self, reference_date: date) -> tuple:
        """Get financial year start and end dates"""
        year = reference_date.year
        
        if reference_date.month >= 4:  # April onwards
            fy_start = date(year, 4, 1)
            fy_end = date(year + 1, 3, 31)
        else:  # January to March
            fy_start = date(year - 1, 4, 1)
            fy_end = date(year, 3, 31)
        
        return fy_start, fy_end

    
    # =============================================================================
    # ACTIVE FILTER ANALYSIS
    # =============================================================================

    def _analyze_active_filters(self, current_filters: Dict, config) -> List[Dict]:
        """Analyze active filters and format for display"""
        try:
            skip_fields = ['page', 'per_page', 'sort', 'direction']
            active_filters = []
            
            for key, value in current_filters.items():
                if not value or key in skip_fields:
                    continue
                
                # Find field configuration
                field_config = self._find_field_config(key, config)
                
                filter_info = {
                    'key': key,
                    'raw_value': value,
                    'display_value': self._format_filter_display_value(value, field_config),
                    'label': self._format_field_label(key, field_config),
                    'field_type': self._get_field_type_safe(field_config) if field_config else 'text',
                    'removable': True
                }
                
                active_filters.append(filter_info)
            
            return active_filters
            
        except Exception as e:
            logger.error(f"Error analyzing active filters: {str(e)}")
            return []

    def _format_filter_display_value(self, value: str, field_config) -> str:
        """Format filter value for display"""
        try:
            if not field_config:
                return str(value)
            
            field_type = self._get_field_type_safe(field_config)
            
            if field_type == 'date':
                try:
                    date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                    return date_obj.strftime('%b %d, %Y')
                except:
                    return value
            
            elif field_type == 'select' and hasattr(field_config, 'options'):
                for option in field_config.options:
                    if option.get('value') == value:
                        return option.get('label', value)
            
            return str(value)
            
        except Exception as e:
            logger.error(f"Error formatting display value: {str(e)}")
            return str(value)

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def _get_field_type_safe(self, field) -> str:
        """Safely get field type as string"""
        try:
            if not field:
                return 'text'
            
            if hasattr(field, 'field_type'):
                if hasattr(field.field_type, 'value'):
                    return field.field_type.value.lower()
                elif hasattr(field.field_type, 'name'):
                    return field.field_type.name.lower()
                else:
                    return str(field.field_type).lower().replace('fieldtype.', '')
            
            return 'text'
            
        except Exception as e:
            logger.error(f"Error getting field type: {str(e)}")
            return 'text'

    def _format_select_options(self, options: List) -> List[Dict]:
        """Format options to consistent structure"""
        formatted = []
        
        for option in options:
            if isinstance(option, dict):
                formatted.append({
                    'value': str(option.get('value', '')),
                    'label': str(option.get('label', option.get('value', '')))
                })
            else:
                formatted.append({
                    'value': str(option),
                    'label': str(option)
                })
        
        return formatted

    def _count_active_filters(self, current_filters: Dict) -> int:
        """Count active filters excluding pagination"""
        skip_fields = ['page', 'per_page', 'sort', 'direction']
        return len([k for k, v in current_filters.items() 
                   if v and k not in skip_fields])

    def _has_date_fields(self, config) -> bool:
        """Check if entity has any date fields"""
        return any(self._get_field_type_safe(f) == 'date' 
                  for f in config.fields if getattr(f, 'filterable', False))

    def _find_field_config(self, field_name: str, config):
        """Find field configuration by name"""
        for field in config.fields:
            if field.name == field_name:
                return field
        return None

    def _format_field_label(self, field_name: str, field_config) -> str:
        """Format field name for display"""
        if field_config and hasattr(field_config, 'label'):
            return field_config.label
        
        return field_name.replace('_', ' ').title()

    def _get_fallback_field_data(self, field) -> Dict:
        """Get safe fallback field data"""
        return {
            'name': getattr(field, 'name', 'unknown'),
            'label': getattr(field, 'label', 'Unknown Field'),
            'type': 'text',
            'value': '',
            'placeholder': 'Filter...',
            'required': False,
            'has_value': False,
            'css_classes': 'universal-filter-auto-submit'
        }

    def _get_error_fallback_filter_data(self, entity_type: str, error: str) -> Dict:
        """Get safe fallback data when errors occur"""
        return {
            'groups': [],
            'backend_data': {},
            'date_preset_data': {'active_preset': 'none', 'has_dates': False},
            'active_filters': [],
            'active_filters_count': 0,
            'entity_metadata': {'entity_type': entity_type},
            'field_configs': {},
            'has_errors': True,
            'error_messages': [error]
        }

    def _get_financial_year_info(self) -> Dict:
        """Get current financial year information"""
        today = date.today()
        fy_start, fy_end = self._get_financial_year_dates(today)
        
        return {
            'current_fy_start': fy_start.isoformat(),
            'current_fy_end': fy_end.isoformat(),
            'fy_label': f"FY {fy_start.year}-{fy_end.year}",
            'start_month': 4  # April
        }
    def _get_entity_search_options(self, field, hospital_id: uuid.UUID, 
                              branch_id: Optional[uuid.UUID]) -> List[Dict]:
        """Get entity search options for filter fields"""
        try:
            # Extract entity search configuration
            if hasattr(field, 'entity_search_config'):
                config = field.entity_search_config
            else:
                # Fallback for fields with search configuration
                config = getattr(field, 'search_config', None)
            
            if not config:
                logger.warning(f"No entity search config found for field {field.name}")
                return []
            
            # Get target entity type
            target_entity = getattr(config, 'target_entity', 'suppliers')
            
            # Use existing entity search service
            try:
                from app.engine.universal_entity_search_service import UniversalEntitySearchService
                search_service = UniversalEntitySearchService()
            except ImportError:
                logger.warning("UniversalEntitySearchService not available, returning empty options")
                return []
            
            # Get recent/popular options (limit to 10 for filter dropdown)
            results = search_service.search_entities(
                config=config,
                search_term="",  # Empty search to get recent items
                hospital_id=hospital_id,
                branch_id=branch_id
            )
            
            return results[:10]  # Limit for filter dropdown
            
        except Exception as e:
            logger.error(f"Error getting entity search options for {field.name}: {str(e)}")
            return []

    def _detect_single_field_preset(self, field_name: str, current_value: str) -> str:
        """Detect which date preset is currently active for a single field"""
        try:
            if not current_value:
                return 'none'
            
            today = date.today()
            
            # Parse the current value
            try:
                current_date = datetime.strptime(current_value, '%Y-%m-%d').date()
            except ValueError:
                return 'none'
            
            # Check common presets
            if current_date == today:
                return 'today'
            elif current_date == today - timedelta(days=1):
                return 'yesterday'
            elif current_date == today - timedelta(days=7):
                return 'last_week'
            elif current_date == today - timedelta(days=30):
                return 'last_month'
            
            # Check financial year
            fy_start, fy_end = self._get_financial_year_dates(today)
            if current_date == fy_start:
                return 'fy_start'
            elif current_date == fy_end:
                return 'fy_end'
            
            # Check calendar year
            if current_date == date(today.year, 1, 1):
                return 'year_start'
            elif current_date == date(today.year, 12, 31):
                return 'year_end'
            
            return 'custom'
            
        except Exception as e:
            logger.error(f"Error detecting preset for {field_name}: {str(e)}")
            return 'none'

    def _get_selected_option_text(self, options: List[Dict], selected_value: str) -> str:
        """Get display text for selected option value"""
        try:
            if not selected_value or not options:
                return ""
            
            # Find matching option
            for option in options:
                if isinstance(option, dict):
                    if str(option.get('value', '')) == str(selected_value):
                        return option.get('label', selected_value)
                else:
                    if str(option) == str(selected_value):
                        return str(option)
            
            # If no match found, return the value itself
            return selected_value
            
        except Exception as e:
            logger.error(f"Error getting selected option text: {str(e)}")
            return selected_value

    def _build_field_configs(self, config, current_filters: Dict, backend_data: Dict) -> Dict:
        """Build field configurations for the filter form"""
        try:
            field_configs = {}
            
            for field in config.fields:
                if not getattr(field, 'filterable', False):
                    continue
                
                field_name = field.name
                current_value = current_filters.get(field_name, '')
                field_type = self._get_field_type_safe(field)
                
                # Build base field config
                field_config = {
                    'name': field_name,
                    'label': getattr(field, 'label', field_name.replace('_', ' ').title()),
                    'type': field_type,
                    'value': current_value,
                    'placeholder': getattr(field, 'placeholder', f'Filter by {field.label}'),
                    'required': getattr(field, 'required', False),
                    'has_value': bool(current_value),
                    'css_classes': 'universal-filter-auto-submit'
                }
                
                # Enhance based on field type
                if field_type == 'date':
                    field_config.update(self._enhance_date_field(field, current_value))
                elif field_type == 'select':
                    field_config.update(self._enhance_select_field(field, current_value, backend_data))
                elif field_type == 'entity_search':
                    field_config.update(self._enhance_entity_search_field(field, current_value, backend_data))
                
                field_configs[field_name] = field_config
            
            return field_configs
            
        except Exception as e:
            logger.error(f"Error building field configs: {str(e)}")
            return {}
        
    def _get_entity_display_value(self, field, current_value: str, backend_data: Dict) -> str:
        """Get display value for entity search field"""
        try:
            if not current_value:
                return ""
            
            # Try to get display value from backend data first
            field_backend_data = backend_data.get(field.name, [])
            if field_backend_data:
                for item in field_backend_data:
                    if isinstance(item, dict) and str(item.get('value', '')) == str(current_value):
                        return item.get('label', current_value)
            
            # Try to get from entity search config
            if hasattr(field, 'entity_search_config') and field.entity_search_config:
                config = field.entity_search_config
                if hasattr(config, 'display_template'):
                    return str(current_value)
            
            # Fallback to value itself
            return str(current_value) if current_value else ""
            
        except Exception as e:
            logger.error(f"Error getting entity display value for {field.name}: {str(e)}")
            return str(current_value) if current_value else ""

# =============================================================================
# GLOBAL SERVICE INSTANCE
# =============================================================================

# Global instance for easy access
universal_filter_service = UniversalFilterService()

def get_universal_filter_service() -> UniversalFilterService:
    """Get the global universal filter service instance"""
    return universal_filter_service


