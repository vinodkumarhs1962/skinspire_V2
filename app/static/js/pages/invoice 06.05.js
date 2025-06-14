// app/static/js/pages/invoice.js

// Add this as the first line in your invoice.js file
console.log("Invoice.js loaded at " + new Date().toISOString());
// console.log("Loading invoice.js with emergency line item fix");
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
    
    // Check for browser autofill in patient field
    handlePatientAutofill();
    
    // Log page initialization to help debugging
    console.log("Invoice page initialized");
});

function handlePatientAutofill() {
    const patientSearch = document.getElementById('patient-search');
    const invoiceForm = document.getElementById('invoice-form');
    if (!patientSearch || !invoiceForm) return;
    
    // Check for browser autofill when page loads
    setTimeout(function() {
        if (patientSearch.value && patientSearch.value.trim() !== '') {
            console.log("Detected possible browser autofill:", patientSearch.value);
            // Try to find this patient
            fetch(`/invoice/web_api/patient/search?q=${encodeURIComponent(patientSearch.value)}`, {
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    // Select the first matching patient
                    const patient = data[0];
                    
                    // Ensure patient_id field exists
                    let patientIdInput = document.getElementById('patient_id');
                    if (!patientIdInput) {
                        patientIdInput = document.createElement('input');
                        patientIdInput.type = 'hidden';
                        patientIdInput.id = 'patient_id';
                        patientIdInput.name = 'patient_id';
                        invoiceForm.appendChild(patientIdInput);
                        console.log("Created missing patient_id field for autofill");
                    }
                    
                    const patientNameInput = document.getElementById('patient_name');
                    const patientInfo = document.getElementById('selected-patient-info');
                    const patientNameDisplay = document.getElementById('patient-name-display');
                    const patientMRNDisplay = document.getElementById('patient-mrn-display');
                    const patientContactDisplay = document.getElementById('patient-contact-display');
                    
                    // Set both the input field and form attribute
                    patientIdInput.value = patient.id;
                    invoiceForm.setAttribute('data-patient-id', patient.id);
                    console.log("Autofill: Set patient ID to:", patient.id);
                    
                    if (patientNameInput) patientNameInput.value = patient.name;
                    
                    // Update the display
                    if (patientNameDisplay) patientNameDisplay.textContent = patient.name;
                    if (patientMRNDisplay) patientMRNDisplay.textContent = `MRN: ${patient.mrn}`;
                    if (patientContactDisplay) patientContactDisplay.textContent = patient.contact || '';
                    if (patientInfo) patientInfo.classList.remove('hidden');
                    
                    console.log("Auto-selected patient from browser autofill:", patient.name);
                }
            })
            .catch(error => console.error("Error handling patient autofill:", error));
        }
    }, 500); // Small delay to allow browser autofill to complete
}

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
    
    // Hide branch selection if we can get it from user
    const branchContainer = document.querySelector('select[name="branch_id"]')?.closest('.mb-4');
    if (branchContainer) {
        // We'll keep the branch selection visible for now but make it less prominent
        branchContainer.style.opacity = '0.7';
    }
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
        
        itemType.addEventListener('change', function() {
            // Get necessary elements
            const itemIdInput = row.querySelector('.item-id');
            const itemNameInput = row.querySelector('.item-name');
            const itemSearchInput = row.querySelector('.item-search');
            const itemSearchResults = row.querySelector('.item-search-results');
            
            // Clear item selection when type changes
            if (itemIdInput) itemIdInput.value = '';
            if (itemNameInput) itemNameInput.value = '';
            if (itemSearchInput) itemSearchInput.value = '';
            
            // Clear search results
            if (itemSearchResults) {
                itemSearchResults.innerHTML = '';
                itemSearchResults.classList.add('hidden');
            }
            
            // Clear any data attributes on the row
            row.removeAttribute('data-item-id');
            row.removeAttribute('data-item-name');
            row.removeAttribute('data-item-type');
            
            // Show/hide medicine fields based on type
            if (this.value === 'Medicine' || this.value === 'Prescription') {
                medicineFields.classList.remove('hidden');
            } else {
                medicineFields.classList.add('hidden');
            }
            
            // Trigger a new search with empty query to show all items of the new type
            // First check if we have access to the performSearch function
            if (typeof window.currentPerformSearch === 'function') {
                window.currentPerformSearch("");
            } else {
                console.log("Cannot perform automatic search - function not available");
                
                // Alternative: Simulate a focus event on the search input
                if (itemSearchInput) {
                    setTimeout(() => {
                        const focusEvent = new Event('focus');
                        itemSearchInput.dispatchEvent(focusEvent);
                    }, 100);
                }
            }
        });
        
        // Initialize search functionality
        initializeItemSearch(row);
        
        // Set line number
        const lineNumber = row.querySelector('.line-number');
        if (lineNumber) {
            const currentIndex = Array.from(lineItemsContainer.querySelectorAll('.line-item-row')).indexOf(row);
            lineNumber.textContent = currentIndex + 1;
        }
        
        // Make quantity and discount fields use whole numbers
        const quantityInput = row.querySelector('.quantity');
        const discountInput = row.querySelector('.discount-percent');
        
        if (quantityInput) {
            quantityInput.setAttribute('step', '1');
            quantityInput.addEventListener('change', function() {
                // Round to whole number
                this.value = Math.round(parseFloat(this.value) || 1);
                if (this.value < 1) this.value = 1;
                
                calculateLineTotal(row);
                calculateTotals();
            });
        }
        
        if (discountInput) {
            discountInput.setAttribute('step', '1');
            discountInput.addEventListener('change', function() {
                // Round to whole number
                this.value = Math.round(parseFloat(this.value) || 0);
                if (this.value < 0) this.value = 0;
                if (this.value > 100) this.value = 100;
                
                calculateLineTotal(row);
                calculateTotals();
            });
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
            const searchQuery = query || "";
            
            // API request
            const url = `/invoice/web_api/item/search?q=${encodeURIComponent(searchQuery)}&type=${encodeURIComponent(itemType.value)}`;
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
                    
                    // Fix the click handler to ensure proper item selection
                    div.addEventListener('click', () => {
                        console.log("Item clicked:", item.name);
                        
                        // Force clear any existing batch and expiry information first
                        const batchSelect = row.querySelector('.batch-select');
                        const expiryDateInput = row.querySelector('.expiry-date');
                        
                        if (batchSelect) {
                            batchSelect.innerHTML = '<option value="">Select Batch</option>';
                        }
                        
                        if (expiryDateInput) {
                            expiryDateInput.value = '';
                        }
                        
                        // Set selected item values in both hidden fields and visible search field
                        if (itemIdInput) {
                            itemIdInput.value = item.id;
                            console.log("Set item ID to:", item.id);
                        }
                        
                        if (itemNameInput) {
                            itemNameInput.value = item.name;
                            console.log("Set item name to:", item.name);
                        }
                        
                        if (itemSearchInput) {
                            itemSearchInput.value = item.name;
                            console.log("Set visible search field to:", item.name);
                        }
                        
                        // Also set data attributes on the row for backup
                        row.setAttribute('data-item-id', item.id);
                        row.setAttribute('data-item-name', item.name);
                        row.setAttribute('data-item-type', item.type);
                        
                        // Set GST info
                        const gstRateField = row.querySelector('.gst-rate');
                        const isGstExemptField = row.querySelector('.is-gst-exempt');
                        
                        if (gstRateField) {
                            gstRateField.value = item.gst_rate || 0;
                        }
                        
                        if (isGstExemptField) {
                            isGstExemptField.value = item.is_gst_exempt || false;
                        }
                        
                        // Set price for non-medicine items
                        if (item.type !== 'Medicine' && item.type !== 'Prescription') {
                            const unitPriceField = row.querySelector('.unit-price');
                            if (unitPriceField) {
                                unitPriceField.value = item.price ? item.price.toFixed(2) : '0.00';
                            }
                        }
                        
                        // Hide results
                        itemSearchResults.classList.add('hidden');
                        
                        // Load batches for medicine
                        if (item.type === 'Medicine' || item.type === 'Prescription') {
                            loadMedicineBatches(item.id, row);
                        }
                        
                        // Calculate totals
                        calculateLineTotal(row);
                        calculateTotals();
                        
                        console.log("Item selection complete for:", item.name);
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
        
        // Add focus event to show full list when field receives focus (this is new)
        itemSearchInput.addEventListener('focus', function() {
            // Show the item list only if it's not already populated
            if (!itemSearchResults.querySelector('div')) {
                performSearch("");
            }
            itemSearchResults.classList.remove('hidden');
        });
        
        // Hide results when clicking outside
        document.addEventListener('click', function(e) {
            if (!itemSearchInput.contains(e.target) && !itemSearchResults.contains(e.target)) {
                itemSearchResults.classList.add('hidden');
            }
        });
    }

    // function initializeItemSearch(row) {
    //     const itemSearchInput = row.querySelector('.item-search');
    //     const itemSearchResults = row.querySelector('.item-search-results');
    //     const itemIdInput = row.querySelector('.item-id');
    //     const itemNameInput = row.querySelector('.item-name');
    //     const itemType = row.querySelector('.item-type');
        
    //     if (!itemSearchInput || !itemSearchResults || !itemIdInput || !itemNameInput || !itemType) {
    //         console.warn("Item search elements missing");
    //         return;
    //     }
        
    //     // Debounce function
    //     const debounce = (func, delay) => {
    //         let timeout;
    //         return function(...args) {
    //             clearTimeout(timeout);
    //             timeout = setTimeout(() => func.apply(this, args), delay);
    //         };
    //     };
        
    //     // Search function
    //     const performSearch = debounce((query) => {
    //         if (query.length < 2) {
    //             itemSearchResults.innerHTML = '';
    //             itemSearchResults.classList.add('hidden');
    //             return;
    //         }
            
    //         // API request - using web-friendly endpoint
    //         const url = `/invoice/web_api/item/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(itemType.value)}`;
    //         console.log("Searching items with URL:", url);
            
    //         fetch(url, {
    //             headers: {
    //                 'Content-Type': 'application/json'
    //             }
    //         })
    //         .then(response => response.json())
    //         .then(data => {
    //             itemSearchResults.innerHTML = '';
                
    //             if (data.length === 0) {
    //                 itemSearchResults.innerHTML = '<div class="p-2 text-gray-500 dark:text-gray-400">No items found</div>';
    //                 itemSearchResults.classList.remove('hidden');
    //                 return;
    //             }
                
    //             data.forEach(item => {
    //                 const div = document.createElement('div');
    //                 div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer';
                    
    //                 // Different display formats based on item type
    //                 if (item.type === 'Medicine' || item.type === 'Prescription') {
    //                     div.innerHTML = `
    //                         <div class="font-semibold">${item.name}</div>
    //                         <div class="text-xs text-gray-600 dark:text-gray-400">GST: ${item.gst_rate}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
    //                     `;
    //                 } else {
    //                     div.innerHTML = `
    //                         <div class="font-semibold">${item.name}</div>
    //                         <div class="text-xs text-gray-600 dark:text-gray-400">Price:  Rs.${item.price ? item.price.toFixed(2) : '0.00'} | GST: ${item.gst_rate}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
    //                     `;
    //                 }
                    
    //                 div.addEventListener('click', () => {
    //                     // Clear any existing batch and expiry information first
    //                     const batchSelect = row.querySelector('.batch-select');
    //                     const expiryDateInput = row.querySelector('.expiry-date');
                        
    //                     if (batchSelect) {
    //                         batchSelect.innerHTML = '<option value="">Select Batch</option>';
    //                     }
                        
    //                     if (expiryDateInput) {
    //                         expiryDateInput.value = '';
    //                     }
                        
    //                     // Set selected item values
    //                     itemIdInput.value = item.id;
    //                     itemNameInput.value = item.name;
    //                     itemSearchInput.value = item.name;
                        
    //                     // Also set data attributes on the row for backup
    //                     row.setAttribute('data-item-id', item.id);
    //                     row.setAttribute('data-item-name', item.name);
    //                     row.setAttribute('data-item-type', item.type);
                        
    //                     // Set GST info - using property names from existing code
    //                     row.querySelector('.gst-rate').value = item.gst_rate || 0;
    //                     row.querySelector('.is-gst-exempt').value = item.is_gst_exempt || false;
                        
    //                     // Set price for non-medicine items
    //                     if (item.type !== 'Medicine' && item.type !== 'Prescription') {
    //                         row.querySelector('.unit-price').value = item.price ? item.price.toFixed(2) : '0.00';
    //                     }
                        
    //                     // Hide results
    //                     itemSearchResults.classList.add('hidden');
                        
    //                     // Load batches for medicine - matching existing code's approach
    //                     if (item.type === 'Medicine' || item.type === 'Prescription') {
    //                         loadMedicineBatches(item.id, row);
    //                     }
                        
    //                     // Calculate totals
    //                     calculateLineTotal(row);
    //                     calculateTotals();
                        
    //                     console.log("Item selected:", item.name, "ID:", item.id);
    //                 });
                    
    //                 itemSearchResults.appendChild(div);
    //             });
                
    //             itemSearchResults.classList.remove('hidden');
    //         })
    //         .catch(error => {
    //             console.error('Error searching items:', error);
    //             itemSearchResults.innerHTML = '<div class="p-2 text-red-500">Error searching items</div>';
    //             itemSearchResults.classList.remove('hidden');
    //         });
    //     }, 300);
        
    //     // Attach event listeners
    //     itemSearchInput.addEventListener('input', function() {
    //         const query = this.value.trim();
    //         performSearch(query);
    //     });
        
    //     // Hide results when clicking outside
    //     document.addEventListener('click', function(e) {
    //         if (!itemSearchInput.contains(e.target) && !itemSearchResults.contains(e.target)) {
    //             itemSearchResults.classList.add('hidden');
    //         }
    //     });
    // }
    
    function loadMedicineBatches(medicineId, row) {
        const batchSelect = row.querySelector('.batch-select');
        const expiryDateInput = row.querySelector('.expiry-date');
        const unitPriceInput = row.querySelector('.unit-price');
        const quantity = row.querySelector('.quantity').value || 1;
        
        if (!batchSelect || !expiryDateInput || !unitPriceInput) {
            console.warn("Batch selection elements missing");
            return;
        }
        
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
            // Consolidate batches with the same batch number
            const consolidatedBatches = {};
            batches.forEach(batch => {
                const batchKey = batch.batch || batch.batch_number;
                if (!consolidatedBatches[batchKey]) {
                    consolidatedBatches[batchKey] = {
                        batch: batchKey,
                        expiry_date: batch.expiry_date || batch.expiry,
                        available_quantity: parseFloat(batch.quantity_available || batch.available_quantity) || 0,
                        unit_price: parseFloat(batch.sale_price || batch.unit_price) || 0
                    };
                } else {
                    // Add quantities for the same batch
                    consolidatedBatches[batchKey].available_quantity += 
                        parseFloat(batch.quantity_available || batch.available_quantity) || 0;
                }
            });

            // Add options for each consolidated batch
            Object.values(consolidatedBatches).forEach(batch => {
                const option = document.createElement('option');
                option.value = batch.batch;
                option.textContent = `${batch.batch} (${batch.available_quantity.toFixed(2)} units)`;
                option.setAttribute('data-expiry', batch.expiry_date);
                option.setAttribute('data-price', batch.unit_price);
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
    
    // Preserved intact for GST calculation logic
    function calculateLineTotal(row) {
        // Get values from the row
        const quantity = parseFloat(row.querySelector('.quantity').value) || 0;
        const unitPrice = parseFloat(row.querySelector('.unit-price').value) || 0;
        const discountPercent = parseFloat(row.querySelector('.discount-percent').value) || 0;
        const gstRate = parseFloat(row.querySelector('.gst-rate').value) || 0;
        const isGstExempt = row.querySelector('.is-gst-exempt').value === 'true';
        const isGstInvoice = document.getElementById('is_gst_invoice').checked;
        const isInterstate = document.getElementById('is_interstate').checked;
        const itemType = row.querySelector('.item-type').value;
        const itemName = row.querySelector('.item-name').value || row.getAttribute('data-item-name') || '';
        const includedInConsultation = row.querySelector('.included-in-consultation')?.checked || false;
        
        // Check if this is Doctor's Examination or a prescription included in consultation
        const isDoctorsExamination = itemName === "Doctor's Examination and Treatment" || 
                                (itemType === 'Prescription' && includedInConsultation) ||
                                (itemType === 'Medicine' && includedInConsultation);
        
        // Calculate pre-discount amount
        const preDiscountAmount = quantity * unitPrice;
        
        // Initialize variables
        let discountAmount = 0;
        let taxableAmount = 0;
        let cgstAmount = 0;
        let sgstAmount = 0;
        let igstAmount = 0;
        let totalGstAmount = 0;
        let lineTotal = 0;
        let baseBeforeGst = 0;
        
        if (isDoctorsExamination) {
            // For Doctor's Examination, no GST regardless of settings
            discountAmount = 0; // No discount for Doctor's Examination
            taxableAmount = preDiscountAmount;
            lineTotal = taxableAmount;
        } 
        else if (itemType === 'Medicine' || itemType === 'Prescription') {
            // For Medicine/Prescription items (MRP based)
            // Calculate taxable value (base before GST)
            const gstFactor = gstRate / 100;
            baseBeforeGst = preDiscountAmount / (1 + gstFactor);
            
            // Calculate discount on taxable value
            discountAmount = (baseBeforeGst * discountPercent) / 100;
            
            // Taxable amount after discount
            taxableAmount = baseBeforeGst - discountAmount;
            
            if (isGstInvoice && !isGstExempt && gstRate > 0) {
                // CHANGED: Calculate GST on original base price (before discount)
                if (isInterstate) {
                    igstAmount = baseBeforeGst * gstFactor;
                    totalGstAmount = igstAmount;
                } else {
                    const halfGstRate = gstFactor / 2;
                    cgstAmount = baseBeforeGst * halfGstRate;
                    sgstAmount = baseBeforeGst * halfGstRate;
                    totalGstAmount = cgstAmount + sgstAmount;
                }
            }
            
            // Line total is taxable amount plus GST
            lineTotal = taxableAmount + totalGstAmount;
        } 
        else {
            // For Service/Package items (forward calculation)
            // Calculate discount on original amount
            discountAmount = (preDiscountAmount * discountPercent) / 100;
            
            // Taxable amount after discount
            taxableAmount = preDiscountAmount - discountAmount;
            
            if (isGstInvoice && !isGstExempt && gstRate > 0) {
                // Calculate GST on original amount (pre-discount)
                if (isInterstate) {
                    igstAmount = (preDiscountAmount * gstRate) / 100;
                    totalGstAmount = igstAmount;
                } else {
                    const halfGstRate = gstRate / 2;
                    cgstAmount = (preDiscountAmount * halfGstRate) / 100;
                    sgstAmount = (preDiscountAmount * halfGstRate) / 100;
                    totalGstAmount = cgstAmount + sgstAmount;
                }
            }
            
            // Line total is taxable amount (post-discount) plus GST
            lineTotal = taxableAmount + totalGstAmount;
        }
        
        // Update GST amount display
        const gstAmountEl = row.querySelector('.gst-amount');
        if (gstAmountEl) {
            gstAmountEl.textContent = totalGstAmount.toFixed(2);
        }
        
        // Update line total - using the correct selector
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
            baseBeforeGst,
            cgstAmount,
            sgstAmount,
            igstAmount,
            totalGstAmount,
            lineTotal,
            isDoctorsExamination
        };
    }
    
    // Calculate totals from all line items
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
        
        // Sum values from all rows
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
        
        // Update hidden form fields (if present)
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
    // Elements
    const patientSearch = document.getElementById('patient-search');
    const patientResults = document.getElementById('patient-search-results');
    const patientIdInput = document.getElementById('patient_id');
    const patientNameInput = document.getElementById('patient_name');
    const patientInfo = document.getElementById('selected-patient-info');
    const patientNameDisplay = document.getElementById('patient-name-display');
    const patientMRNDisplay = document.getElementById('patient-mrn-display');
    const patientContactDisplay = document.getElementById('patient-contact-display');
    const invoiceForm = document.getElementById('invoice-form');
    
    if (!patientSearch || !patientResults) {
        console.warn("Patient search elements missing");
        return;
    }
    
    // Ensure patient_id field exists
    let idField = document.getElementById('patient_id');
    if (!idField && invoiceForm) {
        idField = document.createElement('input');
        idField.type = 'hidden';
        idField.id = 'patient_id';
        idField.name = 'patient_id';
        invoiceForm.appendChild(idField);
        console.log("Created patient_id input field");
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
        // Allow empty query to get all patients (this is the only change)
        const searchQuery = query || "";
        
        console.log("Searching patients with query:", searchQuery);
        
        // AJAX request to search patients
        fetch(`/invoice/web_api/patient/search?q=${encodeURIComponent(searchQuery)}`, {
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
                div.setAttribute('data-patient-id', patient.id);
                div.setAttribute('data-patient-name', patient.name);
                
                // Use the same format as existing code
                div.innerHTML = `
                    <div class="font-semibold">${patient.name}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">MRN: ${patient.mrn}</div>
                    <div class="text-sm text-gray-600 dark:text-gray-400">${patient.contact || ''}</div>
                `;
                
                div.addEventListener('click', function() {
                    // Get the hidden patient_id field (or create it if needed)
                    let patientIdField = document.getElementById('patient_id');
                    if (!patientIdField && invoiceForm) {
                        patientIdField = document.createElement('input');
                        patientIdField.type = 'hidden';
                        patientIdField.id = 'patient_id';
                        patientIdField.name = 'patient_id';
                        invoiceForm.appendChild(patientIdField);
                    }
                    
                    // Set hidden input values
                    if (patientIdField) {
                        patientIdField.value = patient.id;
                        console.log("Set patient ID to:", patient.id);
                    }
                    
                    if (patientNameInput) {
                        patientNameInput.value = patient.name;
                    }
                    
                    // Also set data attributes on the form for extra safety
                    if (invoiceForm) {
                        invoiceForm.setAttribute('data-patient-id', patient.id);
                        invoiceForm.setAttribute('data-patient-name', patient.name);
                        console.log("Stored patient ID in form attribute:", patient.id);
                    }
                    
                    // Special handling for JSON objects in patient name
                    if (patient.name && (patient.name.startsWith('{') || patient.raw_info)) {
                        // If we have raw_info use that, otherwise use name
                        const displayName = patient.raw_info || patient.name;
                        
                        // Try to parse and format for display
                        try {
                            const info = JSON.parse(displayName);
                            if (info.first_name && info.last_name) {
                                // Format nicely for display
                                patientSearch.value = `${info.first_name} ${info.last_name} - ${patient.mrn}`;
                            } else {
                                // Fall back to original format
                                patientSearch.value = `${patient.name} - ${patient.mrn}`;
                            }
                        } catch (e) {
                            // Just use as is if parsing fails
                            patientSearch.value = `${patient.name} - ${patient.mrn}`;
                        }
                    } else {
                        // Normal case - no JSON
                        patientSearch.value = `${patient.name} - ${patient.mrn}`;
                    }
                    
                    // Display selected patient info
                    if (patientNameDisplay) patientNameDisplay.textContent = patient.name;
                    if (patientMRNDisplay) patientMRNDisplay.textContent = `MRN: ${patient.mrn}`;
                    if (patientContactDisplay) patientContactDisplay.textContent = patient.contact || '';
                    if (patientInfo) patientInfo.classList.remove('hidden');
                    
                    // Hide results
                    patientResults.classList.add('hidden');
                    
                    console.log("Patient selected:", patient.name, "ID:", patient.id);
                    
                    // For debugging: log all form fields to make sure patient_id is included
                    console.log("Form fields after patient selection:");
                    const formData = new FormData(invoiceForm);
                    for (let pair of formData.entries()) {
                        console.log(pair[0] + ': ' + pair[1]);
                    }
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
    
    
   // Click on search field shows all patients (like item search)
    patientSearch.addEventListener('click', function() {
        // Only show the full list if there's no search in progress yet
        if (!patientResults.classList.contains('hidden')) {
            return;
        }
        
        // Show all patients when clicking on the empty field
        searchPatients("");
        patientResults.classList.remove('hidden');
    });
    
    // Handle direct entry of patient name (without clicking on search results)
    patientSearch.addEventListener('blur', function() {
        setTimeout(() => {
            const query = this.value.trim();
            if (query && !document.getElementById('patient_id')?.value) {
                console.log("Patient name entered directly:", query);
                
                // If we already have the name in the hidden input, we're good
                if (patientNameInput && patientNameInput.value === query) {
                    console.log("Patient name already set in hidden field");
                    return;
                }
                
                // Try to find matching patient
                fetch(`/invoice/web_api/patient/search?q=${encodeURIComponent(query)}`, {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.length === 1) {
                        // Found exactly one match, use it
                        const patient = data[0];
                        
                        // Set patient ID
                        let patientIdField = document.getElementById('patient_id');
                        if (!patientIdField && invoiceForm) {
                            patientIdField = document.createElement('input');
                            patientIdField.type = 'hidden';
                            patientIdField.id = 'patient_id';
                            patientIdField.name = 'patient_id';
                            invoiceForm.appendChild(patientIdField);
                        }
                        
                        if (patientIdField) {
                            patientIdField.value = patient.id;
                            console.log("Auto-selected patient, set ID to:", patient.id);
                        }
                        
                        // Set patient name
                        if (patientNameInput) {
                            patientNameInput.value = patient.name;
                        }
                        
                        // Update form data attributes
                        if (invoiceForm) {
                            invoiceForm.setAttribute('data-patient-id', patient.id);
                            invoiceForm.setAttribute('data-patient-name', patient.name);
                        }
                        
                        // Update display
                        if (patientNameDisplay) patientNameDisplay.textContent = patient.name;
                        if (patientMRNDisplay) patientMRNDisplay.textContent = `MRN: ${patient.mrn}`;
                        if (patientContactDisplay) patientContactDisplay.textContent = patient.contact || '';
                        if (patientInfo) patientInfo.classList.remove('hidden');
                        
                        console.log("Auto-selected patient:", patient.name, "ID:", patient.id);
                    }
                })
                .catch(error => {
                    console.error('Error searching for patient match:', error);
                });
            }
        }, 200);
    });
    
    // Add a check before form submission to double-check patient ID
    const form = document.getElementById('invoice-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            // Check if we have a patient_id
            const patientIdField = document.getElementById('patient_id');
            const patientNameField = document.getElementById('patient_name');
            
            console.log("Form submission: patient_id field exists =", !!patientIdField);
            console.log("Form submission: patient_id value =", patientIdField?.value || 'empty');
            console.log("Form submission: patient_name value =", patientNameField?.value || 'empty');
            
            // Don't prevent submission - just log for debugging
        });
    }
    
    // Hide results when clicking elsewhere
    document.addEventListener('click', function(e) {
        if (!patientSearch.contains(e.target) && !patientResults.contains(e.target)) {
            patientResults.classList.add('hidden');
        }
    });
}

// function initializePatientSearch() {
//     // Elements
//     const patientSearch = document.getElementById('patient-search');
//     const patientResults = document.getElementById('patient-search-results');
//     const patientIdInput = document.getElementById('patient_id');
//     const patientNameInput = document.getElementById('patient_name');
//     const patientInfo = document.getElementById('selected-patient-info');
//     const patientNameDisplay = document.getElementById('patient-name-display');
//     const patientMRNDisplay = document.getElementById('patient-mrn-display');
//     const patientContactDisplay = document.getElementById('patient-contact-display');
//     const invoiceForm = document.getElementById('invoice-form');
    
//     if (!patientSearch || !patientResults) {
//         console.warn("Patient search elements missing");
//         return;
//     }
    
//     // Ensure patient_id field exists
//     let idField = document.getElementById('patient_id');
//     if (!idField && invoiceForm) {
//         idField = document.createElement('input');
//         idField.type = 'hidden';
//         idField.id = 'patient_id';
//         idField.name = 'patient_id';
//         invoiceForm.appendChild(idField);
//         console.log("Created patient_id input field");
//     }
    
//     // Debounce function
//     const debounce = (func, delay) => {
//         let timeout;
//         return function(...args) {
//             clearTimeout(timeout);
//             timeout = setTimeout(() => func.apply(this, args), delay);
//         };
//     };
    
//     // Search patients - using original endpoint
//     const searchPatients = debounce(function(query) {
//         if (query.length < 1) {
//             patientResults.innerHTML = '';
//             patientResults.classList.add('hidden');
//             return;
//         }
        
//         console.log("Searching patients with query:", query);
        
//         // AJAX request to search patients
//         fetch(`/invoice/web_api/patient/search?q=${encodeURIComponent(query)}`, {
//             headers: {
//                 'Content-Type': 'application/json'
//             }
//         })
//         .then(response => response.json())
//         .then(data => {
//             patientResults.innerHTML = '';
            
//             if (data.length === 0) {
//                 patientResults.innerHTML = '<div class="p-2 text-gray-500 dark:text-gray-400">No patients found</div>';
//                 patientResults.classList.remove('hidden');
//                 return;
//             }
            
//             data.forEach(patient => {
//                 const div = document.createElement('div');
//                 div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer';
//                 div.setAttribute('data-patient-id', patient.id);
//                 div.setAttribute('data-patient-name', patient.name);
                
//                 // Use the same format as existing code
//                 div.innerHTML = `
//                     <div class="font-semibold">${patient.name}</div>
//                     <div class="text-sm text-gray-600 dark:text-gray-400">MRN: ${patient.mrn}</div>
//                     <div class="text-sm text-gray-600 dark:text-gray-400">${patient.contact || ''}</div>
//                 `;
                
//                 div.addEventListener('click', function() {
//                     // Get the hidden patient_id field (or create it if needed)
//                     let patientIdField = document.getElementById('patient_id');
//                     if (!patientIdField && invoiceForm) {
//                         patientIdField = document.createElement('input');
//                         patientIdField.type = 'hidden';
//                         patientIdField.id = 'patient_id';
//                         patientIdField.name = 'patient_id';
//                         invoiceForm.appendChild(patientIdField);
//                     }
                    
//                     // Set hidden input values
//                     if (patientIdField) {
//                         patientIdField.value = patient.id;
//                         console.log("Set patient ID to:", patient.id);
//                     }
                    
//                     if (patientNameInput) {
//                         patientNameInput.value = patient.name;
//                     }
                    
//                     // Also set data attributes on the form for extra safety
//                     if (invoiceForm) {
//                         invoiceForm.setAttribute('data-patient-id', patient.id);
//                         invoiceForm.setAttribute('data-patient-name', patient.name);
//                         console.log("Stored patient ID in form attribute:", patient.id);
//                     }
                    
//                     // Update search input
//                     patientSearch.value = `${patient.name} - ${patient.mrn}`;
                    
//                     // Display selected patient info
//                     if (patientNameDisplay) patientNameDisplay.textContent = patient.name;
//                     if (patientMRNDisplay) patientMRNDisplay.textContent = `MRN: ${patient.mrn}`;
//                     if (patientContactDisplay) patientContactDisplay.textContent = patient.contact || '';
//                     if (patientInfo) patientInfo.classList.remove('hidden');
                    
//                     // Hide results
//                     patientResults.classList.add('hidden');
                    
//                     console.log("Patient selected:", patient.name, "ID:", patient.id);
                    
//                     // For debugging: log all form fields to make sure patient_id is included
//                     console.log("Form fields after patient selection:");
//                     const formData = new FormData(invoiceForm);
//                     for (let pair of formData.entries()) {
//                         console.log(pair[0] + ': ' + pair[1]);
//                     }
//                 });
                
//                 patientResults.appendChild(div);
//             });
            
//             patientResults.classList.remove('hidden');
//         })
//         .catch(error => {
//             console.error('Error searching patients:', error);
//             patientResults.innerHTML = '<div class="p-2 text-red-500">Error searching patients</div>';
//             patientResults.classList.remove('hidden');
//         });
//     }, 300);
    
//     // Add event listener for patient search
//     patientSearch.addEventListener('input', function() {
//         const query = this.value.trim();
//         searchPatients(query);
//     });
    
//     // Handle direct entry of patient name (without clicking on search results)
//     patientSearch.addEventListener('blur', function() {
//         setTimeout(() => {
//             const query = this.value.trim();
//             if (query && !document.getElementById('patient_id')?.value) {
//                 console.log("Patient name entered directly:", query);
                
//                 // If we already have the name in the hidden input, we're good
//                 if (patientNameInput && patientNameInput.value === query) {
//                     console.log("Patient name already set in hidden field");
//                     return;
//                 }
                
//                 // Try to find matching patient
//                 fetch(`/invoice/web_api/patient/search?q=${encodeURIComponent(query)}`, {
//                     headers: {
//                         'Content-Type': 'application/json'
//                     }
//                 })
//                 .then(response => response.json())
//                 .then(data => {
//                     if (data.length === 1) {
//                         // Found exactly one match, use it
//                         const patient = data[0];
                        
//                         // Set patient ID
//                         let patientIdField = document.getElementById('patient_id');
//                         if (!patientIdField && invoiceForm) {
//                             patientIdField = document.createElement('input');
//                             patientIdField.type = 'hidden';
//                             patientIdField.id = 'patient_id';
//                             patientIdField.name = 'patient_id';
//                             invoiceForm.appendChild(patientIdField);
//                         }
                        
//                         if (patientIdField) {
//                             patientIdField.value = patient.id;
//                             console.log("Auto-selected patient, set ID to:", patient.id);
//                         }
                        
//                         // Set patient name
//                         if (patientNameInput) {
//                             patientNameInput.value = patient.name;
//                         }
                        
//                         // Update form data attributes
//                         if (invoiceForm) {
//                             invoiceForm.setAttribute('data-patient-id', patient.id);
//                             invoiceForm.setAttribute('data-patient-name', patient.name);
//                         }
                        
//                         // Update display
//                         if (patientNameDisplay) patientNameDisplay.textContent = patient.name;
//                         if (patientMRNDisplay) patientMRNDisplay.textContent = `MRN: ${patient.mrn}`;
//                         if (patientContactDisplay) patientContactDisplay.textContent = patient.contact || '';
//                         if (patientInfo) patientInfo.classList.remove('hidden');
                        
//                         console.log("Auto-selected patient:", patient.name, "ID:", patient.id);
//                     }
//                 })
//                 .catch(error => {
//                     console.error('Error searching for patient match:', error);
//                 });
//             }
//         }, 200);
//     });
    
//     // Add a check before form submission to double-check patient ID
//     const form = document.getElementById('invoice-form');
//     if (form) {
//         form.addEventListener('submit', function(e) {
//             // Check if we have a patient_id
//             const patientIdField = document.getElementById('patient_id');
//             const patientNameField = document.getElementById('patient_name');
            
//             console.log("Form submission: patient_id field exists =", !!patientIdField);
//             console.log("Form submission: patient_id value =", patientIdField?.value || 'empty');
//             console.log("Form submission: patient_name value =", patientNameField?.value || 'empty');
            
//             // Don't prevent submission - just log for debugging
//         });
//     }
    
//     // Hide results when clicking elsewhere
//     document.addEventListener('click', function(e) {
//         if (!patientSearch.contains(e.target) && !patientResults.contains(e.target)) {
//             patientResults.classList.add('hidden');
//         }
//     });
// }

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

// Replace the initializeFormSubmission function with this improved version:

function initializeFormSubmission() {
    console.log("Initializing form submission handler");
    
    const invoiceForm = document.getElementById('invoice-form');
    const submitButton = document.querySelector('button[type="submit"]');
    
    if (!invoiceForm || !submitButton) {
        console.error("Invoice form or submit button not found");
        return;
    }
    
    // Add form submission handler
    submitButton.addEventListener('click', function(e) {
        // Prevent default form submission
        e.preventDefault();
        console.log("Submit button clicked");
        
        // First check if we have any patient information
        const patientSearch = document.getElementById('patient-search');
        if (!patientSearch || !patientSearch.value) {
            alert('Please select a patient before submitting the invoice.');
            if (patientSearch) patientSearch.focus();
            return;
        }
        
        // Prepare form fields for submission
        prepareFormForSubmission();
        
        // Check if we have line items
        const lineItems = document.querySelectorAll('.line-item-row');
        if (lineItems.length === 0) {
            alert('Please add at least one item to the invoice.');
            return;
        }
        
        // Submit the form
        console.log("Form is prepared and ready - submitting now");
        invoiceForm.submit();
    });
}

// Add this new function to ensure the patient_id field always exists
function ensurePatientIdField() {
    const invoiceForm = document.getElementById('invoice-form');
    if (!invoiceForm) return;
    
    // Get patient name and search value
    const patientNameInput = document.getElementById('patient_name');
    const patientSearchInput = document.getElementById('patient-search');
    const patientName = patientNameInput?.value || '';
    const patientSearchValue = patientSearchInput?.value || '';
    
    // Find or create patient_id input
    let patientIdInput = document.getElementById('patient_id');
    
    // If no patient_id input exists, create one
    if (!patientIdInput) {
        patientIdInput = document.createElement('input');
        patientIdInput.type = 'hidden';
        patientIdInput.id = 'patient_id';
        patientIdInput.name = 'patient_id';
        invoiceForm.appendChild(patientIdInput);
        console.log("Created missing patient_id field");
    }
    
    // Check if the patient_id already has a value
    if (!patientIdInput.value || patientIdInput.value.trim() === '') {
        // Try to get ID from data attribute
        const patientIdFromDataAttr = invoiceForm.getAttribute('data-patient-id');
        if (patientIdFromDataAttr) {
            patientIdInput.value = patientIdFromDataAttr;
            console.log("Set patient_id from data attribute:", patientIdFromDataAttr);
        }
        // If we have a patient name but no ID, make sure field exists for server-side lookup
        else if (patientName) {
            console.log("Patient ID not found but name is available:", patientName);
            // Just ensure the field exists - let server handle the lookup
        }
    }
    
    // Log what we're submitting for debugging
    console.log("Patient ID field value:", patientIdInput.value || "empty");
    console.log("Patient name field value:", patientName || "empty");
    console.log("Patient search field value:", patientSearchValue || "empty");
}

// Also modify prepareFormForSubmission to prioritize the actual patient_id field
function prepareFormForSubmission() {
    const invoiceForm = document.getElementById('invoice-form');
    if (!invoiceForm) return;
    
    console.log("Preparing form for submission");
    
    // ===== PATIENT INFORMATION HANDLING =====
    // Get patient information from various sources
    const patientSearch = document.getElementById('patient-search');
    const patientNameField = document.getElementById('patient_name');
    
    // If we have a patient in the search field but not in the name field, copy it
    if (patientSearch && patientSearch.value && patientNameField && !patientNameField.value) {
        // The patient search field has a value but the hidden name field doesn't
        // Extract just the name part (before any " - " delimiter if present)
        let patientName = patientSearch.value;
        if (patientName.includes(" - ")) {
            patientName = patientName.split(" - ")[0];
        }
        patientNameField.value = patientName;
        console.log("Copied patient name from search field:", patientName);
    }
    
    // ===== LINE ITEMS HANDLING =====
    // Remove any previously created line item fields to avoid duplication
    Array.from(invoiceForm.querySelectorAll('input[name^="line_items-"]')).forEach(el => {
        el.remove();
    });
    
    // Get all line item rows
    const lineItems = document.querySelectorAll('.line-item-row');
    
    // Process each line item (same as before)
    lineItems.forEach((row, index) => {
        // Extract values from the row
        const itemType = row.querySelector('.item-type')?.value || 
                        row.getAttribute('data-item-type') || 
                        'Package'; // Default fallback
        
        const itemId = row.querySelector('.item-id')?.value || 
                      row.getAttribute('data-item-id');
        
        const itemName = row.querySelector('.item-name')?.value || 
                        row.getAttribute('data-item-name') || 
                        row.querySelector('.item-search')?.value;
        
        const quantity = row.querySelector('.quantity')?.value || 1;
        const unitPrice = row.querySelector('.unit-price')?.value || 0;
        const discountPercent = row.querySelector('.discount-percent')?.value || 0;
        
        console.log(`Line item ${index}: Type=${itemType}, ID=${itemId}, Name=${itemName}`);
        
        // Create a helper function to add fields
        const createField = (name, value) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = name;
            input.value = value || '';
            invoiceForm.appendChild(input);
        };
        
        // Create all required fields with proper Flask-WTF naming
        createField(`line_items-${index}-item_type`, itemType);
        createField(`line_items-${index}-item_id`, itemId);
        createField(`line_items-${index}-item_name`, itemName);
        createField(`line_items-${index}-quantity`, quantity);
        createField(`line_items-${index}-unit_price`, unitPrice);
        createField(`line_items-${index}-discount_percent`, discountPercent);
        
        // Handle batch and expiry date for medicines
        if (itemType === 'Medicine' || itemType === 'Prescription') {
            const batch = row.querySelector('.batch-select')?.value;
            const expiryDate = row.querySelector('.expiry-date')?.value;
            
            createField(`line_items-${index}-batch`, batch);
            createField(`line_items-${index}-expiry_date`, expiryDate);
        }
        
        // Add included_in_consultation field
        const includedInConsultation = row.querySelector('.included-in-consultation')?.checked || false;
        createField(`line_items-${index}-included_in_consultation`, includedInConsultation ? 'y' : '');
    });
    
    // Set the line items count
    let lineItemsCountField = document.querySelector('input[name="line_items_count"]');
    if (!lineItemsCountField) {
        lineItemsCountField = document.createElement('input');
        lineItemsCountField.type = 'hidden';
        lineItemsCountField.name = 'line_items_count';
        invoiceForm.appendChild(lineItemsCountField);
    }
    lineItemsCountField.value = lineItems.length;
    
    console.log(`Form prepared with ${lineItems.length} line items`);
}

function validateForm() {
    // Get patient ID in multiple ways to ensure we find it
    const invoiceForm = document.getElementById('invoice-form');
    let patientId = document.getElementById('patient_id')?.value;
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
    console.log("Patient info element visible:", !document.getElementById('selected-patient-info')?.classList.contains('hidden'));
    console.log("Patient search value:", document.getElementById('patient-search')?.value);
    
    // Check if patient was selected (either by ID or by the visible patient info)
    const patientSelected = patientId || 
                          (!document.getElementById('selected-patient-info')?.classList.contains('hidden') &&
                           document.getElementById('patient-search')?.value);
    
    if (!patientSelected) {
        alert('Please select a patient.');
        document.getElementById('patient-search')?.focus();
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
        
        console.log(`Validated line item ${index + 1}: ID=${itemId}, Type=${itemType}`);
    });
    
    return isValid;
}

/**
 * Special calculation function for Doctor's Examination and Treatment items
 * These are treated like medicine items where GST is included in MRP
 * @param {number} price - The MRP price
 * @param {number} quantity - Quantity
 * @param {number} discountPercent - Discount percentage
 * @param {number} gstRate - GST rate
 * @param {boolean} isInterstate - Whether this is an interstate transaction
 * @returns {Object} Calculated values including GST components and total
 */
function calculateDoctorsExaminationGST(price, quantity, discountPercent, gstRate, isInterstate) {
    // Calculate pre-discount amount
    const preDiscountAmount = price * quantity;
    
    // Calculate discount
    const discountAmount = (preDiscountAmount * discountPercent) / 100;
    
    // Taxable amount after discount
    const taxableAmount = preDiscountAmount - discountAmount;
    
    // For Doctor's Examination, GST is included in MRP, so reverse calculate
    const gstFactor = gstRate / 100;
    const baseBeforeGst = preDiscountAmount / (1 + gstFactor);
    
    let cgstAmount = 0;
    let sgstAmount = 0;
    let igstAmount = 0;
    
    if (isInterstate) {
        // Interstate: only IGST
        igstAmount = preDiscountAmount - baseBeforeGst;
    } else {
        // Intrastate: CGST + SGST
        const halfGstAmount = (preDiscountAmount - baseBeforeGst) / 2;
        cgstAmount = halfGstAmount;
        sgstAmount = halfGstAmount;
    }
    
    const totalGstAmount = cgstAmount + sgstAmount + igstAmount;
    
    // Line total remains MRP - discount since GST is already included
    const lineTotal = taxableAmount;
    
    return {
        baseBeforeGst,
        taxableAmount,
        cgstAmount,
        sgstAmount,
        igstAmount,
        totalGstAmount,
        lineTotal
    };
}

