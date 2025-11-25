# Campaign Hook vs Promotion Campaign - Technical Note
## Date: 21-November-2025
## Status: ARCHITECTURAL DECISION NEEDED

---

## OVERVIEW

Two campaign/promotion systems exist in the codebase:

1. **CampaignHookConfig** (OLD): Python-based campaign hooks
2. **promotion_campaigns** (NEW): Database-driven promotions

---

## COMPARISON

| Feature | CampaignHookConfig (OLD) | promotion_campaigns (NEW) |
|---------|--------------------------|---------------------------|
| **Configuration** | Requires Python code/modules | Pure database configuration |
| **Who Can Create** | Developers only | Business users via UI |
| **Discount Logic** | Custom Python function | Fixed: percentage OR fixed_amount |
| **Complexity** | High | Low |
| **Flexibility** | Very high (any logic) | Medium (standard patterns) |
| **Maintenance** | Developer-dependent | Self-service |
| **Used By** | `calculate_campaign_discount()` | `calculate_promotion_discount()` |
| **Status** | NOT USED in multi-discount | ACTIVE in multi-discount |

---

## CURRENT STATE

### CampaignHookConfig Table
**Location**: `app/models/config.py` (if it exists)

**Fields**:
- hook_name, hook_module, hook_function
- effective_from, effective_to
- applies_to_services, applies_to_medicines
- priority

**Current Usage**: ❌ NOT USED
- The old `calculate_campaign_discount()` method checks for this table
- But returns `None` if `CampaignHookConfig is None` (line 487-488)
- Multi-discount system does NOT use this method

---

### promotion_campaigns Table ✅
**Location**: `app/models/master.py:881-921`

**Fields**:
- campaign_name, campaign_code, description
- start_date, end_date, is_active
- discount_type ('percentage' OR 'fixed_amount')
- discount_value
- applies_to ('all', 'services', 'medicines', 'packages')
- specific_items (JSONB array of item_ids)
- min_purchase_amount, max_discount_amount
- max_uses_per_patient, max_total_uses, current_uses
- auto_apply

**Current Usage**: ✅ ACTIVE
- Used by `calculate_promotion_discount()` (line 525-645)
- Integrated into multi-discount priority system
- Highest priority (1) in `get_best_discount_multi()`

---

## FIELD NAME COLLISION: `campaign_hook_id`

### Problem
The `DiscountCalculationResult` class has a field `campaign_hook_id`:
```python
class DiscountCalculationResult:
    def __init__(self, ..., campaign_hook_id: str = None):
        self.campaign_hook_id = campaign_hook_id
```

This field is now being **reused** to store `promotion_campaigns.campaign_id` in the new system:
```python
# In calculate_promotion_discount() - line 631
return DiscountCalculationResult(
    ...,
    campaign_hook_id=str(promotion.campaign_id),  # Actually a promotion_campaign_id!
    ...
)
```

### Impact
- Field name is misleading (`campaign_hook_id` suggests it's for hooks, not promotions)
- Works correctly but confusing for developers
- `DiscountApplicationLog` table also has this field (reused for promotion tracking)

---

## RECOMMENDED ACTIONS

### Option 1: Keep Both Systems (Hybrid Approach)
**Use Case**: Support both simple and complex campaigns

**Implementation**:
1. **Simple promotions** → Use `promotion_campaigns`
   - Standard percentage discounts
   - Fixed amount discounts
   - Time-bound offers
   - Usage limits

2. **Complex campaigns** → Use `CampaignHookConfig`
   - "Buy X get Y free"
   - "Spend $100, get 10% off next purchase"
   - Custom eligibility logic
   - Complex business rules

**Pros**:
- Maximum flexibility
- Supports both simple and complex scenarios
- No migration needed

**Cons**:
- Two systems to maintain
- More complex for developers
- Business users confused about which system to use

**Code Changes Needed**:
- Implement `CampaignHookConfig` table if not exists
- Create campaign hook loader/executor
- Update `calculate_campaign_discount()` to work with hooks
- Add hooks to priority logic (decide where they fit)

---

### Option 2: Deprecate CampaignHookConfig (Recommended ✅)
**Use Case**: Simplify architecture, focus on database-driven promotions

**Implementation**:
1. **Remove CampaignHookConfig entirely**
   - Delete table definition (if exists)
   - Remove `calculate_campaign_discount()` method
   - Remove try/except import block

2. **Rename misleading field**
   - `campaign_hook_id` → `campaign_id` or `promotion_id`
   - Update `DiscountCalculationResult` class
   - Update `DiscountApplicationLog` table

3. **Extend promotion_campaigns for advanced use cases**
   - Add `promotion_type` field: 'discount', 'bogo', 'tiered'
   - Add `promotion_rules` JSONB field for complex logic
   - Implement in application logic (not Python hooks)

**Pros**:
- Simpler architecture
- One system to maintain
- Business users empowered
- Clearer codebase

**Cons**:
- Less flexibility for truly custom campaigns
- Advanced scenarios need more planning
- Migration work needed

**Code Changes Needed**:
```python
# 1. Rename field in DiscountCalculationResult
class DiscountCalculationResult:
    def __init__(self, ..., promotion_id: str = None):  # Was: campaign_hook_id
        self.promotion_id = promotion_id

# 2. Update discount_service.py
# Line 631 - Already correct logic, just rename parameter
return DiscountCalculationResult(
    ...,
    promotion_id=str(promotion.campaign_id),  # Was: campaign_hook_id
    ...
)

# 3. Migration to rename column
ALTER TABLE discount_application_log
RENAME COLUMN campaign_hook_id TO promotion_id;

# 4. Remove old method
# Delete calculate_campaign_discount() method (lines 458-523)
```

---

### Option 3: Do Nothing (Current State)
**Use Case**: It works, don't fix what isn't broken

**Pros**:
- No work required
- System functional

**Cons**:
- Confusing field names
- Dead code in repository (CampaignHookConfig)
- Technical debt accumulating

---

## DECISION MATRIX

| Criteria | Option 1: Hybrid | Option 2: Deprecate | Option 3: Do Nothing |
|----------|-----------------|---------------------|----------------------|
| **Simplicity** | ❌ Complex | ✅ Simple | ⚠️ Confusing |
| **Flexibility** | ✅ Maximum | ⚠️ Limited | ⚠️ Limited |
| **Maintainability** | ❌ Two systems | ✅ One system | ⚠️ Dead code |
| **Business User Friendly** | ⚠️ Confusing | ✅ Clear | ⚠️ Confusing |
| **Developer Effort** | 🔴 High | 🟡 Medium | 🟢 None |
| **Technical Debt** | 🟡 Medium | 🟢 Low | 🔴 High |

---

## RECOMMENDATION: Option 2 (Deprecate CampaignHookConfig) ✅

### Rationale
1. **Simplicity**: One system easier to understand and maintain
2. **Business User Empowerment**: Non-technical users can create promotions
3. **Scalability**: Database-driven approach scales better
4. **Future-Proof**: Can extend `promotion_campaigns` table as needed

### Implementation Plan

#### Phase 1: Clean Up (Immediate)
1. Remove `CampaignHookConfig` import try/except block
2. Mark `calculate_campaign_discount()` as deprecated
3. Document that `campaign_hook_id` is actually `promotion_id`

#### Phase 2: Rename (Short-term)
1. Create migration to rename `campaign_hook_id` → `promotion_id`
2. Update `DiscountCalculationResult` class
3. Update all references in codebase
4. Run tests

#### Phase 3: Remove Dead Code (Medium-term)
1. Delete `calculate_campaign_discount()` method
2. Remove `CampaignHookConfig` table (if exists)
3. Update documentation

---

## MIGRATION SCRIPT (If Choosing Option 2)

```sql
-- Migration: Rename campaign_hook_id to promotion_id
-- Date: TBD
-- Description: Clean up field naming after removing CampaignHookConfig

-- 1. Rename column in discount_application_log
ALTER TABLE discount_application_log
RENAME COLUMN campaign_hook_id TO promotion_id;

-- 2. Add comment
COMMENT ON COLUMN discount_application_log.promotion_id IS
'Reference to promotion_campaigns.campaign_id (was: campaign_hook_id)';

-- Verification
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'discount_application_log'
  AND column_name = 'promotion_id';
```

```python
# Update DiscountCalculationResult class
class DiscountCalculationResult:
    """Data class to hold discount calculation results"""
    def __init__(
        self,
        discount_type: str,
        discount_percent: Decimal,
        discount_amount: Decimal,
        final_price: Decimal,
        original_price: Decimal,
        metadata: Dict = None,
        card_type_id: str = None,
        promotion_id: str = None  # RENAMED from campaign_hook_id
    ):
        self.discount_type = discount_type
        self.discount_percent = discount_percent
        self.discount_amount = discount_amount
        self.final_price = final_price
        self.original_price = original_price
        self.metadata = metadata or {}
        self.card_type_id = card_type_id
        self.promotion_id = promotion_id  # RENAMED

    def to_dict(self) -> Dict:
        return {
            'discount_type': self.discount_type,
            'discount_percent': float(self.discount_percent),
            'discount_amount': float(self.discount_amount),
            'final_price': float(self.final_price),
            'original_price': float(self.original_price),
            'metadata': self.metadata,
            'card_type_id': str(self.card_type_id) if self.card_type_id else None,
            'promotion_id': str(self.promotion_id) if self.promotion_id else None  # RENAMED
        }
```

---

## IMPACT ANALYSIS

### If We Keep CampaignHookConfig (Option 1)
**Affected Code**:
- Need to implement `CampaignHookConfig` model
- Need to create campaign hook loader
- Need to integrate into multi-discount priority
- Need UI for managing hooks (developer-only)

**Estimated Effort**: 8-12 hours

---

### If We Deprecate CampaignHookConfig (Option 2)
**Affected Code**:
- `DiscountCalculationResult` class (line 25-58)
- `calculate_promotion_discount()` return statement (line 625)
- `discount_application_log` table
- All references to `campaign_hook_id` in API responses

**Estimated Effort**: 2-4 hours

---

### If We Do Nothing (Option 3)
**Affected Code**: None

**Estimated Effort**: 0 hours

**Technical Debt**: Accumulating (confusing field names, dead code)

---

## FINAL RECOMMENDATION

**Choose Option 2: Deprecate CampaignHookConfig**

**Reasoning**:
1. The new `promotion_campaigns` table covers 95% of use cases
2. Simpler architecture is easier to maintain
3. Business users empowered to create promotions without developer help
4. Field renaming improves code clarity
5. Can always add Python hooks later if truly needed

**Next Steps**:
1. Get user approval for Option 2
2. Create migration script for field renaming
3. Update DiscountCalculationResult class
4. Run tests
5. Update documentation
6. Remove dead code (calculate_campaign_discount method)

---

**Document Created**: 21-November-2025, 11:05 PM IST
**Author**: Claude Code (AI Assistant)
**Status**: AWAITING USER DECISION

---

## QUESTIONS FOR USER

1. Do you want to **keep** or **remove** the CampaignHookConfig system?
2. If keeping: When would you use hooks vs promotions?
3. If removing: Shall we rename `campaign_hook_id` → `promotion_id` now or later?
4. Are there any complex campaign scenarios that `promotion_campaigns` table cannot handle?

---

**END OF TECHNICAL NOTE**
