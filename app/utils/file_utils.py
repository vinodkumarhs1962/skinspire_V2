"""
Utility functions for file storage and management
"""
import os
import uuid
import logging
from datetime import datetime, timedelta
from flask import current_app, url_for

logger = logging.getLogger(__name__)

def store_temporary_file(file_data, filename=None):
    """
    Store file data in a temporary location and return a URL.
    
    Args:
        file_data: Binary file data to store
        filename: Optional filename
        
    Returns:
        URL to access the temporary file
    """
    try:
        # Create temp dir if it doesn't exist
        temp_dir = os.path.join(current_app.static_folder, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique filename if not provided
        if not filename:
            ext = '.tmp'
            if isinstance(filename, str) and '.' in filename:
                ext = os.path.splitext(filename)[1]
            
            filename = f"{uuid.uuid4()}{ext}"
        
        # Ensure filename is safe
        safe_filename = os.path.basename(filename)
        
        # Create the full path
        file_path = os.path.join(temp_dir, safe_filename)
        
        # Write the data
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Return a URL to the file
        return url_for('static', filename=f'temp/{safe_filename}', _external=True)
        
    except Exception as e:
        logger.error(f"Error storing temporary file: {str(e)}", exc_info=True)
        return None