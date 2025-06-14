# app/config/logo_logging.py

import logging
from logging.handlers import RotatingFileHandler
import os

def configure_logo_logging(app):
    """
    Configure logging specifically for logo-related events
    
    Args:
        app: Flask application instance
    """
    # Ensure logs directory exists
    log_dir = os.path.join(app.root_path, 'logs', 'logo')
    os.makedirs(log_dir, exist_ok=True)
    
    # Logo events log file
    logo_log_path = os.path.join(log_dir, 'logo_events.log')
    
    # Create a rotating file handler
    logo_handler = RotatingFileHandler(
        logo_log_path, 
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    
    # Set log format
    logo_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - Hospital: %(hospital_id)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logo_handler.setFormatter(logo_formatter)
    
    # Create a logger for logo events
    logo_logger = logging.getLogger('hospital_logo_events')
    logo_logger.setLevel(logging.INFO)
    logo_logger.addHandler(logo_handler)
    
    return logo_logger

# Patch the logo service to use this logger
def patch_logo_service_logging(logo_service, logger):
    """
    Patch the logo service to use custom logging
    
    Args:
        logo_service: HospitalLogoService class
        logger: Logger instance
    """
    original_upload_method = logo_service.upload_logo
    
    def logged_upload_method(hospital_id, logo_file):
        try:
            # Add extra context to log record
            extra = {'hospital_id': str(hospital_id)}
            
            # Log start of upload
            logger.info(
                f"Logo upload initiated - Filename: {logo_file.filename}", 
                extra=extra
            )
            
            # Call original method
            result = original_upload_method(hospital_id, logo_file)
            
            # Log result
            if result['success']:
                logger.info(
                    f"Logo upload successful - Filename: {logo_file.filename}", 
                    extra=extra
                )
            else:
                logger.warning(
                    f"Logo upload failed - Filename: {logo_file.filename}, Reason: {result.get('message', 'Unknown')}", 
                    extra=extra
                )
            
            return result
        
        except Exception as e:
            # Log any unexpected errors
            logger.error(
                f"Unexpected error during logo upload - Filename: {logo_file.filename}, Error: {str(e)}", 
                extra={'hospital_id': str(hospital_id)},
                exc_info=True
            )
            raise
    
    # Replace the method
    logo_service.upload_logo = logged_upload_method

# In your application factory or initialization
def init_logo_logging(app):
    """
    Initialize logo logging for the application
    
    Args:
        app: Flask application instance
    """
    from app.services.hospital_logo_service import HospitalLogoService
    
    # Configure logo logging
    logo_logger = configure_logo_logging(app)
    
    # Patch logo service logging
    patch_logo_service_logging(HospitalLogoService, logo_logger)
    
    return logo_logger