# Package Discontinuation - Impact on Invoice Line Items
**Date**: 2025-01-13
**Topic**: How discontinuation affects invoices and line items

## Your Question

> "Will discontinuation change the status of plan as discontinued? It should also change invoice line item also. How do we reflect it? Will it be just a discontinuation status flag? We may have composite invoice with service line item also. So we can not discontinue whole invoice. Will there be any changes in invoice line item?"

## Answer: Invoice Immutability Principle ✅

### **Do NOT modify invoice line items** - This is the correct accounting approach!

## Current Implementation (Already Correct!)

### What Changes During Discontinuation

**1. PackagePaymentPlan Status ✅**
```python
plan.status = 'discontinued'  # ✅ Changed
plan.discontinued_at = datetime.utcnow()
plan.discontinued_by = user_id
plan.discontinuation_reason = reason
plan.refund_amount = credit_note_amount
plan.refund_status = 'pending' or 'approved'
plan.credit_note_id = credit_note.credit_note_id  # Link to credit note
```

**Location**: `app/services/package_payment_service.py:2018-2033`

**2. Credit Note Created ✅**
```python
credit_note = PatientCreditNote(
    credit_note_number='CN/2025-2026/00001',
    original_invoice_id=plan.invoice_id,  # ✅ Links back to invoice
    plan_id=plan.plan_id,
    total_amount=refund_amount,
    reason_code='plan_discontinued',
    reason_description=discontinuation_reason
)
```

**3. AR/GL Reversal ✅**
- AR Subledger: Credit entry (reduces patient receivable)
- GL Entries: Dr Revenue, Cr AR (reverses original revenue recognition)

### What Does NOT Change (By Design!)

**InvoiceLineItem - Remains Unchanged ✅**
```python
# Original invoice line item is NOT modified
# No status field on invoice_line_item
# No discontinuation flag
# Invoice remains immutable
```

## Why Invoice Line Items Should NOT Be Modified

### Accounting Principle: Invoice Immutability

**GAAP/IFRS Requirement**: Once an invoice is posted, it should remain immutable for audit purposes.

### ✅ Correct Approach: Use Credit Notes

```
Original Invoice (Immutable)
├─ Line Item 1: Consultation Service  ₹2,000  (Active)
├─ Line Item 2: Laser Package         ₹50,000 (Paid ₹42,448)
└─ Line Item 3: Medicine              ₹500    (Active)

Package Discontinued → Create Credit Note
Credit Note CN/2025-2026/00001
└─ Reverses: ₹7,552 (for discontinued package)

Net Effect:
- Original invoice: ₹52,500 (unchanged)
- Credit note: -₹7,552
- Net patient liability: ₹44,948
```

### ❌ Wrong Approach: Modify Line Item

```
Original Invoice (MUTATED - breaks audit trail)
├─ Line Item 1: Consultation Service  ₹2,000  (Active)
├─ Line Item 2: Laser Package         ₹50,000 ❌ Status: Discontinued
└─ Line Item 3: Medicine              ₹500    (Active)

Problems:
❌ Changes historical document
❌ Breaks audit trail
❌ Compliance issues
❌ What if invoice was already printed?
```

## How to Check if a Package Line Item is Discontinued

### Method 1: Query via PackagePaymentPlan ✅

```python
# Find if this invoice line item's package was discontinued
line_item = InvoiceLineItem(package_id='xyz')

# Check via package payment plan
plan = session.query(PackagePaymentPlan).filter(
    PackagePaymentPlan.invoice_id == line_item.invoice_id,
    PackagePaymentPlan.package_id == line_item.package_id
).first()

if plan and plan.status == 'discontinued':
    # This line item's package was discontinued
    credit_note_number = plan.credit_note.credit_note_number if plan.credit_note else None
    refund_amount = plan.refund_amount
    reason = plan.discontinuation_reason
```

### Method 2: Check for Credit Notes Against Invoice ✅

```sql
-- Find all credit notes for an invoice
SELECT
    cn.credit_note_number,
    cn.total_amount,
    cn.reason_description,
    cn.plan_id,
    ppp.package_name
FROM patient_credit_notes cn
LEFT JOIN package_payment_plans ppp ON cn.plan_id = ppp.plan_id
WHERE cn.original_invoice_id = 'invoice_id_here'
    AND cn.reason_code = 'plan_discontinued';
```

### Method 3: View with Discontinuation Status (Recommended) ✅

Create a database view that combines invoice line items with package status:

```sql
CREATE OR REPLACE VIEW invoice_line_items_with_status AS
SELECT
    ili.*,
    ppp.plan_id,
    ppp.status AS package_plan_status,
    ppp.discontinued_at,
    ppp.discontinuation_reason,
    ppp.refund_amount AS package_refund_amount,
    cn.credit_note_id,
    cn.credit_note_number,
    cn.total_amount AS credit_note_amount,
    CASE
        WHEN ppp.status = 'discontinued' THEN true
        ELSE false
    END AS is_package_discontinued
FROM invoice_line_item ili
LEFT JOIN package_payment_plans ppp
    ON ili.invoice_id = ppp.invoice_id
    AND ili.package_id = ppp.package_id
LEFT JOIN patient_credit_notes cn
    ON cn.plan_id = ppp.plan_id
    AND cn.reason_code = 'plan_discontinued';
```

**Benefits**:
- Non-invasive (doesn't modify base tables)
- Easy to query
- Shows discontinuation status without modifying invoice

## Handling Composite Invoices

### Your Scenario: Invoice with Multiple Line Items

```
Invoice #INV-001  (Total: ₹52,500)
├─ Line Item 1: Hair Consultation       ₹2,000    [Service]
├─ Line Item 2: Laser Hair Package      ₹50,000   [Package]
└─ Line Item 3: Hair Vitamin Medicine   ₹500      [Medicine]
```

### When Package is Discontinued

```
Original Invoice: ₹52,500 (UNCHANGED)
├─ Line Item 1: Hair Consultation       ₹2,000    [Service] ✅ Active
├─ Line Item 2: Laser Hair Package      ₹50,000   [Package] 🟡 Plan Discontinued
└─ Line Item 3: Hair Vitamin Medicine   ₹500      [Medicine] ✅ Active

Credit Note: CN/2025-2026/00001 (₹7,552)
└─ Reason: "Package discontinued - Patient allergic reaction"

Net Amounts:
- Service: ₹2,000 (full - active)
- Package: ₹42,448 (₹50,000 - ₹7,552 credit note)
- Medicine: ₹500 (full - active)
- Total Net: ₹44,948
```

### How to Display in UI

**Invoice Detail Page**:
```html
<!-- Show original invoice unchanged -->
<table>
  <tr>
    <td>Hair Consultation</td>
    <td>₹2,000</td>
    <td><span class="badge-success">Active</span></td>
  </tr>
  <tr>
    <td>Laser Hair Package (5 sessions)</td>
    <td>₹50,000</td>
    <td>
      <span class="badge-warning">Discontinued</span>
      <small>See Credit Note: CN/2025-2026/00001</small>
    </td>
  </tr>
  <tr>
    <td>Hair Vitamin Medicine</td>
    <td>₹500</td>
    <td><span class="badge-success">Active</span></td>
  </tr>
</table>

<!-- Show credit notes separately -->
<h3>Related Credit Notes</h3>
<table>
  <tr>
    <td>CN/2025-2026/00001</td>
    <td>Package Discontinued</td>
    <td>-₹7,552</td>
  </tr>
</table>

<!-- Show net amount -->
<p><strong>Original Invoice Total:</strong> ₹52,500</p>
<p><strong>Credit Notes:</strong> -₹7,552</p>
<p><strong>Net Amount:</strong> ₹44,948</p>
```

## Database Relationships

### Current Schema (Already Correct!) ✅

```
invoice_header (id: invoice_id)
├─ invoice_line_item (invoice_id, package_id)  [IMMUTABLE]
│
package_payment_plans (invoice_id, package_id, status)
├─ status: 'active' | 'completed' | 'discontinued'
├─ discontinued_at, discontinued_by, discontinuation_reason
├─ credit_note_id → patient_credit_notes
│
patient_credit_notes (original_invoice_id, plan_id)
├─ credit_note_number: 'CN/YYYY-YYYY/NNNNN'
├─ total_amount: refund amount
├─ reason_code: 'plan_discontinued'
│
ar_subledger (reference_type='credit_note')
└─ credit_amount: reduces AR balance

gl_transactions (source_document_type='credit_note')
└─ GL Entries:
   ├─ Dr: Package Revenue (reduce income)
   └─ Cr: Accounts Receivable (reduce AR)
```

## Querying Package Discontinuation Status

### In Python (Service Layer)

```python
def get_invoice_with_discontinuation_status(invoice_id, hospital_id):
    """Get invoice with package discontinuation status"""

    with get_db_session() as session:
        # Get invoice with line items
        invoice = session.query(InvoiceHeader).filter(
            InvoiceHeader.invoice_id == invoice_id
        ).first()

        line_items = []
        for item in invoice.line_items:
            item_dict = to_dict(item)

            # Check if this is a package line item
            if item.package_id:
                # Find package payment plan
                plan = session.query(PackagePaymentPlan).filter(
                    PackagePaymentPlan.invoice_id == invoice_id,
                    PackagePaymentPlan.package_id == item.package_id
                ).first()

                if plan:
                    item_dict['package_plan_status'] = plan.status
                    item_dict['is_discontinued'] = (plan.status == 'discontinued')

                    if plan.status == 'discontinued':
                        item_dict['discontinuation_reason'] = plan.discontinuation_reason
                        item_dict['refund_amount'] = float(plan.refund_amount)

                        # Get credit note details
                        if plan.credit_note:
                            item_dict['credit_note_number'] = plan.credit_note.credit_note_number
                            item_dict['credit_note_amount'] = float(plan.credit_note.total_amount)

            line_items.append(item_dict)

        return {
            'invoice': to_dict(invoice),
            'line_items': line_items
        }
```

### In SQL (Reporting)

```sql
-- Invoice line items with package discontinuation status
SELECT
    ih.invoice_number,
    ih.invoice_date,
    ili.item_name,
    ili.item_type,
    ili.line_total,
    ppp.status AS package_status,
    ppp.discontinued_at,
    ppp.discontinuation_reason,
    cn.credit_note_number,
    cn.total_amount AS refund_amount,
    ili.line_total - COALESCE(cn.total_amount, 0) AS net_amount
FROM invoice_header ih
JOIN invoice_line_item ili ON ih.invoice_id = ili.invoice_id
LEFT JOIN package_payment_plans ppp
    ON ili.invoice_id = ppp.invoice_id
    AND ili.package_id = ppp.package_id
LEFT JOIN patient_credit_notes cn
    ON cn.plan_id = ppp.plan_id
    AND cn.reason_code = 'plan_discontinued'
WHERE ih.invoice_id = 'invoice_id_here'
ORDER BY ili.line_item_id;
```

## Summary

### ✅ What DOES Change (Current Implementation - Correct!)

1. **PackagePaymentPlan.status** = 'discontinued'
2. **PackagePaymentPlan.discontinued_at** = timestamp
3. **PackagePaymentPlan.discontinuation_reason** = reason text
4. **PackagePaymentPlan.refund_amount** = credit note amount
5. **PackagePaymentPlan.credit_note_id** = links to credit note
6. **PatientCreditNote** created (reverses revenue)
7. **AR Subledger** credit entry (reduces receivable)
8. **GL Entries** posted (Dr Revenue, Cr AR)
9. **PackageSessions** cancelled (scheduled sessions)
10. **InstallmentPayments** waived (pending installments)

### ❌ What Does NOT Change (By Design - Correct!)

1. **InvoiceHeader** - Unchanged
2. **InvoiceLineItem** - Unchanged (immutable invoice principle)
3. **Original GL entries** - Not deleted (audit trail preserved)

### 🔍 How to Check Discontinuation Status

**Option 1**: Query PackagePaymentPlan.status
**Option 2**: Check for credit notes against invoice
**Option 3**: Use database view (recommended for reporting)

### 📊 Composite Invoice Handling

- **Service line items**: Remain active ✅
- **Package line items**: Shown as discontinued with credit note reference 🟡
- **Medicine line items**: Remain active ✅
- **Invoice total**: Shows original + credit notes separately
- **Net amount**: Calculated as Original - Credit Notes

## Recommendation

**Current implementation is CORRECT!** ✅

**Do NOT add discontinuation status to invoice_line_item table.**

**Instead**:
1. Continue using PackagePaymentPlan.status for tracking
2. Use credit notes for financial reversal
3. Create database view for easy querying
4. Show discontinuation status in UI by joining with plan table

This approach:
- ✅ Maintains invoice immutability
- ✅ Preserves audit trail
- ✅ Complies with accounting standards
- ✅ Handles composite invoices correctly
- ✅ Uses proper credit note mechanism
