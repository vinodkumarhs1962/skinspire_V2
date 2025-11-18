# Patient Invoice Creation & Display Fixes - January 9, 2025

## Issues Reported

Testing patient invoice creation with multiple line items that get split into four invoices revealed the following issues:

### Stock Validation Issues
1. ✅ **FIXED**: Insufficient stock error for duplicate batch numbers

### Form Data Preservation
2. ✅ **FIXED**: Line items vanish from create invoice screen after validation errors

### UI/UX Improvements
3. ⏳ **PENDING**: Patient search needs enhancement (replicate features from consolidated invoice list - larger feature)
4. ✅ **FIXED**: N/A displayed below batch no. and expiry date fields for services/packages

### Invoice Creation & Navigation
5. ✅ **FIXED**: 4th invoice URL building error for `consolidated_invoice_detail_view`
6. ✅ **FIXED**: Service/package invoice missing "Back to Consolidated Invoice" button

### Invoice List Display Issues
7. ✅ **FIXED**: Patient name blank in invoice list (parent row)
8. ✅ **FIXED**: Clicking on line item navigates to correct invoice detail view
9. ✅ **FIXED**: Non-GST invoice line items now show batch no. and expiry date
10. ✅ **FIXED**: GST invoice line items now show GST%
11. ✅ **FIXED**: Split invoice count column removed from consolidated invoice detail table

## Summary: **10 of 11 issues FIXED** ✅

---

## Detailed Fixes

### 1. Stock Validation for Duplicate Batch Numbers ✅

**Problem**: When multiple line items used the same batch number, validation checked each line independently, causing false "insufficient stock" errors.

**Example**:
- Line 1: Batch 1234561, Qty 1, Available: 1 ✓
- Line 2: Batch 1234561, Qty 2, Available: 1 ✗ (Should check total: 3 > 1)

**Solution**: Modified `app/services/billing_service.py` (lines 650-695)
- **Changed**: Aggregated quantities for same medicine+batch combination before validation
- **Logic**:
  1. Group line items by (medicine_id, batch) tuple
  2. Sum quantities for each group
  3. Validate total quantity against available stock
- **Benefits**:
  - Accurate stock validation
  - Clear error messages showing total requested vs available
  - Supports multiple line items with same batch

**Code Location**: `app/services/billing_service.py:650-695` in `_create_single_invoice_with_category()`

---

### 2. Preserve Line Items After Validation Errors ✅

**Problem**: When invoice creation failed (inventory errors, validation errors), all entered line items were lost, forcing users to re-enter everything.

**Solution**: Two-part fix:

#### Backend (app/views/billing_views.py)
- **Lines 497-544**: Enhanced exception handling to preserve line items for ALL errors (not just inventory errors)
- **Preserved Data**:
  - Item type, ID, name
  - Batch, expiry date
  - Quantity, unit price, discount
  - GST rate
  - Consultation flag

#### Frontend (app/templates/billing/create_invoice.html)
- **Lines 830-927**: Added JavaScript restoration logic
- **Process**:
  1. Backend passes `preserved_line_items` array to template
  2. On page load, JavaScript detects preserved items
  3. Creates new rows using InvoiceItemComponent
  4. Populates all fields with preserved values
  5. Recalculates totals

**Benefits**:
- No data loss on validation errors
- Better user experience
- Preserves batch selections and all input
- Automatic total recalculation

**Code Locations**:
- Backend: `app/views/billing_views.py:497-544`
- Frontend: `app/templates/billing/create_invoice.html:830-927`

---

### 3. Remove N/A Display for Service/Package Items ✅

**Problem**: Batch and Expiry fields showed "N/A" placeholder text for services and packages, cluttering the UI.

**Solution**: Removed placeholder spans from line item template
- **File**: `app/templates/billing/create_invoice.html`
- **Lines 731-743**: Removed `<span class="non-medicine-placeholder">N/A</span>` from both batch and expiry fields
- **Result**: Clean, empty cells for non-medicine items

**Code Location**: `app/templates/billing/create_invoice.html:731-743`

---

### 4. Fix URL Building Error for Consolidated Invoice Detail View ✅

**Problem**: 4th invoice (prescription) gave error:
```
Error creating invoice: Could not build url for endpoint
'universal_views.consolidated_invoice_detail_view' with values ['invoice_id'].
Did you forget to specify values ['parent_invoice_id']?
```

**Root Cause**: Mismatch between action definition and route parameter names
- **Action Used**: `url_pattern="/universal/consolidated_invoice_detail/{parent_transaction_id}"`
- **Route Expected**: `@universal_bp.route('/consolidated_invoice_detail/<parent_invoice_id>')`

**Solution**: Updated "Back to Parent Invoice" action definition
- **File**: `app/config/modules/patient_invoice_config.py`
- **Lines 1117-1132**: Changed from url_pattern to route_name with correct parameter mapping
- **Fixed Code**:
```python
ActionDefinition(
    id="back_to_consolidated",
    label="Back to Parent Invoice",
    icon="fas fa-layer-group",
    button_type=ButtonType.SECONDARY,
    route_name="universal_views.consolidated_invoice_detail_view",
    route_params={'parent_invoice_id': '{parent_transaction_id}'},  # CORRECTED
    ...
)
```

**Code Location**: `app/config/modules/patient_invoice_config.py:1117-1132`

---

### 5. Remove Split Invoice Count Column ✅

**Problem**: Split invoice count column appeared in consolidated invoice detail table, but was not useful since all displayed invoices are already children.

**Solution**: Hidden field from list view
- **File**: `app/config/modules/patient_invoice_config.py`
- **Line 569**: Changed `show_in_list=True` to `show_in_list=False`
- **Result**: Cleaner table display in consolidated invoice detail view

**Code Location**: `app/config/modules/patient_invoice_config.py:565-579`

---

---

### 7. Fix Blank Patient Name in Invoice List ✅

**Problem**: Patient name column was blank in the parent invoice row of consolidated invoice detail view.

**Root Cause**: In `universal_views.py:1178-1189`, the manually constructed parent invoice dict didn't include `patient_name` field, even though child invoices (from the database view) had it.

**Solution**: Added missing fields to parent invoice dict
- **File**: `app/views/universal_views.py`
- **Lines 1177-1194**: Added patient_name, patient_mrn, is_gst_invoice, and branch_name fields
- **Result**: Parent invoice row now displays complete information

**Code Location**: `app/views/universal_views.py:1177-1194`

---

### 8. Fix Line Item Click Navigation ✅

**Problem**: Row click handler used wrong URL pattern (`/view/` instead of `/detail/`) and didn't prevent clicks on action buttons.

**Solution**: Fixed `handleRowClick` JavaScript function
- **File**: `app/templates/engine/universal_list.html`
- **Lines 969-1008**: Updated function to:
  - Use correct Universal Engine route: `/universal/{entity_type}/detail/{item_id}`
  - Prevent navigation when clicking on buttons/links
  - Handle special case for consolidated_invoice_detail (navigate to patient_invoices)
- **Result**: Rows now navigate to correct detail views, buttons work independently

**Code Location**: `app/templates/engine/universal_list.html:969-1008`

---

### 9. Display Batch/Expiry in Non-GST Invoice Line Items ✅

**Problem**: Non-GST medicine line items (OTC, Product, Consumable) didn't show batch and expiry columns because `has_medicine_items` check only looked for 'Medicine' and 'Prescription' types.

**Solution**: Expanded medicine type check
- **File**: `app/services/patient_invoice_service.py`
- **Lines 316-326**: Updated `has_medicine_items` logic to include:
  - Medicine
  - Prescription
  - OTC (Non-GST medicines)
  - Product (GST medicines)
  - Consumable (GST consumables)
- **Result**: Batch and expiry columns now display for all medicine types

**Code Location**: `app/services/patient_invoice_service.py:316-326`

---

### 10. Display GST% in GST Invoice Line Items ✅

**Problem**: Template expected `gst_rate` field but service only provided individual rate components (cgst_rate, sgst_rate, igst_rate).

**Solution**: Added calculated `gst_rate` field
- **File**: `app/services/patient_invoice_service.py`
- **Lines 257-280**: Added GST rate calculation:
  - `gst_rate = igst_rate` (for interstate) OR
  - `gst_rate = cgst_rate + sgst_rate` (for intrastate)
- **Result**: GST% column now displays total tax percentage

**Code Location**: `app/services/patient_invoice_service.py:257-280`

---

### 3. Enhanced Patient Search (Feature Request) ⏳

**Scope**: Larger enhancement requiring new development
- Advanced patient search with filters
- Enhanced autocomplete functionality
- May require new API endpoints

**Status**: **Deferred** - Nice-to-have, not blocking core functionality
**Priority**: Medium

---

## Testing Checklist ✅

### All Fixes - Please Test

- [ ] **Stock Validation**: Create invoice with 2 line items using same batch number
  - Example: Batch A, Qty 1 + Batch A, Qty 2 = Total 3 checked against stock
  - Expected: ✅ Aggregated quantity validation

- [ ] **Form Preservation**: Create invoice that fails validation (e.g., insufficient stock)
  - Expected: ✅ Error displayed, all line items preserved
  - Try: Re-submit after correcting error

- [ ] **N/A Removal**: Add service or package line item
  - Expected: ✅ Batch and expiry columns are empty (no "N/A" text)

- [ ] **URL Fix**: Create invoice that splits into 4 invoices
  - Expected: ✅ All 4 invoices created successfully without URL errors

- [ ] **Back Button**: Open any child invoice
  - Click: "Back to Parent Invoice" button
  - Expected: ✅ Navigate to consolidated invoice detail view

- [ ] **Patient Name**: Open consolidated invoice detail view
  - Expected: ✅ Patient name displays in ALL rows (parent + children)

- [ ] **Row Click**: Click on invoice row in consolidated invoice detail
  - Expected: ✅ Navigates to individual invoice detail view (not legacy screen)
  - Test: Click on action button should still work independently

- [ ] **Batch/Expiry Display**: Open Non-GST invoice (OTC medicines)
  - Check line items table
  - Expected: ✅ Batch number and expiry date columns are visible and populated

- [ ] **GST% Display**: Open GST invoice (Product/Consumable)
  - Check line items table
  - Expected: ✅ GST% column displays total tax percentage (e.g., 18%, 12%)

- [ ] **Column Removal**: Open consolidated invoice detail view
  - Expected: ✅ Split invoice count column is NOT visible in table

---

## Files Modified

### Backend Services
1. `app/services/billing_service.py`
   - Lines 650-695: Stock validation with batch quantity aggregation

2. `app/services/patient_invoice_service.py`
   - Lines 257-280: Added gst_rate calculation
   - Lines 316-326: Expanded has_medicine_items check

### Views
3. `app/views/billing_views.py`
   - Lines 497-544: Form data preservation for all errors

4. `app/views/universal_views.py`
   - Lines 1177-1194: Added patient_name and fields to parent invoice dict

### Templates
5. `app/templates/billing/create_invoice.html`
   - Lines 731-743: Removed N/A placeholder spans
   - Lines 830-927: JavaScript restoration logic for preserved line items

6. `app/templates/engine/universal_list.html`
   - Lines 969-1008: Fixed handleRowClick to use correct Universal Engine routes

### Configuration
7. `app/config/modules/patient_invoice_config.py`
   - Lines 1117-1132: Fixed "Back to Parent Invoice" action route parameters
   - Line 569: Hidden split_invoice_count from list view

---

## Next Steps

1. **Test All Fixes**: Run through comprehensive testing checklist above
2. **Patient Search Enhancement**: Schedule as separate feature (optional, non-blocking)

---

## Notes

- All fixes follow Universal Engine architecture principles
- No breaking changes to existing functionality
- Backward compatible with existing invoices
- Code properly documented with comments

---

**Generated**: January 9, 2025
**Developer**: Claude Code
**Status**: ✅ **10 of 11 issues FIXED** (1 feature request deferred)
**Files Modified**: 7 files across services, views, templates, and configuration
