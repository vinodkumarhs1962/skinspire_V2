# app/core/db_operations/restore.py
"""
Database restore operations.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union

from .utils import (
    get_db_config, normalize_env_name, get_short_env_name,
    get_db_url_components, setup_env_vars, ensure_backup_dir,
    logger, project_root
)
from .backup import backup_database
from .triggers import apply_triggers

def restore_database(env: str, backup_file: Union[str, Path]) -> bool:
    """
    Restore database from backup.
    
    Args:
        env: Target environment ('dev', 'test', 'prod')
        backup_file: Path to backup file
        
    Returns:
        True if successful, False otherwise
    """
    # Check if FLASK_ENV is set and ensure it's compatible with the requested env
    flask_env = os.environ.get('FLASK_ENV')
    if flask_env:
        env_map = {'development': 'dev', 'testing': 'test', 'production': 'prod'}
        expected_env = env_map.get(flask_env)
        
        if expected_env and expected_env != env:
            logger.warning(
                f"Warning: Requested environment '{env}' doesn't match FLASK_ENV '{flask_env}'. "
                f"Using '{expected_env}' based on FLASK_ENV."
            )
            env = expected_env
    
    # Get DatabaseConfig
    db_config = get_db_config()
    
    # Normalize environment name
    full_env = normalize_env_name(env)
    short_env = get_short_env_name(full_env)
    
    # Ensure backup file exists
    backup_path = Path(backup_file)
    if not backup_path.exists():
        # Try with backups directory prefix
        backup_dir = ensure_backup_dir()
        backup_path = backup_dir / backup_file
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False
    
    # Get database URL
    db_url = db_config.get_database_url_for_env(full_env)
    if not db_url:
        logger.error(f"No database URL found for environment: {full_env}")
        return False
    
    try:
        # Parse URL to get connection parameters
        components = get_db_url_components(db_url)
        
        # Create backup of current database before restoring
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pre_restore_name = f"{short_env}_pre_restore_{timestamp}.sql"
        
        logger.info(f"Creating backup before restore: {pre_restore_name}")
        success, pre_restore_path = backup_database(env=short_env, output_file=pre_restore_name)
        
        if not success:
            logger.warning("Failed to create pre-restore backup, continuing with restore")
        
        # Set environment variables for psql
        env_vars = setup_env_vars(components)
        
        try:
            # Prepare database for restore
            logger.info("Preparing database for restore...")
            reset_cmd = [
                'psql',
                '-h', components['host'],
                '-p', components['port'],
                '-U', components['user'],
                '-d', components['dbname'],
                '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
            ]
            
            subprocess.run(reset_cmd, env=env_vars, check=True, capture_output=True)
            
            # Restore from backup
            logger.info(f"Restoring from backup: {backup_path}")
            restore_cmd = [
                'psql',
                '-h', components['host'],
                '-p', components['port'],
                '-U', components['user'],
                '-d', components['dbname'],
                '-f', str(backup_path)
            ]
            
            subprocess.run(restore_cmd, env=env_vars, check=True, capture_output=True)
            
            logger.info("Database restored successfully")
            
            # Re-apply triggers
            logger.info("Re-applying database triggers...")
            triggers_success = apply_triggers(env=short_env)
            
            if not triggers_success:
                logger.warning("Failed to re-apply database triggers")
                
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Restore failed: {e}")
            if e.stdout:
                logger.debug(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            logger.info(f"You can try restoring the pre-restore backup: {pre_restore_path}")
            return False
        finally:
            # Clean up password from environment
            if 'PGPASSWORD' in env_vars:
                del env_vars['PGPASSWORD']
    except Exception as e:
        logger.error(f"Restore process error: {str(e)}")
        return False