# scripts/create_database.py
#   working code 3.3.25

import sys
from pathlib import Path
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash
import uuid

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db import init_db, get_db
from app.models import (
    Hospital, Branch, Staff, User, Patient,
    ModuleMaster, RoleMaster, RoleModuleAccess, UserRoleMapping,
    generate_uuid
)
from app.config.settings import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_default_modules(session):
    """Create default system modules"""
    modules = [
        {
            'name': 'Dashboard',
            'route': '/dashboard',
            'icon': 'dashboard',
            'sequence': 1,
            'submodules': []
        },
        {
            'name': 'User Management',
            'route': '/users',
            'icon': 'users',
            'sequence': 2,
            'submodules': [
                {'name': 'Staff', 'route': '/users/staff', 'sequence': 1},
                {'name': 'Patients', 'route': '/users/patients', 'sequence': 2},
                {'name': 'Roles', 'route': '/users/roles', 'sequence': 3},
            ]
        },
        {
            'name': 'Hospital Settings',
            'route': '/settings',
            'icon': 'settings',
            'sequence': 3,
            'submodules': [
                {'name': 'Branches', 'route': '/settings/branches', 'sequence': 1},
                {'name': 'Parameters', 'route': '/settings/parameters', 'sequence': 2},
            ]
        },
        {
            'name': 'Clinical',
            'route': '/clinical',
            'icon': 'medical_services',
            'sequence': 4,
            'submodules': [
                {'name': 'Appointments', 'route': '/clinical/appointments', 'sequence': 1},
                {'name': 'Consultations', 'route': '/clinical/consultations', 'sequence': 2},
                {'name': 'Prescriptions', 'route': '/clinical/prescriptions', 'sequence': 3},
            ]
        },
        {
            'name': 'Inventory',
            'route': '/inventory',
            'icon': 'inventory',
            'sequence': 5,
            'submodules': [
                {'name': 'Products', 'route': '/inventory/products', 'sequence': 1},
                {'name': 'Stock', 'route': '/inventory/stock', 'sequence': 2},
                {'name': 'Suppliers', 'route': '/inventory/suppliers', 'sequence': 3},
            ]
        }
    ]

    created_modules = {}
    for module_data in modules:
        module = ModuleMaster(
            module_name=module_data['name'],
            route=module_data['route'],
            icon=module_data['icon'],
            sequence=module_data['sequence']
        )
        session.add(module)
        session.flush()
        created_modules[module_data['name']] = module

        # Create submodules
        for sub in module_data.get('submodules', []):
            submodule = ModuleMaster(
                module_name=sub['name'],
                route=sub['route'],
                sequence=sub['sequence'],
                parent_module=module.module_id
            )
            session.add(submodule)

    session.flush()
    logger.info("Created default modules")
    return created_modules

def create_default_roles(session, hospital_id=None):
    """Create default system roles"""
    roles = [
        {
            'name': 'System Administrator',
            'description': 'Full system access',
            'is_system_role': True
        },
        {
            'name': 'Hospital Administrator',
            'description': 'Full hospital access',
            'is_system_role': True
        },
        {
            'name': 'Doctor',
            'description': 'Medical staff access',
            'is_system_role': True
        },
        {
            'name': 'Receptionist',
            'description': 'Front desk access',
            'is_system_role': True
        },
        {
            'name': 'Nurse',
            'description': 'Nursing staff access',
            'is_system_role': True
        },
        {
            'name': 'Pharmacy Staff',
            'description': 'Pharmacy access',
            'is_system_role': True
        },
        {
            'name': 'Patient',
            'description': 'Patient portal access',
            'is_system_role': True
        }
    ]

    created_roles = {}
    for role_data in roles:
        role = RoleMaster(
            hospital_id=hospital_id,
            role_name=role_data['name'],
            description=role_data['description'],
            is_system_role=role_data['is_system_role']
        )
        session.add(role)
        session.flush()
        created_roles[role_data['name']] = role

    logger.info("Created default roles")
    return created_roles

def setup_role_permissions(session, modules, roles):
    """Setup initial role permissions"""
    # System Administrator gets all permissions
    for module in session.query(ModuleMaster).all():
        access = RoleModuleAccess(
            role_id=roles['System Administrator'].role_id,
            module_id=module.module_id,
            can_view=True,
            can_add=True,
            can_edit=True,
            can_delete=True,
            can_export=True
        )
        session.add(access)

    # Hospital Administrator gets all hospital-related permissions
    hospital_modules = ['Dashboard', 'User Management', 'Hospital Settings', 'Clinical', 'Inventory']
    for module_name in hospital_modules:
        if module_name in modules:
            access = RoleModuleAccess(
                role_id=roles['Hospital Administrator'].role_id,
                module_id=modules[module_name].module_id,
                can_view=True,
                can_add=True,
                can_edit=True,
                can_delete=False,
                can_export=True
            )
            session.add(access)

    # Doctor permissions
    clinical_modules = ['Dashboard', 'Clinical']
    for module_name in clinical_modules:
        if module_name in modules:
            access = RoleModuleAccess(
                role_id=roles['Doctor'].role_id,
                module_id=modules[module_name].module_id,
                can_view=True,
                can_add=True,
                can_edit=True,
                can_delete=False,
                can_export=True
            )
            session.add(access)

    session.flush()
    logger.info("Setup role permissions")

def create_master_admin(session):
    """Create master admin user"""
    admin_user = User(
        user_id="0000000000",  # Master admin phone
        entity_type="staff",
        entity_id=str(uuid.uuid4()),  # System admin doesn't need staff record
        is_active=True,
        password_hash=generate_password_hash("master123")
    )
    session.add(admin_user)
    session.flush()

    # Assign system admin role
    sys_admin_role = session.query(RoleMaster).filter_by(
        role_name='System Administrator'
    ).first()
    
    role_mapping = UserRoleMapping(
        user_id=admin_user.user_id,
        role_id=sys_admin_role.role_id
    )
    session.add(role_mapping)
    
    logger.info(f"Created master admin user: {admin_user.user_id}")
    return admin_user

# scripts/create_database.py

def create_initial_hospital(session):
    """Create initial hospital setup"""
    try:
        # Create hospital
        hospital = Hospital(
            name="SkinSpire Main Clinic",
            license_no="HC123456",
            address={
                "street": "123 Medical Ave",
                "city": "Healthcare City",
                "zip": "12345"
            },
            contact_details={
                "phone": "1234567890",
                "email": "contact@skinspire.com"
            },
            settings={
                "timezone": "UTC",
                "currency": "USD"
            },
            encryption_enabled=True
        )
        session.add(hospital)
        session.flush()
        logger.info(f"Created hospital: {hospital.name}")

        # Create hospital roles
        roles = create_default_roles(session, hospital.hospital_id)

        # Create main branch
        branch = Branch(
            hospital_id=hospital.hospital_id,
            name="Main Branch",
            address={
                "street": "123 Medical Ave",
                "city": "Healthcare City",
                "zip": "12345"
            },
            contact_details={
                "phone": "1234567890",
                "email": "mainbranch@skinspire.com"
            }
        )
        session.add(branch)
        session.flush()
        logger.info(f"Created branch: {branch.name}")

        # Create admin staff member
        admin_staff = Staff(
            hospital_id=hospital.hospital_id,
            branch_id=branch.branch_id,
            employee_code="EMP001",
            title="Mr",
            specialization="Administration",
            personal_info={
                "first_name": "Admin",
                "last_name": "User",
                "dob": "1980-01-01",
                "gender": "M"
            },
            contact_info={
                "email": "admin@skinspire.com",
                "phone": "9876543210",
                "address": {
                    "street": "456 Staff Ave",
                    "city": "Healthcare City",
                    "zip": "12345"
                }
            },
            professional_info={
                "role": "Administrator",
                "department": "Administration",
                "qualification": "MBA"
            },
            employment_info={
                "join_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "designation": "Hospital Administrator",
                "employee_type": "Full Time"
            }
        )
        session.add(admin_staff)
        session.flush()

        # Create admin user account - FIXED VERSION
        admin_user = User(
            user_id="9876543210",  # Staff phone number
            hospital_id=hospital.hospital_id,
            entity_type="staff",
            entity_id=admin_staff.staff_id,
            is_active=True,
            password_hash=generate_password_hash("admin123")
        )
        session.add(admin_user)
        session.flush()

        # Assign hospital admin role
        role_mapping = UserRoleMapping(
            user_id=admin_user.user_id,
            role_id=roles['Hospital Administrator'].role_id
        )
        session.add(role_mapping)
        
        logger.info(f"Created hospital admin: {admin_user.user_id}")
        session.commit()
        logger.info("Initial hospital setup complete!")

        return hospital

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating initial data: {str(e)}")
        raise

def main():
    """Main database creation function"""
    try:
        logger.info(f"Using environment: {settings.FLASK_ENV}")
        logger.info(f"Database URL: {settings.DATABASE_URL}")
        
        # Initialize database connection
        db_manager = init_db(settings.DATABASE_URL)
        
        # Create all tables
        logger.info("Creating database tables...")
        db_manager.create_tables()
        logger.info("Tables created successfully!")

        # Create initial data
        with db_manager.get_session() as session:
            logger.info("Creating default modules...")
            modules = create_default_modules(session)
            
            logger.info("Creating system roles...")
            roles = create_default_roles(session)
            
            logger.info("Setting up role permissions...")
            setup_role_permissions(session, modules, roles)
            
            logger.info("Creating master admin...")
            create_master_admin(session)
            
            logger.info("Creating initial hospital...")
            create_initial_hospital(session)

    except Exception as e:
        logger.error(f"Error during database creation: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()