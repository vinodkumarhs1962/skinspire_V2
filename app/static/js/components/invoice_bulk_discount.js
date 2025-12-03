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
        this.userToggledCheckbox = false; // Track if user manually toggled bulk checkbox
        this.userToggledLoyaltyCheckbox = false; // Track if user manually toggled loyalty checkbox
        this.userToggledStandardCheckbox = false; // Track if user manually toggled standard checkbox
        this.isProcessing = false; // Prevent re-entry
        this.canEditDiscount = window.CAN_EDIT_DISCOUNT !== undefined ? window.CAN_EDIT_DISCOUNT : true; // Permission to manually edit discount fields
        this.manualPromoCode = null; // Manually entered promo code (Added 2025-11-25)

        // Request tracking to handle race conditions (Added 2025-11-29)
        this.instanceId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        this.latestRequestTimestamp = 0;
        this.invoiceLevelDiscountInProgress = false; // Block updatePricing during VIP/Staff toggle
        console.log('🔧 BulkDiscountManager instance created:', this.instanceId);

        // Staff discretionary discount (Added 2025-11-29)
        this.staffDiscretionaryEnabled = false;
        this.staffDiscretionaryPercent = 0;
        this.staffDiscretionaryNote = '';

        // VIP discount (Added 2025-11-29)
        this.vipEnabled = false;
        this.vipPercent = 0;
        this.vipDiscountType = 'percentage';
        this.vipCampaignId = null;

        // Exclude campaign flag (Added 2025-11-29)
        this.excludeCampaign = false;
        this.excludedCampaignIds = [];  // Array of specific campaign IDs to exclude

        // Bind methods
        this.initialize = this.initialize.bind(this);
        this.updatePricing = this.updatePricing.bind(this);
        this.toggleBulkDiscount = this.toggleBulkDiscount.bind(this);
        this.setManualPromoCode = this.setManualPromoCode.bind(this);
        this.setStaffDiscretionary = this.setStaffDiscretionary.bind(this);
        this.setVipDiscount = this.setVipDiscount.bind(this);
        this.setExcludeCampaign = this.setExcludeCampaign.bind(this);
        this.setExcludedCampaignIds = this.setExcludedCampaignIds.bind(this);
    }

    /**
     * Set manually entered promo code (Added 2025-11-25)
     * This promo will be included in discount calculations
     */
    setManualPromoCode(promoData) {
        this.manualPromoCode = promoData;
        console.log('Manual promo code set:', promoData ? promoData.campaign_code : 'cleared');
    }

    /**
     * Set staff discretionary discount (Added 2025-11-29)
     * This discount stacks incrementally on top of all other discounts
     */
    setStaffDiscretionary(enabled, percent, note = '') {
        this.staffDiscretionaryEnabled = enabled;
        this.staffDiscretionaryPercent = enabled ? parseFloat(percent) || 0 : 0;
        this.staffDiscretionaryNote = note;
        console.log('Staff discretionary set:', enabled ? `${percent}%` : 'disabled', note ? `(${note})` : '');
    }

    /**
     * Set VIP discount (Added 2025-11-29)
     * Invoice-level discount for VIP customers
     */
    setVipDiscount(enabled, percent, discountType = 'percentage', campaignId = null) {
        this.vipEnabled = enabled;
        this.vipPercent = enabled ? parseFloat(percent) || 0 : 0;
        this.vipDiscountType = discountType;
        this.vipCampaignId = campaignId;
        console.log(`🎫 VIP discount set [${this.instanceId}]:`, enabled ? `${percent}% (${discountType})` : 'disabled');
    }

    /**
     * Set exclude campaign flag (Added 2025-11-29)
     * When true, ALL campaign discounts are bypassed
     */
    setExcludeCampaign(exclude) {
        this.excludeCampaign = exclude;
        console.log('Exclude campaign set:', exclude);
    }

    /**
     * Set excluded campaign IDs (Added 2025-11-29)
     * Array of specific campaign IDs to exclude
     */
    setExcludedCampaignIds(campaignIds) {
        this.excludedCampaignIds = campaignIds || [];
        console.log('Excluded campaign IDs:', this.excludedCampaignIds);
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

                // Update loyalty eligible list
                const loyaltyList = document.getElementById('loyalty-eligible-list');
                if (loyaltyList) {
                    loyaltyList.innerHTML = `
                        <div style="display: flex; align-items: center; padding: 8px; background: linear-gradient(90deg, ${data.card.card_color}20, white); border-radius: 6px; border-left: 4px solid ${data.card.card_color};">
                            <span style="font-size: 20px; margin-right: 10px;">🎁</span>
                            <div>
                                <div style="font-weight: 600; color: #1f2937;">${data.card.card_type_name}</div>
                                <div style="font-size: 12px; color: #6b7280;">${data.card.discount_percent}% discount on eligible items</div>
                            </div>
                        </div>
                    `;
                }

                // Enable and check loyalty checkbox
                const loyaltyCheckbox = document.getElementById('apply-loyalty-discount');
                if (loyaltyCheckbox) {
                    loyaltyCheckbox.disabled = false;
                    loyaltyCheckbox.checked = true;
                    console.log('Loyalty checkbox enabled and checked');
                }
            } else {
                this.currentPatientLoyalty = null;

                // Hide loyalty card display
                const loyaltyDisplay = document.getElementById('patient-loyalty-card-display');
                if (loyaltyDisplay) {
                    loyaltyDisplay.style.display = 'none';
                }

                // Update loyalty eligible list
                const loyaltyList = document.getElementById('loyalty-eligible-list');
                if (loyaltyList) {
                    loyaltyList.innerHTML = '<span style="color: #9ca3af; font-style: italic;">Patient has no loyalty card</span>';
                }

                // Disable loyalty checkbox if no card
                const loyaltyCheckbox = document.getElementById('apply-loyalty-discount');
                if (loyaltyCheckbox) {
                    loyaltyCheckbox.disabled = true;
                    loyaltyCheckbox.checked = false;
                }
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

        // Standard discount checkbox toggle
        const standardCheckbox = document.getElementById('apply-standard-discount');
        if (standardCheckbox) {
            standardCheckbox.addEventListener('change', (e) => {
                this.userToggledStandardCheckbox = true;
                this.handleDiscountCheckboxChange('standard', e.target.checked);
            });
        }

        // Loyalty discount checkbox toggle
        const loyaltyCheckbox = document.getElementById('apply-loyalty-discount');
        if (loyaltyCheckbox) {
            loyaltyCheckbox.addEventListener('change', (e) => {
                this.userToggledLoyaltyCheckbox = true;
                this.handleDiscountCheckboxChange('loyalty', e.target.checked);
            });
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
     * Force recalculation for invoice-level discounts (VIP, Staff Special)
     * This bypasses all guard conditions and directly calls the API
     * Added 2025-11-29
     */
    async forceRecalculateInvoiceDiscounts() {
        console.log('='.repeat(60));
        console.log('🔄 forceRecalculateInvoiceDiscounts called [v3]');
        console.log('   VIP enabled:', this.vipEnabled, 'percent:', this.vipPercent);
        console.log('   Staff enabled:', this.staffDiscretionaryEnabled, 'percent:', this.staffDiscretionaryPercent);
        console.log('   isInitialized:', this.isInitialized);
        console.log('   hospitalConfig:', this.hospitalConfig ? 'loaded' : 'not loaded');
        console.log('   instanceId:', this.instanceId);

        // Set flag to block updatePricing() during this operation
        this.invoiceLevelDiscountInProgress = true;

        // Reset all blocking flags
        this.isProcessing = false;
        this.isUpdatingDiscounts = false;

        try {
            // Collect current line items
            const lineItems = this.collectLineItems();
            console.log('   Line items collected:', lineItems.length);

            // If no line items, still show the discount rows with 0 amount
            if (lineItems.length === 0) {
                console.log('   No line items, showing discount rows with 0 amount');
                // Update the display to show 0 amounts
                const vipDiscountRow = document.getElementById('vip-discount-row');
                const staffSpecialRow = document.getElementById('staff-special-discount-row');

                if (this.vipEnabled && vipDiscountRow) {
                    vipDiscountRow.style.display = 'table-row';
                    document.getElementById('vip-discount-percent-display').textContent = this.vipPercent || 0;
                    document.getElementById('vip-discount-amount-display').textContent = '0.00';
                }
                if (this.staffDiscretionaryEnabled && staffSpecialRow) {
                    staffSpecialRow.style.display = 'table-row';
                    document.getElementById('staff-special-percent-display').textContent = this.staffDiscretionaryPercent || 0;
                    document.getElementById('staff-special-amount-display').textContent = '0.00';
                }
                return;
            }

            // Build exclusion flags based on current checkbox states
            const bulkCheckbox = document.getElementById('bulk-discount-enabled');
            const loyaltyCheckbox = document.getElementById('apply-loyalty-discount');
            const standardCheckbox = document.getElementById('apply-standard-discount');

            const excludeBulk = bulkCheckbox ? !bulkCheckbox.checked : false;
            const excludeLoyalty = this.userToggledLoyaltyCheckbox && loyaltyCheckbox && !loyaltyCheckbox.checked;
            const excludeStandard = this.userToggledStandardCheckbox && standardCheckbox && !standardCheckbox.checked;

            // Call API directly
            await this.applyDiscounts(lineItems, { excludeBulk, excludeLoyalty, excludeStandard });
        } finally {
            // Reset the flag after a delay to allow the discount update to complete
            setTimeout(() => {
                this.invoiceLevelDiscountInProgress = false;
                console.log('🔓 Invoice-level discount operation complete');
            }, 500);
        }
    }

    /**
     * Update pricing in real-time
     * MAIN FUNCTION - Called whenever line items change
     */
    async updatePricing() {
        if (!this.isInitialized || !this.hospitalConfig) {
            console.log('updatePricing: Not initialized or no hospital config');
            return;
        }

        // Block during VIP/Staff toggle to prevent race conditions
        if (this.invoiceLevelDiscountInProgress) {
            console.log('⏸️ Invoice-level discount in progress, skipping updatePricing');
            return;
        }

        // Prevent re-entry
        if (this.isProcessing) {
            console.log('Already processing, skipping updatePricing');
            return;
        }

        // Prevent re-trigger during discount update
        if (this.isUpdatingDiscounts) {
            console.log('Currently updating discounts, skipping updatePricing');
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

            // Manage bulk checkbox enable/disable based on line items and eligibility
            if (checkbox) {
                // If no line items at all, disable checkbox
                if (lineItems.length === 0) {
                    checkbox.checked = false;
                    checkbox.disabled = true;
                    this.userToggledCheckbox = false;
                    this.updateEligibilityBadge('not-eligible', 0, this.hospitalConfig.bulk_discount_min_service_count);
                }
                // If has line items with services, manage checkbox based on eligibility
                else if (serviceItems.length > 0) {
                    if (isEligible) {
                        // Eligible - enable checkbox and auto-check if user hasn't manually unchecked
                        checkbox.disabled = false;
                        if (!this.userToggledCheckbox) {
                            checkbox.checked = true;
                        }
                        this.updateEligibilityBadge('eligible', serviceCount);
                    } else {
                        // Not eligible - disable checkbox, uncheck, and reset user toggle
                        // Checkbox stays disabled until threshold is met again
                        checkbox.checked = false;
                        checkbox.disabled = true;
                        this.userToggledCheckbox = false;  // Reset so next eligibility auto-checks
                        const servicesNeeded = this.hospitalConfig.bulk_discount_min_service_count - serviceCount;
                        this.updateEligibilityBadge('not-eligible', serviceCount, servicesNeeded);
                    }
                }
                // Has line items but no services - disable checkbox
                else {
                    checkbox.checked = false;
                    checkbox.disabled = true;
                    this.userToggledCheckbox = false;
                    this.updateEligibilityBadge('not-eligible', 0, this.hospitalConfig.bulk_discount_min_service_count);
                }
            }

            // Apply discounts via API (backend will determine which discounts apply)
            // Pass checkbox states so backend knows which discounts to skip
            // excludeBulk = true when: user manually unchecked AND still eligible, OR not eligible at all
            const excludeBulk = !isEligible || (this.userToggledCheckbox && checkbox && !checkbox.checked);

            // Check loyalty checkbox state
            const loyaltyCheckbox = document.getElementById('apply-loyalty-discount');
            const excludeLoyalty = this.userToggledLoyaltyCheckbox && loyaltyCheckbox && !loyaltyCheckbox.checked;

            // Check standard checkbox state
            const standardCheckbox = document.getElementById('apply-standard-discount');
            const excludeStandard = this.userToggledStandardCheckbox && standardCheckbox && !standardCheckbox.checked;

            await this.applyDiscounts(lineItems, { excludeBulk, excludeLoyalty, excludeStandard });

        } catch (error) {
            console.error('Error updating pricing:', error);
        } finally {
            this.isProcessing = false;
        }
    }

    /**
     * Collect current line items from the invoice form
     * Updated 2025-11-29: Now collects ALL item types (Service, Medicine, Package, etc.)
     * for proper VIP/Staff invoice-level discount calculation
     */
    collectLineItems() {
        const lineItems = [];
        const rows = document.querySelectorAll('.line-item-row');

        console.log(`Collecting line items from ${rows.length} rows`);

        rows.forEach((row, index) => {
            const itemType = row.querySelector('.item-type')?.value;
            if (!itemType) return;

            const itemId = row.querySelector('.item-id')?.value;
            const quantity = parseInt(row.querySelector('.quantity')?.value || 1);
            const unitPrice = parseFloat(row.querySelector('.unit-price')?.value || 0);

            console.log(`Row ${index}: type=${itemType}, id=${itemId}, qty=${quantity}, price=${unitPrice}`);

            // Collect ALL item types (Service, Medicine, Package, etc.)
            // Include items even with unitPrice = 0 for invoice-level discount calculation
            if (itemId) {
                const item = {
                    index: index,
                    item_type: itemType,
                    item_id: itemId,
                    quantity: quantity,
                    unit_price: unitPrice
                };

                // Add type-specific ID field for backward compatibility
                if (itemType === 'Service' || itemType === 'Package') {
                    item.service_id = itemId;
                } else if (itemType === 'Medicine' || itemType === 'OTC' || itemType === 'Prescription' || itemType === 'Product' || itemType === 'Consumable') {
                    item.medicine_id = itemId;
                }

                lineItems.push(item);
                console.log(`  ✓ Added item: ${itemType} - ${itemId} @ Rs.${unitPrice}`);
            } else {
                console.log(`  ✗ Skipped row ${index}: no itemId`);
            }
        });

        console.log(`Collected ${lineItems.length} line items (all types)`);
        return lineItems;
    }

    /**
     * Apply discounts to line items via backend calculation
     * @param {Array} lineItems - Line items to calculate discounts for
     * @param {Object} options - Options for discount calculation
     * @param {boolean} options.excludeBulk - If true, skip bulk discount (user manually unchecked)
     */
    async applyDiscounts(lineItems, options = {}) {
        if (lineItems.length === 0) return;

        // Use timestamp to track this request and handle race conditions
        const thisRequestTimestamp = Date.now();
        this.latestRequestTimestamp = thisRequestTimestamp;
        console.log(`📤 API Request @${thisRequestTimestamp} starting [${this.instanceId}] (VIP=${this.vipEnabled}, Staff=${this.staffDiscretionaryEnabled})`);

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

            // Include manually entered promo code if available
            const manualPromo = this.manualPromoCode;

            const requestData = {
                hospital_id: hospitalId,
                patient_id: patientId,
                line_items: lineItems,
                exclude_bulk: options.excludeBulk || false,
                exclude_loyalty: options.excludeLoyalty || false,
                exclude_standard: options.excludeStandard || false,
                exclude_campaign: this.excludeCampaign || false,  // Added 2025-11-29
                excluded_campaign_ids: this.excludedCampaignIds || [],  // Per-campaign exclusion
                manual_promo_code: manualPromo ? {
                    campaign_id: manualPromo.campaign_id,
                    campaign_code: manualPromo.campaign_code,
                    discount_type: manualPromo.discount_type,
                    discount_value: manualPromo.discount_value
                } : null,
                // Staff discretionary discount (Added 2025-11-29)
                staff_discretionary: this.staffDiscretionaryEnabled ? {
                    enabled: true,
                    percent: this.staffDiscretionaryPercent,
                    note: this.staffDiscretionaryNote
                } : null,
                // VIP discount (Added 2025-11-29)
                vip_discount: this.vipEnabled ? {
                    enabled: true,
                    percent: this.vipPercent,
                    discount_type: this.vipDiscountType,
                    campaign_id: this.vipCampaignId
                } : null
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

            // Check if this response is stale (a newer request has been made)
            if (thisRequestTimestamp < this.latestRequestTimestamp) {
                console.log(`📥 API Response @${thisRequestTimestamp} IGNORED (stale - latest is @${this.latestRequestTimestamp})`);
                return;
            }

            console.log(`📥 API Response @${thisRequestTimestamp} processing [${this.instanceId}]`);

            if (data.success) {
                // Update line items with calculated discounts
                this.updateLineItemDiscounts(data.line_items);

                // Update pricing summary
                this.updatePricingSummary(data.summary);

                // Update discount breakdown
                this.updateDiscountBreakdown(data.line_items);

                // Update eligible campaigns display (Added 2025-11-29)
                // Use mergeMode=true to update applied status while keeping master list
                if (window.updateEligibleCampaigns && data.eligible_campaigns) {
                    window.updateEligibleCampaigns(data.eligible_campaigns, true);
                }

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
        const rowsArray = Array.from(rows);

        console.log(`Updating ${discountedItems.length} line items with discounts`);

        // Set flag to prevent re-triggering updatePricing
        this.isUpdatingDiscounts = true;

        discountedItems.forEach((item) => {
            // Process Services, Medicines (OTC, Prescription, Product, Consumable), and Packages
            const validTypes = ['Service', 'Package', 'Medicine', 'OTC', 'Prescription', 'Product', 'Consumable'];
            if (!validTypes.includes(item.item_type)) return;

            // Use the index from the API response to match the correct row
            // This handles multiple rows with the same service_id/medicine_id
            const itemIndex = item.index;
            let matchedRow = null;

            if (itemIndex !== undefined && itemIndex < rowsArray.length) {
                // Match by index (most reliable for multiple same items)
                matchedRow = rowsArray[itemIndex];
            } else {
                // Fallback: Find row with matching item-id value
                const itemId = item.service_id || item.medicine_id || item.package_id || item.item_id;
                if (!itemId) {
                    console.warn('Item missing item_id:', item);
                    return;
                }
                rowsArray.forEach(row => {
                    const itemIdInput = row.querySelector('.item-id');
                    if (itemIdInput && itemIdInput.value === itemId) {
                        matchedRow = row;
                    }
                });
            }

            if (!matchedRow) {
                console.warn(`No matching row found for item index ${itemIndex}`);
                return;
            }

            // ✅ FIXED AMOUNT DISCOUNT SUPPORT: Check discount type from campaign/item
            // Handle both percentage and fixed_amount discounts
            const discountType = item.discount_type || 'percentage';
            const metadata = item.discount_metadata || {};

            // Determine if we should use amount mode:
            // 1. If campaign discount is fixed_amount (check metadata.discount_value_type)
            // 2. If discount_type itself is fixed_amount
            // 3. If stacked discounts include any fixed_amount component
            // Note: discount_type from service is 'promotion' for campaigns, so check metadata
            const hasFixedAmountComponent = metadata.discount_value_type === 'fixed_amount' ||
                                            discountType === 'fixed_amount';
            const isStackedWithAmount = discountType === 'stacked' &&
                                        metadata.breakdown &&
                                        metadata.breakdown.some(b => b.type === 'fixed_amount');
            const useAmountMode = hasFixedAmountComponent || isStackedWithAmount;

            console.log(`🎯 Applying discount for row ${itemIndex} (${item.item_name}):`, {
                discountType,
                hasFixedAmountComponent,
                isStackedWithAmount,
                useAmountMode,
                discountPercent: item.discount_percent,
                discountAmount: item.discount_amount
            });

            // Get the InvoiceItemComponent instance if available
            const invoiceItemComponent = window.invoiceItemComponent;

            if (useAmountMode && invoiceItemComponent && typeof invoiceItemComponent.setDiscountMode === 'function') {
                // Use fixed amount mode - switch the display and set amount value
                const discountAmount = item.discount_amount || 0;
                invoiceItemComponent.setDiscountMode(matchedRow, 'fixed_amount', discountAmount);
                console.log(`💵 Applied FIXED AMOUNT discount: ₹${discountAmount}`);
            } else {
                // Use percentage mode (default)
                const discountInput = matchedRow.querySelector('.discount-percent');
                if (discountInput) {
                    // Show whole number if no decimals, otherwise 1 decimal
                    const pct = parseFloat(item.discount_percent) || 0;
                    discountInput.value = pct % 1 === 0 ? pct.toFixed(0) : pct.toFixed(1);

                    // If we have invoiceItemComponent, ensure we're in percentage mode
                    if (invoiceItemComponent && typeof invoiceItemComponent.setDiscountMode === 'function') {
                        // Show percentage row, hide amount row (no hidden field needed)
                        const percentRow = matchedRow.querySelector('.discount-percent-row');
                        const amountRow = matchedRow.querySelector('.discount-amount-row');
                        if (percentRow) percentRow.style.display = 'flex';
                        if (amountRow) amountRow.style.display = 'none';
                    }
                    console.log(`📊 Applied PERCENTAGE discount: ${pct}%`);
                } else {
                    console.warn('Discount input not found in row');
                }
            }

            // Clear override flag when auto-discount is applied
            try {
                this.clearDiscountOverride(matchedRow);
            } catch (err) {
                console.warn('Error clearing discount override:', err);
            }

            // Enforce readonly state based on user permission
            const discountInput = matchedRow.querySelector('.discount-percent');
            const discountAmountInput = matchedRow.querySelector('.discount-amount');
            if (!this.canEditDiscount) {
                if (discountInput) {
                    discountInput.setAttribute('readonly', true);
                    discountInput.style.backgroundColor = '#f3f4f6';
                    discountInput.style.cursor = 'not-allowed';
                    discountInput.title = 'Auto-calculated discount (Manager can edit)';
                }
                if (discountAmountInput) {
                    discountAmountInput.setAttribute('readonly', true);
                    discountAmountInput.style.backgroundColor = '#f3f4f6';
                    discountAmountInput.style.cursor = 'not-allowed';
                    discountAmountInput.title = 'Auto-calculated discount (Manager can edit)';
                }
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
            let discountTypeInputEl = matchedRow.querySelector('.discount-type');
            if (!discountTypeInputEl) {
                discountTypeInputEl = document.createElement('input');
                discountTypeInputEl.type = 'hidden';
                discountTypeInputEl.className = 'discount-type';
                matchedRow.appendChild(discountTypeInputEl);
            }
            discountTypeInputEl.value = item.discount_type || 'none';

            // Add discount badge with tooltip showing breakdown (pass metadata for stacked discounts)
            this.addDiscountBadge(matchedRow, item.discount_type, item.discount_percent, item.discount_metadata);

            // Trigger input event to recalculate line total (but not updatePricing)
            if (discountInput) discountInput.dispatchEvent(new Event('input', { bubbles: true }));
        });

        console.log('Discount update complete');

        // Update eligible discounts display after all line items are updated
        this.updateEligibleDiscountsDisplay();

        // Recalculate invoice totals once after all discounts are applied
        this.recalculateInvoiceTotals();

        // Reset flag after a short delay to allow event handlers to complete
        setTimeout(() => {
            this.isUpdatingDiscounts = false;
        }, 100);
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
            const discountTypeInput = row.querySelector('.discount-type');
            const discountType = discountTypeInput?.value || '';

            if (discountInput) {
                // Check if this row has bulk-related discount
                // Includes: bulk, bulk_plus_loyalty, stacked (when bulk is part of it)
                const hasBulkDiscount = discountType.includes('bulk') ||
                    discountType === 'stacked' ||
                    row.querySelector('.discount-badge.bulk-discount');

                if (hasBulkDiscount && parseFloat(discountInput.value) > 0) {
                    console.log(`Clearing discount from row (type: ${discountType})`);
                    discountInput.value = '0';

                    // Remove all badges
                    const badges = row.querySelectorAll('.discount-badge');
                    badges.forEach(badge => badge.remove());

                    // Clear discount type
                    if (discountTypeInput) discountTypeInput.value = 'none';

                    // Mark this row as having staff override
                    this.setDiscountOverride(row, true);

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
     * Set discount override flag on a row
     * This tells the backend to preserve staff's manual discount instead of recalculating
     */
    setDiscountOverride(row, isOverride) {
        // Find or create the override hidden input
        const rowIndex = row.dataset.index || Array.from(row.parentNode.children).indexOf(row);
        let overrideInput = row.querySelector('.discount-override');

        if (!overrideInput) {
            overrideInput = document.createElement('input');
            overrideInput.type = 'hidden';
            overrideInput.className = 'discount-override';
            overrideInput.name = `line_items-${rowIndex}-discount_override`;
            row.appendChild(overrideInput);
        }

        overrideInput.value = isOverride ? 'true' : 'false';
        console.log(`Row ${rowIndex}: discount_override = ${isOverride}`);
    }

    /**
     * Clear discount override when auto-discount is applied
     */
    clearDiscountOverride(row) {
        this.setDiscountOverride(row, false);
    }

    /**
     * Handle discount checkbox change (Standard, Loyalty, etc.)
     * When staff unchecks a discount type, mark affected rows as overridden
     */
    handleDiscountCheckboxChange(discountType, isChecked) {
        console.log(`Discount checkbox changed: ${discountType} = ${isChecked}`);

        if (!isChecked) {
            // Staff unchecked - clear discount for ALL rows (backend will handle exclusion)
            const rows = document.querySelectorAll('.line-item-row');
            rows.forEach(row => {
                const discountTypeInput = row.querySelector('.discount-type');
                const currentDiscountType = discountTypeInput ? discountTypeInput.value : '';

                // Check if this row has the discount type being toggled
                const matchesType = currentDiscountType === discountType ||
                    (discountType === 'standard' && currentDiscountType === 'standard') ||
                    (discountType === 'loyalty' && (currentDiscountType === 'loyalty' || currentDiscountType === 'loyalty_percent'));

                if (matchesType) {
                    // Set override and clear discount
                    this.setDiscountOverride(row, true);
                    const discountInput = row.querySelector('.discount-percent');
                    if (discountInput) {
                        discountInput.value = '0';
                        discountInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                    // Clear discount type and badges
                    if (discountTypeInput) discountTypeInput.value = 'none';
                    const badges = row.querySelectorAll('.discount-badge');
                    badges.forEach(badge => badge.remove());
                    console.log(`Row with ${discountType} discount - override set, discount cleared`);
                }
            });
            // Recalculate totals (this calls backend with exclusion flags)
            this.updatePricing();
        } else {
            // Staff checked - clear overrides and recalculate from backend
            const rows = document.querySelectorAll('.line-item-row');
            rows.forEach(row => {
                this.clearDiscountOverride(row);
            });
            this.updatePricing();
        }
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

        // Only auto-update checkbox if user hasn't manually toggled it
        if (loyaltyCheckbox && !this.userToggledLoyaltyCheckbox) {
            if (loyaltyAmount > 0) {
                loyaltyCheckbox.checked = true;
                if (loyaltyInfoEl) loyaltyInfoEl.style.display = 'block';
                if (loyaltyAmountEl) loyaltyAmountEl.textContent = `Rs. ${loyaltyAmount.toFixed(2)}`;
                if (loyaltyCardTypeEl && this.currentPatientLoyalty) {
                    loyaltyCardTypeEl.textContent = this.currentPatientLoyalty.card_type_name || 'Active';
                }
            } else {
                loyaltyCheckbox.checked = false;
                if (loyaltyInfoEl) loyaltyInfoEl.style.display = 'none';
            }
        } else if (loyaltyCheckbox && this.userToggledLoyaltyCheckbox) {
            // User manually toggled - just update the info display, not the checkbox
            if (loyaltyInfoEl) {
                loyaltyInfoEl.style.display = loyaltyAmount > 0 ? 'block' : 'none';
            }
            if (loyaltyAmountEl && loyaltyAmount > 0) {
                loyaltyAmountEl.textContent = `Rs. ${loyaltyAmount.toFixed(2)}`;
            }
        }

        // Update invoice-level discounts display (Added 2025-11-29)
        const invoiceDiscounts = summary.invoice_level_discounts || {};
        console.log('📊 Invoice-level discounts from API:', invoiceDiscounts);

        // Use manager's internal flags to determine visibility (more reliable than DOM state)
        // This avoids race conditions where API response arrives after checkbox is toggled
        const vipIsEnabled = this.vipEnabled;
        const staffIsEnabled = this.staffDiscretionaryEnabled;
        console.log('📊 Manager flags:', { vipIsEnabled, staffIsEnabled });

        // VIP Discount - Update both the info card and the totals row
        const vipDiscountInfoEl = document.getElementById('vip-discount-info');
        const vipDiscountRow = document.getElementById('vip-discount-row');
        const vipAmount = invoiceDiscounts.vip_discount_amount || 0;
        const vipPercent = invoiceDiscounts.vip_discount_percent || 0;
        console.log('📊 VIP discount:', { vipAmount, vipPercent, rowFound: !!vipDiscountRow, enabled: vipIsEnabled });

        if (vipDiscountInfoEl) {
            if (vipAmount > 0 || vipIsEnabled) {
                vipDiscountInfoEl.style.display = 'block';
                vipDiscountInfoEl.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 12px; color: #92400e;">Applied on subtotal (${vipPercent || this.vipPercent}%)</span>
                        <span style="font-weight: 600; color: #d97706;">- Rs. ${vipAmount.toFixed(2)}</span>
                    </div>
                `;
            } else {
                vipDiscountInfoEl.style.display = 'none';
            }
        }

        // Update VIP row in totals table - keep visible if enabled
        if (vipDiscountRow) {
            if (vipIsEnabled) {
                vipDiscountRow.style.display = 'table-row';
                document.getElementById('vip-discount-percent-display').textContent = vipPercent || this.vipPercent || 0;
                document.getElementById('vip-discount-amount-display').textContent = vipAmount > 0 ? vipAmount.toFixed(2) : '0.00';
            } else {
                vipDiscountRow.style.display = 'none';
            }
        }

        // Staff Discretionary Discount - Update both the info card and the totals row
        const staffDiscretionaryInfoEl = document.getElementById('staff-discretionary-info');
        const staffSpecialRow = document.getElementById('staff-special-discount-row');
        const staffAmount = invoiceDiscounts.staff_discretionary_amount || 0;
        const staffPercent = invoiceDiscounts.staff_discretionary_percent || 0;
        console.log('📊 Staff discount:', { staffAmount, staffPercent, rowFound: !!staffSpecialRow, enabled: staffIsEnabled });

        if (staffDiscretionaryInfoEl) {
            if (staffAmount > 0 || staffIsEnabled) {
                staffDiscretionaryInfoEl.style.display = 'block';
                staffDiscretionaryInfoEl.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 12px; color: #6d28d9;">Applied on subtotal (${staffPercent || this.staffDiscretionaryPercent}%)</span>
                        <span style="font-weight: 600; color: #7c3aed;">- Rs. ${staffAmount.toFixed(2)}</span>
                    </div>
                `;
            } else {
                staffDiscretionaryInfoEl.style.display = 'none';
            }
        }

        // Update Staff Special row in totals table - keep visible if enabled
        if (staffSpecialRow) {
            if (staffIsEnabled) {
                staffSpecialRow.style.display = 'table-row';
                document.getElementById('staff-special-percent-display').textContent = staffPercent || this.staffDiscretionaryPercent || 0;
                document.getElementById('staff-special-amount-display').textContent = staffAmount > 0 ? staffAmount.toFixed(2) : '0.00';
            } else {
                staffSpecialRow.style.display = 'none';
            }
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

        // Update totals display to reflect invoice-level discounts (Added 2025-11-29)
        // Use requestAnimationFrame to ensure DOM updates are complete
        if (typeof updateTotalsDisplay === 'function') {
            requestAnimationFrame(() => {
                updateTotalsDisplay();
            });
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
     * Shows a simple badge (BULK, PROMO, LOYALTY, MIXED) with hover tooltip for details
     * ✅ FIXED AMOUNT SUPPORT: Handles both percentage and fixed_amount discounts
     */
    addDiscountBadge(row, type, percent, metadata = null) {
        // Remove existing badges
        const existingBadges = row.querySelectorAll('.discount-badge');
        existingBadges.forEach(badge => badge.remove());

        // Find discount input - could be either percent or amount depending on mode
        const discountPercentInput = row.querySelector('.discount-percent');
        const discountAmountInput = row.querySelector('.discount-amount');
        const badgeRowEl = row.querySelector('.discount-badge-row');

        // Find a suitable parent element for the badge
        if (!badgeRowEl && !discountPercentInput?.parentElement && !discountAmountInput?.parentElement) return;

        // ✅ Check if this is a fixed_amount discount
        const isFixedAmount = metadata?.discount_value_type === 'fixed_amount' ||
                             (type === 'fixed_amount') ||
                             (type === 'campaign' && metadata?.discount_value_type === 'fixed_amount');
        const discountAmount = metadata?.discount_amount || 0;

        // Determine badge text, color and tooltip
        let badgeText = '';
        let badgeColor = '';
        let tooltipText = '';

        // Handle bulk_plus_loyalty stacked discount
        if (type === 'bulk_plus_loyalty' && metadata) {
            badgeText = 'MIXED';
            badgeColor = '#8b5cf6'; // Purple
            tooltipText = `Bulk: ${metadata.bulk_percent || 0}%\nLoyalty: ${metadata.loyalty_percent || 0}%\nTotal: ${percent.toFixed(1)}%`;
        }
        // Handle stacked discounts with breakdown (may include mixed types)
        else if (type === 'stacked' && metadata && metadata.breakdown && metadata.breakdown.length > 0) {
            badgeText = 'MIXED';
            badgeColor = '#8b5cf6'; // Purple
            // Check if any component is fixed_amount
            const hasFixedAmount = metadata.breakdown.some(item => item.type === 'fixed_amount');
            if (hasFixedAmount) {
                // Show amounts for stacked discounts with fixed_amount components
                tooltipText = metadata.breakdown.map(item => {
                    let label = item.source;
                    switch(item.source) {
                        case 'bulk': label = 'Bulk'; break;
                        case 'loyalty': label = this.currentPatientLoyalty?.card_type_code || 'Loyalty'; break;
                        case 'campaign': label = 'Promo'; break;
                        case 'vip': label = 'VIP'; break;
                    }
                    // Show amount for fixed_amount, percentage for percentage
                    if (item.type === 'fixed_amount') {
                        return `${label}: ₹${(item.amount || 0).toFixed(2)}`;
                    } else {
                        return `${label}: ${(item.percent || 0).toFixed(1)}% (₹${(item.amount || 0).toFixed(2)})`;
                    }
                }).join('\n') + `\nTotal: ₹${(metadata.total_amount || discountAmount).toFixed(2)}`;
            } else {
                tooltipText = metadata.breakdown.map(item => {
                    let label = item.source;
                    switch(item.source) {
                        case 'bulk': label = 'Bulk'; break;
                        case 'loyalty': label = this.currentPatientLoyalty?.card_type_code || 'Loyalty'; break;
                        case 'campaign': label = 'Promo'; break;
                        case 'vip': label = 'VIP'; break;
                    }
                    return `${label}: ${item.percent.toFixed(1)}%`;
                }).join('\n') + `\nTotal: ${percent.toFixed(1)}%`;
            }
        }
        // ✅ Fixed amount discount (single type)
        else if (isFixedAmount || type === 'fixed_amount') {
            badgeText = 'PROMO';
            badgeColor = '#10b981'; // Green
            tooltipText = `Promotional discount: ₹${discountAmount.toFixed(2)}`;
        }
        // Single discount types (percentage)
        else {
            switch(type) {
                case 'bulk':
                    badgeText = 'BULK';
                    badgeColor = '#3b82f6'; // Blue
                    tooltipText = `Bulk discount: ${percent.toFixed(1)}%`;
                    break;
                case 'loyalty':
                case 'loyalty_percent':
                    badgeText = this.currentPatientLoyalty?.card_type_code || 'LOYALTY';
                    badgeColor = '#f59e0b'; // Amber
                    tooltipText = `Loyalty discount: ${percent.toFixed(1)}%`;
                    break;
                case 'campaign':
                case 'promotion':
                    badgeText = 'PROMO';
                    badgeColor = '#10b981'; // Green
                    tooltipText = `Promotional discount: ${percent.toFixed(1)}%`;
                    break;
                case 'standard':
                    badgeText = 'STD';
                    badgeColor = '#6b7280'; // Gray
                    tooltipText = `Standard discount: ${percent.toFixed(1)}%`;
                    break;
                default:
                    badgeText = type ? type.toUpperCase().substring(0, 5) : 'DISC';
                    badgeColor = '#6b7280'; // Gray
                    tooltipText = `Discount: ${percent.toFixed(1)}%`;
            }
        }

        // Create single compact badge with styled tooltip
        const badge = document.createElement('span');
        badge.className = `discount-badge ${type}-discount`;
        badge.textContent = badgeText;
        badge.style.cssText = `
            display: block;
            background: ${badgeColor};
            color: white;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 9px;
            margin-top: 4px;
            font-weight: 600;
            cursor: help;
            white-space: nowrap;
            position: relative;
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
        `;

        // Create styled tooltip
        const tooltip = document.createElement('div');
        tooltip.className = 'discount-tooltip';
        tooltip.style.cssText = `
            display: none;
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #1f2937;
            color: white;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 13px;
            white-space: nowrap;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            margin-bottom: 6px;
        `;

        // Helper to format percent - show 1 decimal only if needed
        const formatPct = (val) => {
            const num = parseFloat(val) || 0;
            return num % 1 === 0 ? num.toFixed(0) + '%' : num.toFixed(1) + '%';
        };

        // Helper to format amount
        const formatAmt = (val) => {
            const num = parseFloat(val) || 0;
            return '₹' + num.toFixed(2);
        };

        // Build tooltip content with colored badges
        let tooltipHTML = '';
        if (type === 'bulk_plus_loyalty' && metadata) {
            tooltipHTML = `
                <div style="margin-bottom:6px;"><span style="background:#3b82f6;color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">BULK</span> ${formatPct(metadata.bulk_percent)}</div>
                <div style="margin-bottom:6px;"><span style="background:#f59e0b;color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">LOYALTY</span> ${formatPct(metadata.loyalty_percent)}</div>
                <div style="border-top:1px solid #4b5563;padding-top:6px;margin-top:6px;font-weight:600;">Total: ${formatPct(percent)}</div>
            `;
        } else if (type === 'stacked' && metadata && metadata.breakdown && metadata.breakdown.length > 0) {
            // Check if any component is fixed_amount
            const hasFixedAmount = metadata.breakdown.some(item => item.type === 'fixed_amount');
            tooltipHTML = metadata.breakdown.map(item => {
                let label = item.source;
                let color = '#6b7280';
                switch(item.source) {
                    case 'bulk': label = 'BULK'; color = '#3b82f6'; break;
                    case 'loyalty': label = this.currentPatientLoyalty?.card_type_code || 'LOYALTY'; color = '#f59e0b'; break;
                    case 'campaign': label = 'PROMO'; color = '#10b981'; break;
                    case 'vip': label = 'VIP'; color = '#ec4899'; break;
                }
                // ✅ Show amount for fixed_amount, percentage with amount for percentage
                if (item.type === 'fixed_amount') {
                    return `<div style="margin-bottom:6px;"><span style="background:${color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">${label}</span> ${formatAmt(item.amount)}</div>`;
                } else if (hasFixedAmount) {
                    // When mixed, show both % and amount for clarity
                    return `<div style="margin-bottom:6px;"><span style="background:${color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">${label}</span> ${formatPct(item.percent)} (${formatAmt(item.amount)})</div>`;
                } else {
                    return `<div style="margin-bottom:6px;"><span style="background:${color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">${label}</span> ${formatPct(item.percent)}</div>`;
                }
            }).join('');
            // Total line - show amount if mixed, percentage otherwise
            if (hasFixedAmount) {
                tooltipHTML += `<div style="border-top:1px solid #4b5563;padding-top:6px;margin-top:6px;font-weight:600;">Total: ${formatAmt(metadata.total_amount || discountAmount)}</div>`;
            } else {
                tooltipHTML += `<div style="border-top:1px solid #4b5563;padding-top:6px;margin-top:6px;font-weight:600;">Total: ${formatPct(percent)}</div>`;
            }
        } else if (isFixedAmount || type === 'fixed_amount') {
            // ✅ Fixed amount single discount - show amount
            tooltipHTML = `<div><span style="background:${badgeColor};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">${badgeText}</span> ${formatAmt(discountAmount)}</div>`;
        } else {
            tooltipHTML = `<div><span style="background:${badgeColor};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">${badgeText}</span> ${formatPct(percent)}</div>`;
        }
        tooltip.innerHTML = tooltipHTML;

        badge.appendChild(tooltip);

        // Show/hide tooltip on hover
        badge.addEventListener('mouseenter', () => { tooltip.style.display = 'block'; });
        badge.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });

        // Append to badge row if exists, otherwise to parent
        const badgeRow = row.querySelector('.discount-badge-row');
        if (badgeRow) {
            badgeRow.appendChild(badge);
        } else {
            discountInput.parentElement.appendChild(badge);
        }
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

        // If user unchecked bulk discount, mark rows with bulk discount as overridden
        if (!checkbox.checked) {
            // Use the clearDiscounts method which handles all bulk-related discount types
            this.clearDiscounts();
        } else {
            // User re-checked - clear overrides for bulk discount rows and recalculate
            const rows = document.querySelectorAll('.line-item-row');
            rows.forEach(row => {
                const overrideInput = row.querySelector('.discount-override');
                if (overrideInput && overrideInput.value === 'true') {
                    this.clearDiscountOverride(row);
                }
            });

            // Always call API to recalculate - backend decides which discounts apply
            const lineItems = this.collectLineItems();
            this.applyDiscounts(lineItems);
        }
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
        // Create and initialize manager (Singleton pattern with lock to prevent race conditions)
        if (!window.bulkDiscountManager && !window._bulkDiscountManagerCreating) {
            window._bulkDiscountManagerCreating = true;
            window.bulkDiscountManager = new BulkDiscountManager();
            window.bulkDiscountManager.initialize(hospitalId, patientId);
            console.log('✅ BulkDiscountManager initialized from JS file (singleton)');
        } else if (window.bulkDiscountManager) {
            console.log('⚠️ BulkDiscountManager already exists, skipping JS initialization');
        } else {
            console.log('⏳ BulkDiscountManager creation in progress, skipping JS initialization');
        }

        // Attach to form submit for validation (only once)
        if (!window._bulkDiscountFormSubmitAttached) {
            window._bulkDiscountFormSubmitAttached = true;
            invoiceForm.addEventListener('submit', function(e) {
                if (window.bulkDiscountManager && !window.bulkDiscountManager.validateBeforeSubmit()) {
                    e.preventDefault();
                    return false;
                }
            });
        }
    }
});
