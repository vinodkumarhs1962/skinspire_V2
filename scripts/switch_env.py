# scripts/switch_env.py

import os
import sys
from pathlib import Path
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def switch_environment(env_type):
    """Switch the application environment"""
    if env_type not in ['dev', 'test', 'prod']:
        logger.error(f"Invalid environment type: {env_type}")
        logger.info("Valid options: dev, test, prod")
        return False
    
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
                updated_lines.append(f'FLASK_ENV={env_type}\n')
            else:
                updated_lines.append(line)
        
        with open(env_file, 'w') as f:
            f.writelines(updated_lines)
        
        logger.info(f".env file updated with FLASK_ENV={env_type}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Please specify an environment: dev, test, or prod")
        sys.exit(1)
    
    env_type = sys.argv[1].lower()
    success = switch_environment(env_type)
    
    if not success:
        sys.exit(1)
    
    # Display active database URL
    from app.services.database_service import DatabaseService
    logger.info(f"Active database URL: {DatabaseService.get_database_url()}")