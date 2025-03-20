# app/services/user_service.py
import uuid
from app.services.database_service import get_db_session
from app.models import User

def create_user(username, password, user_type, hospital_id, personal_info=None):
   """
   Business logic for user creation, used by both API and UI
   
   Args:
       username (str): User's unique identifier
       password (str): User's password
       user_type (str): Type of user ('staff' or 'patient')
       hospital_id (UUID): Hospital associated with the user
       personal_info (dict, optional): Additional user information
   
   Returns:
       tuple: (success_status, result_or_error_message)
   """
   try:
       entity_id = str(uuid.uuid4())
       
       with get_db_session() as session:
           # Check if user exists
           existing_user = session.query(User).filter_by(user_id=username).first()
           if existing_user:
               return False, "User already exists"
           
           # Create new user
           new_user = User(
               user_id=username,
               hospital_id=hospital_id,
               entity_type='staff' if user_type == 'staff' else 'patient',
               entity_id=entity_id,
               is_active=True,
               failed_login_attempts=0
           )
           
           # Set password
           new_user.set_password(password)
           
           # Add personal info
           if personal_info and hasattr(new_user, 'first_name'):
               new_user.first_name = personal_info.get('first_name', '')
           if personal_info and hasattr(new_user, 'last_name'):
               new_user.last_name = personal_info.get('last_name', '')
           if personal_info and hasattr(new_user, 'email'):
               new_user.email = personal_info.get('email', '')
           
           # Add to database
           session.add(new_user)
           session.flush()
           
           return True, {"user_id": username}
   
   except Exception as e:
       return False, str(e)