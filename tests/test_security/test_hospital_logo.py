# tests/test_security/test_hospital_logo.py
# pytest tests/test_security/test_hospital_logo.py

import os
import io
import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.services.hospital_logo_service import HospitalLogoService
from app.services.database_service import get_db_session
from app.models.master import Hospital

class TestHospitalLogoUpload:

    def create_test_image(self, format='PNG', size=(400, 400)):
        """
        Create a test image in memory
        
        Args:
            format (str): Image format (PNG, JPEG, etc.)
            size (tuple): Image dimensions
        
        Returns:
            FileStorage object with image
        """
        # Create an in-memory image
        image = Image.new('RGB', size, color='red')
        
        # Create an in-memory file
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=format)
        img_byte_arr.seek(0)
        
        # Create FileStorage object
        return FileStorage(
            stream=img_byte_arr, 
            filename=f'test_logo.{format.lower()}', 
            content_type=f'image/{format.lower()}'
        )

    def test_logo_upload_success(self, sample_hospital):
        """
        Test successful logo upload
        """
        # Create test image
        logo_file = self.create_test_image()
        
        # Upload logo
        result = HospitalLogoService.upload_logo(sample_hospital.hospital_id, logo_file)
        
        # Assertions
        assert result['success'] is True
        assert 'logo_info' in result
        
        # Verify logo was saved - using a fresh session
        with get_db_session() as session:
            # Use the ID to get a fresh instance
            updated_hospital = session.get(Hospital, sample_hospital.hospital_id)
            assert updated_hospital.logo is not None
            assert 'variants' in updated_hospital.logo

    def test_logo_upload_file_size_limit(self, sample_hospital):
        """
        Test logo upload exceeding file size limit
        """
        # Override validate_logo_file to force the file size error
        original_validate = HospitalLogoService.validate_logo_file
        
        try:
            def mock_validate(cls, logo_file):
                return {'valid': False, 'message': 'File too large. Maximum size is 5.0MB'}
            
            # Apply the mock
            HospitalLogoService.validate_logo_file = classmethod(mock_validate)
            
            # Create test image
            logo_file = self.create_test_image()
            
            # Attempt upload
            with pytest.raises(ValueError) as excinfo:
                HospitalLogoService.upload_logo(sample_hospital.hospital_id, logo_file)
            
            assert "File too large" in str(excinfo.value)
            
        finally:
            # Restore original method
            HospitalLogoService.validate_logo_file = original_validate
    def test_logo_upload_invalid_file_type(self, sample_hospital):
        """
        Test logo upload with unsupported file type
        """
        # Create a text file
        text_file = FileStorage(
            stream=io.BytesIO(b'invalid file content'), 
            filename='invalid_logo.txt', 
            content_type='text/plain'
        )
        
        # Attempt upload
        with pytest.raises(ValueError) as excinfo:
            HospitalLogoService.upload_logo(sample_hospital.hospital_id, text_file)
        
        assert "Invalid file type" in str(excinfo.value)

    def test_logo_multiple_format_uploads(self, sample_hospital):
        """
        Test logo upload with multiple supported formats
        """
        # Test formats - remove SVG as PIL can't save to SVG
        formats = ['PNG', 'JPEG', 'WEBP']  # PIL can't save as SVG

        for fmt in formats:
            # Create test image
            logo_file = self.create_test_image(format=fmt)
            
            # Upload logo
            result = HospitalLogoService.upload_logo(sample_hospital.hospital_id, logo_file)
            
            # Assertions
            assert result['success'] is True
            assert 'logo_info' in result
            
            # Verify logo was saved
            with get_db_session() as session:
                updated_hospital = session.query(Hospital).get(sample_hospital.hospital_id)
                assert updated_hospital.logo is not None
                assert 'variants' in updated_hospital.logo

    def test_logo_removal(self, sample_hospital):
        """
        Test logo removal functionality
        """ 
        # First, upload a logo
        logo_file = self.create_test_image()
        upload_result = HospitalLogoService.upload_logo(sample_hospital.hospital_id, logo_file)
        
        # Verify logo was uploaded
        with get_db_session() as session:
            hospital = session.query(Hospital).get(sample_hospital.hospital_id)
            assert hospital.logo is not None
        
        # Now remove the logo
        with get_db_session() as session:
            hospital = session.query(Hospital).get(sample_hospital.hospital_id)
            HospitalLogoService.remove_existing_logo(hospital)
            session.commit()
        
        # Verify logo was removed
        with get_db_session() as session:
            hospital = session.query(Hospital).get(sample_hospital.hospital_id)
            assert hospital.logo is None

    def test_logo_variants_generation(self, sample_hospital):
        """
        Test generation of different logo variants
        """
        # Upload logo
        logo_file = self.create_test_image()
        result = HospitalLogoService.upload_logo(sample_hospital.hospital_id, logo_file)
        
        # Verify variants
        with get_db_session() as session:
            hospital = session.query(Hospital).get(sample_hospital.hospital_id)
            logo_info = hospital.logo
            
            # Check for expected variants
            expected_variants = ['original', 'large', 'medium', 'small', 'icon']
            
            assert 'variants' in logo_info
            variants = logo_info['variants']
            
            for variant in expected_variants:
                assert variant in variants, f"Missing {variant} variant"
                
                # Verify each variant has necessary information
                assert 'filename' in variants[variant]
                assert 'path' in variants[variant]
                assert 'size' in variants[variant]

    def test_duplicate_logo_upload(self, sample_hospital):
        """
        Test uploading a logo when one already exists
        """
        # First logo upload
        first_logo = self.create_test_image()
        first_result = HospitalLogoService.upload_logo(sample_hospital.hospital_id, first_logo)
        
        # Store paths of first upload
        with get_db_session() as session:
            hospital = session.query(Hospital).get(sample_hospital.hospital_id)
            first_logo_paths = [variant['path'] for variant in hospital.logo['variants'].values()]
        
        # Second logo upload
        second_logo = self.create_test_image(format='JPEG')
        second_result = HospitalLogoService.upload_logo(sample_hospital.hospital_id, second_logo)
        
        # Verify new logo replaces old one
        with get_db_session() as session:
            hospital = session.query(Hospital).get(sample_hospital.hospital_id)
            second_logo_paths = [variant['path'] for variant in hospital.logo['variants'].values()]
            
            # Verify paths are different
            for first_path, second_path in zip(first_logo_paths, second_logo_paths):
                assert first_path != second_path, "Logo files not replaced"

    def test_logo_settings_validation(self):
        """
        Test logo settings validation
        """
        from app.services.hospital_settings_service import HospitalSettingsService
        
        # Valid image
        valid_logo = self.create_test_image()
        validation_result = HospitalSettingsService.validate_logo_settings(valid_logo)
        assert validation_result['valid'] is True
        
        # Invalid file type
        invalid_file = FileStorage(
            stream=io.BytesIO(b'invalid content'), 
            filename='invalid.txt', 
            content_type='text/plain'
        )
        validation_result = HospitalSettingsService.validate_logo_settings(invalid_file)
        assert validation_result['valid'] is False
        assert "Invalid file type" in validation_result['message']

# Add this at the module level (outside any class)
@pytest.fixture
def sample_hospital(db_session):
    """Get or create a test hospital for logo upload"""
    try:
        # Start with a rollback to ensure clean transaction state
        db_session.rollback()
        
        # Try to find an existing hospital
        hospital = db_session.query(Hospital).first()
        
        if not hospital:
            # Create minimal hospital record with basic fields
            import uuid
            unique_license = f"TEST-{uuid.uuid4().hex[:8]}"
            hospital = Hospital(
                name="Test Hospital",
                license_no=unique_license,
                is_active=True,
                address={"street": "Test Street"},
                contact_details={"phone": "123-456-7890"}
            )
            
            db_session.add(hospital)
            db_session.commit()
        
        # Create a detached copy to avoid session issues
        from app.services.database_service import get_detached_copy
        detached_hospital = get_detached_copy(hospital)
        
        return detached_hospital
        
    except Exception as e:
        db_session.rollback()
        raise
# Then remove the sample_hospital fixture from inside the TestHospitalLogoUpload class

# Pytest configuration for this test module
@pytest.mark.logo
@pytest.mark.security
class TestHospitalLogoUploadIntegration:
    """
    Integration tests for hospital logo upload
    Ensures logo upload works with existing hospital management system
    """
    def test_logo_upload_integration(self, client, db_session):
        """
        Integration test for logo upload through web interface
        """
        try:
            # Rollback any failed transaction
            db_session.rollback()
            
            # Try to find an existing hospital
            hospital = db_session.query(Hospital).first()
            
            # If no hospital exists, create one with a unique license
            if not hospital:
                import uuid
                unique_license = f"INT-{uuid.uuid4().hex[:8]}"
                hospital = Hospital(
                    name="Integration Test Hospital",
                    license_no=unique_license,
                    is_active=True,
                    address={"street": "Test Street"},
                    contact_details={"phone": "123-456-7890"}
                )
                    
                db_session.add(hospital)
                db_session.commit()
                
            # Remember the hospital ID
            hospital_id = hospital.hospital_id
                
            # Prepare logo file
            logo_path = os.path.join(os.path.dirname(__file__), 'test_logo.png')
            
            # Create a test logo image
            with Image.new('RGB', (400, 400), color='blue') as img:
                img.save(logo_path)
            
            # Attempt logo upload through client
            with open(logo_path, 'rb') as logo_file:
                response = client.post(
                    f'/admin/hospital/settings',
                    data={
                        'hospital_id': str(hospital_id),
                        'hospital_logo': (logo_file, 'test_logo.png'),
                        'csrf_token': 'test_csrf_token'  # Mock CSRF token
                    },
                    content_type='multipart/form-data'
                )
            
            # Clean up test logo file
            os.remove(logo_path)
            
            # Assert successful upload
            assert response.status_code in [200, 302]  # Redirect or successful response
            
            # Verify logo was stored in database
            with get_db_session() as session:
                updated_hospital = session.query(Hospital).get(hospital_id)
                assert updated_hospital.logo is not None, "Logo was not saved to database"
                
        except Exception as e:
            # Make sure to rollback any failed transaction
            db_session.rollback()
            raise