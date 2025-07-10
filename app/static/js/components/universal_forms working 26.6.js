/**
 * ==========================================
 * UNIVERSAL FORMS - Minimal JavaScript
 * File: app/static/js/components/universal_forms.js
 * ==========================================
 * 
 * Backend-heavy approach: Most logic handled by Flask
 * JavaScript only for basic UX enhancements
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeUniversalForms();
    initializeActiveFilters();
    setupClickableCards();
        // ✅ NEW: Initialize Universal Entity Search fields
    initializeUniversalEntitySearch();
    
    // ✅ NEW: Initialize date presets
    initializeDatePresets();
    
    // Update active filters display immediately
    setTimeout(updateActiveFiltersDisplay, 100);
});

/**
 * Initialize universal form functionality
 * Minimal JavaScript - most behavior handled by Flask backend
 */
function initializeUniversalForms() {
    setupAutoSubmitFilters();
    setupClickableCards();
    setupFormEnhancements();
    console.log('✅ Universal Forms initialized - Backend-heavy mode');
}

/**
 * Auto-submit filter forms with debounce
 * Submits to Flask backend for processing
 */
function setupAutoSubmitFilters() {
    let debounceTimer;
    
    // Auto-submit on select changes
    document.querySelectorAll('.universal-filter-auto-submit[type="select"]').forEach(function(select) {
        select.addEventListener('change', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                select.form.submit();
            }, 100); // Immediate for select
        });
    });
    
    // Auto-submit on text input with longer debounce
    document.querySelectorAll('.universal-filter-auto-submit[type="text"]').forEach(function(input) {
        input.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                input.form.submit();
            }, 1000); // 1 second delay for text input
        });
    });
    
    // Auto-submit on checkbox/radio changes
    document.querySelectorAll('.universal-filter-auto-submit[type="checkbox"], .universal-filter-auto-submit[type="radio"]').forEach(function(input) {
        input.addEventListener('change', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function() {
                input.form.submit();
            }, 100);
        });
    });
}

function initializeUniversalEntitySearch() {
    // Load entity search configurations
    const configElement = document.getElementById('entity-search-configs');
    if (!configElement) return;
    
    try {
        const configs = JSON.parse(configElement.textContent);
        
        // Initialize each entity search field
        Object.keys(configs).forEach(fieldName => {
            const fieldElement = document.querySelector(`[data-field-name="${fieldName}"]`);
            if (fieldElement) {
                new UniversalEntitySearch(fieldElement);
            }
        });
        
        console.log('✅ Universal Entity Search fields initialized');
    } catch (error) {
        console.error('Error initializing entity search:', error);
    }
}

function initializeDatePresets() {
    // Setup date preset functionality
    window.applyDatePreset = function(presetValue, fieldName) {
        if (!presetValue) return;
        
        // ✅ Backend API call for date calculation
        fetch('/api/universal/date-preset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                preset: presetValue,
                field_name: fieldName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.start_date) {
                const startField = document.getElementById(`filter_start_date`);
                const endField = document.getElementById(`filter_end_date`);
                
                if (startField) startField.value = data.start_date;
                if (endField) endField.value = data.end_date;
                
                // Submit form to apply filter
                document.getElementById('universal-filter-form').submit();
            }
        })
        .catch(error => {
            console.error('Error applying date preset:', error);
        });
    };
}

/**
 * Setup clickable summary cards for filtering
 * Submits form to Flask backend with filter values
 */
function setupClickableCards() {
    document.querySelectorAll('.universal-stat-card.filterable').forEach(function(card) {
        card.addEventListener('click', function() {
            const filterField = card.dataset.filterField;
            const filterValue = card.dataset.filterValue;
            const form = document.getElementById('universal-filter-form');
            
            if (form && filterField && filterValue) {
                // Set the filter value in the form
                const filterInput = form.querySelector(`[name="${filterField}"]`);
                if (filterInput) {
                    if (filterInput.type === 'select-one') {
                        filterInput.value = filterValue;
                    } else if (filterInput.type === 'text') {
                        filterInput.value = filterValue;
                    }
                    
                    // Submit form to Flask backend
                    form.submit();
                } else {
                    // Create hidden input if field doesn't exist
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = filterField;
                    hiddenInput.value = filterValue;
                    form.appendChild(hiddenInput);
                    form.submit();
                }
            }
        });
    });
}

/**
 * Basic form enhancements for better UX
 * No complex logic - just visual improvements
 */
function setupFormEnhancements() {
    // Add loading state when forms are submitted
    document.querySelectorAll('form').forEach(function(form) {
        form.addEventListener('submit', function() {
            // Add loading class to body
            document.body.classList.add('universal-loading');
            
            // Disable submit buttons to prevent double submission
            const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            submitButtons.forEach(function(button) {
                button.disabled = true;
                if (button.textContent) {
                    button.dataset.originalText = button.textContent;
                    button.textContent = 'Loading...';
                }
            });
        });
    });
    
    // Enhanced focus states for form inputs
    document.querySelectorAll('.universal-form-input, .universal-filter-auto-submit').forEach(function(input) {
        input.addEventListener('focus', function() {
            input.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            input.parentElement.classList.remove('focused');
        });
    });
}

/**
 * ==========================================
 * ACTIVE FILTERS FUNCTIONALITY (Entity-Agnostic)
 * ==========================================
 */


function initializeActiveFilters() {
    // Create container if it doesn't exist
    ensureActiveFiltersContainer();
    
    // Initial display update
    updateActiveFiltersDisplay();
    
    // Add real-time listeners to form
    const form = document.getElementById('universal-filter-form');
    if (form) {
        // Listen to all input changes
        form.addEventListener('input', debounce(updateActiveFiltersDisplay, 300));
        form.addEventListener('change', updateActiveFiltersDisplay);
        
        // Listen to date field changes specifically
        const dateFields = form.querySelectorAll('input[type="date"]');
        dateFields.forEach(field => {
            field.addEventListener('change', updateActiveFiltersDisplay);
        });
    }
    
    console.log('✅ Active filters initialized');
}

function updateActiveFiltersDisplay() {
    const wrapper = document.getElementById('active-filters-wrapper');
    const section = document.getElementById('active-filters-section');
    
    if (!wrapper || !section) {
        ensureActiveFiltersContainer();
        return;
    }
    
    const activeFilters = getCurrentActiveFilters();
    
    if (activeFilters.length > 0) {
        wrapper.innerHTML = generateActiveFiltersHTML(activeFilters);
        section.style.display = 'block';
    } else {
        wrapper.innerHTML = getNoFiltersMessage();
        section.style.display = 'block'; // Still show "no filters" message
    }
}

function getCurrentActiveFilters() {
    const form = document.getElementById('universal-filter-form');
    if (!form) return [];
    
    const filters = [];
    
    // Check all form inputs with values (entity-agnostic)
    const inputs = form.querySelectorAll('input[name], select[name], textarea[name]');
    inputs.forEach(input => {
        if (shouldIncludeInActiveFilters(input)) {
            filters.push(createFilterFromInput(input));
        }
    });
    
    return filters;
}

function shouldIncludeInActiveFilters(input) {
    // Entity-agnostic filter logic
    const excludedNames = ['page', 'per_page', 'sort', 'direction', '_token', 'csrf_token'];
    
    return input.name && 
           input.value && 
           input.value.toString().trim() &&
           !excludedNames.includes(input.name) &&
           input.type !== 'hidden' &&
           input.type !== 'submit';
}

function createFilterFromInput(input) {
    let label = getInputLabel(input);
    let displayValue = getInputDisplayValue(input);
    
    // ✅ ADD: Special handling for date inputs
    if (input.type === 'date' && input.value) {
        const startDate = document.getElementById('start_date');
        const endDate = document.getElementById('end_date');
        
        if (input === startDate && endDate && endDate.value) {
            // Show as date range if both dates are set
            label = 'Date Range';
            displayValue = `${formatDisplayDate(startDate.value)} to ${formatDisplayDate(endDate.value)}`;
            return {
                key: 'date_range',
                label: label,
                value: displayValue,
                fieldValue: `${startDate.value}|${endDate.value}`,
                inputType: 'date_range'
            };
        } else if (input === endDate && startDate && startDate.value) {
            // Skip end date if start date already created the range
            return null;
        } else {
            displayValue = formatDisplayDate(input.value);
        }
    }
    
    return {
        key: input.name,
        label: label,
        value: displayValue,
        fieldValue: input.value,
        inputType: input.type || input.tagName.toLowerCase()
    };
}

// ✅ ADD: Helper function for date formatting
function formatDisplayDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-GB', { 
            day: '2-digit', 
            month: 'short', 
            year: 'numeric' 
        });
    } catch (e) {
        return dateStr;
    }
}

function getInputLabel(input) {
    // Try multiple ways to get a good label (entity-agnostic)
    return input.dataset.label || 
           input.getAttribute('aria-label') ||
           (input.labels && input.labels[0] ? input.labels[0].textContent.trim() : null) ||
           formatFieldName(input.name);
}

function getInputDisplayValue(input) {
    let value = input.value;
    
    // Format based on input type (entity-agnostic)
    if (input.type === 'date' && value) {
        try {
            const date = new Date(value);
            value = date.toLocaleDateString();
        } catch (e) {
            // Keep original if parsing fails
        }
    } else if (input.tagName === 'SELECT' && input.selectedOptions.length > 0) {
        value = input.selectedOptions[0].text || input.value;
    } else if (input.type === 'checkbox') {
        value = input.checked ? 'Yes' : 'No';
    }
    
    return value;
}

function formatFieldName(fieldName) {
    // Entity-agnostic field name formatting
    return fieldName
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase())
        .replace(/Id$/, 'ID'); // Fix common "Id" -> "ID"
}

function generateActiveFiltersHTML(filters) {
    let html = `
        <div class="flex items-center gap-2 flex-wrap">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
                <i class="fas fa-filter mr-1"></i>Active filters:
            </span>
    `;
    
    filters.forEach(filter => {
        html += `
            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                <span class="font-medium">${filter.label}:</span>
                <span class="ml-1">${filter.value}</span>
                <button type="button" 
                        class="ml-2 text-blue-600 hover:text-blue-800 dark:text-blue-300 dark:hover:text-blue-100" 
                        onclick="removeActiveFilter('${filter.key}')"
                        title="Remove this filter">
                    <i class="fas fa-times text-xs"></i>
                </button>
            </span>
        `;
    });
    
    html += `
            <button type="button" 
                    class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200 ml-2"
                    onclick="clearAllActiveFilters()">
                <i class="fas fa-times-circle mr-1"></i>Clear all
            </button>
        </div>
    `;
    
    return html;
}

function getNoFiltersMessage() {
    return `
        <div class="flex items-center text-sm text-gray-500 dark:text-gray-400">
            <i class="fas fa-info-circle mr-2"></i>
            <span>No active filters - use the controls above to filter results</span>
        </div>
    `;
}

function removeActiveFilter(filterKey) {
    const form = document.getElementById('universal-filter-form');
    if (!form) return;
    
    const input = form.querySelector(`[name="${filterKey}"]`);
    if (input) {
        // Clear the input based on type (entity-agnostic)
        if (input.type === 'checkbox' || input.type === 'radio') {
            input.checked = false;
        } else if (input.tagName === 'SELECT') {
            input.selectedIndex = 0; // Reset to first option (usually empty)
        } else {
            input.value = '';
        }
        
        // Trigger change event
        input.dispatchEvent(new Event('change', { bubbles: true }));
        
        // Submit form to apply changes
        form.submit();
    }
}

function clearAllActiveFilters() {
    // Navigate to clean URL (entity-agnostic)
    const url = new URL(window.location);
    
    // Keep only essential parameters
    const keepParams = ['entity_type']; // Add others if needed
    const newUrl = new URL(url.pathname, url.origin);
    
    keepParams.forEach(param => {
        if (url.searchParams.has(param)) {
            newUrl.searchParams.set(param, url.searchParams.get(param));
        }
    });
    
    // Navigate
    window.location.href = newUrl.toString();
}

function ensureActiveFiltersContainer() {
    if (document.getElementById('active-filters-section')) return;
    
    // Find filter form or container and add active filters section
    const filterForm = document.getElementById('universal-filter-form');
    if (filterForm && filterForm.parentNode) {
        const container = document.createElement('div');
        container.id = 'active-filters-section';
        container.className = 'bg-blue-50 dark:bg-blue-900 p-3 border-t border-blue-200 dark:border-blue-700';
        container.style.display = 'none';
        container.innerHTML = '<div id="active-filters-wrapper"></div>';
        
        // Insert after the form
        filterForm.parentNode.insertBefore(container, filterForm.nextSibling);
    }
}

/**
 * ==========================================
 * UTILITY FUNCTIONS
 * ==========================================
 */

function debounce(func, wait) {
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

/**
 * ==========================================
 * SUMMARY CARD FILTERING (Entity-Agnostic)
 * ==========================================
 */

function filterByCard(filterField, filterValue) {
    const form = document.getElementById('universal-filter-form');
    if (!form || !filterField || !filterValue) return;
    
    // Find or create the filter input (entity-agnostic)
    let filterInput = form.querySelector(`[name="${filterField}"]`);
    
    if (filterInput) {
        // Set the value based on input type
        if (filterInput.tagName === 'SELECT') {
            filterInput.value = filterValue;
        } else if (filterInput.type === 'checkbox') {
            filterInput.checked = true;
            if (filterInput.value !== filterValue) {
                filterInput.value = filterValue;
            }
        } else {
            filterInput.value = filterValue;
        }
        
        // Trigger change event
        filterInput.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
        // Create hidden input for filter if it doesn't exist
        filterInput = document.createElement('input');
        filterInput.type = 'hidden';
        filterInput.name = filterField;
        filterInput.value = filterValue;
        form.appendChild(filterInput);
    }
    
    // Submit form
    form.submit();
}

// function initializeDatePresets() {
//     const presetButtons = document.querySelectorAll('.date-filter-preset');
//     const startDateInput = document.getElementById('start_date');
//     const endDateInput = document.getElementById('end_date');
    
//     if (!presetButtons.length || !startDateInput || !endDateInput) return;
    
//     presetButtons.forEach(button => {
//         button.addEventListener('click', function(e) {
//             e.preventDefault();
            
//             // Remove active class from all buttons
//             presetButtons.forEach(btn => btn.classList.remove('active'));
//             this.classList.add('active');
            
//             // Apply the preset
//             const preset = this.dataset.preset;
//             applyDatePreset(preset, startDateInput, endDateInput);
            
//             // Update active filters display
//             updateActiveFiltersDisplay();
//         });
//     });
    
//     console.log('✅ Date presets initialized');
// }

// function applyDatePreset(preset, startInput, endInput) {
//     const today = new Date();
    
//     switch(preset) {
//         case 'today':
//             const todayStr = formatDateForInput(today);
//             startInput.value = todayStr;
//             endInput.value = todayStr;
//             break;
            
//         case 'this_month':
//             const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
//             const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
//             startInput.value = formatDateForInput(firstDay);
//             endInput.value = formatDateForInput(lastDay);
//             break;
            
//         case 'financial_year':
//             const year = today.getMonth() >= 3 ? today.getFullYear() : today.getFullYear() - 1;
//             const fyStart = new Date(year, 3, 1); // April 1st
//             const fyEnd = new Date(year + 1, 2, 31); // March 31st next year
//             startInput.value = formatDateForInput(fyStart);
//             endInput.value = formatDateForInput(fyEnd);
//             break;
            
//         case 'clear':
//             startInput.value = '';
//             endInput.value = '';
//             break;
//     }
    
//     // Trigger change events
//     startInput.dispatchEvent(new Event('change', { bubbles: true }));
//     endInput.dispatchEvent(new Event('change', { bubbles: true }));
// }

// function formatDateForInput(date) {
//     return date.toISOString().split('T')[0];
// }