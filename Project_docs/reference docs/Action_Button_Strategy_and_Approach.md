# Action Button Strategy and Approach
**SkinSpire Clinic HMS - Universal Engine**
**Version:** 2.0
**Date:** November 16, 2025
**Status:** Production Standard

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Design Philosophy](#design-philosophy)
3. [Architecture Overview](#architecture-overview)
4. [Configuration Standards](#configuration-standards)
5. [Implementation Patterns](#implementation-patterns)
6. [Technical Reference](#technical-reference)
7. [Migration Guide](#migration-guide)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Executive Summary

### Purpose
This document defines the standardized approach for action buttons across all Universal Engine entities in the SkinSpire Clinic HMS. It provides a consistent, configuration-driven framework for navigation, CRUD operations, and business workflows.

### Key Benefits
- **Consistency**: Uniform button placement and behavior across all modules
- **Maintainability**: Configuration-driven with zero hardcoding
- **Scalability**: Easy to add new entities following established patterns
- **User Experience**: Predictable navigation and action discovery
- **Developer Efficiency**: Reduced development time for new features

### Scope
- All Universal Engine entities (Supplier Module, Patient/Billing Module)
- List views, Detail views, and Form views
- Navigation buttons, CRUD actions, and workflow actions
- Print/Export operations and conditional actions

---

## Design Philosophy

### Core Principles

#### 1. **Configuration Over Code**
All action buttons are defined in entity configuration files, not hardcoded in templates. This ensures:
- Single source of truth for each entity's actions
- Easy modifications without touching template code
- Clear separation of concerns

#### 2. **Explicit Over Implicit**
Using clear, unambiguous flags eliminates confusion:
```python
# ❌ OLD APPROACH (Ambiguous)
show_in_toolbar=True  # Which toolbar? List or Detail?

# ✅ NEW APPROACH (Explicit)
show_in_list_toolbar=True     # List page toolbar
show_in_detail_toolbar=True   # Detail page toolbar
```

#### 3. **Consistency Across Modules**
All entities follow the same standardized layout:
- **List Toolbar**: [Back] [Related Lists...] [Create New]
- **Detail Toolbar**: [Back] [Related Lists...] [Print] [Actions ▼]
- **List Rows**: View, conditional actions (Approve, Delete, etc.)
- **Detail Dropdown**: Edit, Delete, Workflow actions

#### 4. **Context-Aware Actions**
Actions appear only where they make sense:
- Create buttons only in list toolbars
- Edit/Delete in detail dropdown
- Print in both list rows and detail toolbar
- Approve/Delete in list rows when applicable

---

## Architecture Overview

### Component Stack

```
┌─────────────────────────────────────────────────────┐
│   USER INTERFACE (Browser)                         │
│   - List View Template (universal_list.html)       │
│   - Detail View Template (universal_view.html)     │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│   UNIVERSAL ENGINE (Backend)                        │
│   - Data Assembler (data_assembler.py)            │
│   - Entity Service (universal_entity_service.py)   │
│   - Config Cache (universal_config_cache.py)       │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│   CONFIGURATION LAYER                               │
│   - Core Definitions (core_definitions.py)         │
│   - Entity Configs (modules/*.py)                  │
│   - Action Definitions (ActionDefinition class)    │
└─────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User Request → Route Handler
2. Route Handler → Universal Entity Service
3. Entity Service → Config Manager (get entity config)
4. Config Manager → Entity Config File (load actions)
5. Data Assembler → Filter actions by context
6. Data Assembler → Evaluate conditions
7. Template → Render visible actions
8. User → Sees context-appropriate buttons
```

---

## Configuration Standards

### ActionDefinition Structure

```python
from app.config.core_definitions import (
    ActionDefinition,
    ActionDisplayType,
    ButtonType
)

ActionDefinition(
    # ========== IDENTIFICATION ==========
    id="unique_action_id",              # Unique within entity
    label="Button Label",                # Display text
    icon="fas fa-icon-name",            # FontAwesome icon

    # ========== ROUTING ==========
    # Option 1: Flask route name (preferred)
    route_name="views.route_function",
    route_params={"key": "{field_name}"},

    # Option 2: URL pattern
    url_pattern="/path/to/action/{field_name}",

    # ========== DISPLAY CONTROL ==========
    button_type=ButtonType.PRIMARY,      # PRIMARY, SECONDARY, SUCCESS, etc.

    # NEW: Explicit toolbar context flags
    show_in_list=False,                  # Row actions in list table
    show_in_list_toolbar=True,           # List page top toolbar
    show_in_detail_toolbar=False,        # Detail page top toolbar

    display_type=ActionDisplayType.BUTTON,  # BUTTON or DROPDOWN_ITEM

    # ========== CONDITIONAL DISPLAY ==========
    conditions={                         # Field-based conditions
        "status": ["draft", "pending"],
        "is_deleted": [False, None]
    },

    # ========== PERMISSIONS & CONFIRMATIONS ==========
    permission="entity_action_permission",
    confirmation_required=True,
    confirmation_message="Are you sure?",

    # ========== ORDERING ==========
    order=1                              # Display order (left to right)
)
```

### Flag Combinations Reference

| Context | show_in_list | show_in_list_toolbar | show_in_detail_toolbar | display_type |
|---------|--------------|---------------------|----------------------|--------------|
| List Toolbar Button | False | True | False | BUTTON |
| List Row Action | True | False | False | BUTTON |
| Detail Toolbar Button | False | False | True | BUTTON |
| Detail Dropdown Item | False | False | True | DROPDOWN_ITEM |

---

## Implementation Patterns

### Pattern 1: List Page Toolbar (Navigation)

**Purpose**: Cross-navigation between related entity lists + Create new record

**Standard Layout**: `[Back] [Related List 1] [Related List 2] ... [Create New]`

**Example - Supplier Invoices**:
```python
# Back button (auto-added by template)

# Related list navigation
ActionDefinition(
    id="goto_suppliers_list",
    label="Suppliers",
    icon="fas fa-building",
    button_type=ButtonType.SECONDARY,
    route_name="universal_views.universal_list_view",
    route_params={"entity_type": "suppliers"},
    show_in_list=False,
    show_in_list_toolbar=True,
    show_in_detail_toolbar=False,
    display_type=ActionDisplayType.BUTTON,
    permission="suppliers_view",
    order=1
),

# Create new button (always last)
ActionDefinition(
    id="create_invoice",
    label="Create Invoice",
    icon="fas fa-plus",
    button_type=ButtonType.PRIMARY,
    route_name="supplier_views.create_invoice",
    show_in_list=False,
    show_in_list_toolbar=True,
    show_in_detail_toolbar=False,
    display_type=ActionDisplayType.BUTTON,
    permission="supplier_invoice_create",
    order=4
)
```

### Pattern 2: List Row Actions (Per-Record)

**Purpose**: Quick actions on individual records in the list table

**Standard Actions**: View (always first), then conditional actions

**Example - Supplier Invoices**:
```python
# View action (always present)
ActionDefinition(
    id="view_row",
    label="View",
    icon="fas fa-eye",
    button_type=ButtonType.INFO,
    route_name="universal_views.universal_detail_view",
    route_params={"entity_type": "supplier_invoices", "item_id": "{invoice_id}"},
    show_in_list=True,
    show_in_list_toolbar=False,
    show_in_detail_toolbar=False,
    display_type=ActionDisplayType.BUTTON,
    permission="supplier_invoice_view",
    order=1
),

# Conditional action (only for unpaid)
ActionDefinition(
    id="delete_row",
    label="Delete",
    icon="fas fa-trash",
    button_type=ButtonType.DANGER,
    url_pattern="/supplier/invoice/delete/{invoice_id}",
    show_in_list=True,
    show_in_list_toolbar=False,
    show_in_detail_toolbar=False,
    display_type=ActionDisplayType.BUTTON,
    conditions={
        "payment_status": ["unpaid"],
        "is_deleted": [False, None]
    },
    permission="supplier_invoice_delete",
    order=2,
    confirmation_required=True,
    confirmation_message="Are you sure you want to delete this invoice?"
)
```

### Pattern 3: Detail Page Toolbar (Navigation)

**Purpose**: Navigate back to lists, access related records, print

**Standard Layout**: `[Back] [Entity List] [Related Lists...] [Print] [Actions ▼]`

**Example - Supplier Invoices**:
```python
# Back to entity list (always first)
ActionDefinition(
    id="goto_invoices_list",
    label="Supplier Invoices",
    icon="fas fa-file-invoice",
    button_type=ButtonType.SECONDARY,
    route_name="universal_views.universal_list_view",
    route_params={"entity_type": "supplier_invoices"},
    show_in_list=False,
    show_in_list_toolbar=False,
    show_in_detail_toolbar=True,
    display_type=ActionDisplayType.BUTTON,
    permission="supplier_invoice_view",
    order=1
),

# Print (usually last button before dropdown)
ActionDefinition(
    id="print_invoice",
    label="Print Invoice",
    icon="fas fa-print",
    button_type=ButtonType.INFO,
    route_name="universal_views.universal_document_view",
    route_params={
        "entity_type": "supplier_invoices",
        "item_id": "{invoice_id}",
        "doc_type": "invoice"
    },
    show_in_list=False,
    show_in_list_toolbar=False,
    show_in_detail_toolbar=True,
    display_type=ActionDisplayType.BUTTON,
    permission="supplier_invoice_print",
    order=5
)
```

### Pattern 4: Detail Page Dropdown (Actions Menu)

**Purpose**: Edit, Delete, Workflow actions (Approve, Reverse, etc.)

**Standard Actions**: Edit, Delete/Restore, Workflow-specific actions

**Example - Supplier Invoices**:
```python
ActionDefinition(
    id="edit_invoice",
    label="Edit Invoice",
    icon="fas fa-edit",
    button_type=ButtonType.WARNING,
    route_name="supplier_views.edit_supplier_invoice",
    route_params={"invoice_id": "{invoice_id}"},
    show_in_list=False,
    show_in_list_toolbar=False,
    show_in_detail_toolbar=True,
    display_type=ActionDisplayType.DROPDOWN_ITEM,
    conditions={
        "payment_status": ["unpaid", "partial"]
    },
    permission="supplier_invoice_edit",
    order=1
),

ActionDefinition(
    id="delete_invoice",
    label="Delete Invoice",
    icon="fas fa-trash",
    button_type=ButtonType.DANGER,
    url_pattern="/supplier/invoice/delete/{invoice_id}",
    show_in_list=False,
    show_in_list_toolbar=False,
    show_in_detail_toolbar=True,
    display_type=ActionDisplayType.DROPDOWN_ITEM,
    conditions={
        "payment_status": ["unpaid"],
        "is_deleted": [False, None]
    },
    permission="supplier_invoice_delete",
    order=2,
    confirmation_required=True,
    confirmation_message="Are you sure you want to delete this invoice?"
)
```

---

## Technical Reference

### Core Files Modified

#### 1. core_definitions.py
**Location**: `app/config/core_definitions.py`
**Changes**: Added new explicit toolbar flags to ActionDefinition

```python
@dataclass
class ActionDefinition:
    # ... existing fields ...

    # DEPRECATED: Ambiguous flag
    show_in_toolbar: bool = False

    # NEW: Explicit toolbar context flags
    show_in_list_toolbar: bool = False   # Show in LIST page toolbar
    show_in_detail_toolbar: bool = False # Show in DETAIL/VIEW page toolbar
```

**Lines**: 449-460

#### 2. universal_list.html
**Location**: `app/templates/engine/universal_list.html`
**Changes**: Updated toolbar filter to use new explicit flag

```jinja2
{# OLD: Ambiguous filter #}
{% if action.show_in_toolbar %}

{# NEW: Explicit filter #}
{% if action.show_in_list_toolbar %}
```

**Lines**: 62

#### 3. data_assembler.py
**Location**: `app/engine/data_assembler.py`
**Changes**: Added backward compatibility for detail toolbar

```python
# Use new explicit flag if available, fallback to old flag
show_in_detail_toolbar = getattr(action, 'show_in_detail_toolbar', None)
if show_in_detail_toolbar is None:
    # Fallback to old logic for backward compatibility
    show_in_detail_toolbar = getattr(action, 'show_in_detail', False)

if not show_in_detail_toolbar:
    continue
```

**Lines**: 1022-1031

### Entity Configuration Files

All entity configs follow the same structure:

```
app/config/modules/
├── supplier_invoice_config.py      ✅ COMPLETED
├── purchase_orders_config.py       ✅ COMPLETED
├── supplier_payment_config.py      ✅ COMPLETED
├── patient_invoice_config.py       ✅ COMPLETED
├── patient_payment_config.py       ⏳ PENDING
├── package_config.py               ⏳ PENDING
└── consolidated_invoice_config.py  ⏳ PENDING
```

### Condition Evaluation Logic

**Template Logic** (`universal_list.html:745-772`):
```jinja2
{% set show_action = true %}

{% if action.conditions %}
    {% for field, allowed_values in action.conditions.items() %}
        {% set field_value = item.get(field) %}

        {# Handle None values for boolean fields #}
        {% if field == 'is_deleted' and field_value is none %}
            {% set field_value = false %}
        {% endif %}

        {# Check if value is in allowed list #}
        {% if field_value not in allowed_values %}
            {% set show_action = false %}
        {% endif %}
    {% endfor %}
{% endif %}

{% if show_action %}
    {# Render the action button #}
{% endif %}
```

**Backend Logic** (`data_assembler.py:1091-1182`):
```python
def _evaluate_action_conditions(action, item_data):
    """Evaluate if action should be shown based on conditions"""
    if not hasattr(action, 'conditions') or not action.conditions:
        return True

    for field, allowed_values in action.conditions.items():
        field_value = item_data.get(field)

        # Handle None values for boolean fields
        if field == 'is_deleted' and field_value is None:
            field_value = False

        # Check if value is in allowed list
        if field_value not in allowed_values:
            return False

    return True
```

---

## Migration Guide

### Step-by-Step Migration Process

#### Step 1: Update Core Definitions (One-time)
```bash
# Already completed - no action needed
✅ core_definitions.py updated with new flags
✅ universal_list.html updated with new filter
✅ data_assembler.py updated with backward compatibility
```

#### Step 2: Update Entity Configuration

**Before (Old Approach)**:
```python
ActionDefinition(
    id="some_action",
    label="Some Action",
    show_in_toolbar=True,  # ❌ Ambiguous!
    show_in_detail=True,
    # ...
)
```

**After (New Approach)**:
```python
ActionDefinition(
    id="some_action",
    label="Some Action",
    show_in_list_toolbar=True,      # ✅ Explicit
    show_in_detail_toolbar=False,   # ✅ Clear
    # ...
)
```

#### Step 3: Test and Verify

1. **Visual Check**:
   - List page toolbar: Should show navigation + create buttons
   - List row actions: Should show View + conditional actions
   - Detail page toolbar: Should show navigation + print + dropdown
   - Detail dropdown: Should show edit/delete/workflow actions

2. **Conditional Actions**:
   - Delete should only show for unpaid/draft records
   - Approve should only show for pending records
   - Edit should only show for editable statuses

3. **Navigation**:
   - All related list buttons should navigate correctly
   - Back button should return to previous page
   - Create button should open create form

### Migration Checklist Template

```markdown
## Entity: [Entity Name]

### Actions Audit
- [ ] List Toolbar Actions: ____ identified
- [ ] List Row Actions: ____ identified
- [ ] Detail Toolbar Actions: ____ identified
- [ ] Detail Dropdown Actions: ____ identified

### Flag Updates
- [ ] All actions have explicit flags set
- [ ] Old `show_in_toolbar` flag removed
- [ ] Display types correctly set (BUTTON vs DROPDOWN_ITEM)
- [ ] Order values assigned for proper sequencing

### Conditional Logic
- [ ] All conditions use correct field names
- [ ] Allowed values match database values
- [ ] is_deleted handling includes None case

### Testing
- [ ] List page renders correctly
- [ ] Detail page renders correctly
- [ ] All navigation links work
- [ ] Conditional actions show/hide properly
- [ ] Confirmations appear when required
```

---

## Best Practices

### DO's ✅

1. **Use Explicit Flags**
   ```python
   # ✅ GOOD
   show_in_list_toolbar=True
   show_in_detail_toolbar=False
   ```

2. **Set Display Type Correctly**
   ```python
   # ✅ GOOD - Toolbar buttons
   display_type=ActionDisplayType.BUTTON

   # ✅ GOOD - Dropdown actions
   display_type=ActionDisplayType.DROPDOWN_ITEM
   ```

3. **Use Route Names (Preferred)**
   ```python
   # ✅ GOOD - Type-safe, refactor-friendly
   route_name="universal_views.universal_detail_view"
   route_params={"entity_type": "invoices", "item_id": "{invoice_id}"}
   ```

4. **Handle None in Conditions**
   ```python
   # ✅ GOOD - Handles None explicitly
   conditions={
       "is_deleted": [False, None]  # Treats None as False
   }
   ```

5. **Use Meaningful IDs**
   ```python
   # ✅ GOOD - Context-specific IDs
   id="view_row"           # List row action
   id="goto_invoices_list" # Navigation action
   id="edit_invoice"       # Dropdown action
   ```

### DON'Ts ❌

1. **Don't Use Ambiguous Flags**
   ```python
   # ❌ BAD - Which toolbar?
   show_in_toolbar=True
   ```

2. **Don't Hardcode in Templates**
   ```python
   # ❌ BAD - Hardcoded button
   <button>Export</button>

   # ✅ GOOD - Config-driven
   ActionDefinition(id="export", ...)
   ```

3. **Don't Mix Display Types**
   ```python
   # ❌ BAD - Dropdown item in toolbar
   show_in_list_toolbar=True
   display_type=ActionDisplayType.DROPDOWN_ITEM

   # ✅ GOOD
   show_in_list_toolbar=True
   display_type=ActionDisplayType.BUTTON
   ```

4. **Don't Forget Permissions**
   ```python
   # ❌ BAD - No permission check
   ActionDefinition(id="delete", ...)

   # ✅ GOOD
   ActionDefinition(id="delete", permission="invoice_delete", ...)
   ```

5. **Don't Use URL Patterns for Internal Routes**
   ```python
   # ❌ BAD - Brittle, hard to refactor
   url_pattern="/supplier/invoice/view/{invoice_id}"

   # ✅ GOOD - Type-safe, refactor-friendly
   route_name="supplier_views.view_invoice"
   route_params={"invoice_id": "{invoice_id}"}
   ```

### Naming Conventions

**Action IDs**:
- List toolbar: `goto_[entity]_list`
- List row: `[action]_row` (e.g., `view_row`, `delete_row`)
- Detail toolbar: `goto_[entity]_detail`, `print_[entity]`
- Detail dropdown: `[action]_[entity]` (e.g., `edit_invoice`, `delete_invoice`)

**Permissions**:
- View: `[entity]_view`
- Create: `[entity]_create`
- Edit: `[entity]_edit`
- Delete: `[entity]_delete`
- Approve: `[entity]_approve`
- Print: `[entity]_print`

### Order Values

**List Toolbar**: 1-10 (navigation first, create last)
```
1: Related List 1
2: Related List 2
3: Related List 3
4: Create New
```

**List Row**: 1-10 (View first, destructive last)
```
1: View
2: Approve/Workflow
3: Delete
```

**Detail Toolbar**: 1-10 (Entity list first, print last)
```
1: Entity List
2-4: Related Lists
5: Print
```

**Detail Dropdown**: 1-10 (Edit first, destructive last)
```
1: Edit
2: Delete
3-5: Workflow Actions
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Button Not Appearing

**Symptom**: Action button configured but not visible

**Diagnosis Checklist**:
1. Check the correct flag is set:
   - List toolbar: `show_in_list_toolbar=True`
   - Detail toolbar: `show_in_detail_toolbar=True`
   - List row: `show_in_list=True`

2. Check display type matches context:
   - Toolbar: `display_type=ActionDisplayType.BUTTON`
   - Dropdown: `display_type=ActionDisplayType.DROPDOWN_ITEM`

3. Check conditions are being met:
   - Add debug comments to template
   - Check actual field values in database

4. Check permission:
   - User has required permission
   - Permission name matches config

**Solution**:
```python
# ✅ CORRECT LIST TOOLBAR BUTTON
ActionDefinition(
    id="my_action",
    show_in_list=False,              # Not a row action
    show_in_list_toolbar=True,       # Show in toolbar
    show_in_detail_toolbar=False,    # Not in detail
    display_type=ActionDisplayType.BUTTON,  # Button type
    permission="my_permission"       # Check user has this
)
```

#### Issue 2: Conditional Action Always/Never Shows

**Symptom**: Delete button shows for all records or never shows

**Root Cause**: Usually payment_status field out of sync

**Solution**:
1. Run payment status sync migration:
```sql
-- Update payment_status based on actual paid amounts
UPDATE supplier_invoice si
SET payment_status = CASE
    WHEN v.balance_amount <= 0 AND v.paid_amount > 0 THEN 'paid'
    WHEN v.paid_amount > 0 AND v.balance_amount > 0 THEN 'partial'
    WHEN v.paid_amount = 0 THEN 'unpaid'
    ELSE si.payment_status
END
FROM supplier_invoices_view v
WHERE si.invoice_id = v.invoice_id;
```

2. Check condition values match database:
```python
# ✅ Check allowed values
conditions={
    "payment_status": ["unpaid"]  # Must match DB values exactly
}
```

3. Handle None values:
```python
# ✅ Include None in allowed values if field can be NULL
conditions={
    "is_deleted": [False, None]
}
```

#### Issue 3: Actions Dropdown Not Showing

**Symptom**: "Actions ▼" dropdown doesn't appear in detail view

**Diagnosis**:
1. Check if any actions have `display_type=ActionDisplayType.DROPDOWN_ITEM`
2. Check if those actions have `show_in_detail_toolbar=True`

**Solution**:
```python
# ✅ At least one dropdown item needed
ActionDefinition(
    id="edit",
    show_in_detail_toolbar=True,
    display_type=ActionDisplayType.DROPDOWN_ITEM,
    # ...
)
```

#### Issue 4: Navigation Not Working

**Symptom**: Click navigation button, nothing happens or error

**Common Causes**:
1. **Wrong route name**: Check route is registered in Flask
2. **Missing route params**: Check all required params provided
3. **Wrong entity_type**: Check spelling matches registry

**Solution**:
```python
# ✅ CORRECT
route_name="universal_views.universal_list_view",
route_params={"entity_type": "supplier_invoices"}  # Exact match

# ❌ WRONG
route_params={"entity_type": "supplier_invoice"}  # Missing 's'
```

#### Issue 5: Confirmation Not Appearing

**Symptom**: Destructive action executes without confirmation

**Solution**:
```python
# ✅ CORRECT
ActionDefinition(
    id="delete",
    confirmation_required=True,
    confirmation_message="Are you sure you want to delete this record?",
    # ...
)
```

### Debug Template

Add to `universal_list.html` for debugging conditions:

```jinja2
{# DEBUG: Log condition evaluation #}
{% if action.id == 'delete_row' %}
    <!-- DEBUG: Action {{ action.id }} -->
    {% for field, allowed_values in action.conditions.items() %}
        {% set field_value = item.get(field) %}
        <!-- DEBUG: Field {{ field }}={{ field_value }}, Allowed={{ allowed_values }} -->
        {% if field_value not in allowed_values %}
            <!-- DEBUG: HIDING because {{ field }}={{ field_value }} not in {{ allowed_values }} -->
        {% endif %}
    {% endfor %}
{% endif %}
```

Then inspect HTML source to see actual values being evaluated.

---

## Standard Module Configurations

### Supplier Module

#### Supplier Invoices
**List Toolbar**: Back, Suppliers, Purchase Orders, Supplier Payments, Create Invoice
**List Rows**: View, Delete (unpaid only)
**Detail Toolbar**: Invoices List, Suppliers, POs, Payments, Print
**Detail Dropdown**: Edit, Delete, Restore

#### Purchase Orders
**List Toolbar**: Back, Suppliers, Supplier Invoices, Supplier Payments, Create PO
**List Rows**: View, Approve (draft only), Delete (draft only)
**Detail Toolbar**: PO List, Suppliers, Invoices, Payments, Print
**Detail Dropdown**: Edit, Delete, Approve, Create Invoice from PO, Restore

#### Supplier Payments
**List Toolbar**: Back, Suppliers, Supplier Invoices, Purchase Orders, Create Payment
**List Rows**: View, Approve (pending only), Delete (draft/rejected only)
**Detail Toolbar**: Payments List, Suppliers, Invoices, POs, Print
**Detail Dropdown**: Edit, Delete, Approve, Reverse, Restore

### Patient/Billing Module

#### Patient Invoices
**List Toolbar**: Back, Patients, Patient Payments, Package Plans, Consolidated Invoices, Create Invoice
**List Rows**: View, Print, Delete (unpaid only)
**Detail Toolbar**: Invoices List, Patients, Payments, Package Plans, Consolidated Invoices, Print
**Detail Dropdown**: Edit, Delete, Void, Split Invoice

#### Patient Payments
**List Toolbar**: Back, Patients, Patient Invoices, Package Plans, Consolidated Invoices, Create Payment
**List Rows**: View, Print, Approve (pending only), Delete
**Detail Toolbar**: Payments List, Patients, Invoices, Package Plans, Consolidated Invoices, Print
**Detail Dropdown**: Edit, Delete, Approve, Reverse

#### Package Payment Plans
**List Toolbar**: Back, Patients, Patient Invoices, Patient Payments, Consolidated Invoices, Create Plan
**List Rows**: View, Print, Delete
**Detail Toolbar**: Plans List, Patients, Invoices, Payments, Consolidated Invoices, Print
**Detail Dropdown**: Edit, Delete, Discontinue

#### Consolidated Invoices
**List Toolbar**: Back, Patients, Patient Invoices, Patient Payments, Package Plans
**List Rows**: View, Print, Delete
**Detail Toolbar**: Consolidated List, Patients, Invoices, Payments, Package Plans, Print
**Detail Dropdown**: Delete

---

## Appendix

### Related Documentation
- `ACTION_BUTTON_STANDARDIZATION.md` - Implementation plan and checklist
- `Universal Engine Master Architecture.md` - Overall architecture
- `Entity Configuration Guide.md` - Entity configuration reference

### Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-15 | Initial ambiguous design | Development Team |
| 2.0 | 2025-11-16 | Explicit flag redesign, standardization | Development Team |

### Glossary

- **Action Button**: Interactive UI element triggering operations
- **List Toolbar**: Top horizontal button bar on list pages
- **Detail Toolbar**: Top horizontal button bar on detail pages
- **Row Action**: Per-record button in list table action column
- **Dropdown Action**: Action in "Actions ▼" dropdown menu
- **Conditional Action**: Button shown only when conditions met
- **Route Name**: Flask route identifier (e.g., `views.function_name`)
- **Route Params**: URL parameters passed to route
- **Entity Type**: Unique identifier for entity in registry
- **Permission**: Access control identifier for authorization

---

**Document End**

*For questions or clarifications, refer to the development team or technical lead.*
