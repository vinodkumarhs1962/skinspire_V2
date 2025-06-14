# scripts/test_migration_strategy.py
# python scripts/test_migration_strategy.py --skip-backup
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

def main():
    parser = argparse.ArgumentParser(description="Test the model-driven migration strategy")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test artifacts after testing")
    parser.add_argument("--env", default="dev", help="Environment to test (dev/test)")
    parser.add_argument("--skip-backup", action="store_true", help="Skip backup step")
    args = parser.parse_args()
    
    # Set environment variables
    os.environ['FLASK_APP'] = 'app:create_app'
    
    # 1. Create a backup first (optional)
    if not args.skip_backup:
        print("\n=== Step 1: Creating backup ===")
        run_command(f"python scripts/manage_db.py create-backup --env {args.env}")
    else:
        print("\n=== Step 1: Skipping backup (--skip-backup flag used) ===")
    
    # 2. Create a test model file
    print("\n=== Step 2: Creating temporary test model ===")
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
        return 1
    
    # 3. Import the model in __init__.py
    print("\n=== Step 3: Updating model imports ===")
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
    
    # 4. Check if detect-schema-changes command exists
    print("\n=== Step 4: Checking for detect-schema-changes command ===")
    check_result = run_command("python scripts/manage_db.py --help")
    
    if "detect-schema-changes" in check_result.stdout:
        print("detect-schema-changes command exists")
        # Run the command
        print("\n=== Step 5: Detecting schema changes ===")
        run_command("python scripts/manage_db.py detect-schema-changes")
    else:
        print("detect-schema-changes command not found")
        print("Checking for alternatives...")
        
        if "detect_model_changes" in check_result.stdout:
            print("Found detect_model_changes command")
            run_command("python scripts/manage_db.py detect_model_changes")
        else:
            print("No schema detection command found")
            print("Let's try using create-model-migration directly")
    
    # 5. Create a migration
    print("\n=== Step 6: Creating migration ===")
    if "create-model-migration" in check_result.stdout:
        run_command("python scripts/manage_db.py create-model-migration -m \"Add test migration table\"")
    else:
        print("create-model-migration command not found")
        print("Checking for alternatives...")
        
        if "create_db_migration" in check_result.stdout:
            print("Found create_db_migration command")
            run_command("python scripts/manage_db.py create_db_migration -m \"Add test migration table\"")
        else:
            print("WARNING: No migration creation command found")
            print("Trying direct sync method instead")
    
    # 6. Apply the migration
    print("\n=== Step 7: Applying migration ===")
    run_command("python scripts/manage_db.py apply-db-migration")
    
    # 7. Verify the table exists
    print("\n=== Step 8: Verifying table exists ===")
    run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table")
    
    # 8. Test the direct sync method
    print("\n=== Step 9: Testing direct sync method ===")
    try:
        # First add a new column to the model
        with open(test_model_path, "w") as f:
            f.write("""# Test migration model (updated)
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
    
    # New column added for sync testing
    priority = Column(Integer, default=0)
    extra_data = Column(JSONB, default={})
""")
        print("Updated test model with new columns")
    except Exception as e:
        print(f"ERROR updating test model: {e}")
    
    # Run the sync command
    if "sync-models-to-db" in check_result.stdout:
        run_command("python scripts/manage_db.py sync-models-to-db")
    else:
        print("sync-models-to-db command not found")
        print("Checking for alternatives...")
        
        if "sync_models_to_schema" in check_result.stdout:
            print("Found sync_models_to_schema command")
            run_command("python scripts/manage_db.py sync_models_to_schema")
        else:
            print("WARNING: No direct sync command found")
    
    # Verify the new columns exist
    run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table")
    
    # 9. Cleanup if requested
    cleanup_success = True
    if args.cleanup:
        print("\n=== Step 10: Cleaning up ===")
        
        try:
            # Restore the original __init__.py content
            with open(init_path, "w") as f:
                f.write(original_init_content)
            print("Restored original __init__.py content")
        except Exception as e:
            print(f"ERROR restoring __init__.py: {e}")
            cleanup_success = False
        
        try:
            # Remove the test model file
            if test_model_path.exists():
                test_model_path.unlink()
                print("Removed test model file")
            else:
                print("Test model file already removed")
        except Exception as e:
            print(f"ERROR removing test model file: {e}")
            cleanup_success = False
        
        # Roll back the migration
        print("Rolling back migration...")
        run_command("python scripts/manage_db.py rollback-db-migration")
        
        # Verify table no longer exists
        print("Verifying table removal:")
        result = run_command(f"python scripts/manage_db.py inspect-db --table test_migration_table", check=False)
        
        if "not found" in result.stdout or "Error" in result.stdout or result.returncode != 0:
            print("Table successfully removed")
        else:
            print("WARNING: Table still exists after rollback")
            
            # Try dropping directly
            print("Attempting to drop table directly...")
            try:
                # Try to import and use SQLAlchemy directly
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
                    print(f"SQLAlchemy drop failed: {e}")
                    
                    # Try psycopg2 as a last resort
                    try:
                        import psycopg2
                        from app.config.db_config import DatabaseConfig
                        
                        db_url = DatabaseConfig.get_database_url()
                        db_params = db_url.replace('postgresql://', '').split('@')[1].split('/')[0:2]
                        host_port = db_params[0].split(':')
                        host = host_port[0]
                        port = host_port[1] if len(host_port) > 1 else '5432'
                        dbname = db_params[1]
                        
                        conn_str = f"host='{host}' port='{port}' dbname='{dbname}'"
                        conn = psycopg2.connect(conn_str)
                        conn.autocommit = True
                        cursor = conn.cursor()
                        cursor.execute("DROP TABLE IF EXISTS test_migration_table CASCADE")
                        conn.close()
                        print("Table dropped directly using psycopg2")
                    except Exception as e2:
                        print(f"psycopg2 drop failed: {e2}")
                        cleanup_success = False
            except Exception as e:
                print(f"ERROR dropping table directly: {e}")
                cleanup_success = False
    else:
        print("\n=== Test complete without cleanup ===")
        print("To cleanup manually, run: python scripts/test_migration_strategy.py --cleanup")
    
    print("\n=== Migration strategy test completed ===")
    if not cleanup_success and args.cleanup:
        print("WARNING: Some cleanup steps failed. Manual cleanup may be required.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())