# app/core/db_operations/backup.py
"""
Database backup operations.
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

def backup_database(env: str, output_file: Optional[str] = None) -> Tuple[bool, Optional[Path]]:
    """
    Create database backup.
    
    Args:
        env: Environment to backup ('dev', 'test', 'prod')
        output_file: Optional specific output filename
        
    Returns:
        Tuple of (success, backup_file_path)
    """
    # Get DatabaseConfig
    db_config = get_db_config()
    
    # Normalize environment name to full form
    full_env = normalize_env_name(env)
    
    # Get short form of environment name for display/filenames
    short_env = get_short_env_name(full_env)
    
    # Get database URL directly from config
    db_url = db_config.get_database_url_for_env(full_env)
    if not db_url:
        logger.error(f"No database URL found for environment: {full_env}")
        return False, None
    
    # Create backups directory if needed
    backup_dir = ensure_backup_dir()
    
    # Generate backup filename if not provided
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_file or f"{short_env}_backup_{timestamp}.sql"
    
    try:
        # Parse URL to get connection parameters
        components = get_db_url_components(db_url)
        
        # Set environment variables for pg_dump
        env_vars = setup_env_vars(components)
        
        # Build pg_dump command
        backup_path = backup_dir / output_file
        dump_cmd = [
            'pg_dump',
            '-h', components['host'],
            '-p', components['port'],
            '-U', components['user'],
            '-d', components['dbname'],
            '-f', str(backup_path),
            '--verbose'
        ]
        
        logger.info(f"Creating backup of {short_env} database to {backup_path}")
        
        # Run pg_dump
        try:
            result = subprocess.run(
                dump_cmd,
                env=env_vars,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Check if backup was created successfully
            if backup_path.exists() and backup_path.stat().st_size > 0:
                logger.info(f"Backup created successfully: {backup_path}")
                return True, backup_path
            else:
                logger.warning(f"Backup file empty or not created: {backup_path}")
                return False, None
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup failed: {e}")
            if e.stdout:
                logger.debug(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
            return False, None
        finally:
            # Clean up password from environment
            if 'PGPASSWORD' in env_vars:
                del env_vars['PGPASSWORD']
    except Exception as e:
        logger.error(f"Backup process error: {str(e)}")
        return False, None

def list_backups() -> List[Dict[str, Any]]:
    """
    List available database backups.
    
    Returns:
        List of backup information dictionaries
    """
    backup_dir = project_root / 'backups'
    if not backup_dir.exists():
        logger.warning("Backups directory not found")
        return []
    
    backups = sorted(backup_dir.glob('*.sql'), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not backups:
        logger.warning("No database backups found")
        return []
    
    backup_info = []
    for i, backup in enumerate(backups):
        size_kb = backup.stat().st_size / 1024
        mod_time = datetime.fromtimestamp(backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        # Try to determine environment from filename
        env = None
        for env_name in ['dev', 'test', 'prod']:
            if env_name in backup.name:
                env = env_name
                break
        
        backup_info.append({
            'id': i + 1,
            'name': backup.name,
            'path': str(backup),
            'size_kb': round(size_kb, 1),
            'modified': mod_time,
            'environment': env,
            'timestamp': backup.stat().st_mtime
        })
    
    return backup_info