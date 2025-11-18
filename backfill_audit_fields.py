"""
Backfill NULL audit fields with development user 7777777777
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

DEV_USER_ID = '7777777777'

print('=' * 80)
print('BACKFILL AUDIT FIELDS')
print('=' * 80)

with get_db_session() as session:
    # Backfill created_by
    print('\nBackfilling created_by...')
    result = session.execute(text("""
        UPDATE ar_subledger
        SET created_by = :user_id
        WHERE created_by IS NULL OR created_by = ''
    """), {'user_id': DEV_USER_ID})
    print(f'✓ Updated {result.rowcount} records')

    # Backfill updated_by
    print('\nBackfilling updated_by...')
    result = session.execute(text("""
        UPDATE ar_subledger
        SET updated_by = :user_id
        WHERE updated_by IS NULL OR updated_by = ''
    """), {'user_id': DEV_USER_ID})
    print(f'✓ Updated {result.rowcount} records')

    session.commit()

print('\n✓ Backfill completed!')
