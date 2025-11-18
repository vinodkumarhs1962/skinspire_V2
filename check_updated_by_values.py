import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

with get_db_session() as session:
    # Get actual values
    result = session.execute(text("""
        SELECT
            updated_by,
            COUNT(*) as count
        FROM ar_subledger
        GROUP BY updated_by
        ORDER BY count DESC
    """)).fetchall()

    print('updated_by values:')
    for row in result:
        print(f'  {repr(row.updated_by)}: {row.count} records')

    # Sample some records
    print('\nSample records:')
    samples = session.execute(text("""
        SELECT entry_id, created_by, updated_by
        FROM ar_subledger
        LIMIT 10
    """)).fetchall()

    for s in samples:
        print(f'  created_by={repr(s.created_by)}, updated_by={repr(s.updated_by)}')
