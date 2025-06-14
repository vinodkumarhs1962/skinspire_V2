// static/js/components/form_handler.js

/**
 * FormHandler Component
 * 
 * A reusable form handling class with standardized behavior:
 * - Validates form data before submission
 * - Works with PatientSearch component
 * - Handles dynamic field display/hiding
 * - Manages calculated fields (totals, etc.)
 */
class FormHandler {
    /**
     * Create a form handler component
     * @param {Object} options - Configuration options
     */
    constructor(options) {
        this.options = Object.assign({
            // Form selector
            formSelector: 'form',
            
            // Patient search integration
            patientSearchOptions: null,  // PatientSearch options if patient selection is needed
            
            // Field options
            patientIdField: 'patient_id',
            
            // Visibility toggle configurations
            toggles: [],  // Array of {trigger: selector, target: selector, condition: function}
            
            // Calculation configurations
            calculations: [],  // Array of {inputs: [selectors], output: selector, formula: function}
            
            // Validation configurations
            validations: [],  // Array of {field: selector, rules: [functions], message: string}
            
            // Callbacks
            onBeforeSubmit: null,  // Function called before submit
            onValidationFailed: null,  // Function called on validation failure
            onSubmitSuccess: null  // Function called after successful submission
        }, options);
        
        // Get form element
        this.form = document.querySelector(this.options.formSelector);
        if (!this.form) {
            console.error('Form not found:', this.options.formSelector);
            return;
        }
        
        // Initialize patient search if needed
        this.patientSearch = null;
        if (this.options.patientSearchOptions) {
            this.initPatientSearch();
        }
        
        // Initialize form
        this.init();
    }
    
    /**
     * Initialize the form handler
     */
    init() {
        // Set up toggles
        this.initToggles();
        
        // Set up calculations
        this.initCalculations();
        
        // Set up validations
        this.initValidations();
        
        // Add form submit handler
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
        
        console.log('Form handler initialized');
    }
    
    /**
     * Initialize PatientSearch component
     */
    initPatientSearch() {
        if (typeof PatientSearch !== 'function') {
            console.warn('PatientSearch not available');
            return;
        }
        
        // Create options with defaults
        const options = Object.assign({
            containerSelector: this.options.formSelector,
            patientIdField: this.options.patientIdField
        }, this.options.patientSearchOptions);
        
        // Initialize PatientSearch
        this.patientSearch = new PatientSearch(options);
    }
    
    /**
     * Initialize field toggle behaviors
     */
    initToggles() {
        this.options.toggles.forEach(toggle => {
            // Handle multiple triggers (comma-separated selectors)
            const triggerSelectors = toggle.trigger.split(',').map(s => s.trim());
            const triggerEls = triggerSelectors.map(selector => 
                Array.from(document.querySelectorAll(selector))
            ).flat();
            
            const targetEl = document.querySelector(toggle.target);
            
            if (triggerEls.length === 0 || !targetEl) {
                return;
            }
            
            // Initial state - check all triggers
            this.updateToggle(triggerEls, targetEl, toggle.condition);
            
            // Listen for changes on all triggers
            triggerEls.forEach(triggerEl => {
                triggerEl.addEventListener('input', () => {
                    this.updateToggle(triggerEls, targetEl, toggle.condition);
                });
                
                // For select elements
                triggerEl.addEventListener('change', () => {
                    this.updateToggle(triggerEls, targetEl, toggle.condition);
                });
            });
        });
    }
    
    /**
     * Update toggle state based on condition
     */
    updateToggle(triggerEls, targetEl, condition) {
        if (condition(triggerEls)) {
            targetEl.classList.remove('hidden');
        } else {
            targetEl.classList.add('hidden');
        }
    }
    
    /**
     * Initialize calculation behaviors
     */
    initCalculations() {
        this.options.calculations.forEach(calc => {
            // Get input elements
            const inputEls = calc.inputs.map(selector => 
                document.querySelector(selector)
            ).filter(el => el !== null);
            
            const outputEl = document.querySelector(calc.output);
            
            if (!outputEl || inputEls.length === 0) {
                return;
            }
            
            // Initial calculation
            this.updateCalculation(inputEls, outputEl, calc.formula);
            
            // Listen for changes
            inputEls.forEach(input => {
                input.addEventListener('input', () => {
                    this.updateCalculation(inputEls, outputEl, calc.formula);
                });
                
                // For select elements
                input.addEventListener('change', () => {
                    this.updateCalculation(inputEls, outputEl, calc.formula);
                });
            });
        });
    }
    
    /**
     * Update calculation based on formula
     */
    updateCalculation(inputEls, outputEl, formula) {
        const result = formula(inputEls);
        
        if (outputEl.tagName === 'INPUT' || outputEl.tagName === 'TEXTAREA' || outputEl.tagName === 'SELECT') {
            outputEl.value = result;
        } else {
            outputEl.textContent = result;
        }
    }
    
    /**
     * Initialize form validations
     */
    initValidations() {
        this.options.validations.forEach(validation => {
            // Handle multiple fields (comma-separated selectors)
            const fieldSelectors = validation.field.split(',').map(s => s.trim());
            const fieldEls = fieldSelectors.map(selector => 
                document.querySelector(selector)
            ).filter(el => el !== null);
            
            if (fieldEls.length === 0) {
                return;
            }
            
            // Add validation attributes if needed
            fieldEls.forEach(fieldEl => {
                if (validation.required) {
                    fieldEl.setAttribute('required', 'required');
                }
                
                if (validation.min !== undefined) {
                    fieldEl.setAttribute('min', validation.min);
                }
                
                if (validation.max !== undefined) {
                    fieldEl.setAttribute('max', validation.max);
                }
                
                if (validation.pattern) {
                    fieldEl.setAttribute('pattern', validation.pattern);
                }
            });
        });
    }
    
    /**
     * Handle form submission
     */
    handleSubmit(e) {
        // Don't prevent default yet - we'll do that if validation fails
        
        // Check if all required fields are filled
        const isValid = this.validateForm();
        
        if (!isValid) {
            e.preventDefault();
            
            // Call validation failed callback
            if (typeof this.options.onValidationFailed === 'function') {
                this.options.onValidationFailed();
            } else {
                // Default behavior
                alert('Please correct the errors in the form before submitting.');
            }
            
            return false;
        }
        
        // Call before submit callback
        if (typeof this.options.onBeforeSubmit === 'function') {
            const shouldContinue = this.options.onBeforeSubmit();
            
            if (shouldContinue === false) {
                e.preventDefault();
                return false;
            }
        }
        
        // Let the form submit normally
        
        // Call after submit callback (for AJAX forms)
        if (!this.form.getAttribute('action') && typeof this.options.onSubmitSuccess === 'function') {
            e.preventDefault();
            this.options.onSubmitSuccess();
        }
    }
    
    /**
     * Validate the form
     */
    validateForm() {
        let isValid = true;
        
        // Check patient selection if applicable
        if (this.options.patientSearchOptions) {
            const patientIdField = document.getElementById(this.options.patientIdField);
            
            if (!patientIdField || !patientIdField.value) {
                isValid = false;
                
                // Show error message
                const errorEl = document.querySelector(`[data-error-for="${this.options.patientIdField}"]`);
                if (errorEl) {
                    errorEl.textContent = 'Please select a patient';
                    errorEl.classList.remove('hidden');
                }
            }
        }
        
        // Run custom validations
        this.options.validations.forEach(validation => {
            // Handle multiple fields (comma-separated selectors)
            const fieldSelectors = validation.field.split(',').map(s => s.trim());
            const fieldEls = fieldSelectors.map(selector => 
                document.querySelector(selector)
            ).filter(el => el !== null);
            
            if (fieldEls.length === 0) {
                return;
            }
            
            // Clear previous errors
            fieldEls.forEach(fieldEl => {
                const errorEl = document.querySelector(`[data-error-for="${fieldEl.id}"]`);
                if (errorEl) {
                    errorEl.textContent = '';
                    errorEl.classList.add('hidden');
                }
            });
            
            // Run all validation rules
            for (const rule of validation.rules) {
                const isFieldValid = rule(fieldEls);
                
                if (!isFieldValid) {
                    isValid = false;
                    
                    // Show error message on the first field
                    if (fieldEls.length > 0) {
                        const errorEl = document.querySelector(`[data-error-for="${fieldEls[0].id}"]`);
                        if (errorEl) {
                            errorEl.textContent = validation.message;
                            errorEl.classList.remove('hidden');
                        }
                    }
                    
                    break;
                }
            }
        });
        
        return isValid;
    }
    
    /**
     * Add a validation error programmatically
     */
    addError(fieldSelector, message) {
        const errorEl = document.querySelector(`[data-error-for="${fieldSelector}"]`);
        
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }
    }
    
    /**
     * Clear all validation errors
     */
    clearErrors() {
        document.querySelectorAll('[data-error-for]').forEach(el => {
            el.textContent = '';
            el.classList.add('hidden');
        });
    }
}

// Export for global use
window.FormHandler = FormHandler;