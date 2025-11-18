"""
Percentage Discount Campaign

Simple percentage discount campaign with optional constraints:
- Minimum purchase amount
- Maximum discount amount
- Excluded categories

Example hook_config:
{
    "discount_percentage": 20,
    "min_purchase_amount": 500,
    "max_discount_amount": 1000,
    "excluded_medicine_ids": ["uuid1", "uuid2"]
}

Author: Claude Code
Date: 2025-11-17
"""

from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any


def apply_discount(
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    hook_config: Dict[str, Any],
    context: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Apply percentage discount campaign.

    Args:
        entity_id: Medicine/Service/Package UUID
        base_price: Base price before discount
        applicable_date: Date for pricing
        hook_config: Campaign configuration
        context: Additional context (quantity, etc.)

    Returns:
        Discount information if applicable, None otherwise
    """
    # Get configuration
    discount_percentage = Decimal(str(hook_config.get('discount_percentage', 0)))
    min_purchase_amount = Decimal(str(hook_config.get('min_purchase_amount', 0)))
    max_discount_amount = Decimal(str(hook_config.get('max_discount_amount', 0)))
    excluded_ids = hook_config.get('excluded_medicine_ids', [])

    # Validate discount percentage
    if discount_percentage <= 0 or discount_percentage > 100:
        return None

    # Check if entity is excluded
    if entity_id in excluded_ids:
        return None

    # Check minimum purchase amount
    quantity = Decimal(str(context.get('quantity', 1)))
    total_before_discount = base_price * quantity

    if min_purchase_amount > 0 and total_before_discount < min_purchase_amount:
        return None

    # Calculate discount
    discount_amount = base_price * (discount_percentage / Decimal('100'))

    # Apply maximum discount cap (per unit)
    if max_discount_amount > 0:
        max_discount_per_unit = max_discount_amount / quantity
        discount_amount = min(discount_amount, max_discount_per_unit)

    # Calculate adjusted price
    adjusted_price = base_price - discount_amount

    # Ensure price doesn't go negative
    if adjusted_price < 0:
        adjusted_price = Decimal('0')
        discount_amount = base_price

    return {
        'adjusted_price': adjusted_price,
        'discount_amount': discount_amount,
        'discount_percentage': discount_percentage,
        'message': f'{discount_percentage}% discount applied',
        'metadata': {
            'campaign_type': 'percentage_discount',
            'quantity': int(quantity),
            'total_discount': float(discount_amount * quantity)
        }
    }
