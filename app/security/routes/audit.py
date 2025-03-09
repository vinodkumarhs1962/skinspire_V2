# app/security/routes/audit.py

from flask import Blueprint, current_app, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from functools import wraps
from . import audit_bp

def audit_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security = current_app.get_security()
        if not security.check_permission(
            request.user_id,
            request.hospital_id,
            'audit',
            'view'
        ):
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@audit_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'})

@audit_bp.route('/logs', methods=['GET'])
def get_logs():
    """Get audit logs"""
    return jsonify({
        'logs': [
            {
                'id': 1,
                'action': 'login',
                'timestamp': '2025-01-30T12:00:00Z'
            }
        ]
    })

@audit_bp.route('/hospital/<uuid:hospital_id>/logs', methods=['GET'])
@login_required
@audit_admin_required
def get_audit_logs(hospital_id):
    """Get audit logs with filtering"""
    security = current_app.get_security()
    
    # Parse query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    action = request.args.get('action')
    user_id = request.args.get('user_id')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    try:
        if security.legacy_mode:
            # Use existing audit system
            from ...models import EncryptionAudit
            query = EncryptionAudit.query.filter_by(
                hospital_id=hospital_id
            )
            
            if start_date:
                query = query.filter(
                    EncryptionAudit.performed_at >= start_date
                )
            if end_date:
                query = query.filter(
                    EncryptionAudit.performed_at <= end_date
                )
            if action:
                query = query.filter(
                    EncryptionAudit.action == action
                )
            if user_id:
                query = query.filter(
                    EncryptionAudit.performed_by == user_id
                )
            
            total = query.count()
            logs = query.order_by(
                EncryptionAudit.performed_at.desc()
            ).paginate(
                page=page,
                per_page=per_page
            )
            
            return jsonify({
                'total': total,
                'page': page,
                'per_page': per_page,
                'logs': [log.to_dict() for log in logs.items]
            })
        else:
            # Use new audit system
            from ..audit.audit_logger import AuditLogger
            audit_logger = AuditLogger()
            return jsonify(audit_logger.get_logs(
                str(hospital_id),
                filters={
                    'start_date': start_date,
                    'end_date': end_date,
                    'action': action,
                    'user_id': user_id
                },
                page=page,
                per_page=per_page
            ))
    except Exception as e:
        return jsonify({'error': str(e)}), 400