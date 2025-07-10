/**
 * ==========================================
 * UNIVERSAL NAVIGATION - Minimal JavaScript  
 * File: app/static/js/components/universal_navigation.js
 * ==========================================
 */

/**
 * Handle table sorting clicks
 * Navigates to Flask backend URL with sort parameters
 */
function handleUniversalSort(columnName, currentSort) {
    const url = new URL(window.location);
    
    // Determine new sort direction
    let newDirection = 'asc';
    if (currentSort && currentSort.field === columnName) {
        newDirection = currentSort.direction === 'asc' ? 'desc' : 'asc';
    }
    
    // Set sort parameters
    url.searchParams.set('sort', columnName);
    url.searchParams.set('direction', newDirection);
    url.searchParams.delete('page'); // Reset to first page when sorting
    
    // Navigate to Flask backend
    showLoadingState();
    window.location.href = url.toString();
}

/**
 * Handle pagination clicks
 * Navigates to Flask backend URL with page parameters
 */
function handleUniversalPagination(page) {
    const url = new URL(window.location);
    url.searchParams.set('page', page);
    
    // Navigate to Flask backend
    showLoadingState();
    window.location.href = url.toString();
}

/**
 * Handle export functionality
 * Submits current filters to Flask backend export endpoint
 */
function handleUniversalExport(format = 'csv') {
    const form = document.getElementById('universal-filter-form');
    if (!form) {
        console.error('Universal filter form not found');
        return;
    }
    
    // Create a copy of the form for export
    const exportForm = form.cloneNode(true);
    exportForm.id = 'universal-export-form';
    
    // Add export parameter
    const exportInput = document.createElement('input');
    exportInput.type = 'hidden';
    exportInput.name = 'export';
    exportInput.value = format;
    exportForm.appendChild(exportInput);
    
    // Submit to current URL (Flask backend handles export)
    exportForm.method = 'GET';
    exportForm.action = window.location.pathname;
    
    // Add to page, submit, then remove
    document.body.appendChild(exportForm);
    exportForm.submit();
    document.body.removeChild(exportForm);
    
    // Show export message
    showExportMessage(format);
}

/**
 * Clear all filters
 * Navigates to clean Flask backend URL
 */
function clearUniversalFilters() {
    const url = new URL(window.location);
    
    // Keep only essential parameters (entity type, etc.)
    const allowedParams = ['entity_type'];
    const newUrl = new URL(url.pathname, url.origin);
    
    allowedParams.forEach(param => {
        if (url.searchParams.has(param)) {
            newUrl.searchParams.set(param, url.searchParams.get(param));
        }
    });
    
    // Navigate to Flask backend
    showLoadingState();
    window.location.href = newUrl.toString();
}