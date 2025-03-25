# app/config/db_config.py
"""
Database Configuration Module

This module provides centralized database configuration based on the
current environment, while maintaining backward compatibility with
existing code.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import Environment for centralized environment handling
from app.core.environment import Environment, current_env

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Centralized database configuration that preserves backward compatibility"""
    
    # Default configuration with fallbacks
    DEFAULT_CONFIG = {
        'development': {
            'url': 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev',
            'echo': True,
            'pool_size': 5,
            'use_nested_transactions': True,
            'backup_before_migration': True
        },
        'testing': {
            'url': 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test',
            'echo': False,
            'pool_size': 3,
            'use_nested_transactions': False,
            'backup_before_migration': False
        },
        'production': {
            'url': 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod',
            'echo': False,
            'pool_size': 10,
            'use_nested_transactions': True,
            'backup_before_migration': True
        }
    }
    
    @classmethod
    def get_active_env(cls) -> str:
        """
        Get active environment using the centralized Environment class.
        """
        return current_env
    
    @classmethod
    def get_database_url_for_env(cls, env: str) -> str:
        """
        Get database URL for environment - maintains compatibility with
        existing database_service.py logic.
        """
        # Normalize environment name
        normalized_env = Environment.normalize_env(env)
        
        # Check environment variables first (existing approach)
        if normalized_env == 'production':
            url = os.environ.get('PROD_DATABASE_URL')
        elif normalized_env == 'testing':
            url = os.environ.get('TEST_DATABASE_URL')
        else:  # Default to development
            url = os.environ.get('DEV_DATABASE_URL')
        
        # Fall back to defaults if not in environment
        if not url:
            config = cls.DEFAULT_CONFIG.get(normalized_env, cls.DEFAULT_CONFIG['development'])
            url = config.get('url')
            
        return url
    
    @classmethod
    def get_database_url(cls) -> str:
        """
        Get database URL for active environment.
        """
        return cls.get_database_url_for_env(current_env)
    
    @classmethod
    def get_config(cls, env: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete configuration for specified environment.
        
        Args:
            env: Environment name (any format)
                If None, uses active environment
                
        Returns:
            Dictionary with configuration values
        """
        if env is None:
            normalized_env = current_env
        else:
            normalized_env = Environment.normalize_env(env)
        
        # Start with default config
        config = cls.DEFAULT_CONFIG.get(normalized_env, cls.DEFAULT_CONFIG['development']).copy()
        
        # Override with environment variables
        if normalized_env == 'production':
            if os.environ.get('PROD_DATABASE_URL'):
                config['url'] = os.environ.get('PROD_DATABASE_URL')
        elif normalized_env == 'testing':
            if os.environ.get('TEST_DATABASE_URL'):
                config['url'] = os.environ.get('TEST_DATABASE_URL')
        elif normalized_env == 'development':
            if os.environ.get('DEV_DATABASE_URL'):
                config['url'] = os.environ.get('DEV_DATABASE_URL')
        
        # Override use_nested_transactions if explicitly set
        if 'USE_NESTED_TRANSACTIONS' in os.environ:
            config['use_nested_transactions'] = os.environ.get('USE_NESTED_TRANSACTIONS').lower() in ('true', '1', 'yes')
        
        return config