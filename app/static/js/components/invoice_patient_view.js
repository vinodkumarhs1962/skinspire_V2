/**
 * Patient View Launcher
 * Opens pop-up window with clean invoice display for patient
 * Created: Nov 22, 2025
 */

let patientViewWindow = null;

function openPatientView() {
    // Collect current invoice data
    const invoiceData = collectInvoiceData();

    // Open pop-up window
    const width = 1000;
    const height = 800;
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;

    // Close existing window if open
    if (patientViewWindow && !patientViewWindow.closed) {
        patientViewWindow.close();
    }

    patientViewWindow = window.open(
        '/invoice/patient-view',
        'PatientInvoiceView',
        `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
    );

    // Send data to patient window once loaded
    if (patientViewWindow) {
        // Set interval to check if window is loaded
        const checkInterval = setInterval(function() {
            if (patientViewWindow && !patientViewWindow.closed) {
                try {
                    patientViewWindow.postMessage({
                        type: 'INVOICE_DATA',
                        invoice: invoiceData
                    }, '*');
                    clearInterval(checkInterval);
                } catch (e) {
                    // Window not ready yet, will try again
                }
            } else {
                clearInterval(checkInterval);
            }
        }, 100);

        // Clear interval after 5 seconds
        setTimeout(() => clearInterval(checkInterval), 5000);
    }

    return patientViewWindow;
}

function collectInvoiceData() {
    const lineItems = [];
    const rows = document.querySelectorAll('.line-item-row');

    rows.forEach((row, index) => {
        const itemType = row.querySelector('.item-type')?.value;
        const itemName = row.querySelector('.item-name')?.textContent ||
                         row.querySelector('.item-name')?.value ||
                         row.querySelector('[data-item-name]')?.dataset.itemName ||
                         'Unknown Item';
        const quantity = parseFloat(row.querySelector('.quantity')?.value) || 0;
        const unitPrice = parseFloat(row.querySelector('.unit-price')?.value) || 0;
        const discountPercent = parseFloat(row.querySelector('.discount-percent')?.value) || 0;
        const discountType = row.querySelector('.discount-type')?.value || 'none';
        const gstRate = parseFloat(row.querySelector('.gst-rate')?.value) || 0;

        if (quantity > 0 && itemName !== 'Unknown Item') {
            const subtotal = quantity * unitPrice;
            const discountAmount = (subtotal * discountPercent) / 100;
            const afterDiscount = subtotal - discountAmount;
            const gstAmount = (afterDiscount * gstRate) / 100;
            const lineTotal = afterDiscount + gstAmount;

            // Get service/medicine ID and metadata for discount breakdown
            const serviceId = row.querySelector('.item-id')?.value;
            const medicineId = row.querySelector('.item-id')?.value;
            const metadataInput = row.querySelector('.discount-metadata');
            const metadata = metadataInput?.value ? JSON.parse(metadataInput.value) : null;

            lineItems.push({
                serial: index + 1,
                itemType,
                itemName,
                quantity,
                unitPrice,
                subtotal,
                discountPercent,
                discountType,
                discountAmount,
                gstRate,
                gstAmount,
                lineTotal,
                serviceId,
                medicineId,
                discountMetadata: metadata
            });
        }
    });

    // Get totals
    const originalPrice = lineItems.reduce((sum, item) => sum + item.subtotal, 0);
    const totalDiscount = lineItems.reduce((sum, item) => sum + item.discountAmount, 0);
    const subtotalAfterDiscount = originalPrice - totalDiscount;
    const totalGST = lineItems.reduce((sum, item) => sum + item.gstAmount, 0);
    const grandTotal = subtotalAfterDiscount + totalGST;

    // Get discount breakdown by type
    const discountBreakdown = {};
    lineItems.forEach(item => {
        if (item.discountType && item.discountType !== 'none' && item.discountAmount > 0) {
            // Handle stacked discount with breakdown array (new format)
            if (item.discountType === 'stacked' && item.discountMetadata?.breakdown) {
                const metadata = item.discountMetadata;
                const breakdown = metadata.breakdown;

                // Calculate each component from breakdown
                breakdown.forEach(component => {
                    if (component.source && component.percent) {
                        const componentAmount = (item.unitPrice * item.quantity * component.percent) / 100;
                        discountBreakdown[component.source] = (discountBreakdown[component.source] || 0) + componentAmount;
                    }
                });
            }
            // Handle legacy bulk_plus_loyalty format
            else if (item.discountType === 'bulk_plus_loyalty' && item.discountMetadata) {
                const metadata = item.discountMetadata;

                if (metadata.bulk_percent && metadata.loyalty_percent) {
                    // Calculate each component
                    const bulkAmount = (item.unitPrice * item.quantity * metadata.bulk_percent) / 100;
                    const loyaltyAmount = (item.unitPrice * item.quantity * metadata.loyalty_percent) / 100;

                    discountBreakdown['bulk'] = (discountBreakdown['bulk'] || 0) + bulkAmount;
                    discountBreakdown['loyalty'] = (discountBreakdown['loyalty'] || 0) + loyaltyAmount;
                } else {
                    // Fallback: just use the total amount
                    discountBreakdown[item.discountType] =
                        (discountBreakdown[item.discountType] || 0) + item.discountAmount;
                }
            } else {
                discountBreakdown[item.discountType] =
                    (discountBreakdown[item.discountType] || 0) + item.discountAmount;
            }
        }
    });

    // Get promotions from discount metadata
    const promotions = [];
    const promotionMap = new Map();

    lineItems.forEach(item => {
        if (item.discountType === 'promotion' && item.discountMetadata) {
            const metadata = item.discountMetadata;
            const promotionId = metadata.campaign_id || 'promo-1';
            const campaignName = metadata.campaign_name || 'Promotion';
            const campaignCode = metadata.campaign_code || 'PROMO';
            const promotionType = metadata.promotion_type || 'simple_discount';

            if (!promotionMap.has(promotionId)) {
                promotionMap.set(promotionId, {
                    campaignName,
                    campaignCode,
                    promotionType,
                    savings: 0,
                    promotionRules: metadata.promotion_rules || {}
                });
            }

            const promo = promotionMap.get(promotionId);
            promo.savings += item.discountAmount;
        }
    });

    promotions.push(...promotionMap.values());

    // Get patient info
    const patientName = document.getElementById('patient_search')?.value ||
                       document.querySelector('[name="patient_id"] option:checked')?.text ||
                       'Not Selected';
    const patientMrn = document.getElementById('patient_mrn')?.value ||
                      document.querySelector('[data-patient-mrn]')?.dataset.patientMrn ||
                      '-';

    // Get invoice date
    const invoiceDateInput = document.getElementById('invoice_date')?.value ||
                            document.querySelector('[name="invoice_date"]')?.value;
    const invoiceDate = invoiceDateInput || new Date().toISOString().split('T')[0];

    // Check if patient has loyalty card
    const hasLoyaltyCard = document.getElementById('loyalty_card_id')?.value ? true : false;

    return {
        patient: {
            name: patientName,
            mrn: patientMrn,
            hasLoyaltyCard: hasLoyaltyCard
        },
        invoiceDate,
        invoiceNumber: 'DRAFT',
        lineItems,
        totals: {
            originalPrice,
            totalDiscount,
            subtotalAfterDiscount,
            totalGST,
            grandTotal
        },
        discountBreakdown,
        promotions,
        availablePromotions: [], // TODO: Fetch from API
        bulkDiscountConfig: {
            threshold: 5,
            discountPercent: 10
        }
    };
}

// Listen for messages from patient window
window.addEventListener('message', function(event) {
    if (event.data.type === 'REQUEST_INVOICE_DATA') {
        if (patientViewWindow && !patientViewWindow.closed) {
            const invoiceData = collectInvoiceData();
            patientViewWindow.postMessage({
                type: 'INVOICE_DATA',
                invoice: invoiceData
            }, '*');
        }
    }
});

// Auto-refresh patient view when invoice changes
function refreshPatientView() {
    if (patientViewWindow && !patientViewWindow.closed) {
        const invoiceData = collectInvoiceData();
        patientViewWindow.postMessage({
            type: 'INVOICE_DATA',
            invoice: invoiceData
        }, '*');
    }
}

// Export for global use
window.openPatientView = openPatientView;
window.refreshPatientView = refreshPatientView;
