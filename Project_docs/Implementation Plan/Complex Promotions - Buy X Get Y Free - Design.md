# Complex Promotions: Buy X Get Y Free - Design Document
## Date: 21-November-2025, 11:10 PM IST
## Status: DESIGN PROPOSAL

---

## BUSINESS SCENARIOS

### Scenario 1: Buy High-Value Service, Get Consultation Free
**Rule**: If patient purchases a service worth ≥ Rs.5000, consultation is free

**Example**:
- Patient books "Laser Hair Removal" (Rs.8000)
- System automatically adds "Consultation" (Rs.500) with 100% discount

---

### Scenario 2: Buy Service, Get Product Free
**Rule**: Buy "Medi Facial" service, get "Sunscreen 50ml" free

**Example**:
- Patient books "Medi Facial" (Rs.3000)
- System offers "Sunscreen 50ml" (Rs.800) with 100% discount

---

### Scenario 3: Buy X Quantity, Get Y Free
**Rule**: Buy 5 "Botox Units", get 2 units free

**Example**:
- Patient purchases 5 Botox units @ Rs.500 each = Rs.2500
- System adds 2 Botox units @ Rs.0 (100% discount)

---

## CURRENT LIMITATION

**Current `promotion_campaigns` table supports:**
- ✅ Percentage discount on ALL items
- ✅ Fixed amount discount on ALL items
- ✅ Item-specific discounts (via `specific_items` JSONB)

**Current `promotion_campaigns` table DOES NOT support:**
- ❌ "Buy X Get Y Free" logic
- ❌ Cross-item dependencies
- ❌ Conditional free items
- ❌ Quantity-based free items

---

## PROPOSED SOLUTION: Extend promotion_campaigns Table

### Option 1: Add promotion_type Field (Recommended ✅)

#### Database Schema Extension

```sql
-- Migration: Add promotion_type support for complex promotions
-- Date: TBD

ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS promotion_type VARCHAR(20) DEFAULT 'simple_discount'
CHECK (promotion_type IN ('simple_discount', 'buy_x_get_y', 'tiered_discount', 'bundle'));

ALTER TABLE promotion_campaigns
ADD COLUMN IF NOT EXISTS promotion_rules JSONB;

COMMENT ON COLUMN promotion_campaigns.promotion_type IS
'Type of promotion: simple_discount, buy_x_get_y, tiered_discount, bundle';

COMMENT ON COLUMN promotion_campaigns.promotion_rules IS
'Complex promotion rules in JSON format (varies by promotion_type)';
```

---

### Promotion Type Definitions

#### 1. `simple_discount` (Already Implemented ✅)
**Current behavior**: Apply percentage or fixed_amount discount

**promotion_rules**: NULL (not used)

**Example**:
```json
{
  "promotion_type": "simple_discount",
  "discount_type": "percentage",
  "discount_value": 20.00
}
```

---

#### 2. `buy_x_get_y` (NEW - For Your Scenario)
**Behavior**: If patient buys item(s) matching X criteria, add item(s) matching Y criteria with discount

**promotion_rules Structure**:
```json
{
  "trigger": {
    "type": "item_purchase",  // or "min_spend", "item_quantity"
    "conditions": {
      "item_ids": ["service-id-1", "service-id-2"],  // Buy any of these
      "item_type": "Service",  // Or "Medicine", "Package"
      "min_amount": 5000,  // Optional: minimum purchase amount
      "min_quantity": 1  // Optional: minimum quantity
    }
  },
  "reward": {
    "type": "free_item",  // or "discounted_item"
    "items": [
      {
        "item_id": "consultation-service-id",
        "item_type": "Service",
        "quantity": 1,
        "discount_percent": 100.00  // 100% = free
      }
    ],
    "auto_add": true,  // Automatically add to invoice
    "max_free_items": 1  // Limit free items
  }
}
```

**Use Cases**:
1. **Buy High-Value Service → Free Consultation**
2. **Buy Medi Facial → Free Product**
3. **Buy 5 Botox → Get 2 Free**

---

#### 3. `tiered_discount` (Future Enhancement)
**Behavior**: Discount increases with spend amount

**promotion_rules Structure**:
```json
{
  "tiers": [
    {
      "min_amount": 1000,
      "max_amount": 2999,
      "discount_percent": 5.00
    },
    {
      "min_amount": 3000,
      "max_amount": 4999,
      "discount_percent": 10.00
    },
    {
      "min_amount": 5000,
      "max_amount": null,
      "discount_percent": 15.00
    }
  ],
  "applies_to": "invoice_total"  // or "specific_items"
}
```

---

#### 4. `bundle` (Future Enhancement)
**Behavior**: Buy items A + B + C together, get bundle discount

**promotion_rules Structure**:
```json
{
  "bundle_items": [
    {"item_id": "service-1", "item_type": "Service", "required": true},
    {"item_id": "medicine-1", "item_type": "Medicine", "required": true},
    {"item_id": "product-1", "item_type": "Medicine", "required": false}
  ],
  "bundle_discount_percent": 20.00,
  "all_items_required": true
}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Database Schema (1 hour)
1. Add `promotion_type` column to `promotion_campaigns`
2. Add `promotion_rules` JSONB column
3. Set defaults for existing promotions
4. Create migration script

---

### Phase 2: Backend Logic (4-6 hours)

#### Step 1: Extend `calculate_promotion_discount()` Method

**Current**: Only handles simple percentage/fixed_amount

**New**: Check `promotion_type` and dispatch to appropriate handler

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
    invoice_items: List[Dict] = None  # NEW: Full invoice context for buy_x_get_y
) -> Optional[DiscountCalculationResult]:
    """
    Calculate promotion discount based on promotion_type
    """
    # Get active promotions
    promotions = session.query(PromotionCampaign).filter(...)

    for promotion in promotions:
        if promotion.promotion_type == 'simple_discount':
            # Current logic (already implemented)
            result = handle_simple_discount(promotion, ...)
            if result:
                return result

        elif promotion.promotion_type == 'buy_x_get_y':
            # NEW: Handle Buy X Get Y
            result = handle_buy_x_get_y(promotion, invoice_items, ...)
            if result:
                return result

        # ... other promotion types

    return None
```

---

#### Step 2: Implement `handle_buy_x_get_y()` Method

```python
@staticmethod
def handle_buy_x_get_y(
    session: Session,
    promotion: PromotionCampaign,
    invoice_items: List[Dict],
    current_item_type: str,
    current_item_id: str,
    unit_price: Decimal,
    quantity: int
) -> Optional[DiscountCalculationResult]:
    """
    Handle Buy X Get Y Free promotions

    Logic:
    1. Check if trigger condition is met (invoice contains X)
    2. Check if current item is the reward item (Y)
    3. If yes, return 100% discount (or configured discount)
    """
    rules = promotion.promotion_rules
    if not rules:
        return None

    trigger = rules.get('trigger', {})
    reward = rules.get('reward', {})

    # Check trigger condition
    trigger_met = False

    if trigger['type'] == 'item_purchase':
        # Check if invoice contains trigger items
        trigger_item_ids = trigger['conditions'].get('item_ids', [])
        trigger_item_type = trigger['conditions'].get('item_type')
        min_amount = trigger['conditions'].get('min_amount', 0)

        for item in invoice_items:
            if item.get('item_id') in trigger_item_ids:
                if item.get('item_type') == trigger_item_type:
                    # Check if item meets min_amount
                    item_total = Decimal(str(item.get('unit_price', 0))) * int(item.get('quantity', 1))
                    if item_total >= min_amount:
                        trigger_met = True
                        break

    if not trigger_met:
        return None

    # Check if current item is the reward item
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

#### Step 3: Update `apply_discounts_to_invoice_items_multi()`

**Change**: Pass full `invoice_items` context to `calculate_promotion_discount()`

```python
@staticmethod
def apply_discounts_to_invoice_items_multi(
    session: Session,
    hospital_id: str,
    patient_id: str,
    line_items: List[Dict],
    invoice_date: date = None,
    respect_max_discount: bool = True
) -> List[Dict]:
    """
    Apply multi-discount logic to all items
    """
    # ... existing code ...

    for item in service_items:
        service_id = item.get('item_id')
        unit_price = Decimal(str(item.get('unit_price', 0)))
        quantity = int(item.get('quantity', 1))

        # NEW: Pass full invoice_items context
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
            invoice_items=line_items  # NEW: Pass full context
        )

        # ... rest of code ...
```

---

#### Step 4: Update `get_best_discount_multi()` Signature

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
    invoice_items: List[Dict] = None  # NEW: Full invoice context
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

### Phase 3: Frontend Implementation (2-3 hours)

#### UI for Buy X Get Y Promotions

**Admin Panel**: Create Promotion Form

```html
<!-- Promotion Type Selection -->
<select name="promotion_type">
  <option value="simple_discount">Simple Discount (% or fixed)</option>
  <option value="buy_x_get_y">Buy X Get Y Free</option>
  <option value="tiered_discount">Tiered Discount</option>
  <option value="bundle">Bundle Discount</option>
</select>

<!-- Show/Hide based on promotion_type -->

<!-- For "buy_x_get_y" -->
<div id="buy_x_get_y_config" style="display:none;">
  <h4>Trigger Condition</h4>

  <label>Trigger Type:</label>
  <select name="trigger_type">
    <option value="item_purchase">Item Purchase</option>
    <option value="min_spend">Minimum Spend</option>
  </select>

  <label>Trigger Items (Select Services/Medicines that trigger this):</label>
  <select name="trigger_items" multiple>
    <option value="service-1">Laser Hair Removal (Rs.8000)</option>
    <option value="service-2">Medi Facial (Rs.3000)</option>
    <!-- ... -->
  </select>

  <label>Minimum Purchase Amount (optional):</label>
  <input type="number" name="min_amount" placeholder="e.g., 5000">

  <h4>Reward Items (Free/Discounted)</h4>

  <label>Free Items (Select items to give as reward):</label>
  <select name="reward_items" multiple>
    <option value="service-consultation">Consultation (Rs.500)</option>
    <option value="medicine-sunscreen">Sunscreen 50ml (Rs.800)</option>
    <!-- ... -->
  </select>

  <label>Discount on Reward Items:</label>
  <input type="number" name="reward_discount" value="100" min="0" max="100"> %

  <label>Auto-add to Invoice:</label>
  <input type="checkbox" name="auto_add" checked>

  <label>Max Free Items per Invoice:</label>
  <input type="number" name="max_free_items" value="1" min="1">
</div>
```

---

#### Frontend Behavior: Invoice Creation

**Scenario**: Patient adds "Laser Hair Removal" (Rs.8000)

**System Behavior**:
1. **Check for Buy X Get Y promotions**
   - Finds promotion: "Buy service ≥ Rs.5000 → Free Consultation"
   - Trigger met: Rs.8000 ≥ Rs.5000 ✅

2. **Auto-add reward item** (if `auto_add = true`)
   - Add "Consultation" line item
   - Apply 100% discount automatically
   - Show banner: "🎁 Free Consultation added! (Promotion: High-Value Purchase)"

3. **Invoice Display**:
   ```
   Item                        Qty  Price      Discount    Total
   ───────────────────────────────────────────────────────────────
   Laser Hair Removal          1    Rs.8000    0%          Rs.8000
   Consultation (FREE!)        1    Rs.500     100%        Rs.0
                                                            ───────
                                                   Subtotal: Rs.8000
                                                   Discount: Rs.500
                                                      TOTAL: Rs.8000
   ```

---

### Phase 4: Testing (1-2 hours)

#### Test Cases

**Test 1**: Buy High-Value Service → Free Consultation
```python
def test_buy_high_value_get_consultation_free():
    # Create promotion
    promotion = PromotionCampaign(
        promotion_type='buy_x_get_y',
        promotion_rules={
            'trigger': {
                'type': 'item_purchase',
                'conditions': {
                    'item_type': 'Service',
                    'min_amount': 5000
                }
            },
            'reward': {
                'type': 'free_item',
                'items': [
                    {
                        'item_id': 'consultation-id',
                        'item_type': 'Service',
                        'quantity': 1,
                        'discount_percent': 100
                    }
                ],
                'auto_add': True
            }
        }
    )

    # Create invoice with high-value service
    line_items = [
        {'item_type': 'Service', 'item_id': 'laser-id', 'unit_price': 8000, 'quantity': 1},
        {'item_type': 'Service', 'item_id': 'consultation-id', 'unit_price': 500, 'quantity': 1}
    ]

    # Apply discounts
    updated_items = DiscountService.apply_discounts_to_invoice_items_multi(...)

    # Verify consultation is free
    consultation_item = [item for item in updated_items if item['item_id'] == 'consultation-id'][0]
    assert consultation_item['discount_percent'] == 100
    assert consultation_item['discount_amount'] == 500
    assert consultation_item['discount_type'] == 'promotion'
```

---

## SAMPLE DATA

### Example 1: Buy High-Value Service → Free Consultation

```sql
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
) VALUES (
    'your-hospital-id',
    'Premium Service - Free Consultation',
    'PREMIUM_CONSULT_FREE',
    'Buy any service worth Rs.5000 or more, get consultation free',
    '2025-11-01',
    '2025-12-31',
    TRUE,
    'buy_x_get_y',  -- NEW: promotion_type
    'percentage',  -- Not used for buy_x_get_y, but required field
    0,  -- Not used for buy_x_get_y
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
                    "item_id": "consultation-service-id",
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
);
```

---

### Example 2: Buy Medi Facial → Free Sunscreen

```sql
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
) VALUES (
    'your-hospital-id',
    'Medi Facial - Free Sunscreen',
    'MEDIFACIAL_SUNSCREEN',
    'Book Medi Facial service, get Sunscreen 50ml free',
    '2025-11-01',
    '2025-12-31',
    TRUE,
    'buy_x_get_y',
    'percentage',
    0,
    'all',
    '{
        "trigger": {
            "type": "item_purchase",
            "conditions": {
                "item_ids": ["medi-facial-service-id"],
                "item_type": "Service",
                "min_quantity": 1
            }
        },
        "reward": {
            "type": "free_item",
            "items": [
                {
                    "item_id": "sunscreen-50ml-medicine-id",
                    "item_type": "Medicine",
                    "quantity": 1,
                    "discount_percent": 100
                }
            ],
            "auto_add": true,
            "max_free_items": 1
        }
    }'::jsonb,
    TRUE
);
```

---

## ESTIMATED EFFORT

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Database schema extension | 1 hour |
| 2 | Backend logic (buy_x_get_y) | 4-6 hours |
| 3 | Frontend UI for promotion config | 2-3 hours |
| 4 | Testing | 1-2 hours |
| **TOTAL** | | **8-12 hours** |

---

## BACKWARD COMPATIBILITY

**Existing Promotions**: All existing promotions will have:
- `promotion_type = 'simple_discount'` (default)
- `promotion_rules = NULL`

**Migration**: No data migration needed, defaults handle existing records

---

## BENEFITS

1. **No Python Code Required**: All logic in database + generic handler
2. **Business User Friendly**: Can create "Buy X Get Y" promotions via UI
3. **Flexible**: JSON rules allow complex scenarios
4. **Extensible**: Easy to add more promotion types (tiered, bundle)
5. **Backward Compatible**: Existing simple_discount promotions work as-is

---

## RECOMMENDATION

**Implement Option 1: Extend promotion_campaigns with promotion_type** ✅

This approach:
- ✅ Handles "Buy X Get Y Free" scenarios
- ✅ Keeps database-driven approach (no Python hooks)
- ✅ Extensible for future promotion types
- ✅ Business user friendly
- ✅ No need for CampaignHookConfig

---

## NEXT STEPS

1. **User Approval**: Confirm this design meets business needs
2. **Create Migration**: Add `promotion_type` and `promotion_rules` columns
3. **Implement Backend**: `handle_buy_x_get_y()` method
4. **Test**: Create sample promotions and test scenarios
5. **Frontend**: Admin UI for creating Buy X Get Y promotions

---

**Document Created**: 21-November-2025, 11:10 PM IST
**Author**: Claude Code (AI Assistant)
**Status**: AWAITING USER APPROVAL

---

## QUESTIONS FOR USER

1. Does this design handle your "Buy high-value service → free consultation/product" scenario?
2. Should the free item be **auto-added** to invoice or **suggested** to user?
3. Are there other complex promotion types you need (tiered discounts, bundles)?
4. Shall we proceed with implementation?

---

**END OF DESIGN DOCUMENT**
