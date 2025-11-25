"""Check promotion hospital_id"""
from app import create_app, db
from app.models.master import PromotionCampaign

app = create_app()

with app.app_context():
    promo = db.session.query(PromotionCampaign).filter_by(
        campaign_name='Test Promotion 2025'
    ).first()

    if promo:
        print(f"Promotion hospital_id: {promo.hospital_id}")
        print(f"Expected hospital_id: 4ef72e18-e65d-4766-b9eb-0308c42485ca")
        print(f"Match: {str(promo.hospital_id) == '4ef72e18-e65d-4766-b9eb-0308c42485ca'}")
