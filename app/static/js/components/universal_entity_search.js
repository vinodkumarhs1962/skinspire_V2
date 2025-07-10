/**
 * Universal Entity Search Component
 * ARCHITECTURE: Backend-heavy, minimal JavaScript, configuration-driven
 */

class UniversalEntitySearch {
    constructor(fieldElement) {
        this.fieldElement = fieldElement;
        this.fieldName = fieldElement.dataset.fieldName;
        this.config = this.loadConfiguration();
        this.setupElements();
        this.bindEvents();
        this.searchCache = new Map();
        this.debounceTimer = null;
    }
    
    loadConfiguration() {
        const configElement = document.getElementById(`${this.fieldName}_config`);
        return configElement ? JSON.parse(configElement.textContent) : {};
    }
    
    setupElements() {
        this.searchInput = document.getElementById(`${this.fieldName}_search`);
        this.hiddenInput = document.getElementById(this.fieldName);
        this.dropdown = document.getElementById(`${this.fieldName}_dropdown`);
        this.loadingIcon = document.getElementById(`${this.fieldName}_loading`);
    }
    
    bindEvents() {
        // ✅ Search input with debounce
        this.searchInput.addEventListener('input', (e) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.handleSearch(e.target.value);
            }, 300);
        });
        
        // ✅ Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.fieldElement.contains(e.target)) {
                this.hideDropdown();
            }
        });
        
        // ✅ Handle keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });
    }
    
    async handleSearch(searchTerm) {
        if (searchTerm.length < this.config.minChars) {
            this.hideDropdown();
            return;
        }
        
        // ✅ Check cache first
        const cacheKey = `${this.config.entityType}_${searchTerm}`;
        if (this.searchCache.has(cacheKey)) {
            this.displayResults(this.searchCache.get(cacheKey));
            return;
        }
        
        // ✅ Show loading
        this.showLoading();
        
        try {
            // ✅ Backend API call
            const response = await fetch(this.config.searchUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    entity_type: this.config.entityType,
                    search_term: searchTerm,
                    search_fields: this.config.searchFields,
                    display_template: this.config.displayTemplate,
                    min_chars: this.config.minChars,
                    max_results: this.config.maxResults,
                    additional_filters: this.config.additionalFilters
                })
            });
            
            const results = await response.json();
            
            // ✅ Cache results
            this.searchCache.set(cacheKey, results);
            
            // ✅ Display results
            this.displayResults(results);
            
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Search failed. Please try again.');
        } finally {
            this.hideLoading();
        }
    }
    
    displayResults(results) {
        if (!results || results.length === 0) {
            this.showNoResults();
            return;
        }
        
        const html = results.map(result => `
            <div class="universal-search-result px-3 py-2 hover:bg-gray-100 cursor-pointer border-b border-gray-100 last:border-b-0"
                 data-value="${result.value}"
                 data-label="${result.label}">
                <div class="font-medium text-gray-900">${result.label}</div>
                ${result.subtitle ? `<div class="text-sm text-gray-500">${result.subtitle}</div>` : ''}
            </div>
        `).join('');
        
        this.dropdown.innerHTML = html;
        this.showDropdown();
        
        // ✅ Bind click events
        this.dropdown.querySelectorAll('.universal-search-result').forEach(item => {
            item.addEventListener('click', () => {
                this.selectResult(item.dataset.value, item.dataset.label);
            });
        });
    }
    
    selectResult(value, label) {
        this.hiddenInput.value = value;
        this.searchInput.value = label;
        this.hideDropdown();
        
        // ✅ Trigger change event for form handling
        this.hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
    
    showDropdown() {
        this.dropdown.classList.remove('hidden');
    }
    
    hideDropdown() {
        this.dropdown.classList.add('hidden');
    }
    
    showLoading() {
        this.loadingIcon.classList.remove('hidden');
    }
    
    hideLoading() {
        this.loadingIcon.classList.add('hidden');
    }
    
    showNoResults() {
        this.dropdown.innerHTML = `
            <div class="px-3 py-2 text-gray-500 text-sm">
                No ${this.config.entityType} found
            </div>
        `;
        this.showDropdown();
    }
    
    showError(message) {
        this.dropdown.innerHTML = `
            <div class="px-3 py-2 text-red-500 text-sm">
                ${message}
            </div>
        `;
        this.showDropdown();
    }
    
    getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
}

// ✅ Auto-initialize all entity search fields
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.universal-entity-search-field').forEach(field => {
        new UniversalEntitySearch(field);
    });
});