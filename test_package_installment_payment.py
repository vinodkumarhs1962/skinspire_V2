"""
Test package installment payment flow
Tests the corrected implementation where package payments are treated as invoice payments
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from app.services.package_payment_service import PackagePaymentService
from sqlalchemy import text
from decimal import Decimal
import uuid

print('=' * 80)
print('PACKAGE INSTALLMENT PAYMENT TEST')
print('=' * 80)

# Find a package with pending installment
with get_db_session() as session:
    print('\n1. FINDING TEST DATA')
    print('-' * 80)

    # Get a plan with pending installment
    result = session.execute(text("""
        SELECT
            ip.installment_id,
            ip.plan_id,
            ip.installment_number,
            ip.amount,
            ip.paid_amount,
            ip.status,
            ppp.package_name,
            ppp.invoice_id,
            ppp.patient_id,
            ih.invoice_number,
            ih.total_amount as invoice_total,
            ih.paid_amount as invoice_paid,
            ih.balance_due as invoice_balance
        FROM installment_payments ip
        JOIN package_payment_plans ppp ON ip.plan_id = ppp.plan_id
        LEFT JOIN invoice_header ih ON ppp.invoice_id = ih.invoice_id
        WHERE ip.status = 'pending'
          AND ppp.is_deleted = FALSE
        ORDER BY ip.created_at DESC
        LIMIT 1
    """)).first()

    if not result:
        print('✗ No pending installments found for testing')
        print('Please create a package payment plan with pending installments first')
        sys.exit(1)

    print(f'✓ Found test installment:')
    print(f'  Installment ID: {result.installment_id}')
    print(f'  Plan ID: {result.plan_id}')
    print(f'  Package: {result.package_name}')
    print(f'  Installment #: {result.installment_number}')
    print(f'  Amount: ₹{result.amount}')
    print(f'  Status: {result.status}')
    print()
    print(f'  Linked Invoice: {result.invoice_number}')
    print(f'  Invoice ID: {result.invoice_id}')
    print(f'  Invoice Total: ₹{result.invoice_total}')
    print(f'  Invoice Paid: ₹{result.invoice_paid}')
    print(f'  Invoice Balance: ₹{result.invoice_balance}')

    # Store for testing
    installment_id = result.installment_id
    plan_id = result.plan_id
    invoice_id = result.invoice_id
    installment_amount = result.amount
    patient_id = result.patient_id
    invoice_paid_before = result.invoice_paid
    invoice_balance_before = result.invoice_balance

print('\n2. SIMULATING INSTALLMENT PAYMENT')
print('-' * 80)

# We'll simulate what billing_views.py does
from app.services.billing_service import record_multi_invoice_payment
from datetime import datetime

# Create payment via invoice payment flow
payment_test_amount = Decimal(str(installment_amount))

print(f'Creating payment of ₹{payment_test_amount} as invoice payment...')

try:
    with get_db_session() as session:
        # Get hospital_id from invoice
        invoice = session.execute(text("""
            SELECT hospital_id, branch_id
            FROM invoice_header
            WHERE invoice_id = :invoice_id
        """), {'invoice_id': invoice_id}).first()

        hospital_id = invoice.hospital_id
        branch_id = invoice.branch_id

        # SCENARIO: Package installment-only payment
        # Treated as invoice payment (using plan's invoice_id)
        invoice_alloc_list = [{
            'invoice_id': str(invoice_id),
            'allocated_amount': payment_test_amount
        }]

        print(f'  Invoice allocation: {invoice_id} → ₹{payment_test_amount}')

        # Call record_multi_invoice_payment (same as billing_views.py)
        result = record_multi_invoice_payment(
            hospital_id=hospital_id,
            invoice_allocations=invoice_alloc_list,
            payment_date=datetime.now().date(),
            cash_amount=payment_test_amount,
            credit_card_amount=Decimal('0'),
            debit_card_amount=Decimal('0'),
            upi_amount=Decimal('0'),
            card_number_last4=None,
            card_type=None,
            upi_id=None,
            reference_number=None,
            recorded_by='7777777777',
            save_as_draft=False,
            approval_threshold=Decimal('100000'),
            session=session  # Use shared session
        )

        if not result or not result.get('success'):
            print(f'✗ Payment creation failed: {result.get("error") if result else "Unknown error"}')
            sys.exit(1)

        payment_id = result['payment_id']
        print(f'✓ Payment created: {payment_id}')

        # Now update installment record (same as billing_views.py)
        print(f'\nUpdating installment record...')

        package_service = PackagePaymentService()
        installment_result = package_service.record_installment_payment(
            installment_id=str(installment_id),
            paid_amount=payment_test_amount,
            payment_id=payment_id,
            hospital_id=str(hospital_id),
            session=session  # Use shared session
        )

        if not installment_result['success']:
            raise Exception(f"Installment update failed: {installment_result.get('error')}")

        print(f'✓ Installment updated: {installment_result["new_status"]}')

        # Commit transaction
        session.commit()
        print('\n✓ Transaction committed successfully')

except Exception as e:
    print(f'\n✗ ERROR: {str(e)}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('\n3. VERIFICATION - ACCOUNTING ENTRIES')
print('-' * 80)

with get_db_session() as session:
    # Check payment record
    payment = session.execute(text("""
        SELECT
            payment_id,
            payment_number,
            invoice_id,
            total_amount,
            payment_source,
            invoice_count
        FROM payment_details
        WHERE payment_id = :payment_id
    """), {'payment_id': payment_id}).first()

    print('Payment Record:')
    print(f'  Payment Number: {payment.payment_number}')
    print(f'  Amount: ₹{payment.total_amount}')
    print(f'  Invoice ID: {payment.invoice_id or "NULL"}')
    print(f'  Payment Source: {payment.payment_source}')
    print(f'  Invoice Count: {payment.invoice_count}')

    if payment.invoice_id and str(payment.invoice_id) == str(invoice_id):
        print(f'  ✓ CORRECT: Payment linked to package invoice')
    else:
        print(f'  ✗ ERROR: Payment not linked to correct invoice')

    # Check AR entries
    print('\nAR Subledger Entries:')
    ar_entries = session.execute(text("""
        SELECT
            entry_type,
            reference_line_item_id,
            credit_amount,
            item_type,
            item_name
        FROM ar_subledger
        WHERE reference_id = :payment_id
          AND reference_type = 'payment'
        ORDER BY created_at
    """), {'payment_id': payment_id}).fetchall()

    if not ar_entries:
        print('  ✗ ERROR: No AR entries found!')
    else:
        for i, ar in enumerate(ar_entries, 1):
            print(f'\n  Entry {i}:')
            print(f'    Type: {ar.entry_type}')
            print(f'    Line Item ID: {ar.reference_line_item_id or "NULL"}')
            print(f'    Credit: ₹{ar.credit_amount}')
            print(f'    Item Type: {ar.item_type or "N/A"}')
            print(f'    Item Name: {ar.item_name or "N/A"}')

            # Validate
            if ar.entry_type == 'payment':
                print(f'    ✓ CORRECT: entry_type = payment')
            else:
                print(f'    ✗ ERROR: entry_type should be "payment", got "{ar.entry_type}"')

            if ar.reference_line_item_id:
                print(f'    ✓ CORRECT: Line item referenced')
            else:
                print(f'    ✗ ERROR: reference_line_item_id is NULL')

            if ar.item_type == 'Package':
                print(f'    ✓ CORRECT: item_type = Package')
            else:
                print(f'    ⚠ WARNING: item_type should be "Package", got "{ar.item_type}"')

    # Check invoice update
    print('\nInvoice Update:')
    invoice_after = session.execute(text("""
        SELECT total_amount, paid_amount, balance_due
        FROM invoice_header
        WHERE invoice_id = :invoice_id
    """), {'invoice_id': invoice_id}).first()

    print(f'  Before: Paid=₹{invoice_paid_before}, Balance=₹{invoice_balance_before}')
    print(f'  After:  Paid=₹{invoice_after.paid_amount}, Balance=₹{invoice_after.balance_due}')

    expected_paid = Decimal(str(invoice_paid_before)) + payment_test_amount
    if abs(Decimal(str(invoice_after.paid_amount)) - expected_paid) < Decimal('0.01'):
        print(f'  ✓ CORRECT: Invoice paid_amount increased by ₹{payment_test_amount}')
    else:
        print(f'  ✗ ERROR: Invoice paid_amount not updated correctly')

print('\n4. VERIFICATION - PACKAGE TRACKING')
print('-' * 80)

with get_db_session() as session:
    # Check installment update
    installment_after = session.execute(text("""
        SELECT
            installment_number,
            amount,
            paid_amount,
            status,
            payment_id
        FROM installment_payments
        WHERE installment_id = :installment_id
    """), {'installment_id': installment_id}).first()

    print('Installment Record:')
    print(f'  Installment #: {installment_after.installment_number}')
    print(f'  Amount: ₹{installment_after.amount}')
    print(f'  Paid Amount: ₹{installment_after.paid_amount}')
    print(f'  Status: {installment_after.status}')
    print(f'  Payment ID: {installment_after.payment_id}')

    if Decimal(str(installment_after.paid_amount)) == payment_test_amount:
        print(f'  ✓ CORRECT: Paid amount = ₹{payment_test_amount}')
    else:
        print(f'  ✗ ERROR: Paid amount incorrect')

    if installment_after.status == 'paid':
        print(f'  ✓ CORRECT: Status = paid')
    else:
        print(f'  ⚠ WARNING: Status = {installment_after.status} (expected "paid")')

    if str(installment_after.payment_id) == str(payment_id):
        print(f'  ✓ CORRECT: Payment ID linked')
    else:
        print(f'  ✗ ERROR: Payment ID not linked')

    # Check plan update
    plan_after = session.execute(text("""
        SELECT paid_amount, total_amount
        FROM package_payment_plans
        WHERE plan_id = :plan_id
    """), {'plan_id': plan_id}).first()

    print('\nPackage Payment Plan:')
    print(f'  Total Amount: ₹{plan_after.total_amount}')
    print(f'  Paid Amount: ₹{plan_after.paid_amount}')
    print(f'  Balance: ₹{Decimal(str(plan_after.total_amount)) - Decimal(str(plan_after.paid_amount))}')

print('\n' + '=' * 80)
print('TEST COMPLETE')
print('=' * 80)
