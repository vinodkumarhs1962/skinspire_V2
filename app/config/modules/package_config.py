# Package Configuration Module
# File: app/config/modules/package_config.py

"""
Package Configuration - Single Entity Per File
Comprehensive configuration for treatment/service packages
Following implementation plan for Universal Engine extension
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition,
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration, ButtonType,
    ComplexDisplayType, ActionDisplayType, FilterType,
    DocumentConfiguration, PrintLayoutType, DocumentType,
    PageSize, Orientation, DocumentSectionType, ExportFormat,
    EntityCategory, CRUDOperation, FilterOperator, CustomRenderer
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# PACKAGE FIELD DEFINITIONS (Simplified - Only fields that exist in model)
# Total: 20 fields (13 actual + 7 virtual)
# =============================================================================

PACKAGE_FIELDS = [
    # ========== PRIMARY KEY ==========
    FieldDefinition(
        name="package_id",
        label="Package ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="basic_info",
        section="system_fields",
        view_order=0
    ),

    # ========== TENANT FIELDS ==========
    FieldDefinition(
        name="hospital_id",
        label="Hospital",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="technical",
        view_order=0
    ),

    # ========== BASIC INFORMATION ==========
    FieldDefinition(
        name="package_name",
        label="Package Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        sortable=True,
        required=True,
        searchable=True,
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,
        filter_operator=FilterOperator.CONTAINS,
        entity_search_config=EntitySearchConfiguration(
            target_entity='packages',
            search_fields=['package_name', 'package_code'],
            display_template='{package_name}',
            value_field='package_name',
            filter_field='package_name',
            placeholder="Type to search packages...",
            min_chars=2,
            max_results=20,
            preload_common=True,
            cache_results=True,
            additional_filters={'status': 'active'}
        ),
        placeholder="Enter package name",
        css_classes="text-wrap",
        tab_group="basic_info",
        section="basic_details",
        view_order=1
    ),
    FieldDefinition(
        name="package_code",
        label="Package Code",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        required=False,
        placeholder="Enter package code",
        tab_group="basic_info",
        section="basic_details",
        view_order=2
    ),
    FieldDefinition(
        name="package_family_id",
        label="Package Family",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=False,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        entity_search_config=EntitySearchConfiguration(
            target_entity='package_families',
            search_fields=['package_family'],
            display_template='{package_family}',
            value_field='package_family_id',
            placeholder="Select package family...",
            min_chars=1,
            max_results=20
        ),
        help_text="Group packages into families (future feature)",
        tab_group="basic_info",
        section="basic_details",
        view_order=3
    ),
    FieldDefinition(
        name="service_owner",
        label="Service Owner",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter service owner/responsible staff",
        tab_group="basic_info",
        section="basic_details",
        view_order=4
    ),

    # ========== PRICING INFORMATION ==========
    FieldDefinition(
        name="price",
        label="Base Price (Excluding GST)",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        filter_type=FilterType.NUMERIC_RANGE,
        sortable=True,
        required=True,
        placeholder="Enter base price",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=1
    ),
    FieldDefinition(
        name="selling_price",
        label="Selling Price",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        sortable=True,
        required=False,
        placeholder="Enter selling price",
        help_text="Actual selling price (can be different from base price)",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=2
    ),
    FieldDefinition(
        name="max_discount",
        label="Maximum Discount (%)",
        field_type=FieldType.PERCENTAGE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter maximum discount percentage",
        help_text="Maximum allowed discount for this package",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=3
    ),
    FieldDefinition(
        name="currency_code",
        label="Currency",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value="INR",
        required=False,
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=4
    ),

    # ========== GST INFORMATION ==========
    FieldDefinition(
        name="hsn_code",
        label="HSN/SAC Code",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        required=False,
        placeholder="Enter HSN/SAC code",
        help_text="HSN/SAC code for GST classification",
        tab_group="pricing_components",
        section="gst_info",
        view_order=1
    ),
    FieldDefinition(
        name="gst_rate",
        label="GST Rate (%)",
        field_type=FieldType.PERCENTAGE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter GST rate",
        tab_group="pricing_components",
        section="gst_info",
        view_order=2
    ),
    FieldDefinition(
        name="cgst_rate",
        label="CGST Rate (%)",
        field_type=FieldType.PERCENTAGE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter CGST rate",
        tab_group="pricing_components",
        section="gst_info",
        view_order=3
    ),
    FieldDefinition(
        name="sgst_rate",
        label="SGST Rate (%)",
        field_type=FieldType.PERCENTAGE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter SGST rate",
        tab_group="pricing_components",
        section="gst_info",
        view_order=4
    ),
    FieldDefinition(
        name="igst_rate",
        label="IGST Rate (%)",
        field_type=FieldType.PERCENTAGE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter IGST rate",
        tab_group="pricing_components",
        section="gst_info",
        view_order=5
    ),
    FieldDefinition(
        name="is_gst_exempt",
        label="GST Exempt",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value=False,
        help_text="Check if package is GST exempt",
        tab_group="pricing_gst",
        section="gst_info",
        view_order=6
    ),

    # ========== STATUS ==========
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.STATUS_BADGE,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        show_in_edit=True,
        filterable=True,
        sortable=True,
        required=True,
        options=[
            {"value": "active", "label": "Active"},
            {"value": "discontinued", "label": "Discontinued"}
        ],
        default_value="active",
        tab_group="pricing_gst",
        section="status_info",
        view_order=1
    ),

    # ========== AUDIT FIELDS ==========
    FieldDefinition(
        name="created_at",
        label="Created At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        sortable=True,
        tab_group="system_info",
        section="audit_info",
        view_order=1
    ),
    FieldDefinition(
        name="created_by",
        label="Created By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_info",
        view_order=2
    ),
    FieldDefinition(
        name="modified_at",
        label="Modified At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        sortable=True,
        tab_group="system_info",
        section="audit_info",
        view_order=3
    ),
    FieldDefinition(
        name="modified_by",
        label="Modified By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_info",
        view_order=4
    ),

    # ========== VIRTUAL/CALCULATED FIELDS ==========
    FieldDefinition(
        name="active_plans_count",
        label="Active Plans",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Number of active payment plans",
        tab_group="system_info",
        section="calculated_fields",
        view_order=1
    ),
    FieldDefinition(
        name="total_revenue",
        label="Total Revenue",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Total revenue from this package",
        tab_group="system_info",
        section="calculated_fields",
        view_order=2
    ),
    FieldDefinition(
        name="avg_completion_rate",
        label="Avg Completion Rate (%)",
        field_type=FieldType.PERCENTAGE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Average completion rate for this package",
        tab_group="system_info",
        section="calculated_fields",
        view_order=3
    ),

    # ========== BOM VIRTUAL FIELDS ==========
    FieldDefinition(
        name="total_bom_items",
        label="Total BOM Items",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Number of items in Bill of Materials",
        tab_group="bom_delivery",
        section="bom_summary",
        view_order=1
    ),
    FieldDefinition(
        name="bom_cost_estimate",
        label="BOM Cost Estimate",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Estimated cost from Bill of Materials",
        tab_group="bom_delivery",
        section="bom_summary",
        view_order=2
    ),
    FieldDefinition(
        name="total_sessions",
        label="Total Sessions",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Number of delivery sessions planned",
        tab_group="bom_delivery",
        section="session_summary",
        view_order=1
    ),
    FieldDefinition(
        name="total_duration_hours",
        label="Total Duration (Hours)",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Total estimated hours for all sessions",
        tab_group="bom_delivery",
        section="session_summary",
        view_order=2
    ),

    # ========== BOM DISPLAY TABLES ==========
    FieldDefinition(
        name="bom_items_display",
        label="Bill of Materials Items",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        tab_group="bom_delivery",
        section="bom_items_table",
        view_order=1,
        custom_renderer=CustomRenderer(
            template="engine/business/package_bom_items_table.html",
            context_function="get_package_bom_details",
            css_classes="table-responsive w-100"
        )
    ),
    FieldDefinition(
        name="session_plan_display",
        label="Session Delivery Plan",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        tab_group="bom_delivery",
        section="session_plan_table",
        view_order=1,
        custom_renderer=CustomRenderer(
            template="engine/business/package_session_plan_table.html",
            context_function="get_package_bom_details",
            css_classes="table-responsive w-100"
        )
    )
]

# =============================================================================
# SECTION DEFINITIONS (Simplified)
# =============================================================================

PACKAGE_FORM_SECTIONS = {
    "basic_details": SectionDefinition(
        key="basic_details",
        title="Basic Information",
        icon="fas fa-info-circle",
        columns=2,
        order=1,
        collapsible=False,
        default_collapsed=False
    ),
    "pricing_info": SectionDefinition(
        key="pricing_info",
        title="Pricing Information",
        icon="fas fa-rupee-sign",
        columns=2,
        order=2,
        collapsible=False,
        default_collapsed=False
    ),
    "gst_info": SectionDefinition(
        key="gst_info",
        title="GST Information",
        icon="fas fa-file-invoice",
        columns=2,
        order=3,
        collapsible=True,
        default_collapsed=False
    ),
    "status_info": SectionDefinition(
        key="status_info",
        title="Status",
        icon="fas fa-toggle-on",
        columns=2,
        order=4,
        collapsible=False,
        default_collapsed=False
    ),
    "bom_summary": SectionDefinition(
        key="bom_summary",
        title="Bill of Materials Summary",
        icon="fas fa-list-ul",
        columns=2,
        order=5,
        collapsible=False,
        default_collapsed=False
    ),
    "bom_items_table": SectionDefinition(
        key="bom_items_table",
        title="BOM Items",
        icon="fas fa-boxes",
        columns=1,
        order=6,
        collapsible=True,
        default_collapsed=False
    ),
    "session_summary": SectionDefinition(
        key="session_summary",
        title="Session Plan Summary",
        icon="fas fa-calendar-alt",
        columns=2,
        order=7,
        collapsible=False,
        default_collapsed=False
    ),
    "session_plan_table": SectionDefinition(
        key="session_plan_table",
        title="Session Plan Details",
        icon="fas fa-calendar-check",
        columns=1,
        order=8,
        collapsible=True,
        default_collapsed=False
    ),
    "calculated_fields": SectionDefinition(
        key="calculated_fields",
        title="Calculated Information",
        icon="fas fa-calculator",
        columns=2,
        order=7,
        collapsible=True,
        default_collapsed=True
    ),
    "audit_info": SectionDefinition(
        key="audit_info",
        title="Audit Information",
        icon="fas fa-history",
        columns=2,
        order=8,
        collapsible=True,
        default_collapsed=True
    ),
    "technical": SectionDefinition(
        key="technical",
        title="Technical Details",
        icon="fas fa-server",
        columns=2,
        order=9,
        collapsible=True,
        default_collapsed=True
    )
}

PACKAGE_SECTIONS = PACKAGE_FORM_SECTIONS

# =============================================================================
# TAB DEFINITIONS
# =============================================================================

PACKAGE_TABS = {
    'basic_info': TabDefinition(
        key='basic_info',
        label='Basic Info',
        icon='fas fa-box',
        sections={
            'basic_details': PACKAGE_FORM_SECTIONS['basic_details']
        },
        order=0,
        default_active=True
    ),
    'pricing_gst': TabDefinition(
        key='pricing_gst',
        label='Pricing & GST',
        icon='fas fa-money-bill',
        sections={
            'pricing_info': PACKAGE_FORM_SECTIONS['pricing_info'],
            'gst_info': PACKAGE_FORM_SECTIONS['gst_info'],
            'status_info': PACKAGE_FORM_SECTIONS['status_info']
        },
        order=1
    ),
    'bom_delivery': TabDefinition(
        key='bom_delivery',
        label='BOM & Delivery',
        icon='fas fa-tasks',
        sections={
            'bom_summary': PACKAGE_FORM_SECTIONS['bom_summary'],
            'bom_items_table': PACKAGE_FORM_SECTIONS['bom_items_table'],
            'session_summary': PACKAGE_FORM_SECTIONS['session_summary'],
            'session_plan_table': PACKAGE_FORM_SECTIONS['session_plan_table']
        },
        order=2
    ),
    'system_info': TabDefinition(
        key='system_info',
        label='System Info',
        icon='fas fa-cogs',
        sections={
            'calculated_fields': PACKAGE_FORM_SECTIONS['calculated_fields'],
            'audit_info': PACKAGE_FORM_SECTIONS['audit_info'],
            'technical': PACKAGE_FORM_SECTIONS['technical']
        },
        order=3
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

PACKAGE_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    responsive_breakpoint='md',
    tabs=PACKAGE_TABS,
    default_tab='basic_info',
    sticky_tabs=False,
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "package_id",
        "primary_label": "Package ID",
        "title_field": "package_name",
        "title_label": "Package",
        "status_field": "status",
        "secondary_fields": [
            {"field": "package_type", "label": "Type", "icon": "fas fa-tag"},
            {"field": "price", "label": "Price", "icon": "fas fa-rupee-sign"},
            {"field": "active_plans_count", "label": "Active Plans", "icon": "fas fa-users"}
        ]
    }
)

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

PACKAGE_ACTIONS = [
    ActionDefinition(
        id="create",
        label="New Package",
        icon="fas fa-plus",
        url_pattern="/universal/{entity_type}/create",
        button_type=ButtonType.PRIMARY,
        permission="packages_create",
        show_in_list=True,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),
    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        route_name="universal_views.universal_detail_view",
        route_params={"entity_type": "packages", "item_id": "{package_id}"},
        button_type=ButtonType.INFO,
        permission="packages_view",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=10
    ),
    ActionDefinition(
        id="edit",
        label="Edit Package",
        icon="fas fa-edit",
        route_name="universal_views.universal_edit_view",
        route_params={"entity_type": "packages", "item_id": "{package_id}"},
        button_type=ButtonType.PRIMARY,
        permission="packages_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=20
    ),
    ActionDefinition(
        id="manage_bom",
        label="Manage BOM Items",
        icon="fas fa-boxes",
        url_pattern="/universal/package_bom_items/list?package_id={package_id}",
        button_type=ButtonType.INFO,
        permission="packages_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        order=30
    ),
    ActionDefinition(
        id="manage_sessions",
        label="Manage Session Plan",
        icon="fas fa-calendar-alt",
        url_pattern="/universal/package_session_plans/list?package_id={package_id}",
        button_type=ButtonType.INFO,
        permission="packages_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        order=40
    ),
    ActionDefinition(
        id="delete",
        label="Delete Package",
        icon="fas fa-trash",
        url_pattern="/api/universal/{entity_type}/{item_id}/delete",
        button_type=ButtonType.DANGER,
        permission="packages_delete",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=100,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this package?",
        conditions={
            "status": ["inactive", "discontinued"]
        }
    )
]

# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

PACKAGE_SUMMARY_CARDS = [
    {
        "id": "total_packages",
        "label": "Total Packages",
        "icon": "fas fa-box",
        "field": "total_count",
        "type": "number",
        "icon_css": "stat-card-icon primary",
        "filterable": True,
        "visible": True,
        "order": 1
    },
    {
        "id": "active_packages",
        "label": "Active Packages",
        "icon": "fas fa-check-circle",
        "field": "active_count",
        "type": "number",
        "icon_css": "stat-card-icon success",
        "filterable": True,
        "filter_field": "status",
        "filter_value": "active",
        "visible": True,
        "order": 2
    },
    {
        "id": "total_revenue",
        "label": "Total Revenue",
        "icon": "fas fa-rupee-sign",
        "field": "total_revenue",
        "type": "currency",
        "icon_css": "stat-card-icon info",
        "filterable": False,
        "visible": True,
        "order": 3
    }
]

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

PACKAGE_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'created_from': FilterCategory.DATE,
    'created_to': FilterCategory.DATE,
    'modified_from': FilterCategory.DATE,
    'modified_to': FilterCategory.DATE,

    # Selection filters
    'status': FilterCategory.SELECTION,
    'is_gst_exempt': FilterCategory.SELECTION,

    # Search filters
    'search': FilterCategory.SEARCH,
    'q': FilterCategory.SEARCH,
    'package_name': FilterCategory.SEARCH,
    'package_code': FilterCategory.SEARCH,

    # Amount filters
    'price': FilterCategory.AMOUNT,
    'selling_price': FilterCategory.AMOUNT,

    # Relationship filters
    'package_id': FilterCategory.RELATIONSHIP,
    'package_family_id': FilterCategory.RELATIONSHIP
}

PACKAGE_DEFAULT_FILTERS = {
    'status': 'active'
}

PACKAGE_CATEGORY_CONFIGS = {
    FilterCategory.SELECTION: {
        'process_empty_as_all': True,
        'case_sensitive': False
    },
    FilterCategory.SEARCH: {
        'min_length': 2,
        'search_fields': ['package_name', 'package_code'],
        'case_sensitive': False
    },
    FilterCategory.DATE: {
        'default_preset': None,
        'allow_range': True
    },
    FilterCategory.AMOUNT: {
        'allow_range': True
    },
    FilterCategory.RELATIONSHIP: {
        'lazy_load': True,
        'cache_duration': 300
    }
}

# =============================================================================
# ENTITY FILTER CONFIGURATION
# =============================================================================

PACKAGE_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='packages',
    filter_mappings={
        'status': {
            'options': [
                {'value': 'active', 'label': 'Active'},
                {'value': 'discontinued', 'label': 'Discontinued'}
            ]
        }
    }
)

# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================

PACKAGE_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='packages',
    search_fields=['package_name', 'package_code'],
    display_template='{package_name}',
    value_field='package_id',
    min_chars=1,
    max_results=10,
    sort_field='package_name',
    additional_filters={'status': 'active'}
)

# =============================================================================
# PERMISSIONS CONFIGURATION
# =============================================================================

PACKAGE_PERMISSIONS = {
    "list": "packages_list",
    "view": "packages_view",
    "create": "packages_create",
    "edit": "packages_edit",
    "delete": "packages_delete",
    "export": "packages_export",
    "bulk": "packages_bulk"
}

# =============================================================================
# COMPLETE PACKAGE CONFIGURATION
# =============================================================================

PACKAGE_CONFIG = EntityConfiguration(
    # ========== BASIC INFORMATION (REQUIRED) ==========
    entity_type="packages",
    name="Package",
    plural_name="Packages",
    service_name="packages",
    table_name="packages",
    primary_key="package_id",
    title_field="package_name",
    subtitle_field="price",
    icon="fas fa-box",
    page_title="Package Management",
    description="Manage treatment and service packages",
    searchable_fields=["package_name", "package_code"],
    default_sort_field="package_name",
    default_sort_direction="asc",

    # ========== CORE CONFIGURATIONS ==========
    fields=PACKAGE_FIELDS,
    section_definitions=PACKAGE_FORM_SECTIONS,
    form_section_definitions=PACKAGE_FORM_SECTIONS,
    actions=PACKAGE_ACTIONS,
    summary_cards=PACKAGE_SUMMARY_CARDS,
    permissions=PACKAGE_PERMISSIONS,

    # ========== OPTIONAL CONFIGURATIONS ==========
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,

    # View Layout Configuration
    view_layout=PACKAGE_VIEW_LAYOUT,

    # Filter Configuration
    filter_category_mapping=PACKAGE_FILTER_CATEGORY_MAPPING,
    default_filters=PACKAGE_DEFAULT_FILTERS,
    category_configs=PACKAGE_CATEGORY_CONFIGS,

    # Date and Amount Fields
    primary_date_field="created_at",
    primary_amount_field="price",

    # Entity Classification
    entity_category=EntityCategory.MASTER,
    universal_crud_enabled=True,

    # Allowed Operations
    allowed_operations=[
        CRUDOperation.CREATE,
        CRUDOperation.READ,
        CRUDOperation.UPDATE,
        CRUDOperation.DELETE,
        CRUDOperation.LIST,
        CRUDOperation.VIEW,
        CRUDOperation.DOCUMENT,
        CRUDOperation.EXPORT
    ],

    # Model Configuration
    primary_key_field="package_id",
    soft_delete_field="is_deleted",

    # Form Configuration
    create_form_template="engine/universal_create.html",
    edit_form_template="engine/universal_edit.html",

    # Default values
    default_field_values={
        'status': 'active',
        'currency_code': 'INR',
        'is_gst_exempt': False
    },

    # CRUD Field Control
    create_fields=[
        "package_name",
        "package_code",
        "package_family_id",
        "service_owner",
        "price",
        "selling_price",
        "max_discount",
        "currency_code",
        "hsn_code",
        "gst_rate",
        "cgst_rate",
        "sgst_rate",
        "igst_rate",
        "is_gst_exempt"
    ],

    edit_fields=[
        "package_name",
        "package_code",
        "package_family_id",
        "service_owner",
        "price",
        "selling_price",
        "max_discount",
        "currency_code",
        "hsn_code",
        "gst_rate",
        "cgst_rate",
        "sgst_rate",
        "igst_rate",
        "is_gst_exempt",
        "status"
    ],

    readonly_fields=[
        "package_id",
        "hospital_id",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
        "active_plans_count",
        "total_revenue",
        "avg_completion_rate",
        "total_bom_items",
        "bom_cost_estimate",
        "total_sessions",
        "total_duration_hours"
    ],

    # Validation Rules
    unique_fields=["package_name"],
    required_fields=[
        "package_name",
        "price",
        "status"
    ],

    # CRUD Permissions
    create_permission="packages_create",
    edit_permission="packages_edit",
    delete_permission="packages_delete",

    # Delete Configuration
    enable_soft_delete=True,
    cascade_delete=[],
    delete_confirmation_message="Are you sure you want to delete this package?",

    # Success Messages
    create_success_message="Package '{package_name}' created successfully",
    update_success_message="Package '{package_name}' updated successfully",
    delete_success_message="Package deleted successfully",

    # Calculated fields
    include_calculated_fields=[
        "active_plans_count",
        "total_revenue",
        "avg_completion_rate",
        "total_bom_items",
        "bom_cost_estimate",
        "total_sessions",
        "total_duration_hours"
    ]
)

# ========== SIMPLIFIED EXPORTS ==========
config = PACKAGE_CONFIG
filter_config = PACKAGE_ENTITY_FILTER_CONFIG
search_config = PACKAGE_SEARCH_CONFIG
