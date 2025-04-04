# app/services/forgot_password_service.py
"""
Forgot Password Service

Handles password reset functionality with secure token generation and validation.
"""

import secrets
import datetime
import json
from flask import current_app
from typing import Dict, Any, Optional

from app.services.database_service import get_db_session
from app.models.transaction import User, UserSession
from sqlalchemy.orm import Session

class ForgotPasswordService:
    @classmethod
    def initiate_password_reset(
        cls, 
        username_or_email: str
    ) -> Dict[str, Any]:
        """
        Initiate password reset process
        
        Args:
            username_or_email: User identifier (phone or email)
        
        Returns:
            Dictionary with reset token details
        """
        try:
            with get_db_session() as session:
                # Find user by phone or email
                user = (session.query(User)
                        .filter(
                            (User.user_id == username_or_email) | 
                            (User.contact_info.contains(json.dumps({"email": username_or_email})))
                        )
                        .first())
                
                if not user:
                    raise ValueError("User not found")
                
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                reset_token_expiry = datetime.datetime.now(datetime.timezone.utc) + \
                                     datetime.timedelta(hours=1)
                
                # Create a new user session for password reset
                reset_session = UserSession(
                    user_id=user.user_id,
                    token=reset_token,
                    expires_at=reset_token_expiry,
                    is_active=True
                )
                
                # Add and commit the session
                session.add(reset_session)
                session.commit()
                
                return {
                    "success": True,
                    "reset_token": reset_token,
                    "user_id": user.user_id,
                    "expires_at": reset_token_expiry
                }
        
        except Exception as e:
            current_app.logger.error(f"Password reset initiation error: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def validate_reset_token(
        cls, 
        user_id: str, 
        reset_token: str
    ) -> bool:
        """
        Validate password reset token
        
        Args:
            user_id: User's phone number/user_id
            reset_token: Token to validate
        
        Returns:
            Boolean indicating token validity
        """
        try:
            with get_db_session(read_only=True) as session:
                # Find the user session with the given token
                user_session = session.query(UserSession).filter_by(
                    user_id=user_id, 
                    token=reset_token, 
                    is_active=True
                ).first()
                
                # Check if session exists and is not expired
                if (user_session and 
                    user_session.expires_at > datetime.datetime.now(datetime.timezone.utc)):
                    return True
                
                return False
        
        except Exception as e:
            current_app.logger.error(f"Token validation error: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def reset_password(
        cls, 
        user_id: str, 
        reset_token: str, 
        new_password: str
    ) -> Dict[str, Any]:
        """
        Reset user password after token validation
        
        Args:
            user_id: User's phone number/user_id
            reset_token: Password reset token
            new_password: New password to set
        
        Returns:
            Dictionary with reset status
        """
        try:
            with get_db_session() as session:
                # Validate the reset token first
                if not cls.validate_reset_token(user_id, reset_token):
                    raise ValueError("Invalid or expired reset token")
                
                # Find the user
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    raise ValueError(f"User not found: {user_id}")
                
                # Set the new password
                user.set_password(new_password)
                
                # Invalidate all active reset tokens for this user
                session.query(UserSession).filter_by(
                    user_id=user_id, 
                    is_active=True
                ).update({'is_active': False})
                
                # Commit changes
                session.commit()
                
                return {
                    "success": True,
                    "message": "Password reset successful"
                }
        
        except Exception as e:
            current_app.logger.error(f"Password reset error: {str(e)}", exc_info=True)
            raise
    
    @classmethod
    def send_reset_notification(
        cls, 
        user_id: str, 
        reset_token: str
    ) -> Dict[str, Any]:
        """
        Send password reset notification (email/SMS)
        
        Args:
            user_id: User's phone number/user_id
            reset_token: Password reset token
        
        Returns:
            Dictionary with notification status
        """
        try:
            with get_db_session(read_only=True) as session:
                # Find user to get contact details
                user = session.query(User).filter_by(user_id=user_id).first()
                
                if not user:
                    raise ValueError("User not found")
                
                # Determine contact method (email or phone)
                contact_method = None
                contact_value = None
                
                # Check for email in contact_info
                if user.contact_info:
                    contact_info = json.loads(user.contact_info)
                    if 'email' in contact_info:
                        contact_method = 'email'
                        contact_value = contact_info['email']
                    elif 'phone' in contact_info:
                        contact_method = 'phone'
                        contact_value = contact_info['phone']
                
                # Prepare notification details
                notification_details = {
                    "method": contact_method,
                    "recipient": contact_value,
                    "reset_link": f"/reset-password?token={reset_token}"
                }
                
                # In a real system, you'd integrate with email/SMS service
                # For now, log the notification
                current_app.logger.info(
                    f"Password reset notification for user {user_id}: "
                    f"Method={contact_method}, Recipient={contact_value}"
                )
                
                return {
                    "success": True,
                    "message": "Reset notification prepared",
                    "details": notification_details
                }
        
        except Exception as e:
            current_app.logger.error(f"Reset notification error: {str(e)}", exc_info=True)
            raise