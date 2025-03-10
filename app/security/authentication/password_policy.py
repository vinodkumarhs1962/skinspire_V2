# app/security/authentication/password_policy.py
import re

class PasswordPolicy:
    """Password policy enforcement and validation"""
    
    def __init__(self, min_length=8, require_uppercase=True, 
                 require_lowercase=True, require_digits=True,
                 require_special=True):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special
    
    def validate_complexity(self, password):
        """Validate password meets complexity requirements"""
        if len(password) < self.min_length:
            return False
            
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            return False
            
        if self.require_lowercase and not re.search(r'[a-z]', password):
            return False
            
        if self.require_digits and not re.search(r'[0-9]', password):
            return False
            
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
            
        return True
    
    def get_requirements_text(self):
        """Get human-readable password requirements"""
        reqs = [f"At least {self.min_length} characters"]
        
        if self.require_uppercase:
            reqs.append("At least one uppercase letter")
        if self.require_lowercase:
            reqs.append("At least one lowercase letter")
        if self.require_digits:
            reqs.append("At least one number")
        if self.require_special:
            reqs.append("At least one special character")
            
        return reqs