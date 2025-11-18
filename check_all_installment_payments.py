"""
Check all installment payments and their AR entries
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('=' * 80)
print('ALL INSTALLMENT PAYMENTS CHECK')
print('=' * 80)

with get_db_session() as session:
    # Get all installment payments
    print('\n1. ALL INSTALLMENT PAYMENTS')
    print('-' * 80)

    installments = session.execute(text("""
        SELECT ip.payment_id, pd.payment_number, pd.total_amount,
               ip.installment_number, ip.amount, ip.paid_amount,
               ip.status, pd.payment_date
        FROM installment_payments ip
        JOIN payment_details pd ON ip.payment_id = pd.payment_id
        ORDER BY pd.payment_date DESC
    """)).fetchall()

    if not installments:
        print('✗ No installment payments found in the system')
    else:
        print(f'Found {len(installments)} installment payment(s)\n')

        for inst in installments:
            print(f'Payment: {inst.payment_number}')
            print(f'  Payment ID: {inst.payment_id}')
            print(f'  Date: {inst.payment_date}')
            print(f'  Total Payment: ₹{inst.total_amount}')
            print(f'  Installment #: {inst.installment_number}')
            print(f'  Installment Amount: ₹{inst.amount}')
            print(f'  Paid Amount: ₹{inst.paid_amount}')
            print(f'  Status: {inst.status}')

            # Check AR entries for this payment
            ar_count = session.execute(text("""
                SELECT COUNT(*) as count
                FROM ar_subledger
                WHERE reference_id = :payment_id
                  AND reference_type = 'payment'
                  AND entry_type = 'package_installment'
            """), {'payment_id': inst.payment_id}).scalar()

            if ar_count > 0:
                print(f'  AR Entries: ✓ {ar_count} package_installment entry found')
            else:
                print(f'  AR Entries: ✗ MISSING package_installment entry!')

            print()

print('=' * 80)
