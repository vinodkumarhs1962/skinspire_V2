"""
Enhanced Field Definitions - Handles Complex Real-World Scenarios
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Type
from flask_wtf import FlaskForm

class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    AMOUNT = "amount"
    CURRENCY = "currency"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    STATUS_BADGE = "status_badge"
    BOOLEAN = "boolean"
    UUID = "uuid"
    REFERENCE = "reference"
    CUSTOM = "custom"                    # NEW: For complex custom rendering
    MULTI_METHOD_AMOUNT = "multi_method_amount"  # NEW: For payment method breakdown
    BREAKDOWN_DISPLAY = "breakdown_display"      # NEW: For complex field combinations
    ENTITY_SEARCH = "entity_search"        # ✅ NEW: Searchable entity field
    MULTI_ENTITY_SEARCH = "multi_entity_search"  # ✅ NEW: Multiple entity selection
    TEXTAREA = "textarea"  
    JSONB = "jsonb"      

class ComplexDisplayType(Enum):
    """Types of complex display components"""
    MULTI_METHOD_PAYMENT = "multi_method_payment"
    BREAKDOWN_AMOUNTS = "breakdown_amounts"
    CONDITIONAL_DISPLAY = "conditional_display"
    DYNAMIC_CONTENT = "dynamic_content"

@dataclass
class CustomRenderer:
    """Custom renderer for complex fields"""
    template: str                       # Template file or inline template
    context_function: Optional[Callable] = None  # Function to build context
    css_classes: Optional[str] = None
    javascript: Optional[str] = None

@dataclass
class FilterConfiguration:
    """Enhanced filter configuration"""
    filter_type: str                    # 'select', 'multi_select', 'date_range', etc.
    form_field_name: str               # WTForms field name
    parameter_variations: List[str] = field(default_factory=list)  # Alternative parameter names
    backward_compatibility: bool = True
    dynamic_options_function: Optional[Callable] = None
    custom_filter_template: Optional[str] = None
    javascript_behavior: Optional[str] = None

@dataclass  
class EntitySearchConfiguration:
    """Configuration for searchable entity fields"""
    target_entity: str                      # Entity to search (e.g., 'suppliers', 'patients')
    search_fields: List[str]               # Fields to search in (e.g., ['name', 'code'])
    display_template: str                   # How to display results (e.g., "{name} ({code})")
    min_chars: int = 2                     # Minimum characters to trigger search
    max_results: int = 10                  # Maximum results to show
    model_path: Optional[str] = None  # e.g., 'app.models.master.Supplier'
    relationship_joins: Dict[str, str] = field(default_factory=dict)
    service_method: str = "search_entities" # Backend method to call
    additional_filters: Dict[str, Any] = None  # Extra filters (e.g., status='active')
    sort_field: str = "name"               # Default sort field
    cache_timeout: int = 300               # Cache results for 5 minutes
    placeholder_template: str = "Search {entity}..."  # Dynamic placeholder

    def get(self, key: str, default=None):
        """Dictionary-like get method for compatibility"""
        try:
            return getattr(self, key, default)
        except AttributeError:
            return default

@dataclass
class ActionConfiguration:
    """Enhanced action configuration"""
    id: str
    label: str
    icon: str
    button_type: str
    permission: Optional[str] = None
    conditions: Optional[Dict] = None
    url_pattern: Optional[str] = None
    javascript_handler: Optional[str] = None  # Custom JavaScript function
    confirmation_message: Optional[str] = None
    custom_template: Optional[str] = None

@dataclass
class FieldDefinition:
    """Enhanced field definition for complex scenarios"""
    name: str
    label: str
    field_type: FieldType
    show_in_list: bool = False
    show_in_detail: bool = True
    searchable: bool = False
    sortable: bool = False
    filterable: bool = False
    required: bool = False
    readonly: bool = False
    
    # Enhanced display options
    custom_renderer: Optional[CustomRenderer] = None
    complex_display_type: Optional[ComplexDisplayType] = None
    conditional_display: Optional[Dict] = None     # Show/hide based on other fields
    
    # Form integration
    form_field_name: Optional[str] = None          # WTForms field name
    form_field_type: Optional[str] = None          # WTForms field type
    
    # Filter configuration
    filter_config: Optional[FilterConfiguration] = None
    
    # Advanced options
    options: Optional[List[Dict]] = None
    dynamic_options_function: Optional[Callable] = None
    validation: Optional[Dict] = None
    format_pattern: Optional[str] = None
    help_text: Optional[str] = None
    
    # CSS and styling
    css_classes: Optional[str] = None
    table_column_style: Optional[str] = None       # Inline styles for table columns
    width: Optional[str] = None
    align: Optional[str] = None
    
    # JavaScript integration
    javascript_behavior: Optional[str] = None
    custom_events: Optional[List[str]] = None

    # Entity search configuration
    entity_search_config: Optional[EntitySearchConfiguration] = None
    
    # Enhanced autocomplete options
    autocomplete_enabled: bool = False
    autocomplete_min_chars: int = 2
    autocomplete_source: Optional[str] = None  # 'backend', 'static', 'hybrid'

@dataclass
class EntityConfiguration:
    """Enhanced entity configuration for complex real-world scenarios"""
    # REQUIRED PARAMETERS FIRST (no defaults)
    entity_type: str
    service_name: str
    name: str
    plural_name: str
    table_name: str
    primary_key: str
    title_field: str
    subtitle_field: str
    icon: str
    # Field and action definitions
    fields: List[FieldDefinition]        # ✅ MOVE BEFORE defaults
    actions: List[ActionConfiguration]   # ✅ MOVE BEFORE defaults
    
    # OPTIONAL PARAMETERS (with defaults)
    # Form integration
    form_class: Optional[Type[FlaskForm]] = None   # WTForms class
    form_population_functions: List[Callable] = field(default_factory=list)
    
    # Export functionality
    enable_export: bool = True
    export_endpoint: Optional[str] = None
    export_filename_pattern: Optional[str] = None
    
    # Advanced features
    enable_save_filters: bool = False
    enable_filter_presets: bool = True
    enable_complex_search: bool = True
    
    # JavaScript integration
    custom_javascript_files: List[str] = field(default_factory=list)
    javascript_initialization: Optional[str] = None
    
    # Template customization
    custom_templates: Dict[str, str] = field(default_factory=dict)
    template_blocks: Dict[str, str] = field(default_factory=dict)
    
    # CSS integration
    table_css_class: str = "data-table"
    card_css_class: str = "info-card"
    filter_css_class: str = "filter-card"
    custom_css_files: List[str] = field(default_factory=list)
    
    # Display settings
    items_per_page: int = 20
    default_sort_field: str = "created_at"
    default_sort_order: str = "desc"
    fixed_table_layout: bool = False               # For complex table layouts
    
    
    # Summary card configuration
    summary_cards: Optional[List[Dict]] = None
    
    # Complex features
    multi_method_display: bool = False             # Enable payment method breakdown
    complex_filter_behavior: bool = False          # Enable advanced filtering
    scroll_behavior_config: Optional[Dict] = None  # Scroll restoration settings