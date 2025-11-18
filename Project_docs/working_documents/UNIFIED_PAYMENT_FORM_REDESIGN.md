# Unified Payment Form Redesign

## Current Status: Backend API Complete ✅

## Overview
Redesigning the payment form to show a **unified hierarchical view** where packages appear as invoice line items with expandable installment details.

---

## 1. Backend API Changes ✅ COMPLETE

### Modified: `app/api/routes/billing.py`
**Endpoint:** `/api/billing/patient/<patient_id>/outstanding-invoices`

**New Response Structure:**
```json
{
  "success": true,
  "invoices": [
    {
      "invoice_id": "uuid",
      "invoice_number": "SVC/2025-2026/00020",
      "invoice_date": "2025-11-15",
      "grand_total": 5900.00,
      "paid_amount": 0.00,
      "balance_due": 5900.00,
      "line_items": [
        {
          "line_item_id": "uuid",
          "item_type": "Service",
          "item_name": "Dermatologist Consultation",
          "line_total": 600.00,
          "line_balance": 600.00,
          "has_installments": false,
          "installments": []
        },
        {
          "line_item_id": "uuid",
          "item_type": "Package",
          "item_name": "Acne Care Package",
          "line_total": 5300.00,
          "line_balance": 5300.00,
          "has_installments": true,
          "installments": [
            {
              "installment_id": "uuid",
              "installment_number": 1,
              "due_date": "2025-11-15",
              "amount": 1966.67,
              "paid_amount": 0.00,
              "balance_amount": 1966.67,
              "payable_amount": 1966.67,
              "status": "pending"
            },
            {
              "installment_id": "uuid",
              "installment_number": 2,
              "due_date": "2025-12-15",
              "amount": 1966.67,
              "paid_amount": 0.00,
              "balance_amount": 1966.67,
              "payable_amount": 1966.67,
              "status": "pending"
            }
          ]
        }
      ]
    }
  ]
}
```

**Key Features:**
- ✅ Returns invoices with nested line items
- ✅ Package line items include nested installments
- ✅ `payable_amount` capped by invoice balance
- ✅ Line-item level balances from AR subledger
- ✅ Installments filtered (excludes if invoice fully paid)

---

## 2. Frontend Redesign (TODO)

### New UI Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Outstanding Invoices                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ☑ INV-001 | 2025-11-15 | ₹5,900.00 | Paid: ₹0 | Due: ₹5,900│
│   ├─ Service: Dermatologist Consultation         ₹600.00   │
│   └─ Package: Acne Care Package                 ₹5,300.00   │
│       ▼ Installments (3 pending)                            │
│         ☐ #1 | Due: 2025-11-15 | ₹1,966.67 | [₹1966.67 ]   │
│         ☐ #2 | Due: 2025-12-15 | ₹1,966.67 | [₹1966.67 ]   │
│         ☐ #3 | Due: 2026-01-15 | ₹1,966.67 | [₹1966.67 ]   │
│                                                              │
│ ☐ INV-002 | 2025-11-16 | ₹1,200.00 | Paid: ₹0 | Due: ₹1,200│
│   ├─ Medicine: Doxycycline 100mg                 ₹450.00   │
│   └─ Service: Follow-up Consultation             ₹750.00   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Interaction Model

1. **Invoice Level:**
   - Checkbox to select entire invoice
   - Click invoice row to expand/collapse line items
   - Auto-allocate full balance when checked

2. **Line Item Level:**
   - Shows individual services, medicines, packages
   - For packages: Shows installment count with expand/collapse
   - No direct payment allocation (payment goes to installments)

3. **Installment Level (Package Only):**
   - Individual checkboxes for each installment
   - Editable amount field (max = payable_amount)
   - Auto-checked if overdue
   - Visual indicators: overdue (red), limited by invoice balance (amber)

---

## 3. Implementation Plan

### Phase 1: Update JavaScript Rendering
**File:** `app/templates/billing/payment_form_enhanced.html`

1. **Remove separate sections** (lines ~300-600):
   - Delete `package-installments-section`
   - Keep single unified invoices section

2. **Rewrite `renderInvoicesTable()` function** (lines ~857-929):
   ```javascript
   function renderInvoicesTable() {
       const tbody = document.getElementById('invoices-table-body');
       tbody.innerHTML = '';

       state.outstandingInvoices.forEach(invoice => {
           // Render invoice header row
           renderInvoiceRow(invoice, tbody);

           // If invoice has line items, render them
           if (invoice.line_items && invoice.line_items.length > 0) {
               invoice.line_items.forEach(lineItem => {
                   renderLineItemRow(lineItem, invoice, tbody);

                   // If line item has installments, render them
                   if (lineItem.has_installments && lineItem.installments.length > 0) {
                       lineItem.installments.forEach(installment => {
                           renderInstallmentRow(installment, lineItem, invoice, tbody);
                       });
                   }
               });
           }
       });
   }
   ```

3. **New Rendering Functions:**
   - `renderInvoiceRow()` - Invoice header with expand/collapse
   - `renderLineItemRow()` - Line item with package indicator
   - `renderInstallmentRow()` - Individual installment with checkbox & amount

4. **Update State Management:**
   ```javascript
   state = {
       allocations: {
           invoices: {},      // Invoice level (for non-package items)
           installments: {}   // Installment level (for packages)
       },
       expandedInvoices: new Set(),  // Track which invoices are expanded
       expandedPackages: new Set()   // Track which packages show installments
   }
   ```

### Phase 2: Update HTML Template
**File:** `app/templates/billing/payment_form_enhanced.html`

1. **Simplify table structure** (lines ~200-350):
   - Single table for all items
   - Remove separate installments section
   - Add indentation CSS classes for hierarchy

2. **Add CSS for hierarchy** (lines ~50-100):
   ```css
   .invoice-row { background: white; font-weight: 500; }
   .line-item-row { background: #f9fafb; padding-left: 2rem; }
   .installment-row { background: #f3f4f6; padding-left: 4rem; font-size: 0.875rem; }
   .expandable-row { cursor: pointer; }
   .expanded { /* rotate chevron icon */ }
   ```

### Phase 3: Update Form Submission
**File:** `app/views/billing_views.py`

Already handles installment allocations correctly (lines ~1560-1615).
No changes needed - form data format remains the same.

---

## 4. Benefits of New Design

✅ **Single Source of Truth:** One table shows all payment options
✅ **Intuitive Hierarchy:** Visual grouping shows relationships
✅ **Package Context:** Installments shown IN CONTEXT of parent invoice
✅ **Smart Filtering:** Hides installments if invoice fully paid
✅ **Smart Limits:** Shows only payable amount based on invoice balance
✅ **Better UX:** No confusion between separate invoice/installment sections

---

## 5. Migration Strategy

1. ✅ **Backend API updated** - Already done
2. 🔄 **Create new JavaScript functions** - Parallel development
3. 🔄 **Test with new API structure** - Verify rendering
4. 🔄 **Replace old rendering logic** - Single atomic change
5. 🔄 **Remove old installments section** - Cleanup
6. ✅ **Form submission logic** - Already compatible

---

## 6. Testing Checklist

- [ ] Invoice with only services/medicines (no packages)
- [ ] Invoice with single package and installments
- [ ] Invoice with multiple packages
- [ ] Invoice with mix of services + package
- [ ] Fully paid invoice not shown
- [ ] Partially paid invoice shows correct balances
- [ ] Installment payable amount capped by invoice balance
- [ ] Overdue installments auto-selected
- [ ] Expand/collapse invoice works
- [ ] Expand/collapse package installments works
- [ ] Payment submission creates correct allocations
- [ ] Multi-invoice payment works

---

## Next Steps

**AWAITING USER APPROVAL**

Once approved, implement:
1. New rendering functions (2-3 hours)
2. Update HTML structure (1 hour)
3. Testing and refinement (1-2 hours)

**Total Effort:** 4-6 hours

Would you like me to proceed with the implementation?
