"""
Consolidated Patient Invoices Configuration
Phase 3: Tax Compliance - Multi-Invoice Transactions
Shows only parent invoices that have split children
"""

from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, FieldType, SectionDefinition,
    TabDefinition, ActionDefinition, ButtonType, ActionDisplayType,
    FilterOperator, EntityCategory, CRUDOperation, EntitySearchConfiguration,
    FilterType
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

# Filter category mapping (field name -> category)
CONSOLIDATED_INVOICE_FILTER_CATEGORY_MAPPING = {
    'patient_name': FilterCategory.SEARCH,  # Autocomplete search
    'payment_status': FilterCategory.SELECTION,
    'aging_bucket': FilterCategory.SELECTION,
    'invoice_date': FilterCategory.DATE,
    'consolidated_grand_total': FilterCategory.AMOUNT,
    'consolidated_balance_due': FilterCategory.AMOUNT,
}

# Default filters
CONSOLIDATED_INVOICE_DEFAULT_FILTERS = {}

# Category configs
CONSOLIDATED_INVOICE_CATEGORY_CONFIGS = {}

# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

CONSOLIDATED_INVOICE_SUMMARY_CARDS = [
    {
        'id': 'total_count',
        'label': 'Total Consolidated Invoices',
        'field': 'total_count',
        'icon': 'fas fa-folder-open',
        'icon_css': 'stat-card-icon primary',
        'type': 'number'
    },
    {
        'id': 'total_amount',
        'label': 'Total Amount',
        'field': 'consolidated_grand_total_sum',
        'icon': 'fas fa-rupee-sign',
        'icon_css': 'stat-card-icon success',
        'type': 'currency'
    },
    {
        'id': 'total_gst',
        'label': 'Total GST',
        'field': 'total_gst_sum',
        'icon': 'fas fa-percent',
        'icon_css': 'stat-card-icon info',
        'type': 'currency'
    },
    {
        'id': 'total_balance',
        'label': 'Total Balance Due',
        'field': 'consolidated_balance_due_sum',
        'icon': 'fas fa-exclamation-circle',
        'icon_css': 'stat-card-icon warning',
        'type': 'currency'
    }
]

# =============================================================================
# FIELD DEFINITIONS
# =============================================================================

CONSOLIDATED_INVOICE_FIELDS = [
    # === PRIMARY IDENTIFICATION ===
    FieldDefinition(
        name="invoice_id",
        label="Invoice ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        filterable=False,
        readonly=True
    ),

    FieldDefinition(
        name="invoice_number",
        label="Invoice Number",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        searchable=True,
        view_order=1
    ),

    FieldDefinition(
        name="invoice_date",
        label="Invoice Date",
        field_type=FieldType.DATETIME,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        sortable=True,
        view_order=2
    ),

    # === PATIENT INFORMATION ===
    FieldDefinition(
        name="patient_id",
        label="Patient ID",
        field_type=FieldType.TEXT,  # Changed from UUID to prevent FK relationship loading
        show_in_list=False,
        show_in_detail=False,
        filterable=True,  # Enable filtering by patient_id (for autocomplete)
        readonly=True
        # Note: patient_name is already in the view, don't load patient relationship
    ),

    FieldDefinition(
        name="patient_name",
        label="Patient Name",
        field_type=FieldType.TEXT,  # Not a foreign key - it's a display field from the view
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        searchable=True,
        sortable=True,
        readonly=True,
        view_order=3,
        filter_type=FilterType.AUTOCOMPLETE,  # Autocomplete filter with initial list
        filter_operator=FilterOperator.EQUALS,
        autocomplete_config={
            'entity_type': 'patients',
            'api_endpoint': '/api/universal/patients/search',
            'value_field': 'patient_id',        # Field to filter on (UUID)
            'display_field': 'label',           # Field to display
            'placeholder': 'Search patients by name or MRN...',
            'min_chars': 0,                     # 0 = show initial list on focus
            'initial_load_limit': 20,           # Number of recent patients to show
            'search_limit': 10                  # Results when searching
        }
    ),

    FieldDefinition(
        name="patient_mrn",
        label="MRN",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=False,  # Searchable via search box, no need for separate filter
        searchable=True,
        view_order=4
    ),

    # === SPLIT INVOICE TRACKING ===
    FieldDefinition(
        name="child_invoice_count",
        label="Child Invoices",
        field_type=FieldType.INTEGER,
        show_in_list=False,  # Hidden from list view
        show_in_detail=True,
        filterable=False,  # Remove from filters
        view_order=10,
        help_text="Number of split invoices (excludes parent)"
    ),

    FieldDefinition(
        name="total_invoice_count",
        label="Total Invoices",
        field_type=FieldType.INTEGER,
        show_in_list=True,
        show_in_detail=True,
        filterable=False,
        view_order=11,
        help_text="Total invoices in group (parent + children)"
    ),

    FieldDefinition(
        name="service_invoice_count",
        label="Service Invoices",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        filterable=False,
        view_order=12
    ),

    FieldDefinition(
        name="medicine_invoice_count",
        label="Medicine Invoices",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        filterable=False,
        view_order=13
    ),

    FieldDefinition(
        name="exempt_invoice_count",
        label="Exempt Invoices",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        filterable=False,
        view_order=14
    ),

    FieldDefinition(
        name="prescription_invoice_count",
        label="Prescription Invoices",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        filterable=False,
        view_order=15
    ),

    # === CONSOLIDATED AMOUNTS ===
    FieldDefinition(
        name="consolidated_grand_total",
        label="Grand Total",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        filter_operator=FilterOperator.GREATER_THAN_OR_EQUAL,
        view_order=20
    ),

    FieldDefinition(
        name="consolidated_paid_amount",
        label="Paid Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        filterable=False,
        view_order=21
    ),

    FieldDefinition(
        name="consolidated_balance_due",
        label="Balance Due",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        filter_operator=FilterOperator.GREATER_THAN,
        view_order=22
    ),

    # === PAYMENT STATUS ===
    FieldDefinition(
        name="payment_status",
        label="Payment Status",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        view_order=30,
        options=[
            {"value": "paid", "label": "Paid"},
            {"value": "partial", "label": "Partial"},
            {"value": "unpaid", "label": "Unpaid"}
        ]
    ),

    # === AGING ===
    FieldDefinition(
        name="invoice_age_days",
        label="Age (Days)",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        filterable=False,  # Not needed, we have aging_bucket filter
        view_order=40
    ),

    FieldDefinition(
        name="aging_bucket",
        label="Aging",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        view_order=41,
        options=[
            {"value": "0-30 days", "label": "0-30 days"},
            {"value": "31-60 days", "label": "31-60 days"},
            {"value": "61-90 days", "label": "61-90 days"},
            {"value": "90+ days", "label": "90+ days"}
        ]
    ),

    # === TENANT & BRANCH ===
    FieldDefinition(
        name="hospital_id",
        label="Hospital ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        filterable=False
    ),

    FieldDefinition(
        name="branch_id",
        label="Branch ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        filterable=False
    ),

    FieldDefinition(
        name="hospital_name",
        label="Hospital",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        filterable=False,
        view_order=50
    ),

    FieldDefinition(
        name="branch_name",
        label="Branch",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        filterable=False,
        view_order=51
    ),
]

# =============================================================================
# ACTIONS CONFIGURATION
# =============================================================================

CONSOLIDATED_INVOICE_ACTIONS = [
    # === TOOLBAR ACTIONS (for list view) ===
    ActionDefinition(
        id="back",
        label="Back",
        icon="fas fa-arrow-left",
        button_type=ButtonType.SECONDARY,
        url_pattern="javascript:history.back()",
        show_in_list=False,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=0
    ),

    # === LINE ITEM ACTIONS ===
    ActionDefinition(
        id="view_child_invoices",
        label="View Child Invoices",
        icon="fas fa-layer-group",
        button_type=ButtonType.INFO,
        url_pattern="/universal/consolidated_invoice_detail/{invoice_id}",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=1
    ),

    ActionDefinition(
        id="collect_payment",
        label="Collect Payment",
        icon="fas fa-money-bill-wave",
        button_type=ButtonType.SUCCESS,
        route_name="billing_views.record_invoice_payment_enhanced",
        route_params={"invoice_id": "{invoice_id}"},
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_payment_create",
        order=2,
        conditions={"payment_status": ["unpaid", "partial"]}
    ),

    # REMOVED: Back button in list view - not needed, use browser back button
    # Back button in detail view is in consolidated_invoice_detail_config.py
]

# =============================================================================
# ENTITY CONFIGURATION
# =============================================================================

CONSOLIDATED_PATIENT_INVOICES_CONFIG = EntityConfiguration(
    # === BASIC INFO ===
    entity_type="consolidated_patient_invoices",
    name="Consolidated Invoice",
    plural_name="Consolidated Invoices",
    service_name="consolidated_patient_invoices",
    table_name="v_consolidated_patient_invoices",
    primary_key="invoice_id",
    title_field="invoice_number",
    subtitle_field="patient_name",
    icon="fas fa-folder-open",
    page_title="Patient Consolidated Invoices",
    description="Multi-invoice transactions for tax compliance (Phase 3)",

    # === FIELDS & ACTIONS ===
    fields=CONSOLIDATED_INVOICE_FIELDS,
    actions=CONSOLIDATED_INVOICE_ACTIONS,

    # === SEARCH & SORT ===
    searchable_fields=["invoice_number", "patient_name", "patient_mrn"],
    default_sort_field="invoice_date",
    default_sort_direction="desc",

    # === CATEGORY & PERMISSIONS ===
    entity_category=EntityCategory.TRANSACTION,
    allowed_operations=[CRUDOperation.LIST, CRUDOperation.VIEW],  # Read-only

    permissions={
        'view': 'billing.view',
        'list': 'billing.view'
    },

    # === SUMMARY CARDS ===
    summary_cards=CONSOLIDATED_INVOICE_SUMMARY_CARDS,

    # === FILTER CONFIGURATION ===
    filter_category_mapping=CONSOLIDATED_INVOICE_FILTER_CATEGORY_MAPPING,
    default_filters=CONSOLIDATED_INVOICE_DEFAULT_FILTERS,
    category_configs=CONSOLIDATED_INVOICE_CATEGORY_CONFIGS,

    # === LIST VIEW CONFIG ===
    enable_export=True,
    items_per_page=20
)

# =============================================================================
# EXPORTS (Required for Universal Engine to load this configuration)
# =============================================================================

config = CONSOLIDATED_PATIENT_INVOICES_CONFIG
