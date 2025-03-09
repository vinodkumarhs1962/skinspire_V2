# app/security/routes/security_management.py

from flask import Blueprint, current_app, request, jsonify
from flask_login import login_required
from functools import wraps
from ..config import SecurityConfig
from ..bridge import SecurityBridge
from . import security_bp

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security = current_app.get_security()
        if not security.check_permission(
            request.user_id,
            request.hospital_id,
            'security',
            'manage'
        ):
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@security_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'})

@security_bp.route('/config', methods=['GET'])
def get_config():
    """Get security configuration"""
    return jsonify({
        'encryption_enabled': True,
        'audit_enabled': True
    })

@security_bp.route('/hospital/<uuid:hospital_id>/config', methods=['GET'])
@login_required
@admin_required
def get_security_config(hospital_id):
    """Get hospital security configuration"""
    security = current_app.get_security()
    config = security.config_manager.get_hospital_config(str(hospital_id))
    
    return jsonify({
        'encryption_enabled': config.encryption_enabled,
        'audit_enabled': config.audit_enabled,
        'rbac_enabled': config.enforce_rbac,
        'encrypted_fields': config.encrypted_fields or {},
        'audit_retention_days': config.audit_retention_days,
        'key_rotation_days': config.key_rotation_days
    })

@security_bp.route('/hospital/<uuid:hospital_id>/config', methods=['PUT'])
@login_required
@admin_required
def update_security_config(hospital_id):
    """Update hospital security configuration"""
    data = request.get_json()
    security = current_app.get_security()
    
    try:
        # Update configuration
        new_config = security.config_manager.update_hospital_config(
            str(hospital_id),
            data
        )
        
        # Audit the change
        security.audit_log(
            str(hospital_id),
            'SECURITY_CONFIG_UPDATE',
            {'changes': data}
        )
        
        return jsonify({
            'status': 'success',
            'config': {
                'encryption_enabled': new_config.encryption_enabled,
                'audit_enabled': new_config.audit_enabled,
                'rbac_enabled': new_config.enforce_rbac
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@security_bp.route('/hospital/<uuid:hospital_id>/encryption/fields', methods=['GET'])
@login_required
@admin_required
def get_encrypted_fields(hospital_id):
    """Get list of encrypted fields"""
    security = current_app.get_security()
    config = security.config_manager.get_hospital_config(str(hospital_id))
    
    return jsonify({
        'encrypted_fields': config.encrypted_fields or {}
    })

@security_bp.route('/hospital/<uuid:hospital_id>/encryption/fields', methods=['PUT'])
@login_required
@admin_required
def update_encrypted_fields(hospital_id):
    """Update encrypted fields configuration"""
    data = request.get_json()
    security = current_app.get_security()
    
    try:
        # Update configuration
        new_config = security.config_manager.update_hospital_config(
            str(hospital_id),
            {'encrypted_fields': data.get('fields', {})}
        )
        
        # Audit the change
        security.audit_log(
            str(hospital_id),
            'ENCRYPTED_FIELDS_UPDATE',
            {'fields': data.get('fields', {})}
        )
        
        return jsonify({
            'status': 'success',
            'encrypted_fields': new_config.encrypted_fields
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@security_bp.route('/hospital/<uuid:hospital_id>/encryption/rotate', methods=['POST'])
@login_required
@admin_required
def rotate_encryption_key(hospital_id):
    """Rotate hospital encryption key"""
    security = current_app.get_security()
    
    try:
        handler = security.get_encryption_handler(str(hospital_id))
        if not handler:
            return jsonify({'error': 'Encryption not enabled'}), 400
            
        # Perform key rotation
        result = handler.rotate_key()
        
        # Audit the change
        security.audit_log(
            str(hospital_id),
            'ENCRYPTION_KEY_ROTATION',
            {'status': 'success'}
        )
        
        return jsonify({
            'status': 'success',
            'key_id': result.get('key_id'),
            'next_rotation': result.get('next_rotation')
        })
        
    except Exception as e:
        security.audit_log(
            str(hospital_id),
            'ENCRYPTION_KEY_ROTATION',
            {'status': 'failed', 'error': str(e)}
        )
        return jsonify({'error': str(e)}), 400