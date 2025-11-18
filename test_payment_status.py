"""
Quick test to check payment_status values in supplier_invoices_view
"""
import sys
import os
from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.db_config import get_database_url

def check_payment_status():
    """Check actual payment_status values in the database"""
    engine = create_engine(get_database_url())

    with engine.connect() as conn:
        # Get distinct payment_status values
        result = conn.execute(text("""
            SELECT
                payment_status,
                COUNT(*) as count
            FROM supplier_invoices_view
            WHERE is_deleted = false OR is_deleted IS NULL
            GROUP BY payment_status
            ORDER BY payment_status
        """))

        print("\n=== PAYMENT STATUS VALUES ===")
        for row in result:
            print(f"  {row.payment_status}: {row.count} invoices")

        # Get sample invoices with different payment statuses
        result = conn.execute(text("""
            SELECT
                supplier_invoice_number,
                payment_status,
                is_deleted,
                invoice_total_amount,
                paid_amount,
                balance_amount
            FROM supplier_invoices_view
            WHERE is_deleted = false OR is_deleted IS NULL
            ORDER BY invoice_date DESC
            LIMIT 10
        """))

        print("\n=== SAMPLE INVOICES ===")
        for row in result:
            print(f"  {row.supplier_invoice_number}: status={row.payment_status}, "
                  f"deleted={row.is_deleted}, total={row.invoice_total_amount}, "
                  f"paid={row.paid_amount}, balance={row.balance_amount}")

if __name__ == "__main__":
    check_payment_status()
