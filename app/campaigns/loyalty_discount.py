"""
Loyalty Discount Campaign

Discount based on patient's purchase history or loyalty tier.

Example hook_config:
{
    "loyalty_tiers": {
        "silver": {"min_purchases": 5, "discount_percentage": 5},
        "gold": {"min_purchases": 10, "discount_percentage": 10},
        "platinum": {"min_purchases": 25, "discount_percentage": 15}
    },
    "lookback_months": 6
}

Note: This example requires patient purchase history lookup.
In production, you'd query patient_invoices to get purchase count.

Author: Claude Code
Date: 2025-11-17
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, Any


def apply_discount(
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    hook_config: Dict[str, Any],
    context: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Apply loyalty-based discount.

    Args:
        entity_id: Medicine/Service/Package UUID
        base_price: Base price before discount
        applicable_date: Date for pricing
        hook_config: Campaign configuration with loyalty tiers
        context: Must include 'patient_id' and optionally 'purchase_count'

    Returns:
        Discount information if applicable, None otherwise
    """
    # Get patient ID from context
    patient_id = context.get('patient_id')

    if not patient_id:
        # No patient context, no loyalty discount
        return None

    # Get purchase count (in real implementation, this would query database)
    # For this example, we expect it in context
    purchase_count = context.get('purchase_count', 0)

    if purchase_count == 0:
        return None

    # Get loyalty tiers
    loyalty_tiers = hook_config.get('loyalty_tiers', {})

    # Determine applicable tier (highest tier that patient qualifies for)
    applicable_tier = None
    tier_name = None
    max_discount = Decimal('0')

    for name, tier_config in loyalty_tiers.items():
        min_purchases = tier_config.get('min_purchases', 0)
        discount_pct = Decimal(str(tier_config.get('discount_percentage', 0)))

        if purchase_count >= min_purchases and discount_pct > max_discount:
            applicable_tier = tier_config
            tier_name = name
            max_discount = discount_pct

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
        'message': f'Loyalty discount ({tier_name}): {discount_percentage}% off',
        'metadata': {
            'campaign_type': 'loyalty_discount',
            'loyalty_tier': tier_name,
            'patient_id': patient_id,
            'purchase_count': purchase_count
        }
    }


# Helper function for integration (example)
def get_patient_purchase_count(session, patient_id: str, lookback_months: int = 6) -> int:
    """
    Get patient's purchase count in last N months.

    This is a helper function that would be called BEFORE calling the campaign hook,
    to populate the context with purchase_count.

    Example usage in invoice creation:
        from app.campaigns.loyalty_discount import get_patient_purchase_count

        purchase_count = get_patient_purchase_count(session, patient_id, 6)
        context = {
            'patient_id': patient_id,
            'purchase_count': purchase_count,
            'quantity': quantity
        }
    """
    from app.models.transaction import PatientInvoice
    from datetime import datetime, timedelta

    cutoff_date = datetime.now() - timedelta(days=lookback_months * 30)

    count = session.query(PatientInvoice).filter(
        PatientInvoice.patient_id == patient_id,
        PatientInvoice.invoice_date >= cutoff_date,
        PatientInvoice.payment_status == 'paid'
    ).count()

    return count
