"""
Complete Entity Configurations - Based on Your Actual Models
File: app/config/entity_configurations.py

Uses exact field names from your transaction.py and master.py models
Ensures compatibility with all referenced fields in universal engine code

Command to directly run import of bp to test the issues
from app.views.universal_views import universal_bp 

"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from app.config.core_definitions import *
# from app.config.core_definitions import (
#     FieldType,
#     ButtonType,
#     FieldDefinition,
#     ActionDefinition,
#     EntitySearchConfiguration,
#     EntityConfiguration,
#     EntityFilterConfiguration,
#     ComplexDisplayType,
#     CustomRenderer,
#     FilterConfiguration
# )
from app.config.filter_categories import FilterCategory

# =============================================================================
# DECLARATIVE SECTION DEFINITIONS (Optional - for custom sections)
# =============================================================================

SUPPLIER_PAYMENT_SECTION_DEFINITIONS = {
    'identity': SectionDefinition(
        key='identity',
        title='Payment Identity',
        icon='fas fa-fingerprint',
        columns=2,
        order=0
    ),
    'financial': SectionDefinition(
        key='financial',
        title='Financial Details',
        icon='fas fa-money-bill-wave',
        columns=2,
        order=1
    ),
    'breakdown': SectionDefinition(
        key='breakdown',
        title='Payment Breakdown',
        icon='fas fa-chart-pie',
        columns=2,
        collapsible=True,
        order=2
    ),
    'supplier_info': SectionDefinition(
        key='supplier_info',
        title='Supplier Information',
        icon='fas fa-building',
        columns=2,
        order=0
    ),
    'invoice_details': SectionDefinition(
        key='invoice_details',
        title='Invoice Details',
        icon='fas fa-file-invoice',
        columns=2,
        order=1
    ),
    'workflow_status': SectionDefinition(
        key='workflow_status',
        title='Approval Status',
        icon='fas fa-tasks',
        columns=1,
        order=0
    ),
    'audit_trail': SectionDefinition(
        key='audit_trail',
        title='Audit Information',
        icon='fas fa-history',
        columns=2,
        order=0
    )
}

# =============================================================================
# DECLARATIVE TAB DEFINITIONS (Optional - for tabbed layout)
# =============================================================================

SUPPLIER_PAYMENT_TAB_DEFINITIONS = {
    'core': TabDefinition(
        key='core',
        label='Payment Details',
        icon='fas fa-money-bill-wave',
        sections={
            'identity': SUPPLIER_PAYMENT_SECTION_DEFINITIONS['identity'],
            'financial': SUPPLIER_PAYMENT_SECTION_DEFINITIONS['financial'],
            'breakdown': SUPPLIER_PAYMENT_SECTION_DEFINITIONS['breakdown']
        },
        order=0,
        default_active=True
    ),
    'supplier': TabDefinition(
        key='supplier',
        label='Supplier & Invoice',
        icon='fas fa-building',
        sections={
            'supplier_info': SUPPLIER_PAYMENT_SECTION_DEFINITIONS['supplier_info'],
            'invoice_details': SUPPLIER_PAYMENT_SECTION_DEFINITIONS['invoice_details']
        },
        order=1
    ),
    'approval': TabDefinition(
        key='approval',
        label='Workflow & Approval',
        icon='fas fa-check-circle',
        sections={
            'workflow_status': SUPPLIER_PAYMENT_SECTION_DEFINITIONS['workflow_status']
        },
        order=2
    ),
    'system': TabDefinition(
        key='system',
        label='System Information',
        icon='fas fa-cog',
        sections={
            'audit_trail': SUPPLIER_PAYMENT_SECTION_DEFINITIONS['audit_trail']
        },
        order=3
    )
}


# =============================================================================
# SUPPLIER PAYMENT CONFIGURATION - Based on Your SupplierPayment Model
# =============================================================================

SUPPLIER_PAYMENT_CONFIG = EntityConfiguration(
    entity_type="supplier_payments",
    name="Supplier Payment",
    plural_name="Supplier Payments",
    service_name="supplier_payments",
    table_name="supplier_payments",
    primary_key="payment_id",  # Exact field name from your model
    title_field="reference_no",  # Exact field name from your model
    subtitle_field="supplier_name",  # From relationship/join
    icon="fas fa-money-bill-wave",
    # ✅ NEW: Control saved filter suggestions
    enable_saved_filter_suggestions=True,  # Enable for this entity
    enable_auto_submit=False,
    page_title="Supplier Payments",
    description="Manage payments to suppliers and vendors",
    searchable_fields=["reference_no", "supplier_name", "notes"],  # Exact field names
    default_sort_field="payment_date",  # Exact field name from your model
    default_sort_direction="desc",
    model_class="app.models.transaction.SupplierPayment",
    

    fields=[
        # Primary Key - UUID field from your model
        FieldDefinition(
            name="payment_id",  # Exact field name
            label="Payment ID",
            field_type=FieldType.UUID,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            readonly=True,
            # NEW: View organization parameters (declarative)
            tab_group="core",
            section="identity",
            view_order=1
        ),
        
        # System fields - from your TenantMixin
        FieldDefinition(
            name="hospital_id",  # Exact field name
            label="Hospital",
            field_type=FieldType.UUID,
            show_in_list=False,
            show_in_detail=False,
            show_in_form=False,
            required=True
        ),
        FieldDefinition(
            name="branch_id",  # Exact field name
            label="Branch",
            field_type=FieldType.SELECT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            required=False,
            autocomplete_enabled=True,
            autocomplete_source="backend"
        ),
        
        # Payment identification fields - exact names from your model
        FieldDefinition(
            name="payment_date",  # Exact field name
            label="Payment Date",
            field_type=FieldType.DATE,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=True,
            filterable=True,
            # ✅ CONFIGURATION-DRIVEN: Define date range parameter names
            filter_aliases=["start_date", "end_date", "date_from", "date_to"],
            filter_type="date_range",
            required=True,
            # NEW: View organization parameters
            tab_group="core",
            section="identity",
            view_order=3,
            help_text="Date when payment was made",
            options=[
                {"value": "today", "label": "Today"},
                {"value": "yesterday", "label": "Yesterday"},
                {"value": "this_week", "label": "This Week"},
                {"value": "this_month", "label": "This Month"},
                {"value": "last_30_days", "label": "Last 30 Days"},
                {"value": "financial_year", "label": "Financial Year"},
                {"value": "clear", "label": "Clear"}
            ]
        ),

        FieldDefinition(
            name="start_date",
            label="From Date",
            field_type=FieldType.DATE,
            show_in_list=False,
            show_in_detail=False,
            show_in_form=False,
            searchable=False,
            sortable=False,
            filterable=True,
            required=False,
            help_text="Filter from this date",
            placeholder="Start date"
        ),
        FieldDefinition(
            name="end_date", 
            label="To Date",
            field_type=FieldType.DATE,
            show_in_list=False,
            show_in_detail=False,
            show_in_form=False,
            searchable=False,
            sortable=False,
            filterable=True,
            required=False,
            help_text="Filter to this date",
            placeholder="End date"
        ),

        FieldDefinition(
            name="reference_no",  # Exact field name from your model
            label="Payment Reference",
            field_type=FieldType.TEXT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=True,
            sortable=True,
            filterable=True,
            # NEW: View organization parameters
            tab_group="core",
            section="identity",
            view_order=2,
            # ✅ CONFIGURATION-DRIVEN: Define alternative parameter names
            filter_aliases=["ref_no", "reference_number"],
            filter_type="search",
            required=True,
            placeholder="e.g., PAY-2024-001",
            help_text="Unique payment reference number",
            entity_search_config=EntitySearchConfiguration(
                target_entity="supplier_payments",
                search_fields=["reference_no"],
                display_template="{reference_no}",
                min_chars=2,
                max_results=10,
                placeholder_template="Search payment references..."
                
            )
        ),
        
        # Supplier relationship - exact field name from your model
        FieldDefinition(
            name="supplier_id",  # Exact field name - foreign key
            label="Supplier",
            field_type=FieldType.ENTITY_SEARCH,
            show_in_list=False,
            show_in_detail=False,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=True,
            required=True,
            options=[],  # Will be populated dynamically from Supplier model
            help_text="Select the supplier for this payment",
            related_field="supplier",
            # NEW: View organization parameters
            tab_group="supplier",
            section="supplier_info",
            view_order=2,
            autocomplete_enabled=True,      # ✅ ADD only if missing
            autocomplete_source="suppliers", # ✅ ADD only if missing
            entity_search_config=EntitySearchConfiguration(
                target_entity="suppliers",
                search_fields=["supplier_name", "contact_person_name"],
                display_template="{supplier_name}",
                min_chars=2,
                max_results=10,
                additional_filters={"status": "active"},
                placeholder_template="Search suppliers by name or code..."
            )
        ),
        # Display field for supplier name (from relationship)
        FieldDefinition(
            name="supplier_name",  # From relationship join
            label="Supplier",
            field_type=FieldType.TEXT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=False,  # Not editable, comes from relationship
            searchable=True,
            sortable=True,
            filterable=True,
            readonly=True,
            # ✅ CONFIGURATION-DRIVEN: Define all possible search parameter names
            filter_aliases=["supplier_name_search", "search", "supplier_search", "supplier_text"],
            filter_type="search",  # Uses LIKE/ILIKE
            related_field="supplier",  # Indicates relationship join needed
            # NEW: View organization parameters
            tab_group="supplier",
            section="supplier_info",
            view_order=1
        ),
        
        # Invoice relationship - exact field name from your model
        FieldDefinition(
            name="invoice_id",  # Exact field name - foreign key
            label="Invoice",
            field_type=FieldType.SELECT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=True,
            required=False,
            options=[],  # Will be populated dynamically based on supplier
            help_text="Optional: Link to specific invoice",
            related_field="invoice",
            # NEW: View organization parameters
            tab_group="supplier",
            section="invoice_details",
            view_order=1
        ),
        
        # Amount fields - exact names from your model
        FieldDefinition(
            name="amount",  # Exact field name
            label="Total Amount",
            field_type=FieldType.CURRENCY,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=True,
            filterable=True,
            # NEW: View organization parameters
            tab_group="core",
            section="financial",
            view_order=1,
            # ✅ CONFIGURATION-DRIVEN: Define range parameter names
            filter_aliases=["min_amount", "max_amount", "amount_min", "amount_max"],
            filter_type="range",  # Handles >= and <= operations
            required=True,
            help_text="Total payment amount",
            format_pattern="mixed_payment_breakdown"
        ),
        
        # Multi-method payment amounts - exact field names from your model
        FieldDefinition(
            name="cash_amount",  # Exact field name
            label="Cash Amount",
            field_type=FieldType.CURRENCY,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=False,
            required=False,
            help_text="Amount paid in cash",
            # NEW: View organization parameters
            tab_group="core",
            section="breakdown",
            view_order=1,
            conditional_display="item.cash_amount and item.cash_amount > 0"
        ),
        FieldDefinition(
            name="cheque_amount",  # Exact field name
            label="Cheque Amount",
            field_type=FieldType.CURRENCY,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=False,
            required=False,
            help_text="Amount paid by cheque",
            # NEW: View organization parameters
            tab_group="core",
            section="breakdown",
            view_order=2,
            conditional_display="item.cheque_amount and item.cheque_amount > 0"
        ),
        FieldDefinition(
            # Existing parameters
            name="cheque_number",
            label="Cheque Number",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            
            # NEW: View organization parameters
            tab_group="core",
            section="breakdown",
            view_order=3,
            conditional_display="item.cheque_number"
        ),
        FieldDefinition(
            name="bank_transfer_amount",  # Exact field name
            label="Bank Transfer Amount",
            field_type=FieldType.CURRENCY,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=False,
            required=False,
            help_text="Amount paid via bank transfer",
            # NEW: View organization parameters
            tab_group="core",
            section="breakdown",
            view_order=4,
            conditional_display="item.bank_transfer_amount and item.bank_transfer_amount > 0"
        ),
        FieldDefinition(
            name="upi_amount",  # Exact field name
            label="UPI Amount",
            field_type=FieldType.CURRENCY,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=False,
            required=False,
            help_text="Amount paid via UPI"
        ),
        
        # Payment method - exact field name from your model
        FieldDefinition(
            name="payment_method",  # Exact field name
            label="Payment Method",
            field_type=FieldType.SELECT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=True,
            filter_aliases=["payment_methods", "pay_method"],
            required=True,
            options=[
                {"value": "bank_transfer", "label": "Bank Transfer"},
                {"value": "cheque", "label": "Cheque"},
                {"value": "cash", "label": "Cash"},
                {"value": "upi", "label": "UPI"},
                {"value": "mixed", "label": "Mixed Payment"}
            ],
            help_text="Primary payment method used"
        ),
        
        # Workflow and approval fields - exact names from your model
        FieldDefinition(
            name="workflow_status",  # Exact field name
            label="Status",
            field_type=FieldType.STATUS_BADGE,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=True,
            filterable=True,
            required=True,
            # NEW: View organization parameters
            tab_group="approval",
            section="workflow_status",
            view_order=1,
            # ✅ CONFIGURATION-DRIVEN: Define all possible input parameter names
            filter_aliases=["statuses", "status", "approval_status"],
            filter_type="exact",
            options=[
                {"value": "draft", "label": "Draft", "css_class": "universal-status-draft"},
                {"value": "pending", "label": "Pending Approval", "css_class": "universal-status-pending"},
                {"value": "pending_approval", "label": "Pending Approval", "css_class": "universal-status-pending"},
                {"value": "approved", "label": "Approved", "css_class": "universal-status-approved"},
                {"value": "completed", "label": "Payment Completed", "css_class": "universal-status-completed"},
                {"value": "rejected", "label": "Rejected", "css_class": "universal-status-cancelled"},
                {"value": "cancelled", "label": "Cancelled", "css_class": "universal-status-cancelled"}
            ]
        ),
        FieldDefinition(
            name="approval_level",  # Exact field name
            label="Approval Level",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            searchable=False,
            sortable=False,
            filterable=True,
            required=False,
            readonly=True
        ),
        FieldDefinition(
            name="approved_by",  # Exact field name
            label="Approved By",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            searchable=False,
            sortable=False,
            filterable=False,
            required=False,
            readonly=True,
            # NEW: View organization parameters
            tab_group="approval",
            section="workflow_status",
            view_order=2
        ),
        FieldDefinition(
            name="approved_at",  # Exact field name
            label="Approved Date",
            field_type=FieldType.DATETIME,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            searchable=False,
            sortable=True,
            filterable=False,
            required=False,
            readonly=True,
            # NEW: View organization parameters
            tab_group="approval",
            section="workflow_status",
            view_order=3
        ),
        
        # Currency fields - exact names from your model
        FieldDefinition(
            name="currency_code",  # Exact field name
            label="Currency",
            field_type=FieldType.SELECT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=True,
            required=True,
            # NEW: View organization parameters
            tab_group="core",
            section="financial",
            view_order=2,
            options=[
                {"value": "INR", "label": "Indian Rupee (₹)"},
                {"value": "USD", "label": "US Dollar ($)"},
                {"value": "EUR", "label": "Euro (€)"}
            ]
        ),
        FieldDefinition(
            name="exchange_rate",  # Exact field name
            label="Exchange Rate",
            field_type=FieldType.NUMBER,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=False,
            sortable=False,
            filterable=False,
            required=False,
            help_text="Exchange rate if different from base currency"
        ),
        
        # Additional fields - exact names from your model
        FieldDefinition(
            name="notes",  # Exact field name
            label="Notes",
            field_type=FieldType.TEXTAREA,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            searchable=True,
            sortable=False,
            filterable=False,
            required=False,
            placeholder="Additional notes about this payment...",
            help_text="Optional notes about the payment"
        ),
        
        # Timestamp fields - from your TimestampMixin
        FieldDefinition(
            name="created_at",  # Exact field name
            label="Created Date",
            field_type=FieldType.DATETIME,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            searchable=False,
            sortable=True,
            filterable=False,
            required=False,
            readonly=True,
            # NEW: View organization parameters
            tab_group="system",
            section="audit_trail",
            view_order=1
        ),
        FieldDefinition(
            # Existing parameters
            name="created_by",
            label="Created By",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            readonly=True,
            
            # NEW: View organization parameters
            tab_group="system",
            section="audit_trail",
            view_order=2
        ),
        FieldDefinition(
            name="updated_at",  # Exact field name
            label="Last Updated",
            field_type=FieldType.DATETIME,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            searchable=False,
            sortable=True,
            filterable=False,
            required=False,
            readonly=True,
            # NEW: View organization parameters
            tab_group="system",
            section="audit_trail",
            view_order=3
        ),
        FieldDefinition(
            # Existing parameters
            name="updated_by",
            label="Updated By",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            readonly=True,
            
            # NEW: View organization parameters
            tab_group="system",
            section="audit_trail",
            view_order=4
        )
    ],
    
    actions=[
        ActionDefinition(
            id="create",
            label="Record Payment",
            icon="fas fa-plus",
            button_type=ButtonType.PRIMARY,
            route_name="supplier_views.create_payment",
            permission="supplier_payments_create",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True  # ✅ This makes it appear in toolbar
        ),
        ActionDefinition(
            id="view",
            label="View",
            icon="fas fa-eye",
            button_type=ButtonType.OUTLINE,
            route_name="universal_views.universal_detail_view",
            route_params={
                "entity_type": "supplier_payments", 
                "item_id": "{payment_id}"  # ✅ Explicit field mapping
            }, 
            permission="supplier_payments_view",
            show_in_list=True,
            show_in_detail=False
        ),
        ActionDefinition(
            id="edit",
            label="Edit",
            icon="fas fa-edit",
            button_type=ButtonType.WARNING,
            route_name="supplier_views.edit_payment",
            route_params={"payment_id": "{id}"}, 
            permission="supplier_payments_edit",
            show_in_list=True,
            show_in_detail=True
        ),
        ActionDefinition(
            id="duplicate",
            label="Duplicate",
            icon="fas fa-copy",
            button_type=ButtonType.OUTLINE,
            url_pattern="/universal/supplier_payments/duplicate/{id}",
            permission="supplier_payments_create",
            show_in_list=False,
            show_in_detail=True
        ),
        ActionDefinition(
            id="approve",
            label="Approve",
            icon="fas fa-check",
            button_type=ButtonType.SUCCESS,
            url_pattern="/universal/supplier_payments/approve/{id}",
            permission="supplier_payments_approve",
            confirmation_required=True,
            confirmation_message="Are you sure you want to approve this payment?",
            show_in_list=True,
            show_in_detail=True
        ),
        ActionDefinition(
            id="reject",
            label="Reject",
            icon="fas fa-times",
            button_type=ButtonType.DANGER,
            url_pattern="/universal/supplier_payments/reject/{id}",
            permission="supplier_payments_approve",
            confirmation_required=True,
            confirmation_message="Are you sure you want to reject this payment?",
            show_in_list=True,
            show_in_detail=True
        ),
        ActionDefinition(
            id="print",
            label="Print",
            icon="fas fa-print",
            button_type=ButtonType.OUTLINE,
            url_pattern="/universal/supplier_payments/print/{id}",
            permission="supplier_payments_view",
            show_in_list=False,
            show_in_detail=True
        ),
        ActionDefinition(
            id="purchase_orders",
            label="Purchase Orders", 
            icon="fas fa-file-contract",
            button_type=ButtonType.OUTLINE,
            route_name="supplier_views.purchase_order_list",
            permission="supplier_payments_view",
            show_in_list=False,
            show_in_detail=False, 
            show_in_toolbar=True  # ✅ Universal Engine principle
        ),

        ActionDefinition(
            id="invoices",
            label="Invoices",
            icon="fas fa-file-invoice", 
            button_type=ButtonType.OUTLINE,
            route_name="supplier_views.supplier_invoice_list", 
            permission="supplier_payments_view",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True  # ✅ Universal Engine principle
        ),

        ActionDefinition(
            id="suppliers", 
            label="Suppliers",
            icon="fas fa-users",
            button_type=ButtonType.OUTLINE,
            route_name="supplier_views.supplier_list", 
            permission="supplier_payments_view",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True  # ✅ Universal Engine principle
        )
    ],
    
    summary_cards=[
        {
            "id": "total_count",
            "field": "total_count",
            "label": "Total Transactions",
            "icon": "fas fa-receipt",
            "icon_css": "stat-card-icon primary",
            "type": "number",
            "filterable": True,  # ✅ Should update with filters
            "filter_field": "clear_filters",
            "filter_value": "all",
            "visible": True  # ✅ NEW: Control visibility
        },
        {
            "id": "total_amount",
            "field": "total_amount",
            "label": "Total Amount",
            "icon": "fas fa-rupee-sign",
            "icon_css": "stat-card-icon primary",
            "type": "currency",
            "filterable": True,
            "visible": True  # ✅ NEW: Control visibility
        },
        {
            "id": "pending_count",
            "field": "pending_count",
            "label": "Pending Approval",
            "icon": "fas fa-clock",
            "icon_css": "stat-card-icon warning",
            "type": "number",
            "filterable": True,
            "filter_field": "workflow_status",
            "filter_value": "pending",
            "visible": True  # ✅ NEW: Control visibility
        },
        {
            "id": "approved_count",
            "field": "approved_count", # ✅ Service needs to return this
            "label": "Approved",
            "icon": "fas fa-check-circle",
            "icon_css": "stat-card-icon success",
            "type": "number",
            "filterable": True,
            "filter_field": "workflow_status",
            "filter_value": "approved",
            "visible": True  # ✅ NEW: Control visibility
        },
        {
            "id": "completed_count",
            "field": "completed_count", # ✅ Service needs to return this
            "label": "Completed",
            "icon": "fas fa-check-double",
            "icon_css": "stat-card-icon success",
            "type": "number",
            "filterable": True,
            "filter_field": "workflow_status",
            "filter_value": "completed",
            "visible": True  # ✅ NEW: Control visibility
        },
        {
            "id": "this_month_count",
            "field": "this_month_count", # ✅ Service needs to return this
            "label": "This Month Transactions",  # ✅ NEW: Separate card
            "icon": "fas fa-calendar-check",
            "icon_css": "stat-card-icon info",
            "type": "number",
            "filterable": False,
            "filter_field": "date_preset",
            "filter_value": "this_month",
            "visible": True  # ✅ NEW: Control visibility
        },
        
        {
            "id": "this_month_amount",
            "field": "this_month_amount",  # ✅ Service needs to return this
            "label": "This Month Amount",  # ✅ NEW: Separate card for amount
            "icon": "fas fa-calendar-alt",
            "icon_css": "stat-card-icon success",
            "type": "currency",
            "filterable": False,
            "filter_field": "date_preset",
            "filter_value": "this_month",
            "visible": True  # ✅ NEW: Control visibility
        },

        {
            "id": "payment_breakdown",
            "field": "payment_method_breakdown",
            "label": "Payment Breakdown",
            "icon": "fas fa-chart-pie",
            "icon_css": "stat-card-icon info",
            "type": "currency",  # ✅ CHANGED: Use standard type for data formatting
            "card_type": "detail",  # ✅ NEW: Controls rendering style (summary/detail)
            "filterable": False,
            "visible": True,  # ✅ VISIBLE as requested
            "breakdown_fields": {  # ✅ NEW: Define breakdown structure
                "cash_amount": {
                    "label": "Cash",
                    "icon": "fas fa-money-bill-wave",
                    "color": "text-green-600"
                },
                "cheque_amount": {
                    "label": "Cheque", 
                    "icon": "fas fa-money-check",
                    "color": "text-blue-600"
                },
                "bank_amount": {
                    "label": "Bank",
                    "icon": "fas fa-university",
                    "color": "text-purple-600"
                },
                "upi_amount": {
                    "label": "UPI",
                    "icon": "fas fa-mobile-alt", 
                    "color": "text-orange-600"
                }
            }
        },
    

        {
            "id": "bank_transfer_count",
            "field": "bank_transfer_count",  # ✅ Service needs to return this
            "label": "Bank Transfers",
            "icon": "fas fa-university",
            "icon_css": "stat-card-icon primary",
            "type": "number",
            "filterable": True,
            "filter_field": "payment_method",
            "filter_value": "bank_transfer_inclusive",
            "visible": False  # ✅ NEW: Control visibility
        },
        {
            "id": "bank_transfer_amount",
            "field": "bank_transfer_amount_total",
            "label": "Bank Transfers",
            "icon": "fas fa-university",
            "icon_css": "stat-card-icon info",
            "type": "currency",
            "filterable": True,
            "filter_field": "payment_method",
            "filter_value": "bank_transfer",
            "visible": False  # ✅ NEW: Control visibility
        }
    ],
    
    permissions={
        "list": "supplier_payments_list",
        "view": "supplier_payments_view",
        "create": "supplier_payments_create",
        "edit": "supplier_payments_edit",
        "delete": "supplier_payments_delete",
        "approve": "supplier_payments_approve",
        "reject": "supplier_payments_approve",  # Same permission as approve
        "export": "supplier_payments_export",
        "bulk": "supplier_payments_bulk"
    },
     # ========== NEW: VIEW LAYOUT CONFIGURATION ==========
    view_layout=ViewLayoutConfiguration(
        type=LayoutType.TABBED,  # Can easily switch to SIMPLE or ACCORDION
        responsive_breakpoint='md',
        tabs=SUPPLIER_PAYMENT_TAB_DEFINITIONS,
        default_tab='core',
        sticky_tabs=True,
        auto_generate_sections=False,  # Use configured sections
        default_section_columns=2
    ),
    section_definitions=SUPPLIER_PAYMENT_SECTION_DEFINITIONS
)
# =============================================================================
# EASY LAYOUT SWITCHING (For testing different layouts)
# =============================================================================

def switch_layout_type(layout_type: str):
    """Easy function to switch between layout types"""
    if layout_type == 'simple':
        SUPPLIER_PAYMENT_CONFIG.view_layout.type = LayoutType.SIMPLE
    elif layout_type == 'tabbed':
        SUPPLIER_PAYMENT_CONFIG.view_layout.type = LayoutType.TABBED
    elif layout_type == 'accordion':
        SUPPLIER_PAYMENT_CONFIG.view_layout.type = LayoutType.ACCORDION
    
    print(f"🔄 Switched to {layout_type} layout")

# Usage examples:
# switch_layout_type('simple')      # Single column with sections
# switch_layout_type('tabbed')      # Multiple tabs with sections
# switch_layout_type('accordion')   # Collapsible sections

SUPPLIER_PAYMENT_FILTER_CATEGORY_MAPPING = {
    # Date category fields
    'start_date': FilterCategory.DATE,
    'end_date': FilterCategory.DATE,
    'payment_date': FilterCategory.DATE,
    'financial_year': FilterCategory.DATE,
    
    # Amount category fields
    'min_amount': FilterCategory.AMOUNT,
    'max_amount': FilterCategory.AMOUNT,
    'amount_min': FilterCategory.AMOUNT,
    'amount_max': FilterCategory.AMOUNT,
    'amount': FilterCategory.AMOUNT,
    
    # Search category fields
    'supplier_name_search': FilterCategory.SEARCH,
    'search': FilterCategory.SEARCH,
    'reference_no': FilterCategory.SEARCH,
    'invoice_id': FilterCategory.SEARCH,
    
    # Selection category fields
    'workflow_status': FilterCategory.SELECTION,  # ✅ Main field
    'statuses': FilterCategory.SELECTION,         # ✅ Alias
    'status': FilterCategory.SELECTION,           # ✅ Alias  
    'payment_method': FilterCategory.SELECTION,   # ✅ Main field
    'payment_methods': FilterCategory.SELECTION,  # ✅ Alias     
    
    # Relationship category fields
    'supplier_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP,
}

SUPPLIER_PAYMENT_DEFAULT_FILTERS = {
    'financial_year': 'current',
    'workflow_status': None,
}

SUPPLIER_PAYMENT_CATEGORY_CONFIGS = {
    FilterCategory.DATE: {
        'default_preset': 'current_financial_year',
        'auto_apply_financial_year': True
    },
    FilterCategory.AMOUNT: {
        'currency_symbol': '₹',
        'decimal_places': 2
    },
    FilterCategory.SEARCH: {
        'min_search_length': 2,
        'auto_submit': False
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
# EASY LAYOUT SWITCHING (For testing different layouts)
# =============================================================================

def switch_layout_type(layout_type: str):
    """Easy function to switch between layout types"""
    if layout_type == 'simple':
        SUPPLIER_PAYMENT_CONFIG.view_layout.type = LayoutType.SIMPLE
    elif layout_type == 'tabbed':
        SUPPLIER_PAYMENT_CONFIG.view_layout.type = LayoutType.TABBED
    elif layout_type == 'accordion':
        SUPPLIER_PAYMENT_CONFIG.view_layout.type = LayoutType.ACCORDION
    
    print(f"🔄 Switched to {layout_type} layout")

# Usage examples:
# switch_layout_type('simple')      # Single column with sections
# switch_layout_type('tabbed')      # Multiple tabs with sections
# switch_layout_type('accordion')   # Collapsible sections


# ✅ UNIVERSAL FIX: Ensure filter_category_mapping is properly set
if not SUPPLIER_PAYMENT_CONFIG.filter_category_mapping:
    SUPPLIER_PAYMENT_CONFIG.filter_category_mapping = {}
SUPPLIER_PAYMENT_CONFIG.filter_category_mapping.update(SUPPLIER_PAYMENT_FILTER_CATEGORY_MAPPING)
SUPPLIER_PAYMENT_CONFIG.default_filters = SUPPLIER_PAYMENT_DEFAULT_FILTERS  
SUPPLIER_PAYMENT_CONFIG.category_configs = SUPPLIER_PAYMENT_CATEGORY_CONFIGS
SUPPLIER_PAYMENT_CONFIG.model_class = 'app.models.transaction.SupplierPayment'
# ✅ PRIMARY DATE FIELD CONFIGURATION
SUPPLIER_PAYMENT_CONFIG.primary_date_field = "payment_date"

# ✅ PRIMARY AMOUNT FIELD CONFIGURATION
SUPPLIER_PAYMENT_CONFIG.primary_amount_field = "amount"



# =============================================================================
# SUPPLIER CONFIGURATION - Based on Your Supplier Model
# =============================================================================

SUPPLIER_CONFIG = EntityConfiguration(
    entity_type="suppliers",
    name="Supplier",
    plural_name="Suppliers",
    service_name="suppliers",
    table_name="suppliers",
    primary_key="supplier_id",
    title_field="supplier_name",
    subtitle_field="supplier_category",
    icon="fas fa-truck",
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,  # ✅ Manual filter application
    page_title="Supplier Management",
    description="Manage suppliers and vendors",
    searchable_fields=["supplier_name", "contact_person_name", "email"],
    default_sort_field="supplier_name",
    default_sort_direction="asc",
    model_class="app.models.master.Supplier",
    

    fields=[
        # System Fields
        FieldDefinition(
            name="supplier_id",
            label="Supplier ID",
            field_type=FieldType.UUID,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            readonly=True
        ),
        FieldDefinition(
            name="hospital_id",
            label="Hospital",
            field_type=FieldType.UUID,
            show_in_list=False,
            show_in_detail=False,
            show_in_form=False,
            required=True
        ),
        FieldDefinition(
            name="branch_id",
            label="Branch",
            field_type=FieldType.SELECT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            required=True,  # ✅ Not nullable in database
            autocomplete_enabled=True,
            autocomplete_source="backend"
        ),
        
        # Basic Information - CORRECTED field names
        FieldDefinition(
            name="supplier_name",  # ✅ Correct field name
            label="Supplier Name",
            field_type=FieldType.TEXT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=True,
            sortable=True,
            filterable=True,
            width="250px",
            required=True
        ),
        FieldDefinition(
            name="supplier_category",  # ✅ Correct field name
            label="Category",
            field_type=FieldType.SELECT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            sortable=True,
            options=[
                {"value": "medicine", "label": "Medicine"},
                {"value": "equipment", "label": "Equipment"},
                {"value": "consumable", "label": "Consumable"},
                {"value": "service", "label": "Service"}
            ]
        ),
        FieldDefinition(
            name="status",  # ✅ Correct field name
            label="Status",
            field_type=FieldType.SELECT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            sortable=True,
            required=True,
            default="active",
            options=[
                {"value": "active", "label": "Active"},
                {"value": "inactive", "label": "Inactive"}
            ],

        ),
        
        # Contact Information - CORRECTED
        FieldDefinition(
            name="contact_person_name",  # ✅ Correct field name
            label="Contact Person",
            field_type=FieldType.TEXT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=True,
            sortable=True
        ),
        FieldDefinition(
            name="email",  # ✅ Correct field name
            label="Email",
            field_type=FieldType.TEXT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=True,
            placeholder="email@example.com"
        ),
        FieldDefinition(
            name="phone",  # ✅ Virtual field - extracted from contact_info JSONB
            label="Phone",
            field_type=FieldType.TEXT,
            show_in_list=True,  # ✅ Show in list
            show_in_detail=False,  # Use contact_info for detail view
            show_in_form=False,  # Not directly editable
            searchable=False,  # Can't search JSONB extracted field easily
            sortable=False,  # Can't sort JSONB extracted field
            readonly=True,
            virtual=True,  # ✅ Indicates this is extracted, not a real column
            help_text="Extracted from contact information"
        ),
        # Note: Phone is in contact_info JSONB - will handle in service
        FieldDefinition(
            name="contact_info",  # ✅ JSONB field
            label="Contact Info",
            field_type=FieldType.JSONB,
            show_in_list=False,  # We'll extract phone for list display
            show_in_detail=True,
            show_in_form=True,
            help_text="Phone, Mobile, Fax information"
        ),
        
        # Tax Information
        FieldDefinition(
            name="gst_registration_number",  # ✅ Correct field name
            label="GST No.",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            placeholder="00AAAAA0000A0Z0"
        ),
        FieldDefinition(
            name="pan_number",  # ✅ Correct field name
            label="PAN",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            placeholder="AAAAA0000A"
        ),
        
        # Business Information
        FieldDefinition(
            name="payment_terms",  # ✅ Correct field name
            label="Payment Terms",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            help_text="e.g., Net 30 days"
        ),
        FieldDefinition(
            name="performance_rating",  # ✅ Correct field name
            label="Rating",
            field_type=FieldType.NUMBER,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            filterable=True
        ),
        FieldDefinition(
            name="black_listed",  # ✅ Correct field name (not blacklisted)
            label="Blacklisted",
            field_type=FieldType.BOOLEAN,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            default=False
        ),
        
        # Timestamps
        FieldDefinition(
            name="created_at",
            label="Created Date",
            field_type=FieldType.DATETIME,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            sortable=True,
            filterable=True,
            readonly=True
        ),
        FieldDefinition(
            name="updated_at",
            label="Last Updated",
            field_type=FieldType.DATETIME,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            sortable=True,
            readonly=True
        )
    ],
    
    # Summary Cards
    summary_cards=[
        {
            "id": "total_suppliers",
            "field": "total_count",  # ✅ Standard field from service
            "label": "Total Suppliers",
            "icon": "fas fa-truck",
            "icon_css": "stat-card-icon primary",
            "type": "number",
            "filterable": True,
            "filter_field": "clear_filters",  # Clear all filters when clicked
            "filter_value": "all"
        },
        {
            "id": "active_suppliers",
            "field": "active_count",  # ✅ Calculated in service
            "label": "Active Suppliers",
            "icon": "fas fa-check-circle",
            "icon_css": "stat-card-icon success",
            "type": "number",
            "filterable": True,
            "filter_field": "status",
            "filter_value": "active"
        },
        {
            "id": "medicine_suppliers",
            "field": "medicine_suppliers",  # ✅ Calculated in service
            "label": "Medicine Suppliers",
            "icon": "fas fa-pills",
            "icon_css": "stat-card-icon info",
            "type": "number",
            "filterable": True,
            "filter_field": "supplier_category",
            "filter_value": "medicine"
        },
        {
            "id": "blacklisted_suppliers",
            "field": "blacklisted_count",  # ✅ Calculated in service
            "label": "Blacklisted",
            "icon": "fas fa-ban",
            "icon_css": "stat-card-icon danger",
            "type": "number",
            "filterable": True,
            "filter_field": "black_listed",
            "filter_value": "true"
        }
    ],
    
    # Actions
    actions=[
        # Top toolbar buttons
        ActionDefinition(
            id="add_supplier",
            label="Add Supplier",
            icon="fas fa-plus",
            button_type=ButtonType.PRIMARY,
            # ✅ FIX: Use URL pattern instead of route_name for now
            url_pattern="/suppliers/create",  # Direct URL instead of route name
            permission="supplier_create",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True
        ),
        ActionDefinition(
            id="purchase_orders",
            label="Purchase Orders",
            icon="fas fa-file-contract",
            button_type=ButtonType.OUTLINE,
            route_name="supplier_views.purchase_order_list",
            permission="supplier_view",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True
        ),
        ActionDefinition(
            id="supplier_payments",
            label="Payments",
            icon="fas fa-money-bill",
            button_type=ButtonType.OUTLINE,
            route_name="supplier_views.payment_list",
            permission="supplier_view",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True
        ),
        ActionDefinition(
            id="invoices",
            label="Invoices",
            icon="fas fa-file-invoice",
            button_type=ButtonType.OUTLINE,
            route_name="supplier_views.supplier_invoice_list",
            permission="supplier_view",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True
        ),
        ActionDefinition(
            id="export",
            label="Export",
            icon="fas fa-download",
            button_type=ButtonType.OUTLINE,
            url_pattern="/universal/suppliers/export/csv",
            permission="supplier_view",
            show_in_list=False,
            show_in_detail=False,
            show_in_toolbar=True
        ),
        # Row-level actions
        ActionDefinition(
            id="view",
            label="View",
            icon="fas fa-eye",
            button_type=ButtonType.OUTLINE,
            route_name="supplier_views.view_supplier",
            route_params={"supplier_id": "{supplier_id}"},
            permission="supplier_view",
            show_in_list=True,
            show_in_detail=False,
            show_in_toolbar=False
        ),
        ActionDefinition(
            id="edit",
            label="Edit",
            icon="fas fa-edit",
            button_type=ButtonType.WARNING,
            route_name="supplier_views.edit_supplier",
            route_params={"supplier_id": "{supplier_id}"},
            permission="supplier_edit",
            show_in_list=True,
            show_in_detail=True,
            show_in_toolbar=False
        )
    ],

    
    # Permissions
    permissions={
        "list": "supplier_list",
        "view": "supplier_view",
        "create": "supplier_create",
        "edit": "supplier_edit",
        "delete": "supplier_delete",
        "export": "supplier_export"
    },


    
    # Add these after the permissions dict:
    filter_css_class="universal-filter-card",
    table_css_class="universal-data-table",
    
)

# Filter category mapping for suppliers
SUPPLIER_FILTER_CATEGORY_MAPPING = {
    # Date category fields
    # 'start_date': FilterCategory.DATE,     
    # 'end_date': FilterCategory.DATE,       
    'created_at': FilterCategory.DATE,
    'created_date': FilterCategory.DATE,
    
    # Selection category fields
    'status': FilterCategory.SELECTION,
    'supplier_category': FilterCategory.SELECTION,
    'black_listed': FilterCategory.SELECTION,
    
    # Search category fields
    'search': FilterCategory.SEARCH,
    'q': FilterCategory.SEARCH,
    'supplier_name': FilterCategory.SEARCH,
    
    # Amount category fields
    'performance_rating': FilterCategory.AMOUNT
}

# Default filters for suppliers
SUPPLIER_DEFAULT_FILTERS = {
    'status': 'active'
}

# Category configurations for suppliers
SUPPLIER_CATEGORY_CONFIGS = {
    FilterCategory.SELECTION: {
        'process_empty_as_all': True,
        'case_sensitive': False
    },
    FilterCategory.SEARCH: {
        'min_length': 2,
        'search_fields': ['supplier_name', 'contact_person_name', 'email'],
        'case_sensitive': False
    },
    FilterCategory.DATE: {
        'default_preset': None,
        'allow_range': True
    }
}

# Apply configurations to SUPPLIER_CONFIG
if not SUPPLIER_CONFIG.filter_category_mapping:
    SUPPLIER_CONFIG.filter_category_mapping = {}
SUPPLIER_CONFIG.filter_category_mapping.update(SUPPLIER_FILTER_CATEGORY_MAPPING)
SUPPLIER_CONFIG.default_filters = SUPPLIER_DEFAULT_FILTERS
SUPPLIER_CONFIG.category_configs = SUPPLIER_CATEGORY_CONFIGS
SUPPLIER_CONFIG.model_class = 'app.models.master.Supplier'
SUPPLIER_CONFIG.primary_date_field = "created_at"


# =============================================================================
# Entity Filter Configuration
# =============================================================================

# Entity filter configurations
ENTITY_FILTER_CONFIGS = {
    'supplier_payments': EntityFilterConfiguration(
        entity_type='supplier_payments',
        filter_mappings={
            'workflow_status': {
                'options': [
                    {'value': 'pending', 'label': 'Pending'},
                    {'value': 'approved', 'label': 'Approved'},
                    {'value': 'rejected', 'label': 'Rejected'},
                    {'value': 'completed', 'label': 'Completed'} 
                ]
            },
            'payment_method': {
                'options': [
                    {'value': 'cash', 'label': 'Cash'},
                    {'value': 'cheque', 'label': 'Cheque'},
                    {'value': 'bank_transfer', 'label': 'Bank Transfer'},
                    {'value': 'upi', 'label': 'UPI'}
                ]
            }
        }
    ),
    'suppliers': EntityFilterConfiguration(
        entity_type='suppliers',
        filter_mappings={
            'supplier_category': {
                'options': [
                    {'value': 'medicine', 'label': 'Medicine Supplier'},
                    {'value': 'equipment', 'label': 'Equipment Supplier'},
                    {'value': 'service', 'label': 'Service Provider'},
                    {'value': 'consumable', 'label': 'Consumable Supplier'}
                ]
            },
            'status': {
                'options': [
                    {'value': 'active', 'label': 'Active'},
                    {'value': 'inactive', 'label': 'Inactive'},
                    {'value': 'pending', 'label': 'Pending Approval'}
                ]
            },
            'black_listed': {
                'options': [
                    {'value': 'true', 'label': 'Yes'},
                    {'value': 'false', 'label': 'No'}
                ]
            },
            'tax_type': {
                'options': [
                    {'value': 'regular', 'label': 'Regular'},
                    {'value': 'composition', 'label': 'Composition'},
                    {'value': 'unregistered', 'label': 'Unregistered'}
                ]
            }
        }
    )
}

def get_entity_filter_config(entity_type: str) -> Optional[EntityFilterConfiguration]:
    """Get filter configuration for entity type"""
    return ENTITY_FILTER_CONFIGS.get(entity_type)

# Enhanced search configurations
ENTITY_SEARCH_CONFIGS = {
    'suppliers': EntitySearchConfiguration(
        target_entity='suppliers',
        search_fields=['supplier_name', 'contact_person_name'],
        display_template='{supplier_name}',
        model_path='app.models.master.Supplier',
        min_chars=2,
        max_results=10,
        sort_field='supplier_name',
        additional_filters={'status': 'active'}
    )
}

ENTITY_SEARCH_CONFIGS['supplier_payments'] = EntitySearchConfiguration(
    target_entity='supplier_payments',
    search_fields=['reference_no'],  # For reference number search
    display_template='{reference_no}',
    model_path='app.models.transaction.SupplierPayment',
    min_chars=1,
    max_results=10,
    sort_field='reference_no'
)

# =============================================================================
# ENTITY REGISTRY
# =============================================================================

ENTITY_CONFIGS = {
    "supplier_payments": SUPPLIER_PAYMENT_CONFIG,
    "suppliers": SUPPLIER_CONFIG,
    # Add more entities as you implement them
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_entity_config(entity_type: str) -> Optional[EntityConfiguration]:
    """Get entity configuration by type"""
    return ENTITY_CONFIGS.get(entity_type)

def is_valid_entity_type(entity_type: str) -> bool:
    """Check if entity type is valid and registered"""
    return entity_type in ENTITY_CONFIGS

def list_entity_types() -> List[str]:
    """Get list of all registered entity types"""
    return list(ENTITY_CONFIGS.keys())

def get_entity_permissions(entity_type: str) -> Dict[str, str]:
    """Get permission mapping for entity type"""
    config = get_entity_config(entity_type)
    return config.permissions if config else {}

def get_searchable_fields(entity_type: str) -> List[str]:
    """Get list of searchable fields for entity type"""
    config = get_entity_config(entity_type)
    return config.searchable_fields if config else []

def get_filterable_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of filterable fields for entity type"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.filterable]

def get_list_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of fields to show in list view"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.show_in_list]

def get_form_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of fields to show in forms"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.show_in_form]

def get_detail_fields(entity_type: str) -> List[FieldDefinition]:
    """Get list of fields to show in detail view"""
    config = get_entity_config(entity_type)
    if not config:
        return []
    return [field for field in config.fields if field.show_in_detail]

def get_field_by_name(entity_type: str, field_name: str) -> Optional[FieldDefinition]:
    """Get specific field definition by name"""
    config = get_entity_config(entity_type)
    if not config:
        return None
    return next((field for field in config.fields if field.name == field_name), None)


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_entity_config(config: EntityConfiguration) -> List[str]:
    """Validate entity configuration and return list of errors"""
    errors = []
    
    # Check required fields
    if not config.entity_type:
        errors.append("entity_type is required")
    if not config.primary_key:
        errors.append("primary_key is required")
    if not config.fields:
        errors.append("fields list cannot be empty")
    
    # Check primary key exists in fields
    primary_key_found = any(field.name == config.primary_key for field in config.fields)
    if not primary_key_found:
        errors.append(f"primary_key '{config.primary_key}' not found in fields")
    
    # Check title field exists in fields
    title_field_found = any(field.name == config.title_field for field in config.fields)
    if not title_field_found:
        errors.append(f"title_field '{config.title_field}' not found in fields")
    
    # Validate field names are unique
    field_names = [field.name for field in config.fields]
    if len(field_names) != len(set(field_names)):
        errors.append("Duplicate field names found")
    
    # Validate action IDs are unique
    action_ids = [action.id for action in config.actions]
    if len(action_ids) != len(set(action_ids)):
        errors.append("Duplicate action IDs found")
    
    # Validate searchable fields exist
    for search_field in config.searchable_fields:
        if not any(field.name == search_field for field in config.fields):
            errors.append(f"Searchable field '{search_field}' not found in fields")
    
    return errors

def validate_all_configs():
    """Validate all registered entity configurations"""
    print("\n🔍 Validating Entity Configurations...")
    print("=" * 50)
    
    all_valid = True
    for entity_type, config in ENTITY_CONFIGS.items():
        errors = validate_entity_config(config)
        if errors:
            print(f"❌ Configuration errors for {entity_type}:")
            for error in errors:
                print(f"   - {error}")
            all_valid = False
        else:
            print(f"✅ Configuration valid for {entity_type}")
    
    if all_valid:
        print(f"\n🎉 All {len(ENTITY_CONFIGS)} entity configurations are valid!")
    else:
        print(f"\n⚠️  Some configurations have errors - please fix before proceeding")
    
    return all_valid

# =============================================================================
# FIELD NAME MAPPING FOR YOUR EXISTING SERVICES
# =============================================================================

# Map filter names from universal engine to your service's expected format
FILTER_MAPPING = {
    "supplier_payments": {
        "workflow_status": "statuses",  # Your service expects 'statuses' list
        "payment_method": "payment_methods",  # Your service expects 'payment_methods' list
        "supplier_id": "supplier_id",  # Direct mapping
        "start_date": "start_date",  # Direct mapping
        "end_date": "end_date",  # Direct mapping
        "search": "search",  # Direct mapping
        "reference_no": "reference_no",  # Direct mapping
        "amount": "amount",  # Direct mapping
    }
}

def get_service_filter_mapping(entity_type: str) -> Dict[str, str]:
    """Get filter name mapping for service compatibility"""
    return FILTER_MAPPING.get(entity_type, {})

# Run validation when module is imported
if __name__ == "__main__":
    validate_all_configs()