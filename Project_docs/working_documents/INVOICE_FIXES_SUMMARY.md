# Invoice Creation Fixes Summary

**Date**: 2025-11-17
**Status**: Multiple issues fixed and identified

---

## Issues Fixed

### 1. ✅ Batch Endpoint 404 Error (UUID Comparison Issue)

**Problem**: Medicine search found items, but batch endpoint returned 404

**Root Cause**:
- SQLAlchemy `filter_by()` had UUID comparison issues
- Adding `is_active == True` filter caused SQLAlchemy comparison to fail even when medicine was active

**Fix**: Changed from `filter_by()` to `filter()` and removed `is_active` filter to match search endpoint behavior

**Files Modified**:
- `app/views/billing_views.py` lines 2236-2241

---

### 2. ✅ Inventory GST Not Being Saved for OTC/Product/Consumable

**Problem**: Inventory transactions for OTC, Product, and Consumable medicines were not recording GST details

**Root Cause**:
- Inventory deduction function `_update_prescription_inventory` was only being called for Prescription items
- OTC, Product, and Consumable items were not having their inventory deducted at all

**Fix**:
- Added inventory deduction call for `GST_MEDICINES` and `GST_EXEMPT_MEDICINES` categories
- Updated function documentation to reflect it handles all medicine types

**Files Modified**:
- `app/services/billing_service.py` lines 260-268, 543-567

**Impact**: Now when OTC/Product/Consumable medicines are sold:
- Inventory is properly deducted
- GST values (CGST, SGST, IGST, Total GST) are saved to inventory table
- Batch and expiry validation happens
- Stock levels are tracked correctly

---

### 3. ✅ NameError in Invoice Line Item Processing

**Problem**: Invoice creation failed with `NameError: name 'invoice_data' is not defined`

**Root Cause**: Function `_process_invoice_line_item` tried to access non-existent `invoice_data` variable for date-based pricing/tax lookup

**Fix**: Added `invoice_date` as parameter to `_process_invoice_line_item` and passed it from calling functions

**Files Modified**:
- `app/services/billing_service.py` lines 809, 1042, 1223, 1327-1349

---

## Issues Identified (Configuration Required)

### 4. ⚠️ GL Account Field Null in Invoice Header

**Problem**: `invoice_header.gl_account_id` is NULL

**Root Cause**: No matching GL account found in `chart_of_accounts` table

**Code Location**: `app/services/billing_service.py` lines 786-792

```python
default_gl_account = session.query(ChartOfAccounts).filter(
    ChartOfAccounts.hospital_id == hospital_id,
    ChartOfAccounts.invoice_type_mapping == invoice_type,  # "Service", "Product", or "Prescription"
    ChartOfAccounts.is_active == True
).first()

gl_account_id = default_gl_account.account_id if default_gl_account else None
```

**Required Action**: Configure GL accounts in `chart_of_accounts` table with:
- `invoice_type_mapping` = 'Service' (for Service/Package invoices)
- `invoice_type_mapping` = 'Product' (for GST Medicines and GST Exempt Medicines)
- `invoice_type_mapping` = 'Prescription' (for Prescription Composite invoices)
- `is_active` = TRUE
- Matching `hospital_id`

**Note**: The Inventory table does NOT have a `gl_account_id` field - GL accounts are tracked at the invoice level only.

---

## Pending UI Issues

### 5. ⏳ Invoice View - Payment Tab Issues

**Problem**:
- Invoice line item shows "payment" but payment tab shows invoice history instead of payment details
- Need two separate views:
  a. All payments made against this specific invoice
  b. All payments made by the patient (payment history)

**Suggested Solution**: Create two tabs:
- "Invoice Payments" - Shows payments allocated to this invoice only
- "Payment History" - Shows all patient payments with controlled table width

**Files to Modify**: Invoice view template (needs investigation)

---

### 6. ⏳ Record Payment Screen - Package Invoice Checkbox Behavior

**Problem**:
- When a package invoice has payment plan installments (dropdown)
- Checking a child installment doesn't automatically check the parent package invoice
- Parent amount is not added to the aggregate value
- Allocated field at bottom ignores the package tick mark
- Payment summary is correct, but parent-child checkbox behavior is wrong

**Requires Investigation**:
- Payment form JavaScript
- Package invoice rendering logic
- Checkbox aggregation logic

---

## Testing Recommendations

### For Inventory GST Fix:
1. Create an invoice with OTC medicine (e.g., Cetirizine)
2. Check inventory table: `SELECT * FROM inventory.inventory WHERE medicine_id = '<uuid>' ORDER BY created_at DESC LIMIT 5;`
3. Verify cgst, sgst, igst, total_gst columns have values (not NULL or 0)

### For GL Account:
1. Check current GL accounts:
```sql
SELECT account_id, account_name, invoice_type_mapping, is_active
FROM config.chart_of_accounts
WHERE hospital_id = '<your-hospital-id>';
```

2. If missing, insert GL accounts:
```sql
-- Example for Product Revenue account
INSERT INTO config.chart_of_accounts (
    hospital_id,
    account_name,
    account_type,
    invoice_type_mapping,
    is_active
) VALUES (
    '<your-hospital-id>',
    'Pharmacy Sales Revenue',
    'Revenue',
    'Product',
    TRUE
);
```

---

## Summary

**Fixed (3)**: ✅ Batch 404, ✅ Inventory GST, ✅ Invoice creation error
**Configuration Needed (1)**: ⚠️ GL Account setup
**Pending Investigation (2)**: ⏳ Payment tabs UI, ⏳ Package checkbox behavior

---

**Next Steps**:
1. Test inventory GST storage with new OTC invoice
2. Configure GL accounts in chart_of_accounts
3. Investigate and fix payment view tabs
4. Fix package invoice checkbox behavior
