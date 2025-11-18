# app/forms/auth_forms.py
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField, 
    EmailField, HiddenField, DateField, TextAreaField, SubmitField,
    FileField, HiddenField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, ValidationError, Optional
)
import re
from datetime import date
from sqlalchemy import distinct
from flask import current_app
from app.services.database_service import get_db_session
from app.models.master import Hospital, Branch

class LoginForm(FlaskForm):
    """Login form for user authentication"""
    username = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required")
    ])
    # Password is Optional to allow bypass for test user 7777777777
    password = PasswordField('Password', validators=[
        Optional()
    ])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    """User registration form"""
    user_type = SelectField('User Type', choices=[
        ('patient', 'Patient'), 
        ('staff', 'Staff')
    ], validators=[DataRequired()])
    
    title = SelectField('Title', choices=[
        ('Mr', 'Mr'), 
        ('Ms', 'Ms'), 
        ('Mrs', 'Mrs'), 
        ('Dr', 'Dr')
    ])
    
    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(min=2, max=50, message="First name must be between 2 and 50 characters")
    ])
    
    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(min=2, max=50, message="Last name must be between 2 and 50 characters")
    ])
    
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required"),
        Length(min=7, max=15, message="Phone number must be between 7-15 characters")
    ])
    
    email = EmailField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters long")
    ])
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    
    # def validate_phone(self, phone):
    #     """Validate phone number format"""
    #     if not phone.data.isdigit():
    #         raise ValidationError("Phone number must contain only digits")
    #     if len(phone.data) != 10:
    #         raise ValidationError("Phone number must be 10 digits")
    
    def validate_phone(self, phone):
        """Validate phone number format specifically for Indian numbers"""
        # Remove spaces for validation
        cleaned_phone = phone.data.replace(' ', '')
        
        # Check for international format
        if cleaned_phone.startswith('+'):
            # For Indian numbers with country code (+91) - should be +91 followed by 10 digits
            if re.match(r'^\+91[0-9]{10}$', cleaned_phone):
                return  # Valid Indian number with country code
            
            # For other international formats, we can be more restrictive if needed
            # Or you can remove this if you only want to support Indian numbers
            if not re.match(r'^\+[0-9]{1,3}[0-9]{7,12}$', cleaned_phone):
                raise ValidationError("Invalid international phone format.")
            return  # Valid international format
        
        # For plain 10-digit Indian numbers (without country code)
        if len(cleaned_phone) == 10 and cleaned_phone.isdigit():
            return  # Valid Indian 10-digit number
        
        # Reject other formats
        raise ValidationError("Phone number must be 10 digits for Indian numbers")

    def validate_password(self, password):
        """Validate password complexity"""
        if not re.search(r'[A-Z]', password.data):
            raise ValidationError("Password must include at least one uppercase letter")
        if not re.search(r'[a-z]', password.data):
            raise ValidationError("Password must include at least one lowercase letter")
        if not re.search(r'[0-9]', password.data):
            raise ValidationError("Password must include at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password.data):
            raise ValidationError("Password must include at least one special character")

class EnhancedRegistrationForm(RegistrationForm):
    """Enhanced registration form with hospital and branch selection"""
    
    hospital_id = SelectField('Hospital', validators=[Optional()])
    branch_id = SelectField('Branch', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(EnhancedRegistrationForm, self).__init__(*args, **kwargs)
        self.populate_hospitals()
    
    def populate_hospitals(self):
        """Populate hospital choices from database"""
        try:
            with get_db_session() as session:
                hospitals = session.query(Hospital).filter_by(is_active=True).all()
                self.hospital_id.choices = [(str(h.hospital_id), h.name) for h in hospitals]
                # Add empty choice
                self.hospital_id.choices.insert(0, ('', 'Select Hospital'))
        except Exception as e:
            current_app.logger.error(f"Error populating hospitals: {str(e)}")
            self.hospital_id.choices = [('', 'No hospitals available')]
    
    def populate_branches(self, hospital_id):
        """Populate branch choices based on selected hospital"""
        try:
            with get_db_session() as session:
                branches = session.query(Branch).filter_by(
                    hospital_id=hospital_id, 
                    is_active=True
                ).all()
                self.branch_id.choices = [(str(b.branch_id), b.name) for b in branches]
                # Add empty choice
                self.branch_id.choices.insert(0, ('', 'Select Branch'))
        except Exception as e:
            current_app.logger.error(f"Error populating branches: {str(e)}")
            self.branch_id.choices = [('', 'No branches available')]

class ProfileForm(FlaskForm):
    """Basic Profile Form for both Staff and Patient"""
    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(min=2, max=50, message="First name must be between 2 and 50 characters")
    ])
    
    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(min=2, max=50, message="Last name must be between 2 and 50 characters")
    ])
    
    email = EmailField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])

class StaffProfileForm(FlaskForm):
    """Detailed Staff Profile Form"""
    # Personal Information
    title = SelectField('Title', choices=[
        ('Mr', 'Mr'), 
        ('Ms', 'Ms'), 
        ('Mrs', 'Mrs'), 
        ('Dr', 'Dr')
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(min=2, max=50, message="First name must be between 2 and 50 characters")
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(min=2, max=50, message="Last name must be between 2 and 50 characters")
    ])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d')
    gender = SelectField('Gender', choices=[
        ('Male', 'Male'), 
        ('Female', 'Female'), 
        ('Other', 'Other')
    ])
    
    # Contact Information
    email = EmailField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    # phone = StringField('Phone Number', validators=[
    #     DataRequired(message="Phone number is required"),
    #     Length(min=10, max=10, message="Phone number must be 10 digits")
    # ])
    phone = StringField('Phone Number', render_kw={'readonly': True})
    address = StringField('Address')
    
    # Professional Information
    specialization = StringField('Specialization')
    employee_code = StringField('Employee Code')
    qualifications = StringField('Qualifications')
    certifications = StringField('Certifications')
    
    # Employment Information
    join_date = DateField('Join Date', format='%Y-%m-%d')
    designation = StringField('Designation')
    department = StringField('Department')

class PatientProfileForm(FlaskForm):
    """Detailed Patient Profile Form"""
    # Personal Information
    title = SelectField('Title', choices=[
        ('Mr', 'Mr'), 
        ('Ms', 'Ms'), 
        ('Mrs', 'Mrs'), 
        ('Dr', 'Dr')
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(min=2, max=50, message="First name must be between 2 and 50 characters")
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(min=2, max=50, message="Last name must be between 2 and 50 characters")
    ])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[
        DataRequired(message="Date of birth is required")
    ])
    gender = SelectField('Gender', choices=[
        ('Male', 'Male'), 
        ('Female', 'Female'), 
        ('Other', 'Other')
    ], validators=[
        DataRequired(message="Gender is required")
    ])
    marital_status = SelectField('Marital Status', choices=[
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed')
    ])
    
    # Contact Information
    email = EmailField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    # phone = StringField('Phone Number', validators=[
    #     DataRequired(message="Phone number is required"),
    #     Length(min=10, max=10, message="Phone number must be 10 digits")
    # ])
    phone = StringField('Phone Number', render_kw={'readonly': True})
    address = StringField('Address')
    
    # Medical Information
    blood_group = SelectField('Blood Group', choices=[
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'),
        ('AB+', 'AB+'), ('AB-', 'AB-')
    ])
    allergies = StringField('Allergies')
    
    # Emergency Contact
    emergency_contact_name = StringField('Emergency Contact Name')
    emergency_contact_relation = StringField('Relation')
    emergency_contact_phone = StringField('Emergency Contact Phone')
    
    # Preferences
    preferred_language = SelectField('Preferred Language', choices=[
        ('English', 'English'),
        ('Hindi', 'Hindi'),
        ('Tamil', 'Tamil'),
        ('Telugu', 'Telugu'),
        ('Kannada', 'Kannada'),
        ('Malayalam', 'Malayalam')
    ])
    communication_preference = SelectField('Communication Preference', choices=[
        ('Email', 'Email'),
        ('SMS', 'SMS'),
        ('WhatsApp', 'WhatsApp'),
        ('Phone Call', 'Phone Call')
    ])

class PasswordChangeForm(FlaskForm):
    """Password change form"""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message="Current password is required")
    ])
    
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required"),
        Length(min=8, message="Password must be at least 8 characters long")
    ])
    
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password"),
        EqualTo('new_password', message="Passwords must match")
    ])
    
    def validate_new_password(self, field):
        """Validate new password complexity"""
        if not re.search(r'[A-Z]', field.data):
            raise ValidationError("Password must include at least one uppercase letter")
        if not re.search(r'[a-z]', field.data):
            raise ValidationError("Password must include at least one lowercase letter")
        if not re.search(r'[0-9]', field.data):
            raise ValidationError("Password must include at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', field.data):
            raise ValidationError("Password must include at least one special character")

class ForgotPasswordForm(FlaskForm):
    """Form for initiating password reset"""
    username_or_email = StringField('Phone Number or Email', validators=[
        DataRequired(message="Please provide your phone number or email")
    ])

class ResetPasswordForm(FlaskForm):
    """Form for resetting password"""
    user_id = HiddenField('User ID')  # Hidden field to store user identifier
    
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required"),
        Length(min=8, message="Password must be at least 8 characters long")
    ])
    
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password"),
        EqualTo('new_password', message="Passwords must match")
    ])
    
    def validate_new_password(self, field):
        """Validate new password complexity"""
        if not re.search(r'[A-Z]', field.data):
            raise ValidationError("Password must include at least one uppercase letter")
        if not re.search(r'[a-z]', field.data):
            raise ValidationError("Password must include at least one lowercase letter")
        if not re.search(r'[0-9]', field.data):
            raise ValidationError("Password must include at least one number")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', field.data):
            raise ValidationError("Password must include at least one special character")

# Add this to app/forms/auth_forms.py
# Ensure this is compatible with the existing StaffApprovalRequestForm

class StaffApprovalRequestForm(FlaskForm):
    """Form for staff to submit additional information for approval"""
    # Add this to the top of the class to maintain existing attributes:
    role_id = SelectField('Requested Role', 
                        validators=[Optional()],
                        description="Select the role you are applying for",
                        coerce=int)
    qualifications = StringField('Qualifications', 
                               validators=[DataRequired(), Length(max=200)],
                               description="Your educational qualifications")
                               
    experience = TextAreaField('Professional Experience', 
                              validators=[DataRequired(), Length(max=1000)],
                              description="Describe your relevant work experience")
                              
    specialization = StringField('Specialization', 
                                validators=[DataRequired(), Length(max=100)],
                                description="Your area of expertise")
    
    # Add role selection field - using integer for role_id
    role_id = SelectField('Requested Role', 
                        validators=[Optional()],
                        description="Select the role you are applying for",
                        coerce=int)  # Use coerce=int to handle integer role_id
    
    reference = StringField('Professional Reference', 
                          validators=[Optional(), Length(max=200)],
                          description="Name and contact of a professional reference (optional)")
    
    # Add branch selection
    branch_id = SelectField('Branch', 
                          validators=[Optional()],
                          description="Select the branch you will primarily work at")
    
    comments = TextAreaField('Additional Comments', 
                            validators=[Optional(), Length(max=500)])
    
    def __init__(self, *args, **kwargs):
        super(StaffApprovalRequestForm, self).__init__(*args, **kwargs)
        self.hospital_name = None
        self.default_branch_name = None
        self.branch_choices = []
        self.role_choices = []
    
    def populate_branches(self, hospital_id):
        """Populate branch choices for the given hospital"""
        from app.services.database_service import get_db_session
        from app.models.master import Branch, Hospital
        
        with get_db_session() as session:
            # Get hospital name
            hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
            if hospital:
                self.hospital_name = hospital.name
            
            # Get branches for the hospital
            branches = session.query(Branch).filter_by(hospital_id=hospital_id).all()
            
            # Set branch choices
            self.branch_choices = [(str(b.branch_id), b.name) for b in branches]
            self.branch_id.choices = [('', 'Select Branch')] + self.branch_choices
    
    def populate_roles(self, hospital_id):
        """Populate role choices for the given hospital"""
        from app.services.database_service import get_db_session
        from app.models.config import RoleMaster
        
        with get_db_session() as session:
            try:
                # Get roles for the hospital that are active
                roles = session.query(RoleMaster).filter_by(
                    hospital_id=hospital_id
                ).all()
                
                if roles:
                    # Set role choices - use int for role_id
                    self.role_choices = [(r.role_id, r.role_name) for r in roles]
                    self.role_id.choices = [(0, 'Select Role')] + self.role_choices
                else:
                    # No roles found
                    self.role_id.choices = [(0, 'No roles available')]
            except Exception as e:
                # If there's an error, set empty choices
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error populating roles: {str(e)}")
                self.role_id.choices = [(0, 'No roles available')]

    def __init__(self, *args, **kwargs):
        super(StaffApprovalRequestForm, self).__init__(*args, **kwargs)
        self.role_choices = []
        # Default empty choice
        self.role_id.choices = [(0, 'Select Role')]