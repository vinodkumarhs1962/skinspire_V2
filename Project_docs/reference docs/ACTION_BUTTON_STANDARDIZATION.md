# Action Button Standardization Plan
**Date:** 2025-11-16

## Objective
Standardize action buttons across all list and view screens in the Universal Engine for consistent navigation and user experience.

---

## Standard Button Layout

### **LIST VIEW Toolbar (Top of page)**
**Structure:** `[Back] [Related Lists...] [Create New]`

**Example for Supplier Invoices List:**
```
[Back] [Suppliers] [Purchase Orders] [Supplier Payments] [Create Invoice]
```

### **DETAIL/VIEW Toolbar (Top of page)**
**Structure:** `[Back] [Related Lists...] [Print] [Actions ▼]`

**Example for Supplier Invoice View:**
```
[Back] [Supplier Invoices] [Suppliers] [Purchase Orders] [Supplier Payments] [Print] [Actions ▼]
```

### **Actions Dropdown** (in detail/view)
- Edit
- Delete / Restore
- Approve / Unapprove
- Other document-specific actions

### **LIST TABLE Row Actions** (Action column)
- View (always first)
- Approve / Unapprove
- Delete / Restore
- Document-specific actions

---

## Module-Specific Definitions

### **SUPPLIER MODULE**

#### 1. **Supplier Invoices**

**List Toolbar:**
- Back
- Suppliers List
- Purchase Orders List
- Supplier Payments List
- Create Invoice

**View Toolbar:**
- Back
- Supplier Invoices List
- Suppliers List
- Purchase Orders List
- Supplier Payments List
- Print Invoice
- Actions Dropdown:
  - Edit Invoice
  - Delete Invoice
  - Approve Invoice (if pending)

**Row Actions:**
- View
- Approve (if pending)
- Delete

---

#### 2. **Purchase Orders**

**List Toolbar:**
- Back
- Suppliers List
- Supplier Invoices List
- Supplier Payments List
- Create PO

**View Toolbar:**
- Back
- Purchase Orders List
- Suppliers List
- Supplier Invoices List
- Supplier Payments List
- Print PO
- Actions Dropdown:
  - Edit PO
  - Delete PO
  - Approve PO (if draft)
  - Create Invoice from PO

**Row Actions:**
- View
- Approve (if draft)
- Delete

---

#### 3. **Supplier Payments**

**List Toolbar:**
- Back
- Suppliers List
- Supplier Invoices List
- Purchase Orders List
- Create Payment

**View Toolbar:**
- Back
- Supplier Payments List
- Suppliers List
- Supplier Invoices List
- Purchase Orders List
- Print Payment
- Actions Dropdown:
  - Edit Payment (if not approved)
  - Delete Payment
  - Approve Payment (if pending)
  - Reverse Payment (if approved)

**Row Actions:**
- View
- Approve (if pending)
- Delete

---

#### 4. **Suppliers**

**List Toolbar:**
- Back
- Supplier Invoices List
- Purchase Orders List
- Supplier Payments List
- Create Supplier

**View Toolbar:**
- Back
- Suppliers List
- Supplier Invoices List
- Purchase Orders List
- Supplier Payments List
- Print Profile
- Actions Dropdown:
  - Edit Supplier
  - Delete Supplier

**Row Actions:**
- View
- Edit
- Delete

---

### **PATIENT/BILLING MODULE**

#### 1. **Patient Invoices**

**List Toolbar:**
- Back
- Patients List
- Patient Payments List
- Package Plans List
- Consolidated Invoices List
- Create Invoice

**View Toolbar:**
- Back
- Patient Invoices List
- Patients List
- Patient Payments List
- Package Plans List
- Consolidated Invoices List
- Print Invoice
- Actions Dropdown:
  - Edit Invoice
  - Delete Invoice
  - Void Invoice
  - Split Invoice

**Row Actions:**
- View
- Print
- Delete

---

#### 2. **Patient Payments**

**List Toolbar:**
- Back
- Patients List
- Patient Invoices List
- Package Plans List
- Consolidated Invoices List
- Create Payment

**View Toolbar:**
- Back
- Patient Payments List
- Patients List
- Patient Invoices List
- Package Plans List
- Consolidated Invoices List
- Print Receipt
- Actions Dropdown:
  - Edit Payment (if not approved)
  - Delete Payment
  - Approve Payment (if pending)
  - Reverse Payment (if approved)

**Row Actions:**
- View
- Print
- Approve (if pending)
- Delete

---

#### 3. **Package Payment Plans**

**List Toolbar:**
- Back
- Patients List
- Patient Invoices List
- Patient Payments List
- Consolidated Invoices List
- Create Package Plan

**View Toolbar:**
- Back
- Package Plans List
- Patients List
- Patient Invoices List
- Patient Payments List
- Consolidated Invoices List
- Print Plan
- Actions Dropdown:
  - Edit Plan
  - Delete Plan
  - Discontinue Plan

**Row Actions:**
- View
- Print
- Delete

---

#### 4. **Consolidated Invoices**

**List Toolbar:**
- Back
- Patients List
- Patient Invoices List
- Patient Payments List
- Package Plans List

**View Toolbar:**
- Back
- Consolidated Invoices List
- Patients List
- Patient Invoices List
- Patient Payments List
- Package Plans List
- Print Consolidated Invoice
- Actions Dropdown:
  - Delete

**Row Actions:**
- View
- Print
- Delete

---

#### 5. **Patients** (Master Entity)

**List Toolbar:**
- Back
- Patient Invoices List
- Patient Payments List
- Package Plans List
- Consolidated Invoices List
- Create Patient

**View Toolbar:**
- Back
- Patients List
- Patient Invoices List
- Patient Payments List
- Package Plans List
- Consolidated Invoices List
- Print Profile
- Actions Dropdown:
  - Edit Patient
  - Delete Patient

**Row Actions:**
- View
- Edit
- Delete

---

## Configuration Flag Standards

### For **LIST PAGE** actions:

```python
# Toolbar buttons (navigation to other lists, create)
ActionDefinition(
    id="related_list_button",
    show_in_list=False,      # Not in row actions
    show_in_detail=False,    # Not in detail view
    show_in_toolbar=True,    # Show in list toolbar
    display_type=ActionDisplayType.BUTTON
)

# Row actions (per-record actions)
ActionDefinition(
    id="view_record",
    show_in_list=True,       # Show in row
    show_in_detail=False,
    show_in_toolbar=False,
    display_type=ActionDisplayType.BUTTON
)
```

### For **DETAIL/VIEW PAGE** actions:

```python
# Toolbar buttons
ActionDefinition(
    id="navigation_button",
    show_in_list=False,
    show_in_detail=True,     # Show in detail view
    show_in_toolbar=True,    # Show in toolbar
    display_type=ActionDisplayType.BUTTON
)

# Dropdown actions
ActionDefinition(
    id="edit_delete_approve",
    show_in_list=False,
    show_in_detail=True,
    show_in_toolbar=True,
    display_type=ActionDisplayType.DROPDOWN_ITEM
)
```

---

## Implementation Order

1. ✅ Document standardization plan
2. ⏳ Update Supplier Invoice config
3. ⏳ Update Purchase Order config
4. ⏳ Update Supplier Payment config
5. ⏳ Update Supplier config
6. ⏳ Update Patient Invoice config
7. ⏳ Update Patient Payment config
8. ⏳ Update Package Plan config
9. ⏳ Update Consolidated Invoice config
10. ⏳ Verify templates (no hardcoded changes needed)
11. ⏳ Test all navigation flows

---

## Hardcoded Elements to Remove

### Already Removed:
- ✅ Hardcoded Export button in universal_list.html (removed)

### To Verify:
- Check universal_view.html for any hardcoded action buttons
- Check if any custom templates override universal engine actions

---

## Notes

- All navigation uses Universal Engine routes (`universal_views.*`)
- Print functionality uses `universal_document_view` route
- Actions are permission-gated via the `permission` field
- Order matters: use `order` field to sequence buttons left-to-right
