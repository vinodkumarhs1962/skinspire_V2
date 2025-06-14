# app/forms/verification_forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
import re

class PhoneVerificationForm(FlaskForm):
    """Form for phone verification"""
    phone = StringField('Phone Number', validators=[
        DataRequired(),
        Length(min=10, max=15)
    ])
    submit = SubmitField('Send Verification Code')
    
    def validate_phone(self, field):
        """Validate phone number format"""
        if not re.match(r'^\+?[0-9]{10,15}$', field.data):
            raise ValidationError('Invalid phone number format. Use numbers only.')

class EmailVerificationForm(FlaskForm):
    """Form for email verification"""
    email = StringField('Email Address', validators=[
        DataRequired(),
        Length(max=255)
    ])
    submit = SubmitField('Send Verification Code')
    
    def validate_email(self, field):
        """Validate email format"""
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', field.data):
            raise ValidationError('Invalid email format.')

class VerificationCodeForm(FlaskForm):
    """Form for submitting verification code"""
    code_type = HiddenField('Code Type', validators=[DataRequired()])
    code = StringField('Verification Code', validators=[
        DataRequired(),
        Length(min=6, max=6)
    ])
    submit = SubmitField('Verify')
    resend = SubmitField('Resend Code')
    
    def validate_code(self, field):
        """Validate code format"""
        if not field.data.isdigit():
            raise ValidationError('Verification code must contain only digits.')