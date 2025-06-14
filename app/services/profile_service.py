
# app/services/profile_service.py
"""
Centralized Profile Management Service

Handles profile updates and retrieval across different entity types 
(staff and patients) while maintaining system integrity and 
following the multi-tenant architecture.
"""

import json
from datetime import date, datetime
from flask import current_app
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.database_service import get_db_session, get_detached_copy
from app.models.master import Staff, Patient
from app.models.transaction import User

class ProfileService:
    @classmethod
    def _serialize_json_safe(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively convert non-JSON serializable types to strings
        
        Args:
            data: Dictionary potentially containing non-serializable types
        
        Returns:
            Dictionary with all values JSON serializable
        """
        def convert_value(value):
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            elif isinstance(value, dict):
                return cls._serialize_json_safe(value)
            elif isinstance(value, list):
                return [convert_value(item) for item in value]
            return value
        
        return {k: convert_value(v) for k, v in data.items()}

    @classmethod
    def update_profile(
        cls, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user profile across different entity types
        
        Args:
            user_id: User's phone number/user_id
            update_data: Dictionary of fields to update
        
        Returns:
            Dictionary with update status and details
        """
        try:
            with get_db_session() as session:
                # Find the user to determine entity type
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    raise ValueError(f"User not found: {user_id}")
                
                # Store entity_type before session closes
                entity_type = user.entity_type
                
                # Determine the right entity table based on entity_type
                if entity_type == 'staff':
                    profile_updated = cls._update_staff_profile(session, user, update_data)
                elif entity_type == 'patient':
                    profile_updated = cls._update_patient_profile(session, user, update_data)
                else:
                    raise ValueError(f"Unknown entity type: {entity_type}")
                
                # Commit changes
                session.commit()
            
            # Session is now closed, use stored entity_type  
            return {
                "success": True,
                "message": "Profile updated successfully",
                "entity_type": entity_type
            }
        
        except Exception as e:
            current_app.logger.error(f"Profile update error: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def _update_staff_profile(
        cls, 
        session: Session, 
        user: User, 
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update staff profile in the staff table
        
        Args:
            session: Database session
            user: User object
            update_data: Fields to update
        
        Returns:
            Boolean indicating successful update
        """
        staff = session.query(Staff).filter_by(staff_id=user.entity_id).first()
        
        if not staff:
            raise ValueError(f"Staff entity not found for user: {user.user_id}")

        # Check if employee_code is empty and would cause a unique constraint violation
        if 'employee_code' in update_data and update_data['employee_code'] == '':
            current_app.logger.info(f"Removing empty employee_code from update to avoid unique constraint violation")
            del update_data['employee_code']  # Remove it from the update data entirely

        # Convert JSON strings to dictionaries if needed
        personal_info = staff.personal_info
        if isinstance(personal_info, str):
            personal_info = json.loads(personal_info)
        personal_info = personal_info or {}
            
        contact_info = staff.contact_info
        if isinstance(contact_info, str):
            contact_info = json.loads(contact_info)
        contact_info = contact_info or {}
            
        professional_info = staff.professional_info
        if isinstance(professional_info, str):
            professional_info = json.loads(professional_info)
        professional_info = professional_info or {}
            
        employment_info = staff.employment_info
        if isinstance(employment_info, str):
            employment_info = json.loads(employment_info)
        employment_info = employment_info or {}
        
        # Update personal information
        if 'title' in update_data:
            personal_info['title'] = update_data['title']
        
        if 'first_name' in update_data:
            personal_info['first_name'] = update_data['first_name']
            # Also update dedicated field
            staff.first_name = update_data['first_name']
        if 'last_name' in update_data:
            personal_info['last_name'] = update_data['last_name']
            # Also update dedicated field
            staff.last_name = update_data['last_name']
        
        # Update full_name if either first_name or last_name changed
        if 'first_name' in update_data or 'last_name' in update_data:
            # Get current values for any field not in update_data
            first_name = update_data.get('first_name', personal_info.get('first_name', ''))
            last_name = update_data.get('last_name', personal_info.get('last_name', ''))
            
            # Update full_name with SQL
            session.execute(
                text("UPDATE staff SET full_name = :full_name WHERE staff_id = :staff_id"),
                {"full_name": f"{first_name} {last_name}".strip(), "staff_id": staff.staff_id}
            )
        
        
        if 'date_of_birth' in update_data:
            personal_info['date_of_birth'] = update_data['date_of_birth']
        if 'gender' in update_data:
            personal_info['gender'] = update_data['gender']
        


        # Update contact information
        if 'email' in update_data:
            contact_info['email'] = update_data['email']
        if 'phone' in update_data:
            # Log that we're ignoring the phone update
            current_app.logger.info(f"Ignoring phone update attempt for user {user.user_id}")
            # Keep the existing phone in contact_info, don't update it
            update_data.pop('phone')
        if 'address' in update_data:
            contact_info['address'] = update_data['address']
        
        # Update professional information
        if 'specialization' in update_data:
            staff.specialization = update_data['specialization']
            professional_info['specialization'] = update_data['specialization']
        if 'employee_code' in update_data:
            # Only update employee_code if it's not empty
            if update_data['employee_code']:
                staff.employee_code = update_data['employee_code']
            # If it's empty, we shouldn't try to update it (to avoid unique constraint violation)
            # Instead, we should keep the existing value or set it to NULL if allowed
            elif staff.employee_code == '':
                # If it's already empty and we're trying to save empty, we need to handle this
                # The best approach is to not include it in the update at all
                pass  # Skip updating employee_code if it's empty
        if 'qualifications' in update_data:
            professional_info['qualifications'] = update_data['qualifications']
        if 'certifications' in update_data:
            professional_info['certifications'] = update_data['certifications']
            
        # Update employment information
        if 'join_date' in update_data:
            employment_info['join_date'] = update_data['join_date']
        if 'designation' in update_data:
            employment_info['designation'] = update_data['designation']
        if 'department' in update_data:
            employment_info['department'] = update_data['department']
        
        # Apply updates with safe JSON serialization
        staff.personal_info = json.dumps(cls._serialize_json_safe(personal_info))
        staff.contact_info = json.dumps(cls._serialize_json_safe(contact_info))
        staff.professional_info = json.dumps(cls._serialize_json_safe(professional_info))
        staff.employment_info = json.dumps(cls._serialize_json_safe(employment_info))
        
        return True

    @classmethod
    def _update_patient_profile(
        cls, 
        session: Session, 
        user: User, 
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Update patient profile in the patient table
        
        Args:
            session: Database session
            user: User object
            update_data: Fields to update
        
        Returns:
            Boolean indicating successful update
        """
        patient = session.query(Patient).filter_by(patient_id=user.entity_id).first()
        
        if not patient:
            raise ValueError(f"Patient entity not found for user: {user.user_id}")
        
        # Convert JSON strings to dictionaries if needed
        personal_info = patient.personal_info
        if isinstance(personal_info, str):
            personal_info = json.loads(personal_info)
        personal_info = personal_info or {}
            
        contact_info = patient.contact_info
        if isinstance(contact_info, str):
            contact_info = json.loads(contact_info)
        contact_info = contact_info or {}
            
        medical_info = {}
        if patient.medical_info and isinstance(patient.medical_info, str):
            try:
                medical_info = json.loads(patient.medical_info)
            except:
                medical_info = {}
        
        emergency_contact = patient.emergency_contact
        if isinstance(emergency_contact, str):
            emergency_contact = json.loads(emergency_contact)
        emergency_contact = emergency_contact or {}
            
        preferences = patient.preferences
        if isinstance(preferences, str):
            preferences = json.loads(preferences)
        preferences = preferences or {}
        
        # Update personal information
        if 'title' in update_data:
            personal_info['title'] = update_data['title']
        if 'first_name' in update_data:
            personal_info['first_name'] = update_data['first_name']
            patient.first_name = update_data['first_name']
        if 'last_name' in update_data:
            personal_info['last_name'] = update_data['last_name']
            patient.last_name = update_data['last_name']
        if 'first_name' in update_data or 'last_name' in update_data:
            # Get current values for any field not in update_data
            first_name = update_data.get('first_name', personal_info.get('first_name', ''))
            last_name = update_data.get('last_name', personal_info.get('last_name', ''))
            # Update full_name with SQL
            session.execute(
                text("UPDATE patients SET full_name = :full_name WHERE patient_id = :patient_id"),
                {"full_name": f"{first_name} {last_name}".strip(), "patient_id": patient.patient_id}
            )  
        if 'date_of_birth' in update_data:
            personal_info['date_of_birth'] = update_data['date_of_birth']
        if 'gender' in update_data:
            personal_info['gender'] = update_data['gender']
        if 'marital_status' in update_data:
            personal_info['marital_status'] = update_data['marital_status']
        
        # Update contact information
        if 'email' in update_data:
            contact_info['email'] = update_data['email']
        if 'phone' in update_data:
            # Log that we're ignoring the phone update
            current_app.logger.info(f"Ignoring phone update attempt for user {user.user_id}")
            # Keep the existing phone in contact_info, don't update it
            update_data.pop('phone')
        if 'address' in update_data:
            contact_info['address'] = update_data['address']
        
        # Update medical information
        if 'blood_group' in update_data:
            patient.blood_group = update_data['blood_group']
        if 'allergies' in update_data:
            medical_info['allergies'] = update_data['allergies']
        
        # Update emergency contact
        if 'emergency_contact_name' in update_data:
            emergency_contact['name'] = update_data['emergency_contact_name']
        if 'emergency_contact_relation' in update_data:
            emergency_contact['relation'] = update_data['emergency_contact_relation']
        if 'emergency_contact_phone' in update_data:
            emergency_contact['phone'] = update_data['emergency_contact_phone']
            
        # Update preferences
        if 'preferred_language' in update_data:
            preferences['language'] = update_data['preferred_language']
        if 'communication_preference' in update_data:
            preferences['communication'] = update_data['communication_preference']
        
        # Apply updates with safe JSON serialization
        patient.personal_info = json.dumps(cls._serialize_json_safe(personal_info))
        patient.contact_info = json.dumps(cls._serialize_json_safe(contact_info))
        if medical_info:
            patient.medical_info = json.dumps(cls._serialize_json_safe(medical_info))
        patient.emergency_contact = json.dumps(cls._serialize_json_safe(emergency_contact))
        patient.preferences = json.dumps(cls._serialize_json_safe(preferences))
        
        return True

    @classmethod
    def _get_staff_profile(
        cls, 
        session: Session, 
        user: User
    ) -> Dict[str, Any]:
        """
        Retrieve staff profile details
        """
        staff = session.query(Staff).filter_by(staff_id=user.entity_id).first()
        
        if not staff:
            raise ValueError(f"Staff entity not found for user: {user.user_id}")
        
        # Convert JSON fields to dictionaries
        personal_info = staff.personal_info
        if isinstance(personal_info, str):
            try:
                personal_info = json.loads(personal_info)
            except:
                personal_info = {}
        personal_info = personal_info or {}
        
        contact_info = staff.contact_info
        if isinstance(contact_info, str):
            try:
                contact_info = json.loads(contact_info)
            except:
                contact_info = {}
        contact_info = contact_info or {}
        
        professional_info = staff.professional_info
        if isinstance(professional_info, str):
            try:
                professional_info = json.loads(professional_info)
            except:
                professional_info = {}
        professional_info = professional_info or {}
        
        employment_info = staff.employment_info
        if isinstance(employment_info, str):
            try:
                employment_info = json.loads(employment_info)
            except:
                employment_info = {}
        employment_info = employment_info or {}
        
        return {
            "entity_type": "staff",
            "title": personal_info.get('title', ''),
            "first_name": personal_info.get('first_name', ''),
            "last_name": personal_info.get('last_name', ''),
            "date_of_birth": personal_info.get('date_of_birth', ''),
            "gender": personal_info.get('gender', ''),
            "email": contact_info.get('email', ''),
            "phone": contact_info.get('phone', ''),
            "address": contact_info.get('address', ''),
            "specialization": professional_info.get('specialization', '') or staff.specialization,
            "employee_code": staff.employee_code or '',
            "qualifications": professional_info.get('qualifications', ''),
            "certifications": professional_info.get('certifications', ''),
            "join_date": employment_info.get('join_date', ''),
            "designation": employment_info.get('designation', ''),
            "department": employment_info.get('department', ''),
            "user_id": user.user_id
        }

    @classmethod
    def _get_patient_profile(
        cls, 
        session: Session, 
        user: User
    ) -> Dict[str, Any]:
        """
        Retrieve patient profile details
        """
        patient = session.query(Patient).filter_by(patient_id=user.entity_id).first()
        
        if not patient:
            raise ValueError(f"Patient entity not found for user: {user.user_id}")
        
        # Convert JSON fields to dictionaries
        personal_info = patient.personal_info
        if isinstance(personal_info, str):
            try:
                personal_info = json.loads(personal_info)
            except:
                personal_info = {}
        personal_info = personal_info or {}
        
        contact_info = patient.contact_info
        if isinstance(contact_info, str):
            try:
                contact_info = json.loads(contact_info)
            except:
                contact_info = {}
        contact_info = contact_info or {}
        
        # Parse medical_info if it's stored as JSON
        medical_info = {}
        if patient.medical_info:
            try:
                if isinstance(patient.medical_info, str):
                    medical_info = json.loads(patient.medical_info)
                else:
                    medical_info = patient.medical_info
            except:
                medical_info = {}
        
        emergency_contact = patient.emergency_contact
        if isinstance(emergency_contact, str):
            try:
                emergency_contact = json.loads(emergency_contact)
            except:
                emergency_contact = {}
        emergency_contact = emergency_contact or {}
        
        preferences = patient.preferences
        if isinstance(preferences, str):
            try:
                preferences = json.loads(preferences)
            except:
                preferences = {}
        preferences = preferences or {}
        
        return {
            "entity_type": "patient",
            "title": personal_info.get('title', ''),
            "first_name": personal_info.get('first_name', ''),
            "last_name": personal_info.get('last_name', ''),
            "date_of_birth": personal_info.get('date_of_birth', ''),
            "gender": personal_info.get('gender', ''),
            "marital_status": personal_info.get('marital_status', ''),
            "email": contact_info.get('email', ''),
            "phone": contact_info.get('phone', ''),
            "address": contact_info.get('address', ''),
            "blood_group": patient.blood_group or '',
            "allergies": medical_info.get('allergies', ''),
            "emergency_contact_name": emergency_contact.get('name', ''),
            "emergency_contact_relation": emergency_contact.get('relation', ''),
            "emergency_contact_phone": emergency_contact.get('phone', ''),
            "preferred_language": preferences.get('language', ''),
            "communication_preference": preferences.get('communication', ''),
            "user_id": user.user_id
        }

    @classmethod
    def get_profile(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user profile details
        
        Args:
            user_id: User's phone number/user_id
        
        Returns:
            Dictionary with profile information or None
        """
        try:
            with get_db_session(read_only=True) as session:
                # Find the user to determine entity type
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    raise ValueError(f"User not found: {user_id}")
                
                # Retrieve profile based on entity type
                if user.entity_type == 'staff':
                    return cls._get_staff_profile(session, user)
                elif user.entity_type == 'patient':
                    return cls._get_patient_profile(session, user)
                else:
                    raise ValueError(f"Unknown entity type: {user.entity_type}")
        
        except Exception as e:
            current_app.logger.error(f"Profile retrieval error: {str(e)}", exc_info=True)
            return None