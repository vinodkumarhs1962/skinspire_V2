/**
 * Barcode Scanner Handler for Helett HT20 Pro
 *
 * Detects barcode scanner input vs manual keyboard typing
 * and triggers callbacks for page-specific handling.
 *
 * KEY PRINCIPLE: This handler only detects scans and calls callbacks.
 * It does NOT directly modify DOM or bypass existing validation.
 *
 * Usage:
 *   const scanner = new BarcodeScanner({
 *       timeout: 50,           // ms between keystrokes (scanner is fast)
 *       minLength: 6,          // minimum barcode length
 *       onScan: function(data) { ... },   // called when barcode scanned
 *       onError: function(msg) { ... },   // called on errors
 *       debug: false           // enable debug logging
 *   });
 *
 *   scanner.enable();  // enable scanning
 *   scanner.disable(); // disable (e.g., when modal is open)
 */

class BarcodeScanner {
    constructor(options = {}) {
        this.buffer = '';
        this.lastKeyTime = 0;
        this.SCAN_TIMEOUT = options.timeout || 50;      // ms between keystrokes
        this.MIN_LENGTH = options.minLength || 6;       // Minimum barcode length
        this.onScan = options.onScan || this.defaultHandler;
        this.onError = options.onError || this.defaultErrorHandler;
        this.onNotFound = options.onNotFound || null;   // Optional: handle not found
        this.enabled = options.enabled !== false;       // Enable by default
        this.debug = options.debug || false;
        this.processing = false;                        // Prevent double processing

        this.init();
    }

    init() {
        // Bind handler to preserve 'this' context
        this.boundHandler = (e) => this.handleKeyPress(e);
        document.addEventListener('keypress', this.boundHandler);

        if (this.debug) {
            console.log('[BarcodeScanner] Initialized with timeout:', this.SCAN_TIMEOUT, 'ms');
        }
    }

    handleKeyPress(e) {
        if (!this.enabled) return;

        const currentTime = Date.now();
        const timeDiff = currentTime - this.lastKeyTime;

        // Reset buffer if too much time passed (manual typing)
        if (timeDiff > this.SCAN_TIMEOUT && this.buffer.length > 0) {
            if (this.debug) {
                console.log('[BarcodeScanner] Buffer reset - time gap:', timeDiff, 'ms');
            }
            this.buffer = '';
        }
        this.lastKeyTime = currentTime;

        // Enter key signals end of barcode
        if (e.key === 'Enter') {
            if (this.buffer.length >= this.MIN_LENGTH) {
                e.preventDefault();
                e.stopPropagation();

                if (!this.processing) {
                    this.processing = true;
                    this.processScan(this.buffer);
                }
            }
            this.buffer = '';
            return;
        }

        // Accumulate printable characters
        if (e.key.length === 1) {
            this.buffer += e.key;

            if (this.debug && this.buffer.length === 1) {
                console.log('[BarcodeScanner] Buffer started');
            }
        }
    }

    async processScan(barcode) {
        if (this.debug) {
            console.log('[BarcodeScanner] Processing:', barcode);
        }

        try {
            const response = await fetch('/api/barcode/lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ barcode: barcode })
            });

            const data = await response.json();

            if (this.debug) {
                console.log('[BarcodeScanner] Response:', data);
            }

            if (data.success) {
                if (data.medicine_found) {
                    // Medicine found - call main handler
                    this.onScan(data);
                } else {
                    // Medicine not found - call not found handler or main handler
                    if (this.onNotFound) {
                        this.onNotFound(data);
                    } else {
                        this.onScan(data);
                    }
                }
            } else {
                this.onError(data.error || 'Barcode lookup failed');
            }
        } catch (error) {
            console.error('[BarcodeScanner] Error:', error);
            this.onError('Failed to process barcode');
        } finally {
            this.processing = false;
        }
    }

    defaultHandler(data) {
        console.log('[BarcodeScanner] Data received:', data);
        // Override this with page-specific handler
    }

    defaultErrorHandler(message) {
        console.error('[BarcodeScanner] Error:', message);
        // Override with your notification system
        if (typeof showNotification === 'function') {
            showNotification('error', message);
        } else {
            alert(message);
        }
    }

    getCSRFToken() {
        // Try multiple sources for CSRF token
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) return metaToken.content;

        const inputToken = document.querySelector('input[name="csrf_token"]');
        if (inputToken) return inputToken.value;

        // Try cookies
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') return value;
        }

        return '';
    }

    enable() {
        this.enabled = true;
        if (this.debug) {
            console.log('[BarcodeScanner] Enabled');
        }
    }

    disable() {
        this.enabled = false;
        this.buffer = '';
        if (this.debug) {
            console.log('[BarcodeScanner] Disabled');
        }
    }

    destroy() {
        document.removeEventListener('keypress', this.boundHandler);
        if (this.debug) {
            console.log('[BarcodeScanner] Destroyed');
        }
    }

    // Static method to disable scanner when any modal opens
    static setupModalHandlers(scanner) {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('show.bs.modal', () => scanner.disable());
            modal.addEventListener('hidden.bs.modal', () => scanner.enable());
        });
    }
}


/**
 * Barcode Link Modal Handler
 * Uses SweetAlert2 for reliable popup display
 */
class BarcodeLinkModal {
    constructor(options = {}) {
        this.onLinked = options.onLinked || null;
        this.onCancel = options.onCancel || null;
        this.currentParsedData = null;
        this.selectedMedicineId = null;
        this.selectedMedicineName = null;
        this.searchTimeout = null;
        this.swalInstance = null;
    }

    init() {
        // No initialization needed for Swal-based approach
    }

    show(parsedData) {
        this.currentParsedData = parsedData;
        this.selectedMedicineId = null;
        this.selectedMedicineName = null;

        const parsed = parsedData.parsed || parsedData;
        const barcodeDisplay = parsed.gtin || '-';
        const batchDisplay = parsed.batch || '';
        const expiryDisplay = parsed.expiry_formatted || parsed.expiry_date || '';

        // Build batch/expiry row HTML if either exists
        let batchExpiryHtml = '';
        if (batchDisplay || expiryDisplay) {
            batchExpiryHtml = `
                <div style="display: flex; gap: 20px; margin-bottom: 15px;">
                    <div style="flex: 1;">
                        <label style="font-size: 12px; color: #6c757d; margin-bottom: 4px; display: block;">Batch</label>
                        <div style="padding: 8px 12px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;">${batchDisplay || '-'}</div>
                    </div>
                    <div style="flex: 1;">
                        <label style="font-size: 12px; color: #6c757d; margin-bottom: 4px; display: block;">Expiry</label>
                        <div style="padding: 8px 12px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;">${expiryDisplay || '-'}</div>
                    </div>
                </div>
            `;
        }

        const htmlContent = `
            <div style="text-align: left;">
                <div style="margin-bottom: 15px;">
                    <label style="font-size: 12px; color: #6c757d; margin-bottom: 4px; display: block;">Scanned Barcode (GTIN)</label>
                    <div style="padding: 8px 12px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; font-weight: 600;">${barcodeDisplay}</div>
                </div>
                ${batchExpiryHtml}
                <div style="margin-bottom: 10px;">
                    <label style="font-size: 12px; color: #6c757d; margin-bottom: 4px; display: block;">Select Medicine</label>
                    <input type="text" id="swal-medicine-search" class="swal2-input" placeholder="Type to search medicine..." style="margin: 0; width: 100%; box-sizing: border-box;">
                </div>
                <div id="swal-search-results" style="max-height: 320px; overflow-y: auto; border: 1px solid #dee2e6; border-radius: 4px; display: none; background: #fff;"></div>
                <div id="swal-selected-medicine" style="display: none; padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; margin-top: 10px; color: #155724;">
                    <i class="fas fa-check-circle" style="margin-right: 5px;"></i>
                    <span id="swal-selected-name"></span>
                </div>
                <div id="swal-create-link" style="display: none; margin-top: 10px;">
                    <a href="#" id="swal-create-medicine-btn" style="color: #007bff; text-decoration: none;">
                        <i class="fas fa-plus-circle" style="margin-right: 5px;"></i>Medicine not found? Create New Medicine
                    </a>
                </div>
            </div>
        `;

        // Check if Swal is available
        if (typeof Swal === 'undefined') {
            console.error('[BarcodeLinkModal] SweetAlert2 not available');
            alert('Barcode not linked to any medicine. Barcode: ' + barcodeDisplay);
            return;
        }

        Swal.fire({
            title: '<i class="fas fa-link" style="margin-right: 8px;"></i>Link Barcode to Medicine',
            html: htmlContent,
            width: 600,
            showCancelButton: true,
            confirmButtonText: '<i class="fas fa-link" style="margin-right: 5px;"></i>Link & Save',
            cancelButtonText: '<i class="fas fa-times" style="margin-right: 5px;"></i>Cancel',
            confirmButtonColor: '#007bff',
            cancelButtonColor: '#6c757d',
            showLoaderOnConfirm: true,
            allowOutsideClick: () => !Swal.isLoading(),
            customClass: {
                confirmButton: 'btn btn-primary',
                cancelButton: 'btn btn-secondary'
            },
            buttonsStyling: true,
            didOpen: () => {
                this.setupSwalEventHandlers();
                // Ensure buttons are visible
                const buttons = document.querySelectorAll('.swal2-actions button');
                buttons.forEach(btn => {
                    btn.style.opacity = '1';
                    btn.style.visibility = 'visible';
                });
            },
            preConfirm: () => {
                return this.linkBarcodeFromSwal();
            }
        }).then((result) => {
            if (result.isDismissed && this.onCancel) {
                this.onCancel();
            }
        });
    }

    setupSwalEventHandlers() {
        const searchInput = document.getElementById('swal-medicine-search');
        const resultsContainer = document.getElementById('swal-search-results');
        const createLink = document.getElementById('swal-create-link');
        const createBtn = document.getElementById('swal-create-medicine-btn');

        // Initially disable confirm button
        const confirmBtn = Swal.getConfirmButton();
        if (confirmBtn) confirmBtn.disabled = true;

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.trim();

                if (this.searchTimeout) clearTimeout(this.searchTimeout);

                if (query.length < 2) {
                    resultsContainer.style.display = 'none';
                    createLink.style.display = 'none';
                    return;
                }

                this.searchTimeout = setTimeout(async () => {
                    try {
                        const response = await fetch(`/api/barcode/search-medicine?q=${encodeURIComponent(query)}&limit=10`);
                        const data = await response.json();

                        if (data.success) {
                            this.renderSwalResults(data.medicines, resultsContainer, createLink);
                        }
                    } catch (error) {
                        console.error('Search error:', error);
                    }
                }, 300);
            });

            // Focus search input
            setTimeout(() => searchInput.focus(), 100);
        }

        if (createBtn) {
            createBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.openCreateMedicine();
            });
        }
    }

    renderSwalResults(medicines, container, createLink) {
        container.innerHTML = '';

        if (medicines.length === 0) {
            container.innerHTML = '<div style="padding: 10px; text-align: center; color: #6c757d;">No medicines found</div>';
            container.style.display = 'block';
            if (createLink) createLink.style.display = 'block';
            return;
        }

        container.style.display = 'block';
        if (createLink) createLink.style.display = 'block';

        medicines.forEach(med => {
            const item = document.createElement('div');
            item.style.cssText = 'padding: 10px; border-bottom: 1px solid #eee; cursor: pointer;';
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${med.medicine_name}</strong>
                        ${med.manufacturer ? `<span style="color: #6c757d; margin-left: 8px;">- ${med.manufacturer}</span>` : ''}
                    </div>
                    ${med.has_barcode ? '<span style="background: #17a2b8; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">Linked</span>' : ''}
                </div>
            `;

            item.addEventListener('click', () => this.selectMedicineInSwal(med, container));
            item.addEventListener('mouseenter', () => item.style.backgroundColor = '#f8f9fa');
            item.addEventListener('mouseleave', () => item.style.backgroundColor = '');

            container.appendChild(item);
        });
    }

    selectMedicineInSwal(medicine, container) {
        this.selectedMedicineId = medicine.medicine_id;
        this.selectedMedicineName = medicine.medicine_name;

        // Update search input
        const searchInput = document.getElementById('swal-medicine-search');
        if (searchInput) searchInput.value = medicine.medicine_name;

        // Hide results
        container.style.display = 'none';

        // Show selected display
        const selectedDisplay = document.getElementById('swal-selected-medicine');
        const selectedName = document.getElementById('swal-selected-name');
        if (selectedDisplay && selectedName) {
            selectedName.textContent = medicine.medicine_name + (medicine.manufacturer ? ' - ' + medicine.manufacturer : '');
            selectedDisplay.style.display = 'block';
        }

        // Enable confirm button
        const confirmBtn = Swal.getConfirmButton();
        if (confirmBtn) confirmBtn.disabled = false;
    }

    async linkBarcodeFromSwal() {
        if (!this.selectedMedicineId || !this.currentParsedData) {
            Swal.showValidationMessage('Please select a medicine first');
            return false;
        }

        const parsed = this.currentParsedData.parsed || this.currentParsedData;
        const barcode = parsed.gtin;

        if (!barcode) {
            Swal.showValidationMessage('No barcode to link');
            return false;
        }

        try {
            const response = await fetch('/api/barcode/link', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    barcode: barcode,
                    medicine_id: this.selectedMedicineId
                })
            });

            const data = await response.json();

            if (data.success) {
                // Call callback with linked medicine data
                if (this.onLinked) {
                    this.onLinked({
                        medicine_id: data.medicine_id,
                        medicine_name: data.medicine_name,
                        barcode: data.barcode,
                        parsed: parsed
                    });
                }

                // Show success message
                Swal.fire({
                    icon: 'success',
                    title: 'Barcode Linked!',
                    text: data.message || `Barcode linked to ${data.medicine_name}`,
                    timer: 2000,
                    showConfirmButton: false
                });

                return true;
            } else {
                Swal.showValidationMessage(data.error || 'Failed to link barcode');
                return false;
            }
        } catch (error) {
            console.error('Link error:', error);
            Swal.showValidationMessage('Failed to link barcode: ' + error.message);
            return false;
        }
    }

    hide() {
        if (typeof Swal !== 'undefined') {
            Swal.close();
        }
    }

    showToast(type, message) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: type === 'error' ? 'error' : type === 'warning' ? 'warning' : type === 'info' ? 'info' : 'success',
                title: message,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000
            });
        } else if (typeof showNotification === 'function') {
            showNotification(type, message);
        } else if (typeof toastr !== 'undefined') {
            toastr[type](message);
        } else {
            alert(message);
        }
    }

    openCreateMedicine() {
        const parsed = this.currentParsedData?.parsed || this.currentParsedData;
        const barcode = parsed?.gtin || '';

        let url = '/universal/medicines/create';
        if (barcode) {
            url += '?barcode=' + encodeURIComponent(barcode);
        }

        // Close Swal
        Swal.close();
        this.reset();

        // Open in new tab
        window.open(url, '_blank');

        // Show instruction toast
        setTimeout(() => {
            this.showToast('info', 'Create the medicine, then scan barcode again to link.');
        }, 500);
    }

    getCSRFToken() {
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) return metaToken.content;

        const inputToken = document.querySelector('input[name="csrf_token"]');
        if (inputToken) return inputToken.value;

        return '';
    }

    reset() {
        this.currentParsedData = null;
        this.selectedMedicineId = null;
        this.selectedMedicineName = null;

        if (this.onCancel) {
            this.onCancel();
        }
    }
}


// Export for use
window.BarcodeScanner = BarcodeScanner;
window.BarcodeLinkModal = BarcodeLinkModal;
