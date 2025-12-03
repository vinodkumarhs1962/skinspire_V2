# app/views/billing_views.py

import uuid
import json
import logging
logger = logging.getLogger('app.services.billing_service')
from datetime import datetime, timezone, timedelta, date
import decimal
from decimal import Decimal, InvalidOperation
from num2words import num2words
from sqlalchemy import func, and_, or_


from flask import current_app as app
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session as flask_session
from flask_login import login_required, current_user
from flask import url_for as flask_url_for
from urllib.parse import urlencode  # Use standard library for URL encoding

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, DateField, DecimalField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError

from app.controllers.billing_controllers import AdvancePaymentController, PaymentFormController 
from app.forms.billing_forms import InvoiceForm, PaymentForm, AdvancePaymentForm
from app.services.billing_service import (
    create_invoice,
    get_invoice_by_id,
    record_payment,
    approve_payment,
    reject_payment,
    reverse_payment,
    search_invoices,
    void_invoice,
    issue_refund,
    get_batch_selection_for_invoice,
    get_patient_advance_payments,
    get_patient_advance_balance,
    create_advance_payment,
    apply_advance_payment
)
from app.utils.menu_utils import get_menu_items
from app.security.authorization.permission_validator import has_permission, permission_required
from app.services.database_service import get_db_session, get_detached_copy, get_entity_dict
from app.security.authentication.auth_manager import AuthManager
from app.models.master import Hospital, Branch, Medicine, Package, Service, Patient
from app.models.transaction import User, InvoiceHeader, InvoiceLineItem, Inventory, PaymentDetail, PatientAdvancePayment, AdvanceAdjustment, ARSubledger

# For email functionality
from app.services.email_service import send_email_with_attachment

# For WhatsApp functionality
from app.services.whatsapp_service import send_whatsapp_message

# For PDF generation and temporary file storage (optional - requires xhtml2pdf)
try:
    from app.utils.pdf_utils import generate_invoice_pdf
    from app.utils.file_utils import store_temporary_file
    PDF_AVAILABLE = True
except ImportError as e:
    logging.warning(f"PDF generation not available: {str(e)}")
    PDF_AVAILABLE = False
    generate_invoice_pdf = None
    store_temporary_file = None

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint
billing_views_bp = Blueprint('billing_views', __name__, url_prefix='/invoice')

# Helper function to delegate to new API
# Update the billing API endpoints mapping
billing_api_endpoints = {
    'billing_api.api_patient_search': 'billing_api.api_patient_search_web',
    'billing_api.api_item_search': 'billing_api.api_item_search_web',
    'billing_api.api_medicine_batches': 'billing_api.api_medicine_batches_web',
    'billing_api.create_invoice_api': 'billing_api.create_invoice_api_web',
    'billing_api.get_invoice_api': 'billing_api.get_invoice_api_web',
    'billing_api.search_invoices_api': 'billing_api.search_invoices_api_web'
}

def parse_date(date_str):
    """Parse a date string in YYYY-MM-DD format to a date object."""
    if not date_str:
        return None
    try:
        # Try parsing the date string
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Return None if the date string couldn't be parsed
        return None


def delegate_to_api(endpoint_name, **kwargs):
    """Delegate a request to the new API endpoint"""

    """DEPRECATED: Function to delegate requests to API endpoints
    
    This function is deprecated as direct implementations are now available in billing_views.py.
    Kept for backward compatibility with any existing code that might call it.
    """
    current_app.logger.warning(f"Using deprecated delegate_to_api function to access {endpoint_name}. Consider using direct endpoints.")

    from flask import request, current_app, session as flask_session, jsonify
    import requests
    from urllib.parse import urlencode
    
    # Check if this is a billing API endpoint that should use web adapter
    if endpoint_name in billing_api_endpoints:
        # Use the web-friendly adapter endpoint instead
        web_endpoint = billing_api_endpoints[endpoint_name]
        
        # For medicine batches, we need to preserve the medicine_id parameter
        if endpoint_name == 'billing_api.api_medicine_batches':
            medicine_id = kwargs.get('medicine_id')
            new_url = flask_url_for(web_endpoint, medicine_id=medicine_id, _external=True)
        else:
            new_url = flask_url_for(web_endpoint, _external=True)
        
        # Forward the query parameters
        if request.args:
            new_url += "?" + urlencode(request.args)
            
        # Make the request to the adapter endpoint
        try:
            if request.method == 'GET':
                resp = requests.get(new_url)
            elif request.method == 'POST':
                data = request.form or request.get_json(silent=True) or {}
                resp = requests.post(new_url, json=data)
            else:
                resp = requests.request(
                    method=request.method,
                    url=new_url,
                    data=request.get_data()
                )
            return resp.content, resp.status_code, resp.headers.items()
        except Exception as e:
            current_app.logger.error(f"Error delegating to web API: {str(e)}")
            return jsonify({"error": "Error delegating to API"}), 500
    
    # For other endpoints, use the original approach with token authentication
    # Build the URL to the new API endpoint
    new_url = flask_url_for(endpoint_name, _external=True, **kwargs)
    
    # Forward the query parameters
    if request.args:
        new_url += "?" + urlencode(request.args)
    
    # For original delegation pattern
    try:
        # Get all headers to forward
        headers = dict(request.headers)
        
        # If there's no Authorization header but there's a session with an auth token
        if 'Authorization' not in headers and 'auth_token' in flask_session:
            headers['Authorization'] = f'Bearer {flask_session["auth_token"]}'
            
        # Forward the request with appropriate headers
        resp = requests.request(
            method=request.method,
            url=new_url,
            headers=headers,
            data=request.get_data()
        )
        
        # Return the response as-is
        return resp.content, resp.status_code, resp.headers.items()
    except Exception as e:
        current_app.logger.error(f"Error delegating to API: {str(e)}")
        return jsonify({"error": "Error delegating to API"}), 500

@billing_views_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'create')
def create_invoice_view():
    """View for creating a new invoice"""
    # Import SQLAlchemy operators
    from sqlalchemy import or_, and_
    from decimal import InvalidOperation
    
    # Check for error data from previous submission (form data preservation)
    error_data = flask_session.pop('invoice_error_data', None)
    error_message = flask_session.pop('invoice_error_message', None)

    # Display error message if present
    if error_message:
        flash(error_message, 'error')
        logger.info(f"Displaying preserved error: {error_message}")

    # Clear any cached patient ID to ensure fresh selection each time (unless we have error data)
    if 'temp_patient_id' in flask_session and not error_data:
        flask_session.pop('temp_patient_id', None)

    # Prepare patient choices
    patient_choices = [('', 'Select Patient')]
    
    # Log request information
    logger.info(f"create_invoice_view accessed with method: {request.method}")
    logger.info(f"Request Content-Type: {request.content_type}")
    
    if request.method == 'POST':
        logger.info("POST request received")
        logger.info(f"Form data: {request.form}")
        logger.info(f"JSON data: {request.get_json(silent=True)}")
        logger.info(f"Files: {request.files}")
        
        # Log CSRF token information to help diagnose issues
        csrf_token = request.form.get('csrf_token')
        logger.info(f"CSRF token present: {csrf_token is not None}")
        if csrf_token:
            logger.info(f"CSRF token length: {len(csrf_token)}")
    
    try:
        with get_db_session() as session:
            # Get initial set of patients (first 10 active patients)
            patients = session.query(Patient).filter(
                Patient.hospital_id == current_user.hospital_id,
                Patient.is_active == True
            ).limit(10).all()
            
            # Create detached copies of patients
            patients = [get_detached_copy(patient) for patient in patients]

            # Add patients to choices - SIMPLIFIED: first_name + last_name only
            patient_choices.extend([
                (str(patient.patient_id), f"{patient.first_name} {patient.last_name} - {patient.mrn or 'No MRN'}")
                for patient in patients
            ])
    except Exception as e:
        current_app.logger.error(f"Error loading patients: {str(e)}", exc_info=True)
        flash("Unable to load patients. Please try again.", "error")
    
    # Create form with patient choices
    form = InvoiceForm(patient_choices=patient_choices)
    
    # Pre-populate invoice_date with current date
    form.invoice_date.data = datetime.now(timezone.utc).date()

    # Set default place of supply to Karnataka (29)
    form.place_of_supply.data = '29'

    # Generate JWT token for API calls
    auth_token = None
    try:
        with get_db_session() as db_session:
            auth_manager = AuthManager(session=db_session)
            # Create a proper session for the user
            auth_token = auth_manager.create_session(current_user.user_id, str(current_user.hospital_id))
            logger.info(f"Generated auth token: {auth_token[:10]}... for user {current_user.user_id}")
    except Exception as e:
        logger.error(f"Error generating auth token: {str(e)}", exc_info=True)

    # Get branches for dropdown
    branches = []
    try:
        with get_db_session() as session:
            branches_query = session.query(Branch).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True
            ).all()
            
            # Create detached copies before accessing properties
            branches_detached = [get_detached_copy(branch) for branch in branches_query]
            
            # Convert to dictionary format for the template
            branches = [
                {'branch_id': str(branch.branch_id), 'name': branch.name} 
                for branch in branches_detached
            ]
    except Exception as e:
        logger.error(f"Error loading branches: {str(e)}", exc_info=True)

    # Get menu items for dashboard
    menu_items = get_menu_items(current_user)

    # Get user's batch allocation mode preference (manual or auto)
    user_batch_mode = 'manual'  # Default to manual
    if current_user.ui_preferences:
        ui_prefs = current_user.ui_preferences
        if isinstance(ui_prefs, str):
            import json
            ui_prefs = json.loads(ui_prefs)
        user_batch_mode = ui_prefs.get('invoice_batch_mode', 'manual')

    # Process form submission
    if request.method == 'POST':
        # Import CSRF validation utilities if needed
        from flask_wtf.csrf import validate_csrf
        from wtforms.validators import ValidationError
        
        # Check if we have a CSRF token in the form data
        csrf_token = request.form.get('csrf_token')
        if not csrf_token:
            logger.error("Missing CSRF token in form submission")
            flash("Form submission failed: CSRF token missing. Please try again.", "error")
            can_edit_discount = current_user.has_permission('billing', 'edit_discount')
            return render_template(
                'billing/create_invoice.html',
                form=form,
                branches=branches,
                menu_items=menu_items,
                page_title="Create Invoice",
                auth_token=auth_token,
                can_edit_discount=can_edit_discount
            )
        
        # Check for patient_id in form data or data attributes
        patient_id = request.form.get('patient_id')
        patient_name = request.form.get('patient_name')

        # FIX: Detect if patient_id contains a NAME instead of UUID
        if patient_id and (' ' in patient_id or '-' not in patient_id):
            # This looks like a name, not a UUID
            logger.warning(f"❌ DETECTED: patient_id field contains a NAME instead of UUID: '{patient_id}'")
            # Move it to patient_name and clear patient_id
            if not patient_name:
                patient_name = patient_id
            patient_id = None
            logger.info(f"Moved name to patient_name field, will lookup UUID below")

        # Check for cached patient ID from previous attempts
        temp_patient_id = flask_session.get('temp_patient_id')
        if temp_patient_id and not patient_id:
            logger.info(f"Using cached patient ID from session: {temp_patient_id}")
            patient_id = temp_patient_id
            # Set in form for validation
            form.patient_id.data = patient_id
        
        # If patient_id is missing but we have patient_name, try to find the patient
        if not patient_id and patient_name:
            logger.info(f"Patient ID missing but name provided: {patient_name}. Attempting to find patient.")
            try:
                with get_db_session() as session:
                    # Try various ways to find the patient
                    # First try exact match on full name parts
                    name_parts = patient_name.split()
                    
                    query_filters = []
                    
                    # Try matching first and last name
                    if len(name_parts) >= 1:
                        first_name = name_parts[0]
                        last_name = " ".join(name_parts[1:])  # All other parts as last name
                        
                        query_filters.append(
                            and_(
                                Patient.personal_info['first_name'].astext.ilike(first_name),
                                Patient.personal_info['last_name'].astext.ilike(last_name)
                            )
                        )
                    
                    # Add more flexible search patterns
                    query_filters.append(
                        or_(
                            # Search first name or last name with partial match
                            Patient.personal_info['first_name'].astext.ilike(f'%{patient_name}%'),
                            Patient.personal_info['last_name'].astext.ilike(f'%{patient_name}%'),
                            # Also try MRN in case patient_name contains an MRN
                            Patient.mrn.ilike(f'%{patient_name}%')
                        )
                    )
                    
                    # Try each search filter in order
                    patient = None
                    for filter_condition in query_filters:
                        patient = session.query(Patient).filter(
                            Patient.hospital_id == current_user.hospital_id,
                            filter_condition
                        ).first()
                        
                        if patient:
                            break
                    
                    if patient:
                        # Found patient - set ID in form
                        logger.info(f"Found patient by name: {patient_name}, ID: {patient.patient_id}")
                        form.patient_id.data = str(patient.patient_id)
                        patient_id = str(patient.patient_id)
                        
                        # Store in session for later use in case form validation fails
                        flask_session['temp_patient_id'] = patient_id
                    else:
                        # Patient not found - provide a helpful message
                        logger.warning(f"Patient not found with name: {patient_name}")
                        flash(f"Patient '{patient_name}' not found. Please select a patient from the search results.", "error")
                        # Continue with form rendering to allow retry
            except Exception as e:
                logger.error(f"Error finding patient by name: {str(e)}", exc_info=True)
        
        
        # Standard form validation
        if form.validate_on_submit():
            try:
                # Process line items directly from form data for backward compatibility
                line_items = []
                
                # Try to use the form method if available
                if hasattr(form, 'process_line_items') and callable(getattr(form, 'process_line_items')):
                    try:
                        line_items = form.process_line_items()
                    except Exception as e:
                        current_app.logger.warning(f"Could not use form.process_line_items(): {str(e)}")
                        # Fall back to manual processing
                
                # If line_items is still empty, process manually
                if not line_items:
                    current_app.logger.info("📋 Processing line items manually from form data")
                    current_app.logger.info(f"📋 Form keys: {list(request.form.keys())}")

                    for key in request.form:
                        if key.startswith('line_items-') and key.endswith('-item_type'):
                            # Extract index from key
                            index = key.split('-')[1]
                            current_app.logger.info(f"📋 Found line item at index {index}")

                            try:
                                item = {
                                    'item_type': request.form.get(f'line_items-{index}-item_type'),
                                    'item_id': request.form.get(f'line_items-{index}-item_id'),
                                    'item_name': request.form.get(f'line_items-{index}-item_name'),
                                    'batch': request.form.get(f'line_items-{index}-batch'),
                                    'expiry_date': parse_date(request.form.get(f'line_items-{index}-expiry_date')),
                                    'quantity': Decimal(request.form.get(f'line_items-{index}-quantity', '1')),
                                    'unit_price': Decimal(request.form.get(f'line_items-{index}-unit_price', '0')),
                                    'discount_percent': Decimal(request.form.get(f'line_items-{index}-discount_percent', '0')),
                                    'discount_override': request.form.get(f'line_items-{index}-discount_override', 'false').lower() == 'true',
                                    'included_in_consultation': bool(request.form.get(f'line_items-{index}-included_in_consultation')),
                                    # Free Item support (promotional - GST on MRP)
                                    'is_free_item': request.form.get(f'line_items-{index}-is_free_item', 'false').lower() == 'true',
                                    'free_item_reason': request.form.get(f'line_items-{index}-free_item_reason', ''),
                                    # Sample/Trial item support (no GST, no charge)
                                    'is_sample': request.form.get(f'line_items-{index}-is_sample', 'false').lower() == 'true',
                                    'sample_reason': request.form.get(f'line_items-{index}-sample_reason', '')
                                }
                                # Debug log for free/sample fields
                                raw_is_free = request.form.get(f'line_items-{index}-is_free_item', 'NOT_FOUND')
                                raw_is_sample = request.form.get(f'line_items-{index}-is_sample', 'NOT_FOUND')
                                current_app.logger.info(f"🎁 Line {index} FREE/SAMPLE raw values: is_free_item={raw_is_free}, is_sample={raw_is_sample}")
                                current_app.logger.info(f"📋 Line item {index}: {item}")
                                line_items.append(item)
                            except (ValueError, TypeError, decimal.InvalidOperation) as e:
                                current_app.logger.error(f"Error processing line item {index}: {str(e)}")
                                raise ValueError(f"Invalid data in line item {int(index)+1}")

                    current_app.logger.info(f"📋 Total line items extracted: {len(line_items)}")
                
                # Convert invoice_date to datetime with timezone
                invoice_date = form.invoice_date.data
                invoice_date = datetime.combine(invoice_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                
                # Get branch_id and handle empty value
                branch_id = request.form.get('branch_id', '')
                if not branch_id or branch_id.strip() == '':
                    # Get the first branch for the hospital as a fallback
                    with get_db_session() as session:
                        default_branch = session.query(Branch).filter_by(
                            hospital_id=current_user.hospital_id,
                            is_active=True
                        ).first()
                        
                        if default_branch:
                            branch_id = str(default_branch.branch_id)
                            current_app.logger.info(f"Using default branch_id: {branch_id}")
                        else:
                            # If no default branch is found, raise an error
                            raise ValueError("Please select a branch for the invoice")
                
                invoice_data = {
                    'hospital_id': current_user.hospital_id,
                    'branch_id': branch_id,  # Now guaranteed to be non-empty
                    'patient_id': form.patient_id.data,
                    'invoice_date': invoice_date,
                    'line_items': line_items,
                    'notes': form.notes.data,
                    'current_user_id': current_user.user_id
                }
                
                current_app.logger.info("Invoice Creation Request Received")
                current_app.logger.info(f"Hospital ID: {invoice_data['hospital_id']}")
                current_app.logger.info(f"Branch ID: {invoice_data['branch_id']}")
                current_app.logger.info(f"Patient ID: {invoice_data['patient_id']}")
                current_app.logger.info(f"Invoice Date: {invoice_data['invoice_date']}")
                current_app.logger.info(f"Number of Line Items: {len(line_items)}")
                current_app.logger.info(f"Current User ID: {invoice_data['current_user_id']}")
                
                # Log details of each line item
                for i, item in enumerate(line_items, start=1):
                    current_app.logger.info(f"Line Item {i}: Type={item.get('item_type')}, ID={item.get('item_id')}, Name={item.get('item_name')}")
                
                # Create the invoice(s)
                result = create_invoice(**invoice_data)

                # Single invoice case (not split)
                if len(result['invoices']) == 1:
                    invoice = result['invoices'][0]
                    flash(f"Invoice {invoice['invoice_number']} created successfully", "success")
                    # Redirect to universal engine detail view
                    return redirect(url_for('universal_views.universal_detail_view',
                                          entity_type='patient_invoices',
                                          item_id=invoice['invoice_id']))

                # Multiple invoices case (Phase 3 split invoices)
                if len(result['invoices']) > 1:
                    parent_id = result.get('parent_invoice_id')
                    current_app.logger.info(f"Multiple invoices created. Parent ID from result: {parent_id}")

                    if not parent_id:
                        # Fallback: Use first invoice ID as parent
                        parent_id = result['invoices'][0].get('invoice_id')
                        current_app.logger.warning(f"Parent invoice ID was None! Using first invoice ID: {parent_id}")

                    flash(f"✓ {len(result['invoices'])} consolidated invoices created successfully", "success")
                    # Redirect to consolidated invoice detail view (Universal Engine)
                    return redirect(url_for('universal_views.consolidated_invoice_detail_view',
                                          parent_invoice_id=parent_id))

                # No invoices created
                flash("No invoices were created. Please check the form and try again.", "warning")
                return render_template('billing/create_invoice.html', form=form, auth_token=auth_token)
                
            except Exception as e:
                current_app.logger.error(f"Error creating invoice: {str(e)}")

                # Preserve line items to prevent data loss (for ALL errors)
                preserved_line_items = []
                for key in request.form:
                    if key.startswith('line_items-') and key.endswith('-item_type'):
                        # Extract index from key
                        index = key.split('-')[1]

                        try:
                            # Get expiry date and handle format
                            expiry_date_str = request.form.get(f'line_items-{index}-expiry_date', '')

                            item = {
                                'index': index,
                                'item_type': request.form.get(f'line_items-{index}-item_type', ''),
                                'item_id': request.form.get(f'line_items-{index}-item_id', ''),
                                'item_name': request.form.get(f'line_items-{index}-item_name', ''),
                                'batch': request.form.get(f'line_items-{index}-batch', ''),
                                'expiry_date': expiry_date_str if expiry_date_str else '',
                                'quantity': request.form.get(f'line_items-{index}-quantity', '1'),
                                'unit_price': request.form.get(f'line_items-{index}-unit_price', '0'),
                                'discount_percent': request.form.get(f'line_items-{index}-discount_percent', '0'),
                                'discount_override': request.form.get(f'line_items-{index}-discount_override', 'false').lower() == 'true',
                                'gst_rate': request.form.get(f'line_items-{index}-gst_rate', '0'),
                                'included_in_consultation': bool(request.form.get(f'line_items-{index}-included_in_consultation', False))
                            }

                            # Only add if there's actual data
                            if item['item_id'] or item['item_name']:
                                preserved_line_items.append(item)
                                current_app.logger.info(f"Preserved line item {index}: {item['item_name']}")
                        except Exception as item_error:
                            current_app.logger.error(f"Error preserving line item {index}: {str(item_error)}")

                # Determine error type for better messaging
                if "Insufficient stock" in str(e):
                    flash(f"Inventory Error: {str(e)}", "error")
                    inventory_error = str(e)
                else:
                    flash(f"Error creating invoice: {str(e)}", "error")
                    inventory_error = None

                # Preserve patient data explicitly (form binding may not retain it)
                preserved_patient_id = request.form.get('patient_id', '')
                preserved_patient_name = request.form.get('patient_name', '')
                current_app.logger.info(f"Preserved patient: ID={preserved_patient_id}, Name={preserved_patient_name}")

                # Return template with preserved data
                can_edit_discount = current_user.has_permission('billing', 'edit_discount')
                return render_template(
                    'billing/create_invoice.html',
                    form=form,
                    branches=branches,
                    menu_items=menu_items,
                    page_title="Create Invoice",
                    auth_token=auth_token,
                    user_batch_mode=user_batch_mode,
                    inventory_error=inventory_error,
                    preserved_line_items=preserved_line_items,
                    preserved_patient_id=preserved_patient_id,
                    preserved_patient_name=preserved_patient_name,
                    can_edit_discount=can_edit_discount
                )
        else:
            # Handle validation failures
            if request.method == 'POST':
                # Check for CSRF token
                csrf_token = request.form.get('csrf_token')
                current_app.logger.info(f"CSRF token present: {bool(csrf_token)}")
                if csrf_token:
                    current_app.logger.info(f"CSRF token length: {len(csrf_token)}")
                
                # Check if we're trying to handle a JSON string patient
                import json
                if patient_name and (patient_name.startswith('{') or patient_name.startswith('{')):
                    try:
                        # It's a JSON string, try to find patient by raw match on personal_info
                        current_app.logger.info(f"Received JSON patient name: {patient_name}")
                        
                        # Convert the string to an actual JSON object for proper comparison
                        from sqlalchemy import cast, String
                        with get_db_session() as session:
                            # Try searching by the exact string with double quotes
                            patients = session.query(Patient).filter(
                                Patient.hospital_id == current_user.hospital_id,
                                cast(Patient.personal_info, String) == patient_name
                            ).all()
                            
                            if patients:
                                patient_id = str(patients[0].patient_id)
                                current_app.logger.info(f"Found patient by JSON exact match: {patient_id}")
                            else:
                                # Try parsing the JSON and matching the contents
                                parsed_name = json.loads(patient_name)
                                if isinstance(parsed_name, dict):
                                    # Try to match first_name and last_name
                                    first_name = parsed_name.get('first_name', '')
                                    last_name = parsed_name.get('last_name', '')
                                    
                                    patients = session.query(Patient).filter(
                                        Patient.hospital_id == current_user.hospital_id,
                                        cast(Patient.personal_info['first_name'].astext, String).ilike(first_name),
                                        cast(Patient.personal_info['last_name'].astext, String).ilike(last_name)
                                    ).all()
                                    
                                    if patients:
                                        patient_id = str(patients[0].patient_id)
                                        current_app.logger.info(f"Found patient by JSON content match: {patient_id}")
                    except Exception as e:
                        current_app.logger.error(f"Error parsing JSON patient name: {str(e)}")
                
                # If we have a patient name but no ID, try to find the patient
                elif patient_name and not form.patient_id.data:
                    current_app.logger.info(f"Patient ID missing but name provided: {patient_name}. Attempting to find patient.")
                    with get_db_session() as session:
                        # Try to find patient by name
                        patient = session.query(Patient).filter(
                            Patient.hospital_id == current_user.hospital_id,
                            Patient.full_name.ilike(f"%{patient_name}%")
                        ).first()
                        
                        if patient:
                            patient_id = str(patient.patient_id)
                            current_app.logger.info(f"Found patient by name: {patient_name}, ID: {patient_id}")
                        else:
                            current_app.logger.warning(f"Patient not found with name: {patient_name}")
                
                # If we found a patient ID, use it to proceed with manual creation
                if patient_id:
                    # Manually validate the line items
                    valid_line_items = True
                    processed_line_items = []
                    
                    # Get the count of line items
                    line_items_count = int(request.form.get('line_items_count', 0))
                    
                    current_app.logger.info(f"Validating line items: {line_items_count} items found")
                    
                    # Process each line item
                    for i in range(line_items_count):
                        prefix = f'line_items-{i}-'
                        
                        try:
                            item = {
                                'item_type': request.form.get(f'{prefix}item_type'),
                                'item_id': request.form.get(f'{prefix}item_id'),
                                'item_name': request.form.get(f'{prefix}item_name'),
                                'batch': request.form.get(f'{prefix}batch'),
                                'expiry_date': parse_date(request.form.get(f'{prefix}expiry_date')),
                                'quantity': Decimal(request.form.get(f'{prefix}quantity', '1')),
                                'unit_price': Decimal(request.form.get(f'{prefix}unit_price', '0')),
                                'discount_percent': Decimal(request.form.get(f'{prefix}discount_percent', '0')),
                                'discount_override': request.form.get(f'{prefix}discount_override', 'false').lower() == 'true',
                                'included_in_consultation': bool(request.form.get(f'{prefix}included_in_consultation'))
                            }
                            
                            if not item['item_id'] or not item['item_name']:
                                valid_line_items = False
                                break
                            
                            processed_line_items.append(item)
                            current_app.logger.info(f"Line item {i}: {item}")
                            
                        except (ValueError, TypeError, decimal.InvalidOperation) as e:
                            current_app.logger.error(f"Error processing line item {i}: {str(e)}")
                            valid_line_items = False
                            break
                    
                    # If we have valid line items, create the invoice manually
                    if valid_line_items and processed_line_items:
                        current_app.logger.info("Form validation failed but patient_id is available. Attempting manual creation.")
                        
                        try:
                            # Get invoice_date from form
                            invoice_date_str = request.form.get('invoice_date')
                            if invoice_date_str:
                                invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                            else:
                                invoice_date = datetime.now(timezone.utc)
                            
                            # Get branch_id from form
                            branch_id = request.form.get('branch_id')
                            
                            # Create invoice data
                            invoice_data = {
                                'hospital_id': current_user.hospital_id,
                                'branch_id': branch_id,
                                'patient_id': patient_id,
                                'invoice_date': invoice_date,
                                'line_items': processed_line_items,
                                'notes': request.form.get('notes', ''),
                                'current_user_id': current_user.user_id
                            }
                            
                            current_app.logger.info("Invoice Creation Request Received")
                            current_app.logger.info(f"Hospital ID: {invoice_data['hospital_id']}")
                            current_app.logger.info(f"Branch ID: {invoice_data['branch_id']}")
                            current_app.logger.info(f"Patient ID: {invoice_data['patient_id']}")
                            current_app.logger.info(f"Invoice Date: {invoice_data['invoice_date']}")
                            current_app.logger.info(f"Number of Line Items: {len(processed_line_items)}")
                            current_app.logger.info(f"Current User ID: {invoice_data['current_user_id']}")
                            
                            # Log details of each line item
                            for i, item in enumerate(processed_line_items, start=1):
                                current_app.logger.info(f"Line Item {i}: Type={item.get('item_type')}, ID={item.get('item_id')}, Name={item.get('item_name')}")
                            
                            # Create the invoice(s)
                            result = create_invoice(**invoice_data)
                            
                            # Single invoice case
                            if len(result['invoices']) == 1:
                                invoice = result['invoices'][0]
                                flash(f"Invoice {invoice['invoice_number']} created successfully", "success")
                                # Redirect to universal engine detail view
                                return redirect(url_for('universal_views.universal_detail_view',
                                                      entity_type='patient_invoices',
                                                      item_id=invoice['invoice_id']))

                            # Multiple invoices case (Phase 3 split invoices)
                            if len(result['invoices']) > 1:
                                parent_id = result.get('parent_invoice_id')
                                current_app.logger.info(f"Multiple invoices created. Parent ID from result: {parent_id}")

                                if not parent_id:
                                    # Fallback: Use first invoice ID as parent
                                    parent_id = result['invoices'][0].get('invoice_id')
                                    current_app.logger.warning(f"Parent invoice ID was None! Using first invoice ID: {parent_id}")

                                flash(f"✓ {len(result['invoices'])} consolidated invoices created successfully", "success")
                                # Redirect to consolidated invoice detail view (Universal Engine)
                                return redirect(url_for('universal_views.consolidated_invoice_detail_view',
                                                      parent_invoice_id=parent_id))
                        except Exception as e:
                            current_app.logger.error(f"Error creating invoice: {str(e)}")
                            flash(f"Error creating invoice: {str(e)}", "error")
                
                # Log form errors
                current_app.logger.error(f"Form validation failed with errors: \n{form.errors}")
            
            # Normal case or form validation failed
            can_edit_discount = current_user.has_permission('billing', 'edit_discount')
            return render_template(
                'billing/create_invoice.html',
                form=form,
                branches=branches,
                menu_items=menu_items,
                page_title="Create Invoice",
                auth_token=auth_token,  # Pass token to template
                user_batch_mode=user_batch_mode,
                error_data=error_data,  # Pass preserved data from failed submission
                can_edit_discount=can_edit_discount
            )

    # Check if user has permission to edit discount fields manually
    # Front desk users can only see auto-calculated discounts
    # Managers can manually edit discount fields
    can_edit_discount = current_user.has_permission('billing', 'edit_discount')

    return render_template(
        'billing/create_invoice.html',
        form=form,
        branches=branches,
        menu_items=menu_items,
        page_title="Create Invoice",
        auth_token=auth_token,  # Pass token to template
        user_batch_mode=user_batch_mode,  # Pass batch mode preference
        error_data=error_data,  # Pass preserved data from failed submission
        can_edit_discount=can_edit_discount  # Permission to manually edit discount fields
    )

@billing_views_bp.route('/list', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def invoice_list():
    """View list of invoices"""
    try:
        # Get filter parameters from query string
        filters = {}
        
        if request.args.get('invoice_number'):
            filters['invoice_number'] = request.args.get('invoice_number')
            
        if request.args.get('patient_id'):
            filters['patient_id'] = uuid.UUID(request.args.get('patient_id'))
            
        if request.args.get('invoice_type'):
            filters['invoice_type'] = request.args.get('invoice_type')
            
        if request.args.get('is_gst_invoice') is not None:
            filters['is_gst_invoice'] = request.args.get('is_gst_invoice') == 'true'
            
        if request.args.get('date_from'):
            date_from = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
            filters['date_from'] = date_from.replace(tzinfo=timezone.utc)
            
        if request.args.get('date_to'):
            date_to = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
            # Set time to end of day
            date_to = date_to.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            filters['date_to'] = date_to
            
        if request.args.get('payment_status'):
            filters['payment_status'] = request.args.get('payment_status')
        
        # Get page and page size
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        
        # Search invoices
        result = search_invoices(
            hospital_id=current_user.hospital_id,
            filters=filters,
            page=page,
            page_size=page_size
        )
        
        # Get menu items for dashboard
        menu_items = get_menu_items(current_user)
        
        # Check if we came from a create invoice with multiple invoices
        show_related = False
        if request.args.get('created_multiple') == 'true':
            show_related = True
            
        # Get patient name if filtering by patient_id
        patient_name = None
        if 'patient_id' in filters:
            try:
                with get_db_session() as db_session:
                    patient = db_session.query(Patient).filter_by(
                        hospital_id=current_user.hospital_id,
                        patient_id=filters['patient_id']
                    ).first()
                    
                    if patient:
                        # Access properties within session
                        patient_name = patient.full_name
            except Exception as e:
                logger.error(f"Error getting patient name: {str(e)}", exc_info=True)
        
        return render_template(
            'billing/invoice_list.html',
            invoices=result['items'],
            total=result['total'],
            page=result['page'],
            page_size=result['page_size'],
            pages=result['pages'],
            filters=request.args,
            menu_items=menu_items,
            page_title="Invoices",
            show_related=show_related,
            patient_name=patient_name
        )
    
    except Exception as e:
        flash(f'Error retrieving invoices: {str(e)}', 'error')
        logger.error(f"Error retrieving invoices: {str(e)}", exc_info=True)
        return render_template(
            'billing/invoice_list.html',
            invoices=[],
            menu_items=get_menu_items(current_user),
            page_title="Invoices"
        )

@billing_views_bp.route('/<uuid:invoice_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def view_invoice(invoice_id):
    """View invoice details with improved calculation of totals for multiple related invoices"""
    try:
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        
        # Log cancellation status for debugging
        logger.info(f"Invoice {invoice.get('invoice_number')} - is_cancelled: {invoice.get('is_cancelled', False)}")
        
        # Get patient details
        patient = None
        with get_db_session() as session:
            patient_record = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=invoice['patient_id']
            ).first()
            
            if patient_record:
                # Create detached copy before accessing properties
                patient_detached = get_detached_copy(patient_record)
                patient = {
                    'patient_id': str(patient_detached.patient_id),
                    'mrn': patient_detached.mrn,
                    'name': patient_detached.full_name,
                    'personal_info': patient_detached.personal_info,
                    'contact_info': patient_detached.contact_info
                }
        
        # Create payment form
        payment_form = PaymentForm()
        payment_form.invoice_id.data = str(invoice_id)
        
        # Get menu items for dashboard
        menu_items = get_menu_items(current_user)
        
        # Get related invoices if this is part of a multi-invoice creation
        related_invoices = []
        if invoice.get('created_at'):
            # Get invoices created around the same time for the same patient
            created_time = invoice.get('created_at')
            patient_id = invoice.get('patient_id')
            
            # Define a time window (e.g., 5 minutes)
            time_window = timedelta(minutes=5)
            
            with get_db_session() as session:
                related_records = session.query(InvoiceHeader).filter(
                    InvoiceHeader.hospital_id == current_user.hospital_id,
                    InvoiceHeader.patient_id == patient_id,
                    InvoiceHeader.created_at >= created_time - time_window,
                    InvoiceHeader.created_at <= created_time + time_window,
                    InvoiceHeader.invoice_id != invoice_id
                ).all()
                
                if related_records:
                    # Create detached copies
                    for related in related_records:
                        related_dict = get_detached_copy(related)
                        related_invoices.append({
                            'invoice_id': str(related_dict.invoice_id),
                            'invoice_number': related_dict.invoice_number,
                            'invoice_type': related_dict.invoice_type,
                            'is_gst_invoice': related_dict.is_gst_invoice,
                            'grand_total': related_dict.grand_total,
                            'balance_due': related_dict.balance_due,
                            'is_cancelled': related_dict.is_cancelled if hasattr(related_dict, 'is_cancelled') else False,
                            'cancellation_reason': related_dict.cancellation_reason if hasattr(related_dict, 'cancellation_reason') else None
                        })
        
        # Calculate totals for valid (non-cancelled) invoices only
        
        # First, determine if current invoice is cancelled
        current_invoice_cancelled = invoice.get('is_cancelled', False)
        
        # Initialize totals - only include current invoice if not cancelled
        if not current_invoice_cancelled:
            total_amount = float(invoice.get('grand_total', 0))
            total_balance_due = float(invoice.get('balance_due', 0))
        else:
            # Skip cancelled current invoice
            logger.info(f"Excluding cancelled current invoice {invoice.get('invoice_number')} from totals")
            total_amount = 0
            total_balance_due = 0
        
        # Log initial values
        logger.info(f"TOTALS: Starting with current invoice {invoice.get('invoice_number')}: "
                   f"is_cancelled={current_invoice_cancelled}, "
                   f"amount={total_amount}, balance={total_balance_due}")
        
        # Add totals from related invoices, excluding cancelled ones
        for i, related in enumerate(related_invoices):
            # Skip if invoice is cancelled
            if related.get('is_cancelled', False):
                logger.info(f"Excluding cancelled related invoice {related.get('invoice_number')} from totals")
                continue
                
            related_grand = 0
            related_balance = 0
            
            if 'grand_total' in related and related['grand_total'] is not None:
                related_grand = float(related['grand_total'])
                total_amount += related_grand
            
            if 'balance_due' in related and related['balance_due'] is not None:
                related_balance = float(related['balance_due'])
                total_balance_due += related_balance
            
            logger.info(f"TOTALS: Adding related invoice {related.get('invoice_number')}: "
                       f"amount={related_grand}, balance={related_balance}")
        
        # Calculate total paid amount as the difference
        total_paid_amount = total_amount - total_balance_due
        
        logger.info(f"TOTALS: Final calculations (excluding voided invoices): "
                   f"total_amount={total_amount}, "
                   f"total_paid_amount={total_paid_amount}, "
                   f"total_balance_due={total_balance_due}")
        
        # Get payments allocated to THIS specific invoice (from AR subledger)
        # This includes: regular payments, advance adjustments, and wallet redemptions
        invoice_payments = []
        try:
            with get_db_session() as session:
                from sqlalchemy import or_

                # Query 1: Regular payments with line item allocations
                regular_payment_entries = session.query(ARSubledger).filter(
                    ARSubledger.hospital_id == current_user.hospital_id,
                    ARSubledger.entry_type == 'payment',
                    ARSubledger.reference_type == 'payment',
                    ARSubledger.reference_line_item_id.in_(
                        session.query(InvoiceLineItem.line_item_id).filter(
                            InvoiceLineItem.invoice_id == invoice_id
                        ).subquery()
                    )
                ).all()

                # Query 2: Wallet payments (reference_id = invoice_id)
                wallet_payment_entries = session.query(ARSubledger).filter(
                    ARSubledger.hospital_id == current_user.hospital_id,
                    ARSubledger.entry_type == 'payment',
                    ARSubledger.reference_type == 'wallet_payment',
                    ARSubledger.reference_id == invoice_id
                ).all()

                # Query 3: Advance payments linked to this invoice via advance_adjustments
                from app.models.transaction import AdvanceAdjustment
                advance_payment_ids = session.query(AdvanceAdjustment.payment_id).filter(
                    AdvanceAdjustment.invoice_id == invoice_id,
                    AdvanceAdjustment.is_reversed == False
                ).subquery()

                advance_payment_entries = session.query(ARSubledger).filter(
                    ARSubledger.hospital_id == current_user.hospital_id,
                    ARSubledger.entry_type == 'payment',
                    ARSubledger.reference_type == 'payment',
                    ARSubledger.reference_id.in_(advance_payment_ids)
                ).all()

                # Combine all AR entries
                all_ar_entries = regular_payment_entries + wallet_payment_entries + advance_payment_entries

                # Group by payment and aggregate amounts
                payment_allocations = {}
                wallet_allocations = {}  # Separate tracking for wallet (reference_id = invoice_id)

                for ar_entry in all_ar_entries:
                    if ar_entry.reference_type == 'wallet_payment':
                        # For wallet payments, reference_id is invoice_id, not payment_id
                        wallet_key = f"wallet_{ar_entry.reference_id}"
                        if wallet_key not in wallet_allocations:
                            wallet_allocations[wallet_key] = {
                                'ar_entry': ar_entry,
                                'total_allocated': 0,
                                'invoice_id': ar_entry.reference_id
                            }
                        wallet_allocations[wallet_key]['total_allocated'] += float(ar_entry.credit_amount or 0)
                    else:
                        # Regular payments - reference_id is payment_id
                        payment_id = str(ar_entry.reference_id)
                        if payment_id not in payment_allocations:
                            payment_allocations[payment_id] = {
                                'ar_entry': ar_entry,
                                'total_allocated': 0
                            }
                        payment_allocations[payment_id]['total_allocated'] += float(ar_entry.credit_amount or 0)

                # Get full payment details for each unique payment
                for payment_id, alloc_data in payment_allocations.items():
                    try:
                        payment_record = session.query(PaymentDetail).filter_by(
                            hospital_id=current_user.hospital_id,
                            payment_id=uuid.UUID(payment_id)
                        ).first()

                        if payment_record:
                            payment_copy = get_detached_copy(payment_record)
                            payment_copy.allocated_to_invoice = alloc_data['total_allocated']
                            invoice_payments.append(payment_copy)
                    except Exception as e:
                        logger.warning(f"Could not get payment {payment_id}: {str(e)}")

                # Add wallet payments as synthetic payment entries for display
                for wallet_key, alloc_data in wallet_allocations.items():
                    # Create a synthetic object for wallet payment display
                    class WalletPaymentDisplay:
                        pass

                    wallet_display = WalletPaymentDisplay()
                    wallet_display.payment_id = None
                    wallet_display.payment_date = alloc_data['ar_entry'].transaction_date
                    wallet_display.total_amount = Decimal('0')
                    wallet_display.wallet_points_amount = Decimal(str(alloc_data['total_allocated']))
                    wallet_display.advance_adjustment_amount = Decimal('0')
                    wallet_display.cash_amount = Decimal('0')
                    wallet_display.credit_card_amount = Decimal('0')
                    wallet_display.debit_card_amount = Decimal('0')
                    wallet_display.upi_amount = Decimal('0')
                    wallet_display.allocated_to_invoice = alloc_data['total_allocated']
                    wallet_display.reference_number = alloc_data['ar_entry'].reference_number
                    wallet_display.payment_source = 'wallet_redemption'
                    invoice_payments.append(wallet_display)

                logger.info(f"Found {len(invoice_payments)} payments for invoice {invoice_id}")

        except Exception as e:
            logger.error(f"Error getting invoice payments from AR subledger: {str(e)}", exc_info=True)

        # Get ALL payments made by this patient (payment history)
        all_patient_payments = []
        try:
            with get_db_session() as session:
                payment_records = session.query(PaymentDetail).filter(
                    PaymentDetail.hospital_id == current_user.hospital_id,
                    PaymentDetail.patient_id == invoice['patient_id']
                ).order_by(PaymentDetail.payment_date.desc()).all()

                all_patient_payments = [get_detached_copy(payment) for payment in payment_records]
        except Exception as e:
            logger.error(f"Error getting patient payment history: {str(e)}", exc_info=True)
        
        # Make sure values are properly converted to float for the template - create new variables to avoid any reference issues
        final_total_amount = float(total_amount)
        final_total_balance_due = float(total_balance_due)
        final_total_paid_amount = float(total_paid_amount)

        # Add payments allocated to THIS invoice
        invoice['payments'] = invoice_payments

        return render_template(
            'billing/view_invoice.html',
            invoice=invoice,
            patient=patient,
            payment_form=payment_form,
            menu_items=menu_items,
            page_title=f"Invoice #{invoice['invoice_number']}",
            is_consolidated_prescription=invoice.get('is_consolidated_prescription', False),
            related_invoices=related_invoices,
            invoice_payments=invoice_payments,  # Payments allocated to this invoice
            all_patient_payments=all_patient_payments,  # All patient payments (history)

            # Pass explicit total values
            total_amount=final_total_amount,
            total_balance_due=final_total_balance_due,
            total_paid_amount=final_total_paid_amount
        )
    
    except Exception as e:
        flash(f'Error retrieving invoice: {str(e)}', 'error')
        logger.error(f"Error retrieving invoice: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))


# Identify and fix the redirect loop in record_invoice_payment function in billing_views.py
# Focus on the pay_all handling section (around line 580)

@billing_views_bp.route('/payment/new', methods=['GET'])
@login_required
@permission_required('billing', 'create')
def new_payment():
    """
    Generic payment screen with patient selection
    User selects patient first, then proceeds to payment with all outstanding invoices
    """
    try:
        # Just render the patient selection screen
        return render_template(
            'billing/payment_patient_selection.html',
            title='Record New Payment'
        )
    except Exception as e:
        flash(f'Error loading payment screen: {str(e)}', 'error')
        logger.error(f"Error in new_payment: {str(e)}", exc_info=True)
        return redirect(url_for('auth_views.dashboard'))


# Alias route for menu compatibility
@billing_views_bp.route('/payment/patient-selection', methods=['GET'])
@login_required
@permission_required('billing', 'create')
def payment_patient_selection():
    """Alias for new_payment - for menu compatibility"""
    return new_payment()


@billing_views_bp.route('/<uuid:invoice_id>/payment', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'update')
def record_invoice_payment(invoice_id):
    """Record payment for an invoice"""
    try:
        # Check if this is a multi-invoice payment
        pay_all = request.args.get('pay_all') == 'true'
        
        logger.info(f"record_invoice_payment - invoice_id: {invoice_id}, pay_all: {pay_all}")

        # Check if using advance payment
        if request.method == 'POST' and request.form.get('use_advance') == 'true':
            advance_amount = Decimal(request.form.get('advance_amount', '0'))
            
            if advance_amount > 0:
                try:
                    # Check if apply to multiple invoices
                    apply_to_multiple = request.form.get('apply_to_multiple') == 'true'
                    selected_invoice_ids = request.form.getlist('invoice_ids')
                    
                    if apply_to_multiple and selected_invoice_ids:
                        # Apply to multiple invoices
                        logger.info(f"Applying advance payment to multiple invoices: {selected_invoice_ids}")
                        
                        # Sort invoices by date (oldest first)
                        invoices_to_process = []
                        remaining_amount = advance_amount
                        total_applied = Decimal('0')
                        invoices_updated = []
                        
                        with get_db_session() as session:
                            # Get invoice details for sorting
                            for inv_id_str in selected_invoice_ids:
                                try:
                                    inv_id = uuid.UUID(inv_id_str)
                                    invoice = session.query(InvoiceHeader).filter_by(
                                        hospital_id=current_user.hospital_id,
                                        invoice_id=inv_id
                                    ).first()
                                    
                                    if invoice and invoice.balance_due > 0:
                                        invoices_to_process.append({
                                            'invoice_id': invoice.invoice_id,
                                            'invoice_number': invoice.invoice_number,
                                            'balance_due': invoice.balance_due,
                                            'invoice_date': invoice.invoice_date
                                        })
                                except Exception as e:
                                    logger.warning(f"Error processing invoice ID {inv_id_str}: {str(e)}")
                        
                        # Sort by date (oldest first)
                        invoices_to_process.sort(key=lambda x: x.get('invoice_date', datetime.now(timezone.utc)))
                        
                        # Apply advance to each invoice
                        for inv in invoices_to_process:
                            if remaining_amount <= 0:
                                break
                                
                            amount_to_apply = min(remaining_amount, inv['balance_due'])
                            
                            if amount_to_apply > 0:
                                try:
                                    # Apply advance payment
                                    adjustment = apply_advance_payment(
                                        hospital_id=current_user.hospital_id,
                                        invoice_id=inv['invoice_id'],
                                        amount=amount_to_apply,
                                        adjustment_date=datetime.now(timezone.utc),
                                        notes=f"Applied from payment form (multi-invoice)",
                                        current_user_id=current_user.user_id
                                    )
                                    
                                    # Update totals
                                    remaining_amount -= amount_to_apply
                                    total_applied += amount_to_apply
                                    invoices_updated.append(inv['invoice_number'])
                                    
                                    logger.info(f"Applied {amount_to_apply} to invoice {inv['invoice_number']}")
                                except Exception as e:
                                    logger.error(f"Error applying advance to invoice {inv['invoice_number']}: {str(e)}")
                        
                        # Notify user
                        if total_applied > 0:
                            flash(f"Successfully applied {total_applied} from advance payment to {len(invoices_updated)} invoice(s)", "success")
                        else:
                            flash(f"No advance payment was applied", "warning")
                            
                        return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
                    else:
                        # Apply to single invoice (original behavior)
                        # Get invoice first to check balance due
                        invoice = get_invoice_by_id(
                            hospital_id=current_user.hospital_id,
                            invoice_id=invoice_id
                        )
                        
                        # Check if the invoice already has a zero balance
                        if invoice['balance_due'] <= 0:
                            flash(f"This invoice has already been fully paid. No payment needed.", "warning")
                            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
                        
                        # If advance amount exceeds balance due, adjust it
                        if advance_amount > invoice['balance_due']:
                            advance_amount = Decimal(invoice['balance_due'])
                        
                        # Apply advance payment
                        adjustment = apply_advance_payment(
                            hospital_id=current_user.hospital_id,
                            invoice_id=invoice_id,
                            amount=advance_amount,
                            adjustment_date=datetime.now(timezone.utc),
                            notes="Applied from payment form",
                            current_user_id=current_user.user_id
                        )
                        
                        flash(f"Successfully applied {advance_amount} from advance payment", "success")
                        
                        # Check if there's still balance due
                        updated_invoice = get_invoice_by_id(
                            hospital_id=current_user.hospital_id,
                            invoice_id=invoice_id
                        )
                        
                        if updated_invoice['balance_due'] <= 0:
                            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
                            
                        # If there's still balance due, continue with payment form
                        return redirect(url_for('billing_views.record_invoice_payment', invoice_id=invoice_id))
                except ValueError as e:
                    # Handle specifically the balance exceeded error
                    if "exceeds invoice balance due" in str(e):
                        flash(f"Cannot apply payment: This invoice has already been fully paid", "warning")
                    else:
                        flash(f"Error applying advance payment: {str(e)}", "error")
                    logger.error(f"Error applying advance payment: {str(e)}", exc_info=True)
                except Exception as e:
                    flash(f"Error applying advance payment: {str(e)}", "error")
                    logger.error(f"Error applying advance payment: {str(e)}", exc_info=True)
            
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        
        # Use the controller for the standard payment form
        logger.info("Creating PaymentFormController")
        controller = PaymentFormController()
        logger.info("Calling controller.handle_request")
        return controller.handle_request(invoice_id=invoice_id, pay_all=pay_all)
        
    except Exception as e:
        flash(f'Error processing payment: {str(e)}', 'error')
        logger.error(f"Error processing payment: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))

@billing_views_bp.route('/invoice/<uuid:invoice_id>/void', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'update')
def void_invoice_view(invoice_id):
    """Void an invoice"""
    try:
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        
        # Check if invoice can be voided (has no payments)
        if invoice['paid_amount'] > 0:
            flash('This invoice cannot be voided as it already has payments recorded.', 'error')
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        
        # Get patient details
        patient = None
        with get_db_session() as session:
            patient_record = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=invoice['patient_id']
            ).first()
            
            if patient_record:
                patient_detached = get_detached_copy(patient_record)
                patient = {
                    'patient_id': str(patient_detached.patient_id),
                    'mrn': patient_detached.mrn,
                    'name': patient_detached.full_name,
                    'personal_info': patient_detached.personal_info,
                    'contact_info': patient_detached.contact_info
                }
        
        # Handle GET request - display the form
        if request.method == 'GET':
            # Get menu items for dashboard
            menu_items = get_menu_items(current_user)
            
            return render_template(
                'billing/void_form.html',
                invoice=invoice,
                patient=patient,
                menu_items=menu_items,
                page_title=f"Void Invoice #{invoice['invoice_number']}"
            )
            
        # Handle POST request - process the form
        elif request.method == 'POST':
            # Get reason from form
            reason = request.form.get('reason')
            
            if not reason:
                flash('Reason for voiding is required.', 'error')
                return redirect(url_for('billing_views.void_invoice_view', invoice_id=invoice_id))
            
            try:
                # Call the service to void the invoice
                result = void_invoice(
                    hospital_id=current_user.hospital_id,
                    invoice_id=invoice_id,
                    reason=reason,
                    # user_id=current_user.user_id 
                )
                
                if result:
                    flash('Invoice voided successfully.', 'success')
                    return redirect(url_for('billing_views.invoice_list'))
                else:
                    flash('Failed to void invoice.', 'error')
                    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
            
            except Exception as e:
                flash(f'Error voiding invoice: {str(e)}', 'error')
                logger.error(f"Error voiding invoice: {str(e)}", exc_info=True)
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
    
    except Exception as e:
        flash(f'Error processing void request: {str(e)}', 'error')
        logger.error(f"Error processing void request: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))

@billing_views_bp.route('/<uuid:invoice_id>/payment-enhanced', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'create')
def record_invoice_payment_enhanced(invoice_id):
    """
    Enhanced payment form with FIFO allocation, advance usage, and package installments
    Handles multi-invoice payments with user-configurable allocation
    """
    logger.info(f"🔴 record_invoice_payment_enhanced called - Method: {request.method}, Invoice: {invoice_id}")
    try:
        if request.method == 'GET':
            logger.info(f"📖 GET request - Loading payment form for invoice {invoice_id}")
            # Display enhanced payment form
            from app.services.billing_service import get_invoice_by_id, get_patient_advance_balance

            # Get invoice details
            invoice = get_invoice_by_id(
                hospital_id=current_user.hospital_id,
                invoice_id=invoice_id
            )

            if not invoice:
                flash('Invoice not found', 'error')
                return redirect(url_for('universal_views.universal_list_view', entity_type='patient_invoices'))

            # Get patient details
            with get_db_session() as session:
                from app.models.master import Patient
                patient = session.query(Patient).filter_by(
                    hospital_id=current_user.hospital_id,
                    patient_id=invoice['patient_id']
                ).first()

                if not patient:
                    flash('Patient not found', 'error')
                    return redirect(url_for('universal_views.universal_list_view', entity_type='patient_invoices'))

                patient_dict = get_entity_dict(patient)

            # Get wallet info for payment page
            wallet_info = None
            if invoice.get('patient_id'):
                try:
                    from app.services.wallet_service import WalletService
                    wallet_data = WalletService.get_available_balance(
                        patient_id=str(invoice['patient_id']),
                        hospital_id=str(current_user.hospital_id)
                    )
                    if wallet_data and wallet_data.get('points_balance', 0) > 0:
                        wallet_balance = wallet_data['points_balance']
                        wallet_info = {
                            'points': wallet_balance,
                            'value': wallet_balance,  # 1:1 ratio
                            'tier': wallet_data.get('tier_name', 'Member'),
                            'tier_code': wallet_data.get('tier_code', ''),
                            'discount_percent': wallet_data.get('tier_discount_percent', 0),
                            'wallet_id': wallet_data.get('wallet_id')
                        }
                        logger.info(f"Wallet found for patient: {wallet_balance} points ({wallet_info['tier']})")
                except Exception as e:
                    logger.warning(f"Could not fetch wallet for patient {invoice['patient_id']}: {str(e)}")

            # Get approval threshold
            approval_threshold = float(current_app.config.get('APPROVAL_THRESHOLD_L1', '100000.00'))

            # Get total outstanding for the patient (for wallet redemption display)
            total_outstanding = Decimal('0')
            try:
                with get_db_session() as session:
                    from sqlalchemy import func
                    # InvoiceHeader already imported at module level - do not re-import locally
                    result = session.query(func.sum(InvoiceHeader.balance_due)).filter(
                        InvoiceHeader.hospital_id == current_user.hospital_id,
                        InvoiceHeader.patient_id == invoice['patient_id'],
                        InvoiceHeader.balance_due > 0
                    ).scalar()
                    total_outstanding = Decimal(str(result or 0))
            except Exception as e:
                logger.warning(f"Could not calculate total outstanding: {str(e)}")
                total_outstanding = Decimal(str(invoice.get('balance_due', 0)))

            # Render enhanced payment form
            return render_template(
                'billing/payment_form_enhanced.html',
                invoice=invoice,
                patient=patient_dict,
                wallet_info=wallet_info,
                approval_threshold=approval_threshold,
                total_outstanding=float(total_outstanding),
                menu_items=get_menu_items(current_user)
            )

        else:  # POST - Process payment
            logger.info("=" * 80)
            logger.info(f"🔵 PAYMENT FORM SUBMITTED - Invoice ID: {invoice_id}")
            logger.info(f"🔵 Request method: {request.method}")
            logger.info(f"🔵 Form data keys: {list(request.form.keys())}")
            logger.info("=" * 80)

            # Get invoice to extract patient_id for redirect after payment
            from app.services.billing_service import get_invoice_by_id
            invoice_for_redirect = get_invoice_by_id(
                hospital_id=current_user.hospital_id,
                invoice_id=invoice_id
            )
            patient_id_for_redirect = invoice_for_redirect.get('patient_id') if invoice_for_redirect else None

            # Helper function to safely convert to Decimal
            def safe_decimal(value, default='0'):
                """Convert value to Decimal, handling empty strings and None"""
                if not value or value == '':
                    return Decimal(default)
                try:
                    return Decimal(str(value).strip())
                except (InvalidOperation, ValueError, decimal.ConversionSyntax):
                    return Decimal(default)

            # Get form data
            payment_date = request.form.get('payment_date')
            logger.info(f"📅 Payment date: {payment_date}")
            cash_amount = safe_decimal(request.form.get('cash_amount'))
            credit_card_amount = safe_decimal(request.form.get('credit_card_amount'))
            debit_card_amount = safe_decimal(request.form.get('debit_card_amount'))
            upi_amount = safe_decimal(request.form.get('upi_amount'))
            advance_amount = safe_decimal(request.form.get('advance_amount'))
            wallet_points_amount = safe_decimal(request.form.get('wallet_points_amount'))

            logger.info(f"💵 Cash: ₹{cash_amount}, Card: ₹{credit_card_amount}, Debit: ₹{debit_card_amount}, UPI: ₹{upi_amount}, Advance: ₹{advance_amount}, Wallet: {wallet_points_amount} points")

            card_number_last4 = request.form.get('card_number_last4')
            card_type = request.form.get('card_type')
            upi_id = request.form.get('upi_id')
            reference_number = request.form.get('reference_number')

            save_as_draft = request.form.get('save_as_draft') == 'true'

            # Calculate total payment (cash/card/upi only - wallet tracked separately)
            total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount
            # Total payment including wallet points (for validation and record creation)
            total_payment_with_wallet = total_payment + wallet_points_amount

            logger.info(f"💰 Total payment: ₹{total_payment}, Wallet: ₹{wallet_points_amount}, Combined: ₹{total_payment_with_wallet}, Save as draft: {save_as_draft}")

            if total_payment == 0 and advance_amount == 0 and wallet_points_amount == 0:
                logger.warning("❌ No payment amount entered")
                flash('Please enter a payment amount', 'error')
                return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))

            # Get invoice allocations from form
            invoice_allocations = {}
            for key in request.form.keys():
                if key.startswith('invoice_allocations['):
                    # Extract invoice_id from key like "invoice_allocations[uuid]"
                    inv_id = key.split('[')[1].split(']')[0]
                    amount = safe_decimal(request.form.get(key))
                    if amount > 0:
                        invoice_allocations[inv_id] = float(amount)

            # Get installment allocations from form
            installment_allocations = {}
            for key in request.form.keys():
                if key.startswith('installment_allocations['):
                    # Extract installment_id from key
                    inst_id = key.split('[')[1].split(']')[0]
                    amount = safe_decimal(request.form.get(key))
                    if amount > 0:
                        installment_allocations[inst_id] = float(amount)

            # If no specific allocations provided, allocate to current invoice
            if not invoice_allocations and not installment_allocations:
                invoice_allocations[str(invoice_id)] = float(total_payment + advance_amount + wallet_points_amount)

            logger.info(f"📋 Invoice allocations: {invoice_allocations}")
            logger.info(f"📦 Installment allocations: {installment_allocations}")

            # Get approval threshold
            approval_threshold = Decimal(str(current_app.config.get('APPROVAL_THRESHOLD_L1', '100000.00')))

            # Process payment using enhanced service
            from app.services.billing_service import record_multi_invoice_payment, apply_advance_payment

            try:
                # Parse date from form and combine with current time for accurate timestamp
                if payment_date:
                    payment_date_parsed = datetime.strptime(payment_date, '%Y-%m-%d')
                    # Combine user-selected date with current time
                    now = datetime.now()
                    payment_date_obj = payment_date_parsed.replace(
                        hour=now.hour, minute=now.minute, second=now.second, microsecond=now.microsecond
                    )
                else:
                    payment_date_obj = datetime.now()

                # Initialize payment_id tracking
                last_payment_id = None

                # ========================================================================
                # FIFO PAYMENT ALLOCATION: Apply payments to oldest invoices first
                # Priority: 1. Advance  2. Wallet  3. Cash/Card/UPI
                # ========================================================================

                # Track amounts applied to each invoice
                advance_portions_applied = {}
                wallet_portions_applied = {}
                cash_card_portions_applied = {}
                wallet_transaction_id_for_payment = None

                # Get invoice details with balance_due, sorted by invoice_date (FIFO)
                with get_db_session() as session:
                    invoice_ids = [uuid.UUID(inv_id) for inv_id in invoice_allocations.keys()]

                    invoices_query = session.query(InvoiceHeader).filter(
                        InvoiceHeader.hospital_id == current_user.hospital_id,
                        InvoiceHeader.invoice_id.in_(invoice_ids)
                    ).order_by(InvoiceHeader.invoice_date.asc()).all()  # FIFO: oldest first

                    # Build list of invoices with their current balance
                    fifo_invoices = []
                    for inv in invoices_query:
                        fifo_invoices.append({
                            'invoice_id': str(inv.invoice_id),
                            'invoice_number': inv.invoice_number,
                            'invoice_date': inv.invoice_date,
                            'balance_due': Decimal(str(inv.balance_due or 0)),
                            'patient_id': inv.patient_id
                        })

                    logger.info(f"📋 FIFO Invoice Order: {[(inv['invoice_number'], float(inv['balance_due'])) for inv in fifo_invoices]}")

                # Remaining amounts to allocate
                remaining_advance = advance_amount
                remaining_wallet = wallet_points_amount
                remaining_cash_card = total_payment  # cash + card + upi

                # ========================================================================
                # STEP 1: Apply payments in FIFO order with payment method priority
                # ========================================================================
                for inv_data in fifo_invoices:
                    inv_id_str = inv_data['invoice_id']
                    inv_uuid = uuid.UUID(inv_id_str)
                    inv_number = inv_data['invoice_number']
                    inv_balance = inv_data['balance_due']

                    if inv_balance <= 0:
                        logger.info(f"⏭️ Skipping {inv_number} - already paid (balance: ₹{inv_balance})")
                        continue

                    logger.info(f"💳 Processing {inv_number} (balance: ₹{inv_balance})")

                    remaining_invoice_balance = inv_balance

                    # ----- PRIORITY 1: Apply ADVANCE first -----
                    if remaining_advance > 0 and remaining_invoice_balance > 0:
                        advance_to_apply = min(remaining_advance, remaining_invoice_balance)

                        try:
                            apply_advance_payment(
                                hospital_id=current_user.hospital_id,
                                invoice_id=inv_uuid,
                                amount=advance_to_apply,
                                adjustment_date=payment_date_obj,
                                notes="Applied from FIFO payment",
                                current_user_id=current_user.user_id
                            )

                            advance_portions_applied[inv_id_str] = advance_to_apply
                            remaining_advance -= advance_to_apply
                            remaining_invoice_balance -= advance_to_apply

                            logger.info(f"  ✓ Advance: ₹{advance_to_apply} applied to {inv_number} (remaining advance: ₹{remaining_advance})")

                        except Exception as e:
                            logger.error(f"Error applying advance payment: {str(e)}")
                            flash(f'Error applying advance payment: {str(e)}', 'error')
                            return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))

                    # ----- PRIORITY 2: Apply WALLET second -----
                    if remaining_wallet > 0 and remaining_invoice_balance > 0:
                        wallet_to_apply = min(remaining_wallet, remaining_invoice_balance)

                        if not patient_id_for_redirect:
                            flash('Cannot redeem wallet points - invoice has no patient', 'error')
                            return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))

                        try:
                            from app.services.wallet_service import WalletService
                            redemption_result = WalletService.redeem_points(
                                patient_id=str(patient_id_for_redirect),
                                points_amount=int(wallet_to_apply),
                                invoice_id=inv_id_str,
                                invoice_number=inv_number,
                                user_id=str(current_user.user_id)
                            )

                            if not redemption_result['success']:
                                raise ValueError(f"Wallet redemption failed: {redemption_result['message']}")

                            wallet_transaction_id = redemption_result['transaction_id']
                            wallet_transaction_id_for_payment = wallet_transaction_id

                            # Create GL entries for wallet redemption
                            from app.services.wallet_gl_service import WalletGLService
                            WalletGLService.create_wallet_redemption_gl_entries(
                                wallet_transaction_id=wallet_transaction_id,
                                current_user_id=current_user.user_id
                            )

                            wallet_portions_applied[inv_id_str] = Decimal(str(wallet_to_apply))
                            remaining_wallet -= wallet_to_apply
                            remaining_invoice_balance -= wallet_to_apply

                            logger.info(f"  ✓ Wallet: ₹{wallet_to_apply} applied to {inv_number} (remaining wallet: ₹{remaining_wallet})")

                        except Exception as e:
                            logger.error(f"Error redeeming wallet points: {str(e)}")
                            flash(f'Error redeeming wallet points: {str(e)}', 'error')
                            return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))

                    # ----- PRIORITY 3: Apply CASH/CARD/UPI last -----
                    if remaining_cash_card > 0 and remaining_invoice_balance > 0:
                        cash_card_to_apply = min(remaining_cash_card, remaining_invoice_balance)

                        cash_card_portions_applied[inv_id_str] = cash_card_to_apply
                        remaining_cash_card -= cash_card_to_apply
                        remaining_invoice_balance -= cash_card_to_apply

                        logger.info(f"  ✓ Cash/Card: ₹{cash_card_to_apply} allocated to {inv_number} (remaining: ₹{remaining_cash_card})")

                    # Log final status for this invoice
                    total_applied = (
                        advance_portions_applied.get(inv_id_str, Decimal('0')) +
                        wallet_portions_applied.get(inv_id_str, Decimal('0')) +
                        cash_card_portions_applied.get(inv_id_str, Decimal('0'))
                    )
                    logger.info(f"  📊 {inv_number}: Total ₹{total_applied} applied (Adv: ₹{advance_portions_applied.get(inv_id_str, 0)}, Wallet: ₹{wallet_portions_applied.get(inv_id_str, 0)}, Cash/Card: ₹{cash_card_portions_applied.get(inv_id_str, 0)})")

                # Log any remaining unallocated amounts
                if remaining_advance > 0:
                    logger.warning(f"⚠️ Unallocated advance: ₹{remaining_advance}")
                if remaining_wallet > 0:
                    logger.warning(f"⚠️ Unallocated wallet: ₹{remaining_wallet}")
                if remaining_cash_card > 0:
                    logger.warning(f"⚠️ Unallocated cash/card: ₹{remaining_cash_card}")

                # ========================================================================
                # Build final invoice_allocations for cash/card payment recording
                # ========================================================================
                # Only include invoices that have cash/card allocation (advance/wallet handled separately)
                invoice_allocations = {k: v for k, v in cash_card_portions_applied.items() if v > 0}
                original_invoice_allocations = dict(invoice_allocations)  # For compatibility

                logger.info(f"📋 Final cash/card allocations for payment record: {[(k[:8], float(v)) for k, v in invoice_allocations.items()]}")

                # Calculate ACTUALLY applied amounts (not requested amounts)
                total_advance_applied = sum(advance_portions_applied.values()) if advance_portions_applied else Decimal('0')
                total_wallet_applied = sum(wallet_portions_applied.values()) if wallet_portions_applied else Decimal('0')
                total_cash_card_applied = sum(cash_card_portions_applied.values()) if cash_card_portions_applied else Decimal('0')

                logger.info(f"📊 FIFO Allocation Summary: Advance ₹{total_advance_applied}, Wallet ₹{total_wallet_applied}, Cash/Card ₹{total_cash_card_applied}")

                # ========================================================================
                # STEP 2: Record cash/card payment (if any)
                # ========================================================================
                # Advance and Wallet are already recorded via their respective functions
                # Now record the cash/card/upi payment if any was allocated

                # Check if ANY payment was made
                total_all_methods = total_advance_applied + total_wallet_applied + total_cash_card_applied

                if total_all_methods == 0:
                    # No payment was actually allocated (shouldn't happen, but handle gracefully)
                    flash('No payment was allocated to any invoice', 'warning')
                    return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))

                elif total_cash_card_applied == 0:
                    # Payment was ENTIRELY via advance and/or wallet
                    # These are already committed in their respective functions
                    logger.info(f"✅ Payment completed via Advance (₹{total_advance_applied}) + Wallet (₹{total_wallet_applied}) only - no cash/card")
                    # Fall through to success message

                elif total_cash_card_applied > 0:
                    logger.info(f"💰 Recording cash/card payment: ₹{total_cash_card_applied}")

                    # Build invoice_allocations list for cash/card portion only
                    invoice_alloc_list = []
                    for inv_id_str, allocated_amount in cash_card_portions_applied.items():
                        if allocated_amount > 0:
                            invoice_alloc_list.append({
                                'invoice_id': inv_id_str,
                                'allocated_amount': Decimal(str(allocated_amount))
                            })

                    # ========================================================================
                    # ✅ CRITICAL FIX: Use SINGLE session for entire payment operation
                    # This ensures atomicity - either ALL succeeds or ALL rolls back
                    # ========================================================================

                    try:
                        with get_db_session() as session:
                            # SCENARIO 1: Payment has invoice allocations
                            if invoice_alloc_list:
                                logger.info(f"📋 Recording payment for {len(invoice_alloc_list)} invoices with allocations: {[(i['invoice_id'][:8], float(i['allocated_amount'])) for i in invoice_alloc_list]}")

                                # ✅ Check if user confirmed overpayment (if needed)
                                allow_overpayment = request.form.get('allow_overpayment') == 'true'

                                # NOTE: Advance payments are already recorded separately by apply_advance_payment()
                                # which creates its own PaymentDetail record. Do NOT pass advance_adjustment_amount
                                # to avoid duplicate recording.

                                # ✅ Call record_multi_invoice_payment with shared session
                                # Pass TOTAL payment amounts - function will allocate to line items
                                result = record_multi_invoice_payment(
                                    hospital_id=current_user.hospital_id,
                                    invoice_allocations=invoice_alloc_list,
                                    payment_date=payment_date_obj,
                                    cash_amount=cash_amount,
                                    credit_card_amount=credit_card_amount,
                                    debit_card_amount=debit_card_amount,
                                    upi_amount=upi_amount,
                                    card_number_last4=card_number_last4,
                                    card_type=card_type,
                                    upi_id=upi_id,
                                    reference_number=reference_number,
                                    recorded_by=current_user.user_id,
                                    save_as_draft=save_as_draft,
                                    approval_threshold=approval_threshold,
                                    allow_overpayment=allow_overpayment,  # ✅ NEW: Pass overpayment confirmation
                                    wallet_points_amount=total_wallet_applied,  # ✅ Actually applied wallet points
                                    wallet_transaction_id=wallet_transaction_id_for_payment,  # ✅ Wallet transaction ID
                                    advance_adjustment_amount=Decimal('0'),  # ✅ Advance already recorded separately
                                    session=session  # ✅ Pass shared session
                                )

                                # ✅ Check if overpayment confirmation required
                                if result.get('requires_confirmation'):
                                    # Don't commit - return warning to user
                                    session.rollback()
                                    logger.warning("⚠️ Overpayment detected - requiring user confirmation")

                                    # Return JSON with warnings for AJAX handling
                                    return jsonify({
                                        'success': False,
                                        'requires_confirmation': True,
                                        'error': result.get('error'),
                                        'message': result.get('message'),
                                        'overpayment_warnings': result.get('overpayment_warnings', [])
                                    }), 400

                                # Track the payment_id for installment payments
                                if result and result.get('success') and 'payment_id' in result:
                                    last_payment_id = result['payment_id']
                                    logger.info(f"✓ Created multi-invoice payment {last_payment_id} for ₹{total_payment}")
                                elif result and not result.get('success'):
                                    # Payment creation failed for other reasons
                                    raise ValueError(result.get('error', 'Payment creation failed'))

                            # SCENARIO 2: Payment has ONLY installment allocations (no invoices)
                            elif installment_allocations:
                                logger.info(f"📦 Package-only payment: Treating as payment against package invoice")

                                # Get the plan's invoice and create invoice allocation
                                first_installment_id = list(installment_allocations.keys())[0]
                                from app.models.transaction import InstallmentPayment, PackagePaymentPlan

                                installment = session.query(InstallmentPayment).filter(
                                    InstallmentPayment.installment_id == first_installment_id
                                ).first()

                                if not installment:
                                    raise ValueError(f"Installment {first_installment_id} not found")

                                plan = session.query(PackagePaymentPlan).filter(
                                    PackagePaymentPlan.plan_id == installment.plan_id
                                ).first()

                                if not plan:
                                    raise ValueError(f"Payment plan for installment {first_installment_id} not found")

                                if not plan.invoice_id:
                                    raise ValueError(f"Payment plan {plan.plan_id} is not linked to an invoice")

                                # ✅ Build invoice allocation list using the plan's invoice
                                invoice_alloc_list = [{
                                    'invoice_id': str(plan.invoice_id),
                                    'allocated_amount': total_payment
                                }]

                                logger.info(f"📋 Package installment payment treated as invoice payment to {plan.invoice_id}")

                                # ✅ For package installment payments, automatically allow overpayment
                                # The invoice might already be paid by other installments, and this payment
                                # should be recorded as advance against the patient's account
                                allow_overpayment = True
                                logger.info("📦 Package installment payment: Auto-allowing overpayment (will record as advance if invoice paid)")

                                # ✅ Call record_multi_invoice_payment with the package invoice
                                # NOTE: Advance already recorded separately by apply_advance_payment()
                                result = record_multi_invoice_payment(
                                    hospital_id=current_user.hospital_id,
                                    invoice_allocations=invoice_alloc_list,
                                    payment_date=payment_date_obj,
                                    cash_amount=cash_amount,
                                    credit_card_amount=credit_card_amount,
                                    debit_card_amount=debit_card_amount,
                                    upi_amount=upi_amount,
                                    card_number_last4=card_number_last4,
                                    card_type=card_type,
                                    upi_id=upi_id,
                                    reference_number=reference_number,
                                    recorded_by=current_user.user_id,
                                    save_as_draft=save_as_draft,
                                    approval_threshold=approval_threshold,
                                    allow_overpayment=allow_overpayment,  # ✅ NEW: Pass overpayment confirmation
                                    wallet_points_amount=total_wallet_applied,  # ✅ Actually applied wallet points
                                    wallet_transaction_id=wallet_transaction_id_for_payment,  # ✅ Wallet transaction ID
                                    advance_adjustment_amount=Decimal('0'),  # ✅ Advance already recorded separately
                                    session=session  # ✅ Pass shared session
                                )

                                # Track the payment_id for installment payments
                                if result and result.get('success') and 'payment_id' in result:
                                    last_payment_id = result['payment_id']
                                    logger.info(f"✓ Created package invoice payment {last_payment_id} for ₹{total_cash_card_applied}")
                                elif result and not result.get('success'):
                                    # Payment creation failed for other reasons
                                    raise ValueError(result.get('error', 'Package payment creation failed'))

                            # Handle package installments if any (using the SAME session)
                            if installment_allocations and last_payment_id:
                                from app.services.package_payment_service import PackagePaymentService
                                package_service = PackagePaymentService()

                                logger.info(f"📦 Processing {len(installment_allocations)} installment allocation(s)")

                                for installment_id, amount in installment_allocations.items():
                                    installment_result = package_service.record_installment_payment(
                                        installment_id=installment_id,
                                        paid_amount=amount,
                                        payment_id=last_payment_id,
                                        hospital_id=current_user.hospital_id,
                                        session=session  # ✅ Pass shared session
                                    )

                                    if not installment_result['success']:
                                        # Raise exception to trigger rollback
                                        raise ValueError(f"Failed to record installment payment: {installment_result.get('error')}")
                                    else:
                                        logger.info(f"✓ Recorded payment of ₹{amount} for installment {installment_id}, status: {installment_result.get('new_status')}")

                            # ✅ COMMIT TRANSACTION - All operations succeeded
                            session.commit()
                            logger.info("✅ All payment operations committed successfully")

                            # Invalidate cache after successful commit
                            try:
                                from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                                invalidate_service_cache_for_entity('patient_payment_receipts', cascade=False)
                                if installment_allocations:
                                    invalidate_service_cache_for_entity('package_payment_plans', cascade=False)
                                    invalidate_service_cache_for_entity('installment_payments', cascade=False)
                                logger.info("Cache invalidated after payment")
                            except Exception as e:
                                logger.warning(f"Failed to invalidate cache: {str(e)}")

                    except Exception as e:
                        logger.error(f"Error recording payment (transaction rolled back): {str(e)}", exc_info=True)
                        flash(f'Error recording payment: {str(e)}', 'error')
                        return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))

                flash('Payment recorded successfully!', 'success')
                # Redirect to universal payment list for this patient
                if patient_id_for_redirect:
                    return redirect(url_for('universal_views.universal_list_view',
                                           entity_type='patient_payments',
                                           patient_id=str(patient_id_for_redirect)))
                # Fallback to invoice view if we can't get patient_id
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))

            except (ValueError, decimal.InvalidOperation, decimal.ConversionSyntax) as e:
                flash(f'Payment error: {str(e)}', 'error')
                logger.error(f"Enhanced payment validation error: {str(e)}", exc_info=True)
                return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))

    except (ValueError, decimal.InvalidOperation, decimal.ConversionSyntax) as e:
        flash(f'Invalid payment data: {str(e)}', 'error')
        logger.error(f"Enhanced payment data error: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.record_invoice_payment_enhanced', invoice_id=invoice_id))
    except Exception as e:
        flash(f'Error processing payment: {str(e)}', 'error')
        logger.error(f"Enhanced payment error: {str(e)}", exc_info=True)
        return redirect(url_for('universal_views.universal_list_view', entity_type='patient_invoices'))


@billing_views_bp.route('/payment/<uuid:payment_id>/refund', methods=['POST'])
@login_required
@permission_required('billing', 'delete')
def issue_payment_refund(payment_id):
    """Issue a refund for a payment"""
    try:
        invoice_id = request.form.get('invoice_id')
        if not invoice_id:
            flash('Invoice ID is required.', 'error')
            return redirect(url_for('billing_views.invoice_list'))
        
        refund_amount = Decimal(request.form.get('refund_amount', '0'))
        if refund_amount <= 0:
            flash('Refund amount must be greater than zero.', 'error')
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        
        refund_reason = request.form.get('refund_reason')
        if not refund_reason:
            flash('Reason for refund is required.', 'error')
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        
        # Issue the refund
        issue_refund(
            hospital_id=current_user.hospital_id,
            payment_id=payment_id,
            refund_amount=refund_amount,
            refund_date=datetime.now(timezone.utc),
            refund_reason=refund_reason,
            current_user_id=current_user.user_id
        )
        
        flash('Refund issued successfully.', 'success')
        
    except Exception as e:
        flash(f'Error issuing refund: {str(e)}', 'error')
        logger.error(f"Error issuing refund: {str(e)}", exc_info=True)
    
    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))


# ============================================================================
# PAYMENT WORKFLOW ROUTES
# ============================================================================

@billing_views_bp.route('/payment/<uuid:payment_id>/approve', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'approve')
def approve_payment_view(payment_id):
    """Approve a pending payment"""
    try:
        if request.method == 'GET':
            # Show approval confirmation page
            with get_db_session() as session:
                payment = session.query(PaymentDetail).filter_by(
                    payment_id=payment_id,
                    hospital_id=current_user.hospital_id
                ).first()

                if not payment:
                    flash('Payment not found', 'error')
                    return redirect(url_for('billing_views.invoice_list'))

                if payment.workflow_status != 'pending_approval':
                    flash(f'Payment is not pending approval (current status: {payment.workflow_status})', 'warning')
                    return redirect(url_for('billing_views.view_invoice', invoice_id=payment.invoice_id))

                # Get invoice details
                invoice = session.query(InvoiceHeader).filter_by(
                    invoice_id=payment.invoice_id
                ).first()

                # Get patient details
                patient = session.query(Patient).filter_by(
                    patient_id=invoice.patient_id
                ).first()

                payment_dict = get_entity_dict(payment)
                invoice_dict = get_entity_dict(invoice)
                patient_dict = get_entity_dict(patient) if patient else None

                return render_template(
                    'billing/payment_approval.html',
                    payment=payment_dict,
                    invoice=invoice_dict,
                    patient=patient_dict,
                    action='approve',
                    menu_items=get_menu_items(current_user)
                )

        # POST: Process approval
        result = approve_payment(
            payment_id=payment_id,
            approved_by=current_user.user_id,
            hospital_id=current_user.hospital_id
        )

        if result.get('success'):
            flash('Payment approved and GL entries posted successfully', 'success')
        else:
            flash(f"Error approving payment: {result.get('error')}", 'error')

        # Get invoice_id to redirect
        with get_db_session() as session:
            payment = session.query(PaymentDetail).filter_by(
                payment_id=payment_id
            ).first()
            invoice_id = payment.invoice_id if payment else None

        if invoice_id:
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        else:
            return redirect(url_for('billing_views.invoice_list'))

    except Exception as e:
        flash(f'Error processing approval: {str(e)}', 'error')
        logger.error(f"Error processing approval: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))


@billing_views_bp.route('/payment/<uuid:payment_id>/reject', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'approve')
def reject_payment_view(payment_id):
    """Reject a pending payment"""
    try:
        if request.method == 'GET':
            # Show rejection confirmation page
            with get_db_session() as session:
                payment = session.query(PaymentDetail).filter_by(
                    payment_id=payment_id,
                    hospital_id=current_user.hospital_id
                ).first()

                if not payment:
                    flash('Payment not found', 'error')
                    return redirect(url_for('billing_views.invoice_list'))

                if payment.workflow_status != 'pending_approval':
                    flash(f'Payment is not pending approval (current status: {payment.workflow_status})', 'warning')
                    return redirect(url_for('billing_views.view_invoice', invoice_id=payment.invoice_id))

                # Get invoice details
                invoice = session.query(InvoiceHeader).filter_by(
                    invoice_id=payment.invoice_id
                ).first()

                # Get patient details
                patient = session.query(Patient).filter_by(
                    patient_id=invoice.patient_id
                ).first()

                payment_dict = get_entity_dict(payment)
                invoice_dict = get_entity_dict(invoice)
                patient_dict = get_entity_dict(patient) if patient else None

                return render_template(
                    'billing/payment_approval.html',
                    payment=payment_dict,
                    invoice=invoice_dict,
                    patient=patient_dict,
                    action='reject',
                    menu_items=get_menu_items(current_user)
                )

        # POST: Process rejection
        rejection_reason = request.form.get('rejection_reason')
        if not rejection_reason:
            flash('Rejection reason is required', 'error')
            return redirect(url_for('billing_views.reject_payment_view', payment_id=payment_id))

        result = reject_payment(
            payment_id=payment_id,
            rejected_by=current_user.user_id,
            rejection_reason=rejection_reason,
            hospital_id=current_user.hospital_id
        )

        if result.get('success'):
            flash('Payment rejected successfully', 'success')
        else:
            flash(f"Error rejecting payment: {result.get('error')}", 'error')

        # Get invoice_id to redirect
        with get_db_session() as session:
            payment = session.query(PaymentDetail).filter_by(
                payment_id=payment_id
            ).first()
            invoice_id = payment.invoice_id if payment else None

        if invoice_id:
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        else:
            return redirect(url_for('billing_views.invoice_list'))

    except Exception as e:
        flash(f'Error processing rejection: {str(e)}', 'error')
        logger.error(f"Error processing rejection: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))


@billing_views_bp.route('/payment/<uuid:payment_id>/reverse', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'delete')
def reverse_payment_view(payment_id):
    """Reverse an approved payment"""
    try:
        if request.method == 'GET':
            # Show reversal confirmation page
            with get_db_session() as session:
                payment = session.query(PaymentDetail).filter_by(
                    payment_id=payment_id,
                    hospital_id=current_user.hospital_id
                ).first()

                if not payment:
                    flash('Payment not found', 'error')
                    return redirect(url_for('billing_views.invoice_list'))

                if payment.workflow_status != 'approved':
                    flash(f'Only approved payments can be reversed (current status: {payment.workflow_status})', 'warning')
                    return redirect(url_for('billing_views.view_invoice', invoice_id=payment.invoice_id))

                if payment.is_reversed:
                    flash('Payment is already reversed', 'warning')
                    return redirect(url_for('billing_views.view_invoice', invoice_id=payment.invoice_id))

                # Get invoice details
                invoice = session.query(InvoiceHeader).filter_by(
                    invoice_id=payment.invoice_id
                ).first()

                # Get patient details
                patient = session.query(Patient).filter_by(
                    patient_id=invoice.patient_id
                ).first()

                payment_dict = get_entity_dict(payment)
                invoice_dict = get_entity_dict(invoice)
                patient_dict = get_entity_dict(patient) if patient else None

                return render_template(
                    'billing/payment_reversal.html',
                    payment=payment_dict,
                    invoice=invoice_dict,
                    patient=patient_dict,
                    menu_items=get_menu_items(current_user)
                )

        # POST: Process reversal
        reversal_reason = request.form.get('reversal_reason')
        if not reversal_reason:
            flash('Reversal reason is required', 'error')
            return redirect(url_for('billing_views.reverse_payment_view', payment_id=payment_id))

        result = reverse_payment(
            payment_id=payment_id,
            reversed_by=current_user.user_id,
            reversal_reason=reversal_reason,
            hospital_id=current_user.hospital_id
        )

        if result.get('success'):
            flash('Payment reversed successfully and GL entries reversed', 'success')
        else:
            flash(f"Error reversing payment: {result.get('error')}", 'error')

        # Get invoice_id to redirect
        with get_db_session() as session:
            payment = session.query(PaymentDetail).filter_by(
                payment_id=payment_id
            ).first()
            invoice_id = payment.invoice_id if payment else None

        if invoice_id:
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        else:
            return redirect(url_for('billing_views.invoice_list'))

    except Exception as e:
        flash(f'Error processing reversal: {str(e)}', 'error')
        logger.error(f"Error processing reversal: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))


@billing_views_bp.route('/web_api/patient/search', methods=['GET'])
@login_required
def web_api_patient_search():
    """Web-friendly patient search that uses Flask-Login with backward compatibility"""
    try:
        # Try the new search implementation first
        from app.services.patient_service import search_patients
        
        # Get query parameters (same as current implementation)
        query = request.args.get('q', '')
        hospital_id = current_user.hospital_id
        
        # Use new centralized search service
        search_result = search_patients(
            hospital_id=hospital_id,
            search_term=query,
            limit=20  # Changed from 10 to 20
        )
        
        # Format response to match current format expected by existing code
        if isinstance(search_result, dict) and 'items' in search_result:
            # New format - convert to legacy format
            results = []
            for patient in search_result['items']:
                results.append({
                    'id': patient['id'],
                    'name': patient['name'],
                    'mrn': patient['mrn'],
                    'contact': patient['contact']
                })
            return jsonify(results)
        else:
            # Already in legacy format
            return jsonify(search_result)
            
    except Exception as e:
        # Log the error from new implementation
        current_app.logger.error(f"New patient search failed, falling back to legacy search: {str(e)}", exc_info=True)
        
        # Fall back to current search implementation
        try:
            with get_db_session() as session:
                query = request.args.get('q', '')
                hospital_id = current_user.hospital_id
                
                # For empty query, return recent/popular patients without filtering
                if not query:
                    patients = session.query(Patient).filter(
                        Patient.hospital_id == hospital_id,
                        Patient.is_active == True
                    ).order_by(Patient.updated_at.desc()).limit(20).all()  # Changed from 10 to 20
                else:
                    # Improve search queries to include name searching
                    from sqlalchemy import or_
                    
                    # Use existing search logic
                    patients = session.query(Patient).filter(
                        Patient.hospital_id == hospital_id,
                        Patient.is_active == True,
                        or_(
                            # Search by MRN
                            Patient.mrn.ilike(f'%{query}%'),
                            # Search by full_name property if it exists
                            Patient.full_name.ilike(f'%{query}%') if hasattr(Patient, 'full_name') else False,
                            # Search within personal_info fields if structured as JSON
                            Patient.personal_info['first_name'].astext.ilike(f'%{query}%') if hasattr(Patient, 'personal_info') else False,
                            Patient.personal_info['last_name'].astext.ilike(f'%{query}%') if hasattr(Patient, 'personal_info') else False
                        )
                    ).limit(20).all()  # Changed from 10 to 20
                
                # Rest of the function remains unchanged
                # Format results with error handling for personal_info issues
                results = []
                for patient in patients:
                    try:
                        # Get patient name safely (kept from current implementation)
                        name = ""
                        if hasattr(patient, 'personal_info'):
                            if isinstance(patient.personal_info, dict):
                                first_name = patient.personal_info.get('first_name', '')
                                last_name = patient.personal_info.get('last_name', '')
                                name = f"{first_name} {last_name}".strip()
                            elif isinstance(patient.personal_info, str):
                                # Try to parse JSON string
                                import json
                                try:
                                    info = json.loads(patient.personal_info)
                                    if isinstance(info, dict):
                                        first_name = info.get('first_name', '')
                                        last_name = info.get('last_name', '')
                                        name = f"{first_name} {last_name}".strip()
                                    else:
                                        name = str(patient.personal_info)
                                except (json.JSONDecodeError, TypeError):
                                    name = str(patient.personal_info)
                            else:
                                name = f"Patient {patient.mrn}"
                        else:
                            # Try to use the full_name property if it exists
                            if hasattr(patient, 'full_name'):
                                name = patient.full_name
                            else:
                                name = f"Patient {patient.mrn}"
                        
                        # Handle contact info safely (kept from current implementation)
                        contact = None
                        if hasattr(patient, 'contact_info'):
                            if isinstance(patient.contact_info, dict):
                                contact = patient.contact_info.get('phone')
                            elif isinstance(patient.contact_info, str):
                                # Try to parse JSON string
                                import json
                                try:
                                    info = json.loads(patient.contact_info)
                                    if isinstance(info, dict):
                                        contact = info.get('phone')
                                    else:
                                        contact = str(patient.contact_info)
                                except (json.JSONDecodeError, TypeError):
                                    contact = str(patient.contact_info)
                        
                        patient_dict = {
                            'id': str(patient.patient_id),
                            'name': name,
                            'mrn': patient.mrn,
                            'contact': contact,
                            # Add raw values for debugging and handling edge cases
                            'raw_info': str(patient.personal_info) if hasattr(patient, 'personal_info') else None
                        }
                        results.append(patient_dict)
                    except Exception as e:
                        current_app.logger.error(f"Error processing patient record: {str(e)}", exc_info=True)
                        # Include a minimal record so the search doesn't fail
                        results.append({
                            'id': str(patient.patient_id),
                            'name': f"Patient {patient.mrn}",
                            'mrn': patient.mrn,
                            'contact': None
                        })
                
                return jsonify(results)
        except Exception as e:
            current_app.logger.error(f"Legacy patient search also failed: {str(e)}", exc_info=True)
            return jsonify([])  # Return empty list instead of error for better UX

@billing_views_bp.route('/web_api/item/search', methods=['GET'])
@login_required
def web_api_item_search():
    """Web-friendly item search that uses Flask-Login"""
    try:

        with get_db_session() as session:
            # Get query parameters
            query = request.args.get('q', '')
            item_type = request.args.get('type', '')

            if not item_type:
                return jsonify([])

            hospital_id = current_user.hospital_id

            # Get invoice date (for date-based GST/pricing lookup)
            # If not provided, use today's date (for new invoices being created now)
            invoice_date_str = request.args.get('invoice_date')
            if invoice_date_str:
                from datetime import datetime
                try:
                    applicable_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                    current_app.logger.debug(f"[ITEM SEARCH] Using invoice_date={applicable_date} for pricing lookup")
                except ValueError:
                    current_app.logger.warning(f"[ITEM SEARCH] Invalid invoice_date format: {invoice_date_str}. Using today.")
                    from datetime import datetime, timezone
                    applicable_date = datetime.now(timezone.utc).date()
            else:
                from datetime import datetime, timezone
                applicable_date = datetime.now(timezone.utc).date()
            
            # Search based on item type
            results = []
            
            if item_type == 'Package':
                # Package uses 'status' field instead of 'is_active'
                packages = session.query(Package).filter(
                    Package.hospital_id == hospital_id,
                    Package.package_name.ilike(f'%{query}%')
                ).filter(
                    or_(Package.status == 'active', Package.status.is_(None))
                ).order_by(Package.package_name).limit(20).all()

                current_app.logger.info(f"Package search for '{query}': found {len(packages)} results")

                # Use date-based pricing/GST service
                # Use the applicable_date (invoice_date or today) set earlier
                from app.services.pricing_tax_service import get_applicable_pricing_and_tax

                for package in packages:
                    # Get pricing and GST applicable on the invoice date
                    try:
                        pricing_tax = get_applicable_pricing_and_tax(
                            session=session,
                            hospital_id=hospital_id,
                            entity_type='package',
                            entity_id=package.package_id,
                            applicable_date=applicable_date
                        )

                        gst_rate = float(pricing_tax['gst_rate']) if pricing_tax['gst_rate'] else 0.0
                        is_gst_exempt = pricing_tax['is_gst_exempt']
                        price = float(pricing_tax.get('price', 0)) if pricing_tax.get('price') else 0.0

                        # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                        if is_gst_exempt:
                            gst_rate = 0.0

                        current_app.logger.debug(f"Package '{package.package_name}': Using {pricing_tax['source']} - "
                                               f"gst_rate={gst_rate}%, price={price}")
                    except Exception as e:
                        current_app.logger.warning(f"Failed to get date-based pricing for package {package.package_id}: {e}. Using master table values.")
                        gst_rate = float(package.gst_rate) if hasattr(package, 'gst_rate') and package.gst_rate else 0.0
                        is_gst_exempt = package.is_gst_exempt if hasattr(package, 'is_gst_exempt') else False
                        price = float(package.price) if hasattr(package, 'price') and package.price else 0.0

                        # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                        if is_gst_exempt:
                            gst_rate = 0.0

                    results.append({
                        'id': str(package.package_id),
                        'name': package.package_name,
                        'type': 'Package',
                        'price': price,
                        'gst_rate': gst_rate,
                        'is_gst_exempt': is_gst_exempt,
                        'gst_inclusive': False  # Packages are GST exclusive by default
                    })
            
            elif item_type == 'Service':
                # Check if Service has is_active attribute, if not, filter without it
                if hasattr(Service, 'is_active'):
                    services = session.query(Service).filter(
                        Service.hospital_id == hospital_id,
                        Service.is_active == True,
                        Service.service_name.ilike(f'%{query}%')
                    ).order_by(Service.service_name).limit(20).all()
                else:
                    services = session.query(Service).filter(
                        Service.hospital_id == hospital_id,
                        Service.service_name.ilike(f'%{query}%')
                    ).order_by(Service.service_name).limit(20).all()

                # Use date-based pricing/GST service
                # Use the applicable_date (invoice_date or today) set earlier
                from app.services.pricing_tax_service import get_applicable_pricing_and_tax

                for service in services:
                    # Get pricing and GST applicable on the invoice date

                    try:
                        pricing_tax = get_applicable_pricing_and_tax(
                            session=session,
                            hospital_id=hospital_id,
                            entity_type='service',
                            entity_id=service.service_id,
                            applicable_date=applicable_date
                        )

                        gst_rate = float(pricing_tax['gst_rate']) if pricing_tax['gst_rate'] else 0.0
                        is_gst_exempt = pricing_tax['is_gst_exempt']
                        price = float(pricing_tax.get('price', 0)) if pricing_tax.get('price') else 0.0

                        # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                        if is_gst_exempt:
                            gst_rate = 0.0

                        current_app.logger.debug(f"Service '{service.service_name}': Using {pricing_tax['source']} - "
                                               f"gst_rate={gst_rate}%, price={price}")
                    except Exception as e:
                        current_app.logger.warning(f"Failed to get date-based pricing for service {service.service_id}: {e}. Using master table values.")
                        gst_rate = float(service.gst_rate) if hasattr(service, 'gst_rate') and service.gst_rate else 0.0
                        is_gst_exempt = service.is_gst_exempt if hasattr(service, 'is_gst_exempt') else False
                        price = float(service.price) if hasattr(service, 'price') and service.price else 0.0

                        # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                        if is_gst_exempt:
                            gst_rate = 0.0

                    results.append({
                        'id': str(service.service_id),
                        'name': service.service_name,
                        'type': 'Service',
                        'price': price,
                        'gst_rate': gst_rate,
                        'is_gst_exempt': is_gst_exempt,
                        'gst_inclusive': False,  # Services are GST exclusive by default
                        'sac_code': service.sac_code if hasattr(service, 'sac_code') else None
                    })
            
            elif item_type in ['OTC', 'Prescription', 'Product', 'Consumable']:
                # All medicine-based item types use medicine_type field
                # Only show medicines that have inventory in stock

                # First, get medicine IDs that have stock
                medicine_ids_with_stock = session.query(Inventory.medicine_id).filter(
                    Inventory.hospital_id == hospital_id,
                    Inventory.current_stock > 0
                ).distinct().subquery()

                # Query medicines with stock only
                base_filter = and_(
                    Medicine.hospital_id == hospital_id,
                    Medicine.medicine_type == item_type,
                    Medicine.medicine_id.in_(medicine_ids_with_stock)
                )

                # Add search query if provided
                if query:
                    base_filter = and_(base_filter, Medicine.medicine_name.ilike(f'%{query}%'))

                medicines = session.query(Medicine).filter(base_filter).order_by(Medicine.medicine_name).limit(20).all()

                current_app.logger.info(f"{item_type} search for '{query}': found {len(medicines)} results (with stock only)")

                # Use date-based pricing/GST service for medicines
                # Use the applicable_date (invoice_date or today) set earlier
                from app.services.pricing_tax_service import get_applicable_pricing_and_tax

                # Convert to result format
                for medicine in medicines:
                    # Get pricing and GST applicable on the invoice date
                    try:
                        pricing_tax = get_applicable_pricing_and_tax(
                            session=session,
                            hospital_id=hospital_id,
                            entity_type='medicine',
                            entity_id=medicine.medicine_id,
                            applicable_date=applicable_date
                        )

                        gst_rate = float(pricing_tax['gst_rate']) if pricing_tax['gst_rate'] else 0.0
                        is_gst_exempt = pricing_tax['is_gst_exempt']

                        # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                        if is_gst_exempt:
                            gst_rate = 0.0

                        current_app.logger.debug(f"Medicine '{medicine.medicine_name}': Using {pricing_tax['source']} - "
                                               f"gst_rate={gst_rate}%")
                    except Exception as e:
                        current_app.logger.warning(f"Failed to get date-based pricing for medicine {medicine.medicine_id}: {e}. Using master table values.")
                        gst_rate = float(medicine.gst_rate) if hasattr(medicine, 'gst_rate') and medicine.gst_rate else 0.0
                        is_gst_exempt = medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False

                        # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                        if is_gst_exempt:
                            gst_rate = 0.0

                    results.append({
                        'id': str(medicine.medicine_id),
                        'name': medicine.medicine_name,
                        'type': item_type,  # Return the actual type (OTC, Prescription, Product, Consumable)
                        'gst_rate': gst_rate,
                        'is_gst_exempt': is_gst_exempt,
                        'gst_inclusive': medicine.gst_inclusive if hasattr(medicine, 'gst_inclusive') else False,  # ✅ Add gst_inclusive flag
                        'hsn_code': medicine.hsn_code if hasattr(medicine, 'hsn_code') else None
                    })
            
            return jsonify(results)
            
    except Exception as e:
        current_app.logger.error(f"Error searching items: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error searching items'}), 500

@billing_views_bp.route('/web_api/medicine/<uuid:medicine_id>/batches', methods=['GET'])
@login_required
def web_api_medicine_batches(medicine_id):
    """Web-friendly medicine batches lookup that uses Flask-Login"""
    try:
        with get_db_session() as session:
            # Get query parameters
            quantity = Decimal(request.args.get('quantity', '1'))
            hospital_id = current_user.hospital_id

            # Get invoice date (for date-based GST/pricing lookup)
            # If not provided, use today's date (for new invoices being created now)
            invoice_date_str = request.args.get('invoice_date')
            if invoice_date_str:
                from datetime import datetime
                try:
                    applicable_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                    current_app.logger.info(f"[BATCH LOOKUP] Using invoice_date={applicable_date} for pricing lookup")
                except ValueError:
                    current_app.logger.warning(f"[BATCH LOOKUP] Invalid invoice_date format: {invoice_date_str}. Using today.")
                    applicable_date = datetime.now(timezone.utc).date()
            else:
                from datetime import datetime, timezone
                applicable_date = datetime.now(timezone.utc).date()
                current_app.logger.debug(f"[BATCH LOOKUP] No invoice_date provided, using today: {applicable_date}")

            # DEBUG: Log the lookup attempt
            current_app.logger.info(f"[BATCH LOOKUP] Searching for medicine_id={medicine_id} (type={type(medicine_id).__name__}), hospital_id={hospital_id} (type={type(hospital_id).__name__}), user={current_user.user_id}")

            # Get medicine details
            # Don't filter by is_active - it causes comparison issues
            # The search endpoint doesn't filter by is_active either
            medicine = session.query(Medicine).filter(
                Medicine.hospital_id == hospital_id,
                Medicine.medicine_id == medicine_id
            ).first()
            
            if not medicine:
                current_app.logger.warning(f"[BATCH LOOKUP] Medicine NOT FOUND: medicine_id={medicine_id}, hospital_id={hospital_id}")

                # DEBUG: Check if medicine exists with different filters
                # Test 1: Just medicine_id with filter()
                test1 = session.query(Medicine).filter(Medicine.medicine_id == medicine_id).first()
                current_app.logger.warning(f"[BATCH LOOKUP] Test1 (filter medicine_id only): {'FOUND' if test1 else 'NOT FOUND'}")

                # Test 2: Just hospital_id with filter()
                test2 = session.query(Medicine).filter(Medicine.hospital_id == hospital_id).first()
                current_app.logger.warning(f"[BATCH LOOKUP] Test2 (filter hospital_id only): {'FOUND' if test2 else 'NOT FOUND'}")

                # Test 3: Both with filter()
                test3 = session.query(Medicine).filter(
                    Medicine.hospital_id == hospital_id,
                    Medicine.medicine_id == medicine_id
                ).first()
                current_app.logger.warning(f"[BATCH LOOKUP] Test3 (filter both, no is_active): {'FOUND' if test3 else 'NOT FOUND'}")

                if test3:
                    current_app.logger.warning(f"[BATCH LOOKUP] Test3 medicine: name={test3.medicine_name}, is_active={getattr(test3, 'is_active', 'N/A')}")

                return jsonify({'error': 'Medicine not found'}), 404

            current_app.logger.info(f"[BATCH LOOKUP] Medicine FOUND: {medicine.medicine_name}, hospital_id={medicine.hospital_id}")

            # Get the LATEST current_stock per batch (current_stock is a running balance, not a quantity to sum)
            # Use window function to get the most recent record per batch
            from sqlalchemy.sql import text

            query = text("""
                WITH latest_per_batch AS (
                    SELECT
                        i.batch,
                        i.expiry,
                        i.current_stock,
                        i.sale_price,
                        i.pack_mrp,
                        i.cgst,
                        i.sgst,
                        i.igst,
                        i.created_at,
                        ROW_NUMBER() OVER (PARTITION BY i.batch ORDER BY i.created_at DESC) as rn
                    FROM inventory i
                    WHERE i.hospital_id = :hospital_id
                      AND i.medicine_id = :medicine_id
                )
                SELECT
                    batch,
                    expiry,
                    current_stock,
                    sale_price,
                    pack_mrp,
                    cgst,
                    sgst,
                    igst,
                    1 as record_count
                FROM latest_per_batch
                WHERE rn = 1
                  AND current_stock > 0  -- Only batches with available stock
                ORDER BY expiry  -- FIFO based on expiry
            """)

            result_proxy = session.execute(query, {
                'hospital_id': hospital_id,
                'medicine_id': medicine_id
            })

            # Convert result proxy to list of batch records
            consolidated_batches = []
            for row in result_proxy:
                # Create a namespace object to mimic ORM record
                from types import SimpleNamespace
                record = SimpleNamespace(**{column: getattr(row, column) for column in row._mapping.keys()})
                consolidated_batches.append(record)

                # Log batch info
                price_str = f"{record.sale_price:.2f}" if record.sale_price else "0.00"
                current_app.logger.debug(f"[BATCH LOOKUP] Batch '{record.batch}': Stock={record.current_stock}, Price={price_str}")

            current_app.logger.info(f"[BATCH LOOKUP] Found {len(consolidated_batches)} batches with stock for {medicine.medicine_name}")
            
            # IMPORTANT: Get GST rate from pricing_tax_service, NOT from inventory
            # Inventory GST is historical and may not reflect current config
            # Use the applicable_date (invoice_date or today) set earlier
            from app.services.pricing_tax_service import get_applicable_pricing_and_tax

            try:
                pricing_tax = get_applicable_pricing_and_tax(
                    session=session,
                    hospital_id=hospital_id,
                    entity_type='medicine',
                    entity_id=medicine_id,
                    applicable_date=applicable_date
                )

                medicine_gst_rate = pricing_tax['gst_rate']
                medicine_is_gst_exempt = pricing_tax['is_gst_exempt']
                medicine_mrp = pricing_tax.get('mrp', 0)  # ✅ Get MRP from pricing_tax_service
                medicine_pack_mrp = pricing_tax.get('pack_mrp', 0)  # ✅ Get pack_mrp from config

                # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                if medicine_is_gst_exempt:
                    medicine_gst_rate = 0.0

                current_app.logger.info(f"[BATCH LOOKUP] Medicine pricing from {pricing_tax['source']}: "
                                       f"gst_rate={medicine_gst_rate}%, is_gst_exempt={medicine_is_gst_exempt}, "
                                       f"MRP={medicine_mrp}, pack_MRP={medicine_pack_mrp}")
            except Exception as e:
                current_app.logger.warning(f"[BATCH LOOKUP] Failed to get pricing_tax for medicine {medicine_id}: {e}. "
                                         f"Using medicine master table as fallback.")
                # Fallback to medicine master table
                medicine_gst_rate = float(medicine.gst_rate) if medicine.gst_rate else 0.0
                medicine_is_gst_exempt = medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False
                medicine_mrp = float(medicine.mrp) if hasattr(medicine, 'mrp') and medicine.mrp else 0.0
                medicine_pack_mrp = float(medicine.pack_mrp) if hasattr(medicine, 'pack_mrp') and medicine.pack_mrp else 0.0

                # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                if medicine_is_gst_exempt:
                    medicine_gst_rate = 0.0

            # Format the response
            result = []
            for record in consolidated_batches:
                # NOTE: Inventory CGST/SGST/IGST are for reference only (historical transaction data)
                # The ACTUAL GST rate to use comes from pricing_tax_service above
                inventory_cgst = float(record.cgst) if record.cgst else 0
                inventory_sgst = float(record.sgst) if record.sgst else 0
                inventory_igst = float(record.igst) if record.igst else 0
                inventory_pack_mrp = float(record.pack_mrp) if record.pack_mrp else 0  # Backup only

                result.append({
                    'batch': record.batch,
                    'expiry_date': record.expiry.strftime('%Y-%m-%d') if record.expiry else None,
                    'available_quantity': float(record.current_stock) if record.current_stock else 0,
                    'unit_price': float(record.sale_price) if record.sale_price else 0,  # Weighted average price
                    'mrp': float(medicine_mrp) if medicine_mrp else inventory_pack_mrp,  # ✅ From pricing_tax_service, inventory as fallback
                    'gst_rate': medicine_gst_rate,  # ✅ From pricing_tax_service, NOT inventory
                    'is_gst_exempt': medicine_is_gst_exempt,  # ✅ From pricing_tax_service
                    'gst_inclusive': medicine.gst_inclusive if hasattr(medicine, 'gst_inclusive') else False,  # ✅ From medicine master
                    # Include inventory data for reference only (not used for calculation)
                    'inventory_cgst': inventory_cgst,
                    'inventory_sgst': inventory_sgst,
                    'inventory_igst': inventory_igst,
                    'inventory_pack_mrp': inventory_pack_mrp,  # ✅ Historical MRP for reference
                    'is_sufficient': record.current_stock >= quantity,
                    'is_consolidated': record.record_count > 1,  # ✅ Indicates multiple records consolidated
                    'record_count': record.record_count  # ✅ How many records behind this batch
                })
            
            # Sort by expiry date (FIFO)
            result.sort(key=lambda x: x.get('expiry_date', '9999-12-31'))
            
            return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error getting medicine batches: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error getting medicine batches'}), 500

@billing_views_bp.route('/web_api/medicine/<uuid:medicine_id>/fifo-allocation', methods=['GET'])
@login_required
def web_api_medicine_fifo_allocation(medicine_id):
    """
    Get FIFO batch allocation for a medicine based on required quantity
    Uses existing FIFO service from inventory_service.py
    """
    try:
        # Import inventory service here to avoid circular imports
        from app.services.inventory_service import get_batch_selection_for_invoice

        with get_db_session() as session:
            # Get parameters
            quantity_str = request.args.get('quantity', '1')
            try:
                quantity = Decimal(quantity_str)
            except (InvalidOperation, ValueError):
                return jsonify({
                    'success': False,
                    'message': 'Invalid quantity parameter'
                }), 400

            hospital_id = current_user.hospital_id

            # Get invoice date (for date-based GST/pricing lookup)
            # If not provided, use today's date (for new invoices being created now)
            invoice_date_str = request.args.get('invoice_date')
            if invoice_date_str:
                from datetime import datetime
                try:
                    applicable_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
                    current_app.logger.info(f"[FIFO ALLOCATION] Using invoice_date={applicable_date} for pricing lookup")
                except ValueError:
                    current_app.logger.warning(f"[FIFO ALLOCATION] Invalid invoice_date format: {invoice_date_str}. Using today.")
                    from datetime import datetime, timezone
                    applicable_date = datetime.now(timezone.utc).date()
            else:
                from datetime import datetime, timezone
                applicable_date = datetime.now(timezone.utc).date()
                current_app.logger.debug(f"[FIFO ALLOCATION] No invoice_date provided, using today: {applicable_date}")

            # Verify medicine exists
            medicine = session.query(Medicine).filter_by(
                hospital_id=hospital_id,
                medicine_id=medicine_id
            ).first()

            if not medicine:
                return jsonify({
                    'success': False,
                    'message': 'Medicine not found'
                }), 404

            # Get pricing/tax from pricing_tax_service (date-based config)
            # Use the applicable_date (invoice_date or today) set earlier
            from app.services.pricing_tax_service import get_applicable_pricing_and_tax

            try:
                pricing_tax = get_applicable_pricing_and_tax(
                    session=session,
                    hospital_id=hospital_id,
                    entity_type='medicine',
                    entity_id=medicine_id,
                    applicable_date=applicable_date
                )

                medicine_gst_rate = float(pricing_tax['gst_rate'])
                medicine_is_gst_exempt = pricing_tax['is_gst_exempt']
                medicine_mrp = float(pricing_tax.get('mrp', 0))
                medicine_cgst = float(pricing_tax.get('cgst_rate', 0))
                medicine_sgst = float(pricing_tax.get('sgst_rate', 0))
                medicine_igst = float(pricing_tax.get('igst_rate', 0))

                # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                if medicine_is_gst_exempt:
                    medicine_gst_rate = 0.0
                    medicine_cgst = 0.0
                    medicine_sgst = 0.0
                    medicine_igst = 0.0

                current_app.logger.info(f"[FIFO ALLOCATION] Using pricing from {pricing_tax['source']}: "
                                      f"GST={medicine_gst_rate}%, MRP={medicine_mrp}")
            except Exception as e:
                current_app.logger.warning(f"[FIFO ALLOCATION] Failed to get pricing_tax: {e}. Using medicine master table.")
                medicine_gst_rate = float(medicine.gst_rate) if medicine.gst_rate else 0.0
                medicine_is_gst_exempt = medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False
                medicine_mrp = float(medicine.mrp) if hasattr(medicine, 'mrp') and medicine.mrp else 0.0
                medicine_cgst = medicine_gst_rate / 2 if medicine_gst_rate else 0.0
                medicine_sgst = medicine_gst_rate / 2 if medicine_gst_rate else 0.0
                medicine_igst = 0.0

                # Override GST rate to 0 if item is GST exempt (avoid misleading display)
                if medicine_is_gst_exempt:
                    medicine_gst_rate = 0.0
                    medicine_cgst = 0.0
                    medicine_sgst = 0.0
                    medicine_igst = 0.0

            # Get FIFO batch allocation using existing service
            batch_allocations = get_batch_selection_for_invoice(
                hospital_id=hospital_id,
                medicine_id=medicine_id,
                quantity_needed=quantity,
                session=session
            )

            # Format response for frontend
            formatted_batches = []
            for batch in batch_allocations:
                # Query inventory for additional details (stock, historical MRP for reference)
                inventory = session.query(Inventory).filter(
                    Inventory.hospital_id == hospital_id,
                    Inventory.medicine_id == medicine_id,
                    Inventory.batch == batch['batch']
                ).order_by(Inventory.created_at.desc()).first()

                inventory_pack_mrp = float(inventory.pack_mrp) if inventory and inventory.pack_mrp else 0

                formatted_batches.append({
                    'batch': batch['batch'],
                    'expiry_date': batch['expiry_date'].strftime('%Y-%m-%d') if batch.get('expiry_date') else None,
                    'quantity': float(batch['quantity']),
                    'available_stock': float(inventory.current_stock) if inventory else 0,
                    'unit_price': float(batch.get('unit_price', 0)),
                    'sale_price': float(batch.get('sale_price', 0)),
                    'mrp': medicine_mrp if medicine_mrp else inventory_pack_mrp,  # ✅ From pricing_tax_service, inventory as fallback
                    'gst_rate': medicine_gst_rate,  # ✅ From pricing_tax_service
                    'cgst': medicine_cgst,  # ✅ From pricing_tax_service
                    'sgst': medicine_sgst,  # ✅ From pricing_tax_service
                    'igst': medicine_igst,  # ✅ From pricing_tax_service
                    'hsn_code': medicine.hsn_code if hasattr(medicine, 'hsn_code') and medicine.hsn_code else '',
                    'is_gst_exempt': medicine_is_gst_exempt,  # ✅ From pricing_tax_service
                    'inventory_pack_mrp': inventory_pack_mrp  # Historical MRP for reference
                })

            # Calculate totals
            total_allocated = sum(b['quantity'] for b in formatted_batches)
            is_sufficient = total_allocated >= float(quantity)

            return jsonify({
                'success': True,
                'batches': formatted_batches,
                'total_allocated': float(total_allocated),
                'quantity_requested': float(quantity),
                'is_sufficient': is_sufficient,
                'shortage': float(quantity - total_allocated) if not is_sufficient else 0
            })

    except Exception as e:
        current_app.logger.error(f"Error getting FIFO allocation: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Error calculating FIFO allocation. Please try again.'
        }), 500

@billing_views_bp.route('/web_api/patient/<uuid:patient_id>/state', methods=['GET'])
@login_required
def get_patient_state(patient_id):
    """Get patient's state for interstate calculation"""
    try:
        from app.config.core_definitions import INDIAN_STATES

        with get_db_session() as session:
            # Get patient
            patient = session.query(Patient).filter_by(
                patient_id=patient_id,
                hospital_id=current_user.hospital_id
            ).first()

            if not patient:
                return jsonify({'success': False, 'message': 'Patient not found'}), 404

            # Extract patient state from contact_info JSONB
            patient_state_code = None
            patient_state_name = None
            if patient.contact_info:
                if isinstance(patient.contact_info, dict):
                    patient_state_code = patient.contact_info.get('state_code') or patient.contact_info.get('state')

            # Get hospital state
            hospital = session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()

            # Get branch state from session
            branch_state_code = None
            branch_id = flask_session.get('branch_id')
            if branch_id:
                branch = session.query(Branch).filter_by(
                    branch_id=branch_id,
                    hospital_id=current_user.hospital_id
                ).first()
                if branch:
                    branch_state_code = branch.state_code

            # Fallback to hospital state
            hospital_state_code = hospital.state_code if hospital else None
            if not branch_state_code:
                branch_state_code = hospital_state_code

            # Get state name from code
            if patient_state_code:
                for state in INDIAN_STATES:
                    if state.get('value') == patient_state_code:
                        patient_state_name = state.get('label', patient_state_code)
                        break

            # Calculate interstate flag
            is_interstate = False
            if patient_state_code and branch_state_code:
                is_interstate = (patient_state_code != branch_state_code)

            current_app.logger.info(
                f"Patient state info: patient_state={patient_state_code}, "
                f"branch_state={branch_state_code}, interstate={is_interstate}"
            )

            return jsonify({
                'success': True,
                'patient_state_code': patient_state_code or '',
                'patient_state_name': patient_state_name or '',
                'hospital_state_code': branch_state_code or '',
                'is_interstate': is_interstate
            })

    except Exception as e:
        current_app.logger.error(f"Error getting patient state: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@billing_views_bp.route('/patient-view', methods=['GET'])
@login_required
def patient_invoice_view():
    """
    Patient-facing invoice preview pop-up
    Clean, read-only view for extended screen display
    Created: Nov 22, 2025
    URL: /invoice/patient-view (blueprint prefix /invoice + route /patient-view)
    """
    try:
        return render_template('billing/invoice_patient_view.html')
    except Exception as e:
        current_app.logger.error(f"Error loading patient invoice view: {str(e)}", exc_info=True)
        return f"Error loading patient view: {str(e)}", 500


# ==================== PROMO CODE VALIDATION API (Added 2025-11-25) ====================

@billing_views_bp.route('/web_api/promo-code/validate', methods=['POST'])
@login_required
def validate_promo_code_api():
    """
    Validate a manually entered promotion code.

    Used by billing staff when patient brings a personalized promo code
    (received via Email/WhatsApp).

    Request JSON:
        {
            "promo_code": "FESTIVE25",
            "patient_id": "uuid" (optional)
        }

    Response JSON:
        {
            "success": true/false,
            "valid": true/false,
            "error": "error message if invalid",
            "promotion": {
                "campaign_id": "uuid",
                "campaign_code": "FESTIVE25",
                "campaign_name": "Festive Season 25% Off",
                "description": "...",
                "discount_type": "percentage",
                "discount_value": 25.0,
                "applies_to": "all",
                "start_date": "01-Nov-2025",
                "end_date": "31-Dec-2025",
                ...
            }
        }

    Created: 2025-11-25
    """
    try:
        from app.services.discount_service import DiscountService

        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'valid': False,
                'error': 'No data provided'
            }), 400

        promo_code = data.get('promo_code', '').strip()
        patient_id = data.get('patient_id')

        if not promo_code:
            return jsonify({
                'success': False,
                'valid': False,
                'error': 'Promotion code is required'
            }), 400

        # Get hospital_id from current user
        hospital_id = current_user.hospital_id
        if not hospital_id:
            return jsonify({
                'success': False,
                'valid': False,
                'error': 'Hospital not configured for user'
            }), 400

        with get_db_session() as session:
            result = DiscountService.validate_promo_code(
                session=session,
                hospital_id=str(hospital_id),
                promo_code=promo_code,
                patient_id=patient_id,
                invoice_date=date.today()
            )

            return jsonify({
                'success': True,
                'valid': result['valid'],
                'error': result['error'],
                'promotion': result['promotion']
            })

    except Exception as e:
        current_app.logger.error(f"Error validating promo code: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'valid': False,
            'error': f'Server error: {str(e)}'
        }), 500


@billing_views_bp.route('/<uuid:invoice_id>/print', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def print_invoice(invoice_id):
    """Print invoice details"""
    try:
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        
        # Get patient details
        patient = None
        with get_db_session() as session:
            patient_record = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=invoice['patient_id']
            ).first()
            
            if patient_record:
                # Create detached copy before accessing properties
                patient_detached = get_detached_copy(patient_record)
                patient = {
                    'name': patient_detached.full_name,
                    'mrn': patient_detached.mrn,
                    'contact_info': patient_detached.contact_info,
                    'personal_info': patient_detached.personal_info
                }
        
        # Get hospital details
        hospital = None
        with get_db_session() as session:
            hospital_record = session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()
            
            if hospital_record:
                # Simplified hospital object for the template
                hospital = {
                    'name': hospital_record.name,
                    'address': hospital_record.address.get('full_address', '') if hospital_record.address else '',
                    'phone': hospital_record.contact_details.get('phone', '') if hospital_record.contact_details else '',
                    'email': hospital_record.contact_details.get('email', '') if hospital_record.contact_details else '',
                    'gst_registration_number': hospital_record.gst_registration_number
                }
        
        # Get payments for this invoice
        payments = []
        with get_db_session() as session:
            payment_records = session.query(PaymentDetail).filter_by(
                hospital_id=current_user.hospital_id,
                invoice_id=invoice_id
            ).all()
            
            payments = [get_entity_dict(payment) for payment in payment_records]
            
        # Add payments to invoice object
        invoice['payments'] = payments
        
        # Calculate GST summary by tax rates - NEW CODE FOR GST SUMMARY
        tax_groups = {}
        total_taxable = 0
        total_cgst = 0
        total_sgst = 0
        total_igst = 0
        
        # Process each line item
        if 'line_items' in invoice and invoice['line_items']:
            for item in invoice['line_items']:
                # Convert values to proper format
                gst_rate = float(item.get('gst_rate', 0))
                taxable_amount = float(item.get('taxable_amount', 0))
                cgst_amount = float(item.get('cgst_amount', 0))
                sgst_amount = float(item.get('sgst_amount', 0))
                igst_amount = float(item.get('igst_amount', 0))
                
                # Check if this is Doctor's Examination or exempt
                is_doctors_examination = item.get('item_name') == "Doctor's Examination and Treatment" or item.get('is_consolidated_prescription', False)
                
                # Skip items with no GST or exempt items
                if gst_rate <= 0 or is_doctors_examination:
                    continue
                
                # Use integer rate as key for grouping
                gst_rate_int = int(gst_rate)
                
                # Initialize tax group if it doesn't exist
                if gst_rate_int not in tax_groups:
                    tax_groups[gst_rate_int] = {
                        'taxable_value': 0,
                        'cgst_amount': 0,
                        'sgst_amount': 0,
                        'igst_amount': 0
                    }
                
                # Add to tax group
                tax_groups[gst_rate_int]['taxable_value'] += taxable_amount
                tax_groups[gst_rate_int]['cgst_amount'] += cgst_amount
                tax_groups[gst_rate_int]['sgst_amount'] += sgst_amount
                tax_groups[gst_rate_int]['igst_amount'] += igst_amount
                
                # Add to totals
                total_taxable += taxable_amount
                total_cgst += cgst_amount
                total_sgst += sgst_amount
                total_igst += igst_amount
        
        # Add summary to invoice
        invoice['tax_groups'] = tax_groups
        invoice['total_taxable'] = total_taxable
        invoice['total_cgst'] = total_cgst
        invoice['total_sgst'] = total_sgst
        invoice['total_igst'] = total_igst
        
        # Convert amount to words (utility function needed)
        amount_in_words = num2words(invoice['grand_total'])
        
        # Generate absolute URL for the logo
        logo_url = url_for('static', 
                        filename='uploads/hospital_logos/4ef72e18-e65d-4766-b9eb-0308c42485ca/medium_3da15aa2-4a2f-4ace-901b-d4d89d1ff66f.jpg', 
                        _external=True)

        return render_template(
            'billing/print_invoice.html',
            invoice=invoice,
            patient=patient,
            hospital=hospital,
            amount_in_words=amount_in_words,
                          logo_url=logo_url)  # Pass the URL to the template
    
    except Exception as e:
        flash(f'Error preparing invoice for printing: {str(e)}', 'error')
        logger.error(f"Error preparing invoice for printing: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))

@billing_views_bp.route('/group/<string:group_id>/print', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def print_all_invoices(group_id):
    """Print all invoices in a group"""
    try:
        # Find all invoices with the same group ID (middle part of invoice number)
        with get_db_session() as session:
            invoices = session.query(InvoiceHeader).filter(
                InvoiceHeader.hospital_id == current_user.hospital_id,
                InvoiceHeader.invoice_number.like(f"%/{group_id}/%")
            ).all()
            
            if not invoices:
                flash('No invoices found in this group.', 'error')
                return redirect(url_for('billing_views.invoice_list'))
            
            # Get the first invoice's patient ID to get patient details
            patient_id = invoices[0].patient_id
            
            # Get patient details
            patient = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=patient_id
            ).first()
            
            if not patient:
                patient_data = {'name': 'Unknown Patient', 'mrn': 'N/A'}
            else:
                patient_data = {
                    'name': patient.full_name,
                    'mrn': patient.mrn,
                    'contact_info': patient.contact_info,
                    'personal_info': patient.personal_info
                }
            
            # Get hospital details
            hospital_record = session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()
            
            if hospital_record:
                hospital = {
                    'name': hospital_record.name,
                    'address': hospital_record.address.get('full_address', '') if hospital_record.address else '',
                    'phone': hospital_record.contact_details.get('phone', '') if hospital_record.contact_details else '',
                    'email': hospital_record.contact_details.get('email', '') if hospital_record.contact_details else '',
                    'gst_registration_number': hospital_record.gst_registration_number
                }
            else:
                hospital = {'name': 'Hospital', 'address': '', 'phone': '', 'email': ''}
            
            # Create invoice objects suitable for the template
            invoice_objects = []
            for invoice in invoices:
                # Skip cancelled invoices
                if getattr(invoice, 'is_cancelled', False):
                    continue
                    
                invoice_dict = get_entity_dict(invoice)
                
                # Get line items and payments for this invoice
                line_items = []
                payments = []
                
                # Get related data if needed - simplified for this fix
                invoice_objects.append(invoice_dict)
            
            # Generate logo URL
            logo_url = url_for('static', 
                            filename='uploads/hospital_logos/4ef72e18-e65d-4766-b9eb-0308c42485ca/medium_3da15aa2-4a2f-4ace-901b-d4d89d1ff66f.jpg', 
                            _external=True)
            
            # Render combined printable invoice
            return render_template(
                'billing/print_all_invoices.html',
                invoices=invoice_objects,
                patient=patient_data,
                hospital=hospital,
                group_id=group_id,
                logo_url=logo_url
            )
    
    except Exception as e:
        flash(f'Error preparing invoices for printing: {str(e)}', 'error')
        logger.error(f"Error preparing invoices for printing: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))


@billing_views_bp.route('/consolidated_invoice/print_all/<uuid:parent_invoice_id>', methods=['GET'])
@login_required
def print_consolidated_invoices(parent_invoice_id):
    """
    Print all split invoices for a consolidated invoice

    Features:
    - Fetches all split invoices for the parent
    - Checks pharmacy license (branch → hospital fallback)
    - Consolidates prescription items if no license
    - Single PDF with patient header and footer only once
    """
    try:
        from app.services.billing_service import number_to_words
        from app.models.master import Hospital, Patient, Branch
        from app.models.transaction import InvoiceHeader, InvoiceLineItem
        from app.services.database_service import get_db_session, get_entity_dict

        with get_db_session() as session:
            # Get parent invoice to find all related invoices
            parent_invoice = session.query(InvoiceHeader).filter(
                InvoiceHeader.hospital_id == current_user.hospital_id,
                InvoiceHeader.invoice_id == parent_invoice_id
            ).first()

            if not parent_invoice:
                flash('Consolidated invoice not found.', 'error')
                return redirect(url_for('universal_views.universal_list', entity_type='consolidated_patient_invoices'))

            # Find all invoices in this split group (parent + children)
            # If this is a parent, get all children
            # If this is a child, get parent and all siblings
            if parent_invoice.parent_transaction_id:
                # This is a child, get parent
                actual_parent_id = parent_invoice.parent_transaction_id
            else:
                # This is the parent
                actual_parent_id = parent_invoice_id

            # Get all invoices (parent + children)
            all_invoices = session.query(InvoiceHeader).filter(
                InvoiceHeader.hospital_id == current_user.hospital_id,
                or_(
                    InvoiceHeader.invoice_id == actual_parent_id,
                    InvoiceHeader.parent_transaction_id == actual_parent_id
                )
            ).order_by(InvoiceHeader.split_sequence).all()

            if not all_invoices:
                flash('No invoices found for this consolidated invoice.', 'error')
                return redirect(url_for('universal_views.universal_list', entity_type='consolidated_patient_invoices'))

            # Get patient and hospital details
            patient_id = all_invoices[0].patient_id
            branch_id = all_invoices[0].branch_id

            patient = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=patient_id
            ).first()

            hospital = session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()

            branch = None
            if branch_id:
                branch = session.query(Branch).filter_by(
                    hospital_id=current_user.hospital_id,
                    branch_id=branch_id
                ).first()

            # Check pharmacy license (branch → hospital fallback)
            has_pharmacy_license = False
            if branch and branch.pharmacy_registration_number:
                # Check branch license validity
                if hasattr(branch, 'pharmacy_registration_valid_until') and branch.pharmacy_registration_valid_until:
                    if branch.pharmacy_registration_valid_until >= datetime.now(timezone.utc).date():
                        has_pharmacy_license = True
                elif hasattr(branch, 'pharmacy_reg_valid_until') and branch.pharmacy_reg_valid_until:
                    if branch.pharmacy_reg_valid_until >= datetime.now(timezone.utc).date():
                        has_pharmacy_license = True
            elif hospital and hospital.pharmacy_registration_number:
                # Fallback to hospital license
                if hasattr(hospital, 'pharmacy_registration_valid_until') and hospital.pharmacy_registration_valid_until:
                    if hospital.pharmacy_registration_valid_until >= datetime.now(timezone.utc).date():
                        has_pharmacy_license = True
                elif hasattr(hospital, 'pharmacy_reg_valid_until') and hospital.pharmacy_reg_valid_until:
                    if hospital.pharmacy_reg_valid_until >= datetime.now(timezone.utc).date():
                        has_pharmacy_license = True

            logger.info(f"Pharmacy license check: {has_pharmacy_license}")

            # Prepare invoice data
            invoices_data = []
            for invoice in all_invoices:
                # Skip cancelled invoices
                if getattr(invoice, 'is_cancelled', False):
                    continue

                invoice_dict = get_entity_dict(invoice)

                # Get line items
                line_items = session.query(InvoiceLineItem).filter_by(
                    hospital_id=current_user.hospital_id,
                    invoice_id=invoice.invoice_id
                ).all()

                invoice_dict['line_items'] = [get_entity_dict(item) for item in line_items]

                # Generate tax groups
                tax_groups = {}
                for item in invoice_dict['line_items']:
                    gst_rate = item.get('gst_rate', 0)
                    if gst_rate not in tax_groups:
                        tax_groups[gst_rate] = {
                            'taxable_value': 0,
                            'cgst_amount': 0,
                            'sgst_amount': 0,
                            'igst_amount': 0
                        }
                    tax_groups[gst_rate]['taxable_value'] += item.get('taxable_amount', 0)
                    tax_groups[gst_rate]['cgst_amount'] += item.get('cgst_amount', 0)
                    tax_groups[gst_rate]['sgst_amount'] += item.get('sgst_amount', 0)
                    tax_groups[gst_rate]['igst_amount'] += item.get('igst_amount', 0)

                invoice_dict['tax_groups'] = tax_groups
                invoice_dict['amount_in_words'] = number_to_words(invoice.grand_total)

                # If this is prescription invoice and no pharmacy license, consolidate
                if invoice.invoice_type == 'Prescription' and not has_pharmacy_license:
                    # Mark for consolidation
                    invoice_dict['consolidate_prescription'] = True
                    # Calculate total prescription amount
                    prescription_total = sum(item.get('line_total', 0) for item in invoice_dict['line_items'])
                    invoice_dict['prescription_consolidated_total'] = prescription_total
                else:
                    invoice_dict['consolidate_prescription'] = False

                invoices_data.append(invoice_dict)

            # Prepare patient data
            patient_data = {
                'name': patient.full_name if patient else 'Unknown',
                'mrn': patient.mrn if patient else 'N/A',
                'contact_info': patient.contact_info if patient else {}
            }

            # Prepare hospital data
            hospital_data = {
                'hospital_id': str(current_user.hospital_id),  # Add hospital_id for logo path
                'name': hospital.name if hospital else 'Hospital',
                'address': hospital.address.get('full_address', '') if hospital and hospital.address else '',
                'phone': hospital.contact_details.get('phone', '') if hospital and hospital.contact_details else '',
                'email': hospital.contact_details.get('email', '') if hospital and hospital.contact_details else '',
                'gst_registration_number': hospital.gst_registration_number if hospital else '',
                'pharmacy_registration_number': hospital.pharmacy_registration_number if hospital else ''
            }

            # Add pharmacy license validity
            if hospital:
                if hasattr(hospital, 'pharmacy_registration_valid_until'):
                    hospital_data['pharmacy_registration_valid_until'] = hospital.pharmacy_registration_valid_until
                elif hasattr(hospital, 'pharmacy_reg_valid_until'):
                    hospital_data['pharmacy_reg_valid_until'] = hospital.pharmacy_reg_valid_until

            # Render combined template
            return render_template(
                'billing/print_consolidated_invoices.html',
                invoices=invoices_data,
                patient=patient_data,
                hospital=hospital_data,
                has_pharmacy_license=has_pharmacy_license,
                parent_invoice_id=str(actual_parent_id),
                logo_url=None  # Can be enhanced later
            )

    except Exception as e:
        flash(f'Error preparing consolidated invoices for printing: {str(e)}', 'error')
        logger.error(f"Error preparing consolidated invoices for printing: {str(e)}", exc_info=True)
        return redirect(url_for('universal_views.universal_list', entity_type='consolidated_patient_invoices'))


@billing_views_bp.route('/create_diagnostic', methods=['GET', 'POST'])
@login_required
def create_invoice_diagnostic():
    """Diagnostic view for troubleshooting form submission"""
    logger.info(f"DIAGNOSTIC: Request method: {request.method}")
    
    if request.method == 'POST':
        logger.info("DIAGNOSTIC: POST request received")
        logger.info(f"DIAGNOSTIC: Form data: {request.form}")
        logger.info(f"DIAGNOSTIC: Headers: {request.headers}")
        return jsonify({
            "message": "Form data received",
            "form_data": {k: v for k, v in request.form.items()},
            "csrf_token_present": "csrf_token" in request.form,
            "patient_id_present": "patient_id" in request.form,
            "patient_id_value": request.form.get("patient_id", "not found")
        })
    
    # For GET requests, use render_template instead of a raw string
    from flask import render_template_string
    
    # Generate CSRF token
    from flask_wtf.csrf import generate_csrf
    csrf_token = generate_csrf()
    
    return render_template_string("""
    <html>
    <body>
        <h1>Diagnostic Form</h1>
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <input type="hidden" name="patient_id" value="test-patient-id">
            <button type="submit">Submit Test Form</button>
        </form>
        <script>
            document.querySelector('form').addEventListener('submit', function(e) {
                console.log("Form submitted via event listener");
            });
            
            document.querySelector('button').addEventListener('click', function(e) {
                console.log("Button clicked");
                // Don't prevent default
            });
        </script>
    </body>
    </html>
    """, csrf_token=csrf_token)

# Add to your billing_views.py

@billing_views_bp.route('/<uuid:invoice_id>/send-email', methods=['POST'])
@login_required
@permission_required('billing', 'view')
def send_invoice_email(invoice_id):
    """Send invoice via email to the patient"""
    try:
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        
        # Get patient details
        with get_db_session() as session:
            patient = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=invoice['patient_id']
            ).first()
            
            if not patient:
                flash("Patient information not found.", "error")
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
            
            # Check if email is verified
            email = patient.contact_info.get('email') if patient.contact_info else None
            is_email_verified = patient.contact_info.get('is_email_verified', False) if patient.contact_info else False
            
            if not email or not is_email_verified:
                flash("Patient does not have a verified email address.", "error")
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
            
            # Generate PDF invoice
            pdf_data = generate_invoice_pdf(invoice_id)
                       
            hospital = session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()
            
            hospital_name = hospital.name if hospital else "Our Clinic"
            
            subject = f"Invoice #{invoice['invoice_number']} from {hospital_name}"
            body = f"""
            Dear {patient.full_name},
            
            Please find attached your invoice #{invoice['invoice_number']} dated {invoice['invoice_date'].strftime('%d-%b-%Y')}.
            
            Total Amount: {invoice['currency_code']} {invoice['grand_total']}
            
            Thank you for choosing {hospital_name} for your healthcare needs.
            
            Regards,
            {hospital_name} Team
            """
            
            send_email_with_attachment(
                recipient_email=email,
                subject=subject,
                body=body,
                attachment_data=pdf_data,
                attachment_name=f"Invoice_{invoice['invoice_number']}.pdf",
                attachment_type='application/pdf'
            )
            
            flash("Invoice has been sent via email successfully.", "success")
            
    except Exception as e:
        flash(f"Error sending invoice via email: {str(e)}", "error")
        logger.error(f"Error sending invoice via email: {str(e)}", exc_info=True)
    
    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))

@billing_views_bp.route('/<uuid:invoice_id>/send-whatsapp', methods=['POST'])
@login_required
@permission_required('billing', 'view')
def send_invoice_whatsapp(invoice_id):
    """Send invoice via WhatsApp to the patient"""
    try:
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        
        # Get patient details
        with get_db_session() as session:
            patient = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=invoice['patient_id']
            ).first()
            
            if not patient:
                flash("Patient information not found.", "error")
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
            
            # Check if phone is verified
            phone = patient.contact_info.get('phone') if patient.contact_info else None
            is_phone_verified = patient.contact_info.get('is_phone_verified', False) if patient.contact_info else False
            
            if not phone or not is_phone_verified:
                flash("Patient does not have a verified phone number.", "error")
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
            
            # Generate PDF invoice
            pdf_data = generate_invoice_pdf(invoice_id)
            
            # Store the PDF temporarily and get a URL
            pdf_url = store_temporary_file(pdf_data, f"Invoice_{invoice['invoice_number']}.pdf")
                       
            hospital = session.query(Hospital).filter_by(
                hospital_id=current_user.hospital_id
            ).first()
            
            hospital_name = hospital.name if hospital else "Our Clinic"
            
            message = f"""
            Dear {patient.full_name},
            
            Your invoice #{invoice['invoice_number']} dated {invoice['invoice_date'].strftime('%d-%b-%Y')} is ready.
            
            Total Amount: {invoice['currency_code']} {invoice['grand_total']}
            
            You can view your invoice here: {pdf_url}
            
            Thank you for choosing {hospital_name} for your healthcare needs.
            """
            
            send_whatsapp_message(phone, message)
            
            flash("Invoice has been sent via WhatsApp successfully.", "success")
            
    except Exception as e:
        flash(f"Error sending invoice via WhatsApp: {str(e)}", "error")
        logger.error(f"Error sending invoice via WhatsApp: {str(e)}", exc_info=True)
    
    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))

@billing_views_bp.route('/advance/create', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'create')
def create_advance_payment_view():
    """View for creating a new advance payment"""
    controller = AdvancePaymentController()
    return controller.handle_request()

@billing_views_bp.route('/advance/patient/<uuid:patient_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def view_patient_advances(patient_id):
    """View patient's advance payment history"""
    try:
        # Get patient details
        logger.info(f"Viewing advances for patient: {patient_id}")

        with get_db_session() as session:
            patient = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=patient_id
            ).first()
            
            if not patient:
                flash("Patient not found", "error")
                return redirect(url_for('billing_views.invoice_list'))
            
            # Create detached copy
            patient_data = {
                'patient_id': str(patient.patient_id),
                'name': patient.full_name,
                'mrn': patient.mrn,
                'contact_info': patient.contact_info
            }
        
        # Get advance payments for patient
        advance_payments = get_patient_advance_payments(
            hospital_id=current_user.hospital_id,
            patient_id=patient_id
        )
        
        # Get current advance balance
        advance_balance = get_patient_advance_balance(
            hospital_id=current_user.hospital_id,
            patient_id=patient_id
        )
        
        # Get menu items for dashboard
        menu_items = get_menu_items(current_user)
        
        return render_template(
            'billing/patient_advances.html',
            patient=patient_data,
            advance_payments=advance_payments,
            advance_balance=advance_balance,
            menu_items=menu_items,
            page_title=f"Advance Payments - {patient_data['name']}"
        )
        
    except Exception as e:
        flash(f"Error retrieving advance payments: {str(e)}", "error")
        logger.error(f"Error retrieving advance payments: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))

@billing_views_bp.route('/advance/apply/<uuid:invoice_id>', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'update')
def apply_advance_view(invoice_id):
    """View for applying advance payment to an invoice"""
    try:
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        
        # Get patient details
        with get_db_session() as session:
            patient = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=invoice['patient_id']
            ).first()
            
            if not patient:
                flash("Patient information not found", "error")
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
            
            # Create detached copy
            patient_data = {
                'patient_id': str(patient.patient_id),
                'name': patient.full_name,
                'mrn': patient.mrn,
                'contact_info': patient.contact_info
            }
        
        # Get current advance balance
        advance_balance = get_patient_advance_balance(
            hospital_id=current_user.hospital_id,
            patient_id=invoice['patient_id']
        )
        
        # Check if there's an available balance
        if advance_balance <= 0:
            flash("No advance payment available for this patient", "warning")
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        
        # Create form for advance application
        class ApplyAdvanceForm(FlaskForm):
            invoice_id = HiddenField('Invoice ID', validators=[DataRequired()])
            amount = DecimalField('Amount to Apply', validators=[
                DataRequired(),
                NumberRange(min=0.01, message="Amount must be greater than zero")
            ])
            notes = TextAreaField('Notes', validators=[Optional(), Length(max=255)])
            
            def validate_amount(self, field):
                if field.data > advance_balance:
                    raise ValidationError(f"Amount exceeds available advance balance ({advance_balance})")
                
                if field.data > invoice['balance_due']:
                    raise ValidationError(f"Amount exceeds invoice balance due ({invoice['balance_due']})")
        
        # Create form instance
        form = ApplyAdvanceForm()
        form.invoice_id.data = str(invoice_id)
        
        # Pre-populate amount with minimum of advance balance and invoice balance due
        if request.method == 'GET':
            form.amount.data = min(advance_balance, invoice['balance_due'])
        
        # Handle form submission
        if request.method == 'POST':
            if form.validate_on_submit():
                try:
                    # Apply advance payment
                    adjustment = apply_advance_payment(
                        hospital_id=current_user.hospital_id,
                        invoice_id=invoice_id,
                        amount=form.amount.data,
                        adjustment_date=datetime.now(timezone.utc),
                        notes=form.notes.data,
                        current_user_id=current_user.user_id
                    )
                    
                    flash(f"Successfully applied {form.amount.data} from advance payment", "success")
                    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
                    
                except Exception as e:
                    flash(f"Error applying advance payment: {str(e)}", "error")
                    logger.error(f"Error applying advance payment: {str(e)}", exc_info=True)
        
        # Get menu items for dashboard
        menu_items = get_menu_items(current_user)
        
        return render_template(
            'billing/apply_advance.html',
            form=form,
            invoice=invoice,
            patient=patient_data,
            advance_balance=advance_balance,
            menu_items=menu_items,
            page_title="Apply Advance Payment"
        )
        
    except Exception as e:
        flash(f"Error processing advance payment application: {str(e)}", "error")
        logger.error(f"Error processing advance payment application: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))

@billing_views_bp.route('/advance/list', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def advance_payment_list():
    """View list of patients with advance payments"""
    
    try:
        # Get patients with advance payments
        with get_db_session() as session:
            # Get patients with advance balance > 0
            query = session.query(
                Patient,
                func.sum(PatientAdvancePayment.available_balance).label('total_balance')
            ).join(
                PatientAdvancePayment,
                and_(
                    Patient.patient_id == PatientAdvancePayment.patient_id,
                    Patient.hospital_id == PatientAdvancePayment.hospital_id
                )
            ).filter(
                Patient.hospital_id == current_user.hospital_id,
                PatientAdvancePayment.is_active == True,
                PatientAdvancePayment.available_balance > 0
            ).group_by(
                Patient.patient_id
            ).order_by(
                func.sum(PatientAdvancePayment.available_balance).desc()
            )
            
            # Log the query for debugging
            logger.info(f"Running query: {str(query)}")
            
            # Execute the query
            patients_with_advances = query.all()
            
            # Create patient data list
            patients_data = []
            for result in patients_with_advances:
                patient = result[0]  # First element is the Patient object
                total_balance = result[1]  # Second element is the sum
                
                patients_data.append({
                    'patient_id': str(patient.patient_id),
                    'name': patient.full_name,  # Using the full_name property
                    'mrn': patient.mrn,
                    'advance_balance': float(total_balance)
                })
        
        # Get menu items for dashboard
        menu_items = get_menu_items(current_user)
        
        return render_template(
            'billing/advance_payment_list.html',
            patients=patients_data,
            menu_items=menu_items,
            page_title="Advance Payments"
        )

    except Exception as e:
        flash(f"Error retrieving advance payments: {str(e)}", "error")
        logger.error(f"Error retrieving advance payments: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))


# =============================================================================
# UNIVERSAL ENGINE MIGRATION ROUTES (Phase 4/5)
# =============================================================================
# The following routes redirect old billing routes to Universal Engine
# These maintain backward compatibility while migrating to Universal Engine

@billing_views_bp.route('/universal/list', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def universal_invoice_list():
    """
    Redirect to Universal Engine invoice list

    NEW ROUTE: Use this for Universal Engine-powered invoice list
    Provides enhanced filtering, sorting, and export capabilities
    """
    # Forward query parameters to Universal Engine
    return redirect(url_for('universal_views.universal_list_view',
                          entity_type='patient_invoices',
                          **request.args))


@billing_views_bp.route('/universal/<uuid:invoice_id>', methods=['GET'])
@login_required
@permission_required('billing', 'view')
def universal_view_invoice(invoice_id):
    """
    Redirect to Universal Engine invoice detail view

    NEW ROUTE: Use this for Universal Engine-powered invoice detail
    Provides tabbed interface with line items, payments, and GL posting info
    """
    return redirect(url_for('universal_views.universal_detail_view',
                          entity_type='patient_invoices',
                          item_id=invoice_id))


# ==================== VIP ELIGIBILITY CHECK API (Added 2025-11-29) ====================

@billing_views_bp.route('/web_api/vip-eligibility/<uuid:patient_id>', methods=['GET'])
@login_required
def check_vip_eligibility_api(patient_id):
    """
    Check if a patient is VIP eligible and return VIP campaign details.

    VIP patients are identified by is_special_group = True in patients table.
    VIP campaign is configured in hospital_settings (category: 'billing', key: 'vip_discount').

    Response JSON:
        {
            "success": true,
            "is_vip": true/false,
            "auto_apply_default": true/false,
            "vip_campaign": {
                "campaign_id": "uuid",
                "campaign_code": "VIP2025",
                "campaign_name": "VIP Customer Special",
                "discount_type": "percentage",
                "discount_value": 20.0,
                ...
            } or null
        }
    """
    try:
        from app.models import Patient, HospitalSettings
        from app.models.master import PromotionCampaign

        hospital_id = current_user.hospital_id

        with get_db_session() as session:
            # Check if patient is VIP (is_special_group = True)
            patient = session.query(Patient).filter_by(patient_id=patient_id).first()

            if not patient:
                return jsonify({
                    'success': False,
                    'error': 'Patient not found'
                }), 404

            is_vip = getattr(patient, 'is_special_group', False) or False

            if not is_vip:
                return jsonify({
                    'success': True,
                    'is_vip': False,
                    'auto_apply_default': False,
                    'vip_campaign': None
                })

            # Get VIP discount config from hospital settings
            billing_settings = session.query(HospitalSettings).filter_by(
                hospital_id=hospital_id,
                category='billing'
            ).first()

            vip_config = {}
            if billing_settings and billing_settings.settings:
                vip_config = billing_settings.settings.get('vip_discount', {})

            if not vip_config.get('enabled', False):
                return jsonify({
                    'success': True,
                    'is_vip': True,
                    'auto_apply_default': False,
                    'vip_campaign': None,
                    'message': 'VIP discount is disabled in hospital settings'
                })

            # Get VIP campaign details
            campaign_code = vip_config.get('campaign_code', 'VIP2025')
            campaign = session.query(PromotionCampaign).filter(
                PromotionCampaign.hospital_id == hospital_id,
                PromotionCampaign.campaign_code == campaign_code,
                PromotionCampaign.is_active == True,
                PromotionCampaign.is_deleted == False,
                PromotionCampaign.status == 'approved',
                PromotionCampaign.start_date <= date.today(),
                PromotionCampaign.end_date >= date.today()
            ).first()

            if not campaign:
                return jsonify({
                    'success': True,
                    'is_vip': True,
                    'auto_apply_default': False,
                    'vip_campaign': None,
                    'message': f'VIP campaign {campaign_code} not found or inactive'
                })

            return jsonify({
                'success': True,
                'is_vip': True,
                'auto_apply_default': vip_config.get('auto_apply_default', False),
                'vip_campaign': {
                    'campaign_id': str(campaign.campaign_id),
                    'campaign_code': campaign.campaign_code,
                    'campaign_name': campaign.campaign_name,
                    'description': campaign.description,
                    'discount_type': campaign.discount_type,
                    'discount_value': float(campaign.discount_value),
                    'applies_to': campaign.applies_to,
                    'start_date': campaign.start_date.strftime('%d-%b-%Y'),
                    'end_date': campaign.end_date.strftime('%d-%b-%Y')
                }
            })

    except Exception as e:
        logger.error(f"Error checking VIP eligibility: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== STAFF DISCRETIONARY CONFIG API (Added 2025-11-29) ====================

@billing_views_bp.route('/web_api/staff-discretionary-config/<uuid:hospital_id>', methods=['GET'])
@login_required
def get_staff_discretionary_config_api(hospital_id):
    """
    Get staff discretionary discount configuration from hospital settings.

    Response JSON:
        {
            "enabled": true/false,
            "code": "SKINSPIRESPECIAL",
            "name": "Staff Discretionary Discount",
            "max_percent": 5,
            "default_percent": 1,
            "options": [1, 2, 3, 4, 5],
            "requires_note": false,
            "stacking_mode": "incremental"
        }
    """
    try:
        from app.models import HospitalSettings

        with get_db_session() as session:
            billing_settings = session.query(HospitalSettings).filter_by(
                hospital_id=hospital_id,
                category='billing'
            ).first()

            if billing_settings and billing_settings.settings:
                discretionary_config = billing_settings.settings.get('staff_discretionary_discount', {})
                if discretionary_config:
                    return jsonify(discretionary_config)

            # Return default config if not configured
            return jsonify({
                'enabled': True,
                'code': 'SKINSPIRESPECIAL',
                'name': 'Staff Discretionary Discount',
                'max_percent': 5,
                'default_percent': 1,
                'options': [1, 2, 3, 4, 5],
                'requires_note': False,
                'stacking_mode': 'incremental'
            })

    except Exception as e:
        logger.error(f"Error getting staff discretionary config: {str(e)}")
        return jsonify({
            'enabled': True,
            'code': 'SKINSPIRESPECIAL',
            'name': 'Staff Discretionary Discount',
            'max_percent': 5,
            'default_percent': 1,
            'options': [1, 2, 3, 4, 5],
            'requires_note': False,
            'stacking_mode': 'incremental'
        })


# =============================================================================
# DEPRECATION NOTES
# =============================================================================
"""
MIGRATION PLAN:

Old Routes (to be deprecated):
- /invoice/list -> Currently uses billing_service.search_invoices()
- /invoice/<uuid:invoice_id> -> Currently uses billing_service.get_invoice_by_id()

New Routes (Universal Engine):
- /universal/patient_invoices/list -> Uses PatientInvoiceService.search_data()
- /universal/patient_invoices/detail/<item_id> -> Uses PatientInvoiceService.get_by_id()

Migration Steps:
1. ✅ Phase 1-3: Created PatientInvoiceView, PatientInvoiceService, Configuration
2. ✅ Phase 4: Updated menu to point to Universal Engine routes
3. ✅ Phase 5: Added redirect routes for backward compatibility
4. TODO: Update internal links to use Universal Engine routes
5. TODO: Deprecate old routes after confirming no usage

Backward Compatibility Routes:
- /invoice/universal/list -> Redirects to /universal/patient_invoices/list
- /invoice/universal/<uuid> -> Redirects to /universal/patient_invoices/detail/<uuid>

Notes:
- Create, Edit, Delete, Payment routes remain in billing_views.py
- Only List and Detail views are migrated to Universal Engine
- All business logic functions remain in billing_service.py
"""