import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

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

    # Also show a sample
    sample = session.execute(text("""
        SELECT entry_id, created_by, updated_by
        FROM ar_subledger
        ORDER BY created_at DESC
        LIMIT 5
    """)).fetchall()

    print('\nSample (latest 5):')
    for row in sample:
        print(f'  {row.entry_id}: created_by={row.created_by}, updated_by={row.updated_by}')
