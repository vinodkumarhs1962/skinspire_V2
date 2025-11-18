# Multi-Invoice Payment Implementation

## Date: 2025-11-15

## Problem Identified

**Issue:** Payment recording was creating MULTIPLE `payment_id` records when a patient paid for multiple invoices, instead of creating ONE payment with multiple allocations.

**Example of WRONG behavior:**
```
Patient pays ₹5000 for 3 invoices
❌ Created 3 payment_details records (payment_id1, payment_id2, payment_id3)
```

**Expected CORRECT behavior:**
```
Patient pays ₹5000 for 3 invoices
✅ Create 1 payment_details record (payment_id = X, invoice_id = NULL)
✅ Create ar_subledger entries linking payment to 3 invoices
```

## Solution Implemented

### 1. New Function: `record_multi_invoice_payment()`

**Location:** `app/services/billing_service.py` (lines 2511-2807)

**Purpose:** Record a SINGLE payment allocated across MULTIPLE invoices

**Key Features:**
- Creates ONE `payment_details` record with `invoice_id = NULL` (for multi-invoice)
- Creates multiple `ar_subledger` entries linking payment to invoices
- Updates each invoice's `paid_amount` and `balance_due`
- Supports approval workflow
- Posts GL entries with proper linkage

### 2. Function Signature

```python
def record_multi_invoice_payment(
    hospital_id,
    invoice_allocations,  # List of {invoice_id, allocated_amount}
    payment_date,
    cash_amount=Decimal('0'),
    credit_card_amount=Decimal('0'),
    debit_card_amount=Decimal('0'),
    upi_amount=Decimal('0'),
    card_number_last4=None,
    card_type=None,
    upi_id=None,
    reference_number=None,
    recorded_by=None,
    save_as_draft=False,
    approval_threshold=Decimal('100000'),
    session=None
)
```

### 3. Invoice Allocations Format

```python
invoice_allocations = [
    {'invoice_id': 'uuid-1', 'allocated_amount': Decimal('2000')},
    {'invoice_id': 'uuid-2', 'allocated_amount': Decimal('1500')},
    {'invoice_id': 'uuid-3', 'allocated_amount': Decimal('1500')}
]
# Total allocated: ₹5000
```

### 4. How It Works

#### Step 1: Validate Input
- Ensures at least one invoice allocation
- Calculates total payment amount (cash + card + UPI, etc.)
- Validates total payment equals total allocated (±1 paisa tolerance)

#### Step 2: Create Payment Record
```python
payment = PaymentDetail(
    payment_id=uuid.uuid4(),
    hospital_id=hospital_id,
    invoice_id=None,  # ✅ NULL for multi-invoice payments
    total_amount=total_payment,
    # ... payment method details
)
```

#### Step 3: Post GL Entries (if auto-approved)
- Creates GL transaction linking all allocations
- Stores `gl_transaction_id` for ar_subledger linkage

#### Step 4: Create AR Subledger Entries (LINE-ITEM LEVEL)
For each invoice allocation, allocates across LINE ITEMS in priority order (Medicine → Service → Package):

**Process:**
```python
# For each invoice allocation
for each invoice in invoice_allocations:
    # 1. Get line items ordered by priority
    line_items = get_line_items_ordered_by_priority(invoice_id)
    # Order: Medicine (1) → Service (2) → Package (3)

    remaining = allocated_amount_for_invoice

    # 2. Allocate across line items
    for each line_item in line_items:
        # Get current balance for this line item
        line_balance = get_line_item_ar_balance(line_item_id)

        if line_balance <= 0:
            continue  # Already paid

        # Allocate to this line item
        allocated_to_line = min(line_balance, remaining)

        # ✅ Create AR entry for THIS LINE ITEM
        create_ar_subledger_entry(
            entry_type='payment',
            reference_id=payment_id,
            reference_type='payment',
            reference_line_item_id=line_item.line_item_id,  # ✅ LINE ITEM!
            credit_amount=allocated_to_line,  # ✅ Amount to THIS line item
            gl_transaction_id=gl_transaction_id
        )

        remaining -= allocated_to_line
```

**Why Line-Item Level?**
- Package plans track payments per line item (each service/product in package)
- Installment payments require line-item tracking
- Partial payments prioritize: Medicine FIRST, then Service, then Package
- Matches existing single-invoice payment logic

#### Step 5: Update Invoice Balances
```python
invoice.paid_amount = (invoice.paid_amount or 0) + allocated_amount
invoice.balance_due = invoice.grand_total - invoice.paid_amount
```

### 5. Database Impact

**payment_details Table:**
- ONE row created
- `invoice_id = NULL` (for multi-invoice payments)
- `total_amount` = sum of all allocations

**ar_subledger Table:**
- ONE row per LINE ITEM allocated (not per invoice)
- All linked by same `gl_transaction_id`
- Example for payment of ₹5000 to 3 invoices:
  - Invoice 1 (₹2000): 3 line items → 3 ar_subledger rows (with reference_line_item_id)
  - Invoice 2 (₹1500): 2 line items → 2 ar_subledger rows (with reference_line_item_id)
  - Invoice 3 (₹1500): 2 line items → 2 ar_subledger rows (with reference_line_item_id)
  - Total: 7 ar_subledger rows (all with reference_type='payment')

**invoice_header Table:**
- `paid_amount` updated for each invoice
- `balance_due` recalculated

### 6. Views Updated

**Payment View (`v_patient_payment_receipts`):**
- Based on ar_subledger with aggregation
- ONE row per payment_id
- Shows `invoice_count` and `is_multi_invoice_payment` flag
- Shows first invoice for backward compatibility

**Query Logic:**
```sql
WITH payment_ar_summary AS (
    SELECT
        ar_payment.reference_id AS payment_id,
        COUNT(DISTINCT ar_invoice.reference_id) AS invoice_count,
        (ARRAY_AGG(ar_invoice.reference_id))[1] AS first_invoice_id
    FROM ar_subledger ar_payment
    INNER JOIN ar_subledger ar_invoice
        ON ar_payment.gl_transaction_id = ar_invoice.gl_transaction_id
    WHERE ar_payment.reference_type = 'payment'
      AND ar_invoice.reference_type = 'invoice'
    GROUP BY ar_payment.reference_id
)
```

### 7. Service Methods Updated

**Payment Detail View - Invoice Allocations:**
```python
# app/services/patient_payment_service.py
def get_payment_invoice_allocations():
    # Queries ar_subledger for all invoice allocations
    # Returns list with allocated amounts per invoice
```

**Invoice Detail View - Payment History:**
```python
# app/services/patient_invoice_service.py
def get_payment_history():
    # Queries ar_subledger for all payments received
    # Shows allocated amount vs total payment amount
```

### 8. Backup Created

**File:** `app/services/billing_service.py.backup_20251115_125430`

**Size:** 167K

**Can be restored with:**
```bash
cp app/services/billing_service.py.backup_20251115_125430 app/services/billing_service.py
```

### 9. Route Integration ✅ COMPLETED

**Updated:** `app/views/billing_views.py` - `record_invoice_payment_enhanced()` function

**Changes Made:**
1. ✅ Replaced loop calling `record_payment()` multiple times with single call to `record_multi_invoice_payment()`
2. ✅ Advance payments applied separately (before payment methods)
3. ✅ Payment methods recorded as ONE payment across multiple invoices
4. ✅ Added detailed logging for debugging

**Code Flow:**
```python
# STEP 1: Apply advance payments (if any) - separate per invoice
if advance_amount > 0:
    for each invoice:
        apply_advance_payment(invoice_id, advance_portion)

# STEP 2: Record payment methods as ONE multi-invoice payment
if total_payment > 0:
    result = record_multi_invoice_payment(
        invoice_allocations=[...],  # All invoices
        cash_amount=...,
        credit_card_amount=...,
        # ... other payment methods
    )
```

### 10. Next Steps Required

1. **Testing:**
   - Test with 2-3 invoice allocation
   - Verify ar_subledger entries created correctly
   - Verify payment view shows correctly
   - Verify invoice view shows payment history

5. **Data Migration (Optional):**
   - Existing payments with invoice_id can stay as-is
   - New payments use multi-invoice function
   - Views handle both scenarios

## Files Modified

1. ✅ `app/services/billing_service.py` - Added `record_multi_invoice_payment()` with LINE-ITEM level allocation
2. ✅ `migrations/recreate_payment_invoice_views_from_ar_subledger.sql` - Updated payment view
3. ✅ `app/models/views.py` - Added `invoice_count` and `is_multi_invoice_payment` fields
4. ✅ `app/services/patient_payment_service.py` - Updated to use ar_subledger
5. ✅ `app/services/patient_invoice_service.py` - Updated to use ar_subledger
6. ✅ `app/templates/components/business/payment_invoice_allocations.html` - New template
7. ✅ `app/config/modules/patient_payment_config.py` - Added allocation section

## Critical Fix Applied (2025-11-15)

**Issue:** Initial implementation created AR entries at INVOICE level instead of LINE-ITEM level

**Fix:** Updated `record_multi_invoice_payment()` to:
- Get line items for each invoice ordered by priority: Medicine (1) → Service (2) → Package (3)
- Allocate payment across line items (not invoices)
- Create ar_subledger entries with `reference_line_item_id` (not just `reference_id`)
- Ensures compatibility with package plans and installment tracking

## Testing Checklist

- [ ] Create multi-invoice payment with 2-3 invoices
- [ ] Verify ONE payment_id created
- [ ] Verify ar_subledger has correct entries
- [ ] Verify payment list shows one row
- [ ] Verify payment detail shows all invoice allocations
- [ ] Verify invoice detail shows payment allocations
- [ ] Test partial payment scenario
- [ ] Test approval workflow for multi-invoice payment
- [ ] Test GL posting for multi-invoice payment

## Notes

- Function validates total payment = total allocated
- Supports all existing payment methods (cash, card, UPI)
- Maintains approval workflow compatibility
- GL entries link all allocations via `gl_transaction_id`
- Backward compatible with existing single-invoice payments
