# app/api/routes/google_calendar_api.py
"""
Google Calendar API Routes

Handles OAuth flow and calendar integration management.
"""

import json
import logging
from flask import Blueprint, request, jsonify, redirect, url_for, flash, session

from flask_login import login_required, current_user

from app.services.google_calendar_service import google_calendar_service

logger = logging.getLogger(__name__)

# Create blueprint
google_calendar_bp = Blueprint('google_calendar', __name__, url_prefix='/api/google-calendar')


@google_calendar_bp.route('/status', methods=['GET'])
@login_required
def get_integration_status():
    """
    Check if Google Calendar integration is configured and if current user is linked.
    """
    try:
        # Check if integration is configured
        is_configured = google_calendar_service.is_configured

        # Check if current user (if staff) has linked their calendar
        is_linked = False
        if hasattr(current_user, 'staff_id') and current_user.staff_id:
            is_linked = google_calendar_service.is_staff_linked(str(current_user.staff_id))

        return jsonify({
            'success': True,
            'is_configured': is_configured,
            'is_linked': is_linked,
            'message': 'Google Calendar integration available' if is_configured else 'Google Calendar not configured'
        }), 200

    except Exception as e:
        logger.error(f"Error checking integration status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@google_calendar_bp.route('/link', methods=['GET'])
@login_required
def initiate_link():
    """
    Initiate OAuth flow to link staff's Google Calendar.
    Returns authorization URL to redirect user to.
    """
    try:
        if not google_calendar_service.is_configured:
            return jsonify({
                'success': False,
                'error': 'Google Calendar integration not configured. Please contact administrator.'
            }), 400

        # Get staff_id from request or current user
        staff_id = request.args.get('staff_id')
        if not staff_id:
            if hasattr(current_user, 'staff_id') and current_user.staff_id:
                staff_id = str(current_user.staff_id)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Staff ID is required'
                }), 400

        # Generate CSRF token
        import secrets
        csrf_token = secrets.token_urlsafe(32)
        session['gcal_csrf'] = csrf_token

        # Get authorization URL
        auth_url = google_calendar_service.get_authorization_url(staff_id, csrf_token)

        return jsonify({
            'success': True,
            'auth_url': auth_url,
            'message': 'Redirect user to auth_url to complete linking'
        }), 200

    except Exception as e:
        logger.error(f"Error initiating Google Calendar link: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@google_calendar_bp.route('/link/redirect', methods=['GET'])
@login_required
def redirect_to_google():
    """
    Redirect user to Google OAuth consent screen.
    """
    try:
        if not google_calendar_service.is_configured:
            flash('Google Calendar integration not configured', 'error')
            return redirect(url_for('auth_views.settings'))

        staff_id = request.args.get('staff_id')
        if not staff_id:
            if hasattr(current_user, 'staff_id') and current_user.staff_id:
                staff_id = str(current_user.staff_id)
            else:
                flash('Staff ID is required', 'error')
                return redirect(url_for('auth_views.settings'))

        # Generate CSRF token
        import secrets
        csrf_token = secrets.token_urlsafe(32)
        session['gcal_csrf'] = csrf_token

        # Get authorization URL and redirect
        auth_url = google_calendar_service.get_authorization_url(staff_id, csrf_token)
        return redirect(auth_url)

    except Exception as e:
        logger.error(f"Error redirecting to Google: {str(e)}", exc_info=True)
        flash('Error initiating Google Calendar link', 'error')
        return redirect(url_for('auth_views.settings'))


@google_calendar_bp.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    """
    Handle OAuth callback from Google.
    Exchanges authorization code for tokens and stores them.
    """
    try:
        # Check for error
        error = request.args.get('error')
        if error:
            logger.warning(f"OAuth error: {error}")
            flash(f'Google Calendar authorization failed: {error}', 'error')
            return redirect(url_for('auth_views.settings'))

        # Get authorization code
        code = request.args.get('code')
        if not code:
            flash('No authorization code received', 'error')
            return redirect(url_for('auth_views.settings'))

        # Parse state
        state_str = request.args.get('state', '{}')
        try:
            state_data = json.loads(state_str)
        except json.JSONDecodeError:
            state_data = {}

        staff_id = state_data.get('staff_id')
        if not staff_id:
            flash('Invalid state parameter', 'error')
            return redirect(url_for('auth_views.settings'))

        # Verify CSRF (optional but recommended)
        # csrf_token = state_data.get('csrf')
        # stored_csrf = session.pop('gcal_csrf', None)
        # if csrf_token != stored_csrf:
        #     flash('Security validation failed', 'error')
        #     return redirect(url_for('auth_views.settings'))

        # Exchange code for tokens
        tokens = google_calendar_service.exchange_code_for_tokens(code)

        # Save tokens for staff
        success = google_calendar_service.save_staff_tokens(staff_id, tokens)

        if success:
            flash('Google Calendar linked successfully!', 'success')
        else:
            flash('Failed to save calendar link', 'error')

        return redirect(url_for('auth_views.settings'))

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}", exc_info=True)
        flash('Error completing Google Calendar link', 'error')
        return redirect(url_for('auth_views.settings'))


@google_calendar_bp.route('/unlink', methods=['POST'])
@login_required
def unlink_calendar():
    """
    Unlink staff's Google Calendar.
    """
    try:
        data = request.get_json() or {}
        staff_id = data.get('staff_id')

        if not staff_id:
            if hasattr(current_user, 'staff_id') and current_user.staff_id:
                staff_id = str(current_user.staff_id)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Staff ID is required'
                }), 400

        success = google_calendar_service.unlink_staff_calendar(staff_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'Google Calendar unlinked successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to unlink calendar'
            }), 500

    except Exception as e:
        logger.error(f"Error unlinking calendar: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@google_calendar_bp.route('/push-test', methods=['POST'])
@login_required
def test_push_event():
    """
    Test pushing an appointment to Google Calendar.
    """
    try:
        data = request.get_json() or {}
        appointment_id = data.get('appointment_id')

        if not appointment_id:
            return jsonify({
                'success': False,
                'error': 'appointment_id is required'
            }), 400

        success = google_calendar_service.push_appointment_event(appointment_id, action='create')

        if success:
            return jsonify({
                'success': True,
                'message': 'Event pushed to Google Calendar successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to push event. Staff may not have linked their calendar.'
            }), 400

    except Exception as e:
        logger.error(f"Error testing push: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@google_calendar_bp.route('/staff/<staff_id>/status', methods=['GET'])
@login_required
def get_staff_calendar_status(staff_id):
    """
    Check if a specific staff member has linked their Google Calendar.
    """
    try:
        is_linked = google_calendar_service.is_staff_linked(staff_id)

        return jsonify({
            'success': True,
            'staff_id': staff_id,
            'is_linked': is_linked
        }), 200

    except Exception as e:
        logger.error(f"Error checking staff calendar status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
