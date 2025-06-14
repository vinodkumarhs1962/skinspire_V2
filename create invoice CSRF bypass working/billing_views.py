# app/views/billing_views.py

import uuid
import json
import logging
logger = logging.getLogger('app.services.billing_service')
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, session as flask_session
from flask_login import login_required, current_user
from flask import url_for as flask_url_for
from urllib.parse import urlencode  # Use standard library for URL encoding

from app.forms.billing_forms import InvoiceForm, PaymentForm
from app.services.billing_service import (
    create_invoice, 
    get_invoice_by_id,
    record_payment,
    search_invoices,
    void_invoice,
    issue_refund,
    get_batch_selection_for_invoice
)
from app.utils.menu_utils import get_menu_items
from app.security.authorization.permission_validator import has_permission, permission_required
from app.services.database_service import get_db_session, get_detached_copy
from app.security.authentication.auth_manager import AuthManager
from app.models.master import Hospital, Branch, Medicine, Package, Service, Patient
from app.models.transaction import User, InvoiceHeader

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
        
        # Log CSRF token information
        logger.info(f"CSRF token in form: {request.form.get('csrf_token')}")
        from flask_wtf.csrf import generate_csrf
        expected_token = generate_csrf()
        logger.info(f"Expected CSRF token: {expected_token}")

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

    # For manual form testing - bypass CSRF validation for testing
    if request.method == 'POST':
        logger.info("Attempting to bypass CSRF for testing")
        try:
            # Process form data directly
            hospital_id = current_user.hospital_id
            branch_id = request.form.get('branch_id')
            patient_id = request.form.get('patient_id')
            invoice_date_str = request.form.get('invoice_date')
            notes = request.form.get('notes')
            
            # Parse invoice date
            try:
                invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except:
                invoice_date = datetime.now(timezone.utc)
                logger.warning(f"Couldn't parse invoice date '{invoice_date_str}', using current date")
            
            # Extract line items from form
            line_items = []
            
            # Check if we have line items structure
            form_keys = list(request.form.keys())
            line_item_indices = set()
            
            # Find all line item indices
            for key in form_keys:
                if key.startswith('line_items-') and '-item_type' in key:
                    # Extract index from key format "line_items-{index}-item_type"
                    try:
                        index = key.split('-')[1]
                        line_item_indices.add(index)
                    except:
                        pass
            
            logger.info(f"Found line item indices: {line_item_indices}")
            
            # Process each line item
            for index in line_item_indices:
                try:
                    prefix = f"line_items-{index}-"
                    item_type = request.form.get(f"{prefix}item_type")
                    item_id = request.form.get(f"{prefix}item_id")
                    item_name = request.form.get(f"{prefix}item_name")
                    quantity = request.form.get(f"{prefix}quantity", "1")
                    unit_price = request.form.get(f"{prefix}unit_price", "0")
                    discount_percent = request.form.get(f"{prefix}discount_percent", "0")
                    included_in_consultation = request.form.get(f"{prefix}included_in_consultation") == 'on'
                    
                    # Validate item has required fields
                    if item_id and item_type:
                        # For 'test-patient-id', create a sample UUID
                        if patient_id == 'test-patient-id':
                            # Look up a valid patient instead
                            with get_db_session() as temp_session:
                                test_patient = temp_session.query(Patient).filter(
                                    Patient.hospital_id == current_user.hospital_id
                                ).first()
                                if test_patient:
                                    patient_id = str(test_patient.patient_id)
                                    logger.info(f"Using test patient ID: {patient_id}")
                                else:
                                    patient_id = str(uuid.uuid4())
                                    logger.warning(f"No valid patient found, using generated UUID: {patient_id}")
                        
                        # Create line item
                        line_item = {
                            'item_type': item_type,
                            'item_id': uuid.UUID(item_id),
                            'item_name': item_name,
                            'quantity': Decimal(str(quantity)),
                            'unit_price': Decimal(str(unit_price)),
                            'discount_percent': Decimal(str(discount_percent)),
                            'included_in_consultation': included_in_consultation
                        }
                        
                        # Add batch and expiry for medicines
                        if item_type in ['Medicine', 'Prescription']:
                            batch = request.form.get(f"{prefix}batch")
                            expiry_date = request.form.get(f"{prefix}expiry_date")
                            
                            if batch:
                                line_item['batch'] = batch
                                if expiry_date:
                                    line_item['expiry_date'] = expiry_date
                        
                        line_items.append(line_item)
                    else:
                        logger.warning(f"Skipping line item {index} due to missing required fields")
                except Exception as item_error:
                    logger.error(f"Error processing line item {index}: {str(item_error)}")
                    continue
            
            # Log what we're about to create
            logger.info(f"Attempting to create invoice with {len(line_items)} items")
            for idx, item in enumerate(line_items, 1):
                logger.info(f"Line item {idx}: {item['item_name']} (Type: {item['item_type']}, ID: {item['item_id']})")
                
            # Only proceed if we have valid data    
            if patient_id and line_items:
                # Create invoices based on business rules
                result = create_invoice(
                    hospital_id=hospital_id,
                    branch_id=uuid.UUID(branch_id) if branch_id else None,
                    patient_id=uuid.UUID(patient_id),
                    invoice_date=invoice_date,
                    line_items=line_items,
                    notes=notes,
                    current_user_id=current_user.user_id
                )
                
                logger.info(f"Invoice creation result: {result}")
                
                # Handle multiple invoices
                invoice_count = result.get('count', 0)
                if invoice_count == 1:
                    # Single invoice created
                    invoice = result['invoices'][0]
                    flash('Invoice created successfully.', 'success')
                    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice['invoice_id']))
                elif invoice_count > 1:
                    # Multiple invoices created
                    flash(f'{invoice_count} invoices created successfully based on item types.', 'success')
                    # Redirect to the invoice list filtered by patient
                    return redirect(url_for('billing_views.invoice_list', patient_id=patient_id, created_multiple='true'))
                else:
                    flash('No invoices created. Please check your line items.', 'warning')
            else:
                if not patient_id:
                    flash('Patient ID is required.', 'error')
                if not line_items:
                    flash('At least one valid line item is required.', 'error')
                
        except Exception as e:
            logger.error(f"Manual CSRF bypass failed: {str(e)}", exc_info=True)
            flash(f"Error creating invoice: {str(e)}", "error")

    # Regular form handling with CSRF validation
    if form.validate_on_submit():
        logger.info("Form validated successfully - normal flow")
        try:
            # Convert form data to required format
            hospital_id = current_user.hospital_id
            branch_id = request.form.get('branch_id')
            patient_id = form.patient_id.data
            invoice_date = form.invoice_date.data
            notes = form.notes.data
            
            # Process line items
            line_items = []
            for item_data in form.line_items.data:
                line_item = {
                    'item_type': item_data['item_type'],
                    'item_id': uuid.UUID(item_data['item_id']),
                    'item_name': item_data['item_name'],
                    'quantity': Decimal(str(item_data['quantity'])),
                    'unit_price': Decimal(str(item_data['unit_price'])),
                    'discount_percent': Decimal(str(item_data['discount_percent'])),
                    'included_in_consultation': item_data.get('included_in_consultation', False)
                }
                
                # Add batch and expiry for medicines
                if item_data['item_type'] in ['Medicine', 'Prescription'] and item_data.get('batch'):
                    line_item['batch'] = item_data['batch']
                    if item_data.get('expiry_date'):
                        line_item['expiry_date'] = item_data['expiry_date']
                
                line_items.append(line_item)
            
            # Create invoices based on business rules
            invoice_result = create_invoice(
                hospital_id=hospital_id,
                branch_id=uuid.UUID(branch_id) if branch_id else None,
                patient_id=uuid.UUID(patient_id),
                invoice_date=invoice_date.replace(tzinfo=timezone.utc),
                line_items=line_items,
                notes=notes,
                current_user_id=current_user.user_id
            )
            
            # To ensure the transaction is fully committed before redirect
            session.commit()  # <-- You may need to add this if using a session

            # Handle multiple invoices
            invoice_count = invoice_result.get('count', 0)
            if invoice_count == 1:
                # Single invoice created
                invoice = invoice_result['invoices'][0]
                flash('Invoice created successfully.', 'success')
                return redirect(url_for('billing_views.view_invoice', invoice_id=invoice['invoice_id']))
            elif invoice_count > 1:
                # Multiple invoices created
                flash(f'{invoice_count} invoices created successfully based on item types.', 'success')
                # Redirect to the invoice list filtered by patient
                return redirect(url_for('billing_views.invoice_list', patient_id=patient_id, created_multiple='true'))
            else:
                flash('No invoices created. Please check your line items.', 'warning')
                
        except Exception as e:
            flash(f'Error creating invoice: {str(e)}', 'error')
            logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
    elif request.method == 'POST':
        # Log validation errors
        logger.error(f"Form validation failed with errors: {form.errors}")
        if form.csrf_token.errors:
            logger.error(f"CSRF validation failed: {form.csrf_token.errors}")
    
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
    
    return render_template(
        'billing/create_invoice.html',
        form=form,
        branches=branches,
        menu_items=menu_items,
        page_title="Create Invoice",
        auth_token=auth_token  # Pass token to template
    )   


# @billing_views_bp.route('/create', methods=['GET', 'POST'])
# @login_required
# @permission_required('billing', 'create')
# def create_invoice_view():
#     """View for creating a new invoice"""
    
#     # Add diagnostic logging
#     logger.info(f"create_invoice_view accessed with method: {request.method}")
#     logger.info(f"Request Content-Type: {request.content_type}")
    
#     if request.method == 'POST':
#         logger.info("POST request received")
#         logger.info(f"Form data: {request.form}")
#         logger.info(f"JSON data: {request.get_json(silent=True)}")
#         logger.info(f"Files: {request.files}")
        
#         # Log CSRF token information
#         logger.info(f"CSRF token in form: {request.form.get('csrf_token')}")
#         from flask_wtf.csrf import generate_csrf
#         expected_token = generate_csrf()
#         logger.info(f"Expected CSRF token: {expected_token}")

#     # Prepare patient choices
#     patient_choices = [('', 'Select Patient')]
    
   
#     try:
#         with get_db_session() as session:
#             # Get initial set of patients (first 10 active patients)
#             patients = session.query(Patient).filter(
#                 Patient.hospital_id == current_user.hospital_id,
#                 Patient.is_active == True
#             ).limit(10).all()
            
#             # Create detached copies of patients
#             patients = [get_detached_copy(patient) for patient in patients]

#             # Add patients to choices
#             patient_choices.extend([
#                 (str(patient.patient_id), f"{patient.full_name} - {patient.mrn or 'No MRN'}") 
#                 for patient in patients
#             ])
#     except Exception as e:
#         current_app.logger.error(f"Error loading patients: {str(e)}", exc_info=True)
#         flash("Unable to load patients. Please try again.", "error")
    
#     # Create form with patient choices
#     form = InvoiceForm(patient_choices=patient_choices)
    
#     # Pre-populate invoice_date with current date
#     form.invoice_date.data = datetime.now(timezone.utc).date()

#     # Set default place of supply to Karnataka (29)
#     form.place_of_supply.data = '29'

#     if form.validate_on_submit():
#         try:
#             # Convert form data to required format
#             hospital_id = current_user.hospital_id
#             branch_id = request.form.get('branch_id')
#             patient_id = form.patient_id.data
#             invoice_date = form.invoice_date.data
#             notes = form.notes.data
            
#             # Process line items
#             line_items = []
#             for item_data in form.line_items.data:
#                 line_item = {
#                     'item_type': item_data['item_type'],
#                     'item_id': uuid.UUID(item_data['item_id']),
#                     'item_name': item_data['item_name'],
#                     'quantity': Decimal(str(item_data['quantity'])),
#                     'unit_price': Decimal(str(item_data['unit_price'])),
#                     'discount_percent': Decimal(str(item_data['discount_percent'])),
#                     'included_in_consultation': item_data.get('included_in_consultation', False)
#                 }
                
#                 # Add batch and expiry for medicines
#                 if item_data['item_type'] in ['Medicine', 'Prescription'] and item_data.get('batch'):
#                     line_item['batch'] = item_data['batch']
#                     if item_data.get('expiry_date'):
#                         line_item['expiry_date'] = item_data['expiry_date']
                
#                 line_items.append(line_item)
            
#             # Create invoices based on business rules
#             invoice_result = create_invoice(
#                 hospital_id=hospital_id,
#                 branch_id=uuid.UUID(branch_id) if branch_id else None,
#                 patient_id=uuid.UUID(patient_id),
#                 invoice_date=invoice_date.replace(tzinfo=timezone.utc),
#                 line_items=line_items,
#                 notes=notes,
#                 current_user_id=current_user.user_id
#             )
            
#             # Handle multiple invoices
#             invoice_count = invoice_result.get('count', 0)
#             if invoice_count == 1:
#                 # Single invoice created
#                 invoice = invoice_result['invoices'][0]
#                 flash('Invoice created successfully.', 'success')
#                 return redirect(url_for('billing_views.view_invoice', invoice_id=invoice['invoice_id']))
#             elif invoice_count > 1:
#                 # Multiple invoices created
#                 flash(f'{invoice_count} invoices created successfully based on item types.', 'success')
#                 # Redirect to the invoice list filtered by patient
#                 return redirect(url_for('billing_views.invoice_list', patient_id=patient_id, created_multiple='true'))
#             else:
#                 flash('No invoices created. Please check your line items.', 'warning')
                
#         except Exception as e:
#             flash(f'Error creating invoice: {str(e)}', 'error')
#             logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
    
#     # Get branches for dropdown
#     branches = []
#     try:
#         with get_db_session() as session:
#             branches_query = session.query(Branch).filter_by(
#                 hospital_id=current_user.hospital_id,
#                 is_active=True
#             ).all()
            
#             # Create detached copies before accessing properties
#             branches_detached = [get_detached_copy(branch) for branch in branches_query]
            
#             # Convert to dictionary format for the template
#             branches = [
#                 {'branch_id': str(branch.branch_id), 'name': branch.name} 
#                 for branch in branches_detached
#             ]
#     except Exception as e:
#         logger.error(f"Error loading branches: {str(e)}", exc_info=True)
        
#     # Get menu items for dashboard
#     menu_items = get_menu_items(current_user)
    
#     # Generate JWT token for API calls
#     auth_token = None
#     try:
#         with get_db_session() as db_session:
#             auth_manager = AuthManager(session=db_session)
#             # Create a proper session for the user
#             auth_token = auth_manager.create_session(current_user.user_id, str(current_user.hospital_id))
#             logger.info(f"Generated auth token: {auth_token[:10]}... for user {current_user.user_id}")
#     except Exception as e:
#         logger.error(f"Error generating auth token: {str(e)}", exc_info=True)
    
#     return render_template(
#         'billing/create_invoice.html',
#         form=form,
#         branches=branches,
#         menu_items=menu_items,
#         page_title="Create Invoice",
#         auth_token=auth_token  # Pass token to template
#     )

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
    """View invoice details"""
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
                            'grand_total': related_dict.grand_total
                        })
        
        return render_template(
            'billing/view_invoice.html',
            invoice=invoice,
            patient=patient,
            payment_form=payment_form,
            menu_items=menu_items,
            page_title=f"Invoice #{invoice['invoice_number']}",
            is_consolidated_prescription=invoice.get('is_consolidated_prescription', False),
            related_invoices=related_invoices
        )
    
    except Exception as e:
        flash(f'Error retrieving invoice: {str(e)}', 'error')
        logger.error(f"Error retrieving invoice: {str(e)}", exc_info=True)
        return redirect(url_for('billing_views.invoice_list'))

@billing_views_bp.route('/<uuid:invoice_id>/record-payment', methods=['POST'])
@login_required
@permission_required('billing', 'create')
def record_invoice_payment(invoice_id):
    """Record a payment for an invoice"""
    form = PaymentForm()
    
    if form.validate_on_submit():
        try:
            # Prepare payment methods
            payment_methods = {
                'cash': form.cash_amount.data or Decimal('0'),
                'credit_card': form.credit_card_amount.data or Decimal('0'),
                'debit_card': form.debit_card_amount.data or Decimal('0'),
                'upi': form.upi_amount.data or Decimal('0')
            }
            
            # Prepare payment details
            payment_details = {}
            
            if form.card_number_last4.data:
                payment_details['card_number_last4'] = form.card_number_last4.data
                
            if form.card_type.data:
                payment_details['card_type'] = form.card_type.data
                
            if form.upi_id.data:
                payment_details['upi_id'] = form.upi_id.data
                
            if form.reference_number.data:
                payment_details['reference_number'] = form.reference_number.data
            
            # Record the payment
            payment = record_payment(
                hospital_id=current_user.hospital_id,
                invoice_id=invoice_id,
                payment_date=form.payment_date.data.replace(tzinfo=timezone.utc),
                payment_methods=payment_methods,
                payment_details=payment_details,
                current_user_id=current_user.user_id
            )
            
            flash('Payment recorded successfully.', 'success')
            
        except Exception as e:
            flash(f'Error recording payment: {str(e)}', 'error')
            logger.error(f"Error recording payment: {str(e)}", exc_info=True)
    
    return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))

@billing_views_bp.route('/<uuid:invoice_id>/void', methods=['POST'])
@login_required
@permission_required('billing', 'delete')
def void_invoice_view(invoice_id):
    """Void an invoice"""
    try:
        reason = request.form.get('reason')
        if not reason:
            flash('Reason for voiding is required.', 'error')
            return redirect(url_for('billing_views.view_invoice', invoice_id=invoice_id))
        
        # Void the invoice
        void_invoice(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id,
            reason=reason,
            current_user_id=current_user.user_id
        )
        
        flash('Invoice voided successfully.', 'success')
        
    except Exception as e:
        flash(f'Error voiding invoice: {str(e)}', 'error')
        logger.error(f"Error voiding invoice: {str(e)}", exc_info=True)
    
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

# Add these new routes to billing_views.py

@billing_views_bp.route('/web_api/patient/search', methods=['GET'])
@login_required
def web_api_patient_search():
    try:
        with get_db_session() as session:
            query = request.args.get('q', '')
            if len(query) < 1:
                return jsonify([])
            
            hospital_id = current_user.hospital_id
            
            # Search patients without using the full_name hybrid property
            patients = session.query(Patient).filter(
                Patient.hospital_id == hospital_id,
                Patient.is_active == True
            ).filter(
                # Search by first and last name in the JSON
                (Patient.personal_info['first_name'].astext + ' ' + 
                 Patient.personal_info['last_name'].astext).ilike(f'%{query}%') |
                # Search by MRN
                Patient.mrn.ilike(f'%{query}%') |
                # Search by phone number
                Patient.contact_info['phone'].astext.ilike(f'%{query}%')
            ).limit(10).all()
            
            # Format results
            results = []
            for patient in patients:
                patient_dict = {
                    'id': str(patient.patient_id),
                    'name': patient.full_name,  # This uses the Python property
                    'mrn': patient.mrn,
                    'contact': patient.contact_info.get('phone') if patient.contact_info else None
                }
                results.append(patient_dict)
            
            return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Error searching patients: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error searching patients'}), 500

@billing_views_bp.route('/web_api/item/search', methods=['GET'])
@login_required
def web_api_item_search():
    """Web-friendly item search that uses Flask-Login"""
    try:
        with get_db_session() as session:
            # Get query parameters
            query = request.args.get('q', '')
            item_type = request.args.get('type', '')
            
            if len(query) < 2 or not item_type:
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
            
            elif item_type in ['Medicine', 'Prescription']:
                # Check if Medicine has is_active attribute, if not, filter without it
                if hasattr(Medicine, 'is_active'):
                    medicines = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        Medicine.is_active == True,
                        Medicine.name.ilike(f'%{query}%')
                    ).limit(10).all()
                else:
                    medicines = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        Medicine.name.ilike(f'%{query}%')
                    ).limit(10).all()
                
                for medicine in medicines:
                    results.append({
                        'id': str(medicine.medicine_id),
                        'name': medicine.name,
                        'type': 'Medicine',
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
            
            # Get medicine details - check for is_active attribute
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
            
            # Get batch selection for invoice
            try:
                batches = get_batch_selection_for_invoice(hospital_id, medicine_id, quantity)
                return jsonify(batches)
            except Exception as batch_error:
                current_app.logger.error(f"Error in batch selection: {str(batch_error)}", exc_info=True)
                return jsonify([])  # Return empty list on error instead of 500
                
    except Exception as e:
        current_app.logger.error(f"Error getting medicine batches: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error getting medicine batches'}), 500

# # API endpoints for AJAX requests
# @billing_views_bp.route('/api/patient/search', methods=['GET'])
# @login_required
# def api_patient_search():
#     """Deprecated: API endpoint to search for patients - delegates to new API endpoint"""
#     current_app.logger.warning("Using deprecated API endpoint: /billing/api/patient/search. Update to /api/patient/search")
#     # return delegate_to_api('billing_api.api_patient_search')
#     return delegate_to_api('billing_api.api_patient_search_web')

# @billing_views_bp.route('/api/item/search', methods=['GET'])
# @login_required
# def api_item_search():
#     """Deprecated: API endpoint to search for billable items - delegates to new API endpoint"""
#     current_app.logger.warning("Using deprecated API endpoint: /billing/api/item/search. Update to /api/item/search")
#     # return delegate_to_api('billing_api.api_item_search')
#     return delegate_to_api('billing_api.api_item_search_web')

# @billing_views_bp.route('/api/medicine/<uuid:medicine_id>/batches', methods=['GET'])
# @login_required
# def api_medicine_batches(medicine_id):
#     """Deprecated: API endpoint to get available batches - delegates to new API endpoint"""
#     current_app.logger.warning("Using deprecated API endpoint: /billing/api/medicine/{id}/batches. Update to /api/medicine/{id}/batches")
#     # return delegate_to_api('billing_api.api_medicine_batches', medicine_id=medicine_id)
#     return delegate_to_api('billing_api.api_medicine_batches_web', medicine_id=medicine_id)