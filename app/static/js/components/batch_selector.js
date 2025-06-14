/**
 * Batch Selector Component
 * 
 * A reusable component for selecting medicine batches with expiry dates
 * Supports filtering, sorting, and validation of batch data
 */

/**
 * Initialize a batch selector component
 * @param {HTMLElement} element - The batch selector container element
 */
export function initBatchSelector(element) {
    if (!element) return;
    
    // Get the medicine ID hidden input
    const medicineIdInput = element.querySelector('.medicine-id-input');
    if (!medicineIdInput) return;
    
    // Get the batch selection elements
    const batchSelect = element.querySelector('.batch-select');
    const batchIdInput = element.querySelector('.batch-id-input');
    const batchNumberInput = element.querySelector('.batch-number-input');
    const expiryDateInput = element.querySelector('.expiry-date-input');
    const quantityAvailableElement = element.querySelector('.quantity-available');
    const quantityInput = element.querySelector('.quantity-input');
    
    if (!batchSelect || !batchIdInput || !batchNumberInput || !expiryDateInput) return;
    
    // Load initial batches if medicine ID is already set
    if (medicineIdInput.value) {
        loadBatches(medicineIdInput.value, element);
    }
    
    // Handle medicine selection change
    medicineIdInput.addEventListener('change', function() {
        loadBatches(this.value, element);
    });
    
    // Handle batch selection change
    batchSelect.addEventListener('change', function() {
        const selectedBatch = this.options[this.selectedIndex];
        
        if (selectedBatch && selectedBatch.value) {
            // Update batch inputs
            batchIdInput.value = selectedBatch.value;
            batchNumberInput.value = selectedBatch.getAttribute('data-batch-number') || '';
            
            const expiryDate = selectedBatch.getAttribute('data-expiry-date');
            if (expiryDate) {
                expiryDateInput.value = formatDateForInput(new Date(expiryDate));
            } else {
                expiryDateInput.value = '';
            }
            
            // Update available quantity
            const availableQty = selectedBatch.getAttribute('data-quantity') || '0';
            if (quantityAvailableElement) {
                quantityAvailableElement.textContent = availableQty;
                
                // Highlight if low stock
                if (parseFloat(availableQty) < 5) {
                    quantityAvailableElement.classList.add('text-yellow-600', 'dark:text-yellow-400');
                    if (parseFloat(availableQty) <= 0) {
                        quantityAvailableElement.classList.add('text-red-600', 'dark:text-red-400');
                    }
                } else {
                    quantityAvailableElement.classList.remove('text-yellow-600', 'dark:text-yellow-400', 'text-red-600', 'dark:text-red-400');
                }
            }
            
            // Set max quantity if input exists
            if (quantityInput) {
                quantityInput.setAttribute('max', availableQty);
                
                // If current quantity is higher than available, adjust it
                if (parseFloat(quantityInput.value) > parseFloat(availableQty)) {
                    quantityInput.value = availableQty;
                }
            }
            
            // Check expiry date and show warning if expired or near expiry
            if (expiryDate) {
                checkExpiryDate(expiryDate, element);
            }
        } else {
            // Clear inputs for 'Select Batch' option
            batchIdInput.value = '';
            batchNumberInput.value = '';
            expiryDateInput.value = '';
            
            if (quantityAvailableElement) {
                quantityAvailableElement.textContent = '0';
                quantityAvailableElement.classList.remove('text-yellow-600', 'dark:text-yellow-400', 'text-red-600', 'dark:text-red-400');
            }
            
            if (quantityInput) {
                quantityInput.removeAttribute('max');
            }
            
            // Clear any warning
            const warningElement = element.querySelector('.expiry-warning');
            if (warningElement) {
                warningElement.classList.add('hidden');
            }
        }
    });
    
    // Handle manual batch entry if implemented
    const manualEntryToggle = element.querySelector('.manual-entry-toggle');
    if (manualEntryToggle) {
        manualEntryToggle.addEventListener('change', function() {
            toggleManualEntry(this.checked, element);
        });
    }
}

/**
 * Load batches for a medicine via AJAX
 * @param {string} medicineId - The ID of the medicine
 * @param {HTMLElement} element - The batch selector container element
 */
function loadBatches(medicineId, element) {
    if (!medicineId) return;
    
    const batchSelect = element.querySelector('.batch-select');
    if (!batchSelect) return;
    
    // Show loading state
    batchSelect.disabled = true;
    batchSelect.innerHTML = '<option value="">Loading batches...</option>';
    
    // Reset other fields
    const batchIdInput = element.querySelector('.batch-id-input');
    const batchNumberInput = element.querySelector('.batch-number-input');
    const expiryDateInput = element.querySelector('.expiry-date-input');
    
    if (batchIdInput) batchIdInput.value = '';
    if (batchNumberInput) batchNumberInput.value = '';
    if (expiryDateInput) expiryDateInput.value = '';
    
    // Fetch batches via AJAX
    fetch(`/api/inventory/medicine/${medicineId}/batches`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reset select
                batchSelect.innerHTML = '<option value="">Select Batch</option>';
                
                // Sort batches by expiry date (oldest first)
                data.batches.sort((a, b) => new Date(a.expiry_date) - new Date(b.expiry_date));
                
                // Add batch options
                data.batches.forEach(batch => {
                    const option = document.createElement('option');
                    option.value = batch.batch_id;
                    option.textContent = `${batch.batch_number} - Exp: ${formatDate(batch.expiry_date)} (${batch.quantity} available)`;
                    
                    // Set data attributes for easy access
                    option.setAttribute('data-batch-number', batch.batch_number);
                    option.setAttribute('data-expiry-date', batch.expiry_date);
                    option.setAttribute('data-quantity', batch.quantity);
                    
                    // Highlight near expiry or low stock batches
                    const expiryDate = new Date(batch.expiry_date);
                    const today = new Date();
                    const daysToExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
                    
                    if (daysToExpiry <= 0) {
                        // Expired
                        option.classList.add('text-red-600');
                    } else if (daysToExpiry <= 90) {
                        // Expiring soon
                        option.classList.add('text-yellow-600');
                    }
                    
                    batchSelect.appendChild(option);
                });
                
                // Enable select
                batchSelect.disabled = false;
                
            } else {
                batchSelect.innerHTML = '<option value="">No batches available</option>';
                batchSelect.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error fetching batches:', error);
            batchSelect.innerHTML = '<option value="">Error loading batches</option>';
            batchSelect.disabled = false;
        });
}

/**
 * Check expiry date and show warning if needed
 * @param {string} expiryDateStr - The expiry date string
 * @param {HTMLElement} element - The batch selector container element
 */
function checkExpiryDate(expiryDateStr, element) {
    const expiryDate = new Date(expiryDateStr);
    const today = new Date();
    const warningElement = element.querySelector('.expiry-warning');
    
    if (!warningElement) return;
    
    // Calculate days until expiry
    const daysToExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
    
    if (daysToExpiry <= 0) {
        // Expired
        warningElement.textContent = 'Warning: This batch has expired!';
        warningElement.classList.remove('hidden', 'bg-yellow-100', 'text-yellow-800', 'dark:bg-yellow-900', 'dark:text-yellow-200');
        warningElement.classList.add('bg-red-100', 'text-red-800', 'dark:bg-red-900', 'dark:text-red-200');
    } else if (daysToExpiry <= 30) {
        // Expiring very soon
        warningElement.textContent = `Warning: This batch expires in ${daysToExpiry} day${daysToExpiry !== 1 ? 's' : ''}!`;
        warningElement.classList.remove('hidden', 'bg-red-100', 'text-red-800', 'dark:bg-red-900', 'dark:text-red-200');
        warningElement.classList.add('bg-yellow-100', 'text-yellow-800', 'dark:bg-yellow-900', 'dark:text-yellow-200');
    } else if (daysToExpiry <= 90) {
        // Expiring soon
        warningElement.textContent = `Note: This batch expires in ${daysToExpiry} days.`;
        warningElement.classList.remove('hidden', 'bg-red-100', 'text-red-800', 'dark:bg-red-900', 'dark:text-red-200');
        warningElement.classList.add('bg-yellow-100', 'text-yellow-800', 'dark:bg-yellow-900', 'dark:text-yellow-200');
    } else {
        // Not expiring soon
        warningElement.classList.add('hidden');
    }
}

export function validateBatchQuantity(batchSelect, quantityInput) {
    if (!batchSelect || !quantityInput) return;
    
    const selectedOption = batchSelect.options[batchSelect.selectedIndex];
    if (!selectedOption || !selectedOption.value) return;
    
    // Get available quantity from the data attribute
    const availableQty = parseFloat(selectedOption.getAttribute('data-quantity') || '0');
    const currentQty = parseFloat(quantityInput.value || '1');
    
    // Only adjust if current quantity exceeds available AND available is > 0
    if (currentQty > availableQty && availableQty > 0) {
        // Update quantity field with max available stock
        quantityInput.value = availableQty;
        
        // Visual feedback 
        alert(`Quantity adjusted to maximum available: ${availableQty}`);
    }
}