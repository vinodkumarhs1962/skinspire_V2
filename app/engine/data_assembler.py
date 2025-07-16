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

from app.config.entity_configurations import EntityConfiguration
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
        🎯 MAIN ASSEMBLY METHOD - Now uses UniversalFilterService
        BACKWARD COMPATIBLE: Same signature, enhanced functionality
        """
        try:
            logger.info(f"🔧 Assembling data for {config.entity_type}")
            
            # Get current filters
            current_filters = filters or (request.args.to_dict() if request else {})
            
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
            
            # ✅ USE UNIFIED FILTER SERVICE - New approach
            try:
                filter_data = self.filter_service.get_complete_filter_data(
                    entity_type=config.entity_type,
                    hospital_id=current_user.hospital_id if current_user else None,
                    branch_id=branch_context.get('branch_id') if branch_context else None,
                    current_filters=current_filters
                )
            except Exception as e:
                logger.error(f"Filter service failed, using fallback: {str(e)}")
                # ✅ FALLBACK: Use old method if new service fails
                filter_data = self._assemble_enhanced_filter_form_fallback(config, current_filters)
            
            # ✅ CRITICAL FIX: Merge summary data from filter service with raw data
            if filter_data.get('summary_data') and raw_data.get('summary'):
                logger.info(f"[SUMMARY_MERGE] Merging filter service summary data with existing summary")
                existing_summary = raw_data.get('summary', {})
                filter_summary = filter_data.get('summary_data', {})
                
                # Preserve all existing fields and add missing ones from filter service
                merged_summary = existing_summary.copy()
                for key, value in filter_summary.items():
                    if key not in merged_summary or merged_summary[key] == 0:
                        merged_summary[key] = value
                        logger.info(f"[SUMMARY_MERGE] Added missing field {key} = {value}")
                
                raw_data['summary'] = merged_summary
                logger.info(f"[SUMMARY_MERGE] Final merged summary: {list(merged_summary.keys())}")

            template_safe_config = self._make_template_safe_config(config)
            # Assemble other data components
            
            # ✅ FIX: Use filtered count from summary for total_count
            summary = raw_data.get('summary', {})
            if summary and 'total_count' in summary:
                total_count = summary['total_count']  # Use filtered count
                logger.info(f"🔍 [TOTAL_COUNT_FIX] Using filtered total_count: {total_count}")
            else:
                total_count = raw_data.get('total', len(raw_data.get('items', [])))
                logger.info(f"🔍 [TOTAL_COUNT_FIX] Using fallback total_count: {total_count}")
            
            assembled_data = {
                # Core data
                'items': raw_data.get('items', []),
                'total_count': total_count,
                
                # Configuration
                'entity_config': template_safe_config,  # ✅ Template-safe dict
                'entity_type': config.entity_type,
                
                # ✅ FILTER DATA - From unified service or fallback
                'filter_data': filter_data,
                # ✅ FIXED: Merge processed filter data with current filters for template compatibility
               'filters': current_filters,  # This only contains request args 
                
                # Table structure
                'table_columns': self._assemble_table_columns(config),
                'table_data': self._assemble_table_data(config, raw_data.get('items', [])),
                
                # ✅ Summary cards from configuration using existing backend method
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
                'has_errors': filter_data.get('has_errors', False),
                'error_messages': filter_data.get('error_messages', [])
            }
            
            logger.info(f"✅ Assembled data for {config.entity_type}: "
                       f"{assembled_data['total_count']} items, "
                       f"{filter_data.get('active_filters_count', 0)} active filters")
            
            return assembled_data
            
        except Exception as e:
            logger.error(f"❌ Error assembling data for {config.entity_type}: {str(e)}")
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
                    column = {
                        'name': field.name,
                        'label': field.label,
                        'sortable': getattr(field, 'sortable', False),
                        'css_class': getattr(field, 'css_class', ''),
                        'width': getattr(field, 'width', 'auto'),
                        'align': getattr(field, 'align', 'left'),
                        'field_type': self._get_field_type_safe(field)
                    }
                    columns.append(column)
            
            return columns
            
        except Exception as e:
            logger.error(f"Error assembling table columns: {str(e)}")
            return []

    def _assemble_table_data(self, config: EntityConfiguration, items: List[Dict]) -> List[Dict]:
        """Assemble table data from raw items"""
        try:
            if not items:
                return []
            
            table_data = []
            
            for item in items:
                row_data = {}
                
                # Process each field
                for field in config.fields:
                    if getattr(field, 'show_in_list', False):
                        raw_value = item.get(field.name)
                        row_data[field.name] = self._format_field_value(field, raw_value)
                
                # Add row metadata
                row_data['_row_id'] = item.get(config.primary_key)
                row_data['_row_actions'] = self._build_row_actions(config, item)
                
                table_data.append(row_data)
            
            return table_data
            
        except Exception as e:
            logger.error(f"Error assembling table data: {str(e)}")
            return []

    def _format_field_value(self, field, raw_value) -> str:
        """Format field value for display"""
        try:
            if raw_value is None:
                return '—'
            
            field_type = self._get_field_type_safe(field)
            
            if field_type == 'date':
                if isinstance(raw_value, (date, datetime)):
                    return raw_value.strftime('%b %d, %Y')
                elif isinstance(raw_value, str):
                    try:
                        date_obj = datetime.strptime(raw_value, '%Y-%m-%d').date()
                        return date_obj.strftime('%b %d, %Y')
                    except:
                        return raw_value
            
            elif field_type in ['currency', 'amount']:
                try:
                    amount = float(raw_value)
                    return f"₹{amount:,.2f}"
                except:
                    return str(raw_value)
            
            elif field_type == 'status_badge':
                return self._format_status_badge(field, raw_value)
            
            return str(raw_value)
            
        except Exception as e:
            logger.error(f"Error formatting field value: {str(e)}")
            return str(raw_value) if raw_value is not None else '—'

    def _format_status_badge(self, field, value) -> Dict:
        """Format status badge with CSS class"""
        try:
            if hasattr(field, 'options') and field.options:
                for option in field.options:
                    if option.get('value') == value:
                        return {
                            'text': option.get('label', value),
                            'css_class': option.get('css_class', 'status-default')
                        }
            
            return {
                'text': str(value).title(),
                'css_class': 'status-default'
            }
            
        except Exception as e:
            logger.error(f"Error formatting status badge: {str(e)}")
            return {'text': str(value), 'css_class': 'status-default'}

    def _assemble_summary_data(self, config: EntityConfiguration, raw_data: Dict) -> Dict:
        """Assemble summary data from raw data"""
        try:
            logger.info(f"[ASSEMBLER_SUMMARY_DEBUG] Raw data keys: {list(raw_data.keys())}")
            logger.info(f"[ASSEMBLER_SUMMARY_DEBUG] Raw summary: {raw_data.get('summary', {})}")
            
            summary = raw_data.get('summary', {})
            
            logger.info(f"[ASSEMBLER_SUMMARY_DEBUG] Summary after extraction: {summary}")
            # Add computed summary if not provided
            items = raw_data.get('items', [])
            
            if not summary and items:
                summary = {
                    'total_count': len(items),
                    'current_page_count': len(items)
                }
                logger.info(f"[ASSEMBLER_SUMMARY_DEBUG] Created fallback summary: {summary}")

            # Add summary cards configuration
            summary['cards'] = getattr(config, 'summary_cards', [])
            
            logger.info(f"[ASSEMBLER_SUMMARY_DEBUG] Final assembled summary: {summary}")

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
                logger.info(f"🔍 [PAGINATION_FIX] Using filtered count from summary: {filtered_total}")
                
                # Update existing pagination with filtered count
                if pagination:
                    current_page = pagination.get('page', 1)
                    per_page = pagination.get('per_page', 20)
                    
                    pagination.update({
                        'total_count': filtered_total,
                        'total_pages': max(1, (filtered_total + per_page - 1) // per_page)
                    })
                    logger.info(f"🔍 [PAGINATION_FIX] Updated existing pagination with filtered total: {filtered_total}")
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
                logger.info(f"🔍 [PAGINATION_FIX] Using fallback count: {total_items}")
                    
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
            # ✅ DEBUG: Add these 4 lines to see what's happening
            print(f"🔍 [SUMMARY_CARDS_DEBUG] Entity: {config.entity_type}")
            print(f"🔍 [SUMMARY_CARDS_DEBUG] Raw data keys: {list(raw_data.keys())}")
            print(f"🔍 [SUMMARY_CARDS_DEBUG] Summary data: {raw_data.get('summary', {})}")
            print(f"🔍 [SUMMARY_CARDS_DEBUG] Config has {len(config.summary_cards)} cards configured")
            summary_data = raw_data.get('summary', {})
            cards = []
            
           
            # ✅ VALIDATION: Ensure config has summary_cards
            if not hasattr(config, 'summary_cards') or not config.summary_cards:
                logger.warning(f"No summary_cards configuration for {config.entity_type}")
                return []
            
            logger.info(f"✅ Assembling {len(config.summary_cards)} summary cards for {config.entity_type}")
            logger.info(f"✅ Summary data available: {list(summary_data.keys())}")
            
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
                        logger.info(f"✅ Created detail card '{card['id']}' with breakdown data from service: {breakdown_data}")
                        continue


                    # Get raw value from summary data
                    field_name = card_config.get('field', '')
                    raw_value = summary_data.get(field_name, 0)
                    
                    # ✅ FIX: Log missing fields but continue processing
                    if raw_value == 0 and field_name not in summary_data:
                        logger.warning(f"[WARNING]  Card {field_name}: field '{field_name}' missing from summary, using default value 0")

                    logger.info(f"✅ Card {card_config.get('id', field_name)}: field={field_name}, raw_value={raw_value}")
                    
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
                    logger.info(f"✅ Created card: {card['label']} = {card['value']}")
                    
                except Exception as card_error:
                    logger.error(f"❌ Error processing summary card {card_config}: {str(card_error)}")
                    # Continue with other cards even if one fails
                    continue
            
            logger.info(f"✅ Successfully assembled {len(cards)} summary cards for {config.entity_type}")
            print(f"🔍 [SUMMARY_CARDS_DEBUG] Created {len(cards)} cards")
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
                'actions': list(getattr(config, 'actions', [])),  # ✅ Convert to list
                'fields': list(getattr(config, 'fields', [])),    # ✅ Convert to list
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