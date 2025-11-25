# Bulk Service Discount System - Complete Reference Guide
**Version:** 1.0.0
**Last Updated:** November 20, 2025
**Status:** Production Ready ✅

---

## Table of Contents

1. [Overview](#overview)
2. [Business Rules](#business-rules)
3. [System Architecture](#system-architecture)
4. [Database Schema](#database-schema)
5. [Discount Calculation Logic](#discount-calculation-logic)
6. [API Reference](#api-reference)
7. [Configuration Guide](#configuration-guide)
8. [User Guide](#user-guide)
9. [Admin Guide](#admin-guide)
10. [Reporting & Analytics](#reporting--analytics)
11. [Troubleshooting](#troubleshooting)
12. [Integration Points](#integration-points)
13. [Security & Audit](#security--audit)
14. [Future Enhancements](#future-enhancements)

---

## Overview

### Purpose
The Bulk Service Discount System automatically calculates and applies discounts to service items when patients purchase multiple services in a single invoice. The system supports three types of discounts:

1. **Bulk Discounts** - Triggered when the total number of services in an invoice meets or exceeds a hospital-defined threshold
2. **Loyalty Discounts** - Applied based on the patient's loyalty card tier (Silver, Gold, Platinum)
3. **Campaign Discounts** - Time-bound promotional discounts (future enhancement)

### Key Features
- ✅ **Automatic Calculation**: Discounts calculated and applied during invoice creation
- ✅ **Best Discount Selection**: System automatically selects the highest applicable discount
- ✅ **Service-Level Configuration**: Each service defines its own bulk discount percentage
- ✅ **Hospital-Level Policy**: Hospital sets the minimum service count threshold
- ✅ **Max Discount Validation**: Discounts cannot exceed service-defined maximum limits
- ✅ **Complete Audit Trail**: Every discount application is logged with metadata
- ✅ **Loyalty Card Integration**: Patient card tiers with escalating discounts
- ✅ **Manual Override**: Users can adjust discounts within max_discount limits

### Design Philosophy
The system follows a **simple, configurable approach**:
- **Hospital** defines **WHEN** bulk discount triggers (e.g., "5 services")
- **Service** defines **HOW MUCH** discount to give (e.g., "Laser: 10%, Facial: 15%")
- **System** calculates **ALL** discounts and selects **BEST** one automatically

---

## Business Rules

### Rule 1: Bulk Discount Eligibility

**Condition:**
```
Total Service Count in Invoice >= Hospital.bulk_discount_min_service_count
AND Hospital.bulk_discount_enabled = TRUE
AND Service.bulk_discount_percent > 0
```

**Behavior:**
- System counts **only** service line items (excludes medicines, products, consumables)
- All services in invoice contribute to count, regardless of type
- Threshold checked per invoice, not per patient or session

**Example:**
```
Hospital Setting: min_service_count = 5

Invoice A:
  - 3 Laser Hair Reduction
  - 2 Medifacial
  Total: 5 services ✓ → Bulk discount TRIGGERED

Invoice B:
  - 2 Laser Hair Reduction
  - 2 Medifacial
  Total: 4 services ✗ → Bulk discount NOT triggered
```

### Rule 2: Loyalty Card Discount

**Condition:**
```
Patient has active loyalty card
AND Card.expiry_date IS NULL OR Card.expiry_date >= TODAY
AND Card.is_active = TRUE
```

**Behavior:**
- Only ONE active card per patient
- Card discount applies to ALL services (no service-specific limitations)
- Card discount percentage defined at card type level (not per service)

**Card Tiers (Default):**
```
Standard   - 0%  discount (default for all patients)
Silver     - 5%  discount (₹50,000 lifetime spend)
Gold       - 10% discount (₹100,000 lifetime spend)
Platinum   - 15% discount (₹250,000 lifetime spend)
```

### Rule 3: Best Discount Selection

**Logic:**
```
IF multiple discounts apply:
    SELECT discount WITH MAX(discount_percent)
    STORE competing_discounts IN metadata
    RETURN selected_discount
ELSE:
    RETURN no_discount
```

**Precedence:**
- System does **NOT** combine discounts (no stacking)
- Always selects **highest percentage**
- Metadata stores all calculated discounts for audit

**Example:**
```
Patient: Has Gold card (10% discount)
Invoice: 5 services (bulk discount eligible)
Service: Laser Hair Reduction (bulk_discount_percent = 12%)

Calculation:
  - Bulk:    12% ✓ SELECTED
  - Loyalty: 10%
  - Campaign: Not applicable

Applied: 12% bulk discount
Metadata: {competing_discounts: [{type: 'loyalty', percent: 10}]}
```

### Rule 4: Max Discount Validation

**Condition:**
```
IF calculated_discount_percent > Service.max_discount:
    applied_discount = Service.max_discount
    metadata.capped = TRUE
ELSE:
    applied_discount = calculated_discount_percent
```

**Behavior:**
- Every service has optional `max_discount` field
- Discounts **cannot exceed** this limit, even if calculated higher
- System logs when discount is capped

**Example:**
```
Service: Botox Injection
  max_discount: 5%
  bulk_discount_percent: 10%

Patient: Platinum card (15% discount)

Calculation:
  - Bulk:    10%
  - Loyalty: 15%
  - Best:    15% → CAPPED at 5% (max_discount)

Applied: 5% discount
Metadata: {
    capped: true,
    original_best: 15,
    cap_reason: "Exceeds max_discount of 5% for Botox Injection"
}
```

### Rule 5: Effective Date Validation

**Condition:**
```
IF Hospital.bulk_discount_effective_from IS NOT NULL:
    IF invoice_date < effective_from:
        SKIP bulk discount
```

**Behavior:**
- Hospital can set a start date for bulk discount policy
- Invoices before this date do not get bulk discounts
- Loyalty discounts always apply (no date restriction)

---

## System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
│  (Invoice Creation Form, Patient Management, Admin Settings) │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer (Flask)                   │
├─────────────────────────────────────────────────────────────┤
│  billing_views.py → create_invoice()                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
├─────────────────────────────────────────────────────────────┤
│  billing_service.py                                          │
│    ├─ _create_invoice()                                      │
│    └─ [CALLS] discount_service.apply_discounts_to_invoice() │
│                                                               │
│  discount_service.py ★ NEW ★                                 │
│    ├─ apply_discounts_to_invoice_items()                     │
│    ├─ calculate_bulk_discount()                              │
│    ├─ calculate_loyalty_discount()                           │
│    ├─ calculate_campaign_discount()                          │
│    ├─ get_best_discount()                                    │
│    ├─ validate_discount()                                    │
│    └─ log_discount_application()                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
├─────────────────────────────────────────────────────────────┤
│  Models (SQLAlchemy ORM)                                     │
│    ├─ Hospital (bulk discount policy)                        │
│    ├─ Service (bulk discount %)                              │
│    ├─ LoyaltyCardType (card tiers)                           │
│    ├─ PatientLoyaltyCard (patient-card link)                 │
│    ├─ DiscountApplicationLog (audit trail)                   │
│    ├─ InvoiceHeader                                          │
│    └─ InvoiceLineItem                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database (PostgreSQL)                      │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────┐
│ User Action │ Create invoice with 5 services
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│ billing_service._create_invoice()                   │
│   1. Receives line_items from UI                     │
│   2. Calls discount_service.apply_discounts()        │
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│ discount_service.apply_discounts_to_invoice_items() │
│   1. Count total services = 5                        │
│   2. For each service line item:                     │
│      └─ Call get_best_discount()                     │
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│ discount_service.get_best_discount()                │
│   1. calculate_bulk_discount()                       │
│      └─ Check hospital.min_count (5)                 │
│      └─ Get service.bulk_discount_percent (10%)      │
│   2. calculate_loyalty_discount()                    │
│      └─ Query patient_loyalty_cards                  │
│      └─ Get card_type.discount_percent (5%)          │
│   3. calculate_campaign_discount()                   │
│      └─ (Not implemented yet)                        │
│   4. Compare all: 10% bulk vs 5% loyalty             │
│   5. Select highest: 10% bulk ✓                      │
│   6. Validate against max_discount                   │
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│ Return to billing_service                           │
│   - line_items[].discount_percent = 10.00            │
│   - line_items[].discount_type = 'bulk'              │
│   - line_items[].discount_metadata = {...}           │
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│ billing_service._create_invoice() continues         │
│   1. Calculate line item totals (with discount)      │
│   2. Create InvoiceHeader                            │
│   3. Create InvoiceLineItems                         │
│   4. Call log_discount_application() for audit       │
│   5. Complete invoice creation                       │
└──────┬──────────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Success   │ Invoice created with discounts applied
└─────────────┘
```

---

## Database Schema

### ER Diagram

```
┌────────────────┐
│   hospitals    │
├────────────────┤
│ hospital_id PK │───┐
│ name           │   │
│ bulk_discount_ │   │
│  enabled       │   │
│ bulk_discount_ │   │
│  min_service_  │   │
│  count         │   │
│ bulk_discount_ │   │
│  effective_    │   │
│  from          │   │
└────────────────┘   │
                     │
┌────────────────┐   │
│   services     │   │
├────────────────┤   │
│ service_id PK  │───┤
│ service_name   │   │
│ price          │   │
│ max_discount   │   │
│ bulk_discount_ │   │
│  percent       │   │
└────────────────┘   │
                     │
┌──────────────────┐ │
│loyalty_card_types│ │
├──────────────────┤ │
│ card_type_id PK  │─┼──┐
│ hospital_id FK   │─┘  │
│ card_type_code   │    │
│ discount_percent │    │
│ min_lifetime_    │    │
│  spend           │    │
└──────────────────┘    │
                        │
┌────────────────────┐  │
│patient_loyalty_cards │ │
├────────────────────┤  │
│ patient_card_id PK │  │
│ patient_id FK      │──┼──┐
│ card_type_id FK    │──┘  │
│ card_number        │     │
│ issue_date         │     │
│ expiry_date        │     │
│ is_active          │     │
└────────────────────┘     │
                           │
┌────────────────────┐     │
│      patients      │     │
├────────────────────┤     │
│ patient_id PK      │─────┘
│ mrn                │
│ full_name          │
└────────────────────┘
         │
         │
         ▼
┌────────────────────────┐
│  invoice_header        │
├────────────────────────┤
│ invoice_id PK          │───┐
│ patient_id FK          │   │
│ invoice_number         │   │
│ grand_total            │   │
│ total_discount         │   │
└────────────────────────┘   │
                             │
┌────────────────────────┐   │
│  invoice_line_item     │   │
├────────────────────────┤   │
│ line_item_id PK        │───┼──┐
│ invoice_id FK          │───┘  │
│ service_id FK          │      │
│ quantity               │      │
│ unit_price             │      │
│ discount_percent       │      │
│ discount_amount        │      │
│ line_total             │      │
└────────────────────────┘      │
                                │
┌───────────────────────────┐   │
│discount_application_log   │   │
├───────────────────────────┤   │
│ log_id PK                 │   │
│ invoice_id FK             │   │
│ line_item_id FK           │───┘
│ service_id FK             │
│ patient_id FK             │
│ discount_type             │
│ discount_percent          │
│ discount_amount           │
│ original_price            │
│ final_price               │
│ calculation_metadata JSON │
│ service_count_in_invoice  │
│ applied_at                │
└───────────────────────────┘
```

### Table Definitions

#### **hospitals**

| Column | Type | Description |
|--------|------|-------------|
| `hospital_id` | UUID PK | Hospital identifier |
| `name` | VARCHAR(100) | Hospital name |
| `bulk_discount_enabled` | BOOLEAN | Enable/disable bulk discount |
| `bulk_discount_min_service_count` | INTEGER | Min services to trigger (e.g., 5) |
| `bulk_discount_effective_from` | DATE | Policy start date |

**Business Logic:**
- One policy per hospital
- All branches inherit hospital policy
- Effective date allows future activation

**Sample Data:**
```sql
INSERT INTO hospitals (name, bulk_discount_enabled, bulk_discount_min_service_count, bulk_discount_effective_from)
VALUES ('Skinspire Clinic', TRUE, 5, '2025-11-20');
```

#### **services**

| Column | Type | Description |
|--------|------|-------------|
| `service_id` | UUID PK | Service identifier |
| `service_name` | VARCHAR(100) | Service name |
| `price` | NUMERIC(10,2) | Base price (excluding GST) |
| `max_discount` | NUMERIC(5,2) | Maximum allowed discount % |
| `bulk_discount_percent` | NUMERIC(5,2) | Bulk purchase discount % |

**Business Logic:**
- Each service defines its own bulk discount rate
- `bulk_discount_percent` can differ per service (Laser: 10%, Facial: 15%)
- `max_discount` acts as a cap (cannot exceed even if calculated higher)

**Sample Data:**
```sql
UPDATE services
SET bulk_discount_percent = 10.00, max_discount = 15.00
WHERE service_name = 'Laser Hair Reduction';

UPDATE services
SET bulk_discount_percent = 15.00, max_discount = 20.00
WHERE service_name = 'Medifacial';
```

#### **loyalty_card_types**

| Column | Type | Description |
|--------|------|-------------|
| `card_type_id` | UUID PK | Card type identifier |
| `hospital_id` | UUID FK | Hospital owning this card type |
| `card_type_code` | VARCHAR(20) | Unique code (SILVER, GOLD, PLATINUM) |
| `card_type_name` | VARCHAR(50) | Display name |
| `discount_percent` | NUMERIC(5,2) | Discount % for this tier |
| `min_lifetime_spend` | NUMERIC(12,2) | Min spend to qualify |
| `min_visits` | INTEGER | Min visit count to qualify |
| `card_color` | VARCHAR(7) | Hex color for UI |
| `is_active` | BOOLEAN | Active status |

**Business Logic:**
- One set of card types per hospital
- Escalating tiers (Standard < Silver < Gold < Platinum)
- Eligibility criteria: lifetime spend OR visit count
- Visual styling (color) for frontend display

**Sample Data:**
```sql
-- Default card types created by migration:
Standard   - 0%  discount, no requirements
Silver     - 5%  discount, ₹50,000 min spend
Gold       - 10% discount, ₹100,000 min spend
Platinum   - 15% discount, ₹250,000 min spend
```

#### **patient_loyalty_cards**

| Column | Type | Description |
|--------|------|-------------|
| `patient_card_id` | UUID PK | Card assignment identifier |
| `patient_id` | UUID FK | Patient owning the card |
| `card_type_id` | UUID FK | Card type assigned |
| `card_number` | VARCHAR(50) | Physical/digital card number |
| `issue_date` | DATE | Date card was issued |
| `expiry_date` | DATE | Optional expiry date |
| `is_active` | BOOLEAN | Active status |

**Business Logic:**
- One active card per patient (constraint: UNIQUE(patient_id, card_type_id) WHERE is_active)
- Card can have expiry date (NULL = never expires)
- Card number for physical card tracking

**Sample Data:**
```sql
INSERT INTO patient_loyalty_cards (
    patient_id, card_type_id, card_number, issue_date, is_active
)
VALUES (
    'patient-uuid',
    'gold-card-type-uuid',
    'GOLD-000123',
    CURRENT_DATE,
    TRUE
);
```

#### **discount_application_log**

| Column | Type | Description |
|--------|------|-------------|
| `log_id` | UUID PK | Log entry identifier |
| `invoice_id` | UUID FK | Invoice this discount was applied to |
| `line_item_id` | UUID FK | Specific line item discounted |
| `service_id` | UUID FK | Service that was discounted |
| `patient_id` | UUID FK | Patient who received discount |
| `discount_type` | VARCHAR(20) | bulk / loyalty / campaign / manual / none |
| `card_type_id` | UUID FK | If loyalty, which card type |
| `campaign_hook_id` | UUID FK | If campaign, which campaign |
| `original_price` | NUMERIC(12,2) | Price before discount |
| `discount_percent` | NUMERIC(5,2) | Applied discount % |
| `discount_amount` | NUMERIC(12,2) | Discount amount in currency |
| `final_price` | NUMERIC(12,2) | Price after discount |
| `calculation_metadata` | JSONB | Full calculation details |
| `service_count_in_invoice` | INTEGER | Total services in invoice |
| `applied_at` | DATE | When discount was applied |
| `applied_by` | UUID | User who created invoice |

**Business Logic:**
- Immutable audit trail (no updates/deletes)
- One log entry per discounted line item
- JSONB metadata stores:
  - All competing discounts calculated
  - Selection reason
  - Capping information if applicable
  - Service count that triggered bulk discount

**Sample Metadata:**
```json
{
    "service_count": 5,
    "min_threshold": 5,
    "service_name": "Laser Hair Reduction",
    "competing_discounts": [
        {"type": "loyalty", "percent": 5.0, "amount": 250.00}
    ],
    "selection_reason": "Highest discount percentage",
    "capped": false
}
```

---

## Discount Calculation Logic

### Algorithm Pseudocode

```python
def apply_discounts_to_invoice_items(
    session, hospital_id, patient_id, line_items, invoice_date
):
    """
    Main entry point for discount calculation
    """
    # Step 1: Count total services
    service_items = [item for item in line_items if item.type == 'Service']
    total_service_count = len(service_items)

    # Step 2: Apply discount to each service
    for item in service_items:
        # Calculate all applicable discounts
        best_discount = get_best_discount(
            session, hospital_id, item.service_id, patient_id,
            item.unit_price, item.quantity, total_service_count
        )

        # Validate against max_discount
        if best_discount.percent > service.max_discount:
            best_discount.percent = service.max_discount
            best_discount.metadata['capped'] = True

        # Update line item
        item.discount_percent = best_discount.percent
        item.discount_amount = best_discount.amount
        item.discount_type = best_discount.type
        item.discount_metadata = best_discount.metadata

    return line_items


def get_best_discount(
    session, hospital_id, service_id, patient_id,
    unit_price, quantity, total_service_count
):
    """
    Calculate all discounts and select the best one
    """
    discounts = []

    # Discount 1: Bulk
    bulk = calculate_bulk_discount(
        session, hospital_id, service_id, total_service_count,
        unit_price, quantity
    )
    if bulk:
        discounts.append(bulk)

    # Discount 2: Loyalty
    loyalty = calculate_loyalty_discount(
        session, hospital_id, patient_id, service_id,
        unit_price, quantity
    )
    if loyalty:
        discounts.append(loyalty)

    # Discount 3: Campaign (future)
    campaign = calculate_campaign_discount(...)
    if campaign:
        discounts.append(campaign)

    # Select highest
    if not discounts:
        return NO_DISCOUNT

    best = max(discounts, key=lambda d: d.percent)

    # Store competing discounts in metadata
    best.metadata['competing_discounts'] = [
        {type: d.type, percent: d.percent}
        for d in discounts if d != best
    ]

    return best


def calculate_bulk_discount(
    session, hospital_id, service_id, total_service_count,
    unit_price, quantity
):
    """
    Check if bulk discount applies
    """
    # Get hospital policy
    hospital = session.query(Hospital).get(hospital_id)

    # Check if enabled
    if not hospital.bulk_discount_enabled:
        return None

    # Check threshold
    if total_service_count < hospital.bulk_discount_min_service_count:
        return None

    # Check effective date
    if hospital.bulk_discount_effective_from:
        if today < hospital.bulk_discount_effective_from:
            return None

    # Get service discount rate
    service = session.query(Service).get(service_id)
    if not service.bulk_discount_percent or service.bulk_discount_percent == 0:
        return None

    # Calculate discount
    original_price = unit_price * quantity
    discount_percent = service.bulk_discount_percent
    discount_amount = (original_price * discount_percent) / 100
    final_price = original_price - discount_amount

    return DiscountCalculationResult(
        type='bulk',
        percent=discount_percent,
        amount=discount_amount,
        final_price=final_price,
        original_price=original_price,
        metadata={
            'service_count': total_service_count,
            'min_threshold': hospital.bulk_discount_min_service_count
        }
    )


def calculate_loyalty_discount(
    session, hospital_id, patient_id, service_id,
    unit_price, quantity
):
    """
    Check if patient has active loyalty card
    """
    # Query patient's active card
    patient_card = session.query(PatientLoyaltyCard).join(
        LoyaltyCardType
    ).filter(
        PatientLoyaltyCard.patient_id == patient_id,
        PatientLoyaltyCard.is_active == True,
        LoyaltyCardType.is_active == True,
        OR(
            PatientLoyaltyCard.expiry_date == None,
            PatientLoyaltyCard.expiry_date >= today
        )
    ).first()

    if not patient_card:
        return None

    card_type = patient_card.card_type
    if not card_type.discount_percent or card_type.discount_percent == 0:
        return None

    # Calculate discount
    original_price = unit_price * quantity
    discount_percent = card_type.discount_percent
    discount_amount = (original_price * discount_percent) / 100
    final_price = original_price - discount_amount

    return DiscountCalculationResult(
        type='loyalty',
        percent=discount_percent,
        amount=discount_amount,
        final_price=final_price,
        original_price=original_price,
        card_type_id=card_type.card_type_id,
        metadata={
            'card_type_code': card_type.card_type_code,
            'card_type_name': card_type.card_type_name,
            'card_number': patient_card.card_number
        }
    )
```

### Calculation Examples

#### Example 1: Basic Bulk Discount

**Setup:**
```
Hospital: bulk_discount_min_service_count = 5
Service: Laser Hair Reduction
  - price: ₹5,000
  - bulk_discount_percent: 10%
  - max_discount: 15%
Patient: No loyalty card
```

**Invoice:**
```
Line Item 1: Laser Hair Reduction x 5
```

**Calculation:**
```
Step 1: Count services
  total_service_count = 5

Step 2: Check bulk discount eligibility
  5 >= 5 (threshold) ✓
  hospital.bulk_discount_enabled = TRUE ✓
  service.bulk_discount_percent = 10% ✓

Step 3: Calculate bulk discount
  original_price = 5,000 × 5 = ₹25,000
  discount_percent = 10%
  discount_amount = 25,000 × 10% = ₹2,500
  final_price = 25,000 - 2,500 = ₹22,500

Step 4: Check loyalty discount
  patient has no card → None

Step 5: Select best discount
  bulk: 10% ✓ SELECTED
  loyalty: None

Result:
  Each line item gets 10% discount
  Total discount: ₹2,500
  Total payable: ₹22,500
```

#### Example 2: Loyalty vs Bulk Discount

**Setup:**
```
Hospital: bulk_discount_min_service_count = 5
Service: Medifacial
  - price: ₹3,000
  - bulk_discount_percent: 15%
  - max_discount: 20%
Patient: Gold card (10% discount)
```

**Invoice:**
```
Line Item 1: Medifacial x 5
```

**Calculation:**
```
Step 1: Count services
  total_service_count = 5

Step 2: Calculate bulk discount
  original_price = 3,000 × 5 = ₹15,000
  bulk_discount_percent = 15%
  bulk_discount_amount = 15,000 × 15% = ₹2,250

Step 3: Calculate loyalty discount
  loyalty_discount_percent = 10%
  loyalty_discount_amount = 15,000 × 10% = ₹1,500

Step 4: Select best discount
  bulk: 15% (₹2,250) ✓ SELECTED
  loyalty: 10% (₹1,500)

Result:
  Applied discount: 15% bulk
  Total discount: ₹2,250
  Total payable: ₹12,750
  Metadata: {competing_discounts: [{type: 'loyalty', percent: 10}]}
```

#### Example 3: Max Discount Capping

**Setup:**
```
Hospital: bulk_discount_min_service_count = 5
Service: Botox Injection
  - price: ₹10,000
  - bulk_discount_percent: 15%
  - max_discount: 8%
Patient: Platinum card (15% discount)
```

**Invoice:**
```
Line Item 1: Botox Injection x 5
```

**Calculation:**
```
Step 1: Count services
  total_service_count = 5

Step 2: Calculate bulk discount
  bulk_discount_percent = 15%

Step 3: Calculate loyalty discount
  loyalty_discount_percent = 15%

Step 4: Select best discount
  Both equal at 15%, select bulk

Step 5: Validate against max_discount
  calculated_discount = 15%
  max_discount = 8%
  15% > 8% → CAP at 8% ✓

Result:
  Applied discount: 8% (capped from 15%)
  original_price = 10,000 × 5 = ₹50,000
  discount_amount = 50,000 × 8% = ₹4,000
  Total payable: ₹46,000
  Metadata: {
      capped: true,
      original_best: 15,
      cap_reason: "Exceeds max_discount of 8%"
  }
```

#### Example 4: Below Threshold

**Setup:**
```
Hospital: bulk_discount_min_service_count = 5
Service: Laser Hair Reduction
  - price: ₹5,000
  - bulk_discount_percent: 10%
Patient: Silver card (5% discount)
```

**Invoice:**
```
Line Item 1: Laser Hair Reduction x 4
```

**Calculation:**
```
Step 1: Count services
  total_service_count = 4

Step 2: Check bulk discount eligibility
  4 < 5 (threshold) ✗
  Bulk discount NOT triggered

Step 3: Calculate loyalty discount
  loyalty_discount_percent = 5%
  original_price = 5,000 × 4 = ₹20,000
  discount_amount = 20,000 × 5% = ₹1,000

Step 4: Select best discount
  bulk: Not applicable
  loyalty: 5% ✓ SELECTED

Result:
  Applied discount: 5% loyalty
  Total discount: ₹1,000
  Total payable: ₹19,000
```

---

## API Reference

### Python Service API

#### `DiscountService.apply_discounts_to_invoice_items()`

**Purpose:** Main integration point - applies discounts to all service items in an invoice

**Signature:**
```python
@staticmethod
def apply_discounts_to_invoice_items(
    session: Session,
    hospital_id: str,
    patient_id: str,
    line_items: List[Dict],
    invoice_date: date = None,
    respect_max_discount: bool = True
) -> List[Dict]:
```

**Parameters:**
- `session` - SQLAlchemy database session
- `hospital_id` - UUID of the hospital
- `patient_id` - UUID of the patient
- `line_items` - List of dictionaries representing invoice line items
- `invoice_date` - Date of invoice (defaults to today)
- `respect_max_discount` - Whether to enforce service max_discount limits

**Returns:**
- Updated `line_items` list with discount fields populated:
  - `discount_percent` (float)
  - `discount_amount` (float)
  - `discount_type` (str: 'bulk'/'loyalty'/'campaign'/'manual'/'none')
  - `discount_metadata` (dict)
  - `card_type_id` (UUID, if loyalty)

**Usage Example:**
```python
from app.services.discount_service import DiscountService
from app.services.database_service import get_db_session

with get_db_session() as session:
    line_items = [
        {
            'item_type': 'Service',
            'item_id': 'service-uuid-1',
            'item_name': 'Laser Hair Reduction',
            'unit_price': 5000.00,
            'quantity': 3
        },
        {
            'item_type': 'Service',
            'item_id': 'service-uuid-2',
            'item_name': 'Medifacial',
            'unit_price': 3000.00,
            'quantity': 2
        }
    ]

    # Apply discounts
    discounted_items = DiscountService.apply_discounts_to_invoice_items(
        session=session,
        hospital_id='hospital-uuid',
        patient_id='patient-uuid',
        line_items=line_items
    )

    # Check results
    for item in discounted_items:
        if item['discount_percent'] > 0:
            print(f"{item['item_name']}: {item['discount_type']} "
                  f"discount of {item['discount_percent']}%")
```

#### `DiscountService.get_best_discount()`

**Purpose:** Calculate all applicable discounts and return the highest one

**Signature:**
```python
@staticmethod
def get_best_discount(
    session: Session,
    hospital_id: str,
    service_id: str,
    patient_id: str,
    unit_price: Decimal,
    quantity: int,
    total_service_count: int,
    invoice_date: date = None
) -> DiscountCalculationResult:
```

**Returns:**
- `DiscountCalculationResult` object with:
  - `discount_type` (str)
  - `discount_percent` (Decimal)
  - `discount_amount` (Decimal)
  - `final_price` (Decimal)
  - `original_price` (Decimal)
  - `metadata` (dict)
  - `card_type_id` (UUID, optional)
  - `campaign_hook_id` (UUID, optional)

**Usage Example:**
```python
best_discount = DiscountService.get_best_discount(
    session=session,
    hospital_id='hospital-uuid',
    service_id='service-uuid',
    patient_id='patient-uuid',
    unit_price=Decimal('5000.00'),
    quantity=5,
    total_service_count=7
)

print(f"Best discount: {best_discount.discount_type} - {best_discount.discount_percent}%")
print(f"Competing discounts: {best_discount.metadata.get('competing_discounts')}")
```

#### `DiscountService.validate_discount()`

**Purpose:** Validate that a discount percentage doesn't exceed service max_discount

**Signature:**
```python
@staticmethod
def validate_discount(
    session: Session,
    service_id: str,
    discount_percent: Decimal
) -> Tuple[bool, Optional[str]]:
```

**Returns:**
- Tuple of `(is_valid: bool, error_message: str | None)`

**Usage Example:**
```python
is_valid, error_msg = DiscountService.validate_discount(
    session=session,
    service_id='service-uuid',
    discount_percent=Decimal('15.00')
)

if not is_valid:
    print(f"Validation failed: {error_msg}")
```

#### `DiscountService.log_discount_application()`

**Purpose:** Create audit log entry for a discount application

**Signature:**
```python
@staticmethod
def log_discount_application(
    session: Session,
    hospital_id: str,
    invoice_id: str,
    line_item_id: str,
    service_id: str,
    patient_id: str,
    discount_result: DiscountCalculationResult,
    service_count_in_invoice: int,
    applied_by: str = None
) -> DiscountApplicationLog:
```

**Returns:**
- Created `DiscountApplicationLog` ORM object

**Usage Example:**
```python
log_entry = DiscountService.log_discount_application(
    session=session,
    hospital_id='hospital-uuid',
    invoice_id='invoice-uuid',
    line_item_id='line-item-uuid',
    service_id='service-uuid',
    patient_id='patient-uuid',
    discount_result=best_discount,
    service_count_in_invoice=5,
    applied_by='user-uuid'
)

session.add(log_entry)
session.commit()
```

#### `DiscountService.get_discount_summary()`

**Purpose:** Generate discount usage report for a date range

**Signature:**
```python
@staticmethod
def get_discount_summary(
    session: Session,
    hospital_id: str,
    start_date: date,
    end_date: date,
    discount_type: str = None
) -> Dict:
```

**Returns:**
- Dictionary with discount summary statistics:
```json
{
    "period": {"start_date": "2025-11-01", "end_date": "2025-11-30"},
    "total_discount_applications": 150,
    "total_discount_amount": 75000.00,
    "total_original_amount": 500000.00,
    "discount_percentage_overall": 15.0,
    "by_discount_type": {
        "bulk": {
            "count": 100,
            "total_discount": 50000.00,
            "total_original": 400000.00,
            "avg_discount_percent": 12.5
        },
        "loyalty": {
            "count": 50,
            "total_discount": 25000.00,
            "total_original": 100000.00,
            "avg_discount_percent": 10.0
        }
    }
}
```

**Usage Example:**
```python
from datetime import date

summary = DiscountService.get_discount_summary(
    session=session,
    hospital_id='hospital-uuid',
    start_date=date(2025, 11, 1),
    end_date=date(2025, 11, 30),
    discount_type='bulk'  # Optional filter
)

print(f"Total discounts given: ₹{summary['total_discount_amount']:,.2f}")
print(f"Bulk discounts: {summary['by_discount_type']['bulk']['count']} applications")
```

---

### REST API Endpoints

The Discount API provides REST endpoints for real-time discount calculations and configuration retrieval. All endpoints are available under the `/api/discount` prefix.

#### Health Check & Debug Endpoints

##### `GET /api/discount/health`

**Purpose:** Simple health check endpoint to verify API is running

**Response:**
```json
{
    "status": "ok",
    "message": "Discount API is running",
    "endpoints": [
        "/api/discount/health",
        "/api/discount/debug",
        "/api/discount/config/<hospital_id>",
        "/api/discount/calculate",
        "/api/discount/patient-loyalty/<patient_id>"
    ]
}
```

**Status Codes:**
- `200 OK` - API is operational

**Usage Example:**
```bash
curl http://localhost:5000/api/discount/health
```

---

##### `GET /api/discount/debug`

**Purpose:** System diagnostics and debug information

**Response:**
```json
{
    "status": "ok",
    "timestamp": "2025-11-20T17:30:00.000Z",
    "python_version": "3.13.0",
    "database": {
        "status": "connected",
        "info": {
            "hospitals": 1,
            "services": 13
        }
    },
    "discount_service": {
        "imported": true,
        "methods": [
            "apply_discounts_to_invoice_items",
            "calculate_bulk_discount",
            "calculate_campaign_discount",
            "calculate_loyalty_discount",
            "get_best_discount",
            "get_discount_summary",
            "log_discount_application",
            "validate_discount"
        ]
    }
}
```

**Status Codes:**
- `200 OK` - Debug information retrieved successfully

**Usage Example:**
```bash
curl http://localhost:5000/api/discount/debug
```

---

##### `GET /api/discount/test-config/<hospital_id>`

**Purpose:** Lightweight test endpoint for hospital discount configuration (simplified version)

**Parameters:**
- `hospital_id` (path) - Hospital UUID

**Response (Success):**
```json
{
    "success": true,
    "hospital": {
        "id": "4ef72e18-e65d-4766-b9eb-0308c42485ca",
        "name": "Skinspire Clinic",
        "bulk_discount_enabled": true,
        "bulk_discount_min_service_count": 5
    }
}
```

**Response (Error):**
```json
{
    "success": false,
    "error": "Hospital not found",
    "hospital_id": "invalid-uuid"
}
```

**Status Codes:**
- `200 OK` - Configuration retrieved
- `404 Not Found` - Hospital not found
- `500 Internal Server Error` - Server error

**Usage Example:**
```bash
curl http://localhost:5000/api/discount/test-config/4ef72e18-e65d-4766-b9eb-0308c42485ca
```

---

#### Production Endpoints

##### `GET /api/discount/config/<hospital_id>`

**Purpose:** Get complete discount configuration for a hospital including all service discount rates

**Parameters:**
- `hospital_id` (path) - Hospital UUID

**Response:**
```json
{
    "success": true,
    "hospital_config": {
        "hospital_id": "4ef72e18-e65d-4766-b9eb-0308c42485ca",
        "hospital_name": "Skinspire Clinic",
        "bulk_discount_enabled": true,
        "bulk_discount_min_service_count": 5,
        "bulk_discount_effective_from": "2025-11-01"
    },
    "service_discounts": {
        "service-uuid-1": {
            "service_id": "service-uuid-1",
            "service_name": "Laser Hair Reduction",
            "price": 5000.00,
            "bulk_discount_percent": 10.00,
            "max_discount": 100.00,
            "has_bulk_discount": true
        },
        "service-uuid-2": {
            "service_id": "service-uuid-2",
            "service_name": "Medifacial",
            "price": 3000.00,
            "bulk_discount_percent": 15.00,
            "max_discount": 20.00,
            "has_bulk_discount": true
        }
    }
}
```

**Status Codes:**
- `200 OK` - Configuration retrieved successfully
- `404 Not Found` - Hospital not found
- `500 Internal Server Error` - Server error

**Usage Example:**
```javascript
// Frontend usage in invoice_bulk_discount.js
async loadDiscountConfig() {
    const response = await fetch(
        `/api/discount/config/${this.hospitalId}`
    );
    const data = await response.json();

    if (data.success) {
        this.hospitalConfig = data.hospital_config;
        this.serviceDiscounts = data.service_discounts;
    }
}
```

---

##### `POST /api/discount/calculate`

**Purpose:** Calculate discounts for invoice line items in real-time

**Request Body:**
```json
{
    "hospital_id": "hospital-uuid",
    "patient_id": "patient-uuid",
    "line_items": [
        {
            "item_type": "Service",
            "service_id": "service-uuid-1",
            "item_id": "service-uuid-1",
            "item_name": "Laser Hair Reduction",
            "quantity": 3,
            "unit_price": 5000.00
        },
        {
            "item_type": "Service",
            "service_id": "service-uuid-2",
            "item_id": "service-uuid-2",
            "item_name": "Medifacial",
            "quantity": 2,
            "unit_price": 3000.00
        }
    ]
}
```

**Response:**
```json
{
    "success": true,
    "line_items": [
        {
            "item_type": "Service",
            "service_id": "service-uuid-1",
            "item_name": "Laser Hair Reduction",
            "quantity": 3,
            "unit_price": 5000.00,
            "discount_percent": 10.00,
            "discount_amount": 1500.00,
            "discount_type": "bulk",
            "final_price": 13500.00,
            "discount_metadata": {
                "competing_discounts": []
            }
        },
        {
            "item_type": "Service",
            "service_id": "service-uuid-2",
            "item_name": "Medifacial",
            "quantity": 2,
            "unit_price": 3000.00,
            "discount_percent": 15.00,
            "discount_amount": 900.00,
            "discount_type": "bulk",
            "final_price": 5100.00
        }
    ],
    "summary": {
        "total_services": 5,
        "bulk_discount_eligible": true,
        "bulk_discount_threshold": 5,
        "services_needed": 0,
        "total_original_price": 21000.00,
        "total_discount": 2400.00,
        "total_final_price": 18600.00,
        "discount_percentage": 11.43,
        "potential_savings": {
            "applicable": false,
            "message": "Bulk discount already applied"
        }
    }
}
```

**Status Codes:**
- `200 OK` - Discounts calculated successfully
- `400 Bad Request` - Missing required fields
- `500 Internal Server Error` - Calculation error

**Usage Example:**
```javascript
// Frontend usage in invoice_bulk_discount.js
async applyDiscounts(eligibleItems) {
    const response = await fetch('/api/discount/calculate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            hospital_id: this.hospitalId,
            patient_id: this.patientId,
            line_items: eligibleItems
        })
    });

    const data = await response.json();

    if (data.success) {
        this.updatePricingDisplay(data.summary);
        this.updateLineItems(data.line_items);
    }
}
```

---

##### `GET /api/discount/patient-loyalty/<patient_id>`

**Purpose:** Get patient's loyalty card information

**Parameters:**
- `patient_id` (path) - Patient UUID

**Response (With Loyalty Card):**
```json
{
    "success": true,
    "has_loyalty_card": true,
    "card": {
        "card_number": "PLAT-2025-001",
        "card_type_name": "Platinum",
        "card_type_code": "PLATINUM",
        "discount_percent": 15.00,
        "card_color": "#C0C0C0",
        "issue_date": "2025-01-01",
        "expiry_date": "2026-01-01"
    }
}
```

**Response (No Loyalty Card):**
```json
{
    "success": true,
    "has_loyalty_card": false,
    "message": "No active loyalty card"
}
```

**Status Codes:**
- `200 OK` - Information retrieved
- `500 Internal Server Error` - Server error

**Usage Example:**
```javascript
// Check patient loyalty status
async checkPatientLoyalty(patientId) {
    const response = await fetch(
        `/api/discount/patient-loyalty/${patientId}`
    );
    const data = await response.json();

    if (data.success && data.has_loyalty_card) {
        this.displayLoyaltyBadge(data.card);
    }
}
```

---

### Testing the API

#### Using cURL

```bash
# Test health check
curl http://localhost:5000/api/discount/health

# Get debug information
curl http://localhost:5000/api/discount/debug

# Test hospital config (simplified)
curl http://localhost:5000/api/discount/test-config/YOUR-HOSPITAL-UUID

# Get full discount configuration
curl http://localhost:5000/api/discount/config/YOUR-HOSPITAL-UUID

# Calculate discounts
curl -X POST http://localhost:5000/api/discount/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "hospital_id": "YOUR-HOSPITAL-UUID",
    "patient_id": "YOUR-PATIENT-UUID",
    "line_items": [
      {
        "item_type": "Service",
        "service_id": "SERVICE-UUID",
        "quantity": 5,
        "unit_price": 5000.00
      }
    ]
  }'

# Get patient loyalty info
curl http://localhost:5000/api/discount/patient-loyalty/YOUR-PATIENT-UUID
```

#### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:5000"

# Health check
response = requests.get(f"{BASE_URL}/api/discount/health")
print(response.json())

# Debug info
response = requests.get(f"{BASE_URL}/api/discount/debug")
debug_data = response.json()
print(f"Database status: {debug_data['database']['status']}")
print(f"Hospitals: {debug_data['database']['info']['hospitals']}")

# Test config
hospital_id = "YOUR-HOSPITAL-UUID"
response = requests.get(f"{BASE_URL}/api/discount/test-config/{hospital_id}")
config = response.json()
if config['success']:
    print(f"Bulk discount enabled: {config['hospital']['bulk_discount_enabled']}")

# Calculate discounts
payload = {
    "hospital_id": hospital_id,
    "patient_id": None,
    "line_items": [
        {"item_type": "Service", "service_id": "...", "quantity": 5, "unit_price": 5000}
    ]
}
response = requests.post(f"{BASE_URL}/api/discount/calculate", json=payload)
result = response.json()
print(f"Total discount: ₹{result['summary']['total_discount']}")
```

#### Automated Test Suite

A comprehensive test suite is available at `test_discount_endpoints.py`:

```bash
# Run all endpoint tests
python test_discount_endpoints.py

# Expected output:
# ======================================================================
# DISCOUNT API ENDPOINT TEST SUITE
# ======================================================================
#
# TEST: Health Check Endpoint
# [OK] PASS: Health check passed - Status: ok
#
# TEST: Debug Endpoint
# [OK] PASS: Debug endpoint passed
#     Database status: connected
#     Hospitals: 1
#     Services: 13
#
# TEST: Test Config Endpoint
# [OK] PASS: Test config passed
#     Hospital: Skinspire Clinic
#
# TEST: Full Discount Config Endpoint
# [OK] PASS: Full config passed
#     Total services: 13
#     Services with bulk discount: 3
#
# ======================================================================
# TEST SUMMARY
# ======================================================================
# Total: 5/5 tests passed
# SUCCESS: All tests passed!
```

---

## Configuration Guide

### Hospital Configuration

**Set Bulk Discount Policy:**

```sql
-- Enable bulk discount with threshold of 5 services
UPDATE hospitals
SET bulk_discount_enabled = TRUE,
    bulk_discount_min_service_count = 5,
    bulk_discount_effective_from = CURRENT_DATE
WHERE hospital_id = 'your-hospital-uuid';

-- Verify
SELECT name, bulk_discount_enabled, bulk_discount_min_service_count
FROM hospitals;
```

**Adjust Threshold:**

```sql
-- Lower threshold to 3 services
UPDATE hospitals
SET bulk_discount_min_service_count = 3
WHERE name = 'Skinspire Clinic';
```

**Disable Bulk Discount:**

```sql
-- Temporarily disable (can re-enable later)
UPDATE hospitals
SET bulk_discount_enabled = FALSE
WHERE name = 'Skinspire Clinic';
```

### Service Configuration

**Set Bulk Discount Percentage:**

```sql
-- Individual service
UPDATE services
SET bulk_discount_percent = 10.00
WHERE service_name = 'Laser Hair Reduction';

-- Multiple services by pattern
UPDATE services
SET bulk_discount_percent = 15.00
WHERE service_name LIKE '%Facial%'
  AND (max_discount IS NULL OR max_discount >= 15.00);

-- By service type
UPDATE services
SET bulk_discount_percent = 12.00
WHERE service_type = 'Body Treatment';
```

**Verify Configuration:**

```sql
-- List services with bulk discounts
SELECT
    service_name,
    bulk_discount_percent,
    max_discount,
    CASE
        WHEN bulk_discount_percent > max_discount THEN 'EXCEEDS MAX'
        WHEN bulk_discount_percent = 0 THEN 'NO DISCOUNT'
        ELSE 'VALID'
    END as status
FROM services
ORDER BY bulk_discount_percent DESC, service_name;
```

**Bulk Configuration Script:**

```sql
-- Example: Configure all services at once
WITH discount_config AS (
    SELECT UNNEST(ARRAY[
        'Laser Hair Removal', 'Laser Skin Resurfacing', 'Laser Tattoo Removal'
    ]) AS service_pattern, 10.00 AS discount_percent
    UNION ALL
    SELECT UNNEST(ARRAY['Basic Facial', 'Advanced Facial', 'Medifacial']), 15.00
    UNION ALL
    SELECT UNNEST(ARRAY['Chemical Peel', 'Microdermabrasion']), 12.00
    UNION ALL
    SELECT UNNEST(ARRAY['Botox', 'Dermal Filler']), 5.00
)
UPDATE services s
SET bulk_discount_percent = dc.discount_percent
FROM discount_config dc
WHERE s.service_name LIKE '%' || dc.service_pattern || '%'
  AND (s.max_discount IS NULL OR s.max_discount >= dc.discount_percent);
```

### Loyalty Card Configuration

**Create Custom Card Type:**

```sql
-- Add VIP tier (20% discount)
INSERT INTO loyalty_card_types (
    hospital_id,
    card_type_code,
    card_type_name,
    description,
    discount_percent,
    min_lifetime_spend,
    card_color,
    display_sequence,
    is_active
)
SELECT
    hospital_id,
    'VIP',
    'VIP Member',
    'Exclusive VIP membership with 20% discount on all services',
    20.00,
    500000.00,  -- ₹5 lakh lifetime spend
    '#FF0000',   -- Red
    5,
    TRUE
FROM hospitals
WHERE name = 'Skinspire Clinic';
```

**Modify Existing Card Type:**

```sql
-- Increase Gold discount from 10% to 12%
UPDATE loyalty_card_types
SET discount_percent = 12.00
WHERE card_type_code = 'GOLD';

-- Lower Silver eligibility threshold
UPDATE loyalty_card_types
SET min_lifetime_spend = 30000.00
WHERE card_type_code = 'SILVER';
```

**Assign Card to Patient:**

```sql
-- Assign Platinum card to patient
INSERT INTO patient_loyalty_cards (
    hospital_id,
    patient_id,
    card_type_id,
    card_number,
    issue_date,
    expiry_date,  -- NULL = never expires
    is_active
)
VALUES (
    'hospital-uuid',
    'patient-uuid',
    (SELECT card_type_id FROM loyalty_card_types
     WHERE card_type_code = 'PLATINUM' AND hospital_id = 'hospital-uuid'),
    'PLAT-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-001',
    CURRENT_DATE,
    NULL,  -- Never expires
    TRUE
);
```

**Bulk Assign Cards Based on Spend:**

```sql
-- Automatically upgrade patients based on lifetime spend
INSERT INTO patient_loyalty_cards (
    hospital_id, patient_id, card_type_id, card_number, issue_date, is_active
)
SELECT
    ih.hospital_id,
    ih.patient_id,
    lct.card_type_id,
    lct.card_type_code || '-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || ROW_NUMBER() OVER(),
    CURRENT_DATE,
    TRUE
FROM (
    -- Calculate lifetime spend per patient
    SELECT
        hospital_id,
        patient_id,
        SUM(grand_total) as lifetime_spend
    FROM invoice_header
    WHERE is_cancelled = FALSE
    GROUP BY hospital_id, patient_id
) AS ih
JOIN loyalty_card_types lct ON ih.hospital_id = lct.hospital_id
WHERE ih.lifetime_spend >= lct.min_lifetime_spend
  AND lct.card_type_code != 'STANDARD'
  AND NOT EXISTS (
      -- Don't create duplicate cards
      SELECT 1 FROM patient_loyalty_cards plc
      WHERE plc.patient_id = ih.patient_id
        AND plc.is_active = TRUE
  )
ORDER BY ih.lifetime_spend DESC;
```

---

## User Guide

### For Front Desk Staff

#### Creating an Invoice with Bulk Discount

**Scenario:** Patient wants 5 laser hair reduction sessions

**Steps:**
1. Create new invoice for patient
2. Add 5 × "Laser Hair Reduction" line items
3. System automatically applies 10% bulk discount to each line item
4. Verify discount appears in the "Discount %" column
5. Review total savings displayed
6. Process payment as usual

**What You'll See:**
```
Service: Laser Hair Reduction (qty: 5)
Unit Price: ₹5,000
Discount: 10% (Bulk) 🔵
Discount Amount: -₹500
Line Total: ₹4,500
```

#### Checking Patient Loyalty Card

**Before Creating Invoice:**
1. Open patient profile
2. Look for "Loyalty Card" section
3. Note the card tier (Silver/Gold/Platinum)
4. System will automatically apply loyalty discount if applicable

**During Invoice Creation:**
- If patient has Gold card (10%) and bulk discount is 15%
- System will apply 15% bulk discount (higher)
- Discount badge will show "Bulk 15%" instead of "Loyalty 10%"

#### Manual Discount Override

**When to Use:**
- Customer complaints resolution
- Manager approval for special cases
- Promotional offers not in system

**How to Override:**
1. Create invoice normally (automatic discount applies)
2. Click on discount percentage field
3. Enter new discount percentage
4. System validates against max_discount limit
5. If exceeds limit, shows error message
6. Save invoice

**Example:**
```
Automatic Discount: 10% bulk
Max Discount: 15%
Manual Override: 12% ✓ (within limit)
Manual Override: 18% ✗ (exceeds max, blocked)
```

#### Troubleshooting

**Issue: Discount Not Applying**

Check:
1. Count service items → Must be ≥ 5 (or hospital threshold)
2. Check if services have bulk_discount_percent > 0
3. Verify patient loyalty card is active (if expecting loyalty discount)
4. Ask manager to check hospital bulk discount settings

**Issue: Discount Lower Than Expected**

Explanation:
- Service has max_discount limit
- System caps at this limit even if calculated discount is higher
- Example: Bulk = 15%, but max_discount = 10% → Applied = 10%

### For Patients

#### Understanding Your Discount

**Bulk Purchase Discount:**
- When you book 5+ services in one visit, you save more!
- Different services have different discount rates
- Example: 5 laser sessions = 10% off, 5 facials = 15% off

**Loyalty Card Benefits:**
```
Silver Card   - 5% discount on all services
Gold Card     - 10% discount on all services
Platinum Card - 15% discount on all services
```

**How to Maximize Savings:**
- Book multiple sessions together (5 or more)
- Ask about combining different services
- Upgrade your loyalty card by spending more
- System automatically gives you the best discount

**Sample Savings:**
```
Without Discount:
  5 × Laser Hair Reduction @ ₹5,000 = ₹25,000

With 10% Bulk Discount:
  5 × Laser Hair Reduction @ ₹4,500 = ₹22,500
  You Save: ₹2,500

With Platinum Card (15%):
  5 × Laser Hair Reduction @ ₹4,250 = ₹21,250
  You Save: ₹3,750
```

---

## Admin Guide

### Dashboard & Monitoring

#### Daily Discount Report

```sql
-- Today's discount summary
SELECT
    discount_type,
    COUNT(*) as applications,
    SUM(discount_amount) as total_discount,
    SUM(original_price) as total_sales,
    ROUND(SUM(discount_amount) / SUM(original_price) * 100, 2) as discount_rate
FROM discount_application_log
WHERE applied_at = CURRENT_DATE
GROUP BY discount_type
ORDER BY total_discount DESC;
```

**Expected Output:**
```
discount_type | applications | total_discount | total_sales | discount_rate
--------------+--------------+----------------+-------------+--------------
bulk          |          45  |    22,500.00   |  180,000.00 |         12.50
loyalty       |          20  |     8,000.00   |   80,000.00 |         10.00
manual        |           5  |     3,000.00   |   25,000.00 |         12.00
```

#### Top Services by Discount Usage

```sql
-- Services with highest discount usage this month
SELECT
    s.service_name,
    COUNT(dal.log_id) as times_discounted,
    AVG(dal.discount_percent) as avg_discount_pct,
    SUM(dal.discount_amount) as total_discount_given
FROM discount_application_log dal
JOIN services s ON dal.service_id = s.service_id
WHERE dal.applied_at >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY s.service_name
ORDER BY total_discount_given DESC
LIMIT 10;
```

#### Loyalty Card Utilization

```sql
-- Active loyalty cards and their usage
SELECT
    lct.card_type_name,
    COUNT(DISTINCT plc.patient_id) as active_cardholders,
    COUNT(dal.log_id) as discount_uses,
    SUM(dal.discount_amount) as total_discount_value,
    ROUND(AVG(dal.discount_percent), 2) as avg_discount_pct
FROM loyalty_card_types lct
LEFT JOIN patient_loyalty_cards plc
    ON lct.card_type_id = plc.card_type_id
    AND plc.is_active = TRUE
LEFT JOIN discount_application_log dal
    ON dal.card_type_id = lct.card_type_id
    AND dal.applied_at >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY lct.card_type_name, lct.display_sequence
ORDER BY lct.display_sequence;
```

### Policy Management

#### Adjusting Bulk Discount Thresholds

**Analyze Current Distribution:**

```sql
-- Count invoices by service count
SELECT
    service_count_in_invoice,
    COUNT(*) as invoice_count,
    SUM(discount_amount) as total_discounts
FROM discount_application_log
WHERE discount_type = 'bulk'
  AND applied_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY service_count_in_invoice
ORDER BY service_count_in_invoice;
```

**Decision Making:**
- If most invoices have 3-4 services: Consider lowering threshold to 3
- If few invoices reach threshold: Consider lowering to boost adoption
- If too many invoices qualify: Consider raising to control costs

**Implementation:**
```sql
-- Lower threshold to 3 services
UPDATE hospitals
SET bulk_discount_min_service_count = 3
WHERE name = 'Skinspire Clinic';

-- Monitor impact over next 7 days
SELECT
    applied_at::date as date,
    COUNT(*) as bulk_discounts_given,
    SUM(discount_amount) as total_discount
FROM discount_application_log
WHERE discount_type = 'bulk'
  AND applied_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY applied_at::date
ORDER BY applied_at::date;
```

#### Service Discount Optimization

**Identify Under-Used Services:**

```sql
-- Services rarely discounted (may need higher bulk discount)
SELECT
    s.service_name,
    s.bulk_discount_percent,
    COUNT(dal.log_id) as discount_count
FROM services s
LEFT JOIN discount_application_log dal
    ON s.service_id = dal.service_id
    AND dal.discount_type = 'bulk'
    AND dal.applied_at >= DATE_TRUNC('month', CURRENT_DATE)
WHERE s.bulk_discount_percent > 0
GROUP BY s.service_name, s.bulk_discount_percent
HAVING COUNT(dal.log_id) < 5
ORDER BY discount_count;
```

**Increase Discount for Low-Demand Services:**

```sql
-- Boost discount from 10% to 15% to stimulate demand
UPDATE services
SET bulk_discount_percent = 15.00
WHERE service_name = 'Laser Tattoo Removal'
  AND max_discount >= 15.00;
```

#### Loyalty Program Management

**Upgrade Eligible Patients:**

```sql
-- Find patients eligible for upgrade based on lifetime spend
WITH patient_spend AS (
    SELECT
        ih.hospital_id,
        ih.patient_id,
        p.full_name,
        p.mrn,
        SUM(ih.grand_total) as lifetime_spend,
        COALESCE(plc.card_type_id, NULL) as current_card_id
    FROM invoice_header ih
    JOIN patients p ON ih.patient_id = p.patient_id
    LEFT JOIN patient_loyalty_cards plc
        ON ih.patient_id = plc.patient_id
        AND plc.is_active = TRUE
    WHERE ih.is_cancelled = FALSE
    GROUP BY ih.hospital_id, ih.patient_id, p.full_name, p.mrn, plc.card_type_id
),
eligible_upgrades AS (
    SELECT
        ps.*,
        lct_current.card_type_name as current_card,
        lct_eligible.card_type_name as eligible_card,
        lct_eligible.card_type_id as eligible_card_id
    FROM patient_spend ps
    LEFT JOIN loyalty_card_types lct_current
        ON ps.current_card_id = lct_current.card_type_id
    JOIN loyalty_card_types lct_eligible
        ON ps.hospital_id = lct_eligible.hospital_id
        AND ps.lifetime_spend >= lct_eligible.min_lifetime_spend
        AND (ps.current_card_id IS NULL
             OR lct_eligible.display_sequence > COALESCE((
                SELECT display_sequence
                FROM loyalty_card_types
                WHERE card_type_id = ps.current_card_id
             ), 0))
)
SELECT
    mrn,
    full_name,
    lifetime_spend,
    COALESCE(current_card, 'None') as current_card,
    eligible_card,
    eligible_card_id
FROM eligible_upgrades
ORDER BY lifetime_spend DESC;
```

**Send Upgrade Notifications:**

```sql
-- Export list for marketing team
\copy (SELECT mrn, full_name, lifetime_spend, eligible_card FROM eligible_upgrades) TO '/tmp/loyalty_upgrades.csv' CSV HEADER;
```

---

## Reporting & Analytics

### Standard Reports

#### 1. Discount Impact Report

**Purpose:** Assess financial impact of discounts on revenue

```sql
WITH monthly_stats AS (
    SELECT
        DATE_TRUNC('month', applied_at) as month,
        discount_type,
        COUNT(*) as applications,
        SUM(original_price) as gross_revenue,
        SUM(discount_amount) as total_discounts,
        SUM(final_price) as net_revenue
    FROM discount_application_log
    WHERE applied_at >= CURRENT_DATE - INTERVAL '6 months'
    GROUP BY DATE_TRUNC('month', applied_at), discount_type
)
SELECT
    TO_CHAR(month, 'YYYY-MM') as month,
    discount_type,
    applications,
    ROUND(gross_revenue, 2) as gross_revenue,
    ROUND(total_discounts, 2) as total_discounts,
    ROUND(net_revenue, 2) as net_revenue,
    ROUND((total_discounts / gross_revenue * 100), 2) as discount_rate_pct
FROM monthly_stats
ORDER BY month DESC, total_discounts DESC;
```

#### 2. Service Profitability Analysis

**Purpose:** Identify which services are most/least profitable after discounts

```sql
WITH service_performance AS (
    SELECT
        s.service_name,
        s.bulk_discount_percent,
        s.max_discount,
        COUNT(DISTINCT dal.invoice_id) as invoices,
        COUNT(dal.log_id) as line_items,
        SUM(dal.original_price) as gross_revenue,
        SUM(dal.discount_amount) as discounts_given,
        SUM(dal.final_price) as net_revenue,
        AVG(dal.discount_percent) as avg_discount_pct
    FROM services s
    LEFT JOIN discount_application_log dal
        ON s.service_id = dal.service_id
        AND dal.applied_at >= CURRENT_DATE - INTERVAL '30 days'
    WHERE s.is_active = TRUE
    GROUP BY s.service_id, s.service_name, s.bulk_discount_percent, s.max_discount
)
SELECT
    service_name,
    bulk_discount_percent as configured_discount,
    ROUND(avg_discount_pct, 2) as actual_avg_discount,
    invoices,
    line_items,
    ROUND(gross_revenue, 2) as gross_revenue,
    ROUND(discounts_given, 2) as discounts_given,
    ROUND(net_revenue, 2) as net_revenue,
    ROUND((discounts_given / NULLIF(gross_revenue, 0) * 100), 2) as discount_rate_pct,
    CASE
        WHEN avg_discount_pct > bulk_discount_percent THEN 'Over Target'
        WHEN avg_discount_pct < bulk_discount_percent THEN 'Under Target'
        ELSE 'On Target'
    END as performance
FROM service_performance
WHERE gross_revenue > 0
ORDER BY net_revenue DESC;
```

#### 3. Patient Discount Behavior

**Purpose:** Understand which patients utilize discounts most

```sql
WITH patient_discount_usage AS (
    SELECT
        p.patient_id,
        p.mrn,
        p.full_name,
        lct.card_type_name,
        COUNT(DISTINCT dal.invoice_id) as invoices_with_discount,
        SUM(dal.discount_amount) as total_savings,
        AVG(dal.service_count_in_invoice) as avg_services_per_invoice,
        SUM(CASE WHEN dal.discount_type = 'bulk' THEN 1 ELSE 0 END) as bulk_uses,
        SUM(CASE WHEN dal.discount_type = 'loyalty' THEN 1 ELSE 0 END) as loyalty_uses
    FROM patients p
    JOIN discount_application_log dal ON p.patient_id = dal.patient_id
    LEFT JOIN patient_loyalty_cards plc
        ON p.patient_id = plc.patient_id
        AND plc.is_active = TRUE
    LEFT JOIN loyalty_card_types lct
        ON plc.card_type_id = lct.card_type_id
    WHERE dal.applied_at >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY p.patient_id, p.mrn, p.full_name, lct.card_type_name
)
SELECT
    mrn,
    full_name,
    COALESCE(card_type_name, 'No Card') as loyalty_card,
    invoices_with_discount,
    ROUND(total_savings, 2) as total_savings,
    ROUND(avg_services_per_invoice, 1) as avg_services_per_invoice,
    bulk_uses,
    loyalty_uses,
    CASE
        WHEN bulk_uses > loyalty_uses THEN 'Bulk Buyer'
        WHEN loyalty_uses > bulk_uses THEN 'Loyal Customer'
        ELSE 'Mixed'
    END as customer_type
FROM patient_discount_usage
ORDER BY total_savings DESC
LIMIT 50;
```

#### 4. Discount Effectiveness Dashboard

**Purpose:** Executive summary of discount program performance

```sql
-- Overall metrics
SELECT
    'Today' as period,
    COUNT(DISTINCT invoice_id) as invoices_with_discounts,
    COUNT(*) as line_items_discounted,
    ROUND(SUM(original_price), 2) as gross_revenue,
    ROUND(SUM(discount_amount), 2) as total_discounts,
    ROUND(SUM(final_price), 2) as net_revenue,
    ROUND(AVG(discount_percent), 2) as avg_discount_pct,
    ROUND((SUM(discount_amount) / SUM(original_price) * 100), 2) as overall_discount_rate
FROM discount_application_log
WHERE applied_at = CURRENT_DATE

UNION ALL

SELECT
    'This Month',
    COUNT(DISTINCT invoice_id),
    COUNT(*),
    ROUND(SUM(original_price), 2),
    ROUND(SUM(discount_amount), 2),
    ROUND(SUM(final_price), 2),
    ROUND(AVG(discount_percent), 2),
    ROUND((SUM(discount_amount) / SUM(original_price) * 100), 2)
FROM discount_application_log
WHERE applied_at >= DATE_TRUNC('month', CURRENT_DATE)

UNION ALL

SELECT
    'Last 90 Days',
    COUNT(DISTINCT invoice_id),
    COUNT(*),
    ROUND(SUM(original_price), 2),
    ROUND(SUM(discount_amount), 2),
    ROUND(SUM(final_price), 2),
    ROUND(AVG(discount_percent), 2),
    ROUND((SUM(discount_amount) / SUM(original_price) * 100), 2)
FROM discount_application_log
WHERE applied_at >= CURRENT_DATE - INTERVAL '90 days';
```

### Data Export for Analysis

#### Export to CSV

```sql
-- Export detailed discount log
\copy (
    SELECT
        dal.applied_at,
        dal.invoice_id,
        p.mrn as patient_mrn,
        p.full_name as patient_name,
        s.service_name,
        dal.quantity,
        dal.original_price,
        dal.discount_type,
        dal.discount_percent,
        dal.discount_amount,
        dal.final_price,
        lct.card_type_name as loyalty_card,
        dal.service_count_in_invoice
    FROM discount_application_log dal
    JOIN patients p ON dal.patient_id = p.patient_id
    JOIN services s ON dal.service_id = s.service_id
    LEFT JOIN loyalty_card_types lct ON dal.card_type_id = lct.card_type_id
    WHERE dal.applied_at >= CURRENT_DATE - INTERVAL '30 days'
    ORDER BY dal.applied_at DESC
) TO '/tmp/discounts_30days.csv' CSV HEADER;
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Discount Not Applying

**Symptoms:**
- User creates invoice with 5+ services
- No discount appears in line items
- discount_percent = 0

**Diagnosis Steps:**

```sql
-- Step 1: Check hospital configuration
SELECT
    name,
    bulk_discount_enabled,
    bulk_discount_min_service_count,
    bulk_discount_effective_from
FROM hospitals
WHERE hospital_id = 'your-hospital-uuid';
```

**Expected:** `enabled = TRUE`, `min_count ≤ service count in invoice`

```sql
-- Step 2: Check service configuration
SELECT
    service_name,
    bulk_discount_percent,
    max_discount,
    is_active
FROM services
WHERE service_id = 'problematic-service-uuid';
```

**Expected:** `bulk_discount_percent > 0`, `is_active = TRUE`

```sql
-- Step 3: Check patient loyalty card
SELECT
    plc.*,
    lct.card_type_name,
    lct.discount_percent
FROM patient_loyalty_cards plc
JOIN loyalty_card_types lct ON plc.card_type_id = lct.card_type_id
WHERE plc.patient_id = 'patient-uuid'
  AND plc.is_active = TRUE;
```

**Possible Causes:**
1. Hospital bulk discount disabled → Enable it
2. Service bulk_discount_percent = 0 → Set to desired %
3. Service count below threshold → Lower threshold or add more services
4. Effective date in future → Check bulk_discount_effective_from

**Solution:**
```sql
-- Fix most common issue: service not configured
UPDATE services
SET bulk_discount_percent = 10.00
WHERE service_id = 'problematic-service-uuid'
  AND (max_discount IS NULL OR max_discount >= 10.00);
```

#### Issue 2: Wrong Discount Selected

**Symptoms:**
- System applies bulk discount when loyalty discount is higher
- Or vice versa

**Diagnosis:**

```sql
-- Check discount calculation log
SELECT
    discount_type,
    discount_percent,
    calculation_metadata
FROM discount_application_log
WHERE invoice_id = 'problem-invoice-uuid'
ORDER BY applied_at DESC
LIMIT 1;
```

**Look for:**
- `calculation_metadata->>'competing_discounts'`: Shows all calculated discounts
- `calculation_metadata->>'selection_reason'`: Why this one was selected

**Example Metadata:**
```json
{
    "competing_discounts": [
        {"type": "loyalty", "percent": 5.0, "amount": 250.00}
    ],
    "selection_reason": "Highest discount percentage",
    "service_count": 5,
    "min_threshold": 5
}
```

**Possible Causes:**
1. Loyalty card inactive/expired → Check patient_loyalty_cards.is_active
2. Bulk discount percentage higher → Verify service.bulk_discount_percent
3. Comparison logic error → Check application logs for errors

#### Issue 3: Discount Exceeds Maximum

**Symptoms:**
- User manually enters 20% discount
- System shows error: "Exceeds maximum allowed discount"

**Diagnosis:**

```sql
-- Check service max_discount
SELECT
    service_name,
    max_discount,
    bulk_discount_percent
FROM services
WHERE service_id = 'service-uuid';
```

**Possible Causes:**
1. Service has low max_discount (e.g., 5%)
2. User trying to apply higher discount manually

**Solutions:**

**Option A: Increase max_discount (permanent)**
```sql
UPDATE services
SET max_discount = 25.00
WHERE service_id = 'service-uuid';
```

**Option B: Manager override (one-time)**
- Requires approval workflow (future enhancement)
- Temporarily increase max_discount for this patient

**Option C: Explain to user**
- This service has a maximum discount policy
- Contact manager for special cases

#### Issue 4: Audit Log Missing Entries

**Symptoms:**
- Discount applied successfully
- No entry in discount_application_log table

**Diagnosis:**

```sql
-- Check if invoice exists
SELECT COUNT(*) FROM invoice_header WHERE invoice_id = 'invoice-uuid';

-- Check if log entries exist for this invoice
SELECT COUNT(*) FROM discount_application_log WHERE invoice_id = 'invoice-uuid';
```

**Possible Causes:**
1. Logging function not called (code bug)
2. Transaction rolled back after discount applied
3. Database error during log insertion

**Solution:**

```bash
# Check application logs
tail -f /path/to/app.log | grep -i "discount"

# Look for errors like:
# ERROR: Failed to create discount log entry: ...
```

**Manual Log Creation (if needed):**
```sql
-- Recreate log entries from invoice line items
INSERT INTO discount_application_log (
    hospital_id, invoice_id, line_item_id, service_id, patient_id,
    discount_type, discount_percent, discount_amount,
    original_price, final_price, applied_at,
    service_count_in_invoice, calculation_metadata
)
SELECT
    ih.hospital_id,
    ili.invoice_id,
    ili.line_item_id,
    ili.service_id,
    ih.patient_id,
    'manual' as discount_type,
    ili.discount_percent,
    ili.discount_amount,
    (ili.unit_price * ili.quantity) as original_price,
    ili.line_total as final_price,
    ih.invoice_date::date as applied_at,
    (SELECT COUNT(*) FROM invoice_line_item WHERE invoice_id = ih.invoice_id AND item_type = 'Service') as service_count,
    '{"manually_recreated": true}'::jsonb as metadata
FROM invoice_line_item ili
JOIN invoice_header ih ON ili.invoice_id = ih.invoice_id
WHERE ili.invoice_id = 'invoice-uuid'
  AND ili.item_type = 'Service'
  AND ili.discount_percent > 0
  AND NOT EXISTS (
      SELECT 1 FROM discount_application_log
      WHERE line_item_id = ili.line_item_id
  );
```

### Performance Issues

#### Issue: Slow Discount Calculation

**Symptoms:**
- Invoice creation takes > 5 seconds
- Timeout errors in UI

**Diagnosis:**

```sql
-- Check database query performance
EXPLAIN ANALYZE
SELECT * FROM patient_loyalty_cards plc
JOIN loyalty_card_types lct ON plc.card_type_id = lct.card_type_id
WHERE plc.patient_id = 'patient-uuid'
  AND plc.is_active = TRUE;
```

**Possible Causes:**
1. Missing indexes on patient_loyalty_cards
2. Too many joins in discount calculation
3. Large discount_application_log table

**Solutions:**

**Add Missing Indexes:**
```sql
-- Index on patient_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_patient_loyalty_patient_active
ON patient_loyalty_cards(patient_id)
WHERE is_active = TRUE AND is_deleted = FALSE;

-- Composite index for service discount lookups
CREATE INDEX IF NOT EXISTS idx_services_discount
ON services(service_id, bulk_discount_percent, max_discount)
WHERE is_active = TRUE;
```

**Optimize Queries:**
- Use session-level caching for hospital config
- Cache service discount percentages
- Avoid N+1 queries (batch load services)

**Clean Up Old Logs (if table too large):**
```sql
-- Archive logs older than 1 year
CREATE TABLE discount_application_log_archive AS
SELECT * FROM discount_application_log
WHERE applied_at < CURRENT_DATE - INTERVAL '1 year';

DELETE FROM discount_application_log
WHERE applied_at < CURRENT_DATE - INTERVAL '1 year';

-- Vacuum to reclaim space
VACUUM FULL discount_application_log;
```

---

## Integration Points

### Billing System Integration

**File:** `app/services/billing_service.py`

**Integration Point:** `_create_invoice()` function

```python
# Line 844-881 in billing_service.py
try:
    logger.info("DISCOUNT CALCULATION: Starting automatic discount application")

    # Apply discounts to service items
    line_items = DiscountService.apply_discounts_to_invoice_items(
        session=session,
        hospital_id=hospital_id,
        patient_id=patient_id,
        line_items=line_items,
        invoice_date=invoice_date.date() if isinstance(invoice_date, datetime) else invoice_date,
        respect_max_discount=True
    )

    # Log discount application summary
    service_items_with_discount = [
        item for item in line_items
        if item.get('item_type') == 'Service' and item.get('discount_percent', 0) > 0
    ]

    if service_items_with_discount:
        logger.info(f"✅ Applied discounts to {len(service_items_with_discount)} service items")

except Exception as e:
    logger.error(f"❌ Error during discount calculation: {str(e)}", exc_info=True)
    logger.warning("⚠️ Continuing with invoice creation without automatic discounts")
```

**Key Points:**
- Discount calculation happens **before** line item processing
- Wrapped in try-except to prevent invoice creation failure
- Logs all discount applications for debugging
- Returns updated `line_items` with discount fields populated

### Invoice Line Item Processing

**File:** `app/services/billing_service.py`

**Function:** `_process_invoice_line_item()`

The discount fields from `line_items` are used when creating `InvoiceLineItem` objects:

```python
# Line item creation uses discount fields
line_item = InvoiceLineItem(
    invoice_id=invoice.invoice_id,
    item_type=item_data['item_type'],
    service_id=item_data.get('service_id'),
    quantity=item_data['quantity'],
    unit_price=item_data['unit_price'],
    discount_percent=item_data.get('discount_percent', Decimal('0')),  # ← From discount_service
    discount_amount=item_data.get('discount_amount', Decimal('0')),    # ← From discount_service
    taxable_amount=item_data['taxable_amount'],
    line_total=item_data['line_total']
)
```

### Universal Engine Integration

**For List/View Pages:**

The discount fields are already in the database, so Universal Engine list/view pages automatically show them:

```python
# In patient_invoice_config.py
FieldDefinition(
    name='discount_percent',
    label='Discount %',
    field_type=FieldType.NUMBER,
    display_in_list=True,
    display_in_view=True
)
```

**For Custom Invoice Templates:**

Discount information can be rendered in invoice PDFs/HTML:

```html
<!-- In invoice template -->
<td>{{ line_item.service_name }}</td>
<td class="text-right">₹{{ line_item.unit_price|number_format }}</td>
<td class="text-right">
    {% if line_item.discount_percent > 0 %}
        <span class="discount-badge {{ line_item.discount_type }}">
            {{ line_item.discount_type|title }} {{ line_item.discount_percent }}%
        </span>
    {% else %}
        -
    {% endif %}
</td>
<td class="text-right">₹{{ line_item.line_total|number_format }}</td>
```

### Future: Frontend API Endpoint

**Endpoint:** `/api/calculate_discounts` (to be implemented)

**Purpose:** Allow frontend to calculate discounts before invoice submission

**Request:**
```json
POST /api/calculate_discounts
{
    "hospital_id": "uuid",
    "patient_id": "uuid",
    "invoice_date": "2025-11-20",
    "line_items": [
        {"service_id": "uuid", "quantity": 3, "unit_price": 5000.00},
        {"service_id": "uuid", "quantity": 2, "unit_price": 3000.00}
    ]
}
```

**Response:**
```json
{
    "success": true,
    "line_items": [
        {
            "service_id": "uuid",
            "service_name": "Laser Hair Reduction",
            "quantity": 3,
            "unit_price": 5000.00,
            "discount_type": "bulk",
            "discount_percent": 10.00,
            "discount_amount": 1500.00,
            "final_price": 13500.00,
            "discount_metadata": {
                "service_count": 5,
                "competing_discounts": []
            }
        }
    ],
    "summary": {
        "total_services": 5,
        "bulk_discount_triggered": true,
        "total_discount": 3000.00
    }
}
```

---

## Security & Audit

### Audit Trail

Every discount application is logged in `discount_application_log` with:

1. **Who:** `applied_by` (user_id who created invoice)
2. **What:** `discount_type`, `discount_percent`, `discount_amount`
3. **When:** `applied_at` (date of application)
4. **Why:** `calculation_metadata` (full calculation details)
5. **Where:** `invoice_id`, `line_item_id` (trace back to invoice)
6. **Context:** `service_count_in_invoice`, `patient_id`, `service_id`

### Immutability

- `discount_application_log` table is **append-only** (no updates/deletes)
- Original calculations preserved even if invoice is modified later
- Audit trail cannot be tampered with

### Data Privacy

**Sensitive Data:**
- Patient MRN and name (personally identifiable)
- Discount amounts (financial data)

**Access Controls:**
- Discount logs only accessible by authorized users
- Reports should filter by hospital_id (multi-tenant isolation)
- Export functions should require manager/admin role

### Compliance

**Financial Auditing:**
- All discounts traceable to specific invoices
- Calculation methodology documented in metadata
- Can regenerate financial reports for any date range

**Tax Compliance:**
- Discounts applied **before** GST calculation (correct tax base)
- Discount amount shown separately on invoice
- Audit trail for tax authority inquiries

---

## Future Enhancements

### Phase 2: Frontend UI

**Priority: Medium | Effort: 2-3 days**

**Features:**
1. **Discount Badge on Line Items**
   - Visual indicator: "Bulk 10%" or "Loyalty 5%"
   - Color-coded: Blue (bulk), Gold (loyalty), Green (campaign)
   - Tooltip showing calculation details

2. **Discount Notification**
   - Alert when adding 5th service: "Bulk discount now available!"
   - Show potential savings: "Add 1 more service to save ₹500"

3. **Discount Summary Panel**
   - Total discount breakdown
   - Savings comparison: "You're saving ₹2,500 today!"

**Implementation:**
```javascript
// invoice.js
function showDiscountOpportunity() {
    const serviceCount = countServiceItems();
    const threshold = hospitalConfig.bulk_discount_min_service_count;

    if (serviceCount >= threshold) {
        showNotification('success', `Bulk discount active! ${serviceCount} services`);
    } else if (serviceCount === threshold - 1) {
        showNotification('info', `Add 1 more service to unlock bulk discount!`);
    }
}
```

### Phase 3: Campaign Discounts

**Priority: High | Effort: 3-5 days**

**Concept:** Time-bound promotional discounts using existing `CampaignHookConfig`

**Examples:**
- "Weekend Special: 20% off all facials (Sat-Sun)"
- "Birthday Month: 15% off for patients with birthday this month"
- "New Year Offer: 25% off packages (Jan 1-15)"
- "Referral Bonus: 10% off for referred patients"

**Implementation:**
```python
# app/campaigns/weekend_special.py
def calculate_weekend_discount(context):
    if context['invoice_date'].weekday() in [5, 6]:  # Sat, Sun
        if 'facial' in context['service_name'].lower():
            return {
                'discount_percent': 20.00,
                'campaign_name': 'Weekend Special'
            }
    return None
```

**Configuration:**
```sql
INSERT INTO campaign_hook_config (
    hospital_id,
    hook_name,
    hook_type,
    hook_module_path,
    hook_function_name,
    applies_to_services,
    effective_from,
    effective_to,
    is_active,
    hook_config
)
VALUES (
    'hospital-uuid',
    'Weekend Facial Special',
    'python_module',
    'app.campaigns.weekend_special',
    'calculate_weekend_discount',
    TRUE,
    '2025-11-20',
    '2025-12-31',
    TRUE,
    '{"service_pattern": "facial", "discount_percent": 20, "days": [6, 7]}'::jsonb
);
```

### Phase 4: Discount Approval Workflow

**Priority: Low | Effort: 5-7 days**

**Concept:** Require manager approval for high-value discounts

**Rules:**
- Discounts > 20% → Require L1 approval
- Discounts > 30% OR > ₹10,000 → Require L2 approval
- Manual overrides → Always require approval

**Workflow:**
```
1. User creates invoice with high discount
2. System flags for approval (status: 'pending_approval')
3. Manager receives notification
4. Manager reviews and approves/rejects
5. If approved, invoice is finalized
6. If rejected, user must adjust discount
```

**Database:**
```sql
-- Add approval tracking
ALTER TABLE invoice_header
ADD COLUMN discount_approval_status VARCHAR(20),
ADD COLUMN discount_approval_required BOOLEAN DEFAULT FALSE,
ADD COLUMN discount_approved_by UUID,
ADD COLUMN discount_approved_at TIMESTAMP;
```

### Phase 5: Dynamic Pricing

**Priority: Low | Effort: 10+ days**

**Concept:** AI-driven dynamic pricing based on demand, inventory, season

**Features:**
- Demand-based: Higher discounts during low-demand periods
- Inventory-based: Promote services with available slots
- Seasonal: Adjust discounts based on seasonal trends
- Patient-specific: Personalized offers based on history

**Example:**
```python
def calculate_dynamic_discount(service, patient, date):
    score = 0

    # Factor 1: Demand (30%)
    if get_booking_rate(service, date) < 0.5:
        score += 30

    # Factor 2: Patient Value (40%)
    if patient.lifetime_spend > 100000:
        score += 40
    elif patient.lifetime_spend > 50000:
        score += 20

    # Factor 3: Season (30%)
    if is_off_season(date):
        score += 30

    return min(score, service.max_discount)
```

### Phase 6: Combo Offers

**Priority: Medium | Effort: 5-7 days**

**Concept:** Pre-defined service combinations with special pricing

**Examples:**
- "Bridal Package: Facial + Hair + Makeup = 25% off"
- "Hair Removal Combo: Full body = 30% off"
- "Skin Care Bundle: 3 facials + 2 peels = 20% off"

**Database:**
```sql
CREATE TABLE combo_offers (
    combo_id UUID PRIMARY KEY,
    hospital_id UUID REFERENCES hospitals(hospital_id),
    combo_name VARCHAR(100),
    description TEXT,
    discount_percent NUMERIC(5,2),
    effective_from DATE,
    effective_to DATE,
    is_active BOOLEAN
);

CREATE TABLE combo_offer_items (
    combo_item_id UUID PRIMARY KEY,
    combo_id UUID REFERENCES combo_offers(combo_id),
    service_id UUID REFERENCES services(service_id),
    quantity INTEGER,
    is_mandatory BOOLEAN
);
```

**Logic:**
```python
def check_combo_eligibility(line_items):
    for combo in active_combos:
        required_items = combo.get_items()
        if all(item in line_items for item in required_items):
            return combo.discount_percent
    return None
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-20 | Initial release with bulk and loyalty discounts |
| 1.1.0 | TBD | Frontend UI enhancements |
| 1.2.0 | TBD | Campaign discount integration |
| 2.0.0 | TBD | Approval workflow |

---

## Support & Contact

**Technical Support:**
- Email: tech@skinspire.com
- Phone: +91-XXX-XXX-XXXX

**Documentation:**
- Implementation Guide: `Project_docs/Implementation Plan/Bulk Service Discount Implementation Summary.md`
- Deployment Summary: `Project_docs/Implementation Plan/Deployment Summary - Bulk Discounts LIVE.md`
- This Reference: `Project_docs/reference docs/Bulk Service Discount System - Complete Reference Guide.md`

**Code Repository:**
- Migration: `migrations/20251120_create_bulk_discount_system.sql`
- Service: `app/services/discount_service.py`
- Models: `app/models/master.py`
- Integration: `app/services/billing_service.py`

---

**Document End**
