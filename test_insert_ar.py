"""
Test inserting a new AR entry to see what the trigger sets
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from app.models.transaction import ARSubledger
from datetime import datetime, timezone
from decimal import Decimal
import uuid

print('Testing AR insert with trigger...')

with get_db_session() as session:
    # Create a test AR entry
    test_entry = ARSubledger(
        hospital_id=uuid.uuid4(),
        branch_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        entry_type='test',
        reference_id=uuid.uuid4(),
        reference_type='test',
        reference_number='TEST-001',
        debit_amount=Decimal('100.00'),
        credit_amount=Decimal('0'),
        transaction_date=datetime.now(timezone.utc),
        current_balance=Decimal('100.00')
    )

    # Explicitly set audit fields
    test_entry.created_by = 'MY_TEST_VALUE'
    test_entry.updated_by = 'MY_TEST_VALUE'

    print(f'\nBEFORE INSERT:')
    print(f'  created_by: {repr(test_entry.created_by)}')
    print(f'  updated_by: {repr(test_entry.updated_by)}')

    session.add(test_entry)
    session.flush()

    print(f'\nAFTER FLUSH (trigger has run):')
    print(f'  created_by: {repr(test_entry.created_by)}')
    print(f'  updated_by: {repr(test_entry.updated_by)}')

    session.rollback()  # Don't actually save
    print('\nRolled back (test only)')
