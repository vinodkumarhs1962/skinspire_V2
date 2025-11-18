# Batch Allocation Mode Implementation Plan

## Overview
Add user preference-based toggle between **Automated FIFO** and **Manual Batch Selection** modes for invoice creation.

## User Stories

### Auto Mode (Current - Existing Functionality)
1. User selects item type → item dropdown populated
2. User selects item → enters qty → presses Enter
3. FIFO allocation modal opens → shows proposed batch allocation
4. User accepts → multiple line items created (if needed)

### Manual Mode (New - Simplified Workflow)
1. User selects item type → item dropdown populated
2. User selects item → batch dropdown appears inline
3. Batch dropdown shows: "Batch-001 (Exp: 15/Jan/2025) - Avail: 150 units"
4. User picks one batch → enters qty → saves
5. For multiple batches: User repeats add item process

---

## Implementation Components

### 1. Database - User Preference Storage
**Table:** `users`
**Column:** `ui_preferences` (JSONB - already exists)

**New Key:**
```json
{
  "theme": "light",
  "invoice_batch_mode": "manual"  // or "auto"
}
```

**Default:** `"manual"` (simpler for new users)

---

### 2. Backend API Endpoints

#### A. Get Available Batches
**Endpoint:** `GET /api/inventory/batches/<item_id>`
**File:** `app/api/routes/inventory.py`

**Response:**
```json
{
  "success": true,
  "batches": [
    {
      "batch_number": "BATCH-001",
      "expiry_date": "2025-01-15",
      "available_qty": 150,
      "unit_price": 25.50,
      "display": "BATCH-001 (Exp: 15/Jan/2025) - Avail: 150"
    },
    ...
  ]
}
```

**Query Logic:**
- Filter: `item_id`, `hospital_id`, `available_qty > 0`
- Sort: `expiry_date ASC` (FIFO - oldest first)

#### B. Update User Batch Mode Preference
**Endpoint:** `POST /api/user/preferences/batch-mode`
**File:** `app/security/routes/auth.py` (or create new user preferences API)

**Request:**
```json
{
  "batch_mode": "manual"  // or "auto"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Batch mode updated to manual",
  "batch_mode": "manual"
}
```

---

### 3. Frontend - Invoice Create Template

**File:** `app/templates/billing/create_invoice.html`

**Add Toggle Switch** (Top right of form, near submit button):
```html
<div class="flex items-center space-x-2 mb-4">
  <label class="text-sm font-medium">Batch Mode:</label>
  <button
    id="batch-mode-toggle"
    class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
    data-mode="manual">
    <span class="sr-only">Toggle batch mode</span>
    <span class="translate-x-1 inline-block h-4 w-4 transform rounded-full bg-white transition-transform"></span>
  </button>
  <span id="batch-mode-label" class="text-sm text-gray-600">Manual</span>
</div>
```

**Add Batch Dropdown in Line Item Template** (Hidden by default):
```html
<select class="batch-dropdown hidden" name="batch_number_{index}">
  <option value="">-- Select Batch --</option>
  <!-- Populated via JS -->
</select>
```

---

### 4. Frontend - JavaScript Changes

**File:** `app/static/js/components/invoice_item.js`

#### A. Load User Preference on Page Load
```javascript
// In constructor or init method
loadUserBatchMode() {
  // Fetch from current_user context or API
  // Set this.batchMode = 'manual' or 'auto'
  // Update toggle UI
}
```

#### B. Modify `initFIFOAllocation(row)` Method
**Current:** Always triggers FIFO modal on Enter key
**Updated:** Check batch mode first

```javascript
initFIFOAllocation(row) {
  const quantityInput = row.querySelector('.quantity');
  const itemType = row.querySelector('.item-type');

  // Check batch mode
  if (this.batchMode === 'manual') {
    // Manual mode: Load batch dropdown inline
    this.initManualBatchSelection(row);
  } else {
    // Auto mode: Keep existing FIFO modal logic
    quantityInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && medicineBasedTypes.includes(itemType.value)) {
        window.fifoModal.show(...);  // Existing code
      }
    });
  }
}
```

#### C. New Method: `initManualBatchSelection(row)`
```javascript
initManualBatchSelection(row) {
  const itemIdInput = row.querySelector('.item-id');
  const batchDropdown = row.querySelector('.batch-dropdown');

  // When item is selected, fetch and populate batches
  itemIdInput.addEventListener('change', async () => {
    const itemId = itemIdInput.value;
    if (!itemId) return;

    // Fetch batches from API
    const response = await fetch(`/api/inventory/batches/${itemId}`);
    const data = await response.json();

    // Populate dropdown
    batchDropdown.innerHTML = '<option value="">-- Select Batch --</option>';
    data.batches.forEach(batch => {
      const option = document.createElement('option');
      option.value = batch.batch_number;
      option.textContent = batch.display;
      option.dataset.unitPrice = batch.unit_price;
      option.dataset.availableQty = batch.available_qty;
      option.dataset.expiryDate = batch.expiry_date;
      batchDropdown.appendChild(option);
    });

    // Show batch dropdown
    batchDropdown.classList.remove('hidden');
  });

  // When batch is selected, populate related fields
  batchDropdown.addEventListener('change', () => {
    const selectedOption = batchDropdown.options[batchDropdown.selectedIndex];
    if (selectedOption.value) {
      row.querySelector('.unit-price').value = selectedOption.dataset.unitPrice;
      row.querySelector('.expiry-date').value = selectedOption.dataset.expiryDate;
    }
  });
}
```

#### D. Toggle Handler
```javascript
handleBatchModeToggle() {
  const toggle = document.getElementById('batch-mode-toggle');
  const label = document.getElementById('batch-mode-label');

  toggle.addEventListener('click', async () => {
    const currentMode = toggle.dataset.mode;
    const newMode = currentMode === 'manual' ? 'auto' : 'manual';

    // Update via API
    const response = await fetch('/api/user/preferences/batch-mode', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({batch_mode: newMode})
    });

    if (response.ok) {
      this.batchMode = newMode;
      toggle.dataset.mode = newMode;
      label.textContent = newMode === 'manual' ? 'Manual' : 'Auto';
      // Update toggle UI colors
    }
  });
}
```

---

### 5. Inventory Service - Batch Fetching Logic

**File:** `app/services/inventory_service.py` (create if doesn't exist)

**Function:**
```python
def get_available_batches_for_item(item_id: str, hospital_id: str, branch_id: str = None):
    """
    Get all available batches for an item, sorted by expiry date (FIFO)

    Returns:
        List of dicts with batch info:
        - batch_number
        - expiry_date
        - available_qty
        - unit_price
        - display (formatted string)
    """
    # Query medicine_batch table
    # Filter: medicine_id = item_id, hospital_id, available_qty > 0
    # Sort: expiry_date ASC
    # Return formatted list
```

---

## Testing Checklist

### Manual Mode
- [ ] Toggle switch shows "Manual" by default
- [ ] Item selection populates batch dropdown
- [ ] Batch dropdown shows all available batches sorted by expiry
- [ ] Batch selection auto-fills unit price and expiry
- [ ] Can save line item with one batch
- [ ] Can add multiple line items for same medicine with different batches

### Auto Mode
- [ ] Toggle switch shows "Auto"
- [ ] Pressing Enter on qty opens FIFO modal
- [ ] Modal shows proposed allocation
- [ ] Accepting allocation creates multiple line items
- [ ] Existing functionality works as before

### Preference Persistence
- [ ] Mode selection saved to user preferences
- [ ] Mode persists across page refreshes
- [ ] Mode persists across login sessions

---

## Files to Modify

1. ✅ **app/api/routes/inventory.py** - Add batch fetching endpoint
2. ✅ **app/security/routes/auth.py** - Add preference update endpoint (or create new user API)
3. ✅ **app/services/inventory_service.py** - Add batch fetching service method
4. ✅ **app/templates/billing/create_invoice.html** - Add toggle + batch dropdown
5. ✅ **app/static/js/components/invoice_item.js** - Modify batch allocation logic
6. ✅ **app/views/billing_views.py** - Pass user batch mode preference to template

---

## Migration Notes

- No database schema changes (ui_preferences already JSONB)
- Existing invoices not affected
- Both modes fully functional
- Can switch modes mid-session without data loss

---

## Next Steps

Please review this plan and confirm:
1. ✅ User preference storage approach
2. ✅ Default mode (manual)
3. ✅ API endpoint structure
4. ✅ Toggle placement in UI
5. ✅ Any additional fields needed in batch dropdown

Once approved, I'll proceed with implementation.
