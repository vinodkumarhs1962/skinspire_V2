"""
Create 'system' user for audit trail
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text
import uuid

print('Creating system user...')

with get_db_session() as session:
    # Check if already exists
    existing = session.execute(text("""
        SELECT user_id FROM users WHERE user_id = 'system'
    """)).first()

    if existing:
        print('System user already exists')
    else:
        # Get a hospital_id and staff_id to link to
        hospital = session.execute(text("""
            SELECT hospital_id FROM hospitals LIMIT 1
        """)).first()

        if not hospital:
            print('ERROR: No hospitals found')
            sys.exit(1)

        # Create a dummy staff record for system
        staff_id = uuid.uuid4()
        session.execute(text("""
            INSERT INTO staff (staff_id, hospital_id, staff_name, email, phone, role, status, is_deleted)
            VALUES (:staff_id, :hospital_id, 'System', 'system@system.local', 'system', 'system', 'active', FALSE)
        """), {'staff_id': staff_id, 'hospital_id': hospital.hospital_id})

        # Create system user
        session.execute(text("""
            INSERT INTO users (user_id, hospital_id, entity_type, entity_id, is_active, created_by, updated_by)
            VALUES ('system', :hospital_id, 'staff', :staff_id, TRUE, 'system', 'system')
        """), {'hospital_id': hospital.hospital_id, 'staff_id': staff_id})

        session.commit()
        print('System user created successfully')

print('Done')
