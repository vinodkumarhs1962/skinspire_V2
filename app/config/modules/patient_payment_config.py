# Complete Patient Payment Configuration Module
# File: app/config/modules/patient_payment_config.py

"""
Patient Payment Configuration Module
Contains ALL configuration for patient payment receipts
Single source of truth - no duplication
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from sqlalchemy import false
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition,
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition, CustomRenderer,
    EntitySearchConfiguration, FilterConfiguration,
    EntityFilterConfiguration, ButtonType, ActionDisplayType, ComplexDisplayType, DocumentType,
    PageSize, Orientation, DocumentSectionType, ExportFormat, DocumentFieldMapping, TableColumnConfig,
    DocumentSection, DocumentConfiguration, PrintLayoutType, FilterOperator, FilterType
)

from app.config.filter_categories import FilterCategory

# =============================================================================
# PATIENT PAYMENT FIELD DEFINITIONS
# =============================================================================

PATIENT_PAYMENT_FIELDS = [
    # ==========================================================================
    # SYSTEM FIELDS
    # ==========================================================================

    FieldDefinition(
        name="payment_id",
        label="Payment ID",
        field_type=FieldType.UUID,
        show_in_list=True,  # ✅ Show in list for multi-invoice payments
        show_in_detail=True,  # ✅ Show in detail view
        show_in_form=False,
        searchable=True,  # ✅ Make searchable
        sortable=True,  # ✅ Make sortable
        readonly=True,
        tab_group="payment_details",
        section="header",
        view_order=0,
        width="150px"  # ✅ Set column width
    ),

    FieldDefinition(
        name="hospital_id",
        label="Hospital",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=True,
        tab_group="system_info",
        section="technical_info",
        view_order=0
    ),

    FieldDefinition(
        name="hospital_name",
        label="Hospital Name",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="technical_info",
        view_order=1
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
        tab_group="system_info",
        section="technical_info",
        view_order=2
    ),

    FieldDefinition(
        name="branch_name",
        label="Branch Name",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="technical_info",
        view_order=3
    ),

    # ==========================================================================
    # TRACEABILITY FIELDS (Added: 2025-11-15)
    # ==========================================================================

    FieldDefinition(
        name="payment_number",
        label="Payment Number",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        searchable=True,
        sortable=True,
        readonly=True,
        tab_group="payment_details",
        section="header",
        view_order=0,
        width="150px"
    ),

    FieldDefinition(
        name="recorded_by",
        label="Recorded By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_info",
        view_order=5
    ),

    FieldDefinition(
        name="payment_source",
        label="Payment Source",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        filterable=True,
        filter_type=FilterType.SELECT,
        options=[
            {"value": "", "label": "All Sources"},
            {"value": "single_invoice", "label": "Single Invoice"},
            {"value": "multi_invoice", "label": "Multiple Invoices"},
            {"value": "package_installment", "label": "Package Installment"},
            {"value": "advance", "label": "Advance Payment"}
        ],
        readonly=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=8
    ),

    FieldDefinition(
        name="invoice_count",
        label="Invoice Count",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=9
    ),

    # NOTE: advance_adjustment_amount moved to payment_methods section

    FieldDefinition(
        name="last_modified_by",
        label="Last Modified By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_info",
        view_order=6
    ),

    FieldDefinition(
        name="last_modified_at",
        label="Last Modified At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_info",
        view_order=7
    ),

    FieldDefinition(
        name="bank_reconciled",
        label="Bank Reconciled",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reconciliation_info",
        view_order=3
    ),

    FieldDefinition(
        name="bank_reconciled_date",
        label="Bank Reconciliation Date",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reconciliation_info",
        view_order=4
    ),

    FieldDefinition(
        name="bank_reconciled_by",
        label="Bank Reconciled By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reconciliation_info",
        view_order=5
    ),

    # ==========================================================================
    # CORE PAYMENT FIELDS
    # ==========================================================================

    FieldDefinition(
        name="invoice_number",
        label="Invoice Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,  # ✅ Don't show in body - will be in header_config
        show_in_form=True,
        searchable=True,
        sortable=True,
        required=False,  # ✅ May be NULL for multi-invoice payments
        placeholder="Invoice reference (NULL for multi-invoice)",
        tab_group="payment_details",
        section="header",
        view_order=1,
        css_classes="text-wrap",  # ✅ Allow wrapping for NULL display
        width="150px"
    ),

    FieldDefinition(
        name="payment_date",
        label="Date",  # ✅ Shorter label
        field_type=FieldType.DATE,  # ✅ Changed to DATE (not DATETIME) for dd/mmm format
        format_pattern="%d/%b",  # ✅ dd/mmm format only
        show_in_list=True,
        show_in_detail=False,  # ✅ Don't show in body - will be in header_config
        show_in_form=True,
        searchable=False,
        sortable=True,
        filterable=True,
        filter_aliases=["start_date", "end_date", "date_from", "date_to"],
        filter_type="date_range",
        required=True,
        tab_group="payment_details",
        section="header",
        view_order=2,
        width="150px"  # ✅ Increased width for dd/mmm (was 80px)
    ),

    # ==========================================================================
    # PATIENT INFORMATION FIELDS
    # ==========================================================================

    FieldDefinition(
        name="patient_id",
        label="Patient ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True,
        tab_group="patient_info",
        section="patient_details",
        view_order=0
    ),

    FieldDefinition(
        name="patient_name",
        label="Patient Name",
        field_type=FieldType.TEXT,

        # === DISPLAY PROPERTIES ===
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        readonly=True,

        # === SEARCH PROPERTIES ===
        searchable=True,

        # === FILTER PROPERTIES ===
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,
        filter_operator=FilterOperator.EQUALS,

        # === ENTITY SEARCH CONFIGURATION ===
        entity_search_config=EntitySearchConfiguration(
            target_entity='patients',
            search_fields=['full_name', 'mrn'],
            display_template='{patient_name}',
            value_field='patient_name',      # Use name as value
            filter_field='patient_name',     # Filter by name field
            placeholder="Type to search patients...",
            preload_common=True,
            cache_results=True,
            min_chars=1,
            max_results=20
        ),

        # === LAYOUT PROPERTIES ===
        tab_group="patient_info",
        section="patient_details",
        view_order=1,
        css_classes="text-wrap align-top",  # Enable text wrapping
        width="180px"
        # NOTE: Removed complex_display_type - patient_name comes from SQL view TRIM(CONCAT_WS(' ', title, first_name, last_name))
    ),

    FieldDefinition(
        name="patient_mrn",
        label="MRN",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        searchable=True,
        sortable=True,
        readonly=True,
        tab_group="patient_info",
        section="patient_details",
        view_order=2,
        width="100px"
    ),

    FieldDefinition(
        name="patient_phone",
        label="Phone",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        searchable=True,
        readonly=True,
        tab_group="patient_info",
        section="patient_details",
        view_order=3
    ),

    FieldDefinition(
        name="patient_email",
        label="Email",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="patient_info",
        section="patient_details",
        view_order=4
    ),

    FieldDefinition(
        name="patient_status",
        label="Patient Status",
        field_type=FieldType.STATUS_BADGE,  # ✅ Use STATUS_BADGE for badge display
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="patient_info",
        section="patient_details",
        view_order=5,
        # ✅ Map boolean values to badge labels
        options=[
            {"value": "true", "label": "Active", "color": "success"},
            {"value": "false", "label": "Inactive", "color": "secondary"},
            {"value": True, "label": "Active", "color": "success"},  # Handle boolean type
            {"value": False, "label": "Inactive", "color": "secondary"}  # Handle boolean type
        ]
    ),

    # ==========================================================================
    # INVOICE REFERENCE FIELDS
    # ==========================================================================

    # Invoice summary fields - hidden (section removed as redundant)
    FieldDefinition(
        name="invoice_id",
        label="Invoice ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True
    ),

    FieldDefinition(
        name="invoice_date",
        label="Invoice Date",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y",
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True
    ),

    FieldDefinition(
        name="invoice_type",
        label="Invoice Type",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True
    ),

    FieldDefinition(
        name="invoice_total",
        label="Invoice Total",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True
    ),

    FieldDefinition(
        name="invoice_paid_amount",
        label="Total Paid",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True
    ),

    FieldDefinition(
        name="invoice_balance_due",
        label="Balance Due",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True
    ),

    FieldDefinition(
        name="invoice_payment_status",
        label="Payment Status",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True
    ),

    # ==========================================================================
    # PAYMENT AMOUNT FIELDS
    # ==========================================================================

    FieldDefinition(
        name="total_amount",
        label="💵 Cash/Card/UPI",
        field_type=FieldType.CURRENCY,
        db_column="total_amount",
        filter_operator=FilterOperator.BETWEEN,
        show_in_list=False,  # ✅ Hide from list - use payment_method_total instead
        show_in_detail=False,  # ✅ Hide from detail - shown in payment_methods section breakdown
        show_in_form=True,
        searchable=False,
        sortable=True,
        filterable=False,
        required=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=10,  # Show after payment_method_total
        format_pattern="mixed_payment_breakdown",
        css_classes="text-muted",
        width="150px"
    ),

    # === AMOUNT RANGE FILTERS (Virtual Fields) ===
    FieldDefinition(
        name="amount_min",
        label="Min Amount",
        field_type=FieldType.NUMBER,
        virtual=True,  # Not a database field
        filterable=True,  # Show in filters
        filter_type=FilterType.TEXT,  # Use text input
        filter_operator=FilterOperator.GREATER_THAN_OR_EQUAL,
        placeholder="Minimum amount...",
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False
    ),

    FieldDefinition(
        name="amount_max",
        label="Max Amount",
        field_type=FieldType.NUMBER,
        virtual=True,  # Not a database field
        filterable=True,  # Show in filters
        filter_type=FilterType.TEXT,  # Use text input
        filter_operator=FilterOperator.LESS_THAN_OR_EQUAL,
        placeholder="Maximum amount...",
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False
    ),

    FieldDefinition(
        name="refunded_amount",
        label="Refunded Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="refund_info",
        view_order=1
    ),

    FieldDefinition(
        name="net_amount",
        label="Net Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,  # ✅ Hide from list - only show total_amount (like supplier payments)
        show_in_detail=True,  # ✅ Show in detail view only
        show_in_form=False,
        sortable=True,
        readonly=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=6,
        width="150px"
    ),

    # ==========================================================================
    # PAYMENT METHOD BREAKDOWN FIELDS
    # ==========================================================================

    FieldDefinition(
        name="cash_amount",
        label="💵 Cash",  # Icon in label
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="payment_details",
        section="payment_methods",
        view_order=1
    ),

    FieldDefinition(
        name="credit_card_amount",
        label="💳 Credit Card",  # Icon in label
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="payment_details",
        section="payment_methods",
        view_order=2
    ),

    FieldDefinition(
        name="debit_card_amount",
        label="💳 Debit Card",  # Icon in label
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="payment_details",
        section="payment_methods",
        view_order=3
    ),

    FieldDefinition(
        name="upi_amount",
        label="📱 UPI",  # Icon in label
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="payment_details",
        section="payment_methods",
        view_order=4
    ),

    FieldDefinition(
        name="wallet_points_amount",
        label="🎁 Wallet Points",  # Icon in label
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=False,
        tab_group="payment_details",
        section="payment_methods",
        view_order=5
    ),

    FieldDefinition(
        name="advance_adjustment_amount",
        label="⏩ Advance Adjustment",  # Icon in label
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=False,
        tab_group="payment_details",
        section="payment_methods",
        view_order=6
    ),

    FieldDefinition(
        name="payment_method_total",
        label="💰 Total Payment",
        field_type=FieldType.CURRENCY,
        show_in_list=True,  # ✅ Show in list - includes cash/card/upi + wallet + advance
        show_in_detail=True,
        show_in_form=False,
        required=False,
        sortable=True,
        tab_group="payment_details",
        section="payment_summary",  # ✅ Show in payment summary (primary total)
        view_order=1,  # Show first
        css_classes="text-2xl font-bold text-success",
        width="150px"
    ),

    # Total in payment_methods section - uses a virtual field to read from payment_method_total
    FieldDefinition(
        name="payment_total_display",
        label="💰 Total",
        field_type=FieldType.CURRENCY,
        virtual=True,  # Virtual field - value comes from payment_method_total
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=False,
        tab_group="payment_details",
        section="payment_methods",
        view_order=99,  # Show at the end of breakdown
        css_classes="font-bold text-primary border-t pt-2"
    ),

    # ==========================================================================
    # PAYMENT METHOD DETAILS
    # ==========================================================================

    FieldDefinition(
        name="card_number_last4",
        label="Card Last 4 Digits",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="payment_details",
        section="payment_method_details",
        view_order=1
    ),

    FieldDefinition(
        name="card_type",
        label="Card Type",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="payment_details",
        section="payment_method_details",
        view_order=2
    ),

    FieldDefinition(
        name="upi_id",
        label="UPI ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        required=False,
        tab_group="payment_details",
        section="payment_method_details",
        view_order=3
    ),

    FieldDefinition(
        name="reference_number",
        label="Reference Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        required=False,
        tab_group="payment_details",
        section="payment_summary",
        view_order=6
    ),

    # ==========================================================================
    # WALLET POINTS DETAILS (shown when wallet_points_amount > 0)
    # ==========================================================================

    FieldDefinition(
        name="wallet_transaction_id",
        label="🔗 Wallet Transaction ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=False,
        tab_group="payment_details",
        section="wallet_points_details",
        view_order=1
    ),

    FieldDefinition(
        name="wallet_points_detail_amount",
        label="🎁 Points Redeemed (₹1 = 1 point)",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=False,
        tab_group="payment_details",
        section="wallet_points_details",
        view_order=2
    ),

    # ==========================================================================
    # ADVANCE ADJUSTMENT DETAILS (shown when advance_adjustment_amount > 0)
    # ==========================================================================

    FieldDefinition(
        name="advance_adjustment_id",
        label="🔗 Advance Adjustment ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=False,
        tab_group="payment_details",
        section="advance_details",
        view_order=1
    ),

    FieldDefinition(
        name="advance_amount_applied",
        label="⏩ Advance Applied",
        field_type=FieldType.CURRENCY,
        db_column="advance_adjustment_amount",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        required=False,
        tab_group="payment_details",
        section="advance_details",
        view_order=2
    ),

    # ✅ Separate field for displaying invoice numbers in multi-invoice payments
    FieldDefinition(
        name="invoice_numbers_display",
        label="Invoice Numbers",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=7,
        custom_renderer=CustomRenderer(
            template="components/fields/text_display.html",
            context_function="get_payment_reference_display"
        )
    ),

    FieldDefinition(
        name="payment_method_primary",
        label="Payment Method",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        filterable=True,
        filter_type=FilterType.SELECT,
        options=[
            {"value": "", "label": "All Methods"},
            {"value": "Cash", "label": "Cash"},
            {"value": "Credit Card", "label": "Credit Card"},
            {"value": "Debit Card", "label": "Debit Card"},
            {"value": "UPI", "label": "UPI"},
            {"value": "Multiple", "label": "Multiple"},
            {"value": "Advance Adjustment", "label": "Advance Adjustment"}
        ],
        readonly=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=7,
        width="110px"
    ),

    # ==========================================================================
    # CURRENCY FIELDS
    # ==========================================================================

    FieldDefinition(
        name="currency_code",
        label="Currency",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        default_value="INR",
        tab_group="payment_details",
        section="currency_info",
        view_order=1
    ),

    FieldDefinition(
        name="exchange_rate",
        label="Exchange Rate",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        default_value=1.0,
        tab_group="payment_details",
        section="currency_info",
        view_order=2
    ),

    # NOTE: Removed advance_adjustment_id and has_advance_adjustment fields
    # These columns don't exist in v_patient_payment_receipts view

    # ==========================================================================
    # WORKFLOW STATUS FIELDS
    # ==========================================================================

    FieldDefinition(
        name="workflow_status",
        label="Status",
        field_type=FieldType.STATUS_BADGE,  # Use STATUS_BADGE like supplier payments
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        filterable=True,
        filter_type=FilterType.SELECT,
        options=[
            {"value": "", "label": "All Status"},
            {"value": "draft", "label": "Draft", "css_class": "status-draft"},
            {"value": "pending_approval", "label": "Pending Approval", "css_class": "status-pending"},
            {"value": "approved", "label": "Approved", "css_class": "status-approved"},
            {"value": "rejected", "label": "Rejected", "css_class": "status-rejected"},
            {"value": "reversed", "label": "Reversed", "css_class": "status-reversed"}
        ],
        readonly=True,
        tab_group="workflow",
        section="workflow_status",
        view_order=1,
        width="130px"
    ),

    FieldDefinition(
        name="requires_approval",
        label="Requires Approval",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="workflow_status",
        view_order=2
    ),

    # ==========================================================================
    # SUBMISSION TRACKING FIELDS
    # ==========================================================================

    FieldDefinition(
        name="submitted_by",
        label="Submitted By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="submission_info",
        view_order=1
    ),

    FieldDefinition(
        name="submitted_at",
        label="Submitted At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="submission_info",
        view_order=2
    ),

    # ==========================================================================
    # APPROVAL TRACKING FIELDS
    # ==========================================================================

    FieldDefinition(
        name="approved_by",
        label="Approved By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="approval_info",
        view_order=1
    ),

    FieldDefinition(
        name="approved_at",
        label="Approved At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="approval_info",
        view_order=2
    ),

    # ==========================================================================
    # REJECTION TRACKING FIELDS
    # ==========================================================================

    FieldDefinition(
        name="rejected_by",
        label="Rejected By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="rejection_info",
        view_order=1
    ),

    FieldDefinition(
        name="rejected_at",
        label="Rejected At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="rejection_info",
        view_order=2
    ),

    FieldDefinition(
        name="rejection_reason",
        label="Rejection Reason",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="rejection_info",
        view_order=3
    ),

    # ==========================================================================
    # GL POSTING FIELDS
    # ==========================================================================

    FieldDefinition(
        name="gl_posted",
        label="GL Posted",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="gl_posting",
        view_order=1
    ),

    FieldDefinition(
        name="posting_date",
        label="Posting Date",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="gl_posting",
        view_order=2
    ),

    FieldDefinition(
        name="gl_entry_id",
        label="GL Entry ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="gl_posting",
        view_order=3
    ),

    # ==========================================================================
    # REVERSAL TRACKING FIELDS
    # ==========================================================================

    FieldDefinition(
        name="is_reversed",
        label="Reversed",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reversal_info",
        view_order=1
    ),

    FieldDefinition(
        name="reversed_at",
        label="Reversed At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reversal_info",
        view_order=2
    ),

    FieldDefinition(
        name="reversed_by",
        label="Reversed By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reversal_info",
        view_order=3
    ),

    FieldDefinition(
        name="reversal_reason",
        label="Reversal Reason",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reversal_info",
        view_order=4
    ),

    FieldDefinition(
        name="reversal_gl_entry_id",
        label="Reversal GL Entry",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reversal_info",
        view_order=5
    ),

    # ==========================================================================
    # SOFT DELETE FIELDS
    # ==========================================================================

    FieldDefinition(
        name="is_deleted",
        label="Deleted",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="delete_info",
        view_order=1
    ),

    FieldDefinition(
        name="deleted_at",
        label="Deleted At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="delete_info",
        view_order=2
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
        section="delete_info",
        view_order=3
    ),

    FieldDefinition(
        name="deletion_reason",
        label="Deletion Reason",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="delete_info",
        view_order=4
    ),

    # ==========================================================================
    # RECONCILIATION FIELDS
    # ==========================================================================

    FieldDefinition(
        name="reconciliation_status",
        label="Reconciliation Status",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reconciliation_info",
        view_order=1
    ),

    FieldDefinition(
        name="reconciliation_date",
        label="Reconciliation Date",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="reconciliation_info",
        view_order=2
    ),

    # ==========================================================================
    # REFUND INFORMATION FIELDS
    # ==========================================================================

    FieldDefinition(
        name="refund_date",
        label="Refund Date",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="refund_info",
        view_order=2
    ),

    FieldDefinition(
        name="refund_reason",
        label="Refund Reason",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="refund_info",
        view_order=3
    ),

    FieldDefinition(
        name="has_refund",
        label="Has Refund",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="refund_info",
        view_order=4
    ),

    # ==========================================================================
    # NOTES FIELD
    # ==========================================================================

    FieldDefinition(
        name="notes",
        label="Notes",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        required=False,
        tab_group="payment_details",
        section="notes",
        view_order=1
    ),

    # ==========================================================================
    # AUDIT FIELDS
    # ==========================================================================

    FieldDefinition(
        name="created_at",
        label="Created At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
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
        name="updated_at",
        label="Updated At",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_info",
        view_order=3
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
        section="audit_info",
        view_order=4
    ),

    # ==========================================================================
    # AGING FIELDS
    # ==========================================================================

    FieldDefinition(
        name="payment_age_days",
        label="Payment Age (Days)",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="invoice_details",
        section="aging_info",
        view_order=1
    ),

    FieldDefinition(
        name="aging_bucket",
        label="Aging Bucket",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="invoice_details",
        section="aging_info",
        view_order=2
    ),

    # ==========================================================================
    # CUSTOM RENDERERS - Invoice Line Items & Workflow Timeline
    # ==========================================================================

    # Payment Invoice Allocations Display (Many-to-Many)
    FieldDefinition(
        name="payment_invoice_allocations",
        label="Invoice Allocations",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="invoice_details",
        section="invoice_allocations",
        view_order=5,
        custom_renderer=CustomRenderer(
            template="components/business/payment_invoice_allocations.html",
            context_function="get_payment_invoice_allocations",
            css_classes="w-100"
        )
    ),

    # Invoice Items Display
    FieldDefinition(
        name="invoice_items_display",
        label="Invoice Line Items",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="invoice_details",
        section="invoice_items",
        view_order=10,
        custom_renderer=CustomRenderer(
            template="engine/business/universal_line_items_table.html",
            context_function="get_invoice_items_for_payment",
            css_classes="w-100"
        )
    ),

    # Workflow Timeline Display
    FieldDefinition(
        name="workflow_timeline",
        label="Workflow Timeline",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="workflow",
        section="workflow_timeline",
        view_order=1,
        custom_renderer=CustomRenderer(
            template="components/business/workflow_timeline.html",
            context_function="get_payment_workflow_timeline",
            css_classes="workflow-timeline"
        )
    ),

    # Patient Payment History Display
    FieldDefinition(
        name="patient_payment_history",
        label="Recent Payment History",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="payment_history",
        section="patient_payments",
        view_order=1,
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_patient_payment_history",
            css_classes="w-100"
        )
    ),
]

# =============================================================================
# TAB DEFINITIONS WITH NESTED SECTIONS
# =============================================================================

PATIENT_PAYMENT_TABS = {
    "payment_details": TabDefinition(
        key="payment_details",
        label="Payment Details",
        icon="fas fa-money-bill-wave",
        sections={
            "header": SectionDefinition(
                key="header",
                title="",  # No title for header section
                icon="",
                columns=1,
                order=-1,
                css_class="header-section",
                collapsible=False
            ),
            # ✅ Removed patient_info_summary - redundant with Patient Info tab
            "payment_summary": SectionDefinition(
                key="payment_summary",
                title="Payment Summary",
                icon="fas fa-calculator",
                columns=2,
                order=3
            ),
            # Payment method sections - two column display with icons
            "payment_methods": SectionDefinition(
                key="payment_methods",
                title="Payment Method Breakdown",
                icon="fas fa-credit-card",
                columns=2,
                order=4,
                collapsible=False,
                default_collapsed=False
            ),
            # Card payment details (Credit/Debit combined) - only show when used
            "card_details": SectionDefinition(
                key="card_details",
                title="Card Payment Details",
                icon="fas fa-credit-card",
                columns=2,
                order=5,
                collapsible=True,
                default_collapsed=False,
                conditional_display="credit_card_amount > 0 or debit_card_amount > 0"
            ),
            # UPI payment details - only show when used
            "upi_details": SectionDefinition(
                key="upi_details",
                title="UPI Payment Details",
                icon="fas fa-mobile-alt",
                columns=2,
                order=6,
                collapsible=True,
                default_collapsed=False,
                conditional_display="upi_amount > 0"
            ),
            # Wallet points details - only show when used
            "wallet_points_details": SectionDefinition(
                key="wallet_points_details",
                title="🎁 Wallet Points Redemption",
                icon="fas fa-gift",
                columns=2,
                order=7,
                collapsible=True,
                default_collapsed=False,
                conditional_display="wallet_points_amount > 0"
            ),
            # Advance adjustment details - only show when used
            "advance_details": SectionDefinition(
                key="advance_details",
                title="⏩ Advance Adjustment Details",
                icon="fas fa-forward",
                columns=2,
                order=8,
                collapsible=True,
                default_collapsed=False,
                conditional_display="advance_adjustment_amount > 0"
            ),
            "currency_info": SectionDefinition(
                key="currency_info",
                title="Currency Information",
                icon="fas fa-dollar-sign",
                columns=2,
                order=6
            ),
            # NOTE: Removed advance_info section - fields don't exist in view
            "refund_info": SectionDefinition(
                key="refund_info",
                title="Refund Information",
                icon="fas fa-undo",
                columns=2,
                order=7
            ),
            "notes": SectionDefinition(
                key="notes",
                title="Notes",
                icon="fas fa-sticky-note",
                columns=1,
                order=8
            ),
        },
        order=1,
        default_active=True
    ),

    "invoice_details": TabDefinition(
        key="invoice_details",
        label="Invoice Details",
        icon="fas fa-file-invoice",
        sections={
            "invoice_allocations": SectionDefinition(
                key="invoice_allocations",
                title="Invoice Allocations (Payment Breakdown)",
                icon="fas fa-file-invoice-dollar",
                columns=1,
                order=0,
                collapsible=False
            ),
            "invoice_items": SectionDefinition(
                key="invoice_items",
                title="Invoice Line Items",
                icon="fas fa-list-ul",
                columns=1,
                order=1
            ),
            "aging_info": SectionDefinition(
                key="aging_info",
                title="Aging Information",
                icon="fas fa-clock",
                columns=2,
                order=3
            ),
        },
        order=2,
        default_active=False
    ),

    "patient_info": TabDefinition(
        key="patient_info",
        label="Patient Info",
        icon="fas fa-user-injured",
        sections={
            "patient_details": SectionDefinition(
                key="patient_details",
                title="Patient Details",
                icon="fas fa-id-card",
                columns=2,
                order=1
            ),
        },
        order=3,
        default_active=False
    ),

    "workflow": TabDefinition(
        key="workflow",
        label="Workflow",
        icon="fas fa-tasks",
        sections={
            "workflow_status": SectionDefinition(
                key="workflow_status",
                title="Current Status",
                icon="fas fa-info-circle",
                columns=2,
                order=0,
                collapsible=False
            ),
            "workflow_timeline": SectionDefinition(
                key="workflow_timeline",
                title="Workflow Timeline",
                icon="fas fa-project-diagram",
                columns=1,
                order=1,
                collapsible=False
            ),
            "submission_info": SectionDefinition(
                key="submission_info",
                title="Submission Information",
                icon="fas fa-paper-plane",
                columns=2,
                order=2,
                collapsible=True
            ),
            "approval_info": SectionDefinition(
                key="approval_info",
                title="Approval Details",
                icon="fas fa-check-circle",
                columns=2,
                order=3,
                collapsible=True
            ),
            "rejection_info": SectionDefinition(
                key="rejection_info",
                title="Rejection Details",
                icon="fas fa-times-circle",
                columns=2,
                order=4,
                collapsible=True
            ),
            "gl_posting": SectionDefinition(
                key="gl_posting",
                title="GL Posting",
                icon="fas fa-book",
                columns=2,
                order=5,
                collapsible=True
            ),
            "reversal_info": SectionDefinition(
                key="reversal_info",
                title="Reversal Information",
                icon="fas fa-undo-alt",
                columns=2,
                order=6,
                collapsible=True
            ),
            "reconciliation_info": SectionDefinition(
                key="reconciliation_info",
                title="Bank Reconciliation",
                icon="fas fa-balance-scale",
                columns=2,
                order=7,
                collapsible=True
            ),
        },
        order=4,
        default_active=False
    ),

    "payment_history": TabDefinition(
        key="payment_history",
        label="Payment History",
        icon="fas fa-history",
        sections={
            "patient_payments": SectionDefinition(
                key="patient_payments",
                title="Last 6 Months Payment History",
                icon="fas fa-clock",
                columns=1,
                order=0
            )
        },
        order=5
    ),

    "system_info": TabDefinition(
        key="system_info",
        label="System Info",
        icon="fas fa-cog",
        sections={
            "technical_info": SectionDefinition(
                key="technical_info",
                title="System Information",
                icon="fas fa-server",
                columns=2,
                order=1
            ),
            "audit_info": SectionDefinition(
                key="audit_info",
                title="Audit Trail",
                icon="fas fa-history",
                columns=2,
                order=2
            ),
            "delete_info": SectionDefinition(
                key="delete_info",
                title="Deletion Information",
                icon="fas fa-trash",
                columns=2,
                order=3
            ),
        },
        order=6,
        default_active=False
    ),
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

PATIENT_PAYMENT_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    responsive_breakpoint='md',
    tabs=PATIENT_PAYMENT_TABS,
    default_tab='payment_details',
    sticky_tabs=True,
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "payment_id",
        "primary_label": "Payment Receipt",
        # Title field - this appears at the top
        "title_field": "patient_name",
        "title_label": "Patient",
        "status_field": "workflow_status",
        "secondary_fields": [
            {"field": "patient_mrn", "label": "MRN", "icon": "fas fa-id-card"},
            {"field": "payment_date", "label": "Payment Date", "icon": "fas fa-calendar", "type": "date"},
            {"field": "payment_method_total", "label": "Amount Paid", "icon": "fas fa-rupee-sign", "type": "currency", "css_classes": "text-xl font-bold text-success"},
            {"field": "payment_method_primary", "label": "Payment Method", "icon": "fas fa-credit-card"}
        ]
    }
)

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

PATIENT_PAYMENT_ACTIONS = [

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
        id="goto_patient_invoices_list",
        label="Patient Invoices",
        icon="fas fa-file-invoice",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "patient_invoices"},
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="billing_invoice_view",
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
        id="create_payment",
        label="Record Payment",
        icon="fas fa-plus",
        button_type=ButtonType.PRIMARY,
        route_name="billing_views.payment_patient_selection",
        show_in_list=False,
        show_in_list_toolbar=True,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="patient_payments_create",
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
        route_params={"entity_type": "patient_payments", "item_id": "{payment_id}"},
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="patient_payments_view",
        order=1
    ),

    ActionDefinition(
        id="print_row",
        label="Print",
        icon="fas fa-print",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_document_view",
        route_params={"entity_type": "patient_payments", "item_id": "{payment_id}", "doc_type": "receipt"},
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        permission="patient_payments_view",
        order=2
    ),

    ActionDefinition(
        id="approve_row",
        label="Approve",
        icon="fas fa-check-circle",
        button_type=ButtonType.SUCCESS,
        route_name="billing_views.approve_payment",
        route_params={"payment_id": "{payment_id}"},
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        conditions={
            "workflow_status": ["pending_approval"],
            "is_deleted": [False],
            "is_reversed": [False]
        },
        permission="patient_payments_approve",
        order=3,
        confirmation_required=True,
        confirmation_message="Are you sure you want to approve this payment? GL entries will be posted."
    ),

    ActionDefinition(
        id="delete_row",
        label="Delete",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        route_name="billing_views.delete_payment",
        route_params={"payment_id": "{payment_id}"},
        show_in_list=True,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=False,
        display_type=ActionDisplayType.BUTTON,
        conditions={
            "workflow_status": ["draft", "rejected"],
            "is_deleted": [False]
        },
        permission="patient_payments_delete",
        order=4,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this payment?"
    ),

    # =============================================================================
    # DETAIL/VIEW PAGE - TOOLBAR ACTIONS (Navigation buttons)
    # =============================================================================

    ActionDefinition(
        id="goto_payments_list",
        label="Patient Payments",
        icon="fas fa-money-bill",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_list_view",
        route_params={"entity_type": "patient_payments"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="patient_payments_view",
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
        id="goto_invoices_detail",
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
        id="print_payment",
        label="Print Receipt",
        icon="fas fa-print",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_document_view",
        route_params={
            "entity_type": "patient_payments",
            "item_id": "{payment_id}",
            "doc_type": "receipt"
        },
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="patient_payments_view",
        order=6
    ),

    # =============================================================================
    # DETAIL/VIEW PAGE - DROPDOWN ACTIONS (Edit, Delete, Approve, Reverse)
    # =============================================================================

    ActionDefinition(
        id="edit_payment",
        label="Edit Payment",
        icon="fas fa-edit",
        button_type=ButtonType.WARNING,
        route_name="billing_views.edit_payment",
        route_params={"payment_id": "{payment_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "workflow_status": ["draft", "rejected"],
            "is_deleted": [False]
        },
        permission="patient_payments_edit",
        order=1
    ),

    ActionDefinition(
        id="delete_payment",
        label="Delete Payment",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        route_name="billing_views.delete_payment",
        route_params={"payment_id": "{payment_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "workflow_status": ["draft", "rejected"],
            "is_deleted": [False]
        },
        permission="patient_payments_delete",
        order=2,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this payment?"
    ),

    ActionDefinition(
        id="approve_payment",
        label="Approve Payment",
        icon="fas fa-check-circle",
        button_type=ButtonType.SUCCESS,
        route_name="billing_views.approve_payment",
        route_params={"payment_id": "{payment_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "workflow_status": ["pending_approval"],
            "is_deleted": [False],
            "is_reversed": [False]
        },
        permission="patient_payments_approve",
        order=3,
        confirmation_required=True,
        confirmation_message="Are you sure you want to approve this payment? GL entries will be posted."
    ),

    ActionDefinition(
        id="reverse_payment",
        label="Reverse Payment",
        icon="fas fa-exchange-alt",
        button_type=ButtonType.DANGER,
        route_name="billing_views.reverse_payment",
        route_params={"payment_id": "{payment_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "workflow_status": ["approved"],
            "is_deleted": [False],
            "is_reversed": [False],
            "gl_posted": [True]
        },
        permission="patient_payments_reverse",
        order=4,
        confirmation_required=True,
        confirmation_message="Are you sure you want to reverse this payment? This will create GL reversal entries."
    ),

    ActionDefinition(
        id="restore_payment",
        label="Restore Payment",
        icon="fas fa-undo",
        button_type=ButtonType.SUCCESS,
        route_name="billing_views.restore_payment",
        route_params={"payment_id": "{payment_id}"},
        show_in_list=False,
        show_in_list_toolbar=False,
        show_in_detail_toolbar=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "is_deleted": [True]
        },
        permission="patient_payments_delete",
        order=5,
        confirmation_required=True,
        confirmation_message="Are you sure you want to restore this deleted payment?"
    ),
]

# =============================================================================
# SUMMARY CARDS
# =============================================================================

PATIENT_PAYMENT_SUMMARY_CARDS = [
    {
        "id": "total_count",
        "field": "total_count",
        "label": "Total Payments",
        "icon": "fas fa-receipt",
        "icon_css": "stat-card-icon primary",
        "type": "number",
        "visible": True,
        "order": 1
    },

    {
        "id": "total_amount",
        "field": "payment_method_total",  # ✅ Use payment_method_total (includes wallet + advance)
        "label": "Total Amount",
        "icon": "fas fa-rupee-sign",
        "icon_css": "stat-card-icon success",
        "type": "currency",
        "visible": True,
        "order": 2
    },

    {
        "id": "pending_approval_count",
        "field": "pending_approval_count",
        "label": "Pending Approval",
        "icon": "fas fa-clock",
        "icon_css": "stat-card-icon warning",
        "type": "number",
        "filter_field": "workflow_status",
        "filter_value": "pending_approval",
        "visible": True,
        "order": 3
    },

    {
        "id": "approved_count",
        "field": "approved_count",
        "label": "Approved",
        "icon": "fas fa-check-circle",
        "icon_css": "stat-card-icon success",
        "type": "number",
        "filter_field": "workflow_status",
        "filter_value": "approved",
        "visible": True,
        "order": 4
    },

    {
        "id": "current_month_count",
        "field": "current_month_count",
        "label": "This Month",
        "icon": "fas fa-calendar-check",
        "icon_css": "stat-card-icon info",
        "type": "number",
        "visible": True,
        "order": 5
    },

    {
        "id": "cash_amount_total",
        "field": "cash_amount_sum",  # Reference the hidden aggregation card
        "label": "Cash Payments",
        "icon": "fas fa-money-bill",
        "icon_css": "stat-card-icon success",
        "type": "currency",
        "visible": True,
        "order": 6
    },

    {
        "id": "card_amount_total",
        "field": "card_amount_sum",  # Reference the hidden aggregation card
        "label": "Card Payments",
        "icon": "fas fa-credit-card",
        "icon_css": "stat-card-icon primary",
        "type": "currency",
        "visible": True,
        "order": 7
    },

    {
        "id": "upi_amount_total",
        "field": "upi_amount_sum",  # Reference the hidden aggregation card
        "label": "UPI Payments",
        "icon": "fas fa-mobile-alt",
        "icon_css": "stat-card-icon info",
        "type": "currency",
        "visible": True,
        "order": 8
    },

    # ==========================================================================
    # HIDDEN AGGREGATION CARDS - For automatic calculation
    # ==========================================================================
    # These hidden cards enable proper SUM calculations in the Universal Engine

    {
        "id": "cash_amount_sum",
        "field": "cash_amount",  # Matches view column name
        "label": "Cash Total",
        "type": "currency",  # Triggers SUM calculation
        "visible": False  # Hidden - just for calculation
    },
    {
        "id": "card_amount_sum",
        "field": "credit_card_amount",  # Matches view column name
        "label": "Credit Card Total",
        "type": "currency",  # Triggers SUM calculation
        "visible": False  # Hidden - just for calculation
    },
    {
        "id": "debit_card_amount_sum",
        "field": "debit_card_amount",  # Matches view column name
        "label": "Debit Card Total",
        "type": "currency",  # Triggers SUM calculation
        "visible": False  # Hidden - just for calculation
    },
    {
        "id": "upi_amount_sum",
        "field": "upi_amount",  # Matches view column name
        "label": "UPI Total",
        "type": "currency",  # Triggers SUM calculation
        "visible": False  # Hidden - just for calculation
    },
]

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

PATIENT_PAYMENT_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'start_date': FilterCategory.DATE,
    'end_date': FilterCategory.DATE,
    'payment_date': FilterCategory.DATE,
    'date_from': FilterCategory.DATE,
    'date_to': FilterCategory.DATE,
    # Removed 'financial_year' - not available in v_patient_payment_receipts
    'date_range': FilterCategory.DATE,

    # Amount filters
    'amount_min': FilterCategory.AMOUNT,
    'amount_max': FilterCategory.AMOUNT,
    'min_amount': FilterCategory.AMOUNT,
    'max_amount': FilterCategory.AMOUNT,
    'total_amount': FilterCategory.AMOUNT,

    # Search filters
    'patient_name_search': FilterCategory.SEARCH,
    'search': FilterCategory.SEARCH,
    'patient_search': FilterCategory.SEARCH,
    'invoice_number': FilterCategory.SEARCH,
    'patient_mrn': FilterCategory.SEARCH,
    'reference_number': FilterCategory.SEARCH,
    'notes': FilterCategory.SEARCH,

    # Selection filters
    'workflow_status': FilterCategory.SELECTION,
    'statuses': FilterCategory.SELECTION,
    'status': FilterCategory.SELECTION,
    'payment_method': FilterCategory.SELECTION,
    'payment_method_primary': FilterCategory.SELECTION,
    'payment_methods': FilterCategory.SELECTION,

    # Relationship filters
    'patient_id': FilterCategory.RELATIONSHIP,
    'patient_name': FilterCategory.SEARCH,
    'branch_id': FilterCategory.RELATIONSHIP,
}

PATIENT_PAYMENT_DEFAULT_FILTERS = {
    # Removed 'financial_year': 'current' - view doesn't have financial_year column
    'workflow_status': '',
    'payment_method_primary': ''  # ✅ Changed from 'payment_method' to match actual field name
}

PATIENT_PAYMENT_CATEGORY_CONFIGS = {
    FilterCategory.DATE: {
        'default_preset': 'current_financial_year',
        'auto_apply_financial_year': True
    },
    FilterCategory.AMOUNT: {
        'currency_symbol': '₹',
        'decimal_places': 2,
        'allow_range': True,
        'range_operators': ['between', 'less_than', 'greater_than']
    },
    FilterCategory.SEARCH: {
        'min_search_length': 1,
        'auto_submit': False,
        'search_on_enter': True
    },
    FilterCategory.SELECTION: {
        'show_empty_option': True,
        'empty_option_label': 'All'
    },
}

# =============================================================================
# PERMISSIONS
# =============================================================================

PATIENT_PAYMENT_PERMISSIONS = {
    'view': 'patient_payments_view',
    'create': 'patient_payments_create',
    'edit': 'patient_payments_edit',
    'delete': 'patient_payments_delete',
    'approve': 'patient_payments_approve',
    'reverse': 'patient_payments_reverse',
    'refund': 'patient_payments_refund',
}

# =============================================================================
# DOCUMENT CONFIGURATIONS
# =============================================================================

PATIENT_PAYMENT_RECEIPT_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type="receipt",
    title="Payment Receipt",

    # Use simple layout with header for clean receipt
    print_layout_type=PrintLayoutType.SIMPLE_WITH_HEADER,
    include_header_section=True,
    include_action_buttons=False,

    # Page setup
    page_size="A4",
    orientation="portrait",
    margins={
        "top": "15mm",
        "right": "15mm",
        "bottom": "15mm",
        "left": "15mm"
    },

    # Company header
    show_logo=True,
    show_company_info=True,
    header_text="PAYMENT RECEIPT",

    # Only show essential tabs for receipt
    visible_tabs=["payment_details", "invoice_details", "patient_info"],

    # Hide these specific sections
    hidden_sections=[
        "documents",
        "technical_info",
        "audit_trail",
        "workflow_status",
        "workflow_history",
        "workflow_steps"
    ],

    # Signature lines
    signature_fields=[
        {"label": "Authorized By", "width": "250px"},
        {"label": "Received From", "width": "250px"}
    ],

    # Footer
    show_footer=True,
    footer_text="This is a computer generated receipt",
    show_print_info=True,

    # Terms and Conditions for Receipt
    show_terms=True,
    terms_title="Terms and Conditions",
    terms_content=[
        "This receipt is valid subject to realization of payment.",
        "Please retain this receipt for future reference.",
        "Any discrepancy should be reported within 7 days."
    ],

    # Status-specific footer messages
    status_footer_text={
        "approved": "This is an approved payment receipt.",
        "draft": "This is a draft receipt pending approval.",
        "pending_approval": "This receipt is pending approval.",
        "rejected": "This payment has been rejected."
    },

    # Show date with signatures
    show_signature_date=True,

    # Watermark
    watermark_draft=True,
    watermark_text="DRAFT",

    allowed_formats=["pdf", "print", "preview"]
)

# Document Configs Dictionary
PATIENT_PAYMENT_DOCUMENT_CONFIGS = {
    "receipt": PATIENT_PAYMENT_RECEIPT_CONFIG,
}


# =============================================================================
# MAIN ENTITY CONFIGURATION
# =============================================================================

PATIENT_PAYMENT_CONFIG = EntityConfiguration(
    # Basic Information
    entity_type="patient_payments",
    name="Patient Payment",
    plural_name="Patient Payments",
    service_name="patient_payments",
    table_name="v_patient_payment_receipts",
    primary_key="payment_id",
    title_field="invoice_number",
    subtitle_field="patient_name",
    icon="fas fa-money-bill-wave",

    # List View Configuration
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    page_title="Patient Payments",
    description="Patient payment receipts and transactions",
    searchable_fields=["payment_id", "invoice_number", "patient_name", "patient_mrn", "reference_number", "notes"],
    default_sort_field="payment_date",
    default_sort_direction="desc",

    # Core Configuration References
    fields=PATIENT_PAYMENT_FIELDS,
    view_layout=PATIENT_PAYMENT_VIEW_LAYOUT,
    actions=PATIENT_PAYMENT_ACTIONS,
    summary_cards=PATIENT_PAYMENT_SUMMARY_CARDS,
    permissions=PATIENT_PAYMENT_PERMISSIONS,

    # Filter Configuration
    filter_category_mapping=PATIENT_PAYMENT_FILTER_CATEGORY_MAPPING,
    default_filters=PATIENT_PAYMENT_DEFAULT_FILTERS,
    category_configs=PATIENT_PAYMENT_CATEGORY_CONFIGS,

    # Date and Amount Configuration
    primary_date_field="payment_date",
    primary_amount_field="payment_method_total",  # ✅ Use payment_method_total (includes wallet + advance)

    # Soft Delete Configuration
    enable_soft_delete=True,
    soft_delete_field="is_deleted",
    cascade_delete=False,
    delete_confirmation_message="Are you sure you want to delete this payment?",

    # Document Generation Support
    document_enabled=True,
    document_configs=PATIENT_PAYMENT_DOCUMENT_CONFIGS,
    default_document="receipt",

    # Fields that need to be calculated/included for documents
    include_calculated_fields=[
        "patient_name",          # From patient relationship
        "patient_mrn",           # From patient relationship
        "patient_address",       # From patient relationship
        "amount_in_words",       # Convert amount to words
        "created_by_name",       # From created_by user
        "approved_by_name",      # From approved_by user
        "branch_name",           # From current branch context
        "invoice_allocations",   # List of invoice allocations for multi-invoice payments
    ],

    # Optional: Document-specific permissions (uses view permission by default)
    document_permissions={
        "receipt": "patient_payments_view",
    }
)

# =============================================================================
# ENTITY FILTER CONFIGURATION
# =============================================================================

PATIENT_PAYMENT_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='patient_payments',
    filter_mappings={
        'workflow_status': {
            'options': [
                {'value': '', 'label': 'All Status'},
                {'value': 'draft', 'label': 'Draft'},
                {'value': 'pending_approval', 'label': 'Pending Approval'},
                {'value': 'approved', 'label': 'Approved'},
                {'value': 'rejected', 'label': 'Rejected'},
                {'value': 'reversed', 'label': 'Reversed'}
            ]
        },
        'payment_method_primary': {
            'options': [
                {'value': '', 'label': 'All Methods'},
                {'value': 'Cash', 'label': 'Cash'},
                {'value': 'Credit Card', 'label': 'Credit Card'},
                {'value': 'Debit Card', 'label': 'Debit Card'},
                {'value': 'UPI', 'label': 'UPI'},
                {'value': 'Multiple', 'label': 'Multiple'},
                {'value': 'Advance Adjustment', 'label': 'Advance Adjustment'}
            ]
        },
        'patient_name': {
            'field': 'patient_name',
            'type': 'entity_dropdown',
            'label': 'Patient',
            'entity_type': 'patients',
            'search_fields': ['full_name', 'mrn'],
            'display_template': '{patient_name}',
            'placeholder': 'Type to search patients...'
        }
    }
)

# =============================================================================
# ENTITY SEARCH CONFIGURATION
# =============================================================================

PATIENT_PAYMENT_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='patient_payments',
    search_fields=['payment_id', 'invoice_number', 'patient_name', 'patient_mrn'],
    display_template='{payment_id} - {patient_name}',  # ✅ Use payment_id as primary identifier
    min_chars=1,
    max_results=10,
    sort_field='payment_date'
)

# =============================================================================
# EXPORT MAIN CONFIGURATION
# =============================================================================

# Export the main configuration object (required by Universal Engine)
config = PATIENT_PAYMENT_CONFIG
filter_config = PATIENT_PAYMENT_ENTITY_FILTER_CONFIG  # ✅ Export filter config for filters to work!
search_config = PATIENT_PAYMENT_SEARCH_CONFIG  # ✅ Export search config
