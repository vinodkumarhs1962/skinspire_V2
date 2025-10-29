"""
Supplier Invoice Configuration for Universal Engine
File: app/config/modules/supplier_invoice_config.py

Complete configuration leveraging Universal Engine v5.0 capabilities
Transaction entity - read-only operations in Universal Engine
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
    DocumentFieldMapping, TableColumnConfig, DocumentSection, PrintLayoutType, FilterType
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# SUPPLIER INVOICE FIELD DEFINITIONS
# =============================================================================

SUPPLIER_INVOICE_FIELDS = [
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
        name="supplier_invoice_number",
        label="Invoice Number",
        field_type=FieldType.TEXT,
        required=True,
        searchable=True,
        sortable=True,
        filterable=True,
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
        format_pattern="%d-%b-%Y",  # dd-mmm-yyyy format
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
    
    FieldDefinition(
        name="due_date",
        label="Due Date",
        field_type=FieldType.DATE,
        sortable=True,
        filterable=True,
        filter_operator=FilterOperator.DATE_ON_OR_BEFORE,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="dates",
        view_order=3
    ),
    
    # === SUPPLIER RELATIONSHIP ===
    FieldDefinition(
        name="supplier_id",
        label="Supplier",
        field_type=FieldType.ENTITY_SEARCH,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=True,
        required=True,
        filterable=False,
        tab_group="invoice_details",
        section="supplier_info",
        view_order=10,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        autocomplete_min_chars=2,
        entity_search_config=EntitySearchConfiguration(
            target_entity='suppliers',
            display_template='{supplier_name}',  # ✅ Use only existing fields
            search_fields=['supplier_name', 'contact_person_name'],  # ✅ Actual fields
            min_chars=2,
            value_field='supplier_id',
            placeholder="Type to search suppliers...",
            preload_common=True,
            cache_results=True
        )
    ),
    
    FieldDefinition(
        name="supplier_name",
        label="Supplier",  # Simplified label
        field_type=FieldType.TEXT,
        
        # === DISPLAY PROPERTIES ===
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        readonly=True,
        
        # === SEARCH PROPERTIES ===
        searchable=True,
        
        # === FILTER PROPERTIES (FIXED) ===
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,
        filter_operator=FilterOperator.CONTAINS,  # Changed to CONTAINS for name search
        entity_search_config=EntitySearchConfiguration(
            target_entity='suppliers',
            search_fields=['supplier_name', 'contact_person_name'],
            display_template='{supplier_name}',
            value_field='supplier_name',      # Use name as value
            filter_field='supplier_name',        # FIX: Filter by supplier_name field
            placeholder="Type to search suppliers...",
            preload_common=True,
            cache_results=True
        ),
        
        # === LAYOUT PROPERTIES ===
        tab_group="invoice_details",
        section="supplier_info",
        view_order=11,
        css_classes="supplier-column",
        complex_display_type=ComplexDisplayType.ENTITY_REFERENCE
    ),

    
    FieldDefinition(
        name="supplier_category",
        label="Category",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="supplier_info",
        view_order=12
    ),
    
    FieldDefinition(
        name="supplier_gst",
        label="GST Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="supplier_info",
        view_order=13
    ),
    
    # === PURCHASE ORDER RELATIONSHIP ===
    FieldDefinition(
        name="po_id",
        label="Purchase Order",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=True,
        tab_group="invoice_details",
        section="po_info",
        view_order=20
    ),
    
    FieldDefinition(
        name="po_number",
        label="PO Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        searchable=True,
        sortable=True,
        tab_group="invoice_details",
        section="po_info",
        view_order=21
    ),
    
    FieldDefinition(
        name="po_date",
        label="PO Date",
        field_type=FieldType.DATE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="invoice_details",
        section="po_info",
        view_order=22
    ),
    
    # === FINANCIAL INFORMATION ===
    FieldDefinition(
        name="invoice_total_amount",
        label="Total Amount",
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
        view_order=30,
        css_classes="text-xl font-bold text-green-600"
    ),
    
    FieldDefinition(
        name="cgst_amount",
        label="CGST",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="tax_details",
        view_order=31
    ),
    
    FieldDefinition(
        name="sgst_amount",
        label="SGST",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="tax_details",
        view_order=32
    ),
    
    FieldDefinition(
        name="igst_amount",
        label="IGST",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="tax_details",
        view_order=33
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
        view_order=34
    ),
    
    # === STATUS AND WORKFLOW ===
    FieldDefinition(
        name="payment_status",
        label="Payment Status",
        field_type=FieldType.STATUS_BADGE,
        db_column="payment_status",  # Direct mapping
        filter_aliases=["status", "payment_status"],  # ✅ Add aliases for flexibility
        filter_operator=FilterOperator.EQUALS,
        options=[
            # ✅ Invoice-specific payment states (NOT workflow states)
            {"value": "pending", "label": "Pending", "color": "warning"},
            {"value": "partial", "label": "Partially Paid", "color": "info"},
            {"value": "paid", "label": "Paid", "color": "success"},
            {"value": "overdue", "label": "Overdue", "color": "danger"},
            {"value": "cancelled", "label": "Cancelled", "color": "secondary"}
        ],
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,  # Read-only from view
        searchable=False,
        sortable=True,
        filterable=True,
        readonly=True,
        tab_group="invoice_details",
        section="payment_status",
        view_order=40,
        css_classes="payment-status-column"
    ),
    
    FieldDefinition(
        name="gl_posted",
        label="GL Posted",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="posting_info",
        section="posting_status",
        view_order=41
    ),
    
    FieldDefinition(
        name="inventory_posted",
        label="Inventory Posted",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="posting_info",
        section="posting_status",
        view_order=42
    ),
    
    # === AGING ANALYSIS ===
    FieldDefinition(
        name="invoice_age_days",
        label="Age (Days)",
        field_type=FieldType.INTEGER,
        filterable=True,
        filter_operator=FilterOperator.LESS_THAN_OR_EQUAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        virtual=False,  # This field exists in the view
        tab_group="invoice_details",
        section="aging",
        view_order=50
    ),
    
    FieldDefinition(
        name="days_overdue",
        label="Days Overdue",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        virtual=False,  # This field exists in the view
        tab_group="invoice_details",
        section="aging",
        view_order=51,
        css_classes="text-red-600 font-bold"
    ),
    
    FieldDefinition(
        name="aging_bucket",
        label="Aging Bucket",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        filterable=False,
        tab_group="invoice_details",
        section="aging",
        view_order=52
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
        view_order=60,
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
        view_order=70,
        custom_renderer=CustomRenderer(
            template="engine/business/universal_line_items_table.html",
            context_function="get_invoice_lines",
            css_classes="w-100"
        )
    ),

    FieldDefinition(
        name="po_lines_display",
        label="Purchase Order Line Items",
        field_type=FieldType.CUSTOM,
        virtual=True,
        show_in_detail=True,
        show_in_list=False,
        show_in_form=False,
        readonly=True,
        tab_group="line_items",
        section="po_items",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="engine/business/universal_line_items_table.html",
            context_function="get_po_line_items",
            css_classes="w-100"
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
        view_order=80,
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_payment_history",
            css_classes="table-responsive payment-history-table"
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
        view_order=90
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
        view_order=91
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
        view_order=92
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
        view_order=93
    ),

    # Payment History Display - matching PO format
    FieldDefinition(
        name="payment_history_display",
        label="Payment History",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="payments",
        section="payment_history",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_payment_history",  # You'll need to add this method to supplier_invoice_service.py
            css_classes="table-responsive payment-history-table"
        )
    ),

    # Purchase Order Details Display (if invoice is linked to PO)
    FieldDefinition(
        name="po_details_display",
        label="Purchase Order Details",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="invoice_details",  # Or create a separate 'po_details' tab
        section="po_info",
        view_order=25,
        custom_renderer=CustomRenderer(
            template="components/business/po_summary_card.html",
            context_function="get_po_details",  # You'll need to add this method
            css_classes="po-summary-card"
        )
    )
]

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

SUPPLIER_INVOICE_SECTIONS = {
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
    "supplier_info": SectionDefinition(
        key="supplier_info",
        title="Supplier Information",
        icon="fas fa-building",
        columns=2,
        order=3
    ),
    "po_info": SectionDefinition(
        key="po_info",
        title="Purchase Order Reference",
        icon="fas fa-file-invoice",
        columns=2,
        order=4
    ),
    "amounts": SectionDefinition(
        key="amounts",
        title="Invoice Amounts",
        icon="fas fa-rupee-sign",
        columns=2,
        order=5
    ),
    "tax_details": SectionDefinition(
        key="tax_details",
        title="Tax Information",
        icon="fas fa-percent",
        columns=2,
        order=6
    ),
    "status": SectionDefinition(
        key="status",
        title="Payment Status",
        icon="fas fa-info-circle",
        columns=2,
        order=7
    ),
    "aging": SectionDefinition(
        key="aging",
        title="Aging Information",
        icon="fas fa-clock",
        columns=2,
        order=8
    ),
    
    # Line Items Tab Sections
    "items": SectionDefinition(
        key="items",
        title="Invoice Line Items",  # FIX 2: Added title
        icon="fas fa-shopping-cart",
        columns=1,  # FIX 1: Full width
        order=1
    ),
    
    # Payments Tab Sections
    "payment_history": SectionDefinition(
        key="payment_history",
        title="",  # No title as table has its own header
        icon="",
        columns=1,
        order=1
    ),
    "payment_summary": SectionDefinition(
        key="payment_summary",
        title="Payment Summary",
        icon="fas fa-money-bill",
        columns=2,
        order=2
    ),

    "po_items": SectionDefinition(
        key="po_items",
        title="Purchase Order Line Items (For Comparison)",
        icon="fas fa-shopping-cart",
        columns=1,
        order=2
    ),
    
    # Posting Info Tab Sections
    "posting_status": SectionDefinition(
        key="posting_status",
        title="Posting Status",
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
    "technical_info": SectionDefinition(
        key="technical_info",
        title="Technical Information",
        icon="fas fa-cog",
        columns=2,
        order=2
    ),
    
    # Additional Info Section
    "additional_info": SectionDefinition(
        key="additional_info",
        title="Additional Information",
        icon="fas fa-info",
        columns=1,
        order=9
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION (TABBED)
# =============================================================================

SUPPLIER_INVOICE_TABS = {
    "invoice_details": TabDefinition(
        key="invoice_details",
        label="Invoice Details",
        icon="fas fa-file-invoice-dollar",
        sections={
            "identification": SUPPLIER_INVOICE_SECTIONS["identification"],
            "supplier_info": SUPPLIER_INVOICE_SECTIONS["supplier_info"],
            "dates": SUPPLIER_INVOICE_SECTIONS["dates"],
            "po_info": SUPPLIER_INVOICE_SECTIONS["po_info"],
            "status": SUPPLIER_INVOICE_SECTIONS["status"],
            "amounts": SUPPLIER_INVOICE_SECTIONS["amounts"],
            "tax_details": SUPPLIER_INVOICE_SECTIONS["tax_details"],
            "aging": SUPPLIER_INVOICE_SECTIONS["aging"],
            "additional_info": SUPPLIER_INVOICE_SECTIONS["additional_info"]
        },
        order=0,
        default_active=True
    ),
    "line_items": TabDefinition(
        key="line_items",
        label="Line Items",
        icon="fas fa-list",
        sections={
            "items": SUPPLIER_INVOICE_SECTIONS["items"],
            "po_items": SUPPLIER_INVOICE_SECTIONS["po_items"]
        },
        order=1
    ),
    "payments": TabDefinition(
        key="payments",
        label="Payments",
        icon="fas fa-money-bill-wave",
        sections={
            "payment_history": SUPPLIER_INVOICE_SECTIONS["payment_history"],
            "payment_summary": SUPPLIER_INVOICE_SECTIONS["payment_summary"]
        },
        order=2
    ),
    "posting_info": TabDefinition(
        key="posting_info",
        label="GL Posting",
        icon="fas fa-check-circle",
        sections={
            "posting_status": SUPPLIER_INVOICE_SECTIONS["posting_status"]
        },
        order=3
    ),
    "system_info": TabDefinition(
        key="system_info",
        label="System Info",
        icon="fas fa-cog",
        sections={
            "audit": SUPPLIER_INVOICE_SECTIONS["audit"],
            "technical_info": SUPPLIER_INVOICE_SECTIONS["technical_info"]
        },
        order=4
    )
}

SUPPLIER_INVOICE_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    tabs=SUPPLIER_INVOICE_TABS,
    sections=SUPPLIER_INVOICE_SECTIONS,
    default_tab="invoice_details",
    sticky_tabs=True,  # ADDED: like PO
    auto_generate_sections=False,  # ADDED
    default_section_columns=2,  # ADDED
    enable_print=True,  # ADDED
    enable_export=True,  # ADDED
    # CRITICAL FIX: Added header_config like purchase_orders
    header_config={
        "primary_field": "supplier_invoice_number",
        "primary_label": "Invoice Number",
        "title_field": "supplier_name",
        "title_label": "Supplier",
        "status_field": "payment_status",  # Show payment status badge
        "secondary_fields": [
            {"field": "invoice_date", "label": "Invoice Date", "icon": "fas fa-calendar", "type": "date", "format": "%d-%b-%Y"},
            {"field": "invoice_total_amount", "label": "Total Amount", "icon": "fas fa-rupee-sign", "type": "currency", "css_classes": "text-xl font-bold text-primary"},
            {"field": "due_date", "label": "Due Date", "icon": "fas fa-clock", "type": "date", "format": "%d-%b-%Y"},
            {"field": "balance_amount", "label": "Balance", "icon": "fas fa-money-bill", "type": "currency", "css_classes": "text-lg font-semibold text-danger"}
        ]
    }
)

# =============================================================================
# ACTIONS CONFIGURATION
# =============================================================================

SUPPLIER_INVOICE_ACTIONS = [
    # === LIST VIEW ACTIONS ===
    ActionDefinition(
        id="view",
        label="View Details",
        icon="fas fa-eye",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_detail_view",
        route_params={"entity_type": "supplier_invoices", "item_id": "{invoice_id}"},
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        permission="supplier_invoice_view",
        order=1
    ),
    
    ActionDefinition(
        id="make_payment",
        label="Make Payment",
        icon="fas fa-money-bill-wave",
        button_type=ButtonType.SUCCESS,
        route_name="supplier_views.create_payment",
        route_params={"invoice_id": "{invoice_id}"},
        show_in_list=True,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        permission="supplier_payment_create",
        order=1.5,
        conditions={
            "payment_status": ["pending", "partial", "overdue"]
        }
    ),

    ActionDefinition(
        id="export",
        label="Export",
        icon="fas fa-download",
        button_type=ButtonType.SECONDARY,
        url_pattern="/universal/supplier_invoices/export",
        show_in_list=False,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="supplier_invoice_export",
        order=2
    ),
    
    # === DETAIL VIEW ACTIONS - TOOLBAR ===
    ActionDefinition(
        id="back",
        label="Back to List",
        icon="fas fa-arrow-left",
        button_type=ButtonType.SECONDARY,
        route_name="universal_entity.list",
        route_params={"entity_type": "supplier_invoices"},
        show_in_list=False,
        show_in_detail=True,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="supplier_invoice_list",
        order=1
    ),
    
    ActionDefinition(
        id="print_invoice",
        label="Print Invoice",
        icon="fas fa-print",
        button_type=ButtonType.INFO,
        route_name="universal_views.universal_document_view",
        route_params={"entity_type": "supplier_invoices", "item_id": "{invoice_id}", "doc_type": "invoice"},
        show_in_list=True,
        show_in_detail=True,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="supplier_invoice_print",
        order=2
    ),
    
    ActionDefinition(
        id="download_pdf",
        label="Download PDF",
        icon="fas fa-file-pdf",
        button_type=ButtonType.SUCCESS,
        url_pattern="/universal/supplier_invoices/document/{invoice_id}?type=invoice&format=pdf",
        show_in_list=False,
        show_in_detail=True,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        permission="supplier_invoice_document",
        order=3
    ),
    
    # === DETAIL VIEW ACTIONS - DROPDOWN (Navigation only, no modifications) ===
    ActionDefinition(
        id="view_supplier",
        label="View Supplier",
        icon="fas fa-building",
        button_type=ButtonType.INFO,
        url_pattern="/universal/suppliers/view/{supplier_id}",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditional_display="item.supplier_id",
        permission="suppliers_view",
        order=4
    ),
    
    ActionDefinition(
        id="view_po",
        label="View Purchase Order",
        icon="fas fa-file-invoice",
        button_type=ButtonType.INFO,
        url_pattern="/universal/purchase_orders/view/{po_id}",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditional_display="item.po_id",
        permission="purchase_order_view",
        order=5
    ),
    
    ActionDefinition(
        id="view_payments",
        label="View Related Payments",
        icon="fas fa-money-check",
        button_type=ButtonType.INFO,
        url_pattern="/supplier/invoices/{invoice_id}/payments",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditional_display="item.paid_amount > 0",
        permission="supplier_payment_view",
        order=6
    ),
    
    ActionDefinition(
        id="download_statement",
        label="Download Statement",
        icon="fas fa-file-alt",
        button_type=ButtonType.SECONDARY,
        url_pattern="/universal/supplier_invoices/document/{invoice_id}?type=statement&format=pdf",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        permission="supplier_invoice_document",
        order=7
    )
]
# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

SUPPLIER_INVOICE_SUMMARY_CARDS = [
    # =========================================================================
    # VISIBLE CARDS
    # =========================================================================
    
    {
        "id": "total_count",
        "field": "total_count",  # Special field handled by Universal Engine
        "label": "Total Invoices",
        "icon": "fas fa-file-invoice",
        "icon_css": "stat-card-icon primary",
        "type": "number",
        "visible": True,
        "order": 1
    },
    
    {
        "id": "total_amount",
        "field": "invoice_total_amount",  # ✅ Direct database column!
        "label": "Total Amount",
        "icon": "fas fa-rupee-sign", 
        "icon_css": "stat-card-icon success",
        "type": "currency",  # Tells Universal Engine to SUM this column
        "visible": True,
        "order": 2
    },
    
    # =========================================================================
    # HIDDEN CALCULATION CARDS (Universal Engine processes these)
    # =========================================================================
    
    # Hidden card for pending amount calculation
    {
        "id": "pending_amount_calc",
        "field": "invoice_total_amount",  # Column to sum
        "type": "currency",  # Triggers SUM aggregation
        "visible": False,  # Hidden - just for calculation
        "filter_condition": {  # ✅ Universal Engine applies this filter!
            "payment_status": ["pending", "partial"]  # WHERE payment_status IN ('pending', 'partial')
        }
    },
    
    # Hidden card for overdue amount calculation  
    {
        "id": "overdue_amount_calc",
        "field": "invoice_total_amount",  # Column to sum
        "type": "currency",
        "visible": False,
        "filter_condition": {
            "payment_status": "overdue"  # WHERE payment_status = 'overdue'
        }
    },
    
    # =========================================================================
    # VISIBLE CARDS THAT REFERENCE CALCULATIONS
    # =========================================================================
    
    {
        "id": "pending_amount",
        "field": "pending_amount_calc",  # ✅ References the hidden calculation
        "label": "Pending Payment",
        "icon": "fas fa-clock",
        "icon_css": "stat-card-icon warning",
        "type": "currency",
        "visible": True,
        "order": 3
    },
    
    {
        "id": "overdue_amount", 
        "field": "overdue_amount_calc",  # ✅ References the hidden calculation
        "label": "Overdue",
        "icon": "fas fa-exclamation-triangle",
        "icon_css": "stat-card-icon danger",
        "type": "currency",
        "visible": True,
        "order": 4
    }
]

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

SUPPLIER_INVOICE_FILTER_CATEGORY_MAPPING = {
    # Search filters - Multiple aliases for supplier name
    # Generic search - MUST be here for search box to work
    'search': FilterCategory.SEARCH,
    'supplier_name': FilterCategory.SEARCH,  # ✅ Direct field name
    'supplier_name_search': FilterCategory.SEARCH,  # ✅ Add alias
    'supplier_search': FilterCategory.SEARCH,  # ✅ Add alias
    'supplier_invoice_number': FilterCategory.SEARCH,
    'po_number': FilterCategory.SEARCH,
    'supplier_id': FilterCategory.SEARCH,
    'notes': FilterCategory.SEARCH,
    
    # Selection filters with proper mapping
    'payment_status': FilterCategory.SELECTION,  # ✅ Main field
    'status': FilterCategory.SELECTION,  # ✅ Alias for payment_status
    'aging_bucket': FilterCategory.SELECTION,
    'gl_posted': FilterCategory.SELECTION,
    'inventory_posted': FilterCategory.SELECTION,
    
    # Date filters
    'invoice_date': FilterCategory.DATE,
    'due_date': FilterCategory.DATE,
    
    # Amount filters
    'invoice_total_amount': FilterCategory.AMOUNT,
    'invoice_age_days': FilterCategory.AMOUNT,
    
    # Relationship filters
    'po_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP
}

SUPPLIER_INVOICE_DEFAULT_FILTERS = {
    # 'payment_status': ['pending', 'partial']  # Show unpaid invoices by default
    # 'workflow_status': '',  # Default to "All" (empty string)
    'payment_status': '',  # Default to "All" (empty string shows all statuses)
}

SUPPLIER_INVOICE_CATEGORY_CONFIGS = {
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
        'search_fields': ['supplier_name', 'supplier_invoice_number', 'po_number']  # ✅ Specify search fields
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

SUPPLIER_INVOICE_DOCUMENT_CONFIGS = {
    "invoice": DocumentConfiguration(
        enabled=True,
        document_type="invoice",
        title="Supplier Invoice",
        subtitle="Tax Invoice",
        page_size="A4",
        orientation="portrait",
        margins={"top": 20, "bottom": 20, "left": 15, "right": 15},
        print_layout_type="simple_with_header",
        show_logo=True,
        show_company_info=True,
        show_footer=True,
        visible_tabs=["invoice_details", "line_items"],
        header_text="SUPPLIER INVOICE",
        footer_text="This is a system generated document",
        show_print_info=True,
        signature_fields=[
            {"label": "Received By", "width": "200px"},
            {"label": "Verified By", "width": "200px"},
            {"label": "Approved By", "width": "200px"}
        ],
        allowed_formats=["pdf", "print", "excel"],
        default_format="pdf"
    ),
    "statement": DocumentConfiguration(
        enabled=True,
        document_type="report",
        title="Invoice Statement",
        subtitle="Supplier Invoice List",
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

SUPPLIER_INVOICE_PERMISSIONS = {
    "list": "supplier_invoice_list",
    "view": "supplier_invoice_view",
    "export": "supplier_invoice_export",
    "print": "supplier_invoice_print",
    "document": "supplier_invoice_document"
    # REMOVED: create, edit, delete, cancel, email - transaction entities are read-only
}

# =============================================================================
# ENTITY FILTER CONFIGURATION
# =============================================================================

SUPPLIER_INVOICE_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='supplier_invoices',
    filter_mappings={
        # Payment Status with correct options
        'payment_status': {
            'field': 'payment_status',
            'type': 'select',
            'label': 'Payment Status',
            'options': [
                {'value': '', 'label': 'All'},  # ✅ Add "All" option
                {'value': 'pending', 'label': 'Pending'},
                {'value': 'partial', 'label': 'Partially Paid'},
                {'value': 'paid', 'label': 'Paid'},
                {'value': 'overdue', 'label': 'Overdue'},
                {'value': 'cancelled', 'label': 'Cancelled'}
            ]
        },
        
        # Supplier Name filter configuration
        'supplier_name': {
            'field': 'supplier_name',
            'type': 'text',  # ✅ Text search, not select
            'label': 'Supplier Name',
            'placeholder': 'Search supplier name...',
            'search_in_view': True  # ✅ Search in view column
        },
        
        # Aging Bucket
        'aging_bucket': {
            'field': 'aging_bucket',
            'type': 'select',
            'label': 'Aging',
            'options': [
                {'value': '', 'label': 'All'},
                {'value': '0-30', 'label': '0-30 Days'},
                {'value': '31-60', 'label': '31-60 Days'},
                {'value': '61-90', 'label': '61-90 Days'},
                {'value': '90+', 'label': 'Over 90 Days'}
            ]
        },
        
        # Supplier ID (for entity search)
        'supplier_id': {
            'field': 'supplier_id',
            'type': 'entity_search',
            'entity_type': 'suppliers',
            'display_field': 'supplier_name',
            'search_fields': ['supplier_name', 'supplier_code'],
            'placeholder': 'Search suppliers...',
            'label': 'Supplier'
        }
    }
)

# =============================================================================
# ENTITY SEARCH CONFIGURATION
# =============================================================================

SUPPLIER_INVOICE_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='supplier_invoices',
    search_fields=['supplier_invoice_number', 'supplier_name', 'po_number'],
    display_template='{supplier_invoice_number} - {supplier_name}',
    min_chars=1,
    max_results=10,
    sort_field='invoice_date'
)

# =============================================================================
# MAIN CONFIGURATION
# =============================================================================

SUPPLIER_INVOICE_CONFIG = EntityConfiguration(
    # === BASIC INFORMATION ===
    entity_type="supplier_invoices",
    name="Supplier Invoice",
    plural_name="Supplier Invoices",
    service_name="supplier_invoices",
    icon="fas fa-file-invoice-dollar",
    
    # === DATABASE CONFIGURATION ===
    table_name="supplier_invoices_view",
    primary_key="invoice_id",
    
    # === DISPLAY CONFIGURATION ===
    title_field="supplier_invoice_number",
    subtitle_field="supplier_name",
    page_title="Supplier Invoices",
    description="Manage supplier invoices and track payments",
    
    # === SEARCH AND SORT ===
    searchable_fields=["supplier_invoice_number", "supplier_name", "po_number", "notes"],
    default_sort_field="invoice_date",
    default_sort_direction="desc",
    
    # === CORE CONFIGURATIONS ===
    fields=SUPPLIER_INVOICE_FIELDS,
    view_layout=SUPPLIER_INVOICE_VIEW_LAYOUT,
    section_definitions=SUPPLIER_INVOICE_SECTIONS,
    actions=SUPPLIER_INVOICE_ACTIONS,
    summary_cards=SUPPLIER_INVOICE_SUMMARY_CARDS,
    permissions=SUPPLIER_INVOICE_PERMISSIONS,
    
    # === FILTER CONFIGURATION ===
    filter_category_mapping=SUPPLIER_INVOICE_FILTER_CATEGORY_MAPPING,
    default_filters=SUPPLIER_INVOICE_DEFAULT_FILTERS,
    category_configs=SUPPLIER_INVOICE_CATEGORY_CONFIGS,
    
    # === DATE AND AMOUNT CONFIGURATION ===
    primary_date_field="invoice_date",
    primary_amount_field="invoice_total_amount",
    
    # === DOCUMENT GENERATION ===
    document_enabled=True,
    document_configs=SUPPLIER_INVOICE_DOCUMENT_CONFIGS,
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
        "supplier_name",
        "supplier_category",
        "supplier_gst",
        "supplier_email",
        "po_number",
        "po_date",
        "total_gst_amount",
        "invoice_age_days",
        "days_overdue",
        "aging_bucket",
        "branch_name",
        "hospital_name"
    ],
    
    # === FEATURE FLAGS ===
    enable_audit_trail=True,
    enable_soft_delete=False,
    enable_bulk_operations=False,
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    
    # === ENTITY CATEGORY ===
    entity_category=EntityCategory.TRANSACTION,
    
    # === DOCUMENT PERMISSIONS ===
    document_permissions={
        "invoice": "supplier_invoice_view",
        "statement": "supplier_invoice_list"
    }
)

# =============================================================================
# MODULE EXPORTS
# =============================================================================

def get_module_configs():
    """Return all configurations from this module"""
    return {
        "supplier_invoices": SUPPLIER_INVOICE_CONFIG
    }

def get_module_filter_configs():
    """Return filter configurations"""
    return {
        "supplier_invoices": SUPPLIER_INVOICE_FILTER_CATEGORY_MAPPING
    }

# Direct exports for simplified access
config = SUPPLIER_INVOICE_CONFIG
filter_config = SUPPLIER_INVOICE_ENTITY_FILTER_CONFIG
search_config = SUPPLIER_INVOICE_SEARCH_CONFIG