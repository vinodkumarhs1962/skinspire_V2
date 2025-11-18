/**
 * Package Payment Plan Create Form - Cascading Workflow
 * Handles: Patient Autocomplete → Invoice Selection → Auto-populate
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

let selectedPatientId = null;
let selectedPatientData = null;
let searchTimeout = null;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    setMinimumDate();
});

function initializeEventListeners() {
    // Patient search
    const searchInput = document.getElementById('patient-search');
    if (searchInput) {
        searchInput.addEventListener('input', handlePatientSearch);
        searchInput.addEventListener('focus', function() {
            if (this.value.length >= 2) {
                document.getElementById('patient-results').classList.remove('hidden');
            }
        });
    }

    // Clear patient button
    const clearButton = document.getElementById('clear-patient');
    if (clearButton) {
        clearButton.addEventListener('click', clearPatientSelection);
    }

    // Invoice selection
    const invoiceSelect = document.getElementById('invoice-select');
    if (invoiceSelect) {
        invoiceSelect.addEventListener('change', handleInvoiceSelection);
    }

    // Form submission
    const form = document.getElementById('payment-plan-form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    // Close error modal
    const closeModalBtn = document.getElementById('close-error-modal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeErrorModal);
    }

    // Click outside to close patient results
    document.addEventListener('click', function(e) {
        const searchInput = document.getElementById('patient-search');
        const resultsDiv = document.getElementById('patient-results');

        if (searchInput && resultsDiv && !searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
            resultsDiv.classList.add('hidden');
        }
    });
}

function setMinimumDate() {
    const dateInput = document.getElementById('first_installment_date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.setAttribute('min', today);
        dateInput.value = today;
    }
}

// ============================================================================
// STEP 1: PATIENT SEARCH & SELECTION
// ============================================================================

function handlePatientSearch(e) {
    const query = e.target.value.trim();

    // Clear previous timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    // Hide results if query too short
    if (query.length < 2) {
        document.getElementById('patient-results').classList.add('hidden');
        return;
    }

    // Show loading
    document.getElementById('patient-loading').classList.remove('hidden');

    // Debounce search
    searchTimeout = setTimeout(() => {
        searchPatients(query);
    }, 300);
}

async function searchPatients(query) {
    try {
        const response = await fetch(`/api/universal/patients/search?q=${encodeURIComponent(query)}`);

        if (!response.ok) {
            throw new Error('Failed to search patients');
        }

        const data = await response.json();

        if (data.success) {
            displayPatientResults(data.results || []);
        } else {
            showError(data.error || 'Failed to search patients');
        }
    } catch (error) {
        console.error('Patient search error:', error);
        showError('Failed to search patients. Please try again.');
    } finally {
        document.getElementById('patient-loading').classList.add('hidden');
    }
}

function displayPatientResults(results) {
    const resultsDiv = document.getElementById('patient-results');

    if (results.length === 0) {
        resultsDiv.innerHTML = `
            <div class="p-4 text-center text-gray-500 dark:text-gray-400">
                <i class="fas fa-search mr-2"></i>
                No patients found
            </div>
        `;
        resultsDiv.classList.remove('hidden');
        return;
    }

    resultsDiv.innerHTML = results.map(patient => `
        <div class="patient-result-item p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-200 dark:border-gray-600 last:border-b-0"
             data-patient-id="${patient.patient_id}"
             data-patient-name="${escapeHtml(patient.patient_name || patient.full_name || '')}"
             data-patient-mrn="${escapeHtml(patient.mrn || '')}"
             data-patient-phone="${escapeHtml(patient.phone || '')}"
             data-patient-email="${escapeHtml(patient.email || '')}"
             onclick="selectPatient(this)">
            <div class="flex items-center">
                <i class="fas fa-user-circle text-blue-500 text-2xl mr-3"></i>
                <div class="flex-1">
                    <div class="font-semibold text-gray-900 dark:text-white">
                        ${escapeHtml(patient.patient_name || patient.full_name || 'Unknown')}
                    </div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">
                        <span class="mr-3"><strong>MRN:</strong> ${escapeHtml(patient.mrn || 'N/A')}</span>
                        ${patient.phone ? `<span><i class="fas fa-phone mr-1"></i>${escapeHtml(patient.phone)}</span>` : ''}
                    </div>
                </div>
            </div>
        </div>
    `).join('');

    resultsDiv.classList.remove('hidden');
}

function selectPatient(element) {
    selectedPatientId = element.dataset.patientId;
    selectedPatientData = {
        patient_id: element.dataset.patientId,
        patient_name: element.dataset.patientName,
        mrn: element.dataset.patientMrn,
        phone: element.dataset.patientPhone,
        email: element.dataset.patientEmail
    };

    // Update hidden field
    document.getElementById('patient_id').value = selectedPatientId;

    // Display selected patient
    document.getElementById('selected-patient-name').textContent = selectedPatientData.patient_name;
    document.getElementById('selected-patient-mrn').textContent = selectedPatientData.mrn;

    if (selectedPatientData.phone) {
        document.getElementById('selected-patient-phone').textContent = selectedPatientData.phone;
        document.getElementById('selected-patient-phone-container').classList.remove('hidden');
    } else {
        document.getElementById('selected-patient-phone-container').classList.add('hidden');
    }

    if (selectedPatientData.email) {
        document.getElementById('selected-patient-email').textContent = selectedPatientData.email;
        document.getElementById('selected-patient-email-container').classList.remove('hidden');
    } else {
        document.getElementById('selected-patient-email-container').classList.add('hidden');
    }

    // Show selected patient card
    document.getElementById('selected-patient-card').classList.remove('hidden');

    // Hide search results
    document.getElementById('patient-results').classList.add('hidden');

    // Clear search input
    document.getElementById('patient-search').value = '';

    // Load invoices for this patient
    loadPatientInvoices(selectedPatientId);
}

function clearPatientSelection() {
    selectedPatientId = null;
    selectedPatientData = null;

    // Clear hidden field
    document.getElementById('patient_id').value = '';

    // Hide selected patient card
    document.getElementById('selected-patient-card').classList.add('hidden');

    // Hide invoice section
    document.getElementById('invoice-selection-section').classList.add('hidden');

    // Hide plan details section
    document.getElementById('plan-details-section').classList.add('hidden');

    // Reset form
    document.getElementById('invoice-select').innerHTML = '<option value="">Select invoice with package...</option>';
    document.getElementById('payment-plan-form').reset();

    // Disable submit button
    document.getElementById('submit-button').disabled = true;

    // Clear search input
    document.getElementById('patient-search').value = '';
}

// ============================================================================
// STEP 2: INVOICE LOADING & SELECTION
// ============================================================================

async function loadPatientInvoices(patientId) {
    // Show invoice section
    document.getElementById('invoice-selection-section').classList.remove('hidden');

    // Show loading
    document.getElementById('invoice-loading').classList.remove('hidden');
    document.getElementById('no-invoices-message').classList.add('hidden');

    try {
        const response = await fetch(`/api/package/patient/${patientId}/invoices-with-packages`);

        if (!response.ok) {
            throw new Error('Failed to load invoices');
        }

        const data = await response.json();

        if (data.success) {
            populateInvoiceDropdown(data.invoices || []);
        } else {
            showError(data.error || 'Failed to load invoices');
        }
    } catch (error) {
        console.error('Invoice loading error:', error);
        showError('Failed to load invoices. Please try again.');
    } finally {
        document.getElementById('invoice-loading').classList.add('hidden');
    }
}

function populateInvoiceDropdown(invoices) {
    const select = document.getElementById('invoice-select');

    if (invoices.length === 0) {
        select.innerHTML = '<option value="">No invoices with packages found</option>';
        select.disabled = true;
        document.getElementById('no-invoices-message').classList.remove('hidden');
        return;
    }

    select.disabled = false;
    document.getElementById('no-invoices-message').classList.add('hidden');

    select.innerHTML = '<option value="">Select invoice with package...</option>' +
        invoices.map(inv => {
            const displayText = `${inv.invoice_number} - ${inv.package_name} - ₹${formatCurrency(inv.line_item_total)} (${inv.invoice_date})`;
            return `<option value="${inv.invoice_id}"
                            data-package-id="${inv.package_id}"
                            data-package-name="${escapeHtml(inv.package_name)}"
                            data-total-amount="${inv.line_item_total}"
                            data-invoice-number="${escapeHtml(inv.invoice_number)}">
                        ${escapeHtml(displayText)}
                    </option>`;
        }).join('');
}

function handleInvoiceSelection(e) {
    const selectedOption = e.target.options[e.target.selectedIndex];

    if (!selectedOption.value) {
        // Hide plan details if no invoice selected
        document.getElementById('plan-details-section').classList.add('hidden');
        document.getElementById('submit-button').disabled = true;
        return;
    }

    // Get data from selected option
    const invoiceId = selectedOption.value;
    const packageId = selectedOption.dataset.packageId;
    const packageName = selectedOption.dataset.packageName;
    const totalAmount = parseFloat(selectedOption.dataset.totalAmount);

    // Update hidden fields
    document.getElementById('invoice_id').value = invoiceId;
    document.getElementById('package_id').value = packageId;
    document.getElementById('total_amount').value = totalAmount;

    // Update display fields
    document.getElementById('package_name_display').value = packageName;
    document.getElementById('total_amount_display').value = '₹' + formatCurrency(totalAmount);

    // Show plan details section
    document.getElementById('plan-details-section').classList.remove('hidden');

    // Enable submit button
    document.getElementById('submit-button').disabled = false;

    // Scroll to plan details
    document.getElementById('plan-details-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ============================================================================
// FORM SUBMISSION
// ============================================================================

function handleFormSubmit(e) {
    // Validate required fields
    const patientId = document.getElementById('patient_id').value;
    const invoiceId = document.getElementById('invoice_id').value;
    const packageId = document.getElementById('package_id').value;
    const totalSessions = document.getElementById('total_sessions').value;
    const installmentCount = document.getElementById('installment_count').value;
    const firstInstallmentDate = document.getElementById('first_installment_date').value;

    if (!patientId) {
        e.preventDefault();
        showError('Please select a patient');
        return false;
    }

    if (!invoiceId) {
        e.preventDefault();
        showError('Please select an invoice');
        return false;
    }

    if (!totalSessions || totalSessions < 1) {
        e.preventDefault();
        showError('Please enter the number of sessions (minimum 1)');
        return false;
    }

    if (!installmentCount || installmentCount < 1) {
        e.preventDefault();
        showError('Please enter the number of installments (minimum 1)');
        return false;
    }

    if (!firstInstallmentDate) {
        e.preventDefault();
        showError('Please select the first installment date');
        return false;
    }

    // Disable submit button to prevent double submission
    document.getElementById('submit-button').disabled = true;
    document.getElementById('submit-button').innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creating...';

    return true;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatCurrency(amount) {
    return parseFloat(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    document.getElementById('error-message').textContent = message;
    document.getElementById('error-modal').classList.remove('hidden');
}

function closeErrorModal() {
    document.getElementById('error-modal').classList.add('hidden');
}
