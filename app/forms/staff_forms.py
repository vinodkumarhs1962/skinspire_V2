# app/forms/staff_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, FileField, SubmitField, HiddenField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
import re

class StaffManagementForm(FlaskForm):
    """Form for hospital administrators to manage staff members"""
    staff_id = HiddenField('Staff ID')

    employee_code = StringField('Employee ID', validators=[
        Optional(),
        Length(max=20, message="Employee ID cannot exceed 20 characters")
    ])

    title = SelectField('Title', choices=[
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
        ('Mrs', 'Mrs'),
        ('Dr', 'Dr')
    ], validators=[Optional()])

    staff_type = SelectField('Staff Type', choices=[
        ('staff', 'General Staff'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('therapist', 'Therapist'),
        ('receptionist', 'Receptionist'),
        ('pharmacist', 'Pharmacist'),
        ('admin', 'Administrator')
    ], default='staff', validators=[DataRequired(message="Staff type is required")])

    first_name = StringField('First Name', validators=[
        DataRequired(message="First name is required"),
        Length(min=2, max=50, message="First name must be between 2 and 50 characters")
    ])

    last_name = StringField('Last Name', validators=[
        DataRequired(message="Last name is required"),
        Length(min=2, max=50, message="Last name must be between 2 and 50 characters")
    ])

    # Specialization dropdown - populated dynamically based on staff_type
    specialization_id = SelectField('Specialization', validators=[Optional()], coerce=str)

    # Keep legacy specialization field for backward compatibility (free-text entry)
    specialization = StringField('Specialization (Custom)', validators=[
        Optional(),
        Length(max=100, message="Specialization cannot exceed 100 characters")
    ])
    
    role_id = SelectField('Role', coerce=int, validators=[Optional()])
    
    branch_id = SelectField('Branch', validators=[Optional()])
    
    status = SelectField('Status', choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated')
    ], validators=[Optional()])
    
    notes = TextAreaField('Admin Notes', validators=[Optional()])

    is_resource = BooleanField('Available as Resource', default=False)

    def validate_employee_code(self, field):
        """Validate employee code format if provided"""
        if field.data:
            # Example: Enforce alphanumeric format
            if not re.match(r'^[A-Za-z0-9-]+$', field.data):
                raise ValidationError("Employee ID must contain only letters, numbers, and hyphens")

class EmployeeIDGeneratorForm(FlaskForm):
    """Form for configuring employee ID generation settings"""
    prefix = StringField('Prefix', validators=[
        Optional(),
        Length(max=5, message="Prefix cannot exceed 5 characters")
    ])
    
    next_number = StringField('Next Number', validators=[
        DataRequired(message="Next number is required")
    ])
    
    padding = SelectField('Padding', choices=[
        ('2', '2 digits (01, 02...)'),
        ('3', '3 digits (001, 002...)'),
        ('4', '4 digits (0001, 0002...)'),
        ('5', '5 digits (00001, 00002...)')
    ], validators=[Optional()])
    
    suffix = StringField('Suffix', validators=[
        Optional(),
        Length(max=5, message="Suffix cannot exceed 5 characters")
    ])
    
    separator = SelectField('Separator', choices=[
        ('', 'None'),
        ('-', 'Hyphen (-)'),
        ('_', 'Underscore (_)'),
        ('.', 'Dot (.)')
    ], validators=[Optional()])
    
    submit = SubmitField('Save Settings')
    
    def validate_next_number(self, field):
        """Validate next number is a positive integer"""
        try:
            num = int(field.data)
            if num <= 0:
                raise ValidationError("Next number must be greater than zero")
        except ValueError:
            raise ValidationError("Next number must be a valid integer")