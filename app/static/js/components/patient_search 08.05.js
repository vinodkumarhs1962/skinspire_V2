/**
 * PatientSearch Component
 * 
 * A reusable patient search field with standardized behavior:
 * - Shows recent patients when focused with empty input
 * - Searches as user types
 * - Handles selection and updates hidden fields
 * - Consistent error handling and display
 */
class PatientSearch {
    /**
     * Create a patient search component
     * @param {Object} options - Configuration options
     */
    constructor(options) {
        this.options = Object.assign({
            // Selectors with flexible options
            containerSelector: '.patient-search-container, #invoice-form, form',
            inputSelector: '.patient-search-input, #patient-search, #patient_search',
            resultsSelector: '.patient-search-results, #patient-search-results, #patient_search_results',
            
            // Display elements
            patientInfoSelector: '#selected-patient-info',
            patientNameDisplaySelector: '#patient-name-display',
            patientMRNDisplaySelector: '#patient-mrn-display',
            patientContactDisplaySelector: '#patient-contact-display',
            
            // Hidden fields
            patientIdField: 'patient_id',
            patientNameField: 'patient_name', // Optional in some forms
            requirePatientName: false,        // Make patient_name field optional
            
            // Display options
            showPatientMRN: true,
            showPatientContact: true,
            
            // Behavior
            minChars: 0,                  // Show all patients on focus if empty
            debounceTime: 300,            // Debounce time for search input (ms)
            limit: 20,                    // Results to show
            
            // API settings
            searchEndpoint: '/invoice/web_api/patient/search',
            
            // Integration options
            respectExistingHandlers: true,    // Don't override existing handlers
            handleSubmission: false,          // Don't interfere with form submission
            
            // Callbacks
            onSelect: null,               // Called when patient is selected
            onError: null                 // Called on search error
        }, options);
        
        // Find container element using the first valid selector
        this.container = this._findElement(this.options.containerSelector);
        if (!this.container) {
            console.error('Patient search container not found using selectors:', this.options.containerSelector);
            return;
        }
        
        // Find input element
        this.input = this._findElement(this.options.inputSelector, this.container);
        if (!this.input) {
            console.error('Patient search input not found using selectors:', this.options.inputSelector);
            return;
        }
        
        // Find results container
        this.results = this._findElement(this.options.resultsSelector, this.container);
        if (!this.results) {
            console.error('Patient search results container not found using selectors:', this.options.resultsSelector);
            return;
        }
        
        // Find display elements (optional)
        this.patientInfo = document.querySelector(this.options.patientInfoSelector);
        this.patientNameDisplay = document.querySelector(this.options.patientNameDisplaySelector);
        this.patientMRNDisplay = document.querySelector(this.options.patientMRNDisplaySelector);
        this.patientContactDisplay = document.querySelector(this.options.patientContactDisplaySelector);
        
        // Get or create hidden fields
        this.patientIdInput = document.getElementById(this.options.patientIdField);
        if (!this.patientIdInput) {
            console.warn(`Patient ID field '${this.options.patientIdField}' not found. Creating it.`);
            this.patientIdInput = document.createElement('input');
            this.patientIdInput.type = 'hidden';
            this.patientIdInput.id = this.options.patientIdField;
            this.patientIdInput.name = this.options.patientIdField;
            this.container.appendChild(this.patientIdInput);
        }
        
        // Patient name field is optional depending on the form
        if (this.options.requirePatientName || document.getElementById(this.options.patientNameField)) {
            this.patientNameInput = document.getElementById(this.options.patientNameField);
            if (!this.patientNameInput) {
                console.warn(`Patient name field '${this.options.patientNameField}' not found. Creating it.`);
                this.patientNameInput = document.createElement('input');
                this.patientNameInput.type = 'hidden';
                this.patientNameInput.id = this.options.patientNameField;
                this.patientNameInput.name = this.options.patientNameField;
                this.container.appendChild(this.patientNameInput);
            }
        }
        
        // Check for existing implementation
        this.hasExistingImplementation = this._detectExistingImplementation();
        
        // If there's an existing implementation and we should respect it, adjust behavior
        if (this.hasExistingImplementation && this.options.respectExistingHandlers) {
            console.log("Detected existing patient search implementation, adjusting behavior");
            this.options.handleSubmission = false;
            this.options.integrationMode = true;
        }
        
        // Initialize the component
        this.init();
        console.log('Patient search component initialized');
    }
    
    /**
     * Initialize the component with event listeners
     */
    init() {
        // Create debounced search function
        this.debouncedSearch = this.debounce(
            this.searchPatients.bind(this), 
            this.options.debounceTime
        );
        
        // Add event listeners
        this._addEventListeners();
        
        // Initialize with default state
        this.clearSelection();
    }
    
    /**
     * Add event listeners to component elements
     */
    _addEventListeners() {
        // Input event listener for searching
        this.input.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            this.debouncedSearch(query);
        });
        
        // Focus event to show all patients when empty
        this.input.addEventListener('focus', () => {
            const query = this.input.value.trim();
            if (query.length < this.options.minChars) {
                this.searchPatients('');
            }
        });
        
        // Handle clicks on results
        this.results.addEventListener('click', (e) => {
            const item = e.target.closest('[data-patient-id]');
            if (item) {
                const patientId = item.dataset.patientId;
                const patientName = item.dataset.patientName;
                const patientMRN = item.dataset.patientMrn;
                const patientContact = item.dataset.patientContact;
                
                this.selectPatient({
                    id: patientId,
                    name: patientName,
                    mrn: patientMRN,
                    contact: patientContact
                });
            }
        });
        
        // Handle clicks outside to close results
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.results.contains(e.target)) {
                this.hideResults();
            }
        });
        
        // Add keyboard navigation
        this.input.addEventListener('keydown', (e) => {
            if (this.results.classList.contains('hidden')) {
                return;
            }
            
            const items = this.results.querySelectorAll('[data-patient-id]');
            const activeItem = this.results.querySelector('.bg-gray-100');
            let activeIndex = -1;
            
            if (activeItem) {
                activeIndex = Array.from(items).indexOf(activeItem);
            }
            
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if (activeIndex < items.length - 1) {
                        if (activeItem) {
                            activeItem.classList.remove('bg-gray-100', 'dark:bg-gray-700');
                        }
                        items[activeIndex + 1].classList.add('bg-gray-100', 'dark:bg-gray-700');
                        items[activeIndex + 1].scrollIntoView({ block: 'nearest' });
                    }
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    if (activeIndex > 0) {
                        if (activeItem) {
                            activeItem.classList.remove('bg-gray-100', 'dark:bg-gray-700');
                        }
                        items[activeIndex - 1].classList.add('bg-gray-100', 'dark:bg-gray-700');
                        items[activeIndex - 1].scrollIntoView({ block: 'nearest' });
                    }
                    break;
                    
                case 'Enter':
                    e.preventDefault();
                    if (activeItem) {
                        const patientId = activeItem.dataset.patientId;
                        const patientName = activeItem.dataset.patientName;
                        const patientMRN = activeItem.dataset.patientMrn;
                        const patientContact = activeItem.dataset.patientContact;
                        
                        this.selectPatient({
                            id: patientId,
                            name: patientName,
                            mrn: patientMRN,
                            contact: patientContact
                        });
                    }
                    break;
                    
                case 'Escape':
                    e.preventDefault();
                    this.hideResults();
                    break;
            }
        });
        
        // Optional form submission handler
        if (this.options.handleSubmission) {
            const form = this.input.closest('form');
            if (form) {
                form.addEventListener('submit', (e) => {
                    // Validate patient selection
                    if (!this.patientIdInput.value.trim()) {
                        e.preventDefault();
                        alert('Please select a patient before submitting.');
                        return false;
                    }
                });
            }
        }
    }
    
    /**
     * Search patients using the API
     * @param {string} query - Search query
     */
    searchPatients(query) {
        // Show loading state
        this.results.innerHTML = '<div class="p-2 text-gray-500">Searching...</div>';
        this.showResults();
        
        // Build query URL
        const url = new URL(this.options.searchEndpoint, window.location.origin);
        url.searchParams.append('q', query);
        url.searchParams.append('limit', this.options.limit);
        
        // Perform search
        fetch(url.toString(), {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Search failed: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Handle the standardized response format
            if (data.items) {
                this.displayResults(data.items);
            } else if (Array.isArray(data)) {
                // Support legacy API format
                this.displayResults(data);
            } else {
                // Handle error or empty results
                this.results.innerHTML = '<div class="p-2 text-gray-500">No patients found</div>';
            }
        })
        .catch(error => {
            console.error('Patient search error:', error);
            
            this.results.innerHTML = `
                <div class="p-2 text-red-500">
                    <div class="font-semibold">Error searching patients</div>
                    <div class="text-sm">${error.message || 'Please try again'}</div>
                </div>
            `;
            
            if (this.options.onError) {
                this.options.onError(error);
            }
        });
    }
    
    /**
     * Display search results
     * @param {Array} patients - Array of patient objects
     */
    displayResults(patients) {
        // Clear previous results
        this.results.innerHTML = '';
        
        // Handle empty results
        if (!patients || patients.length === 0) {
            this.results.innerHTML = '<div class="p-2 text-gray-500">No patients found</div>';
            this.showResults();
            return;
        }
        
        // Create results list
        const list = document.createElement('div');
        list.className = 'divide-y divide-gray-200 dark:divide-gray-700 max-h-60 overflow-y-auto';
        
        // Add each patient to the list
        patients.forEach(patient => {
            const item = document.createElement('div');
            item.className = 'p-2 hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer';
            item.setAttribute('data-patient-id', patient.id);
            item.setAttribute('data-patient-name', patient.name);
            item.setAttribute('data-patient-mrn', patient.mrn || '');
            item.setAttribute('data-patient-contact', patient.contact || '');
            
            // Build patient display
            let html = `<div class="font-semibold">${this.escapeHtml(patient.name)}</div>`;
            
            if (this.options.showPatientMRN && patient.mrn) {
                html += `<div class="text-sm text-gray-600 dark:text-gray-400">MRN: ${this.escapeHtml(patient.mrn)}</div>`;
            }
            
            if (this.options.showPatientContact && patient.contact) {
                html += `<div class="text-sm text-gray-600 dark:text-gray-400">${this.escapeHtml(patient.contact)}</div>`;
            }
            
            item.innerHTML = html;
            list.appendChild(item);
        });
        
        this.results.appendChild(list);
        this.showResults();
    }
    
    /**
     * Select a patient and update form fields
     * @param {Object} patient - Patient object
     */
    selectPatient(patient) {
        // Update hidden fields
        this.patientIdInput.value = patient.id;
        
        // Update patient name field if it exists
        if (this.patientNameInput) {
            this.patientNameInput.value = patient.name;
        }
        
        // Update visible input
        this.input.value = patient.mrn ? 
            `${patient.name} - ${patient.mrn}` : 
            patient.name;
        
        // Hide results
        this.hideResults();
        
        // Update display if elements exist
        if (this.patientInfo) {
            this.patientInfo.classList.remove('hidden');
        }
        
        if (this.patientNameDisplay) {
            this.patientNameDisplay.textContent = patient.name;
        }
        
        if (this.patientMRNDisplay) {
            this.patientMRNDisplay.textContent = patient.mrn ? `MRN: ${patient.mrn}` : '';
        }
        
        if (this.patientContactDisplay) {
            this.patientContactDisplay.textContent = patient.contact ? `Contact: ${patient.contact}` : '';
        }
        
        // Call select callback if provided
        if (this.options.onSelect) {
            this.options.onSelect(patient);
        }
        
        // Also update any additional data attributes on the form for compatibility
        const form = this.input.closest('form');
        if (form) {
            form.setAttribute('data-patient-id', patient.id);
            form.setAttribute('data-patient-name', patient.name);
        }
        
        // Trigger change event for form validation
        this.input.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    /**
     * Clear the current selection
     */
    clearSelection() {
        // Clear hidden fields
        this.patientIdInput.value = '';
        if (this.patientNameInput) {
            this.patientNameInput.value = '';
        }
        
        // Clear visible input
        this.input.value = '';
        
        // Hide patient info display if it exists
        if (this.patientInfo) {
            this.patientInfo.classList.add('hidden');
        }
    }
    
    /**
     * Show the results dropdown
     */
    showResults() {
        this.results.classList.remove('hidden');
    }
    
    /**
     * Hide the results dropdown
     */
    hideResults() {
        this.results.classList.add('hidden');
    }
    
    /**
     * Find the first element matching any of the selectors
     * @param {string} selectors - Comma-separated list of selectors
     * @param {Element} context - Element to search within (optional)
     * @returns {Element|null} - The first matching element or null
     */
    _findElement(selectors, context = document) {
        const selectorList = selectors.split(',').map(s => s.trim());
        
        for (const selector of selectorList) {
            const element = context.querySelector(selector);
            if (element) {
                return element;
            }
        }
        
        return null;
    }
    
    /**
     * Detect if there's an existing patient search implementation
     * @returns {boolean} - True if existing implementation detected
     */
    _detectExistingImplementation() {
        // Check for inline scripts that mention patient search
        const inlineScripts = Array.from(document.querySelectorAll('script:not([src])'))
            .filter(script => {
                const content = script.textContent;
                return content.includes('patient-search') || 
                       content.includes('patient_search') ||
                       content.includes('searchPatients');
            });
        
        return inlineScripts.length > 0;
    }
    
    /**
     * Create a debounced function
     * @param {Function} func - Function to debounce
     * @param {number} delay - Delay in milliseconds
     * @returns {Function} Debounced function
     */
    debounce(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }
    
    /**
     * Escape HTML entities in a string
     * @param {string} unsafe - String to escape
     * @returns {string} Escaped string
     */
    escapeHtml(unsafe) {
        if (!unsafe) return '';
        
        return String(unsafe)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Export for global use
window.PatientSearch = PatientSearch;