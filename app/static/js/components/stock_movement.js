/**
 * Stock Movement Component
 * 
 * A reusable component for handling stock movement operations
 * including transfers, adjustments, and tracking
 */

/**
 * Initialize stock movement functionality
 * @param {HTMLElement} container - The container element for stock movement operations
 */
export function initStockMovement(container) {
    if (!container) return;
    
    // Initialize different types of stock movements based on the container's data attribute
    const movementType = container.getAttribute('data-movement-type');
    
    switch (movementType) {
        case 'transfer':
            initStockTransfer(container);
            break;
        case 'adjustment':
            initStockAdjustment(container);
            break;
        case 'tracking':
            initStockTracking(container);
            break;
        default:
            // Default to basic initialization
            initBasicStockMovement(container);
    }
}

/**
 * Initialize basic stock movement functionality
 * @param {HTMLElement} container - The container element
 */
function initBasicStockMovement(container) {
    // Set up medicine selection
    const medicineSelect = container.querySelector('.medicine-select');
    if (medicineSelect) {
        medicineSelect.addEventListener('change', function() {
            if (this.value) {
                loadMedicineDetails(this.value, container);
            } else {
                // Clear medicine details
                const detailsContainer = container.querySelector('.medicine-details');
                if (detailsContainer) {
                    detailsContainer.innerHTML = '';
                    detailsContainer.classList.add('hidden');
                }
            }
        });
        
        // Load initial medicine details if a medicine is selected
        if (medicineSelect.value) {
            loadMedicineDetails(medicineSelect.value, container);
        }
    }
    
    // Set up batch selection via the batch selector component
    const batchContainer = container.querySelector('.batch-selector');
    if (batchContainer) {
        import('./batch_selector.js')
            .then(module => {
                module.initBatchSelector(batchContainer);
            })
            .catch(err => {
                console.error('Failed to load batch selector component:', err);
            });
    }
    
    // Set up form validation
    const form = container.closest('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateStockMovementForm(form)) {
                e.preventDefault();
                return false;
            }
        });
    }
}

/**
 * Initialize stock transfer functionality
 * @param {HTMLElement} container - The container element
 */
function initStockTransfer(container) {
    // Initialize basic stock movement first
    initBasicStockMovement(container);
    
    // Additional transfer-specific setup
    const sourceLocationSelect = container.querySelector('#source_location');
    const targetLocationSelect = container.querySelector('#target_location');
    
    if (sourceLocationSelect && targetLocationSelect) {
        // Prevent selecting the same location for source and target
        sourceLocationSelect.addEventListener('change', function() {
            validateLocations(sourceLocationSelect, targetLocationSelect);
        });
        
        targetLocationSelect.addEventListener('change', function() {
            validateLocations(sourceLocationSelect, targetLocationSelect);
        });
        
        // Initial validation
        validateLocations(sourceLocationSelect, targetLocationSelect);
    }
}

/**
 * Validate that source and target locations are different
 * @param {HTMLSelectElement} sourceSelect - The source location select element
 * @param {HTMLSelectElement} targetSelect - The target location select element
 */
function validateLocations(sourceSelect, targetSelect) {
    if (sourceSelect.value && targetSelect.value && sourceSelect.value === targetSelect.value) {
        // Show error
        const errorElement = document.getElementById('location_error');
        if (errorElement) {
            errorElement.textContent = 'Source and target locations cannot be the same.';
            errorElement.classList.remove('hidden');
        }
        
        // Disable submit button
        const submitButton = document.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
        }
    } else {
        // Hide error
        const errorElement = document.getElementById('location_error');
        if (errorElement) {
            errorElement.textContent = '';
            errorElement.classList.add('hidden');
        }
        
        // Enable submit button
        const submitButton = document.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = false;
        }
    }
}

/**
 * Initialize stock adjustment functionality
 * @param {HTMLElement} container - The container element
 */
function initStockAdjustment(container) {
    // Initialize basic stock movement first
    initBasicStockMovement(container);
    
    // Additional adjustment-specific setup
    const adjustmentTypeRadios = container.querySelectorAll('input[name="adjustment_type"]');
    const quantityInput = container.querySelector('#adjustment_quantity');
    const quantityLabel = container.querySelector('label[for="adjustment_quantity"]');
    
    // Update quantity label based on adjustment type
    adjustmentTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (quantityLabel) {
                quantityLabel.textContent = this.value === 'addition' ? 'Quantity to Add:' : 'Quantity to Remove:';
            }
        });
    });
    
    // Validate quantity against current stock for deductions
    if (quantityInput) {
        quantityInput.addEventListener('input', function() {
            const adjustmentType = container.querySelector('input[name="adjustment_type"]:checked')?.value;
            if (adjustmentType === 'deduction') {
                validateDeductionQuantity(container);
            }
        });
    }
    
    // Check the adjustment type when medicine or batch changes
    const medicineSelect = container.querySelector('.medicine-select');
    const batchSelect = container.querySelector('.batch-select');
    
    if (medicineSelect) {
        medicineSelect.addEventListener('change', function() {
            const adjustmentType = container.querySelector('input[name="adjustment_type"]:checked')?.value;
            if (adjustmentType === 'deduction') {
                // Reset quantity since medicine changed
                if (quantityInput) {
                    quantityInput.value = '';
                }
            }
        });
    }
    
    if (batchSelect) {
        batchSelect.addEventListener('change', function() {
            const adjustmentType = container.querySelector('input[name="adjustment_type"]:checked')?.value;
            if (adjustmentType === 'deduction') {
                validateDeductionQuantity(container);
            }
        });
    }
    
    // Also check when adjustment type changes
    adjustmentTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'deduction') {
                validateDeductionQuantity(container);
            } else {
                // Clear any error
                const errorElement = container.querySelector('#quantity_error');
                if (errorElement) {
                    errorElement.textContent = '';
                    errorElement.classList.add('hidden');
                }
                
                // Enable submit button
                const submitButton = container.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = false;
                }
            }
        });
    });
}

/**
 * Validate deduction quantity against available stock
 * @param {HTMLElement} container - The container element
 */
function validateDeductionQuantity(container) {
    const quantityInput = container.querySelector('#adjustment_quantity');
    const batchSelect = container.querySelector('.batch-select');
    const errorElement = container.querySelector('#quantity_error');
    const submitButton = container.querySelector('button[type="submit"]');
    
    if (!quantityInput || !batchSelect || !errorElement) return;
    
    const quantity = parseFloat(quantityInput.value) || 0;
    const selectedOption = batchSelect.options[batchSelect.selectedIndex];
    
    if (!selectedOption || !selectedOption.value) return;
    
    const availableQuantity = parseFloat(selectedOption.getAttribute('data-quantity')) || 0;
    
    if (quantity > availableQuantity) {
        // Show error
        errorElement.textContent = `Cannot remove more than available stock (${availableQuantity}).`;
        errorElement.classList.remove('hidden');
        
        // Disable submit button
        if (submitButton) {
            submitButton.disabled = true;
        }
    } else {
        // Hide error
        errorElement.textContent = '';
        errorElement.classList.add('hidden');
        
        // Enable submit button
        if (submitButton) {
            submitButton.disabled = false;
        }
    }
}

/**
 * Initialize stock tracking functionality
 * @param {HTMLElement} container - The container element
 */
function initStockTracking(container) {
    // Set up filter functionality
    const filterForm = container.querySelector('.stock-tracking-filter');
    if (filterForm) {
        // Auto-submit on filter change if auto-submit is checked
        const filterInputs = filterForm.querySelectorAll('select, input:not([type="checkbox"])');
        filterInputs.forEach(input => {
            input.addEventListener('change', function() {
                const autoSubmit = filterForm.querySelector('#auto_submit');
                if (autoSubmit && autoSubmit.checked) {
                    filterForm.submit();
                }
            });
        });
    }
    
    // Set up date range picker if available
    const dateRangeSelect = container.querySelector('#date_range');
    const fromDateInput = container.querySelector('#from_date');
    const toDateInput = container.querySelector('#to_date');
    
    if (dateRangeSelect && fromDateInput && toDateInput) {
        dateRangeSelect.addEventListener('change', function() {
            if (this.value) {
                setDateRange(this.value, fromDateInput, toDateInput);
            }
        });
    }
    
    // Set up stock movement details modal
    const viewButtons = container.querySelectorAll('.view-movement-btn');
    viewButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const movementId = this.getAttribute('data-movement-id');
            if (movementId) {
                showMovementDetails(movementId);
            }
        });
    });
}

/**
 * Set date range based on a predefined range
 * @param {string} range - The predefined date range
 * @param {HTMLInputElement} fromDateInput - The from date input element
 * @param {HTMLInputElement} toDateInput - The to date input element
 */
function setDateRange(range, fromDateInput, toDateInput) {
    const today = new Date();
    let fromDate = new Date();
    let toDate = new Date();
    
    switch (range) {
        case 'today':
            // Both today
            break;
            
        case 'yesterday':
            fromDate.setDate(today.getDate() - 1);
            toDate.setDate(today.getDate() - 1);
            break;
            
        case 'this_week':
            fromDate.setDate(today.getDate() - today.getDay());
            break;
            
        case 'last_week':
            fromDate.setDate(today.getDate() - today.getDay() - 7);
            toDate.setDate(today.getDate() - today.getDay() - 1);
            break;
            
        case 'this_month':
            fromDate = new Date(today.getFullYear(), today.getMonth(), 1);
            break;
            
        case 'last_month':
            fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            toDate = new Date(today.getFullYear(), today.getMonth(), 0);
            break;
            
        case 'custom':
            // Don't change dates for custom range
            return;
    }
    
    // Format dates for input fields
    fromDateInput.value = formatDateForInput(fromDate);
    toDateInput.value = formatDateForInput(toDate);
}

/**
 * Format a date object as YYYY-MM-DD for input fields
 * @param {Date} date - The date object to format
 * @returns {string} Formatted date string
 */
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

/**
 * Show stock movement details in a modal
 * @param {string} movementId - The ID of the stock movement to show
 */
function showMovementDetails(movementId) {
    const modal = document.getElementById('movementDetailsModal');
    const modalContent = document.getElementById('movementDetailsContent');
    
    if (!modal || !modalContent) return;
    
    // Show modal
    modal.classList.remove('hidden');
    
    // Show loading state
    modalContent.innerHTML = `
        <div class="flex items-center justify-center p-8">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
    `;
    
    // Fetch movement details
    fetch(`/api/inventory/stock-movement/${movementId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const movement = data.movement;
                
                // Format date for display
                const movementDate = new Date(movement.transaction_date);
                const formattedDate = movementDate.toLocaleDateString('en-GB', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                // Build details HTML
                modalContent.innerHTML = `
                    <div class="bg-white dark:bg-gray-800 p-6 rounded-lg">
                        <h3 class="text-lg font-semibold mb-4 dark:text-gray-200">${movement.medicine_name} - ${movement.stock_type}</h3>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                            <div>
                                <p class="text-sm text-gray-500 dark:text-gray-400">Transaction Date</p>
                                <p class="font-medium dark:text-gray-300">${formattedDate}</p>
                            </div>
                            <div>
                                <p class="text-sm text-gray-500 dark:text-gray-400">Batch</p>
                                <p class="font-medium dark:text-gray-300">${movement.batch}</p>
                            </div>
                            <div>
                                <p class="text-sm text-gray-500 dark:text-gray-400">Quantity</p>
                                <p class="font-medium ${parseInt(movement.units) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
                                    ${parseInt(movement.units) >= 0 ? '+' : ''}${movement.units} units
                                </p>
                            </div>
                            <div>
                                <p class="text-sm text-gray-500 dark:text-gray-400">Current Stock</p>
                                <p class="font-medium dark:text-gray-300">${movement.current_stock} units</p>
                            </div>
                        </div>
                        
                        ${movement.reference_id ? `
                        <div class="mb-4">
                            <p class="text-sm text-gray-500 dark:text-gray-400">Reference</p>
                            <p class="font-medium dark:text-gray-300">${movement.reference_id}</p>
                        </div>
                        ` : ''}
                        
                        ${movement.reason ? `
                        <div class="mb-4">
                            <p class="text-sm text-gray-500 dark:text-gray-400">Reason</p>
                            <p class="dark:text-gray-300">${movement.reason}</p>
                        </div>
                        ` : ''}
                        
                        <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                            <p class="text-sm text-gray-500 dark:text-gray-400">Additional Details</p>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                                <div>
                                    <p class="text-sm dark:text-gray-300">Expiry: ${movement.expiry ? new Date(movement.expiry).toLocaleDateString('en-GB') : 'N/A'}</p>
                                </div>
                                <div>
                                    <p class="text-sm dark:text-gray-300">Location: ${movement.location || 'Main Store'}</p>
                                </div>
                                ${movement.distributor_invoice_no ? `
                                <div>
                                    <p class="text-sm dark:text-gray-300">Distributor Invoice: ${movement.distributor_invoice_no}</p>
                                </div>
                                ` : ''}
                                ${movement.po_id ? `
                                <div>
                                    <p class="text-sm dark:text-gray-300">PO Number: ${movement.po_number || movement.po_id}</p>
                                </div>
                                ` : ''}
                                ${movement.bill_id ? `
                                <div>
                                    <p class="text-sm dark:text-gray-300">Bill Number: ${movement.bill_number || movement.bill_id}</p>
                                </div>
                                ` : ''}
                                ${movement.patient_id ? `
                                <div>
                                    <p class="text-sm dark:text-gray-300">Patient: ${movement.patient_name || movement.patient_id}</p>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                        
                        <div class="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4">
                            <p class="text-sm text-gray-500 dark:text-gray-400">Transaction Information</p>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                                <div>
                                    <p class="text-sm dark:text-gray-300">Created by: ${movement.created_by || 'System'}</p>
                                </div>
                                <div>
                                    <p class="text-sm dark:text-gray-300">Created at: ${new Date(movement.created_at).toLocaleString()}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                modalContent.innerHTML = `
                    <div class="bg-red-50 dark:bg-red-900 p-4 rounded-md">
                        <p class="text-red-600 dark:text-red-400">${data.message || 'Failed to load movement details'}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error fetching movement details:', error);
            modalContent.innerHTML = `
                <div class="bg-red-50 dark:bg-red-900 p-4 rounded-md">
                    <p class="text-red-600 dark:text-red-400">Error loading movement details. Please try again.</p>
                </div>
            `;
        });
    
    // Set up close button
    const closeBtn = document.getElementById('closeMovementModal');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.classList.add('hidden');
        });
    }
}

/**
 * Load medicine details via AJAX
 * @param {string} medicineId - The ID of the medicine
 * @param {HTMLElement} container - The container element
 */
function loadMedicineDetails(medicineId, container) {
    if (!medicineId) return;
    
    // Show loading indicator
    const detailsContainer = container.querySelector('.medicine-details');
    if (detailsContainer) {
        detailsContainer.innerHTML = '<div class="text-center py-4"><div class="spinner"></div><p class="mt-2 text-gray-600 dark:text-gray-400">Loading medicine details...</p></div>';
        detailsContainer.classList.remove('hidden');
    }
    
    // Fetch medicine details via AJAX
    fetch(`/api/inventory/medicine/${medicineId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update UI
                if (detailsContainer) {
                    detailsContainer.innerHTML = `
                        <div class="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                            <h3 class="font-semibold text-lg mb-2 dark:text-gray-200">${data.medicine.name}</h3>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Current Stock: <span class="font-semibold dark:text-gray-300">${data.medicine.current_stock} ${data.medicine.unit_of_measure}</span></p>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Category: <span class="font-semibold dark:text-gray-300">${data.medicine.category}</span></p>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Safety Stock: <span class="font-semibold dark:text-gray-300">${data.medicine.safety_stock} ${data.medicine.unit_of_measure}</span></p>
                                </div>
                                <div>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Manufacturer: <span class="font-semibold dark:text-gray-300">${data.medicine.manufacturer}</span></p>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Last Updated: <span class="font-semibold dark:text-gray-300">${data.medicine.last_updated}</span></p>
                                </div>
                            </div>
                        </div>
                    `;
                }
            } else {
                if (detailsContainer) {
                    detailsContainer.innerHTML = `
                        <div class="bg-red-50 dark:bg-red-900 p-4 rounded-lg">
                            <p class="text-red-600 dark:text-red-400">${data.message || 'Failed to load medicine details'}</p>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('Error fetching medicine details:', error);
            if (detailsContainer) {
                detailsContainer.innerHTML = `
                    <div class="bg-red-50 dark:bg-red-900 p-4 rounded-lg">
                        <p class="text-red-600 dark:text-red-400">Error loading medicine details. Please try again.</p>
                    </div>
                `;
            }
        });
}

/**
 * Validate the stock movement form
 * @param {HTMLFormElement} form - The form element
 * @returns {boolean} Whether the form is valid
 */
function validateStockMovementForm(form) {
    if (!form) return false;
    
    let isValid = true;
    let errorMessage = '';
    
    // Get the movement type from the container
    const container = form.querySelector('[data-movement-type]');
    const movementType = container ? container.getAttribute('data-movement-type') : null;
    
    // Basic validations for all movement types
    const medicineSelect = form.querySelector('.medicine-select');
    if (medicineSelect && !medicineSelect.value) {
        errorMessage += 'Please select a medicine.\n';
        isValid = false;
    }
    
    // Check if we need batch validation
    const batchIdInput = form.querySelector('.batch-id-input');
    const batchNumberInput = form.querySelector('.batch-number-input');
    const manualEntryToggle = form.querySelector('.manual-entry-toggle');
    
    if (batchIdInput || batchNumberInput) {
        // If manual entry is not checked, batch ID is required
        if (manualEntryToggle && !manualEntryToggle.checked) {
            if (batchIdInput && !batchIdInput.value) {
                errorMessage += 'Please select a batch.\n';
                isValid = false;
            }
        } 
        // If manual entry is checked, batch number is required
        else if (manualEntryToggle && manualEntryToggle.checked) {
            if (batchNumberInput && !batchNumberInput.value) {
                errorMessage += 'Please enter a batch number.\n';
                isValid = false;
            }
            
            // Also validate expiry date
            const expiryDateInput = form.querySelector('.expiry-date-input');
            if (expiryDateInput && !expiryDateInput.value) {
                errorMessage += 'Please enter an expiry date.\n';
                isValid = false;
            }
        }
    }
    
    // Validate quantity
    const quantityInput = form.querySelector('#adjustment_quantity, #transfer_quantity');
    if (quantityInput && (!quantityInput.value || parseFloat(quantityInput.value) <= 0)) {
        errorMessage += 'Please enter a valid quantity greater than zero.\n';
        isValid = false;
    }
    
    // Movement type specific validations
    if (movementType === 'transfer') {
        const sourceLocationSelect = form.querySelector('#source_location');
        const targetLocationSelect = form.querySelector('#target_location');
        
        if (sourceLocationSelect && !sourceLocationSelect.value) {
            errorMessage += 'Please select a source location.\n';
            isValid = false;
        }
        
        if (targetLocationSelect && !targetLocationSelect.value) {
            errorMessage += 'Please select a target location.\n';
            isValid = false;
        }
        
        if (sourceLocationSelect && targetLocationSelect && 
            sourceLocationSelect.value && targetLocationSelect.value && 
            sourceLocationSelect.value === targetLocationSelect.value) {
            errorMessage += 'Source and target locations cannot be the same.\n';
            isValid = false;
        }
    } else if (movementType === 'adjustment') {
        const adjustmentTypeRadios = form.querySelectorAll('input[name="adjustment_type"]');
        let adjustmentTypeSelected = false;
        
        adjustmentTypeRadios.forEach(radio => {
            if (radio.checked) {
                adjustmentTypeSelected = true;
            }
        });
        
        if (!adjustmentTypeSelected) {
            errorMessage += 'Please select an adjustment type (addition or deduction).\n';
            isValid = false;
        }
        
        const reasonInput = form.querySelector('#adjustment_reason');
        if (reasonInput && (!reasonInput.value || reasonInput.value.trim().length < 5)) {
            errorMessage += 'Please provide a more detailed reason for this adjustment.\n';
            isValid = false;
        }
        
        // Validate deduction quantity against available stock
        const adjustmentType = form.querySelector('input[name="adjustment_type"]:checked')?.value;
        if (adjustmentType === 'deduction' && batchIdInput && batchIdInput.value) {
            const batchSelect = form.querySelector('.batch-select');
            if (batchSelect && quantityInput) {
                const selectedOption = batchSelect.options[batchSelect.selectedIndex];
                if (selectedOption && selectedOption.value) {
                    const availableQuantity = parseFloat(selectedOption.getAttribute('data-quantity')) || 0;
                    const deductionQuantity = parseFloat(quantityInput.value) || 0;
                    
                    if (deductionQuantity > availableQuantity) {
                        errorMessage += `Cannot remove more than available stock (${availableQuantity}).\n`;
                        isValid = false;
                    }
                }
            }
        }
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

// Export module functions
export { 
    initStockMovement,
    initStockTransfer,
    initStockAdjustment,
    initStockTracking
};