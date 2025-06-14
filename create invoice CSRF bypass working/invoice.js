// app/static/js/pages/invoice.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeInvoiceComponents();
    
    // Initialize patient search
    initializePatientSearch();
    
    // Initialize GST toggle
    initializeGSTToggle();
    
    // Initialize form submission
    initializeFormSubmission();
    
    // Optimize invoice header layout
    improveInvoiceHeaderLayout();
    
    // Log page initialization to help debugging
    console.log("Invoice page initialized");
});

function improveInvoiceHeaderLayout() {
    // Fix the header layout for better appearance
    console.log("Improving invoice header layout");
    
    // Make header text smaller
    const headerFields = document.querySelectorAll('.invoice-header label, .invoice-header .text-lg');
    headerFields.forEach(field => {
        field.classList.add('text-sm');
        if (field.classList.contains('text-lg')) {
            field.classList.remove('text-lg');
        }
    });
    
    // Establish a proper grid layout
    const headerContainer = document.querySelector('.invoice-header');
    if (headerContainer) {
        // Set up a clean 2-column grid
        headerContainer.style.display = 'grid';
        headerContainer.style.gridTemplateColumns = 'repeat(2, 1fr)';
        headerContainer.style.gap = '1rem';
        headerContainer.style.marginBottom = '2rem';
        
        // Arrange the first column (patient info)
        const patientSection = headerContainer.querySelector('.col-span-1');
        if (patientSection) {
            patientSection.style.gridColumn = '1';
            patientSection.style.gridRow = '1 / span 3';
        }
        
        // Organize the second and third columns
        const columns = Array.from(headerContainer.children);
        if (columns.length >= 3) {
            // Invoice Date and Branch in second column
            columns[1].style.gridColumn = '2';
            columns[1].style.gridRow = '1';
            
            // GST and Currency in third column/row
            columns[2].style.gridColumn = '2';
            columns[2].style.gridRow = '2';
        }
        
        // Make sure line items section has proper spacing
        const lineItemsSection = document.querySelector('.line-items-container');
        if (lineItemsSection) {
            lineItemsSection.style.marginTop = '2rem';
        }
    }
    
    // Hide fields that are handled by the backend automatically
    const fieldsToHide = [
        document.querySelector('label[for="invoice_type"]'),
        document.querySelector('label[for="is_gst_invoice"]'),
        document.querySelector('label[for="is_interstate"]')
    ];
    
    fieldsToHide.forEach(field => {
        if (field) {
            const container = field.closest('.mb-4');
            if (container) {
                container.style.display = 'none';
            }
        }
    });
}

function initializeInvoiceComponents() {
    // Elements
    const lineItemsContainer = document.getElementById('line-items-container');
    const addItemButton = document.getElementById('add-line-item');
    const noItemsRow = document.getElementById('no-items-row');
    const lineItemTemplate = document.getElementById('line-item-template');
    
    // Variables
    let lineItemCount = 0;
    
    // If no template element, silently fail
    if (!lineItemTemplate || !lineItemsContainer) {
        console.warn("Line item template or container missing");
        return;
    }
    
    // Add new line item
    if (addItemButton) {
        addItemButton.addEventListener('click', function() {
            console.log("Add item button clicked");
            
            // Hide the "no items" row if exists
            if (noItemsRow) {
                noItemsRow.style.display = 'none';
            }
            
            // Create new row from template
            const content = lineItemTemplate.content.cloneNode(true);
            const row = content.querySelector('.line-item-row');
            
            // Replace {index} placeholders
            const currentIndex = lineItemCount;
            const rowHtml = row.innerHTML;
            row.innerHTML = rowHtml.replace(/{index}/g, currentIndex);
            
            // Add to container
            lineItemsContainer.appendChild(row);
            
            // Initialize row
            initializeLineItem(row);
            
            // Update line numbers and calculate totals
            updateLineNumbers();
            calculateTotals();
            
            // Increment counter
            lineItemCount++;
            
            console.log("Line item added, current count:", lineItemCount);
        });
    }
    
    // Event delegation for row actions
    if (lineItemsContainer) {
        lineItemsContainer.addEventListener('click', function(e) {
            const target = e.target;
            
            // Handle delete button
            if (target.closest('.remove-line-item')) {
                removeItem(target.closest('.line-item-row'));
            }
            
            // Handle save button
            if (target.closest('.save-line-item')) {
                saveItem(target.closest('.line-item-row'));
            }
        });
        
        // Event delegation for input changes
        lineItemsContainer.addEventListener('input', function(e) {
            if (e.target.matches('.quantity, .unit-price, .discount-percent')) {
                calculateLineTotal(e.target.closest('.line-item-row'));
                calculateTotals();
            }
        });
    }
    
    // Initialize existing line items (if any)
    document.querySelectorAll('.line-item-row').forEach(row => {
        initializeLineItem(row);
    });
    
    // Calculate initial totals
    calculateTotals();
    
    // Make functions accessible globally
    window.invoiceComponentFunctions = {
        addNewItem: function() {
            addItemButton.click();
        },
        removeItem: removeItem,
        saveItem: saveItem,
        updateLineNumbers: updateLineNumbers,
        calculateLineTotal: calculateLineTotal,
        calculateTotals: calculateTotals
    };
    
    // Helper functions
    function removeItem(row) {
        if (!row) return;
        
        // Remove row from DOM
        row.remove();
        
        // Show "no items" row if empty
        if (lineItemsContainer.querySelectorAll('.line-item-row').length === 0 && noItemsRow) {
            noItemsRow.style.display = '';
        }
        
        // Update line numbers and recalculate totals
        updateLineNumbers();
        calculateTotals();
        
        console.log("Line item removed");
    }
    
    function saveItem(row) {
        if (!row) return;
        
        // Validate required fields
        const itemId = row.querySelector('.item-id').value || row.getAttribute('data-item-id');
        const itemName = row.querySelector('.item-name').value || row.getAttribute('data-item-name') || row.querySelector('.item-search').value;
        
        if (!itemId || !itemName) {
            alert('Please select a valid item');
            return;
        }
        
        // Make sure hidden inputs have values
        const itemIdInput = row.querySelector('.item-id');
        const itemNameInput = row.querySelector('.item-name');
        
        if (itemIdInput && !itemIdInput.value && itemId) {
            itemIdInput.value = itemId;
        }
        
        if (itemNameInput && !itemNameInput.value && itemName) {
            itemNameInput.value = itemName;
        }
        
        // For medicine, validate batch
        const itemType = row.querySelector('.item-type').value;
        if (itemType === 'Medicine' || itemType === 'Prescription') {
            const batch = row.querySelector('.batch-select').value;
            if (!batch) {
                alert('Please select a batch for this item');
                return;
            }
        }
        
        // Mark row as saved
        row.classList.add('saved');
        
        // Update UI to show saved state
        const saveButton = row.querySelector('.save-line-item');
        if (saveButton) {
            saveButton.classList.add('text-gray-400');
            saveButton.classList.remove('text-green-500', 'hover:text-green-700');
            saveButton.setAttribute('disabled', 'disabled');
        }
        
        // Recalculate totals
        calculateLineTotal(row);
        calculateTotals();
        
        console.log("Line item saved:", itemName, "ID:", itemId);
    }
    
    function updateLineNumbers() {
        const rows = lineItemsContainer.querySelectorAll('.line-item-row');
        rows.forEach((row, index) => {
            const lineNumberEl = row.querySelector('.line-number');
            if (lineNumberEl) {
                lineNumberEl.textContent = index + 1;
            }
        });
    }
    
    function initializeLineItem(row) {
        // Initialize item type change
        const itemType = row.querySelector('.item-type');
        const medicineFields = row.querySelector('.medicine-fields');
        
        if (itemType && medicineFields) {
            itemType.addEventListener('change', function() {
                // Clear item selection
                const itemIdInput = row.querySelector('.item-id');
                const itemNameInput = row.querySelector('.item-name');
                const itemSearchInput = row.querySelector('.item-search');
                
                if (itemIdInput) itemIdInput.value = '';
                if (itemNameInput) itemNameInput.value = '';
                if (itemSearchInput) itemSearchInput.value = '';
                
                // Show/hide medicine fields based on type
                if (this.value === 'Medicine' || this.value === 'Prescription') {
                    medicineFields.classList.remove('hidden');
                } else {
                    medicineFields.classList.add('hidden');
                }
            });
        }
        
        // Initialize search functionality
        initializeItemSearch(row);
        
        // Set line number
        const lineNumber = row.querySelector('.line-number');
        if (lineNumber) {
            const currentIndex = Array.from(lineItemsContainer.querySelectorAll('.line-item-row')).indexOf(row);
            lineNumber.textContent = currentIndex + 1;
        }
    }
    
    function initializeItemSearch(row) {
        const itemSearchInput = row.querySelector('.item-search');
        const itemSearchResults = row.querySelector('.item-search-results');
        const itemIdInput = row.querySelector('.item-id');
        const itemNameInput = row.querySelector('.item-name');
        const itemType = row.querySelector('.item-type');
        
        if (!itemSearchInput || !itemSearchResults || !itemIdInput || !itemNameInput || !itemType) {
            console.warn("Item search elements missing");
            return;
        }
        
        // Debounce function
        const debounce = (func, delay) => {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), delay);
            };
        };
        
        // Search function
        const performSearch = debounce((query) => {
            if (query.length < 2) {
                itemSearchResults.innerHTML = '';
                itemSearchResults.classList.add('hidden');
                return;
            }
            
            // API request - using web-friendly endpoint
            const url = `/invoice/web_api/item/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(itemType.value)}`;
            console.log("Searching items with URL:", url);
            
            fetch(url, {
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                itemSearchResults.innerHTML = '';
                
                if (data.length === 0) {
                    itemSearchResults.innerHTML = '<div class="p-2 text-gray-500 dark:text-gray-400">No items found</div>';
                    itemSearchResults.classList.remove('hidden');
                    return;
                }
                
                data.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer';
                    
                    // Different display formats based on item type
                    if (item.type === 'Medicine' || item.type === 'Prescription') {
                        div.innerHTML = `
                            <div class="font-semibold">${item.name}</div>
                            <div class="text-xs text-gray-600 dark:text-gray-400">GST: ${item.gst_rate}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
                        `;
                    } else {
                        div.innerHTML = `
                            <div class="font-semibold">${item.name}</div>
                            <div class="text-xs text-gray-600 dark:text-gray-400">Price:  Rs.${item.price ? item.price.toFixed(2) : '0.00'} | GST: ${item.gst_rate}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
                        `;
                    }
                    
                    div.addEventListener('click', () => {
                        // Set selected item values
                        itemIdInput.value = item.id;
                        itemNameInput.value = item.name;
                        itemSearchInput.value = item.name;
                        
                        // Also set data attributes on the row for backup
                        row.setAttribute('data-item-id', item.id);
                        row.setAttribute('data-item-name', item.name);
                        row.setAttribute('data-item-type', item.type);
                        
                        // Set GST info - using property names from existing code
                        row.querySelector('.gst-rate').value = item.gst_rate || 0;
                        row.querySelector('.is-gst-exempt').value = item.is_gst_exempt || false;
                        
                        // Set price for non-medicine items
                        if (item.type !== 'Medicine' && item.type !== 'Prescription') {
                            row.querySelector('.unit-price').value = item.price ? item.price.toFixed(2) : '0.00';
                        }
                        
                        // Hide results
                        itemSearchResults.classList.add('hidden');
                        
                        // Load batches for medicine - matching existing code's approach
                        if (item.type === 'Medicine' || item.type === 'Prescription') {
                            loadMedicineBatches(item.id, row);
                        }
                        
                        // Calculate totals
                        calculateLineTotal(row);
                        calculateTotals();
                        
                        console.log("Item selected:", item.name, "ID:", item.id);
                    });
                    
                    itemSearchResults.appendChild(div);
                });
                
                itemSearchResults.classList.remove('hidden');
            })
            .catch(error => {
                console.error('Error searching items:', error);
                itemSearchResults.innerHTML = '<div class="p-2 text-red-500">Error searching items</div>';
                itemSearchResults.classList.remove('hidden');
            });
        }, 300);
        
        // Attach event listeners
        itemSearchInput.addEventListener('input', function() {
            const query = this.value.trim();
            performSearch(query);
        });
        
        // Hide results when clicking outside
        document.addEventListener('click', function(e) {
            if (!itemSearchInput.contains(e.target) && !itemSearchResults.contains(e.target)) {
                itemSearchResults.classList.add('hidden');
            }
        });
    }
    function loadMedicineBatches(medicineId, row) {
        const batchSelect = row.querySelector('.batch-select');
        const expiryDateInput = row.querySelector('.expiry-date');
        const unitPriceInput = row.querySelector('.unit-price');
        const quantity = row.querySelector('.quantity').value || 1;
        
        if (!batchSelect || !expiryDateInput || !unitPriceInput) {
            console.warn("Batch selection elements missing");
            return;
        }
        
        // Get auth token
        const tokenElement = document.querySelector('meta[name="auth-token"]');
        const token = tokenElement ? tokenElement.getAttribute('content') : null;
        
        // API request for batches - using web-friendly endpoint
        console.log("Loading batches for medicine ID:", medicineId);
        
        fetch(`/invoice/web_api/medicine/${medicineId}/batches?quantity=${quantity}`, {
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Clear existing options
            batchSelect.innerHTML = '<option value="">Select Batch</option>';
            
            const batches = Array.isArray(data) ? data : (data.batches || []);
            
            if (batches.length === 0) {
                batchSelect.innerHTML += '<option value="" disabled>No batches available</option>';
                return;
            }
            
            // Add options for each batch - matching format from existing code
            batches.forEach(batch => {
                const option = document.createElement('option');
                option.value = batch.batch || batch.batch_number;
                option.textContent = `${batch.batch || batch.batch_number} (${batch.quantity_available || batch.available_quantity} units)`;
                option.setAttribute('data-expiry', batch.expiry_date || batch.expiry);
                option.setAttribute('data-price', batch.sale_price || batch.unit_price);
                batchSelect.appendChild(option);
            });
            
            // Select first batch if available - matching behavior in existing code
            if (batchSelect.options.length > 1) {
                batchSelect.selectedIndex = 1;
                const selectedOption = batchSelect.options[1];
                expiryDateInput.value = selectedOption.getAttribute('data-expiry') || '';
                unitPriceInput.value = selectedOption.getAttribute('data-price') || '0.00';
                
                // Calculate totals
                calculateLineTotal(row);
                calculateTotals();
            }
            
            console.log("Batches loaded:", batches.length);
        })
        .catch(error => {
            console.error('Error loading medicine batches:', error);
            batchSelect.innerHTML = '<option value="">Error loading batches</option>';
        });
        
        // Add change event listener for batch selection
        batchSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption) {
                expiryDateInput.value = selectedOption.getAttribute('data-expiry') || '';
                unitPriceInput.value = selectedOption.getAttribute('data-price') || '0.00';
                
                // Calculate totals
                calculateLineTotal(row);
                calculateTotals();
            }
        });
    }
    
    function calculateLineTotal(row) {
        // Using a similar calculation approach as the existing code
        const quantity = parseFloat(row.querySelector('.quantity').value) || 0;
        const unitPrice = parseFloat(row.querySelector('.unit-price').value) || 0;
        const discountPercent = parseFloat(row.querySelector('.discount-percent').value) || 0;
        const gstRate = parseFloat(row.querySelector('.gst-rate').value) || 0;
        const isGstExempt = row.querySelector('.is-gst-exempt').value === 'true';
        const isGstInvoice = document.getElementById('is_gst_invoice').checked;
        const isInterstate = document.getElementById('is_interstate').checked;
        
        // Calculate pre-discount amount
        const preDiscountAmount = quantity * unitPrice;
        
        // Calculate discount
        const discountAmount = (preDiscountAmount * discountPercent) / 100;
        
        // Calculate taxable amount (after discount)
        const taxableAmount = preDiscountAmount - discountAmount;
        
        // Calculate GST
        let cgstAmount = 0;
        let sgstAmount = 0;
        let igstAmount = 0;
        let totalGstAmount = 0;
        
        if (isGstInvoice && !isGstExempt && gstRate > 0) {
            if (isInterstate) {
                // Interstate: only IGST
                igstAmount = (taxableAmount * gstRate) / 100;
                totalGstAmount = igstAmount;
            } else {
                // Intrastate: CGST + SGST
                const halfGstRate = gstRate / 2;
                cgstAmount = (taxableAmount * halfGstRate) / 100;
                sgstAmount = (taxableAmount * halfGstRate) / 100;
                totalGstAmount = cgstAmount + sgstAmount;
            }
        }
        
        // Calculate line total
        const lineTotal = taxableAmount + totalGstAmount;
        
        // Update GST amount display
        const gstAmountEl = row.querySelector('.gst-amount');
        if (gstAmountEl) {
            gstAmountEl.textContent = totalGstAmount.toFixed(2);
        }
        
        // Update line total
        const lineTotalEl = row.querySelector('.line-total');
        if (lineTotalEl) {
            lineTotalEl.textContent = lineTotal.toFixed(2);
        }
        
        return {
            quantity,
            unitPrice,
            discountPercent,
            discountAmount,
            taxableAmount,
            cgstAmount,
            sgstAmount,
            igstAmount,
            totalGstAmount,
            lineTotal
        };
    }
    
    function calculateTotals() {
        const rows = lineItemsContainer.querySelectorAll('.line-item-row');
        const isGstInvoice = document.getElementById('is_gst_invoice').checked;
        
        // Initialize totals
        let subtotal = 0;
        let totalDiscount = 0;
        let totalTaxableValue = 0;
        let totalCgst = 0;
        let totalSgst = 0;
        let totalIgst = 0;
        let grandTotal = 0;
        
        // Sum values from all rows - similar to existing code
        rows.forEach(row => {
            const result = calculateLineTotal(row);
            
            // Add to totals
            subtotal += result.quantity * result.unitPrice;
            totalDiscount += result.discountAmount;
            totalTaxableValue += result.taxableAmount;
            totalCgst += result.cgstAmount;
            totalSgst += result.sgstAmount;
            totalIgst += result.igstAmount;
            grandTotal += result.lineTotal;
        });
        
        // Update totals in the UI
        const subtotalEl = document.getElementById('subtotal');
        const totalDiscountEl = document.getElementById('total-discount');
        const totalCgstEl = document.getElementById('total-cgst');
        const totalSgstEl = document.getElementById('total-sgst');
        const totalIgstEl = document.getElementById('total-igst');
        const grandTotalEl = document.getElementById('grand-total');
        
        if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
        if (totalDiscountEl) totalDiscountEl.textContent = totalDiscount.toFixed(2);
        if (totalCgstEl) totalCgstEl.textContent = totalCgst.toFixed(2);
        if (totalSgstEl) totalSgstEl.textContent = totalSgst.toFixed(2);
        if (totalIgstEl) totalIgstEl.textContent = totalIgst.toFixed(2);
        if (grandTotalEl) grandTotalEl.textContent = grandTotal.toFixed(2);
        
        // Update hidden form fields (if present) - similar to existing code
        const totalAmountInput = document.getElementById('total-amount-input');
        const totalDiscountInput = document.getElementById('total-discount-input');
        const totalTaxableValueInput = document.getElementById('total-taxable-value-input');
        const totalCgstAmountInput = document.getElementById('total-cgst-amount-input');
        const totalSgstAmountInput = document.getElementById('total-sgst-amount-input');
        const totalIgstAmountInput = document.getElementById('total-igst-amount-input');
        const grandTotalInput = document.getElementById('grand-total-input');
        
        if (totalAmountInput) totalAmountInput.value = subtotal.toFixed(2);
        if (totalDiscountInput) totalDiscountInput.value = totalDiscount.toFixed(2);
        if (totalTaxableValueInput) totalTaxableValueInput.value = totalTaxableValue.toFixed(2);
        if (totalCgstAmountInput) totalCgstAmountInput.value = totalCgst.toFixed(2);
        if (totalSgstAmountInput) totalSgstAmountInput.value = totalSgst.toFixed(2);
        if (totalIgstAmountInput) totalIgstAmountInput.value = totalIgst.toFixed(2);
        if (grandTotalInput) grandTotalInput.value = grandTotal.toFixed(2);
    }
}

function initializePatientSearch() {
    // Using the same endpoint and logic as the existing code
    const patientSearch = document.getElementById('patient-search');
    const patientResults = document.getElementById('patient-search-results');
    const patientIdInput = document.getElementById('patient_id');
    const patientNameInput = document.getElementById('patient_name');
    const patientInfo = document.getElementById('selected-patient-info');
    const patientNameDisplay = document.getElementById('patient-name-display');
    const patientMRNDisplay = document.getElementById('patient-mrn-display');
    const patientContactDisplay = document.getElementById('patient-contact-display');
    
    if (!patientSearch || !patientResults) {
        console.warn("Patient search elements missing");
        return;
    }
    
    // Debounce function
    const debounce = (func, delay) => {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    };
    
    // Search patients - using original endpoint
    const searchPatients = debounce(function(query) {
        if (query.length < 1) {
            patientResults.innerHTML = '';
            patientResults.classList.add('hidden');
            return;
        }
        
        console.log("Searching patients with query:", query);
        
        // AJAX request to search patients
        fetch(`/invoice/web_api/patient/search?q=${encodeURIComponent(query)}`, {
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            patientResults.innerHTML = '';
            
            if (data.length === 0) {
                patientResults.innerHTML = '<div class="p-2 text-gray-500 dark:text-gray-400">No patients found</div>';
                patientResults.classList.remove('hidden');
                return;
            }
            
            data.forEach(patient => {
                const div = document.createElement('div');
                div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer';
                
                // Use the same format as existing code
                div.innerHTML = `
                    <div class="font-semibold">${patient.name}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">MRN: ${patient.mrn}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">${patient.contact || ''}</div>
                `;
                
                div.addEventListener('click', function() {
                    // Set hidden input values
                    if (patientIdInput) {
                        patientIdInput.value = patient.id;
                        console.log("Set patient ID to:", patient.id);
                        
                        // Also set a data attribute on the form for extra safety
                        const invoiceForm = document.getElementById('invoice-form');
                        if (invoiceForm) {
                            invoiceForm.setAttribute('data-patient-id', patient.id);
                            invoiceForm.setAttribute('data-patient-name', patient.name);
                        }
                    }
                    
                    if (patientNameInput) {
                        patientNameInput.value = patient.name;
                    }
                    
                    // Update search input
                    patientSearch.value = `${patient.name} - ${patient.mrn}`;
                    
                    // Display selected patient info
                    if (patientNameDisplay) patientNameDisplay.textContent = patient.name;
                    if (patientMRNDisplay) patientMRNDisplay.textContent = `MRN: ${patient.mrn}`;
                    if (patientContactDisplay) patientContactDisplay.textContent = patient.contact || '';
                    if (patientInfo) patientInfo.classList.remove('hidden');
                    
                    // Hide results
                    patientResults.classList.add('hidden');
                    
                    console.log("Patient selected:", patient.name, "ID:", patient.id);
                });
                
                patientResults.appendChild(div);
            });
            
            patientResults.classList.remove('hidden');
        })
        .catch(error => {
            console.error('Error searching patients:', error);
            patientResults.innerHTML = '<div class="p-2 text-red-500">Error searching patients</div>';
            patientResults.classList.remove('hidden');
        });
    }, 300);
    
    // Add event listener for patient search
    patientSearch.addEventListener('input', function() {
        const query = this.value.trim();
        searchPatients(query);
    });
    
    // Hide results when clicking elsewhere
    document.addEventListener('click', function(e) {
        if (!patientSearch.contains(e.target) && !patientResults.contains(e.target)) {
            patientResults.classList.add('hidden');
        }
    });
}

function initializeGSTToggle() {
    // Match the existing functionality for GST toggling
    const isGstInvoice = document.getElementById('is_gst_invoice');
    const isInterstate = document.getElementById('is_interstate');
    const gstElements = document.querySelectorAll('.gst-element');
    const gstColumn = document.querySelectorAll('.gst-column');
    
    if (!isGstInvoice) {
        console.warn("GST invoice checkbox not found");
        return;
    }
    
    // Function to toggle GST elements visibility
    function toggleGstElements() {
        const isGstChecked = isGstInvoice.checked;
        
        // Show/hide GST-related elements
        gstElements.forEach(el => {
            if (isGstChecked) {
                el.style.display = '';
            } else {
                el.style.display = 'none';
            }
        });
        
        // Show/hide GST column in table
        gstColumn.forEach(el => {
            if (isGstChecked) {
                el.style.display = '';
            } else {
                el.style.display = 'none';
            }
        });
        
        // Recalculate totals
        if (window.invoiceComponentFunctions) {
            window.invoiceComponentFunctions.calculateTotals();
        }
        
        console.log("GST elements toggled:", isGstChecked);
    }
    
    // Initial toggle
    toggleGstElements();
    
    // Handle GST toggle
    isGstInvoice.addEventListener('change', toggleGstElements);
    
    // Handle interstate toggle
    if (isInterstate) {
        isInterstate.addEventListener('change', function() {
            // Recalculate totals when interstate status changes
            if (window.invoiceComponentFunctions) {
                window.invoiceComponentFunctions.calculateTotals();
            }
            console.log("Interstate toggled:", isInterstate.checked);
        });
    }
}
function validateForm() {
    // Get patient ID in multiple ways to ensure we find it
    let patientId = document.getElementById('patient_id')?.value;
    const invoiceForm = document.getElementById('invoice-form');
    const patientIdFromForm = invoiceForm?.getAttribute('data-patient-id');
    
    // Try to get from form attribute if the input is empty
    if (!patientId && patientIdFromForm) {
        patientId = patientIdFromForm;
        console.log("Using patient ID from form attribute:", patientId);
        
        // Update the hidden input if it exists but is empty
        const patientIdInput = document.getElementById('patient_id');
        if (patientIdInput && !patientIdInput.value) {
            patientIdInput.value = patientId;
        }
    }
    
    // Debug output current state
    console.log("Validating form. Patient ID:", patientId);
    console.log("Patient info element visible:", !document.getElementById('selected-patient-info').classList.contains('hidden'));
    console.log("Patient search value:", document.getElementById('patient-search').value);
    
    // Check if patient was selected (either by ID or by the visible patient info)
    const patientSelected = patientId || 
                          (!document.getElementById('selected-patient-info').classList.contains('hidden') &&
                           document.getElementById('patient-search').value);
    
    if (!patientSelected) {
        alert('Please select a patient.');
        document.getElementById('patient-search').focus();
        return false;
    }
    
    // Check if there are line items
    const lineItems = document.querySelectorAll('.line-item-row');
    if (lineItems.length === 0) {
        alert('Please add at least one item.');
        if (document.getElementById('add-line-item')) {
            document.getElementById('add-line-item').focus();
        }
        return false;
    }
    
    // Validate each line item
    let isValid = true;
    lineItems.forEach((row, index) => {
        // Get item ID in multiple ways
        let itemId = row.querySelector('.item-id')?.value;
        const itemIdFromAttr = row.getAttribute('data-item-id');
        
        // If input is empty but we have a backup ID, use it
        if (!itemId && itemIdFromAttr) {
            itemId = itemIdFromAttr;
            const itemIdInput = row.querySelector('.item-id');
            if (itemIdInput) {
                itemIdInput.value = itemId;
                console.log(`Restored item ID for line ${index + 1} from data attribute:`, itemId);
            }
        }
        
        if (!itemId) {
            alert(`Please select a valid item for line ${index + 1}.`);
            isValid = false;
            return;
        }
        
        // Get item name in multiple ways
        let itemName = row.querySelector('.item-name')?.value;
        const itemNameFromAttr = row.getAttribute('data-item-name');
        const itemSearchValue = row.querySelector('.item-search')?.value;
        
        // If input is empty but we have a backup name, use it
        if (!itemName && (itemNameFromAttr || itemSearchValue)) {
            itemName = itemNameFromAttr || itemSearchValue;
            const itemNameInput = row.querySelector('.item-name');
            if (itemNameInput) {
                itemNameInput.value = itemName;
                console.log(`Restored item name for line ${index + 1}:`, itemName);
            }
        }
        
        // For medicines, validate batch
        const itemType = row.querySelector('.item-type')?.value || row.getAttribute('data-item-type');
        if ((itemType === 'Medicine' || itemType === 'Prescription') && !row.classList.contains('saved')) {
            const batch = row.querySelector('.batch-select')?.value;
            if (!batch) {
                alert(`Please select a batch for item in line ${index + 1}.`);
                isValid = false;
                return;
            }
        }
        
        // Log validation for this line item
        console.log(`Validated line item ${index + 1}: ID=${itemId}, Name=${itemName}, Type=${itemType}`);
    });
    
    return isValid;
}

function prepareFormForSubmission() {
    // Create a backup copy of the patient ID in a hidden field
    const patientId = document.getElementById('patient_id')?.value;
    const invoiceForm = document.getElementById('invoice-form');
    
    if (patientId && invoiceForm) {
        // Create or update a hidden backup field
        let backupField = document.getElementById('patient_id_backup');
        if (!backupField) {
            backupField = document.createElement('input');
            backupField.type = 'hidden';
            backupField.id = 'patient_id_backup';
            backupField.name = 'patient_id_backup';
            invoiceForm.appendChild(backupField);
        }
        backupField.value = patientId;
        
        console.log("Backed up patient ID:", patientId);
    }
    
    // Double-check that patient_id is being submitted
    const formData = new FormData(invoiceForm);
    if (!formData.get('patient_id') && formData.get('patient_id_backup')) {
        // If the original is missing but we have a backup, use it
        const patientIdInput = document.getElementById('patient_id');
        if (patientIdInput) {
            patientIdInput.value = formData.get('patient_id_backup');
        }
    }
    
    // Reindex line items before submission (in case items were removed)
    const lineItems = document.querySelectorAll('.line-item-row');
    lineItems.forEach((row, index) => {
        // Check if item ID and name are set
        const itemIdInput = row.querySelector('.item-id');
        const itemNameInput = row.querySelector('.item-name');
        const itemIdFromAttr = row.getAttribute('data-item-id');
        const itemNameFromAttr = row.getAttribute('data-item-name');
        
        // Restore from attributes if needed
        if (itemIdInput && !itemIdInput.value && itemIdFromAttr) {
            itemIdInput.value = itemIdFromAttr;
        }
        
        if (itemNameInput && !itemNameInput.value && itemNameFromAttr) {
            itemNameInput.value = itemNameFromAttr;
        }
        
        // Now reindex all the input names
        row.querySelectorAll('[name^="line_items-"]').forEach(input => {
            const newName = input.name.replace(/line_items-\d+-/, `line_items-${index}-`);
            console.log(`Reindexing ${input.name} to ${newName}`);
            input.name = newName;
        });
    });
    
    // Create a hidden field for the total line items count if needed
    if (!document.getElementById('line_items_count')) {
        const countInput = document.createElement('input');
        countInput.type = 'hidden';
        countInput.id = 'line_items_count';
        countInput.name = 'line_items_count';
        countInput.value = lineItems.length;
        invoiceForm.appendChild(countInput);
    } else {
        document.getElementById('line_items_count').value = lineItems.length;
    }
    
    console.log("Form prepared for submission with line items:", lineItems.length);
    
    // Debug the final form data
    const finalFormData = new FormData(invoiceForm);
    console.log("Final form data for submission:");
    for (let [key, value] of finalFormData.entries()) {
        if (key.includes('item_id') || key.includes('item_name') || key === 'patient_id') {
            console.log(`${key}: ${value}`);
        }
    }
}

// function initializeFormSubmission() {
//     // Match the existing form validation logic
//     const invoiceForm = document.getElementById('invoice-form');
//     const createButton = document.querySelector('button[type="submit"]');
    
//     if (!invoiceForm) {
//         console.warn("Invoice form not found");
//         return;
//     }
    
//     console.log("Initializing form submission handler");
    
//     // Fix for the form submission issue
//     // Make sure the Create Invoice button works properly
//     if (createButton) {
//         createButton.addEventListener('click', function(e) {
//             e.preventDefault(); // Prevent default to handle our custom logic
//             console.log("Create invoice button clicked directly");
            
//             // Save any unsaved line items first
//             document.querySelectorAll('.line-item-row:not(.saved)').forEach(row => {
//                 // Auto-save unsaved rows
//                 if (row.querySelector('.item-id').value || row.getAttribute('data-item-id')) {
//                     saveItem(row);
//                 }
//             });
            
//             // Check if there are any validation issues
//             if (!validateForm()) {
//                 return;
//             }
            
//             // If we get here, form is valid - ensure it submits
//             try {
//                 // Update form before submission
//                 prepareFormForSubmission();
                
//                 // For debugging: print out key form fields
//                 const formData = new FormData(invoiceForm);
//                 const patientId = formData.get('patient_id');
//                 console.log(`Submitting form with Patient ID: ${patientId}`);
                
//                 // Check if we have at least one line item with valid data
//                 let hasValidLineItem = false;
//                 for (let [key, value] of formData.entries()) {
//                     if (key.includes('item_id') && value) {
//                         hasValidLineItem = true;
//                         console.log(`Found valid line item: ${key}=${value}`);
//                         break;
//                     }
//                 }
                
//                 if (!hasValidLineItem) {
//                     alert("No valid line items found. Please add at least one item.");
//                     return;
//                 }
                
//                 // Submit the form
//                 console.log("Form is valid, submitting...");
//                 invoiceForm.submit();
//             } catch (err) {
//                 console.error("Error submitting form:", err);
//                 alert("Error submitting form: " + err.message);
//             }
//         });
//     }
    
//     // Also handle the form submit event as a backup
//     invoiceForm.addEventListener('submit', function(e) {
//         console.log("Form submit event triggered");
        
//         // Double-check that the patient ID is still in the form
//         const patientId = document.getElementById('patient_id')?.value;
//         const patientIdFromForm = invoiceForm.getAttribute('data-patient-id');
        
//         if (!patientId && patientIdFromForm) {
//             // If missing, try to restore it
//             const patientIdInput = document.getElementById('patient_id');
//             if (patientIdInput) {
//                 patientIdInput.value = patientIdFromForm;
//                 console.log("Restored patient ID from form attribute:", patientIdFromForm);
//             }
//         }
        
//         // No need to validate again as the button click already did that
//         // Just make sure form is prepared properly
//         prepareFormForSubmission();
//         console.log("Form submitted via standard submit event");
//     });
// }

// Step 1: Simple Form Submit Solution
// Replace only the initializeFormSubmission function with this version

// Complete replacement of the initializeFormSubmission function
// This is the absolute most basic implementation that should work

// Enhanced debug version with special flags for testing

// CSRF-aware form submission handler
// This version specifically addresses CSRF token issues

// Enhanced form submission handler that captures and logs all form data
// Use this to debug the data structure being sent to the server

function initializeFormSubmission() {
    console.log("Initializing simplified form submission");
    
    const form = document.getElementById('invoice-form');
    if (!form) {
        console.error("Invoice form not found");
        return;
    }
    
    // Log form properties
    console.log("Form action:", form.action);
    console.log("Form method:", form.method);
    
    // Add native form submission logging
    form.addEventListener('submit', function(event) {
        console.log("Form native submit event triggered");
        
        // Don't prevent default - we want to see if the natural submission works
        console.log("Form is submitting naturally");
        
        // Optional: Display submission notification to user
        setTimeout(() => {
            alert("Form is being submitted. Check console for details.");
        }, 100);
    });
    
    console.log("Form submission handler initialized");
}

// Add this TEMPORARY function for testing
function temporaryTestSubmission() {
    console.log("Testing simplified form submission");
    
    const form = document.getElementById('invoice-form');
    
    // Create minimal test form data
    const formData = new FormData();
    formData.append('csrf_token', document.querySelector('input[name="csrf_token"]').value);
    formData.append('patient_id', document.getElementById('patient_id').value || 'test-patient-id');
    formData.append('invoice_date', document.querySelector('input[name="invoice_date"]').value);
    
    // Add branch_id if it exists
    const branchSelect = document.querySelector('select[name="branch_id"]');
    if (branchSelect) {
        formData.append('branch_id', branchSelect.value);
    }
    
    // Add at least one simplified line item
    formData.append('line_items-0-item_type', 'Package');
    formData.append('line_items-0-item_id', document.querySelector('.item-id')?.value || '');
    formData.append('line_items-0-item_name', document.querySelector('.item-name')?.value || '');
    formData.append('line_items-0-quantity', '1');
    formData.append('line_items-0-unit_price', '100.00');
    formData.append('line_items-0-discount_percent', '0');
    
    // Log what we're submitting
    console.log("Form data being submitted:");
    for (let [key, value] of formData.entries()) {
        console.log(`${key}: ${value}`);
    }
    
    // Submit using fetch API
    fetch(form.action || window.location.pathname, {
        method: 'POST',
        body: formData,
        headers: {
            'Accept': 'text/html'
        }
    })
    .then(response => {
        console.log("Response status:", response.status);
        return response.text();
    })
    .then(html => {
        console.log("Response received");
        // Don't replace page content - just log success
    })
    .catch(error => {
        console.error("Form submission error:", error);
    });
    
    return false; // Prevent normal form submission
}

// Add a test button
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('invoice-form');
    if (form) {
        const testButton = document.createElement('button');
        testButton.type = 'button';
        testButton.textContent = 'Test Simple Submission';
        testButton.className = 'bg-yellow-500 hover:bg-yellow-700 text-white font-bold py-2 px-4 rounded mt-4';
        testButton.addEventListener('click', temporaryTestSubmission);
        
        // Add it to the form or a specific container
        const submitContainer = form.querySelector('.flex.justify-end');
        if (submitContainer) {
            submitContainer.appendChild(testButton);
        } else {
            form.appendChild(testButton);
        }
        
        console.log("Test button added to form");
    } else {
        console.error("Form not found, couldn't add test button");
    }
});
//     // Also add a direct event listener to the form
//     if (form) {
//         form.addEventListener('submit', function(e) {
//             console.log("Form submit event triggered");
//         });
//     }
// }

// Add at the end of your invoice.js file
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOMContentLoaded fired");
    const invoiceForm = document.getElementById('invoice-form');
    const createButton = document.querySelector('button[type="submit"]');
    console.log("Form found:", !!invoiceForm);
    console.log("Button found:", !!createButton);
    
    // Test direct event binding
    if (createButton) {
      createButton.addEventListener('click', function(e) {
        console.log("Direct button click event fired");
      });
    }
  });