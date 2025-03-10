# app/views/auth_views.py
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
                
                # Login the user with Flask-Login
                user = User.query.filter_by(user_id=username).first()
                if user:
                    login_user(user, remember=form.remember_me.data)
                    
                flash('Login successful', 'success')
                
                # Redirect to appropriate dashboard based on user role
                if hasattr(user, 'entity_type') and user.entity_type == 'staff':
                    # Further role checking could be done here
                    return redirect(url_for('auth_views.dashboard'))
                else:
                    # Patient dashboard
                    return redirect(url_for('auth_views.dashboard'))
            else:
                error_msg = 'Invalid credentials'
                if response.status_code != 401:  # If not just wrong credentials
                    try:
                        error_msg = response.json().get('error', 'Authentication failed')
                    except:
                        error_msg = 'Authentication failed'
                flash(error_msg, 'error')
        except requests.exceptions.RequestException as e:
            flash(f'Connection error: {str(e)}', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_views_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration view"""
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Extract form data
        user_type = form.user_type.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        
        # If staff registration, verify approval code
        if user_type == 'staff':
            approval_code = form.approval_code.data
            # You would verify the approval code here
            # For now, using a placeholder check
            if approval_code != 'STAFF123':
                flash('Invalid staff approval code', 'error')
                return render_template('auth/register.html', form=form)
        
        # Call your API to create the user
        try:
            user_data = {
                'username': phone,
                'password': password,
                'user_type': user_type,
                'personal_info': {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'phone': phone
                }
            }
            
            # You'll need to implement this endpoint in your auth.py
            response = requests.post(
                url_for('auth.register', _external=True),
                json=user_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 201:
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('auth_views.login'))
            else:
                try:
                    error_data = response.json()
                    flash(error_data.get('error', 'Registration failed'), 'error')
                except:
                    flash('Registration failed. Please try again.', 'error')
        except requests.exceptions.RequestException as e:
            flash(f'Connection error: {str(e)}', 'error')
    
    return render_template('auth/register.html', form=form)

@auth_views_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view after successful login"""
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