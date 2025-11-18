"""
Check the update_timestamp trigger function
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

with get_db_session() as session:
    # Get function definition
    result = session.execute(text("""
        SELECT pg_get_functiondef(oid) as definition
        FROM pg_proc
        WHERE proname = 'update_timestamp'
    """)).first()

    if result:
        print('update_timestamp function definition:')
        print('=' * 80)
        print(result.definition)
        print('=' * 80)
    else:
        print('Function update_timestamp not found')
