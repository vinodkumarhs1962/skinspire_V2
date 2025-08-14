# Master Entities Configuration Module
# File: app/config/modules/master_entities.py

"""
Master Entities Configuration Module
Contains configurations for suppliers, patients, users, etc.
Fully compatible with Universal Engine v2.0
Fixed structure to match financial_transactions.py pattern
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition, 
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration, ButtonType,
    ComplexDisplayType, ActionDisplayType,
    DocumentConfiguration, PrintLayoutType, DocumentType,
    PageSize, Orientation, DocumentSectionType, ExportFormat,
    CustomRenderer  # Added for transaction history custom rendering
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# SUPPLIER FIELD DEFINITIONS (Aligned with database model)
# =============================================================================

SUPPLIER_FIELDS = [
    # ========== PRIMARY KEY ==========
    FieldDefinition(
        name="supplier_id",
        label="Supplier ID", 
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="profile",  # Changed from basic_info
        section="identification",
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
        required=True,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        tab_group="profile",  # Changed from basic_info
        section="identification",
        view_order=1
    ),
    
    # ========== BASIC INFORMATION ==========
    FieldDefinition(
        name="supplier_name",
        label="Supplier Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        filterable=True,
        required=True,
        placeholder="Enter supplier name",
        tab_group="profile",  # Changed from basic_info
        section="identification",
        view_order=2,
        css_classes="text-lg font-bold"
    ),
    FieldDefinition(
        name="supplier_category",
        label="Category",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        sortable=True,
        required=True,
        options=[
            {"value": "medicine", "label": "Medicine Supplier"},
            {"value": "equipment", "label": "Equipment Supplier"},
            {"value": "service", "label": "Service Provider"},
            {"value": "consumable", "label": "Consumable Supplier"}
        ],
        tab_group="business_info",
        section="business_details",
        view_order=1
    ),
    
    # ========== CONTACT INFORMATION ==========
    FieldDefinition(
        name="contact_person_name",
        label="Contact Person",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        placeholder="Enter contact person name",
        tab_group="profile",  # Changed from contact_info
        section="primary_contact",
        view_order=1
    ),
    FieldDefinition(
        name="contact_info",
        label="Contact Information",
        field_type=FieldType.JSONB,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="profile",  # Changed from contact_info
        section="primary_contact",
        view_order=2
    ),
    FieldDefinition(
        name="phone",  # Virtual field - extracted from contact_info JSONB
        label="Phone",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        virtual=True,
        placeholder="Enter phone number",
        tab_group="profile",  # Changed from contact_info
        section="primary_contact",
        view_order=3
    ),
    FieldDefinition(
        name="email",
        label="Email",
        field_type=FieldType.EMAIL,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        placeholder="Enter email address",
        validation_pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        tab_group="profile",  # <- MISSING!
        section="primary_contact",  # <- MISSING!
        view_order=4  # <- MISSING!
        ),
    FieldDefinition(
        name="manager_name",
        label="Manager Name",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="profile",
        section="secondary_contact",
        view_order=1
    ),
    FieldDefinition(
        name="manager_contact_info",
        label="Manager Contact",
        field_type=FieldType.JSONB,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="profile",
        section="secondary_contact",
        view_order=2
    ),
    FieldDefinition(
        name="supplier_address",
        label="Address",
        field_type=FieldType.JSONB,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="profile",
        section="address",
        view_order=1
    ),
    # ========== TAX INFORMATION ==========
    FieldDefinition(
        name="gst_registration_number",
        label="GSTIN",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        filterable=True,
        placeholder="Enter GST registration number",
        validation_pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
        tab_group="business_info",
        section="tax_details",
        view_order=1
    ),
    FieldDefinition(
        name="pan_number",
        label="PAN Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        placeholder="Enter PAN number",
        validation_pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
        tab_group="business_info",
        section="tax_details",
        view_order=2
    ),
    FieldDefinition(
        name="tax_type",
        label="Tax Type",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        options=[
            {"value": "regular", "label": "Regular"},
            {"value": "composition", "label": "Composition"},
            {"value": "unregistered", "label": "Unregistered"}
        ],
        tab_group="business_info",
        section="tax_details",
        view_order=3
    ),
    FieldDefinition(
        name="state_code",
        label="State Code",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        placeholder="Enter state code",
        validation_pattern=r'^[0-9]{2}$',
        tab_group="business_info",
        section="tax_details",
        view_order=4
    ),
    
    # ========== PAYMENT & BANKING ==========
    FieldDefinition(
        name="payment_terms",
        label="Payment Terms",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        options=[
            {"value": "immediate", "label": "Immediate"},
            {"value": "7_days", "label": "7 Days"},
            {"value": "15_days", "label": "15 Days"},
            {"value": "30_days", "label": "30 Days"},
            {"value": "45_days", "label": "45 Days"},
            {"value": "60_days", "label": "60 Days"},
            {"value": "90_days", "label": "90 Days"}
        ],
        tab_group="business_info",
        section="payment_info",
        view_order=1
    ),
    FieldDefinition(
        name="bank_details",
        label="Bank Details",
        field_type=FieldType.JSONB,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="business_info",
        section="bank_details",
        view_order=1
    ),
    
    # ========== COMPLIANCE & STATUS ==========
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        sortable=True,
        required=True,
        options=[
            {"value": "active", "label": "Active"},
            {"value": "inactive", "label": "Inactive"},
            {"value": "pending", "label": "Pending Approval"}
        ],
        default_value="active",
        tab_group="profile",  # Changed from basic_info
        section="status",
        view_order=1,
        css_classes="status-badge"
    ),
    FieldDefinition(
        name="black_listed",
        label="Blacklisted",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        default_value=False,
        tab_group="business_info",
        section="compliance",
        view_order=1
    ),
    FieldDefinition(
        name="performance_rating",
        label="Performance Rating",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        min_value=1,
        max_value=5,
        placeholder="1-5 rating",
        tab_group="business_info",
        section="performance",
        view_order=1
    ),
    
    # ========== ADDITIONAL INFORMATION ==========
    FieldDefinition(
        name="remarks",
        label="Remarks",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        placeholder="Enter any remarks or notes",
        tab_group="business_info",  # Changed from additional_info
        section="notes",
        view_order=1
    ),
    
    # ========== AUDIT FIELDS (from TimestampMixin) ==========
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
        section="audit",
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
        section="audit",
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
        section="audit",
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
        section="audit",
        view_order=4
    ),
    
    # ========== VIRTUAL/CALCULATED FIELDS ==========
    FieldDefinition(
        name="total_purchases",
        label="Total Purchases",
        field_type=FieldType.DECIMAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="business_info",
        section="statistics",
        view_order=1
    ),
    FieldDefinition(
        name="outstanding_balance",
        label="Outstanding Balance",
        field_type=FieldType.DECIMAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="business_info",
        section="statistics",
        view_order=2
    ),
    
    # ========== TRANSACTION HISTORY FIELDS (Virtual) ==========
    # Reuse existing payment history component from financial_transactions.py
    FieldDefinition(
        name="supplier_payment_history",
        label="Payment History",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="transaction_history",
        section="payment_history",
        view_order=1,
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_supplier_payment_history_6months",
            css_classes="payment-history-table"
        )
    ),
    
    # Reuse invoice items display from financial_transactions.py
    FieldDefinition(
        name="supplier_invoice_history",
        label="Invoice History",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="transaction_history",
        section="invoice_history",
        view_order=1,
        custom_renderer=CustomRenderer(
            template="components/business/invoice_items_table.html",
            context_function="get_supplier_invoice_history",
            css_classes="table-responsive invoice-items-table"
        )
    ),
    
    # Balance summary fields
    FieldDefinition(
        name="current_balance",
        label="Current Balance",
        field_type=FieldType.DECIMAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="transaction_history",
        section="balance_summary",
        view_order=1,
        css_classes="text-xl font-bold text-danger"
    ),
    FieldDefinition(
        name="total_invoiced",
        label="Total Invoiced Amount",
        field_type=FieldType.DECIMAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="transaction_history",
        section="balance_summary",
        view_order=2
    ),
    FieldDefinition(
        name="total_paid",
        label="Total Paid Amount",
        field_type=FieldType.DECIMAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="transaction_history",
        section="balance_summary",
        view_order=3,
        css_classes="text-success"
    ),
    FieldDefinition(
        name="last_payment_date",
        label="Last Payment Date",
        field_type=FieldType.DATE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        virtual=True,
        readonly=True,
        tab_group="transaction_history",
        section="balance_summary",
        view_order=4
    )
]

# =============================================================================
# SECTION DEFINITIONS (Dictionary format like financial_transactions.py)
# =============================================================================

SUPPLIER_SECTIONS = {
    'identification': SectionDefinition(
        key='identification',
        title='Identification',
        icon='fas fa-id-card',
        columns=2,
        order=0
    ),
    'status': SectionDefinition(
        key='status',
        title='Status',
        icon='fas fa-toggle-on',
        columns=1,
        order=1
    ),
    'primary_contact': SectionDefinition(
        key='primary_contact',
        title='Primary Contact',
        icon='fas fa-user',
        columns=2,
        order=0
    ),
    'secondary_contact': SectionDefinition(
        key='secondary_contact',
        title='Secondary Contact',
        icon='fas fa-user-friends',
        columns=2,
        order=1
    ),
    'address': SectionDefinition(
        key='address',
        title='Address',
        icon='fas fa-map-marker-alt',
        columns=2,
        order=2
    ),
    'business_details': SectionDefinition(
        key='business_details',
        title='Business Details',
        icon='fas fa-building',
        columns=2,
        order=0
    ),
    'tax_details': SectionDefinition(
        key='tax_details',
        title='Tax Information',
        icon='fas fa-percent',
        columns=2,
        order=1
    ),
    'payment_info': SectionDefinition(
        key='payment_info',
        title='Payment Information',
        icon='fas fa-credit-card',
        columns=2,
        order=2
    ),
    'bank_details': SectionDefinition(
        key='bank_details',
        title='Bank Details',
        icon='fas fa-university',
        columns=2,
        order=3
    ),
    'compliance': SectionDefinition(
        key='compliance',
        title='Compliance',
        icon='fas fa-clipboard-check',
        columns=2,
        order=4
    ),
    'performance': SectionDefinition(
        key='performance',
        title='Performance',
        icon='fas fa-chart-line',
        columns=2,
        order=5
    ),
    'statistics': SectionDefinition(
        key='statistics',
        title='Statistics',
        icon='fas fa-chart-bar',
        columns=2,
        order=6
    ),
    'notes': SectionDefinition(
        key='notes',
        title='Notes & Remarks',
        icon='fas fa-sticky-note',
        columns=1,
        order=7  # Now under business_info
    ),
    'payment_history': SectionDefinition(
        key='payment_history',
        title='Last 6 Months Payment History',
        icon='fas fa-clock',
        columns=1,  # Full width for table
        order=0
    ),
    'invoice_history': SectionDefinition(
        key='invoice_history',
        title='Recent Supplier Invoices',
        icon='fas fa-file-invoice',
        columns=1,  # Full width for table
        order=1
    ),
    'balance_summary': SectionDefinition(
        key='balance_summary',
        title='Balance Summary',
        icon='fas fa-balance-scale',
        columns=2,
        order=2
    ),
    'technical': SectionDefinition(
        key='technical',
        title='Technical Details',
        icon='fas fa-server',
        columns=2,
        order=0
    ),
    'audit': SectionDefinition(
        key='audit',
        title='Audit Trail',
        icon='fas fa-history',
        columns=2,
        order=1
    )
}

# =============================================================================
# TAB DEFINITIONS (Dictionary format like financial_transactions.py)
# =============================================================================

SUPPLIER_TABS = {
    'profile': TabDefinition(
        key='profile',  # CRITICAL: This key must match exactly
        label='Profile',
        icon='fas fa-user-circle',
        sections={
            'identification': SUPPLIER_SECTIONS['identification'],
            'status': SUPPLIER_SECTIONS['status'],
            'primary_contact': SUPPLIER_SECTIONS['primary_contact'],
            'secondary_contact': SUPPLIER_SECTIONS['secondary_contact'],
            'address': SUPPLIER_SECTIONS['address']
        },
        order=0,
        default_active=True  # This tab will be active by default
    ),
    'business_info': TabDefinition(
        key='business_info',  # CRITICAL: This key must match exactly
        label='Business Information',
        icon='fas fa-briefcase',
        sections={
            'business_details': SUPPLIER_SECTIONS['business_details'],
            'tax_details': SUPPLIER_SECTIONS['tax_details'],
            'payment_info': SUPPLIER_SECTIONS['payment_info'],
            'bank_details': SUPPLIER_SECTIONS['bank_details'],
            'compliance': SUPPLIER_SECTIONS['compliance'],
            'performance': SUPPLIER_SECTIONS['performance'],
            'statistics': SUPPLIER_SECTIONS['statistics'],
            'notes': SUPPLIER_SECTIONS['notes']
        },
        order=1
    ),
    'transaction_history': TabDefinition(
        key='transaction_history',  # CRITICAL: This key must match exactly
        label='Transaction History',
        icon='fas fa-history',
        sections={
            'payment_history': SUPPLIER_SECTIONS['payment_history'],
            'invoice_history': SUPPLIER_SECTIONS['invoice_history'],
            'balance_summary': SUPPLIER_SECTIONS['balance_summary']
        },
        order=2
    ),
    'system_info': TabDefinition(
        key='system_info',  # CRITICAL: This key must match exactly
        label='System Information',
        icon='fas fa-cogs',
        sections={
            'technical': SUPPLIER_SECTIONS['technical'],
            'audit': SUPPLIER_SECTIONS['audit']
        },
        order=3
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

SUPPLIER_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    responsive_breakpoint='md',
    tabs=SUPPLIER_TABS,
    default_tab='profile',  # CRITICAL: Must match one of the tab keys above
    sticky_tabs=False,
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "supplier_id",
        "primary_label": "Supplier ID",
        "title_field": "supplier_name",
        "title_label": "Supplier",
        "status_field": "status",
        "secondary_fields": [
            {"field": "supplier_category", "label": "Category", "icon": "fas fa-tag"},
            {"field": "contact_person_name", "label": "Contact Person", "icon": "fas fa-user"},
            {"field": "phone", "label": "Phone", "icon": "fas fa-phone"},
            {"field": "email", "label": "Email", "icon": "fas fa-envelope"}
        ]
    }
)

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

SUPPLIER_ACTIONS = [
    ActionDefinition(
        id="create",
        label="New Supplier",
        icon="fas fa-plus",
        url_pattern="/universal/{entity_type}/create",
        button_type=ButtonType.PRIMARY,
        permission="suppliers_create",
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
        route_params={"entity_type": "suppliers", "item_id": "{supplier_id}"},
        button_type=ButtonType.INFO,
        permission="suppliers_view",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=10
    ),
    # FIXED: Edit action uses universal route pattern
    ActionDefinition(
        id="edit",
        label="Edit Supplier",
        icon="fas fa-edit",
        route_name="universal_views.universal_edit_view",
        route_params={"entity_type": "suppliers", "item_id": "{supplier_id}"},
        button_type=ButtonType.PRIMARY,
        permission="suppliers_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,  # FIXED: Changed to dropdown
        order=20
    ),
    # FIXED: Add print/document actions
    ActionDefinition(
        id="print",
        label="Print Profile",
        icon="fas fa-print",
        route_name="universal_views.universal_document_view",
        route_params={
            "entity_type": "suppliers",
            "item_id": "{supplier_id}",
            "doc_type": "profile"
        },
        button_type=ButtonType.SECONDARY,
        permission="suppliers_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        button_group="document_ops",
        order=30
    ),
    # FIXED: Add export action
    ActionDefinition(
        id="export",
        label="Export Data",
        icon="fas fa-download",
        route_name="universal_views.universal_export_view",
        route_params={"entity_type": "suppliers", "item_id": "{supplier_id}"},
        button_type=ButtonType.INFO,
        permission="suppliers_export",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=40
    ),
    # FIXED: Add payment history action
    ActionDefinition(
        id="payment_history",
        label="Payment History",
        icon="fas fa-history",
        route_name="universal_views.universal_detail_view",
        route_params={
            "entity_type": "suppliers", 
            "item_id": "{supplier_id}",
            "tab": "transaction_history"
        },
        button_type=ButtonType.INFO,
        permission="suppliers_view",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=50
    ),
    # FIXED: Delete action uses universal API pattern
    ActionDefinition(
        id="delete",
        label="Delete Supplier",
        icon="fas fa-trash",
        url_pattern="/api/universal/{entity_type}/{item_id}/delete",
        button_type=ButtonType.DANGER,
        permission="suppliers_delete",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=100,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this supplier? This action cannot be undone.",
        conditions={
            "status": ["inactive", "draft"]  # Only allow deletion of inactive suppliers
        }
    ),
    # FIXED: Add deactivate action (safer than delete)
    ActionDefinition(
        id="deactivate",
        label="Deactivate",
        icon="fas fa-pause",
        url_pattern="/api/universal/{entity_type}/{item_id}/deactivate",
        button_type=ButtonType.WARNING,
        permission="suppliers_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=90,
        confirmation_required=True,
        confirmation_message="Are you sure you want to deactivate this supplier?",
        conditions={
            "status": ["active"]  # Only show for active suppliers
        }
    ),
    # FIXED: Add activate action
    ActionDefinition(
        id="activate",
        label="Activate",
        icon="fas fa-play",
        url_pattern="/api/universal/{entity_type}/{item_id}/activate",
        button_type=ButtonType.SUCCESS,
        permission="suppliers_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=95,
        confirmation_required=True,
        confirmation_message="Are you sure you want to activate this supplier?",
        conditions={
            "status": ["inactive"]  # Only show for inactive suppliers
        }
    )
]

# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

SUPPLIER_SUMMARY_CARDS = [
    {
        "id": "total_suppliers",
        "label": "Total Suppliers",
        "icon": "fas fa-truck",
        "field": "total_count",
        "type": "number",
        "icon_css": "stat-card-icon primary",
        "filterable": True,
        "visible": True,
        "order": 1
    },
    {
        "id": "active_suppliers",
        "label": "Active Suppliers",
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
        "id": "medicine_suppliers",
        "label": "Medicine Suppliers",
        "icon": "fas fa-pills",
        "field": "medicine_suppliers",
        "type": "number",
        "icon_css": "stat-card-icon info",
        "filterable": True,
        "filter_field": "supplier_category",
        "filter_value": "medicine",
        "visible": True,
        "order": 3
    },
    {
        "id": "blacklisted",
        "label": "Blacklisted",
        "icon": "fas fa-ban",
        "field": "blacklisted_count",
        "type": "number",
        "icon_css": "stat-card-icon danger",
        "filterable": True,
        "filter_field": "black_listed",
        "filter_value": "true",
        "visible": True,
        "order": 4
    }
]

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

SUPPLIER_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'created_from': FilterCategory.DATE,
    'created_to': FilterCategory.DATE,
    'modified_from': FilterCategory.DATE,
    'modified_to': FilterCategory.DATE,
    
    # Selection filters
    'status': FilterCategory.SELECTION,
    'supplier_category': FilterCategory.SELECTION,
    'black_listed': FilterCategory.SELECTION,
    'tax_type': FilterCategory.SELECTION,
    'payment_terms': FilterCategory.SELECTION,
    
    # Search filters
    'search': FilterCategory.SEARCH,
    'q': FilterCategory.SEARCH,
    'supplier_name': FilterCategory.SEARCH,
    'contact_person_name': FilterCategory.SEARCH,
    'email': FilterCategory.SEARCH,
    'gst_registration_number': FilterCategory.SEARCH,
    
    # Amount/Number filters
    'performance_rating': FilterCategory.AMOUNT,
    
    # Relationship filters
    'supplier_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP
}

SUPPLIER_DEFAULT_FILTERS = {
    'status': 'active'
}

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

SUPPLIER_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
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
        },
        'payment_terms': {
            'options': [
                {'value': 'immediate', 'label': 'Immediate'},
                {'value': '7_days', 'label': '7 Days'},
                {'value': '15_days', 'label': '15 Days'},
                {'value': '30_days', 'label': '30 Days'},
                {'value': '45_days', 'label': '45 Days'},
                {'value': '60_days', 'label': '60 Days'},
                {'value': '90_days', 'label': '90 Days'}
            ]
        }
    }
)

# =============================================================================
# SEARCH CONFIGURATION
# =============================================================================

SUPPLIER_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='suppliers',
    search_fields=['supplier_name', 'contact_person_name'],
    display_template='{supplier_name}',
    model_path='app.models.master.Supplier',
    min_chars=1,
    max_results=10,
    sort_field='supplier_name',
    additional_filters={'status': 'active'}
)

# =============================================================================
# PERMISSIONS CONFIGURATION
# =============================================================================

SUPPLIER_PERMISSIONS = {
    "list": "suppliers_list",
    "view": "suppliers_view", 
    "create": "suppliers_create",
    "edit": "suppliers_edit",
    "delete": "suppliers_delete",
    "export": "suppliers_export",
    "bulk": "suppliers_bulk",
    "view_financial": "suppliers_view_financial"
}

# =============================================================================
# DOCUMENT CONFIGURATIONS
# =============================================================================

# Supplier Profile Document
SUPPLIER_PROFILE_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.REPORT,
    title="Supplier Profile",
    page_size=PageSize.A4,
    orientation=Orientation.PORTRAIT,
    print_layout_type=PrintLayoutType.SIMPLE_WITH_HEADER,
    show_logo=True,
    show_company_info=True,
    header_text="SUPPLIER MASTER PROFILE",
    visible_tabs=["profile", "business_info"],  # CORRECT TAB NAMES
    hidden_sections=["transaction_history"],  # Remove or update as needed
    signature_fields=[
        {"label": "Verified By", "width": "200px"},
        {"label": "Approved By", "width": "200px"}
    ],
    show_footer=True,
    footer_text="This is a system generated document",
    show_print_info=True,
    # ✅ FIXED: Use string values like financial_transactions.py, not enum values
    allowed_formats=["pdf", "print", "excel", "word"]  # Changed from [ExportFormat.PDF, ...]
)

# Supplier Statement Document
SUPPLIER_STATEMENT_CONFIG = DocumentConfiguration(
    enabled=True,
    document_type=DocumentType.STATEMENT,
    title="Supplier Statement",
    page_size=PageSize.A4,
    orientation=Orientation.LANDSCAPE,
    print_layout_type=PrintLayoutType.SIMPLE,
    show_logo=True,
    show_company_info=True,
    header_text="SUPPLIER ACCOUNT STATEMENT",
    visible_tabs=["transaction_history"],
    show_footer=True,
    footer_text="Statement Period: {from_date} to {to_date}",
    # ✅ FIXED: Use string values for allowed_formats
    allowed_formats=["pdf", "print", "excel", "word"]  # Changed from [ExportFormat.PDF, ...]
)

SUPPLIER_DOCUMENT_CONFIGS = {
    "profile": SUPPLIER_PROFILE_CONFIG,
    "statement": SUPPLIER_STATEMENT_CONFIG
}

# =============================================================================
# COMPLETE SUPPLIER CONFIGURATION
# =============================================================================

SUPPLIER_CONFIG = EntityConfiguration(
    # ========== BASIC INFORMATION (REQUIRED) ==========
    entity_type="suppliers",
    name="Supplier",
    plural_name="Suppliers",
    service_name="suppliers",
    table_name="suppliers",
    primary_key="supplier_id",
    title_field="supplier_name",
    subtitle_field="supplier_category",
    icon="fas fa-truck",
    page_title="Supplier Management",
    description="Manage suppliers and vendors",
    searchable_fields=["supplier_name", "contact_person_name", "email"],
    default_sort_field="supplier_name",
    default_sort_direction="asc",
    
    # ========== CORE CONFIGURATIONS ==========
    fields=SUPPLIER_FIELDS,
    actions=SUPPLIER_ACTIONS,
    summary_cards=SUPPLIER_SUMMARY_CARDS,
    permissions=SUPPLIER_PERMISSIONS,
    
    # ========== OPTIONAL CONFIGURATIONS ==========
    model_class="app.models.master.Supplier",
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    
    # View Layout Configuration
    view_layout=SUPPLIER_VIEW_LAYOUT,
    section_definitions=SUPPLIER_SECTIONS,
    
    # Filter Configuration
    filter_category_mapping=SUPPLIER_FILTER_CATEGORY_MAPPING,
    default_filters=SUPPLIER_DEFAULT_FILTERS,
    category_configs=SUPPLIER_CATEGORY_CONFIGS,
    
    # Date and Amount Fields
    primary_date_field="created_at",
    primary_amount_field=None,  # Suppliers don't have a primary amount field
    
    # Document Generation Support
    document_enabled=True,
    document_configs=SUPPLIER_DOCUMENT_CONFIGS,
    default_document="profile",
    
    # Calculated fields for documents
    include_calculated_fields=[
        "total_purchases",
        "outstanding_balance",
        "supplier_payment_history",
        "supplier_invoice_history",
        "current_balance",
        "total_invoiced",
        "total_paid",
        "last_payment_date"
    ],
    
    # Document permissions
    document_permissions={
        "profile": "suppliers_view",
        "statement": "suppliers_view_financial"
    }
)

# =============================================================================
# MODULE REGISTRY
# =============================================================================

MASTER_ENTITY_CONFIGS = {
    "suppliers": SUPPLIER_CONFIG
    # Future: Add patients, users, etc.
}

# Entity filter configs for module
MASTER_ENTITY_FILTER_CONFIGS = {
    "suppliers": SUPPLIER_ENTITY_FILTER_CONFIG
    # Future: Add other entity filters
}

# Entity search configs for module
MASTER_ENTITY_SEARCH_CONFIGS = {
    "suppliers": SUPPLIER_SEARCH_CONFIG
    # Future: Add other entity searches
}

# =============================================================================
# MODULE EXPORT FUNCTIONS
# =============================================================================

def get_module_configs():
    """Return all configurations from this module"""
    return MASTER_ENTITY_CONFIGS

def get_module_filter_configs():
    """Return all filter configurations from this module"""
    return MASTER_ENTITY_FILTER_CONFIGS

def get_module_search_configs():
    """Return all search configurations from this module"""
    return MASTER_ENTITY_SEARCH_CONFIGS