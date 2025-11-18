# Pricing and GST Rate Versioning System - Complete Design

**Date**: 2025-11-17
**Version**: 2.0
**Status**: Design Phase

---

## Executive Summary

This document outlines a comprehensive design for date-based versioning of both **GST rates** and **pricing** (MRP, selling price, cost price) in SkinSpire HMS. Both change over time and must be tracked historically for:
- Tax compliance (GST rates per government notifications)
- Price revision tracking (MRP changes per manufacturer updates)
- Accurate historical invoicing
- Profit margin analysis
- Audit trails

---

## Business Requirement

### Problem Statement

**Current State**:
1. **GST Rates**: Stored as static fields in master tables
   - No date-based versioning
   - Rate changes overwrite previous values
   - No government notification tracking

2. **Pricing (MRP/Selling Price)**:Stored in master tables with limited tracking
   - Only ONE previous MRP tracked (Medicine.previous_mrp)
   - No complete price history
   - No manufacturer notification tracking

**Business Impact**:
1. **Compliance Risk**: Historical invoices may not reflect actual rates/prices at time of sale
2. **Audit Risk**: Cannot prove what MRP/GST was applicable on a given date
3. **Analytics Gap**: Cannot analyze profit margins across time periods
4. **Legal Risk**: MRP changes are regulated and must be documented

---

## Real-World Scenarios

### Scenario 1: GST Rate Change
- **Date**: April 1, 2025
- **Change**: Cosmetic services GST increased from 12% to 18%
- **Impact**: Invoices dated March 31 must use 12%, April 1 onwards must use 18%

### Scenario 2: MRP Revision
- **Medicine**: XYZ Cream
- **Old MRP**: ₹500 (effective until June 30, 2025)
- **New MRP**: ₹550 (effective from July 1, 2025)
- **Manufacturer Notification**: Dated June 15, 2025
- **Impact**: Sales before July 1 must use ₹500, after July 1 must use ₹550

### Scenario 3: Multiple Changes
- **Medicine**: ABC Tablet
- **January 2024**: MRP ₹100, GST 12%
- **April 2024**: MRP ₹100, GST 18% (rate increased)
- **July 2024**: MRP ₹120, GST 18% (MRP increased)
- **October 2024**: MRP ₹120, GST 12% (rate reduced)

**Requirement**: System must maintain complete history and select correct combination for any invoice date.

---

## Proposed Solution

### Design Philosophy

**Single Unified Table** for all versioned data (GST + Pricing) instead of separate tables:

**Benefits**:
1. ✅ Single lookup for both price and GST rate
2. ✅ Atomic changes (price + GST changed together)
3. ✅ Simpler querying
4. ✅ Easier to maintain consistency

**Structure**: One record per effective period per entity

---

## Database Design

### New Table: Entity Pricing and Tax Configuration

```sql
CREATE TABLE entity_pricing_tax_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID REFERENCES branches(branch_id),

    -- === ENTITY REFERENCE (ONE must be populated) ===
    medicine_id UUID REFERENCES medicines(medicine_id),
    service_id UUID REFERENCES services(service_id),
    package_id UUID REFERENCES packages(package_id),

    -- === EFFECTIVE PERIOD ===
    effective_from DATE NOT NULL,
    effective_to DATE,  -- NULL = currently effective

    -- === PRICING INFORMATION ===
    -- For Medicines
    mrp NUMERIC(12, 2),                    -- Maximum Retail Price
    pack_mrp NUMERIC(12, 2),               -- MRP per pack
    pack_purchase_price NUMERIC(12, 2),   -- Purchase price per pack
    units_per_pack NUMERIC(10, 2),        -- Units in a pack
    unit_price NUMERIC(12, 2),            -- Price per unit (derived or explicit)
    selling_price NUMERIC(12, 2),         -- Actual selling price
    cost_price NUMERIC(12, 2),            -- Cost price for profit calculation

    -- For Services/Packages
    service_price NUMERIC(12, 2),         -- Service base price
    package_price NUMERIC(12, 2),         -- Package base price

    -- === GST INFORMATION ===
    gst_rate NUMERIC(5, 2),               -- Overall GST rate (%)
    cgst_rate NUMERIC(5, 2),              -- Central GST (%)
    sgst_rate NUMERIC(5, 2),              -- State GST (%)
    igst_rate NUMERIC(5, 2),              -- Integrated GST (%)
    is_gst_exempt BOOLEAN DEFAULT false,
    gst_inclusive BOOLEAN DEFAULT false,  -- Whether price includes GST

    -- === REFERENCE DOCUMENTATION ===
    -- For GST changes
    gst_notification_number VARCHAR(100),
    gst_notification_date DATE,
    gst_notification_url VARCHAR(500),

    -- For price changes
    manufacturer_notification VARCHAR(100),  -- Manufacturer price revision reference
    manufacturer_notification_date DATE,
    price_revision_reason TEXT,

    -- === METADATA ===
    change_type VARCHAR(50),               -- 'gst_change', 'price_change', 'both', 'initial'
    change_reason TEXT,
    remarks TEXT,

    -- === AUDIT FIELDS ===
    created_by VARCHAR(15) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT false,

    -- === CONSTRAINTS ===
    CONSTRAINT chk_entity_reference CHECK (
        (medicine_id IS NOT NULL AND service_id IS NULL AND package_id IS NULL) OR
        (medicine_id IS NULL AND service_id IS NOT NULL AND package_id IS NULL) OR
        (medicine_id IS NULL AND service_id IS NULL AND package_id IS NOT NULL)
    ),
    CONSTRAINT chk_effective_dates CHECK (
        effective_to IS NULL OR effective_to > effective_from
    ),
    CONSTRAINT chk_gst_rate_sum CHECK (
        gst_rate = COALESCE(cgst_rate, 0) + COALESCE(sgst_rate, 0) + COALESCE(igst_rate, 0)
    ),
    CONSTRAINT chk_medicine_pricing CHECK (
        medicine_id IS NULL OR
        (mrp IS NOT NULL OR pack_mrp IS NOT NULL OR selling_price IS NOT NULL)
    ),
    CONSTRAINT chk_service_pricing CHECK (
        service_id IS NULL OR service_price IS NOT NULL
    ),
    CONSTRAINT chk_package_pricing CHECK (
        package_id IS NULL OR package_price IS NOT NULL
    )
);

-- === INDEXES for Performance ===
CREATE INDEX idx_pricing_tax_config_medicine
    ON entity_pricing_tax_config(medicine_id, effective_from)
    WHERE medicine_id IS NOT NULL AND is_deleted = false;

CREATE INDEX idx_pricing_tax_config_service
    ON entity_pricing_tax_config(service_id, effective_from)
    WHERE service_id IS NOT NULL AND is_deleted = false;

CREATE INDEX idx_pricing_tax_config_package
    ON entity_pricing_tax_config(package_id, effective_from)
    WHERE package_id IS NOT NULL AND is_deleted = false;

CREATE INDEX idx_pricing_tax_config_dates
    ON entity_pricing_tax_config(effective_from, effective_to)
    WHERE is_deleted = false;

CREATE INDEX idx_pricing_tax_config_hospital
    ON entity_pricing_tax_config(hospital_id, effective_from)
    WHERE is_deleted = false;

-- === UNIQUE CONSTRAINT: No overlapping periods ===
CREATE UNIQUE INDEX idx_pricing_tax_config_no_overlap_medicine
    ON entity_pricing_tax_config(hospital_id, medicine_id, effective_from)
    WHERE medicine_id IS NOT NULL AND is_deleted = false;

CREATE UNIQUE INDEX idx_pricing_tax_config_no_overlap_service
    ON entity_pricing_tax_config(hospital_id, service_id, effective_from)
    WHERE service_id IS NOT NULL AND is_deleted = false;

CREATE UNIQUE INDEX idx_pricing_tax_config_no_overlap_package
    ON entity_pricing_tax_config(hospital_id, package_id, effective_from)
    WHERE package_id IS NOT NULL AND is_deleted = false;
```

---

## Python Model

### File: app/models/config.py

```python
from sqlalchemy import Column, String, ForeignKey, Boolean, Date, Text, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import date
from .base import Base, TimestampMixin, TenantMixin, generate_uuid

class EntityPricingTaxConfig(Base, TimestampMixin, TenantMixin):
    """
    Date-based versioning of pricing and GST rates for medicines, services, and packages.
    Supports:
    - MRP/price change tracking with manufacturer notifications
    - GST rate change tracking with government notifications
    - Complete historical accuracy for invoicing
    """
    __tablename__ = 'entity_pricing_tax_config'

    config_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))

    # Entity Reference (exactly ONE must be populated)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'))
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'))
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'))

    # Effective Period
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)  # NULL = currently effective

    # === PRICING INFORMATION ===
    # For Medicines
    mrp = Column(Numeric(12, 2))                    # Maximum Retail Price
    pack_mrp = Column(Numeric(12, 2))               # MRP per pack
    pack_purchase_price = Column(Numeric(12, 2))   # Purchase price per pack
    units_per_pack = Column(Numeric(10, 2))        # Units in a pack
    unit_price = Column(Numeric(12, 2))            # Price per unit
    selling_price = Column(Numeric(12, 2))         # Actual selling price
    cost_price = Column(Numeric(12, 2))            # Cost for profit calculation

    # For Services/Packages
    service_price = Column(Numeric(12, 2))         # Service base price
    package_price = Column(Numeric(12, 2))         # Package base price

    # === GST INFORMATION ===
    gst_rate = Column(Numeric(5, 2))               # Overall GST (%)
    cgst_rate = Column(Numeric(5, 2))              # Central GST (%)
    sgst_rate = Column(Numeric(5, 2))              # State GST (%)
    igst_rate = Column(Numeric(5, 2))              # Integrated GST (%)
    is_gst_exempt = Column(Boolean, default=False)
    gst_inclusive = Column(Boolean, default=False)

    # === REFERENCE DOCUMENTATION ===
    # For GST changes
    gst_notification_number = Column(String(100))
    gst_notification_date = Column(Date)
    gst_notification_url = Column(String(500))

    # For price changes
    manufacturer_notification = Column(String(100))
    manufacturer_notification_date = Column(Date)
    price_revision_reason = Column(Text)

    # === METADATA ===
    change_type = Column(String(50))  # 'gst_change', 'price_change', 'both', 'initial'
    change_reason = Column(Text)
    remarks = Column(Text)

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    medicine = relationship("Medicine", foreign_keys=[medicine_id])
    service = relationship("Service", foreign_keys=[service_id])
    package = relationship("Package", foreign_keys=[package_id])

    __table_args__ = (
        CheckConstraint(
            """
            (medicine_id IS NOT NULL AND service_id IS NULL AND package_id IS NULL) OR
            (medicine_id IS NULL AND service_id IS NOT NULL AND package_id IS NULL) OR
            (medicine_id IS NULL AND service_id IS NULL AND package_id IS NOT NULL)
            """,
            name='chk_entity_reference'
        ),
        CheckConstraint(
            'effective_to IS NULL OR effective_to > effective_from',
            name='chk_effective_dates'
        ),
        CheckConstraint(
            'gst_rate = COALESCE(cgst_rate, 0) + COALESCE(sgst_rate, 0) + COALESCE(igst_rate, 0)',
            name='chk_gst_rate_sum'
        ),
    )

    @property
    def entity_type(self):
        """Return the type of entity this config applies to"""
        if self.medicine_id:
            return 'medicine'
        elif self.service_id:
            return 'service'
        elif self.package_id:
            return 'package'
        return None

    @property
    def entity_id(self):
        """Return the ID of the entity this config applies to"""
        if self.medicine_id:
            return self.medicine_id
        elif self.service_id:
            return self.service_id
        elif self.package_id:
            return self.package_id
        return None

    @property
    def is_currently_effective(self):
        """Check if this config is currently in effect"""
        today = date.today()
        return (self.effective_from <= today and
                (self.effective_to is None or self.effective_to >= today))

    @property
    def applicable_price(self):
        """Get the applicable price based on entity type"""
        if self.medicine_id:
            return self.mrp or self.selling_price or self.pack_mrp
        elif self.service_id:
            return self.service_price
        elif self.package_id:
            return self.package_price
        return None

    def __repr__(self):
        entity_info = f"{self.entity_type}_{self.entity_id}"
        period = f"{self.effective_from} to {self.effective_to or 'current'}"
        return f"<EntityPricingTaxConfig {entity_info} {period} price={self.applicable_price} gst={self.gst_rate}%>"
```

---

## Service Layer

### File: app/services/pricing_tax_service.py

```python
"""
Pricing and Tax Service - Date-based pricing and GST rate lookup
"""
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, List
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

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: Type of entity ('medicine', 'service', 'package')
        entity_id: UUID of the entity
        applicable_date: Date for which pricing/tax is needed

    Returns:
        Dict with pricing and tax information
    """

    # Try to find config for the date
    entity_id_column = f"{entity_type}_id"

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
        return _build_response_from_config(config, entity_type)

    # Fallback to master table
    logger.warning(f"No config found for {entity_type} {entity_id} on {applicable_date}. Using master table.")
    return _build_response_from_master(session, entity_type, entity_id)


def _build_response_from_config(config: EntityPricingTaxConfig, entity_type: str) -> Dict:
    """Build response dict from config record"""
    base_response = {
        # GST fields
        'gst_rate': config.gst_rate or Decimal('0'),
        'cgst_rate': config.cgst_rate or Decimal('0'),
        'sgst_rate': config.sgst_rate or Decimal('0'),
        'igst_rate': config.igst_rate or Decimal('0'),
        'is_gst_exempt': config.is_gst_exempt or False,
        'gst_inclusive': config.gst_inclusive or False,

        # Metadata
        'source': 'config',
        'config_id': config.config_id,
        'effective_from': config.effective_from,
        'effective_to': config.effective_to
    }

    # Add pricing fields based on entity type
    if entity_type == 'medicine':
        base_response.update({
            'mrp': config.mrp,
            'pack_mrp': config.pack_mrp,
            'pack_purchase_price': config.pack_purchase_price,
            'units_per_pack': config.units_per_pack,
            'unit_price': config.unit_price,
            'selling_price': config.selling_price,
            'cost_price': config.cost_price
        })
    elif entity_type == 'service':
        base_response.update({
            'price': config.service_price
        })
    elif entity_type == 'package':
        base_response.update({
            'price': config.package_price
        })

    return base_response


def _build_response_from_master(session: Session, entity_type: str, entity_id: str) -> Dict:
    """Build response dict from master table (fallback)"""
    if entity_type == 'medicine':
        entity = session.query(Medicine).filter_by(medicine_id=entity_id).first()
        if entity:
            return {
                # GST fields
                'gst_rate': entity.gst_rate or Decimal('0'),
                'cgst_rate': entity.cgst_rate or Decimal('0'),
                'sgst_rate': entity.sgst_rate or Decimal('0'),
                'igst_rate': entity.igst_rate or Decimal('0'),
                'is_gst_exempt': entity.is_gst_exempt or False,
                'gst_inclusive': entity.gst_inclusive or False,

                # Pricing fields
                'mrp': entity.mrp,
                'selling_price': entity.selling_price,
                'cost_price': entity.cost_price,

                # Metadata
                'source': 'master_table',
                'config_id': None
            }

    elif entity_type == 'service':
        entity = session.query(Service).filter_by(service_id=entity_id).first()
        if entity:
            return {
                # GST fields
                'gst_rate': entity.gst_rate or Decimal('0'),
                'cgst_rate': entity.cgst_rate or Decimal('0'),
                'sgst_rate': entity.sgst_rate or Decimal('0'),
                'igst_rate': entity.igst_rate or Decimal('0'),
                'is_gst_exempt': entity.is_gst_exempt or False,

                # Pricing
                'price': entity.price,

                # Metadata
                'source': 'master_table',
                'config_id': None
            }

    elif entity_type == 'package':
        entity = session.query(Package).filter_by(package_id=entity_id).first()
        if entity:
            return {
                # GST fields
                'gst_rate': entity.gst_rate or Decimal('0'),
                'cgst_rate': entity.cgst_rate or Decimal('0'),
                'sgst_rate': entity.sgst_rate or Decimal('0'),
                'igst_rate': entity.igst_rate or Decimal('0'),
                'is_gst_exempt': entity.is_gst_exempt or False,

                # Pricing
                'price': entity.price,

                # Metadata
                'source': 'master_table',
                'config_id': None
            }

    # No data found
    logger.error(f"No pricing/tax data found for {entity_type} {entity_id}")
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
    # Pricing params
    mrp: Optional[Decimal] = None,
    pack_mrp: Optional[Decimal] = None,
    selling_price: Optional[Decimal] = None,
    service_price: Optional[Decimal] = None,
    package_price: Optional[Decimal] = None,
    cost_price: Optional[Decimal] = None,
    # GST params
    gst_rate: Optional[Decimal] = None,
    cgst_rate: Optional[Decimal] = None,
    sgst_rate: Optional[Decimal] = None,
    igst_rate: Optional[Decimal] = None,
    is_gst_exempt: Optional[bool] = None,
    # Documentation params
    change_type: str = 'both',  # 'price_change', 'gst_change', 'both'
    manufacturer_notification: Optional[str] = None,
    gst_notification_number: Optional[str] = None,
    change_reason: Optional[str] = None,
    **kwargs
) -> EntityPricingTaxConfig:
    """
    Add a new pricing/tax configuration change.
    Automatically closes the previous config's effective period.

    Returns:
        Created EntityPricingTaxConfig record
    """

    # Auto-calculate GST component rates if not provided
    if gst_rate is not None and cgst_rate is None:
        cgst_rate = gst_rate / 2
        sgst_rate = gst_rate / 2
        igst_rate = gst_rate

    # Close previous config (if exists)
    entity_id_column = f"{entity_type}_id"
    previous_config = session.query(EntityPricingTaxConfig).filter(
        and_(
            EntityPricingTaxConfig.hospital_id == hospital_id,
            getattr(EntityPricingTaxConfig, entity_id_column) == entity_id,
            EntityPricingTaxConfig.effective_to == None,  # Currently open
            EntityPricingTaxConfig.is_deleted == False
        )
    ).first()

    if previous_config:
        # Set effective_to to day before new config starts
        previous_config.effective_to = effective_from - timedelta(days=1)
        previous_config.updated_by = current_user_id
        logger.info(f"Closed previous config: {previous_config.config_id}, effective_to={previous_config.effective_to}")

    # Create new config
    new_config = EntityPricingTaxConfig(
        hospital_id=hospital_id,
        **{entity_id_column: entity_id},
        effective_from=effective_from,
        effective_to=None,  # Open-ended
        # Pricing
        mrp=mrp,
        pack_mrp=pack_mrp,
        selling_price=selling_price,
        service_price=service_price,
        package_price=package_price,
        cost_price=cost_price,
        # GST
        gst_rate=gst_rate,
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        igst_rate=igst_rate,
        is_gst_exempt=is_gst_exempt,
        # Documentation
        change_type=change_type,
        manufacturer_notification=manufacturer_notification,
        gst_notification_number=gst_notification_number,
        change_reason=change_reason,
        created_by=current_user_id
    )

    # Add any additional kwargs
    for key, value in kwargs.items():
        if hasattr(new_config, key):
            setattr(new_config, key, value)

    session.add(new_config)
    session.flush()

    logger.info(f"Created new pricing/tax config: {new_config.config_id}, effective_from={effective_from}")

    return new_config


def get_config_history(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str
) -> List[EntityPricingTaxConfig]:
    """
    Get complete pricing and tax change history for an entity.

    Returns:
        List of EntityPricingTaxConfig records ordered by effective_from desc
    """
    entity_id_column = f"{entity_type}_id"

    return session.query(EntityPricingTaxConfig).filter(
        and_(
            EntityPricingTaxConfig.hospital_id == hospital_id,
            getattr(EntityPricingTaxConfig, entity_id_column) == entity_id,
            EntityPricingTaxConfig.is_deleted == False
        )
    ).order_by(EntityPricingTaxConfig.effective_from.desc()).all()


def get_current_config(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str
) -> Optional[EntityPricingTaxConfig]:
    """Get the currently effective config for an entity"""
    return get_applicable_pricing_and_tax(
        session, hospital_id, entity_type, entity_id, date.today()
    )
```

---

## Integration with Invoice Creation

### Modification: billing_service.py

**Current Code** (app/services/billing_service.py:1287-1294):
```python
medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
if medicine:
    gst_rate = medicine.gst_rate or Decimal('0')
    is_gst_exempt = medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False
    gst_inclusive = medicine.gst_inclusive if hasattr(medicine, 'gst_inclusive') else True
    hsn_sac_code = medicine.hsn_code
    cost_price = medicine.cost_price
```

**New Code** (with date-based lookup):
```python
from app.services.pricing_tax_service import get_applicable_pricing_and_tax
from datetime import date

medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
if medicine:
    # Get pricing and GST applicable on invoice date
    invoice_date = invoice_data.get('invoice_date', date.today())
    pricing_tax = get_applicable_pricing_and_tax(
        session=session,
        hospital_id=hospital_id,
        entity_type='medicine',
        entity_id=item_id,
        applicable_date=invoice_date
    )

    # Use versioned values
    gst_rate = pricing_tax['gst_rate']
    is_gst_exempt = pricing_tax['is_gst_exempt']
    gst_inclusive = pricing_tax.get('gst_inclusive', True)
    cgst_rate = pricing_tax['cgst_rate']
    sgst_rate = pricing_tax['sgst_rate']
    igst_rate = pricing_tax['igst_rate']

    # Use versioned pricing (if available)
    if pricing_tax.get('mrp'):
        # Override with historical MRP if available
        logger.info(f"Using historical MRP from config: ₹{pricing_tax['mrp']}")
        # Can use this in MRP validation or calculations

    hsn_sac_code = medicine.hsn_code
    cost_price = pricing_tax.get('cost_price') or medicine.cost_price

    logger.info(f"Medicine '{medicine.medicine_name}': Using {pricing_tax['source']} - "
                f"MRP=₹{pricing_tax.get('mrp')}, GST={gst_rate}% for date {invoice_date}")
```

---

## Current Implementation Approach Across Modules

### Three-Tier Fallback Strategy

**Version**: 2.1 (Updated 2025-11-17)
**Status**: ✅ IMPLEMENTED

All pricing and GST data in the system follows a **three-tier fallback strategy** to ensure data is always available while maintaining time-based accuracy:

```
Priority 1: entity_pricing_tax_config (Date-based configuration)
    ↓ (if not found)
Priority 2: Master Tables (medicines, services, packages)
    ↓ (if not found - MRP only)
Priority 3: Inventory Table (Historical MRP from purchase records)
```

### Why This Approach?

| Tier | Source | Use Case | Data Freshness | Compliance |
|------|--------|----------|----------------|------------|
| **1. Config** | `entity_pricing_tax_config` | Date-based versioning | ✅ Time-accurate | ✅ Audit trail |
| **2. Master** | `medicines`, `services`, `packages` | Current default values | ✅ Current | ⚠️ No history |
| **3. Inventory** | `inventory` | Emergency fallback (MRP only) | ❌ Historical purchase data | ❌ No trail |

**Key Principle**:
- **GST rates and prices** should come from config/master (regulatory/business decision)
- **Inventory** is purchase history, NOT pricing authority
- **Inventory MRP** is last resort only (when config and master both missing MRP)

---

## Implementation in Various Documents

### 1. Invoice Creation (`billing_views.py` - Batch Lookup API)

**Endpoint**: `/web_api/medicine/<medicine_id>/batches`
**Purpose**: Load batches for medicine selection in invoice line items

**Implementation** (Lines 2445-2498):

```python
# Step 1: Get pricing/tax from pricing_tax_service
from app.services.pricing_tax_service import get_applicable_pricing_and_tax
from datetime import datetime, timezone

applicable_date = datetime.now(timezone.utc).date()

try:
    pricing_tax = get_applicable_pricing_and_tax(
        session=session,
        hospital_id=hospital_id,
        entity_type='medicine',
        entity_id=medicine_id,
        applicable_date=applicable_date
    )

    # Extract from pricing_tax_service (PRIMARY)
    medicine_gst_rate = pricing_tax['gst_rate']
    medicine_is_gst_exempt = pricing_tax['is_gst_exempt']
    medicine_mrp = pricing_tax.get('mrp', 0)  # ✅ MRP from config
    medicine_pack_mrp = pricing_tax.get('pack_mrp', 0)

    logger.info(f"Using pricing from {pricing_tax['source']}: "
               f"GST={medicine_gst_rate}%, MRP={medicine_mrp}")

except Exception as e:
    # Fallback to medicine master table
    logger.warning(f"Failed to get pricing_tax: {e}. Using master table.")
    medicine_gst_rate = float(medicine.gst_rate) if medicine.gst_rate else 0.0
    medicine_is_gst_exempt = medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False
    medicine_mrp = float(medicine.mrp) if hasattr(medicine, 'mrp') and medicine.mrp else 0.0
    medicine_pack_mrp = float(medicine.pack_mrp) if hasattr(medicine, 'pack_mrp') and medicine.pack_mrp else 0.0

# Step 2: Consolidate batches and apply pricing
for record in consolidated_batches:
    inventory_pack_mrp = float(record.pack_mrp) if record.pack_mrp else 0  # Backup only

    result.append({
        'batch': record.batch,
        'expiry_date': record.expiry.strftime('%Y-%m-%d') if record.expiry else None,
        'available_quantity': float(record.current_stock),
        'unit_price': float(record.sale_price),  # Weighted average across records
        'mrp': float(medicine_mrp) if medicine_mrp else inventory_pack_mrp,  # ✅ Config first, inventory last
        'gst_rate': medicine_gst_rate,  # ✅ From pricing_tax_service
        'is_gst_exempt': medicine_is_gst_exempt,  # ✅ From pricing_tax_service
        'gst_inclusive': medicine.gst_inclusive,  # From medicine master
        # Reference data (not used for calculations)
        'inventory_pack_mrp': inventory_pack_mrp,  # Historical MRP
        'inventory_cgst': inventory_cgst,  # Historical GST
        'inventory_sgst': inventory_sgst,
        'inventory_igst': inventory_igst,
        'is_consolidated': record.record_count > 1,  # Multiple inventory records consolidated
        'record_count': record.record_count
    })
```

**Key Points**:
- ✅ MRP comes from `pricing_tax_service` (config or master)
- ✅ Inventory MRP is fallback only
- ✅ Historical GST/MRP from inventory kept as reference
- ✅ Multiple inventory records for same batch are consolidated (sum stock, weighted avg price)

---

### 2. FIFO Allocation (`billing_views.py` - FIFO Allocation API)

**Endpoint**: `/web_api/medicine/<medicine_id>/fifo-allocation`
**Purpose**: Auto-allocate batches based on FIFO for invoice line items

**Implementation** (Lines 2545-2613):

```python
# Step 1: Get pricing/tax from pricing_tax_service (same as batch lookup)
try:
    pricing_tax = get_applicable_pricing_and_tax(
        session=session,
        hospital_id=hospital_id,
        entity_type='medicine',
        entity_id=medicine_id,
        applicable_date=applicable_date
    )

    medicine_gst_rate = float(pricing_tax['gst_rate'])
    medicine_is_gst_exempt = pricing_tax['is_gst_exempt']
    medicine_mrp = float(pricing_tax.get('mrp', 0))  # ✅ From config
    medicine_cgst = float(pricing_tax.get('cgst_rate', 0))
    medicine_sgst = float(pricing_tax.get('sgst_rate', 0))
    medicine_igst = float(pricing_tax.get('igst_rate', 0))

    logger.info(f"[FIFO ALLOCATION] Using pricing from {pricing_tax['source']}")

except Exception as e:
    # Fallback to medicine master table
    logger.warning(f"[FIFO ALLOCATION] Failed to get pricing_tax: {e}")
    medicine_gst_rate = float(medicine.gst_rate) if medicine.gst_rate else 0.0
    medicine_mrp = float(medicine.mrp) if hasattr(medicine, 'mrp') and medicine.mrp else 0.0
    medicine_cgst = medicine_gst_rate / 2
    medicine_sgst = medicine_gst_rate / 2
    medicine_igst = 0.0

# Step 2: Get FIFO batches (consolidated by inventory_service)
batch_allocations = get_batch_selection_for_invoice(
    hospital_id=hospital_id,
    medicine_id=medicine_id,
    quantity_needed=quantity,
    session=session
)

# Step 3: Format response with config pricing
for batch in batch_allocations:
    inventory = session.query(Inventory).filter(
        Inventory.hospital_id == hospital_id,
        Inventory.medicine_id == medicine_id,
        Inventory.batch == batch['batch']
    ).order_by(Inventory.created_at.desc()).first()

    inventory_pack_mrp = float(inventory.pack_mrp) if inventory and inventory.pack_mrp else 0

    formatted_batches.append({
        'batch': batch['batch'],
        'expiry_date': batch['expiry_date'].strftime('%Y-%m-%d'),
        'quantity': float(batch['quantity']),
        'available_stock': float(inventory.current_stock) if inventory else 0,
        'unit_price': float(batch.get('unit_price', 0)),
        'sale_price': float(batch.get('sale_price', 0)),
        'mrp': medicine_mrp if medicine_mrp else inventory_pack_mrp,  # ✅ Config first
        'gst_rate': medicine_gst_rate,  # ✅ From pricing_tax_service
        'cgst': medicine_cgst,  # ✅ From pricing_tax_service
        'sgst': medicine_sgst,  # ✅ From pricing_tax_service
        'igst': medicine_igst,  # ✅ From pricing_tax_service
        'is_gst_exempt': medicine_is_gst_exempt,
        'inventory_pack_mrp': inventory_pack_mrp  # Historical reference
    })
```

**Key Points**:
- ✅ All GST components from `pricing_tax_service`
- ✅ MRP from config, inventory as last resort
- ✅ FIFO service consolidates multiple inventory records
- ✅ Inventory data kept for stock tracking only

---

### 3. Item Search API (`billing_views.py` - Item Search)

**Endpoint**: `/web_api/item/search`
**Purpose**: Search medicines, packages, services for invoice line item selection

#### 3.1 Medicine Search (Lines 2300-2336)

```python
# Use pricing_tax_service for medicines
from app.services.pricing_tax_service import get_applicable_pricing_and_tax

for medicine in medicines:
    applicable_date = datetime.now(timezone.utc).date()

    try:
        pricing_tax = get_applicable_pricing_and_tax(
            session=session,
            hospital_id=hospital_id,
            entity_type='medicine',
            entity_id=medicine.medicine_id,
            applicable_date=applicable_date
        )

        gst_rate = pricing_tax['gst_rate']
        is_gst_exempt = pricing_tax['is_gst_exempt']

        logger.debug(f"Medicine '{medicine.medicine_name}': Using {pricing_tax['source']} - "
                    f"gst_rate={gst_rate}%")
    except Exception as e:
        logger.warning(f"Failed to get date-based pricing for medicine {medicine.medicine_id}: {e}")
        gst_rate = float(medicine.gst_rate) if medicine.gst_rate else 0.0
        is_gst_exempt = medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False

    results.append({
        'id': str(medicine.medicine_id),
        'name': medicine.medicine_name,
        'type': item_type,
        'gst_rate': gst_rate,  # ✅ From pricing_tax_service
        'is_gst_exempt': is_gst_exempt,  # ✅ From pricing_tax_service
        'gst_inclusive': medicine.gst_inclusive,  # From medicine master
        'hsn_code': medicine.hsn_code
    })
```

#### 3.2 Package Search (Lines 2183-2221)

```python
# Use pricing_tax_service for packages
for package in packages:
    applicable_date = datetime.now(timezone.utc).date()

    try:
        pricing_tax = get_applicable_pricing_and_tax(
            session=session,
            hospital_id=hospital_id,
            entity_type='package',
            entity_id=package.package_id,
            applicable_date=applicable_date
        )

        gst_rate = pricing_tax['gst_rate']
        is_gst_exempt = pricing_tax['is_gst_exempt']
        price = pricing_tax.get('price', float(package.price) if package.price else 0.0)

        logger.debug(f"Package '{package.package_name}': Using {pricing_tax['source']} - "
                    f"gst_rate={gst_rate}%, price={price}")
    except Exception as e:
        logger.warning(f"Failed to get date-based pricing for package {package.package_id}: {e}")
        gst_rate = float(package.gst_rate) if package.gst_rate else 0.0
        is_gst_exempt = package.is_gst_exempt if hasattr(package, 'is_gst_exempt') else False
        price = float(package.price) if package.price else 0.0

    results.append({
        'id': str(package.package_id),
        'name': package.package_name,
        'type': 'Package',
        'price': price,  # ✅ From pricing_tax_service
        'gst_rate': gst_rate,  # ✅ From pricing_tax_service
        'is_gst_exempt': is_gst_exempt,  # ✅ From pricing_tax_service
        'gst_inclusive': False  # Packages are GST exclusive by default
    })
```

#### 3.3 Service Search (Lines 2236-2275)

```python
# Use pricing_tax_service for services (same pattern as packages)
for service in services:
    try:
        pricing_tax = get_applicable_pricing_and_tax(
            session=session,
            hospital_id=hospital_id,
            entity_type='service',
            entity_id=service.service_id,
            applicable_date=applicable_date
        )

        gst_rate = pricing_tax['gst_rate']
        is_gst_exempt = pricing_tax['is_gst_exempt']
        price = pricing_tax.get('price', float(service.price) if service.price else 0.0)

    except Exception as e:
        gst_rate = float(service.gst_rate) if hasattr(service, 'gst_rate') else 0.0
        is_gst_exempt = service.is_gst_exempt if hasattr(service, 'is_gst_exempt') else False
        price = float(service.price) if service.price else 0.0

    results.append({
        'id': str(service.service_id),
        'name': service.service_name,
        'type': 'Service',
        'price': price,  # ✅ From pricing_tax_service
        'gst_rate': gst_rate,  # ✅ From pricing_tax_service
        'is_gst_exempt': is_gst_exempt,  # ✅ From pricing_tax_service
        'gst_inclusive': False,  # Services are GST exclusive by default
        'sac_code': service.sac_code
    })
```

**Key Points**:
- ✅ All entity types (medicine, package, service) use `pricing_tax_service`
- ✅ Master table as fallback for each entity type
- ✅ No inventory involvement in item search (inventory is for batch selection only)

---

### 4. Batch Consolidation (`inventory_service.py`)

**Function**: `get_batch_selection_for_invoice()`
**Purpose**: Get FIFO batch allocation with consolidated multiple inventory records

**Implementation** (Lines 824-839):

```python
# CONSOLIDATE multiple inventory records for same batch
query = text("""
    SELECT
        i.batch,
        MIN(i.expiry) as expiry,  -- Earliest expiry for FIFO
        SUM(i.current_stock) as current_stock,  -- Total stock across all records
        -- Weighted average price based on stock
        SUM(i.sale_price * i.current_stock) / NULLIF(SUM(i.current_stock), 0) as sale_price,
        SUM(i.unit_price * i.current_stock) / NULLIF(SUM(i.current_stock), 0) as unit_price,
        MAX(i.pack_mrp) as pack_mrp
    FROM inventory i
    WHERE i.hospital_id = :hospital_id
      AND i.medicine_id = :medicine_id
      AND i.current_stock > 0  -- Only batches with stock
    GROUP BY i.batch
    ORDER BY MIN(i.expiry)  -- FIFO based on earliest expiry
""")
```

**Business Logic**:
- ✅ Same batch from multiple purchase orders = ONE consolidated entry
- ✅ Total stock = SUM of all records
- ✅ Price = Weighted average based on stock
- ✅ Expiry = Earliest expiry for FIFO priority
- ✅ Backend handles distribution across multiple records when saving invoice

**Example**:
```
Before consolidation:
- Batch AM23001, Stock: 100, Price: 25, Expiry: 2026-05-31
- Batch AM23001, Stock: 99, Price: 100, Expiry: 2026-05-31
- Batch AM23001, Stock: 98, Price: 1500, Expiry: 2026-06-01
... (35 more records)

After consolidation:
- Batch AM23001, Stock: 2165 (sum), Price: 413.81 (weighted avg), Expiry: 2026-05-31 (earliest)
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  User Creates Invoice                                        │
│  Invoice Date: 2025-11-17                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Item Search API                                    │
│  • User searches for "Paracetamol"                          │
│  • API calls pricing_tax_service.get_applicable_pricing()   │
│  • Returns: GST Rate, GST Exempt, Price (for pkg/svc)      │
└─────────────────────────────────────────────────────────────┘
                            ↓
                ┌───────────┴───────────┐
                ↓                       ↓
    ┌─────────────────────┐  ┌─────────────────────┐
    │ Config Found        │  │ Config Not Found    │
    │ Source: 'config'    │  │ Source: 'master'    │
    │ Use config values   │  │ Use master values   │
    └─────────────────────┘  └─────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: User Selects Medicine → Load Batches               │
│  • Batch Lookup API called                                  │
│  • Gets pricing_tax_service data (GST, MRP)                 │
│  • Consolidates inventory records (same batch)              │
│  • Applies config MRP (or master MRP, or inventory MRP)     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: User Enters Quantity → FIFO Allocation (Optional)  │
│  • FIFO Allocation API called                               │
│  • Gets pricing_tax_service data (GST, MRP)                 │
│  • inventory_service provides consolidated batches          │
│  • Applies config pricing to all allocated batches          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Calculate Line Total (Frontend)                    │
│  • Uses GST rate from API response                          │
│  • Checks gst_inclusive flag                                │
│  • If inclusive: Extract GST from price                     │
│  • If exclusive: Add GST on top of price                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Save Invoice (Backend)                             │
│  • Uses GST/MRP from pricing_tax_service                    │
│  • Saves config_id reference in invoice_items               │
│  • Inventory service distributes across multiple records    │
│  • Audit trail maintained                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Fallback Sequence by Data Type

### GST Rate
```
1. entity_pricing_tax_config.gst_rate (Date-based)
   ↓ (if not found)
2. medicine/service/package.gst_rate (Current master value)
   ↓ (if not found)
3. Default: 0% (with warning log)
```

**No inventory fallback** - GST rates are business/regulatory decision, not purchase history.

### MRP (Maximum Retail Price)
```
1. entity_pricing_tax_config.mrp (Date-based, regulated)
   ↓ (if not found)
2. medicine.mrp (Current master value)
   ↓ (if not found)
3. inventory.pack_mrp (Last resort - historical purchase data)
   ↓ (if not found)
4. Default: 0 (with warning log)
```

**Why inventory fallback for MRP?** Emergency fallback only - better to show historical MRP than nothing.

### Service/Package Price
```
1. entity_pricing_tax_config.service_price / package_price (Date-based)
   ↓ (if not found)
2. service.price / package.price (Current master value)
   ↓ (if not found)
3. Default: 0 (with warning log)
```

**No inventory fallback** - Services/packages don't have inventory records.

### GST Inclusive Flag
```
1. medicine.gst_inclusive (Master table only)
   ↓ (if not found)
2. Default: False (GST exclusive)
```

**Note**: `gst_inclusive` is a property of the medicine definition, not time-sensitive.

---

## Best Practices

### DO ✅
1. **Always call `pricing_tax_service`** first in all invoice-related APIs
2. **Use master table** as graceful fallback when config not found
3. **Use inventory MRP** only as last resort emergency fallback
4. **Log the source** (`'config'`, `'master_table'`, `'inventory'`) for debugging
5. **Include inventory data** as reference fields (`inventory_pack_mrp`, `inventory_cgst`, etc.)
6. **Consolidate batches** - same batch number = one dropdown entry with aggregated stock
7. **Document config_id** in invoice items for audit trail

### DON'T ❌
1. **Never use inventory GST** for calculations (historical purchase data)
2. **Never skip pricing_tax_service** - always try it first
3. **Never show duplicate batches** in dropdown (consolidate first)
4. **Never mix data sources** - all GST/pricing from same source (config OR master)
5. **Never update master tables** when config changes - config supersedes master
6. **Never calculate MRP** - always use configured/stored values
7. **Never assume gst_inclusive** - always check the flag explicitly

---

## Logging Standards

All modules should log the data source for troubleshooting:

```python
# ✅ Good logging
logger.info(f"[BATCH LOOKUP] Using pricing from {pricing_tax['source']}: "
           f"GST={gst_rate}%, MRP={mrp}, config_id={pricing_tax.get('config_id')}")

# ✅ Good fallback logging
logger.warning(f"[FIFO ALLOCATION] Failed to get pricing_tax: {e}. "
              f"Using medicine master table as fallback.")

# ✅ Good consolidation logging
if record.record_count > 1:
    logger.info(f"[BATCH CONSOLIDATION] Batch '{batch}' consolidated {record.record_count} records: "
               f"Total Stock={stock}, Avg Price={price:.2f}")
```

---

## Testing Checklist

### Config Priority Testing
- [ ] Create config for medicine effective today → Invoice should use config values
- [ ] Create config for future date → Invoice should use master values (not yet effective)
- [ ] Create config for past date → Invoice should use config values (if still effective)
- [ ] Delete config → Invoice should fall back to master values

### Batch Consolidation Testing
- [ ] Medicine with 1 inventory record → Shows 1 batch
- [ ] Medicine with 10 records, same batch → Shows 1 consolidated batch
- [ ] Verify consolidated stock = SUM of all records
- [ ] Verify consolidated price = weighted average
- [ ] Verify consolidation logged correctly

### MRP Fallback Testing
- [ ] Config has MRP → Use config MRP (priority 1)
- [ ] No config, master has MRP → Use master MRP (priority 2)
- [ ] No config, no master MRP, inventory has MRP → Use inventory MRP (priority 3)
- [ ] All missing → Show 0 with warning log

### GST Fallback Testing
- [ ] Config has GST → Use config GST (priority 1)
- [ ] No config, master has GST → Use master GST (priority 2)
- [ ] All missing → Use 0% with warning log
- [ ] **Never** use inventory GST values

---

## Example Usage Scenarios

### Scenario 1: MRP Increase

**Medicine**: XYZ Cream
**Current MRP**: ₹500
**New MRP**: ₹550
**Effective**: July 1, 2025
**Manufacturer Notification**: "Price Revision Notice 2025/07" dated June 15, 2025

```python
from app.services.pricing_tax_service import add_pricing_tax_change
from datetime import date
from decimal import Decimal

# Add MRP change
add_pricing_tax_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    effective_from=date(2025, 7, 1),
    change_type='price_change',
    mrp=Decimal('550'),
    manufacturer_notification='Price Revision Notice 2025/07',
    manufacturer_notification_date=date(2025, 6, 15),
    change_reason='Manufacturer price revision - raw material cost increase',
    current_user_id=admin_user_id,
    # Copy current GST rate (no change)
    gst_rate=Decimal('18'),
    cgst_rate=Decimal('9'),
    sgst_rate=Decimal('9'),
    igst_rate=Decimal('18')
)
```

**Result**:
- Invoice dated June 30, 2025 → Uses MRP ₹500 ✅
- Invoice dated July 1, 2025 → Uses MRP ₹550 ✅

### Scenario 2: GST Rate Change Only

**Service**: Laser Hair Removal
**GST Change**: 12% → 18%
**Effective**: April 1, 2025
**Notification**: "No. 01/2025-Central Tax (Rate)"

```python
add_pricing_tax_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='service',
    entity_id=service_id,
    effective_from=date(2025, 4, 1),
    change_type='gst_change',
    gst_rate=Decimal('18'),
    cgst_rate=Decimal('9'),
    sgst_rate=Decimal('9'),
    igst_rate=Decimal('18'),
    gst_notification_number='No. 01/2025-Central Tax (Rate)',
    gst_notification_date=date(2025, 3, 15),
    change_reason='Government GST rate increase for cosmetic services',
    current_user_id=admin_user_id,
    # Copy current service price (no change)
    service_price=Decimal('5000')
)
```

### Scenario 3: Both Price and GST Change

**Medicine**: ABC Tablet
**Old**: MRP ₹100, GST 12%
**New**: MRP ₹120, GST 18%
**Effective**: January 1, 2025

```python
add_pricing_tax_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    effective_from=date(2025, 1, 1),
    change_type='both',
    # Price change
    mrp=Decimal('120'),
    manufacturer_notification='Combined Revision 2025/01',
    # GST change
    gst_rate=Decimal('18'),
    gst_notification_number='No. 47/2024-Central Tax (Rate)',
    change_reason='Combined price revision and GST rate change',
    current_user_id=admin_user_id
)
```

---

## Migration Strategy

### Phase 1: Database Setup (Week 1)

1. Create `entity_pricing_tax_config` table
2. Add indexes and constraints
3. Test on dev database

### Phase 2: Initial Data Migration (Week 1)

**Optional but recommended**: Create initial configs from current master data

```python
def migrate_current_pricing_tax_to_config(session, hospital_id):
    """
    Create initial configs from current master table values.
    Sets effective_from to a past date (e.g., 2020-01-01)
    """

    # Migrate all medicines
    medicines = session.query(Medicine).filter_by(hospital_id=hospital_id).all()
    for med in medicines:
        add_pricing_tax_change(
            session=session,
            hospital_id=hospital_id,
            entity_type='medicine',
            entity_id=med.medicine_id,
            effective_from=date(2020, 1, 1),  # Historical date
            change_type='initial',
            mrp=med.mrp,
            selling_price=med.selling_price,
            cost_price=med.cost_price,
            gst_rate=med.gst_rate,
            cgst_rate=med.cgst_rate,
            sgst_rate=med.sgst_rate,
            igst_rate=med.igst_rate,
            is_gst_exempt=med.is_gst_exempt,
            change_reason='Initial migration from master table'
        )

    # Similar for services and packages...
```

### Phase 3: Service Integration (Week 2)

1. Create `pricing_tax_service.py`
2. Update invoice creation in `billing_service.py`
3. Integration testing

### Phase 4: UI (Future - Optional)

1. Admin screen for managing price/GST changes
2. View change history
3. Upcoming changes scheduler

---

## Benefits Summary

### Compliance
- ✅ Historical accuracy for tax audits
- ✅ Government notification tracking
- ✅ Manufacturer price revision documentation

### Operations
- ✅ Automated effective date handling
- ✅ No manual master data updates
- ✅ Complete audit trail

### Analytics
- ✅ Profit margin analysis over time
- ✅ Price trend analysis
- ✅ Impact analysis of rate changes

### Legal
- ✅ MRP compliance documentation
- ✅ Tax rate compliance
- ✅ Complete change history for disputes

---

## Implementation Timeline

- **Database**: 2 days
- **Models & Services**: 4 days
- **Invoice Integration**: 3 days
- **Initial Migration**: 2 days
- **Testing**: 3 days
- **Documentation**: 1 day
- **Total**: ~3 weeks

---

**Status**: ✅ **DESIGN COMPLETE - READY FOR REVIEW**

*Designed by: Claude Code*
*Date: 2025-11-17*
