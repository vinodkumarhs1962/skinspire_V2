"""
Comprehensive verification of Payment PMT-2025-000105
Checks all database entries: payment_details, ar_subledger, gl_transaction, gl_entry, installment_payments
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text
from decimal import Decimal

PAYMENT_ID = '54fe8db1-a019-4d23-976f-4efd92a020a1'

print('=' * 80)
print('COMPREHENSIVE PAYMENT VERIFICATION - PMT-2025-000105')
print('=' * 80)

with get_db_session() as session:
    # 1. Payment Details
    print('\n1. PAYMENT DETAILS')
    print('-' * 80)
    payment = session.execute(text("""
        SELECT payment_id, payment_number, total_amount, cash_amount,
               credit_card_amount, debit_card_amount, upi_amount,
               payment_source, invoice_count, workflow_status
        FROM payment_details
        WHERE payment_id = :payment_id
    """), {'payment_id': PAYMENT_ID}).first()

    print(f'Payment Number: {payment.payment_number}')
    print(f'Total Amount: ₹{payment.total_amount}')
    print(f'  Cash: ₹{payment.cash_amount or 0}')
    print(f'  Credit Card: ₹{payment.credit_card_amount or 0}')
    print(f'  Debit Card: ₹{payment.debit_card_amount or 0}')
    print(f'  UPI: ₹{payment.upi_amount or 0}')
    print(f'Payment Source: {payment.payment_source}')
    print(f'Invoice Count: {payment.invoice_count}')
    print(f'Workflow Status: {payment.workflow_status}')

    # Verify payment method breakdown
    method_total = (payment.cash_amount or 0) + (payment.credit_card_amount or 0) + (payment.debit_card_amount or 0) + (payment.upi_amount or 0)
    print(f'\nPayment Method Total: ₹{method_total}')
    print(f'Match: {"✓ PASS" if abs(method_total - payment.total_amount) < 0.01 else "✗ FAIL"}')

    # 2. AR Subledger Entries
    print('\n2. AR SUBLEDGER ENTRIES')
    print('-' * 80)
    ar_entries = session.execute(text("""
        SELECT ar.entry_id, ar.entry_type, ar.reference_line_item_id,
               ar.credit_amount, ar.gl_transaction_id,
               ili.item_type, ili.item_name
        FROM ar_subledger ar
        LEFT JOIN invoice_line_item ili ON ar.reference_line_item_id = ili.line_item_id
        WHERE ar.reference_id = :payment_id
          AND ar.reference_type = 'payment'
        ORDER BY ar.entry_type, ar.credit_amount
    """), {'payment_id': PAYMENT_ID}).fetchall()

    ar_total = Decimal('0')
    for i, ar in enumerate(ar_entries, 1):
        print(f'\nAR Entry {i}:')
        print(f'  Entry Type: {ar.entry_type}')
        print(f'  Line Item ID: {ar.reference_line_item_id or "NULL (Package)"}')
        print(f'  Item: {ar.item_type} - {ar.item_name if ar.item_name else "Package Installment"}')
        print(f'  Credit Amount: ₹{ar.credit_amount}')
        print(f'  GL Transaction: {ar.gl_transaction_id}')
        ar_total += ar.credit_amount

    print(f'\nTotal AR Credits: ₹{ar_total}')
    print(f'Payment Total: ₹{payment.total_amount}')
    print(f'Match: {"✓ PASS" if abs(ar_total - payment.total_amount) < 0.01 else "✗ FAIL"}')

    # 3. GL Transaction
    print('\n3. GL TRANSACTION')
    print('-' * 80)
    gl_trans = session.execute(text("""
        SELECT transaction_id, total_debit, total_credit, transaction_type
        FROM gl_transaction
        WHERE reference_id = CAST(:payment_id AS VARCHAR)
          AND transaction_type = 'payment_receipt'
    """), {'payment_id': PAYMENT_ID}).first()

    if gl_trans:
        print(f'Transaction ID: {gl_trans.transaction_id}')
        print(f'Total Debit: ₹{gl_trans.total_debit}')
        print(f'Total Credit: ₹{gl_trans.total_credit}')
        is_balanced = abs(gl_trans.total_debit - gl_trans.total_credit) < 0.01
        print(f'Is Balanced: {is_balanced}')

        # GL Entries
        print('\nGL Entries:')
        gl_entries = session.execute(text("""
            SELECT account_name, debit_amount, credit_amount
            FROM gl_entry
            WHERE transaction_id = :trans_id
            ORDER BY debit_amount DESC, credit_amount DESC
        """), {'trans_id': gl_trans.transaction_id}).fetchall()

        for entry in gl_entries:
            if entry.debit_amount and entry.debit_amount > 0:
                print(f'  Debit {entry.account_name}: ₹{entry.debit_amount}')
            if entry.credit_amount and entry.credit_amount > 0:
                print(f'  Credit {entry.account_name}: ₹{entry.credit_amount}')

        print(f'\nGL Debit Total: ₹{gl_trans.total_debit}')
        print(f'Payment Total: ₹{payment.total_amount}')
        print(f'Match: {"✓ PASS" if abs(gl_trans.total_debit - payment.total_amount) < 0.01 else "✗ FAIL"}')
    else:
        print('✗ No GL transaction found!')

    # 4. Installment Payments
    print('\n4. INSTALLMENT PAYMENTS')
    print('-' * 80)
    installments = session.execute(text("""
        SELECT installment_id, plan_id, installment_number, amount, status
        FROM installment_payments
        WHERE payment_id = :payment_id
    """), {'payment_id': PAYMENT_ID}).fetchall()

    if installments:
        for inst in installments:
            print(f'Installment ID: {inst.installment_id}')
            print(f'Plan ID: {inst.plan_id}')
            print(f'Installment Number: {inst.installment_number}')
            print(f'Amount: ₹{inst.amount}')
            print(f'Status: {inst.status}')
    else:
        print('No installment payment records found')

    # 5. Invoice Summary
    print('\n5. INVOICE SUMMARY')
    print('-' * 80)
    invoices = session.execute(text("""
        SELECT DISTINCT ih.invoice_id, ih.invoice_number, ih.grand_total
        FROM invoice_header ih
        JOIN invoice_line_item ili ON ih.invoice_id = ili.invoice_id
        JOIN ar_subledger ar ON ili.line_item_id = ar.reference_line_item_id
        WHERE ar.reference_id = :payment_id
          AND ar.reference_type = 'payment'
          AND ar.reference_line_item_id IS NOT NULL
        ORDER BY ih.invoice_number
    """), {'payment_id': PAYMENT_ID}).fetchall()

    for inv in invoices:
        # Calculate total paid from this payment for this invoice
        paid_from_this_payment = session.execute(text("""
            SELECT COALESCE(SUM(ar.credit_amount), 0) as amount
            FROM ar_subledger ar
            JOIN invoice_line_item ili ON ar.reference_line_item_id = ili.line_item_id
            WHERE ili.invoice_id = :invoice_id
              AND ar.reference_id = :payment_id
              AND ar.reference_type = 'payment'
        """), {'invoice_id': inv.invoice_id, 'payment_id': PAYMENT_ID}).first()

        print(f'\nInvoice: {inv.invoice_number}')
        print(f'  Grand Total: ₹{inv.grand_total}')
        print(f'  Paid from this payment: ₹{paid_from_this_payment.amount}')

    print('\n' + '=' * 80)
    print('VERIFICATION SUMMARY')
    print('=' * 80)
    print(f'✓ Payment Total: ₹{payment.total_amount}')
    print(f'  Payment Methods Total: ₹{method_total} - {"✓ PASS" if abs(method_total - payment.total_amount) < 0.01 else "✗ FAIL"}')
    print(f'  AR Total: ₹{ar_total} - {"✓ PASS" if abs(ar_total - payment.total_amount) < 0.01 else "✗ FAIL"}')
    if gl_trans:
        is_balanced = abs(gl_trans.total_debit - gl_trans.total_credit) < 0.01
        print(f'  GL Total: ₹{gl_trans.total_debit} - {"✓ PASS" if abs(gl_trans.total_debit - payment.total_amount) < 0.01 else "✗ FAIL"}')
        print(f'  GL Balanced: {is_balanced} - {"✓ PASS" if is_balanced else "✗ FAIL"}')
    print('=' * 80)
