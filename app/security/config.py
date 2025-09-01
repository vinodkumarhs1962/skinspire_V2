# app/security/config.py

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import timedelta

@dataclass
class SecurityConfig:
    """Central configuration for all security features"""
    
    # Encryption Settings
    encryption_enabled: bool = False
    encryption_algorithm: str = "AES-256"
    key_rotation_days: int = 90
    encrypted_fields: Dict[str, bool] = field(default_factory=lambda: {})
    
    # Base Security Settings
    BASE_SECURITY_SETTINGS: Dict = field(default_factory=lambda: {
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
        
        # Rate Limiting
        'login_rate_limit': 5,  # requests per minute
        'rate_limit_window': 60,  # seconds
        
        # Audit
        'audit_enabled': True,
        'audit_retention_days': 365,
        'audit_level': 'INFO'
    })
    
    # Audit Settings
    audit_enabled: bool = True
    audit_retention_days: int = 365
    audit_level: str = "INFO"
    
    # Session Settings
    session_timeout: timedelta = field(default_factory=lambda: timedelta(hours=12))
    max_failed_attempts: int = 3
    lockout_duration: timedelta = field(default_factory=lambda: timedelta(minutes=30))
    
    # RBAC Settings
    enforce_rbac: bool = True
    default_role: str = "guest"
    
    def __post_init__(self):
        if self.encrypted_fields is None:
            self.encrypted_fields = {}
        
        if not hasattr(self, 'BASE_SECURITY_SETTINGS'):
            self.BASE_SECURITY_SETTINGS = {
                'session_timeout': self.session_timeout,
                'max_active_sessions': 5,
                'max_login_attempts': self.max_failed_attempts,
                'lockout_duration': self.lockout_duration,
                'audit_enabled': self.audit_enabled,
                'audit_retention_days': self.audit_retention_days
            }
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'SecurityConfig':
        """Create config from dictionary"""
        return cls(**{
            k: v for k, v in config_dict.items() 
            if k in cls.__dataclass_fields__
        })
    
    def get_hospital_config(self, hospital_settings: Dict) -> 'SecurityConfig':
        """Create hospital-specific configuration"""
        hospital_config = self.__dict__.copy()
        hospital_config.update(hospital_settings)
        return SecurityConfig.from_dict(hospital_config)
    
    def is_field_encrypted(self, field_name: str) -> bool:
        """Check if a field should be encrypted"""
        if not self.encryption_enabled:
            return False
        return self.encrypted_fields.get(field_name, False)
    
    def get_audit_config(self) -> Dict:
        """Get audit configuration"""
        return {
            'enabled': self.audit_enabled,
            'retention_days': self.audit_retention_days,
            'level': self.audit_level
        }
    
    def get_rbac_config(self) -> Dict:
        """Get RBAC configuration"""
        return {
            'enabled': self.enforce_rbac,
            'default_role': self.default_role
        }

class SecurityConfigManager:
    """Manages security configurations for different hospitals"""
    
    def __init__(self, default_config: Optional[SecurityConfig] = None):
        self.default_config = default_config or SecurityConfig()
        self.hospital_configs: Dict[str, SecurityConfig] = {}
    
    def get_hospital_config(self, hospital_id: str) -> SecurityConfig:
        """Get hospital-specific security configuration"""
        if hospital_id not in self.hospital_configs:
            return self.default_config
        return self.hospital_configs[hospital_id]
    
    def update_hospital_config(self, hospital_id: str, 
                             config_updates: Dict) -> SecurityConfig:
        """Update hospital-specific configuration"""
        current_config = self.get_hospital_config(hospital_id)
        new_config = SecurityConfig.from_dict({
            **current_config.__dict__,
            **config_updates
        })
        self.hospital_configs[hospital_id] = new_config
        return new_config
    
    def reset_hospital_config(self, hospital_id: str) -> None:
        """Reset hospital config to defaults"""
        if hospital_id in self.hospital_configs:
            del self.hospital_configs[hospital_id]