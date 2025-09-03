# =============================================================================
# SAFER DATA ASSEMBLER MIGRATION - WITH COMPATIBILITY WRAPPERS
# File: app/engine/data_assembler.py (SAFER REPLACEMENT)
# =============================================================================

"""
Enhanced Universal Data Assembler - Cleaned with Compatibility Wrappers
Uses new UniversalFilterService but maintains backward compatibility

SAFER APPROACH:
- Keeps old method signatures as compatibility wrappers
- Gradually deprecates old methods
- Allows for gradual migration of calling code
- Zero breaking changes during transition
"""

from typing import Dict, Any, Optional, List, Union
import uuid
from datetime import datetime, date
from flask import request, url_for, current_app
from flask_login import current_user
from flask_wtf import FlaskForm

from app.config.core_definitions import EntityConfiguration, FieldDefinition, ActionDisplayType, ButtonType, ActionDefinition
from app.engine.universal_service_cache import cache_service_method
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class EnhancedUniversalDataAssembler:
    """
    Enhanced data assembler with UniversalFilterService integration
    Maintains backward compatibility during transition
    """
    
    def __init__(self):
        # Lazy import to avoid circular dependencies
        self._filter_service = None
    
    @property
    def filter_service(self):
        """Lazy load filter service"""
        if self._filter_service is None:
            from app.engine.universal_filter_service import get_universal_filter_service
            self._filter_service = get_universal_filter_service()
        return self._filter_service

    # =============================================================================
    # MAIN ASSEMBLY METHOD - UPDATED TO USE UNIVERSAL FILTER SERVICE
    # =============================================================================

    def assemble_complex_list_data(self, config: EntityConfiguration, raw_data: Dict, 
                              form_instance: Optional[FlaskForm] = None,
                              filters: Optional[Dict] = None,
                              branch_context: Optional[Dict] = None) -> Dict:
        """
        MODIFIED: Now uses filter processor's template method
        """
        try:
            # Get current filters
            if raw_data.get('request_args'):
                current_filters = raw_data['request_args']
            elif filters:
                current_filters = filters  
            else:
                current_filters = request.args.to_dict() if request else {}
            
            # Get branch context
            if not branch_context and current_user:
                try:
                    from app.utils.context_helpers import get_branch_uuid_from_context_or_request
                    branch_uuid, branch_name = get_branch_uuid_from_context_or_request()
                    branch_context = {'branch_id': branch_uuid, 'branch_name': branch_name}
                except Exception as e:
                    logger.warning(f"Could not get branch context: {str(e)}")
                    branch_context = {}
            
            # Clean branch context for template
            branch_context = self._clean_branch_context_for_template(branch_context)
            
            # ✅ NEW: Get filter fields from processor
            hospital_id = current_user.hospital_id if current_user else None
            branch_id = branch_context.get('branch_id') if branch_context else None
            
            # Initialize filter processor if not already done
            if not hasattr(self, 'filter_processor'):
                from app.engine.categorized_filter_processor import get_categorized_filter_processor
                self.filter_processor = get_categorized_filter_processor()
            
            # Get template-ready filter fields
            filter_fields = self.filter_processor.get_template_filter_fields(
                entity_type=config.entity_type,
                hospital_id=hospital_id,
                branch_id=branch_id
            )
            
            # Prepare template-safe config
            template_safe_config = self._make_template_safe_config(config)
            
            # Get total count
            total_count = raw_data.get('total', len(raw_data.get('items', [])))
            
            assembled_data = {
                # Core data
                'items': raw_data.get('items', []),
                'total_count': total_count,
                
                # Configuration
                'entity_config': template_safe_config,
                'entity_type': config.entity_type,
                
                # ✅ NEW: Filter fields from processor
                'filter_fields': filter_fields,
                'filters': current_filters,
                
                # Keep existing filter_data for backward compatibility
                'filter_data': {
                    'groups': [],
                    'backend_data': {},
                    'active_filters_count': len([k for k, v in current_filters.items() 
                                                if v and k not in ['page', 'per_page']]),
                    'has_filters': len(filter_fields) > 0
                },
                
                # Table structure
                'table_columns': self._assemble_table_columns(config),
                'table_data': self._assemble_table_data(config, raw_data.get('items', [])),
                
                # Summary cards
                'summary_cards': self._assemble_summary_cards(config, raw_data),
                
                # Summary and pagination
                'summary': self._assemble_summary_data(config, raw_data),
                'pagination': self._assemble_pagination_data(raw_data, current_filters),
                
                # Context
                'branch_context': branch_context or {},
                'current_url': request.url if request else '',
                'base_url': request.base_url if request else '',
                
                # Form data
                'form_instance': form_instance,
                
                # Status
                'has_data': len(raw_data.get('items', [])) > 0,
                'has_errors': False,
                'error_messages': []
            }
            
            return assembled_data
            
        except Exception as e:
            logger.error(f"Error assembling list data: {str(e)}")
            return self._get_error_fallback_data(config, str(e))

    def _clean_branch_context_for_template(self, raw_branch_context) -> Dict:
        """Clean branch context for template display"""
        if not raw_branch_context:
            return {}
        
        try:
            clean_context = {}
            
            # Handle different branch context formats
            if isinstance(raw_branch_context, dict):
                # Standard format
                if 'branch_name' in raw_branch_context:
                    clean_context['branch_name'] = raw_branch_context['branch_name']
                
                # Permission service format
                if 'assigned_branch_id' in raw_branch_context:
                    branch_id = raw_branch_context['assigned_branch_id']
                    if branch_id:
                        # Look up branch name using existing branch service
                        branch_name = self._get_branch_name_from_service(branch_id)
                        
                        if branch_name:
                            clean_context['branch_name'] = branch_name
                        else:
                            # Fallback to truncated ID if lookup fails
                            clean_context['branch_display'] = f"Branch {branch_id[:8]}..."
                        clean_context['branch_id'] = branch_id
                
                # Multi-branch indicators
                if raw_branch_context.get('is_multi_branch_user'):
                    clean_context['is_multi_branch'] = True
                    if raw_branch_context.get('can_cross_branch'):
                        clean_context['branch_display'] = "Multi-Branch Access"
                    
                # CRITICAL FIX: Ensure raw context is never passed through
                if not clean_context:
                    # If no clean data could be extracted, return empty context
                    logger.warning(f"Could not clean branch context: {raw_branch_context}")
                    return {}
            
            return clean_context
            
        except Exception as e:
            logger.error(f"Error cleaning branch context: {str(e)}")
            return {}

    def _get_branch_name_from_service(self, branch_id: str) -> Optional[str]:
        """Look up branch name using existing branch service"""
        try:
            from app.services.branch_service import get_hospital_branches
            from flask_login import current_user
            
            if not current_user or not hasattr(current_user, 'hospital_id'):
                return None
                
            # Get all branches for the hospital
            branches = get_hospital_branches(current_user.hospital_id)
            
            # Find the specific branch by ID
            for branch in branches:
                if branch.get('branch_id') == str(branch_id):
                    return branch.get('name')
            
            logger.warning(f"Branch not found in hospital branches: {branch_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error looking up branch name using service: {str(e)}")
            return None
        
    # =============================================================================
    # BACKWARD COMPATIBILITY WRAPPERS - DEPRECATED BUT FUNCTIONAL
    # =============================================================================

    def _assemble_enhanced_filter_form(self, config: EntityConfiguration, current_filters: Dict) -> Dict:
        """
        🔄 COMPATIBILITY WRAPPER: Old method signature maintained
        DEPRECATED: Use filter_service.get_complete_filter_data() instead
        """
        logger.warning(f"DEPRECATED: _assemble_enhanced_filter_form called for {config.entity_type}. "
                      f"Use UniversalFilterService.get_complete_filter_data() instead.")
        
        try:
            # Try new method first
            filter_data = self.filter_service.get_complete_filter_data(
                entity_type=config.entity_type,
                hospital_id=current_user.hospital_id if current_user else None,
                branch_id=None,
                current_filters=current_filters
            )
            
            # Convert to old format for backward compatibility
            return {
                'groups': filter_data.get('groups', []),
                'backend_data': filter_data.get('backend_data', {}),
                'active_filters_count': filter_data.get('active_filters_count', 0),
                'has_filters': len(filter_data.get('groups', [])) > 0
            }
            
        except Exception as e:
            logger.error(f"New filter service failed, using fallback: {str(e)}")
            return self._assemble_enhanced_filter_form_fallback(config, current_filters)

    def _assemble_enhanced_filter_data(self, config: EntityConfiguration, form_instance: FlaskForm = None) -> Dict:
        """
        🔄 COMPATIBILITY WRAPPER: Old method signature maintained  
        DEPRECATED: Use filter_service.get_complete_filter_data() instead
        """
        logger.warning(f"DEPRECATED: _assemble_enhanced_filter_data called for {config.entity_type}")
        
        current_filters = request.args.to_dict() if request else {}
        return self._assemble_enhanced_filter_form(config, current_filters)

    def _build_filter_field_data(self, field, current_filters: Dict, backend_data: Dict) -> Dict:
        """
        🔄 COMPATIBILITY WRAPPER: Old method signature maintained
        DEPRECATED: Logic moved to UniversalFilterService
        """
        logger.warning(f"DEPRECATED: _build_filter_field_data called for {field.name}")
        
        try:
            # Try to use new service
            filter_data = self.filter_service.get_complete_filter_data(
                entity_type='unknown',  # We don't have entity context here
                hospital_id=current_user.hospital_id if current_user else None,
                current_filters=current_filters
            )
            
            # Find matching field in new format
            for group in filter_data.get('groups', []):
                for field_data in group.get('fields', []):
                    if field_data.get('name') == field.name:
                        return field_data
            
            # Fallback to basic field data
            return self._get_fallback_field_data(field)
            
        except Exception as e:
            logger.error(f"Error in _build_filter_field_data: {str(e)}")
            return self._get_fallback_field_data(field)

    def _get_filter_backend_data(self, config: EntityConfiguration, current_filters: Dict) -> Dict:
        """
        🔄 COMPATIBILITY WRAPPER: Old method signature maintained
        DEPRECATED: Use filter_service._get_unified_backend_data() instead
        """
        logger.warning(f"DEPRECATED: _get_filter_backend_data called for {config.entity_type}")
        
        try:
            filter_data = self.filter_service.get_complete_filter_data(
                entity_type=config.entity_type,
                hospital_id=current_user.hospital_id if current_user else None,
                current_filters=current_filters
            )
            
            return filter_data.get('backend_data', {})
            
        except Exception as e:
            logger.error(f"Error getting backend data: {str(e)}")
            return {}

    @cache_service_method('entity_search', 'get_filter_backend_data')
    def get_filter_backend_data(self, entity_type: str, config: EntityConfiguration) -> Dict:
        """
        🔄 COMPATIBILITY WRAPPER: Old standalone function signature
        DEPRECATED: Use filter_service._get_unified_backend_data() instead
        """
        logger.warning(f"DEPRECATED: get_filter_backend_data standalone function called for {entity_type}")
        
        return self._get_filter_backend_data(config, {})

    def _detect_active_date_preset(self, field, current_filters: Dict) -> str:
        """
        🔄 COMPATIBILITY WRAPPER: Old method signature maintained
        DEPRECATED: Use filter_service._analyze_date_presets() instead
        """
        logger.warning(f"DEPRECATED: _detect_active_date_preset called for {field.name}")
        
        try:
            preset_data = self.filter_service._analyze_date_presets(current_filters)
            return preset_data.get('active_preset', 'none')
            
        except Exception as e:
            logger.error(f"Error detecting date preset: {str(e)}")
            return 'none'

    def _get_enhanced_filter_type(self, field) -> str:
        """
        🔄 COMPATIBILITY WRAPPER: Old method signature maintained
        DEPRECATED: Use filter_service._get_field_type_safe() instead
        """
        logger.warning(f"DEPRECATED: _get_enhanced_filter_type called for {field.name}")
        
        return self._get_field_type_safe(field)

    # =============================================================================
    # FALLBACK METHODS - BASIC IMPLEMENTATIONS FOR EMERGENCIES
    # =============================================================================

    def _assemble_enhanced_filter_form_fallback(self, config: EntityConfiguration, current_filters: Dict) -> Dict:
        """
        Fallback implementation if UniversalFilterService fails
        Basic filter form assembly without advanced features
        """
        try:
            logger.info(f"Using fallback filter assembly for {config.entity_type}")
            
            filterable_fields = [f for f in config.fields if getattr(f, 'filterable', False)]
            
            if not filterable_fields:
                return {
                    'groups': [],
                    'backend_data': {},
                    'active_filters_count': 0,
                    'has_filters': False
                }
            
            # Basic group creation
            group = {
                'label': 'Filters',
                'type': 'standard',
                'fields': []
            }
            
            for field in filterable_fields:
                field_data = {
                    'name': field.name,
                    'label': field.label,
                    'type': self._get_field_type_safe(field),
                    'value': current_filters.get(field.name, ''),
                    'placeholder': f"Filter by {field.label}...",
                    'required': getattr(field, 'required', False),
                    'has_value': bool(current_filters.get(field.name))
                }
                
                # Add basic options for select fields
                if hasattr(field, 'options') and field.options:
                    field_data['options'] = [{'value': '', 'label': f'All {field.label}'}] + field.options
                
                group['fields'].append(field_data)
            
            active_count = len([k for k, v in current_filters.items() 
                              if v and k not in ['page', 'per_page']])
            
            return {
                'groups': [group] if group['fields'] else [],
                'backend_data': {},
                'active_filters_count': active_count,
                'has_filters': len(filterable_fields) > 0,
                'fallback_mode': True
            }
            
        except Exception as e:
            logger.error(f"Even fallback filter assembly failed: {str(e)}")
            return {
                'groups': [],
                'backend_data': {},
                'active_filters_count': 0,
                'has_filters': False,
                'error': str(e)
            }

    # =============================================================================
    # EXISTING METHODS - KEPT AS-IS
    # =============================================================================

    def _assemble_table_columns(self, config: EntityConfiguration) -> List[Dict]:
        """Assemble table columns from configuration"""
        try:
            columns = []
            
            for field in config.fields:
                if getattr(field, 'show_in_list', False):
                    
                    # Get complex_display_type and convert enum to string value
                    complex_display_type_enum = getattr(field, 'complex_display_type', None)
                    complex_display_type_value = complex_display_type_enum.value if complex_display_type_enum else None

                    # Determine alignment - currency/amount fields should be right-aligned
                    field_type = self._get_field_type_safe(field)
                    if field_type in ['currency', 'amount', 'decimal', 'number']:
                        default_align = 'right'
                    else:
                        default_align = 'left'

                    column = {
                        'name': field.name,
                        'label': field.label,
                        'sortable': getattr(field, 'sortable', False),
                        'css_class': getattr(field, 'css_class', ''),
                        'width': getattr(field, 'width', None),
                        'max_width': getattr(field, 'max_width', None),
                        'align': getattr(field, 'align', 'left'),
                        'field_type': self._get_field_type_safe(field),
                        'format_pattern': getattr(field, 'format_pattern', None),
                        'complex_display_type': complex_display_type_value,
                        'css_classes': getattr(field, 'css_classes', ''),
                        'related_field': getattr(field, 'related_field', None),
                        'related_display_field': getattr(field, 'related_display_field', None),
                        
                        # Universal virtual field metadata for template
                        'virtual': getattr(field, 'virtual', False),
                        'virtual_target': getattr(field, 'virtual_target', None),
                        'virtual_key': getattr(field, 'virtual_key', None)
                    }
                    columns.append(column)
            
            return columns
            
        except Exception as e:
            logger.error(f"Error assembling table columns: {str(e)}")
            return []

    def _extract_virtual_field_value(self, field, item: Dict):
        """Extract virtual field value from JSONB or nested structure - ONLY FOR VIRTUAL FIELDS"""
        try:
            virtual_target = getattr(field, 'virtual_target', None)
            virtual_key = getattr(field, 'virtual_key', None)
            
            if virtual_target and virtual_key:
                target_data = item.get(virtual_target, {})
                if isinstance(target_data, dict):
                    return target_data.get(virtual_key, '')
                else:
                    return ''
            else:
                return ''
        
        except Exception as e:
            logger.error(f"Error extracting virtual field value for {field.name}: {str(e)}")
            return ''

    def _assemble_table_data(self, config: EntityConfiguration, items: List[Dict]) -> List[Dict]:
        """Assemble table data from raw items - PRESERVES ORIGINAL LOGIC"""
        try:
            if not items:
                return []
            
            table_data = []
            
            for item in items:
                row_data = {}
                
                # Process each field that should show in list
                for field in config.fields:
                    if getattr(field, 'show_in_list', False):
                        
                        # HYBRID APPROACH: Only use virtual field logic for virtual fields
                        if getattr(field, 'virtual', False):
                            # Virtual field - use new extraction logic
                            raw_value = self._extract_virtual_field_value(field, item)
                        else:
                            # Direct field - use ORIGINAL logic (preserve existing behavior)
                            raw_value = item.get(field.name)
                        
                        # Store current item for badge formatting
                        self._current_item = item  
                        row_data[field.name] = self._format_field_value(field, raw_value, item)
                
                # Add row metadata
                row_data['_row_id'] = item.get(config.primary_key)
                row_data['_row_actions'] = self._build_row_actions(config, item)
                
                table_data.append(row_data)
            
            return table_data
            
        except Exception as e:
            logger.error(f"Error assembling table data for {config.entity_type}: {str(e)}")
            return []

    def _format_field_value(self, field, raw_value, item=None) -> str:
        """Format field value for display"""
        try:
            if raw_value is None:
                return ''
            
            field_type = self._get_field_type_safe(field)

            # SPECIAL CASE: Currency fields with format patterns should return raw values
            # Let the template handle the formatting
            if field_type == 'currency' and getattr(field, 'format_pattern', None) == 'mixed_payment_breakdown':
                # Return raw numeric value for template processing
                try:
                    return str(float(raw_value))
                except (ValueError, TypeError):
                    return '0'
            
            if field_type == 'currency' or field_type == 'amount':
                try:
                    # Always return numeric value - let template handle formatting
                    return float(raw_value) if raw_value is not None else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            if field_type == 'date':
                if isinstance(raw_value, (date, datetime)):
                    return raw_value.strftime('%d/%b/%Y')  # Was: '%b %d, %Y'
                elif isinstance(raw_value, str):
                    try:
                        date_obj = datetime.strptime(raw_value, '%Y-%m-%d').date()
                        return date_obj.strftime('%d/%b/%Y')  # Was: '%b %d, %Y'
                    except:
                        return raw_value
            
            elif field_type == 'datetime':
                if isinstance(raw_value, datetime):
                    # For datetime objects, show date and time
                    return raw_value.strftime('%d/%b/%Y %H:%M')
                elif isinstance(raw_value, date):
                    # For date objects, just show date
                    return raw_value.strftime('%d/%b/%Y')
                elif isinstance(raw_value, str):
                    try:
                        # ✅ FIXED: Handle timezone-aware datetime strings first
                        from dateutil import parser
                        dt_obj = parser.parse(raw_value)
                        return dt_obj.strftime('%d/%b/%Y %H:%M')
                    except:
                        try:
                            # Try parsing as full datetime first
                            dt_obj = datetime.strptime(raw_value, '%Y-%m-%d %H:%M:%S')
                            return dt_obj.strftime('%d/%b/%Y %H:%M')
                        except:
                            try:
                                # Try parsing as datetime without seconds
                                dt_obj = datetime.strptime(raw_value, '%Y-%m-%d %H:%M')
                                return dt_obj.strftime('%d/%b/%Y %H:%M')
                            except:
                                try:
                                    # Try parsing as just date
                                    date_obj = datetime.strptime(raw_value, '%Y-%m-%d').date()
                                    return date_obj.strftime('%d/%b/%Y')
                                except:
                                    return raw_value

            # Also handle the case where a field is marked as DATE but contains datetime
            elif field_type == 'date':
                if isinstance(raw_value, datetime):
                    # If it's actually a datetime, format as date only
                    return raw_value.strftime('%d/%b/%Y')
                elif isinstance(raw_value, date):
                    return raw_value.strftime('%d/%b/%Y')
                elif isinstance(raw_value, str):
                    try:
                        # ✅ FIXED: Handle timezone-aware datetime strings first
                        from dateutil import parser
                        dt_obj = parser.parse(raw_value)
                        return dt_obj.strftime('%d/%b/%Y')
                    except:
                        try:
                            # Try parsing as datetime first (common case)
                            dt_obj = datetime.strptime(raw_value, '%Y-%m-%d %H:%M:%S')
                            return dt_obj.strftime('%d/%b/%Y')
                        except:
                            try:
                                # Try parsing as date
                                date_obj = datetime.strptime(raw_value, '%Y-%m-%d').date()
                                return date_obj.strftime('%d/%b/%Y')
                            except:
                                return raw_value

            elif field_type in ['currency', 'amount']:
                try:
                    amount = float(raw_value)
                    return f"₹{amount:,.2f}"
                except:
                    return str(raw_value)
            
            elif field_type == 'status_badge':
                result = self._format_status_badge(field, raw_value, item)
                # Return the badge HTML, or create default badge
                if isinstance(result, dict) and 'badge_html' in result:
                    return result['badge_html']
                elif isinstance(result, dict) and 'formatted_value' in result:
                    css_class = result.get('css_class', 'status-badge status-default')
                    return f'<span class="{css_class}">{result["formatted_value"]}</span>'
                else:
                    return f'<span class="status-badge status-default">{str(raw_value)}</span>'
            
            return str(raw_value)
            
        except Exception as e:
            logger.error(f"Error formatting field value: {str(e)}")
            return str(raw_value) if raw_value is not None else '—'

    def _format_status_badge(self, field, value, item=None) -> Dict:
        """
        Format status badge with CSS class
        ENHANCED: Universal deleted status detection
        """
        try:
            # Universal DELETED STATUS DETECTION
            is_deleted = False
            if item:
                # Check multiple possible deleted flags (handle both dict and object)
                if isinstance(item, dict):
                    is_deleted = (item.get('is_deleted', False) or 
                                item.get('deleted_flag', False) or
                                item.get('deleted', False))
                else:
                    is_deleted = (getattr(item, 'is_deleted', False) or 
                                getattr(item, 'deleted_flag', False) or
                                getattr(item, 'deleted', False))
            
            # If deleted, override status to show "Deleted" regardless of actual status
            if is_deleted:
                logger.debug(f"[STATUS_BADGE_DEBUG] Detected deleted item, showing Deleted badge")
                return {
                    'formatted_value': 'Deleted',
                    'css_class': 'status-badge status-deleted',
                    'badge_html': '<span class="status-badge status-deleted"><i class="fas fa-trash-alt"></i> Deleted</span>'
                }

            # ✅ FIXED: Return consistent structure for non-deleted status
            if hasattr(field, 'options') and field.options:
                for option in field.options:
                    if str(option.get('value', '')).lower() == str(value).lower():
                        return {
                            'formatted_value': option.get('label', value),
                            'css_class': f"status-badge {option.get('css_class', 'status-default')}",
                            'badge_html': f'<span class="status-badge {option.get("css_class", "status-default")}">{option.get("label", value)}</span>'
                        }

            # ✅ FIXED: Default case with consistent structure
            return {
                'formatted_value': str(value).title(),
                'css_class': 'status-badge status-default',
                'badge_html': f'<span class="status-badge status-default">{str(value).title()}</span>'
            }
            
        except Exception as e:
            logger.error(f"Error formatting status badge: {str(e)}")
            return {'text': str(value), 'css_class': 'status-default'}

    def _assemble_summary_data(self, config: EntityConfiguration, raw_data: Dict) -> Dict:
        """Assemble summary data from raw data"""
        try:
            
            summary = raw_data.get('summary', {})
            
            # Add computed summary if not provided
            items = raw_data.get('items', [])
            
            if not summary and items:
                summary = {
                    'total_count': len(items),
                    'current_page_count': len(items)
                }

            # Add summary cards configuration
            summary['cards'] = getattr(config, 'summary_cards', [])

            return summary
            
        except Exception as e:
            logger.error(f"Error assembling summary data: {str(e)}")
            return {}

    def _assemble_pagination_data(self, raw_data: Dict, current_filters: Dict) -> Dict:
        """Assemble pagination data"""
        try:
            pagination = raw_data.get('pagination', {})
            
            # ✅ FIX: Always use filtered count from summary when available
            summary = raw_data.get('summary', {})
            if summary and 'total_count' in summary:
                filtered_total = summary['total_count']  # Use filtered count
                
                # Update existing pagination with filtered count
                if pagination:
                    current_page = pagination.get('page', 1)
                    per_page = pagination.get('per_page', 20)
                    
                    pagination.update({
                        'total_count': filtered_total,
                        'total_pages': max(1, (filtered_total + per_page - 1) // per_page)
                    })
                else:
                    # Create new pagination with filtered count
                    current_page = int(current_filters.get('page', 1))
                    per_page = int(current_filters.get('per_page', 20))
                    
                    pagination = {
                        'total_items': filtered_total,
                        'current_page': current_page,
                        'per_page': per_page,
                        'total_pages': max(1, (filtered_total + per_page - 1) // per_page),
                        'has_prev': current_page > 1,
                        'has_next': current_page * per_page < filtered_total,
                        'total_count': filtered_total,
                        'page': current_page
                    }
            elif not pagination:
                # Fallback when no summary and no pagination
                total_items = raw_data.get('total', len(raw_data.get('items', [])))
                    
                current_page = int(current_filters.get('page', 1))
                per_page = int(current_filters.get('per_page', 20))
                
                pagination = {
                    'total_items': total_items,
                    'current_page': current_page,
                    'per_page': per_page,
                    'total_pages': max(1, (total_items + per_page - 1) // per_page),
                    'has_prev': current_page > 1,
                    'has_next': current_page * per_page < total_items,
                    'total_count': total_items,
                    'page': current_page
                }
            
            return pagination
            
        except Exception as e:
            logger.error(f"Error assembling pagination data: {str(e)}")
            return {'total_items': 0, 'current_page': 1, 'per_page': 20, 'total_pages': 1}

    def _build_row_actions(self, config: EntityConfiguration, item: Dict) -> List[Dict]:
        """Build action buttons for table rows"""
        try:
            actions = []
            
            for action_config in config.actions:
                if not getattr(action_config, 'show_in_list', False):
                    continue
                
                if self._check_action_conditions(action_config, item):
                    action = {
                        'name': getattr(action_config, 'name', action_config.id),
                        'label': action_config.label,
                        'icon': action_config.icon,
                        'css_class': getattr(action_config, 'css_class', 'btn-sm'),
                        'url': self._build_action_url(action_config, item, config),
                        'confirmation_required': getattr(action_config, 'confirmation_required', False),
                        'confirmation_message': getattr(action_config, 'confirmation_message', '')
                    }
                    actions.append(action)
            
            return actions
            
        except Exception as e:
            logger.error(f"Error building row actions: {str(e)}")
            return []

    def _check_action_conditions(self, action_config, item: Dict) -> bool:
        """Check if action should be shown based on conditions"""
        try:
            if not hasattr(action_config, 'conditions') or not action_config.conditions:
                return True
            
            for field_name, allowed_values in action_config.conditions.items():
                item_value = item.get(field_name)
                if item_value not in allowed_values:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking action conditions: {str(e)}")
            return True

    def _build_action_url(self, action_config, item: Dict, config: EntityConfiguration) -> str:
        """Build action URL from configuration"""
        try:
            if not hasattr(action_config, 'url_pattern') or not action_config.url_pattern:
                return '#'
            
            url_pattern = action_config.url_pattern
            item_id = item.get(config.primary_key)
            
            if '<id>' in url_pattern and item_id:
                return url_pattern.replace('<id>', str(item_id))
            
            return url_pattern
            
        except Exception as e:
            logger.error(f"Error building action URL: {str(e)}")
            return '#'

    # ============================================================================= 
    # SUMMARY CARDS ASSEMBLER
    # =============================================================================

    def _assemble_summary_cards(self, config: EntityConfiguration, raw_data: Dict) -> List[Dict]:
        """
        ✅ MISSING METHOD: Assemble summary cards from configuration
        This method was referenced but missing from your data assembler
        """
        try:
            summary_data = raw_data.get('summary', {})
            cards = []
            
           
            # ✅ VALIDATION: Ensure config has summary_cards
            if not hasattr(config, 'summary_cards') or not config.summary_cards:
                logger.warning(f"No summary_cards configuration for {config.entity_type}")
                return []
            
            # ✅ ASSEMBLY: Process each configured card
            for card_config in config.summary_cards:
                try:
                    # ✅ VISIBILITY CHECK: Skip hidden cards
                    if not card_config.get('visible', True):
                        continue

                    # ✅ SPECIAL HANDLING: Detail cards (breakdown, charts, etc.)
                    if card_config.get('card_type') == 'detail':
                        # ✅ Get breakdown data from summary (provided by service layer)
                        breakdown_fields = card_config.get('breakdown_fields', {})
                        breakdown_data = {field: summary_data.get(field, 0) for field in breakdown_fields.keys()}
                        card = {
                            'id': card_config['id'],
                            'label': card_config['label'],
                            'icon': card_config['icon'],
                            'icon_css_class': card_config.get('icon_css', 'stat-card-icon primary'),
                            'type': card_config.get('type', 'currency'),  # Use standard type for formatting
                            'card_type': 'detail',  # Specify this is a detail card
                            'breakdown_data': breakdown_data,
                            'breakdown_fields': breakdown_fields,
                            'filterable': card_config.get('filterable', False),
                            'value': card_config.get('label', 'Details'),  # Display value for the card
                            'raw_value': breakdown_data,  # Raw data for template access
                            'visible': card_config.get('visible', True),
                            'filter_field': card_config.get('filter_field'),
                            'filter_value': card_config.get('filter_value')
                        }
                        cards.append(card)
                        continue


                    # Get raw value from summary data
                    field_name = card_config.get('field', '')
                    raw_value = summary_data.get(field_name, 0)
                    
                    # ✅ FIX: Log missing fields but continue processing
                    if raw_value == 0 and field_name not in summary_data:
                        logger.warning(f"[WARNING]  Card {field_name}: field '{field_name}' missing from summary, using default value 0")

                    
                    # ✅ FORMATTING: Format value based on type
                    card_type = card_config.get('type', 'number')
                    if card_type == 'currency':
                        # Handle currency formatting
                        try:
                            numeric_value = float(raw_value) if raw_value is not None else 0.0
                            formatted_value = f"₹{numeric_value:,.2f}"
                        except (ValueError, TypeError):
                            formatted_value = "₹0.00"
                    elif card_type == 'number':
                        # Handle number formatting
                        try:
                            numeric_value = int(raw_value) if raw_value is not None else 0
                            formatted_value = f"{numeric_value:,}"
                        except (ValueError, TypeError):
                            formatted_value = "0"
                    else:
                        # Default string formatting
                        formatted_value = str(raw_value) if raw_value is not None else "0"
                    
                    # ✅ CARD CREATION: Build card data structure
                    card = {
                        'id': card_config.get('id', field_name),
                        'label': card_config.get('label', field_name.replace('_', ' ').title()),
                        'value': formatted_value,
                        'raw_value': raw_value,
                        'icon': card_config.get('icon', 'fas fa-chart-bar'),
                        'icon_css_class': card_config.get('icon_css', 'stat-card-icon primary'),
                        'type': card_config.get('type', 'number'),
                        'filterable': card_config.get('filterable', False),
                        'filter_field': card_config.get('filter_field'),
                        'filter_value': card_config.get('filter_value'),
                        'clickable': card_config.get('clickable', False),
                        'action': card_config.get('action')
                    }
                    
                    cards.append(card)
                    
                except Exception as card_error:
                    logger.error(f"❌ Error processing summary card {card_config}: {str(card_error)}")
                    # Continue with other cards even if one fails
                    continue
            
            return cards
            
        except Exception as e:
            print(f"❌ [SUMMARY_CARDS_ERROR] {str(e)}")
            logger.error(f"❌ Error assembling summary cards for {config.entity_type}: {str(e)}")
        return []

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def _make_template_safe_config(self, config: EntityConfiguration) -> Dict:
        """Convert EntityConfiguration dataclass to template-safe dictionary"""
        try:
            return {
                'entity_type': getattr(config, 'entity_type', 'unknown'),
                'name': getattr(config, 'name', 'Unknown'),
                'plural_name': getattr(config, 'plural_name', 'Unknown'),
                'icon': getattr(config, 'icon', 'fas fa-list'),
                'page_title': getattr(config, 'page_title', 'Unknown Entity'),
                'description': getattr(config, 'description', 'Unknown entity type'),
                'primary_key': getattr(config, 'primary_key', 'id'),
                'title_field': getattr(config, 'title_field', 'name'),
                'subtitle_field': getattr(config, 'subtitle_field', 'description'),
                'actions': getattr(config, 'actions', []),  # Keep as ActionDefinition objects
                'fields': getattr(config, 'fields', []),    # Keep as FieldDefinition objects
                'summary_cards': list(getattr(config, 'summary_cards', [])),  # ✅ Convert to list
                'permissions': dict(getattr(config, 'permissions', {})),  # ✅ Convert to dict
                'enable_saved_filter_suggestions': getattr(config, 'enable_saved_filter_suggestions', True),
                'enable_auto_submit': getattr(config, 'enable_auto_submit', True)  # ✅ ADD THIS LINE
            }
        except Exception as e:
            logger.error(f"Error converting config to template-safe format: {str(e)}")
            # Safe fallback
            return {
                'entity_type': 'unknown',
                'name': 'Unknown',
                'plural_name': 'Unknown',
                'icon': 'fas fa-list',
                'page_title': 'Unknown Entity',
                'description': 'Unknown entity type',
                'primary_key': 'id',
                'title_field': 'name',
                'subtitle_field': 'description',
                'actions': [],
                'fields': [],
                'summary_cards': [],
                'permissions': {},
                'enable_saved_filter_suggestions': True,
                'enable_auto_submit': True
            }

    def _get_field_type_safe(self, field) -> str:
        """Safely get field type as string"""
        try:
            if not field or not hasattr(field, 'field_type'):
                return 'text'
            
            if hasattr(field.field_type, 'value'):
                return field.field_type.value.lower()
            elif hasattr(field.field_type, 'name'):
                return field.field_type.name.lower()
            else:
                return str(field.field_type).lower().replace('fieldtype.', '')
                
        except Exception as e:
            logger.error(f"Error getting field type: {str(e)}")
            return 'text'

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

    def _get_error_fallback_data(self, config: EntityConfiguration, error: str) -> Dict:
        """Get safe fallback data when assembly fails"""
        template_safe_config = self._make_template_safe_config(config)
        
        return {
            'items': [],
            'total_count': 0,
            'entity_config': template_safe_config,
            'entity_type': config.entity_type,
            'filter_data': {
                'groups': [],
                'backend_data': {},
                'active_filters': [],
                'active_filters_count': 0,
                'has_errors': True,
                'error_messages': [error]
            },
            'table_columns': [],
            'table_data': [],
            'summary': {},
            'pagination': {'total_items': 0, 'current_page': 1, 'total_pages': 1},
            'branch_context': {},
            'current_url': '',
            'base_url': '',
            'form_instance': None,
            'has_data': False,
            'has_errors': True,
            'error_messages': [error]
        }

    # =============================================================================
    # VIEW FIELD ASSEMBLY FUNCTIONS
    # =============================================================================

    def assemble_universal_view_data(self, config: EntityConfiguration, raw_item_data: Dict, **kwargs) -> Dict:
        """
        Main view data assembly - with fixed layout type handling
        """
        try:
            item = raw_item_data.get('item')
            if not item:
                raise ValueError("No item found in raw data")
            
            item_id = getattr(item, config.primary_key, None)
            
            # Get layout type FIRST
            layout_type = self._get_layout_type(config)
            has_tabs = self._has_tabbed_layout(config)
            
            logger.info(f"[VIEW] Assembling view data for {config.entity_type}")
            logger.info(f"[VIEW] Layout type: '{layout_type}', Has tabs: {has_tabs}")
            
            # Assemble field sections
            field_sections = self._assemble_view_sections_from_fields(config, item)
            
            assembled_data = {
                'entity_config': self._make_template_safe_config(config),
                'entity_type': config.entity_type,
                'item': item,
                'item_id': item_id,
                
                # Core view data
                'field_sections': field_sections,
                'action_buttons': self._assemble_view_action_buttons(config, item, item_id),
                'page_title': f"{config.name} Details",
                'breadcrumbs': self._build_view_breadcrumbs(config, item),
                
                # CRITICAL: Ensure layout_type is a string, not an enum
                'layout_type': layout_type,  # This MUST be 'tabbed' as a string
                'has_tabs': has_tabs,
                'has_accordion': layout_type == 'accordion',
                
                # Header configuration
                'header_config': self._enhance_header_config(config) if hasattr(config.view_layout, 'header_config') else None,
                'header_data': item,
                'header_actions': self._assemble_header_action_buttons(config, item, item_id),

                # Context information
                'branch_context': kwargs.get('branch_context', {}),
                'user_permissions': kwargs.get('user_permissions', {}),
            }
            
            # Final verification log
            logger.info(f"[VIEW] Final assembled data - layout_type: '{assembled_data['layout_type']}'")
            logger.info(f"[VIEW] Field sections count: {len(assembled_data['field_sections'])}")
            
            return self._clean_view_data(assembled_data)
            
        except Exception as e:
            logger.error(f"❌ [DATA_ASSEMBLER] View assembly error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_error_fallback_data(config, str(e))


    def _assemble_header_action_buttons(self, config: EntityConfiguration, item: Any, item_id: str) -> Dict[str, List[Dict]]:
        """
        Assemble action buttons for header - respects display_type configuration
        """
        try:
            button_actions = []
            dropdown_actions = []
            processed_ids = set()
            
            logger.info(f"[DEBUG] Processing {len(config.actions)} actions for header")

            for action in config.actions:
                if action.id in processed_ids:
                    logger.debug(f"[DEBUG] Skipping duplicate action: {action.id}")
                    continue
                    
                if not getattr(action, 'show_in_detail', False):
                    logger.debug(f"[DEBUG] Action {action.id} not shown in detail view")
                    continue
                
                if not self._evaluate_action_conditions(action, item):
                    continue
                
                # Get display type
                display_type = getattr(action, 'display_type', ActionDisplayType.DROPDOWN_ITEM)
                if isinstance(display_type, ActionDisplayType):
                    display_type_value = display_type.value
                else:
                    display_type_value = str(display_type)
                logger.info(f"[DEBUG] Action {action.id} has display_type: {display_type_value}")

                # Get button type value
                button_type = getattr(action, 'button_type', ButtonType.OUTLINE)
                if hasattr(button_type, 'value'):
                    button_type_value = button_type.value
                else:
                    button_type_value = str(button_type)

                # Build action data
                action_data = {
                    'id': action.id,
                    'label': action.label,
                    'icon': action.icon,
                    'url': action.get_url(item, config),  # Use the action's built-in get_url method
                    'javascript_handler': getattr(action, 'javascript_handler', None),
                    'button_type': button_type_value,  # Now always a string
                    'display_type': display_type_value,
                    'confirmation_required': getattr(action, 'confirmation_required', False),
                    'confirmation_message': getattr(action, 'confirmation_message', ''),
                    'order': getattr(action, 'order', 999)
                }
                
                # Add to appropriate list based on display type
                if display_type_value == 'button':
                    button_actions.append(action_data)
                    logger.info(f"[DEBUG] Added {action.id} to button_actions")
                else:
                    dropdown_actions.append(action_data)
                    logger.info(f"[DEBUG] Added {action.id} to dropdown_actions")

                processed_ids.add(action.id)
            
            # Sort both lists by order
            button_actions.sort(key=lambda x: x['order'])
            dropdown_actions.sort(key=lambda x: x['order'])
            logger.info(f"[DEBUG] Final counts - buttons: {len(button_actions)}, dropdown: {len(dropdown_actions)}")

            return {
                'button_actions': button_actions,
                'dropdown_actions': dropdown_actions
            }
            
        except Exception as e:
            logger.error(f"Error assembling header actions: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'button_actions': [], 'dropdown_actions': []}

    def _evaluate_action_conditions(self, action: ActionDefinition, item: Any) -> bool:
        """
        Evaluate action conditions based on configuration
        """
        try:
            if not hasattr(action, 'conditions') or not action.conditions:
                return True
            
            for field, allowed_values in action.conditions.items():
                # Get value from item (works with dict or object)
                if isinstance(item, dict):
                    actual_value = item.get(field)
                else:
                    actual_value = getattr(item, field, None)
                
                # Ensure allowed_values is a list
                if not isinstance(allowed_values, list):
                    allowed_values = [allowed_values]
                
                # Check if value matches any allowed value
                if actual_value not in allowed_values:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating conditions: {str(e)}")
            return True  # Default to showing action on error

    def _enhance_header_config(self, config: EntityConfiguration) -> Dict:
        """Enhance header config with field metadata for better template handling"""
        header_config = config.view_layout.header_config.copy() if config.view_layout.header_config else {}
        
        # Find the title field configuration
        if header_config.get('title_field') == 'supplier_name':
            for field in config.fields:
                if field.name == 'supplier_name' and hasattr(field, 'related_field'):
                    # Use the related field for entity references
                    header_config['title_field'] = field.related_field  # 'supplier'
                    header_config['title_field_name'] = 'supplier_name'
                    break
        
        return header_config


    def _clean_view_data(self, data: Any) -> Any:
        """
        Clean view data to remove Undefined objects and ensure JSON serializable
        Minimal implementation to fix JSON serialization errors
        """
        from jinja2 import Undefined
        from datetime import date, datetime
        
        if isinstance(data, Undefined):
            return None
        elif isinstance(data, dict):
            return {k: self._clean_view_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_view_data(item) for item in data]
        elif isinstance(data, (date, datetime)):
            return data.isoformat()
        elif hasattr(data, '__dict__') and not isinstance(data, (str, int, float, bool, type(None))):
            # Convert objects to dictionaries
            try:
                from app.services.database_service import get_entity_dict
                entity_dict = get_entity_dict(data)
                # Debug supplier_name
                if hasattr(data, 'supplier_name'):
                    logger.info(f"[DEBUG] Object has supplier_name: {data.supplier_name}")
                if 'supplier_name' in entity_dict:
                    logger.info(f"[DEBUG] Dict has supplier_name: {entity_dict['supplier_name']}")
                return entity_dict
            except Exception as e:
                logger.error(f"Failed to convert entity to dict: {str(e)}")
                return str(data)
        else:
            return data


    def _assemble_view_sections_from_fields(self, config: EntityConfiguration, item: Any) -> List[Dict]:
        """
        Assemble view sections by reading enhanced field definitions directly
        MUCH SIMPLER - no embedded configuration, just reads field properties
        """
        try:
            # Get fields that should show in detail view
            detail_fields = [f for f in config.fields if getattr(f, 'show_in_detail', True)]
            
            logger.info(f"[VIEW] Assembling sections for {config.entity_type}")
            logger.info(f"[VIEW] Total fields: {len(config.fields)}, Detail fields: {len(detail_fields)}")

            if not detail_fields:
                return []
            
            # Get layout type from configuration
            layout_type = self._get_layout_type(config)
            
            if layout_type == 'tabbed':
                result = self._organize_by_tabs_from_fields(detail_fields, item, config)
                logger.info(f"[VIEW] Tabbed layout assembled: {len(result)} tabs")
                
                # Log details about each tab
                for tab in result:
                    total_fields = sum(len(section.get('fields', [])) for section in tab.get('sections', []))
                    logger.info(f"[VIEW] Tab '{tab['key']}': {len(tab.get('sections', []))} sections, {total_fields} fields")
                
                return result
            elif layout_type == 'accordion':
                return self._organize_by_accordion_from_fields(detail_fields, item, config)
            else:
                # Simple layout
                return self._organize_simple_from_fields(detail_fields, item, config)
                
        except Exception as e:
            logger.error(f"Error assembling view sections: {str(e)}")
            return self._create_fallback_sections(detail_fields, item, config)

    def _organize_by_tabs_from_fields(self, fields: List[FieldDefinition], item: Any, config: EntityConfiguration) -> List[Dict]:
        """
        Organize fields into tabs by reading tab_group from field definitions
        PROPERLY reads tab configuration including order
        """
        tabs = {}
        
        # First, pre-create all tabs from configuration to ensure proper order
        if (hasattr(config, 'view_layout') and 
            config.view_layout and 
            hasattr(config.view_layout, 'tabs') and 
            config.view_layout.tabs):
            
            for tab_key, tab_config in config.view_layout.tabs.items():
                tabs[tab_key] = {
                    'key': tab_key,
                    'label': tab_config.label if hasattr(tab_config, 'label') else tab_key.replace('_', ' ').title(),
                    'icon': tab_config.icon if hasattr(tab_config, 'icon') else 'fas fa-info-circle',
                    'order': tab_config.order if hasattr(tab_config, 'order') else 999,
                    'sections': {}
                }
                
                # Pre-create sections from tab configuration
                if hasattr(tab_config, 'sections') and tab_config.sections:
                    for section_key, section_config in tab_config.sections.items():
                        tabs[tab_key]['sections'][section_key] = {
                            'key': section_key,
                            'title': section_config.title if hasattr(section_config, 'title') else section_key.replace('_', ' ').title(),
                            'icon': section_config.icon if hasattr(section_config, 'icon') else None,
                            'columns': section_config.columns if hasattr(section_config, 'columns') else 2,
                            'order': section_config.order if hasattr(section_config, 'order') else 0,
                            'collapsible': getattr(section_config, 'collapsible', False),
                            'fields': []
                        }
        
        # PHASE 1: Process all non-custom-renderer fields first
        logger.info(f"[PHASE1] Processing standard fields for {config.entity_type}")
        standard_count = 0
        custom_fields = []  # Store custom renderer fields for phase 2

        # Process fields into their assigned tabs/sections
        for field in fields:
            if not self._should_display_field(field, item):
                continue
            
            # Check if it's a custom renderer field
            if self._field_has_custom_renderer(field):
                # Save for phase 2
                custom_fields.append(field)
                continue
            
            standard_count += 1

            # Get tab and section from field definition
            tab_key = getattr(field, 'tab_group', 'details')
            section_key = getattr(field, 'section', 'general')
            
            # Create tab if not exists
            if tab_key not in tabs:
                tabs[tab_key] = {
                    'key': tab_key,
                    'label': tab_key.replace('_', ' ').title(),
                    'icon': 'fas fa-info-circle',
                    'order': 999,
                    'sections': {}
                }
            
            # Create section if not exists
            if section_key not in tabs[tab_key]['sections']:
                tabs[tab_key]['sections'][section_key] = {
                    'key': section_key,
                    'title': section_key.replace('_', ' ').title(),
                    'icon': None,
                    'columns': 2,
                    'order': 0,
                    'collapsible': False,
                    'fields': []
                }
            
            # Add formatted field to section (skip custom renderer processing)
            formatted_field = self._format_field_for_view(field, item, skip_custom_renderer=True)
            tabs[tab_key]['sections'][section_key]['fields'].append(formatted_field)
        
        logger.info(f"[PHASE1] Processed {standard_count} standard fields")

        # PHASE 2: Now process custom renderer fields
        if custom_fields:
            logger.info(f"[PHASE2] Processing {len(custom_fields)} custom renderer fields")
            
            for field in custom_fields:
                # Get tab and section from field definition
                tab_key = getattr(field, 'tab_group', 'details')
                section_key = getattr(field, 'section', 'general')
                
                # Create tab if not exists (same logic as phase 1)
                if tab_key not in tabs:
                    tabs[tab_key] = {
                        'key': tab_key,
                        'label': tab_key.replace('_', ' ').title(),
                        'icon': 'fas fa-info-circle',
                        'order': 999,
                        'sections': {}
                    }
                
                # Create section if not exists
                if section_key not in tabs[tab_key]['sections']:
                    tabs[tab_key]['sections'][section_key] = {
                        'key': section_key,
                        'title': section_key.replace('_', ' ').title(),
                        'icon': None,
                        'columns': 2,
                        'order': 0,
                        'collapsible': False,
                        'fields': []
                    }
                
                # Add formatted field with custom renderer
                formatted_field = self._format_field_for_view(field, item, skip_custom_renderer=False)
                tabs[tab_key]['sections'][section_key]['fields'].append(formatted_field)

        # Convert to list and sort
        result = []
        for tab_key, tab_data in tabs.items():
            # Convert sections dict to list and sort
            sections_list = sorted(tab_data['sections'].values(), key=lambda x: x['order'])
            tab_data['sections'] = sections_list
            result.append(tab_data)
        
        # Sort tabs by order
        result.sort(key=lambda x: x['order'])
        
        # Log summary only (not details)
        logger.info(f"[VIEW] Assembled {len(result)} tabs for {config.entity_type}")
        
        return result


    # def _organize_by_tabs_from_fields(self, fields: List[FieldDefinition], item: Any, config: EntityConfiguration) -> List[Dict]:
    #     """
    #     Organize fields into tabs by reading tab_group from field definitions
    #     PROPERLY reads tab configuration including order
    #     """
    #     tabs = {}
        
    #     # First, pre-create all tabs from configuration to ensure proper order
    #     if (hasattr(config, 'view_layout') and 
    #         config.view_layout and 
    #         hasattr(config.view_layout, 'tabs') and 
    #         config.view_layout.tabs):
            
    #         for tab_key, tab_config in config.view_layout.tabs.items():
    #             tabs[tab_key] = {
    #                 'key': tab_key,
    #                 'label': tab_config.label if hasattr(tab_config, 'label') else tab_key.title(),
    #                 'icon': tab_config.icon if hasattr(tab_config, 'icon') else 'fas fa-folder',
    #                 'order': tab_config.order if hasattr(tab_config, 'order') else 999,
    #                 'default_active': tab_config.default_active if hasattr(tab_config, 'default_active') else False,
    #                 'sections': {}
    #             }
                
    #             # Pre-create sections from tab configuration
    #             if hasattr(tab_config, 'sections') and tab_config.sections:
    #                 for section_key, section_config in tab_config.sections.items():
    #                     tabs[tab_key]['sections'][section_key] = {
    #                         'key': section_key,
    #                         'title': section_config.title if hasattr(section_config, 'title') else section_key.title(),
    #                         'icon': section_config.icon if hasattr(section_config, 'icon') else 'fas fa-info-circle',
    #                         'columns': section_config.columns if hasattr(section_config, 'columns') else 2,
    #                         'collapsible': section_config.collapsible if hasattr(section_config, 'collapsible') else False,
    #                         'order': section_config.order if hasattr(section_config, 'order') else 999,
    #                         'fields': []
    #                     }
        
    #     # Now populate fields into the pre-created structure
    #     for field in fields:
    #         if not self._should_display_field(field, item):
    #             continue
                
    #         # Read tab and section from field definition
    #         tab_key = getattr(field, 'tab_group', 'main')
    #         section_key = getattr(field, 'section', 'details')
            
    #         # Create tab if not exists (for fields without pre-configured tabs)
    #         if tab_key not in tabs:
    #             tabs[tab_key] = {
    #                 'key': tab_key,
    #                 'label': self._get_tab_label(tab_key, config),
    #                 'icon': self._get_tab_icon(tab_key, config),
    #                 'order': 999,  # Put unconfigured tabs at the end
    #                 'default_active': False,
    #                 'sections': {}
    #             }
            
    #         # Create section if not exists
    #         if section_key not in tabs[tab_key]['sections']:
    #             tabs[tab_key]['sections'][section_key] = {
    #                 'key': section_key,
    #                 'title': self._get_section_title(section_key, config),
    #                 'icon': self._get_section_icon(section_key, config),
    #                 'columns': 2,
    #                 'collapsible': False,
    #                 'order': 999,
    #                 'fields': []
    #             }
            
    #         # Add formatted field
    #         tabs[tab_key]['sections'][section_key]['fields'].append(
    #             self._format_field_for_view(field, item)
    #         )
        
    #     # Convert to sorted list
    #     tab_list = []
    #     for tab_data in tabs.values():
    #         # Sort sections within tab by their configured order
    #         tab_data['sections'] = sorted(tab_data['sections'].values(), key=lambda x: x.get('order', 999))
    #         tab_list.append(tab_data)
        
    #     # Sort tabs by their configured order
    #     return sorted(tab_list, key=lambda x: x.get('order', 999))

    def _organize_by_accordion_from_fields(self, fields: List[FieldDefinition], item: Any, config: EntityConfiguration) -> List[Dict]:
        """
        Organize fields into accordion by reading section from field definitions
        """
        sections = {}
        
        for field in fields:
            if not self._should_display_field(field, item):
                continue
                
            # Read section from field definition (enhanced property)
            section_key = getattr(field, 'section', 'details')
            
            # Create section if not exists
            if section_key not in sections:
                sections[section_key] = {
                    'key': section_key,
                    'title': self._get_section_title(section_key, config),
                    'icon': self._get_section_icon(section_key, config),
                    'columns': 2,  # Default
                    'default_collapsed': False,  # Can be enhanced later
                    'order': 0,  # Can be enhanced later
                    'fields': []
                }
            
            # Add formatted field
            sections[section_key]['fields'].append(
                self._format_field_for_view(field, item)
            )
        
        # Return as single "tab" for template compatibility
        return [{
            'key': 'accordion',
            'label': f'{config.name} Details',
            'icon': config.icon,
            'sections': sorted(sections.values(), key=lambda x: x['order'])
        }]

    def _organize_simple_from_fields(self, fields: List[FieldDefinition], item: Any, config: EntityConfiguration) -> List[Dict]:
        """
        Organize fields into simple layout by reading section from field definitions
        """
        sections = {}
        
        for field in fields:
            if not self._should_display_field(field, item):
                continue
                
            # Read section from field definition (enhanced property)
            section_key = getattr(field, 'section', 'details')
            
            # Create section if not exists
            if section_key not in sections:
                sections[section_key] = {
                    'key': section_key,
                    'title': self._get_section_title(section_key, config),
                    'icon': self._get_section_icon(section_key, config),
                    'columns': 2,  # Default
                    'order': 0,  # Can be enhanced later
                    'fields': []
                }
            
            # Add formatted field
            sections[section_key]['fields'].append(
                self._format_field_for_view(field, item)
            )
        
        # Return as single "tab" for template compatibility
        return [{
            'key': 'simple',
            'label': f'{config.name} Details',
            'icon': config.icon,
            'sections': sorted(sections.values(), key=lambda x: x['order'])
        }]

    def _format_field_for_view(self, field: FieldDefinition, item: Any, skip_custom_renderer: bool = False) -> Dict:
        """
        Format ANY field for view display - purely configuration-driven.
        No entity-specific checks or hardcoded field names!
        
        NEW PARAMETER: skip_custom_renderer - if True, skip custom renderer processing
        """
        try:
            # Get field name from configuration
            field_name = getattr(field, 'name', 'unknown')
            
            # Determine field characteristics from configuration
            has_custom_renderer = self._field_has_custom_renderer(field)
            is_virtual = getattr(field, 'virtual', False)
            
            # Initialize the field data structure
            field_data = {
                'name': field_name,
                'label': getattr(field, 'label', field_name),
                'field_type': self._get_field_type_safe(field),
                'view_order': getattr(field, 'view_order', 0),
                'css_class': getattr(field, 'css_class', ''),
                'columns_span': getattr(field, 'columns_span', None),
                'help_text': getattr(field, 'help_text', None),
                'is_virtual': is_virtual,
                'is_custom_renderer': has_custom_renderer,
            }
            
            # Handle value based on field configuration
            # NEW: Check skip_custom_renderer flag
            if has_custom_renderer and not skip_custom_renderer:
                # Custom renderer fields - value comes from context function
                field_data['value'] = None  # Will be populated by renderer
                field_data['is_empty'] = False  # Custom renderers handle their own emptiness
                field_data['custom_renderer'] = self._extract_renderer_config(field)
            else:
                # Regular fields - get value from item
                raw_value = self._get_field_value(item, field_name)
                field_data['value'] = self._format_field_value(field, raw_value)
                field_data['is_empty'] = self._is_value_empty(raw_value)
                field_data['custom_renderer'] = None if skip_custom_renderer else self._extract_renderer_config(field) if has_custom_renderer else None
            
            # Add display conditions if configured
            if hasattr(field, 'conditional_display'):
                field_data['conditional_display'] = getattr(field, 'conditional_display')
            
            return field_data
            
        except Exception as e:
            logger.error(f"Error formatting field {getattr(field, 'name', 'unknown')}: {str(e)}")
            return self._get_error_field_format(field)

    def _should_display_field(self, field: FieldDefinition, item: Any, context: Optional[Dict] = None) -> bool:
        """
        Determine if field should be displayed based on configuration.
        Evaluates conditional_display if present.
        Entity-agnostic - works based on field configuration only.
        """
        # Check basic display flag
        if not getattr(field, 'show_in_detail', True):
            return False
        
        # Check conditional display if configured
        conditional = getattr(field, 'conditional_display', None)
        if not conditional:
            return True
        
        try:
            # Build evaluation context
            eval_context = {
                'item': item,
            }
            
            # Add additional context if provided
            if context:
                eval_context.update({
                    'user': context.get('user'),
                    'branch_id': context.get('branch_id'),
                    'hospital_id': context.get('hospital_id'),
                })
            
            # Simple evaluation - you might want to use a safer evaluator
            result = self._evaluate_condition(conditional, eval_context)
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Error evaluating condition for {getattr(field, 'name', 'unknown')}: {str(e)}")
            # Default to showing field if condition fails
            return True

    def _get_layout_type(self, config: EntityConfiguration) -> str:
        """Get layout type from configuration - FIXED VERSION"""
        try:
            if hasattr(config, 'view_layout') and config.view_layout:
                layout_type = config.view_layout.type
                
                # Handle the LayoutType enum properly
                if hasattr(layout_type, 'value'):
                    # This is an enum, get its value
                    result = layout_type.value
                elif hasattr(layout_type, 'name'):
                    # Fallback to name if value doesn't exist
                    result = layout_type.name.lower()
                else:
                    # Last resort - convert to string
                    result = str(layout_type).lower().replace('layouttype.', '')
                
                logger.info(f"[VIEW] Layout type for {config.entity_type}: '{result}'")
                return result
            else:
                logger.info(f"[VIEW] No view_layout found for {config.entity_type}, defaulting to simple")
                return 'simple'
                
        except Exception as e:
            logger.error(f"Error getting layout type: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return 'simple'

    def _get_button_css_class(self, button_type) -> str:
        """
        Get CSS class for button based on ButtonType
        Maps ButtonType enum values to CSS classes
        """
        try:
            if hasattr(button_type, 'value'):
                # ButtonType enum has the CSS class as its value
                return button_type.value
            else:
                # Fallback for string button types
                return f"btn-{str(button_type).lower()}"
        except Exception as e:
            logger.error(f"Error getting button CSS class: {str(e)}")
            return "btn-secondary"  # Safe default

    def _has_tabbed_layout(self, config: EntityConfiguration) -> bool:
        """Check if configuration uses tabbed layout"""
        try:
            if hasattr(config, 'view_layout') and config.view_layout:
                layout_type = config.view_layout.type
                
                # Check for tabbed layout properly
                if hasattr(layout_type, 'value'):
                    return layout_type.value == 'tabbed'
                elif hasattr(layout_type, 'name'):
                    return layout_type.name.lower() == 'tabbed'
                else:
                    return str(layout_type).lower() == 'tabbed'
            return False
        except:
            return False

    def _has_accordion_layout(self, config: EntityConfiguration) -> bool:
        """Check if using accordion layout"""
        return self._get_layout_type(config) == 'accordion'

    def _get_tab_label(self, tab_key: str, config: EntityConfiguration) -> str:
        """Get display label for tab - ONLY from configuration, no hardcoding"""
        if not tab_key:
            return 'Details'
        
        # Read ONLY from configuration
        if (hasattr(config, 'view_layout') and 
            config.view_layout and 
            hasattr(config.view_layout, 'tabs') and 
            config.view_layout.tabs):
            
            # tabs is a dict of TabDefinition objects
            tab_config = config.view_layout.tabs.get(tab_key)
            if tab_config and hasattr(tab_config, 'label'):
                return tab_config.label
        
        # Generic fallback - no hardcoded mappings!
        return str(tab_key).replace('_', ' ').title()

    def _get_tab_icon(self, tab_key: str, config: EntityConfiguration) -> str:
        """Get icon for tab - ONLY from configuration, no hardcoding"""
        if not tab_key:
            return 'fas fa-folder'
        
        # Read ONLY from configuration
        if (hasattr(config, 'view_layout') and 
            config.view_layout and 
            hasattr(config.view_layout, 'tabs') and 
            config.view_layout.tabs):
            
            # tabs is a dict of TabDefinition objects
            tab_config = config.view_layout.tabs.get(tab_key)
            if tab_config and hasattr(tab_config, 'icon'):
                return tab_config.icon
        
        # Generic fallback icon - no hardcoded mappings!
        return 'fas fa-folder'

    def _get_section_title(self, section_key: str, config: EntityConfiguration) -> str:
        """Get display title for section - ONLY from configuration"""
        if not section_key:
            return 'Information'
        
        # First check if there's a tab-specific section definition
        if (hasattr(config, 'view_layout') and 
            config.view_layout and 
            hasattr(config.view_layout, 'tabs') and 
            config.view_layout.tabs):
            
            # Look through all tabs for this section
            for tab_config in config.view_layout.tabs.values():
                if hasattr(tab_config, 'sections') and tab_config.sections:
                    section_config = tab_config.sections.get(section_key)
                    if section_config and hasattr(section_config, 'title'):
                        return section_config.title
        
        # Check global section definitions
        if hasattr(config, 'section_definitions') and config.section_definitions:
            section_config = config.section_definitions.get(section_key)
            if section_config and hasattr(section_config, 'title'):
                return section_config.title
        
        # Generic fallback - no hardcoded mappings!
        return str(section_key).replace('_', ' ').title()

    def _get_section_icon(self, section_key: str, config: EntityConfiguration) -> str:
        """Get icon for section - ONLY from configuration"""
        if not section_key:
            return 'fas fa-info-circle'
        
        # First check if there's a tab-specific section definition
        if (hasattr(config, 'view_layout') and 
            config.view_layout and 
            hasattr(config.view_layout, 'tabs') and 
            config.view_layout.tabs):
            
            # Look through all tabs for this section
            for tab_config in config.view_layout.tabs.values():
                if hasattr(tab_config, 'sections') and tab_config.sections:
                    section_config = tab_config.sections.get(section_key)
                    if section_config and hasattr(section_config, 'icon'):
                        return section_config.icon
        
        # Check global section definitions
        if hasattr(config, 'section_definitions') and config.section_definitions:
            section_config = config.section_definitions.get(section_key)
            if section_config and hasattr(section_config, 'icon'):
                return section_config.icon
        
        # Generic fallback icon
        return 'fas fa-info-circle'


    def _assemble_view_action_buttons(self, config: EntityConfiguration, item: Any, item_id: str) -> List[Dict]:
        """Assemble action buttons for view"""
        try:
            actions = []
            
            for action in config.actions:
                if action.show_in_detail:
                    # Check conditions
                    if action.conditions and not self._check_action_conditions(action, item):
                        continue
                    
                    # Convert item to dict if it's an object
                    item_dict = {}
                    if hasattr(item, '__dict__'):
                        item_dict = {key: getattr(item, key, None) for key in dir(item) 
                                    if not key.startswith('_') and not callable(getattr(item, key))}
                    else:
                        item_dict = item if isinstance(item, dict) else {}
                    
                    # Generate URL properly
                    url = action.get_url(item_dict, config)
                    
                    actions.append({
                        'id': action.id,
                        'label': action.label,
                        'icon': action.icon,
                        'url': url,
                        'button_type': action.button_type,
                        'css_class': f'btn-{action.button_type.value}',
                        'confirmation_required': action.confirmation_required,
                        'confirmation_message': action.confirmation_message,
                    })
            
            # ===== NEW CODE: ADD DOCUMENT BUTTONS =====
            # Check if documents are enabled for this entity
            if getattr(config, 'document_enabled', False):
                from app.engine.document_service import get_document_service
                doc_service = get_document_service()
                
                # Get document buttons
                document_buttons = doc_service.get_document_buttons(config, item_id)
                
                # Add document buttons to actions
                for doc_button in document_buttons:
                    # Check if it's a dropdown
                    if doc_button.get('type') == 'dropdown':
                        # Add as dropdown button
                        actions.append({
                            'id': doc_button.get('id'),
                            'label': doc_button.get('label'),
                            'icon': doc_button.get('icon'),
                            'type': 'dropdown',
                            'dropdown_items': doc_button.get('dropdown_items', []),
                            'css_class': doc_button.get('class', 'btn-outline dropdown-toggle')
                        })
                    else:
                        # Add as regular button
                        actions.append({
                            'id': doc_button.get('id'),
                            'label': doc_button.get('label'),
                            'icon': doc_button.get('icon'),
                            'url': doc_button.get('url'),
                            'target': doc_button.get('target', '_blank'),
                            'css_class': doc_button.get('class', 'btn-outline')
                        })
            # ===== END NEW CODE =====

            # Default actions if none configured
            if not actions:
                actions.extend([
                    {
                        'id': 'back',
                        'label': f'Back to {config.plural_name}',
                        'icon': 'fas fa-arrow-left',
                        'url': f'/universal/{config.entity_type}/list',
                        'css_class': 'universal-action-btn btn-secondary'
                    },
                    {
                        'id': 'edit',
                        'label': f'Edit {config.name}',
                        'icon': 'fas fa-edit',
                        'url': f'/universal/{config.entity_type}/edit/{item_id}',
                        'css_class': 'universal-action-btn btn-warning'
                    }
                ])
            
            return actions
            
        except Exception as e:
            logger.error(f"Error assembling action buttons: {str(e)}")
            return []

    def _build_view_breadcrumbs(self, config: EntityConfiguration, item: Any) -> List[Dict]:
        """
        Build breadcrumb navigation
        """
        try:
            return [
                {'label': 'Dashboard', 'url': '/dashboard'},
                {'label': config.plural_name, 'url': f'/universal/{config.entity_type}/list'},
                {'label': str(getattr(item, config.title_field, 'Details')), 'url': '#'}
            ]
        except:
            return []
        
    def _create_fallback_sections(self, detail_fields: List[FieldDefinition], item: Any, config: EntityConfiguration) -> List[Dict]:
        """
        Create fallback sections when normal assembly fails
        Minimal implementation to fix the missing method error
        """
        try:
            # Create a single section with all available fields
            section = {
                'key': 'details',
                'title': 'Details',
                'icon': 'fas fa-info-circle',
                'columns': 2,
                'fields': []
            }
            
            # Use existing fields if available
            if detail_fields:
                for field in detail_fields:
                    if getattr(field, 'show_in_detail', True):
                        section['fields'].append(self._format_field_for_view(field, item))
            
            # Return in the expected format (list of tabs with sections)
            return [{
                'key': 'simple',
                'label': f'{config.name} Details',
                'icon': config.icon,
                'sections': [section]
            }]
            
        except Exception as e:
            logger.error(f"Error in fallback section creation: {str(e)}")
            # Ultimate fallback - empty structure
            return [{
                'key': 'error',
                'label': 'Error',
                'icon': 'fas fa-exclamation-triangle',
                'sections': []
            }]

    def _field_has_custom_renderer(self, field: FieldDefinition) -> bool:
        """
        Check if field has a custom renderer - configuration-based only.
        No entity-specific checks!
        """
        return (
            hasattr(field, 'custom_renderer') and 
            field.custom_renderer is not None
        )

    def _extract_renderer_config(self, field: FieldDefinition) -> Optional[Dict]:
        """
        Extract custom renderer configuration in a generic way.
        Works for ANY field with a custom_renderer attribute.
        """
        if not self._field_has_custom_renderer(field):
            return None
        
        renderer = field.custom_renderer
        config = {}
        
        # Template is required
        if hasattr(renderer, 'template'):
            config['template'] = renderer.template
        else:
            logger.warning(f"Custom renderer for {field.name} missing template")
            return None
        
        # Extract context_function and ensure it's a string
        if hasattr(renderer, 'context_function'):
            context_func = renderer.context_function
            if context_func:
                # Convert to string if it's a callable
                if callable(context_func):
                    config['context_function'] = context_func.__name__
                    logger.debug(f"Converted callable to string: {context_func.__name__}")
                else:
                    config['context_function'] = str(context_func)
            else:
                config['context_function'] = None
        
        # Extract CSS classes
        if hasattr(renderer, 'css_classes'):
            config['css_classes'] = renderer.css_classes or ''
        
        # Extract JavaScript if present
        if hasattr(renderer, 'javascript'):
            config['javascript'] = renderer.javascript
        
        # Extract any other renderer properties dynamically
        # This makes it future-proof for new properties
        for attr_name in dir(renderer):
            if not attr_name.startswith('_') and attr_name not in ['template', 'context_function', 'css_classes', 'javascript']:
                attr_value = getattr(renderer, attr_name, None)
                if attr_value is not None:
                    config[attr_name] = attr_value
        
        return config

    def _get_field_value(self, item: Any, field_name: str) -> Any:
        """
        Get field value from item - works with dict or object.
        Entity-agnostic value extraction.
        """
        if isinstance(item, dict):
            return item.get(field_name)
        else:
            return getattr(item, field_name, None)

    def _is_value_empty(self, value: Any) -> bool:
        """
        Check if a value should be considered empty.
        Generic check that works for any data type.
        """
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (list, dict)) and not value:
            return True
        if isinstance(value, (int, float)) and value == 0:
            # Consider 0 as non-empty for numbers (it's a valid value)
            return False
        return False

    def _safe_string_convert(self, value: Any) -> str:
        """
        Safely convert any value to string.
        Handles callables, None, and other types.
        """
        if value is None:
            return None
        if callable(value):
            return value.__name__ if hasattr(value, '__name__') else str(value)
        return str(value)

# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS (STANDALONE)
# =============================================================================

def assemble_complex_list_data(config: EntityConfiguration, raw_data: Dict, 
                              form_instance: Optional[FlaskForm] = None) -> Dict:
    """
    🔄 LEGACY COMPATIBILITY: Standalone function maintained for backward compatibility
    DEPRECATED: Use EnhancedUniversalDataAssembler().assemble_complex_list_data() instead
    """
    logger.warning("DEPRECATED: Using standalone assemble_complex_list_data function. "
                  "Use EnhancedUniversalDataAssembler class instead.")
    
    assembler = EnhancedUniversalDataAssembler()
    return assembler.assemble_complex_list_data(config, raw_data, form_instance)

# =============================================================================
# MIGRATION GUIDANCE FUNCTION
# =============================================================================

def check_deprecated_usage():
    """
    Function to help identify deprecated usage patterns
    Run this in development to find code that needs updating
    """
    import inspect
    import warnings
    
    # This would log all deprecated method calls
    # Useful for identifying code that needs migration
    warnings.filterwarnings("default", category=DeprecationWarning)
    
    print("🔍 Deprecated usage checker enabled")
    print("   - Watch logs for DEPRECATED warnings")
    print("   - Update calling code to use UniversalFilterService directly")
    print("   - Remove compatibility wrappers once migration complete")