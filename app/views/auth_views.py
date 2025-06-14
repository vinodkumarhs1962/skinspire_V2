# app/views/auth_views.py
# The login page at: http://127.0.0.1:5000/login
# After login, the admin dashboards at:

# http://127.0.0.1:5000/admin/system-admin-dashboard
# http://127.0.0.1:5000/admin/hospital-admin-dashboard


from flask import (
    Blueprint, render_template, redirect, url_for, request, 
    flash, current_app, session, jsonify
)
from flask_login import login_user, current_user, logout_user, login_required
import json
# from datetime import datetime
import datetime
from sqlalchemy import text

# Import necessary forms
from app.forms.auth_forms import (
    LoginForm, RegistrationForm, ProfileForm, 
    StaffProfileForm, PatientProfileForm,
    PasswordChangeForm, ForgotPasswordForm, ResetPasswordForm, StaffApprovalRequestForm,
    EnhancedRegistrationForm
)


# Import services
from app.services.profile_service import ProfileService
from app.services.forgot_password_service import ForgotPasswordService
from app.services.approval_service import ApprovalService

# Import database service
from app.services.database_service import get_db_session, get_detached_copy, get_entity_dict

# Import verification middleware
from app.security.verification_middleware import verification_required

# Import models
from app.models.transaction import User, UserSession

# Import utilities
from app.utils.menu_utils import get_menu_items, generate_menu_for_role

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

    # Add Hospital import
    from app.models.master import Hospital

    # Fetch hospital for logo
    hospital = None
    try:
        with get_db_session() as session:
            hospital = session.query(Hospital).first()
    except Exception as e:
        current_app.logger.error(f"Hospital fetch error: {str(e)}")

    if form.validate_on_submit():
        try:
            # Import phone normalization utility
            from app.utils.phone_utils import normalize_phone_number

            # Get raw input from login form
            raw_username = form.username.data
            
            with get_db_session() as session:
                # Find user by direct match first (backward compatibility)
                user = session.query(User).filter_by(user_id=raw_username).first()
                
                # If not found, try normalizing the phone number
                if not user:
                    # Normalize the entered phone number
                    normalized_phone = normalize_phone_number(raw_username)
                    user = session.query(User).filter_by(user_id=normalized_phone).first()
                
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
    
    return render_template('auth/login.html', form=form, hospital=hospital)

# Fix for register function in auth_views.py
@auth_views_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration view with validation"""
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))
        
    form = RegistrationForm()
    from app.models.master import Hospital
    from app.services.database_service import get_db_session
    # Fetch hospital for logo
    hospital = None
    try:
        with get_db_session() as session:
            hospital = session.query(Hospital).first()
            current_app.logger.info(f"Hospital for registration: {hospital}")
    except Exception as e:
        current_app.logger.error(f"Hospital fetch error: {str(e)}")

    if form.validate_on_submit():
        try:
            from app.services.database_service import get_db_session, get_detached_copy
            from app.models.master import Staff, Patient, Hospital, Branch
            import uuid
            from flask import session as flask_session
            
            # Import phone utils for normalization
            from app.utils.phone_utils import normalize_phone_number
            
            # Get raw phone number
            raw_phone_number = form.phone.data
            
            # Normalize phone number to E.164 format
            normalized_phone = normalize_phone_number(raw_phone_number)
            
            # Check if normalized number exceeds database length limit
            if len(normalized_phone) > 15:
                flash('Phone number exceeds maximum length', 'error')
                return render_template('auth/register.html', form=form)
            
            # Log the normalization for debugging
            current_app.logger.info(f"Normalized phone from {raw_phone_number} to {normalized_phone}")
            
            # Use normalized phone as user_id
            user_id = normalized_phone
            
            # Store user type
            user_type = form.user_type.data
            
            with get_db_session() as db_session:
                # Check if user already exists
                existing_user = db_session.query(User).filter_by(user_id=user_id).first()
                
                if existing_user:
                    flash('User with this phone number already exists', 'error')
                    return render_template('auth/register.html', form=form)
                
                # Get the default hospital and branch
                default_hospital = db_session.query(Hospital).first()
                if not default_hospital:
                    flash('No hospital configured in the system', 'error')
                    return render_template('auth/register.html', form=form)
                
                default_branch = db_session.query(Branch).filter_by(hospital_id=default_hospital.hospital_id).first()
                
                # Store hospital_id outside the session
                hospital_id = default_hospital.hospital_id
                
                # Create entity based on user type
                entity_id = uuid.uuid4()
                
                # Prepare common personal and contact info
                personal_info = json.dumps({
                    'title': form.title.data,
                    'first_name': form.first_name.data,
                    'last_name': form.last_name.data
                })
                
                # Store both normalized and original phone number
                contact_info = json.dumps({
                    'phone': normalized_phone,  # Normalized format for system use
                    'display_phone': raw_phone_number,  # Original format for display
                    'email': form.email.data
                })
                
                # Rest of your existing registration code...
                if user_type == 'staff':
                    # Extract first and last name
                    first_name = form.first_name.data
                    last_name = form.last_name.data
                    # Create staff entity
                    staff = Staff(
                        staff_id=entity_id,
                        hospital_id=hospital_id,
                        branch_id=default_branch.branch_id if default_branch else None,
                        personal_info=personal_info,
                        contact_info=contact_info,
                        professional_info=json.dumps({}),
                        employment_info=json.dumps({}),
                        first_name=first_name,
                        last_name=last_name
                    )
                    db_session.add(staff)
                    db_session.flush()
                    
                    # Update the full_name column directly with SQL
                    db_session.execute(
                        text("UPDATE staff SET full_name = :full_name WHERE staff_id = :staff_id"),
                        {"full_name": f"{first_name} {last_name}".strip(), "staff_id": staff.staff_id}
                    )
                    
                elif user_type == 'patient':
                    # Create patient entity with both JSON fields and dedicated fields
                    first_name = form.first_name.data
                    last_name = form.last_name.data
                    
                    # Create patient entity
                    patient = Patient(
                        patient_id=entity_id,
                        hospital_id=hospital_id,
                        branch_id=default_branch.branch_id if default_branch else None,
                        # Set both JSON and dedicated fields
                        personal_info=personal_info,  # This already contains first_name and last_name
                        contact_info=contact_info,
                        emergency_contact=json.dumps({}),
                        preferences=json.dumps({}),
                        # Set dedicated fields explicitly
                        first_name=first_name,
                        last_name=last_name,
                    )
                    db_session.add(patient)
                    db_session.flush()
                    
                    # Update the full_name column directly with SQL
                    db_session.execute(
                        text("UPDATE patients SET full_name = :full_name WHERE patient_id = :patient_id"),
                        {"full_name": f"{first_name} {last_name}".strip(), "patient_id": patient.patient_id}
                    )
                    
                    current_app.logger.info(f"Created patient with direct full_name update: {first_name} {last_name}")
                
                # Create new user with reference to entity
                new_user = User(
                    user_id=user_id,  # Use normalized phone as user_id
                    entity_type=user_type,
                    entity_id=entity_id,
                    hospital_id=hospital_id
                )
                
                # Set password
                new_user.set_password(form.password.data)
                
                # Add user to session
                db_session.add(new_user)
                
                # Log the user creation
                current_app.logger.info(f"Created user account for {user_id}")
                
                # Attempt to commit
                current_app.logger.info("Attempting to commit changes to database...")
                db_session.commit()
                
            # Outside the database session
            current_app.logger.info(f"User registered successfully: {normalized_phone}")
            
            # Check if verification is required
            from app.services.verification_service import VerificationService
            
            with get_db_session() as verification_session:
                user = verification_session.query(User).filter_by(user_id=normalized_phone).first()
                if user:
                    phone_required, email_required = VerificationService.verification_required(user)
                    
                    # Store important data in session
                    flask_session['new_user_id'] = normalized_phone
                    
                    # If staff, set staff registration user ID and redirect to approval form
                    if user_type == 'staff':
                        flask_session['staff_registration_user_id'] = normalized_phone
                        current_app.logger.info(f"Staff registration - redirecting to approval form for {normalized_phone}")
                        
                        # Auto-login to access approval form
                        login_user(user)
                        
                        flash('Registration successful! Please submit additional information for approval.', 'success')
                        return redirect(url_for('auth_views.staff_approval_request'))
                    
                    # If verification is required, redirect to verification
                    elif phone_required or email_required:
                        flash('Registration successful! Please complete verification to access all features.', 'success')
                        return redirect(url_for('verification_views.verification_status'))
                    
                    # Otherwise, standard patient flow
                    else:
                        flash('Registration successful! Please log in.', 'success')
                        return redirect(url_for('auth_views.login'))
            
            # Default fallback if something went wrong
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
    
    return render_template('auth/register.html', form=form, hospital=hospital)
    
@auth_views_bp.route('/dashboard')
@login_required
@verification_required
def dashboard():
    """Dashboard view with dynamic menu generation"""
    # Log dashboard access
    current_app.logger.info("Dashboard route accessed")
    
    # Log user details for debugging
    current_app.logger.info(f"Current User: {current_user}")
    current_app.logger.info(f"Is Authenticated: {current_user.is_authenticated}")
    current_app.logger.info(f"User ID: {current_user.user_id}")
    
    # Access Flask session correctly
    from flask import session as flask_session
    current_app.logger.info(f"Session User ID: {flask_session.get('user_id')}")
    current_app.logger.info(f"Session Contents: {flask_session}")
    
    # Get hospital information for logo display
    try:
        from app.models.master import Hospital
        from app.models.transaction import User
        
        hospital = None
        hospital_id = getattr(current_user, 'hospital_id', None)
        
        # Get fresh user data and hospital within a session
        with get_db_session() as db_session:
            # Get fresh user to avoid detached instance issues
            user = db_session.query(User).filter_by(user_id=current_user.user_id).first()
            
            if hospital_id:
                hospital = db_session.query(Hospital).filter_by(
                    hospital_id=hospital_id
                ).first()
                
                # Debug log for hospital logo
                if hospital and hasattr(hospital, 'logo') and hospital.logo:
                    current_app.logger.info(f"Hospital has logo: {hospital.logo is not None}")
            
            # Create detached copies for use outside the session
            if user:
                user_detached = get_detached_copy(user)
            if hospital:
                hospital_detached = get_detached_copy(hospital)
    
        # Use user_detached outside the session context for menu generation
        if 'user_detached' in locals():
            entity_type = getattr(user_detached, 'entity_type', 'patient')
            menu_items = generate_menu_for_role(entity_type)
        else:
            # Fallback if user can't be found
            entity_type = getattr(current_user, 'entity_type', 'patient') 
            menu_items = generate_menu_for_role(entity_type)
            
    except Exception as e:
        current_app.logger.error(f"Error loading user/hospital data: {str(e)}", exc_info=True)
        # Fall back to entity_type from current_user in case of errors
        entity_type = getattr(current_user, 'entity_type', 'patient')
        menu_items = generate_menu_for_role(entity_type)
        hospital_detached = None
    
    # Pass data to template
    template_args = {
        'menu_items': menu_items,
        'user': user_detached if 'user_detached' in locals() else None
    }
    
    if 'hospital_detached' in locals() and hospital_detached:
        template_args['hospital'] = hospital_detached
    
    current_app.logger.info(f"Template args: {template_args}")
    return render_template('dashboard/index.html', **template_args)

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

# Enhanced register view to be added to app/views/auth_views.py

@auth_views_bp.route('/register-enhanced', methods=['GET', 'POST'])
def register_enhanced():
    """Enhanced user registration view with branch selection and approval workflow"""
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))
        
    form = EnhancedRegistrationForm()
    
    # Handle AJAX request for branch population
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'GET':
        hospital_id = request.args.get('hospital_id')
        if hospital_id:
            form.populate_branches(hospital_id)
            return jsonify({
                'branches': [{'id': id, 'name': name} for id, name in form.branch_id.choices]
            })
    
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
                    return render_template('auth/register_enhanced.html', form=form)
                
                # Get the selected hospital and branch
                hospital_id = form.hospital_id.data if form.hospital_id.data else None
                branch_id = form.branch_id.data if form.branch_id.data else None
                
                # For patient registration without hospital selection, get default hospital
                if form.user_type.data == 'patient' and not hospital_id:
                    default_hospital = session.query(Hospital).first()
                    if not default_hospital:
                        flash('No hospital configured in the system', 'error')
                        return render_template('auth/register_enhanced.html', form=form)
                    hospital_id = default_hospital.hospital_id
                
                # Ensure we have a hospital_id
                if not hospital_id:
                    flash('Please select a hospital', 'error')
                    return render_template('auth/register_enhanced.html', form=form)
                
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
                        hospital_id=hospital_id,
                        branch_id=branch_id,
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
                        hospital_id=hospital_id,
                        branch_id=branch_id,
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
                    hospital_id=hospital_id,
                    # Set staff users as inactive until approved
                    is_active=form.user_type.data != 'staff'
                )
                
                # Set password
                new_user.set_password(form.password.data)
                
                # Add user to session
                session.add(new_user)
                
                # Commit changes
                session.commit()
                
                # For staff users, redirect to approval request form
                if form.user_type.data == 'staff':
                    # Store user_id in session for approval form
                    session['staff_registration_user_id'] = form.phone.data
                    flash('Registration successful! Please submit additional information for approval.', 'success')
                    return redirect(url_for('auth_views.staff_approval_request'))
                else:
                    # For patients, go straight to login
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
    
    return render_template('auth/register_enhanced.html', form=form)

@auth_views_bp.route('/staff-approval-request', methods=['GET', 'POST'])
@login_required
def staff_approval_request():
    """Staff approval request form after registration"""
    # Log that this route was accessed
    current_app.logger.info("Staff approval request route accessed")
    
    # Import models needed
    from app.models.master import Staff, Hospital, Branch
    from app.models.config import RoleMaster
    from app.models.transaction import StaffApprovalRequest
    from app.services.approval_service import ApprovalService
    
    # Check if user is authenticated
    if not current_user.is_authenticated:
        # Try to get the staff_registration_user_id from session
        staff_user_id = session.get('staff_registration_user_id')
        
        if staff_user_id:
            # Log the attempt to find user
            current_app.logger.info(f"Attempting to find user with ID: {staff_user_id}")
            
            # Try to get and login the user
            with get_db_session() as db_session:
                user = db_session.query(User).filter_by(user_id=staff_user_id).first()
                
                if user:
                    # Create a detached copy for login
                    detached_user = get_detached_copy(user)
                    login_user(detached_user)
                    current_app.logger.info(f"Auto-logged in user: {staff_user_id}")
                else:
                    current_app.logger.warning(f"Could not find user with ID: {staff_user_id}")
                    flash('User not found. Please login first.', 'error')
                    return redirect(url_for('auth_views.login'))
        else:
            current_app.logger.warning("No staff_registration_user_id in session")
            flash('Please login first', 'error')
            return redirect(url_for('auth_views.login'))
    
    # Now check if user is staff
    if not hasattr(current_user, 'entity_type') or current_user.entity_type != 'staff':
        current_app.logger.warning(f"User {current_user.user_id} tried to access staff approval but is not staff")
        flash('This page is only available for staff members', 'error')
        return redirect(url_for('auth_views.dashboard'))
    
    # Check for existing requests first
    with get_db_session() as session:
        # Query latest request
        existing_request = session.query(StaffApprovalRequest).filter_by(
            staff_id=current_user.entity_id
        ).order_by(StaffApprovalRequest.created_at.desc()).first()
        
        # For pending requests, show status page
        if existing_request and existing_request.status == 'pending' and 'resubmit' not in request.args:
            status = ApprovalService.get_request_status(current_user.user_id)
            flash('Your approval request is pending review.', 'info')
            return render_template('auth/staff_approval_status.html', status=status)
        
        # For approved requests, redirect to dashboard
        if existing_request and existing_request.status == 'approved' and 'resubmit' not in request.args:
            flash('Your profile has already been approved!', 'success')
            return redirect(url_for('auth_views.dashboard'))
        
        # For rejected requests, allow resubmission with warning
        if existing_request and existing_request.status == 'rejected':
            flash('Your previous request was rejected. Please update your information and submit again.', 'warning')
        
        # Get staff information
        staff = session.query(Staff).filter_by(staff_id=current_user.entity_id).first()
        
        if not staff:
            current_app.logger.error(f"Staff entity not found for user: {current_user.user_id}")
            flash('Staff profile not found', 'error')
            return redirect(url_for('auth_views.dashboard'))
        
        # Get hospital and branch information
        hospital = session.query(Hospital).filter_by(hospital_id=staff.hospital_id).first()
        branch = None
        if staff.branch_id:
            branch = session.query(Branch).filter_by(branch_id=staff.branch_id).first()
    
    # Create form
    form = StaffApprovalRequestForm()
    
    # Populate form with hospital, branch, and role information
    if hospital:
        hospital_id = hospital.hospital_id
        
        # Set hospital name and populate branches if the method exists
        if hasattr(form, 'populate_branches'):
            form.hospital_name = hospital.name
            form.populate_branches(hospital_id)
        
        # Populate roles if the method exists
        if hasattr(form, 'populate_roles'):
            try:
                form.populate_roles(hospital_id)
                current_app.logger.info(f"Populated roles: {form.role_choices}")
            except Exception as e:
                current_app.logger.error(f"Error populating roles: {str(e)}")
    
    # Set default branch in dropdown
    if branch and hasattr(form, 'default_branch_name'):
        form.default_branch_name = branch.name
        # Pre-select current branch in dropdown if the form has branch_id
        if hasattr(form, 'branch_id') and hasattr(form, 'process'):
            form.branch_id.default = str(branch.branch_id)
            form.process()  # This is needed to apply the default value
    
    # Log form data on submission for debugging
    if request.method == 'POST':
        current_app.logger.info(f"Form data submitted: {request.form}")
        current_app.logger.info(f"Form errors: {form.errors}")
        
        # Log validation state
        for field_name, field in form._fields.items():
            if field_name != 'csrf_token':
                current_app.logger.info(f"Field '{field_name}': value='{field.data}', valid={field.validate(form)}")
    
    if form.validate_on_submit():
        try:
            current_app.logger.info("Form validated successfully, processing submission")
            
            # Build request data
            request_data = {
                'qualifications': form.qualifications.data,
                'experience': form.experience.data,
                'specialization': form.specialization.data,
                'comments': form.comments.data
            }
            
            # Add reference if it exists
            if hasattr(form, 'reference') and form.reference.data:
                request_data['reference'] = form.reference.data
                
            # Add branch_id if available in the form
            if hasattr(form, 'branch_id') and form.branch_id.data:
                request_data['branch_id'] = form.branch_id.data
                
            # Add role_id if available in the form - note it's an integer
            if hasattr(form, 'role_id') and form.role_id.data and form.role_id.data != 0:
                request_data['role_id'] = form.role_id.data
            
            # Submit approval request using service
            current_app.logger.info(f"Submitting approval request with data: {request_data}")
            result = ApprovalService.submit_approval_request(current_user.user_id, request_data)
            
            if result.get('success'):
                flash('Your approval request has been submitted. You will be notified once it is processed.', 'success')
                return redirect(url_for('auth_views.dashboard'))
            else:
                flash(result.get('message', 'Failed to submit approval request.'), 'error')
        except Exception as e:
            current_app.logger.error(f"Error submitting approval request: {str(e)}", exc_info=True)
            flash('An error occurred while submitting your request. Please try again.', 'error')
    else:
        # Make sure form errors are displayed
        if request.method == 'POST':
            for field_name, errors in form.errors.items():
                for error in errors:
                    field_label = getattr(form, field_name).label.text if hasattr(form, field_name) else field_name
                    flash(f'{field_label}: {error}', 'error')
                    current_app.logger.error(f"Form validation error: {field_label}: {error}")
    
    # Get menu items for navigation
    menu_items = generate_menu_for_role(current_user.entity_type)
    
    # Log that we're rendering the template
    current_app.logger.info("Rendering staff approval request form")
    
    return render_template(
        'auth/staff_approval_request.html',
        form=form,
        menu_items=menu_items
    )