"""
Find a suitable installment for testing
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text
from decimal import Decimal

print('=' * 80)
print('FINDING TESTABLE PACKAGE INSTALLMENT')
print('=' * 80)

with get_db_session() as session:
    # Get plans with pending installments where invoice has balance
    results = session.execute(text("""
        SELECT
            ip.installment_id,
            ip.plan_id,
            ip.installment_number,
            ip.amount,
            ip.paid_amount,
            ip.status,
            ppp.package_name,
            ppp.invoice_id,
            ih.invoice_number,
            ih.total_amount as invoice_total,
            ih.paid_amount as invoice_paid,
            ih.balance_due as invoice_balance
        FROM installment_payments ip
        JOIN package_payment_plans ppp ON ip.plan_id = ppp.plan_id
        JOIN invoice_header ih ON ppp.invoice_id = ih.invoice_id
        WHERE ip.status = 'pending'
          AND ppp.is_deleted = FALSE
          AND ih.balance_due > 0
        ORDER BY ih.balance_due DESC
        LIMIT 5
    """)).fetchall()

    if not results:
        print('\nNo suitable installments found.')
        print('\nTo create test data:')
        print('1. Create a package invoice (e.g., for ₹5,000)')
        print('2. Set up installment plan (e.g., 2 x ₹2,500)')
        print('3. Do NOT pay the full invoice amount')
        print('4. Leave at least one installment as "pending"')
    else:
        print(f'\nFound {len(results)} testable installment(s):\n')

        for i, r in enumerate(results, 1):
            print(f'{i}. Installment ID: {r.installment_id}')
            print(f'   Package: {r.package_name}')
            print(f'   Installment #{r.installment_number}: ₹{r.amount}')
            print(f'   Invoice: {r.invoice_number}')
            print(f'   Invoice Total: ₹{r.invoice_total}')
            print(f'   Invoice Paid: ₹{r.invoice_paid}')
            print(f'   Invoice Balance: ₹{r.invoice_balance}')

            # Check if installment amount <= invoice balance
            if Decimal(str(r.amount)) <= Decimal(str(r.invoice_balance)):
                print(f'   ✓ TESTABLE: Installment amount (₹{r.amount}) <= Invoice balance (₹{r.invoice_balance})')
            else:
                print(f'   ⚠ PARTIAL: Installment (₹{r.amount}) > Balance (₹{r.invoice_balance})')

            print()

print('=' * 80)
