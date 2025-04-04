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
from app.security.utils.auth_utils import (
    get_or_create_hospital,
    get_or_create_branch,
    create_staff_entity,
    create_patient_entity,
    create_user_account,
    authenticate_user
)

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

    if form.validate_on_submit():  # This already checks CSRF token
        username = form.username.data
        password = form.password.data

        from app.services.database_service import get_db_session, get_detached_copy
        import datetime
        
        with get_db_session() as session:
            # Find and authenticate user
            user = session.query(User).filter_by(user_id=username).first()
            
            if not user or not user.check_password(password):
                # Handle failed login
                if user:
                    user.failed_login_attempts += 1
                    session.commit()
                
                flash('Invalid username or password', 'error')
                return render_template('auth/login.html', form=form)
            
            # Update login statistics
            user.last_login = datetime.datetime.now()
            user.failed_login_attempts = 0
            
            # Create a safe detached copy of the user before the session closes
            # This is exactly what the entity lifecycle helpers are designed for
            detached_user = get_detached_copy(user)
            
            # Commit changes
            session.commit()
        
        # Now use the detached_user copy outside the session context
        login_user(detached_user, remember=form.remember_me.data if hasattr(form, 'remember_me') else False)
        
        flash('Login successful', 'success')
        return redirect(url_for('auth_views.dashboard'))
    
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
        
        try:
            # Import the database service
            from app.services.database_service import get_db_session
            
            # Use database service session
            with get_db_session() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(user_id=phone).first()
                if existing_user:
                    flash('User already exists', 'error')
                    return render_template('auth/register.html', form=form)
                
                # Get or create hospital and branch
                hospital = get_or_create_hospital(session)
                branch = get_or_create_branch(session, hospital.hospital_id)
                
                # Create the entity (Staff or Patient)
                entity_type = user_type  # 'staff' or 'patient'
                
                if entity_type == 'staff':
                    _, entity_id = create_staff_entity(
                        session, hospital.hospital_id, branch.branch_id, 
                        first_name, last_name, phone, email
                    )
                else:  # patient
                    _, entity_id = create_patient_entity(
                        session, hospital.hospital_id, branch.branch_id, 
                        first_name, last_name, phone, email
                    )
                
                # Create the user account
                new_user = create_user_account(
                    session, phone, hospital.hospital_id, 
                    entity_type, entity_id, password
                )
                
                # Commit changes to the database
                current_app.logger.info("Attempting to commit changes to database...")
                session.commit()
                current_app.logger.info("Database changes committed successfully")

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
    # Update this function to use direct database operations
    from app.services.database_service import get_db_session
    
    if 'auth_token' in session:
        # Instead of making an API call, directly invalidate the token in database
        try:
            with get_db_session() as db_session:
                token = session['auth_token']
                user_session = db_session.query(UserSession).filter_by(token=token).first()
                if user_session:
                    user_session.is_active = False
                    db_session.commit()
                
            # Clear session token
            session.pop('auth_token', None)
        except Exception as e:
            current_app.logger.error(f"Error during token invalidation: {str(e)}", exc_info=True)
            # Still proceed with local logout
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
    from app.services.database_service import get_db_session
    
    form = ProfileForm()
    
    if form.validate_on_submit():
        try:
            # Directly update user profile in the database
            with get_db_session() as session:
                # Find the user
                user = session.query(User).filter_by(user_id=current_user.user_id).first()
                
                if user:
                    # Update the user's profile information
                    user.first_name = form.first_name.data
                    user.last_name = form.last_name.data
                    user.email = form.email.data
                    
                    # Commit the changes
                    session.commit()
                    
                    # Update current_user to reflect changes
                    current_user.first_name = form.first_name.data
                    current_user.last_name = form.last_name.data
                    current_user.email = form.email.data
                    
                    flash('Profile updated successfully', 'success')
                else:
                    flash('User not found', 'error')
        except Exception as e:
            current_app.logger.error(f"Error updating profile: {str(e)}", exc_info=True)
            flash(f'Failed to update profile: {str(e)}', 'error')
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
    from app.services.database_service import get_db_session
    
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        try:
            # Directly update password in the database
            with get_db_session() as session:
                # Find the user
                user = session.query(User).filter_by(user_id=current_user.user_id).first()
                
                if user:
                    # Verify current password
                    if user.check_password(form.current_password.data):
                        # Update to new password
                        user.set_password(form.new_password.data)
                        session.commit()
                        flash('Password changed successfully', 'success')
                    else:
                        flash('Current password is incorrect', 'error')
                else:
                    flash('User not found', 'error')
        except Exception as e:
            current_app.logger.error(f"Error changing password: {str(e)}", exc_info=True)
            flash(f'Failed to change password: {str(e)}', 'error')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('auth_views.settings'))