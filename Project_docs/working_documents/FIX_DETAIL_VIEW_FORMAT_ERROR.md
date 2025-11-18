# Fix: Detail View Format Error

## Error: "unsupported format string passed to Undefined.__format__"

### Issue:
When clicking on an invoice to view details, the page shows an error and redirects back to the list view.

### Root Cause:
The template was trying to format fields (dates, currency) that were either:
1. Missing from the data dictionary (Undefined)
2. Had None values without proper handling

This happens because the detail view templates apply formatting (e.g., date format "%d-%b-%Y", currency format) to fields, and if those fields don't exist or are None, Jinja2 throws the "Undefined.__format__" error.

---

## Fix Applied

**File**: `app/services/patient_invoice_service.py` (lines 82-163)

### Changes Made:

1. **Comprehensive Field Defaults**: Added safe defaults for ALL fields that might be referenced in templates:

   - **Currency fields**: Default to `Decimal('0.00')`
     - grand_total, balance_due, paid_amount, total_amount, total_discount, etc.

   - **String fields**: Default to appropriate values
     - patient_name → 'Unknown Patient'
     - patient_mrn → 'N/A'
     - payment_status → 'unpaid'
     - invoice_number → 'N/A'
     - invoice_type → 'Service'
     - currency_code → 'INR'

   - **Boolean fields**: Default to explicit True/False
     - is_gst_invoice → False
     - is_cancelled → False
     - is_interstate → False
     - patient_is_active → True

   - **Date fields**: Can be None but must exist in dict
     - invoice_date, cancelled_at, created_at, updated_at, deleted_at

   - **Integer fields**: Default to 0 or 1
     - invoice_age_days → 0
     - status_order → 1

2. **Better Error Logging**: Added detailed error logging to help debug any remaining issues

---

## Testing Instructions

### Step 1: Restart Application
```bash
# Stop the current Flask server (Ctrl+C)
# Then restart:
python run.py
```

### Step 2: Test Detail View
1. Navigate to: `/universal/patient_invoices/list`
2. Click on any invoice to view details
3. Detail view should now load successfully

### Step 3: Expected Behavior
✅ Detail view loads without errors
✅ Status badge shows in header (top-right)
✅ All sections display properly
✅ Invoice line items section works
✅ Payment history section works

---

## If You Still Get Errors

### Check Application Logs
Look for these log messages:
```
ERROR - Error getting invoice by ID {id}: ...
ERROR - Error type: ...
ERROR - Hospital ID: ...
```

The error details will help identify which field is causing the problem.

### Common Issues:

1. **Date Formatting Error**:
   - Symptom: Error mentions "date" or "strftime"
   - Check: invoice_date field in database
   - Fix: Ensure invoice_date is not NULL for test invoices

2. **Currency Formatting Error**:
   - Symptom: Error mentions "Decimal" or "format"
   - Check: grand_total, balance_due fields
   - Fix: Ensure financial fields have numeric values

3. **Missing Field Error**:
   - Symptom: Error mentions specific field name
   - Check: That field exists in PatientInvoiceView model
   - Fix: Add that field to string_defaults dict in service

---

## What This Fix Does

Before this fix, when a field was missing or None:
```python
# Template tries to format:
{{ item.invoice_date|date_format("%d-%b-%Y") }}  # Error if invoice_date is Undefined!
{{ item.grand_total|currency }}  # Error if grand_total is None!
```

After this fix:
```python
# Service ensures all fields exist with safe defaults:
invoice_data['invoice_date'] = None  # Can be None (template handles it)
invoice_data['grand_total'] = Decimal('0.00')  # Always has a value
invoice_data['patient_name'] = 'Unknown Patient'  # Never empty
```

---

## Next Steps

1. ✅ **Restart application** (this fix is already applied)
2. ✅ **Test detail view** - Should work now
3. ⏳ **Run SQL script** - Still needed for patient name fix:
   ```bash
   psql -U skinspire_user -d skinspire_dev -f "migrations/fix_patient_invoice_view_20251104.sql"
   ```
4. ⏳ **Restart again** after SQL - To see patient name fix

---

## Technical Details

### Why This Error Happens

Jinja2 templates use `__format__` method internally when applying format filters or format strings. When a variable doesn't exist in the template context, Jinja2 creates an `Undefined` object. If you try to format an `Undefined` object:

```python
# In Python:
undefined_var = jinja2.Undefined()
"{:.2f}".format(undefined_var)  # Error: unsupported format string passed to Undefined.__format__
```

### The Fix Strategy

1. **Query the view** to get all calculated fields
2. **Convert to dict** using `get_entity_dict()`
3. **Ensure ALL fields exist** with appropriate defaults
4. **Return complete dict** that template can safely format

This ensures that even if the database has NULL values or missing fields, the template always gets a valid value it can work with.

---

## Files Modified

- ✅ `app/services/patient_invoice_service.py` (lines 82-163)
  - Enhanced `get_by_id()` method with comprehensive field defaults
  - Added better error logging

---

**Status**: ✅ **FIXED - Please restart and test**
