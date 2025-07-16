/**
 * =============================================================================
 * UNIVERSAL FORMS JAVASCRIPT - CORE LIBRARY
 * File: /static/js/components/universal_forms.js
 * =============================================================================
 * 
 * Universal Engine Core JavaScript Library
 * Backend-Heavy Architecture | Configuration-Driven | Entity-Agnostic
 * 
 * Features:
 * ✅ Universal Filter Management
 * ✅ Date Presets with Financial Year Logic
 * ✅ Active Filters Display and Management
 * ✅ Entity Search Integration
 * ✅ Auto-Submit Form Handling
 * ✅ Mobile Responsive Behavior
 * ✅ Error Handling and Fallbacks
 */

// =============================================================================
// UNIVERSAL FORMS CORE CLASS
// =============================================================================

class UniversalFormsEngine {
    constructor(config = {}) {
        this.config = {
            autoSubmitDelay: 800,
            entitySearchMinChars: 2,
            entitySearchDelay: 300,
            maxActiveFilterDisplay: 10,
            financialYearStartMonth: 3, // April (0-based)
            ...config
        };
        
        this.state = {
            filterFormSubmitTimeout: null,
            activeFiltersCache: {},
            entitySearchCache: {},
            currentEntityType: null,
            isInitialized: false
        };
        
        console.log('🚀 Universal Forms Engine initialized');
    }

    // =============================================================================
    // INITIALIZATION METHODS
    // =============================================================================

    initialize(entityType = null) {
        if (this.state.isInitialized) {
            console.warn('Universal Forms Engine already initialized');
            return;
        }

        this.state.currentEntityType = entityType;
        
        try {
            this.initializeFilterForm();
            this.initializeDatePresets();
            this.initializeActiveFiltersDisplay();
            this.initializeEntitySearch();
            this.initializeFilterAutoSubmit();
            this.initializeMobileHandlers();
            this.bindGlobalEvents();
            
            this.state.isInitialized = true;
            console.log('✅ Universal Forms Engine fully initialized for entity:', entityType);
        } catch (error) {
            console.error('❌ Error initializing Universal Forms Engine:', error);
        }
    }

    initializeFilterForm() {
        const form = this.getFilterForm();
        if (!form) return;
        
        // Prevent multiple rapid submissions
        form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Handle form reset
        const clearBtn = form.querySelector('.universal-clear-all-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearAllFilters());
        }
        
        console.log('✅ Filter form initialized');
    }

    initializeDatePresets() {
        const presetButtons = document.querySelectorAll('.universal-date-preset-btn');
        
        presetButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const preset = button.getAttribute('data-preset');
                this.applyDatePreset(preset);
            });
        });
        
        // Set default preset if no dates are selected
        this.setDefaultDatePreset();
        
        console.log('✅ Date presets initialized');
    }

    initializeActiveFiltersDisplay() {
        this.updateActiveFiltersDisplay();
        console.log('✅ Active filters display initialized');
    }

    initializeEntitySearch() {
        const entitySearchFields = document.querySelectorAll('[data-entity-search]');
        
        entitySearchFields.forEach(field => {
            this.setupEntitySearchField(field);
        });
        
        console.log('✅ Entity search initialized');
    }

    initializeFilterAutoSubmit() {
        const form = this.getFilterForm();
        if (!form) return;
        
        // ✅ Check entity-level auto-submit configuration
        const entityConfig = window.assembledData?.entity_config || {};
        const autoSubmitEnabled = entityConfig.enable_auto_submit !== false; // Default to true
        
        console.log('🔧 Auto-submit configuration:', {
            entityType: entityConfig.entity_type,
            autoSubmitEnabled: autoSubmitEnabled
        });
        
        if (autoSubmitEnabled) {
            // ✅ ENABLE AUTO-SUBMIT: Add event listeners
            const autoSubmitFields = form.querySelectorAll('.universal-filter-auto-submit');
            
            autoSubmitFields.forEach(field => {
                if (field.tagName === 'SELECT') {
                    field.addEventListener('change', (e) => this.handleAutoSubmit(e));
                } else if (field.type === 'date') {
                    field.addEventListener('change', (e) => this.handleAutoSubmit(e));
                } else {
                    field.addEventListener('input', (e) => this.handleDebouncedAutoSubmit(e));
                    field.addEventListener('change', (e) => this.handleAutoSubmit(e));
                }
            });
            
            console.log('✅ Auto-submit enabled for', autoSubmitFields.length, 'fields');
        } else {
            // ✅ DISABLE AUTO-SUBMIT: Remove auto-submit classes and show Apply button
            const autoSubmitFields = form.querySelectorAll('.universal-filter-auto-submit');
            autoSubmitFields.forEach(field => {
                field.classList.remove('universal-filter-auto-submit');
                // Add visual indication that manual submit is required
                field.classList.add('universal-manual-submit');
            });
            
            // Ensure Apply button is visible
            const applyButton = form.querySelector('.universal-apply-filters-btn');
            if (applyButton) {
                applyButton.style.display = 'flex';
            }
            
            console.log('✅ Auto-submit disabled - Apply button mode enabled');
        }
    }

    // ✅ NEW: Enhanced form submission with loading states
    handleFormSubmit(event) {
        const form = event.target;
        const submitBtn = form.querySelector('.universal-apply-filters-btn');
        
        if (submitBtn) {
            // Show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Applying Filters...';
            
            // Reset after form submission
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-search"></i> Apply Filters';
            }, 2000);
        }
        
        // Add loading class to form fields
        const formFields = form.querySelectorAll('.universal-form-input');
        formFields.forEach(field => field.classList.add('loading'));
    }

    // ✅ NEW: Enhanced auto-submit with visual feedback
    handleAutoSubmit(event) {
        const field = event.target;
        
        // Add loading visual feedback
        field.classList.add('loading');
        
        this.updateActiveFiltersDisplay();
        
        if (this.state.filterFormSubmitTimeout) {
            clearTimeout(this.state.filterFormSubmitTimeout);
        }
        
        this.state.filterFormSubmitTimeout = setTimeout(() => {
            this.submitFilterForm();
            
            // Remove loading state after submission
            setTimeout(() => {
                field.classList.remove('loading');
            }, 1000);
        }, 500);
    }

    initializeMobileHandlers() {
        // Handle mobile filter toggle
        const filterToggle = document.querySelector('.universal-filter-toggle');
        if (filterToggle) {
            filterToggle.addEventListener('click', () => this.toggleMobileFilters());
        }
        
        // Handle mobile date preset layout
        if (window.innerWidth <= 640) {
            const datePresets = document.querySelector('.universal-date-presets');
            if (datePresets) {
                datePresets.classList.add('mobile-grid');
            }
        }
        
        console.log('✅ Mobile handlers initialized');
    }

    bindGlobalEvents() {
        // Global error handling
        window.addEventListener('error', (event) => {
            console.error('Universal Forms Error:', event.error);
        });

        // Make key methods globally available for inline handlers
        window.universalForms = {
            applyDatePreset: (preset) => this.applyDatePreset(preset),
            clearDateFilters: () => this.clearDateFilters(),
            removeActiveFilter: (fieldName) => this.removeActiveFilter(fieldName),
            clearAllFilters: () => this.clearAllFilters(),
            submitFilterForm: () => this.submitFilterForm()
        };
        // ✅ BACKUP: Direct window exposure for compatibility
        window.handleDatePreset = (preset) => this.applyDatePreset(preset); 
    }

    // =============================================================================
    // DATE PRESETS FUNCTIONALITY
    // =============================================================================

    setDefaultDatePreset() {
        console.log('🚫 Auto date preset temporarily disabled for testing');
        return; // Exit early
        const startDateField = document.getElementById('start_date');
        const endDateField = document.getElementById('end_date');
        
        if (startDateField && endDateField) {
            // ✅ Check URL parameters first
            const urlParams = new URLSearchParams(window.location.search);
            const hasUrlStartDate = urlParams.get('start_date');
            const hasUrlEndDate = urlParams.get('end_date');
            
            // ✅ Check current field values
            const hasFieldStartDate = startDateField.value.trim();
            const hasFieldEndDate = endDateField.value.trim();
            
            console.log('🔍 Default preset check:', {
                hasUrlStartDate,
                hasUrlEndDate,
                hasFieldStartDate,
                hasFieldEndDate
            });
            
            // // ✅ Check if user has submitted form with other filters (intentional filter application)
            // const hasOtherFilters = urlParams.get('supplier_id') || urlParams.get('supplier_search') || 
            //                     urlParams.get('search') || urlParams.get('workflow_status') || 
            //                     urlParams.get('payment_method') || urlParams.get('reference_no');

            // ✅ Check if user has submitted form with other filters (intentional filter application)
            const hasOtherFilters = urlParams.get('supplier_id') || urlParams.get('supplier_search') || 
                                urlParams.get('search') || urlParams.get('workflow_status') || 
                                urlParams.get('payment_method') || urlParams.get('reference_no') ||
                                urlParams.get('supplier_name_search') || urlParams.get('amount_min') ||
                                urlParams.get('amount_max');

            // ✅ If no dates in URL or fields, apply Financial Year default ONLY if no other filters
            if (!hasUrlStartDate && !hasUrlEndDate && !hasFieldStartDate && !hasFieldEndDate && !hasOtherFilters) {
                
                // ✅ SMART CHECK: Is this a fresh page visit or navigation from filters?
                const isPageRefresh = performance.navigation.type === 1; // TYPE_RELOAD
                const isBackNavigation = performance.navigation.type === 2; // TYPE_BACK_FORWARD
                const hasNavigationContext = document.referrer.includes('/universal/');
                
                // ✅ ONLY auto-apply FY on truly fresh visits, not when user is navigating/filtering
                if (!isPageRefresh && !isBackNavigation && !hasNavigationContext) {
                    console.log('✅ Fresh visit - applying Financial Year preset');
                    this.applyDatePreset('financial_year', false);
                } else {
                    console.log('🔧 User navigation detected - skipping auto Financial Year');
                    // ✅ Still detect what preset is active based on current dates
                    this.updateActiveDatePreset();
                }
                return;
            }
            
            // ✅ If dates exist, detect which preset is active
            if (hasFieldStartDate || hasFieldEndDate) {
                this.updateActiveDatePreset();
            }
        }
    }

    applyDatePreset(presetValue, autoSubmit = true) {
        console.log(`📅 Applying date preset: ${presetValue}`);
        
        const dates = this.calculatePresetDates(presetValue);
        if (!dates) return;
        
        // Set the date fields
        const startDateField = document.getElementById('start_date');
        const endDateField = document.getElementById('end_date');
        
        if (startDateField) {
            startDateField.value = dates.startDate;
            startDateField.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        if (endDateField) {
            endDateField.value = dates.endDate;
            endDateField.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        // Update UI
        this.updateActiveDatePresetButton(presetValue);
        this.updateActiveFiltersDisplay();
        
        // Auto-submit if requested
        if (autoSubmit) {
            setTimeout(() => this.submitFilterForm(), 100);
        }
    }

    calculatePresetDates(presetValue) {
        const today = new Date();
        today.setHours(0, 0, 0, 0); // Reset time to midnight for consistency
        let startDate = '';
        let endDate = '';
        
        switch(presetValue) {
            case 'today':
                startDate = endDate = this.formatDateForInput(today);
                break;
                
            case 'yesterday':
                const yesterday = new Date(today);
                yesterday.setDate(yesterday.getDate() - 1);
                startDate = endDate = this.formatDateForInput(yesterday);
                break;
                
            case 'this_week':
                const startOfWeek = new Date(today);
                startOfWeek.setDate(today.getDate() - today.getDay());
                startDate = this.formatDateForInput(startOfWeek);
                endDate = this.formatDateForInput(today);
                break;
                
            case 'this_month':
                const currentDate = new Date(); // Always get fresh current date
                const firstDayOfCurrentMonth = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
                startDate = this.formatDateForInput(firstDayOfCurrentMonth);
                endDate = this.formatDateForInput(currentDate);
                break;
                
            case 'last_30_days':
                const thirtyDaysAgo = new Date(today);
                thirtyDaysAgo.setDate(today.getDate() - 30);
                startDate = this.formatDateForInput(thirtyDaysAgo);
                endDate = this.formatDateForInput(today);
                break;
                
            case 'financial_year':
                const fyDates = this.getFinancialYearDates(today);
                startDate = this.formatDateForInput(fyDates.start);
                endDate = this.formatDateForInput(fyDates.end);
                break;
                
            case 'clear':
                startDate = '';
                endDate = '';
                break;
                
            default:
                console.warn(`Unknown date preset: ${presetValue}`);
                return null;
        }
        
        return { startDate, endDate };
    }

    getFinancialYearDates(currentDate) {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        
        let fyStart, fyEnd;
        
        if (month >= this.config.financialYearStartMonth) {
            fyStart = new Date(year, this.config.financialYearStartMonth, 1);
            fyEnd = new Date(year + 1, this.config.financialYearStartMonth - 1, 31);
        } else {
            fyStart = new Date(year - 1, this.config.financialYearStartMonth, 1);
            fyEnd = new Date(year, this.config.financialYearStartMonth - 1, 31);
        }
        
        return { start: fyStart, end: fyEnd };
    }

    updateActiveDatePreset() {
        const startDate = document.getElementById('start_date')?.value;
        const endDate = document.getElementById('end_date')?.value;
        
        if (!startDate || !endDate) {
            this.updateActiveDatePresetButton('clear');
            return;
        }
        
        const start = new Date(startDate);
        const end = new Date(endDate);
        const today = new Date();
        
        if (startDate === endDate && startDate === this.formatDateForInput(today)) {
            this.updateActiveDatePresetButton('today');
        } else if (this.isThisMonthPreset(start, end, today)) {
            this.updateActiveDatePresetButton('this_month');
        } else if (this.isFinancialYearPreset(start, end, today)) {
            this.updateActiveDatePresetButton('financial_year');
        } else {
            this.updateActiveDatePresetButton('custom');
        }
    }

    isThisMonthPreset(start, end, today) {
        const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        return start.toDateString() === monthStart.toDateString() && 
               end.toDateString() === today.toDateString();
    }

    isFinancialYearPreset(start, end, today) {
        const fyDates = this.getFinancialYearDates(today);
        return start.toDateString() === fyDates.start.toDateString() && 
               end.toDateString() === fyDates.end.toDateString();
    }

    updateActiveDatePresetButton(activePreset) {
        const presetButtons = document.querySelectorAll('.universal-date-preset-btn');
        
        presetButtons.forEach(button => {
            button.classList.remove('active');
            if (button.getAttribute('data-preset') === activePreset) {
                button.classList.add('active');
            }
        });
    }

    clearDateFilters() {
        this.applyDatePreset('clear');
    }

    // =============================================================================
    // ACTIVE FILTERS MANAGEMENT
    // =============================================================================

    updateActiveFiltersDisplay() {
        const form = this.getFilterForm();
        if (!form) return;
        
        const activeFilters = this.getActiveFilters();
        let container = document.getElementById('active-filters-display');
        
        if (activeFilters.length === 0) {
            if (container) {
                container.style.display = 'none';
            }
            return;
        }
        
        if (!container) {
            container = this.createActiveFiltersContainer();
            const filterForm = document.querySelector('.universal-filter-card-body');
            if (filterForm) {
                filterForm.appendChild(container);
            }
        }
        
        container.innerHTML = this.generateActiveFiltersHTML(activeFilters);
        container.style.display = 'block';
        
        this.updateFilterCountBadge(activeFilters.length);
    }

    getActiveFilters() {
        const form = this.getFilterForm();
        if (!form) return [];
        
        const filters = [];
        const formData = new FormData(form);
        const skipFields = ['page', 'per_page', 'sort', 'direction'];
        
        // ✅ Enhanced FY detection using backend state
        const backendState = document.getElementById('backend-filter-state');
        const startDate = formData.get('start_date');
        const endDate = formData.get('end_date');
        
        let isFinancialYear = false;
        
        if (backendState && backendState.dataset.isDefaultState === 'true') {
            // ✅ Backend says we're in default FY state
            isFinancialYear = true;
        } else if (startDate && endDate) {
            // ✅ Fallback: Check if dates match FY calculation
            const fyDates = this.calculatePresetDates('financial_year');
            isFinancialYear = startDate === fyDates.startDate && endDate === fyDates.endDate;
        }

        for (const [key, value] of formData.entries()) {
            if (value && value.trim() && !skipFields.includes(key)) {
                const field = form.querySelector(`[name="${key}"]`);
                let displayValue = value;
                
                // Special handling for financial year dates
                if ((key === 'start_date' || key === 'end_date') && isFinancialYear) {
                    if (key === 'start_date') {
                        filters.push({
                            key: 'date_range',
                            value: 'financial_year',
                            displayValue: 'Financial Year',
                            label: 'Date Range'
                        });
                    }
                    continue; // Skip individual date fields when showing as preset
                }

                if (field && field.tagName === 'SELECT') {
                    const selectedOption = field.options[field.selectedIndex];
                    displayValue = selectedOption ? selectedOption.text : value;
                }
                
                if (field && field.type === 'date') {
                    displayValue = this.formatDateForDisplay(value);
                }
                
                filters.push({
                    key: key,
                    label: this.formatFieldLabel(key),
                    value: displayValue,
                    rawValue: value
                });
            }
        }
        
        return filters;
    }

    createActiveFiltersContainer() {
        const container = document.createElement('div');
        container.id = 'active-filters-display';
        container.className = 'universal-active-filters';
        return container;
    }

    generateActiveFiltersHTML(filters) {
        if (filters.length === 0) return '';
        
        let html = `
            <div class="universal-active-filters-list">
                <span class="universal-active-filters-label">
                    <i class="fas fa-filter"></i>Active filters:
                </span>
        `;
        
        filters.forEach(filter => {
            html += `
                <span class="universal-filter-tag">
                    <span class="filter-name">${filter.label}:</span>
                    <span class="filter-value">${filter.value}</span>
                    <button type="button" 
                            class="universal-filter-remove"
                            onclick="window.universalForms.removeActiveFilter('${filter.key}')"
                            title="Remove this filter">
                        <i class="fas fa-times"></i>
                    </button>
                </span>
            `;
        });
        
        html += `
                <button type="button" 
                        class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200 ml-2"
                        onclick="window.universalForms.clearAllFilters()">
                    <i class="fas fa-times-circle mr-1"></i>Clear all filters
                </button>
            </div>
        `;
        
        return html;
    }

    removeActiveFilter(fieldName) {
        console.log(`🗑️ Removing filter: ${fieldName}`);
        
        const form = this.getFilterForm();
        if (!form) return;
        
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (field) {
            if (field.type === 'checkbox' || field.type === 'radio') {
                field.checked = false;
            } else {
                field.value = '';
            }
            
            field.dispatchEvent(new Event('change', { bubbles: true }));
            this.updateActiveFiltersDisplay();
            this.updateActiveDatePreset();
            
            setTimeout(() => this.submitFilterForm(), 100);
        }
    }

    clearAllFilters() {
        console.log('🗑️ Clearing all filters');
        
        const form = this.getFilterForm();
        if (form) {
            // Clear all form fields
            form.reset();
            
            // Remove all URL parameters except essential ones
            const url = new URL(window.location);
            const preserveParams = ['entity_type'];
            const newUrl = new URL(url.pathname, url.origin);
            
            preserveParams.forEach(param => {
                if (url.searchParams.has(param)) {
                    newUrl.searchParams.set(param, url.searchParams.get(param));
                }
            });
            
            // Navigate to clean URL - backend will apply defaults
            window.location.href = newUrl.toString();
        }
    }

    // =============================================================================
    // FORM SUBMISSION AND AUTO-SUBMIT
    // =============================================================================

    handleFormSubmit(event) {
        const form = event.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Applying...';
            
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-search"></i> Apply Filters';
            }, 2000);
        }
    }

    handleAutoSubmit(event) {
        this.updateActiveFiltersDisplay();
        
        if (this.state.filterFormSubmitTimeout) {
            clearTimeout(this.state.filterFormSubmitTimeout);
        }
        
        this.state.filterFormSubmitTimeout = setTimeout(() => {
            this.submitFilterForm();
        }, 500);
    }

    handleDebouncedAutoSubmit(event) {
        this.updateActiveFiltersDisplay();
        
        if (this.state.filterFormSubmitTimeout) {
            clearTimeout(this.state.filterFormSubmitTimeout);
        }
        
        this.state.filterFormSubmitTimeout = setTimeout(() => {
            this.submitFilterForm();
        }, this.config.autoSubmitDelay);
    }

    submitFilterForm() {
        const form = this.getFilterForm();
        if (!form) return;
        
        // Reset page to 1 when filters change
        const pageInput = form.querySelector('[name="page"]');
        if (pageInput) {
            pageInput.value = '1';
        }
        
        form.submit();
    }

    // =============================================================================
    // ENTITY SEARCH FUNCTIONALITY
    // =============================================================================

    setupEntitySearchField(field) {
        const entityType = field.getAttribute('data-entity-type') || 'suppliers';
        const searchUrl = field.getAttribute('data-search-url') || '/universal/api/entity-search';
        
        let searchTimeout;
        
        field.addEventListener('input', () => {
            const searchTerm = field.value;
            
            if (searchTimeout) clearTimeout(searchTimeout);
            
            if (searchTerm.length < this.config.entitySearchMinChars) {
                this.hideEntitySearchResults(field);
                return;
            }
            
            searchTimeout = setTimeout(() => {
                this.performEntitySearch(field, entityType, searchTerm, searchUrl);
            }, this.config.entitySearchDelay);
        });
        
        document.addEventListener('click', (event) => {
            if (!field.contains(event.target)) {
                this.hideEntitySearchResults(field);
            }
        });
    }

    performEntitySearch(field, entityType, searchTerm, searchUrl) {
        const cacheKey = `${entityType}:${searchTerm}`;
        if (this.state.entitySearchCache[cacheKey]) {
            this.showEntitySearchResults(field, this.state.entitySearchCache[cacheKey]);
            return;
        }
        
        this.showEntitySearchLoading(field);
        
        fetch(searchUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                entity_type: entityType,
                search_term: searchTerm,
                search_fields: ['name', 'code', 'description'],
                display_template: '{name} ({code})',
                min_chars: this.config.entitySearchMinChars,
                max_results: 10
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.state.entitySearchCache[cacheKey] = data.results;
                this.showEntitySearchResults(field, data.results);
            } else {
                this.showEntitySearchError(field, data.error || 'Search failed');
            }
        })
        .catch(error => {
            console.error('Entity search error:', error);
            this.showEntitySearchError(field, 'Search failed');
        });
    }

    showEntitySearchResults(field, results) {
        this.hideEntitySearchResults(field);
        
        if (results.length === 0) {
            this.showEntitySearchMessage(field, 'No results found');
            return;
        }
        
        const dropdown = this.createEntitySearchDropdown(field, results);
        field.parentNode.appendChild(dropdown);
    }

    createEntitySearchDropdown(field, results) {
        const dropdown = document.createElement('div');
        dropdown.className = 'universal-entity-search-dropdown';
        
        results.forEach(result => {
            const item = document.createElement('div');
            item.className = 'universal-entity-search-item';
            item.textContent = result.display_value || result.name;
            item.setAttribute('data-value', result.id);
            
            item.addEventListener('click', () => {
                field.value = item.textContent;
                field.setAttribute('data-selected-id', item.getAttribute('data-value'));
                
                // ✅ FIX: Populate the hidden field that gets submitted with the form
                const fieldName = field.closest('.universal-entity-search-field').getAttribute('data-field-name');
                const hiddenField = document.getElementById(fieldName);
                if (hiddenField) {
                    hiddenField.value = item.getAttribute('data-value');
                }
                
                field.dispatchEvent(new Event('change', { bubbles: true }));
                this.hideEntitySearchResults(field);
            });
            
            dropdown.appendChild(item);
        });
        
        return dropdown;
    }

    showEntitySearchLoading(field) {
        this.hideEntitySearchResults(field);
        this.showEntitySearchMessage(field, 'Searching...');
    }

    showEntitySearchError(field, message) {
        this.hideEntitySearchResults(field);
        this.showEntitySearchMessage(field, message, 'error');
    }

    showEntitySearchMessage(field, message, type = 'info') {
        const dropdown = document.createElement('div');
        dropdown.className = `universal-entity-search-dropdown universal-entity-search-${type}`;
        dropdown.textContent = message;
        field.parentNode.appendChild(dropdown);
    }

    hideEntitySearchResults(field) {
        const existingDropdown = field.parentNode.querySelector('.universal-entity-search-dropdown');
        if (existingDropdown) {
            existingDropdown.remove();
        }
    }

    // =============================================================================
    // MOBILE FUNCTIONALITY
    // =============================================================================

    toggleMobileFilters() {
        const filterCard = document.querySelector('.universal-filter-card-body');
        if (filterCard) {
            filterCard.classList.toggle('mobile-visible');
        }
    }

    // =============================================================================
    // UTILITY METHODS
    // =============================================================================

    getFilterForm() {
        return document.getElementById('universal-filter-form');
    }

    formatDateForInput(date) {
        // Fix timezone issue by using local date components
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0'); // getMonth() is 0-based
        const day = String(date.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        console.log(`📅 [DATE_FIX] Formatted date: ${formattedDate} (original: ${date})`);
        return formattedDate;
    }

    formatDateForDisplay(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric' 
            });
        } catch (e) {
            return dateString;
        }
    }

    formatFieldLabel(fieldName) {
        return fieldName
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase())
            .replace('Id', 'ID');
    }

    updateFilterCountBadge(count) {
        const badge = document.querySelector('.universal-filter-count-badge');
        if (badge) {
            // Keep existing count, just update if needed
        }
    }

    getCsrfToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// =============================================================================
// GLOBAL INSTANCE AND INITIALIZATION
// =============================================================================

// Create global instance
window.UniversalFormsEngine = UniversalFormsEngine;
window.universalFormsInstance = null;

// Auto-initialization function
window.initUniversalForms = function(entityType = null, config = {}) {
    if (!window.universalFormsInstance) {
        window.universalFormsInstance = new UniversalFormsEngine(config);
    }
    window.universalFormsInstance.initialize(entityType);
};

// Auto-initialize on DOM ready if not already initialized
document.addEventListener('DOMContentLoaded', function() {
    if (!window.universalFormsInstance) {
        const entityType = document.body.getAttribute('data-entity-type') || 
                         document.querySelector('[data-entity-type]')?.getAttribute('data-entity-type');
        window.initUniversalForms(entityType);
    }
});

console.log('📋 Universal Forms Engine loaded and ready');