"""
Backfill script for Payment PMT-2025-000106
Creates missing AR entry for package installment payment

Payment Details:
- Payment ID: 09cc6ef3-3ff2-415c-965d-26a02cd2c9cc
- Payment Number: PMT-2025-000106
- Total Amount: ₹4,800.00
- Current AR Total: ₹2,300.00
- Missing AR: ₹2,500.00 (package installment)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text
from decimal import Decimal
import uuid

PAYMENT_ID = '09cc6ef3-3ff2-415c-965d-26a02cd2c9cc'
MISSING_AMOUNT = Decimal('2500.00')

print('=' * 80)
print('BACKFILL AR ENTRY FOR PAYMENT PMT-2025-000106')
print('=' * 80)

with get_db_session() as session:
    # 1. Get payment details
    print('\n1. FETCHING PAYMENT DETAILS')
    print('-' * 80)

    payment = session.execute(text("""
        SELECT payment_id, payment_number, total_amount, payment_date,
               patient_id, branch_id, hospital_id, gl_entry_id
        FROM payment_details
        WHERE payment_id = :payment_id
    """), {'payment_id': PAYMENT_ID}).first()

    if not payment:
        print('❌ ERROR: Payment not found!')
        sys.exit(1)

    print(f'✓ Payment: {payment.payment_number}')
    print(f'  Total: ₹{payment.total_amount}')
    print(f'  Patient: {payment.patient_id}')
    print(f'  Branch: {payment.branch_id}')
    print(f'  GL Transaction: {payment.gl_entry_id}')

    # 2. Check existing AR
    print('\n2. CHECKING EXISTING AR ENTRIES')
    print('-' * 80)

    existing_ar = session.execute(text("""
        SELECT COUNT(*) as count, COALESCE(SUM(credit_amount), 0) as total
        FROM ar_subledger
        WHERE reference_id = :payment_id
          AND reference_type = 'payment'
    """), {'payment_id': payment.payment_id}).first()

    print(f'Existing AR Entries: {existing_ar.count}')
    print(f'Existing AR Total: ₹{existing_ar.total}')
    print(f'Payment Total: ₹{payment.total_amount}')
    print(f'Missing: ₹{payment.total_amount - existing_ar.total}')

    # 3. Get installment details
    print('\n3. FETCHING INSTALLMENT DETAILS')
    print('-' * 80)

    installment = session.execute(text("""
        SELECT ip.installment_id, ip.plan_id, ip.installment_number, ip.amount, ip.status,
               ppp.patient_id, ppp.branch_id
        FROM installment_payments ip
        JOIN package_payment_plans ppp ON ip.plan_id = ppp.plan_id
        WHERE ip.payment_id = :payment_id
    """), {'payment_id': payment.payment_id}).first()

    if not installment:
        print('❌ ERROR: No installment record found!')
        sys.exit(1)

    print(f'✓ Installment #{installment.installment_number}')
    print(f'  Plan ID: {installment.plan_id}')
    print(f'  Full Amount Due: ₹{installment.amount}')
    print(f'  Status: {installment.status}')
    print(f'  Partial Payment: ₹{MISSING_AMOUNT}')

    # 4. Confirm
    print('\n' + '=' * 80)
    print('PROPOSED ACTION:')
    print('=' * 80)
    print(f'Create AR subledger entry:')
    print(f'  Entry Type: package_installment')
    print(f'  Reference ID: {payment.payment_id}')
    print(f'  Reference Line Item: NULL')
    print(f'  Credit Amount: ₹{MISSING_AMOUNT}')
    print(f'  GL Transaction: {payment.gl_entry_id}')

    confirm = input('\nProceed with backfill? (yes/no): ')

    if confirm.lower() != 'yes':
        print('Backfill cancelled.')
        sys.exit(0)

    # 5. Create AR entry
    print('\n4. CREATING AR ENTRY')
    print('-' * 80)

    try:
        from app.services.subledger_service import create_ar_subledger_entry

        create_ar_subledger_entry(
            session=session,
            hospital_id=uuid.UUID(str(payment.hospital_id)),
            branch_id=uuid.UUID(str(payment.branch_id)),
            patient_id=uuid.UUID(str(payment.patient_id)),
            entry_type='package_installment',
            reference_id=uuid.UUID(str(payment.payment_id)),
            reference_type='payment',
            reference_number=payment.payment_number,
            reference_line_item_id=None,  # NULL for package installments
            debit_amount=Decimal('0'),
            credit_amount=MISSING_AMOUNT,
            transaction_date=payment.payment_date,
            gl_transaction_id=uuid.UUID(str(payment.gl_entry_id)) if payment.gl_entry_id else None,
            current_user_id='system_backfill'
        )

        session.commit()
        print(f'✓ AR entry created successfully!')

    except Exception as e:
        session.rollback()
        print(f'❌ ERROR creating AR entry: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 6. Verify
    print('\n5. VERIFICATION')
    print('-' * 80)

    final_ar = session.execute(text("""
        SELECT COUNT(*) as count, COALESCE(SUM(credit_amount), 0) as total
        FROM ar_subledger
        WHERE reference_id = :payment_id
          AND reference_type = 'payment'
    """), {'payment_id': payment.payment_id}).first()

    print(f'Final AR Entries: {final_ar.count}')
    print(f'Final AR Total: ₹{final_ar.total}')
    print(f'Payment Total: ₹{payment.total_amount}')

    if abs(final_ar.total - payment.total_amount) < 0.01:
        print('✓✓✓ SUCCESS: AR total matches payment total!')
    else:
        print('⚠ WARNING: AR total does not match payment total!')
        print(f'  Difference: ₹{abs(final_ar.total - payment.total_amount)}')

print('\n' + '=' * 80)
print('BACKFILL COMPLETED')
print('=' * 80)
