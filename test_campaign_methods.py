"""
Test Campaign Tracking Methods in Isolation
Created: Nov 21, 2025
Tests build_campaigns_applied_json and record_promotion_usage methods
"""

import sys
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, 'C:/Users/vinod/AppData/Local/Programs/Skinspire Repository/Skinspire_v2')

from app.services.discount_service import DiscountService

# Database connection
DATABASE_URL = "postgresql://skinspire_admin:Skinspire123$@localhost/skinspire_dev"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def test_build_campaigns_applied_json():
    """Test: build_campaigns_applied_json method"""
    print("\n" + "="*80)
    print("TEST 1: build_campaigns_applied_json()")
    print("="*80)

    session = Session()
    try:
        # Get promotion ID
        promo = session.execute(text("""
            SELECT campaign_id FROM promotion_campaigns
            WHERE campaign_code = 'PREMIUM_CONSULT'
        """)).fetchone()

        if not promo:
            print("[FAIL] PREMIUM_CONSULT promotion not found")
            return False

        promotion_id = str(promo[0])

        # Simulate line items with promotion discount
        line_items = [
            {
                'item_type': 'Service',
                'item_id': '6b308d3a-7233-4396-8da1-c6d0391acb1c',
                'item_name': 'Botox Injection',
                'unit_price': 4500.00,
                'quantity': 1,
                'discount_type': 'standard',  # Botox doesn't get discounted
                'discount_percent': 0,
                'discount_amount': 0
            },
            {
                'item_type': 'Service',
                'item_id': 'd19643ed-0017-413a-8838-49aa793755ab',
                'item_name': 'General Consultation',
                'unit_price': 500.00,
                'quantity': 1,
                'discount_type': 'promotion',  # Consultation gets promotion discount
                'discount_percent': 100,
                'discount_amount': 500.00,
                'promotion_id': promotion_id
            }
        ]

        # Call method
        result = DiscountService.build_campaigns_applied_json(
            session=session,
            line_items=line_items
        )

        # Verify result
        if not result:
            print("[FAIL] Method returned None")
            return False

        print("[PASS] Method returned data")
        print(f"  Structure: {result.keys()}")

        if 'applied_promotions' not in result:
            print("[FAIL] Missing 'applied_promotions' key")
            return False

        print("[PASS] Has 'applied_promotions' key")

        promotions = result['applied_promotions']
        if len(promotions) == 0:
            print("[FAIL] No promotions in list")
            return False

        print(f"[PASS] Found {len(promotions)} promotion(s)")

        promo_info = promotions[0]
        print(f"\nPromotion Info:")
        print(f"  Campaign Name: {promo_info.get('campaign_name')}")
        print(f"  Campaign Code: {promo_info.get('campaign_code')}")
        print(f"  Promotion Type: {promo_info.get('promotion_type')}")
        print(f"  Items Affected: {promo_info.get('items_affected')}")
        print(f"  Total Discount: Rs.{promo_info.get('total_discount')}")

        if promo_info.get('campaign_code') == 'PREMIUM_CONSULT':
            print("[PASS] Correct campaign identified")
        else:
            print(f"[FAIL] Wrong campaign: {promo_info.get('campaign_code')}")
            return False

        if promo_info.get('total_discount') == 500.0:
            print("[PASS] Correct discount amount")
        else:
            print(f"[FAIL] Wrong discount: {promo_info.get('total_discount')}")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def test_record_promotion_usage():
    """Test: record_promotion_usage method"""
    print("\n" + "="*80)
    print("TEST 2: record_promotion_usage()")
    print("="*80)

    session = Session()
    try:
        # Get test data
        hospital = session.execute(text("SELECT hospital_id FROM hospitals LIMIT 1")).fetchone()
        patient = session.execute(text("SELECT patient_id FROM patients LIMIT 1")).fetchone()
        promo = session.execute(text("""
            SELECT campaign_id, current_uses FROM promotion_campaigns
            WHERE campaign_code = 'PREMIUM_CONSULT'
        """)).fetchone()

        if not all([hospital, patient, promo]):
            print("[FAIL] Missing test data")
            return False

        patient_id = str(patient[0])
        promotion_id = str(promo[0])
        initial_uses = promo[1] or 0

        print(f"Initial promotion uses: {initial_uses}")

        # Create fake invoice ID
        fake_invoice_id = '00000000-0000-0000-0000-000000000001'

        # Simulate line items
        line_items = [
            {
                'item_id': 'd19643ed-0017-413a-8838-49aa793755ab',
                'discount_type': 'promotion',
                'discount_amount': 500.00,
                'promotion_id': promotion_id
            }
        ]

        # Call method
        DiscountService.record_promotion_usage(
            session=session,
            hospital_id=str(hospital[0]),
            invoice_id=fake_invoice_id,
            line_items=line_items,
            patient_id=patient_id,
            invoice_date=date.today()
        )

        print("[PASS] Method executed without errors")

        # Flush to make changes visible within transaction
        session.flush()

        # Check if usage log was created
        log_count = session.execute(text("""
            SELECT COUNT(*) FROM promotion_usage_log
            WHERE invoice_id = :invoice_id
        """), {'invoice_id': fake_invoice_id}).scalar()

        if log_count > 0:
            print(f"[PASS] Usage log created ({log_count} record)")
        else:
            print("[FAIL] No usage log created")
            session.rollback()
            return False

        # Check if counter was incremented (before rollback)
        new_uses = session.execute(text("""
            SELECT current_uses FROM promotion_campaigns
            WHERE campaign_id = :campaign_id
        """), {'campaign_id': promotion_id}).scalar()

        if new_uses == initial_uses + 1:
            print(f"[PASS] Counter incremented ({initial_uses} -> {new_uses})")
        else:
            print(f"[FAIL] Counter not incremented correctly ({initial_uses} -> {new_uses})")
            session.rollback()
            return False

        # Rollback test data
        session.rollback()
        print("\n[Note: Transaction rolled back - test data not saved]")

        return True

    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()

def main():
    print("\n" + "="*80)
    print("  CAMPAIGN METHODS TEST SUITE")
    print("  Nov 21, 2025")
    print("="*80)

    results = []
    results.append(("build_campaigns_applied_json", test_build_campaigns_applied_json()))
    results.append(("record_promotion_usage", test_record_promotion_usage()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\nRESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("Status: ALL TESTS PASSED")
    else:
        print(f"Status: {total - passed} test(s) FAILED")

    print('='*80 + "\n")

if __name__ == "__main__":
    main()
