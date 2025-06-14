# app/forms/billing_forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, BooleanField, TextAreaField, DecimalField
from wtforms import FieldList, FormField, HiddenField, ValidationError
from wtforms.validators import DataRequired, Optional, Length, NumberRange

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
        if len(field.data) < 1:
            raise ValidationError("At least one line item is required")
        
        # Ensure all items have types and IDs
        for i, item in enumerate(field.data):
            if not item['item_type'] or not item['item_id']:
                raise ValidationError(f"Line item {i+1} is missing type or ID")
            
            # For Medicine and Prescription types, batch is required
            if item['item_type'] in ['Medicine', 'Prescription'] and not item.get('batch'):
                raise ValidationError(f"Batch is required for Medicine/Prescription items (line {i+1})")


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