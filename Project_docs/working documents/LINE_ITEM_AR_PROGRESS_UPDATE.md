# Line-Item AR Splitting - Progress Update

**Date**: 2025-11-12
**Status**: 🚧 IN PROGRESS (Phase 1 Complete)

---

## ✅ Phase 1: Foundation (COMPLETED)

### 1. Database Schema ✅
- **File**: `migrations/add_line_item_reference_to_ar_subledger.sql`
- **Status**: Migration successfully executed
- **Changes**:
  - Added `reference_line_item_id UUID` column to `ar_subledger` table
  - Added foreign key constraint to `invoice_line_item(line_item_id)`
  - Created index `idx_ar_subledger_line_item` for performance
  - Added column comment for documentation

**Verification**:
```sql
-- Column exists and properly configured
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'ar_subledger'
  AND column_name = 'reference_line_item_id';
```

---

### 2. Model Updates ✅
- **File**: `app/models/transaction.py`
- **Status**: Model updated with new field and relationship
- **Changes**:
  ```python
  class ARSubledger(Base, TimestampMixin, TenantMixin):
      # ...existing fields...
      reference_line_item_id = Column(UUID(as_uuid=True), ForeignKey('invoice_line_item.line_item_id'))

      # New relationship
      line_item = relationship("InvoiceLineItem", foreign_keys=[reference_line_item_id])
  ```

---

### 3. Service Layer Updates ✅
- **File**: `app/services/subledger_service.py`
- **Status**: Updated with line-item support

#### 3.1 Updated: `create_ar_subledger_entry()`
**Added Parameter**:
```python
def create_ar_subledger_entry(
    # ...existing parameters...
    reference_line_item_id: Optional[Union[str, uuid.UUID]] = None,  # NEW
    # ...remaining parameters...
) -> Dict:
```

**Usage**:
```python
# Create AR entry for specific line item
ar_result = create_ar_subledger_entry(
    hospital_id=hospital_id,
    branch_id=branch_id,
    patient_id=patient_id,
    entry_type='invoice',
    reference_id=invoice_id,
    reference_type='invoice',
    reference_number=invoice_number,
    debit_amount=line_item.line_total,
    reference_line_item_id=line_item.line_item_id,  # ✅ NEW
    # ...other parameters...
)
```

#### 3.2 Added: `get_line_item_ar_balance()`
**New Function**:
```python
def get_line_item_ar_balance(
    hospital_id: Union[str, uuid.UUID],
    patient_id: Union[str, uuid.UUID],
    line_item_id: Union[str, uuid.UUID],
    session: Optional[Session] = None
) -> Decimal:
    """
    Calculate AR balance for a specific invoice line item

    Returns:
        Outstanding AR balance for this line item (positive = amount owed)
    """
```

**Usage Example**:
```python
# Get line item balance
from app.services.subledger_service import get_line_item_ar_balance

line_item_balance = get_line_item_ar_balance(
    hospital_id=hospital_id,
    patient_id=patient_id,
    line_item_id=line_item_id
)

# Example result:
# Line item total: ₹5,900
# Paid: ₹500
# Balance: ₹5,400
```

---

### 4. Package Payment Service ✅
- **File**: `app/services/package_payment_service.py`
- **Status**: Payment allocation method implemented

#### Added: `_calculate_package_allocated_payment()`
**Purpose**: Calculate allocated payment for package from mixed invoice

**Business Rule Implemented**:
> Services get paid first, then packages get remaining balance

**Method**:
```python
def _calculate_package_allocated_payment(
    self,
    session,
    invoice_id: str,
    package_id: str
) -> Decimal:
    """
    Calculate allocated payment for a specific package from a mixed invoice

    Payment Allocation Rule:
    1. All service line items get paid first (in order)
    2. Package line items get remaining balance
    """
```

**Example**:
```python
Invoice Total: ₹9,400
- Service 1: ₹2,000
- Service 2: ₹1,500
- Package 1: ₹5,900

Payment Made: ₹4,000

Allocation (calculated automatically):
- Service 1: ₹2,000 (fully paid) ✅
- Service 2: ₹1,500 (fully paid) ✅
- Package 1: ₹500 (partially paid)

package_plan.paid_amount = ₹500  # Not ₹4,000!
```

---

## 📋 Phase 2: Service Integration (PENDING)

### Next Tasks

#### Task 1: Update Billing Service AR Posting ⏳
**File**: `app/services/billing_service.py`
**Goal**: Create one AR entry per line item instead of one per invoice

**Current Code** (WRONG):
```python
# Single AR entry for entire invoice
ar_result = create_ar_subledger_entry(
    # ...
    debit_amount=invoice.invoice_total,  # ❌ Entire invoice
    # ...
)
```

**Required Code** (CORRECT):
```python
# Create AR entry for EACH line item
line_items = session.query(InvoiceLineItem).filter(
    InvoiceLineItem.invoice_id == invoice.invoice_id
).all()

for line_item in line_items:
    ar_result = create_ar_subledger_entry(
        # ...
        debit_amount=line_item.line_total,  # ✅ Line item amount
        reference_line_item_id=str(line_item.line_item_id),  # ✅ Line item ref
        description=f'Invoice {invoice_number} - {line_item.item_name}',
        # ...
    )
```

**Impact**:
- AR entries will show exactly what was billed for
- Enables line-item level payment tracking
- Foundation for payment allocation

---

#### Task 2: Create/Update Patient Payment Service ⏳
**File**: `app/services/patient_payment_service.py` (may need to create)
**Goal**: Implement payment allocation across line items with services-first rule

**Required Method**:
```python
def record_payment_with_allocation(
    self,
    hospital_id: str,
    patient_id: str,
    invoice_id: str,
    payment_amount: Decimal,
    payment_date: date,
    payment_method: str,
    # ...
) -> Dict[str, Any]:
    """
    Record patient payment with line-item allocation

    Allocation Rule: Services first, then packages

    Returns:
        {
            'success': bool,
            'payment_id': str,
            'allocation': [
                {'line_item_id': str, 'item_name': str, 'allocated': Decimal},
                ...
            ],
            'ar_entries': [str]  # List of AR entry IDs
        }
    """
```

**Process**:
1. Get all line items ordered by type (Services first, then Packages)
2. For each line item:
   - Get current AR balance using `get_line_item_ar_balance()`
   - Allocate payment up to line item balance
   - Create AR credit entry with `reference_line_item_id`
   - Track allocation details
3. Return allocation breakdown

---

#### Task 3: Update Package Service to Use AR Entries ⏳
**File**: `app/services/package_payment_service.py`
**Goal**: Get accurate `paid_amount` from AR entries instead of invoice

**Current Implementation** (IN-MEMORY):
```python
def _calculate_package_allocated_payment(
    self,
    session,
    invoice_id: str,
    package_id: str
) -> Decimal:
    # Uses invoice.paid_amount and allocates in-memory
    # This is a CALCULATION, not reading actual postings
```

**Required Update** (USE AR ENTRIES):
```python
def _calculate_package_allocated_payment(
    self,
    session,
    invoice_id: str,
    package_id: str
) -> Decimal:
    """
    Calculate allocated payment from actual AR entries

    This is more accurate - uses actual posted AR entries
    """
    from app.services.subledger_service import get_line_item_ar_balance

    # Find the line item for this package
    line_item = session.query(InvoiceLineItem).filter(
        InvoiceLineItem.invoice_id == invoice_id,
        InvoiceLineItem.package_id == package_id,
        InvoiceLineItem.item_type == 'Package'
    ).first()

    if not line_item:
        return Decimal('0.00')

    # Get actual AR entries for this line item
    entries = session.query(ARSubledger).filter(
        ARSubledger.reference_line_item_id == str(line_item.line_item_id)
    ).all()

    total_debits = sum(e.debit_amount or Decimal('0') for e in entries)
    total_credits = sum(e.credit_amount or Decimal('0') for e in entries)

    # Paid amount = credits (payments)
    paid_amount = total_credits

    return paid_amount
```

**Advantage**: Uses actual AR postings, not calculations. More accurate and auditable.

---

#### Task 4: Testing ⏳
**Goal**: Verify line-item AR splitting works end-to-end

**Test Case 1: Create Mixed Invoice**
```python
# Create invoice with services and package
invoice_data = {
    'patient_id': patient_id,
    'line_items': [
        {'item_type': 'Service', 'item_name': 'Consultation', 'line_total': 2000},
        {'item_type': 'Service', 'item_name': 'Lab Test', 'line_total': 1500},
        {'item_type': 'Package', 'package_id': pkg_id, 'line_total': 5900}
    ]
}

# Verify AR entries created for EACH line item
```

**Expected AR Entries** (3 entries, not 1):
```sql
SELECT
    reference_line_item_id,
    entry_type,
    debit_amount,
    description
FROM ar_subledger
WHERE reference_id = '<invoice_id>'
ORDER BY created_at;

-- Expected:
-- line1, debit, 2000, 'Invoice INV-123 - Service: Consultation'
-- line2, debit, 1500, 'Invoice INV-123 - Service: Lab Test'
-- line3, debit, 5900, 'Invoice INV-123 - Package: Hair Restoration'
```

**Test Case 2: Record Partial Payment**
```python
# Record payment of ₹4,000 for invoice of ₹9,400
payment_result = record_payment_with_allocation(
    patient_id=patient_id,
    invoice_id=invoice_id,
    payment_amount=Decimal('4000.00'),
    # ...
)

# Verify allocation
assert payment_result['allocation'] == [
    {'item_name': 'Consultation', 'allocated': 2000},
    {'item_name': 'Lab Test', 'allocated': 1500},
    {'item_name': 'Hair Restoration', 'allocated': 500}
]
```

**Expected AR Credit Entries** (3 credits):
```sql
-- line1, credit, 2000 (Service 1 fully paid)
-- line2, credit, 1500 (Service 2 fully paid)
-- line3, credit, 500  (Package partially paid)
```

**Test Case 3: Verify Line Item Balances**
```python
# Get balances for each line item
balance1 = get_line_item_ar_balance(hospital_id, patient_id, line_item_id_1)
balance2 = get_line_item_ar_balance(hospital_id, patient_id, line_item_id_2)
balance3 = get_line_item_ar_balance(hospital_id, patient_id, line_item_id_3)

# Expected:
assert balance1 == Decimal('0.00')    # Service 1 fully paid
assert balance2 == Decimal('0.00')    # Service 2 fully paid
assert balance3 == Decimal('5400.00') # Package has ₹5,400 outstanding
```

**Test Case 4: Create Package Plan**
```python
# Create package plan for the partially paid package
plan_data = {
    'invoice_id': invoice_id,
    'package_id': package_id,
    'total_amount': 5900,
    # ...
}

plan_result = package_service.create(plan_data, hospital_id, branch_id)

# Verify paid_amount
assert plan_result['data']['paid_amount'] == Decimal('500.00')  # Not 4000!
assert plan_result['data']['balance_amount'] == Decimal('5400.00')
```

---

## 📊 Benefits of Line-Item AR Splitting

### 1. Accurate Payment Tracking
- Know exactly which services/packages are paid
- Clear breakdown of outstanding amounts

### 2. Proper Payment Allocation
- Services paid first (business rule enforced)
- Packages receive remaining balance only

### 3. Package Plan Accuracy
- Package plans show correct `paid_amount`
- Discontinuation calculations are accurate

### 4. Standard Accounting Practice
- Proper AR subledger with line-item detail
- Audit trail for all allocations

### 5. Reporting Capabilities
- AR aging by service type vs packages
- Payment allocation reports
- Line-item level reconciliation

---

## 🚀 Next Steps

1. **Update Billing Service** - Modify AR posting to create per-line-item entries
2. **Create Payment Service** - Implement allocation logic
3. **Update Package Service** - Use AR entries instead of calculations
4. **Test End-to-End** - Verify complete workflow
5. **Update Documentation** - Document new payment allocation process

---

## 📝 Files Modified So Far

1. `migrations/add_line_item_reference_to_ar_subledger.sql` - ✅ Created and executed
2. `app/models/transaction.py` - ✅ ARSubledger model updated
3. `app/services/subledger_service.py` - ✅ Added line-item methods
4. `app/services/package_payment_service.py` - ✅ Added allocation method
5. `LINE_ITEM_AR_SPLITTING_IMPLEMENTATION.md` - ✅ Implementation plan
6. `LINE_ITEM_AR_PROGRESS_UPDATE.md` - ✅ This file

## 📝 Files to Modify Next

1. `app/services/billing_service.py` - ⏳ Update AR posting logic
2. `app/services/patient_payment_service.py` - ⏳ Create/update with allocation
3. `app/services/package_payment_service.py` - ⏳ Use AR entries (update existing method)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Phase 1 Status**: ✅ COMPLETE
**Phase 2 Status**: ⏳ PENDING
