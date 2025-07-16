/**
 * ==========================================
 * UNIVERSAL UTILITIES - Minimal JavaScript
 * File: app/static/js/components/universal_utils.js  
 * ==========================================
 */

/**
 * Show loading state
 * Simple visual feedback while Flask processes request
 */
function showLoadingState() {
    document.body.classList.add('universal-loading');
    
    // Add loading spinner if it doesn't exist
    if (!document.querySelector('.universal-loading-spinner')) {
        const spinner = document.createElement('div');
        spinner.className = 'universal-loading-spinner';
        spinner.innerHTML = `
            <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                        background: white; padding: 1rem; border-radius: 0.5rem; box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                        display: flex; align-items: center; gap: 0.5rem; z-index: 9999;">
                <div style="width: 1rem; height: 1rem; border: 2px solid #e5e7eb; border-top: 2px solid #3b82f6; 
                           border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <span>Loading...</span>
            </div>
            <style>
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
        `;
        document.body.appendChild(spinner);
    }
}

/**
 * Hide loading state
 * Called when page loads or navigation completes
 */
function hideLoadingState() {
    document.body.classList.remove('universal-loading');
    
    const spinner = document.querySelector('.universal-loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

/**
 * Show export message
 * User feedback for export operations
 */
function showExportMessage(format) {
    const message = document.createElement('div');
    message.className = 'universal-export-message';
    message.innerHTML = `
        <div style="position: fixed; top: 1rem; right: 1rem; 
                    background: #10b981; color: white; padding: 0.75rem 1rem; 
                    border-radius: 0.5rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    display: flex; align-items: center; gap: 0.5rem; z-index: 9999;">
            <svg style="width: 1rem; height: 1rem;" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
            </svg>
            <span>Export (${format.toUpperCase()}) started!</span>
        </div>
    `;
    
    document.body.appendChild(message);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (message.parentNode) {
            message.parentNode.removeChild(message);
        }
    }, 3000);
}

/**
 * Handle date preset clicks
 * Sets date range in form and submits to Flask backend
 */
// function handleDatePreset(preset) {
//     const form = document.getElementById('universal-filter-form');
//     if (!form) return;
    
//     // Get current date
//     const today = new Date();
//     let startDate, endDate;
    
//     switch (preset) {
//         case 'today':
//             startDate = endDate = today.toISOString().split('T')[0];
//             break;
//         case 'yesterday':
//             const yesterday = new Date(today);
//             yesterday.setDate(yesterday.getDate() - 1);
//             startDate = endDate = yesterday.toISOString().split('T')[0];
//             break;
//         case 'this_week':
//             const weekStart = new Date(today);
//             weekStart.setDate(today.getDate() - today.getDay());
//             startDate = weekStart.toISOString().split('T')[0];
//             endDate = today.toISOString().split('T')[0];
//             break;
//         case 'this_month':
//             startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
//             endDate = today.toISOString().split('T')[0];
//             break;
//         case 'last_30_days':
//             const thirtyDaysAgo = new Date(today);
//             thirtyDaysAgo.setDate(today.getDate() - 30);
//             startDate = thirtyDaysAgo.toISOString().split('T')[0];
//             endDate = today.toISOString().split('T')[0];
//             break;
//         default:
//             return;
//     }
    
//     // Set date inputs if they exist
//     const startDateInput = form.querySelector('[name="start_date"], [name="date_from"]');
//     const endDateInput = form.querySelector('[name="end_date"], [name="date_to"]');
    
//     if (startDateInput) startDateInput.value = startDate;
//     if (endDateInput) endDateInput.value = endDate;
    
//     // Submit form to Flask backend
//     form.submit();
// }

/**
 * Initialize universal components when page loads
 * Main entry point for all universal JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // Hide loading state when page is ready
    hideLoadingState();
    
    // Setup universal components
    if (typeof initializeUniversalForms !== 'undefined') {
        initializeUniversalForms();
    }
    
    console.log('🚀 Universal Engine JavaScript initialized');
    console.log('📋 Backend-heavy mode: Most logic handled by Flask');
});

/**
 * ==========================================
 * GLOBAL UNIVERSAL FUNCTIONS
 * Available throughout the application
 * ==========================================
 */

// Export functions to global scope for template usage
window.handleUniversalSort = handleUniversalSort;
window.handleUniversalPagination = handleUniversalPagination;
window.handleUniversalExport = handleUniversalExport;
window.clearUniversalFilters = clearUniversalFilters;
// window.handleDatePreset = handleDatePreset;
window.showLoadingState = showLoadingState;
window.hideLoadingState = hideLoadingState;