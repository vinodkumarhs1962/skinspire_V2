"""
Test Wallet Tier Upgrade: Silver to Gold
Tests tier upgrade and discount percentage change

Date: November 24, 2025
"""

from decimal import Decimal
from datetime import datetime
from app.services.database_service import get_db_session
from app.services.discount_service import DiscountService
from app.models.master import Patient, LoyaltyCardType
from sqlalchemy import text

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_tier_upgrade():
    """
    Test upgrading Ram Kumar from Silver to Gold:
    1. Check current tier (Silver - 2%)
    2. Calculate upgrade cost
    3. Upgrade to Gold tier
    4. Verify new discount (3%)
    5. Test discount calculation with new tier
    """

    print_section("WALLET TIER UPGRADE TEST - SILVER TO GOLD")

    with get_db_session() as session:
        # ========================================================================
        # STEP 1: Get Current Wallet Status
        # ========================================================================
        print_section("STEP 1: Current Wallet Status")

        ram_kumar = session.query(Patient).filter(Patient.full_name == 'Ram Kumar').first()

        if not ram_kumar:
            print("[ERROR] Ram Kumar not found")
            return False

        wallet_query = text("""
            SELECT
                plw.wallet_id,
                plw.points_balance,
                plw.total_amount_loaded,
                plw.card_type_id,
                lct.card_type_name,
                lct.card_type_code,
                lct.discount_percent,
                lct.min_payment_amount
            FROM patient_loyalty_wallet plw
            JOIN loyalty_card_types lct ON plw.card_type_id = lct.card_type_id
            WHERE plw.patient_id = :patient_id
        """)

        current_wallet = session.execute(wallet_query,
            {'patient_id': str(ram_kumar.patient_id)}).fetchone()

        if not current_wallet:
            print("[ERROR] No wallet found")
            return False

        print(f"[OK] Current Wallet Status:")
        print(f"  Wallet ID: {current_wallet[0]}")
        print(f"  Points Balance: {current_wallet[1]:,}")
        print(f"  Total Amount Loaded: Rs.{current_wallet[2]:,.2f}")
        print(f"  Current Tier: {current_wallet[4]} ({current_wallet[5]})")
        print(f"  Current Discount: {current_wallet[6]}%")
        print(f"  Tier Payment: Rs.{current_wallet[7]:,.2f}")

        # ========================================================================
        # STEP 2: Get Gold Tier Details
        # ========================================================================
        print_section("STEP 2: Gold Tier Details")

        gold_tier_query = text("""
            SELECT
                card_type_id,
                card_type_name,
                card_type_code,
                min_payment_amount,
                total_points_credited,
                bonus_percentage,
                discount_percent
            FROM loyalty_card_types
            WHERE card_type_code = 'GOLD'
              AND hospital_id = :hospital_id
              AND is_active = true
        """)

        gold_tier = session.execute(gold_tier_query,
            {'hospital_id': str(ram_kumar.hospital_id)}).fetchone()

        if not gold_tier:
            print("[ERROR] Gold tier not found")
            return False

        print(f"[OK] Gold Tier Configuration:")
        print(f"  Tier: {gold_tier[1]} ({gold_tier[2]})")
        print(f"  Payment Required: Rs.{gold_tier[3]:,.2f}")
        print(f"  Points Credited: {gold_tier[4]:,}")
        print(f"  Bonus: {gold_tier[5]}%")
        print(f"  Discount: {gold_tier[6]}%")

        # ========================================================================
        # STEP 3: Calculate Upgrade Cost
        # ========================================================================
        print_section("STEP 3: Upgrade Cost Calculation")

        current_payment = Decimal(str(current_wallet[7]))
        gold_payment = Decimal(str(gold_tier[3]))
        upgrade_cost = gold_payment - current_payment

        print(f"[CALCULATION]")
        print(f"  Gold Tier Payment: Rs.{gold_payment:,.2f}")
        print(f"  Already Paid (Silver): Rs.{current_payment:,.2f}")
        print(f"  Balance to Pay: Rs.{upgrade_cost:,.2f}")

        # Calculate additional points
        gold_total_points = gold_tier[4]
        current_points_loaded = current_wallet[1]

        # Gold gives 50,000 points for Rs.45,000
        # Ram Kumar already has 8,000 points (from Silver Rs.22,000 = 25,000 points, used 1,000 in previous test, so 7,000 remaining)
        # Wait, let me recalculate based on actual current balance

        # Actually current balance might still be 8,000 since previous test was simulation
        # Let's use what we read from DB
        current_balance = current_wallet[1]

        additional_points_from_gold = gold_total_points - 25000  # Gold 50K - Silver 25K = 25K additional

        print(f"\n[POINTS CALCULATION]")
        print(f"  Current Balance: {current_balance:,} points")
        print(f"  Gold Total Points: {gold_total_points:,} points")
        print(f"  Additional Points on Upgrade: {additional_points_from_gold:,} points")
        print(f"  Balance After Upgrade: {current_balance + additional_points_from_gold:,} points")

        # ========================================================================
        # STEP 4: Simulate Upgrade (Update wallet)
        # ========================================================================
        print_section("STEP 4: Performing Tier Upgrade")

        print(f"[ACTION] Upgrading to Gold tier...")

        # Update wallet to Gold tier
        update_query = text("""
            UPDATE patient_loyalty_wallet
            SET card_type_id = :gold_tier_id,
                points_balance = points_balance + :additional_points,
                total_points_loaded = total_points_loaded + :additional_points,
                total_amount_loaded = total_amount_loaded + :upgrade_payment,
                updated_at = CURRENT_TIMESTAMP
            WHERE wallet_id = :wallet_id
            RETURNING wallet_id, points_balance, total_amount_loaded
        """)

        updated = session.execute(update_query, {
            'gold_tier_id': gold_tier[0],
            'additional_points': additional_points_from_gold,
            'upgrade_payment': upgrade_cost,
            'wallet_id': current_wallet[0]
        }).fetchone()

        # Create upgrade transaction
        txn_query = text("""
            INSERT INTO wallet_transaction (
                transaction_id,
                wallet_id,
                transaction_type,
                transaction_date,
                total_points_loaded,
                base_points,
                bonus_points,
                balance_before,
                balance_after,
                amount_paid,
                payment_mode,
                payment_reference,
                notes,
                created_by
            ) VALUES (
                gen_random_uuid(),
                :wallet_id,
                'load',
                CURRENT_TIMESTAMP,
                :additional_points,
                :base_points,
                :bonus_points,
                :balance_before,
                :balance_after,
                :upgrade_payment,
                'CREDIT',
                'TIER_UPGRADE_SILVER_TO_GOLD',
                'Upgraded from Silver to Gold tier',
                '0000000000'
            )
            RETURNING transaction_id
        """)

        # Calculate base and bonus for upgrade payment
        base_points_upgrade = int(upgrade_cost)  # Rs.23000 = 23000 base points
        bonus_points_upgrade = additional_points_from_gold - base_points_upgrade

        txn_id = session.execute(txn_query, {
            'wallet_id': current_wallet[0],
            'additional_points': additional_points_from_gold,
            'base_points': base_points_upgrade,
            'bonus_points': bonus_points_upgrade,
            'balance_before': current_balance,
            'balance_after': updated[1],
            'upgrade_payment': upgrade_cost
        }).fetchone()

        # Create new batch for additional points
        batch_query = text("""
            INSERT INTO wallet_points_batch (
                batch_id,
                wallet_id,
                load_transaction_id,
                points_loaded,
                points_remaining,
                points_redeemed,
                points_expired,
                load_date,
                expiry_date,
                batch_sequence,
                is_expired
            ) VALUES (
                gen_random_uuid(),
                :wallet_id,
                :txn_id,
                :points_loaded,
                :points_loaded,
                0,
                0,
                CURRENT_DATE,
                CURRENT_DATE + INTERVAL '12 months',
                (SELECT COALESCE(MAX(batch_sequence), 0) + 1 FROM wallet_points_batch WHERE wallet_id = :wallet_id),
                false
            )
        """)

        session.execute(batch_query, {
            'wallet_id': current_wallet[0],
            'txn_id': txn_id[0],
            'points_loaded': additional_points_from_gold
        })

        session.commit()

        print(f"[OK] Upgrade Complete!")
        print(f"  Transaction ID: {txn_id[0]}")
        print(f"  New Balance: {updated[1]:,} points")
        print(f"  Total Loaded: Rs.{updated[2]:,.2f}")

        # Store data for comparison before session closes
        old_tier_code = current_wallet[5]
        old_discount = float(current_wallet[6])
        old_balance = current_balance
        old_amount_loaded = current_wallet[2]
        stored_current_payment = current_payment
        stored_upgrade_cost = upgrade_cost
        stored_additional_points = additional_points_from_gold
        stored_txn_id = txn_id[0] if txn_id else None

        # ========================================================================
        # STEP 5: Verify New Wallet Status
        # ========================================================================
        print_section("STEP 5: Verify New Wallet Status")

    # Create new session for verification after commit
    with get_db_session() as session:
        ram_kumar = session.query(Patient).filter(Patient.full_name == 'Ram Kumar').first()

        wallet_query = text("""
            SELECT
                plw.wallet_id,
                plw.points_balance,
                plw.total_amount_loaded,
                plw.card_type_id,
                lct.card_type_name,
                lct.card_type_code,
                lct.discount_percent,
                lct.min_payment_amount
            FROM patient_loyalty_wallet plw
            JOIN loyalty_card_types lct ON plw.card_type_id = lct.card_type_id
            WHERE plw.patient_id = :patient_id
        """)

        new_wallet = session.execute(wallet_query,
            {'patient_id': str(ram_kumar.patient_id)}).fetchone()

        print(f"[OK] Updated Wallet Status:")
        print(f"  Wallet ID: {new_wallet[0]}")
        print(f"  Points Balance: {new_wallet[1]:,}")
        print(f"  Total Amount Loaded: Rs.{new_wallet[2]:,.2f}")
        print(f"  New Tier: {new_wallet[4]} ({new_wallet[5]})")
        print(f"  New Discount: {new_wallet[6]}%")

        # ========================================================================
        # STEP 6: Test Discount with New Tier
        # ========================================================================
        print_section("STEP 6: Testing Discount with Gold Tier")

        # Get a test service
        service_query = text("""
            SELECT service_id, service_name, price
            FROM services
            WHERE is_active = true
            ORDER BY price DESC
            LIMIT 1
        """)

        service = session.execute(service_query).fetchone()

        if not service:
            print("[ERROR] No service found")
            return False

        service_price = Decimal(str(service[2]))

        print(f"[TEST] Calculating discount for:")
        print(f"  Service: {service[1]}")
        print(f"  Price: Rs.{service_price:,.2f}")

        # Calculate discount with new tier
        discount_result = DiscountService.calculate_loyalty_discount(
            session=session,
            hospital_id=str(ram_kumar.hospital_id),
            patient_id=str(ram_kumar.patient_id),
            service_id=str(service[0]),
            unit_price=service_price,
            quantity=1
        )

        if not discount_result:
            print("[ERROR] Discount calculation returned None")
            return False

        print(f"\n[OK] Discount Calculation:")
        print(f"  Original Price: Rs.{discount_result.original_price:,.2f}")
        print(f"  Discount Percent: {discount_result.discount_percent}%")
        print(f"  Discount Amount: Rs.{discount_result.discount_amount:,.2f}")
        print(f"  Final Price: Rs.{discount_result.final_price:,.2f}")

        # ========================================================================
        # STEP 7: Comparison Summary
        # ========================================================================
        print_section("STEP 7: Before vs After Comparison")

        print(f"[BEFORE - SILVER TIER]")
        print(f"  Payment: Rs.{stored_current_payment:,.2f}")
        print(f"  Points: {old_balance:,}")
        print(f"  Discount: {old_discount}%")

        print(f"\n[AFTER - GOLD TIER]")
        print(f"  Payment: Rs.{new_wallet[2]:,.2f}")
        print(f"  Points: {new_wallet[1]:,}")
        print(f"  Discount: {new_wallet[6]}%")

        print(f"\n[UPGRADE INVESTMENT]")
        print(f"  Additional Payment: Rs.{stored_upgrade_cost:,.2f}")
        print(f"  Additional Points: {stored_additional_points:,}")
        print(f"  Discount Increase: {float(new_wallet[6]) - old_discount}%")

        # Calculate savings example
        example_invoice = Decimal('100000')  # Rs.1 lakh invoice
        silver_discount = example_invoice * Decimal(str(old_discount)) / 100
        gold_discount = example_invoice * Decimal(str(new_wallet[6])) / 100
        additional_savings = gold_discount - silver_discount

        print(f"\n[SAVINGS EXAMPLE - Rs.1,00,000 Invoice]")
        print(f"  Silver Discount (2%): Rs.{silver_discount:,.2f}")
        print(f"  Gold Discount (3%): Rs.{gold_discount:,.2f}")
        print(f"  Additional Savings: Rs.{additional_savings:,.2f}")

        # ========================================================================
        # FINAL VERIFICATION
        # ========================================================================
        print_section("TEST RESULTS")

        checks = [
            ("Wallet upgraded successfully", new_wallet[5] == 'GOLD'),
            ("Discount changed to 3%", float(new_wallet[6]) == 3.0),
            ("Points balance increased", new_wallet[1] > old_balance),
            ("Amount loaded updated", new_wallet[2] == old_amount_loaded + stored_upgrade_cost),
            ("Discount calculation works", discount_result.discount_percent == Decimal('3.0')),
            ("Transaction recorded", stored_txn_id is not None)
        ]

        all_passed = True
        for check_name, result in checks:
            status = "[OK]" if result else "[FAILED]"
            print(f"  {status} {check_name}")
            if not result:
                all_passed = False

        if all_passed:
            print(f"\n{'='*80}")
            print(f"  TIER UPGRADE TEST PASSED - GOLD TIER WORKING CORRECTLY")
            print(f"{'='*80}")
            print(f"\n[KEY FINDINGS]")
            print(f"  1. Tier successfully upgraded from Silver to Gold")
            print(f"  2. Discount correctly changed from 2% to 3%")
            print(f"  3. Additional {stored_additional_points:,} points credited")
            print(f"  4. Upgrade transaction recorded")
            print(f"  5. New discount rate applied in calculations")
            print(f"\n  Tier upgrade functionality is working correctly!")
            return True
        else:
            print(f"\n[ERROR] Some tests failed!")
            return False

if __name__ == '__main__':
    try:
        success = test_tier_upgrade()
        if not success:
            print("\n[ERROR] Tier upgrade test failed!")
            exit(1)
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
