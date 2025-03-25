# app/core/db_operations/migration.py
"""
Database migration operations.
"""

import os
import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Union

from .utils import (
    get_db_config, normalize_env_name, get_short_env_name,
    logger, project_root
)
from .backup import backup_database
from .triggers import apply_triggers

def create_migration(message: str, env: str, backup: bool = True) -> Tuple[bool, Optional[Path]]:
    """
    Create database migration.
    
    Args:
        message: Migration message
        env: Target environment
        backup: Whether to create backup before migration
        
    Returns:
        Tuple of (success, migration_file_path)
    """
    # Get DatabaseConfig
    db_config = get_db_config()
    
    # Normalize environment name
    full_env = normalize_env_name(env)
    short_env = get_short_env_name(full_env)
    
    # Create backup if requested
    if backup:
        logger.info(f"Creating backup before migration...")
        backup_success, _ = backup_database(env=short_env)
        if not backup_success:
            logger.warning("Failed to create pre-migration backup")
    
    # Create migration
    logger.info(f"Creating migration: {message}")
    
    # Set environment variables
    current_env = os.environ.get('FLASK_ENV')
    os.environ['FLASK_ENV'] = full_env
    
    try:
        # Run flask db migrate
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'migrate', '-m', message],
            check=True, 
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.splitlines():
            logger.info(line)
        
        # Find the newly created migration file
        migrations_dir = project_root / 'migrations' / 'versions'
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob('*.py'), key=lambda p: p.stat().st_mtime, reverse=True)
            if migration_files:
                logger.info(f"Created migration file: {migration_files[0]}")
                return True, migration_files[0]
            else:
                logger.warning("No migration file found. Migration likely didn't detect any changes.")
                return False, None
        else:
            logger.warning("Migrations directory not found after migration command")
            return False, None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e}")
        if e.stdout:
            logger.debug(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        return False, None
    finally:
        # Restore original environment
        if current_env:
            os.environ['FLASK_ENV'] = current_env
        else:
            os.environ.pop('FLASK_ENV', None)

def apply_migration(env: str) -> bool:
    """
    Apply pending migrations.
    
    Args:
        env: Target environment
        
    Returns:
        True if successful, False otherwise
    """
    # Get DatabaseConfig
    db_config = get_db_config()
    
    # Normalize environment name
    full_env = normalize_env_name(env)
    short_env = get_short_env_name(full_env)
    
    # Set environment variables
    current_env = os.environ.get('FLASK_ENV')
    os.environ['FLASK_ENV'] = full_env
    
    try:
        # Run flask db upgrade
        logger.info("Applying migrations...")
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'upgrade'],
            check=True,
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.splitlines():
            logger.info(line)
        
        # Re-apply triggers
        logger.info("Re-applying database triggers...")
        triggers_success = apply_triggers(env=short_env)
        
        if not triggers_success:
            logger.warning("Failed to re-apply database triggers")
            
        logger.info("Migration applied successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration application failed: {e}")
        if e.stdout:
            logger.debug(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        return False
    finally:
        # Restore original environment
        if current_env:
            os.environ['FLASK_ENV'] = current_env
        else:
            os.environ.pop('FLASK_ENV', None)

def rollback_migration(env: str, steps: int = 1) -> bool:
    """
    Roll back migrations.
    
    Args:
        env: Target environment
        steps: Number of steps to roll back
        
    Returns:
        True if successful, False otherwise
    """
    # Get DatabaseConfig
    db_config = get_db_config()
    
    # Normalize environment name
    full_env = normalize_env_name(env)
    short_env = get_short_env_name(full_env)
    
    # Create backup before rollback
    logger.info(f"Creating backup before rollback...")
    backup_success, _ = backup_database(env=short_env)
    if not backup_success:
        logger.warning("Failed to create pre-rollback backup")
    
    # Get current migration history
    migrations_dir = project_root / 'migrations' / 'versions'
    if not migrations_dir.exists():
        logger.error("Migrations directory not found")
        return False
        
    migration_files = sorted(migrations_dir.glob('*.py'), key=lambda p: p.stat().st_mtime)
    if len(migration_files) < steps:
        logger.error(f"Cannot roll back {steps} migrations - only {len(migration_files)} migrations exist")
        return False
    
    # Set environment variables
    current_env = os.environ.get('FLASK_ENV')
    os.environ['FLASK_ENV'] = full_env
    
    try:
        # Determine downgrade command
        if steps == 1:
            downgrade_cmd = ['db', 'downgrade', '-1']
        else:
            # Find the revision to roll back to
            target_revision = None
            if len(migration_files) > steps:
                # Extract revision from migration file
                target_file = migration_files[-(steps+1)]
                with open(target_file, 'r') as f:
                    content = f.read()
                    # Try to extract revision
                    rev_match = re.search(r'revision\s*=\s*[\'"](.*?)[\'"]', content)
                    if rev_match:
                        target_revision = rev_match.group(1)
            
            if target_revision:
                downgrade_cmd = ['db', 'downgrade', target_revision]
            else:
                downgrade_cmd = ['db', 'downgrade', f'-{steps}']
        
        # Run flask db downgrade
        logger.info(f"Rolling back {steps} migration(s)...")
        result = subprocess.run(
            [sys.executable, '-m', 'flask'] + downgrade_cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        for line in result.stdout.splitlines():
            logger.info(line)
        
        logger.info("Migration rollback completed successfully")
        
        # Re-apply triggers
        logger.info("Re-applying database triggers...")
        triggers_success = apply_triggers(env=short_env)
        
        if not triggers_success:
            logger.warning("Failed to re-apply database triggers")
            
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration rollback failed: {e}")
        if e.stdout:
            logger.debug(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        return False
    finally:
        # Restore original environment
        if current_env:
            os.environ['FLASK_ENV'] = current_env
        else:
            os.environ.pop('FLASK_ENV', None)

def show_migrations() -> List[Dict[str, Any]]:
    """
    Get migration history.
    
    Returns:
        List of migration information dictionaries
    """
    migrations_dir = project_root / 'migrations' / 'versions'
    if not migrations_dir.exists():
        logger.warning("No migrations directory found")
        return []
        
    migration_files = sorted(migrations_dir.glob('*.py'), key=lambda p: p.stat().st_mtime)
    
    if not migration_files:
        logger.warning("No migrations found")
        return []
    
    migrations_info = []
    for i, migration in enumerate(migration_files):
        # Extract revision and description from file
        revision = ""
        description = migration.stem.split('_', 1)[1].replace('_', ' ') if '_' in migration.stem else migration.stem
        
        with open(migration, 'r') as f:
            content = f.read()
            # Extract revision
            rev_match = re.search(r'revision\s*=\s*[\'"](.*?)[\'"]', content)
            if rev_match:
                revision = rev_match.group(1)
            
            # Try to extract description from docstring
            doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
            if doc_match:
                first_line = doc_match.group(1).strip().split('\n')[0]
                if first_line:
                    description = first_line
        
        # Format creation time
        created_at = datetime.fromtimestamp(migration.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        migrations_info.append({
            'id': i + 1,
            'revision': revision,
            'short_revision': revision[:8] if revision else '',
            'description': description,
            'filename': migration.name,
            'path': str(migration),
            'created_at': created_at,
            'timestamp': migration.stat().st_mtime
        })
    
    return migrations_info