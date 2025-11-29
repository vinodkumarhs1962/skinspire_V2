file_path = r'app/services/discount_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix: Compare automatic and manual promo codes, pick the MAX
old_promo_logic = """        # 1. PROMOTION/CAMPAIGN DISCOUNT
        promotion_discount = DiscountService.calculate_promotion_discount(
            session, hospital_id, patient_id, item_type, item_id, unit_price, quantity, invoice_date,
            invoice_items=invoice_items
        )

        # If no automatic promotion found but manual promo code provided, use it
        if not promotion_discount and manual_promo_code:
            logger.info(f"Using manual promo code: {manual_promo_code.get('campaign_code')}")
            original_price = unit_price * quantity
            promo_discount_type = manual_promo_code.get('discount_type', 'percentage')
            promo_discount_value = Decimal(str(manual_promo_code.get('discount_value', 0)))

            if promo_discount_type == 'percentage':
                discount_amount = (original_price * promo_discount_value) / 100
                discount_percent = promo_discount_value
            else:
                discount_amount = promo_discount_value
                discount_percent = (discount_amount / original_price * 100) if original_price > 0 else Decimal('0')

            promotion_discount = DiscountCalculationResult(
                discount_type='promotion',
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                final_price=original_price - discount_amount,
                original_price=original_price,
                promotion_id=manual_promo_code.get('campaign_id'),
                metadata={
                    'campaign_id': manual_promo_code.get('campaign_id'),
                    'campaign_code': manual_promo_code.get('campaign_code'),
                    'campaign_name': manual_promo_code.get('campaign_code', 'Manual Promo'),
                    'discount_type': promo_discount_type,
                    'manual_entry': True
                }
            )

        if promotion_discount:"""

new_promo_logic = """        # 1. PROMOTION/CAMPAIGN DISCOUNT
        # First, check for automatic promotions
        auto_promotion_discount = DiscountService.calculate_promotion_discount(
            session, hospital_id, patient_id, item_type, item_id, unit_price, quantity, invoice_date,
            invoice_items=invoice_items
        )

        # Then, calculate manual promo code discount if provided
        manual_promotion_discount = None
        if manual_promo_code:
            logger.info(f"Processing manual promo code: {manual_promo_code.get('campaign_code')}")
            original_price = unit_price * quantity
            promo_discount_type = manual_promo_code.get('discount_type', 'percentage')
            promo_discount_value = Decimal(str(manual_promo_code.get('discount_value', 0)))

            if promo_discount_type == 'percentage':
                discount_amount = (original_price * promo_discount_value) / 100
                discount_percent = promo_discount_value
            else:
                discount_amount = promo_discount_value
                discount_percent = (discount_amount / original_price * 100) if original_price > 0 else Decimal('0')

            manual_promotion_discount = DiscountCalculationResult(
                discount_type='promotion',
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                final_price=original_price - discount_amount,
                original_price=original_price,
                promotion_id=manual_promo_code.get('campaign_id'),
                metadata={
                    'campaign_id': manual_promo_code.get('campaign_id'),
                    'campaign_code': manual_promo_code.get('campaign_code'),
                    'campaign_name': manual_promo_code.get('campaign_code', 'Manual Promo'),
                    'discount_type': promo_discount_type,
                    'manual_entry': True
                }
            )

        # Pick the MAX discount between automatic and manual
        promotion_discount = None
        if auto_promotion_discount and manual_promotion_discount:
            if auto_promotion_discount.discount_percent >= manual_promotion_discount.discount_percent:
                promotion_discount = auto_promotion_discount
                logger.info(f"Using automatic promotion ({auto_promotion_discount.discount_percent}%) over manual ({manual_promotion_discount.discount_percent}%)")
            else:
                promotion_discount = manual_promotion_discount
                logger.info(f"Using manual promotion ({manual_promotion_discount.discount_percent}%) over automatic ({auto_promotion_discount.discount_percent}%)")
        elif auto_promotion_discount:
            promotion_discount = auto_promotion_discount
            logger.info(f"Using automatic promotion: {auto_promotion_discount.discount_percent}%")
        elif manual_promotion_discount:
            promotion_discount = manual_promotion_discount
            logger.info(f"Using manual promotion: {manual_promotion_discount.discount_percent}%")

        if promotion_discount:"""

if old_promo_logic in content:
    content = content.replace(old_promo_logic, new_promo_logic)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fixed promo logic to pick MAX between automatic and manual')
else:
    print('Pattern not found')

print('Done!')
