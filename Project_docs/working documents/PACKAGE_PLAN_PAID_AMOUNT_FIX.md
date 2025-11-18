# Package Plan Paid Amount Fix

**Issue Date**: 2025-11-12
**Status**: ✅ FIXED

---

## 🐛 Issue Identified

**Problem**: When creating a package payment plan from a **paid invoice**, the plan's `paid_amount` field was showing **₹0** instead of the actual invoice payment amount.

**User Report**:
> "Invoice GST/2025-2026/00037 is paid for ₹5900 for hair restoration package. However in create package plan, the paid_amount is showing zero."

---

## 🔍 Root Cause Analysis

### What Was Happening

When creating a `PackagePaymentPlan` record, the service was:
1. ✅ Correctly linking to the invoice via `invoice_id`
2. ❌ **NOT** checking if the invoice had been paid
3. ❌ Always setting `paid_amount = 0` (default value)

**File**: `app/services/package_payment_service.py`
**Method**: `create()` (lines 308-345)

**Original Code** (lines 308-330):
```python
# Create plan record
plan = PackagePaymentPlan(
    plan_id=plan_id,
    hospital_id=hospital_id,
    branch_id=branch_id,
    patient_id=data.get('patient_id'),
    invoice_id=data.get('invoice_id'),
    package_id=data.get('package_id'),
    # ... other fields ...
    total_amount=Decimal(str(data.get('total_amount', 0))),
    # ❌ paid_amount NOT SET - defaults to 0
    installment_count=int(data.get('installment_count', 1)),
    installment_frequency=data.get('installment_frequency', 'monthly'),
    first_installment_date=first_installment_date,
    status='active',
    # ... other fields ...
)
```

**Result**: Plan created with `paid_amount = 0` even though invoice was paid ₹5,900.

---

## 🔧 Fix Applied

### Added Invoice Payment Check

**File**: `app/services/package_payment_service.py`
**Lines**: 307-334

**New Code**:
```python
# Check if invoice has been paid (to set initial paid_amount)
invoice_paid_amount = Decimal('0.00')
invoice_id = data.get('invoice_id')
if invoice_id:
    try:
        invoice = session.query(InvoiceHeader).filter(
            InvoiceHeader.invoice_id == invoice_id
        ).first()
        if invoice and hasattr(invoice, 'paid_amount') and invoice.paid_amount:
            invoice_paid_amount = invoice.paid_amount
            logger.info(f"Invoice {invoice_id} has paid_amount: ₹{invoice_paid_amount}")
    except Exception as inv_err:
        logger.warning(f"Could not check invoice paid_amount: {inv_err}")

# Create plan record
plan = PackagePaymentPlan(
    # ... other fields ...
    total_amount=Decimal(str(data.get('total_amount', 0))),
    paid_amount=invoice_paid_amount,  # ✅ Set from invoice paid_amount
    installment_count=int(data.get('installment_count', 1)),
    # ... other fields ...
)
```

### Added Import

**File**: `app/services/package_payment_service.py`
**Line**: 23

```python
from app.models.transaction import PackagePaymentPlan, InstallmentPayment, PackageSession, InvoiceHeader
```

---

## ✅ Expected Behavior After Fix

### Scenario 1: Invoice Paid in Full

**Setup**:
- Invoice: GST/2025-2026/00037
- Invoice Amount: ₹5,900
- Invoice Status: Paid in full
- Payment Amount: ₹5,900

**When Creating Package Plan**:
1. User selects invoice GST/2025-2026/00037
2. Service queries invoice and finds `paid_amount = ₹5,900`
3. Plan created with `paid_amount = ₹5,900` ✅
4. Log message: "Invoice xxx has paid_amount: ₹5900"

**Result**:
```python
PackagePaymentPlan:
  total_amount: ₹5,900
  paid_amount: ₹5,900  # ✅ Correctly populated
  balance_amount: ₹0   # Fully paid
```

### Scenario 2: Invoice Partially Paid

**Setup**:
- Invoice Amount: ₹5,900
- Payment Made: ₹2,000
- Invoice `paid_amount`: ₹2,000

**Result**:
```python
PackagePaymentPlan:
  total_amount: ₹5,900
  paid_amount: ₹2,000  # ✅ Correctly populated
  balance_amount: ₹3,900
```

### Scenario 3: Invoice Not Paid

**Setup**:
- Invoice Amount: ₹5,900
- Payment Made: ₹0
- Invoice `paid_amount`: ₹0

**Result**:
```python
PackagePaymentPlan:
  total_amount: ₹5,900
  paid_amount: ₹0  # Correct - no payment made
  balance_amount: ₹5,900
```

---

## 🧪 Testing Steps

### Step 1: Verify Existing Plan (Created Before Fix)

Check the plan that was created with zero paid_amount:

```sql
SELECT
    plan_id,
    invoice_id,
    total_amount,
    paid_amount,
    status
FROM package_payment_plans
WHERE invoice_id = (
    SELECT invoice_id
    FROM invoice_header
    WHERE invoice_number = 'GST/2025-2026/00037'
);
```

**Expected**:
- `paid_amount`: 0 (before fix)

### Step 2: Check Invoice Payment Status

```sql
SELECT
    invoice_id,
    invoice_number,
    invoice_total,
    paid_amount,
    payment_status
FROM invoice_header
WHERE invoice_number = 'GST/2025-2026/00037';
```

**Expected**:
- `paid_amount`: 5900.00
- `payment_status`: 'paid' or 'completed'

### Step 3: Fix Existing Plan (Manual Update)

If you want to fix the existing plan that was created before the fix:

```sql
UPDATE package_payment_plans
SET
    paid_amount = (
        SELECT paid_amount
        FROM invoice_header
        WHERE invoice_header.invoice_id = package_payment_plans.invoice_id
    ),
    updated_at = NOW(),
    updated_by = '7777777777'  -- Your user ID
WHERE invoice_id = (
    SELECT invoice_id
    FROM invoice_header
    WHERE invoice_number = 'GST/2025-2026/00037'
)
AND paid_amount = 0;
```

### Step 4: Test New Plan Creation

1. Navigate to: `/package/payment-plan/create`
2. Select patient
3. Select invoice: **GST/2025-2026/00037** (or any other paid invoice)
4. Fill in other details
5. Submit form
6. View created plan
7. ✅ Verify `paid_amount` shows ₹5,900 (not ₹0)

### Step 5: Check Application Logs

```bash
tail -50 C:/Users/vinod/AppData/Local/Programs/Skinspire\ Repository/Skinspire_v2/logs/app.log | grep "paid_amount"
```

**Expected log entry**:
```
Invoice <invoice_id> has paid_amount: ₹5900
```

---

## 🎯 Impact on Discontinuation

This fix is **critical** for the discontinuation workflow we just implemented:

### Before Fix (Wrong)
```python
Plan:
  total_amount: ₹5,900
  paid_amount: ₹0  # ❌ Wrong!

Discontinuation Calculation:
  Unused sessions value: ₹3,933
  Credit note amount: ₹3,933
  Refund status: 'none'  # ❌ Wrong! Should be 'approved'
```

### After Fix (Correct)
```python
Plan:
  total_amount: ₹5,900
  paid_amount: ₹5,900  # ✅ Correct!

Discontinuation Calculation:
  Unused sessions value: ₹3,933
  Credit note amount: ₹3,933
  Refund status: 'approved'  # ✅ Correct! Payment made, needs refund
```

**Why This Matters**:
- If `paid_amount = 0`: System thinks no refund is needed (just AR adjustment)
- If `paid_amount = 5900`: System correctly identifies refund is required
- Affects refund status and cash refund processing

---

## 📊 Database Schema Reference

### InvoiceHeader Fields
```python
invoice_id: UUID
invoice_number: String
invoice_total: Numeric(12,2)
paid_amount: Numeric(12,2)  # ← This is what we check
payment_status: String      # 'unpaid', 'partial', 'paid'
```

### PackagePaymentPlan Fields
```python
plan_id: UUID
invoice_id: UUID (FK → invoice_header)
total_amount: Numeric(12,2)
paid_amount: Numeric(12,2)  # ← This is what we populate
balance_amount: Computed (total_amount - paid_amount)
```

---

## 🚀 Ready for Testing

The fix is now deployed. Next time you create a package plan from a paid invoice:
- ✅ `paid_amount` will be populated correctly
- ✅ Discontinuation will correctly identify refund scenarios
- ✅ Credit note workflow will work as expected

---

## 📝 Related Documents

- `DISCONTINUATION_BUSINESS_LOGIC_FIX.md` - Credit note calculation fix
- `TESTING_GUIDE_CREDIT_NOTES.md` - Complete testing guide
- `PACKAGE_DISCONTINUATION_IMPLEMENTATION_COMPLETE.md` - Full feature documentation

---

**Document Version**: 1.0
**Fix Date**: 2025-11-12
**Status**: Ready for Testing
