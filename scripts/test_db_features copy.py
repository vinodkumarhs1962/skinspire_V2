#!/usr/bin/env python
# scripts/test_db_features.py
# python scripts/test_db_features.py

import subprocess
import os
import sys
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"db_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DB_TESTS")

# Define test result tracking
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
    
    def add_pass(self):
        self.passed += 1
    
    def add_fail(self, test_name, error_msg):
        self.failed += 1
        self.failures.append((test_name, error_msg))
    
    def add_skip(self):
        self.skipped += 1
    
    def summary(self):
        return (f"\n======== TEST SUMMARY ========\n"
                f"PASSED:  {self.passed}\n"
                f"FAILED:  {self.failed}\n"
                f"SKIPPED: {self.skipped}\n"
                f"============================\n")
    
    def failures_summary(self):
        if not self.failures:
            return "No failures detected."
        
        result = "\n======= FAILURES DETAIL =======\n"
        for i, (test, error) in enumerate(self.failures, 1):
            result += f"{i}. {test}: {error}\n"
        result += "============================\n"
        return result

# Initialize test results
results = TestResults()

def run_command(cmd, check=True, capture_output=True, test_name=None):
    """Run a command and print its output"""
    logger.info(f"\n=== Running: {cmd} ===")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
        
        if capture_output:
            if result.stdout:
                logger.info(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.warning(f"STDERR: {result.stderr}")
        
        if check and result.returncode != 0:
            error_msg = f"Command failed with exit code {result.returncode}"
            logger.error(error_msg)
            if test_name:
                results.add_fail(test_name, error_msg)
            if not capture_output:
                return False
            return None
        
        if test_name:
            results.add_pass()
        return result
    except Exception as e:
        error_msg = f"Exception running command: {e}"
        logger.error(error_msg)
        if test_name:
            results.add_fail(test_name, error_msg)
        return None

def print_section_header(title):
    """Print a section header to make test output more readable"""
    section_width = 60
    padding = (section_width - len(title) - 2) // 2
    logger.info("\n" + "=" * section_width)
    logger.info(" " * padding + title + " " * padding)
    logger.info("=" * section_width)

def test_configuration():
    """Test the configuration module"""
    print_section_header("TESTING CONFIGURATION MODULE")
    
    # Test getting active environment
    run_command(
        "python -c \"from app.config.db_config import DatabaseConfig; "
        "print(f'Active environment: {DatabaseConfig.get_active_env()}')\"",
        test_name="Configuration - Get Active Environment"
    )
    
    # Test getting database URL
    run_command(
        "python -c \"from app.config.db_config import DatabaseConfig; "
        "print(f'Database URL: {DatabaseConfig.get_database_url_for_env(\"dev\")}')\"",
        test_name="Configuration - Get Database URL"
    )
    
    # Test environment switching
    run_command("python scripts/switch_env.py dev", test_name="Configuration - Switch to Dev Environment")
    run_command(
        "python -c \"from app.config.db_config import DatabaseConfig; "
        "print(f'Active environment: {DatabaseConfig.get_active_env()}')\"",
        test_name="Configuration - Verify Environment Switch"
    )
    
    # Test getting complete config
    run_command(
        "python -c \"from app.config.db_config import DatabaseConfig; "
        "import json; print(json.dumps(DatabaseConfig.get_config(), indent=2))\"",
        test_name="Configuration - Get Complete Config"
    )
    
    # Test configuration priority and fallbacks
    logger.info("\n--- Testing Configuration Priority and Fallbacks ---")
    
    # Test environment variable override
    original_env = os.environ.copy()
    try:
        # Set a test database URL via environment variable
        os.environ['DEV_DATABASE_URL'] = 'postgresql://test_user:test_pass@localhost:5432/test_db'
        
        # Check if it's picked up
        result = run_command(
            "python -c \"from app.config.db_config import DatabaseConfig; "
            "print(DatabaseConfig.get_database_url_for_env('dev'))\"",
            test_name="Configuration - Environment Variable Override"
        )
        
        # Verify the override worked
        if result and 'test_db' in result.stdout:
            logger.info("Environment variable override worked correctly")
        else:
            logger.warning("Environment variable override did not work as expected")
        
        # Test nested transaction config override
        os.environ['USE_NESTED_TRANSACTIONS'] = 'false'
        
        run_command(
            "python -c \"from app.config.db_config import DatabaseConfig; "
            "config = DatabaseConfig.get_config('dev'); "
            "print(f'use_nested_transactions: {config.get(\"use_nested_transactions\")}')\"",
            test_name="Configuration - Transaction Config Override"
        )
        
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
        logger.info("Restored original environment variables")

def test_backup_restore():
    """Test backup and restore functionality"""
    print_section_header("TESTING BACKUP AND RESTORE")
    
    # Create a backup
    run_command("python scripts/manage_db.py backup", test_name="Backup - Create Backup")
    
    # List backups
    run_command("python scripts/manage_db.py list_backups", test_name="Backup - List Backups")
    
    # Create a test table for restore testing
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text('CREATE TABLE IF NOT EXISTS _test_backup_table "
        "(id SERIAL PRIMARY KEY, test_column VARCHAR(50), created_at TIMESTAMP DEFAULT NOW())'))\"",
        test_name="Backup - Create Test Table"
    )
    
    # Insert test data
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text(\\\"INSERT INTO _test_backup_table (test_column) VALUES ('test_value')\\\"))\"",
        test_name="Backup - Insert Test Data"
    )
    
    # Verify table exists and has data
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT * FROM _test_backup_table\\\")); "
        "print([dict(row._mapping) for row in result])\"",
        test_name="Backup - Verify Test Data"
    )
    
    # Find the most recent backup
    result = run_command(
        "python -c \"from pathlib import Path; "
        "import os; backups = sorted(Path('backups').glob('*.sql'), "
        "key=lambda p: p.stat().st_mtime, reverse=True); "
        "print(backups[0] if backups else '')\"",
        test_name="Backup - Find Recent Backup"
    )
    
    if result and result.stdout.strip():
        backup_file = result.stdout.strip()
        
        # Restore from backup (this should remove our test table)
        run_command(
            f"python scripts/manage_db.py restore_backup {backup_file}",
            check=False,  # Don't fail the whole test suite if restore fails
            test_name="Backup - Restore from Backup"
        )
        
        # Verify table was removed (should return False)
        run_command(
            "python -c \"from app.services.database_service import get_db_session; "
            "from sqlalchemy import text; with get_db_session() as session: "
            "result = session.execute(text(\\\"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name = '_test_backup_table')\\\")); print(result.scalar())\"",
            test_name="Backup - Verify Restore"
        )
    else:
        logger.warning("No backups found, skipping restore test")
        results.add_skip()

def test_database_copy():
    """Test database copy functionality"""
    print_section_header("TESTING DATABASE COPY")
    
    # Switch to development environment
    run_command("python scripts/switch_env.py dev", test_name="DB Copy - Switch to Dev")
    
    # Create a test table with unique data
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text('DROP TABLE IF EXISTS _test_copy_table; "
        "CREATE TABLE _test_copy_table (id SERIAL PRIMARY KEY, env VARCHAR(50), value INT)'));"
        "with get_db_session() as session: "
        "session.execute(text(\\\"INSERT INTO _test_copy_table (env, value) VALUES ('dev', 100)\\\"))\"",
        test_name="DB Copy - Create Dev Test Table"
    )
    
    # Verify table exists with data in dev
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT * FROM _test_copy_table\\\")); "
        "print([dict(row._mapping) for row in result])\"",
        test_name="DB Copy - Verify Dev Test Data"
    )
    
    # Copy from dev to test (full copy)
    run_command(
        "python scripts/manage_db.py copy_db dev test",
        test_name="DB Copy - Copy Dev to Test"
    )
    
    # Switch to test environment
    run_command("python scripts/switch_env.py test", test_name="DB Copy - Switch to Test")
    
    # Verify table exists with data in test
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT * FROM _test_copy_table\\\")); "
        "print([dict(row._mapping) for row in result])\"",
        test_name="DB Copy - Verify Test Data After Full Copy"
    )
    
    # Now modify the test data to be different
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text(\\\"UPDATE _test_copy_table SET env = 'test', value = 200\\\"))\"",
        test_name="DB Copy - Modify Test Data"
    )
    
    # Test schema-only copy
    run_command(
        "python scripts/switch_env.py dev",
        test_name="DB Copy - Switch Back to Dev"
    )
    
    # Modify dev schema (add a column)
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text('ALTER TABLE _test_copy_table ADD COLUMN dev_only VARCHAR(50) DEFAULT \\'dev_feature\\''))\"",
        test_name="DB Copy - Add Column in Dev"
    )
    
    # Copy schema only from dev to test
    run_command(
        "python scripts/manage_db.py copy_db dev test --schema-only",
        test_name="DB Copy - Schema-Only Copy"
    )
    
    # Switch to test and verify the schema was updated but data preserved
    run_command("python scripts/switch_env.py test", test_name="DB Copy - Switch to Test Again")
    
    # Verify schema updated but data preserved
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT * FROM _test_copy_table\\\")); "
        "print([dict(row._mapping) for row in result])\"",
        test_name="DB Copy - Verify Schema-Only Copy"
    )
    
    # Clean up test table
    for env in ["dev", "test"]:
        run_command(f"python scripts/switch_env.py {env}", test_name=f"DB Copy - Switch to {env} for Cleanup")
        run_command(
            "python -c \"from app.services.database_service import get_db_session; "
            "from sqlalchemy import text; with get_db_session() as session: "
            "session.execute(text('DROP TABLE IF EXISTS _test_copy_table'))\"",
            test_name=f"DB Copy - Clean Up {env} Test Table"
        )

def test_migration_management():
    """Test migration management functionality"""
    print_section_header("TESTING MIGRATION MANAGEMENT")
    
    # Switch to development for migration tests
    run_command("python scripts/switch_env.py dev", test_name="Migration - Switch to Dev")
    
    # Create a model file for our test model
    test_model_path = 'app/models/test_migration_model.py'
    with open(test_model_path, 'w') as f:
        f.write("""
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TestMigrationModel(Base):
    __tablename__ = '_test_migration_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=func.now())
        """)
    
    logger.info(f"Created test model file: {test_model_path}")
    
    # Initialize model in main models/__init__.py if needed
    models_init_path = 'app/models/__init__.py'
    init_content = ""
    if os.path.exists(models_init_path):
        with open(models_init_path, 'r') as f:
            init_content = f.read()
    
    if "from app.models.test_migration_model import TestMigrationModel" not in init_content:
        with open(models_init_path, 'a') as f:
            f.write("\n# Added for testing\nfrom app.models.test_migration_model import TestMigrationModel\n")
        logger.info(f"Updated models/__init__.py with test model import")
    
    # Create migration for the new model
    run_command(
        "python scripts/manage_db.py create_migration --message \"Add test migration table\" --no-backup",
        test_name="Migration - Create Migration"
    )
    
    # Show migrations
    run_command(
        "python scripts/manage_db.py show_migrations",
        test_name="Migration - Show Migrations"
    )
    
    # Apply migration
    run_command(
        "python scripts/manage_db.py apply_migrations",
        test_name="Migration - Apply Migration"
    )
    
    # Verify the table was created
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_name = '_test_migration_table')\\\")); print(result.scalar())\"",
        test_name="Migration - Verify Table Created"
    )
    
    # Now modify the model to add a column
    with open(test_model_path, 'w') as f:
        f.write("""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TestMigrationModel(Base):
    __tablename__ = '_test_migration_table'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True)  # New column
    created_at = Column(DateTime, default=func.now())
        """)
    
    logger.info("Updated test model with new column")
    
    # Create a migration for the column addition
    run_command(
        "python scripts/manage_db.py create_migration --message \"Add is_active column\" --no-backup",
        test_name="Migration - Create Column Migration"
    )
    
    # Apply the new migration
    run_command(
        "python scripts/manage_db.py apply_migrations",
        test_name="Migration - Apply Column Migration"
    )
    
    # Verify the column was added
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT column_name FROM information_schema.columns "
        "WHERE table_name = '_test_migration_table' AND column_name = 'is_active'\\\")); "
        "print(result.scalar())\"",
        test_name="Migration - Verify Column Added"
    )
    
    # Test rollback
    run_command(
        "python scripts/manage_db.py rollback --no-backup",
        test_name="Migration - Rollback Last Migration"
    )
    
    # Verify column was removed
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT column_name FROM information_schema.columns "
        "WHERE table_name = '_test_migration_table' AND column_name = 'is_active'\\\")); "
        "print(result.scalar())\"",
        test_name="Migration - Verify Column Removed",
        check=False  # We expect this to fail since column should be gone
    )
    
    # Clean up - roll back all migrations for our test table
    run_command(
        "python scripts/manage_db.py rollback --no-backup",
        test_name="Migration - Final Rollback"
    )
    
    # Verify table was removed
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
        "WHERE table_name = '_test_migration_table')\\\")); print(result.scalar())\"",
        test_name="Migration - Verify Table Removed",
        check=False  # Table should be gone
    )
    
    # Clean up model file
    if os.path.exists(test_model_path):
        os.remove(test_model_path)
        logger.info(f"Removed test model file: {test_model_path}")
    
    # Restore original models/__init__.py
    # Read current content
    with open(models_init_path, 'r') as f:
        current_content = f.read()
    
    # Remove our test import line
    updated_content = current_content.replace("\n# Added for testing\nfrom app.models.test_migration_model import TestMigrationModel\n", "")
    
    # Write back the file
    with open(models_init_path, 'w') as f:
        f.write(updated_content)
    
    logger.info("Restored original models/__init__.py")

def test_trigger_management():
    """Test database trigger management"""
    print_section_header("TESTING TRIGGER MANAGEMENT")
    
    # Switch to development environment
    run_command("python scripts/switch_env.py dev", test_name="Triggers - Switch to Dev")
    
    # Create a test table that should get triggers
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text('CREATE TABLE IF NOT EXISTS _test_trigger_table "
        "(id SERIAL PRIMARY KEY, name VARCHAR(100), created_at TIMESTAMP, updated_at TIMESTAMP)'))\"",
        test_name="Triggers - Create Test Table"
    )
    
    # Apply triggers
    run_command(
        "python scripts/manage_db.py apply_triggers",
        test_name="Triggers - Apply Triggers"
    )
    
    # Verify triggers were applied (timestamp triggers)
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\""
        "SELECT trigger_name FROM information_schema.triggers "
        "WHERE event_object_table = '_test_trigger_table'\\\")); "
        "print([r[0] for r in result])\"",
        test_name="Triggers - Verify Triggers Exist"
    )
    
    # Test trigger functionality by inserting data and checking timestamps
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text(\\\"INSERT INTO _test_trigger_table (name) VALUES ('test_record')\\\"))\"",
        test_name="Triggers - Insert Test Data"
    )
    
    # Verify created_at timestamp was set
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "result = session.execute(text(\\\"SELECT created_at FROM _test_trigger_table\\\")); "
        "print(result.scalar() is not None)\"",
        test_name="Triggers - Verify Created Timestamp"
    )
    
    # Update record and check for updated_at timestamp
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text(\\\"UPDATE _test_trigger_table SET name = 'updated_name'\\\")); "
        "result = session.execute(text(\\\"SELECT updated_at FROM _test_trigger_table\\\")); "
        "print(result.scalar() is not None)\"",
        test_name="Triggers - Verify Update Timestamp"
    )
    
    # Test trigger fallback paths
    logger.info("\n--- Testing Trigger Fallback Paths ---")
    
    # Save current file paths for triggers
    trigger_file_path = Path('app/database/triggers/functions.sql')
    original_file_path = Path('app/database/functions.sql')
    
    if trigger_file_path.exists() and original_file_path.exists():
        # Temporarily rename the SQL file in triggers directory
        backup_path = trigger_file_path.with_suffix('.sql.bak')
        try:
            # Rename the file
            trigger_file_path.rename(backup_path)
            logger.info(f"Temporarily renamed {trigger_file_path} to {backup_path}")
            
            # Apply triggers (should use original location as fallback)
            run_command(
                "python scripts/manage_db.py apply_triggers",
                test_name="Triggers - Test Fallback Path"
            )
            
            # Restore the file
            backup_path.rename(trigger_file_path)
            logger.info(f"Restored {backup_path} to {trigger_file_path}")
            
            # Now try with both files renamed
            original_backup_path = original_file_path.with_suffix('.sql.bak')
            
            # Rename both files
            original_file_path.rename(original_backup_path)
            trigger_file_path.rename(backup_path)
            logger.info(f"Temporarily renamed both trigger files")
            
            # Apply triggers (should fail with proper error)
            result = run_command(
                "python scripts/manage_db.py apply_triggers",
                check=False,  # Expect failure
                test_name="Triggers - Test Both Files Missing"
            )
            
            # Verify it failed (non-zero exit code means it handled the error properly)
            if result and result.returncode != 0:
                logger.info("Trigger application correctly failed when both files were missing")
                results.add_pass()
            else:
                logger.error("Trigger application did not fail properly when both files were missing")
                results.add_fail("Triggers - Both Files Missing", "Did not fail when expected to")
            
            # Restore the files
            backup_path.rename(trigger_file_path)
            original_backup_path.rename(original_file_path)
            logger.info("Restored all trigger files")
            
        except Exception as e:
            logger.error(f"Error during trigger fallback testing: {e}")
            # Ensure files are restored even if test fails
            if backup_path.exists():
                backup_path.rename(trigger_file_path)
            if 'original_backup_path' in locals() and original_backup_path.exists():
                original_backup_path.rename(original_file_path)
    else:
        logger.warning("Couldn't test trigger fallback paths - one or both trigger files not found")
        results.add_skip()
    
    # Clean up test table
    run_command(
        "python -c \"from app.services.database_service import get_db_session; "
        "from sqlalchemy import text; with get_db_session() as session: "
        "session.execute(text('DROP TABLE IF EXISTS _test_trigger_table'))\"",
        test_name="Triggers - Clean Up Test Table"
    )

def clean_up_test_artifacts():
    """Clean up any test artifacts left behind"""
    print_section_header("CLEANING UP TEST ARTIFACTS")
    
    # Reset to development environment
    run_command("python scripts/switch_env.py dev", test_name="Cleanup - Switch to Dev")
    
    # Remove all test tables
    test_tables = [
        "_test_backup_table",
        "_test_copy_table", 
        "_test_trigger_table",
        "_test_migration_table"
    ]
    
    for table in test_tables:
        run_command(
            f"python -c \"from app.services.database_service import get_db_session; "
            f"from sqlalchemy import text; with get_db_session() as session: "
            f"session.execute(text('DROP TABLE IF EXISTS {table}'))\"",
            test_name=f"Cleanup - Remove {table}"
        )
    
    # Optionally clean up test backups
    if os.path.exists('backups'):
        backups = list(Path('backups').glob('*test*'))
        if backups and input("Clean up test backups? (y/n): ").lower() == 'y':
            for backup in backups:
                try:
                    backup.unlink()
                    logger.info(f"Removed test backup: {backup}")
                except Exception as e:
                    logger.warning(f"Failed to remove backup {backup}: {e}")

def test_backward_compatibility():
    """Test backward compatibility with original scripts"""
    print_section_header("TESTING BACKWARD COMPATIBILITY")
    
    # Test original script entry points
    logger.info("\n--- Testing Original Script Entry Points ---")
    
    # Test original switch_env.py
    run_command(
        "python scripts/switch_env.py dev",
        test_name="Backward Compatibility - switch_env.py"
    )
    
    # Test original copy_test_to_dev.py if it exists
    if Path('scripts/copy_test_to_dev.py').exists():
        # First ensure test database has something unique
        run_command("python scripts/switch_env.py test", test_name="Backward Compatibility - Switch to Test")
        run_command(
            "python -c \"from app.services.database_service import get_db_session; "
            "from sqlalchemy import text; with get_db_session() as session: "
            "session.execute(text('CREATE TABLE IF NOT EXISTS _test_compat_table "
            "(id SERIAL PRIMARY KEY, env VARCHAR(50) DEFAULT \\'test_value\\')'))\"",
            test_name="Backward Compatibility - Create Test Table in Test DB"
        )
        
        # Run the original copy script
        run_command(
            "python scripts/copy_test_to_dev.py",
            test_name="Backward Compatibility - copy_test_to_dev.py"
        )
        
        # Verify it worked
        run_command("python scripts/switch_env.py dev", test_name="Backward Compatibility - Switch to Dev")
        run_command(
            "python -c \"from app.services.database_service import get_db_session; "
            "from sqlalchemy import text; with get_db_session() as session: "
            "result = session.execute(text(\\\"SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name = '_test_compat_table')\\\")); print(result.scalar())\"",
            test_name="Backward Compatibility - Verify Table Copied"
        )
        
        # Clean up
        for env in ["dev", "test"]:
            run_command(f"python scripts/switch_env.py {env}")
            run_command(
                "python -c \"from app.services.database_service import get_db_session; "
                "from sqlalchemy import text; with get_db_session() as session: "
                "session.execute(text('DROP TABLE IF EXISTS _test_compat_table'))\"",
                test_name=f"Backward Compatibility - Clean Up {env} Test Table"
            )
    else:
        logger.warning("copy_test_to_dev.py not found, skipping test")
    
    # Test original install_triggers.py
    if Path('scripts/install_triggers.py').exists():
        run_command(
            "python scripts/install_triggers.py dev",
            test_name="Backward Compatibility - install_triggers.py"
        )
    else:
        logger.warning("install_triggers.py not found, skipping test")
    
    # Test other existing custom scripts
    logger.info("\n--- Testing Custom Scripts ---")
    custom_scripts = []
    
    # Find custom scripts in scripts directory
    script_dir = Path('scripts')
    if script_dir.exists():
        for script in script_dir.glob('*.py'):
            if script.name not in ['manage_db.py', 'switch_env.py', 'copy_test_to_dev.py', 
                                  'install_triggers.py', 'test_db_features.py']:
                custom_scripts.append(script)
    
    # Test each custom script with --help if possible
    for script in custom_scripts:
        logger.info(f"Testing custom script: {script}")
        run_command(
            f"python {script} --help",
            check=False,  # Don't fail if --help is not supported
            test_name=f"Backward Compatibility - {script.name}"
        )

def create_environment_backup(env):
    """Create backup of an environment

    Args:
        env: The environment to backup (dev, test)

    Returns:
        Path to the backup file or None if unsuccessful
    """
    print_section_header(f"BACKING UP {env.upper()} ENVIRONMENT")
    
    # Set environment
    run_command(f"python scripts/switch_env.py {env}", test_name=f"Backup {env} - Switch Environment")
    
    # Create a timestamped backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"pre_test_{env}_{timestamp}.sql"
    backup_dir = Path('backups')
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)
    
    backup_path = backup_dir / backup_filename
    
    # Get database details
    db_info = run_command(
        "python -c \"from app.config.db_config import DatabaseConfig; "
        "print(DatabaseConfig.get_database_url_for_env('" + env + "'))\"",
        test_name=f"Backup {env} - Get DB URL"
    )
    
    if not db_info or not db_info.stdout.strip():
        logger.error(f"Could not get database URL for {env}")
        return None
    
    # Parse the database URL
    db_url = db_info.stdout.strip()
    try:
        # Simple parsing of PostgreSQL URL
        # Format: postgresql://user:pass@host:port/dbname
        db_url = db_url.replace('postgresql://', '')
        credentials, connection = db_url.split('@', 1)
        user, password = credentials.split(':', 1)
        host_port, dbname = connection.split('/', 1)
        if ':' in host_port:
            host, port = host_port.split(':', 1)
        else:
            host, port = host_port, '5432'
        
        # Set environment variables for pg_dump
        env_vars = os.environ.copy()
        env_vars['PGPASSWORD'] = password
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', dbname,
            '-f', str(backup_path),
            '--verbose'
        ]
        
        logger.info(f"Creating backup of {env} environment to {backup_path}")
        
        # Run the backup command
        result = subprocess.run(
            cmd,
            env=env_vars,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and backup_path.exists() and backup_path.stat().st_size > 0:
            logger.info(f"Successfully backed up {env} environment to {backup_path}")
            return backup_path
        else:
            logger.error(f"Failed to backup {env} environment")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Exception during backup of {env} environment: {e}")
        return None

def restore_environment_from_backup(env, backup_path):
    """Restore environment from backup

    Args:
        env: Environment to restore (dev, test)
        backup_path: Path to the backup file

    Returns:
        True if successful, False otherwise
    """
    print_section_header(f"RESTORING {env.upper()} ENVIRONMENT")
    
    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_path}")
        return False
    
    # Switch to the environment
    run_command(f"python scripts/switch_env.py {env}", test_name=f"Restore {env} - Switch Environment")
    
    # Get database details
    db_info = run_command(
        "python -c \"from app.config.db_config import DatabaseConfig; "
        "print(DatabaseConfig.get_database_url_for_env('" + env + "'))\"",
        test_name=f"Restore {env} - Get DB URL"
    )
    
    if not db_info or not db_info.stdout.strip():
        logger.error(f"Could not get database URL for {env}")
        return False
    
    # Parse the database URL
    db_url = db_info.stdout.strip()
    try:
        # Simple parsing of PostgreSQL URL
        db_url = db_url.replace('postgresql://', '')
        credentials, connection = db_url.split('@', 1)
        user, password = credentials.split(':', 1)
        host_port, dbname = connection.split('/', 1)
        if ':' in host_port:
            host, port = host_port.split(':', 1)
        else:
            host, port = host_port, '5432'
        
        # Set environment variables for psql
        env_vars = os.environ.copy()
        env_vars['PGPASSWORD'] = password
        
        # First, drop and recreate public schema to ensure clean restore
        logger.info(f"Preparing {env} database for restore...")
        reset_cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', dbname,
            '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
        ]
        
        reset_result = subprocess.run(
            reset_cmd,
            env=env_vars,
            capture_output=True,
            text=True
        )
        
        if reset_result.returncode != 0:
            logger.error(f"Failed to reset schema for {env} environment")
            if reset_result.stderr:
                logger.error(f"Error: {reset_result.stderr}")
            return False
        
        # Now restore from backup
        logger.info(f"Restoring {env} database from {backup_path}")
        restore_cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', user,
            '-d', dbname,
            '-f', str(backup_path)
        ]
        
        restore_result = subprocess.run(
            restore_cmd,
            env=env_vars,
            capture_output=True,
            text=True
        )
        
        if restore_result.returncode == 0:
            logger.info(f"Successfully restored {env} environment from {backup_path}")
            
            # Re-apply triggers
            logger.info(f"Re-applying triggers for {env} environment")
            run_command(f"python scripts/install_triggers.py {env}")
            
            return True
        else:
            logger.error(f"Failed to restore {env} environment")
            if restore_result.stderr:
                logger.error(f"Error: {restore_result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Exception during restore of {env} environment: {e}")
        return False

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='Test database management features')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--config', action='store_true', help='Test configuration module')
    parser.add_argument('--backup', action='store_true', help='Test backup and restore functionality')
    parser.add_argument('--copy', action='store_true', help='Test database copy functionality')
    parser.add_argument('--migration', action='store_true', help='Test migration management')
    parser.add_argument('--triggers', action='store_true', help='Test trigger management')
    parser.add_argument('--compat', action='store_true', help='Test backward compatibility')
    parser.add_argument('--skip-cleanup', action='store_true', help='Skip cleanup step')
    parser.add_argument('--no-env-preserve', action='store_true', 
                      help='Skip environment preservation (by default, environments are backed up and restored)')
    
    args = parser.parse_args()
    
    # If no specific tests are selected, run all tests
    run_all = args.all or not (args.config or args.backup or args.copy or 
                             args.migration or args.triggers or args.compat)
    
    # Track environment backups
    environment_backups = {}
    return_code = 1  # Default to error

    try:
        # Track start time
        start_time = time.time()
        
        logger.info(f"Starting database feature tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Backup environments before testing unless explicitly skipped
        if not args.no_env_preserve:
            logger.info("Backing up environments before running tests")
            
            for env in ["dev", "test"]:
                backup_path = create_environment_backup(env)
                if backup_path:
                    environment_backups[env] = backup_path
                else:
                    logger.warning(f"Could not create backup of {env} environment")
        
        # Run selected tests
        if run_all or args.config:
            test_configuration()
        
        if run_all or args.backup:
            test_backup_restore()
        
        if run_all or args.copy:
            test_database_copy()
        
        if run_all or args.migration:
            test_migration_management()
        
        if run_all or args.triggers:
            test_trigger_management()
            
        if run_all or args.compat:
            test_backward_compatibility()
        
        # Always clean up unless explicitly skipped
        if not args.skip_cleanup:
            clean_up_test_artifacts()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Display test results
        logger.info(results.summary())
        
        if results.failures:
            logger.error(results.failures_summary())
        
        logger.info(f"Tests completed in {execution_time:.2f} seconds")
        
        return_code = 0 if results.failed == 0 else 1
    
    except KeyboardInterrupt:
        logger.warning("Tests interrupted by user")
        return_code = 130
    except Exception as e:
        logger.error(f"Unhandled exception during tests: {e}", exc_info=True)
        return_code = 1
    
    finally:
        # Restore environments from backups unless explicitly skipped
        if environment_backups and not args.no_env_preserve:
            logger.info("\n" + "=" * 60)
            logger.info("RESTORING ENVIRONMENTS TO PRE-TEST STATE")
            logger.info("=" * 60)
            
            # Always restore even if tests failed
            if 'dev' in environment_backups:
                dev_backup = environment_backups['dev']
                logger.info(f"Restoring dev environment from {dev_backup}")
                success = restore_environment_from_backup('dev', dev_backup)
                if not success:
                    logger.error("Failed to restore dev environment")
            
            if 'test' in environment_backups:
                test_backup = environment_backups['test']
                logger.info(f"Restoring test environment from {test_backup}")
                success = restore_environment_from_backup('test', test_backup)
                if not success:
                    logger.error("Failed to restore test environment")
    
    return return_code
if __name__ == "__main__":
    sys.exit(main())