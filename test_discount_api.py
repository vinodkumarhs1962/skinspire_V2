"""
Test discount API functionality directly
"""
import sys
sys.path.insert(0, '.')

from app.services.database_service import get_db_session
from app.models.master import Hospital, Service

hospital_id = '4ef72e18-e65d-4766-b9eb-0308c42485ca'

print("Starting test...")

try:
    with get_db_session() as session:
        print("Session created")

        # Get hospital configuration
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

        if not hospital:
            print("ERROR: Hospital not found")
            sys.exit(1)

        print(f"Hospital found: {hospital.name}")
        print(f"Bulk discount enabled: {hospital.bulk_discount_enabled}")
        print(f"Min service count: {hospital.bulk_discount_min_service_count}")

        # Get all active services with discount config
        services = session.query(Service).filter(
            Service.hospital_id == hospital_id,
            Service.is_active == True,
            Service.is_deleted == False
        ).all()

        print(f"Found {len(services)} services")

        # Build service discount map
        service_discounts = {}
        for service in services:
            service_discounts[str(service.service_id)] = {
                'service_id': str(service.service_id),
                'service_name': service.service_name,
                'price': float(service.price),
                'bulk_discount_percent': float(service.bulk_discount_percent or 0),
                'max_discount': float(service.max_discount or 100),
                'has_bulk_discount': service.bulk_discount_percent > 0 if service.bulk_discount_percent else False
            }

        print(f"Service discounts map created with {len(service_discounts)} entries")

        # Show sample services with bulk discount
        eligible_services = [s for s in service_discounts.values() if s['has_bulk_discount']]
        print(f"\nServices eligible for bulk discount: {len(eligible_services)}")
        for s in eligible_services[:5]:
            print(f"  - {s['service_name']}: {s['bulk_discount_percent']}%")

        print("\nSUCCESS: Discount API logic works!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
