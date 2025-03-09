# app/security/bridge.py
# At the top of bridge.py, modify the import to be explicit
from .config import SecurityConfig, SecurityConfigManager
from typing import Optional, Any
from functools import wraps
from flask import current_app, g

class SecurityBridge:
    """Bridge between old and new security implementations"""
    
    def __init__(self, config_manager: SecurityConfigManager):
        self.config_manager = config_manager
        self.legacy_mode = True  # Flag to control migration
    
    def get_encryption_handler(self, hospital_id: str):
        """Get appropriate encryption handler"""
        config = self.config_manager.get_hospital_config(hospital_id)
        
        if not config.encryption_enabled:
            return None
            
        if self.legacy_mode:
            return current_app.encryption  # Use existing encryption
        else:
            # Import and use new encryption when ready
            from .encryption.hospital_encryption import HospitalEncryption
            return HospitalEncryption(config)
    
    def encrypt_field(self, hospital_id: str, field_name: str, 
                     value: Any) -> Optional[str]:
        """Bridge for field encryption"""
        handler = self.get_encryption_handler(hospital_id)
        if not handler:
            return value
            
        config = self.config_manager.get_hospital_config(hospital_id)
        if not config.is_field_encrypted(field_name):
            return value
            
        return handler.encrypt_data(value)
    
    def decrypt_field(self, hospital_id: str, field_name: str, 
                     value: Any) -> Any:
        """Bridge for field decryption"""
        handler = self.get_encryption_handler(hospital_id)
        if not handler:
            return value
            
        config = self.config_manager.get_hospital_config(hospital_id)
        if not config.is_field_encrypted(field_name):
            return value
            
        return handler.decrypt_data(value)
    
    def check_permission(self, user_id: str, hospital_id: str, 
                        module: str, action: str) -> bool:
        """Bridge for permission checking"""
        config = self.config_manager.get_hospital_config(hospital_id)
        
        if not config.enforce_rbac:
            return True
            
        if self.legacy_mode:
            # Use existing permission check
            return current_app.security.check_permission(
                user_id, module, action
            )
        else:
            # Import and use new RBAC when ready
            from .authorization.rbac_manager import RBACManager
            return RBACManager().check_permission(
                user_id, hospital_id, module, action
            )
    
    def audit_log(self, hospital_id: str, action: str, 
                  details: dict) -> None:
        """Bridge for audit logging"""
        config = self.config_manager.get_hospital_config(hospital_id)
        
        if not config.audit_enabled:
            return
            
        if self.legacy_mode:
            # Use existing audit logging
            current_app.audit.log(action, details)
        else:
            # Import and use new audit logger when ready
            from .audit.audit_logger import AuditLogger
            AuditLogger().log(hospital_id, action, details)

def initialize_security(app, default_config: Optional[SecurityConfig] = None):
    """Initialize security bridge"""
    config_manager = SecurityConfigManager(default_config)
    bridge = SecurityBridge(config_manager)
    
    # Store in app context
    app.security_bridge = bridge
    
    # Migration helper
    def get_security():
        if not hasattr(g, 'security_bridge'):
            g.security_bridge = current_app.security_bridge
        return g.security_bridge
    
    app.get_security = get_security