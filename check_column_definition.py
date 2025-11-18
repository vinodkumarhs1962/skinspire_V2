"""
Check column definition for updated_by
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import inspect, text

with get_db_session() as session:
    # Get column info
    result = session.execute(text("""
        SELECT column_name, data_type, column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'ar_subledger'
          AND column_name IN ('created_by', 'updated_by')
        ORDER BY column_name
    """)).fetchall()

    print('Column definitions:')
    for row in result:
        print(f'\n{row.column_name}:')
        print(f'  Type: {row.data_type}')
        print(f'  Default: {row.column_default}')
        print(f'  Nullable: {row.is_nullable}')
