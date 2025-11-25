# FRONTEND - MULTI-DISCOUNT UI AND PRINT FACILITY
**Date**: November 22, 2025
**Status**: Planning Phase
**Backend**: ✓ Complete (5/5 tests passing)

---

## OVERVIEW

Implement frontend UI and print templates to display the multi-discount system with:
- **4 Discount Types**: Standard, Bulk, Loyalty, Promotion
- **Discount Type Indicators**: Visual badges showing which discount was applied
- **Promotion Tracking**: Display campaigns_applied on invoices
- **Print/PDF Support**: Enhanced invoice print template with promotion details

---

## CURRENT STATE ANALYSIS

### Invoice Creation UI (`create_invoice.html`)

**Lines 776-891: Bulk Discount Panel**
- Existing "Pricing Consultation" panel
- Shows bulk discount toggle and pricing summary
- Currently shows only bulk discount information
- **Needs**: Expansion to show all 4 discount types

**Lines 1125-1140: Discount Column**
- Shows discount percent input field
- Has role-based editing (readonly for front desk)
- **Needs**: Discount type indicator badge

**Lines 936-953: Table Footer Totals**
- Shows Subtotal, Total Discount, CGST, SGST, IGST
- **Needs**: Discount breakdown by type

### Print Invoice Template (`print_invoice.html`)

**Lines 217-222, 291-298: Discount Display**
- Shows discount percent and amount: `10% (500.00)`
- No indication of discount TYPE
- **Needs**: Discount type badge/label

**Lines 360-423: Totals Section**
- Shows total discount amount (line 374-376)
- No breakdown by discount type
- **Needs**: Promotion campaign section

---

## IMPLEMENTATION PLAN

### Phase 1: Discount Type Indicators (Invoice Creation)

#### 1.1: Add Discount Type Badge to Line Items

**Location**: `create_invoice.html` line item template
**File**: `app/templates/billing/create_invoice.html`

**Current** (lines 1125-1140):
```html
<!-- Discount Percent -->
<td class="px-2 py-2">
    <input type="number"
           class="discount-percent form-input text-sm w-full text-right"
           value="0"
           min="0"
           max="100">
</td>
```

**Enhanced**:
```html
<!-- Discount Percent with Type Indicator -->
<td class="px-2 py-2">
    <div style="position: relative;">
        <input type="number"
               class="discount-percent form-input text-sm w-full text-right"
               value="0"
               min="0"
               max="100">

        <!-- Discount Type Badge (Hidden initially, shown when discount applied) -->
        <div class="discount-type-badge" style="display: none; margin-top: 2px;">
            <span class="badge badge-xs" style="font-size: 9px; padding: 2px 6px;">
                <!-- Will show: Standard / Bulk / Loyalty / Promotion -->
            </span>
        </div>

        <!-- Hidden field to store discount type -->
        <input type="hidden" class="discount-type" value="">
    </div>
</td>
```

**Badge Styles**:
```css
.badge-discount-standard {
    background-color: #e5e7eb;
    color: #374151;
}

.badge-discount-bulk {
    background-color: #dbeafe;
    color: #1e40af;
}

.badge-discount-loyalty {
    background-color: #fef3c7;
    color: #92400e;
}

.badge-discount-promotion {
    background-color: #dcfce7;
    color: #166534;
    font-weight: 700;
}
```

#### 1.2: Update Pricing Consultation Panel

**Location**: `create_invoice.html` lines 776-891
**Enhancement**: Show all discount types, not just bulk

**Current**: "Bulk Discount Consultation Panel"
**New**: "Multi-Discount Pricing Panel"

**Enhanced Panel Structure**:
```html
<div class="multi-discount-panel" id="discount-panel">
    <!-- Header -->
    <div class="panel-header">
        <h3>Pricing Consultation</h3>
        <p>Real-time discount calculation (4 types)</p>
    </div>

    <!-- Discount Type Indicators (4 Checkboxes - Display Only) -->
    <div class="discount-type-indicators">
        <div class="indicator-grid">
            <!-- Standard Discount -->
            <div class="discount-indicator">
                <input type="checkbox" id="has-standard-discount" disabled>
                <label>
                    <span class="badge badge-discount-standard">Standard</span>
                    <span class="discount-amount">Rs.0</span>
                </label>
            </div>

            <!-- Bulk Discount -->
            <div class="discount-indicator">
                <input type="checkbox" id="has-bulk-discount" disabled>
                <label>
                    <span class="badge badge-discount-bulk">Bulk</span>
                    <span class="discount-amount">Rs.0</span>
                </label>
            </div>

            <!-- Loyalty Discount -->
            <div class="discount-indicator">
                <input type="checkbox" id="has-loyalty-discount" disabled>
                <label>
                    <span class="badge badge-discount-loyalty">Loyalty</span>
                    <span class="discount-amount">Rs.0</span>
                </label>
            </div>

            <!-- Promotion Discount -->
            <div class="discount-indicator promotion-highlight">
                <input type="checkbox" id="has-promotion-discount" disabled>
                <label>
                    <span class="badge badge-discount-promotion">Promotion 🎁</span>
                    <span class="discount-amount">Rs.0</span>
                </label>
            </div>
        </div>
    </div>

    <!-- Promotion Details (shown when promotion active) -->
    <div id="promotion-details-panel" style="display: none;">
        <div class="promotion-banner">
            <strong>🎉 Promotion Applied:</strong>
            <span id="promotion-name"></span>
            <span id="promotion-code" class="badge badge-discount-promotion"></span>
        </div>
        <div class="promotion-description">
            <span id="promotion-message"></span>
        </div>
    </div>

    <!-- Pricing Summary -->
    <div class="pricing-summary">
        <table>
            <tr>
                <td>Original Price:</td>
                <td><span id="summary-original-price">Rs.0.00</span></td>
            </tr>
            <tr>
                <td>Total Discount:</td>
                <td><span id="summary-total-discount">- Rs.0.00</span></td>
            </tr>
            <tr>
                <td><strong>Patient Pays:</strong></td>
                <td><strong id="summary-final-price">Rs.0.00</strong></td>
            </tr>
        </table>
    </div>
</div>
```

---

### Phase 2: Print Template Enhancement

#### 2.1: Add Discount Type Column to Line Items

**Location**: `print_invoice.html` lines 179-237 (Services table)

**Current Discount Column** (lines 216-223):
```html
<th style="width: 10%;">Discount</th>
...
<td class="text-right">
    {% if item.discount_amount and item.discount_amount > 0 %}
        {{ item.discount_percent|int }}% ({{ "%.2f"|format(item.discount_amount) }})
    {% else %}
        -
    {% endif %}
</td>
```

**Enhanced with Discount Type**:
```html
<th style="width: 13%;">Discount (Type)</th>
...
<td class="text-right">
    {% if item.discount_amount and item.discount_amount > 0 %}
        <div>{{ item.discount_percent|int }}% ({{ "%.2f"|format(item.discount_amount) }})</div>
        {% if item.discount_type %}
        <div class="discount-type-label">
            {% if item.discount_type == 'promotion' %}
                <span class="badge-print badge-promotion">Promotion</span>
            {% elif item.discount_type == 'bulk' %}
                <span class="badge-print badge-bulk">Bulk</span>
            {% elif item.discount_type == 'loyalty' %}
                <span class="badge-print badge-loyalty">Loyalty</span>
            {% elif item.discount_type == 'standard' %}
                <span class="badge-print badge-standard">Standard</span>
            {% endif %}
        </div>
        {% endif %}
    {% else %}
        -
    {% endif %}
</td>
```

**Print Badge Styles** (add to `<style>` section):
```css
.badge-print {
    font-size: 8px;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
    text-transform: uppercase;
    margin-top: 2px;
    display: inline-block;
}

.badge-promotion {
    background-color: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
}

.badge-bulk {
    background-color: #dbeafe;
    color: #1e40af;
    border: 1px solid #93c5fd;
}

.badge-loyalty {
    background-color: #fef3c7;
    color: #92400e;
    border: 1px solid #fde68a;
}

.badge-standard {
    background-color: #f3f4f6;
    color: #374151;
    border: 1px solid #d1d5db;
}

@media print {
    .badge-print {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
}
```

#### 2.2: Add Promotion Campaign Section

**Location**: `print_invoice.html` after totals section (after line 423)

**New Section**:
```html
<!-- Promotion Campaigns Applied (if any) -->
{% if invoice.campaigns_applied and invoice.campaigns_applied.applied_promotions %}
<div class="promotions-section" style="margin-top: 20px; padding: 15px; background-color: #f0fdf4; border: 2px solid #86efac; border-radius: 8px;">
    <div style="font-weight: bold; margin-bottom: 10px; color: #166534;">
        🎁 Promotions Applied to This Invoice:
    </div>

    {% for promotion in invoice.campaigns_applied.applied_promotions %}
    <div class="promotion-item" style="margin-bottom: 10px; padding: 8px; background-color: white; border-left: 4px solid #22c55e;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>{{ promotion.campaign_name }}</strong>
                <span class="badge-print badge-promotion" style="margin-left: 8px;">
                    {{ promotion.campaign_code }}
                </span>
            </div>
            <div style="color: #166534; font-weight: 600;">
                Saved: Rs.{{ "%.2f"|format(promotion.total_discount) }}
            </div>
        </div>

        <div style="font-size: 9px; color: #666; margin-top: 5px;">
            Type: {{ promotion.promotion_type.replace('_', ' ').title() }}
            {% if promotion.items_affected %}
                | Items: {{ promotion.items_affected|length }}
            {% endif %}
        </div>
    </div>
    {% endfor %}

    <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #86efac; text-align: right;">
        <strong>Total Promotion Savings: Rs.{{ "%.2f"|format(invoice.campaigns_applied.applied_promotions|sum(attribute='total_discount')) }}</strong>
    </div>
</div>
{% endif %}
```

#### 2.3: Add Discount Breakdown in Totals Section

**Location**: `print_invoice.html` lines 360-423

**Enhancement**: After "Total Discount" line (after line 376)

```html
{% if invoice.total_discount > 0 %}
<tr>
    <td style="text-align: right; padding: 5px; width: 70%;">Total Discount:</td>
    <td style="text-align: right; padding: 5px; width: 30%;">{{ "%.2f"|format(invoice.total_discount) }}</td>
</tr>

<!-- NEW: Discount Breakdown by Type -->
{% if invoice.discount_breakdown %}
<tr>
    <td colspan="2" style="padding: 0 5px;">
        <div style="font-size: 9px; color: #666; text-align: right;">
            {% if invoice.discount_breakdown.standard > 0 %}
                Standard: Rs.{{ "%.2f"|format(invoice.discount_breakdown.standard) }}
            {% endif %}
            {% if invoice.discount_breakdown.bulk > 0 %}
                {% if invoice.discount_breakdown.standard > 0 %} | {% endif %}
                Bulk: Rs.{{ "%.2f"|format(invoice.discount_breakdown.bulk) }}
            {% endif %}
            {% if invoice.discount_breakdown.loyalty > 0 %}
                {% if invoice.discount_breakdown.standard > 0 or invoice.discount_breakdown.bulk > 0 %} | {% endif %}
                Loyalty: Rs.{{ "%.2f"|format(invoice.discount_breakdown.loyalty) }}
            {% endif %}
            {% if invoice.discount_breakdown.promotion > 0 %}
                {% if invoice.discount_breakdown.standard > 0 or invoice.discount_breakdown.bulk > 0 or invoice.discount_breakdown.loyalty > 0 %} | {% endif %}
                Promotion: Rs.{{ "%.2f"|format(invoice.discount_breakdown.promotion) }}
            {% endif %}
        </div>
    </td>
</tr>
{% endif %}
{% endif %}
```

---

### Phase 3: Backend Support for Frontend

#### 3.1: Add discount_breakdown to Invoice Model

**File**: `app/models/transaction.py`
**Location**: InvoiceHeader class

**Add property method**:
```python
@property
def discount_breakdown(self):
    """Calculate discount breakdown by type from line items"""
    breakdown = {
        'standard': Decimal('0'),
        'bulk': Decimal('0'),
        'loyalty': Decimal('0'),
        'promotion': Decimal('0')
    }

    for item in self.line_items:
        discount_type = item.discount_type or 'standard'
        discount_amount = item.discount_amount or Decimal('0')

        if discount_type in breakdown:
            breakdown[discount_type] += discount_amount

    return breakdown
```

#### 3.2: Pass discount_type to Frontend in Line Items

**File**: `app/views/billing_views.py`
**Function**: `create_invoice_view()` (after discount application)

**Enhancement**: Ensure `discount_type` is in the response

Current code already includes this from `apply_discounts_to_invoice_items_multi()` which returns:
```python
{
    'item_id': '...',
    'discount_type': 'promotion',  # ← Already included
    'discount_percent': 100,
    'discount_amount': 500.00,
    # ...
}
```

**Verify in template rendering** that line items include `discount_type`.

---

### Phase 4: JavaScript Enhancements

#### 4.1: Real-Time Discount Type Display

**File**: `app/static/js/components/invoice_item.js`
**Function**: `calculateLineTotal()` or create new `updateDiscountTypeDisplay()`

**New Function**:
```javascript
updateDiscountTypeDisplay(row) {
    const discountPercent = parseFloat(row.querySelector('.discount-percent').value) || 0;
    const discountTypeInput = row.querySelector('.discount-type');
    const discountBadge = row.querySelector('.discount-type-badge');
    const badge = discountBadge.querySelector('.badge');

    if (discountPercent > 0 && discountTypeInput && discountTypeInput.value) {
        const discountType = discountTypeInput.value;

        // Show badge
        discountBadge.style.display = 'block';

        // Set badge text and class
        badge.textContent = discountType.charAt(0).toUpperCase() + discountType.slice(1);
        badge.className = 'badge badge-xs badge-discount-' + discountType;
    } else {
        // Hide badge if no discount
        discountBadge.style.display = 'none';
    }
}
```

**Call from**: `calculateLineTotal()` after discount calculation

#### 4.2: Multi-Discount Panel Update

**File**: `app/static/js/components/invoice_bulk_discount.js`
**Enhancement**: Update to show all 4 discount types

**New Function**: `updateDiscountBreakdown()`
```javascript
function updateDiscountBreakdown() {
    const lineItems = document.querySelectorAll('.line-item-row');

    let breakdown = {
        standard: 0,
        bulk: 0,
        loyalty: 0,
        promotion: 0
    };

    lineItems.forEach(row => {
        const discountType = row.querySelector('.discount-type')?.value;
        const discountAmount = parseFloat(row.querySelector('.discount-amount')?.value) || 0;

        if (discountType && breakdown.hasOwnProperty(discountType)) {
            breakdown[discountType] += discountAmount;
        }
    });

    // Update UI
    updateDiscountIndicator('standard', breakdown.standard);
    updateDiscountIndicator('bulk', breakdown.bulk);
    updateDiscountIndicator('loyalty', breakdown.loyalty);
    updateDiscountIndicator('promotion', breakdown.promotion);

    // Show promotion details if any
    if (breakdown.promotion > 0) {
        showPromotionBanner();
    } else {
        hidePromotionBanner();
    }
}

function updateDiscountIndicator(type, amount) {
    const checkbox = document.getElementById(`has-${type}-discount`);
    const amountSpan = checkbox?.closest('.discount-indicator')
                              ?.querySelector('.discount-amount');

    if (amount > 0) {
        checkbox.checked = true;
        amountSpan.textContent = `Rs.${amount.toFixed(2)}`;
    } else {
        checkbox.checked = false;
        amountSpan.textContent = 'Rs.0';
    }
}

function showPromotionBanner() {
    const promotionPanel = document.getElementById('promotion-details-panel');

    // TODO: Fetch promotion details from invoice data
    // For now, show generic message
    document.getElementById('promotion-name').textContent = 'Buy X Get Y Promotion';
    document.getElementById('promotion-code').textContent = 'PREMIUM_CONSULT';
    document.getElementById('promotion-message').textContent =
        'Free consultation applied automatically!';

    promotionPanel.style.display = 'block';
}
```

---

## FILE CHANGES SUMMARY

### Files to Modify

1. **`app/templates/billing/create_invoice.html`**
   - Add discount type badge to line item template (lines 1125-1140)
   - Replace bulk discount panel with multi-discount panel (lines 776-891)
   - Add discount type indicators (4 checkboxes)
   - Add promotion banner

2. **`app/templates/billing/print_invoice.html`**
   - Add discount type column/label to services table (lines 179-237)
   - Add discount type column/label to medicines table (lines 239-312)
   - Add promotion campaign section (after line 423)
   - Add discount breakdown to totals (after line 376)

3. **`app/static/js/components/invoice_item.js`**
   - Add `updateDiscountTypeDisplay()` function
   - Call from `calculateLineTotal()`
   - Handle discount_type field

4. **`app/static/js/components/invoice_bulk_discount.js`**
   - Rename to `invoice_multi_discount.js`
   - Add `updateDiscountBreakdown()` function
   - Add `showPromotionBanner()` function
   - Update existing bulk discount logic

5. **`app/models/transaction.py`**
   - Add `discount_breakdown` property to InvoiceHeader
   - Calculate breakdown from line items

6. **`app/views/billing_views.py`**
   - Verify `discount_type` is passed to template
   - Verify `campaigns_applied` is passed for print view

---

## CSS ADDITIONS

**File**: Create new CSS or add to existing
**Location**: `app/static/css/components/multi_discount.css` (new file)

```css
/* ================================================================
   MULTI-DISCOUNT UI STYLES
   Nov 22, 2025
   ================================================================ */

/* Discount Type Badges */
.badge-discount-standard {
    background-color: #e5e7eb;
    color: #374151;
    border: 1px solid #d1d5db;
}

.badge-discount-bulk {
    background-color: #dbeafe;
    color: #1e40af;
    border: 1px solid #93c5fd;
}

.badge-discount-loyalty {
    background-color: #fef3c7;
    color: #92400e;
    border: 1px solid #fde68a;
}

.badge-discount-promotion {
    background-color: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
    font-weight: 700;
}

/* Multi-Discount Panel */
.multi-discount-panel {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin-bottom: 24px;
}

.discount-type-indicators {
    padding: 16px;
    background: #f8fafc;
    border-top: 1px solid #e5e7eb;
}

.indicator-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
}

.discount-indicator {
    display: flex;
    align-items: center;
    padding: 12px;
    background: white;
    border-radius: 6px;
    border: 2px solid #e5e7eb;
}

.discount-indicator input[type="checkbox"] {
    margin-right: 8px;
    width: 18px;
    height: 18px;
}

.discount-indicator.promotion-highlight {
    border-color: #86efac;
    background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
}

.promotion-banner {
    padding: 12px;
    background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
    border-radius: 6px;
    margin: 12px;
    font-size: 14px;
    color: #166534;
}

.promotion-description {
    padding: 0 12px 12px 12px;
    font-size: 13px;
    color: #065f46;
    font-style: italic;
}

/* Print-specific styles */
@media print {
    .badge-print {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    .promotions-section {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        page-break-inside: avoid;
    }
}
```

---

## TESTING CHECKLIST

### Invoice Creation UI
- [ ] Discount type badges appear when discount is applied
- [ ] Badge shows correct type (Standard/Bulk/Loyalty/Promotion)
- [ ] Multi-discount panel shows all 4 discount types
- [ ] Checkboxes checked when discount type is active
- [ ] Promotion banner appears when promotion applied
- [ ] Promotion shows campaign name and code
- [ ] Real-time updates when adding/removing items

### Print Invoice
- [ ] Discount column shows discount type badge
- [ ] Promotion campaign section appears when promotions applied
- [ ] Campaign details show correctly (name, code, type, savings)
- [ ] Discount breakdown shows in totals
- [ ] Print badges render with colors (print-color-adjust)
- [ ] PDF generation includes all promotion details

### Backend
- [ ] `discount_type` field populated on line items
- [ ] `campaigns_applied` JSONB populated on invoice
- [ ] `discount_breakdown` property calculates correctly
- [ ] All 4 discount types tracked independently

---

## NEXT STEPS

1. **Implement Phase 1**: Discount type indicators on invoice creation
2. **Implement Phase 2**: Print template enhancements
3. **Implement Phase 3**: Backend support methods
4. **Implement Phase 4**: JavaScript real-time updates
5. **Testing**: Comprehensive frontend testing
6. **Documentation**: User guide for multi-discount features

---

**Status**: Ready for Implementation
**Backend**: ✓ Complete
**Frontend**: In Progress
**Estimated Time**: 4-6 hours
