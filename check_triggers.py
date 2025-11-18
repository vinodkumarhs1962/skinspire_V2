"""
Check triggers on payment_details table
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

with get_db_session() as session:
    print('Triggers on payment_details table:')
    print('=' * 80)

    triggers = session.execute(text("""
        SELECT
            t.tgname AS trigger_name,
            p.proname AS function_name,
            CASE
                WHEN t.tgtype & 2 = 2 THEN 'BEFORE'
                WHEN t.tgtype & 64 = 64 THEN 'INSTEAD OF'
                ELSE 'AFTER'
            END AS timing,
            CASE
                WHEN t.tgtype & 4 = 4 THEN 'INSERT'
                WHEN t.tgtype & 8 = 8 THEN 'DELETE'
                WHEN t.tgtype & 16 = 16 THEN 'UPDATE'
                ELSE 'TRUNCATE'
            END AS event
        FROM pg_trigger t
        JOIN pg_proc p ON t.tgfoid = p.oid
        WHERE tgrelid = 'payment_details'::regclass
          AND NOT tgisinternal
        ORDER BY t.tgname
    """)).fetchall()

    if not triggers:
        print('No triggers found')
    else:
        for trig in triggers:
            print(f'\nTrigger: {trig.trigger_name}')
            print(f'  Function: {trig.function_name}')
            print(f'  Timing: {trig.timing}')
            print(f'  Event: {trig.event}')

print('\n' + '=' * 80)
