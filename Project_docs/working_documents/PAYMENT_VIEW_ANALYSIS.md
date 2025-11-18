# Payment View Issues Analysis

**Date**: 2025-11-17
**Status**: Issues Identified

---

## Issue 1: Invoice View Payment Tabs

### Current Behavior (WRONG):
Looking at `app/views/billing_views.py` lines 982-1022:

```python
# Gets all payments for related invoices
payment_records = session.query(PaymentDetail).filter(
    PaymentDetail.hospital_id == current_user.hospital_id,
    PaymentDetail.invoice_id.in_(invoice_ids)  # All related invoice IDs
).order_by(PaymentDetail.payment_date.desc()).all()

all_payments = [get_detached_copy(payment) for payment in payment_records]

# Sets invoice payments to ALL payments
invoice['payments'] = all_payments  # Line 1011 - WRONG!

# Passes same data to template
all_payments=all_payments  # Line 1022
```

**Problem**: Both tabs show the SAME data - all payments from related invoices created in the same batch.

### What User Needs:

**Tab 1: "Invoice Payments"**
- Show only payments ALLOCATED to this specific invoice
- Source: `ar_subledger` table filtered by `invoice_header_id`
- Shows actual FIFO allocations made by payment service
- Example: Invoice INV-001 might have received ₹500 from Payment PMT-001 and ₹300 from PMT-002

**Tab 2: "Patient Payment History"**
- Show ALL payments made by the patient (any invoice, any date)
- Source: `payment_receipt_header` table filtered by `patient_id`
- Shows complete payment history for the patient
- With controlled table width for better display

---

## Issue 2: Package Invoice Checkbox Behavior

### Current Behavior (WRONG):
On the payment form (`/invoice/payment/record`):
- Package invoice has payment plan installments in dropdown
- When user checks a child installment:
  - ✅ Installment amount shows in the box
  - ❌ Parent package invoice checkbox doesn't get checked
  - ❌ Parent amount not added to aggregate
  - ❌ Allocated field at bottom ignores the package selection
  - ✅ Payment summary IS correct (so calculation works, just UI issue)

### Parent-Child Checkbox Logic Needed:
1. When child installment is checked → parent checkbox should auto-check
2. When child installment is unchecked → if no other children checked, uncheck parent
3. Parent amount should aggregate child amounts
4. Allocated field should include parent checkbox in calculation

---

## Root Causes:

### Issue 1:
**File**: `app/views/billing_views.py` function `view_invoice()` lines 982-1022

The code is querying `PaymentDetail` which is the OLD payment structure. After FIFO implementation, actual payment allocations are stored in `ar_subledger` table.

### Issue 2:
**File**: Likely in payment form JavaScript (need to investigate)
- `app/static/js/pages/*.js` or
- `app/templates/billing/payment_form*.html`

Parent-child checkbox event handlers not properly wired.

---

## Fix Plan:

### Fix 1: Invoice View Payment Tabs

**Step 1**: Modify `view_invoice()` to query AR subledger for invoice-specific payments

```python
# Get payments allocated to THIS specific invoice
invoice_payments = session.query(ARSubledger).filter(
    ARSubledger.hospital_id == current_user.hospital_id,
    ARSubledger.invoice_header_id == invoice_id,
    ARSubledger.transaction_type == 'payment'
).join(PaymentReceiptHeader).order_by(ARSubledger.created_at.desc()).all()
```

**Step 2**: Get all patient payments (not filtered by invoice)

```python
# Get ALL patient payments
patient_payments = session.query(PaymentReceiptHeader).filter(
    PaymentReceiptHeader.hospital_id == current_user.hospital_id,
    PaymentReceiptHeader.patient_id == patient_id
).order_by(PaymentReceiptHeader.payment_date.desc()).all()
```

**Step 3**: Update template to use correct data sources

**Step 4**: Add table width controls to payment history tab

### Fix 2: Package Checkbox Behavior

**Step 1**: Find the payment form JavaScript file

**Step 2**: Add event handler for child checkbox changes

```javascript
// When child installment checkbox changes
installmentCheckbox.addEventListener('change', function() {
    const parentCheckbox = document.getElementById('parent-package-checkbox');
    const allInstallmentCheckboxes = document.querySelectorAll('.installment-checkbox');

    // Check if any installment is checked
    const anyChecked = Array.from(allInstallmentCheckboxes).some(cb => cb.checked);

    // Auto-check/uncheck parent
    parentCheckbox.checked = anyChecked;

    // Trigger parent calculation
    updatePackageTotal();
});
```

**Step 3**: Update allocation calculation to include parent

---

## Files to Modify:

1. `app/views/billing_views.py` - view_invoice() function
2. `app/templates/billing/view_invoice.html` - payment tab structure
3. Payment form JavaScript file (TBD after investigation)
4. Payment form template (TBD after investigation)

---

**Next Steps**: Implement fixes starting with Issue 1
