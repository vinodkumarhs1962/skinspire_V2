# app/config/env_setup.py
"""
Environment Setup Module

This module provides functions to set up the environment consistently
across different entry points (web app, CLI tools, scripts, etc.)

It ensures database URLs and other environment variables are set correctly
before other modules are imported, preventing issues during initialization.
"""

import os
import sys
from pathlib import Path
import logging

# Import Environment for centralized environment handling
from app.core.environment import Environment, current_env

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """
    Set up environment variables needed for database operations.
    
    This function should be called before any app modules are imported
    to ensure database URLs and other environment variables are properly set.
    """
    logger.debug(f"Setting up environment for: {current_env}")
    
    # Set database URLs if not already set
    if current_env == 'testing' and not os.environ.get('TEST_DATABASE_URL'):
        os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
        logger.debug("Set TEST_DATABASE_URL environment variable")
    
    elif current_env == 'development' and not os.environ.get('DEV_DATABASE_URL'):
        os.environ['DEV_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
        logger.debug("Set DEV_DATABASE_URL environment variable")
    
    elif current_env == 'production' and not os.environ.get('PROD_DATABASE_URL'):
        os.environ['PROD_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod'
        logger.debug("Set PROD_DATABASE_URL environment variable")

    # Set other environment variables as needed
    # For example, disabling nested transactions for testing
    if current_env == 'testing' and 'USE_NESTED_TRANSACTIONS' not in os.environ:
        os.environ['USE_NESTED_TRANSACTIONS'] = 'False'
        logger.debug("Disabled nested transactions for testing")

    return True

def load_env_from_dotenv():
    """
    Load environment variables from .env file if available.
    
    Returns:
        bool: True if .env was loaded successfully, False otherwise
    """
    try:
        from dotenv import load_dotenv
        # Find the project root
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / '.env'
        
        if env_path.exists():
            loaded = load_dotenv(dotenv_path=env_path)
            if loaded:
                logger.debug(f"Loaded environment variables from {env_path}")
            return loaded
        else:
            logger.debug(f"No .env file found at {env_path}")
            return False
    except ImportError:
        logger.debug("python-dotenv not installed, skipping .env loading")
        return False

def set_dev_environment():
    """Set up development environment"""
    Environment.set_environment('development')
    setup_environment()
    return current_env

def set_test_environment():
    """Set up test environment"""
    Environment.set_environment('testing')
    setup_environment()
    return current_env

def set_prod_environment():
    """Set up production environment"""
    Environment.set_environment('production')
    setup_environment()
    return current_env

def get_active_environment():
    """
    Get active environment from the centralized Environment class.
    
    Returns:
        str: The current environment ('development', 'testing', or 'production')
    """
    return current_env

def ensure_database_urls():
    """
    Ensure database URLs are set in environment variables.
    This should be called before settings initialization.
    """
    # Set database URLs if not already set
    if current_env == 'development' and not os.environ.get('DEV_DATABASE_URL'):
        os.environ['DEV_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
    elif current_env == 'testing' and not os.environ.get('TEST_DATABASE_URL'):
        os.environ['TEST_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test'
    elif current_env == 'production' and not os.environ.get('PROD_DATABASE_URL'):
        os.environ['PROD_DATABASE_URL'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod'
    
    return True

# Auto-execute setup when imported
load_env_from_dotenv()
environment_configured = setup_environment()
ensure_database_urls()

logger.debug(f"Environment configured: {environment_configured}, FLASK_ENV={current_env}")