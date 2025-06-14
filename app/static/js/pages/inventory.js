/**
 * Inventory Management JavaScript
 * 
 * Handles all inventory-related functionality including:
 * - Stock management
 * - Batch tracking
 * - Stock movements
 * - Inventory adjustments
 * - Low stock alerts
 * - Expiry tracking
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize inventory components
    initInventoryFilters();
    initBatchManagement();
    initStockAdjustment();
    initExpiryTracking();
    initLowStockAlerts();
    initDataTables();
    initInventoryCharts();
    
    // Handle inventory-specific form submissions
    setupFormSubmissions();
});

/**
 * Initialize inventory filter functionality
 */
function initInventoryFilters() {
    const filterForm = document.getElementById('inventoryFilterForm');
    const resetButton = document.getElementById('resetFilters');
    
    if (filterForm) {
        // Handle filter changes to update UI dynamically
        const filterInputs = filterForm.querySelectorAll('select, input');
        filterInputs.forEach(input => {
            input.addEventListener('change', function() {
                // For select elements with multiple selection
                if (this.tagName === 'SELECT' && this.multiple) {
                    const selectedOptions = Array.from(this.selectedOptions).map(option => option.value);
                    updateFilterPills(this.name, selectedOptions);
                } else {
                    updateFilterPills(this.name, this.value);
                }
            });
        });
        
        // Apply filters on form submission
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            applyInventoryFilters();
        });
    }
    
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            resetInventoryFilters();
        });
    }
    
    // Initialize any filter pills from URL parameters
    initFilterPillsFromUrl();
}

/**
 * Updates the filter pills display based on selected filters
 */
function updateFilterPills(filterName, filterValue) {
    const pillsContainer = document.getElementById('filterPills');
    if (!pillsContainer) return;
    
    // Remove existing pill for this filter
    const existingPill = document.querySelector(`[data-filter-name="${filterName}"]`);
    if (existingPill) {
        existingPill.remove();
    }
    
    // Don't add an empty pill
    if (!filterValue || (Array.isArray(filterValue) && filterValue.length === 0)) {
        return;
    }
    
    // Create new pill
    const pill = document.createElement('span');
    pill.classList.add('inline-flex', 'items-center', 'px-2.5', 'py-0.5', 'rounded-full', 'text-xs', 
        'font-medium', 'bg-blue-100', 'text-blue-800', 'dark:bg-blue-900', 'dark:text-blue-300', 'mr-2', 'mb-2');
    pill.setAttribute('data-filter-name', filterName);
    
    // Get readable filter name
    const filterLabel = document.querySelector(`label[for="${filterName}"]`)?.textContent || 
        document.querySelector(`[name="${filterName}"]`)?.getAttribute('data-label') || 
        filterName;
    
    // Get readable filter value
    let displayValue;
    if (Array.isArray(filterValue)) {
        displayValue = filterValue.join(', ');
    } else {
        const selectElement = document.querySelector(`select[name="${filterName}"]`);
        if (selectElement) {
            displayValue = selectElement.querySelector(`option[value="${filterValue}"]`)?.textContent || filterValue;
        } else {
            displayValue = filterValue;
        }
    }
    
    pill.innerHTML = `
        ${filterLabel}: ${displayValue}
        <button type="button" class="ml-1 inline-flex items-center justify-center w-4 h-4 text-blue-400 hover:text-blue-500 dark:text-blue-300 dark:hover:text-blue-200">
            <span class="sr-only">Remove filter</span>
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
        </button>
    `;
    
    // Add remove filter functionality
    pill.querySelector('button').addEventListener('click', function() {
        // Clear the form field
        const formField = document.querySelector(`[name="${filterName}"]`);
        if (formField) {
            if (formField.tagName === 'SELECT' && formField.multiple) {
                Array.from(formField.options).forEach(option => option.selected = false);
            } else {
                formField.value = '';
            }
        }
        
        // Remove the pill
        pill.remove();
        
        // Apply filters if auto-submit enabled
        if (document.getElementById('autoSubmit')?.checked) {
            applyInventoryFilters();
        }
    });
    
    pillsContainer.appendChild(pill);
    
    // Apply filters if auto-submit enabled
    if (document.getElementById('autoSubmit')?.checked) {
        applyInventoryFilters();
    }
}

/**
 * Initialize filter pills based on URL parameters
 */
function initFilterPillsFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    
    urlParams.forEach((value, key) => {
        if (value && document.querySelector(`[name="${key}"]`)) {
            // Handle multiple values for the same key (for multi-select fields)
            if (document.querySelector(`[name="${key}"][multiple]`)) {
                const values = urlParams.getAll(key);
                updateFilterPills(key, values);
                
                // Set the form field values
                const selectElement = document.querySelector(`[name="${key}"]`);
                if (selectElement) {
                    Array.from(selectElement.options).forEach(option => {
                        option.selected = values.includes(option.value);
                    });
                }
            } else {
                updateFilterPills(key, value);
                
                // Set the form field value
                const formField = document.querySelector(`[name="${key}"]`);
                if (formField) {
                    formField.value = value;
                }
            }
        }
    });
}

/**
 * Apply inventory filters by submitting the form
 */
function applyInventoryFilters() {
    const filterForm = document.getElementById('inventoryFilterForm');
    if (filterForm) {
        const formData = new FormData(filterForm);
        const params = new URLSearchParams(formData);
        
        // Remove empty values
        for (const [key, value] of params.entries()) {
            if (!value) {
                params.delete(key);
            }
        }
        
        // Redirect to the filtered URL
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    }
}

/**
 * Reset all inventory filters
 */
function resetInventoryFilters() {
    const filterForm = document.getElementById('inventoryFilterForm');
    if (filterForm) {
        filterForm.reset();
        
        // Clear all filter pills
        const pillsContainer = document.getElementById('filterPills');
        if (pillsContainer) {
            pillsContainer.innerHTML = '';
        }
        
        // Redirect to the base URL without params
        window.location.href = window.location.pathname;
    }
}

/**
 * Initialize batch management functionality
 */
function initBatchManagement() {
    // Set up batch expiry warnings
    const expiryWarningThreshold = 90; // Days before expiry to start warning
    const batchExpiryElements = document.querySelectorAll('[data-expiry-date]');
    
    batchExpiryElements.forEach(element => {
        const expiryDate = new Date(element.getAttribute('data-expiry-date'));
        const today = new Date();
        const daysRemaining = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
        
        if (daysRemaining <= 0) {
            // Expired
            element.classList.add('text-red-600', 'dark:text-red-400', 'font-bold');
        } else if (daysRemaining <= expiryWarningThreshold) {
            // Expiring soon
            element.classList.add('text-yellow-600', 'dark:text-yellow-400');
            
            if (daysRemaining <= 30) {
                element.classList.add('font-semibold');
            }
        }
    });
    
    // Set up batch selection for inventory operations
    setupBatchSelector();
}

/**
 * Initialize stock adjustment functionality
 */
function initStockAdjustment() {
    const adjustmentForm = document.getElementById('stockAdjustmentForm');
    
    if (adjustmentForm) {
        adjustmentForm.addEventListener('submit', function(e) {
            // Validate before submission
            if (!validateStockAdjustment()) {
                e.preventDefault();
                return false;
            }
            
            // Confirm large adjustments
            const quantity = parseFloat(document.getElementById('adjustment_quantity').value || 0);
            const direction = document.querySelector('input[name="adjustment_type"]:checked').value;
            const medicineName = document.getElementById('medicine_name').value;
            
            if (Math.abs(quantity) > 10) {
                if (!confirm(`You are about to ${direction === 'addition' ? 'add' : 'remove'} ${quantity} units of ${medicineName}. Are you sure?`)) {
                    e.preventDefault();
                    return false;
                }
            }
        });
        
        // Update the form based on selected medicine
        const medicineSelect = document.getElementById('medicine_id');
        if (medicineSelect) {
            medicineSelect.addEventListener('change', function() {
                updateMedicineDetails(this.value);
            });
        }
    }
    
    // Initialize radio button behavior for adjustment type
    const adjustmentTypeRadios = document.querySelectorAll('input[name="adjustment_type"]');
    adjustmentTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const quantityLabel = document.querySelector('label[for="adjustment_quantity"]');
            if (quantityLabel) {
                quantityLabel.textContent = this.value === 'addition' ? 'Quantity to Add:' : 'Quantity to Remove:';
            }
        });
    });
}

/**
 * Validate stock adjustment form
 */
function validateStockAdjustment() {
    const medicineId = document.getElementById('medicine_id').value;
    const quantity = parseFloat(document.getElementById('adjustment_quantity').value || 0);
    const reason = document.getElementById('adjustment_reason').value;
    
    let isValid = true;
    let errorMessage = '';
    
    if (!medicineId) {
        errorMessage += 'Please select a medicine.\n';
        isValid = false;
    }
    
    if (isNaN(quantity) || quantity <= 0) {
        errorMessage += 'Please enter a valid quantity (must be greater than 0).\n';
        isValid = false;
    }
    
    if (!reason || reason.trim().length < 5) {
        errorMessage += 'Please provide a more detailed reason for this adjustment.\n';
        isValid = false;
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

/**
 * Update medicine details in the adjustment form
 */
function updateMedicineDetails(medicineId) {
    if (!medicineId) return;
    
    // Show loading indicator
    const detailsContainer = document.getElementById('medicineDetails');
    if (detailsContainer) {
        detailsContainer.innerHTML = '<div class="text-center py-4"><div class="spinner"></div><p class="mt-2 text-gray-600 dark:text-gray-400">Loading medicine details...</p></div>';
        detailsContainer.classList.remove('hidden');
    }
    
    // Fetch medicine details via AJAX
    fetch(`/api/inventory/medicine/${medicineId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update medicine name hidden field
                document.getElementById('medicine_name').value = data.medicine.name;
                
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
                
                // Enable the batch selector if the medicine has batches
                const batchSelector = document.getElementById('batch_selector');
                if (batchSelector && data.medicine.batches && data.medicine.batches.length > 0) {
                    batchSelector.innerHTML = '';
                    
                    data.medicine.batches.forEach(batch => {
                        const option = document.createElement('option');
                        option.value = batch.batch;
                        option.textContent = `${batch.batch} (Exp: ${batch.expiry}, Stock: ${batch.quantity})`;
                        option.setAttribute('data-expiry', batch.expiry);
                        option.setAttribute('data-quantity', batch.quantity);
                        batchSelector.appendChild(option);
                    });
                    
                    document.getElementById('batchSelectorContainer').classList.remove('hidden');
                } else if (batchSelector) {
                    document.getElementById('batchSelectorContainer').classList.add('hidden');
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
 * Initialize expiry tracking functionality
 */
function initExpiryTracking() {
    // Set up expiry date highlighting and sorting
    const expiryTable = document.getElementById('expiryTable');
    if (expiryTable) {
        // Set up sorting
        const headers = expiryTable.querySelectorAll('th[data-sort]');
        headers.forEach(header => {
            header.addEventListener('click', function() {
                const sortKey = this.getAttribute('data-sort');
                const sortDirection = this.getAttribute('data-sort-direction') === 'asc' ? 'desc' : 'asc';
                
                // Update headers
                headers.forEach(h => {
                    h.setAttribute('data-sort-direction', h === this ? sortDirection : '');
                    h.querySelectorAll('.sort-icon').forEach(icon => icon.classList.add('hidden'));
                    
                    if (h === this) {
                        h.querySelector(`.sort-icon-${sortDirection}`).classList.remove('hidden');
                    }
                });
                
                // Sort the table
                sortExpiryTable(sortKey, sortDirection);
            });
        });
        
        // Initialize default sort - by days to expiry
        document.querySelector('th[data-sort="daysToExpiry"]').click();
    }
}

/**
 * Sort the expiry tracking table
 */
function sortExpiryTable(sortKey, direction) {
    const table = document.getElementById('expiryTable');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Sort the rows
    rows.sort((a, b) => {
        let aValue = a.querySelector(`[data-${sortKey}]`).getAttribute(`data-${sortKey}`);
        let bValue = b.querySelector(`[data-${sortKey}]`).getAttribute(`data-${sortKey}`);
        
        // Convert to appropriate types for comparison
        if (sortKey === 'daysToExpiry' || sortKey === 'quantity') {
            aValue = parseFloat(aValue);
            bValue = parseFloat(bValue);
        }
        
        // Compare
        if (aValue < bValue) {
            return direction === 'asc' ? -1 : 1;
        } else if (aValue > bValue) {
            return direction === 'asc' ? 1 : -1;
        }
        return 0;
    });
    
    // Re-add rows in sorted order
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Initialize low stock alerts
 */
function initLowStockAlerts() {
    const lowStockTable = document.getElementById('lowStockTable');
    if (lowStockTable) {
        // Set up sorting
        const headers = lowStockTable.querySelectorAll('th[data-sort]');
        headers.forEach(header => {
            header.addEventListener('click', function() {
                const sortKey = this.getAttribute('data-sort');
                const sortDirection = this.getAttribute('data-sort-direction') === 'asc' ? 'desc' : 'asc';
                
                // Update headers
                headers.forEach(h => {
                    h.setAttribute('data-sort-direction', h === this ? sortDirection : '');
                    h.querySelectorAll('.sort-icon').forEach(icon => icon.classList.add('hidden'));
                    
                    if (h === this) {
                        h.querySelector(`.sort-icon-${sortDirection}`).classList.remove('hidden');
                    }
                });
                
                // Sort the table
                sortLowStockTable(sortKey, sortDirection);
            });
        });
        
        // Initialize default sort - by stock percentage
        document.querySelector('th[data-sort="stockPercentage"]').click();
    }
}

/**
 * Sort the low stock table
 */
function sortLowStockTable(sortKey, direction) {
    const table = document.getElementById('lowStockTable');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Sort the rows
    rows.sort((a, b) => {
        let aValue = a.querySelector(`[data-${sortKey}]`).getAttribute(`data-${sortKey}`);
        let bValue = b.querySelector(`[data-${sortKey}]`).getAttribute(`data-${sortKey}`);
        
        // Convert to appropriate types for comparison
        if (['currentStock', 'safetyStock', 'stockPercentage'].includes(sortKey)) {
            aValue = parseFloat(aValue);
            bValue = parseFloat(bValue);
        }
        
        // Compare
        if (aValue < bValue) {
            return direction === 'asc' ? -1 : 1;
        } else if (aValue > bValue) {
            return direction === 'asc' ? 1 : -1;
        }
        return 0;
    });
    
    // Re-add rows in sorted order
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Initialize DataTables for inventory tables
 */
function initDataTables() {
    // Only initialize if DataTables library is available
    if (typeof $.fn.DataTable !== 'undefined') {
        // Stock list table
        const stockTable = $('#stockListTable');
        if (stockTable.length) {
            stockTable.DataTable({
                responsive: true,
                dom: '<"top"flp>rt<"bottom"ip>',
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search inventory...",
                    lengthMenu: "Show _MENU_ items per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ items",
                },
                pageLength: 25,
                order: [[2, 'asc']], // Sort by medicine name by default
                columnDefs: [
                    { orderable: false, targets: [0, -1] } // Disable sorting on checkbox and action columns
                ]
            });
        }
        
        // Stock movement table
        const movementTable = $('#stockMovementTable');
        if (movementTable.length) {
            movementTable.DataTable({
                responsive: true,
                dom: '<"top"flp>rt<"bottom"ip>',
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search movements...",
                    lengthMenu: "Show _MENU_ entries per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                },
                pageLength: 20,
                order: [[1, 'desc']], // Sort by date descending by default
            });
        }
    }
}

/**
 * Initialize inventory-related charts
 */
function initInventoryCharts() {
    // Only initialize if Chart.js library is available
    if (typeof Chart !== 'undefined') {
        // Stock Category Distribution Chart
        const categoryCtx = document.getElementById('categoryDistributionChart');
        if (categoryCtx) {
            // Extract data from the HTML data attributes
            const labels = JSON.parse(categoryCtx.getAttribute('data-labels') || '[]');
            const values = JSON.parse(categoryCtx.getAttribute('data-values') || '[]');
            
            new Chart(categoryCtx, {
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
                                    return `${label}: ${value} items (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Stock Value Chart
        const valueCtx = document.getElementById('stockValueChart');
        if (valueCtx) {
            // Extract data from the HTML data attributes
            const labels = JSON.parse(valueCtx.getAttribute('data-labels') || '[]');
            const values = JSON.parse(valueCtx.getAttribute('data-values') || '[]');
            
            new Chart(valueCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Stock Value',
                        data: values,
                        backgroundColor: '#4F46E5',
                        borderColor: '#4338CA',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151',
                                callback: function(value) {
                                    return ' Rs.' + value.toLocaleString();
                                }
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
                                    return `Stock Value:  Rs.${value.toLocaleString()}`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Stock Movement Trend Chart
        const trendCtx = document.getElementById('stockMovementTrendChart');
        if (trendCtx) {
            // Extract data from the HTML data attributes
            const labels = JSON.parse(trendCtx.getAttribute('data-labels') || '[]');
            const inflow = JSON.parse(trendCtx.getAttribute('data-inflow') || '[]');
            const outflow = JSON.parse(trendCtx.getAttribute('data-outflow') || '[]');
            
            new Chart(trendCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Stock Inflow',
                            data: inflow,
                            borderColor: '#10B981',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            fill: true
                        },
                        {
                            label: 'Stock Outflow',
                            data: outflow,
                            borderColor: '#EF4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
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
                            labels: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            }
                        }
                    }
                }
            });
        }
    }
}

/**
 * Set up the batch selector component
 */
function setupBatchSelector() {
    // Load the batch selector component via dynamic import
    import('/static/js/components/batch_selector.js')
        .then(module => {
            // Initialize batch selectors on the page
            const batchSelectors = document.querySelectorAll('.batch-selector');
            batchSelectors.forEach(selector => {
                module.initBatchSelector(selector);
            });
        })
        .catch(err => {
            console.error('Failed to load batch selector component:', err);
        });
}

/**
 * Set up form submissions with validation and confirmation
 */
function setupFormSubmissions() {
    // Opening stock form
    const openingStockForm = document.getElementById('openingStockForm');
    if (openingStockForm) {
        openingStockForm.addEventListener('submit', function(e) {
            if (!validateOpeningStockForm()) {
                e.preventDefault();
                return false;
            }
        });
    }
    
    // Stock transfer form
    const transferForm = document.getElementById('stockTransferForm');
    if (transferForm) {
        transferForm.addEventListener('submit', function(e) {
            if (!validateStockTransferForm()) {
                e.preventDefault();
                return false;
            }
            
            // Confirm large transfers
            const quantity = parseFloat(document.getElementById('transfer_quantity').value || 0);
            const sourceName = document.getElementById('source_location').options[document.getElementById('source_location').selectedIndex].text;
            const targetName = document.getElementById('target_location').options[document.getElementById('target_location').selectedIndex].text;
            
            if (quantity > 10) {
                if (!confirm(`You are about to transfer ${quantity} units from ${sourceName} to ${targetName}. Are you sure?`)) {
                    e.preventDefault();
                    return false;
                }
            }
        });
    }
    
    // Batch expiry form
    const expiryForm = document.getElementById('batchExpiryForm');
    if (expiryForm) {
        expiryForm.addEventListener('submit', function(e) {
            if (!validateBatchExpiryForm()) {
                e.preventDefault();
                return false;
            }
        });
    }
}

/**
 * Validate opening stock form
 */
function validateOpeningStockForm() {
    let isValid = true;
    let errorMessage = '';
    
    // Validate medicine selection
    const medicineId = document.getElementById('medicine_id').value;
    if (!medicineId) {
        errorMessage += 'Please select a medicine.\n';
        isValid = false;
    }
    
    // Validate batch number
    const batchNumber = document.getElementById('batch_number').value;
    if (!batchNumber || batchNumber.trim().length < 2) {
        errorMessage += 'Please enter a valid batch number.\n';
        isValid = false;
    }
    
    // Validate expiry date
    const expiryDate = document.getElementById('expiry_date').value;
    if (!expiryDate) {
        errorMessage += 'Please enter an expiry date.\n';
        isValid = false;
    } else {
        const today = new Date();
        const expiry = new Date(expiryDate);
        if (expiry <= today) {
            errorMessage += 'Expiry date must be in the future.\n';
            isValid = false;
        }
    }
    
    // Validate quantity
    const quantity = parseFloat(document.getElementById('quantity').value || 0);
    if (isNaN(quantity) || quantity <= 0) {
        errorMessage += 'Please enter a valid quantity (must be greater than 0).\n';
        isValid = false;
    }
    
    // Validate purchase price
    const purchasePrice = parseFloat(document.getElementById('purchase_price').value || 0);
    if (isNaN(purchasePrice) || purchasePrice <= 0) {
        errorMessage += 'Please enter a valid purchase price (must be greater than 0).\n';
        isValid = false;
    }
    
    // Validate MRP
    const mrp = parseFloat(document.getElementById('mrp').value || 0);
    if (isNaN(mrp) || mrp <= 0) {
        errorMessage += 'Please enter a valid MRP (must be greater than 0).\n';
        isValid = false;
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

/**
 * Validate stock transfer form
 */
function validateStockTransferForm() {
    let isValid = true;
    let errorMessage = '';
    
    // Validate medicine selection
    const medicineId = document.getElementById('medicine_id').value;
    if (!medicineId) {
        errorMessage += 'Please select a medicine.\n';
        isValid = false;
    }
    
    // Validate batch selection
    const batchId = document.getElementById('batch_id').value;
    if (!batchId) {
        errorMessage += 'Please select a batch.\n';
        isValid = false;
    }
    
    // Validate source location
    const sourceLocation = document.getElementById('source_location').value;
    if (!sourceLocation) {
        errorMessage += 'Please select a source location.\n';
        isValid = false;
    }
    
    // Validate target location
    const targetLocation = document.getElementById('target_location').value;
    if (!targetLocation) {
        errorMessage += 'Please select a target location.\n';
        isValid = false;
    }
    
    // Validate source and target are different
    if (sourceLocation === targetLocation) {
        errorMessage += 'Source and target locations must be different.\n';
        isValid = false;
    }
    
    // Validate quantity
    const quantity = parseFloat(document.getElementById('transfer_quantity').value || 0);
    if (isNaN(quantity) || quantity <= 0) {
        errorMessage += 'Please enter a valid quantity (must be greater than 0).\n';
        isValid = false;
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

/**
 * Validate batch expiry form
 */
function validateBatchExpiryForm() {
    let isValid = true;
    let errorMessage = '';
    
    // Validate at least one batch is selected
    const selectedBatches = document.querySelectorAll('input[name="batch_ids[]"]:checked');
    if (selectedBatches.length === 0) {
        errorMessage += 'Please select at least one batch.\n';
        isValid = false;
    }
    
    // Validate action selection
    const actionRadios = document.querySelectorAll('input[name="expiry_action"]');
    let actionSelected = false;
    actionRadios.forEach(radio => {
        if (radio.checked) {
            actionSelected = true;
        }
    });
    
    if (!actionSelected) {
        errorMessage += 'Please select an action to take for the expired batches.\n';
        isValid = false;
    }
    
    // If writeoff selected, validate reason
    const writeoffRadio = document.querySelector('input[name="expiry_action"][value="writeoff"]');
    if (writeoffRadio && writeoffRadio.checked) {
        const reason = document.getElementById('writeoff_reason').value;
        if (!reason || reason.trim().length < 5) {
            errorMessage += 'Please provide a detailed reason for the write-off.\n';
            isValid = false;
        }
    }
    
    if (!isValid) {
        alert('Please correct the following errors:\n\n' + errorMessage);
    }
    
    return isValid;
}

// Export any functionality that might be needed by other modules
export { initBatchManagement, updateMedicineDetails };