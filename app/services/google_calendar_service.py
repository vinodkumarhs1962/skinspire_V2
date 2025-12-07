# app/services/google_calendar_service.py
"""
Google Calendar Integration Service

Provides one-way push sync from Skinspire to Google Calendar.
When appointments are created, updated, or cancelled, events are pushed to staff's Google Calendar.

Setup Requirements:
1. Create a Google Cloud project
2. Enable Google Calendar API
3. Create OAuth 2.0 credentials (Web application type)
4. Add authorized redirect URI: https://your-domain/api/google-calendar/oauth/callback
5. Set environment variables:
   - GOOGLE_CLIENT_ID
   - GOOGLE_CLIENT_SECRET
   - GOOGLE_REDIRECT_URI

Usage:
    from app.services.google_calendar_service import google_calendar_service

    # Link staff's calendar (initiates OAuth)
    auth_url = google_calendar_service.get_authorization_url(staff_id)

    # After OAuth callback, push event
    google_calendar_service.push_appointment_event(appointment_id, action='create')
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from contextlib import contextmanager

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.models.master import Staff

logger = logging.getLogger(__name__)


def _get_independent_session():
    """
    Create a completely independent database session for Google Calendar operations.
    This avoids conflicts with Flask's request-scoped sessions.
    """
    from app.config.db_config import DatabaseConfig

    # Get database URL from config
    db_url = DatabaseConfig.get_database_url()

    # Create independent engine and session
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


@contextmanager
def get_gcal_session():
    """Context manager for independent database session."""
    session = _get_independent_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class GoogleCalendarService:
    """Service for Google Calendar integration."""

    # OAuth 2.0 endpoints
    AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    CALENDAR_API_URL = 'https://www.googleapis.com/calendar/v3'

    # Scopes needed for calendar operations
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.events'  # Read/write access to events
    ]

    def __init__(self):
        """Initialize with credentials from environment."""
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/api/google-calendar/oauth/callback')

        self._initialized = bool(self.client_id and self.client_secret)

        if not self._initialized:
            logger.warning("Google Calendar integration not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    @property
    def is_configured(self) -> bool:
        """Check if Google Calendar integration is properly configured."""
        return self._initialized

    def get_authorization_url(self, staff_id: str, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL for staff to link their Google Calendar.

        Args:
            staff_id: Staff ID to link calendar for
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if not self.is_configured:
            raise ValueError("Google Calendar integration not configured")

        # Include staff_id in state for callback
        state_data = json.dumps({'staff_id': staff_id, 'csrf': state or ''})

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.SCOPES),
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent',  # Always show consent screen to get refresh token
            'state': state_data
        }

        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response containing access_token, refresh_token, expires_in
        """
        if not self.is_configured:
            raise ValueError("Google Calendar integration not configured")

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }

        response = requests.post(self.TOKEN_URL, data=data)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise Exception(f"Failed to exchange code for tokens: {response.text}")

        return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token using refresh token.

        Args:
            refresh_token: Stored refresh token

        Returns:
            New token response
        """
        if not self.is_configured:
            raise ValueError("Google Calendar integration not configured")

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }

        response = requests.post(self.TOKEN_URL, data=data)

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise Exception(f"Failed to refresh token: {response.text}")

        return response.json()

    def save_staff_tokens(self, staff_id: str, tokens: Dict[str, Any]) -> bool:
        """
        Save OAuth tokens for a staff member.
        Tokens are stored in staff.settings JSONB field.

        Args:
            staff_id: Staff UUID
            tokens: Token response from OAuth

        Returns:
            True if successful
        """
        try:
            import uuid
            staff_uuid = uuid.UUID(staff_id)

            # Use independent session to avoid Flask session conflicts
            with get_gcal_session() as session:
                staff = session.query(Staff).filter_by(staff_id=staff_uuid).first()

                if not staff:
                    logger.error(f"Staff not found: {staff_id}")
                    return False

                # Get existing settings or create new
                settings = staff.settings or {}

                # Store Google Calendar tokens
                settings['google_calendar'] = {
                    'access_token': tokens.get('access_token'),
                    'refresh_token': tokens.get('refresh_token'),
                    'token_type': tokens.get('token_type', 'Bearer'),
                    'expires_at': (datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))).isoformat(),
                    'linked_at': datetime.utcnow().isoformat(),
                    'is_linked': True
                }

                staff.settings = settings
                # Note: commit is handled by context manager

                logger.info(f"Google Calendar linked for staff: {staff_id}")
                return True

        except Exception as e:
            logger.error(f"Error saving staff tokens: {str(e)}", exc_info=True)
            return False

    def get_staff_access_token(self, staff_id: str) -> Optional[str]:
        """
        Get valid access token for staff, refreshing if expired.

        Args:
            staff_id: Staff UUID

        Returns:
            Valid access token or None
        """
        try:
            import uuid
            staff_uuid = uuid.UUID(staff_id)

            # Use independent session to avoid Flask session conflicts
            with get_gcal_session() as session:
                staff = session.query(Staff).filter_by(staff_id=staff_uuid).first()

                if not staff or not staff.settings:
                    return None

                gcal = staff.settings.get('google_calendar')
                if not gcal or not gcal.get('is_linked'):
                    return None

                # Check if token is expired
                expires_at = datetime.fromisoformat(gcal.get('expires_at', '2000-01-01'))

                if datetime.utcnow() >= expires_at - timedelta(minutes=5):
                    # Token expired or expiring soon, refresh it
                    refresh_token = gcal.get('refresh_token')
                    if not refresh_token:
                        logger.warning(f"No refresh token for staff: {staff_id}")
                        return None

                    try:
                        new_tokens = self.refresh_access_token(refresh_token)

                        # Update stored tokens
                        gcal['access_token'] = new_tokens.get('access_token')
                        gcal['expires_at'] = (datetime.utcnow() + timedelta(seconds=new_tokens.get('expires_in', 3600))).isoformat()

                        # Preserve refresh token if not returned
                        if new_tokens.get('refresh_token'):
                            gcal['refresh_token'] = new_tokens['refresh_token']

                        staff.settings = {**staff.settings, 'google_calendar': gcal}
                        # Note: commit is handled by context manager

                        return gcal['access_token']

                    except Exception as e:
                        logger.error(f"Failed to refresh token for staff {staff_id}: {e}")
                        return None

                return gcal.get('access_token')

        except Exception as e:
            logger.error(f"Error getting staff access token: {str(e)}", exc_info=True)
            return None

    def push_appointment_event(self, appointment_id: str, action: str = 'create') -> bool:
        """
        Push appointment to staff's Google Calendar.

        Args:
            appointment_id: Appointment UUID
            action: 'create', 'update', or 'delete'

        Returns:
            True if successful
        """
        if not self.is_configured:
            logger.debug("Google Calendar not configured, skipping push")
            return False

        try:
            import uuid
            from app.models.appointment import Appointment
            from app.models.master import Patient

            appt_uuid = uuid.UUID(appointment_id)

            # Use independent session to avoid Flask session conflicts
            with get_gcal_session() as session:
                appointment = session.query(Appointment).filter_by(
                    appointment_id=appt_uuid
                ).first()

                if not appointment:
                    logger.warning(f"Appointment not found: {appointment_id}")
                    return False

                # Get staff's access token
                staff_id = str(appointment.staff_id) if appointment.staff_id else None
                if not staff_id:
                    logger.debug(f"No staff assigned to appointment: {appointment_id}")
                    return False

                access_token = self.get_staff_access_token(staff_id)
                if not access_token:
                    logger.debug(f"Staff {staff_id} not linked to Google Calendar")
                    return False

                # Get patient info
                patient = session.query(Patient).filter_by(patient_id=appointment.patient_id).first()
                patient_name = patient.full_name if patient else 'Unknown Patient'

                # Build event data
                start_datetime = datetime.combine(
                    appointment.appointment_date,
                    appointment.start_time or datetime.now().time().replace(hour=9, minute=0)
                )

                if appointment.end_time:
                    end_datetime = datetime.combine(appointment.appointment_date, appointment.end_time)
                else:
                    duration = appointment.estimated_duration_minutes or 30
                    end_datetime = start_datetime + timedelta(minutes=duration)

                event_data = {
                    'summary': f"Appointment: {patient_name}",
                    'description': self._build_event_description(appointment, patient),
                    'start': {
                        'dateTime': start_datetime.isoformat(),
                        'timeZone': 'Asia/Kolkata'  # TODO: Get from branch settings
                    },
                    'end': {
                        'dateTime': end_datetime.isoformat(),
                        'timeZone': 'Asia/Kolkata'
                    },
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'popup', 'minutes': 15}
                        ]
                    }
                }

                # Get stored Google Calendar event ID if exists
                gcal_event_id = None
                if appointment.external_refs and isinstance(appointment.external_refs, dict):
                    gcal_event_id = appointment.external_refs.get('google_calendar_event_id')

                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }

                if action == 'delete' or appointment.status in ['cancelled', 'no_show']:
                    # Delete event from Google Calendar
                    if gcal_event_id:
                        response = requests.delete(
                            f"{self.CALENDAR_API_URL}/calendars/primary/events/{gcal_event_id}",
                            headers=headers
                        )
                        if response.status_code in [200, 204, 404]:
                            logger.info(f"Deleted Google Calendar event for appointment: {appointment_id}")
                            return True
                        else:
                            logger.warning(f"Failed to delete event: {response.text}")
                            return False
                    return True  # Nothing to delete

                elif action == 'update' and gcal_event_id:
                    # Update existing event
                    response = requests.put(
                        f"{self.CALENDAR_API_URL}/calendars/primary/events/{gcal_event_id}",
                        headers=headers,
                        json=event_data
                    )

                    if response.status_code == 200:
                        logger.info(f"Updated Google Calendar event for appointment: {appointment_id}")
                        return True
                    elif response.status_code == 404:
                        # Event was deleted, create new one
                        action = 'create'
                    else:
                        logger.warning(f"Failed to update event: {response.text}")
                        return False

                if action == 'create' or (action == 'update' and not gcal_event_id):
                    # Create new event
                    response = requests.post(
                        f"{self.CALENDAR_API_URL}/calendars/primary/events",
                        headers=headers,
                        json=event_data
                    )

                    if response.status_code in [200, 201]:
                        event_result = response.json()
                        new_event_id = event_result.get('id')

                        # Store Google Calendar event ID in appointment metadata
                        external_refs = appointment.external_refs or {}
                        external_refs['google_calendar_event_id'] = new_event_id
                        appointment.external_refs = external_refs
                        session.commit()

                        logger.info(f"Created Google Calendar event {new_event_id} for appointment: {appointment_id}")
                        return True
                    else:
                        logger.warning(f"Failed to create event: {response.text}")
                        return False

                return True

        except Exception as e:
            logger.error(f"Error pushing appointment to Google Calendar: {str(e)}", exc_info=True)
            return False

    def _build_event_description(self, appointment, patient) -> str:
        """Build Google Calendar event description."""
        lines = []

        if patient:
            # Get phone from contact_info JSON field
            if patient.contact_info and isinstance(patient.contact_info, dict):
                phone = patient.contact_info.get('phone', '')
                if phone:
                    lines.append(f"Phone: {phone}")
            if hasattr(patient, 'mrn') and patient.mrn:
                lines.append(f"MRN: {patient.mrn}")

        if appointment.chief_complaint:
            lines.append(f"Chief Complaint: {appointment.chief_complaint}")

        if appointment.appointment_type:
            lines.append(f"Type: {appointment.appointment_type}")

        lines.append(f"Status: {appointment.status}")
        lines.append(f"Appointment #: {appointment.appointment_number}")

        lines.append("")
        lines.append("--- Managed by Skinspire ---")

        return "\n".join(lines)

    def unlink_staff_calendar(self, staff_id: str) -> bool:
        """
        Unlink staff's Google Calendar.

        Args:
            staff_id: Staff UUID

        Returns:
            True if successful
        """
        try:
            import uuid
            staff_uuid = uuid.UUID(staff_id)

            # Use independent session to avoid Flask session conflicts
            with get_gcal_session() as session:
                staff = session.query(Staff).filter_by(staff_id=staff_uuid).first()

                if not staff:
                    return False

                if staff.settings and 'google_calendar' in staff.settings:
                    settings = dict(staff.settings)
                    settings['google_calendar'] = {'is_linked': False}
                    staff.settings = settings
                    # Note: commit is handled by context manager

                logger.info(f"Google Calendar unlinked for staff: {staff_id}")
                return True

        except Exception as e:
            logger.error(f"Error unlinking staff calendar: {str(e)}", exc_info=True)
            return False

    def is_staff_linked(self, staff_id: str) -> bool:
        """
        Check if staff has linked their Google Calendar.

        Args:
            staff_id: Staff UUID

        Returns:
            True if calendar is linked
        """
        try:
            import uuid
            staff_uuid = uuid.UUID(staff_id)

            # Use independent session to avoid Flask session conflicts
            with get_gcal_session() as session:
                staff = session.query(Staff).filter_by(staff_id=staff_uuid).first()

                if not staff or not staff.settings:
                    return False

                gcal = staff.settings.get('google_calendar', {})
                return gcal.get('is_linked', False)

        except Exception as e:
            logger.error(f"Error checking staff calendar link: {str(e)}", exc_info=True)
            return False


# Singleton instance
google_calendar_service = GoogleCalendarService()
