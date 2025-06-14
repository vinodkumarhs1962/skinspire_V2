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
        this.container.addEventListener('click', (e) => {
          const target = e.target;
          
          // Handle delete button
          if (target.closest('.remove-line-item')) {
            this.removeItem(target.closest('.line-item-row'));
          }
          
          // Handle save button
          if (target.closest('.save-line-item')) {
            this.saveItem(target.closest('.line-item-row'));
          }
        });
        
        // Event delegation for input changes
        this.container.addEventListener('input', (e) => {
          if (e.target.matches('.quantity, .unit-price, .discount-percent')) {
            this.calculateLineTotal(e.target.closest('.line-item-row'));
            this.calculateTotals();
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
      
      // For medicine, validate batch
      const itemType = row.querySelector('.item-type').value;
      if (itemType === 'Medicine' || itemType === 'Prescription') {
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
    
    initRow(row) {
      // Initialize item type change
      const itemType = row.querySelector('.item-type');
      const medicineFields = row.querySelector('.medicine-fields');
      
      if (itemType && medicineFields) {
        itemType.addEventListener('change', function() {
          // Show/hide medicine fields based on type
          if (this.value === 'Medicine' || this.value === 'Prescription') {
            medicineFields.classList.remove('hidden');
          } else {
            medicineFields.classList.add('hidden');
          }
        });
      }
      
      // Initialize search functionality
      this.initItemSearch(row);
      
      // Set line number
      row.querySelector('.line-number').textContent = this.container.querySelectorAll('.line-item-row').length;
    }
    
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
        if (query.length < 2) {
          itemSearchResults.innerHTML = '';
          itemSearchResults.classList.add('hidden');
          return;
        }
        
        // Get auth token
        const tokenElement = document.querySelector('meta[name="auth-token"]');
        const token = tokenElement ? tokenElement.getAttribute('content') : null;
        
        // API request
        fetch(`/api/item/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(itemType.value)}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })
        .then(response => response.json())
        .then(data => {
          itemSearchResults.innerHTML = '';
          
          if (data.length === 0) {
            itemSearchResults.innerHTML = '<div class="p-2 text-gray-500 dark:text-gray-400">No items found</div>';
            itemSearchResults.classList.remove('hidden');
            return;
          }
          
          data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-600 cursor-pointer';
            
            // Different display formats based on item type
            if (item.type === 'Medicine' || item.type === 'Prescription') {
              div.innerHTML = `
                <div class="font-semibold">${item.name}</div>
                <div class="text-xs text-gray-600 dark:text-gray-400">GST: ${item.gst_rate}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
              `;
            } else {
              div.innerHTML = `
                <div class="font-semibold">${item.name}</div>
                <div class="text-xs text-gray-600 dark:text-gray-400">Price:  Rs.${item.price.toFixed(2)} | GST: ${item.gst_rate}%${item.is_gst_exempt ? ' (Exempt)' : ''}</div>
              `;
            }
            
            div.addEventListener('click', () => {
              // Set selected item values
              itemIdInput.value = item.id;
              itemNameInput.value = item.name;
              itemSearchInput.value = item.name;
              
              // Set GST info
              row.querySelector('.gst-rate').value = item.gst_rate || 0;
              row.querySelector('.is-gst-exempt').value = item.is_gst_exempt || false;
              
              // Set price for non-medicine items
              if (item.type !== 'Medicine' && item.type !== 'Prescription') {
                row.querySelector('.unit-price').value = item.price ? item.price.toFixed(2) : '0.00';
              }
              
              // Hide results
              itemSearchResults.classList.add('hidden');
              
              // Load batches for medicine
              if (item.type === 'Medicine' || item.type === 'Prescription') {
                this.loadMedicineBatches(item.id, row);
              }
              
              // Calculate totals
              this.calculateLineTotal(row);
              this.calculateTotals();
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
      const quantity = row.querySelector('.quantity').value || 1;
      
      if (!batchSelect || !expiryDateInput || !unitPriceInput) return;
      
      // Get auth token
      const tokenElement = document.querySelector('meta[name="auth-token"]');
      const token = tokenElement ? tokenElement.getAttribute('content') : null;
      
      // API request for batches
      fetch(`/api/medicine/${medicineId}/batches?quantity=${quantity}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      .then(response => response.json())
      .then(data => {
        // Clear existing options
        batchSelect.innerHTML = '<option value="">Select Batch</option>';
        
        const batches = Array.isArray(data) ? data : (data.batches || []);
        
        if (batches.length === 0) {
          batchSelect.innerHTML += '<option value="" disabled>No batches available</option>';
          return;
        }
        
        // Add options for each batch
        batches.forEach(batch => {
          const option = document.createElement('option');
          option.value = batch.batch || batch.batch_number;
          option.textContent = `${batch.batch || batch.batch_number} (${batch.quantity_available || batch.available_quantity} units)`;
          option.setAttribute('data-expiry', batch.expiry_date || batch.expiry);
          option.setAttribute('data-price', batch.sale_price || batch.unit_price);
          batchSelect.appendChild(option);
        });
        
        // Select first batch if available
        if (batchSelect.options.length > 1) {
          batchSelect.selectedIndex = 1;
          const selectedOption = batchSelect.options[1];
          expiryDateInput.value = selectedOption.getAttribute('data-expiry') || '';
          unitPriceInput.value = selectedOption.getAttribute('data-price') || '0.00';
          
          // Calculate totals
          this.calculateLineTotal(row);
          this.calculateTotals();
        }
      })
      .catch(error => {
        console.error('Error loading medicine batches:', error);
        batchSelect.innerHTML = '<option value="">Error loading batches</option>';
      });
      
      // Add change event listener for batch selection
      batchSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        if (selectedOption) {
          expiryDateInput.value = selectedOption.getAttribute('data-expiry') || '';
          unitPriceInput.value = selectedOption.getAttribute('data-price') || '0.00';
        }
      });
    }
    
    calculateLineTotal(row) {
      const quantity = parseFloat(row.querySelector('.quantity').value) || 0;
      const unitPrice = parseFloat(row.querySelector('.unit-price').value) || 0;
      const discountPercent = parseFloat(row.querySelector('.discount-percent').value) || 0;
      const gstRate = parseFloat(row.querySelector('.gst-rate').value) || 0;
      const isGstExempt = row.querySelector('.is-gst-exempt').value === 'true';
      const isGstInvoice = document.getElementById('is_gst_invoice').checked;
      const isInterstate = document.getElementById('is_interstate').checked;
      
      // Calculate pre-discount amount
      const preDiscountAmount = quantity * unitPrice;
      
      // Calculate discount
      const discountAmount = (preDiscountAmount * discountPercent) / 100;
      
      // Calculate taxable amount (after discount)
      const taxableAmount = preDiscountAmount - discountAmount;
      
      // Calculate GST
      let cgstAmount = 0;
      let sgstAmount = 0;
      let igstAmount = 0;
      let totalGstAmount = 0;
      
      if (isGstInvoice && !isGstExempt && gstRate > 0) {
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
      }
      
      // Calculate line total
      const lineTotal = taxableAmount + totalGstAmount;
      
      // Update GST amount display
      row.querySelector('.gst-amount').textContent = totalGstAmount.toFixed(2);
      
      // Update line total
      row.querySelector('.line-total').textContent = lineTotal.toFixed(2);
      
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
      const isGstInvoice = document.getElementById('is_gst_invoice').checked;
      
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
      
      // Update totals in the UI
      document.getElementById('subtotal').textContent = subtotal.toFixed(2);
      document.getElementById('total-discount').textContent = totalDiscount.toFixed(2);
      document.getElementById('total-cgst').textContent = totalCgst.toFixed(2);
      document.getElementById('total-sgst').textContent = totalSgst.toFixed(2);
      document.getElementById('total-igst').textContent = totalIgst.toFixed(2);
      document.getElementById('grand-total').textContent = grandTotal.toFixed(2);
    }
    
    updateLineNumbers() {
      const rows = this.container.querySelectorAll('.line-item-row');
      rows.forEach((row, index) => {
        row.querySelector('.line-number').textContent = index + 1;
      });
    }
  }