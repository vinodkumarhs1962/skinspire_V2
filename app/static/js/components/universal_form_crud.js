/**
 * =============================================================================
 * UNIVERSAL FORM CRUD JAVASCRIPT
 * File: /static/js/components/universal_form_crud.js
 * =============================================================================
 * 
 * Universal Engine CRUD Form Operations
 * Handles Create, Edit, Delete form interactions
 * 
 * Features:
 * ✅ Form Validation (Bootstrap + Custom)
 * ✅ Auto-Save Drafts
 * ✅ Unsaved Changes Warning
 * ✅ Field Formatting (Phone, Currency, etc.)
 * ✅ Dynamic Field Visibility
 * ✅ Delete Confirmation
 * ✅ Success/Error Notifications
 * ✅ Mobile Responsive
 */

// =============================================================================
// UNIVERSAL FORM CRUD CLASS
// =============================================================================

class UniversalFormCRUD {
    constructor(config = {}) {
        this.config = {
            autoSaveInterval: 30000,    // 30 seconds
            autoSaveEnabled: true,
            unsavedWarningEnabled: true,
            validationEnabled: true,
            formattingEnabled: true,
            deleteConfirmationEnabled: true,
            notificationDuration: 5000,
            ...config
        };
        
        this.state = {
            formChanged: false,
            autoSaveTimer: null,
            validationErrors: {},
            currentFormId: null,
            currentEntityType: null,
            isSubmitting: false
        };
        
        console.log('🚀 Universal Form CRUD Engine initialized');
    }
    
    // =============================================================================
    // INITIALIZATION
    // =============================================================================
    
    initialize(formId = null, entityType = null) {
        try {
            // Auto-detect form if not provided
            if (!formId) {
                formId = this.detectFormId();
            }
            
            if (!formId) {
                console.warn('No CRUD form found on page');
                return;
            }
            
            this.state.currentFormId = formId;
            this.state.currentEntityType = entityType || this.detectEntityType();
            
            const form = document.getElementById(formId);
            if (!form) {
                console.error(`Form not found: ${formId}`);
                return;
            }
            
            // Initialize all features
            if (this.config.validationEnabled) {
                this.initializeValidation(form);
            }
            
            if (this.config.autoSaveEnabled) {
                this.initializeAutoSave(form);
            }
            
            if (this.config.unsavedWarningEnabled) {
                this.initializeUnsavedWarning(form);
            }
            
            if (this.config.formattingEnabled) {
                this.initializeFieldFormatting(form);
            }
            
            if (this.config.deleteConfirmationEnabled) {
                this.initializeDeleteHandlers();
            }
            
            this.initializeDynamicFields(form);
            this.initializeSubmitHandlers(form);
            this.bindGlobalHelpers();
            
            console.log(`✅ Form CRUD initialized for: ${formId} (${this.state.currentEntityType})`);
            
        } catch (error) {
            console.error('❌ Error initializing Form CRUD:', error);
        }
    }
    
    detectFormId() {
        // Try to find CRUD forms on the page
        const possibleIds = ['universal-create-form', 'universal-edit-form', 'crud-form'];
        for (const id of possibleIds) {
            if (document.getElementById(id)) {
                return id;
            }
        }
        // Try to find any form with CRUD class
        const form = document.querySelector('.universal-crud-form');
        return form ? form.id : null;
    }
    
    detectEntityType() {
        // Try to detect entity type from various sources
        const form = document.getElementById(this.state.currentFormId);
        if (form) {
            // Check data attribute
            if (form.dataset.entityType) return form.dataset.entityType;
            
            // Check hidden field
            const entityField = form.querySelector('input[name="entity_type"]');
            if (entityField) return entityField.value;
        }
        
        // Check URL
        const urlParts = window.location.pathname.split('/');
        const universalIndex = urlParts.indexOf('universal');
        if (universalIndex >= 0 && urlParts[universalIndex + 1]) {
            return urlParts[universalIndex + 1];
        }
        
        return 'unknown';
    }
    
    // =============================================================================
    // FORM VALIDATION
    // =============================================================================
    
    initializeValidation(form) {
        // Bootstrap validation
        form.addEventListener('submit', (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                this.handleValidationErrors(form);
            }
            form.classList.add('was-validated');
        }, false);
        
        // Real-time field validation
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('change', () => this.validateField(input));
        });
        
        console.log('✅ Form validation initialized');
    }
    
    validateField(field) {
        // Remove previous validation classes
        field.classList.remove('is-valid', 'is-invalid');
        
        // Basic HTML5 validation
        if (!field.checkValidity()) {
            field.classList.add('is-invalid');
            this.showFieldError(field, field.validationMessage);
            return false;
        }
        
        // Custom validations
        const isValid = this.runCustomValidations(field);
        
        if (isValid) {
            field.classList.add('is-valid');
            this.clearFieldError(field);
        } else {
            field.classList.add('is-invalid');
        }
        
        return isValid;
    }
    
    runCustomValidations(field) {
        let isValid = true;
        
        // Email validation
        if (field.type === 'email' && field.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value)) {
                this.showFieldError(field, 'Please enter a valid email address');
                isValid = false;
            }
        }
        
        // Phone validation
        if (field.type === 'tel' && field.value) {
            const phoneRegex = /^[\d\s\-\+\(\)]+$/;
            if (!phoneRegex.test(field.value)) {
                this.showFieldError(field, 'Please enter a valid phone number');
                isValid = false;
            }
        }
        
        // GST validation (Indian GST)
        if (field.name === 'gst_number' && field.value) {
            const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
            if (!gstRegex.test(field.value.toUpperCase())) {
                this.showFieldError(field, 'Please enter a valid GST number');
                isValid = false;
            }
        }
        
        // PAN validation (Indian PAN)
        if (field.name === 'pan_number' && field.value) {
            const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
            if (!panRegex.test(field.value.toUpperCase())) {
                this.showFieldError(field, 'Please enter a valid PAN number');
                isValid = false;
            }
        }
        
        // Field matching (e.g., password confirmation)
        if (field.dataset.match) {
            const matchField = document.getElementById(field.dataset.match);
            if (matchField && field.value !== matchField.value) {
                this.showFieldError(field, 'Fields do not match');
                isValid = false;
            }
        }
        
        return isValid;
    }
    
    showFieldError(field, message) {
        // Find or create error element
        let errorEl = field.parentElement.querySelector('.invalid-feedback');
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.className = 'invalid-feedback';
            field.parentElement.appendChild(errorEl);
        }
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }
    
    clearFieldError(field) {
        const errorEl = field.parentElement.querySelector('.invalid-feedback');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }
    
    handleValidationErrors(form) {
        // Focus first invalid field
        const firstInvalid = form.querySelector(':invalid');
        if (firstInvalid) {
            firstInvalid.focus();
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Show notification
            this.showNotification('error', 'Please correct the errors in the form');
        }
    }
    
    // =============================================================================
    // AUTO-SAVE FUNCTIONALITY
    // =============================================================================
    
    initializeAutoSave(form) {
        if (typeof(Storage) === "undefined") {
            console.warn('LocalStorage not supported - auto-save disabled');
            return;
        }
        
        const storageKey = this.getStorageKey();
        
        // Restore saved draft on load
        this.restoreDraft(form, storageKey);
        
        // Save draft on input change
        form.addEventListener('input', () => {
            this.state.formChanged = true;
            this.scheduleSaveDraft(form, storageKey);
        });
        
        // Clear draft on successful submit
        form.addEventListener('submit', () => {
            if (form.checkValidity()) {
                this.clearDraft(storageKey);
            }
        });
        
        console.log('✅ Auto-save initialized');
    }
    
    getStorageKey() {
        const formId = this.state.currentFormId;
        const entityType = this.state.currentEntityType;
        const userId = this.getCurrentUserId();
        return `universal_form_draft_${entityType}_${formId}_${userId}`;
    }
    
    getCurrentUserId() {
        // Try to get user ID from various sources
        const userEl = document.querySelector('[data-user-id]');
        if (userEl) return userEl.dataset.userId;
        
        // Check meta tag
        const meta = document.querySelector('meta[name="user-id"]');
        if (meta) return meta.content;
        
        return 'default';
    }
    
    scheduleSaveDraft(form, storageKey) {
        // Clear existing timer
        if (this.state.autoSaveTimer) {
            clearTimeout(this.state.autoSaveTimer);
        }
        
        // Schedule new save
        this.state.autoSaveTimer = setTimeout(() => {
            this.saveDraft(form, storageKey);
            this.showAutoSaveIndicator();
        }, 2000); // Save after 2 seconds of inactivity
    }
    
    saveDraft(form, storageKey) {
        try {
            const formData = new FormData(form);
            const data = {};
            
            formData.forEach((value, key) => {
                // Skip file inputs
                const field = form.elements[key];
                if (field && field.type !== 'file') {
                    data[key] = value;
                }
            });
            
            data._savedAt = new Date().toISOString();
            data._formId = this.state.currentFormId;
            data._entityType = this.state.currentEntityType;
            
            localStorage.setItem(storageKey, JSON.stringify(data));
            console.log('📝 Draft saved');
            
        } catch (error) {
            console.error('Error saving draft:', error);
        }
    }
    
    restoreDraft(form, storageKey) {
        try {
            const savedData = localStorage.getItem(storageKey);
            if (!savedData) return;
            
            const data = JSON.parse(savedData);
            const savedTime = new Date(data._savedAt);
            const now = new Date();
            const hoursDiff = (now - savedTime) / (1000 * 60 * 60);
            
            // Only restore if less than 24 hours old
            if (hoursDiff < 24) {
                const timeAgo = this.formatTimeAgo(savedTime);
                
                if (confirm(`Found unsaved changes from ${timeAgo}. Would you like to restore them?`)) {
                    Object.keys(data).forEach(key => {
                        if (key.startsWith('_')) return; // Skip metadata
                        
                        const field = form.elements[key];
                        if (field) {
                            if (field.type === 'checkbox' || field.type === 'radio') {
                                field.checked = data[key] === 'on' || data[key] === '1' || data[key] === true;
                            } else {
                                field.value = data[key];
                            }
                        }
                    });
                    
                    this.showNotification('success', 'Draft restored successfully');
                } else {
                    this.clearDraft(storageKey);
                }
            } else {
                // Clear old draft
                this.clearDraft(storageKey);
            }
        } catch (error) {
            console.error('Error restoring draft:', error);
            this.clearDraft(storageKey);
        }
    }
    
    clearDraft(storageKey) {
        try {
            localStorage.removeItem(storageKey);
            console.log('🗑️ Draft cleared');
        } catch (error) {
            console.error('Error clearing draft:', error);
        }
    }
    
    showAutoSaveIndicator() {
        let indicator = document.getElementById('auto-save-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'auto-save-indicator';
            indicator.className = 'auto-save-indicator';
            indicator.innerHTML = '<i class="fas fa-save"></i> Draft saved';
            document.body.appendChild(indicator);
        }
        
        indicator.classList.add('show');
        setTimeout(() => {
            indicator.classList.remove('show');
        }, 2000);
    }
    
    formatTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
        return date.toLocaleString();
    }
    
    // =============================================================================
    // UNSAVED CHANGES WARNING
    // =============================================================================
    
    initializeUnsavedWarning(form) {
        // Track form changes
        form.addEventListener('change', () => {
            this.state.formChanged = true;
        });
        
        // Reset on submit
        form.addEventListener('submit', () => {
            this.state.formChanged = false;
        });
        
        // Warn on navigation
        window.addEventListener('beforeunload', (e) => {
            if (this.state.formChanged && !this.state.isSubmitting) {
                const message = 'You have unsaved changes. Are you sure you want to leave?';
                e.preventDefault();
                e.returnValue = message;
                return message;
            }
        });
        
        // Warn on internal navigation
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && this.state.formChanged && !this.state.isSubmitting) {
                const href = link.getAttribute('href');
                if (href && !href.startsWith('#') && !link.classList.contains('no-warn')) {
                    if (!confirm('You have unsaved changes. Are you sure you want to leave?')) {
                        e.preventDefault();
                    }
                }
            }
        });
        
        console.log('✅ Unsaved changes warning initialized');
    }
    
    // =============================================================================
    // FIELD FORMATTING
    // =============================================================================
    
    initializeFieldFormatting(form) {
        // Phone number formatting
        form.querySelectorAll('input[type="tel"], .phone-input').forEach(input => {
            input.addEventListener('input', () => this.formatPhoneNumber(input));
        });
        
        // Currency formatting
        form.querySelectorAll('.currency-input, .amount-input').forEach(input => {
            input.addEventListener('blur', () => this.formatCurrency(input));
            input.addEventListener('focus', () => this.unformatCurrency(input));
        });
        
        // Uppercase formatting
        form.querySelectorAll('.uppercase-input').forEach(input => {
            input.addEventListener('input', () => {
                input.value = input.value.toUpperCase();
            });
        });
        
        // GST number formatting
        form.querySelectorAll('[name="gst_number"]').forEach(input => {
            input.addEventListener('input', () => {
                input.value = input.value.toUpperCase();
            });
        });
        
        // PAN number formatting
        form.querySelectorAll('[name="pan_number"]').forEach(input => {
            input.addEventListener('input', () => {
                input.value = input.value.toUpperCase();
            });
        });
        
        console.log('✅ Field formatting initialized');
    }
    
    formatPhoneNumber(input) {
        // Remove non-digits
        let value = input.value.replace(/\D/g, '');
        
        // Indian phone number format
        if (value.length > 0) {
            if (value.length <= 5) {
                value = value;
            } else if (value.length <= 10) {
                value = value.slice(0, 5) + '-' + value.slice(5);
            } else {
                value = '+91-' + value.slice(0, 5) + '-' + value.slice(5, 10);
            }
        }
        
        input.value = value;
    }
    
    formatCurrency(input) {
        let value = parseFloat(input.value.replace(/[^0-9.-]/g, ''));
        if (!isNaN(value)) {
            // Format with Indian currency notation
            input.value = this.formatIndianCurrency(value);
        }
    }
    
    unformatCurrency(input) {
        input.value = input.value.replace(/[^0-9.-]/g, '');
    }
    
    formatIndianCurrency(num) {
        const formatted = num.toFixed(2);
        const parts = formatted.split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{2})+(?!\d))/g, ',');
        return '₹ ' + parts.join('.');
    }
    
    // =============================================================================
    // DYNAMIC FIELD VISIBILITY
    // =============================================================================
    
    initializeDynamicFields(form) {
        // Fields that show/hide based on other fields
        const conditionalFields = form.querySelectorAll('[data-show-if]');
        
        conditionalFields.forEach(field => {
            const condition = field.dataset.showIf;
            const [triggerField, triggerValue] = condition.split('=');
            const trigger = form.querySelector(`[name="${triggerField}"]`);
            
            if (trigger) {
                // Initial check
                this.toggleFieldVisibility(field, trigger, triggerValue);
                
                // Listen for changes
                trigger.addEventListener('change', () => {
                    this.toggleFieldVisibility(field, trigger, triggerValue);
                });
            }
        });
        
        console.log('✅ Dynamic fields initialized');
    }
    
    toggleFieldVisibility(field, trigger, expectedValue) {
        const container = field.closest('.form-group') || field.closest('.col-md-6') || field.parentElement;
        
        let show = false;
        if (trigger.type === 'checkbox') {
            show = trigger.checked && expectedValue === 'true';
        } else if (trigger.type === 'radio') {
            show = trigger.checked && trigger.value === expectedValue;
        } else {
            show = trigger.value === expectedValue;
        }
        
        container.style.display = show ? 'block' : 'none';
        
        // Update required attribute
        const inputs = container.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (show && input.dataset.wasRequired === 'true') {
                input.setAttribute('required', 'required');
            } else if (!show) {
                if (input.hasAttribute('required')) {
                    input.dataset.wasRequired = 'true';
                }
                input.removeAttribute('required');
            }
        });
    }
    
    // =============================================================================
    // DELETE CONFIRMATION
    // =============================================================================
    
    initializeDeleteHandlers() {
        document.addEventListener('click', (e) => {
            const deleteBtn = e.target.closest('.delete-btn, .btn-delete, [data-action="delete"]');
            if (deleteBtn) {
                e.preventDefault();
                this.handleDelete(deleteBtn);
            }
        });
        
        console.log('✅ Delete handlers initialized');
    }
    
    handleDelete(button) {
        const entityName = button.dataset.entityName || 'this item';
        const deleteUrl = button.dataset.deleteUrl || button.href;
        const confirmMessage = button.dataset.confirmMessage || 
                             `Are you sure you want to delete ${entityName}? This action cannot be undone.`;
        
        if (confirm(confirmMessage)) {
            this.performDelete(deleteUrl);
        }
    }
    
    performDelete(url) {
        // Show loading
        this.showNotification('info', 'Deleting...');
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCSRFToken()
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showNotification('success', data.message || 'Deleted successfully');
                
                // Redirect if URL provided
                if (data.redirect_url) {
                    this.state.formChanged = false; // Prevent unsaved warning
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1000);
                }
            } else {
                this.showNotification('error', data.message || 'Failed to delete');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            this.showNotification('error', 'An error occurred while deleting');
        });
    }
    
    // =============================================================================
    // FORM SUBMISSION
    // =============================================================================
    
    initializeSubmitHandlers(form) {
        form.addEventListener('submit', (e) => {
            this.state.isSubmitting = true;
            
            // Show loading state
            const submitBtns = form.querySelectorAll('[type="submit"]');
            submitBtns.forEach(btn => {
                btn.disabled = true;
                btn.dataset.originalText = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
            });
        });
        
        console.log('✅ Submit handlers initialized');
    }
    
    // =============================================================================
    // NOTIFICATIONS
    // =============================================================================
    
    showNotification(type, message) {
        // Remove existing notifications
        const existing = document.querySelector('.crud-notification');
        if (existing) existing.remove();
        
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' :
                          type === 'warning' ? 'alert-warning' : 'alert-info';
        
        const icon = type === 'success' ? 'fa-check-circle' :
                    type === 'error' ? 'fa-exclamation-circle' :
                    type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle';
        
        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show crud-notification`;
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            <i class="fas ${icon} me-2"></i>
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-dismiss
        setTimeout(() => {
            notification.remove();
        }, this.config.notificationDuration);
    }
    
    // =============================================================================
    // UTILITIES
    // =============================================================================
    
    getCSRFToken() {
        // Try various methods to get CSRF token
        const token = document.querySelector('[name=csrf_token]');
        if (token) return token.value;
        
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;
        
        return '';
    }
    
    bindGlobalHelpers() {
        // Make functions available globally
        window.universalFormCRUD = {
            validateField: (field) => this.validateField(field),
            formatPhoneNumber: (input) => this.formatPhoneNumber(input),
            formatCurrency: (input) => this.formatCurrency(input),
            showNotification: (type, message) => this.showNotification(type, message),
            saveDraft: () => {
                const form = document.getElementById(this.state.currentFormId);
                if (form) this.saveDraft(form, this.getStorageKey());
            },
            clearDraft: () => this.clearDraft(this.getStorageKey())
        };
    }
}

// =============================================================================
// AUTO-INITIALIZATION
// =============================================================================

// Create global instance
window.UniversalFormCRUD = UniversalFormCRUD;
window.formCRUD = null;

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a CRUD form page
    const crudForm = document.querySelector('#universal-create-form, #universal-edit-form, .universal-crud-form');
    
    if (crudForm) {
        // Get entity type from various sources
        const entityType = crudForm.dataset.entityType || 
                         document.body.dataset.entityType ||
                         window.entityType;
        
        // Initialize
        window.formCRUD = new UniversalFormCRUD();
        window.formCRUD.initialize(crudForm.id, entityType);
    }
});

// =============================================================================
// CSS STYLES (Inject into page)
// =============================================================================

const styles = `
<style>
/* Auto-save indicator */
.auto-save-indicator {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #28a745;
    color: white;
    padding: 10px 20px;
    border-radius: 4px;
    opacity: 0;
    transform: translateY(20px);
    transition: all 0.3s;
    z-index: 9999;
    display: flex;
    align-items: center;
    gap: 8px;
}

.auto-save-indicator.show {
    opacity: 1;
    transform: translateY(0);
}

/* Field validation states */
.form-control.is-valid,
.form-select.is-valid {
    border-color: #28a745;
    padding-right: calc(1.5em + 0.75rem);
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 8 8'%3e%3cpath fill='%2328a745' d='M2.3 6.73L.6 4.53c-.4-1.04.46-1.4 1.1-.8l1.1 1.4 3.4-3.8c.6-.63 1.6-.27 1.2.7l-4 4.6c-.43.5-.8.4-1.1.1z'/%3e%3c/svg%3e");
    background-repeat: no-repeat;
    background-position: right calc(0.375em + 0.1875rem) center;
    background-size: calc(0.75em + 0.375rem) calc(0.75em + 0.375rem);
}

.form-control.is-invalid,
.form-select.is-invalid {
    border-color: #dc3545;
    padding-right: calc(1.5em + 0.75rem);
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='%23dc3545' viewBox='-2 -2 7 7'%3e%3cpath stroke='%23dc3545' d='M0 0l3 3m0-3L0 3'/%3e%3c/svg%3e");
    background-repeat: no-repeat;
    background-position: right calc(0.375em + 0.1875rem) center;
    background-size: calc(0.75em + 0.375rem) calc(0.75em + 0.375rem);
}

/* Notification styles */
.crud-notification {
    animation: slideInRight 0.3s ease-out;
}

@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* Loading state for submit buttons */
.btn[disabled] .fa-spinner {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
</style>
`;

// Inject styles
document.head.insertAdjacentHTML('beforeend', styles);

console.log('📝 Universal Form CRUD JavaScript loaded');