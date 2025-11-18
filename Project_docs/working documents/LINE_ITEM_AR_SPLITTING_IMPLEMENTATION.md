# Line-Item AR Splitting Implementation Plan

**Issue Date**: 2025-11-12
**Status**: 🚧 IN PROGRESS

---

## 📋 Overview

Implement **line-item level AR (Accounts Receivable) splitting** to properly track payment allocation for mixed invoices containing both services and packages.

### Business Rule
**Payment Allocation Priority**: Services first, then packages
- In a mixed invoice, any partial payment should be allocated to service line items first
- Packages receive remaining balance only after all services are fully paid

### Current Problem
**Invoice-level AR tracking**:
```
Invoice Total: ₹9,400
- Service 1: ₹2,000
- Service 2: ₹1,500
- Package 1: ₹5,900

Current AR Entry (WRONG):
Dr: AR (1100)              ₹9,400  [single entry for entire invoice]
Cr: Service Revenue (4210) ₹3,500
Cr: Package Revenue (4200) ₹5,900

When ₹4,000 paid:
Cr: AR (1100)              ₹4,000  [no breakdown by line item]
Dr: Cash (1000)            ₹4,000

❌ Problem: Cannot tell which services/packages were paid
```

### Proposed Solution
**Line-item level AR tracking**:
```
Invoice Creation:
Dr: AR (1100) - Service 1  ₹2,000  [reference: line_item_id_1]
Dr: AR (1100) - Service 2  ₹1,500  [reference: line_item_id_2]
Dr: AR (1100) - Package 1  ₹5,900  [reference: line_item_id_3]
Cr: Service Revenue (4210) ₹3,500
Cr: Package Revenue (4200) ₹5,900

When ₹4,000 paid (Services first rule):
Cr: AR (1100) - Service 1  ₹2,000  [fully paid]
Cr: AR (1100) - Service 2  ₹1,500  [fully paid]
Cr: AR (1100) - Package 1  ₹500    [partially paid]
Dr: Cash (1000)            ₹4,000

✅ Clear tracking: Services 1 & 2 fully paid, Package 1 has ₹5,400 outstanding
```

---

## 🗂️ Implementation Components

### 1. Database Changes

#### Add Column to `ar_subledger` Table

**Migration File**: `migrations/add_line_item_reference_to_ar_subledger.sql`

```sql
-- Add reference to invoice line item for detailed payment tracking
ALTER TABLE ar_subledger
ADD COLUMN reference_line_item_id UUID REFERENCES invoice_line_item(line_item_id);

-- Add index for performance
CREATE INDEX idx_ar_subledger_line_item
ON ar_subledger(reference_line_item_id)
WHERE reference_line_item_id IS NOT NULL;

-- Add comment
COMMENT ON COLUMN ar_subledger.reference_line_item_id IS
'Reference to specific invoice line item for payment allocation tracking. Enables service-first payment allocation rule.';
```

**Schema After Change**:
```python
# app/models/transaction.py - ARSubledger model
class ARSubledger(db.Model, TimestampMixin, TenantMixin):
    __tablename__ = 'ar_subledger'

    entry_id = db.Column(db.String(36), primary_key=True)
    hospital_id = db.Column(db.String(36), db.ForeignKey('hospital.hospital_id'))
    patient_id = db.Column(db.String(36), db.ForeignKey('patient.patient_id'))

    reference_type = db.Column(db.String(50))  # 'invoice', 'payment', 'credit_note'
    reference_id = db.Column(db.String(36))
    reference_line_item_id = db.Column(db.String(36), db.ForeignKey('invoice_line_item.line_item_id'))  # NEW

    entry_date = db.Column(db.Date)
    entry_type = db.Column(db.String(20))  # 'debit', 'credit'
    debit_amount = db.Column(db.Numeric(12, 2))
    credit_amount = db.Column(db.Numeric(12, 2))
    current_balance = db.Column(db.Numeric(12, 2))
    description = db.Column(db.Text)
```

---

### 2. Service Layer Changes

#### 2.1 AR Subledger Service (`app/services/subledger_service.py`)

**Update**: `create_ar_entry()` method to accept `reference_line_item_id`

```python
def create_ar_entry(
    self,
    hospital_id: str,
    patient_id: str,
    reference_type: str,
    reference_id: str,
    entry_date: date,
    entry_type: str,
    amount: Decimal,
    description: str,
    branch_id: Optional[str] = None,
    reference_line_item_id: Optional[str] = None  # NEW PARAMETER
) -> Dict[str, Any]:
    """
    Create AR subledger entry (debit or credit)

    New Parameter:
        reference_line_item_id: UUID of invoice line item for detailed tracking
    """
    # ... existing code ...

    ar_entry = ARSubledger(
        entry_id=entry_id,
        hospital_id=hospital_id,
        branch_id=branch_id,
        patient_id=patient_id,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_line_item_id=reference_line_item_id,  # NEW
        entry_date=entry_date,
        entry_type=entry_type,
        debit_amount=amount if entry_type == 'debit' else Decimal('0.00'),
        credit_amount=amount if entry_type == 'credit' else Decimal('0.00'),
        current_balance=new_balance,
        description=description,
        # ... other fields ...
    )
```

**Add New Method**: `get_line_item_ar_balance()`

```python
def get_line_item_ar_balance(
    self,
    hospital_id: str,
    patient_id: str,
    line_item_id: str
) -> Decimal:
    """
    Get AR balance for a specific invoice line item

    Returns:
        Outstanding balance for this line item (positive = amount owed)
    """
    with get_db_session() as session:
        entries = session.query(ARSubledger).filter(
            ARSubledger.hospital_id == hospital_id,
            ARSubledger.patient_id == patient_id,
            ARSubledger.reference_line_item_id == line_item_id
        ).all()

        balance = Decimal('0.00')
        for entry in entries:
            if entry.entry_type == 'debit':
                balance += entry.debit_amount or Decimal('0.00')
            elif entry.entry_type == 'credit':
                balance -= entry.credit_amount or Decimal('0.00')

        return balance
```

---

#### 2.2 Billing Service (`app/services/billing_service.py`)

**Update**: Invoice creation AR posting logic

**Current Code** (WRONG):
```python
# Single AR entry for entire invoice
ar_result = ar_service.create_ar_entry(
    hospital_id=hospital_id,
    patient_id=invoice.patient_id,
    reference_type='invoice',
    reference_id=str(invoice.invoice_id),
    entry_date=invoice.invoice_date,
    entry_type='debit',
    amount=invoice.invoice_total,  # ❌ Entire invoice amount
    description=f'Invoice {invoice.invoice_number}'
)
```

**New Code** (CORRECT):
```python
# Create AR entry for EACH line item
from app.models.transaction import InvoiceLineItem

line_items = session.query(InvoiceLineItem).filter(
    InvoiceLineItem.invoice_id == invoice.invoice_id
).all()

ar_entry_ids = []
for line_item in line_items:
    # Determine description based on item type
    if line_item.item_type == 'Service':
        description = f'Invoice {invoice.invoice_number} - Service: {line_item.item_name}'
    elif line_item.item_type == 'Package':
        description = f'Invoice {invoice.invoice_number} - Package: {line_item.item_name}'
    else:
        description = f'Invoice {invoice.invoice_number} - {line_item.item_name}'

    # Create separate AR entry for this line item
    ar_result = ar_service.create_ar_entry(
        hospital_id=hospital_id,
        patient_id=invoice.patient_id,
        reference_type='invoice',
        reference_id=str(invoice.invoice_id),
        reference_line_item_id=str(line_item.line_item_id),  # ✅ Line item reference
        entry_date=invoice.invoice_date,
        entry_type='debit',
        amount=line_item.line_total,  # ✅ Line item amount
        description=description
    )

    if ar_result['success']:
        ar_entry_ids.append(ar_result['entry_id'])
        logger.info(f"AR entry created for line item {line_item.line_item_id}: ₹{line_item.line_total}")
    else:
        logger.error(f"Failed to create AR entry for line item {line_item.line_item_id}")

logger.info(f"✓ Created {len(ar_entry_ids)} AR entries for invoice {invoice.invoice_number}")
```

---

#### 2.3 Patient Payment Service (NEW or update existing)

**File**: `app/services/patient_payment_service.py` (create if doesn't exist)

**Method**: `record_payment_with_allocation()`

```python
def record_payment_with_allocation(
    self,
    hospital_id: str,
    patient_id: str,
    invoice_id: str,
    payment_amount: Decimal,
    payment_date: date,
    payment_method: str,
    branch_id: Optional[str] = None,
    user_id: Optional[str] = None
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
    try:
        with get_db_session() as session:
            from app.models.transaction import InvoiceHeader, InvoiceLineItem
            from sqlalchemy import case

            # Get invoice
            invoice = session.query(InvoiceHeader).filter(
                InvoiceHeader.invoice_id == invoice_id
            ).first()

            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Get line items ordered by priority (Services first, then Packages)
            line_items = session.query(InvoiceLineItem).filter(
                InvoiceLineItem.invoice_id == invoice_id
            ).order_by(
                case(
                    (InvoiceLineItem.item_type == 'Service', 1),
                    else_=2
                ),
                InvoiceLineItem.line_item_id
            ).all()

            # Allocate payment across line items
            remaining_payment = payment_amount
            allocation_details = []
            ar_entry_ids = []

            ar_service = ARSubledgerService()

            for item in line_items:
                if remaining_payment <= 0:
                    break

                # Get current AR balance for this line item
                line_item_balance = ar_service.get_line_item_ar_balance(
                    hospital_id=hospital_id,
                    patient_id=patient_id,
                    line_item_id=str(item.line_item_id)
                )

                if line_item_balance <= 0:
                    continue  # Already paid

                # Allocate payment to this line item
                allocated = min(line_item_balance, remaining_payment)

                # Create AR credit entry
                ar_result = ar_service.create_ar_entry(
                    hospital_id=hospital_id,
                    patient_id=patient_id,
                    reference_type='payment',
                    reference_id='<payment_id>',  # Will be updated
                    reference_line_item_id=str(item.line_item_id),
                    entry_date=payment_date,
                    entry_type='credit',
                    amount=allocated,
                    description=f'Payment for {item.item_name}',
                    branch_id=branch_id
                )

                if ar_result['success']:
                    ar_entry_ids.append(ar_result['entry_id'])
                    allocation_details.append({
                        'line_item_id': str(item.line_item_id),
                        'item_type': item.item_type,
                        'item_name': item.item_name,
                        'line_total': float(item.line_total),
                        'allocated': float(allocated),
                        'remaining_balance': float(line_item_balance - allocated)
                    })

                    remaining_payment -= allocated
                    logger.info(f"Allocated ₹{allocated} to {item.item_type}: {item.item_name}")

            # Update invoice paid_amount
            invoice.paid_amount = (invoice.paid_amount or Decimal('0.00')) + payment_amount
            session.commit()

            return {
                'success': True,
                'payment_amount': float(payment_amount),
                'allocation': allocation_details,
                'ar_entries': ar_entry_ids,
                'unallocated': float(remaining_payment)
            }

    except Exception as e:
        logger.error(f"Error recording payment with allocation: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}
```

---

#### 2.4 Package Payment Service (`app/services/package_payment_service.py`)

**Update**: `_calculate_package_allocated_payment()` to use AR entries

**Current Code**: Uses `invoice.paid_amount` and allocates in-memory

**New Code**: Query actual AR entries for the package line item

```python
def _calculate_package_allocated_payment(
    self,
    session,
    invoice_id: str,
    package_id: str
) -> Decimal:
    """
    Calculate allocated payment for a specific package from AR entries

    Uses actual AR postings (more accurate than in-memory calculation)
    """
    try:
        from app.services.subledger_service import ARSubledgerService

        # Find the line item for this package
        line_item = session.query(InvoiceLineItem).filter(
            InvoiceLineItem.invoice_id == invoice_id,
            InvoiceLineItem.package_id == package_id,
            InvoiceLineItem.item_type == 'Package'
        ).first()

        if not line_item:
            logger.warning(f"Package {package_id} not found in invoice {invoice_id}")
            return Decimal('0.00')

        # Get AR balance for this line item
        ar_service = ARSubledgerService()

        # Calculate total debits and credits
        entries = session.query(ARSubledger).filter(
            ARSubledger.reference_line_item_id == str(line_item.line_item_id)
        ).all()

        total_debits = sum(e.debit_amount or Decimal('0.00') for e in entries)
        total_credits = sum(e.credit_amount or Decimal('0.00') for e in entries)

        # Paid amount = credits (payments reduce AR)
        paid_amount = total_credits

        logger.info(f"Package {package_id} AR: Debits=₹{total_debits}, Credits=₹{total_credits}, Paid=₹{paid_amount}")

        return paid_amount

    except Exception as e:
        logger.error(f"Error getting package allocated payment from AR: {str(e)}", exc_info=True)
        return Decimal('0.00')
```

---

### 3. Model Updates

**File**: `app/models/transaction.py`

**Update**: `ARSubledger` model

```python
class ARSubledger(db.Model, TimestampMixin, TenantMixin):
    """
    Accounts Receivable Subledger

    Tracks patient-level receivables with line-item detail for payment allocation
    """
    __tablename__ = 'ar_subledger'

    entry_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hospital_id = db.Column(db.String(36), db.ForeignKey('hospital.hospital_id'), nullable=False)
    branch_id = db.Column(db.String(36), db.ForeignKey('branch.branch_id'))
    patient_id = db.Column(db.String(36), db.ForeignKey('patient.patient_id'), nullable=False)

    reference_type = db.Column(db.String(50))  # 'invoice', 'payment', 'credit_note', 'adjustment'
    reference_id = db.Column(db.String(36))
    reference_line_item_id = db.Column(db.String(36), db.ForeignKey('invoice_line_item.line_item_id'))  # NEW

    entry_date = db.Column(db.Date, nullable=False)
    entry_type = db.Column(db.String(20), nullable=False)  # 'debit', 'credit'
    debit_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    credit_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    current_balance = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))
    description = db.Column(db.Text)

    # Relationships
    patient = db.relationship('Patient', backref='ar_entries', lazy='joined')
    line_item = db.relationship('InvoiceLineItem', backref='ar_entries', lazy='joined')  # NEW
```

---

## 🧪 Testing Plan

### Test Case 1: Mixed Invoice with Partial Payment

**Setup**:
```sql
-- Create invoice with services and package
INSERT INTO invoice_line_item (line_item_id, invoice_id, item_type, item_name, quantity, unit_price, line_total)
VALUES
  ('line1', 'inv123', 'Service', 'Consultation', 1, 2000, 2000),
  ('line2', 'inv123', 'Service', 'Lab Test', 1, 1500, 1500),
  ('line3', 'inv123', 'Package', 'Hair Restoration', 1, 5900, 5900);
```

**Expected AR Entries on Invoice Creation**:
```sql
SELECT
    reference_line_item_id,
    entry_type,
    debit_amount,
    description
FROM ar_subledger
WHERE reference_id = 'inv123'
ORDER BY created_at;

-- Expected:
-- line1, debit, 2000, 'Invoice INV-123 - Service: Consultation'
-- line2, debit, 1500, 'Invoice INV-123 - Service: Lab Test'
-- line3, debit, 5900, 'Invoice INV-123 - Package: Hair Restoration'
```

**Record Payment**: ₹4,000

**Expected AR Entries on Payment**:
```sql
-- Expected allocation (Services first):
-- line1, credit, 2000 (fully paid)
-- line2, credit, 1500 (fully paid)
-- line3, credit, 500  (partially paid)
```

**Verify Line Item Balances**:
```sql
SELECT
    il.item_name,
    il.line_total,
    COALESCE(SUM(CASE WHEN ar.entry_type = 'debit' THEN ar.debit_amount ELSE 0 END), 0) as total_debit,
    COALESCE(SUM(CASE WHEN ar.entry_type = 'credit' THEN ar.credit_amount ELSE 0 END), 0) as total_credit,
    COALESCE(SUM(CASE WHEN ar.entry_type = 'debit' THEN ar.debit_amount ELSE 0 END), 0) -
    COALESCE(SUM(CASE WHEN ar.entry_type = 'credit' THEN ar.credit_amount ELSE 0 END), 0) as balance
FROM invoice_line_item il
LEFT JOIN ar_subledger ar ON ar.reference_line_item_id = il.line_item_id
WHERE il.invoice_id = 'inv123'
GROUP BY il.line_item_id, il.item_name, il.line_total;

-- Expected:
-- Consultation:      line_total=2000, balance=0    (fully paid)
-- Lab Test:          line_total=1500, balance=0    (fully paid)
-- Hair Restoration:  line_total=5900, balance=5400 (partially paid)
```

### Test Case 2: Package Plan Creation with Allocated Payment

**Create Package Plan**:
```python
plan_data = {
    'invoice_id': 'inv123',
    'package_id': 'pkg_hair_restoration',
    'total_amount': 5900,
    # ... other fields
}

result = package_service.create(plan_data, hospital_id, branch_id)
```

**Expected**:
```python
# Plan should have paid_amount = 500 (not 4000)
plan.paid_amount == Decimal('500.00')  # Only what was allocated to this package
plan.balance_amount == Decimal('5400.00')
```

**Verify Logs**:
```
Package pkg_hair_restoration AR: Debits=₹5900, Credits=₹500, Paid=₹500
✓ Package plan created with paid_amount: ₹500
```

---

## 📊 Database Verification Queries

### Query 1: AR Balance by Line Item
```sql
WITH line_item_ar AS (
    SELECT
        il.line_item_id,
        il.invoice_id,
        ih.invoice_number,
        il.item_type,
        il.item_name,
        il.line_total,
        COALESCE(SUM(CASE WHEN ar.entry_type = 'debit' THEN ar.debit_amount ELSE 0 END), 0) as total_debit,
        COALESCE(SUM(CASE WHEN ar.entry_type = 'credit' THEN ar.credit_amount ELSE 0 END), 0) as total_credit
    FROM invoice_line_item il
    JOIN invoice_header ih ON ih.invoice_id = il.invoice_id
    LEFT JOIN ar_subledger ar ON ar.reference_line_item_id = il.line_item_id
    WHERE ih.patient_id = '<patient_id>'
    GROUP BY il.line_item_id, il.invoice_id, ih.invoice_number, il.item_type, il.item_name, il.line_total
)
SELECT
    invoice_number,
    item_type,
    item_name,
    line_total,
    total_debit,
    total_credit,
    (total_debit - total_credit) as outstanding_balance,
    CASE
        WHEN (total_debit - total_credit) = 0 THEN 'Paid'
        WHEN total_credit = 0 THEN 'Unpaid'
        ELSE 'Partial'
    END as payment_status
FROM line_item_ar
ORDER BY invoice_number, item_type, item_name;
```

### Query 2: Payment Allocation Report
```sql
SELECT
    ih.invoice_number,
    ih.invoice_date,
    ih.invoice_total,
    il.item_type,
    il.item_name,
    il.line_total,
    COALESCE(SUM(CASE WHEN ar.reference_type = 'payment' THEN ar.credit_amount ELSE 0 END), 0) as allocated_payment,
    il.line_total - COALESCE(SUM(CASE WHEN ar.reference_type = 'payment' THEN ar.credit_amount ELSE 0 END), 0) as remaining_balance
FROM invoice_header ih
JOIN invoice_line_item il ON il.invoice_id = ih.invoice_id
LEFT JOIN ar_subledger ar ON ar.reference_line_item_id = il.line_item_id
WHERE ih.invoice_id = '<invoice_id>'
GROUP BY ih.invoice_number, ih.invoice_date, ih.invoice_total, il.item_type, il.item_name, il.line_total
ORDER BY
    CASE WHEN il.item_type = 'Service' THEN 1 ELSE 2 END,
    il.line_item_id;
```

---

## 🚀 Deployment Steps

1. **Backup Database**:
   ```bash
   pg_dump -h localhost -U postgres -d skinspire_dev > backups/pre_line_item_ar_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Run Migration**:
   ```bash
   psql -h localhost -U postgres -d skinspire_dev -f migrations/add_line_item_reference_to_ar_subledger.sql
   ```

3. **Update Models**:
   - Commit model changes in `app/models/transaction.py`

4. **Update Services** (in order):
   - `subledger_service.py` (add reference_line_item_id parameter)
   - `billing_service.py` (update AR posting logic)
   - `patient_payment_service.py` (create/update with allocation logic)
   - `package_payment_service.py` (update to use AR entries)

5. **Test with Sample Data**:
   - Create mixed invoice
   - Record partial payment
   - Verify allocation
   - Create package plan
   - Verify paid_amount

6. **Deploy to Test Environment**: Test thoroughly before production

---

## 📋 Checklist

- [ ] Database migration created and tested
- [ ] ARSubledger model updated with new column
- [ ] ARSubledgerService updated with reference_line_item_id parameter
- [ ] ARSubledgerService.get_line_item_ar_balance() method added
- [ ] Billing service updated to create per-line-item AR entries
- [ ] Patient payment service created/updated with allocation logic
- [ ] Package payment service updated to use AR entries
- [ ] Test Case 1 verified (mixed invoice, partial payment)
- [ ] Test Case 2 verified (package plan with allocated payment)
- [ ] Database verification queries tested
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] Deployed to test environment
- [ ] User acceptance testing completed

---

## 📝 Benefits

1. **Accurate Payment Allocation**: Services paid first, then packages
2. **Clear AR Tracking**: Know exactly what line items are paid/outstanding
3. **Standard Accounting**: Follows proper AR subledger practices
4. **Refund Clarity**: Credit notes can reference specific line items
5. **Aging Reports**: Can show aging by service type vs packages
6. **Audit Trail**: Complete payment history per line item
7. **Package Plan Accuracy**: Paid amount reflects actual allocated payment

---

**Document Version**: 1.0
**Created**: 2025-11-12
**Status**: Implementation in progress
