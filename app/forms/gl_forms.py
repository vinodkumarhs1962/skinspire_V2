from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, SelectField, HiddenField, IntegerField, BooleanField
from wtforms.validators import DataRequired, Optional, NumberRange, ValidationError
from datetime import date

class GLTransactionFilterForm(FlaskForm):
    """Form for filtering GL transactions."""
    
    transaction_type = SelectField('Transaction Type', validators=[Optional()],
                                  choices=[
                                      ('', 'All'),
                                      ('invoice', 'Sales Invoice'),
                                      ('payment', 'Customer Payment'),
                                      ('supplier_invoice', 'Supplier Invoice'),
                                      ('supplier_payment', 'Supplier Payment'),
                                      ('adjustment', 'Adjustment Entry'),
                                      ('journal', 'Journal Entry')
                                  ])
    
    reference_id = StringField('Reference ID', validators=[Optional()])
    
    start_date = DateField('From Date', validators=[Optional()])
    end_date = DateField('To Date', validators=[Optional()])
    
    min_amount = DecimalField('Minimum Amount', validators=[Optional()])
    max_amount = DecimalField('Maximum Amount', validators=[Optional()])
    
    account_id = SelectField('Account', validators=[Optional()])
    
    reconciliation_status = SelectField('Reconciliation Status', validators=[Optional()],
                                      choices=[
                                          ('', 'All'),
                                          ('none', 'Not Applicable'),
                                          ('pending', 'Pending'),
                                          ('reconciled', 'Reconciled')
                                      ])
    
    def validate_end_date(self, field):
        """Validate that end_date is after start_date if both are provided."""
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('End Date must be after Start Date')
    
    def validate_max_amount(self, field):
        """Validate that max_amount is greater than min_amount if both are provided."""
        if field.data and self.min_amount.data and field.data < self.min_amount.data:
            raise ValidationError('Maximum amount must be greater than minimum amount')

class GLReportForm(FlaskForm):
    """Form for generating financial reports."""
    
    report_type = SelectField('Report Type', validators=[DataRequired()],
                            choices=[
                                ('trial_balance', 'Trial Balance'),
                                ('profit_loss', 'Profit & Loss Statement'),
                                ('balance_sheet', 'Balance Sheet'),
                                ('cash_flow', 'Cash Flow Statement'),
                                ('account_ledger', 'Account Ledger')
                            ])
    
    start_date = DateField('From Date', validators=[DataRequired()], default=lambda: date(date.today().year, 4, 1))
    end_date = DateField('To Date', validators=[DataRequired()], default=date.today)
    
    account_id = SelectField('Account (for Account Ledger)', validators=[Optional()])
    
    comparative = SelectField('Comparative', validators=[Optional()],
                            choices=[
                                ('', 'None'),
                                ('previous_year', 'Previous Year'),
                                ('previous_quarter', 'Previous Quarter'),
                                ('previous_month', 'Previous Month')
                            ])
    
    def validate_end_date(self, field):
        """Validate that end_date is after start_date."""
        if field.data < self.start_date.data:
            raise ValidationError('End Date must be after Start Date')

class GSTReportForm(FlaskForm):
    """Form for generating GST reports."""
    
    report_type = SelectField('Report Type', validators=[DataRequired()],
                            choices=[
                                ('gstr1', 'GSTR-1 (Outward Supplies)'),
                                ('gstr2a', 'GSTR-2A (Inward Supplies)'),
                                ('gstr3b', 'GSTR-3B (Summary Return)'),
                                ('gst_summary', 'GST Summary'),
                                ('itc_report', 'Input Tax Credit Report'),
                                ('hsn_summary', 'HSN Summary')
                            ])
    
    month = IntegerField('Month', validators=[
        DataRequired(),
        NumberRange(min=1, max=12, message='Month must be between 1 and 12')
    ], default=date.today().month)
    
    year = IntegerField('Year', validators=[
        DataRequired(),
        NumberRange(min=2000, max=2100, message='Year must be between 2000 and 2100')
    ], default=date.today().year)
    
    export_format = SelectField('Export Format', validators=[Optional()],
                               choices=[
                                   ('html', 'HTML'),
                                   ('excel', 'Excel'),
                                   ('json', 'JSON')
                               ], default='html')
    
    include_cancelled = BooleanField('Include Cancelled Invoices', default=False)