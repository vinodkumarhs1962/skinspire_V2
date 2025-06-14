from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, BooleanField, 
    DateField, DecimalField, HiddenField, FieldList, FormField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Email, Regexp, ValidationError
from datetime import date, datetime

class SupplierForm(FlaskForm):
    """Form for creating and editing suppliers."""
    
    supplier_name = StringField('Supplier Name', validators=[
        DataRequired(),
        Length(min=2, max=100, message='Supplier name must be between 2 and 100 characters')
    ])
    
    supplier_category = SelectField('Supplier Category', validators=[Optional()],
                                   choices=[
                                       ('', 'Select Category'),
                                       ('distributor', 'Distributor'),
                                       ('manufacturer', 'Manufacturer'),
                                       ('retailer', 'Retail Supplier'),
                                       ('wholesaler', 'Wholesaler'),
                                       ('other', 'Other')
                                   ])
    
    # Address fields
    address_line1 = StringField('Address Line 1', validators=[
        DataRequired(),
        Length(max=100, message='Address line 1 must be less than 100 characters')
    ])
    
    address_line2 = StringField('Address Line 2', validators=[
        Optional(),
        Length(max=100, message='Address line 2 must be less than 100 characters')
    ])
    
    city = StringField('City', validators=[
        DataRequired(),
        Length(max=50, message='City must be less than 50 characters')
    ])
    
    state = StringField('State', validators=[
        DataRequired(),
        Length(max=50, message='State must be less than 50 characters')
    ])
    
    country = StringField('Country', validators=[
        DataRequired(),
        Length(max=50, message='Country must be less than 50 characters')
    ])
    
    pincode = StringField('PIN Code', validators=[
        DataRequired(),
        Length(max=10, message='PIN code must be less than 10 characters')
    ])
    
    # Contact information
    contact_person_name = StringField('Contact Person', validators=[
        Optional(),
        Length(max=100, message='Contact person name must be less than 100 characters')
    ])
    
    phone = StringField('Phone', validators=[
        Optional(),
        Length(max=20, message='Phone number must be less than 20 characters')
    ])
    
    mobile = StringField('Mobile', validators=[
        DataRequired(),
        Length(max=20, message='Mobile number must be less than 20 characters')
    ])
    
    email = StringField('Email', validators=[
        Optional(),
        Email(message='Invalid email address'),
        Length(max=100, message='Email must be less than 100 characters')
    ])
    
    # Manager information
    manager_name = StringField('Manager Name', validators=[
        Optional(),
        Length(max=100, message='Manager name must be less than 100 characters')
    ])
    
    manager_phone = StringField('Manager Phone', validators=[
        Optional(),
        Length(max=20, message='Manager phone must be less than 20 characters')
    ])
    
    manager_mobile = StringField('Manager Mobile', validators=[
        Optional(),
        Length(max=20, message='Manager mobile must be less than 20 characters')
    ])
    
    manager_email = StringField('Manager Email', validators=[
        Optional(),
        Email(message='Invalid manager email address'),
        Length(max=100, message='Manager email must be less than 100 characters')
    ])
    
    # Business rules
    payment_terms = StringField('Payment Terms', validators=[
        Optional(),
        Length(max=100, message='Payment terms must be less than 100 characters')
    ])
    
    # GST Information
    gst_registration_number = StringField('GSTIN', validators=[
        Optional(),
        Regexp(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', 
               message='Invalid GST Registration Number format')
    ])
    
    pan_number = StringField('PAN', validators=[
        Optional(),
        Regexp(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', message='Invalid PAN format')
    ])
    
    tax_type = SelectField('Tax Type', validators=[Optional()],
                          choices=[
                              ('', 'Select Tax Type'),
                              ('regular', 'Regular'),
                              ('composition', 'Composition'),
                              ('unregistered', 'Unregistered')
                          ])
    
    state_code = StringField('State Code', validators=[
        Optional(),
        Regexp(r'^[0-9]{2}$', message='State code must be a 2-digit number')
    ])
    
    # Bank details
    bank_account_name = StringField('Account Name', validators=[
        Optional(),
        Length(max=100, message='Account name must be less than 100 characters')
    ])
    
    bank_account_number = StringField('Account Number', validators=[
        Optional(),
        Length(max=30, message='Account number must be less than 30 characters')
    ])
    
    bank_name = StringField('Bank Name', validators=[
        Optional(),
        Length(max=100, message='Bank name must be less than 100 characters')
    ])
    
    ifsc_code = StringField('IFSC Code', validators=[
        Optional(),
        Regexp(r'^[A-Z]{4}0[A-Z0-9]{6}$', message='Invalid IFSC code format')
    ])
    
    bank_branch = StringField('Branch', validators=[
        Optional(),
        Length(max=100, message='Branch name must be less than 100 characters')
    ])
    
    # Additional information
    remarks = TextAreaField('Remarks', validators=[
        Optional(),
        Length(max=255, message='Remarks must be less than 255 characters')
    ])

class PurchaseOrderLineForm(FlaskForm):
    """Form for purchase order line items."""
    
    medicine_id = HiddenField('Medicine ID', validators=[DataRequired()])
    medicine_name = StringField('Medicine Name', render_kw={'readonly': True})
    units = DecimalField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Quantity must be greater than zero')
    ])
    pack_purchase_price = DecimalField('Pack Purchase Price', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Purchase price must be greater than zero')
    ])
    pack_mrp = DecimalField('Pack MRP', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='MRP must be greater than zero')
    ])
    units_per_pack = DecimalField('Units Per Pack', validators=[
        DataRequired(),
        NumberRange(min=1, message='Units per pack must be at least 1')
    ])
    hsn_code = StringField('HSN Code', validators=[Optional()])
    gst_rate = DecimalField('GST Rate %', validators=[Optional()])
    cgst_rate = DecimalField('CGST Rate %', validators=[Optional()])
    sgst_rate = DecimalField('SGST Rate %', validators=[Optional()])
    igst_rate = DecimalField('IGST Rate %', validators=[Optional()])

class PurchaseOrderForm(FlaskForm):
    """Form for creating purchase orders."""
    
    supplier_id = SelectField('Supplier', validators=[DataRequired()])
    po_date = DateField('PO Date', validators=[DataRequired()], default=date.today)
    expected_delivery_date = DateField('Expected Delivery Date', validators=[Optional()])
    quotation_id = StringField('Quotation Reference', validators=[Optional()])
    quotation_date = DateField('Quotation Date', validators=[Optional()])
    currency_code = SelectField('Currency', validators=[DataRequired()], default='INR')
    exchange_rate = DecimalField('Exchange Rate', validators=[
        DataRequired(),
        NumberRange(min=0.000001, message='Exchange rate must be greater than zero')
    ], default=1.0)
    
    # These will be dynamically handled in the view
    medicine_ids = HiddenField('Medicine IDs')
    medicine_names = HiddenField('Medicine Names')
    quantities = HiddenField('Quantities')
    pack_purchase_prices = HiddenField('Pack Purchase Prices')
    pack_mrps = HiddenField('Pack MRPs')
    units_per_packs = HiddenField('Units Per Pack')
    hsn_codes = HiddenField('HSN Codes')
    gst_rates = HiddenField('GST Rates')
    cgst_rates = HiddenField('CGST Rates')
    sgst_rates = HiddenField('SGST Rates')
    igst_rates = HiddenField('IGST Rates')

class SupplierInvoiceLineForm(FlaskForm):
    """Form for supplier invoice line items."""
    
    medicine_id = HiddenField('Medicine ID', validators=[DataRequired()])
    medicine_name = StringField('Medicine Name', render_kw={'readonly': True})
    units = DecimalField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Quantity must be greater than zero')
    ])
    pack_purchase_price = DecimalField('Pack Purchase Price', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Purchase price must be greater than zero')
    ])
    pack_mrp = DecimalField('Pack MRP', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='MRP must be greater than zero')
    ])
    units_per_pack = DecimalField('Units Per Pack', validators=[
        DataRequired(),
        NumberRange(min=1, message='Units per pack must be at least 1')
    ])
    is_free_item = BooleanField('Free Item')
    referenced_line_id = HiddenField('Referenced Line ID')
    discount_percent = DecimalField('Discount %', validators=[
        Optional(),
        NumberRange(min=0, max=100, message='Discount must be between 0 and 100')
    ], default=0)
    pre_gst_discount = BooleanField('Pre-GST Discount', default=True)
    hsn_code = StringField('HSN Code', validators=[Optional()])
    gst_rate = DecimalField('GST Rate %', validators=[Optional()])
    cgst_rate = DecimalField('CGST Rate %', validators=[Optional()])
    sgst_rate = DecimalField('SGST Rate %', validators=[Optional()])
    igst_rate = DecimalField('IGST Rate %', validators=[Optional()])
    batch_number = StringField('Batch Number', validators=[
        DataRequired(),
        Length(min=1, max=20, message='Batch number must be between 1 and 20 characters')
    ])
    manufacturing_date = DateField('Manufacturing Date', validators=[Optional()])
    expiry_date = DateField('Expiry Date', validators=[DataRequired()])
    itc_eligible = BooleanField('ITC Eligible', default=True)
    
    def validate_expiry_date(self, field):
        """Validate that expiry date is in the future."""
        if field.data and field.data <= date.today():
            raise ValidationError('Expiry date must be in the future')
    
    def validate_manufacturing_date(self, field):
        """Validate that manufacturing date is before expiry date if provided."""
        if field.data and self.expiry_date.data and field.data >= self.expiry_date.data:
            raise ValidationError('Manufacturing date must be before expiry date')

class SupplierInvoiceForm(FlaskForm):
    """Form for creating supplier invoices."""
    
    supplier_id = SelectField('Supplier', validators=[DataRequired()])
    po_id = SelectField('Purchase Order', validators=[Optional()])
    supplier_invoice_number = StringField('Invoice Number', validators=[
        DataRequired(),
        Length(min=1, max=50, message='Invoice number must be between 1 and 50 characters')
    ])
    invoice_date = DateField('Invoice Date', validators=[DataRequired()], default=date.today)
    supplier_gstin = StringField('Supplier GSTIN', validators=[
        Optional(),
        Regexp(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', 
               message='Invalid GST Registration Number format')
    ])
    place_of_supply = StringField('Place of Supply (State Code)', validators=[
        DataRequired(),
        Regexp(r'^[0-9]{2}$', message='State code must be a 2-digit number')
    ])
    reverse_charge = BooleanField('Reverse Charge', default=False)
    currency_code = SelectField('Currency', validators=[DataRequired()], default='INR')
    exchange_rate = DecimalField('Exchange Rate', validators=[
        DataRequired(),
        NumberRange(min=0.000001, message='Exchange rate must be greater than zero')
    ], default=1.0)
    due_date = DateField('Due Date', validators=[Optional()])
    itc_eligible = BooleanField('ITC Eligible', default=True)
    
    # These will be dynamically handled in the view
    medicine_ids = HiddenField('Medicine IDs')
    medicine_names = HiddenField('Medicine Names')
    quantities = HiddenField('Quantities')
    pack_purchase_prices = HiddenField('Pack Purchase Prices')
    pack_mrps = HiddenField('Pack MRPs')
    units_per_packs = HiddenField('Units Per Pack')
    is_free_items = HiddenField('Is Free Items')
    referenced_line_ids = HiddenField('Referenced Line IDs')
    discount_percents = HiddenField('Discount Percentages')
    pre_gst_discounts = HiddenField('Pre-GST Discounts')
    hsn_codes = HiddenField('HSN Codes')
    gst_rates = HiddenField('GST Rates')
    cgst_rates = HiddenField('CGST Rates')
    sgst_rates = HiddenField('SGST Rates')
    igst_rates = HiddenField('IGST Rates')
    batch_numbers = HiddenField('Batch Numbers')
    manufacturing_dates = HiddenField('Manufacturing Dates')
    expiry_dates = HiddenField('Expiry Dates')
    item_itc_eligibles = HiddenField('Item ITC Eligibles')
    
    def validate_due_date(self, field):
        """Validate that due date is after invoice date if provided."""
        if field.data and field.data < self.invoice_date.data:
            raise ValidationError('Due date must be on or after invoice date')

class SupplierPaymentForm(FlaskForm):
    """Form for recording supplier payments."""
    
    supplier_id = HiddenField('Supplier ID', validators=[DataRequired()])
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=date.today)
    payment_method = SelectField('Payment Method', validators=[DataRequired()],
                                choices=[
                                    ('cash', 'Cash'),
                                    ('cheque', 'Cheque'),
                                    ('bank_transfer', 'Bank Transfer'),
                                    ('upi', 'UPI'),
                                    ('card', 'Card'),
                                    ('other', 'Other')
                                ])
    currency_code = SelectField('Currency', validators=[DataRequired()], default='INR')
    exchange_rate = DecimalField('Exchange Rate', validators=[
        DataRequired(),
        NumberRange(min=0.000001, message='Exchange rate must be greater than zero')
    ], default=1.0)
    amount = DecimalField('Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than zero')
    ])
    reference_no = StringField('Reference Number', validators=[
        Optional(),
        Length(max=50, message='Reference number must be less than 50 characters')
    ])
    notes = TextAreaField('Notes', validators=[
        Optional(),
        Length(max=255, message='Notes must be less than 255 characters')
    ])

class SupplierFilterForm(FlaskForm):
    """Form for filtering suppliers."""
    
    name = StringField('Supplier Name', validators=[Optional()])
    supplier_category = SelectField('Category', validators=[Optional()],
                                  choices=[
                                      ('', 'All'),
                                      ('distributor', 'Distributor'),
                                      ('manufacturer', 'Manufacturer'),
                                      ('retailer', 'Retail Supplier'),
                                      ('wholesaler', 'Wholesaler'),
                                      ('other', 'Other')
                                  ])
    gst_number = StringField('GSTIN', validators=[Optional()])
    status = SelectField('Status', validators=[Optional()],
                        choices=[
                            ('active', 'Active'),
                            ('inactive', 'Inactive'),
                            ('blacklisted', 'Blacklisted'),
                            ('all', 'All')
                        ], default='active')

class PurchaseOrderFilterForm(FlaskForm):
    """Form for filtering purchase orders."""
    
    po_number = StringField('PO Number', validators=[Optional()])
    supplier_id = SelectField('Supplier', validators=[Optional()])
    status = SelectField('Status', validators=[Optional()],
                        choices=[
                            ('', 'All'),
                            ('draft', 'Draft'),
                            ('approved', 'Approved'),
                            ('received', 'Received'),
                            ('cancelled', 'Cancelled')
                        ])
    start_date = DateField('From Date', validators=[Optional()])
    end_date = DateField('To Date', validators=[Optional()])
    
    def validate_end_date(self, field):
        """Validate that end_date is after start_date if both are provided."""
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('End Date must be after Start Date')

class SupplierInvoiceFilterForm(FlaskForm):
    """Form for filtering supplier invoices."""
    
    invoice_number = StringField('Invoice Number', validators=[Optional()])
    supplier_id = SelectField('Supplier', validators=[Optional()])
    po_id = SelectField('Purchase Order', validators=[Optional()])
    payment_status = SelectField('Payment Status', validators=[Optional()],
                                choices=[
                                    ('', 'All'),
                                    ('unpaid', 'Unpaid'),
                                    ('partial', 'Partially Paid'),
                                    ('paid', 'Paid')
                                ])
    start_date = DateField('From Date', validators=[Optional()])
    end_date = DateField('To Date', validators=[Optional()])
    
    def validate_end_date(self, field):
        """Validate that end_date is after start_date if both are provided."""
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('End Date must be after Start Date')