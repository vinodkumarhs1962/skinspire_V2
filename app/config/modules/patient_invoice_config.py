"""
Patient Invoice Configuration for Universal Engine
File: app/config/modules/patient_invoice_config.py

Complete configuration leveraging Universal Engine v5.0 capabilities
Transaction entity - read-only operations in Universal Engine
Create/Edit/Delete handled by billing_views.py custom routes
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, EntityConfiguration, EntityCategory,
    CRUDOperation, SectionDefinition, ViewLayoutConfiguration, LayoutType,
    TabDefinition, ActionDefinition, ButtonType, ActionDisplayType,
    DocumentConfiguration, EntityFilterConfiguration, EntitySearchConfiguration,
    ComplexDisplayType, CustomRenderer, FilterOperator, DocumentType,
    PageSize, Orientation, DocumentSectionType, ExportFormat,
    DocumentFieldMapping, TableColumnConfig, DocumentSection, PrintLayoutType, FilterType,
    InvoiceSplitCategory, InvoiceSplitConfig
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# PATIENT INVOICE FIELD DEFINITIONS
# =============================================================================

PATIENT_INVOICE_FIELDS = [
    # === PRIMARY IDENTIFIERS ===
    FieldDefinition(
        name="invoice_id",
        label="Invoice ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="invoice_details",
        section="identification",
        view_order=0
    ),

    FieldDefinition(
        name="invoice_number",
        label="Invoice Number",
        field_type=FieldType.TEXT,
        required=True,
        searchable=True,
        sortable=True,
        filterable=False,  # REMOVED: Use text search instead
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        placeholder="Enter invoice number",
        tab_group="invoice_details",
        section="identification",
        view_order=1
    ),

    # === DATES ===
    FieldDefinition(
        name="invoice_date",
        label="Invoice Date",
        field_type=FieldType.DATE,
        format_pattern="%d-%b-%Y",
        required=True,
        sortable=True,
        filterable=True,
        filter_operator=FilterOperator.DATE_ON_OR_BEFORE,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="dates",
        view_order=2
    ),

    # === INVOICE CLASSIFICATION ===
    FieldDefinition(
        name="invoice_type",
        label="Invoice Type",
        field_type=FieldType.SELECT,
        options=[
            {"value": "Service", "label": "Service"},
            {"value": "Product", "label": "Product"},
            {"value": "Prescription", "label": "Prescription"},
            {"value": "Misc", "label": "Miscellaneous"}
        ],
        show_in_list=False,  # HIDDEN: Save space for patient_name
        show_in_detail=True,
        show_in_form=True,
        filterable=False,  # REMOVED: Not commonly filtered
        sortable=True,
        tab_group="invoice_details",
        section="classification",
        view_order=3
    ),

    FieldDefinition(
        name="is_gst_invoice",
        label="GST Invoice",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="classification",
        view_order=4
    ),

    # === PATIENT INFORMATION ===
    FieldDefinition(
        name="patient_id",
        label="Patient ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        required=False,
        filterable=False,  # ✅ NOT filterable - patient_name handles filtering (UUID or text)
        readonly=True,
        tab_group="invoice_details",
        section="patient_info",
        view_order=10
        # Note: patient_name autocomplete stores UUID in patient_name field
    ),

    FieldDefinition(
        name="patient_name",
        label="Patient Name",
        field_type=FieldType.TEXT,  # Not a foreign key - it's a display field from the view
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        readonly=True,
        searchable=True,
        filterable=True,
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
        },
        tab_group="invoice_details",
        section="patient_info",
        view_order=11,
        css_classes="font-semibold"
    ),

    FieldDefinition(
        name="patient_mrn",
        label="MRN",
        field_type=FieldType.TEXT,
        show_in_list=False,  # HIDDEN: Save space, use text search
        show_in_detail=True,
        show_in_form=False,
        searchable=True,  # Available in text search
        filterable=False,  # REMOVED: Use text search instead
        sortable=True,
        tab_group="invoice_details",
        section="patient_info",
        view_order=12,
        css_classes="text-sm text-gray-600"
    ),

    FieldDefinition(
        name="patient_phone",
        label="Phone",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="patient_info",
        view_order=13
    ),

    FieldDefinition(
        name="patient_mobile",
        label="Mobile",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="patient_info",
        view_order=14
    ),

    FieldDefinition(
        name="patient_email",
        label="Email",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="patient_info",
        view_order=15
    ),

    # === BRANCH AND HOSPITAL INFORMATION ===
    FieldDefinition(
        name="branch_name",
        label="Branch",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        filterable=False,  # REMOVED: Users work in one branch
        tab_group="invoice_details",
        section="branch_info",
        view_order=20
    ),

    FieldDefinition(
        name="hospital_name",
        label="Hospital",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="branch_info",
        view_order=21
    ),

    # === FINANCIAL INFORMATION ===
    FieldDefinition(
        name="total_amount",
        label="Total Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        sortable=True,
        tab_group="invoice_details",
        section="amounts",
        view_order=30
    ),

    FieldDefinition(
        name="total_discount",
        label="Discount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="amounts",
        view_order=31
    ),

    FieldDefinition(
        name="total_taxable_value",
        label="Taxable Value",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="amounts",
        view_order=32
    ),

    FieldDefinition(
        name="grand_total",
        label="Grand Total",
        field_type=FieldType.CURRENCY,
        required=True,
        sortable=True,
        filterable=True,
        filter_operator=FilterOperator.LESS_THAN_OR_EQUAL,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="amounts",
        view_order=33,
        css_classes="text-xl font-bold text-green-600"
    ),

    FieldDefinition(
        name="paid_amount",
        label="Paid Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        readonly=True,
        tab_group="invoice_details",
        section="payment_status",
        view_order=34,
        css_classes="text-blue-600 font-semibold"
    ),

    FieldDefinition(
        name="balance_due",
        label="Balance Due",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        filterable=True,
        filter_operator=FilterOperator.GREATER_THAN,
        readonly=True,
        tab_group="invoice_details",
        section="payment_status",
        view_order=35,
        css_classes="text-lg font-semibold text-red-600"
    ),

    # === GST BREAKDOWN ===
    FieldDefinition(
        name="total_cgst_amount",
        label="CGST",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="tax_details",
        view_order=40
    ),

    FieldDefinition(
        name="total_sgst_amount",
        label="SGST",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="tax_details",
        view_order=41
    ),

    FieldDefinition(
        name="total_igst_amount",
        label="IGST",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="tax_details",
        view_order=42
    ),

    FieldDefinition(
        name="total_gst_amount",
        label="Total GST",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="tax_details",
        view_order=43
    ),

    # === GST INFORMATION ===
    FieldDefinition(
        name="place_of_supply",
        label="Place of Supply",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="gst_info",
        view_order=44
    ),

    FieldDefinition(
        name="reverse_charge",
        label="Reverse Charge",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="gst_info",
        view_order=45
    ),

    FieldDefinition(
        name="e_invoice_irn",
        label="E-Invoice IRN",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="gst_info",
        view_order=46
    ),

    FieldDefinition(
        name="is_interstate",
        label="Interstate",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="gst_info",
        view_order=47
    ),

    # === CURRENCY ===
    FieldDefinition(
        name="currency_code",
        label="Currency",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value="INR",
        tab_group="invoice_details",
        section="currency_info",
        view_order=48
    ),

    FieldDefinition(
        name="exchange_rate",
        label="Exchange Rate",
        field_type=FieldType.DECIMAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value=1.0,
        tab_group="invoice_details",
        section="currency_info",
        view_order=49
    ),

    # === STATUS AND WORKFLOW ===
    FieldDefinition(
        name="payment_status",
        label="Payment Status",
        field_type=FieldType.STATUS_BADGE,
        db_column="payment_status",
        filter_aliases=["status", "payment_status"],
        filter_operator=FilterOperator.EQUALS,
        options=[
            {"value": "unpaid", "label": "Unpaid", "color": "warning"},
            {"value": "partial", "label": "Partially Paid", "color": "info"},
            {"value": "paid", "label": "Paid", "color": "success"},
            {"value": "cancelled", "label": "Cancelled", "color": "secondary"}
        ],
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        searchable=False,
        sortable=True,
        filterable=True,
        readonly=True,
        tab_group="invoice_details",
        section="payment_status",
        view_order=50,
        css_classes="payment-status-column"
    ),

    # === CANCELLATION INFORMATION ===
    FieldDefinition(
        name="is_cancelled",
        label="Cancelled",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        filterable=True,
        readonly=True,
        tab_group="invoice_details",
        section="cancellation_info",
        view_order=60
    ),

    FieldDefinition(
        name="cancellation_reason",
        label="Cancellation Reason",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="invoice_details",
        section="cancellation_info",
        view_order=61
    ),

    FieldDefinition(
        name="cancelled_at",
        label="Cancelled At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="invoice_details",
        section="cancellation_info",
        view_order=62
    ),

    # === SPLIT INVOICE TRACKING ===
    # REMOVED: Split invoice tracking fields - user requested removal of split invoices functionality
    # FieldDefinition(
    #     name="parent_transaction_id",
    #     label="Parent Invoice ID",
    #     field_type=FieldType.UUID,
    #     show_in_list=False,
    #     show_in_detail=True,
    #     show_in_form=False,
    #     readonly=True,
    #     filterable=False,
    #     tab_group="invoice_details",
    #     section="split_tracking",
    #     view_order=63
    # ),
    #
    # FieldDefinition(
    #     name="is_split_invoice",
    #     label="Consolidated Invoice",
    #     field_type=FieldType.BOOLEAN,
    #     show_in_list=False,
    #     show_in_detail=True,
    #     show_in_form=False,
    #     readonly=True,
    #     filterable=True,
    #     tab_group="invoice_details",
    #     section="split_tracking",
    #     view_order=64
    # ),
    #
    # FieldDefinition(
    #     name="split_sequence",
    #     label="Split Sequence",
    #     field_type=FieldType.INTEGER,
    #     show_in_list=False,
    #     show_in_detail=True,
    #     show_in_form=False,
    #     readonly=True,
    #     filterable=False,
    #     tab_group="invoice_details",
    #     section="split_tracking",
    #     view_order=65,
    #     conditional_display="item.is_split_invoice"
    # ),
    #
    # FieldDefinition(
    #     name="split_reason",
    #     label="Split Reason",
    #     field_type=FieldType.TEXT,
    #     show_in_list=False,
    #     show_in_detail=True,
    #     show_in_form=False,
    #     readonly=True,
    #     filterable=False,
    #     tab_group="invoice_details",
    #     section="split_tracking",
    #     view_order=66,
    #     conditional_display="item.is_split_invoice"
    # ),
    #
    # FieldDefinition(
    #     name="split_invoice_count",
    #     label="Split Invoice Count",
    #     field_type=FieldType.INTEGER,
    #     show_in_list=False,
    #     show_in_detail=True,
    #     show_in_form=False,
    #     readonly=True,
    #     filterable=True,
    #     filter_operator=FilterOperator.GREATER_THAN,
    #     tab_group="invoice_details",
    #     section="split_tracking",
    #     view_order=67,
    #     conditional_display="item.split_invoice_count > 0"
    # ),

    # === AGING ANALYSIS ===
    FieldDefinition(
        name="invoice_age_days",
        label="Age (Days)",
        field_type=FieldType.INTEGER,
        filterable=False,  # REMOVED: Use aging_bucket dropdown instead
        filter_operator=FilterOperator.LESS_THAN_OR_EQUAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        virtual=False,
        tab_group="invoice_details",
        section="aging",
        view_order=70
    ),

    FieldDefinition(
        name="aging_bucket",
        label="Aging Bucket",
        field_type=FieldType.SELECT,  # CHANGED: Dropdown for easier filtering
        options=[  # FIXED: Match actual database view values
            {"value": "Paid", "label": "Paid"},
            {"value": "0-30 days", "label": "0-30 days (Current)"},
            {"value": "31-60 days", "label": "31-60 days"},
            {"value": "61-90 days", "label": "61-90 days"},
            {"value": "90+ days", "label": "90+ days (Overdue)"},
            {"value": "Cancelled", "label": "Cancelled"}
        ],
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        filterable=True,
        sortable=True,
        tab_group="invoice_details",
        section="aging",
        view_order=71
    ),

    FieldDefinition(
        name="aging_status",
        label="Aging Status",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="aging",
        view_order=72
    ),

    # === GL ACCOUNT ===
    FieldDefinition(
        name="gl_account_id",
        label="GL Account",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="posting_info",
        section="gl_info",
        view_order=80
    ),

    # === NOTES ===
    FieldDefinition(
        name="notes",
        label="Notes",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        tab_group="invoice_details",
        section="additional_info",
        view_order=90,
        placeholder="Enter any additional notes"
    ),

    # === CUSTOM RENDERERS FOR LINE ITEMS AND PAYMENTS ===
    FieldDefinition(
        name="invoice_lines_display",
        label="Invoice Line Items",
        field_type=FieldType.CUSTOM,
        virtual=True,
        show_in_detail=True,
        show_in_list=False,
        show_in_form=False,
        readonly=True,
        tab_group="line_items",
        section="items",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="engine/business/universal_line_items_table.html",
            context_function="get_invoice_lines",
            css_classes="table-responsive w-100"  # Full width - triggers col-span in layout
        )
    ),

    FieldDefinition(
        name="payment_history_display",
        label="Payment History",
        field_type=FieldType.CUSTOM,
        virtual=True,
        show_in_detail=True,
        show_in_list=False,
        show_in_form=False,
        readonly=True,
        tab_group="payments",
        section="payment_history",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_payment_history",
            css_classes="table-responsive payment-history-table"
        )
    ),

    # NEW: Patient Payment History (Last 6 Months)
    FieldDefinition(
        name="patient_payment_history_display",
        label="Patient Payment History (Last 6 Months)",
        field_type=FieldType.CUSTOM,
        virtual=True,
        show_in_detail=True,
        show_in_list=False,
        show_in_form=False,
        readonly=True,
        tab_group="patient_history",
        section="patient_payment_history",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="components/business/patient_payment_history_table.html",
            context_function="get_patient_payment_history",
            css_classes="table-responsive patient-payment-history-table"
        )
    ),

    # === AUDIT FIELDS ===
    FieldDefinition(
        name="created_at",
        label="Created At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit",
        view_order=100
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
        section="audit",
        view_order=101
    ),

    FieldDefinition(
        name="updated_at",
        label="Updated At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit",
        view_order=102
    ),

    FieldDefinition(
        name="updated_by",
        label="Updated By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit",
        view_order=103
    ),

    # === SOFT DELETE TRACKING FIELDS ===
    FieldDefinition(
        name="is_deleted",
        label="Is Deleted",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True,
        filterable=True,
    ),

    FieldDefinition(
        name="deleted_at",
        label="Deleted At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        format_pattern="%d/%b/%Y at %H:%M",
        tab_group="system_info",
        section="audit",
        view_order=104
    ),

    FieldDefinition(
        name="deleted_by",
        label="Deleted By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit",
        view_order=105
    ),

    # === SPLIT INVOICES (CUSTOM RENDERER) ===
    # REMOVED: Split Invoices tab - user requested removal
    # FieldDefinition(
    #     name="child_invoices_display",
    #     label="Split Invoices",
    #     field_type=FieldType.CUSTOM,
    #     virtual=True,
    #     show_in_list=False,
    #     show_in_detail=True,
    #     show_in_form=False,
    #     tab_group="split_invoices",
    #     section="children",
    #     view_order=1,
    #     conditional_display="item.parent_transaction_id is None and item.split_invoice_count > 0",
    #     custom_renderer=CustomRenderer(
    #         template="engine/business/child_invoices_table.html",
    #         context_function="get_child_invoices",
    #         css_classes="w-100"
    #     )
    # ),
]

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

PATIENT_INVOICE_SECTIONS = {
    # Invoice Details Tab Sections
    "identification": SectionDefinition(
        key="identification",
        title="Invoice Identification",
        icon="fas fa-id-card",
        columns=2,
        order=1
    ),
    "dates": SectionDefinition(
        key="dates",
        title="Important Dates",
        icon="fas fa-calendar",
        columns=2,
        order=2
    ),
    "classification": SectionDefinition(
        key="classification",
        title="Invoice Classification",
        icon="fas fa-tag",
        columns=2,
        order=3
    ),
    "patient_info": SectionDefinition(
        key="patient_info",
        title="Patient Information",
        icon="fas fa-user",
        columns=2,
        order=4
    ),
    "branch_info": SectionDefinition(
        key="branch_info",
        title="Branch & Hospital",
        icon="fas fa-building",
        columns=2,
        order=5
    ),
    "amounts": SectionDefinition(
        key="amounts",
        title="Invoice Amounts",
        icon="fas fa-rupee-sign",
        columns=2,
        order=6
    ),
    "tax_details": SectionDefinition(
        key="tax_details",
        title="Tax Information",
        icon="fas fa-percent",
        columns=2,
        order=7
    ),
    "gst_info": SectionDefinition(
        key="gst_info",
        title="GST Details",
        icon="fas fa-file-invoice",
        columns=2,
        order=8
    ),
    "currency_info": SectionDefinition(
        key="currency_info",
        title="Currency",
        icon="fas fa-money-bill",
        columns=2,
        order=9
    ),
    "payment_status": SectionDefinition(
        key="payment_status",
        title="Payment Status",
        icon="fas fa-info-circle",
        columns=2,
        order=10
    ),
    "cancellation_info": SectionDefinition(
        key="cancellation_info",
        title="Cancellation Information",
        icon="fas fa-ban",
        columns=2,
        order=11
    ),
    "aging": SectionDefinition(
        key="aging",
        title="Aging Information",
        icon="fas fa-clock",
        columns=2,
        order=12
    ),

    # Line Items Tab Sections
    "items": SectionDefinition(
        key="items",
        title="Invoice Line Items",
        icon="fas fa-shopping-cart",
        columns=1,
        order=1
    ),

    # Payments Tab Sections
    "payment_history": SectionDefinition(
        key="payment_history",
        title="",
        icon="",
        columns=1,
        order=1
    ),

    # Patient Payment History Tab Section (NEW: Last 6 months for this patient)
    "patient_payment_history": SectionDefinition(
        key="patient_payment_history",
        title="",
        icon="",
        columns=1,
        order=1
    ),

    # Posting Info Tab Sections
    "gl_info": SectionDefinition(
        key="gl_info",
        title="GL Posting Information",
        icon="fas fa-check-circle",
        columns=2,
        order=1
    ),

    # System Info Tab Sections
    "audit": SectionDefinition(
        key="audit",
        title="Audit Information",
        icon="fas fa-history",
        columns=2,
        order=1
    ),

    # Additional Info Section
    "additional_info": SectionDefinition(
        key="additional_info",
        title="Additional Information",
        icon="fas fa-info",
        columns=1,
        order=13
    ),

    # REMOVED: Split Invoices Tab Section - user requested removal
    # "children": SectionDefinition(
    #     key="children",
    #     title="Tax-Compliant Split Invoices",
    #     icon="fas fa-layer-group",
    #     columns=1,
    #     order=1
    # )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION (TABBED)
# =============================================================================

PATIENT_INVOICE_TABS = {
    "invoice_details": TabDefinition(
        key="invoice_details",
        label="Invoice Details",
        icon="fas fa-file-invoice-dollar",
        sections={
            "identification": PATIENT_INVOICE_SECTIONS["identification"],
            "patient_info": PATIENT_INVOICE_SECTIONS["patient_info"],
            "dates": PATIENT_INVOICE_SECTIONS["dates"],
            "classification": PATIENT_INVOICE_SECTIONS["classification"],
            "branch_info": PATIENT_INVOICE_SECTIONS["branch_info"],
            "payment_status": PATIENT_INVOICE_SECTIONS["payment_status"],
            "amounts": PATIENT_INVOICE_SECTIONS["amounts"],
            "tax_details": PATIENT_INVOICE_SECTIONS["tax_details"],
            "gst_info": PATIENT_INVOICE_SECTIONS["gst_info"],
            "currency_info": PATIENT_INVOICE_SECTIONS["currency_info"],
            "cancellation_info": PATIENT_INVOICE_SECTIONS["cancellation_info"],
            "aging": PATIENT_INVOICE_SECTIONS["aging"],
            "additional_info": PATIENT_INVOICE_SECTIONS["additional_info"]
        },
        order=0,
        default_active=True
    ),
    "line_items": TabDefinition(
        key="line_items",
        label="Line Items",
        icon="fas fa-list",
        sections={
            "items": PATIENT_INVOICE_SECTIONS["items"]
        },
        order=1
    ),
    "payments": TabDefinition(
        key="payments",
        label="Payments",
        icon="fas fa-money-bill-wave",
        sections={
            "payment_history": PATIENT_INVOICE_SECTIONS["payment_history"]
        },
        order=2
    ),
    # NEW: Patient Payment History tab (Last 6 months for this patient)
    "patient_history": TabDefinition(
        key="patient_history",
        label="Patient Payment History",
        icon="fas fa-history",
        sections={
            "patient_payment_history": PATIENT_INVOICE_SECTIONS["patient_payment_history"]
        },
        order=3
    ),
    # REMOVED: Split Invoices tab - user requested removal
    # Split invoice information is accessible via "Back to Parent Invoice" button instead
    "posting_info": TabDefinition(
        key="posting_info",
        label="GL Posting",
        icon="fas fa-check-circle",
        sections={
            "gl_info": PATIENT_INVOICE_SECTIONS["gl_info"]
        },
        order=4
    ),
    "system_info": TabDefinition(
        key="system_info",
        label="System Info",
        icon="fas fa-cog",
        sections={
            "audit": PATIENT_INVOICE_SECTIONS["audit"]
        },
        order=5
    )
}

PATIENT_INVOICE_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    tabs=PATIENT_INVOICE_TABS,
    sections=PATIENT_INVOICE_SECTIONS,
    default_tab="invoice_details",
    sticky_tabs=True,
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "invoice_number",
        "primary_label": "Invoice Number",
        "title_field": "patient_name",
        "title_label": "Patient",
        "status_field": "payment_status",
        "secondary_fields": [
            {"field": "invoice_date", "label": "Invoice Date", "icon": "fas fa-calendar", "type": "date", "format": "%d-%b-%Y"},
            {"field": "grand_total", "label": "Grand Total", "icon": "fas fa-rupee-sign", "type": "currency", "css_classes": "text-xl font-bold text-primary"},
            {"field": "patient_mrn", "label": "MRN", "icon": "fas fa-id-card", "type": "text"},
            {"field": "balance_due", "label": "Balance", "icon": "fas fa-money-bill", "type": "currency", "css_classes": "text-lg font-semibold text-danger"}
        ]
    }
)

# =============================================================================
# ACTIONS CONFIGURATION
# =============================================================================

PATIENT_INVOICE_ACTIONS = [

    # =============================================================================
    # LIST PAGE - TOOLBAR ACTIONS (Navigation to other lists, create)
    # =============================================================================

    ActionDefinition(
        id="goto_patients_list",
        label="Patients",
        icon="fas fa-users",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "patients"},
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="patients_view",
        order=1
    ),

    ActionDefinition(
        id="goto_patient_payments_list",
        label="Patient Payments",
        icon="fas fa-money-bill",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "patient_payments"},
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_payment_view",
        order=2
    ),

    ActionDefinition(
        id="goto_package_plans_list",
        label="Package Plans",
        icon="fas fa-calendar-alt",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "package_payment_plans"},
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=3
    ),

    ActionDefinition(
        id="goto_consolidated_invoices_list",
        label="Consolidated Invoices",
        icon="fas fa-layer-group",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "consolidated_patient_invoices"},
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=4
    ),

    ActionDefinition(
        id="create_invoice",
        label="Create Invoice",
        icon="fas fa-plus",
        button_type=ButtonType.PRIMARY,
        route_name="billing_views.create_invoice",
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_create",
        order=5
    ),

    # =============================================================================
    # LIST PAGE - ROW ACTIONS (Per-record actions in table)
    # =============================================================================

    ActionDefinition(
        id="view_row",
        label="View",
        icon="fas fa-eye",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_detail_view",
        route_params={"entity_type": "patient_invoices", "item_id": "{invoice_id}"},
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=1
    ),

    ActionDefinition(
        id="print_row",
        label="Print",
        icon="fas fa-print",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_document_view",
        route_params={"entity_type": "patient_invoices", "item_id": "{invoice_id}", "doc_type": "invoice"},
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_print",
        order=2
    ),

    ActionDefinition(
        id="delete_row",
        label="Delete",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        url_pattern="/billing/invoice/delete/{invoice_id}",
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        conditions={
            "payment_status": ["unpaid"],
            "is_cancelled": [False, None]
        },
        permission="billing_invoice_delete",
        order=3,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this invoice?"
    ),

    # =============================================================================
    # DETAIL/VIEW PAGE - TOOLBAR ACTIONS (Navigation buttons)
    # =============================================================================

    ActionDefinition(
        id="goto_invoices_list",
        label="Patient Invoices",
        icon="fas fa-file-invoice",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "patient_invoices"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=1
    ),

    ActionDefinition(
        id="goto_patients_detail",
        label="Patients",
        icon="fas fa-users",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "patients"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="patients_view",
        order=2
    ),

    ActionDefinition(
        id="goto_payments_detail",
        label="Patient Payments",
        icon="fas fa-money-bill",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "patient_payments"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_payment_view",
        order=3
    ),

    ActionDefinition(
        id="goto_package_plans_detail",
        label="Package Plans",
        icon="fas fa-calendar-alt",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "package_payment_plans"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=4
    ),

    ActionDefinition(
        id="goto_consolidated_detail",
        label="Consolidated Invoices",
        icon="fas fa-layer-group",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "consolidated_patient_invoices"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
        order=5
    ),

    ActionDefinition(
        id="print_invoice",
        label="Print Invoice",
        icon="fas fa-print",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_document_view",
        route_params={"entity_type": "patient_invoices", "item_id": "{invoice_id}", "doc_type": "invoice"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_print",
        order=6
    ),

    # =============================================================================
    # DETAIL/VIEW PAGE - DROPDOWN ACTIONS (Edit, Delete, Void, Split)
    # =============================================================================

    ActionDefinition(
        id="edit_invoice",
        label="Edit Invoice",
        icon="fas fa-edit",
        button_type=ButtonType.WARNING,
        route_name="billing_views.edit_invoice",
        route_params={"invoice_id": "{invoice_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "payment_status": ["unpaid", "partial"],
            "is_cancelled": [False, None]
        },
        permission="billing_invoice_edit",
        order=1
    ),

    ActionDefinition(
        id="delete_invoice",
        label="Delete Invoice",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        url_pattern="/billing/invoice/delete/{invoice_id}",
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "payment_status": ["unpaid"],
            "is_cancelled": [False, None]
        },
        permission="billing_invoice_delete",
        order=2,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this invoice?"
    ),

    ActionDefinition(
        id="void_invoice",
        label="Void Invoice",
        icon="fas fa-ban",
        button_type=ButtonType.DANGER,
        url_pattern="/billing/invoice/cancel/{invoice_id}",
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "payment_status": ["unpaid"],
            "is_cancelled": [False, None]
        },
        permission="billing_invoice_cancel",
        order=3,
        confirmation_required=True,
        confirmation_message="Are you sure you want to void this invoice? This action cannot be undone."
    ),

    # REMOVED: Split Invoice action - user requested removal
    # ActionDefinition(
    #     id="split_invoice",
    #     label="Split Invoice",
    #     icon="fas fa-cut",
    #     button_type=ButtonType.WARNING,
    #     url_pattern="/billing/invoice/split/{invoice_id}",
    #     show_in_list=False,
    #     show_in_list_toolbar=False,
    #     show_in_detail_toolbar=True,
    #     display_type=ActionDisplayType.DROPDOWN_ITEM,
    #     conditions={
    #         "payment_status": ["unpaid"],
    #         "is_cancelled": [False, None]
    #     },
    #     permission="billing_invoice_edit",
    #     order=4
    # ),
]

# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

PATIENT_INVOICE_SUMMARY_CARDS = [
    {
        "id": "total_count",
        "field": "total_count",
        "label": "Total Invoices",
        "icon": "fas fa-file-invoice",
        "icon_css": "stat-card-icon primary",
        "type": "number",
        "visible": True,
        "order": 1
    },

    {
        "id": "total_amount",
        "field": "grand_total",
        "label": "Total Amount",
        "icon": "fas fa-rupee-sign",
        "icon_css": "stat-card-icon success",
        "type": "currency",
        "visible": True,
        "order": 2
    },

    # Hidden card for outstanding calculation
    {
        "id": "outstanding_calc",
        "field": "balance_due",
        "type": "currency",
        "visible": False,
        "filter_condition": {
            "payment_status": ["unpaid", "partial"]
        }
    },

    {
        "id": "outstanding_amount",
        "field": "outstanding_calc",
        "label": "Outstanding",
        "icon": "fas fa-clock",
        "icon_css": "stat-card-icon warning",
        "type": "currency",
        "visible": True,
        "order": 3
    },

    # Hidden card for paid calculation
    {
        "id": "paid_calc",
        "field": "grand_total",
        "type": "currency",
        "visible": False,
        "filter_condition": {
            "payment_status": "paid"
        }
    },

    {
        "id": "paid_amount_total",
        "field": "paid_calc",
        "label": "Collected",
        "icon": "fas fa-check-circle",
        "icon_css": "stat-card-icon success",
        "type": "currency",
        "visible": True,
        "order": 4
    }
]

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

PATIENT_INVOICE_FILTER_CATEGORY_MAPPING = {
    # Search filters
    'search': FilterCategory.SEARCH,
    'patient_name': FilterCategory.SEARCH,
    'patient_mrn': FilterCategory.SEARCH,
    'invoice_number': FilterCategory.SEARCH,
    'notes': FilterCategory.SEARCH,

    # Selection filters
    'payment_status': FilterCategory.SELECTION,
    'status': FilterCategory.SELECTION,
    'invoice_type': FilterCategory.SELECTION,
    'aging_bucket': FilterCategory.SELECTION,
    'is_cancelled': FilterCategory.SELECTION,

    # Date filters
    'invoice_date': FilterCategory.DATE,

    # Amount filters
    'grand_total': FilterCategory.AMOUNT,
    'balance_due': FilterCategory.AMOUNT,
    'invoice_age_days': FilterCategory.AMOUNT,

    # Relationship filters
    'patient_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP
}

PATIENT_INVOICE_DEFAULT_FILTERS = {
    'payment_status': '',  # Default to "All"
    'is_cancelled': False  # Hide cancelled by default
}

PATIENT_INVOICE_CATEGORY_CONFIGS = {
    FilterCategory.DATE: {
        'default_preset': 'last_3_months',
        'auto_apply_financial_year': False
    },
    FilterCategory.AMOUNT: {
        'currency_symbol': '₹',
        'decimal_places': 2
    },
    FilterCategory.SEARCH: {
        'min_search_length': 2,
        'auto_submit': False,
        'search_fields': ['patient_name', 'patient_mrn', 'invoice_number']
    },
    FilterCategory.SELECTION: {
        'auto_submit': True,
        'include_empty_options': True
    },
    FilterCategory.RELATIONSHIP: {
        'lazy_load': True,
        'cache_duration': 300
    }
}

# =============================================================================
# DOCUMENT CONFIGURATION
# =============================================================================

PATIENT_INVOICE_DOCUMENT_CONFIGS = {
    "invoice": DocumentConfiguration(
        enabled=True,
        document_type="invoice",
        title="Patient Invoice",
        subtitle="Tax Invoice",
        page_size="A4",
        orientation="portrait",
        margins={"top": 20, "bottom": 20, "left": 15, "right": 15},
        print_layout_type="simple_with_header",
        show_logo=True,
        show_company_info=True,
        show_footer=True,
        visible_tabs=["invoice_details", "line_items"],
        header_text="PATIENT INVOICE",
        footer_text="This is a system generated document",
        show_print_info=True,
        signature_fields=[
            {"label": "Received By", "width": "200px"},
            {"label": "Verified By", "width": "200px"}
        ],
        allowed_formats=["pdf", "print", "excel"],
        default_format="pdf"
    ),
    "statement": DocumentConfiguration(
        enabled=True,
        document_type="report",
        title="Invoice Statement",
        subtitle="Patient Invoice List",
        page_size="A4",
        orientation="landscape",
        margins={"top": 20, "bottom": 20, "left": 15, "right": 15},
        print_layout_type="simple",
        show_logo=False,
        show_company_info=False,
        show_footer=True,
        header_text="INVOICE STATEMENT",
        footer_text="Statement generated on {current_date}",
        allowed_formats=["pdf", "excel", "csv"],
        default_format="excel"
    )
}

# =============================================================================
# PERMISSIONS CONFIGURATION
# =============================================================================

PATIENT_INVOICE_PERMISSIONS = {
    "list": "billing_invoice_list",
    "view": "billing_invoice_view",
    "edit": "billing_invoice_edit",
    "cancel": "billing_invoice_cancel",
    "export": "billing_invoice_export",
    "print": "billing_invoice_print",
    "document": "billing_invoice_document"
}

# =============================================================================
# ENTITY FILTER CONFIGURATION
# =============================================================================

PATIENT_INVOICE_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='patient_invoices',
    filter_mappings={
        'payment_status': {
            'field': 'payment_status',
            'type': 'select',
            'label': 'Payment Status',
            'options': [
                {'value': '', 'label': 'All'},
                {'value': 'unpaid', 'label': 'Unpaid'},
                {'value': 'partial', 'label': 'Partially Paid'},
                {'value': 'paid', 'label': 'Paid'},
                {'value': 'cancelled', 'label': 'Cancelled'}
            ]
        },

        'patient_name': {
            'field': 'patient_name',
            'type': 'text',
            'label': 'Patient Name',
            'placeholder': 'Search patient name...',
            'search_in_view': True
        },

        'invoice_type': {
            'field': 'invoice_type',
            'type': 'select',
            'label': 'Invoice Type',
            'options': [
                {'value': '', 'label': 'All'},
                {'value': 'Service', 'label': 'Service'},
                {'value': 'Product', 'label': 'Product'},
                {'value': 'Prescription', 'label': 'Prescription'},
                {'value': 'Misc', 'label': 'Miscellaneous'}
            ]
        },

        'aging_bucket': {
            'field': 'aging_bucket',
            'type': 'select',
            'label': 'Aging',
            'options': [
                {'value': '', 'label': 'All'},
                {'value': '0-30 days', 'label': '0-30 Days'},
                {'value': '31-60 days', 'label': '31-60 Days'},
                {'value': '61-90 days', 'label': '61-90 Days'},
                {'value': '90+ days', 'label': 'Over 90 Days'}
            ]
        },

        'patient_id': {
            'field': 'patient_id',
            'type': 'entity_search',
            'entity_type': 'patients',
            'display_field': 'patient_name',
            'search_fields': ['full_name', 'first_name', 'last_name', 'mrn'],
            'placeholder': 'Search patients...',
            'label': 'Patient'
        }
    }
)

# =============================================================================
# ENTITY SEARCH CONFIGURATION
# =============================================================================

PATIENT_INVOICE_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='patient_invoices',
    search_fields=['invoice_number', 'patient_name', 'patient_mrn'],
    display_template='{invoice_number} - {patient_name} (MRN: {patient_mrn})',
    min_chars=1,
    max_results=10,
    sort_field='invoice_date'
)

# =============================================================================
# MAIN CONFIGURATION
# =============================================================================

PATIENT_INVOICE_CONFIG = EntityConfiguration(
    # === BASIC INFORMATION ===
    entity_type="patient_invoices",
    name="Patient Invoice",
    plural_name="Patient Invoices",
    service_name="patient_invoices",
    icon="fas fa-file-invoice-dollar",

    # === DATABASE CONFIGURATION ===
    table_name="patient_invoices_view",
    primary_key="invoice_id",

    # === DISPLAY CONFIGURATION ===
    title_field="invoice_number",
    subtitle_field="patient_name",
    page_title="Patient Invoices",
    description="Manage patient invoices and track payments",

    # === SEARCH AND SORT ===
    searchable_fields=["invoice_number", "patient_name", "patient_mrn", "notes"],
    default_sort_field="invoice_date",
    default_sort_direction="desc",

    # === CORE CONFIGURATIONS ===
    fields=PATIENT_INVOICE_FIELDS,
    view_layout=PATIENT_INVOICE_VIEW_LAYOUT,
    section_definitions=PATIENT_INVOICE_SECTIONS,
    actions=PATIENT_INVOICE_ACTIONS,
    summary_cards=PATIENT_INVOICE_SUMMARY_CARDS,
    permissions=PATIENT_INVOICE_PERMISSIONS,

    # === FILTER CONFIGURATION ===
    filter_category_mapping=PATIENT_INVOICE_FILTER_CATEGORY_MAPPING,
    default_filters=PATIENT_INVOICE_DEFAULT_FILTERS,
    category_configs=PATIENT_INVOICE_CATEGORY_CONFIGS,

    # === DATE AND AMOUNT CONFIGURATION ===
    primary_date_field="invoice_date",
    primary_amount_field="grand_total",

    # === DOCUMENT GENERATION ===
    document_enabled=True,
    document_configs=PATIENT_INVOICE_DOCUMENT_CONFIGS,
    default_document="invoice",

    # === UNIVERSAL CRUD SETTINGS ===
    universal_crud_enabled=False,  # Transaction entity - read-only in Universal Engine
    allowed_operations=[
        CRUDOperation.READ,
        CRUDOperation.LIST,
        CRUDOperation.EXPORT,
        CRUDOperation.DOCUMENT
    ],

    # === CALCULATED FIELDS ===
    include_calculated_fields=[
        "patient_name",
        "patient_mrn",
        "patient_phone",
        "patient_mobile",
        "patient_email",
        "branch_name",
        "hospital_name",
        "total_gst_amount",
        "invoice_age_days",
        "aging_bucket",
        "aging_status",
        "payment_status"
    ],

    # === FEATURE FLAGS ===
    enable_audit_trail=True,
    enable_soft_delete=False,  # InvoiceHeader doesn't have SoftDeleteMixin yet
    enable_bulk_operations=False,
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,

    # === ENTITY CATEGORY ===
    entity_category=EntityCategory.TRANSACTION,

    # === DOCUMENT PERMISSIONS ===
    document_permissions={
        "invoice": "billing_invoice_view",
        "statement": "billing_invoice_list"
    }
)

# =============================================================================
# INVOICE SPLIT CONFIGURATION - Phase 3
# =============================================================================

# Configure the 4-way invoice split for tax compliance
INVOICE_SPLIT_CONFIGS = [
    InvoiceSplitConfig(
        category=InvoiceSplitCategory.SERVICE_PACKAGE,
        prefix="SVC",
        name="Service & Package Invoice",
        description="Services and packages only",
        starting_number=1,
        item_types=["Service", "Package"],
        requires_gst=None  # Both GST and non-GST allowed
    ),
    InvoiceSplitConfig(
        category=InvoiceSplitCategory.GST_MEDICINES,
        prefix="MED",
        name="GST Medicines/Products Invoice",
        description="OTC, Products, Consumables with GST",
        starting_number=1,
        item_types=["OTC", "Product", "Consumable", "Medicine"],
        requires_gst=True  # GST applicable only
    ),
    InvoiceSplitConfig(
        category=InvoiceSplitCategory.GST_EXEMPT_MEDICINES,
        prefix="EXM",
        name="GST Exempt Medicines Invoice",
        description="Medicines/products with GST exemption",
        starting_number=1,
        item_types=["OTC", "Product", "Consumable", "Medicine"],
        requires_gst=False  # GST exempt only
    ),
    InvoiceSplitConfig(
        category=InvoiceSplitCategory.PRESCRIPTION_COMPOSITE,
        prefix="RX",
        name="Prescription/Composite Invoice",
        description="Prescription medicines + consultation",
        starting_number=1,
        item_types=["Prescription"],
        requires_gst=None  # Can be either based on consolidation
    )
]

def get_invoice_split_config(category: InvoiceSplitCategory) -> Optional[InvoiceSplitConfig]:
    """
    Get invoice split configuration for a specific category

    Args:
        category: InvoiceSplitCategory enum value

    Returns:
        InvoiceSplitConfig if found, None otherwise
    """
    for config in INVOICE_SPLIT_CONFIGS:
        if config.category == category:
            return config
    return None

def categorize_line_item(item_type: str, is_gst_exempt: bool, is_prescription: bool = False) -> Optional[InvoiceSplitCategory]:
    """
    Determine which invoice category a line item belongs to

    Args:
        item_type: Type of line item (Service, Package, OTC, etc.)
        is_gst_exempt: Whether item is GST exempt
        is_prescription: Whether item is prescription type

    Returns:
        InvoiceSplitCategory enum value or None
    """
    # Prescription items always go to prescription/composite category
    if is_prescription or item_type == "Prescription":
        return InvoiceSplitCategory.PRESCRIPTION_COMPOSITE

    # Service and Package items
    if item_type in ["Service", "Package"]:
        return InvoiceSplitCategory.SERVICE_PACKAGE

    # Medicine/Product/OTC items - check GST status
    if item_type in ["OTC", "Product", "Consumable", "Medicine"]:
        if is_gst_exempt:
            return InvoiceSplitCategory.GST_EXEMPT_MEDICINES
        else:
            return InvoiceSplitCategory.GST_MEDICINES

    return None

# =============================================================================
# MODULE EXPORTS
# =============================================================================

def get_module_configs():
    """Return all configurations from this module"""
    return {
        "patient_invoices": PATIENT_INVOICE_CONFIG
    }

def get_module_filter_configs():
    """Return filter configurations"""
    return {
        "patient_invoices": PATIENT_INVOICE_FILTER_CATEGORY_MAPPING
    }

# Direct exports for simplified access
config = PATIENT_INVOICE_CONFIG
filter_config = PATIENT_INVOICE_ENTITY_FILTER_CONFIG
search_config = PATIENT_INVOICE_SEARCH_CONFIG
