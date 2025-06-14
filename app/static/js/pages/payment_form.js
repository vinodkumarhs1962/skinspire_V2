// static/js/components/payment_form.js

const PaymentForm = (function() {
    // Private properties
    let container;
    let invoiceId;
    let invoiceTotal;
    let balanceDue;
    let successCallback;
    
    // Initialize the payment form
    function init(containerElement, invoiceIdValue, total, balance, callback) {
        container = containerElement;
        invoiceId = invoiceIdValue;
        invoiceTotal = total;
        balanceDue = balance;
        successCallback = callback;
        
        render();
        bindEvents();
    }
    
    // Render the payment form
    function render() {
        container.innerHTML = `
            <div class="bg-white dark:bg-gray-800 p-4 rounded-md shadow">
                <h3 class="text-lg font-medium mb-4">Record Payment</h3>
                
                <div class="mb-4">
                    <div class="flex justify-between mb-2">
                        <span>Invoice Total:</span>
                        <span class="font-bold">${invoiceTotal.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between mb-2">
                        <span>Balance Due:</span>
                        <span class="font-bold text-red-500">${balanceDue.toFixed(2)}</span>
                    </div>
                </div>
                
                <form id="payment-form" class="space-y-4">
                    <input type="hidden" name="invoice_id" value="${invoiceId}">
                    <input type="hidden" name="payment_date" value="${new Date().toISOString().split('T')[0]}">
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <!-- Cash Payment -->
                        <div class="form-group">
                            <label for="cash-amount" class="block text-sm font-medium mb-1">Cash Amount</label>
                            <input type="number" id="cash-amount" name="cash_amount" value="0.00" min="0" step="0.01"
                                   class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 payment-amount">
                        </div>
                        
                        <!-- Credit Card Payment -->
                        <div class="form-group">
                            <label for="credit-card-amount" class="block text-sm font-medium mb-1">Credit Card Amount</label>
                            <input type="number" id="credit-card-amount" name="credit_card_amount" value="0.00" min="0" step="0.01"
                                   class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 payment-amount">
                        </div>
                        
                        <!-- Debit Card Payment -->
                        <div class="form-group">
                            <label for="debit-card-amount" class="block text-sm font-medium mb-1">Debit Card Amount</label>
                            <input type="number" id="debit-card-amount" name="debit_card_amount" value="0.00" min="0" step="0.01"
                                   class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 payment-amount">
                        </div>
                        
                        <!-- UPI Payment -->
                        <div class="form-group">
                            <label for="upi-amount" class="block text-sm font-medium mb-1">UPI Amount</label>
                            <input type="number" id="upi-amount" name="upi_amount" value="0.00" min="0" step="0.01"
                                   class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 payment-amount">
                        </div>
                    </div>
                    
                    <!-- Card details (conditional) -->
                    <div id="card-details" class="hidden">
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="form-group">
                                <label for="card-number-last4" class="block text-sm font-medium mb-1">Card Number (Last 4 digits)</label>
                                <input type="text" id="card-number-last4" name="card_number_last4" maxlength="4" pattern="[0-9]{4}"
                                       class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600">
                            </div>
                            
                            <div class="form-group">
                                <label for="card-type" class="block text-sm font-medium mb-1">Card Type</label>
                                <select id="card-type" name="card_type" class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600">
                                    <option value="">Select type</option>
                                    <option value="Visa">Visa</option>
                                    <option value="MasterCard">MasterCard</option>
                                    <option value="RuPay">RuPay</option>
                                    <option value="Amex">American Express</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    
                    <!-- UPI details (conditional) -->
                    <div id="upi-details" class="hidden">
                        <div class="form-group">
                            <label for="upi-id" class="block text-sm font-medium mb-1">UPI ID</label>
                            <input type="text" id="upi-id" name="upi_id"
                                   class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600">
                        </div>
                    </div>
                    
                    <!-- Reference number -->
                    <div class="form-group">
                        <label for="reference-number" class="block text-sm font-medium mb-1">Reference Number</label>
                        <input type="text" id="reference-number" name="reference_number"
                               class="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600">
                    </div>
                    
                    <!-- Total payment amount calculation -->
                    <div class="pt-4 border-t dark:border-gray-700">
                        <div class="flex justify-between mb-2">
                            <span class="font-medium">Total Payment Amount:</span>
                            <span id="total-payment-amount" class="font-bold">0.00</span>
                            <input type="hidden" id="total-amount" name="total_amount" value="0.00">
                        </div>
                        
                        <div class="flex justify-between mb-2 text-sm" id="remaining-amount-container">
                            <span>Remaining Balance:</span>
                            <span id="remaining-amount" class="font-medium text-red-500">${balanceDue.toFixed(2)}</span>
                        </div>
                    </div>
                    
                    <div class="pt-4">
                        <button type="submit" id="submit-payment" class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
                            Record Payment
                        </button>
                        <button type="button" id="cancel-payment" class="px-4 py-2 ml-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        `;
    }
    
    // Bind events to form elements
    function bindEvents() {
        const paymentForm = document.getElementById('payment-form');
        const cancelButton = document.getElementById('cancel-payment');
        const paymentAmountInputs = document.querySelectorAll('.payment-amount');
        const creditCardAmountInput = document.getElementById('credit-card-amount');
        const debitCardAmountInput = document.getElementById('debit-card-amount');
        const upiAmountInput = document.getElementById('upi-amount');
        const cardDetailsContainer = document.getElementById('card-details');
        const upiDetailsContainer = document.getElementById('upi-details');
        
        // Update total when any payment amount changes
        paymentAmountInputs.forEach(input => {
            input.addEventListener('input', updateTotalPayment);
        });
        
        // Show/hide card details based on card payment amounts
        [creditCardAmountInput, debitCardAmountInput].forEach(input => {
            input.addEventListener('input', function() {
                const cardAmount = parseFloat(creditCardAmountInput.value) || 0;
                const debitAmount = parseFloat(debitCardAmountInput.value) || 0;
                
                if (cardAmount > 0 || debitAmount > 0) {
                    cardDetailsContainer.classList.remove('hidden');
                } else {
                    cardDetailsContainer.classList.add('hidden');
                }
            });
        });
        
        // Show/hide UPI details based on UPI payment amount
        upiAmountInput.addEventListener('input', function() {
            const upiAmount = parseFloat(upiAmountInput.value) || 0;
            
            if (upiAmount > 0) {
                upiDetailsContainer.classList.remove('hidden');
            } else {
                upiDetailsContainer.classList.add('hidden');
            }
        });
        
        // Form submission
        paymentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            processPayment();
        });
        
        // Cancel button
        cancelButton.addEventListener('click', function() {
            container.innerHTML = '';
        });
        
        // Initialize total calculation
        updateTotalPayment();
    }
    
    // Update total payment amount
    function updateTotalPayment() {
        const cashAmount = parseFloat(document.getElementById('cash-amount').value) || 0;
        const creditCardAmount = parseFloat(document.getElementById('credit-card-amount').value) || 0;
        const debitCardAmount = parseFloat(document.getElementById('debit-card-amount').value) || 0;
        const upiAmount = parseFloat(document.getElementById('upi-amount').value) || 0;
        
        const totalPayment = cashAmount + creditCardAmount + debitCardAmount + upiAmount;
        const remainingAmount = balanceDue - totalPayment;
        
        // Update UI
        document.getElementById('total-payment-amount').textContent = totalPayment.toFixed(2);
        document.getElementById('total-amount').value = totalPayment.toFixed(2);
        
        const remainingAmountElement = document.getElementById('remaining-amount');
        if (remainingAmountElement) {
            remainingAmountElement.textContent = remainingAmount.toFixed(2);
            
            // Change color based on remaining amount
            if (remainingAmount < 0) {
                remainingAmountElement.classList.remove('text-red-500');
                remainingAmountElement.classList.add('text-red-700');
                showValidationError('Payment amount exceeds balance due');
            } else if (remainingAmount === 0) {
                remainingAmountElement.classList.remove('text-red-500', 'text-red-700');
                remainingAmountElement.classList.add('text-green-500');
                clearValidationErrors();
            } else {
                remainingAmountElement.classList.remove('text-green-500', 'text-red-700');
                remainingAmountElement.classList.add('text-red-500');
                clearValidationErrors();
            }
        }
        
        // Enable/disable submit button based on payment amount
        const submitButton = document.getElementById('submit-payment');
        if (submitButton) {
            submitButton.disabled = totalPayment <= 0 || totalPayment > balanceDue;
        }
    }
    
    // Process the payment
    function processPayment() {
        const form = document.getElementById('payment-form');
        
        // Create FormData object
        const formData = new FormData(form);
        
        // Convert to JSON object
        const paymentData = {};
        formData.forEach((value, key) => {
            // Convert numeric values
            if (!isNaN(value) && value !== '') {
                paymentData[key] = parseFloat(value);
            } else {
                paymentData[key] = value;
            }
        });
        
        // Check required fields based on payment methods
        if (!validatePayment(paymentData)) {
            return;
        }
        
        // Submit payment via AJAX
        submitPayment(paymentData);
    }
    
    // Validate payment data based on method
    function validatePayment(data) {
        clearValidationErrors();
        
        // Check if total payment amount is valid
        if (data.total_amount <= 0) {
            showValidationError('Payment amount must be greater than zero');
            return false;
        }
        
        if (data.total_amount > balanceDue) {
            showValidationError('Payment amount exceeds balance due');
            return false;
        }
        
        // Validate credit/debit card details if used
        if ((data.credit_card_amount > 0 || data.debit_card_amount > 0)) {
            if (!data.card_number_last4 || data.card_number_last4.length !== 4 || isNaN(data.card_number_last4)) {
                showValidationError('Please enter the last 4 digits of the card number');
                return false;
            }
            
            if (!data.card_type) {
                showValidationError('Please select the card type');
                return false;
            }
        }
        
        // Validate UPI details if used
        if (data.upi_amount > 0 && !data.upi_id) {
            showValidationError('Please enter the UPI ID');
            return false;
        }
        
        return true;
    }
    
    // Show validation error message
    function showValidationError(message) {
        clearValidationErrors();
        
        const errorDiv = document.createElement('div');
        errorDiv.id = 'payment-validation-error';
        errorDiv.className = 'bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4';
        errorDiv.textContent = message;
        
        const form = document.getElementById('payment-form');
        form.insertBefore(errorDiv, form.firstChild);
    }
    
    // Clear validation errors
    function clearValidationErrors() {
        const existingError = document.getElementById('payment-validation-error');
        if (existingError) {
            existingError.remove();
        }
    }
    
    // Submit payment to server
    function submitPayment(paymentData) {
        const submitButton = document.getElementById('submit-payment');
        submitButton.disabled = true;
        submitButton.textContent = 'Processing...';
        
        fetch('/api/record-payment', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(paymentData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (successCallback) {
                    successCallback(data);
                }
            } else {
                showValidationError(data.message || 'Failed to process payment');
                submitButton.disabled = false;
                submitButton.textContent = 'Record Payment';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showValidationError('An error occurred while processing the payment');
            submitButton.disabled = false;
            submitButton.textContent = 'Record Payment';
        });
    }
    
    // Get CSRF token from meta tag
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
    
    // Public API
    return {
        init: init
    };
})();