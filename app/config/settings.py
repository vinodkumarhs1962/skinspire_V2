# app/config/settings.py
"""
Application Settings Module

This module provides application-wide settings with environment-specific
configurations based on the centralized environment system.
"""

import os
import logging
from datetime import timedelta
from typing import Dict, Any
import secrets  # For secure key generation
from dotenv import load_dotenv
from pathlib import Path

# Import Environment for centralized environment handling
from app.core.environment import Environment, current_env

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings with environment-specific configurations"""
    
    # Environment (using centralized system)
    FLASK_ENV = current_env
    DEBUG = current_env != 'production'
    
    # Flask Core Settings
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database URLs (use DatabaseConfig)
    # DATABASE_URL will be set during initialization
    SQLALCHEMY_DATABASE_URI = None
    
    # Redis configuration for session management
    REDIS_URLS = {
        'development': os.getenv('DEV_REDIS_URL', 'redis://localhost:6379/0'),
        'testing': os.getenv('TEST_REDIS_URL', 'redis://localhost:6379/1'),
        'production': os.getenv('PROD_REDIS_URL')
    }
    
    # Encryption Settings
    MASTER_ENCRYPTION_KEY = os.getenv('MASTER_ENCRYPTION_KEY')
    ENCRYPTION_ENABLED = os.getenv('ENCRYPTION_ENABLED', 'True').lower() == 'true'
    
    # Base Security Settings
    BASE_SECURITY_SETTINGS = {
        # Session Management
        'session_timeout': timedelta(hours=12),
        'session_extend_on_access': True,
        'max_active_sessions': 5,
        
        # Password Policy
        'password_min_length': 12,
        'password_max_length': 128,
        'password_require_uppercase': True,
        'password_require_lowercase': True,
        'password_require_numbers': True,
        'password_require_special': True,
        'password_expiry_days': 90,
        'password_history_size': 5,
        'password_hash_rounds': 100000,
        
        # Account Security
        'max_login_attempts': 5,
        'lockout_duration': timedelta(minutes=30),
        'require_mfa': False,
        'mfa_issuer': 'Skinspire Clinic',
        
        # Encryption
        'encryption_algorithm': 'AES-256',
        'key_rotation_days': 90,
        'encrypted_fields': {
            'medical_info': True,
            'personal_info': True,
            'payment_info': True
        },

        # Add to BASE_SECURITY_SETTINGS
        'rate_limiting': {
            'login_rate_limit': 5,  # Maximum attempts
            'rate_limit_window': 300,  # 5 minutes in seconds
            'lockout_duration': 1800  # 30 minutes in seconds
        },
        
        # Audit
        'audit_enabled': True,
        'audit_retention_days': 365,
        'audit_level': 'INFO'
    }
    
    # Environment-specific security settings
    ENVIRONMENT_SECURITY_SETTINGS = {
        'development': {
            'require_mfa': False,
            'session_timeout': timedelta(days=1),
            'audit_retention_days': 30
        },
        'testing': {
            'require_mfa': False,
            'password_expiry_days': None,
            'audit_enabled': False
        },
        'production': {
            'session_timeout': timedelta(hours=8),
            'max_active_sessions': 3,
            'password_min_length': 14,
            'require_mfa': True,
            'audit_retention_days': 730  # 2 years
        }
    }
    
    def __init__(self):
        # Import here to avoid circular imports
        from app.config.db_config import DatabaseConfig
        
        try:
            # Get database URL for current environment
            self.DATABASE_URL = DatabaseConfig.get_database_url()
            self.SQLALCHEMY_DATABASE_URI = self.DATABASE_URL
            
            if not self.DATABASE_URL:
                logger.warning(f"Database URL not set for environment: {current_env}")
                
                # Try to set default values based on environment
                if current_env == 'development':
                    self.DATABASE_URL = os.getenv('DEV_DATABASE_URL', 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev')
                elif current_env == 'testing':
                    self.DATABASE_URL = os.getenv('TEST_DATABASE_URL', 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test')
                elif current_env == 'production':
                    self.DATABASE_URL = os.getenv('PROD_DATABASE_URL')
                
                # Update SQLAlchemy URI if we now have a URL
                if self.DATABASE_URL:
                    self.SQLALCHEMY_DATABASE_URI = self.DATABASE_URL
            
            # Validate Redis URL in production
            if current_env == 'production' and not self.REDIS_URL:
                logger.warning("Redis URL must be set in production")
            
            # Validate encryption key if encryption is enabled
            if self.ENCRYPTION_ENABLED and not self.MASTER_ENCRYPTION_KEY:
                logger.warning("Master encryption key must be set when encryption is enabled")
        
        except Exception as e:
            logger.warning(f"Settings initialization encountered an error: {e}")
    
    @property
    def REDIS_URL(self) -> str:
        """Get Redis URL for current environment"""
        return self.REDIS_URLS.get(current_env)
    
    @property
    def SECURITY_SETTINGS(self) -> Dict[str, Any]:
        """Get merged security settings for current environment"""
        env_settings = self.ENVIRONMENT_SECURITY_SETTINGS.get(current_env, {})
        return {
            **self.BASE_SECURITY_SETTINGS,
            **env_settings,
            'encryption_enabled': self.ENCRYPTION_ENABLED
        }
    
    def get_hospital_security_settings(self, hospital_id: str) -> Dict[str, Any]:
        """Get hospital-specific security settings"""
        # This method can be extended to load hospital-specific overrides
        # from the database if needed
        return self.SECURITY_SETTINGS
    
    def get_database_url_for_env(self, env: str) -> str:
        """
        Get database URL for a specific environment without changing the current environment.
        This method allows accessing different environment URLs without affecting the main DATABASE_URL property.
        
        Args:
            env: The environment to get the URL for (any format)
            
        Returns:
            The database URL for the specified environment
        """
        # Import here to avoid circular imports
        from app.config.db_config import DatabaseConfig
        return DatabaseConfig.get_database_url_for_env(env)

    def validate_database_url(self, env: str) -> bool:
        """
        Validate that a database URL exists for the specified environment.
        Useful for checking configurations before attempting connections.
        
        Args:
            env: The environment to validate
            
        Returns:
            True if the database URL exists for the environment
        """
        url = self.get_database_url_for_env(env)
        return bool(url)

# Create settings instance with more resilient initialization
try:
    settings = Settings()
except Exception as e:
    logger.error(f"Settings initialization failed: {e}")
    # Create a minimal settings instance to prevent crashes
    settings = object.__new__(Settings)
    settings.FLASK_ENV = current_env
    settings.DEBUG = current_env != 'production'