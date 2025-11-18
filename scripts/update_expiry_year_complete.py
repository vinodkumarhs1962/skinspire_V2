"""
Complete Expiry Year Update Script - All Inward Inventory Tables
=================================================================
Updates expiry dates in ALL tables related to inward inventory:
1. supplier_invoice_line - Supplier invoice line items (PRIMARY)
2. inventory - Inventory movements
3. invoice_line_item - Patient invoice line items (for reference)
4. prescription_invoice_maps - Prescription mappings

Usage:
    python scripts/update_expiry_year_complete.py [--dry-run] [--from-year YYYY] [--to-year YYYY]

Options:
    --dry-run       Show what would be changed without making changes
    --from-year     Source year to change FROM (default: 2025)
    --to-year       Target year to change TO (default: 2026)
"""

import sys
import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import extract

# Add parent directory to path
sys.path.insert(0, '.')

from app.services.database_service import get_db_session
from app.models.transaction import (
    Inventory,
    SupplierInvoiceLine,
    InvoiceLineItem,
    PrescriptionInvoiceMap
)


def update_expiry_year_all_tables(from_year: int = 2025, to_year: int = 2026, dry_run: bool = False):
    """
    Update expiry year across all inward inventory tables
    """
    year_diff = to_year - from_year

    print(f"\n{'='*80}")
    print(f"COMPLETE Inventory Expiry Year Update Script")
    print(f"{'='*80}")
    print(f"From Year: {from_year}")
    print(f"To Year:   {to_year}")
    print(f"Mode:      {'DRY RUN (preview only)' if dry_run else 'LIVE UPDATE'}")
    print(f"{'='*80}\n")

    tables_to_update = [
        {
            'name': 'supplier_invoice_line',
            'model': SupplierInvoiceLine,
            'expiry_field': 'expiry_date',
            'description': 'Supplier Invoice Line Items (INWARD INVENTORY)',
            'primary': True
        },
        {
            'name': 'inventory',
            'model': Inventory,
            'expiry_field': 'expiry',
            'description': 'Inventory Movements',
            'primary': True
        },
        {
            'name': 'invoice_line_item',
            'model': InvoiceLineItem,
            'expiry_field': 'expiry_date',
            'description': 'Patient Invoice Line Items (OUTWARD - for reference)',
            'primary': False
        },
        {
            'name': 'prescription_invoice_maps',
            'model': PrescriptionInvoiceMap,
            'expiry_field': 'expiry_date',
            'description': 'Prescription Invoice Maps (for reference)',
            'primary': False
        }
    ]

    total_updated = 0
    summary = {}

    try:
        with get_db_session() as session:

            for table_info in tables_to_update:
                model = table_info['model']
                expiry_field = getattr(model, table_info['expiry_field'])
                table_name = table_info['name']
                description = table_info['description']
                is_primary = table_info['primary']

                print(f"\n{'='*80}")
                print(f"{'🔴 PRIMARY' if is_primary else '🔵 REFERENCE'}: {description}")
                print(f"Table: {table_name}")
                print(f"{'='*80}")

                # Query records with matching expiry year
                query = session.query(model).filter(
                    extract('year', expiry_field) == from_year
                )

                records = query.all()
                count = len(records)

                if count == 0:
                    print(f"✓ No records found with expiry year {from_year}")
                    summary[table_name] = {'count': 0, 'updated': 0}
                    continue

                print(f"Found {count} record(s) with expiry year {from_year}\n")

                # Show sample records
                print(f"Sample records (first 10):")
                print("-" * 80)

                for i, record in enumerate(records[:10]):
                    expiry_value = getattr(record, table_info['expiry_field'])
                    new_expiry = expiry_value + relativedelta(years=year_diff)

                    # Get medicine name
                    if hasattr(record, 'medicine_name'):
                        medicine_name = record.medicine_name
                    elif hasattr(record, 'item_name'):
                        medicine_name = record.item_name
                    else:
                        medicine_name = 'Unknown'

                    # Get batch
                    if hasattr(record, 'batch_number'):
                        batch = record.batch_number
                    elif hasattr(record, 'batch'):
                        batch = record.batch
                    else:
                        batch = 'N/A'

                    print(f"{i+1}. {medicine_name[:40]:<40} Batch: {batch[:15]:<15} "
                          f"{expiry_value.strftime('%Y-%m-%d')} → {new_expiry.strftime('%Y-%m-%d')}")

                if count > 10:
                    print(f"... and {count - 10} more records")

                print("-" * 80)
                print(f"Total: {count} records in {table_name}\n")

                summary[table_name] = {'count': count, 'updated': 0}

                if not dry_run:
                    # Update records
                    for record in records:
                        old_expiry = getattr(record, table_info['expiry_field'])
                        new_expiry = old_expiry + relativedelta(years=year_diff)
                        setattr(record, table_info['expiry_field'], new_expiry)
                        record.updated_at = datetime.now()
                        summary[table_name]['updated'] += 1

                    total_updated += count

            # Summary
            print(f"\n{'='*80}")
            print("SUMMARY")
            print(f"{'='*80}")
            print(f"{'Table':<35} {'Found':<10} {'Status':<15}")
            print("-" * 80)

            for table_name, stats in summary.items():
                status = f"Updated {stats['updated']}" if not dry_run else "Preview only"
                primary_marker = "🔴" if any(t['name'] == table_name and t['primary'] for t in tables_to_update) else "🔵"
                print(f"{primary_marker} {table_name:<33} {stats['count']:<10} {status:<15}")

            print("-" * 80)
            print(f"Total records across all tables: {sum(s['count'] for s in summary.values())}")
            print(f"{'='*80}\n")

            if dry_run:
                print("✓ DRY RUN MODE - No changes made")
                print("  Remove --dry-run flag to apply changes")
                return 0

            # Confirm before committing
            confirm = input(f"\nCommit {total_updated} updates to database? (yes/no): ").strip().lower()

            if confirm != 'yes':
                print("✗ Update cancelled - rolling back")
                session.rollback()
                return 0

            # Commit changes
            session.commit()

            print(f"\n✓ Successfully updated {total_updated} records")
            print(f"  Expiry year changed from {from_year} to {to_year}")
            print(f"\n🔴 PRIMARY tables (inward inventory): supplier_invoice_line, inventory")
            print(f"🔵 REFERENCE tables (for consistency): invoice_line_item, prescription_invoice_maps")

            return total_updated

    except Exception as e:
        print(f"\n✗ Error updating expiry year: {str(e)}")
        import traceback
        traceback.print_exc()
        return -1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Update expiry year across all inward inventory tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating database'
    )

    parser.add_argument(
        '--from-year',
        type=int,
        default=2025,
        help='Year to change FROM (default: 2025)'
    )

    parser.add_argument(
        '--to-year',
        type=int,
        default=2026,
        help='Year to change TO (default: 2026)'
    )

    args = parser.parse_args()

    # Validate years
    if args.from_year < 2020 or args.from_year > 2030:
        print("Error: from-year must be between 2020 and 2030")
        return 1

    if args.to_year < 2020 or args.to_year > 2030:
        print("Error: to-year must be between 2020 and 2030")
        return 1

    if args.from_year == args.to_year:
        print("Error: from-year and to-year must be different")
        return 1

    # Run the update
    updated_count = update_expiry_year_all_tables(
        from_year=args.from_year,
        to_year=args.to_year,
        dry_run=args.dry_run
    )

    return 0 if updated_count >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
