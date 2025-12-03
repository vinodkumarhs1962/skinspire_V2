// app/static/js/components/buy_x_get_y_handler.js

/**
 * BuyXGetYHandler
 * Manages Buy X Get Y Free promotions during invoice creation
 *
 * Logic:
 * 1. Listens for line item changes (add, remove, quantity change)
 * 2. Checks all line items against active Buy X Get Y campaigns
 * 3. Auto-adds free item lines when trigger conditions are met
 * 4. Auto-removes free item lines when trigger conditions are no longer met
 * 5. Free items have:
 *    - is_free_item = true
 *    - Unit price = 0 (for line total)
 *    - GST calculated on original MRP
 *    - Cannot be edited/removed by user (auto-managed)
 */
class BuyXGetYHandler {
    constructor(options = {}) {
        this.hospitalId = options.hospitalId;
        this.patientId = options.patientId;
        this.invoiceItemComponent = options.invoiceItemComponent;
        this.container = options.container || document.getElementById('line-items-body');

        // Cache for active Buy X Get Y campaigns
        this.campaigns = [];
        this.campaignsLoaded = false;

        // Track free items added by this handler
        // Map: triggerId -> { freeRowId, campaignId, rewardItemId }
        this.freeItemsMap = new Map();

        // Debounce timer
        this.checkDebounceTimer = null;

        // Initialize
        this.init();
    }

    async init() {
        console.log('🎁 BuyXGetYHandler initializing...');

        // Load active Buy X Get Y campaigns
        await this.loadCampaigns();

        // Set up event listeners
        this.setupEventListeners();

        console.log('✅ BuyXGetYHandler initialized');
    }

    async loadCampaigns() {
        try {
            // Build URL with optional patient_id for VIP targeting
            let url = `/api/discount/buy-x-get-y/active?hospital_id=${this.hospitalId}`;
            if (this.patientId) {
                url += `&patient_id=${this.patientId}`;
            }

            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                this.campaigns = data.campaigns || [];
                this.campaignsLoaded = true;
                console.log(`[BuyXGetY] Loaded ${this.campaigns.length} Buy X Get Y campaigns`);
            } else {
                console.warn('[BuyXGetY] Failed to load Buy X Get Y campaigns');
                this.campaigns = [];
            }
        } catch (error) {
            console.error('[BuyXGetY] Error loading campaigns:', error);
            this.campaigns = [];
        }
    }

    setupEventListeners() {
        // Listen for line item events
        document.addEventListener('line-item-changed', () => this.debouncedCheck());
        document.addEventListener('line-item-added', () => this.debouncedCheck());
        document.addEventListener('line-item-removed', () => this.debouncedCheck());

        // Also listen for quantity changes directly
        if (this.container) {
            this.container.addEventListener('change', (e) => {
                if (e.target.classList.contains('quantity')) {
                    this.debouncedCheck();
                }
            });
        }
    }

    debouncedCheck() {
        // Debounce to avoid too many checks
        if (this.checkDebounceTimer) {
            clearTimeout(this.checkDebounceTimer);
        }
        this.checkDebounceTimer = setTimeout(() => {
            this.checkBuyXGetY();
        }, 500);
    }

    /**
     * Main check function - called when line items change
     */
    async checkBuyXGetY() {
        if (!this.campaignsLoaded) {
            console.log('[BuyXGetY] Campaigns not loaded yet, skipping check');
            return;
        }
        if (this.campaigns.length === 0) {
            console.log('[BuyXGetY] No Buy X Get Y campaigns available');
            return;
        }

        console.log(`[BuyXGetY] Checking eligibility with ${this.campaigns.length} campaigns...`);

        // Get excluded campaign IDs from global state
        const excludedIds = window.excludedCampaignIds || [];

        // Get all current line items (excluding free items)
        const lineItems = this.getLineItems();
        const regularItems = lineItems.filter(item => !item.isFreeItem);

        console.log(`📋 Regular items: ${regularItems.length}`);

        // Track which triggers are currently active
        const activeTriggers = new Set();

        // Check each campaign (skip if excluded by user)
        for (const campaign of this.campaigns) {
            // Skip if this campaign is in the excluded list
            if (excludedIds.includes(campaign.campaign_id) || excludedIds.includes(String(campaign.campaign_id))) {
                console.log(`⏭️ Campaign "${campaign.campaign_name}" is excluded by user, skipping`);
                continue;
            }

            const triggerResult = this.checkTrigger(campaign, regularItems);

            if (triggerResult.triggered) {
                console.log(`✅ Campaign "${campaign.campaign_name}" triggered by item ${triggerResult.triggerItemId}`);
                activeTriggers.add(this.getTriggerKey(campaign.campaign_id, triggerResult.triggerItemId));

                // Add free item if not already added
                await this.addFreeItemIfNeeded(campaign, triggerResult);
            }
        }

        // Remove free items that are no longer valid (or if campaign was excluded)
        this.removeInvalidFreeItems(activeTriggers);
    }

    /**
     * Get all line items from the invoice
     */
    getLineItems() {
        if (!this.container) {
            console.warn('[BuyXGetY] Container is null!');
            return [];
        }

        const rows = this.container.querySelectorAll('.line-item-row');
        console.log(`[BuyXGetY] Found ${rows.length} line-item-row elements in container`);
        const items = [];

        rows.forEach((row, index) => {
            const itemId = row.querySelector('.item-id')?.value;
            const itemType = row.querySelector('.item-type')?.value;
            const itemName = row.querySelector('.item-name')?.value;
            const quantity = parseFloat(row.querySelector('.quantity')?.value) || 0;
            const unitPrice = parseFloat(row.querySelector('.unit-price')?.value) || 0;
            const isFreeItem = row.dataset.isFreeItem === 'true';

            console.log(`[BuyXGetY] Row ${index}: itemId=${itemId}, itemType=${itemType}, qty=${quantity}`);

            if (itemId) {
                items.push({
                    rowIndex: index,
                    row: row,
                    itemId: itemId,
                    itemType: this.normalizeItemType(itemType),
                    itemName: itemName,
                    quantity: quantity,
                    unitPrice: unitPrice,
                    total: quantity * unitPrice,
                    isFreeItem: isFreeItem,
                    triggerLineId: row.dataset.triggerLineId
                });
            }
        });

        return items;
    }

    /**
     * Normalize item type to match campaign format
     */
    normalizeItemType(type) {
        const typeMap = {
            'Package': 'package',
            'Service': 'service',
            'OTC': 'medicine',
            'Prescription': 'medicine',
            'Product': 'medicine',
            'Consumable': 'medicine'
        };
        return typeMap[type] || type?.toLowerCase() || '';
    }

    /**
     * Check if campaign trigger conditions are met
     * Updated 2025-12-02: Added detailed logging for debugging
     */
    checkTrigger(campaign, items) {
        const rules = campaign.promotion_rules;
        if (!rules || !rules.trigger) {
            console.log(`[BuyXGetY] Campaign "${campaign.campaign_name}" has no trigger rules`);
            return { triggered: false };
        }

        const trigger = rules.trigger;
        const conditions = trigger.conditions || {};

        if (trigger.type !== 'item_purchase') {
            console.log(`[BuyXGetY] Campaign "${campaign.campaign_name}" trigger type is "${trigger.type}", not item_purchase`);
            return { triggered: false };
        }

        const triggerItemIds = conditions.item_ids || [];
        const triggerItemTypeRaw = conditions.item_type;
        // Normalize the trigger item type the same way as line item types (Added 2025-12-02)
        const triggerItemType = triggerItemTypeRaw ? this.normalizeItemType(triggerItemTypeRaw) : null;
        const minAmount = parseFloat(conditions.min_amount) || 0;
        const minQuantity = parseInt(conditions.min_quantity) || 0;

        console.log(`[BuyXGetY] Checking campaign "${campaign.campaign_name}":`);
        console.log(`   - Trigger item type: "${triggerItemTypeRaw || 'any'}" → normalized: "${triggerItemType || 'any'}"`);
        console.log(`   - Trigger item IDs: ${triggerItemIds.length > 0 ? triggerItemIds.join(', ') : 'any'}`);
        console.log(`   - Min quantity: ${minQuantity}, Min amount: ${minAmount}`);

        // Check each item
        for (const item of items) {
            console.log(`   - Checking item: "${item.itemName}" (type: ${item.itemType}, id: ${item.itemId}, qty: ${item.quantity}, total: ${item.total})`);

            // Check item type match - both sides are now normalized
            if (triggerItemType && item.itemType !== triggerItemType) {
                console.log(`     ✗ Type mismatch: "${item.itemType}" !== "${triggerItemType}"`);
                continue;
            }

            // Check specific item IDs (if specified)
            if (triggerItemIds.length > 0 && !triggerItemIds.includes(item.itemId)) {
                console.log(`     ✗ Item ID not in trigger list`);
                continue;
            }

            // Check minimum amount
            if (minAmount > 0 && item.total >= minAmount) {
                console.log(`     ✓ Triggered by amount: ${item.total} >= ${minAmount}`);
                return {
                    triggered: true,
                    triggerItemId: item.itemId,
                    triggerRowIndex: item.rowIndex,
                    triggerRow: item.row
                };
            }

            // Check minimum quantity
            if (minQuantity > 0 && item.quantity >= minQuantity) {
                console.log(`     ✓ Triggered by quantity: ${item.quantity} >= ${minQuantity}`);
                return {
                    triggered: true,
                    triggerItemId: item.itemId,
                    triggerRowIndex: item.rowIndex,
                    triggerRow: item.row
                };
            }

            // If no min_amount or min_quantity, just matching item is enough
            if (minAmount === 0 && minQuantity === 0) {
                console.log(`     ✓ Triggered (no quantity/amount requirements)`);
                return {
                    triggered: true,
                    triggerItemId: item.itemId,
                    triggerRowIndex: item.rowIndex,
                    triggerRow: item.row
                };
            }

            // Log why it didn't trigger
            if (minQuantity > 0 && item.quantity < minQuantity) {
                console.log(`     ✗ Quantity not met: ${item.quantity} < ${minQuantity}`);
            }
            if (minAmount > 0 && item.total < minAmount) {
                console.log(`     ✗ Amount not met: ${item.total} < ${minAmount}`);
            }
        }

        console.log(`   ✗ No items matched trigger conditions`);
        return { triggered: false };
    }

    /**
     * Generate unique key for trigger tracking
     */
    getTriggerKey(campaignId, triggerItemId) {
        return `${campaignId}::${triggerItemId}`;
    }

    /**
     * Add free item line if not already present
     */
    async addFreeItemIfNeeded(campaign, triggerResult) {
        const triggerKey = this.getTriggerKey(campaign.campaign_id, triggerResult.triggerItemId);

        // Check if already added
        if (this.freeItemsMap.has(triggerKey)) {
            console.log(`🎁 Free item already exists for trigger ${triggerKey}`);
            return;
        }

        const rules = campaign.promotion_rules;
        const reward = rules.reward;

        if (!reward || !reward.items || reward.items.length === 0) {
            console.warn(`Campaign ${campaign.campaign_name} has no reward items`);
            return;
        }

        // Add each reward item
        for (const rewardItem of reward.items) {
            await this.addFreeItemRow(campaign, rewardItem, triggerResult, triggerKey);
        }
    }

    /**
     * Add a single free item row
     */
    async addFreeItemRow(campaign, rewardItem, triggerResult, triggerKey) {
        console.log(`🎁 Adding free item: ${rewardItem.item_id} for campaign ${campaign.campaign_name}`);

        // Fetch item details
        const itemDetails = await this.fetchItemDetails(rewardItem.item_id, rewardItem.item_type);
        if (!itemDetails) {
            console.error(`Failed to fetch details for reward item ${rewardItem.item_id}`);
            return;
        }

        // Add new row using the invoice item component
        const row = this.invoiceItemComponent.addNewItem();

        // Mark as free item
        row.dataset.isFreeItem = 'true';
        row.dataset.triggerLineId = triggerResult.triggerItemId;
        row.dataset.campaignId = campaign.campaign_id;
        row.classList.add('free-item-row', 'bg-green-50', 'dark:bg-green-900/20');

        // Set item type
        const itemTypeSelect = row.querySelector('.item-type');
        itemTypeSelect.value = this.getSelectableItemType(rewardItem.item_type);
        itemTypeSelect.dispatchEvent(new Event('change'));
        itemTypeSelect.disabled = true;

        // Set item details
        row.querySelector('.item-id').value = rewardItem.item_id;
        row.querySelector('.item-name').value = itemDetails.name;
        row.querySelector('.item-search').value = itemDetails.name + ' [FREE]';
        row.querySelector('.item-search').disabled = true;

        // Set quantity
        const qty = rewardItem.quantity || 1;
        row.querySelector('.quantity').value = qty;
        row.querySelector('.quantity').disabled = true;

        // Set unit price to ORIGINAL MRP (for GST calculation on MRP)
        const originalPrice = itemDetails.price || 0;
        row.querySelector('.unit-price').value = originalPrice.toFixed(2);
        row.querySelector('.unit-price').disabled = true;

        // Set GST rate (GST is calculated on original MRP for compliance)
        const gstRate = itemDetails.gst_rate || 0;
        row.querySelector('.gst-rate').value = gstRate;

        // Set discount to 100% (makes line total = 0, but GST calculated on MRP)
        row.querySelector('.discount-percent').value = '100';
        row.querySelector('.discount-percent').disabled = true;

        // Store original price for reference
        row.dataset.originalPrice = originalPrice;

        // Add free item badge
        const nameCell = row.querySelector('.item-search')?.parentElement;
        if (nameCell) {
            const badge = document.createElement('span');
            badge.className = 'ml-2 px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded-full font-medium';
            badge.innerHTML = '<i class="fas fa-gift mr-1"></i>FREE';
            badge.title = campaign.campaign_name;
            nameCell.appendChild(badge);
        }

        // Add reason text
        const reasonText = `${campaign.campaign_name} - ${campaign.campaign_code}`;

        // Hide remove button for free items
        const removeBtn = row.querySelector('.remove-line-item');
        if (removeBtn) {
            removeBtn.style.display = 'none';
        }

        // Store reference
        this.freeItemsMap.set(triggerKey, {
            row: row,
            campaignId: campaign.campaign_id,
            rewardItemId: rewardItem.item_id
        });

        // Calculate line total
        this.invoiceItemComponent.calculateLineTotal(row);
        this.invoiceItemComponent.calculateTotals();

        // Mark campaign as applied in the campaign card (Added 2025-12-02)
        this.markCampaignAsApplied(campaign.campaign_id, true);

        console.log(`✅ Free item added: ${itemDetails.name} for campaign ${campaign.campaign_name}`);
    }

    /**
     * Convert item type to selectable format for the item-type dropdown
     */
    getSelectableItemType(type) {
        if (!type) return 'Service';

        const typeMap = {
            'package': 'Package',
            'Package': 'Package',
            'service': 'Service',
            'Service': 'Service',
            // Medicine subtypes - map to their exact values for the dropdown
            'medicine': 'OTC',
            'Medicine': 'OTC',
            'OTC': 'OTC',
            'otc': 'OTC',
            'Prescription': 'Prescription',
            'prescription': 'Prescription',
            'Product': 'Product',
            'product': 'Product',
            'Consumable': 'Consumable',
            'consumable': 'Consumable'
        };
        return typeMap[type] || type;
    }

    /**
     * Fetch item details from API
     */
    async fetchItemDetails(itemId, itemType) {
        try {
            const response = await fetch(`/api/discount/item/${itemType}/${itemId}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('[BuyXGetY] Error fetching item details:', error);
        }
        return null;
    }

    /**
     * Remove free items that are no longer valid
     */
    removeInvalidFreeItems(activeTriggers) {
        const keysToRemove = [];
        const campaignIdsToUnmark = new Set();

        for (const [key, freeItemInfo] of this.freeItemsMap) {
            if (!activeTriggers.has(key)) {
                console.log(`🗑️ Removing free item for inactive trigger: ${key}`);

                // Track campaign ID to potentially unmark
                campaignIdsToUnmark.add(freeItemInfo.campaignId);

                // Remove the row from DOM
                if (freeItemInfo.row && freeItemInfo.row.parentNode) {
                    freeItemInfo.row.remove();
                }

                keysToRemove.push(key);
            }
        }

        // Clean up map
        for (const key of keysToRemove) {
            this.freeItemsMap.delete(key);
        }

        // Check which campaigns no longer have any active free items
        for (const campaignId of campaignIdsToUnmark) {
            const stillHasActiveItems = Array.from(this.freeItemsMap.values()).some(
                info => info.campaignId === campaignId
            );
            if (!stillHasActiveItems) {
                this.markCampaignAsApplied(campaignId, false);
            }
        }

        // Recalculate totals if any were removed
        if (keysToRemove.length > 0) {
            this.invoiceItemComponent.updateLineNumbers();
            this.invoiceItemComponent.calculateTotals();
        }
    }

    /**
     * Mark a campaign as applied/not-applied in the campaign card display
     * Added 2025-12-02
     * Updated 2025-12-02: Also adds campaign to eligibleCampaigns if not present
     */
    markCampaignAsApplied(campaignId, isApplied) {
        console.log(`🔍 markCampaignAsApplied called: campaignId=${campaignId}, isApplied=${isApplied}`);

        // Find the campaign in our local cache (BuyXGetY campaigns)
        const localCampaign = this.campaigns.find(c =>
            c.campaign_id === campaignId || String(c.campaign_id) === String(campaignId)
        );

        // Initialize arrays if they don't exist
        if (!window.eligibleCampaigns) window.eligibleCampaigns = [];
        if (!window.allAvailableCampaigns) window.allAvailableCampaigns = [];

        // Update in eligibleCampaigns
        let campaign = window.eligibleCampaigns.find(c =>
            c.campaign_id === campaignId || String(c.campaign_id) === String(campaignId)
        );

        // If campaign not found in eligibleCampaigns but exists in our local cache, add it
        if (!campaign && localCampaign && isApplied) {
            console.log(`📥 Adding Buy X Get Y campaign "${localCampaign.campaign_name}" to eligibleCampaigns`);
            const campaignToAdd = {
                ...localCampaign,
                applied: true,
                promotion_type: 'buy_x_get_y'
            };
            window.eligibleCampaigns.push(campaignToAdd);
            window.allAvailableCampaigns.push(campaignToAdd);
            campaign = campaignToAdd;
        }

        if (campaign) {
            campaign.applied = isApplied;
            console.log(`📢 Campaign "${campaign.campaign_name}" marked as ${isApplied ? 'APPLIED' : 'NOT APPLIED'}`);
        } else {
            console.warn(`⚠️ Campaign ${campaignId} not found in eligibleCampaigns or local cache`);
        }

        // Update in allAvailableCampaigns (master list)
        const masterCampaign = window.allAvailableCampaigns.find(c =>
            c.campaign_id === campaignId || String(c.campaign_id) === String(campaignId)
        );
        if (masterCampaign) {
            masterCampaign.applied = isApplied;
        }

        // Re-render the campaign list to show updated applied status
        if (typeof window.renderCampaignList === 'function') {
            window.renderCampaignList();
        }
    }

    /**
     * Get count of active free items
     */
    getFreeItemCount() {
        return this.freeItemsMap.size;
    }

    /**
     * Clear all free items (e.g., when invoice is reset)
     */
    clearAllFreeItems() {
        // Collect campaign IDs to unmark
        const campaignIdsToUnmark = new Set();

        for (const [key, freeItemInfo] of this.freeItemsMap) {
            campaignIdsToUnmark.add(freeItemInfo.campaignId);
            if (freeItemInfo.row && freeItemInfo.row.parentNode) {
                freeItemInfo.row.remove();
            }
        }
        this.freeItemsMap.clear();

        // Unmark all campaigns that had free items
        for (const campaignId of campaignIdsToUnmark) {
            this.markCampaignAsApplied(campaignId, false);
        }
    }
}

// Export for global use
window.BuyXGetYHandler = BuyXGetYHandler;
