// ============================================================================
// PATIENT PAYMENT FORM - JAVASCRIPT (Adapted from Supplier Payment Logic)
// ============================================================================
// This script provides the same robust validation and UX as supplier payment form
// Copy this entire content and replace the <script> section in payment_form_enhanced.html
// ============================================================================

<script>
(function() {
    'use strict';

    // ============================================
    // FIELD REFERENCES
    // ============================================
    const form = document.getElementById('enhanced-payment-form');
    const advanceField = document.getElementById('advance_amount');
    const cashField = document.getElementById('cash_amount');
    const creditCardField = document.getElementById('credit_card_amount');
    const debitCardField = document.getElementById('debit_card_amount');
    const upiField = document.getElementById('upi_amount');
    const cardDetails = document.getElementById('card-details');
    const upiDetails = document.getElementById('upi-details');
    const validationDiv = document.getElementById('validation-message');
    const paymentBreakdownDiv = document.getElementById('payment-breakdown');

    // ============================================
    // STATE MANAGEMENT
    // ============================================
    const state = {
        patientId: '{{ patient.patient_id }}',
        hospitalId: '{{ current_user.hospital_id }}',
        currentInvoiceId: '{{ invoice.invoice_id }}',
        approvalThreshold: {{ approval_threshold }},

        outstandingInvoices: [],
        pendingInstallments: [],
        advanceBalance: 0,

        allocations: {
            invoices: {},       // { invoice_id: amount }
            installments: {}    // { installment_id: amount }
        }
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    document.addEventListener('DOMContentLoaded', async function() {
        console.log('[INIT] Patient payment form initialized');

        // Fetch all data
        await Promise.all([
            fetchOutstandingInvoices(),
            fetchAdvanceBalance(),
            fetchPendingInstallments()
        ]);

        // Set up event listeners for payment method fields
        [advanceField, cashField, creditCardField, debitCardField, upiField].forEach(field => {
            if (field) {
                field.addEventListener('input', function() {
                    toggleMethodDetails();
                    updateSummary();
                    validateAmounts();
                });
            }
        });

        // Initial update
        toggleMethodDetails();
        updateSummary();
        validateAmounts();

        console.log('[INIT] Initialization complete');
    });

    // ============================================
    // DATA FETCHING
    // ============================================

    async function fetchOutstandingInvoices() {
        try {
            const response = await fetch(`/api/billing/patient/${state.patientId}/outstanding-invoices`);
            if (!response.ok) throw new Error('Failed to fetch invoices');

            const data = await response.json();
            state.outstandingInvoices = data.invoices || [];

            document.getElementById('invoices-loading').classList.add('hidden');
            document.getElementById('invoices-table-container').classList.remove('hidden');

            if (state.outstandingInvoices.length === 0) {
                document.getElementById('no-invoices-message').classList.remove('hidden');
            } else {
                renderInvoicesTable();
            }
        } catch (error) {
            console.error('[ERROR] Fetching invoices:', error);
        }
    }

    async function fetchAdvanceBalance() {
        try {
            const response = await fetch(`/api/billing/patient/${state.patientId}/advance-balance`);
            if (!response.ok) throw new Error('Failed to fetch advance balance');

            const data = await response.json();
            state.advanceBalance = parseFloat(data.balance) || 0;

            const advanceDisplayEl = document.getElementById('advance-balance-display');
            if (advanceDisplayEl) {
                advanceDisplayEl.textContent = state.advanceBalance.toFixed(2);
            }

            if (advanceField) {
                advanceField.setAttribute('max', state.advanceBalance);
            }

            console.log('[ADVANCE] Balance loaded:', state.advanceBalance);
        } catch (error) {
            console.error('[ERROR] Fetching advance balance:', error);
        }
    }

    async function fetchPendingInstallments() {
        try {
            const response = await fetch(`/api/billing/patient/${state.patientId}/pending-installments`);
            if (!response.ok) throw new Error('Failed to fetch installments');

            const data = await response.json();
            state.pendingInstallments = data.installments || [];

            if (state.pendingInstallments.length > 0) {
                document.getElementById('package-installments-section').classList.remove('hidden');
                document.getElementById('installments-loading').classList.add('hidden');
                document.getElementById('installments-table-container').classList.remove('hidden');
                renderInstallmentsTable();
            }
        } catch (error) {
            console.error('[ERROR] Fetching installments:', error);
        }
    }

    // ============================================
    // RENDERING FUNCTIONS
    // ============================================

    function renderInvoicesTable() {
        const tbody = document.getElementById('invoices-table-body');
        tbody.innerHTML = '';

        // Auto-allocate full balance on first render
        state.outstandingInvoices.forEach((invoice) => {
            const balance = parseFloat(invoice.balance_due);
            if (state.allocations.invoices[invoice.invoice_id] === undefined) {
                state.allocations.invoices[invoice.invoice_id] = balance;
            }
        });

        state.outstandingInvoices.forEach((invoice) => {
            const row = document.createElement('tr');
            const balance = parseFloat(invoice.balance_due);
            const allocated = state.allocations.invoices[invoice.invoice_id] || 0;

            row.className = invoice.invoice_id === state.currentInvoiceId ?
                'bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors duration-150' :
                'hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150';

            row.innerHTML = `
                <td class="px-3 py-3 whitespace-nowrap" onclick="event.stopPropagation()">
                    <input type="checkbox"
                           class="invoice-checkbox form-checkbox h-4 w-4 text-blue-600 rounded"
                           data-invoice-id="${invoice.invoice_id}"
                           data-balance="${balance}"
                           ${allocated > 0 ? 'checked' : ''}>
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm text-gray-900 dark:text-white cursor-pointer invoice-row-clickable" data-invoice-id="${invoice.invoice_id}">
                    <div class="flex items-center">
                        <i class="fas fa-file-invoice mr-2 text-blue-500"></i>
                        <span class="hover:underline">${invoice.invoice_number}</span>
                        ${invoice.invoice_id === state.currentInvoiceId ? '<span class="ml-2 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 px-2 py-0.5 rounded">Current</span>' : ''}
                    </div>
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                    ${formatDate(invoice.invoice_date)}
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm text-right text-gray-900 dark:text-white">
                    ₹${parseFloat(invoice.grand_total).toFixed(2)}
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm text-right text-green-600 dark:text-green-400">
                    ₹${parseFloat(invoice.paid_amount).toFixed(2)}
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm text-right font-medium text-gray-900 dark:text-white">
                    ₹${balance.toFixed(2)}
                </td>
                <td class="px-3 py-3 whitespace-nowrap" onclick="event.stopPropagation()">
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-2 flex items-center text-gray-500 text-xs">₹</span>
                        <input type="number"
                               class="invoice-allocation-input w-full pl-5 pr-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
        });

        attachInvoiceEventListeners();
        updateInvoiceTotals();
    }

    function renderInstallmentsTable() {
        const tbody = document.getElementById('installments-table-body');
        tbody.innerHTML = '';

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        // Auto-allocate overdue installments
        const overdueInstallments = state.pendingInstallments.filter(inst => {
            const dueDate = new Date(inst.due_date);
            dueDate.setHours(0, 0, 0, 0);
            return dueDate < today;
        });

        overdueInstallments.forEach(installment => {
            if (state.allocations.installments[installment.installment_id] === undefined) {
                state.allocations.installments[installment.installment_id] = parseFloat(installment.amount);
            }
        });

        state.pendingInstallments.forEach(installment => {
            const row = document.createElement('tr');
            const isOverdue = new Date(installment.due_date) < today;
            const amount = parseFloat(installment.amount);
            const allocated = state.allocations.installments[installment.installment_id] || 0;

            row.className = isOverdue ?
                'bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30' :
                'hover:bg-gray-50 dark:hover:bg-gray-700';

            row.innerHTML = `
                <td class="px-3 py-3 whitespace-nowrap">
                    <input type="checkbox"
                           class="installment-checkbox form-checkbox h-4 w-4 text-purple-600 rounded"
                           data-installment-id="${installment.installment_id}"
                           data-amount="${amount}"
                           ${allocated > 0 ? 'checked' : ''}>
                </td>
                <td class="px-3 py-3 text-sm text-gray-900 dark:text-white">
                    ${installment.package_name}
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                    #${installment.installment_number}
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm ${isOverdue ? 'text-red-600 dark:text-red-400 font-medium' : 'text-gray-600 dark:text-gray-400'}">
                    ${formatDate(installment.due_date)}
                    ${isOverdue ? '<i class="fas fa-exclamation-circle ml-1"></i>' : ''}
                </td>
                <td class="px-3 py-3 whitespace-nowrap">
                    <span class="px-2 py-1 text-xs font-medium rounded ${getStatusClass(installment.status)}">
                        ${installment.status}
                    </span>
                </td>
                <td class="px-3 py-3 whitespace-nowrap text-sm text-right font-medium text-gray-900 dark:text-white">
                    ₹${amount.toFixed(2)}
                </td>
                <td class="px-3 py-3 whitespace-nowrap">
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-2 flex items-center text-gray-500 text-xs">₹</span>
                        <input type="number"
                               class="installment-allocation-input w-full pl-5 pr-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-purple-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                               data-installment-id="${installment.installment_id}"
                               data-amount="${amount}"
                               value="${allocated.toFixed(2)}"
                               step="0.01"
                               min="0"
                               max="${amount}">
                    </div>
                </td>
            `;

            tbody.appendChild(row);
        });

        attachInstallmentEventListeners();
        updateInstallmentTotals();
    }

    // ============================================
    // EVENT LISTENERS
    // ============================================

    function attachInvoiceEventListeners() {
        // Checkbox handlers
        document.querySelectorAll('.invoice-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const invoiceId = this.dataset.invoiceId;
                const balance = parseFloat(this.dataset.balance);
                const input = document.querySelector(`.invoice-allocation-input[data-invoice-id="${invoiceId}"]`);

                if (this.checked) {
                    const currentAllocation = state.allocations.invoices[invoiceId] || 0;
                    if (currentAllocation === 0) {
                        input.value = balance.toFixed(2);
                        state.allocations.invoices[invoiceId] = balance;
                    }
                } else {
                    input.value = '0.00';
                    state.allocations.invoices[invoiceId] = 0;
                }

                updateInvoiceTotals();
                updateSummary();
                validateAmounts();
            });
        });

        // Amount input handlers
        document.querySelectorAll('.invoice-allocation-input').forEach(input => {
            input.addEventListener('input', function() {
                const invoiceId = this.dataset.invoiceId;
                const amount = parseFloat(this.value) || 0;
                const checkbox = document.querySelector(`.invoice-checkbox[data-invoice-id="${invoiceId}"]`);

                checkbox.checked = amount > 0;
                state.allocations.invoices[invoiceId] = amount;

                updateInvoiceTotals();
                updateSummary();
                validateAmounts();
            });
        });

        // Clickable invoice rows
        document.querySelectorAll('.invoice-row-clickable').forEach(element => {
            element.addEventListener('click', function() {
                const invoiceId = this.dataset.invoiceId;
                const currentUrl = window.location.href;
                window.location.href = `/billing/invoice/${invoiceId}?return_url=${encodeURIComponent(currentUrl)}`;
            });
        });
    }

    function attachInstallmentEventListeners() {
        // Checkbox handlers
        document.querySelectorAll('.installment-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const installmentId = this.dataset.installmentId;
                const amount = parseFloat(this.dataset.amount);
                const input = document.querySelector(`.installment-allocation-input[data-installment-id="${installmentId}"]`);

                if (this.checked) {
                    const currentAllocation = state.allocations.installments[installmentId] || 0;
                    if (currentAllocation === 0) {
                        input.value = amount.toFixed(2);
                        state.allocations.installments[installmentId] = amount;
                    }
                } else {
                    input.value = '0.00';
                    state.allocations.installments[installmentId] = 0;
                }

                updateInstallmentTotals();
                updateSummary();
                validateAmounts();
            });
        });

        // Amount input handlers
        document.querySelectorAll('.installment-allocation-input').forEach(input => {
            input.addEventListener('input', function() {
                const installmentId = this.dataset.installmentId;
                const amount = parseFloat(this.value) || 0;
                const checkbox = document.querySelector(`.installment-checkbox[data-installment-id="${installmentId}"]`);

                checkbox.checked = amount > 0;
                state.allocations.installments[installmentId] = amount;

                updateInstallmentTotals();
                updateSummary();
                validateAmounts();
            });
        });
    }

    // ============================================
    // UPDATE FUNCTIONS
    // ============================================

    function updateInvoiceTotals() {
        const totalBalance = state.outstandingInvoices.reduce((sum, inv) =>
            sum + parseFloat(inv.balance_due), 0);

        const totalAllocation = Object.values(state.allocations.invoices).reduce((sum, val) => sum + val, 0);

        document.getElementById('total-invoice-balance').textContent = '₹' + totalBalance.toFixed(2);
        document.getElementById('total-invoice-allocation').textContent = totalAllocation.toFixed(2);
    }

    function updateInstallmentTotals() {
        const totalAmount = state.pendingInstallments.reduce((sum, inst) =>
            sum + parseFloat(inst.amount), 0);

        const totalAllocation = Object.values(state.allocations.installments).reduce((sum, val) => sum + val, 0);

        document.getElementById('total-installment-amount').textContent = '₹' + totalAmount.toFixed(2);
        document.getElementById('total-installment-allocation').textContent = totalAllocation.toFixed(2);
    }

    function toggleMethodDetails() {
        const creditCardAmount = parseFloat(creditCardField?.value) || 0;
        const debitCardAmount = parseFloat(debitCardField?.value) || 0;
        const upiAmount = parseFloat(upiField?.value) || 0;

        if (cardDetails) {
            const hasCardPayment = creditCardAmount > 0 || debitCardAmount > 0;
            cardDetails.classList.toggle('hidden', !hasCardPayment);
        }

        if (upiDetails) {
            upiDetails.classList.toggle('hidden', upiAmount === 0);
        }
    }

    function updateSummary() {
        // Calculate payment method totals
        const advanceAmount = parseFloat(advanceField?.value) || 0;
        const cashAmount = parseFloat(cashField?.value) || 0;
        const creditCardAmount = parseFloat(creditCardField?.value) || 0;
        const debitCardAmount = parseFloat(debitCardField?.value) || 0;
        const upiAmount = parseFloat(upiField?.value) || 0;

        const methodTotal = advanceAmount + cashAmount + creditCardAmount + debitCardAmount + upiAmount;

        // Calculate allocation totals
        const invoiceAllocation = Object.values(state.allocations.invoices).reduce((sum, val) => sum + val, 0);
        const installmentAllocation = Object.values(state.allocations.installments).reduce((sum, val) => sum + val, 0);
        const allocationTotal = invoiceAllocation + installmentAllocation;

        const difference = methodTotal - allocationTotal;

        // Update payment method breakdown
        let breakdownHTML = '<div class="space-y-2">';

        if (advanceAmount > 0) {
            breakdownHTML += `<div class="flex justify-between text-green-600"><span>Advance:</span><span>₹${advanceAmount.toFixed(2)}</span></div>`;
        }
        if (cashAmount > 0) {
            breakdownHTML += `<div class="flex justify-between"><span>Cash:</span><span>₹${cashAmount.toFixed(2)}</span></div>`;
        }
        if (creditCardAmount > 0) {
            breakdownHTML += `<div class="flex justify-between"><span>Credit Card:</span><span>₹${creditCardAmount.toFixed(2)}</span></div>`;
        }
        if (debitCardAmount > 0) {
            breakdownHTML += `<div class="flex justify-between"><span>Debit Card:</span><span>₹${debitCardAmount.toFixed(2)}</span></div>`;
        }
        if (upiAmount > 0) {
            breakdownHTML += `<div class="flex justify-between"><span>UPI:</span><span>₹${upiAmount.toFixed(2)}</span></div>`;
        }

        if (methodTotal === 0) {
            breakdownHTML += '<div class="text-sm text-gray-500 dark:text-gray-400 italic">No payment methods entered</div>';
        }

        breakdownHTML += '</div>';
        if (paymentBreakdownDiv) {
            paymentBreakdownDiv.innerHTML = breakdownHTML;
        }

        // Update totals
        document.getElementById('summary-invoice-allocation').textContent = invoiceAllocation.toFixed(2);
        document.getElementById('summary-installment-allocation').textContent = installmentAllocation.toFixed(2);
        document.getElementById('summary-total-allocated').textContent = allocationTotal.toFixed(2);
        document.getElementById('summary-method-total').textContent = methodTotal.toFixed(2);
        document.getElementById('summary-allocation-total').textContent = allocationTotal.toFixed(2);

        // Update difference
        const differenceAmountEl = document.getElementById('difference-amount');
        if (differenceAmountEl) {
            differenceAmountEl.textContent = '₹' + Math.abs(difference).toFixed(2);

            if (Math.abs(difference) > 0.01) {
                if (difference > 0) {
                    differenceAmountEl.className = 'text-lg font-bold text-orange-600 dark:text-orange-400';
                } else {
                    differenceAmountEl.className = 'text-lg font-bold text-red-600 dark:text-red-400';
                }
            } else {
                differenceAmountEl.className = 'text-lg font-bold text-green-600 dark:text-green-400';
            }
        }

        // Show approval threshold warning if needed
        const approvalWarning = document.getElementById('approval-threshold-warning');
        if (approvalWarning) {
            approvalWarning.classList.toggle('hidden', methodTotal < state.approvalThreshold);
        }
    }

    function validateAmounts() {
        // Calculate totals
        const advanceAmount = parseFloat(advanceField?.value) || 0;
        const cashAmount = parseFloat(cashField?.value) || 0;
        const creditCardAmount = parseFloat(creditCardField?.value) || 0;
        const debitCardAmount = parseFloat(debitCardField?.value) || 0;
        const upiAmount = parseFloat(upiField?.value) || 0;

        const methodTotal = advanceAmount + cashAmount + creditCardAmount + debitCardAmount + upiAmount;

        const invoiceAllocation = Object.values(state.allocations.invoices).reduce((sum, val) => sum + val, 0);
        const installmentAllocation = Object.values(state.allocations.installments).reduce((sum, val) => sum + val, 0);
        const allocationTotal = invoiceAllocation + installmentAllocation;

        const difference = methodTotal - allocationTotal;

        // Validate advance doesn't exceed balance
        if (advanceAmount > state.advanceBalance) {
            showValidationError(`Advance amount (₹${advanceAmount.toFixed(2)}) exceeds available balance (₹${state.advanceBalance.toFixed(2)})`);
            disableSubmitButtons();
            return;
        }

        // Validate payment methods match allocation
        if (Math.abs(difference) > 0.01) {
            const message = difference > 0
                ? `Payment methods total (₹${methodTotal.toFixed(2)}) exceeds allocation total (₹${allocationTotal.toFixed(2)}) by ₹${difference.toFixed(2)}`
                : `Payment methods total (₹${methodTotal.toFixed(2)}) is less than allocation total (₹${allocationTotal.toFixed(2)}) by ₹${Math.abs(difference).toFixed(2)}`;

            showValidationWarning(message);
            disableSubmitButtons();
        } else if (methodTotal > 0 && allocationTotal > 0) {
            showValidationSuccess('Payment methods match allocation total. Ready to submit!');
            enableSubmitButtons();
        } else if (methodTotal === 0 && allocationTotal === 0) {
            clearValidation();
            disableSubmitButtons();
        } else {
            clearValidation();
            disableSubmitButtons();
        }
    }

    function showValidationError(message) {
        if (validationDiv) {
            validationDiv.innerHTML = `
                <div class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <div class="flex items-start">
                        <i class="fas fa-times-circle text-red-600 mr-2 mt-0.5"></i>
                        <span class="text-sm text-red-800 dark:text-red-200">${message}</span>
                    </div>
                </div>`;
        }
    }

    function showValidationWarning(message) {
        if (validationDiv) {
            validationDiv.innerHTML = `
                <div class="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                    <div class="flex items-start">
                        <i class="fas fa-exclamation-triangle text-orange-600 mr-2 mt-0.5"></i>
                        <span class="text-sm text-orange-800 dark:text-orange-200">${message}</span>
                    </div>
                </div>`;
        }
    }

    function showValidationSuccess(message) {
        if (validationDiv) {
            validationDiv.innerHTML = `
                <div class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                    <div class="flex items-start">
                        <i class="fas fa-check-circle text-green-600 mr-2 mt-0.5"></i>
                        <span class="text-sm text-green-800 dark:text-green-200">${message}</span>
                    </div>
                </div>`;
        }
    }

    function clearValidation() {
        if (validationDiv) {
            validationDiv.innerHTML = '';
        }
    }

    function enableSubmitButtons() {
        const submitButton = document.getElementById('submit-button');
        const draftButton = document.getElementById('save-draft-button');

        if (submitButton) submitButton.disabled = false;
        if (draftButton) draftButton.disabled = false;
    }

    function disableSubmitButtons() {
        const submitButton = document.getElementById('submit-button');
        const draftButton = document.getElementById('save-draft-button');

        if (submitButton) submitButton.disabled = true;
        if (draftButton) draftButton.disabled = true;
    }

    // ============================================
    // FORM SUBMISSION
    // ============================================

    if (form) {
        form.addEventListener('submit', function(e) {
            console.log('[SUBMIT] Form submission validation starting...');

            // Calculate totals
            const advanceAmount = parseFloat(advanceField?.value) || 0;
            const cashAmount = parseFloat(cashField?.value) || 0;
            const creditCardAmount = parseFloat(creditCardField?.value) || 0;
            const debitCardAmount = parseFloat(debitCardField?.value) || 0;
            const upiAmount = parseFloat(upiField?.value) || 0;

            const methodTotal = advanceAmount + cashAmount + creditCardAmount + debitCardAmount + upiAmount;

            const invoiceAllocation = Object.values(state.allocations.invoices).reduce((sum, val) => sum + val, 0);
            const installmentAllocation = Object.values(state.allocations.installments).reduce((sum, val) => sum + val, 0);
            const allocationTotal = invoiceAllocation + installmentAllocation;

            // Validate advance
            if (advanceAmount > state.advanceBalance) {
                e.preventDefault();
                alert(`Advance amount (₹${advanceAmount.toFixed(2)}) exceeds available balance (₹${state.advanceBalance.toFixed(2)})`);
                return false;
            }

            // Validate payment methods match allocation
            if (Math.abs(methodTotal - allocationTotal) > 0.01) {
                e.preventDefault();
                alert('Payment methods total must match allocation total. Please adjust amounts.');
                return false;
            }

            // Validate card details if card payment entered
            if (creditCardAmount > 0 || debitCardAmount > 0) {
                const last4 = document.getElementById('card_number_last4')?.value;
                const cardType = document.getElementById('card_type')?.value;

                if (!last4 || !/^\d{4}$/.test(last4)) {
                    e.preventDefault();
                    alert('Please enter the last 4 digits of the card');
                    return false;
                }
                if (!cardType) {
                    e.preventDefault();
                    alert('Please select card type');
                    return false;
                }
            }

            // Validate UPI details if UPI payment entered
            if (upiAmount > 0) {
                const upiId = document.getElementById('upi_id')?.value;
                if (!upiId || !upiId.trim()) {
                    e.preventDefault();
                    alert('Please enter UPI ID');
                    return false;
                }
            }

            // Add allocation data to form
            Object.entries(state.allocations.invoices).forEach(([invoiceId, amount]) => {
                if (amount > 0) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = `invoice_allocations[${invoiceId}]`;
                    input.value = amount;
                    form.appendChild(input);
                }
            });

            Object.entries(state.allocations.installments).forEach(([installmentId, amount]) => {
                if (amount > 0) {
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = `installment_allocations[${installmentId}]`;
                    input.value = amount;
                    form.appendChild(input);
                }
            });

            console.log('[SUBMIT] Validation passed');
        });
    }

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================

    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    }

    function getStatusClass(status) {
        const classes = {
            'pending': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
            'partial': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
            'overdue': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
            'paid': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
            'waived': 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300'
        };
        return classes[status] || classes['pending'];
    }

})();
</script>
