// app/static/js/pages/invoice.js
// Clean version - Works with InvoiceItemComponent class

console.log("📄 invoice.js loaded");

document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ invoice.js initialized");

    // NOTE: Line item operations handled by InvoiceItemComponent (initialized in template)
    // This file only handles: patient search, GST toggle, form submission

    initializePatientSearch();
    initializeGSTToggle();
    initializeFormSubmission();
});

// =================================================================
// PATIENT SEARCH
// =================================================================
function initializePatientSearch() {
    const patientSearch = document.getElementById('patient_search');  // Fixed: was 'patient-search'
    const patientResults = document.getElementById('patient_dropdown');  // Fixed: was 'patient-search-results'
    const patientIdInput = document.getElementById('patient_id');
    const patientNameInput = document.getElementById('patient_name');
    const patientInfo = document.getElementById('selected-patient-info');
    const invoiceForm = document.getElementById('invoice-form');
    const loadingIndicator = document.getElementById('patient_loading');

    if (!patientSearch || !patientResults) {
        console.warn("Patient search elements missing:", {
            patientSearch: !!patientSearch,
            patientResults: !!patientResults
        });
        return;
    }

    console.log("✅ Patient search initialized");

    // Debounce function
    const debounce = (func, delay) => {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    };

    // Search patients
    const searchPatients = debounce(function(query) {
        if (!query || query.length < 2) {
            patientResults.innerHTML = '';
            patientResults.classList.add('hidden');
            if (loadingIndicator) loadingIndicator.classList.add('hidden');
            return;
        }

        // Show loading
        if (loadingIndicator) loadingIndicator.classList.remove('hidden');

        fetch(`/invoice/web_api/patient/search?q=${encodeURIComponent(query)}`, {
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (loadingIndicator) loadingIndicator.classList.add('hidden');
            patientResults.innerHTML = '';

            if (data.length === 0) {
                patientResults.innerHTML = '<div class="p-3 text-gray-500 dark:text-gray-400">No patients found</div>';
                patientResults.classList.remove('hidden');
                return;
            }

            data.forEach(patient => {
                const div = document.createElement('div');
                div.className = 'p-3 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-200 dark:border-gray-600 last:border-b-0';
                div.innerHTML = `
                    <div class="font-semibold text-gray-900 dark:text-white">${patient.name}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">MRN: ${patient.mrn}</div>
                    ${patient.contact ? `<div class="text-sm text-gray-600 dark:text-gray-400">${patient.contact}</div>` : ''}
                `;

                div.addEventListener('click', function() {
                    if (patientIdInput) patientIdInput.value = patient.id;  // API returns 'id' not 'patient_id'
                    if (patientNameInput) patientNameInput.value = patient.name;
                    patientSearch.value = `${patient.name} - MRN: ${patient.mrn}`;

                    // Update display (if exists)
                    const nameDisplay = document.getElementById('patient-name-display');
                    const mrnDisplay = document.getElementById('patient-mrn-display');
                    const contactDisplay = document.getElementById('patient-contact-display');

                    if (nameDisplay) nameDisplay.textContent = patient.name;
                    if (mrnDisplay) mrnDisplay.textContent = `MRN: ${patient.mrn}`;
                    if (contactDisplay) contactDisplay.textContent = patient.contact || '';
                    if (patientInfo) patientInfo.classList.remove('hidden');

                    patientResults.classList.add('hidden');
                    console.log('✅ Patient selected:', patient.name, 'ID:', patient.id);
                });

                patientResults.appendChild(div);
            });

            patientResults.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error searching patients:', error);
            if (loadingIndicator) loadingIndicator.classList.add('hidden');
            patientResults.innerHTML = '<div class="p-3 text-red-500">Error searching patients</div>';
            patientResults.classList.remove('hidden');
        });
    }, 300);

    // Event listeners
    patientSearch.addEventListener('input', function() {
        searchPatients(this.value.trim());
    });

    patientSearch.addEventListener('focus', function() {
        // If user focuses and there's already a search query, re-run search
        if (this.value.trim().length >= 2) {
            searchPatients(this.value.trim());
        }
    });

    // Hide results when clicking outside
    document.addEventListener('click', function(e) {
        if (!patientSearch.contains(e.target) && !patientResults.contains(e.target)) {
            patientResults.classList.add('hidden');
        }
    });

    console.log("✅ Patient search initialized");
}

// =================================================================
// GST TOGGLE
// =================================================================
function initializeGSTToggle() {
    const isGstInvoice = document.getElementById('is_gst_invoice');
    const isInterstate = document.getElementById('is_interstate');
    const gstElements = document.querySelectorAll('.gst-element');
    const cgstRow = document.querySelector('.cgst-row');
    const sgstRow = document.querySelector('.sgst-row');
    const igstRow = document.querySelector('.igst-row');

    if (!isGstInvoice) {
        console.warn("GST invoice checkbox not found");
        return;
    }

    function toggleGstElements() {
        const isGstChecked = isGstInvoice.checked;
        const isInterstateChecked = isInterstate?.checked || false;

        gstElements.forEach(el => {
            el.style.display = isGstChecked ? '' : 'none';
        });

        // Show/hide CGST/SGST vs IGST based on interstate
        if (isGstChecked && isInterstateChecked) {
            if (cgstRow) cgstRow.classList.add('hidden');
            if (sgstRow) sgstRow.classList.add('hidden');
            if (igstRow) igstRow.classList.remove('hidden');
        } else {
            if (cgstRow) cgstRow.classList.remove('hidden');
            if (sgstRow) sgstRow.classList.remove('hidden');
            if (igstRow) igstRow.classList.add('hidden');
        }
    }

    toggleGstElements();
    isGstInvoice.addEventListener('change', toggleGstElements);
    if (isInterstate) {
        isInterstate.addEventListener('change', toggleGstElements);
    }

    console.log("✅ GST toggle initialized");
}

// =================================================================
// FORM SUBMISSION
// =================================================================
function initializeFormSubmission() {
    const form = document.getElementById('invoice-form');
    const submitButton = document.querySelector('button[type="submit"]');

    if (!form) {
        console.warn("Invoice form not found");
        return;
    }

    form.addEventListener('submit', function(e) {
        // Validate patient
        const patientId = document.getElementById('patient_id')?.value;
        const patientSearch = document.getElementById('patient_search')?.value;

        if (!patientId && !patientSearch) {
            e.preventDefault();
            alert('Please select a patient.');
            document.getElementById('patient_search')?.focus();
            return false;
        }

        // Validate line items
        const lineItems = document.querySelectorAll('.line-item-row');
        if (lineItems.length === 0) {
            e.preventDefault();
            alert('Please add at least one line item.');
            return false;
        }

        // Show loading state
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creating Invoice...';
        }

        // Prepare line items for submission
        prepareLineItemsForSubmission();

        console.log("✅ Form validated and submitting");
    });

    console.log("✅ Form submission initialized");
}

// =================================================================
// HELPER FUNCTIONS
// =================================================================
function prepareLineItemsForSubmission() {
    const form = document.getElementById('invoice-form');
    const lineItems = document.querySelectorAll('.line-item-row');

    // Remove old line item fields
    form.querySelectorAll('input[name^="line_items-"]').forEach(el => el.remove());

    lineItems.forEach((row, index) => {
        const itemType = row.querySelector('.item-type')?.value;
        const itemId = row.querySelector('.item-id')?.value;
        const itemName = row.querySelector('.item-name')?.value || row.querySelector('.item-search')?.value;
        const quantity = row.querySelector('.quantity')?.value;
        const unitPrice = row.querySelector('.unit-price')?.value;
        const discountPercent = row.querySelector('.discount-percent')?.value;

        const addField = (name, value) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = name;
            input.value = value || '';
            form.appendChild(input);
        };

        addField(`line_items-${index}-item_type`, itemType);
        addField(`line_items-${index}-item_id`, itemId);
        addField(`line_items-${index}-item_name`, itemName);
        addField(`line_items-${index}-quantity`, quantity);
        addField(`line_items-${index}-unit_price`, unitPrice);
        addField(`line_items-${index}-discount_percent`, discountPercent);

        // Medicine-specific fields for all medicine-based types
        const medicineBasedTypes = ['OTC', 'Prescription', 'Product', 'Consumable'];
        if (medicineBasedTypes.includes(itemType)) {
            const batch = row.querySelector('.batch-select')?.value;
            const expiryDate = row.querySelector('.expiry-date')?.value;
            addField(`line_items-${index}-batch`, batch);
            addField(`line_items-${index}-expiry_date`, expiryDate);

            // Check if this line item has multiple batch allocations
            const batchAllocations = row.dataset.batchAllocations;
            if (batchAllocations) {
                addField(`line_items-${index}-batch_allocations`, batchAllocations);
            }
        }
    });

    // Set line items count
    let countField = form.querySelector('input[name="line_items_count"]');
    if (!countField) {
        countField = document.createElement('input');
        countField.type = 'hidden';
        countField.name = 'line_items_count';
        form.appendChild(countField);
    }
    countField.value = lineItems.length;

    console.log(`✅ ${lineItems.length} line items prepared for submission`);
}
