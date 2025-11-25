"""
Pricing and Tax Service - Date-based pricing and GST rate lookup

This service provides date-based versioning of pricing (MRP, selling price) and GST rates
for medicines, services, and packages. It ensures tax compliance by using rates applicable
on the invoice date, not current rates.

Priority Lookup:
1. Date-specific config from entity_pricing_tax_config table
2. Current values from master table (fallback)
3. Campaign hooks (optional promotional pricing)
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, List, Any
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
    applicable_date: date,
    apply_campaigns: bool = True,
    campaign_context: Optional[Dict[str, Any]] = None
) -> Dict:
    """
    Get pricing and GST rate applicable for a given entity on a specific date.

    This is the PRIMARY function used by invoice creation to get correct rates.

    Priority:
    1. Date-specific config from entity_pricing_tax_config (historical accuracy)
    2. Current values from master table (fallback for entities without configs)
    3. Campaign hooks (optional promotional pricing - applied to base price)

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: Type of entity ('medicine', 'service', 'package')
        entity_id: UUID of the entity
        applicable_date: Date for which pricing/tax is needed (invoice date)
        apply_campaigns: Whether to apply campaign hooks (default: True)
        campaign_context: Context for campaigns (quantity, patient_id, etc.)

    Returns:
        Dict with pricing and tax information:
        {
            'gst_rate': Decimal,
            'cgst_rate': Decimal,
            'sgst_rate': Decimal,
            'igst_rate': Decimal,
            'is_gst_exempt': bool,
            'gst_inclusive': bool,
            'mrp': Decimal (for medicines),
            'selling_price': Decimal (for medicines),
            'cost_price': Decimal,
            'applicable_price': Decimal,
            'source': str ('config', 'master_table', or 'campaign'),
            'config_id': UUID or None,
            'campaign_applied': bool,
            'campaign_info': Dict or None  # If campaign was applied
        }

    Example:
        >>> pricing = get_applicable_pricing_and_tax(
        ...     session, hospital_id, 'medicine', medicine_id, date(2025, 7, 15),
        ...     campaign_context={'quantity': 10, 'patient_id': 'patient-uuid'}
        ... )
        >>> gst_rate = pricing['gst_rate']  # GST rate applicable on July 15, 2025
        >>> price = pricing['applicable_price']  # Price after campaigns (if any)
    """

    # Validate entity_type
    if entity_type not in ['medicine', 'service', 'package']:
        raise ValueError(f"Invalid entity_type: {entity_type}. Must be 'medicine', 'service', or 'package'")

    entity_id_column = f"{entity_type}_id"

    # Step 1: Try to find date-specific config
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
        logger.info(f"Found pricing/tax config for {entity_type} {entity_id} on {applicable_date}: "
                   f"MRP={config.mrp}, GST={config.gst_rate}%")
        result = _build_response_from_config(config, entity_type)
    else:
        # Step 2: Fallback to master table
        logger.warning(f"No config found for {entity_type} {entity_id} on {applicable_date}. "
                      f"Falling back to master table.")
        result = _build_response_from_master(session, entity_type, entity_id)

    # DEPRECATED (2025-11-21): Campaign hooks system removed
    # Use promotion_campaigns table via discount_service.py for all promotions
    result['campaign_applied'] = False
    result['campaign_info'] = None

    return result


def _build_response_from_config(config: EntityPricingTaxConfig, entity_type: str) -> Dict:
    """
    Build standardized response dict from config record.

    Internal helper function - not meant to be called directly.
    """
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

    # Add entity-specific pricing fields
    if entity_type == 'medicine':
        base_response.update({
            'mrp': config.mrp,
            'pack_mrp': config.pack_mrp,
            'pack_purchase_price': config.pack_purchase_price,
            'units_per_pack': config.units_per_pack,
            'unit_price': config.unit_price,
            'selling_price': config.selling_price,
            'cost_price': config.cost_price,
            'applicable_price': config.mrp or config.selling_price or config.pack_mrp
        })
    elif entity_type == 'service':
        base_response.update({
            'price': config.service_price,
            'applicable_price': config.service_price
        })
    elif entity_type == 'package':
        base_response.update({
            'price': config.package_price,
            'applicable_price': config.package_price
        })

    return base_response


def _build_response_from_master(session: Session, entity_type: str, entity_id: str) -> Dict:
    """
    Build standardized response dict from master table (fallback).

    Internal helper function - not meant to be called directly.
    """
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
                'applicable_price': entity.mrp or entity.selling_price,

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
                'applicable_price': entity.price,

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
                'applicable_price': entity.price,

                # Metadata
                'source': 'master_table',
                'config_id': None
            }

    # No data found anywhere - return defaults
    logger.error(f"No pricing/tax data found for {entity_type} {entity_id} in config or master table")
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
    pack_purchase_price: Optional[Decimal] = None,
    units_per_pack: Optional[Decimal] = None,
    unit_price: Optional[Decimal] = None,
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
    gst_inclusive: Optional[bool] = None,
    # Documentation params
    change_type: str = 'both',  # 'price_change', 'gst_change', 'both', 'initial'
    manufacturer_notification: Optional[str] = None,
    manufacturer_notification_date: Optional[date] = None,
    price_revision_reason: Optional[str] = None,
    gst_notification_number: Optional[str] = None,
    gst_notification_date: Optional[date] = None,
    change_reason: Optional[str] = None,
    remarks: Optional[str] = None
) -> EntityPricingTaxConfig:
    """
    Add a new pricing/tax configuration change.
    Automatically closes the previous config's effective period.

    This function is used when:
    - Government changes GST rate (with notification)
    - Manufacturer changes MRP (with notification)
    - Both change simultaneously

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: 'medicine', 'service', or 'package'
        entity_id: UUID of the entity
        effective_from: Date from which new rates are effective
        current_user_id: User making the change
        ... (pricing and GST parameters)
        change_type: Type of change ('price_change', 'gst_change', 'both', 'initial')

    Returns:
        Created EntityPricingTaxConfig record

    Example:
        >>> # GST rate increase from 12% to 18%
        >>> add_pricing_tax_change(
        ...     session, hospital_id, 'medicine', medicine_id,
        ...     effective_from=date(2025, 4, 1),
        ...     gst_rate=Decimal('18'),
        ...     gst_notification_number='No. 01/2025-Central Tax (Rate)',
        ...     change_type='gst_change'
        ... )
    """

    # Validate entity_type
    if entity_type not in ['medicine', 'service', 'package']:
        raise ValueError(f"Invalid entity_type: {entity_type}")

    # Auto-calculate GST component rates if only total rate provided
    if gst_rate is not None and cgst_rate is None:
        cgst_rate = gst_rate / 2
        sgst_rate = gst_rate / 2
        igst_rate = gst_rate
        logger.info(f"Auto-calculated GST components: CGST={cgst_rate}%, SGST={sgst_rate}%, IGST={igst_rate}%")

    entity_id_column = f"{entity_type}_id"

    # Step 1: Close previous config (if exists)
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
        logger.info(f"Closed previous config {previous_config.config_id}: "
                   f"effective_to={previous_config.effective_to}")

    # Step 2: Create new config
    new_config = EntityPricingTaxConfig(
        hospital_id=hospital_id,
        **{entity_id_column: entity_id},
        effective_from=effective_from,
        effective_to=None,  # Open-ended
        # Pricing
        mrp=mrp,
        pack_mrp=pack_mrp,
        pack_purchase_price=pack_purchase_price,
        units_per_pack=units_per_pack,
        unit_price=unit_price,
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
        gst_inclusive=gst_inclusive,
        # Documentation
        change_type=change_type,
        manufacturer_notification=manufacturer_notification,
        manufacturer_notification_date=manufacturer_notification_date,
        price_revision_reason=price_revision_reason,
        gst_notification_number=gst_notification_number,
        gst_notification_date=gst_notification_date,
        change_reason=change_reason,
        remarks=remarks,
        created_by=current_user_id
    )

    session.add(new_config)
    session.flush()

    logger.info(f"Created new pricing/tax config: {new_config.config_id}, "
               f"effective_from={effective_from}, change_type={change_type}")

    return new_config


def get_config_history(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str,
    limit: Optional[int] = None
) -> List[EntityPricingTaxConfig]:
    """
    Get complete pricing and tax change history for an entity.

    Useful for:
    - Audit trail
    - Understanding price/rate evolution
    - Compliance reporting

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: 'medicine', 'service', or 'package'
        entity_id: UUID of the entity
        limit: Optional limit on number of records

    Returns:
        List of EntityPricingTaxConfig records ordered by effective_from desc

    Example:
        >>> history = get_config_history(session, hospital_id, 'medicine', medicine_id)
        >>> for config in history:
        ...     print(f"{config.effective_from}: MRP={config.mrp}, GST={config.gst_rate}%")
    """
    entity_id_column = f"{entity_type}_id"

    query = session.query(EntityPricingTaxConfig).filter(
        and_(
            EntityPricingTaxConfig.hospital_id == hospital_id,
            getattr(EntityPricingTaxConfig, entity_id_column) == entity_id,
            EntityPricingTaxConfig.is_deleted == False
        )
    ).order_by(EntityPricingTaxConfig.effective_from.desc())

    if limit:
        query = query.limit(limit)

    return query.all()


def get_current_config(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str
) -> Optional[EntityPricingTaxConfig]:
    """
    Get the currently effective config for an entity (as of today).

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: 'medicine', 'service', or 'package'
        entity_id: UUID of the entity

    Returns:
        EntityPricingTaxConfig record or None if no current config exists

    Example:
        >>> current = get_current_config(session, hospital_id, 'medicine', medicine_id)
        >>> if current:
        ...     print(f"Current GST: {current.gst_rate}%")
    """
    today = date.today()
    pricing_tax = get_applicable_pricing_and_tax(
        session, hospital_id, entity_type, entity_id, today
    )

    if pricing_tax.get('config_id'):
        return session.query(EntityPricingTaxConfig).filter_by(
            config_id=pricing_tax['config_id']
        ).first()

    return None


def get_rate_changes_in_period(
    session: Session,
    hospital_id: str,
    start_date: date,
    end_date: date,
    entity_type: Optional[str] = None
) -> List[EntityPricingTaxConfig]:
    """
    Get all rate changes that became effective within a date range.

    Useful for:
    - Compliance reporting
    - Impact analysis
    - Rate change notifications

    Args:
        session: Database session
        hospital_id: Hospital UUID
        start_date: Start of period
        end_date: End of period
        entity_type: Optional filter by entity type

    Returns:
        List of EntityPricingTaxConfig records

    Example:
        >>> # Get all GST changes in Q1 2025
        >>> changes = get_rate_changes_in_period(
        ...     session, hospital_id,
        ...     date(2025, 1, 1), date(2025, 3, 31)
        ... )
    """
    query = session.query(EntityPricingTaxConfig).filter(
        and_(
            EntityPricingTaxConfig.hospital_id == hospital_id,
            EntityPricingTaxConfig.effective_from >= start_date,
            EntityPricingTaxConfig.effective_from <= end_date,
            EntityPricingTaxConfig.is_deleted == False
        )
    )

    if entity_type:
        entity_id_column = f"{entity_type}_id"
        query = query.filter(getattr(EntityPricingTaxConfig, entity_id_column) != None)

    return query.order_by(EntityPricingTaxConfig.effective_from).all()
