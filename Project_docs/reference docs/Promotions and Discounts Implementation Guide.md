# Promotions and Discounts Implementation Guide

## SkinSpire Clinic HMS - Comprehensive Documentation

**Version:** 1.6
**Date:** December 2, 2025
**Author:** Development Team

---

## Table of Contents

1. [Executive Overview](#1-executive-overview)
2. [Business Logic](#2-business-logic)
   - 2.1-2.4 Discount Hierarchy and Modes
   - 2.5 Buy X Get Y - Complete Implementation
3. [Discount Types and Calculations](#3-discount-types-and-calculations)
4. [Discount Stacking Configuration](#4-discount-stacking-configuration)
5. [Validated Test Scenarios](#5-validated-test-scenarios)
6. [Centralized Architecture](#6-centralized-architecture)
7. [Invoice-Level Discounts (VIP & Staff Discretionary)](#7-invoice-level-discounts-vip--staff-discretionary)
8. [Free Items and Sample/Trial Items](#8-free-items-and-sampletrial-items)
9. [Campaign Management](#9-campaign-management)
   - 9.1-9.4 Campaign Structure, Groups, Workflow
   - 9.5 Campaign Cards in Invoice Creation
   - 9.6 Hospital Discount Stacking Settings UI
10. [Database Schema](#10-database-schema)
11. [Key Services and Components](#11-key-services-and-components)
12. [Frontend Components](#12-frontend-components)
13. [Configuration and Settings](#13-configuration-and-settings)
14. [Integration Points](#14-integration-points)
15. [Maintenance and Troubleshooting](#15-maintenance-and-troubleshooting)

---

## 1. Executive Overview

### 1.1 Purpose

The Promotions and Discounts module provides a comprehensive system for:
- Creating and managing marketing campaigns
- Applying various types of discounts to patient invoices
- Configuring how discounts stack/combine at the organization level
- Simulating discount outcomes for planning purposes
- Tracking promotion effectiveness and analytics

### 1.2 Key Features

- **Four Discount Types**: Campaign, Bulk, Loyalty, VIP
- **Three Campaign Discount Modes**: Percentage, Fixed Amount, Buy X Get Y
- **Configurable Stacking**: Organization-level control over how discounts combine
- **Campaign Groups**: Group related campaigns for streamlined management
- **Approval Workflow**: Multi-level approval for campaign creation
- **Timeline Visualization**: Visual planning with holiday/weekend awareness
- **Patient-Specific Targeting**: VIP, personalized, and group-based campaigns

---

## 2. Business Logic

### 2.1 Discount Application Hierarchy

```
Total Discount = f(Campaign, Bulk, Loyalty, VIP) based on stacking configuration
```

The system supports three stacking modes per discount type:

| Mode | Behavior | Use Case |
|------|----------|----------|
| **Exclusive** | Only this discount applies; ALL others are excluded | VIP gets special treatment - no other discounts |
| **Incremental** | Discount always adds/stacks with others | Bulk + Loyalty should combine |
| **Absolute** | Competes with other absolutes (best wins), then STACKS with incrementals | Multiple promos - best promo wins, but still adds to bulk/loyalty |

**Mode Priority Logic:**
1. **EXCLUSIVE check first**: If ANY discount has `mode = exclusive` AND value > 0, the highest exclusive wins and ALL others are excluded
2. **If no exclusive**: All `incremental` discounts ADD together
3. **ABSOLUTE resolution**: Among `absolute` discounts, the HIGHEST wins. The winning absolute then ADDS to the incremental total
4. **Max cap**: Apply `max_total_discount` cap if configured

**Key Insight**: Absolute does NOT compete with incrementals - it competes with OTHER absolutes. The winner then stacks with incrementals.

### 2.2 Default Stacking Behavior

| Discount Type | Default Mode | Special Rules |
|---------------|--------------|---------------|
| Campaign | Exclusive | When exclusive, no other discounts apply |
| Bulk | Incremental | Can be excluded when campaign exists |
| Loyalty | Incremental | Based on patient tier (Bronze/Silver/Gold/Platinum) |
| VIP | Absolute | Competes with other absolute discounts |

### 2.3 Calculation Flow

```
1. Check if Campaign applies
   - If campaign.mode == 'exclusive': Return campaign discount only
   - If campaign.mode == 'incremental': Add to total, continue

2. Check Bulk discount
   - If bulk.exclude_with_campaign AND campaign exists: Skip
   - If bulk.mode == 'incremental': Add to total
   - If bulk.mode == 'absolute': Add to absolute candidates

3. Check Loyalty discount
   - If loyalty.mode == 'incremental': Add to total
   - If loyalty.mode == 'absolute': Add to absolute candidates

4. Check VIP discount
   - If vip.mode == 'incremental': Add to total
   - If vip.mode == 'absolute': Add to absolute candidates

5. Resolve absolute candidates (best one wins)

6. Apply max_total_discount cap if configured
```

### 2.4 Campaign Discount Types

#### Percentage Discount
- Standard percentage off item price
- Example: 10% off all services

#### Fixed Amount Discount
- Flat rupee amount off item price
- Example: Rs. 500 off facial treatment
- Comparison: Converted to equivalent percentage for comparison

#### Buy X Get Y
- Purchase X items, get Y items free/discounted
- **Important**: X items charged at list price (no discount)
- Y items receive full discount or specified discount
- Example: Buy 2 Get 1 Free
- **Supports multiple reward items** per campaign (e.g., Buy 1 Get 2 different items free)

### 2.5 Buy X Get Y - Complete Implementation

#### 2.5.1 End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BUY X GET Y - COMPLETE FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. CAMPAIGN LOADING (Invoice Page Load)                                     │
│     └── API: /api/discount/buy-x-get-y/active?hospital_id={id}&patient_id={id}│
│     └── Campaigns cached in window.eligibleCampaigns                        │
│     └── Displayed in "Eligible Campaigns" card with checkboxes              │
│                                                                              │
│  2. LINE ITEM CHANGE DETECTION (Real-time)                                   │
│     └── Events: line-item-added, line-item-removed, line-item-changed       │
│     └── BuyXGetYHandler debounces with 500ms timeout                        │
│     └── Collects all line items (excluding free items)                      │
│                                                                              │
│  3. TRIGGER VALIDATION                                                       │
│     └── Checks: Item Type, Item ID, Quantity/Amount minimums                │
│     └── Item type normalization: Service→service, OTC/Prescription→medicine │
│     └── Supports multiple triggers from different campaigns                 │
│                                                                              │
│  4. FREE ITEM ADDITION                                                       │
│     └── Creates new line item with data-isFreeItem="true"                   │
│     └── 100% discount, Unit price = original MRP (for GST compliance)       │
│     └── Disabled fields, green background, FREE badge                       │
│     └── Tracked in freeItemsMap to prevent duplicates                       │
│                                                                              │
│  5. CAMPAIGN CARD UPDATES                                                    │
│     └── Badge changes from "ELIGIBLE" to "APPLIED" (green)                  │
│     └── Shows trigger → reward details                                      │
│                                                                              │
│  6. DISCOUNT RECALCULATION                                                   │
│     └── BulkDiscountManager.updatePricing() called                          │
│     └── GST calculated on original MRP for tax compliance                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.5.2 Campaign Configuration (promotion_rules JSON)

```json
{
  "trigger": {
    "type": "item_purchase",
    "conditions": {
      "item_type": "Service|Medicine|Package",
      "item_ids": ["optional array of UUIDs"],
      "item_name": "optional display name",
      "min_quantity": 2,
      "min_amount": null
    }
  },
  "reward": {
    "items": [
      {
        "item_type": "Service",
        "item_id": "UUID",
        "item_name": "Free Consultation",
        "quantity": 1,
        "discount_percent": 100
      },
      {
        "item_type": "Medicine",
        "item_id": "UUID",
        "item_name": "Free Sample Cream",
        "quantity": 1,
        "discount_percent": 100
      }
    ]
  }
}
```

**Note**: Supports MULTIPLE reward items per campaign (array format).

#### 2.5.3 Free Item Business Rules

| Rule | Behavior |
|------|----------|
| **Discount** | Always 100% (or specified discount_percent) |
| **Unit Price** | Set to ORIGINAL MRP (not zero!) |
| **GST** | Calculated on original MRP (tax compliance) |
| **Line Total** | Rs. 0 (quantity × MRP × 0%) |
| **Visibility** | Yes - transparent to patient |
| **Editable** | No - fields disabled, remove button hidden |
| **Duplicates** | Prevented via freeItemsMap tracking |
| **Auto-cleanup** | Removed when trigger no longer met |

#### 2.5.4 Item Type Normalization

```javascript
// Frontend normalization for trigger matching
itemTypeMap = {
    'Service': 'service',
    'Package': 'package',
    'OTC': 'medicine',
    'Prescription': 'medicine',
    'Product': 'medicine',
    'Consumable': 'medicine'
}
```

#### 2.5.5 Example Scenario

**Campaign**: "Free Consultation when buying Skin Treatment"

```
User Action: Selects "Skin Treatment" (Rs. 1,000)

Invoice Display:
┌──────────────────────────────┬──────────┬──────────┬──────────┐
│ Item                         │ Rate     │ Discount │ Total    │
├──────────────────────────────┼──────────┼──────────┼──────────┤
│ Skin Treatment               │ ₹1,000   │ 0%       │ ₹1,000   │
├──────────────────────────────┼──────────┼──────────┼──────────┤
│ Free Consultation (FREE)     │ ₹500     │ 100%     │ ₹0       │
│ [🎁 FREE]                    │          │          │          │
└──────────────────────────────┴──────────┴──────────┴──────────┘
Subtotal: ₹1,000
GST (on ₹1,500 MRP): ₹270  ← GST calculated on both items
Total: ₹1,270

When user removes "Skin Treatment":
  → Free Consultation auto-removed
  → Campaign badge changes to "ELIGIBLE"
```

#### 2.5.6 Key Files

| File | Purpose |
|------|---------|
| `buy_x_get_y_handler.js` | Frontend BXGY logic, trigger validation, free item creation |
| `invoice_bulk_discount.js` | Discount calculations, API calls |
| `create_invoice.html` | Campaign cards rendering, toggle functions |
| `discount_service.py` | Backend calculations |
| `discount_api.py` | API endpoints |

---

## 3. Discount Types and Calculations

### 3.1 Campaign Discount

```python
# Location: app/services/discount_service.py

# Campaign discount can be:
# - percentage: Direct percentage value
# - fixed_amount: Converted to percentage = (amount / item_price) * 100
# - buy_x_get_y: X items = 0% discount, Y items = 100% (or specified)
```

### 3.2 Bulk Discount

Applied based on quantity thresholds defined at service/item level:

```python
# Example bulk discount rules
bulk_rules = [
    {"min_qty": 5, "discount_percent": 5},
    {"min_qty": 10, "discount_percent": 10},
    {"min_qty": 20, "discount_percent": 15}
]
```

### 3.3 Loyalty Discount

Based on patient loyalty tier:

| Tier | Typical Discount |
|------|-----------------|
| Bronze | 2% |
| Silver | 5% |
| Gold | 8% |
| Platinum | 12% |

### 3.4 VIP Discount

Special discount for VIP-tagged patients, typically used for:
- Corporate clients
- Influencers
- Long-term high-value patients

---

## 4. Discount Stacking Configuration

### 4.0 Quick Reference - Stacking Modes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STACKING MODES QUICK REFERENCE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXCLUSIVE                                                                   │
│  └── Only this discount applies. ALL others excluded.                       │
│      Example: VIP exclusive at 15% → No bulk, no loyalty, no promo          │
│                                                                              │
│  INCREMENTAL                                                                 │
│  └── Always adds/stacks with other discounts.                               │
│      Example: Bulk 15% + Loyalty 3% = 18% total                             │
│                                                                              │
│  ABSOLUTE                                                                    │
│  └── Competes with OTHER absolutes (best wins).                             │
│      Winner then STACKS with incrementals.                                   │
│      Example: Promo1 10% vs Promo2 18% → Promo2 wins                        │
│               Promo2 18% + Bulk 15% + Loyalty 3% = 36% total                │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  TYPICAL CONFIGURATION (Skinspire Clinic):                                   │
│    VIP:      exclusive  → VIP patients get only VIP discount                │
│    Campaign: absolute   → Best promo wins, stacks with bulk/loyalty         │
│    Bulk:     incremental → Always stacks                                     │
│    Loyalty:  incremental → Always stacks                                     │
│    Max Cap:  50%         → Total never exceeds 50%                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Configuration Schema

```json
{
  "campaign": {
    "mode": "exclusive|incremental|absolute",
    "buy_x_get_y_exclusive": true
  },
  "loyalty": {
    "mode": "exclusive|incremental|absolute"
  },
  "bulk": {
    "mode": "exclusive|incremental|absolute",
    "exclude_with_campaign": true
  },
  "vip": {
    "mode": "exclusive|incremental|absolute"
  },
  "max_total_discount": 50
}
```

**Note:** All four discount types support all three modes. The `exclusive` mode for any type means if that discount applies, no other discounts will be applied.

### 4.2 Configuration Location

**Database**: `hospitals.discount_stacking_config` (JSONB column)

**UI**: Admin > Hospital Settings > Discount Stacking Configuration

### 4.3 Example Scenarios

**Scenario 1: Exclusive Campaign**
- Config: Campaign mode = exclusive
- Discounts: Campaign 15%, Bulk 5%, Loyalty 3%, VIP 10%
- **Result**: 15% (only campaign applies)

**Scenario 2: Incremental Campaign with Absolute VIP**
- Config: Campaign = incremental, Loyalty = incremental, VIP = absolute
- Discounts: Campaign 10%, Loyalty 3%, VIP 15%
- **Result**: 10% + 3% + 15% = 28%

**Scenario 3: With Max Cap**
- Config: All incremental, max_total_discount = 25%
- Discounts: Campaign 10%, Bulk 5%, Loyalty 5%, VIP 10%
- Calculated: 30%, **Result**: 25% (capped)

---

## 5. Validated Test Scenarios

All scenarios below have been tested and validated using `test_discount_stacking_scenarios.py`.

### 5.1 Complete Test Results Matrix

| # | Scenario | Configuration | Discounts Available | Expected | Status |
|---|----------|---------------|---------------------|----------|--------|
| 1 | Exclusive Campaign | Campaign=exclusive | C:15%, B:5%, L:3%, V:10% | **15%** | PASS |
| 2 | All Incremental | All=incremental | C:10%, B:5%, L:3%, V:8% | **26%** | PASS |
| 3 | Bulk Excluded with Campaign | bulk.exclude_with_campaign=true | C:10%, B:5%, L:3%, V:8% | **21%** | PASS |
| 4 | VIP Absolute Mode | VIP=absolute, others=incremental | C:10%, B:5%, L:3%, V:20% | **33%** | PASS |
| 5 | Multiple Absolute (VIP wins) | L&V=absolute | C:10%, L:8%, V:15% | **25%** | PASS |
| 6 | Max Cap Applied | cap=25% | C:15%, B:5%, L:5%, V:10% | **25%** | PASS |
| 7 | Fixed Amount Campaign | Rs.500 on Rs.2500 item | C:Rs500, L:3%, V:10% | **33%** | PASS |
| 8 | Standard Fallback | No other discounts | Standard:5% | **5%** | PASS |
| 9 | No Discounts | All zeros | None | **0%** | PASS |
| 10 | Buy X Get Y | Buy 2 Get 1 (33.33% effective) | C:33.33%, L:3%, V:10% | **46.33%** | PASS |
| 11 | Loyalty loses to VIP | L&V both absolute | C:10%, B:5%, L:8%, V:12% | **27%** | PASS |
| 12 | Only Bulk + Loyalty | No campaign, no VIP | B:7%, L:5% | **12%** | PASS |
| 13 | High Discounts + Cap | cap=50% | C:30%, B:15%, L:10%, V:20% | **50%** | PASS |
| 14 | All Absolute (VIP wins) | B,L,V all absolute | C:10%, B:8%, L:6%, V:15% | **25%** | PASS |
| 15 | Campaign Only | Single discount | C:20% only | **20%** | PASS |

**Legend**: C=Campaign, B=Bulk, L=Loyalty, V=VIP

### 5.2 Key Validated Behaviors

#### 5.2.1 Exclusive Mode
When campaign mode = `exclusive`, **only the campaign discount applies**. All other discounts (bulk, loyalty, VIP) are excluded regardless of their values.

```
Input:  Campaign 15% (exclusive), Bulk 5%, Loyalty 3%, VIP 10%
Output: 15% total
        Excluded: Bulk (Campaign is exclusive)
        Excluded: Loyalty (Campaign is exclusive)
        Excluded: VIP (Campaign is exclusive)
```

#### 5.2.2 Incremental Stacking
When all discounts are in `incremental` mode, they **add together**: Campaign + Bulk + Loyalty + VIP.

```
Input:  Campaign 10%, Bulk 5%, Loyalty 3%, VIP 8% (all incremental)
Output: 26% total (10 + 5 + 3 + 8)
```

#### 5.2.3 Bulk Exclusion with Campaign
When `bulk.exclude_with_campaign = true`, bulk discount is **automatically skipped** if any campaign discount applies.

```
Input:  Campaign 10%, Bulk 5% (exclude_with_campaign=true), Loyalty 3%, VIP 8%
Output: 21% total (10 + 3 + 8, bulk excluded)
        Excluded: Bulk (Excluded when campaign applies)
```

#### 5.2.4 Absolute Mode Competition
When multiple discounts are in `absolute` mode, **only the highest percentage wins**. Lower values are excluded with detailed comparison reason.

```
Input:  Campaign 10% (incremental), Bulk 8% (absolute), Loyalty 6% (absolute), VIP 15% (absolute)
Output: 25% total (10 + 15)
        Applied: Campaign 10%, VIP 15% (absolute winner)
        Excluded: Bulk (Lower than vip: 8% < 15%)
        Excluded: Loyalty (Lower than vip: 6% < 15%)
```

#### 5.2.5 Max Discount Cap
When `max_total_discount` is configured, the total discount is **hard capped** at that value. The breakdown shows the original calculated value before capping.

```
Input:  Campaign 30%, Bulk 15%, Loyalty 10%, VIP 20% (all incremental, cap=50%)
Output: 50% total (capped from 75%)
        Breakdown shows: "capped from 75.0%"
```

#### 5.2.6 Fixed Amount to Percentage Conversion
Fixed amount discounts are **converted to percentage** based on item price for comparison and stacking:

```
Formula: percentage = (fixed_amount / item_price) * 100

Example: Rs.500 discount on Rs.2500 item
         percentage = (500 / 2500) * 100 = 20%
```

#### 5.2.7 Buy X Get Y Effective Discount
Buy X Get Y campaigns use `effective_percent` to represent the average discount across all qualifying items:

```
Buy 2 Get 1 Free:
  - X (2) items: Charged at full price (0% discount)
  - Y (1) item: Free (100% discount)
  - Effective: 33.33% average discount across 3 items

This effective_percent stacks with other incremental discounts.
```

#### 5.2.8 Standard Discount Fallback
If no other discounts apply (all zeros), the **standard discount** is used as a fallback:

```
Input:  Campaign 0%, Bulk 0%, Loyalty 0%, VIP 0%, Standard 5%
Output: 5% total (standard fallback)
```

### 5.3 Mixed Mode Configuration Scenario

This scenario demonstrates how the stacking logic works with a realistic mixed configuration:

**Configuration:**
- VIP: **Exclusive** (if VIP discount applies, nothing else stacks)
- Loyalty: **Incremental** (always adds to total)
- Campaign: **Absolute** (competes with other absolutes, winner adds to incrementals)
- Bulk: **Incremental** (always adds to total)

**Scenario Analysis:**

| # | Discounts Available | Calculation | Result |
|---|---------------------|-------------|--------|
| 1 | VIP 15%, Campaign 10%, Loyalty 5%, Bulk 3% | VIP is exclusive = **15% only** | **15%** |
| 2 | Campaign 10%, Loyalty 5%, Bulk 3% (no VIP) | Incrementals (L+B) + Absolute(C) = 5+3+10 | **18%** |
| 3 | Campaign 10%, Loyalty 5% (no VIP, no Bulk) | Incremental (5%) + Absolute (10%) | **15%** |
| 4 | Campaign 10%, Bulk 3% (no VIP, no Loyalty) | Incremental (3%) + Absolute (10%) | **13%** |
| 5 | VIP 15% only | VIP exclusive = 15% | **15%** |
| 6 | Campaign 8%, Loyalty 3% + Max Cap 10% | Incremental (3%) + Absolute (8%) = 11%, capped | **10%** |

**Key Insight: Mode Priority**

```
IF any discount has mode='exclusive' AND value > 0:
    → Highest exclusive wins, ALL others excluded
ELSE:
    → All incrementals ADD together
    → Among absolutes, HIGHEST WINS and adds to incrementals total
    → Apply max cap if configured
```

**Code Flow:**
```
Step 1: Check for EXCLUSIVE discounts
        └── If found: Pick highest exclusive, exclude all others, DONE

Step 2: If no exclusive:
        ├── Add all INCREMENTAL discounts together
        └── Pick best ABSOLUTE discount, add to total

Step 3: Apply max_total_discount cap if configured
```

### 5.4 Running the Test Suite

The test file is located at: `test_discount_stacking_scenarios.py`

```bash
# Run all tests
python test_discount_stacking_scenarios.py

# Expected output:
# Total Tests: 15
# Passed: 15
# Failed: 0
# Success Rate: 100.0%
# ALL TESTS PASSED!
```

### 5.5 Adding New Test Scenarios

To add new test scenarios, follow this template in `test_discount_stacking_scenarios.py`:

```python
# =========================================================================
# SCENARIO N: Description
# =========================================================================
config_n = {
    'campaign': {'mode': 'exclusive|incremental', 'buy_x_get_y_exclusive': True},
    'loyalty': {'mode': 'incremental|absolute'},
    'bulk': {'mode': 'incremental|absolute', 'exclude_with_campaign': True|False},
    'vip': {'mode': 'absolute|incremental'},
    'max_total_discount': None|50  # Optional cap
}

discounts_n = {
    'campaign': {'percent': 10, 'type': 'percentage', 'name': 'Campaign Name'},
    'bulk': {'percent': 5},
    'loyalty': {'percent': 3, 'card_type': 'Gold'},
    'vip': {'percent': 15}
}

result_n = DiscountService.calculate_stacked_discount(discounts_n, config_n)
results.append(print_result(
    "N. Scenario Description",
    result_n,
    expected=XX.X  # Expected total percentage
))
```

---

## 6. Centralized Architecture

### 6.1 Overview

The discount calculation system follows a **Single Source of Truth** architecture. All discount calculations flow through centralized methods in `DiscountService`, ensuring consistency across all contexts (Invoice, Dashboard Simulation, API).

```
┌─────────────────────────────────────────────────────────────────┐
│           DiscountService (SINGLE SOURCE OF TRUTH)              │
├─────────────────────────────────────────────────────────────────┤
│ Core Calculation Methods:                                       │
│  • calculate_bulk_discount()           - Invoice (actual qty)   │
│  • calculate_bulk_discount_simulation() - Dashboard (assumed)   │
│  • calculate_loyalty_percentage_discount()                      │
│  • calculate_standard_discount()                                │
│  • calculate_promotion_discount()                               │
│  • calculate_vip_discount()                                     │
│  • calculate_stacked_discount()        - Stacking logic         │
├─────────────────────────────────────────────────────────────────┤
│ Orchestration:                                                  │
│  • get_best_discount_multi(simulation_mode=False)  - Invoice    │
│  • get_best_discount_multi(simulation_mode=True)   - Dashboard  │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
┌───────────────────────────┐    ┌───────────────────────────────┐
│   INVOICE CONTEXT          │    │   SIMULATION CONTEXT          │
│                            │    │                               │
│ • Actual qty check         │    │ • Assumes bulk eligible       │
│ • Staff overrides apply    │    │ • No overrides                │
│   (exclude_bulk/loyalty)   │    │ • Shows potential savings     │
│ • Final discount to items  │    │ • What-if analysis            │
└───────────────────────────┘    └───────────────────────────────┘
```

### 6.2 Context Differences

| Aspect | Invoice Context | Simulation Context |
|--------|-----------------|-------------------|
| **Bulk Eligibility** | Checks actual item quantities against threshold | Assumes eligible if item has bulk_discount_percent > 0 |
| **Staff Override** | Checkboxes allow staff to exclude bulk/loyalty | Not applicable |
| **Purpose** | Final discount applied to invoice | Preview potential savings |
| **Method** | `get_best_discount_multi(simulation_mode=False)` | `get_best_discount_multi(simulation_mode=True)` |

### 6.3 Core Calculation Methods

**Location**: `app/services/discount_service.py`

#### 6.3.1 Individual Discount Calculators

```python
# Bulk discount for invoice (checks actual quantities)
calculate_bulk_discount(session, hospital_id, service_id, total_item_count, unit_price, quantity)

# Bulk discount for simulation (assumes eligible)
calculate_bulk_discount_simulation(session, hospital_id, item_type, item_id, unit_price, quantity)

# Loyalty discount (uses card_type.discount_percent - published rate)
calculate_loyalty_percentage_discount(session, hospital_id, patient_id, item_type, item_id, unit_price, quantity)

# Standard discount (fallback)
calculate_standard_discount(session, item_type, item_id, unit_price, quantity)

# Campaign/Promotion discount
calculate_promotion_discount(session, hospital_id, patient_id, item_type, item_id, unit_price, quantity, invoice_date)

# VIP discount
calculate_vip_discount(session, hospital_id, patient_id, item_type, item_id, unit_price, quantity)
```

#### 6.3.2 Orchestration Method

```python
def get_best_discount_multi(
    session, hospital_id, patient_id, item_type, item_id,
    unit_price, quantity, total_item_count,
    invoice_date=None, invoice_items=None,
    exclude_bulk=False,      # Staff override: skip bulk
    exclude_loyalty=False,   # Staff override: skip loyalty
    simulation_mode=False    # True for dashboard simulation
) -> DiscountCalculationResult:
    """
    Central orchestrator that:
    1. Calls all individual discount calculators
    2. Applies stacking configuration
    3. Returns final calculated discount

    Context Handling:
    - simulation_mode=False: Invoice context (actual qty check, overrides apply)
    - simulation_mode=True: Dashboard context (assumes eligible, no overrides)
    """
```

### 6.4 Staff Override Mechanism

Staff can override proposed discounts via checkboxes in the invoice UI:

```
┌─────────────────────────────────────────────┐
│  Pricing and Discount Control (Staff View)  │
├─────────────────────────────────────────────┤
│  ☑ Apply Bulk Discount      (15%)          │
│  ☑ Apply Loyalty Discount   (3%)           │
│  ☐ Apply Campaign Discount  (10%)          │
│  ☑ Apply VIP Discount       (5%)           │
└─────────────────────────────────────────────┘
```

**Flow when staff unchecks a checkbox:**

1. Frontend sets `userToggledCheckbox = true` (for bulk) or `userToggledLoyaltyCheckbox = true`
2. API request includes `exclude_bulk: true` or `exclude_loyalty: true`
3. Backend skips that discount type in calculation
4. Line items updated without that discount

**Implementation:**

```javascript
// Frontend: invoice_bulk_discount.js
const excludeBulk = !isEligible || (this.userToggledCheckbox && !checkbox.checked);
const excludeLoyalty = this.userToggledLoyaltyCheckbox && loyaltyCheckbox && !loyaltyCheckbox.checked;

await this.applyDiscounts(lineItems, { excludeBulk, excludeLoyalty });
```

```python
# Backend: discount_service.py
if not exclude_bulk:
    bulk_discount = calculate_bulk_discount(...)
else:
    logger.info("Bulk discount excluded by staff override")

if not exclude_loyalty:
    loyalty_discount = calculate_loyalty_percentage_discount(...)
else:
    logger.info("Loyalty discount excluded by staff override")
```

### 6.5 Loyalty Discount Source

**Important**: Loyalty discount uses the **card type's published rate**, not the service-level field.

| Field | Location | Usage |
|-------|----------|-------|
| `discount_percent` | `loyalty_card_types` table | **USED** - Published rate for card type (e.g., Gold = 3%) |
| `loyalty_discount_percent` | `services` table | **NOT USED** - Legacy field, kept for backward compatibility |

This ensures loyalty discount is:
- Same for all services/medicines
- Published and transparent to patients
- Consistent across invoice and simulation

### 6.6 Bulk Discount Eligibility

**Invoice Context:**
- Checks `total_item_count >= hospital.bulk_discount_min_service_count`
- Only applies if threshold is met

**Simulation Context:**
- Assumes eligible if `item.bulk_discount_percent > 0`
- Shows "Requires min X items" in reason

**Dynamic Recalculation:**
- When line items are added/removed, bulk eligibility is rechecked
- `line-item-removed` event triggers `updatePricing()`
- If count drops below threshold, bulk discount is removed and checkbox is reset

### 6.7 Files Modified for Centralization

| File | Changes |
|------|---------|
| `discount_service.py` | Added `simulation_mode`, `exclude_bulk`, `exclude_loyalty` params; Created `calculate_bulk_discount_simulation()` |
| `promotion_dashboard_service.py` | Replaced inline calculations with calls to centralized methods |
| `discount_api.py` | Passes override flags to service layer |
| `invoice_bulk_discount.js` | Tracks user toggles, passes `excludeBulk`/`excludeLoyalty` in API requests |
| `invoice_item.js` | Dispatches `line-item-removed` event for recalculation |

---

## 7. Invoice-Level Discounts (VIP & Staff Discretionary)

### 7.1 Two-Tier Discount Architecture

The discount system operates at two levels:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DISCOUNT CALCULATION FLOW                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TIER 1: LINE-ITEM LEVEL                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ For each item in invoice:                                        │   │
│  │   • Campaign Discount (promo)                                    │   │
│  │   • Bulk Discount (quantity-based)                               │   │
│  │   • Loyalty Discount (card tier)                                 │   │
│  │   • Standard Discount (fallback)                                 │   │
│  │                                                                   │   │
│  │ Stacking: Based on hospital's discount_stacking_config           │   │
│  │ Result: Line-item discount applied to each item                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│  TIER 2: INVOICE LEVEL                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Applied on subtotal (after line-item discounts):                 │   │
│  │   • VIP Discount (for VIP/Special Group patients)                │   │
│  │   • Staff Discretionary Discount (manual override)               │   │
│  │                                                                   │   │
│  │ Stacking: VIP mode determines behavior (exclusive/absolute/inc)  │   │
│  │ Result: Additional discount on invoice total                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│                      FINAL INVOICE TOTAL                                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 VIP Discount at Invoice Level

VIP discount is applied at the INVOICE level (not per line-item) for patients marked as `is_special_group = true`.

#### 7.2.1 VIP Stacking Modes

| VIP Mode | Behavior | Example |
|----------|----------|---------|
| **exclusive** | VIP replaces ALL line-item discounts | Line items show 0% discount, only VIP % on total |
| **absolute** | VIP competes with line-item total (better wins) | If VIP 15% > line discounts 10%, VIP adds 5% more |
| **incremental** | VIP stacks on top of line-item discounts | Line discounts + VIP both apply |

#### 7.2.2 VIP Exclusive Mode Flow

When VIP mode is `exclusive` and patient is VIP:

```
1. Line-item discounts are calculated (Campaign 10%, Bulk 5%, etc.)
2. VIP exclusive kicks in at invoice level
3. ALL line-item discounts are ZEROED OUT
4. VIP discount applies on ORIGINAL total price
5. Result: Only VIP discount is shown

Example:
  Original Price: Rs. 10,000
  Line-item Discounts: Rs. 1,500 (15% from bulk+campaign)
  VIP Discount: 20%

  WITH VIP EXCLUSIVE:
    Line-item discount: Rs. 0 (cleared)
    VIP discount: Rs. 2,000 (20% of 10,000)
    Final: Rs. 8,000
```

#### 7.2.3 VIP Absolute Mode Flow

When VIP mode is `absolute`:

```
1. Calculate VIP discount on original price
2. Compare with line-item discount total
3. If VIP is better, add the DIFFERENCE as additional discount
4. If line-item is better, VIP adds nothing

Example:
  Original Price: Rs. 10,000
  Line-item Discounts: Rs. 1,000 (10%)
  VIP Discount: 15% = Rs. 1,500

  VIP (1,500) > Line-item (1,000)
  Additional VIP discount: Rs. 500 (1,500 - 1,000)
  Final: Rs. 8,500
```

#### 7.2.4 VIP Incremental Mode Flow

When VIP mode is `incremental`:

```
1. Apply line-item discounts first
2. Calculate VIP on SUBTOTAL (after line-item discounts)
3. Add VIP discount to total

Example:
  Original Price: Rs. 10,000
  Line-item Discounts: Rs. 1,000 (10%)
  Subtotal: Rs. 9,000
  VIP Discount: 15% of Rs. 9,000 = Rs. 1,350

  Total discount: Rs. 1,000 + Rs. 1,350 = Rs. 2,350
  Final: Rs. 7,650
```

### 7.3 Staff Discretionary Discount

Staff discretionary discount is a manual percentage discount that staff can apply on top of all other discounts.

```
Flow:
1. Line-item discounts applied
2. VIP discount applied (if applicable)
3. Staff Discretionary applied on remaining subtotal

Example:
  Original: Rs. 10,000
  Line-item: Rs. 1,000 (10%)
  VIP: Rs. 450 (5% of 9,000)
  Subtotal after VIP: Rs. 8,550
  Staff Discretionary: 10% of Rs. 8,550 = Rs. 855

  Final: Rs. 7,695
```

### 7.4 Manual Override via Checkbox

Staff can manually disable VIP discount using a checkbox in the invoice UI:

```
┌─────────────────────────────────────────────┐
│  Invoice-Level Discounts                     │
├─────────────────────────────────────────────┤
│  ☑ Apply VIP Discount         (15%)         │
│  ☑ Staff Discretionary        (5%)          │
└─────────────────────────────────────────────┘
```

**When VIP checkbox is unchecked:**
1. Frontend sends `vip_discount: {enabled: false}`
2. Backend sets `exclude_vip = true`
3. VIP discount is NOT calculated at line-item level
4. VIP invoice-level handling is skipped
5. Other discounts (Campaign, Bulk, Loyalty) apply normally

### 7.5 Implementation Details

**Location**: `app/api/routes/discount_api.py` (lines 338-395)

```python
# VIP handling at invoice level
if vip_discount and vip_discount.get('enabled'):
    vip_discount_percent = float(vip_discount.get('percent', 0))
    if vip_discount_percent > 0:
        if vip_stacking_mode == 'exclusive':
            # Clear all line-item discounts, apply VIP only
            for item in discounted_items:
                item['discount_amount'] = 0
                item['discount_percent'] = 0
            vip_discount_amount = (total_original_price * vip_discount_percent) / 100

        elif vip_stacking_mode == 'absolute':
            # VIP competes with line-item total
            vip_on_original = (total_original_price * vip_discount_percent) / 100
            if vip_on_original > line_item_discount:
                vip_discount_amount = vip_on_original - line_item_discount

        else:  # incremental
            # VIP stacks on subtotal after line-item discounts
            vip_discount_amount = (subtotal_after_line_discounts * vip_discount_percent) / 100
```

### 7.6 Complete Example with All Discounts

**Scenario**: VIP patient with Bulk, Loyalty, Campaign, and Staff Discretionary

```
Configuration:
  VIP mode: incremental
  Bulk mode: incremental
  Loyalty mode: incremental
  Campaign mode: absolute

Patient: Ram Kumar (is_special_group = true)
Service: Advanced Facial x 5

Calculation:
  Step 1: Line-Item Level
    Original Price: Rs. 25,000 (5 x 5,000)
    Bulk Discount: 15% = Rs. 3,750
    Loyalty Discount: 3% = Rs. 750
    Campaign (absolute): 10% = Rs. 2,500

    Stacking: Bulk(15%) + Loyalty(3%) + Campaign(10%) = 28%
    Line-item discount: Rs. 7,000
    Subtotal: Rs. 18,000

  Step 2: Invoice Level
    VIP Discount: 5% of Rs. 18,000 = Rs. 900
    Subtotal after VIP: Rs. 17,100

    Staff Discretionary: 2% of Rs. 17,100 = Rs. 342

  Final:
    Total Discount: Rs. 7,000 + Rs. 900 + Rs. 342 = Rs. 8,242
    Final Price: Rs. 16,758
    Effective Discount: 33%
```

---

## 8. Free Items and Sample/Trial Items

### 8.1 Overview

The system supports two special item types for promotional and trial purposes:

| Type | GST Treatment | Price Treatment | Use Case |
|------|---------------|-----------------|----------|
| **Free Item** | GST calculated on MRP | 100% discount applied | Promotional giveaways (Buy X Get Y rewards) |
| **Sample/Trial** | No GST | No charge (Rs. 0) | Product trials, samples for testing |

### 8.2 Free Items (Promotional)

Free items are promotional items where:
- **GST is calculated on the MRP** (for tax compliance)
- **100% discount is applied** (item is free to customer)
- Used for Buy X Get Y promotions where Y items are given free

```
Example: Buy 2 Get 1 Free promotion
  Item: Face Cream @ Rs. 500 (MRP)

  Line Item 1: Face Cream - Rs. 500 + GST (18%) = Rs. 590 (Paid)
  Line Item 2: Face Cream - Rs. 500 + GST (18%) = Rs. 590 (Paid)
  Line Item 3: Face Cream - Rs. 500 + GST (18%) = Rs. 590 → 100% Discount = Rs. 0 (FREE)

  Note: GST is still calculated on the free item for tax records
```

### 8.3 Sample/Trial Items

Sample items are trial products where:
- **No GST is charged** (not a sale)
- **No charge to customer** (Rs. 0 total)
- Used for product testing, samples, demonstrations

```
Example: Product Sample
  Item: New Serum Sample

  Line Item: New Serum Sample - Rs. 0 (No GST, No Charge)

  Note: Tracked for inventory and customer records
```

### 8.4 Database Schema

The `invoice_line_item` table includes these fields:

```sql
-- Free Item fields
is_free_item BOOLEAN DEFAULT FALSE,
free_item_reason VARCHAR(500),

-- Sample/Trial fields
is_sample BOOLEAN DEFAULT FALSE,
sample_reason VARCHAR(500)
```

### 8.5 Data Flow

The complete data flow for Free/Sample items:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FREE/SAMPLE ITEM DATA FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. FRONTEND (HTML)                                                          │
│     └── Hidden inputs: is_free_item, free_item_reason, is_sample, sample_reason │
│                                                                              │
│  2. JAVASCRIPT (invoice.js)                                                  │
│     └── Populates hidden inputs based on item type selection                 │
│                                                                              │
│  3. FLASK FORM (billing_forms.py)                                            │
│     └── InvoiceLineItemForm includes field definitions:                      │
│         • is_free_item = HiddenField('Is Free Item', default='false')        │
│         • free_item_reason = HiddenField('Free Item Reason', default='')     │
│         • is_sample = HiddenField('Is Sample', default='false')              │
│         • sample_reason = HiddenField('Sample Reason', default='')           │
│                                                                              │
│  4. VIEW (billing_views.py)                                                  │
│     └── Receives form data, passes to service layer                         │
│                                                                              │
│  5. SERVICE (billing_service.py)                                             │
│     └── _process_invoice_line_item() extracts and includes fields            │
│     └── Creates InvoiceLineItem with is_free_item, is_sample, etc.          │
│                                                                              │
│  6. DATABASE (invoice_line_item table)                                       │
│     └── Stores is_free_item, free_item_reason, is_sample, sample_reason     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**CRITICAL**: Flask-WTF only processes fields that are **defined in the Form class**. If a field is missing from `InvoiceLineItemForm`, the data will not be extracted even if HTML hidden inputs exist.

### 8.6 UI Indicators

Free and Sample items are visually indicated across multiple views:

#### 8.6.1 Invoice List View

Indicators appear **below the Payment Status badge**:

```
┌─────────────────────────────────────────────────────────────────┐
│ Invoice #    │ Patient     │ Amount   │ Payment Status          │
├──────────────┼─────────────┼──────────┼─────────────────────────┤
│ MED/00036    │ John Doe    │ ₹5,000   │ [PAID]                  │
│              │             │          │ [🎁 FREE]               │
├──────────────┼─────────────┼──────────┼─────────────────────────┤
│ MED/00037    │ Jane Smith  │ ₹2,500   │ [UNPAID]                │
│              │             │          │ [🧪 SAMPLE]             │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation**: `data_assembler.py` - `_format_status_badge()` appends badges when `has_free_items='true'` or `has_sample_items='true'`.

#### 8.6.2 Invoice Detail View - Header Section

Badges appear in the **Payment Status section**:

```
┌─────────────────────────────────────────────────────────────────┐
│ Payment Status Section                                           │
├─────────────────────────────────────────────────────────────────┤
│ Paid Amount:     ₹5,000                                          │
│ Balance Due:     ₹0                                              │
│ Payment Status:  [PAID]                                          │
│ Free Items:      [🎁 FREE]                                       │
│ Sample Items:    (not shown if none)                             │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation**: Virtual fields `has_free_items` and `has_sample_items` with `conditional_display` to only show when `'true'`.

#### 8.6.3 Invoice Detail View - Line Items Table

Badges appear **below the item name** with row highlighting:

```
┌────┬──────────────────────────┬─────┬──────────┬──────────┐
│ #  │ Item Name                │ Qty │ Rate     │ Total    │
├────┼──────────────────────────┼─────┼──────────┼──────────┤
│ 1  │ Face Cream               │ 1   │ ₹500     │ ₹590     │
├────┼──────────────────────────┼─────┼──────────┼──────────┤  ← Green row
│ 2  │ Face Cream               │ 1   │ ₹500     │ ₹0       │
│    │ [🎁 FREE]                │     │          │          │
├────┼──────────────────────────┼─────┼──────────┼──────────┤  ← Blue row
│ 3  │ Sample Serum             │ 1   │ ₹0       │ ₹0       │
│    │ [🧪 SAMPLE]              │     │          │          │
└────┴──────────────────────────┴─────┴──────────┴──────────┘
```

**Implementation**: `universal_line_items_table.html` template with:
- Row class: `table-success` for FREE, `table-info` for SAMPLE
- Badge below item name using `status-badge status-success` and `status-badge status-purple`

### 8.7 Service Layer Implementation

#### 8.7.1 Form Processing (billing_forms.py)

```python
class InvoiceLineItemForm(FlaskForm):
    # ... other fields ...

    # Free Item support (promotional - GST on MRP, 100% discount)
    is_free_item = HiddenField('Is Free Item', default='false')
    free_item_reason = HiddenField('Free Item Reason', default='')

    # Sample/Trial item support (no GST, no charge)
    is_sample = HiddenField('Is Sample', default='false')
    sample_reason = HiddenField('Sample Reason', default='')
```

#### 8.7.2 Line Item Processing (billing_service.py)

```python
def _process_invoice_line_item(self, item_form, session, hospital_id, ...):
    # ... processing logic ...

    return {
        # ... other fields ...
        'is_free_item': item_form.is_free_item.data == 'true',
        'free_item_reason': item_form.free_item_reason.data or '',
        'is_sample': item_form.is_sample.data == 'true',
        'sample_reason': item_form.sample_reason.data or ''
    }
```

#### 8.7.3 Virtual Field Computation (patient_invoice_service.py)

For list view, virtual fields are computed in `_convert_items_to_dict()`:

```python
def _convert_items_to_dict(self, items: list, session) -> list:
    items_dict = super()._convert_items_to_dict(items, session)

    # Get invoice IDs
    invoice_ids = [item_dict.get('invoice_id') for item_dict in items_dict]

    # Batch query for free items
    free_items_query = session.query(InvoiceLineItem.invoice_id).filter(
        InvoiceLineItem.invoice_id.in_(invoice_ids),
        InvoiceLineItem.is_free_item == True
    ).distinct().all()
    free_invoice_ids = {str(row[0]) for row in free_items_query}

    # Batch query for sample items
    sample_items_query = session.query(InvoiceLineItem.invoice_id).filter(
        InvoiceLineItem.invoice_id.in_(invoice_ids),
        InvoiceLineItem.is_sample == True
    ).distinct().all()
    sample_invoice_ids = {str(row[0]) for row in sample_items_query}

    # Add virtual fields
    for item_dict in items_dict:
        invoice_id_str = str(item_dict.get('invoice_id', ''))
        item_dict['has_free_items'] = 'true' if invoice_id_str in free_invoice_ids else 'false'
        item_dict['has_sample_items'] = 'true' if invoice_id_str in sample_invoice_ids else 'false'

    return items_dict
```

For detail view, computed in `_compute_free_sample_flags()`:

```python
def _compute_free_sample_flags(self, session, invoice_uuid, invoice_data):
    has_free = session.query(InvoiceLineItem).filter(
        InvoiceLineItem.invoice_id == invoice_uuid,
        InvoiceLineItem.is_free_item == True
    ).first() is not None

    has_sample = session.query(InvoiceLineItem).filter(
        InvoiceLineItem.invoice_id == invoice_uuid,
        InvoiceLineItem.is_sample == True
    ).first() is not None

    invoice_data['has_free_items'] = 'true' if has_free else 'false'
    invoice_data['has_sample_items'] = 'true' if has_sample else 'false'
    return invoice_data
```

### 8.8 Configuration (patient_invoice_config.py)

Virtual field definitions for Universal Engine:

```python
FieldDefinition(
    name="has_free_items",
    label="Free Items",
    field_type=FieldType.STATUS_BADGE,
    virtual=True,
    options=[
        {"value": "true", "label": "<i class='fas fa-gift'></i> FREE", "css_class": "status-success"},
        {"value": "false", "label": "", "css_class": ""}
    ],
    show_in_list=False,  # Rendered below payment_status in list view
    show_in_detail=True,
    conditional_display="item.get('has_free_items') == 'true'"
),

FieldDefinition(
    name="has_sample_items",
    label="Sample Items",
    field_type=FieldType.STATUS_BADGE,
    virtual=True,
    options=[
        {"value": "true", "label": "<i class='fas fa-flask'></i> SAMPLE", "css_class": "status-purple"},
        {"value": "false", "label": "", "css_class": ""}
    ],
    show_in_list=False,  # Rendered below payment_status in list view
    show_in_detail=True,
    conditional_display="item.get('has_sample_items') == 'true'"
)
```

### 8.9 CSS Styling (status.css)

```css
/* Success status - Green (for FREE items indicator) */
.status-success {
    background-color: rgb(220 252 231) !important; /* green-100 */
    color: rgb(22 101 52) !important; /* green-800 */
    border: 1px solid rgb(187 247 208) !important; /* green-200 */
}

/* Purple status - for SAMPLE items indicator */
.status-purple {
    background-color: rgb(243 232 255) !important; /* purple-100 */
    color: rgb(107 33 168) !important; /* purple-800 */
    border: 1px solid rgb(216 180 254) !important; /* purple-200 */
}
```

### 8.10 Key Files Modified

| File | Changes |
|------|---------|
| `billing_forms.py` | Added `is_free_item`, `free_item_reason`, `is_sample`, `sample_reason` fields to `InvoiceLineItemForm` |
| `billing_service.py` | Updated `_process_invoice_line_item()` and `InvoiceLineItem` creation to include free/sample fields |
| `patient_invoice_service.py` | Added `_convert_items_to_dict()` override and `_compute_free_sample_flags()` helper |
| `patient_invoice_config.py` | Added virtual field definitions for `has_free_items` and `has_sample_items` |
| `data_assembler.py` | Updated `_format_status_badge()` to append free/sample badges for payment_status field; Fixed `_extract_virtual_field_value()` to handle computed virtual fields |
| `universal_line_items_table.html` | Added FREE/SAMPLE badge display below item name with row highlighting |
| `status.css` | Added `status-success` and `status-purple` CSS classes |

---

## 9. Campaign Management

### 9.1 Campaign Structure

```
Campaign
├── Basic Info (name, description, dates)
├── Discount Configuration
│   ├── discount_type: percentage|fixed_amount|buy_x_get_y
│   ├── discount_value: number
│   └── buy_config: {x: 2, y: 1, y_discount: 100}
├── Targeting
│   ├── target_groups: [item_group_ids]
│   ├── target_special_group: "vip"|"loyalty"|null
│   └── is_personalized: boolean
├── Campaign Groups: [group_ids]
└── Approval Status: pending|approved|rejected
```

### 9.2 Campaign Groups

Campaign groups allow organizing related campaigns:

```
Campaign Group
├── name
├── description
├── color (for visualization)
├── is_active
└── campaigns[] (many-to-many)
```

### 9.3 Approval Workflow

1. **Draft**: Campaign created, not yet submitted
2. **Pending Approval**: Awaiting manager approval
3. **Approved**: Ready for activation
4. **Rejected**: Returned with feedback
5. **Active**: Currently running (within date range)
6. **Expired**: Past end date

### 9.4 Campaign Filtering Logic

```python
# Location: app/services/promotion_dashboard_service.py

# Campaigns are filtered based on:
# 1. Date range (start_date <= today <= end_date)
# 2. Approval status (approved/active)
# 3. Target groups (item groups for services)
# 4. Special targeting:
#    - VIP: target_special_group == 'vip'
#    - Personalized: is_personalized == True AND patient_id matches
# 5. Hospital association
```

### 9.5 Campaign Cards in Invoice Creation

The Create Invoice page displays campaign cards in a dedicated section, allowing staff to see and control applicable promotions.

#### 9.5.1 Campaign Card Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ ☑ Summer Skin Care Sale                    [APPLIED] [BUY X GET Y]│
│   Code: SUMMER2025                                               │
│   Buy: Any Service → Get: Free Consultation + Sample Cream       │
│   Valid Till: 31-Dec-2025                                        │
│   Discount: FREE                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Card Components**:
- **Checkbox**: Toggle campaign inclusion/exclusion
- **Campaign Name**: Green text when active
- **Status Badge**: APPLIED (green) or ELIGIBLE (amber)
- **Type Badge**: "BUY X GET Y" for BXGY campaigns
- **Trigger/Reward Details**: For BXGY shows "Buy: X → Get: Y"
- **Campaign Code**: Reference code
- **Valid Till Date**: Expiration
- **Discount Display**: Percentage, amount, or "FREE"

#### 9.5.2 Campaign States

| State | Badge | Checkbox | Display | Description |
|-------|-------|----------|---------|-------------|
| **ELIGIBLE** | Amber | Checked | Main list | Available but not yet triggered |
| **APPLIED** | Green | Checked | Main list (top) | Actively applied to invoice |
| **EXCLUDED** | None | Unchecked | Bottom section | Manually excluded by staff |

#### 9.5.3 Rendering Priority

```javascript
// Campaigns sorted in this order:
1. Applied campaigns (BXGY first, then by discount value)
2. Eligible campaigns (by discount value, highest first)
3. Excluded campaigns (separate "Excluded" section)
```

#### 9.5.4 Key Functions (create_invoice.html)

| Function | Purpose |
|----------|---------|
| `renderCampaignList()` | Render all campaigns with status and exclusion |
| `toggleCampaignDiscount()` | Master checkbox: enable/disable ALL campaigns |
| `toggleIndividualCampaign()` | Toggle single campaign exclusion |
| `reAddCampaign()` | Restore excluded campaign |
| `updateEligibleCampaigns()` | Refresh from API with merge mode |

#### 9.5.5 Campaign Exclusion Flow

```
1. Staff unchecks campaign checkbox
2. Campaign ID added to window.excludedCampaignIds
3. Campaign card moved to "Excluded" section
4. BuyXGetYHandler.checkBuyXGetY() skips excluded campaigns
5. API /api/discount/calculate receives excluded_campaign_ids
6. Free items from excluded campaigns are auto-removed
7. Staff can re-add via click icon in excluded section
```

#### 9.5.6 Form Submission Data

Hidden fields store applied campaign info for invoice save:

```html
<input type="hidden" name="applied-campaign-id" value="best_campaign_id">
<input type="hidden" name="applied-campaign-ids" value='["id1","id2"]'>
<input type="hidden" name="applied-promo-code" value="SUMMER2025">
```

---

## 9.6 Hospital Discount Stacking Settings

The hospital settings page (`Admin > Hospital Settings`) provides a comprehensive UI for configuring discount stacking behavior.

### 9.6.1 Settings Location

**Template**: `app/templates/admin/hospital_settings.html`
**Backend**: `app/views/admin_views.py` - `hospital_settings()` function
**Database**: `hospitals.discount_stacking_config` (JSONB column)

### 9.6.2 Configuration UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DISCOUNT STACKING CONFIGURATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DISCOUNT TYPE MODES (Left Column)         │  LIMITS (Right Column)         │
│  ─────────────────────────────────         │  ──────────────────────         │
│                                            │                                 │
│  Campaign / Promo Discount                 │  Max Total Discount Cap         │
│  ┌─────────────────────────────┐           │  ┌─────────────────────┐        │
│  │ ○ Exclusive                 │           │  │ [ 50 ] %            │        │
│  │ ● Absolute    ← Recommended │           │  └─────────────────────┘        │
│  │ ○ Incremental               │           │                                 │
│  │ ☑ X items at list price     │           │  Staff Discretionary            │
│  └─────────────────────────────┘           │  ┌─────────────────────┐        │
│                                            │  │ Max: [ 5 ] %        │        │
│  Loyalty Card Discount                     │  │ Options: 1,2,3,4,5  │        │
│  ┌─────────────────────────────┐           │  │ ☐ Requires Note     │        │
│  │ ○ Exclusive                 │           │  └─────────────────────┘        │
│  │ ○ Absolute                  │           │                                 │
│  │ ● Incremental ← Recommended │           │                                 │
│  └─────────────────────────────┘           │                                 │
│                                            │                                 │
│  Bulk Quantity Discount                    │                                 │
│  ┌─────────────────────────────┐           │                                 │
│  │ ○ Exclusive                 │           │                                 │
│  │ ○ Absolute                  │           │                                 │
│  │ ● Incremental ← Recommended │           │                                 │
│  │ ☑ Exclude when campaign     │           │                                 │
│  └─────────────────────────────┘           │                                 │
│                                            │                                 │
│  VIP / Special Group Discount              │                                 │
│  ┌─────────────────────────────┐           │                                 │
│  │ ● Exclusive   ← Recommended │           │                                 │
│  │ ○ Absolute                  │           │                                 │
│  │ ○ Incremental               │           │                                 │
│  └─────────────────────────────┘           │                                 │
│                                            │                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.6.3 Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| **campaign.mode** | Select | exclusive | How campaign discounts interact |
| **campaign.buy_x_get_y_exclusive** | Checkbox | true | X items always at list price |
| **loyalty.mode** | Select | incremental | How loyalty discounts interact |
| **bulk.mode** | Select | incremental | How bulk discounts interact |
| **bulk.exclude_with_campaign** | Checkbox | true | Skip bulk if campaign applies |
| **vip.mode** | Select | absolute | How VIP discounts interact |
| **max_total_discount** | Number | null | Cap on total % (0-100) |
| **staff_disc_max_percent** | Number | 5 | Max staff discretionary % |
| **staff_disc_options** | Text | 1,2,3,4,5 | Quick % options |
| **staff_disc_requires_note** | Checkbox | false | Require reason for staff disc |

### 9.6.4 Stacking Mode Definitions

| Mode | Behavior | When to Use |
|------|----------|-------------|
| **Exclusive** | Only this discount applies; ALL others excluded | VIP-only treatment |
| **Incremental** | Always stacks with other discounts | Loyalty + Bulk should combine |
| **Absolute** | Competes with other absolutes (best wins), then stacks with incrementals | Best promo wins |

### 9.6.5 Default Configuration JSON

```json
{
  "campaign": {
    "mode": "exclusive",
    "buy_x_get_y_exclusive": true
  },
  "loyalty": {
    "mode": "incremental"
  },
  "bulk": {
    "mode": "incremental",
    "exclude_with_campaign": true
  },
  "vip": {
    "mode": "absolute"
  },
  "max_total_discount": null
}
```

### 9.6.6 Recommended Configuration

```
┌────────────────────────────────────────────────────────────────┐
│                    RECOMMENDED SETTINGS                         │
├────────────────────────────────────────────────────────────────┤
│ VIP:        Exclusive    → VIP gets only their discount        │
│ Campaign:   Absolute     → Best promo wins, stacks with others │
│ Bulk:       Incremental  → Always stacks                       │
│ Loyalty:    Incremental  → Always stacks                       │
│ Max Cap:    50%          → Prevents excessive discounts        │
└────────────────────────────────────────────────────────────────┘
```

### 9.6.7 Live Example Calculator

The settings page includes a **Live Example Calculator** that demonstrates stacking behavior in real-time:

```
Example Discounts:
  Campaign: 10%
  Bulk: 5%
  Loyalty: 3%
  VIP: 15%

Result with Current Settings:
  [Calculated total updates as you change mode selectors]
```

### 9.6.8 Saving Configuration

```python
# admin_views.py - hospital_settings()
if request.form.get('form_type') == 'discount_stacking':
    discount_stacking_config = {
        'campaign': {
            'mode': request.form.get('campaign_mode', 'exclusive'),
            'buy_x_get_y_exclusive': request.form.get('buy_x_get_y_exclusive') == 'on'
        },
        'loyalty': {
            'mode': request.form.get('loyalty_mode', 'incremental')
        },
        'bulk': {
            'mode': request.form.get('bulk_mode', 'incremental'),
            'exclude_with_campaign': request.form.get('exclude_with_campaign') == 'on'
        },
        'vip': {
            'mode': request.form.get('vip_mode', 'exclusive')
        },
        'max_total_discount': float(max_val) if max_val else None
    }
    hospital.discount_stacking_config = discount_stacking_config
    session.commit()
```

---

## 10. Database Schema

### 10.1 Key Tables

```sql
-- Campaign/Promotion table
CREATE TABLE campaign_promotions (
    campaign_id UUID PRIMARY KEY,
    hospital_id UUID REFERENCES hospitals,
    name VARCHAR(255),
    description TEXT,
    discount_type VARCHAR(50),  -- percentage, fixed_amount, buy_x_get_y
    discount_value DECIMAL(10,2),
    buy_x_get_y_config JSONB,
    target_groups UUID[],       -- Item group IDs
    target_special_group VARCHAR(50),  -- 'vip', 'loyalty', etc.
    is_personalized BOOLEAN DEFAULT FALSE,
    personalized_patient_id UUID,
    start_date DATE,
    end_date DATE,
    approval_status VARCHAR(50),
    approved_by UUID,
    approved_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Campaign Groups
CREATE TABLE campaign_groups (
    group_id UUID PRIMARY KEY,
    hospital_id UUID REFERENCES hospitals,
    name VARCHAR(255),
    description TEXT,
    color VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
);

-- Campaign-Group association (many-to-many)
CREATE TABLE campaign_group_memberships (
    campaign_id UUID REFERENCES campaign_promotions,
    group_id UUID REFERENCES campaign_groups,
    PRIMARY KEY (campaign_id, group_id)
);

-- Hospital stacking configuration
ALTER TABLE hospitals
ADD COLUMN discount_stacking_config JSONB DEFAULT '{...}'::jsonb;
```

### 10.2 Migrations

| Migration File | Purpose |
|----------------|---------|
| `20251128_add_discount_stacking_config.sql` | Add stacking config to hospitals |
| `20251128_campaign_groups.sql` | Create campaign groups tables |
| `20251128_campaign_groups_soft_delete.sql` | Add soft delete to groups |
| `20251128_campaign_approval_workflow.sql` | Add approval workflow fields |

---

## 11. Key Services and Components

### 11.1 DiscountService (SINGLE SOURCE OF TRUTH)

**Location**: `app/services/discount_service.py`

**Key Methods**:

```python
class DiscountService:

    @staticmethod
    def get_stacking_config(session, hospital_id) -> dict:
        """
        Returns hospital's discount stacking configuration with defaults.
        This is THE ONLY place to get stacking config.
        """

    @staticmethod
    def calculate_stacked_discount(discounts: dict, stacking_config: dict,
                                    item_price: float = None) -> dict:
        """
        CENTRALIZED discount stacking calculator.
        ALL modules must use this method for discount calculations.

        Args:
            discounts: {
                'campaign': {'percent': 10, 'type': 'percentage', ...},
                'bulk': {'percent': 5},
                'loyalty': {'percent': 3},
                'vip': {'percent': 15},
                'standard': {'percent': 5}
            }
            stacking_config: From get_stacking_config()
            item_price: Required for fixed_amount campaigns

        Returns:
            {
                'total_percent': 23,
                'total_amount': 2300,  # if item_price provided
                'breakdown': {'campaign': 10, 'loyalty': 3, 'vip': 15},
                'applied_discounts': ['campaign', 'loyalty', 'vip'],
                'excluded_discounts': ['bulk'],
                'capped': False
            }
        """

    @staticmethod
    def get_max_discount_preview(session, hospital_id, patient_id=None,
                                  service_ids=None, check_date=None) -> dict:
        """
        Preview max possible discount for dashboard/simulation.
        """
```

### 11.2 PromotionDashboardService

**Location**: `app/services/promotion_dashboard_service.py`

**Key Methods**:

```python
class PromotionDashboardService:

    @staticmethod
    def get_applicable_campaigns(session, hospital_id, filters=None) -> list:
        """
        Get campaigns applicable based on filters.
        Filters: patient_id, service_ids, date_range, campaign_groups
        """

    @staticmethod
    def get_campaign_timeline_data(session, hospital_id,
                                    start_date, end_date) -> list:
        """
        Get campaign data formatted for timeline visualization.
        """

    @staticmethod
    def simulate_discount(session, hospital_id, patient_id,
                          service_ids, quantity=1) -> dict:
        """
        Simulate what discount a patient would receive.
        Uses DiscountService.calculate_stacked_discount() internally.
        """
```

### 11.3 BillingService

**Location**: `app/services/billing_service.py`

**Integration**: Uses `DiscountService.get_best_discount_multi()` which internally calls `DiscountService.calculate_stacked_discount()` for actual invoice discount calculations.

**Key Method**: `apply_discounts_to_invoice_items_multi()`
- Collects all applicable discounts (Campaign, Bulk, Loyalty, VIP, Standard)
- Passes them to the centralized stacking calculator
- Applies the result to each invoice line item
- Respects hospital's `discount_stacking_config` settings

---

## 12. Frontend Components

### 12.1 Promotion Timeline

**Location**: `app/static/js/components/promotion_timeline.js`

**Features**:
- Visual timeline of campaigns
- Day/Week/Month views
- Holiday highlighting (national + state-specific)
- Sunday highlighting
- Campaign group color coding
- Hover zoom for details

### 12.2 Promotion Simulator

**Location**: `app/static/js/components/promotion_simulator.js`

**Features**:
- Patient selection
- Service selection
- Real-time discount preview
- Breakdown of applied discounts

### 12.3 Invoice Discount Components

**Location**: `app/static/js/components/invoice_item.js`, `invoice_bulk_discount.js`

**Features**:
- Line item discount display
- Bulk discount application
- Campaign discount badge

---

## 13. Configuration and Settings

### 13.1 Admin UI

**Location**: Admin > Hospital Settings > Discount Stacking Configuration

**Configurable Options**:
- Campaign stacking mode (exclusive/incremental)
- Buy X Get Y exclusive flag
- Loyalty stacking mode
- Bulk stacking mode
- Bulk exclude with campaign flag
- VIP stacking mode
- Maximum total discount cap

### 13.2 Configuration Files

```
app/config/modules/
├── promotion_config.py     # Promotion-specific settings
├── service_config.py       # Service/item settings
└── patient_payment_config.py  # Payment-related configs
```

---

## 14. Integration Points

### 14.1 Invoice Creation Flow

```
1. User adds items to invoice
2. System checks for applicable campaigns (PromotionDashboardService)
3. System gets patient loyalty tier
4. System checks for VIP status
5. System calculates bulk discount based on quantities
6. System calls DiscountService.calculate_stacked_discount()
7. Final discount applied to invoice line items
```

### 14.2 Dashboard Flow

```
1. User opens promotion dashboard
2. Filters applied (patient, dates, groups)
3. PromotionDashboardService.get_applicable_campaigns()
4. Timeline populated with campaign data
5. Max discount preview shown (using centralized calculator)
```

### 14.3 Simulation Flow

```
1. User selects patient and services
2. PromotionDashboardService.simulate_discount()
3. Internally calls DiscountService.calculate_stacked_discount()
4. Returns breakdown for display
```

---

## 15. Maintenance and Troubleshooting

### 15.1 Key Files for Modifications

| Change Type | Files to Modify |
|-------------|-----------------|
| Stacking logic | `app/services/discount_service.py` (ONLY) |
| Campaign filtering | `app/services/promotion_dashboard_service.py` |
| Timeline display | `app/static/js/components/promotion_timeline.js` |
| Settings UI | `app/templates/admin/hospital_settings.html` |
| Invoice display | `app/services/billing_service.py` |

### 15.2 Adding New Discount Type

1. Update `discount_stacking_config` schema in Hospital model
2. Add handling in `DiscountService.calculate_stacked_discount()`
3. Update Settings UI to include new type
4. Add migration for schema changes

### 15.3 Debugging Discount Calculations

```python
# Add to DiscountService.calculate_stacked_discount() for debugging:
import logging
logger = logging.getLogger(__name__)

# Inside the method:
logger.debug(f"Input discounts: {discounts}")
logger.debug(f"Stacking config: {stacking_config}")
logger.debug(f"Result: {result}")
```

### 15.4 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Campaign not showing | Filtering by target_groups | Check item belongs to target group |
| VIP discount not applied | Patient not VIP tagged | Verify patient.is_vip flag |
| Max discount exceeded | Cap not set | Set max_total_discount in config |
| Buy X Get Y wrong | X items getting discount | Verify buy_x_get_y_exclusive = True |

### 15.5 Testing

```python
# Test stacking calculation
from app.services.discount_service import DiscountService

config = {
    'campaign': {'mode': 'incremental'},
    'loyalty': {'mode': 'incremental'},
    'bulk': {'mode': 'incremental', 'exclude_with_campaign': True},
    'vip': {'mode': 'absolute'},
    'max_total_discount': 50
}

discounts = {
    'campaign': {'percent': 10, 'type': 'percentage'},
    'bulk': {'percent': 5},
    'loyalty': {'percent': 3},
    'vip': {'percent': 15}
}

result = DiscountService.calculate_stacked_discount(discounts, config)
print(result)
# Expected: {'total_percent': 28, 'breakdown': {...}, ...}
```

---

## Appendix A: API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/promotions/dashboard` | GET | Dashboard data |
| `/api/promotions/simulate` | POST | Simulate discount |
| `/api/promotions/campaigns` | GET/POST | Campaign CRUD |
| `/api/promotions/groups` | GET/POST | Campaign groups CRUD |
| `/admin/hospital/settings` | GET/POST | Settings including stacking config |

## Appendix B: Holiday Configuration

The timeline component includes Indian government holidays:

**National Holidays** (apply everywhere):
- Republic Day (Jan 26)
- Independence Day (Aug 15)
- Gandhi Jayanti (Oct 2)
- Diwali, Holi, etc.

**State-Specific Holidays**: Based on hospital's GST state code

**Location**: `app/static/js/components/promotion_timeline.js` - `initializeHolidays()`

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-28 | Dev Team | Initial comprehensive documentation |
| 1.1 | 2025-11-28 | Dev Team | Added Section 5: Validated Test Scenarios with 15 comprehensive test cases |
| 1.2 | 2025-11-29 | Dev Team | Updated to three stacking modes (exclusive, incremental, absolute) for all discount types. Added Section 5.3 Mixed Mode Configuration Scenario. |
| 1.3 | 2025-11-29 | Dev Team | Added Section 6: Centralized Architecture. Documented Single Source of Truth pattern, simulation_mode parameter, staff override mechanism (exclude_bulk/exclude_loyalty), loyalty discount source clarification, and bulk discount dynamic recalculation. |
| 1.4 | 2025-11-29 | Dev Team | **Major Update**: Clarified absolute mode behavior - absolutes compete among themselves, winner STACKS with incrementals (not competes). Added Section 7: Invoice-Level Discounts (VIP & Staff Discretionary) with complete two-tier architecture, VIP exclusive/absolute/incremental modes at invoice level, staff discretionary flow, manual override via checkbox, and comprehensive examples. Fixed VIP exclusion bug when checkbox is unchecked. |
| 1.5 | 2025-12-02 | Dev Team | **Added Section 8: Free Items and Sample/Trial Items**. Complete documentation of FREE item (promotional with GST on MRP, 100% discount) and SAMPLE item (no GST, no charge) features. Includes: database schema (is_free_item, free_item_reason, is_sample, sample_reason), data flow from HTML through Flask Form to database, UI indicators in list view (below payment status), detail view (in Payment Status section), and line items table (below item name with row highlighting). Key files: billing_forms.py, billing_service.py, patient_invoice_service.py, patient_invoice_config.py, data_assembler.py, universal_line_items_table.html, status.css. Fixed virtual field extraction in data_assembler for computed fields. |
| 1.6 | 2025-12-02 | Dev Team | **Major Enhancement - Complete Implementation Details**: (1) Added Section 2.5: Buy X Get Y Complete Implementation with end-to-end flow, promotion_rules JSON structure, free item business rules, item type normalization, example scenarios, and key files. (2) Added Section 9.5: Campaign Cards in Invoice Creation with card structure, states (ELIGIBLE/APPLIED/EXCLUDED), rendering priority, key functions, exclusion flow, and form submission data. (3) Added Section 9.6: Hospital Discount Stacking Settings UI with complete configuration UI diagram, all configurable fields, mode definitions, default JSON, recommended settings, live example calculator, and save logic. Document now comprehensively covers the entire promotions and discounts module from UI to database. |

---

*This document should be updated whenever significant changes are made to the promotions and discounts module.*
