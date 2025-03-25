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