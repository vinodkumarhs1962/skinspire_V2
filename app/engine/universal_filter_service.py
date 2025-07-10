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
from app.config.field_definitions import FieldType, EntitySearchConfiguration
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalFilterService:
    """
    Single source of truth for all filter-related backend logic
    Entity-agnostic, configuration-driven, backend-heavy
    """
    
    def __init__(self):
        self.cache = {}
        self.entity_service_registry = {
            'supplier_payments': 'app.services.supplier_service',
            'suppliers': 'app.services.supplier_service',
            'patients': 'app.services.patient_service',
            'medicines': 'app.services.medicine_service'
        }

    # =============================================================================
    # MAIN PUBLIC API - SINGLE ENTRY POINT
    # =============================================================================

    def get_complete_filter_data(self, entity_type: str, hospital_id: uuid.UUID, 
                                branch_id: Optional[uuid.UUID] = None, 
                                current_filters: Optional[Dict] = None) -> Dict:
        """Get complete filter data for any entity"""
        try:
            current_filters = current_filters or {}
            config = get_entity_config(entity_type)
            
            if not config:
                return {
                    'groups': [],
                    'backend_data': {},
                    'active_filters': [],
                    'active_filters_count': 0,
                    'has_errors': True,
                    'error_messages': [f'No config for {entity_type}']
                }
            
            # Build all components separately first
            backend_data = self._get_unified_backend_data(config, hospital_id, branch_id) or {}
            groups = self._build_filter_groups(config, current_filters, hospital_id, branch_id) or []
            
            # Return complete data
            return {
                'groups': groups,
                'backend_data': backend_data,
                'active_filters': [],
                'active_filters_count': 0,
                'entity_metadata': {'entity_type': entity_type},
                'field_configs': {},
                'has_errors': False,
                'error_messages': []
            }
            
        except Exception as e:
            logger.error(f"Error in get_complete_filter_data: {str(e)}")
            return {
                'groups': [],
                'backend_data': {},
                'active_filters': [],
                'active_filters_count': 0,
                'has_errors': True,
                'error_messages': [str(e)]
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
            backend_data = self._get_unified_backend_data(config, hospital_id, branch_id)
            
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
        return {
            'supports_presets': True,
            'preset_options': self._get_date_preset_options(),
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

    # =============================================================================
    # UNIFIED BACKEND DATA RETRIEVAL
    # =============================================================================

    def _get_unified_backend_data(self, config, hospital_id: uuid.UUID, 
                                 branch_id: Optional[uuid.UUID]) -> Dict:
        """
        Single method to get all backend data for filter dropdowns
        Consolidates all scattered logic into one place
        """
        try:
            cache_key = f"{config.entity_type}_{hospital_id}_{branch_id}"
            
            # Check cache first
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            backend_data = {}
            
            # Process each filterable field
            for field in config.fields:
                if not getattr(field, 'filterable', False):
                    continue
                
                field_type = self._get_field_type_safe(field)
                
                if field_type == 'select':
                    backend_data[field.name] = self._get_select_field_options(
                        field, config.entity_type, hospital_id, branch_id)
                
                elif field_type == 'entity_search':
                    backend_data[field.name] = self._get_entity_search_options(
                        field, hospital_id, branch_id)
            
            # Add entity-specific backend data
            entity_specific_data = self._get_entity_specific_backend_data(
                config.entity_type, hospital_id, branch_id)
            backend_data.update(entity_specific_data)
            
            # Cache result
            self.cache[cache_key] = backend_data
            
            logger.debug(f"✅ Built unified backend data for {config.entity_type}: "
                        f"{list(backend_data.keys())}")
            
            return backend_data
            
        except Exception as e:
            logger.error(f"Error getting unified backend data: {str(e)}")
            return {}

    def _get_select_field_options(self, field, entity_type: str, 
                                 hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> List[Dict]:
        """Get options for select fields"""
        try:
            # First try field configuration
            if hasattr(field, 'options') and field.options:
                return self._format_select_options(field.options)
            
            # Then try entity filter configuration
            filter_config = get_entity_filter_config(entity_type)
            if filter_config and field.name in filter_config.filter_mappings:
                options = filter_config.filter_mappings[field.name].get('options', [])
                return self._format_select_options(options)
            
            # Fallback to pattern-based options
            return self._get_pattern_based_options(field.name)
            
        except Exception as e:
            logger.error(f"Error getting select options for {field.name}: {str(e)}")
            return []

    def _get_pattern_based_options(self, field_name: str) -> List[Dict]:
        """Get options based on field name patterns"""
        pattern_options = {
            'status': [
                {'value': 'active', 'label': 'Active'},
                {'value': 'inactive', 'label': 'Inactive'},
                {'value': 'pending', 'label': 'Pending'}
            ],
            'payment_method': [
                {'value': 'cash', 'label': 'Cash'},
                {'value': 'cheque', 'label': 'Cheque'},
                {'value': 'bank_transfer', 'label': 'Bank Transfer'},
                {'value': 'upi', 'label': 'UPI'}
            ],
            'workflow_status': [
                {'value': 'pending', 'label': 'Pending'},
                {'value': 'approved', 'label': 'Approved'},
                {'value': 'completed', 'label': 'Completed'},
                {'value': 'rejected', 'label': 'Rejected'}
            ]
        }
        
        for pattern, options in pattern_options.items():
            if pattern in field_name.lower():
                return options
        
        return []

    def _get_entity_specific_backend_data(self, entity_type: str, 
                                        hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> Dict:
        """Get entity-specific backend data using service delegation"""
        try:
            if entity_type == 'supplier_payments':
                return self._get_supplier_payment_backend_data(hospital_id, branch_id)
            elif entity_type == 'suppliers':
                return self._get_supplier_backend_data(hospital_id, branch_id)
            # Add more entities as needed
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting entity-specific data for {entity_type}: {str(e)}")
            return {}

    def _get_supplier_payment_backend_data(self, hospital_id: uuid.UUID, 
                                         branch_id: Optional[uuid.UUID]) -> Dict:
        """Get supplier payment specific backend data"""
        try:
            from app.services.supplier_service import get_suppliers_for_choice
            
            backend_data = {}
            
            # Get suppliers for dropdown
            suppliers_result = get_suppliers_for_choice(hospital_id)
            if suppliers_result.get('success') and suppliers_result.get('suppliers'):
                suppliers = [
                    {
                        'value': str(supplier.supplier_id),
                        'label': supplier.supplier_name
                    }
                    for supplier in suppliers_result['suppliers']
                ]
                backend_data['supplier_id'] = suppliers
            
            return backend_data
            
        except Exception as e:
            logger.error(f"Error getting supplier payment backend data: {str(e)}")
            return {}

    # =============================================================================
    # DATE PRESET ANALYSIS
    # =============================================================================

    def _analyze_date_presets(self, current_filters: Dict) -> Dict:
        """Analyze current date filters and detect active presets"""
        try:
            start_date = current_filters.get('start_date')
            end_date = current_filters.get('end_date')
            
            preset_data = {
                'active_preset': 'none',
                'preset_options': self._get_date_preset_options(),
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

    def _get_date_preset_options(self) -> List[Dict]:
        """Get available date preset options"""
        return [
            {'value': 'today', 'label': 'Today', 'icon': 'fas fa-calendar-day'},
            {'value': 'this_week', 'label': 'This Week', 'icon': 'fas fa-calendar-week'},
            {'value': 'this_month', 'label': 'This Month', 'icon': 'fas fa-calendar-alt'},
            {'value': 'last_30_days', 'label': 'Last 30 Days', 'icon': 'fas fa-calendar-minus'},
            {'value': 'financial_year', 'label': 'Financial Year', 'icon': 'fas fa-calendar-year'},
            {'value': 'clear', 'label': 'Clear', 'icon': 'fas fa-times'}
        ]

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