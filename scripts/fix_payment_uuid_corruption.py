"""
Fix UUID corruption in payment_details table
Run this script to identify and fix corrupted UUID data in payment_details table
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.database_service import get_db_session
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_fix_payment_uuids():
    """Check for and fix corrupted UUIDs in payment_details table"""

    with get_db_session() as session:
        try:
            # Check for corrupted payment_id values (strings instead of UUIDs)
            logger.info("Checking for corrupted UUID values in payment_details...")

            check_query = text("""
                SELECT payment_id, invoice_id, payment_date, total_amount
                FROM payment_details
                WHERE pg_typeof(payment_id::text) = pg_typeof('text'::text)
                   OR payment_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                LIMIT 10;
            """)

            result = session.execute(check_query)
            corrupted_records = result.fetchall()

            if corrupted_records:
                logger.warning(f"Found {len(corrupted_records)} corrupted payment records:")
                for record in corrupted_records:
                    logger.warning(f"  Payment ID: {record[0]}, Invoice: {record[1]}, Amount: {record[3]}")

                response = input("\nDo you want to DELETE these corrupted records? (yes/no): ")
                if response.lower() == 'yes':
                    delete_query = text("""
                        DELETE FROM payment_details
                        WHERE pg_typeof(payment_id::text) = pg_typeof('text'::text)
                           OR payment_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
                    """)
                    session.execute(delete_query)
                    session.commit()
                    logger.info("Corrupted payment records deleted successfully!")
                else:
                    logger.info("Skipping deletion. Payment recording will continue to fail.")
            else:
                logger.info("No corrupted UUID values found in payment_details table")

            # Also check payment_allocation table if it exists
            logger.info("\nChecking for corrupted UUID values in payment_allocation...")

            check_allocation_query = text("""
                SELECT allocation_id, payment_id, invoice_id, amount
                FROM payment_allocation
                WHERE pg_typeof(allocation_id::text) = pg_typeof('text'::text)
                   OR allocation_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                LIMIT 10;
            """)

            try:
                result = session.execute(check_allocation_query)
                corrupted_allocations = result.fetchall()

                if corrupted_allocations:
                    logger.warning(f"Found {len(corrupted_allocations)} corrupted allocation records:")
                    for record in corrupted_allocations:
                        logger.warning(f"  Allocation ID: {record[0]}, Payment: {record[1]}, Amount: {record[3]}")

                    response = input("\nDo you want to DELETE these corrupted allocation records? (yes/no): ")
                    if response.lower() == 'yes':
                        delete_alloc_query = text("""
                            DELETE FROM payment_allocation
                            WHERE pg_typeof(allocation_id::text) = pg_typeof('text'::text)
                               OR allocation_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
                        """)
                        session.execute(delete_alloc_query)
                        session.commit()
                        logger.info("Corrupted allocation records deleted successfully!")
                    else:
                        logger.info("Skipping deletion.")
                else:
                    logger.info("No corrupted UUID values found in payment_allocation table")
            except Exception as e:
                logger.info(f"payment_allocation table check skipped: {str(e)}")

            # Check invoice_header for corrupted UUIDs
            logger.info("\nChecking for corrupted UUID values in invoice_header...")

            check_invoice_query = text("""
                SELECT invoice_id, invoice_number, patient_id, total_amount
                FROM invoice_header
                WHERE pg_typeof(invoice_id::text) = pg_typeof('text'::text)
                   OR invoice_id::text !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                LIMIT 10;
            """)

            result = session.execute(check_invoice_query)
            corrupted_invoices = result.fetchall()

            if corrupted_invoices:
                logger.error(f"Found {len(corrupted_invoices)} corrupted invoice records:")
                for record in corrupted_invoices:
                    logger.error(f"  Invoice ID: {record[0]}, Number: {record[1]}, Amount: {record[3]}")
                logger.error("CRITICAL: Invoice records are corrupted. DO NOT DELETE these!")
            else:
                logger.info("No corrupted UUID values found in invoice_header table")

        except Exception as e:
            logger.error(f"Error checking for corrupted UUIDs: {str(e)}")
            session.rollback()
            raise

if __name__ == '__main__':
    check_and_fix_payment_uuids()
