"""
Update AR updated_by using SQLAlchemy ORM
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from app.models.transaction import ARSubledger

print('Updating AR entries using SQLAlchemy ORM...')

with get_db_session() as session:
    # Get all AR entries
    ar_entries = session.query(ARSubledger).all()

    print(f'Found {len(ar_entries)} AR entries')

    # Update each one
    for entry in ar_entries:
        if not entry.created_by:
            entry.created_by = 'system_backfill'
        if not entry.updated_by:
            entry.updated_by = 'system_backfill'

    # Commit
    session.commit()
    print('Committed')

# Verify
print('\nVerifying...')
with get_db_session() as session:
    total = session.query(ARSubledger).count()
    with_created = session.query(ARSubledger).filter(ARSubledger.created_by.isnot(None)).count()
    with_updated = session.query(ARSubledger).filter(ARSubledger.updated_by.isnot(None)).count()

    print(f'Total: {total}')
    print(f'With created_by: {with_created}')
    print(f'With updated_by: {with_updated}')

    # Sample
    samples = session.query(ARSubledger).limit(5).all()
    print('\nSample:')
    for s in samples:
        print(f'  created_by={repr(s.created_by)}, updated_by={repr(s.updated_by)}')
