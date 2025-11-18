# GST and MRP Versioning - Implementation Guide

**Date**: 2025-11-17
**Priority**: HIGH - Tax Compliance
**Status**: Ready for Implementation

---

## What We've Built

### 1. Core Pricing & GST Versioning ✅ READY
**Files Created**:
- `migrations/create_entity_pricing_tax_config.sql` - Database migration
- `app/models/config.py` - Added `EntityPricingTaxConfig` model
- `Project_docs/PRICING_AND_GST_VERSIONING_DESIGN.md` - Complete design document

**Purpose**: Date-based versioning of:
- GST rates (government notification tracking)
- MRP/pricing (manufacturer notification tracking)

### 2. Campaign Hook Architecture ✅ DESIGNED (Future)
**Files Created**:
- `Project_docs/CAMPAIGN_HOOK_ARCHITECTURE.md` - Plugin architecture design
- `Project_docs/PROMOTIONAL_PRICING_DESIGN.md` - Detailed campaign design (reference)

**Purpose**: Optional plugin system for hospital-specific promotional campaigns

---

## Implementation Priority

### Phase 1: NOW (Tax Compliance) - IMPLEMENT IMMEDIATELY

**Goal**: GST and MRP versioning for tax compliance

**Steps**:

#### Step 1: Run Database Migration

```bash
# Connect to your database
psql -U postgres -d skinspire_db

# Run the migration
\i migrations/create_entity_pricing_tax_config.sql
```

**Verify**:
```sql
-- Check table created
SELECT COUNT(*) FROM entity_pricing_tax_config;

-- Check indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'entity_pricing_tax_config';
```

#### Step 2: Create Service Layer

**File to create**: `app/services/pricing_tax_service.py`

**Core Functions Needed**:
1. `get_applicable_pricing_and_tax()` - Get pricing/GST for a date
2. `add_pricing_tax_change()` - Record a price/GST change
3. `get_config_history()` - View change history

**Template** (simplified, you can expand):
```python
"""
Pricing and Tax Service - Date-based pricing and GST rate lookup
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.config import EntityPricingTaxConfig
from app.models.master import Medicine, Service, Package
import logging

logger = logging.getLogger(__name__)


def get_applicable_pricing_and_tax(
    session: Session,
    hospital_id: str,
    entity_type: str,  # 'medicine', 'service', 'package'
    entity_id: str,
    applicable_date: date
) -> Dict:
    """
    Get pricing and GST rate applicable for a given entity on a specific date.

    Priority:
    1. Date-specific config from entity_pricing_tax_config
    2. Current values from master table (fallback)
    """
    entity_id_column = f"{entity_type}_id"

    # Try to find config for the date
    config = session.query(EntityPricingTaxConfig).filter(
        and_(
            EntityPricingTaxConfig.hospital_id == hospital_id,
            getattr(EntityPricingTaxConfig, entity_id_column) == entity_id,
            EntityPricingTaxConfig.effective_from <= applicable_date,
            or_(
                EntityPricingTaxConfig.effective_to == None,
                EntityPricingTaxConfig.effective_to >= applicable_date
            ),
            EntityPricingTaxConfig.is_deleted == False
        )
    ).order_by(EntityPricingTaxConfig.effective_from.desc()).first()

    if config:
        logger.info(f"Found pricing/tax config for {entity_type} {entity_id} on {applicable_date}")
        return {
            # GST fields
            'gst_rate': config.gst_rate or Decimal('0'),
            'cgst_rate': config.cgst_rate or Decimal('0'),
            'sgst_rate': config.sgst_rate or Decimal('0'),
            'igst_rate': config.igst_rate or Decimal('0'),
            'is_gst_exempt': config.is_gst_exempt or False,
            'gst_inclusive': config.gst_inclusive or False,
            # Pricing
            'mrp': config.mrp,
            'selling_price': config.selling_price,
            'cost_price': config.cost_price,
            'applicable_price': config.applicable_price,
            # Metadata
            'source': 'config',
            'config_id': config.config_id
        }

    # Fallback to master table
    logger.warning(f"No config found for {entity_type} {entity_id} on {applicable_date}. Using master table.")

    if entity_type == 'medicine':
        entity = session.query(Medicine).filter_by(medicine_id=entity_id).first()
        if entity:
            return {
                'gst_rate': entity.gst_rate or Decimal('0'),
                'cgst_rate': entity.cgst_rate or Decimal('0'),
                'sgst_rate': entity.sgst_rate or Decimal('0'),
                'igst_rate': entity.igst_rate or Decimal('0'),
                'is_gst_exempt': entity.is_gst_exempt or False,
                'gst_inclusive': entity.gst_inclusive or False,
                'mrp': entity.mrp,
                'selling_price': entity.selling_price,
                'cost_price': entity.cost_price,
                'applicable_price': entity.mrp or entity.selling_price,
                'source': 'master_table',
                'config_id': None
            }

    # Similar for service and package...

    # Default
    return {
        'gst_rate': Decimal('0'),
        'cgst_rate': Decimal('0'),
        'sgst_rate': Decimal('0'),
        'igst_rate': Decimal('0'),
        'is_gst_exempt': False,
        'source': 'default',
        'config_id': None
    }


def add_pricing_tax_change(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str,
    effective_from: date,
    current_user_id: Optional[str] = None,
    **kwargs  # mrp, gst_rate, etc.
) -> EntityPricingTaxConfig:
    """
    Add a new pricing/tax configuration change.
    Automatically closes the previous config's effective period.
    """
    entity_id_column = f"{entity_type}_id"

    # Close previous config (if exists)
    previous_config = session.query(EntityPricingTaxConfig).filter(
        and_(
            EntityPricingTaxConfig.hospital_id == hospital_id,
            getattr(EntityPricingTaxConfig, entity_id_column) == entity_id,
            EntityPricingTaxConfig.effective_to == None,
            EntityPricingTaxConfig.is_deleted == False
        )
    ).first()

    if previous_config:
        previous_config.effective_to = effective_from - timedelta(days=1)
        previous_config.updated_by = current_user_id

    # Create new config
    new_config = EntityPricingTaxConfig(
        hospital_id=hospital_id,
        **{entity_id_column: entity_id},
        effective_from=effective_from,
        effective_to=None,
        created_by=current_user_id,
        **kwargs
    )

    session.add(new_config)
    session.flush()

    logger.info(f"Created new pricing/tax config: {new_config.config_id}")

    return new_config
```

#### Step 3: Update Invoice Creation (billing_service.py)

**Find this section** (around line 1289):
```python
medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
if medicine:
    gst_rate = medicine.gst_rate or Decimal('0')
    # ... rest of code
```

**Replace with**:
```python
from app.services.pricing_tax_service import get_applicable_pricing_and_tax
from datetime import date

medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
if medicine:
    # Get pricing/GST applicable on invoice date (NOT current rate)
    invoice_date = invoice_data.get('invoice_date', datetime.now()).date()

    pricing_tax = get_applicable_pricing_and_tax(
        session=session,
        hospital_id=hospital_id,
        entity_type='medicine',
        entity_id=item_id,
        applicable_date=invoice_date
    )

    # Use versioned values
    gst_rate = pricing_tax['gst_rate']
    cgst_rate = pricing_tax['cgst_rate']
    sgst_rate = pricing_tax['sgst_rate']
    igst_rate = pricing_tax['igst_rate']
    is_gst_exempt = pricing_tax['is_gst_exempt']
    gst_inclusive = pricing_tax.get('gst_inclusive', True)

    hsn_sac_code = medicine.hsn_code
    cost_price = pricing_tax.get('cost_price') or medicine.cost_price

    logger.info(f"Medicine '{medicine.medicine_name}': Using {pricing_tax['source']} - "
                f"GST={gst_rate}% for date {invoice_date}")
```

**Do the same for**:
- Service-based line items
- Package-based line items

---

### Phase 2: FUTURE (Optional Campaign Hooks)

**When**: After Phase 1 is stable and hospitals request promotional campaigns

**What**: Implement the campaign hook architecture from `CAMPAIGN_HOOK_ARCHITECTURE.md`

**Benefits**:
- Hospitals can plug in custom campaign logic
- No core code changes needed
- Each hospital can have unique promotions

---

## Usage Examples

### Example 1: Record GST Rate Change

**Scenario**: Government increases medicine GST from 12% to 18% effective April 1, 2025

```python
from app.services.pricing_tax_service import add_pricing_tax_change
from datetime import date
from decimal import Decimal

add_pricing_tax_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    effective_from=date(2025, 4, 1),
    change_type='gst_change',
    gst_rate=Decimal('18'),
    cgst_rate=Decimal('9'),
    sgst_rate=Decimal('9'),
    igst_rate=Decimal('18'),
    gst_notification_number='No. 01/2025-Central Tax (Rate)',
    gst_notification_date=date(2025, 3, 15),
    change_reason='Government GST rate increase',
    current_user_id=admin_user_id,
    # Keep current pricing (no change)
    mrp=Decimal('500')
)
```

**Result**:
- Invoices dated March 31 → Use 12% GST
- Invoices dated April 1 onwards → Use 18% GST

### Example 2: Record MRP Change

**Scenario**: Manufacturer increases MRP from ₹500 to ₹550 effective July 1, 2025

```python
add_pricing_tax_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    effective_from=date(2025, 7, 1),
    change_type='price_change',
    mrp=Decimal('550'),
    manufacturer_notification='Price Revision 2025/07',
    manufacturer_notification_date=date(2025, 6, 15),
    price_revision_reason='Raw material cost increase',
    current_user_id=admin_user_id,
    # Keep current GST (no change)
    gst_rate=Decimal('18'),
    cgst_rate=Decimal('9'),
    sgst_rate=Decimal('9'),
    igst_rate=Decimal('18')
)
```

### Example 3: Combined Change

**Scenario**: Both MRP and GST change on same date

```python
add_pricing_tax_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    effective_from=date(2025, 1, 1),
    change_type='both',
    # Price change
    mrp=Decimal('600'),
    manufacturer_notification='Combined Revision 2025/01',
    # GST change
    gst_rate=Decimal('12'),
    cgst_rate=Decimal('6'),
    sgst_rate=Decimal('6'),
    igst_rate=Decimal('12'),
    gst_notification_number='No. 47/2024-Central Tax (Rate)',
    change_reason='Combined price and GST revision',
    current_user_id=admin_user_id
)
```

---

## Testing Strategy

### Test 1: Create Invoice Before Rate Change
```python
# Create invoice dated March 31, 2025
# Verify it uses old rate (12%)
```

### Test 2: Create Invoice On Rate Change Date
```python
# Create invoice dated April 1, 2025
# Verify it uses new rate (18%)
```

### Test 3: Create Invoice After Rate Change
```python
# Create invoice dated April 15, 2025
# Verify it uses new rate (18%)
```

### Test 4: Fallback to Master Table
```python
# Create invoice for medicine with NO config
# Verify it uses master table rates
```

---

## Database Queries for Verification

### Check All Configs for a Medicine
```sql
SELECT
    config_id,
    effective_from,
    effective_to,
    mrp,
    gst_rate,
    change_type,
    change_reason
FROM entity_pricing_tax_config
WHERE medicine_id = 'your-medicine-uuid'
  AND is_deleted = false
ORDER BY effective_from DESC;
```

### Get Current Config for a Medicine
```sql
SELECT *
FROM entity_pricing_tax_config
WHERE medicine_id = 'your-medicine-uuid'
  AND effective_from <= CURRENT_DATE
  AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
  AND is_deleted = false;
```

### Find All Open-Ended Configs (Currently Effective)
```sql
SELECT
    medicine_id,
    effective_from,
    mrp,
    gst_rate
FROM entity_pricing_tax_config
WHERE effective_to IS NULL
  AND is_deleted = false;
```

---

## Benefits

### Tax Compliance ✅
- Historical accuracy for tax audits
- Government notification tracking
- Date-based rate selection ensures compliance

### Business Operations ✅
- No manual master data updates needed
- Audit trail of all changes
- Manufacturer notification tracking

### Reporting ✅
- Rate change history available
- Impact analysis possible
- Complete change documentation

---

## Key Design Decisions

### 1. Single Table for Both Pricing and GST ✅
**Why**: Atomic changes, single lookup, simpler querying

### 2. Optional Campaign Hooks (Not Core) ✅
**Why**: Campaign logic is hospital-specific, should be pluggable

### 3. Fallback to Master Table ✅
**Why**: System works even without configs, gradual migration

### 4. Soft Delete ✅
**Why**: Preserve history, audit requirements

---

## Implementation Checklist

### Database
- [ ] Run migration: `migrations/create_entity_pricing_tax_config.sql`
- [ ] Verify table created with correct constraints
- [ ] Verify indexes created

### Code
- [ ] Create `app/services/pricing_tax_service.py`
- [ ] Update `app/services/billing_service.py` medicine lookup
- [ ] Update service lookup (if used)
- [ ] Update package lookup (if used)

### Testing
- [ ] Test invoice creation before rate change date
- [ ] Test invoice creation on rate change date
- [ ] Test invoice creation after rate change date
- [ ] Test fallback to master table

### Documentation
- [ ] Document how to add rate changes
- [ ] Train users on rate change process
- [ ] Create admin guide for notifications

---

## Next Steps

1. **Review this guide** and the design documents
2. **Run the database migration** on dev database
3. **Create the service layer** (`pricing_tax_service.py`)
4. **Update invoice creation** to use new service
5. **Test thoroughly** with various dates
6. **Deploy to production** after testing

---

**Questions?** Review these documents:
- `Project_docs/PRICING_AND_GST_VERSIONING_DESIGN.md` - Complete technical design
- `Project_docs/CAMPAIGN_HOOK_ARCHITECTURE.md` - Future campaign hooks (optional)

**Status**: ✅ Ready to implement Phase 1 (GST/MRP versioning)

*Prepared by: Claude Code*
*Date: 2025-11-17*
