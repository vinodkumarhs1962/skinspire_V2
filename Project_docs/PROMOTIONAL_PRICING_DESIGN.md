# Promotional Pricing and Time-Sensitive Discounts - Design Extension

**Date**: 2025-11-17
**Version**: 1.0
**Status**: Design Phase
**Extends**: PRICING_AND_GST_VERSIONING_DESIGN.md

---

## Executive Summary

This document extends the pricing and GST versioning system to support **time-sensitive promotional pricing** and **discount campaigns**. This enables the hospital to run:
- Seasonal discounts (e.g., Summer Special - 20% off laser treatments)
- Festival offers (e.g., Diwali Package Discount)
- Clearance sales (e.g., Medicines nearing expiry - 30% off)
- Early bird discounts (e.g., Book in advance, get 15% off)
- Loyalty discounts (e.g., Repeat customers get 10% off)

---

## Business Scenarios

### Scenario 1: Festival Discount Campaign
**Campaign**: "Diwali Special - 25% off all cosmetic packages"
**Duration**: October 20-31, 2025
**Applicable to**: All cosmetic packages
**Additional rules**: Minimum package value ₹5,000

### Scenario 2: Clearance Sale
**Campaign**: "Medicines expiring in 3 months - 30% off"
**Duration**: Ongoing (auto-applied based on expiry date)
**Applicable to**: Specific medicines based on expiry
**Additional rules**: Cannot be combined with other offers

### Scenario 3: Early Bird Appointment Discount
**Campaign**: "Book 7 days in advance - 15% off consultation"
**Duration**: Permanent offer
**Applicable to**: Services only
**Additional rules**: Appointment must be booked at least 7 days ahead

### Scenario 4: Volume Discount
**Campaign**: "Buy 10 or more units - 20% off"
**Duration**: Permanent for specific medicines
**Applicable to**: Specific medicine categories
**Additional rules**: Minimum quantity 10

---

## Database Design

### New Table: Promotional Campaigns

```sql
CREATE TABLE promotional_campaigns (
    campaign_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID REFERENCES branches(branch_id),

    -- Campaign Details
    campaign_name VARCHAR(200) NOT NULL,
    campaign_code VARCHAR(50) UNIQUE,  -- e.g., 'DIWALI2025', 'SUMMER20'
    description TEXT,
    campaign_type VARCHAR(50),  -- 'seasonal', 'festival', 'clearance', 'loyalty', 'volume', 'early_bird'

    -- Validity Period
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_to TIMESTAMP WITH TIME ZONE,  -- NULL = permanent campaign
    is_active BOOLEAN DEFAULT true,

    -- Applicability Scope
    applies_to VARCHAR(50),  -- 'all', 'medicine', 'service', 'package', 'category'

    -- Specific Entities (if applies_to is specific)
    applicable_medicine_ids UUID[],  -- Array of medicine UUIDs
    applicable_service_ids UUID[],   -- Array of service UUIDs
    applicable_package_ids UUID[],   -- Array of package UUIDs
    applicable_categories VARCHAR[],  -- Array of category names/HSN/SAC codes

    -- Discount Configuration
    discount_type VARCHAR(30),  -- 'percentage', 'fixed_amount', 'special_price', 'buy_x_get_y'
    discount_percentage NUMERIC(5, 2),
    discount_fixed_amount NUMERIC(12, 2),
    special_price NUMERIC(12, 2),  -- Override price (e.g., flat ₹500)

    -- Buy X Get Y Configuration (for BOGO type offers)
    buy_quantity INTEGER,    -- Buy X
    get_quantity INTEGER,    -- Get Y free
    get_discount_percent NUMERIC(5, 2),  -- Or Y at X% discount

    -- Applicability Rules
    min_quantity NUMERIC(10, 2),     -- Minimum quantity to qualify
    max_quantity NUMERIC(10, 2),     -- Maximum quantity allowed
    min_invoice_value NUMERIC(12, 2),  -- Minimum invoice value
    min_advance_days INTEGER,        -- Minimum days in advance (for appointments)

    -- Customer Eligibility
    customer_type VARCHAR[],  -- ['new', 'returning', 'vip', 'all']
    min_previous_visits INTEGER,  -- For loyalty discounts

    -- Priority and Stacking
    priority INTEGER DEFAULT 0,  -- Higher priority wins if multiple campaigns match
    can_stack BOOLEAN DEFAULT false,  -- Can be combined with other campaigns
    cannot_combine_with UUID[],  -- Array of campaign IDs that cannot be combined

    -- Usage Limits
    max_uses_total INTEGER,      -- Max uses across all customers
    max_uses_per_customer INTEGER,
    current_use_count INTEGER DEFAULT 0,

    -- Approval and Workflow
    approval_required BOOLEAN DEFAULT false,
    approved_by VARCHAR(15) REFERENCES users(user_id),
    approved_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_by VARCHAR(15) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(15),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT false
);

-- Indexes
CREATE INDEX idx_promo_campaigns_active ON promotional_campaigns(hospital_id, is_active, valid_from, valid_to) WHERE is_deleted = false;
CREATE INDEX idx_promo_campaigns_dates ON promotional_campaigns(valid_from, valid_to) WHERE is_deleted = false AND is_active = true;
CREATE INDEX idx_promo_campaigns_code ON promotional_campaigns(campaign_code) WHERE is_deleted = false;
```

### New Table: Campaign Usage Tracking

```sql
CREATE TABLE campaign_usage_log (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES promotional_campaigns(campaign_id),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Usage Details
    invoice_id UUID REFERENCES invoice_header(invoice_id),
    patient_id UUID REFERENCES patients(patient_id),
    usage_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Discount Applied
    original_amount NUMERIC(12, 2),
    discount_amount NUMERIC(12, 2),
    final_amount NUMERIC(12, 2),

    -- Line Item Reference
    line_item_id UUID REFERENCES invoice_line_item(line_item_id),
    entity_type VARCHAR(30),  -- 'medicine', 'service', 'package'
    entity_id UUID,

    -- Metadata
    created_by VARCHAR(15) REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_campaign_usage_campaign ON campaign_usage_log(campaign_id, usage_date);
CREATE INDEX idx_campaign_usage_patient ON campaign_usage_log(patient_id, usage_date);
CREATE INDEX idx_campaign_usage_invoice ON campaign_usage_log(invoice_id);
```

---

## Python Models

### File: app/models/config.py (additions)

```python
from sqlalchemy import Column, String, ForeignKey, Boolean, Integer, TIMESTAMP, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base, TimestampMixin, TenantMixin, generate_uuid

class PromotionalCampaign(Base, TimestampMixin, TenantMixin):
    """
    Time-sensitive promotional pricing and discount campaigns.
    Supports seasonal offers, clearance sales, volume discounts, and more.
    """
    __tablename__ = 'promotional_campaigns'

    campaign_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.branch_id'))

    # Campaign Details
    campaign_name = Column(String(200), nullable=False)
    campaign_code = Column(String(50), unique=True)
    description = Column(Text)
    campaign_type = Column(String(50))  # 'seasonal', 'festival', 'clearance', etc.

    # Validity Period
    valid_from = Column(TIMESTAMP(timezone=True), nullable=False)
    valid_to = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True)

    # Applicability Scope
    applies_to = Column(String(50))  # 'all', 'medicine', 'service', 'package', 'category'
    applicable_medicine_ids = Column(ARRAY(UUID))
    applicable_service_ids = Column(ARRAY(UUID))
    applicable_package_ids = Column(ARRAY(UUID))
    applicable_categories = Column(ARRAY(String))

    # Discount Configuration
    discount_type = Column(String(30))  # 'percentage', 'fixed_amount', 'special_price'
    discount_percentage = Column(Numeric(5, 2))
    discount_fixed_amount = Column(Numeric(12, 2))
    special_price = Column(Numeric(12, 2))

    # Buy X Get Y
    buy_quantity = Column(Integer)
    get_quantity = Column(Integer)
    get_discount_percent = Column(Numeric(5, 2))

    # Applicability Rules
    min_quantity = Column(Numeric(10, 2))
    max_quantity = Column(Numeric(10, 2))
    min_invoice_value = Column(Numeric(12, 2))
    min_advance_days = Column(Integer)

    # Customer Eligibility
    customer_type = Column(ARRAY(String))
    min_previous_visits = Column(Integer)

    # Priority and Stacking
    priority = Column(Integer, default=0)
    can_stack = Column(Boolean, default=False)
    cannot_combine_with = Column(ARRAY(UUID))

    # Usage Limits
    max_uses_total = Column(Integer)
    max_uses_per_customer = Column(Integer)
    current_use_count = Column(Integer, default=0)

    # Approval
    approval_required = Column(Boolean, default=False)
    approved_by = Column(String(15), ForeignKey('users.user_id'))
    approved_at = Column(TIMESTAMP(timezone=True))

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    hospital = relationship("Hospital")
    branch = relationship("Branch")
    approver = relationship("User", foreign_keys=[approved_by])
    usage_logs = relationship("CampaignUsageLog", back_populates="campaign")

    @property
    def is_currently_valid(self):
        """Check if campaign is currently valid"""
        now = datetime.now(timezone.utc)
        return (self.is_active and
                self.valid_from <= now and
                (self.valid_to is None or self.valid_to >= now) and
                not self.is_deleted)

    @property
    def is_usage_limit_reached(self):
        """Check if campaign has reached its usage limit"""
        if self.max_uses_total is None:
            return False
        return self.current_use_count >= self.max_uses_total

    def __repr__(self):
        return f"<PromotionalCampaign {self.campaign_code} '{self.campaign_name}' valid={self.valid_from} to {self.valid_to}>"


class CampaignUsageLog(Base, TimestampMixin, TenantMixin):
    """
    Tracks usage of promotional campaigns for analytics and limit enforcement.
    """
    __tablename__ = 'campaign_usage_log'

    usage_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('promotional_campaigns.campaign_id'), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey('hospitals.hospital_id'), nullable=False)

    # Usage Details
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('invoice_header.invoice_id'))
    patient_id = Column(UUID(as_uuid=True), ForeignKey('patients.patient_id'))
    usage_date = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Discount Applied
    original_amount = Column(Numeric(12, 2))
    discount_amount = Column(Numeric(12, 2))
    final_amount = Column(Numeric(12, 2))

    # Line Item Reference
    line_item_id = Column(UUID(as_uuid=True), ForeignKey('invoice_line_item.line_item_id'))
    entity_type = Column(String(30))
    entity_id = Column(UUID(as_uuid=True))

    # Relationships
    campaign = relationship("PromotionalCampaign", back_populates="usage_logs")
    hospital = relationship("Hospital")
    invoice = relationship("InvoiceHeader")
    patient = relationship("Patient")

    def __repr__(self):
        return f"<CampaignUsageLog campaign={self.campaign_id} discount=₹{self.discount_amount}>"
```

---

## Service Layer

### File: app/services/promotional_service.py

```python
"""
Promotional Pricing Service - Time-sensitive discounts and campaigns
"""
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.config import PromotionalCampaign, CampaignUsageLog
import logging

logger = logging.getLogger(__name__)


def get_applicable_promotions(
    session: Session,
    hospital_id: str,
    entity_type: str,  # 'medicine', 'service', 'package'
    entity_id: str,
    patient_id: Optional[str] = None,
    quantity: Decimal = Decimal('1'),
    invoice_value: Optional[Decimal] = None,
    invoice_date: datetime = None
) -> List[Dict]:
    """
    Get all applicable promotional campaigns for a given entity at a given time.

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: Type of entity
        entity_id: UUID of entity
        patient_id: Patient UUID (for eligibility check)
        quantity: Quantity being purchased
        invoice_value: Total invoice value (for minimum value rules)
        invoice_date: Invoice datetime (defaults to now)

    Returns:
        List of applicable campaigns (dicts) sorted by priority desc
    """

    if invoice_date is None:
        invoice_date = datetime.now(timezone.utc)

    # Query active campaigns valid at invoice_date
    campaigns = session.query(PromotionalCampaign).filter(
        and_(
            PromotionalCampaign.hospital_id == hospital_id,
            PromotionalCampaign.is_active == True,
            PromotionalCampaign.is_deleted == False,
            PromotionalCampaign.valid_from <= invoice_date,
            or_(
                PromotionalCampaign.valid_to == None,
                PromotionalCampaign.valid_to >= invoice_date
            )
        )
    ).all()

    applicable = []

    for campaign in campaigns:
        if _is_campaign_applicable(
            campaign, entity_type, entity_id, patient_id,
            quantity, invoice_value, session
        ):
            applicable.append({
                'campaign_id': campaign.campaign_id,
                'campaign_code': campaign.campaign_code,
                'campaign_name': campaign.campaign_name,
                'discount_type': campaign.discount_type,
                'discount_percentage': campaign.discount_percentage,
                'discount_fixed_amount': campaign.discount_fixed_amount,
                'special_price': campaign.special_price,
                'priority': campaign.priority,
                'can_stack': campaign.can_stack,
                'cannot_combine_with': campaign.cannot_combine_with or []
            })

    # Sort by priority descending
    applicable.sort(key=lambda x: x['priority'], reverse=True)

    logger.info(f"Found {len(applicable)} applicable campaigns for {entity_type} {entity_id}")

    return applicable


def _is_campaign_applicable(
    campaign: PromotionalCampaign,
    entity_type: str,
    entity_id: str,
    patient_id: Optional[str],
    quantity: Decimal,
    invoice_value: Optional[Decimal],
    session: Session
) -> bool:
    """
    Check if a campaign is applicable to the given entity and conditions.
    """

    # Check usage limit
    if campaign.is_usage_limit_reached:
        logger.debug(f"Campaign {campaign.campaign_code} has reached usage limit")
        return False

    # Check entity applicability
    if campaign.applies_to == 'all':
        pass  # Applies to everything
    elif campaign.applies_to == entity_type:
        # Check if specific entity IDs are specified
        entity_id_field = f"applicable_{entity_type}_ids"
        applicable_ids = getattr(campaign, entity_id_field, None)
        if applicable_ids and entity_id not in [str(id) for id in applicable_ids]:
            logger.debug(f"Entity {entity_id} not in campaign's applicable list")
            return False
    else:
        # Campaign applies to different entity type
        return False

    # Check quantity rules
    if campaign.min_quantity and quantity < campaign.min_quantity:
        logger.debug(f"Quantity {quantity} below minimum {campaign.min_quantity}")
        return False
    if campaign.max_quantity and quantity > campaign.max_quantity:
        logger.debug(f"Quantity {quantity} exceeds maximum {campaign.max_quantity}")
        return False

    # Check invoice value rules
    if campaign.min_invoice_value and invoice_value:
        if invoice_value < campaign.min_invoice_value:
            logger.debug(f"Invoice value {invoice_value} below minimum {campaign.min_invoice_value}")
            return False

    # Check customer eligibility (if patient_id provided)
    if patient_id and campaign.customer_type:
        # This would require customer type classification logic
        # For now, simplified check
        pass

    if patient_id and campaign.min_previous_visits:
        # Count previous visits for this patient
        from app.models.transaction import InvoiceHeader
        visit_count = session.query(InvoiceHeader).filter_by(
            patient_id=patient_id
        ).count()
        if visit_count < campaign.min_previous_visits:
            logger.debug(f"Patient has {visit_count} visits, needs {campaign.min_previous_visits}")
            return False

    # Check per-customer usage limit
    if patient_id and campaign.max_uses_per_customer:
        usage_count = session.query(CampaignUsageLog).filter_by(
            campaign_id=campaign.campaign_id,
            patient_id=patient_id
        ).count()
        if usage_count >= campaign.max_uses_per_customer:
            logger.debug(f"Patient has used campaign {usage_count} times (max {campaign.max_uses_per_customer})")
            return False

    return True


def calculate_discounted_price(
    original_price: Decimal,
    quantity: Decimal,
    campaigns: List[Dict]
) -> Dict:
    """
    Calculate final price after applying promotional discounts.

    Args:
        original_price: Original unit price
        quantity: Quantity
        campaigns: List of applicable campaigns (from get_applicable_promotions)

    Returns:
        Dict with: original_amount, discount_amount, final_amount, campaigns_applied
    """

    if not campaigns:
        total_amount = original_price * quantity
        return {
            'original_amount': total_amount,
            'discount_amount': Decimal('0'),
            'final_amount': total_amount,
            'campaigns_applied': []
        }

    # Resolve campaign stacking and conflicts
    campaigns_to_apply = _resolve_campaign_stacking(campaigns)

    original_amount = original_price * quantity
    discount_amount = Decimal('0')
    campaigns_applied = []

    for campaign in campaigns_to_apply:
        campaign_discount = Decimal('0')

        if campaign['discount_type'] == 'percentage':
            campaign_discount = (original_amount * campaign['discount_percentage']) / 100

        elif campaign['discount_type'] == 'fixed_amount':
            campaign_discount = campaign['discount_fixed_amount'] * quantity

        elif campaign['discount_type'] == 'special_price':
            # Special price override
            special_total = campaign['special_price'] * quantity
            campaign_discount = original_amount - special_total

        discount_amount += campaign_discount
        campaigns_applied.append({
            'campaign_id': campaign['campaign_id'],
            'campaign_code': campaign['campaign_code'],
            'campaign_name': campaign['campaign_name'],
            'discount': campaign_discount
        })

    # Ensure discount doesn't exceed original amount
    if discount_amount > original_amount:
        discount_amount = original_amount

    final_amount = original_amount - discount_amount

    return {
        'original_amount': original_amount,
        'discount_amount': discount_amount,
        'final_amount': final_amount,
        'campaigns_applied': campaigns_applied
    }


def _resolve_campaign_stacking(campaigns: List[Dict]) -> List[Dict]:
    """
    Resolve which campaigns can be applied together based on stacking rules.
    Returns campaigns that can be safely stacked, sorted by priority.
    """

    if not campaigns:
        return []

    # Already sorted by priority desc
    selected = []

    for campaign in campaigns:
        # Check if this campaign can be combined with already selected ones
        can_add = True

        if not campaign['can_stack'] and len(selected) > 0:
            # This campaign cannot stack with others
            can_add = False

        # Check cannot_combine_with
        for existing in selected:
            if str(existing['campaign_id']) in [str(id) for id in campaign['cannot_combine_with']]:
                can_add = False
                break

        if can_add:
            selected.append(campaign)

        # If highest priority campaign doesn't allow stacking, only use it
        if len(selected) == 1 and not selected[0]['can_stack']:
            break

    return selected


def log_campaign_usage(
    session: Session,
    campaign_id: str,
    hospital_id: str,
    invoice_id: str,
    patient_id: str,
    line_item_id: str,
    entity_type: str,
    entity_id: str,
    original_amount: Decimal,
    discount_amount: Decimal,
    final_amount: Decimal,
    current_user_id: Optional[str] = None
) -> CampaignUsageLog:
    """
    Log usage of a promotional campaign for tracking and limit enforcement.
    """

    usage_log = CampaignUsageLog(
        campaign_id=campaign_id,
        hospital_id=hospital_id,
        invoice_id=invoice_id,
        patient_id=patient_id,
        line_item_id=line_item_id,
        entity_type=entity_type,
        entity_id=entity_id,
        original_amount=original_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
        created_by=current_user_id
    )

    session.add(usage_log)

    # Update campaign usage count
    campaign = session.query(PromotionalCampaign).filter_by(
        campaign_id=campaign_id
    ).first()

    if campaign:
        campaign.current_use_count = (campaign.current_use_count or 0) + 1

    session.flush()

    logger.info(f"Logged campaign usage: {campaign_id}, discount=₹{discount_amount}")

    return usage_log


def create_promotional_campaign(
    session: Session,
    hospital_id: str,
    campaign_name: str,
    campaign_code: str,
    valid_from: datetime,
    valid_to: Optional[datetime],
    discount_type: str,
    current_user_id: Optional[str] = None,
    **kwargs
) -> PromotionalCampaign:
    """
    Create a new promotional campaign.

    Required kwargs based on discount_type:
    - percentage: discount_percentage
    - fixed_amount: discount_fixed_amount
    - special_price: special_price

    Optional kwargs: See PromotionalCampaign model for all fields
    """

    campaign = PromotionalCampaign(
        hospital_id=hospital_id,
        campaign_name=campaign_name,
        campaign_code=campaign_code,
        valid_from=valid_from,
        valid_to=valid_to,
        discount_type=discount_type,
        created_by=current_user_id,
        **kwargs
    )

    session.add(campaign)
    session.flush()

    logger.info(f"Created promotional campaign: {campaign_code} - {campaign_name}")

    return campaign
```

---

## Integration with Invoice Creation

### Modification: billing_service.py

**After getting pricing and tax, apply promotions**:

```python
from app.services.pricing_tax_service import get_applicable_pricing_and_tax
from app.services.promotional_service import get_applicable_promotions, calculate_discounted_price
from datetime import datetime

# Step 1: Get base pricing and tax (date-based)
invoice_date = invoice_data.get('invoice_date', datetime.now())
pricing_tax = get_applicable_pricing_and_tax(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    applicable_date=invoice_date.date()
)

base_price = pricing_tax.get('mrp') or pricing_tax.get('selling_price')
gst_rate = pricing_tax['gst_rate']

# Step 2: Get applicable promotions (time-sensitive)
applicable_campaigns = get_applicable_promotions(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    patient_id=patient_id,
    quantity=quantity,
    invoice_value=estimated_invoice_total,
    invoice_date=invoice_date
)

# Step 3: Calculate discounted price
pricing_result = calculate_discounted_price(
    original_price=base_price,
    quantity=quantity,
    campaigns=applicable_campaigns
)

# Use discounted price for invoice line item
unit_price = pricing_result['final_amount'] / quantity if quantity > 0 else Decimal('0')
discount_amount = pricing_result['discount_amount']

# Log campaigns used (after invoice creation)
for campaign_info in pricing_result['campaigns_applied']:
    log_campaign_usage(
        session=session,
        campaign_id=campaign_info['campaign_id'],
        hospital_id=hospital_id,
        invoice_id=invoice_id,
        patient_id=patient_id,
        line_item_id=line_item_id,
        entity_type='medicine',
        entity_id=medicine_id,
        original_amount=pricing_result['original_amount'],
        discount_amount=campaign_info['discount'],
        final_amount=pricing_result['final_amount']
    )

logger.info(f"Applied {len(pricing_result['campaigns_applied'])} promotional campaigns, "
            f"discount=₹{discount_amount}")
```

---

## Example Campaign Configurations

### Example 1: Diwali Festival Offer

```python
create_promotional_campaign(
    session=session,
    hospital_id=hospital_id,
    campaign_name="Diwali Special - 25% off Cosmetic Packages",
    campaign_code="DIWALI2025",
    campaign_type="festival",
    valid_from=datetime(2025, 10, 20, 0, 0, 0, tzinfo=timezone.utc),
    valid_to=datetime(2025, 10, 31, 23, 59, 59, tzinfo=timezone.utc),
    discount_type="percentage",
    discount_percentage=Decimal('25'),
    applies_to="package",
    applicable_categories=['Cosmetic'],
    min_invoice_value=Decimal('5000'),
    priority=10,
    can_stack=False,
    max_uses_total=100,
    current_user_id=admin_user_id
)
```

### Example 2: Volume Discount

```python
create_promotional_campaign(
    session=session,
    hospital_id=hospital_id,
    campaign_name="Buy 10+ Units - Get 20% Off",
    campaign_code="BULK20",
    campaign_type="volume",
    valid_from=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    valid_to=None,  # Permanent
    discount_type="percentage",
    discount_percentage=Decimal('20'),
    applies_to="medicine",
    min_quantity=Decimal('10'),
    priority=5,
    can_stack=True,  # Can combine with other offers
    current_user_id=admin_user_id
)
```

### Example 3: Clearance Sale (Expiry-based)

```python
create_promotional_campaign(
    session=session,
    hospital_id=hospital_id,
    campaign_name="Medicines Expiring Soon - 30% Off",
    campaign_code="CLEARANCE30",
    campaign_type="clearance",
    valid_from=datetime.now(timezone.utc),
    valid_to=None,
    discount_type="percentage",
    discount_percentage=Decimal('30'),
    applies_to="medicine",
    applicable_medicine_ids=expiring_medicine_ids,  # Dynamically populated
    priority=15,  # Higher priority
    can_stack=False,
    cannot_combine_with=[],  # Cannot combine with anything
    description="Special discount on medicines expiring within 3 months",
    current_user_id=admin_user_id
)
```

---

## Benefits

### Business Flexibility
- ✅ Run seasonal promotions easily
- ✅ Reward loyal customers
- ✅ Clear expiring stock quickly
- ✅ Attract new customers with special offers

### Operational Control
- ✅ Time-bound campaigns (auto start/stop)
- ✅ Usage limits (prevent abuse)
- ✅ Approval workflow for high-value discounts
- ✅ Stacking rules (control which offers can combine)

### Analytics
- ✅ Track campaign effectiveness
- ✅ Measure discount ROI
- ✅ Customer segmentation insights
- ✅ Usage pattern analysis

---

## Implementation Timeline

- **Database**: 2 days
- **Models**: 2 days
- **Promotional Service**: 3 days
- **Invoice Integration**: 2 days
- **Campaign Management UI**: 1 week (optional)
- **Testing**: 3 days
- **Total**: ~2-3 weeks

---

**Status**: ✅ **DESIGN COMPLETE - READY FOR REVIEW**

*Designed by: Claude Code*
*Date: 2025-11-17*
*Extends: PRICING_AND_GST_VERSIONING_DESIGN.md*
