/**
 * Universal Dropdown Search Adapter
 * File: app/static/js/components/universal_dropdown_search_adapter.js
 * 
 * A reusable adapter that enables Universal Engine entity search functionality
 * for any non-universal forms. Provides progressive enhancement with graceful fallback.
 * 
 * Features:
 * - Searchable entity dropdowns with type-ahead
 * - Client-side caching for performance
 * - Works with static and dynamically added elements
 * - Preserves all data attributes
 * - Falls back to original functionality if Universal Engine unavailable
 * 
 * Usage:
 * UniversalDropdownAdapter.initialize('selector', 'entity_type', options);
 * 
 * Example:
 * UniversalDropdownAdapter.initialize('#supplier_id', 'suppliers');
 * UniversalDropdownAdapter.initialize('.medicine-select', 'medicines', { dynamic: true });
 */

(function(window, document) {
    'use strict';
    
    // Universal Dropdown Search Adapter
    const UniversalDropdownAdapter = {
        // Configuration
        config: {
            enabled: true,
            apiBaseUrl: '/api/universal',
            debounceDelay: 300,
            minSearchLength: 2,
            maxResults: 20,
            cacheTimeout: 300000, // 5 minutes in milliseconds
            debug: false
        },
        
        // Cache storage
        cache: {},
        
        // Active instances
        instances: new Map(),
        
        /**
         * Initialize dropdown adapter for specified elements
         * @param {string} selector - CSS selector for target elements
         * @param {string} entityType - Entity type (suppliers, medicines, etc.)
         * @param {Object} options - Optional configuration
         */
        initialize: function(selector, entityType, options = {}) {
            // Merge options with defaults
            const instanceConfig = Object.assign({}, this.config, options);
            
            // Log initialization if debug mode
            if (instanceConfig.debug) {
                console.log(`Initializing Universal Dropdown for ${entityType} on ${selector}`);
            }
            
            // Find all matching elements
            const elements = document.querySelectorAll(selector);
            
            if (elements.length === 0) {
                if (instanceConfig.debug) {
                    console.warn(`No elements found for selector: ${selector}`);
                }
                return;
            }
            
            // Initialize each element
            elements.forEach(element => {
                if (!element.hasAttribute('data-universal-initialized')) {
                    this.initializeElement(element, entityType, instanceConfig);
                    element.setAttribute('data-universal-initialized', 'true');
                }
            });
            
            // Handle dynamic elements if specified
            if (options.dynamic) {
                this.observeDynamicElements(selector, entityType, instanceConfig);
            }
        },
        
        /**
         * Initialize a single element
         */
        initializeElement: function(selectElement, entityType, config) {
            // Check if Universal Engine is available
            if (!this.isUniversalEngineAvailable()) {
                if (config.debug) {
                    console.log('Universal Engine not available, skipping initialization');
                }
                return;
            }
            
            // Create wrapper structure
            const wrapper = this.createWrapper();
            const searchInput = this.createSearchInput(entityType);
            const resultsDiv = this.createResultsDiv();
            
            // Store original options for fallback
            const originalOptions = Array.from(selectElement.options).map(opt => ({
                value: opt.value,
                text: opt.text,
                data: Object.assign({}, opt.dataset)
            }));
            
            // Setup the DOM structure
            selectElement.style.display = 'none';
            selectElement.parentNode.insertBefore(wrapper, selectElement);
            wrapper.appendChild(searchInput);
            wrapper.appendChild(resultsDiv);
            wrapper.appendChild(selectElement);
            
            // Set initial value if one is selected
            const selectedOption = selectElement.selectedOptions[0];
            if (selectedOption && selectedOption.value) {
                searchInput.value = selectedOption.text;
                searchInput.setAttribute('data-selected-value', selectedOption.value);
            }
            
            // Create instance object
            const instance = {
                selectElement,
                searchInput,
                resultsDiv,
                entityType,
                config,
                originalOptions,
                searchTimeout: null
            };
            
            // Store instance
            this.instances.set(selectElement, instance);
            
            // Attach event handlers
            this.attachEventHandlers(instance);
        },
        
        /**
         * Create wrapper element
         */
        createWrapper: function() {
            const wrapper = document.createElement('div');
            wrapper.className = 'universal-dropdown-wrapper';
            wrapper.style.position = 'relative';
            return wrapper;
        },
        
        /**
         * Create search input element
         */
        createSearchInput: function(entityType) {
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-select universal-search-input';
            input.placeholder = `Search ${entityType}...`;
            input.style.width = '100%';
            input.setAttribute('autocomplete', 'off');
            return input;
        },
        
        /**
         * Create results dropdown element
         */
        createResultsDiv: function() {
            const div = document.createElement('div');
            div.className = 'universal-dropdown-results';
            div.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                max-height: 300px;
                overflow-y: auto;
                background: white;
                border: 1px solid #ddd;
                border-top: none;
                display: none;
                z-index: 1000;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-radius: 0 0 4px 4px;
            `;
            return div;
        },
        
        /**
         * Attach event handlers to instance
         */
        attachEventHandlers: function(instance) {
            const { searchInput, resultsDiv } = instance;
            
            // Input handler with debouncing
            searchInput.addEventListener('input', (e) => {
                clearTimeout(instance.searchTimeout);
                const query = e.target.value.trim();
                
                instance.searchTimeout = setTimeout(() => {
                    if (query.length === 0 || query.length >= instance.config.minSearchLength) {
                        this.performSearch(instance, query);
                    }
                }, instance.config.debounceDelay);
            });
            
            // Focus handler - show initial results
            searchInput.addEventListener('focus', () => {
                if (searchInput.value.trim().length === 0) {
                    this.performSearch(instance, '');
                }
            });
            
            // Clear handler
            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    searchInput.value = '';
                    instance.selectElement.value = '';
                    resultsDiv.style.display = 'none';
                } else if (e.key === 'ArrowDown' && resultsDiv.style.display === 'block') {
                    // Focus first result
                    const firstItem = resultsDiv.querySelector('.universal-dropdown-item');
                    if (firstItem) firstItem.focus();
                }
            });
            
            // Click outside handler
            document.addEventListener('click', (e) => {
                if (!instance.searchInput.parentNode.contains(e.target)) {
                    resultsDiv.style.display = 'none';
                }
            });
        },
        
        /**
         * Perform search
         */
        performSearch: async function(instance, query) {
            const { entityType, config, resultsDiv } = instance;
            const cacheKey = `${entityType}:${query}`;
            
            // Check cache first
            const cachedData = this.getCachedData(cacheKey);
            if (cachedData) {
                this.displayResults(instance, cachedData);
                return;
            }
            
            // Show loading state
            this.showLoading(resultsDiv);
            
            try {
                // Make API request
                const url = `${config.apiBaseUrl}/${entityType}/search?q=${encodeURIComponent(query)}&limit=${config.maxResults}`;
                
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                const results = data.results || data;
                
                // Cache the results
                this.setCachedData(cacheKey, results);
                
                // Display results
                this.displayResults(instance, results);
                
            } catch (error) {
                if (config.debug) {
                    console.error('Search error:', error);
                }
                // Fall back to local filtering
                this.fallbackSearch(instance, query);
            }
        },
        
        /**
         * Display search results
         */
        displayResults: function(instance, results) {
            const { resultsDiv, entityType, selectElement } = instance;
            
            // Clear previous results
            resultsDiv.innerHTML = '';
            
            if (!results || results.length === 0) {
                resultsDiv.innerHTML = '<div class="no-results" style="padding: 10px; color: #666;">No results found</div>';
                resultsDiv.style.display = 'block';
                return;
            }
            
            // Create result items
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'universal-dropdown-item';
                item.style.cssText = 'padding: 8px 12px; cursor: pointer;';
                item.setAttribute('tabindex', '0');
                
                // Get display text and value
                const displayText = this.getDisplayText(result, entityType);
                const value = this.getValue(result, entityType);
                
                item.textContent = displayText;
                item.setAttribute('data-value', value);
                
                // Store additional data attributes
                this.setDataAttributes(item, result, entityType);
                
                // Hover effects
                item.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = '#f0f0f0';
                });
                
                item.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = '';
                });
                
                // Click handler
                item.addEventListener('click', () => {
                    this.selectItem(instance, item);
                });
                
                // Keyboard navigation
                item.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        this.selectItem(instance, item);
                    } else if (e.key === 'ArrowDown') {
                        const next = item.nextElementSibling;
                        if (next) next.focus();
                    } else if (e.key === 'ArrowUp') {
                        const prev = item.previousElementSibling;
                        if (prev) prev.focus();
                        else instance.searchInput.focus();
                    }
                });
                
                resultsDiv.appendChild(item);
            });
            
            resultsDiv.style.display = 'block';
        },
        
        /**
         * Get display text from result
         */
        getDisplayText: function(result, entityType) {
            return result.display || 
                   result.label || 
                   result.text || 
                   result[entityType.slice(0, -1) + '_name'] || 
                   result.name || 
                   '';
        },
        
        /**
         * Get value from result
         */
        getValue: function(result, entityType) {
            return result.value || 
                   result.id || 
                   result[entityType.slice(0, -1) + '_id'] || 
                   '';
        },
        
        /**
         * Set data attributes based on entity type
         */
        setDataAttributes: function(item, result, entityType) {
            // Common attributes
            const commonAttrs = ['gst', 'state', 'payment_terms', 'hsn', 'pack_size'];
            
            // Entity-specific mappings
            const entityMappings = {
                'suppliers': ['supplier_gst', 'state_code', 'payment_terms'],
                'medicines': ['gst_rate', 'hsn_code', 'pack_size', 'strength', 'generic_name']
            };
            
            // Apply common attributes
            commonAttrs.forEach(attr => {
                if (result[attr]) {
                    item.setAttribute(`data-${attr}`, result[attr]);
                }
            });
            
            // Apply entity-specific attributes
            const mappings = entityMappings[entityType] || [];
            mappings.forEach(attr => {
                if (result[attr]) {
                    const dataAttr = attr.replace(/_/g, '-');
                    item.setAttribute(`data-${dataAttr}`, result[attr]);
                }
            });
        },
        
        /**
         * Select an item
         */
        selectItem: function(instance, item) {
            const { searchInput, selectElement, resultsDiv } = instance;
            
            const value = item.getAttribute('data-value');
            const text = item.textContent;
            
            // Update search input
            searchInput.value = text;
            searchInput.setAttribute('data-selected-value', value);
            
            // Check if option exists in original select
            let option = selectElement.querySelector(`option[value="${value}"]`);
            
            if (!option) {
                // Create new option from Universal Engine result
                option = document.createElement('option');
                option.value = value;
                option.text = text;
                
                // Copy all data attributes
                Array.from(item.attributes).forEach(attr => {
                    if (attr.name.startsWith('data-') && attr.name !== 'data-value') {
                        option.setAttribute(attr.name, attr.value);
                    }
                });
                
                selectElement.appendChild(option);
            }
            
            // Set the value
            selectElement.value = value;
            
            // Trigger change event
            const event = new Event('change', { bubbles: true });
            selectElement.dispatchEvent(event);
            
            // Hide results
            resultsDiv.style.display = 'none';
        },
        
        /**
         * Fallback search using original options
         */
        fallbackSearch: function(instance, query) {
            const { originalOptions } = instance;
            
            const filtered = originalOptions.filter(opt => 
                opt.text.toLowerCase().includes(query.toLowerCase())
            );
            
            const results = filtered.map(opt => ({
                value: opt.value,
                display: opt.text,
                ...opt.data
            }));
            
            this.displayResults(instance, results);
        },
        
        /**
         * Show loading state
         */
        showLoading: function(resultsDiv) {
            resultsDiv.innerHTML = '<div style="padding: 10px; color: #666;">Searching...</div>';
            resultsDiv.style.display = 'block';
        },
        
        /**
         * Check if Universal Engine is available
         */
        isUniversalEngineAvailable: function() {
            return this.config.enabled && typeof fetch !== 'undefined';
        },
        
        /**
         * Get cached data
         */
        getCachedData: function(key) {
            const cached = this.cache[key];
            if (cached && (Date.now() - cached.timestamp < this.config.cacheTimeout)) {
                if (this.config.debug) {
                    console.log(`Cache hit for: ${key}`);
                }
                return cached.data;
            }
            return null;
        },
        
        /**
         * Set cached data
         */
        setCachedData: function(key, data) {
            this.cache[key] = {
                data: data,
                timestamp: Date.now()
            };
        },
        
        /**
         * Observe for dynamically added elements
         */
        observeDynamicElements: function(selector, entityType, config) {
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach((node) => {
                            if (node.nodeType === 1) { // Element node
                                const elements = node.matches(selector) ? 
                                    [node] : node.querySelectorAll(selector);
                                
                                elements.forEach(element => {
                                    if (!element.hasAttribute('data-universal-initialized')) {
                                        this.initializeElement(element, entityType, config);
                                        element.setAttribute('data-universal-initialized', 'true');
                                    }
                                });
                            }
                        });
                    }
                });
            });
            
            // Start observing
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            return observer;
        },
        
        /**
         * Destroy an instance
         */
        destroy: function(selector) {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                const instance = this.instances.get(element);
                if (instance) {
                    // Restore original select
                    element.style.display = '';
                    instance.searchInput.parentNode.remove();
                    element.removeAttribute('data-universal-initialized');
                    this.instances.delete(element);
                }
            });
        },
        
        /**
         * Clear cache
         */
        clearCache: function(entityType = null) {
            if (entityType) {
                // Clear cache for specific entity type
                Object.keys(this.cache).forEach(key => {
                    if (key.startsWith(entityType + ':')) {
                        delete this.cache[key];
                    }
                });
            } else {
                // Clear all cache
                this.cache = {};
            }
        }
    };
    
    // Expose to global scope
    window.UniversalDropdownAdapter = UniversalDropdownAdapter;
    
})(window, document);