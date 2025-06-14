# app/services/hospital_logo_service.py
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from PIL import Image
from werkzeug.utils import secure_filename

from app.services.database_service import get_db_session
from app.models.master import Hospital

logger = logging.getLogger(__name__)

class HospitalLogoService:
    """Service for managing hospital logos"""
    
    # Allowed image types
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'svg', 'webp'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    # Logo size configurations
    LOGO_SIZES = {
        'original': None,  # Keep original
        'large': (400, 400),  # Large display (website header)
        'medium': (200, 200),  # Medium display (dashboard)
        'small': (100, 100),  # Small display (sidebar, thumbnails)
        'icon': (50, 50)  # Favicon or small icon
    }

    @classmethod
    def validate_logo_file(cls, logo_file) -> Dict[str, Any]:
        """
        Validate logo file
        
        Args:
            logo_file: File storage object
        
        Returns:
            Dict with validation results
        """
        # Check file extension
        filename = logo_file.filename.lower()
        if not any(filename.endswith(ext) for ext in cls.ALLOWED_EXTENSIONS):
            return {
                'valid': False, 
                'message': f'Invalid file type. Allowed types: {", ".join(cls.ALLOWED_EXTENSIONS)}'
            }
        
        # Check file size
        logo_file.seek(0, os.SEEK_END)
        file_size = logo_file.tell()
        logo_file.seek(0)
        
        if file_size > cls.MAX_FILE_SIZE:
            return {
                'valid': False, 
                'message': f'File too large. Maximum size is {cls.MAX_FILE_SIZE / 1024 / 1024}MB'
            }
        
        return {'valid': True}

    @classmethod
    def generate_unique_filename(cls, original_filename: str) -> str:
        """
        Generate a unique filename
        
        Args:
            original_filename: Original filename
        
        Returns:
            Unique filename
        """
        ext = original_filename.lower().rsplit('.', 1)[-1]
        unique_id = str(uuid.uuid4())
        return f"{unique_id}.{ext}"

    @classmethod
    def resize_image(cls, image: Image.Image, size: Optional[tuple] = None) -> Image.Image:
        """
        Resize image while maintaining aspect ratio
        
        Args:
            image: PIL Image object
            size: Target size as (width, height)
        
        Returns:
            Resized PIL Image
        """
        if size is None:
            return image
        
        image.thumbnail(size, Image.Resampling.LANCZOS)
        return image

    @classmethod
    def save_logo_variants(cls, logo_file, unique_filename: str, upload_dir: str) -> Dict[str, Any]:
        """
        Save different logo variants
        
        Args:
            logo_file: File storage object
            unique_filename: Base unique filename
            upload_dir: Directory to save logos
        
        Returns:
            Dict with logo variant information
        """
        # Ensure upload directory exists
        os.makedirs(upload_dir, exist_ok=True)
        
        # Open image
        image = Image.open(logo_file)
        
        # Prepare logo variants dictionary
        logo_variants = {}
        
        for variant, size in cls.LOGO_SIZES.items():
            # Create a copy of the image to resize
            resized_image = cls.resize_image(image.copy(), size)
            
            # Generate variant filename
            variant_filename = f"{variant}_{unique_filename}"
            variant_path = os.path.join(upload_dir, variant_filename)
            
            # Save image
            resized_image.save(variant_path)
            
            # Store variant information
            logo_variants[variant] = {
                'filename': variant_filename,
                'path': variant_path,
                'size': resized_image.size
            }
        
        return logo_variants

    @classmethod
    def upload_logo(cls, hospital_id: str, logo_file) -> Dict[str, Any]:
        """
        Upload and process hospital logo
        
        Args:
            hospital_id: Hospital ID
            logo_file: File storage object
        
        Returns:
            Dict with upload results
        
        Raises:
            ValueError: If validation fails
        """
        # Validate file - do this outside the try-except block
        validation = cls.validate_logo_file(logo_file)
        if not validation['valid']:
            raise ValueError(validation['message'])
            
        try:
            # Define upload directory
            upload_dir = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'static', 
                'uploads', 
                'hospital_logos', 
                str(hospital_id)
            )
            
            # Generate unique filename
            unique_filename = cls.generate_unique_filename(logo_file.filename)
            
            # Save logo variants
            logo_variants = cls.save_logo_variants(logo_file, unique_filename, upload_dir)
            
            # Prepare logo information
            logo_info = {
                'original_filename': logo_file.filename,
                'upload_timestamp': datetime.utcnow().isoformat(),
                'mime_type': logo_file.mimetype,
                'variants': logo_variants
            }
            
            # Update hospital logo in database
            with get_db_session() as session:
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                
                if not hospital:
                    return {'success': False, 'message': 'Hospital not found'}
                
                # Remove old logo files if exists
                cls.remove_existing_logo(hospital)
                
                # Update logo
                hospital.logo = logo_info
                
                # Commit changes
                session.commit()
            
            return {
                'success': True, 
                'message': 'Logo uploaded successfully',
                'logo_info': logo_info
            }
        
        except Exception as e:
            logger.error(f"Logo upload error: {str(e)}", exc_info=True)
            return {'success': False, 'message': str(e)}

    @classmethod
    def remove_existing_logo(cls, hospital: Hospital):
        """
        Remove existing logo files for a hospital
        
        Args:
            hospital: Hospital model instance
        """
        if hospital.logo and 'variants' in hospital.logo:
            for variant in hospital.logo['variants'].values():
                try:
                    os.remove(variant['path'])
                except FileNotFoundError:
                    pass  # Ignore if file already removed
                except Exception as e:
                    logger.error(f"Error removing logo file: {str(e)}")
            
            # Clear logo information
            hospital.logo = None