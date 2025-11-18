# GL Account Configuration - Complete ✅

**Date**: 2025-11-17
**Status**: Successfully Configured
**Hospital ID**: 4ef72e18-e65d-4766-b9eb-0308c42485ca

---

## What Was Done

### Problem
- Invoice header `gl_account_id` field was NULL
- Billing service couldn't find GL accounts with matching `invoice_type_mapping`

### Solution
Updated existing GL accounts to add invoice type mappings:

| GL Account No | Account Name | Invoice Type Mapping | Status |
|---------------|--------------|---------------------|--------|
| **4100** | Service Revenue | **Service** | ✅ Active |
| **4300** | Medicine Revenue | **Product** | ✅ Active |
| **4320** | Prescription Sales | **Prescription** | ✅ Active |

---

## How It Works Now

### Invoice Creation Flow:

1. **Service/Package Invoices**
   - Invoice Type: `'Service'`
   - Maps to: **GL 4100** (Service Revenue)
   - Used for: Consultation, treatments, packages

2. **Medicine Invoices (OTC/Product/Consumable)**
   - Invoice Type: `'Product'`
   - Maps to: **GL 4300** (Medicine Revenue)
   - Used for: OTC medicines, GST medicines, GST-exempt medicines

3. **Prescription Composite Invoices**
   - Invoice Type: `'Prescription'`
   - Maps to: **GL 4320** (Prescription Sales)
   - Used for: Consolidated prescription items

### Code Reference

**File**: `app/services/billing_service.py` lines 786-792

```python
# Get default GL account for this invoice type
default_gl_account = session.query(ChartOfAccounts).filter(
    ChartOfAccounts.hospital_id == hospital_id,
    ChartOfAccounts.invoice_type_mapping == invoice_type,  # Now matches!
    ChartOfAccounts.is_active == True
).first()

gl_account_id = default_gl_account.account_id if default_gl_account else None
```

---

## Testing

### Test Invoice Creation:

1. **Test Service Invoice**
   ```sql
   SELECT invoice_number, invoice_type, gl_account_id, grand_total
   FROM invoice_header
   WHERE invoice_type = 'Service'
   ORDER BY created_at DESC
   LIMIT 1;
   ```
   Expected: `gl_account_id` should point to GL 4100

2. **Test Medicine Invoice**
   ```sql
   SELECT invoice_number, invoice_type, gl_account_id, grand_total
   FROM invoice_header
   WHERE invoice_type = 'Product'
   ORDER BY created_at DESC
   LIMIT 1;
   ```
   Expected: `gl_account_id` should point to GL 4300

3. **Test Prescription Invoice**
   ```sql
   SELECT invoice_number, invoice_type, gl_account_id, grand_total
   FROM invoice_header
   WHERE invoice_type = 'Prescription'
   ORDER BY created_at DESC
   LIMIT 1;
   ```
   Expected: `gl_account_id` should point to GL 4320

---

## Verification Query

To check current mappings:

```sql
SELECT
    gl_account_no,
    account_name,
    invoice_type_mapping,
    is_active
FROM chart_of_accounts
WHERE hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'
AND invoice_type_mapping IS NOT NULL
ORDER BY gl_account_no;
```

**Current Result**:
```
 gl_account_no |    account_name    | invoice_type_mapping | is_active
---------------+--------------------+----------------------+-----------
 4100          | Service Revenue    | Service              | t
 4300          | Medicine Revenue   | Product              | t
 4320          | Prescription Sales | Prescription         | t
```

---

## Your Complete GL Account Structure

You already have a comprehensive chart of accounts with **55 accounts** covering:

### Assets (GL 1000-1999):
- Accounts Receivable, Cash, Bank Accounts
- Payment gateway accounts (UPI, Cards, etc.)
- Inventory accounts
- GST Input Tax Credit (CGST, SGST, IGST)

### Liabilities (GL 2000-2999):
- Accounts Payable
- GST Output Tax (CGST, SGST, IGST)
- Employee Payables
- Patient Advances
- Loans

### Income (GL 4000-4999):
- Service Revenue (now mapped to 'Service')
- Medicine Revenue (now mapped to 'Product')
- Prescription Sales (now mapped to 'Prescription')
- Package Revenue
- Consultation Revenue

### Expenses (GL 5000-5999):
- Purchase accounts
- Salary expenses
- Rent, utilities
- Depreciation
- Bank charges
- Credit note adjustments

---

## Files Modified

1. **migrations/update_gl_invoice_mappings.sql** - Script that updated mappings
2. **app/services/billing_service.py** - Already had correct lookup logic

---

## What's Fixed Now

✅ **Invoice Header GL Account**: Will be populated correctly
✅ **Service Invoices**: Map to GL 4100
✅ **Medicine Invoices**: Map to GL 4300
✅ **Prescription Invoices**: Map to GL 4320
✅ **Inventory GST**: Already fixed (stores CGST, SGST, IGST)

---

## Next Steps

1. **Test**: Create a new invoice and verify `gl_account_id` is not NULL
2. **Monitor**: Check a few invoices to ensure correct GL mapping
3. **Remaining UI Issues**:
   - Payment tabs on invoice view
   - Package checkbox behavior on payment form

---

**Status**: ✅ GL Account Configuration Complete
**Date**: 2025-11-17 19:55
**Script**: migrations/update_gl_invoice_mappings.sql
