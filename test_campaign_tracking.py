"""
Test Campaign Tracking on Invoice Creation
Created: Nov 21, 2025
Tests that promotions are tracked on invoices correctly
"""

import sys
import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, 'C:/Users/vinod/AppData/Local/Programs/Skinspire Repository/Skinspire_v2')

from app.services.billing_service import create_invoice

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

def test_campaign_tracking_on_invoice():
    """Test: Campaign tracking when creating invoice with Buy X Get Y promotion"""
    print_section("TEST: Campaign Tracking on Invoice Creation")

    session = Session()
    try:
        # Get test data
        hospital = session.execute(text("SELECT hospital_id FROM hospitals LIMIT 1")).fetchone()
        branch = session.execute(text("SELECT branch_id FROM branches LIMIT 1")).fetchone()
        patient = session.execute(text("SELECT patient_id FROM patients LIMIT 1")).fetchone()

        if not all([hospital, branch, patient]):
            print_result("Get test data", False, "Missing hospital, branch, or patient")
            return False

        hospital_id = uuid.UUID(str(hospital[0]))
        branch_id = uuid.UUID(str(branch[0]))
        patient_id = uuid.UUID(str(patient[0]))

        # Service IDs
        botox_service_id = '6b308d3a-7233-4396-8da1-c6d0391acb1c'  # Rs. 4500
        consultation_service_id = 'd19643ed-0017-413a-8838-49aa793755ab'  # Rs. 500

        # Build line items (Botox + Consultation = triggers Buy X Get Y)
        line_items = [
            {
                'item_type': 'Service',
                'item_id': botox_service_id,
                'item_name': 'Botox Injection',
                'unit_price': 4500.00,
                'quantity': 1
            },
            {
                'item_type': 'Service',
                'item_id': consultation_service_id,
                'item_name': 'General Consultation',
                'unit_price': 500.00,
                'quantity': 1
            }
        ]

        print("Creating invoice with:")
        print(f"  - Botox Injection (Rs.4500) - Trigger item")
        print(f"  - General Consultation (Rs.500) - Reward item")
        print("")

        # Create invoice
        result = create_invoice(
            hospital_id=hospital_id,
            branch_id=branch_id,
            patient_id=patient_id,
            invoice_date=datetime.now(),
            line_items=line_items,
            notes="Test invoice for campaign tracking",
            current_user_id="test_user",
            session=session
        )

        print_result("Invoice created", True, f"Invoice number: {result.get('invoice_number')}")

        # Get the created invoice
        invoice_id = result.get('invoices', [{}])[0].get('invoice_id') if result.get('invoices') else None

        if not invoice_id:
            print_result("Get invoice ID", False, "Could not get invoice ID from result")
            return False

        # Check campaigns_applied field
        invoice_query = text("""
            SELECT
                invoice_number,
                total_discount,
                campaigns_applied
            FROM invoice_header
            WHERE invoice_id = :invoice_id
        """)

        invoice = session.execute(invoice_query, {'invoice_id': invoice_id}).fetchone()

        if not invoice:
            print_result("Fetch invoice", False, "Invoice not found in database")
            return False

        print(f"\nInvoice Details:")
        print(f"  Invoice Number: {invoice[0]}")
        print(f"  Total Discount: Rs.{invoice[1]}")
        print(f"  Campaigns Applied: {invoice[2]}")

        campaigns_applied = invoice[2]
        passed = True

        # Verify campaigns_applied is populated
        if not campaigns_applied:
            print_result("campaigns_applied populated", False, "Field is NULL")
            passed = False
        else:
            print_result("campaigns_applied populated", True)

            # Verify structure
            if 'applied_promotions' in campaigns_applied:
                promotions = campaigns_applied['applied_promotions']
                print_result("JSON structure valid", True, f"{len(promotions)} promotion(s)")

                if len(promotions) > 0:
                    promo = promotions[0]
                    print(f"\nPromotion Details:")
                    print(f"  Campaign Name: {promo.get('campaign_name')}")
                    print(f"  Campaign Code: {promo.get('campaign_code')}")
                    print(f"  Promotion Type: {promo.get('promotion_type')}")
                    print(f"  Items Affected: {len(promo.get('items_affected', []))}")
                    print(f"  Total Discount: Rs.{promo.get('total_discount')}")

                    if promo.get('campaign_code') == 'PREMIUM_CONSULT':
                        print_result("Correct promotion applied", True)
                    else:
                        print_result("Correct promotion applied", False,
                                    f"Expected PREMIUM_CONSULT, got {promo.get('campaign_code')}")
                        passed = False
                else:
                    print_result("Promotion found", False, "No promotions in array")
                    passed = False
            else:
                print_result("JSON structure valid", False, "Missing 'applied_promotions' key")
                passed = False

        # Check promotion_usage_log
        usage_log_query = text("""
            SELECT
                pul.campaign_id,
                pc.campaign_name,
                pul.discount_amount,
                pul.used_at
            FROM promotion_usage_log pul
            JOIN promotion_campaigns pc ON pul.campaign_id = pc.campaign_id
            WHERE pul.invoice_id = :invoice_id
        """)

        usage_logs = session.execute(usage_log_query, {'invoice_id': invoice_id}).fetchall()

        if len(usage_logs) > 0:
            print_result("Usage log created", True, f"{len(usage_logs)} record(s)")
            for log in usage_logs:
                print(f"  - {log[1]}: Rs.{log[2]} at {log[3]}")
        else:
            print_result("Usage log created", False, "No usage log entries found")
            passed = False

        # Check promotion current_uses increment
        promo_query = text("""
            SELECT campaign_name, current_uses, max_uses
            FROM promotion_campaigns
            WHERE campaign_code = 'PREMIUM_CONSULT'
        """)

        promo = session.execute(promo_query).fetchone()

        if promo:
            print(f"\nPromotion Counter:")
            print(f"  Campaign: {promo[0]}")
            print(f"  Current Uses: {promo[1] or 0}")
            print(f"  Max Uses: {promo[2] or 'Unlimited'}")

            if promo[1] and promo[1] > 0:
                print_result("Promotion counter incremented", True)
            else:
                print_result("Promotion counter incremented", False, "Counter not incremented")
                passed = False
        else:
            print_result("Promotion found", False, "PREMIUM_CONSULT promotion not found")
            passed = False

        # Rollback to avoid cluttering the database with test data
        session.rollback()
        print("\n[Note: Transaction rolled back - test data not saved]")

        return passed

    except Exception as e:
        print_result("Test execution", False, f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()

def main():
    print("\n" + "="*80)
    print("  CAMPAIGN TRACKING TEST SUITE")
    print("  Nov 21, 2025")
    print("="*80)

    result = test_campaign_tracking_on_invoice()

    # Summary
    print_section("TEST SUMMARY")
    if result:
        print("[PASS] Campaign tracking test passed")
        print("\nVerified:")
        print("  - campaigns_applied JSONB field populated")
        print("  - promotion_usage_log entries created")
        print("  - promotion_campaigns.current_uses incremented")
    else:
        print("[FAIL] Campaign tracking test failed")
        print("\nCheck errors above for details")

    print('='*80 + "\n")

if __name__ == "__main__":
    main()
