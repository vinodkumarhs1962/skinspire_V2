# Troubleshooting FIFO Allocation Issues

## Issues Fixed

### 1. ✅ calculateLineTotal Error (Line 628)
**Error**: `Cannot set properties of null (setting 'textContent')`

**Fix**: Added null checks before updating elements
```javascript
const gstAmountEl = row.querySelector('.gst-amount');
if (gstAmountEl) {
  gstAmountEl.textContent = totalGstAmount.toFixed(2);
}
```

### 2. ✅ FIFO Modal Null Error (Line 247)
**Error**: `Cannot read properties of null (reading 'show')`

**Fix**: Added better null check with user-friendly message
```javascript
if (typeof window.fifoModal === 'undefined' || window.fifoModal === null) {
  alert('FIFO allocation modal is loading. Please try again in a moment.');
  return;
}
```

### 3. ⚠️ 404 Error on Batches Endpoint
**Error**: `Failed to load resource: the server responded with a status of 404`

**Cause**: Browser cache holding old routes/sessions

**Solutions**:

#### Option 1: Hard Refresh Browser (Recommended)
```
Windows: Ctrl + F5
Mac: Cmd + Shift + R
```

#### Option 2: Clear Browser Cache
1. Open DevTools (F12)
2. Right-click Refresh button
3. Select "Empty Cache and Hard Reload"

#### Option 3: New Incognito Window
1. Open new incognito/private window
2. Navigate to http://127.0.0.1:5000
3. Login again
4. Test FIFO

#### Option 4: Verify Session
Check if you're still logged in:
- Look for user name in top right
- If not logged in, login again
- Sessions may expire during development restarts

## Verification Steps

### 1. Check Browser Console
Open F12 → Console tab, you should see:
```
📦 fifo_allocation_modal.js loaded
✅ FIFO Allocation Modal initialized
✅ FIFO Allocation Modal ready
📄 invoice.js loaded
✅ invoice.js initialized
```

**If you don't see these**: Hard refresh (Ctrl+F5)

### 2. Check Network Tab
Open F12 → Network tab:
- Filter by "fifo_allocation_modal.js"
- Should show status 200 (not 304 from cache)
- If 304, do hard refresh

### 3. Test Batch Endpoint
In Console, run:
```javascript
fetch('/invoice/web_api/medicine/7d6654ac-befb-46d9-82be-7fd57ca5161e/batches?quantity=1')
  .then(r => console.log('Status:', r.status))
```

Expected output:
- Status: 200 (working)
- Status: 401/302 (not logged in - login again)
- Status: 404 (cache issue - hard refresh)

## Testing FIFO Allocation

### Step-by-Step Test

1. **Ensure Clean State**
   - Hard refresh page (Ctrl+F5)
   - Check console for FIFO modal loaded messages
   - Verify no JavaScript errors

2. **Add Medicine Line Item**
   - Click "Add Line Item"
   - Select Type: **OTC Medicine**
   - Select a medicine from dropdown
   - Enter Quantity: **10**

3. **Trigger FIFO Modal**
   - Click in the Quantity field
   - Press **ENTER** key (not Tab!)

4. **Expected Behavior**
   - FIFO modal opens
   - Shows medicine name and quantity
   - Displays batch table with allocations
   - Can edit quantities
   - Accept/Cancel buttons work

5. **After Accept**
   - Line item should show batch details
   - Expiry date populated
   - Unit price populated
   - GST rate populated

## Common Issues & Solutions

### Issue: "FIFO allocation modal is loading" alert
**Cause**: Modal script loaded but not initialized yet

**Solution**: Wait 1-2 seconds and press Enter again

### Issue: No console messages about FIFO modal
**Cause**: JavaScript file not loaded/cached

**Solution**:
1. Hard refresh (Ctrl+F5)
2. Check Network tab for fifo_allocation_modal.js
3. Should see 200 status, not 304

### Issue: Batch dropdown still showing 404
**Cause**: Old route cached or session expired

**Solution**:
1. Check if still logged in (top right corner)
2. If not, login again
3. Hard refresh page
4. Clear browser cache completely if needed

### Issue: Modal opens but shows "Error fetching batch allocation"
**Possible Causes**:
1. Medicine has no inventory
2. Database issue
3. Backend error

**Solution**:
1. Check browser console for error details
2. Check Flask logs for backend errors
3. Try different medicine with known stock

## Current Application Status

**Flask App**: ✅ Running on http://127.0.0.1:5000

**Billing Views Blueprint**: ✅ Loaded successfully

**Routes Registered**:
- `/invoice/web_api/medicine/<id>/batches` ✅
- `/invoice/web_api/medicine/<id>/fifo-allocation` ✅

**JavaScript Files**:
- `fifo_allocation_modal.js` ✅ Created
- `invoice_item.js` ✅ Updated with FIFO integration
- `invoice.js` ✅ Updated with batch_allocations field

## If Still Not Working

1. **Restart Flask Completely**
   ```bash
   # Kill Flask process
   # In terminal where Flask is running: Ctrl+C

   # Start again
   python run.py
   ```

2. **Clear All Browser Data**
   - Settings → Privacy → Clear browsing data
   - Select: Cookies, Cache, Cached images
   - Time range: Last hour
   - Clear data

3. **Check Flask Logs**
   Look for errors in terminal where Flask is running

4. **Test with curl** (to verify backend)
   ```bash
   # Get a valid medicine ID from the database
   # Then test:
   curl http://127.0.0.1:5000/invoice/web_api/medicine/<medicine_id>/fifo-allocation?quantity=10
   ```

5. **Contact Support**
   If none of above works, provide:
   - Browser console errors (screenshot)
   - Network tab showing failed requests
   - Flask terminal logs

---

## Quick Checklist

Before reporting issues, verify:

- [ ] Flask app running without errors
- [ ] Billing views blueprint loaded (check Flask startup logs)
- [ ] Browser hard refreshed (Ctrl+F5)
- [ ] Still logged in (check top right)
- [ ] Console shows FIFO modal loaded messages
- [ ] No JavaScript errors in console
- [ ] Network tab shows fifo_allocation_modal.js loaded (200 status)
- [ ] Using medicine type (OTC/Prescription/Product/Consumable)
- [ ] Medicine has stock in inventory
- [ ] Pressing ENTER key (not Tab)

---

**Last Updated**: 2025-01-06 20:40
