# =============================================================================
# UNIVERSAL FORMS - INTEGRATED WITH EXISTING FORM PATTERNS
# Following SkinSpire HMS Existing Form Structure and Patterns
# =============================================================================

# =============================================================================
# FILE: app/forms/universal_forms.py
# PURPOSE: Universal form generation following your existing form patterns
# =============================================================================

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, DateField, DateTimeField,
    IntegerField, FloatField, BooleanField, HiddenField, validators
)
from wtforms.validators import DataRequired, Optional, Length, Email, ValidationError
from typing import Dict, Any, List, Type
from datetime import datetime

# Import your existing form patterns and validators
from app.utils.form_helpers import populate_supplier_choices, populate_branch_choices_for_user

# Import universal architecture components
from app.config.entity_configurations import EntityConfiguration, FieldType, FieldDefinition

class UniversalFormFieldFactory:
    """Factory for creating form fields based on field definitions"""
    
    @staticmethod
    def create_field(field_def: FieldDefinition) -> Type:
        """Create WTForms field based on field definition"""
        
        # Base arguments for all fields
        field_args = {
            'label': field_def.label,
            'description': field_def.help_text,
            'render_kw': {
                'class': f'form-input {field_def.css_classes}',
                'placeholder': field_def.placeholder or field_def.label
            }
        }
        
        # Add validators
        field_validators = []
        if field_def.required:
            field_validators.append(DataRequired(message=f'{field_def.label} is required'))
        else:
            field_validators.append(Optional())
            
        # Add field-specific validators
        for rule in field_def.validation_rules:
            validator = UniversalFormFieldFactory._get_validator(rule, field_def)
            if validator:
                field_validators.append(validator)
        
        field_args['validators'] = field_validators
        
        # Create field based on type
        if field_def.field_type == FieldType.TEXT:
            return StringField(**field_args)
            
        elif field_def.field_type == FieldType.TEXTAREA:
            field_args['render_kw']['rows'] = 4
            return TextAreaField(**field_args)
            
        elif field_def.field_type == FieldType.EMAIL:
            field_validators.append(Email(message='Please enter a valid email address'))
            field_args['validators'] = field_validators
            field_args['render_kw']['type'] = 'email'
            return StringField(**field_args)
            
        elif field_def.field_type == FieldType.PHONE:
            field_args['render_kw']['type'] = 'tel'
            return StringField(**field_args)
            
        elif field_def.field_type == FieldType.NUMBER:
            field_args['render_kw']['type'] = 'number'
            return IntegerField(**field_args)
            
        elif field_def.field_type == FieldType.AMOUNT:
            field_args['render_kw']['type'] = 'number'
            field_args['render_kw']['step'] = '0.01'
            field_args['render_kw']['min'] = '0'
            return FloatField(**field_args)
            
        elif field_def.field_type == FieldType.DATE:
            field_args['render_kw']['type'] = 'date'
            return DateField(**field_args)
            
        elif field_def.field_type == FieldType.DATETIME:
            field_args['render_kw']['type'] = 'datetime-local'
            return DateTimeField(**field_args)
            
        elif field_def.field_type == FieldType.BOOLEAN:
            field_args['render_kw']['class'] = 'form-checkbox'
            return BooleanField(**field_args)
            
        elif field_def.field_type == FieldType.SELECT:
            choices = [(opt['value'], opt['label']) for opt in field_def.options]
            if not field_def.required:
                choices.insert(0, ('', f'Select {field_def.label}'))
            field_args['choices'] = choices
            field_args['render_kw']['class'] = 'form-select'
            return SelectField(**field_args)
            
        elif field_def.field_type == FieldType.FOREIGN_KEY:
            # Dynamic choices will be populated based on related entity
            field_args['choices'] = [('', f'Select {field_def.label}')]
            field_args['render_kw']['class'] = 'form-select'
            field_args['render_kw']['data-entity'] = field_def.related_entity
            return SelectField(**field_args)
            
        # Healthcare-specific fields
        elif field_def.field_type == FieldType.PATIENT_MRN:
            field_args['render_kw']['class'] += ' font-mono'
            field_args['render_kw']['pattern'] = '[A-Z0-9]+'
            field_validators.append(Length(min=6, max=20, message='MRN must be 6-20 characters'))
            field_args['validators'] = field_validators
            return StringField(**field_args)
            
        elif field_def.field_type == FieldType.GST_NUMBER:
            field_args['render_kw']['class'] += ' font-mono'
            field_args['render_kw']['pattern'] = '[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}'
            field_args['render_kw']['maxlength'] = '15'
            field_validators.append(Length(min=15, max=15, message='GST number must be 15 characters'))
            field_args['validators'] = field_validators
            return StringField(**field_args)
            
        elif field_def.field_type == FieldType.PAN_NUMBER:
            field_args['render_kw']['class'] += ' font-mono uppercase'
            field_args['render_kw']['pattern'] = '[A-Z]{5}[0-9]{4}[A-Z]{1}'
            field_args['render_kw']['maxlength'] = '10'
            field_validators.append(Length(min=10, max=10, message='PAN number must be 10 characters'))
            field_args['validators'] = field_validators
            return StringField(**field_args)
            
        elif field_def.field_type == FieldType.HSN_CODE:
            field_args['render_kw']['class'] += ' font-mono'
            field_args['render_kw']['pattern'] = '[0-9]+'
            return StringField(**field_args)
            
        elif field_def.field_type == FieldType.INVOICE_NUMBER:
            field_args['render_kw']['class'] += ' font-mono'
            return StringField(**field_args)
            
        # Default to text field
        else:
            return StringField(**field_args)
    
    @staticmethod
    def _get_validator(rule: str, field_def: FieldDefinition):
        """Get validator based on rule name"""
        if rule == 'email':
            return Email()
        elif rule.startswith('length:'):
            # Example: length:5,50
            parts = rule.split(':')[1].split(',')
            min_len = int(parts[0]) if parts[0] else 0
            max_len = int(parts[1]) if len(parts) > 1 and parts[1] else None
            return Length(min=min_len, max=max_len)
        elif rule == 'gst_validation':
            return UniversalFormValidators.validate_gst
        elif rule == 'pan_validation':
            return UniversalFormValidators.validate_pan
        elif rule == 'mrn_validation':
            return UniversalFormValidators.validate_mrn
        
        return None

class UniversalFormValidators:
    """Custom validators for healthcare-specific fields"""
    
    @staticmethod
    def validate_gst(form, field):
        """Validate GST number format"""
        if field.data:
            gst = field.data.upper()
            if len(gst) != 15:
                raise ValidationError('GST number must be 15 characters long')
            
            # GST format: 2 digits + 5 letters + 4 digits + 1 letter + 1 digit/letter + Z + 1 digit/letter
            import re
            pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z]{1}[0-9A-Z]{1}$'
            if not re.match(pattern, gst):
                raise ValidationError('Invalid GST number format')
    
    @staticmethod
    def validate_pan(form, field):
        """Validate PAN number format"""
        if field.data:
            pan = field.data.upper()
            if len(pan) != 10:
                raise ValidationError('PAN number must be 10 characters long')
            
            # PAN format: 5 letters + 4 digits + 1 letter
            import re
            pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
            if not re.match(pattern, pan):
                raise ValidationError('Invalid PAN number format')
    
    @staticmethod
    def validate_mrn(form, field):
        """Validate MRN format"""
        if field.data:
            mrn = field.data.upper()
            if len(mrn) < 6 or len(mrn) > 20:
                raise ValidationError('MRN must be between 6 and 20 characters')
            
            # MRN should be alphanumeric
            if not mrn.isalnum():
                raise ValidationError('MRN should contain only letters and numbers')

class UniversalSearchForm(FlaskForm):
    """Universal search form following your existing search form patterns"""
    
    def __init__(self, entity_config: EntityConfiguration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = entity_config
        
        # Add search field
        self.search = StringField(
            'Search',
            render_kw={
                'class': 'form-input',
                'placeholder': f'Search {", ".join(entity_config.default_search_fields)}...'
            }
        )
        
        # Add filterable fields dynamically
        for field_def in entity_config.fields:
            if field_def.filterable:
                self._add_filter_field(field_def)
        
        # Add date range fields if any date fields exist
        date_fields = [f for f in entity_config.fields if f.field_type == FieldType.DATE and f.filterable]
        if date_fields:
            self.start_date = DateField(
                'Start Date',
                validators=[Optional()],
                render_kw={'class': 'form-input', 'type': 'date'}
            )
            self.end_date = DateField(
                'End Date', 
                validators=[Optional()],
                render_kw={'class': 'form-input', 'type': 'date'}
            )
            self.date_preset = SelectField(
                'Date Range',
                choices=[
                    ('', 'All Dates'),
                    ('today', 'Today'),
                    ('this_week', 'This Week'),
                    ('this_month', 'This Month'),
                    ('custom', 'Custom Range')
                ],
                render_kw={'class': 'form-select'}
            )
    
    def _add_filter_field(self, field_def: FieldDefinition):
        """Add filter field to form"""
        field_name = f'filter_{field_def.name}'
        
        if field_def.field_type == FieldType.SELECT or field_def.field_type == FieldType.STATUS_BADGE:
            choices = [('', f'All {field_def.label}')]
            choices.extend([(opt['value'], opt['label']) for opt in field_def.options])
            
            filter_field = SelectField(
                field_def.label,
                choices=choices,
                render_kw={'class': 'form-select'}
            )
        elif field_def.field_type == FieldType.FOREIGN_KEY:
            filter_field = SelectField(
                field_def.label,
                choices=[('', f'All {field_def.label}')],
                render_kw={
                    'class': 'form-select',
                    'data-entity': field_def.related_entity
                }
            )
        else:
            filter_field = StringField(
                field_def.label,
                render_kw={
                    'class': 'form-input',
                    'placeholder': f'Filter by {field_def.label.lower()}'
                }
            )
        
        setattr(self, field_name, filter_field)

class UniversalEntityForm(FlaskForm):
    """Universal entity form following your existing entity form patterns"""
    
    def __init__(self, entity_config: EntityConfiguration, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = entity_config
        
        # Add fields dynamically based on configuration
        for field_def in entity_config.fields:
            if field_def.show_in_form if hasattr(field_def, 'show_in_form') else True:
                form_field = UniversalFormFieldFactory.create_field(field_def)
                setattr(self, field_def.name, form_field)
        
        # Populate dynamic choices for foreign key fields
        self._populate_foreign_key_choices()
    
    def _populate_foreign_key_choices(self):
        """Populate choices for foreign key fields using your existing helpers"""
        from flask_login import current_user
        
        for field_def in self.config.fields:
            if field_def.field_type == FieldType.FOREIGN_KEY and hasattr(self, field_def.name):
                form_field = getattr(self, field_def.name)
                
                try:
                    if field_def.related_entity == 'suppliers':
                        # Use your existing supplier choice helper
                        choices = populate_supplier_choices(current_user.hospital_id)
                        form_field.choices = [('', f'Select {field_def.label}')] + choices
                    
                    elif field_def.related_entity == 'branches':
                        # Use your existing branch choice helper
                        choices = populate_branch_choices_for_user(current_user.user_id, current_user.hospital_id)
                        form_field.choices = [('', f'Select {field_def.label}')] + choices
                    
                    # Add more entity types as needed
                    elif field_def.related_entity == 'patients':
                        form_field.choices = self._get_patient_choices()
                    
                    elif field_def.related_entity == 'medicines':
                        form_field.choices = self._get_medicine_choices()
                        
                except Exception as e:
                    from flask import current_app
                    current_app.logger.warning(f"Error populating choices for {field_def.name}: {str(e)}")
                    form_field.choices = [('', f'Select {field_def.label}')]
    
    def _get_patient_choices(self):
        """Get patient choices for dropdown"""
        try:
            from flask_login import current_user
            from app.services.database_service import get_db_session
            from app.models.master import Patient
            
            with get_db_session() as session:
                patients = session.query(Patient).filter(
                    Patient.hospital_id == current_user.hospital_id,
                    Patient.patient_status == 'active'
                ).order_by(Patient.full_name).limit(100).all()
                
                return [(str(patient.patient_id), f"{patient.full_name} ({patient.mrn})") 
                       for patient in patients]
        except Exception:
            return []
    
    def _get_medicine_choices(self):
        """Get medicine choices for dropdown"""
        try:
            from flask_login import current_user
            from app.services.database_service import get_db_session
            from app.models.master import Medicine
            
            with get_db_session() as session:
                medicines = session.query(Medicine).filter(
                    Medicine.hospital_id == current_user.hospital_id,
                    Medicine.medicine_status == 'active'
                ).order_by(Medicine.medicine_name).limit(100).all()
                
                return [(str(medicine.medicine_id), medicine.medicine_name) 
                       for medicine in medicines]
        except Exception:
            return []

# =============================================================================
# SPECIALIZED FORMS - Following your existing specialized form patterns
# =============================================================================

class PatientSearchForm(UniversalSearchForm):
    """Patient-specific search form with additional healthcare fields"""
    
    def __init__(self, *args, **kwargs):
        from app.core.entity_registry import EntityConfigurationRegistry
        from app.config.entity_configurations import EntityType
        
        config = EntityConfigurationRegistry.get_config(EntityType.PATIENT)
        super().__init__(config, *args, **kwargs)
        
        # Add patient-specific search fields
        self.mrn = StringField(
            'MRN',
            render_kw={
                'class': 'form-input font-mono',
                'placeholder': 'Patient MRN'
            }
        )
        
        self.age_from = IntegerField(
            'Age From',
            validators=[Optional()],
            render_kw={'class': 'form-input', 'type': 'number', 'min': '0', 'max': '150'}
        )
        
        self.age_to = IntegerField(
            'Age To',
            validators=[Optional()],
            render_kw={'class': 'form-input', 'type': 'number', 'min': '0', 'max': '150'}
        )

class SupplierInvoiceSearchForm(UniversalSearchForm):
    """Supplier invoice-specific search form"""
    
    def __init__(self, *args, **kwargs):
        from app.core.entity_registry import EntityConfigurationRegistry
        from app.config.entity_configurations import EntityType
        
        config = EntityConfigurationRegistry.get_config(EntityType.SUPPLIER_INVOICE)
        super().__init__(config, *args, **kwargs)
        
        # Add supplier invoice-specific fields
        self.invoice_number = StringField(
            'Invoice Number',
            render_kw={
                'class': 'form-input font-mono',
                'placeholder': 'Invoice Number'
            }
        )
        
        self.po_number = StringField(
            'PO Number',
            render_kw={
                'class': 'form-input',
                'placeholder': 'Purchase Order Number'
            }
        )
        
        self.amount_from = FloatField(
            'Amount From',
            validators=[Optional()],
            render_kw={'class': 'form-input', 'type': 'number', 'step': '0.01', 'min': '0'}
        )
        
        self.amount_to = FloatField(
            'Amount To',
            validators=[Optional()],
            render_kw={'class': 'form-input', 'type': 'number', 'step': '0.01', 'min': '0'}
        )

# =============================================================================
# FORM UTILITIES - Following your existing form utility patterns
# =============================================================================

class FormFieldRenderer:
    """Utility class for rendering form fields in templates"""
    
    @staticmethod
    def render_field(field, field_def: FieldDefinition = None, **kwargs):
        """Render form field with proper styling and attributes"""
        
        # Apply healthcare-specific styling
        css_classes = ['form-input']
        
        if field_def:
            if field_def.field_type == FieldType.SELECT or field_def.field_type == FieldType.FOREIGN_KEY:
                css_classes = ['form-select']
            elif field_def.field_type == FieldType.BOOLEAN:
                css_classes = ['form-checkbox']
            elif field_def.field_type in [FieldType.PATIENT_MRN, FieldType.GST_NUMBER, FieldType.PAN_NUMBER]:
                css_classes.append('font-mono')
            
            if field_def.is_phi:
                css_classes.append('phi-field')
            
            if field_def.required:
                css_classes.append('required')
        
        # Apply error styling
        if field.errors:
            css_classes.append('error')
        
        # Update field's render_kw
        if hasattr(field, 'render_kw') and field.render_kw:
            existing_classes = field.render_kw.get('class', '').split()
            all_classes = list(set(existing_classes + css_classes))
            field.render_kw['class'] = ' '.join(all_classes)
        
        return field

class FormValidator:
    """Universal form validation utilities"""
    
    @staticmethod
    def validate_entity_form(form: UniversalEntityForm, entity_config: EntityConfiguration) -> List[str]:
        """Validate entity form with business rules"""
        errors = []
        
        # Apply business rule validations
        for rule in entity_config.business_rules:
            try:
                rule_errors = FormValidator._apply_business_rule(form, rule, entity_config)
                errors.extend(rule_errors)
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Error applying business rule {rule}: {str(e)}")
        
        return errors
    
    @staticmethod
    def _apply_business_rule(form: UniversalEntityForm, rule: str, config: EntityConfiguration) -> List[str]:
        """Apply specific business rule validation"""
        errors = []
        
        if rule == 'gst_required_for_business':
            # Example business rule: GST required for business entities
            if hasattr(form, 'entity_type') and form.entity_type.data == 'business':
                if hasattr(form, 'gst_number') and not form.gst_number.data:
                    errors.append('GST number is required for business entities')
        
        elif rule == 'patient_mrn_unique':
            # Example: Check MRN uniqueness
            if hasattr(form, 'mrn') and form.mrn.data:
                if FormValidator._check_mrn_exists(form.mrn.data):
                    errors.append('MRN already exists')
        
        return errors
    
    @staticmethod
    def _check_mrn_exists(mrn: str) -> bool:
        """Check if MRN already exists"""
        try:
            from flask_login import current_user
            from app.services.database_service import get_db_session
            from app.models.master import Patient
            
            with get_db_session() as session:
                existing = session.query(Patient).filter(
                    Patient.mrn == mrn,
                    Patient.hospital_id == current_user.hospital_id
                ).first()
                
                return existing is not None
        except Exception:
            return False

# =============================================================================
# FORM FACTORY - Following your existing factory patterns
# =============================================================================

class UniversalFormFactory:
    """Factory for creating forms based on entity configuration"""
    
    @staticmethod
    def create_search_form(entity_type: str):
        """Create search form for entity type"""
        try:
            from app.config.entity_configurations import EntityType
            from app.core.entity_registry import EntityConfigurationRegistry
            
            entity_enum = EntityType(entity_type)
            config = EntityConfigurationRegistry.get_config(entity_enum)
            
            # Check for specialized forms first
            if entity_type == 'patients':
                return PatientSearchForm()
            elif entity_type == 'supplier_invoices':
                return SupplierInvoiceSearchForm()
            else:
                return UniversalSearchForm(config)
                
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error creating search form for {entity_type}: {str(e)}")
            return FlaskForm()  # Fallback to basic form
    
    @staticmethod
    def create_entity_form(entity_type: str, obj=None):
        """Create entity form for CRUD operations"""
        try:
            from app.config.entity_configurations import EntityType
            from app.core.entity_registry import EntityConfigurationRegistry
            
            entity_enum = EntityType(entity_type)
            config = EntityConfigurationRegistry.get_config(entity_enum)
            
            return UniversalEntityForm(config, obj=obj)
            
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error creating entity form for {entity_type}: {str(e)}")
            return FlaskForm()  # Fallback to basic form

# =============================================================================
# USAGE EXAMPLES - Integration with your existing patterns
# =============================================================================

"""
Example usage in your views:

# Universal form usage
from app.forms.universal_forms import UniversalFormFactory

@app.route('/universal/<entity_type>/search')
def entity_search(entity_type):
    form = UniversalFormFactory.create_search_form(entity_type)
    return render_template('universal/search.html', form=form)

@app.route('/universal/<entity_type>/create', methods=['GET', 'POST'])
def entity_create(entity_type):
    form = UniversalFormFactory.create_entity_form(entity_type)
    
    if form.validate_on_submit():
        # Process form data
        pass
    
    return render_template('universal/form.html', form=form)

# Integration with existing forms in templates:

# In your templates (following your existing form template patterns):
{% for field in form %}
    {% if field.type != 'HiddenField' and field.type != 'CSRFTokenField' %}
    <div class="form-group">
        {{ field.label(class="form-label") }}
        {{ field(class="form-input") }}
        {% if field.errors %}
        <div class="form-errors">
            {% for error in field.errors %}
            <span class="error-message">{{ error }}</span>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    {% endif %}
{% endfor %}
"""