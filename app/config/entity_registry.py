# app/config/entity_registry.py
"""
Central Entity Registry - Single source of truth for all entities
No hardcoding, easy to extend, configuration-driven
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

class EntityCategory(Enum):
    """Entity categories for operation scope control"""
    MASTER = "master"
    TRANSACTION = "transaction"
    REPORT = "report"  # Future: read-only reports
    LOOKUP = "lookup"  # Future: simple lookup tables

@dataclass
class EntityRegistration:
    """Registration details for each entity"""
    category: EntityCategory
    module: str  # Which config module contains this entity
    service_class: Optional[str] = None  # Entity-specific service class
    model_class: Optional[str] = None  # SQLAlchemy model class
    enabled: bool = True  # Enable/disable entities easily

# =============================================================================
# ENTITY REGISTRY - Single place to manage all entities
# =============================================================================

ENTITY_REGISTRY: Dict[str, EntityRegistration] = {
    
    # ========== MASTER ENTITIES (Full CRUD Support) ==========
    "suppliers": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.supplier_config",
        service_class="app.services.supplier_master_service.SupplierMasterService",
        model_class="app.models.master.Supplier"
    ),

    "medicines": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.medicine_config",
        service_class="app.services.medicine_service.UniversalMedicineService",
        model_class="app.models.master.Medicine"
    ),

    "services": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.service_config",
        service_class="app.engine.universal_entity_service.UniversalEntityService",
        model_class="app.models.master.Service"
    ),

    "patients": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.supplier_config",
        service_class="app.services.patient_service.PatientService",
        model_class="app.models.master.Patient"
    ),

    "packages": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.package_config",  # Minimal config for autocomplete and basic CRUD
        service_class="app.services.package_service.PackageService",
        model_class="app.models.master.Package"
    ),

    "package_bom_items": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.package_bom_item_config",
        service_class="app.services.package_service.PackageService",  # Use PackageService for custom list logic
        model_class="app.models.master.PackageBOMItem"
    ),

    "package_session_plans": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.package_session_plan_config",
        service_class="app.engine.universal_entity_service.UniversalEntityService",
        model_class="app.models.master.PackageSessionPlan"
    ),

    "package_payment_plans": EntityRegistration(
        category=EntityCategory.MASTER,  # Full CRUD like master entities
        module="app.config.modules.package_payment_plan_config",
        service_class="app.services.package_payment_service.PackagePaymentService",
        model_class="app.models.views.PackagePaymentPlanView"  # ✅ FIX: Use VIEW model not base model!
    ),


    # ========== TRANSACTION ENTITIES (Read-Only in Universal Engine) ==========
    "supplier_payments": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.supplier_payment_config",  # Updated module path
        service_class="app.services.supplier_payment_service.SupplierPaymentService",
        model_class="app.models.views.SupplierPaymentView"  # ← Use VIEW like PurchaseOrders
    ),

    "patient_payments": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.patient_payment_config",
        service_class="app.services.patient_payment_service.PatientPaymentService",
        model_class="app.models.views.PatientPaymentReceiptView"  # Use VIEW for list/search
    ),

    "supplier_invoices": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.supplier_invoice_config",
        service_class="app.services.supplier_invoice_service.SupplierInvoiceService",
        model_class="app.models.views.SupplierInvoiceView"  # Changed to use view model
    ),
    
    "purchase_orders": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.purchase_orders_config",  # New module
        service_class="app.services.purchase_order_service.PurchaseOrderService",  # New service
        model_class="app.models.views.PurchaseOrderView"
    ),

    "patient_invoices": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.patient_invoice_config",
        service_class="app.services.patient_invoice_service.PatientInvoiceService",
        model_class="app.models.views.PatientInvoiceView"  # View model for list/search
    ),

    "consolidated_patient_invoices": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.consolidated_patient_invoices_config",
        service_class="app.services.consolidated_patient_invoice_service.ConsolidatedPatientInvoiceService",
        model_class="app.models.views.ConsolidatedPatientInvoiceView"  # Dedicated view for consolidated invoices
    ),

    "consolidated_invoice_detail": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.consolidated_invoice_detail_config",
        service_class="app.services.consolidated_patient_invoice_service.ConsolidatedPatientInvoiceService",  # Reuse same service
        model_class="app.models.views.PatientInvoiceView"  # Individual invoices view
    ),

}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_entity_registration(entity_type: str) -> Optional[EntityRegistration]:
    """Get registration details for an entity"""
    return ENTITY_REGISTRY.get(entity_type)

def get_entities_by_category(category: EntityCategory) -> List[str]:
    """Get all entities of a specific category"""
    return [
        entity_type 
        for entity_type, reg in ENTITY_REGISTRY.items() 
        if reg.category == category and reg.enabled
    ]

def is_master_entity(entity_type: str) -> bool:
    """Check if entity is a master entity"""
    reg = get_entity_registration(entity_type)
    return reg and reg.category == EntityCategory.MASTER

def is_transaction_entity(entity_type: str) -> bool:
    """Check if entity is a transaction entity"""
    reg = get_entity_registration(entity_type)
    return reg and reg.category == EntityCategory.TRANSACTION

def register_entity(entity_type: str, registration: EntityRegistration):
    """Register a new entity dynamically"""
    ENTITY_REGISTRY[entity_type] = registration

def get_entity_config_module(entity_type: str) -> Optional[str]:
    """Get the configuration module for an entity"""
    reg = get_entity_registration(entity_type)
    return reg.module if reg else None

# =============================================================================
# BULK CONFIGURATION HELPERS
# =============================================================================

def get_master_entities() -> List[str]:
    """Get all master entities for CRUD operations"""
    return get_entities_by_category(EntityCategory.MASTER)

def get_transaction_entities() -> List[str]:
    """Get all transaction entities (read-only)"""
    return get_entities_by_category(EntityCategory.TRANSACTION)

def get_all_entities() -> List[str]:
    """Get all registered entities"""
    return list(ENTITY_REGISTRY.keys())

# =============================================================================
# CUSTOM URL MAPPINGS (For transaction entities)
# =============================================================================

CUSTOM_ENTITY_URLS = {
    "supplier_payments": {
        "create": "/supplier/payment/create",
        "edit": "/supplier/payment/edit/{payment_id}",
        "delete": None,  # No delete for payments
    },
    "supplier_invoices": {
        "create": "/supplier/invoice/create",
        "edit": "/supplier/invoice/edit/{invoice_id}",
        "delete": None,
    },
    "purchase_orders": {
        "create": "/supplier/po/create",
        "edit": "/supplier/po/edit/{po_id}",
        "delete": None,
    },
    "patient_invoices": {
        "create": "/billing/invoice/create",
        "edit": "/billing/invoice/edit/{invoice_id}",
        "delete": None,
    },
    "patient_payments": {
        "create": "/billing/payment/patient-selection",  # Patient selection first, then payment form
        "edit": None,  # No edit for payments (only approve/reject/reverse)
        "delete": None,  # Use workflow actions (soft delete via service)
    },
    "billing_transactions": {
        "create": "/billing/create",
        "edit": "/billing/edit/{transaction_id}",
        "delete": None,
    },
    "package_payment_plans": {
        "create": "/package/payment-plan/create",  # Custom route with cascading workflow
        "edit": None,  # Use Universal Engine for edit
        "delete": None,  # Use Universal Engine for delete
    },
}

def get_custom_url(entity_type: str, operation: str) -> Optional[str]:
    """Get custom URL for transaction entity operations"""
    return CUSTOM_ENTITY_URLS.get(entity_type, {}).get(operation)