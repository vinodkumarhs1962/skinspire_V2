// app/static/js/components/invoice_item.js

/**
 * InvoiceItemComponent
 * Manages invoice line items
 */
class InvoiceItemComponent {
    constructor(options) {
      this.container = document.getElementById(options.containerId);
      this.template = document.getElementById(options.templateId);
      this.noItemsRow = document.getElementById(options.noItemsRowId);
      this.addButton = document.getElementById(options.addButtonId);
      this.itemCount = 0;

      // Initialize batch mode from user preference (passed from template)
      // Default to 'manual' if not specified
      const toggleElement = document.getElementById('batch-mode-toggle');
      this.batchMode = toggleElement ? toggleElement.dataset.mode : 'manual';

      // Bind methods
      this.addNewItem = this.addNewItem.bind(this);
      this.removeItem = this.removeItem.bind(this);
      this.saveItem = this.saveItem.bind(this);
      this.updateLineNumbers = this.updateLineNumbers.bind(this);
      this.calculateTotals = this.calculateTotals.bind(this);

      // Initialize
      this.initEventListeners();
    }
    
    initEventListeners() {
      // Add item button
      if (this.addButton) {
        this.addButton.addEventListener('click', this.addNewItem);
      }
      
      // Event delegation for row actions
      if (this.container) {
        console.log('📦 Container found for event delegation:', this.container.id);
        this.container.addEventListener('click', (e) => {
          const target = e.target;
          console.log('🖱️ Click detected on:', target.tagName, target.className);

          // Handle delete button
          if (target.closest('.remove-line-item')) {
            this.removeItem(target.closest('.line-item-row'));
          }

          // Handle save button
          if (target.closest('.save-line-item')) {
            this.saveItem(target.closest('.line-item-row'));
          }

          // Handle free/sample dropdown toggle
          if (target.closest('.free-sample-toggle')) {
            console.log('🎁 Free/Sample toggle clicked');
            e.stopPropagation();
            this.toggleFreeSampleMenu(target.closest('.line-item-row'));
          }

          // Handle free item option
          if (target.closest('.free-item-option')) {
            this.setFreeItem(target.closest('.line-item-row'));
          }

          // Handle sample item option
          if (target.closest('.sample-item-option')) {
            this.setSampleItem(target.closest('.line-item-row'));
          }

          // Handle clear free/sample status
          if (target.closest('.clear-free-sample-option')) {
            this.clearFreeSampleStatus(target.closest('.line-item-row'));
          }
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
          if (!e.target.closest('.free-sample-dropdown')) {
            document.querySelectorAll('.free-sample-menu').forEach(menu => {
              menu.classList.add('hidden');
            });
          }
        });
        
        // Event delegation for input changes
        this.container.addEventListener('input', (e) => {
          if (e.target.matches('.quantity, .unit-price, .discount-percent, .discount-amount')) {
            this.calculateLineTotal(e.target.closest('.line-item-row'));
            this.calculateTotals();
            // Notify bulk discount manager of line item changes
            document.dispatchEvent(new Event('line-item-changed'));
          }
        });
      }
    }
    
    addNewItem() {
      // Hide the "no items" row if exists
      if (this.noItemsRow) {
        this.noItemsRow.style.display = 'none';
      }

      // Create new row from template
      const content = this.template.content.cloneNode(true);
      const row = content.querySelector('.line-item-row');

      // Replace {index} placeholders
      const currentIndex = this.itemCount;
      row.innerHTML = row.innerHTML.replace(/{index}/g, currentIndex);

      // Add to container
      this.container.appendChild(row);

      // Initialize row
      this.initRow(row);

      // Update line numbers and calculate totals
      this.updateLineNumbers();
      this.calculateTotals();

      // Increment counter
      this.itemCount++;

      // Notify bulk discount manager of line item addition (Added 2025-11-29)
      document.dispatchEvent(new Event('line-item-added'));

      // Return the row for programmatic access (e.g., preserving line items on error)
      return row;
    }

    // Alias for addNewItem (used by restoration code)
    addLineItem() {
      return this.addNewItem();
    }
    
    removeItem(row) {
      if (!row) return;

      // Remove row from DOM
      row.remove();

      // Show "no items" row if empty
      if (this.container.querySelectorAll('.line-item-row').length === 0 && this.noItemsRow) {
        this.noItemsRow.style.display = '';
      }

      // Update line numbers and recalculate totals
      this.updateLineNumbers();
      this.calculateTotals();

      // Notify bulk discount manager of line item removal
      // This triggers recalculation of bulk discount eligibility
      document.dispatchEvent(new Event('line-item-removed'));
    }
    
    saveItem(row) {
      if (!row) return;
      
      // Validate required fields
      const itemId = row.querySelector('.item-id').value;
      const itemName = row.querySelector('.item-name').value;
      
      if (!itemId || !itemName) {
        alert('Please select a valid item');
        return;
      }
      
      // For medicine-based types, validate batch (skip for sample items)
      const itemType = row.querySelector('.item-type').value;
      const isSample = row.querySelector('.is-sample')?.value === 'true';
      const medicineBasedTypes = ['OTC', 'Prescription', 'Product', 'Consumable'];
      if (medicineBasedTypes.includes(itemType) && !isSample) {
        const batch = row.querySelector('.batch-select').value;
        if (!batch) {
          alert('Please select a batch for this item');
          return;
        }
      }
      
      // Mark row as saved
      row.classList.add('saved');
      
      // Update UI to show saved state
      const saveButton = row.querySelector('.save-line-item');
      if (saveButton) {
        saveButton.classList.add('text-gray-400');
        saveButton.classList.remove('text-green-500', 'hover:text-green-700');
        saveButton.setAttribute('disabled', 'disabled');
      }
      
      // Recalculate totals
      this.calculateLineTotal(row);
      this.calculateTotals();
    }

    /**
     * Toggle free/sample dropdown menu
     */
    toggleFreeSampleMenu(row) {
      console.log('🎁 toggleFreeSampleMenu called, row:', row);
      if (!row) return;
      const menu = row.querySelector('.free-sample-menu');
      console.log('🎁 Menu element found:', menu);
      if (menu) {
        // Close all other menus first
        document.querySelectorAll('.free-sample-menu').forEach(m => {
          if (m !== menu) m.classList.add('hidden');
        });
        menu.classList.toggle('hidden');
        console.log('🎁 Menu visibility toggled, hidden:', menu.classList.contains('hidden'));
      }
    }

    /**
     * Set item as FREE (Promotional) - GST calculated on MRP, 100% discount
     */
    setFreeItem(row) {
      if (!row) return;

      const itemId = row.querySelector('.item-id')?.value;
      if (!itemId) {
        alert('Please select an item first.');
        return;
      }

      const reason = prompt('Free Item Reason:\n(e.g., "Promotional offer", "Customer loyalty reward")', '');
      if (reason === null) return;

      // Close menu
      row.querySelector('.free-sample-menu')?.classList.add('hidden');

      // Get elements
      const isFreeItemInput = row.querySelector('.is-free-item');
      const freeItemReasonInput = row.querySelector('.free-item-reason');
      const isSampleInput = row.querySelector('.is-sample');
      const sampleReasonInput = row.querySelector('.sample-reason');
      const unitPriceInput = row.querySelector('.unit-price');
      const discountInput = row.querySelector('.discount-percent');
      const toggleBtn = row.querySelector('.free-sample-toggle i');

      // Store original values
      row.dataset.originalPrice = unitPriceInput?.value || '0';
      row.dataset.originalDiscount = discountInput?.value || '0';
      row.dataset.originalGstRate = row.querySelector('.gst-rate')?.value || '0';

      // Set free item state (keep price, 100% discount, GST on MRP)
      console.log('🎁 Setting free item - isFreeItemInput found:', !!isFreeItemInput);
      if (isFreeItemInput) {
        isFreeItemInput.value = 'true';
        console.log('🎁 Set is-free-item to:', isFreeItemInput.value);
      }
      if (freeItemReasonInput) freeItemReasonInput.value = reason || 'Promotional free item';
      if (isSampleInput) isSampleInput.value = 'false';
      if (sampleReasonInput) sampleReasonInput.value = '';

      // Keep original price (for GST calculation), set 100% discount
      if (discountInput) {
        discountInput.value = '100';
        discountInput.disabled = true;
      }
      if (unitPriceInput) unitPriceInput.disabled = true;

      // Update icon and styling
      if (toggleBtn) {
        toggleBtn.className = 'fas fa-gift text-sm text-green-600';
      }
      row.classList.remove('sample-item-row', 'bg-purple-50', 'dark:bg-purple-900/20');
      row.classList.add('free-item-row', 'bg-green-50', 'dark:bg-green-900/20');

      // Add badge
      this.addStatusBadge(row, 'FREE', 'green', 'fa-gift', reason);

      console.log(`🎁 Item marked as FREE: ${row.querySelector('.item-name')?.value}`);

      this.calculateLineTotal(row);
      this.calculateTotals();
      document.dispatchEvent(new Event('line-item-changed'));
    }

    /**
     * Set item as SAMPLE - No GST, price = 0
     */
    setSampleItem(row) {
      if (!row) return;

      const itemId = row.querySelector('.item-id')?.value;
      if (!itemId) {
        alert('Please select an item first.');
        return;
      }

      const reason = prompt('Sample/Trial Reason:\n(e.g., "Product trial", "New treatment trial with consent")', '');
      if (reason === null) return;

      // Close menu
      row.querySelector('.free-sample-menu')?.classList.add('hidden');

      // Get elements
      const isFreeItemInput = row.querySelector('.is-free-item');
      const freeItemReasonInput = row.querySelector('.free-item-reason');
      const isSampleInput = row.querySelector('.is-sample');
      const sampleReasonInput = row.querySelector('.sample-reason');
      const unitPriceInput = row.querySelector('.unit-price');
      const discountInput = row.querySelector('.discount-percent');
      const gstRateInput = row.querySelector('.gst-rate');
      const isGstExemptInput = row.querySelector('.is-gst-exempt');
      const toggleBtn = row.querySelector('.free-sample-toggle i');

      // Store original values
      row.dataset.originalPrice = unitPriceInput?.value || '0';
      row.dataset.originalDiscount = discountInput?.value || '0';
      row.dataset.originalGstRate = gstRateInput?.value || '0';

      // Set sample state (price = 0, no GST)
      if (isSampleInput) isSampleInput.value = 'true';
      if (sampleReasonInput) sampleReasonInput.value = reason || 'Sample item';
      if (isFreeItemInput) isFreeItemInput.value = 'false';
      if (freeItemReasonInput) freeItemReasonInput.value = '';

      // Set price = 0, GST = 0
      if (unitPriceInput) {
        unitPriceInput.value = '0';
        unitPriceInput.disabled = true;
      }
      if (discountInput) {
        discountInput.value = '0';
        discountInput.disabled = true;
      }
      if (gstRateInput) gstRateInput.value = '0';
      if (isGstExemptInput) isGstExemptInput.value = 'true';

      // Update GST display
      const gstRateDisplay = row.querySelector('.gst-rate-display');
      if (gstRateDisplay) gstRateDisplay.textContent = '0%';

      // Update icon and styling
      if (toggleBtn) {
        toggleBtn.className = 'fas fa-flask text-sm text-purple-600';
      }
      row.classList.remove('free-item-row', 'bg-green-50', 'dark:bg-green-900/20');
      row.classList.add('sample-item-row', 'bg-purple-50', 'dark:bg-purple-900/20');

      // Add badge
      this.addStatusBadge(row, 'SAMPLE', 'purple', 'fa-flask', reason);

      console.log(`🧪 Item marked as SAMPLE: ${row.querySelector('.item-name')?.value}`);

      this.calculateLineTotal(row);
      this.calculateTotals();
      document.dispatchEvent(new Event('line-item-changed'));
    }

    /**
     * Clear free/sample status
     */
    clearFreeSampleStatus(row) {
      if (!row) return;

      // Close menu
      row.querySelector('.free-sample-menu')?.classList.add('hidden');

      const isFreeItem = row.querySelector('.is-free-item')?.value === 'true';
      const isSample = row.querySelector('.is-sample')?.value === 'true';

      if (!isFreeItem && !isSample) return;

      if (!confirm('Clear free/sample status? This will restore the original pricing.')) return;

      // Get elements
      const isFreeItemInput = row.querySelector('.is-free-item');
      const freeItemReasonInput = row.querySelector('.free-item-reason');
      const isSampleInput = row.querySelector('.is-sample');
      const sampleReasonInput = row.querySelector('.sample-reason');
      const unitPriceInput = row.querySelector('.unit-price');
      const discountInput = row.querySelector('.discount-percent');
      const gstRateInput = row.querySelector('.gst-rate');
      const isGstExemptInput = row.querySelector('.is-gst-exempt');
      const toggleBtn = row.querySelector('.free-sample-toggle i');

      // Clear states
      if (isFreeItemInput) isFreeItemInput.value = 'false';
      if (freeItemReasonInput) freeItemReasonInput.value = '';
      if (isSampleInput) isSampleInput.value = 'false';
      if (sampleReasonInput) sampleReasonInput.value = '';

      // Restore original values
      if (unitPriceInput) {
        unitPriceInput.value = row.dataset.originalPrice || '0';
        unitPriceInput.disabled = false;
      }
      if (discountInput) {
        discountInput.value = row.dataset.originalDiscount || '0';
        discountInput.disabled = false;
      }
      if (gstRateInput) gstRateInput.value = row.dataset.originalGstRate || '0';
      if (isGstExemptInput) isGstExemptInput.value = 'false';

      // Reset icon and styling
      if (toggleBtn) {
        toggleBtn.className = 'fas fa-gift text-sm';
      }
      row.classList.remove('free-item-row', 'bg-green-50', 'dark:bg-green-900/20');
      row.classList.remove('sample-item-row', 'bg-purple-50', 'dark:bg-purple-900/20');

      // Remove badge
      this.removeStatusBadge(row);

      console.log(`✖️ Free/Sample status cleared: ${row.querySelector('.item-name')?.value}`);

      this.calculateLineTotal(row);
      this.calculateTotals();
      document.dispatchEvent(new Event('line-item-changed'));
    }

    /**
     * Add status badge (FREE or SAMPLE)
     */
    addStatusBadge(row, label, color, icon, reason) {
      this.removeStatusBadge(row); // Remove existing badge first

      const nameCell = row.querySelector('.item-search')?.parentElement;
      if (!nameCell) return;

      const badge = document.createElement('span');
      badge.className = `status-badge ml-2 px-2 py-0.5 text-xs bg-${color}-100 text-${color}-800 dark:bg-${color}-900 dark:text-${color}-200 rounded-full font-medium`;
      badge.innerHTML = `<i class="fas ${icon} mr-1"></i>${label}`;
      badge.title = reason || `${label} item`;
      nameCell.appendChild(badge);
    }

    /**
     * Remove status badge
     */
    removeStatusBadge(row) {
      const badge = row.querySelector('.status-badge');
      if (badge) badge.remove();
    }

    /**
     * Switch discount display mode between 'percentage' and 'fixed_amount'
     * Called when a campaign discount is applied to show the appropriate input field
     * BACKWARD COMPATIBLE: Works with legacy templates that only have percentage field
     * NOTE: Display mode is determined by which row is visible (no hidden field needed)
     * @param {HTMLElement} row - The line item row
     * @param {string} discountType - 'percentage' or 'fixed_amount'
     * @param {number} value - The discount value to set
     */
    setDiscountMode(row, discountType, value = 0) {
      if (!row) return;

      const percentRow = row.querySelector('.discount-percent-row');
      const amountRow = row.querySelector('.discount-amount-row');
      const percentInput = row.querySelector('.discount-percent');
      const amountInput = row.querySelector('.discount-amount');

      // ✅ BACKWARD COMPATIBILITY: If amount field doesn't exist, use percentage-only mode
      if (!amountRow || !amountInput) {
        console.log('💡 setDiscountMode: Legacy template detected (no amount field), using percentage mode');
        // For fixed_amount on legacy template, convert to percentage
        if (discountType === 'fixed_amount' && percentInput) {
          const quantity = parseFloat(row.querySelector('.quantity')?.value || 1);
          const unitPrice = parseFloat(row.querySelector('.unit-price')?.value || 0);
          const grossAmount = quantity * unitPrice;
          // Convert fixed amount to percentage
          const equivalentPercent = grossAmount > 0 ? (value / grossAmount) * 100 : 0;
          percentInput.value = equivalentPercent.toFixed(2);
          console.log(`💡 Converted fixed amount ₹${value} to ${equivalentPercent.toFixed(2)}% (legacy mode)`);
        } else if (percentInput) {
          percentInput.value = parseFloat(value || 0);
        }
        this.calculateLineTotal(row);
        this.calculateTotals();
        return;
      }

      console.log(`💰 setDiscountMode: type=${discountType}, value=${value}`);

      if (discountType === 'fixed_amount') {
        // Show amount input, hide percentage input
        if (percentRow) percentRow.style.display = 'none';
        amountRow.style.display = 'flex';

        // Set the value
        amountInput.value = parseFloat(value || 0).toFixed(2);
        if (percentInput) percentInput.value = '0';  // Reset percentage

        console.log(`💵 Switched to FIXED AMOUNT mode: ₹${value}`);
      } else {
        // Show percentage input, hide amount input (default)
        if (percentRow) percentRow.style.display = 'flex';
        amountRow.style.display = 'none';

        // Set the value
        if (percentInput) percentInput.value = parseFloat(value || 0);
        amountInput.value = '0';  // Reset amount

        console.log(`📊 Switched to PERCENTAGE mode: ${value}%`);
      }

      // Recalculate after mode switch
      this.calculateLineTotal(row);
      this.calculateTotals();
    }

    /**
     * Get the current discount mode for a row
     * Determines mode based on which input row is visible (no hidden field needed)
     * @param {HTMLElement} row - The line item row
     * @returns {string} 'percentage' or 'fixed_amount'
     */
    getDiscountMode(row) {
      if (!row) return 'percentage';
      const amountRow = row.querySelector('.discount-amount-row');
      // If amount row exists and is visible, it's fixed_amount mode
      if (amountRow && amountRow.style.display !== 'none') {
        return 'fixed_amount';
      }
      return 'percentage';
    }

    /**
     * Get effective discount for a row (amount or percentage based on mode)
     * @param {HTMLElement} row - The line item row
     * @returns {object} {type: 'percentage'|'fixed_amount', value: number}
     */
    getEffectiveDiscount(row) {
      if (!row) return { type: 'percentage', value: 0 };

      const mode = this.getDiscountMode(row);
      if (mode === 'fixed_amount') {
        const amountInput = row.querySelector('.discount-amount');
        return { type: 'fixed_amount', value: parseFloat(amountInput?.value || 0) };
      } else {
        const percentInput = row.querySelector('.discount-percent');
        return { type: 'percentage', value: parseFloat(percentInput?.value || 0) };
      }
    }

    initRow(row) {
      // Initialize batch and expiry fields - disabled and hidden by default until type is selected
      const batchSelect = row.querySelector('.batch-select');
      const expiryInput = row.querySelector('.expiry-date');
      if (batchSelect) {
        batchSelect.disabled = true;
        batchSelect.classList.add('hidden');
      }
      if (expiryInput) {
        expiryInput.disabled = true;
        expiryInput.classList.add('hidden');
      }
      // Hide N/A placeholders by default (shown only when non-medicine type is selected)
      row.querySelectorAll('.non-medicine-placeholder').forEach(el => el.classList.add('hidden'));

      // Initialize item type change
      const itemType = row.querySelector('.item-type');
      const itemSearchInput = row.querySelector('.item-search');

      if (itemType) {
        itemType.addEventListener('change', function() {
          // Show/hide medicine fields for medicine-based types (OTC, Prescription, Product, Consumable)
          const medicineBasedTypes = ['OTC', 'Prescription', 'Product', 'Consumable'];

          // Clear all line item fields when type changes
          row.querySelector('.item-id').value = '';
          row.querySelector('.item-name').value = '';
          if (itemSearchInput) itemSearchInput.value = '';
          row.querySelector('.quantity').value = '1';
          row.querySelector('.unit-price').value = '0.00';
          row.querySelector('.discount-percent').value = '0';
          row.querySelector('.gst-rate').value = '0';
          // Clear display fields if they exist
          const gstRateDisplay = row.querySelector('.gst-rate-display');
          const lineTotalDisplay = row.querySelector('.line-total-display');
          if (gstRateDisplay) gstRateDisplay.textContent = '0%';
          if (lineTotalDisplay) lineTotalDisplay.textContent = '0.00';

          const batchSelect = row.querySelector('.batch-select');
          const expiryInput = row.querySelector('.expiry-date');

          if (medicineBasedTypes.includes(this.value)) {
            // Medicine type selected: Show and enable batch/expiry fields
            if (batchSelect) {
              batchSelect.disabled = false;
              batchSelect.classList.remove('hidden');
              batchSelect.innerHTML = '<option value="">Select Batch</option>';
            }
            if (expiryInput) {
              expiryInput.disabled = false;
              expiryInput.classList.remove('hidden');
              expiryInput.value = '';
            }
            // Hide N/A placeholders for medicine types
            row.querySelectorAll('.non-medicine-placeholder').forEach(el => el.classList.add('hidden'));
          } else {
            // Package/Service type selected: Hide and disable batch/expiry fields
            if (batchSelect) {
              batchSelect.disabled = true;
              batchSelect.classList.add('hidden');
              batchSelect.innerHTML = '<option value="">N/A</option>';
            }
            if (expiryInput) {
              expiryInput.disabled = true;
              expiryInput.classList.add('hidden');
              expiryInput.value = '';
            }
            // Show N/A placeholders for non-medicine types
            row.querySelectorAll('.non-medicine-placeholder').forEach(el => el.classList.remove('hidden'));
          }

          // Focus on search to trigger showing items of new type
          if (itemSearchInput) {
            itemSearchInput.focus();
          }
        });
      }

      // Initialize search functionality
      this.initItemSearch(row);

      // Initialize FIFO allocation for medicines (Enter key on quantity field)
      this.initFIFOAllocation(row);

      // Set line number
      row.querySelector('.line-number').textContent = this.container.querySelectorAll('.line-item-row').length;
    }

    initFIFOAllocation(row) {
      const quantityInput = row.querySelector('.quantity');
      const itemType = row.querySelector('.item-type');
      const itemIdInput = row.querySelector('.item-id');
      const itemNameInput = row.querySelector('.item-name');

      if (!quantityInput || !itemType) {
        return;
      }

      // Medicine-based types that use FIFO allocation
      const medicineBasedTypes = ['OTC', 'Prescription', 'Product', 'Consumable'];

      // *** BATCH MODE CHECK ***
      // Only trigger FIFO modal if batch mode is 'auto'
      // In 'manual' mode, users select batch from dropdown (no modal)
      if (this.batchMode !== 'auto') {
        console.log('Batch mode is manual - FIFO modal disabled');
        return;
      }

      // Listen for Enter key on quantity field (AUTO MODE ONLY)
      quantityInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && medicineBasedTypes.includes(itemType.value)) {
          e.preventDefault();

          const medicineId = itemIdInput.value;
          const medicineName = itemNameInput.value;
          const quantity = parseFloat(quantityInput.value) || 0;

          if (!medicineId) {
            alert('Please select a medicine first');
            return;
          }

          if (quantity <= 0) {
            alert('Please enter a valid quantity');
            return;
          }

          // Check if FIFO modal is available
          if (typeof window.fifoModal === 'undefined' || window.fifoModal === null) {
            console.warn('FIFO modal not initialized yet, falling back to manual batch selection');
            alert('FIFO allocation modal is loading. Please try again in a moment.');
            return;
          }

          // Show FIFO allocation modal
          window.fifoModal.show(
            {
              id: medicineId,
              name: medicineName,
              type: itemType.value
            },
            quantity,
            (batches) => {
              // Callback when user confirms allocation
              this.applyFIFOAllocation(row, batches);
            }
          );
        }
      });
    }

    applyFIFOAllocation(row, batches) {
      console.log('Applying FIFO allocation:', batches);

      if (batches.length === 0) {
        console.warn('No batches to apply');
        return;
      }

      // Get current medicine info from the row
      const itemType = row.querySelector('.item-type').value;
      const medicineId = row.querySelector('.item-id').value;
      const medicineName = row.querySelector('.item-name').value;

      if (batches.length === 1) {
        // Single batch - populate current row
        const batch = batches[0];
        this.populateBatchInRow(row, batch);
        console.log('✅ Single batch applied to current row');
      } else {
        // Multiple batches - create separate line item for each batch
        console.log(`🔵 Creating ${batches.length} separate line items for multiple batches`);

        // Populate first batch in current row
        this.populateBatchInRow(row, batches[0]);

        // Create new line items for remaining batches
        for (let i = 1; i < batches.length; i++) {
          const batch = batches[i];

          // Add new line item
          this.addNewItem();

          // Get the newly added row (last row)
          const rows = this.container.querySelectorAll('.line-item-row');
          const newRow = rows[rows.length - 1];

          // Set item type
          newRow.querySelector('.item-type').value = itemType;
          // Trigger change event to show medicine fields
          newRow.querySelector('.item-type').dispatchEvent(new Event('change'));

          // Set medicine info
          newRow.querySelector('.item-id').value = medicineId;
          newRow.querySelector('.item-name').value = medicineName;
          newRow.querySelector('.item-search').value = medicineName;
          newRow.querySelector('.item-search').title = medicineName; // Tooltip

          // Show full item name in wrap display if name is long
          const itemNameDisplay = newRow.querySelector('.item-name-display');
          if (itemNameDisplay && medicineName.length > 25) {
            itemNameDisplay.textContent = medicineName;
            itemNameDisplay.classList.remove('hidden');
          }

          // Populate batch data
          this.populateBatchInRow(newRow, batch);
        }

        console.log(`✅ Created ${batches.length} line items for multiple batches`);
      }

      console.log('✅ FIFO allocation applied successfully');
    }

    populateBatchInRow(row, batch) {
      console.log('📦 Populating batch in row:', batch);

      const batchSelect = row.querySelector('.batch-select');
      const expiryInput = row.querySelector('.expiry-date');
      const unitPriceInput = row.querySelector('.unit-price');
      const gstRateInput = row.querySelector('.gst-rate');
      const quantityInput = row.querySelector('.quantity');

      // Show medicine fields and hide N/A placeholders
      const medicineFields = row.querySelectorAll('.medicine-field');
      medicineFields.forEach(field => field.classList.remove('hidden'));

      const naPlaceholders = row.querySelectorAll('.non-medicine-placeholder');
      naPlaceholders.forEach(placeholder => placeholder.classList.add('hidden'));

      // Update batch dropdown (create option if doesn't exist)
      if (batchSelect) {
        const optionValue = batch.batch;
        let option = Array.from(batchSelect.options).find(opt => opt.value === optionValue);

        if (!option) {
          option = new Option(batch.batch, batch.batch, false, true);
          batchSelect.add(option);
        }
        batchSelect.value = optionValue;
        batchSelect.classList.remove('hidden');
        console.log('✅ Batch set to:', optionValue);
      }

      // Update other fields
      if (expiryInput) {
        expiryInput.value = batch.expiry_date || '';
        expiryInput.classList.remove('hidden');
        console.log('✅ Expiry set to:', batch.expiry_date);
      }

      if (unitPriceInput) {
        unitPriceInput.value = parseFloat(batch.unit_price || 0).toFixed(2);
        console.log('✅ Unit price set to:', batch.unit_price);
      }

      if (gstRateInput) {
        const gstRate = parseFloat(batch.gst_rate || 0).toFixed(2);
        gstRateInput.value = gstRate;
        console.log('✅ GST rate set to:', gstRate);
      }

      if (quantityInput) {
        quantityInput.value = parseFloat(batch.quantity || 0);
        console.log('✅ Quantity set to:', batch.quantity);
      }

      // Recalculate line total for this row
      console.log('🔵 Calculating line total...');
      const result = this.calculateLineTotal(row);
      console.log('✅ Line total calculated:', result);

      this.calculateTotals();
    }

    // showBatchDetails method removed - no longer needed with separate line items per batch
    
    initItemSearch(row) {
      const itemSearchInput = row.querySelector('.item-search');
      const itemSearchResults = row.querySelector('.item-search-results');
      const itemIdInput = row.querySelector('.item-id');
      const itemNameInput = row.querySelector('.item-name');
      const itemType = row.querySelector('.item-type');
      
      if (!itemSearchInput || !itemSearchResults || !itemIdInput || !itemNameInput || !itemType) {
        return;
      }
      
      // Debounce function
      const debounce = (func, delay) => {
        let timeout;
        return function(...args) {
          clearTimeout(timeout);
          timeout = setTimeout(() => func.apply(this, args), delay);
        };
      };
      
      // Search function
      const performSearch = debounce((query) => {
        // Allow empty query to show top items

        // API request
        fetch(`/invoice/web_api/item/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(itemType.value)}`, {
          headers: {
            'Content-Type': 'application/json'
          }
        })
        .then(response => response.json())
        .then(data => {
          console.log(`Item search results for type "${itemType.value}":`, data);
          itemSearchResults.innerHTML = '';

          if (!data || data.length === 0) {
            itemSearchResults.innerHTML = '<div class="p-2 text-gray-500 dark:text-gray-400">No items found</div>';
            itemSearchResults.classList.remove('hidden');
            return;
          }
          
          data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer';
            
            // Different display formats based on item type
            const medicineBasedTypes = ['OTC', 'Prescription', 'Product', 'Consumable'];
            if (medicineBasedTypes.includes(item.type)) {
              div.innerHTML = `
                <div class="font-semibold">${item.name}</div>
                <div class="text-xs text-gray-600 dark:text-gray-400">Type: ${item.type} | GST: ${item.gst_rate || 0}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
              `;
            } else {
              // Package or Service
              const price = item.price ? parseFloat(item.price).toFixed(2) : '0.00';
              div.innerHTML = `
                <div class="font-semibold">${item.name}</div>
                <div class="text-xs text-gray-600 dark:text-gray-400">Price: Rs.${price} | GST: ${item.gst_rate || 0}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
              `;
            }
            
            const self = this; // Capture 'this' reference for the component
            div.addEventListener('click', () => {
              // Set selected item values
              itemIdInput.value = item.id;
              itemNameInput.value = item.name;
              itemSearchInput.value = item.name;
              itemSearchInput.title = item.name; // Tooltip for full name

              // Show full item name in wrap display if name is long
              const itemNameDisplay = row.querySelector('.item-name-display');
              if (itemNameDisplay) {
                if (item.name.length > 25) {
                  itemNameDisplay.textContent = item.name;
                  itemNameDisplay.classList.remove('hidden');
                } else {
                  itemNameDisplay.classList.add('hidden');
                }
              }

              // Set GST info - ensure string values for hidden inputs
              const gstRateValue = item.gst_rate || 0;
              const isGstExemptValue = item.is_gst_exempt ? 'true' : 'false';  // ✅ Always string
              const gstInclusiveValue = item.gst_inclusive ? 'true' : 'false';  // ✅ Add gst_inclusive

              row.querySelector('.gst-rate').value = gstRateValue;
              row.querySelector('.is-gst-exempt').value = isGstExemptValue;
              row.querySelector('.gst-inclusive').value = gstInclusiveValue;

              console.log(`📋 Item selected: ${item.name}, Type: ${item.type}, GST Rate: ${gstRateValue}%, Exempt: ${isGstExemptValue}, Inclusive: ${gstInclusiveValue}`);

              // Set price for non-medicine items (Package, Service)
              const medicineBasedTypes = ['OTC', 'Prescription', 'Product', 'Consumable'];
              if (!medicineBasedTypes.includes(item.type)) {
                const priceValue = item.price ? item.price.toFixed(2) : '0.00';
                row.querySelector('.unit-price').value = priceValue;
                console.log(`💰 Non-medicine price set: ${priceValue}`);
              }

              // Hide results
              itemSearchResults.classList.add('hidden');

              // *** BATCH MODE CHECK ***
              // Manual mode: Load batches immediately when item is selected
              // Auto mode: Batches loaded via FIFO modal (press Enter on quantity field)
              if (self.batchMode === 'manual' && medicineBasedTypes.includes(item.type)) {
                self.loadMedicineBatches(item.id, row);
              }

              // Calculate totals
              console.log('🔢 Calculating line total after item selection...');
              self.calculateLineTotal(row);
              self.calculateTotals();
              // Notify bulk discount manager of line item changes
              document.dispatchEvent(new Event('line-item-changed'));
            });
            
            itemSearchResults.appendChild(div);
          });
          
          itemSearchResults.classList.remove('hidden');
        })
        .catch(error => {
          console.error('Error searching items:', error);
          itemSearchResults.innerHTML = '<div class="p-2 text-red-500">Error searching items</div>';
          itemSearchResults.classList.remove('hidden');
        });
      }, 300);
      
      // Attach event listeners
      itemSearchInput.addEventListener('input', function() {
        const query = this.value.trim();
        performSearch(query);
      });

      // Show top items on focus
      itemSearchInput.addEventListener('focus', function() {
        const query = this.value.trim();
        performSearch(query);
      });

      // Show top items on click
      itemSearchInput.addEventListener('click', function() {
        const query = this.value.trim();
        performSearch(query);
      });

      // Hide results when clicking outside
      document.addEventListener('click', function(e) {
        if (!itemSearchInput.contains(e.target) && !itemSearchResults.contains(e.target)) {
          itemSearchResults.classList.add('hidden');
        }
      });
    }
    
    loadMedicineBatches(medicineId, row) {
      const batchSelect = row.querySelector('.batch-select');
      const expiryDateInput = row.querySelector('.expiry-date');
      const unitPriceInput = row.querySelector('.unit-price');

      if (!batchSelect || !expiryDateInput || !unitPriceInput) return;

      // Show loading state
      batchSelect.innerHTML = '<option value="">Loading batches...</option>';
      batchSelect.disabled = true;

      console.log(`🔍 Fetching batches for medicine: ${medicineId}`);

      // Use web-friendly billing endpoint with session-based auth (Flask-Login)
      fetch(`/invoice/web_api/medicine/${medicineId}/batches`, {
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'same-origin'  // Include cookies for session auth
      })
      .then(response => response.json())
      .then(data => {
        // Re-enable dropdown
        batchSelect.disabled = false;

        // Clear existing options
        batchSelect.innerHTML = '<option value="">Select Batch</option>';

        // API returns direct array of batches
        if (!Array.isArray(data) || data.length === 0) {
          batchSelect.innerHTML += '<option value="" disabled>No batches available</option>';
          console.warn('No batches available for medicine:', medicineId);
          return;
        }

        console.log(`✅ Loaded ${data.length} batches for medicine ${medicineId}`);

        // Calculate already allocated quantities for this medicine in other rows
        const allocatedByBatch = this.getAllocatedQuantitiesByBatch(medicineId, row);
        console.log('📊 Already allocated quantities:', allocatedByBatch);

        // Add options for each batch with adjusted available quantities
        let availableBatchCount = 0;
        data.forEach(batch => {
          // Calculate remaining quantity after subtracting allocated
          const allocated = allocatedByBatch[batch.batch] || 0;
          const adjustedAvailable = batch.available_quantity - allocated;

          // Skip batches with no remaining stock
          if (adjustedAvailable <= 0) {
            console.log(`⚠️ Skipping batch ${batch.batch} - no remaining stock (allocated: ${allocated})`);
            return;
          }

          const option = document.createElement('option');
          option.value = batch.batch;

          // Build display: "BATCH-001 (Exp: 15/Jan/2025) - Avail: 70 units"
          const expiryDisplay = batch.expiry_date ?
            new Date(batch.expiry_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) :
            'No Expiry';
          const adjustedDisplay = `${batch.batch} (Exp: ${expiryDisplay}) - Avail: ${adjustedAvailable} units`;
          option.textContent = adjustedDisplay;

          option.setAttribute('data-expiry', batch.expiry_date || '');
          option.setAttribute('data-price', batch.unit_price || '0.00');
          option.setAttribute('data-gst-rate', batch.gst_rate || '0');  // ✅ Store GST from pricing_tax_service
          option.setAttribute('data-is-gst-exempt', batch.is_gst_exempt || 'false');  // ✅ Store exemption status
          option.setAttribute('data-gst-inclusive', batch.gst_inclusive || 'false');  // ✅ Store inclusive flag
          option.setAttribute('data-available', adjustedAvailable);
          batchSelect.appendChild(option);
          availableBatchCount++;
        });

        console.log(`📦 Batch dropdown populated with ${availableBatchCount} available batches (out of ${data.length} total)`);
      })
      .catch(error => {
        console.error('Error loading medicine batches:', error);
        batchSelect.disabled = false;
        batchSelect.innerHTML = '<option value="">Error loading batches</option>';
      });

      // Add change event listener for batch selection (only once)
      if (!batchSelect.hasAttribute('data-listener-added')) {
        batchSelect.setAttribute('data-listener-added', 'true');
        const self = this;
        batchSelect.addEventListener('change', function() {
          const selectedOption = this.options[this.selectedIndex];
          if (selectedOption && selectedOption.value) {
            // Update expiry and price
            expiryDateInput.value = selectedOption.getAttribute('data-expiry') || '';
            unitPriceInput.value = selectedOption.getAttribute('data-price') || '0.00';

            // ✅ CRITICAL: Update GST rate from batch data (which comes from pricing_tax_service)
            const gstRate = selectedOption.getAttribute('data-gst-rate') || '0';
            const isGstExempt = selectedOption.getAttribute('data-is-gst-exempt') || 'false';
            const gstInclusive = selectedOption.getAttribute('data-gst-inclusive') || 'false';

            row.querySelector('.gst-rate').value = gstRate;
            row.querySelector('.is-gst-exempt').value = isGstExempt;
            row.querySelector('.gst-inclusive').value = gstInclusive;

            console.log(`✅ Batch selected: ${selectedOption.value}`);
            console.log(`   Price: ${unitPriceInput.value}, Expiry: ${expiryDateInput.value}`);
            console.log(`   GST Rate: ${gstRate}%, GST Exempt: ${isGstExempt}, GST Inclusive: ${gstInclusive} (from pricing_tax_service)`);

            // Recalculate totals after batch selection
            self.calculateLineTotal(row);
            self.calculateTotals();
          }
        });
      }
    }

    getAllocatedQuantitiesByBatch(medicineId, currentRow) {
      /**
       * Calculate quantities already allocated to each batch for a given medicine
       * across all line items (excluding the current row)
       *
       * Returns: Object with batch_number as key and allocated quantity as value
       * Example: { "BATCH-001": 30, "BATCH-002": 50 }
       */
      const allocatedByBatch = {};

      // Loop through all line item rows in the invoice
      const allRows = this.container.querySelectorAll('.line-item-row');
      allRows.forEach(otherRow => {
        // Skip the current row (we're calculating allocations for other rows)
        if (otherRow === currentRow) return;

        // Check if this row has the same medicine
        const otherMedicineId = otherRow.querySelector('.item-id')?.value;
        if (otherMedicineId !== medicineId) return;

        // Get batch and quantity from this row
        const batchSelect = otherRow.querySelector('.batch-select');
        const quantityInput = otherRow.querySelector('.quantity');

        if (batchSelect && quantityInput) {
          const batch = batchSelect.value;
          const quantity = parseFloat(quantityInput.value) || 0;

          // Only count if a batch is selected and quantity > 0
          if (batch && quantity > 0) {
            allocatedByBatch[batch] = (allocatedByBatch[batch] || 0) + quantity;
            console.log(`📌 Row allocated ${quantity} units of batch ${batch}`);
          }
        }
      });

      return allocatedByBatch;
    }

    calculateLineTotal(row) {
      const quantity = parseFloat(row.querySelector('.quantity').value) || 0;
      const unitPrice = parseFloat(row.querySelector('.unit-price').value) || 0;
      const gstRate = parseFloat(row.querySelector('.gst-rate').value) || 0;
      const isGstExempt = row.querySelector('.is-gst-exempt').value === 'true';
      const gstInclusive = row.querySelector('.gst-inclusive').value === 'true';  // ✅ CRITICAL: Check if GST is inclusive
      // Both is_gst_invoice and is_interstate are now hidden inputs with string values
      const isGstInvoiceValue = document.getElementById('is_gst_invoice')?.value || 'false';
      const isGstInvoice = isGstInvoiceValue === 'true';
      const isInterstateValue = document.getElementById('is_interstate')?.value || 'false';
      const isInterstate = isInterstateValue === 'true';

      // Calculate gross amount
      const grossAmount = quantity * unitPrice;

      // ✅ BACKWARD COMPATIBLE: Handle both percentage and fixed_amount discount types
      // Determine mode based on which input is visible (no hidden field needed)
      const discountTypeMode = this.getDiscountMode(row);

      let discountPercent = 0;
      let discountAmount = 0;

      if (discountTypeMode === 'fixed_amount') {
        // Fixed amount discount - use the discount-amount field
        const discountAmountInput = row.querySelector('.discount-amount');
        discountAmount = parseFloat(discountAmountInput?.value || 0);
        // Calculate equivalent percentage for storage (both fields synced)
        discountPercent = grossAmount > 0 ? (discountAmount / grossAmount) * 100 : 0;
      } else {
        // Percentage discount (default/legacy) - use the discount-percent field
        const discountPercentInput = row.querySelector('.discount-percent');
        discountPercent = parseFloat(discountPercentInput?.value || 0);
        // Calculate amount from percentage (both fields synced)
        discountAmount = (grossAmount * discountPercent) / 100;
      }

      console.log('💰 Calculate Line Total - Input values:', {
        quantity,
        unitPrice,
        gstRate,
        isGstInvoice,
        isGstExempt,
        gstInclusive,  // ✅ Log inclusive flag
        isInterstate,
        discountTypeMode,  // ✅ Log discount type mode
        discountPercent,
        discountAmount
      });

      // Amount after discount
      const amountAfterDiscount = grossAmount - discountAmount;

      // Calculate GST based on inclusive/exclusive pricing
      let taxableAmount = 0;
      let cgstAmount = 0;
      let sgstAmount = 0;
      let igstAmount = 0;
      let totalGstAmount = 0;
      let lineTotal = 0;

      if (isGstInvoice && !isGstExempt && gstRate > 0) {
        if (gstInclusive) {
          // ✅ GST INCLUSIVE: Price already includes GST, extract the GST component
          // Formula: taxable_amount = amount_with_gst / (1 + rate/100)
          const divisor = 1 + (gstRate / 100);
          taxableAmount = amountAfterDiscount / divisor;
          totalGstAmount = amountAfterDiscount - taxableAmount;

          if (isInterstate) {
            // Interstate: only IGST
            igstAmount = totalGstAmount;
          } else {
            // Intrastate: CGST + SGST (split 50-50)
            cgstAmount = totalGstAmount / 2;
            sgstAmount = totalGstAmount / 2;
          }

          lineTotal = amountAfterDiscount;  // Total is the amount after discount (GST already included)
          console.log('✅ GST INCLUSIVE calculated:', { taxableAmount, cgstAmount, sgstAmount, igstAmount, totalGstAmount, lineTotal });
        } else {
          // ✅ GST EXCLUSIVE: Price does NOT include GST, add GST on top
          taxableAmount = amountAfterDiscount;

          if (isInterstate) {
            // Interstate: only IGST
            igstAmount = (taxableAmount * gstRate) / 100;
            totalGstAmount = igstAmount;
          } else {
            // Intrastate: CGST + SGST
            const halfGstRate = gstRate / 2;
            cgstAmount = (taxableAmount * halfGstRate) / 100;
            sgstAmount = (taxableAmount * halfGstRate) / 100;
            totalGstAmount = cgstAmount + sgstAmount;
          }

          lineTotal = taxableAmount + totalGstAmount;  // Total is taxable + GST
          console.log('✅ GST EXCLUSIVE calculated:', { taxableAmount, cgstAmount, sgstAmount, igstAmount, totalGstAmount, lineTotal });
        }
      } else {
        // No GST applicable
        taxableAmount = amountAfterDiscount;
        lineTotal = amountAfterDiscount;
        console.log('⚠️ GST NOT calculated. Conditions:', {
          isGstInvoice,
          isGstExempt,
          gstRate,
          passesCheck: isGstInvoice && !isGstExempt && gstRate > 0
        });
      }

      console.log('💵 Final amounts:', { taxableAmount, totalGstAmount, lineTotal });

      // Update GST rate display (percentage)
      const gstRateDisplayEl = row.querySelector('.gst-rate-display');
      if (gstRateDisplayEl) {
        gstRateDisplayEl.textContent = gstRate > 0 ? `${gstRate}%` : '0%';
        console.log(`✅ Line GST rate display updated: ${gstRate}%`);
      } else {
        console.warn('⚠️ .gst-rate-display element not found in row');
      }

      // Update line total display (visible to user)
      const lineTotalDisplayEl = row.querySelector('.line-total-display');
      if (lineTotalDisplayEl) {
        lineTotalDisplayEl.textContent = lineTotal.toFixed(2);
        console.log(`✅ Line total display updated: ${lineTotal.toFixed(2)}`);
      } else {
        console.warn('⚠️ .line-total-display element not found in row');
      }
      
      return {
        quantity,
        unitPrice,
        discountPercent,
        discountAmount,
        taxableAmount,
        cgstAmount,
        sgstAmount,
        igstAmount,
        totalGstAmount,
        lineTotal
      };
    }
    
    calculateTotals() {
      const rows = this.container.querySelectorAll('.line-item-row');

      // Initialize totals
      let subtotal = 0;
      let totalDiscount = 0;
      let totalCgst = 0;
      let totalSgst = 0;
      let totalIgst = 0;
      let grandTotal = 0;
      
      // Sum values from all rows
      rows.forEach(row => {
        const result = this.calculateLineTotal(row);
        
        // Add to totals
        subtotal += result.quantity * result.unitPrice;
        totalDiscount += result.discountAmount;
        totalCgst += result.cgstAmount;
        totalSgst += result.sgstAmount;
        totalIgst += result.igstAmount;
        grandTotal += result.lineTotal;
      });
      
      // Update totals in the UI (with null checks)
      const subtotalEl = document.getElementById('subtotal');
      const totalDiscountEl = document.getElementById('total-discount');
      const totalCgstEl = document.getElementById('total-cgst');
      const totalSgstEl = document.getElementById('total-sgst');
      const totalIgstEl = document.getElementById('total-igst');
      const grandTotalEl = document.getElementById('grand-total');

      console.log('📊 Updating invoice totals:', {
        subtotal,
        totalDiscount,
        totalCgst,
        totalSgst,
        totalIgst,
        grandTotal,
        elementsFound: {
          subtotal: !!subtotalEl,
          totalDiscount: !!totalDiscountEl,
          totalCgst: !!totalCgstEl,
          totalSgst: !!totalSgstEl,
          totalIgst: !!totalIgstEl,
          grandTotal: !!grandTotalEl
        }
      });

      if (subtotalEl) subtotalEl.textContent = subtotal.toFixed(2);
      if (totalDiscountEl) totalDiscountEl.textContent = totalDiscount.toFixed(2);
      if (totalCgstEl) totalCgstEl.textContent = totalCgst.toFixed(2);
      if (totalSgstEl) totalSgstEl.textContent = totalSgst.toFixed(2);
      if (totalIgstEl) totalIgstEl.textContent = totalIgst.toFixed(2);
      if (grandTotalEl) grandTotalEl.textContent = grandTotal.toFixed(2);

      console.log('✅ Invoice totals updated in calculation fields');

      // Update display fields directly (visible to user)
      const subtotalDisplayEl = document.getElementById('subtotal-display');
      const totalDiscountDisplayEl = document.getElementById('total-discount-display');
      const cgstDisplayEl = document.getElementById('cgst-display');
      const sgstDisplayEl = document.getElementById('sgst-display');
      const igstDisplayEl = document.getElementById('igst-display');
      const grandTotalDisplayEl = document.getElementById('grand-total-display');

      if (subtotalDisplayEl) subtotalDisplayEl.textContent = subtotal.toFixed(2);
      if (totalDiscountDisplayEl) totalDiscountDisplayEl.textContent = totalDiscount.toFixed(2);
      if (cgstDisplayEl) cgstDisplayEl.textContent = totalCgst.toFixed(2);
      if (sgstDisplayEl) sgstDisplayEl.textContent = totalSgst.toFixed(2);
      if (igstDisplayEl) igstDisplayEl.textContent = totalIgst.toFixed(2);
      if (grandTotalDisplayEl) grandTotalDisplayEl.textContent = grandTotal.toFixed(2);

      console.log('✅ Display totals updated:', {
        subtotalDisplay: subtotal.toFixed(2),
        cgstDisplay: totalCgst.toFixed(2),
        sgstDisplay: totalSgst.toFixed(2),
        grandTotalDisplay: grandTotal.toFixed(2)
      });
    }
    
    updateLineNumbers() {
      const rows = this.container.querySelectorAll('.line-item-row');
      rows.forEach((row, index) => {
        row.querySelector('.line-number').textContent = index + 1;
      });
    }
  }