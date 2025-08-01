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
    supplier_id = SelectField('Supplier', validators=[DataRequired()])
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
    """Individual line item form for editing PO - FIXED validation"""
    medicine_id = HiddenField('Medicine ID')  # REMOVED DataRequired - template will validate
    medicine_name = StringField('Medicine', render_kw={'readonly': True})
    
    # FIXED: Remove validators to prevent validation errors
    quantity = DecimalField('Quantity', render_kw={'step': '0.01', 'min': '0'})
    pack_purchase_price = DecimalField('Rate', render_kw={'step': '0.01', 'min': '0'}) 
    pack_mrp = DecimalField('MRP', render_kw={'step': '0.01', 'min': '0'})
    
    units_per_pack = HiddenField('Units per Pack', default=1)
    discount_percent = DecimalField('Discount %', default=0, render_kw={'step': '0.1', 'min': '0', 'max': '100'})
    is_free_item = BooleanField('Free Item', default=False)
    hsn_code = HiddenField('HSN Code')
    gst_rate = HiddenField('GST Rate')

class PurchaseOrderEditForm(FlaskForm):
    """Centralized edit form for PO - FIXED optional fields"""
    # Header fields
    po_number = StringField('PO Number', render_kw={'readonly': True})
    supplier_id = SelectField('Supplier', validators=[DataRequired()])
    po_date = DateField('PO Date', validators=[DataRequired()])
    
    # FIXED: All optional fields - no validators
    expected_delivery_date = DateField('Expected Delivery')  
    quotation_id = StringField('Quotation ID')  
    quotation_date = DateField('Quotation Date')  # FIXED: No validators
    
    currency_code = SelectField('Currency', choices=[('INR', 'INR'), ('USD', 'USD')], default='INR')
    exchange_rate = DecimalField('Exchange Rate', default=1.0, validators=[NumberRange(min=0.000001)])
    notes = TextAreaField('Notes')
    
    # Line items - no min_entries to avoid validation issues
    line_items = FieldList(FormField(PurchaseOrderEditLineForm), min_entries=0)

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
    """Form for recording supplier payments - Simple field validation only"""
    
    # === BASIC PAYMENT INFORMATION ===
    supplier_id = HiddenField('Supplier ID', validators=[DataRequired()])
    invoice_id = HiddenField('Invoice ID')  # Optional
    
    # === BRANCH SELECTION ===
    branch_id = SelectField('Branch', validators=[DataRequired()], 
                           choices=[('', 'Select Branch')])
    
    payment_date = DateField('Payment Date', validators=[DataRequired()], default=date.today)
    amount = DecimalField('Payment Amount', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than zero')
    ])
    
    # === PAYMENT METHOD ===
    payment_method = SelectField('Payment Method', validators=[DataRequired()],
                                choices=[
                                    ('', 'Select Payment Method'),
                                    ('cash', 'Cash'),
                                    ('cheque', 'Cheque'),
                                    ('bank_transfer', 'Bank Transfer'),
                                    ('upi', 'UPI'),
                                    ('mixed', 'Multiple Methods')
                                ])
    
    # === MULTI-METHOD AMOUNTS ===
    cash_amount = DecimalField('Cash Amount', validators=[Optional()], default=0)
    cheque_amount = DecimalField('Cheque Amount', validators=[Optional()], default=0)
    bank_transfer_amount = DecimalField('Bank Transfer Amount', validators=[Optional()], default=0)
    upi_amount = DecimalField('UPI Amount', validators=[Optional()], default=0)
    
    # === CHEQUE DETAILS ===
    cheque_number = StringField('Cheque Number', validators=[Optional()])
    cheque_date = DateField('Cheque Date', validators=[Optional()])
    cheque_bank = StringField('Cheque Bank', validators=[Optional()])
    cheque_branch = StringField('Bank Branch', validators=[Optional()])
    
    # === BANK TRANSFER DETAILS ===
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
    
    # === UPI DETAILS ===
    upi_id = StringField('UPI ID', validators=[Optional()])
    upi_transaction_id = StringField('UPI Transaction ID', validators=[Optional()])
    upi_reference_id = StringField('UPI Reference', validators=[Optional()])
    
    # === CURRENCY ===
    currency_code = SelectField('Currency', validators=[DataRequired()], default='INR',
                               choices=[
                                   ('INR', 'INR'),
                                   ('USD', 'USD'),
                                   ('EUR', 'EUR'),
                                   ('GBP', 'GBP')
                               ])
    exchange_rate = DecimalField('Exchange Rate', validators=[DataRequired()], default=1.0)
    
    # === BASIC INFO ===
    reference_no = StringField('Reference Number', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    # === WORKFLOW ===
    requires_approval = BooleanField('Requires Approval', default=False)
    
    # === DOCUMENT UPLOAD ===
    receipt_document = FileField('Receipt/Proof', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Only JPG, PNG, PDF allowed')
    ])
    
    bank_statement = FileField('Bank Statement', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Only JPG, PNG, PDF allowed')
    ])
    
    # === TDS ===
    tds_applicable = BooleanField('TDS Applicable', default=False)
    tds_rate = DecimalField('TDS Rate (%)', validators=[Optional()], default=0)
    tds_amount = DecimalField('TDS Amount', validators=[Optional()], default=0)
    tds_reference = StringField('TDS Reference', validators=[Optional()])
    
    # === RECONCILIATION ===
    mark_reconciled = BooleanField('Mark as Reconciled', default=False)
    bank_statement_date = DateField('Bank Statement Date', validators=[Optional()])
    bank_statement_reference = StringField('Bank Statement Reference', validators=[Optional()])
    reconciliation_notes = TextAreaField('Reconciliation Notes', validators=[Optional()])
    
    # === NOTIFICATION ===
    notify_supplier = BooleanField('Notify Supplier', default=True)
    notification_method = SelectField('Notification Method', validators=[Optional()],
                                    choices=[
                                        ('email', 'Email'),
                                        ('sms', 'SMS'),
                                        ('portal', 'Portal'),
                                        ('none', 'None')
                                    ], default='email')
    
    # === HIDDEN GATEWAY FIELDS (Future) ===
    payment_category = HiddenField('Category', default='manual')
    payment_source = HiddenField('Source', default='internal')
    gateway_payment_id = HiddenField('Gateway Payment ID')
    gateway_order_id = HiddenField('Gateway Order ID')
    gateway_transaction_id = HiddenField('Gateway Transaction ID')


# === HELPER FUNCTIONS ===
def populate_branch_choices(form, current_user):
    """Populate branch choices for the form"""
    try:
        from app.services.database_service import get_db_session
        from app.models.master import Branch
        
        with get_db_session(read_only=True) as session:
            branches = session.query(Branch).filter_by(
                hospital_id=current_user.hospital_id,
                is_active=True
            ).order_by(Branch.branch_name).all()
            
            choices = [('', 'Select Branch')]
            for branch in branches:
                choices.append((str(branch.branch_id), f"{branch.branch_name} ({branch.branch_code})"))
            
            form.branch_id.choices = choices
        return True
        
    except Exception as e:
        form.branch_id.choices = [('', 'Error loading branches')]
        return False


def setup_payment_form(form, current_user):
    """Setup form with branch choices and defaults"""
    populate_branch_choices(form, current_user)
    
    # Set default branch if user has one
    try:
        from app.services.database_service import get_db_session
        from app.models.master import Staff
        
        if current_user.entity_type == 'staff':
            with get_db_session(read_only=True) as session:
                staff = session.query(Staff).filter_by(
                    staff_id=current_user.entity_id
                ).first()
                
                if staff and staff.branch_id and not form.branch_id.data:
                    form.branch_id.data = str(staff.branch_id)
                    
    except Exception:
        pass  # Ignore errors, just don't set default

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