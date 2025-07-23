"""
Core Definitions - Building blocks for the configuration system
File: app/config/core_definitions.py

COMPREHENSIVE VERSION: Includes ALL parameters from both field_definitions.py 
and entity_configurations.py to ensure complete backward compatibility
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Type, Union
from flask_wtf import FlaskForm
from flask import url_for

# =============================================================================
# CORE ENUMS - Complete type definitions from both files
# =============================================================================

class FieldType(Enum):
    """All field types from both files combined"""
    # Text types
    TEXT = "text"
    TEXTAREA = "textarea"
    EMAIL = "email"
    
    # Numeric types
    NUMBER = "number"
    AMOUNT = "amount"
    CURRENCY = "currency"
    
    # Date/Time types
    DATE = "date"
    DATETIME = "datetime"
    
    # Selection types
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    BOOLEAN = "boolean"
    STATUS_BADGE = "status_badge"
    
    # Reference types
    UUID = "uuid"
    REFERENCE = "reference"
    ENTITY_SEARCH = "entity_search"
    MULTI_ENTITY_SEARCH = "multi_entity_search"
    
    # Data types
    JSONB = "jsonb"
    
    # Special/Complex types
    CUSTOM = "custom"
    MULTI_METHOD_AMOUNT = "multi_method_amount"
    BREAKDOWN_DISPLAY = "breakdown_display"

class ButtonType(Enum):
    """Button visual styles from entity_configurations.py"""
    PRIMARY = "btn-primary"
    SECONDARY = "btn-secondary"  # Added for completeness
    OUTLINE = "btn-outline"
    WARNING = "btn-warning"
    DANGER = "btn-danger"
    SUCCESS = "btn-success"
    INFO = "btn-info"  # Added for future use

class ComplexDisplayType(Enum):
    """Complex display component types from field_definitions.py"""
    MULTI_METHOD_PAYMENT = "multi_method_payment"
    BREAKDOWN_AMOUNTS = "breakdown_amounts"
    CONDITIONAL_DISPLAY = "conditional_display"
    DYNAMIC_CONTENT = "dynamic_content"

# =============================================================================
# CORE DATA CLASSES - Complete field definition with ALL parameters
# =============================================================================

@dataclass
class FieldDefinition:
    """
    COMPREHENSIVE Field Definition - Includes ALL parameters from both files
    This ensures complete backward compatibility
    """
    # ========== REQUIRED PARAMETERS ==========
    name: str                          # Database field name
    label: str                         # Display label
    field_type: FieldType             # Data type
    
    # ========== DISPLAY CONTROL ==========
    show_in_list: bool = False        # Show in list/table view
    show_in_detail: bool = True       # Show in detail/view page
    show_in_form: bool = True         # Show in create/edit forms ✓ FROM entity_configurations
    
    # ========== BEHAVIOR CONTROL ==========
    searchable: bool = False          # Enable text search on this field
    sortable: bool = False            # Enable column sorting
    filterable: bool = False          # Enable filtering
    required: bool = False            # Form validation requirement
    readonly: bool = False            # Read-only in forms
    virtual: bool = False             # Computed/derived field ✓ FROM usage
    
    # ========== FORM CONFIGURATION ==========
    placeholder: str = ""             # Input placeholder text ✓ FROM entity_configurations
    help_text: str = ""               # Help text below field
    default: Optional[Any] = None     # Default value ✓ FROM usage
    options: List[Dict] = field(default_factory=list)  # Dropdown options
    
    # ========== VALIDATION ==========
    validation_pattern: Optional[str] = None   # Regex pattern ✓ FROM docs
    min_value: Optional[float] = None          # Minimum numeric value ✓ FROM docs
    max_value: Optional[float] = None          # Maximum numeric value ✓ FROM docs
    validation: Optional[Dict] = None          # Custom validation rules ✓ FROM field_definitions
    
    # ========== RELATIONSHIPS ==========
    related_field: Optional[str] = None        # Foreign key field
    related_display_field: Optional[str] = None # Display field for relationships ✓ FROM docs
    
    # ========== DISPLAY CUSTOMIZATION ==========
    width: Optional[str] = None               # Column width
    align: Optional[str] = None               # Text alignment
    css_classes: Optional[str] = None         # Custom CSS classes
    table_column_style: Optional[str] = None  # Inline styles for tables
    format_pattern: Optional[str] = None      # Display format pattern
    
    # ========== ADVANCED DISPLAY ==========
    custom_renderer: Optional['CustomRenderer'] = None     # Custom rendering object
    complex_display_type: Optional[ComplexDisplayType] = None  # Complex display type
    conditional_display: Optional[Dict] = None              # Show/hide conditions
    
    # ========== AUTOCOMPLETE ==========
    autocomplete_enabled: bool = False
    autocomplete_source: Optional[str] = None  # 'backend', 'static', 'hybrid'
    autocomplete_min_chars: int = 2            # ✓ FROM field_definitions
    entity_search_config: Optional['EntitySearchConfiguration'] = None
    
    # ========== FILTER CONFIGURATION ==========
    filter_aliases: List[str] = field(default_factory=list)  # Alternative parameter names
    filter_type: str = "exact"        # Filter match type: exact, range, contains, etc.
    filter_config: Optional['FilterConfiguration'] = None
    
    # ========== FORM INTEGRATION ==========
    form_field_name: Optional[str] = None      # WTForms field name override
    form_field_type: Optional[str] = None      # WTForms field type override
    
    # ========== JAVASCRIPT/DYNAMIC ==========
    javascript_behavior: Optional[str] = None   # Custom JS behavior
    custom_events: Optional[List[str]] = None   # Custom JS events
    dynamic_options_function: Optional[Callable] = None  # Dynamic options loader

@dataclass
class ActionDefinition:
    """
    COMPREHENSIVE Action Definition - From entity_configurations.py
    Includes all parameters for backward compatibility
    """
    # ========== REQUIRED PARAMETERS ==========
    id: str                           # Unique action identifier
    label: str                        # Button/link text
    icon: str                         # FontAwesome icon class
    button_type: ButtonType          # Visual style
    
    # ========== ROUTING ==========
    route_name: Optional[str] = None      # Flask route name
    route_params: Optional[Dict] = None   # Route parameters
    url_pattern: Optional[str] = None     # URL pattern (deprecated but kept for compatibility)
    
    # ========== PERMISSIONS & BEHAVIOR ==========
    permission: Optional[str] = None      # Required permission
    confirmation_required: bool = False   # Show confirmation dialog
    confirmation_message: str = ""        # Confirmation message
    
    # ========== DISPLAY CONTROL ==========
    show_in_list: bool = True            # Show in list view actions
    show_in_detail: bool = True          # Show in detail view
    show_in_toolbar: bool = False        # Show in page toolbar
    
    # ========== ADVANCED FEATURES ==========
    conditions: Optional[Dict[str, Any]] = None    # Conditional display rules
    custom_handler: Optional[str] = None           # Custom handler function name
    javascript_handler: Optional[str] = None       # JS function name
    custom_template: Optional[str] = None          # Custom template override

    def get_url(self, item: Dict, entity_config=None) -> str:
        """
        Generate URL for this action based on configuration
        
        Smart mapping: {id} automatically maps to the entity's primary key field
        
        Args:
            item: Dictionary containing the data item (e.g., payment record)
            entity_config: Optional EntityConfiguration for primary key lookup
            
        Returns:
            Generated URL string
        """
        try:
            if self.route_name:
                # Build kwargs from route_params
                kwargs = {}
                if self.route_params:
                    for param, template in self.route_params.items():
                        if isinstance(template, str) and template.startswith('{') and template.endswith('}'):
                            # Extract field name from template {field_name}
                            field_name = template[1:-1]
                            
                            # ✅ SMART MAPPING: {id} → primary key field
                            if field_name == 'id' and entity_config and hasattr(entity_config, 'primary_key'):
                                actual_field_name = entity_config.primary_key
                                value = item.get(actual_field_name, '')
                                kwargs[param] = str(value) if value else ''
                            # Handle nested fields with dot notation
                            elif '.' in field_name:
                                # e.g., {supplier.supplier_id}
                                parts = field_name.split('.')
                                value = item
                                for part in parts:
                                    if isinstance(value, dict):
                                        value = value.get(part, '')
                                    else:
                                        value = ''
                                        break
                                kwargs[param] = str(value) if value else ''
                            else:
                                # Simple field lookup with safe get
                                value = item.get(field_name, '')
                                kwargs[param] = str(value) if value else ''
                        else:
                            # Static value
                            kwargs[param] = template
                
                # Generate URL using Flask's url_for
                try:
                    from flask import url_for
                    return url_for(self.route_name, **kwargs)
                except Exception as url_error:
                    # If url_for fails (e.g., outside request context), return safe fallback
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"url_for failed for {self.route_name}: {url_error}")
                    return '#'
                
            elif self.url_pattern:
                # Simple string replacement for URL patterns
                url = self.url_pattern
                
                # Replace all {field_name} patterns in the URL
                import re
                pattern = r'\{([^}]+)\}'
                
                def replace_field(match):
                    field_name = match.group(1)
                    
                    # ✅ SMART MAPPING: {id} → primary key field
                    if field_name == 'id' and entity_config and hasattr(entity_config, 'primary_key'):
                        actual_field_name = entity_config.primary_key
                        value = item.get(actual_field_name, '')
                        return str(value) if value else ''
                    # Handle nested fields with dot notation
                    elif '.' in field_name:
                        parts = field_name.split('.')
                        value = item
                        for part in parts:
                            if isinstance(value, dict):
                                value = value.get(part, '')
                            else:
                                value = ''
                                break
                        return str(value) if value else ''
                    else:
                        # Safe get with empty string default
                        value = item.get(field_name, '')
                        return str(value) if value else ''
                
                url = re.sub(pattern, replace_field, url)
                return url
                
            else:
                # No URL configuration
                return '#'
                
        except Exception as e:
            # Log error and return safe fallback
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error generating URL for action {self.id}: {str(e)}")
            return '#'

# Note: ActionConfiguration from field_definitions.py is simpler
# We use ActionDefinition as it's more complete

# =============================================================================
# UTILITY CLASSES - From field_definitions.py
# =============================================================================

@dataclass
class CustomRenderer:
    """Configuration for custom field rendering"""
    template: str                              # Template path or inline template
    context_function: Optional[Callable] = None # Function to build context
    css_classes: Optional[str] = None          # Additional CSS classes
    javascript: Optional[str] = None           # Associated JavaScript

@dataclass
class FilterConfiguration:
    """Enhanced filter configuration for complex filtering needs"""
    filter_type: str                          # 'select', 'multi_select', 'date_range', etc.
    form_field_name: str                      # WTForms field name
    parameter_variations: List[str] = field(default_factory=list)  # URL parameter aliases
    backward_compatibility: bool = True       # Support old parameter names
    dynamic_options_function: Optional[Callable] = None  # Dynamic option loader
    custom_filter_template: Optional[str] = None        # Custom filter template
    javascript_behavior: Optional[str] = None           # Custom JS behavior

@dataclass
class EntitySearchConfiguration:
    """Configuration for searchable entity fields"""
    target_entity: str                        # Entity to search (e.g., 'suppliers')
    search_fields: List[str]                  # Fields to search in
    display_template: str                     # Display format (e.g., "{name} ({code})")
    min_chars: int = 2                        # Minimum characters to trigger search
    max_results: int = 10                     # Maximum results to return
    model_path: Optional[str] = None          # Model import path
    relationship_joins: Dict[str, str] = field(default_factory=dict)  # Join config
    service_method: str = "search_entities"   # Backend method to call
    additional_filters: Optional[Dict[str, Any]] = None  # Extra filters
    sort_field: str = "name"                  # Default sort field
    cache_timeout: int = 300                  # Cache duration in seconds
    placeholder_template: str = "Search {entity}..."  # Search box placeholder
    
    def get(self, key: str, default=None):
        """Dictionary-like interface for backward compatibility"""
        try:
            return getattr(self, key, default)
        except AttributeError:
            return default

# =============================================================================
# ENTITY CONFIGURATION - Comprehensive version from both files
# =============================================================================

@dataclass
class EntityConfiguration:
    """
    COMPREHENSIVE Entity Configuration - Merged from both files
    Includes ALL parameters to ensure complete backward compatibility
    
    IMPORTANT: Required parameters (no defaults) MUST come before optional parameters
    """
    # ========== ALL REQUIRED PARAMETERS FIRST ==========
    entity_type: str                      # Unique entity identifier
    name: str                            # Singular display name
    plural_name: str                     # Plural display name
    service_name: str                    # Service identifier
    table_name: str                      # Database table name
    primary_key: str                     # Primary key field name
    title_field: str                     # Field for titles/headers
    subtitle_field: str                  # Field for subtitles
    icon: str                           # FontAwesome icon class
    page_title: str                     # Page header
    description: str                    # Page description
    searchable_fields: List[str]        # Text search fields
    default_sort_field: str             # Default sort column
    default_sort_direction: str         # Default sort direction
    fields: List[FieldDefinition]       # Field definitions
    actions: List[ActionDefinition]     # Action definitions
    summary_cards: List[Dict]           # Summary statistics
    permissions: Dict[str, str]         # Permission mapping
    
    # ========== ALL OPTIONAL PARAMETERS AFTER ==========
    # Database
    model_class: Optional[str] = None
    
    # Sort aliases
    default_sort_order: str = "desc"
    
    # CSS Classes
    filter_css_class: str = "universal-filter-card"
    table_css_class: str = "universal-data-table"
    card_css_class: str = "info-card"
    custom_css_files: List[str] = field(default_factory=list)
    
    # Feature Flags
    enable_saved_filter_suggestions: bool = True
    enable_auto_submit: bool = False
    enable_export: bool = True
    enable_save_filters: bool = False
    enable_filter_presets: bool = True
    enable_complex_search: bool = True
    
    # Export Configuration
    export_endpoint: Optional[str] = None
    export_filename_pattern: Optional[str] = None
    
    # Form Integration
    form_class: Optional[Type[FlaskForm]] = None
    form_population_functions: List[Callable] = field(default_factory=list)
    
    # JavaScript Integration
    custom_javascript_files: List[str] = field(default_factory=list)
    javascript_initialization: Optional[str] = None
    
    # Template Customization
    custom_templates: Dict[str, str] = field(default_factory=dict)
    template_blocks: Dict[str, str] = field(default_factory=dict)
    template_overrides: Optional[Dict[str, str]] = None
    
    # Display Settings
    items_per_page: int = 20
    fixed_table_layout: bool = False
    
    # Complex Features
    multi_method_display: bool = False
    complex_filter_behavior: bool = False
    scroll_behavior_config: Optional[Dict] = None
    
    # Filter Configuration
    filter_category_mapping: Optional[Dict] = None
    default_filters: Optional[Dict] = None
    category_configs: Optional[Dict] = None
    
    # Field References
    primary_date_field: Optional[str] = None
    primary_amount_field: Optional[str] = None
    
    # Advanced Configuration
    css_classes: Optional[Dict[str, str]] = None
    validation_rules: Optional[Dict[str, Any]] = None

# =============================================================================
# ENTITY-SPECIFIC HELPER CLASSES
# =============================================================================

@dataclass
class EntityFilterConfiguration:
    """Configuration for entity filter dropdowns - FROM entity_configurations.py"""
    entity_type: str
    filter_mappings: Dict[str, Dict] = field(default_factory=dict)

# =============================================================================
# TYPE ALIASES AND COMPATIBILITY
# =============================================================================

# For backward compatibility with different import styles
FieldDefinitionType = FieldDefinition
ActionDefinitionType = ActionDefinition
EntityConfigurationType = EntityConfiguration

# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_field_definition(field_def: FieldDefinition) -> List[str]:
    """Validate a field definition for common issues"""
    errors = []
    
    if not field_def.name:
        errors.append("Field name is required")
    
    if not field_def.label:
        errors.append("Field label is required")
    
    if field_def.min_value is not None and field_def.max_value is not None:
        if field_def.min_value > field_def.max_value:
            errors.append(f"min_value ({field_def.min_value}) cannot be greater than max_value ({field_def.max_value})")
    
    if field_def.required and field_def.readonly:
        errors.append("Field cannot be both required and readonly")
    
    return errors

def validate_action_definition(action_def: ActionDefinition) -> List[str]:
    """Validate an action definition for common issues"""
    errors = []
    
    if not action_def.id:
        errors.append("Action id is required")
    
    if not action_def.label:
        errors.append("Action label is required")
    
    if not action_def.route_name and not action_def.url_pattern:
        errors.append("Either route_name or url_pattern is required")
    
    if action_def.confirmation_required and not action_def.confirmation_message:
        errors.append("Confirmation message is required when confirmation_required is True")
    
    return errors