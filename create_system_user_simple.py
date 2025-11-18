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
        # Get a hospital_id to link to
        hospital = session.execute(text("""
            SELECT hospital_id FROM hospitals LIMIT 1
        """)).first()

        if not hospital:
            print('ERROR: No hospitals found')
            sys.exit(1)

        # Get an existing staff_id to link to (or use admin)
        staff = session.execute(text("""
            SELECT staff_id FROM staff LIMIT 1
        """)).first()

        if not staff:
            print('ERROR: No staff found')
            sys.exit(1)

        # Create system user (bypass audit triggers)
        try:
            session.execute(text("""
                INSERT INTO users (user_id, hospital_id, entity_type, entity_id, is_active, created_at, updated_at)
                VALUES ('system', :hospital_id, 'staff', :staff_id, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """), {'hospital_id': hospital.hospital_id, 'staff_id': staff.staff_id})

            session.commit()
            print('System user created successfully')
        except Exception as e:
            print(f'ERROR: {e}')
            # Might already exist from another process
            session.rollback()

print('Done')
