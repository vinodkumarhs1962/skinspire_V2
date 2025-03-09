# skinspire_v2/app/api/routes/__init__.py

from flask import Blueprint

# Create blueprints
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')
# auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
patient_bp = Blueprint('patient', __name__, url_prefix='/api/patient')

# Import routes to register them
from . import admin, patient  # This should come after blueprint creation

# Export blueprints
__all__ = ['admin_bp', 'patient_bp']