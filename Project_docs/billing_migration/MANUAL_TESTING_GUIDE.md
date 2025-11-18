# Manual Testing Guide - Invoice Create After Migration

**Purpose**: Verify that invoice create functionality works correctly after database migration for split invoice tracking.

**Application Status**: ✅ Flask app is running on http://127.0.0.1:5000

---

## Pre-Test Checklist

- [x] Database migration applied successfully
- [x] Patient invoices view updated to v2.0
- [x] InvoiceHeader model has new split tracking fields
- [x] PatientInvoiceView model updated
- [x] Flask application started on http://127.0.0.1:5000

---

## Test 1: Login & Access

**Steps**:
1. Open browser: http://127.0.0.1:5000
2. Login with test credentials:
   - User ID: `9876543210`
   - Password: `password123`

**Expected Result**:
- ✅ Login successful
- ✅ Dashboard loads
- ✅ No errors in console (F12 Developer Tools)

---

## Test 2: Navigate to Invoice Create

**Steps**:
1. From sidebar menu, click **Billing** → **Create Invoice**
2. Or navigate directly to: http://127.0.0.1:5000/invoice/create

**Expected Result**:
- ✅ Invoice create page loads
- ✅ Patient search field visible
- ✅ GST checkbox visible
- ✅ Line items section visible
- ✅ No JavaScript errors in console (F12 → Console tab)

**Check Console for**:
```
📄 invoice.js loaded
✅ invoice.js initialized
✅ Patient search initialized
✅ GST toggle initialized
✅ Form submission initialized
```

---

## Test 3: Patient Search

**Steps**:
1. Click on **Patient Search** field
2. Type first 2-3 letters of a patient name (or leave empty to see all)

**Expected Result**:
- ✅ Dropdown appears with patient list
- ✅ Shows patient name, MRN, and contact
- ✅ Click on a patient
- ✅ Patient details populate (name, MRN display)
- ✅ Search field shows selected patient

**API Check** (F12 → Network tab):
```
Request: GET /invoice/web_api/patient/search?q=<query>
Status: 200 OK
Response: JSON array of patients
```

---

## Test 4: Add Line Item - Service

**Steps**:
1. In line items section, click **Add Line Item** button
2. Select **Type**: `Service` from dropdown
3. Click on **Item** dropdown

**Expected Result**:
- ✅ Dropdown shows list of services (up to 20)
- ✅ Each shows service name and price
- ✅ Select a service
- ✅ MRP field auto-fills
- ✅ Quantity defaults to 1
- ✅ **Batch and Expiry fields are DISABLED** (grayed out)

**API Check**:
```
Request: GET /invoice/web_api/item/search?type=Service&q=
Status: 200 OK
Response: JSON array with {id, name, price, gst_rate, ...}
```

---

## Test 5: Add Line Item - Package

**Steps**:
1. Add new line item
2. Select **Type**: `Package`
3. Click on **Item** dropdown

**Expected Result**:
- ✅ Dropdown shows list of packages
- ✅ Select a package
- ✅ MRP auto-fills
- ✅ **Batch and Expiry fields are DISABLED**

**API Check**:
```
Request: GET /invoice/web_api/item/search?type=Package&q=
Status: 200 OK
Response: JSON array of packages
```

---

## Test 6: Add Line Item - OTC Medicine

**Steps**:
1. Add new line item
2. Select **Type**: `OTC Medicine`
3. Click on **Item** dropdown

**Expected Result**:
- ✅ Dropdown shows OTC medicines WITH STOCK information
- ✅ Shows medicine name and current stock (e.g., "Paracetamol (Stock: 100)")
- ✅ Select a medicine
- ✅ **Batch dropdown is ENABLED**
- ✅ **Expiry date field is ENABLED**

**API Check**:
```
Request: GET /invoice/web_api/item/search?type=OTC&q=
Status: 200 OK
Response: JSON array with medicines having current_stock > 0
```

---

## Test 7: Batch Selection for Medicine

**Steps**:
1. With OTC medicine selected, click **Batch** dropdown
2. Observe available batches

**Expected Result**:
- ✅ Dropdown shows available batches for selected medicine
- ✅ Shows: Batch number, Expiry date, Stock, MRP
- ✅ Select a batch
- ✅ Expiry date auto-fills
- ✅ MRP auto-fills
- ✅ GST rate auto-fills

**API Check**:
```
Request: GET /invoice/web_api/medicine/{medicine_id}/batches
Status: 200 OK
Response: JSON array with {batch, expiry_date, stock, mrp, gst_rate, ...}
```

---

## Test 8: Add Line Item - Prescription Medicine

**Steps**:
1. Add new line item
2. Select **Type**: `Prescription Medicine`
3. Verify item search works

**Expected Result**:
- ✅ Shows prescription medicines only
- ✅ Batch and expiry fields ENABLED
- ✅ Batch selection works same as OTC

---

## Test 9: Add Line Item - Product

**Steps**:
1. Add new line item
2. Select **Type**: `Product`
3. Verify item search works

**Expected Result**:
- ✅ Shows products with stock > 0
- ✅ Batch and expiry fields ENABLED
- ✅ Batch selection works

---

## Test 10: Add Line Item - Consumable

**Steps**:
1. Add new line item
2. Select **Type**: `Consumable`
3. Verify item search works

**Expected Result**:
- ✅ Shows consumables with stock > 0
- ✅ Batch and expiry fields ENABLED
- ✅ Batch selection works

---

## Test 11: Item Type Change Behavior

**Steps**:
1. Add a line item and select `OTC Medicine`
2. Select an item and batch
3. Now change **Type** to `Service`

**Expected Result**:
- ✅ Item dropdown clears
- ✅ All fields clear (MRP, GST, Quantity, Batch, Expiry)
- ✅ Batch and Expiry fields become DISABLED
- ✅ Ready for new selection

---

## Test 12: GST Toggle

**Steps**:
1. Check the **GST Invoice** checkbox
2. Observe GST fields visibility
3. Uncheck the checkbox

**Expected Result**:
- ✅ When checked: CGST/SGST rows visible in summary
- ✅ When unchecked: GST rows hidden
- ✅ Toggle works smoothly

---

## Test 13: Multiple Line Items

**Steps**:
1. Add 3 different line items:
   - 1 Service
   - 1 Package
   - 1 OTC Medicine (with batch)
2. Verify all line items display correctly

**Expected Result**:
- ✅ All 3 line items show in the list
- ✅ Each has correct type icon/label
- ✅ Medicine item shows batch and expiry
- ✅ Service/Package items show N/A for batch
- ✅ Delete button works for each item

---

## Test 14: Form Validation

**Steps**:
1. Try to submit form WITHOUT selecting a patient

**Expected Result**:
- ✅ Alert: "Please select a patient."
- ✅ Form does NOT submit
- ✅ Focus returns to patient search field

**Steps**:
2. Select a patient, but don't add any line items
3. Try to submit

**Expected Result**:
- ✅ Alert: "Please add at least one line item."
- ✅ Form does NOT submit

---

## Test 15: Invoice Submission (DO NOT SUBMIT YET)

**IMPORTANT**: Don't actually submit the invoice yet since Phase 2 (FIFO batch allocation) will change the submission flow.

**Expected Behavior** (for reference):
- When submit is clicked:
  1. Button shows "Creating Invoice..." with spinner
  2. Form data serialized with all line items
  3. POST to `/invoice/create`
  4. On success: Redirect to invoice detail view
  5. On error: Show error message

---

## Test 16: Database Schema Verification

**Steps**:
1. Open a new terminal
2. Run these queries:

```bash
# Connect to database
PGPASSWORD='Skinspire123$' psql -U skinspire_admin -d skinspire_dev -h localhost

# Query 1: Check invoice_header columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'invoice_header'
  AND column_name IN ('parent_transaction_id', 'split_sequence', 'is_split_invoice', 'split_reason');

# Query 2: Check patient_invoices_view columns
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'patient_invoices_view'
  AND column_name IN ('split_invoice_count', 'parent_invoice_number');

# Query 3: Check existing invoices have default values
SELECT invoice_number, is_split_invoice, split_sequence, parent_transaction_id
FROM invoice_header
LIMIT 5;

# Exit
\q
```

**Expected Result**:
- ✅ All new columns exist in invoice_header
- ✅ All new columns exist in patient_invoices_view
- ✅ Existing invoices have: is_split_invoice=false, split_sequence=1, parent_transaction_id=null

---

## Test 17: Console Error Check

**Steps**:
1. Open browser console (F12 → Console)
2. Perform all above tests
3. Check for any errors

**Expected Result**:
- ✅ No red errors
- ✅ Only info/log messages
- ✅ All API calls return 200 OK status
- ✅ No 404 errors for JavaScript files

---

## Known Issues (Expected)

1. **⚠️ Billing views blueprint warning**:
   ```
   WARNING - Billing views blueprint could not be loaded: No module named 'xhtml2pdf'
   ```
   - **Impact**: PDF generation feature not available
   - **Fix**: Install xhtml2pdf if needed: `pip install xhtml2pdf`
   - **For this test**: Can be ignored, doesn't affect invoice create

2. **⚠️ Medicine entity not registered**:
   ```
   WARNING - No registration found for entity: medicines
   ```
   - **Impact**: Medicine master CRUD via Universal Engine not available
   - **For this test**: Doesn't affect invoice create (uses direct queries)

---

## Test Summary Checklist

After completing all tests, verify:

- [ ] Application starts without errors
- [ ] Login works
- [ ] Invoice create page loads
- [ ] Patient search functional
- [ ] All 6 item types searchable (Service, Package, OTC, Prescription, Product, Consumable)
- [ ] Batch selection works for medicine types
- [ ] Batch/Expiry fields disabled for Service/Package
- [ ] Item type change clears fields correctly
- [ ] GST toggle works
- [ ] Multiple line items can be added
- [ ] Form validation works
- [ ] Database schema has new fields
- [ ] Existing invoices unaffected
- [ ] No console errors

---

## What's Next: Phase 2 - FIFO Allocation

Once testing is complete and everything works, we'll implement:

1. **FIFO Allocation Modal**
   - Auto-batch selection when user enters quantity
   - Show batch breakdown (multiple batches if needed)
   - Allow manual override

2. **Enter Key Trigger**
   - Press Enter after entering quantity
   - Modal shows FIFO batch allocation preview
   - User can accept or modify

3. **Multi-Batch Line Items**
   - Single line item can have multiple batches
   - Display batch breakdown in table
   - Separate invoices for different batches (backend)

---

## Reporting Issues

If you find any issues during testing:

1. **Note the test number** where issue occurred
2. **Screenshot** the error (if visible)
3. **Copy console errors** (F12 → Console)
4. **Copy network errors** (F12 → Network → Failed requests)
5. **Describe expected vs actual behavior**

---

**Testing Date**: ______________________

**Tested By**: ______________________

**Overall Result**: [ ] Pass  [ ] Pass with minor issues  [ ] Fail

**Notes**:
_____________________________________________________________________
_____________________________________________________________________
_____________________________________________________________________
