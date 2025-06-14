# app/services/employee_id_service.py
import json
import uuid
from datetime import datetime
from flask import current_app
from app.services.database_service import get_db_session, get_detached_copy
from app.models.master import Hospital, Staff
from app.models.transaction import User

class EmployeeIDService:
    """Service for handling employee ID generation and management"""
    
    @classmethod
    def get_id_settings(cls, hospital_id):
        """
        Get employee ID generation settings for a hospital
        
        Args:
            hospital_id: Hospital ID
            
        Returns:
            Dict with ID generation settings
        """
        try:
            with get_db_session() as session:
                # Find hospital
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                
                if not hospital:
                    return cls._get_default_settings()
                
                # Try to get settings from hospital settings
                settings = hospital.settings or {}
                
                # Convert from string if needed
                if isinstance(settings, str):
                    try:
                        settings = json.loads(settings)
                    except (json.JSONDecodeError, TypeError):
                        settings = {}
                
                # Get employee ID settings or default
                id_settings = settings.get('employee_id', cls._get_default_settings())
                
                return id_settings
        
        except Exception as e:
            current_app.logger.error(f"Error getting employee ID settings: {str(e)}", exc_info=True)
            return cls._get_default_settings()
    
    @classmethod
    def update_id_settings(cls, hospital_id, id_settings):
        """
        Update employee ID generation settings for a hospital
        
        Args:
            hospital_id: Hospital ID
            id_settings: Dict with new settings
            
        Returns:
            Dict with success status and message
        """
        try:
            with get_db_session() as session:
                # Find hospital
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                
                if not hospital:
                    return {'success': False, 'message': 'Hospital not found'}
                
                # Get current settings
                settings = hospital.settings or {}
                
                # Convert from string if needed
                if isinstance(settings, str):
                    try:
                        settings = json.loads(settings)
                    except (json.JSONDecodeError, TypeError):
                        settings = {}
                
                # Update employee ID settings
                settings['employee_id'] = id_settings
                
                # Save settings back to hospital
                hospital.settings = settings
                session.commit()
                
                return {'success': True, 'message': 'Settings updated successfully'}
        
        except Exception as e:
            current_app.logger.error(f"Error updating employee ID settings: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}
    
    @classmethod
    def generate_employee_id(cls, hospital_id):
        """
        Generate a new employee ID based on hospital settings
        
        Args:
            hospital_id: Hospital ID
            
        Returns:
            Generated employee ID string
        """
        try:
            # Get settings
            settings = cls.get_id_settings(hospital_id)
            
            # Get next number
            next_num = int(settings.get('next_number', 1))
            
            # Get padding
            padding = int(settings.get('padding', 3))
            
            # Format number part with padding
            num_part = str(next_num).zfill(padding)
            
            # Construct ID using prefix, formatted number, and suffix
            prefix = settings.get('prefix', '')
            suffix = settings.get('suffix', '')
            separator = settings.get('separator', '')
            
            # Build employee ID
            parts = []
            if prefix:
                parts.append(prefix)
            parts.append(num_part)
            if suffix:
                parts.append(suffix)
            
            employee_id = separator.join(parts)
            
            # Increment next number in settings
            settings['next_number'] = next_num + 1
            cls.update_id_settings(hospital_id, settings)
            
            return employee_id
        
        except Exception as e:
            current_app.logger.error(f"Error generating employee ID: {str(e)}", exc_info=True)
            # Return a fallback ID if generation fails
            return f"EMP-{uuid.uuid4().hex[:6].upper()}"
    
    @classmethod
    def update_employee_id(cls, staff_id, employee_code):
        """
        Update employee ID for a staff member
        
        Args:
            staff_id: Staff ID (UUID)
            employee_code: New employee code
            
        Returns:
            Dict with success status and message
        """
        try:
            with get_db_session() as session:
                # Find staff
                staff = session.query(Staff).filter_by(staff_id=staff_id).first()
                
                if not staff:
                    return {'success': False, 'message': 'Staff not found'}
                
                # Check if code is already in use by another staff member
                if employee_code:
                    existing = session.query(Staff).filter(
                        Staff.employee_code == employee_code,
                        Staff.staff_id != staff_id
                    ).first()
                    
                    if existing:
                        return {'success': False, 'message': 'Employee ID already in use'}
                
                # Update employee code
                staff.employee_code = employee_code
                session.commit()
                
                return {'success': True, 'message': 'Employee ID updated successfully'}
        
        except Exception as e:
            current_app.logger.error(f"Error updating employee ID: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}
    
    @classmethod
    def _get_default_settings(cls):
        """Get default employee ID generation settings"""
        return {
            'prefix': 'EMP',
            'next_number': 1,
            'padding': 3,
            'suffix': '',
            'separator': '-'
        }