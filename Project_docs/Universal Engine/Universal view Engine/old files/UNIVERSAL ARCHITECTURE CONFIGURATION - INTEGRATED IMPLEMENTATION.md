# =============================================================================
# UNIVERSAL ARCHITECTURE CONFIGURATION - INTEGRATED IMPLEMENTATION
# Following SkinSpire HMS Existing Structure and Patterns
# =============================================================================

# =============================================================================
# FILE: app/config/entity_configurations.py
# PURPOSE: Core entity configuration classes following existing config patterns
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Type
from enum import Enum
import uuid

# Import your existing models to maintain integration
from app.models.master import Patient, Supplier, Medicine, Staff, Service
from app.models.transaction import (
    SupplierInvoice, PatientInvoice, SupplierPayment, 
    Appointment, PurchaseOrderHeader
)

class EntityType(Enum):
    """Entity types mapped to your existing models"""
    # Master Data Entities (from models/master.py)
    PATIENT = "patients"
    SUPPLIER = "suppliers"
    MEDICINE = "medicines"
    STAFF = "staff"
    SERVICE = "services"
    
    # Transaction Entities (from models/transaction.py)
    SUPPLIER_INVOICE = "supplier_invoices"
    PATIENT_INVOICE = "patient_invoices"
    SUPPLIER_PAYMENT = "supplier_payments"
    APPOINTMENT = "appointments"
    PURCHASE_ORDER = "purchase_orders"

class FieldType(Enum):
    """Field types for universal form and display generation"""
    # Basic Fields
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    TEXTAREA = "textarea"
    
    # Selection Fields
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    
    # Healthcare-Specific Fields
    PATIENT_MRN = "patient_mrn"
    GST_NUMBER = "gst_number"
    PAN_NUMBER = "pan_number"
    HSN_CODE = "hsn_code"
    MEDICINE_BATCH = "medicine_batch"
    INVOICE_NUMBER = "invoice_number"
    
    # Financial Fields
    AMOUNT = "amount"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    
    # Relationship Fields
    FOREIGN_KEY = "foreign_key"
    
    # Display Fields
    STATUS_BADGE = "status_badge"
    IMAGE = "image"
    FILE = "file"
    
    # Search Fields
    SEARCH = "search"
    AUTOCOMPLETE = "autocomplete"
    DATE_RANGE = "date_range"

@dataclass
class FieldDefinition:
    """Universal field definition following your existing form patterns"""
    name: str                           # Database field name
    field_type: FieldType              # Field type for rendering
    label: str                         # Display label
    searchable: bool = False           # Include in search
    filterable: bool = False           # Available as filter
    sortable: bool = False             # Allow sorting
    show_in_list: bool = False         # Display in list view
    show_in_view: bool = True          # Display in detail view
    required: bool = False             # Required for creation/edit
    placeholder: str = ""              # Input placeholder
    help_text: str = ""               # Help text
    validation_rules: List[str] = field(default_factory=list)  # Validation rules
    options: List[Dict[str, Any]] = field(default_factory=list)  # Select options
    related_entity: str = ""           # Foreign key relationship
    related_display_field: str = ""    # Field to display from related entity
    css_classes: str = ""              # Additional CSS classes
    
    # Healthcare-specific attributes
    is_phi: bool = False               # Contains PHI data
    audit_required: bool = False       # Requires audit logging
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        return {
            'name': self.name,
            'field_type': self.field_type.value,
            'label': self.label,
            'searchable': self.searchable,
            'filterable': self.filterable,
            'sortable': self.sortable,
            'show_in_list': self.show_in_list,
            'show_in_view': self.show_in_view,
            'required': self.required,
            'placeholder': self.placeholder,
            'help_text': self.help_text,
            'options': self.options,
            'css_classes': self.css_classes,
        }

@dataclass
class ActionDefinition:
    """Action button definitions for entity operations"""
    action_id: str                     # Unique action identifier
    label: str                         # Button label
    icon: str                          # FontAwesome icon class
    handler_type: str = "standard"     # standard, custom, ajax
    permission_required: str = ""      # Permission needed for action
    css_classes: str = "btn btn-primary"  # Button styling
    confirmation_required: bool = False # Show confirmation dialog
    confirmation_message: str = ""     # Confirmation dialog message
    url_pattern: str = ""              # URL pattern for action
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        return {
            'action_id': self.action_id,
            'label': self.label,
            'icon': self.icon,
            'handler_type': self.handler_type,
            'css_classes': self.css_classes,
            'confirmation_required': self.confirmation_required,
            'confirmation_message': self.confirmation_message,
        }

@dataclass
class PermissionConfig:
    """Permission configuration for entity access"""
    module_name: str                   # Permission module (e.g., 'supplier')
    view_permission: str = "view"      # View permission
    create_permission: str = "create"  # Create permission
    edit_permission: str = "edit"      # Edit permission
    delete_permission: str = "delete"  # Delete permission
    branch_aware: bool = True          # Uses branch-aware permissions

@dataclass
class DisplayConfig:
    """Display configuration for entity presentation"""
    default_display_mode: str = "table"  # table, card, calendar
    items_per_page: int = 25           # Default pagination
    default_sort_field: str = ""       # Default sort field
    default_sort_order: str = "asc"    # Default sort order (asc/desc)
    enable_export: bool = True         # Allow data export
    enable_print: bool = True          # Allow printing
    show_summary_stats: bool = True    # Show summary statistics
    
@dataclass
class EntityConfiguration:
    """Universal entity configuration following your existing patterns"""
    entity_type: EntityType
    model_class: Type                  # Your existing SQLAlchemy model class
    name: str                          # Singular name (e.g., "Patient")
    plural_name: str                   # Plural name (e.g., "Patients")
    icon: str                          # FontAwesome icon class
    table_name: str                    # Database table name
    primary_key: str                   # Primary key field name
    title_field: str                   # Main display field
    subtitle_field: str = ""           # Secondary display field
    description_field: str = ""        # Description field
    
    # Field definitions
    fields: List[FieldDefinition] = field(default_factory=list)
    actions: List[ActionDefinition] = field(default_factory=list)
    
    # Search configuration
    default_search_fields: List[str] = field(default_factory=list)
    quick_search_fields: List[str] = field(default_factory=list)
    
    # Related entities
    related_entities: List[str] = field(default_factory=list)
    
    # Configuration objects
    permissions: PermissionConfig = field(default_factory=lambda: PermissionConfig(""))
    display: DisplayConfig = field(default_factory=DisplayConfig)
    
    # Business rules
    business_rules: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)
    
    # Integration settings
    service_class: str = ""            # Associated service class name
    controller_class: str = ""         # Associated controller class name
    form_class: str = ""              # Associated form class name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        return {
            'entity_type': self.entity_type.value,
            'name': self.name,
            'plural_name': self.plural_name,
            'icon': self.icon,
            'table_name': self.table_name,
            'primary_key': self.primary_key,
            'title_field': self.title_field,
            'subtitle_field': self.subtitle_field,
            'fields': [field.to_dict() for field in self.fields],
            'actions': [action.to_dict() for action in self.actions],
            'default_search_fields': self.default_search_fields,
            'permissions': self.permissions.__dict__,
            'display': self.display.__dict__,
        }

# =============================================================================
# FILE: app/config/healthcare_entities.py  
# PURPOSE: Healthcare-specific entity configurations using your existing models
# =============================================================================

from .entity_configurations import (
    EntityConfiguration, EntityType, FieldDefinition, FieldType, 
    ActionDefinition, PermissionConfig, DisplayConfig
)

class HealthcareEntityFactory:
    """Factory for creating healthcare entity configurations"""
    
    @staticmethod
    def create_patient_config() -> EntityConfiguration:
        """Patient configuration using your existing Patient model"""
        return EntityConfiguration(
            entity_type=EntityType.PATIENT,
            model_class=Patient,
            name="Patient", 
            plural_name="Patients",
            icon="fas fa-user-injured",
            table_name="patients",
            primary_key="patient_id",
            title_field="full_name",
            subtitle_field="mrn",
            description_field="patient_summary",
            
            fields=[
                FieldDefinition(
                    name="mrn", 
                    field_type=FieldType.PATIENT_MRN,
                    label="MRN",
                    searchable=True,
                    show_in_list=True,
                    sortable=True,
                    required=True,
                    is_phi=True
                ),
                FieldDefinition(
                    name="full_name",
                    field_type=FieldType.TEXT,
                    label="Patient Name", 
                    searchable=True,
                    show_in_list=True,
                    sortable=True,
                    required=True,
                    is_phi=True
                ),
                FieldDefinition(
                    name="date_of_birth",
                    field_type=FieldType.DATE,
                    label="Date of Birth",
                    filterable=True,
                    show_in_list=True,
                    sortable=True,
                    is_phi=True
                ),
                FieldDefinition(
                    name="gender",
                    field_type=FieldType.SELECT,
                    label="Gender",
                    filterable=True,
                    show_in_list=True,
                    options=[
                        {"value": "M", "label": "Male"},
                        {"value": "F", "label": "Female"},
                        {"value": "O", "label": "Other"}
                    ]
                ),
                FieldDefinition(
                    name="contact_number",
                    field_type=FieldType.PHONE,
                    label="Contact Number",
                    searchable=True,
                    show_in_list=True,
                    is_phi=True
                ),
                FieldDefinition(
                    name="email_address",
                    field_type=FieldType.EMAIL,
                    label="Email",
                    searchable=True,
                    show_in_view=True,
                    is_phi=True
                ),
                FieldDefinition(
                    name="patient_status",
                    field_type=FieldType.STATUS_BADGE,
                    label="Status",
                    filterable=True,
                    show_in_list=True,
                    options=[
                        {"value": "active", "label": "Active", "class": "status-success"},
                        {"value": "inactive", "label": "Inactive", "class": "status-warning"},
                        {"value": "deceased", "label": "Deceased", "class": "status-danger"}
                    ]
                ),
            ],
            
            actions=[
                ActionDefinition(
                    action_id="view",
                    label="View Details",
                    icon="fas fa-eye",
                    handler_type="standard",
                    permission_required="view"
                ),
                ActionDefinition(
                    action_id="edit", 
                    label="Edit Patient",
                    icon="fas fa-edit",
                    handler_type="standard",
                    permission_required="edit"
                ),
                ActionDefinition(
                    action_id="appointments",
                    label="Appointments",
                    icon="fas fa-calendar",
                    handler_type="custom",
                    permission_required="view"
                ),
                ActionDefinition(
                    action_id="billing",
                    label="Billing History", 
                    icon="fas fa-file-invoice",
                    handler_type="custom",
                    permission_required="view"
                ),
            ],
            
            default_search_fields=["mrn", "full_name", "contact_number", "email_address"],
            quick_search_fields=["mrn", "full_name"],
            related_entities=["appointments", "patient_invoices", "prescriptions"],
            
            permissions=PermissionConfig(
                module_name="patient",
                branch_aware=True
            ),
            
            display=DisplayConfig(
                default_display_mode="table",
                items_per_page=25,
                default_sort_field="full_name",
                show_summary_stats=True
            ),
            
            service_class="PatientService",
            form_class="PatientForm"
        )
    
    @staticmethod
    def create_supplier_config() -> EntityConfiguration:
        """Supplier configuration using your existing Supplier model"""
        return EntityConfiguration(
            entity_type=EntityType.SUPPLIER,
            model_class=Supplier,
            name="Supplier",
            plural_name="Suppliers", 
            icon="fas fa-truck",
            table_name="suppliers",
            primary_key="supplier_id",
            title_field="supplier_name",
            subtitle_field="gst_registration_number",
            
            fields=[
                FieldDefinition(
                    name="supplier_name",
                    field_type=FieldType.TEXT,
                    label="Supplier Name",
                    searchable=True,
                    show_in_list=True,
                    sortable=True,
                    required=True
                ),
                FieldDefinition(
                    name="supplier_category",
                    field_type=FieldType.SELECT,
                    label="Category",
                    filterable=True,
                    show_in_list=True,
                    options=[
                        {"value": "retail", "label": "Retail Supplier"},
                        {"value": "distributor", "label": "Distributor"},
                        {"value": "manufacturer", "label": "Manufacturer"},
                        {"value": "equipment", "label": "Equipment Supplier"}
                    ]
                ),
                FieldDefinition(
                    name="gst_registration_number",
                    field_type=FieldType.GST_NUMBER,
                    label="GST Number", 
                    searchable=True,
                    show_in_list=True,
                    audit_required=True
                ),
                FieldDefinition(
                    name="pan_number",
                    field_type=FieldType.PAN_NUMBER,
                    label="PAN Number",
                    searchable=True,
                    show_in_view=True
                ),
                FieldDefinition(
                    name="contact_person_name",
                    field_type=FieldType.TEXT,
                    label="Contact Person",
                    show_in_list=True,
                    searchable=True
                ),
                FieldDefinition(
                    name="supplier_status",
                    field_type=FieldType.STATUS_BADGE,
                    label="Status",
                    filterable=True,
                    show_in_list=True,
                    options=[
                        {"value": "active", "label": "Active", "class": "status-success"},
                        {"value": "inactive", "label": "Inactive", "class": "status-warning"},
                        {"value": "blacklisted", "label": "Blacklisted", "class": "status-danger"}
                    ]
                ),
            ],
            
            actions=[
                ActionDefinition(
                    action_id="view",
                    label="View Details", 
                    icon="fas fa-eye"
                ),
                ActionDefinition(
                    action_id="edit",
                    label="Edit Supplier",
                    icon="fas fa-edit"
                ),
                ActionDefinition(
                    action_id="invoices",
                    label="Invoices",
                    icon="fas fa-file-invoice",
                    handler_type="custom"
                ),
                ActionDefinition(
                    action_id="payments",
                    label="Payments", 
                    icon="fas fa-money-bill",
                    handler_type="custom"
                ),
            ],
            
            default_search_fields=["supplier_name", "gst_registration_number", "contact_person_name"],
            quick_search_fields=["supplier_name", "gst_registration_number"],
            related_entities=["supplier_invoices", "supplier_payments", "purchase_orders"],
            
            permissions=PermissionConfig(
                module_name="supplier",
                branch_aware=True
            ),
            
            service_class="SupplierService"
        )
    
    @staticmethod 
    def create_supplier_invoice_config() -> EntityConfiguration:
        """Supplier Invoice configuration using your existing SupplierInvoice model"""
        return EntityConfiguration(
            entity_type=EntityType.SUPPLIER_INVOICE,
            model_class=SupplierInvoice,
            name="Supplier Invoice",
            plural_name="Supplier Invoices",
            icon="fas fa-file-invoice",
            table_name="supplier_invoices", 
            primary_key="invoice_id",
            title_field="invoice_number",
            subtitle_field="supplier_name",
            
            fields=[
                FieldDefinition(
                    name="invoice_number",
                    field_type=FieldType.INVOICE_NUMBER,
                    label="Invoice Number",
                    searchable=True,
                    show_in_list=True,
                    sortable=True,
                    required=True
                ),
                FieldDefinition(
                    name="invoice_date",
                    field_type=FieldType.DATE,
                    label="Invoice Date",
                    filterable=True,
                    show_in_list=True,
                    sortable=True,
                    required=True
                ),
                FieldDefinition(
                    name="supplier_name",
                    field_type=FieldType.FOREIGN_KEY,
                    label="Supplier",
                    searchable=True,
                    show_in_list=True,
                    sortable=True,
                    related_entity="suppliers",
                    related_display_field="supplier_name"
                ),
                FieldDefinition(
                    name="po_number", 
                    field_type=FieldType.TEXT,
                    label="PO Number",
                    searchable=True,
                    show_in_list=True
                ),
                FieldDefinition(
                    name="total_amount",
                    field_type=FieldType.AMOUNT,
                    label="Total Amount",
                    show_in_list=True,
                    sortable=True
                ),
                FieldDefinition(
                    name="payment_status",
                    field_type=FieldType.STATUS_BADGE,
                    label="Payment Status",
                    filterable=True,
                    show_in_list=True,
                    options=[
                        {"value": "pending", "label": "Pending", "class": "status-warning"},
                        {"value": "partial", "label": "Partial", "class": "status-info"}, 
                        {"value": "paid", "label": "Paid", "class": "status-success"},
                        {"value": "overdue", "label": "Overdue", "class": "status-danger"}
                    ]
                ),
                FieldDefinition(
                    name="due_date",
                    field_type=FieldType.DATE,
                    label="Due Date",
                    filterable=True,
                    show_in_list=True,
                    sortable=True
                ),
            ],
            
            actions=[
                ActionDefinition(
                    action_id="view",
                    label="View Invoice",
                    icon="fas fa-eye"
                ),
                ActionDefinition(
                    action_id="edit",
                    label="Edit Invoice", 
                    icon="fas fa-edit"
                ),
                ActionDefinition(
                    action_id="payment",
                    label="Record Payment",
                    icon="fas fa-money-bill",
                    handler_type="custom"
                ),
                ActionDefinition(
                    action_id="print",
                    label="Print Invoice",
                    icon="fas fa-print", 
                    handler_type="custom"
                ),
            ],
            
            default_search_fields=["invoice_number", "supplier_name", "po_number"],
            quick_search_fields=["invoice_number", "po_number"],
            related_entities=["supplier_payments", "purchase_orders"],
            
            permissions=PermissionConfig(
                module_name="supplier_invoice",
                branch_aware=True
            ),
            
            display=DisplayConfig(
                default_sort_field="invoice_date",
                default_sort_order="desc"
            ),
            
            service_class="SupplierService"
        )

# =============================================================================
# FILE: app/core/entity_registry.py
# PURPOSE: Central registry for entity configurations
# =============================================================================

from typing import Dict, Optional
from .entity_configurations import EntityConfiguration, EntityType
from .healthcare_entities import HealthcareEntityFactory

class EntityConfigurationRegistry:
    """Central registry for all entity configurations"""
    
    _configurations: Dict[EntityType, EntityConfiguration] = {}
    _initialized = False
    
    @classmethod
    def register(cls, config: EntityConfiguration):
        """Register an entity configuration"""
        cls._configurations[config.entity_type] = config
    
    @classmethod
    def get_config(cls, entity_type: EntityType) -> Optional[EntityConfiguration]:
        """Get configuration for an entity type"""
        if not cls._initialized:
            cls.initialize_default_configs()
        return cls._configurations.get(entity_type)
    
    @classmethod
    def get_all_configs(cls) -> Dict[EntityType, EntityConfiguration]:
        """Get all registered configurations"""
        if not cls._initialized:
            cls.initialize_default_configs()
        return cls._configurations.copy()
    
    @classmethod
    def initialize_default_configs(cls):
        """Initialize default healthcare entity configurations"""
        if cls._initialized:
            return
            
        # Register healthcare entity configurations
        cls.register(HealthcareEntityFactory.create_patient_config())
        cls.register(HealthcareEntityFactory.create_supplier_config())
        cls.register(HealthcareEntityFactory.create_supplier_invoice_config())
        
        # Add more entity configurations as needed
        # cls.register(HealthcareEntityFactory.create_medicine_config())
        # cls.register(HealthcareEntityFactory.create_appointment_config())
        
        cls._initialized = True
    
    @classmethod
    def list_entity_types(cls) -> List[str]:
        """Get list of available entity types"""
        if not cls._initialized:
            cls.initialize_default_configs()
        return [entity_type.value for entity_type in cls._configurations.keys()]

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

"""
Example usage in your existing application:

# In your views (app/views/universal_views.py)
from app.core.entity_registry import EntityConfigurationRegistry
from app.config.entity_configurations import EntityType

@app.route('/universal/patients')
def patient_list():
    config = EntityConfigurationRegistry.get_config(EntityType.PATIENT)
    # Use config for universal rendering
    
# In your templates  
{{ config.name }}  # "Patient"
{{ config.icon }}  # "fas fa-user-injured"
{% for field in config.fields %}
    {% if field.show_in_list %}
        {{ field.label }}
    {% endif %}
{% endfor %}

# In your services (app/services/universal_search_service.py)
config = EntityConfigurationRegistry.get_config(entity_type)
model_class = config.model_class  # Your existing Patient, Supplier, etc.
table_name = config.table_name    # Your existing table names
"""