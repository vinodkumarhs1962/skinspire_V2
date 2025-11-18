"""
Check which tables have the track_user_changes trigger
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

with get_db_session() as session:
    # Get all tables with track_user_changes trigger
    result = session.execute(text("""
        SELECT DISTINCT event_object_table as table_name
        FROM information_schema.triggers
        WHERE trigger_name = 'track_user_changes'
        ORDER BY event_object_table
    """)).fetchall()

    print(f'Tables with track_user_changes trigger: {len(result)}')
    print('=' * 80)
    for row in result:
        print(f'  - {row.table_name}')

    # Check how many tables have updated_by column
    print('\n\nTables with updated_by column:')
    print('=' * 80)

    tables_with_updated_by = session.execute(text("""
        SELECT DISTINCT table_name
        FROM information_schema.columns
        WHERE column_name = 'updated_by'
          AND table_schema = 'public'
        ORDER BY table_name
    """)).fetchall()

    print(f'Found {len(tables_with_updated_by)} tables:')
    for row in tables_with_updated_by:
        print(f'  - {row.table_name}')

    # Check which updated_by tables DON'T have the trigger
    print('\n\nTables with updated_by but NO track_user_changes trigger:')
    print('=' * 80)

    tables_without_trigger = session.execute(text("""
        SELECT DISTINCT c.table_name
        FROM information_schema.columns c
        WHERE c.column_name = 'updated_by'
          AND c.table_schema = 'public'
          AND c.table_name NOT IN (
              SELECT DISTINCT event_object_table
              FROM information_schema.triggers
              WHERE trigger_name = 'track_user_changes'
          )
        ORDER BY c.table_name
    """)).fetchall()

    if tables_without_trigger:
        print(f'Found {len(tables_without_trigger)} tables:')
        for row in tables_without_trigger:
            print(f'  - {row.table_name}')
    else:
        print('All tables with updated_by have the trigger')
