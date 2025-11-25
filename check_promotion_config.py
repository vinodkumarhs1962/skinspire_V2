"""
Diagnostic script to check promotion configuration
"""
import sys
from datetime import datetime
from app import create_app
from app.models.master import PromotionCampaign
from app import db

app = create_app()

with app.app_context():
    hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'

    print("\n" + "="*80)
    print("CHECKING PROMOTION CONFIGURATION")
    print("="*80)

    # Get all promotions for this hospital
    all_promotions = db.session.query(PromotionCampaign).filter_by(
        hospital_id=hospital_id
    ).order_by(PromotionCampaign.created_at.desc()).limit(5).all()

    print(f"\nTotal promotions found for hospital: {len(all_promotions)}")
    print("-"*80)

    today = datetime.now().date()

    for idx, promo in enumerate(all_promotions, 1):
        print(f"\n[{idx}] Promotion: {promo.campaign_name}")
        print(f"    ID: {promo.campaign_id}")
        print(f"    is_active: {promo.is_active}")
        print(f"    is_deleted: {promo.is_deleted}")
        print(f"    start_date: {promo.start_date}")
        print(f"    end_date: {promo.end_date}")
        print(f"    applies_to: {promo.applies_to}")
        print(f"    specific_items: {promo.specific_items}")
        print(f"    discount_type: {promo.discount_type}")
        print(f"    discount_value: {promo.discount_value}")
        print(f"    promotion_type: {promo.promotion_type}")
        print(f"    created_at: {promo.created_at}")

        # Check each filter condition
        print(f"\n    Filter Checks:")
        print(f"    ✓ hospital_id matches: {promo.hospital_id == hospital_id}")
        print(f"    {'✓' if promo.is_active else '✗'} is_active == True: {promo.is_active}")
        print(f"    {'✓' if not promo.is_deleted else '✗'} is_deleted == False: {not promo.is_deleted}")
        print(f"    {'✓' if promo.start_date <= today else '✗'} start_date <= today: {promo.start_date} <= {today} = {promo.start_date <= today}")
        print(f"    {'✓' if promo.end_date >= today else '✗'} end_date >= today: {promo.end_date} >= {today} = {promo.end_date >= today}")

        applies_to_check = promo.applies_to in ['all', 'services']
        print(f"    {'✓' if applies_to_check else '✗'} applies_to in ['all', 'services']: {promo.applies_to}")

        all_pass = (
            promo.hospital_id == hospital_id and
            promo.is_active and
            not promo.is_deleted and
            promo.start_date <= today and
            promo.end_date >= today and
            applies_to_check
        )

        print(f"\n    RESULT: {'✓ WOULD BE SELECTED' if all_pass else '✗ WOULD BE FILTERED OUT'}")
        print("-"*80)

    # Now check what the actual query would return
    print("\n" + "="*80)
    print("ACTUAL QUERY RESULT (as used in discount_service.py)")
    print("="*80)

    from sqlalchemy import and_, or_

    active_promotions = db.session.query(PromotionCampaign).filter(
        and_(
            PromotionCampaign.hospital_id == hospital_id,
            PromotionCampaign.is_active == True,
            PromotionCampaign.is_deleted == False,
            PromotionCampaign.start_date <= today,
            PromotionCampaign.end_date >= today,
            or_(
                PromotionCampaign.applies_to == 'all',
                PromotionCampaign.applies_to == 'services'
            )
        )
    ).all()

    print(f"\nPromotions that pass ALL filters: {len(active_promotions)}")

    if active_promotions:
        for promo in active_promotions:
            print(f"\n✓ {promo.campaign_name}")
            print(f"  Discount: {promo.discount_value}% {promo.discount_type}")
    else:
        print("\n✗ NO PROMOTIONS PASS THE FILTERS!")
        print("\nThis is why promotion discount is not appearing.")

    print("\n" + "="*80)
