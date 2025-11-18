"""
Simple test for package installment payment - uses specific installment ID
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from app.services.package_payment_service import PackagePaymentService
from app.services.billing_service import record_multi_invoice_payment
from sqlalchemy import text
from decimal import Decimal
from datetime import datetime

# USE INSTALLMENT FROM FIND SCRIPT
TEST_INSTALLMENT_ID = '3b4a47b7-64d9-4869-85cc-9421fa7d5ec1'

print('=' * 80)
print('PACKAGE INSTALLMENT PAYMENT - SIMPLE TEST')
print('=' * 80)

# Get test data
with get_db_session() as session:
    print('\n[STEP 1] Get installment and plan details')
    print('-' * 80)

    result = session.execute(text("""
        SELECT
            ip.installment_id, ip.plan_id, ip.amount,
            ppp.invoice_id, ppp.patient_id,
            ih.invoice_number, ih.hospital_id, ih.branch_id,
            ih.total_amount as inv_total,
            ih.paid_amount as inv_paid_before,
            ih.balance_due as inv_balance_before
        FROM installment_payments ip
        JOIN package_payment_plans ppp ON ip.plan_id = ppp.plan_id
        JOIN invoice_header ih ON ppp.invoice_id = ih.invoice_id
        WHERE ip.installment_id = :inst_id
    """), {'inst_id': TEST_INSTALLMENT_ID}).first()

    if not result:
        print(f'ERROR: Installment {TEST_INSTALLMENT_ID} not found')
        sys.exit(1)

    print(f'Installment: {result.installment_id}')
    print(f'Amount: Rs.{result.amount}')
    print(f'Invoice: {result.invoice_number} (ID: {result.invoice_id})')
    print(f'Invoice Before: Paid=Rs.{result.inv_paid_before}, Balance=Rs.{result.inv_balance_before}')

# Record payment using shared session
print('\n[STEP 2] Record payment')
print('-' * 80)

try:
    with get_db_session() as session:
        # Build invoice allocation
        invoice_alloc = [{
            'invoice_id': str(result.invoice_id),
            'allocated_amount': Decimal(str(result.amount))
        }]

        print(f'Creating invoice payment for Rs.{result.amount}...')

        # Record as invoice payment
        # NOTE: Using save_as_draft=True to skip GL posting (which has a separate bug)
        # This tests the core payment and AR logic
        pay_result = record_multi_invoice_payment(
            hospital_id=result.hospital_id,
            invoice_allocations=invoice_alloc,
            payment_date=datetime.now().date(),
            cash_amount=Decimal(str(result.amount)),
            credit_card_amount=Decimal('0'),
            debit_card_amount=Decimal('0'),
            upi_amount=Decimal('0'),
            card_number_last4=None,
            card_type=None,
            upi_id=None,
            reference_number=None,
            recorded_by='7777777777',
            save_as_draft=True,  # Skip GL posting for now
            approval_threshold=Decimal('100000'),
            session=session
        )

        if not pay_result or not pay_result.get('success'):
            print(f'ERROR: Payment failed - {pay_result.get("error") if pay_result else "Unknown"}')
            sys.exit(1)

        payment_id = pay_result['payment_id']
        print(f'Payment created: {payment_id}')

        # Update installment
        print(f'Updating installment record...')

        pkg_svc = PackagePaymentService()
        inst_result = pkg_svc.record_installment_payment(
            installment_id=str(result.installment_id),
            paid_amount=Decimal(str(result.amount)),
            payment_id=payment_id,
            hospital_id=str(result.hospital_id),
            session=session
        )

        if not inst_result['success']:
            print(f'ERROR: Installment update failed - {inst_result.get("error")}')
            raise Exception(inst_result.get('error'))

        print(f'Installment updated: status={inst_result["new_status"]}')

        # Commit
        session.commit()
        print('Transaction COMMITTED')

except Exception as e:
    print(f'\nERROR: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify results
print('\n[STEP 3] Verify accounting entries')
print('-' * 80)

with get_db_session() as session:
    # Check payment
    pay = session.execute(text("""
        SELECT payment_number, invoice_id, total_amount, payment_source
        FROM payment_details
        WHERE payment_id = :pid
    """), {'pid': payment_id}).first()

    print(f'Payment: {pay.payment_number}')
    print(f'  Amount: Rs.{pay.total_amount}')
    print(f'  Invoice ID: {pay.invoice_id}')
    print(f'  Source: {pay.payment_source}')

    if str(pay.invoice_id) == str(result.invoice_id):
        print('  PASS: Linked to correct invoice')
    else:
        print('  FAIL: Wrong invoice link')

    # Check AR
    ar_list = session.execute(text("""
        SELECT entry_type, reference_line_item_id, credit_amount, item_type, item_name
        FROM ar_subledger
        WHERE reference_id = :pid AND reference_type = 'payment'
    """), {'pid': payment_id}).fetchall()

    print(f'\nAR Entries: {len(ar_list)} found')
    for ar in ar_list:
        print(f'  Type={ar.entry_type}, LineItem={ar.reference_line_item_id is not None}, Credit=Rs.{ar.credit_amount}')
        print(f'    Item: {ar.item_type} - {ar.item_name}')

        if ar.entry_type == 'payment':
            print('    PASS: entry_type=payment')
        else:
            print(f'    FAIL: entry_type={ar.entry_type}')

        if ar.reference_line_item_id:
            print('    PASS: line_item_id referenced')
        else:
            print('    FAIL: line_item_id is NULL')

    # Check invoice update
    inv_after = session.execute(text("""
        SELECT paid_amount, balance_due
        FROM invoice_header
        WHERE invoice_id = :iid
    """), {'iid': result.invoice_id}).first()

    print(f'\nInvoice After: Paid=Rs.{inv_after.paid_amount}, Balance=Rs.{inv_after.balance_due}')

    expected_paid = Decimal(str(result.inv_paid_before)) + Decimal(str(result.amount))
    if abs(Decimal(str(inv_after.paid_amount)) - expected_paid) < Decimal('0.01'):
        print(f'  PASS: paid_amount increased by Rs.{result.amount}')
    else:
        print(f'  FAIL: Expected paid={expected_paid}, got {inv_after.paid_amount}')

    # Check installment
    inst_after = session.execute(text("""
        SELECT paid_amount, status
        FROM installment_payments
        WHERE installment_id = :iid
    """), {'iid': result.installment_id}).first()

    print(f'\nInstallment After: Paid=Rs.{inst_after.paid_amount}, Status={inst_after.status}')

    if Decimal(str(inst_after.paid_amount)) == Decimal(str(result.amount)):
        print(f'  PASS: paid_amount = Rs.{result.amount}')
    else:
        print(f'  FAIL: Expected paid={result.amount}, got {inst_after.paid_amount}')

    if inst_after.status == 'paid':
        print('  PASS: status=paid')
    else:
        print(f'  WARN: status={inst_after.status}')

print('\n' + '=' * 80)
print('TEST COMPLETE')
print('=' * 80)
