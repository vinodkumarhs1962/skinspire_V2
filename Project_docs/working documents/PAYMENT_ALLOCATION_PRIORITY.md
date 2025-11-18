# Payment Allocation Priority - Business Rule

**Date**: 2025-11-12
**Status**: ✅ IMPLEMENTED

---

## 🎯 Business Rule

**Payment Allocation Priority**:
```
1. Services (Highest Priority)
2. Medicines (Second Priority)
3. Packages (Lowest Priority)
```

---

## 📖 Rationale

### User's Business Insight:
> "Individual services and medicines are point-of-sale items. Packages will most likely have installments, it will be easy to collect."

### Priority Breakdown:

#### **Priority 1: Services** (Consultations, Lab Tests, Procedures)
- ✅ Already delivered at point-of-sale
- ✅ Cannot be "un-delivered"
- ✅ One-time service, no future sessions
- ✅ Must be paid upfront

**Examples**: Consultation, Blood Test, X-Ray, Minor Procedures

---

#### **Priority 2: Medicines** (Inventory Items)
- ✅ Already dispensed at point-of-sale
- ✅ Stock has left inventory (cannot return easily)
- ✅ COGS already posted
- ✅ Physical goods handed over to patient
- ✅ Must be paid upfront

**Examples**: Tablets, Syrup, Ointments, Injections

---

#### **Priority 3: Packages** (Treatment Plans)
- ⏰ Multi-session delivery over time
- ⏰ Have installment payment plans
- ⏰ Easier to collect over longer period
- ⏰ Can adjust remaining sessions if needed

**Examples**: Hair Restoration Package (6 sessions), Skin Treatment (12 sessions)

---

## 💰 Example Scenario

### Invoice Breakdown:
```
Invoice #GST/2025-2026/00123
Date: 2025-11-12
Patient: John Doe

Line Items:
1. Consultation               ₹2,000  [Service]
2. Blood Test                 ₹1,500  [Service]
3. Paracetamol 500mg (30tab)  ₹300    [Medicine]
4. Skin Whitening Cream       ₹500    [Medicine]
5. Hair Restoration (6 sess)  ₹5,900  [Package]
─────────────────────────────────────
Invoice Total:                ₹10,200
```

### Scenario A: Full Payment
```
Payment Received: ₹10,200

Allocation:
1. Consultation:     ₹2,000 ✅ PAID
2. Blood Test:       ₹1,500 ✅ PAID
3. Paracetamol:      ₹300   ✅ PAID
4. Skin Cream:       ₹500   ✅ PAID
5. Hair Package:     ₹5,900 ✅ PAID

Remaining Payment: ₹0
```

**AR Entries Created**:
```sql
-- Services paid
Cr: AR (1100) - Consultation     ₹2,000 [line_item_id_1]
Cr: AR (1100) - Blood Test        ₹1,500 [line_item_id_2]

-- Medicines paid
Cr: AR (1100) - Paracetamol      ₹300   [line_item_id_3]
Cr: AR (1100) - Skin Cream        ₹500   [line_item_id_4]

-- Package paid
Cr: AR (1100) - Hair Package      ₹5,900 [line_item_id_5]

Dr: Cash (1000)                   ₹10,200
```

---

### Scenario B: Partial Payment (₹4,000)
```
Payment Received: ₹4,000

Allocation (Priority: Services → Medicines → Packages):
1. Consultation:     ₹2,000 ✅ PAID (remaining: ₹2,000)
2. Blood Test:       ₹1,500 ✅ PAID (remaining: ₹500)
3. Paracetamol:      ₹300   ✅ PAID (remaining: ₹200)
4. Skin Cream:       ₹200   ⚠️ PARTIAL (remaining: ₹0)
5. Hair Package:     ₹0     ❌ UNPAID

Remaining Payment: ₹0
```

**AR Entries Created**:
```sql
-- Services fully paid (Priority 1)
Cr: AR (1100) - Consultation     ₹2,000 [line_item_id_1]
Cr: AR (1100) - Blood Test        ₹1,500 [line_item_id_2]

-- Medicines paid (Priority 2)
Cr: AR (1100) - Paracetamol      ₹300   [line_item_id_3]
Cr: AR (1100) - Skin Cream        ₹200   [line_item_id_4] (partial)

-- Package unpaid (Priority 3)
-- No credit entry for package

Dr: Cash (1000)                   ₹4,000
```

**Outstanding Balances**:
```
1. Consultation:     ₹0       (paid)
2. Blood Test:       ₹0       (paid)
3. Paracetamol:      ₹0       (paid)
4. Skin Cream:       ₹300     (₹500 - ₹200 = ₹300 outstanding)
5. Hair Package:     ₹5,900   (fully outstanding)
──────────────────────────────
Total Outstanding:   ₹6,200
```

---

### Scenario C: Partial Payment (₹5,000)
```
Payment Received: ₹5,000

Allocation (Priority: Services → Medicines → Packages):
1. Consultation:     ₹2,000 ✅ PAID (remaining: ₹3,000)
2. Blood Test:       ₹1,500 ✅ PAID (remaining: ₹1,500)
3. Paracetamol:      ₹300   ✅ PAID (remaining: ₹1,200)
4. Skin Cream:       ₹500   ✅ PAID (remaining: ₹700)
5. Hair Package:     ₹700   ⚠️ PARTIAL (remaining: ₹0)

Remaining Payment: ₹0
```

**AR Entries Created**:
```sql
-- All services paid (Priority 1)
Cr: AR (1100) - Consultation     ₹2,000 [line_item_id_1]
Cr: AR (1100) - Blood Test        ₹1,500 [line_item_id_2]

-- All medicines paid (Priority 2)
Cr: AR (1100) - Paracetamol      ₹300   [line_item_id_3]
Cr: AR (1100) - Skin Cream        ₹500   [line_item_id_4]

-- Package partially paid (Priority 3)
Cr: AR (1100) - Hair Package      ₹700   [line_item_id_5]

Dr: Cash (1000)                   ₹5,000
```

**Outstanding Balances**:
```
1. Consultation:     ₹0       (paid)
2. Blood Test:       ₹0       (paid)
3. Paracetamol:      ₹0       (paid)
4. Skin Cream:       ₹0       (paid)
5. Hair Package:     ₹5,200   (₹5,900 - ₹700 = ₹5,200 outstanding)
──────────────────────────────
Total Outstanding:   ₹5,200
```

**Package Plan Creation**:
```python
# When creating package payment plan for Hair Restoration
package_plan = {
    'total_amount': 5900.00,
    'paid_amount': 700.00,        # Allocated from invoice payment
    'balance_amount': 5200.00,    # Outstanding
    'installment_count': 5,
    'installment_amount': 1040.00 # ₹5,200 / 5 = ₹1,040 per installment
}
```

---

## 🔧 Implementation

### Code Location:
- **File**: `app/services/package_payment_service.py`
- **Method**: `_calculate_package_allocated_payment()`
- **Lines**: 1827-1843 (ordering), 1855-1884 (allocation logic)

### SQLAlchemy Query:
```python
from sqlalchemy import case

line_items = session.query(InvoiceLineItem).filter(
    InvoiceLineItem.invoice_id == invoice_id
).order_by(
    # Priority: 1=Services, 2=Medicines, 3=Packages
    case(
        (InvoiceLineItem.item_type == 'Service', 1),
        (InvoiceLineItem.item_type == 'Medicine', 2),
        (InvoiceLineItem.item_type == 'Package', 3),
        else_=4
    ),
    InvoiceLineItem.line_item_id
).all()
```

### Allocation Logic:
```python
for item in line_items:
    if remaining_payment <= 0:
        break

    item_total = item.line_total or Decimal('0.00')

    if item.item_type == 'Service':
        # Priority 1: Services paid first
        allocated = min(item_total, remaining_payment)
        remaining_payment -= allocated

    elif item.item_type == 'Medicine':
        # Priority 2: Medicines paid second
        allocated = min(item_total, remaining_payment)
        remaining_payment -= allocated

    elif item.item_type == 'Package':
        # Priority 3: Packages paid last
        allocated = min(item_total, remaining_payment)
        remaining_payment -= allocated
```

---

## 📊 Impact on Other Modules

### 1. **AR Subledger Service**
- ✅ Updated to support `reference_line_item_id`
- ✅ New method `get_line_item_ar_balance()` added
- **Status**: Complete

### 2. **Billing Service** ⏳
- ⏳ Need to update AR posting to create per-line-item entries
- ⏳ Each line item gets its own AR debit entry
- **Status**: Pending

### 3. **Patient Payment Service** ⏳
- ⏳ Need to implement `record_payment_with_allocation()`
- ⏳ Use priority logic to allocate payments
- **Status**: Pending

### 4. **Package Payment Service**
- ✅ `_calculate_package_allocated_payment()` updated
- ✅ Priority logic implemented
- **Status**: Complete

---

## 🧪 Testing Checklist

- [ ] Create mixed invoice (services + medicines + packages)
- [ ] Verify AR entries created per line item
- [ ] Record partial payment (₹4,000 scenario)
- [ ] Verify allocation follows priority (S→M→P)
- [ ] Check line item balances using `get_line_item_ar_balance()`
- [ ] Create package plan from partially paid invoice
- [ ] Verify `paid_amount` reflects allocated payment only
- [ ] Test full payment scenario
- [ ] Test zero payment scenario
- [ ] Generate AR aging report by item type

---

## 📈 Business Benefits

### 1. **Cash Flow Management**
- Point-of-sale items collected first
- Reduces risk of non-payment for delivered services
- Packages have longer collection period

### 2. **Inventory Control**
- Medicines paid promptly after dispensing
- Reduces inventory AR exposure
- COGS matched with revenue collection

### 3. **Clear Patient Communication**
```
Patient Statement:
"Your payment of ₹4,000 has been allocated as follows:
✓ Consultation: ₹2,000 - Paid in full
✓ Blood Test: ₹1,500 - Paid in full
✓ Paracetamol: ₹300 - Paid in full
⚠ Skin Cream: ₹200 paid, ₹300 outstanding
⚠ Hair Package: ₹5,900 outstanding (installment plan available)"
```

### 4. **Accurate Reporting**
- AR aging by item type
- Collection efficiency by category
- Outstanding analysis: Services vs Medicines vs Packages

---

## 📝 Related Documents

- `LINE_ITEM_AR_SPLITTING_IMPLEMENTATION.md` - Complete implementation plan
- `LINE_ITEM_AR_PROGRESS_UPDATE.md` - Progress tracking
- `PACKAGE_PLAN_PAID_AMOUNT_FIX.md` - Original paid_amount issue
- `DISCONTINUATION_BUSINESS_LOGIC_FIX.md` - Credit note logic

---

**Document Version**: 1.0
**Created**: 2025-11-12
**Priority**: Services → Medicines → Packages
**Status**: ✅ Priority Logic Implemented, ⏳ Full Integration Pending
