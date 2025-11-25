"""
Direct test of discount stacking - bypasses API to test core logic
"""
import sys
from app import create_app
from app.services.database_service import get_db_session
from app.services.discount_service import DiscountService

app = create_app()

with app.app_context():
    print("=" * 70)
    print("TESTING DISCOUNT STACKING - DIRECT SERVICE CALL")
    print("=" * 70)

    hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'
    patient_id = 'c5f9c602-5350-4b93-8bae-b91a2451d74a'  # Ram Kumar
    service_id = '40b89b81-5528-401d-b54c-345515491db1'  # Advanced Facial

    line_items = [
        {
            'item_type': 'Service',
            'service_id': service_id,
            'item_id': service_id,
            'quantity': 5,
            'unit_price': 5000.00
        }
    ]

    print(f"\nTest Data:")
    print(f"  Patient: Ram Kumar")
    print(f"  Service: Advanced Facial")
    print(f"  Quantity: 5")
    print(f"  Unit Price: ₹5,000")
    print(f"  Total Before Discount: ₹25,000")

    with get_db_session() as session:
        print(f"\n{'='*70}")
        print("Applying Multi-Discount Method...")
        print(f"{'='*70}")

        discounted_items = DiscountService.apply_discounts_to_invoice_items_multi(
            session=session,
            hospital_id=hospital_id,
            patient_id=patient_id,
            line_items=line_items,
            respect_max_discount=True
        )

        print(f"\nResults:")
        print(f"{'='*70}")

        for idx, item in enumerate(discounted_items, 1):
            print(f"\nItem {idx}:")
            print(f"  Discount Type: {item.get('discount_type')}")
            print(f"  Discount Percent: {item.get('discount_percent')}%")
            print(f"  Discount Amount: ₹{item.get('discount_amount')}")
            print(f"  Final Price: ₹{item.get('final_price')}")
            print(f"  Card Type ID: {item.get('card_type_id')}")

            if 'discount_metadata' in item:
                metadata = item['discount_metadata']
                print(f"  Metadata:")
                for key, value in metadata.items():
                    print(f"    {key}: {value}")

        # Calculate totals
        total_original = sum(float(item.get('unit_price', 0)) * int(item.get('quantity', 1)) for item in discounted_items)
        total_discount = sum(float(item.get('discount_amount', 0)) for item in discounted_items)
        total_final = sum(float(item.get('final_price', 0)) for item in discounted_items)

        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Total Original Price: ₹{total_original:,.2f}")
        print(f"Total Discount: ₹{total_discount:,.2f}")
        print(f"Total Final Price: ₹{total_final:,.2f}")
        print(f"Effective Discount %: {(total_discount/total_original*100):.2f}%")

        print(f"\n{'='*70}")
        print("VERIFICATION")
        print(f"{'='*70}")

        expected_bulk = 0.15  # 15% bulk discount
        expected_loyalty = 0.05  # 5% loyalty discount
        expected_total = expected_bulk + expected_loyalty  # 20% when stacked

        actual_percent = (total_discount/total_original)

        print(f"Expected Discount: {expected_total*100}% (15% bulk + 5% loyalty)")
        print(f"Actual Discount: {actual_percent*100:.2f}%")

        if abs(actual_percent - expected_total) < 0.01:  # Allow 1% tolerance
            print(f"\n✅ SUCCESS: Discounts are stacking correctly!")
            print(f"   Bulk (15%) + Loyalty (5%) = {actual_percent*100:.2f}%")
        elif abs(actual_percent - expected_bulk) < 0.01:
            print(f"\n❌ FAILED: Only bulk discount applied (15%)")
            print(f"   Loyalty discount (5%) not stacking")
        elif abs(actual_percent - expected_loyalty) < 0.01:
            print(f"\n❌ FAILED: Only loyalty discount applied (5%)")
            print(f"   Bulk discount (15%) not stacking")
        else:
            print(f"\n⚠️  UNEXPECTED: Discount is {actual_percent*100:.2f}%")

        print(f"\n{'='*70}")
