"""
Quick script to update patient payment receipts view
Run this to apply the database view changes
"""

import os
from app.services.database_service import get_db_engine
from sqlalchemy import text

def update_patient_payment_view():
    """Read and execute the patient payment receipts view SQL"""

    # Get the SQL file path
    sql_file = os.path.join(
        os.path.dirname(__file__),
        'app', 'database', 'view scripts',
        'patient_payment_receipts_view v1.0.sql'
    )

    # Read the SQL
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Execute
    engine = get_db_engine()
    with engine.connect() as conn:
        # Execute as a single statement
        conn.execute(text(sql_content))
        conn.commit()
        print("Successfully updated v_patient_payment_receipts view")
        print("   - Added payment_method_primary field")
        print("   - Added date grouping fields (payment_year, payment_month, etc.)")
        print("   - Added refund information fields")
        print("\nPlease restart the application now")

if __name__ == '__main__':
    print("Updating patient payment receipts view...")
    try:
        update_patient_payment_view()
    except Exception as e:
        print(f"Error updating view: {e}")
        import traceback
        traceback.print_exc()
