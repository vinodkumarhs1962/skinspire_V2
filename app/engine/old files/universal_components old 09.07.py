"""
Universal components that work for all entities through configuration
"""

from typing import Dict, Any, List, Optional
from flask import request, current_app
from flask_login import current_user 
from app.engine.data_assembler import EnhancedUniversalDataAssembler as DataAssembler

class UniversalListService:
    """Universal list service that works for ALL entities through configuration"""
    """DEPRECATE: Functionality moved to enhanced universal_views.py"""
    
    def __init__(self, config):
        self.config = config
        self.data_assembler = DataAssembler()
    
    def get_list_data(self, **kwargs):
        """Get assembled list data using service integration"""
        from app.engine.service_integration import UniversalServiceAdapter
        
        # Get raw data from existing services
        adapter = UniversalServiceAdapter()
        raw_data = adapter.get_data_for_entity(
            entity_type=self.config.entity_type,
            **kwargs
        )
        
        # Assemble UI data using your DataAssembler
        from app.engine.data_assembler import EnhancedUniversalDataAssembler as DataAssembler
        assembler = DataAssembler()
        
        assembled_data = assembler.assemble_list_data(
            config=self.config,
            raw_data=raw_data,
            filters=kwargs.get('filters', {})
        )
        
        return assembled_data
    
    def _extract_filters(self) -> Dict[str, Any]:
        """Extract and validate filters from request"""
        filters = {
            'hospital_id': getattr(current_user, 'hospital_id', None),
            'page': int(request.args.get('page', 1)),
            'per_page': int(request.args.get('per_page', self.config.items_per_page)),
            'search': request.args.get('search'),
            'sort_field': request.args.get('sort_field', self.config.default_sort_field),
            'sort_order': request.args.get('sort_order', self.config.default_sort_order)
        }
        
        # Add field-specific filters based on configuration
        for field in self.config.fields:
            if field.filterable:
                filter_value = request.args.get(field.name)
                if filter_value:
                    filters[field.name] = filter_value
        
        # Add date range filters
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        # Remove None values
        return {k: v for k, v in filters.items() if v is not None and v != ''}
    
    def _get_raw_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get raw data using appropriate entity service"""
        from app.engine import universal_view_engine
        
        # Get entity service through universal view engine
        entity_service = universal_view_engine.get_entity_service(self.config.entity_type)
        
        # Call appropriate service method based on entity type
        if hasattr(entity_service, 'search_payments'):
            return entity_service.search_payments(filters)
        elif hasattr(entity_service, 'search_invoices'):
            return entity_service.search_invoices(filters)
        elif hasattr(entity_service, 'search_patients'):
            return entity_service.search_patients(filters)
        elif hasattr(entity_service, 'search'):
            return entity_service.search(filters)
        else:
            raise AttributeError(f"No search method found for service: {type(entity_service)}")

class UniversalDetailService:
    """Universal detail service that works for ALL entities through configuration"""
    """DEPRECATE: Functionality moved to enhanced universal_views.py"""
    
    def __init__(self, config):
        self.config = config
        self.data_assembler = DataAssembler()
    
    def get_detail_data(self, entity_id: str) -> Dict[str, Any]:
        """Get complete detail data assembled for frontend display"""
        try:
            # Get raw entity data
            raw_data = self._get_raw_entity_data(entity_id)
            
            if not raw_data:
                return None
            
            # Get related data if configured
            related_data = self._get_related_data(entity_id, raw_data)
            
            # Assemble complete UI data structure
            assembled_data = self.data_assembler.assemble_detail_data(
                self.config, raw_data, related_data
            )
            
            return assembled_data
            
        except Exception as e:
            current_app.logger.error(f"Error in universal detail service: {str(e)}")
            raise
    
    def _get_raw_entity_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get raw entity data by ID"""
        from app.engine import universal_view_engine
        
        # Get entity service
        entity_service = universal_view_engine.get_entity_service(self.config.entity_type)
        
        # Call appropriate get method
        if hasattr(entity_service, 'get_payment_by_id'):
            return entity_service.get_payment_by_id(entity_id, current_user.hospital_id)
        elif hasattr(entity_service, 'get_invoice_by_id'):
            return entity_service.get_invoice_by_id(entity_id, current_user.hospital_id)
        elif hasattr(entity_service, 'get_by_id'):
            return entity_service.get_by_id(entity_id, current_user.hospital_id)
        else:
            raise AttributeError(f"No get method found for service: {type(entity_service)}")
    
    def _get_related_data(self, entity_id: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get related entity data"""
        # This will be implemented as we add more entities
        # For now, return empty dict
        return {}

def universal_list_view(entity_type: str):
    """Universal view function that handles ALL entity lists"""
    try:
        from flask import render_template
        from app.config.entity_configurations import get_entity_config
        
        # Get entity configuration
        config = get_entity_config(entity_type)
        
        # Use universal list service
        list_service = UniversalListService(config)
        assembled_data = list_service.get_list_data()
        
        # Render universal template
        return render_template('engine/universal_list.html', **assembled_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal list view for {entity_type}: {str(e)}")
        return render_template('engine/universal_error.html', 
                             error=str(e), 
                             entity_type=entity_type)

def universal_detail_view(entity_type: str, entity_id: str):
    """Universal view function that handles ALL entity details"""
    try:
        from flask import render_template
        from app.config.entity_configurations import get_entity_config
        
        # Get entity configuration
        config = get_entity_config(entity_type)
        
        # Use universal detail service
        detail_service = UniversalDetailService(config)
        assembled_data = detail_service.get_detail_data(entity_id)
        
        if not assembled_data:
            return render_template('engine/universal_error.html',
                                 error=f"{config.name} not found",
                                 entity_type=entity_type)
        
        # Render universal template
        return render_template('engine/universal_detail.html', **assembled_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal detail view for {entity_type}/{entity_id}: {str(e)}")
        return render_template('engine/universal_error.html',
                             error=str(e),
                             entity_type=entity_type)