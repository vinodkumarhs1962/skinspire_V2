# =============================================================================
# UNIVERSAL SERVICE LAYER - INTEGRATED WITH EXISTING SERVICES
# Following SkinSpire HMS Existing Service Patterns
# =============================================================================

# =============================================================================
# FILE: app/services/universal_search_service.py
# PURPOSE: Universal search service that delegates to your existing services
# =============================================================================

from typing import Dict, Any, List, Optional, Tuple
from flask import current_app
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import Query

# Import your existing services and patterns
from app.services.database_service import get_db_session
from app.services.supplier_service import search_supplier_invoices  # Your existing function
from app.config.entity_configurations import EntityConfiguration, EntityType, FieldType
from app.core.entity_registry import EntityConfigurationRegistry

class UniversalSearchService:
    """Universal search service that integrates with your existing services"""
    
    def __init__(self, entity_config: EntityConfiguration):
        self.config = entity_config
        self.entity_type = entity_config.entity_type
        self.model_class = entity_config.model_class
    
    def search(self, filters: Dict[str, Any], page: int = 1, per_page: int = 25) -> Dict[str, Any]:
        """
        Universal search method that delegates to existing services where available
        """
        try:
            # Delegate to your existing service methods where they exist
            if self.entity_type == EntityType.SUPPLIER_INVOICE:
                return self._search_supplier_invoices(filters, page, per_page)
            elif self.entity_type == EntityType.SUPPLIER:
                return self._search_suppliers(filters, page, per_page)
            elif self.entity_type == EntityType.PATIENT:
                return self._search_patients(filters, page, per_page)
            else:
                # Universal implementation for new entities
                return self._universal_search(filters, page, per_page)
                
        except Exception as e:
            current_app.logger.error(f"Search error for {self.entity_type.value}: {str(e)}", exc_info=True)
            return self._empty_result()
    
    def _search_supplier_invoices(self, filters: Dict[str, Any], page: int, per_page: int) -> Dict[str, Any]:
        """Delegate to your existing supplier invoice search"""
        
        # Map universal filters to your existing search_supplier_invoices parameters
        try:
            # Use your existing search function
            result = search_supplier_invoices(
                hospital_id=filters.get('hospital_id'),
                branch_id=filters.get('branch_id'),
                supplier_id=filters.get('supplier_id'),
                invoice_number=filters.get('invoice_number'),
                po_number=filters.get('po_number'),
                payment_status=filters.get('payment_status'),
                start_date=filters.get('start_date'),
                end_date=filters.get('end_date'),
                page=page,
                per_page=per_page
            )
            
            # Convert to universal format if needed
            return self._standardize_result(result)
            
        except Exception as e:
            current_app.logger.error(f"Supplier invoice search error: {str(e)}", exc_info=True)
            return self._empty_result()
    
    def _search_suppliers(self, filters: Dict[str, Any], page: int, per_page: int) -> Dict[str, Any]:
        """Search suppliers using your existing patterns"""
        
        with get_db_session() as session:
            try:
                # Use your existing model and query patterns
                query = session.query(self.model_class)
                
                # Apply your existing hospital and branch filtering
                if filters.get('hospital_id'):
                    query = query.filter(self.model_class.hospital_id == filters['hospital_id'])
                
                if filters.get('branch_id'):
                    query = query.filter(self.model_class.branch_id == filters['branch_id'])
                
                # Apply search filters
                search_term = filters.get('search')
                if search_term:
                    search_conditions = []
                    for field_name in self.config.default_search_fields:
                        if hasattr(self.model_class, field_name):
                            field = getattr(self.model_class, field_name)
                            search_conditions.append(field.ilike(f'%{search_term}%'))
                    
                    if search_conditions:
                        query = query.filter(or_(*search_conditions))
                
                # Apply specific field filters
                for field in self.config.fields:
                    if field.filterable and field.name in filters:
                        filter_value = filters[field.name]
                        if filter_value and hasattr(self.model_class, field.name):
                            model_field = getattr(self.model_class, field.name)
                            
                            if field.field_type == FieldType.SELECT:
                                query = query.filter(model_field == filter_value)
                            elif field.field_type == FieldType.DATE_RANGE:
                                # Handle date range filtering
                                if 'start_date' in filters and 'end_date' in filters:
                                    query = query.filter(
                                        and_(
                                            model_field >= filters['start_date'],
                                            model_field <= filters['end_date']
                                        )
                                    )
                            else:
                                query = query.filter(model_field.ilike(f'%{filter_value}%'))
                
                # Apply sorting
                sort_field = filters.get('sort_field', self.config.display.default_sort_field)
                sort_order = filters.get('sort_order', self.config.display.default_sort_order)
                
                if sort_field and hasattr(self.model_class, sort_field):
                    model_field = getattr(self.model_class, sort_field)
                    if sort_order == 'desc':
                        query = query.order_by(desc(model_field))
                    else:
                        query = query.order_by(asc(model_field))
                
                # Get total count
                total = query.count()
                
                # Apply pagination
                offset = (page - 1) * per_page
                items = query.offset(offset).limit(per_page).all()
                
                # Convert to dictionaries for template rendering
                items_data = []
                for item in items:
                    item_dict = {}
                    for field in self.config.fields:
                        if hasattr(item, field.name):
                            value = getattr(item, field.name)
                            item_dict[field.name] = self._format_field_value(value, field)
                    
                    # Add primary key
                    item_dict[self.config.primary_key] = getattr(item, self.config.primary_key)
                    items_data.append(item_dict)
                
                return {
                    'items': items_data,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page,
                    'has_prev': page > 1,
                    'has_next': page < ((total + per_page - 1) // per_page),
                    'prev_num': page - 1 if page > 1 else None,
                    'next_num': page + 1 if page < ((total + per_page - 1) // per_page) else None
                }
                
            except Exception as e:
                current_app.logger.error(f"Supplier search error: {str(e)}", exc_info=True)
                return self._empty_result()
    
    def _search_patients(self, filters: Dict[str, Any], page: int, per_page: int) -> Dict[str, Any]:
        """Search patients - placeholder for your existing patient service integration"""
        
        # TODO: Integrate with your existing patient service when available
        # For now, use universal implementation
        return self._universal_search(filters, page, per_page)
    
    def _universal_search(self, filters: Dict[str, Any], page: int, per_page: int) -> Dict[str, Any]:
        """Universal search implementation for entities without existing services"""
        
        with get_db_session() as session:
            try:
                # Build query using your existing database session pattern
                query = session.query(self.model_class)
                
                # Apply hospital/branch filtering (following your existing pattern)
                if hasattr(self.model_class, 'hospital_id') and filters.get('hospital_id'):
                    query = query.filter(self.model_class.hospital_id == filters['hospital_id'])
                
                if hasattr(self.model_class, 'branch_id') and filters.get('branch_id'):
                    query = query.filter(self.model_class.branch_id == filters['branch_id'])
                
                # Apply search and filters using configuration
                query = self._apply_search_filters(query, filters)
                query = self._apply_field_filters(query, filters) 
                query = self._apply_sorting(query, filters)
                
                # Get results with pagination
                total = query.count()
                offset = (page - 1) * per_page
                items = query.offset(offset).limit(per_page).all()
                
                # Format results for template rendering
                items_data = [self._format_item(item) for item in items]
                
                return {
                    'items': items_data,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page,
                    'has_prev': page > 1,
                    'has_next': page < ((total + per_page - 1) // per_page),
                    'prev_num': page - 1 if page > 1 else None,
                    'next_num': page + 1 if page < ((total + per_page - 1) // per_page) else None
                }
                
            except Exception as e:
                current_app.logger.error(f"Universal search error: {str(e)}", exc_info=True)
                return self._empty_result()
    
    def _apply_search_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """Apply search term filtering"""
        search_term = filters.get('search')
        if not search_term:
            return query
        
        search_conditions = []
        for field_name in self.config.default_search_fields:
            if hasattr(self.model_class, field_name):
                field = getattr(self.model_class, field_name)
                search_conditions.append(field.ilike(f'%{search_term}%'))
        
        if search_conditions:
            query = query.filter(or_(*search_conditions))
        
        return query
    
    def _apply_field_filters(self, query: Query, filters: Dict[str, Any]) -> Query:
        """Apply individual field filters"""
        for field in self.config.fields:
            if not field.filterable or field.name not in filters:
                continue
                
            filter_value = filters[field.name]
            if not filter_value or not hasattr(self.model_class, field.name):
                continue
                
            model_field = getattr(self.model_class, field.name)
            
            if field.field_type == FieldType.SELECT:
                query = query.filter(model_field == filter_value)
            elif field.field_type == FieldType.STATUS_BADGE:
                query = query.filter(model_field == filter_value)
            elif field.field_type in [FieldType.TEXT, FieldType.GST_NUMBER, FieldType.PAN_NUMBER]:
                query = query.filter(model_field.ilike(f'%{filter_value}%'))
            elif field.field_type == FieldType.DATE:
                # Handle date filtering
                query = query.filter(model_field == filter_value)
        
        return query
    
    def _apply_sorting(self, query: Query, filters: Dict[str, Any]) -> Query:
        """Apply sorting to query"""
        sort_field = filters.get('sort_field', self.config.display.default_sort_field)
        sort_order = filters.get('sort_order', self.config.display.default_sort_order)
        
        if sort_field and hasattr(self.model_class, sort_field):
            model_field = getattr(self.model_class, sort_field)
            if sort_order == 'desc':
                query = query.order_by(desc(model_field))
            else:
                query = query.order_by(asc(model_field))
        
        return query
    
    def _format_item(self, item) -> Dict[str, Any]:
        """Format database item for template rendering"""
        item_dict = {}
        
        # Add primary key
        item_dict[self.config.primary_key] = getattr(item, self.config.primary_key)
        
        # Add configured fields
        for field in self.config.fields:
            if hasattr(item, field.name):
                value = getattr(item, field.name)
                item_dict[field.name] = self._format_field_value(value, field)
        
        # Add title and subtitle fields
        if hasattr(item, self.config.title_field):
            item_dict['_title'] = getattr(item, self.config.title_field)
        
        if self.config.subtitle_field and hasattr(item, self.config.subtitle_field):
            item_dict['_subtitle'] = getattr(item, self.config.subtitle_field)
        
        return item_dict
    
    def _format_field_value(self, value, field) -> Any:
        """Format field value for display"""
        if value is None:
            return ""
        
        if field.field_type == FieldType.DATE:
            return value.strftime('%Y-%m-%d') if hasattr(value, 'strftime') else str(value)
        elif field.field_type == FieldType.DATETIME:
            return value.strftime('%Y-%m-%d %H:%M') if hasattr(value, 'strftime') else str(value)
        elif field.field_type == FieldType.AMOUNT:
            return float(value) if value else 0.0
        elif field.field_type == FieldType.BOOLEAN:
            return bool(value)
        else:
            return str(value)
    
    def _standardize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize result format from existing services"""
        # If your existing service returns different format, convert here
        return result
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result on error"""
        return {
            'items': [],
            'total': 0,
            'page': 1,
            'per_page': 25,
            'pages': 0,
            'has_prev': False,
            'has_next': False,
            'prev_num': None,
            'next_num': None
        }

# =============================================================================
# FILE: app/services/universal_list_service.py 
# PURPOSE: Universal list rendering service
# =============================================================================

from typing import Dict, Any, List
from app.config.entity_configurations import EntityConfiguration

class UniversalListService:
    """Service for universal list rendering and formatting"""
    
    def __init__(self, entity_config: EntityConfiguration):
        self.config = entity_config
    
    def prepare_list_data(self, search_result: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for list template rendering"""
        
        # Get list fields (fields marked for list display)
        list_fields = [field for field in self.config.fields if field.show_in_list]
        
        # Prepare action buttons
        actions = self._prepare_actions()
        
        # Prepare filter options
        filter_options = self._prepare_filter_options()
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_stats(search_result)
        
        return {
            'config': self.config,
            'items': search_result['items'],
            'pagination': {
                'total': search_result['total'],
                'page': search_result['page'],
                'per_page': search_result['per_page'],
                'pages': search_result['pages'],
                'has_prev': search_result['has_prev'],
                'has_next': search_result['has_next'],
                'prev_num': search_result['prev_num'],
                'next_num': search_result['next_num']
            },
            'list_fields': list_fields,
            'actions': actions,
            'filter_options': filter_options,
            'summary_stats': summary_stats,
            'active_filters': filters
        }
    
    def _prepare_actions(self) -> List[Dict[str, Any]]:
        """Prepare action buttons for list"""
        return [action.to_dict() for action in self.config.actions]
    
    def _prepare_filter_options(self) -> Dict[str, List[Dict[str, Any]]]:
        """Prepare filter options for search form"""
        filter_options = {}
        
        for field in self.config.fields:
            if field.filterable and field.options:
                filter_options[field.name] = field.options
        
        return filter_options
    
    def _calculate_summary_stats(self, search_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics for the list"""
        total_items = search_result['total']
        
        # Basic stats
        stats = {
            'total_count': total_items,
            'filtered_count': len(search_result['items']),
            'page_count': search_result['pages']
        }
        
        # Entity-specific stats can be added here
        if self.config.entity_type == EntityType.SUPPLIER_INVOICE:
            stats.update(self._calculate_invoice_stats(search_result['items']))
        
        return stats
    
    def _calculate_invoice_stats(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate invoice-specific statistics"""
        if not items:
            return {}
        
        total_amount = sum(float(item.get('total_amount', 0)) for item in items)
        pending_count = sum(1 for item in items if item.get('payment_status') == 'pending')
        
        return {
            'total_amount': total_amount,
            'pending_count': pending_count,
            'average_amount': total_amount / len(items) if items else 0
        }

# =============================================================================
# FILE: app/services/entity_integration_service.py
# PURPOSE: Integration service for connecting universal architecture with existing services
# =============================================================================

from typing import Dict, Any, Optional, Type
from app.config.entity_configurations import EntityType
from app.services.universal_search_service import UniversalSearchService
from app.services.universal_list_service import UniversalListService

class EntityIntegrationService:
    """Service for integrating universal architecture with existing services"""
    
    @staticmethod
    def get_entity_service(entity_type: EntityType) -> Optional[Type]:
        """Get the appropriate service class for an entity type"""
        
        service_map = {
            EntityType.SUPPLIER: 'SupplierService',
            EntityType.SUPPLIER_INVOICE: 'SupplierService', 
            EntityType.PATIENT: 'PatientService',
            EntityType.MEDICINE: 'MedicineService',
            # Add more mappings as needed
        }
        
        service_name = service_map.get(entity_type)
        if service_name:
            # Dynamically import and return service class
            try:
                module = __import__(f'app.services.{service_name.lower()}', fromlist=[service_name])
                return getattr(module, service_name)
            except (ImportError, AttributeError):
                return None
        
        return None
    
    @staticmethod
    def get_search_service(entity_config) -> UniversalSearchService:
        """Get universal search service for entity"""
        return UniversalSearchService(entity_config)
    
    @staticmethod
    def get_list_service(entity_config) -> UniversalListService:
        """Get universal list service for entity"""
        return UniversalListService(entity_config)
    
    @staticmethod
    def handle_custom_action(entity_type: EntityType, action_id: str, entity_id: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom actions for specific entity types"""
        
        if entity_type == EntityType.SUPPLIER_INVOICE and action_id == 'payment':
            # Delegate to existing payment handling
            return {
                'redirect_url': f'/supplier/payment/record/{entity_id}',
                'success': True
            }
        elif entity_type == EntityType.PATIENT and action_id == 'appointments':
            # Delegate to existing appointment handling
            return {
                'redirect_url': f'/patient/{entity_id}/appointments',
                'success': True
            }
        
        # Default action handling
        return {
            'redirect_url': f'/universal/{entity_type.value}/{entity_id}',
            'success': True
        }

# =============================================================================
# USAGE EXAMPLES AND INTEGRATION PATTERNS
# =============================================================================

"""
Example usage in your views:

# app/views/universal_views.py
from app.services.universal_search_service import UniversalSearchService
from app.services.universal_list_service import UniversalListService
from app.core.entity_registry import EntityConfigurationRegistry

@universal_bp.route('/<entity_type>')
@login_required
def entity_list(entity_type):
    # Get entity configuration
    config = EntityConfigurationRegistry.get_config(EntityType(entity_type))
    
    # Use universal search service (delegates to your existing services)
    search_service = UniversalSearchService(config)
    search_result = search_service.search(request.args.to_dict())
    
    # Use universal list service for formatting
    list_service = UniversalListService(config)
    template_data = list_service.prepare_list_data(search_result, request.args.to_dict())
    
    return render_template('pages/universal/entity_list.html', **template_data)

Example integration with your existing supplier views:

# app/views/supplier_views.py (add this alongside existing routes)
@supplier_views_bp.route('/invoices/universal', methods=['GET'])
@login_required
@require_web_branch_permission('supplier_invoice', 'view')
def supplier_invoice_list_universal():
    config = EntityConfigurationRegistry.get_config(EntityType.SUPPLIER_INVOICE)
    search_service = UniversalSearchService(config)
    
    # This will automatically use your existing search_supplier_invoices function
    search_result = search_service.search({
        'hospital_id': current_user.hospital_id,
        **request.args.to_dict()
    })
    
    list_service = UniversalListService(config)
    template_data = list_service.prepare_list_data(search_result, request.args.to_dict())
    
    return render_template('pages/universal/entity_list.html', **template_data)
"""