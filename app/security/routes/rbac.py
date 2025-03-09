# app/security/routes/rbac.py

from flask import Blueprint, current_app, request, jsonify
from flask_login import login_required
from functools import wraps
#from ...core.security import SecurityManager
from . import rbac_bp

bp = Blueprint('rbac', __name__, url_prefix='/api/rbac')

@rbac_bp.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({'status': 'healthy'})

@rbac_bp.route('/roles', methods=['GET'])
def get_roles():
    """Get all roles"""
    return jsonify({
        'roles': [
            {'id': 1, 'name': 'admin'},
            {'id': 2, 'name': 'user'}
        ]
    })

def rbac_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security = current_app.get_security()
        if not security.check_permission(
            request.user_id,
            request.hospital_id,
            'rbac',
            'manage'
        ):
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/hospital/<uuid:hospital_id>/roles', methods=['GET'])
@login_required
@rbac_admin_required
def get_roles(hospital_id):
    """Get all roles for a hospital"""
    security = current_app.get_security()
    
    try:
        if security.legacy_mode:
            # Use existing role system
            from ...models.user import RoleMaster
            roles = RoleMaster.query.filter_by(
                hospital_id=hospital_id
            ).all()
            return jsonify([{
                'id': role.role_id,
                'name': role.role_name,
                'description': role.description
            } for role in roles])
        else:
            # Use new RBAC system
            from ..authorization.rbac_manager import RBACManager
            rbac = RBACManager()
            return jsonify(rbac.get_roles(str(hospital_id)))
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/hospital/<uuid:hospital_id>/roles', methods=['POST'])
@login_required
@rbac_admin_required
def create_role(hospital_id):
    """Create a new role"""
    data = request.get_json()
    security = current_app.get_security()
    
    try:
        if security.legacy_mode:
            # Use existing role system
            from ...models.user import RoleMaster
            role = RoleMaster(
                hospital_id=hospital_id,
                role_name=data['name'],
                description=data.get('description', '')
            )
            db.session.add(role)
            db.session.commit()
            
            result = {
                'id': role.role_id,
                'name': role.role_name,
                'description': role.description
            }
        else:
            # Use new RBAC system
            from ..authorization.rbac_manager import RBACManager
            rbac = RBACManager()
            result = rbac.create_role(str(hospital_id), data)
        
        # Audit the change
        security.audit_log(
            str(hospital_id),
            'ROLE_CREATED',
            {'role': data['name']}
        )
        
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/hospital/<uuid:hospital_id>/roles/<int:role_id>/permissions', 
          methods=['GET'])
@login_required
@rbac_admin_required
def get_role_permissions(hospital_id, role_id):
    """Get permissions for a role"""
    security = current_app.get_security()
    
    try:
        if security.legacy_mode:
            # Use existing permission system
            from ...models.user import RoleModuleAccess
            permissions = RoleModuleAccess.query.filter_by(
                role_id=role_id
            ).all()
            return jsonify([{
                'module_id': perm.module_id,
                'can_view': perm.can_view,
                'can_add': perm.can_add,
                'can_edit': perm.can_edit,
                'can_delete': perm.can_delete
            } for perm in permissions])
        else:
            # Use new RBAC system
            from ..authorization.rbac_manager import RBACManager
            rbac = RBACManager()
            return jsonify(rbac.get_role_permissions(
                str(hospital_id), 
                role_id
            ))
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp.route('/hospital/<uuid:hospital_id>/roles/<int:role_id>/permissions', 
          methods=['PUT'])
@login_required
@rbac_admin_required
def update_role_permissions(hospital_id, role_id):
    """Update role permissions"""
    data = request.get_json()
    security = current_app.get_security()
    
    try:
        if security.legacy_mode:
            # Use existing permission system
            from ...models.user import RoleModuleAccess
            for module_id, permissions in data['permissions'].items():
                access = RoleModuleAccess.query.filter_by(
                    role_id=role_id,
                    module_id=module_id
                ).first()
                
                if not access:
                    access = RoleModuleAccess(
                        role_id=role_id,
                        module_id=module_id
                    )
                    db.session.add(access)
                
                for key, value in permissions.items():
                    setattr(access, key, value)
            
            db.session.commit()
            result = {'status': 'success'}
        else:
            # Use new RBAC system
            from ..authorization.rbac_manager import RBACManager
            rbac = RBACManager()
            result = rbac.update_role_permissions(
                str(hospital_id),
                role_id,
                data['permissions']
            )
        
        # Audit the change
        security.audit_log(
            str(hospital_id),
            'ROLE_PERMISSIONS_UPDATED',
            {
                'role_id': role_id,
                'changes': data['permissions']
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400