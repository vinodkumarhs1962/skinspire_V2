# tests/test_security/test_password_policy.py
# pytest tests/test_security/test_password_policy.py
import pytest
from app.security.authentication.password_policy import PasswordPolicy  # Adjust import if needed

def test_password_complexity():
    """Test password complexity validation"""
    policy = PasswordPolicy()
    
    # Test valid passwords
    assert policy.validate_complexity("Secure123!") is True
    assert policy.validate_complexity("P@ssw0rd") is True
    
    # Test invalid passwords
    assert policy.validate_complexity("password") is False  # No uppercase, numbers or special chars
    assert policy.validate_complexity("Password") is False  # No numbers or special chars
    assert policy.validate_complexity("password123") is False  # No uppercase or special chars
    assert policy.validate_complexity("Pass123") is False  # Too short