# scripts/verify_test_data.py
#   working test 3.3.25

import sys
import os
from pathlib import Path
import logging
from datetime import datetime
from tabulate import tabulate
from sqlalchemy import func

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import init_db
from app.models import (
    Hospital, Branch, Staff, User, Patient,
    ModuleMaster, RoleMaster, RoleModuleAccess, UserRoleMapping
)
from app.config.settings import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_system_setup(session):
    """Verify basic system setup"""
    logger.info("\nVerifying System Setup:")
    
    # Check modules
    module_count = session.query(ModuleMaster).count()
    modules_by_parent = session.query(
        ModuleMaster.parent_module,
        func.count(ModuleMaster.module_id)
    ).group_by(ModuleMaster.parent_module).all()
    
    logger.info(f"Total Modules: {module_count}")
    logger.info("Module Structure:")
    for parent, count in modules_by_parent:
        prefix = "Root" if parent is None else f"Sub-modules of {parent}"
        logger.info(f"- {prefix}: {count}")
    
    # Check roles
    roles = session.query(RoleMaster).all()
    role_data = [[r.role_name, r.description, r.is_system_role] for r in roles]
    print("\nSystem Roles:")
    print(tabulate(
        role_data,
        headers=['Role Name', 'Description', 'System Role'],
        tablefmt='grid'
    ))

def verify_hospital_data(session):
    """Verify hospital and branch setup"""
    hospital = session.query(Hospital).first()
    logger.info("\nHospital Information:")
    logger.info(f"Name: {hospital.name}")
    logger.info(f"License: {hospital.license_no}")
    logger.info(f"Encryption Enabled: {hospital.encryption_enabled}")
    
    branches = session.query(Branch).filter_by(hospital_id=hospital.hospital_id).all()
    branch_data = []
    for branch in branches:
        branch_data.append([
            branch.name,
            branch.address.get('city'),
            branch.contact_details.get('phone'),
            'Active' if branch.is_active else 'Inactive'
        ])
    
    print("\nBranch Information:")
    print(tabulate(
        branch_data,
        headers=['Name', 'City', 'Phone', 'Status'],
        tablefmt='grid'
    ))

def verify_staff_data(session):
    """Verify staff data"""
    staff = session.query(Staff).all()
    
    # Group staff by specialization
    spec_groups = {}
    for s in staff:
        spec = s.specialization or 'Unknown'
        if spec not in spec_groups:
            spec_groups[spec] = []
        spec_groups[spec].append(s)
    
    logger.info("\nStaff Distribution:")
    for spec, members in spec_groups.items():
        logger.info(f"\n{spec}: {len(members)} members")
        staff_data = []
        for s in members:
            staff_data.append([
                s.employee_code,
                f"{s.personal_info.get('first_name', '')} {s.personal_info.get('last_name', '')}",
                s.contact_info.get('phone', ''),
                s.professional_info.get('qualification', ''),
                s.employment_info.get('designation', '')
            ])
        print(tabulate(
            staff_data,
            headers=['Code', 'Name', 'Phone', 'Qualification', 'Designation'],
            tablefmt='grid'
        ))

def verify_patient_data(session):
    """Verify patient data"""
    patients = session.query(Patient).all()
    
    # Age distribution
    age_groups = {'0-20': 0, '21-40': 0, '41-60': 0, '60+': 0}
    gender_dist = {'M': 0, 'F': 0}
    
    patient_data = []
    for p in patients:
        # Calculate age
        dob = datetime.strptime(p.personal_info.get('dob', ''), '%Y-%m-%d')
        age = (datetime.now() - dob).days // 365
        
        # Update distributions
        if age <= 20: age_groups['0-20'] += 1
        elif age <= 40: age_groups['21-40'] += 1
        elif age <= 60: age_groups['41-60'] += 1
        else: age_groups['60+'] += 1
        
        gender_dist[p.personal_info.get('gender', 'M')] += 1
        
        patient_data.append([
            p.mrn,
            f"{p.personal_info.get('first_name', '')} {p.personal_info.get('last_name', '')}",
            p.blood_group,
            p.contact_info.get('phone', ''),
            'Active' if p.is_active else 'Inactive'
        ])
    
    logger.info("\nPatient Demographics:")
    logger.info("Age Distribution:")
    for group, count in age_groups.items():
        logger.info(f"- {group}: {count} patients")
    
    logger.info("\nGender Distribution:")
    for gender, count in gender_dist.items():
        logger.info(f"- {gender}: {count} patients")
    
    print("\nPatient List:")
    print(tabulate(
        patient_data,
        headers=['MRN', 'Name', 'Blood Group', 'Phone', 'Status'],
        tablefmt='grid'
    ))

def verify_user_accounts(session):
    """Verify user accounts and role assignments"""
    users = session.query(User).all()
    
    # Group users by entity type
    entity_groups = {'staff': [], 'patient': []}
    for user in users:
        entity_groups[user.entity_type].append(user)
    
    logger.info("\nUser Account Summary:")
    logger.info(f"Total Users: {len(users)}")
    for entity_type, users in entity_groups.items():
        logger.info(f"{entity_type.title()}: {len(users)} users")
    
    # Check role assignments
    role_assignments = session.query(
        RoleMaster.role_name,
        func.count(UserRoleMapping.user_id)
    ).join(UserRoleMapping).group_by(RoleMaster.role_name).all()
    
    logger.info("\nRole Assignments:")
    for role_name, count in role_assignments:
        logger.info(f"- {role_name}: {count} users")

def verify_timestamp_columns(session):
    """Verify timestamp columns exist in all tables"""
    logger.info("\nVerifying Timestamp Columns:")
    
    from sqlalchemy import text
    
    # Get all tables in the public schema
    result = session.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
    """))
    
    tables = [row[0] for row in result]
    
    timestamp_data = []
    for table_name in tables:
        # Check if timestamp columns exist
        result = session.execute(text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
              AND column_name IN ('created_at', 'updated_at', 'created_by', 'updated_by')
        """))
        
        columns = [row[0] for row in result]
        timestamp_data.append([
            table_name,
            'Yes' if 'created_at' in columns else 'No',
            'Yes' if 'updated_at' in columns else 'No',
            'Yes' if 'created_by' in columns else 'No',
            'Yes' if 'updated_by' in columns else 'No'
        ])
    
    print("\nTimestamp Column Verification:")
    print(tabulate(
        timestamp_data,
        headers=['Table Name', 'created_at', 'updated_at', 'created_by', 'updated_by'],
        tablefmt='grid'
    ))

def verify_all_data():
    """Main verification function"""
    try:
        # Set environment for testing
        os.environ['FLASK_ENV'] = 'testing'
        
        # Explicitly use test database URL
        database_url = settings.get_database_url_for_env('testing')
        if not database_url:
            logger.error("TEST_DATABASE_URL not found in environment variables")
            raise ValueError("TEST_DATABASE_URL must be set in .env file")
        
        logger.info(f"Using environment: {os.environ.get('FLASK_ENV', 'testing')}")
        logger.info(f"Using database URL: {database_url}")
        logger.info("Starting data verification...")
        
        db_manager = init_db(database_url)
        
        with db_manager.get_session() as session:
            # Verify timestamp columns first
            verify_timestamp_columns(session)
            
            # Verify other data
            verify_system_setup(session)
            verify_hospital_data(session)
            verify_staff_data(session)
            verify_patient_data(session)
            verify_user_accounts(session)
            
            logger.info("\nData verification complete!")
            
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        raise

def main():
    """Script entry point"""
    try:
        verify_all_data()
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()