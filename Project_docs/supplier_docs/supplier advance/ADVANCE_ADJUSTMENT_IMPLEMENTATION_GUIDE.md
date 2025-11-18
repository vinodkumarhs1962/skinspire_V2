# Supplier Advance Adjustment Implementation Guide

## Overview
This guide documents the complete implementation of a **subledger approach** for tracking supplier advance payment allocations. This replaces the dynamic calculation method with a proper audit trail.

---

## Database Changes

### 1. SQL Migration Script
**Location:** `migrations/add_supplier_advance_adjustment_complete.sql`

**Run this script to apply changes:**
```bash
psql -U postgres -d skinspire_dev -f migrations/add_supplier_advance_adjustment_complete.sql
```

**What it does:**
1. Adds `advance_amount` column to `supplier_payment` table
2. Creates `supplier_advance_adjustments` table for tracking advance allocations
3. Creates indexes for performance
4. Creates `v_supplier_advance_balance` view for quick balance lookup
5. Adds triggers for timestamp management

---

## Model Changes (Already Applied)

### File: `app/models/transaction.py`

#### 1. **SupplierPayment Model** (Lines 952-1152)
**Added Field:**
```python
advance_amount = Column(Numeric(12, 2), default=0)  # Line 999
```

**Added Relationship Comments:**
```python
# Advance adjustment relationships (defined in SupplierAdvanceAdjustment model using backref)
# - advance_allocations_out: List of adjustments where this payment is the source (advance being used)
# - advance_allocations_in: List of adjustments where this payment is the target (receiving advance allocation)
```

#### 2. **New Model: SupplierAdvanceAdjustment** (Lines 1634-1661)
Complete subledger table for tracking:
- Source payment (the advance being used)
- Target payment (the new payment receiving the advance)
- Invoice being paid
- Amount allocated
- Adjustment type (allocation, reversal, refund)

---

## Database View Created

### `v_supplier_advance_balance`
**Purpose:** Provides real-time view of available advance balance per supplier

**Query Example:**
```sql
SELECT * FROM v_supplier_advance_balance
WHERE supplier_id = 'a9e3ab6f-522d-4fca-8614-206a71414ee4'
ORDER BY advance_date ASC;  -- FIFO order
```

**Returns:**
- `advance_payment_id`: The unallocated payment ID
- `original_advance_amount`: Original payment amount
- `allocated_amount`: Total already allocated
- `remaining_balance`: Available balance
- `allocation_count`: Number of times this advance was used

---

## Service Layer Changes Required

### File: `app/services/supplier_payment_service.py`

You need to modify `create_payment` method to:

### **CURRENT PROBLEM:**
When payment has advance + other methods (e.g., ₹70 total: ₹20 advance + ₹50 cash):
- ❌ Only ₹50 (cash) gets saved in payment record
- ❌ ₹20 (advance) is allocated but NOT recorded in the payment
- ❌ No subledger entry created

### **REQUIRED FIX:**

#### **Step 1: Change Payment Amount Calculation**
**Current (Line 657):**
```python
amount=net_new_payment,  # WRONG: Excludes advance
```

**Should be:**
```python
amount=total_amount,  # CORRECT: Include all payment methods
```

#### **Step 2: Add advance_amount Field**
**After Line 669, add:**
```python
# Multi-method amounts
cash_amount=Decimal(str(data.get('cash_amount', 0))),
cheque_amount=Decimal(str(data.get('cheque_amount', 0))),
bank_transfer_amount=Decimal(str(data.get('bank_transfer_amount', 0))),
upi_amount=Decimal(str(data.get('upi_amount', 0))),
advance_amount=advance_allocation,  # ADD THIS LINE
```

#### **Step 3: Create Subledger Entries**
**After advance allocation (around line 606), add:**
```python
if advance_allocation > 0:
    # Get the allocated payment IDs from allocation_result
    allocated_payments = allocation_result.get('payments', [])

    # Create subledger entries for each source payment
    from app.models.transaction import SupplierAdvanceAdjustment

    for alloc in allocated_payments:
        adjustment = SupplierAdvanceAdjustment(
            adjustment_id=uuid.uuid4(),
            hospital_id=uuid.UUID(hospital_id) if isinstance(hospital_id, str) else hospital_id,
            branch_id=uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id,
            source_payment_id=uuid.UUID(alloc['payment_id']),
            target_payment_id=None,  # Will be set after payment is created
            invoice_id=uuid.UUID(data['invoice_id']) if data.get('invoice_id') and isinstance(data['invoice_id'], str) else data.get('invoice_id'),
            supplier_id=uuid.UUID(data['supplier_id']) if isinstance(data['supplier_id'], str) else data['supplier_id'],
            amount=Decimal(str(alloc['amount'])),
            adjustment_date=datetime.now(timezone.utc),
            adjustment_type='allocation',
            notes=f"Allocated from {'full' if alloc['allocation_type'] == 'full' else 'partial'} payment",
            created_by=user_id
        )
        session.add(adjustment)

    # After payment is created and flushed, update target_payment_id
    # (Do this after line 708: session.flush())
```

#### **Step 4: Update Subledger with Target Payment ID**
**After line 708 (session.flush()), add:**
```python
# Update subledger entries with the target payment ID
if advance_allocation > 0:
    from app.models.transaction import SupplierAdvanceAdjustment
    session.query(SupplierAdvanceAdjustment).filter(
        SupplierAdvanceAdjustment.invoice_id == payment.invoice_id,
        SupplierAdvanceAdjustment.target_payment_id.is_(None),
        SupplierAdvanceAdjustment.created_by == user_id
    ).update({
        'target_payment_id': payment.payment_id,
        'updated_at': datetime.now(timezone.utc),
        'updated_by': user_id
    }, synchronize_session=False)
```

---

## GL Entries (Accounts Payable)

### Issue: AP GL Entries Not Being Made

Check `app/services/gl_service.py` - function `create_supplier_payment_gl_entries()`

**Typical AP entry should be:**
```
Dr. Accounts Payable (Supplier)  ₹70
    Cr. Cash                       ₹50
    Cr. Advance Allocation         ₹20
```

**For advance allocation component:**
- This is an internal transfer, NOT a cash outflow
- Should credit "Supplier Advance" account (asset)
- Should NOT affect cash unless there's actual cash paid

---

## Validation Changes Required

### File: `app/services/supplier_payment_service.py`

#### Method: `_validate_multi_method_amounts()` (Line 1351)

**Current:**
```python
method_sum = (
    Decimal(str(data.get('advance_allocation_amount', 0))) +
    Decimal(str(data.get('cash_amount', 0))) +
    Decimal(str(data.get('cheque_amount', 0))) +
    Decimal(str(data.get('bank_transfer_amount', 0))) +
    Decimal(str(data.get('upi_amount', 0)))
)
```

✅ **This is CORRECT** - validation already includes advance in the sum

---

## Testing Checklist

### Test Case 1: Advance Only (₹10)
- [ ] Payment record created with `amount = ₹10`
- [ ] Payment record has `advance_amount = ₹10`
- [ ] Other method amounts are 0
- [ ] Subledger entry created linking source→target
- [ ] Invoice payment status updated
- [ ] Advance balance reduced

### Test Case 2: Mixed Payment (₹70 total: ₹20 advance + ₹50 cash)
- [ ] Payment record created with `amount = ₹70`
- [ ] Payment record has `advance_amount = ₹20`
- [ ] Payment record has `cash_amount = ₹50`
- [ ] Subledger entry created for ₹20 allocation
- [ ] GL entry shows:
  - Dr. AP ₹70
  - Cr. Cash ₹50
  - Cr. Supplier Advance ₹20

### Test Case 3: Verify Advance Balance
```sql
-- Check advance balance
SELECT * FROM v_supplier_advance_balance
WHERE supplier_id = '<supplier_id>';

-- Check subledger entries
SELECT * FROM supplier_advance_adjustments
WHERE supplier_id = '<supplier_id>'
ORDER BY adjustment_date DESC;

-- Check payment details
SELECT payment_id, amount, advance_amount, cash_amount, cheque_amount
FROM supplier_payment
WHERE supplier_id = '<supplier_id>'
ORDER BY payment_date DESC;
```

---

## Advantages of Subledger Approach

### ✅ Benefits
1. **Audit Trail**: Every advance allocation is tracked
2. **Performance**: No need to calculate balance dynamically
3. **Accuracy**: Point-in-time balance tracking
4. **Reporting**: Easy to generate advance utilization reports
5. **Reversal Support**: Can reverse/cancel allocations
6. **FIFO Tracking**: Clear record of which advance was used when

### ❌ Old Dynamic Approach Problems
1. Had to scan all payments every time
2. No audit trail of allocations
3. Couldn't track partial allocations easily
4. Performance degraded with many payments
5. No way to reverse allocations

---

## Next Steps

1. **Run the SQL migration** (see Database Changes section)
2. **Update service layer** with changes outlined above
3. **Test all three scenarios** in Testing Checklist
4. **Fix GL posting** to include advance allocation entries
5. **Add reporting queries** using the new subledger

---

## Questions Addressed

### Q1: Why is advance not saving in mixed payments?
**A:** Payment amount was set to `net_new_payment` (excluding advance) instead of `total_amount`. Also, `advance_amount` field wasn't being populated.

### Q2: Why aren't AP GL entries being made?
**A:** Need to check `gl_service.py` - likely missing logic to handle advance allocation as a separate GL line item.

### Q3: Should we use a subledger for advance adjustments?
**A:** ✅ **YES!** Already implemented. Much better than dynamic calculation for:
- Performance
- Audit trail
- Accuracy
- Reporting
- Reversal support

---

## Support

If you encounter issues:
1. Check `logs/app.log` for errors
2. Verify migration ran successfully
3. Check the test queries in Testing Checklist
4. Review this guide for required service changes

