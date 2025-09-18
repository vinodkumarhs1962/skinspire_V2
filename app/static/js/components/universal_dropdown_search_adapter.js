/**
 * Universal Dropdown Search Adapter - Complete Self-Contained Component
 * File: app/static/js/components/universal_dropdown_search_adapter.js
 * 
 * A fully self-contained adapter that includes all styles and functionality.
 * No external CSS needed - everything is included.
 * 
 * Usage in template:
 * 1. Include this script
 * 2. Call UniversalDropdownAdapter.init() or initialize specific elements
 * 
 * @version 2.0
 * @author SkinSpire HMS Team
 */

(function(window, document) {
    'use strict';
    
    // Universal Dropdown Search Adapter with embedded styles
    const UniversalDropdownAdapter = {
        // Configuration
        config: {
            enabled: true,
            apiBaseUrl: '/api/universal',
            debounceDelay: 300,
            minSearchLength: 2,
            maxResults: 20,
            cacheTimeout: 300000, // 5 minutes
            debug: false,
            autoInit: true, // Auto-initialize common selectors
            selectors: {
                // Default selectors to auto-initialize
                supplier: '#supplier_id',
                medicine: '.medicine-select',
                patient: '#patient_id',
                user: '#user_id'
            }
        },
        
        // Cache storage
        cache: {},
        
        // Active instances
        instances: new Map(),
        
        // CSS injection flag
        stylesInjected: false,
        
        /**
         * Initialize the adapter - main entry point
         * Can be called without parameters to auto-initialize
         * Or with specific selector and entity type
         */
        init: function(selector, entityType, options) {
            // Inject styles if not already done
            this.injectStyles();
            
            // If called without parameters, auto-initialize common fields
            if (!selector) {
                this.autoInitialize();
                return;
            }
            
            // Initialize specific selector
            this.initialize(selector, entityType, options);
        },
        
        /**
         * Auto-initialize common form fields
         */
        autoInitialize: function() {
            const self = this;
            
            // Wait for DOM ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => self.autoInitialize());
                return;
            }
            
            console.log('🚀 Universal Dropdown Adapter Auto-Initializing...');
            
            // Initialize suppliers
            if (document.querySelector(this.config.selectors.supplier)) {
                this.init(this.config.selectors.supplier, 'suppliers', {
                    minSearchLength: 1,
                    maxResults: 50
                });
            }
            
            // Initialize medicine
            if (document.querySelectorAll(this.config.selectors.medicine).length > 0) {
                this.init(this.config.selectors.medicine, 'medicine', {
                    minSearchLength: 2,
                    maxResults: 30,
                    dynamic: true // Watch for dynamically added elements
                });
            }
            
            // Initialize patients
            if (document.querySelector(this.config.selectors.patient)) {
                this.init(this.config.selectors.patient, 'patient', {
                    minSearchLength: 2,
                    maxResults: 30
                });
            }
            
            // Initialize users
            if (document.querySelector(this.config.selectors.user)) {
                this.init(this.config.selectors.user, 'user', {
                    minSearchLength: 2,
                    maxResults: 20
                });
            }
        },
        
        /**
         * Inject all required styles
         */
        injectStyles: function() {
            if (this.stylesInjected) return;
            
            const styles = `
                /* Universal Dropdown Adapter Styles - Matching Universal Engine */
                .universal-dropdown-wrapper {
                    position: relative;
                    width: 100%;
                }
                
                /* Hide original select when adapter is active */
                .universal-dropdown-wrapper select {
                    display: none !important;
                }
                
                /* Search input - matches Universal Engine form inputs */
                .universal-dropdown-search {
                    width: 100%;
                    padding: 0.5rem 0.75rem;
                    font-size: 0.875rem;
                    line-height: 1.25rem;
                    color: rgb(17 24 39);
                    background-color: white;
                    border: 1px solid rgb(209 213 219);
                    border-radius: 0.375rem;
                    transition: all 0.15s ease-in-out;
                    display: block;
                    font-family: inherit;
                }
                
                .universal-dropdown-search:focus {
                    outline: none;
                    border-color: rgb(59 130 246);
                    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
                }
                
                .universal-dropdown-search:disabled {
                    background-color: rgb(249 250 251);
                    cursor: not-allowed;
                    opacity: 0.5;
                }
                
                /* Results dropdown - matches Universal Engine */
                .universal-dropdown-results {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    margin-top: 0.25rem;
                    background: white;
                    border: 1px solid rgb(209 213 219);
                    border-radius: 0.375rem;
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                    max-height: 300px;
                    overflow-y: auto;
                    z-index: 1050;
                    display: none;
                }
                
                /* Dropdown items */
                .universal-dropdown-item {
                    padding: 0.5rem 0.75rem;
                    cursor: pointer;
                    transition: background-color 0.15s ease-in-out;
                    border-bottom: 1px solid rgb(243 244 246);
                    font-size: 0.875rem;
                    line-height: 1.25rem;
                    color: rgb(17 24 39);
                }
                
                .universal-dropdown-item:last-child {
                    border-bottom: none;
                }
                
                .universal-dropdown-item:hover,
                .universal-dropdown-item:focus {
                    background-color: rgb(243 244 246);
                    outline: none;
                }
                
                .universal-dropdown-item:active {
                    background-color: rgb(229 231 235);
                }
                
                /* Highlight matching text */
                .universal-dropdown-item strong {
                    color: rgb(59 130 246);
                    font-weight: 600;
                }
                
                /* Loading state */
                .universal-dropdown-loading {
                    padding: 0.75rem;
                    text-align: center;
                    color: rgb(107 114 128);
                    font-size: 0.875rem;
                }
                
                /* No results */
                .universal-dropdown-no-results {
                    padding: 0.75rem;
                    text-align: center;
                    color: rgb(107 114 128);
                    font-size: 0.875rem;
                    font-style: italic;
                }
                
                /* Scrollbar styling */
                .universal-dropdown-results::-webkit-scrollbar {
                    width: 6px;
                }
                
                .universal-dropdown-results::-webkit-scrollbar-track {
                    background: rgb(249 250 251);
                }
                
                .universal-dropdown-results::-webkit-scrollbar-thumb {
                    background: rgb(209 213 219);
                    border-radius: 3px;
                }
                
                .universal-dropdown-results::-webkit-scrollbar-thumb:hover {
                    background: rgb(156 163 175);
                }
                
                /* Clear button hover effect */
                .universal-dropdown-clear:hover {
                    color: rgb(239 68 68);
                }
                
                /* Dropdown icon rotation when open */
                .universal-dropdown-icon.rotated {
                    transform: translateY(-50%) rotate(180deg);
                }
                
                /* Input container for positioning icons */
                .universal-dropdown-input-container {
                    position: relative;
                    width: 100%;
                }
                
                /* Dark mode support */
                @media (prefers-color-scheme: dark) {
                    .universal-dropdown-search {
                        color: rgb(243 244 246);
                        background-color: rgb(31 41 55);
                        border-color: rgb(75 85 99);
                    }
                    
                    .universal-dropdown-search:focus {
                        border-color: rgb(96 165 250);
                        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
                    }
                    
                    .universal-dropdown-results {
                        background: rgb(31 41 55);
                        border-color: rgb(75 85 99);
                    }
                    
                    .universal-dropdown-item {
                        color: rgb(209 213 219);
                        border-bottom-color: rgb(55 65 81);
                    }
                    
                    .universal-dropdown-item:hover,
                    .universal-dropdown-item:focus {
                        background-color: rgb(55 65 81);
                        color: rgb(243 244 246);
                    }
                    
                    .universal-dropdown-item:active {
                        background-color: rgb(75 85 99);
                    }
                    
                    .universal-dropdown-item strong {
                        color: rgb(96 165 250);
                    }
                    
                    .universal-dropdown-loading,
                    .universal-dropdown-no-results {
                        color: rgb(156 163 175);
                    }
                    
                    .universal-dropdown-results::-webkit-scrollbar-track {
                        background: rgb(55 65 81);
                    }
                    
                    .universal-dropdown-results::-webkit-scrollbar-thumb {
                        background: rgb(107 114 128);
                    }
                    
                    .universal-dropdown-results::-webkit-scrollbar-thumb:hover {
                        background: rgb(156 163 175);
                    }
                }
                
                /* Animation for dropdown appearance */
                @keyframes slideDown {
                    from {
                        opacity: 0;
                        transform: translateY(-10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .universal-dropdown-results.show {
                    display: block;
                    animation: slideDown 0.2s ease-out;
                }
            `;
            
            // Create and inject style element
            const styleElement = document.createElement('style');
            styleElement.id = 'universal-dropdown-adapter-styles';
            styleElement.textContent = styles;
            document.head.appendChild(styleElement);
            
            this.stylesInjected = true;
            console.log('✅ Universal Dropdown styles injected');
        },
        
        /**
         * Initialize dropdown for specific elements
         */
        initialize: function(selector, entityType, options = {}) {
            // Merge options
            const config = Object.assign({}, this.config, options);
            
            // Find elements
            const elements = document.querySelectorAll(selector);
            if (elements.length === 0) {
                if (config.debug) {
                    console.warn(`No elements found for selector: ${selector}`);
                }
                return;
            }
            
            // Initialize each element
            elements.forEach(element => {
                if (!element.hasAttribute('data-universal-initialized')) {
                    this.initializeElement(element, entityType, config);
                    element.setAttribute('data-universal-initialized', 'true');
                }
            });
            
            // Handle dynamic elements if specified
            if (options.dynamic) {
                this.observeDynamicElements(selector, entityType, config);
            }
            
            console.log(`✅ Universal Dropdown initialized for ${entityType} (${selector})`);
        },
        
        /**
         * Initialize a single element
         */
        initializeElement: function(selectElement, entityType, config) {
            // Create wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'universal-dropdown-wrapper';
            
            // Create search input
            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.className = 'universal-dropdown-search';
            searchInput.placeholder = `Type to search ${entityType}...`;
            searchInput.setAttribute('autocomplete', 'off');
            
            // Copy disabled state
            if (selectElement.disabled) {
                searchInput.disabled = true;
            }
            
            // Create results container
            const resultsDiv = document.createElement('div');
            resultsDiv.className = 'universal-dropdown-results';
            
            // Store original options
            const originalOptions = Array.from(selectElement.options).map(opt => ({
                value: opt.value,
                text: opt.text,
                data: Object.assign({}, opt.dataset)
            }));
            
            // Setup DOM
            selectElement.parentNode.insertBefore(wrapper, selectElement);
            wrapper.appendChild(searchInput);
            wrapper.appendChild(resultsDiv);
            wrapper.appendChild(selectElement);
            
            // Set initial value
            const selectedOption = selectElement.selectedOptions[0];
            if (selectedOption && selectedOption.value) {
                searchInput.value = selectedOption.text;
                searchInput.setAttribute('data-selected-value', selectedOption.value);
            }
            
            // Create instance
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
            
            // Attach handlers
            this.attachEventHandlers(instance);
        },
        
        /**
         * Attach event handlers
         */
        attachEventHandlers: function(instance) {
            const self = this;
            const { searchInput, resultsDiv } = instance;
            
            // Input handler
            searchInput.addEventListener('input', function(e) {
                clearTimeout(instance.searchTimeout);
                const query = e.target.value.trim();
                
                instance.searchTimeout = setTimeout(() => {
                    if (query.length === 0 || query.length >= instance.config.minSearchLength) {
                        self.performSearch(instance, query);
                    }
                }, instance.config.debounceDelay);
            });
            
            // Focus handler
            searchInput.addEventListener('focus', function() {
                if (this.value.trim().length === 0) {
                    self.performSearch(instance, '');
                } else {
                    resultsDiv.classList.add('show');
                }
            });
            
            // Blur handler
            searchInput.addEventListener('blur', function(e) {
                // Delay to allow click on results
                setTimeout(() => {
                    resultsDiv.classList.remove('show');
                    resultsDiv.style.display = 'none';
                }, 200);
            });
            
            // Keyboard navigation
            searchInput.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    searchInput.value = '';
                    instance.selectElement.value = '';
                    resultsDiv.style.display = 'none';
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    const firstItem = resultsDiv.querySelector('.universal-dropdown-item');
                    if (firstItem) firstItem.focus();
                }
            });
        },
        
        /**
         * Perform search
         */
        performSearch: async function(instance, query) {
            const { entityType, config, resultsDiv } = instance;
            const cacheKey = `${entityType}:${query}`;
            
            // Check cache
            const cached = this.getCachedData(cacheKey);
            if (cached) {
                this.displayResults(instance, cached);
                return;
            }
            
            // Show loading
            this.showLoading(resultsDiv);
            
            try {
                const url = `${config.apiBaseUrl}/${entityType}/search?q=${encodeURIComponent(query)}&limit=${config.maxResults}`;
                
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });
                
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const data = await response.json();
                const results = data.results || data;
                
                // Cache results
                this.setCachedData(cacheKey, results);
                
                // Display
                this.displayResults(instance, results);
                
            } catch (error) {
                if (config.debug) {
                    console.error('Search error:', error);
                }
                // COMMENT THIS LINE TO DISABLE FALLBACK:
                // this.fallbackSearch(instance, query);
                
                // Optional: Show error message instead
                resultsDiv.innerHTML = '<div class="universal-dropdown-no-results">Unable to search. Please try again.</div>';
                resultsDiv.classList.add('show');
                resultsDiv.style.display = 'block';
            }
        },
        
        /**
         * Display results with Universal Engine styling
         */
        displayResults: function(instance, results) {
            const { resultsDiv, entityType, searchInput } = instance;
            
            resultsDiv.innerHTML = '';
            
            if (!results || results.length === 0) {
                resultsDiv.innerHTML = '<div class="universal-dropdown-no-results">No results found</div>';
                resultsDiv.classList.add('show');
                resultsDiv.style.display = 'block';
                return;
            }
            
            const searchTerm = searchInput.value.toLowerCase();
            
            results.forEach(result => {
                const item = document.createElement('div');
                item.className = 'universal-dropdown-item';
                item.setAttribute('tabindex', '0');
                
                // Get display text
                const displayText = this.getDisplayText(result, entityType);
                const value = this.getValue(result, entityType);
                
                // Highlight matching text
                if (searchTerm) {
                    const regex = new RegExp(`(${searchTerm})`, 'gi');
                    item.innerHTML = displayText.replace(regex, '<strong>$1</strong>');
                } else {
                    item.textContent = displayText;
                }
                
                item.setAttribute('data-value', value);
                this.setDataAttributes(item, result, entityType);
                
                // Event handlers
                item.addEventListener('click', () => {
                    this.selectItem(instance, item);
                });
                
                item.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        this.selectItem(instance, item);
                    } else if (e.key === 'ArrowDown') {
                        const next = item.nextElementSibling;
                        if (next) next.focus();
                    } else if (e.key === 'ArrowUp') {
                        const prev = item.previousElementSibling;
                        if (prev) prev.focus();
                        else searchInput.focus();
                    }
                });
                
                resultsDiv.appendChild(item);
            });
            
            resultsDiv.classList.add('show');
            resultsDiv.style.display = 'block';
        },
        
        /**
         * Helper methods
         */
        showLoading: function(resultsDiv) {
            resultsDiv.innerHTML = '<div class="universal-dropdown-loading">Searching...</div>';
            resultsDiv.classList.add('show');
            resultsDiv.style.display = 'block';
        },
        
        getDisplayText: function(result, entityType) {
            return result.display || result.label || result.text || 
                   result[entityType.slice(0, -1) + '_name'] || result.name || '';
        },
        
        getValue: function(result, entityType) {
            return result.value || result.id || 
                   result[entityType.slice(0, -1) + '_id'] || '';
        },
        
        setDataAttributes: function(item, result, entityType) {
            const attrs = ['gst', 'state', 'payment_terms', 'hsn', 'pack_size', 
                          'gst_rate', 'hsn_code', 'strength', 'generic_name', 
                          'state_code', 'supplier_gst'];
            
            attrs.forEach(attr => {
                if (result[attr] !== undefined) {
                    item.setAttribute(`data-${attr.replace(/_/g, '-')}`, result[attr]);
                }
            });
        },
        
        selectItem: function(instance, item) {
            const { searchInput, selectElement, resultsDiv } = instance;
            
            const value = item.getAttribute('data-value');
            const text = item.textContent;
            
            // Update input
            searchInput.value = text;
            searchInput.setAttribute('data-selected-value', value);
            
            // Update or create option
            let option = selectElement.querySelector(`option[value="${value}"]`);
            if (!option) {
                option = document.createElement('option');
                option.value = value;
                option.text = text;
                
                // Copy data attributes
                Array.from(item.attributes).forEach(attr => {
                    if (attr.name.startsWith('data-') && attr.name !== 'data-value') {
                        option.setAttribute(attr.name, attr.value);
                    }
                });
                
                selectElement.appendChild(option);
            }
            
            // Set value and trigger change
            selectElement.value = value;
            selectElement.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Hide results
            resultsDiv.classList.remove('show');
            resultsDiv.style.display = 'none';
        },
        
        fallbackSearch: function(instance, query) {
            const filtered = instance.originalOptions.filter(opt => 
                opt.text.toLowerCase().includes(query.toLowerCase())
            );
            
            const results = filtered.map(opt => ({
                value: opt.value,
                display: opt.text,
                ...opt.data
            }));
            
            this.displayResults(instance, results);
        },
        
        getCachedData: function(key) {
            const cached = this.cache[key];
            if (cached && (Date.now() - cached.timestamp < this.config.cacheTimeout)) {
                return cached.data;
            }
            return null;
        },
        
        setCachedData: function(key, data) {
            this.cache[key] = {
                data: data,
                timestamp: Date.now()
            };
        },
        
        observeDynamicElements: function(selector, entityType, config) {
            const self = this;
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1 && node.matches) {
                            const elements = node.matches(selector) ? 
                                [node] : node.querySelectorAll(selector);
                            
                            elements.forEach(element => {
                                if (!element.hasAttribute('data-universal-initialized')) {
                                    setTimeout(() => {
                                        self.initializeElement(element, entityType, config);
                                        element.setAttribute('data-universal-initialized', 'true');
                                    }, 100);
                                }
                            });
                        }
                    });
                });
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        },
        
        /**
         * Destroy an instance
         */
        destroy: function(selector) {
            const elements = document.querySelectorAll(selector);
            elements.forEach(element => {
                const instance = this.instances.get(element);
                if (instance) {
                    element.style.display = '';
                    if (instance.searchInput.parentNode) {
                        instance.searchInput.parentNode.remove();
                    }
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
                Object.keys(this.cache).forEach(key => {
                    if (key.startsWith(entityType + ':')) {
                        delete this.cache[key];
                    }
                });
            } else {
                this.cache = {};
            }
        }
    };
    
    // Export to global
    window.UniversalDropdownAdapter = UniversalDropdownAdapter;
    
    // Auto-initialize if configured
    if (UniversalDropdownAdapter.config.autoInit) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                UniversalDropdownAdapter.autoInitialize();
            });
        } else {
            UniversalDropdownAdapter.autoInitialize();
        }
    }
    
})(window, document);