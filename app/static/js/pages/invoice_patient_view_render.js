/**
 * Patient View Renderer
 * Populates patient-facing invoice preview
 * Created: Nov 22, 2025
 */

function loadInvoiceData(data) {
    console.log('Loading invoice data:', data);

    // Populate patient info
    document.getElementById('patient-name').textContent = data.patient.name || 'Not Selected';
    document.getElementById('patient-mrn').textContent = data.patient.mrn || '-';
    document.getElementById('invoice-date').textContent = formatDate(data.invoiceDate);
    document.getElementById('invoice-number').textContent = data.invoiceNumber || 'DRAFT';

    // Populate line items
    const lineItemsBody = document.getElementById('line-items-body');
    lineItemsBody.innerHTML = '';

    if (data.lineItems && data.lineItems.length > 0) {
        data.lineItems.forEach(item => {
            const row = document.createElement('tr');

            let itemDetails = `<div class="item-name">${escapeHtml(item.itemName)}</div>`;

            if (item.discountType === 'promotion' && item.discountAmount > 0) {
                itemDetails += `
                    <div class="discount-indicator">
                        🎁 PROMOTION APPLIED
                    </div>
                    <div style="font-size: 13px; color: #166534; margin-top: 4px;">
                        Free with Premium Service
                    </div>
                `;
            } else if (item.discountAmount > 0) {
                const discountTypeName = item.discountType.charAt(0).toUpperCase() + item.discountType.slice(1);
                itemDetails += `
                    <div style="font-size: 13px; color: #dc2626; margin-top: 4px;">
                        ${item.discountPercent}% ${discountTypeName} Discount
                    </div>
                `;
            }

            let amountDisplay = formatCurrency(item.subtotal);
            if (item.discountAmount > 0) {
                amountDisplay = `
                    <div>${formatCurrency(item.subtotal)}</div>
                    <div class="discount-amount" style="margin-top: 4px;">
                        - ${formatCurrency(item.discountAmount)}
                    </div>
                    <div style="border-top: 1px solid #e5e7eb; margin-top: 4px; padding-top: 4px; font-weight: 600;">
                        ${formatCurrency(item.lineTotal)}
                    </div>
                `;
            }

            row.innerHTML = `
                <td style="text-align: center;">${item.serial}</td>
                <td>${itemDetails}</td>
                <td style="text-align: center;">${item.quantity}</td>
                <td style="text-align: right;">${formatCurrency(item.unitPrice)}</td>
                <td style="text-align: right;">${amountDisplay}</td>
            `;

            lineItemsBody.appendChild(row);
        });
    } else {
        lineItemsBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center" style="padding: 40px; color: #6b7280;">
                    No items added yet
                </td>
            </tr>
        `;
    }

    // Populate pricing summary
    document.getElementById('original-price').textContent = formatCurrency(data.totals.originalPrice);
    document.getElementById('total-discount').textContent = `- ${formatCurrency(data.totals.totalDiscount)}`;
    document.getElementById('subtotal-after-discount').textContent = formatCurrency(data.totals.subtotalAfterDiscount);
    document.getElementById('gst-amount').textContent = formatCurrency(data.totals.totalGST);
    document.getElementById('grand-total').textContent = formatCurrency(data.totals.grandTotal);

    // Populate discount breakdown
    if (data.discountBreakdown && Object.keys(data.discountBreakdown).length > 0) {
        const discountBreakdownDiv = document.getElementById('discount-breakdown');
        discountBreakdownDiv.innerHTML = '<div style="padding: 12px 0; border-bottom: 1px solid #e5e7eb;"><strong>DISCOUNTS APPLIED:</strong></div>';

        const badgeColors = {
            'standard': '#f3f4f6',
            'bulk': '#dbeafe',
            'loyalty': '#fef3c7',
            'promotion': '#dcfce7'
        };

        const textColors = {
            'standard': '#374151',
            'bulk': '#1e40af',
            'loyalty': '#92400e',
            'promotion': '#166534'
        };

        for (const [type, amount] of Object.entries(data.discountBreakdown)) {
            if (amount > 0) {
                const label = type.charAt(0).toUpperCase() + type.slice(1);
                const bgColor = badgeColors[type] || '#e5e7eb';
                const textColor = textColors[type] || '#374151';

                discountBreakdownDiv.innerHTML += `
                    <div class="pricing-row indent">
                        <span>
                            <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 8px; background-color: ${bgColor}; color: ${textColor}; font-weight: 600;">${label}</span>
                        </span>
                        <span class="discount-amount">- ${formatCurrency(amount)}</span>
                    </div>
                `;
            }
        }
    }

    // Populate promotions with detailed information
    if (data.promotions && data.promotions.length > 0) {
        const promotionsSection = document.getElementById('promotions-section');
        promotionsSection.style.display = 'block';
        promotionsSection.className = 'promotions-section';
        promotionsSection.innerHTML = `
            <div class="section-title" style="color: #166534; margin-bottom: 16px;">
                🎁 ACTIVE PROMOTION${data.promotions.length > 1 ? 'S' : ''}
            </div>
        `;

        data.promotions.forEach((promo, index) => {
            // Get promotion description based on type
            let offerDescription = promo.offerDescription || 'Special promotional offer';

            if (promo.promotionType === 'buy_x_get_y' && promo.promotionRules) {
                const minAmount = promo.promotionRules.trigger?.conditions?.min_amount || 3000;
                offerDescription = `Buy service worth Rs.${minAmount}+, get consultation free`;
            }

            promotionsSection.innerHTML += `
                <div class="promotion-item" style="${index === 0 ? 'border: 3px solid #22c55e;' : ''}">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                        <div>
                            <span class="promotion-name">✓ ${escapeHtml(promo.campaignName)}</span>
                            <span class="promotion-code">${escapeHtml(promo.campaignCode)}</span>
                        </div>
                        <span class="promotion-savings">
                            <i class="fas fa-check-circle" style="margin-right: 4px;"></i>
                            Saved: ${formatCurrency(promo.savings)}
                        </span>
                    </div>
                    <div class="promotion-details" style="margin-top: 8px;">
                        <strong>Offer:</strong> ${escapeHtml(offerDescription)}
                    </div>
                    <div class="promotion-details" style="margin-top: 4px; font-size: 12px; opacity: 0.8;">
                        Type: ${promo.promotionType.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </div>
                </div>
            `;
        });

        // Add total promotion savings if multiple promotions
        if (data.promotions.length > 1) {
            const totalPromotionSavings = data.promotions.reduce((sum, p) => sum + p.savings, 0);
            promotionsSection.innerHTML += `
                <div style="margin-top: 16px; padding-top: 16px; border-top: 2px solid #86efac; text-align: right;">
                    <strong style="font-size: 18px; color: #166534;">
                        Total Promotion Savings: ${formatCurrency(totalPromotionSavings)}
                    </strong>
                </div>
            `;
        }
    }

    // Generate savings tips
    generateSavingsTips(data);

    // Amount in words
    const grandTotal = data.totals?.grandTotal || 0;
    const amountWords = numberToWords(grandTotal);
    const amountWordsEl = document.getElementById('amount-words-text');
    if (amountWordsEl) {
        amountWordsEl.textContent = amountWords;
    }
}

function generateSavingsTips(data) {
    const tipsContainer = document.getElementById('savings-tips-container');
    tipsContainer.innerHTML = '';

    const tips = [];

    // Tip 1: Bulk Discount Opportunity
    // Count TOTAL QUANTITY of services, not just number of line items
    const serviceCount = data.lineItems
        .filter(item => item.itemType === 'Service')
        .reduce((sum, item) => sum + (item.quantity || 1), 0);
    const bulkThreshold = data.bulkDiscountConfig?.threshold || 5;
    const bulkDiscountPercent = data.bulkDiscountConfig?.discountPercent || 10;

    if (serviceCount > 0 && serviceCount < bulkThreshold) {
        const servicesNeeded = bulkThreshold - serviceCount;
        const currentServiceTotal = data.lineItems
            .filter(item => item.itemType === 'Service')
            .reduce((sum, item) => sum + item.subtotal, 0);
        const potentialSavings = (currentServiceTotal * bulkDiscountPercent) / 100;

        tips.push({
            icon: '🎯',
            title: `Add ${servicesNeeded} more service${servicesNeeded > 1 ? 's' : ''} to unlock BULK DISCOUNT`,
            description: `Get ${bulkDiscountPercent}% off on all services when you book ${bulkThreshold} or more`,
            amount: `Potential savings: ${formatCurrency(potentialSavings)}`
        });
    }

    // Tip 2: Loyalty Membership
    if (!data.patient.hasLoyaltyCard) {
        const annualServiceSpend = 50000; // Estimated
        const loyaltyDiscountPercent = 5; // 5% for Gold membership
        const membershipFee = 2000;
        const estimatedSavings = (annualServiceSpend * loyaltyDiscountPercent) / 100;

        tips.push({
            icon: '⭐',
            title: 'Join our GOLD MEMBERSHIP for year-round savings',
            description: `Get ${loyaltyDiscountPercent}% off on all services and exclusive benefits`,
            amount: `Annual fee: ${formatCurrency(membershipFee)} | Estimated yearly savings: ${formatCurrency(estimatedSavings)}+`
        });
    }

    // Tip 3: Other Available Promotions
    if (data.availablePromotions && data.availablePromotions.length > 0) {
        const promotionsList = data.availablePromotions.map(p =>
            `• ${escapeHtml(p.name)} - ${escapeHtml(p.description)}`
        ).join('<br>');

        tips.push({
            icon: '🎁',
            title: 'Other promotions you can combine',
            description: promotionsList,
            amount: ''
        });
    }
    // Removed hardcoded generic tips - only show actual promotions from database

    // Tip 4: Combo Packages (if applicable)
    const hasMultipleServices = data.lineItems.filter(item => item.itemType === 'Service').length > 1;
    if (hasMultipleServices) {
        tips.push({
            icon: '📦',
            title: 'Ask about our COMBO PACKAGES',
            description: 'Pre-designed treatment packages with bundled savings',
            amount: 'Save 15-20% compared to individual services'
        });
    }

    // Render tips
    if (tips.length > 0) {
        tips.forEach(tip => {
            const tipElement = document.createElement('div');
            tipElement.className = 'savings-tip';
            tipElement.innerHTML = `
                <div class="savings-tip-icon">${tip.icon}</div>
                <div class="savings-tip-content">
                    <div class="savings-tip-title">${escapeHtml(tip.title)}</div>
                    <div class="savings-tip-description">${tip.description}</div>
                    ${tip.amount ? `<div class="savings-tip-amount">${escapeHtml(tip.amount)}</div>` : ''}
                </div>
            `;
            tipsContainer.appendChild(tipElement);
        });
    } else {
        tipsContainer.innerHTML = `
            <div class="text-center" style="padding: 20px; color: #92400e;">
                <i class="fas fa-check-circle" style="font-size: 32px;"></i>
                <div style="margin-top: 8px;">You're getting the best available discounts!</div>
            </div>
        `;
    }
}

function formatCurrency(amount) {
    const num = parseFloat(amount) || 0;
    return `Rs. ${num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { day: '2-digit', month: 'short', year: 'numeric' };
    return date.toLocaleDateString('en-IN', options);
}

function numberToWords(num) {
    const amount = Math.round(num);

    if (amount === 0) return 'Zero';

    const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine'];
    const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
    const teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];

    function convertLessThan1000(n) {
        if (n === 0) return '';

        let result = '';

        if (n >= 100) {
            result += ones[Math.floor(n / 100)] + ' Hundred ';
            n %= 100;
        }

        if (n >= 20) {
            result += tens[Math.floor(n / 10)] + ' ';
            n %= 10;
        } else if (n >= 10) {
            result += teens[n - 10] + ' ';
            return result;
        }

        if (n > 0) {
            result += ones[n] + ' ';
        }

        return result;
    }

    let result = '';

    if (amount >= 10000000) { // Crores
        result += convertLessThan1000(Math.floor(amount / 10000000)) + 'Crore ';
        amount %= 10000000;
    }

    if (amount >= 100000) { // Lakhs
        result += convertLessThan1000(Math.floor(amount / 100000)) + 'Lakh ';
        amount %= 100000;
    }

    if (amount >= 1000) { // Thousands
        result += convertLessThan1000(Math.floor(amount / 1000)) + 'Thousand ';
        amount %= 1000;
    }

    if (amount > 0) {
        result += convertLessThan1000(amount);
    }

    return 'Rupees ' + result.trim() + ' Only';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Listen for messages from parent window
window.addEventListener('message', function(event) {
    if (event.data.type === 'INVOICE_DATA') {
        loadInvoiceData(event.data.invoice);
    }
});

// Request data on load
window.addEventListener('load', function() {
    if (window.opener) {
        window.opener.postMessage({ type: 'REQUEST_INVOICE_DATA' }, '*');
    }
});
