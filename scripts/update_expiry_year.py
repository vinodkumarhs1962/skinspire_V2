"""
Update Inventory Expiry Year Script
====================================
Changes all inventory records with expiry year 2025 to 2026

Usage:
    python scripts/update_expiry_year.py [--dry-run] [--from-year YYYY] [--to-year YYYY]

Options:
    --dry-run       Show what would be changed without making changes
    --from-year     Source year to change FROM (default: 2025)
    --to-year       Target year to change TO (default: 2026)

Examples:
    # Dry run (preview changes)
    python scripts/update_expiry_year.py --dry-run

    # Update 2025 to 2026
    python scripts/update_expiry_year.py

    # Update 2024 to 2025
    python scripts/update_expiry_year.py --from-year 2024 --to-year 2025
"""

import sys
import argparse
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import extract, func

# Add parent directory to path
sys.path.insert(0, '.')

from app.services.database_service import get_db_session
from app.models.transaction import Inventory


def update_expiry_year(from_year: int = 2025, to_year: int = 2026, dry_run: bool = False):
    """
    Update expiry year for all inventory records

    Args:
        from_year: Year to change FROM
        to_year: Year to change TO
        dry_run: If True, only show what would be changed

    Returns:
        Number of records updated
    """

    year_diff = to_year - from_year

    print(f"\n{'='*70}")
    print(f"Inventory Expiry Year Update Script")
    print(f"{'='*70}")
    print(f"From Year: {from_year}")
    print(f"To Year:   {to_year}")
    print(f"Mode:      {'DRY RUN (preview only)' if dry_run else 'LIVE UPDATE'}")
    print(f"{'='*70}\n")

    try:
        with get_db_session() as session:
            # Find all inventory records with expiry year = from_year
            query = session.query(Inventory).filter(
                extract('year', Inventory.expiry) == from_year
            )

            records = query.all()
            total_records = len(records)

            if total_records == 0:
                print(f"✓ No inventory records found with expiry year {from_year}")
                return 0

            print(f"Found {total_records} inventory record(s) with expiry year {from_year}\n")

            # Group by medicine for summary
            medicine_summary = {}
            for record in records:
                medicine_key = (record.medicine_name, record.batch)
                if medicine_key not in medicine_summary:
                    medicine_summary[medicine_key] = {
                        'count': 0,
                        'old_expiry': record.expiry,
                        'new_expiry': record.expiry + relativedelta(years=year_diff),
                        'current_stock': 0
                    }
                medicine_summary[medicine_key]['count'] += 1
                medicine_summary[medicine_key]['current_stock'] += record.current_stock or 0

            # Display summary
            print("Summary of records to be updated:")
            print("-" * 70)
            print(f"{'Medicine Name':<30} {'Batch':<15} {'Old Expiry':<12} {'New Expiry':<12} {'Stock':<8}")
            print("-" * 70)

            for (medicine_name, batch), info in sorted(medicine_summary.items()):
                print(f"{medicine_name[:29]:<30} {batch[:14]:<15} "
                      f"{info['old_expiry'].strftime('%Y-%m-%d'):<12} "
                      f"{info['new_expiry'].strftime('%Y-%m-%d'):<12} "
                      f"{int(info['current_stock']):<8}")

            print("-" * 70)
            print(f"Total: {len(medicine_summary)} unique medicine-batch combinations")
            print(f"Total: {total_records} inventory transaction records\n")

            if dry_run:
                print("✓ DRY RUN MODE - No changes made")
                print("  Remove --dry-run flag to apply changes")
                return 0

            # Confirm before updating
            confirm = input(f"\nUpdate {total_records} records? (yes/no): ").strip().lower()

            if confirm != 'yes':
                print("✗ Update cancelled")
                return 0

            # Perform the update
            print(f"\nUpdating {total_records} records...")

            updated_count = 0
            for record in records:
                old_expiry = record.expiry
                new_expiry = old_expiry + relativedelta(years=year_diff)

                record.expiry = new_expiry
                record.updated_at = datetime.now()

                updated_count += 1

                if updated_count % 100 == 0:
                    print(f"  Updated {updated_count}/{total_records} records...")

            session.commit()

            print(f"\n✓ Successfully updated {updated_count} inventory records")
            print(f"  Expiry year changed from {from_year} to {to_year}")

            return updated_count

    except Exception as e:
        print(f"\n✗ Error updating expiry year: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Update inventory expiry year',
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
    updated_count = update_expiry_year(
        from_year=args.from_year,
        to_year=args.to_year,
        dry_run=args.dry_run
    )

    return 0 if updated_count >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
