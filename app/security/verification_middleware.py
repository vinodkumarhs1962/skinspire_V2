# app/security/verification_middleware.py

from functools import wraps
from flask import redirect, url_for, flash, current_app, request
from flask_login import current_user

from app.services.verification_service import VerificationService

def verification_required(view_func):
    """
    Middleware to enforce verification requirements for protected routes
    
    Usage:
        @app.route('/protected')
        @login_required
        @verification_required
        def protected_view():
            return 'This is protected'
    """
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        # Skip for static files and verification-related routes
        if request.endpoint and ('static' in request.endpoint or 
                                'verification' in request.endpoint or
                                request.endpoint == 'auth_views.staff_approval_request'):
            return view_func(*args, **kwargs)
        
        if not current_user.is_authenticated:
            return view_func(*args, **kwargs)
        
        # Check if verification is required
        phone_required, email_required = VerificationService.verification_required(current_user)
        
        # Check if grace period is still active
        verification_settings = VerificationService.get_verification_settings(current_user.hospital_id)
        grace_period_days = verification_settings.get('verification_grace_period_days', 7)
        
        # TODO: Implement grace period check based on user creation date
        
        # Check verification status
        verification_needed = False
        
        if phone_required and not current_user.is_phone_verified:
            verification_needed = True
            flash('Phone verification required', 'warning')
        
        if email_required and not current_user.is_email_verified:
            verification_needed = True
            flash('Email verification required', 'warning')
        
        if verification_needed:
            # Redirect to verification status page
            return redirect(url_for('verification_views.verification_status'))
        
        return view_func(*args, **kwargs)
    
    return decorated_view