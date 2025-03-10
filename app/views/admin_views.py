# app/views/admin_views.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_required, current_user
import requests
from app.utils.menu_utils import generate_menu_for_role

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