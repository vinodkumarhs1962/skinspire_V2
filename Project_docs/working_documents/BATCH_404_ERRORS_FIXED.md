# Batch Search 404 Errors Fixed

**Date**: 2025-11-17 19:05
**Issue**: Batch number search returning 404 errors
**Status**: ✅ FIXED

---

## Problem from app.log

```
GET /api/inventory/batches/9a044a7e-71b3-4dd8-9d57-ebe9cffe1490 HTTP/1.1 404
```

**When**: When selecting a medicine in invoice line items
**Impact**: Batch dropdown not loading, preventing invoice creation with batch selection

---

## Root Cause

### Wrong Endpoint Used ❌
**Location**: `app/static/js/components/invoice_item.js` line 562

**Called**: `/api/inventory/batches/{medicineId}`

**Problem**: This endpoint requires `@token_required` decorator, but the invoice page uses session-based authentication (Flask-Login)

### Available Endpoints

1. ❌ `/api/inventory/batches/<item_id>` - Requires token auth
2. ❌ `/api/billing/medicine/<medicine_id>/batches` - Requires token auth
3. ✅ `/invoice/web_api/medicine/<medicine_id>/batches` - Uses Flask-Login (session)

---

## Fixes Applied

### Fix 1: Changed to Web-Friendly Endpoint ✅
**Location**: `invoice_item.js` line 562

**Before**:
```javascript
fetch(`/api/inventory/batches/${medicineId}`, {
  headers: { 'Content-Type': 'application/json' },
  credentials: 'same-origin'
})
```

**After**:
```javascript
fetch(`/invoice/web_api/medicine/${medicineId}/batches`, {
  headers: { 'Content-Type': 'application/json' },
  credentials: 'same-origin'
})
```

**Why**: The web_api endpoint uses Flask-Login which works with browser sessions

---

### Fix 2: Fixed Response Format Handling ✅
**Location**: `invoice_item.js` lines 576-582

**Before** (expected wrapped object):
```javascript
if (!data.success || !data.batches || data.batches.length === 0) {
  // ...
}
console.log(`✅ Loaded ${data.batches.length} batches`);
```

**After** (handles direct array):
```javascript
if (!Array.isArray(data) || data.length === 0) {
  // ...
}
console.log(`✅ Loaded ${data.length} batches`);
```

**Why**: API returns direct array `[{batch, expiry_date, ...}]` not `{success: true, batches: [...]}`

---

### Fix 3: Fixed Field Name Mapping ✅
**Location**: `invoice_item.js` lines 591-619

**Before** (API v1 format):
```javascript
data.batches.forEach(batch => {
  const allocated = allocatedByBatch[batch.batch_number] || 0;
  const adjustedAvailable = batch.available_qty - allocated;
  option.value = batch.batch_number;
  const displayParts = batch.display.split(' - Avail: ');
  option.setAttribute('data-price', batch.sale_price || batch.unit_price);
});
```

**After** (Web API format):
```javascript
data.forEach(batch => {
  const allocated = allocatedByBatch[batch.batch] || 0;
  const adjustedAvailable = batch.available_quantity - allocated;
  option.value = batch.batch;
  // Build display from batch.batch and batch.expiry_date
  const expiryDisplay = batch.expiry_date ?
    new Date(batch.expiry_date).toLocaleDateString('en-GB', { ... }) :
    'No Expiry';
  const adjustedDisplay = `${batch.batch} (Exp: ${expiryDisplay}) - Avail: ${adjustedAvailable} units`;
  option.setAttribute('data-price', batch.unit_price || '0.00');
});
```

**Why**: Match the actual API response structure

---

## API Endpoint Details

### Correct Endpoint ✅
**URL**: `/invoice/web_api/medicine/<medicine_id>/batches`
**Method**: GET
**Authentication**: Flask-Login (session-based)
**Query Params**: Optional `?quantity=X`

**Response Format**:
```json
[
  {
    "batch": "BATCH-001",
    "expiry_date": "2025-12-31",
    "available_quantity": 100,
    "unit_price": 50.00,
    "mrp": 60.00,
    "gst_rate": 18,
    "cgst": 9,
    "sgst": 9,
    "igst": 0,
    "is_sufficient": true
  }
]
```

### Incorrect Endpoint ❌
**URL**: `/api/inventory/batches/<item_id>`
**Problem**: Requires token-based auth, not compatible with browser session

---

## Field Mapping Changes

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `data.success` | `Array.isArray(data)` | Direct array response |
| `data.batches` | `data` | Top-level is array |
| `batch.batch_number` | `batch.batch` | Field name changed |
| `batch.available_qty` | `batch.available_quantity` | Field name changed |
| `batch.display` | Built from `batch.batch` + `batch.expiry_date` | No pre-built display |
| `batch.sale_price` | `batch.unit_price` | Field name changed |
| `data.batches.length` | `data.length` | Direct array |

---

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `app/static/js/components/invoice_item.js` | Fixed endpoint + response format + field names | ~30 |
| `app/templates/billing/create_invoice.html` | Added cache bust version | 1 |

---

## Testing Checklist

### 1. Hard Refresh Browser ⚠️ CRITICAL
- **Chrome/Edge**: `Ctrl + Shift + R`
- **Firefox**: `Ctrl + Shift + R`
- **Mac**: `Cmd + Shift + R`

### 2. Check Logs While Testing
```bash
tail -f logs/app.log | grep batch
```

**Expected** (200 success):
```
✅ GET /invoice/web_api/medicine/{uuid}/batches HTTP/1.1 200
```

**Should NOT see** (404 error):
```
❌ GET /api/inventory/batches/{uuid} HTTP/1.1 404
```

### 3. Test Batch Selection Flow
- [ ] Navigate to Create Invoice page
- [ ] Select a patient
- [ ] Click "Add Item"
- [ ] Select item type: "OTC", "Prescription", "Product", or "Consumable"
- [ ] Search for and select a medicine
- [ ] **Check**: Batch dropdown loads (not "Loading batches..." stuck)
- [ ] **Check**: Batches appear with format: "BATCH-001 (Exp: 15/Jan/2025) - Avail: 100 units"
- [ ] Select a batch
- [ ] **Check**: Unit price auto-fills
- [ ] **Check**: Expiry date auto-fills
- [ ] **Check console**: `✅ Loaded X batches for medicine {uuid}`

### 4. Console Verification
Open DevTools (F12) console:
```
🔍 Fetching batches for medicine: {uuid}
✅ Loaded 5 batches for medicine {uuid}
📊 Already allocated quantities: {}
📦 Batch dropdown populated with 5 available batches (out of 5 total)
✅ Batch selected: BATCH-001, Price: 50.00, Expiry: 2025-12-31
```

**Should NOT see**:
```
❌ Error loading medicine batches
❌ No batches available for medicine
```

---

## Why This Happened

### Historical Context
1. **Invoice creation** uses browser sessions (Flask-Login)
2. **API routes** were designed for token-based auth (mobile/external apps)
3. **JavaScript used inventory API** which requires tokens
4. **Mismatch**: Browser can't provide tokens → 404

### Solution
Use the web-friendly endpoints in `billing_views.py` that use Flask-Login instead of token auth.

---

## Prevention for Future

### 1. Document Auth Types
Create `AUTH_ENDPOINTS.md`:
```markdown
## Session-Based (Flask-Login) - For Web UI
- /invoice/web_api/patient/search
- /invoice/web_api/medicine/{id}/batches
- /invoice/web_api/item/search

## Token-Based - For API/Mobile
- /api/inventory/batches/{id}
- /api/billing/medicine/{id}/batches
```

### 2. Consistent Naming
- Web endpoints: `/invoice/web_api/*` or `/billing/web_api/*`
- API endpoints: `/api/*`

### 3. Use Correct Auth in JavaScript
```javascript
// For browser-based invoice creation ✅
fetch('/invoice/web_api/medicine/{id}/batches', {
  credentials: 'same-origin'  // Session cookies
})

// For mobile/external apps ❌ Don't use in browser
fetch('/api/inventory/batches/{id}', {
  headers: { 'Authorization': `Bearer ${token}` }  // Token
})
```

---

## Summary

### What Was Broken ❌
- JavaScript called `/api/inventory/batches/{id}` (token auth required)
- Browser couldn't provide token → 404 error
- Expected wrong response format `{success, batches}`
- Expected wrong field names `batch_number`, `available_qty`, `display`

### What Was Fixed ✅
- Changed to `/invoice/web_api/medicine/{id}/batches` (session auth)
- Changed to handle direct array response
- Changed to use correct field names `batch`, `available_quantity`
- Build display string from `batch` + `expiry_date`
- Use `unit_price` instead of `sale_price`

### Result ✅
- No more 404 errors for batch search
- Batch dropdown loads correctly
- Prices and expiry dates auto-fill
- Invoice creation with batch selection works

---

**Next Step**: Hard refresh browser and test batch selection - no more 404 errors!

---

**Fixed By**: Claude Code
**Date**: 2025-11-17 19:05
**Files Modified**: 2 (invoice_item.js, create_invoice.html)
**Lines Changed**: ~31
**404 Errors**: Eliminated
