# skinspire_v2/app/security/routes/__init__.py

from flask import Blueprint
# from . import security_management, rbac, audit, auth
# Create blueprints
# Create blueprints without type hints
security_bp = Blueprint('security', __name__, url_prefix='/api/security')
rbac_bp = Blueprint('rbac', __name__, url_prefix='/api/rbac')
audit_bp = Blueprint('audit', __name__, url_prefix='/api/audit')
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Import routes to register them
# Import routes to register them


# Export blueprints
__all__ = ['security_bp', 'rbac_bp', 'audit_bp', 'auth_bp']

# Third: Import the routes that use these blueprints
from . import security_management, rbac, audit, auth