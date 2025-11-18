"""
Check PMT-2025-000102 payment details and what it should have been
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('=' * 80)
print('PMT-2025-000102 INVESTIGATION')
print('=' * 80)

with get_db_session() as session:
    # Get payment details
    print('\n1. PAYMENT DETAILS')
    print('-' * 80)

    payment = session.execute(text("""
        SELECT
            pd.payment_id,
            pd.payment_number,
            pd.total_amount,
            pd.payment_date,
            pd.invoice_id,
            pd.patient_id,
            pd.payment_source,
            pd.invoice_count,
            ih.invoice_number
        FROM payment_details pd
        LEFT JOIN invoice_header ih ON pd.invoice_id = ih.invoice_id
        WHERE pd.payment_number = 'PMT-2025-000102'
    """)).first()

    if not payment:
        print('✗ Payment not found')
    else:
        print(f'Payment Number: {payment.payment_number}')
        print(f'Payment ID: {payment.payment_id}')
        print(f'Total Amount: ₹{payment.total_amount}')
        print(f'Payment Date: {payment.payment_date}')
        print(f'Payment Source: {payment.payment_source}')
        print(f'Invoice Count: {payment.invoice_count}')

        if payment.invoice_id:
            print(f'Invoice ID: {payment.invoice_id}')
            print(f'Invoice Number: {payment.invoice_number}')
        else:
            print('Invoice ID: NULL')

        # Check installment payment for this payment_id
        print('\n2. INSTALLMENT PAYMENT DETAILS')
        print('-' * 80)

        installment = session.execute(text("""
            SELECT
                ip.installment_id,
                ip.plan_id,
                ip.installment_number,
                ip.amount,
                ip.paid_amount,
                ip.status,
                ppp.package_name,
                ppp.invoice_id as plan_invoice_id,
                ih.invoice_number as plan_invoice_number
            FROM installment_payments ip
            JOIN package_payment_plans ppp ON ip.plan_id = ppp.plan_id
            LEFT JOIN invoice_header ih ON ppp.invoice_id = ih.invoice_id
            WHERE ip.payment_id = :payment_id
        """), {'payment_id': payment.payment_id}).first()

        if installment:
            print(f'✓ Installment found')
            print(f'  Plan ID: {installment.plan_id}')
            print(f'  Package: {installment.package_name}')
            print(f'  Installment #: {installment.installment_number}')
            print(f'  Amount: ₹{installment.amount}')
            print(f'  Paid Amount: ₹{installment.paid_amount}')
            print(f'  Status: {installment.status}')

            if installment.plan_invoice_id:
                print(f'  ✓ PLAN LINKED TO INVOICE: {installment.plan_invoice_number}')
                print(f'  Invoice ID: {installment.plan_invoice_id}')
            else:
                print(f'  ✗ Plan NOT linked to invoice!')

        else:
            print('✗ No installment payment found')

        # Check AR entries
        print('\n3. AR SUBLEDGER ENTRIES')
        print('-' * 80)

        ar_entries = session.execute(text("""
            SELECT entry_type, reference_line_item_id, credit_amount,
                   item_type, item_name, created_at
            FROM ar_subledger
            WHERE reference_id = :payment_id
              AND reference_type = 'payment'
            ORDER BY created_at
        """), {'payment_id': payment.payment_id}).fetchall()

        if ar_entries:
            print(f'Found {len(ar_entries)} AR entry/entries:')
            for i, ar in enumerate(ar_entries, 1):
                print(f'\n  Entry {i}:')
                print(f'    Type: {ar.entry_type}')
                print(f'    Line Item ID: {ar.reference_line_item_id or "NULL"}')
                print(f'    Credit: ₹{ar.credit_amount}')
                print(f'    Item Type: {ar.item_type or "N/A"}')
                print(f'    Item Name: {ar.item_name or "N/A"}')
        else:
            print('✗ NO AR ENTRIES FOUND!')

print('\n' + '=' * 80)
