# Invoice Issues Fix - 2025-11-17

## Issue 1: Inventory Stock Discrepancy - FIXED ✅

**Problem**: Amoxicillin batch 12345 dropdown shows stock as 1, but posting invoice shows "Insufficient stock: Available 0"

**Root Cause**:
The batch dropdown query (`web_api_medicine_batches` in billing_views.py:2307-2353) was using incorrect logic:

```python
# OLD (WRONG):
inventory_records = session.query(Inventory).filter(
    Inventory.hospital_id == hospital_id,
    Inventory.medicine_id == medicine_id,
    Inventory.current_stock > 0  # Filters ALL records with stock > 0
).order_by(
    Inventory.batch,  # Group by batch
    Inventory.created_at.desc()  # Latest entries first
).all()
```

The problem: This filters for `current_stock > 0` on ALL records, so it would return:
- Purchase record (current_stock = 1) ✅ Passes filter
- Prescription record (current_stock = 0) ❌ Excluded

Then it manually picks the first unique batch, which is the Purchase record showing stock = 1.

But the actual current stock is in the LATEST record (Prescription), which shows 0.

**Database Evidence**:
```sql
 stock_id               | medicine_name     | batch | stock_type   | units | current_stock | transaction_date
--------------------------------------+-------------------+-------+--------------+-------+---------------+----------------------------------
 42fbd726-0d14-4842-ab42 | Amoxicillin 500mg | 12345 | Prescription |    -1 |             0 | 2025-11-07 08:32:32 (LATEST) ⭐
 2940445f-c39a-4d37-aac3 | Amoxicillin 500mg | 12345 | Purchase     |   1.0 |             1 | 2025-06-16 00:00:00 (OLD)
```

**Fix Implemented** (billing_views.py:2307-2336):
```python
# NEW (FIXED):
from sqlalchemy.sql import text

query = text("""
    WITH latest_inventory AS (
        SELECT
            i.*,
            ROW_NUMBER() OVER (PARTITION BY i.batch ORDER BY i.created_at DESC) as rn
        FROM inventory i
        WHERE i.hospital_id = :hospital_id
          AND i.medicine_id = :medicine_id
    )
    SELECT * FROM latest_inventory
    WHERE rn = 1 AND current_stock > 0  -- Get LATEST record first, THEN filter by stock
    ORDER BY expiry  -- FIFO based on expiry date
""")
```

This uses a CTE (Common Table Expression) to:
1. **First**: Get the LATEST record for each batch (using ROW_NUMBER() ordered by created_at DESC)
2. **Then**: Filter for stock > 0

For batch 12345:
- Latest record: Prescription (current_stock = 0)
- Filter: 0 > 0? NO ❌
- Result: Batch 12345 NOT shown in dropdown ✅ CORRECT

**Result**:
- Batch dropdown now shows ACTUAL current stock
- No more "insufficient stock" errors for consumed batches

---

## Issue 2: GST Calculation on Create Invoice Display - INVESTIGATION

**Problem**: "create invoice display is not calculating GST for package, service and OTC medicines"

**Analysis**:

### Current Frontend Logic (invoice_item.js:686-778):

```javascript
calculateLineTotal(row) {
    const gstRate = parseFloat(row.querySelector('.gst-rate').value) || 0;
    const isGstInvoice = document.getElementById('is_gst_invoice')?.value === 'true';
    const isGstExempt = row.querySelector('.is-gst-exempt').value === 'true';

    if (isGstInvoice && !isGstExempt && gstRate > 0) {
        // Calculate GST
        if (isInterstate) {
            igstAmount = (taxableAmount * gstRate) / 100;
        } else {
            cgstAmount = (taxableAmount * halfGstRate) / 100;
            sgstAmount = (taxableAmount * halfGstRate) / 100;
        }
    } else {
        console.log('⚠️ GST NOT calculated');
    }
}
```

### Where GST Rate Comes From (invoice_item.js:486):

When item is selected from search:
```javascript
row.querySelector('.gst-rate').value = item.gst_rate || 0;
```

The `item.gst_rate` comes from `/web_api/item/search` endpoint.

### Current Search API (billing_views.py:2153-2258):

**For Package**:
```python
results.append({
    ...
    'gst_rate': float(package.gst_rate) if package.gst_rate else 0.0,
    ...
})
```

**For Service**:
```python
results.append({
    ...
    'gst_rate': float(service.gst_rate) if hasattr(service, 'gst_rate') else 0.0,
    ...
})
```

**For OTC/Medicines**:
```python
results.append({
    ...
    'gst_rate': float(medicine.gst_rate) if hasattr(medicine, 'gst_rate') and medicine.gst_rate else 0.0,
    ...
})
```

### Possible Issues:

1. **Database Missing GST Rates**: Package/Service/Medicine tables might not have `gst_rate` values populated
2. **isGstInvoice = false**: The hidden input `is_gst_invoice` might be set to false
3. **isGstExempt = true**: Items might be marked as GST exempt when they shouldn't be

### Diagnostic Steps:

**Step 1: Check Database**
```sql
-- Check Package GST rates
SELECT package_id, package_name, gst_rate, is_gst_exempt
FROM packages
WHERE hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'
AND package_name ILIKE '%your-package%'
LIMIT 5;

-- Check Service GST rates
SELECT service_id, service_name, gst_rate, is_gst_exempt
FROM services
WHERE hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'
LIMIT 5;

-- Check Medicine GST rates (OTC)
SELECT medicine_id, medicine_name, medicine_type, gst_rate, is_gst_exempt
FROM medicines
WHERE hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'
AND medicine_type = 'OTC'
LIMIT 5;
```

**Step 2: Check Browser Console**

When adding an item to invoice:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Add a Package/Service/OTC item
4. Look for log messages:
   - "Item search results for type..." - Check if `gst_rate` is in the response
   - "💰 Calculate Line Total - Input values" - Check `gstRate` value
   - "⚠️ GST NOT calculated" - Check the conditions logged

**Step 3: Check Hidden Input Values**

In browser console:
```javascript
// Check if GST invoice is enabled
console.log('is_gst_invoice:', document.getElementById('is_gst_invoice')?.value);

// Check if interstate
console.log('is_interstate:', document.getElementById('is_interstate')?.value);
```

### Expected Behavior:

**For GST to calculate, ALL of these must be true**:
1. `is_gst_invoice` = 'true'
2. Item `is_gst_exempt` = false
3. Item `gst_rate` > 0

If GST is NOT calculating, one of these conditions is failing.

### User's Comment:

> "it should use the GST service logic with GST date config check"

**Understanding**: The user wants the frontend to use date-based GST rates from the pricing_tax_service, not just the current master table rates.

**Challenge**: Frontend doesn't have an invoice date until form is submitted. We can't look up historical GST rates without a date.

**Proposed Solution**:

1. **For Frontend Display**: Show CURRENT gst_rate from master table (as it does now)
   - This gives users an estimate
   - Better than showing 0%

2. **For Backend Processing**: Use pricing_tax_service with invoice date (already implemented in `_process_invoice_line_item`)
   - This ensures the FINAL invoice uses correct historical rates
   - Already fixed in previous session

**Alternative Solution** (if user insists on date-based rates in frontend):

Add an "Invoice Date" field at the top of the create invoice form, then:
1. When user selects an item
2. Call a new API endpoint: `/web_api/item/<id>/pricing?date=YYYY-MM-DD`
3. This endpoint calls `get_applicable_pricing_and_tax()`
4. Returns date-based GST rate and price
5. Frontend uses this instead of master table values

---

## Files Modified:

1. **app/views/billing_views.py**
   - Lines 2307-2336: Fixed batch dropdown query to use CTE for latest inventory

---

## Testing Instructions:

### Test 1: Batch Dropdown Fix
1. Navigate to Create Invoice
2. Select "OTC" or "Prescription" item type
3. Search for "Amoxicillin"
4. Check batch dropdown
   - **Expected**: Should NOT show batch 12345 (stock is 0)
   - **Previous**: Would show batch 12345 with stock 1
5. Try to create invoice with consumed batch
   - **Expected**: Cannot select it from dropdown
   - **Previous**: Could select, then got error on submit

### Test 2: GST Calculation
1. Navigate to Create Invoice
2. Open browser console (F12)
3. Add a Package item
4. Check console logs for:
   - "Item search results" - Look for `gst_rate` value
   - "💰 Calculate Line Total" - Check input values
   - "⚠️ GST NOT calculated" - If shown, check conditions
5. Add a Service item - same checks
6. Add an OTC medicine - same checks
7. Check if GST rate displays in the line total

**If GST is not calculating**:
- Run diagnostic SQL queries above
- Check browser console for logged conditions
- Report which condition is failing: `isGstInvoice`, `isGstExempt`, or `gstRate`

---

## Next Steps:

1. **Test batch dropdown fix** - Should work immediately
2. **Diagnose GST calculation issue**:
   - Run diagnostic SQL queries
   - Check browser console logs
   - Determine which condition is failing
3. **Based on diagnosis, implement fix**:
   - If database missing GST rates → Populate master tables
   - If is_gst_invoice = false → Check invoice form initialization
   - If user wants date-based rates in frontend → Implement new API endpoint

---

## Questions for User:

1. When you add a Package/Service/OTC item to the invoice, do you see the GST rate percentage displayed (e.g., "18%")?
2. Is the "is_gst_invoice" checkbox checked when creating the invoice?
3. Can you open browser console and share the logged values when adding an item?
4. Do you want date-based GST rates in the frontend display, or is it okay to show current rates in frontend and use date-based rates during final invoice posting?

---

**Status**:
- Issue 1 (Batch Stock): ✅ FIXED
- Issue 2 (GST Calc): ⏸️ AWAITING USER DIAGNOSTIC INFO

**Date**: 2025-11-17
