#!/usr/bin/env python
# scripts/db_inspector.py
# Quick tool to list tables, columns, and triggers in the database
# Usage: python scripts/db_inspector.py [dev|test|prod]

import os
import sys
from sqlalchemy import create_engine, text

# Try to get database URL from environment
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check command line args for environment specification
    env_type = 'test'  # Default to test
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['dev', 'test', 'prod']:
        env_type = sys.argv[1].lower()
    
    # Get appropriate database URL
    if env_type == 'dev':
        database_url = os.getenv('DEV_DATABASE_URL', None)
    elif env_type == 'test':
        database_url = os.getenv('TEST_DATABASE_URL', None)
    elif env_type == 'prod':
        database_url = os.getenv('PROD_DATABASE_URL', None)
    
except ImportError:
    database_url = None

# Default value if not found in environment
if not database_url:
    database_url = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'

def inspect_database():
    """Inspect database tables, columns, and triggers"""
    print(f"Connecting to database: {database_url}")
    
    # Create engine
    engine = create_engine(database_url)
    connection = engine.connect()
    
    try:
        print("\n=== DATABASE SCHEMAS ===")
        schemas = connection.execute(text(
            "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname != 'information_schema'"
        )).fetchall()
        
        for schema in schemas:
            print(f"Schema: {schema[0]}")
        
        print("\n=== TABLES BY SCHEMA ===")
        for schema in schemas:
            tables = connection.execute(text(
                f"SELECT tablename FROM pg_tables WHERE schemaname = '{schema[0]}'"
            )).fetchall()
            
            print(f"\nSchema '{schema[0]}' contains {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")
        
        print("\n=== LOOKING FOR USERS TABLE ===")
        users_results = connection.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_name ILIKE '%user%'"
        )).fetchall()
        
        if users_results:
            print(f"Found {len(users_results)} tables matching 'user':")
            for schema, table in users_results:
                print(f"  - {schema}.{table}")
                
                # Show columns for this table
                columns = connection.execute(text(
                    f"SELECT column_name, data_type FROM information_schema.columns "
                    f"WHERE table_schema = '{schema}' AND table_name = '{table}' "
                    f"ORDER BY ordinal_position"
                )).fetchall()
                
                print(f"    Columns ({len(columns)}):")
                for col_name, data_type in columns:
                    print(f"      {col_name} ({data_type})")
                
                # Show triggers for this table
                triggers = connection.execute(text(
                    f"SELECT trigger_name FROM information_schema.triggers "
                    f"WHERE event_object_schema = '{schema}' AND event_object_table = '{table}'"
                )).fetchall()
                
                print(f"    Triggers ({len(triggers)}):")
                for trigger in triggers:
                    print(f"      {trigger[0]}")
        else:
            print("No tables found matching 'user'")
        
        print("\n=== DATABASE FUNCTIONS ===")
        functions = connection.execute(text(
            "SELECT n.nspname AS schema, p.proname AS function_name "
            "FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid "
            "WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname != 'information_schema'"
        )).fetchall()
        
        print(f"Found {len(functions)} functions:")
        # Group by schema
        schema_funcs = {}
        for schema, func in functions:
            if schema not in schema_funcs:
                schema_funcs[schema] = []
            schema_funcs[schema].append(func)
        
        for schema, funcs in schema_funcs.items():
            print(f"\nSchema '{schema}' contains {len(funcs)} functions:")
            # Show functions related to triggers
            trigger_funcs = [f for f in funcs if any(keyword in f for keyword in ['trigger', 'timestamp', 'hash', 'audit'])]
            
            print(f"  Trigger-related functions ({len(trigger_funcs)}):")
            for func in sorted(trigger_funcs):
                print(f"    - {func}")
        
        print("\n=== ALL TRIGGERS ===")
        triggers = connection.execute(text(
            "SELECT trigger_schema, event_object_table, trigger_name "
            "FROM information_schema.triggers "
            "ORDER BY trigger_schema, event_object_table, trigger_name"
        )).fetchall()
        
        print(f"Found {len(triggers)} triggers in total:")
        
        # Group by schema.table
        table_triggers = {}
        for schema, table, trigger in triggers:
            key = f"{schema}.{table}"
            if key not in table_triggers:
                table_triggers[key] = []
            table_triggers[key].append(trigger)
        
        for table, trigger_list in table_triggers.items():
            print(f"\n  {table} has {len(trigger_list)} triggers:")
            for trigger in sorted(trigger_list):
                print(f"    - {trigger}")
        
    finally:
        connection.close()

if __name__ == '__main__':
    inspect_database()