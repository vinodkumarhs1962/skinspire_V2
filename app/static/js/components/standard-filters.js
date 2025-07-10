/**
 * ENHANCED StandardFilters - Central improvements to standard-filters.js
 * This replaces the existing standard-filters.js file with improved functionality
 */

class StandardFilters {
    constructor(options = {}) {
        this.options = {
            formId: 'filter-form',
            autoLoad: true,
            defaultPeriod: 'current-month',
            entityName: 'records',
            enableAutoSubmit: false,
            debounceMs: 300,
            enableTableEnhancements: true,
            enableSearchClear: true,
            enableTooltips: true,
            enableMobileOptimizations: true,
            searchPlaceholder: 'Search...',
            
            // ENHANCED: Better filter chip management
            enableFilterChips: true,
            chipContainer: '.filter-chips-container',
            
            // ENHANCED: Parameter name mapping for backward compatibility
            parameterMapping: {
                'supplier': ['supplier', 'supplier_search', 'supplier_name'],
                'status': ['status', 'payment_status', 'workflow_status'],
                'amount': ['min_amount', 'amount_min'],
                'method': ['payment_method', 'method']
            },
            
            // ENHANCED: Custom filter labels
            filterLabels: {
                'supplier': 'Supplier',
                'supplier_search': 'Supplier',
                'payment_method': 'Method',
                'min_amount': 'Min Amount',
                'start_date': 'From',
                'end_date': 'To',
                'payment_status': 'Status',
                'workflow_status': 'Status'
            },
            
            ...options
        };
        
        this.form = null;
        this.searchInput = null;
        this.startDate = null;
        this.endDate = null;
        this.presets = null;
        this.clearButton = null;
        this.summaryText = null;
        this.resultsCount = null;
        this.chipContainer = null;
        
        // Table enhancement properties
        this.dataTable = null;
        this.supplierCells = null;
        this.methodBadges = null;
        
        if (this.options.autoLoad) {
            this.init();
        }
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        this.findElements();
        this.bindEvents();
        this.initializeDefaults();
        
        if (this.options.enableTableEnhancements) {
            this.initializeTableEnhancements();
        }
        
        if (this.options.enableFilterChips) {
            this.initializeFilterChips();
        }
        
        console.log(`StandardFilters initialized for ${this.options.entityName}`);
    }

    findElements() {
        this.form = document.getElementById(this.options.formId);
        this.searchInput = document.getElementById('search-input');
        this.startDate = document.getElementById('start_date');
        this.endDate = document.getElementById('end_date');
        this.presets = document.querySelectorAll('.date-filter-preset');
        this.clearButton = document.querySelector('.search-input-clear');
        this.summaryText = document.getElementById('summary-text');
        this.resultsCount = document.getElementById('results-count');
        this.chipContainer = document.querySelector(this.options.chipContainer);
        
        // Table elements
        this.dataTable = document.querySelector('.data-table, table');
        this.supplierCells = document.querySelectorAll('.data-table td:nth-child(2), table td:nth-child(2)');
        this.methodBadges = document.querySelectorAll('.data-table .status-badge, table .status-badge');
    }

    bindEvents() {
        // ENHANCED: Search input with better error handling
        if (this.searchInput) {
            this.searchInput.addEventListener('input', 
                this.debounce(() => this.handleSearchInput(), this.options.debounceMs)
            );
            this.searchInput.addEventListener('keypress', (e) => this.handleSearchKeypress(e));
            this.searchInput.addEventListener('focus', () => this.handleSearchFocus());
            
            // Update placeholder if configured
            if (this.options.searchPlaceholder) {
                this.searchInput.placeholder = this.options.searchPlaceholder;
            }
        }

        // ENHANCED: Search clear button functionality
        if (this.clearButton && this.options.enableSearchClear) {
            this.clearButton.addEventListener('click', () => this.clearSearch());
            this.updateClearButtonVisibility();
        }

        // Date preset events
        if (this.presets) {
            this.presets.forEach((preset, index) => {
                preset.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.handlePresetClick(index);
                });
            });
        }

        // Form submission
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // ENHANCED: Listen for filter removal events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.filter-chip-remove')) {
                e.preventDefault();
                this.handleFilterChipRemove(e.target.closest('.filter-chip-remove'));
            }
        });
    }

    initializeDefaults() {
        this.setDefaultPeriod();
        this.updateSummary();
        this.updateClearButtonVisibility();
    }

    // ENHANCED: Initialize filter chips functionality
    initializeFilterChips() {
        this.renderFilterChips();
        
        // Add "Clear All" functionality if there are active filters
        if (this.hasActiveFilters()) {
            this.addClearAllButton();
        }
    }

    // ENHANCED: Render filter chips based on current form values
    renderFilterChips() {
        if (!this.chipContainer && !this.shouldCreateChipContainer()) {
            return;
        }
        
        // Create chip container if it doesn't exist
        if (!this.chipContainer) {
            this.createChipContainer();
        }
        
        // Clear existing chips
        this.chipContainer.innerHTML = '';
        
        const activeFilters = this.getActiveFilters();
        const chipWrapper = document.createElement('div');
        chipWrapper.className = 'flex flex-wrap items-center gap-2';
        
        if (activeFilters.length > 0) {
            // Add label
            const label = document.createElement('span');
            label.className = 'text-sm text-gray-600 dark:text-gray-400';
            label.textContent = 'Active filters:';
            chipWrapper.appendChild(label);
            
            // Add chips
            activeFilters.forEach(filter => {
                const chip = this.createFilterChip(filter.key, filter.value, filter.label);
                chipWrapper.appendChild(chip);
            });
            
            // Add clear all button
            const clearAllBtn = this.createClearAllButton();
            chipWrapper.appendChild(clearAllBtn);
        }
        
        this.chipContainer.appendChild(chipWrapper);
    }

    // ENHANCED: Get active filters with better parameter mapping
    getActiveFilters() {
        if (!this.form) return [];
        
        const formData = new FormData(this.form);
        const filters = [];
        
        for (let [key, value] of formData.entries()) {
            if (value && value.trim() && key !== 'page') {
                const label = this.getFilterLabel(key);
                const displayValue = this.formatFilterValue(key, value);
                
                filters.push({
                    key: key,
                    value: value,
                    label: label,
                    displayValue: displayValue
                });
            }
        }
        
        return filters;
    }

    // ENHANCED: Format filter values for display
    formatFilterValue(key, value) {
        // Handle different value types
        if (key === 'min_amount' || key === 'amount_min') {
            return `₹${parseFloat(value).toFixed(2)}`;
        }
        
        if (key === 'start_date' || key === 'end_date') {
            return this.formatDisplayDate(value);
        }
        
        // Handle select options - get display text if available
        const selectElement = this.form.querySelector(`select[name="${key}"]`);
        if (selectElement) {
            const option = selectElement.querySelector(`option[value="${value}"]`);
            if (option) {
                return option.textContent.trim();
            }
        }
        
        return value;
    }

    // ENHANCED: Create filter chip element
    createFilterChip(key, value, label) {
        const chip = document.createElement('span');
        chip.className = 'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
        chip.innerHTML = `
            ${label}: ${this.formatFilterValue(key, value)}
            <button type="button" 
                    class="filter-chip-remove ml-1 text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-100" 
                    data-filter-key="${key}"
                    title="Remove ${label} filter">
                <i class="fas fa-times text-xs"></i>
            </button>
        `;
        
        return chip;
    }

    // ENHANCED: Create clear all button
    createClearAllButton() {
        const clearAllBtn = document.createElement('a');
        clearAllBtn.href = window.location.pathname;
        clearAllBtn.className = 'text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200';
        clearAllBtn.textContent = 'Clear all';
        
        return clearAllBtn;
    }

    // ENHANCED: Handle filter chip removal
    handleFilterChipRemove(removeButton) {
        const filterKey = removeButton.dataset.filterKey;
        if (!filterKey) return;
        
        this.removeFilter(filterKey);
    }

    // ENHANCED: Remove specific filter
    removeFilter(filterKey) {
        if (!this.form) return;
        
        // Handle date range special case
        if (filterKey === 'date_range') {
            this.clearDates();
        } else {
            // Remove single filter
            const element = this.form.querySelector(`[name="${filterKey}"]`);
            if (element) {
                element.value = '';
            }
        }
        
        // Auto-submit if enabled, otherwise update chips
        if (this.options.enableAutoSubmit) {
            this.submitForm();
        } else {
            this.renderFilterChips();
            this.updateSummary();
        }
    }

    // ENHANCED: Search input handling
    handleSearchInput() {
        this.updateClearButtonVisibility();
        
        if (this.options.enableAutoSubmit) {
            this.submitForm();
        }
    }

    // ENHANCED: Search clear functionality
    clearSearch() {
        if (this.searchInput) {
            this.searchInput.value = '';
            this.updateClearButtonVisibility();
            this.searchInput.focus();
            
            if (this.options.enableAutoSubmit) {
                this.submitForm();
            }
        }
    }

    // ENHANCED: Update clear button visibility
    updateClearButtonVisibility() {
        if (!this.clearButton || !this.searchInput) return;
        
        const hasValue = this.searchInput.value.trim().length > 0;
        this.clearButton.style.display = hasValue ? 'block' : 'none';
    }

    // ENHANCED: Get filter label with better mapping
    getFilterLabel(key) {
        // Check custom labels first
        if (this.options.filterLabels[key]) {
            return this.options.filterLabels[key];
        }
        
        // Default label generation
        return key.replace(/_/g, ' ')
                 .replace(/\b\w/g, l => l.toUpperCase());
    }

    // ENHANCED: Handle form submission
    handleFormSubmit(e) {
        this.setLoadingState(true);
        console.log('Filter form submitted');
    }

    // ENHANCED: Check if chip container should be created
    shouldCreateChipContainer() {
        return this.hasActiveFilters() && this.form;
    }

    // ENHANCED: Create chip container dynamically
    createChipContainer() {
        if (!this.form) return;
        
        const container = document.createElement('div');
        container.className = 'filter-chips-container mb-4';
        
        // Insert after filter card
        const filterCard = document.querySelector('.filter-card');
        if (filterCard) {
            filterCard.insertAdjacentElement('afterend', container);
        } else {
            // Fallback: insert after form
            this.form.insertAdjacentElement('afterend', container);
        }
        
        this.chipContainer = container;
    }

    // ENHANCED: Better active filter detection
    hasActiveFilters() {
        if (!this.form) return false;
        
        const formData = new FormData(this.form);
        for (let [key, value] of formData.entries()) {
            if (value && value.trim() && key !== 'page') {
                return true;
            }
        }
        return false;
    }

    // ENHANCED: Date formatting for display
    formatDisplayDate(dateString) {
        if (!dateString) return '';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-IN', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
        } catch (e) {
            return dateString;
        }
    }

    // Existing methods with enhancements
    setDateRange(startDate, endDate) {
        if (this.startDate) this.startDate.value = this.formatDate(startDate);
        if (this.endDate) this.endDate.value = this.formatDate(endDate);
        this.updateActivePreset();
        this.renderFilterChips();
    }

    formatDate(date) {
        if (!date) return '';
        const d = new Date(date);
        return d.toISOString().split('T')[0];
    }

    setToday() {
        const today = new Date();
        this.setDateRange(today, today);
    }

    setCurrentMonth() {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        this.setDateRange(firstDay, lastDay);
    }

    setFinancialYear() {
        const now = new Date();
        const year = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
        const startDate = new Date(year, 3, 1); // April 1st
        const endDate = new Date(year + 1, 2, 31); // March 31st
        this.setDateRange(startDate, endDate);
    }

    clearDates() {
        this.setDateRange('', '');
    }

    updateActivePreset() {
        if (!this.presets) return;
        
        this.presets.forEach(preset => preset.classList.remove('active'));
        
        // Logic to determine which preset is active based on current dates
        // This is simplified - you may want to enhance this
        if (this.startDate && this.endDate) {
            const start = this.startDate.value;
            const end = this.endDate.value;
            
            if (start && end) {
                const today = this.formatDate(new Date());
                if (start === today && end === today) {
                    this.presets[0]?.classList.add('active'); // Today
                }
                // Add more preset detection logic as needed
            }
        }
    }

    updateSummary() {
        const recordCount = this.getCurrentRecordCount();
        const hasFilters = this.hasActiveFilters();
        
        if (this.resultsCount) {
            this.resultsCount.textContent = `${recordCount} ${hasFilters ? 'filtered ' : ''}results`;
        }
        
        if (this.summaryText) {
            this.summaryText.textContent = hasFilters 
                ? `Showing filtered ${this.options.entityName}` 
                : `All ${this.options.entityName}`;
        }
    }

    getCurrentRecordCount() {
        const countElement = document.querySelector('[data-record-count]');
        if (countElement) {
            return parseInt(countElement.dataset.recordCount) || 0;
        }
        
        if (this.dataTable) {
            const rows = this.dataTable.querySelectorAll('tbody tr');
            return rows.length;
        }
        
        return 0;
    }

    // Table enhancements
    initializeTableEnhancements() {
        if (!this.dataTable) return;
        
        // Add hover effects, tooltips, etc.
        this.addTableTooltips();
        this.addMobileEnhancements();
    }

    addTableTooltips() {
        if (!this.options.enableTooltips) return;
        
        // Add tooltips to truncated content
        this.supplierCells.forEach(cell => {
            if (cell.scrollWidth > cell.clientWidth) {
                cell.title = cell.textContent.trim();
            }
        });
    }

    addMobileEnhancements() {
        if (!this.options.enableMobileOptimizations) return;
        
        // Add mobile-specific table enhancements
        // This is a placeholder for mobile optimizations
    }

    // Loading states
    setLoadingState(loading) {
        const filterCard = document.querySelector('.filter-card');
        if (filterCard) {
            filterCard.classList.toggle('filter-loading', loading);
        }
        
        if (loading) {
            this.showLoadingOverlay();
        } else {
            this.hideLoadingOverlay();
        }
    }

    showLoadingOverlay() {
        let overlay = document.getElementById('filter-loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'filter-loading-overlay';
            overlay.className = 'fixed inset-0 bg-black bg-opacity-25 z-50 flex items-center justify-center';
            overlay.innerHTML = `
                <div class="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-lg">
                    <div class="flex items-center space-x-3">
                        <i class="fas fa-spinner fa-spin text-blue-500"></i>
                        <span class="text-gray-800 dark:text-gray-200">Applying filters...</span>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        overlay.style.display = 'flex';
    }

    hideLoadingOverlay() {
        const overlay = document.getElementById('filter-loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    // Utility functions
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Public API
    reset() {
        if (this.form) {
            this.form.reset();
        }
        this.clearSearch();
        this.setDefaultPeriod();
        this.renderFilterChips();
        this.updateSummary();
    }

    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        
        if (this.searchInput && newOptions.searchPlaceholder) {
            this.searchInput.placeholder = newOptions.searchPlaceholder;
        }
    }

    getFilterData() {
        if (!this.form) return {};
        
        const formData = new FormData(this.form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            if (value && value.trim()) {
                data[key] = value;
            }
        }
        return data;
    }

    setFilterData(data) {
        if (!this.form) return;
        
        Object.keys(data).forEach(key => {
            const element = this.form.querySelector(`[name="${key}"]`);
            if (element) {
                element.value = data[key];
            }
        });
        
        this.renderFilterChips();
        this.updateSummary();
    }

    refreshTableEnhancements() {
        this.findElements();
        if (this.options.enableTableEnhancements) {
            setTimeout(() => this.initializeTableEnhancements(), 100);
        }
    }

    submitForm() {
        if (this.form) {
            this.setLoadingState(true);
            this.form.submit();
        }
    }

    setDefaultPeriod() {
        if (this.options.defaultPeriod === 'current-month') {
            this.setCurrentMonth();
        }
    }

    handlePresetClick(index) {
        const presetFunctions = [
            () => this.setToday(),
            () => this.setCurrentMonth(), 
            () => this.setFinancialYear(),
            () => this.clearDates()
        ];
        
        if (presetFunctions[index]) {
            presetFunctions[index]();
            
            if (this.options.enableAutoSubmit) {
                this.submitForm();
            }
        }
    }

    handleSearchKeypress(e) {
        if (e.key === 'Enter' && this.options.enableAutoSubmit) {
            e.preventDefault();
            this.submitForm();
        }
    }

    handleSearchFocus() {
        // Add any focus-specific logic here
    }
}

// Export for use in other scripts
window.StandardFilters = StandardFilters;

// ENHANCED: Auto-initialization with better detection
document.addEventListener('DOMContentLoaded', function() {
    // Check for data attribute initialization first
    const autoInitElement = document.querySelector('[data-standard-filters]');
    if (autoInitElement) {
        const options = JSON.parse(autoInitElement.dataset.standardFilters || '{}');
        window.standardFilters = new StandardFilters(options);
        return;
    }
    
    // Auto-initialize for specific page types
    const paymentListForm = document.querySelector('form[action*="payment_list"]');
    if (paymentListForm && !window.standardFilters) {
        window.standardFilters = new StandardFilters({
            formId: paymentListForm.id || 'filter-form',
            entityName: 'payments',
            enableTableEnhancements: true,
            enableSearchClear: true,
            enableFilterChips: true,
            searchPlaceholder: 'Search by supplier name...',
            enableAutoSubmit: false,
            filterLabels: {
                'supplier': 'Supplier',
                'supplier_search': 'Supplier',
                'payment_method': 'Payment Method',
                'min_amount': 'Min Amount',
                'payment_status': 'Status'
            }
        });
        return;
    }
    
    // Auto-initialize for supplier invoice lists
    const supplierInvoiceForm = document.querySelector('form[action*="supplier_invoice_list"]');
    if (supplierInvoiceForm && !window.standardFilters) {
        window.standardFilters = new StandardFilters({
            formId: supplierInvoiceForm.id || 'filter-form',
            entityName: 'invoices',
            enableTableEnhancements: true,
            enableSearchClear: true,
            enableFilterChips: true,
            searchPlaceholder: 'Search invoices...',
            enableAutoSubmit: false
        });
        return;
    }
    
    // Generic form with filter-form ID
    const genericFilterForm = document.getElementById('filter-form');
    if (genericFilterForm && !window.standardFilters) {
        window.standardFilters = new StandardFilters({
            enableTableEnhancements: true,
            enableSearchClear: true,
            enableFilterChips: true
        });
    }
});