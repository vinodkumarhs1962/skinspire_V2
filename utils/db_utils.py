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