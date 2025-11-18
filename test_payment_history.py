#!/usr/bin/env python
"""Test payment history logic for patient invoices"""

from app import create_app, db
from app.models.views import PatientInvoiceView, PatientPaymentReceiptView
from app.models.transaction import ARSubledger
from sqlalchemy import and_

app = create_app()

with app.app_context():
    with db.session() as session:
        # First, check if ANY AR entries exist for patient invoices
        print('=== CHECKING AR SUBLEDGER FOR PATIENT INVOICES ===')
        print()

        # Count all AR entries
        all_ar_entries = session.query(ARSubledger).count()
        print(f'Total AR entries in database: {all_ar_entries}')

        # Count AR entries for invoices
        invoice_ar_entries = session.query(ARSubledger).filter(
            ARSubledger.reference_type == 'invoice'
        ).count()
        print(f'AR entries for invoices: {invoice_ar_entries}')

        # Count AR entries for payments
        payment_ar_entries = session.query(ARSubledger).filter(
            ARSubledger.reference_type == 'payment'
        ).count()
        print(f'AR entries for payments: {payment_ar_entries}')
        print()

        # Check if there are AR entries with PATIENT invoice entry_type
        patient_invoice_ar = session.query(ARSubledger).filter(
            ARSubledger.entry_type == 'patient_invoice'
        ).count()
        print(f'AR entries with entry_type="patient_invoice": {patient_invoice_ar}')

        # Check distinct entry_types
        distinct_entry_types = session.query(ARSubledger.entry_type).distinct().all()
        print(f'Distinct entry_types in AR: {[t[0] for t in distinct_entry_types]}')
        print()

        # Sample some AR entries
        print('=== SAMPLE AR ENTRIES ===')
        sample_entries = session.query(ARSubledger).limit(5).all()
        for entry in sample_entries:
            print(f'Entry Type: {entry.entry_type}, Ref Type: {entry.reference_type}, Ref ID: {entry.reference_id}')
        print()

        # Get a paid invoice
        invoice = session.query(PatientInvoiceView).filter(
            PatientInvoiceView.payment_status == 'paid'
        ).first()

        if invoice:
            print(f'Testing with Invoice: {invoice.invoice_number}')
            print(f'Invoice ID: {invoice.invoice_id}')
            print(f'Payment Status: {invoice.payment_status}')
            print(f'Total: {invoice.total_amount}')
            print(f'Paid: {invoice.paid_amount}')
            print()

            # Step 1: Check AR entries for this invoice
            print('Step 1: AR entries for this invoice')
            ar_invoice_entries = session.query(ARSubledger).filter(
                ARSubledger.reference_type == 'invoice',
                ARSubledger.reference_id == invoice.invoice_id
            ).all()

            print(f'Found {len(ar_invoice_entries)} AR invoice entries')
            for entry in ar_invoice_entries:
                print(f'  Entry Type: {entry.entry_type}')
                print(f'  GL Transaction ID: {entry.gl_transaction_id}')
                print(f'  Debit: {entry.debit_amount}')
                print(f'  Credit: {entry.credit_amount}')
                print(f'  Reference Type: {entry.reference_type}')
                print(f'  Reference ID: {entry.reference_id}')
                print()

            # Step 2: Get gl_transaction_ids
            gl_txn_ids = [e.gl_transaction_id for e in ar_invoice_entries if e.gl_transaction_id]
            print(f'Step 2: GL Transaction IDs: {gl_txn_ids}')
            print()

            if gl_txn_ids:
                # Step 3: Find payment entries with these gl_transaction_ids
                print('Step 3: Payment entries with these GL Transaction IDs')
                payment_entries = session.query(ARSubledger).filter(
                    ARSubledger.entry_type == 'payment',
                    ARSubledger.reference_type == 'payment',
                    ARSubledger.gl_transaction_id.in_(gl_txn_ids)
                ).all()

                print(f'Found {len(payment_entries)} payment entries')
                for entry in payment_entries:
                    print(f'  Payment Reference ID: {entry.reference_id}')
                    print(f'  GL Transaction ID: {entry.gl_transaction_id}')
                    print(f'  Credit Amount: {entry.credit_amount}')
                    print()

                if payment_entries:
                    # Step 4: Get payment IDs
                    payment_ids = list(set([e.reference_id for e in payment_entries]))
                    print(f'Step 4: Payment IDs: {payment_ids}')
                    print()

                    # Step 5: Query payment details
                    print('Step 5: Payment details from view')
                    payments_data = session.query(PatientPaymentReceiptView).filter(
                        PatientPaymentReceiptView.payment_id.in_(payment_ids)
                    ).all()

                    print(f'Found {len(payments_data)} payment records in view')
                    for payment in payments_data:
                        print(f'  Payment ID: {payment.payment_id}')
                        print(f'  Receipt No: {payment.receipt_number}')
                        print(f'  Date: {payment.payment_date}')
                        print(f'  Total Amount: {payment.total_amount}')
                        print(f'  Method: {payment.payment_method_primary}')
                        print()
                else:
                    print('*** NO PAYMENT ENTRIES FOUND - THIS IS THE PROBLEM! ***')
            else:
                print('*** NO GL TRANSACTION IDs FOUND - THIS IS THE PROBLEM! ***')
                print('This means the AR invoice entries do not have gl_transaction_id set')
        else:
            print('No paid invoices found')
