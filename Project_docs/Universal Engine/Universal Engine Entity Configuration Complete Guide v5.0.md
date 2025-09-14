Universal Engine Entity Configuration Complete Guide v5.0
Comprehensive Edition - Merged v4.0 + v5.0
Table of Contents
Part I: Foundation

Introduction
Core Concepts
Architecture Overview
Entity Categories

Part II: Configuration System

Field Configuration
Entity Configuration
View Layout Configuration
Action Configuration
Document Configuration

Part III: Advanced Features

Database Views for Transaction Entities
Filter System
Entity Service Architecture
Entity Registry
Summary Cards

Part IV: Implementation

Complete Configuration Examples
Service Override Guidelines
Best Practices
Migration Guide
Troubleshooting


Part I: Foundation
Introduction
The Universal Engine v5.0 is a configuration-driven framework that eliminates code duplication and ensures consistency across entity management. It provides a complete solution for CRUD operations, filtering, searching, viewing, and document generation through configuration rather than code.
Key Benefits:

Write once, use everywhere: Single configuration drives all functionality
Consistency: Uniform behavior across all entities
Maintainability: Changes in one place affect entire system
Performance: Optimized with database views and caching
Extensibility: Easy to add new entities or modify existing ones

Core Concepts
Configuration-Driven Architecture
Everything starts with configuration. Instead of writing code for each entity, you define its structure and behavior through configuration objects.
Single Source of Truth
Field definitions in configuration drive:

Database queries
Form generation
Validation rules
Display formatting
Filter behavior
Export formats

Entity-Agnostic Processing
The Universal Engine processes all entities the same way, using configuration to determine specific behavior.
Architecture Overview
┌───────────────────────────────────────────────────────┐
│                    Universal Engine v5.0              │
├───────────────┬──────────────────┬────────────────────┤
│Configuration  │  Core Engine     │  Service Layer     │
├───────────────┼──────────────────┼────────────────────┤
│Field Defs     │Filter Processor  │UniversalEntityService│
│Entity Config  │Data Assembler    │Entity-Specific     │
│View Layouts   │Search Engine     │Service Overrides   │
│Actions        │Document Gen      │                    │
└───────────────┴──────────────────┴────────────────────┘
Entity Categories
Master Entities
Core business data that changes infrequently:

Suppliers, Patients, Medicines, Users
Typically have simple relationships
Direct table access is sufficient

Transaction Entities
Business transactions with complex relationships:

Purchase Orders, Payments, Invoices
Require data from multiple tables
Use database views for performance

Reference Entities
Lookup and configuration data:

Countries, States, Categories
Rarely change
Often cached


Part II: Configuration System
Field Configuration
FieldDefinition Structure
pythonfrom dataclasses import dataclass
from typing import Optional, List, Any

@dataclass
class FieldDefinition:
    # === REQUIRED PARAMETERS ===
    name: str                          # Field identifier
    label: str                         # Display label
    field_type: FieldType             # Data type
    
    # === DATABASE MAPPING (v5.0) ===
    db_column: Optional[str] = None   # Actual database column name
    
    # === DISPLAY CONTROL ===
    show_in_list: bool = False        # Show in table/list view
    show_in_detail: bool = True       # Show in detail view
    show_in_form: bool = True         # Show in forms
    
    # === BEHAVIOR ===
    required: bool = False             # Required field
    readonly: bool = False             # Read-only field
    virtual: bool = False              # Calculated field
    filterable: bool = False           # Can filter by this field
    searchable: bool = False           # Include in text search
    sortable: bool = False             # Can sort by this field
    
    # === FILTER CONFIGURATION (v5.0) ===
    filter_operator: Optional[FilterOperator] = None  # Filter behavior
    filter_aliases: List[str] = field(default_factory=list)  # Alternative names
    
    # === VALIDATION ===
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    regex_pattern: Optional[str] = None
    
    # === OPTIONS (for SELECT fields) ===
    options: Optional[List[Dict]] = None  # Static options
    options_callback: Optional[str] = None  # Dynamic options function
    
    # === FORMATTING ===
    format_pattern: Optional[str] = None  # Display format
    placeholder: Optional[str] = None     # Input placeholder
    help_text: Optional[str] = None      # Help tooltip
    
    # === LAYOUT ===
    tab_group: Optional[str] = None      # Tab assignment
    section: Optional[str] = None        # Section within tab
    view_order: int = 0                  # Display order
    width: Optional[str] = None          # Column width
Field Types (FieldType Enum)
pythonclass FieldType(Enum):
    # Text Types
    TEXT = "text"
    TEXTAREA = "textarea"
    EMAIL = "email"
    URL = "url"
    
    # Numeric Types
    INTEGER = "integer"
    DECIMAL = "decimal"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    
    # Date/Time Types
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    
    # Selection Types
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    BOOLEAN = "boolean"
    
    # Special Types
    UUID = "uuid"
    STATUS_BADGE = "status_badge"
    ENTITY_SEARCH = "entity_search"
    FILE = "file"
    IMAGE = "image"
    JSON = "json"
    CUSTOM = "custom"
Filter Operators (v5.0)
pythonclass FilterOperator(Enum):
    EQUALS = "equals"                    # Default
    CONTAINS = "contains"                 # Text search (ILIKE)
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    BETWEEN = "between"
    DATE_ON_OR_BEFORE = "on_or_before"
    DATE_ON_OR_AFTER = "on_or_after"
    IN = "in"
    NOT_IN = "not_in"
Entity Configuration
python@dataclass
class EntityConfiguration:
    # === BASIC INFORMATION ===
    entity_type: str                    # Unique identifier
    name: str                           # Singular name
    plural_name: str                    # Plural name
    icon: str                          # FontAwesome icon
    
    # === DATABASE ===
    model_class: str                    # Model class path
    table_name: str                     # Table/view name
    primary_key: str                    # Primary key field
    
    # === FIELDS ===
    fields: List[FieldDefinition]       # Field definitions
    
    # === DISPLAY ===
    title_field: str                    # Field for record title
    subtitle_field: Optional[str]       # Field for subtitle
    searchable_fields: List[str]        # Fields for text search
    default_sort_field: str             # Default sort field
    default_sort_direction: str         # 'asc' or 'desc'
    
    # === LAYOUT ===
    view_layout: ViewLayoutConfiguration
    section_definitions: Dict[str, SectionDefinition]
    
    # === ACTIONS ===
    actions: List[ActionDefinition]
    
    # === FILTERS (v5.0) ===
    filter_category_mapping: Dict[str, FilterCategory]
    default_filters: Dict[str, Any]
    primary_date_field: Optional[str]
    primary_amount_field: Optional[str]
    
    # === FEATURES ===
    enable_audit_trail: bool = True
    enable_soft_delete: bool = True
    enable_bulk_operations: bool = False
    enable_import_export: bool = True
    
    # === PERMISSIONS ===
    permissions: Dict[str, str]         # Operation -> permission mapping
View Layout Configuration
python@dataclass
class ViewLayoutConfiguration:
    type: LayoutType                    # SIMPLE, TABBED, ACCORDION
    tabs: Optional[Dict[str, TabDefinition]]
    sections: Optional[Dict[str, SectionDefinition]]
    default_tab: Optional[str]
    columns_per_row: int = 2
    
@dataclass
class TabDefinition:
    key: str
    label: str
    icon: str
    sections: Dict[str, SectionDefinition]
    order: int
    show_if: Optional[str]              # Conditional display
    
@dataclass
class SectionDefinition:
    key: str
    title: str
    icon: Optional[str]
    columns: int = 2
    collapsible: bool = False
    collapsed: bool = False
    order: int
Action Configuration
python@dataclass
class ActionDefinition:
    id: str                             # Unique identifier
    label: str                          # Button text
    icon: str                          # Icon class
    button_type: ButtonType             # PRIMARY, SECONDARY, etc.
    
    # Routing
    route_name: Optional[str]
    route_params: Optional[Dict]
    url_pattern: Optional[str]
    
    # Display
    show_in_list: bool = False
    show_in_detail: bool = False
    show_in_toolbar: bool = False
    display_type: ActionDisplayType      # BUTTON, DROPDOWN_ITEM, LINK
    
    # Behavior
    permission: Optional[str]
    confirmation_required: bool = False
    confirmation_message: Optional[str]
    conditions: Optional[Dict]          # Show conditionally
    order: int = 0
Document Configuration
python@dataclass
class DocumentConfiguration:
    enabled: bool = True
    document_type: str                  # invoice, receipt, report
    title: str
    subtitle: Optional[str]
    
    # Page Setup
    page_size: str = "A4"
    orientation: str = "portrait"
    margins: Dict[str, int]
    
    # Content
    show_header: bool = True
    show_footer: bool = True
    show_logo: bool = True
    visible_sections: List[str]
    
    # Export
    allowed_formats: List[str]          # pdf, excel, csv
    default_format: str = "pdf"

Part III: Advanced Features
Database Views for Transaction Entities
Why Use Database Views?
Transaction entities typically require:

Data from multiple related tables
Calculated fields
Aggregated summaries
Denormalized data for performance

Instead of complex joins at runtime, create database views that pre-join and calculate data.
Creating a Transaction View
sql-- Example: Purchase Orders View with denormalized data
CREATE OR REPLACE VIEW purchase_orders_view AS
SELECT 
    -- Main table fields
    poh.po_id,
    poh.po_number,
    poh.po_date,
    poh.po_status,
    
    -- Standardized field names (v5.0)
    poh.po_status as status,  -- Standardized status field
    
    -- Denormalized supplier data (avoid runtime joins)
    s.supplier_id,
    s.supplier_name,
    s.supplier_category,
    s.contact_person_name as supplier_contact_person,
    s.mobile as supplier_mobile,
    s.email as supplier_email,
    s.gst_registration_number as supplier_gst,
    s.payment_terms as supplier_payment_terms,
    
    -- Denormalized branch data
    b.branch_id,
    b.branch_name,
    b.state_code as branch_state_code,
    
    -- Calculated fields
    COUNT(pol.line_id) as line_count,
    SUM(pol.quantity * pol.unit_price) as calculated_total,
    
    -- Date helpers for filtering
    EXTRACT(YEAR FROM poh.po_date) as po_year,
    EXTRACT(MONTH FROM poh.po_date) as po_month,
    TO_CHAR(poh.po_date, 'YYYY-MM') as po_month_year,
    
    -- Status helpers
    CASE 
        WHEN poh.po_status = 'draft' THEN 1
        WHEN poh.po_status = 'pending' THEN 2
        WHEN poh.po_status = 'approved' THEN 3
        ELSE 4
    END as status_order

FROM purchase_order_header poh
LEFT JOIN suppliers s ON poh.supplier_id = s.supplier_id
LEFT JOIN branches b ON poh.branch_id = b.branch_id
LEFT JOIN purchase_order_line pol ON poh.po_id = pol.po_id
GROUP BY poh.po_id, s.supplier_id, b.branch_id;

-- Create indexes for performance
CREATE INDEX idx_po_view_date ON purchase_order_header(po_date);
CREATE INDEX idx_po_view_status ON purchase_order_header(po_status);
CREATE INDEX idx_po_view_supplier ON purchase_order_header(supplier_id);
View Model Definition
python# models/views.py
class PurchaseOrderView(Base):
    """
    Read-only view model for purchase orders
    Maps to database view, not table
    """
    __tablename__ = 'purchase_orders_view'
    __table_args__ = {'info': {'is_view': True}}  # Mark as view
    
    # Primary key (required even for views)
    po_id = Column(UUID(as_uuid=True), primary_key=True)
    
    # Main fields
    po_number = Column(String(20))
    po_date = Column(DateTime(timezone=True))
    po_status = Column(String(20))
    status = Column(String(20))  # Standardized field
    
    # Denormalized fields (no relationships needed)
    supplier_name = Column(String(200))
    supplier_category = Column(String(50))
    branch_name = Column(String(100))
    
    # Calculated fields
    line_count = Column(Integer)
    calculated_total = Column(Numeric(12, 2))
    
    # Note: No relationships, no lazy loading
    # All data comes from the view
Filter System
Filter Categories
pythonclass FilterCategory(Enum):
    DATE = "date"           # Date range filters
    AMOUNT = "amount"       # Numeric range filters
    SEARCH = "search"       # Text search filters
    SELECTION = "selection" # Dropdown filters
    RELATIONSHIP = "relationship"  # Foreign key filters
Category-Based Processing
Each category has specialized processing:
python# Date filters handle presets
DATE: {
    'presets': ['today', 'this_week', 'this_month', 'financial_year'],
    'range_support': True,
    'operators': ['on_or_before', 'on_or_after', 'between']
}

# Search filters use ILIKE
SEARCH: {
    'case_sensitive': False,
    'min_length': 2,
    'operators': ['contains', 'starts_with', 'ends_with']
}

# Selection filters handle multiple values
SELECTION: {
    'multiple': True,
    'empty_means_all': True,
    'operators': ['equals', 'in', 'not_in']
}
Filter Configuration Example
pythonPURCHASE_ORDER_FILTER_CATEGORY_MAPPING = {
    # Standardized field names (v5.0)
    'status': FilterCategory.SELECTION,
    'po_status': FilterCategory.SELECTION,  # Backward compatibility
    
    # Search fields
    'supplier_name': FilterCategory.SEARCH,
    'po_number': FilterCategory.SEARCH,
    
    # Date fields
    'po_date': FilterCategory.DATE,
    'expected_delivery': FilterCategory.DATE,
    
    # Amount fields
    'total_amount': FilterCategory.AMOUNT,
    
    # Relationships
    'supplier_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP
}
Entity Service Architecture
Base Universal Service
pythonclass UniversalEntityService:
    """
    Base service providing complete CRUD and search functionality
    All entities get this functionality for free
    """
    
    def __init__(self, entity_type: str, model_class: Type):
        self.entity_type = entity_type
        self.model_class = model_class
        self.config = get_entity_config(entity_type)
        self.filter_processor = get_categorized_filter_processor()
    
    # Standard interface methods (don't override unless necessary)
    def search_data(self, filters: dict, **kwargs) -> dict:
        """Universal search with filtering, sorting, pagination"""
        
    def get_by_id(self, item_id: UUID, **kwargs) -> Optional[Model]:
        """Get single record by ID"""
        
    def create(self, data: dict, **kwargs) -> Model:
        """Create new record"""
        
    def update(self, item_id: UUID, data: dict, **kwargs) -> Model:
        """Update existing record"""
        
    def delete(self, item_id: UUID, soft: bool = True, **kwargs) -> bool:
        """Delete record (soft or hard)"""
        
    def bulk_operation(self, operation: str, ids: List[UUID], **kwargs) -> dict:
        """Perform bulk operations"""
Entity-Specific Service
pythonclass PurchaseOrderService(UniversalEntityService):
    """
    Purchase Order specific service
    Inherits all standard functionality
    Adds only PO-specific business logic
    """
    
    def __init__(self):
        # Use view model for better performance
        super().__init__('purchase_orders', PurchaseOrderView)
    
    # === OVERRIDE ONLY WHAT'S SPECIFIC ===
    
    def get_summary_stats(self, filters: Dict, hospital_id: UUID) -> Dict:
        """PO-specific summary calculations"""
        # Custom business logic
        
    def approve_purchase_order(self, po_id: UUID, approver_id: UUID) -> bool:
        """PO-specific workflow"""
        # Custom approval logic
        
    def generate_po_number(self) -> str:
        """PO-specific number generation"""
        # Custom numbering logic
    
    # === DON'T OVERRIDE THESE (use parent) ===
    # - search_data()
    # - get_by_id()
    # - create() [unless special validation needed]
    # - update() [unless special validation needed]
Entity Registry
Service Registry
python# services/entity_registry.py
from typing import Type, Dict
from app.engine.universal_entity_service import UniversalEntityService

# Import entity-specific services
from app.services.purchase_order_service import PurchaseOrderService
from app.services.supplier_payment_service import SupplierPaymentService
from app.services.supplier_invoice_service import SupplierInvoiceService

# Register services that need custom logic
ENTITY_SERVICES: Dict[str, Type[UniversalEntityService]] = {
    'purchase_orders': PurchaseOrderService,
    'supplier_payments': SupplierPaymentService,
    'supplier_invoices': SupplierInvoiceService,
    # Entities not listed here use UniversalEntityService
}

def get_entity_service(entity_type: str) -> UniversalEntityService:
    """
    Get service instance for entity type
    Returns specific service or generic UniversalEntityService
    """
    service_class = ENTITY_SERVICES.get(entity_type)
    
    if service_class:
        # Entity has custom service
        return service_class()
    else:
        # Use generic service
        model_class = get_model_class(entity_type)
        return UniversalEntityService(entity_type, model_class)
Configuration Registry
python# config/entity_registry.py
from typing import Dict
from app.config.core_definitions import EntityConfiguration

def register_all_configs() -> Dict[str, EntityConfiguration]:
    """Register all entity configurations"""
    configs = {}
    
    # Import all module configurations
    from app.config.modules import (
        purchase_orders_config,
        financial_transactions,
        master_entities,
        inventory_config,
        patient_config
    )
    
    # Register each module's configurations
    for module in [
        purchase_orders_config,
        financial_transactions,
        master_entities,
        inventory_config,
        patient_config
    ]:
        if hasattr(module, 'get_module_configs'):
            configs.update(module.get_module_configs())
    
    return configs

# Global registry
ENTITY_CONFIGS = register_all_configs()

def get_entity_config(entity_type: str) -> Optional[EntityConfiguration]:
    """Get configuration for entity type"""
    return ENTITY_CONFIGS.get(entity_type)
Summary Cards
python@dataclass
class SummaryCardDefinition:
    title: str                          # Card title
    field: str                          # Field to display
    icon: str                          # Icon class
    color: str                          # Card color theme
    type: str                          # number, currency, percentage
    
    # Filtering
    filterable: bool = False            # Click to filter
    filter_field: Optional[str] = None  # Field to filter
    filter_value: Optional[Any] = None  # Value to filter
    
    # Formatting
    format_pattern: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    
    # Display
    visible: bool = True
    order: int = 0

Part IV: Implementation
Complete Configuration Examples
Full Transaction Entity Configuration
python# config/modules/purchase_orders_config.py

from app.config.core_definitions import *
from app.config.filter_categories import FilterCategory

# 1. Field Definitions with db_column mapping
PURCHASE_ORDER_FIELDS = [
    FieldDefinition(
        name="po_id",
        label="PO ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="header",
        section="identification",
        view_order=0
    ),
    
    FieldDefinition(
        name="status",  # Standardized name (v5.0)
        label="Status",
        field_type=FieldType.STATUS_BADGE,
        db_column="po_status",  # Maps to actual DB column
        filter_aliases=["po_status", "workflow_status"],  # Backward compatibility
        filter_operator=FilterOperator.EQUALS,
        options=[
            {"value": "draft", "label": "Draft", "color": "secondary"},
            {"value": "pending", "label": "Pending", "color": "warning"},
            {"value": "approved", "label": "Approved", "color": "success"},
            {"value": "cancelled", "label": "Cancelled", "color": "danger"}
        ],
        filterable=True,
        sortable=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        tab_group="header",
        section="workflow",
        view_order=10
    ),
    
    FieldDefinition(
        name="supplier_name",
        label="Supplier",
        field_type=FieldType.TEXT,
        filter_operator=FilterOperator.CONTAINS,  # Search behavior
        searchable=True,
        sortable=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,  # Not in form (comes from view)
        tab_group="header",
        section="supplier",
        view_order=20
    ),
    # ... more fields
]

# 2. Section Definitions
PURCHASE_ORDER_SECTIONS = {
    "identification": SectionDefinition(
        key="identification",
        title="Identification",
        icon="fas fa-id-card",
        columns=2,
        order=1
    ),
    "workflow": SectionDefinition(
        key="workflow",
        title="Status & Workflow",
        icon="fas fa-tasks",
        columns=2,
        order=2
    ),
    # ... more sections
}

# 3. Tab Definitions
PURCHASE_ORDER_TABS = {
    "header": TabDefinition(
        key="header",
        label="Order Details",
        icon="fas fa-file-invoice",
        sections={
            "identification": PURCHASE_ORDER_SECTIONS["identification"],
            "workflow": PURCHASE_ORDER_SECTIONS["workflow"],
        },
        order=1
    ),
    # ... more tabs
}

# 4. View Layout
PURCHASE_ORDER_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    tabs=PURCHASE_ORDER_TABS,
    default_tab="header",
    columns_per_row=2
)

# 5. Actions
PURCHASE_ORDER_ACTIONS = [
    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        button_type=ButtonType.INFO,
        route_name="universal_views.view",
        route_params={"entity_type": "purchase_orders"},
        show_in_list=True,
        permission="purchase_order_view",
        order=1
    ),
    # ... more actions
]

# 6. Summary Cards
PURCHASE_ORDER_SUMMARY_CARDS = [
    {
        "title": "Total Orders",
        "field": "total_count",
        "icon": "fas fa-shopping-cart",
        "color": "primary",
        "type": "number",
        "visible": True,
        "order": 1
    },
    # ... more cards
]

# 7. Filter Configuration
PURCHASE_ORDER_FILTER_CATEGORY_MAPPING = {
    'status': FilterCategory.SELECTION,
    'po_status': FilterCategory.SELECTION,  # Alias
    'supplier_name': FilterCategory.SEARCH,
    'po_date': FilterCategory.DATE,
    'total_amount': FilterCategory.AMOUNT,
    'supplier_id': FilterCategory.RELATIONSHIP
}

# 8. Main Configuration
PURCHASE_ORDER_CONFIG = EntityConfiguration(
    # Basic Info
    entity_type="purchase_orders",
    name="Purchase Order",
    plural_name="Purchase Orders",
    icon="fas fa-file-invoice",
    
    # Database
    model_class="app.models.views.PurchaseOrderView",  # View model
    table_name="purchase_orders_view",
    primary_key="po_id",
    
    # Fields & Layout
    fields=PURCHASE_ORDER_FIELDS,
    view_layout=PURCHASE_ORDER_VIEW_LAYOUT,
    section_definitions=PURCHASE_ORDER_SECTIONS,
    
    # Actions & Cards
    actions=PURCHASE_ORDER_ACTIONS,
    summary_cards=PURCHASE_ORDER_SUMMARY_CARDS,
    
    # Filters
    filter_category_mapping=PURCHASE_ORDER_FILTER_CATEGORY_MAPPING,
    primary_date_field="po_date",
    primary_amount_field="total_amount",
    
    # Display
    title_field="po_number",
    subtitle_field="supplier_name",
    searchable_fields=["po_number", "supplier_name"],
    default_sort_field="po_date",
    default_sort_direction="desc",
    
    # Features
    enable_audit_trail=True,
    enable_soft_delete=True,
    enable_bulk_operations=False,
    
    # Permissions
    permissions={
        "list": "purchase_order_list",
        "view": "purchase_order_view",
        "create": "purchase_order_create",
        "edit": "purchase_order_edit",
        "delete": "purchase_order_delete",
        "approve": "purchase_order_approve"
    }
)

# 9. Module Registration
def get_module_configs():
    """Return all configurations from this module"""
    return {
        "purchase_orders": PURCHASE_ORDER_CONFIG
    }

def get_module_filter_configs():
    """Return filter configurations"""
    return {
        "purchase_orders": PURCHASE_ORDER_FILTER_CATEGORY_MAPPING
    }
Service Override Guidelines
When to Override
DO Override for:

Business-specific calculations (summary stats, totals)
Workflow operations (approve, reject, cancel)
Custom validation beyond field rules
Integration with external systems
Complex permission checks
Custom number generation

DON'T Override for:

Basic CRUD operations
Standard filtering/searching
Sorting and pagination
Field validation (use configuration)
Standard permission checks

Good Override Pattern
pythonclass SupplierPaymentService(UniversalEntityService):
    """Good: Only overrides specific business logic"""
    
    def __init__(self):
        super().__init__('supplier_payments', SupplierPaymentView)
    
    def process_payment_approval(self, payment_id: UUID) -> bool:
        """Custom business logic for payment approval"""
        # Get payment using parent method
        payment = self.get_by_id(payment_id)
        
        if not payment:
            return False
        
        # Custom validation
        if payment.amount > 1000000:
            # Requires additional approval
            return self._request_senior_approval(payment)
        
        # Update status
        return self.update(payment_id, {
            'status': 'approved',
            'approved_at': datetime.now(),
            'approved_by': current_user.id
        })
Bad Override Pattern
pythonclass SupplierPaymentService(UniversalEntityService):
    """Bad: Reimplements standard functionality"""
    
    def search_data(self, filters: dict, **kwargs):
        """DON'T: Reimplementing standard search"""
        # Writing custom query logic - WRONG!
        with get_db_session() as session:
            query = session.query(SupplierPayment)
            # ... reimplementing filter logic
        
    def get_by_id(self, item_id: UUID):
        """DON'T: Reimplementing standard get"""
        # This is already in parent class
Best Practices
1. Field Standardization
python# Good: Consistent field names
FieldDefinition(
    name="status",  # Always 'status'
    db_column="workflow_status",  # Map to actual column
    filter_aliases=["workflow_status", "payment_status"]
)

# Bad: Inconsistent names
FieldDefinition(
    name="workflow_status",  # Different for each entity
    # No standardization
)
2. Use Views for Complex Entities
python# Good: View with denormalized data
class SupplierPaymentView(Base):
    __tablename__ = 'supplier_payments_view'
    supplier_name = Column(String)  # Denormalized
    invoice_numbers = Column(String)  # Aggregated

# Bad: Multiple joins at runtime
class SupplierPayment(Base):
    supplier = relationship("Supplier")  # Requires join
    invoices = relationship("Invoice")  # Another join
3. Configuration-Driven Options
python# Good: Options in field definition
FieldDefinition(
    name="payment_method",
    options=[
        {"value": "cash", "label": "Cash"},
        {"value": "cheque", "label": "Cheque"}
    ]
)

# Bad: Hardcoded in forms/templates
<select name="payment_method">
    <option value="cash">Cash</option>  <!-- Hardcoded -->
</select>
4. Proper Service Layering
python# Good: Thin service layer
class InvoiceService(UniversalEntityService):
    def calculate_tax(self, invoice_id: UUID):
        """Only custom business logic"""
        
# Bad: Fat service layer
class InvoiceService(UniversalEntityService):
    def get_all_invoices(self):  # Reimplements parent
    def filter_invoices(self):   # Reimplements parent
    def sort_invoices(self):     # Reimplements parent
Migration Guide
Step-by-Step Migration Process
Step 1: Analyze Current Entity

Identify all fields
Map relationships
Document business rules
List custom operations

Step 2: Create Database View
sqlCREATE OR REPLACE VIEW entity_name_view AS
SELECT 
    -- Include all needed fields
    -- Denormalize relationships
    -- Add calculated fields
    -- Standardize field names
Step 3: Create View Model
pythonclass EntityNameView(Base):
    __tablename__ = 'entity_name_view'
    __table_args__ = {'info': {'is_view': True}}
Step 4: Define Configuration
pythonENTITY_FIELDS = [
    FieldDefinition(...),
    # All fields with proper settings
]

ENTITY_CONFIG = EntityConfiguration(
    entity_type="entity_name",
    model_class="app.models.views.EntityNameView",
    fields=ENTITY_FIELDS,
    # ... complete configuration
)
Step 5: Create Service (if needed)
pythonclass EntityNameService(UniversalEntityService):
    def __init__(self):
        super().__init__('entity_name', EntityNameView)
    
    # Only custom business logic
Step 6: Register Entity
python# In entity_registry.py
ENTITY_SERVICES['entity_name'] = EntityNameService
ENTITY_CONFIGS['entity_name'] = ENTITY_CONFIG
Step 7: Update Routes
python# Use universal routes
/universal/entity_name/list
/universal/entity_name/view/<id>
/universal/entity_name/create
/universal/entity_name/edit/<id>
Step 8: Test & Cleanup

Test all operations
Verify filters work
Check permissions
Remove legacy code

Troubleshooting
Common Issues and Solutions
Issue: Field not displaying in list
Solution:
python# Check these settings
FieldDefinition(
    show_in_list=True,  # Must be True
    # Also check if field exists in view/model
)
Issue: Filter not working
Solution:
python# Verify configuration
FieldDefinition(
    filterable=True,  # Must be True
    filter_operator=FilterOperator.CONTAINS,  # Set operator
    db_column="actual_column",  # Map if different
)

# Check filter category mapping
FILTER_CATEGORY_MAPPING = {
    'field_name': FilterCategory.APPROPRIATE_CATEGORY
}
Issue: Status field shows blank
Solution:
python# Use db_column mapping
FieldDefinition(
    name="status",  # Standardized
    db_column="po_status",  # Actual column
)

# Ensure view includes both columns
SELECT po_status, po_status as status
Issue: Custom service not being used
Solution:
python# Register in entity_registry.py
ENTITY_SERVICES = {
    'entity_type': YourCustomService,  # Exact match
}

# Verify import
from app.services.your_service import YourCustomService
Issue: Slow performance on list view
Solution:

Create database view with joins
Add appropriate indexes
Use view model instead of table model
Enable caching in service


Appendix
Version History
v5.0 (Current)

Added database view architecture
Introduced db_column mapping
Standardized field names
Enhanced filter operators
Improved service registry

v4.0

Introduced categorized filter processor
Added filter categories
Unified configuration structure
Entity registry system

v3.0

Added summary cards
Document generation
Bulk operations

v2.0

View layout configurations
Action definitions
Permission system

v1.0

Initial Universal Engine
Basic CRUD operations
Simple filtering

Glossary

Entity: A business object (e.g., Purchase Order, Payment)
View: Database view providing denormalized data
Model: SQLAlchemy class mapping to table/view
Configuration: Declarative definition of entity behavior
Service: Business logic layer
Registry: Central registration of entities and services
Field Definition: Complete specification of a data field
Filter Category: Grouping of filters by behavior
db_column: Mapping between standardized name and database column

# =============================================================================
# COMPLETE LIST OF VALID FIELDDEFINITION PARAMETERS
# =============================================================================
"""
Valid FieldDefinition parameters (for reference):
- name: str
- label: str
- field_type: FieldType
- db_column: str (optional - maps to database column if different from name)
- filter_aliases: List[str] (optional - alternative names for filtering)
- filter_operator: FilterOperator (optional - how to filter)
- filter_type: str (optional - type of filter widget)
- options: List[Dict] (optional - for SELECT/STATUS_BADGE types)
- show_in_list: bool
- show_in_detail: bool
- show_in_form: bool
- searchable: bool
- sortable: bool
- filterable: bool
- readonly: bool
- required: bool
- virtual: bool (optional - for calculated fields)
- related_field: str (optional - for relationships)
- tab_group: str (optional - for tabbed layouts)
- section: str (optional - for grouping)
- view_order: int (optional - order in detail view)
- placeholder: str (optional)
- help_text: str (optional)
- css_classes: str (optional)
- complex_display_type: ComplexDisplayType (optional)
- custom_renderer: CustomRenderer (optional)
- conditional_display: str (optional)
- autocomplete_enabled: bool (optional)
- autocomplete_source: str (optional)
- entity_search_config: EntitySearchConfiguration (optional)
- format_pattern: str (optional)
- rows: int (optional - for TEXTAREA)
- min_value: Any (optional)
- max_value: Any (optional)
- default_value: Any (optional)



This comprehensive guide represents the complete Universal Engine v5.0 documentation, merging all features from v4.0 and v5.0. For implementation support, consult the codebase examples and development team.