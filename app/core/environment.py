# app/core/environment.py
"""
Environment Module

This module provides a centralized system for determining and setting
the application environment (development, testing, or production).

It serves as the single source of truth for which environment is active,
ensuring consistency throughout the application.
"""

import os
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class Environment:
    """
    Central environment management class
    
    This class handles discovering, normalizing, and setting the
    application environment across different sources.
    """
    
    # Valid environment names and mappings
    VALID_ENVIRONMENTS = {
        'development': ['dev', 'development', 'develop', 'local'],
        'testing': ['test', 'testing', 'qa'],
        'production': ['prod', 'production']
    }
    
    # Environment variable names
    ENV_VAR_NAME = 'FLASK_ENV'
    OVERRIDE_VAR_NAME = 'SKINSPIRE_ENV'
    
    # Environment file name
    ENV_FILE_NAME = '.flask_env_type'
    
    @classmethod
    def discover(cls):
        """
        Discover the current environment from various sources.
        
        Priority order:
        1. SKINSPIRE_ENV environment variable (explicit override)
        2. .flask_env_type file
        3. FLASK_ENV environment variable
        4. Default to 'development'
        
        Returns:
            str: Normalized environment name ('development', 'testing', or 'production')
        """
        # 1. Check explicit override
        if cls.OVERRIDE_VAR_NAME in os.environ:
            env = os.environ[cls.OVERRIDE_VAR_NAME]
            logger.debug(f"Using environment from {cls.OVERRIDE_VAR_NAME}: {env}")
            return cls.normalize_env(env)
        
        # 2. Check environment file
        project_root = cls._get_project_root()
        env_file = project_root / cls.ENV_FILE_NAME
        
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    env = f.read().strip()
                    logger.debug(f"Using environment from {cls.ENV_FILE_NAME}: {env}")
                    return cls.normalize_env(env)
            except Exception as e:
                logger.warning(f"Error reading environment file: {e}")
        
        # 3. Check FLASK_ENV
        if cls.ENV_VAR_NAME in os.environ:
            env = os.environ[cls.ENV_VAR_NAME]
            logger.debug(f"Using environment from {cls.ENV_VAR_NAME}: {env}")
            return cls.normalize_env(env)
        
        # 4. Default
        logger.debug("No environment specified, defaulting to 'development'")
        return 'development'
    
    @classmethod
    def normalize_env(cls, env):
        """
        Normalize environment name to standard format.
        
        Args:
            env: Environment name in any format
            
        Returns:
            str: Normalized environment name ('development', 'testing', or 'production')
        """
        if not env:
            return 'development'
            
        env_lower = str(env).lower().strip()
        
        # Check against valid environment mappings
        for normalized, variants in cls.VALID_ENVIRONMENTS.items():
            if env_lower in variants:
                return normalized
        
        # Default to development for unknown values
        logger.warning(f"Unknown environment: '{env}', defaulting to 'development'")
        return 'development'
    
    @classmethod
    def get_short_name(cls, env):
        """
        Get short name (dev/test/prod) for environment.
        
        Args:
            env: Environment name in any format
            
        Returns:
            str: Short environment name ('dev', 'test', or 'prod')
        """
        normalized = cls.normalize_env(env)
        
        short_names = {
            'development': 'dev',
            'testing': 'test',
            'production': 'prod'
        }
        
        return short_names.get(normalized, 'dev')
    
    @classmethod
    def set_environment(cls, env):
        """
        Set the environment in all relevant places to ensure consistency.
        
        Args:
            env: Environment name in any format
            
        Returns:
            str: The normalized environment that was set
        """
        normalized = cls.normalize_env(env)
        short_name = cls.get_short_name(normalized)
        
        # 1. Set environment variables
        os.environ[cls.ENV_VAR_NAME] = normalized
        os.environ[cls.OVERRIDE_VAR_NAME] = normalized
        
        # 2. Update environment file
        try:
            project_root = cls._get_project_root()
            env_file = project_root / cls.ENV_FILE_NAME
            
            with open(env_file, 'w') as f:
                f.write(short_name)
                
            logger.debug(f"Updated {cls.ENV_FILE_NAME} with '{short_name}'")
        except Exception as e:
            logger.warning(f"Failed to update environment file: {e}")
        
        # 3. Update global module variable
        global current_env
        current_env = normalized
        
        logger.info(f"Environment set to: {normalized} ({short_name})")
        return normalized
    
    @classmethod
    def _get_project_root(cls):
        """
        Get the project root directory.
        
        Returns:
            Path: Project root path
        """
        # Try to get project root from current file location
        current_file = Path(__file__)
        
        # Go up 3 levels: file -> core -> app -> project_root
        project_root = current_file.parent.parent.parent
        
        return project_root
    
    @classmethod
    def is_production(cls):
        """Check if current environment is production"""
        return current_env == 'production'
    
    @classmethod
    def is_testing(cls):
        """Check if current environment is testing"""
        return current_env == 'testing'
    
    @classmethod
    def is_development(cls):
        """Check if current environment is development"""
        return current_env == 'development'

# Discover environment at module import time
current_env = Environment.discover()
logger.debug(f"Active environment: {current_env}")