"""
Campaign Plugins - Hospital-Specific Promotional Campaign Implementations

This package contains example campaign implementations that demonstrate
how to create custom pricing campaigns using the campaign hook system.

Each campaign module should implement a function with this signature:

    def campaign_function(
        entity_id: str,
        base_price: Decimal,
        applicable_date: date,
        hook_config: Dict,
        context: Dict
    ) -> Optional[Dict]:
        '''
        Args:
            entity_id: Medicine/Service/Package UUID
            base_price: Base price before campaign
            applicable_date: Date for which to calculate price
            hook_config: Campaign configuration from database
            context: Additional context (patient_id, quantity, etc.)

        Returns:
            Dict with discount info if applicable, None otherwise:
            {
                'adjusted_price': Decimal,
                'discount_amount': Decimal,
                'discount_percentage': Decimal (optional),
                'message': str (optional),
                'metadata': Dict (optional)
            }
        '''
        pass

Author: Claude Code
Date: 2025-11-17
"""

__all__ = [
    'percentage_discount',
    'volume_discount',
    'loyalty_discount',
    'seasonal_campaign'
]
