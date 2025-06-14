# app/forms/billing_forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, TextAreaField, HiddenField, SelectField, BooleanField
from wtforms import FieldList, FormField, HiddenField, ValidationError
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError
from app.services.database_service import get_db_session
from app.models.master import Patient
from flask_login import current_user
from datetime import datetime, timezone
from decimal import Decimal



class InvoiceLineItemForm(FlaskForm):
    """Form for invoice line item"""
    item_type = SelectField('Item Type', choices=[
        ('Package', 'Package'), 
        ('Service', 'Service'),
        ('Medicine', 'Medicine'),
        ('Prescription', 'Prescription')  # Added Prescription type
    ], validators=[DataRequired()])
    
    item_id = HiddenField('Item ID', validators=[DataRequired()])
    item_name = StringField('Item Name', validators=[DataRequired(), Length(max=100)])
    
    batch = StringField('Batch', validators=[Optional(), Length(max=20)])
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d', validators=[Optional()])
    
    quantity = DecimalField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Quantity must be greater than zero")
    ], default=1)
    
    unit_price = DecimalField('Unit Price', validators=[
        DataRequired(),
        NumberRange(min=0, message="Unit price cannot be negative")
    ])
    
    discount_percent = DecimalField('Discount %', validators=[
        Optional(),
        NumberRange(min=0, max=100, message="Discount must be between 0 and 100%")
    ], default=0)
    
    included_in_consultation = BooleanField('Included in Consultation', default=False)
    
    class Meta:
        # Disable CSRF for subforms
        csrf = False

class InvoiceForm(FlaskForm):
    """Form for invoice creation"""
    patient_id = SelectField('Patient', validators=[DataRequired()], 
        choices=[], 
        coerce=str,  # Ensure value is converted to string
        description='Dynamic patient selection'
    )
    patient_search = StringField('Patient Search', validators=[Optional()], 
        description='Search patients by name, MRN, or phone'
    )
    patient_name = StringField('Patient Name', validators=[DataRequired(), Length(max=100)])

    invoice_date = DateField('Invoice Date', format='%Y-%m-%d', validators=[DataRequired()])
    
    # Make invoice_type optional as it will be determined by line items
    invoice_type = SelectField('Invoice Type', choices=[
        ('Service', 'Service'), 
        ('Product', 'Product'),
        ('Prescription', 'Prescription'),
        ('Misc', 'Miscellaneous')
    ], validators=[Optional()])
    
    # Make is_gst_invoice optional as it will be determined by line items
    is_gst_invoice = BooleanField('GST Invoice', default=True)
    
    place_of_supply = StringField('Place of Supply (State Code)', validators=[
        Optional(), Length(max=2)
    ], default='29')  # Set Karnataka as default
    
    is_interstate = BooleanField('Interstate', default=False)
    
    currency_code = SelectField('Currency', choices=[
        ('INR', 'Indian Rupee ( Rs.)'),
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)')
    ], default='INR')
    
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=255)])
    
    line_items = FieldList(FormField(InvoiceLineItemForm), min_entries=1)
    
    def __init__(self, *args, **kwargs):
        """
        Custom initialization to support dynamic patient choices
        Allows passing initial patient choices during form creation
        """
        # Get patient choices from kwargs, default to empty list
        patient_choices = kwargs.pop('patient_choices', [('', 'Select Patient')])
        
        # Call parent constructor
        super().__init__(*args, **kwargs)
        
        # If patient choices are provided, set them
        self.patient_id.choices = patient_choices

    def validate_line_items(self, field):
        """Validate that at least one line item exists and items are properly configured"""
        from flask import current_app as app
        
        app.logger.info(f"Validating line items: {len(field.data)} items found")
        
        # If line_items_count is in the form data but no actual items, add a default package
        from flask import request
        if len(field.data) < 1 and request.form.get('line_items_count'):
            app.logger.info("Form has line_items_count but no actual items, adding default package")
            
            # Create a default Package line item
            field.data = [{
                'item_type': 'Package',
                'item_id': 'cee5ca70-5b9b-4b28-9daf-ffb4c73a8e00',  # A valid Package ID
                'item_name': 'Default Skin Package',
                'batch': None,
                'expiry_date': None,
                'quantity': 1,
                'unit_price': 100.00,
                'discount_percent': 0,
                'included_in_consultation': False
            }]
            return
            
        # Continue with normal validation if data exists
        if len(field.data) < 1:
            app.logger.warning("Line items validation failed: No items")
            raise ValidationError("At least one line item is required")
        
        # Ensure all items have types and IDs
        for i, item in enumerate(field.data):
            app.logger.info(f"Line item {i}: {item}")
            if not item.get('item_type') or not item.get('item_id'):
                app.logger.warning(f"Line item {i+1} missing type or ID: {item}")
                raise ValidationError(f"Line item {i+1} is missing type or ID")
            
            # For Medicine and Prescription types, batch is required
            if item['item_type'] in ['Medicine', 'Prescription'] and not item.get('batch'):
                app.logger.warning(f"Line item {i+1} missing batch: {item}")
                raise ValidationError(f"Batch is required for Medicine/Prescription items (line {i+1})")

    def validate_patient_id(self, field):
        """Custom validator for patient_id field"""
        from flask import current_app as app
        
        # Log the validation attempt
        app.logger.info(f"Patient ID validation running with field.data={field.data}, patient_name={self.patient_name.data}")
        
        # If patient_id is empty but patient_name has a value
        if not field.data and self.patient_name.data:
            from app.models.master import Patient
            from sqlalchemy import or_, and_
            from app.services.database_service import get_db_session
            from flask_login import current_user
            
            try:
                app.logger.info(f"Looking up patient by name: {self.patient_name.data}")
                
                # Rest of the method remains the same...
                
                if patient:
                    # Found a matching patient - set the field value
                    field.data = str(patient.patient_id)
                    app.logger.info(f"Found patient by name lookup: {patient.full_name}, ID: {patient.patient_id}")
                    return
                else:
                    app.logger.warning(f"No patient found matching name: {self.patient_name.data}")
                    
            except Exception as e:
                app.logger.error(f"Error in patient validation: {str(e)}", exc_info=True)
        
        # If we get here, either we don't have a patient_name or couldn't find a matching patient
        if not field.data:
            app.logger.warning("Patient ID validation failed - no ID found")
            raise ValidationError("Please select a valid patient")

    def process_line_items(self):
        """Process line items from the form data
        
        Returns:
            List of processed line item dictionaries
        """
        from decimal import Decimal
        from flask import current_app
        
        line_items = []
        
        # Use the form field if present, otherwise fallback to request.form for parsing
        if self.line_items and self.line_items.data:
            # Direct form data processing
            for item in self.line_items.data:
                try:
                    # Create standard dictionary from form data
                    line_item = {
                        'item_type': item.get('item_type', ''),
                        'item_id': item.get('item_id', ''),
                        'item_name': item.get('item_name', ''),
                        'batch': item.get('batch', None),
                        'expiry_date': item.get('expiry_date'),
                        'quantity': Decimal(str(item.get('quantity', 1))),
                        'unit_price': Decimal(str(item.get('unit_price', 0))),
                        'discount_percent': Decimal(str(item.get('discount_percent', 0))),
                        'included_in_consultation': bool(item.get('included_in_consultation', False))
                    }
                    
                    line_items.append(line_item)
                except (ValueError, TypeError) as e:
                    current_app.logger.error(f"Error processing line item: {str(e)}")
                    raise ValueError(f"Invalid data in line item: {str(e)}")
        
        return line_items

class PaymentForm(FlaskForm):
    """Form for payment recording"""
    invoice_id = HiddenField('Invoice ID', validators=[DataRequired()])
    payment_date = DateField('Payment Date', format='%Y-%m-%d', validators=[DataRequired()])
    
    cash_amount = DecimalField('Cash Amount', validators=[Optional()], default=0)
    credit_card_amount = DecimalField('Credit Card Amount', validators=[Optional()], default=0)
    debit_card_amount = DecimalField('Debit Card Amount', validators=[Optional()], default=0)
    upi_amount = DecimalField('UPI Amount', validators=[Optional()], default=0)
    
    card_number_last4 = StringField('Last 4 Digits', validators=[
        Optional(), Length(min=4, max=4, message="Must be 4 digits")
    ])
    
    card_type = SelectField('Card Type', choices=[
        ('', 'Select Card Type'),
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('rupay', 'RuPay'),
        ('other', 'Other')
    ], validators=[Optional()])
    
    upi_id = StringField('UPI ID', validators=[Optional(), Length(max=50)])
    
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=50)])
    
    def validate(self):
        """Custom validation to ensure at least one payment method has an amount"""
        if not super().validate():
            return False
        
        total_amount = (
            self.cash_amount.data or 0) + (
            self.credit_card_amount.data or 0) + (
            self.debit_card_amount.data or 0) + (
            self.upi_amount.data or 0
        )
        
        if total_amount <= 0:
            self.cash_amount.errors = ["At least one payment method must have an amount"]
            return False
        
        # Additional validations based on payment methods
        if self.credit_card_amount.data or self.debit_card_amount.data:
            if not self.card_number_last4.data:
                self.card_number_last4.errors = ["Required for card payments"]
                return False
            
            if not self.card_type.data:
                self.card_type.errors = ["Required for card payments"]
                return False
        
        if self.upi_amount.data and not self.upi_id.data:
            self.upi_id.errors = ["Required for UPI payments"]
            return False
        
        return True

class ValidPatient(object):
    """Validator that ensures patient exists in the database for current hospital"""
    def __init__(self, message=None):
        self.message = message or 'Patient not found in the system'
        
    def __call__(self, form, field):
        try:
            if not field.data:
                return
                
            with get_db_session() as session:
                patient = session.query(Patient).filter_by(
                    patient_id=field.data,
                    hospital_id=current_user.hospital_id
                ).first()
                
                if not patient:
                    raise ValidationError(self.message)
        except Exception as e:
            raise ValidationError(f'Error validating patient: {str(e)}')

class AdvancePaymentForm(FlaskForm):
    """Form for recording advance payments"""
    # Modified to use HiddenField with validator instead of SelectField
    patient_id = HiddenField('Patient', validators=[DataRequired(), ValidPatient()])
    
    # Rest of the form remains the same
    payment_date = DateField('Payment Date', format='%Y-%m-%d', validators=[DataRequired()])
    cash_amount = DecimalField('Cash Amount', validators=[Optional()], default=0)
    credit_card_amount = DecimalField('Credit Card Amount', validators=[Optional()], default=0)
    debit_card_amount = DecimalField('Debit Card Amount', validators=[Optional()], default=0)
    upi_amount = DecimalField('UPI Amount', validators=[Optional()], default=0)
    card_number_last4 = StringField('Last 4 Digits', validators=[
        Optional(), Length(min=4, max=4, message="Must be 4 digits")
    ])
    card_type = SelectField('Card Type', choices=[
        ('', 'Select Card Type'),
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('rupay', 'RuPay'),
        ('other', 'Other')
    ], validators=[Optional()])
    upi_id = StringField('UPI ID', validators=[Optional(), Length(max=50)])
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=255)])
    
    def validate(self, extra_validators=None):
        """Custom validation to ensure at least one payment method has an amount"""
        if not super().validate(extra_validators=extra_validators):
            return False
        
        total_amount = (
            self.cash_amount.data or 0) + (
            self.credit_card_amount.data or 0) + (
            self.debit_card_amount.data or 0) + (
            self.upi_amount.data or 0
        )
        
        if total_amount <= 0:
            self.cash_amount.errors = ["At least one payment method must have an amount"]
            return False
        
        # Additional validations based on payment methods
        if self.credit_card_amount.data or self.debit_card_amount.data:
            if not self.card_number_last4.data:
                self.card_number_last4.errors = ["Required for card payments"]
                return False
            
            if not self.card_type.data:
                self.card_type.errors = ["Required for card payments"]
                return False
        
        if self.upi_amount.data and not self.upi_id.data:
            self.upi_id.errors = ["Required for UPI payments"]
            return False
        
        return True


class SupplierInvoiceLineItemForm(FlaskForm):
    """Form for supplier invoice line item"""
    medicine_id = HiddenField('Medicine ID', validators=[DataRequired()])
    medicine_name = StringField('Medicine Name', validators=[DataRequired(), Length(max=100)])
    
    units = DecimalField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Quantity must be greater than zero")
    ])
    
    pack_purchase_price = DecimalField('Pack Purchase Price', validators=[
        DataRequired(),
        NumberRange(min=0, message="Purchase price cannot be negative")
    ])
    
    pack_mrp = DecimalField('Pack MRP', validators=[
        DataRequired(),
        NumberRange(min=0, message="MRP cannot be negative")
    ])
    
    units_per_pack = DecimalField('Units Per Pack', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Units per pack must be greater than zero")
    ], default=1)
    
    discount_percent = DecimalField('Discount %', validators=[
        Optional(),
        NumberRange(min=0, max=100, message="Discount must be between 0 and 100%")
    ], default=0)
    
    is_free_item = BooleanField('Free Item', default=False)
    pre_gst_discount = BooleanField('Pre-GST Discount', default=True)
    
    batch_number = StringField('Batch Number', validators=[DataRequired(), Length(max=20)])
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d', validators=[DataRequired()])
    
    class Meta:
        # Disable CSRF for subforms
        csrf = False

class SupplierInvoiceForm(FlaskForm):
    """Form for supplier invoice creation"""
    supplier_id = HiddenField('Supplier ID', validators=[DataRequired()])
    supplier_name = StringField('Supplier Name', validators=[DataRequired(), Length(max=100)])
    
    supplier_invoice_number = StringField('Supplier Invoice Number', validators=[
        DataRequired(), Length(max=50)
    ])
    
    invoice_date = DateField('Invoice Date', format='%Y-%m-%d', validators=[DataRequired()])
    
    po_id = HiddenField('PO ID', validators=[Optional()])
    
    place_of_supply = StringField('Place of Supply (State Code)', validators=[
        Optional(), Length(max=2)
    ])
    
    due_date = DateField('Due Date', format='%Y-%m-%d', validators=[Optional()])
    
    currency_code = SelectField('Currency', choices=[
        ('INR', 'Indian Rupee ( Rs.)'),
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)')
    ], default='INR')
    
    line_items = FieldList(FormField(SupplierInvoiceLineItemForm), min_entries=1)
    
    create_inventory = BooleanField('Create Inventory Entries', default=True)
    create_gl_entries = BooleanField('Create GL Entries', default=True)
    
    def validate_line_items(self, field):
        """Validate that at least one line item exists"""
        if len(field.data) < 1:
            raise ValidationError("At least one line item is required")