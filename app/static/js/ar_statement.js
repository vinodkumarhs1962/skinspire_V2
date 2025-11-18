/**
 * AR Statement Modal JavaScript
 * Handles patient AR statement display with transaction history
 *
 * Version: 1.0
 * Created: 2025-11-13
 */

/**
 * Open AR statement modal for a patient
 * @param {string} patientId - Patient UUID
 * @param {string} highlightId - Optional transaction ID to highlight (invoice_id, payment_id, credit_note_id, or plan_id)
 */
function openARStatementModal(patientId, highlightId = null) {
    if (!patientId) {
        showError('Patient ID is required');
        return;
    }

    // Build URL with optional highlight parameter
    const url = `/api/ar-statement/${patientId}${highlightId ? `?highlight_id=${highlightId}` : ''}`;

    // Show loading state
    const modal = document.getElementById('arStatementModal');
    if (modal) {
        modal.classList.remove('hidden');
        showARStatementLoading();
    }

    // Fetch AR statement data
    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(result => {
            if (result.success) {
                populateARStatementModal(result);
            } else {
                showError('Failed to load AR statement: ' + (result.error || 'Unknown error'));
                closeARStatementModal();
            }
        })
        .catch(error => {
            console.error('Error loading AR statement:', error);
            showError('Failed to load AR statement. Please try again.');
            closeARStatementModal();
        });
}

/**
 * Show loading state in AR statement modal
 */
function showARStatementLoading() {
    const tbody = document.getElementById('ar-transactions-body');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-gray-500">
                    <i class="fas fa-spinner fa-spin mr-2"></i>Loading transactions...
                </td>
            </tr>
        `;
    }
}

/**
 * Populate modal with AR statement data
 * @param {Object} data - AR statement data from API
 */
function populateARStatementModal(data) {
    // Patient info
    const patientInfo = data.patient_info || {};
    setElementText('ar-patient-name', patientInfo.full_name || '—');
    setElementText('ar-patient-number', patientInfo.patient_number || '—');
    setElementText('ar-as-of-date', formatDate(data.as_of_date));

    // Current balance with color coding
    const summary = data.summary || {};
    const balance = parseFloat(summary.current_balance || 0);
    const balanceElement = document.getElementById('ar-current-balance');
    if (balanceElement) {
        balanceElement.textContent = formatCurrency(balance);
        // Green for credit (patient has credit), red for debit (patient owes)
        balanceElement.className = balance < 0
            ? 'text-2xl font-bold text-green-600 dark:text-green-400'
            : 'text-2xl font-bold text-red-600 dark:text-red-400';
    }

    // Transactions table
    populateTransactionsTable(data.transactions || []);

    // Summary totals
    const totalInvoiced = parseFloat(summary.total_invoiced || 0);
    const totalPaid = parseFloat(summary.total_paid || 0);
    const totalCreditNotes = parseFloat(summary.total_credit_notes || 0);
    const totalCredit = totalPaid + totalCreditNotes;

    setElementText('ar-total-debit', formatCurrency(totalInvoiced));
    setElementText('ar-total-credit', formatCurrency(totalCredit));
    setElementText('ar-total-balance', formatCurrency(balance));

    setElementText('ar-summary-invoiced', formatCurrency(totalInvoiced));
    setElementText('ar-summary-paid', formatCurrency(totalPaid));
    setElementText('ar-summary-credit-notes', formatCurrency(totalCreditNotes));

    const summaryBalanceElement = document.getElementById('ar-summary-balance');
    if (summaryBalanceElement) {
        summaryBalanceElement.textContent = formatCurrency(balance);
        summaryBalanceElement.className = balance < 0
            ? 'text-lg font-bold text-green-600 dark:text-green-400'
            : 'text-lg font-bold text-red-600 dark:text-red-400';
    }
}

/**
 * Populate transactions table
 * @param {Array} transactions - Array of transaction objects
 */
function populateTransactionsTable(transactions) {
    const tbody = document.getElementById('ar-transactions-body');
    if (!tbody) return;

    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-gray-500">
                    No transactions found for this patient.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = '';

    transactions.forEach(txn => {
        const row = document.createElement('tr');

        // Add highlighting class if this transaction should be highlighted
        if (txn.is_highlighted) {
            row.className = 'bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400';
        } else {
            row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors';
        }

        // Format balance with color
        const balance = parseFloat(txn.current_balance || 0);
        const balanceClass = balance < 0
            ? 'text-green-600 dark:text-green-400 font-semibold'
            : 'text-red-600 dark:text-red-400 font-semibold';

        row.innerHTML = `
            <td class="px-4 py-3 text-sm text-gray-700 dark:text-gray-300">${formatDate(txn.transaction_date)}</td>
            <td class="px-4 py-3 text-sm">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getEntryTypeBadgeClass(txn.entry_type)}">
                    ${formatEntryType(txn.entry_type)}
                </span>
            </td>
            <td class="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">${txn.reference_number || '—'}</td>
            <td class="px-4 py-3 text-sm text-right text-gray-700 dark:text-gray-300">${formatCurrency(parseFloat(txn.debit_amount || 0))}</td>
            <td class="px-4 py-3 text-sm text-right text-gray-700 dark:text-gray-300">${formatCurrency(parseFloat(txn.credit_amount || 0))}</td>
            <td class="px-4 py-3 text-sm text-right ${balanceClass}">${formatCurrency(balance)}</td>
        `;

        tbody.appendChild(row);
    });
}

/**
 * Get badge class for entry type
 * @param {string} entryType - Entry type (invoice, payment, credit_note)
 * @returns {string} Tailwind CSS classes for badge
 */
function getEntryTypeBadgeClass(entryType) {
    const classes = {
        'invoice': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        'payment': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        'credit_note': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
        'debit_note': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
    };
    return classes[entryType] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
}

/**
 * Format entry type for display
 * @param {string} entryType - Entry type
 * @returns {string} Formatted entry type
 */
function formatEntryType(entryType) {
    const types = {
        'invoice': 'Invoice',
        'payment': 'Payment',
        'credit_note': 'Credit Note',
        'debit_note': 'Debit Note'
    };
    return types[entryType] || entryType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Close AR statement modal
 */
function closeARStatementModal() {
    const modal = document.getElementById('arStatementModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Print AR statement
 */
function printARStatement() {
    window.print();
}

/**
 * Helper function to set element text safely
 * @param {string} elementId - Element ID
 * @param {string} text - Text to set
 */
function setElementText(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}

/**
 * Format currency value
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '₹0.00';
    }

    const absAmount = Math.abs(amount);
    const formatted = absAmount.toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });

    return amount < 0 ? `₹${formatted}` : `₹${formatted}`;
}

/**
 * Format date for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
function formatDate(dateString) {
    if (!dateString) return '—';

    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '—';

        // Format as DD-MMM-YYYY (e.g., 13-Nov-2025)
        const day = date.getDate().toString().padStart(2, '0');
        const month = date.toLocaleString('en-US', { month: 'short' });
        const year = date.getFullYear();

        return `${day}-${month}-${year}`;
    } catch (error) {
        console.error('Error formatting date:', error);
        return '—';
    }
}

/**
 * Show error message
 * @param {string} message - Error message to display
 */
function showError(message) {
    // Use existing notification system if available, otherwise alert
    if (typeof showNotification === 'function') {
        showNotification(message, 'error');
    } else if (typeof window.showToast === 'function') {
        window.showToast(message, 'error');
    } else {
        alert(message);
    }
}

// Close modal on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('arStatementModal');
        if (modal && !modal.classList.contains('hidden')) {
            closeARStatementModal();
        }
    }
});
