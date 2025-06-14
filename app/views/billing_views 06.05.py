# app/views/billing_views.py

import uuid
import json
import logging
logger = logging.getLogger('app.services.billing_service')
from datetime import datetime, timezone, timedelta, date
import decimal
from decimal import Decimal, InvalidOperation
from num2words import num2words
from sqlalchemy import func, and_

from flask import current_app as app
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session as flask_session
from flask_login import login_required, current_user
from flask import url_for as flask_url_for
from urllib.parse import urlencode  # Use standard library for URL encoding

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, DateField, DecimalField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError

from app.forms.billing_forms import InvoiceForm, PaymentForm, AdvancePaymentForm
from app.services.billing_service import (
    create_invoice, 
    get_invoice_by_id,
    record_payment,
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
from app.models.transaction import User, InvoiceHeader, Inventory, PaymentDetail, PatientAdvancePayment, AdvanceAdjustment

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
    
    # Clear any cached patient ID to ensure fresh selection each time
    if 'temp_patient_id' in flask_session:
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

            # Add patients to choices
            patient_choices.extend([
                (str(patient.patient_id), f"{patient.full_name} - {patient.mrn or 'No MRN'}") 
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
            return render_template(
                'billing/create_invoice.html',
                form=form,
                branches=branches,
                menu_items=menu_items,
                page_title="Create Invoice",
                auth_token=auth_token
            )
        
        # Check for patient_id in form data or data attributes
        patient_id = request.form.get('patient_id')
        patient_name = request.form.get('patient_name')
        
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
                    if len(name_parts) >= 2:
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
                line_items = process_line_items(form)
                
                # Convert invoice_date to datetime with timezone
                invoice_date = form.invoice_date.data
                invoice_date = datetime.combine(invoice_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                
                invoice_data = {
                    'hospital_id': current_user.hospital_id,
                    'branch_id': form.branch_id.data,
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
                
                # Single invoice case
                if len(result['invoices']) == 1:
                    invoice = result['invoices'][0]
                    flash(f"Invoice {invoice['invoice_number']} created successfully", "success")
                    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice['invoice_id']))
                
                # Multiple invoices case
                if len(result['invoices']) > 1:
                    flash(f"{len(result['invoices'])} invoices created successfully", "success")
                    # Redirect to invoice list filtered for this patient
                    return redirect(url_for('billing_views.list_invoices', 
                                        patient_id=invoice_data['patient_id'],
                                        created_multiple=True))
                
                # No invoices created
                flash("No invoices were created. Please check the form and try again.", "warning")
                return render_template('billing/create_invoice.html', form=form, auth_token=auth_token)
                
            except Exception as e:
                current_app.logger.error(f"Error creating invoice: {str(e)}")
                flash(f"Error creating invoice: {str(e)}", "error")
                return render_template('billing/create_invoice.html', form=form, auth_token=auth_token)
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
                                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice['invoice_id']))
                            
                            # Multiple invoices case
                            if len(result['invoices']) > 1:
                                flash(f"{len(result['invoices'])} invoices created successfully", "success")
                                # Fix: Use the correct route name (invoice_list instead of list_invoices)
                                # and pass parameters as query string
                                return redirect(url_for('billing_views.invoice_list') + 
                                            f"?patient_id={invoice_data['patient_id']}&created_multiple=true")
                        except Exception as e:
                            current_app.logger.error(f"Error creating invoice: {str(e)}")
                            flash(f"Error creating invoice: {str(e)}", "error")
                
                # Log form errors
                current_app.logger.error(f"Form validation failed with errors: \n{form.errors}")
            
            # Normal case or form validation failed
            return render_template(
                'billing/create_invoice.html',
                form=form,
                branches=branches,
                menu_items=menu_items,
                page_title="Create Invoice",
                auth_token=auth_token  # Pass token to template
            )

    return render_template(
        'billing/create_invoice.html',
        form=form,
        branches=branches,
        menu_items=menu_items,
        page_title="Create Invoice",
        auth_token=auth_token  # Pass token to template
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
        
        # Get all payments for all invoices for display in the payment history tab
        all_payments = []
        try:
            # Get invoice IDs for all related invoices
            invoice_ids = [invoice_id]
            for related in related_invoices:
                if 'invoice_id' in related:
                    try:
                        invoice_ids.append(uuid.UUID(related['invoice_id']))
                    except Exception as e:
                        logger.warning(f"Failed to convert invoice_id {related['invoice_id']} to UUID: {str(e)}")
            
            # Get all payments for these invoices
            with get_db_session() as session:
                payment_records = session.query(PaymentDetail).filter(
                    PaymentDetail.hospital_id == current_user.hospital_id,
                    PaymentDetail.invoice_id.in_(invoice_ids)
                ).order_by(PaymentDetail.payment_date.desc()).all()
                
                all_payments = [get_detached_copy(payment) for payment in payment_records]
        except Exception as e:
            logger.error(f"Error getting all payments: {str(e)}", exc_info=True)
        
        # Make sure values are properly converted to float for the template - create new variables to avoid any reference issues
        final_total_amount = float(total_amount)
        final_total_balance_due = float(total_balance_due)
        final_total_paid_amount = float(total_paid_amount)
        
        # Add payments to the invoice dictionary
        invoice['payments'] = all_payments

        return render_template(
            'billing/view_invoice.html',
            invoice=invoice,
            patient=patient,
            payment_form=payment_form,
            menu_items=menu_items,
            page_title=f"Invoice #{invoice['invoice_number']}",
            is_consolidated_prescription=invoice.get('is_consolidated_prescription', False),
            related_invoices=related_invoices,
            all_payments=all_payments,

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

@billing_views_bp.route('/<uuid:invoice_id>/payment', methods=['GET', 'POST'])
@login_required
@permission_required('billing', 'update')
def record_invoice_payment(invoice_id):
    """Record payment for an invoice"""
    try:
        # Check if this is a multi-invoice payment
        pay_all = request.args.get('pay_all') == 'true'
        
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        
        # Ensure we have fresh balance data from the database
        with get_db_session() as session:
            fresh_invoice = session.query(InvoiceHeader).filter_by(
                hospital_id=current_user.hospital_id,
                invoice_id=invoice_id
            ).first()
            
            if fresh_invoice:
                # Update the invoice with fresh balance data
                invoice['balance_due'] = float(fresh_invoice.balance_due)
                invoice['paid_amount'] = float(fresh_invoice.paid_amount)
                logger.info(f"Using fresh balance due: {invoice['balance_due']} for payment form")

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
        
        # Get related invoices if pay_all is true
        related_invoices = []
        total_balance_due = float(invoice['balance_due'])
        total_amount = float(invoice['grand_total'])
        total_paid_amount = float(invoice['paid_amount'])
        
        if pay_all:
            # Similar logic as in view_invoice to get related invoices
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
                        InvoiceHeader.invoice_id != invoice_id,
                        InvoiceHeader.is_cancelled == False,  # Exclude cancelled invoices
                        InvoiceHeader.balance_due > 0  # Only include those with balance due
                    ).all()
                    
                    # Calculate total balance due including related invoices
                    for related in related_records:
                        related_dict = get_entity_dict(related)
                        related_invoices.append(related_dict)
                        total_balance_due += float(related_dict['balance_due'])
                        total_amount += float(related_dict['grand_total'])
                        total_paid_amount += float(related_dict['paid_amount'])
        
        # Get available advance balance
        advance_balance = get_patient_advance_balance(
            hospital_id=current_user.hospital_id,
            patient_id=invoice['patient_id']
        )
        
        # Create payment form
        payment_form = PaymentForm()
        payment_form.invoice_id.data = str(invoice_id)

        # Get menu items for dashboard
        menu_items = get_menu_items(current_user)
        
        # Handle GET request - display the form
        if request.method == 'GET':
            # Set today's date as default
            payment_form.payment_date.data = datetime.now().date()
            
            logger.info(f"Using fresh balance due: {invoice['balance_due']} for payment form")
            logger.info(f"Advance balance: {advance_balance}")

            return render_template(
                'billing/payment_form_page.html',
                invoice=invoice,
                patient=patient,
                payment_form=payment_form,
                menu_items=menu_items,
                page_title=f"Record Payment for Invoice #{invoice['invoice_number']}",
                related_invoices=related_invoices if pay_all else None,
                total_balance_due=total_balance_due,
                total_amount=total_amount,
                total_paid_amount=total_paid_amount,
                pay_all=pay_all,
                advance_balance=advance_balance
            )
                  
        # Handle POST request - process the form
        elif request.method == 'POST':
            # Check if using advance payment
            use_advance = request.form.get('use_advance') == 'true'
            advance_amount = Decimal(request.form.get('advance_amount', '0'))
            
            if use_advance and advance_amount > 0:
                try:
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
                        
                    # If there's still balance due, continue with regular payment processing
                    invoice = updated_invoice
                    
                except Exception as e:
                    flash(f"Error applying advance payment: {str(e)}", "error")
                    logger.error(f"Error applying advance payment: {str(e)}", exc_info=True)
            
            # Proceed with regular payment processing
            # Check if form data is valid manually (avoids validate_on_submit issue)
            is_valid = payment_form.is_submitted() and payment_form.validate()
            
            if is_valid:
                try:
                    # Get form data
                    invoice_id = payment_form.invoice_id.data
                    payment_date = payment_form.payment_date.data
                    cash_amount = payment_form.cash_amount.data or Decimal('0')
                    credit_card_amount = payment_form.credit_card_amount.data or Decimal('0')
                    debit_card_amount = payment_form.debit_card_amount.data or Decimal('0')
                    upi_amount = payment_form.upi_amount.data or Decimal('0')
                    card_number_last4 = payment_form.card_number_last4.data
                    card_type = payment_form.card_type.data
                    upi_id = payment_form.upi_id.data
                    reference_number = payment_form.reference_number.data
                    
                    # Calculate total
                    total_amount = cash_amount + credit_card_amount + debit_card_amount + upi_amount
                    
                    # Validate payment amount
                    if total_amount <= 0:
                        flash('Payment amount must be greater than zero.', 'error')
                        # Render the template instead of redirecting
                        menu_items = get_menu_items(current_user)
                        return render_template(
                            'billing/payment_form_page.html',
                            invoice=invoice,
                            patient=patient,
                            payment_form=payment_form,
                            menu_items=menu_items,
                            page_title=f"Record Payment for Invoice #{invoice['invoice_number']}",
                            related_invoices=related_invoices if pay_all else None,
                            total_balance_due=total_balance_due,
                            pay_all=pay_all,
                            advance_balance=advance_balance
                        )
                    
                    # If pay_all is true, distribute payment across invoices
                    if pay_all and related_invoices:
                        # Get selected invoice IDs from form
                        selected_invoice_ids = request.form.getlist('invoice_ids')
                        
                        if not selected_invoice_ids:
                            flash('No invoices selected for payment.', 'error')
                            # Render the template instead of redirecting
                            menu_items = get_menu_items(current_user)
                            return render_template(
                                'billing/payment_form_page.html',
                                invoice=invoice,
                                patient=patient,
                                payment_form=payment_form,
                                menu_items=menu_items,
                                page_title=f"Record Payment for Invoice #{invoice['invoice_number']}",
                                related_invoices=related_invoices if pay_all else None,
                                total_balance_due=total_balance_due,
                                pay_all=pay_all,
                                advance_balance=advance_balance
                            )
                        
                        # Calculate the total balance due for selected invoices
                        selected_balance_due = Decimal('0')
                        
                        # Add the current invoice if selected
                        if str(invoice_id) in selected_invoice_ids:
                            selected_balance_due += Decimal(str(invoice['balance_due']))
                        
                        # Add related invoices if selected
                        for related in related_invoices:
                            if related['invoice_id'] in selected_invoice_ids:
                                selected_balance_due += Decimal(str(related['balance_due']))
                        
                        # Add debug logging
                        logger.info(f"DEBUG - Selected invoice IDs: {selected_invoice_ids}")
                        logger.info(f"DEBUG - Payment amount: {total_amount}")
                        logger.info(f"DEBUG - Selected balance due: {selected_balance_due}")
                        
                        # Instead of validation - let's always proceed but with a warning
                        if total_amount > selected_balance_due:
                            flash(f'Payment amount ({total_amount}) exceeds selected balance due ({selected_balance_due}). Excess will be treated as advance.', 'warning')
                            logger.warning(f"Payment amount ({total_amount}) exceeds selected balance due ({selected_balance_due}). Treating as advance.")
                        
                        # Distribute payment proportionally
                        remaining_payment = total_amount
                        payment_results = []
                        
                        # Always include the current invoice first if selected
                        if str(invoice_id) in selected_invoice_ids:
                            # Process this invoice first
                            invoice_to_pay = invoice
                            balance = Decimal(str(invoice['balance_due']))
                            
                            # Calculate payment for this invoice
                            invoice_payment = min(remaining_payment, balance)
                            
                            if invoice_payment > 0:
                                # Calculate proportional amounts for each payment method
                                proportion = invoice_payment / total_amount
                                inv_cash = cash_amount * proportion
                                inv_credit = credit_card_amount * proportion
                                inv_debit = debit_card_amount * proportion
                                inv_upi = upi_amount * proportion
                                
                                # Record payment for this invoice
                                try:
                                    result = record_payment(
                                        hospital_id=current_user.hospital_id,
                                        invoice_id=uuid.UUID(invoice_id),
                                        payment_date=payment_date,
                                        cash_amount=inv_cash,
                                        credit_card_amount=inv_credit,
                                        debit_card_amount=inv_debit,
                                        upi_amount=inv_upi,
                                        card_number_last4=card_number_last4,
                                        card_type=card_type,
                                        upi_id=upi_id,
                                        reference_number=reference_number,
                                        # Enable excess payment handling
                                        handle_excess=True,
                                        recorded_by=current_user.user_id
                                    )
                                    
                                    payment_results.append({
                                        'invoice_id': invoice_id,
                                        'invoice_number': invoice['invoice_number'],
                                        'amount': invoice_payment,
                                        'success': bool(result)
                                    })
                                    
                                    remaining_payment -= invoice_payment
                                except Exception as e:
                                    logger.error(f"Error recording payment for invoice {invoice_id}: {str(e)}", exc_info=True)
                                    payment_results.append({
                                        'invoice_id': invoice_id,
                                        'invoice_number': invoice['invoice_number'],
                                        'amount': invoice_payment,
                                        'success': False,
                                        'error': str(e)
                                    })
                        
                        # Process related invoices if selected
                        for related in related_invoices:
                            if related['invoice_id'] in selected_invoice_ids and remaining_payment > 0:
                                # Calculate payment for this invoice
                                balance = Decimal(str(related['balance_due']))
                                invoice_payment = min(remaining_payment, balance)
                                
                                if invoice_payment > 0:
                                    # Calculate proportional amounts for each payment method
                                    proportion = invoice_payment / total_amount
                                    inv_cash = cash_amount * proportion
                                    inv_credit = credit_card_amount * proportion
                                    inv_debit = debit_card_amount * proportion
                                    inv_upi = upi_amount * proportion
                                    
                                    # Record payment for this invoice
                                    try:
                                        result = record_payment(
                                            hospital_id=current_user.hospital_id,
                                            invoice_id=uuid.UUID(related['invoice_id']),
                                            payment_date=payment_date,
                                            cash_amount=inv_cash,
                                            credit_card_amount=inv_credit,
                                            debit_card_amount=inv_debit,
                                            upi_amount=inv_upi,
                                            card_number_last4=card_number_last4,
                                            card_type=card_type,
                                            upi_id=upi_id,
                                            reference_number=reference_number,
                                            # Enable excess payment handling
                                            handle_excess=True,
                                            recorded_by=current_user.user_id
                                        )
                                        
                                        payment_results.append({
                                            'invoice_id': related['invoice_id'],
                                            'invoice_number': related['invoice_number'],
                                            'amount': invoice_payment,
                                            'success': bool(result)
                                        })
                                        
                                        remaining_payment -= invoice_payment
                                    except Exception as e:
                                        logger.error(f"Error recording payment for invoice {related['invoice_id']}: {str(e)}", exc_info=True)
                                        payment_results.append({
                                            'invoice_id': related['invoice_id'],
                                            'invoice_number': related['invoice_number'],
                                            'amount': invoice_payment,
                                            'success': False,
                                            'error': str(e)
                                        })
                        
                        # Check if any payments were successful
                        successful_payments = [p for p in payment_results if p['success']]
                        if successful_payments:
                            flash(f'Successfully recorded payments for {len(successful_payments)} invoices.', 'success')
                        else:
                            flash('Failed to record any payments.', 'error')
                    else:
                        # Regular single invoice payment
                        # For single invoice payment, allow excess payment to be handled as advance
                        if total_amount > Decimal(str(invoice['balance_due'])):
                            flash(f'Payment amount ({total_amount}) exceeds balance due ({invoice["balance_due"]}). Excess will be treated as advance.', 'warning')
                            logger.warning(f"Payment amount ({total_amount}) exceeds balance due ({invoice['balance_due']}). Treating as advance.")
                        
                        result = record_payment(
                            hospital_id=current_user.hospital_id,
                            invoice_id=uuid.UUID(invoice_id),
                            payment_date=payment_date,
                            cash_amount=cash_amount,
                            credit_card_amount=credit_card_amount,
                            debit_card_amount=debit_card_amount,
                            upi_amount=upi_amount,
                            card_number_last4=card_number_last4,
                            card_type=card_type,
                            upi_id=upi_id,
                            reference_number=reference_number,
                            # Enable excess payment handling
                            handle_excess=True,
                            recorded_by=current_user.user_id
                        )
                        
                        if result:
                            # Check if excess amount was handled
                            if 'excess_amount' in result and result['excess_amount'] > 0:
                                flash(f'Payment recorded successfully. Excess amount of {result["excess_amount"]} added as advance payment.', 'success')
                            else:
                                flash('Payment recorded successfully.', 'success')
                        else:
                            flash('Failed to record payment.', 'error')
                    
                    # Use a direct redirect to avoid the loop
                    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
                
                except Exception as e:
                    flash(f'Error recording payment: {str(e)}', 'error')
                    logger.error(f"Error recording payment: {str(e)}", exc_info=True)
                    
                    # Render the template instead of redirecting
                    menu_items = get_menu_items(current_user)
                    logger.info(f"Balance due in invoice before render: {invoice['balance_due']}")
                    return render_template(
                        'billing/payment_form_page.html',
                        invoice=invoice,
                        patient=patient,
                        payment_form=payment_form,
                        menu_items=menu_items,
                        page_title=f"Record Payment for Invoice #{invoice['invoice_number']}",
                        related_invoices=related_invoices if pay_all else None,
                        total_balance_due=total_balance_due,
                        pay_all=pay_all,
                        advance_balance=advance_balance
                    )
            else:
                # Form validation failed
                flash('Please correct the errors in the form.', 'error')
                # Render the template instead of redirecting
                menu_items = get_menu_items(current_user)
                logger.info(f"Balance due in invoice before render: {invoice['balance_due']}")
                return render_template(
                    'billing/payment_form_page.html',
                    invoice=invoice,
                    patient=patient,
                    payment_form=payment_form,
                    menu_items=menu_items,
                    page_title=f"Record Payment for Invoice #{invoice['invoice_number']}",
                    related_invoices=related_invoices if pay_all else None,
                    total_balance_due=total_balance_due,
                    pay_all=pay_all,
                    advance_balance=advance_balance
                )
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

@billing_views_bp.route('/web_api/patient/search', methods=['GET'])
@login_required
def web_api_patient_search():
    try:
        with get_db_session() as session:
            query = request.args.get('q', '')
            hospital_id = current_user.hospital_id
            
            # For empty query, return recent/popular patients without filtering
            if not query:
                patients = session.query(Patient).filter(
                    Patient.hospital_id == hospital_id,
                    Patient.is_active == True
                ).order_by(Patient.updated_at.desc()).limit(10).all()
            else:
                # Improve search queries to include name searching
                from sqlalchemy import or_
                
                # Handle search queries with more comprehensive matching
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
                ).limit(10).all()
            
            # Format results with error handling for personal_info issues
            results = []
            for patient in patients:
                try:
                    # Get patient name safely
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
                    
                    # Handle contact info safely
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
        current_app.logger.error(f"Error searching patients: {str(e)}", exc_info=True)
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
            
            # Search based on item type
            results = []
            
            if item_type == 'Package':
                # Check if Package has is_active attribute, if not, filter without it
                if hasattr(Package, 'is_active'):
                    packages = session.query(Package).filter(
                        Package.hospital_id == hospital_id,
                        Package.is_active == True,
                        Package.package_name.ilike(f'%{query}%')
                    ).limit(10).all()
                else:
                    packages = session.query(Package).filter(
                        Package.hospital_id == hospital_id,
                        Package.package_name.ilike(f'%{query}%')
                    ).limit(10).all()
                
                for package in packages:
                    results.append({
                        'id': str(package.package_id),
                        'name': package.package_name,
                        'type': 'Package',
                        'price': float(package.price) if package.price else 0.0,
                        'gst_rate': float(package.gst_rate) if package.gst_rate else 0.0,
                        'is_gst_exempt': package.is_gst_exempt if hasattr(package, 'is_gst_exempt') else False
                    })
            
            elif item_type == 'Service':
                # Check if Service has is_active attribute, if not, filter without it
                if hasattr(Service, 'is_active'):
                    services = session.query(Service).filter(
                        Service.hospital_id == hospital_id,
                        Service.is_active == True,
                        Service.service_name.ilike(f'%{query}%')
                    ).limit(10).all()
                else:
                    services = session.query(Service).filter(
                        Service.hospital_id == hospital_id,
                        Service.service_name.ilike(f'%{query}%')
                    ).limit(10).all()
                
                for service in services:
                    results.append({
                        'id': str(service.service_id),
                        'name': service.service_name,
                        'type': 'Service',
                        'price': float(service.price) if service.price else 0.0,
                        'gst_rate': float(service.gst_rate) if hasattr(service, 'gst_rate') else 0.0,
                        'is_gst_exempt': service.is_gst_exempt if hasattr(service, 'is_gst_exempt') else False,
                        'sac_code': service.sac_code if hasattr(service, 'sac_code') else None
                    })
            
            elif item_type == 'Medicine':
                # For Medicine type, exclude prescription-required medicines
                medicine_filter = Medicine.medicine_name.ilike(f'%{query}%')
                
                # Add prescription filter if attribute exists
                if hasattr(Medicine, 'prescription_required'):
                    medicine_filter = and_(
                        medicine_filter, 
                        Medicine.prescription_required == False
                    )
                
                # Add active filter if it exists
                if hasattr(Medicine, 'is_active'):
                    medicines = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        Medicine.is_active == True,
                        medicine_filter
                    ).limit(10).all()
                else:
                    medicines = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        medicine_filter
                    ).limit(10).all()
                
                # Convert to result format
                for medicine in medicines:
                    results.append({
                        'id': str(medicine.medicine_id),
                        'name': medicine.medicine_name,
                        'type': 'Medicine',
                        'gst_rate': float(medicine.gst_rate) if hasattr(medicine, 'gst_rate') else 0.0,
                        'is_gst_exempt': medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False,
                        'hsn_code': medicine.hsn_code if hasattr(medicine, 'hsn_code') else None
                    })
            
            elif item_type == 'Prescription':
                # For Prescription type, only show prescription-required medicines
                prescription_filter = Medicine.medicine_name.ilike(f'%{query}%')
                
                # Add prescription filter if attribute exists
                if hasattr(Medicine, 'prescription_required'):
                    prescription_filter = and_(
                        prescription_filter, 
                        Medicine.prescription_required == True
                    )
                
                # Add active filter if it exists
                if hasattr(Medicine, 'is_active'):
                    medicines = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        Medicine.is_active == True,
                        prescription_filter
                    ).limit(10).all()
                else:
                    medicines = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        prescription_filter
                    ).limit(10).all()
                
                # Convert to result format
                for medicine in medicines:
                    results.append({
                        'id': str(medicine.medicine_id),
                        'name': medicine.medicine_name,
                        'type': 'Prescription',  # Set type as Prescription
                        'gst_rate': float(medicine.gst_rate) if hasattr(medicine, 'gst_rate') else 0.0,
                        'is_gst_exempt': medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False,
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
            
            # Get medicine details
            if hasattr(Medicine, 'is_active'):
                medicine = session.query(Medicine).filter_by(
                    hospital_id=hospital_id,
                    medicine_id=medicine_id,
                    is_active=True
                ).first()
            else:
                medicine = session.query(Medicine).filter_by(
                    hospital_id=hospital_id,
                    medicine_id=medicine_id
                ).first()
            
            if not medicine:
                return jsonify({'error': 'Medicine not found'}), 404
            
            # Query inventory for available batches
            batches = session.query(
                Inventory.batch.label('batch'),
                Inventory.expiry.label('expiry_date'),
                Inventory.current_stock.label('available_quantity'),
                Inventory.sale_price.label('unit_price')
            ).filter(
                Inventory.hospital_id == hospital_id,
                Inventory.medicine_id == medicine_id,
                Inventory.current_stock > 0
            ).order_by(
                Inventory.expiry
            ).all()
            
            # Format the response
            result = []
            for batch in batches:
                result.append({
                    'batch': batch.batch,
                    'expiry_date': batch.expiry_date.strftime('%Y-%m-%d') if batch.expiry_date else None,
                    'available_quantity': float(batch.available_quantity) if batch.available_quantity else 0,
                    'unit_price': float(batch.unit_price) if batch.unit_price else 0
                })
            
            return jsonify(result)
            
    except Exception as e:
        current_app.logger.error(f"Error getting medicine batches: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error getting medicine batches'}), 500

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
            
            # Send email with PDF attachment
            from app.services.email_service import send_email_with_attachment
            
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
            
            # Send WhatsApp message with PDF link
            from app.services.whatsapp_service import send_whatsapp_message
            
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
    # Get patient choices for form - KEEP THIS FOR BACKWARD COMPATIBILITY
    patient_choices = [('', 'Select Patient')]
    
    try:
        with get_db_session() as session:
            # Get initial set of patients (first 10 active patients)
            # Avoid using Patient.full_name in SQL queries
            patients = session.query(Patient).filter(
                Patient.hospital_id == current_user.hospital_id,
                Patient.is_active == True
            ).limit(10).all()
            
            # Add patients to choices - KEEP THIS FOR BACKWARD COMPATIBILITY 
            for patient in patients:
                try:
                    # Get full_name safely after query is executed
                    name = ""
                    if hasattr(patient, 'personal_info') and isinstance(patient.personal_info, dict):
                        first_name = patient.personal_info.get('first_name', '')
                        last_name = patient.personal_info.get('last_name', '')
                        name = f"{first_name} {last_name}".strip()
                    elif hasattr(patient, 'full_name'):
                        name = patient.full_name
                    else:
                        name = f"Patient {patient.mrn}"
                        
                    patient_choices.append((
                        str(patient.patient_id), 
                        f"{name} - {patient.mrn or 'No MRN'}"
                    ))
                except Exception as e:
                    logger.error(f"Error processing patient for choices: {str(e)}")
                
    except Exception as e:
        current_app.logger.error(f"Error loading patients: {str(e)}", exc_info=True)
        flash("Unable to load patients. Please try again.", "error")
    
    # Create form with patient choices - KEEP THIS FOR BACKWARD COMPATIBILITY
    form = AdvancePaymentForm()
    form.patient_id.choices = patient_choices

    # Handle form submission - KEEP EXISTING SUBMISSION LOGIC
    if form.validate_on_submit():
        try:
            # Get form data
            patient_id = uuid.UUID(form.patient_id.data)
            payment_date = form.payment_date.data
            cash_amount = form.cash_amount.data or Decimal('0')
            credit_card_amount = form.credit_card_amount.data or Decimal('0')
            debit_card_amount = form.debit_card_amount.data or Decimal('0')
            upi_amount = form.upi_amount.data or Decimal('0')
            total_amount = cash_amount + credit_card_amount + debit_card_amount + upi_amount
            
            # Create advance payment
            result = create_advance_payment(
                hospital_id=current_user.hospital_id,
                patient_id=patient_id,
                amount=total_amount,
                payment_date=payment_date,
                cash_amount=cash_amount,
                credit_card_amount=credit_card_amount,
                debit_card_amount=debit_card_amount,
                upi_amount=upi_amount,
                card_number_last4=form.card_number_last4.data,
                card_type=form.card_type.data,
                upi_id=form.upi_id.data,
                reference_number=form.reference_number.data,
                notes=form.notes.data,
                current_user_id=current_user.user_id
            )
            
            flash(f"Advance payment of {total_amount} recorded successfully", "success")
            return redirect(url_for('billing_views.view_patient_advances', patient_id=patient_id))
            
        except Exception as e:
            flash(f"Error recording advance payment: {str(e)}", "error")
            logger.error(f"Error recording advance payment: {str(e)}", exc_info=True)
    elif request.method == 'POST':
        logger.error(f"Form validation failed: {form.errors}")
        flash("Please correct the errors in the form", "error")
    
    # Pre-populate payment_date with current date - KEEP THIS
    if request.method == 'GET':
        form.payment_date.data = datetime.now(timezone.utc).date()
    
    # Get menu items for dashboard - KEEP THIS
    menu_items = get_menu_items(current_user)
    
    # Return the template with the form - KEEP THIS
    return render_template(
        'billing/advance_payment.html',
        form=form,
        menu_items=menu_items,
        page_title="Record Advance Payment"
    )

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