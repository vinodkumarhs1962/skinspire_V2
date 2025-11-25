/* =============================================================================
   Universal Entity Dropdown Component
   File: app/static/js/components/universal_entity_dropdown.js
   
   Searchable dropdown with caching for Universal Engine v5.1
   Progressive enhancement - degrades gracefully
   ============================================================================= */

(function() {
    'use strict';

    // ADD: Prevent multiple initializations
    if (window.EntityDropdownInitialized) {
        console.log('Entity dropdown already initialized, skipping...');
        return;
    }
    window.EntityDropdownInitialized = true;

    // Cache for search results
    const searchCache = new Map();
    const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

    class EntityDropdown {
        constructor(container) {
            // ADD: Safety check for container
            if (!container || container.dataset.dropdownInstance) {
                console.warn('Container already has dropdown instance or is invalid');
                return;
            }
            
            // Mark container as having an instance
            container.dataset.dropdownInstance = 'true';
            
            this.container = container;
            this.hiddenInput = container.querySelector('.entity-dropdown-hidden-input');
            this.searchInput = container.querySelector('.entity-dropdown-search');
            this.resultsContainer = container.querySelector('.entity-dropdown-results');
            
            // ADD: Safe parse with error handling
            try {
                this.config = JSON.parse(container.dataset.entityConfig || '{}');
                console.log('[EntityDropdown] Loaded config:', this.config);
                console.log('[EntityDropdown] Search endpoint:', this.config.search_endpoint);
            } catch (e) {
                console.error('Failed to parse entity config:', e);
                this.config = {};
            }
            
            this.fieldName = container.dataset.name;
            this.currentValue = container.dataset.value || '';
            this.currentDisplay = container.dataset.displayValue || '';
            
            // State
            this.isOpen = false;
            this.searchTimeout = null;
            this.highlightedIndex = -1;
            this.results = [];
            this.abortController = null;
            
            // Initialize only if elements exist
            if (this.hiddenInput && this.searchInput) {
                this.init();
            }
        }

        init() {
            // Set initial values
            if (this.currentValue) {
                this.hiddenInput.value = this.currentValue;
                this.searchInput.value = this.currentDisplay;
                this.addClearButton();
            }

            // Bind events
            this.bindEvents();
            
            // Create results container if it doesn't exist
            if (!this.resultsContainer) {
                this.resultsContainer = document.createElement('div');
                this.resultsContainer.className = 'entity-dropdown-results';
                this.resultsContainer.style.display = 'none';
                this.container.appendChild(this.resultsContainer);
            }
        }

        bindEvents() {
            // ADD: Prevent duplicate event binding
            if (this.searchInput.dataset.eventsbound) {
                return;
            }
            this.searchInput.dataset.eventsbound = 'true';

            // Store bound functions for cleanup
            this._handleFocus = () => this.handleFocus();
            this._handleBlur = (e) => this.handleBlur(e);
            this._handleInput = (e) => this.handleInput(e);
            this._handleKeydown = (e) => this.handleKeydown(e);
            
            // Search input events
            this.searchInput.addEventListener('focus', this._handleFocus);
            this.searchInput.addEventListener('blur', this._handleBlur);
            this.searchInput.addEventListener('input', this._handleInput);
            this.searchInput.addEventListener('keydown', this._handleKeydown);
            
            // ADD: Use a single document click handler
            if (!window.entityDropdownDocClickHandler) {
                window.entityDropdownDocClickHandler = (e) => {
                    document.querySelectorAll('.entity-dropdown-container[data-dropdown-instance]').forEach(container => {
                        if (!container.contains(e.target)) {
                            const dropdown = container.querySelector('.entity-dropdown-results');
                            if (dropdown) dropdown.style.display = 'none';
                        }
                    });
                };
                document.addEventListener('click', window.entityDropdownDocClickHandler);
            }
        }

        handleFocus() {
            // Load common items on focus if configured
            if (this.config.preload_common && !this.searchInput.value) {
                this.performSearch('');
            } else if (this.searchInput.value) {
                this.open();
            }
        }

        handleBlur(event) {
            // Delay to allow click on results
            setTimeout(() => {
                if (!this.container.contains(document.activeElement)) {
                    this.close();
                }
            }, 200);
        }

        handleInput(event) {
            const query = event.target.value;
            
            // Clear existing timeout
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
            
            // Reset if empty
            if (!query) {
                this.hiddenInput.value = '';
                this.currentValue = '';
                this.currentDisplay = '';
                if (this.config.preload_common) {
                    this.performSearch('');
                } else {
                    this.close();
                }
                return;
            }
            
            // Debounce search
            this.searchTimeout = setTimeout(() => {
                this.performSearch(query);
            }, 300);
        }

        handleKeydown(event) {
            if (!this.isOpen) {
                if (event.key === 'ArrowDown' || event.key === 'Enter') {
                    this.performSearch(this.searchInput.value || '');
                }
                return;
            }

            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    this.highlightNext();
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    this.highlightPrevious();
                    break;
                case 'Enter':
                    event.preventDefault();
                    if (this.highlightedIndex >= 0) {
                        this.selectItem(this.results[this.highlightedIndex]);
                    }
                    break;
                case 'Escape':
                    this.close();
                    break;
            }
        }

        async performSearch(query) {
            // Check minimum characters
            const minChars = this.config.min_chars || 2;
            if (query && query.length < minChars) {
                return;
            }

            // Check cache first
            if (this.config.cache_results) {
                const cacheKey = `${this.config.target_entity}:${query}`;
                const cached = searchCache.get(cacheKey);
                if (cached && (Date.now() - cached.timestamp < CACHE_TTL)) {
                    this.displayResults(cached.data);
                    return;
                }
            }

            // Cancel previous request
            if (this.abortController) {
                this.abortController.abort();
            }

            // Show loading state
            this.showLoading();

            try {
                // Create new abort controller
                this.abortController = new AbortController();

                // Build search URL
                const params = new URLSearchParams({
                    q: query,
                    limit: 10,
                    fields: JSON.stringify(this.config.search_fields || ['name'])
                });

                const searchUrl = `${this.config.search_endpoint}?${params}`;
                console.log('[EntityDropdown] Fetching:', searchUrl);

                const response = await fetch(
                    searchUrl,
                    {
                        method: 'GET',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': 'application/json'
                        },
                        signal: this.abortController.signal
                    }
                );

                if (!response.ok) {
                    throw new Error(`Search failed: ${response.statusText}`);
                }

                const data = await response.json();

                // Cache results
                if (this.config.cache_results) {
                    const cacheKey = `${this.config.target_entity}:${query}`;
                    searchCache.set(cacheKey, {
                        data: data.results || data,
                        timestamp: Date.now()
                    });
                }

                this.displayResults(data.results || data);

            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Entity search error:', error);
                    this.showError('Search failed. Please try again.');
                }
            } finally {
                this.abortController = null;
            }
        }

        displayResults(results) {
            this.results = results || [];
            this.highlightedIndex = -1;

            if (this.results.length === 0) {
                this.showNoResults();
                return;
            }

            // Build results HTML - Use correct value fields
            const html = this.results.map((item, index) => {
                const display = this.formatDisplay(item);
                const valueField = this.config.value_field || 'id';
                const itemValue = item.value || item[valueField] || item.id || 
                                item.supplier_id || item.patient_id || item.medicine_id || '';
                const isSelected = itemValue === this.currentValue;
                
                return `
                    <div class="entity-dropdown-item ${isSelected ? 'selected' : ''}"
                        data-index="${index}"
                        data-value="${itemValue}">
                        ${display}
                    </div>
                `;
            }).join('');

            this.resultsContainer.innerHTML = html;

            // Bind click events to results
            this.resultsContainer.querySelectorAll('.entity-dropdown-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const index = parseInt(item.dataset.index);
                    this.selectItem(this.results[index]);
                });
            });

            this.open();
        }

        formatDisplay(item) {
            // Use the display/label/name field directly from API response
            // Prioritize fields that contain the actual display name
            let display = item.display || item.label || item.text ||
                        item.name || item.supplier_name || item.patient_name ||
                        item.medicine_name || '';

            // If display is still empty or contains UUID, try to extract name
            if (!display || display.includes('-')) {
                // Look for any field with 'name' in it
                for (const key in item) {
                    if (key.includes('name') && item[key] && !item[key].includes('-')) {
                        display = item[key];
                        break;
                    }
                }
            }

            // Highlight search term
            const searchTerm = this.searchInput.value;
            if (searchTerm && display) {
                const regex = new RegExp(`(${this.escapeRegex(searchTerm)})`, 'gi');
                display = display.replace(regex, '<span class="entity-dropdown-highlight">$1</span>');
            }

            // Build secondary info (for medicines: type, services: code, etc.)
            let secondaryInfo = '';
            if (item.medicine_type) {
                secondaryInfo = `<div class="entity-dropdown-item-secondary">
                    <span class="badge badge-sm badge-info">${item.medicine_type}</span>
                    ${item.generic_name ? `<span class="text-muted text-sm">| ${item.generic_name}</span>` : ''}
                </div>`;
            } else if (item.code) {
                secondaryInfo = `<div class="entity-dropdown-item-secondary">
                    <span class="text-muted text-sm">Code: ${item.code}</span>
                </div>`;
            } else if (item.generic_name) {
                secondaryInfo = `<div class="entity-dropdown-item-secondary">
                    <span class="text-muted text-sm">${item.generic_name}</span>
                </div>`;
            }

            return `
                <div class="entity-dropdown-item-content">
                    <div class="entity-dropdown-item-primary">${display}</div>
                    ${secondaryInfo}
                </div>
            `;
        }

        selectItem(item) {
            // Set values - Use correct fields from API response
            const valueField = this.config.value_field || 'id';
            const value = item.value || item[valueField] || item.id || 
                        item.supplier_id || item.patient_id || item.medicine_id || '';
            
            // Get display name - prioritize name fields over templates
            const display = item.label || item.display || item.text || 
                        item.name || item.supplier_name || item.patient_name || 
                        item.medicine_name || this.formatDisplayPlain(item);

            // Store values
            this.hiddenInput.value = value;
            this.searchInput.value = display;  // Show only name, not UUID
            this.currentValue = value;
            this.currentDisplay = display;

            // Update data attributes for persistence
            this.container.dataset.value = value;
            this.container.dataset.displayValue = display;

            // Close dropdown
            this.close();

            // Trigger change event for auto-submit
            const changeEvent = new Event('change', { bubbles: true });
            this.hiddenInput.dispatchEvent(changeEvent);

            // Dispatch custom event with full item data for cascading/auto-populate features
            const selectedEvent = new CustomEvent('entity-selected', {
                detail: item,
                bubbles: true
            });
            this.container.dispatchEvent(selectedEvent);

            // If auto-submit is enabled, submit the form
            if (this.searchInput.classList.contains('universal-filter-auto-submit')) {
                const form = this.container.closest('form');
                if (form) {
                    form.submit();
                }
            }
        }

        addClearButton() {
            // Remove existing clear button if any
            const existingBtn = this.container.querySelector('.entity-dropdown-clear');
            if (existingBtn) existingBtn.remove();
            
            // Create clear button
            const clearBtn = document.createElement('span');
            clearBtn.className = 'entity-dropdown-clear';
            clearBtn.innerHTML = '×';
            clearBtn.title = 'Clear selection';
            clearBtn.style.cssText = `
                position: absolute;
                right: 30px;
                top: 50%;
                transform: translateY(-50%);
                cursor: pointer;
                color: #dc3545;
                font-size: 20px;
                line-height: 1;
                padding: 0 5px;
                z-index: 10;
            `;
            
            clearBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearSelection();
            });
            
            this.container.appendChild(clearBtn);
        }

        clearSelection() {
            this.hiddenInput.value = '';
            this.searchInput.value = '';
            this.currentValue = '';
            this.currentDisplay = '';
            
            // Remove clear button
            const clearBtn = this.container.querySelector('.entity-dropdown-clear');
            if (clearBtn) clearBtn.remove();
            
            // Trigger change event
            const changeEvent = new Event('change', { bubbles: true });
            this.hiddenInput.dispatchEvent(changeEvent);
            
            // Submit form if auto-submit enabled
            if (this.searchInput.classList.contains('universal-filter-auto-submit')) {
                const form = this.container.closest('form');
                if (form) form.submit();
            }
        }

        formatDisplayPlain(item) {
            // First try to use direct name fields from API
            let display = item.label || item.display || item.text || 
                        item.name || item.supplier_name || item.patient_name || 
                        item.medicine_name;
            
            if (display) {
                return display;
            }
            
            // Fallback to template if no direct field found
            const template = this.config.display_template || '{name}';
            display = template;

            // Only use template if we have the fields it needs
            Object.keys(item).forEach(key => {
                const regex = new RegExp(`\\{${key}\\}`, 'g');
                const value = item[key] || '';
                // Skip UUID values in display
                if (value && !value.includes('-')) {
                    display = display.replace(regex, value);
                } else {
                    display = display.replace(regex, '');
                }
            });

            // Clean up any remaining placeholders
            display = display.replace(/\{[^}]*\}/g, '').trim();
            
            return display || 'Unknown';
        }

        highlightNext() {
            if (this.highlightedIndex < this.results.length - 1) {
                this.highlightedIndex++;
                this.updateHighlight();
            }
        }

        highlightPrevious() {
            if (this.highlightedIndex > 0) {
                this.highlightedIndex--;
                this.updateHighlight();
            }
        }

        updateHighlight() {
            const items = this.resultsContainer.querySelectorAll('.entity-dropdown-item');
            items.forEach((item, index) => {
                if (index === this.highlightedIndex) {
                    item.classList.add('highlighted');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('highlighted');
                }
            });
        }

        showLoading() {
            this.resultsContainer.innerHTML = `
                <div class="entity-dropdown-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    Searching...
                </div>
            `;
            this.open();
        }

        showNoResults() {
            this.resultsContainer.innerHTML = `
                <div class="entity-dropdown-no-results">
                    No results found
                </div>
            `;
            this.open();
        }

        showError(message) {
            this.resultsContainer.innerHTML = `
                <div class="entity-dropdown-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    ${message}
                </div>
            `;
            this.open();
        }

        open() {
            this.isOpen = true;
            this.container.classList.add('open');
            this.resultsContainer.style.display = 'block';
        }

        close() {
            this.isOpen = false;
            this.container.classList.remove('open');
            this.resultsContainer.style.display = 'none';
            this.highlightedIndex = -1;
        }

        escapeRegex(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }
        // ADD: Cleanup method for removing event listeners
        destroy() {
            if (this.searchInput && this._handleFocus) {
                this.searchInput.removeEventListener('focus', this._handleFocus);
                this.searchInput.removeEventListener('blur', this._handleBlur);
                this.searchInput.removeEventListener('input', this._handleInput);
                this.searchInput.removeEventListener('keydown', this._handleKeydown);
                this.searchInput.dataset.eventsbound = '';
            }
            
            if (this.abortController) {
                this.abortController.abort();
            }
            
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
            
            this.container.dataset.dropdownInstance = '';
            this.container.dataset.initialized = '';
        }
    }

    // Initialize all entity dropdowns when DOM is ready
    function initializeEntityDropdowns() {
        // ADD: Prevent running if already processing
        if (window.entityDropdownInitializing) {
            console.log('Already initializing dropdowns, skipping...');
            return;
        }
        window.entityDropdownInitializing = true;
        
        try {
            const dropdowns = document.querySelectorAll('.entity-dropdown-container:not([data-initialized])');
            
            dropdowns.forEach(container => {
                try {
                    new EntityDropdown(container);
                    container.dataset.initialized = 'true';
                } catch (e) {
                    console.error('Failed to initialize dropdown:', e);
                }
            });
        } finally {
            window.entityDropdownInitializing = false;
        }
    }

    // ADD: Single initialization with delay
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(initializeEntityDropdowns, 100);
        }, { once: true });
    } else {
        // Small delay to ensure DOM is fully ready
        setTimeout(initializeEntityDropdowns, 100);
    }

    // Re-initialize when new content is added (with guard)
    document.addEventListener('universal:content-updated', function() {
        if (!window.entityDropdownInitializing) {
            initializeEntityDropdowns();
        }
    }, { once: false });

    // Export for use in other scripts
    window.EntityDropdown = EntityDropdown;
    window.initializeEntityDropdowns = initializeEntityDropdowns;

})();