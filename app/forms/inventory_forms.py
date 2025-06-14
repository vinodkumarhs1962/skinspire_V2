from flask_wtf import FlaskForm
from wtforms import StringField, DateField, DecimalField, SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError
from datetime import date

class OpeningStockForm(FlaskForm):
    """Form for recording opening stock."""
    
    medicine_id = HiddenField('Medicine ID', validators=[DataRequired()])
    medicine_name = StringField('Medicine Name', render_kw={'readonly': True})
    
    batch = StringField('Batch Number', validators=[
        DataRequired(),
        Length(min=1, max=20, message='Batch number must be between 1 and 20 characters')
    ])
    
    expiry_date = DateField('Expiry Date', validators=[DataRequired()])
    
    quantity = DecimalField('Quantity', validators=[
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
    
    location = StringField('Location', validators=[
        Optional(),
        Length(max=50, message='Location must be less than 50 characters')
    ])
    
    def validate_expiry_date(self, field):
        """Validate that expiry date is in the future."""
        if field.data and field.data <= date.today():
            raise ValidationError('Expiry date must be in the future')

class StockAdjustmentForm(FlaskForm):
    """Form for stock adjustments."""
    
    medicine_id = HiddenField('Medicine ID', validators=[DataRequired()])
    medicine_name = StringField('Medicine Name', render_kw={'readonly': True})
    
    batch = SelectField('Batch', validators=[DataRequired()])
    
    adjustment_type = SelectField('Adjustment Type', validators=[DataRequired()],
                                choices=[
                                    ('increase', 'Stock Increase'),
                                    ('decrease', 'Stock Decrease')
                                ])
    
    quantity = DecimalField('Quantity', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Quantity must be greater than zero')
    ])
    
    reason = SelectField('Reason', validators=[DataRequired()],
                        choices=[
                            ('physical_count', 'Physical Count Adjustment'),
                            ('damaged', 'Damaged Stock'),
                            ('expired', 'Expired Stock'),
                            ('transfer', 'Stock Transfer'),
                            ('correction', 'Data Correction'),
                            ('other', 'Other')
                        ])
    
    notes = TextAreaField('Notes', validators=[
        Optional(),
        Length(max=255, message='Notes must be less than 255 characters')
    ])
    
    location = StringField('Location', validators=[
        Optional(),
        Length(max=50, message='Location must be less than 50 characters')
    ])

class BatchManagementForm(FlaskForm):
    """Form for batch management and filtering."""
    
    medicine_id = SelectField('Medicine', validators=[Optional()])
    
    batch = StringField('Batch Number', validators=[
        Optional(),
        Length(max=20, message='Batch number must be less than 20 characters')
    ])
    
    expiry_from = DateField('Expiry From', validators=[Optional()])
    expiry_to = DateField('Expiry To', validators=[Optional()])
    
    location = StringField('Location', validators=[
        Optional(),
        Length(max=50, message='Location must be less than 50 characters')
    ])
    
    def validate_expiry_to(self, field):
        """Validate that expiry_to is after expiry_from if both are provided."""
        if field.data and self.expiry_from.data and field.data < self.expiry_from.data:
            raise ValidationError('Expiry To must be after Expiry From')

class InventoryFilterForm(FlaskForm):
    """Form for filtering inventory and stock movements."""
    
    medicine_id = SelectField('Medicine', validators=[Optional()])
    
    batch = StringField('Batch Number', validators=[
        Optional(),
        Length(max=20, message='Batch number must be less than 20 characters')
    ])
    
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    
    stock_type = SelectField('Transaction Type', validators=[Optional()],
                            choices=[
                                ('', 'All'),
                                ('opening_stock', 'Opening Stock'),
                                ('purchase', 'Purchase'),
                                ('sales', 'Sales'),
                                ('adjustment', 'Adjustment'),
                                ('consumption', 'Consumption'),
                                ('return', 'Return'),
                                ('transfer', 'Transfer')
                            ])
    
    location = StringField('Location', validators=[
        Optional(),
        Length(max=50, message='Location must be less than 50 characters')
    ])
    
    def validate_end_date(self, field):
        """Validate that end_date is after start_date if both are provided."""
        if field.data and self.start_date.data and field.data < self.start_date.data:
            raise ValidationError('End Date must be after Start Date')