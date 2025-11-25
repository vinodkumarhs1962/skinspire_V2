# Next Task: Buy X Get Y Implementation Guide
## Quick Start for Next Session
## Estimated Effort: 4-6 hours

---

## CURRENT STATUS

✅ **COMPLETE**:
- Database schema extended (`promotion_type`, `promotion_rules`)
- Models updated (`PromotionCampaign` has new fields)
- Campaign tracking added (`invoice_header.campaigns_applied`)
- Field renamed (`campaign_hook_id` → `promotion_id`)
- Multi-discount backend working (Standard, Bulk, Loyalty%, Promotion simple_discount)

⏳ **NEXT TASK**:
- Implement Buy X Get Y Free promotion logic

---

## IMPLEMENTATION STEPS

### Step 1: Create `handle_buy_x_get_y()` Method

**Location**: `app/services/discount_service.py` (add after `calculate_promotion_discount`)

**Method Signature**:
```python
@staticmethod
def handle_buy_x_get_y(
    session: Session,
    promotion: PromotionCampaign,
    invoice_items: List[Dict],  # Full invoice context
    current_item_type: str,
    current_item_id: str,
    unit_price: Decimal,
    quantity: int
) -> Optional[DiscountCalculationResult]:
    """
    Handle Buy X Get Y Free promotions

    Logic:
    1. Parse promotion_rules JSON
    2. Check if trigger condition is met (invoice contains X)
    3. Check if current item is the reward item (Y)
    4. If yes, return discount (usually 100% for "free")
    """
```

**Implementation Pattern**:
```python
rules = promotion.promotion_rules
if not rules:
    return None

trigger = rules.get('trigger', {})
reward = rules.get('reward', {})

# Step 1: Check trigger condition
trigger_met = False

if trigger['type'] == 'item_purchase':
    trigger_item_ids = trigger['conditions'].get('item_ids', [])
    trigger_item_type = trigger['conditions'].get('item_type')
    min_amount = trigger['conditions'].get('min_amount', 0)

    for item in invoice_items:
        if item.get('item_id') in trigger_item_ids:
            if item.get('item_type') == trigger_item_type:
                item_total = Decimal(str(item.get('unit_price', 0))) * int(item.get('quantity', 1))
                if item_total >= min_amount:
                    trigger_met = True
                    break

if not trigger_met:
    return None

# Step 2: Check if current item is reward item
reward_items = reward.get('items', [])
for reward_item in reward_items:
    if (reward_item['item_id'] == current_item_id and
        reward_item['item_type'] == current_item_type):

        # Calculate discount (usually 100% for "free")
        discount_percent = Decimal(str(reward_item.get('discount_percent', 100)))
        original_price = unit_price * quantity
        discount_amount = (original_price * discount_percent) / 100
        final_price = original_price - discount_amount

        return DiscountCalculationResult(
            discount_type='promotion',
            discount_percent=discount_percent,
            discount_amount=discount_amount,
            final_price=final_price,
            original_price=original_price,
            promotion_id=str(promotion.campaign_id),
            metadata={
                'promotion_type': 'buy_x_get_y',
                'campaign_name': promotion.campaign_name,
                'trigger_met': True,
                'reward_item': True
            }
        )

return None
```

---

### Step 2: Extend `calculate_promotion_discount()`

**Current Location**: `app/services/discount_service.py:457-645`

**Add Logic**:
```python
@staticmethod
def calculate_promotion_discount(
    session: Session,
    hospital_id: str,
    patient_id: str,
    item_type: str,
    item_id: str,
    unit_price: Decimal,
    quantity: int = 1,
    invoice_date: date = None,
    invoice_items: List[Dict] = None  # NEW: Full invoice context
) -> Optional[DiscountCalculationResult]:
    """
    Calculate promotion discount based on promotion_type
    """
    # Get active promotions
    promotions = session.query(PromotionCampaign).filter(...)

    for promotion in promotions:
        # NEW: Check promotion_type
        if promotion.promotion_type == 'simple_discount':
            # Current logic (already implemented)
            # ... existing code ...

        elif promotion.promotion_type == 'buy_x_get_y':
            # NEW: Handle Buy X Get Y
            if invoice_items is None:
                continue  # Need invoice context for buy_x_get_y

            result = DiscountService.handle_buy_x_get_y(
                session=session,
                promotion=promotion,
                invoice_items=invoice_items,
                current_item_type=item_type,
                current_item_id=item_id,
                unit_price=unit_price,
                quantity=quantity
            )
            if result:
                return result

        # ... other promotion types (tiered, bundle) for future

    return None
```

---

### Step 3: Update `get_best_discount_multi()` Signature

**Current Location**: `app/services/discount_service.py:727-881`

**Change**:
```python
@staticmethod
def get_best_discount_multi(
    session: Session,
    hospital_id: str,
    patient_id: str,
    item_type: str,
    item_id: str,
    unit_price: Decimal,
    quantity: int,
    total_item_count: int,
    invoice_date: date = None,
    invoice_items: List[Dict] = None  # NEW: Pass full invoice context
) -> DiscountCalculationResult:
    """
    Calculate all applicable discounts using priority logic
    """
    # ... existing code ...

    # 1. PROMOTION (Priority 1 - Highest)
    promotion_discount = DiscountService.calculate_promotion_discount(
        session, hospital_id, patient_id, item_type, item_id,
        unit_price, quantity, invoice_date,
        invoice_items=invoice_items  # NEW: Pass context
    )
    if promotion_discount:
        return promotion_discount

    # ... rest of priority logic ...
```

---

### Step 4: Update `apply_discounts_to_invoice_items_multi()`

**Current Location**: `app/services/discount_service.py:1054-1225`

**Change**: Pass `line_items` to `get_best_discount_multi()`

```python
for item in service_items:
    service_id = item.get('item_id') or item.get('service_id')
    # ...

    best_discount = DiscountService.get_best_discount_multi(
        session=session,
        hospital_id=hospital_id,
        patient_id=patient_id,
        item_type='Service',
        item_id=service_id,
        unit_price=unit_price,
        quantity=quantity,
        total_item_count=total_service_count,
        invoice_date=invoice_date,
        invoice_items=line_items  # NEW: Pass full invoice context
    )
```

**Repeat for medicines and packages loops**

---

## TEST SCENARIOS

### Test 1: Buy High-Value Service → Free Consultation

```python
def test_buy_x_get_y_high_value_service():
    # Create promotion
    promotion = create_promotion_buy_x_get_y(
        trigger_min_amount=5000,
        reward_item_id='consultation-id',
        reward_discount=100
    )

    # Create invoice
    line_items = [
        {'item_type': 'Service', 'item_id': 'laser-id', 'unit_price': 8000, 'quantity': 1},
        {'item_type': 'Service', 'item_id': 'consultation-id', 'unit_price': 500, 'quantity': 1}
    ]

    # Apply discounts
    updated_items = DiscountService.apply_discounts_to_invoice_items_multi(...)

    # Verify
    consultation = [item for item in updated_items if item['item_id'] == 'consultation-id'][0]
    assert consultation['discount_percent'] == 100
    assert consultation['discount_amount'] == 500
    assert consultation['discount_type'] == 'promotion'
```

---

## SAMPLE PROMOTION DATA

```sql
-- Insert test Buy X Get Y promotion
INSERT INTO promotion_campaigns (
    hospital_id,
    campaign_name,
    campaign_code,
    description,
    start_date,
    end_date,
    is_active,
    promotion_type,
    discount_type,
    discount_value,
    applies_to,
    promotion_rules,
    auto_apply
)
SELECT
    hospital_id,
    'Premium Service - Free Consultation',
    'PREMIUM_CONSULT',
    'Buy service worth Rs.5000 or more, get consultation free',
    CURRENT_DATE,
    CURRENT_DATE + INTERVAL '30 days',
    TRUE,
    'buy_x_get_y',
    'percentage',
    0,
    'services',
    '{
        "trigger": {
            "type": "item_purchase",
            "conditions": {
                "item_type": "Service",
                "min_amount": 5000
            }
        },
        "reward": {
            "type": "free_item",
            "items": [
                {
                    "item_id": "' || s.service_id::text || '",
                    "item_type": "Service",
                    "quantity": 1,
                    "discount_percent": 100
                }
            ],
            "auto_add": true,
            "max_free_items": 1
        }
    }'::jsonb,
    TRUE
FROM hospitals h
CROSS JOIN services s
WHERE s.service_name = 'Consultation'
LIMIT 1;
```

---

## VERIFICATION CHECKLIST

- [ ] `handle_buy_x_get_y()` method created
- [ ] `calculate_promotion_discount()` checks promotion_type
- [ ] `get_best_discount_multi()` accepts invoice_items parameter
- [ ] `apply_discounts_to_invoice_items_multi()` passes line_items
- [ ] Test promotion created in database
- [ ] Test scenario 1: High-value service → Free consultation (PASSED)
- [ ] Test scenario 2: Specific service → Free product (PASSED)
- [ ] Test scenario 3: Below threshold → No reward (PASSED)

---

## FILES TO MODIFY

1. **app/services/discount_service.py**
   - Add `handle_buy_x_get_y()` method
   - Update `calculate_promotion_discount()` to dispatch by type
   - Update `get_best_discount_multi()` signature
   - Update `apply_discounts_to_invoice_items_multi()` calls

**Total Changes**: ~150 lines

---

## EXPECTED BEHAVIOR

### Scenario: Patient buys "Laser Hair Removal" (Rs.8000)

**With Buy X Get Y Promotion Active**:

1. **Invoice Creation**:
   - Line 1: Laser Hair Removal @ Rs.8000
   - Line 2: Consultation @ Rs.500 (manually added by user)

2. **Discount Calculation**:
   - System checks promotions
   - Finds "Buy service ≥ Rs.5000 → Free Consultation"
   - Trigger met: Rs.8000 ≥ Rs.5000 ✅
   - Applies 100% discount to consultation line

3. **Invoice Display**:
   ```
   Item                   Qty  Price      Discount    Total
   ─────────────────────────────────────────────────────────
   Laser Hair Removal     1    Rs.8000    0%          Rs.8000
   Consultation (FREE!)   1    Rs.500     100%        Rs.0
                                                      ───────
                                          Subtotal:   Rs.8000
                                          Discount:   Rs.500
                                             TOTAL:   Rs.8000
   ```

4. **Campaign Tracking**:
   - `invoice_header.campaigns_applied`:
   ```json
   [{
     "campaign_id": "uuid",
     "campaign_name": "Premium Service - Free Consultation",
     "promotion_type": "buy_x_get_y",
     "total_discount": 500.00,
     "items_affected": ["consultation-id"]
   }]
   ```

---

## SUCCESS CRITERIA

✅ Buy X Get Y logic complete when:
1. Trigger conditions correctly identified from invoice_items
2. Reward items receive correct discount (usually 100%)
3. Non-reward items unaffected
4. Promotion priority (1) respected
5. Test scenarios pass
6. No regression in existing discount types

---

## ESTIMATED TIMELINE

| Task | Time |
|------|------|
| Create handle_buy_x_get_y() method | 2 hours |
| Update calculate_promotion_discount() | 1 hour |
| Update method signatures | 30 minutes |
| Testing | 1-2 hours |
| Documentation | 30 minutes |
| **TOTAL** | **5-6 hours** |

---

## QUICK REFERENCE

**Current File**: `app/services/discount_service.py`

**Key Line Numbers** (approximate):
- Line 457: `calculate_promotion_discount()` - MODIFY
- Line 645: Insert `handle_buy_x_get_y()` - NEW METHOD
- Line 727: `get_best_discount_multi()` - ADD PARAMETER
- Line 1054: `apply_discounts_to_invoice_items_multi()` - PASS CONTEXT

**Database**:
- Table: `promotion_campaigns`
- Fields: `promotion_type`, `promotion_rules`

**Test File**: `test_multi_discount_backend.py` (or create new test file)

---

**Document Created**: 21-November-2025, 11:30 PM IST
**Status**: READY FOR IMPLEMENTATION
**Next Session**: Start with Step 1 (Create handle_buy_x_get_y method)

---

**END OF IMPLEMENTATION GUIDE**
