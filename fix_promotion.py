"""
Fix promotion by setting is_active to True
"""
from app import create_app, db
from app.models.master import PromotionCampaign

app = create_app()

with app.app_context():
    # Find the promotion
    promo = db.session.query(PromotionCampaign).filter_by(
        campaign_name='Test Promotion 2025',
        hospital_id='4ef72e18-e65d-4766-b9eb-0308c42485ca'
    ).first()

    if promo:
        print(f"\nFound promotion: {promo.campaign_name}")
        print(f"Current is_active: {promo.is_active}")

        # Update is_active to True
        promo.is_active = True
        db.session.commit()

        print(f"Updated is_active: {promo.is_active}")
        print("\n✅ PROMOTION IS NOW ACTIVE!")
        print("\nPromotion Details:")
        print(f"  - Name: {promo.campaign_name}")
        print(f"  - Discount: {promo.discount_value}% {promo.discount_type}")
        print(f"  - Applies to: {promo.applies_to}")
        print(f"  - Valid: {promo.start_date} to {promo.end_date}")
        print(f"  - Active: {promo.is_active}")
        print("\n🎉 The promotion should now apply to Advanced Facial service!")
    else:
        print("❌ Promotion not found")
