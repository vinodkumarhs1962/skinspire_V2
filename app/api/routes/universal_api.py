# =============================================================================
# Universal API Blueprint
# File: app/api/routes/universal_api.py
# 
# Entity-agnostic API endpoints for Universal Engine
# Provides search, autocomplete, and data APIs for all entities
# =============================================================================

from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from typing import Dict, Any, List
import uuid
import json

from app.utils.unicode_logging import get_unicode_safe_logger
from app.services.database_service import get_db_session
from app.config.entity_configurations import get_entity_config
from app.config.entity_configurations import is_valid_entity_type
from app.engine.universal_services import get_universal_service
from app.views.universal_views import has_entity_permission

logger = get_unicode_safe_logger(__name__)

# Create blueprint with /api/universal prefix
universal_api_bp = Blueprint(
    'universal_api',
    __name__,
    url_prefix='/api/universal'
)

@universal_api_bp.route('/<entity_type>/search', methods=['GET'])
@login_required
def entity_search(entity_type: str):
    """
    Universal entity search endpoint for dropdown searches
    
    Query Parameters:
        q: Search query string
        limit: Maximum results to return (default 10, max 50)
        fields: JSON array of fields to search
        exact: Whether to search by exact ID
    
    Returns:
        JSON response with search results
    """
    try:
        # Validate entity type
        if not is_valid_entity_type(entity_type):
            logger.warning(f"Invalid entity type requested: {entity_type}")
            return jsonify({
                'error': f"Invalid entity type: {entity_type}",
                'success': False,
                'results': []
            }), 400
        
        # Check permissions
        if not has_entity_permission(current_user, entity_type, 'read'):
            return jsonify({
                'error': 'Access denied',
                'success': False,
                'results': []
            }), 403
        
        # Get query parameters
        search_term = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)
        search_fields = request.args.get('fields', '[]')
        exact_match = request.args.get('exact', 'false').lower() == 'true'
        
        # Parse search fields
        try:
            search_fields = json.loads(search_fields) if search_fields else []
        except:
            search_fields = []
        
        # Handle singular/plural entity names for configuration lookup
        config_entity_type = entity_type
        if entity_type == 'medicines':
            config_entity_type = 'medicine'  # Map plural to singular for config

        # Get entity configuration
        config = get_entity_config(config_entity_type)
        if not config:
            logger.error(f"No configuration found for entity: {config_entity_type}")
            return jsonify({
                'error': f"No configuration for entity: {entity_type}",
                'success': False,
                'results': []
            }), 404
        
        # FIXED: Get context - User has direct hospital_id attribute
        hospital_id = current_user.hospital_id
        
        # Get branch_id from session
        from flask import session as flask_session
        branch_id = flask_session.get('branch_id')
        
        # Convert to UUID if needed
        if hospital_id and isinstance(hospital_id, str):
            hospital_id = uuid.UUID(hospital_id)
        if branch_id and isinstance(branch_id, str):
            branch_id = uuid.UUID(branch_id)
        
        # Log the search request
        logger.info(f"Search request for {entity_type}: '{search_term}' (limit: {limit})")
        logger.info(f"Context - Hospital: {hospital_id}, Branch: {branch_id}")
        
        # Perform search based on entity type
        results = []
        
        if entity_type == 'suppliers':
            # Special handling for suppliers
            results = search_suppliers(search_term, hospital_id, branch_id, limit)
        elif entity_type == 'patients':
            # Special handling for patients
            # active_only: True for create invoice (only active patients), False for history/lists (all patients)
            active_only = request.args.get('active_only', 'false').lower() == 'true'
            results = search_patients(search_term, hospital_id, branch_id, limit, active_only)
        elif entity_type in ['medicine', 'medicines']:  # Handle both singular and plural
            # Special handling for medicines
            results = search_medicines(search_term, hospital_id, branch_id, limit)
        else:
            # Generic entity search
            results = generic_entity_search(
                config_entity_type, search_term, hospital_id, branch_id, limit, config  # Use config_entity_type
            )
        
        # Format successful response
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results),
            'query': search_term,
            'entity_type': entity_type
        })
        
    except Exception as e:
        logger.error(f"Entity search error for {entity_type}: {str(e)}", exc_info=True)
        return jsonify({
            'error': f"Search failed: {str(e)}",
            'success': False,
            'results': []
        }), 500


def search_suppliers(search_term: str, hospital_id: uuid.UUID, 
                    branch_id: uuid.UUID, limit: int) -> List[Dict]:
    """
    Search suppliers - returns both ID and name for compatibility
    """
    try:
        from app.models.master import Supplier
        
        with get_db_session() as session:
            query = session.query(Supplier).filter(
                Supplier.hospital_id == hospital_id
            )
            
            # Apply soft delete filter
            if hasattr(Supplier, 'deleted_at'):
                query = query.filter(Supplier.deleted_at.is_(None))
            
            # Filter active suppliers only
            query = query.filter(Supplier.status == 'active')
            
            # Add branch filter if specified
            if branch_id:
                query = query.filter(Supplier.branch_id == branch_id)
            
            # Add search filter only if search term provided
            if search_term and search_term.strip():  # ✅ Check for non-empty
                search_pattern = f'%{search_term}%'
                query = query.filter(
                    (Supplier.supplier_name.ilike(search_pattern)) |
                    (Supplier.contact_person_name.ilike(search_pattern))
                )
            
            # Order by supplier name
            query = query.order_by(Supplier.supplier_name)
            
            # Get results - if no search term, return common/recent suppliers
            if not search_term:
                # For initial load, you might want to show:
                # Option 1: Most recently used suppliers
                # Option 2: Most common suppliers
                # Option 3: First N suppliers alphabetically
                limit = min(limit, 20)  # Limit initial load to 20
            
            suppliers = query.limit(limit).all()
            
            # Format for backward compatibility
            results = []
            for supplier in suppliers:
                results.append({
                    'id': supplier.supplier_name,
                    'supplier_id': str(supplier.supplier_id),
                    'supplier_name': supplier.supplier_name,
                    'name': supplier.supplier_name,
                    'value': supplier.supplier_name,
                    'label': supplier.supplier_name,
                    'display': supplier.supplier_name,
                    'text': supplier.supplier_name,
                    'uuid': str(supplier.supplier_id),
                    'contact_person': supplier.contact_person_name or '',
                    'category': supplier.supplier_category or ''
                })
            
            return results
            
    except Exception as e:
        logger.error(f"Supplier search error: {str(e)}")
        return []


def search_patients(search_term: str, hospital_id: uuid.UUID,
                   branch_id: uuid.UUID, limit: int, active_only: bool = False) -> List[Dict]:
    """
    Search patients - returns name for display and filtering

    Args:
        search_term: Search query
        hospital_id: Hospital UUID
        branch_id: Branch UUID (not used - multi-branch access allowed)
        limit: Max results
        active_only: If True, only return active non-deleted patients (for create invoice)
                     If False, return all patients including inactive/deleted (for history/lists)
    """
    try:
        from app.models.master import Patient

        with get_db_session() as session:
            query = session.query(Patient).filter(
                Patient.hospital_id == hospital_id
            )

            # Apply filters based on context (create invoice vs history search)
            if active_only:
                # CREATE INVOICE: Only active, non-deleted patients
                if hasattr(Patient, 'deleted_at'):
                    query = query.filter(Patient.deleted_at.is_(None))
                elif hasattr(Patient, 'is_deleted'):
                    query = query.filter(Patient.is_deleted == False)

                # Filter active patients only
                if hasattr(Patient, 'status'):
                    query = query.filter(Patient.status == 'active')
            else:
                # HISTORY/LISTS: Show all patients (we'll mark their status in display)
                # No filters - include deleted and inactive patients
                pass

            # NO BRANCH FILTER for patient search - Show all patients in hospital
            # This allows cross-branch patient access (important for multi-branch clinics)

            # Add search filter only if search term provided
            if search_term and search_term.strip():
                search_pattern = f'%{search_term}%'
                # Check if Patient has direct name fields or uses JSON
                if hasattr(Patient, 'first_name'):
                    query = query.filter(
                        (Patient.first_name.ilike(search_pattern)) |
                        (Patient.last_name.ilike(search_pattern)) |
                        (Patient.mrn.ilike(search_pattern))
                    )
                else:
                    # If using full_name or JSON field
                    query = query.filter(
                        (Patient.full_name.ilike(search_pattern)) |
                        (Patient.mrn.ilike(search_pattern))
                    )

                # For search results, order by name for easy scanning
                if hasattr(Patient, 'first_name'):
                    query = query.order_by(Patient.first_name, Patient.last_name)
                elif hasattr(Patient, 'full_name'):
                    query = query.order_by(Patient.full_name)
            else:
                # For initial load (no search term), show most recent patients
                # Order by created_at DESC to show newest patients first
                if hasattr(Patient, 'created_at'):
                    query = query.order_by(Patient.created_at.desc())
                elif hasattr(Patient, 'first_name'):
                    query = query.order_by(Patient.first_name, Patient.last_name)
                elif hasattr(Patient, 'full_name'):
                    query = query.order_by(Patient.full_name)

                # Limit initial load to 20 most recent patients
                limit = min(limit, 20)
            
            # Get results
            patients = query.limit(limit).all()
            
            # Format results - consistent with supplier pattern and patient_service
            results = []
            for patient in patients:
                # Get patient name - SIMPLIFIED: Just first_name + last_name (NO TITLE)
                patient_name = ''
                if hasattr(patient, 'first_name') and hasattr(patient, 'last_name'):
                    name_parts = []
                    if patient.first_name:
                        name_parts.append(patient.first_name)
                    if patient.last_name:
                        name_parts.append(patient.last_name)
                    patient_name = ' '.join(name_parts) if name_parts else ''
                elif hasattr(patient, 'full_name') and patient.full_name:
                    patient_name = patient.full_name

                # Fallback to JSON extraction if still no name
                if not patient_name:
                    # Try to extract from personal_info JSON
                    try:
                        if hasattr(patient, 'personal_info') and patient.personal_info:
                            info = patient.personal_info
                            if isinstance(info, str):
                                import json
                                info = json.loads(info)
                            first_name = info.get('first_name', '')
                            last_name = info.get('last_name', '')
                            patient_name = f"{first_name} {last_name}".strip() or 'Unknown Patient'
                        else:
                            patient_name = 'Unknown Patient'
                    except:
                        patient_name = 'Unknown Patient'
                
                # Get patient status
                status = 'active'  # Default
                is_deleted = False

                if hasattr(patient, 'is_deleted') and patient.is_deleted:
                    is_deleted = True
                    status = 'deleted'
                elif hasattr(patient, 'deleted_at') and patient.deleted_at is not None:
                    is_deleted = True
                    status = 'deleted'
                elif hasattr(patient, 'status'):
                    status = patient.status or 'active'

                # Create display name with MRN and status badge
                display_name = patient_name
                if patient.mrn:
                    display_name = f"{patient_name} (MRN: {patient.mrn})"

                # Add status badge for non-active patients (for history/list views)
                status_badge = ''
                if status == 'deleted':
                    status_badge = ' [DELETED]'
                elif status == 'inactive':
                    status_badge = ' [INACTIVE]'

                # Display name with status (for dropdown)
                display_name_with_status = display_name + status_badge

                results.append({
                    # For filtering - value must be NAME (like suppliers)
                    'value': patient_name,                     # ✅ Use NAME for filtering (not UUID)
                    'label': display_name_with_status,         # Label for display WITH status
                    'subtitle': patient.mrn,                   # Subtitle with MRN
                    'status': status,                          # Patient status
                    'status_badge': status_badge.strip('[] '), # Status text without brackets

                    # Compatibility fields
                    'id': patient_name,                        # Use patient name as ID for filtering
                    'patient_id': str(patient.patient_id),    # Keep UUID for reference
                    'patient_name': patient_name,             # Actual name
                    'name': patient_name,                     # Generic name field
                    'display': display_name,                   # Display text WITHOUT status
                    'text': display_name_with_status,          # Alternative display field WITH status

                    # Additional fields for reference
                    'uuid': str(patient.patient_id),          # Actual UUID if needed
                    'mrn': patient.mrn or '',                 # MRN for reference
                    'title': patient.title if hasattr(patient, 'title') else '',
                    'first_name': patient.first_name if hasattr(patient, 'first_name') else '',
                    'last_name': patient.last_name if hasattr(patient, 'last_name') else '',
                    'is_deleted': is_deleted                   # Deletion flag
                })
            
            return results
            
    except Exception as e:
        logger.error(f"Patient search error: {str(e)}")
        return []


def search_medicines(search_term: str, hospital_id: uuid.UUID, 
                    branch_id: uuid.UUID, limit: int) -> List[Dict]:
    """
    Search medicines - returns name for display and filtering
    """
    try:
        from app.models.master import Medicine
        
        with get_db_session() as session:
            query = session.query(Medicine).filter(
                Medicine.hospital_id == hospital_id
            )
            
            # Apply soft delete filter
            if hasattr(Medicine, 'deleted_at'):
                query = query.filter(Medicine.deleted_at.is_(None))
            elif hasattr(Medicine, 'is_deleted'):
                query = query.filter(Medicine.is_deleted == False)
            
            # Filter active medicines only (if status field exists)
            if hasattr(Medicine, 'status'):
                query = query.filter(Medicine.status == 'active')
            
            # Add branch filter if specified (some medicines might not have branch)
            if branch_id and hasattr(Medicine, 'branch_id'):
                query = query.filter(Medicine.branch_id == branch_id)
            
            # Add search filter only if search term provided
            if search_term and search_term.strip():
                search_pattern = f'%{search_term}%'
                # Search by medicine name and generic name
                filters = [Medicine.medicine_name.ilike(search_pattern)]
                
                if hasattr(Medicine, 'generic_name'):
                    filters.append(Medicine.generic_name.ilike(search_pattern))
                if hasattr(Medicine, 'medicine_code'):
                    filters.append(Medicine.medicine_code.ilike(search_pattern))
                
                from sqlalchemy import or_
                query = query.filter(or_(*filters))
            
            # Order by medicine name
            query = query.order_by(Medicine.medicine_name)
            
            # Limit initial load if no search term
            if not search_term:
                limit = min(limit, 20)  # Limit initial load to 20
            
            # Get results
            medicines = query.limit(limit).all()
            
            # Format results - consistent with supplier pattern
            results = []
            for medicine in medicines:
                # Create display name with generic name if available
                display_name = medicine.medicine_name
                if hasattr(medicine, 'generic_name') and medicine.generic_name:
                    display_name = f"{medicine.medicine_name} ({medicine.generic_name})"
                
                # Add strength/dosage if available
                if hasattr(medicine, 'strength') and medicine.strength:
                    display_name = f"{display_name} - {medicine.strength}"
                
                results.append({
                    # Multiple formats for compatibility - use name as value
                    'id': medicine.medicine_name,              # Use name as ID for filtering
                    'medicine_id': str(medicine.medicine_id),  # Keep UUID for reference
                    'medicine_name': medicine.medicine_name,   # Actual name
                    'name': medicine.medicine_name,            # Generic name field
                    'value': medicine.medicine_name,           # Value for dropdown (NAME not UUID)
                    'label': display_name,                     # Label for display with details
                    'display': display_name,                   # Display text
                    'text': display_name,                      # Alternative display field
                    
                    # Additional fields for reference
                    'uuid': str(medicine.medicine_id),         # Actual UUID if needed
                    'generic_name': medicine.generic_name if hasattr(medicine, 'generic_name') else '',
                    'category': medicine.category.name if hasattr(medicine, 'category') and medicine.category else '',  # FIX: category_name → name
                    'manufacturer': medicine.manufacturer.manufacturer_name if hasattr(medicine, 'manufacturer') and medicine.manufacturer else '',
                    'dosage_form': medicine.dosage_form if hasattr(medicine, 'dosage_form') else '',
                    'strength': medicine.strength if hasattr(medicine, 'strength') else '',
                    'medicine_code': medicine.medicine_code if hasattr(medicine, 'medicine_code') else ''
                })
            
            return results
            
    except Exception as e:
        logger.error(f"Medicine search error: {str(e)}")
        return []


def generic_entity_search(entity_type: str, search_term: str, hospital_id: uuid.UUID,
                         branch_id: uuid.UUID, limit: int, config: Any) -> List[Dict]:
    """
    Generic entity search for any entity type
    """
    try:
        # Get model class from registry
        from app.config.entity_registry import get_entity_registration
        import importlib
        
        registration = get_entity_registration(entity_type)
        if not registration or not registration.model_class:
            logger.error(f"No model found for entity type: {entity_type}")
            return []
        
        # Import the model class dynamically
        try:
            module_path, class_name = registration.model_class.rsplit('.', 1)
            module = importlib.import_module(module_path)
            model_class = getattr(module, class_name)
        except Exception as e:
            logger.error(f"Error loading model class for {entity_type}: {str(e)}")
            return []
        
        with get_db_session() as session:
            query = session.query(model_class)
            
            # Apply standard filters
            if hasattr(model_class, 'hospital_id'):
                query = query.filter(model_class.hospital_id == hospital_id)
            
            # Apply soft delete filter
            if hasattr(model_class, 'deleted_at'):
                query = query.filter(model_class.deleted_at.is_(None))
            elif hasattr(model_class, 'is_deleted'):
                query = query.filter(model_class.is_deleted == False)
            
            # Filter active only
            if hasattr(model_class, 'status'):
                query = query.filter(model_class.status == 'active')
            
            # Branch filter
            if branch_id and hasattr(model_class, 'branch_id'):
                query = query.filter(model_class.branch_id == branch_id)
            
            # Search filter only if term provided
            if search_term and search_term.strip():
                search_pattern = f'%{search_term}%'
                search_fields = config.searchable_fields if config else ['name']
                
                filters = []
                for field_name in search_fields:
                    if hasattr(model_class, field_name):
                        field = getattr(model_class, field_name)
                        filters.append(field.ilike(search_pattern))
                
                if filters:
                    from sqlalchemy import or_
                    query = query.filter(or_(*filters))
            
            # Order by title field
            if config and config.title_field and hasattr(model_class, config.title_field):
                query = query.order_by(getattr(model_class, config.title_field))
            
            # Limit initial load
            if not search_term:
                limit = min(limit, 20)
            
            # Get results
            items = query.limit(limit).all()
            
            # Format results
            results = []
            for item in items:
                # Get display name
                display_name = 'Unknown'
                if config and config.title_field and hasattr(item, config.title_field):
                    display_name = getattr(item, config.title_field)
                elif hasattr(item, 'name'):
                    display_name = item.name
                
                # Get ID field
                id_field = config.primary_key if config else f'{entity_type[:-1]}_id'
                item_id = getattr(item, id_field) if hasattr(item, id_field) else None
                
                results.append({
                    'id': display_name,                # Use name as ID
                    'uuid': str(item_id) if item_id else '',
                    'name': display_name,
                    'value': display_name,
                    'label': display_name,
                    'display': display_name,
                    'text': display_name
                })
            
            return results
            
    except Exception as e:
        logger.error(f"Generic entity search error for {entity_type}: {str(e)}")
        return []


# Additional API endpoints can be added here

@universal_api_bp.route('/<entity_type>/autocomplete', methods=['GET'])
@login_required
def entity_autocomplete(entity_type: str):
    """
    Autocomplete endpoint for entity fields
    Returns simplified results optimized for autocomplete
    """
    # Reuse the search endpoint with simplified response
    return entity_search(entity_type)


@universal_api_bp.route('/<entity_type>/validate', methods=['POST'])
@login_required
def validate_entity_field(entity_type: str):
    """
    Validate entity field values
    """
    try:
        data = request.get_json()
        field_name = data.get('field')
        field_value = data.get('value')
        
        # TODO: Implement field validation logic
        
        return jsonify({
            'valid': True,
            'message': 'Valid'
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'message': str(e)
        }), 400


@universal_api_bp.route('/test', methods=['GET'])
def test_api():
    """
    Test endpoint to verify API is working
    """
    return jsonify({
        'success': True,
        'message': 'Universal API is working',
        'endpoints': [
            '/api/universal/<entity_type>/search',
            '/api/universal/<entity_type>/autocomplete',
            '/api/universal/<entity_type>/validate',
            '/api/universal/test'
        ]
    })


# Health check
@universal_api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'service': 'universal_api'
    })