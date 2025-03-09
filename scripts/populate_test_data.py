# scripts/populate_test_data.py
#   working test 3.3.25

import sys
import os
from pathlib import Path
import logging
from datetime import datetime, timezone, timedelta
import random
from werkzeug.security import generate_password_hash

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.db import init_db
from app.models import Hospital, Branch, Staff, User, Patient, UserRoleMapping, RoleMaster
from app.config.settings import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_phone():
    """Generate a random 10-digit phone number"""
    return f"98{random.randint(10000000, 99999999)}"

def create_test_doctors(session, hospital_id, branch_id):
    """Create test doctor records"""
    specializations = [
        "Dermatologist", "Plastic Surgeon", "Aesthetic Physician",
        "Cosmetic Surgeon", "Skin Specialist"
    ]
    doctors = []
    
    for i in range(5):  # Create 5 doctors
        phone = generate_phone()
        staff = Staff(
            hospital_id=hospital_id,
            branch_id=branch_id,
            employee_code=f"DOC{i+1:03d}",
            title="Dr",
            specialization=random.choice(specializations),
            personal_info={
                "first_name": f"Doctor{i+1}",
                "last_name": f"Smith{i+1}",
                "dob": "1980-01-01",
                "gender": random.choice(["M", "F"])
            },
            contact_info={
                "email": f"doctor{i+1}@skinspire.com",
                "phone": phone,
                "address": {
                    "street": f"{i+1} Doctor Street",
                    "city": "Healthcare City",
                    "zip": "12345"
                }
            },
            professional_info={
                "qualification": "MD, Dermatology",
                "experience": f"{random.randint(5, 20)} years",
                "licenses": ["Medical License #12345"]
            },
            employment_info={
                "join_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "designation": "Senior Consultant",
                "employee_type": "Full Time"
            }
        )
        session.add(staff)
        session.flush()
        
        # Create user account for doctor
        user = User(
            user_id=phone,
            hospital_id=hospital_id,
            entity_type="staff",
            entity_id=staff.staff_id,
            is_active=True,
            password_hash=generate_password_hash("test123")
        )
        session.add(user)
        session.flush()
        
        # Assign doctor role
        doctor_role = session.query(RoleMaster).filter_by(
            hospital_id=hospital_id,
            role_name='Doctor'
        ).first()
        
        role_mapping = UserRoleMapping(
            user_id=user.user_id,
            role_id=doctor_role.role_id
        )
        session.add(role_mapping)
        doctors.append(staff)
        
    logger.info(f"Created {len(doctors)} test doctors")
    return doctors

def create_test_staff(session, hospital_id, branch_id):
    """Create test staff members"""
    roles = [
        {
            "role": "Nurse",
            "title": "Ms",
            "qualification": "BSc Nursing"
        },
        {
            "role": "Receptionist",
            "title": "Ms",
            "qualification": "Bachelor's in Administration"
        },
        {
            "role": "Pharmacy Staff",
            "title": "Mr",
            "qualification": "B.Pharm"
        }
    ]
    
    staff_members = []
    for role in roles:
        # Create 2 staff members for each role
        for i in range(2):
            phone = generate_phone()
            staff = Staff(
                hospital_id=hospital_id,
                branch_id=branch_id,
                employee_code=f"{role['role'][:3].upper()}{i+1:03d}",
                title=role['title'],
                specialization=role['role'],
                personal_info={
                    "first_name": f"{role['role']}{i+1}",
                    "last_name": "Staff",
                    "dob": "1990-01-01",
                    "gender": random.choice(["M", "F"])
                },
                contact_info={
                    "email": f"{role['role'].lower()}{i+1}@skinspire.com",
                    "phone": phone,
                    "address": {
                        "street": f"{i+1} Staff Street",
                        "city": "Healthcare City",
                        "zip": "12345"
                    }
                },
                professional_info={
                    "qualification": role['qualification'],
                    "experience": f"{random.randint(1, 5)} years"
                },
                employment_info={
                    "join_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "designation": role['role'],
                    "employee_type": "Full Time"
                }
            )
            session.add(staff)
            session.flush()
            
            # Create user account
            user = User(
                user_id=phone,
                hospital_id=hospital_id,
                entity_type="staff",
                entity_id=staff.staff_id,
                is_active=True,
                password_hash=generate_password_hash("test123")
            )
            session.add(user)
            session.flush()
            
            # Assign role
            staff_role = session.query(RoleMaster).filter_by(
                hospital_id=hospital_id,
                role_name=role['role']
            ).first()
            
            role_mapping = UserRoleMapping(
                user_id=user.user_id,
                role_id=staff_role.role_id
            )
            session.add(role_mapping)
            staff_members.append(staff)
    
    logger.info(f"Created {len(staff_members)} support staff members")
    return staff_members

def create_test_patients(session, hospital_id, branch_id):
    """Create test patients"""
    patients = []
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    
    for i in range(20):  # Create 20 test patients
        phone = generate_phone()
        patient = Patient(
            hospital_id=hospital_id,
            branch_id=branch_id,
            mrn=f"PAT{i+1:04d}",
            title=random.choice(["Mr", "Ms", "Mrs"]),
            blood_group=random.choice(blood_groups),
            personal_info={
                "first_name": f"Patient{i+1}",
                "last_name": f"Test{i+1}",
                "dob": (datetime.now(timezone.utc) - 
                       timedelta(days=365*random.randint(20, 70))).strftime("%Y-%m-%d"),
                "gender": random.choice(["M", "F"]),
                "marital_status": random.choice(["Single", "Married"])
            },
            contact_info={
                "email": f"patient{i+1}@example.com",
                "phone": phone,
                "address": {
                    "street": f"{i+1} Patient Street",
                    "city": "Healthcare City",
                    "zip": "12345"
                }
            },
            medical_info="Test medical information - to be encrypted",
            emergency_contact={
                "name": f"Emergency Contact {i+1}",
                "relationship": "Family",
                "phone": generate_phone()
            },
            preferences={
                "language": "English",
                "communication": ["Email", "SMS"]
            }
        )
        session.add(patient)
        session.flush()
        
        # Create user account for patient portal
        user = User(
            user_id=phone,
            hospital_id=hospital_id,
            entity_type="patient",
            entity_id=patient.patient_id,
            is_active=True,
            password_hash=generate_password_hash("test123")
        )
        session.add(user)
        session.flush()
        
        # Assign patient role
        patient_role = session.query(RoleMaster).filter_by(
            hospital_id=hospital_id,
            role_name='Patient'
        ).first()
        
        role_mapping = UserRoleMapping(
            user_id=user.user_id,
            role_id=patient_role.role_id
        )
        session.add(role_mapping)
        patients.append(patient)
    
    logger.info(f"Created {len(patients)} test patients")
    return patients

def populate_test_data():
    """Main function to populate test data"""
    try:
        # Explicitly use testing database URL
        database_url = settings.get_database_url_for_env('testing')
        if not database_url:
            logger.error("TEST_DATABASE_URL not found in environment variables")
            raise ValueError("TEST_DATABASE_URL must be set in .env file")
            
        logger.info(f"Using test database URL: {database_url}")
        db_manager = init_db(database_url)
        
        with db_manager.get_session() as session:
            # Get the main hospital
            hospital = session.query(Hospital).filter_by(
                license_no="HC123456"
            ).first()
            
            if not hospital:
                logger.error("Main hospital not found. Please run create_database.py first.")
                return
            
            # Get the main branch
            branch = session.query(Branch).filter_by(
                hospital_id=hospital.hospital_id
            ).first()
            
            if not branch:
                logger.error("Main branch not found.")
                return
            
            # Create test doctors
            doctors = create_test_doctors(session, hospital.hospital_id, branch.branch_id)
            
            # Create other staff members
            staff = create_test_staff(session, hospital.hospital_id, branch.branch_id)
            
            # Create test patients
            patients = create_test_patients(session, hospital.hospital_id, branch.branch_id)
            
            session.commit()
            
            logger.info("\nTest data population summary:")
            logger.info(f"- Doctors: {len(doctors)}")
            logger.info(f"- Support Staff: {len(staff)}")
            logger.info(f"- Patients: {len(patients)}")
            logger.info("Test data population complete!")

    except Exception as e:
        logger.error(f"Error populating test data: {str(e)}")
        raise

def main():
    """Script entry point"""
    try:
        # Set environment for testing
        os.environ['FLASK_ENV'] = 'testing'
        
        logger.info(f"Using environment: {os.environ.get('FLASK_ENV', 'testing')}")
        logger.info("Starting test data population...")
        populate_test_data()
        
    except Exception as e:
        logger.error(f"Failed to populate test data: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()