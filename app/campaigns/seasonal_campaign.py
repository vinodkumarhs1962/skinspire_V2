"""
Seasonal Campaign (Diwali, Christmas, etc.)

Date-specific campaign with special discounts during festival periods.

Example hook_config:
{
    "festival_name": "Diwali 2025",
    "discount_percentage": 20,
    "min_purchase_amount": 1000,
    "max_discount_amount": 500,
    "bonus_message": "Happy Diwali! Enjoy special festive discounts"
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
    Apply seasonal/festival discount.

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
    festival_name = hook_config.get('festival_name', 'Seasonal Campaign')
    discount_percentage = Decimal(str(hook_config.get('discount_percentage', 0)))
    min_purchase_amount = Decimal(str(hook_config.get('min_purchase_amount', 0)))
    max_discount_amount = Decimal(str(hook_config.get('max_discount_amount', 0)))
    bonus_message = hook_config.get('bonus_message', '')

    # Validate discount
    if discount_percentage <= 0:
        return None

    # Get quantity
    quantity = Decimal(str(context.get('quantity', 1)))
    total_before_discount = base_price * quantity

    # Check minimum purchase amount
    if min_purchase_amount > 0 and total_before_discount < min_purchase_amount:
        return None

    # Calculate discount
    discount_amount = base_price * (discount_percentage / Decimal('100'))

    # Apply maximum discount cap
    if max_discount_amount > 0:
        max_discount_per_unit = max_discount_amount / quantity
        discount_amount = min(discount_amount, max_discount_per_unit)

    # Calculate adjusted price
    adjusted_price = base_price - discount_amount

    # Ensure non-negative
    if adjusted_price < 0:
        adjusted_price = Decimal('0')
        discount_amount = base_price

    # Build message
    message = f'{festival_name}: {discount_percentage}% discount'
    if bonus_message:
        message += f' - {bonus_message}'

    return {
        'adjusted_price': adjusted_price,
        'discount_amount': discount_amount,
        'discount_percentage': discount_percentage,
        'message': message,
        'metadata': {
            'campaign_type': 'seasonal_campaign',
            'festival_name': festival_name,
            'quantity': int(quantity),
            'total_discount': float(discount_amount * quantity)
        }
    }
