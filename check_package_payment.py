"""
Check latest package installment payment and AR entries
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('=' * 80)
print('PACKAGE INSTALLMENT PAYMENT CHECK')
print('=' * 80)

with get_db_session() as session:
    # Get latest payment
    print('\n1. LATEST PAYMENT')
    print('-' * 80)

    payment = session.execute(text("""
        SELECT payment_id, payment_number, total_amount, payment_date, payment_source
        FROM payment_details
        ORDER BY payment_date DESC, created_at DESC
        LIMIT 1
    """)).first()

    if payment:
        print(f'Payment: {payment.payment_number}')
        print(f'Total: ₹{payment.total_amount}')
        print(f'Date: {payment.payment_date}')
        print(f'Source: {payment.payment_source}')

        # Check for installment payment
        print('\n2. INSTALLMENT PAYMENT RECORD')
        print('-' * 80)

        installment = session.execute(text("""
            SELECT ip.installment_id, ip.plan_id, ip.installment_number,
                   ip.amount, ip.paid_amount, ip.status
            FROM installment_payments ip
            WHERE ip.payment_id = :payment_id
        """), {'payment_id': payment.payment_id}).first()

        if installment:
            print(f'✓ Installment found')
            print(f'  Installment #: {installment.installment_number}')
            print(f'  Full Amount: ₹{installment.amount}')
            print(f'  Paid Amount: ₹{installment.paid_amount}')
            print(f'  Status: {installment.status}')
        else:
            print('✗ No installment payment record found')

        # Check AR entries
        print('\n3. AR SUBLEDGER ENTRIES')
        print('-' * 80)

        ar_entries = session.execute(text("""
            SELECT entry_type, reference_line_item_id,
                   credit_amount, item_type, item_name,
                   created_by, created_at
            FROM ar_subledger
            WHERE reference_id = :payment_id
              AND reference_type = 'payment'
            ORDER BY created_at
        """), {'payment_id': payment.payment_id}).fetchall()

        if ar_entries:
            print(f'Found {len(ar_entries)} AR entries:')
            for i, ar in enumerate(ar_entries, 1):
                print(f'\n  Entry {i}:')
                print(f'    Type: {ar.entry_type}')
                print(f'    Line Item ID: {ar.reference_line_item_id or "NULL (Package)"}')
                print(f'    Credit: ₹{ar.credit_amount}')
                print(f'    Item Type: {ar.item_type or "N/A"}')
                print(f'    Item Name: {ar.item_name or "N/A"}')
                print(f'    Created By: {ar.created_by}')
        else:
            print('✗ NO AR ENTRIES FOUND!')
            print('\n  This is the issue - package installment payment')
            print('  should create AR entry but it did not.')
    else:
        print('No payments found')

print('\n' + '=' * 80)
