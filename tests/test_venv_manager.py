# tests/test_venv_manager.py

import pytest
import sys
import os
import shutil
from pathlib import Path
import subprocess
from scripts.venv_manager import VenvManager

@pytest.fixture
def test_venv():
    """Fixture to provide a VenvManager instance with test paths"""
    # Use a temporary test environment name
    manager = VenvManager(venv_name="test-skinspire-env")
    
    # Clean up any existing test environment
    if manager.venv_path.exists():
        shutil.rmtree(manager.venv_path)
    
    yield manager
    
    # Cleanup after tests
    if manager.venv_path.exists():
        shutil.rmtree(manager.venv_path)

def test_initial_setup(test_venv):
    """Test initial manager setup and path configurations"""
    assert test_venv.venv_name == "test-skinspire-env"
    assert "test-skinspire-env" in str(test_venv.venv_path)
    assert test_venv.requirements_path.exists()

def test_venv_health_check_nonexistent(test_venv):
    """Test health check on non-existent environment"""
    assert not test_venv.check_venv_health()

def test_venv_creation(test_venv):
    """Test virtual environment creation"""
    assert test_venv.create_venv()
    assert test_venv.venv_path.exists()
    assert test_venv.scripts_path.exists()
    assert test_venv.python_path.exists()
    assert test_venv.pip_path.exists()

def test_venv_health_check_after_creation(test_venv):
    """Test health check after environment creation"""
    test_venv.create_venv()
    assert test_venv.check_venv_health()

def test_package_detection(test_venv):
    """Test package detection and comparison"""
    # Create environment first
    test_venv.create_venv()
    
    # Get required packages
    required = test_venv.get_required_packages()
    assert required, "No packages found in requirements.txt"
    
    # Get installed packages before installation
    installed_before = test_venv.get_installed_packages()
    
    # Install a test package
    subprocess.run([
        str(test_venv.pip_path),
        "install",
        "pytest==8.3.4"  # Use a specific version
    ], check=True)
    
    # Get installed packages after installation
    installed_after = test_venv.get_installed_packages()
    assert 'pytest' in installed_after
    assert installed_after['pytest'] == '8.3.4'

def test_force_recreation(test_venv):
    """Test forced recreation of environment"""
    # Create initial environment
    test_venv.create_venv()
    initial_creation_time = test_venv.venv_path.stat().st_mtime
    
    # Force recreate
    test_venv.create_venv(force=True)
    new_creation_time = test_venv.venv_path.stat().st_mtime
    
    assert new_creation_time > initial_creation_time

def test_new_environment_name(test_venv):
    """Test creating environment with new name"""
    new_name = "another-test-env"
    manager = VenvManager(venv_name=new_name)
    
    try:
        assert manager.venv_name == new_name
        assert new_name in str(manager.venv_path)
        
        # Create the environment
        assert manager.create_venv()
        assert manager.venv_path.exists()
        
    finally:
        # Cleanup
        if manager.venv_path.exists():
            shutil.rmtree(manager.venv_path)

def test_package_installation(test_venv):
    """Test package installation process"""
    # Create environment
    test_venv.create_venv()
    
    # Should successfully install packages
    assert test_venv.check_and_install_packages()
    
    # Verify some key packages are installed
    installed = test_venv.get_installed_packages()
    required = test_venv.get_required_packages()
    
    for package in ['flask', 'sqlalchemy', 'pytest']:  # Test a few key packages
        if package in required:
            assert package in installed
            if required[package]:  # If version was specified
                assert installed[package] == required[package]

def test_logging(test_venv):
    """Test logging functionality"""
    # Test normal log
    test_message = "Test log message"
    test_venv.log(test_message)
    assert any(log["message"] == test_message and not log["is_error"] 
              for log in test_venv.logs)
    
    # Test error log
    error_message = "Test error message"
    test_venv.log(error_message, error=True)
    assert any(log["message"] == error_message and log["is_error"] 
              for log in test_venv.logs)

def test_complete_setup(test_venv):
    """Test complete setup process"""
    assert test_venv.run()
    assert test_venv.check_venv_health()
    
    # Verify packages are installed
    installed = test_venv.get_installed_packages()
    required = test_venv.get_required_packages()
    
    # Check if all required packages are installed
    for package, version in required.items():
        assert package in installed
        if version:
            assert installed[package] == version

@pytest.mark.skipif(sys.platform != "win32", reason="Windows specific test")
def test_windows_paths(test_venv):
    """Test Windows-specific path configurations"""
    assert test_venv.python_path.name == "python.exe"
    assert test_venv.pip_path.name == "pip.exe"
    assert "Scripts" in str(test_venv.scripts_path)

@pytest.mark.skipif(sys.platform == "win32", reason="Unix specific test")
def test_unix_paths(test_venv):
    """Test Unix-specific path configurations"""
    assert test_venv.python_path.name == "python"
    assert test_venv.pip_path.name == "pip"
    assert "bin" in str(test_venv.scripts_path)