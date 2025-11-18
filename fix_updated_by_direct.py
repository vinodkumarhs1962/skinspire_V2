import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('Fixing updated_by fields...')

with get_db_session() as session:
    # Try direct update
    try:
        result = session.execute(text("""
            UPDATE ar_subledger
            SET updated_by = 'system_backfill'
            WHERE updated_by IS NULL OR updated_by = ''
        """))

        print(f'Rows affected: {result.rowcount}')

        # Commit
        session.commit()
        print('Committed')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        session.rollback()

# Verify in new session
print('\nVerifying...')
with get_db_session() as session:
    result = session.execute(text("""
        SELECT
            COUNT(*) as total,
            COUNT(created_by) as with_created,
            COUNT(updated_by) as with_updated
        FROM ar_subledger
    """)).first()

    print(f'Total: {result.total}')
    print(f'With created_by: {result.with_created}')
    print(f'With updated_by: {result.with_updated}')
