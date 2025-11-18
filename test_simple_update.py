"""
Test simple update using session.query().update()
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from app.models.transaction import ARSubledger

print('Testing bulk update...')

with get_db_session() as session:
    # Try bulk update
    count = session.query(ARSubledger).update(
        {ARSubledger.updated_by: 'system_backfill'},
        synchronize_session=False
    )

    print(f'Updated {count} records')

    session.commit()
    print('Committed')

# Verify
print('\nVerifying...')
with get_db_session() as session:
    total = session.query(ARSubledger).count()
    with_updated = session.query(ARSubledger).filter(ARSubledger.updated_by.isnot(None)).count()

    print(f'Total: {total}')
    print(f'With updated_by: {with_updated}')

    # Sample
    samples = session.query(ARSubledger).limit(5).all()
    print('\nSample:')
    for s in samples:
        print(f'  entry_id={str(s.entry_id)[:8]}, updated_by={repr(s.updated_by)}')
