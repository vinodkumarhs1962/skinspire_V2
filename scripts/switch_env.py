# scripts/switch_env.py
"""
DEPRECATED: This module is being updated to integrate with the centralized 
database configuration system. In the future, environment switching will be 
available through 'python scripts/manage_db.py switch-env'.

The current implementation maintains backward compatibility while integrating
with the centralized database configuration.
"""

import os
import sys
import argparse
import warnings
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import from core modules
try:
    from app.core.db_operations.utils import get_db_config, normalize_env_name, get_short_env_name
except ImportError:
    # Fallback if core modules not available
    get_db_config = None
    normalize_env_name = lambda x: x
    get_short_env_name = lambda x: x

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def switch_environment(env_type):
    """
    Switch the application environment
    
    Args:
        env_type: Target environment ('dev', 'test', 'prod')
        
    Returns:
        True if successful, False otherwise
    """
    warnings.warn(
        "This function is being updated. In the future, use 'python scripts/manage_db.py switch-env'.",
        PendingDeprecationWarning,
        stacklevel=2
    )
    
    if env_type not in ['dev', 'test', 'prod']:
        logger.error(f"Invalid environment type: {env_type}")
        logger.info("Valid options: dev, test, prod")
        return False
    
    # Map short environment names to full names
    env_map = {
        'dev': 'development',
        'test': 'testing',
        'prod': 'production'
    }
    
    # Get the full environment name
    full_env = env_map.get(env_type, env_type)

    # Create or update the environment type file
    env_type_file = os.path.join(project_root, '.flask_env_type')
    with open(env_type_file, 'w') as f:
        f.write(env_type)
    
    logger.info(f"Environment switched to: {env_type}")
    
    # Update .env file to match - this is optional
    env_file = os.path.join(project_root, '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        updated_lines = []
        for line in lines:
            if line.startswith('FLASK_ENV='):
                updated_lines.append(f'FLASK_ENV={full_env}\n')
            else:
                updated_lines.append(line)
        
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)
        
        logger.info(f".env file updated with FLASK_ENV={full_env}")
    
    # Notify about the change to the centralized configuration
    try:
        if get_db_config:
            db_config = get_db_config()
            logger.info(f"Using centralized database configuration from db_config.py")
            logger.info(f"Active environment: {db_config.get_active_env()}")
            logger.info(f"Database URL: {db_config.get_database_url()}")
    except Exception as e:
        logger.warning(f"Warning: Could not access centralized configuration: {e}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Switch application environment')
    parser.add_argument('env', choices=['dev', 'test', 'prod'], help='Target environment')
    parser.add_argument('--status', action='store_true', help='Show current environment status')
    args = parser.parse_args()
    
    if args.status:
        # Show current environment status
        logger.info("Current environment status:")
        
        # Check environment type file
        env_type_file = os.path.join(project_root, '.flask_env_type')
        if os.path.exists(env_type_file):
            with open(env_type_file, 'r') as f:
                env_type = f.read().strip()
            logger.info(f"Environment type file (.flask_env_type): {env_type}")
        else:
            logger.info("Environment type file (.flask_env_type) not found")
        
        # Check FLASK_ENV in .env file
        env_file = os.path.join(project_root, '.env')
        if os.path.exists(env_file):
            flask_env = None
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('FLASK_ENV='):
                        flask_env = line.strip().split('=', 1)[1]
                        break
            if flask_env:
                logger.info(f"FLASK_ENV in .env file: {flask_env}")
            else:
                logger.info("FLASK_ENV not found in .env file")
        else:
            logger.info(".env file not found")
        
        # Check environment variables
        logger.info(f"FLASK_ENV environment variable: {os.environ.get('FLASK_ENV', 'Not set')}")
        
        # Check centralized configuration if available
        try:
            if get_db_config:
                db_config = get_db_config()
                logger.info(f"Centralized configuration active environment: {db_config.get_active_env()}")
                
                # Display database URLs
                logger.info("Database URLs:")
                for env in ['development', 'testing', 'production']:
                    url = db_config.get_database_url_for_env(env)
                    # Mask password
                    if '://' in url and '@' in url:
                        parts = url.split('@')
                        credentials = parts[0].split('://')
                        if len(credentials) > 1 and ':' in credentials[1]:
                            user_pass = credentials[1].split(':')
                            url = f"{credentials[0]}://{user_pass[0]}:****@{parts[1]}"
                    logger.info(f"  {env}: {url}")
        except Exception as e:
            logger.warning(f"Warning: Could not access centralized configuration: {e}")
    else:
        # Switch environment
        success = switch_environment(args.env)
        
        if not success:
            sys.exit(1)
            
        # Display active database URL
        logger.info("Updated environment information:")
        
        try:
            # First try the centralized configuration
            if get_db_config:
                db_config = get_db_config()
                logger.info(f"Active environment: {db_config.get_active_env()}")
                
                # Get database URL - mask password for display
                db_url = db_config.get_database_url()
                if '://' in db_url and '@' in db_url:
                    parts = db_url.split('@')
                    credentials = parts[0].split('://')
                    if len(credentials) > 1 and ':' in credentials[1]:
                        user_pass = credentials[1].split(':')
                        db_url = f"{credentials[0]}://{user_pass[0]}:****@{parts[1]}"
                
                logger.info(f"Active database URL: {db_url}")
            else:
                # Fallback to legacy database service
                try:
                    from app.services.database_service import DatabaseService
                    logger.info(f"Active database URL: {DatabaseService.get_database_url()}")
                except ImportError:
                    logger.warning("Could not access database service for URL information")
        except Exception as e:
            logger.warning(f"Warning: Could not access database configuration: {e}")