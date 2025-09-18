# app/forms/supplier_forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, BooleanField, 
    DateField, DecimalField, HiddenField, FieldList, FormField, IntegerField, SubmitField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Email, Regexp, ValidationError
from datetime import date, datetime
from app.services.branch_service import populate_branch_choices_for_user

class SupplierForm(FlaskForm):
    """Form for creating and editing suppliers - aligned with original view."""
    
    # NEW: Optional branch selection (for admin users)
    branch_id = SelectField('Branch', validators=[Optional()], choices=[])

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
                                       ('others', 'Others')
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
    
    # Manager information (aligned with original)
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
    
    performance_rating = IntegerField('Performance Rating', validators=[
        Optional(),
        NumberRange(min=1, max=5, message='Rating must be between 1 and 5')
    ])
    
    black_listed = BooleanField('Black Listed')
    
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
    
    # Bank details (aligned with original)
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # NEW: Populate branch choices if user has access to multiple branches
        try:
            from flask_login import current_user
            from app.services.database_service import get_db_session
            from app.models.master import Branch
            
            if current_user and hasattr(current_user, 'hospital_id'):
                with get_db_session(read_only=True) as session:
                    branches = session.query(Branch).filter_by(
                        hospital_id=current_user.hospital_id,
                        is_active=True
                    ).order_by(Branch.name).all()
                    
                    if len(branches) > 1:  # Only show if multiple branches
                        self.branch_id.choices = [('', 'Select Branch')] + [
                            (str(branch.branch_id), f"{branch.name}") 
                            for branch in branches
                        ]
                    else:
                        # Single branch - hide the field
                        self.branch_id.render_kw = {'style': 'display: none;'}
                        if branches:
                            self.branch_id.data = str(branches[0].branch_id)
                            
        except Exception as e:
            # Fallback to default if error
            self.branch_id.choices = [('', 'Default Branch')]

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
    # Branch handling is done automatically in controller
    # based on user's branch assignment

    # Main fields
    branch_id = SelectField('Branch', validators=[Optional()], choices=[])
    po_number = StringField('PO Number', render_kw={'readonly': True})
    supplier_id = SelectField('Supplier', validators=[DataRequired()], choices=[], coerce=str)
    po_date = DateField('PO Date', validators=[DataRequired()], default=date.today)
    expected_delivery_date = DateField('Expected Delivery Date', validators=[Optional()])
    quotation_id = StringField('Quotation Reference', validators=[Optional()])
    quotation_date = DateField('Quotation Date', validators=[Optional()])
    currency_code = SelectField('Currency', validators=[DataRequired()], 
                              choices=[('INR', 'INR'), ('USD', 'USD'), ('EUR', 'EUR')],
                              default='INR')
    exchange_rate = DecimalField('Exchange Rate', validators=[
        DataRequired(),
        NumberRange(min=0.000001, message='Exchange rate must be greater than zero')
    ], default=1.0)
    
    # Additional details
    delivery_instructions = TextAreaField('Delivery Instructions', validators=[Optional()])
    terms_conditions = TextAreaField('Terms and Conditions', validators=[Optional()])
    notes = TextAreaField('Internal Notes', validators=[Optional()])
    
    # New hidden fields for discount and free items
    discount_percents = HiddenField('Discount Percents')
    discount_amounts = HiddenField('Discount Amounts')  
    is_free_items = HiddenField('Is Free Items') 

    # Status
    status = SelectField('Status', validators=[Optional()],
                        choices=[
                            ('draft', 'Draft'),
                            ('approved', 'Approved'),
                            ('cancelled', 'Cancelled')
                        ],
                        default='draft')
    
    # Hidden fields for line items data
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

class PurchaseOrderEditLineForm(FlaskForm):
    """Individual line item form for editing PO - with correct field names"""
    medicine_id = HiddenField('Medicine ID')
    medicine_name = StringField('Medicine', render_kw={'readonly': True})
    
    # Keep original field names as they match the database model
    quantity = DecimalField('Quantity', render_kw={'step': '0.01', 'min': '0'})
    pack_purchase_price = DecimalField('Rate', render_kw={'step': '0.01', 'min': '0'})
    pack_mrp = DecimalField('MRP', render_kw={'step': '0.01', 'min': '0'})
    
    units_per_pack = HiddenField('Units per Pack', default=1)
    discount_percent = DecimalField('Discount %', default=0, render_kw={'step': '0.1', 'min': '0', 'max': '100'})
    is_free_item = BooleanField('Free Item', default=False)
    hsn_code = HiddenField('HSN Code')
    gst_rate = HiddenField('GST Rate')

class PurchaseOrderEditForm(FlaskForm):
    """Centralized edit form for PO - with all required fields"""
    # Header fields
    po_number = StringField('PO Number', render_kw={'readonly': True})
    supplier_id = SelectField('Supplier', validators=[DataRequired()])
    po_date = DateField('PO Date', validators=[DataRequired()])
    
    # Optional date fields
    expected_delivery_date = DateField('Expected Delivery Date', validators=[Optional()])
    quotation_date = DateField('Quotation Date', validators=[Optional()])
    
    # Reference fields
    quotation_id = StringField('Quotation Reference', validators=[Optional()])
    
    # Currency fields
    currency_code = SelectField('Currency', 
                                choices=[('INR', 'INR'), ('USD', 'USD'), ('EUR', 'EUR')],
                                default='INR',
                                validators=[DataRequired()])
    exchange_rate = DecimalField('Exchange Rate', 
                                default=1.0, 
                                validators=[
                                    DataRequired(),
                                    NumberRange(min=0.000001, message='Exchange rate must be greater than zero')
                                ])
    
    # Additional text fields
    delivery_instructions = TextAreaField('Delivery Instructions', validators=[Optional()])
    terms_conditions = TextAreaField('Terms and Conditions', validators=[Optional()])
    notes = TextAreaField('Internal Notes', validators=[Optional()])
    
    # Branch field (if applicable)
    branch_id = SelectField('Branch', validators=[Optional()], choices=[])
    
    # Hidden total fields for calculations
    total_amount = HiddenField('Total Amount', default=0)
    subtotal = HiddenField('Subtotal', default=0)
    total_gst = HiddenField('Total GST', default=0)
    
    # Hidden fields for line item aggregates
    discount_percents = HiddenField('Discount Percents')
    discount_amounts = HiddenField('Discount Amounts')
    is_free_items = HiddenField('Is Free Items')
    
    # Line items - using FieldList with FormField
    line_items = FieldList(FormField(PurchaseOrderEditLineForm), min_entries=0)
    
    # hidden status field
    status = HiddenField('Status', default='draft')

    # Hidden fields for JavaScript population (if needed)
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

class SupplierInvoiceForm(FlaskForm):
    """Form for creating supplier invoices"""
    # Branch handling is done automatically in controller
    # based on user's branch assignment

    branch_id = SelectField('Branch', validators=[Optional()], choices=[])
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
    payment_status = SelectField('Payment Status', 
                               choices=[
                                   ('unpaid', 'Unpaid'),
                                   ('partial', 'Partially Paid'),
                                   ('paid', 'Paid')
                               ],
                               default='unpaid')
    due_date = DateField('Due Date', validators=[Optional()])
    itc_eligible = BooleanField('ITC Eligible', default=True)
    is_interstate = BooleanField('Interstate')
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    
    # Hidden fields for backward compatibility with JavaScript version
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

class SupplierInvoiceLineForm(FlaskForm):
    """Form for adding a line item to supplier invoice"""
    
    medicine_id = SelectField('Medicine', validators=[DataRequired()], 
                            choices=[('', 'Select Medicine')])
    batch_number = StringField('Batch Number', validators=[
        DataRequired(),
        Length(min=1, max=20, message='Batch number must be between 1 and 20 characters')
    ])
    expiry_date = DateField('Expiry Date', validators=[DataRequired()], format='%Y-%m-%d')
    quantity = DecimalField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Quantity must be greater than zero')
    ], default=1)
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
    ], default=1)
    discount_percent = DecimalField('Discount %', validators=[
        Optional(),
        NumberRange(min=0, max=100, message='Discount must be between 0 and 100')
    ], default=0)
    is_free_item = BooleanField('Free Item')


class SupplierInvoiceEditLineForm(FlaskForm):
    """Individual line item form for editing supplier invoice - FIXED validation"""
    medicine_id = HiddenField('Medicine ID')  # No validators - template will validate
    medicine_name = StringField('Medicine', render_kw={'readonly': True})
    
    # FIXED: Remove validators to prevent validation errors
    batch_number = StringField('Batch Number', render_kw={'maxlength': '20'})
    expiry_date = DateField('Expiry Date')
    quantity = DecimalField('Quantity', render_kw={'step': '0.01', 'min': '0'})
    pack_purchase_price = DecimalField('Rate', render_kw={'step': '0.01', 'min': '0'})
    pack_mrp = DecimalField('MRP', render_kw={'step': '0.01', 'min': '0'})
    
    units_per_pack = HiddenField('Units per Pack', default=1)
    discount_percent = DecimalField('Discount %', default=0, render_kw={'step': '0.1', 'min': '0', 'max': '100'})
    is_free_item = BooleanField('Free Item', default=False)
    hsn_code = HiddenField('HSN Code')
    gst_rate = HiddenField('GST Rate')
    manufacturing_date = DateField('Manufacturing Date', validators=[Optional()])
    itc_eligible = BooleanField('ITC Eligible', default=True)


class SupplierInvoiceEditLineForm(FlaskForm):
    """Individual line item form for editing supplier invoice - FIXED validation"""
    medicine_id = HiddenField('Medicine ID')  # No validators - template will validate
    medicine_name = StringField('Medicine', render_kw={'readonly': True})
    
    # FIXED: Remove validators to prevent validation errors
    batch_number = StringField('Batch Number', render_kw={'maxlength': '20'})
    expiry_date = DateField('Expiry Date')
    quantity = DecimalField('Quantity', render_kw={'step': '0.01', 'min': '0'})
    pack_purchase_price = DecimalField('Rate', render_kw={'step': '0.01', 'min': '0'})
    pack_mrp = DecimalField('MRP', render_kw={'step': '0.01', 'min': '0'})
    
    units_per_pack = HiddenField('Units per Pack', default=1)
    discount_percent = DecimalField('Discount %', default=0, render_kw={'step': '0.1', 'min': '0', 'max': '100'})
    is_free_item = BooleanField('Free Item', default=False)
    hsn_code = HiddenField('HSN Code')
    gst_rate = HiddenField('GST Rate')
    manufacturing_date = DateField('Manufacturing Date', validators=[Optional()])
    itc_eligible = BooleanField('ITC Eligible', default=True)


class SupplierInvoiceEditForm(FlaskForm):
    """Centralized edit form for supplier invoice - FIXED with default choices"""
    # Header fields
    supplier_invoice_number = StringField('Invoice Number', validators=[DataRequired()])
    invoice_date = DateField('Invoice Date', validators=[DataRequired()])
    
    # CRITICAL FIX: Set default choices to prevent None error
    supplier_id = SelectField('Supplier', validators=[DataRequired()], 
                             choices=[('', 'Select Supplier')], coerce=str)
    
    # FIXED: All optional fields - no validators where not required
    po_id = SelectField('Purchase Order', validators=[Optional()], 
                       choices=[('', 'Select Purchase Order (Optional)')], coerce=str)
    supplier_gstin = StringField('Supplier GSTIN', validators=[Optional()])
    place_of_supply = StringField('Place of Supply', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[Optional()])
    
    # Checkboxes with defaults
    reverse_charge = BooleanField('Reverse Charge', default=False)
    is_interstate = BooleanField('Interstate', default=False)
    itc_eligible = BooleanField('ITC Eligible', default=True)
    
    # CRITICAL FIX: Set default choices for currency
    currency_code = SelectField('Currency', 
                                choices=[('INR', 'INR'), ('USD', 'USD'), ('EUR', 'EUR')], 
                                default='INR', coerce=str)
    exchange_rate = DecimalField('Exchange Rate', default=1.0, validators=[NumberRange(min=0.000001)])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    # Line items - no min_entries to avoid validation issues
    line_items = FieldList(FormField(SupplierInvoiceEditLineForm), min_entries=0)


class SupplierPaymentForm(FlaskForm):
    """Enhanced form for recording supplier payments - ALL EXISTING FIELDS PRESERVED + NEW FIELDS ADDED"""
    
    # ===================================================================
    # EXISTING FIELDS (PRESERVED AS-IS)
    # ===================================================================
    
    # === BASIC PAYMENT INFORMATION (EXISTING) ===
    supplier_id = SelectField('Supplier', 
                             validators=[DataRequired()], 
                             choices=[('', 'Select Supplier')],
                             coerce=str)  # 🔧 CRITICAL FIX
    
    invoice_id = SelectField('Invoice (Optional)', 
                            validators=[Optional()], 
                            choices=[('', 'Select Invoice (Optional)')],
                            coerce=str)  # 🔧 CRITICAL FIX
    
    # === BRANCH SELECTION (EXISTING) ===
    branch_id = SelectField('Branch', 
                           validators=[DataRequired()], 
                           choices=[('', 'Select Branch')],
                           coerce=str)  # 🔧 CRITICAL FIX
    
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=date.today)
    amount = DecimalField('Payment Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than zero')
    ])
    
    # === PAYMENT METHOD (EXISTING) ===
    payment_method = SelectField('Payment Method', validators=[Optional()],
                                choices=[
                                    ('', 'Select Payment Method'),
                                    ('cash', 'Cash'),
                                    ('cheque', 'Cheque'),
                                    ('bank_transfer', 'Bank Transfer'),
                                    ('upi', 'UPI'),
                                    ('mixed', 'Multiple Methods')
                                ],coerce=str)  # 🔧 CRITICAL FIX
    
    # === MULTI-METHOD AMOUNTS (EXISTING) ===
    cash_amount = DecimalField('Cash Amount', validators=[Optional()], default=0)
    cheque_amount = DecimalField('Cheque Amount', validators=[Optional()], default=0)
    bank_transfer_amount = DecimalField('Bank Transfer Amount', validators=[Optional()], default=0)
    upi_amount = DecimalField('UPI Amount', validators=[Optional()], default=0)
    
    # === CHEQUE DETAILS (EXISTING) ===
    cheque_number = StringField('Cheque Number', validators=[Optional()])
    cheque_date = DateField('Cheque Date', validators=[Optional()])
    cheque_bank = StringField('Cheque Bank', validators=[Optional()])
    cheque_branch = StringField('Bank Branch', validators=[Optional()])
    
    # === BANK TRANSFER DETAILS (EXISTING) ===
    bank_name = StringField('Bank Name', validators=[Optional()])
    bank_branch = StringField('Bank Branch', validators=[Optional()])
    account_number_last4 = StringField('Account Last 4 Digits', validators=[
        Optional(),
        Length(max=4, message='Maximum 4 digits')
    ])
    bank_reference_number = StringField('Bank Reference', validators=[Optional()])
    ifsc_code = StringField('IFSC Code', validators=[Optional()])
    transfer_mode = SelectField('Transfer Mode', validators=[Optional()],
                               choices=[
                                   ('', 'Select Mode'),
                                   ('neft', 'NEFT'),
                                   ('rtgs', 'RTGS'),
                                   ('imps', 'IMPS'),
                                   ('swift', 'SWIFT')
                               ])
    
    # === UPI DETAILS (EXISTING) ===
    upi_id = StringField('UPI ID', validators=[Optional()])
    upi_transaction_id = StringField('UPI Transaction ID', validators=[Optional()])
    upi_reference_id = StringField('UPI Reference', validators=[Optional()])
    
    # === CURRENCY (EXISTING) ===
    currency_code = SelectField('Currency', 
                               validators=[DataRequired()], 
                               default='INR',
                               choices=[
                                   ('INR', 'INR'),
                                   ('USD', 'USD'),
                                   ('EUR', 'EUR')
                               ],
                               coerce=str)  # 🔧 CRITICAL FIX
    exchange_rate = DecimalField('Exchange Rate', validators=[DataRequired()], default=1.0)
    
    # === BASIC INFO (EXISTING) ===
    reference_no = StringField('Reference Number', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    # === WORKFLOW (EXISTING) ===
    requires_approval = BooleanField('Requires Approval', default=False)
    
    # === DOCUMENT UPLOAD (EXISTING) ===
    receipt_document = FileField('Receipt/Proof', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Only JPG, PNG, PDF allowed')
    ])
    
    bank_statement = FileField('Bank Statement', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Only JPG, PNG, PDF allowed')
    ])
    
    # === TDS (EXISTING) ===
    tds_applicable = BooleanField('TDS Applicable', default=False)
    tds_rate = DecimalField('TDS Rate (%)', validators=[Optional()], default=0)
    tds_amount = DecimalField('TDS Amount', validators=[Optional()], default=0)
    tds_reference = StringField('TDS Reference', validators=[Optional()])
    
    # === RECONCILIATION (EXISTING) ===
    mark_reconciled = BooleanField('Mark as Reconciled', default=False)
    bank_statement_date = DateField('Bank Statement Date', validators=[Optional()])
    bank_statement_reference = StringField('Bank Statement Reference', validators=[Optional()])
    reconciliation_notes = TextAreaField('Reconciliation Notes', validators=[Optional()])
    
    # === NOTIFICATION (EXISTING) ===
    notify_supplier = BooleanField('Notify Supplier', default=True)
    notification_method = SelectField('Notification Method', validators=[Optional()],
                                    choices=[
                                        ('email', 'Email'),
                                        ('sms', 'SMS'),
                                        ('portal', 'Portal'),
                                        ('none', 'None')
                                    ], default='email')
    
    # === HIDDEN GATEWAY FIELDS (EXISTING - Future) ===
    payment_category = HiddenField('Category', default='manual')
    payment_source = HiddenField('Source', default='internal')
    gateway_payment_id = HiddenField('Gateway Payment ID')
    gateway_order_id = HiddenField('Gateway Order ID')
    gateway_transaction_id = HiddenField('Gateway Transaction ID')
    
    # ===================================================================
    # NEW FIELDS (ADDED FOR ENHANCED FUNCTIONALITY)
    # ===================================================================
    
    # === NEW: ENHANCED BANK ACCOUNT DETAILS ===
    bank_account_name = StringField('Account Holder Name', validators=[
        Optional(), 
        Length(max=100, message='Account name must be less than 100 characters')
    ])
    
    # === NEW: ENHANCED UPI SUPPORT ===
    upi_app_name = SelectField('UPI App', validators=[Optional()], choices=[
        ('', 'Select UPI App'),
        ('gpay', 'Google Pay'),
        ('phonepe', 'PhonePe'),
        ('paytm', 'Paytm'),
        ('bhim', 'BHIM UPI'),
        ('amazonpay', 'Amazon Pay'),
        ('mobikwik', 'MobiKwik'),
        ('freecharge', 'FreeCharge'),
        ('other', 'Other')
    ],coerce=str)  # 🔧 CRITICAL FIX
    
    # === NEW: ADDITIONAL DOCUMENT TYPES ===
    authorization_document = FileField('Authorization Document', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Only JPG, PNG, PDF allowed')
    ])
    
    # === NEW: ENHANCED TDS FIELDS ===
    tds_section = StringField('TDS Section', validators=[Optional(), Length(max=10)])
    tds_certificate_number = StringField('TDS Certificate Number', validators=[Optional(), Length(max=50)])
    tds_deduction_date = DateField('TDS Deduction Date', validators=[Optional()])
    
    # === NEW: PROCESSING FIELDS ===
    processing_fee = DecimalField('Processing Fee', validators=[Optional()], default=0)
    
    # ===================================================================
    # ENHANCED VALIDATION (EXISTING + NEW)
    # ===================================================================
    
    def validate(self, extra_validators=None):
        """Enhanced validation with all existing rules + new multi-method rules"""
        if not super().validate(extra_validators):
            return False
        
        # === EXISTING VALIDATION: Multi-method amount validation ===
        method_total = (
            (self.cash_amount.data or 0) +
            (self.cheque_amount.data or 0) +
            (self.bank_transfer_amount.data or 0) +
            (self.upi_amount.data or 0)
        )
        
        # Allow either traditional single-method or multi-method
        if method_total > 0:
            if abs(float(self.amount.data) - float(method_total)) > 0.01:
                self.amount.errors.append(
                    f'Total amount ({self.amount.data}) must equal sum of payment methods ({method_total})'
                )
                return False
        
        # === EXISTING VALIDATION: Method-specific validations ===
        
        # Cheque validation (existing)
        if self.cheque_amount.data and self.cheque_amount.data > 0:
            if not self.cheque_number.data:
                self.cheque_number.errors.append('Cheque number required when cheque amount specified')
                return False
            if not self.cheque_date.data:
                self.cheque_date.errors.append('Cheque date required when cheque amount specified')
                return False
            if not self.cheque_bank.data:
                self.cheque_bank.errors.append('Cheque bank required when cheque amount specified')
                return False
        
        # Bank transfer validation (existing)
        if self.bank_transfer_amount.data and self.bank_transfer_amount.data > 0:
            if not self.bank_reference_number.data:
                self.bank_reference_number.errors.append('Bank reference required for transfers')
                return False
        
        # UPI validation (existing + enhanced)
        if self.upi_amount.data and self.upi_amount.data > 0:
            if not self.upi_transaction_id.data:
                self.upi_transaction_id.errors.append('UPI transaction ID required')
                return False
            # NEW: UPI app validation
            if not self.upi_app_name.data:
                self.upi_app_name.errors.append('UPI app selection required for UPI payments')
                return False
        
        # === NEW VALIDATION: Enhanced bank account validation ===
        if self.bank_transfer_amount.data and self.bank_transfer_amount.data > 10000:
            if not self.bank_account_name.data:
                self.bank_account_name.errors.append('Account holder name required for transfers above  Rs.10,000')
                return False
        
        # === NEW VALIDATION: TDS validation ===
        if self.tds_applicable.data:
            if not self.tds_rate.data or self.tds_rate.data <= 0:
                self.tds_rate.errors.append('TDS rate required when TDS is applicable')
                return False
            if not self.tds_amount.data or self.tds_amount.data <= 0:
                self.tds_amount.errors.append('TDS amount required when TDS is applicable')
                return False
        
        # === NEW VALIDATION: Processing fee validation ===
        if self.processing_fee.data and self.processing_fee.data < 0:
            self.processing_fee.errors.append('Processing fee cannot be negative')
            return False
        
        # === EXISTING VALIDATION: File size validation (enhanced) ===
        for file_field in [self.receipt_document, self.bank_statement, self.authorization_document]:
            if file_field.data:
                # Note: Actual file size validation typically done in view/controller
                # This is just a placeholder for form-level validation
                pass
        
        return True
    
    # ===================================================================
    # HELPER METHODS (NEW)
    # ===================================================================
    
    def get_payment_method_summary(self):
        """Get summary of payment methods used"""
        methods = []
        if self.cash_amount.data and self.cash_amount.data > 0:
            methods.append(f"Cash:  Rs.{self.cash_amount.data}")
        if self.cheque_amount.data and self.cheque_amount.data > 0:
            methods.append(f"Cheque:  Rs.{self.cheque_amount.data}")
        if self.bank_transfer_amount.data and self.bank_transfer_amount.data > 0:
            methods.append(f"Bank Transfer:  Rs.{self.bank_transfer_amount.data}")
        if self.upi_amount.data and self.upi_amount.data > 0:
            methods.append(f"UPI:  Rs.{self.upi_amount.data}")
        
        return "; ".join(methods) if methods else "Single method payment"
    
    def requires_documents(self):
        """Check if payment requires supporting documents"""
        # High value payments require documents
        if self.amount.data and self.amount.data > 50000:
            return True
        
        # Cheque payments require documents
        if self.cheque_amount.data and self.cheque_amount.data > 0:
            return True
        
        # Bank transfers above certain amount require documents
        if self.bank_transfer_amount.data and self.bank_transfer_amount.data > 10000:
            return True
        
        return False
    
    def get_approval_level_required(self):
        """Determine approval level required for this payment"""
        if not self.amount.data:
            return 'none'
        
        amount = float(self.amount.data)
        
        if amount <= 5000:
            return 'auto_approved'
        elif amount <= 50000:
            return 'level_1'
        else:
            return 'level_2'


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
                                      ('others', 'Others')
                                  ])
    gst_number = StringField('GSTIN', validators=[Optional()])
    status = SelectField('Status', validators=[Optional()],
                        choices=[
                            ('active', 'Active'),
                            ('inactive', 'Inactive'),
                            ('blacklisted', 'Blacklisted'),
                            ('all', 'All')
                        ], default='active')

    # NEW: Branch filter (optional)
    branch_id = SelectField('Branch', validators=[Optional()],
                           choices=[('', 'All Branches')])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate branch choices
        try:
            from flask_login import current_user
            if current_user and hasattr(current_user, 'hospital_id'):
                populate_branch_choices_for_user(self.branch_id, current_user, required=False)
        except Exception:
            self.branch_id.choices = [('', 'All Branches')]

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
    
    # NEW: Branch filter (optional)
    branch_id = SelectField('Branch', validators=[Optional()],
                           choices=[('', 'All Branches')])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate branch choices
        try:
            from flask_login import current_user
            if current_user and hasattr(current_user, 'hospital_id'):
                populate_branch_choices_for_user(self.branch_id, current_user, required=False)
        except Exception:
            self.branch_id.choices = [('', 'All Branches')]

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
    
    # NEW: Branch filter (optional)
    branch_id = SelectField('Branch', validators=[Optional()],
                           choices=[('', 'All Branches')])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate branch choices
        try:
            from flask_login import current_user
            if current_user and hasattr(current_user, 'hospital_id'):
                populate_branch_choices_for_user(self.branch_id, current_user, required=False)
        except Exception:
            self.branch_id.choices = [('', 'All Branches')]

    def validate_end_date(self, field):
        """Validate that end_date is after start_date if both are provided."""
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('End Date must be after Start Date')


class SupplierReturnForm(FlaskForm):
    """Form for supplier returns."""
    
    return_id = HiddenField()
    supplier_id = SelectField('Supplier', validators=[DataRequired()])
    invoice_id = SelectField('Original Invoice', validators=[DataRequired()])
    
    return_date = DateField('Return Date', format='%Y-%m-%d', validators=[DataRequired()], 
                          default=date.today)
    return_number = StringField('Return Number', validators=[DataRequired(), Length(max=50)])
    
    # Return items (will be dynamically handled like invoice items)
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
    batch_numbers = HiddenField('Batch Numbers')
    
    # Return reason
    return_reason = SelectField('Return Reason',
                              choices=[
                                  ('damaged', 'Damaged Goods'),
                                  ('expired', 'Expired/Near Expiry'),
                                  ('quality', 'Quality Issues'),
                                  ('wrong_item', 'Wrong Item Delivered'),
                                  ('excess', 'Excess Delivery'),
                                  ('other', 'Other')
                              ],
                              validators=[DataRequired()])
    
    remarks = TextAreaField('Additional Remarks', validators=[Optional(), Length(max=500)])

class SupplierInvoiceCancelForm(FlaskForm):
    """Form for canceling a supplier invoice."""
    cancellation_reason = TextAreaField('Reason for Cancellation', 
                                        validators=[DataRequired(message="Cancellation reason is required")])
    submit = SubmitField('Confirm Cancellation')  # Add this line if missing

class PurchaseOrderCancelForm(FlaskForm):
    """Form for cancelling a purchase order"""
    cancel_reason = TextAreaField(
        'Cancellation Reason', 
        validators=[
            DataRequired(message="Cancellation reason is required"),
            Length(min=10, max=500, message="Reason must be between 10 and 500 characters")
        ],
        render_kw={
            "rows": 4,
            "placeholder": "Please provide a detailed reason for cancelling this purchase order..."
        }
    )
    submit = SubmitField('Cancel Purchase Order')

class PaymentApprovalForm(FlaskForm):
    """Form for approving or rejecting payments"""
    action = SelectField('Action', validators=[DataRequired()], choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('request_more_info', 'Request More Information')
    ])
    approval_notes = TextAreaField('Approval Notes', validators=[
        DataRequired(),
        Length(min=5, max=500, message='Notes must be between 5 and 500 characters')
    ])
    submit = SubmitField('Submit Approval')

# ADD this new form class:
class DocumentUploadForm(FlaskForm):
    """Form for uploading payment documents"""
    document_type = SelectField('Document Type', validators=[DataRequired()], choices=[
        ('receipt', 'Payment Receipt'),
        ('bank_statement', 'Bank Statement'),
        ('authorization', 'Authorization Letter'),
        ('invoice_copy', 'Invoice Copy'),
        ('cheque_image', 'Cheque Image'),
        ('other', 'Other Document')
    ])
    file = FileField('Select File', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF, JPG, PNG files allowed')
    ])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    required_for_approval = BooleanField('Required for Approval')
    submit = SubmitField('Upload Document')
    
    def validate_file(self, field):
        """Enhanced file validation"""
        if not field.data:
            raise ValidationError('Please select a file to upload')
        
        filename = field.data.filename
        if not filename:
            raise ValidationError('Invalid file selected')
        
        # Check file extension
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
        if file_ext not in allowed_extensions:
            raise ValidationError(f'File type .{file_ext} not allowed. Use: {", ".join(allowed_extensions)}')

# ADD this new form class:
class PaymentSearchForm(FlaskForm):
    """Form for searching and filtering payments"""
    supplier_id = SelectField('Supplier', validators=[Optional()], choices=[('', 'All Suppliers')])
    branch_id = SelectField('Branch', validators=[Optional()], choices=[('', 'All Branches')])
    workflow_status = SelectField('Status', validators=[Optional()], choices=[
        ('', 'All Statuses'),
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ])
    payment_method = SelectField('Payment Method', validators=[Optional()], choices=[
        ('', 'All Methods'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('mixed', 'Multiple Methods')
    ])
    start_date = DateField('From Date', validators=[Optional()])
    end_date = DateField('To Date', validators=[Optional()])
    min_amount = DecimalField('Minimum Amount', validators=[Optional(), NumberRange(min=0)])
    max_amount = DecimalField('Maximum Amount', validators=[Optional(), NumberRange(min=0)])
    
    def validate_end_date(self, field):
        """Ensure end date is after start date"""
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('End date must be after start date')
    
    def validate_max_amount(self, field):
        """Ensure max amount is greater than min amount"""
        if (field.data and self.min_amount.data and 
            field.data < self.min_amount.data):
            raise ValidationError('Maximum amount must be greater than minimum amount')
        

class SupplierCreditNoteForm(FlaskForm):
    """
    Phase 1: Simple credit note form
    Minimal implementation with core functionality only
    """
    
    # Hidden fields for context
    payment_id = HiddenField('Payment ID', validators=[DataRequired()])
    supplier_id = HiddenField('Supplier ID')
    branch_id = HiddenField('Branch ID')
    
    # Credit note details
    credit_note_number = StringField(
        'Credit Note Number',
        validators=[DataRequired(message="Credit note number is required")],
        render_kw={'readonly': True, 'class': 'form-control readonly-field'}
    )
    
    credit_note_date = DateField(
        'Credit Note Date',
        validators=[DataRequired(message="Credit note date is required")],
        default=date.today
    )
    
    credit_amount = DecimalField(
        'Credit Amount (₹)',
        validators=[
            DataRequired(message="Credit amount is required"),
            NumberRange(min=0.01, message="Credit amount must be greater than 0")
        ],
        places=2
    )
    
    reason_code = SelectField(
        'Reason',
        validators=[DataRequired(message="Please select a reason")],
        choices=[]  # Will be populated dynamically
    )
    
    credit_reason = TextAreaField(
        'Detailed Reason',
        validators=[
            DataRequired(message="Please provide detailed reason"),
            Length(min=10, max=500, message="Reason must be between 10 and 500 characters")
        ],
        render_kw={'rows': 4, 'placeholder': 'Please explain the reason for this credit note...'}
    )
    
    # Display fields (readonly)
    payment_reference = StringField(
        'Payment Reference',
        render_kw={'readonly': True, 'class': 'form-control readonly-field'}
    )
    
    supplier_name = StringField(
        'Supplier Name', 
        render_kw={'readonly': True, 'class': 'form-control readonly-field'}
    )
    
    # Form actions
    submit = SubmitField('Create Credit Note')
    cancel = SubmitField('Cancel', render_kw={'formnovalidate': True})
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate reason choices from configuration
        from app.utils.credit_note_utils import get_credit_note_reasons
        self.reason_code.choices = get_credit_note_reasons()
    
    def validate_credit_amount(self, field):
        """Custom validation for credit amount"""
        if field.data and field.data <= 0:
            raise ValidationError('Credit amount must be greater than zero')
    
    def validate_credit_note_date(self, field):
        """Custom validation for credit note date"""
        if field.data and field.data > date.today():
            raise ValidationError('Credit note date cannot be in the future')
    
    def validate_credit_reason(self, field):
        """Custom validation for detailed reason"""
        if self.reason_code.data == 'other' and field.data:
            if len(field.data.strip()) < 20:
                raise ValidationError('For "Other" reason, please provide at least 20 characters of explanation')