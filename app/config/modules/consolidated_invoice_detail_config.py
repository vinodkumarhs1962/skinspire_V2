"""
Consolidated Invoice Detail View Configuration
Shows individual invoices (parent + children) for a consolidated group
Uses patient_invoices fields for table, consolidated summary cards for header
"""

from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, FieldType, SectionDefinition,
    TabDefinition, ActionDefinition, ButtonType, ActionDisplayType,
    FilterOperator, EntityCategory, CRUDOperation
)
from app.config.filter_categories import FilterCategory

# Import patient invoice fields for reuse
from app.config.modules.patient_invoice_config import PATIENT_INVOICE_FIELDS

# Import consolidated summary cards for reuse
from app.config.modules.consolidated_patient_invoices_config import CONSOLIDATED_INVOICE_SUMMARY_CARDS

# Note: Patient info will be shown as a separate header section above summary cards
# Not as a summary card itself

# =============================================================================
# ACTIONS CONFIGURATION
# =============================================================================

CONSOLIDATED_DETAIL_ACTIONS = [
    # === TOOLBAR ACTIONS ===
    ActionDefinition(
        id="back",
        label="Back to Consolidated Invoices",
        icon="fas fa-arrow-left",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "consolidated_patient_invoices"},
        show_in_list=False,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=1
    ),

    ActionDefinition(
        id="print_all",
        label="Print All Invoices",
        icon="fas fa-print",
        button_type=ButtonType.SECONDARY,
        url_pattern="/invoice/consolidated_invoice/print_all/{parent_invoice_id}",
        show_in_list=False,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=2
    ),

    # === LINE ITEM ACTIONS ===
    ActionDefinition(
        id="view_invoice",
        label="View",
        icon="fas fa-eye",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_detail_view",
        route_params={"entity_type": "patient_invoices", "item_id": "{invoice_id}"},
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=10
    ),

    ActionDefinition(
        id="print_invoice",
        label="Print",
        icon="fas fa-print",
        button_type=ButtonType.SECONDARY,
        url_pattern="/billing/invoice/print/{invoice_id}",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=11
    ),

    ActionDefinition(
        id="delete_invoice",
        label="Delete",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        url_pattern="/billing/invoice/delete/{invoice_id}",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_delete",
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this invoice?",
        order=12
    ),
]

# =============================================================================
# PATIENT INFO SECTION (For future use in detail view)
# =============================================================================

PATIENT_INFO_SECTION = SectionDefinition(
    key="patient_info",
    title="Patient Information",
    icon="fas fa-user-circle",
    columns=2,
    order=1,
    collapsible=False,
    default_collapsed=False,
    show_divider=True
)

# =============================================================================
# ENTITY CONFIGURATION
# =============================================================================

CONSOLIDATED_INVOICE_DETAIL_CONFIG = EntityConfiguration(
    # === BASIC INFO ===
    entity_type="consolidated_invoice_detail",
    name="Invoice Breakdown",
    plural_name="Invoice Breakdown",
    service_name="consolidated_patient_invoices",  # Use same service
    table_name="v_patient_invoices",  # Individual invoices view
    primary_key="invoice_id",
    title_field="invoice_number",
    subtitle_field="patient_name",
    icon="fas fa-layer-group",
    page_title="Invoice Breakdown",
    description="Individual invoices in consolidated group",

    # === FIELDS & ACTIONS ===
    # Use patient invoice fields (individual invoice columns)
    fields=PATIENT_INVOICE_FIELDS,
    actions=CONSOLIDATED_DETAIL_ACTIONS,

    # === SEARCH & SORT ===
    searchable_fields=[],  # No search in detail view
    enable_complex_search=False,  # Disable search card
    show_filter_card=False,  # Hide entire filter card
    show_info_card=True,  # Show info header card
    default_sort_field="split_sequence",
    default_sort_direction="asc",

    # === CATEGORY & PERMISSIONS ===
    entity_category=EntityCategory.TRANSACTION,
    allowed_operations=[CRUDOperation.LIST, CRUDOperation.VIEW],  # Read-only

    permissions={
        'view': 'billing.view',
        'list': 'billing.view'
    },

    # === SUMMARY CARDS ===
    # Use consolidated summary cards (total amount, GST, etc.)
    summary_cards=CONSOLIDATED_INVOICE_SUMMARY_CARDS,

    # === FILTER CONFIGURATION ===
    # No filters in detail view
    filter_category_mapping={},
    default_filters={},
    category_configs={},

    # === LIST VIEW CONFIG ===
    enable_export=False,
    items_per_page=50  # Show all invoices in group
)

# =============================================================================
# EXPORTS (Required for Universal Engine to load this configuration)
# =============================================================================

config = CONSOLIDATED_INVOICE_DETAIL_CONFIG
