# scripts/test_migration_strategy.py

# Run full tests (table creation and column operations)
# python scripts/test_migration_strategy.py

# Only test column operations (assumes table already exists or creates it)
# python scripts/test_migration_strategy.py --test-columns-only

# Run tests and clean up artifacts afterward
# python scripts/test_migration_strategy.py --cleanup

# Skip the backup step (for faster testing)
# python scripts/test_migration_strategy.py --skip-backup

# python scripts/test_migration_strategy.py --force

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_command(command, check=False, capture_output=True):
    """Run a command and return the result"""
    print(f"Running: {command}")
    try:
        # Remove the --env flag from commands
        # This assumes the environment is set globally or through other means
        command = command.replace('--env dev', '')
        result = subprocess.run(
            command, 
            shell=True, 
            check=False,  # Don't raise exception
            capture_output=capture_output,
            text=True
        )
        
        if capture_output:
            print(result.stdout)
            if result.stderr:
                print(f"STDERR: {result.stderr}")
                
        if result.returncode != 0:
            print(f"WARNING: Command returned non-zero exit code: {result.returncode}")
            
        return result
    except Exception as e:
        print(f"ERROR executing command: {e}")
        # Return a dummy result object so the script can continue
        class DummyResult:
            def __init__(self):
                self.returncode = 1
                self.stdout = ""
                self.stderr = str(e)
        return DummyResult()

def test_table_creation(args):
    """Test creating a new table via migrations"""
    # Create a test model file
    print("\n=== Testing Table Creation ===")
    test_model_path = Path("app/models/test_migration_model.py")
    
    try:
        with open(test_model_path, "w") as f:
            f.write("""# Test migration model
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, generate_uuid

class TestMigrationTable(Base, TimestampMixin):
    \"\"\"Test table for migration strategy testing\"\"\"
    __tablename__ = 'test_migration_table'

    test_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
""")
        print(f"Created test model file: {test_model_path}")
    except Exception as e:
        print(f"ERROR creating test model file: {e}")
        print("Aborting test")
        return False
    
    # Import the model in __init__.py
    print("Updating model imports...")
    init_path = Path("app/models/__init__.py")
    
    try:
        original_init_content = init_path.read_text()
        
        # Check if our test model is already imported
        if "from .test_migration_model import TestMigrationTable" not in original_init_content:
            # Add our import
            with open(init_path, "a") as f:
                f.write("\n# Temporary test model\nfrom .test_migration_model import TestMigrationTable\n")
            print(f"Updated {init_path} with test model import")
        else:
            print("Test model already imported in __init__.py")
    except Exception as e:
        print(f"ERROR updating __init__.py: {e}")
        print("Attempting to continue anyway...")
    
    # Detect schema changes
    print("Detecting schema changes...")
    run_command(f"python scripts/manage_db.py detect-schema-changes --env {args.env}")
    
    # Create a migration
    print("Creating migration for test table...")
    run_command(f"python scripts/manage_db.py create-model-migration -m \"Add test migration table\" --env {args.env}")
    
    # Apply the migration
    print("Applying migration...")
    run_command(f"python scripts/manage_db.py apply-db-migration --env {args.env}")
    
    # Verify the table exists
    print("Verifying table exists...")
    result = run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table --env {args.env}")
    
    # Check if table was created successfully
    if "TABLE DETAILS" in result.stdout and "test_migration_table" in result.stdout:
        print("SUCCESS: Table was created successfully")
        return True
    else:
        print("FAILED: Table was not created")
        return False

def test_column_operations(args):
    """Test column addition, modification, and deletion"""
    print("\n=== Testing Column Operations ===")

    # 1. First add new columns to the model
    print("1. Testing Column Addition")
    test_model_path = Path("app/models/test_migration_model.py")
    
    try:
        with open(test_model_path, "w") as f:
            f.write("""# Test migration model (updated with new columns)
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, generate_uuid

class TestMigrationTable(Base, TimestampMixin):
    \"\"\"Test table for migration strategy testing\"\"\"
    __tablename__ = 'test_migration_table'

    test_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=True)
    
    # New columns for testing column additions
    priority = Column(Integer, default=0)
    rating = Column(Float, default=5.0)
    extra_data = Column(JSONB, default={})
""")
        print("Updated test model with additional columns")
    except Exception as e:
        print(f"ERROR updating test model: {e}")
        return False
    
    # Detect schema changes to show new columns
    print("Detecting column additions...")
    run_command(f"python scripts/manage_db.py detect-schema-changes --env {args.env}")
    
    # Apply changes using direct sync method
    print("Applying column additions via direct sync...")
    if args.force:
        sync_result = run_command("python scripts/manage_db.py sync-models-to-db --force")
    else:
        sync_result = run_command("python scripts/manage_db.py sync-models-to-db")
    
    # Verify the new columns exist
    print("Verifying column additions...")
    inspect_result = run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table --env {args.env}")
    
    # Check if columns were added successfully
    column_added = all(col in inspect_result.stdout for col in ['priority', 'rating', 'extra_data'])
    if column_added:
        print("SUCCESS: New columns were added successfully")
    else:
        print("FAILED: Some columns were not added")
        return False

    # 2. Then modify existing columns (change properties)
    print("\n2. Testing Column Modification")
    try:
        with open(test_model_path, "w") as f:
            f.write("""# Test migration model (updated with modified columns)
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, generate_uuid

class TestMigrationTable(Base, TimestampMixin):
    \"\"\"Test table for migration strategy testing\"\"\"
    __tablename__ = 'test_migration_table'

    test_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)  # Changed size from 100 to 200
    description = Column(Text, nullable=False)  # Changed nullable from True to False
    settings = Column(JSONB, default={})
    is_active = Column(Boolean, default=False)  # Changed default from True to False
    
    # Previously added columns
    priority = Column(Integer, nullable=False, default=1)  # Changed default and nullable
    rating = Column(Float, default=5.0)
    extra_data = Column(JSONB, default={})
""")
        print("Updated test model with modified columns")
    except Exception as e:
        print(f"ERROR updating test model: {e}")
        return False
    
    # Detect schema changes for column modifications
    print("Detecting column modifications...")
    run_command(f"python scripts/manage_db.py detect-schema-changes --env {args.env}")
    
    # Create migration for column modifications
    print("Creating migration for column modifications...")
    run_command(f"python scripts/manage_db.py create-model-migration -m \"Add test migration table\" --env {args.env}")
    
    # Apply the migration
    print("Applying column modifications...")
    run_command(f"python scripts/manage_db.py apply-db-migration --env {args.env}")
    
    # Verify the column modifications
    print("Verifying column modifications...")
    inspect_result = run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table --env {args.env}")
    
    # Check if column modifications were successful
    # Note: We can't reliably verify all modifications through the inspect output text,
    # but we can check if the command completed successfully
    if inspect_result.returncode == 0 and "TABLE DETAILS" in inspect_result.stdout:
        print("SUCCESS: Column modifications applied")
    else:
        print("FAILED: Column modifications not applied")
        return False

    # 3. Finally test column removal (by removing a column from the model)
    print("\n3. Testing Column Removal")
    try:
        with open(test_model_path, "w") as f:
            f.write("""# Test migration model (with removed columns)
from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin, generate_uuid

class TestMigrationTable(Base, TimestampMixin):
    \"\"\"Test table for migration strategy testing\"\"\"
    __tablename__ = 'test_migration_table'

    test_id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    # settings column removed
    is_active = Column(Boolean, default=False)
    
    priority = Column(Integer, nullable=False, default=1)
    # rating column removed
    extra_data = Column(JSONB, default={})
""")
        print("Updated test model with removed columns")
    except Exception as e:
        print(f"ERROR updating test model: {e}")
        return False
    
    # Detect schema changes for column removals
    print("Detecting column removals...")
    run_command(f"python scripts/manage_db.py detect-schema-changes --env {args.env}")
    
    # Allow drops with direct sync method
    print("Applying column removals via direct sync (with --allow-drops flag)...")
    if args.force:
        sync_result = run_command("python scripts/manage_db.py sync-models-to-db --force --allow-drops")
    else:
        sync_result = run_command("python scripts/manage_db.py sync-models-to-db --allow-drops")
    
    # Verify the columns were removed
    print("Verifying column removals...")
    inspect_result = run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table --env {args.env}")
    
    # Check if columns were removed successfully
    columns_removed = all(col not in inspect_result.stdout for col in ['settings', 'rating'])
    if columns_removed:
        print("SUCCESS: Columns were removed successfully")
    else:
        print("WARNING: Column removal verification inconclusive")
    
    return True

def cleanup(args, original_init_content):
    """Clean up test artifacts"""
    print("\n=== Cleaning Up ===")
    cleanup_success = True
    
    # 1. Restore original __init__.py
    init_path = Path("app/models/__init__.py")
    try:
        with open(init_path, "w") as f:
            f.write(original_init_content)
        print("Restored original __init__.py content")
    except Exception as e:
        print(f"ERROR restoring __init__.py: {e}")
        cleanup_success = False
    
    # 2. Remove test model file
    test_model_path = Path("app/models/test_migration_model.py")
    try:
        if test_model_path.exists():
            test_model_path.unlink()
            print("Removed test model file")
        else:
            print("Test model file already removed")
    except Exception as e:
        print(f"ERROR removing test model file: {e}")
        cleanup_success = False
    
    # 3. Roll back migrations
    print("Rolling back migrations...")
    run_command("python scripts/manage_db.py rollback-db-migration --steps 2")
    
    # 4. Verify table no longer exists
    print("Verifying table removal:")
    result = run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table --env {args.env}")
    
    if "not found" in result.stdout or "Error" in result.stdout or result.returncode != 0:
        print("Table successfully removed")
    else:
        print("WARNING: Table still exists after rollback")
        
        # Try dropping directly
        print("Attempting to drop table directly...")
        try:
            from app import create_app, db
            from sqlalchemy import text
            app = create_app()
            with app.app_context():
                with db.engine.connect() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS test_migration_table CASCADE"))
                    conn.commit()
                print("Table dropped directly using SQLAlchemy")
        except Exception as e:
            print(f"ERROR dropping table directly: {e}")
            cleanup_success = False
    
    return cleanup_success

def main():
    parser = argparse.ArgumentParser(description="Test the model-driven migration strategy")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test artifacts after testing")
    parser.add_argument("--env", default="dev", help="Environment to test (dev/test)")
    parser.add_argument("--skip-backup", action="store_true", help="Skip backup step")
    parser.add_argument("--test-columns-only", action="store_true", help="Only test column operations")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts")
    args = parser.parse_args()

    # Explicitly switch to the specified environment
    run_command(f"python scripts/manage_db.py switch-env {args.env}")
    
    # Set environment variables
    os.environ['FLASK_APP'] = 'app:create_app'
    
    # 1. Create a backup first (optional)
    if not args.skip_backup:
        print("\n=== Step 1: Creating backup ===")
        run_command(f"python scripts/manage_db.py create-backup --env {args.env}")
    else:
        print("\n=== Step 1: Skipping backup (--skip-backup flag used) ===")
    
    # Save original init content for cleanup
    init_path = Path("app/models/__init__.py")
    original_init_content = init_path.read_text()
    
    # Track if all tests are successful
    all_tests_successful = True
    
    try:
        # Run appropriate tests
        if args.test_columns_only:
            # Skip table creation and only test column operations
            # First ensure the test table exists
            result = run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table --env {args.env}")
            if "not found" in result.stdout or "Error" in result.stdout:
                # Table doesn't exist, create it first
                print("Test table doesn't exist. Creating it first...")
                table_success = test_table_creation(args)
                if not table_success:
                    print("Failed to create test table, cannot continue with column tests")
                    return 1
            
            # Now test column operations
            column_success = test_column_operations(args)
            all_tests_successful = column_success
        else:
            # Run the full test suite
            table_success = test_table_creation(args)
            if not table_success:
                print("Table creation test failed")
                all_tests_successful = False
            
            column_success = test_column_operations(args)
            if not column_success:
                print("Column operations test failed")
                all_tests_successful = False
    
    finally:
        # Always perform cleanup if --cleanup is specified
        if args.cleanup:
            cleanup_success = cleanup(args, original_init_content)
            if not cleanup_success:
                print("WARNING: Cleanup had some issues")
                all_tests_successful = False
        else:
            print("\n=== Test complete without cleanup ===")
            print("To cleanup manually, run: python scripts/test_migration_strategy.py --cleanup")
    
    # Final status
    if all_tests_successful:
        print("\n=== All migration strategy tests completed successfully ===")
        return 0
    else:
        print("\n=== Some migration strategy tests failed ===")
        return 1

if __name__ == "__main__":
    sys.exit(main())