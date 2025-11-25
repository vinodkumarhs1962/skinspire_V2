"""
Test API response format for stacked discounts
"""
from app import create_app
from app.services.database_service import get_db_session
from app.services.discount_service import DiscountService
import json

app = create_app()

with app.app_context():
    print("=" * 70)
    print("TESTING API RESPONSE FORMAT")
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

    with get_db_session() as session:
        discounted_items = DiscountService.apply_discounts_to_invoice_items_multi(
            session=session,
            hospital_id=hospital_id,
            patient_id=patient_id,
            line_items=line_items,
            respect_max_discount=True
        )

        print("\nAPI Response (JSON format):")
        print("=" * 70)
        print(json.dumps(discounted_items, indent=2, default=str))

        print("\n\nKey Fields Frontend Needs:")
        print("=" * 70)
        for item in discounted_items:
            print(f"\ndiscount_type: {item.get('discount_type')}")
            print(f"discount_percent: {item.get('discount_percent')}")
            print(f"discount_amount: {item.get('discount_amount')}")
            print(f"card_type_id: {item.get('card_type_id')}")

            if 'discount_metadata' in item:
                print(f"\nMetadata:")
                metadata = item['discount_metadata']
                if 'bulk_percent' in metadata:
                    print(f"  - bulk_percent: {metadata['bulk_percent']}")
                if 'loyalty_percent' in metadata:
                    print(f"  - loyalty_percent: {metadata['loyalty_percent']}")
                if 'selection_reason' in metadata:
                    print(f"  - selection_reason: {metadata['selection_reason']}")
