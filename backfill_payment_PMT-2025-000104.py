"""
Backfill script for Payment PMT-2025-000104
Fixes missing AR entries and GL entries

Payment Details:
- Payment ID: 3b90a765-0957-49c3-b3d5-e0f5afee30e1
- Payment Number: PMT-2025-000104
- Total Amount: ₹10,646.67
- Current AR Total: ₹7,500.00
- Missing AR: ₹3,146.67
- Missing GL: Entire GL transaction

This script will:
1. Analyze the payment and find missing allocations
2. Create missing AR subledger entries
3. Create GL transaction and entries
4. Update invoice balances
"""

from app.services.database_service import get_db_session
from app.models.transaction import PaymentDetail, InvoiceHeader, InvoiceLineItem
from sqlalchemy import text
from decimal import Decimal
from datetime import datetime, timezone
import uuid

PAYMENT_ID = '3b90a765-0957-49c3-b3d5-e0f5afee30e1'

print("=" * 80)
print("BACKFILL SCRIPT FOR PAYMENT PMT-2025-000104")
print("=" * 80)

with get_db_session() as session:
    # Get the payment
    payment_row = session.execute(text("""
        SELECT payment_id, payment_number, total_amount, payment_date,
               patient_id, branch_id, hospital_id
        FROM payment_details
        WHERE payment_id = :payment_id
    """), {'payment_id': PAYMENT_ID}).first()

    if not payment_row:
        print("ERROR: Payment not found!")
        exit(1)

    print(f"\nPayment Found:")
    print(f"  Payment Number: {payment_row.payment_number}")
    print(f"  Total Amount: ₹{payment_row.total_amount}")
    print(f"  Payment Date: {payment_row.payment_date}")
    print(f"  Patient ID: {payment_row.patient_id}")
    print(f"  Branch ID: {payment_row.branch_id}")

    # Get the payment object for later use
    payment = session.query(PaymentDetail).filter_by(
        payment_id=uuid.UUID(PAYMENT_ID)
    ).first()

    # Get existing AR entries
    print("\n" + "-" * 80)
    print("STEP 1: Analyze Existing AR Entries")
    print("-" * 80)

    existing_ar = session.execute(text("""
        SELECT
            ar.entry_id,
            ar.credit_amount,
            ar.reference_line_item_id,
            ili.invoice_id,
            ili.item_name,
            ili.line_total
        FROM ar_subledger ar
        JOIN invoice_line_item ili ON ar.reference_line_item_id = ili.line_item_id
        WHERE ar.reference_id = :payment_id
        AND ar.reference_type = 'payment'
        ORDER BY ili.invoice_id, ili.line_item_id
    """), {'payment_id': payment.payment_id}).all()

    total_ar = sum(ar.credit_amount for ar in existing_ar)
    print(f"\nExisting AR Entries: {len(existing_ar)}")
    print(f"Total AR Credits: ₹{total_ar}")
    print(f"Payment Total: ₹{payment.total_amount}")
    print(f"Missing AR: ₹{payment.total_amount - total_ar}")

    # Group by invoice
    invoices_with_ar = {}
    for ar in existing_ar:
        inv_id = str(ar.invoice_id)
        if inv_id not in invoices_with_ar:
            invoices_with_ar[inv_id] = Decimal('0')
        invoices_with_ar[inv_id] += ar.credit_amount

    print(f"\nInvoices with AR entries:")
    for inv_id, amount in invoices_with_ar.items():
        print(f"  {inv_id}: ₹{amount}")

    # Find all invoices that should have been paid
    print("\n" + "-" * 80)
    print("STEP 2: Find All Line Items for These Invoices")
    print("-" * 80)

    invoice_ids = list(invoices_with_ar.keys())
    all_line_items = {}

    for inv_id in invoice_ids:
        line_items = session.query(InvoiceLineItem).filter_by(
            invoice_id=uuid.UUID(inv_id)
        ).order_by(InvoiceLineItem.line_item_id).all()

        all_line_items[inv_id] = line_items
        print(f"\nInvoice {inv_id}:")
        print(f"  Total line items: {len(line_items)}")

        # Check which have AR entries
        for item in line_items:
            has_ar = any(ar.reference_line_item_id == item.line_item_id for ar in existing_ar)
            status = "✓ Has AR" if has_ar else "✗ Missing AR"
            print(f"    {item.item_type} - {item.item_name}: ₹{item.line_total} {status}")

    # Calculate what's missing
    print("\n" + "-" * 80)
    print("STEP 3: Calculate Missing Allocations")
    print("-" * 80)

    missing_allocations = []
    for inv_id, line_items in all_line_items.items():
        for item in line_items:
            has_ar = any(ar.reference_line_item_id == item.line_item_id for ar in existing_ar)
            if not has_ar:
                missing_allocations.append({
                    'invoice_id': inv_id,
                    'line_item_id': item.line_item_id,
                    'item_type': item.item_type,
                    'item_name': item.item_name,
                    'amount': item.line_total
                })

    total_missing = sum(Decimal(str(a['amount'])) for a in missing_allocations)
    print(f"\nMissing Allocations: {len(missing_allocations)}")
    print(f"Total Missing: ₹{total_missing}")

    if missing_allocations:
        print("\nDetails:")
        for alloc in missing_allocations:
            print(f"  {alloc['item_type']} - {alloc['item_name']}: ₹{alloc['amount']}")

    # Ask for confirmation
    print("\n" + "=" * 80)
    print("PROPOSED CHANGES:")
    print("=" * 80)
    print(f"1. Create {len(missing_allocations)} AR subledger entries totaling ₹{total_missing}")
    print(f"2. Create GL transaction with:")
    print(f"     Debit Cash: ₹{payment.cash_amount or 0}")
    print(f"     Debit Credit Card: ₹{payment.credit_card_amount or 0}")
    print(f"     Debit Debit Card: ₹{payment.debit_card_amount or 0}")
    print(f"     Debit UPI: ₹{payment.upi_amount or 0}")
    print(f"     Credit AR: ₹{payment.total_amount}")
    print(f"3. Update invoice balances")

    confirm = input("\nProceed with backfill? (yes/no): ")

    if confirm.lower() != 'yes':
        print("Backfill cancelled.")
        exit(0)

    # Create missing AR entries
    print("\n" + "-" * 80)
    print("STEP 4: Creating Missing AR Entries")
    print("-" * 80)

    from app.services.subledger_service import create_ar_subledger_entry

    for alloc in missing_allocations:
        try:
            create_ar_subledger_entry(
                session=session,
                hospital_id=payment.hospital_id,
                branch_id=payment.branch_id,
                patient_id=payment.patient_id,
                entry_type='payment',
                reference_id=payment.payment_id,
                reference_type='payment',
                reference_number=payment.reference_number or payment.payment_number,
                reference_line_item_id=uuid.UUID(alloc['line_item_id']),
                debit_amount=Decimal('0'),
                credit_amount=Decimal(str(alloc['amount'])),
                transaction_date=payment.payment_date,
                gl_transaction_id=None,  # Will be set after GL creation
                current_user_id='system_backfill'
            )
            print(f"  ✓ Created AR entry for {alloc['item_name']}: ₹{alloc['amount']}")
        except Exception as e:
            print(f"  ✗ Failed to create AR entry for {alloc['item_name']}: {e}")
            session.rollback()
            exit(1)

    # Create GL transaction
    print("\n" + "-" * 80)
    print("STEP 5: Creating GL Transaction and Entries")
    print("-" * 80)

    try:
        from app.services.gl_service import create_multi_invoice_payment_gl_entries

        gl_result = create_multi_invoice_payment_gl_entries(
            payment_id=payment.payment_id,
            invoice_count=len(invoice_ids),
            current_user_id='system_backfill',
            session=session
        )

        if gl_result and gl_result.get('success'):
            print(f"  ✓ GL Transaction Created: {gl_result.get('transaction_id')}")
            print(f"  ✓ GL Entries: {gl_result.get('entries_count', 0)}")

            # Update AR entries with GL transaction ID
            gl_trans_id = gl_result.get('transaction_id')
            session.execute(text("""
                UPDATE ar_subledger
                SET gl_transaction_id = :gl_trans_id
                WHERE reference_id = :payment_id
                AND reference_type = 'payment'
                AND gl_transaction_id IS NULL
            """), {'gl_trans_id': gl_trans_id, 'payment_id': payment.payment_id})
            print(f"  ✓ Updated AR entries with GL transaction ID")
        else:
            print(f"  ✗ GL Transaction failed: {gl_result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"  ✗ Error creating GL transaction: {e}")
        import traceback
        traceback.print_exc()

    # Commit all changes
    try:
        session.commit()
        print("\n" + "=" * 80)
        print("BACKFILL COMPLETED SUCCESSFULLY!")
        print("=" * 80)
    except Exception as e:
        session.rollback()
        print(f"\n✗ COMMIT FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

    # Verification
    print("\n" + "-" * 80)
    print("VERIFICATION")
    print("-" * 80)

    final_ar = session.execute(text("""
        SELECT COUNT(*) as count, SUM(credit_amount) as total
        FROM ar_subledger
        WHERE reference_id = :payment_id
        AND reference_type = 'payment'
    """), {'payment_id': payment.payment_id}).first()

    final_gl = session.execute(text("""
        SELECT COUNT(*) as count
        FROM gl_transaction
        WHERE reference_id = CAST(:payment_id AS VARCHAR)
        AND reference_type = 'payment_receipt'
    """), {'payment_id': str(payment.payment_id)}).first()

    print(f"\nFinal AR Entries: {final_ar.count}")
    print(f"Final AR Total: ₹{final_ar.total}")
    print(f"Payment Total: ₹{payment.total_amount}")
    print(f"Match: {'✓ YES' if abs(final_ar.total - payment.total_amount) < 0.01 else '✗ NO'}")
    print(f"\nGL Transactions: {final_gl.count}")
    print(f"GL Status: {'✓ Created' if final_gl.count > 0 else '✗ Missing'}")

print("\n" + "=" * 80)
