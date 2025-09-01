# Implementation Plan for Skinspire Database Management Enhancements

Based on the code and documents in the knowledge area, I'll detail a step-by-step implementation plan for enhancing the database management system while ensuring backward compatibility.

## Phase 1: Core Configuration System

### Step 1: Create Centralized Configuration Module

Create a new file: `app/config/db_config.py`

```python
# app/config/db_config.py
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Centralized database configuration that preserves backward compatibility"""
    
    # Default configuration with fallbacks
    DEFAULT_CONFIG = {
        'development': {
            'url': 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev',
            'echo': True,
            'pool_size': 5,
            'use_nested_transactions': True,
            'backup_before_migration': True
        },
        'testing': {
            'url': 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test',
            'echo': False,
            'pool_size': 3,
            'use_nested_transactions': False,
            'backup_before_migration': False
        },
        'production': {
            'url': 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod',
            'echo': False,
            'pool_size': 10,
            'use_nested_transactions': True,
            'backup_before_migration': True
        }
    }
    
    @classmethod
    def get_active_env(cls) -> str:
        """
        Get active environment with consistent fallback logic.
        This replicates the existing database_service.py logic.
        """
        env = os.environ.get('FLASK_ENV', 'development')
        
        # Check for environment override file (from existing switch_env.py logic)
        env_type_file = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / '.flask_env_type'
        if env_type_file.exists():
            with open(env_type_file, 'r') as f:
                env_override = f.read().strip()
                if env_override in ['dev', 'test', 'prod']:
                    # Map short forms to full names
                    env_map = {'dev': 'development', 'test': 'testing', 'prod': 'production'}
                    env = env_map.get(env_override, env_override)
        
        return env
    
    @classmethod
    def get_database_url_for_env(cls, env: str) -> str:
        """
        Get database URL for environment - maintains compatibility with
        existing database_service.py logic.
        """
        # Map short forms to full names for backward compatibility
        env_map = {'dev': 'development', 'test': 'testing', 'prod': 'production'}
        normalized_env = env_map.get(env, env)
        
        # Check environment variables first (existing approach)
        if normalized_env == 'production' or normalized_env == 'prod':
            url = os.environ.get('PROD_DATABASE_URL')
        elif normalized_env == 'testing' or normalized_env == 'test':
            url = os.environ.get('TEST_DATABASE_URL')
        else:  # Default to development
            url = os.environ.get('DEV_DATABASE_URL')
        
        # Fall back to defaults if not in environment
        if not url:
            config = cls.DEFAULT_CONFIG.get(normalized_env, cls.DEFAULT_CONFIG['development'])
            url = config.get('url')
            
        return url
    
    @classmethod
    def get_config(cls, env: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete configuration for specified environment.
        
        Args:
            env: Environment name ('development'/'dev', 'testing'/'test', 'production'/'prod')
                If None, uses active environment
                
        Returns:
            Dictionary with configuration values
        """
        if env is None:
            env = cls.get_active_env()
        
        # Map short forms to full names
        env_map = {'dev': 'development', 'test': 'testing', 'prod': 'production'}
        normalized_env = env_map.get(env, env)
        
        # Start with default config
        config = cls.DEFAULT_CONFIG.get(normalized_env, cls.DEFAULT_CONFIG['development']).copy()
        
        # Override with environment variables
        if normalized_env == 'production':
            if os.environ.get('PROD_DATABASE_URL'):
                config['url'] = os.environ.get('PROD_DATABASE_URL')
        elif normalized_env == 'testing':
            if os.environ.get('TEST_DATABASE_URL'):
                config['url'] = os.environ.get('TEST_DATABASE_URL')
        elif normalized_env == 'development':
            if os.environ.get('DEV_DATABASE_URL'):
                config['url'] = os.environ.get('DEV_DATABASE_URL')
        
        # Override use_nested_transactions if explicitly set
        if 'USE_NESTED_TRANSACTIONS' in os.environ:
            config['use_nested_transactions'] = os.environ.get('USE_NESTED_TRANSACTIONS').lower() in ('true', '1', 'yes')
        
        return config
```

### Step 2: Enhance database_service.py to Use Configuration Module

Create a new file: `utils/db_utils.py` for shared utilities

```python
# utils/db_utils.py
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def ensure_directory(path: str) -> None:
    """Ensure directory exists, creating it if necessary"""
    directory = Path(path)
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def get_backup_directory() -> Path:
    """Get the directory for database backups"""
    backup_dir = Path('backups')
    ensure_directory(str(backup_dir))
    return backup_dir

def get_environment_display_name(env: str) -> str:
    """Convert environment code to display name"""
    env_map = {
        'dev': 'Development',
        'test': 'Testing',
        'prod': 'Production',
        'development': 'Development',
        'testing': 'Testing',
        'production': 'Production'
    }
    return env_map.get(env, env.capitalize())
```

Modify `database_service.py` to use the configuration module (without breaking compatibility):

```python
# Modified sections of app/services/database_service.py

# Add imports at the top
from app.config.db_config import DatabaseConfig

# Update get_active_environment method:
@classmethod
def get_active_environment(cls) -> str:
    """
    Get the currently active database environment
    
    Returns:
        String representing the environment ('development', 'testing', or 'production')
    """
    # Use centralized configuration
    return DatabaseConfig.get_active_env()

# Update get_database_url_for_env method:
@classmethod
def get_database_url_for_env(cls, env: str) -> str:
    """
    Get the database URL for the specified environment
    
    Args:
        env: Environment name ('development'/'dev', 'testing'/'test', 'production'/'prod')
        
    Returns:
        Database URL string
    """
    # Use centralized configuration
    return DatabaseConfig.get_database_url_for_env(env)
```

## Phase 2: Database Backup and Copy Enhancement

### Step 1: Create Backup Manager Module

Create a new file: `scripts/db/backup_manager.py`

```python
# scripts/db/backup_manager.py
import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.config.db_config import DatabaseConfig
from utils.db_utils import get_backup_directory, get_environment_display_name

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_db_url(url: str) -> Dict[str, str]:
    """
    Parse database URL into components
    
    Args:
        url: Database URL (postgresql://user:pass@host:port/dbname)
        
    Returns:
        Dictionary with URL components
    """
    try:
        # Handle URL format: postgresql://user:pass@host:port/dbname
        if '://' in url:
            # Remove protocol
            url = url.split('://', 1)[1]
        
        # Split credentials and connection
        if '@' in url:
            credentials, connection = url.split('@', 1)
        else:
            credentials, connection = '', url
        
        # Parse credentials
        if ':' in credentials:
            user, password = credentials.split(':', 1)
        else:
            user, password = credentials, ''
        
        # Parse connection
        if '/' in connection:
            host_port, dbname = connection.split('/', 1)
        else:
            host_port, dbname = connection, ''
        
        # Parse host/port
        if ':' in host_port:
            host, port = host_port.split(':', 1)
        else:
            host, port = host_port, '5432'  # Default PostgreSQL port
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'dbname': dbname
        }
    except Exception as e:
        logger.error(f"Failed to parse database URL: {e}")
        return {}

def create_backup(env: str, output_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
    """
    Create database backup
    
    Args:
        env: Environment to backup ('dev', 'test', 'prod')
        output_file: Optional specific output filename
        
    Returns:
        Tuple of (success, backup_file_path)
    """
    # Get database URL for environment
    db_url = DatabaseConfig.get_database_url_for_env(env)
    if not db_url:
        logger.error(f"No database URL found for environment: {env}")
        return False, None
    
    # Parse URL
    db_info = parse_db_url(db_url)
    if not db_info or not db_info.get('dbname'):
        logger.error(f"Failed to parse database URL or missing database name")
        return False, None
    
    # Setup backup directory and filename
    backup_dir = get_backup_directory()
    
    if not output_file:
        # Generate filename based on environment and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{env}_{db_info['dbname']}_{timestamp}.sql"
    
    backup_path = backup_dir / output_file
    
    # Set environment variables for pg_dump
    env_vars = os.environ.copy()
    if db_info.get('password'):
        env_vars['PGPASSWORD'] = db_info['password']
    
    # Build pg_dump command
    cmd = [
        'pg_dump',
        '-h', db_info.get('host', 'localhost'),
        '-p', db_info.get('port', '5432'),
        '-U', db_info.get('user', 'postgres'),
        '-d', db_info.get('dbname', ''),
        '-f', str(backup_path),
        '--verbose'
    ]
    
    logger.info(f"Creating backup of {get_environment_display_name(env)} database to {backup_path}")
    
    try:
        # Run pg_dump
        process = subprocess.run(
            cmd,
            env=env_vars,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Check for successful backup
        if backup_path.exists() and backup_path.stat().st_size > 0:
            logger.info(f"Backup created successfully: {backup_path}")
            return True, backup_path
        else:
            logger.error(f"Backup failed or empty: {backup_path}")
            return False, None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False, None
    finally:
        # Clean up password from environment
        if 'PGPASSWORD' in env_vars:
            del env_vars['PGPASSWORD']

def restore_backup(backup_file: str, env: str) -> bool:
    """
    Restore database from backup
    
    Args:
        backup_file: Path to backup file
        env: Target environment ('dev', 'test', 'prod')
        
    Returns:
        True if successful, False otherwise
    """
    # Get database URL for environment
    db_url = DatabaseConfig.get_database_url_for_env(env)
    if not db_url:
        logger.error(f"No database URL found for environment: {env}")
        return False
    
    # Parse URL
    db_info = parse_db_url(db_url)
    if not db_info or not db_info.get('dbname'):
        logger.error(f"Failed to parse database URL or missing database name")
        return False
    
    # Ensure backup file exists
    backup_path = Path(backup_file)
    if not backup_path.exists():
        # Try looking in backups directory
        backup_dir = get_backup_directory()
        backup_path = backup_dir / backup_file
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False
    
    # Create backup of current database before restoring
    create_backup(env, f"{env}_{db_info['dbname']}_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
    
    # Set environment variables for psql
    env_vars = os.environ.copy()
    if db_info.get('password'):
        env_vars['PGPASSWORD'] = db_info['password']
    
    try:
        # First, drop and recreate public schema to ensure clean restore
        logger.info(f"Preparing database for restore...")
        reset_cmd = [
            'psql',
            '-h', db_info.get('host', 'localhost'),
            '-p', db_info.get('port', '5432'),
            '-U', db_info.get('user', 'postgres'),
            '-d', db_info.get('dbname', ''),
            '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
        ]
        
        subprocess.run(
            reset_cmd,
            env=env_vars,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Now restore from backup
        logger.info(f"Restoring {get_environment_display_name(env)} database from {backup_path}")
        restore_cmd = [
            'psql',
            '-h', db_info.get('host', 'localhost'),
            '-p', db_info.get('port', '5432'),
            '-U', db_info.get('user', 'postgres'),
            '-d', db_info.get('dbname', ''),
            '-f', str(backup_path)
        ]
        
        process = subprocess.run(
            restore_cmd,
            env=env_vars,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Database restored successfully")
        
        # Apply triggers after restore
        logger.info(f"Re-applying database triggers...")
        subprocess.run(
            ['python', f"{project_root}/scripts/install_triggers.py", env],
            check=True
        )
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Restore failed: {e}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False
    finally:
        # Clean up password from environment
        if 'PGPASSWORD' in env_vars:
            del env_vars['PGPASSWORD']

def list_backups() -> None:
    """List available database backups"""
    backup_dir = get_backup_directory()
    backups = sorted(backup_dir.glob('*.sql'), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not backups:
        logger.info("No database backups found")
        return
    
    print("\nAvailable Database Backups:")
    print("===========================")
    print(f"{'Filename':<50} {'Size':<10} {'Date':<20}")
    print("-" * 80)
    
    for backup in backups:
        size_kb = backup.stat().st_size / 1024
        size_display = f"{size_kb:.1f} KB"
        mod_time = datetime.fromtimestamp(backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{backup.name:<50} {size_display:<10} {mod_time:<20}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database Backup Manager")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create backup command
    backup_parser = subparsers.add_parser('backup', help='Create database backup')
    backup_parser.add_argument('--env', default=None, choices=['dev', 'test', 'prod'], 
                             help='Environment to backup (default: current environment)')
    backup_parser.add_argument('--output', help='Output filename')
    
    # Restore backup command
    restore_parser = subparsers.add_parser('restore', help='Restore database from backup')
    restore_parser.add_argument('file', help='Backup file to restore from')
    restore_parser.add_argument('--env', default=None, choices=['dev', 'test', 'prod'],
                              help='Target environment (default: current environment)')
    
    # List backups command
    list_parser = subparsers.add_parser('list', help='List available backups')
    
    args = parser.parse_args()
    
    # Get current environment if not specified
    if hasattr(args, 'env') and args.env is None:
        args.env = DatabaseConfig.get_active_env()
        # Convert full env name to short form
        if args.env == 'development':
            args.env = 'dev'
        elif args.env == 'testing':
            args.env = 'test'
        elif args.env == 'production':
            args.env = 'prod'
    
    if args.command == 'backup':
        success, backup_path = create_backup(args.env, args.output)
        sys.exit(0 if success else 1)
    elif args.command == 'restore':
        success = restore_backup(args.file, args.env)
        sys.exit(0 if success else 1)
    elif args.command == 'list':
        list_backups()
    else:
        parser.print_help()
```

### Step 2: Create Enhanced Database Copy Script

Create a new file: `scripts/db/copy_db.py`

```python
# scripts/db/copy_db.py
import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.config.db_config import DatabaseConfig
from utils.db_utils import get_backup_directory, get_environment_display_name

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_db_url(url: str) -> Dict[str, str]:
    """Parse database URL into components"""
    try:
        # Handle URL format: postgresql://user:pass@host:port/dbname
        if '://' in url:
            # Remove protocol
            url = url.split('://', 1)[1]
        
        # Split credentials and connection
        if '@' in url:
            credentials, connection = url.split('@', 1)
        else:
            credentials, connection = '', url
        
        # Parse credentials
        if ':' in credentials:
            user, password = credentials.split(':', 1)
        else:
            user, password = credentials, ''
        
        # Parse connection
        if '/' in connection:
            host_port, dbname = connection.split('/', 1)
        else:
            host_port, dbname = connection, ''
        
        # Parse host/port
        if ':' in host_port:
            host, port = host_port.split(':', 1)
        else:
            host, port = host_port, '5432'  # Default PostgreSQL port
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'dbname': dbname
        }
    except Exception as e:
        logger.error(f"Failed to parse database URL: {e}")
        return {}

def copy_database(source_env: str, target_env: str, schema_only: bool = False, 
                 data_only: bool = False, tables: Optional[List[str]] = None) -> bool:
    """
    Copy database from source environment to target environment
    
    Args:
        source_env: Source environment ('dev', 'test', 'prod')
        target_env: Target environment ('dev', 'test', 'prod')
        schema_only: Copy only schema without data
        data_only: Copy only data without altering schema
        tables: Optional list of specific tables to copy
        
    Returns:
        True if successful, False otherwise
    """
    # Validate environments
    if source_env == target_env:
        logger.error("Source and target environments cannot be the same")
        return False
    
    # Get database URLs
    source_url = DatabaseConfig.get_database_url_for_env(source_env)
    target_url = DatabaseConfig.get_database_url_for_env(target_env)
    
    if not source_url or not target_url:
        logger.error(f"Database URL not found for environments")
        return False
    
    # Parse URLs
    source_info = parse_db_url(source_url)
    target_info = parse_db_url(target_url)
    
    if not source_info or not target_info:
        logger.error("Failed to parse database URLs")
        return False
    
    # Set environment variables for first process
    env_vars = os.environ.copy()
    if source_info.get('password'):
        env_vars['PGPASSWORD'] = source_info['password']
    
    # Create backup of target database first
    logger.info(f"Creating backup of target {get_environment_display_name(target_env)} database...")
    
    backup_dir = get_backup_directory()
    backup_file = backup_dir / f"{target_env}_{target_info['dbname']}_pre_copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    target_backup_cmd = [
        'pg_dump',
        '-h', target_info.get('host', 'localhost'),
        '-p', target_info.get('port', '5432'),
        '-U', target_info.get('user', 'postgres'),
        '-d', target_info.get('dbname', ''),
        '-f', str(backup_file)
    ]
    
    try:
        subprocess.run(
            target_backup_cmd,
            env=env_vars,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Target database backed up to {backup_file}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to backup target database: {e}")
        logger.warning("Proceeding with copy operation without backup")
    
    # For direct pipe transfer, we'll use temporary files to ensure clean handling
    temp_dump = backup_dir / f"temp_{source_env}_to_{target_env}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    # Build pg_dump command with appropriate options
    dump_cmd = [
        'pg_dump',
        '-h', source_info.get('host', 'localhost'),
        '-p', source_info.get('port', '5432'),
        '-U', source_info.get('user', 'postgres'),
        '-d', source_info.get('dbname', ''),
        '-f', str(temp_dump)
    ]
    
    if schema_only:
        dump_cmd.append('--schema-only')
    elif data_only:
        dump_cmd.append('--data-only')
    
    if tables:
        # Add specific tables to the command
        for table in tables:
            dump_cmd.extend(['-t', table])
    
    # Update env vars for PGPASSWORD
    if source_info.get('password'):
        env_vars['PGPASSWORD'] = source_info['password']
    
    try:
        # Step 1: Dump source database
        logger.info(f"Dumping {get_environment_display_name(source_env)} database...")
        subprocess.run(
            dump_cmd,
            env=env_vars,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Update env vars for target database
        if target_info.get('password'):
            env_vars['PGPASSWORD'] = target_info['password']
        
        # Step 2: If not data_only, drop and recreate schema in target
        if not data_only:
            logger.info(f"Preparing {get_environment_display_name(target_env)} database...")
            reset_cmd = [
                'psql',
                '-h', target_info.get('host', 'localhost'),
                '-p', target_info.get('port', '5432'),
                '-U', target_info.get('user', 'postgres'),
                '-d', target_info.get('dbname', ''),
                '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
            ]
            
            subprocess.run(
                reset_cmd,
                env=env_vars,
                check=True,
                capture_output=True,
                text=True
            )
        
        # Step 3: Restore to target database
        logger.info(f"Restoring to {get_environment_display_name(target_env)} database...")
        restore_cmd = [
            'psql',
            '-h', target_info.get('host', 'localhost'),
            '-p', target_info.get('port', '5432'),
            '-U', target_info.get('user', 'postgres'),
            '-d', target_info.get('dbname', ''),
            '-f', str(temp_dump)
        ]
        
        subprocess.run(
            restore_cmd,
            env=env_vars,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Step 4: Re-apply triggers
        logger.info(f"Re-applying database triggers...")
        subprocess.run(
            ['python', f"{project_root}/scripts/install_triggers.py", target_env],
            check=True
        )
        
        logger.info(f"Database copy completed successfully: {source_env} -> {target_env}")
        
        # Clean up temp file
        if temp_dump.exists():
            temp_dump.unlink()
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Database copy failed: {e}")
        if hasattr(e, 'stdout'):
            logger.error(f"Command output: {e.stdout}")
        if hasattr(e, 'stderr'):
            logger.error(f"Command error: {e.stderr}")
        
        logger.info(f"You can restore the target database from backup: {backup_file}")
        return False
    finally:
        # Clean up temp files
        if temp_dump.exists():
            try:
                temp_dump.unlink()
            except:
                pass
        
        # Clean up password from environment
        if 'PGPASSWORD' in env_vars:
            del env_vars['PGPASSWORD']

# Create backward-compatible wrapper for copy_test_to_dev.py
def copy_test_to_dev():
    """Backward-compatible wrapper for copy_test_to_dev.py"""
    logger.info("Running copy_test_to_dev using enhanced copy_db functionality")
    return copy_database('test', 'dev')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Copy database between environments")
    
    # Check if this script is being run as copy_test_to_dev.py
    if 'copy_test_to_dev.py' in sys.argv[0]:
        # Run in backward-compatible mode
        success = copy_test_to_dev()
        sys.exit(0 if success else 1)
    
    # Regular CLI arguments
    parser.add_argument("source", choices=["dev", "test", "prod"], help="Source environment")
    parser.add_argument("target", choices=["dev", "test", "prod"], help="Target environment")
    parser.add_argument("--schema-only", action="store_true", help="Copy only schema (no data)")
    parser.add_argument("--data-only", action="store_true", help="Copy only data (preserve schema)")
    parser.add_argument("--tables", nargs="+", help="Specific tables to copy")
    
    args = parser.parse_args()
    
    if args.schema_only and args.data_only:
        logger.error("Cannot use both --schema-only and --data-only options")
        sys.exit(1)
    
    success = copy_database(args.source, args.target, args.schema_only, args.data_only, args.tables)
    sys.exit(0 if success else 1)
```

### Step 3: Create a Symlink for Backward Compatibility with copy_test_to_dev.py

Create a file: `scripts/copy_test_to_dev.py` that imports from the new module

```python
# scripts/copy_test_to_dev.py
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import from new module
from scripts.db.copy_db import copy_test_to_dev

if __name__ == "__main__":
    success = copy_test_to_dev()
    sys.exit(0 if success else 1)
```

## Phase 3: Enhanced Migration Management

### Step 1: Create Migration Helpers Module
Create a new file: app/database/migrations/helpers.py
# app/database/migrations/helpers.py
import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from app.config.db_config import DatabaseConfig
from scripts.db.backup_manager import create_backup

# Setup logging
logger = logging.getLogger(__name__)

def get_migration_directory() -> Path:
    """Get the Alembic migrations directory"""
    migrations_dir = project_root / 'migrations'
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")
    return migrations_dir

def get_versions_directory() -> Path:
    """Get the Alembic versions directory"""
    versions_dir = get_migration_directory() / 'versions'
    if not versions_dir.exists():
        raise FileNotFoundError(f"Versions directory not found: {versions_dir}")
    return versions_dir

def get_latest_migration() -> Optional[Path]:
    """Get the latest migration file"""
    versions_dir = get_versions_directory()
    migration_files = sorted(versions_dir.glob('*.py'), key=lambda p: p.stat().st_mtime, reverse=True)
    return migration_files[0] if migration_files else None

def get_migration_history() -> List[Dict[str, Any]]:
    """Get history of migrations"""
    versions_dir = get_versions_directory()
    migration_files = sorted(versions_dir.glob('*.py'), key=lambda p: p.stat().st_mtime)
    
    history = []
    for file in migration_files:
        # Extract information from filename and contents
        revision = None
        down_revision = None
        description = None
        
        with open(file, 'r') as f:
            content = f.read()
            
            # Extract revision
            rev_match = re.search(r'revision\s*=\s*[\'"](.*?)[\'"]', content)
            if rev_match:
                revision = rev_match.group(1)
            
            # Extract down_revision
            down_rev_match = re.search(r'down_revision\s*=\s*[\'"](.*?)[\'"]', content)
            if down_rev_match:
                down_revision = down_rev_match.group(1)
            
            # Extract description from docstring or filename
            desc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip().split('\n')[0]
        
        if not description:
            # Extract from filename (format: xxxx_description.py)
            parts = file.stem.split('_', 1)
            if len(parts) > 1:
                description = parts[1].replace('_', ' ')
        
        # Get file stats
        stats = file.stat()
        created_at = datetime.fromtimestamp(stats.st_mtime)
        
        history.append({
            'file': file.name,
            'revision': revision,
            'down_revision': down_revision,
            'description': description,
            'created_at': created_at
        })
    
    return history

def backup_before_migration(env: str) -> Optional[Path]:
    """
    Create database backup before migration
    
    Args:
        env: Target environment ('dev', 'test', 'prod')
        
    Returns:
        Path to backup file or None if backup failed
    """
    # Use environment-specific naming format
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"{env}_pre_migration_{timestamp}.sql"
    
    # Create backup
    success, backup_path = create_backup(env, backup_file)
    if success:
        logger.info(f"Created pre-migration backup: {backup_path}")
        return backup_path
    else:
        logger.warning("Failed to create pre-migration backup")
        return None
```

### Step 2: Create Migration Manager Script

Create a new file: `scripts/db/migration_manager.py`

```python
# scripts/db/migration_manager.py
import os
import sys
import argparse
import subprocess
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.config.db_config import DatabaseConfig
from app.database.migrations.helpers import (
    get_migration_directory, get_versions_directory,
    get_latest_migration, get_migration_history,
    backup_before_migration
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_flask_command(command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
    """
    Run Flask command with environment setup
    
    Args:
        command: Command to run (list of args)
        capture_output: Whether to capture command output
        
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    # Ensure Flask app is set
    env = os.environ.copy()
    if 'FLASK_APP' not in env:
        env['FLASK_APP'] = 'app'
    
    # Build full command
    flask_cmd = [sys.executable, '-m', 'flask'] + command
    
    try:
        if capture_output:
            process = subprocess.run(
                flask_cmd,
                env=env,
                check=False,  # Don't raise exception, we'll handle it
                capture_output=True,
                text=True
            )
            return process.returncode, process.stdout, process.stderr
        else:
            # Run with output directly to console
            process = subprocess.run(
                flask_cmd,
                env=env,
                check=False  # Don't raise exception, we'll handle it
            )
            return process.returncode, "", ""
    except Exception as e:
        logger.error(f"Error running Flask command: {e}")
        return 1, "", str(e)

def create_migration(message: str, env: str, backup: bool = True, auto_apply: bool = False) -> bool:
    """
    Create database migration
    
    Args:
        message: Migration message
        env: Target environment ('dev', 'test', 'prod')
        backup: Create backup before migration
        auto_apply: Automatically apply migration
        
    Returns:
        True if successful, False otherwise
    """
    # Set environment
    os.environ['FLASK_ENV'] = env
    
    # Create backup if requested
    if backup:
        backup_path = backup_before_migration(env)
        if not backup_path and not input("Failed to create backup. Continue anyway? [y/N] ").lower().startswith('y'):
            logger.info("Migration cancelled")
            return False
    
    # Create migration
    logger.info(f"Creating migration: {message}")
    exit_code, stdout, stderr = run_flask_command(['db', 'migrate', '-m', message])
    
    if exit_code != 0:
        logger.error(f"Migration creation failed: {stderr}")
        return False
    
    logger.info(stdout)
    
    # Find the newly created migration file
    migration_file = get_latest_migration()
    if not migration_file:
        logger.warning("No migration file found. Migration likely didn't create any changes.")
        return True
    
    logger.info(f"Created migration file: {migration_file}")
    
    # Ask to review migration if not auto-applying
    if not auto_apply:
        response = input("Would you like to review the migration file? [Y/n] ")
        if not response.lower().startswith('n'):
            # On Windows, use default program to open file
            try:
                os.startfile(migration_file)
            except AttributeError:
                # On non-Windows platforms
                if sys.platform.startswith('darwin'):
                    subprocess.run(['open', migration_file])
                else:
                    subprocess.run(['xdg-open', migration_file])
    
    # Ask to apply migration
    if auto_apply or input("Apply migration now? [y/N] ").lower().startswith('y'):
        return apply_migration(env)
    else:
        logger.info("Migration created but not applied")
        return True

def apply_migration(env: str) -> bool:
    """
    Apply pending migrations
    
    Args:
        env: Target environment ('dev', 'test', 'prod')
        
    Returns:
        True if successful, False otherwise
    """
    # Set environment
    os.environ['FLASK_ENV'] = env
    
    # Apply migration
    logger.info(f"Applying migrations to {env} environment")
    exit_code, stdout, stderr = run_flask_command(['db', 'upgrade'], capture_output=False)
    
    if exit_code != 0:
        logger.error(f"Migration application failed")
        return False
    
    logger.info("Migration applied successfully")
    
    # Apply database triggers
    logger.info("Re-applying database triggers")
    trigger_exit_code = subprocess.call([sys.executable, f"{project_root}/scripts/install_triggers.py", env])
    
    if trigger_exit_code != 0:
        logger.warning("Failed to re-apply database triggers")
    else:
        logger.info("Database triggers applied successfully")
    
    return True

def rollback_migration(env: str, steps: int = 1, backup: bool = True) -> bool:
    """
    Roll back migrations
    
    Args:
        env: Target environment ('dev', 'test', 'prod')
        steps: Number of migrations to roll back
        backup: Create backup before rollback
        
    Returns:
        True if successful, False otherwise
    """
    # Set environment
    os.environ['FLASK_ENV'] = env
    
    # Create backup if requested
    if backup:
        backup_path = backup_before_migration(env)
        if not backup_path and not input("Failed to create backup. Continue anyway? [y/N] ").lower().startswith('y'):
            logger.info("Rollback cancelled")
            return False
    
    # Get current migration history
    migrations = get_migration_history()
    if len(migrations) < steps:
        logger.error(f"Cannot roll back {steps} migrations - only {len(migrations)} migrations exist")
        return False
    
    # Show migrations to be rolled back
    target_migrations = migrations[-steps:]
    logger.info(f"Will roll back the following {steps} migration(s):")
    for i, migration in enumerate(target_migrations):
        logger.info(f"{i+1}. {migration.get('description', 'Unknown')} ({migration.get('file', 'Unknown')})")
    
    # Confirm rollback
    if not input(f"Roll back {steps} migration(s)? [y/N] ").lower().startswith('y'):
        logger.info("Rollback cancelled")
        return False
    
    # Roll back migrations
    logger.info(f"Rolling back {steps} migration(s)")
    
    if steps == 1:
        command = ['db', 'downgrade', '-1']
    else:
        # Find the revision to roll back to
        target_revision = migrations[-(steps+1)]['revision'] if len(migrations) > steps else 'base'
        command = ['db', 'downgrade', target_revision]
    
    exit_code, stdout, stderr = run_flask_command(command, capture_output=False)
    
    if exit_code != 0:
        logger.error(f"Migration rollback failed")
        return False
    
    logger.info("Migration rollback completed successfully")
    
    # Apply database triggers
    logger.info("Re-applying database triggers")
    trigger_exit_code = subprocess.call([sys.executable, f"{project_root}/scripts/install_triggers.py", env])
    
    if trigger_exit_code != 0:
        logger.warning("Failed to re-apply database triggers")
    else:
        logger.info("Database triggers applied successfully")
    
    return True

def show_migrations() -> None:
    """Show migration history"""
    migrations = get_migration_history()
    
    if not migrations:
        logger.info("No migrations found")
        return
    
    print("\nMigration History:")
    print("=====================================")
    print(f"{'#':<3} {'Revision':<10} {'Description':<40} {'Created At':<20}")
    print("-" * 80)
    
    for i, migration in enumerate(migrations):
        desc = migration.get('description', 'Unknown')
        if len(desc) > 37:
            desc = desc[:34] + "..."
        
        print(f"{i+1:<3} {migration.get('revision', 'Unknown')[:8]:<10} {desc:<40} {migration.get('created_at').strftime('%Y-%m-%d %H:%M:%S'):<20}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database Migration Manager")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create migration command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('--message', '-m', required=True, help='Migration message')
    create_parser.add_argument('--env', default=None, help='Target environment (default: current environment)')
    create_parser.add_argument('--backup', action='store_true', default=True, help='Create backup before migration')
    create_parser.add_argument('--no-backup', action='store_true', help='Skip backup')
    create_parser.add_argument('--apply', action='store_true', help='Automatically apply migration')
    
    # Apply migrations command
    apply_parser = subparsers.add_parser('apply', help='Apply pending migrations')
    apply_parser.add_argument('--env', default=None, help='Target environment (default: current environment)')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Roll back migrations')
    rollback_parser.add_argument('--steps', type=int, default=1, help='Number of migrations to roll back')
    rollback_parser.add_argument('--env', default=None, help='Target environment (default: current environment)')
    rollback_parser.add_argument('--backup', action='store_true', default=True, help='Create backup before rollback')
    rollback_parser.add_argument('--no-backup', action='store_true', help='Skip backup')
    
    # Show migrations command
    show_parser = subparsers.add_parser('show', help='Show migration history')
    
    args = parser.parse_args()
    
    # Get current environment if not specified
    if hasattr(args, 'env') and args.env is None:
        args.env = DatabaseConfig.get_active_env()
        # Convert full env name to short form
        if args.env == 'development':
            args.env = 'dev'
        elif args.env == 'testing':
            args.env = 'test'
        elif args.env == 'production':
            args.env = 'prod'
    
    if args.command == 'create':
        backup = args.backup and not args.no_backup
        success = create_migration(args.message, args.env, backup, args.apply)
        sys.exit(0 if success else 1)
    elif args.command == 'apply':
        success = apply_migration(args.env)
        sys.exit(0 if success else 1)
    elif args.command == 'rollback':
        backup = args.backup and not args.no_backup
        success = rollback_migration(args.env, args.steps, backup)
        sys.exit(0 if success else 1)
    elif args.command == 'show':
        show_migrations()
    else:
        parser.print_help()
```

### Step 3: Create a Wrapper Script for Migration Manager

Create a new file: `scripts/migration_manager.py`

```python
# scripts/migration_manager.py
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import from new module
from scripts.db.migration_manager import (
    create_migration, apply_migration, rollback_migration, show_migrations
)

if __name__ == "__main__":
    # Simple redirection to scripts/db/migration_manager.py
    import scripts.db.migration_manager
    scripts.db.migration_manager.main()
```

## Phase 4: Enhancement of manage_db.py

### Step 1: Enhance manage_db.py to Integrate New Tools

Modify `scripts/manage_db.py` to include the new functionality while preserving backward compatibility:

```python
# Modified sections of scripts/manage_db.py

# Add imports to new modules
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scripts.db.backup_manager import create_backup, restore_backup, list_backups
from scripts.db.copy_db import copy_database
from scripts.db.migration_manager import create_migration, apply_migration, rollback_migration, show_migrations

# Add new CLI commands to the existing cli group

@cli.command()
@with_appcontext
def backup():
    """Create database backup"""
    app = get_app()
    with app.app_context():
        env = DatabaseConfig.get_active_env()
        short_env = 'dev' if env == 'development' else 'test' if env == 'testing' else 'prod'
        success, backup_path = create_backup(short_env)
        if success:
            click.echo(f"Backup created: {backup_path}")
        else:
            click.echo("Backup failed")
            sys.exit(1)

@cli.command()
@click.option('--file', help='Backup file to restore')
@with_appcontext
def restore_backup(file):
    """Restore database from backup"""
    app = get_app()
    with app.app_context():
        env = DatabaseConfig.get_active_env()
        short_env = 'dev' if env == 'development' else 'test' if env == 'testing' else 'prod'
        
        if not file:
            # List backups and ask user to choose
            list_backups()
            file = click.prompt("Enter backup file to restore", type=str)
        
        success = restore_backup(file, short_env)
        if success:
            click.echo(f"Database restored successfully from {file}")
        else:
            click.echo("Restore failed")
            sys.exit(1)

@cli.command()
@click.argument('source', type=click.Choice(['dev', 'test', 'prod']))
@click.argument('target', type=click.Choice(['dev', 'test', 'prod']))
@click.option('--schema-only', is_flag=True, help='Copy only schema (no data)')
@click.option('--data-only', is_flag=True, help='Copy only data (preserve schema)')
@with_appcontext
def copy_db(source, target, schema_only, data_only):
    """Copy database between environments"""
    if schema_only and data_only:
        click.echo("Error: Cannot use both --schema-only and --data-only")
        sys.exit(1)
    
    success = copy_database(source, target, schema_only, data_only)
    if success:
        click.echo(f"Database copied successfully from {source} to {target}")
    else:
        click.echo("Database copy failed")
        sys.exit(1)

@cli.command()
@click.option('--message', '-m', required=True, help='Migration message')
@click.option('--backup/--no-backup', default=True, help='Create backup before migration')
@click.option('--apply', is_flag=True, help='Automatically apply migration')
@with_appcontext
def create_migration(message, backup, apply):
    """Create new database migration"""
    app = get_app()
    with app.app_context():
        env = DatabaseConfig.get_active_env()
        short_env = 'dev' if env == 'development' else 'test' if env == 'testing' else 'prod'
        
        success = create_migration(message, short_env, backup, apply)
        if success:
            click.echo("Migration created successfully")
        else:
            click.echo("Migration creation failed")
            sys.exit(1)

@cli.command()
@with_appcontext
def apply_migrations():
    """Apply pending database migrations"""
    app = get_app()
    with app.app_context():
        env = DatabaseConfig.get_active_env()
        short_env = 'dev' if env == 'development' else 'test' if env == 'testing' else 'prod'
        
        success = apply_migration(short_env)
        if success:
            click.echo("Migrations applied successfully")
        else:
            click.echo("Migration application failed")
            sys.exit(1)

@cli.command()
@click.option('--steps', type=int, default=1, help='Number of migrations to roll back')
@click.option('--backup/--no-backup', default=True, help='Create backup before rollback')
@with_appcontext
def rollback(steps, backup):
    """Roll back migrations"""
    app = get_app()
    with app.app_context():
        env = DatabaseConfig.get_active_env()
        short_env = 'dev' if env == 'development' else 'test' if env == 'testing' else 'prod'
        
        success = rollback_migration(short_env, steps, backup)
        if success:
            click.echo("Migrations rolled back successfully")
        else:
            click.echo("Migration rollback failed")
            sys.exit(1)

@cli.command()
@with_appcontext
def show_migrations():
    """Show migration history"""
    show_migrations()
```

## Phase 5: Creating Directory Structure

### Step 1: Create the Directories

Create the following directories to organize the code:

```bash
# Create scripts/db directory
mkdir -p scripts/db

# Create backups directory
mkdir -p backups

# Create app/database/migrations directory
mkdir -p app/database/migrations

# Create app/database/triggers directory 
mkdir -p app/database/triggers

# Create utils directory if it doesn't exist
mkdir -p utils
```

### Step 2: Move SQL Files to Triggers Directory

Move the SQL files to the triggers directory:

```bash
# Move SQL files to triggers directory
cp app/database/functions.sql app/database/triggers/functions.sql
cp app/database/core_trigger_functions.sql app/database/triggers/core_triggers.sql
```

## Phase 6: Documentation and Testing

### Step 1: Create Test Scripts for New Features

Create a test script: `tests/test_db_utils.py`

```python
# tests/test_db_utils.py
import sys
import os
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import test environment configuration first
from tests.test_environment import setup_test_environment

from app.config.db_config import DatabaseConfig
from utils.db_utils import get_backup_directory, ensure_directory

def test_db_config_get_active_env():
    """Test that DatabaseConfig.get_active_env() correctly identifies the environment"""
    # Should default to testing in test environment
    env = DatabaseConfig.get_active_env()
    assert env == 'testing', f"Expected 'testing', got '{env}'"

def test_db_config_get_database_url():
    """Test that DatabaseConfig.get_database_url_for_env() returns correct URLs"""
    # Test environment URLs
    test_url = DatabaseConfig.get_database_url_for_env('test')
    assert 'skinspire_test' in test_url, f"Expected test DB URL, got '{test_url}'"
    
    # Development environment URLs
    dev_url = DatabaseConfig.get_database_url_for_env('dev')
    assert 'skinspire_dev' in dev_url, f"Expected dev DB URL, got '{dev_url}'"

def test_get_backup_directory():
    """Test that get_backup_directory returns correct path and creates directory"""
    backup_dir = get_backup_directory()
    assert backup_dir.exists(), f"Backup directory not created: {backup_dir}"
    assert backup_dir.is_dir(), f"Backup path is not a directory: {backup_dir}"
    assert backup_dir.name == 'backups', f"Expected 'backups' directory, got '{backup_dir.name}'"

def test_ensure_directory():
    """Test that ensure_directory creates directory"""
    test_dir = Path('test_temp_dir')
    
    # Clean up if exists from previous test run
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    
    # Test creation
    ensure_directory(str(test_dir))
    assert test_dir.exists(), f"Directory not created: {test_dir}"
    assert test_dir.is_dir(), f"Path is not a directory: {test_dir}"
    
    # Clean up
    import shutil
    shutil.rmtree(test_dir)
```

### Step 2: Create Documentation for New Features

Update the comprehensive database management guide with information about the new scripts and features.

## Summary of Implemented Enhancements

This implementation plan preserves backward compatibility while adding significant new capabilities:

1. **Centralized Configuration**
   - Created `db_config.py` to standardize database configuration
   - Works with existing `.env` variables and environment detection

2. **Improved Database Backup**
   - Added dedicated backup manager module
   - Integrated with existing scripts
   - Added automatic backups before critical operations

3. **Enhanced Environment Synchronization**
   - Improved database copy capabilities
   - Added selective copy (schema-only, data-only)
   - Maintained backward compatibility with existing scripts

4. **Improved Migration Management**
   - Enhanced Alembic migrations integration
   - Added backup capabilities during migrations
   - Added migration history viewing
   - Added easy rollback functionality

5. **Expanded CLI Tools**
   - Extended `manage_db.py` with new commands
   - Created targeted command-line tools
   - Maintained backward compatibility

The implementation maintains backward compatibility by:
1. Creating wrapper scripts for existing entry points
2. Maintaining the same parameter structures
3. Using the same environment variables
4. Preserving existing behavior by default

This approach allows for a gradual transition to the enhanced tools while ensuring existing workflows continue to function without disruption.