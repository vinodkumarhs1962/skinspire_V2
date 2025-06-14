# scripts/direct_migration.py
# python scripts/direct_migration.py --init "Initial migration setup"
# python scripts/direct_migration.py "Add hospital_settings table"
# python scripts/direct_migration.py --init "Initial setup" "Add hospital_settings table"
# python scripts/direct_migration.py "Add hospital_settings table" --upgrade
import os
import sys
from pathlib import Path
import subprocess
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def force_remove_migrations():
    """
    Forcefully remove migrations directory using system commands
    """
    try:
        # Paths to remove
        migrations_dir = project_root / 'migrations'
        alembic_version_table = project_root / 'alembic_version'
        
        # Windows-specific forced removal
        if sys.platform.startswith('win'):
            # Remove migrations directory
            subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', str(migrations_dir)], 
                           check=False, 
                           stderr=subprocess.PIPE, 
                           stdout=subprocess.PIPE)
            
            # Remove Alembic version table tracking file if exists
            if alembic_version_table.exists():
                subprocess.run(['cmd', '/c', 'del', '/f', '/q', str(alembic_version_table)], 
                               check=False, 
                               stderr=subprocess.PIPE, 
                               stdout=subprocess.PIPE)
        else:
            # Unix-like systems
            subprocess.run(['rm', '-rf', str(migrations_dir)], 
                           check=False, 
                           stderr=subprocess.PIPE, 
                           stdout=subprocess.PIPE)
            
            # Remove Alembic version table tracking file if exists
            if alembic_version_table.exists():
                subprocess.run(['rm', '-f', str(alembic_version_table)], 
                               check=False, 
                               stderr=subprocess.PIPE, 
                               stdout=subprocess.PIPE)
        
        logger.info(f"Forcefully removed migrations directory and tracking files")
        return True
    except Exception as e:
        logger.error(f"Error forcefully removing migrations: {e}")
        return False

def prepare_migration_script():
    """
    Prepare migration script by carefully handling problematic sections
    """
    try:
        # Find the latest migration script
        versions_dir = project_root / 'migrations' / 'versions'
        migration_files = sorted(versions_dir.glob('*.py'), key=os.path.getmtime, reverse=True)
        
        if not migration_files:
            logger.error("No migration scripts found")
            return False
        
        # Get the most recent migration script
        latest_migration = migration_files[0]
        logger.info(f"Preparing migration script: {latest_migration}")
        
        # Read the current content
        with open(latest_migration, 'r') as f:
            content = f.readlines()
        
        # Process the content line by line
        modified_content = []
        in_upgrade_block = False
        in_downgrade_block = False
        
        for line in content:
            stripped_line = line.strip()
            
            # Track function blocks
            if stripped_line.startswith('def upgrade():'):
                in_upgrade_block = True
                modified_content.append(line)
                continue
            
            if stripped_line.startswith('def downgrade():'):
                in_upgrade_block = False
                in_downgrade_block = True
                modified_content.append(line)
                continue
            
            # Skip drop table commands in upgrade function
            if in_upgrade_block and 'op.drop_table(' in stripped_line:
                modified_content.append(f"# REMOVED: {line}")
                continue
            
            # Skip create table commands for existing tables in downgrade function
            if in_downgrade_block:
                existing_tables = ['users', 'hospitals', 'branches', 'staff', 'patients']
                if ('op.create_table(' in stripped_line and 
                    any(table in stripped_line for table in existing_tables)):
                    modified_content.append(f"# SKIPPED: {line}")
                    continue
            
            # Ensure functions are not empty
            if (in_upgrade_block and stripped_line == '') or \
               (in_downgrade_block and stripped_line == ''):
                modified_content.append('    pass\n')
                continue
            
            # Add the line
            modified_content.append(line)
        
        # Write back the modified content
        with open(latest_migration, 'w') as f:
            f.writelines(modified_content)
        
        logger.info("Migration script prepared successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error preparing migration script: {e}")
        return False

def run_flask_command(command, capture=True):
    """
    Run Flask CLI commands with proper environment setup
    """
    try:
        # Prepare environment variables
        env = os.environ.copy()
        
        # Explicitly set FLASK_APP to point to create_app in app/__init__.py
        env['FLASK_APP'] = 'app:create_app'
        
        # Use the project root as working directory
        result = subprocess.run(
            [sys.executable, '-m', 'flask'] + command, 
            cwd=project_root,
            env=env,
            capture_output=capture,
            text=True,
            check=True
        )
        
        # Log output
        if not capture:
            print(result.stdout)
            print(result.stderr)
        else:
            if result.stdout:
                logger.info(result.stdout)
            if result.stderr:
                logger.warning(result.stderr)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error running Flask command: {e}")
        return False

def initialize_migrations():
    """
    Safely initialize migrations
    """
    try:
        # Force remove existing migrations
        if not force_remove_migrations():
            logger.error("Failed to remove existing migrations")
            return False
        
        # Initialize migrations
        logger.info("Initializing migrations...")
        if not run_flask_command(['db', 'init'], capture=False):
            logger.error("Failed to initialize migrations")
            return False
        
        logger.info("Migrations initialized successfully")
        return True
    
    except Exception as e:
        logger.error(f"Error during migration initialization: {e}")
        return False

def create_migration(message):
    """
    Create a new database migration
    
    Args:
        message (str): Migration message/description
    """
    try:
        logger.info(f"Creating migration with message: {message}")
        
        # Generate migration script
        if not run_flask_command(['db', 'migrate', '-m', message], capture=False):
            logger.error("Failed to create migration")
            return False
        
        # Prepare migration script by removing problematic operations
        if not prepare_migration_script():
            logger.error("Failed to prepare migration script")
            return False
        
        logger.info("Migration created successfully")
        logger.info("IMPORTANT: Review the migration script before applying!")
        logger.info("Use 'flask db upgrade' to apply the migration when ready.")
        
        return True
    
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False

def main():
    """
    Main script entry point
    """
    # Check if initialization is requested
    init_flag = "--init" in sys.argv
    
    # Additional flags
    upgrade_flag = "--upgrade" in sys.argv
    
    # Initialize migrations if requested
    if init_flag:
        if not initialize_migrations():
            sys.exit(1)
        # Remove init flag from args
        sys.argv.remove("--init")
    
    # Ensure migration message is provided
    if len(sys.argv) < 2:
        logger.error("Usage: python direct_migration.py <message> [--init] [--upgrade]")
        sys.exit(1)
    
    # Get migration message (the last non-flag argument)
    message = [arg for arg in sys.argv[1:] if not arg.startswith('--')][-1]
    
    # Create migration
    success = create_migration(message)
    
    # Optionally apply upgrade if flag is present
    if success and upgrade_flag:
        logger.info("Applying migration...")
        success = run_flask_command(['db', 'upgrade'], capture=False)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()