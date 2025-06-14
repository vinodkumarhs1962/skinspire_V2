# app/views/verification_views.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, session
from flask_login import current_user, login_required
import datetime
import logging

# Import verification forms
from app.forms.verification_forms import (
    PhoneVerificationForm,
    EmailVerificationForm,
    VerificationCodeForm
)

# Import services
from app.services.verification_service import VerificationService
from app.utils.menu_utils import generate_menu_for_role

# Create blueprint
verification_views_bp = Blueprint('verification_views', __name__)

# Set up logger
logger = logging.getLogger(__name__)

@verification_views_bp.context_processor
def inject_current_year():
    """Inject current year into all templates"""
    return {'current_year': datetime.datetime.now().year}

@verification_views_bp.route('/verify-phone', methods=['GET', 'POST'])
@login_required
def verify_phone():
    """Phone verification view"""
    # Check if already verified
    if current_user.is_phone_verified:
        flash('Your phone number is already verified', 'info')
        return redirect(url_for('auth_views.settings'))
    
    # Create form
    form = PhoneVerificationForm()
    verification_form = VerificationCodeForm()
    verification_form.code_type.data = 'phone'
    
    # Pre-populate phone field with user's phone number
    if request.method == 'GET':
        form.phone.data = current_user.phone
    
    # Process form submission
    if form.validate_on_submit():
        result = VerificationService.initiate_phone_verification(
            current_user.user_id, 
            form.phone.data
        )
        
        if result.get('success'):
            flash('Verification code sent to your phone. Please enter the code to complete verification.', 'success')
            # Store the phone number in session for validation
            session['verifying_phone'] = form.phone.data
            # Show the code verification form
            return render_template(
                'auth/verify_phone.html',
                form=form,
                verification_form=verification_form,
                show_verification=True,
                menu_items=generate_menu_for_role(current_user.entity_type)
            )
        else:
            flash(result.get('message', 'Failed to send verification code.'), 'error')
    
    # Get menu items for navigation
    menu_items = generate_menu_for_role(current_user.entity_type)
    
    return render_template(
        'auth/verify_phone.html',
        form=form,
        verification_form=verification_form,
        show_verification=False,
        menu_items=menu_items
    )

@verification_views_bp.route('/verify-email', methods=['GET', 'POST'])
@login_required
def verify_email():
    """Email verification view"""
    # Check if already verified
    if current_user.is_email_verified:
        flash('Your email is already verified', 'info')
        return redirect(url_for('auth_views.settings'))
    
    # Create form
    form = EmailVerificationForm()
    verification_form = VerificationCodeForm()
    verification_form.code_type.data = 'email'
    
    # Pre-populate email field with user's email
    if request.method == 'GET':
        form.email.data = current_user.email
    
    # Process form submission
    if form.validate_on_submit():
        result = VerificationService.initiate_email_verification(
            current_user.user_id, 
            form.email.data
        )
        
        if result.get('success'):
            flash('Verification code sent to your email. Please enter the code to complete verification.', 'success')
            # Store the email in session for validation
            session['verifying_email'] = form.email.data
            # Show the code verification form
            return render_template(
                'auth/verify_email.html',
                form=form,
                verification_form=verification_form,
                show_verification=True,
                menu_items=generate_menu_for_role(current_user.entity_type)
            )
        else:
            flash(result.get('message', 'Failed to send verification code.'), 'error')
    
    # Get menu items for navigation
    menu_items = generate_menu_for_role(current_user.entity_type)
    
    return render_template(
        'auth/verify_email.html',
        form=form,
        verification_form=verification_form,
        show_verification=False,
        menu_items=menu_items
    )

@verification_views_bp.route('/verify-code', methods=['POST'])
@login_required
def verify_code():
    """Process verification code submission"""
    # Create form
    form = VerificationCodeForm()
    
    # Log form data for debugging
    logger.info(f"Verify code form data: code_type={form.code_type.data}, code={form.code.data}")

    if form.validate_on_submit():
        code_type = form.code_type.data
        
        # Check if resend button was clicked
        if form.resend.data:
            result = VerificationService.resend_verification_code(
                current_user.user_id,
                code_type
            )
            
            if result.get('success'):
                flash('Verification code resent. Please check your phone or email.', 'success')
            else:
                flash(result.get('message', 'Failed to resend verification code.'), 'error')
                
            # Redirect back to the appropriate verification page
            if code_type == 'phone':
                return redirect(url_for('verification_views.verify_phone'))
            else:
                return redirect(url_for('verification_views.verify_email'))
                
        # Process verification code
        result = VerificationService.verify_code(
            current_user.user_id,
            code_type,
            form.code.data
        )
        
        if result.get('success'):
            flash('Verification successful!', 'success')
            return redirect(url_for('auth_views.settings'))
        else:
            flash(result.get('message', 'Invalid verification code.'), 'error')
            
            # Redirect back to the appropriate verification page
            if code_type == 'phone':
                return redirect(url_for('verification_views.verify_phone'))
            else:
                return redirect(url_for('verification_views.verify_email'))
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{error}", 'error')
        
        # Redirect back based on code type
        code_type = form.code_type.data
        if code_type == 'phone':
            return redirect(url_for('verification_views.verify_phone'))
        else:
            return redirect(url_for('verification_views.verify_email'))

@verification_views_bp.route('/verification-status', methods=['GET'])
@login_required
def verification_status():
    """View to display verification status"""
    # Get verification status
    status = VerificationService.get_verification_status(current_user.user_id)
    
    # Get menu items for navigation
    menu_items = generate_menu_for_role(current_user.entity_type)
    
    return render_template(
        'auth/verification_status.html',
        status=status,
        menu_items=menu_items
    )