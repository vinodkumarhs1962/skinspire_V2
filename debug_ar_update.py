"""
Debug AR update_by field
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from app.models.transaction import ARSubledger

print('Debugging AR updated_by field...')

with get_db_session() as session:
    # Get one AR entry
    entry = session.query(ARSubledger).first()

    print(f'\nBEFORE UPDATE:')
    print(f'  created_by: {repr(entry.created_by)}')
    print(f'  updated_by: {repr(entry.updated_by)}')

    # Set updated_by
    entry.updated_by = 'TEST_VALUE'

    print(f'\nAFTER ASSIGNMENT:')
    print(f'  created_by: {repr(entry.created_by)}')
    print(f'  updated_by: {repr(entry.updated_by)}')

    # Flush to see if it changes
    session.flush()

    print(f'\nAFTER FLUSH:')
    print(f'  created_by: {repr(entry.created_by)}')
    print(f'  updated_by: {repr(entry.updated_by)}')

    # Check dirty state
    print(f'\nDirty attributes: {session.is_modified(entry)}')
    if session.is_modified(entry):
        print(f'  Modified: {[attr.key for attr in entry.__class__.__mapper__.attrs if session.is_modified(entry, [attr.key])]}')

    # Commit
    session.commit()

    print(f'\nAFTER COMMIT:')
    print(f'  created_by: {repr(entry.created_by)}')
    print(f'  updated_by: {repr(entry.updated_by)}')

# Verify in new session
print('\nVerifying in new session...')
with get_db_session() as session:
    entry = session.query(ARSubledger).first()
    print(f'  created_by: {repr(entry.created_by)}')
    print(f'  updated_by: {repr(entry.updated_by)}')
