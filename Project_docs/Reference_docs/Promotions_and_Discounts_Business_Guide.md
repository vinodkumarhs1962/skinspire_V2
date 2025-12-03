# Promotions and Discounts Business Guide

## Overview

The SkinSpire Promotion Module provides a comprehensive suite of discount and promotional tools to help clinics attract customers, reward loyalty, and drive revenue. This guide explains the various promotion types, discount stacking scenarios, and how to leverage them for your business.

---

## Table of Contents

1. [Discount Types](#1-discount-types)
2. [Bulk Discount](#2-bulk-discount)
3. [Loyalty Card Program](#3-loyalty-card-program)
4. [VIP Discount](#4-vip-discount)
5. [Promotion Campaign Types](#5-promotion-campaign-types)
6. [Discount Stacking Modes](#6-discount-stacking-modes)
7. [Targeting Options](#7-targeting-options)
8. [Campaign Conditions](#8-campaign-conditions)
9. [Package Payments and Installments](#9-package-payments-and-installments)
10. [Real-World Scenarios](#10-real-world-scenarios)
11. [Best Practices](#11-best-practices)

---

## 1. Discount Types

The system supports two fundamental discount types that can be applied across all promotion campaigns:

### 1.1 Percentage Discount

A percentage-based discount that scales with the item price.

| Attribute | Description |
|-----------|-------------|
| **How it works** | Discount = Item Price × Discount % |
| **Best for** | General promotions, tiered discounts |
| **Example** | 20% off on all services |

**Calculation Example:**
- Service Price: ₹2,500
- Discount: 20%
- Discount Amount: ₹500
- Final Price: ₹2,000

### 1.2 Fixed Amount Discount (Flat Discount)

A fixed rupee amount discount regardless of item price (subject to minimum purchase).

| Attribute | Description |
|-----------|-------------|
| **How it works** | Discount = Fixed Amount (e.g., ₹500) |
| **Best for** | Festival offers, promotional events |
| **Example** | ₹500 off on purchases above ₹3,000 |

**Calculation Example:**
- Service Price: ₹3,500
- Discount: ₹500 flat
- Final Price: ₹3,000

---

## 2. Bulk Discount

Bulk discount rewards customers who book multiple items in a single invoice, encouraging higher-value transactions.

### 2.1 How Bulk Discount Works

| Setting | Description |
|---------|-------------|
| **Minimum Item Count** | Number of items required to qualify (e.g., 5) |
| **Discount Percentage** | Discount applied when threshold is met |
| **Applies To** | Services, Medicines, or both (configurable) |

### 2.2 Counting Rules

The system counts **total quantity**, not just line items:

| Scenario | Line Items | Quantities | Total Count | Bulk Eligible? (Min: 5) |
|----------|------------|------------|-------------|------------------------|
| Same service, multiple sessions | 1 | Qty: 5 | 5 | Yes |
| Multiple services | 3 | Qty: 2, 2, 1 | 5 | Yes |
| Mixed | 2 | Qty: 3, 1 | 4 | No |

### 2.3 Bulk Discount Scenarios

#### Scenario A: Single Service, Multiple Sessions

**Use Case:** Patient books 5 sessions of the same treatment

| Item | Unit Price | Quantity | Line Total |
|------|-----------|----------|------------|
| Laser Hair Removal | ₹2,000 | 5 | ₹10,000 |

- **Total Count:** 5 (meets minimum)
- **Bulk Discount:** 10%
- **Discount Amount:** ₹1,000
- **Final Amount:** ₹9,000

#### Scenario B: Multiple Services, Combined Sessions

**Use Case:** Patient books different treatments totaling 5+ sessions

| Item | Unit Price | Quantity | Line Total |
|------|-----------|----------|------------|
| Chemical Peel | ₹1,500 | 2 | ₹3,000 |
| Microdermabrasion | ₹1,200 | 2 | ₹2,400 |
| HydraFacial | ₹2,000 | 1 | ₹2,000 |
| **Total** | | **5** | **₹7,400** |

- **Total Count:** 5 (meets minimum)
- **Bulk Discount:** 10%
- **Discount Amount:** ₹740
- **Final Amount:** ₹6,660

#### Scenario C: Bulk Discount on Medicines

**Use Case:** Patient purchases multiple medicine items

| Item | Unit Price | Quantity | Line Total |
|------|-----------|----------|------------|
| Moisturizer 100ml | ₹450 | 2 | ₹900 |
| Sunscreen SPF50 | ₹600 | 2 | ₹1,200 |
| Vitamin C Serum | ₹800 | 1 | ₹800 |
| **Total** | | **5** | **₹2,900** |

- **Total Count:** 5 (meets minimum)
- **Bulk Discount:** 8% (medicines may have different rate)
- **Discount Amount:** ₹232
- **Final Amount:** ₹2,668

### 2.4 Bulk Discount Configuration

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| Min Service Count | Minimum services to qualify | 5 |
| Service Bulk Discount % | Discount for services | 10% |
| Min Medicine Count | Minimum medicines to qualify | 5 |
| Medicine Bulk Discount % | Discount for medicines | 5-8% |

---

## 3. Loyalty Card Program

The loyalty program rewards repeat customers with automatic discounts and redeemable points.

### 3.1 Loyalty Card Tiers

| Tier | Discount % | Qualification | Benefits |
|------|-----------|---------------|----------|
| **Silver** | 3% | Entry level / ₹5,000 spend | Basic discount |
| **Gold** | 5% | ₹15,000 lifetime spend | Enhanced discount |
| **Platinum** | 10% | ₹50,000 lifetime spend | Premium discount + priority |

### 3.2 How Loyalty Discount Works

- Discount is applied **automatically** based on patient's card tier
- Applied to **each line item** in the invoice
- **Stacks with other discounts** based on hospital configuration

**Example: Gold Member Purchase**

| Item | Price | Loyalty (5%) | Net Price |
|------|-------|--------------|-----------|
| Facial Treatment | ₹2,000 | ₹100 | ₹1,900 |
| Skin Consultation | ₹500 | ₹25 | ₹475 |
| **Total** | **₹2,500** | **₹125** | **₹2,375** |

### 3.3 Loyalty Points System

Customers earn points on purchases that can be redeemed for discounts.

#### Point Earning

| Transaction | Points Earned |
|-------------|---------------|
| ₹100 spent | 1 point |
| ₹1,000 spent | 10 points |
| Special promotions | Bonus points (2x, 3x) |

#### Point Redemption

| Points | Redemption Value |
|--------|------------------|
| 100 points | ₹100 discount |
| 500 points | ₹500 discount |

### 3.4 Loyalty Points in Payment Cycle

**Scenario: Customer Uses Points for Partial Payment**

| Step | Description | Amount |
|------|-------------|--------|
| 1. Invoice Total | Services + Medicines | ₹5,000 |
| 2. Loyalty Discount (5%) | Automatic tier discount | -₹250 |
| 3. Subtotal | After discount | ₹4,750 |
| 4. Points Redemption | Customer has 200 points | -₹200 |
| 5. Amount Due | Balance to pay | ₹4,550 |
| 6. Payment | Cash/Card/UPI | ₹4,550 |
| 7. Points Earned | 5% of ₹4,550 = 45 points | +45 pts |

**Key Rules:**
- Points are earned on **actual payment amount** (after discounts and redemptions)
- Points redemption is **optional** - customer chooses how many to use
- Minimum redemption may apply (e.g., 50 points minimum)

---

## 4. VIP Discount

VIP discount is a special privilege for premium customers marked as "Special Group" or "VIP" in the system.

### 4.1 VIP Discount Configuration

| Setting | Description |
|---------|-------------|
| VIP Discount % | Percentage discount for VIP patients |
| Stacking Mode | How VIP interacts with other discounts |
| Target Patients | Patients with is_special_group = true |

### 4.2 VIP Stacking Modes

The VIP discount can operate in three modes:

| Mode | Behavior | Best For |
|------|----------|----------|
| **Exclusive** | VIP replaces ALL other discounts | Maximum VIP privilege |
| **Incremental** | VIP adds on top of other discounts | Reward stacking |
| **Absolute** | VIP competes with others; best wins | Guaranteed minimum |

---

## 5. Promotion Campaign Types

### 5.1 Simple Discount Campaign

A straightforward discount applied automatically or via promo code on eligible items.

**Use Cases:**
- Seasonal sales (Summer Special, Winter Care)
- Festival promotions (Diwali Offer, Christmas Sale)
- New service launch discounts
- Member-exclusive offers

**Configuration Options:**

| Option | Description |
|--------|-------------|
| Discount Type | Percentage or Fixed Amount |
| Discount Value | The discount % or ₹ amount |
| Applies To | All / Services / Medicines / Packages |
| Auto-Apply | Automatically apply or require promo code |

### 5.2 Buy X Get Y Free Campaign

A promotional scheme where purchasing specific items (triggers) earns free items (rewards).

**Use Cases:**
- Buy 5 sessions, get 1 free
- Buy a package, get a complimentary product
- Purchase consultation, get free medicine sample

**How It Works:**

| Component | Description |
|-----------|-------------|
| Trigger Items | Items that must be purchased |
| Trigger Quantity | Minimum quantity required |
| Reward Items | Items given free |
| Reward Quantity | Number of free items |

**Example: "Buy 5 Get 1 Free"**
- Trigger: Acne Treatment Session (Qty: 5)
- Reward: Acne Treatment Session (Qty: 1 FREE)
- Customer pays for 5, gets 6

---

## 6. Discount Stacking Modes

When multiple discounts apply to the same item, the system uses **stacking modes** to determine the final discount.

### 6.1 Available Stacking Modes

| Mode | Symbol | Behavior |
|------|--------|----------|
| **Incremental** | + | Discounts add together |
| **Absolute** | vs | Best discount wins, can stack with incrementals |
| **Exclusive** | × | Only this discount applies, others ignored |

### 6.2 Default Stacking Configuration

| Discount Type | Default Mode | Rationale |
|---------------|--------------|-----------|
| Bulk Discount | Incremental | Rewards volume |
| Loyalty Discount | Incremental | Rewards membership |
| Campaign Discount | Absolute | Best campaign wins |
| VIP Discount | Configurable | Hospital decides |

### 6.3 Stacking Scenarios

#### Scenario 1: VIP as EXCLUSIVE

**Configuration:** VIP mode = Exclusive (VIP replaces everything)

**Situation:** VIP patient (20% VIP) books service with:
- Bulk discount: 10%
- Loyalty discount: 5%
- Campaign discount: 15%

| Discount | Calculated | Applied? |
|----------|------------|----------|
| Bulk | 10% | No (excluded) |
| Loyalty | 5% | No (excluded) |
| Campaign | 15% | No (excluded) |
| **VIP** | **20%** | **Yes (only this)** |

**Result:** 20% discount (VIP only)

**When to Use:** When VIP customers should get a guaranteed flat rate regardless of other promotions.

---

#### Scenario 2: VIP as INCREMENTAL

**Configuration:** VIP mode = Incremental (VIP adds to others)

**Situation:** VIP patient (10% VIP) books service with:
- Bulk discount: 10% (incremental)
- Loyalty discount: 5% (incremental)
- Campaign discount: 15% (absolute)

| Step | Discount | Running Total |
|------|----------|---------------|
| 1. Incrementals | Bulk 10% + Loyalty 5% | 15% |
| 2. Absolute (Campaign) | 15% vs incrementals | 15% (tie, campaign used) |
| 3. VIP (Incremental) | +10% | **25%** |

**Result:** 25% discount (Campaign + VIP stacked)

**When to Use:** When VIP should always get extra benefit on top of best available offer.

---

#### Scenario 3: Bulk as INCREMENTAL

**Configuration:** Bulk mode = Incremental

**Situation:** Patient (Gold 5% loyalty) books 5 services with:
- Bulk discount: 10%
- Campaign discount: 12%

| Step | Discount | Running Total |
|------|----------|---------------|
| 1. Bulk (Incremental) | 10% | 10% |
| 2. Loyalty (Incremental) | 5% | 15% |
| 3. Campaign (Absolute) | 12% vs 15% | 15% (incrementals win) |

**Result:** 15% discount (Bulk + Loyalty, campaign excluded)

**When to Use:** When volume purchases should always be rewarded additionally.

---

#### Scenario 4: Bulk as ABSOLUTE

**Configuration:** Bulk mode = Absolute

**Situation:** Patient (Gold 5% loyalty) books 5 services with:
- Bulk discount: 10%
- Campaign discount: 12%

| Step | Discount | Running Total |
|------|----------|---------------|
| 1. Loyalty (Incremental) | 5% | 5% |
| 2. Bulk vs Campaign (Absolute) | 10% vs 12% | 12% (campaign wins) |
| 3. Winner + Incrementals | 12% + 5% | **17%** |

**Result:** 17% discount (Campaign + Loyalty)

**When to Use:** When bulk should compete fairly with campaigns, not always add on.

---

#### Scenario 5: Campaigns Competing (All Absolute)

**Configuration:** Multiple campaigns, all in Absolute mode

**Situation:** Service eligible for 3 campaigns:
- Diwali Special: 15%
- New Customer: 20%
- Weekend Offer: 10%

| Campaign | Discount Amount (on ₹2,000) |
|----------|----------------------------|
| Diwali Special | ₹300 |
| **New Customer** | **₹400** (Winner) |
| Weekend Offer | ₹200 |

**Result:** New Customer (20%) wins - highest discount amount

**Selection Logic:** System selects campaign with **highest discount amount** (not percentage).

**Example where Fixed Amount wins:**

| Campaign | Type | Value | On ₹2,000 |
|----------|------|-------|-----------|
| Percentage Offer | % | 15% | ₹300 |
| **Flat Discount** | **Fixed** | **₹500** | **₹500** (Winner) |

---

#### Scenario 6: Loyalty + Bulk + Campaign Combined

**Configuration:**
- Bulk: Incremental
- Loyalty: Incremental
- Campaign: Absolute

**Situation:** Gold member books 5 services (₹2,000 each = ₹10,000 total)
- Bulk: 10%
- Loyalty: 5%
- Campaign: 12%

**Calculation:**

| Step | Description | Discount |
|------|-------------|----------|
| 1 | Incrementals: Bulk + Loyalty | 10% + 5% = 15% |
| 2 | Absolute: Campaign vs Incrementals | 12% < 15% |
| 3 | Winner | Incrementals win (15%) |

**Final Breakdown:**
| | Amount |
|--|--------|
| Original | ₹10,000 |
| Discount (15%) | ₹1,500 |
| **Final** | **₹8,500** |

---

## 7. Targeting Options

### 7.1 Item Category Targeting

| Target | Description | Example |
|--------|-------------|---------|
| **All** | Services, medicines, packages | Store-wide sale |
| **Services** | Only clinic services | Service promotions |
| **Medicines** | Pharmacy items | Clearance sale |
| **Packages** | Treatment packages | Package upgrades |

### 7.2 Promotion Groups

Create custom item groups for targeted promotions.

**Example:** "Premium Skin Care" group containing:
- Chemical Peel
- Laser Treatment
- HydraFacial

Campaign applies only to items in this group.

### 7.3 Special Group Targeting

Target promotions exclusively to VIP/Special Group patients.

---

## 8. Campaign Conditions

### 8.1 Minimum Purchase Amount

| Setting | Effect |
|---------|--------|
| Min ₹3,000 | Discount only if item price >= ₹3,000 |

### 8.2 Date Range

| Field | Purpose |
|-------|---------|
| Start Date | Campaign activation |
| End Date | Campaign expiry |

### 8.3 Usage Limits

| Limit | Description |
|-------|-------------|
| Max Per Patient | Single use per customer |
| Max Total | First N customers |

### 8.4 Auto-Apply vs Personalized

| Mode | Behavior |
|------|----------|
| Auto-Apply | Automatic at checkout |
| Personalized | Requires promo code |

---

## 9. Package Payments and Installments

### 9.1 Package Overview

Treatment packages bundle multiple services at a discounted price, with flexible payment options.

**Example Package: "Complete Acne Care"**

| Component | Sessions | Individual Price | Package Price |
|-----------|----------|------------------|---------------|
| Consultation | 2 | ₹1,000 | |
| Chemical Peel | 4 | ₹6,000 | |
| LED Therapy | 4 | ₹4,000 | |
| **Total** | **10** | **₹11,000** | **₹9,000** |

Package Discount: ₹2,000 (18% savings)

### 9.2 Installment Payment Options

Packages can be paid in installments:

| Plan | Structure | Example (₹9,000 package) |
|------|-----------|--------------------------|
| **Full Payment** | 100% upfront | ₹9,000 |
| **2 Installments** | 50% + 50% | ₹4,500 × 2 |
| **3 Installments** | 40% + 30% + 30% | ₹3,600 + ₹2,700 + ₹2,700 |
| **Custom** | Flexible amounts | As agreed |

### 9.3 Installment Payment Flow

**Scenario: 3-Installment Package Purchase**

| Step | Action | Amount | Balance |
|------|--------|--------|---------|
| 1 | Package booked | ₹9,000 | ₹9,000 |
| 2 | First payment (40%) | ₹3,600 | ₹5,400 |
| 3 | Sessions start | - | - |
| 4 | Second payment (30%) | ₹2,700 | ₹2,700 |
| 5 | More sessions | - | - |
| 6 | Final payment (30%) | ₹2,700 | ₹0 |
| 7 | Package complete | - | Paid in full |

### 9.4 Loyalty Points on Package Installments

Points are earned on **each payment**, not on package value:

| Payment | Amount Paid | Points Earned (1%) |
|---------|-------------|-------------------|
| Installment 1 | ₹3,600 | 36 points |
| Installment 2 | ₹2,700 | 27 points |
| Installment 3 | ₹2,700 | 27 points |
| **Total** | **₹9,000** | **90 points** |

### 9.5 Discounts on Packages

Packages can receive additional discounts:

| Discount Type | Applicable? | Notes |
|---------------|-------------|-------|
| Loyalty % | Yes | Applied on package price |
| Campaign | Yes | If package in target |
| Bulk | No | Package is single unit |
| VIP | Yes | If patient is VIP |

**Example: VIP Buying Package**

| | Amount |
|--|--------|
| Package Price | ₹9,000 |
| VIP Discount (10%) | -₹900 |
| **Final Price** | **₹8,100** |

Installments adjusted: ₹3,240 + ₹2,430 + ₹2,430

---

## 10. Real-World Scenarios

### Scenario 1: Regular Customer with Bulk Purchase

**Customer:** Priya, Gold member (5% loyalty)
**Purchase:** 6 Laser sessions @ ₹2,000 each
**Promotions Active:** Summer Sale 12%

| Factor | Value |
|--------|-------|
| Subtotal | ₹12,000 |
| Bulk Discount (10%) | Incremental |
| Loyalty (5%) | Incremental |
| Campaign (12%) | Absolute |

**Calculation:**
- Incrementals: 10% + 5% = 15% = ₹1,800
- Campaign: 12% = ₹1,440
- Winner: Incrementals (15%) = **₹1,800 discount**

**Final:** ₹12,000 - ₹1,800 = **₹10,200**

---

### Scenario 2: VIP Customer with Exclusive Mode

**Customer:** Dr. Sharma, VIP (20% exclusive)
**Purchase:** Consultation ₹1,000 + Treatment ₹3,000
**Promotions Active:** Diwali 15%, Bulk eligible

| Without VIP | With VIP (Exclusive) |
|-------------|---------------------|
| Bulk: 10% | Ignored |
| Campaign: 15% | Ignored |
| **Best: 15%** | **VIP: 20%** |
| Discount: ₹600 | Discount: ₹800 |

**Result:** VIP gets ₹800 discount (better than 15%)

---

### Scenario 3: VIP Customer with Incremental Mode

**Customer:** Mrs. Kapoor, VIP (10% incremental)
**Purchase:** 5 services totaling ₹8,000
**Active:** Campaign 15%

| Discount | Mode | Value |
|----------|------|-------|
| Campaign | Absolute | 15% |
| VIP | Incremental | +10% |
| **Total** | | **25%** |

**Result:** ₹8,000 × 25% = **₹2,000 discount**
**Final:** ₹6,000

---

### Scenario 4: Festival Flat Discount

**Customer:** New walk-in
**Purchase:** Premium Facial ₹3,500
**Campaign:** Rajyotsava ₹500 flat (min ₹3,000)

| Check | Result |
|-------|--------|
| Price >= Min? | ₹3,500 >= ₹3,000 ✓ |
| Discount | ₹500 flat |

**Final:** ₹3,500 - ₹500 = **₹3,000**

---

### Scenario 5: Competing Campaigns

**Customer:** Regular patient
**Purchase:** Anti-aging treatment ₹5,000
**Active Campaigns:**
- New Year Sale: 20% (₹1,000)
- Flat ₹800 off (₹800)
- Weekend Special: 15% (₹750)

**Winner:** New Year Sale (₹1,000 highest)
**Final:** ₹5,000 - ₹1,000 = **₹4,000**

---

### Scenario 6: Full Stack - Bulk + Loyalty + Campaign + VIP

**Customer:** Platinum VIP (10% incremental)
**Card:** Platinum (10% loyalty)
**Purchase:** 5 sessions @ ₹2,000 = ₹10,000
**Campaign:** Member Special 8%

**Configuration:**
- Bulk: Incremental
- Loyalty: Incremental
- Campaign: Absolute
- VIP: Incremental

| Step | Calculation |
|------|-------------|
| 1. Incrementals | Bulk 10% + Loyalty 10% = 20% |
| 2. Absolute | Campaign 8% vs 20% → 20% wins |
| 3. VIP adds | 20% + 10% = **30%** |

**Final:** ₹10,000 × 30% = ₹3,000 discount = **₹7,000**

---

### Scenario 7: Package with Installments + Points

**Customer:** Gold member
**Package:** Skin Rejuvenation ₹15,000

| | Amount |
|--|--------|
| Package | ₹15,000 |
| Loyalty 5% | -₹750 |
| **Net Package** | **₹14,250** |

**Installment Plan:** 3 payments

| Payment | Amount | Points Earned |
|---------|--------|---------------|
| Payment 1 | ₹5,700 | 57 pts |
| Payment 2 | ₹4,275 | 43 pts |
| Payment 3 | ₹4,275 | 43 pts |
| **Total** | **₹14,250** | **143 pts** |

---

### Scenario 8: Points Redemption at Checkout

**Customer:** Has 500 loyalty points
**Purchase:** ₹3,000 service
**Loyalty Discount:** 5% = ₹150

| Step | Amount |
|------|--------|
| Service | ₹3,000 |
| Loyalty Discount | -₹150 |
| Subtotal | ₹2,850 |
| Points Redeemed (200 pts) | -₹200 |
| **Amount Due** | **₹2,650** |
| Points Earned (1% of ₹2,650) | +27 pts |
| **New Points Balance** | 327 pts |

---

## 11. Best Practices

### Campaign Strategy

| Goal | Recommended Approach |
|------|---------------------|
| Attract new customers | High %, single use, promo code |
| Increase transaction size | Bulk discounts, min purchase |
| Reward loyalty | Tiered loyalty + VIP incremental |
| Clear inventory | High % on specific items |
| Festival buzz | Flat amount, limited time |

### Stacking Mode Selection

| Situation | Recommended Mode |
|-----------|------------------|
| VIP should always get best deal | VIP Exclusive |
| VIP gets extra on top | VIP Incremental |
| Volume should always be rewarded | Bulk Incremental |
| Fair competition between offers | Bulk Absolute |

### Common Configurations

**Conservative (Protect Margins):**
- Bulk: Absolute
- VIP: Absolute
- Max cap: 30%

**Generous (Maximize Customer Benefit):**
- Bulk: Incremental
- VIP: Incremental
- Loyalty: Incremental

### Monitoring Checklist

- [ ] Review active campaigns weekly
- [ ] Check discount amounts vs revenue
- [ ] Monitor campaign usage counts
- [ ] Deactivate expired campaigns
- [ ] Analyze which discounts drive conversions

---

## Summary

| Feature | Capability |
|---------|------------|
| **Discount Types** | Percentage, Fixed Amount |
| **Bulk Discount** | Volume-based, services & medicines |
| **Loyalty Program** | Tiered discounts + points |
| **VIP Discount** | Exclusive, Incremental, Absolute modes |
| **Campaigns** | Simple Discount, Buy X Get Y |
| **Stacking** | Configurable per discount type |
| **Packages** | Installment payments supported |
| **Points** | Earn on payments, redeem at checkout |

---

*Document Version: 2.0*
*Last Updated: December 2025*
*Module: Promotions and Discounts*
