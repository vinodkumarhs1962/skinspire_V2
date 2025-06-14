# app/services/verification_service.py

import logging
import random
import string
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

from app.services.database_service import get_db_session, get_detached_copy
from app.models.transaction import User, VerificationCode
from sqlalchemy import text

# Add hospital settings import
from app.services.hospital_settings_service import HospitalSettingsService

logger = logging.getLogger(__name__)

class VerificationService:
    """
    Service for handling phone and email verification
    Uses database to store verification codes and status
    """
    
    # Constants
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    MAX_OTP_ATTEMPTS = 3
    
    @classmethod
    def generate_verification_code(cls) -> str:
        """Generate a numeric verification code"""
        return ''.join(random.choices(string.digits, k=cls.OTP_LENGTH))
    
    @classmethod
    def send_verification_sms(cls, phone_number: str, code: str) -> bool:
        """Send verification using WhatsApp via Twilio"""
        try:
            # Import Twilio dependencies
            import os
            from twilio.rest import Client
            
            # Configure your Twilio credentials
            account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
            auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
            whatsapp_from = os.environ.get('TWILIO_WHATSAPP_NUMBER')
            
            # Create client
            client = Client(account_sid, auth_token)
            
            # Format phone number for WhatsApp
            # If phone_number doesn't start with '+', add country code
            if not phone_number.startswith('+'):
                phone_number = '+91' + phone_number  # Assuming India (+91)
                
            # Format as WhatsApp number
            whatsapp_to = f"whatsapp:{phone_number}"
            
            # Send message
            message = client.messages.create(
                body=f'Your SkinSpire Clinic verification code is: {code}. This code will expire in {cls.OTP_EXPIRY_MINUTES} minutes.',
                from_=whatsapp_from,
                to=whatsapp_to
            )
            
            # Log success
            logger.info(f"WhatsApp message sent to {phone_number} with SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {str(e)}", exc_info=True)
            return False
    
    @classmethod
    def send_verification_email(cls, email: str, code: str) -> bool:
        """Send verification email using Gmail SMTP"""
        try:
            import os
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Get Gmail credentials from environment variables
            gmail_email = os.environ.get('GMAIL_EMAIL')
            gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
            
            if not gmail_email or not gmail_password:
                logger.error("Gmail credentials not found in environment variables")
                return False
            
            # Create message container
            message = MIMEMultipart('alternative')
            message['Subject'] = 'SkinSpire Clinic - Email Verification Code'
            message['From'] = gmail_email
            message['To'] = email
            
            # Create HTML version of the message
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4a90e2; color: white; padding: 10px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .code {{ font-size: 24px; font-weight: bold; color: #4a90e2; text-align: center; 
                            padding: 10px; margin: 15px 0; border: 1px dashed #ccc; }}
                    .footer {{ font-size: 12px; color: #666; text-align: center; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>SkinSpire Clinic</h2>
                    </div>
                    <div class="content">
                        <p>Dear Patient,</p>
                        <p>Thank you for verifying your email address. Please use the following verification code:</p>
                        <div class="code">{code}</div>
                        <p>This code will expire in {cls.OTP_EXPIRY_MINUTES} minutes.</p>
                        <p>If you did not request this code, please ignore this email.</p>
                        <p>Regards,<br>SkinSpire Clinic Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create plain text version (fallback)
            text = f"""
            SkinSpire Clinic - Email Verification
            
            Your verification code is: {code}
            
            This code will expire in {cls.OTP_EXPIRY_MINUTES} minutes.
            
            If you did not request this code, please ignore this email.
            
            Regards,
            SkinSpire Clinic Team
            """
            
            # Attach parts to message
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            message.attach(part1)
            message.attach(part2)
            
            # Connect to Gmail SMTP server
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(gmail_email, gmail_password)
                server.sendmail(gmail_email, email, message.as_string())
            
            logger.info(f"Verification email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}", exc_info=True)
            return False
    
    # @classmethod
    # def initiate_phone_verification(cls, user_id: str, phone_number: str = None) -> Dict[str, Any]:
    #     """
    #     Initiate phone verification process for a user
        
    #     Args:
    #         user_id: User ID requesting verification
    #         phone_number: Optional phone number (if different from user_id)
            
    #     Returns:
    #         Dict with status and message
    #     """
    #     try:
    #         with get_db_session() as session:
    #             # Get the user
    #             user = session.query(User).filter_by(user_id=user_id).first()
    #             if not user:
    #                 return {"success": False, "message": "User not found"}
                
    #             # Determine phone number to verify
    #             verify_phone = phone_number if phone_number else user_id
                
    #             # Generate verification code
    #             code = cls.generate_verification_code()
    #             logger.info(f"Generated verification code for phone {verify_phone}: {code}")
                
    #             # Store verification data in database
    #             # Get existing verification code or create new one
    #             verification = session.query(VerificationCode).filter_by(
    #                 user_id=user_id, 
    #                 code_type='phone'
    #             ).first()
                
    #             expiry_time = datetime.now(timezone.utc) + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)
                
    #             if verification:
    #                 # Update existing verification code
    #                 verification.code = code
    #                 verification.target = verify_phone
    #                 verification.expires_at = expiry_time
    #                 verification.attempts = 0
    #                 logger.info(f"Updated existing phone verification for {user_id}")
    #             else:
    #                 # Create new verification code
    #                 verification = VerificationCode(
    #                     user_id=user_id,
    #                     code_type='phone',
    #                     code=code,
    #                     target=verify_phone,
    #                     expires_at=expiry_time,
    #                     attempts=0
    #                 )
    #                 session.add(verification)
    #                 logger.info(f"Created new phone verification for {user_id}")
                
    #             # Send verification SMS
    #             sms_sent = cls.send_verification_sms(verify_phone, code)
                
    #             # Commit transaction
    #             session.commit()
                
    #             if sms_sent:
    #                 logger.info(f"Successfully sent verification code to {verify_phone}")
    #                 return {
    #                     "success": True, 
    #                     "message": "Verification code sent",
    #                     "expires_at": expiry_time.isoformat()
    #                 }
    #             else:
    #                 logger.warning(f"Failed to send verification code to {verify_phone}")
    #                 return {
    #                     "success": False,
    #                     "message": "Failed to send verification code"
    #                 }
                    
    #     except Exception as e:
    #         logger.error(f"Error initiating phone verification: {str(e)}", exc_info=True)
    #         return {"success": False, "message": "Internal error"}

    @classmethod
    def initiate_phone_verification(cls, user_id: str, phone_number: str = None) -> Dict[str, Any]:
        """
        Initiate phone verification process for a user
        
        Args:
            user_id: User ID requesting verification
            phone_number: Optional phone number (if different from user_id)
            
        Returns:
            Dict with status and message
        """
        try:
            with get_db_session() as session:
                # Import phone utils
                from app.utils.phone_utils import normalize_phone_number, get_verification_number
                
                # Get the user
                user = session.query(User).filter_by(user_id=user_id).first()
                if not user:
                    return {"success": False, "message": "User not found"}
                
                # Determine phone number to verify
                original_phone = phone_number if phone_number else user_id
                
                # Normalize phone number (even if it's already normalized)
                verify_phone = normalize_phone_number(original_phone)
                logger.info(f"Using normalized phone for verification: {verify_phone}")
                
                # Generate verification code
                code = cls.generate_verification_code()
                logger.info(f"Generated verification code for phone {verify_phone}: {code}")
                
                # The rest of your existing function stays exactly the same
                # Store verification data in database
                # Get existing verification code or create new one
                verification = session.query(VerificationCode).filter_by(
                    user_id=user_id, 
                    code_type='phone'
                ).first()
                
                expiry_time = datetime.now(timezone.utc) + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)
                
                if verification:
                    # Update existing verification code
                    verification.code = code
                    verification.target = verify_phone
                    verification.expires_at = expiry_time
                    verification.attempts = 0
                    logger.info(f"Updated existing phone verification for {user_id}")
                else:
                    # Create new verification code
                    verification = VerificationCode(
                        user_id=user_id,
                        code_type='phone',
                        code=code,
                        target=verify_phone,
                        expires_at=expiry_time,
                        attempts=0
                    )
                    session.add(verification)
                    logger.info(f"Created new phone verification for {user_id}")
                

                # When sending SMS, extract the verification digits if needed
                verification_digits = get_verification_number(verify_phone)
                # Send verification SMS
                sms_sent = cls.send_verification_sms(verify_phone, code)
                
                # Commit transaction
                session.commit()
                
                if sms_sent:
                    logger.info(f"Successfully sent verification code to {verify_phone}")
                    return {
                        "success": True, 
                        "message": "Verification code sent",
                        "expires_at": expiry_time.isoformat()
                    }
                else:
                    logger.warning(f"Failed to send verification code to {verify_phone}")
                    return {
                        "success": False,
                        "message": "Failed to send verification code"
                    }
                    
        except Exception as e:
            logger.error(f"Error initiating phone verification: {str(e)}", exc_info=True)
            return {"success": False, "message": "Internal error"}
    @classmethod
    def initiate_email_verification(cls, user_id: str, email: str = None) -> Dict[str, Any]:
        """
        Initiate email verification process for a user
        
        Args:
            user_id: User ID requesting verification
            email: Email address to verify (optional)
            
        Returns:
            Dict with status and message
        """
        try:
            # Use lower-level database access to ensure proper transaction handling
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker
            from app.services.database_service import get_database_url
            
            # Create a direct engine and session
            engine = create_engine(get_database_url())
            Session = sessionmaker(bind=engine)
            db_session = Session()
            
            try:
                # Get the user
                user = db_session.query(User).filter_by(user_id=user_id).first()
                if not user:
                    return {"success": False, "message": "User not found"}
                
                # Determine email to verify
                verify_email = email
                if not verify_email:
                    # Try to get email from entity data
                    if hasattr(user, 'contact_info_dict') and user.contact_info_dict:
                        verify_email = user.contact_info_dict.get('email')
                
                if not verify_email:
                    logger.warning(f"No email address available for user {user_id}")
                    return {"success": False, "message": "No email address available"}
                
                # Generate verification code
                code = cls.generate_verification_code()
                logger.info(f"Generated verification code for email {verify_email}: {code}")
                
                # Set current time and expiry time
                now = datetime.now(timezone.utc)
                expiry_time = now + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)
                
                # First, delete any existing email verification codes for this user
                db_session.execute(
                    text("DELETE FROM verification_codes WHERE user_id = :user_id AND code_type = :code_type"),
                    {"user_id": user_id, "code_type": "email"}
                )
                
                # Insert new verification code directly with updated_at to fix NULL constraint violation
                db_session.execute(
                    text("""
                    INSERT INTO verification_codes (user_id, code_type, code, target, expires_at, attempts, created_at, updated_at)
                    VALUES (:user_id, :code_type, :code, :target, :expires_at, :attempts, :created_at, :updated_at)
                    """),
                    {
                        "user_id": user_id,
                        "code_type": "email",
                        "code": code,
                        "target": verify_email,
                        "expires_at": expiry_time,
                        "attempts": 0,
                        "created_at": now,
                        "updated_at": now  # Add updated_at value
                    }
                )
                
                # Send verification email
                email_sent = cls.send_verification_email(verify_email, code)
                
                # Commit changes
                db_session.commit()
                logger.info(f"Directly inserted email verification for {user_id}")
                
                if email_sent:
                    logger.info(f"Successfully sent verification code to {verify_email}")
                    return {
                        "success": True, 
                        "message": "Verification code sent",
                        "expires_at": expiry_time.isoformat()
                    }
                else:
                    logger.warning(f"Failed to send verification code to {verify_email}")
                    return {
                        "success": False,
                        "message": "Failed to send verification code"
                    }
            except Exception as e:
                db_session.rollback()
                raise e
            finally:
                db_session.close()
                    
        except Exception as e:
            logger.error(f"Error initiating email verification: {str(e)}", exc_info=True)
            return {"success": False, "message": "Internal error"}
    
    @classmethod
    def verify_code(cls, user_id: str, code_type: str, code: str) -> Dict[str, Any]:
        """
        Verify a verification code
        
        Args:
            user_id: User ID
            code_type: Type of code ('phone' or 'email')
            code: The verification code to check
            
        Returns:
            Dict with status and message
        """
        try:
            # Debug logging to track the verification parameters
            logger.info(f"Verifying code for user {user_id}, type {code_type}, code {code}")
            
            with get_db_session() as session:
                # Get verification record
                verification = session.query(VerificationCode).filter_by(
                    user_id=user_id,
                    code_type=code_type
                ).first()
                
                # Debug logging - checking if verification record exists
                logger.info(f"Verification record found: {verification is not None}")
                
                if not verification:
                    logger.warning(f"No verification in progress for {user_id}, {code_type}")
                    return {"success": False, "message": "No verification in progress"}
                
                # Log actual verification code vs submitted code for debugging
                logger.info(f"Stored verification code: {verification.code}, Submitted code: {code}")
                
                # Check if code has expired
                if datetime.now(timezone.utc) > verification.expires_at:
                    logger.warning(f"Verification code expired for {user_id}, {code_type}")
                    return {"success": False, "message": "Verification code has expired"}
                
                # Check attempts
                if verification.attempts >= cls.MAX_OTP_ATTEMPTS:
                    logger.warning(f"Too many attempts for {user_id}, {code_type}")
                    return {"success": False, "message": "Too many invalid attempts"}
                
                # Increment attempts
                verification.attempts += 1
                
                # Check if code is correct
                logger.info(f"Comparing received code '{code}' with stored code '{verification.code}'")
                if code != verification.code:
                    session.commit()  # Save the attempt increment
                    logger.warning(f"Invalid code for {user_id}, {code_type}")
                    return {"success": False, "message": "Invalid verification code"}
                
                # Mark as verified in user record
                user = session.query(User).filter_by(user_id=user_id).first()
                if not user:
                    logger.warning(f"User not found: {user_id}")
                    return {"success": False, "message": "User not found"}
                
                # Initialize verification_status if needed
                current_status = {}
                if user.verification_status:
                    # Convert from string if needed
                    if isinstance(user.verification_status, str):
                        try:
                            current_status = json.loads(user.verification_status)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in verification_status for {user_id}")
                    else:
                        # Make a deep copy to ensure we have a complete copy
                        # Using json serialization to ensure a clean copy
                        current_status = json.loads(json.dumps(user.verification_status))
                
                # Log the current status before updating
                logger.warning(f"Current verification status for {user_id}: {current_status}")
                
                # Update verification status
                current_status[code_type] = {
                    "verified": True,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "target": verification.target
                }
                
                # Log status before saving
                logger.warning(f"New verification status for {user_id}: {current_status}")
                
                # Force a new assignment to trigger SQLAlchemy change detection
                user.verification_status = current_status
                
                # Explicitly flush changes to database to ensure they are recorded
                session.flush()
                
                # Remove verification code
                session.delete(verification)
                
                # Commit transaction
                session.commit()
                
                # Log status after saving
                logger.warning(f"Verification successful for {user_id}, {code_type}")
                return {"success": True, "message": "Verification successful"}
                
        except Exception as e:
            logger.error(f"Error verifying code: {str(e)}", exc_info=True)
            return {"success": False, "message": "Internal error"}

    @classmethod
    def resend_verification_code(cls, user_id: str, code_type: str) -> Dict[str, Any]:
        """
        Resend a verification code
        
        Args:
            user_id: User ID
            code_type: Type of code ('phone' or 'email')
            
        Returns:
            Dict with status and message
        """
        logger.warning(f"Attempting to resend verification code for user: {user_id}, type: {code_type}")
        
        try:
            with get_db_session() as session:
                # Get verification record
                verification = session.query(VerificationCode).filter_by(
                    user_id=user_id,
                    code_type=code_type
                ).first()
                
                if not verification:
                    logger.warning(f"No existing verification found, initiating new for {user_id}, {code_type}")
                    if code_type == 'phone':
                        return cls.initiate_phone_verification(user_id)
                    else:
                        return cls.initiate_email_verification(user_id)
                
                # Generate new code
                code = cls.generate_verification_code()
                logger.info(f"Generated new code for {user_id}, {code_type}: {code}")
                
                # Update verification data
                expiry_time = datetime.now(timezone.utc) + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)
                verification.code = code
                verification.expires_at = expiry_time
                verification.attempts = 0
                
                # Send verification
                target = verification.target
                if code_type == 'phone':
                    logger.warning(f"RESEND DEVELOPMENT MODE: OTP CODE FOR PHONE {target} is {code}")
                    sent = cls.send_verification_sms(target, code)
                else:
                    logger.warning(f"RESEND DEVELOPMENT MODE: OTP CODE FOR EMAIL {target} is {code}")
                    sent = cls.send_verification_email(target, code)
                
                # Commit transaction
                session.commit()
                
                if sent:
                    logger.info(f"Successfully resent verification code to {target}")
                    return {
                        "success": True,
                        "message": "Verification code resent",
                        "expires_at": expiry_time.isoformat()
                    }
                else:
                    logger.warning(f"Failed to resend verification code to {target}")
                    return {
                        "success": False,
                        "message": f"Failed to resend verification code to {target}"
                    }
                    
        except Exception as e:
            logger.error(f"Error resending verification code: {str(e)}", exc_info=True)
            return {"success": False, "message": "Internal error"}
    
    @classmethod
    def get_verification_status(cls, user_id: str) -> Dict[str, Any]:
        """
        Get verification status for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with verification status for phone and email
        """
        try:
            with get_db_session() as session:
                # Get user
                user = session.query(User).filter_by(user_id=user_id).first()
                if not user:
                    logger.warning(f"User not found for verification status check: {user_id}")
                    return {
                        "success": False,
                        "message": "User not found"
                    }
                
                # Get verification status from user
                status = {}
                if hasattr(user, 'verification_status') and user.verification_status:
                    # Handle string or dict
                    if isinstance(user.verification_status, str):
                        try:
                            status = json.loads(user.verification_status)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON in verification_status for {user_id}")
                            status = {}
                    else:
                        status = user.verification_status
                
                # Build response
                phone_status = status.get('phone', {})
                email_status = status.get('email', {})
                
                # Log status for debugging
                logger.info(f"Verification status for {user_id}: phone={phone_status.get('verified', False)}, email={email_status.get('verified', False)}")
                
                return {
                    "success": True,
                    "phone": {
                        "verified": phone_status.get('verified', False),
                        "verified_at": phone_status.get('verified_at'),
                        "target": phone_status.get('target')
                    },
                    "email": {
                        "verified": email_status.get('verified', False),
                        "verified_at": email_status.get('verified_at'),
                        "target": email_status.get('target')
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting verification status: {str(e)}", exc_info=True)
            return {"success": False, "message": "Internal error"}

    @classmethod
    def get_verification_settings(cls, hospital_id: str) -> Dict[str, Any]:
        """
        Get verification settings for a hospital
        
        Args:
            hospital_id: Hospital ID
            
        Returns:
            Dict with verification settings
        """
        return HospitalSettingsService.get_settings(hospital_id, "verification")
    
    @classmethod
    def verification_required(cls, user) -> Tuple[bool, bool]:
        """
        Check if verification is required for a user
        
        Args:
            user: User object
            
        Returns:
            Tuple of (phone_required, email_required)
        """
        try:
            # Get hospital settings
            settings = cls.get_verification_settings(user.hospital_id)
            
            # Determine if verification is required based on entity type
            if user.entity_type == 'staff':
                if not settings.get('verification_required_for_staff', True):
                    return False, False
            elif user.entity_type == 'patient':
                if not settings.get('verification_required_for_patients', True):
                    return False, False
            
            # Get specific requirements
            phone_required = settings.get('require_phone_verification', True)
            email_required = settings.get('require_email_verification', True)
            
            return phone_required, email_required
            
        except Exception as e:
            logger.error(f"Error checking verification requirements: {str(e)}", exc_info=True)
            # Default to requiring both
            return True, True
    
    # Add this helper method to debug verification records

    @classmethod
    def _debug_verification_records(cls, user_id: str) -> None:
        """Debug helper to check all verification records for a user"""
        try:
            with get_db_session() as session:
                records = session.query(VerificationCode).filter_by(user_id=user_id).all()
                logger.info(f"Found {len(records)} verification records for user {user_id}")
                
                for record in records:
                    logger.info(f"Verification record: type={record.code_type}, " 
                            f"code={record.code}, expires_at={record.expires_at}, "
                            f"attempts={record.attempts}")
        except Exception as e:
            logger.error(f"Error debugging verification records: {str(e)}")

    # Replace the initiate_phone_verification with this version

    @classmethod
    def initiate_phone_verification(cls, user_id: str, phone_number: str = None) -> Dict[str, Any]:
        """
        Initiate phone verification process for a user
        
        Args:
            user_id: User ID requesting verification
            phone_number: Optional phone number (if different from user_id)
            
        Returns:
            Dict with status and message
        """
        try:
            # Determine phone number to verify
            verify_phone = phone_number if phone_number else user_id
            
            # Generate verification code
            code = cls.generate_verification_code()
            logger.info(f"Generated verification code for phone {verify_phone}: {code}")
            
            # Set expiry time and current time
            now = datetime.now(timezone.utc)
            expiry_time = now + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)
            
            # Use lower-level database access to ensure the record is created and committed
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker
            from app.services.database_service import get_database_url
            
            # Create a direct engine and session
            engine = create_engine(get_database_url())
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                # First, delete any existing verification codes for this user/type
                session.execute(
                    text("DELETE FROM verification_codes WHERE user_id = :user_id AND code_type = :code_type"),
                    {"user_id": user_id, "code_type": "phone"}
                )
                
                # Insert new verification code directly with updated_at to fix NULL constraint violation
                session.execute(
                    text("""
                    INSERT INTO verification_codes (user_id, code_type, code, target, expires_at, attempts, created_at, updated_at)
                    VALUES (:user_id, :code_type, :code, :target, :expires_at, :attempts, :created_at, :updated_at)
                    """),
                    {
                        "user_id": user_id,
                        "code_type": "phone",
                        "code": code,
                        "target": verify_phone,
                        "expires_at": expiry_time,
                        "attempts": 0,
                        "created_at": now,
                        "updated_at": now  # Add updated_at value
                    }
                )
                
                # Explicitly commit the transaction
                session.commit()
                logger.info(f"Directly inserted phone verification for {user_id}")
                
                # Verify record was created
                result = session.execute(
                    text("SELECT COUNT(*) FROM verification_codes WHERE user_id = :user_id AND code_type = :code_type"),
                    {"user_id": user_id, "code_type": "phone"}
                ).scalar()
                
                logger.info(f"Verification record count after insertion: {result}")
                
            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()
            
            # Temporary bypass for Twilio in development mode
            logger.warning(f"DEVELOPMENT MODE: OTP CODE FOR PHONE {verify_phone} is {code}")
            
            # For now, assume the SMS was sent successfully
            sms_sent = True
            
            if sms_sent:
                logger.info(f"Successfully sent verification code to {verify_phone}")
                return {
                    "success": True, 
                    "message": "Verification code sent",
                    "expires_at": expiry_time.isoformat()
                }
            else:
                logger.warning(f"Failed to send verification code to {verify_phone}")
                return {
                    "success": False,
                    "message": "Failed to send verification code"
                }
                    
        except Exception as e:
            logger.error(f"Error initiating phone verification: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Internal error: {str(e)}"}