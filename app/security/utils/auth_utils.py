"""
Authentication utility functions for SkinSpire Clinic

This module provides helper functions for user authentication flows,
focusing on the web route implementation with direct database access.
"""

from typing import Tuple, Dict, Optional, Any, Union
from app.models.transaction import User
from app.models.master import Staff, Patient, Hospital, Branch
from sqlalchemy.orm import Session
from datetime import datetime 
import logging

logger = logging.getLogger(__name__)

def get_or_create_hospital(session: Session) -> Hospital:
    """
    Get the default hospital or create one if needed
    
    Args:
        session: SQLAlchemy database session
        
    Returns:
        Hospital: Default hospital object
    """
    hospital = session.query(Hospital).first()
    if not hospital:
        # Create a default hospital for development/testing
        hospital = Hospital(
            name="SkinSpire Clinic",
            license_no="DEFAULT001",
            address={"street": "123 Main St", "city": "Bangalore"},
            contact_details={"phone": "1234567890", "email": "info@skinspire.com"}
        )
        session.add(hospital)
        session.flush()  # Get the ID without committing
        logger.info(f"Created default hospital with ID: {hospital.hospital_id}")
    return hospital

def get_or_create_branch(session: Session, hospital_id: str) -> Branch:
    """
    Get the default branch or create one if needed
    
    Args:
        session: SQLAlchemy database session
        hospital_id: Parent hospital ID
        
    Returns:
        Branch: Default branch object
    """
    branch = session.query(Branch).filter_by(hospital_id=hospital_id).first()
    if not branch:
        # Create a default branch for development/testing
        branch = Branch(
            hospital_id=hospital_id,
            name="Main Branch",
            address={"street": "123 Main St", "city": "Bangalore"},
            contact_details={"phone": "1234567890", "email": "main@skinspire.com"}
        )
        session.add(branch)
        session.flush()  # Get the ID without committing
        logger.info(f"Created default branch with ID: {branch.branch_id}")
    return branch

def create_staff_entity(
    session: Session, 
    hospital_id: str, 
    branch_id: str, 
    first_name: str, 
    last_name: str, 
    phone: str, 
    email: str
) -> Tuple[Staff, str]:
    """
    Create a staff entity
    
    Args:
        session: SQLAlchemy database session
        hospital_id: Hospital ID
        branch_id: Branch ID
        first_name: Staff first name
        last_name: Staff last name
        phone: Staff phone number
        email: Staff email address
        
    Returns:
        Tuple[Staff, str]: Created staff object and its ID
    """
    staff = Staff(
        hospital_id=hospital_id,
        branch_id=branch_id,
        employee_code=f"EMP{phone[-4:]}",
        personal_info={
            "first_name": first_name,
            "last_name": last_name,
            "gender": "unspecified"
        },
        contact_info={
            "phone": phone,
            "email": email,
            "address": {}
        },
        professional_info={}
    )
    session.add(staff)
    session.flush()  # Get the ID without committing
    logger.debug(f"Created staff entity with ID: {staff.staff_id}")
    return staff, staff.staff_id

def create_patient_entity(
    session: Session, 
    hospital_id: str, 
    branch_id: str, 
    first_name: str, 
    last_name: str, 
    phone: str, 
    email: str
) -> Tuple[Patient, str]:
    """
    Create a patient entity
    
    Args:
        session: SQLAlchemy database session
        hospital_id: Hospital ID
        branch_id: Branch ID
        first_name: Patient first name
        last_name: Patient last name
        phone: Patient phone number
        email: Patient email address
        
    Returns:
        Tuple[Patient, str]: Created patient object and its ID
    """
    patient = Patient(
        hospital_id=hospital_id,
        branch_id=branch_id,
        mrn=f"PAT{phone[-4:]}",
        personal_info={
            "first_name": first_name,
            "last_name": last_name,
            "gender": "unspecified"
        },
        contact_info={
            "phone": phone,
            "email": email,
            "address": {}
        }
    )
    session.add(patient)
    session.flush()  # Get the ID without committing
    logger.debug(f"Created patient entity with ID: {patient.patient_id}")
    return patient, patient.patient_id

def create_user_account(
    session: Session, 
    phone: str, 
    hospital_id: str, 
    entity_type: str, 
    entity_id: str, 
    password: str
) -> User:
    """
    Create a user account
    
    Args:
        session: SQLAlchemy database session
        phone: User's phone number (used as user_id)
        hospital_id: Hospital ID
        entity_type: Type of entity ('staff' or 'patient')
        entity_id: ID of the associated entity
        password: User's password (will be hashed)
        
    Returns:
        User: Created user object
    """
    new_user = User(
        user_id=phone,
        hospital_id=hospital_id,
        entity_type=entity_type,
        entity_id=entity_id,
        is_active=True,
        failed_login_attempts=0
    )
    
    # Set password using the model's password hashing method
    new_user.set_password(password)
    
    # Add to database
    session.add(new_user)
    logger.info(f"Created user account for {phone}")
    return new_user

def authenticate_user(
    session: Session, 
    username: str, 
    password: str
) -> Tuple[bool, Optional[User], Optional[str]]:
    """
    Authenticate a user with username and password
    
    Args:
        session: SQLAlchemy database session
        username: User's username (typically phone number)
        password: User's password
        
    Returns:
        Tuple[bool, Optional[User], Optional[str]]: 
            - Success flag
            - User object if successful, None otherwise
            - Error message if failed, None otherwise
    """
    user = session.query(User).filter_by(user_id=username).first()
    
    if not user:
        logger.warning(f"Authentication failed: User {username} not found")
        return False, None, "User not found"
        
    if not user.check_password(password):
        # Track failed login attempt
        user.failed_login_attempts += 1
        session.flush()
        logger.warning(f"Authentication failed: Invalid password for user {username}")
        return False, None, "Invalid password"
        
    # Successful authentication
    user.last_login = datetime.now()
    user.failed_login_attempts = 0
    session.flush()
    logger.info(f"User {username} authenticated successfully")
    return True, user, None