"""
Backfill created_by and updated_by audit fields in AR Subledger
Sets all empty audit fields to 'system_backfill'
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('=' * 80)
print('BACKFILL AR SUBLEDGER AUDIT FIELDS')
print('=' * 80)

with get_db_session() as session:
    # Check current state
    print('\n1. CHECKING CURRENT STATE')
    print('-' * 80)

    summary = session.execute(text("""
        SELECT
            COUNT(*) as total_entries,
            COUNT(created_by) as entries_with_created_by,
            COUNT(updated_by) as entries_with_updated_by
        FROM ar_subledger
    """)).first()

    print(f'Total AR Entries: {summary.total_entries}')
    print(f'Entries with created_by: {summary.entries_with_created_by}')
    print(f'Entries with updated_by: {summary.entries_with_updated_by}')
    print(f'Missing created_by: {summary.total_entries - summary.entries_with_created_by}')
    print(f'Missing updated_by: {summary.total_entries - summary.entries_with_updated_by}')

    if summary.entries_with_created_by == summary.total_entries and summary.entries_with_updated_by == summary.total_entries:
        print('\n✓ All AR entries already have audit fields populated!')
        sys.exit(0)

    # Confirm backfill
    print('\n' + '=' * 80)
    print('PROPOSED ACTION:')
    print('=' * 80)
    print('Update all AR entries with missing audit fields to:')
    print('  created_by = \'system_backfill\'')
    print('  updated_by = \'system_backfill\'')
    print('\nProceeding with backfill...')

    # Backfill created_by
    print('\n2. BACKFILLING created_by')
    print('-' * 80)

    result = session.execute(text("""
        UPDATE ar_subledger
        SET created_by = 'system_backfill'
        WHERE created_by IS NULL
    """))

    print(f'✓ Updated {result.rowcount} records with created_by')

    # Backfill updated_by
    print('\n3. BACKFILLING updated_by')
    print('-' * 80)

    result = session.execute(text("""
        UPDATE ar_subledger
        SET updated_by = 'system_backfill'
        WHERE updated_by IS NULL
    """))

    print(f'✓ Updated {result.rowcount} records with updated_by')

    # Commit before verification
    session.commit()

# Verify in new session
print('\n4. VERIFICATION')
print('-' * 80)

with get_db_session() as session:
    final = session.execute(text("""
        SELECT
            COUNT(*) as total_entries,
            COUNT(created_by) as entries_with_created_by,
            COUNT(updated_by) as entries_with_updated_by
        FROM ar_subledger
    """)).first()

    print(f'Total AR Entries: {final.total_entries}')
    print(f'Entries with created_by: {final.entries_with_created_by}')
    print(f'Entries with updated_by: {final.entries_with_updated_by}')

    if final.entries_with_created_by == final.total_entries and final.entries_with_updated_by == final.total_entries:
        print('\n✓✓✓ SUCCESS: All AR entries now have audit fields!')
    else:
        print('\n⚠ WARNING: Some entries still missing audit fields!')
        print(f'  Missing created_by: {final.total_entries - final.entries_with_created_by}')
        print(f'  Missing updated_by: {final.total_entries - final.entries_with_updated_by}')

print('\n' + '=' * 80)
print('BACKFILL COMPLETED')
print('=' * 80)
