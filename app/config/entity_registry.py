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
        module="app.config.modules.master_entities",
        service_class="app.services.supplier_master_service.SupplierMasterService",
        model_class="app.models.master.Supplier"
    ),
    
    "patients": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.master_entities",
        service_class="app.services.patient_service.PatientService",
        model_class="app.models.master.Patient"
    ),
    
    "users": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.master_entities",
        service_class="app.services.user_service.UserService",
        model_class="app.models.master.User"
    ),
    
    "medicines": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.inventory",
        service_class="app.services.medicine_service.MedicineService",
        model_class="app.models.master.Medicine"
    ),
    
    "categories": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.master_entities",
        model_class="app.models.master.Category"
    ),
    
    "branches": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.master_entities",
        model_class="app.models.master.Branch"
    ),
    
    "departments": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.master_entities",
        model_class="app.models.master.Department"
    ),
    
    # ========== TRANSACTION ENTITIES (Read-Only in Universal Engine) ==========
    "supplier_payments": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.financial_transactions",
        service_class="app.services.supplier_payment_service.SupplierPaymentService",
        model_class="app.models.transaction.SupplierPayment"
    ),
    
    "supplier_invoices": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.financial_transactions",
        service_class="app.services.supplier_invoice_service.SupplierInvoiceService",
        model_class="app.models.transaction.SupplierInvoice"
    ),
    
    "purchase_orders": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.financial_transactions",
        service_class="app.services.purchase_order_service.PurchaseOrderService",
        model_class="app.models.transaction.PurchaseOrder"
    ),
    
    "billing_transactions": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.billing",
        service_class="app.services.billing_service.BillingService",
        model_class="app.models.transaction.BillingTransaction"
    ),
    
    "inventory_movements": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.inventory",
        service_class="app.services.inventory_service.InventoryMovementService",
        model_class="app.models.transaction.InventoryMovement"
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
    "billing_transactions": {
        "create": "/billing/create",
        "edit": "/billing/edit/{transaction_id}",
        "delete": None,
    },
}

def get_custom_url(entity_type: str, operation: str) -> Optional[str]:
    """Get custom URL for transaction entity operations"""
    return CUSTOM_ENTITY_URLS.get(entity_type, {}).get(operation)