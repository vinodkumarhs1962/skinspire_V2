/**
 * Supplier Management JavaScript
 * 
 * Handles all supplier-related functionality including:
 * - Supplier CRUD operations
 * - Purchase order management
 * - Supplier invoice processing
 * - Payment recording
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize supplier components
    initSupplierForm();
    initPurchaseOrderManagement();
    initSupplierInvoiceForm();
    initPaymentProcessing();
    initSupplierDataTables();
    initSupplierCharts();
});

/**
 * Initialize supplier form functionality
 */
function initSupplierForm() {
    const supplierForm = document.getElementById('supplierForm');
    
    if (supplierForm) {
        // Form validation
        supplierForm.addEventListener('submit', function(e) {
            if (!validateSupplierForm()) {
                e.preventDefault();
                return false;
            }
        });
        
        // Handle GST number validation
        const gstinInput = document.getElementById('gst_registration_number');
        if (gstinInput) {
            gstinInput.addEventListener('blur', function() {
                validateGSTIN(this.value);
            });
        }
        
        // Handle state code auto-population from GSTIN
        const stateCodeInput = document.getElementById('state_code');
        if (gstinInput && stateCodeInput) {
            gstinInput.addEventListener('input', function() {
                const gstin = this.value.trim();
                if (gstin.length >= 2) {
                    stateCodeInput.value = gstin.substring(0, 2);
                }
            });
        }
        
        // Handle tax type selection change
        const taxTypeSelect = document.getElementById('tax_type');
        if (taxTypeSelect) {
            taxTypeSelect.addEventListener('change', function() {
                toggleGSTFields(this.value);
            });
            
            // Initialize on page load
            toggleGSTFields(taxTypeSelect.value);
        }
        
        // Handle address fields
        setupAddressFields();
    }
}

/**
 * Toggle GST-related fields based on tax type
 */
function toggleGSTFields(taxType) {
    const gstFields = document.getElementById('gst_fields');
    if (gstFields) {
        if (taxType === 'Regular' || taxType === 'Composition') {
            gstFields.classList.remove('hidden');
            
            // Make GSTIN field required for Regular taxpayers
            const gstinInput = document.getElementById('gst_registration_number');
            if (gstinInput) {
                gstinInput.required = (taxType === 'Regular');
            }
        } else {
            gstFields.classList.add('hidden');
        }
    }
}

/**
 * Validate GSTIN (GST Identification Number)
 */
function validateGSTIN(gstin) {
    gstin = gstin.trim();
    const gstinField = document.getElementById('gst_registration_number');
    const gstinError = document.getElementById('gstin_error');
    
    // Skip validation if empty
    if (!gstin) {
        clearValidationState(gstinField, gstinError);
        return true;
    }
    
    // Basic format validation
    const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    if (!gstinRegex.test(gstin)) {
        setInvalidState(gstinField, gstinError, 'Invalid GSTIN format. It should be like 29ABCDE1234F1Z5.');
        return false;
    }
    
    // Additional validation (checksum, etc.) could be added here
    // For now, just do a basic check that the state code is valid
    const stateCode = parseInt(gstin.substring(0, 2), 10);
    if (stateCode < 1 || stateCode > 38) {
        setInvalidState(gstinField, gstinError, 'Invalid state code in GSTIN.');
        return false;
    }
    
    // GSTIN appears valid
    setValidState(gstinField, gstinError);
    return true;
}

/**
 * Setup address fields with proper formatting and validation
 */
function setupAddressFields() {
    // City autocomplete
    const cityInput = document.getElementById('city');
    if (cityInput && typeof window.citiesList !== 'undefined') {
        const cityDatalist = document.getElementById('cities_list');
        if (!cityDatalist) {
            // Create datalist if it doesn't exist
            const datalist = document.createElement('datalist');
            datalist.id = 'cities_list';
            
            // Add cities from the global cities list
            window.citiesList.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                datalist.appendChild(option);
            });
            
            document.body.appendChild(datalist);
            cityInput.setAttribute('list', 'cities_list');
        }
    }
    
    // Pincode validation
    const pincodeInput = document.getElementById('pincode');
    if (pincodeInput) {
        pincodeInput.addEventListener('blur', function() {
            validatePincode(this.value);
        });
    }
}

/**
 * Validate Indian Pincode
 */
function validatePincode(pincode) {
    pincode = pincode.trim();
    const pincodeField = document.getElementById('pincode');
    const pincodeError = document.getElementById('pincode_error');
    
    // Skip validation if empty
    if (!pincode) {
        clearValidationState(pincodeField, pincodeError);
        return true;
    }
    
    // Basic format validation
    const pincodeRegex = /^[1-9][0-9]{5}$/;
    if (!pincodeRegex.test(pincode)) {
        setInvalidState(pincodeField, pincodeError, 'Invalid pincode format. It should be a 6-digit number.');
        return false;
    }
    
    // Pincode appears valid
    setValidState(pincodeField, pincodeError);
    return true;
}

/**
 * Set field to valid state
 */
function setValidState(field, errorElement) {
    field.classList.remove('border-red-500', 'dark:border-red-500');
    field.classList.add('border-green-500', 'dark:border-green-500');
    
    if (errorElement) {
        errorElement.textContent = '';
        errorElement.classList.add('hidden');
    }
}

/**
 * Set field to invalid state with error message
 */
function setInvalidState(field, errorElement, message) {
    field.classList.remove('border-green-500', 'dark:border-green-500');
    field.classList.add('border-red-500', 'dark:border-red-500');
    
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');
    }
}

/**
 * Clear validation state
 */
function clearValidationState(field, errorElement) {
    field.classList.remove('border-red-500', 'dark:border-red-500', 'border-green-500', 'dark:border-green-500');
    
    if (errorElement) {
        errorElement.textContent = '';
        errorElement.classList.add('hidden');
    }
}

/**
 * Validate entire supplier form
 */
function validateSupplierForm() {
    let isValid = true;
    
    // Validate required fields
    const requiredFields = [
        { id: 'supplier_name', message: 'Supplier name is required' },
        { id: 'supplier_category', message: 'Supplier category is required' },
        { id: 'contact_person_name', message: 'Contact person name is required' },
        { id: 'email', message: 'Email is required' },
        { id: 'tax_type', message: 'Tax type is required' }
    ];
    
    requiredFields.forEach(field => {
        const element = document.getElementById(field.id);
        const errorElement = document.getElementById(`${field.id}_error`);
        
        if (element && !element.value.trim()) {
            setInvalidState(element, errorElement, field.message);
            isValid = false;
        } else if (element) {
            clearValidationState(element, errorElement);
        }
    });
    
    // Validate GSTIN if tax type is Regular or Composition
    const taxType = document.getElementById('tax_type').value;
    if (taxType === 'Regular' || taxType === 'Composition') {
        const gstinValid = validateGSTIN(document.getElementById('gst_registration_number').value);
        isValid = isValid && gstinValid;
    }
    
    // Validate pincode
    const pincodeValid = validatePincode(document.getElementById('pincode').value);
    isValid = isValid && pincodeValid;
    
    // Validate email format
    const email = document.getElementById('email').value.trim();
    const emailField = document.getElementById('email');
    const emailError = document.getElementById('email_error');
    
    if (email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            setInvalidState(emailField, emailError, 'Invalid email format');
            isValid = false;
        } else {
            clearValidationState(emailField, emailError);
        }
    }
    
    return isValid;
}

/**
 * Initialize purchase order management
 */
function initPurchaseOrderManagement() {
    const poForm = document.getElementById('purchaseOrderForm');
    
    if (poForm) {
        // Handle supplier selection
        const supplierSelect = document.getElementById('supplier_id');
        if (supplierSelect) {
            supplierSelect.addEventListener('change', function() {
                loadSupplierDetails(this.value);
            });
            
            // Load initial supplier details if a supplier is selected
            if (supplierSelect.value) {
                loadSupplierDetails(supplierSelect.value);
            }
        }
        
        // Handle add item button
        const addItemBtn = document.getElementById('addItemBtn');
        if (addItemBtn) {
            addItemBtn.addEventListener('click', function() {
                addNewItemRow();
            });
        }
        
        // Form validation
        poForm.addEventListener('submit', function(e) {
            if (!validatePurchaseOrderForm()) {
                e.preventDefault();
                return false;
            }
        });
        
        // Initialize item rows
        initializeItemRows();
        
        // Calculate totals on page load
        calculateTotals();
    }
    
    // Initialize PO list view functionality
    initPurchaseOrderListFunctions();
}

/**
 * Load supplier details via AJAX
 */
function loadSupplierDetails(supplierId) {
    if (!supplierId) return;
    
    // Show loading indicator
    const detailsContainer = document.getElementById('supplierDetails');
    if (detailsContainer) {
        detailsContainer.innerHTML = '<div class="text-center py-4"><div class="spinner"></div><p class="mt-2 text-gray-600 dark:text-gray-400">Loading supplier details...</p></div>';
        detailsContainer.classList.remove('hidden');
    }
    
    // Fetch supplier details via AJAX
    fetch(`/api/suppliers/${supplierId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update UI
                if (detailsContainer) {
                    detailsContainer.innerHTML = `
                        <div class="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                            <h3 class="font-semibold text-lg mb-2 dark:text-gray-200">${data.supplier.name}</h3>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Category: <span class="font-semibold dark:text-gray-300">${data.supplier.category}</span></p>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Contact: <span class="font-semibold dark:text-gray-300">${data.supplier.contact_person}</span></p>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Email: <span class="font-semibold dark:text-gray-300">${data.supplier.email}</span></p>
                                </div>
                                <div>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">GSTIN: <span class="font-semibold dark:text-gray-300">${data.supplier.gstin || 'N/A'}</span></p>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Tax Type: <span class="font-semibold dark:text-gray-300">${data.supplier.tax_type}</span></p>
                                    <p class="text-sm text-gray-600 dark:text-gray-400">Payment Terms: <span class="font-semibold dark:text-gray-300">${data.supplier.payment_terms || 'N/A'}</span></p>
                                </div>
                            </div>
                        </div>
                    `;
                }
                
                // Update form fields with supplier data
                if (data.supplier.state_code) {
                    document.getElementById('place_of_supply').value = data.supplier.state_code;
                }
            } else {
                if (detailsContainer) {
                    detailsContainer.innerHTML = `
                        <div class="bg-red-50 dark:bg-red-900 p-4 rounded-lg">
                            <p class="text-red-600 dark:text-red-400">${data.message || 'Failed to load supplier details'}</p>
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('Error fetching supplier details:', error);
            if (detailsContainer) {
                detailsContainer.innerHTML = `
                    <div class="bg-red-50 dark:bg-red-900 p-4 rounded-lg">
                        <p class="text-red-600 dark:text-red-400">Error loading supplier details. Please try again.</p>
                    </div>
                `;
            }
        });
}

/**
 * Initialize item rows in the PO form
 */
function initializeItemRows() {
    const itemTable = document.getElementById('poItems');
    if (!itemTable) return;
    
    // Set up event listeners for existing rows
    const itemRows = itemTable.querySelectorAll('tbody tr');
    itemRows.forEach(row => {
        setupItemRowEventListeners(row);
    });
}

/**
 * Add new item row to the purchase order form
 */
function addNewItemRow() {
    const itemTable = document.getElementById('poItems');
    if (!itemTable) return;
    
    const tbody = itemTable.querySelector('tbody');
    const rowCount = tbody.querySelectorAll('tr').length;
    const newRowIndex = rowCount;
    
    // Create new row with all necessary fields
    const newRow = document.createElement('tr');
    newRow.innerHTML = `
        <td class="p-2">
            <select name="items[${newRowIndex}][medicine_id]" class="medicine-select w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md">
                <option value="">Select Medicine</option>
                ${document.getElementById('medicine_template').innerHTML}
            </select>
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][quantity]" class="quantity-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="1" value="1">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][units_per_pack]" class="units-per-pack-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="1" value="1">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][pack_price]" class="pack-price-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="0" step="0.01" value="0.00">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][pack_mrp]" class="pack-mrp-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="0" step="0.01" value="0.00">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][gst_rate]" class="gst-rate-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="0" max="28" step="0.01" value="12.00">
        </td>
        <td class="p-2">
            <span class="subtotal"> Rs.0.00</span>
            <input type="hidden" name="items[${newRowIndex}][subtotal]" class="subtotal-input" value="0.00">
        </td>
        <td class="p-2">
            <span class="gst-amount"> Rs.0.00</span>
            <input type="hidden" name="items[${newRowIndex}][gst_amount]" class="gst-amount-input" value="0.00">
        </td>
        <td class="p-2">
            <span class="row-total"> Rs.0.00</span>
            <input type="hidden" name="items[${newRowIndex}][total]" class="row-total-input" value="0.00">
        </td>
        <td class="p-2">
            <button type="button" class="remove-row-btn text-red-600 hover:text-red-900">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
            </button>
        </td>
    `;
    
    tbody.appendChild(newRow);
    
    // Set up event listeners for the new row
    setupItemRowEventListeners(newRow);
    
    // Focus the medicine select in the new row
    const medicineSelect = newRow.querySelector('.medicine-select');
    if (medicineSelect) {
        medicineSelect.focus();
    }
}

/**
 * Set up event listeners for an item row
 */
function setupItemRowEventListeners(row) {
    // Medicine selection
    const medicineSelect = row.querySelector('.medicine-select');
    if (medicineSelect) {
        medicineSelect.addEventListener('change', function() {
            // Load medicine details if needed
            // This would normally fetch details like HSN code, default GST rate, etc.
            loadMedicineDetails(this.value, row);
            calculateRowTotal(row);
        });
    }
    
    // Quantity input
    const quantityInput = row.querySelector('.quantity-input');
    if (quantityInput) {
        quantityInput.addEventListener('input', function() {
            calculateRowTotal(row);
        });
    }
    
    // Units per pack input
    const unitsPerPackInput = row.querySelector('.units-per-pack-input');
    if (unitsPerPackInput) {
        unitsPerPackInput.addEventListener('input', function() {
            calculateRowTotal(row);
        });
    }
    
    // Pack price input
    const packPriceInput = row.querySelector('.pack-price-input');
    if (packPriceInput) {
        packPriceInput.addEventListener('input', function() {
            calculateRowTotal(row);
        });
    }
    
    // Pack MRP input
    const packMrpInput = row.querySelector('.pack-mrp-input');
    if (packMrpInput) {
        packMrpInput.addEventListener('input', function() {
            calculateRowTotal(row);
        });
    }
    
    // GST rate input
    const gstRateInput = row.querySelector('.gst-rate-input');
    if (gstRateInput) {
        gstRateInput.addEventListener('input', function() {
            calculateRowTotal(row);
        });
    }
    
    // Remove row button
    const removeBtn = row.querySelector('.remove-row-btn');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            row.remove();
            calculateTotals();
        });
    }
}

/**
 * Load medicine details via AJAX
 */
function loadMedicineDetails(medicineId, row) {
    if (!medicineId) return;
    
    // Fetch medicine details via AJAX
    fetch(`/api/inventory/medicine/${medicineId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update GST rate
                const gstRateInput = row.querySelector('.gst-rate-input');
                if (gstRateInput && data.medicine.gst_rate) {
                    gstRateInput.value = data.medicine.gst_rate;
                }
                
                // Update last purchase price if available
                const packPriceInput = row.querySelector('.pack-price-input');
                if (packPriceInput && data.medicine.last_purchase_price) {
                    packPriceInput.value = data.medicine.last_purchase_price;
                }
                
                // Update MRP if available
                const packMrpInput = row.querySelector('.pack-mrp-input');
                if (packMrpInput && data.medicine.mrp) {
                    packMrpInput.value = data.medicine.mrp;
                }
                
                // Update units per pack if available
                const unitsPerPackInput = row.querySelector('.units-per-pack-input');
                if (unitsPerPackInput && data.medicine.units_per_pack) {
                    unitsPerPackInput.value = data.medicine.units_per_pack;
                }
                
                // Recalculate totals
                calculateRowTotal(row);
            }
        })
        .catch(error => {
            console.error('Error fetching medicine details:', error);
        });
}

/**
 * Calculate row total for a purchase order item
 */
function calculateRowTotal(row) {
    // Get input values
    const quantity = parseFloat(row.querySelector('.quantity-input').value) || 0;
    const unitsPerPack = parseFloat(row.querySelector('.units-per-pack-input').value) || 1;
    const packPrice = parseFloat(row.querySelector('.pack-price-input').value) || 0;
    const gstRate = parseFloat(row.querySelector('.gst-rate-input').value) || 0;
    
    // Calculate subtotal
    const subtotal = quantity * packPrice;
    
    // Calculate GST amount
    const gstAmount = subtotal * (gstRate / 100);
    
    // Calculate row total
    const rowTotal = subtotal + gstAmount;
    
    // Update displayed values
    row.querySelector('.subtotal').textContent = ` Rs.${subtotal.toFixed(2)}`;
    row.querySelector('.subtotal-input').value = subtotal.toFixed(2);
    
    row.querySelector('.gst-amount').textContent = ` Rs.${gstAmount.toFixed(2)}`;
    row.querySelector('.gst-amount-input').value = gstAmount.toFixed(2);
    
    row.querySelector('.row-total').textContent = ` Rs.${rowTotal.toFixed(2)}`;
    row.querySelector('.row-total-input').value = rowTotal.toFixed(2);
    
    // Update overall totals
    calculateTotals();
}

/**
 * Calculate overall totals for the purchase order
 */
function calculateTotals() {
    const itemTable = document.getElementById('poItems');
    if (!itemTable) return;
    
    // Get all rows
    const rows = itemTable.querySelectorAll('tbody tr');
    
    // Initialize totals
    let subtotal = 0;
    let gstTotal = 0;
    let grandTotal = 0;
    
    // Sum up values from each row
    rows.forEach(row => {
        subtotal += parseFloat(row.querySelector('.subtotal-input').value) || 0;
        gstTotal += parseFloat(row.querySelector('.gst-amount-input').value) || 0;
        grandTotal += parseFloat(row.querySelector('.row-total-input').value) || 0;
    });
    
    // Update summary fields
    document.getElementById('subtotal_display').textContent = ` Rs.${subtotal.toFixed(2)}`;
    document.getElementById('subtotal').value = subtotal.toFixed(2);
    
    document.getElementById('gst_total_display').textContent = ` Rs.${gstTotal.toFixed(2)}`;
    document.getElementById('gst_total').value = gstTotal.toFixed(2);
    
    document.getElementById('grand_total_display').textContent = ` Rs.${grandTotal.toFixed(2)}`;
    document.getElementById('grand_total').value = grandTotal.toFixed(2);
}

/**
 * Validate the purchase order form
 */
function validatePurchaseOrderForm() {
    let isValid = true;
    let errorMessage = '';
    
    // Validate supplier
    const supplierId = document.getElementById('supplier_id').value;
    if (!supplierId) {
        errorMessage += 'Please select a supplier.\n';
        isValid = false;
    }
    
    // Validate expected delivery date
    const deliveryDate = document.getElementById('expected_delivery_date').value;
    if (!deliveryDate) {
        errorMessage += 'Please select an expected delivery date.\n';
        isValid = false;
    }
    
    // Validate at least one item is added
    const itemRows = document.querySelectorAll('#poItems tbody tr');
    if (itemRows.length === 0) {
        errorMessage += 'Please add at least one item to the purchase order.\n';
        isValid = false;
    }
    
    // Validate item details
    let hasInvalidItems = false;
    itemRows.forEach((row, index) => {
        const medicineId = row.querySelector('.medicine-select').value;
        const quantity = parseFloat(row.querySelector('.quantity-input').value) || 0;
        const packPrice = parseFloat(row.querySelector('.pack-price-input').value) || 0;
        
        if (!medicineId) {
            hasInvalidItems = true;
        }
        
        if (quantity <= 0) {
            hasInvalidItems = true;
        }
        
        if (packPrice <= 0) {
            hasInvalidItems = true;
        }
    });
    
    if (hasInvalidItems) {
        errorMessage += 'Please check all items. Each item must have a medicine selected, valid quantity, and price.\n';
        isValid = false;
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

/**
 * Initialize purchase order list view functions
 */
function initPurchaseOrderListFunctions() {
    // Handle PO status filter buttons
    const statusFilterBtns = document.querySelectorAll('.po-status-filter');
    if (statusFilterBtns.length) {
        statusFilterBtns.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Remove active class from all buttons
                statusFilterBtns.forEach(b => b.classList.remove('bg-blue-600', 'text-white'));
                
                // Add active class to clicked button
                this.classList.add('bg-blue-600', 'text-white');
                
                // Apply filter
                const status = this.getAttribute('data-status');
                filterPurchaseOrders(status);
            });
        });
        
        // Initialize with "all" filter
        document.querySelector('.po-status-filter[data-status="all"]').click();
    }
    
    // Handle PO delete confirmation
    const deleteButtons = document.querySelectorAll('.delete-po-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const poId = this.getAttribute('data-po-id');
            const poNumber = this.getAttribute('data-po-number');
            
            if (confirm(`Are you sure you want to delete Purchase Order #${poNumber}? This action cannot be undone.`)) {
                // Submit the delete form
                document.getElementById(`delete-po-form-${poId}`).submit();
            }
        });
    });
}

/**
 * Filter purchase orders by status
 */
function filterPurchaseOrders(status) {
    const poItems = document.querySelectorAll('.po-item');
    
    poItems.forEach(item => {
        if (status === 'all' || item.getAttribute('data-status') === status) {
            item.classList.remove('hidden');
        } else {
            item.classList.add('hidden');
        }
    });
}

/**
 * Initialize supplier invoice form
 */
function initSupplierInvoiceForm() {
    const invoiceForm = document.getElementById('supplierInvoiceForm');
    
    if (invoiceForm) {
        // Handle supplier selection
        const supplierSelect = document.getElementById('supplier_id');
        if (supplierSelect) {
            supplierSelect.addEventListener('change', function() {
                loadSupplierDetails(this.value);
            });
            
            // Load initial supplier details if a supplier is selected
            if (supplierSelect.value) {
                loadSupplierDetails(supplierSelect.value);
            }
        }
        
        // Handle purchase order selection
        const poSelect = document.getElementById('po_id');
        if (poSelect) {
            poSelect.addEventListener('change', function() {
                loadPurchaseOrderDetails(this.value);
            });
        }
        
        // Handle add item button
        const addItemBtn = document.getElementById('addItemBtn');
        if (addItemBtn) {
            addItemBtn.addEventListener('click', function() {
                addNewInvoiceItemRow();
            });
        }
        
        // Form validation
        invoiceForm.addEventListener('submit', function(e) {
            if (!validateSupplierInvoiceForm()) {
                e.preventDefault();
                return false;
            }
        });
        
        // Initialize item rows
        initializeInvoiceItemRows();
        
        // Calculate totals on page load
        calculateInvoiceTotals();
    }
}

/**
 * Load purchase order details via AJAX
 */
function loadPurchaseOrderDetails(poId) {
    if (!poId) return;
    
    // Show loading indicator
    const itemsContainer = document.getElementById('invoiceItemsContainer');
    if (itemsContainer) {
        itemsContainer.innerHTML = '<div class="text-center py-4"><div class="spinner"></div><p class="mt-2 text-gray-600 dark:text-gray-400">Loading purchase order details...</p></div>';
    }
    
    // Fetch PO details via AJAX
    fetch(`/api/suppliers/purchase-orders/${poId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update supplier ID if not already selected
                const supplierSelect = document.getElementById('supplier_id');
                if (supplierSelect && !supplierSelect.value) {
                    supplierSelect.value = data.po.supplier_id;
                    loadSupplierDetails(data.po.supplier_id);
                }
                
                // Clear existing items
                const itemsTable = document.getElementById('invoiceItems');
                if (itemsTable) {
                    const tbody = itemsTable.querySelector('tbody');
                    tbody.innerHTML = '';
                    
                    // Add items from PO
                    data.po.items.forEach((item, index) => {
                        addNewInvoiceItemRow(item);
                    });
                    
                    // Calculate totals
                    calculateInvoiceTotals();
                }
            } else {
                alert('Failed to load purchase order details: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error fetching purchase order details:', error);
            alert('Error loading purchase order details. Please try again.');
        });
}

/**
 * Initialize invoice item rows
 */
function initializeInvoiceItemRows() {
    const itemTable = document.getElementById('invoiceItems');
    if (!itemTable) return;
    
    // Set up event listeners for existing rows
    const itemRows = itemTable.querySelectorAll('tbody tr');
    itemRows.forEach(row => {
        setupInvoiceItemRowEventListeners(row);
    });
}

/**
 * Add new item row to the supplier invoice form
 */
function addNewInvoiceItemRow(itemData = null) {
    const itemTable = document.getElementById('invoiceItems');
    if (!itemTable) return;
    
    const tbody = itemTable.querySelector('tbody');
    const rowCount = tbody.querySelectorAll('tr').length;
    const newRowIndex = rowCount;
    
    // Create new row with all necessary fields
    const newRow = document.createElement('tr');
    newRow.innerHTML = `
        <td class="p-2">
            <select name="items[${newRowIndex}][medicine_id]" class="medicine-select w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md">
                <option value="">Select Medicine</option>
                ${document.getElementById('medicine_template').innerHTML}
            </select>
        </td>
        <td class="p-2">
            <input type="text" name="items[${newRowIndex}][batch_number]" class="batch-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md">
        </td>
        <td class="p-2">
            <input type="date" name="items[${newRowIndex}][expiry_date]" class="expiry-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][quantity]" class="quantity-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="1" value="1">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][units_per_pack]" class="units-per-pack-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="1" value="1">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][pack_price]" class="pack-price-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="0" step="0.01" value="0.00">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][pack_mrp]" class="pack-mrp-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="0" step="0.01" value="0.00">
        </td>
        <td class="p-2">
            <input type="number" name="items[${newRowIndex}][gst_rate]" class="gst-rate-input w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md" min="0" max="28" step="0.01" value="12.00">
        </td>
        <td class="p-2">
            <input type="checkbox" name="items[${newRowIndex}][is_free]" class="free-item-checkbox">
        </td>
        <td class="p-2">
            <span class="subtotal"> Rs.0.00</span>
            <input type="hidden" name="items[${newRowIndex}][subtotal]" class="subtotal-input" value="0.00">
        </td>
        <td class="p-2">
            <span class="gst-amount"> Rs.0.00</span>
            <input type="hidden" name="items[${newRowIndex}][gst_amount]" class="gst-amount-input" value="0.00">
        </td>
        <td class="p-2">
            <span class="row-total"> Rs.0.00</span>
            <input type="hidden" name="items[${newRowIndex}][total]" class="row-total-input" value="0.00">
        </td>
        <td class="p-2">
            <button type="button" class="remove-row-btn text-red-600 hover:text-red-900">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
            </button>
        </td>
    `;
    
    tbody.appendChild(newRow);
    
    // Set up event listeners for the new row
    setupInvoiceItemRowEventListeners(newRow);
    
    // If item data provided, populate the row
    if (itemData) {
        populateInvoiceItemRow(newRow, itemData);
    }
    
    // Focus the medicine select in the new row
    const medicineSelect = newRow.querySelector('.medicine-select');
    if (medicineSelect) {
        medicineSelect.focus();
    }
}

/**
 * Populate invoice item row with data
 */
function populateInvoiceItemRow(row, itemData) {
    // Set medicine ID
    const medicineSelect = row.querySelector('.medicine-select');
    if (medicineSelect) {
        medicineSelect.value = itemData.medicine_id;
    }
    
    // Set quantity
    const quantityInput = row.querySelector('.quantity-input');
    if (quantityInput) {
        quantityInput.value = itemData.quantity;
    }
    
    // Set units per pack
    const unitsPerPackInput = row.querySelector('.units-per-pack-input');
    if (unitsPerPackInput) {
        unitsPerPackInput.value = itemData.units_per_pack;
    }
    
    // Set pack price
    const packPriceInput = row.querySelector('.pack-price-input');
    if (packPriceInput) {
        packPriceInput.value = itemData.pack_price;
    }
    
    // Set pack MRP
    const packMrpInput = row.querySelector('.pack-mrp-input');
    if (packMrpInput) {
        packMrpInput.value = itemData.pack_mrp;
    }
    
    // Set GST rate
    const gstRateInput = row.querySelector('.gst-rate-input');
    if (gstRateInput) {
        gstRateInput.value = itemData.gst_rate;
    }
    
    // Calculate row total
    calculateInvoiceRowTotal(row);
}

/**
 * Set up event listeners for an invoice item row
 */
function setupInvoiceItemRowEventListeners(row) {
    // Medicine selection
    const medicineSelect = row.querySelector('.medicine-select');
    if (medicineSelect) {
        medicineSelect.addEventListener('change', function() {
            loadMedicineDetails(this.value, row);
            calculateInvoiceRowTotal(row);
        });
    }
    
    // Quantity input
    const quantityInput = row.querySelector('.quantity-input');
    if (quantityInput) {
        quantityInput.addEventListener('input', function() {
            calculateInvoiceRowTotal(row);
        });
    }
    
    // Units per pack input
    const unitsPerPackInput = row.querySelector('.units-per-pack-input');
    if (unitsPerPackInput) {
        unitsPerPackInput.addEventListener('input', function() {
            calculateInvoiceRowTotal(row);
        });
    }
    
    // Pack price input
    const packPriceInput = row.querySelector('.pack-price-input');
    if (packPriceInput) {
        packPriceInput.addEventListener('input', function() {
            calculateInvoiceRowTotal(row);
        });
    }
    
    // Pack MRP input
    const packMrpInput = row.querySelector('.pack-mrp-input');
    if (packMrpInput) {
        packMrpInput.addEventListener('input', function() {
            calculateInvoiceRowTotal(row);
        });
    }
    
    // GST rate input
    const gstRateInput = row.querySelector('.gst-rate-input');
    if (gstRateInput) {
        gstRateInput.addEventListener('input', function() {
            calculateInvoiceRowTotal(row);
        });
    }
    
    // Free item checkbox
    const freeItemCheckbox = row.querySelector('.free-item-checkbox');
    if (freeItemCheckbox) {
        freeItemCheckbox.addEventListener('change', function() {
            // Disable/enable price fields based on free item status
            const priceInputs = row.querySelectorAll('.pack-price-input, .pack-mrp-input');
            priceInputs.forEach(input => {
                input.disabled = this.checked;
                
                if (this.checked) {
                    input.dataset.oldValue = input.value;
                    input.value = '0.00';
                } else if (input.dataset.oldValue) {
                    input.value = input.dataset.oldValue;
                }
            });
            
            calculateInvoiceRowTotal(row);
        });
    }
    
    // Remove row button
    const removeBtn = row.querySelector('.remove-row-btn');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            row.remove();
            calculateInvoiceTotals();
        });
    }
}

/**
 * Calculate row total for an invoice item
 */
function calculateInvoiceRowTotal(row) {
    // Get input values
    const quantity = parseFloat(row.querySelector('.quantity-input').value) || 0;
    const unitsPerPack = parseFloat(row.querySelector('.units-per-pack-input').value) || 1;
    const packPrice = parseFloat(row.querySelector('.pack-price-input').value) || 0;
    const gstRate = parseFloat(row.querySelector('.gst-rate-input').value) || 0;
    const isFree = row.querySelector('.free-item-checkbox').checked;
    
    // If it's a free item, all values are zero
    if (isFree) {
        row.querySelector('.subtotal').textContent = ' Rs.0.00';
        row.querySelector('.subtotal-input').value = '0.00';
        
        row.querySelector('.gst-amount').textContent = ' Rs.0.00';
        row.querySelector('.gst-amount-input').value = '0.00';
        
        row.querySelector('.row-total').textContent = ' Rs.0.00';
        row.querySelector('.row-total-input').value = '0.00';
    } else {
        // Calculate subtotal
        const subtotal = quantity * packPrice;
        
        // Calculate GST amount
        const gstAmount = subtotal * (gstRate / 100);
        
        // Calculate row total
        const rowTotal = subtotal + gstAmount;
        
        // Update displayed values
        row.querySelector('.subtotal').textContent = ` Rs.${subtotal.toFixed(2)}`;
        row.querySelector('.subtotal-input').value = subtotal.toFixed(2);
        
        row.querySelector('.gst-amount').textContent = ` Rs.${gstAmount.toFixed(2)}`;
        row.querySelector('.gst-amount-input').value = gstAmount.toFixed(2);
        
        row.querySelector('.row-total').textContent = ` Rs.${rowTotal.toFixed(2)}`;
        row.querySelector('.row-total-input').value = rowTotal.toFixed(2);
    }
    
    // Update overall totals
    calculateInvoiceTotals();
}

/**
 * Calculate overall totals for the supplier invoice
 */
function calculateInvoiceTotals() {
    const itemTable = document.getElementById('invoiceItems');
    if (!itemTable) return;
    
    // Get all rows
    const rows = itemTable.querySelectorAll('tbody tr');
    
    // Initialize totals
    let subtotal = 0;
    let gstTotal = 0;
    let grandTotal = 0;
    
    // Sum up values from each row
    rows.forEach(row => {
        subtotal += parseFloat(row.querySelector('.subtotal-input').value) || 0;
        gstTotal += parseFloat(row.querySelector('.gst-amount-input').value) || 0;
        grandTotal += parseFloat(row.querySelector('.row-total-input').value) || 0;
    });
    
    // Update summary fields
    document.getElementById('subtotal_display').textContent = ` Rs.${subtotal.toFixed(2)}`;
    document.getElementById('subtotal').value = subtotal.toFixed(2);
    
    document.getElementById('gst_total_display').textContent = ` Rs.${gstTotal.toFixed(2)}`;
    document.getElementById('gst_total').value = gstTotal.toFixed(2);
    
    document.getElementById('grand_total_display').textContent = ` Rs.${grandTotal.toFixed(2)}`;
    document.getElementById('grand_total').value = grandTotal.toFixed(2);
}

/**
 * Validate the supplier invoice form
 */
function validateSupplierInvoiceForm() {
    let isValid = true;
    let errorMessage = '';
    
    // Validate supplier
    const supplierId = document.getElementById('supplier_id').value;
    if (!supplierId) {
        errorMessage += 'Please select a supplier.\n';
        isValid = false;
    }
    
    // Validate invoice number
    const invoiceNumber = document.getElementById('supplier_invoice_number').value;
    if (!invoiceNumber) {
        errorMessage += 'Please enter supplier invoice number.\n';
        isValid = false;
    }
    
    // Validate invoice date
    const invoiceDate = document.getElementById('invoice_date').value;
    if (!invoiceDate) {
        errorMessage += 'Please select invoice date.\n';
        isValid = false;
    }
    
    // Validate at least one item is added
    const itemRows = document.querySelectorAll('#invoiceItems tbody tr');
    if (itemRows.length === 0) {
        errorMessage += 'Please add at least one item to the invoice.\n';
        isValid = false;
    }
    
    // Validate item details
    let hasInvalidItems = false;
    itemRows.forEach((row, index) => {
        const medicineId = row.querySelector('.medicine-select').value;
        const quantity = parseFloat(row.querySelector('.quantity-input').value) || 0;
        const isFree = row.querySelector('.free-item-checkbox').checked;
        const batchNumber = row.querySelector('.batch-input').value;
        const expiryDate = row.querySelector('.expiry-input').value;
        
        if (!medicineId) {
            hasInvalidItems = true;
        }
        
        if (quantity <= 0) {
            hasInvalidItems = true;
        }
        
        if (!batchNumber) {
            hasInvalidItems = true;
        }
        
        if (!expiryDate) {
            hasInvalidItems = true;
        }
        
        if (!isFree) {
            const packPrice = parseFloat(row.querySelector('.pack-price-input').value) || 0;
            if (packPrice <= 0) {
                hasInvalidItems = true;
            }
        }
    });
    
    if (hasInvalidItems) {
        errorMessage += 'Please check all items. Each item must have a medicine selected, batch number, expiry date, valid quantity, and price (unless free item).\n';
        isValid = false;
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

/**
 * Initialize payment processing functionality
 */
function initPaymentProcessing() {
    const paymentForm = document.getElementById('supplierPaymentForm');
    
    if (paymentForm) {
        // Link to the payment form component
        import('/static/js/components/payment_form.js')
            .then(module => {
                module.initPaymentForm(paymentForm);
            })
            .catch(err => {
                console.error('Failed to load payment form component:', err);
            });
    }
    
    // Initialize payment history view
    initPaymentHistory();
}

/**
 * Initialize payment history functionality
 */
function initPaymentHistory() {
    // Set up payment details modal
    const paymentDetailButtons = document.querySelectorAll('.view-payment-details-btn');
    
    paymentDetailButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const paymentId = this.getAttribute('data-payment-id');
            showPaymentDetails(paymentId);
        });
    });
}

/**
 * Show payment details in modal
 */
function showPaymentDetails(paymentId) {
    const modal = document.getElementById('paymentDetailsModal');
    const content = document.getElementById('paymentDetailsContent');
    
    if (!modal || !content) return;
    
    // Show loading state
    content.innerHTML = '<div class="text-center py-6"><div class="spinner"></div><p class="mt-2">Loading payment details...</p></div>';
    modal.classList.remove('hidden');
    
    // Fetch payment details
    fetch(`/api/suppliers/payments/${paymentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const payment = data.payment;
                
                // Format the payment details
                content.innerHTML = `
                    <div class="bg-white dark:bg-gray-800 overflow-hidden shadow rounded-lg">
                        <div class="px-4 py-5 sm:px-6 border-b border-gray-200 dark:border-gray-700">
                            <h3 class="text-lg leading-6 font-medium text-gray-900 dark:text-gray-200">Payment Details</h3>
                            <p class="mt-1 max-w-2xl text-sm text-gray-500 dark:text-gray-400">Payment ID: ${payment.payment_id}</p>
                        </div>
                        <div class="border-b border-gray-200 dark:border-gray-700 px-4 py-5 sm:p-6">
                            <dl class="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-6">
                                <div>
                                    <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Supplier</dt>
                                    <dd class="mt-1 text-sm text-gray-900 dark:text-gray-200">${payment.supplier_name}</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Amount</dt>
                                    <dd class="mt-1 text-sm text-gray-900 dark:text-gray-200"> Rs.${parseFloat(payment.amount).toFixed(2)}</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Payment Date</dt>
                                    <dd class="mt-1 text-sm text-gray-900 dark:text-gray-200">${new Date(payment.payment_date).toLocaleDateString()}</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Payment Method</dt>
                                    <dd class="mt-1 text-sm text-gray-900 dark:text-gray-200">${payment.payment_method}</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Reference Number</dt>
                                    <dd class="mt-1 text-sm text-gray-900 dark:text-gray-200">${payment.reference_no || 'N/A'}</dd>
                                </div>
                                <div>
                                    <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Status</dt>
                                    <dd class="mt-1 text-sm text-gray-900 dark:text-gray-200">${payment.status}</dd>
                                </div>
                                <div class="col-span-2">
                                    <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Notes</dt>
                                    <dd class="mt-1 text-sm text-gray-900 dark:text-gray-200">${payment.notes || 'No notes available'}</dd>
                                </div>
                            </dl>
                        </div>
                        ${payment.invoices && payment.invoices.length > 0 ? `
                        <div class="px-4 py-5 sm:p-6">
                            <h4 class="text-md font-medium text-gray-900 dark:text-gray-200 mb-4">Applied to Invoices</h4>
                            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead class="bg-gray-50 dark:bg-gray-700">
                                    <tr>
                                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Invoice Number</th>
                                        <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Invoice Date</th>
                                        <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Amount Applied</th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white divide-y divide-gray-200 dark:bg-gray-800 dark:divide-gray-700">
                                    ${payment.invoices.map(invoice => `
                                    <tr>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${invoice.invoice_number}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${new Date(invoice.invoice_date).toLocaleDateString()}</td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-300"> Rs.${parseFloat(invoice.amount_applied).toFixed(2)}</td>
                                    </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        ` : ''}
                    </div>
                `;
            } else {
                content.innerHTML = `
                    <div class="bg-red-50 dark:bg-red-900 p-4 rounded-md">
                        <div class="flex">
                            <div class="flex-shrink-0">
                                <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                                </svg>
                            </div>
                            <div class="ml-3">
                                <h3 class="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
                                <div class="mt-2 text-sm text-red-700 dark:text-red-300">
                                    <p>${data.message || 'Failed to load payment details'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error fetching payment details:', error);
            content.innerHTML = `
                <div class="bg-red-50 dark:bg-red-900 p-4 rounded-md">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                            </svg>
                        </div>
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-red-800 dark:text-red-200">Error</h3>
                            <div class="mt-2 text-sm text-red-700 dark:text-red-300">
                                <p>An error occurred while loading payment details.</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    
    // Setup modal close button
    const closeBtn = document.getElementById('closePaymentDetailsModal');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.classList.add('hidden');
        });
    }
}

/**
 * Initialize DataTables for supplier tables
 */
function initSupplierDataTables() {
    // Only initialize if DataTables library is available
    if (typeof $.fn.DataTable !== 'undefined') {
        // Supplier list table
        const supplierTable = $('#supplierListTable');
        if (supplierTable.length) {
            supplierTable.DataTable({
                responsive: true,
                dom: '<"top"flp>rt<"bottom"ip>',
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search suppliers...",
                    lengthMenu: "Show _MENU_ items per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ items",
                },
                pageLength: 25,
                order: [[1, 'asc']], // Sort by supplier name by default
                columnDefs: [
                    { orderable: false, targets: [-1] } // Disable sorting on action column
                ]
            });
        }
        
        // Supplier invoice table
        const invoiceTable = $('#supplierInvoiceTable');
        if (invoiceTable.length) {
            invoiceTable.DataTable({
                responsive: true,
                dom: '<"top"flp>rt<"bottom"ip>',
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search invoices...",
                    lengthMenu: "Show _MENU_ entries per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                },
                pageLength: 20,
                order: [[1, 'desc']], // Sort by invoice date descending by default
            });
        }
        
        // Payment history table
        const paymentTable = $('#paymentHistoryTable');
        if (paymentTable.length) {
            paymentTable.DataTable({
                responsive: true,
                dom: '<"top"flp>rt<"bottom"ip>',
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search payments...",
                    lengthMenu: "Show _MENU_ entries per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                },
                pageLength: 20,
                order: [[1, 'desc']], // Sort by payment date descending by default
            });
        }
    }
}

/**
 * Initialize supplier-related charts
 */
function initSupplierCharts() {
    // Only initialize if Chart.js library is available
    if (typeof Chart !== 'undefined') {
        // Supplier Payment Distribution Chart
        const paymentCtx = document.getElementById('supplierPaymentChart');
        if (paymentCtx) {
            // Extract data from the HTML data attributes
            const labels = JSON.parse(paymentCtx.getAttribute('data-labels') || '[]');
            const values = JSON.parse(paymentCtx.getAttribute('data-values') || '[]');
            
            new Chart(paymentCtx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: [
                            '#4F46E5', '#3B82F6', '#0EA5E9', '#06B6D4', '#14B8A6',
                            '#10B981', '#22C55E', '#84CC16', '#EAB308', '#F59E0B'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}:  Rs.${value.toLocaleString()} (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Monthly Purchase Trend Chart
        const trendCtx = document.getElementById('purchaseTrendChart');
        if (trendCtx) {
            // Extract data from the HTML data attributes
            const labels = JSON.parse(trendCtx.getAttribute('data-labels') || '[]');
            const values = JSON.parse(trendCtx.getAttribute('data-values') || '[]');
            
            new Chart(trendCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Purchase Amount',
                        data: values,
                        borderColor: '#4F46E5',
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return ' Rs.' + value.toLocaleString();
                                },
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            grid: {
                                color: document.documentElement.classList.contains('dark') ? '#374151' : '#E5E7EB'
                            }
                        },
                        x: {
                            ticks: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            grid: {
                                color: document.documentElement.classList.contains('dark') ? '#374151' : '#E5E7EB'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw || 0;
                                    return `Purchase Amount:  Rs.${value.toLocaleString()}`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }
}

// Export functions that might be needed by other modules
export { 
    loadSupplierDetails, 
    validateSupplierForm 
};