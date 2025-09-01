# Universal Engine Entity Configuration Complete Guide v3.1
## Comprehensive Configuration Manual for Universal Engine with CRUD & Document Extensions

---

## 📋 **Document Overview**

| **Attribute** | **Details** |
|---------------|-------------|
| **Project** | Skinspire Clinic HMS - Universal Engine v3.1 |
| **Version** | Universal Engine v3.1 (Built on v3.0) |
| **Status** | **PRODUCTION READY** |
| **Date** | December 2024 |
| **Architecture** | Configuration-Driven, Backend-Heavy, Entity-Agnostic |
| **New Features** | CRUD Operations, Document Engine, Enhanced Filtering |

---

## 📚 **Table of Contents**
1. [Universal Engine v3.1 Overview](#1-universal-engine-v31-overview)
2. [System Architecture](#2-system-architecture) 
3. [Entity Classification](#3-entity-classification)
4. [Configuration Structure](#4-configuration-structure)
5. [Core Definitions Reference](#5-core-definitions-reference)
6. [Step-by-Step Configuration](#6-step-by-step-configuration)
7. [CRUD Operations Configuration](#7-crud-operations-configuration)
8. [Document Engine Configuration](#8-document-engine-configuration)
9. [Advanced Features](#9-advanced-features)
10. [Best Practices & Patterns](#10-best-practices--patterns)
11. [Troubleshooting Guide](#11-troubleshooting-guide)
12. [Quick Reference](#12-quick-reference)

---

## **1. Universal Engine v3.1 Overview**

### **🎯 Core Principles**

#### **✅ Configuration-Driven**
Every aspect of entity behavior is defined through configuration, not code:

```python
# ✅ GOOD: Configuration-driven
FieldDefinition(
    name="status",
    field_type=FieldType.SELECT,
    options=[
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"}
    ],
    required=True,
    default_value="active"
)

# ❌ BAD: Hardcoded logic
if entity_type == "suppliers":
    status_options = ["active", "inactive"]  # Don't do this!
```

#### **✅ Backend-Heavy Architecture**
- All business logic, calculations, and database operations in Python services
- JavaScript only for UI interactions (tabs, dropdowns, validation feedback)
- Database queries optimized at service level

#### **✅ Entity-Agnostic Design**
- One implementation serves all entities
- Same patterns work for any entity type
- Maximum code reuse across modules

#### **✅ Separation of Concerns**

```
📁 Master Entities (suppliers, patients, users)
   ✅ Full CRUD Operations (Create, Read, Update, Delete)
   ✅ Document Generation (Print, PDF, Excel)
   ✅ Complex Business Logic Supported

📁 Transaction Entities (payments, billing, invoices)  
   ✅ Read Operations Only (View, List, Search)
   ✅ Document Generation (Receipts, Statements)
   ❌ No Create/Update/Delete (Business Logic Too Complex)
```

### **🚀 v3.1 New Capabilities**

| **Feature** | **Master Entities** | **Transaction Entities** |
|-------------|---------------------|---------------------------|
| **List View** | ✅ | ✅ |
| **Detail View** | ✅ | ✅ |
| **Search & Filter** | ✅ | ✅ |
| **Create** | ✅ | ❌ |
| **Edit** | ✅ | ❌ |
| **Delete** | ✅ | ❌ |
| **Document Generation** | ✅ | ✅ |
| **Export** | ✅ | ✅ |
| **Auto-Save** | ✅ | N/A |
| **Form Validation** | ✅ | N/A |

---

## **2. System Architecture**

### **📁 File Structure**

```
app/
├── config/
│   ├── core_definitions.py              ✅ [Enhanced with v3.1]
│   ├── entity_registry.py               ✅ [Central entity registry]
│   ├── entity_configurations.py         ✅ [Configuration loader]
│   └── modules/
│       ├── master_entities.py           ✅ [Master entity configs]
│       └── financial_transactions.py    ✅ [Transaction entity configs]
├── engine/
│   ├── universal_crud_service.py        ✅ [CRUD operations]
│   ├── universal_scope_controller.py    ✅ [Operation validation]
│   ├── document_service.py              ✅ [Document generation]
│   ├── data_assembler.py                ✅ [Data assembly]
│   └── categorized_filter_processor.py  ✅ [Advanced filtering]
├── views/
│   └── universal_views.py               ✅ [All view routes]
├── templates/engine/
│   ├── universal_list.html              ✅ [List view template]
│   ├── universal_view.html              ✅ [Detail view template]
│   ├── universal_create.html            ✅ [Create form template]
│   ├── universal_edit.html              ✅ [Edit form template]
│   └── universal_document.html          ✅ [Document template]
└── static/
    ├── css/components/
    │   ├── universal_list.css            ✅ [List styling]
    │   ├── universal_view.css            ✅ [View styling]
    │   └── universal_form.css            ✅ [Form styling]
    └── js/components/
        ├── universal_forms.js            ✅ [List interactions]
        └── universal_form_crud.js        ✅ [CRUD operations]
```

### **🔄 Data Flow Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        UNIVERSAL ENGINE v3.1 FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Entity Registry validates operation scope                              │
│     └─> Masters: Full CRUD, Transactions: Read-only                        │
│                                                                             │
│  2. Configuration Loader fetches entity configuration                      │
│     └─> Fields, layout, permissions, validation rules                      │
│                                                                             │
│  3. Universal Service handles business logic                               │
│     └─> Database operations, calculations, relationships                   │
│                                                                             │
│  4. Data Assembler processes data for presentation                         │
│     └─> Format fields, apply permissions, generate actions                 │
│                                                                             │
│  5. Templates render universal UI                                          │
│     └─> Dynamic forms, tables, documents based on configuration            │
│                                                                             │
│  6. JavaScript provides progressive enhancement                            │
│     └─> Auto-save, validation feedback, UI interactions                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## **3. Entity Classification**

### **📊 Entity Registry** 
Located in `app/config/entity_registry.py`:

```python
from enum import Enum
from dataclasses import dataclass

class EntityCategory(Enum):
    MASTER = "master"           # Full CRUD support
    TRANSACTION = "transaction" # Read-only
    REPORT = "report"          # Future: Read-only reports  
    LOOKUP = "lookup"          # Future: Simple lookups

@dataclass  
class EntityRegistration:
    category: EntityCategory
    module: str                    # Config module path
    service_class: Optional[str]   # Service class path
    model_class: Optional[str]     # SQLAlchemy model path
    enabled: bool = True

# Central registry - single source of truth
ENTITY_REGISTRY: Dict[str, EntityRegistration] = {
    
    # Master Entities (Full CRUD)
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
    
    # Transaction Entities (Read-only)
    "supplier_payments": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.financial_transactions",
        service_class="app.services.supplier_payment_service.SupplierPaymentService",
        model_class="app.models.transaction.SupplierPayment"
    )
}
```

### **🔒 Operation Scope Control**

```python
# Universal Scope Controller automatically validates operations
class UniversalScopeController:
    def validate_operation(self, entity_type: str, operation: CRUDOperation) -> bool:
        registration = ENTITY_REGISTRY.get(entity_type)
        
        if registration.category == EntityCategory.MASTER:
            return True  # All operations allowed
            
        elif registration.category == EntityCategory.TRANSACTION:
            return operation in [
                CRUDOperation.LIST, 
                CRUDOperation.VIEW, 
                CRUDOperation.DOCUMENT,
                CRUDOperation.EXPORT
            ]
```

---

## **4. Configuration Structure**

### **🏗️ EntityConfiguration Structure**

```python
EntityConfiguration
├── Basic Info (required, no defaults)
│   ├── entity_type: str
│   ├── name: str  
│   ├── plural_name: str
│   ├── service_name: str
│   ├── primary_key: str
│   └── title_field: str
├── Core Components
│   ├── fields: List[FieldDefinition]
│   ├── section_definitions: Dict[str, SectionDefinition]
│   ├── view_layout: ViewLayoutConfiguration
│   ├── actions: List[ActionDefinition]
│   ├── summary_cards: List[Dict]
│   └── permissions: Dict[str, str]
├── CRUD Configuration (v3.1)
│   ├── entity_category: EntityCategory
│   ├── universal_crud_enabled: bool
│   ├── allowed_operations: List[CRUDOperation]
│   ├── create_fields: List[str]
│   ├── edit_fields: List[str]
│   ├── readonly_fields: List[str]
│   ├── model_class_path: str
│   └── primary_key_field: str
├── Document Configuration (v3.1)
│   ├── document_enabled: bool
│   ├── document_configs: Dict[str, DocumentConfiguration]
│   ├── default_document: str
│   └── include_calculated_fields: List[str]
├── Filter Configuration
│   ├── filter_category_mapping: Dict
│   ├── default_filters: Dict
│   └── category_configs: Dict
└── Optional Settings
    ├── searchable_fields: List[str]
    ├── default_sort_field: str
    ├── primary_date_field: str
    └── primary_amount_field: str
```

---

## **5. Core Definitions Reference**

### **📝 FieldDefinition** 
Located in `app/config/core_definitions.py`:

```python
@dataclass
class FieldDefinition:
    # Basic Properties
    name: str                              # Database field name
    label: str                             # Display label
    field_type: FieldType                  # Field type enum
    
    # Display Control
    show_in_list: bool = True              # Show in list view
    show_in_detail: bool = True            # Show in detail view
    show_in_form: bool = True              # Show in create/edit forms
    
    # Form Properties
    required: bool = False                 # Required field validation
    readonly: bool = False                 # Read-only field
    placeholder: str = ""                  # Input placeholder
    help_text: str = ""                    # Help text
    default_value: Any = None              # Default value for new records
    
    # List Properties  
    searchable: bool = False               # Include in text search
    sortable: bool = False                 # Allow column sorting
    filterable: bool = False               # Show in filters
    
    # Layout Properties
    tab_group: str = "general"             # Tab assignment
    section: str = "basic_info"            # Section assignment
    view_order: int = 0                    # Order within section
    
    # Field Type Specific
    options: List[Dict] = field(default_factory=list)  # For SELECT fields
    min_value: Optional[float] = None                   # For NUMBER/DECIMAL
    max_value: Optional[float] = None                   # For NUMBER/DECIMAL
    format_pattern: str = ""                           # Display format
    
    # Advanced Properties
    virtual: bool = False                  # Calculated field (not in DB)
    related_field: str = ""                # For virtual fields
    conditional_display: str = ""          # Show/hide conditions
    validation: Dict = field(default_factory=dict)     # Custom validation
    css_classes: str = ""                  # Custom CSS classes
    
    # CRUD Specific (v3.1)
    create_required: bool = False          # Required in create form
    edit_required: bool = False            # Required in edit form
    create_readonly: bool = False          # Readonly in create
    edit_readonly: bool = False            # Readonly in edit
```

### **🎨 Field Types**

```python
class FieldType(Enum):
    # Text Fields
    TEXT = "text"                          # Single line text
    TEXTAREA = "textarea"                  # Multi-line text
    EMAIL = "email"                        # Email with validation
    URL = "url"                           # URL with validation
    
    # Number Fields
    NUMBER = "number"                      # Integer
    DECIMAL = "decimal"                    # Float/Money
    CURRENCY = "currency"                  # Money with formatting
    PERCENTAGE = "percentage"              # Percentage
    
    # Date/Time Fields
    DATE = "date"                          # Date only
    DATETIME = "datetime"                  # Date and time
    TIME = "time"                          # Time only
    
    # Selection Fields
    SELECT = "select"                      # Dropdown
    MULTI_SELECT = "multi_select"          # Multi-select
    BOOLEAN = "boolean"                    # Checkbox
    RADIO = "radio"                        # Radio buttons
    
    # System Fields
    UUID = "uuid"                          # Unique identifier
    JSONB = "jsonb"                       # JSON data
    
    # Relationship Fields
    ENTITY_SEARCH = "entity_search"        # Related entity search
    
    # Special Fields
    CUSTOM = "custom"                      # Custom renderer
    FILE = "file"                         # File upload
    IMAGE = "image"                       # Image upload
```

### **📄 DocumentConfiguration**

```python
@dataclass
class DocumentConfiguration:
    # Basic Settings
    enabled: bool = True
    document_type: str = "receipt"
    title: str = "Document"
    
    # Layout Configuration
    page_size: str = "A4"                  # A4, A5, Letter
    orientation: str = "portrait"          # portrait, landscape
    print_layout_type: PrintLayoutType = PrintLayoutType.STANDARD
    
    # Header Configuration
    show_logo: bool = True
    show_company_info: bool = True
    header_text: Optional[str] = None
    
    # Content Configuration
    visible_tabs: List[str] = field(default_factory=list)
    hidden_sections: List[str] = field(default_factory=list)
    custom_field_order: List[str] = field(default_factory=list)
    
    # Footer Configuration
    show_footer: bool = True
    footer_text: Optional[str] = None
    show_print_info: bool = True
    signature_fields: List[Dict] = field(default_factory=list)
    
    # Export Options
    allowed_formats: List[str] = field(default_factory=lambda: ["pdf", "print"])
```

---

## **6. Step-by-Step Configuration**

### **Step 1: Register Entity**

First, register your entity in `app/config/entity_registry.py`:

```python
ENTITY_REGISTRY["your_entity"] = EntityRegistration(
    category=EntityCategory.MASTER,  # or EntityCategory.TRANSACTION
    module="app.config.modules.master_entities",
    service_class="app.services.your_entity_service.YourEntityService",
    model_class="app.models.master.YourEntity"
)
```

### **Step 2: Import Required Definitions**

In your configuration module:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition, 
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition, ButtonType,
    ActionDisplayType, DocumentConfiguration, EntityCategory,
    CRUDOperation, PrintLayoutType, PageSize, Orientation
)
from app.config.filter_categories import FilterCategory
```

### **Step 3: Define Fields**

```python
YOUR_ENTITY_FIELDS = [
    # Primary Key - Always first
    FieldDefinition(
        name="entity_id",
        label="ID", 
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="profile",
        section="identification",
        view_order=0
    ),
    
    # Required Fields
    FieldDefinition(
        name="entity_name",
        label="Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        searchable=True,
        sortable=True,
        filterable=True,
        placeholder="Enter entity name",
        tab_group="profile",
        section="basic_info",
        view_order=1,
        
        # CRUD specific
        create_required=True,
        edit_required=True
    ),
    
    # Selection Field
    FieldDefinition(
        name="category",
        label="Category",
        field_type=FieldType.SELECT,
        options=[
            {"value": "type1", "label": "Type 1"},
            {"value": "type2", "label": "Type 2"}
        ],
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        filterable=True,
        default_value="type1",
        tab_group="profile",
        section="basic_info",
        view_order=2
    ),
    
    # Virtual/Calculated Field
    FieldDefinition(
        name="calculated_total",
        label="Total Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,                      # Not stored in DB
        related_field="transactions",      # Calculated from transactions
        tab_group="financial",
        section="summary",
        view_order=1
    )
]
```

### **Step 4: Define Sections and Tabs**

```python
YOUR_ENTITY_SECTIONS = {
    "identification": SectionDefinition(
        name="identification",
        title="Identification",
        description="Basic identification information",
        icon="fas fa-id-card",
        collapsible=False,
        order=1
    ),
    "basic_info": SectionDefinition(
        name="basic_info",
        title="Basic Information", 
        description="Essential entity information",
        icon="fas fa-info-circle",
        collapsible=False,
        order=2
    ),
    "financial": SectionDefinition(
        name="financial",
        title="Financial Information",
        description="Financial data and calculations",
        icon="fas fa-dollar-sign",
        collapsible=True,
        order=3
    )
}

YOUR_ENTITY_TABS = {
    "profile": TabDefinition(
        name="profile",
        title="Profile",
        icon="fas fa-user",
        sections=["identification", "basic_info"],
        order=1
    ),
    "financial": TabDefinition(
        name="financial", 
        title="Financial",
        icon="fas fa-chart-line",
        sections=["financial"],
        order=2
    )
}

# Layout Configuration
YOUR_ENTITY_VIEW_LAYOUT = ViewLayoutConfiguration(
    layout_type=LayoutType.TABBED,         # SIMPLE, TABBED, or ACCORDION
    sections=YOUR_ENTITY_SECTIONS,
    tabs=YOUR_ENTITY_TABS,
    default_tab="profile",
    show_section_descriptions=True
)
```

### **Step 5: Define Actions**

```python
YOUR_ENTITY_ACTIONS = [
    # List Actions
    ActionDefinition(
        id="create",
        label="Add New",
        icon="fas fa-plus",
        url_pattern="/universal/{entity_type}/create",
        button_type=ButtonType.PRIMARY,
        permission="entity_create",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),
    
    # Detail Actions  
    ActionDefinition(
        id="edit",
        label="Edit",
        icon="fas fa-edit", 
        url_pattern="/universal/{entity_type}/edit/{item_id}",
        button_type=ButtonType.SECONDARY,
        permission="entity_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),
    
    ActionDefinition(
        id="delete",
        label="Delete",
        icon="fas fa-trash",
        url_pattern="/universal/{entity_type}/delete/{item_id}",
        button_type=ButtonType.DANGER,
        permission="entity_delete", 
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        confirm_message="Are you sure you want to delete this entity?",
        order=3
    )
]
```

### **Step 6: Define Summary Cards**

```python
YOUR_ENTITY_SUMMARY_CARDS = [
    {
        "id": "total_count",
        "field": "total_count",
        "label": "Total Entities",
        "icon": "fas fa-cube",
        "icon_css": "stat-card-icon primary",
        "type": "number",
        "filterable": True,
        "filter_field": "clear_filters",
        "filter_value": "all",
        "visible": True
    },
    {
        "id": "active_count", 
        "field": "active_count",
        "label": "Active",
        "icon": "fas fa-check-circle",
        "icon_css": "stat-card-icon success",
        "type": "number",
        "filterable": True,
        "filter_field": "status",
        "filter_value": "active",
        "visible": True
    }
]
```

### **Step 7: Define Filters**

```python
YOUR_ENTITY_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'created_date': FilterCategory.DATE,
    'start_date': FilterCategory.DATE,
    'end_date': FilterCategory.DATE,
    
    # Selection filters
    'status': FilterCategory.SELECTION,
    'category': FilterCategory.SELECTION,
    
    # Search filters
    'search': FilterCategory.SEARCH,
    'name': FilterCategory.SEARCH,
    
    # Amount filters
    'amount_from': FilterCategory.AMOUNT,
    'amount_to': FilterCategory.AMOUNT,
    
    # Relationship filters
    'branch_id': FilterCategory.RELATIONSHIP
}

YOUR_ENTITY_DEFAULT_FILTERS = {
    'status': 'active'  # Default active filter
}
```

### **Step 8: Document Configuration** 

```python
# Profile Document
YOUR_ENTITY_PROFILE_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type="profile",
    title="Entity Profile",
    page_size="A4",
    orientation="portrait",
    print_layout_type=PrintLayoutType.STANDARD,
    show_logo=True,
    show_company_info=True,
    header_text="ENTITY PROFILE",
    visible_tabs=["profile"],
    signature_fields=[
        {"label": "Verified By", "width": "200px"},
        {"label": "Approved By", "width": "200px"}
    ],
    show_footer=True,
    footer_text="System generated document",
    allowed_formats=["pdf", "print", "excel"]
)

YOUR_ENTITY_DOCUMENT_CONFIGS = {
    "profile": YOUR_ENTITY_PROFILE_CONFIG
}
```

### **Step 9: Create Main Configuration**

```python
YOUR_ENTITY_CONFIG = EntityConfiguration(
    # ========== REQUIRED PARAMETERS ==========
    entity_type="your_entities",
    name="Your Entity",
    plural_name="Your Entities", 
    service_name="your_entities",
    table_name="your_entities",
    primary_key="entity_id",
    title_field="entity_name",
    subtitle_field="category",
    icon="fas fa-cube",
    page_title="Your Entity Management",
    description="Manage your entities",
    searchable_fields=["entity_name", "category"],
    default_sort_field="entity_name",
    default_sort_direction="asc",
    
    # ========== CORE CONFIGURATIONS ==========
    fields=YOUR_ENTITY_FIELDS,
    section_definitions=YOUR_ENTITY_SECTIONS,
    view_layout=YOUR_ENTITY_VIEW_LAYOUT,
    actions=YOUR_ENTITY_ACTIONS,
    summary_cards=YOUR_ENTITY_SUMMARY_CARDS,
    permissions={
        "list": "entity_list",
        "view": "entity_view",
        "create": "entity_create", 
        "edit": "entity_edit",
        "delete": "entity_delete"
    },
    
    # ========== CRUD CONFIGURATION (v3.1) ==========
    entity_category=EntityCategory.MASTER,
    universal_crud_enabled=True,
    allowed_operations=[
        CRUDOperation.CREATE,
        CRUDOperation.READ,
        CRUDOperation.UPDATE,
        CRUDOperation.DELETE,
        CRUDOperation.LIST,
        CRUDOperation.VIEW,
        CRUDOperation.DOCUMENT
    ],
    model_class_path="app.models.master.YourEntity",
    primary_key_field="entity_id",
    create_fields=["entity_name", "category", "description"],
    edit_fields=["entity_name", "category", "description"],
    readonly_fields=["created_at", "updated_at"],
    
    # ========== DOCUMENT CONFIGURATION (v3.1) ==========
    document_enabled=True,
    document_configs=YOUR_ENTITY_DOCUMENT_CONFIGS,
    default_document="profile",
    include_calculated_fields=["calculated_total"],
    
    # ========== FILTER CONFIGURATION ==========
    filter_category_mapping=YOUR_ENTITY_FILTER_CATEGORY_MAPPING,
    default_filters=YOUR_ENTITY_DEFAULT_FILTERS,
    
    # ========== OPTIONAL SETTINGS ==========
    model_class="app.models.master.YourEntity",
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    primary_date_field="created_at"
)
```

---

## **7. CRUD Operations Configuration**

### **🔧 CRUD Service Integration**

The Universal CRUD Service automatically handles Create, Update, Delete operations for Master entities:

```python
class UniversalCRUDService:
    def create_entity(self, entity_type: str, data: dict, context: dict):
        """
        1. Validates entity category (master only)
        2. Loads model class dynamically  
        3. Applies field-level validation
        4. Delegates to entity service if available
        5. Performs database operation with session management
        """
        
    def update_entity(self, entity_type: str, item_id: str, data: dict, context: dict):
        """
        1. Validates category and permissions
        2. Loads existing entity
        3. Processes only editable fields
        4. Applies business rules through service
        5. Updates with proper session management
        """
        
    def delete_entity(self, entity_type: str, item_id: str, context: dict):
        """
        1. Validates category and permissions
        2. Checks delete conditions
        3. Verifies no dependent records
        4. Performs soft/hard delete as configured
        """
```

### **📝 Form Configuration**

#### **Field-Level CRUD Control**

```python
FieldDefinition(
    name="supplier_code",
    label="Supplier Code",
    field_type=FieldType.TEXT,
    
    # Form Control
    show_in_form=True,                   # Show in create/edit forms
    required=True,                       # Basic validation
    
    # CRUD-Specific Control
    create_required=True,                # Required in create form
    edit_required=False,                 # Optional in edit form
    create_readonly=False,               # Editable in create
    edit_readonly=True,                  # Read-only in edit
    
    # Validation
    validation={
        "minlength": 3,
        "maxlength": 10,
        "pattern": "^[A-Z0-9]+$",
        "custom_message": "Code must be uppercase alphanumeric"
    }
)
```

#### **Auto-Save Configuration**

```python
# Auto-save is enabled by default for all CRUD forms
# Data is saved to localStorage every 2 seconds after changes
# Restored automatically when form is reopened

# Disable auto-save for sensitive forms:
EntityConfiguration(
    # ... other config
    auto_save_enabled=False,             # Disable auto-save
    auto_save_interval=5000,             # Custom interval (ms)
    auto_save_exclude_fields=["password"] # Exclude sensitive fields
)
```

### **🎨 Form Layouts**

#### **Create Form**
- Uses `create_fields` list if specified, otherwise all `show_in_form=True` fields
- Applies `create_required` and `create_readonly` settings
- Auto-populates `default_value` settings
- Includes client-side and server-side validation

#### **Edit Form**  
- Uses `edit_fields` list if specified, otherwise all `show_in_form=True` fields
- Applies `edit_required` and `edit_readonly` settings
- Pre-populates with existing data
- Shows unsaved changes warning

---

## **8. Document Engine Configuration**

### **📄 Document Types**

```python
class DocumentType(Enum):
    RECEIPT = "receipt"                  # Transaction receipts
    INVOICE = "invoice"                  # Billing invoices
    STATEMENT = "statement"              # Account statements
    REPORT = "report"                    # General reports
    PROFILE = "profile"                  # Entity profiles
    SUMMARY = "summary"                  # Summary documents
```

### **🎨 Print Layout Types**

```python
class PrintLayoutType(Enum):
    SIMPLE = "simple"                    # Basic layout
    STANDARD = "standard"                # Standard with header/footer
    COMPACT = "compact"                  # Compact for small documents
    TABULAR = "tabular"                  # Table-heavy layouts
    SIMPLE_WITH_HEADER = "simple_with_header"  # Simple with header only
```

### **📃 Document Configuration Examples**

#### **Profile Document**
```python
ENTITY_PROFILE_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type="profile",
    title="Entity Profile",
    
    # Layout
    page_size="A4",
    orientation="portrait", 
    print_layout_type=PrintLayoutType.STANDARD,
    
    # Header
    show_logo=True,
    show_company_info=True,
    header_text="ENTITY MASTER PROFILE",
    
    # Content Control
    visible_tabs=["profile", "contact"],
    hidden_sections=["internal_notes"],
    custom_field_order=["name", "category", "contact_info"],
    
    # Footer
    signature_fields=[
        {"label": "Prepared By", "width": "200px"},
        {"label": "Verified By", "width": "200px"}
    ],
    show_footer=True,
    footer_text="System generated document - {current_date}",
    show_print_info=True,
    
    # Export Options
    allowed_formats=["pdf", "print", "excel", "word"],
    watermark_draft=False
)
```

#### **Statement Document**
```python  
ENTITY_STATEMENT_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type="statement",
    title="Entity Statement",
    
    # Layout for tabular data
    page_size="A4",
    orientation="landscape",
    print_layout_type=PrintLayoutType.TABULAR,
    
    # Content
    show_logo=True,
    header_text="ENTITY ACCOUNT STATEMENT",
    visible_tabs=["transactions"],
    
    # Line items table
    show_line_items=True,
    line_item_columns=["date", "description", "amount", "balance"],
    
    # Footer
    show_footer=True,
    footer_text="Statement Period: {from_date} to {to_date}",
    
    allowed_formats=["pdf", "print", "excel"]
)
```

### **🔗 Document Integration**

Documents are automatically integrated when you set:

```python
EntityConfiguration(
    # Enable documents
    document_enabled=True,
    
    # Define available documents  
    document_configs={
        "profile": ENTITY_PROFILE_CONFIG,
        "statement": ENTITY_STATEMENT_CONFIG
    },
    
    # Default document for quick access
    default_document="profile",
    
    # Fields to include in documents (calculated fields)
    include_calculated_fields=[
        "total_transactions",
        "current_balance", 
        "outstanding_amount"
    ]
)
```

### **📊 Document Generation Flow**

```
1. User views entity detail page
   └─> Universal Engine fetches complete data with calculations

2. Document buttons appear automatically
   └─> Based on document_configs and permissions

3. User clicks document button
   └─> No additional database queries - uses cached data

4. Document Service processes configuration
   └─> Applies layout, formatting, field selection

5. Universal document template renders
   └─> Print-friendly HTML generated

6. Optional PDF generation
   └─> ReportLab converts HTML to PDF
```

---

## **9. Advanced Features**

### **🔍 Advanced Filtering**

The Categorized Filter Processor automatically handles complex filtering:

```python
# Filter Categories
class FilterCategory(Enum):
    DATE = "date"                        # Date range filters
    AMOUNT = "amount"                    # Amount range filters  
    SEARCH = "search"                    # Text search filters
    SELECTION = "selection"              # Dropdown selections
    RELATIONSHIP = "relationship"        # Related entity filters
    BOOLEAN = "boolean"                  # True/false filters
    MULTI_SELECT = "multi_select"        # Multiple selections

# Configuration Example
ENTITY_FILTER_CATEGORY_MAPPING = {
    # Automatically creates date range picker
    'created_date': FilterCategory.DATE,
    'start_date': FilterCategory.DATE,
    'end_date': FilterCategory.DATE,
    
    # Creates amount range inputs  
    'amount_min': FilterCategory.AMOUNT,
    'amount_max': FilterCategory.AMOUNT,
    'total_amount': FilterCategory.AMOUNT,
    
    # Creates text search input
    'search': FilterCategory.SEARCH,
    'name_search': FilterCategory.SEARCH,
    
    # Creates dropdown with options
    'status': FilterCategory.SELECTION,
    'category': FilterCategory.SELECTION,
    
    # Creates related entity search
    'supplier_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP
}
```

### **📱 Responsive Design**

All Universal Engine templates are fully responsive:

```css
/* Automatic responsive breakpoints */
@media (max-width: 768px) {
    /* Mobile optimizations */
    .universal-table { display: block; }
    .universal-form { padding: 1rem; }
}

@media (max-width: 480px) {
    /* Phone optimizations */ 
    .summary-cards { grid-template-columns: 1fr; }
    .action-buttons { flex-direction: column; }
}
```

### **♿ Accessibility**

Built-in accessibility features:

```html
<!-- Semantic HTML structure -->
<main role="main">
  <section aria-label="Entity List">
    <table role="table" aria-label="Entity data">
      <thead>
        <tr role="row">
          <th role="columnheader" tabindex="0" aria-sort="ascending">
            Name
          </th>
        </tr>
      </thead>
    </table>
  </section>
</main>

<!-- Keyboard navigation support -->
<button tabindex="0" aria-label="Edit entity" role="button">
  <i class="fas fa-edit" aria-hidden="true"></i>
  Edit
</button>
```

### **🌐 Internationalization**

Multi-language support configuration:

```python
# Field labels with translations
FieldDefinition(
    name="supplier_name",
    label="Supplier Name",
    
    # Translation support
    translations={
        "hi": "आपूर्तिकर्ता नाम",
        "es": "Nombre del Proveedor",
        "fr": "Nom du Fournisseur"
    }
)

# Document translations
DocumentConfiguration(
    title="Supplier Profile",
    translations={
        "hi": {
            "title": "आपूर्तिकर्ता प्रोफ़ाइल",
            "header_text": "आपूर्तिकर्ता मास्टर प्रोफ़ाइल"
        }
    }
)
```

---

## **10. Best Practices & Patterns**

### **✅ Configuration Best Practices**

#### **1. Field Organization**
```python
# Good: Logical grouping with consistent order
FIELDS = [
    # System fields first (ID, timestamps)
    FieldDefinition(name="entity_id", view_order=0),
    FieldDefinition(name="created_at", view_order=1),
    
    # Core business fields  
    FieldDefinition(name="entity_name", view_order=10),
    FieldDefinition(name="category", view_order=11),
    
    # Contact information
    FieldDefinition(name="email", view_order=20),
    FieldDefinition(name="phone", view_order=21),
    
    # Calculated fields last
    FieldDefinition(name="calculated_total", view_order=100, virtual=True)
]
```

#### **2. Consistent Naming**
```python
# Good: Consistent naming conventions
entity_type="suppliers"           # Plural, lowercase
name="Supplier"                   # Singular, title case  
plural_name="Suppliers"           # Plural, title case
primary_key="supplier_id"         # entity_type_id pattern
title_field="supplier_name"       # entity_type_name pattern
```

#### **3. Permission Mapping**
```python
# Good: Consistent permission structure
permissions={
    "list": "suppliers_list",
    "view": "suppliers_view", 
    "create": "suppliers_create",
    "edit": "suppliers_edit",
    "delete": "suppliers_delete",
    "export": "suppliers_export"
}
```

#### **4. Section Organization**
```python
# Good: Logical section hierarchy
sections = {
    "identification": {
        "order": 1,
        "fields": ["id", "code", "name"]
    },
    "contact_info": {
        "order": 2, 
        "fields": ["email", "phone", "address"]
    },
    "business_info": {
        "order": 3,
        "fields": ["category", "gst_number", "pan_number"]
    },
    "financial_info": {
        "order": 4,
        "fields": ["payment_terms", "credit_limit"]
    }
}
```

### **🎯 Performance Patterns**

#### **1. Virtual Fields for Calculations**
```python
# Good: Mark calculated fields as virtual
FieldDefinition(
    name="outstanding_balance",
    field_type=FieldType.CURRENCY,
    virtual=True,                    # Not in database
    related_field="transactions",    # Calculated from relationships
    show_in_form=False              # Don't show in forms
)
```

#### **2. Efficient Filter Configuration**  
```python
# Good: Use appropriate filter types
filter_category_mapping = {
    'name': FilterCategory.SEARCH,        # Full-text search
    'status': FilterCategory.SELECTION,   # Predefined options
    'created_date': FilterCategory.DATE,  # Date range picker
    'amount': FilterCategory.AMOUNT       # Number range
}
```

#### **3. Smart Default Filters**
```python
# Good: Set reasonable defaults
default_filters = {
    'status': 'active',              # Hide inactive by default
    'date_range': 'current_year'     # Show current year data
}
```

### **🔒 Security Patterns**

#### **1. Field-Level Permissions**
```python
# Good: Control field visibility by permission
FieldDefinition(
    name="internal_notes",
    show_in_detail=True,
    permission_required="suppliers_view_internal",  # Custom permission
    conditional_display="user.has_permission('admin')"
)
```

#### **2. Document Permissions**
```python  
# Good: Control document access
document_permissions = {
    "profile": "suppliers_view_profile",
    "statement": "suppliers_view_financial",
    "confidential": "suppliers_admin"
}
```

### **🎨 UI/UX Patterns**

#### **1. Progressive Disclosure**
```python
# Good: Use tabs for complex entities
view_layout = ViewLayoutConfiguration(
    layout_type=LayoutType.TABBED,
    tabs={
        "basic": TabDefinition(
            title="Basic Info",
            sections=["identification", "contact"],
            order=1
        ),
        "advanced": TabDefinition(
            title="Advanced", 
            sections=["business_info", "financial"],
            order=2
        )
    }
)
```

#### **2. Contextual Actions**
```python
# Good: Show relevant actions per context
actions = [
    ActionDefinition(
        id="create",
        show_in_list=True,           # Show in list view
        show_in_detail=False         # Hide in detail view
    ),
    ActionDefinition(
        id="edit", 
        show_in_list=False,          # Hide in list view
        show_in_detail=True          # Show in detail view
    )
]
```

---

## **11. Troubleshooting Guide**

### **🚨 Common Issues**

| **Issue** | **Symptoms** | **Solution** |
|-----------|--------------|--------------|
| **Entity not found** | 404 error on entity URLs | Check entity registration in `entity_registry.py` |
| **Fields not displaying** | Empty forms or views | Verify `show_in_list`, `show_in_detail`, `show_in_form` settings |
| **CRUD operations blocked** | Create/edit buttons missing | Check `entity_category=MASTER` and `universal_crud_enabled=True` |
| **Documents not generating** | No document buttons | Set `document_enabled=True` and configure `document_configs` |
| **Filters not working** | No filter dropdowns | Configure `filter_category_mapping` |
| **Validation errors** | Form submission fails | Check `required` fields and `validation` rules |
| **Permission errors** | Access denied messages | Verify permission mappings and user permissions |
| **Performance issues** | Slow page loads | Use virtual fields for calculations, optimize queries |

### **🔍 Debugging Steps**

#### **1. Check Entity Registry**
```python
# Verify entity is registered
from app.config.entity_registry import ENTITY_REGISTRY
print(ENTITY_REGISTRY.get('your_entity'))
```

#### **2. Validate Configuration**
```python  
# Check configuration loading
from app.config.entity_configurations import get_entity_config
config = get_entity_config('your_entity')
print(f"Config loaded: {config is not None}")
print(f"Fields count: {len(config.fields) if config else 0}")
```

#### **3. Test Permissions**
```python
# Check user permissions
from flask_login import current_user
print(f"User permissions: {current_user.get_permissions()}")
```

#### **4. Review Logs**
```bash
# Check application logs for errors
tail -f logs/app.log | grep -i error
tail -f logs/app.log | grep -i your_entity
```

### **🛠️ Development Tools**

#### **Configuration Validator**
```python
def validate_entity_config(entity_type: str):
    """Validate entity configuration"""
    config = get_entity_config(entity_type)
    
    issues = []
    
    # Check required fields
    if not config.entity_type:
        issues.append("Missing entity_type")
        
    if not config.fields:
        issues.append("No fields defined")
        
    # Check field consistency  
    for field in config.fields:
        if field.required and field.readonly:
            issues.append(f"Field {field.name} cannot be both required and readonly")
            
    return issues
```

#### **Testing Helper**
```python
def test_entity_operations(entity_type: str):
    """Test basic entity operations"""
    from app.engine.universal_crud_service import UniversalCRUDService
    
    crud_service = UniversalCRUDService()
    
    # Test create
    try:
        result = crud_service.create_entity(entity_type, {
            "name": "Test Entity",
            "category": "test"
        }, {})
        print(f"Create test: {'✅' if result['success'] else '❌'}")
    except Exception as e:
        print(f"Create test failed: {e}")
```

---

## **12. Quick Reference**

### **📋 Configuration Checklist**

#### **New Entity Setup**
- [ ] Register in `entity_registry.py` with correct category
- [ ] Define fields with proper types and properties
- [ ] Configure sections and layout 
- [ ] Set up actions with correct permissions
- [ ] Configure summary cards
- [ ] Define filter categories
- [ ] Set up document configurations (if needed)
- [ ] Test all operations

#### **CRUD Configuration**
- [ ] Set `entity_category=EntityCategory.MASTER`
- [ ] Enable `universal_crud_enabled=True`  
- [ ] Define `allowed_operations` list
- [ ] Set `model_class_path` correctly
- [ ] Configure `create_fields` and `edit_fields`
- [ ] Set field-level CRUD properties
- [ ] Test create, edit, delete operations

#### **Document Configuration**
- [ ] Set `document_enabled=True`
- [ ] Configure document types needed
- [ ] Set appropriate layout types
- [ ] Define visible tabs and sections
- [ ] Configure export formats
- [ ] Add calculated fields to `include_calculated_fields`
- [ ] Test document generation

### **🎯 Field Configuration Quick Reference**

```python
# Text Field
FieldDefinition(
    name="field_name", label="Display Label",
    field_type=FieldType.TEXT, required=True,
    show_in_list=True, show_in_detail=True, show_in_form=True,
    searchable=True, sortable=True, filterable=True
)

# Selection Field  
FieldDefinition(
    name="status", label="Status",
    field_type=FieldType.SELECT,
    options=[{"value": "active", "label": "Active"}],
    required=True, default_value="active"
)

# Virtual Field
FieldDefinition(
    name="calculated_field", label="Calculated Value",
    field_type=FieldType.CURRENCY, virtual=True,
    show_in_form=False, readonly=True
)
```

### **📊 Layout Quick Reference**

```python
# Simple Layout - All sections visible
view_layout = ViewLayoutConfiguration(
    layout_type=LayoutType.SIMPLE
)

# Tabbed Layout - Organized in tabs  
view_layout = ViewLayoutConfiguration(
    layout_type=LayoutType.TABBED,
    tabs={"tab1": TabDefinition(...)}
)

# Accordion Layout - Collapsible sections
view_layout = ViewLayoutConfiguration(
    layout_type=LayoutType.ACCORDION
)
```

### **📄 Document Quick Reference**

```python  
# Basic Document
DocumentConfiguration(
    enabled=True, document_type="profile",
    title="Document Title", page_size="A4",
    orientation="portrait", show_logo=True,
    allowed_formats=["pdf", "print"]
)
```

### **🔗 URL Patterns**

| **Operation** | **URL Pattern** | **Example** |
|---------------|-----------------|-------------|
| **List** | `/universal/{entity}/list` | `/universal/suppliers/list` |
| **View** | `/universal/{entity}/detail/{id}` | `/universal/suppliers/detail/123` |
| **Create** | `/universal/{entity}/create` | `/universal/suppliers/create` |
| **Edit** | `/universal/{entity}/edit/{id}` | `/universal/suppliers/edit/123` |
| **Delete** | `/universal/{entity}/delete/{id}` | `/universal/suppliers/delete/123` |
| **Document** | `/universal/{entity}/document/{id}/{type}` | `/universal/suppliers/document/123/profile` |

---

## **🎉 Conclusion**

The Universal Engine v3.1 provides a powerful, configuration-driven approach to entity management that:

- **Maximizes Code Reuse**: One implementation serves all entities
- **Minimizes Development Time**: 90% time saving for master entities  
- **Ensures Consistency**: Same UX patterns across all modules
- **Maintains Flexibility**: Highly configurable without code changes
- **Provides Rich Features**: CRUD operations, document generation, advanced filtering
- **Ensures Scalability**: Easy to add new entities and features

By following this comprehensive guide, you can configure any entity to work seamlessly with the Universal Engine, providing rich functionality through simple configuration.

### **Key Takeaways**

1. **Start with Entity Registry**: Always register entities with correct categories
2. **Configure Thoroughly**: Complete configuration prevents runtime issues  
3. **Follow Patterns**: Use established patterns for consistency
4. **Test Incrementally**: Validate each component as you build
5. **Leverage Existing Examples**: Reference working configurations in the project

The Universal Engine v3.1 is production-ready and provides a solid foundation for managing all entities in the Skinspire Clinic HMS system.

---

**📚 Additional Resources**
- **Entity Registry**: `app/config/entity_registry.py`
- **Core Definitions**: `app/config/core_definitions.py`  
- **Working Examples**: `app/config/modules/financial_transactions.py`
- **Working Examples**: `app/config/modules/master_entities.py`
- **CRUD Service**: `app/engine/universal_crud_service.py`
- **Document Service**: `app/engine/document_service.py`

*Universal Engine v3.1 - Configuration-Driven Excellence*