"""
Core Definitions - Building blocks for the configuration system
File: app/config/core_definitions.py

COMPREHENSIVE VERSION: Includes ALL parameters from both field_definitions.py 
and entity_configurations.py to ensure complete backward compatibility

Enhanced Core Definitions - Building blocks for Universal Engine v3.0
File: app/config/core_definitions.py

Includes ALL v2.0 enhancements + v2.1 view template enhancements
Complete backward compatibility with existing configurations

"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Type, Union
from flask_wtf import FlaskForm
from flask import url_for
import re

from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

# =============================================================================
# CORE ENUMS - Complete type definitions from both files
# =============================================================================

class EntityCategory(Enum):
    """Classification of entities for operation scope control"""
    MASTER = "master"          # Simple entities with full CRUD support
    TRANSACTION = "transaction" # Complex entities with read-only in Universal Engine
    REPORT = "report"          # Future: read-only report entities
    LOOKUP = "lookup"          # Future: simple lookup tables

class CRUDOperation(Enum):
    """Available CRUD operations in Universal Engine"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    VIEW = "view"
    DOCUMENT = "document"
    EXPORT = "export"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"

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
    INTEGER = "integer"
    PERCENTAGE = "percentage"
    
    # Date/Time types
    DATE = "date"
    DATETIME = "datetime"
    
    # Selection types
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    BOOLEAN = "boolean"
    STATUS_BADGE = "status_badge"
    STATUS = "status"
    DECIMAL = "decimal"
    
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
    # Payment related
    MULTI_METHOD_PAYMENT = "multi_method_payment"   # Mixed payment display
    BREAKDOWN_AMOUNTS = "breakdown_amounts"         # Amount breakdowns
    # Display logic
    CONDITIONAL_DISPLAY = "conditional_display"     # Show/hide based on conditions
    DYNAMIC_CONTENT = "dynamic_content"             # Dynamic content generation
    # Entity reference display (FIX: Add this missing value)
    ENTITY_REFERENCE = "entity_reference"           # Display related entity info

class LayoutType(Enum):
    """View template layout types"""
    SIMPLE = "simple"
    TABBED = "tabbed"
    ACCORDION = "accordion"
    MASTER_DETAIL = "master_detail"

class ActionDisplayType(Enum):
    """How an action should be displayed in the UI"""
    BUTTON = "button"          # Standalone button
    DROPDOWN_ITEM = "dropdown" # Item in dropdown menu  
    BOTH = "both"             # Show in both places
    HIDDEN = "hidden"         # Not shown (API only)

class DocumentType(Enum):
    """Types of documents that can be generated"""
    RECEIPT = "receipt"
    INVOICE = "invoice"
    REPORT = "report"
    STATEMENT = "statement"
    CERTIFICATE = "certificate"
    LETTER = "letter"
    LABEL = "label"

class PrintLayoutType(Enum):
    """Print layout types that reuse view components"""
    SIMPLE = "simple"           # Uses layout_simple.html
    TABBED = "tabbed"           # Uses layout_tabbed.html (tabs become sections)
    ACCORDION = "accordion"     # Uses layout_accordion.html (all sections expanded)
    SIMPLE_WITH_HEADER = "simple_with_header"  # Simple layout with enhanced header
    COMPACT = "compact"         # Condensed version for receipts

class PageSize(Enum):
    """Standard page sizes for documents"""
    A4 = "A4"
    A5 = "A5"
    LETTER = "letter"
    LEGAL = "legal"
    THERMAL_80MM = "thermal_80"
    THERMAL_58MM = "thermal_58"

class Orientation(Enum):
    """Page orientation"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"

class DocumentSectionType(Enum):
    """Document section types"""
    HEADER = "header"
    BODY = "body"
    TABLE = "table"
    SUMMARY = "summary"
    FOOTER = "footer"
    SIGNATURE = "signature"

class ExportFormat(Enum):
    """Supported export formats"""
    PDF = "pdf"
    HTML = "html"
    PRINT = "print"
    EXCEL = "excel"
    WORD = "word"
    CSV = "csv"

# =============================================================================
# VIEW SECTION DEFINITIONS - Eliminates Hardcoded Values
# =============================================================================

@dataclass
class SectionDefinition:
    """
    Configurable section definition - ELIMINATES hardcoded section names
    Replaces hardcoded 'Key Information', 'Details', etc.
    """
    key: str                              # Unique section identifier
    title: str                            # Display title
    icon: str                             # FontAwesome icon class
    columns: int = 2                      # Number of columns
    order: int = 0                        # Display order
    css_class: Optional[str] = None       # Custom CSS class
    collapsible: bool = False             # Can collapse
    default_collapsed: bool = False       # Start collapsed  # ADD THIS
    show_divider: bool = True             # Show bottom divider
    conditional_display: Optional[str] = None  # Display condition

@dataclass 
class TabDefinition:
    """
    Configurable tab definition - ELIMINATES hardcoded tab structures
    """
    key: str                           # Unique tab identifier
    label: str                         # Tab display name
    icon: str                          # Tab icon
    sections: Dict[str, SectionDefinition] = field(default_factory=dict)
    order: int = 0                     # Tab order
    default_active: bool = False       # Default active tab
    conditions: Optional[str] = None   # Show/hide conditions

@dataclass
class ViewLayoutConfiguration:
    """Complete layout configuration for view templates"""
    type: LayoutType = LayoutType.SIMPLE
    responsive_breakpoint: str = 'md'  # Bootstrap breakpoint
    
    # Section-based configuration (for simple/accordion layouts)
    sections: Dict[str, SectionDefinition] = field(default_factory=dict)
    
    # Tab-based configuration (for tabbed layout)
    tabs: Dict[str, TabDefinition] = field(default_factory=dict)
    default_tab: Optional[str] = None
    sticky_tabs: bool = False
    
    # Master-detail configuration
    master_panel_width: str = '30%'
    master_fields: List[str] = field(default_factory=list)
    
    # Auto-generation settings
    auto_generate_sections: bool = True  # Auto-create sections if not defined
    default_section_columns: int = 2     # Default column count
    fallback_section_title: str = "Information"  # Default section name
    fallback_section_icon: str = "fas fa-info-circle"  # Default icon

    # ========== NEW PARAMETERS TO ADD ==========
    # Action buttons configuration
    enable_print: bool = False          # Enable print button in view
    enable_export: bool = False         # Enable export button in view
    
    # Header configuration
    header_config: Optional[Dict[str, Any]] = None  # Header display configuration with primary_field, status_field, etc.


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
    show_in_edit: bool = False        # Show in edit view only
    
    # ========== NEW: VIEW ORGANIZATION (v2.1) ==========
    tab_group: Optional[str] = None    # Which tab (eliminates hardcoding)
    section: Optional[str] = None      # Which section within tab
    view_order: int = 0                # Display order within section
    columns_span: Optional[int] = None # Grid span (1-12, default auto)
    conditional_display: Optional[str] = None  # Show/hide condition

    # ========== BEHAVIOR CONTROL ==========
    searchable: bool = False          # Enable text search on this field
    sortable: bool = False            # Enable column sorting
    filterable: bool = False          # Enable filtering
    required: bool = False            # Form validation requirement
    readonly: bool = False            # Read-only in forms
    virtual: bool = False             # Computed/derived field ✓ FROM usage
    
    # ========== VIRTUAL FIELD MAPPING ==========
    virtual_target: Optional[str] = None    # Target JSONB field (e.g., 'contact_info')
    virtual_key: Optional[str] = None       # Key within JSONB (e.g., 'phone')
    virtual_transform: Optional[str] = None # Custom transform function name

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
    default_value: Optional[Any] = None        # Default value for the field
    unique: bool = False
    validators: List[str] = field(default_factory=list)
    step: Optional[float] = None             # Step increment for number inputs
    
    # ========== RELATIONSHIPS ==========
    related_field: Optional[str] = None        # Foreign key field
    related_display_field: Optional[str] = None # Display field for relationships ✓ FROM docs
    
    # ========== DISPLAY CUSTOMIZATION ==========
    width: Optional[str] = None               # Column width
    align: Optional[str] = None               # Text alignment
    css_classes: Optional[str] = None         # Custom CSS classes
    table_column_style: Optional[str] = None  # Inline styles for tables
    format_pattern: Optional[str] = None      # Display format pattern
    rows: Optional[int] = None
    
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
    
    # ========== NEW PARAMETERS TO ADD ==========
    display_type: ActionDisplayType = ActionDisplayType.DROPDOWN_ITEM  # NEW: How to display
    button_group: Optional[str] = None   # NEW: Group buttons together

    # ========== ADVANCED FEATURES ==========
    conditions: Optional[Dict[str, Any]] = None    # Conditional display rules
    custom_handler: Optional[str] = None           # Custom handler function name
    javascript_handler: Optional[str] = None       # JS function name
    custom_template: Optional[str] = None          # Custom template override
    order: int = 999                               # NEW: Display order for sorting


    # ========== NEW: EXPRESSION-BASED CONDITIONAL DISPLAY ==========
    conditional_display: Optional[str] = None    # Expression-based display condition

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
                    
                    logger.debug(f"🔍 [URL_REPLACE_DEBUG] Processing placeholder: {field_name}")

                    # ✅ NEW: Handle {entity_type} placeholder
                    if field_name == 'entity_type' and entity_config and hasattr(entity_config, 'entity_type'):
                        result = str(entity_config.entity_type)
                        logger.debug(f"🔍 [URL_REPLACE_DEBUG] Replaced {field_name} with: {result}")
                        return result

                    # ✅ SMART MAPPING: {id} → primary key field
                    elif field_name == 'id' and entity_config and hasattr(entity_config, 'primary_key'):
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
            logger.error(f"❌ [ACTION_URL_ERROR] Error generating URL for action {self.id}: {str(e)}")
            logger.error(f"❌ [ACTION_URL_ERROR] Item data: {item}")
            logger.error(f"❌ [ACTION_URL_ERROR] Entity config: {entity_config}")
            return '#'

# Note: ActionConfiguration from field_definitions.py is simpler
# We use ActionDefinition as it's more complete

@dataclass
class DocumentFieldMapping:
    """Maps entity field to document display"""
    entity_field: str                          # Field name from entity
    document_label: Optional[str] = None       # Override label for document
    format_type: Optional[str] = None          # Special formatting (currency, date, etc.)
    show_if_empty: bool = True                 # Show field even if value is empty
    default_value: Optional[str] = None        # Default if field is empty
    prefix: Optional[str] = None               # Text before value
    suffix: Optional[str] = None               # Text after value

@dataclass
class TableColumnConfig:
    """Configuration for table columns in documents"""
    field_name: str                           # Field name from entity
    label: str                                # Column header
    width: Optional[str] = None               # Column width (e.g., "20%", "100px")
    align: str = "left"                       # Text alignment
    format_type: Optional[str] = None         # Formatting type
    total: bool = False                       # Include in totals row

@dataclass
class DocumentSection:
    """Configuration for a document section"""
    section_type: DocumentSectionType
    title: Optional[str] = None               # Section title
    fields: List[DocumentFieldMapping] = field(default_factory=list)
    
    # For table sections
    source_field: Optional[str] = None        # Entity field containing table data
    columns: List[TableColumnConfig] = field(default_factory=list)
    show_totals: bool = False
    
    # Layout options
    columns_count: int = 1                    # Number of columns for fields
    css_class: Optional[str] = None           # Custom CSS class
    show_border: bool = False
    
    # Conditional display
    show_condition: Optional[str] = None      # e.g., "item.status == 'approved'"

@dataclass
class DocumentConfiguration:
    """Complete configuration for a document type"""
    # Basic Information
    enabled: bool = True
    document_type: DocumentType = DocumentType.RECEIPT
    title: str = "Document"
    subtitle: Optional[str] = None
    
    # Print layout configuration
    print_layout_type: PrintLayoutType = PrintLayoutType.SIMPLE_WITH_HEADER
    include_header_section: bool = True  # Include entity header info
    include_action_buttons: bool = False  # Hide action buttons in print

    # Page Setup
    page_size: PageSize = PageSize.A4
    orientation: Orientation = Orientation.PORTRAIT
    margins: Dict[str, str] = field(default_factory=lambda: {
        "top": "20mm", "right": "15mm", "bottom": "20mm", "left": "15mm"
    })
    
    # Document Sections
    sections: List[DocumentSection] = field(default_factory=list)
    
    # Header Configuration
    show_logo: bool = True
    logo_position: str = "left"  # left, center, right
    show_company_info: bool = True
    header_fields: List[DocumentFieldMapping] = field(default_factory=list)
    header_text: Optional[str] = None
    
    # Footer Configuration
    show_footer: bool = True
    footer_text: Optional[str] = None
    show_page_numbers: bool = False
    show_print_info: bool = True
    
    # Status-specific footer text (NEW)
    status_footer_text: Optional[Dict[str, str]] = None
    # Example: {"approved": "This is an approved document", "draft": "This is a draft document"}

    # Terms and Conditions Configuration (NEW)
    show_terms: bool = False
    terms_title: Optional[str] = None
    terms_content: Optional[Union[str, List[str]]] = None

    # Confidentiality (MISSING - ADD THIS)
    confidential_notice: bool = False

    # Watermark
    watermark_draft: bool = True  # Show DRAFT watermark for non-approved items
    watermark_text: str = "DRAFT"
    
    # Field visibility control
    # If specified, only these fields/sections are shown
    visible_sections: Optional[List[str]] = None  # None means show all
    hidden_sections: Optional[List[str]] = None   # Sections to hide
    visible_tabs: Optional[List[str]] = None       # For tabbed layout
    

    # Export Options
    allowed_formats: List[ExportFormat] = field(
        default_factory=lambda: [ExportFormat.PDF, ExportFormat.PRINT]
    )
    default_format: ExportFormat = ExportFormat.HTML
    
    # Security
    require_approval: bool = False            # Document only for approved items
    watermark_draft: bool = True              # Show watermark for draft items
    
    # Template Override (optional)
    custom_template: Optional[str] = None     # Path to custom template

    # Signature fields
    signature_fields: List[Dict[str, str]] = field(default_factory=list)
    show_signature_date: bool = False
    # Example: [{"label": "Authorized By", "width": "200px"}, {"label": "Received By", "width": "200px"}]


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

    # ========== VIEW LAYOUT CONFIGURATION (v2.1) ==========
    view_layout: Optional[ViewLayoutConfiguration] = None
    section_definitions: Dict[str, SectionDefinition] = field(default_factory=dict)
    form_section_definitions: Optional[Dict[str, SectionDefinition]] = field(default=None)

    # ========== ENHANCED FEATURES (v2.0) ==========
    model_class: Optional[str] = None

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

    # ========== SERVICE DELEGATION ==========
    service_module: Optional[str] = None  # Module path for entity-specific service
    # Convention: Functions should be named create_{entity_type}, update_{entity_type}, delete_{entity_type}
    # Example: 'app.services.supplier_service' expects create_supplier, update_supplier, delete_supplier

    # ========== DEFAULT VALUES ==========
    default_field_values: Dict[str, Any] = field(default_factory=dict)
    # Default values for fields when creating new entities
    # Example: {'status': 'active', 'is_deleted': False}

    # Document Generation Support 
    document_enabled: bool = False
    document_configs: Dict[str, DocumentConfiguration] = field(default_factory=dict)
    default_document: str = "receipt"
    include_calculated_fields: List[str] = field(default_factory=list)
    document_permissions: Dict[str, str] = field(default_factory=dict)

    # Entity Classification (defaults to MASTER for backward compatibility)
    entity_category: EntityCategory = field(default=EntityCategory.MASTER)
    
    # CRUD Control (defaults to enabled for backward compatibility)
    universal_crud_enabled: bool = field(default=True)
    
    # Allowed Operations (defaults to all operations)
    allowed_operations: List[CRUDOperation] = field(
        default_factory=lambda: [
            CRUDOperation.LIST,
            CRUDOperation.VIEW,
            CRUDOperation.CREATE,
            CRUDOperation.UPDATE,
            CRUDOperation.DELETE,
            CRUDOperation.DOCUMENT,
            CRUDOperation.EXPORT
        ]
    )
    
    # Model Discovery (optional - works without these)
    model_class_path: Optional[str] = field(default=None)
    primary_key_field: str = field(default="id")
    soft_delete_field: Optional[str] = field(default="is_deleted")  # Changed from None
    
    # Custom URL Overrides (optional - for transaction entities)
    custom_create_url: Optional[str] = field(default=None)
    custom_edit_url: Optional[str] = field(default=None)
    custom_delete_url: Optional[str] = field(default=None)
    
    # Form Configuration (optional - uses defaults if not specified)
    form_class_path: Optional[str] = field(default=None)
    create_form_template: str = field(default="engine/universal_create.html")
    edit_form_template: str = field(default="engine/universal_edit.html")
    
    # Field-Level CRUD Control (optional - auto-detected if not specified)
    create_fields: Optional[List[str]] = field(default=None)
    edit_fields: Optional[List[str]] = field(default=None)
    readonly_fields: List[str] = field(default_factory=list)
    
    # Validation Rules (optional enhancements)
    unique_fields: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    
    # CRUD Permissions (optional - uses general permissions if not specified)
    create_permission: Optional[str] = field(default=None)
    edit_permission: Optional[str] = field(default=None)
    delete_permission: Optional[str] = field(default=None)
    
    # Delete Configuration (sensible defaults)
    enable_soft_delete: bool = field(default=True)
    cascade_delete: List[str] = field(default_factory=list)
    delete_confirmation_message: str = field(
        default="Are you sure you want to delete this item?"
    )
    
    # Success Messages (with defaults using entity_label)
    create_success_message: str = field(default="{entity_label} created successfully")
    update_success_message: str = field(default="{entity_label} updated successfully")
    delete_success_message: str = field(default="{entity_label} deleted successfully")
    
    # Bulk Operations (optional)
    enable_bulk_operations: bool = field(default=False)
    bulk_operations: List[str] = field(default_factory=list)
    
    # Auto-save and Drafts (optional)
    enable_auto_save: bool = field(default=False)
    auto_save_interval: int = field(default=30)  # seconds
    
    # Audit Trail (optional)
    enable_audit_trail: bool = field(default=False)
    audit_fields: List[str] = field(default_factory=lambda: [
        "created_at", "created_by", "updated_at", "updated_by"
    ])



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
# INDIAN STATES - GLOBAL CONSTANT
# Used across multiple entities for GST state codes
# =============================================================================

INDIAN_STATES = [
    {"value": "01", "label": "Jammu & Kashmir"},
    {"value": "02", "label": "Himachal Pradesh"},
    {"value": "03", "label": "Punjab"},
    {"value": "04", "label": "Chandigarh"},
    {"value": "05", "label": "Uttarakhand"},
    {"value": "06", "label": "Haryana"},
    {"value": "07", "label": "Delhi"},
    {"value": "08", "label": "Rajasthan"},
    {"value": "09", "label": "Uttar Pradesh"},
    {"value": "10", "label": "Bihar"},
    {"value": "11", "label": "Sikkim"},
    {"value": "12", "label": "Arunachal Pradesh"},
    {"value": "13", "label": "Nagaland"},
    {"value": "14", "label": "Manipur"},
    {"value": "15", "label": "Mizoram"},
    {"value": "16", "label": "Tripura"},
    {"value": "17", "label": "Meghalaya"},
    {"value": "18", "label": "Assam"},
    {"value": "19", "label": "West Bengal"},
    {"value": "20", "label": "Jharkhand"},
    {"value": "21", "label": "Odisha"},
    {"value": "22", "label": "Chhattisgarh"},
    {"value": "23", "label": "Madhya Pradesh"},
    {"value": "24", "label": "Gujarat"},
    {"value": "25", "label": "Daman & Diu"},  # Old code, kept for compatibility
    {"value": "26", "label": "Dadra & Nagar Haveli and Daman & Diu"},
    {"value": "27", "label": "Maharashtra"},
    {"value": "28", "label": "Andhra Pradesh (Before Division)"},
    {"value": "29", "label": "Karnataka"},
    {"value": "30", "label": "Goa"},
    {"value": "31", "label": "Lakshadweep"},
    {"value": "32", "label": "Kerala"},
    {"value": "33", "label": "Tamil Nadu"},
    {"value": "34", "label": "Puducherry"},
    {"value": "35", "label": "Andaman & Nicobar Islands"},
    {"value": "36", "label": "Telangana"},
    {"value": "37", "label": "Andhra Pradesh"},
    {"value": "38", "label": "Ladakh"},
]



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

def validate_entity_configuration(config: EntityConfiguration) -> List[str]:
    """Validate entity configuration"""
    errors = []
    
    if not config.entity_type:
        errors.append("Entity type is required")
    
    if not config.fields:
        errors.append("At least one field must be defined")
    
    # Validate view layout configuration
    if config.view_layout:
        if config.view_layout.type == LayoutType.TABBED and not config.view_layout.tabs:
            errors.append("Tabbed layout requires tab definitions")
    
    return errors

# =============================================================================
# BACKWARD COMPATIBILITY HELPERS
# =============================================================================

def migrate_entity_config(config: EntityConfiguration) -> EntityConfiguration:
    """
    Helper to migrate old configs to v3.0
    Called automatically when loading configs
    """
    # Auto-detect entity category if not set
    if not hasattr(config, 'entity_category'):
        # Use entity type hints to determine category
        if 'payment' in config.entity_type or 'invoice' in config.entity_type:
            config.entity_category = EntityCategory.TRANSACTION
        else:
            config.entity_category = EntityCategory.MASTER
    
    # Auto-detect primary key field if not set
    if not hasattr(config, 'primary_key_field') or not config.primary_key_field:
        # Try common patterns
        if hasattr(config, 'fields'):
            for field in config.fields:
                if '_id' in field.name and field.field_type == FieldType.UUID:
                    config.primary_key_field = field.name
                    break
    
    # Auto-populate create/edit fields if not set
    if not hasattr(config, 'create_fields') or not config.create_fields:
        if hasattr(config, 'fields'):
            config.create_fields = [
                f.name for f in config.fields 
                if f.show_in_form and not f.readonly
            ]
    
    if not hasattr(config, 'edit_fields') or not config.edit_fields:
        config.edit_fields = config.create_fields
    
    return config

def is_v3_compatible(config: EntityConfiguration) -> bool:
    """Check if a config has v3.0 fields"""
    return hasattr(config, 'entity_category') and hasattr(config, 'universal_crud_enabled')

# =============================================================================
# COMPATIBILITY WARNINGS
# =============================================================================

import warnings

def check_config_compatibility(config: EntityConfiguration):
    """Check and warn about potential compatibility issues"""
    if not hasattr(config, 'entity_category'):
        warnings.warn(
            f"Entity '{config.entity_type}' missing v3.0 category. "
            f"Defaulting to MASTER. Consider updating configuration.",
            DeprecationWarning
        )
    
    if not hasattr(config, 'model_class_path') and config.entity_category == EntityCategory.MASTER:
        warnings.warn(
            f"Master entity '{config.entity_type}' missing model_class_path. "
            f"CRUD operations may not work properly.",
            UserWarning
        )