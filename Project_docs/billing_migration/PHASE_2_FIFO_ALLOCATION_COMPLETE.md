# Phase 2 Complete: FIFO Allocation Modal

**Date Completed**: 2025-01-06
**Status**: ✅ Complete - Ready for Testing

## Overview

Phase 2 implements the FIFO (First In First Out) batch allocation modal that automatically allocates medicine batches based on expiry dates when users enter quantities in the invoice create form.

## Completed Components

### 1. ✅ FIFO Allocation Modal Component
**File**: `app/static/js/components/fifo_allocation_modal.js`

**Features**:
- Beautiful Tailwind CSS modal with dark mode support
- Displays medicine name and required quantity
- Shows FIFO-calculated batch allocation in table format
- Allows manual override of quantities per batch
- Remove batch functionality
- Real-time quantity and amount calculations
- Warning indicators for insufficient/excess stock
- Accept/Cancel workflow
- Responsive design

**Key Methods**:
```javascript
// Show modal for medicine allocation
fifoModal.show(medicine, quantity, onConfirmCallback)

// Batch table with editable quantities
// Real-time validation and warnings
// Confirm allocation callback
```

### 2. ✅ FIFO Allocation API Endpoint
**File**: `app/views/billing_views.py`
**Route**: `/invoice/web_api/medicine/<medicine_id>/fifo-allocation?quantity=<qty>`

**Features**:
- Uses existing `get_batch_selection_for_invoice()` service from `inventory_service.py`
- Returns FIFO-sorted batch allocations
- Includes all necessary fields: batch, expiry, quantity, prices, GST rates, HSN code
- Error handling for invalid medicine/quantity
- Calculates shortage if insufficient stock

**Response Format**:
```json
{
  "success": true,
  "batches": [
    {
      "batch": "BATCH001",
      "expiry_date": "2026-01-31",
      "quantity": 50,
      "available_stock": 100,
      "unit_price": 10.50,
      "sale_price": 12.00,
      "mrp": 15.00,
      "gst_rate": 12.0,
      "cgst": 6.0,
      "sgst": 6.0,
      "igst": 0,
      "hsn_code": "30049099"
    }
  ],
  "total_allocated": 50,
  "quantity_requested": 50,
  "is_sufficient": true,
  "shortage": 0
}
```

### 3. ✅ Enter Key Integration
**File**: `app/static/js/components/invoice_item.js`

**New Methods**:
- `initFIFOAllocation(row)` - Attaches Enter key listener to quantity field
- `applyFIFOAllocation(row, batches)` - Applies confirmed allocation to line item
- `showBatchDetails(batches)` - Shows detailed batch breakdown

**Workflow**:
1. User selects medicine type (OTC, Prescription, Product, Consumable)
2. User selects specific medicine from dropdown
3. User enters quantity in quantity field
4. **User presses Enter key** → FIFO modal opens
5. Modal shows automatic batch allocation
6. User can:
   - Accept allocation as-is
   - Edit quantities per batch
   - Remove batches
   - Cancel
7. On confirm:
   - Single batch: Populates batch dropdown, expiry, price, GST
   - Multiple batches: Shows "Multiple Batches (X)" indicator with weighted averages

**Visual Indicators for Multiple Batches**:
```html
<div class="batch-indicator">
  <i class="fas fa-layer-group"></i>
  <strong>3 batches allocated</strong>
  <button>View Details</button>
</div>
```

### 4. ✅ Template Integration
**File**: `app/templates/billing/create_invoice.html`

**Changes**:
- Added `<script src="fifo_allocation_modal.js">` before invoice_item.js
- Modal renders on page load
- Available globally via `window.fifoModal`

### 5. ✅ Form Submission Enhancement
**File**: `app/static/js/pages/invoice.js`

**Changes**:
- `prepareLineItemsForSubmission()` now includes `batch_allocations` field
- Multi-batch data stored as JSON string in `row.dataset.batchAllocations`
- Submitted as hidden field: `line_items-0-batch_allocations`

**Form Data Example**:
```
line_items-0-item_type: OTC
line_items-0-item_id: <uuid>
line_items-0-item_name: Paracetamol 500mg
line_items-0-quantity: 100
line_items-0-unit_price: 10.50
line_items-0-batch: MULTIPLE
line_items-0-batch_allocations: [{"batch":"BATCH001","quantity":50,...},{"batch":"BATCH002","quantity":50,...}]
```

---

## User Workflow

### Single Batch Scenario

1. **Select Medicine**
   - Type: OTC Medicine
   - Item: Paracetamol 500mg

2. **Enter Quantity**
   - Quantity: 50
   - Press **Enter**

3. **FIFO Modal Opens**
   ```
   Medicine: Paracetamol 500mg
   Quantity Required: 50

   Batch       Expiry      Stock  Allocated  Price   Amount
   BATCH001    2026-01-31  100    50         ₹10.50  ₹525.00
   ```

4. **User Accepts**
   - Line item populated:
     - Batch: BATCH001
     - Expiry: 2026-01-31
     - Unit Price: ₹10.50
     - GST Rate: 12%

### Multiple Batch Scenario

1. **Select Medicine**
   - Type: OTC Medicine
   - Item: Paracetamol 500mg

2. **Enter Quantity**
   - Quantity: 150
   - Press **Enter**

3. **FIFO Modal Opens**
   ```
   Medicine: Paracetamol 500mg
   Quantity Required: 150

   Batch       Expiry      Stock  Allocated  Price   Amount
   BATCH001    2026-01-31  100    100        ₹10.50  ₹1050.00
   BATCH002    2026-02-28  80     50         ₹11.00  ₹550.00
   ───────────────────────────────────────────────────────────
   Total:                         150                ₹1600.00
   ```

4. **User Can Edit**
   - Change BATCH001 quantity to 80
   - Change BATCH002 quantity to 70
   - Or remove a batch entirely

5. **User Accepts**
   - Line item shows:
     - Batch: Multiple Batches (2)
     - Expiry: 2026-01-31 (earliest)
     - Unit Price: ₹10.67 (weighted average)
     - GST Rate: 12% (weighted average)
   - Blue indicator: "2 batches allocated [View Details]"

### Insufficient Stock Scenario

1. **Enter Quantity**
   - Quantity: 200
   - Available: 150

2. **FIFO Modal Shows Warning**
   ```
   ⚠️ Warning: Insufficient stock!
   Required: 200, Available: 150. Short by 50 units.

   Batch       Expiry      Stock  Allocated  Price   Amount
   BATCH001    2026-01-31  100    100        ₹10.50  ₹1050.00
   BATCH002    2026-02-28  50     50         ₹11.00  ₹550.00
   ```

3. **Button Changes**
   - "Accept (Partial)" instead of "Accept Allocation"
   - User can accept partial allocation or cancel

---

## Technical Implementation

### FIFO Logic

The existing `get_batch_selection_for_invoice()` in `inventory_service.py` handles FIFO:

```python
def get_batch_selection_for_invoice(hospital_id, medicine_id, quantity_needed, session):
    # Get batches ordered by expiry date (FIFO)
    # Allocate quantity across batches
    # Return list of {batch, expiry_date, quantity, unit_price, sale_price}
```

**Allocation Strategy**:
1. Query all batches with `current_stock > 0`
2. Order by `expiry` date ASC (earliest expiry first)
3. Allocate quantity sequentially:
   - If batch stock >= remaining qty → Take all from this batch, done
   - If batch stock < remaining qty → Take all from this batch, continue to next

### Modal State Management

```javascript
class FIFOAllocationModal {
  currentMedicine: Object  // {id, name, type}
  currentQuantity: Number
  batchAllocations: Array  // Current batch allocations
  onConfirmCallback: Function  // Called when user confirms
}
```

### Data Flow

```
1. User presses Enter on quantity field
   ↓
2. invoice_item.js → fifoModal.show(medicine, qty, callback)
   ↓
3. Modal → API GET /fifo-allocation?quantity=X
   ↓
4. inventory_service.get_batch_selection_for_invoice()
   ↓
5. Modal displays batches in table
   ↓
6. User edits/confirms
   ↓
7. Callback → invoice_item.js → applyFIFOAllocation(row, batches)
   ↓
8. Row updated with batch data
   ↓
9. On submit → invoice.js → prepareLineItemsForSubmission()
   ↓
10. batch_allocations JSON sent to backend
```

---

## Files Modified

### New Files
- ✅ `app/static/js/components/fifo_allocation_modal.js` (400 lines)

### Modified Files
- ✅ `app/views/billing_views.py` (+100 lines) - New FIFO API endpoint
- ✅ `app/templates/billing/create_invoice.html` (+1 line) - Script include
- ✅ `app/static/js/components/invoice_item.js` (+180 lines) - FIFO integration
- ✅ `app/static/js/pages/invoice.js` (+5 lines) - Batch allocations field

---

## Testing Checklist

### Functional Tests

- [ ] **Modal Appearance**
  - [ ] Press Enter on quantity field for OTC medicine
  - [ ] Modal opens with medicine name and quantity
  - [ ] Batch table displays correctly
  - [ ] Close buttons work (X, Cancel, ESC key, outside click)

- [ ] **Single Batch Allocation**
  - [ ] Medicine with sufficient stock in one batch
  - [ ] Allocation fills automatically
  - [ ] Accept button works
  - [ ] Line item populates with batch details
  - [ ] Expiry, price, GST all correct

- [ ] **Multiple Batch Allocation**
  - [ ] Medicine requiring multiple batches
  - [ ] All batches shown in FIFO order (earliest expiry first)
  - [ ] Total quantity matches request
  - [ ] Weighted averages calculated correctly
  - [ ] "Multiple Batches (X)" indicator appears
  - [ ] View Details button shows batch breakdown

- [ ] **Manual Override**
  - [ ] Edit quantity in batch table
  - [ ] Total updates in real-time
  - [ ] Remove batch button works
  - [ ] Warning appears if total != requested
  - [ ] Can still accept modified allocation

- [ ] **Insufficient Stock**
  - [ ] Warning message displays
  - [ ] Shows shortage amount
  - [ ] Button changes to "Accept (Partial)"
  - [ ] Can accept partial allocation

- [ ] **Error Handling**
  - [ ] Invalid medicine ID → Error message
  - [ ] No batches available → Error message
  - [ ] Network error → Error message
  - [ ] Zero quantity → Validation alert

- [ ] **Form Submission**
  - [ ] Single batch: batch field populated
  - [ ] Multiple batches: batch_allocations JSON included
  - [ ] Form data correct on backend
  - [ ] Invoice created successfully

### UI/UX Tests

- [ ] Dark mode compatibility
- [ ] Responsive on different screen sizes
- [ ] Loading spinner appears while fetching
- [ ] Smooth animations
- [ ] Keyboard navigation works
- [ ] Focus management correct

### Integration Tests

- [ ] Works with all medicine types (OTC, Prescription, Product, Consumable)
- [ ] Does NOT trigger for Service/Package types
- [ ] Multiple line items work independently
- [ ] Totals calculate correctly after allocation
- [ ] GST calculations accurate

---

## Known Limitations & Future Enhancements

### Current Limitations
1. **Backend Invoice Splitting**: Not yet implemented
   - Multiple batches submitted but not auto-split into separate invoices
   - Backend needs to handle `batch_allocations` JSON
   - Will be implemented in Phase 3

2. **Batch Details Modal**: Uses alert() for now
   - Could be enhanced with a proper modal

3. **Inventory Deduction**: Not yet implemented
   - Need to update inventory on invoice creation
   - Need to handle multi-batch deduction

### Future Enhancements (Phase 3)
1. **Backend Invoice Splitting Service**
   - Parse `batch_allocations` JSON
   - Create separate invoice for each batch
   - Link via `parent_transaction_id`
   - Set `is_split_invoice=True`, `split_reason='BATCH_ALLOCATION'`

2. **Consolidated Invoice View**
   - Show parent invoice with all child invoices
   - Display batch breakdown
   - Combined totals and payment tracking

3. **GST-Based Splitting**
   - Further split by GST vs non-GST items
   - Split by interstate vs intrastate

4. **Prescription Consolidation**
   - Combine prescription medicines into single invoice
   - Separate from OTC/products

---

## API Documentation

### GET `/invoice/web_api/medicine/<medicine_id>/fifo-allocation`

**Parameters**:
- `medicine_id` (UUID, required): Medicine UUID
- `quantity` (number, required): Quantity needed

**Response** (200 OK):
```json
{
  "success": true,
  "batches": [...],
  "total_allocated": 100,
  "quantity_requested": 100,
  "is_sufficient": true,
  "shortage": 0
}
```

**Error Response** (400/404/500):
```json
{
  "success": false,
  "message": "Error message here"
}
```

---

## Next Steps: Phase 3 - Backend Invoice Splitting

### Tasks
1. **Create Invoice Splitting Service**
   - Parse batch_allocations JSON from form
   - Create parent invoice record
   - Create child invoice for each batch
   - Set split tracking fields

2. **Consolidated View Template**
   - `app/templates/billing/consolidated_invoice_view.html`
   - Show parent + all children
   - Batch breakdown table
   - Payment tracking across split invoices

3. **Update Invoice Creation Logic**
   - Check for `batch_allocations` in line items
   - Trigger splitting if present
   - Return consolidated view instead of single invoice

**Estimated Timeline**: Week 3-4 (10-14 days)

---

## Testing Instructions

### Quick Test
```
1. Login to application
2. Navigate to: Billing → Create Invoice
3. Select patient
4. Add line item:
   - Type: OTC Medicine
   - Item: (Select any medicine with stock)
   - Quantity: 50
5. Press ENTER key (not Tab)
6. FIFO modal should appear
7. Verify batch allocation
8. Click "Accept Allocation"
9. Verify line item populated
10. Add to invoice and verify totals
```

### Console Check
Open browser console (F12), should see:
```
📦 fifo_allocation_modal.js loaded
✅ FIFO Allocation Modal initialized
✅ FIFO Allocation Modal ready
```

When pressing Enter:
```
Applying FIFO allocation: [...]
✅ FIFO allocation applied successfully
```

---

**Phase 2 Status**: ✅ COMPLETE - Ready for User Testing

**Dependencies for Phase 3**:
- Phase 2 testing complete
- User feedback incorporated
- Backend invoice splitting service design approved
