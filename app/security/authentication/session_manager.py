# app/security/authentication/session_manager.py

from __future__ import annotations
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from flask import session, request, current_app
import redis
import jwt
from ..config import SecurityConfig
import json
import logging
from app.models import UserSession, LoginHistory, User
from sqlalchemy.orm import Session as SQLAlchemySession

# Set up logging properly
logger = logging.getLogger(__name__)

class SessionManager:
    """
    Enhanced session manager that handles both Redis-based session storage 
    and database session tracking for audit purposes
    """
    
    def __init__(self, security_config: SecurityConfig, redis_client: redis.Redis, db_session: SQLAlchemySession = None):
        self.config = security_config
        self.redis = redis_client
        self.db_session = db_session
        self.session_prefix = "session:"
        self.activity_prefix = "activity:"
        self.logger = logging.getLogger(__name__)

    def create_session(self, user_id: str, hospital_id: str, additional_data: Dict = None) -> Dict:
        """
        Create a new session with both Redis storage and database tracking
        
        Args:
            user_id: User identifier
            hospital_id: Hospital context
            additional_data: Optional additional session data
            
        Returns:
            Dict containing session information and token
        """
        try:
            # Generate session ID and timestamp
            session_id = self._generate_session_id()
            timestamp = datetime.now(timezone.utc)
            
            # Create Redis session data
            session_data = {
                'user_id': user_id,
                'hospital_id': hospital_id,
                'created_at': timestamp.isoformat(),
                'last_activity': timestamp.isoformat(),
                'ip_address': request.remote_addr,
                'user_agent': request.user_agent.string,
                'data': additional_data or {}
            }
            
            # Store in Redis with expiration
            self.redis.setex(
                f"{self.session_prefix}{session_id}",
                self.config.session_timeout.total_seconds(),
                json.dumps(session_data)
            )
            
            # Track user activity in Redis
            self._update_user_activity(user_id, session_id, timestamp)
            
            # Create database session record if db_session available
            if self.db_session:
                db_session = UserSession(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=timestamp,
                    expires_at=timestamp + self.config.session_timeout
                )
                
                # Create login history record
                login_history = LoginHistory(
                    user_id=user_id,
                    session_id=session_id,
                    login_time=timestamp,
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string,
                    status='success'
                )
                
                self.db_session.add(db_session)
                self.db_session.add(login_history)
                self.db_session.commit()
            
            # Generate authentication token
            token = self._generate_token(session_id, user_id, hospital_id)
            
            return {
                'token': token,
                'session_id': session_id,
                'expires_at': (timestamp + self.config.session_timeout).isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            if self.db_session:
                self.db_session.rollback()
            raise

    def validate_session(self, token: str) -> Optional[Dict]:
        """
        Validate and refresh a session using JWT token
        
        Args:
            token: JWT authentication token
            
        Returns:
            Dict with session data if valid, None if invalid
        """
        try:
            # Decode token
            payload = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            session_id = payload['session_id']
            
            # Check Redis session
            session_key = f"{self.session_prefix}{session_id}"
            session_data = self.redis.get(session_key)
            
            if not session_data:
                return None
                
            session_data = json.loads(session_data)
            current_time = datetime.now(timezone.utc)
            
            # Update last activity
            session_data['last_activity'] = current_time.isoformat()
            self.redis.setex(
                session_key,
                self.config.session_timeout.total_seconds(),
                json.dumps(session_data)
            )
            
            # Update user activity
            self._update_user_activity(
                session_data['user_id'],
                session_id,
                current_time
            )
            
            # Update database session if available
            if self.db_session:
                db_session = self.db_session.query(UserSession).filter_by(
                    session_id=session_id
                ).first()
                
                if db_session:
                    db_session.expires_at = current_time + self.config.session_timeout
                    self.db_session.commit()
            
            return session_data

        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            self.logger.error(f"Error validating session: {str(e)}")
            return None

    def end_session(self, token: str) -> bool:
        """
        End a session using JWT token
        
        Args:
            token: JWT authentication token
            
        Returns:
            bool indicating success
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            
            session_id = payload['session_id']
            
            # Remove Redis session
            session_key = f"{self.session_prefix}{session_id}"
            session_data = self.redis.get(session_key)
            
            if session_data:
                session_data = json.loads(session_data)
                user_id = session_data['user_id']
                
                self.redis.delete(session_key)
                self._remove_session_from_activity(user_id, session_id)
                
                # Update database records if available
                if self.db_session:
                    # Update login history
                    history = self.db_session.query(LoginHistory).filter_by(
                        session_id=session_id
                    ).first()
                    
                    if history:
                        history.logout_time = datetime.now(timezone.utc)
                    
                    # Remove session
                    self.db_session.query(UserSession).filter_by(
                        session_id=session_id
                    ).delete()
                    
                    self.db_session.commit()
                
                return True
                
            return False

        except jwt.InvalidTokenError:
            return False
        except Exception as e:
            self.logger.error(f"Error ending session: {str(e)}")
            if self.db_session:
                self.db_session.rollback()
            return False

    def _generate_token(self, session_id: str, user_id: str, hospital_id: str) -> str:
        """Generate JWT token for session"""
        payload = {
            'session_id': session_id,
            'user_id': user_id,
            'hospital_id': hospital_id,
            'exp': datetime.now(timezone.utc) + self.config.session_timeout
        }
        
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    # ... (keep existing helper methods)
    
    def get_active_sessions(self, user_id: str) -> List[Dict]:
        """Get all active sessions for a user"""
        activity_key = f"{self.activity_prefix}{user_id}"
        sessions = []
        
        session_ids = self.redis.smembers(activity_key)
        for session_id in session_ids:
            session_data = self.redis.get(
                f"{self.session_prefix}{session_id.decode()}"
            )
            if session_data:
                sessions.append(json.loads(session_data))
            else:
                # Clean up stale session reference
                self.redis.srem(activity_key, session_id)
        
        return sessions
    
    def end_all_sessions(self, user_id: str, except_session_id: str = None) -> int:
        """End all sessions for a user except current"""
        activity_key = f"{self.activity_prefix}{user_id}"
        ended_count = 0
        
        session_ids = self.redis.smembers(activity_key)
        for session_id in session_ids:
            session_id = session_id.decode()
            if session_id != except_session_id:
                if self.end_session(session_id):
                    ended_count += 1
        
        return ended_count
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        from uuid import uuid4
        return str(uuid4())
    
    def _update_user_activity(self, user_id: str, session_id: str,
                            timestamp: datetime) -> None:
        """Update user activity tracking"""
        activity_key = f"{self.activity_prefix}{user_id}"
        
        # Add session to user's active sessions
        self.redis.sadd(activity_key, session_id)
        
        # Set activity key expiration
        self.redis.expire(
            activity_key,
            self.config.session_timeout.total_seconds()
        )
    
    def _remove_session_from_activity(self, user_id: str,
                                    session_id: str) -> None:
        """Remove session from user activity tracking"""
        activity_key = f"{self.activity_prefix}{user_id}"
        self.redis.srem(activity_key, session_id)