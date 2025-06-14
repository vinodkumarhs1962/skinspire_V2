# flask_cli.py
# CLI Commands for Database and Migration Management
#
# Quick Reference Commands:
# 1. Create Migration:
#    python -m flask --app flask_cli.py db migrate -m "Description of changes"
#
# 2. Apply Migrations:
#    python -m flask --app flask_cli.py db upgrade
#
# 3. Rollback Last Migration:
#    python -m flask --app flask_cli.py db downgrade
#
# 4. View Current Migration:
#    python -m flask --app flask_cli.py db current
#
# 5. Reset Migration Tracking:
#    python -m flask --app flask_cli.py db stamp head
#
# 6. Database Backup:
#    pg_dump skinspire_dev > skinspire_dev_backup.sql
#    python scripts/manage_db.py create-backup --env dev
#
# 7. Database Restore:
#    psql -U skinspire_admin -d skinspire_dev -f skinspire_dev_backup.sql
#    python scripts/manage_db.py restore-backup
#
# 8. Reset Alembic Version Table:
#    psql -U skinspire_admin -d skinspire_dev -c "DELETE FROM alembic_version;"

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Explicitly set development environment
os.environ['FLASK_ENV'] = 'development'
os.environ['SKINSPIRE_ENV'] = 'development'

# Create a minimal Flask app for migrations
app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True  # Helpful for debugging SQL

# Initialize SQLAlchemy and Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db, render_item=True)

# Import all models to ensure they're recognized during migration
# Base models and mixins
from app.models.base import Base, TimestampMixin, TenantMixin, SoftDeleteMixin

# Configuration models
from app.models.config import (
    ModuleMaster, RoleMaster, RoleModuleAccess, 
    UserRoleMapping, ParameterSettings
)

# Master data models
from app.models.master import (
    Hospital, Branch, Staff, Patient, HospitalSettings
)

# Transaction models
from app.models.transaction import (
    User, LoginHistory, UserSession, 
    VerificationCode, StaffApprovalRequest
)

def print_model_info():
    """
    Diagnostic print of loaded models
    """
    models_info = {
        "Base Models": [Base, TimestampMixin, TenantMixin, SoftDeleteMixin],
        "Config Models": [ModuleMaster, RoleMaster, RoleModuleAccess, UserRoleMapping, ParameterSettings],
        "Master Models": [Hospital, Branch, Staff, Patient, HospitalSettings],
        "Transaction Models": [User, LoginHistory, UserSession, VerificationCode, StaffApprovalRequest]
    }

    print("\nLoaded Models:")
    for category, model_list in models_info.items():
        print(f"\n{category}:")
        for model in model_list:
            print(f"- {model.__name__}")

# Optional diagnostic print
if __name__ == '__main__':
    print(f"Current Environment: {os.environ.get('FLASK_ENV', 'Not Set')}")
    print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print_model_info()