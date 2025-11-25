#!/usr/bin/env python
"""Quick script to check promotion configuration"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config.db_config import DatabaseConfig
from sqlalchemy import create_engine, text
from datetime import date

def check_promotions():
    db_url = DatabaseConfig.get_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # Check for active promotions
        result = conn.execute(text('''
            SELECT id, name, promotion_type, discount_type, discount_value,
                   start_date, end_date, is_active, conditions, applies_to,
                   specific_items
            FROM promotion_campaigns
            WHERE is_active = true
            AND start_date <= :today
            AND end_date >= :today
            ORDER BY created_at DESC
        '''), {"today": date.today()}).fetchall()

        if result:
            print(f"\n✅ Found {len(result)} active promotion(s) for today ({date.today()}):\n")
            for row in result:
                print(f"Campaign: {row[1]}")
                print(f"  ID: {row[0]}")
                print(f"  Type: {row[2]}")
                print(f"  Discount: {row[3]} - {row[4]}%")
                print(f"  Dates: {row[5]} to {row[6]}")
                print(f"  Applies To: {row[9]}")
                print(f"  Specific Items: {row[10]}")
                print(f"  Conditions: {row[8]}")
                print('---')
        else:
            print(f"\n❌ No active promotions found for today ({date.today()})")

            # Check if there are any promotions at all
            all_promos = conn.execute(text('''
                SELECT id, name, start_date, end_date, is_active
                FROM promotion_campaigns
                ORDER BY created_at DESC
                LIMIT 5
            ''')).fetchall()

            if all_promos:
                print("\nRecent promotions (regardless of active status):")
                for row in all_promos:
                    print(f"  - {row[1]} | Active: {row[4]} | {row[2]} to {row[3]}")
            else:
                print("\n⚠️  No promotions exist in database yet")

        # Check Advanced Facial service
        print("\n\nAdvanced Facial Service:")
        service = conn.execute(text('''
            SELECT service_id, service_name, category
            FROM services
            WHERE service_name ILIKE '%advanced%facial%'
            LIMIT 1
        ''')).fetchone()

        if service:
            print(f"  ✅ Found: {service[1]} (ID: {service[0]}, Category: {service[2]})")
        else:
            print("  ❌ Not found in database")

if __name__ == '__main__':
    try:
        check_promotions()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
