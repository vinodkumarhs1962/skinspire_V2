"""
Utility functions for patient data management.

This module contains helper functions for managing patient data,
especially focused on synchronizing between JSON fields and dedicated columns
to support the transition towards a more structured database schema.
"""

import json
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

def sync_patient_name_fields(patient, personal_info_data=None, update_json=True, update_fields=True):
    """
    Synchronize patient name fields between JSON and dedicated columns.
    
    This utility helps maintain consistency between the legacy JSON storage approach
    and the new dedicated columns approach, ensuring both are kept in sync during
    the transition period.
    
    Args:
        patient: Patient model instance
        personal_info_data: Optional dict or JSON string to use instead of patient.personal_info
        update_json: Whether to update JSON with values from dedicated fields
        update_fields: Whether to update dedicated fields with values from JSON
        
    Returns:
        Updated patient instance with synchronized fields
    """
    # Get personal_info
    if personal_info_data is not None:
        personal_info = personal_info_data
    else:
        personal_info = patient.personal_info
    
    # Convert to dict if string
    personal_info_dict = {}
    if isinstance(personal_info, str):
        try:
            personal_info_dict = json.loads(personal_info)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse personal_info as JSON: {e}")
            personal_info_dict = {}
        except Exception as e:
            logger.error(f"Unexpected error parsing personal_info: {e}")
            personal_info_dict = {}
    else:
        personal_info_dict = personal_info or {}
    
    # Update dedicated fields from JSON if requested
    if update_fields:
        if 'first_name' in personal_info_dict:
            patient.first_name = personal_info_dict['first_name']
        
        if 'last_name' in personal_info_dict:
            patient.last_name = personal_info_dict['last_name']
        
        # Always update full_name based on available data
        first_name = personal_info_dict.get('first_name', '')
        last_name = personal_info_dict.get('last_name', '')
        patient.full_name = f"{first_name} {last_name}".strip()
    
    # Update JSON from dedicated fields if requested
    if update_json:
        if hasattr(patient, 'first_name') and patient.first_name:
            personal_info_dict['first_name'] = patient.first_name
        
        if hasattr(patient, 'last_name') and patient.last_name:
            personal_info_dict['last_name'] = patient.last_name
            
        # Update the patient's personal_info with the modified dict
        if isinstance(patient.personal_info, str):
            # If it was a string, keep it as a string
            patient.personal_info = json.dumps(personal_info_dict)
        else:
            # Otherwise, keep it as a dict
            patient.personal_info = personal_info_dict
    
    return patient

def extract_patient_name(personal_info: Union[str, Dict]) -> Dict[str, str]:
    """
    Extract first name, last name, and full name from personal_info.
    
    Args:
        personal_info: Patient personal info as JSON string or dict
        
    Returns:
        Dictionary with 'first_name', 'last_name', and 'full_name' keys
    """
    # Convert to dict if string
    if isinstance(personal_info, str):
        try:
            info_dict = json.loads(personal_info)
        except:
            logger.warning("Failed to parse personal_info, returning empty values")
            return {'first_name': '', 'last_name': '', 'full_name': ''}
    else:
        info_dict = personal_info or {}
    
    # Extract name components
    first_name = info_dict.get('first_name', '')
    last_name = info_dict.get('last_name', '')
    full_name = f"{first_name} {last_name}".strip()
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'full_name': full_name
    }

def update_patient_name(patient, first_name=None, last_name=None):
    """
    Update patient name fields both in dedicated columns and JSON.
    
    Args:
        patient: Patient model instance
        first_name: New first name (optional)
        last_name: New last name (optional)
        
    Returns:
        Updated patient instance
    """
    # Get current personal_info as dict
    if isinstance(patient.personal_info, str):
        try:
            personal_info = json.loads(patient.personal_info)
        except:
            logger.warning("Failed to parse personal_info, creating new dict")
            personal_info = {}
    else:
        personal_info = patient.personal_info or {}
    
    # Update fields that are provided
    if first_name is not None:
        patient.first_name = first_name
        personal_info['first_name'] = first_name
    
    if last_name is not None:
        patient.last_name = last_name
        personal_info['last_name'] = last_name
    
    # Get the values to use for full_name
    first = first_name if first_name is not None else (patient.first_name or personal_info.get('first_name', ''))
    last = last_name if last_name is not None else (patient.last_name or personal_info.get('last_name', ''))
    
    # Update full_name
    patient.full_name = f"{first} {last}".strip()
    
    # Update personal_info
    if isinstance(patient.personal_info, str):
        patient.personal_info = json.dumps(personal_info)
    else:
        patient.personal_info = personal_info
    
    return patient

def has_dedicated_name_fields(patient) -> bool:
    """
    Check if patient has populated dedicated name fields.
    
    Args:
        patient: Patient model instance
        
    Returns:
        True if at least one dedicated name field is populated
    """
    return (hasattr(patient, 'first_name') and bool(patient.first_name)) or \
           (hasattr(patient, 'last_name') and bool(patient.last_name)) or \
           (hasattr(patient, 'full_name') and bool(patient.full_name))

def format_patient_display_name(patient) -> str:
    """
    Generate a consistent display name for a patient.
    
    This handles various scenarios of how name data might be stored
    and provides a consistent way to display patient names.
    
    Args:
        patient: Patient model instance
        
    Returns:
        Formatted display name
    """
    # Try dedicated fields first
    if has_dedicated_name_fields(patient):
        if hasattr(patient, 'full_name') and patient.full_name:
            return patient.full_name
        
        name_parts = []
        if hasattr(patient, 'title') and patient.title:
            name_parts.append(patient.title)
        if hasattr(patient, 'first_name') and patient.first_name:
            name_parts.append(patient.first_name)
        if hasattr(patient, 'last_name') and patient.last_name:
            name_parts.append(patient.last_name)
        
        if name_parts:
            return " ".join(name_parts)
    
    # Fall back to JSON fields
    try:
        if hasattr(patient, 'personal_info'):
            if isinstance(patient.personal_info, dict):
                info = patient.personal_info
            elif isinstance(patient.personal_info, str):
                info = json.loads(patient.personal_info)
            else:
                return f"Patient {getattr(patient, 'mrn', '')}"
                
            name_parts = []
            if info.get('title'):
                name_parts.append(info['title'])
            if info.get('first_name'):
                name_parts.append(info['first_name'])
            if info.get('last_name'):
                name_parts.append(info['last_name'])
                
            if name_parts:
                return " ".join(name_parts)
    except:
        pass
    
    # Last resort: use MRN or ID if available
    if hasattr(patient, 'mrn') and patient.mrn:
        return f"Patient {patient.mrn}"
    elif hasattr(patient, 'patient_id'):
        return f"Patient {str(patient.patient_id)[:8]}"
    else:
        return "Unknown Patient"