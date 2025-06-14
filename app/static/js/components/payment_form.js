/**
 * Payment Form Component
 * 
 * A reusable component for handling payment forms with multiple payment methods
 * and invoice allocation functionality
 */

/**
 * Initialize a payment form component
 * @param {HTMLElement} formElement - The payment form element
 */
export function initPaymentForm(formElement) {
    if (!formElement) return;
    
    // Get key elements
    const paymentMethodSelect = formElement.querySelector('#payment_method');
    const paymentMethodDetails = formElement.querySelectorAll('.payment-method-details');
    const amountInput = formElement.querySelector('#amount');
    const totalAmountElement = formElement.querySelector('#total_amount');
    const allocateAllBtn = formElement.querySelector('#allocate_all_btn');
    const invoiceItems = formElement.querySelectorAll('.invoice-item');
    const allocatedTotalElement = formElement.querySelector('#allocated_total');
    const remainingToAllocateElement = formElement.querySelector('#remaining_to_allocate');
    
    // Initialize payment method details visibility
    if (paymentMethodSelect) {
        // Hide all payment method details initially
        paymentMethodDetails.forEach(details => {
            details.classList.add('hidden');
        });
        
        // Show the selected payment method details
        const selectedMethod = paymentMethodSelect.value;
        if (selectedMethod) {
            const selectedDetails = formElement.querySelector(`#${selectedMethod}_details`);
            if (selectedDetails) {
                selectedDetails.classList.remove('hidden');
            }
        }
        
        // Handle payment method change
        paymentMethodSelect.addEventListener('change', function() {
            // Hide all payment method details
            paymentMethodDetails.forEach(details => {
                details.classList.add('hidden');
            });
            
            // Show the selected payment method details
            const selectedMethod = this.value;
            const selectedDetails = formElement.querySelector(`#${selectedMethod}_details`);
            if (selectedDetails) {
                selectedDetails.classList.remove('hidden');
            }
        });
    }
    
    // Handle auto-allocation of amount to invoices
    if (allocateAllBtn && amountInput && totalAmountElement) {
        allocateAllBtn.addEventListener('click', function() {
            const amount = parseFloat(amountInput.value) || 0;
            const totalDue = parseFloat(totalAmountElement.getAttribute('data-amount')) || 0;
            
            // Calculate allocation ratio (amount to allocate / total due)
            const allocationRatio = amount / totalDue;
            
            // Allocate to each invoice proportionally
            invoiceItems.forEach(item => {
                const invoiceAmount = parseFloat(item.getAttribute('data-amount')) || 0;
                const invoiceAllocationInput = item.querySelector('.invoice-allocation');
                
                if (invoiceAllocationInput) {
                    // Calculate allocation for this invoice
                    let allocation;
                    if (allocationRatio >= 1) {
                        // If payment covers all, allocate the full invoice amount
                        allocation = invoiceAmount;
                    } else {
                        // Otherwise, allocate proportionally
                        allocation = invoiceAmount * allocationRatio;
                        // Round to 2 decimal places
                        allocation = Math.round(allocation * 100) / 100;
                    }
                    
                    invoiceAllocationInput.value = allocation.toFixed(2);
                }
            });
            
            // Update allocation totals
            updateAllocationTotals();
        });
    }
    
    // Handle amount input changes
    if (amountInput) {
        amountInput.addEventListener('input', function() {
            updateAllocationTotals();
        });
    }
    
    // Handle invoice allocation input changes
    invoiceItems.forEach(item => {
        const invoiceAllocationInput = item.querySelector('.invoice-allocation');
        if (invoiceAllocationInput) {
            invoiceAllocationInput.addEventListener('input', function() {
                // Validate that allocation doesn't exceed invoice amount
                const invoiceAmount = parseFloat(item.getAttribute('data-amount')) || 0;
                let allocation = parseFloat(this.value) || 0;
                
                if (allocation > invoiceAmount) {
                    allocation = invoiceAmount;
                    this.value = allocation.toFixed(2);
                }
                
                updateAllocationTotals();
            });
        }
    });
    
    // Initialize allocation totals
    updateAllocationTotals();
    
    // Form validation
    formElement.addEventListener('submit', function(e) {
        if (!validatePaymentForm(formElement)) {
            e.preventDefault();
            return false;
        }
    });
}

/**
 * Update allocation totals
 */
function updateAllocationTotals() {
    const formElement = document.getElementById('supplierPaymentForm') || document.getElementById('patientPaymentForm');
    if (!formElement) return;
    
    const amountInput = formElement.querySelector('#amount');
    const allocatedTotalElement = formElement.querySelector('#allocated_total');
    const remainingToAllocateElement = formElement.querySelector('#remaining_to_allocate');
    const invoiceItems = formElement.querySelectorAll('.invoice-item');
    
    if (!amountInput || !allocatedTotalElement || !remainingToAllocateElement) return;
    
    const totalAmount = parseFloat(amountInput.value) || 0;
    let allocatedTotal = 0;
    
    // Sum up all allocations
    invoiceItems.forEach(item => {
        const invoiceAllocationInput = item.querySelector('.invoice-allocation');
        if (invoiceAllocationInput) {
            allocatedTotal += parseFloat(invoiceAllocationInput.value) || 0;
        }
    });
    
    // Round to 2 decimal places to avoid floating point issues
    allocatedTotal = Math.round(allocatedTotal * 100) / 100;
    
    // Update allocated total display
    allocatedTotalElement.textContent = allocatedTotal.toFixed(2);
    
    // Update remaining to allocate
    const remainingToAllocate = Math.max(0, totalAmount - allocatedTotal);
    remainingToAllocateElement.textContent = remainingToAllocate.toFixed(2);
    
    // Add visual indicators if allocation doesn't match payment amount
    if (Math.abs(totalAmount - allocatedTotal) > 0.01) {
        remainingToAllocateElement.classList.remove('text-green-600', 'dark:text-green-400');
        remainingToAllocateElement.classList.add('text-red-600', 'dark:text-red-400');
    } else {
        remainingToAllocateElement.classList.remove('text-red-600', 'dark:text-red-400');
        remainingToAllocateElement.classList.add('text-green-600', 'dark:text-green-400');
    }
}

/**
 * Validate the payment form
 * @param {HTMLElement} formElement - The payment form element
 * @returns {boolean} Whether the form is valid
 */
function validatePaymentForm(formElement) {
    if (!formElement) return false;
    
    let isValid = true;
    let errorMessage = '';
    
    // Get form elements
    const amountInput = formElement.querySelector('#amount');
    const paymentMethodSelect = formElement.querySelector('#payment_method');
    const paymentDateInput = formElement.querySelector('#payment_date');
    const referenceInput = formElement.querySelector('#reference_no');
    const allocatedTotalElement = formElement.querySelector('#allocated_total');
    
    // Validate amount
    if (!amountInput || !amountInput.value || parseFloat(amountInput.value) <= 0) {
        errorMessage += 'Please enter a valid payment amount greater than zero.\n';
        isValid = false;
    }
    
    // Validate payment method
    if (!paymentMethodSelect || !paymentMethodSelect.value) {
        errorMessage += 'Please select a payment method.\n';
        isValid = false;
    }
    
    // Validate payment date
    if (!paymentDateInput || !paymentDateInput.value) {
        errorMessage += 'Please enter a payment date.\n';
        isValid = false;
    }
    
    // Validate reference number for certain payment methods
    if (paymentMethodSelect && ['bank_transfer', 'cheque', 'credit_card', 'upi'].includes(paymentMethodSelect.value)) {
        if (!referenceInput || !referenceInput.value) {
            errorMessage += 'Please enter a reference number for this payment method.\n';
            isValid = false;
        }
    }
    
    // Validate payment method specific fields
    if (paymentMethodSelect) {
        const selectedMethod = paymentMethodSelect.value;
        
        if (selectedMethod === 'cheque') {
            const chequeNumberInput = formElement.querySelector('#cheque_number');
            const chequeDateInput = formElement.querySelector('#cheque_date');
            const bankNameInput = formElement.querySelector('#bank_name');
            
            if (!chequeNumberInput || !chequeNumberInput.value) {
                errorMessage += 'Please enter a cheque number.\n';
                isValid = false;
            }
            
            if (!chequeDateInput || !chequeDateInput.value) {
                errorMessage += 'Please enter a cheque date.\n';
                isValid = false;
            }
            
            if (!bankNameInput || !bankNameInput.value) {
                errorMessage += 'Please enter the bank name.\n';
                isValid = false;
            }
        } else if (selectedMethod === 'credit_card') {
            const cardNumberInput = formElement.querySelector('#card_number_last4');
            const cardTypeInput = formElement.querySelector('#card_type');
            
            if (!cardNumberInput || !cardNumberInput.value) {
                errorMessage += 'Please enter the last 4 digits of the card.\n';
                isValid = false;
            }
            
            if (!cardTypeInput || !cardTypeInput.value) {
                errorMessage += 'Please select the card type.\n';
                isValid = false;
            }
        } else if (selectedMethod === 'upi') {
            const upiIdInput = formElement.querySelector('#upi_id');
            
            if (!upiIdInput || !upiIdInput.value) {
                errorMessage += 'Please enter the UPI ID.\n';
                isValid = false;
            }
        }
    }
    
    // Validate allocated amount matches payment amount
    if (amountInput && allocatedTotalElement) {
        const totalAmount = parseFloat(amountInput.value) || 0;
        const allocatedTotal = parseFloat(allocatedTotalElement.textContent) || 0;
        
        if (Math.abs(totalAmount - allocatedTotal) > 0.01) {
            errorMessage += 'The allocated amount must equal the payment amount.\n';
            isValid = false;
        }
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

// Export the component's public API
export { initPaymentForm };