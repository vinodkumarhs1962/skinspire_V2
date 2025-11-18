# Patient Invoice Creation Bug - Fixed

## Problem

When creating a patient invoice, the system was throwing this error:

```
Error creating invoice: invalid input syntax for type uuid: "Patient1 Test1"
```

The system was trying to insert the patient **NAME** instead of the patient **UUID** into the `patient_id` field in both `invoice_header` and `inventory` tables.

## Root Cause

**File:** `app/api/routes/universal_api.py` (line 362)

The patient search API was returning the patient name in the `id` field:

```python
'id': patient_name,  # Use patient name as ID for filtering
'patient_id': str(patient.patient_id),  # Keep UUID for reference
```

**File:** `app/static/js/pages/invoice.js` (line 67)

The JavaScript was using `patient.id` (which contained the name) instead of `patient.patient_id` (which contains the UUID):

```javascript
if (patientIdInput) patientIdInput.value = patient.id;  // ❌ WRONG - sets "Patient1 Test1"
```

## Solution

**File Modified:** `app/static/js/pages/invoice.js` (line 68)

Changed the JavaScript to use the correct field:

```javascript
// FIX: Use patient.patient_id (UUID) instead of patient.id (name)
if (patientIdInput) patientIdInput.value = patient.patient_id || patient.uuid;  // ✅ CORRECT
```

## Why This Happened

The universal API was designed to return the patient name as `id` for compatibility with autocomplete filtering (similar to how suppliers work). However, the invoice creation form needed the actual UUID, not the name.

The API returns both:
- `id`: Patient name (for filtering/display)
- `patient_id`: Patient UUID (for database operations)
- `uuid`: Patient UUID (alternative field)

The fix ensures the JavaScript uses the correct field for the hidden `patient_id` form input.

## Testing

After this fix:

1. **Clear browser cache** or hard refresh (Ctrl+F5)
2. Navigate to Create Invoice
3. Search for and select a patient
4. Add line items
5. Submit the invoice

**Expected Result:** Invoice creates successfully without UUID errors.

## Files Changed

1. ✅ `app/static/js/pages/invoice.js` - Fixed patient ID assignment
2. ✅ `app/api/routes/billing.py` - Added debug logging and validation

## Related

Patient UUID for "Patient1 Test1": `5ad47172-824a-46b1-a9f1-d5fbeab57990`

This fix ensures that UUIDs are always used for database operations while patient names are used for display/filtering purposes.
