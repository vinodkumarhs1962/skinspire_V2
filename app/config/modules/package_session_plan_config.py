"""
Package Session Plan Configuration
Entity configuration for Package Session Delivery Plans
"""

from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, SectionDefinition,
    FieldType, FilterType, ButtonType, ActionDisplayType,
    EntityCategory, FilterOperator, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration,
    ViewLayoutConfiguration, LayoutType
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# FIELD DEFINITIONS - Simplified, no sections/tabs initially
# =============================================================================

PACKAGE_SESSION_PLAN_FIELDS = [
    # Primary Key (Hidden)
    FieldDefinition(
        name="session_plan_id",
        label="Session Plan ID",
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

    # Session Number
    FieldDefinition(
        name="session_number",
        label="Session Number",
        field_type=FieldType.NUMBER,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        filter_type=FilterType.TEXT,
        section="session_details",
        placeholder="Enter session number (e.g., 1, 2, 3)"
    ),

    # Session Name
    FieldDefinition(
        name="session_name",
        label="Session Name",
        field_type=FieldType.TEXT,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        filter_type=FilterType.TEXT,
        section="session_details",
        css_classes="text-wrap",
        width="250px",
        placeholder="Enter session name"
    ),

    # Session Description
    FieldDefinition(
        name="session_description",
        label="Description",
        field_type=FieldType.TEXTAREA,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="session_details",
        placeholder="Describe what happens in this session"
    ),

    # Estimated Duration (Minutes)
    FieldDefinition(
        name="estimated_duration_minutes",
        label="Duration (Minutes)",
        field_type=FieldType.NUMBER,
        required=False,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        section="session_details",
        placeholder="Estimated duration in minutes"
    ),

    # Recommended Gap (Days)
    FieldDefinition(
        name="recommended_gap_days",
        label="Gap from Previous (Days)",
        field_type=FieldType.NUMBER,
        required=False,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        section="session_details",
        placeholder="Days between this and previous session"
    ),

    # Is Mandatory
    FieldDefinition(
        name="is_mandatory",
        label="Mandatory Session",
        field_type=FieldType.BOOLEAN,
        required=False,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        default_value=True,
        filterable=True,
        filter_type=FilterType.SELECT,
        section="session_details",
        options=[
            {"value": "true", "label": "Mandatory", "color": "success"},
            {"value": "false", "label": "Optional", "color": "warning"}
        ]
    ),

    # Resource Requirements (JSONB - JSON textarea)
    FieldDefinition(
        name="resource_requirements",
        label="Resource Requirements (JSON)",
        field_type=FieldType.TEXTAREA,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="session_details",
        placeholder='[{"resource_type": "doctor", "role": "Dermatologist", "duration_minutes": 30, "quantity": 1}]',
        help_text="JSON array of resource requirements"
    ),

    # Scheduling Notes
    FieldDefinition(
        name="scheduling_notes",
        label="Scheduling Notes",
        field_type=FieldType.TEXTAREA,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="session_details",
        placeholder="Special scheduling instructions or notes"
    ),

    # Prerequisites
    FieldDefinition(
        name="prerequisites",
        label="Prerequisites",
        field_type=FieldType.TEXTAREA,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="session_details",
        placeholder="What must be completed before this session"
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
        section="session_details",
        placeholder="Display sequence number"
    )
]

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

PACKAGE_SESSION_PLAN_ACTIONS = [
    # List view action - Create new session plan
    ActionDefinition(
        id="create",
        label="Add Session",
        icon="fas fa-plus",
        url_pattern="/universal/{entity_type}/create?package_id={package_id}",
        button_type=ButtonType.PRIMARY,
        show_in_list=True,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),

    # Detail view action - Back to Package
    ActionDefinition(
        id="back_to_package",
        label="Back to Package",
        icon="fas fa-arrow-left",
        url_pattern="/universal/packages/detail/{package_id}",
        button_type=ButtonType.SECONDARY,
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        order=5
    ),

    # Detail view action - Edit session plan
    ActionDefinition(
        id="edit",
        label="Edit Session Plan",
        icon="fas fa-edit",
        route_name="universal_views.universal_edit_view",
        route_params={"entity_type": "package_session_plans", "item_id": "{session_plan_id}"},
        button_type=ButtonType.PRIMARY,
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=10
    ),

    # List view action - View session plan
    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        route_name="universal_views.universal_detail_view",
        route_params={"entity_type": "package_session_plans", "item_id": "{session_plan_id}"},
        button_type=ButtonType.INFO,
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=15
    ),

    # Detail view action - Delete session plan
    ActionDefinition(
        id="delete",
        label="Delete Session Plan",
        icon="fas fa-trash",
        url_pattern="/universal/{entity_type}/delete/{session_plan_id}",
        button_type=ButtonType.DANGER,
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this session plan?",
        order=90
    )
]

# =============================================================================
# FILTER & SEARCH CONFIGURATION
# =============================================================================

PACKAGE_SESSION_PLAN_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='package_session_plans',
    filter_mappings={
        'is_mandatory': {
            'options': [
                {"value": "true", "label": "Mandatory"},
                {"value": "false", "label": "Optional"}
            ]
        }
    }
)

PACKAGE_SESSION_PLAN_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='package_session_plans',
    search_fields=["session_name", "session_description"],
    display_template='{session_name}',
    min_chars=2
)

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

PACKAGE_SESSION_PLAN_SECTIONS = {
    "session_details": SectionDefinition(
        key="session_details",
        title="Session Plan Details",
        icon="fas fa-calendar-check",
        columns=2,
        order=1,
        collapsible=False,
        default_collapsed=False
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

PACKAGE_SESSION_PLAN_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.SIMPLE,  # Simple layout for child entities
    responsive_breakpoint='md',
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "session_plan_id",
        "primary_label": "Session Plan ID",
        "title_field": "session_name",
        "title_label": "Session",
        "status_field": None,  # Session plans don't have status
        "secondary_fields": [
            {"field": "session_number", "label": "Session #", "icon": "fas fa-hashtag"},
            {"field": "estimated_duration_minutes", "label": "Duration (min)", "icon": "fas fa-clock"},
            {"field": "recommended_gap_days", "label": "Gap (days)", "icon": "fas fa-calendar-alt"},
            {"field": "is_mandatory", "label": "Mandatory", "icon": "fas fa-exclamation-circle"}
        ]
    }
)

# =============================================================================
# ENTITY CONFIGURATION
# =============================================================================

PACKAGE_SESSION_PLAN_CONFIG = EntityConfiguration(
    # Basic Information (Required)
    entity_type="package_session_plans",
    name="Package Session Plan",
    plural_name="Package Session Plans",
    service_name="package_session_plans",
    table_name="package_session_plan",  # ✅ FIX: Singular to match model __tablename__
    primary_key="session_plan_id",
    title_field="session_name",
    subtitle_field="session_number",
    icon="fas fa-calendar-check",
    page_title="Package Session Plans",
    description="Session Delivery Plans for Packages",
    searchable_fields=["session_name", "session_description"],
    default_sort_field="session_number",
    default_sort_direction="asc",

    # Core Configurations (Required)
    fields=PACKAGE_SESSION_PLAN_FIELDS,
    actions=PACKAGE_SESSION_PLAN_ACTIONS,
    summary_cards=[],
    permissions={},

    # View Layout Configuration
    view_layout=PACKAGE_SESSION_PLAN_VIEW_LAYOUT,
    section_definitions=PACKAGE_SESSION_PLAN_SECTIONS,

    # Form Configuration
    form_section_definitions=PACKAGE_SESSION_PLAN_SECTIONS
)

# Export required objects
config = PACKAGE_SESSION_PLAN_CONFIG
filter_config = PACKAGE_SESSION_PLAN_FILTER_CONFIG
search_config = PACKAGE_SESSION_PLAN_SEARCH_CONFIG
