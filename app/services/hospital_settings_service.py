# app/services/hospital_settings_service.py

import logging
import json
from typing import Dict, Any, Optional

from app.services.database_service import get_db_session
from app.models.master import Hospital, HospitalSettings

logger = logging.getLogger(__name__)

class HospitalSettingsService:
    """Service for managing hospital-specific settings"""
    
    # Default settings (including logo-related configurations)
    DEFAULT_SETTINGS = {
        "verification": {
            "require_email_verification": True,
            "require_phone_verification": True,
            "verification_required_for_login": False,
            "verification_required_for_staff": True,
            "verification_required_for_patients": True,
            "verification_grace_period_days": 7,
            "otp_length": 6,
            "otp_expiry_minutes": 10,
            "max_otp_attempts": 3
        },
        "logo": {
            "max_size_mb": 5,  # Maximum logo file size in MB
            "allowed_types": ["png", "jpg", "jpeg", "svg", "webp"],
            "max_dimensions": {
                "width": 2000,
                "height": 2000
            },
            "storage_path": "/uploads/hospital_logos/"
        }
    }
    
    @classmethod
    def get_settings(cls, hospital_id: str, category: str = "verification") -> Dict[str, Any]:
        """
        Get settings for a specific hospital and category
        
        Args:
            hospital_id: Hospital ID
            category: Settings category (default: verification)
            
        Returns:
            Dict with settings
        """
        try:
            with get_db_session() as session:
                # Get settings from database
                settings_record = session.query(HospitalSettings).filter_by(
                    hospital_id=hospital_id,
                    category=category,
                    is_active=True
                ).first()
                
                if not settings_record:
                    # Return default settings if not found
                    return cls.DEFAULT_SETTINGS.get(category, {})
                
                # Return settings
                return settings_record.settings
                
        except Exception as e:
            logger.error(f"Error getting hospital settings: {str(e)}", exc_info=True)
            
            # Return default settings on error
            return cls.DEFAULT_SETTINGS.get(category, {})
    
    @classmethod
    def update_settings(cls, hospital_id: str, category: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update settings for a specific hospital and category
        
        Args:
            hospital_id: Hospital ID
            category: Settings category
            settings: New settings
            
        Returns:
            Dict with status and message
        """
        try:
            with get_db_session() as session:
                # Get existing settings record
                settings_record = session.query(HospitalSettings).filter_by(
                    hospital_id=hospital_id,
                    category=category,
                    is_active=True
                ).first()
                
                if settings_record:
                    # Update existing record
                    # Merge with existing settings to maintain backward compatibility
                    existing_settings = settings_record.settings or {}
                    existing_settings.update(settings)
                    settings_record.settings = existing_settings
                else:
                    # Create new record
                    settings_record = HospitalSettings(
                        hospital_id=hospital_id,
                        category=category,
                        settings=settings
                    )
                    session.add(settings_record)
                
                # Commit changes
                session.commit()
                
                return {"success": True, "message": "Settings updated successfully"}
                
        except Exception as e:
            logger.error(f"Error updating hospital settings: {str(e)}", exc_info=True)
            return {"success": False, "message": "Internal error"}
    
    @classmethod
    def validate_logo_settings(cls, logo_file) -> Dict[str, Any]:
        """
        Validate logo upload settings based on hospital configuration
        
        Args:
            logo_file: File to be validated
        
        Returns:
            Validation result
        """
        # Get logo settings (use default if not configured)
        logo_settings = cls.DEFAULT_SETTINGS.get('logo', {})
        
        # Validate file size
        logo_file.seek(0, 2)  # Go to end of file
        file_size = logo_file.tell()
        logo_file.seek(0)  # Reset file pointer
        
        max_size_bytes = logo_settings.get('max_size_mb', 5) * 1024 * 1024
        if file_size > max_size_bytes:
            return {
                'valid': False, 
                'message': f'File too large. Maximum size is {logo_settings.get("max_size_mb", 5)}MB'
            }
        
        # Validate file extension
        import os
        file_ext = os.path.splitext(logo_file.filename)[1].lower().replace('.', '')
        allowed_types = logo_settings.get('allowed_types', ['png', 'jpg', 'jpeg', 'svg', 'webp'])
        
        if file_ext not in allowed_types:
            return {
                'valid': False, 
                'message': f'Invalid file type. Allowed types: {", ".join(allowed_types)}'
            }
        
        # Additional validation can be added here (e.g., image dimensions)
        return {'valid': True, 'message': 'Logo validation successful'}