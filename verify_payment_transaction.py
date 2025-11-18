"""
Generic Payment Transaction Verification Script
Verifies the latest payment transaction or a specific payment by ID
Checks all database entries: payment_details, ar_subledger, gl_transaction, gl_entry, installment_payments

Usage:
    python verify_payment_transaction.py                    # Verify latest payment
    python verify_payment_transaction.py <payment_id>       # Verify specific payment
    python verify_payment_transaction.py <payment_number>   # Verify by payment number
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text
from decimal import Decimal
import argparse

def verify_payment(payment_id=None, payment_number=None):
    """
    Verify a payment transaction across all related tables

    Args:
        payment_id: Payment UUID (optional)
        payment_number: Payment number like PMT-2025-000105 (optional)
    """

    with get_db_session() as session:
        # Step 1: Get the payment to verify
        print('=' * 80)
        print('PAYMENT TRANSACTION VERIFICATION')
        print('=' * 80)

        if payment_number:
            print(f'\nSearching for payment: {payment_number}')
            payment = session.execute(text("""
                SELECT payment_id, payment_number, total_amount, cash_amount,
                       credit_card_amount, debit_card_amount, upi_amount,
                       payment_source, invoice_count, workflow_status, payment_date,
                       patient_id, hospital_id, branch_id
                FROM payment_details
                WHERE payment_number = :payment_number
            """), {'payment_number': payment_number}).first()
        elif payment_id:
            print(f'\nSearching for payment ID: {payment_id}')
            payment = session.execute(text("""
                SELECT payment_id, payment_number, total_amount, cash_amount,
                       credit_card_amount, debit_card_amount, upi_amount,
                       payment_source, invoice_count, workflow_status, payment_date,
                       patient_id, hospital_id, branch_id
                FROM payment_details
                WHERE payment_id = :payment_id
            """), {'payment_id': payment_id}).first()
        else:
            print('\nFetching latest payment...')
            payment = session.execute(text("""
                SELECT payment_id, payment_number, total_amount, cash_amount,
                       credit_card_amount, debit_card_amount, upi_amount,
                       payment_source, invoice_count, workflow_status, payment_date,
                       patient_id, hospital_id, branch_id
                FROM payment_details
                ORDER BY created_at DESC
                LIMIT 1
            """)).first()

        if not payment:
            print('❌ ERROR: Payment not found!')
            return False

        print(f'\n✓ Found Payment: {payment.payment_number}')
        print(f'  Payment ID: {payment.payment_id}')
        print(f'  Payment Date: {payment.payment_date}')

        # Step 2: Verify Payment Details
        print('\n' + '=' * 80)
        print('1. PAYMENT DETAILS VERIFICATION')
        print('=' * 80)

        print(f'\nPayment Number: {payment.payment_number}')
        print(f'Total Amount: ₹{payment.total_amount}')
        print(f'\nPayment Method Breakdown:')
        print(f'  Cash: ₹{payment.cash_amount or 0}')
        print(f'  Credit Card: ₹{payment.credit_card_amount or 0}')
        print(f'  Debit Card: ₹{payment.debit_card_amount or 0}')
        print(f'  UPI: ₹{payment.upi_amount or 0}')
        print(f'\nPayment Source: {payment.payment_source}')
        print(f'Invoice Count: {payment.invoice_count}')
        print(f'Workflow Status: {payment.workflow_status}')

        # Verify payment method total
        method_total = (
            (payment.cash_amount or 0) +
            (payment.credit_card_amount or 0) +
            (payment.debit_card_amount or 0) +
            (payment.upi_amount or 0)
        )
        print(f'\nPayment Method Total: ₹{method_total}')
        method_match = abs(method_total - payment.total_amount) < 0.01
        print(f'Total Match: {"✓ PASS" if method_match else "✗ FAIL"}')

        if not method_match:
            print(f'  ERROR: Payment methods (₹{method_total}) ≠ Total (₹{payment.total_amount})')
            print(f'  Difference: ₹{abs(method_total - payment.total_amount)}')

        # Step 3: Verify AR Subledger Entries
        print('\n' + '=' * 80)
        print('2. AR SUBLEDGER VERIFICATION')
        print('=' * 80)

        ar_entries = session.execute(text("""
            SELECT ar.entry_id, ar.entry_type, ar.reference_line_item_id,
                   ar.credit_amount, ar.gl_transaction_id,
                   ili.item_type, ili.item_name, ili.invoice_id
            FROM ar_subledger ar
            LEFT JOIN invoice_line_item ili ON ar.reference_line_item_id = ili.line_item_id
            WHERE ar.reference_id = :payment_id
              AND ar.reference_type = 'payment'
            ORDER BY ar.entry_type, ar.credit_amount
        """), {'payment_id': str(payment.payment_id)}).fetchall()

        print(f'\nTotal AR Entries: {len(ar_entries)}')

        ar_total = Decimal('0')
        invoice_allocations = {}
        package_installment_total = Decimal('0')

        for i, ar in enumerate(ar_entries, 1):
            print(f'\nAR Entry {i}:')
            print(f'  Entry Type: {ar.entry_type}')
            print(f'  Line Item ID: {ar.reference_line_item_id or "NULL (Package Installment)"}')

            if ar.entry_type == 'package_installment':
                print(f'  Item: Package Installment Payment')
                package_installment_total += ar.credit_amount
            else:
                print(f'  Item: {ar.item_type} - {ar.item_name}')
                # Track by invoice
                inv_id = str(ar.invoice_id) if ar.invoice_id else 'Unknown'
                if inv_id not in invoice_allocations:
                    invoice_allocations[inv_id] = Decimal('0')
                invoice_allocations[inv_id] += ar.credit_amount

            print(f'  Credit Amount: ₹{ar.credit_amount}')
            print(f'  GL Transaction: {ar.gl_transaction_id or "NOT LINKED"}')
            ar_total += ar.credit_amount

        print(f'\n{"─" * 80}')
        print(f'AR Summary:')
        print(f'  Invoice Payments: ₹{ar_total - package_installment_total} ({len(invoice_allocations)} invoices)')
        if package_installment_total > 0:
            print(f'  Package Installments: ₹{package_installment_total}')
        print(f'  Total AR Credits: ₹{ar_total}')
        print(f'  Payment Total: ₹{payment.total_amount}')

        ar_match = abs(ar_total - payment.total_amount) < 0.01
        print(f'  AR Match: {"✓ PASS" if ar_match else "✗ FAIL"}')

        if not ar_match:
            print(f'  ERROR: AR total (₹{ar_total}) ≠ Payment total (₹{payment.total_amount})')
            print(f'  Difference: ₹{abs(ar_total - payment.total_amount)}')

        # Step 4: Verify GL Transaction
        print('\n' + '=' * 80)
        print('3. GL TRANSACTION VERIFICATION')
        print('=' * 80)

        gl_trans = session.execute(text("""
            SELECT transaction_id, total_debit, total_credit, transaction_type,
                   transaction_date
            FROM gl_transaction
            WHERE reference_id = CAST(:payment_id AS VARCHAR)
              AND UPPER(transaction_type) = 'PAYMENT_RECEIPT'
        """), {'payment_id': str(payment.payment_id)}).first()

        if gl_trans:
            print(f'\nGL Transaction Found:')
            print(f'  Transaction ID: {gl_trans.transaction_id}')
            print(f'  Transaction Date: {gl_trans.transaction_date}')
            print(f'  Total Debit: ₹{gl_trans.total_debit}')
            print(f'  Total Credit: ₹{gl_trans.total_credit}')

            is_balanced = abs(gl_trans.total_debit - gl_trans.total_credit) < 0.01
            print(f'  Is Balanced: {is_balanced} {"✓" if is_balanced else "✗"}')

            # Get GL Entries
            print(f'\nGL Entries:')
            gl_entries = session.execute(text("""
                SELECT ge.debit_amount, ge.credit_amount, coa.account_name
                FROM gl_entry ge
                JOIN chart_of_accounts coa ON ge.account_id = coa.account_id
                WHERE ge.transaction_id = :trans_id
                ORDER BY ge.debit_amount DESC, ge.credit_amount DESC
            """), {'trans_id': gl_trans.transaction_id}).fetchall()

            total_gl_debit = Decimal('0')
            total_gl_credit = Decimal('0')

            for entry in gl_entries:
                if entry.debit_amount and entry.debit_amount > 0:
                    print(f'  Dr. {entry.account_name}: ₹{entry.debit_amount}')
                    total_gl_debit += entry.debit_amount
                if entry.credit_amount and entry.credit_amount > 0:
                    print(f'  Cr. {entry.account_name}: ₹{entry.credit_amount}')
                    total_gl_credit += entry.credit_amount

            print(f'\n{"─" * 80}')
            print(f'GL Summary:')
            print(f'  Total Debits: ₹{total_gl_debit}')
            print(f'  Total Credits: ₹{total_gl_credit}')
            print(f'  Payment Total: ₹{payment.total_amount}')

            gl_match = abs(gl_trans.total_debit - payment.total_amount) < 0.01
            print(f'  GL Match: {"✓ PASS" if gl_match else "✗ FAIL"}')

            if not gl_match:
                print(f'  ERROR: GL debit (₹{gl_trans.total_debit}) ≠ Payment total (₹{payment.total_amount})')

            if not is_balanced:
                print(f'  ERROR: GL not balanced! Debit: ₹{gl_trans.total_debit}, Credit: ₹{gl_trans.total_credit}')
        else:
            print('\n⚠ WARNING: No GL transaction found!')
            print('  GL posting may be conditional on workflow status')
            if payment.workflow_status != 'approved':
                print(f'  Payment status is "{payment.workflow_status}" - GL may not be posted yet')

        # Step 5: Verify Installment Payments
        print('\n' + '=' * 80)
        print('4. INSTALLMENT PAYMENTS VERIFICATION')
        print('=' * 80)

        installments = session.execute(text("""
            SELECT installment_id, plan_id, installment_number,
                   amount, status
            FROM installment_payments
            WHERE payment_id = :payment_id
        """), {'payment_id': str(payment.payment_id)}).fetchall()

        if installments:
            print(f'\nFound {len(installments)} installment payment(s):')
            installment_total = Decimal('0')

            for inst in installments:
                print(f'\nInstallment #{inst.installment_number}:')
                print(f'  Installment ID: {inst.installment_id}')
                print(f'  Plan ID: {inst.plan_id}')
                print(f'  Installment Amount: ₹{inst.amount}')
                print(f'  Status: {inst.status}')
                installment_total += inst.amount

            print(f'\n{"─" * 80}')
            print(f'Installment Total: ₹{installment_total}')

            # Compare with package AR entries
            if package_installment_total > 0:
                print(f'Package AR Total: ₹{package_installment_total}')
                inst_match = abs(installment_total - package_installment_total) < 0.01
                print(f'Match: {"✓ PASS" if inst_match else "⚠ MISMATCH"}')

                if not inst_match:
                    print(f'  Note: Installment record (₹{installment_total}) may be full amount')
                    print(f'        AR entry (₹{package_installment_total}) is actual payment received')
            else:
                print('⚠ WARNING: No package installment AR entry found!')
        else:
            print('\nNo installment payments found')
            if package_installment_total > 0:
                print(f'⚠ WARNING: Found package AR entry (₹{package_installment_total}) but no installment record!')

        # Step 6: Invoice Summary
        print('\n' + '=' * 80)
        print('5. INVOICE SUMMARY')
        print('=' * 80)

        if invoice_allocations:
            print(f'\nPayment allocated to {len(invoice_allocations)} invoice(s):')

            for inv_id in invoice_allocations.keys():
                invoice = session.execute(text("""
                    SELECT invoice_number, grand_total, invoice_date
                    FROM invoice_header
                    WHERE invoice_id = :invoice_id
                """), {'invoice_id': inv_id}).first()

                if invoice:
                    print(f'\nInvoice: {invoice.invoice_number}')
                    print(f'  Date: {invoice.invoice_date}')
                    print(f'  Grand Total: ₹{invoice.grand_total}')
                    print(f'  Paid from this payment: ₹{invoice_allocations[inv_id]}')

                    # Check if fully paid
                    pct = (invoice_allocations[inv_id] / invoice.grand_total) * 100
                    print(f'  Allocation: {pct:.1f}%')
        else:
            print('\nNo invoice allocations found')
            if package_installment_total > 0:
                print('  This is a package installment-only payment')

        # Final Summary
        print('\n' + '=' * 80)
        print('VERIFICATION SUMMARY')
        print('=' * 80)

        all_pass = True

        print(f'\n✓ Payment Number: {payment.payment_number}')
        print(f'✓ Payment Total: ₹{payment.total_amount}')
        print(f'\nVerification Results:')

        print(f'  1. Payment Methods: {"✓ PASS" if method_match else "✗ FAIL"}')
        if not method_match:
            all_pass = False

        print(f'  2. AR Subledger: {"✓ PASS" if ar_match else "✗ FAIL"}')
        if not ar_match:
            all_pass = False

        if gl_trans:
            print(f'  3. GL Transaction: {"✓ PASS" if gl_match else "✗ FAIL"}')
            if not gl_match:
                all_pass = False
            print(f'  4. GL Balanced: {"✓ PASS" if is_balanced else "✗ FAIL"}')
            if not is_balanced:
                all_pass = False
        else:
            print(f'  3. GL Transaction: ⚠ NOT FOUND')
            print(f'     (May be conditional on approval status)')

        if installments and package_installment_total > 0:
            inst_match = abs(installment_total - package_installment_total) < 0.01
            print(f'  5. Installments: {"✓ PASS" if inst_match else "⚠ MISMATCH (Check notes above)"}')

        print('\n' + '=' * 80)
        if all_pass:
            print('✓✓✓ ALL VERIFICATIONS PASSED ✓✓✓')
        else:
            print('✗✗✗ SOME VERIFICATIONS FAILED - REVIEW ABOVE ✗✗✗')
        print('=' * 80)

        return all_pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Verify payment transaction across all database tables'
    )
    parser.add_argument(
        'identifier',
        nargs='?',
        help='Payment ID (UUID) or Payment Number (PMT-2025-XXXXXX). If not provided, verifies latest payment.'
    )

    args = parser.parse_args()

    # Determine if identifier is payment_id or payment_number
    if args.identifier:
        if args.identifier.startswith('PMT-'):
            verify_payment(payment_number=args.identifier)
        else:
            verify_payment(payment_id=args.identifier)
    else:
        verify_payment()
