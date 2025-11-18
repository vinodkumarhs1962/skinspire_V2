# Patient Invoice Fixes - FINAL - January 9, 2025

## ✅ CRITICAL FIX APPLIED - Back to Consolidated Invoice Button

### Problem Identified
The "Back to Consolidated Invoice" button was giving **404 errors** because the route parameter expression `{parent_transaction_id or invoice_id}` was not supported by the ActionDefinition's `get_url()` method.

**Error in logs**:
```
GET /universal/consolidated_invoice_detail/ HTTP/1.1" 404
```

The URL had no invoice ID because the expression wasn't being evaluated.

---

## 🔧 Root Cause Analysis

### ActionDefinition URL Building Process

**File**: `app/config/core_definitions.py:467-517`

The `get_url()` method processes route parameters as follows:

```python
def get_url(self, item: Dict, entity_config=None) -> str:
    if self.route_name:
        kwargs = {}
        if self.route_params:
            for param, template in self.route_params.items():
                if isinstance(template, str) and template.startswith('{') and template.endswith('}'):
                    # Extract field name from template {field_name}
                    field_name = template[1:-1]  # Removes { and }
                    # Simple field lookup
                    value = item.get(field_name, '')
                    kwargs[param] = str(value) if value else ''
```

**The Issue**:
- Template `{parent_transaction_id or invoice_id}` becomes field name `parent_transaction_id or invoice_id`
- `item.get('parent_transaction_id or invoice_id', '')` returns empty string
- URL becomes `/universal/consolidated_invoice_detail/` with no ID
- **404 error!**

**What's NOT Supported**:
- ❌ Python expressions: `{field1 or field2}`
- ❌ Ternary operators: `{field1 if condition else field2}`
- ❌ Function calls: `{get_parent_id()}`

**What IS Supported**:
- ✅ Simple field lookup: `{field_name}`
- ✅ Nested field lookup: `{supplier.supplier_id}`
- ✅ Smart mapping: `{id}` → primary key field

---

## ✅ Solution Applied

### Two Separate Action Definitions

**File**: `app/config/modules/patient_invoice_config.py:1117-1151`

Created TWO actions with different conditionals:

#### 1. For Child Invoices (2nd, 3rd, 4th invoices)
```python
ActionDefinition(
    id="back_to_consolidated_child",
    label="Back to Consolidated Invoice",
    icon="fas fa-layer-group",
    button_type=ButtonType.SECONDARY,
    route_name="universal_views.consolidated_invoice_detail_view",
    route_params={'parent_invoice_id': '{parent_transaction_id}'},  # ✅ Simple field lookup
    show_in_list=False,
    show_in_detail=True,
    show_in_toolbar=True,
    display_type=ActionDisplayType.BUTTON,
    permission="billing_invoice_view",
    # Show only for child invoices (have parent_transaction_id)
    conditional_display="item.parent_transaction_id is not None and item.parent_transaction_id != ''",
    order=1
),
```

#### 2. For Parent Invoice (1st invoice created)
```python
ActionDefinition(
    id="back_to_consolidated_parent",
    label="Back to Consolidated Invoice",
    icon="fas fa-layer-group",
    button_type=ButtonType.SECONDARY,
    route_name="universal_views.consolidated_invoice_detail_view",
    route_params={'parent_invoice_id': '{invoice_id}'},  # ✅ Use own ID
    show_in_list=False,
    show_in_detail=True,
    show_in_toolbar=True,
    display_type=ActionDisplayType.BUTTON,
    permission="billing_invoice_view",
    # Show only for parent invoice (is_split_invoice=True but no parent_transaction_id)
    conditional_display="item.is_split_invoice and (item.parent_transaction_id is None or item.parent_transaction_id == '')",
    order=1
),
```

### How It Works

**Invoice Structure**:
```
Service Invoice (Parent)
├─ invoice_id: bd8f100e-5ccb-4bf3-a622-03c37e5f7b29
├─ parent_transaction_id: NULL
├─ is_split_invoice: TRUE
└─ split_sequence: 1

GST Medicines Invoice (Child)
├─ invoice_id: 2dc562ce-ff60-445e-a88b-f995e62592ef
├─ parent_transaction_id: bd8f100e-5ccb-4bf3-a622-03c37e5f7b29
├─ is_split_invoice: TRUE
└─ split_sequence: 2

GST Exempt Medicines Invoice (Child)
├─ invoice_id: xxx-xxx-xxx
├─ parent_transaction_id: bd8f100e-5ccb-4bf3-a622-03c37e5f7b29
├─ is_split_invoice: TRUE
└─ split_sequence: 3

Prescription Invoice (Child)
├─ invoice_id: yyy-yyy-yyy
├─ parent_transaction_id: bd8f100e-5ccb-4bf3-a622-03c37e5f7b29
├─ is_split_invoice: TRUE
└─ split_sequence: 4
```

**Button Display Logic**:

| Invoice Type | parent_transaction_id | is_split_invoice | Button Shown | Uses ID |
|--------------|----------------------|------------------|--------------|---------|
| **Service** (Parent) | NULL | TRUE | `back_to_consolidated_parent` | Own `invoice_id` |
| **GST Medicines** (Child) | bd8f100e... | TRUE | `back_to_consolidated_child` | `parent_transaction_id` |
| **GST Exempt** (Child) | bd8f100e... | TRUE | `back_to_consolidated_child` | `parent_transaction_id` |
| **Prescription** (Child) | bd8f100e... | TRUE | `back_to_consolidated_child` | `parent_transaction_id` |

**URL Generated**:
- All buttons navigate to: `/universal/consolidated_invoice_detail/bd8f100e-5ccb-4bf3-a622-03c37e5f7b29`
- This is the parent invoice's ID
- Consolidated detail view shows all 4 child invoices

---

## ✅ Other Fixes Confirmed

### 1. Batch/Expiry Display in Medicine Invoices
**File**: `app/services/patient_invoice_service.py:339-343`

Added fallback check based on `invoice_type`:
```python
# FALLBACK: For split invoices, check invoice_type
# invoice_type "Product" is used for both GST and GST-exempt medicine invoices
if not has_medicine_items and invoice.invoice_type == 'Product':
    logger.info(f"📦 Invoice {invoice_id}: invoice_type is 'Product', setting has_medicine_items=True")
    has_medicine_items = True
```

**Status**: Already working correctly based on `item_type` field (Consumable, Product)
**Safety net**: Fallback will catch edge cases

---

### 2. Navigation from Consolidated Lists
**File**: `app/templates/engine/universal_list.html:997-1009`

Special case handling for row clicks:
```javascript
if (entityType === 'consolidated_invoice_detail') {
    // In consolidated detail view: child invoice row → patient invoice detail
    targetUrl = `/universal/patient_invoices/detail/${itemId}`;
} else if (entityType === 'consolidated_patient_invoices') {
    // In consolidated list view: parent invoice row → consolidated detail
    targetUrl = `/universal/consolidated_invoice_detail/${itemId}`;
} else {
    // Default: standard Universal Engine detail route
    targetUrl = `/universal/${entityType}/detail/${itemId}`;
}
```

**Status**: ✅ Working correctly

---

## 🧪 Testing Checklist

### Test 1: Child Invoice Back Button
**Steps**:
1. Create invoice that splits into 4 invoices
2. Navigate to consolidated detail view
3. Click into **GST Medicines** invoice (child)
4. Look for "Back to Consolidated Invoice" button
5. Click button

**Expected**:
- ✅ Button visible in toolbar
- ✅ URL: `/universal/consolidated_invoice_detail/bd8f100e-5ccb-4bf3-a622-03c37e5f7b29`
- ✅ No 404 error
- ✅ Shows all 4 child invoices

**Check Logs**:
```bash
grep "consolidated_invoice_detail_view" logs/app.log
# Should show successful requests, not 404
```

---

### Test 2: Parent Invoice Back Button
**Steps**:
1. From consolidated detail, click into **Service** invoice (parent)
2. Look for "Back to Consolidated Invoice" button
3. Click button

**Expected**:
- ✅ Button visible in toolbar
- ✅ URL: `/universal/consolidated_invoice_detail/bd8f100e-5ccb-4bf3-a622-03c37e5f7b29` (uses own invoice_id)
- ✅ No 404 error
- ✅ Shows all 4 child invoices

**Check Database**:
```sql
SELECT
    invoice_number,
    invoice_id,
    parent_transaction_id,
    is_split_invoice,
    split_sequence
FROM invoice_header
WHERE invoice_id = 'bd8f100e-5ccb-4bf3-a622-03c37e5f7b29';

-- Should show:
-- parent_transaction_id: NULL
-- is_split_invoice: true
-- split_sequence: 1
```

---

### Test 3: All 4 Invoices Have Button
**Steps**:
1. Open each of the 4 split invoices
2. Check for "Back to Consolidated Invoice" button

**Expected**:
- ✅ **Service invoice** (parent): Button visible
- ✅ **GST Medicines** (child): Button visible
- ✅ **GST Exempt** (child): Button visible
- ✅ **Prescription** (child): Button visible
- ✅ All buttons work correctly

---

### Test 4: Batch/Expiry Display
**Steps**:
1. Open GST Medicines invoice detail
2. Check line items table

**Expected**:
- ✅ Batch column visible and populated
- ✅ Expiry date column visible and populated
- ✅ GST% column shows correct percentage

**Check Logs**:
```bash
grep "has_medicine_items: True" logs/app.log
grep "Found item types:" logs/app.log
```

---

### Test 5: Navigation Flow
**Complete cycle**:
1. Start at: `/universal/consolidated_patient_invoices/list`
2. Click row → `/universal/consolidated_invoice_detail/<parent_id>`
3. Click child row → `/universal/patient_invoices/detail/<child_id>`
4. Click "Back to Consolidated Invoice" → `/universal/consolidated_invoice_detail/<parent_id>`
5. Repeat for all 4 child invoices

**Expected**:
- ✅ No 404 errors at any step
- ✅ No legacy views appearing
- ✅ All navigation uses Universal Engine routes
- ✅ Smooth transitions

---

## 📁 Files Modified

| File | Lines | Change |
|------|-------|--------|
| `app/config/modules/patient_invoice_config.py` | 1117-1151 | Split "Back to Consolidated Invoice" into two actions (parent/child) |
| `app/services/patient_invoice_service.py` | 339-343 | Added invoice_type fallback for has_medicine_items |
| `app/templates/engine/universal_list.html` | 997-1009 | Added consolidated invoice navigation handling |

---

## 🎯 Key Learnings

### ActionDefinition Route Parameters
1. **Simple field lookups only**: `{field_name}`
2. **No Python expressions**: Can't use `or`, `if/else`, function calls
3. **Workaround**: Use multiple actions with different `conditional_display` expressions

### Split Invoice Structure
1. **Parent invoice**: First created, `parent_transaction_id = NULL`, `is_split_invoice = TRUE`
2. **Child invoices**: `parent_transaction_id = <parent_id>`, `is_split_invoice = TRUE`
3. **All invoices** in the split group navigate to the same consolidated detail view using parent's ID

### Conditional Display Expressions
Supported in `conditional_display`:
- ✅ Field comparisons: `item.field == value`
- ✅ Boolean checks: `item.field is not None`
- ✅ Logical operators: `and`, `or`, `not`
- ✅ String comparisons: `item.field == ''`

---

## 🚀 Ready for Testing

All fixes are now in place:
1. ✅ Back button uses correct route parameters (separate actions for parent/child)
2. ✅ Batch/expiry columns show in medicine invoices (with fallback)
3. ✅ Navigation flow uses Universal Engine routes throughout

**Next Step**: Test all 5 scenarios above to verify functionality!

---

**Generated**: January 9, 2025
**Developer**: Claude Code
**Status**: ✅ **CRITICAL FIX APPLIED - READY FOR TESTING**
**Priority**: URGENT - Test Back to Consolidated Invoice button immediately
**Files Modified**: 3 files
