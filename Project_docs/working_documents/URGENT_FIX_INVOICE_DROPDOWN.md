# URGENT FIX - Invoice Dropdown Restored

## What Happened

I broke the invoice dropdown by adding a filter for a column that doesn't exist.

**My mistake:**
```python
# WRONG - This column doesn't exist on SupplierInvoice model
query = query.filter(SupplierInvoice.is_cancelled == False)
```

The `SupplierInvoice` model does NOT have an `is_cancelled` column. It has:
- `is_deleted` (from SoftDeleteMixin)
- `is_reversed`
- `is_credit_note`

But NO `is_cancelled`.

## What I Fixed

**File 1: `app/api/routes/supplier.py`**
- ❌ Removed: `SupplierInvoice.is_cancelled == False` filter (line 87)
- ✅ Changed: Balance_due filter to only skip if payment_status='paid' AND balance <= 0.01

**File 2: `app/services/supplier_service.py`**
- ❌ Removed: `SupplierInvoice.is_cancelled == False` filter (line 3071)

## Current Status

✅ Invoice dropdown should now work normally
✅ Invoices with payment_status='unpaid' or 'partial' will show
✅ Only invoices with payment_status='paid' AND zero balance will be excluded

## Testing

1. Refresh your browser (Ctrl+Shift+R)
2. Go to payment form
3. Select a supplier
4. Invoice dropdown should now show unpaid/partial invoices

If it still doesn't work, check app.log for errors.

## Root Cause Analysis

**Problem:** I assumed `is_cancelled` existed without verifying the model structure.

**Lesson:** Always check the actual model definition before adding filters on columns.

**How to check for cancelled invoices:**
- Use `is_deleted = True` from SoftDeleteMixin if you soft-delete cancelled invoices
- OR add a status column like `invoice_status` with values like 'active', 'cancelled', 'completed'
- OR use the existing `payment_status` field

## Remaining Issues (From Original Report)

Now that the dropdown is fixed, the other issues remain:

1. ✅ Invoice dropdown - FIXED (reverted broken filter)
2. ⚠️ Payment method showing "mixed" for advance - Requires database view migration
3. ⚠️ Reference_no and notes empty - Code fix is in place (needs testing)
4. ⚠️ Payment detail view not showing data - Requires database view migration

**CRITICAL:** You still need to run the database migration to fix issues #2, #3, #4:

```bash
psql -U postgres -d skinspire_dev -f "migrations/add_advance_amount_to_payments_view.sql"
```

But at least now you can proceed with creating payments!
