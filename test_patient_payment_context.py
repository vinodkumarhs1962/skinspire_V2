#!/usr/bin/env python
# Test script to verify patient payment context functions return correct structure

import sys
import uuid
from app.services.patient_payment_service import PatientPaymentService

# Test payment ID (you'll need to replace with actual ID from database)
test_payment_id = "db7b3a1b-2024-4566-8e55-b6b9d9cf8af5"  # Replace with real ID
test_hospital_id = "4ef72e18-e65d-4766-b9eb-0308c42485ca"  # Replace with real hospital ID

print("Testing PatientPaymentService context functions...")
print("=" * 80)

service = PatientPaymentService()

# Test 1: get_invoice_items_for_payment
print("\n1. Testing get_invoice_items_for_payment...")
try:
    result = service.get_invoice_items_for_payment(
        item_id=test_payment_id,
        hospital_id=test_hospital_id
    )
    print(f"   Result type: {type(result)}")
    print(f"   Has 'summary' key: {'summary' in result}")
    if 'summary' in result:
        print(f"   Summary type: {type(result['summary'])}")
        print(f"   Summary keys: {result['summary'].keys() if isinstance(result['summary'], dict) else 'Not a dict'}")
    print(f"   Result keys: {result.keys()}")
    print("   ✅ SUCCESS")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: get_payment_workflow_timeline
print("\n2. Testing get_payment_workflow_timeline...")
try:
    result = service.get_payment_workflow_timeline(
        item_id=test_payment_id,
        hospital_id=test_hospital_id
    )
    print(f"   Result type: {type(result)}")
    print(f"   Result keys: {result.keys()}")
    print("   ✅ SUCCESS")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: get_patient_payment_history
print("\n3. Testing get_patient_payment_history...")
try:
    result = service.get_patient_payment_history(
        item_id=test_payment_id,
        hospital_id=test_hospital_id
    )
    print(f"   Result type: {type(result)}")
    print(f"   Result keys: {result.keys()}")
    print("   ✅ SUCCESS")
except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Tests complete!")
