"""
Check package payment plan structure and invoice linkage
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.database_service import get_db_session
from sqlalchemy import text

print('=' * 80)
print('PACKAGE PAYMENT PLAN STRUCTURE CHECK')
print('=' * 80)

with get_db_session() as session:
    # Get all package payment plans
    print('\n1. ALL PACKAGE PAYMENT PLANS')
    print('-' * 80)

    plans = session.execute(text("""
        SELECT
            ppp.plan_id,
            ppp.package_name,
            ppp.invoice_id,
            ppp.patient_id,
            ppp.total_amount,
            ppp.paid_amount,
            ppp.status,
            ppp.created_at,
            ih.invoice_number,
            ih.total_amount as invoice_total
        FROM package_payment_plans ppp
        LEFT JOIN invoice_header ih ON ppp.invoice_id = ih.invoice_id
        WHERE ppp.is_deleted = FALSE
        ORDER BY ppp.created_at DESC
        LIMIT 10
    """)).fetchall()

    if not plans:
        print('✗ No package payment plans found')
    else:
        print(f'Found {len(plans)} package payment plan(s)\n')

        for plan in plans:
            print(f'Plan ID: {plan.plan_id}')
            print(f'  Package: {plan.package_name}')
            print(f'  Total Amount: ₹{plan.total_amount}')
            print(f'  Paid Amount: ₹{plan.paid_amount}')
            print(f'  Status: {plan.status}')
            print(f'  Created: {plan.created_at}')

            if plan.invoice_id:
                print(f'  ✓ LINKED TO INVOICE: {plan.invoice_number} (₹{plan.invoice_total})')
            else:
                print(f'  ✗ NO INVOICE LINK!')

            # Check installments
            installments = session.execute(text("""
                SELECT installment_number, amount, paid_amount, status, due_date
                FROM installment_payments
                WHERE plan_id = :plan_id
                ORDER BY installment_number
            """), {'plan_id': plan.plan_id}).fetchall()

            if installments:
                print(f'  Installments: {len(installments)}')
                for inst in installments:
                    print(f'    #{inst.installment_number}: ₹{inst.amount} (Paid: ₹{inst.paid_amount or 0}, Status: {inst.status}, Due: {inst.due_date})')

            print()

print('=' * 80)
