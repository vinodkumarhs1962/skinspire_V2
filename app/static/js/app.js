/**
 * Skinspire Healthcare - Master JavaScript
 * Central import file for all reusable JavaScript components
 */

// Import standard filter functionality
// (This will be loaded after standard-filters.js)

// Global Healthcare App Object
window.HealthcareApp = {
    filters: null,
    
    // Initialize all components
    init: function() {
        this.initializeGlobalComponents();
        console.log('HealthcareApp initialized');
    },
    
    // Global component initialization
    initializeGlobalComponents: function() {
        // Initialize FontAwesome fixes
        this.fixFontAwesome();
        
        // Initialize global event listeners
        this.bindGlobalEvents();
        
        // Initialize tooltips
        this.initializeTooltips();
    },
    
    // Fix FontAwesome rendering issues
    fixFontAwesome: function() {
        document.querySelectorAll('.fas, .far, .fab').forEach(icon => {
            icon.style.fontFamily = '"Font Awesome 5 Free"';
        });
    },
    
    // Global event bindings
    bindGlobalEvents: function() {
        // Global escape key handler
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                // Close any open dropdowns, modals, etc.
                document.querySelectorAll('.dropdown-menu:not(.hidden)').forEach(menu => {
                    menu.classList.add('hidden');
                });
            }
        });
        
        // Global click outside handler for dropdowns
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.dropdown')) {
                document.querySelectorAll('.dropdown-menu:not(.hidden)').forEach(menu => {
                    menu.classList.add('hidden');
                });
            }
        });
    },
    
    // Initialize tooltip functionality
    initializeTooltips: function() {
        // Add hover tooltips for truncated text
        document.querySelectorAll('.grid-cell-truncate').forEach(cell => {
            if (cell.scrollWidth > cell.clientWidth) {
                cell.title = cell.textContent.trim();
            }
        });
    },
    
    // Utility functions
    utils: {
        formatCurrency: function(amount, currency = '₹') {
            return `${currency}${parseFloat(amount).toFixed(2)}`;
        },
        
        formatDate: function(date, format = 'DD/MM/YYYY') {
            if (!date) return '';
            const d = new Date(date);
            const day = String(d.getDate()).padStart(2, '0');
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const year = d.getFullYear();
            
            switch (format) {
                case 'DD/MM/YYYY':
                    return `${day}/${month}/${year}`;
                case 'YYYY-MM-DD':
                    return `${year}-${month}-${day}`;
                default:
                    return `${day}/${month}/${year}`;
            }
        },
        
        showNotification: function(message, type = 'info') {
            // Simple notification system
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} fixed top-4 right-4 z-50`;
            notification.innerHTML = `
                <div class="alert-content">
                    <div class="alert-message">${message}</div>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.HealthcareApp.init();
});