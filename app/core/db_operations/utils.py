# app/core/db_operations/utils.py
"""
Shared utility functions for database operations.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union

# Add project root to path to ensure imports work consistently
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables for lazy loading
_db_config = None

def get_db_config():
    """Get DatabaseConfig, initializing it only when needed"""
    global _db_config
    if _db_config is None:
        try:
            from app.config.db_config import DatabaseConfig
            _db_config = DatabaseConfig
        except Exception as e:
            logger.error(f"Error accessing database configuration: {str(e)}")
            raise
    return _db_config

def normalize_env_name(env: Optional[str]) -> str:
    """
    Convert between short and full environment names consistently.
    
    Args:
        env: Environment name to normalize, can be None
        
    Returns:
        Normalized environment name
    """
    if env is None:
        # Try to get from environment variable first
        env = os.environ.get('FLASK_ENV', 'development')
        
    # Mapping from short to full names
    env_map = {
        'dev': 'development',
        'test': 'testing',
        'prod': 'production'
    }
    # Mapping from full to short names
    short_map = {
        'development': 'dev',
        'testing': 'test',
        'production': 'prod'
    }
    
    # Determine if we need full or short name based on input
    if env in env_map:
        # Convert short to full
        return env_map[env]
    elif env in short_map:
        # It's already a full name
        return env
    else:
        # Default to development
        return 'development'

def get_short_env_name(env: str) -> str:
    """
    Convert full environment name to short form.
    
    Args:
        env: Full environment name
        
    Returns:
        Short environment name
    """
    short_map = {
        'development': 'dev',
        'testing': 'test',
        'production': 'prod'
    }
    return short_map.get(env, env)

def get_db_url_components(db_url: str) -> Dict[str, str]:
    """
    Parse database URL into components.
    
    Args:
        db_url: Database URL in format postgresql://user:password@host:port/dbname
        
    Returns:
        Dictionary with parsed components
    """
    try:
        # Remove protocol
        url = db_url.split('://', 1)[1]
        
        # Split credentials and connection
        credentials, connection = url.split('@', 1)
        
        # Parse credentials
        user, password = credentials.split(':', 1) if ':' in credentials else (credentials, '')
        
        # Parse connection
        host_port, dbname = connection.split('/', 1)
        
        # Parse host/port
        host, port = host_port.split(':', 1) if ':' in host_port else (host_port, '5432')
        
        return {
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'dbname': dbname
        }
    except Exception as e:
        logger.error(f"Error parsing database URL: {str(e)}")
        raise ValueError(f"Invalid database URL format: {db_url}")

def setup_env_vars(components: Dict[str, str]) -> Dict[str, str]:
    """
    Set up environment variables for PostgreSQL commands.
    
    Args:
        components: Dictionary with database connection components
        
    Returns:
        Dictionary with environment variables
    """
    env_vars = os.environ.copy()
    if components.get('password'):
        env_vars['PGPASSWORD'] = components['password']
    return env_vars

def ensure_backup_dir() -> Path:
    """
    Ensure backups directory exists.
    
    Returns:
        Path to backups directory
    """
    backup_dir = project_root / 'backups'
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)
        logger.info(f"Created backups directory at {backup_dir}")
    return backup_dir