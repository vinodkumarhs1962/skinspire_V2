"""
Package BOM Item Configuration
Entity configuration for Package Bill of Materials items
"""

from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, SectionDefinition,
    FieldType, FilterType, ButtonType, ActionDisplayType,
    EntityCategory, FilterOperator, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration,
    ViewLayoutConfiguration, LayoutType, CRUDOperation
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# FIELD DEFINITIONS - Simplified, no sections/tabs initially
# =============================================================================

PACKAGE_BOM_ITEM_FIELDS = [
    # Primary Key (Hidden)
    FieldDefinition(
        name="bom_item_id",
        label="BOM Item ID",
        field_type=FieldType.TEXT,
        required=False,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False
    ),

    # Package ID (Hidden - populated from context)
    FieldDefinition(
        name="package_id",
        label="Package",
        field_type=FieldType.TEXT,
        required=True,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False
    ),

    # Package Name (Display in list and header - not in form)
    FieldDefinition(
        name="package_name",
        label="Package",
        field_type=FieldType.TEXT,
        required=False,
        show_in_list=True,  # Show in list view
        show_in_detail=True,
        show_in_form=False,  # Show in header, not form
        readonly=True,
        # NOT virtual - directly populated by PackageService.search_data()
        width="200px",
        css_classes="text-wrap"
    ),

    # Package Created Date (from Package table)
    FieldDefinition(
        name="package_created_at",
        label="Package Date",
        field_type=FieldType.DATE,
        required=False,
        show_in_list=True,  # Show in list view
        show_in_detail=True,
        show_in_form=False,  # Not editable
        readonly=True,
        # Populated by PackageService.search_data() from Package.created_at
        width="130px"
    ),

    # Item Type (Required - determines which entity to select from)
    FieldDefinition(
        name="item_type",
        label="Item Type",
        field_type=FieldType.SELECT,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        filter_type=FilterType.SELECT,
        section="bom_item_details",
        width="140px",  # Increased width for better visibility
        options=[
            {"value": "service", "label": "Service"},
            {"value": "medicine", "label": "Medicine"}
            # NOTE: consumable and equipment removed - no models exist yet
            # Add them when models are created
        ],
        help_text="Select the type of item first, then choose the specific item"
    ),

    # Item ID (Polymorphic reference - REQUIRED in DB, auto-populated)
    FieldDefinition(
        name="item_id",
        label="Item ID",
        field_type=FieldType.UUID,
        required=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,  # Hidden - auto-populated from item selection
        readonly=True,
        section="bom_item_details"
    ),

    # Item Name - Entity search dropdown (target changes based on item_type)
    FieldDefinition(
        name="item_name",
        label="Item Name",
        field_type=FieldType.ENTITY_SEARCH,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        filter_type=FilterType.TEXT,
        section="bom_item_details",
        css_classes="text-wrap",
        width="180px",  # Reduced width to make room for other columns
        # Default entity search config (will be updated by JavaScript based on item_type)
        entity_search_config=EntitySearchConfiguration(
            target_entity='services',  # Default - changes with item_type
            search_endpoint='/api/universal/services/search',
            search_fields=['service_name', 'code'],
            display_template='{service_name}',
            value_field='service_name',
            placeholder='Select item type first...',
            min_chars=2,
            preload_common=False
        ),
        help_text="Select item type first, then search for the item"
    ),

    # Quantity
    FieldDefinition(
        name="quantity",
        label="Quantity",
        field_type=FieldType.NUMBER,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        section="bom_item_details",
        default_value=1
    ),

    # Unit of Measure (text field - auto-populated from service/medicine)
    FieldDefinition(
        name="unit_of_measure",
        label="Unit",
        field_type=FieldType.TEXT,
        required=True,  # Required especially for medicines
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        section="bom_item_details",
        placeholder="Auto-filled from item",
        help_text="Unit will be auto-populated when you select an item"
    ),

    # Supply Method
    FieldDefinition(
        name="supply_method",
        label="Supply Method",
        field_type=FieldType.SELECT,
        required=True,
        show_in_list=False,  # Hidden from list - not essential
        show_in_detail=True,
        show_in_form=True,
        default_value="per_package",
        filterable=True,
        filter_type=FilterType.SELECT,
        section="bom_item_details",
        options=[
            {"value": "per_package", "label": "Per Package"},
            {"value": "per_session", "label": "Per Session"},
            {"value": "on_demand", "label": "On Demand"},
            {"value": "conditional", "label": "Conditional"}
        ]
    ),

    # Price
    FieldDefinition(
        name="current_price",
        label="Unit Price (₹)",
        field_type=FieldType.NUMBER,
        required=False,
        show_in_list=False,  # Hidden from list - we show line_total instead
        show_in_detail=True,
        show_in_form=True,
        section="bom_item_details",
        help_text="Enter unit price for this item"
    ),

    # Line Total (Computed: quantity * current_price)
    FieldDefinition(
        name="line_total",
        label="Line Total (₹)",
        field_type=FieldType.NUMBER,
        required=False,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        readonly=False,  # Allow display in create form - JavaScript will auto-calculate
        section="bom_item_details",
        css_classes="font-semibold text-green-600",
        help_text="Auto-calculated: Quantity × Unit Price"
    ),

    # Is Optional
    FieldDefinition(
        name="is_optional",
        label="Optional Item",
        field_type=FieldType.BOOLEAN,
        required=False,
        show_in_list=False,  # Hidden from list - not essential
        show_in_detail=True,
        show_in_form=True,
        section="bom_item_details",
        default_value=False,
        help_text="Check if this item is optional (not mandatory for package)"
    ),

    # Display Sequence
    FieldDefinition(
        name="display_sequence",
        label="Display Order",
        field_type=FieldType.NUMBER,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="bom_item_details"
    ),

    # Notes
    FieldDefinition(
        name="notes",
        label="Notes",
        field_type=FieldType.TEXTAREA,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="bom_item_details"
    ),

    # Status (Workflow)
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.SELECT,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,  # Set by workflow actions
        readonly=True,
        filterable=True,
        filter_type=FilterType.SELECT,
        default_value="draft",
        section="approval_info",
        width="120px",
        options=[
            {"value": "draft", "label": "Draft"},
            {"value": "pending_approval", "label": "Pending Approval"},
            {"value": "approved", "label": "Approved"},
            {"value": "rejected", "label": "Rejected"}
        ],
        help_text="Workflow status of the BOM item"
    ),

    # Approved By (from ApprovalMixin)
    FieldDefinition(
        name="approved_by",
        label="Approved By",
        field_type=FieldType.TEXT,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="approval_info"
    ),

    # Approved At (from ApprovalMixin)
    FieldDefinition(
        name="approved_at",
        label="Approved At",
        field_type=FieldType.DATETIME,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="approval_info"
    ),

    # Rejection Reason
    FieldDefinition(
        name="rejection_reason",
        label="Rejection Reason",
        field_type=FieldType.TEXTAREA,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="approval_info",
        help_text="Reason for rejection if status is rejected"
    ),

    # System Info Fields
    FieldDefinition(
        name="bom_item_id",
        label="BOM Item ID",
        field_type=FieldType.TEXT,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="system_info"
    ),

    # Note: package_id and item_id fields are defined at the top of PACKAGE_BOM_ITEM_FIELDS
    # Removed duplicate fields from system_info section

    FieldDefinition(
        name="created_by",
        label="Created By",
        field_type=FieldType.TEXT,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="system_info"
    ),

    FieldDefinition(
        name="created_at",
        label="Created At",
        field_type=FieldType.DATETIME,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="system_info"
    ),

    FieldDefinition(
        name="updated_by",
        label="Updated By",
        field_type=FieldType.TEXT,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="system_info"
    ),

    FieldDefinition(
        name="updated_at",
        label="Updated At",
        field_type=FieldType.DATETIME,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="system_info"
    ),

    FieldDefinition(
        name="deleted_at",
        label="Deleted At",
        field_type=FieldType.DATETIME,
        required=False,
        show_in_list=False,  # Don't show in list - deleted rows will be styled instead
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="system_info"
    )
]

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

PACKAGE_BOM_ITEM_ACTIONS = [
    # =============================================================================
    # LIST TOOLBAR ACTIONS (Navigation + Create)
    # =============================================================================

    # Navigate to Packages list
    ActionDefinition(
        id="goto_packages_list",
        label="Packages",
        icon="fas fa-box-open",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "packages"},
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),

    # Create action - Hidden from list toolbar, but allowed from Package detail view
    # BOM items must be created with package_id context
    ActionDefinition(
        id="create",
        label="Create BOM Item",
        icon="fas fa-plus",
        button_type=ButtonType.SUCCESS,
        route_name="universal_views.universal_create_view",
        route_params={"entity_type": "package_bom_items"},
        show_in_list=False,
        show_in_list_toolbar=False,  # Hide from list toolbar
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        order=2
    ),

    # =============================================================================
    # LIST ROW ACTIONS (Per-record actions in table)
    # =============================================================================

    # View action (always first in row)
    ActionDefinition(
        id="view_row",
        label="View",
        icon="fas fa-eye",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_detail_view",
        route_params={"entity_type": "package_bom_items", "item_id": "{bom_item_id}"},
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),

    # Submit for Approval action (in list row - for draft items)
    ActionDefinition(
        id="submit_row",
        label="Submit",
        icon="fas fa-paper-plane",
        button_type=ButtonType.PRIMARY,
        url_pattern="/universal/{entity_type}/submit_for_approval/{bom_item_id}",
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        confirmation_required=True,
        confirmation_message="Submit this BOM item for approval?",
        javascript_handler="handleApproveAction",  # POST form handler from package_bom_list_grouping.js
        conditional_display="item.status == 'draft' and item.deleted_at is None",
        order=2
    ),

    # Approve action (in list row - for pending_approval items only)
    ActionDefinition(
        id="approve_row",
        label="Approve",
        icon="fas fa-check-circle",
        button_type=ButtonType.SUCCESS,
        url_pattern="/universal/{entity_type}/approve/{bom_item_id}",
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        confirmation_required=True,
        confirmation_message="Approve this BOM item?",
        javascript_handler="handleApproveAction",  # POST form handler from package_bom_list_grouping.js
        conditional_display="item.status == 'pending_approval' and item.deleted_at is None",
        order=3
    ),

    # =============================================================================
    # DETAIL TOOLBAR ACTIONS (Navigation + Print)
    # =============================================================================

    # Back to parent package detail view
    ActionDefinition(
        id="goto_package_detail",
        label="Package",
        icon="fas fa-box-open",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_detail_view",
        route_params={"entity_type": "packages", "item_id": "{package_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),

    # Navigate to packages list
    ActionDefinition(
        id="goto_packages_list_detail",
        label="All Packages",
        icon="fas fa-boxes",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "packages"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=2
    ),

    # Print BOM item
    ActionDefinition(
        id="print_bom_item",
        label="Print",
        icon="fas fa-print",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_document_view",
        route_params={
            "entity_type": "package_bom_items",
            "item_id": "{bom_item_id}",
            "doc_type": "profile"
        },
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=5
    ),

    # =============================================================================
    # DETAIL DROPDOWN ACTIONS (Edit, Delete, etc.)
    # =============================================================================

    # Edit BOM item
    ActionDefinition(
        id="edit_bom_item",
        label="Edit BOM Item",
        icon="fas fa-edit",
        button_type=ButtonType.PRIMARY,
        route_name="universal_views.universal_edit_view",
        route_params={"entity_type": "package_bom_items", "item_id": "{bom_item_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=1
    ),

    # Delete BOM item
    ActionDefinition(
        id="delete_bom_item",
        label="Delete BOM Item",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        url_pattern="/universal/{entity_type}/delete/{bom_item_id}",
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this BOM item?",
        conditional_display="item.deleted_at is None",  # Only show if not deleted
        order=2
    ),

    # Restore/Undelete BOM item (for soft-deleted items)
    ActionDefinition(
        id="restore_bom_item",
        label="Restore BOM Item",
        icon="fas fa-undo",
        button_type=ButtonType.SUCCESS,
        url_pattern="/universal/{entity_type}/undelete/{bom_item_id}",
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Are you sure you want to restore this BOM item?",
        conditional_display="item.deleted_at is not None",  # Only show if deleted
        order=3
    ),

    # Submit for Approval
    ActionDefinition(
        id="submit_for_approval",
        label="Submit for Approval",
        icon="fas fa-paper-plane",
        button_type=ButtonType.PRIMARY,
        url_pattern="/universal/{entity_type}/submit_for_approval/{bom_item_id}",
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Submit this BOM item for approval?",
        conditional_display="item.status in ['draft'] and item.deleted_at is None",
        order=4
    ),

    # Approve BOM Item
    ActionDefinition(
        id="approve_bom_item",
        label="Approve",
        icon="fas fa-check-circle",
        button_type=ButtonType.SUCCESS,
        url_pattern="/universal/{entity_type}/approve/{bom_item_id}",
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Are you sure you want to approve this BOM item?",
        conditional_display="item.status in ['draft', 'pending_approval'] and item.deleted_at is None",
        order=5
    ),

    # Reject BOM Item
    ActionDefinition(
        id="reject_bom_item",
        label="Reject",
        icon="fas fa-times-circle",
        button_type=ButtonType.DANGER,
        url_pattern="/universal/{entity_type}/reject/{bom_item_id}",
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Are you sure you want to reject this BOM item?",
        conditional_display="item.status in ['draft', 'pending_approval'] and item.deleted_at is None",
        order=6
    )
]

# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

PACKAGE_BOM_ITEM_SUMMARY_CARDS = [
    {
        "title": "Total BOM Items",
        "field": "total_count",
        "icon": "fas fa-boxes",
        "icon_css": "stat-card-icon primary",
        "color": "primary",
        "type": "number",
        "filterable": True,
        "visible": True,
        "order": 1
    },
    {
        "title": "Approved Items",
        "field": "approved_count",
        "icon": "fas fa-check-circle",
        "icon_css": "stat-card-icon success",
        "color": "success",
        "type": "number",
        "filterable": True,
        "filter_value": "approved",
        "filter_field": "status",
        "visible": True,
        "order": 2
    },
    {
        "title": "Pending Approval",
        "field": "pending_approval_count",
        "icon": "fas fa-clock",
        "icon_css": "stat-card-icon warning",
        "color": "warning",
        "type": "number",
        "filterable": True,
        "filter_value": "pending_approval",
        "filter_field": "status",
        "visible": True,
        "order": 3
    },
    {
        "title": "Draft Items",
        "field": "draft_count",
        "icon": "fas fa-edit",
        "icon_css": "stat-card-icon info",
        "color": "info",
        "type": "number",
        "filterable": True,
        "filter_value": "draft",
        "filter_field": "status",
        "visible": True,
        "order": 4
    }
]

# =============================================================================
# FILTER & SEARCH CONFIGURATION
# =============================================================================

PACKAGE_BOM_ITEM_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='package_bom_items',
    filter_mappings={
        'item_type': {
            'options': [
                {"value": "service", "label": "Service"},
                {"value": "medicine", "label": "Medicine"},
                {"value": "consumable", "label": "Consumable"},
                {"value": "equipment", "label": "Equipment"}
            ]
        }
    }
)

PACKAGE_BOM_ITEM_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='package_bom_items',
    search_fields=["item_name", "notes"],
    display_template='{item_name}',
    min_chars=2
)

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

PACKAGE_BOM_ITEM_SECTIONS = {
    "bom_item_details": SectionDefinition(
        key="bom_item_details",
        title="BOM Item Details",
        icon="fas fa-box",
        columns=2,
        order=1,
        collapsible=False,
        default_collapsed=False
    ),
    "approval_info": SectionDefinition(
        key="approval_info",
        title="Approval Information",
        icon="fas fa-clipboard-check",
        columns=2,
        order=2,
        collapsible=True,
        default_collapsed=False
    ),
    "system_info": SectionDefinition(
        key="system_info",
        title="System Information",
        icon="fas fa-info-circle",
        columns=2,
        order=3,
        collapsible=True,
        default_collapsed=True
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

PACKAGE_BOM_ITEM_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.SIMPLE,  # Simple layout for child entities
    responsive_breakpoint='md',
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "package_name",  # Show package name prominently
        "primary_label": "Package:",
        "title_field": "item_name",
        "title_label": "BOM Item",
        "status_field": "status",  # Show status badge in top right
        "info_cards": [
            {
                "title": "Item Type",
                "field": "item_type",
                "icon": "fas fa-tag",
                "color": "primary"
            },
            {
                "title": "Quantity",
                "field": "quantity",
                "icon": "fas fa-hashtag",
                "color": "info"
            },
            {
                "title": "Unit Price",
                "field": "current_price",
                "icon": "fas fa-rupee-sign",
                "color": "warning"
            },
            {
                "title": "Line Total",
                "field": "line_total",
                "icon": "fas fa-calculator",
                "color": "warning",
                "type": "currency"
            }
        ],
        "secondary_fields": [
            {"field": "supply_method", "label": "Supply Method", "icon": "fas fa-truck"},
            {"field": "current_price", "label": "Unit Price", "icon": "fas fa-rupee-sign", "type": "currency"},
            {"field": "is_optional", "label": "Optional", "icon": "fas fa-question-circle"}
        ]
    }
)

# =============================================================================
# ENTITY CONFIGURATION
# =============================================================================

PACKAGE_BOM_ITEM_CONFIG = EntityConfiguration(
    # Basic Information (Required)
    entity_type="package_bom_items",
    name="Package BOM Item",
    plural_name="Package BOM Items",
    service_name="package_bom_items",
    table_name="package_bom_items",
    primary_key="bom_item_id",
    title_field="item_name",
    subtitle_field="item_type",
    icon="fas fa-box",
    page_title="Package BOM Items",
    description="Bill of Materials for Packages",
    searchable_fields=["item_name", "notes"],
    default_sort_field="package_name",  # Sort by package first, then item_type
    default_sort_direction="asc",

    # Core Configurations (Required)
    fields=PACKAGE_BOM_ITEM_FIELDS,
    actions=PACKAGE_BOM_ITEM_ACTIONS,
    summary_cards=PACKAGE_BOM_ITEM_SUMMARY_CARDS,
    permissions={},

    # View Layout Configuration
    view_layout=PACKAGE_BOM_ITEM_VIEW_LAYOUT,
    section_definitions=PACKAGE_BOM_ITEM_SECTIONS,

    # Form Configuration
    form_section_definitions=PACKAGE_BOM_ITEM_SECTIONS,

    # Form Scripts - Entity-specific JavaScript for cascading dropdown behavior
    form_scripts=['js/package_bom_item_dropdown.js'],

    # Custom CSS and JavaScript for list grouping by package and dropdown behavior
    custom_css_files=['css/package_bom_list_grouping.css'],
    custom_javascript_files=[
        'js/package_bom_list_grouping.js',
        'js/package_bom_item_dropdown.js'
    ],

    # CRUD Control - BOM items can be created from Package detail view
    universal_crud_enabled=True,
    allowed_operations=[
        CRUDOperation.LIST,
        CRUDOperation.VIEW,
        CRUDOperation.CREATE,  # Create allowed (from Package detail view)
        CRUDOperation.UPDATE,  # Edit allowed
        CRUDOperation.DELETE,  # Delete/Restore allowed
        CRUDOperation.DOCUMENT,  # Document/Print enabled
        CRUDOperation.EXPORT
    ],

    # Document Configuration
    document_enabled=True,

    # Calculated/Virtual Fields - populated by PackageService
    include_calculated_fields=[
        "package_name",  # Populated from package relationship
        "package_created_at",  # Populated from package.created_at
    ],

    # CRUD Field Control
    create_fields=[
        "item_type",          # Required - select type first (triggers item dropdown)
        "item_name",          # Required - entity dropdown based on item_type (TODO: implement)
        "quantity",           # Required - number input
        "unit_of_measure",    # Required - text input (especially for medicines)
        "supply_method",      # Required - per_package, per_session, etc.
        "current_price",      # Optional - unit price
        "line_total",         # Readonly - auto-calculated (quantity * price)
        "is_optional",        # Optional - checkbox
        "display_sequence",   # Optional - ordering
        "notes"               # Optional - textarea
    ],

    edit_fields=[
        "item_type",          # Required - select type first
        "item_id",            # Readonly - show UUID for reference
        "item_name",          # Required - entity dropdown
        "quantity",           # Required
        "unit_of_measure",    # Required - text input
        "supply_method",      # Required
        "current_price",      # Optional
        "line_total",         # Readonly - auto-calculated
        "is_optional",        # Optional
        "display_sequence",   # Optional
        "notes"               # Optional
    ]
)

# Export required objects
config = PACKAGE_BOM_ITEM_CONFIG
filter_config = PACKAGE_BOM_ITEM_FILTER_CONFIG
search_config = PACKAGE_BOM_ITEM_SEARCH_CONFIG
