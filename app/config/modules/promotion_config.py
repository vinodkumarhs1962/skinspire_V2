"""
Promotion Configuration
Entity configuration for Promotions Dashboard - Campaign management
Supports CRUD operations on promotion_campaigns table
"""

from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, FieldType, ActionDefinition,
    FilterType, EntityCategory, EntitySearchConfiguration,
    EntityFilterConfiguration, CRUDOperation, ButtonType, ActionDisplayType,
    SectionDefinition
)

# =============================================================================
# FIELD DEFINITIONS - Campaign Promotion Fields
# =============================================================================

CAMPAIGN_FIELDS = [
    # ===== PRIMARY KEY =====
    FieldDefinition(
        name="campaign_id",
        label="Campaign ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True
    ),

    # ===== BASIC INFORMATION =====
    FieldDefinition(
        name="campaign_code",
        label="Campaign Code",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        required=True,
        width="120px",
        section="basic",
        help_text="Unique code for manual application (e.g., DIWALI2025)"
    ),

    FieldDefinition(
        name="campaign_name",
        label="Campaign Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        required=True,
        width="200px",
        section="basic"
    ),

    FieldDefinition(
        name="description",
        label="Description",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        section="basic",
        rows=3
    ),

    # ===== PROMOTION TYPE =====
    FieldDefinition(
        name="promotion_type",
        label="Promotion Type",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=True,
        width="150px",
        section="discount",
        options=[
            {'value': 'simple_discount', 'label': 'Simple Discount'},
            {'value': 'buy_x_get_y', 'label': 'Buy X Get Y Free'}
        ],
        default='simple_discount'
    ),

    # ===== DISCOUNT CONFIGURATION =====
    FieldDefinition(
        name="discount_type",
        label="Discount Type",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=True,
        width="120px",
        section="discount",
        options=[
            {'value': 'percentage', 'label': 'Percentage'},
            {'value': 'fixed_amount', 'label': 'Fixed Amount'}
        ]
    ),

    FieldDefinition(
        name="discount_value",
        label="Discount Value",
        field_type=FieldType.DECIMAL,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        width="100px",
        section="discount",
        help_text="Enter percentage (e.g., 10 for 10%) or fixed amount"
    ),

    # ===== VALIDITY PERIOD =====
    FieldDefinition(
        name="start_date",
        label="Start Date",
        field_type=FieldType.DATE,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        sortable=True,
        filterable=True,
        required=True,
        width="110px",
        section="validity"
    ),

    FieldDefinition(
        name="end_date",
        label="End Date",
        field_type=FieldType.DATE,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        sortable=True,
        filterable=True,
        required=True,
        width="110px",
        section="validity"
    ),

    # ===== STATUS =====
    FieldDefinition(
        name="is_active",
        label="Status",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        default=True,
        width="80px",
        section="basic"
    ),

    # ===== TARGETING =====
    FieldDefinition(
        name="applies_to",
        label="Applies To",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=True,
        width="120px",
        section="targeting",
        options=[
            {'value': 'all', 'label': 'All Items'},
            {'value': 'services', 'label': 'Services Only'},
            {'value': 'medicines', 'label': 'Medicines Only'},
            {'value': 'packages', 'label': 'Packages Only'}
        ],
        default='all'
    ),

    FieldDefinition(
        name="specific_items",
        label="Specific Items",
        field_type=FieldType.JSONB,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="targeting",
        help_text="Leave empty for all items of selected type, or specify item IDs"
    ),

    # ===== CONSTRAINTS =====
    FieldDefinition(
        name="min_purchase_amount",
        label="Min Purchase Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="constraints",
        help_text="Minimum invoice amount to qualify for this promotion"
    ),

    FieldDefinition(
        name="max_discount_amount",
        label="Max Discount Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="constraints",
        help_text="Maximum discount amount in currency"
    ),

    FieldDefinition(
        name="max_uses_per_patient",
        label="Max Uses/Patient",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="constraints",
        help_text="How many times a single patient can use this promotion"
    ),

    FieldDefinition(
        name="max_total_uses",
        label="Max Total Uses",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="constraints",
        help_text="Total uses allowed across all patients"
    ),

    FieldDefinition(
        name="current_uses",
        label="Current Uses",
        field_type=FieldType.INTEGER,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        width="90px",
        section="usage"
    ),

    # ===== VISIBILITY =====
    FieldDefinition(
        name="is_personalized",
        label="Personalized",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        default=False,
        width="100px",
        section="visibility",
        help_text="Private promotions require manual code entry"
    ),

    # Special Group Targeting (Added 2025-11-27)
    FieldDefinition(
        name="target_special_group",
        label="Special Group Only",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        default=False,
        width="120px",
        section="visibility",
        help_text="Only applies to patients marked as Special Group (VIP)"
    ),

    FieldDefinition(
        name="auto_apply",
        label="Auto Apply",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default=False,
        section="visibility",
        help_text="Automatically apply when conditions are met"
    ),

    # ===== TERMS =====
    FieldDefinition(
        name="terms_and_conditions",
        label="Terms & Conditions",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="terms",
        rows=4
    ),

    # ===== BUY X GET Y RULES (JSON) =====
    FieldDefinition(
        name="promotion_rules",
        label="Promotion Rules",
        field_type=FieldType.JSONB,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        section="rules",
        help_text="Complex promotion rules (for Buy X Get Y type)"
    ),

    # ===== AUDIT =====
    FieldDefinition(
        name="created_at",
        label="Created",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="audit"
    ),

    FieldDefinition(
        name="updated_at",
        label="Updated",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        section="audit"
    )
]

# =============================================================================
# SECTION DEFINITIONS - Form Layout
# =============================================================================

CAMPAIGN_SECTIONS = {
    'basic': SectionDefinition(
        key='basic',
        title='Basic Information',
        icon='fas fa-info-circle',
        columns=2,
        order=1
    ),
    'discount': SectionDefinition(
        key='discount',
        title='Discount Configuration',
        icon='fas fa-percent',
        columns=2,
        order=2
    ),
    'validity': SectionDefinition(
        key='validity',
        title='Validity Period',
        icon='fas fa-calendar-alt',
        columns=2,
        order=3
    ),
    'targeting': SectionDefinition(
        key='targeting',
        title='Targeting',
        icon='fas fa-crosshairs',
        columns=2,
        order=4
    ),
    'constraints': SectionDefinition(
        key='constraints',
        title='Usage Constraints',
        icon='fas fa-shield-alt',
        columns=2,
        order=5
    ),
    'visibility': SectionDefinition(
        key='visibility',
        title='Visibility & Auto-Apply',
        icon='fas fa-eye',
        columns=2,
        order=6
    ),
    'rules': SectionDefinition(
        key='rules',
        title='Complex Rules',
        icon='fas fa-cogs',
        columns=1,
        order=7,
        collapsible=True,
        default_collapsed=True
    ),
    'terms': SectionDefinition(
        key='terms',
        title='Terms & Conditions',
        icon='fas fa-file-contract',
        columns=1,
        order=8,
        collapsible=True
    ),
    'usage': SectionDefinition(
        key='usage',
        title='Usage Statistics',
        icon='fas fa-chart-bar',
        columns=2,
        order=9
    ),
    'audit': SectionDefinition(
        key='audit',
        title='Audit Information',
        icon='fas fa-history',
        columns=2,
        order=10,
        collapsible=True,
        default_collapsed=True
    )
}

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

CAMPAIGN_ACTIONS = [
    ActionDefinition(
        id="create",
        label="New Campaign",
        icon="fas fa-plus",
        button_type=ButtonType.PRIMARY,
        route_name="promotion_views.campaign_create",
        show_in_list_toolbar=True,
        show_in_list=False,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),

    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        button_type=ButtonType.INFO,
        route_name="promotion_views.campaign_detail",
        route_params={'campaign_id': '{campaign_id}'},
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=2
    ),

    ActionDefinition(
        id="edit",
        label="Edit",
        icon="fas fa-edit",
        button_type=ButtonType.WARNING,
        route_name="promotion_views.campaign_edit",
        route_params={'campaign_id': '{campaign_id}'},
        show_in_list=True,
        show_in_detail=True,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=3
    ),

    ActionDefinition(
        id="toggle",
        label="Toggle Status",
        icon="fas fa-toggle-on",
        button_type=ButtonType.WARNING,
        route_name="promotion_views.campaign_toggle",
        route_params={'campaign_id': '{campaign_id}'},
        show_in_list=True,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Are you sure you want to change the status of this campaign?",
        order=4
    ),

    ActionDefinition(
        id="duplicate",
        label="Duplicate",
        icon="fas fa-copy",
        button_type=ButtonType.SECONDARY,
        route_name="promotion_views.campaign_duplicate",
        route_params={'campaign_id': '{campaign_id}'},
        show_in_list=True,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=5
    ),

    ActionDefinition(
        id="delete",
        label="Delete",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        route_name="promotion_views.campaign_delete",
        route_params={'campaign_id': '{campaign_id}'},
        show_in_list=True,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this campaign? This action cannot be undone.",
        order=6
    )
]

# =============================================================================
# ENTITY CONFIGURATION
# =============================================================================

config = EntityConfiguration(
    # ========== BASIC INFORMATION ==========
    entity_type="promotion_campaigns",
    name="Campaign",
    plural_name="Campaigns",
    service_name="promotion_campaigns",
    table_name="promotion_campaigns",
    primary_key="campaign_id",
    title_field="campaign_name",
    subtitle_field="campaign_code",
    icon="fas fa-bullhorn",
    page_title="Campaign Promotions",
    description="Manage promotional campaigns and discounts",

    # ========== SEARCH & SORT ==========
    searchable_fields=["campaign_name", "campaign_code", "description"],
    default_sort_field="start_date",
    default_sort_direction="desc",

    # ========== CORE CONFIGURATIONS ==========
    fields=CAMPAIGN_FIELDS,
    actions=CAMPAIGN_ACTIONS,
    summary_cards=[],
    permissions={
        'create': 'promotions.create',
        'read': 'promotions.read',
        'update': 'promotions.update',
        'delete': 'promotions.delete'
    },

    # ========== CATEGORY ==========
    category=EntityCategory.MASTER
)

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

filter_config = EntityFilterConfiguration(
    entity_type='promotion_campaigns',
    filter_mappings={
        'is_active': {'type': 'boolean', 'field': 'is_active'},
        'promotion_type': {'type': 'select', 'field': 'promotion_type'},
        'applies_to': {'type': 'select', 'field': 'applies_to'},
        'is_personalized': {'type': 'boolean', 'field': 'is_personalized'},
        'start_date': {'type': 'date_range', 'field': 'start_date'},
        'end_date': {'type': 'date_range', 'field': 'end_date'}
    }
)

# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================

search_config = EntitySearchConfiguration(
    target_entity='promotion_campaigns',
    search_endpoint='/api/promotions/campaigns/search',
    search_fields=['campaign_name', 'campaign_code', 'description'],
    display_template='{campaign_code} - {campaign_name}',
    value_field='campaign_id',
    sort_field='campaign_name',
    max_results=20
)
