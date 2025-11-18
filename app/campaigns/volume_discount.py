"""
Volume Discount Campaign

Tiered discount based on purchase quantity:
- Buy 10-20 units: 5% off
- Buy 21-50 units: 10% off
- Buy 51+ units: 15% off

Example hook_config:
{
    "tiers": [
        {"min_quantity": 10, "max_quantity": 20, "discount_percentage": 5},
        {"min_quantity": 21, "max_quantity": 50, "discount_percentage": 10},
        {"min_quantity": 51, "max_quantity": null, "discount_percentage": 15}
    ]
}

Author: Claude Code
Date: 2025-11-17
"""

from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any, List


def apply_discount(
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    hook_config: Dict[str, Any],
    context: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Apply volume-based discount.

    Args:
        entity_id: Medicine/Service/Package UUID
        base_price: Base price before discount
        applicable_date: Date for pricing
        hook_config: Campaign configuration with tiers
        context: Must include 'quantity'

    Returns:
        Discount information if applicable, None otherwise
    """
    # Get quantity from context
    quantity = int(context.get('quantity', 1))

    if quantity <= 0:
        return None

    # Get tiers configuration
    tiers: List[Dict] = hook_config.get('tiers', [])

    if not tiers:
        return None

    # Find applicable tier
    applicable_tier = None
    for tier in tiers:
        min_qty = tier.get('min_quantity', 0)
        max_qty = tier.get('max_quantity')  # Can be None for open-ended

        if quantity >= min_qty:
            if max_qty is None or quantity <= max_qty:
                applicable_tier = tier
                break

    # No tier applies
    if not applicable_tier:
        return None

    # Calculate discount
    discount_percentage = Decimal(str(applicable_tier['discount_percentage']))
    discount_amount = base_price * (discount_percentage / Decimal('100'))
    adjusted_price = base_price - discount_amount

    return {
        'adjusted_price': adjusted_price,
        'discount_amount': discount_amount,
        'discount_percentage': discount_percentage,
        'message': f'Volume discount: {discount_percentage}% off for {quantity} units',
        'metadata': {
            'campaign_type': 'volume_discount',
            'quantity': quantity,
            'tier_min': applicable_tier.get('min_quantity'),
            'tier_max': applicable_tier.get('max_quantity'),
            'total_discount': float(discount_amount * quantity)
        }
    }
