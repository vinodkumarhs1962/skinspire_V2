/**
 * Skinspire Clinic - Common Utilities
 * This file contains reusable utility functions for the application.
 */

// Format date to a readable string
function formatDate(date, includeTime = false) {
    if (!date) return '';
    const dateObj = new Date(date);
    
    const options = { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    };
    
    if (includeTime) {
        options.hour = '2-digit';
        options.minute = '2-digit';
    }
    
    return dateObj.toLocaleDateString('en-US', options);
}

// Format currency values
function formatCurrency(amount, currency = 'INR') {
    if (amount === null || amount === undefined) return '';
    
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Debounce function for search inputs, etc.
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// Display a flash message
function showFlashMessage(message, type = 'success', duration = 3000) {
    // Create flash message container if it doesn't exist
    let container = document.getElementById('flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.id = 'flash-messages';
        container.className = 'fixed top-4 right-4 z-50 flex flex-col items-end space-y-2';
        document.body.appendChild(container);
    }
    
    // Create message element
    const flashElement = document.createElement('div');
    
    // Set appropriate styles based on message type
    let bgColor, textColor;
    switch(type) {
        case 'error':
            bgColor = 'bg-red-500';
            textColor = 'text-white';
            break;
        case 'warning':
            bgColor = 'bg-yellow-500';
            textColor = 'text-gray-900';
            break;
        case 'info':
            bgColor = 'bg-blue-500';
            textColor = 'text-white';
            break;
        case 'success':
        default:
            bgColor = 'bg-green-500';
            textColor = 'text-white';
            break;
    }
    
    flashElement.className = `${bgColor} ${textColor} px-4 py-2 rounded shadow-md flex items-center transform transition-all duration-300 ease-in-out`;
    flashElement.innerHTML = `
        <span>${message}</span>
        <button class="ml-3 focus:outline-none" onclick="this.parentElement.remove()">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        </button>
    `;
    
    // Add to container
    container.appendChild(flashElement);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (flashElement.parentElement) {
            flashElement.classList.add('opacity-0', 'translate-x-full');
            setTimeout(() => flashElement.remove(), 300);
        }
    }, duration);
}

// Export functions to make them available globally
window.utils = {
    formatDate,
    formatCurrency,
    debounce,
    showFlashMessage
};