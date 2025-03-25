# tests/test_db_utils.py
import sys
import os
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import test environment configuration first
from tests.test_environment import setup_test_environment

from app.config.db_config import DatabaseConfig
from utils.db_utils import get_backup_directory, ensure_directory

def test_db_config_get_active_env():
    """Test that DatabaseConfig.get_active_env() correctly identifies the environment"""
    # Should default to testing in test environment
    env = DatabaseConfig.get_active_env()
    assert env == 'testing', f"Expected 'testing', got '{env}'"

def test_db_config_get_database_url():
    """Test that DatabaseConfig.get_database_url_for_env() returns correct URLs"""
    # Test environment URLs
    test_url = DatabaseConfig.get_database_url_for_env('test')
    assert 'skinspire_test' in test_url, f"Expected test DB URL, got '{test_url}'"
    
    # Development environment URLs
    dev_url = DatabaseConfig.get_database_url_for_env('dev')
    assert 'skinspire_dev' in dev_url, f"Expected dev DB URL, got '{dev_url}'"

def test_get_backup_directory():
    """Test that get_backup_directory returns correct path and creates directory"""
    backup_dir = get_backup_directory()
    assert backup_dir.exists(), f"Backup directory not created: {backup_dir}"
    assert backup_dir.is_dir(), f"Backup path is not a directory: {backup_dir}"
    assert backup_dir.name == 'backups', f"Expected 'backups' directory, got '{backup_dir.name}'"

def test_ensure_directory():
    """Test that ensure_directory creates directory"""
    test_dir = Path('test_temp_dir')
    
    # Clean up if exists from previous test run
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)
    
    # Test creation
    ensure_directory(str(test_dir))
    assert test_dir.exists(), f"Directory not created: {test_dir}"
    assert test_dir.is_dir(), f"Path is not a directory: {test_dir}"
    
    # Clean up
    import shutil
    shutil.rmtree(test_dir)