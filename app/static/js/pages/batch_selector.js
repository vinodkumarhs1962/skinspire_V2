// static/js/components/batch_selector.js

const BatchSelector = (function() {
    // Private properties
    let container;
    let batches;
    let onSelectCallback;
    
    // Initialize the batch selector
    function init(containerElement, batchData, callback) {
        container = containerElement;
        batches = batchData;
        onSelectCallback = callback;
        
        render();
    }
    
    // Render the batch selector component
    function render() {
        container.innerHTML = '';
        
        if (!batches || batches.length === 0) {
            container.innerHTML = '<div class="text-red-500 text-sm mt-2">No batches available</div>';
            return;
        }
        
        // Sort batches by expiry date (FIFO)
        batches.sort((a, b) => new Date(a.expiry) - new Date(b.expiry));
        
        // Create table for batches
        const table = document.createElement('table');
        table.className = 'min-w-full bg-white dark:bg-gray-800 text-sm mt-2 border dark:border-gray-700';
        
        // Table header
        const thead = document.createElement('thead');
        thead.innerHTML = `
            <tr class="bg-gray-50 dark:bg-gray-700">
                <th class="px-2 py-1 text-left">Select</th>
                <th class="px-2 py-1 text-left">Batch</th>
                <th class="px-2 py-1 text-left">Expiry</th>
                <th class="px-2 py-1 text-right">Available</th>
                <th class="px-2 py-1 text-right">Sale Price</th>
            </tr>
        `;
        table.appendChild(thead);
        
        // Table body
        const tbody = document.createElement('tbody');
        
        batches.forEach((batch, index) => {
            const tr = document.createElement('tr');
            tr.className = index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50 dark:bg-gray-700';
            
            // Format expiry date
            const expiryDate = new Date(batch.expiry);
            const formattedExpiry = expiryDate.toLocaleDateString();
            
            // Check if expiring soon (within 90 days)
            const today = new Date();
            const daysUntilExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
            const expiryClass = daysUntilExpiry <= 90 ? 'text-red-500 font-bold' : '';
            
            tr.innerHTML = `
                <td class="px-2 py-1">
                    <input type="radio" name="batch-select" id="batch-${batch.batch}" 
                           ${index === 0 ? 'checked' : ''} class="batch-radio">
                </td>
                <td class="px-2 py-1">${batch.batch}</td>
                <td class="px-2 py-1 ${expiryClass}">${formattedExpiry}</td>
                <td class="px-2 py-1 text-right">${batch.current_stock}</td>
                <td class="px-2 py-1 text-right">${batch.sale_price}</td>
            `;
            
            tbody.appendChild(tr);
            
            // Add click event for the radio button
            tr.querySelector('.batch-radio').addEventListener('change', function() {
                selectBatch(batch);
            });
        });
        
        table.appendChild(tbody);
        container.appendChild(table);
        
        // Select the first batch by default
        if (batches.length > 0) {
            selectBatch(batches[0]);
        }
    }
    
    // Handle batch selection
    function selectBatch(batch) {
        if (onSelectCallback) {
            onSelectCallback(batch);
        }
    }
    
    // Public API
    return {
        init: init
    };
})();