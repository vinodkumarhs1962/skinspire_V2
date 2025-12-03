"""
End-to-End Test for Buy X Get Y Free Promotion
Tests the complete flow from campaign creation to invoice application
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from decimal import Decimal
import json

from app.services.database_service import get_db_session
from app.models.master import Hospital, Service, PromotionCampaign
from app.services.discount_service import DiscountService

def test_buy_x_get_y():
    """
    Test Scenario: Buy 5 Advanced Facial, Get 1 Basic Cleanup FREE

    Steps:
    1. Get hospital and services
    2. Create a Buy X Get Y campaign
    3. Simulate invoice with 5 Advanced Facial
    4. Verify the discount calculation returns free Basic Cleanup
    """

    print("=" * 60)
    print("BUY X GET Y END-TO-END TEST")
    print("=" * 60)

    with get_db_session() as session:
        # Step 1: Get hospital with active services (Skinspire Clinic)
        hospital = session.query(Hospital).filter(
            Hospital.name == 'Skinspire Clinic'
        ).first()
        if not hospital:
            # Fallback to any hospital
            hospital = session.query(Hospital).first()
        if not hospital:
            print("ERROR: No hospital found in database")
            return False

        hospital_id = str(hospital.hospital_id)
        print(f"\n1. Using Hospital: {hospital.name} ({hospital_id})")

        # Step 2: Get two services for the test
        services = session.query(Service).filter(
            Service.hospital_id == hospital.hospital_id,
            Service.is_active == True
        ).limit(2).all()

        if len(services) < 2:
            print("ERROR: Need at least 2 active services for this test")
            return False

        trigger_service = services[0]  # Service that triggers the promotion
        reward_service = services[1]   # Service given for free

        print(f"\n2. Test Services:")
        print(f"   Trigger: {trigger_service.service_name} (ID: {trigger_service.service_id})")
        print(f"   Reward:  {reward_service.service_name} (ID: {reward_service.service_id})")

        # Step 3: Create Buy X Get Y Campaign
        campaign_code = "TEST_BXGY_001"

        # Check if test campaign already exists
        existing = session.query(PromotionCampaign).filter(
            PromotionCampaign.campaign_code == campaign_code,
            PromotionCampaign.hospital_id == hospital.hospital_id
        ).first()

        if existing:
            print(f"\n3. Test campaign already exists, using it: {existing.campaign_name}")
            campaign_id = str(existing.campaign_id)
            campaign_name = existing.campaign_name
            promotion_rules = existing.promotion_rules
        else:
            # Create new campaign
            campaign = PromotionCampaign(
                hospital_id=hospital.hospital_id,
                campaign_code=campaign_code,
                campaign_name="Buy 5 Get 1 Free Test",
                description="Buy 5 of trigger service, get 1 reward service free",
                promotion_type="buy_x_get_y",
                discount_type="percentage",
                discount_value=100,  # 100% off = FREE
                start_date=date.today() - timedelta(days=1),
                end_date=date.today() + timedelta(days=30),
                is_active=True,
                status="approved",
                auto_apply=True,
                applies_to="services",
                promotion_rules={
                    "trigger": {
                        "type": "item_purchase",
                        "conditions": {
                            "item_type": "service",
                            "item_ids": [str(trigger_service.service_id)],
                            "min_quantity": 5
                        }
                    },
                    "reward": {
                        "items": [{
                            "item_type": "service",
                            "item_id": str(reward_service.service_id),
                            "item_name": reward_service.service_name,
                            "quantity": 1,
                            "discount_percent": 100
                        }]
                    }
                }
            )
            session.add(campaign)
            session.flush()  # Get the ID without closing transaction
            campaign_id = str(campaign.campaign_id)
            campaign_name = campaign.campaign_name
            promotion_rules = campaign.promotion_rules
            print(f"\n3. Created test campaign: {campaign_name}")

        print(f"   Campaign ID: {campaign_id}")
        print(f"   Promotion Rules: {json.dumps(promotion_rules, indent=2)}")

        # Step 4: Test with invoice items (quantity = 5, should trigger)
        print("\n4. Testing with 5 units (should trigger):")

        invoice_items = [{
            'item_id': str(trigger_service.service_id),
            'item_type': 'Service',
            'item_name': trigger_service.service_name,
            'unit_price': float(trigger_service.price or 1000),
            'quantity': 5
        }]

        print(f"   Invoice items: {invoice_items}")

        # Call the discount service to check Buy X Get Y
        result = DiscountService.calculate_promotion_discount(
            session=session,
            hospital_id=hospital_id,
            patient_id=None,
            item_type='Service',
            item_id=str(reward_service.service_id),  # Check if reward service gets discount
            unit_price=Decimal(str(reward_service.price or 500)),
            quantity=1,
            invoice_items=invoice_items
        )

        if result:
            print(f"\n   RESULT: Discount found!")
            print(f"   - Discount Type: {result.discount_type}")
            print(f"   - Discount %: {result.discount_percent}")
            print(f"   - Discount Amount: {result.discount_amount}")
            print(f"   - Final Price: {result.final_price}")
            print(f"   - Metadata: {result.metadata}")

            if result.metadata.get('promotion_type') == 'buy_x_get_y':
                print("\n   SUCCESS: Buy X Get Y promotion correctly applied!")
                success_trigger = True
            else:
                print(f"\n   WARNING: Discount found but not from Buy X Get Y (got: {result.metadata.get('promotion_type')})")
                print(f"   Campaign: {result.metadata.get('campaign_name')} ({result.metadata.get('campaign_code')})")
                success_trigger = False
        else:
            print("\n   FAILED: No discount returned for reward service")
            success_trigger = False

        # Step 5: Test with quantity = 3 (should NOT trigger)
        print("\n5. Testing with 3 units (should NOT trigger):")

        invoice_items_no_trigger = [{
            'item_id': str(trigger_service.service_id),
            'item_type': 'Service',
            'item_name': trigger_service.service_name,
            'unit_price': float(trigger_service.price or 1000),
            'quantity': 3  # Less than min_quantity of 5
        }]

        result_no_trigger = DiscountService.calculate_promotion_discount(
            session=session,
            hospital_id=hospital_id,
            patient_id=None,
            item_type='Service',
            item_id=str(reward_service.service_id),
            unit_price=Decimal(str(reward_service.price or 500)),
            quantity=1,
            invoice_items=invoice_items_no_trigger
        )

        if result_no_trigger and result_no_trigger.metadata.get('promotion_type') == 'buy_x_get_y':
            print("   FAILED: Buy X Get Y should NOT have triggered with qty=3")
            success_no_trigger = False
        else:
            print("   SUCCESS: Buy X Get Y correctly NOT triggered with qty=3")
            success_no_trigger = True

        # Step 6: Test API endpoint
        print("\n6. Testing API endpoint:")
        from flask import Flask
        from app.api.routes.discount_api import discount_bp

        app = Flask(__name__)
        app.register_blueprint(discount_bp)

        with app.test_client() as client:
            response = client.get(f'/api/discount/buy-x-get-y/active?hospital_id={hospital_id}')
            if response.status_code == 200:
                data = response.get_json()
                print(f"   API Response: {data['count']} active campaigns found")

                # Check if our test campaign is in the list
                found = any(c['campaign_code'] == campaign_code for c in data['campaigns'])
                if found:
                    print(f"   Test campaign found in API response")
                else:
                    print(f"   Test campaign not found in API response")
            else:
                print(f"   API returned status {response.status_code}")

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Trigger test (qty=5):     {'PASS' if success_trigger else 'FAIL'}")
        print(f"No-trigger test (qty=3):  {'PASS' if success_no_trigger else 'FAIL'}")
        print("=" * 60)

        return success_trigger and success_no_trigger


if __name__ == "__main__":
    success = test_buy_x_get_y()
    sys.exit(0 if success else 1)
