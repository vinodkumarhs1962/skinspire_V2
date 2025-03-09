from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from app.models.transaction import User
import requests
import json

auth_views_bp = Blueprint('auth_views', __name__)

@auth_views_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth_views.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Call your existing API endpoint
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
                login_user(user)
                
            flash('Login successful', 'success')
            return redirect(url_for('auth_views.dashboard'))
        else:
            error_msg = 'Invalid credentials'
            if response.status_code != 401:  # If not just wrong credentials
                try:
                    error_msg = response.json().get('error', 'Authentication failed')
                except:
                    error_msg = 'Authentication failed'
            flash(error_msg, 'error')
    
    return render_template('auth/login.html')

@auth_views_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view after successful login"""
    return render_template('dashboard/index.html')

@auth_views_bp.route('/logout')
def logout():
    if 'auth_token' in session:
        # Call your API to invalidate the token
        response = requests.post(
            url_for('auth.logout', _external=True),
            headers={'Authorization': f'Bearer {session["auth_token"]}'}
        )
        
        # Clear session regardless of response
        session.pop('auth_token', None)
    
    logout_user()  # For Flask-Login
    flash('You have been logged out', 'info')
    return redirect(url_for('auth_views.login'))