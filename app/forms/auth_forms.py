# app/forms/auth_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, EmailField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
import re

class LoginForm(FlaskForm):
    """Login form for user authentication"""
    username = StringField('Phone Number', validators=[DataRequired(message="Phone number is required")])
    password = PasswordField('Password', validators=[DataRequired(message="Password is required")])
    remember_me = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    """User registration form"""
    user_type = SelectField('User Type', choices=[
        ('patient', 'Patient'), 
        ('staff', 'Staff')
    ], validators=[DataRequired()])
    
  
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
        Length(min=10, max=10, message="Phone number must be 10 digits")
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
    
    def validate_phone(self, phone):
        """Validate phone number format"""
        if not phone.data.isdigit():
            raise ValidationError("Phone number must contain only digits")
        if len(phone.data) != 10:
            raise ValidationError("Phone number must be 10 digits")
    
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
    
 # Add these new forms to your existing auth_forms.py  changes 10.3

class ProfileForm(FlaskForm):
    """User profile update form"""
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