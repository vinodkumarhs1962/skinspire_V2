# Discount Stacking Fixes - November 22, 2025

## Issues Fixed

### 1. **Staff View - Bulk and Loyalty Shown Separately** ✅
**Problem:** Staff view allocated entire 20% to bulk discount, loyalty showed as 0%

**Root Causes:**
- API was calculating separate amounts but not returning them
- Frontend was showing total_discount in bulk amount field
- Loyalty checkbox never ticked

**Fixes Applied:**

**Backend (`app/api/routes/discount_api.py`):**
- Lines 267-280: Added logic to calculate `bulk_discount_amount` and `loyalty_discount_amount` separately
- Lines 331-332: Added both amounts to API summary response

**Frontend (`app/static/js/components/invoice_bulk_discount.js`):**
- Lines 559-642: Updated `addDiscountBadge()` to handle `bulk_plus_loyalty` type and show TWO badges
- Lines 337: Pass `discount_metadata` to badge method
- Lines 454-491: Updated `updatePricingSummary()` to:
  - Show bulk_discount_amount in bulk panel (not total_discount)
  - Tick loyalty checkbox when loyalty_discount_amount > 0
  - Display loyalty amount and card type

**Result:**
- Bulk shows: "Bulk 15%" badge with ₹3,750 amount
- Loyalty shows: "Loyalty 5%" badge with ₹1,250 amount
- Loyalty checkbox auto-ticked
- Total discount: ₹5,000 (20%)

---

### 2. **Patient View - Clear Discount Breakdown** ✅
**Problem:** Patient view showed "20% none discount" instead of clear breakdown

**Root Cause:**
- Patient view grouped discounts by `discount_type`
- When type was `bulk_plus_loyalty`, it showed as one unclear entry

**Fixes Applied:**

**Frontend (`app/static/js/components/invoice_patient_view.js`):**
- Lines 103-132: Updated discount breakdown logic to:
  - Detect `bulk_plus_loyalty` type
  - Extract metadata with bulk_percent and loyalty_percent
  - Calculate each component amount
  - Add as separate `bulk` and `loyalty` entries

**Result:**
- Patient view now shows:
  - **Bulk Discount:** ₹3,750
  - **Loyalty Discount:** ₹1,250
  - **Total Discount:** ₹5,000

---

### 3. **Backend Bug - Decimal Type Mismatch** ✅
**Problem:** Loyalty discount calculation crashed with `TypeError: unsupported operand type(s) for *: 'float' and 'decimal.Decimal'`

**Fixes Applied:**

**Backend (`app/services/discount_service.py`):**
- Line 436: Added `float()` conversion: `discount_percent = float(card_type.discount_percent)`

**Result:** Loyalty discount calculation now works without type errors

---

## Configuration Changes

### Database Updates

1. **Service Configuration (Advanced Facial):**
```sql
UPDATE services
SET loyalty_discount_percent = 5.00,
    max_discount = 20.00
WHERE service_id = '40b89b81-5528-401d-b54c-345515491db1';
```

2. **Hospital Loyalty Mode:**
```sql
UPDATE hospitals
SET loyalty_discount_mode = 'additional'
WHERE hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca';
```

3. **Test Promotion (Disabled):**
```sql
UPDATE promotion_campaigns
SET is_active = false
WHERE campaign_id = 'bf675bdd-6b2a-4af5-80ca-3c7410162408';
```

4. **Patient Loyalty Card (Ram Kumar):**
- Card Number: `SILVER-RAM-2025`
- Card Type: Silver Member (5% discount)
- Status: Active
- Expiry: 2026-11-22

---

## Files Modified

### Backend Files
1. `app/services/discount_service.py` - Fixed Decimal type conversion
2. `app/api/routes/discount_api.py` - Added bulk/loyalty breakdown to summary

### Frontend Files
1. `app/static/js/components/invoice_bulk_discount.js` - Staff view discount display
2. `app/static/js/components/invoice_patient_view.js` - Patient view breakdown

---

## Testing Checklist

### Test Scenario: Advanced Facial x 5
- Patient: Ram Kumar (Silver Member 5%)
- Service: Advanced Facial (₹5,000 each, bulk 15% at qty 5)
- Quantity: 5
- Total Before Discount: ₹25,000

### Expected Results:

**Staff View:**
- ✅ Bulk Discount checkbox: Ticked
- ✅ Bulk Discount badge: "Bulk 15%"
- ✅ Bulk Discount amount: ₹3,750
- ✅ Loyalty checkbox: Ticked
- ✅ Loyalty card shown: Silver Member
- ✅ Loyalty amount: ₹1,250
- ✅ Line item shows: Two badges ("Bulk 15%" and "Loyalty 5%")
- ✅ Discount field: 20.00%
- ✅ Subtotal after discount: ₹20,000
- ⚠️ **Need to verify:** GST calculation on ₹20,000
- ⚠️ **Need to verify:** Grand total includes GST correctly

**Patient View:**
- ✅ Discount Breakdown section shows:
  - Bulk Discount: ₹3,750
  - Loyalty Discount: ₹1,250
- ✅ Total Discount: ₹5,000
- ✅ Subtotal After Discount: ₹20,000
- ✅ GST calculated on ₹20,000
- ✅ Grand Total = ₹20,000 + GST

---

## Known Issues / To Verify

1. **GST Calculation in Staff View:**
   - User reported: "Total patient pays is incorrect. It is not considering GST"
   - Need to test if GST is being calculated on discounted price
   - Check if invoice total calculations trigger properly after discount updates

2. **Multi-Service Testing:**
   - Current test used single service type
   - Need to test mixed cart (services + medicines + packages)

---

## How Discount Stacking Works

### Priority System:
1. **Promotion** (Priority 1) - Always wins, no stacking
2. **Bulk + Loyalty** (Priority 2) - Can stack in 'additional' mode
3. **Standard** (Priority 4) - Fallback

### Stacking Logic:
- When `loyalty_discount_mode = 'additional'`:
  - Bulk% + Loyalty% = Combined%
  - Combined% capped by `service.max_discount`
  - Backend returns `discount_type: "bulk_plus_loyalty"`
  - Metadata contains `bulk_percent` and `loyalty_percent`

- When `loyalty_discount_mode = 'absolute'`:
  - System picks higher of bulk% or loyalty%
  - No stacking

### API Response Format:
```json
{
  "discount_type": "bulk_plus_loyalty",
  "discount_percent": 20.0,
  "discount_amount": 5000.0,
  "card_type_id": "570dde56-1c67-45ad-981e-a2eec02570fc",
  "discount_metadata": {
    "bulk_percent": 15.0,
    "loyalty_percent": 5.0,
    "selection_reason": "Combined bulk + loyalty (additional mode)"
  }
}
```

---

## Next Steps

1. Start Flask server
2. Test complete invoice flow with Ram Kumar
3. Verify GST calculation
4. Test other discount combinations
5. Document final results
