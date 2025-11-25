/**
 * Invoice Bulk Discount Module
 * Real-time pricing consultation and discount calculation
 *
 * Purpose: Provide transparent pricing during patient discussions
 * - Shows current total price in real-time
 * - Indicates potential savings if more services added
 * - Auto-applies bulk discounts when eligible
 * - Allows manual override with validation
 */

class BulkDiscountManager {
    constructor() {
        this.hospitalConfig = null;
        this.serviceDiscounts = {};
        this.currentPatientLoyalty = null;
        this.isEnabled = false;
        this.isInitialized = false;
        this.userToggledCheckbox = false; // Track if user manually toggled
        this.isProcessing = false; // Prevent re-entry
        this.canEditDiscount = window.CAN_EDIT_DISCOUNT !== undefined ? window.CAN_EDIT_DISCOUNT : true; // Permission to manually edit discount fields

        // Bind methods
        this.initialize = this.initialize.bind(this);
        this.updatePricing = this.updatePricing.bind(this);
        this.toggleBulkDiscount = this.toggleBulkDiscount.bind(this);
    }

    /**
     * Initialize the bulk discount manager
     */
    async initialize(hospitalId, patientId) {
        try {
            console.log('Initializing Bulk Discount Manager...');

            // Load discount configuration
            await this.loadDiscountConfig(hospitalId);

            // Load patient loyalty card (if any)
            if (patientId) {
                await this.loadPatientLoyalty(patientId);
            }

            // Attach event listeners
            this.attachEventListeners();

            // Initial update
            this.updatePricing();

            this.isInitialized = true;
            console.log('✅ Bulk Discount Manager initialized');

        } catch (error) {
            console.error('❌ Failed to initialize Bulk Discount Manager:', error);
            this.showError('Failed to load discount configuration');
        }
    }

    /**
     * Load discount configuration from backend
     */
    async loadDiscountConfig(hospitalId) {
        try {
            const response = await fetch(`/api/discount/config/${hospitalId}`);
            const data = await response.json();

            if (data.success) {
                this.hospitalConfig = data.hospital_config;
                this.serviceDiscounts = data.service_discounts;

                console.log(`Discount config loaded: ${this.hospitalConfig.bulk_discount_enabled ? 'ENABLED' : 'DISABLED'}`);
                console.log(`Threshold: ${this.hospitalConfig.bulk_discount_min_service_count} services`);

            } else {
                throw new Error(data.error || 'Failed to load discount config');
            }
        } catch (error) {
            console.error('Error loading discount config:', error);
            throw error;
        }
    }

    /**
     * Load patient's loyalty card information
     */
    async loadPatientLoyalty(patientId) {
        try {
            const response = await fetch(`/api/discount/patient-loyalty/${patientId}`);
            const data = await response.json();

            if (data.success && data.has_loyalty_card) {
                this.currentPatientLoyalty = data.card;
                console.log(`Patient has ${data.card.card_type_name} card (${data.card.discount_percent}% discount)`);

                // Show loyalty card badge
                this.displayLoyaltyCardBadge(data.card);
            }
        } catch (error) {
            console.error('Error loading patient loyalty:', error);
            // Non-fatal error, continue without loyalty info
        }
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Bulk discount checkbox toggle
        const checkbox = document.getElementById('bulk-discount-enabled');
        if (checkbox) {
            checkbox.addEventListener('change', this.toggleBulkDiscount);
        }

        // Eligible discounts toggle buttons
        const bulkToggle = document.getElementById('bulk-eligible-toggle');
        if (bulkToggle) {
            bulkToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleEligibleDiscountsDisplay('bulk');
            });
        }

        const loyaltyToggle = document.getElementById('loyalty-eligible-toggle');
        if (loyaltyToggle) {
            loyaltyToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleEligibleDiscountsDisplay('loyalty');
            });
        }

        const standardToggle = document.getElementById('standard-eligible-toggle');
        if (standardToggle) {
            standardToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleEligibleDiscountsDisplay('standard');
            });
        }

        const promotionToggle = document.getElementById('promotion-eligible-toggle');
        if (promotionToggle) {
            promotionToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleEligibleDiscountsDisplay('promotion');
            });
        }

        // Line item changes (add, remove, change)
        document.addEventListener('line-item-added', () => this.updatePricing());
        document.addEventListener('line-item-removed', () => this.updatePricing());
        document.addEventListener('line-item-changed', () => this.updatePricing());

        // Service selection changes
        const serviceSelects = document.querySelectorAll('.service-select');
        serviceSelects.forEach(select => {
            select.addEventListener('change', () => this.updatePricing());
        });

        // Quantity changes
        const quantityInputs = document.querySelectorAll('.quantity-input');
        quantityInputs.forEach(input => {
            input.addEventListener('change', () => this.updatePricing());
        });
    }

    /**
     * Update pricing in real-time
     * MAIN FUNCTION - Called whenever line items change
     */
    async updatePricing() {
        if (!this.isInitialized || !this.hospitalConfig) {
            return;
        }

        // Prevent re-entry
        if (this.isProcessing) {
            console.log('Already processing, skipping updatePricing');
            return;
        }

        try {
            this.isProcessing = true;

            // Collect current line items
            const lineItems = this.collectLineItems();

            // If no line items, don't call API
            if (lineItems.length === 0) {
                console.log('No line items to price, skipping API call');
                this.isProcessing = false;
                return;
            }

            // Count services (sum of quantities, not just line items)
            const serviceItems = lineItems.filter(item => item.item_type === 'Service');
            const serviceCount = serviceItems.reduce((sum, item) => sum + item.quantity, 0);

            console.log(`Service count: ${serviceCount} (from ${serviceItems.length} line items)`);

            // Update service count display
            this.updateServiceCountDisplay(serviceCount);

            // Check eligibility
            const isEligible = serviceCount >= this.hospitalConfig.bulk_discount_min_service_count;
            const checkbox = document.getElementById('bulk-discount-enabled');

            if (!checkbox) return;

            // Auto-check/uncheck checkbox based on eligibility (only if user hasn't manually toggled)
            if (isEligible) {
                // Only auto-check if user hasn't manually unchecked
                if (!this.userToggledCheckbox) {
                    checkbox.checked = true;
                }
                checkbox.disabled = false;
                this.updateEligibilityBadge('eligible', serviceCount);
            } else {
                // Only auto-uncheck if user hasn't manually checked
                if (!this.userToggledCheckbox) {
                    checkbox.checked = false;
                }
                checkbox.disabled = false;
                const servicesNeeded = this.hospitalConfig.bulk_discount_min_service_count - serviceCount;
                this.updateEligibilityBadge('not-eligible', serviceCount, servicesNeeded);
            }

            // Always apply discounts via API (backend will determine which discounts apply)
            // Even if bulk checkbox is unchecked, loyalty/other discounts may still apply
            await this.applyDiscounts(lineItems);

        } catch (error) {
            console.error('Error updating pricing:', error);
        } finally {
            this.isProcessing = false;
        }
    }

    /**
     * Collect current line items from the invoice form
     */
    collectLineItems() {
        const lineItems = [];
        const rows = document.querySelectorAll('.line-item-row');

        console.log(`Collecting line items from ${rows.length} rows`);

        rows.forEach((row, index) => {
            const itemType = row.querySelector('.item-type')?.value;
            if (!itemType) return;

            const serviceId = row.querySelector('.item-id')?.value;
            const quantity = parseInt(row.querySelector('.quantity')?.value || 1);
            const unitPrice = parseFloat(row.querySelector('.unit-price')?.value || 0);

            console.log(`Row ${index}: type=${itemType}, id=${serviceId}, qty=${quantity}, price=${unitPrice}`);

            if (itemType === 'Service' && serviceId) {
                lineItems.push({
                    index: index,
                    item_type: itemType,
                    service_id: serviceId,
                    item_id: serviceId,
                    quantity: quantity,
                    unit_price: unitPrice
                });
            }
        });

        console.log(`Collected ${lineItems.length} service line items`);
        return lineItems;
    }

    /**
     * Apply discounts to line items via backend calculation
     */
    async applyDiscounts(lineItems) {
        if (lineItems.length === 0) return;

        try {
            // Get hospital and patient IDs
            const hospitalId = document.querySelector('[name="hospital_id"]')?.value;
            const patientId = document.querySelector('[name="patient_id"]')?.value;

            if (!hospitalId) {
                console.error('Hospital ID not found');
                return;
            }

            // Don't call API if no patient selected (prevents UUID error with empty string)
            if (!patientId || patientId === '' || patientId === 'null') {
                console.log('No patient selected, skipping discount calculation');
                return;
            }

            const requestData = {
                hospital_id: hospitalId,
                patient_id: patientId,
                line_items: lineItems
            };

            console.log('Sending discount calculation request:', requestData);

            // Call backend API to calculate discounts
            const response = await fetch('/api/discount/calculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (data.success) {
                // Update line items with calculated discounts
                this.updateLineItemDiscounts(data.line_items);

                // Update pricing summary
                this.updatePricingSummary(data.summary);

                // Update discount breakdown
                this.updateDiscountBreakdown(data.line_items);

            } else {
                throw new Error(data.error || 'Failed to calculate discounts');
            }

        } catch (error) {
            console.error('Error applying discounts:', error);
            this.showError('Failed to calculate discounts. Please try again.');
        }
    }

    /**
     * Update line item discount fields in the UI
     */
    updateLineItemDiscounts(discountedItems) {
        const rows = document.querySelectorAll('.line-item-row');

        console.log(`Updating ${discountedItems.length} line items with discounts`);

        discountedItems.forEach((item) => {
            if (item.item_type !== 'Service') return;

            // Find the matching row by service_id
            const serviceId = item.service_id || item.item_id;
            if (!serviceId) {
                console.warn('Item missing service_id:', item);
                return;
            }

            // Find row with matching item-id value
            let matchedRow = null;
            rows.forEach(row => {
                const itemIdInput = row.querySelector('.item-id');
                if (itemIdInput && itemIdInput.value === serviceId) {
                    matchedRow = row;
                }
            });

            if (!matchedRow) {
                console.warn(`No matching row found for service ${serviceId}`);
                return;
            }

            const discountInput = matchedRow.querySelector('.discount-percent');
            if (discountInput) {
                console.log(`Setting discount for ${item.item_name || serviceId}: ${item.discount_percent}%`);
                discountInput.value = item.discount_percent.toFixed(2);

                // Enforce readonly state based on user permission
                // Front desk users cannot manually edit discount fields
                if (!this.canEditDiscount) {
                    discountInput.setAttribute('readonly', true);
                    discountInput.style.backgroundColor = '#f3f4f6';
                    discountInput.style.cursor = 'not-allowed';
                    discountInput.title = 'Auto-calculated discount (Manager can edit)';
                }

                // Store discount metadata in hidden input for patient view access
                let metadataInput = matchedRow.querySelector('.discount-metadata');
                if (!metadataInput) {
                    metadataInput = document.createElement('input');
                    metadataInput.type = 'hidden';
                    metadataInput.className = 'discount-metadata';
                    matchedRow.appendChild(metadataInput);
                }
                metadataInput.value = JSON.stringify(item.discount_metadata || {});

                // Store discount type for patient view
                let discountTypeInput = matchedRow.querySelector('.discount-type');
                if (!discountTypeInput) {
                    discountTypeInput = document.createElement('input');
                    discountTypeInput.type = 'hidden';
                    discountTypeInput.className = 'discount-type';
                    matchedRow.appendChild(discountTypeInput);
                }
                discountTypeInput.value = item.discount_type || 'none';

                // Add discount badge (pass metadata for stacked discounts)
                this.addDiscountBadge(matchedRow, item.discount_type, item.discount_percent, item.discount_metadata);

                // Trigger input event to recalculate line total and invoice totals
                // This will trigger the invoice_item.js event handler which handles all calculations
                discountInput.dispatchEvent(new Event('input', { bubbles: true }));
            } else {
                console.warn('Discount input not found in row');
            }
        });

        console.log('Discount update complete');

        // Update eligible discounts display after all line items are updated
        this.updateEligibleDiscountsDisplay();
    }

    /**
     * Clear discounts from all line items
     */
    clearDiscounts() {
        const rows = document.querySelectorAll('.line-item-row');

        console.log(`Clearing bulk discounts from ${rows.length} rows`);

        rows.forEach(row => {
            const itemType = row.querySelector('.item-type')?.value;
            if (itemType !== 'Service') return;

            const discountInput = row.querySelector('.discount-percent');
            if (discountInput) {
                // Only clear if it was auto-applied (has badge)
                const badge = row.querySelector('.discount-badge');
                if (badge && badge.classList.contains('bulk-discount')) {
                    console.log('Clearing discount from row');
                    discountInput.value = '0';
                    badge.remove();
                    // Trigger input event to recalculate
                    discountInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        });

        // Clear pricing summary
        this.updatePricingSummary({
            total_services: 0,
            total_original_price: 0,
            total_discount: 0,
            total_final_price: 0,
            discount_percentage: 0
        });

        // Hide discount breakdown
        const breakdown = document.getElementById('bulk-discount-breakdown');
        if (breakdown) breakdown.style.display = 'none';

        this.recalculateInvoiceTotals();
    }

    /**
     * Update service count display
     */
    updateServiceCountDisplay(count) {
        const display = document.getElementById('service-count-display');
        if (display) {
            display.textContent = `${count} service${count !== 1 ? 's' : ''}`;
        }

        const threshold = document.getElementById('threshold-display');
        if (threshold) {
            threshold.textContent = `Need ${this.hospitalConfig.bulk_discount_min_service_count} for bulk discount`;
        }

        const info = document.getElementById('bulk-discount-info');
        if (info) info.style.display = 'block';
    }

    /**
     * Update eligibility badge
     */
    updateEligibilityBadge(status, currentCount, servicesNeeded = 0) {
        const badge = document.getElementById('bulk-discount-badge');
        if (!badge) return;

        badge.style.display = 'inline-block';

        if (status === 'eligible') {
            badge.className = 'badge badge-success';
            badge.innerHTML = `✓ Eligible (${currentCount} services)`;
        } else {
            badge.className = 'badge badge-warning';
            badge.innerHTML = `Add ${servicesNeeded} more service${servicesNeeded !== 1 ? 's' : ''} to unlock`;
        }
    }

    /**
     * Update pricing summary panel
     */
    updatePricingSummary(summary) {
        // Get grand total from invoice display element (which includes GST)
        const grandTotalDisplayEl = document.getElementById('grand-total-display');
        const grandTotalHiddenEl = document.getElementById('grand-total');

        let grandTotal = 0;
        if (grandTotalDisplayEl && grandTotalDisplayEl.textContent) {
            grandTotal = parseFloat(grandTotalDisplayEl.textContent);
        } else if (grandTotalHiddenEl && grandTotalHiddenEl.textContent) {
            grandTotal = parseFloat(grandTotalHiddenEl.textContent);
        } else {
            grandTotal = summary.total_final_price || 0;
        }

        // Update ORIGINAL pricing summary (outside collapsible)
        const originalPriceEl = document.getElementById('summary-original-price');
        if (originalPriceEl) {
            originalPriceEl.textContent = `₹${summary.total_original_price.toFixed(2)}`;
        }

        const discountEl = document.getElementById('summary-discount');
        if (discountEl) {
            discountEl.textContent = `- ₹${summary.total_discount.toFixed(2)}`;
            discountEl.style.color = summary.total_discount > 0 ? '#ef4444' : '#6b7280';
        }

        const finalPriceEl = document.getElementById('summary-final-price');
        if (finalPriceEl) {
            finalPriceEl.textContent = `₹${grandTotal.toFixed(2)}`;
            finalPriceEl.style.fontWeight = 'bold';
            finalPriceEl.style.fontSize = '1.5rem';
            finalPriceEl.style.color = summary.total_discount > 0 ? '#10b981' : '#1f2937';
        }

        // Update COLLAPSIBLE pricing summary (inside discount controls)
        const originalPriceCollapsibleEl = document.getElementById('summary-original-price-collapsible');
        if (originalPriceCollapsibleEl) {
            originalPriceCollapsibleEl.textContent = `₹${summary.total_original_price.toFixed(2)}`;
        }

        const discountCollapsibleEl = document.getElementById('summary-discount-collapsible');
        if (discountCollapsibleEl) {
            discountCollapsibleEl.textContent = `- ₹${summary.total_discount.toFixed(2)}`;
        }

        // Calculate and display GST (grandTotal - (original - discount))
        const priceAfterDiscount = summary.total_original_price - summary.total_discount;
        const gstAmount = grandTotal - priceAfterDiscount;
        const gstCollapsibleEl = document.getElementById('summary-gst-collapsible');
        if (gstCollapsibleEl) {
            gstCollapsibleEl.textContent = `₹${gstAmount.toFixed(2)}`;
        }

        const finalPriceCollapsibleEl = document.getElementById('summary-final-price-collapsible');
        if (finalPriceCollapsibleEl) {
            finalPriceCollapsibleEl.textContent = `₹${grandTotal.toFixed(2)}`;
        }

        // Update bulk discount info panel (services count and amount)
        const bulkServiceCountEl = document.getElementById('bulk-service-count');
        const bulkAmountEl = document.getElementById('bulk-amount');
        const bulkDiscountInfoEl = document.getElementById('bulk-discount-info');

        const bulkAmount = summary.bulk_discount_amount || 0;

        if (bulkServiceCountEl) {
            bulkServiceCountEl.textContent = summary.total_services || 0;
        }
        if (bulkAmountEl) {
            bulkAmountEl.textContent = `Rs. ${bulkAmount.toFixed(2)}`;
        }
        if (bulkDiscountInfoEl && summary.total_services > 0 && bulkAmount > 0) {
            bulkDiscountInfoEl.style.display = 'block';
        } else if (bulkDiscountInfoEl) {
            bulkDiscountInfoEl.style.display = 'none';
        }

        // Update loyalty discount info panel
        const loyaltyCheckbox = document.getElementById('apply-loyalty-discount');
        const loyaltyInfoEl = document.getElementById('loyalty-discount-info');
        const loyaltyAmountEl = document.getElementById('loyalty-amount');
        const loyaltyCardTypeEl = document.getElementById('loyalty-card-type');

        const loyaltyAmount = summary.loyalty_discount_amount || 0;

        if (loyaltyCheckbox && loyaltyAmount > 0) {
            loyaltyCheckbox.checked = true;
            if (loyaltyInfoEl) loyaltyInfoEl.style.display = 'block';
            if (loyaltyAmountEl) loyaltyAmountEl.textContent = `Rs. ${loyaltyAmount.toFixed(2)}`;
            if (loyaltyCardTypeEl && this.currentPatientLoyalty) {
                loyaltyCardTypeEl.textContent = this.currentPatientLoyalty.card_type_name || 'Active';
            }
        } else if (loyaltyCheckbox) {
            loyaltyCheckbox.checked = false;
            if (loyaltyInfoEl) loyaltyInfoEl.style.display = 'none';
        }

        // Update savings badge
        const savingsBadge = document.getElementById('savings-badge');
        if (savingsBadge) {
            if (summary.total_discount > 0) {
                savingsBadge.style.display = 'inline-block';
                savingsBadge.textContent = `You save ₹${summary.total_discount.toFixed(0)}!`;
            } else {
                savingsBadge.style.display = 'none';
            }
        }

        // Update potential savings
        if (summary.potential_savings && summary.potential_savings.applicable) {
            this.showPotentialSavings(summary.potential_savings);
        } else {
            this.hidePotentialSavings();
        }

        // NOTE: updateEligibleDiscountsDisplay() is called from updateLineItemDiscounts()
        // to avoid infinite loop
    }

    /**
     * Show potential savings notification
     */
    showPotentialSavings(potentialSavings) {
        const panel = document.getElementById('potential-savings-panel');
        if (!panel) return;

        panel.style.display = 'block';
        panel.innerHTML = `
            <div class="potential-savings-content">
                <div class="icon">💡</div>
                <div class="message">
                    <strong>Tip:</strong> ${potentialSavings.message}
                    <div class="details">
                        Estimated savings: <strong>₹${potentialSavings.estimated_savings}</strong>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Hide potential savings panel
     */
    hidePotentialSavings() {
        const panel = document.getElementById('potential-savings-panel');
        if (panel) panel.style.display = 'none';
    }

    /**
     * Update discount breakdown display
     */
    updateDiscountBreakdown(lineItems) {
        const breakdown = document.getElementById('bulk-discount-breakdown');
        const text = document.getElementById('discount-breakdown-text');

        if (!breakdown || !text) return;

        // Group discounts by percentage
        const discountGroups = {};

        lineItems.forEach(item => {
            if (item.item_type !== 'Service' || item.discount_percent === 0) return;

            const pct = item.discount_percent;
            const serviceName = this.serviceDiscounts[item.service_id]?.service_name || item.item_name;

            if (!discountGroups[pct]) {
                discountGroups[pct] = [];
            }
            if (!discountGroups[pct].includes(serviceName)) {
                discountGroups[pct].push(serviceName);
            }
        });

        // Format breakdown text
        const breakdownParts = Object.entries(discountGroups).map(([pct, services]) => {
            return `<span class="discount-item">${pct}% off ${services.join(', ')}</span>`;
        });

        if (breakdownParts.length > 0) {
            text.innerHTML = breakdownParts.join(' | ');
            breakdown.style.display = 'block';
        } else {
            breakdown.style.display = 'none';
        }
    }

    /**
     * Add discount badge to line item
     */
    addDiscountBadge(row, type, percent, metadata = null) {
        // Remove existing badges
        const existingBadges = row.querySelectorAll('.discount-badge');
        existingBadges.forEach(badge => badge.remove());

        const discountInput = row.querySelector('.discount-percent');
        if (!discountInput || !discountInput.parentElement) return;

        // Handle bulk_plus_loyalty stacked discount
        if (type === 'bulk_plus_loyalty' && metadata) {
            // Create bulk badge
            const bulkBadge = document.createElement('span');
            bulkBadge.className = 'discount-badge bulk-discount';
            bulkBadge.textContent = `Bulk ${metadata.bulk_percent || 0}%`;
            bulkBadge.style.cssText = `
                display: inline-block;
                background: #3b82f6;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                margin-left: 8px;
                font-weight: 500;
            `;
            discountInput.parentElement.appendChild(bulkBadge);

            // Create loyalty badge
            const loyaltyBadge = document.createElement('span');
            loyaltyBadge.className = 'discount-badge loyalty-discount';
            loyaltyBadge.textContent = `Loyalty ${metadata.loyalty_percent || 0}%`;
            loyaltyBadge.style.cssText = `
                display: inline-block;
                background: #f59e0b;
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                margin-left: 4px;
                font-weight: 500;
            `;
            discountInput.parentElement.appendChild(loyaltyBadge);
            return;
        }

        // Single discount type
        const badge = document.createElement('span');
        badge.className = `discount-badge ${type}-discount`;

        let badgeText = '';
        let badgeColor = '';

        switch(type) {
            case 'bulk':
                badgeText = 'Bulk';
                badgeColor = '#3b82f6'; // Blue
                break;
            case 'loyalty':
                badgeText = `${this.currentPatientLoyalty?.card_type_code || 'Loyalty'} ${percent.toFixed(0)}%`;
                badgeColor = '#f59e0b'; // Amber
                break;
            case 'campaign':
            case 'promotion':
                badgeText = `Promotion ${percent.toFixed(0)}%`;
                badgeColor = '#10b981'; // Green
                break;
            default:
                badgeText = `${percent.toFixed(0)}%`;
                badgeColor = '#6b7280'; // Gray
        }

        badge.textContent = badgeText;
        badge.style.cssText = `
            display: inline-block;
            background: ${badgeColor};
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            margin-left: 8px;
            font-weight: 500;
        `;

        discountInput.parentElement.appendChild(badge);
    }

    /**
     * Display loyalty card badge at header
     */
    displayLoyaltyCardBadge(card) {
        const container = document.getElementById('patient-loyalty-card-display');
        if (!container) return;

        container.innerHTML = `
            <div class="loyalty-card-badge" style="background: ${card.card_color}">
                <span class="card-icon">🎁</span>
                <span class="card-name">${card.card_type_name}</span>
                <span class="card-discount">${card.discount_percent}% discount</span>
            </div>
        `;
        container.style.display = 'block';
    }

    /**
     * Toggle bulk discount manually
     */
    toggleBulkDiscount() {
        const checkbox = document.getElementById('bulk-discount-enabled');

        // Mark that user has manually toggled the checkbox
        this.userToggledCheckbox = true;

        console.log(`User toggled checkbox to: ${checkbox.checked}`);

        // Always call API to recalculate - backend decides which discounts apply
        // Even if bulk is unchecked, loyalty/other discounts should still work
        const lineItems = this.collectLineItems();
        this.applyDiscounts(lineItems);
    }

    /**
     * Recalculate line item totals
     */
    recalculateLineItem(row) {
        const quantity = parseFloat(row.querySelector('.quantity')?.value || 0);
        const unitPrice = parseFloat(row.querySelector('.unit-price')?.value || 0);
        const discountPercent = parseFloat(row.querySelector('.discount-percent')?.value || 0);

        const subtotal = quantity * unitPrice;
        const discountAmount = (subtotal * discountPercent) / 100;
        const lineTotal = subtotal - discountAmount;

        // Update display
        const lineTotalEl = row.querySelector('.line-total-display');
        if (lineTotalEl) {
            lineTotalEl.textContent = `₹${lineTotal.toFixed(2)}`;
        }
    }

    /**
     * Recalculate invoice totals
     */
    recalculateInvoiceTotals() {
        // This should call the existing invoice total calculation function
        if (typeof window.calculateInvoiceTotals === 'function') {
            window.calculateInvoiceTotals();
        }
    }

    /**
     * Validate before form submission
     */
    validateBeforeSubmit() {
        const checkbox = document.getElementById('bulk-discount-enabled');

        if (checkbox && checkbox.checked) {
            const lineItems = this.collectLineItems();
            const serviceItems = lineItems.filter(item => item.item_type === 'Service');
            const serviceCount = serviceItems.reduce((sum, item) => sum + item.quantity, 0);

            // Final validation
            if (serviceCount < this.hospitalConfig.bulk_discount_min_service_count) {
                alert(
                    `Bulk discount requires ${this.hospitalConfig.bulk_discount_min_service_count} services.\n` +
                    `You only have ${serviceCount} service(s) in this invoice.\n\n` +
                    `Please add ${this.hospitalConfig.bulk_discount_min_service_count - serviceCount} more service(s) or uncheck bulk discount.`
                );

                // Auto-uncheck and clear discounts
                checkbox.checked = false;
                this.clearDiscounts();

                return false;  // Prevent form submission
            }
        }

        return true;  // Allow submission
    }

    /**
     * Toggle eligible discounts display section
     */
    toggleEligibleDiscountsDisplay(type) {
        const sectionId = `${type}-eligible-discounts`;
        const section = document.getElementById(sectionId);
        const toggleBtn = document.getElementById(`${type}-eligible-toggle`);

        if (section) {
            const isVisible = section.style.display !== 'none';
            section.style.display = isVisible ? 'none' : 'block';

            // Update button text
            if (toggleBtn) {
                toggleBtn.textContent = isVisible ? 'ℹ️ Details' : '❌ Hide';
            }
        }
    }

    /**
     * Update eligible discounts display from line item metadata
     */
    updateEligibleDiscountsDisplay() {
        console.log('🔍 updateEligibleDiscountsDisplay() called');

        // Collect all metadata from line items
        const allEligibleDiscounts = {
            bulk: [],
            loyalty: [],
            promotion: [],
            standard: []
        };

        const rows = document.querySelectorAll('.line-item-row');

        rows.forEach((row, index) => {
            const metadataInput = row.querySelector('.discount-metadata');
            if (metadataInput && metadataInput.value) {
                try {
                    const metadata = JSON.parse(metadataInput.value);
                    if (metadata.all_eligible_discounts) {
                        console.log(`Row ${index} all_eligible_discounts:`, metadata.all_eligible_discounts);
                        metadata.all_eligible_discounts.forEach(discount => {
                            const type = discount.type || 'standard';
                            if (allEligibleDiscounts[type]) {
                                // Check if we already have this discount
                                const exists = allEligibleDiscounts[type].some(d =>
                                    d.percent === discount.percent && d.reason === discount.reason
                                );
                                if (!exists) {
                                    allEligibleDiscounts[type].push(discount);
                                }
                            }
                        });
                    }
                } catch (e) {
                    console.warn('Failed to parse metadata:', e);
                }
            }
        });

        console.log('Collected eligible discounts:', allEligibleDiscounts);

        // Render each discount type in its own section
        this.renderEligibleDiscounts('bulk', allEligibleDiscounts.bulk);
        this.renderEligibleDiscounts('loyalty', allEligibleDiscounts.loyalty);
        this.renderEligibleDiscounts('standard', allEligibleDiscounts.standard);
        this.renderEligibleDiscounts('promotion', allEligibleDiscounts.promotion);
    }

    /**
     * Render eligible discounts for a specific type
     */
    renderEligibleDiscounts(type, discounts) {
        const listEl = document.getElementById(`${type}-eligible-list`);
        if (!listEl) return;

        if (!discounts || discounts.length === 0) {
            listEl.innerHTML = `<div style="color: #9ca3af; font-style: italic;">No ${type} discounts available</div>`;
            return;
        }

        const html = discounts.map(discount => {
            const icon = discount.applied ? '✅' : '⬜';
            const statusText = discount.applied ? 'Applied' : 'Not Applied';
            const statusColor = discount.applied ? '#10b981' : '#6b7280';

            // Get display name based on type
            let displayName = '';
            if (type === 'promotion') {
                displayName = discount.campaign_name || 'Promotion';
            } else if (type === 'loyalty') {
                displayName = discount.card_type_name || 'Loyalty Card';
            } else {
                displayName = type.charAt(0).toUpperCase() + type.slice(1);
            }

            return `
                <div style="display: flex; align-items: start; padding: 6px 0; border-bottom: 1px solid #e5e7eb;">
                    <span style="font-size: 16px; margin-right: 8px;">${icon}</span>
                    <div style="flex: 1;">
                        <div style="font-weight: 500; color: #111827;">
                            ${displayName}: ${discount.percent}% (₹${discount.amount.toFixed(2)})
                        </div>
                        <div style="font-size: 12px; color: #6b7280; margin-top: 2px;">
                            ${discount.reason || 'Eligible'}
                        </div>
                        <div style="font-size: 11px; color: ${statusColor}; margin-top: 2px; font-weight: 500;">
                            ${statusText}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        listEl.innerHTML = html;
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error(message);
        // TODO: Show user-friendly error notification
        alert(message);
    }
}

// Global instance
window.bulkDiscountManager = null;

/**
 * Initialize bulk discount on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on invoice creation page
    const invoiceForm = document.getElementById('invoice-form');
    if (!invoiceForm) return;

    // Get hospital and patient IDs
    const hospitalId = document.querySelector('[name="hospital_id"]')?.value;
    const patientId = document.querySelector('[name="patient_id"]')?.value;

    if (hospitalId) {
        // Create and initialize manager
        window.bulkDiscountManager = new BulkDiscountManager();
        window.bulkDiscountManager.initialize(hospitalId, patientId);

        // Attach to form submit for validation
        invoiceForm.addEventListener('submit', function(e) {
            if (window.bulkDiscountManager && !window.bulkDiscountManager.validateBeforeSubmit()) {
                e.preventDefault();
                return false;
            }
        });
    }
});
