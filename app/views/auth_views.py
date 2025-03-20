# app/views/auth_views.py
from flask import current_app 
from app.utils.menu_utils import generate_menu_for_role
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, g
from flask_login import login_user, current_user, logout_user, login_required
from app.forms.auth_forms import LoginForm, RegistrationForm
from app.models.transaction import User, UserSession
import requests
import json
import datetime

auth_views_bp = Blueprint('auth_views', __name__)

@auth_views_bp.context_processor
def inject_current_year():
    return {'current_year': datetime.datetime.now().year}

@auth_views_bp.route('/')
def index():
    """Landing page redirects to login"""
    return redirect(url_for('auth_views.login'))

@auth_views_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Call your existing API endpoint
        try:
            response = requests.post(
                url_for('auth.login', _external=True),
                json={'username': username, 'password': password},
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                data = response.json()
                # Store token in session
                session['auth_token'] = data['token']

                # Use your database service instead of direct query
                from app.services.database_service import get_db_session
                
                with get_db_session() as db_session:
                    user = db_session.query(User).filter_by(user_id=username).first()
                    
                    if user:
                        login_user(user)
                        flash('Login successful', 'success')
                        return redirect(url_for('auth_views.dashboard'))
                    else:
                        flash('User not found', 'error')
            else:
                flash('Login failed: Invalid credentials', 'error')
        except requests.RequestException as e:
            flash(f'Connection error: {str(e)}', 'error')
            
    # If GET request or form validation failed or login failed
    return render_template('auth/login.html', form=form)

# app/views/auth_views.py - Only the register function is updated here

@auth_views_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration view"""
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))
    
    form = RegistrationForm()
    
    if request.method == 'POST':
        print(f"Form submitted: {request.form}")
        print(f"Form validation: {form.validate()}")
    
    if form.validate_on_submit():
        # Extract form data
        user_type = form.user_type.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        
        try:
            # Import the database service and models
            from app.services.database_service import get_db_session
            from app.models.transaction import User
            from app.models.master import Staff, Patient, Hospital, Branch
            import uuid
            
            # Use database service session
            with get_db_session() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(user_id=phone).first()
                if existing_user:
                    flash('User already exists', 'error')
                    return render_template('auth/register.html', form=form)
                
                # Get default hospital or create one if needed
                hospital = session.query(Hospital).first()
                if not hospital:
                    # Create a default hospital for development/testing
                    hospital = Hospital(
                        name="SkinSpire Clinic",
                        license_no="DEFAULT001",
                        address={"street": "123 Main St", "city": "Bangalore"},
                        contact_details={"phone": "1234567890", "email": "info@skinspire.com"}
                    )
                    session.add(hospital)
                    session.flush()  # Get the ID without committing
            
                # Get default branch or create one if needed
                branch = session.query(Branch).filter_by(hospital_id=hospital.hospital_id).first()
                if not branch:
                    # Create a default branch for development/testing
                    branch = Branch(
                        hospital_id=hospital.hospital_id,
                        name="Main Branch",
                        address={"street": "123 Main St", "city": "Bangalore"},
                        contact_details={"phone": "1234567890", "email": "main@skinspire.com"}
                    )
                    session.add(branch)
                    session.flush()  # Get the ID without committing
                
                # Create the entity (Staff or Patient)
                entity_type = user_type  # 'staff' or 'patient'
                
                if entity_type == 'staff':
                    staff = Staff(
                        hospital_id=hospital.hospital_id,
                        branch_id=branch.branch_id if branch else None,
                        employee_code=f"EMP{phone[-4:]}",
                        personal_info={
                            "first_name": first_name,
                            "last_name": last_name,
                            "gender": "unspecified"
                        },
                        contact_info={
                            "phone": phone,
                            "email": email,
                            "address": {}
                        },
                        professional_info={}
                    )
                    session.add(staff)
                    session.flush()  # Get the ID without committing
                    entity_id = staff.staff_id
                else:  # patient
                    patient = Patient(
                        hospital_id=hospital.hospital_id,
                        branch_id=branch.branch_id if branch else None,
                        mrn=f"PAT{phone[-4:]}",
                        personal_info={
                            "first_name": first_name,
                            "last_name": last_name,
                            "gender": "unspecified"
                        },
                        contact_info={
                            "phone": phone,
                            "email": email,
                            "address": {}
                        }
                    )
                    session.add(patient)
                    session.flush()  # Get the ID without committing
                    entity_id = patient.patient_id
                
                # Create the user account
                new_user = User(
                    user_id=phone,
                    hospital_id=hospital.hospital_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    is_active=True,
                    failed_login_attempts=0
                )
                
                # Set password using the model's password hashing method
                new_user.set_password(password)
                
                # Add to database
                session.add(new_user)
                
                # Log success
                current_app.logger.info(f"User registered successfully: {phone}")
                
                # Redirect to login page with success message
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('auth_views.login'))
                
        except Exception as e:
            # Log error and show message to user
            current_app.logger.error(f"Registration error: {str(e)}", exc_info=True)
            flash(f'Registration failed: {str(e)}', 'error')
            print(f"Exception during registration: {str(e)}")
    
    return render_template('auth/register.html', form=form)

# @auth_views_bp.route('/register', methods=['GET', 'POST'])
# def register():
#     """User registration view"""
#     if current_user.is_authenticated:
#         return redirect(url_for('auth_views.dashboard'))
    
#     form = RegistrationForm()
    
#     # Debug logging
#     if request.method == 'POST':
#         print(f"Form submitted: {request.form}")
#         print(f"Form validation: {form.validate()}")
    
#     if form.validate_on_submit():
#         # Extract form data
#         user_type = form.user_type.data
#         first_name = form.first_name.data
#         last_name = form.last_name.data
#         phone = form.phone.data
#         email = form.email.data
#         password = form.password.data
        
#         try:
#             # Generate a placeholder entity ID
#             import uuid
#             entity_id = str(uuid.uuid4())
            
#             # Create user data
#             user_data = {
#                 'username': phone,
#                 'password': password,
#                 'user_type': user_type,
#                 'hospital_id': '4ef72e18-e65d-4766-b9eb-0308c42485ca',
#                 'entity_id': entity_id,
#                 'personal_info': {
#                     'first_name': first_name,
#                     'last_name': last_name,
#                     'email': email,
#                     'phone': phone
#                 }
#             }
            
#             print(f"Sending to API: {user_data}")
            
#             # Import the registration function directly
#             from app.security.routes.auth import register as auth_register_function
            
#             # Use Flask's test_request_context to bypass HTTP and CSRF
#             from flask import current_app
#             with current_app.test_request_context(
#                 path='/api/auth/register',
#                 method='POST',
#                 json=user_data
#             ):
#                 # Call the function directly
#                 response = auth_register_function()
                
#                 # Extract response data and status code
#                 if isinstance(response, tuple):
#                     response_data, status_code = response
#                 else:
#                     response_data = response
#                     status_code = 200
                
#                 print(f"Direct API response: {status_code}")
#                 print(f"Response data: {response_data}")
                
#                 # Process the response
#                 if status_code == 201:
#                     flash('Registration successful! You can now log in.', 'success')
#                     return redirect(url_for('auth_views.login'))
#                 else:
#                     if isinstance(response_data, dict):
#                         error_msg = response_data.get('error', 'Registration failed')
#                     else:
#                         error_msg = 'Registration failed'
#                     flash(error_msg, 'error')
#                     print(f"Registration error: {error_msg}")
                
#         except Exception as e:
#             flash(f'Registration error: {str(e)}', 'error')
#             print(f"Exception during registration: {str(e)}")
    
#     return render_template('auth/register.html', form=form)

@auth_views_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view after successful login"""
    
    import logging
    
    # Use root logger to ensure visibility
    logger = logging.getLogger
    current_app.logger.info("Dashboard route accessed")
    current_app.logger.info(f"Current User: {current_user}")
    current_app.logger.info(f"Is Authenticated: {current_user.is_authenticated}")
    current_app.logger.info(f"User ID: {current_user.get_id()}")
    current_app.logger.info(f"Session User ID: {session.get('user_id')}")
    current_app.logger.info(f"Session Contents: {dict(session)}")
    
    # Get user menu items based on role
    user_role = current_user.entity_type if hasattr(current_user, 'entity_type') else 'patient'
    
    # This is a placeholder. In a real implementation, you would fetch
    # menu items from a database based on user role
    menu_items = generate_menu_for_role(user_role)
    
    return render_template('dashboard/index.html', menu_items=menu_items)

@auth_views_bp.route('/logout')
def logout():
    if 'auth_token' in session:
        # Call your API to invalidate the token
        try:
            response = requests.post(
                url_for('auth.logout', _external=True),
                headers={'Authorization': f'Bearer {session["auth_token"]}'}
            )
            
            # Clear session regardless of response
            session.pop('auth_token', None)
        except requests.exceptions.RequestException:
            # Still proceed with local logout even if API call fails
            session.pop('auth_token', None)
    
    logout_user()  # For Flask-Login
    flash('You have been logged out', 'info')
    return redirect(url_for('auth_views.login'))

def generate_menu_for_role(role):
    """Generate menu items based on user role"""
    # Basic menu items available to all users
    menu = [
        {
            'name': 'Dashboard',
            'url': url_for('auth_views.dashboard'),
            'icon': 'home'
        }
    ]
    
    # Add role-specific menu items
    if role == 'staff':
        menu.extend([
            {
                'name': 'Patients',
                'url': '#',
                'icon': 'users',
                'children': [
                    {'name': 'Patient List', 'url': '#', 'icon': 'list'},
                    {'name': 'New Patient', 'url': '#', 'icon': 'user-plus'}
                ]
            },
            {
                'name': 'Appointments',
                'url': '#',
                'icon': 'calendar',
                'children': [
                    {'name': 'View Schedule', 'url': '#', 'icon': 'clock'},
                    {'name': 'New Appointment', 'url': '#', 'icon': 'plus'}
                ]
            }
        ])
    elif role == 'patient':
        menu.extend([
            {
                'name': 'My Appointments',
                'url': '#',
                'icon': 'calendar'
            },
            {
                'name': 'My Records',
                'url': '#',
                'icon': 'clipboard'
            }
        ])
    
    return menu

# Add to app/views/auth_views.py if not already present

@auth_views_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """User settings view"""
    # Initialize forms
    from app.forms.auth_forms import ProfileForm, PasswordChangeForm
    
    profile_form = ProfileForm()
    password_form = PasswordChangeForm()
    
    # Populate profile form with current user data
    if hasattr(current_user, 'first_name'):
        profile_form.first_name.data = current_user.first_name
    if hasattr(current_user, 'last_name'):
        profile_form.last_name.data = current_user.last_name
    if hasattr(current_user, 'email'):
        profile_form.email.data = current_user.email
    
    # Get menu items for navigation
    user_role = current_user.entity_type if hasattr(current_user, 'entity_type') else 'patient'
    menu_items = generate_menu_for_role(user_role)
    
    # Get login history if available
    login_history = []
    try:
        # This would be an API call to get login history
        # For now, just show the most recent login
        if hasattr(current_user, 'last_login') and current_user.last_login:
            login_history = [{
                'date': current_user.last_login,
                'status': 'Successful',
                'ip_address': 'Not available'
            }]
    except Exception as e:
        current_app.logger.error(f"Error fetching login history: {str(e)}")
    
    return render_template(
        'auth/settings.html',
        profile_form=profile_form,
        password_form=password_form,
        menu_items=menu_items,
        login_history=login_history
    )

@auth_views_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Handle profile update form submission"""
    from app.forms.auth_forms import ProfileForm
    
    form = ProfileForm()
    
    if form.validate_on_submit():
        try:
            # Call API to update user profile
            response = requests.put(
                url_for('auth.update_profile', _external=True),
                json={
                    'user_id': current_user.user_id,
                    'first_name': form.first_name.data,
                    'last_name': form.last_name.data,
                    'email': form.email.data
                },
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {session.get("auth_token")}'
                }
            )
            
            if response.status_code == 200:
                flash('Profile updated successfully', 'success')
            else:
                try:
                    error_data = response.json()
                    flash(error_data.get('error', 'Failed to update profile'), 'error')
                except:
                    flash('Failed to update profile', 'error')
        except requests.exceptions.RequestException as e:
            flash(f'Connection error: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('auth_views.settings'))

@auth_views_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Handle password change form submission"""
    from app.forms.auth_forms import PasswordChangeForm
    
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        try:
            # Call API to change password
            response = requests.put(
                url_for('auth.change_password', _external=True),
                json={
                    'user_id': current_user.user_id,
                    'current_password': form.current_password.data,
                    'new_password': form.new_password.data
                },
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {session.get("auth_token")}'
                }
            )
            
            if response.status_code == 200:
                flash('Password changed successfully', 'success')
            else:
                try:
                    error_data = response.json()
                    flash(error_data.get('error', 'Failed to change password'), 'error')
                except:
                    flash('Failed to change password', 'error')
        except requests.exceptions.RequestException as e:
            flash(f'Connection error: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('auth_views.settings'))