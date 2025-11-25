# Real-Time Bulk Discount UI - Implementation Guide
**Option A: Services with 0% bulk discount are EXCLUDED from threshold count**

---

## Overview

This guide provides the HTML, CSS, and JavaScript snippets to add real-time bulk discount pricing consultation to the patient invoice creation page.

**Key Features:**
- ✅ Real-time pricing updates as services are added/removed
- ✅ Clear indication of bulk discount eligibility
- ✅ Transparent pricing for patient discussions
- ✅ Automatic discount application when eligible
- ✅ Excludes ineligible services (bulk_discount_percent = 0) from count
- ✅ Manual override with validation

---

## Implementation Steps

### Step 1: Add HTML to `create_invoice.html`

**Location:** Insert after patient selection, before line items table

```html
<!-- ================================================== -->
<!-- BULK DISCOUNT CONSULTATION PANEL -->
<!-- ================================================== -->
<div class="bulk-discount-consultation-panel" id="bulk-discount-panel" style="margin-bottom: 24px;">

    <!-- Header Section -->
    <div class="panel-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px; border-radius: 8px 8px 0 0;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 24px;">🎁</span>
                <div>
                    <h3 style="margin: 0; font-size: 18px; font-weight: 600;">Pricing Consultation</h3>
                    <p style="margin: 4px 0 0 0; font-size: 13px; opacity: 0.9;">Live pricing with bulk discount calculator</p>
                </div>
            </div>

            <!-- Patient Loyalty Card Display -->
            <div id="patient-loyalty-card-display" style="display: none;"></div>
        </div>
    </div>

    <!-- Control Section -->
    <div class="panel-controls" style="background: #f8fafc; padding: 16px; border-left: 3px solid #667eea; border-right: 3px solid #667eea;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;">

            <!-- Bulk Discount Toggle -->
            <div style="flex: 1; min-width: 300px;">
                <label class="bulk-discount-toggle" style="display: flex; align-items: center; cursor: pointer; user-select: none;">
                    <input
                        type="checkbox"
                        id="bulk-discount-enabled"
                        class="form-checkbox"
                        style="width: 20px; height: 20px; margin-right: 12px; cursor: pointer;"
                    >
                    <span style="font-size: 15px; font-weight: 500; color: #1f2937;">
                        Apply Bulk Service Discount
                    </span>

                    <!-- Eligibility Badge -->
                    <span
                        id="bulk-discount-badge"
                        class="badge"
                        style="margin-left: 12px; display: none; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;"
                    ></span>
                </label>
            </div>

            <!-- Service Count Info -->
            <div id="bulk-discount-info" style="display: none; text-align: right;">
                <div style="font-size: 14px; color: #6b7280; line-height: 1.6;">
                    <div>
                        <strong id="service-count-display" style="color: #1f2937; font-size: 16px;">0 services</strong>
                    </div>
                    <div style="font-size: 12px;">
                        <span id="threshold-display">Need 5 for bulk discount</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Discount Breakdown (shown when checked) -->
        <div id="bulk-discount-breakdown" class="discount-breakdown" style="display: none; margin-top: 12px; padding: 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
            <div style="font-size: 13px; color: #4b5563;">
                <strong style="color: #1f2937;">Active Discounts:</strong>
                <span id="discount-breakdown-text"></span>
            </div>
        </div>

        <!-- Ineligible Services Info -->
        <div id="ineligible-services-info" class="info-message" style="display: none; margin-top: 12px;"></div>
    </div>

    <!-- Pricing Summary Section -->
    <div class="pricing-summary" style="background: white; padding: 20px; border-left: 3px solid #667eea; border-right: 3px solid #667eea; border-bottom: 3px solid #667eea; border-radius: 0 0 8px 8px;">
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: center;">

            <!-- Left: Pricing Breakdown -->
            <div class="price-details">
                <table style="width: 100%; font-size: 14px;">
                    <tr>
                        <td style="padding: 6px 0; color: #6b7280;">Original Price:</td>
                        <td style="padding: 6px 0; text-align: right; font-weight: 500;">
                            <span id="summary-original-price">₹0.00</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #ef4444;">Discount:</td>
                        <td style="padding: 6px 0; text-align: right; font-weight: 500; color: #ef4444;">
                            <span id="summary-discount">- ₹0.00</span>
                        </td>
                    </tr>
                    <tr style="border-top: 2px solid #e5e7eb;">
                        <td style="padding: 12px 0 6px 0; font-size: 16px; font-weight: 600; color: #1f2937;">
                            Patient Pays:
                        </td>
                        <td style="padding: 12px 0 6px 0; text-align: right;">
                            <div id="summary-final-price" style="font-size: 24px; font-weight: 700; color: #10b981;">
                                ₹0.00
                            </div>
                        </td>
                    </tr>
                </table>

                <!-- Savings Badge -->
                <div id="savings-badge" class="savings-badge" style="display: none; margin-top: 12px; padding: 8px 16px; background: #d1fae5; color: #065f46; border-radius: 6px; text-align: center; font-weight: 600;">
                    You save ₹0!
                </div>
            </div>

            <!-- Right: Potential Savings -->
            <div id="potential-savings-panel" class="potential-savings" style="display: none; min-width: 300px; max-width: 400px; padding: 16px; background: #fef3c7; border: 2px solid #fbbf24; border-radius: 8px;">
                <!-- Content dynamically inserted by JS -->
            </div>
        </div>
    </div>
</div>

<!-- Hidden inputs for IDs -->
<input type="hidden" name="hospital_id" id="hospital_id" value="{{ hospital_id }}">
<input type="hidden" name="patient_id" id="patient_id" value="{{ patient_id }}">

<!-- ================================================== -->
<!-- END BULK DISCOUNT CONSULTATION PANEL -->
<!-- ================================================== -->
```

---

### Step 2: Add CSS Styles

**Location:** Add to `app/static/css/components/` or inline in template `<style>` tag

**File:** `app/static/css/components/bulk_discount.css`

```css
/**
 * Bulk Discount Consultation Panel Styles
 * Real-time pricing for patient discussions
 */

/* ========================================
   Panel Container
   ======================================== */
.bulk-discount-consultation-panel {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.3s ease;
}

.bulk-discount-consultation-panel:hover {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

/* ========================================
   Badges
   ======================================== */
.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    transition: all 0.2s ease;
}

.badge-success {
    background: #d1fae5;
    color: #065f46;
    border: 1px solid #6ee7b7;
}

.badge-warning {
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #fbbf24;
}

.badge-info {
    background: #dbeafe;
    color: #1e40af;
    border: 1px solid #93c5fd;
}

/* ========================================
   Discount Type Badges (on line items)
   ======================================== */
.discount-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    margin-left: 8px;
    color: white;
    transition: transform 0.2s ease;
}

.discount-badge:hover {
    transform: scale(1.05);
}

.bulk-discount {
    background: #3b82f6;
    box-shadow: 0 1px 2px rgba(59, 130, 246, 0.3);
}

.loyalty-discount {
    background: #f59e0b;
    box-shadow: 0 1px 2px rgba(245, 158, 11, 0.3);
}

.campaign-discount {
    background: #10b981;
    box-shadow: 0 1px 2px rgba(16, 185, 129, 0.3);
}

/* ========================================
   Loyalty Card Badge
   ======================================== */
.loyalty-card-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: white;
    font-size: 13px;
    font-weight: 500;
}

.loyalty-card-badge .card-icon {
    font-size: 18px;
}

.loyalty-card-badge .card-discount {
    padding: 2px 8px;
    background: rgba(255, 255, 255, 0.3);
    border-radius: 8px;
    font-weight: 600;
}

/* ========================================
   Pricing Summary
   ======================================== */
.pricing-summary {
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.price-details tr {
    transition: background 0.2s ease;
}

.price-details tr:hover {
    background: #f9fafb;
}

/* ========================================
   Savings Badge
   ======================================== */
.savings-badge {
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.9;
        transform: scale(1.02);
    }
}

/* ========================================
   Potential Savings Panel
   ======================================== */
.potential-savings {
    animation: slideInRight 0.4s ease;
}

@keyframes slideInRight {
    from {
        opacity: 0;
        transform: translateX(20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.potential-savings-content {
    display: flex;
    align-items: flex-start;
    gap: 12px;
}

.potential-savings-content .icon {
    font-size: 32px;
    line-height: 1;
}

.potential-savings-content .message {
    flex: 1;
    font-size: 13px;
    line-height: 1.6;
    color: #78350f;
}

.potential-savings-content .details {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #fbbf24;
    font-size: 12px;
}

.potential-savings-content strong {
    color: #92400e;
    font-weight: 700;
}

/* ========================================
   Info Messages
   ======================================== */
.info-message {
    padding: 12px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    font-size: 13px;
    color: #1e40af;
    line-height: 1.6;
}

.info-message strong {
    font-weight: 600;
    color: #1e3a8a;
}

/* ========================================
   Discount Breakdown
   ======================================== */
.discount-breakdown {
    animation: expandDown 0.3s ease;
}

@keyframes expandDown {
    from {
        max-height: 0;
        opacity: 0;
    }
    to {
        max-height: 100px;
        opacity: 1;
    }
}

.discount-item {
    display: inline-block;
    padding: 4px 8px;
    margin-right: 8px;
    background: #f3f4f6;
    border-radius: 4px;
    font-size: 12px;
}

/* ========================================
   Checkbox Styling
   ======================================== */
.bulk-discount-toggle input[type="checkbox"] {
    appearance: none;
    width: 20px;
    height: 20px;
    border: 2px solid #d1d5db;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    position: relative;
    transition: all 0.2s ease;
}

.bulk-discount-toggle input[type="checkbox"]:hover {
    border-color: #667eea;
}

.bulk-discount-toggle input[type="checkbox"]:checked {
    background: #667eea;
    border-color: #667eea;
}

.bulk-discount-toggle input[type="checkbox"]:checked::after {
    content: '✓';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    font-size: 14px;
    font-weight: bold;
}

.bulk-discount-toggle input[type="checkbox"]:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* ========================================
   Responsive Design
   ======================================== */
@media (max-width: 768px) {
    .bulk-discount-consultation-panel {
        margin-left: -16px;
        margin-right: -16px;
        border-radius: 0;
    }

    .pricing-summary > div {
        grid-template-columns: 1fr;
    }

    #potential-savings-panel {
        min-width: unset;
        max-width: 100%;
    }

    .panel-header > div {
        flex-direction: column;
        gap: 12px;
    }
}

/* ========================================
   Print Styles (hide in print)
   ======================================== */
@media print {
    .bulk-discount-consultation-panel {
        display: none;
    }
}
```

---

### Step 3: Load JavaScript

**Location:** Add before closing `</body>` tag in `create_invoice.html`

```html
<!-- Bulk Discount Real-Time Pricing -->
<script src="{{ url_for('static', filename='js/components/invoice_bulk_discount.js') }}"></script>

<!-- Initialize on page load -->
<script>
    // Configuration is auto-loaded from data attributes and API
    console.log('Bulk discount module loaded');
</script>
```

---

### Step 4: Integration Points

#### A. Line Item Events

Ensure your existing invoice.js fires these custom events:

```javascript
// When line item is added
document.dispatchEvent(new CustomEvent('line-item-added'));

// When line item is removed
document.dispatchEvent(new CustomEvent('line-item-removed'));

// When line item is changed (service selected, quantity changed)
document.dispatchEvent(new CustomEvent('line-item-changed'));
```

#### B. Form Submission

No changes needed - validation is automatic via form submit event listener in `invoice_bulk_discount.js`.

---

### Step 5: Backend API Endpoints

Already created:
- `GET /api/discount/config/<hospital_id>` - Get discount configuration
- `POST /api/discount/calculate` - Calculate discounts in real-time
- `GET /api/discount/patient-loyalty/<patient_id>` - Get patient loyalty card

Registered in `app/__init__.py` via `discount_bp` blueprint.

---

## Testing Checklist

### Test 1: Eligible Services Only
```
Scenario: 5 Laser Hair Reduction services
Expected:
  - Badge: "✓ Eligible (5 services)"
  - Checkbox: Auto-checked
  - Discounts: 10% applied to all 5
  - Summary: Shows original price, discount, final price
```

### Test 2: Mixed Eligible/Ineligible
```
Scenario:
  - 1 Doctor's Consultation (bulk_discount_percent = 0)
  - 4 Laser Hair Reduction (bulk_discount_percent = 10%)

Expected:
  - Badge: "Add 1 more eligible service to unlock"
  - Info: "Doctor's Consultation is not eligible for bulk discount"
  - Count: "4 eligible (5 total, 1 excluded)"
  - Discounts: Not applied (below threshold)
```

### Test 3: Add Service to Unlock
```
Scenario: Start with 4 eligible services
Action: Add 5th eligible service
Expected:
  - Badge changes from warning to success
  - Checkbox auto-checks
  - Discounts instantly applied to all 5
  - Summary updates in real-time
  - User sees savings immediately
```

### Test 4: Remove Service Below Threshold
```
Scenario: Have 5 eligible services (discount active)
Action: Remove 1 service
Expected:
  - Badge changes to warning: "Add 1 more..."
  - Checkbox auto-unchecks
  - Discounts cleared from all items
  - Summary resets
  - Potential savings panel appears
```

### Test 5: Loyalty vs Bulk
```
Scenario:
  - Patient has Gold card (10% loyalty)
  - 5 Medifacial services (15% bulk)

Expected:
  - Both discounts calculated
  - 15% bulk selected (higher)
  - Badge shows "Bulk 15%"
  - Loyalty card badge visible in header
  - Metadata shows competing discount (loyalty 10%)
```

### Test 6: Max Discount Capping
```
Scenario:
  - Service: Botox (max_discount = 5%, bulk_discount_percent = 10%)
  - 5 services in invoice

Expected:
  - Bulk discount calculated as 10%
  - Capped at 5% (max_discount)
  - Badge shows "Bulk 5%"
  - Info message: "Discount capped at maximum allowed"
```

### Test 7: Form Validation
```
Scenario: User manually checks bulk discount with only 3 services
Action: Submit form
Expected:
  - Alert: "Bulk discount requires 5 services..."
  - Form submission prevented
  - Checkbox auto-unchecked
  - Discounts cleared
  - User can fix and resubmit
```

---

## Configuration Required

### 1. Set Service Bulk Discount Percentages

```sql
-- Configure which services are eligible
UPDATE services
SET bulk_discount_percent = 10.00
WHERE service_name LIKE '%Laser%';

UPDATE services
SET bulk_discount_percent = 15.00
WHERE service_name LIKE '%Facial%';

-- Make consultations ineligible
UPDATE services
SET bulk_discount_percent = 0.00
WHERE service_type = 'Consultation';
```

### 2. Enable Hospital Bulk Discount

```sql
-- Already done via migration, but verify:
SELECT
    name,
    bulk_discount_enabled,
    bulk_discount_min_service_count
FROM hospitals;

-- Should show:
-- bulk_discount_enabled = TRUE
-- bulk_discount_min_service_count = 5
```

---

## Troubleshooting

### Issue: Panel Not Showing

**Check:**
1. Is `hospital_id` hidden input present?
2. Is JavaScript file loaded? (Check browser console)
3. Are there JS errors? (Check browser console)

**Fix:**
```javascript
// In browser console:
console.log(window.bulkDiscountManager);
// Should not be null
```

### Issue: Discounts Not Calculating

**Check:**
1. Backend API responding? (Network tab)
2. Service discount percentages set? (Check database)
3. Hospital bulk discount enabled? (Check database)

**Fix:**
```bash
# Test API manually:
curl http://localhost:5000/api/discount/config/{hospital-id}
```

### Issue: Wrong Service Count

**Check:**
1. Are services with 0% being counted?
2. Check JavaScript console for logs

**Expected Log:**
```
Service 'Doctor's Consultation' NOT eligible for bulk discount
Eligible services for bulk discount: 4
```

---

## Success Metrics

**After Implementation, Monitor:**

1. **User Engagement**
   - % of invoices with bulk discount checkbox checked
   - Average services per invoice (should increase)

2. **Revenue Impact**
   - Average discount % per invoice
   - Total revenue vs total discount given

3. **User Behavior**
   - Do users add more services to reach threshold?
   - Do users understand the pricing?

4. **Performance**
   - Page load time (should be < 2 seconds)
   - API response time (should be < 500ms)

---

## Future Enhancements

1. **Service Recommendations**
   - "Patients who book Laser also book..."
   - Suggest services to reach threshold

2. **Package Suggestions**
   - "Save more with our Laser Package"
   - Show package vs individual pricing

3. **Historical Pricing**
   - "You paid ₹25,000 last visit"
   - Show price comparison

4. **Appointment Scheduler Integration**
   - "Schedule 5 sessions now, pay in installments"
   - Link to appointment booking

---

## Support

**Files Created:**
- `app/api/routes/discount_api.py` - Backend API
- `app/static/js/components/invoice_bulk_discount.js` - Frontend logic
- `app/static/css/components/bulk_discount.css` - Styling (to be created)

**Documentation:**
- This implementation guide
- `Bulk Service Discount System - Complete Reference Guide.md`
- `Deployment Summary - Bulk Discounts LIVE.md`

**Contact:**
For issues or questions, review the application logs:
```bash
tail -f logs/app.log | grep -i discount
```

---

**Implementation Status:** ✅ Backend Complete | ⏳ Frontend Ready for Integration | 🧪 Testing Pending
