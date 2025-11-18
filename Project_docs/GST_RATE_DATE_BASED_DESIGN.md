# Date-Based GST Rate Management System - Design Document

**Date**: 2025-11-17
**Version**: 1.0
**Status**: Design Phase

---

## Executive Summary

This document outlines the design for implementing date-based GST rate management in the SkinSpire HMS. GST rates change over time based on government notifications with specific effective dates. The system must apply the correct GST rate based on the invoice date, not the current rate in the master data.

---

## Business Requirement

### Problem Statement

**Current State**:
- GST rates are stored as static fields in Medicine, Service, and Package master tables
- When GST rate changes (e.g., from 12% to 18% from April 1, 2025), master data must be manually updated
- Historical invoices might not reflect the correct rate applicable at their creation date
- No audit trail of GST rate changes

**Business Impact**:
- **Supplier Invoices**: ✅ No impact - GST taken as per supplier's invoice (user input)
- **Patient Invoices**: ❌ CRITICAL - Must use GST rate applicable on invoice date for compliance

**Regulatory Requirement**:
- GST rates are governed by government notifications with specific effective dates
- Invoices must reflect the GST rate applicable on the date of supply/invoice
- Tax authorities can audit historical invoices - rates must be historically accurate

---

## Current Implementation

### Master Tables with GST Fields

#### Medicine Table
```python
class Medicine(Base):
    # Current fields (app/models/master.py:532-537)
    hsn_code = Column(String(10))
    gst_rate = Column(Numeric(5, 2))       # Static rate
    cgst_rate = Column(Numeric(5, 2))      # Static rate
    sgst_rate = Column(Numeric(5, 2))      # Static rate
    igst_rate = Column(Numeric(5, 2))      # Static rate
    is_gst_exempt = Column(Boolean, default=False)
```

#### Service Table
```python
class Service(Base):
    # Current fields (app/models/master.py:356-360)
    sac_code = Column(String(10))
    gst_rate = Column(Numeric(5, 2))       # Static rate
    cgst_rate = Column(Numeric(5, 2))      # Static rate
    sgst_rate = Column(Numeric(5, 2))      # Static rate
    igst_rate = Column(Numeric(5, 2))      # Static rate
    is_gst_exempt = Column(Boolean, default=False)
```

#### Package Table
```python
class Package(Base):
    # Current fields (app/models/master.py:326-330)
    gst_rate = Column(Numeric(5, 2))       # Static rate
    cgst_rate = Column(Numeric(5, 2))      # Static rate
    sgst_rate = Column(Numeric(5, 2))      # Static rate
    igst_rate = Column(Numeric(5, 2))      # Static rate
    is_gst_exempt = Column(Boolean, default=False)
```

### Invoice Creation Flow

```python
# Current implementation (app/services/billing_service.py:1289)
medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
if medicine:
    gst_rate = medicine.gst_rate or Decimal('0')
    # Use this rate for invoice line item calculation
```

**Problem**: Always uses current rate from master, not rate applicable on invoice date.

---

## Proposed Solution

### Design Principles

1. **Backward Compatibility**: Existing master table GST fields remain unchanged (for current/default rates)
2. **Historical Accuracy**: Invoice line items store actual rates used (already done)
3. **Date-Based Selection**: System selects applicable rate based on invoice date
4. **Audit Trail**: All rate changes are tracked with effective dates
5. **Ease of Use**: Simple UI to configure rate changes
6. **Government Notification Tracking**: Link rate changes to notification references

---

## Database Design

### New Table: GST Rate Configuration

```sql
CREATE TABLE gst_rate_config (
    rate_config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Entity Reference (ONE of these will be populated)
    medicine_id UUID REFERENCES medicines(medicine_id),
    service_id UUID REFERENCES services(service_id),
    package_id UUID REFERENCES packages(package_id),

    -- Alternatively: HSN/SAC based rates (for category-level configuration)
    hsn_sac_code VARCHAR(10),  -- If populated, applies to all items with this code

    -- GST Rate Details
    gst_rate NUMERIC(5, 2) NOT NULL,
    cgst_rate NUMERIC(5, 2),
    sgst_rate NUMERIC(5, 2),
    igst_rate NUMERIC(5, 2),
    is_gst_exempt BOOLEAN DEFAULT false,

    -- Effective Period
    effective_from DATE NOT NULL,           -- Rate applicable from this date
    effective_to DATE,                      -- NULL = currently effective

    -- Government Notification Details
    notification_number VARCHAR(50),        -- e.g., "No. 01/2024-Central Tax (Rate)"
    notification_date DATE,                 -- Date of notification
    notification_description TEXT,          -- Brief description
    notification_url VARCHAR(500),          -- Link to notification PDF

    -- Metadata
    reason VARCHAR(500),                    -- Reason for rate change
    created_by VARCHAR(15) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT chk_entity_reference CHECK (
        (medicine_id IS NOT NULL AND service_id IS NULL AND package_id IS NULL AND hsn_sac_code IS NULL) OR
        (medicine_id IS NULL AND service_id IS NOT NULL AND package_id IS NULL AND hsn_sac_code IS NULL) OR
        (medicine_id IS NULL AND service_id IS NULL AND package_id IS NOT NULL AND hsn_sac_code IS NULL) OR
        (medicine_id IS NULL AND service_id IS NULL AND package_id IS NULL AND hsn_sac_code IS NOT NULL)
    ),
    CONSTRAINT chk_effective_dates CHECK (
        effective_to IS NULL OR effective_to > effective_from
    ),
    CONSTRAINT chk_gst_rate_sum CHECK (
        gst_rate = COALESCE(cgst_rate, 0) + COALESCE(sgst_rate, 0) + COALESCE(igst_rate, 0)
    )
);

-- Indexes for performance
CREATE INDEX idx_gst_rate_config_medicine ON gst_rate_config(medicine_id, effective_from) WHERE medicine_id IS NOT NULL;
CREATE INDEX idx_gst_rate_config_service ON gst_rate_config(service_id, effective_from) WHERE service_id IS NOT NULL;
CREATE INDEX idx_gst_rate_config_package ON gst_rate_config(package_id, effective_from) WHERE package_id IS NOT NULL;
CREATE INDEX idx_gst_rate_config_hsn_sac ON gst_rate_config(hsn_sac_code, effective_from) WHERE hsn_sac_code IS NOT NULL;
CREATE INDEX idx_gst_rate_config_dates ON gst_rate_config(effective_from, effective_to);
```

### Design Notes

1. **Entity-Level vs Category-Level Rates**:
   - Entity-level: Specific to one medicine/service/package (most common)
   - Category-level: HSN/SAC code based (affects all items with that code)
   - Priority: Entity-level overrides category-level

2. **Effective Period**:
   - `effective_to = NULL` means currently effective (open-ended)
   - When new rate is added, previous rate's `effective_to` is auto-set

3. **Backward Compatibility**:
   - If no rate config exists for a date, fallback to master table rate
   - Migration can create initial rate configs from current master data

---

## Python Model

### File: app/models/config.py

```python
from sqlalchemy import Column, String, ForeignKey, Boolean, Date, Text, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, TenantMixin, generate_uuid

class GSTRateConfig(Base, TimestampMixin, TenantMixin):
    """
    Date-based GST rate configuration for medicines, services, and packages.
    Supports historical GST rate changes with government notification tracking.
    """
    __tablename__ = 'gst_rate_config'

    rate_config_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)

    # Entity Reference (exactly ONE must be populated)
    medicine_id = Column(UUID(as_uuid=True), ForeignKey('medicines.medicine_id'))
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.service_id'))
    package_id = Column(UUID(as_uuid=True), ForeignKey('packages.package_id'))

    # Alternative: HSN/SAC based rates (for category-level configuration)
    hsn_sac_code = Column(String(10))

    # GST Rate Details
    gst_rate = Column(Numeric(5, 2), nullable=False)
    cgst_rate = Column(Numeric(5, 2))
    sgst_rate = Column(Numeric(5, 2))
    igst_rate = Column(Numeric(5, 2))
    is_gst_exempt = Column(Boolean, default=False)

    # Effective Period
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)  # NULL = currently effective

    # Government Notification Details
    notification_number = Column(String(50))
    notification_date = Column(Date)
    notification_description = Column(Text)
    notification_url = Column(String(500))

    # Metadata
    reason = Column(String(500))

    # Relationships
    hospital = relationship("Hospital")
    medicine = relationship("Medicine", foreign_keys=[medicine_id])
    service = relationship("Service", foreign_keys=[service_id])
    package = relationship("Package", foreign_keys=[package_id])

    __table_args__ = (
        CheckConstraint(
            """
            (medicine_id IS NOT NULL AND service_id IS NULL AND package_id IS NULL AND hsn_sac_code IS NULL) OR
            (medicine_id IS NULL AND service_id IS NOT NULL AND package_id IS NULL AND hsn_sac_code IS NULL) OR
            (medicine_id IS NULL AND service_id IS NULL AND package_id IS NOT NULL AND hsn_sac_code IS NULL) OR
            (medicine_id IS NULL AND service_id IS NULL AND package_id IS NULL AND hsn_sac_code IS NOT NULL)
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
        """Return the type of entity this rate applies to"""
        if self.medicine_id:
            return 'medicine'
        elif self.service_id:
            return 'service'
        elif self.package_id:
            return 'package'
        elif self.hsn_sac_code:
            return 'hsn_sac_code'
        return None

    @property
    def is_currently_effective(self):
        """Check if this rate is currently in effect"""
        from datetime import date
        today = date.today()
        return (self.effective_from <= today and
                (self.effective_to is None or self.effective_to >= today))

    def __repr__(self):
        entity_info = f"{self.entity_type}_{getattr(self, f'{self.entity_type}_id', self.hsn_sac_code)}"
        return f"<GSTRateConfig {entity_info} rate={self.gst_rate}% from={self.effective_from}>"
```

---

## Service Layer

### File: app/services/gst_rate_service.py

```python
"""
GST Rate Service - Date-based GST rate lookup
"""
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session
from app.models.config import GSTRateConfig
from app.models.master import Medicine, Service, Package
import logging

logger = logging.getLogger(__name__)

def get_applicable_gst_rate(
    session: Session,
    hospital_id: str,
    entity_type: str,  # 'medicine', 'service', 'package'
    entity_id: str,
    applicable_date: date,
    hsn_sac_code: Optional[str] = None
) -> Dict:
    """
    Get the GST rate applicable for a given entity on a specific date.

    Priority:
    1. Entity-specific rate config for the date
    2. HSN/SAC code based rate config for the date
    3. Current rate from master table (fallback)

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: Type of entity ('medicine', 'service', 'package')
        entity_id: UUID of the entity
        applicable_date: Date for which rate is needed
        hsn_sac_code: Optional HSN/SAC code for category-level lookup

    Returns:
        Dict with keys: gst_rate, cgst_rate, sgst_rate, igst_rate, is_gst_exempt, source
    """

    # Step 1: Try entity-specific rate config
    entity_id_column = f"{entity_type}_id"

    rate_config = session.query(GSTRateConfig).filter(
        GSTRateConfig.hospital_id == hospital_id,
        getattr(GSTRateConfig, entity_id_column) == entity_id,
        GSTRateConfig.effective_from <= applicable_date,
        (GSTRateConfig.effective_to == None) | (GSTRateConfig.effective_to >= applicable_date)
    ).order_by(GSTRateConfig.effective_from.desc()).first()

    if rate_config:
        logger.info(f"Found entity-specific GST rate config for {entity_type} {entity_id} on {applicable_date}: {rate_config.gst_rate}%")
        return {
            'gst_rate': rate_config.gst_rate,
            'cgst_rate': rate_config.cgst_rate,
            'sgst_rate': rate_config.sgst_rate,
            'igst_rate': rate_config.igst_rate,
            'is_gst_exempt': rate_config.is_gst_exempt,
            'source': 'rate_config_entity',
            'config_id': rate_config.rate_config_id
        }

    # Step 2: Try HSN/SAC code based rate config (if provided)
    if hsn_sac_code:
        rate_config = session.query(GSTRateConfig).filter(
            GSTRateConfig.hospital_id == hospital_id,
            GSTRateConfig.hsn_sac_code == hsn_sac_code,
            GSTRateConfig.effective_from <= applicable_date,
            (GSTRateConfig.effective_to == None) | (GSTRateConfig.effective_to >= applicable_date)
        ).order_by(GSTRateConfig.effective_from.desc()).first()

        if rate_config:
            logger.info(f"Found HSN/SAC based GST rate config for code {hsn_sac_code} on {applicable_date}: {rate_config.gst_rate}%")
            return {
                'gst_rate': rate_config.gst_rate,
                'cgst_rate': rate_config.cgst_rate,
                'sgst_rate': rate_config.sgst_rate,
                'igst_rate': rate_config.igst_rate,
                'is_gst_exempt': rate_config.is_gst_exempt,
                'source': 'rate_config_hsn_sac',
                'config_id': rate_config.rate_config_id
            }

    # Step 3: Fallback to master table (current rate)
    if entity_type == 'medicine':
        entity = session.query(Medicine).filter_by(medicine_id=entity_id).first()
    elif entity_type == 'service':
        entity = session.query(Service).filter_by(service_id=entity_id).first()
    elif entity_type == 'package':
        entity = session.query(Package).filter_by(package_id=entity_id).first()
    else:
        raise ValueError(f"Invalid entity_type: {entity_type}")

    if entity:
        logger.warning(f"No rate config found for {entity_type} {entity_id} on {applicable_date}. Using master table rate: {entity.gst_rate}%")
        return {
            'gst_rate': entity.gst_rate or Decimal('0'),
            'cgst_rate': entity.cgst_rate,
            'sgst_rate': entity.sgst_rate,
            'igst_rate': entity.igst_rate,
            'is_gst_exempt': getattr(entity, 'is_gst_exempt', False),
            'source': 'master_table',
            'config_id': None
        }

    # No rate found anywhere
    logger.error(f"No GST rate found for {entity_type} {entity_id}")
    return {
        'gst_rate': Decimal('0'),
        'cgst_rate': Decimal('0'),
        'sgst_rate': Decimal('0'),
        'igst_rate': Decimal('0'),
        'is_gst_exempt': False,
        'source': 'default',
        'config_id': None
    }


def add_gst_rate_change(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str,
    new_rate: Decimal,
    effective_from: date,
    notification_number: Optional[str] = None,
    notification_date: Optional[date] = None,
    reason: Optional[str] = None,
    current_user_id: Optional[str] = None,
    cgst_rate: Optional[Decimal] = None,
    sgst_rate: Optional[Decimal] = None,
    igst_rate: Optional[Decimal] = None
) -> GSTRateConfig:
    """
    Add a new GST rate change for an entity.
    Automatically closes the previous rate config's effective period.

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: 'medicine', 'service', or 'package'
        entity_id: UUID of the entity
        new_rate: New GST rate (total)
        effective_from: Date from which new rate is effective
        notification_number: Government notification reference
        notification_date: Date of government notification
        reason: Reason for rate change
        current_user_id: User making the change
        cgst_rate: Optional CGST rate (if None, will be calculated as new_rate/2)
        sgst_rate: Optional SGST rate (if None, will be calculated as new_rate/2)
        igst_rate: Optional IGST rate (if None, will equal new_rate)

    Returns:
        Created GSTRateConfig record
    """

    # Calculate component rates if not provided
    if cgst_rate is None:
        cgst_rate = new_rate / 2
    if sgst_rate is None:
        sgst_rate = new_rate / 2
    if igst_rate is None:
        igst_rate = new_rate

    # Close previous rate config (if exists)
    entity_id_column = f"{entity_type}_id"
    previous_config = session.query(GSTRateConfig).filter(
        GSTRateConfig.hospital_id == hospital_id,
        getattr(GSTRateConfig, entity_id_column) == entity_id,
        GSTRateConfig.effective_to == None  # Currently open
    ).first()

    if previous_config:
        # Set effective_to to day before new rate starts
        from datetime import timedelta
        previous_config.effective_to = effective_from - timedelta(days=1)
        previous_config.updated_by = current_user_id
        logger.info(f"Closed previous rate config: {previous_config.rate_config_id}, effective_to={previous_config.effective_to}")

    # Create new rate config
    new_config = GSTRateConfig(
        hospital_id=hospital_id,
        **{entity_id_column: entity_id},
        gst_rate=new_rate,
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        igst_rate=igst_rate,
        effective_from=effective_from,
        effective_to=None,  # Open-ended
        notification_number=notification_number,
        notification_date=notification_date,
        reason=reason,
        created_by=current_user_id
    )

    session.add(new_config)
    session.flush()

    logger.info(f"Created new GST rate config: {new_config.rate_config_id}, rate={new_rate}%, effective_from={effective_from}")

    return new_config


def get_rate_history(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str
) -> list:
    """
    Get complete GST rate change history for an entity.

    Returns:
        List of GSTRateConfig records ordered by effective_from desc
    """
    entity_id_column = f"{entity_type}_id"

    return session.query(GSTRateConfig).filter(
        GSTRateConfig.hospital_id == hospital_id,
        getattr(GSTRateConfig, entity_id_column) == entity_id
    ).order_by(GSTRateConfig.effective_from.desc()).all()
```

---

## Integration with Invoice Creation

### Modification: billing_service.py

**Current Code** (app/services/billing_service.py:1289):
```python
medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
if medicine:
    gst_rate = medicine.gst_rate or Decimal('0')
```

**New Code** (with date-based lookup):
```python
from app.services.gst_rate_service import get_applicable_gst_rate
from datetime import date

medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
if medicine:
    # Get GST rate applicable on invoice date (not current rate)
    invoice_date = invoice_data.get('invoice_date', date.today())
    rate_info = get_applicable_gst_rate(
        session=session,
        hospital_id=hospital_id,
        entity_type='medicine',
        entity_id=item_id,
        applicable_date=invoice_date,
        hsn_sac_code=medicine.hsn_code
    )

    gst_rate = rate_info['gst_rate']
    is_gst_exempt = rate_info['is_gst_exempt']
    cgst_rate = rate_info['cgst_rate']
    sgst_rate = rate_info['sgst_rate']
    igst_rate = rate_info['igst_rate']

    logger.info(f"Medicine '{medicine.medicine_name}': Using {rate_info['source']} GST rate={gst_rate}% for date {invoice_date}")
```

Similar changes needed for:
- Service-based invoice line items
- Package-based invoice line items

---

## Migration Strategy

### Phase 1: Database Setup (Week 1)

1. **Create GST Rate Config Table**
   - Run migration to create `gst_rate_config` table
   - Add indexes for performance

2. **Create Model and Service**
   - Add `GSTRateConfig` model to `app/models/config.py`
   - Create `app/services/gst_rate_service.py`

3. **Initial Data Migration (Optional)**
   - Create initial rate configs from current master table rates
   - Set effective_from as a past date (e.g., 2020-01-01)
   - This provides historical consistency

### Phase 2: Service Integration (Week 2)

1. **Update Invoice Creation Logic**
   - Modify `billing_service.py` to use `get_applicable_gst_rate()`
   - Test with various dates

2. **Update Package Creation**
   - Similar changes for package invoice creation

3. **Testing**
   - Unit tests for rate lookup service
   - Integration tests for invoice creation with different dates

### Phase 3: UI for Rate Management (Week 3-4)

1. **Admin UI for Rate Configuration**
   - Screen to add new rate changes
   - View rate history
   - Bulk rate update for category (HSN/SAC based)

2. **Master Data Enhancements**
   - Show "Current Rate" vs "Historical Rates" in medicine/service/package detail
   - Link to rate change history

---

## Example Usage Scenarios

### Scenario 1: Government Increases Medicine GST from 12% to 18%

**Government Notification**: No. 01/2025-Central Tax (Rate), dated March 15, 2025, effective April 1, 2025

**Action**:
```python
add_gst_rate_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    new_rate=Decimal('18'),
    effective_from=date(2025, 4, 1),
    notification_number='No. 01/2025-Central Tax (Rate)',
    notification_date=date(2025, 3, 15),
    reason='GST rate increased from 12% to 18% as per government notification',
    current_user_id=admin_user_id
)
```

**Result**:
- Invoice dated March 31, 2025 → Uses 12% GST ✅
- Invoice dated April 1, 2025 → Uses 18% GST ✅
- Invoice dated April 2, 2025 → Uses 18% GST ✅

### Scenario 2: Bulk Category Update (All Cosmetic Services)

**All services with SAC code 999333 (Cosmetic Services) rate changes from 18% to 12%**

```python
add_gst_rate_change(
    session=session,
    hospital_id=hospital_id,
    entity_type='hsn_sac_code',  # Category-level
    entity_id=None,
    hsn_sac_code='999333',
    new_rate=Decimal('12'),
    effective_from=date(2025, 7, 1),
    notification_number='No. 15/2025-Central Tax (Rate)',
    notification_date=date(2025, 6, 20),
    reason='GST rate reduced for cosmetic services',
    current_user_id=admin_user_id
)
```

**Result**: All services with SAC 999333 will use 12% from July 1, 2025 onwards

---

## Benefits

### Compliance
- ✅ Accurate historical GST rates for audits
- ✅ Government notification tracking
- ✅ Date-based rate selection ensures compliance

### Operational
- ✅ Easy rate updates (no manual master data changes)
- ✅ Bulk updates possible (HSN/SAC based)
- ✅ Audit trail of all rate changes

### Reporting
- ✅ Rate change history available
- ✅ Impact analysis possible (which invoices affected)
- ✅ Notification reference for tax audits

---

## Testing Strategy

### Unit Tests
1. `test_get_applicable_gst_rate_entity_specific()`
2. `test_get_applicable_gst_rate_hsn_sac_based()`
3. `test_get_applicable_gst_rate_fallback_to_master()`
4. `test_add_gst_rate_change_closes_previous()`
5. `test_get_rate_history()`

### Integration Tests
1. Create invoice before rate change date → Verify old rate used
2. Create invoice on rate change date → Verify new rate used
3. Create invoice after rate change date → Verify new rate used
4. Create invoice with no rate config → Verify master table fallback

### Edge Cases
1. Multiple rate changes in short period
2. Rate change on same day as invoice
3. Future-dated invoices
4. Historical invoice amendments

---

## Implementation Checklist

### Database
- [ ] Create `gst_rate_config` table migration
- [ ] Add indexes
- [ ] Run migration on dev database
- [ ] Verify constraints work correctly

### Models
- [ ] Add `GSTRateConfig` model to `app/models/config.py`
- [ ] Update model imports
- [ ] Test model instantiation

### Services
- [ ] Create `app/services/gst_rate_service.py`
- [ ] Implement `get_applicable_gst_rate()`
- [ ] Implement `add_gst_rate_change()`
- [ ] Implement `get_rate_history()`
- [ ] Add logging

### Invoice Integration
- [ ] Update `billing_service.py` medicine GST lookup
- [ ] Update service GST lookup
- [ ] Update package GST lookup
- [ ] Test invoice creation with various dates

### Testing
- [ ] Write unit tests for gst_rate_service
- [ ] Write integration tests for invoice creation
- [ ] Test edge cases
- [ ] Performance testing with large rate config dataset

### UI (Future Phase)
- [ ] Admin screen for rate configuration
- [ ] Rate history viewer
- [ ] Bulk rate update tool
- [ ] Master data integration

---

## Risk Analysis

### Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance degradation with large config dataset | Medium | Proper indexing, caching frequently used rates |
| Data migration complexity | Medium | Phased approach, thorough testing |
| User training required | Low | Comprehensive documentation, simple UI |
| Historical data accuracy concerns | High | Optional initial migration, clear documentation |

---

## Timeline Estimate

- **Database Setup**: 2 days
- **Model and Service**: 3 days
- **Invoice Integration**: 3 days
- **Testing**: 3 days
- **Documentation**: 1 day
- **Total**: ~2 weeks for core implementation

**UI Phase** (optional, future): Additional 2 weeks

---

**Status**: ✅ **DESIGN COMPLETE - READY FOR REVIEW**

*Designed by: Claude Code*
*Date: 2025-11-17*
