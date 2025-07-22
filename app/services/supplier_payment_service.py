"""
Supplier Payment Service - Clean wrapper around existing functionality
Preserves ALL existing behavior while providing clean interface
"""

from typing import Dict, Any
from app.services.universal_supplier_service import EnhancedUniversalSupplierService
from app.utils.unicode_logging import get_unicode_safe_logger

logger = get_unicode_safe_logger(__name__)

class SupplierPaymentService:
    """
    Clean interface for supplier payments
    Delegates to existing EnhancedUniversalSupplierService
    This ensures 100% backward compatibility
    """
    
    def __init__(self):
        # Use existing service internally
        self._legacy_service = EnhancedUniversalSupplierService()
    
    def search_data(self, filters: dict, **kwargs) -> dict:
        """
        Same interface as all entity services
        Delegates to existing implementation
        """
        # Ensure entity_type is set correctly
        kwargs['entity_type'] = 'supplier_payments'
        
        # Delegate to existing service
        return self._legacy_service.search_data(filters, **kwargs)
    
    def search_payments_with_form_integration(self, form_class, **kwargs) -> dict:
        """
        Keep specialized method for backward compatibility
        Used by views that expect this method
        """
        return self._legacy_service.search_payments_with_form_integration(form_class, **kwargs)