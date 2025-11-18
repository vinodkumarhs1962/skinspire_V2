from app.services.database_service import get_db_session
from sqlalchemy import text

print("=" * 80)
print("PAYMENT DATABASE ENTRIES CHECK")
print("=" * 80)

# Get the latest payment ID
with get_db_session() as session:
    payment = session.execute(text("""
        SELECT payment_id, payment_number, total_amount, payment_date
        FROM payment_details
        ORDER BY created_at DESC
        LIMIT 1
    """)).first()

    if not payment:
        print("No payments found!")
        exit()

    payment_id = payment.payment_id
    print(f"\nChecking entries for Payment: {payment.payment_number}")
    print(f"Payment ID: {payment_id}")
    print(f"Amount: {payment.total_amount}")
    print(f"Date: {payment.payment_date}")
    print("=" * 80)

    # Check AR Subledger
    print("\n1. AR SUBLEDGER ENTRIES")
    print("-" * 80)
    ar_count = session.execute(text("""
        SELECT COUNT(*) as count,
               SUM(credit_amount) as total_credit,
               SUM(debit_amount) as total_debit
        FROM ar_subledger
        WHERE reference_id = :payment_id
        AND reference_type = 'payment'
    """), {'payment_id': payment_id}).first()

    if ar_count.count > 0:
        print(f"Status: FOUND ({ar_count.count} entries)")
        print(f"Total Credit: {ar_count.total_credit}")
        print(f"Total Debit: {ar_count.total_debit}")

        # Show details
        ar_details = session.execute(text("""
            SELECT entry_id, transaction_date, credit_amount, debit_amount,
                   reference_line_item_id, entry_type
            FROM ar_subledger
            WHERE reference_id = :payment_id
            AND reference_type = 'payment'
            ORDER BY transaction_date
        """), {'payment_id': payment_id}).all()

        for idx, ar in enumerate(ar_details, 1):
            print(f"\n  Entry {idx}:")
            print(f"    Entry ID: {ar.entry_id}")
            print(f"    Type: {ar.entry_type}")
            print(f"    Date: {ar.transaction_date}")
            print(f"    Credit: {ar.credit_amount}")
            print(f"    Debit: {ar.debit_amount}")
            print(f"    Line Item ID: {ar.reference_line_item_id}")
    else:
        print("Status: NOT FOUND - NO AR ENTRIES!")

    # Check GL Transaction
    print("\n\n2. GL TRANSACTION")
    print("-" * 80)
    gl_trans = session.execute(text("""
        SELECT transaction_id, transaction_date, transaction_type,
               total_debit, total_credit
        FROM gl_transaction
        WHERE reference_id = :payment_id
        AND reference_type = 'payment_receipt'
    """), {'payment_id': payment_id}).first()

    if gl_trans:
        print(f"Status: FOUND")
        print(f"Transaction ID: {gl_trans.transaction_id}")
        print(f"Type: {gl_trans.transaction_type}")
        print(f"Date: {gl_trans.transaction_date}")
        print(f"Total Debit: {gl_trans.total_debit}")
        print(f"Total Credit: {gl_trans.total_credit}")

        # Check GL Entries
        print("\n3. GL ENTRIES")
        print("-" * 80)
        gl_entries = session.execute(text("""
            SELECT entry_id, account_id, debit_amount, credit_amount
            FROM gl_entry
            WHERE transaction_id = :transaction_id
            ORDER BY entry_id
        """), {'transaction_id': gl_trans.transaction_id}).all()

        if gl_entries:
            print(f"Status: FOUND ({len(gl_entries)} entries)")
            for idx, entry in enumerate(gl_entries, 1):
                print(f"\n  Entry {idx}:")
                print(f"    Entry ID: {entry.entry_id}")
                print(f"    Account ID: {entry.account_id}")
                print(f"    Debit: {entry.debit_amount or 0}")
                print(f"    Credit: {entry.credit_amount or 0}")
        else:
            print("Status: NOT FOUND - NO GL ENTRIES!")
    else:
        print("Status: NOT FOUND - NO GL TRANSACTION!")
        print("\n3. GL ENTRIES")
        print("-" * 80)
        print("Status: NOT FOUND - No GL transaction exists")

    # Check Package Payment Plans
    print("\n\n4. PACKAGE PAYMENT PLANS")
    print("-" * 80)
    package_plans = session.execute(text("""
        SELECT plan_id, package_id, total_amount, paid_amount
        FROM package_payment_plans
        WHERE patient_id = (
            SELECT patient_id FROM payment_details WHERE payment_id = :payment_id
        )
    """), {'payment_id': payment_id}).all()

    if package_plans:
        print(f"Status: FOUND ({len(package_plans)} plans)")
        for idx, plan in enumerate(package_plans, 1):
            print(f"\n  Plan {idx}:")
            print(f"    Plan ID: {plan.plan_id}")
            print(f"    Package ID: {plan.package_id}")
            print(f"    Total: {plan.total_amount}")
            print(f"    Paid: {plan.paid_amount}")
    else:
        print("Status: NOT FOUND - No package plans for this patient")

    # Check Installment Payments
    print("\n\n5. INSTALLMENT PAYMENTS")
    print("-" * 80)
    installments = session.execute(text("""
        SELECT installment_id, plan_id, payment_id, amount
        FROM installment_payments
        WHERE payment_id = :payment_id
    """), {'payment_id': payment_id}).all()

    if installments:
        print(f"Status: FOUND ({len(installments)} installments)")
        for idx, inst in enumerate(installments, 1):
            print(f"\n  Installment {idx}:")
            print(f"    Installment ID: {inst.installment_id}")
            print(f"    Plan ID: {inst.plan_id}")
            print(f"    Amount: {inst.amount}")
    else:
        print("Status: NOT FOUND - No installment payments")

    # Check Invoice Allocations (from AR subledger)
    print("\n\n6. INVOICE ALLOCATIONS")
    print("-" * 80)
    invoices = session.execute(text("""
        SELECT DISTINCT ili.invoice_id, ih.invoice_number, ih.total_amount,
               SUM(ar.credit_amount) as allocated_amount
        FROM ar_subledger ar
        JOIN invoice_line_item ili ON ar.reference_line_item_id = ili.line_item_id
        JOIN invoice_header ih ON ili.invoice_id = ih.invoice_id
        WHERE ar.reference_id = :payment_id
        AND ar.reference_type = 'payment'
        GROUP BY ili.invoice_id, ih.invoice_number, ih.total_amount
    """), {'payment_id': payment_id}).all()

    if invoices:
        print(f"Status: FOUND ({len(invoices)} invoices)")
        for idx, inv in enumerate(invoices, 1):
            print(f"\n  Invoice {idx}:")
            print(f"    Invoice Number: {inv.invoice_number}")
            print(f"    Invoice Total: {inv.total_amount}")
            print(f"    Allocated Amount: {inv.allocated_amount}")
    else:
        print("Status: NOT FOUND - No invoice allocations")

    # Check Advance Adjustments
    print("\n\n7. ADVANCE ADJUSTMENTS")
    print("-" * 80)
    advance = session.execute(text("""
        SELECT adjustment_id, advance_id, adjusted_amount
        FROM advance_adjustments
        WHERE payment_id = :payment_id
    """), {'payment_id': payment_id}).all()

    if advance:
        print(f"Status: FOUND ({len(advance)} adjustments)")
        for idx, adj in enumerate(advance, 1):
            print(f"\n  Adjustment {idx}:")
            print(f"    Adjustment ID: {adj.adjustment_id}")
            print(f"    Advance ID: {adj.advance_id}")
            print(f"    Amount: {adj.adjusted_amount}")
    else:
        print("Status: NOT FOUND - No advance adjustments")

    # Summary
    print("\n\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    has_entries = []
    missing_entries = []

    if ar_count.count > 0:
        has_entries.append(f"AR Subledger ({ar_count.count} entries)")
    else:
        missing_entries.append("AR Subledger")

    if gl_trans:
        has_entries.append("GL Transaction")
        if gl_entries:
            has_entries.append(f"GL Entries ({len(gl_entries)} entries)")
        else:
            missing_entries.append("GL Entries")
    else:
        missing_entries.append("GL Transaction")
        missing_entries.append("GL Entries")

    if package_plans:
        has_entries.append(f"Package Plans ({len(package_plans)} plans)")

    if installments:
        has_entries.append(f"Installment Payments ({len(installments)} installments)")

    if invoices:
        has_entries.append(f"Invoice Allocations ({len(invoices)} invoices)")
    else:
        missing_entries.append("Invoice Allocations")

    if advance:
        has_entries.append(f"Advance Adjustments ({len(advance)} adjustments)")

    print("\nTables WITH entries:")
    if has_entries:
        for item in has_entries:
            print(f"  + {item}")
    else:
        print("  - None")

    print("\nTables WITHOUT entries (MISSING):")
    if missing_entries:
        for item in missing_entries:
            print(f"  - {item} ** ISSUE **")
    else:
        print("  - None (All good!)")

    print("\n" + "=" * 80)
