"""
Universal Service Integration Layer - Central Hub for Universal Engine
Enhanced version with form integration and configuration-driven behavior
"""

from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from flask_login import current_user

from app.config.entity_configurations import get_entity_config
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class UniversalServiceAdapter:
    """
    Enhanced universal service adapter that works with any entity type
    Uses configuration to determine behavior - NO entity hardcoding
    Central hub for all universal service operations
    """
    
    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.config = get_entity_config(entity_type)
        
        if not self.config:
            raise ValueError(f"No configuration found for entity type: {entity_type}")
    
    def search_data(self, hospital_id: uuid.UUID, filters: Dict, **kwargs) -> Dict:
        """
        Universal search method that delegates to appropriate service
        Uses configuration to determine which service to use
        """
        try:
            # Get service based on configuration
            if self.entity_type == 'supplier_payments':
                from app.services.universal_supplier_service import EnhancedUniversalSupplierService
                service = EnhancedUniversalSupplierService()
                return service.search_payments_with_form_integration(
                    form_class=self._get_form_class(),
                    form_population_functions=self._get_form_population_functions(),
                    **kwargs
                )
            # TODO: Add more entity types as they are implemented
            else:
                raise NotImplementedError(f"Service not implemented for {self.entity_type}")
                
        except Exception as e:
            logger.error(f"Error in universal search for {self.entity_type}: {str(e)}")
            return self._get_empty_result(str(e))
    
    def get_data_for_entity(self, entity_type: str, **kwargs) -> Dict[str, Any]:
        """
        LEGACY COMPATIBILITY: Maintains backward compatibility with old interface
        Converts old interface to new search_data interface
        """
        logger.warning(f"DEPRECATED: get_data_for_entity called for {entity_type}. Use search_data instead.")
        
        # Convert old parameters to new format
        filters = kwargs.get('filters', {})
        hospital_id = kwargs.get('hospital_id') or current_user.hospital_id
        
        return self.search_data(hospital_id=hospital_id, filters=filters, **kwargs)
    
    def _get_form_class(self):
        """Get form class based on configuration"""
        try:
            if self.entity_type == 'supplier_payments':
                from app.forms.supplier_forms import SupplierPaymentFilterForm
                return SupplierPaymentFilterForm
            # TODO: Add more form classes based on entity configuration
            return None
        except ImportError:
            logger.warning(f"Could not import form class for {self.entity_type}")
            return None
    
    def _get_form_population_functions(self) -> List:
        """Get form population functions based on configuration"""
        functions = []
        
        try:
            if self.entity_type == 'supplier_payments':
                from app.utils.form_helpers import populate_supplier_choices
                functions.append(populate_supplier_choices)
            # TODO: Add more population functions based on entity configuration
        except ImportError:
            logger.warning(f"Could not import form population functions for {self.entity_type}")
        
        return functions
    
    def _get_empty_result(self, error: str) -> Dict:
        """Get empty result for error cases"""
        return {
            'items': [],
            'total': 0,
            'page': 1,
            'per_page': self.config.items_per_page if self.config else 20,
            'summary': {},
            'error': error,
            'error_timestamp': datetime.now().isoformat()
        }


# =============================================================================
# UNIVERSAL SERVICE FACTORY FUNCTIONS
# =============================================================================

def get_universal_service(entity_type: str) -> UniversalServiceAdapter:
    """
    Factory function to get universal service for any entity type
    Uses configuration to validate entity type
    Central factory for all universal services
    """
    return UniversalServiceAdapter(entity_type)


def create_universal_adapter(entity_type: str) -> UniversalServiceAdapter:
    """
    Alternative factory function for creating universal adapters
    Provides more explicit naming for adapter creation
    """
    return UniversalServiceAdapter(entity_type)