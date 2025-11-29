# Medicine Configuration Module
# File: app/config/modules/medicine_config.py

"""
Medicine Configuration - Single Entity Per File
Direct export pattern - no registration functions needed
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
# MEDICINE FIELD DEFINITIONS (Aligned with database model)
# Total: ~35 fields as per implementation plan
# =============================================================================

MEDICINE_FIELDS = [
    # ========== PRIMARY KEY ==========
    FieldDefinition(
        name="medicine_id",
        label="Medicine ID",
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
    FieldDefinition(
        name="branch_id",
        label="Branch",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=False,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        tab_group="basic_info",
        section="basic_details",
        view_order=1
    ),

    # ========== BASIC INFORMATION ==========
    FieldDefinition(
        name="medicine_name",
        label="Medicine Name",
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
            target_entity='medicines',
            search_fields=['medicine_name', 'generic_name'],
            display_template='{medicine_name}',
            value_field='medicine_name',
            filter_field='medicine_name',
            placeholder="Type to search medicines...",
            min_chars=2,
            max_results=20,
            preload_common=True,
            cache_results=True,
            additional_filters={'status': 'active'}
        ),
        placeholder="Enter medicine name",
        css_classes="text-wrap",
        width="220px",  # Increased column width for better readability
        tab_group="basic_info",
        section="basic_details",
        view_order=2
    ),
    FieldDefinition(
        name="generic_name",
        label="Generic Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        required=False,
        placeholder="Enter generic/chemical name",
        css_classes="text-wrap",
        width="200px",  # Increased column width for better readability
        tab_group="basic_info",
        section="basic_details",
        view_order=3
    ),
    FieldDefinition(
        name="dosage_form",
        label="Dosage Form",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        sortable=True,
        required=True,
        options=[
            {"value": "tablet", "label": "Tablet"},
            {"value": "capsule", "label": "Capsule"},
            {"value": "syrup", "label": "Syrup"},
            {"value": "injection", "label": "Injection"},
            {"value": "cream", "label": "Cream"},
            {"value": "ointment", "label": "Ointment"},
            {"value": "drops", "label": "Drops"},
            {"value": "powder", "label": "Powder"},
            {"value": "gel", "label": "Gel"},
            {"value": "lotion", "label": "Lotion"},
            {"value": "inhaler", "label": "Inhaler"},
            {"value": "patch", "label": "Patch"}
        ],
        tab_group="basic_info",
        section="basic_details",
        view_order=4
    ),
    FieldDefinition(
        name="unit_of_measure",
        label="Unit of Measure",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        options=[
            {"value": "strip", "label": "Strip"},
            {"value": "bottle", "label": "Bottle"},
            {"value": "vial", "label": "Vial"},
            {"value": "tube", "label": "Tube"},
            {"value": "box", "label": "Box"},
            {"value": "piece", "label": "Piece"},
            {"value": "pack", "label": "Pack"}
        ],
        tab_group="basic_info",
        section="basic_details",
        view_order=5
    ),
    FieldDefinition(
        name="medicine_type",
        label="Medicine Type",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        sortable=True,
        required=True,
        options=[
            {"value": "OTC", "label": "Over The Counter (OTC)"},
            {"value": "Prescription", "label": "Prescription"},
            {"value": "Product", "label": "Product"},
            {"value": "Consumable", "label": "Consumable"},
            {"value": "Misc", "label": "Miscellaneous"}
        ],
        tab_group="basic_info",
        section="basic_details",
        view_order=6
    ),

    # ========== RELATIONSHIP FIELDS ==========
    FieldDefinition(
        name="manufacturer_id",
        label="Manufacturer",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=False,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        entity_search_config=EntitySearchConfiguration(
            target_entity='manufacturers',
            search_fields=['manufacturer_name'],
            display_template='{manufacturer_name}',
            value_field='manufacturer_id',
            placeholder="Type to search manufacturers...",
            min_chars=2,
            max_results=20
        ),
        tab_group="relationships",
        section="supplier_manufacturer",
        view_order=1
    ),
    FieldDefinition(
        name="preferred_supplier_id",
        label="Preferred Supplier",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=False,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        entity_search_config=EntitySearchConfiguration(
            target_entity='suppliers',
            search_fields=['supplier_name'],
            display_template='{supplier_name}',
            value_field='supplier_id',
            placeholder="Type to search suppliers...",
            min_chars=2,
            max_results=20
        ),
        tab_group="relationships",
        section="supplier_manufacturer",
        view_order=2
    ),
    FieldDefinition(
        name="category_id",
        label="Category",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=False,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        entity_search_config=EntitySearchConfiguration(
            target_entity='medicine_categories',
            search_fields=['name'],
            display_template='{name}',
            value_field='category_id',
            placeholder="Select category...",
            min_chars=1,
            max_results=20
        ),
        tab_group="relationships",
        section="supplier_manufacturer",
        view_order=3
    ),

    # ========== GST INFORMATION ==========
    FieldDefinition(
        name="hsn_code",
        label="HSN Code",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        required=False,
        placeholder="Enter HSN code",
        help_text="HSN code for GST classification",
        tab_group="pricing_gst",
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
        tab_group="pricing_gst",
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
        tab_group="pricing_gst",
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
        tab_group="pricing_gst",
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
        tab_group="pricing_gst",
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
        help_text="Check if medicine is GST exempt",
        tab_group="pricing_gst",
        section="gst_info",
        view_order=6
    ),
    FieldDefinition(
        name="gst_inclusive",
        label="GST Inclusive in MRP",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value=False,
        help_text="Check if MRP includes GST",
        tab_group="pricing_gst",
        section="gst_info",
        view_order=7
    ),

    # ========== PRICING INFORMATION ==========
    FieldDefinition(
        name="cost_price",
        label="Cost Price",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter cost price",
        help_text="Cost price for profit calculation",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=1
    ),
    FieldDefinition(
        name="mrp",
        label="MRP (Maximum Retail Price)",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        filter_type=FilterType.NUMERIC_RANGE,
        sortable=True,
        required=True,
        placeholder="Enter MRP",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=2
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
        help_text="Actual selling price (can be less than MRP)",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=3
    ),
    FieldDefinition(
        name="last_purchase_price",
        label="Last Purchase Price",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=4
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
        view_order=5
    ),
    FieldDefinition(
        name="mrp_effective_date",
        label="MRP Effective Date",
        field_type=FieldType.DATE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        help_text="Date when MRP was last updated",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=6
    ),
    FieldDefinition(
        name="previous_mrp",
        label="Previous MRP",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        help_text="Previous MRP for tracking",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=7
    ),

    # ========== INVENTORY MANAGEMENT ==========
    FieldDefinition(
        name="safety_stock",
        label="Safety Stock",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Enter minimum stock level",
        help_text="Minimum stock level for reorder",
        tab_group="inventory",
        section="inventory_details",
        view_order=1
    ),
    FieldDefinition(
        name="current_stock",
        label="Current Stock",
        field_type=FieldType.NUMBER,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        sortable=True,
        tab_group="inventory",
        section="inventory_details",
        view_order=2
    ),
    FieldDefinition(
        name="priority",
        label="Priority",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        options=[
            {"value": "high", "label": "High"},
            {"value": "medium", "label": "Medium"},
            {"value": "low", "label": "Low"}
        ],
        default_value="medium",
        help_text="Priority level for reordering",
        tab_group="inventory",
        section="inventory_details",
        view_order=3
    ),

    # ========== BUSINESS RULES ==========
    FieldDefinition(
        name="prescription_required",
        label="Prescription Required",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value=False,
        help_text="Check if prescription is required",
        tab_group="basic_info",
        section="business_rules",
        view_order=1
    ),
    FieldDefinition(
        name="is_consumable",
        label="Is Consumable",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value=False,
        help_text="Check if used in procedures",
        tab_group="basic_info",
        section="business_rules",
        view_order=2
    ),

    # Bulk Discount Eligibility (Added 2025-11-27)
    FieldDefinition(
        name="bulk_discount_eligible",
        label="Bulk Discount Eligible",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        default_value=False,
        help_text="Enable to allow bulk discount for this medicine",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=8
    ),
    FieldDefinition(
        name="bulk_discount_percent",
        label="Bulk Discount %",
        field_type=FieldType.PERCENTAGE,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        default_value=0,
        help_text="Discount percentage when bulk discount applies",
        tab_group="pricing_gst",
        section="pricing_info",
        view_order=9
    ),

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
            {"value": "inactive", "label": "Inactive"},
            {"value": "discontinued", "label": "Discontinued"}
        ],
        default_value="active",
        tab_group="basic_info",
        section="business_rules",
        view_order=3
    ),

    # ========== GL ACCOUNT ==========
    FieldDefinition(
        name="default_gl_account",
        label="Default GL Account",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        tab_group="relationships",
        section="gl_mapping",
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
        name="stock_value",
        label="Current Stock Value",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Current stock × Cost price",
        tab_group="inventory",
        section="calculated_fields",
        view_order=1
    ),
    FieldDefinition(
        name="reorder_status",
        label="Reorder Status",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Based on current stock vs safety stock",
        tab_group="inventory",
        section="calculated_fields",
        view_order=2
    ),
    FieldDefinition(
        name="last_purchase_info",
        label="Last Purchase Info",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        help_text="Last purchase date and supplier",
        tab_group="inventory",
        section="calculated_fields",
        view_order=3
    )
]

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

MEDICINE_FORM_SECTIONS = {
    "system_fields": SectionDefinition(
        key="system_fields",
        title="System Fields",
        icon="fas fa-database",
        columns=2,
        order=1,
        collapsible=True,
        default_collapsed=True
    ),
    "basic_details": SectionDefinition(
        key="basic_details",
        title="Basic Information",
        icon="fas fa-info-circle",
        columns=2,
        order=2,
        collapsible=False,
        default_collapsed=False
    ),
    "business_rules": SectionDefinition(
        key="business_rules",
        title="Business Rules",
        icon="fas fa-cogs",
        columns=2,
        order=3,
        collapsible=True,
        default_collapsed=False
    ),
    "pricing_info": SectionDefinition(
        key="pricing_info",
        title="Pricing Information",
        icon="fas fa-rupee-sign",
        columns=2,
        order=4,
        collapsible=False,
        default_collapsed=False
    ),
    "gst_info": SectionDefinition(
        key="gst_info",
        title="GST Information",
        icon="fas fa-file-invoice",
        columns=2,
        order=5,
        collapsible=True,
        default_collapsed=False
    ),
    "inventory_details": SectionDefinition(
        key="inventory_details",
        title="Inventory Details",
        icon="fas fa-boxes",
        columns=2,
        order=6,
        collapsible=False,
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
    "supplier_manufacturer": SectionDefinition(
        key="supplier_manufacturer",
        title="Supplier & Manufacturer",
        icon="fas fa-industry",
        columns=2,
        order=8,
        collapsible=True,
        default_collapsed=False
    ),
    "gl_mapping": SectionDefinition(
        key="gl_mapping",
        title="GL Account Mapping",
        icon="fas fa-book",
        columns=2,
        order=9,
        collapsible=True,
        default_collapsed=True
    ),
    "audit_info": SectionDefinition(
        key="audit_info",
        title="Audit Information",
        icon="fas fa-history",
        columns=2,
        order=10,
        collapsible=True,
        default_collapsed=True
    ),
    "technical": SectionDefinition(
        key="technical",
        title="Technical Details",
        icon="fas fa-server",
        columns=2,
        order=11,
        collapsible=True,
        default_collapsed=True
    )
}

MEDICINE_SECTIONS = MEDICINE_FORM_SECTIONS

# =============================================================================
# TAB DEFINITIONS
# =============================================================================

MEDICINE_TABS = {
    'basic_info': TabDefinition(
        key='basic_info',
        label='Basic Info',
        icon='fas fa-pills',
        sections={
            'basic_details': MEDICINE_FORM_SECTIONS['basic_details'],
            'business_rules': MEDICINE_FORM_SECTIONS['business_rules']
        },
        order=0,
        default_active=True
    ),
    'pricing_gst': TabDefinition(
        key='pricing_gst',
        label='Pricing & GST',
        icon='fas fa-money-bill',
        sections={
            'pricing_info': MEDICINE_FORM_SECTIONS['pricing_info'],
            'gst_info': MEDICINE_FORM_SECTIONS['gst_info']
        },
        order=1
    ),
    'inventory': TabDefinition(
        key='inventory',
        label='Inventory',
        icon='fas fa-warehouse',
        sections={
            'inventory_details': MEDICINE_FORM_SECTIONS['inventory_details'],
            'calculated_fields': MEDICINE_FORM_SECTIONS['calculated_fields']
        },
        order=2
    ),
    'relationships': TabDefinition(
        key='relationships',
        label='Relationships',
        icon='fas fa-link',
        sections={
            'supplier_manufacturer': MEDICINE_FORM_SECTIONS['supplier_manufacturer'],
            'gl_mapping': MEDICINE_FORM_SECTIONS['gl_mapping']
        },
        order=3
    ),
    'system_info': TabDefinition(
        key='system_info',
        label='System Info',
        icon='fas fa-cogs',
        sections={
            'audit_info': MEDICINE_FORM_SECTIONS['audit_info'],
            'technical': MEDICINE_FORM_SECTIONS['technical']
        },
        order=4
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

MEDICINE_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    responsive_breakpoint='md',
    tabs=MEDICINE_TABS,
    default_tab='basic_info',
    sticky_tabs=False,
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "medicine_id",
        "primary_label": "Medicine ID",
        "title_field": "medicine_name",
        "title_label": "Medicine",
        "status_field": "status",
        "secondary_fields": [
            {"field": "generic_name", "label": "Generic Name", "icon": "fas fa-atom"},
            {"field": "dosage_form", "label": "Form", "icon": "fas fa-capsules"},
            {"field": "mrp", "label": "MRP", "icon": "fas fa-rupee-sign"},
            {"field": "current_stock", "label": "Stock", "icon": "fas fa-boxes"}
        ]
    }
)

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

MEDICINE_ACTIONS = [
    ActionDefinition(
        id="create",
        label="New Medicine",
        icon="fas fa-plus",
        url_pattern="/universal/{entity_type}/create",
        button_type=ButtonType.PRIMARY,
        permission="medicines_create",
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
        route_params={"entity_type": "medicines", "item_id": "{medicine_id}"},
        button_type=ButtonType.INFO,
        permission="medicines_view",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=10
    ),
    ActionDefinition(
        id="edit",
        label="Edit Medicine",
        icon="fas fa-edit",
        route_name="universal_views.universal_edit_view",
        route_params={"entity_type": "medicines", "item_id": "{medicine_id}"},
        button_type=ButtonType.PRIMARY,
        permission="medicines_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=20
    ),
    ActionDefinition(
        id="print",
        label="Print Details",
        icon="fas fa-print",
        route_name="universal_views.universal_document_view",
        route_params={
            "entity_type": "medicines",
            "item_id": "{medicine_id}",
            "doc_type": "profile"
        },
        button_type=ButtonType.SECONDARY,
        permission="medicines_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        button_group="document_ops",
        order=30
    ),
    ActionDefinition(
        id="export",
        label="Export Data",
        icon="fas fa-download",
        route_name="universal_views.universal_export_view",
        route_params={"entity_type": "medicines", "item_id": "{medicine_id}"},
        button_type=ButtonType.INFO,
        permission="medicines_export",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=40
    ),
    ActionDefinition(
        id="delete",
        label="Delete Medicine",
        icon="fas fa-trash",
        url_pattern="/api/universal/{entity_type}/{item_id}/delete",
        button_type=ButtonType.DANGER,
        permission="medicines_delete",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=100,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this medicine? This action cannot be undone.",
        conditions={
            "status": ["inactive", "discontinued"]
        }
    ),
    ActionDefinition(
        id="deactivate",
        label="Deactivate",
        icon="fas fa-pause",
        url_pattern="/api/universal/{entity_type}/{item_id}/deactivate",
        button_type=ButtonType.WARNING,
        permission="medicines_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=90,
        confirmation_required=True,
        confirmation_message="Are you sure you want to deactivate this medicine?",
        conditions={
            "status": ["active"]
        }
    ),
    ActionDefinition(
        id="activate",
        label="Activate",
        icon="fas fa-play",
        url_pattern="/api/universal/{entity_type}/{item_id}/activate",
        button_type=ButtonType.SUCCESS,
        permission="medicines_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=95,
        confirmation_required=True,
        confirmation_message="Are you sure you want to activate this medicine?",
        conditions={
            "status": ["inactive"]
        }
    )
]

# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

MEDICINE_SUMMARY_CARDS = [
    {
        "id": "total_medicines",
        "label": "Total Medicines",
        "icon": "fas fa-pills",
        "field": "total_count",
        "type": "number",
        "icon_css": "stat-card-icon primary",
        "filterable": True,
        "visible": True,
        "order": 1
    },
    {
        "id": "low_stock_items",
        "label": "Low Stock Items",
        "icon": "fas fa-exclamation-triangle",
        "field": "low_stock_count",
        "type": "number",
        "icon_css": "stat-card-icon danger",
        "filterable": True,
        "visible": True,
        "order": 2
    },
    {
        "id": "total_inventory_value",
        "label": "Total Inventory Value",
        "icon": "fas fa-rupee-sign",
        "field": "total_inventory_value",
        "type": "currency",
        "icon_css": "stat-card-icon success",
        "filterable": False,
        "visible": True,
        "order": 3
    },
    {
        "id": "active_medicines",
        "label": "Active Medicines",
        "icon": "fas fa-check-circle",
        "field": "active_count",
        "type": "number",
        "icon_css": "stat-card-icon info",
        "filterable": True,
        "filter_field": "status",
        "filter_value": "active",
        "visible": True,
        "order": 4
    }
]

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

MEDICINE_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'created_from': FilterCategory.DATE,
    'created_to': FilterCategory.DATE,
    'modified_from': FilterCategory.DATE,
    'modified_to': FilterCategory.DATE,
    'mrp_effective_date_from': FilterCategory.DATE,
    'mrp_effective_date_to': FilterCategory.DATE,

    # Selection filters
    'status': FilterCategory.SELECTION,
    'medicine_type': FilterCategory.SELECTION,
    'dosage_form': FilterCategory.SELECTION,
    'priority': FilterCategory.SELECTION,
    'is_gst_exempt': FilterCategory.SELECTION,
    'prescription_required': FilterCategory.SELECTION,
    'is_consumable': FilterCategory.SELECTION,

    # Search filters
    'search': FilterCategory.SEARCH,
    'q': FilterCategory.SEARCH,
    'medicine_name': FilterCategory.SEARCH,
    'generic_name': FilterCategory.SEARCH,
    'hsn_code': FilterCategory.SEARCH,

    # Amount filters
    'mrp': FilterCategory.AMOUNT,
    'selling_price': FilterCategory.AMOUNT,
    'cost_price': FilterCategory.AMOUNT,
    'current_stock': FilterCategory.AMOUNT,

    # Relationship filters
    'medicine_id': FilterCategory.RELATIONSHIP,
    'manufacturer_id': FilterCategory.RELATIONSHIP,
    'preferred_supplier_id': FilterCategory.RELATIONSHIP,
    'category_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP
}

MEDICINE_DEFAULT_FILTERS = {
    'status': 'active'
}

MEDICINE_CATEGORY_CONFIGS = {
    FilterCategory.SELECTION: {
        'process_empty_as_all': True,
        'case_sensitive': False
    },
    FilterCategory.SEARCH: {
        'min_length': 2,
        'search_fields': ['medicine_name', 'generic_name', 'hsn_code'],
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

MEDICINE_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='medicines',
    filter_mappings={
        'medicine_type': {
            'options': [
                {'value': 'OTC', 'label': 'Over The Counter (OTC)'},
                {'value': 'Prescription', 'label': 'Prescription'},
                {'value': 'Product', 'label': 'Product'},
                {'value': 'Consumable', 'label': 'Consumable'},
                {'value': 'Misc', 'label': 'Miscellaneous'}
            ]
        },
        'dosage_form': {
            'options': [
                {'value': 'tablet', 'label': 'Tablet'},
                {'value': 'capsule', 'label': 'Capsule'},
                {'value': 'syrup', 'label': 'Syrup'},
                {'value': 'injection', 'label': 'Injection'},
                {'value': 'cream', 'label': 'Cream'},
                {'value': 'ointment', 'label': 'Ointment'},
                {'value': 'drops', 'label': 'Drops'},
                {'value': 'powder', 'label': 'Powder'},
                {'value': 'gel', 'label': 'Gel'},
                {'value': 'lotion', 'label': 'Lotion'},
                {'value': 'inhaler', 'label': 'Inhaler'},
                {'value': 'patch', 'label': 'Patch'}
            ]
        },
        'medicine_name': {
            'field': 'medicine_name',
            'type': 'text',
            'label': 'Medicine Name',
            'placeholder': 'Search medicine name...',
            'search_in_table': True
        },
        'status': {
            'options': [
                {'value': 'active', 'label': 'Active'},
                {'value': 'inactive', 'label': 'Inactive'},
                {'value': 'discontinued', 'label': 'Discontinued'}
            ]
        },
        'priority': {
            'options': [
                {'value': 'high', 'label': 'High'},
                {'value': 'medium', 'label': 'Medium'},
                {'value': 'low', 'label': 'Low'}
            ]
        },
        'is_gst_exempt': {
            'options': [
                {'value': 'true', 'label': 'Yes'},
                {'value': 'false', 'label': 'No'}
            ]
        },
        'prescription_required': {
            'options': [
                {'value': 'true', 'label': 'Yes'},
                {'value': 'false', 'label': 'No'}
            ]
        }
    }
)

# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================

MEDICINE_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='medicines',
    search_endpoint='/api/universal/medicines/search',
    search_fields=['medicine_name', 'generic_name', 'medicine_type'],
    display_template='{medicine_name} ({medicine_type})',
    value_field='medicine_name',
    min_chars=1,
    max_results=10,
    sort_field='medicine_name',
    additional_filters={'status': 'active'}
)

# =============================================================================
# PERMISSIONS CONFIGURATION
# =============================================================================

MEDICINE_PERMISSIONS = {
    "list": "medicines_list",
    "view": "medicines_view",
    "create": "medicines_create",
    "edit": "medicines_edit",
    "delete": "medicines_delete",
    "export": "medicines_export",
    "bulk": "medicines_bulk"
}

# =============================================================================
# DOCUMENT CONFIGURATIONS
# =============================================================================

MEDICINE_PROFILE_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.REPORT,
    title="Medicine Profile",
    page_size=PageSize.A4,
    orientation=Orientation.PORTRAIT,
    print_layout_type=PrintLayoutType.SIMPLE_WITH_HEADER,
    show_logo=True,
    show_company_info=True,
    header_text="MEDICINE MASTER PROFILE",
    visible_tabs=["basic_info", "pricing_gst", "inventory"],
    hidden_sections=[],
    signature_fields=[
        {"label": "Verified By", "width": "200px"},
        {"label": "Approved By", "width": "200px"}
    ],
    show_footer=True,
    footer_text="This is a system generated document",
    show_print_info=True,
    allowed_formats=["pdf", "print", "excel", "word"]
)

MEDICINE_DOCUMENT_CONFIGS = {
    "profile": MEDICINE_PROFILE_CONFIG
}

# =============================================================================
# COMPLETE MEDICINE CONFIGURATION
# =============================================================================

MEDICINE_CONFIG = EntityConfiguration(
    # ========== BASIC INFORMATION (REQUIRED) ==========
    entity_type="medicines",
    name="Medicine",
    plural_name="Medicines",
    service_name="medicines",
    table_name="medicines",
    primary_key="medicine_id",
    title_field="medicine_name",
    subtitle_field="generic_name",
    icon="fas fa-pills",
    page_title="Medicine Management",
    description="Manage medicines and pharmaceutical products",
    searchable_fields=["medicine_name", "generic_name", "hsn_code"],
    default_sort_field="medicine_name",
    default_sort_direction="asc",

    # ========== CORE CONFIGURATIONS ==========
    fields=MEDICINE_FIELDS,
    section_definitions=MEDICINE_FORM_SECTIONS,
    form_section_definitions=MEDICINE_FORM_SECTIONS,
    actions=MEDICINE_ACTIONS,
    summary_cards=MEDICINE_SUMMARY_CARDS,
    permissions=MEDICINE_PERMISSIONS,

    # ========== OPTIONAL CONFIGURATIONS ==========
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,

    # View Layout Configuration
    view_layout=MEDICINE_VIEW_LAYOUT,

    # Filter Configuration
    filter_category_mapping=MEDICINE_FILTER_CATEGORY_MAPPING,
    default_filters=MEDICINE_DEFAULT_FILTERS,
    category_configs=MEDICINE_CATEGORY_CONFIGS,

    # Date and Amount Fields
    primary_date_field="created_at",
    primary_amount_field="mrp",

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
    primary_key_field="medicine_id",
    soft_delete_field="is_deleted",

    # Form Configuration
    create_form_template="engine/universal_create.html",
    edit_form_template="engine/universal_edit.html",

    # Default values
    default_field_values={
        'status': 'active',
        'currency_code': 'INR',
        'priority': 'medium',
        'is_gst_exempt': False,
        'gst_inclusive': False,
        'prescription_required': False,
        'is_consumable': False
    },

    # CRUD Field Control
    create_fields=[
        "medicine_name",
        "generic_name",
        "dosage_form",
        "unit_of_measure",
        "medicine_type",
        "manufacturer_id",
        "preferred_supplier_id",
        "category_id",
        "hsn_code",
        "gst_rate",
        "cgst_rate",
        "sgst_rate",
        "igst_rate",
        "is_gst_exempt",
        "gst_inclusive",
        "cost_price",
        "mrp",
        "selling_price",
        "currency_code",
        "mrp_effective_date",
        "safety_stock",
        "priority",
        "prescription_required",
        "is_consumable",
        "default_gl_account"
    ],

    edit_fields=[
        "medicine_name",
        "generic_name",
        "dosage_form",
        "unit_of_measure",
        "medicine_type",
        "manufacturer_id",
        "preferred_supplier_id",
        "category_id",
        "hsn_code",
        "gst_rate",
        "cgst_rate",
        "sgst_rate",
        "igst_rate",
        "is_gst_exempt",
        "gst_inclusive",
        "cost_price",
        "mrp",
        "selling_price",
        "currency_code",
        "mrp_effective_date",
        "safety_stock",
        "priority",
        "prescription_required",
        "is_consumable",
        "status",
        "default_gl_account"
    ],

    readonly_fields=[
        "medicine_id",
        "hospital_id",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
        "current_stock",
        "last_purchase_price",
        "previous_mrp",
        "stock_value",
        "reorder_status",
        "last_purchase_info"
    ],

    # Validation Rules
    unique_fields=["medicine_name"],
    required_fields=[
        "medicine_name",
        "dosage_form",
        "unit_of_measure",
        "medicine_type",
        "mrp",
        "status"
    ],

    # CRUD Permissions
    create_permission="medicines_create",
    edit_permission="medicines_edit",
    delete_permission="medicines_delete",

    # Delete Configuration
    enable_soft_delete=True,
    cascade_delete=[],
    delete_confirmation_message="Are you sure you want to delete this medicine? This action cannot be undone.",

    # Success Messages
    create_success_message="Medicine '{medicine_name}' created successfully",
    update_success_message="Medicine '{medicine_name}' updated successfully",
    delete_success_message="Medicine deleted successfully",

    # Document Generation Support
    document_enabled=True,
    document_configs=MEDICINE_DOCUMENT_CONFIGS,
    default_document="profile",

    # Calculated fields
    include_calculated_fields=[
        "current_stock",
        "stock_value",
        "reorder_status",
        "last_purchase_info"
    ],

    # Document permissions
    document_permissions={
        "profile": "medicines_view"
    }
)

# ========== SIMPLIFIED EXPORTS ==========
config = MEDICINE_CONFIG
filter_config = MEDICINE_ENTITY_FILTER_CONFIG
search_config = MEDICINE_SEARCH_CONFIG
