# Universal View Engine Foundation - Detailed Implementation Plan
## Phase 1: Foundation Setup (Weeks 1-3)

---

## 📋 **Prerequisites and Setup**

### **Environment Verification**
- [ ] Python 3.12.8 environment active
- [ ] Flask 3.1.0 installed and working
- [ ] Your existing Skinspire HMS codebase accessible
- [ ] Database connection tested
- [ ] Your existing supplier payment functionality working

### **Backup Strategy**
```bash
# Create implementation branch
git checkout -b feature/universal-engine-foundation
git push -u origin feature/universal-engine-foundation

# Document current state
git tag baseline-before-universal-engine
```

---

## 🏗️ **Week 1: Universal View Engine Core Setup**

### **Day 1: Directory Structure Creation**

#### **Step 1.1: Create Universal View Engine Directory**
```bash
# Create the core universal view engine structure
mkdir -p app/engine
touch app/engine/__init__.py
touch app/engine/universal_view_engine.py
touch app/engine/universal_components.py
touch app/engine/data_assembler.py

# Create enhanced config structure
touch app/config/entity_configurations.py
touch app/config/field_definitions.py
touch app/config/universal_config.py
```

#### **Step 1.2: Create Initial Universal View Engine Core**
Create `app/engine/__init__.py`:
```python
"""
Universal View Engine for Skinspire HMS
Core view engine that provides universal functionality for all entities
"""

from .universal_view_engine import UniversalViewEngine
from .universal_components import UniversalListService, UniversalDetailService
from .data_assembler import DataAssembler

# Global view engine instance
universal_view_engine = UniversalViewEngine()

__all__ = ['universal_view_engine', 'UniversalViewEngine', 'UniversalListService', 'UniversalDetailService', 'DataAssembler']
```

#### **Step 1.3: Implement Core Universal View Engine**
Create `app/engine/universal_view_engine.py`:
```python
"""
Core Universal View Engine - Orchestrates all universal view functionality
"""

from typing import Dict, Any, Optional
from flask import current_app
import importlib

class UniversalViewEngine:
    """
    Core view engine that orchestrates universal functionality for all entities.
    This is the main entry point for all universal view operations.
    """
    
    def __init__(self):
        self.entity_services = {}
        self.entity_configs = {}
        
    def get_entity_service(self, entity_type: str):
        """Get or create entity service based on entity type"""
        if entity_type not in self.entity_services:
            self.entity_services[entity_type] = self._load_entity_service(entity_type)
        return self.entity_services[entity_type]
    
    def get_entity_config(self, entity_type: str):
        """Get entity configuration"""
        if entity_type not in self.entity_configs:
            self.entity_configs[entity_type] = self._load_entity_config(entity_type)
        return self.entity_configs[entity_type]
    
    def render_entity_list(self, entity_type: str, **kwargs) -> str:
        """Universal list rendering for any entity"""
        try:
            from .universal_components import UniversalListService
            
            # Get configuration
            config = self.get_entity_config(entity_type)
            
            # Use universal list service
            list_service = UniversalListService(config)
            assembled_data = list_service.get_list_data()
            
            # Add any additional context
            assembled_data.update(kwargs)
            
            return assembled_data
            
        except Exception as e:
            current_app.logger.error(f"Error in universal view engine list rendering for {entity_type}: {str(e)}")
            raise
    
    def render_entity_detail(self, entity_type: str, entity_id: str, **kwargs) -> str:
        """Universal detail rendering for any entity"""
        try:
            from .universal_components import UniversalDetailService
            
            # Get configuration
            config = self.get_entity_config(entity_type)
            
            # Use universal detail service
            detail_service = UniversalDetailService(config)
            assembled_data = detail_service.get_detail_data(entity_id)
            
            # Add any additional context
            assembled_data.update(kwargs)
            
            return assembled_data
            
        except Exception as e:
            current_app.logger.error(f"Error in universal view engine detail rendering for {entity_type}/{entity_id}: {str(e)}")
            raise
    
    def _load_entity_service(self, entity_type: str):
        """Dynamically load appropriate entity service"""
        # Map entity types to service modules (business entity grouping)
        service_map = {
            'supplier_payments': ('app.services.universal_supplier_service', 'UniversalSupplierPaymentService'),
            'supplier_invoices': ('app.services.universal_supplier_service', 'UniversalSupplierInvoiceService'),
            'patients': ('app.services.universal_patient_service', 'UniversalPatientService'),
            'medicines': ('app.services.universal_medicine_service', 'UniversalMedicineService'),
        }
        
        if entity_type not in service_map:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        module_path, class_name = service_map[entity_type]
        
        try:
            module = importlib.import_module(module_path)
            service_class = getattr(module, class_name)
            return service_class()
        except ImportError as e:
            current_app.logger.error(f"Failed to import service for {entity_type}: {str(e)}")
            raise
    
    def _load_entity_config(self, entity_type: str):
        """Load entity configuration"""
        try:
            from app.config.entity_configurations import get_entity_config
            return get_entity_config(entity_type)
        except ImportError as e:
            current_app.logger.error(f"Failed to load config for {entity_type}: {str(e)}")
            raise
```

### **Day 2: Entity Configuration System**

#### **Step 2.1: Create Field Definitions**
Create `app/config/field_definitions.py`:
```python
"""
Field type definitions for universal engine
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum

class FieldType(Enum):
    """Universal field types"""
    # Basic Fields
    TEXT = "text"
    TEXTAREA = "textarea"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    
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
    """Universal field definition"""
    name: str                              # Database field name
    label: str                             # Display label
    field_type: FieldType                  # Field type for rendering
    show_in_list: bool = False             # Display in list view
    show_in_detail: bool = True            # Display in detail view
    searchable: bool = False               # Include in search
    filterable: bool = False               # Available as filter
    sortable: bool = False                 # Allow sorting
    required: bool = False                 # Required for forms
    placeholder: str = ""                  # Input placeholder
    help_text: str = ""                    # Help text
    options: List[Dict[str, Any]] = None   # Select options
    related_entity: str = ""               # Foreign key relationship
    related_display_field: str = ""        # Field to display from related entity
    css_classes: str = ""                  # Additional CSS classes
    validation_rules: List[str] = None     # Validation rules
    
    # Healthcare-specific attributes
    is_phi: bool = False                   # Contains PHI data
    audit_required: bool = False           # Requires audit logging
    
    def __post_init__(self):
        if self.options is None:
            self.options = []
        if self.validation_rules is None:
            self.validation_rules = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'label': self.label,
            'field_type': self.field_type.value,
            'show_in_list': self.show_in_list,
            'show_in_detail': self.show_in_detail,
            'searchable': self.searchable,
            'filterable': self.filterable,
            'sortable': self.sortable,
            'required': self.required,
            'placeholder': self.placeholder,
            'help_text': self.help_text,
            'options': self.options,
            'related_entity': self.related_entity,
            'css_classes': self.css_classes,
            'is_phi': self.is_phi
        }

@dataclass
class ActionDefinition:
    """Universal action definition"""
    action_id: str                         # Unique action identifier
    label: str                             # Button label
    icon: str                              # FontAwesome icon class
    handler_type: str = "standard"         # standard, custom, ajax
    permission_required: str = ""          # Permission needed
    css_classes: str = "btn btn-primary"   # Button styling
    confirmation_required: bool = False    # Show confirmation dialog
    confirmation_message: str = ""         # Confirmation message
    url_pattern: str = ""                  # URL pattern for action
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'action_id': self.action_id,
            'label': self.label,
            'icon': self.icon,
            'handler_type': self.handler_type,
            'css_classes': self.css_classes,
            'confirmation_required': self.confirmation_required,
            'confirmation_message': self.confirmation_message,
            'url_pattern': self.url_pattern
        }
```

#### **Step 2.2: Create Entity Configuration System**
Create `app/config/entity_configurations.py`:
```python
"""
Entity configuration system for universal engine
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .field_definitions import FieldDefinition, ActionDefinition

@dataclass
class EntityConfiguration:
    """Universal entity configuration"""
    entity_type: str                       # Unique entity identifier
    service_name: str                      # Service class name
    name: str                              # Singular name (e.g., "Payment")
    plural_name: str                       # Plural name (e.g., "Payments")
    table_name: str                        # Database table name
    primary_key: str                       # Primary key field name
    title_field: str                       # Main display field
    subtitle_field: str = ""               # Secondary display field
    description_field: str = ""            # Description field
    icon: str = "fas fa-file"              # FontAwesome icon
    
    # Field and action definitions
    fields: List[FieldDefinition] = field(default_factory=list)
    actions: List[ActionDefinition] = field(default_factory=list)
    
    # Search configuration
    default_search_fields: List[str] = field(default_factory=list)
    quick_search_fields: List[str] = field(default_factory=list)
    
    # Display configuration
    default_sort_field: str = ""
    default_sort_order: str = "desc"       # asc or desc
    items_per_page: int = 25
    
    # Permissions
    permission_module: str = ""            # Permission module name
    
    # Business rules
    business_rules: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering"""
        return {
            'entity_type': self.entity_type,
            'service_name': self.service_name,
            'name': self.name,
            'plural_name': self.plural_name,
            'table_name': self.table_name,
            'primary_key': self.primary_key,
            'title_field': self.title_field,
            'subtitle_field': self.subtitle_field,
            'icon': self.icon,
            'fields': [field_def.to_dict() for field_def in self.fields],
            'actions': [action.to_dict() for action in self.actions],
            'default_search_fields': self.default_search_fields,
            'default_sort_field': self.default_sort_field,
            'default_sort_order': self.default_sort_order,
            'items_per_page': self.items_per_page,
            'permission_module': self.permission_module
        }

# Entity configuration registry
_entity_configs: Dict[str, EntityConfiguration] = {}

def register_entity_config(config: EntityConfiguration):
    """Register an entity configuration"""
    _entity_configs[config.entity_type] = config

def get_entity_config(entity_type: str) -> EntityConfiguration:
    """Get entity configuration by type"""
    if entity_type not in _entity_configs:
        raise ValueError(f"No configuration found for entity type: {entity_type}")
    return _entity_configs[entity_type]

def get_all_entity_configs() -> Dict[str, EntityConfiguration]:
    """Get all registered entity configurations"""
    return _entity_configs.copy()

def list_entity_types() -> List[str]:
    """Get list of all registered entity types"""
    return list(_entity_configs.keys())

# Supplier Payment Configuration (First Implementation)
def create_supplier_payment_config() -> EntityConfiguration:
    """Create supplier payment entity configuration"""
    from .field_definitions import FieldDefinition, FieldType, ActionDefinition
    
    return EntityConfiguration(
        entity_type="supplier_payments",
        service_name="supplier_payments",
        name="Supplier Payment",
        plural_name="Supplier Payments",
        table_name="supplier_payments",
        primary_key="payment_id",
        title_field="payment_reference",
        subtitle_field="supplier_name",
        icon="fas fa-money-bill",
        
        fields=[
            FieldDefinition(
                name="payment_reference",
                label="Payment Reference",
                field_type=FieldType.TEXT,
                show_in_list=True,
                searchable=True,
                sortable=True,
                required=True
            ),
            FieldDefinition(
                name="supplier_name",
                label="Supplier",
                field_type=FieldType.TEXT,
                show_in_list=True,
                searchable=True,
                sortable=True
            ),
            FieldDefinition(
                name="payment_amount",
                label="Amount",
                field_type=FieldType.AMOUNT,
                show_in_list=True,
                sortable=True
            ),
            FieldDefinition(
                name="payment_date",
                label="Payment Date",
                field_type=FieldType.DATE,
                show_in_list=True,
                sortable=True,
                filterable=True
            ),
            FieldDefinition(
                name="payment_status",
                label="Status",
                field_type=FieldType.STATUS_BADGE,
                show_in_list=True,
                filterable=True,
                options=[
                    {"value": "pending", "label": "Pending", "class": "status-warning"},
                    {"value": "completed", "label": "Completed", "class": "status-success"},
                    {"value": "cancelled", "label": "Cancelled", "class": "status-danger"}
                ]
            ),
            FieldDefinition(
                name="payment_method",
                label="Payment Method",
                field_type=FieldType.SELECT,
                show_in_list=True,
                filterable=True,
                options=[
                    {"value": "bank_transfer", "label": "Bank Transfer"},
                    {"value": "cheque", "label": "Cheque"},
                    {"value": "cash", "label": "Cash"}
                ]
            ),
            FieldDefinition(
                name="bank_reference",
                label="Bank Reference",
                field_type=FieldType.TEXT,
                show_in_detail=True,
                searchable=True
            ),
            FieldDefinition(
                name="notes",
                label="Notes",
                field_type=FieldType.TEXTAREA,
                show_in_detail=True
            )
        ],
        
        actions=[
            ActionDefinition(
                action_id="view",
                label="View",
                icon="fas fa-eye",
                handler_type="standard",
                css_classes="btn btn-sm btn-outline"
            ),
            ActionDefinition(
                action_id="edit",
                label="Edit",
                icon="fas fa-edit",
                handler_type="standard",
                css_classes="btn btn-sm btn-primary"
            ),
            ActionDefinition(
                action_id="approve",
                label="Approve",
                icon="fas fa-check",
                handler_type="custom",
                css_classes="btn btn-sm btn-success",
                confirmation_required=True,
                confirmation_message="Are you sure you want to approve this payment?"
            )
        ],
        
        default_search_fields=["payment_reference", "supplier_name", "bank_reference"],
        quick_search_fields=["payment_reference", "supplier_name"],
        default_sort_field="payment_date",
        default_sort_order="desc",
        items_per_page=25,
        permission_module="supplier_payment"
    )

# Initialize configurations
def initialize_entity_configs():
    """Initialize all entity configurations"""
    # Register supplier payment configuration
    register_entity_config(create_supplier_payment_config())
    
    # Add more configurations as implemented
    # register_entity_config(create_patient_config())
    # register_entity_config(create_medicine_config())

# Auto-initialize when module is imported
initialize_entity_configs()
```

### **Day 3: Universal Components Foundation**

#### **Step 3.1: Create Universal Components**
Create `app/engine/universal_components.py`:
```python
"""
Universal components that work for all entities through configuration
"""

from typing import Dict, Any, List, Optional
from flask import request, current_user, current_app
from .data_assembler import DataAssembler

class UniversalListService:
    """Universal list service that works for ALL entities through configuration"""
    
    def __init__(self, config):
        self.config = config
        self.data_assembler = DataAssembler()
    
    def get_list_data(self) -> Dict[str, Any]:
        """Get complete list data assembled for frontend display"""
        try:
            # Extract filters from request
            filters = self._extract_filters()
            
            # Get raw data from appropriate entity service
            raw_data = self._get_raw_data(filters)
            
            # Assemble complete UI data structure
            assembled_data = self.data_assembler.assemble_list_data(
                self.config, raw_data, filters
            )
            
            return assembled_data
            
        except Exception as e:
            current_app.logger.error(f"Error in universal list service: {str(e)}")
            raise
    
    def _extract_filters(self) -> Dict[str, Any]:
        """Extract and validate filters from request"""
        filters = {
            'hospital_id': getattr(current_user, 'hospital_id', None),
            'page': int(request.args.get('page', 1)),
            'per_page': int(request.args.get('per_page', self.config.items_per_page)),
            'search': request.args.get('search'),
            'sort_field': request.args.get('sort_field', self.config.default_sort_field),
            'sort_order': request.args.get('sort_order', self.config.default_sort_order)
        }
        
        # Add field-specific filters based on configuration
        for field in self.config.fields:
            if field.filterable:
                filter_value = request.args.get(field.name)
                if filter_value:
                    filters[field.name] = filter_value
        
        # Add date range filters
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        # Remove None values
        return {k: v for k, v in filters.items() if v is not None and v != ''}
    
    def _get_raw_data(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Get raw data using appropriate entity service"""
        from app.engine import universal_view_engine
        
        # Get entity service through universal view engine
        entity_service = universal_view_engine.get_entity_service(self.config.entity_type)
        
        # Call appropriate service method based on entity type
        if hasattr(entity_service, 'search_payments'):
            return entity_service.search_payments(filters)
        elif hasattr(entity_service, 'search_invoices'):
            return entity_service.search_invoices(filters)
        elif hasattr(entity_service, 'search_patients'):
            return entity_service.search_patients(filters)
        elif hasattr(entity_service, 'search'):
            return entity_service.search(filters)
        else:
            raise AttributeError(f"No search method found for service: {type(entity_service)}")

class UniversalDetailService:
    """Universal detail service that works for ALL entities through configuration"""
    
    def __init__(self, config):
        self.config = config
        self.data_assembler = DataAssembler()
    
    def get_detail_data(self, entity_id: str) -> Dict[str, Any]:
        """Get complete detail data assembled for frontend display"""
        try:
            # Get raw entity data
            raw_data = self._get_raw_entity_data(entity_id)
            
            if not raw_data:
                return None
            
            # Get related data if configured
            related_data = self._get_related_data(entity_id, raw_data)
            
            # Assemble complete UI data structure
            assembled_data = self.data_assembler.assemble_detail_data(
                self.config, raw_data, related_data
            )
            
            return assembled_data
            
        except Exception as e:
            current_app.logger.error(f"Error in universal detail service: {str(e)}")
            raise
    
    def _get_raw_entity_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get raw entity data by ID"""
        from app.engine import universal_view_engine
        
        # Get entity service
        entity_service = universal_view_engine.get_entity_service(self.config.entity_type)
        
        # Call appropriate get method
        if hasattr(entity_service, 'get_payment_by_id'):
            return entity_service.get_payment_by_id(entity_id, current_user.hospital_id)
        elif hasattr(entity_service, 'get_invoice_by_id'):
            return entity_service.get_invoice_by_id(entity_id, current_user.hospital_id)
        elif hasattr(entity_service, 'get_by_id'):
            return entity_service.get_by_id(entity_id, current_user.hospital_id)
        else:
            raise AttributeError(f"No get method found for service: {type(entity_service)}")
    
    def _get_related_data(self, entity_id: str, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get related entity data"""
        # This will be implemented as we add more entities
        # For now, return empty dict
        return {}

def universal_list_view(entity_type: str):
    """Universal view function that handles ALL entity lists"""
    try:
        from flask import render_template
        from app.config.entity_configurations import get_entity_config
        
        # Get entity configuration
        config = get_entity_config(entity_type)
        
        # Use universal list service
        list_service = UniversalListService(config)
        assembled_data = list_service.get_list_data()
        
        # Render universal template
        return render_template('engine/universal_list.html', **assembled_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal list view for {entity_type}: {str(e)}")
        return render_template('engine/universal_error.html', 
                             error=str(e), 
                             entity_type=entity_type)

def universal_detail_view(entity_type: str, entity_id: str):
    """Universal view function that handles ALL entity details"""
    try:
        from flask import render_template
        from app.config.entity_configurations import get_entity_config
        
        # Get entity configuration
        config = get_entity_config(entity_type)
        
        # Use universal detail service
        detail_service = UniversalDetailService(config)
        assembled_data = detail_service.get_detail_data(entity_id)
        
        if not assembled_data:
            return render_template('engine/universal_error.html',
                                 error=f"{config.name} not found",
                                 entity_type=entity_type)
        
        # Render universal template
        return render_template('engine/universal_detail.html', **assembled_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in universal detail view for {entity_type}/{entity_id}: {str(e)}")
        return render_template('engine/universal_error.html',
                             error=str(e),
                             entity_type=entity_type)
```

### **Day 4: Data Assembler Implementation**

#### **Step 4.1: Create Data Assembler**
Create `app/engine/data_assembler.py`:
```python
"""
Data assembler - handles all backend data assembly for universal components
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

class DataAssembler:
    """Assembles all UI data structures in backend Python"""
    
    def assemble_list_data(self, config, raw_data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble complete list data for frontend display"""
        
        return {
            # Page metadata
            'page_title': config.plural_name,
            'page_icon': config.icon,
            'entity_type': config.entity_type,
            'entity_config': config.to_dict(),
            
            # Assembled table structure
            'table_columns': self.assemble_table_columns(config),
            'table_rows': self.assemble_table_rows(config, raw_data.get('items', [])),
            
            # Assembled search form
            'search_form': self.assemble_search_form(config, filters),
            
            # Assembled filter options
            'filter_options': self.assemble_filter_options(config),
            
            # Assembled action buttons
            'action_buttons': self.assemble_action_buttons(config),
            
            # Assembled pagination
            'pagination': self.assemble_pagination(raw_data),
            
            # Assembled summary statistics
            'summary_stats': self.assemble_summary_stats(config, raw_data),
            
            # Current filters and state
            'active_filters': filters,
            'current_user_id': getattr(self._get_current_user(), 'user_id', None)
        }
    
    def assemble_detail_data(self, config, entity_data: Dict[str, Any], related_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble complete detail data for frontend display"""
        
        return {
            # Page metadata
            'page_title': f"{config.name} Details",
            'page_icon': config.icon,
            'entity_type': config.entity_type,
            'entity_config': config.to_dict(),
            
            # Entity data
            'entity_title': entity_data.get(config.title_field, 'Unknown'),
            'entity_subtitle': entity_data.get(config.subtitle_field, ''),
            'entity_id': entity_data.get(config.primary_key),
            
            # Assembled detail sections
            'detail_sections': self.assemble_detail_sections(config, entity_data),
            
            # Assembled action buttons
            'detail_actions': self.assemble_detail_actions(config, entity_data),
            
            # Related data
            'related_data': related_data
        }
    
    def assemble_table_columns(self, config) -> List[Dict[str, Any]]:
        """Assemble table columns from configuration"""
        columns = []
        
        for field in config.fields:
            if field.show_in_list:
                columns.append({
                    'name': field.name,
                    'label': field.label,
                    'sortable': field.sortable,
                    'type': field.field_type.value,
                    'css_class': f'col-{field.name}',
                    'align': 'right' if field.field_type.value == 'amount' else 'left'
                })
        
        # Add actions column if actions are defined
        if config.actions:
            columns.append({
                'name': 'actions',
                'label': 'Actions',
                'sortable': False,
                'type': 'actions',
                'css_class': 'col-actions',
                'align': 'center'
            })
        
        return columns
    
    def assemble_table_rows(self, config, items: List[Dict]) -> List[Dict[str, Any]]:
        """Assemble and format table rows"""
        rows = []
        
        for item in items:
            row = {
                'id': item.get(config.primary_key),
                'cells': [],
                'css_class': self._get_row_css_class(config, item)
            }
            
            # Assemble data cells
            for field in config.fields:
                if field.show_in_list:
                    cell_data = self.format_cell_data(field, item.get(field.name))
                    row['cells'].append(cell_data)
            
            # Assemble action buttons for this row
            if config.actions:
                action_buttons = self.assemble_row_actions(config, item)
                row['cells'].append({
                    'type': 'actions',
                    'content': action_buttons,
                    'css_class': 'actions-cell'
                })
            
            rows.append(row)
        
        return rows
    
    def format_cell_data(self, field, value) -> Dict[str, Any]:
        """Format cell data based on field type"""
        if value is None or value == '':
            return {
                'type': field.field_type.value,
                'value': '',
                'display': '-',
                'css_class': 'empty-cell'
            }
        
        if field.field_type.value == 'amount':
            return {
                'type': 'amount',
                'value': float(value),
                'display': f'₹{float(value):,.2f}',
                'css_class': 'amount-cell text-right font-medium'
            }
        elif field.field_type.value == 'date':
            if hasattr(value, 'strftime'):
                formatted_date = value.strftime('%Y-%m-%d')
            else:
                formatted_date = str(value)
            return {
                'type': 'date',
                'value': value,
                'display': formatted_date,
                'css_class': 'date-cell'
            }
        elif field.field_type.value == 'status_badge':
            status_option = next((opt for opt in field.options if opt['value'] == str(value)), None)
            if status_option:
                return {
                    'type': 'status_badge',
                    'value': value,
                    'display': f'<span class="status-badge {status_option["class"]}">{status_option["label"]}</span>',
                    'css_class': 'status-cell'
                }
        elif field.field_type.value in ['patient_mrn', 'gst_number', 'invoice_number']:
            return {
                'type': field.field_type.value,
                'value': value,
                'display': f'<span class="font-mono text-sm">{value}</span>',
                'css_class': 'code-cell'
            }
        
        # Default text formatting
        display_value = str(value)
        if len(display_value) > 50:
            display_value = display_value[:47] + '...'
        
        return {
            'type': 'text',
            'value': value,
            'display': display_value,
            'css_class': 'text-cell'
        }
    
    def assemble_search_form(self, config, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble search form structure"""
        search_fields = []
        
        for field in config.fields:
            if field.searchable:
                search_fields.append({
                    'name': field.name,
                    'label': field.label,
                    'type': field.field_type.value,
                    'value': filters.get(field.name, ''),
                    'placeholder': f'Search {field.label.lower()}...'
                })
        
        return {
            'quick_search': {
                'name': 'search',
                'value': filters.get('search', ''),
                'placeholder': f'Search {", ".join(config.default_search_fields)}...'
            },
            'fields': search_fields,
            'date_range': {
                'start_date': filters.get('start_date', ''),
                'end_date': filters.get('end_date', '')
            }
        }
    
    def assemble_filter_options(self, config) -> Dict[str, List[Dict[str, Any]]]:
        """Assemble filter dropdown options"""
        filter_options = {}
        
        for field in config.fields:
            if field.filterable and field.options:
                filter_options[field.name] = field.options
        
        return filter_options
    
    def assemble_action_buttons(self, config) -> List[Dict[str, Any]]:
        """Assemble page-level action buttons"""
        buttons = []
        
        # Standard create button
        buttons.append({
            'id': 'create',
            'label': f'New {config.name}',
            'icon': 'fas fa-plus',
            'url': f'/universal/{config.entity_type}/create',
            'css_class': 'btn btn-primary'
        })
        
        # Export button
        buttons.append({
            'id': 'export',
            'label': 'Export',
            'icon': 'fas fa-download',
            'url': f'/universal/{config.entity_type}/export',
            'css_class': 'btn btn-outline'
        })
        
        return buttons
    
    def assemble_row_actions(self, config, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assemble action buttons for table row"""
        actions = []
        entity_id = item.get(config.primary_key)
        
        for action in config.actions:
            actions.append({
                'id': action.action_id,
                'label': action.label,
                'icon': action.icon,
                'url': f'/universal/{config.entity_type}/{entity_id}/{action.action_id}',
                'css_class': action.css_classes,
                'confirmation_required': action.confirmation_required,
                'confirmation_message': action.confirmation_message
            })
        
        return actions
    
    def assemble_pagination(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble pagination data"""
        return {
            'current_page': raw_data.get('page', 1),
            'total_pages': raw_data.get('pages', 1),
            'total_items': raw_data.get('total', 0),
            'per_page': raw_data.get('per_page', 25),
            'has_prev': raw_data.get('has_prev', False),
            'has_next': raw_data.get('has_next', False),
            'prev_page': raw_data.get('page', 1) - 1 if raw_data.get('has_prev') else None,
            'next_page': raw_data.get('page', 1) + 1 if raw_data.get('has_next') else None
        }
    
    def assemble_summary_stats(self, config, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble summary statistics"""
        items = raw_data.get('items', [])
        
        stats = {
            'total_count': raw_data.get('total', 0),
            'page_count': len(items)
        }
        
        # Entity-specific statistics
        if config.entity_type == "supplier_payments":
            total_amount = sum(float(item.get('payment_amount', 0)) for item in items)
            pending_count = len([item for item in items if item.get('payment_status') == 'pending'])
            
            stats.update({
                'total_amount': total_amount,
                'pending_count': pending_count,
                'average_amount': total_amount / len(items) if items else 0
            })
        
        return stats
    
    def assemble_detail_sections(self, config, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assemble detail view sections"""
        sections = []
        
        # Basic Information Section
        basic_fields = []
        for field in config.fields:
            if field.show_in_detail:
                field_data = {
                    'name': field.name,
                    'label': field.label,
                    'value': entity_data.get(field.name),
                    'display': self.format_detail_field_value(field, entity_data.get(field.name)),
                    'type': field.field_type.value,
                    'css_class': self._get_detail_field_css_class(field)
                }
                basic_fields.append(field_data)
        
        sections.append({
            'title': 'Basic Information',
            'fields': basic_fields
        })
        
        return sections
    
    def assemble_detail_actions(self, config, entity_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assemble detail view action buttons"""
        actions = []
        entity_id = entity_data.get(config.primary_key)
        
        for action in config.actions:
            actions.append({
                'id': action.action_id,
                'label': action.label,
                'icon': action.icon,
                'url': f'/universal/{config.entity_type}/{entity_id}/{action.action_id}',
                'css_class': action.css_classes
            })
        
        return actions
    
    def format_detail_field_value(self, field, value) -> str:
        """Format field value for detail display"""
        if value is None:
            return '-'
        
        if field.field_type.value == 'amount':
            return f'₹{float(value):,.2f}'
        elif field.field_type.value == 'date':
            if hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d')
        elif field.field_type.value == 'status_badge':
            status_option = next((opt for opt in field.options if opt['value'] == str(value)), None)
            if status_option:
                return f'<span class="status-badge {status_option["class"]}">{status_option["label"]}</span>'
        
        return str(value)
    
    def _get_row_css_class(self, config, item: Dict[str, Any]) -> str:
        """Get CSS class for table row based on item data"""
        css_classes = ['table-row']
        
        # Add status-based classes
        if config.entity_type == "supplier_payments":
            status = item.get('payment_status')
            if status == 'pending':
                css_classes.append('row-warning')
            elif status == 'completed':
                css_classes.append('row-success')
        
        return ' '.join(css_classes)
    
    def _get_detail_field_css_class(self, field) -> str:
        """Get CSS class for detail field"""
        css_classes = ['detail-field']
        
        if field.field_type.value == 'amount':
            css_classes.append('amount-field')
        elif field.field_type.value in ['patient_mrn', 'gst_number']:
            css_classes.append('code-field')
        elif field.is_phi:
            css_classes.append('phi-field')
        
        return ' '.join(css_classes)
    
    def _get_current_user(self):
        """Get current user safely"""
        try:
            from flask_login import current_user
            return current_user
        except:
            return None
```

### **Day 5: Testing and Validation**

#### **Step 5.1: Create Test Configuration**
Create `tests/test_universal_view_engine.py`:
```python
"""
Tests for universal view engine foundation
"""

import unittest
from app.config.entity_configurations import get_entity_config, list_entity_types
from app.config.field_definitions import FieldType
from app.engine.data_assembler import DataAssembler

class TestUniversalViewEngineFoundation(unittest.TestCase):
    """Test universal view engine foundation components"""
    
    def test_universal_view_engine_configuration_loading(self):
        """Test that entity configurations can be loaded"""
        # Test supplier payment configuration
        config = get_entity_config('supplier_payments')
        
        self.assertEqual(config.entity_type, 'supplier_payments')
        self.assertEqual(config.name, 'Supplier Payment')
        self.assertEqual(config.plural_name, 'Supplier Payments')
        self.assertTrue(len(config.fields) > 0)
        self.assertTrue(len(config.actions) > 0)
    
    def test_field_definitions(self):
        """Test field definitions"""
        config = get_entity_config('supplier_payments')
        
        # Check that payment_reference field exists and is configured correctly
        payment_ref_field = next((f for f in config.fields if f.name == 'payment_reference'), None)
        self.assertIsNotNone(payment_ref_field)
        self.assertEqual(payment_ref_field.field_type, FieldType.TEXT)
        self.assertTrue(payment_ref_field.show_in_list)
        self.assertTrue(payment_ref_field.searchable)
    
    def test_data_assembler(self):
        """Test data assembler functionality"""
        config = get_entity_config('supplier_payments')
        assembler = DataAssembler()
        
        # Test table column assembly
        columns = assembler.assemble_table_columns(config)
        self.assertIsInstance(columns, list)
        self.assertTrue(len(columns) > 0)
        
        # Check that columns have required properties
        for column in columns:
            self.assertIn('name', column)
            self.assertIn('label', column)
            self.assertIn('type', column)
    
    def test_entity_registry(self):
        """Test entity registry functionality"""
        entity_types = list_entity_types()
        self.assertIn('supplier_payments', entity_types)
    
    def test_search_form_assembly(self):
        """Test search form assembly"""
        config = get_entity_config('supplier_payments')
        assembler = DataAssembler()
        
        filters = {'search': 'test', 'payment_status': 'pending'}
        search_form = assembler.assemble_search_form(config, filters)
        
        self.assertIn('quick_search', search_form)
        self.assertIn('fields', search_form)
        self.assertEqual(search_form['quick_search']['value'], 'test')

if __name__ == '__main__':
    unittest.main()
```

#### **Step 5.2: Run Foundation Tests**
```bash
# Run foundation tests
python -m pytest tests/test_universal_view_engine.py -v

# Expected output:
# test_universal_view_engine_configuration_loading PASSED
# test_field_definitions PASSED  
# test_data_assembler PASSED
# test_entity_registry PASSED
# test_search_form_assembly PASSED
```

---

## 📋 **Week 1 Completion Checklist**

### **Files Created**
- [ ] `app/engine/__init__.py` - View engine package initialization
- [ ] `app/engine/universal_view_engine.py` - Core view engine orchestrator
- [ ] `app/engine/universal_components.py` - Universal view/service components
- [ ] `app/engine/data_assembler.py` - Backend data assembly logic
- [ ] `app/config/entity_configurations.py` - Entity configuration system
- [ ] `app/config/field_definitions.py` - Field type definitions
- [ ] `tests/test_universal_view_engine.py` - Foundation tests

### **Functionality Verified**
- [ ] Entity configuration system loads correctly
- [ ] Supplier payment configuration is complete and valid
- [ ] Data assembler can build table columns and search forms
- [ ] Universal view engine can load entity configurations
- [ ] All foundation tests pass

### **Week 1 Success Criteria**
- [ ] Universal view engine core is functional
- [ ] Entity configuration system is working
- [ ] Data assembler can format data structures
- [ ] Foundation is ready for entity service integration
- [ ] Code is committed to feature branch

---

**Ready for Week 2: Entity Service Implementation!** 🚀

Would you like me to continue with the Week 2 implementation plan, or do you have any questions about the Week 1 foundation setup?