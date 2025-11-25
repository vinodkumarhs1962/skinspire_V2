"""
Test Buy X Get Y Promotion Logic
Created: Nov 21, 2025
Tests the Buy X Get Y Free promotion implementation
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

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)

def print_result(test_name, passed, details=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"     {details}")

def test_buy_x_get_y_trigger_met():
    """Test: High-value service purchase triggers free consultation"""
    print_section("TEST 1: Buy X Get Y - Trigger Met (Botox Rs.4500 -> Free Consultation)")

    session = Session()
    try:
        # Get hospital and patient
        hospital = session.execute(text("SELECT hospital_id FROM hospitals LIMIT 1")).fetchone()
        patient = session.execute(text("SELECT patient_id FROM patients LIMIT 1")).fetchone()

        if not hospital or not patient:
            print_result("Get test data", False, "Missing hospital or patient")
            return False

        hospital_id = str(hospital[0])
        patient_id = str(patient[0])

        # Service IDs from database
        botox_service_id = '6b308d3a-7233-4396-8da1-c6d0391acb1c'  # Rs. 4500
        consultation_service_id = 'd19643ed-0017-413a-8838-49aa793755ab'  # Rs. 500

        # Simulate invoice with high-value service + consultation
        invoice_items = [
            {
                'item_type': 'Service',
                'item_id': botox_service_id,
                'service_id': botox_service_id,
                'unit_price': Decimal('4500.00'),
                'quantity': 1
            },
            {
                'item_type': 'Service',
                'item_id': consultation_service_id,
                'service_id': consultation_service_id,
                'unit_price': Decimal('500.00'),
                'quantity': 1
            }
        ]

        # Calculate promotion discount for consultation
        result = DiscountService.calculate_promotion_discount(
            session=session,
            hospital_id=hospital_id,
            patient_id=patient_id,
            item_type='Service',
            item_id=consultation_service_id,
            unit_price=Decimal('500.00'),
            quantity=1,
            invoice_date=date.today(),
            invoice_items=invoice_items
        )

        if result is None:
            print_result("Trigger recognition", False, "No promotion discount found")
            return False

        print(f"     Discount Type: {result.discount_type}")
        print(f"     Discount %: {result.discount_percent}%")
        print(f"     Discount Amount: Rs.{result.discount_amount}")
        print(f"     Original Price: Rs.{result.original_price}")
        print(f"     Final Price: Rs.{result.final_price}")
        print(f"     Metadata: {result.metadata}")

        # Verify 100% discount
        passed = (
            result.discount_type == 'promotion' and
            result.discount_percent == Decimal('100') and
            result.discount_amount == Decimal('500.00') and
            result.final_price == Decimal('0.00')
        )

        print_result("Free consultation applied", passed,
                    f"Expected 100% off, got {result.discount_percent}%")

        return passed

    except Exception as e:
        print_result("Test execution", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def test_buy_x_get_y_trigger_not_met():
    """Test: Low-value service does NOT trigger free consultation"""
    print_section("TEST 2: Buy X Get Y - Trigger NOT Met (Basic Facial Rs.800 -> Consultation)")

    session = Session()
    try:
        # Get hospital and patient
        hospital = session.execute(text("SELECT hospital_id FROM hospitals LIMIT 1")).fetchone()
        patient = session.execute(text("SELECT patient_id FROM patients LIMIT 1")).fetchone()

        if not hospital or not patient:
            print_result("Get test data", False, "Missing hospital or patient")
            return False

        hospital_id = str(hospital[0])
        patient_id = str(patient[0])

        # Service IDs from database
        basic_facial_id = '894b033f-64f7-42a4-b052-6a9d2a14e13a'  # Rs. 800
        consultation_service_id = 'd19643ed-0017-413a-8838-49aa793755ab'  # Rs. 500

        # Simulate invoice with LOW-value service + consultation
        invoice_items = [
            {
                'item_type': 'Service',
                'item_id': basic_facial_id,
                'service_id': basic_facial_id,
                'unit_price': Decimal('800.00'),
                'quantity': 1
            },
            {
                'item_type': 'Service',
                'item_id': consultation_service_id,
                'service_id': consultation_service_id,
                'unit_price': Decimal('500.00'),
                'quantity': 1
            }
        ]

        # Calculate promotion discount for consultation
        result = DiscountService.calculate_promotion_discount(
            session=session,
            hospital_id=hospital_id,
            patient_id=patient_id,
            item_type='Service',
            item_id=consultation_service_id,
            unit_price=Decimal('500.00'),
            quantity=1,
            invoice_date=date.today(),
            invoice_items=invoice_items
        )

        if result is None:
            print_result("Trigger correctly NOT fired", True,
                        "No promotion (Rs.800 < Rs.3000 threshold)")
            return True
        else:
            print_result("Trigger correctly NOT fired", False,
                        f"Unexpected discount found: {result.discount_percent}%")
            return False

    except Exception as e:
        print_result("Test execution", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def test_buy_x_get_y_multiple_rewards():
    """Test: High-value service with multiple consultations"""
    print_section("TEST 3: Buy X Get Y - Multiple Reward Items")

    session = Session()
    try:
        # Get hospital and patient
        hospital = session.execute(text("SELECT hospital_id FROM hospitals LIMIT 1")).fetchone()
        patient = session.execute(text("SELECT patient_id FROM patients LIMIT 1")).fetchone()

        if not hospital or not patient:
            print_result("Get test data", False, "Missing hospital or patient")
            return False

        hospital_id = str(hospital[0])
        patient_id = str(patient[0])

        # Service IDs from database
        botox_service_id = '6b308d3a-7233-4396-8da1-c6d0391acb1c'  # Rs. 4500
        consultation_service_id = 'd19643ed-0017-413a-8838-49aa793755ab'  # Rs. 500

        # Simulate invoice with Botox + 2 consultations
        invoice_items = [
            {
                'item_type': 'Service',
                'item_id': botox_service_id,
                'service_id': botox_service_id,
                'unit_price': Decimal('4500.00'),
                'quantity': 1
            },
            {
                'item_type': 'Service',
                'item_id': consultation_service_id,
                'service_id': consultation_service_id,
                'unit_price': Decimal('500.00'),
                'quantity': 2  # Two consultations
            }
        ]

        # Calculate promotion discount for 2 consultations
        result = DiscountService.calculate_promotion_discount(
            session=session,
            hospital_id=hospital_id,
            patient_id=patient_id,
            item_type='Service',
            item_id=consultation_service_id,
            unit_price=Decimal('500.00'),
            quantity=2,
            invoice_date=date.today(),
            invoice_items=invoice_items
        )

        if result is None:
            print_result("Promotion applied", False, "No promotion discount found")
            return False

        print(f"     Discount %: {result.discount_percent}%")
        print(f"     Discount Amount: Rs.{result.discount_amount}")
        print(f"     Original Price: Rs.{result.original_price}")
        print(f"     Final Price: Rs.{result.final_price}")

        # Current implementation applies discount to full quantity
        # Expected: 100% off on Rs.1000 (2 consultations)
        passed = (
            result.discount_percent == Decimal('100') and
            result.discount_amount == Decimal('1000.00')
        )

        print_result("Multiple items discount", passed,
                    f"Expected Rs.1000 discount, got Rs.{result.discount_amount}")

        return passed

    except Exception as e:
        print_result("Test execution", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def test_multi_discount_integration():
    """Test: Buy X Get Y vs other discount types (priority)"""
    print_section("TEST 4: Multi-Discount Priority - Promotion vs Bulk")

    session = Session()
    try:
        # Get hospital and patient
        hospital = session.execute(text("SELECT hospital_id FROM hospitals LIMIT 1")).fetchone()
        patient = session.execute(text("SELECT patient_id FROM patients LIMIT 1")).fetchone()

        if not hospital or not patient:
            print_result("Get test data", False, "Missing hospital or patient")
            return False

        hospital_id = str(hospital[0])
        patient_id = str(patient[0])

        # Service IDs
        botox_service_id = '6b308d3a-7233-4396-8da1-c6d0391acb1c'  # Rs. 4500
        consultation_service_id = 'd19643ed-0017-413a-8838-49aa793755ab'  # Rs. 500

        # Simulate invoice
        invoice_items = [
            {
                'item_type': 'Service',
                'item_id': botox_service_id,
                'service_id': botox_service_id,
                'unit_price': Decimal('4500.00'),
                'quantity': 5  # Bulk quantity
            },
            {
                'item_type': 'Service',
                'item_id': consultation_service_id,
                'service_id': consultation_service_id,
                'unit_price': Decimal('500.00'),
                'quantity': 1
            }
        ]

        # Get best discount (should prioritize promotion over bulk)
        result = DiscountService.get_best_discount_multi(
            session=session,
            hospital_id=hospital_id,
            patient_id=patient_id,
            item_type='Service',
            item_id=consultation_service_id,
            unit_price=Decimal('500.00'),
            quantity=1,
            total_item_count=5,
            invoice_date=date.today(),
            invoice_items=invoice_items
        )

        print(f"     Discount Type: {result.discount_type}")
        print(f"     Discount %: {result.discount_percent}%")
        print(f"     Priority Level: {result.metadata.get('priority', 'N/A')}")

        # Promotion should win (priority 1)
        passed = result.discount_type == 'promotion'

        print_result("Promotion priority over bulk", passed,
                    f"Expected 'promotion', got '{result.discount_type}'")

        return passed

    except Exception as e:
        print_result("Test execution", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def main():
    print("\n" + "="*80)
    print("  BUY X GET Y PROMOTION - TEST SUITE")
    print("  Nov 21, 2025")
    print("="*80)

    results = []

    # Run tests
    results.append(("Trigger Met - Free Consultation", test_buy_x_get_y_trigger_met()))
    results.append(("Trigger NOT Met - No Discount", test_buy_x_get_y_trigger_not_met()))
    results.append(("Multiple Reward Items", test_buy_x_get_y_multiple_rewards()))
    results.append(("Multi-Discount Priority", test_multi_discount_integration()))

    # Summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print(f"\n{'='*80}")
    print(f"  RESULTS: {passed}/{total} tests passed")
    if passed == total:
        print("  Status: ALL TESTS PASSED")
    else:
        print(f"  Status: {total - passed} test(s) FAILED")
    print('='*80 + "\n")

if __name__ == "__main__":
    main()
