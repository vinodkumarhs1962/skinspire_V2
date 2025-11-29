/**
 * Promotion Simulator Component
 * Simulates which promotions would apply to a given item and patient
 * Uses cascading dropdown pattern similar to invoice line items
 * Supports P1 > P2 > P4 priority system
 */

class PromotionSimulator {
    constructor(options = {}) {
        // Get DOM elements
        this.itemTypeSelect = document.getElementById(options.itemTypeSelect || 'sim-item-type');
        this.itemSearchInput = document.getElementById(options.itemSearchInput || 'sim-item-search');
        this.itemSearchResults = document.getElementById(options.itemSearchResults || 'sim-item-results');
        this.selectedItemDisplay = document.getElementById(options.selectedItemDisplay || 'sim-selected-item');
        this.quantityInput = document.getElementById(options.quantityInput || 'sim-qty');
        this.dateInput = document.getElementById(options.dateInput || 'sim-date');
        this.runButton = document.getElementById(options.runButton || 'run-simulation-btn');
        this.clearButton = document.getElementById(options.clearButton || 'clear-simulation-btn');
        this.resultsContainer = document.getElementById(options.resultsContainer || 'simulation-results');

        // Hidden inputs for selected item
        this.itemIdInput = document.getElementById(options.itemIdInput || 'sim-item-id');
        this.itemNameInput = document.getElementById(options.itemNameInput || 'sim-item-name');
        this.itemPriceInput = document.getElementById(options.itemPriceInput || 'sim-item-price');

        // Patient search elements
        this.patientSearchInput = document.getElementById('sim-patient-search');
        this.patientDropdown = document.getElementById('sim-patient-dropdown');
        this.patientIdInput = document.getElementById('sim-patient-id');
        this.patientContextDisplay = document.getElementById('sim-patient-context');

        // Include draft campaigns checkbox
        this.includeDraftCheckbox = document.getElementById('sim-include-draft');

        // State
        this.selectedItem = null;
        this.selectedPatient = null;
        this.searchTimeout = null;
        this.patientSearchTimeout = null;
        this.isSearching = false;

        if (!this.itemTypeSelect || !this.itemSearchInput) {
            console.error('Simulator elements not found');
            return;
        }

        this.attachEventListeners();
        console.log('[Simulator] Initialized');
    }

    attachEventListeners() {
        // Item type change - clear selection and reset search
        this.itemTypeSelect.addEventListener('change', () => this.onItemTypeChange());

        // Item search with debounce
        this.itemSearchInput.addEventListener('input', (e) => this.onSearchInput(e));
        this.itemSearchInput.addEventListener('focus', (e) => this.onSearchFocus(e));

        // Patient search with debounce
        if (this.patientSearchInput) {
            this.patientSearchInput.addEventListener('input', (e) => this.onPatientSearchInput(e));
            this.patientSearchInput.addEventListener('focus', (e) => this.onPatientSearchFocus(e));
        }

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.itemSearchInput.contains(e.target) &&
                !this.itemSearchResults.contains(e.target)) {
                this.hideSearchResults();
            }
            if (this.patientSearchInput && this.patientDropdown &&
                !this.patientSearchInput.contains(e.target) &&
                !this.patientDropdown.contains(e.target)) {
                this.patientDropdown.classList.add('hidden');
            }
        });

        // Clear all button
        this.clearButton?.addEventListener('click', () => this.clearAll());

        // Run simulation
        this.runButton?.addEventListener('click', () => this.runSimulation());

        // Auto-run on Enter in quantity field
        this.quantityInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.runSimulation();
        });

        // Enter key in search field
        this.itemSearchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideSearchResults();
            }
        });
    }

    // =========================================================================
    // PATIENT SEARCH
    // =========================================================================

    onPatientSearchInput(e) {
        const query = e.target.value.trim();

        if (this.patientSearchTimeout) {
            clearTimeout(this.patientSearchTimeout);
        }

        if (query.length >= 2) {
            this.patientSearchTimeout = setTimeout(() => {
                this.performPatientSearch(query);
            }, 300);
        } else {
            this.patientDropdown?.classList.add('hidden');
        }
    }

    onPatientSearchFocus(e) {
        const query = e.target.value.trim();
        if (query.length >= 2) {
            this.performPatientSearch(query);
        }
    }

    async performPatientSearch(query) {
        try {
            const response = await fetch(`/api/universal/patients/search?q=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();

            if (data.success && data.results && data.results.length > 0) {
                this.renderPatientResults(data.results);
            } else {
                this.patientDropdown.innerHTML = '<div class="promo-autocomplete-no-results">No patients found</div>';
                this.patientDropdown.classList.remove('hidden');
            }
        } catch (error) {
            console.error('[Simulator] Patient search error:', error);
        }
    }

    renderPatientResults(results) {
        this.patientDropdown.innerHTML = '';

        results.forEach(patient => {
            const div = document.createElement('div');
            div.className = 'promo-autocomplete-item';

            // Build badges for VIP and loyalty
            let badges = '';
            if (patient.is_vip || patient.is_special_group) {
                badges += '<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 mr-1"><i class="fas fa-star mr-1"></i>VIP</span>';
            }
            if (patient.has_loyalty_card) {
                badges += '<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800"><i class="fas fa-heart mr-1"></i>Loyalty</span>';
            }

            div.innerHTML = `
                <div class="promo-autocomplete-item-label">${patient.label || patient.name}</div>
                <div class="promo-autocomplete-item-subtitle">
                    ${patient.mrn || ''} ${badges}
                </div>
            `;

            div.addEventListener('click', () => this.selectPatient(patient));
            this.patientDropdown.appendChild(div);
        });

        this.patientDropdown.classList.remove('hidden');
    }

    selectPatient(patient) {
        this.selectedPatient = patient;
        this.patientSearchInput.value = patient.label || patient.name;
        if (this.patientIdInput) {
            // Use patient_id (UUID) not value (which is patient name for filtering)
            this.patientIdInput.value = patient.patient_id || patient.uuid || '';
        }
        this.patientDropdown.classList.add('hidden');

        // Show patient context
        this.showPatientContext(patient);
        console.log('[Simulator] Selected patient:', patient, 'UUID:', this.patientIdInput?.value);
    }

    showPatientContext(patient) {
        if (!this.patientContextDisplay) return;

        let html = '<div class="flex flex-wrap gap-2">';

        if (patient.is_vip || patient.is_special_group) {
            html += '<span class="inline-flex items-center px-2 py-1 rounded bg-yellow-100 text-yellow-800 text-xs"><i class="fas fa-star mr-1"></i>VIP Patient - Eligible for VIP campaigns</span>';
        }

        if (patient.has_loyalty_card) {
            const cardInfo = patient.loyalty_card_type || 'Loyalty Card';
            const validStatus = patient.loyalty_card_valid ?
                '<span class="text-green-600"><i class="fas fa-check-circle mr-1"></i>Valid</span>' :
                '<span class="text-red-600"><i class="fas fa-times-circle mr-1"></i>Expired</span>';
            html += `<span class="inline-flex items-center px-2 py-1 rounded bg-purple-100 text-purple-800 text-xs"><i class="fas fa-heart mr-1"></i>${cardInfo} ${validStatus}</span>`;
        }

        if (!patient.is_vip && !patient.is_special_group && !patient.has_loyalty_card) {
            html += '<span class="text-gray-500 text-xs"><i class="fas fa-user mr-1"></i>Regular patient - Standard discounts apply</span>';
        }

        html += '</div>';
        this.patientContextDisplay.innerHTML = html;
        this.patientContextDisplay.classList.remove('hidden');
    }

    clearPatient() {
        this.selectedPatient = null;
        if (this.patientSearchInput) this.patientSearchInput.value = '';
        if (this.patientIdInput) this.patientIdInput.value = '';
        if (this.patientContextDisplay) {
            this.patientContextDisplay.innerHTML = '';
            this.patientContextDisplay.classList.add('hidden');
        }
    }

    // =========================================================================
    // ITEM SEARCH
    // =========================================================================

    onItemTypeChange() {
        // Clear current selection when type changes
        this.clearSelection();

        // Focus on search input
        this.itemSearchInput.focus();

        // Update placeholder based on type
        const typeLabels = {
            'service': 'Search for services...',
            'medicine': 'Search for medicines...',
            'package': 'Search for packages...'
        };
        this.itemSearchInput.placeholder = typeLabels[this.itemTypeSelect.value] || 'Type to search...';

        console.log(`[Simulator] Item type changed to: ${this.itemTypeSelect.value}`);
    }

    onSearchInput(e) {
        const query = e.target.value.trim();

        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        this.searchTimeout = setTimeout(() => {
            if (query.length >= 1) {
                this.performSearch(query);
            } else {
                this.hideSearchResults();
            }
        }, 300);
    }

    onSearchFocus(e) {
        const query = e.target.value.trim();
        if (query.length >= 1) {
            this.performSearch(query);
        } else {
            this.performSearch('');
        }
    }

    async performSearch(query) {
        const itemType = this.itemTypeSelect.value;

        if (!itemType) {
            this.showSearchMessage('Please select an item type first');
            return;
        }

        this.isSearching = true;
        this.showSearchMessage('<i class="fas fa-spinner fa-spin mr-2"></i>Searching...');

        try {
            const url = `/promotions/api/items/${itemType}?search=${encodeURIComponent(query)}&limit=20`;
            const response = await fetch(url, {
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.error) {
                this.showSearchMessage(`<span class="text-red-500">${data.error}</span>`);
                return;
            }

            this.renderSearchResults(data.items || []);

        } catch (error) {
            console.error('[Simulator] Error searching items:', error);
            this.showSearchMessage('<span class="text-red-500">Error searching items</span>');
        }

        this.isSearching = false;
    }

    renderSearchResults(items) {
        if (!items || items.length === 0) {
            this.showSearchMessage('No items found');
            return;
        }

        this.itemSearchResults.innerHTML = '';

        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'p-2 hover:bg-blue-50 dark:hover:bg-gray-700 cursor-pointer border-b border-gray-100 dark:border-gray-700 last:border-0';

            const priceDisplay = item.price ? `₹${parseFloat(item.price).toLocaleString(undefined, {minimumFractionDigits: 2})}` : 'N/A';
            const itemType = this.itemTypeSelect.value;
            let extraInfo = '';

            if (itemType === 'medicine') {
                extraInfo = item.category ? `<span class="text-gray-400">| ${item.category}</span>` : '';
            } else if (itemType === 'service') {
                extraInfo = item.department ? `<span class="text-gray-400">| ${item.department}</span>` : '';
            } else if (itemType === 'package') {
                extraInfo = item.validity_days ? `<span class="text-gray-400">| ${item.validity_days} days</span>` : '';
            }

            // Show bulk discount indicator if item has bulk discount configured
            let bulkBadge = '';
            if (item.bulk_discount_percent > 0) {
                bulkBadge = `<span class="ml-2 px-1.5 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">Bulk ${item.bulk_discount_percent}%</span>`;
            }

            div.innerHTML = `
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <div class="font-medium text-gray-900 dark:text-white text-sm">${item.name}${bulkBadge}</div>
                        <div class="text-xs text-gray-500">
                            ${item.code || ''} ${extraInfo}
                        </div>
                    </div>
                    <div class="text-right">
                        <span class="font-semibold text-blue-600 dark:text-blue-400 text-sm">${priceDisplay}</span>
                    </div>
                </div>
            `;

            div.addEventListener('click', () => this.selectItem(item));
            this.itemSearchResults.appendChild(div);
        });

        this.showSearchResults();
    }

    selectItem(item) {
        console.log('[Simulator] Selected item:', item);

        this.selectedItem = item;

        if (this.itemIdInput) this.itemIdInput.value = item.id;
        if (this.itemNameInput) this.itemNameInput.value = item.name;
        if (this.itemPriceInput) this.itemPriceInput.value = item.price || 0;

        this.itemSearchInput.value = item.name;
        this.showSelectedItem(item);
        this.hideSearchResults();
        this.quantityInput?.focus();
    }

    showSelectedItem(item) {
        if (!this.selectedItemDisplay) return;

        const priceDisplay = item.price ? `₹${parseFloat(item.price).toLocaleString(undefined, {minimumFractionDigits: 2})}` : 'N/A';
        const typeIcons = {
            'service': 'fa-concierge-bell text-blue-600',
            'medicine': 'fa-pills text-green-600',
            'package': 'fa-box text-purple-600'
        };
        const icon = typeIcons[this.itemTypeSelect.value] || 'fa-tag text-gray-600';

        // Show bulk/standard discount info
        let discountInfo = '';
        if (item.bulk_discount_percent > 0) {
            discountInfo += `<span class="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded mr-1"><i class="fas fa-layer-group mr-1"></i>Bulk: ${item.bulk_discount_percent}%</span>`;
        }
        if (item.standard_discount_percent > 0) {
            discountInfo += `<span class="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded"><i class="fas fa-tag mr-1"></i>Std: ${item.standard_discount_percent}%</span>`;
        }

        this.selectedItemDisplay.innerHTML = `
            <div class="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div class="flex items-center">
                    <div class="p-2 bg-white dark:bg-gray-800 rounded-lg mr-3">
                        <i class="fas ${icon}"></i>
                    </div>
                    <div>
                        <div class="font-medium text-gray-900 dark:text-white">${item.name}</div>
                        <div class="text-xs text-gray-500">${item.code || this.itemTypeSelect.value} ${discountInfo}</div>
                    </div>
                </div>
                <div class="text-right">
                    <div class="font-bold text-blue-600 dark:text-blue-400">${priceDisplay}</div>
                    <button type="button" class="clear-item-btn text-xs text-red-500 hover:text-red-700 mt-1">
                        <i class="fas fa-times mr-1"></i>Clear
                    </button>
                </div>
            </div>
        `;

        this.selectedItemDisplay.classList.remove('hidden');

        // Re-attach clear button listener
        const clearBtn = this.selectedItemDisplay.querySelector('.clear-item-btn');
        clearBtn?.addEventListener('click', () => this.clearSelection());
    }

    clearSelection() {
        this.selectedItem = null;

        if (this.itemIdInput) this.itemIdInput.value = '';
        if (this.itemNameInput) this.itemNameInput.value = '';
        if (this.itemPriceInput) this.itemPriceInput.value = '';

        this.itemSearchInput.value = '';

        if (this.selectedItemDisplay) {
            this.selectedItemDisplay.innerHTML = '';
            this.selectedItemDisplay.classList.add('hidden');
        }

        if (this.resultsContainer) {
            this.resultsContainer.innerHTML = '';
            this.resultsContainer.classList.add('hidden');
        }

        this.itemSearchInput.focus();
    }

    clearAll() {
        this.clearSelection();
        this.clearPatient();
        if (this.quantityInput) this.quantityInput.value = 1;
        if (this.dateInput) this.dateInput.value = new Date().toISOString().split('T')[0];
        if (this.resultsContainer) {
            this.resultsContainer.innerHTML = '';
            this.resultsContainer.classList.add('hidden');
        }
    }

    showSearchResults() {
        this.itemSearchResults.classList.remove('hidden');
    }

    hideSearchResults() {
        this.itemSearchResults.classList.add('hidden');
    }

    showSearchMessage(message) {
        this.itemSearchResults.innerHTML = `<div class="p-3 text-sm text-gray-500">${message}</div>`;
        this.showSearchResults();
    }

    // =========================================================================
    // SIMULATION
    // =========================================================================

    async runSimulation() {
        const itemType = this.itemTypeSelect.value;
        const itemId = this.itemIdInput?.value || '';
        const quantity = parseInt(this.quantityInput?.value || 1);
        const simulationDate = this.dateInput?.value;
        const patientId = this.patientIdInput?.value || null;
        const includeDraft = this.includeDraftCheckbox?.checked || false;

        if (!itemId) {
            this.showError('Please select an item first');
            return;
        }

        // Show loading state
        this.runButton.disabled = true;
        this.runButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Simulating...';

        try {
            const response = await fetch('/promotions/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_type: itemType,
                    item_id: itemId,
                    quantity: quantity,
                    simulation_date: simulationDate,
                    patient_id: patientId,
                    include_draft: includeDraft
                })
            });

            const result = await response.json();

            if (result.error) {
                this.showError(result.error);
            } else {
                this.renderResults(result);
            }
        } catch (error) {
            console.error('[Simulator] Simulation error:', error);
            this.showError('An error occurred during simulation');
        }

        // Reset button
        this.runButton.disabled = false;
        this.runButton.innerHTML = '<i class="fas fa-play mr-2"></i>Simulate';
    }

    renderResults(result) {
        this.resultsContainer.classList.remove('hidden');

        const promotions = result.applicable_promotions || [];
        const finalDiscount = result.final_discount;
        const patientContext = result.patient_context;

        // Separate base discounts from loyalty top-up
        const baseDiscounts = promotions.filter(p => p.type !== 'loyalty');
        const loyaltyDiscounts = promotions.filter(p => p.type === 'loyalty');

        let promotionsHtml = '';

        // Base Discounts Section (Campaign, Bulk, Standard) - MAX wins
        if (baseDiscounts.length > 0) {
            promotionsHtml += this.renderDiscountSection('Base Discounts (MAX wins)', 'fa-tag', 'blue', baseDiscounts);
        }

        // Loyalty Top-up Section
        if (loyaltyDiscounts.length > 0) {
            promotionsHtml += this.renderDiscountSection('Loyalty Top-up (Always Added)', 'fa-heart', 'purple', loyaltyDiscounts);
        }

        if (promotions.length === 0) {
            promotionsHtml = `
                <div class="p-6 text-center text-gray-500">
                    <i class="fas fa-info-circle text-2xl mb-2"></i>
                    <p>No promotions applicable for this item</p>
                </div>
            `;
        }

        // Patient context display
        let patientHtml = '';
        if (patientContext) {
            patientHtml = `
                <div class="mb-4 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700">
                    <div class="flex items-center gap-2 text-sm">
                        <i class="fas fa-user text-purple-600"></i>
                        <span class="font-medium">${patientContext.name}</span>
                        ${patientContext.is_vip ? '<span class="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded"><i class="fas fa-star mr-1"></i>VIP</span>' : ''}
                        ${patientContext.has_loyalty_card ? `<span class="px-2 py-0.5 text-xs bg-purple-100 text-purple-800 rounded"><i class="fas fa-heart mr-1"></i>${patientContext.loyalty_card_type || 'Loyalty'}</span>` : ''}
                    </div>
                </div>
            `;
        }

        this.resultsContainer.innerHTML = `
            ${patientHtml}
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Applicable Promotions -->
                <div class="lg:col-span-2 bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden">
                    <div class="px-4 py-3 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                        <h4 class="font-semibold text-gray-900 dark:text-white">
                            <i class="fas fa-list mr-2 text-blue-600"></i>All Applicable Promotions
                        </h4>
                    </div>
                    <div class="divide-y divide-gray-200 dark:divide-gray-700">
                        ${promotionsHtml}
                    </div>
                </div>

                <!-- Final Calculation Card -->
                <div class="bg-white dark:bg-gray-800 rounded-lg shadow border border-gray-200 dark:border-gray-700">
                    <div class="px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 rounded-t-lg">
                        <h4 class="font-semibold text-white">
                            <i class="fas fa-calculator mr-2"></i>Final Calculation
                        </h4>
                    </div>
                    <div class="p-4 space-y-4">
                        <!-- Item Info -->
                        <div class="text-center pb-4 border-b border-gray-200 dark:border-gray-700">
                            <p class="text-sm text-gray-500 dark:text-gray-400">Item</p>
                            <p class="font-semibold text-gray-900 dark:text-white">${result.item?.name || 'Unknown'}</p>
                            <p class="text-xs text-gray-400">Qty: ${result.quantity} x ₹${result.item?.unit_price?.toLocaleString() || 0}</p>
                        </div>

                        <!-- Price Breakdown -->
                        <div class="space-y-2">
                            <div class="flex justify-between">
                                <span class="text-gray-600 dark:text-gray-400">Original Price</span>
                                <span class="font-medium text-gray-900 dark:text-white">
                                    ₹${result.original_price?.toLocaleString(undefined, {minimumFractionDigits: 2}) || '0.00'}
                                </span>
                            </div>

                            ${finalDiscount ? `
                                ${finalDiscount.base_discount ? `
                                    <div class="flex justify-between items-center py-1.5 bg-blue-50 dark:bg-blue-900/20 rounded px-2 -mx-2">
                                        <span class="text-blue-700 dark:text-blue-300 text-sm">
                                            <i class="fas fa-tag mr-1"></i>${finalDiscount.base_discount.name}
                                            (${finalDiscount.base_discount.percent}%)
                                        </span>
                                        <span class="font-medium text-blue-600 dark:text-blue-400">
                                            -₹${finalDiscount.base_discount.amount?.toLocaleString(undefined, {minimumFractionDigits: 2}) || '0.00'}
                                        </span>
                                    </div>
                                ` : ''}
                                ${finalDiscount.loyalty_topup ? `
                                    <div class="flex justify-between items-center py-1.5 bg-purple-50 dark:bg-purple-900/20 rounded px-2 -mx-2">
                                        <span class="text-purple-700 dark:text-purple-300 text-sm">
                                            <i class="fas fa-heart mr-1"></i>${finalDiscount.loyalty_topup.name}
                                            (${finalDiscount.loyalty_topup.percent}%) <span class="text-xs opacity-75">TOP-UP</span>
                                        </span>
                                        <span class="font-medium text-purple-600 dark:text-purple-400">
                                            -₹${finalDiscount.loyalty_topup.amount?.toLocaleString(undefined, {minimumFractionDigits: 2}) || '0.00'}
                                        </span>
                                    </div>
                                ` : ''}
                                <div class="flex justify-between items-center py-1.5 bg-green-50 dark:bg-green-900/20 rounded px-2 -mx-2 border-t border-green-200 dark:border-green-800">
                                    <span class="text-green-700 dark:text-green-300 font-medium">
                                        <i class="fas fa-calculator mr-1"></i>Total Discount
                                        (${finalDiscount.total_percent || finalDiscount.percent || 0}%)
                                    </span>
                                    <span class="font-bold text-green-600 dark:text-green-400">
                                        -₹${finalDiscount.amount?.toLocaleString(undefined, {minimumFractionDigits: 2}) || '0.00'}
                                    </span>
                                </div>
                            ` : `
                                <div class="flex justify-between text-gray-400 py-2">
                                    <span>No discount applicable</span>
                                    <span>-₹0.00</span>
                                </div>
                            `}
                        </div>

                        <!-- Final Price -->
                        <div class="pt-4 border-t border-gray-200 dark:border-gray-700">
                            <div class="flex justify-between items-center">
                                <span class="text-lg font-bold text-gray-900 dark:text-white">Final Price</span>
                                <span class="text-2xl font-bold text-blue-600">
                                    ₹${result.final_price?.toLocaleString(undefined, {minimumFractionDigits: 2}) || '0.00'}
                                </span>
                            </div>
                            ${finalDiscount ? `
                                <p class="text-xs text-green-600 text-right mt-1">
                                    You save ₹${finalDiscount.amount?.toLocaleString(undefined, {minimumFractionDigits: 2})}!
                                </p>
                            ` : ''}
                        </div>

                        <!-- Simulation Info -->
                        <div class="pt-4 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500">
                            <p><i class="fas fa-calendar mr-1"></i>Simulation Date: ${result.simulation_date}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderDiscountSection(title, icon, color, promos) {
        const colorClasses = {
            blue: { bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-300', badge: 'bg-blue-100 text-blue-800' },
            purple: { bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-300', badge: 'bg-purple-100 text-purple-800' },
            gray: { bg: 'bg-gray-50 dark:bg-gray-800', border: 'border-gray-300', badge: 'bg-gray-100 text-gray-800' }
        };
        const colors = colorClasses[color] || colorClasses.gray;

        let promosHtml = promos.map(p => `
            <div class="py-2 px-3 ${p.would_apply ? (p.is_topup ? 'bg-purple-50 dark:bg-purple-900/30' : 'bg-green-50 dark:bg-green-900/20') : ''} ${p.is_draft ? 'border-l-2 border-gray-400 border-dashed' : ''}">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        ${this.getTypeIcon(p.type)}
                        <div>
                            <span class="font-medium text-gray-900 dark:text-white text-sm">${p.name}</span>
                            ${p.code ? `<span class="text-gray-400 text-xs ml-1">(${p.code})</span>` : ''}
                            ${p.stacking_mode ? this.getStackingModeBadge(p.stacking_mode) : ''}
                            ${p.is_draft ? '<span class="ml-1 px-1.5 py-0.5 text-xs bg-gray-200 text-gray-700 rounded"><i class="fas fa-edit mr-1"></i>Draft</span>' : ''}
                            ${p.is_topup ? '<span class="ml-1 px-1.5 py-0.5 text-xs bg-purple-200 text-purple-800 rounded">TOP-UP</span>' : ''}
                        </div>
                    </div>
                    <div class="flex items-center gap-3 text-sm">
                        <span class="text-gray-600 dark:text-gray-400">
                            ${p.discount_percent > 0 ? p.discount_percent + '%' : ''}
                            ${p.discount_type === 'fixed_amount' ? '₹' + p.discount_value : ''}
                        </span>
                        <span class="font-medium ${p.is_topup ? 'text-purple-600' : 'text-green-600'}">₹${p.discount_amount?.toLocaleString(undefined, {minimumFractionDigits: 2}) || '0.00'}</span>
                        ${p.would_apply
                            ? `<span class="px-2 py-0.5 rounded-full text-xs font-medium ${p.is_topup ? 'bg-purple-100 text-purple-800' : 'bg-green-100 text-green-800'}"><i class="fas fa-check mr-1"></i>${p.is_topup ? 'Added' : 'Applied'}</span>`
                            : `<span class="text-xs text-gray-400">${p.reason || ''}</span>`
                        }
                    </div>
                </div>
                ${p.type === 'bulk' && p.eligibility_note ? `
                    <div class="mt-1 ml-6 text-xs text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-2 py-1 rounded">
                        <i class="fas fa-info-circle mr-1"></i>${p.eligibility_note}
                    </div>
                ` : ''}
            </div>
        `).join('');

        return `
            <div class="${colors.bg} border-l-4 ${colors.border}">
                <div class="px-3 py-2 flex items-center gap-2 border-b border-gray-200 dark:border-gray-700">
                    <i class="fas ${icon} ${color === 'purple' ? 'text-purple-600' : 'text-blue-600'}"></i>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">${title}</span>
                </div>
                ${promosHtml}
            </div>
        `;
    }

    showError(message) {
        this.resultsContainer.classList.remove('hidden');
        this.resultsContainer.innerHTML = `
            <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div class="flex items-center">
                    <i class="fas fa-exclamation-circle text-red-600 dark:text-red-400 text-xl mr-3"></i>
                    <div>
                        <p class="font-semibold text-red-800 dark:text-red-200">Simulation Error</p>
                        <p class="text-sm text-red-600 dark:text-red-400">${message}</p>
                    </div>
                </div>
            </div>
        `;
    }

    getTypeIcon(type) {
        const icons = {
            'campaign': '<i class="fas fa-bullhorn text-blue-600"></i>',
            'bulk': '<i class="fas fa-layer-group text-orange-600"></i>',
            'loyalty': '<i class="fas fa-heart text-purple-600"></i>',
            'standard': '<i class="fas fa-tag text-gray-600"></i>'
        };
        return icons[type] || icons.standard;
    }

    getStackingModeBadge(mode) {
        const badges = {
            'exclusive': '<span class="ml-1 px-1.5 py-0.5 text-xs bg-red-100 text-red-700 rounded font-medium" title="Only this discount applies, all others excluded">EXCL</span>',
            'absolute': '<span class="ml-1 px-1.5 py-0.5 text-xs bg-amber-100 text-amber-700 rounded font-medium" title="Competes with other absolutes (best wins), then stacks with incrementals">ABS</span>',
            'incremental': '<span class="ml-1 px-1.5 py-0.5 text-xs bg-green-100 text-green-700 rounded font-medium" title="Always adds to total discount">INCR</span>',
            'fallback': '<span class="ml-1 px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded font-medium" title="Only applies if no other discounts">FALL</span>'
        };
        return badges[mode] || '';
    }
}

// Export for global use
window.PromotionSimulator = PromotionSimulator;
