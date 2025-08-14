# Universal Engine Entity Configuration - Complete Guide
## Step-by-Step Configuration Instructions

---

## 📋 **Table of Contents**
1. [Universal Engine Principles](#1-universal-engine-principles)
2. [Pre-Configuration Checklist](#2-pre-configuration-checklist)
3. [Step-by-Step Configuration Process](#3-step-by-step-configuration-process)
4. [Configuration Structure Guide](#4-configuration-structure-guide)
5. [Custom Rendering Examples](#5-custom-rendering-examples)
6. [Validation & Testing](#6-validation-testing)
7. [Common Patterns & Best Practices](#7-common-patterns--best-practices)
8. [Troubleshooting Guide](#8-troubleshooting-guide)

---

## **1. Universal Engine Principles**

### **Core Principles to Follow**

#### **✅ Configuration-Driven**
- ALL behavior defined in configuration, not code
- No entity-specific logic in templates or services
- Use enums and constants, not magic strings

```python
# ✅ GOOD: Configuration-driven
FieldDefinition(
    name="status",
    field_type=FieldType.SELECT,
    options=[
        {"value": "active", "label": "Active"},
        {"value": "inactive", "label": "Inactive"}
    ]
)

# ❌ BAD: Hardcoded logic
if entity_type == "suppliers":
    status_options = ["active", "inactive"]  # Don't do this!
```

#### **✅ Backend-Heavy**
- All calculations in service layer
- No business logic in JavaScript
- Database queries optimized at service level

```python
# Service Layer (GOOD)
class SupplierMasterService(UniversalEntityService):
    def _calculate_summary(self, session, hospital_id, branch_id, filters, total_count):
        # Calculate total_purchases here
        summary['total_purchases'] = self._get_total_purchases(supplier_id)
        return summary

# Configuration (Reference calculated field)
FieldDefinition(
    name="total_purchases",
    virtual=True,  # Calculated, not stored
    readonly=True
)
```

#### **✅ Entity-Agnostic**
- Universal components don't know about specific entities
- Same patterns work for any entity
- Reusable across all modules

#### **✅ Minimal JavaScript**
- Only for UI interactions (tabs, accordions, dropdowns)
- No data processing or calculations
- Progressive enhancement approach

---

## **2. Pre-Configuration Checklist**

### **Before You Start, Gather:**

#### **📊 Database Model**
```python
# Check your model in app/models/master.py or transaction.py
class Supplier(Base):
    __tablename__ = 'suppliers'
    
    supplier_id = Column(UUID, primary_key=True)
    supplier_name = Column(String(100), nullable=False)
    contact_info = Column(JSONB)  # Note: JSONB, not JSON
    # ... map ALL fields
```

#### **🔍 Field Mapping**
| Database Column | Field Type | Required | Virtual | Notes |
|----------------|------------|----------|---------|-------|
| supplier_id | UUID | Yes | No | Primary key |
| supplier_name | TEXT | Yes | No | Display name |
| contact_info | JSONB | No | No | Store as JSONB |
| phone | - | No | Yes | Extract from contact_info |
| total_purchases | - | No | Yes | Calculate in service |

#### **📁 Module Structure**
```
app/config/modules/
├── master_entities.py       # Master data (suppliers, patients)
├── financial_transactions.py # Transactions (payments, invoices)
└── inventory.py             # Inventory (medicines, stock)
```

#### **🔧 Service Implementation**
```python
# app/services/supplier_master_service.py
class SupplierMasterService(UniversalEntityService):
    def __init__(self):
        super().__init__('suppliers', Supplier)
    
    def _convert_items_to_dict(self, items, session):
        # Extract virtual fields like phone from JSONB
        pass
```

---

## **3. Step-by-Step Configuration Process**

### **Step 1: Import Required Definitions**
```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition, 
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration, ButtonType,
    ComplexDisplayType, ActionDisplayType,
    DocumentConfiguration, PrintLayoutType, DocumentType,
    PageSize, Orientation, ExportFormat
)
from app.config.filter_categories import FilterCategory
```

### **Step 2: Define Fields**
```python
ENTITY_FIELDS = [
    # Primary Key - Always first
    FieldDefinition(
        name="entity_id",  # Must match database column
        label="Entity ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="profile",  # Which tab
        section="identification",  # Which section
        view_order=0  # Order within section
    ),
    
    # Required Fields
    FieldDefinition(
        name="entity_name",
        label="Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,  # Form validation
        searchable=True,  # Text search
        sortable=True,  # Column sort
        filterable=True,  # Filter dropdown
        placeholder="Enter name",
        tab_group="profile",
        section="basic_info",
        view_order=1
    ),
    
    # Virtual/Calculated Fields
    FieldDefinition(
        name="calculated_total",
        label="Total",
        field_type=FieldType.DECIMAL,
        virtual=True,  # Not in database
        readonly=True,  # Can't edit
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,  # Don't show in forms
        tab_group="statistics",
        section="summary",
        view_order=1
    )
]
```

### **Step 3: Define Sections**
```python
ENTITY_SECTIONS = {
    'identification': SectionDefinition(
        key='identification',
        title='Identification',
        icon='fas fa-id-card',
        columns=2,  # 2-column layout
        order=0
    ),
    'basic_info': SectionDefinition(
        key='basic_info',
        title='Basic Information',
        icon='fas fa-info-circle',
        columns=2,
        order=1
    ),
    # Conditional section
    'payment_details': SectionDefinition(
        key='payment_details',
        title='Payment Information',
        icon='fas fa-credit-card',
        columns=2,
        order=2,
        conditional_display="item.has_payments"  # Only show if condition true
    )
}
```

### **Step 4: Define Tabs**
```python
ENTITY_TABS = {
    'profile': TabDefinition(
        key='profile',
        label='Profile',
        icon='fas fa-user',
        sections={
            'identification': ENTITY_SECTIONS['identification'],
            'basic_info': ENTITY_SECTIONS['basic_info']
        },
        order=0,
        default_active=True  # Open by default
    ),
    'financial': TabDefinition(
        key='financial',
        label='Financial',
        icon='fas fa-dollar-sign',
        sections={
            'payment_details': ENTITY_SECTIONS['payment_details']
        },
        order=1
    )
}
```

### **Step 5: Configure View Layout**
```python
ENTITY_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,  # SIMPLE, TABBED, or ACCORDION
    responsive_breakpoint='md',
    tabs=ENTITY_TABS,
    default_tab='profile',
    sticky_tabs=False,
    auto_generate_sections=False,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "entity_id",
        "primary_label": "ID",
        "title_field": "entity_name",  # Main display field
        "title_label": "Name",
        "status_field": "status",
        "secondary_fields": [
            {"field": "category", "label": "Category", "icon": "fas fa-tag"},
            {"field": "created_at", "label": "Created", "icon": "fas fa-calendar", "type": "date"}
        ]
    }
)
```

### **Step 6: Define Actions**
```python
ENTITY_ACTIONS = [
    ActionDefinition(
        id="create",
        label="New Entity",
        icon="fas fa-plus",
        url_pattern="/universal/{entity_type}/create",
        button_type=ButtonType.PRIMARY,
        permission="entity_create",
        show_in_list=True,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),
    ActionDefinition(
        id="edit",
        label="Edit",
        icon="fas fa-edit",
        url_pattern="/entities/edit/{entity_id}",
        button_type=ButtonType.PRIMARY,
        permission="entity_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        order=2,
        conditions={
            "status": ["draft", "pending"]  # Only show for these statuses
        }
    )
]
```

### **Step 7: Configure Filters**
```python
ENTITY_FILTER_MAPPING = {
    # Date filters
    'created_from': FilterCategory.DATE,
    'created_to': FilterCategory.DATE,
    
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

ENTITY_DEFAULT_FILTERS = {
    'status': 'active'  # Default filter
}
```

### **Step 8: Create Main Configuration**
```python
ENTITY_CONFIG = EntityConfiguration(
    # ========== REQUIRED PARAMETERS (no defaults) ==========
    entity_type="entities",
    name="Entity",
    plural_name="Entities",
    service_name="entities",
    table_name="entities",
    primary_key="entity_id",
    title_field="entity_name",
    subtitle_field="category",
    icon="fas fa-cube",
    page_title="Entity Management",
    description="Manage entities",
    searchable_fields=["entity_name", "description"],
    default_sort_field="entity_name",
    default_sort_direction="asc",
    fields=ENTITY_FIELDS,
    actions=ENTITY_ACTIONS,
    summary_cards=ENTITY_SUMMARY_CARDS,
    permissions=ENTITY_PERMISSIONS,
    
    # ========== OPTIONAL PARAMETERS ==========
    model_class="app.models.master.Entity",
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    view_layout=ENTITY_VIEW_LAYOUT,
    section_definitions=ENTITY_SECTIONS,
    filter_category_mapping=ENTITY_FILTER_MAPPING,
    default_filters=ENTITY_DEFAULT_FILTERS,
    category_configs=ENTITY_CATEGORY_CONFIGS,
    primary_date_field="created_at",
    primary_amount_field="amount",
    document_enabled=True,
    document_configs=ENTITY_DOCUMENT_CONFIGS,
    default_document="profile"
)
```

---

## **4. Configuration Structure Guide**

### **Layout Types Decision Tree**

```
Choose Layout Type:
├── Simple Layout (LayoutType.SIMPLE)
│   ├── Use when: < 20 fields
│   ├── Good for: Quick views, simple entities
│   └── Example: User profiles, categories
│
├── Tabbed Layout (LayoutType.TABBED)
│   ├── Use when: > 20 fields, logical groupings
│   ├── Good for: Complex entities with categories
│   └── Example: Suppliers, Patients, Products
│
└── Accordion Layout (LayoutType.ACCORDION)
    ├── Use when: Progressive disclosure needed
    ├── Good for: Mobile-first, step-by-step views
    └── Example: Forms, wizards, mobile views
```

### **Field Organization Best Practices**

```python
# Group related fields in sections
'contact_section': {
    'email': view_order=1,
    'phone': view_order=2,
    'address': view_order=3
}

# Use tabs for major categories
'profile_tab': ['identification', 'contact', 'basic_info']
'financial_tab': ['payments', 'invoices', 'balance']
'history_tab': ['audit', 'changes', 'logs']
```

---

## **5. Custom Rendering Examples**

### **Example 1: Multi-Method Payment Display**
```python
FieldDefinition(
    name="payment_methods",
    label="Payment Methods",
    field_type=FieldType.CUSTOM,
    custom_renderer=CustomRenderer(
        template='components/multi_payment_display.html',
        context_function=lambda item: {
            'cash': item.get('cash_amount', 0),
            'bank': item.get('bank_amount', 0),
            'upi': item.get('upi_amount', 0)
        }
    )
)
```

### **Example 2: Status Badge with Color**
```python
FieldDefinition(
    name="status",
    label="Status",
    field_type=FieldType.STATUS_BADGE,
    custom_renderer=CustomRenderer(
        template='<span class="badge badge-{color}">{value}</span>',
        context_function=lambda item: {
            'color': 'success' if item['status'] == 'active' else 'danger',
            'value': item['status'].upper()
        }
    )
)
```

### **Example 3: Transaction History Table**
```python
FieldDefinition(
    name="transaction_history",
    label="Recent Transactions",
    field_type=FieldType.CUSTOM,
    virtual=True,
    custom_renderer=CustomRenderer(
        template='components/transaction_table.html',
        context_function=lambda item: {
            'transactions': item.get('recent_transactions', [])[:10],
            'show_balance': True,
            'currency_symbol': '₹'
        }
    ),
    tab_group="history",
    section="transactions",
    view_order=1
)
```

---

## **6. Validation & Testing**

### **Configuration Validation Checklist**

#### **✅ Field Validation**
```python
# Check each field:
assert field.name in database_columns or field.virtual
assert field.field_type in FieldType.__members__.values()
assert field.tab_group in defined_tabs
assert field.section in defined_sections
```

#### **✅ Enum Validation**
```python
# Validate all enums exist:
FieldType.TEXT ✓ (not FieldType.STRING ✗)
FieldType.JSONB ✓ (not FieldType.JSON ✗)
PrintLayoutType.SIMPLE_WITH_HEADER ✓ (not PrintLayoutType.STANDARD ✗)
```

#### **✅ Structure Validation**
```python
# Tabs must be dictionary, not list
tabs = {  # ✓ Correct
    'tab_key': TabDefinition(key='tab_key', ...)
}

tabs = [  # ✗ Wrong
    TabDefinition(id='tab_id', ...)
]
```

### **Testing Steps**

1. **Load Test**
   ```bash
   # Navigate to list view
   /universal/entity_type/list
   # Check logs for configuration errors
   ```

2. **Field Display Test**
   - All fields appear in correct tabs/sections
   - Virtual fields show calculated values
   - Required fields marked with asterisk

3. **Action Test**
   - Buttons appear in correct locations
   - Permissions control visibility
   - URLs generate correctly

4. **Filter Test**
   - Search works for searchable fields
   - Sort works for sortable columns
   - Filters apply correctly

---

## **7. Common Patterns & Best Practices**

### **Pattern 1: JSONB Field Extraction**
```python
# Database has JSONB, extract specific fields
FieldDefinition(
    name="contact_info",
    field_type=FieldType.JSONB,  # Store entire JSON
    show_in_form=True
)

FieldDefinition(
    name="phone",  # Virtual field
    field_type=FieldType.TEXT,
    virtual=True,  # Extracted from contact_info
    show_in_list=True
)

# In service:
def _convert_items_to_dict(self, items, session):
    for item in items:
        if item.contact_info:
            item_dict['phone'] = item.contact_info.get('phone', '')
```

### **Pattern 2: Conditional Display**
```python
# Show section only if condition met
SectionDefinition(
    key='payment_info',
    title='Payment Information',
    conditional_display="item.has_payments == true"
)

# Show field only for certain statuses
FieldDefinition(
    name="approval_date",
    conditional_display="item.status == 'approved'"
)
```

### **Pattern 3: Related Entity Display**
```python
FieldDefinition(
    name="supplier_name",
    field_type=FieldType.TEXT,
    related_field="supplier",  # Relationship
    complex_display_type=ComplexDisplayType.ENTITY_REFERENCE
)
```

---

## **8. Troubleshooting Guide**

### **Common Errors & Solutions**

#### **Error: "TabDefinition.__init__() got an unexpected keyword argument 'id'"**
```python
# ✗ Wrong
TabDefinition(id="tab_name", ...)

# ✓ Correct
TabDefinition(key="tab_name", ...)
```

#### **Error: "type object 'FieldType' has no attribute 'JSON'"**
```python
# ✗ Wrong
field_type=FieldType.JSON

# ✓ Correct
field_type=FieldType.JSONB
```

#### **Error: "Configuration not found for entity"**
```python
# Check entity_configurations.py:
MODULE_MAPPING = {
    "your_entity": "app.config.modules.your_module",  # Add this
}

# In your module:
def get_module_configs():
    return {"your_entity": YOUR_ENTITY_CONFIG}
```

#### **Error: "Field not found in model"**
```python
# Either:
1. Add field to database model
2. Mark field as virtual=True
3. Remove field from configuration
```

---

## **📝 Quick Reference Card**

### **Required Imports**
```python
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition, 
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition, ButtonType,
    ActionDisplayType, DocumentConfiguration
)
```

### **Configuration Structure**
```
EntityConfiguration
├── Basic Info (required, no defaults)
├── Fields (List[FieldDefinition])
├── Sections (Dict[str, SectionDefinition])
├── Tabs (Dict[str, TabDefinition])
├── View Layout (ViewLayoutConfiguration)
├── Actions (List[ActionDefinition])
├── Filters (Dict mappings)
├── Documents (Dict[str, DocumentConfiguration])
└── Permissions (Dict[str, str])
```

### **Field Types Quick Reference**
- `TEXT` - Single line text
- `TEXTAREA` - Multi-line text
- `NUMBER` - Integer
- `DECIMAL` - Float/Money
- `DATE` - Date only
- `DATETIME` - Date and time
- `SELECT` - Dropdown
- `BOOLEAN` - Checkbox
- `UUID` - Unique ID
- `JSONB` - JSON data (not JSON!)
- `ENTITY_SEARCH` - Related entity
- `CUSTOM` - Custom renderer

### **Layout Types**
- `SIMPLE` - All sections visible
- `TABBED` - Organized in tabs
- `ACCORDION` - Collapsible sections

### **Button Types**
- `PRIMARY` - Main action (blue)
- `SECONDARY` - Secondary (gray)
- `SUCCESS` - Success (green)
- `DANGER` - Delete (red)
- `WARNING` - Warning (yellow)
- `INFO` - Information (light blue)
- `OUTLINE` - Border only

---

## **🎯 Remember: Configuration Over Code!**

The Universal Engine's power comes from configuration. When in doubt:
1. Check existing working configurations (financial_transactions.py)
2. Validate against core_definitions.py
3. Test incrementally
4. Follow the patterns

Your configuration is the single source of truth - make it complete, correct, and consistent!