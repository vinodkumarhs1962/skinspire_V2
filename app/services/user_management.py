# app/services/user_management.py

from app.models import User, Staff, Patient, UserRoleMapping
from app.database import get_db
from app.security.encryption.field_encryption import FieldEncryption
from werkzeug.security import generate_password_hash

class UserManagementService:
    """Service class for user management operations"""
    
    def __init__(self, hospital_id, current_user_id=None):
        self.hospital_id = hospital_id
        self.current_user_id = current_user_id
        self.db_manager = get_db()
        
    def list_users(self, filters=None, page=1, per_page=10):
        """List users with filtering and pagination"""
        with self.db_manager.get_session() as session:
            # Implementation
            
    def get_user(self, user_id):
        """Get user details"""
        with self.db_manager.get_session() as session:
            # Implementation
            
    def create_user(self, user_data):
        """Create a new user"""
        with self.db_manager.get_session() as session:
            try:
                # Create user object
                user = User(
                    user_id=user_data['user_id'],
                    hospital_id=self.hospital_id,
                    entity_type=user_data['entity_type'],
                    entity_id=user_data['entity_id'],
                    is_active=True
                )
                
                # Set password with explicit hashing
                user.set_password(user_data['password'])
                
                # Add the user to the session
                session.add(user)
                session.commit()
                
                return user.user_id
                
            except Exception as e:
                session.rollback()
                raise e
            
    # More methods for update, deactivate, etc.