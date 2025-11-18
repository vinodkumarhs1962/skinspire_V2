"""
Test script to verify patient payment data flow
"""
from app import create_app
from app.services.database_service import get_db_session
from sqlalchemy import text
import json

app = create_app()

with app.app_context():
    print("=" * 80)
    print("TESTING PATIENT PAYMENT DATA FLOW")
    print("=" * 80)

    with get_db_session() as session:
        # Test 1: Check view data
        print("\n1. RAW VIEW DATA:")
        print("-" * 80)
        result = session.execute(text("""
            SELECT payment_id, patient_name, patient_mrn, payment_method_primary, total_amount
            FROM v_patient_payment_receipts
            LIMIT 3
        """)).fetchall()

        for row in result:
            print(f"  PaymentID: {row[0]}")
            print(f"  PatientName: [{row[1]}]")
            print(f"  MRN: {row[2]}")
            print(f"  PaymentMethod: [{row[3]}]")
            print(f"  Amount: {row[4]}")
            print()

        # Test 2: Check configuration
        print("\n2. CONFIGURATION CHECK:")
        print("-" * 80)
        from app.config.entity_configurations import get_entity_config

        config = get_entity_config('patient_payments')

        # Find payment_method_primary field
        pm_field = None
        for field in config.fields:
            if field.name == 'payment_method_primary':
                pm_field = field
                break

        if pm_field:
            print(f"  Field Name: {pm_field.name}")
            print(f"  Label: {pm_field.label}")
            print(f"  Filterable: {pm_field.filterable}")
            print(f"  Filter Type: {pm_field.filter_type}")
            print(f"  Has Options: {bool(pm_field.options)}")
            if pm_field.options:
                print(f"  Number of Options: {len(pm_field.options)}")
                print(f"  First 3 Options: {pm_field.options[:3]}")
        else:
            print("  ❌ payment_method_primary field NOT FOUND in config!")

        # Find patient_name field
        pn_field = None
        for field in config.fields:
            if field.name == 'patient_name':
                pn_field = field
                break

        if pn_field:
            print(f"\n  Patient Name Field:")
            print(f"    Show in List: {pn_field.show_in_list}")
            print(f"    Field Type: {pn_field.field_type}")
            print(f"    Width: {pn_field.width}")

        # Test 3: Check service
        print("\n3. SERVICE OUTPUT:")
        print("-" * 80)
        from app.services.patient_payment_service import PatientPaymentService

        service = PatientPaymentService()
        result = service.search_data(
            filters={},
            hospital_id='ee18f62c-0607-400f-8b88-a5c58c5a82e8',
            branch_id=None,
            page=1,
            per_page=2
        )

        print(f"  Success: {result.get('success')}")
        print(f"  Total: {result.get('total')}")
        print(f"  Items count: {len(result.get('items', []))}")

        if result.get('success') and result.get('items'):
            for idx, item in enumerate(result['items'], 1):
                print(f"\n  Item {idx}:")
                print(f"    Patient Name: [{item.get('patient_name')}]")
                print(f"    Payment Method: [{item.get('payment_method_primary')}]")
                print(f"    Total Amount: {item.get('total_amount')}")
        else:
            print("  ❌ No items returned")
            if result.get('error'):
                print(f"  Error: {result.get('error')}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
