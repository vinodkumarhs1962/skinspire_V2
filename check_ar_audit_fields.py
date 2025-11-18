"""
Check AR Subledger Audit Fields
Verifies that created_by and updated_by fields are populated
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('=' * 80)
print('AR SUBLEDGER AUDIT FIELDS CHECK')
print('=' * 80)

with get_db_session() as session:
    # Get latest payment's AR entries with audit fields
    result = session.execute(text("""
        SELECT
            entry_type,
            reference_line_item_id,
            item_type,
            item_name,
            credit_amount,
            created_by,
            updated_by,
            created_at,
            updated_at
        FROM ar_subledger
        WHERE reference_id = (
            SELECT payment_id
            FROM payment_details
            ORDER BY payment_date DESC, created_at DESC
            LIMIT 1
        )
        AND reference_type = 'payment'
        ORDER BY transaction_date, created_at
    """)).fetchall()

    print(f'\nFound {len(result)} AR entries for latest payment\n')

    all_have_created_by = True
    all_have_updated_by = True
    all_have_item_details = True

    for i, row in enumerate(result, 1):
        print(f'AR Entry #{i}:')
        print(f'  Entry Type: {row.entry_type}')
        print(f'  Line Item ID: {row.reference_line_item_id or "NULL (Package)"}')
        print(f'  Item Type: {row.item_type or "❌ MISSING"}')
        print(f'  Item Name: {row.item_name or "❌ MISSING"}')
        print(f'  Credit Amount: ₹{row.credit_amount}')
        print(f'  Created By: {row.created_by or "❌ MISSING"}')
        print(f'  Updated By: {row.updated_by or "❌ MISSING"}')
        print(f'  Created At: {row.created_at}')
        print(f'  Updated At: {row.updated_at}')
        print()

        if not row.created_by:
            all_have_created_by = False
        if not row.updated_by:
            all_have_updated_by = False
        if not row.item_type or not row.item_name:
            all_have_item_details = False

    print('=' * 80)
    print('AUDIT FIELD VERIFICATION SUMMARY')
    print('=' * 80)
    print(f'Created By: {"✓ ALL POPULATED" if all_have_created_by else "❌ SOME MISSING"}')
    print(f'Updated By: {"✓ ALL POPULATED" if all_have_updated_by else "❌ SOME MISSING"}')
    print(f'Item Details: {"✓ ALL POPULATED" if all_have_item_details else "❌ SOME MISSING"}')
    print('=' * 80)

    # Also check ALL AR entries
    print('\nCHECKING ALL AR ENTRIES IN SYSTEM')
    print('=' * 80)

    summary = session.execute(text("""
        SELECT
            COUNT(*) as total_entries,
            COUNT(created_by) as entries_with_created_by,
            COUNT(updated_by) as entries_with_updated_by,
            COUNT(item_type) as entries_with_item_type,
            COUNT(item_name) as entries_with_item_name
        FROM ar_subledger
    """)).first()

    print(f'Total AR Entries: {summary.total_entries}')
    print(f'Entries with created_by: {summary.entries_with_created_by} ({summary.entries_with_created_by}/{summary.total_entries})')
    print(f'Entries with updated_by: {summary.entries_with_updated_by} ({summary.entries_with_updated_by}/{summary.total_entries})')
    print(f'Entries with item_type: {summary.entries_with_item_type} ({summary.entries_with_item_type}/{summary.total_entries})')
    print(f'Entries with item_name: {summary.entries_with_item_name} ({summary.entries_with_item_name}/{summary.total_entries})')

    if summary.entries_with_created_by < summary.total_entries:
        print(f'\n⚠ WARNING: {summary.total_entries - summary.entries_with_created_by} entries missing created_by')
    if summary.entries_with_updated_by < summary.total_entries:
        print(f'⚠ WARNING: {summary.total_entries - summary.entries_with_updated_by} entries missing updated_by')
    if summary.entries_with_item_type < summary.total_entries:
        print(f'⚠ WARNING: {summary.total_entries - summary.entries_with_item_type} entries missing item_type')
    if summary.entries_with_item_name < summary.total_entries:
        print(f'⚠ WARNING: {summary.total_entries - summary.entries_with_item_name} entries missing item_name')

print('\n' + '=' * 80)
print('CHECK COMPLETED')
print('=' * 80)
