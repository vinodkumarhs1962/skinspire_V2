"""
Test script to verify discount system works with NEW wallet system
Date: November 24, 2025
"""

from decimal import Decimal
from app.services.database_service import get_db_session
from app.services.discount_service import DiscountService
from app.models.master import Patient
from sqlalchemy import text

def test_wallet_discount():
    """Test that Ram Kumar's wallet provides correct discount"""

    print("=" * 80)
    print("TESTING LOYALTY WALLET DISCOUNT SYSTEM")
    print("=" * 80)

    with get_db_session() as session:
        # Step 1: Get Ram Kumar's patient_id
        ram_kumar = session.query(Patient).filter(Patient.full_name == 'Ram Kumar').first()

        if not ram_kumar:
            print("[ERROR] Ram Kumar not found in patients table")
            return False

        print(f"\n[OK] Found patient: {ram_kumar.full_name} (ID: {ram_kumar.patient_id})")

        # Step 2: Verify wallet exists
        wallet_query = text("""
            SELECT
                plw.wallet_id,
                plw.points_balance,
                plw.wallet_status,
                lct.card_type_name,
                lct.discount_percent
            FROM patient_loyalty_wallet plw
            JOIN loyalty_card_types lct ON plw.card_type_id = lct.card_type_id
            WHERE plw.patient_id = :patient_id
        """)

        wallet_result = session.execute(wallet_query, {'patient_id': str(ram_kumar.patient_id)}).fetchone()

        if not wallet_result:
            print(f"[ERROR] ERROR: No wallet found for Ram Kumar")
            return False

        print(f"\n[OK] Wallet found:")
        print(f"  - Wallet ID: {wallet_result[0]}")
        print(f"  - Points Balance: {wallet_result[1]}")
        print(f"  - Status: {wallet_result[2]}")
        print(f"  - Tier: {wallet_result[3]}")
        print(f"  - Discount Percent: {wallet_result[4]}%")

        # Step 3: Get a test service
        service_query = text("""
            SELECT service_id, service_name, price
            FROM services
            WHERE is_active = true
            LIMIT 1
        """)

        service_result = session.execute(service_query).fetchone()

        if not service_result:
            print(f"[ERROR] ERROR: No active services found")
            return False

        service_id = service_result[0]
        service_name = service_result[1]
        service_rate = Decimal(str(service_result[2]))

        print(f"\n[OK] Test service: {service_name}")
        print(f"  - Service ID: {service_id}")
        print(f"  - Rate: Rs.{service_rate}")

        # Step 4: Test calculate_loyalty_discount function
        print(f"\n" + "=" * 80)
        print("TESTING DISCOUNT CALCULATION")
        print("=" * 80)

        discount_result = DiscountService.calculate_loyalty_discount(
            session=session,
            hospital_id=str(ram_kumar.hospital_id),
            patient_id=str(ram_kumar.patient_id),
            service_id=str(service_id),
            unit_price=service_rate,
            quantity=1
        )

        if discount_result is None:
            print(f"[ERROR] ERROR: Discount calculation returned None")
            print(f"   This means the wallet was not found or has no discount")
            return False

        print(f"\n[OK] Discount calculation successful!")
        print(f"  - Discount Type: {discount_result.discount_type}")
        print(f"  - Original Price: Rs.{discount_result.original_price}")
        print(f"  - Discount Percent: {discount_result.discount_percent}%")
        print(f"  - Discount Amount: Rs.{discount_result.discount_amount}")
        print(f"  - Final Price: Rs.{discount_result.final_price}")
        print(f"  - Metadata: {discount_result.metadata}")

        # Step 5: Verify discount percent matches tier
        expected_discount = float(wallet_result[4])  # discount_percent from wallet query
        actual_discount = float(discount_result.discount_percent)

        if abs(expected_discount - actual_discount) < 0.01:  # Allow for float precision
            print(f"\n[SUCCESS] SUCCESS: Discount percent matches tier ({expected_discount}%)")
        else:
            print(f"\n[ERROR] ERROR: Discount mismatch!")
            print(f"   Expected: {expected_discount}% (from tier)")
            print(f"   Actual: {actual_discount}% (from calculation)")
            return False

        # Step 6: Test calculate_loyalty_percentage_discount (for multi-item types)
        print(f"\n" + "=" * 80)
        print("TESTING MULTI-ITEM DISCOUNT CALCULATION")
        print("=" * 80)

        discount_result2 = DiscountService.calculate_loyalty_percentage_discount(
            session=session,
            hospital_id=str(ram_kumar.hospital_id),
            patient_id=str(ram_kumar.patient_id),
            item_type='Service',
            item_id=str(service_id),
            unit_price=service_rate,
            quantity=1
        )

        if discount_result2 is None:
            print(f"[OK] No item-specific loyalty discount (this is OK)")
        else:
            print(f"[OK] Item-specific discount calculation successful!")
            print(f"  - Discount Percent: {discount_result2.discount_percent}%")

        print(f"\n" + "=" * 80)
        print("ALL TESTS PASSED [SUCCESS]")
        print("=" * 80)
        print("\nSummary:")
        print(f"  [OK] Wallet migration successful")
        print(f"  [OK] Wallet query successful")
        print(f"  [OK] Discount calculation working")
        print(f"  [OK] Discount percent correct ({expected_discount}%)")
        print(f"\nThe NEW wallet system is fully integrated with the discount engine!")

        return True

if __name__ == '__main__':
    try:
        success = test_wallet_discount()
        if not success:
            print("\n[ERROR] Tests failed!")
            exit(1)
    except Exception as e:
        print(f"\n[ERROR] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
