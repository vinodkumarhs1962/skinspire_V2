# Universal Engine Entity Configuration Complete Guide v4.0
## The Definitive Reference for Universal Engine with CRUD, Documents & Dual-Layer Caching

---

## 📋 **Document Overview**

| **Attribute** | **Details** |
|---------------|-------------|
| **Project** | Skinspire Clinic HMS - Universal Engine |
| **Version** | v4.0 Comprehensive (Combines v3.1 + v3.2) |
| **Status** | **PRODUCTION READY** |
| **Last Updated** | December 2024 |
| **Architecture** | Configuration-Driven, Backend-Heavy, Entity-Agnostic, Dual-Layer Cached |
| **Core Features** | CRUD Operations, Document Engine, Search/Filter, Dual-Layer Caching |

---

## 📚 **Table of Contents**

### **Part I: Foundation**
1. [Universal Engine Overview](#1-universal-engine-overview)
2. [System Architecture](#2-system-architecture)
3. [Core Principles & Design Philosophy](#3-core-principles--design-philosophy)
4. [Entity Classification System](#4-entity-classification-system)

### **Part II: Configuration Structure**
5. [Configuration Components](#5-configuration-components)
6. [Core Definitions Reference](#6-core-definitions-reference)
7. [Field Configuration Guide](#7-field-configuration-guide)
8. [Layout & View Configuration](#8-layout--view-configuration)

### **Part III: Implementation**
9. [Step-by-Step Entity Setup](#9-step-by-step-entity-setup)
10. [Service Layer Implementation](#10-service-layer-implementation)
11. [CRUD Operations Configuration](#11-crud-operations-configuration)
12. [Document Engine Configuration](#12-document-engine-configuration)

### **Part IV: Performance & Caching**
13. [Dual-Layer Cache Architecture](#13-dual-layer-cache-architecture)
14. [Service Cache Configuration](#14-service-cache-configuration)
15. [Configuration Cache Setup](#15-configuration-cache-setup)
16. [Cache Management & Monitoring](#16-cache-management--monitoring)

### **Part V: Advanced Topics**
17. [Filter & Search Configuration](#17-filter--search-configuration)
18. [Permissions & Security](#18-permissions--security)
19. [Best Practices & Patterns](#19-best-practices--patterns)
20. [Troubleshooting & Debugging](#20-troubleshooting--debugging)

### **Part VI: Reference**
21. [Quick Reference Guide](#21-quick-reference-guide)
22. [Performance Benchmarks](#22-performance-benchmarks)
23. [URL Patterns & Routes](#23-url-patterns--routes)
24. [Appendix & Resources](#24-appendix--resources)

---

# **Part I: Foundation**

## **1. Universal Engine Overview**

### **🎯 What is the Universal Engine?**

The Universal Engine is a configuration-driven framework that provides complete entity management capabilities through configuration rather than code. It eliminates the need to write repetitive CRUD operations, UI templates, and business logic for each entity.

### **✨ Key Capabilities**

| **Feature** | **Description** | **Benefit** |
|-------------|-----------------|-------------|
| **Configuration-Driven** | Define entity behavior through configuration | 90% less code |
| **Dual-Layer Caching** | Automatic service & config caching | 90% faster performance |
| **CRUD Operations** | Create, Read, Update, Delete for master entities | Zero code required |
| **Document Generation** | PDF, Print, Excel documents | Configuration-based |
| **Advanced Filtering** | Category-based filters with caching | Highly performant |
| **Permission System** | Role-based access control | Secure by default |
| **Auto-Save** | Draft saving with conflict resolution | Better UX |
| **Responsive UI** | Mobile-first design | Works everywhere |

### **📊 Supported Entity Types**

| **Entity Category** | **CRUD** | **Documents** | **Cache** | **Example Entities** |
|---------------------|----------|---------------|-----------|----------------------|
| **Master** | ✅ Full | ✅ | ✅ | Suppliers, Patients, Users |
| **Transaction** | ❌ Read-only | ✅ | ✅ | Payments, Invoices, Bills |
| **Report** | ❌ Read-only | ✅ | ✅ | Analytics, Dashboards |
| **Lookup** | ✅ Limited | ❌ | ✅ | Countries, Categories |

---

## **2. System Architecture**

### **📐 High-Level Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Universal Engine v4.0 Architecture                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │   Browser   │───▶│   Routes    │───▶│ Universal   │                   │
│  │   Request   │    │  (Flask)    │    │   Views     │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│         │                                      │                           │
│         ▼                                      ▼                           │
│  ┌─────────────────────────────────────────────────────┐                 │
│  │            Entity Registry & Scope Controller        │                 │
│  │         (Validates operations per entity type)       │                 │
│  └─────────────────────────────────────────────────────┘                 │
│                           │                                               │
│                           ▼                                               │
│  ┌─────────────────────────────────────────────────────┐                 │
│  │           Configuration Loader (with Cache)          │◄──── Config    │
│  │         🆕 Hit Ratio: 95-100% after warmup          │      Cache     │
│  └─────────────────────────────────────────────────────┘      Layer     │
│                           │                                               │
│                           ▼                                               │
│  ┌─────────────────────────────────────────────────────┐                 │
│  │         Universal Service Layer (with Cache)         │◄──── Service   │
│  │         🆕 Hit Ratio: 70-90% for repeated queries   │      Cache     │
│  └─────────────────────────────────────────────────────┘      Layer     │
│                           │                                               │
│                           ▼                                               │
│  ┌─────────────────────────────────────────────────────┐                 │
│  │              Data Assembler & Formatter              │                 │
│  │    (Processes data for presentation, permissions)    │                 │
│  └─────────────────────────────────────────────────────┘                 │
│                           │                                               │
│                           ▼                                               │
│  ┌─────────────────────────────────────────────────────┐                 │
│  │          Universal Templates (Jinja2)                │                 │
│  │    (Dynamic forms, tables, documents, layouts)       │                 │
│  └─────────────────────────────────────────────────────┘                 │
│                           │                                               │
│                           ▼                                               │
│  ┌─────────────────────────────────────────────────────┐                 │
│  │        Progressive Enhancement (JavaScript)          │                 │
│  │    (Auto-save, validation, UI interactions)          │                 │
│  └─────────────────────────────────────────────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### **🔄 Request Flow with Caching**

```python
# 1. Request arrives at Universal View
@universal_bp.route('/universal/<entity_type>/list')
def universal_list_view(entity_type):
    
    # 2. Configuration loaded (CACHED - 100% hit ratio)
    config = get_entity_config(entity_type)  # ← Config Cache Hit
    
    # 3. Service fetches data (CACHED - 70-90% hit ratio)
    service = get_universal_service(entity_type)
    data = service.search_data(filters)  # ← Service Cache Hit
    
    # 4. Data assembled and rendered
    return render_template('universal_list.html', data=data)
```

---

## **3. Core Principles & Design Philosophy**

### **🎯 Design Principles**

#### **1. Configuration Over Code**
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

#### **2. Backend-Heavy Architecture**
- **Backend handles**: Business logic, calculations, database queries, caching
- **Frontend handles**: UI interactions, progressive enhancement
- **Never**: Put business logic in JavaScript

#### **3. Entity-Agnostic Design**
- One implementation for all entities
- No entity-specific code in universal components
- Configuration drives all differences

#### **4. Separation of Concerns**

| **Layer** | **Responsibility** | **Location** |
|-----------|-------------------|--------------|
| **Configuration** | Define entity behavior | `/config/modules/` |
| **Service** | Business logic & data | `/services/` |
| **View** | Request handling | `/views/` |
| **Template** | Presentation | `/templates/` |
| **Cache** | Performance | Automatic |

#### **5. Performance by Default**
- Dual-layer caching enabled automatically
- Lazy loading for related data
- Pagination for large datasets
- Optimized database queries

---

## **4. Entity Classification System**

### **📊 Entity Registry**

The Entity Registry (`app/config/entity_registry.py`) is the single source of truth for all entities:

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

class EntityCategory(Enum):
    MASTER = "master"           # Full CRUD support
    TRANSACTION = "transaction" # Read-only
    REPORT = "report"          # Read-only reports
    LOOKUP = "lookup"          # Simple lookups

@dataclass
class EntityRegistration:
    category: EntityCategory
    module: str                    # Config module path
    service_class: Optional[str]   # Service class path
    model_class: Optional[str]     # SQLAlchemy model path
    cache_enabled: bool = True     # 🆕 Enable caching
    cache_ttl: int = 1800          # 🆕 Cache TTL in seconds
    enabled: bool = True

# Central registry - single source of truth
ENTITY_REGISTRY: Dict[str, EntityRegistration] = {
    
    # Master Entities (Full CRUD + Cache)
    "suppliers": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.master_entities",
        service_class="app.services.supplier_master_service.SupplierMasterService",
        model_class="app.models.master.Supplier",
        cache_enabled=True,
        cache_ttl=3600  # 1 hour for master data
    ),
    
    "patients": EntityRegistration(
        category=EntityCategory.MASTER,
        module="app.config.modules.master_entities",
        service_class="app.services.patient_service.PatientService",
        model_class="app.models.master.Patient",
        cache_enabled=True,
        cache_ttl=3600
    ),
    
    # Transaction Entities (Read-only + Short Cache)
    "supplier_payments": EntityRegistration(
        category=EntityCategory.TRANSACTION,
        module="app.config.modules.financial_transactions",
        service_class="app.services.supplier_payment_service.SupplierPaymentService",
        model_class="app.models.transaction.SupplierPayment",
        cache_enabled=True,
        cache_ttl=300  # 5 minutes for transactions
    )
}
```

### **🔒 Operation Scope Control**

```python
class UniversalScopeController:
    """Controls what operations are allowed per entity category"""
    
    ALLOWED_OPERATIONS = {
        EntityCategory.MASTER: [
            CRUDOperation.CREATE,
            CRUDOperation.READ,
            CRUDOperation.UPDATE,
            CRUDOperation.DELETE,
            CRUDOperation.LIST,
            CRUDOperation.EXPORT,
            CRUDOperation.DOCUMENT
        ],
        EntityCategory.TRANSACTION: [
            CRUDOperation.READ,
            CRUDOperation.LIST,
            CRUDOperation.EXPORT,
            CRUDOperation.DOCUMENT
        ],
        EntityCategory.REPORT: [
            CRUDOperation.READ,
            CRUDOperation.LIST,
            CRUDOperation.EXPORT
        ],
        EntityCategory.LOOKUP: [
            CRUDOperation.READ,
            CRUDOperation.LIST,
            CRUDOperation.CREATE,
            CRUDOperation.UPDATE
        ]
    }
    
    def validate_operation(self, entity_type: str, operation: CRUDOperation) -> bool:
        """Check if operation is allowed for entity"""
        registration = ENTITY_REGISTRY.get(entity_type)
        if not registration:
            return False
        
        allowed = self.ALLOWED_OPERATIONS.get(registration.category, [])
        return operation in allowed
```

---

# **Part II: Configuration Structure**

## **5. Configuration Components**

### **🏗️ EntityConfiguration Structure**

```python
@dataclass
class EntityConfiguration:
    """Complete configuration for an entity"""
    
    # ========== BASIC INFO (Required) ==========
    entity_type: str                    # Unique identifier
    name: str                          # Display name
    plural_name: str                   # Plural display name
    service_name: str                  # Service identifier
    table_name: str                    # Database table
    primary_key: str                   # Primary key field
    title_field: str                   # Field for display title
    
    # ========== UI CONFIGURATION ==========
    icon: str = "fas fa-cube"         # FontAwesome icon
    page_title: str = None             # Page header title
    description: str = None            # Entity description
    subtitle_field: str = None         # Secondary display field
    
    # ========== FIELD DEFINITIONS ==========
    fields: List[FieldDefinition] = field(default_factory=list)
    searchable_fields: List[str] = field(default_factory=list)
    default_sort_field: str = None
    default_sort_direction: str = "asc"
    
    # ========== LAYOUT CONFIGURATION ==========
    section_definitions: Dict[str, SectionDefinition] = field(default_factory=dict)
    view_layout: ViewLayoutConfiguration = None
    summary_cards: List[Dict] = field(default_factory=list)
    
    # ========== CRUD CONFIGURATION ==========
    entity_category: EntityCategory = EntityCategory.MASTER
    universal_crud_enabled: bool = False
    allowed_operations: List[CRUDOperation] = field(default_factory=list)
    create_fields: List[str] = field(default_factory=list)
    edit_fields: List[str] = field(default_factory=list)
    readonly_fields: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    model_class_path: str = None
    primary_key_field: str = None
    
    # ========== DOCUMENT CONFIGURATION ==========
    document_enabled: bool = False
    document_configs: Dict[str, DocumentConfiguration] = field(default_factory=dict)
    default_document: str = None
    include_calculated_fields: List[str] = field(default_factory=list)
    
    # ========== FILTER CONFIGURATION ==========
    filter_category_mapping: Dict = field(default_factory=dict)
    default_filters: Dict = field(default_factory=dict)
    category_configs: Dict = field(default_factory=dict)
    
    # ========== CACHE CONFIGURATION (NEW) ==========
    cache_config: Dict = field(default_factory=lambda: {
        "enabled": True,
        "ttl": 1800,
        "max_entries": 1000,
        "invalidate_on_write": True,
        "cache_filters": True,
        "cache_detail_views": True,
        "warmup_on_startup": False,
        "exclude_fields": []
    })
    
    # ========== ACTION CONFIGURATION ==========
    actions: List[ActionDefinition] = field(default_factory=list)
    permissions: Dict[str, str] = field(default_factory=dict)
    
    # ========== DATE/TIME FIELDS ==========
    primary_date_field: str = None
    primary_amount_field: str = None
```

---

## **6. Core Definitions Reference**

### **📝 FieldDefinition**

```python
@dataclass
class FieldDefinition:
    """Defines a single field in an entity"""
    
    # Basic Properties
    name: str                          # Field name in database/model
    label: str                         # Display label
    field_type: FieldType              # Data type
    
    # Display Control
    show_in_list: bool = True         # Show in list view
    show_in_detail: bool = True       # Show in detail view
    show_in_form: bool = True         # Show in create/edit form
    show_in_filter: bool = False      # Show as filter option
    
    # Validation
    required: bool = False            # Field is required
    readonly: bool = False            # Field is read-only
    unique: bool = False              # Field must be unique
    
    # Search & Sort
    searchable: bool = False          # Include in text search
    sortable: bool = False            # Allow sorting
    filterable: bool = False          # Allow filtering
    
    # Form Properties
    placeholder: str = None           # Input placeholder
    help_text: str = None            # Help text
    default_value: Any = None        # Default value
    options: List[Dict] = None       # Options for SELECT
    
    # Layout
    tab_group: str = None            # Tab assignment
    section: str = None              # Section assignment
    view_order: int = 0              # Display order
    column_width: str = None         # Bootstrap column class
    
    # CRUD Specific
    create_required: bool = None     # Required on create
    edit_required: bool = None       # Required on edit
    create_readonly: bool = False    # Readonly on create
    edit_readonly: bool = False      # Readonly on edit
    
    # Advanced
    virtual: bool = False            # Calculated field
    relationship: str = None         # Related entity
    renderer: str = None             # Custom renderer
    validator: str = None            # Custom validator
    
    # Document Specific
    document_format: str = None      # Format in documents
    document_label: str = None       # Label in documents
    print_format: str = None         # Print format
```

### **🎨 FieldType Enum**

```python
class FieldType(Enum):
    """Available field types"""
    
    # Text Types
    TEXT = "text"
    TEXTAREA = "textarea"
    EMAIL = "email"
    URL = "url"
    PASSWORD = "password"
    
    # Numeric Types
    INTEGER = "integer"
    DECIMAL = "decimal"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    
    # Date/Time Types
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    
    # Selection Types
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    MULTISELECT = "multiselect"
    
    # Special Types
    UUID = "uuid"
    JSON = "json"
    FILE = "file"
    IMAGE = "image"
    BOOLEAN = "boolean"
    
    # Relationship Types
    FOREIGN_KEY = "foreign_key"
    MANY_TO_MANY = "many_to_many"
```

---

## **7. Field Configuration Guide**

### **📋 Common Field Patterns**

#### **Primary Key Field**
```python
FieldDefinition(
    name="entity_id",
    label="ID",
    field_type=FieldType.UUID,
    show_in_list=False,
    show_in_detail=True,
    show_in_form=False,
    readonly=True,
    view_order=0
)
```

#### **Required Text Field**
```python
FieldDefinition(
    name="name",
    label="Name",
    field_type=FieldType.TEXT,
    required=True,
    searchable=True,
    sortable=True,
    filterable=True,
    placeholder="Enter name",
    help_text="Full legal name",
    view_order=1
)
```

#### **Selection Field**
```python
FieldDefinition(
    name="status",
    label="Status",
    field_type=FieldType.SELECT,
    options=[
        {"value": "active", "label": "Active", "color": "success"},
        {"value": "inactive", "label": "Inactive", "color": "danger"},
        {"value": "pending", "label": "Pending", "color": "warning"}
    ],
    required=True,
    default_value="active",
    filterable=True,
    view_order=2
)
```

#### **Currency Field**
```python
FieldDefinition(
    name="amount",
    label="Amount",
    field_type=FieldType.CURRENCY,
    required=True,
    sortable=True,
    filterable=True,
    renderer="currency_renderer",
    document_format="currency",
    view_order=3
)
```

#### **Virtual/Calculated Field**
```python
FieldDefinition(
    name="total_outstanding",
    label="Outstanding Balance",
    field_type=FieldType.CURRENCY,
    virtual=True,
    show_in_form=False,
    readonly=True,
    renderer="calculate_outstanding",
    view_order=4
)
```

#### **Relationship Field**
```python
FieldDefinition(
    name="supplier_id",
    label="Supplier",
    field_type=FieldType.FOREIGN_KEY,
    relationship="suppliers",
    required=True,
    searchable=True,
    filterable=True,
    renderer="supplier_name_renderer",
    view_order=5
)
```

---

## **8. Layout & View Configuration**

### **🎨 Layout Types**

```python
class LayoutType(Enum):
    SIMPLE = "simple"        # All sections visible
    TABBED = "tabbed"       # Organized in tabs
    ACCORDION = "accordion"  # Collapsible sections
    WIZARD = "wizard"       # Step-by-step form
```

### **📐 Section Configuration**

```python
# Define sections for grouping fields
ENTITY_SECTIONS = {
    "basic_info": SectionDefinition(
        key="basic_info",
        title="Basic Information",
        icon="fas fa-info-circle",
        columns=2,
        collapsible=False,
        initially_collapsed=False,
        show_in_create=True,
        show_in_edit=True,
        show_in_view=True,
        order=1
    ),
    "contact_info": SectionDefinition(
        key="contact_info",
        title="Contact Information",
        icon="fas fa-address-book",
        columns=2,
        collapsible=True,
        initially_collapsed=False,
        show_in_create=True,
        show_in_edit=True,
        show_in_view=True,
        order=2
    ),
    "financial_info": SectionDefinition(
        key="financial_info",
        title="Financial Details",
        icon="fas fa-dollar-sign",
        columns=1,
        collapsible=True,
        initially_collapsed=True,
        show_in_create=False,
        show_in_edit=True,
        show_in_view=True,
        order=3
    )
}
```

### **📑 Tab Configuration**

```python
# Define tabs for tabbed layout
ENTITY_TABS = {
    "profile": TabDefinition(
        key="profile",
        label="Profile",
        icon="fas fa-user",
        sections=["basic_info", "contact_info"],
        order=1,
        show_in_create=True,
        show_in_edit=True,
        show_in_view=True
    ),
    "financial": TabDefinition(
        key="financial",
        label="Financial",
        icon="fas fa-money-bill",
        sections=["financial_info", "payment_terms"],
        order=2,
        show_in_create=False,
        show_in_edit=True,
        show_in_view=True
    ),
    "documents": TabDefinition(
        key="documents",
        label="Documents",
        icon="fas fa-file-alt",
        sections=["documents"],
        order=3,
        show_in_create=False,
        show_in_edit=False,
        show_in_view=True
    )
}
```

### **🖼️ View Layout Configuration**

```python
# Configure the overall layout
ENTITY_VIEW_LAYOUT = ViewLayoutConfiguration(
    layout_type=LayoutType.TABBED,
    tabs=ENTITY_TABS,
    sections=ENTITY_SECTIONS,
    show_header=True,
    show_sidebar=False,
    show_breadcrumb=True,
    show_actions=True,
    enable_quick_edit=True,
    enable_auto_save=True,
    auto_save_interval=30,  # seconds
    confirmation_required=True,
    confirmation_message="Are you sure you want to save changes?"
)
```

---

# **Part III: Implementation**

## **9. Step-by-Step Entity Setup**

### **🚀 Complete Entity Setup Process**

#### **Step 1: Register Entity in Registry**

```python
# File: app/config/entity_registry.py

ENTITY_REGISTRY["your_entity"] = EntityRegistration(
    category=EntityCategory.MASTER,
    module="app.config.modules.your_module",
    service_class="app.services.your_entity_service.YourEntityService",
    model_class="app.models.master.YourEntity",
    cache_enabled=True,
    cache_ttl=1800  # 30 minutes
)
```

#### **Step 2: Create Configuration Module**

```python
# File: app/config/modules/your_module.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import *
from app.config.filter_categories import FilterCategory

# Step 2.1: Define Fields
YOUR_ENTITY_FIELDS = [
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
    FieldDefinition(
        name="name",
        label="Name",
        field_type=FieldType.TEXT,
        required=True,
        searchable=True,
        sortable=True,
        filterable=True,
        placeholder="Enter name",
        tab_group="profile",
        section="basic_info",
        view_order=1
    ),
    # ... more fields
]

# Step 2.2: Define Sections
YOUR_ENTITY_SECTIONS = {
    "basic_info": SectionDefinition(
        key="basic_info",
        title="Basic Information",
        icon="fas fa-info-circle",
        columns=2,
        order=1
    ),
    # ... more sections
}

# Step 2.3: Define Tabs
YOUR_ENTITY_TABS = {
    "profile": TabDefinition(
        key="profile",
        label="Profile",
        icon="fas fa-user",
        sections=["basic_info"],
        order=1
    ),
    # ... more tabs
}

# Step 2.4: Configure Layout
YOUR_ENTITY_VIEW_LAYOUT = ViewLayoutConfiguration(
    layout_type=LayoutType.TABBED,
    tabs=YOUR_ENTITY_TABS,
    sections=YOUR_ENTITY_SECTIONS
)

# Step 2.5: Configure Actions
YOUR_ENTITY_ACTIONS = [
    ActionDefinition(
        id="create",
        label="Create New",
        icon="fas fa-plus",
        button_type=ButtonType.PRIMARY,
        action_type=ActionDisplayType.HEADER_BUTTON,
        url_pattern="/universal/your_entity/create",
        permission_required="your_entity.create",
        show_in_list=True,
        show_in_detail=False
    ),
    # ... more actions
]

# Step 2.6: Configure Summary Cards
YOUR_ENTITY_SUMMARY_CARDS = [
    {
        "id": "total_active",
        "title": "Active Records",
        "icon": "fas fa-check-circle",
        "color": "success",
        "value_field": "total_active",
        "link": "?status=active",
        "show_trend": True
    },
    # ... more cards
]

# Step 2.7: Configure Filters
YOUR_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    supported_categories=[
        FilterCategory.STATUS,
        FilterCategory.DATE_RANGE,
        FilterCategory.SEARCH
    ],
    category_configs={
        FilterCategory.STATUS: {
            "field": "status",
            "options": [
                {"value": "active", "label": "Active"},
                {"value": "inactive", "label": "Inactive"}
            ]
        }
    }
)

# Step 2.8: Configure Documents
YOUR_ENTITY_DOCUMENT_CONFIGS = {
    "profile": DocumentConfiguration(
        enabled=True,
        document_type="profile",
        title="Entity Profile",
        page_size="A4",
        orientation="portrait",
        show_logo=True,
        allowed_formats=["pdf", "print"]
    )
}

# Step 2.9: Create Main Configuration
YOUR_ENTITY_CONFIG = EntityConfiguration(
    # Basic Info
    entity_type="your_entity",
    name="Your Entity",
    plural_name="Your Entities",
    service_name="your_entity",
    table_name="your_entities",
    primary_key="entity_id",
    title_field="name",
    
    # Components
    fields=YOUR_ENTITY_FIELDS,
    section_definitions=YOUR_ENTITY_SECTIONS,
    view_layout=YOUR_ENTITY_VIEW_LAYOUT,
    actions=YOUR_ENTITY_ACTIONS,
    summary_cards=YOUR_ENTITY_SUMMARY_CARDS,
    
    # CRUD Configuration
    entity_category=EntityCategory.MASTER,
    universal_crud_enabled=True,
    allowed_operations=[
        CRUDOperation.CREATE,
        CRUDOperation.READ,
        CRUDOperation.UPDATE,
        CRUDOperation.DELETE
    ],
    create_fields=["name", "status", "category"],
    edit_fields=["name", "status", "category"],
    readonly_fields=["entity_id", "created_at"],
    
    # Document Configuration
    document_enabled=True,
    document_configs=YOUR_ENTITY_DOCUMENT_CONFIGS,
    
    # Filter Configuration
    filter_category_mapping=YOUR_ENTITY_FILTER_CONFIG.category_configs,
    
    # Cache Configuration
    cache_config={
        "enabled": True,
        "ttl": 1800,
        "invalidate_on_write": True,
        "warmup_on_startup": True
    }
)

# Step 2.10: Register Configuration
def get_module_configs():
    """Return all configurations from this module"""
    return {
        "your_entity": YOUR_ENTITY_CONFIG
    }
```

---

## **10. Service Layer Implementation**

### **🔧 Service Implementation with Caching**

```python
# File: app/services/your_entity_service.py

from app.engine.universal_entity_service import UniversalEntityService
from app.engine.universal_service_cache import cache_service_method
from app.models.master import YourEntity
from typing import Dict, Any, Optional, List

class YourEntityService(UniversalEntityService):
    """Service for Your Entity with caching"""
    
    def __init__(self):
        super().__init__('your_entity', YourEntity)
        self.entity_type = 'your_entity'  # Required for cache
    
    # ========== CACHED READ OPERATIONS ==========
    
    @cache_service_method()  # Automatic caching
    def search_data(self, filters: dict, **kwargs) -> dict:
        """Search entities with caching"""
        return super().search_data(filters, **kwargs)
    
    @cache_service_method()
    def get_item_data(self, item_id: str, **kwargs) -> dict:
        """Get entity details with caching"""
        return super().get_item_data(item_id, **kwargs)
    
    @cache_service_method()
    def get_list_data(self, filters: dict, **kwargs) -> dict:
        """Get entity list with caching"""
        return super().get_list_data(filters, **kwargs)
    
    # ========== WRITE OPERATIONS (Clear Cache) ==========
    
    def create_entity(self, data: dict, user_context: dict) -> dict:
        """Create entity and clear cache"""
        result = super().create_entity(data, user_context)
        
        if result.get('success'):
            # Clear cache for this entity type
            self._invalidate_entity_cache()
        
        return result
    
    def update_entity(self, entity_id: str, data: dict, user_context: dict) -> dict:
        """Update entity and clear cache"""
        result = super().update_entity(entity_id, data, user_context)
        
        if result.get('success'):
            # Clear cache for this entity type
            self._invalidate_entity_cache()
        
        return result
    
    def delete_entity(self, entity_id: str, user_context: dict) -> dict:
        """Delete entity and clear cache"""
        result = super().delete_entity(entity_id, user_context)
        
        if result.get('success'):
            # Clear cache for this entity type
            self._invalidate_entity_cache()
        
        return result
    
    # ========== CACHE MANAGEMENT ==========
    
    def _invalidate_entity_cache(self):
        """Clear all cache entries for this entity"""
        from app.engine.universal_service_cache import get_service_cache_manager
        
        cache_manager = get_service_cache_manager()
        # Clear all cache entries for this entity type
        cleared = 0
        for key in list(cache_manager.cache_store.keys()):
            if self.entity_type in key:
                del cache_manager.cache_store[key]
                cleared += 1
        
        if cleared > 0:
            logger.info(f"Cleared {cleared} cache entries for {self.entity_type}")
    
    # ========== CUSTOM BUSINESS LOGIC ==========
    
    def calculate_summary_stats(self, hospital_id: str) -> dict:
        """Calculate summary statistics (custom method)"""
        # Custom business logic here
        pass
    
    @cache_service_method(ttl=300)  # Custom TTL: 5 minutes
    def get_dashboard_metrics(self, filters: dict) -> dict:
        """Get dashboard metrics with short cache"""
        # Implementation
        pass
```

---

## **11. CRUD Operations Configuration**

### **🔧 CRUD Configuration Details**

```python
# CRUD-specific configuration in EntityConfiguration

entity_category=EntityCategory.MASTER,  # Enables full CRUD
universal_crud_enabled=True,

# Define allowed operations explicitly
allowed_operations=[
    CRUDOperation.CREATE,
    CRUDOperation.READ,
    CRUDOperation.UPDATE,
    CRUDOperation.DELETE,
    CRUDOperation.LIST,
    CRUDOperation.EXPORT
],

# Field-level CRUD control
create_fields=[  # Fields shown in create form
    "name", "category", "status", "description"
],

edit_fields=[  # Fields shown in edit form
    "name", "category", "status", "description", "notes"
],

readonly_fields=[  # Never editable
    "entity_id", "created_at", "created_by", "updated_at"
],

required_fields=[  # Must have values
    "name", "category"
],

# Model configuration
model_class_path="app.models.master.YourEntity",
primary_key_field="entity_id"
```

### **📝 Field-Level CRUD Properties**

```python
FieldDefinition(
    name="status",
    label="Status",
    
    # General display
    show_in_list=True,
    show_in_detail=True,
    show_in_form=True,
    
    # CRUD-specific
    create_required=True,      # Required on create
    create_readonly=False,     # Editable on create
    edit_required=False,       # Optional on edit
    edit_readonly=False,       # Editable on edit
    
    # Default for create
    default_value="active",
    
    # Validation
    validator="validate_status_change"  # Custom validator
)
```

---

## **12. Document Engine Configuration**

### **📄 Document Configuration**

```python
# Document configuration for an entity

from app.config.core_definitions import (
    DocumentConfiguration, PrintLayoutType, 
    PageSize, Orientation
)

# Profile Document
ENTITY_PROFILE_DOC = DocumentConfiguration(
    enabled=True,
    document_type="profile",
    title="Entity Master Profile",
    
    # Page Setup
    page_size=PageSize.A4,
    orientation=Orientation.PORTRAIT,
    margins={"top": 20, "bottom": 20, "left": 15, "right": 15},
    
    # Layout
    print_layout_type=PrintLayoutType.STANDARD,
    show_logo=True,
    show_company_info=True,
    show_header=True,
    show_footer=True,
    
    # Content Control
    visible_tabs=["profile", "financial"],
    visible_sections=["basic_info", "contact_info"],
    exclude_fields=["password", "internal_notes"],
    
    # Header/Footer
    header_text="CONFIDENTIAL - ENTITY PROFILE",
    footer_text="System Generated Document - Page {page}",
    
    # Signatures
    signature_fields=[
        {"label": "Prepared By", "width": "200px"},
        {"label": "Verified By", "width": "200px"},
        {"label": "Approved By", "width": "200px"}
    ],
    
    # Export Options
    allowed_formats=["pdf", "print", "excel"],
    default_format="pdf",
    
    # Styling
    css_classes=["document-professional"],
    watermark=None
)

# Statement Document
ENTITY_STATEMENT_DOC = DocumentConfiguration(
    enabled=True,
    document_type="statement",
    title="Account Statement",
    page_size=PageSize.A4,
    orientation=Orientation.LANDSCAPE,
    
    # Include transaction table
    include_tables=["transactions"],
    table_configs={
        "transactions": {
            "columns": ["date", "description", "debit", "credit", "balance"],
            "show_totals": True,
            "pagination": 20  # Rows per page
        }
    }
)

# Register documents
ENTITY_DOCUMENT_CONFIGS = {
    "profile": ENTITY_PROFILE_DOC,
    "statement": ENTITY_STATEMENT_DOC
}
```

---

# **Part IV: Performance & Caching**

## **13. Dual-Layer Cache Architecture**

### **🚀 Cache Overview**

The Universal Engine implements two complementary cache layers:

| **Cache Layer** | **What It Caches** | **Hit Ratio** | **TTL** | **Impact** |
|-----------------|-------------------|---------------|---------|------------|
| **Service Cache** | Database query results | 70-90% | 30 min | 70% faster |
| **Config Cache** | Entity configurations | 95-100% | 1 hour | 20% faster |
| **Combined** | Both layers | 85-95% | Varies | 90% faster |

### **📊 Cache Flow Diagram**

```
Request → Check Service Cache → HIT? → Return Cached Data
              ↓ MISS
         Load Configuration (Check Config Cache)
              ↓
         Execute Database Query
              ↓
         Store in Service Cache
              ↓
         Return Fresh Data
```

---

## **14. Service Cache Configuration**

### **🔧 Basic Setup**

```python
# Step 1: Import cache decorator
from app.engine.universal_service_cache import cache_service_method

# Step 2: Apply to service methods
class YourService(UniversalEntityService):
    
    @cache_service_method()  # Default settings
    def search_data(self, filters: dict, **kwargs) -> dict:
        return super().search_data(filters, **kwargs)
    
    @cache_service_method(ttl=600)  # Custom 10-minute TTL
    def get_summary(self, **kwargs) -> dict:
        # Your implementation
        pass
```

### **⚙️ Advanced Configuration**

```python
# In EntityConfiguration
cache_config={
    # Basic Settings
    "enabled": True,                    # Enable/disable cache
    "ttl": 1800,                        # Time-to-live in seconds
    
    # Size Limits
    "max_entries": 1000,                # Max cached items
    "max_memory_mb": 50,                # Max memory per entity
    
    # Behavior
    "invalidate_on_write": True,        # Clear on create/update/delete
    "cache_filters": True,               # Cache filtered queries
    "cache_detail_views": True,          # Cache detail views
    "cache_aggregates": False,           # Cache summary stats
    
    # Performance
    "warmup_on_startup": True,          # Preload common queries
    "warmup_queries": [                 # Queries to preload
        {"status": "active"},
        {"branch_id": "main"}
    ],
    
    # Cache Key Control
    "exclude_fields": [                 # Exclude from cache key
        "created_at", 
        "updated_at",
        "last_accessed"
    ],
    
    # TTL by Operation
    "operation_ttl": {
        "list": 1800,      # 30 minutes for lists
        "detail": 3600,    # 1 hour for details
        "search": 900,     # 15 minutes for search
        "aggregate": 300   # 5 minutes for stats
    }
}
```

### **🔄 Cache Invalidation Patterns**

```python
# Automatic invalidation on write operations
def update_entity(self, entity_id: str, data: dict) -> dict:
    result = super().update_entity(entity_id, data)
    
    if result.get('success'):
        # Automatic cache invalidation
        self._invalidate_entity_cache()
        
        # Optional: Selective invalidation
        self._invalidate_specific_cache(entity_id)
    
    return result

# Manual cache management
from app.engine.universal_service_cache import get_service_cache_manager

def clear_all_entity_cache(entity_type: str):
    """Clear all cache for an entity type"""
    cache_manager = get_service_cache_manager()
    
    cleared = 0
    for key in list(cache_manager.cache_store.keys()):
        if entity_type in key:
            del cache_manager.cache_store[key]
            cleared += 1
    
    return cleared
```

---

## **15. Configuration Cache Setup**

### **🔧 Configuration Cache (Automatic)**

The configuration cache is **fully automatic** - no setup required!

```python
# Automatically cached on first access
config = get_entity_config('your_entity')  # First call: ~10ms
config = get_entity_config('your_entity')  # Second call: ~0.01ms (1000x faster!)
```

### **📊 What Gets Cached**

- Entity configurations
- Field definitions
- Section & tab layouts
- Filter configurations
- Search configurations
- Document configurations
- Permission mappings

### **⚙️ Configuration**

```python
# In app/__init__.py
def initialize_cache_system(app):
    """Initialize caching system"""
    
    # Configuration cache settings
    app.config['CONFIG_CACHE_ENABLED'] = True
    app.config['CONFIG_CACHE_PRELOAD'] = True  # Preload common configs
    app.config['CONFIG_CACHE_TTL'] = 3600      # 1 hour TTL
    
    # Initialize
    from app.engine.universal_config_cache import init_config_cache
    init_config_cache(app)
```

---

## **16. Cache Management & Monitoring**

### **📊 Cache Dashboard**

Access real-time cache statistics at `/admin/cache-dashboard`:

- Hit ratios by entity
- Memory usage
- Cache size
- Performance metrics
- Clear/warm controls

### **🔍 Monitoring Cache Performance**

```python
# Get cache statistics programmatically
from app.engine.universal_service_cache import get_service_cache_manager
from app.engine.universal_config_cache import get_cached_configuration_loader

# Service cache stats
service_cache = get_service_cache_manager()
service_stats = service_cache.get_cache_statistics()
print(f"Service Cache Hit Ratio: {service_stats['hit_ratio']:.2%}")
print(f"Service Cache Entries: {service_stats['cache_size']}")

# Config cache stats
config_cache = get_cached_configuration_loader()
config_stats = config_cache.get_cache_statistics()
print(f"Config Cache Hit Ratio: {config_stats['hit_ratio']:.2%}")
```

### **🔧 Cache CLI Commands**

```bash
# View cache status
python -m app.cache_cli status

# Clear all caches
python -m app.cache_cli clear --all

# Clear specific entity cache
python -m app.cache_cli clear --entity suppliers

# Warm up caches
python -m app.cache_cli warmup

# Monitor cache (live)
python -m app.cache_cli monitor
```

### **🚀 Cache Optimization Tips**

1. **Choose Appropriate TTL**
   - Master data: 1-2 hours
   - Transactions: 5-15 minutes
   - Real-time data: 1-2 minutes

2. **Exclude Volatile Fields**
   ```python
   cache_config={
       "exclude_fields": ["last_accessed", "view_count"]
   }
   ```

3. **Use Warmup for Common Queries**
   ```python
   cache_config={
       "warmup_queries": [
           {"status": "active"},
           {"created_date": "today"}
       ]
   }
   ```

4. **Monitor Memory Usage**
   - Keep under 500MB total
   - Set max_entries limits
   - Use shorter TTL if needed

---

# **Part V: Advanced Topics**

## **17. User Preferences & Custom Validation**

### **🔧 User Preferences System**

The Universal Engine leverages the `ui_preferences` JSONB field in the User model for user-specific customization:

```python
# User model structure
class User(Base):
    user_id = Column(String(15), primary_key=True)
    ui_preferences = Column(JSONB, default={})  # Stores user preferences
    # ... other fields
```

#### **Implementation Example: Deleted Records Visibility**

```python
# In universal_entity_service.py
def _get_user_show_deleted_preference(self, user: Optional[Any] = None) -> bool:
    """Get user's preference for showing deleted records"""
    show_deleted = False
    
    try:
        # Check user's ui_preferences
        if user and hasattr(user, 'ui_preferences') and user.ui_preferences:
            show_deleted = user.ui_preferences.get('show_deleted_records', False)
        
        # Fallback to current_user if no user provided
        if not user:
            from flask_login import current_user
            if current_user and hasattr(current_user, 'ui_preferences'):
                show_deleted = current_user.ui_preferences.get('show_deleted_records', False)
        
        return show_deleted
        
    except Exception as e:
        logger.warning(f"Error getting show_deleted preference: {e}")
        return False  # Safe default

def _get_base_query(self, session: Session, hospital_id: uuid.UUID, 
                    branch_id: Optional[uuid.UUID], user: Optional[Any] = None):
    """Apply user preferences to base query"""
    query = session.query(self.model_class)
    
    # Apply soft delete filter based on user preference
    show_deleted = self._get_user_show_deleted_preference(user)
    
    if not show_deleted:
        # Check multiple possible soft delete fields
        if hasattr(self.model_class, 'is_deleted'):
            query = query.filter(self.model_class.is_deleted == False)
        elif hasattr(self.model_class, 'deleted_flag'):
            query = query.filter(self.model_class.deleted_flag == False)
    
    return query
```

#### **Available User Preferences**

```python
# Common user preferences stored in ui_preferences
ui_preferences = {
    # Display Preferences
    "theme": "dark",                      # UI theme
    "show_deleted_records": False,        # Show soft-deleted records
    "records_per_page": 20,               # Pagination size
    "default_view": "grid",               # List view type (grid/table)
    "compact_mode": False,                # Compact display mode
    
    # Behavior Preferences
    "auto_save_enabled": True,            # Auto-save in forms
    "auto_save_interval": 30,             # Auto-save interval (seconds)
    "confirm_delete": True,               # Require delete confirmation
    "enable_shortcuts": True,             # Keyboard shortcuts
    
    # Entity-Specific Preferences
    "default_filters": {
        "suppliers": {"status": "active"},
        "payments": {"date_range": "month"}
    },
    "column_visibility": {
        "suppliers": ["name", "email", "status"],
        "payments": ["date", "amount", "status"]
    },
    
    # Notification Preferences
    "email_notifications": True,
    "push_notifications": False,
    "notification_frequency": "immediate"
}
```

#### **Updating User Preferences**

```python
# Route to update user preferences
@universal_bp.route('/preferences/update', methods=['POST'])
@login_required
def update_preferences():
    """Update user preferences"""
    from sqlalchemy.orm.attributes import flag_modified
    
    preference_key = request.form.get('key')
    preference_value = request.form.get('value')
    
    with get_db_session() as session:
        user = session.query(User).filter_by(user_id=current_user.user_id).first()
        
        if not user.ui_preferences:
            user.ui_preferences = {}
        
        # Update preference
        user.ui_preferences[preference_key] = preference_value
        
        # Mark JSONB field as modified (required for SQLAlchemy)
        flag_modified(user, "ui_preferences")
        
        session.commit()
    
    return jsonify({"success": True})
```

---

## **18. Advanced Field Configuration**

### **🎨 Complex Display Types**

```python
from enum import Enum

class ComplexDisplayType(Enum):
    """Advanced display patterns for fields"""
    BADGE = "badge"                    # Status badge
    PROGRESS_BAR = "progress_bar"      # Progress indicator
    RATING = "rating"                  # Star rating
    TAG_LIST = "tag_list"             # Multiple tags
    TIMELINE = "timeline"              # Timeline view
    CHART = "chart"                    # Mini chart
    AVATAR = "avatar"                  # User avatar
    COLOR_PICKER = "color_picker"     # Color selection
    CODE_EDITOR = "code_editor"       # Code with syntax highlight
    MARKDOWN = "markdown"              # Markdown renderer
    JSON_VIEWER = "json_viewer"        # JSON tree view
```

#### **Field with Complex Display**

```python
FieldDefinition(
    name="status",
    label="Status",
    field_type=FieldType.SELECT,
    complex_display_type=ComplexDisplayType.BADGE,
    
    # Badge configuration
    display_config={
        "badge_colors": {
            "active": "success",
            "pending": "warning",
            "inactive": "danger"
        },
        "badge_icons": {
            "active": "fas fa-check",
            "pending": "fas fa-clock",
            "inactive": "fas fa-times"
        }
    }
)

FieldDefinition(
    name="completion",
    label="Progress",
    field_type=FieldType.PERCENTAGE,
    complex_display_type=ComplexDisplayType.PROGRESS_BAR,
    
    # Progress bar configuration
    display_config={
        "show_percentage": True,
        "color_thresholds": {
            0: "danger",     # 0-33% red
            33: "warning",   # 33-66% yellow
            66: "success"    # 66-100% green
        },
        "striped": True,
        "animated": True
    }
)
```

### **🔄 Conditional Display**

Fields can be shown/hidden based on conditions:

```python
FieldDefinition(
    name="discount_reason",
    label="Discount Reason",
    field_type=FieldType.TEXTAREA,
    
    # Only show if discount is applied
    conditional_display="item.discount_percentage > 0",
    
    # Multiple conditions
    conditional_display={
        "type": "AND",  # AND/OR
        "conditions": [
            "item.discount_percentage > 0",
            "item.status != 'draft'"
        ]
    }
)

FieldDefinition(
    name="approval_notes",
    label="Approval Notes",
    field_type=FieldType.TEXTAREA,
    
    # Show based on user role
    conditional_display="user.role in ['manager', 'admin']",
    
    # Complex condition with custom function
    conditional_display={
        "type": "CUSTOM",
        "function": "check_approval_visibility",
        "params": ["item.status", "user.permissions"]
    }
)
```

#### **Conditional Display Functions**

```python
# Register custom condition evaluators
CONDITION_EVALUATORS = {
    "check_approval_visibility": lambda item, user: (
        item.get('status') == 'pending_approval' and 
        user.has_permission('approve_payments')
    ),
    
    "check_financial_visibility": lambda item, user: (
        user.has_permission('view_financial_data') or
        item.get('created_by') == user.user_id
    )
}
```

### **🎨 Custom Renderers**

Custom renderers provide complete control over field display:

```python
@dataclass
class CustomRenderer:
    """Custom field renderer configuration"""
    template: str                           # Template path or inline template
    context_function: Optional[str] = None  # Function to prepare context
    css_classes: str = ""                   # Additional CSS classes
    javascript: Optional[str] = None        # Custom JavaScript

# Example: Timeline Renderer
FieldDefinition(
    name="workflow_timeline",
    label="Workflow History",
    field_type=FieldType.JSON,
    virtual=True,  # Calculated field
    
    custom_renderer=CustomRenderer(
        template="renderers/timeline.html",
        context_function="prepare_timeline_context",
        css_classes="timeline-vertical",
        javascript="initTimelineInteractions"
    )
)

# Context function for timeline
def prepare_timeline_context(item, field, user):
    """Prepare timeline data for rendering"""
    timeline_data = []
    
    for event in item.get('workflow_history', []):
        timeline_data.append({
            'date': event['timestamp'],
            'title': event['action'],
            'description': event['notes'],
            'user': event['user_name'],
            'icon': get_action_icon(event['action']),
            'color': get_action_color(event['status'])
        })
    
    return {
        'timeline': timeline_data,
        'show_details': user.has_permission('view_workflow_details')
    }
```

#### **Template for Custom Renderer**

```html
<!-- templates/renderers/timeline.html -->
<div class="timeline {{ css_classes }}">
    {% for event in timeline %}
    <div class="timeline-item">
        <div class="timeline-marker {{ event.color }}">
            <i class="{{ event.icon }}"></i>
        </div>
        <div class="timeline-content">
            <h6>{{ event.title }}</h6>
            <p>{{ event.description }}</p>
            <small>{{ event.date }} by {{ event.user }}</small>
        </div>
    </div>
    {% endfor %}
</div>
```
# Custom Renderer Implementation Complete Guide

## Table of Contents
1. [Business Purpose & Use Cases](#business-purpose--use-cases)
2. [Architecture Overview](#architecture-overview)
3. [Configuration Guide](#configuration-guide)
4. [Service Method Implementation](#service-method-implementation)
5. [Template Integration](#template-integration)
6. [Real-World Examples](#real-world-examples)
7. [Troubleshooting](#troubleshooting)

---

## Business Purpose & Use Cases

### What are Custom Renderers?
Custom renderers allow fields to display complex, dynamic content that goes beyond simple value display. They enable:
- **Dynamic data fetching** from multiple sources
- **Complex visualizations** (tables, charts, timelines)
- **Aggregated information** (summaries, calculations)
- **Interactive components** (expandable sections, modals)

### Common Business Use Cases

#### 1. **Master-Detail Display**
**Purpose:** Show related line items within a parent record
```
Example: Display all purchase order line items within the PO detail view
Business Value: Users see complete information without navigation
```

#### 2. **Transaction History**
**Purpose:** Show historical transactions related to an entity
```
Example: 6-month payment history for a supplier
Business Value: Quick financial overview for decision making
```

#### 3. **Workflow Visualization**
**Purpose:** Display process status and history
```
Example: Approval workflow timeline for payments
Business Value: Clear visibility of process bottlenecks
```

#### 4. **Aggregated Summaries**
**Purpose:** Calculate and display summary information
```
Example: Outstanding balance across all supplier invoices
Business Value: Instant financial position awareness
```

#### 5. **Cross-Entity Data**
**Purpose:** Combine data from multiple entities
```
Example: Show invoices and payments for a purchase order
Business Value: Complete transaction trail in one view
```

---

## Architecture Overview

### Data Flow
```
Configuration → Data Assembler → Service Method → Template → Display
     ↓              ↓                ↓              ↓          ↓
  Define field   Detect renderer  Fetch data   Format HTML  User sees
```

### Components

1. **Configuration (Python)**
   - Defines field with CustomRenderer
   - Specifies template and context function

2. **Data Assembler (Python)**
   - Detects custom renderer fields
   - Extracts configuration for template

3. **Service Method (Python)**
   - Fetches and processes data
   - Returns structured data dict

4. **Template (Jinja2/HTML)**
   - Calls service method
   - Renders data using specified template

---

## Configuration Guide

### Step 1: Import Required Classes
```python
from app.config.core_definitions import (
    FieldDefinition, 
    FieldType, 
    CustomRenderer
)
```

### Step 2: Define Custom Renderer Field
```python
FieldDefinition(
    name="po_line_items_display",           # Unique field identifier
    label="Purchase Order Items",           # Display label
    field_type=FieldType.CUSTOM,           # Must be CUSTOM type
    
    # Display control
    show_in_list=False,                    # Not in list view
    show_in_detail=True,                   # Show in detail view
    show_in_form=False,                    # Not in forms
    readonly=True,                          # Display only
    virtual=True,                           # Not stored in DB
    
    # Layout configuration
    tab_group="line_items",                 # Tab placement
    section="items_display",                # Section within tab
    view_order=10,                          # Display order
    
    # Custom Renderer Configuration
    custom_renderer=CustomRenderer(
        template="components/business/po_items_table.html",
        context_function="get_po_line_items_display",
        css_classes="table-responsive po-items-table"
    )
)
```

### Configuration Parameters Explained

#### CustomRenderer Parameters
| Parameter | Purpose | Required | Example |
|-----------|---------|----------|---------|
| `template` | Path to HTML template | Yes | `"components/business/table.html"` |
| `context_function` | Service method name | Yes | `"get_payment_history"` |
| `css_classes` | Additional CSS classes | No | `"table-responsive striped"` |
| `javascript` | Associated JS function | No | `"initDataTable"` |

#### Field Parameters for Custom Renderers
| Parameter | Recommended Value | Why |
|-----------|------------------|-----|
| `field_type` | `FieldType.CUSTOM` | Identifies as custom renderer |
| `virtual` | `True` | Data not stored in database |
| `readonly` | `True` | Display only, not editable |
| `show_in_form` | `False` | Custom renderers are for display |

---

## Service Method Implementation

### Method Signature
```python
def get_[context_function_name](self, 
                                item_id: str = None, 
                                item: dict = None, 
                                hospital_id: str = None,
                                branch_id: str = None,
                                **kwargs) -> Dict:
    """
    Fetch and prepare data for custom renderer
    
    Args:
        item_id: Primary key of current entity
        item: Current entity data dict
        hospital_id: Current hospital context
        branch_id: Current branch context
        **kwargs: Additional parameters
        
    Returns:
        Dict with data for template
    """
```

### Basic Implementation Pattern
```python
def get_po_line_items_display(self, item_id: str = None, 
                              item: dict = None, **kwargs) -> Dict:
    """Get purchase order line items for display"""
    try:
        # 1. Get the ID to work with
        po_id = None
        if item and isinstance(item, dict):
            po_id = item.get('po_id')
        elif item_id:
            po_id = item_id
            
        if not po_id:
            return self._empty_result()
        
        # 2. Convert to proper type if needed
        if isinstance(po_id, str):
            po_id = uuid.UUID(po_id)
        
        # 3. Fetch data from database
        with get_db_session() as session:
            # Main entity
            po = session.query(PurchaseOrderHeader).filter_by(
                po_id=po_id
            ).first()
            
            if not po:
                return self._empty_result()
            
            # Related data
            lines = session.query(PurchaseOrderLine).filter_by(
                po_id=po_id
            ).order_by(PurchaseOrderLine.line_number).all()
            
            # 4. Process and format data
            items = []
            total_amount = 0
            total_gst = 0
            
            for line in lines:
                item_dict = {
                    'line_number': line.line_number,
                    'item_name': line.medicine_name,
                    'hsn_code': line.hsn_code or '-',
                    'quantity': float(line.units or 0),
                    'unit_price': float(line.pack_purchase_price or 0),
                    'gst_rate': float(line.gst_rate or 0),
                    'gst_amount': float(line.total_gst or 0),
                    'total_amount': float(line.line_total or 0)
                }
                items.append(item_dict)
                total_amount += item_dict['total_amount']
                total_gst += item_dict['gst_amount']
            
            # 5. Return structured data
            return {
                'items': items,                    # Main data
                'has_items': bool(items),          # Control flag
                'currency_symbol': '₹',            # Display config
                'summary': {                       # Aggregated data
                    'total_items': len(items),
                    'total_amount': total_amount,
                    'total_gst': total_gst,
                    'subtotal': total_amount - total_gst
                },
                'metadata': {                      # Additional info
                    'po_number': po.po_number,
                    'po_date': po.po_date,
                    'status': po.status
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting PO line items: {str(e)}")
        return self._error_result(str(e))
    
def _empty_result(self) -> Dict:
    """Standard empty result structure"""
    return {
        'items': [],
        'has_items': False,
        'summary': {},
        'metadata': {}
    }

def _error_result(self, error: str) -> Dict:
    """Standard error result structure"""
    return {
        'items': [],
        'has_error': True,
        'error_message': error,
        'summary': {},
        'metadata': {}
    }
```

### Advanced Patterns

#### 1. **Aggregation Pattern**
```python
def get_payment_summary(self, item_id: str = None, **kwargs) -> Dict:
    """Calculate payment summary across multiple invoices"""
    
    with get_db_session() as session:
        # Use SQL aggregation for performance
        result = session.query(
            func.count(Payment.payment_id).label('count'),
            func.sum(Payment.amount).label('total'),
            func.avg(Payment.amount).label('average'),
            func.max(Payment.payment_date).label('latest')
        ).filter(
            Payment.supplier_id == item_id
        ).first()
        
        return {
            'summary': {
                'payment_count': result.count or 0,
                'total_paid': float(result.total or 0),
                'average_payment': float(result.average or 0),
                'last_payment_date': result.latest
            },
            'has_payments': result.count > 0
        }
```

#### 2. **Time-Based Pattern**
```python
def get_payment_history_6months(self, item_id: str = None, **kwargs) -> Dict:
    """Get 6 months payment history"""
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    with get_db_session() as session:
        payments = session.query(Payment).filter(
            Payment.supplier_id == item_id,
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).order_by(desc(Payment.payment_date)).all()
        
        # Group by month for visualization
        monthly_data = {}
        for payment in payments:
            month_key = payment.payment_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': payment.payment_date.strftime('%B %Y'),
                    'payments': [],
                    'total': 0
                }
            
            monthly_data[month_key]['payments'].append({
                'date': payment.payment_date,
                'amount': float(payment.amount),
                'reference': payment.payment_number
            })
            monthly_data[month_key]['total'] += float(payment.amount)
        
        return {
            'monthly_data': list(monthly_data.values()),
            'has_history': bool(monthly_data),
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }
```

#### 3. **Cross-Entity Pattern**
```python
def get_po_financial_summary(self, item_id: str = None, **kwargs) -> Dict:
    """Combine PO, Invoice, and Payment data"""
    
    with get_db_session() as session:
        # Get PO
        po = session.query(PurchaseOrder).get(item_id)
        
        # Get related invoices
        invoices = session.query(Invoice).filter_by(
            po_id=item_id
        ).all()
        
        # Get payments through invoices
        invoice_ids = [inv.invoice_id for inv in invoices]
        payments = session.query(Payment).filter(
            Payment.invoice_id.in_(invoice_ids)
        ).all() if invoice_ids else []
        
        # Calculate summaries
        po_amount = float(po.total_amount or 0)
        invoiced_amount = sum(float(inv.total_amount or 0) for inv in invoices)
        paid_amount = sum(float(pay.amount or 0) for pay in payments)
        
        return {
            'po_summary': {
                'number': po.po_number,
                'amount': po_amount,
                'status': po.status
            },
            'invoice_summary': {
                'count': len(invoices),
                'total': invoiced_amount,
                'pending': invoiced_amount - paid_amount
            },
            'payment_summary': {
                'count': len(payments),
                'total': paid_amount,
                'outstanding': po_amount - paid_amount
            },
            'has_financials': bool(invoices or payments)
        }
```

---

## Template Integration

### Basic Template Structure
```html
<!-- components/business/po_items_table.html -->
{% if data.has_items %}
<div class="po-items-container {{ data.css_classes }}">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>#</th>
                <th>Item</th>
                <th>HSN</th>
                <th>Qty</th>
                <th>Rate</th>
                <th>GST</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {% for item in data.items %}
            <tr>
                <td>{{ item.line_number }}</td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.hsn_code }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ data.currency_symbol }}{{ item.unit_price|format_number }}</td>
                <td>{{ data.currency_symbol }}{{ item.gst_amount|format_number }}</td>
                <td>{{ data.currency_symbol }}{{ item.total_amount|format_number }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr class="font-weight-bold">
                <td colspan="5">Total</td>
                <td>{{ data.currency_symbol }}{{ data.summary.total_gst|format_number }}</td>
                <td>{{ data.currency_symbol }}{{ data.summary.total_amount|format_number }}</td>
            </tr>
        </tfoot>
    </table>
</div>
{% else %}
<div class="alert alert-info">
    <i class="fas fa-info-circle"></i> No items found
</div>
{% endif %}
```

### Advanced Template Patterns

#### 1. **Conditional Display**
```html
{% if data.has_error %}
    <div class="alert alert-danger">
        {{ data.error_message }}
    </div>
{% elif data.has_items %}
    <!-- Main content -->
{% else %}
    <div class="text-muted">No data available</div>
{% endif %}
```

#### 2. **Nested Data Display**
```html
{% for month in data.monthly_data %}
<div class="month-section">
    <h5>{{ month.month }}</h5>
    <table class="table">
        {% for payment in month.payments %}
        <tr>
            <td>{{ payment.date|format_date }}</td>
            <td>{{ payment.reference }}</td>
            <td class="text-right">{{ payment.amount|format_currency }}</td>
        </tr>
        {% endfor %}
        <tr class="total-row">
            <td colspan="2">Monthly Total</td>
            <td class="text-right font-weight-bold">
                {{ month.total|format_currency }}
            </td>
        </tr>
    </table>
</div>
{% endfor %}
```

#### 3. **Interactive Elements**
```html
<div class="expandable-section">
    {% for item in data.items %}
    <div class="item-row" onclick="toggleDetails('{{ item.id }}')">
        <span>{{ item.name }}</span>
        <span class="badge">{{ item.count }}</span>
    </div>
    <div id="details-{{ item.id }}" class="item-details" style="display:none;">
        <!-- Detailed information -->
    </div>
    {% endfor %}
</div>

<script>
function toggleDetails(id) {
    var details = document.getElementById('details-' + id);
    details.style.display = details.style.display === 'none' ? 'block' : 'none';
}
</script>
```

---

## Real-World Examples

### Example 1: Purchase Order Line Items

**Business Need:** Display all items in a purchase order with totals

**Configuration:**
```python
FieldDefinition(
    name="po_line_items_display",
    label="Order Items",
    field_type=FieldType.CUSTOM,
    virtual=True,
    show_in_detail=True,
    tab_group="items",
    custom_renderer=CustomRenderer(
        template="components/business/po_items_table.html",
        context_function="get_po_line_items_display",
        css_classes="table-responsive"
    )
)
```

**Service Method:**
```python
def get_po_line_items_display(self, item_id=None, item=None, **kwargs):
    po_id = item.get('po_id') if item else item_id
    
    with get_db_session() as session:
        lines = session.query(POLine).filter_by(po_id=po_id).all()
        
        items = []
        for line in lines:
            items.append({
                'product': line.product_name,
                'quantity': line.quantity,
                'price': line.unit_price,
                'total': line.quantity * line.unit_price
            })
        
        return {
            'items': items,
            'has_items': bool(items),
            'total': sum(i['total'] for i in items)
        }
```

### Example 2: Payment History Timeline

**Business Need:** Show payment history as a timeline

**Configuration:**
```python
FieldDefinition(
    name="payment_timeline",
    label="Payment Timeline",
    field_type=FieldType.CUSTOM,
    virtual=True,
    custom_renderer=CustomRenderer(
        template="components/timeline.html",
        context_function="get_payment_timeline",
        css_classes="timeline-vertical"
    )
)
```

**Service Method:**
```python
def get_payment_timeline(self, item_id=None, **kwargs):
    with get_db_session() as session:
        payments = session.query(Payment).filter_by(
            supplier_id=item_id
        ).order_by(desc(Payment.date)).limit(10).all()
        
        timeline_events = []
        for payment in payments:
            timeline_events.append({
                'date': payment.date,
                'title': f'Payment #{payment.number}',
                'amount': payment.amount,
                'status': payment.status,
                'icon': 'fa-check' if payment.status == 'completed' else 'fa-clock',
                'color': 'success' if payment.status == 'completed' else 'warning'
            })
        
        return {
            'events': timeline_events,
            'has_events': bool(timeline_events)
        }
```

### Example 3: Summary Cards

**Business Need:** Display key metrics as cards

**Configuration:**
```python
FieldDefinition(
    name="supplier_metrics",
    label="Key Metrics",
    field_type=FieldType.CUSTOM,
    virtual=True,
    custom_renderer=CustomRenderer(
        template="components/metric_cards.html",
        context_function="get_supplier_metrics"
    )
)
```

**Service Method:**
```python
def get_supplier_metrics(self, item_id=None, **kwargs):
    with get_db_session() as session:
        # Various calculations
        metrics = {
            'total_orders': session.query(Order).filter_by(supplier_id=item_id).count(),
            'pending_amount': session.query(func.sum(Invoice.amount)).filter_by(
                supplier_id=item_id, status='pending'
            ).scalar() or 0,
            'last_order_date': session.query(func.max(Order.date)).filter_by(
                supplier_id=item_id
            ).scalar()
        }
        
        return {
            'metrics': [
                {
                    'label': 'Total Orders',
                    'value': metrics['total_orders'],
                    'icon': 'fa-shopping-cart',
                    'color': 'primary'
                },
                {
                    'label': 'Pending Amount',
                    'value': f"₹{metrics['pending_amount']:,.2f}",
                    'icon': 'fa-rupee-sign',
                    'color': 'warning'
                },
                {
                    'label': 'Last Order',
                    'value': metrics['last_order_date'].strftime('%d %b %Y') if metrics['last_order_date'] else 'Never',
                    'icon': 'fa-calendar',
                    'color': 'info'
                }
            ]
        }
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. **Context Function Not Found**
**Error:** `Unknown context function: get_po_items`

**Causes:**
- Method doesn't exist in service
- Method name mismatch
- Service not properly initialized

**Solution:**
```python
# Verify method exists
class PurchaseOrderService(UniversalEntityService):
    def get_po_items(self, item_id=None, item=None, **kwargs):
        # Implementation
        pass
```

#### 2. **Template Not Found**
**Error:** `Template 'components/table.html' not found`

**Causes:**
- Wrong path in configuration
- Template file doesn't exist

**Solution:**
```python
# Check template path
custom_renderer=CustomRenderer(
    template="components/business/table.html"  # Full path from templates/
)
```

#### 3. **No Data Displayed**
**Symptom:** Custom renderer area is blank

**Debug Steps:**
```python
# 1. Add logging to service method
def get_data(self, item_id=None, **kwargs):
    logger.info(f"get_data called with item_id={item_id}")
    result = {...}
    logger.info(f"Returning: {result}")
    return result

# 2. Check template receives data
<!-- In template -->
<div>Debug: {{ data|tojson }}</div>

# 3. Verify configuration
print(field.custom_renderer.context_function)  # Should match method name
```

#### 4. **Performance Issues**
**Symptom:** Slow page load with custom renderers

**Solutions:**
```python
# 1. Use eager loading
query = query.options(joinedload(Model.relationship))

# 2. Limit data
items = query.limit(100).all()

# 3. Cache results
@cache_service_method('entity', 'method')
def get_data(self, ...):
    pass

# 4. Use pagination
def get_data(self, page=1, per_page=20, **kwargs):
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
```

### Debug Checklist

- [ ] Configuration has correct `context_function` name
- [ ] Service method exists with exact name match
- [ ] Service method returns dict (not None)
- [ ] Template file exists at specified path
- [ ] Template handles empty data case
- [ ] Field has `virtual=True` for calculated data
- [ ] Field has `show_in_detail=True` to appear
- [ ] No Python errors in service method
- [ ] No template syntax errors

### Testing Custom Renderers

```python
# Test service method directly
from app.services.purchase_order_service import PurchaseOrderService

service = PurchaseOrderService()
result = service.get_po_line_items_display(
    item_id='test-id',
    item={'po_id': 'test-id'}
)

print("Result keys:", result.keys())
print("Has items:", result.get('has_items'))
print("Item count:", len(result.get('items', [])))
```

---

## Best Practices

### Do's
- ✅ Return consistent data structure
- ✅ Handle empty/null cases
- ✅ Include control flags (has_data, has_error)
- ✅ Use database sessions efficiently
- ✅ Format data in service, not template
- ✅ Log errors with context
- ✅ Cache expensive operations

### Don'ts
- ❌ Don't return None (return empty dict)
- ❌ Don't do complex logic in templates
- ❌ Don't fetch unnecessary data
- ❌ Don't hardcode entity IDs
- ❌ Don't forget error handling
- ❌ Don't mix presentation logic in service

### Performance Guidelines
1. **Limit data fetched** - Use pagination/limits
2. **Use joins wisely** - Avoid N+1 queries
3. **Cache when possible** - Especially for summaries
4. **Aggregate in database** - Use SQL functions
5. **Lazy load relationships** - Unless needed immediately

---

## Summary

Custom renderers provide a powerful way to display complex, dynamic data in your application. By following this guide:

1. **Configure** fields with CustomRenderer
2. **Implement** service methods to fetch data
3. **Create** templates to display data
4. **Test** thoroughly with various data scenarios

The system is designed to be:
- **Flexible** - Any data structure supported
- **Reusable** - Templates can be shared
- **Maintainable** - Clear separation of concerns
- **Performant** - With proper optimization

Remember: Custom renderers are for **display only**. For data entry, use standard form fields.



### **🔧 Dynamic Field Behavior**

```python
FieldDefinition(
    name="payment_method",
    label="Payment Method",
    field_type=FieldType.SELECT,
    
    # Dynamic options based on context
    dynamic_options_function=lambda user, item: [
        {"value": "cash", "label": "Cash"},
        {"value": "card", "label": "Card"},
        {"value": "upi", "label": "UPI"},
        # Add wire transfer only for large amounts
        {"value": "wire", "label": "Wire Transfer"} 
        if item.get('amount', 0) > 10000 else None
    ],
    
    # JavaScript behavior
    javascript_behavior="""
    $(document).on('change', '[name="payment_method"]', function() {
        var method = $(this).val();
        
        // Show/hide related fields
        if (method === 'card') {
            $('.card-details').slideDown();
        } else {
            $('.card-details').slideUp();
        }
        
        // Update commission calculation
        updateCommissionRate(method);
    });
    """,
    
    # Custom events
    custom_events=[
        {
            "event": "change",
            "handler": "handlePaymentMethodChange",
            "params": ["value", "item"]
        }
    ]
)
```

---

## **19. Advanced Action Configuration**

### **🎯 Conditional Actions**

Actions can be shown/hidden based on complex conditions:

```python
ActionDefinition(
    id="approve",
    label="Approve",
    icon="fas fa-check",
    button_type=ButtonType.SUCCESS,
    
    # Simple condition
    conditional_display="item.status == 'pending'",
    
    # Multiple conditions
    conditions={
        "item_conditions": [
            "item.status == 'pending'",
            "item.amount < user.approval_limit"
        ],
        "user_conditions": [
            "user.has_permission('approve_payments')",
            "user.department == item.department"
        ],
        "operator": "AND"  # All conditions must be true
    },
    
    # Custom condition function
    condition_function="can_approve_payment",
    
    # Dynamic label based on condition
    dynamic_label=lambda item: (
        "Approve Payment" if item['amount'] < 10000
        else "Approve Large Payment"
    )
)
```

#### **Condition Evaluators**

```python
# Register action condition evaluators
ACTION_CONDITIONS = {
    "can_approve_payment": lambda item, user: (
        item['status'] == 'pending' and
        user.has_permission('approve_payments') and
        item['amount'] <= user.approval_limit and
        not item.get('is_locked', False)
    ),
    
    "can_edit_entity": lambda item, user: (
        item['status'] != 'approved' or
        user.has_permission('edit_approved') or
        item['created_by'] == user.user_id
    ),
    
    "can_delete_entity": lambda item, user: (
        item['status'] == 'draft' or
        user.role == 'admin'
    )
}
```

### **🔄 Dynamic Actions**

```python
ActionDefinition(
    id="workflow_action",
    label="",  # Dynamic label
    icon="",   # Dynamic icon
    
    # Dynamic properties based on item state
    dynamic_config=lambda item, user: {
        "label": get_next_workflow_action(item['status']),
        "icon": get_workflow_icon(item['status']),
        "button_type": get_workflow_button_type(item['status']),
        "confirmation_message": get_workflow_confirmation(item['status'])
    },
    
    # Custom handler
    custom_handler="handle_workflow_transition",
    
    # JavaScript handler for client-side logic
    javascript_handler="""
    function handleWorkflowAction(itemId, currentStatus) {
        // Show loading
        showLoadingOverlay();
        
        // Get next status
        var nextStatus = getNextWorkflowStatus(currentStatus);
        
        // Validate transition
        if (!validateTransition(currentStatus, nextStatus)) {
            showError('Invalid workflow transition');
            return false;
        }
        
        // Submit transition
        submitWorkflowTransition(itemId, nextStatus);
    }
    """
)
```

### **🎨 Action Groups**

```python
# Group related actions together
ACTION_GROUPS = {
    "workflow": {
        "label": "Workflow",
        "icon": "fas fa-tasks",
        "actions": ["submit", "approve", "reject", "cancel"],
        "show_condition": "item.status != 'completed'"
    },
    
    "financial": {
        "label": "Financial",
        "icon": "fas fa-dollar-sign",
        "actions": ["generate_invoice", "apply_discount", "refund"],
        "show_condition": "user.has_permission('financial_operations')"
    },
    
    "document": {
        "label": "Documents",
        "icon": "fas fa-file-alt",
        "actions": ["print", "download_pdf", "email"],
        "show_condition": "item.document_ready == true"
    }
}
```

### **🔧 Custom Action Handlers**

```python
# Register custom action handlers
ACTION_HANDLERS = {
    "handle_workflow_transition": lambda item, user, params: {
        # Validate transition
        if not validate_workflow_transition(item['status'], params['next_status']):
            return {"success": False, "error": "Invalid transition"}
        
        # Update status
        item['status'] = params['next_status']
        item['workflow_history'].append({
            'timestamp': datetime.now(),
            'action': f"Status changed to {params['next_status']}",
            'user': user.user_id,
            'notes': params.get('notes', '')
        })
        
        # Trigger notifications
        notify_workflow_change(item, user)
        
        return {"success": True, "message": "Workflow updated"}
    },
    
    "bulk_approve": lambda items, user, params: {
        approved = []
        failed = []
        
        for item in items:
            if can_approve(item, user):
                item['status'] = 'approved'
                item['approved_by'] = user.user_id
                item['approved_at'] = datetime.now()
                approved.append(item['id'])
            else:
                failed.append(item['id'])
        
        return {
            "success": True,
            "approved": approved,
            "failed": failed,
            "message": f"Approved {len(approved)} items"
        }
    }
}
```

---

## **20. Advanced Validation & Business Rules**

### **🔒 Field-Level Validation**

```python
FieldDefinition(
    name="email",
    label="Email",
    field_type=FieldType.EMAIL,
    
    # Built-in validators
    required=True,
    unique=True,
    
    # Custom validator function
    validator="validate_company_email",
    
    # Regex pattern validation
    validation_pattern=r"^[a-zA-Z0-9._%+-]+@company\.com$",
    validation_message="Must be a company email address",
    
    # Async validation (server-side)
    async_validator={
        "endpoint": "/api/validate/email",
        "method": "POST",
        "debounce": 500  # milliseconds
    },
    
    # Cross-field validation
    cross_field_validation={
        "fields": ["email", "alternate_email"],
        "validator": "ensure_different_emails",
        "message": "Primary and alternate emails must be different"
    }
)
```

### **📊 Business Rules Engine**

```python
@dataclass
class BusinessRule:
    """Business rule definition"""
    id: str
    name: str
    description: str
    trigger: str  # create, update, delete, status_change
    conditions: List[str]
    actions: List[Dict]
    priority: int = 0
    enabled: bool = True

# Example Business Rules
BUSINESS_RULES = [
    BusinessRule(
        id="auto_approve_small_payments",
        name="Auto-approve small payments",
        trigger="create",
        conditions=[
            "entity_type == 'payments'",
            "item.amount < 1000",
            "item.vendor.trusted == True"
        ],
        actions=[
            {"type": "set_field", "field": "status", "value": "approved"},
            {"type": "set_field", "field": "auto_approved", "value": True},
            {"type": "notify", "template": "auto_approval", "recipients": ["creator"]}
        ]
    ),
    
    BusinessRule(
        id="enforce_credit_limit",
        name="Enforce customer credit limit",
        trigger="create",
        conditions=[
            "entity_type == 'sales_order'",
            "customer.outstanding + item.amount > customer.credit_limit"
        ],
        actions=[
            {"type": "block", "message": "Credit limit exceeded"},
            {"type": "require_approval", "approver_role": "finance_manager"},
            {"type": "notify", "template": "credit_limit_exceeded", "recipients": ["finance_team"]}
        ]
    )
]
```

### **🔄 Workflow State Machine**

```python
@dataclass
class WorkflowState:
    """Workflow state definition"""
    name: str
    label: str
    color: str
    icon: str
    allowed_transitions: List[str]
    required_fields: List[str]
    permissions: Dict[str, List[str]]  # role -> allowed actions

WORKFLOW_STATES = {
    "draft": WorkflowState(
        name="draft",
        label="Draft",
        color="secondary",
        icon="fas fa-pencil-alt",
        allowed_transitions=["submitted", "cancelled"],
        required_fields=[],
        permissions={
            "creator": ["edit", "delete", "submit"],
            "admin": ["edit", "delete", "submit"]
        }
    ),
    
    "submitted": WorkflowState(
        name="submitted",
        label="Submitted",
        color="info",
        icon="fas fa-paper-plane",
        allowed_transitions=["approved", "rejected", "draft"],
        required_fields=["amount", "description", "category"],
        permissions={
            "creator": ["view", "withdraw"],
            "approver": ["approve", "reject", "return"],
            "admin": ["approve", "reject", "edit"]
        }
    ),
    
    "approved": WorkflowState(
        name="approved",
        label="Approved",
        color="success",
        icon="fas fa-check-circle",
        allowed_transitions=["completed", "cancelled"],
        required_fields=["approval_notes", "approved_by"],
        permissions={
            "creator": ["view"],
            "approver": ["view", "complete"],
            "admin": ["edit", "complete", "cancel"]
        }
    )
}
```

---

## **21. Advanced Search & Filter Configuration**

### **🔍 Filter Categories**

```python
from app.config.filter_categories import FilterCategory

# Configure filter categories
ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    supported_categories=[
        FilterCategory.STATUS,
        FilterCategory.DATE_RANGE,
        FilterCategory.AMOUNT_RANGE,
        FilterCategory.SEARCH,
        FilterCategory.RELATIONSHIP
    ],
    
    category_configs={
        FilterCategory.STATUS: {
            "field": "status",
            "label": "Status",
            "type": "select",
            "options": [
                {"value": "active", "label": "Active", "color": "success"},
                {"value": "inactive", "label": "Inactive", "color": "danger"}
            ],
            "default": "active"
        },
        
        FilterCategory.DATE_RANGE: {
            "field": "created_date",
            "label": "Date Range",
            "type": "daterange",
            "presets": [
                {"value": "today", "label": "Today"},
                {"value": "week", "label": "This Week"},
                {"value": "month", "label": "This Month"}
            ]
        },
        
        FilterCategory.AMOUNT_RANGE: {
            "field": "amount",
            "label": "Amount",
            "type": "range",
            "min": 0,
            "max": 1000000,
            "step": 100
        },
        
        FilterCategory.RELATIONSHIP: {
            "field": "supplier_id",
            "label": "Supplier",
            "type": "select",
            "source": "suppliers",  # Load from entity
            "display_field": "name",
            "value_field": "supplier_id"
        }
    },
    
    # Default filters
    default_filters={
        "status": "active",
        "branch_id": "current"
    }
)
```

### **🔎 Search Configuration**

```python
ENTITY_SEARCH_CONFIG = EntitySearchConfiguration(
    # Fields to search
    searchable_fields=[
        "name", "description", "code", "reference"
    ],
    
    # Search behavior
    search_type="fuzzy",  # exact, fuzzy, fulltext
    min_search_length=2,
    
    # Advanced search
    enable_advanced_search=True,
    advanced_search_fields=[
        {
            "field": "name",
            "label": "Name",
            "type": "text",
            "operator": "contains"
        },
        {
            "field": "amount",
            "label": "Amount",
            "type": "number",
            "operator": "between"
        }
    ]
)
```

---

### **🔍 Dynamic Filter Configuration**

```python
from app.config.filter_categories import FilterCategory

class DynamicFilterConfiguration:
    """Advanced filter configuration with dynamic behavior"""
    
    def __init__(self):
        self.filters = {}
        self.dependencies = {}
        self.dynamic_options = {}
    
    def add_filter(self, name: str, config: Dict):
        """Add a dynamic filter"""
        self.filters[name] = config
    
    def add_dependency(self, filter_name: str, depends_on: str, handler: Callable):
        """Add filter dependency"""
        if filter_name not in self.dependencies:
            self.dependencies[filter_name] = []
        self.dependencies[filter_name].append({
            'depends_on': depends_on,
            'handler': handler
        })

# Example: Cascading Filters
ENTITY_DYNAMIC_FILTERS = DynamicFilterConfiguration()

# Country -> State -> City cascading filter
ENTITY_DYNAMIC_FILTERS.add_filter('country', {
    'type': 'select',
    'label': 'Country',
    'options_source': 'api',
    'api_endpoint': '/api/countries',
    'cache': True,
    'cache_ttl': 3600
})

ENTITY_DYNAMIC_FILTERS.add_filter('state', {
    'type': 'select',
    'label': 'State',
    'options_source': 'dynamic',
    'depends_on': 'country',
    'disabled_when_empty': 'country'
})

ENTITY_DYNAMIC_FILTERS.add_dependency(
    'state',
    'country',
    lambda country_id: fetch_states_for_country(country_id)
)

ENTITY_DYNAMIC_FILTERS.add_filter('city', {
    'type': 'select',
    'label': 'City',
    'options_source': 'dynamic',
    'depends_on': 'state',
    'disabled_when_empty': 'state'
})
```

### **🔎 Advanced Search Configuration**

```python
@dataclass
class AdvancedSearchConfiguration:
    """Advanced search with multiple strategies"""
    
    # Search strategies
    search_strategies: Dict[str, SearchStrategy] = field(default_factory=dict)
    
    # Weighted search fields
    weighted_fields: Dict[str, float] = field(default_factory=dict)
    
    # Search suggestions
    enable_suggestions: bool = True
    suggestion_source: str = "elastic"  # elastic, database, cache
    
    # Search history
    track_search_history: bool = True
    personalized_results: bool = True
    
    # Fuzzy search
    fuzzy_search_enabled: bool = True
    fuzzy_threshold: float = 0.7

# Example Configuration
ADVANCED_SEARCH_CONFIG = AdvancedSearchConfiguration(
    weighted_fields={
        "name": 2.0,        # Higher weight for name matches
        "description": 1.0,
        "tags": 1.5,
        "code": 2.5         # Highest weight for exact code matches
    },
    
    search_strategies={
        "full_text": FullTextSearchStrategy(
            fields=["name", "description", "notes"],
            minimum_score=0.5
        ),
        "semantic": SemanticSearchStrategy(
            model="sentence-transformers/all-MiniLM-L6-v2",
            similarity_threshold=0.7
        ),
        "phonetic": PhoneticSearchStrategy(
            algorithm="metaphone",
            fields=["name", "contact_name"]
        )
    }
)
```

---

## **22. Performance Optimization Techniques**

### **⚡ Query Optimization**

```python
class OptimizedEntityService(UniversalEntityService):
    """Service with advanced performance optimizations"""
    
    def __init__(self):
        super().__init__()
        
        # Query optimization settings
        self.enable_query_cache = True
        self.enable_eager_loading = True
        self.enable_batch_loading = True
        self.max_batch_size = 100
    
    def get_optimized_query(self, session, filters):
        """Build optimized query with eager loading"""
        
        # Start with base query
        query = session.query(self.model_class)
        
        # Eager load relationships based on view requirements
        if self.should_eager_load('supplier'):
            query = query.options(
                joinedload(self.model_class.supplier)
                .selectinload(Supplier.contact_persons)
            )
        
        # Use subquery for counts
        if self.needs_count_data():
            subquery = session.query(
                PaymentItem.payment_id,
                func.count(PaymentItem.id).label('item_count'),
                func.sum(PaymentItem.amount).label('total_amount')
            ).group_by(PaymentItem.payment_id).subquery()
            
            query = query.outerjoin(
                subquery,
                self.model_class.payment_id == subquery.c.payment_id
            )
        
        # Apply query hints
        query = query.execution_options(
            synchronize_session='fetch',
            populate_existing=True
        )
        
        return query
    
    @cache_service_method(ttl=60)  # Short TTL for real-time data
    def get_dashboard_metrics(self, hospital_id: str) -> dict:
        """Get optimized dashboard metrics with caching"""
        
        with get_db_session() as session:
            # Use single query with multiple aggregations
            result = session.query(
                func.count(self.model_class.id).label('total_count'),
                func.sum(case(
                    (self.model_class.status == 'active', 1),
                    else_=0
                )).label('active_count'),
                func.sum(self.model_class.amount).label('total_amount'),
                func.avg(self.model_class.amount).label('avg_amount')
            ).filter(
                self.model_class.hospital_id == hospital_id
            ).first()
            
            return {
                'total': result.total_count or 0,
                'active': result.active_count or 0,
                'total_amount': float(result.total_amount or 0),
                'average_amount': float(result.avg_amount or 0)
            }
```

### **🚀 Batch Processing**

```python
class BatchProcessor:
    """Efficient batch processing for large operations"""
    
    def __init__(self, batch_size: int = 100):
        self.batch_size = batch_size
        self.error_handler = None
        self.progress_callback = None
    
    def process_in_batches(self, items: List, processor: Callable) -> Dict:
        """Process items in batches with error handling"""
        
        total = len(items)
        processed = 0
        errors = []
        results = []
        
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            
            try:
                # Process batch
                batch_results = processor(batch)
                results.extend(batch_results)
                
                # Update progress
                processed += len(batch)
                if self.progress_callback:
                    self.progress_callback(processed, total)
                
            except Exception as e:
                # Handle batch error
                if self.error_handler:
                    self.error_handler(batch, e)
                errors.append({
                    'batch_index': i,
                    'error': str(e),
                    'items': batch
                })
        
        return {
            'success': len(errors) == 0,
            'processed': processed,
            'total': total,
            'results': results,
            'errors': errors
        }
```

---

## **23. Security & Permission Extensions**

### **🔐 Row-Level Security**

```python
@dataclass
class RowLevelSecurity:
    """Row-level security configuration"""
    
    enabled: bool = True
    
    # Security policies
    policies: List[SecurityPolicy] = field(default_factory=list)
    
    # Data classification
    classification_field: str = "data_classification"
    classifications: Dict[str, SecurityLevel] = field(default_factory=dict)

@dataclass
class SecurityPolicy:
    """Individual security policy"""
    
    name: str
    description: str
    
    # Condition for applying policy
    condition: str  # Expression
    
    # What the policy allows/denies
    effect: str  # "allow" or "deny"
    actions: List[str]  # ["read", "write", "delete"]
    
    # Additional filters to apply
    filters: Dict[str, Any] = field(default_factory=dict)

# Example Row-Level Security
ROW_LEVEL_SECURITY = RowLevelSecurity(
    policies=[
        SecurityPolicy(
            name="own_records_only",
            description="Users can only see their own records",
            condition="user.role == 'user'",
            effect="allow",
            actions=["read", "write"],
            filters={"created_by": "user.user_id"}
        ),
        
        SecurityPolicy(
            name="department_isolation",
            description="Users can only see records from their department",
            condition="user.role in ['manager', 'employee']",
            effect="allow",
            actions=["read"],
            filters={"department_id": "user.department_id"}
        ),
        
        SecurityPolicy(
            name="sensitive_data_protection",
            description="Protect sensitive data",
            condition="item.data_classification == 'confidential'",
            effect="deny",
            actions=["read"],
            filters={"user.clearance_level": {"$lt": 3}}
        )
    ]
)
```

### **🔑 Field-Level Encryption**

```python
@dataclass
class FieldEncryption:
    """Field-level encryption configuration"""
    
    enabled: bool = True
    encryption_type: str = "AES256"
    
    # Fields to encrypt
    encrypted_fields: List[str] = field(default_factory=list)
    
    # Encryption key management
    key_source: str = "vault"  # vault, env, kms
    key_rotation_days: int = 90
    
    # Searchable encryption
    enable_searchable_encryption: bool = False
    blind_index_fields: List[str] = field(default_factory=list)

# Example Configuration
FIELD_ENCRYPTION = FieldEncryption(
    encrypted_fields=[
        "social_security_number",
        "credit_card_number",
        "bank_account",
        "medical_record_number"
    ],
    
    blind_index_fields=[
        "social_security_number"  # Can search while encrypted
    ]
)
```

---

## **24. Integration & Extensibility**

### **🔌 Plugin System**

```python
@dataclass
class PluginDefinition:
    """Plugin configuration for extending entity functionality"""
    
    id: str
    name: str
    version: str
    
    # Plugin type
    plugin_type: str  # "field", "action", "validator", "renderer"
    
    # Plugin implementation
    module_path: str
    class_name: str
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    requires: List[str] = field(default_factory=list)
    
    # Hooks
    hooks: Dict[str, str] = field(default_factory=dict)

# Example Plugin Registration
ENTITY_PLUGINS = [
    PluginDefinition(
        id="audit_trail",
        name="Audit Trail Plugin",
        version="1.0.0",
        plugin_type="lifecycle",
        module_path="app.plugins.audit_trail",
        class_name="AuditTrailPlugin",
        config={
            "track_fields": ["status", "amount", "approval_status"],
            "track_relationships": True,
            "store_old_values": True
        },
        hooks={
            "before_create": "log_creation",
            "after_update": "log_changes",
            "after_delete": "log_deletion"
        }
    ),
    
    PluginDefinition(
        id="workflow_engine",
        name="Workflow Engine",
        version="2.0.0",
        plugin_type="lifecycle",
        module_path="app.plugins.workflow",
        class_name="WorkflowEngine",
        config={
            "workflow_definition": "payment_approval_workflow",
            "auto_transition": True,
            "send_notifications": True
        }
    )
]
```

### **🎯 Event System**

```python
@dataclass
class EventDefinition:
    """Event configuration for entity lifecycle"""
    
    name: str
    trigger: str  # "before_create", "after_update", etc.
    
    # Event handlers
    handlers: List[EventHandler] = field(default_factory=list)
    
    # Async processing
    async_enabled: bool = False
    queue_name: str = "default"

@dataclass
class EventHandler:
    """Individual event handler"""
    
    id: str
    handler_type: str  # "function", "webhook", "queue"
    
    # Handler configuration
    function_name: Optional[str] = None
    webhook_url: Optional[str] = None
    queue_config: Optional[Dict] = None
    
    # Conditions
    condition: Optional[str] = None
    
    # Error handling
    retry_count: int = 3
    retry_delay: int = 60  # seconds

# Example Event Configuration
ENTITY_EVENTS = [
    EventDefinition(
        name="payment_created",
        trigger="after_create",
        handlers=[
            EventHandler(
                id="send_notification",
                handler_type="function",
                function_name="send_payment_notification"
            ),
            EventHandler(
                id="update_balance",
                handler_type="function",
                function_name="update_supplier_balance"
            ),
            EventHandler(
                id="webhook_accounting",
                handler_type="webhook",
                webhook_url="https://accounting.api/payments",
                condition="item.amount > 10000"
            )
        ],
        async_enabled=True
    )
]
```

---

## **25. Best Practices & Advanced Patterns**

### **🔒 Permission Configuration**

```python
# In EntityConfiguration
permissions={
    # Operation permissions
    "view": "your_entity.view",
    "create": "your_entity.create",
    "edit": "your_entity.edit",
    "delete": "your_entity.delete",
    "export": "your_entity.export",
    "print": "your_entity.print",
    
    # Field-level permissions
    "view_financial": "your_entity.view_financial",
    "edit_financial": "your_entity.edit_financial",
    
    # Custom permissions
    "approve": "your_entity.approve",
    "verify": "your_entity.verify"
}
```

### **🛡️ Field-Level Security**

```python
FieldDefinition(
    name="salary",
    label="Salary",
    field_type=FieldType.CURRENCY,
    
    # Permission-based visibility
    view_permission="hr.view_salary",
    edit_permission="hr.edit_salary",
    
    # Conditional visibility
    show_condition="user.role == 'hr_manager'",
    
    # Data masking
    mask_format="****{last4}",  # Show only last 4 digits
    unmask_permission="hr.unmask_salary"
)
```

---

### **✅ Advanced Configuration Best Practices**

1. **User Preference Strategy**
   ```python
   # Good: Centralized preference management
   class UserPreferenceManager:
       def get_preference(self, user, key, default=None):
           if not user.ui_preferences:
               return default
           return user.ui_preferences.get(key, default)
       
       def set_preference(self, user, key, value):
           if not user.ui_preferences:
               user.ui_preferences = {}
           user.ui_preferences[key] = value
           flag_modified(user, "ui_preferences")
   ```

2. **Conditional Display Pattern**
   ```python
   # Good: Reusable condition evaluators
   CONDITION_LIBRARY = {
       "is_draft": "item.status == 'draft'",
       "is_editable": "item.status in ['draft', 'pending']",
       "is_owner": "item.created_by == user.user_id",
       "has_permission": lambda perm: f"user.has_permission('{perm}')",
       "above_threshold": lambda amt: f"item.amount > {amt}"
   }
   ```

3. **Custom Renderer Pattern**
   ```python
   # Good: Modular renderer registry
   RENDERER_REGISTRY = {
       "timeline": TimelineRenderer,
       "chart": ChartRenderer,
       "tree": TreeRenderer,
       "kanban": KanbanRenderer
   }
   
   def get_renderer(renderer_type):
       return RENDERER_REGISTRY.get(renderer_type, DefaultRenderer)
   ```

4. **Performance Optimization Pattern**
   ```python
   # Good: Selective eager loading
   def optimize_query_for_view(query, view_type):
       if view_type == 'list':
           # Minimal data for list view
           query = query.options(load_only('id', 'name', 'status'))
       elif view_type == 'detail':
           # Full data with relationships
           query = query.options(
               joinedload('supplier'),
               selectinload('items')
           )
       return query
   ```

### **❌ Advanced Anti-Patterns to Avoid**

1. **Don't hardcode user preferences**
   ```python
   # ❌ Bad
   if user.user_id == "admin":
       show_deleted = True
   
   # ✅ Good
   show_deleted = user.ui_preferences.get('show_deleted_records', False)
   ```

2. **Don't mix display logic with business logic**
   ```python
   # ❌ Bad
   if field.complex_display_type == ComplexDisplayType.BADGE:
       item.status = 'approved'  # Don't change data in display logic!
   
   # ✅ Good
   # Keep display and business logic separate
   display_value = format_as_badge(item.status)
   ```

3. **Don't create circular dependencies**
   ```python
   # ❌ Bad
   field1.conditional_display = "field2.value > 0"
   field2.conditional_display = "field1.value > 0"  # Circular!
   
   # ✅ Good
   # Use hierarchical conditions
   field2.conditional_display = "item.category == 'premium'"
   ```

---

## **26. Troubleshooting Advanced Features**

### **🔍 Common Advanced Issues & Solutions**

| **Issue** | **Symptom** | **Solution** |
|-----------|-------------|--------------|
| **User preference not saving** | UI preferences lost on reload | Ensure `flag_modified(user, "ui_preferences")` is called |
| **Conditional display not working** | Fields always show/hide | Check expression syntax, verify evaluator is registered |
| **Custom renderer not loading** | Default display shown | Verify template path, check context function exists |
| **Action condition failing** | Button always hidden | Debug condition with logging, check user permissions |
| **Performance degradation** | Slow with complex conditions | Cache condition results, optimize evaluators |
| **Plugin not loading** | Feature missing | Check module path, verify dependencies |

### **🛠️ Advanced Debugging Tools**

```python
# Debug user preferences
def debug_user_preferences(user_id):
    """Debug user preferences"""
    with get_db_session() as session:
        user = session.query(User).filter_by(user_id=user_id).first()
        print(f"User: {user_id}")
        print(f"UI Preferences: {json.dumps(user.ui_preferences, indent=2)}")
        print(f"Preference type: {type(user.ui_preferences)}")

# Debug conditional display
def debug_conditional_display(field, item, user):
    """Debug why field is/isn't showing"""
    condition = field.conditional_display
    print(f"Field: {field.name}")
    print(f"Condition: {condition}")
    print(f"Item data: {item}")
    print(f"User permissions: {user.get_permissions()}")
    
    # Evaluate condition
    try:
        result = eval(condition, {'item': item, 'user': user})
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

# Debug custom renderer
def debug_custom_renderer(field, item):
    """Debug custom renderer issues"""
    renderer = field.custom_renderer
    print(f"Template: {renderer.template}")
    print(f"Context function: {renderer.context_function}")
    
    # Try to call context function
    if renderer.context_function:
        try:
            context = globals()[renderer.context_function](item, field, current_user)
            print(f"Context: {json.dumps(context, indent=2)}")
        except Exception as e:
            print(f"Context error: {e}")

# Performance profiling
from functools import wraps
import time

def profile_performance(func):
    """Profile function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        logger.info(f"{func.__name__} took {duration:.3f}s")
        
        if duration > 1.0:  # Log slow operations
            logger.warning(f"Slow operation: {func.__name__} ({duration:.3f}s)")
        
        return result
    return wrapper
```

### **📝 Advanced Configuration Validation**

```python
def validate_advanced_configuration(config: EntityConfiguration):
    """Validate advanced configuration options"""
    
    issues = []
    warnings = []
    
    # Check conditional displays
    for field in config.fields:
        if field.conditional_display:
            try:
                # Test compile the condition
                compile(field.conditional_display, '<string>', 'eval')
            except SyntaxError as e:
                issues.append(f"Field {field.name}: Invalid condition syntax: {e}")
    
    # Check custom renderers
    for field in config.fields:
        if field.custom_renderer:
            # Check template exists
            template_path = field.custom_renderer.template
            if not os.path.exists(f"templates/{template_path}"):
                warnings.append(f"Field {field.name}: Template not found: {template_path}")
            
            # Check context function
            if field.custom_renderer.context_function:
                func_name = field.custom_renderer.context_function
                if func_name not in globals():
                    warnings.append(f"Field {field.name}: Context function not found: {func_name}")
    
    # Check action conditions
    for action in config.actions:
        if action.conditional_display:
            try:
                compile(action.conditional_display, '<string>', 'eval')
            except SyntaxError as e:
                issues.append(f"Action {action.id}: Invalid condition: {e}")
    
    # Check for circular dependencies
    dependency_graph = build_dependency_graph(config.fields)
    if has_circular_dependency(dependency_graph):
        issues.append("Circular dependency detected in field conditions")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }
```

---

# **Part VI: Reference**

## **27. Quick Reference Guide**

1. **Start with Entity Registry**
   - Always register entity first
   - Set correct category (MASTER/TRANSACTION)
   - Configure cache settings

2. **Define Fields Comprehensively**
   ```python
   # Good: Complete field definition
   FieldDefinition(
       name="status",
       label="Status",
       field_type=FieldType.SELECT,
       required=True,
       default_value="active",
       options=[...],
       searchable=True,
       filterable=True,
       tab_group="profile",
       section="basic_info",
       view_order=10
   )
   ```

3. **Use Consistent Naming**
   - Entity type: `snake_case` (e.g., `supplier_payments`)
   - Field names: `snake_case` (e.g., `payment_date`)
   - Display labels: `Title Case` (e.g., `Payment Date`)

4. **Configure Cache Appropriately**
   - Master entities: Longer TTL (1-2 hours)
   - Transaction entities: Shorter TTL (5-15 minutes)
   - Always use cache decorator on service methods

5. **Organize Fields Logically**
   - Group related fields in sections
   - Use tabs for complex entities
   - Order fields by importance

### **❌ Common Pitfalls to Avoid**

1. **Don't hardcode entity-specific logic**
   ```python
   # ❌ Bad
   if entity_type == "suppliers":
       # Special logic
   
   # ✅ Good
   if config.entity_category == EntityCategory.MASTER:
       # Category-based logic
   ```

2. **Don't skip cache decorators**
   ```python
   # ❌ Bad - No caching
   def search_data(self, filters, **kwargs):
       return super().search_data(filters, **kwargs)
   
   # ✅ Good - With caching
   @cache_service_method()
   def search_data(self, filters, **kwargs):
       return super().search_data(filters, **kwargs)
   ```

3. **Don't mix business logic layers**
   - Keep calculations in services
   - Keep display logic in templates
   - Keep validation in forms/models

---

## **20. Troubleshooting & Debugging**

### **🔍 Common Issues & Solutions**

| **Issue** | **Symptom** | **Solution** |
|-----------|-------------|--------------|
| **Entity not loading** | 404 error | Check entity registry, verify module path |
| **Fields not showing** | Missing in form/view | Check `show_in_form`, `show_in_detail` flags |
| **Cache not working** | Slow performance | Add `@cache_service_method()` decorator |
| **Permissions denied** | 403 error | Check user permissions, verify permission keys |
| **Data not saving** | Form errors | Check required fields, validation rules |
| **Documents not generating** | No button/error | Set `document_enabled=True`, check configs |

### **🛠️ Debugging Tools**

```python
# 1. Validate configuration
from app.config.entity_configurations import get_entity_config

config = get_entity_config('your_entity')
print(f"Config loaded: {config is not None}")
print(f"Fields: {len(config.fields)}")
print(f"CRUD enabled: {config.universal_crud_enabled}")

# 2. Check cache performance
from app.engine.universal_service_cache import debug_cache_key_for_request

debug_info = debug_cache_key_for_request()
print(debug_info)

# 3. Test service methods
from app.engine.universal_services import get_universal_service

service = get_universal_service('your_entity')
result = service.search_data({}, hospital_id='xxx')
print(f"Results: {result.get('total_count')}")

# 4. Validate permissions
from flask_login import current_user
from app.security.authorization.permission_validator import has_permission

can_view = has_permission(current_user, 'your_entity', 'view')
print(f"Can view: {can_view}")
```

### **📝 Logging & Monitoring**

```python
# Enable debug logging
import logging

# For configuration issues
logging.getLogger('app.config').setLevel(logging.DEBUG)

# For cache issues
logging.getLogger('app.engine.universal_service_cache').setLevel(logging.DEBUG)

# For service issues
logging.getLogger('app.engine.universal_entity_service').setLevel(logging.DEBUG)

# Check logs
tail -f logs/app.log | grep -i your_entity
```

---

# **Part VI: Reference**

## **21. Quick Reference Guide**

### **📋 Entity Setup Checklist**

- [ ] Register entity in `entity_registry.py`
- [ ] Create configuration module
- [ ] Define all fields with proper types
- [ ] Configure sections and tabs
- [ ] Set up view layout
- [ ] Configure actions and permissions
- [ ] Add summary cards
- [ ] Configure filters
- [ ] Set up documents (if needed)
- [ ] Create service class with cache decorators
- [ ] Test all operations
- [ ] Monitor cache performance

### **🚀 Minimal Working Configuration**

```python
# Minimal entity configuration
MINIMAL_ENTITY_CONFIG = EntityConfiguration(
    # Required fields only
    entity_type="simple_entity",
    name="Simple Entity",
    plural_name="Simple Entities",
    service_name="simple_entity",
    table_name="simple_entities",
    primary_key="id",
    title_field="name",
    
    # Minimal fields
    fields=[
        FieldDefinition(
            name="id",
            label="ID",
            field_type=FieldType.UUID,
            readonly=True
        ),
        FieldDefinition(
            name="name",
            label="Name",
            field_type=FieldType.TEXT,
            required=True
        )
    ],
    
    # Enable features
    universal_crud_enabled=True,
    entity_category=EntityCategory.MASTER
)
```

---

## **22. Performance Benchmarks**

### **📊 Performance Metrics**

| **Operation** | **Without Cache** | **With Cache** | **Improvement** |
|---------------|-------------------|----------------|-----------------|
| Entity Config Load | 10ms | 0.01ms | 1000x |
| List View (20 items) | 200ms | 20ms | 10x |
| Detail View | 150ms | 5ms | 30x |
| Filtered Search | 300ms | 30ms | 10x |
| Document Generation | 500ms | 100ms | 5x |
| Bulk Export (1000 items) | 5000ms | 1000ms | 5x |

### **💾 Memory Usage**

| **Component** | **Memory Usage** | **Items Cached** |
|---------------|------------------|------------------|
| Service Cache | ~300MB | 5000 queries |
| Config Cache | ~5MB | 50 configurations |
| Total | ~305MB | All entities |

---

## **23. URL Patterns & Routes**

### **🔗 Standard URL Patterns**

| **Operation** | **Pattern** | **Example** |
|---------------|-------------|-------------|
| **List** | `/universal/{entity}/list` | `/universal/suppliers/list` |
| **View** | `/universal/{entity}/detail/{id}` | `/universal/suppliers/detail/uuid` |
| **Create** | `/universal/{entity}/create` | `/universal/suppliers/create` |
| **Edit** | `/universal/{entity}/edit/{id}` | `/universal/suppliers/edit/uuid` |
| **Delete** | `/universal/{entity}/delete/{id}` | `/universal/suppliers/delete/uuid` |
| **Export** | `/universal/{entity}/export` | `/universal/suppliers/export?format=excel` |
| **Document** | `/universal/{entity}/document/{id}/{type}` | `/universal/suppliers/document/uuid/profile` |

### **🔗 API Endpoints**

| **Operation** | **Pattern** | **Method** |
|---------------|-------------|------------|
| **List API** | `/api/universal/{entity}` | GET |
| **Detail API** | `/api/universal/{entity}/{id}` | GET |
| **Create API** | `/api/universal/{entity}` | POST |
| **Update API** | `/api/universal/{entity}/{id}` | PUT |
| **Delete API** | `/api/universal/{entity}/{id}` | DELETE |
| **Search API** | `/api/universal/{entity}/search` | POST |

---

## **24. Appendix & Resources**

### **📁 Project Structure**

```
app/
├── config/
│   ├── entity_registry.py         # Entity registry
│   ├── entity_configurations.py   # Configuration loader
│   ├── core_definitions.py        # Core classes
│   ├── filter_categories.py       # Filter definitions
│   └── modules/
│       ├── master_entities.py     # Master configs
│       └── financial_transactions.py  # Transaction configs
├── engine/
│   ├── universal_entity_service.py    # Base service
│   ├── universal_crud_service.py      # CRUD operations
│   ├── universal_service_cache.py     # Service cache
│   ├── universal_config_cache.py      # Config cache
│   └── document_service.py            # Document engine
├── services/
│   └── your_entity_service.py     # Entity services
├── models/
│   └── master.py                  # SQLAlchemy models
├── views/
│   └── universal_views.py         # Universal routes
└── templates/
    └── universal/
        ├── list.html              # List template
        ├── detail.html            # Detail template
        ├── form.html              # Form template
        └── document.html          # Document template
```

### **📚 Key Files Reference**

| **File** | **Purpose** |
|----------|-------------|
| `entity_registry.py` | Central entity registration |
| `entity_configurations.py` | Configuration loader with cache |
| `core_definitions.py` | Core data structures |
| `universal_entity_service.py` | Base service class |
| `universal_service_cache.py` | Service caching layer |
| `universal_config_cache.py` | Configuration caching |
| `universal_crud_service.py` | CRUD operations |
| `document_service.py` | Document generation |
| `universal_views.py` | Route handlers |

### **🔧 Environment Variables**

```bash
# Cache Configuration
SERVICE_CACHE_ENABLED=true
SERVICE_CACHE_MAX_MEMORY_MB=500
SERVICE_CACHE_DEFAULT_TTL=1800

CONFIG_CACHE_ENABLED=true
CONFIG_CACHE_PRELOAD=true
CONFIG_CACHE_TTL=3600

# Performance
CACHE_WARMUP_ON_STARTUP=true
CACHE_MONITORING_ENABLED=true
```

### **📖 Additional Documentation**

- **Cache Strategy**: `Optimal Multi-Layer Caching Strategy.md`
- **Document Engine**: `Universal Document Engine v3.0.md`
- **Development Guidelines**: `SkinSpire Clinic HMS Technical Development Guidelines v2.0`
- **Architecture**: `Universal Engine Master Architecture Revised Implementation Guide v2.0`

---

## **🎉 Conclusion**

The Universal Engine v4.0 provides a complete, production-ready framework for entity management with:

- **90% Performance Improvement** through dual-layer caching
- **90% Code Reduction** through configuration-driven design
- **100% Consistency** across all entities
- **Enterprise Features** including CRUD, documents, filtering, and caching
- **Zero-Code Integration** for new entities

By following this comprehensive guide, you can:
1. Configure any entity in minutes
2. Get automatic caching and performance optimization
3. Provide rich functionality without writing code
4. Maintain consistency across your application
5. Scale effortlessly as requirements grow

The Universal Engine represents the pinnacle of configuration-driven development, delivering enterprise-grade functionality through simple, maintainable configurations.

---

**Universal Engine v4.0 - Configuration-Driven Excellence**

*Built for the SkinSpire Clinic HMS Project*
*Engineered for Performance, Designed for Simplicity*