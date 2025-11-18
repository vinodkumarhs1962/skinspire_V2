// app/static/js/components/fifo_allocation_modal.js
// FIFO Batch Allocation Modal - Shows automatic batch allocation preview
// Allows user to accept FIFO suggestion or manually override

console.log("📦 fifo_allocation_modal.js loaded");

class FIFOAllocationModal {
    constructor() {
        this.modal = null;
        this.currentMedicine = null;
        this.currentQuantity = 0;
        this.batchAllocations = [];
        this.onConfirmCallback = null;

        this.init();
    }

    init() {
        // Create modal HTML structure
        this.createModalHTML();
        this.attachEventListeners();
        console.log("✅ FIFO Allocation Modal initialized");
    }

    createModalHTML() {
        const modalHTML = `
            <div id="fifo-allocation-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden overflow-y-auto h-full w-full z-50">
                <div class="relative top-20 mx-auto p-5 border w-11/12 max-w-3xl shadow-lg rounded-md bg-white dark:bg-gray-800">
                    <!-- Modal Header -->
                    <div class="flex items-center justify-between pb-3 border-b dark:border-gray-700">
                        <h3 class="text-xl font-semibold text-gray-900 dark:text-white">
                            FIFO Batch Allocation
                        </h3>
                        <button type="button" class="close-modal text-gray-400 bg-transparent hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm p-1.5 ml-auto inline-flex items-center dark:hover:bg-gray-600 dark:hover:text-white">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>

                    <!-- Modal Body -->
                    <div class="mt-4">
                        <!-- Medicine Info -->
                        <div class="bg-blue-50 dark:bg-blue-900 dark:bg-opacity-20 p-4 rounded-lg mb-4">
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Medicine</label>
                                    <p class="text-lg font-semibold text-gray-900 dark:text-white" id="fifo-medicine-name">-</p>
                                </div>
                                <div>
                                    <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Quantity Required</label>
                                    <p class="text-lg font-semibold text-gray-900 dark:text-white" id="fifo-quantity-required">-</p>
                                </div>
                            </div>
                        </div>

                        <!-- Allocation Strategy Info -->
                        <div class="mb-4 flex items-center text-sm text-gray-600 dark:text-gray-400">
                            <i class="fas fa-info-circle mr-2"></i>
                            <span>Batches selected using FIFO (First In First Out) based on expiry date</span>
                        </div>

                        <!-- Batch Allocation Table -->
                        <div class="overflow-x-auto">
                            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead class="bg-gray-50 dark:bg-gray-700">
                                    <tr>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                            Batch
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                            Expiry Date
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                            Available Stock
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                            Allocated Qty
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                            Unit Price
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                            Amount
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                                            Action
                                        </th>
                                    </tr>
                                </thead>
                                <tbody id="fifo-batch-tbody" class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                                    <!-- Rows populated dynamically -->
                                </tbody>
                                <tfoot class="bg-gray-50 dark:bg-gray-700">
                                    <tr>
                                        <td colspan="3" class="px-4 py-3 text-right font-semibold text-gray-700 dark:text-gray-300">
                                            Total:
                                        </td>
                                        <td class="px-4 py-3 font-semibold text-gray-900 dark:text-white" id="fifo-total-qty">
                                            0
                                        </td>
                                        <td></td>
                                        <td class="px-4 py-3 font-semibold text-gray-900 dark:text-white" id="fifo-total-amount">
                                            ₹0.00
                                        </td>
                                        <td></td>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>

                        <!-- Warning if insufficient stock -->
                        <div id="fifo-warning" class="hidden mt-4 bg-yellow-50 dark:bg-yellow-900 dark:bg-opacity-20 border-l-4 border-yellow-400 p-4">
                            <div class="flex">
                                <div class="flex-shrink-0">
                                    <i class="fas fa-exclamation-triangle text-yellow-400"></i>
                                </div>
                                <div class="ml-3">
                                    <p class="text-sm text-yellow-700 dark:text-yellow-400">
                                        <strong>Warning:</strong> Insufficient stock!
                                        <span id="fifo-warning-text"></span>
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Modal Footer -->
                    <div class="flex items-center justify-end pt-4 border-t border-gray-200 dark:border-gray-700 space-x-2">
                        <button type="button" class="close-modal px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md shadow-sm hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-300">
                            Cancel
                        </button>
                        <button type="button" id="fifo-confirm-btn" class="px-4 py-2 bg-blue-600 text-white text-base font-medium rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300">
                            <i class="fas fa-check mr-2"></i>
                            Accept Allocation
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Append to body
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('fifo-allocation-modal');
    }

    attachEventListeners() {
        // Close modal buttons
        const closeButtons = this.modal.querySelectorAll('.close-modal');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.hide());
        });

        // Close on outside click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });

        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.modal.classList.contains('hidden')) {
                this.hide();
            }
        });

        // Confirm button
        document.getElementById('fifo-confirm-btn').addEventListener('click', () => {
            this.confirmAllocation();
        });
    }

    /**
     * Show FIFO allocation modal for a medicine
     * @param {Object} medicine - Medicine object {id, name, type}
     * @param {Number} quantity - Quantity required
     * @param {Function} onConfirm - Callback when allocation is confirmed
     */
    async show(medicine, quantity, onConfirm) {
        this.currentMedicine = medicine;
        this.currentQuantity = quantity;
        this.onConfirmCallback = onConfirm;

        // Update modal header
        document.getElementById('fifo-medicine-name').textContent = medicine.name;
        document.getElementById('fifo-quantity-required').textContent = quantity;

        // Show loading state
        this.showLoading();
        this.modal.classList.remove('hidden');

        // Fetch FIFO allocation from backend
        try {
            const response = await fetch(`/invoice/web_api/medicine/${medicine.id}/fifo-allocation?quantity=${quantity}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                this.batchAllocations = data.batches || [];
                this.renderBatchTable();
            } else {
                this.showError(data.message || 'Failed to get batch allocation');
            }
        } catch (error) {
            console.error('Error fetching FIFO allocation:', error);
            this.showError('Failed to fetch batch allocation. Please try again.');
        }
    }

    showLoading() {
        const tbody = document.getElementById('fifo-batch-tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-4 py-8 text-center">
                    <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
                    <p class="mt-2 text-gray-500 dark:text-gray-400">Calculating FIFO allocation...</p>
                </td>
            </tr>
        `;
    }

    showError(message) {
        const tbody = document.getElementById('fifo-batch-tbody');
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="px-4 py-8 text-center">
                    <i class="fas fa-exclamation-circle text-2xl text-red-500"></i>
                    <p class="mt-2 text-red-600 dark:text-red-400">${message}</p>
                </td>
            </tr>
        `;
    }

    renderBatchTable() {
        const tbody = document.getElementById('fifo-batch-tbody');
        tbody.innerHTML = '';

        if (this.batchAllocations.length === 0) {
            this.showError('No batches available for this medicine');
            return;
        }

        let totalQty = 0;
        let totalAmount = 0;

        this.batchAllocations.forEach((batch, index) => {
            const amount = parseFloat(batch.quantity) * parseFloat(batch.unit_price || 0);
            totalQty += parseFloat(batch.quantity);
            totalAmount += amount;

            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-3 text-sm text-gray-900 dark:text-gray-300">
                    ${batch.batch}
                </td>
                <td class="px-4 py-3 text-sm text-gray-900 dark:text-gray-300">
                    ${this.formatDate(batch.expiry_date)}
                </td>
                <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                    ${batch.available_stock || 0}
                </td>
                <td class="px-4 py-3">
                    <input type="number"
                           class="batch-qty-input w-20 px-2 py-1 border rounded text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                           value="${batch.quantity}"
                           min="0"
                           max="${batch.available_stock || 0}"
                           data-index="${index}">
                </td>
                <td class="px-4 py-3 text-sm text-gray-900 dark:text-gray-300">
                    ₹${parseFloat(batch.unit_price || 0).toFixed(2)}
                </td>
                <td class="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white batch-amount">
                    ₹${amount.toFixed(2)}
                </td>
                <td class="px-4 py-3">
                    <button type="button"
                            class="remove-batch text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                            data-index="${index}"
                            title="Remove this batch">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });

        // Update totals
        document.getElementById('fifo-total-qty').textContent = totalQty.toFixed(2);
        document.getElementById('fifo-total-amount').textContent = `₹${totalAmount.toFixed(2)}`;

        // Check if total matches required quantity
        this.checkQuantityMatch(totalQty);

        // Attach event listeners to inputs
        this.attachBatchInputListeners();
    }

    attachBatchInputListeners() {
        // Quantity input change
        const qtyInputs = document.querySelectorAll('.batch-qty-input');
        qtyInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                const index = parseInt(e.target.dataset.index);
                const newQty = parseFloat(e.target.value) || 0;

                // Update batch allocation
                this.batchAllocations[index].quantity = newQty;

                // Recalculate totals
                this.updateTotals();
            });
        });

        // Remove batch buttons
        const removeButtons = document.querySelectorAll('.remove-batch');
        removeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.batchAllocations.splice(index, 1);
                this.renderBatchTable();
            });
        });
    }

    updateTotals() {
        let totalQty = 0;
        let totalAmount = 0;

        this.batchAllocations.forEach((batch, index) => {
            const qty = parseFloat(batch.quantity) || 0;
            const price = parseFloat(batch.unit_price) || 0;
            const amount = qty * price;

            totalQty += qty;
            totalAmount += amount;

            // Update amount cell
            const amountCells = document.querySelectorAll('.batch-amount');
            if (amountCells[index]) {
                amountCells[index].textContent = `₹${amount.toFixed(2)}`;
            }
        });

        document.getElementById('fifo-total-qty').textContent = totalQty.toFixed(2);
        document.getElementById('fifo-total-amount').textContent = `₹${totalAmount.toFixed(2)}`;

        this.checkQuantityMatch(totalQty);
    }

    checkQuantityMatch(totalQty) {
        const warning = document.getElementById('fifo-warning');
        const warningText = document.getElementById('fifo-warning-text');
        const confirmBtn = document.getElementById('fifo-confirm-btn');

        if (totalQty < this.currentQuantity) {
            // Insufficient quantity
            warning.classList.remove('hidden');
            warningText.textContent = `Required: ${this.currentQuantity}, Available: ${totalQty}. Short by ${(this.currentQuantity - totalQty).toFixed(2)} units.`;
            confirmBtn.innerHTML = '<i class="fas fa-exclamation-triangle mr-2"></i>Accept (Partial)';
        } else if (totalQty > this.currentQuantity) {
            // Excess quantity
            warning.classList.remove('hidden');
            warningText.textContent = `Required: ${this.currentQuantity}, Allocated: ${totalQty}. Excess of ${(totalQty - this.currentQuantity).toFixed(2)} units.`;
            confirmBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Accept Allocation';
        } else {
            // Perfect match
            warning.classList.add('hidden');
            confirmBtn.innerHTML = '<i class="fas fa-check mr-2"></i>Accept Allocation';
        }
    }

    confirmAllocation() {
        console.log('🔵 Confirm allocation clicked');
        console.log('Current batch allocations:', this.batchAllocations);

        if (this.batchAllocations.length === 0) {
            alert('No batches allocated. Please select at least one batch.');
            return;
        }

        // Filter out zero-quantity batches
        const validBatches = this.batchAllocations.filter(b => parseFloat(b.quantity) > 0);

        if (validBatches.length === 0) {
            alert('All batch quantities are zero. Please allocate some quantity.');
            return;
        }

        console.log('✅ Valid batches to apply:', validBatches);

        // Call the callback with allocated batches
        if (this.onConfirmCallback) {
            console.log('🔵 Calling callback function...');
            this.onConfirmCallback(validBatches);
        } else {
            console.error('❌ No callback function defined!');
        }

        this.hide();
    }

    hide() {
        this.modal.classList.add('hidden');
        this.currentMedicine = null;
        this.currentQuantity = 0;
        this.batchAllocations = [];
        this.onConfirmCallback = null;
    }

    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-IN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
}

// Export class globally
window.FIFOAllocationModal = FIFOAllocationModal;

// Initialize modal globally when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.fifoModal = new FIFOAllocationModal();
    console.log("✅ FIFO Allocation Modal ready");
});
