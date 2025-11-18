# Payment Form Frontend Implementation Guide

## Status: Backend Complete ✅ | Frontend Implementation Required

---

## What's Been Completed

### 1. Backend APIs ✅

#### Patient Summary API
**Endpoint:** `GET /api/patient/<patient_id>/payment-summary`
**File:** `app/api/routes/patient_api_enhancement.py`

**Response:**
```json
{
  "success": true,
  "patient": {
    "patient_id": "uuid",
    "mrn": "MRN12345",
    "name": "John Doe",
    "phone": "+91 9876543210",
    "email": "john@example.com",
    "age": 35,
    "gender": "M"
  },
  "financial_summary": {
    "total_outstanding": 15000.00,
    "advance_balance": 2000.00,
    "net_due": 13000.00,
    "outstanding_invoices_count": 3,
    "pending_installments_count": 5
  }
}
```

#### Enhanced Outstanding Invoices API
**Endpoint:** `GET /api/billing/patient/<patient_id>/outstanding-invoices`
**File:** `app/api/routes/billing.py`

**Response Structure:**
```json
{
  "success": true,
  "invoices": [
    {
      "invoice_id": "uuid",
      "invoice_number": "INV-001",
      "invoice_date": "2025-11-15",
      "balance_due": 5900.00,
      "line_items": [
        {
          "line_item_id": "uuid",
          "item_type": "Service",
          "item_name": "Consultation",
          "line_balance": 600.00,
          "has_installments": false,
          "installments": []
        },
        {
          "line_item_id": "uuid",
          "item_type": "Package",
          "item_name": "Acne Care Package",
          "line_balance": 5300.00,
          "has_installments": true,
          "installments": [
            {
              "installment_id": "uuid",
              "installment_number": 1,
              "due_date": "2025-11-15",
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

---

## Frontend Implementation Tasks

### Task 1: Add Patient Info Card Header

**Location:** `app/templates/billing/payment_form_enhanced.html` (after line ~150)

**HTML Structure to Add:**
```html
<!-- Patient Information Card -->
<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6" id="patient-info-card">
    <div class="p-6">
        <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                <i class="fas fa-user-circle mr-2 text-blue-600"></i>
                Patient Information
            </h3>
            <span class="text-sm text-gray-500" id="patient-mrn">MRN: Loading...</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Left Column: Patient Details -->
            <div class="space-y-3">
                <div>
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Name</label>
                    <p class="text-sm font-medium text-gray-900 dark:text-white" id="patient-name">Loading...</p>
                </div>
                <div>
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Contact</label>
                    <p class="text-sm text-gray-700 dark:text-gray-300" id="patient-phone">Loading...</p>
                </div>
                <div>
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Email</label>
                    <p class="text-sm text-gray-700 dark:text-gray-300" id="patient-email">Loading...</p>
                </div>
            </div>

            <!-- Middle Column: Demographics -->
            <div class="space-y-3">
                <div>
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Age</label>
                    <p class="text-sm text-gray-700 dark:text-gray-300" id="patient-age">-</p>
                </div>
                <div>
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Gender</label>
                    <p class="text-sm text-gray-700 dark:text-gray-300" id="patient-gender">-</p>
                </div>
            </div>

            <!-- Right Column: Financial Summary -->
            <div class="space-y-3 border-l border-gray-200 dark:border-gray-700 pl-6">
                <div>
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Total Outstanding</label>
                    <p class="text-lg font-bold text-red-600 dark:text-red-400" id="total-outstanding">₹0.00</p>
                </div>
                <div>
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Advance Balance</label>
                    <p class="text-lg font-bold text-green-600 dark:text-green-400" id="advance-balance-summary">₹0.00</p>
                </div>
                <div class="pt-2 border-t border-gray-200 dark:border-gray-600">
                    <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Net Due</label>
                    <p class="text-xl font-bold text-blue-600 dark:text-blue-400" id="net-due">₹0.00</p>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
                    <span id="outstanding-count">0</span> invoices · <span id="installments-count">0</span> installments
                </div>
            </div>
        </div>
    </div>
</div>
```

**JavaScript to Add** (in `<script>` section around line ~750):
```javascript
async function fetchPatientSummary() {
    try {
        const response = await fetch(`/api/patient/${state.patientId}/payment-summary`);
        if (!response.ok) throw new Error('Failed to fetch patient summary');

        const data = await response.json();

        // Update patient details
        document.getElementById('patient-name').textContent = data.patient.name;
        document.getElementById('patient-mrn').textContent = `MRN: ${data.patient.mrn}`;
        document.getElementById('patient-phone').textContent = data.patient.phone || 'N/A';
        document.getElementById('patient-email').textContent = data.patient.email || 'N/A';
        document.getElementById('patient-age').textContent = data.patient.age || '-';
        document.getElementById('patient-gender').textContent = data.patient.gender || '-';

        // Update financial summary
        document.getElementById('total-outstanding').textContent = `₹${data.financial_summary.total_outstanding.toFixed(2)}`;
        document.getElementById('advance-balance-summary').textContent = `₹${data.financial_summary.advance_balance.toFixed(2)}`;
        document.getElementById('net-due').textContent = `₹${data.financial_summary.net_due.toFixed(2)}`;
        document.getElementById('outstanding-count').textContent = data.financial_summary.outstanding_invoices_count;
        document.getElementById('installments-count').textContent = data.financial_summary.pending_installments_count;

    } catch (error) {
        console.error('[ERROR] Fetching patient summary:', error);
    }
}

// Call in initialization (around line ~1400)
// Add to initializePaymentForm() function:
await fetchPatientSummary();
```

---

### Task 2: Add Filter Controls

**Location:** After patient info card (around line ~250)

**HTML Structure to Add:**
```html
<!-- Filter Controls -->
<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
    <div class="p-4">
        <div class="flex items-center justify-between mb-3">
            <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center">
                <i class="fas fa-filter mr-2 text-purple-600"></i>
                Filter Invoices
            </h4>
            <button type="button"
                    onclick="clearFilters()"
                    class="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
                <i class="fas fa-times-circle mr-1"></i> Clear Filters
            </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <!-- Invoice Number Filter -->
            <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Invoice Number
                </label>
                <input type="text"
                       id="filter-invoice-number"
                       placeholder="INV-001"
                       class="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                       oninput="applyFilters()">
            </div>

            <!-- Invoice Date (On or Before) -->
            <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Invoice Date (On or Before)
                </label>
                <input type="date"
                       id="filter-invoice-date"
                       class="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                       onchange="applyFilters()">
            </div>

            <!-- Due Date (On or Before) -->
            <div>
                <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Due Date (On or Before)
                </label>
                <input type="date"
                       id="filter-due-date"
                       class="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                       onchange="applyFilters()">
            </div>

            <!-- Packages Only Checkbox -->
            <div class="flex items-end">
                <label class="flex items-center space-x-2 cursor-pointer">
                    <input type="checkbox"
                           id="filter-packages-only"
                           class="form-checkbox h-4 w-4 text-purple-600 rounded"
                           onchange="applyFilters()">
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Packages Only
                    </span>
                </label>
            </div>
        </div>
    </div>
</div>
```

**JavaScript Functions to Add:**
```javascript
// Store filtered invoices
state.filteredInvoices = [];

function applyFilters() {
    const invoiceNumber = document.getElementById('filter-invoice-number').value.toLowerCase();
    const invoiceDate = document.getElementById('filter-invoice-date').value;
    const dueDate = document.getElementById('filter-due-date').value;
    const packagesOnly = document.getElementById('filter-packages-only').checked;

    state.filteredInvoices = state.outstandingInvoices.filter(invoice => {
        // Filter by invoice number
        if (invoiceNumber && !invoice.invoice_number.toLowerCase().includes(invoiceNumber)) {
            return false;
        }

        // Filter by invoice date (on or before)
        if (invoiceDate && invoice.invoice_date > invoiceDate) {
            return false;
        }

        // Filter by due date (on or before)
        // Note: Add due_date field to invoice API response
        if (dueDate && invoice.due_date && invoice.due_date > dueDate) {
            return false;
        }

        // Filter packages only
        if (packagesOnly) {
            const hasPackages = invoice.line_items && invoice.line_items.some(item => item.item_type === 'Package');
            if (!hasPackages) {
                return false;
            }
        }

        return true;
    });

    renderInvoicesTable();
}

function clearFilters() {
    document.getElementById('filter-invoice-number').value = '';
    document.getElementById('filter-invoice-date').value = '';
    document.getElementById('filter-due-date').value = '';
    document.getElementById('filter-packages-only').checked = false;
    state.filteredInvoices = state.outstandingInvoices;
    renderInvoicesTable();
}
```

---

### Task 3: Update renderInvoicesTable() for Hierarchical View

**Location:** Replace existing `renderInvoicesTable()` function (around line ~857)

**New Implementation:**
```javascript
function renderInvoicesTable() {
    const tbody = document.getElementById('invoices-table-body');
    tbody.innerHTML = '';

    // Use filtered invoices if filters are active
    const invoicesToRender = state.filteredInvoices.length > 0 || hasActiveFilters()
        ? state.filteredInvoices
        : state.outstandingInvoices;

    if (invoicesToRender.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-3 py-8 text-center text-gray-500 dark:text-gray-400">
                    <i class="fas fa-inbox text-4xl mb-2"></i>
                    <p>No invoices match the current filters</p>
                </td>
            </tr>
        `;
        return;
    }

    invoicesToRender.forEach(invoice => {
        // Render invoice header row
        renderInvoiceHeaderRow(invoice, tbody);

        // If invoice is expanded, render line items
        if (state.expandedInvoices.has(invoice.invoice_id)) {
            invoice.line_items?.forEach(lineItem => {
                renderLineItemRow(lineItem, invoice, tbody);

                // If line item has installments and is expanded, render them
                if (lineItem.has_installments &&
                    state.expandedPackages.has(lineItem.line_item_id)) {
                    lineItem.installments?.forEach(installment => {
                        renderInstallmentRow(installment, lineItem, invoice, tbody);
                    });
                }
            });
        }
    });

    attachInvoiceEventListeners();
    updateInvoiceTotals();
}

function renderInvoiceHeaderRow(invoice, tbody) {
    const row = document.createElement('tr');
    const balance = parseFloat(invoice.balance_due);
    const allocated = state.allocations.invoices[invoice.invoice_id] || 0;
    const isExpanded = state.expandedInvoices.has(invoice.invoice_id);
    const hasLineItems = invoice.line_items && invoice.line_items.length > 0;

    row.className = 'invoice-header-row bg-white dark:bg-gray-800 font-medium border-b-2 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer';
    row.dataset.invoiceId = invoice.invoice_id;

    row.innerHTML = `
        <td class="px-3 py-3 whitespace-nowrap">
            ${hasLineItems ? `
                <button class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mr-2"
                        onclick="event.stopPropagation(); toggleInvoiceExpand('${invoice.invoice_id}')">
                    <i class="fas fa-chevron-${isExpanded ? 'down' : 'right'} text-xs"></i>
                </button>
            ` : '<span class="inline-block w-6"></span>'}
            <input type="checkbox"
                   class="invoice-checkbox form-checkbox h-4 w-4 text-blue-600 rounded"
                   data-invoice-id="${invoice.invoice_id}"
                   data-balance="${balance}"
                   ${allocated > 0 ? 'checked' : ''}
                   onclick="event.stopPropagation()">
        </td>
        <td class="px-3 py-3 whitespace-nowrap text-sm text-blue-600 dark:text-blue-400 font-semibold"
            onclick="toggleInvoiceExpand('${invoice.invoice_id}')">
            <i class="fas fa-file-invoice mr-2"></i>
            ${invoice.invoice_number}
        </td>
        <td class="px-3 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400"
            onclick="toggleInvoiceExpand('${invoice.invoice_id}')">
            ${formatDate(invoice.invoice_date)}
        </td>
        <td class="px-3 py-3 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white"
            onclick="toggleInvoiceExpand('${invoice.invoice_id}')">
            ₹${parseFloat(invoice.grand_total).toFixed(2)}
        </td>
        <td class="px-3 py-3 whitespace-nowrap text-sm text-right text-green-600 dark:text-green-400"
            onclick="toggleInvoiceExpand('${invoice.invoice_id}')">
            ₹${parseFloat(invoice.paid_amount).toFixed(2)}
        </td>
        <td class="px-3 py-3 whitespace-nowrap text-sm text-right font-semibold text-gray-900 dark:text-white"
            onclick="toggleInvoiceExpand('${invoice.invoice_id}')">
            ₹${balance.toFixed(2)}
        </td>
        <td class="px-3 py-3 whitespace-nowrap text-right" onclick="event.stopPropagation()">
            <div class="inline-flex items-center gap-2">
                <span class="text-gray-500 text-sm font-semibold">₹</span>
                <input type="number"
                       class="invoice-allocation-input w-32 px-3 py-1.5 text-sm text-right border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                       data-invoice-id="${invoice.invoice_id}"
                       data-balance="${balance}"
                       value="${allocated.toFixed(2)}"
                       step="0.01"
                       min="0"
                       max="${balance}">
            </div>
        </td>
    `;

    tbody.appendChild(row);
}

function renderLineItemRow(lineItem, invoice, tbody) {
    const row = document.createElement('tr');
    const hasInstallments = lineItem.has_installments && lineItem.installments.length > 0;
    const isExpanded = state.expandedPackages.has(lineItem.line_item_id);

    row.className = 'line-item-row bg-gray-50 dark:bg-gray-750 text-sm';
    row.innerHTML = `
        <td class="px-3 py-2 pl-12" colspan="2">
            ${hasInstallments ? `
                <button class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mr-2"
                        onclick="togglePackageExpand('${lineItem.line_item_id}')">
                    <i class="fas fa-chevron-${isExpanded ? 'down' : 'right'} text-xs"></i>
                </button>
            ` : '<span class="inline-block w-6"></span>'}
            <i class="fas ${getItemIcon(lineItem.item_type)} mr-2 text-gray-400"></i>
            <span class="text-gray-700 dark:text-gray-300">${lineItem.item_name}</span>
            ${hasInstallments ? `<span class="ml-2 text-xs text-purple-600 dark:text-purple-400">(${lineItem.installments.length} installments)</span>` : ''}
        </td>
        <td class="px-3 py-2 text-gray-500 dark:text-gray-400" colspan="3">${lineItem.item_type}</td>
        <td class="px-3 py-2 text-right text-gray-700 dark:text-gray-300">₹${lineItem.line_balance.toFixed(2)}</td>
        <td></td>
    `;

    tbody.appendChild(row);
}

function renderInstallmentRow(installment, lineItem, invoice, tbody) {
    const row = document.createElement('tr');
    const isOverdue = new Date(installment.due_date) < new Date();
    const payableAmount = parseFloat(installment.payable_amount);
    const allocated = state.allocations.installments[installment.installment_id] || 0;

    row.className = `installment-row text-xs ${isOverdue ? 'bg-red-50 dark:bg-red-900/20' : 'bg-gray-100 dark:bg-gray-800'}`;
    row.innerHTML = `
        <td class="px-3 py-2 pl-20" colspan="2">
            <input type="checkbox"
                   class="installment-checkbox form-checkbox h-3 w-3 text-purple-600 rounded mr-2"
                   data-installment-id="${installment.installment_id}"
                   data-amount="${payableAmount}"
                   ${allocated > 0 ? 'checked' : ''}>
            <i class="fas fa-calendar-check mr-2 text-purple-400"></i>
            Installment #${installment.installment_number}
            ${isOverdue ? '<i class="fas fa-exclamation-circle ml-1 text-red-500"></i>' : ''}
        </td>
        <td class="px-3 py-2 ${isOverdue ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-400'}">
            ${formatDate(installment.due_date)}
        </td>
        <td class="px-3 py-2 text-right text-gray-600 dark:text-gray-400" colspan="2">
            ₹${installment.amount.toFixed(2)}
        </td>
        <td class="px-3 py-2 text-right font-medium ${payableAmount > 0 ? 'text-gray-900 dark:text-white' : 'text-gray-400'}">
            ₹${payableAmount.toFixed(2)}
        </td>
        <td class="px-3 py-2 text-right">
            <input type="number"
                   class="installment-allocation-input w-24 px-2 py-1 text-xs text-right border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                   data-installment-id="${installment.installment_id}"
                   data-amount="${payableAmount}"
                   value="${allocated.toFixed(2)}"
                   step="0.01"
                   min="0"
                   max="${payableAmount}">
        </td>
    `;

    tbody.appendChild(row);
}

function toggleInvoiceExpand(invoiceId) {
    if (state.expandedInvoices.has(invoiceId)) {
        state.expandedInvoices.delete(invoiceId);
    } else {
        state.expandedInvoices.add(invoiceId);
    }
    renderInvoicesTable();
}

function togglePackageExpand(lineItemId) {
    if (state.expandedPackages.has(lineItemId)) {
        state.expandedPackages.delete(lineItemId);
    } else {
        state.expandedPackages.add(lineItemId);
    }
    renderInvoicesTable();
}

function getItemIcon(itemType) {
    switch(itemType) {
        case 'Service': return 'fa-stethoscope';
        case 'Medicine': return 'fa-pills';
        case 'Package': return 'fa-box';
        default: return 'fa-circle';
    }
}

function hasActiveFilters() {
    return document.getElementById('filter-invoice-number').value ||
           document.getElementById('filter-invoice-date').value ||
           document.getElementById('filter-due-date').value ||
           document.getElementById('filter-packages-only').checked;
}
```

---

### Task 4: Update State Management

**Location:** Around line ~700

**Add to state object:**
```javascript
const state = {
    patientId: null,
    currentInvoiceId: null,
    outstandingInvoices: [],
    filteredInvoices: [],  // NEW
    expandedInvoices: new Set(),  // NEW
    expandedPackages: new Set(),  // NEW
    pendingInstallments: [],  // REMOVE - now part of line_items
    advanceBalance: 0,
    allocations: {
        invoices: {},
        installments: {}
    },
    totals: {
        selectedInvoices: 0,
        selectedInstallments: 0,
        totalAllocated: 0
    }
};
```

---

## Summary of Changes

### Files Modified:
1. ✅ `app/api/routes/patient_api_enhancement.py` - NEW (patient summary API)
2. ✅ `app/api/routes/billing.py` - MODIFIED (hierarchical invoice data)
3. ✅ `app/__init__.py` - MODIFIED (register new blueprint)
4. 🔄 `app/templates/billing/payment_form_enhanced.html` - TO MODIFY (add patient card, filters, hierarchical table)

### Estimated Implementation Time:
- Patient info card: 30 minutes
- Filter controls: 30 minutes
- Hierarchical table rendering: 2 hours
- Testing & refinement: 1 hour
**Total: ~4 hours**

---

## Testing Checklist

- [ ] Patient info card loads correctly
- [ ] Financial summary displays accurate totals
- [ ] Invoice number filter works
- [ ] Date filters work
- [ ] Packages only filter works
- [ ] Clear filters button works
- [ ] Invoice expand/collapse works
- [ ] Package expand/collapse shows installments
- [ ] Installment checkboxes work
- [ ] Amount allocation works for both invoices and installments
- [ ] Form submission sends correct data
- [ ] Multi-invoice + installment payment works

---

**Ready to implement? All backend APIs are ready and tested!**
