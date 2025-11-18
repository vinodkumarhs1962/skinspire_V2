# New file: app/services/patient_service.py
import uuid
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from flask import current_app
from sqlalchemy import or_, and_, func
from sqlalchemy.dialects.postgresql import JSONB

from app.services.database_service import get_db_session, get_detached_copy
from app.models.master import Patient, Hospital, Branch

# Configure logger
logger = logging.getLogger(__name__)

def search_patients(
    hospital_id: uuid.UUID,
    search_term: str = None,
    limit: int = 20,
    offset: int = 0,
    include_inactive: bool = False,
    session = None
) -> List[Dict]:
    """
    Search for patients by name, MRN, or other attributes
    
    Args:
        hospital_id: UUID of the hospital
        search_term: Optional search term to filter patients
        limit: Maximum number of results to return
        offset: Number of results to skip for pagination
        include_inactive: Whether to include inactive patients
        session: Optional database session
        
    Returns:
        List of patient dictionaries with basic info
    """
    if session is not None:
        return _search_patients(
            session, hospital_id, search_term, limit, offset, include_inactive
        )
    
    with get_db_session() as new_session:
        return _search_patients(
            new_session, hospital_id, search_term, limit, offset, include_inactive
        )

# Modified _search_patients function in patient_service.py
def _search_patients(
    session,
    hospital_id: uuid.UUID,
    search_term: str = None,
    limit: int = 20,
    offset: int = 0,
    include_inactive: bool = False
) -> List[Dict]:
    """Internal function to search patients within a session"""
    try:
        # Input validation
        if limit < 1:
            limit = 20  # Enforce minimum
        if limit > 100:
            limit = 100  # Enforce maximum
        if offset < 0:
            offset = 0
        
        # Start with base query
        query = session.query(Patient).filter(
            Patient.hospital_id == hospital_id
        )
        
        # Filter by active status unless specifically requested
        if not include_inactive:
            query = query.filter(Patient.is_active == True)
        
        # Apply search filter if provided
        if search_term and search_term.strip():
            search_term = f"%{search_term.strip()}%"
            
            # Simplify search to just use standard fields
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Patient.first_name.ilike(search_term),
                    Patient.last_name.ilike(search_term),
                    Patient.full_name.ilike(search_term),
                    Patient.mrn.ilike(search_term)
                )
            )
        
        # Apply pagination - EXPLICITLY USE THE LIMIT PARAMETER
        total_count = query.count()  # Get total before pagination
        patients = query.order_by(Patient.updated_at.desc()).limit(limit).offset(offset).all()
        
        # Format results
        results = []
        for patient in patients:
            try:
                # Get name - SIMPLIFIED: Just first_name + last_name (NO TITLE)
                name = ""
                if hasattr(patient, 'first_name') and hasattr(patient, 'last_name'):
                    # Just concatenate first and last name
                    name_parts = []
                    if patient.first_name:
                        name_parts.append(patient.first_name)
                    if patient.last_name:
                        name_parts.append(patient.last_name)
                    name = ' '.join(name_parts) if name_parts else ''
                elif hasattr(patient, 'full_name') and patient.full_name:
                    # Fallback to full_name if first/last not available
                    name = patient.full_name
                else:
                    name = ''
                
                # Get contact info
                contact = ""
                if hasattr(patient, 'contact_info') and patient.contact_info:
                    if isinstance(patient.contact_info, dict):
                        contact = patient.contact_info.get('phone', '')
                    elif isinstance(patient.contact_info, str):
                        try:
                            import json
                            info = json.loads(patient.contact_info)
                            if isinstance(info, dict):
                                contact = info.get('phone', '')
                        except:
                            pass
                
                # Create result entry
                patient_dict = {
                    'id': str(patient.patient_id),
                    'name': name or f"Patient {patient.mrn or 'Unknown'}",
                    'mrn': patient.mrn or "",
                    'contact': contact
                }
                results.append(patient_dict)
            except Exception as e:
                logger.error(f"Error processing patient result: {str(e)}", exc_info=True)
                # Add minimal data for error case
                results.append({
                    'id': str(patient.patient_id),
                    'name': f"Patient {patient.mrn or 'Unknown'}",
                    'mrn': getattr(patient, 'mrn', ''),
                    'contact': ''
                })
        
        # Return dictionary with pagination info
        return {
            'items': results,
            'total': total_count,
            'page': (offset // limit) + 1 if limit > 0 else 1,
            'page_size': limit,
            'pages': (total_count + limit - 1) // limit if limit > 0 else 1
        }
    except Exception as e:
        logger.error(f"Error searching patients: {str(e)}", exc_info=True)
        # Return empty result set
        return {
            'items': [],
            'total': 0,
            'page': 1,
            'page_size': limit,
            'pages': 0,
            'error': str(e)
        }