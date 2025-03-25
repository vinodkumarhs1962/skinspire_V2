#!/usr/bin/env python
# scripts/db_inspector.py
"""
DEPRECATED: This module is deprecated and will be moved to the core modules
in a future version.

Please use 'python scripts/manage_db.py inspect-db' when available.
This tool is currently retained for its specialized database inspection
capabilities.
"""

import os
import sys
import argparse
import warnings
import logging
from pathlib import Path
from sqlalchemy import create_engine, text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Show deprecation warning
warnings.warn(
    "This script is deprecated. In the future, use 'python scripts/manage_db.py inspect-db' instead.",
    DeprecationWarning,
    stacklevel=2
)

def get_database_url(env):
    """Get database URL for specified environment"""
    from app.core.db_operations.utils import get_db_config, normalize_env_name
    
    # Get DatabaseConfig and normalize environment
    db_config = get_db_config()
    full_env = normalize_env_name(env)
    
    # Get database URL for environment
    return db_config.get_database_url_for_env(full_env)

def inspect_database(env='test'):
    """Inspect database tables, columns, and triggers"""
    try:
        # Get database URL for environment
        database_url = get_database_url(env)
        
        # Mask password for display
        masked_url = database_url
        if '://' in masked_url and '@' in masked_url:
            parts = masked_url.split('@')
            credentials = parts[0].split('://')
            if len(credentials) > 1 and ':' in credentials[1]:
                user_pass = credentials[1].split(':')
                masked_url = f"{credentials[0]}://{user_pass[0]}:***@{parts[1]}"
        
        print(f"Connecting to database: {masked_url}")
        
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
    except Exception as e:
        logger.error(f"Error inspecting database: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Inspect database structure')
    parser.add_argument('env', nargs='?', default='test', choices=['dev', 'test', 'prod'], 
                       help='Environment to inspect (default: test)')
    args = parser.parse_args()
    
    success = inspect_database(args.env)
    sys.exit(0 if success else 1)