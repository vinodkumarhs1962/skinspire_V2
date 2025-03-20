# app/security/authentication/auth_manager.py

from app.database.context import user_context
import logging
from werkzeug.security import check_password_hash
from datetime import datetime, timezone
import jwt
import uuid
from flask import current_app, request
from typing import Dict, Any, Optional
from app.models import User, UserSession, LoginHistory, UserRoleMapping, RoleMaster
from ..config import SecurityConfig
from .session_manager import SessionManager

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Handles user authentication and session management with integrated Redis support.
    Maintains compatibility with existing database session tracking while adding
    Redis-based session handling for improved performance.
    """
    
    def __init__(self, session=None, redis_client=None):
        """
        Initialize auth manager with optional Redis support
        
        Args:
            session: SQLAlchemy session
            redis_client: Optional Redis client for enhanced session management
        """
        self._session = session
        self.config = SecurityConfig()
        
        # Initialize session manager if Redis is available
        self.session_manager = SessionManager(
            security_config=self.config,
            redis_client=redis_client,
            db_session=session
        ) if redis_client else None
    
    def set_db_session(self, session):
        """
        Set or update the database session used by this manager
        
        Args:
            session: SQLAlchemy session
        """
        self._session = session
        
        # Update session manager if it exists
        if self.session_manager:
            self.session_manager.set_db_session(session)
    
    @property
    def session(self):
        """Get the current database session"""
        return self._session
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and manage login attempts.
        Preserves existing role-based authentication while adding enhanced session support.
        """
        if not self._session:
            logger.error("No database session available for authentication")
            return {'success': False, 'error': 'Database session unavailable'}
            
        try:
            # Get user with active status check
            user = self._session.query(User).filter_by(
                user_id=username,
                is_active=True
            ).first()
            
            if not user:
                self._log_login_attempt(username, 'failed', 'User not found')
                return {
                    'success': False,
                    'error': 'Invalid credentials'
                }
            
            # Check account lockout
            if user.failed_login_attempts >= self.config.BASE_SECURITY_SETTINGS['max_login_attempts']:
                self._log_login_attempt(username, 'failed', 'Account locked')
                return {
                    'success': False,
                    'error': 'Account is locked due to multiple failed attempts'
                }
            
            # Verify password
            if not user.check_password(password):
                user.failed_login_attempts += 1
                # Don't commit - let the caller manage the transaction
                self._session.flush()
                
                self._log_login_attempt(username, 'failed', 'Invalid password')
                return {
                    'success': False,
                    'error': 'Invalid credentials'
                }
            
            # Reset failed attempts and update login time
            user.failed_login_attempts = 0
            user.last_login = datetime.now(timezone.utc)
            
            # Get user roles (preserving existing role functionality)
            roles = self._session.query(RoleMaster).join(
                UserRoleMapping
            ).filter(
                UserRoleMapping.user_id == username
            ).all()
            
            role_names = [role.role_name for role in roles]
            
            # Flush changes to make them visible within current transaction
            self._session.flush()
            
            # Log successful login
            self._log_login_attempt(username, 'success')
            
            return {
                'success': True,
                'user': user,
                'roles': role_names
            }
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}", exc_info=True)
            # Don't rollback - let the caller manage the transaction
            raise
    
    def create_session(self, user_id: str, hospital_id: str) -> str:
        """Create new user session with proper context handling"""
        if not self._session:
            logger.error("No database session available for session creation")
            raise ValueError("Database session unavailable")
            
        try:
            # Use user_context if it doesn't manage its own transactions
            # Otherwise use a simpler approach
            
            # First end any existing sessions
            self._session.query(UserSession).filter_by(
                user_id=user_id,
                is_active=True
            ).update({
                'is_active': False
            })
            
            # Create new session
            session_id = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + \
                       self.config.BASE_SECURITY_SETTINGS['session_timeout']
            token = self._generate_token(user_id, session_id)
            
            session = UserSession(
                session_id=session_id,
                user_id=user_id,
                token=token,
                expires_at=expires_at,
                is_active=True
            )
            
            self._session.add(session)
            self._session.flush()  # Ensure we catch any DB errors but don't commit
            
            return token
                
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            # Don't rollback - let the caller manage the transaction
            raise
    
    def validate_token(self, token: str) -> Optional[User]:
        """
        Validate token using both database and Redis if available.
        Returns associated user if valid.
        """
        if not self._session:
            logger.error("No database session available for token validation")
            raise ValueError("Database session unavailable")
            
        try:
            # Check Redis session first if available
            if self.session_manager:
                decoded = jwt.decode(
                    token,
                    current_app.config['SECRET_KEY'],
                    algorithms=['HS256']
                )
                redis_session = self.session_manager.validate_session(
                    decoded['session_id']
                )
                if not redis_session:
                    raise ValueError('Invalid Redis session')
            
            # Validate database session
            session = self._session.query(UserSession).filter_by(
                token=token,
                is_active=True
            ).first()
            
            if not session:
                raise ValueError('Invalid or expired session')
            
            # Check expiration
            if session.expires_at < datetime.now(timezone.utc):
                session.is_active = False
                # Flush but don't commit
                self._session.flush()
                raise ValueError('Session expired')
            
            # Get and validate user
            user = self._session.query(User).filter_by(
                user_id=session.user_id,
                is_active=True
            ).first()
            
            if not user:
                raise ValueError('User not found or inactive')
            
            return user
            
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}", exc_info=True)
            # Don't rollback - let the caller manage the transaction
            raise
    
    def end_session(self, token: str) -> None:
        """
        End user session in both database and Redis if available
        """
        if not self._session:
            logger.error("No database session available for ending session")
            raise ValueError("Database session unavailable")
            
        try:
            # End database session
            self._session.query(UserSession).filter_by(
                token=token
            ).update({
                'is_active': False
            })
            
            # End Redis session if available
            if self.session_manager:
                try:
                    decoded = jwt.decode(
                        token,
                        current_app.config['SECRET_KEY'],
                        algorithms=['HS256']
                    )
                    self.session_manager.end_session(decoded['session_id'])
                except jwt.InvalidTokenError:
                    logger.warning("Invalid token during session end")
            
            # Flush but don't commit
            self._session.flush()
            
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}", exc_info=True)
            # Don't rollback - let the caller manage the transaction
            raise
    
    def _log_login_attempt(self, user_id: str, status: str, 
                          failure_reason: Optional[str] = None) -> None:
        """Log login attempt with enhanced tracking"""
        if not self._session:
            logger.error("No database session available for logging login attempt")
            return
            
        try:
            log = LoginHistory(
                user_id=user_id,
                login_time=datetime.now(timezone.utc),
                status=status,
                failure_reason=failure_reason,
                ip_address=getattr(request, 'remote_addr', None),
                user_agent=str(getattr(request, 'user_agent', '')) if request else None
            )
            
            self._session.add(log)
            # Flush but don't commit
            self._session.flush()
            
        except Exception as e:
            logger.error(f"Failed to log login attempt: {str(e)}", exc_info=True)
            # Don't rollback - let the caller manage the transaction
    
    def _generate_token(self, user_id: str, session_id: str) -> str:
        """Generate JWT token with enhanced payload"""
        payload = {
            'user_id': user_id,
            'session_id': session_id,
            'exp': datetime.now(timezone.utc) + self.config.BASE_SECURITY_SETTINGS['session_timeout'],
            'iat': datetime.now(timezone.utc)
        }
        
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

def validate_token_function(token, session=None):
    """
    Standalone function to validate a token and return the associated user
    
    Args:
        token: Authentication token to validate
        session: Optional database session
        
    Returns:
        User object if valid, None otherwise
    """
    from app.services.database_service import get_db_session
    
    try:
        # If session provided, use it directly
        if session:
            auth_manager = AuthManager(session=session)
            return auth_manager.validate_token(token)
        
        # Otherwise use a new session
        with get_db_session() as session:
            auth_manager = AuthManager(session=session)
            return auth_manager.validate_token(token)
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return None