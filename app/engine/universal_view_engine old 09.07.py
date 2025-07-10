"""
Core Universal View Engine - Orchestrates all universal view functionality
"""

from typing import Dict, Any, Optional
from flask import current_app
import importlib

class UniversalViewEngine:
    """
    Core view engine that orchestrates universal functionality for all entities.
    This is the main entry point for all universal view operations.
    """
    
    def __init__(self):
        self.entity_services = {}
        self.entity_configs = {}
        
    def get_entity_service(self, entity_type: str):
        """Get or create entity service based on entity type"""
        if entity_type not in self.entity_services:
            self.entity_services[entity_type] = self._load_entity_service(entity_type)
        return self.entity_services[entity_type]
    
    def get_entity_config(self, entity_type: str):
        """Get entity configuration"""
        if entity_type not in self.entity_configs:
            self.entity_configs[entity_type] = self._load_entity_config(entity_type)
        return self.entity_configs[entity_type]
    
    def render_entity_list(self, entity_type: str, **kwargs) -> str:
        """Universal list rendering for any entity"""
        try:
            from .universal_components import UniversalListService
            
            # Get configuration
            config = self.get_entity_config(entity_type)
            
            # Use universal list service
            list_service = UniversalListService(config)
            assembled_data = list_service.get_list_data()
            
            # Add any additional context
            assembled_data.update(kwargs)
            
            return assembled_data
            
        except Exception as e:
            current_app.logger.error(f"Error in universal view engine list rendering for {entity_type}: {str(e)}")
            raise
    
    def render_entity_detail(self, entity_type: str, entity_id: str, **kwargs) -> str:
        """Universal detail rendering for any entity"""
        try:
            from .universal_components import UniversalDetailService
            
            # Get configuration
            config = self.get_entity_config(entity_type)
            
            # Use universal detail service
            detail_service = UniversalDetailService(config)
            assembled_data = detail_service.get_detail_data(entity_id)
            
            # Add any additional context
            assembled_data.update(kwargs)
            
            return assembled_data
            
        except Exception as e:
            current_app.logger.error(f"Error in universal view engine detail rendering for {entity_type}/{entity_id}: {str(e)}")
            raise
    
    def _load_entity_service(self, entity_type: str):
        """Dynamically load appropriate entity service"""
        # Map entity types to service modules (business entity grouping)
        service_map = {
            'supplier_payments': ('app.services.universal_supplier_service', 'UniversalSupplierPaymentService'),
            'supplier_invoices': ('app.services.universal_supplier_service', 'UniversalSupplierInvoiceService'),
            'patients': ('app.services.universal_patient_service', 'UniversalPatientService'),
            'medicines': ('app.services.universal_medicine_service', 'UniversalMedicineService'),
        }
        
        if entity_type not in service_map:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        module_path, class_name = service_map[entity_type]
        
        try:
            module = importlib.import_module(module_path)
            service_class = getattr(module, class_name)
            return service_class()
        except ImportError as e:
            current_app.logger.error(f"Failed to import service for {entity_type}: {str(e)}")
            raise
    
    def _load_entity_config(self, entity_type: str):
        """Load entity configuration"""
        try:
            from app.config.entity_configurations import get_entity_config
            return get_entity_config(entity_type)
        except ImportError as e:
            current_app.logger.error(f"Failed to load config for {entity_type}: {str(e)}")
            raise