# app/views/auth_views.py
from flask import (
    Blueprint, render_template, redirect, url_for, request, 
    flash, current_app, session
)
from flask_login import login_user, current_user, logout_user, login_required
import datetime
import json

# Import necessary forms
from app.forms.auth_forms import (
    LoginForm, RegistrationForm, ProfileForm, 
    StaffProfileForm, PatientProfileForm,
    PasswordChangeForm, ForgotPasswordForm, ResetPasswordForm
)

# Import services
from app.services.profile_service import ProfileService
from app.services.forgot_password_service import ForgotPasswordService

# Import database service
from app.services.database_service import get_db_session, get_detached_copy, get_entity_dict

# Import models
from app.models.transaction import User, UserSession

# Import utilities
from app.utils.menu_utils import generate_menu_for_role

# Create blueprint
auth_views_bp = Blueprint('auth_views', __name__)

@auth_views_bp.context_processor
def inject_current_year():
    """Inject current year into all templates"""
    return {'current_year': datetime.datetime.now().year}

@auth_views_bp.route('/')
def index():
    """Landing page redirects to login"""
    return redirect(url_for('auth_views.login'))

@auth_views_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login view with enhanced error handling"""
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        try:
            with get_db_session() as session:
                # Find user
                user = session.query(User).filter_by(user_id=form.username.data).first()
                
                if not user or not user.check_password(form.password.data):
                    flash('Invalid username or password', 'error')
                    return render_template('auth/login.html', form=form)
                
                # Update login statistics
                user.last_login = datetime.datetime.now()
                user.failed_login_attempts = 0
                
                # Create a detached copy of user for use after session closes
                detached_user = get_detached_copy(user)
                
                # Commit changes
                session.commit()
            
            # Use the detached user outside of the session context
            login_user(detached_user, remember=form.remember_me.data)
            
            flash('Login successful', 'success')
            return redirect(url_for('auth_views.dashboard'))
        
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}", exc_info=True)
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_views_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration view with validation"""
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            from app.services.database_service import get_db_session
            from app.models.master import Staff, Patient, Hospital, Branch
            import uuid
            
            with get_db_session() as session:
                # Check if user already exists
                existing_user = session.query(User).filter_by(user_id=form.phone.data).first()
                
                if existing_user:
                    flash('User with this phone number already exists', 'error')
                    return render_template('auth/register.html', form=form)
                
                # Get the default hospital and branch
                # In a production system, this might be determined by user selection
                # or based on the registration context
                default_hospital = session.query(Hospital).first()
                if not default_hospital:
                    flash('No hospital configured in the system', 'error')
                    return render_template('auth/register.html', form=form)
                
                default_branch = session.query(Branch).filter_by(hospital_id=default_hospital.hospital_id).first()
                
                # Create entity based on user type
                entity_id = uuid.uuid4()
                
                # Prepare common personal and contact info
                personal_info = json.dumps({
                    'title': form.title.data,
                    'first_name': form.first_name.data,
                    'last_name': form.last_name.data
                })
                
                contact_info = json.dumps({
                    'phone': form.phone.data,
                    'email': form.email.data
                })
                
                if form.user_type.data == 'staff':
                    # Create staff entity
                    staff = Staff(
                        staff_id=entity_id,
                        hospital_id=default_hospital.hospital_id,
                        branch_id=default_branch.branch_id if default_branch else None,
                        personal_info=personal_info,
                        contact_info=contact_info,
                        professional_info=json.dumps({}),
                        employment_info=json.dumps({})
                    )
                    session.add(staff)
                    
                elif form.user_type.data == 'patient':
                    # Create patient entity
                    patient = Patient(
                        patient_id=entity_id,
                        hospital_id=default_hospital.hospital_id,
                        branch_id=default_branch.branch_id if default_branch else None,
                        personal_info=personal_info,
                        contact_info=contact_info,
                        emergency_contact=json.dumps({}),
                        preferences=json.dumps({})
                    )
                    session.add(patient)
                
                # Create new user with reference to entity
                new_user = User(
                    user_id=form.phone.data,
                    entity_type=form.user_type.data,
                    entity_id=entity_id,
                    hospital_id=default_hospital.hospital_id
                )
                
                # Set password
                new_user.set_password(form.password.data)
                
                # Add user to session
                session.add(new_user)
                
                # Log the user creation
                current_app.logger.info(f"Created user account for {form.phone.data}")
                
                # Attempt to commit
                current_app.logger.info("Attempting to commit changes to database...")
                session.commit()
                current_app.logger.info("Database changes committed successfully")
                
                # Log the success
                current_app.logger.info(f"User registered successfully: {form.phone.data}")
                
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth_views.login'))
                
        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}", exc_info=True)
            flash('An error occurred during registration. Please try again.', 'error')
    else:
        # Log form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return render_template('auth/register.html', form=form)

@auth_views_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view with dynamic menu generation"""
    # Log dashboard access
    current_app.logger.info("Dashboard route accessed")
    
    # Log user details for debugging
    current_app.logger.info(f"Current User: {current_user}")
    current_app.logger.info(f"Is Authenticated: {current_user.is_authenticated}")
    current_app.logger.info(f"User ID: {current_user.user_id}")
    current_app.logger.info(f"Session User ID: {session.get('user_id')}")
    current_app.logger.info(f"Session Contents: {session}")
    
    # Determine user role
    user_role = current_user.entity_type if hasattr(current_user, 'entity_type') else 'patient'
    
    # Generate menu based on user role
    menu_items = generate_menu_for_role(user_role)
    
    return render_template('dashboard/index.html', menu_items=menu_items)

@auth_views_bp.route('/settings', methods=['GET'])
@login_required
def settings():
    """Comprehensive user settings view"""
    try:
        # Get user profile using service
        user_profile = ProfileService.get_profile(current_user.user_id)
        
        # Determine appropriate form based on entity type
        if user_profile and user_profile.get('entity_type') == 'staff':
            profile_form = StaffProfileForm()
        elif user_profile and user_profile.get('entity_type') == 'patient':
            profile_form = PatientProfileForm()
        else:
            profile_form = ProfileForm()
        
        # Populate form with current profile data
        if user_profile:
            for field, value in user_profile.items():
                if hasattr(profile_form, field):
                    # Special handling for date fields
                    if field in ['date_of_birth', 'join_date']:
                        try:
                            # Use datetime module's parsing method
                            if value:
                                # Remove any quotes from the string
                                value = value.strip('"')
                                # Explicitly use datetime.datetime.strptime
                                date_value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
                                getattr(profile_form, field).data = date_value
                            else:
                                getattr(profile_form, field).data = None
                        except (ValueError, TypeError) as e:
                            current_app.logger.warning(f"Invalid date format for {field}: {value}. Error: {e}")
                            getattr(profile_form, field).data = None
                    else:
                        getattr(profile_form, field).data = value
        
        # Password change form
        password_form = PasswordChangeForm()
        
        # Get menu items for navigation
        user_role = user_profile.get('entity_type', 'patient') if user_profile else 'patient'
        menu_items = generate_menu_for_role(user_role)
        
        return render_template(
            'auth/settings.html',
            profile_form=profile_form,
            password_form=password_form,
            menu_items=menu_items
        )
    except Exception as e:
        current_app.logger.error(f"Settings page error: {str(e)}", exc_info=True)
        flash('An error occurred while loading settings. Please try again.', 'error')
        return redirect(url_for('auth_views.dashboard'))
        
@auth_views_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        # Determine appropriate form based on current user type
        user_profile = ProfileService.get_profile(current_user.user_id)
        
        if user_profile and user_profile.get('entity_type') == 'staff':
            form = StaffProfileForm()
        elif user_profile and user_profile.get('entity_type') == 'patient':
            form = PatientProfileForm()
        else:
            form = ProfileForm()
        
        if form.validate_on_submit():
            # Prepare update data from form
            update_data = {field.name: field.data for field in form if field.name not in ['csrf_token']}
            
            # Use ProfileService to update profile
            result = ProfileService.update_profile(
                user_id=current_user.user_id, 
                update_data=update_data
            )
            
            flash('Profile updated successfully', 'success')
        else:
            # Log form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'error')
    except Exception as e:
        current_app.logger.error(f"Error updating profile: {str(e)}", exc_info=True)
        flash(f'Failed to update profile. Please try again.', 'error')
    
    return redirect(url_for('auth_views.settings'))

@auth_views_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Handle password change form submission"""
    form = PasswordChangeForm()
    
    if form.validate_on_submit():
        try:
            with get_db_session() as session:
                # Find the user
                user = session.query(User).filter_by(user_id=current_user.user_id).first()
                
                if not user:
                    flash('User not found', 'error')
                    return redirect(url_for('auth_views.settings'))
                
                # Verify current password
                if not user.check_password(form.current_password.data):
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('auth_views.settings'))
                
                # Set new password
                user.set_password(form.new_password.data)
                
                # Commit changes
                session.commit()
                
                flash('Password changed successfully', 'success')
        
        except Exception as e:
            current_app.logger.error(f"Password change error: {str(e)}", exc_info=True)
            flash('Failed to change password. Please try again.', 'error')
    else:
        # Log form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('auth_views.settings'))

@auth_views_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password request handler"""
    # Create the form instance
    form = ForgotPasswordForm()
    
    if form.validate_on_submit():
        try:
            # Initiate password reset process
            reset_result = ForgotPasswordService.initiate_password_reset(
                form.username_or_email.data
            )
            
            # In a real system, you'd send an email/SMS here
            # For demonstration, we're just logging the reset token
            current_app.logger.info(f"Password reset token: {reset_result.get('reset_token')}")
            
            flash('Password reset instructions have been sent to your email or phone if the account exists.', 'success')
            return redirect(url_for('auth_views.login'))
        
        except ValueError as ve:
            # Handle specific value errors (like user not found)
            current_app.logger.warning(f"Password reset value error: {str(ve)}")
            # Don't expose whether user exists or not for security
            flash('Password reset instructions have been sent if the account exists.', 'info')
            return redirect(url_for('auth_views.login'))
        except Exception as e:
            # Handle general errors
            current_app.logger.error(f"Forgot password error: {str(e)}", exc_info=True)
            flash('An error occurred. Please try again later.', 'error')
    
    # Make sure to pass the form to the template
    return render_template('auth/forgot_password.html', form=form)

@auth_views_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Password reset handler"""
    # Get token from query parameters
    reset_token = request.args.get('token')
    user_id = request.args.get('user_id')
    
    # Create form instance
    form = ResetPasswordForm()
    
    # For GET requests, validate the token
    if request.method == 'GET':
        if not reset_token or not user_id:
            flash('Invalid or missing reset information', 'error')
            return redirect(url_for('auth_views.login'))
        
        try:
            # Validate token
            is_valid_token = ForgotPasswordService.validate_reset_token(
                user_id=user_id, 
                reset_token=reset_token
            )
            
            if not is_valid_token:
                flash('Invalid or expired reset token', 'error')
                return redirect(url_for('auth_views.login'))
                
            # Set the user_id in the form for POST submission
            form.user_id.data = user_id
            
        except Exception as e:
            current_app.logger.error(f"Token validation error: {str(e)}", exc_info=True)
            flash('An error occurred. Please request a new reset link.', 'error')
            return redirect(url_for('auth_views.login'))
    
    # For POST requests, process the form
    if form.validate_on_submit():
        try:
            # Reset password using the service
            reset_result = ForgotPasswordService.reset_password(
                user_id=form.user_id.data,
                reset_token=reset_token,
                new_password=form.new_password.data
            )
            
            flash('Password reset successful. Please log in with your new password.', 'success')
            return redirect(url_for('auth_views.login'))
        
        except ValueError as ve:
            flash(str(ve), 'error')
        except Exception as e:
            current_app.logger.error(f"Password reset error: {str(e)}", exc_info=True)
            flash('An error occurred. Please try again.', 'error')
    
    # Render the reset password form
    return render_template('auth/reset_password.html', form=form, token=reset_token, user_id=user_id)

@auth_views_bp.route('/logout')
@login_required
def logout():
    """Logout the current user"""
    try:
        with get_db_session() as session:
            # Find and invalidate active user sessions
            session.query(UserSession).filter_by(
                user_id=current_user.user_id, 
                is_active=True
            ).update({'is_active': False})
            
            session.commit()
        
        # Log out the user
        logout_user()
        
        flash('You have been logged out', 'info')
        return redirect(url_for('auth_views.login'))
    
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}", exc_info=True)
        flash('An error occurred during logout', 'error')
        return redirect(url_for('auth_views.login'))