"""Debug script to investigate medicine 404 issue"""
import sys
from app import create_app, db
from app.models.master import Medicine
from app.models.transaction import Inventory
from sqlalchemy import and_

app = create_app()

with app.app_context():

    # The medicine ID from the 404 error
    medicine_id = '6ddf27d5-e733-470d-9449-b594030959b2'

    print("=" * 80)
    print("INVESTIGATING MEDICINE 404 ISSUE")
    print("=" * 80)

    # Check if medicine exists at all
    print(f"\n1. Checking if medicine {medicine_id} exists in database:")
    medicine = db.session.query(Medicine).filter_by(medicine_id=medicine_id).first()

    if medicine:
        print(f"   ✅ Medicine EXISTS")
        print(f"   - Name: {medicine.medicine_name}")
        print(f"   - Type: {medicine.medicine_type}")
        print(f"   - Hospital ID: {medicine.hospital_id}")
        print(f"   - is_active: {getattr(medicine, 'is_active', 'NO FIELD')}")
    else:
        print(f"   ❌ Medicine NOT FOUND in database")
        sys.exit(1)

    # Check inventory for this medicine
    print(f"\n2. Checking inventory for this medicine:")
    inventory = db.session.query(Inventory).filter(
        Inventory.medicine_id == medicine_id,
        Inventory.current_stock > 0
    ).all()

    if inventory:
        print(f"   ✅ Found {len(inventory)} inventory record(s) with stock")
        for inv in inventory:
            print(f"   - Batch: {inv.batch}, Stock: {inv.current_stock}, Hospital: {inv.hospital_id}")
    else:
        print(f"   ❌ No inventory with stock found")

    # Check all hospitals
    print(f"\n3. Checking all hospitals in database:")
    from app.models.config import Hospital
    hospitals = db.session.query(Hospital).all()
    for h in hospitals:
        print(f"   - {h.hospital_name}: {h.hospital_id}")

    # Now simulate the search endpoint
    print(f"\n4. Simulating search endpoint (Prescription type):")

    # Get medicine IDs with stock (same logic as search endpoint)
    medicine_ids_with_stock = db.session.query(Inventory.medicine_id).filter(
        Inventory.current_stock > 0
    ).distinct().all()
    medicine_ids_with_stock = [m[0] for m in medicine_ids_with_stock]

    print(f"   - Total medicines with stock: {len(medicine_ids_with_stock)}")
    print(f"   - Our medicine in list? {medicine_id in medicine_ids_with_stock}")

    # Try search for each hospital
    for hospital in hospitals:
        base_filter = and_(
            Medicine.hospital_id == hospital.hospital_id,
            Medicine.medicine_type == 'Prescription',
            Medicine.medicine_id.in_(medicine_ids_with_stock)
        )

        results = db.session.query(Medicine).filter(base_filter).all()
        print(f"\n   Hospital: {hospital.hospital_name}")
        print(f"   - Found {len(results)} prescription medicines with stock")

        # Check if our medicine is in results
        our_medicine = [m for m in results if str(m.medicine_id) == medicine_id]
        if our_medicine:
            print(f"   - ✅ Our medicine IS in search results for this hospital")
        else:
            print(f"   - ❌ Our medicine NOT in search results for this hospital")

    # Now simulate batch endpoint for each hospital
    print(f"\n5. Simulating batch endpoint lookup:")
    for hospital in hospitals:
        med = db.session.query(Medicine).filter_by(
            hospital_id=hospital.hospital_id,
            medicine_id=medicine_id
        ).first()

        print(f"\n   Hospital: {hospital.hospital_name}")
        if med:
            print(f"   - ✅ Medicine FOUND by batch endpoint")
        else:
            print(f"   - ❌ Medicine NOT FOUND by batch endpoint (would return 404)")

    print("\n" + "=" * 80)
    print("DIAGNOSIS:")
    print("=" * 80)

    # The key question: does medicine.hospital_id match the hospital where it has stock?
    if medicine and inventory:
        medicine_hospital = medicine.hospital_id
        inventory_hospitals = set([inv.hospital_id for inv in inventory])

        print(f"Medicine record says hospital_id: {medicine_hospital}")
        print(f"Inventory records say hospital_id: {inventory_hospitals}")

        if medicine_hospital in inventory_hospitals:
            print("✅ CONSISTENT: Medicine and inventory have matching hospital_id")
        else:
            print("❌ MISMATCH: Medicine.hospital_id != Inventory.hospital_id")
            print("   This is the problem! The medicine record points to one hospital,")
            print("   but the inventory belongs to a different hospital.")
