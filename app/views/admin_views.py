# app/views/admin_views.py

import uuid
import json
import datetime
from sqlalchemy import func, desc

from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, current_app
from flask_login import login_required, current_user
import requests
from app.utils.menu_utils import generate_menu_for_role

from app.models.master import Hospital, Branch, Staff, HospitalSettings 
from app.models.transaction import User, StaffApprovalRequest
from app.services.hospital_settings_service import HospitalSettingsService
from app.services.approval_service import ApprovalService
from app.services.database_service import get_db_session, get_detached_copy, get_entity_dict

admin_views_bp = Blueprint('admin_views', __name__, url_prefix='/admin')

# Decorator to check admin access
def admin_required(f):
    """Decorator to check if user has admin role"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(current_user, 'entity_type') or current_user.entity_type != 'staff':
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('auth_views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check system admin access - add this to the file
def system_admin_required(f):
    """Decorator to check if user has system admin role"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This is a simplified check - in production should check roles in DB
        # For now, we'll check if the user has a specific attribute or role
        has_permission = False
        
        # Check user roles - adjust this logic based on your role implementation
        try:
            # Example: check if user has system admin role
            # This can be enhanced based on your role structure
            if hasattr(current_user, 'roles'):
                for role in current_user.roles:
                    if role.role_name == 'system_admin':
                        has_permission = True
                        break
            
            # Temporary fallback - in development, allow staff to access
            if hasattr(current_user, 'entity_type') and current_user.entity_type == 'staff':
                has_permission = True
        except:
            pass
            
        if not has_permission:
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('auth_views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to check hospital admin access - add this to the file
def hospital_admin_required(f):
    """Decorator to check if user has hospital admin role"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This is a simplified check - in production should check roles in DB
        has_permission = False
        
        # Check user roles - adjust this logic based on your role implementation
        try:
            # Example: check if user has hospital admin role
            # This can be enhanced based on your role structure
            if hasattr(current_user, 'roles'):
                for role in current_user.roles:
                    if role.role_name == 'hospital_admin':
                        has_permission = True
                        break
            
            # Temporary fallback - in development, allow staff to access
            if hasattr(current_user, 'entity_type') and current_user.entity_type == 'staff':
                has_permission = True
        except:
            pass
            
        if not has_permission:
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('auth_views.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# System Admin Dashboard - add to existing admin_views.py
@admin_views_bp.route('/system-admin-dashboard')
@login_required
#@system_admin_required
def system_admin_dashboard():
    """System Administrator Dashboard"""
    try:
        with get_db_session() as session:
            # Get summary statistics
            total_hospitals = session.query(func.count(Hospital.hospital_id)).scalar() or 0
            total_branches = session.query(func.count(Branch.branch_id)).scalar() or 0
            
            # Count hospital admins (simplified - in reality, would check roles)
            total_admins = session.query(func.count(User.user_id)).filter(
                User.entity_type == 'staff'
            ).scalar() or 0
            
            # Count active users
            active_users = session.query(func.count(User.user_id)).filter(
                User.is_active == True
            ).scalar() or 0
            
            # Get recent hospitals
            hospitals = session.query(Hospital).order_by(
                Hospital.created_at.desc()
            ).limit(5).all()
            
            # Convert to dict for template
            hospitals = [get_entity_dict(h) for h in hospitals]
            
            # Get recent admin accounts
            admins = session.query(User).filter(
                User.entity_type == 'staff'
            ).order_by(
                User.created_at.desc()
            ).limit(5).all()
            
            # Convert to dict and add hospital name
            admin_list = []
            for admin in admins:
                admin_dict = get_entity_dict(admin)
                
                # Get hospital name (if any)
                if admin.hospital_id:
                    hospital = session.query(Hospital).filter(
                        Hospital.hospital_id == admin.hospital_id
                    ).first()
                    if hospital:
                        admin_dict['hospital_name'] = hospital.name
                
                admin_list.append(admin_dict)
            
            # Get recent activity logs (simplified - would typically come from a logging table)
            activity_logs = []
            
            # Get the current user's hospital for logo display
            hospital_id = getattr(current_user, 'hospital_id', None)
            if hospital_id:
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                if hospital:
                    # Create a detached copy for template use
                    detached_hospital = get_detached_copy(hospital)
                    current_user.hospital = detached_hospital
        
        # Get menu items for navigation
        menu_items = generate_menu_for_role(current_user.entity_type)
        current_app.logger.info("System admin dashboard accessed")
        return render_template(
            'admin/system_admin_dashboard.html',
            menu_items=menu_items,
            total_hospitals=total_hospitals,
            total_branches=total_branches,
            total_admins=total_admins,
            active_users=active_users,
            hospitals=hospitals,
            admins=admin_list,
            activity_logs=activity_logs
        )
    
    except Exception as e:
        current_app.logger.error(f"Error loading system admin dashboard: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('auth_views.dashboard'))

# Hospital Admin Dashboard - add to existing admin_views.py
@admin_views_bp.route('/hospital-admin-dashboard')
@login_required
#@hospital_admin_required
def hospital_admin_dashboard():
    """Hospital Administrator Dashboard"""
    try:
        # Get current hospital ID
        hospital_id = getattr(current_user, 'hospital_id', None)
        
        if not hospital_id:
            flash("No hospital associated with your account", 'error')
            return redirect(url_for('auth_views.dashboard'))
        
        with get_db_session() as session:
            # Get hospital information
            hospital = session.query(Hospital).filter(
                Hospital.hospital_id == hospital_id
            ).first()
            
            if not hospital:
                flash("Hospital not found", 'error')
                return redirect(url_for('auth_views.dashboard'))
            
            # Create a detached copy of hospital with logo for template use
            detached_hospital = get_detached_copy(hospital)
            current_user.hospital = detached_hospital
            
            # Convert hospital to dict
            hospital = get_entity_dict(hospital)
            
            # Get branch count
            branch_count = session.query(func.count(Branch.branch_id)).filter(
                Branch.hospital_id == hospital_id
            ).scalar() or 0
            
            # Get staff count
            staff_count = session.query(func.count(Staff.staff_id)).filter(
                Staff.hospital_id == hospital_id
            ).scalar() or 0
            
            # Get patient count (assuming Patient model exists)
            patient_count = 0  # Placeholder
            
            # Get pending approval requests
            pending_approvals = session.query(StaffApprovalRequest).filter(
                StaffApprovalRequest.hospital_id == hospital_id,
                StaffApprovalRequest.status == 'pending'
            ).order_by(
                StaffApprovalRequest.created_at.desc()
            ).limit(3).all()
            
            # Convert to dict and add staff info
            approval_list = []
            for approval in pending_approvals:
                approval_dict = get_entity_dict(approval)
                
                # Get staff info
                staff = session.query(Staff).filter(
                    Staff.staff_id == approval.staff_id
                ).first()
                
                if staff:
                    # Add staff info to approval dict
                    approval_dict['staff_info'] = {
                        'personal_info': json.loads(staff.personal_info) if isinstance(staff.personal_info, str) else staff.personal_info,
                        'contact_info': json.loads(staff.contact_info) if isinstance(staff.contact_info, str) else staff.contact_info
                    }
                
                approval_list.append(approval_dict)
            
            # Get pending approval count
            pending_approvals_count = session.query(func.count(StaffApprovalRequest.request_id)).filter(
                StaffApprovalRequest.hospital_id == hospital_id,
                StaffApprovalRequest.status == 'pending'
            ).scalar() or 0
            
            # Get branches
            branches = session.query(Branch).filter(
                Branch.hospital_id == hospital_id
            ).order_by(
                Branch.name
            ).limit(5).all()
            
            # Convert to dict
            branch_list = [get_entity_dict(b) for b in branches]
            
            # Get staff members
            staff_members = session.query(Staff).filter(
                Staff.hospital_id == hospital_id
            ).order_by(
                Staff.created_at.desc()
            ).limit(5).all()
            
            # Convert to dict
            staff_list = []
            for staff in staff_members:
                staff_dict = get_entity_dict(staff)
                
                # Get branch name if available
                if staff.branch_id:
                    branch = session.query(Branch).filter(
                        Branch.branch_id == staff.branch_id
                    ).first()
                    if branch:
                        staff_dict['branch_name'] = branch.name
                
                staff_list.append(staff_dict)
            
            # Get verification settings
            verification_settings = HospitalSettingsService.get_settings(hospital_id, "verification")
            
            # Get roles for the hospital (simplified - would check role assignment table)
            roles = []  # Placeholder
            
        # Get menu items for navigation
        menu_items = generate_menu_for_role(current_user.entity_type)
        current_app.logger.info("Hospital admin dashboard accessed")
        return render_template(
            'admin/hospital_admin_dashboard.html',
            menu_items=menu_items,
            hospital=hospital,
            branch_count=branch_count,
            staff_count=staff_count,
            patient_count=patient_count,
            pending_approvals=approval_list,
            pending_approvals_count=pending_approvals_count,
            branches=branch_list,
            staff_members=staff_list,
            verification_settings=verification_settings,
            roles=roles
        )
    
    except Exception as e:
        current_app.logger.error(f"Error loading hospital admin dashboard: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('auth_views.dashboard'))

# Staff Approval Admin View - Add to admin_views.py
@admin_views_bp.route('/staff-approvals')
@login_required
@admin_required
def staff_approval_admin():
    """Admin view for managing staff approval requests"""
    try:
        with get_db_session() as session:
            # Get hospital_id from current user
            hospital_id = getattr(current_user, 'hospital_id', None)
            
            # For system admins, get requests from all hospitals if no hospital_id provided
            if not hospital_id and hasattr(current_user, 'is_super_admin') and current_user.is_super_admin:
                hospital_id = request.args.get('hospital_id', None)
            
            # If still no hospital_id, redirect to dashboard
            if not hospital_id:
                flash("No hospital selected", 'error')
                return redirect(url_for('auth_views.dashboard'))
            
            # Get pending requests
            pending_requests = session.query(StaffApprovalRequest).filter(
                StaffApprovalRequest.hospital_id == hospital_id,
                StaffApprovalRequest.status == 'pending'
            ).order_by(
                StaffApprovalRequest.created_at.desc()
            ).all()
            
            # Convert to dict and add staff info
            pending_list = []
            for request in pending_requests:
                request_dict = get_entity_dict(request)
                
                # Get staff info
                staff = session.query(Staff).filter(
                    Staff.staff_id == request.staff_id
                ).first()
                
                if staff:
                    # Add staff info to request dict
                    request_dict['staff_info'] = {
                        'personal_info': json.loads(staff.personal_info) if isinstance(staff.personal_info, str) else staff.personal_info,
                        'contact_info': json.loads(staff.contact_info) if isinstance(staff.contact_info, str) else staff.contact_info
                    }
                
                pending_list.append(request_dict)
        
        # Get menu items for navigation
        menu_items = generate_menu_for_role(current_user.entity_type)
        
        return render_template(
            'auth/staff_approval_admin.html',
            menu_items=menu_items,
            pending_requests=pending_list
        )
    
    except Exception as e:
        current_app.logger.error(f"Error loading staff approval admin: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('auth_views.dashboard'))

# Staff Approval Detail View - Add to admin_views.py
@admin_views_bp.route('/staff-approval/<request_id>')
@login_required
@admin_required
def staff_approval_detail(request_id):
    """Admin view for viewing a specific approval request"""
    try:
        # First get the approval request and staff data
        with get_db_session() as session:
            # Get request details
            approval_request = session.query(StaffApprovalRequest).filter(
                StaffApprovalRequest.request_id == request_id
            ).first()
            
            if not approval_request:
                flash("Request not found", 'error')
                return redirect(url_for('admin_views.staff_approval_admin'))
            
            # Get staff info
            staff = session.query(Staff).filter(
                Staff.staff_id == approval_request.staff_id
            ).first()
            
            # Get user for verification
            user = session.query(User).filter_by(
                entity_id=approval_request.staff_id, 
                entity_type='staff'
            ).first()
            
            # Create detached copies of entities we need outside this session
            approval_request_copy = get_detached_copy(approval_request)
            staff_copy = get_detached_copy(staff)
            user_copy = get_detached_copy(user) if user else None

            # Get available roles
            from app.models.config import RoleMaster
            available_roles = session.query(RoleMaster).filter_by(
                hospital_id=approval_request.hospital_id, 
                status='active'
            ).all()
            
            # Convert roles to list of dicts for template
            role_list = [
                {
                    'role_id': role.role_id, 
                    'role_name': role.role_name
                } for role in available_roles
            ]
        
        # Now handle verification in a separate step with detached copies
        # Use the verification_helpers utility to check status correctly
        from app.utils.verification_helpers import get_user_verification_status
        
        verification_status = {'phone_verified': False, 'email_verified': False}
        if user_copy:
            verification_status = get_user_verification_status(user_copy)
        
        email_verified = verification_status.get('email_verified', False)
        phone_verified = verification_status.get('phone_verified', False)
        
        # Log the verification status
        current_app.logger.info(f"Verification status for {request_id}: phone={phone_verified}, email={email_verified}")
        
        # Get menu items for navigation
        menu_items = generate_menu_for_role(current_user.entity_type)
        
        # Process request data
        try:
            request_data = json.loads(approval_request_copy.request_data) if approval_request_copy.request_data else {}
        except (json.JSONDecodeError, TypeError):
            request_data = {}
            current_app.logger.error(f"Invalid JSON in request_data for approval request {request_id}")
        
        # Prepare request dict
        request_dict = get_entity_dict(approval_request_copy)
        request_dict['request_data'] = request_data
        
        # Prepare staff info
        personal_info = {}
        contact_info = {}
        try:
            if staff_copy.personal_info:
                personal_info = json.loads(staff_copy.personal_info) if isinstance(staff_copy.personal_info, str) else staff_copy.personal_info
        except (json.JSONDecodeError, TypeError):
            personal_info = {}
        
        try:
            if staff_copy.contact_info:
                contact_info = json.loads(staff_copy.contact_info) if isinstance(staff_copy.contact_info, str) else staff_copy.contact_info
        except (json.JSONDecodeError, TypeError):
            contact_info = {}
        
        request_dict['staff_info'] = {
            'personal_info': personal_info,
            'contact_info': contact_info
        }
        
        # Add verification status
        request_dict['email_verified'] = email_verified
        request_dict['phone_verified'] = phone_verified
        
        # IMPORTANT: Explicitly set the status to ensure it's available in the template
        # This is crucial for the conditional rendering of approval/reject buttons
        request_dict['status'] = approval_request_copy.status
        
        # Add debug logging to verify what's being passed to the template
        current_app.logger.info(f"Request details for template: status={request_dict['status']}, " +
                              f"email_verified={request_dict['email_verified']}, " + 
                              f"phone_verified={request_dict['phone_verified']}")
        
        return render_template(
            'auth/staff_approval_detail.html',
            menu_items=menu_items,
            request=request_dict,
            available_roles=role_list
        )
    
    except Exception as e:
        current_app.logger.error(f"Error loading approval detail: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('admin_views.staff_approval_admin'))

# Process Approval - Add to admin_views.py
@admin_views_bp.route('/process-approval/<request_id>', methods=['POST'])
@login_required
@admin_required
def process_approval(request_id):
    """Process approval decision (approve/reject)"""
    try:
        # Get action and notes
        action = request.form.get('action')
        notes = request.form.get('notes', '')
        role_id = request.form.get('role_id')
        
        if action not in ['approve', 'reject']:
            flash('Invalid action', 'error')
            return redirect(url_for('admin_views.staff_approval_detail', request_id=request_id))
        
        # Prepare request data
        approval_data = {
            'notes': notes,
            'approver_id': current_user.user_id
        }
        
        # Add role information for approval
        if role_id and role_id != '0':
            approval_data['role_id'] = int(role_id)
        
        # Use approval service to process request
        if action == 'approve':
            # Check verification status before approval
            with get_db_session() as session:
                # Find the request
                approval_request = session.query(StaffApprovalRequest).filter_by(
                    request_id=request_id
                ).first()
                
                if not approval_request:
                    flash('Approval request not found', 'error')
                    return redirect(url_for('admin_views.staff_approval_admin'))
                
                # Get user for verification check
                user = session.query(User).filter_by(
                    entity_id=approval_request.staff_id, 
                    entity_type='staff'
                ).first()
                
                if not user:
                    flash('Associated user not found', 'error')
                    return redirect(url_for('admin_views.staff_approval_admin'))
                
                # Use verification helper to check status correctly
                from app.utils.verification_helpers import get_user_verification_status
                verification_status = get_user_verification_status(user)
                
                # Only allow approval if both email and phone are verified
                if not (verification_status.get('email_verified', False) and 
                        verification_status.get('phone_verified', False)):
                    flash('Email and phone verification are required before approval', 'error')
                    return redirect(url_for('admin_views.staff_approval_detail', request_id=request_id))
            
            # Proceed with approval
            result = ApprovalService.approve_request(request_id, current_user.user_id, notes, role_id)
        else:
            result = ApprovalService.reject_request(request_id, current_user.user_id, notes)
        
        if result.get('success'):
            flash(result.get('message', 'Request processed successfully'), 'success')
        else:
            flash(result.get('message', 'Failed to process request'), 'error')
        
        return redirect(url_for('admin_views.staff_approval_admin'))
    
    except Exception as e:
        current_app.logger.error(f"Error processing approval: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('admin_views.staff_approval_admin'))

@admin_views_bp.route('/users')
@login_required
@admin_required
def user_list():
    """User management view"""
    # Get query parameters for filtering
    search = request.args.get('search', '')
    role = request.args.get('role', '')
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Call API to get user list
    try:
        response = requests.get(
            url_for('auth.users', _external=True),
            params={
                'search': search,
                'role': role,
                'status': status,
                'page': page,
                'per_page': per_page
            },
            headers={
                'Authorization': f'Bearer {session.get("auth_token")}'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            users = data.get('users', [])
            total_users = data.get('count', 0)
        else:
            flash('Failed to load users', 'error')
            users = []
            total_users = 0
    except requests.exceptions.RequestException as e:
        flash(f'Connection error: {str(e)}', 'error')
        users = []
        total_users = 0
    
    # Get menu items for navigation
    menu_items = generate_menu_for_role(current_user.entity_type)
    
    return render_template('admin/users.html', 
                          users=users, 
                          total_users=total_users,
                          menu_items=menu_items,
                          search=search,
                          role=role,
                          status=status,
                          page=page,
                          per_page=per_page)

# Add to app/views/admin_views.py

# Locate this function in app/views/admin_views.py and update it
# Updated hospital_settings function using get_detached_copy

@admin_views_bp.route('/hospital/settings', methods=['GET', 'POST'])
@login_required
# Temporarily remove admin_required for testing
def hospital_settings():
    """Hospital settings management view"""
    from app.services.hospital_settings_service import HospitalSettingsService
    from app.services.hospital_logo_service import HospitalLogoService
    from app.models.master import Hospital  # Import Hospital model locally
    
    # Get current hospital ID from user
    hospital_id = getattr(current_user, 'hospital_id', None)
    
    # If hospital_id is None, use a default hospital for testing
    if hospital_id is None:
        # Get first hospital from database
        with get_db_session() as session:
            default_hospital = session.query(Hospital).first()
            if default_hospital:
                hospital_id = default_hospital.hospital_id
                # Log the hospital ID for debugging
                current_app.logger.info(f"Using first hospital found: {hospital_id}")
            else:
                # Create a default hospital if none exists
                current_app.logger.warning("No hospital found in database. Using default ID.")
                hospital_id = "00000000-0000-0000-0000-000000000000"  # Use a placeholder UUID
                flash("No hospital configured. Using default settings.", "warning")
    
    # Handle logo upload or removal
    if request.method == 'POST':
        # Log the form data for debugging
        current_app.logger.info(f"Hospital settings form data: {request.form}")
        current_app.logger.info(f"Files in request: {request.files}")
        
        # Check for logo upload - check for both field names for compatibility
        logo_file = None
        if 'upload_logo' in request.files and request.files['upload_logo'].filename:
            logo_file = request.files['upload_logo']
            current_app.logger.info(f"Found logo in 'upload_logo' field: {logo_file.filename}")
        elif 'hospital_logo' in request.files and request.files['hospital_logo'].filename:
            logo_file = request.files['hospital_logo']
            current_app.logger.info(f"Found logo in 'hospital_logo' field: {logo_file.filename}")
        
        # Process logo file if found
        if logo_file and logo_file.filename:
            try:
                # Use logo service to upload
                result = HospitalLogoService.upload_logo(hospital_id, logo_file)
                
                if result['success']:
                    flash('Logo uploaded successfully', 'success')
                    current_app.logger.info(f"Logo upload success: {result.get('message')}")
                else:
                    flash(result.get('message', 'Failed to upload logo'), 'error')
                    current_app.logger.error(f"Logo upload failed: {result.get('message')}")
            
            except Exception as e:
                current_app.logger.error(f"Logo upload error: {str(e)}", exc_info=True)
                flash(f'An error occurred: {str(e)}', 'error')
        
        # Check for logo removal
        elif request.form.get('remove_logo'):
            try:
                with get_db_session() as session:
                    # Find the hospital
                    hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                    
                    if hospital:
                        # Remove existing logo files
                        HospitalLogoService.remove_existing_logo(hospital)
                        
                        # Commit changes
                        session.commit()
                
                flash('Logo removed successfully', 'success')
            
            except Exception as e:
                current_app.logger.error(f"Logo removal error: {str(e)}", exc_info=True)
                flash(f'An error occurred: {str(e)}', 'error')
        
        # Handle verification settings update
        elif any(key in request.form for key in ['require_phone_verification', 'require_email_verification']):
            # Get verification settings from form
            verification_settings = {
                "require_email_verification": request.form.get('require_email_verification') == 'on',
                "require_phone_verification": request.form.get('require_phone_verification') == 'on',
                "verification_required_for_login": request.form.get('verification_required_for_login') == 'on',
                "verification_required_for_staff": request.form.get('verification_required_for_staff') == 'on',
                "verification_required_for_patients": request.form.get('verification_required_for_patients') == 'on',
                "verification_grace_period_days": int(request.form.get('verification_grace_period_days', 7)),
                "otp_length": int(request.form.get('otp_length', 6)),
                "otp_expiry_minutes": int(request.form.get('otp_expiry_minutes', 10)),
                "max_otp_attempts": int(request.form.get('max_otp_attempts', 3))
            }
            
            # Update settings
            result = HospitalSettingsService.update_settings(
                hospital_id=hospital_id,
                category="verification",
                settings=verification_settings
            )
            
            if result.get('success'):
                flash('Settings updated successfully', 'success')
            else:
                flash(f'Failed to update settings: {result.get("message")}', 'error')
    
    # Get current settings
    verification_settings = HospitalSettingsService.get_settings(hospital_id, "verification")
    
    # Get current hospital details including logo, using get_detached_copy
    hospital = None
    with get_db_session() as session:
        # Get the hospital with all needed relationships loaded
        hospital_query = session.query(Hospital).filter_by(hospital_id=hospital_id)
        
        # Load the hospital
        db_hospital = hospital_query.first()
        
        # Create a detached copy of the hospital to use outside the session
        if db_hospital:
            hospital = get_detached_copy(db_hospital)
            
            # Debug the hospital logo field
            if hospital and hasattr(hospital, 'logo') and hospital.logo:
                current_app.logger.info(f"Hospital logo data: {hospital.logo}")
                if isinstance(hospital.logo, str):
                    import json
                    try:
                        hospital.logo = json.loads(hospital.logo)
                        current_app.logger.info("Converted hospital logo from string to dict")
                    except json.JSONDecodeError:
                        current_app.logger.error("Failed to parse hospital logo JSON")
    
    # Get menu items for navigation
    menu_items = generate_menu_for_role(current_user.entity_type)
    
    # For the template to work correctly, attach the detached hospital to current_user
    # This is a temporary attachment just for the request
    current_user.hospital = hospital
    
    return render_template(
        'admin/hospital_settings.html',
        verification_settings=verification_settings,
        hospital=hospital,
        menu_items=menu_items
    )

# Add these routes to your existing admin_views.py file

@admin_views_bp.route('/staff-management', methods=['GET'])
@login_required
@admin_required
def staff_management():
    """Staff Management Dashboard"""
    try:
        # Get hospital ID from current user
        hospital_id = getattr(current_user, 'hospital_id', None)
        
        if not hospital_id:
            flash("No hospital associated with your account", 'error')
            return redirect(url_for('auth_views.dashboard'))
        
        # Get staff list with pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        status_filter = request.args.get('status', '')
        
        with get_db_session() as session:
            # Base query
            query = session.query(Staff).filter(Staff.hospital_id == hospital_id)
            
            # Apply filters
            if search:
                # Use JSONB query to search in personal_info
                query = query.filter(
                    Staff.personal_info.contains(json.dumps({"first_name": search})) | 
                    Staff.personal_info.contains(json.dumps({"last_name": search})) |
                    Staff.employee_code.ilike(f"%{search}%")
                )
            
            if status_filter:
                query = query.filter(Staff.is_active == (status_filter == 'active'))
            
            if role_filter:
                # This requires a join with UserRoleMapping which may need to be implemented
                # Simplified for now
                pass
            
            # Get total count for pagination
            total_staff = query.count()
            
            # Apply pagination
            staff_list = query.order_by(Staff.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
            
            # Convert to dicts and add additional info
            staff_dicts = []
            for staff in staff_list:
                staff_dict = get_entity_dict(staff)
                
                # Parse JSON fields
                if staff.personal_info:
                    try:
                        staff_dict['personal_info'] = json.loads(staff.personal_info) if isinstance(staff.personal_info, str) else staff.personal_info
                    except (json.JSONDecodeError, TypeError):
                        staff_dict['personal_info'] = {}
                
                if staff.contact_info:
                    try:
                        staff_dict['contact_info'] = json.loads(staff.contact_info) if isinstance(staff.contact_info, str) else staff.contact_info
                    except (json.JSONDecodeError, TypeError):
                        staff_dict['contact_info'] = {}
                
                # Get associated user info
                user = session.query(User).filter_by(
                    entity_id=staff.staff_id,
                    entity_type='staff'
                ).first()
                
                if user:
                    staff_dict['user_id'] = user.user_id
                    staff_dict['is_active'] = user.is_active
                
                # Get branch name if available
                if staff.branch_id:
                    branch = session.query(Branch).filter_by(branch_id=staff.branch_id).first()
                    if branch:
                        staff_dict['branch_name'] = branch.name
                
                staff_dicts.append(staff_dict)
            
            # Get roles for dropdown
            from app.models.config import RoleMaster
            roles = session.query(RoleMaster).filter_by(
                hospital_id=hospital_id,
                status='active'
            ).all()
            
            role_list = [{'role_id': role.role_id, 'role_name': role.role_name} for role in roles]
            
            # Get branches for dropdown
            branches = session.query(Branch).filter_by(
                hospital_id=hospital_id,
                is_active=True
            ).all()
            
            branch_list = [{'branch_id': branch.branch_id, 'name': branch.name} for branch in branches]
        
        # Get menu items for navigation
        menu_items = generate_menu_for_role(current_user.entity_type)
        
        return render_template(
            'auth/staff_management.html',
            menu_items=menu_items,
            staff_list=staff_dicts,
            total_staff=total_staff,
            page=page,
            per_page=per_page,
            search=search,
            role_filter=role_filter,
            status_filter=status_filter,
            roles=role_list,
            branches=branch_list
        )
    
    except Exception as e:
        current_app.logger.error(f"Error loading staff management: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('admin_views.hospital_admin_dashboard'))

@admin_views_bp.route('/staff-management/<uuid:staff_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def staff_detail(staff_id):
    """View and update staff details"""
    from app.forms.staff_forms import StaffManagementForm
    from app.services.employee_id_service import EmployeeIDService
    
    try:
        # Get hospital ID from current user
        hospital_id = getattr(current_user, 'hospital_id', None)
        
        if not hospital_id:
            flash("No hospital associated with your account", 'error')
            return redirect(url_for('auth_views.dashboard'))
        
        form = StaffManagementForm()
        
        # Populate role and branch choices
        with get_db_session() as session:
            # Get roles for dropdown
            from app.models.config import RoleMaster
            roles = session.query(RoleMaster).filter_by(
                hospital_id=hospital_id,
                status='active'
            ).all()
            
            form.role_id.choices = [(0, 'Select Role')] + [(r.role_id, r.role_name) for r in roles]
            
            # Get branches for dropdown
            branches = session.query(Branch).filter_by(
                hospital_id=hospital_id,
                is_active=True
            ).all()
            
            form.branch_id.choices = [('', 'Select Branch')] + [(str(b.branch_id), b.name) for b in branches]
        
        # Handle form submission for updates
        if form.validate_on_submit():
            with get_db_session() as session:
                # Find staff
                staff = session.query(Staff).filter_by(
                    staff_id=staff_id,
                    hospital_id=hospital_id
                ).first()
                
                if not staff:
                    flash("Staff not found", 'error')
                    return redirect(url_for('admin_views.staff_management'))
                
                # Handle employee ID update
                if form.employee_code.data != staff.employee_code:
                    result = EmployeeIDService.update_employee_id(staff_id, form.employee_code.data)
                    if not result.get('success'):
                        flash(result.get('message', 'Failed to update employee ID'), 'error')
                        return redirect(url_for('admin_views.staff_detail', staff_id=staff_id))
                
                # Update personal information
                personal_info = json.loads(staff.personal_info) if isinstance(staff.personal_info, str) else staff.personal_info or {}
                personal_info.update({
                    'title': form.title.data,
                    'first_name': form.first_name.data,
                    'last_name': form.last_name.data
                })
                staff.personal_info = personal_info
                
                # Update specialization
                staff.specialization = form.specialization.data
                
                # Update branch if provided
                if form.branch_id.data:
                    staff.branch_id = form.branch_id.data
                
                # Update role if provided (simplified - would normally update UserRoleMapping)
                if form.role_id.data and form.role_id.data != 0:
                    professional_info = json.loads(staff.professional_info) if isinstance(staff.professional_info, str) else staff.professional_info or {}
                    role = session.query(RoleMaster).filter_by(role_id=form.role_id.data).first()
                    if role:
                        professional_info['role_id'] = role.role_id
                        professional_info['role_name'] = role.role_name
                        staff.professional_info = professional_info
                
                # Update active status
                is_active = form.status.data == 'active'
                staff.is_active = is_active
                
                # Also update user active status
                user = session.query(User).filter_by(
                    entity_id=staff_id,
                    entity_type='staff'
                ).first()
                
                if user:
                    user.is_active = is_active
                
                # Commit changes
                session.commit()
                
                flash("Staff information updated successfully", 'success')
                return redirect(url_for('admin_views.staff_management'))
        
        # GET request - populate form with current data
        with get_db_session() as session:
            # Find staff
            staff = session.query(Staff).filter_by(
                staff_id=staff_id,
                hospital_id=hospital_id
            ).first()
            
            if not staff:
                flash("Staff not found", 'error')
                return redirect(url_for('admin_views.staff_management'))
            
            # Get associated user
            user = session.query(User).filter_by(
                entity_id=staff_id,
                entity_type='staff'
            ).first()
            
            # Parse JSON fields
            personal_info = {}
            contact_info = {}
            professional_info = {}
            
            if staff.personal_info:
                try:
                    personal_info = json.loads(staff.personal_info) if isinstance(staff.personal_info, str) else staff.personal_info
                except (json.JSONDecodeError, TypeError):
                    personal_info = {}
            
            if staff.contact_info:
                try:
                    contact_info = json.loads(staff.contact_info) if isinstance(staff.contact_info, str) else staff.contact_info
                except (json.JSONDecodeError, TypeError):
                    contact_info = {}
            
            if staff.professional_info:
                try:
                    professional_info = json.loads(staff.professional_info) if isinstance(staff.professional_info, str) else staff.professional_info
                except (json.JSONDecodeError, TypeError):
                    professional_info = {}
            
            # Populate form
            form.staff_id.data = str(staff_id)
            form.employee_code.data = staff.employee_code
            form.title.data = personal_info.get('title')
            form.first_name.data = personal_info.get('first_name')
            form.last_name.data = personal_info.get('last_name')
            form.specialization.data = staff.specialization
            
            # Set branch if available
            if staff.branch_id:
                form.branch_id.data = str(staff.branch_id)
            
            # Set role if available
            role_id = professional_info.get('role_id')
            if role_id:
                form.role_id.data = int(role_id)
            
            # Set status
            form.status.data = 'active' if staff.is_active else 'inactive'
            
            # Staff details for display
            staff_details = {
                'staff_id': staff_id,
                'employee_code': staff.employee_code,
                'personal_info': personal_info,
                'contact_info': contact_info,
                'professional_info': professional_info,
                'is_active': staff.is_active,
                'created_at': staff.created_at
            }
            
            # Get approval info if available
            from app.models.transaction import StaffApprovalRequest
            approval_request = session.query(StaffApprovalRequest).filter_by(
                staff_id=staff_id
            ).order_by(StaffApprovalRequest.created_at.desc()).first()
            
            approval_info = None
            if approval_request:
                approval_info = {
                    'request_id': approval_request.request_id,
                    'status': approval_request.status,
                    'approved_at': approval_request.approved_at,
                    'approved_by': approval_request.approved_by,
                    'notes': approval_request.notes
                }
                
                # Get approver name if available
                if approval_request.approved_by:
                    approver = session.query(User).filter_by(user_id=approval_request.approved_by).first()
                    if approver:
                        approval_info['approver_name'] = f"{approver.first_name} {approver.last_name}"
            
            # Get associated user info
            user_info = None
            if user:
                user_info = {
                    'user_id': user.user_id,
                    'is_active': user.is_active,
                    'last_login': user.last_login
                }
        
        # Get menu items for navigation
        menu_items = generate_menu_for_role(current_user.entity_type)
        
        return render_template(
            'auth/staff_detail.html',
            menu_items=menu_items,
            form=form,
            staff=staff_details,
            approval_info=approval_info,
            user_info=user_info
        )
    
    except Exception as e:
        current_app.logger.error(f"Error handling staff detail: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('admin_views.staff_management'))

@admin_views_bp.route('/generate-employee-id', methods=['POST'])
@login_required
@admin_required
def generate_employee_id():
    """Generate a new employee ID"""
    try:
        from app.services.employee_id_service import EmployeeIDService
        
        # Get hospital ID from current user
        hospital_id = getattr(current_user, 'hospital_id', None)
        
        if not hospital_id:
            return jsonify({'success': False, 'message': 'No hospital associated with your account'})
        
        # Generate new ID
        employee_id = EmployeeIDService.generate_employee_id(hospital_id)
        
        return jsonify({'success': True, 'employee_id': employee_id})
    
    except Exception as e:
        current_app.logger.error(f"Error generating employee ID: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})

@admin_views_bp.route('/employee-id-settings', methods=['GET', 'POST'])
@login_required
@admin_required
def employee_id_settings():
    """Configure employee ID generation settings"""
    from app.forms.staff_forms import EmployeeIDGeneratorForm
    from app.services.employee_id_service import EmployeeIDService
    
    try:
        # Get hospital ID from current user
        hospital_id = getattr(current_user, 'hospital_id', None)
        
        if not hospital_id:
            flash("No hospital associated with your account", 'error')
            return redirect(url_for('admin_views.dashboard'))
        
        form = EmployeeIDGeneratorForm()
        
        if form.validate_on_submit():
            # Get settings from form
            settings = {
                'prefix': form.prefix.data,
                'next_number': int(form.next_number.data),
                'padding': int(form.padding.data),
                'suffix': form.suffix.data,
                'separator': form.separator.data
            }
            
            # Update settings
            result = EmployeeIDService.update_id_settings(hospital_id, settings)
            
            if result.get('success'):
                flash("Employee ID settings updated successfully", 'success')
            else:
                flash(result.get('message', 'Failed to update settings'), 'error')
            
            return redirect(url_for('admin_views.employee_id_settings'))
        
        # GET request - populate form with current settings
        if request.method == 'GET':
            # Get current settings
            settings = EmployeeIDService.get_id_settings(hospital_id)
            
            # Populate form
            form.prefix.data = settings.get('prefix', '')
            form.next_number.data = settings.get('next_number', 1)
            form.padding.data = str(settings.get('padding', 3))
            form.suffix.data = settings.get('suffix', '')
            form.separator.data = settings.get('separator', '')
            
            # Generate preview ID
            preview_id = EmployeeIDService.generate_employee_id(hospital_id)
        
        # Get menu items for navigation
        menu_items = generate_menu_for_role(current_user.entity_type)
        
        return render_template(
            'auth/employee_id_settings.html',
            menu_items=menu_items,
            form=form,
            preview_id=preview_id if 'preview_id' in locals() else None
        )
    
    except Exception as e:
        current_app.logger.error(f"Error handling employee ID settings: {str(e)}", exc_info=True)
        flash(f"An error occurred: {str(e)}", 'error')
        return redirect(url_for('admin_views.hospital_admin_dashboard'))