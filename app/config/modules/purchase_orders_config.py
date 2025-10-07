"""
Purchase Order Configuration for Universal Engine
File: app/config/modules/purchase_orders_config.py

Complete configuration leveraging Universal Engine v4.0 capabilities
Using correct field types from core_definitions.py
Based on financial_transactions.py patterns
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from sqlalchemy import true
from app.config.core_definitions import (
    FieldDefinition, FieldType, EntityConfiguration, EntityCategory,
    CRUDOperation, SectionDefinition, ViewLayoutConfiguration, LayoutType,
    TabDefinition, ActionDefinition, ButtonType, ActionDisplayType,
    DocumentConfiguration, EntityFilterConfiguration, EntitySearchConfiguration, 
    ComplexDisplayType, CustomRenderer, FilterOperator, FilterType
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# PURCHASE ORDER FIELD DEFINITIONS
# =============================================================================

PURCHASE_ORDER_FIELDS = [
    # === PRIMARY IDENTIFIERS ===
    FieldDefinition(
        name="po_id",
        label="PO ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="order_details",  # Changed from "header"
        section="identification",
        view_order=0
    ),
    
    FieldDefinition(
        name="po_number",
        label="PO Number",
        field_type=FieldType.TEXT,
        required=True,
        searchable=True,
        sortable=True,
        filterable=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        placeholder="Enter PO number",
        tab_group="order_details",  # Changed from "header"
        section="identification",
        view_order=1
    ),
    
    # === SUPPLIER RELATIONSHIP (Following financial_transactions.py pattern) ===
    FieldDefinition(
        name="supplier_id",
        label="Supplier",
        field_type=FieldType.ENTITY_SEARCH,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=True,
        required=True,
        filterable=False,
        tab_group="order_details",  # Changed from "header"
        section="supplier_info",
        view_order=10,
        autocomplete_enabled=True,
        autocomplete_source="suppliers",
        entity_search_config=EntitySearchConfiguration(
            target_entity="suppliers",
            search_fields=["supplier_name", "contact_person_name"],
            display_template="{supplier_name}",
            min_chars=2,
            max_results=10,
            additional_filters={"status": "active"}
        )
    ),
    
    # Virtual field for supplier name display (Following financial_transactions.py pattern)
    FieldDefinition(
        name="supplier_name",
        label="Supplier Name",  # Can be just "Supplier" as in payment config
        field_type=FieldType.TEXT,
        virtual=False,
        
        # === DISPLAY PROPERTIES (unchanged) ===
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        readonly=True,
        
        # === SEARCH PROPERTIES ===
        searchable=True,  # VERIFIED: Both configs have this as True
        
        # === FILTER PROPERTIES (VERIFIED PATTERN) ===
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,  # ⭐ VERIFIED: Both configs use this
        filter_operator=FilterOperator.CONTAINS,  # VERIFIED: Invoice uses CONTAINS, Payment uses EQUALS
        
        # === ENTITY SEARCH CONFIGURATION (VERIFIED) ===
        entity_search_config=EntitySearchConfiguration(
            target_entity='suppliers',
            search_fields=['supplier_name', 'contact_person_name'],  # VERIFIED: Both configs use these fields
            display_template='{supplier_name}',  # VERIFIED: Both configs use this template
            value_field='supplier_name',      # VERIFIED: Both use name as value (NOT UUID)
            filter_field='supplier_name',     # VERIFIED: Both filter by name field
            placeholder="Type to search suppliers...",  # VERIFIED: Same in both configs
            preload_common=True,              # VERIFIED: Both configs use True
            cache_results=True,               # VERIFIED: Both configs use True
            min_chars=2,                      # Invoice: 2, Payment: 1 (using Invoice pattern)
            max_results=20                    # Payment config value (Invoice doesn't specify)
        ),
        
        # === LAYOUT PROPERTIES (keep existing) ===
        placeholder="Search supplier name...",  # Additional placeholder for list view
        tab_group="order_details",
        section="supplier_info",
        view_order=11,
        complex_display_type=ComplexDisplayType.ENTITY_REFERENCE  # VERIFIED: Both configs use this
    ),
    
    # === DATE FIELDS ===
    FieldDefinition(
        name="po_date",
        label="PO Date",
        field_type=FieldType.DATE,  # ✅ Changed to DATE (no time)
        format_pattern="%d-%b-%Y", 
        required=True,
        sortable=True,
        filterable=False,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filter_aliases=["start_date", "end_date"],
        filter_type="date_range",
        tab_group="order_details",  # Changed from "header"
        section="dates",
        view_order=20
    ),
    
    FieldDefinition(
        name="expected_delivery_date",
        label="Expected Delivery",
        field_type=FieldType.DATE,
        format_pattern="%d-%b-%Y",
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        filter_operator=FilterOperator.DATE_ON_OR_BEFORE,  # ✅ ADD THIS
        placeholder="On or before this date",  # ✅ ADD/UPDATE THIS
        tab_group="order_details",  # Changed from "header"
        section="dates",
        view_order=21
    ),
    
    # === STATUS AND WORKFLOW ===
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.STATUS_BADGE,
        db_column="po_status",  # ✅ Maps to actual DB column
        options=[
            {"value": "draft", "label": "Draft", "color": "secondary"},
            {"value": "pending", "label": "Pending", "color": "warning"},
            {"value": "approved", "label": "Approved", "color": "info"},
            {"value": "partially_received", "label": "Partially Received", "color": "primary"},
            {"value": "received", "label": "Received", "color": "success"},
            {"value": "cancelled", "label": "Cancelled", "color": "danger"}
        ],
        required=True,
        default_value="pending",
        filterable=True,
        sortable=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        tab_group="order_details",
        section="workflow",
        view_order=22
    ),
    
    # === FINANCIAL FIELDS ===
    FieldDefinition(
        name="total_amount",
        label="Total Amount",
        field_type=FieldType.CURRENCY,
        virtual=False, 
        sortable=True,
        filterable=False,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        filter_aliases=["min_amount", "max_amount"],
        filter_type="amount_range",
        tab_group="financials",  # Changed from "financial"
        section="amounts",
        view_order=40
    ),
    
    FieldDefinition(
        name="currency_code",
        label="Currency",
        field_type=FieldType.SELECT,
        options=[
            {"value": "INR", "label": "INR"},
            {"value": "USD", "label": "USD"},
            {"value": "EUR", "label": "EUR"},
            {"value": "GBP", "label": "GBP"}
        ],
        default_value="INR",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        tab_group="financials",  # Changed from "financial"
        section="currency_info",
        view_order=41
    ),
    
    FieldDefinition(
        name="exchange_rate",
        label="Exchange Rate",
        field_type=FieldType.DECIMAL,
        default_value=1.0,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="financials",  # Changed from "financial"
        section="currency_info",
        view_order=42
    ),
    
    # === REFERENCE FIELDS ===
    FieldDefinition(
        name="quotation_id",
        label="Quotation ID",
        field_type=FieldType.TEXT,
        searchable=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="order_details",  # Moved from "references"
        section="references",
        view_order=50
    ),
    
    # === BRANCH RELATIONSHIP (Following financial_transactions.py pattern) ===
    FieldDefinition(
        name="branch_id",
        label="Branch",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=False,
        required=False,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        tab_group="order_details",  # Changed from "header"
        section="identification",
        view_order=5
    ),
    
    # === APPROVAL FIELDS ===
    FieldDefinition(
        name="quotation_date",
        label="Quotation Date",
        field_type=FieldType.DATE,
        format_pattern="%d/%b/%Y",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="order_details",  # Moved from "references"
        section="references",
        view_order=51
    ),
    
    FieldDefinition(
        name="approved_by",
        label="Approved By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="order_details",  # Changed from "header"
        section="status_info",
        view_order=31
    ),
    
    # === AUDIT FIELDS ===
    FieldDefinition(
        name="created_at",
        label="Created Date",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        sortable=True,
        tab_group="audit",
        section="audit_info",
        view_order=70
    ),
    
    FieldDefinition(
        name="created_by",
        label="Created By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="audit",
        section="audit_info",
        view_order=71
    ),
    
    FieldDefinition(
        name="updated_at",
        label="Last Updated",
        field_type=FieldType.DATETIME,
        format_pattern="%d/%b/%Y %H:%M",
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="audit",
        section="audit_info",
        view_order=72
    ),
    
    FieldDefinition(
        name="updated_by",
        label="Updated By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="audit",
        section="audit_info",
        view_order=73
    ),
    
    # === VIRTUAL/CALCULATED FIELDS ===
    FieldDefinition(
        name="line_count",
        label="Items",
        field_type=FieldType.NUMBER,
        virtual=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="line_items",  # Changed from "items"
        section="items_summary",
        view_order=80
    ),
    # Virtual fields for invoice/payment information
    FieldDefinition(
        name="linked_invoices_display",
        label="Related Invoices",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="financials",
        section="invoice_summary",
        view_order=10,
        custom_renderer=CustomRenderer(
            template="components/business/invoice_items_table.html",
            context_function="get_po_invoices",
            css_classes="table-responsive"
        )
    ),
    FieldDefinition(
        name="payment_history_display",
        label="Payment History",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="financials",
        section="payment_summary",
        view_order=20,
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_po_payments",
            css_classes="table-responsive"
        )
    ),
    
    # === NEW: Custom renderer field for line items display ===
    FieldDefinition(
        name="po_line_items_display",
        label="Order Line Items",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="line_items",
        section="items_display",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="engine/business/universal_line_items_table.html",  # Universal template
            context_function="get_po_line_items_display",
            css_classes="w-100"
        )
    ),
    
    # === SOFT DELETE ===
    FieldDefinition(
        name="deleted_flag",
        label="Deleted",
        field_type=FieldType.BOOLEAN,
        default_value=False,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False
    ),
    # === SOFT DELETE TRACKING FIELDS ===
    FieldDefinition(
        name="is_deleted",  # Will exist after migration
        label="Is Deleted",
        field_type=FieldType.BOOLEAN,  # ✅ Verified in core_definitions.py
        show_in_list=False,
        show_in_detail=False,  # Hidden from UI
        show_in_form=False,
        readonly=True,
        filterable=True,  # Allow admin filtering
    ),
    
    FieldDefinition(
        name="deleted_at",  # Will exist after migration
        label="Deleted At", 
        field_type=FieldType.DATETIME,  # ✅ Verified in core_definitions.py
        show_in_list=False,
        show_in_detail=True,  # Show for audit
        show_in_form=False,
        readonly=True,
        format_pattern="%d/%b/%Y at %H:%M",
        tab_group="audit",  # ✅ Verified tab exists in current config
        section="audit_info",  # ✅ Verified section exists
        view_order=95
    ),
    
    FieldDefinition(
        name="deleted_by",  # Will exist after migration
        label="Deleted By",
        field_type=FieldType.TEXT,  # ✅ Verified in core_definitions.py
        show_in_list=False,
        show_in_detail=True,  # Show for audit
        show_in_form=False,
        readonly=True,
        tab_group="audit",
        section="audit_info",
        view_order=96
    ),
    
    # ✅ NEW: Missing approval timestamp field (approved_by exists in view)
    FieldDefinition(
        name="approved_at",  # Will exist after migration
        label="Approved At",
        field_type=FieldType.DATETIME,  # ✅ Verified in core_definitions.py
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        format_pattern="%d/%b/%Y at %H:%M",
        tab_group="order_details",  # ✅ Verified tab exists
        section="status_info",  # ✅ Verified section exists
        view_order=32
    ),
    
    # ✅ NEW: Virtual fields for business logic (calculated in service)
    FieldDefinition(
        name="has_invoice",
        label="Has Invoice",
        field_type=FieldType.BOOLEAN,  # ✅ Verified in core_definitions.py
        virtual=True,  # Calculated field
        show_in_list=False,
        show_in_detail=False,  # Used by actions only
        show_in_form=False,
        readonly=True
    ),
    
    FieldDefinition(
        name="invoice_count",
        label="Invoice Count",
        field_type=FieldType.NUMBER,  # ✅ Verified in core_definitions.py (was INTEGER)
        virtual=True,  # Calculated field
        show_in_list=False,
        show_in_detail=True,  # Can show for information
        show_in_form=False,
        readonly=True,
        tab_group="financials",  # ✅ Verified tab exists
        section="invoice_summary",  # ✅ Verified section exists
        view_order=90
    ),
    
    FieldDefinition(
        name="approval_status",
        label="Approval Status",
        field_type=FieldType.TEXT,  # ✅ Verified in core_definitions.py
        virtual=True,  # Calculated field
        show_in_list=False,  # Good for list display
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="order_details",
        section="status_info",
        view_order=30
    ),
    
    # ✅ NEW: Action visibility control fields (used by action conditions)
    FieldDefinition(
        name="can_be_deleted",
        label="Can Be Deleted",
        field_type=FieldType.BOOLEAN,  # ✅ Verified in core_definitions.py
        virtual=True,
        show_in_list=False,
        show_in_detail=False,  # Hidden from UI
        show_in_form=False,
        readonly=True
    ),
    
    FieldDefinition(
        name="can_be_approved",
        label="Can Be Approved", 
        field_type=FieldType.BOOLEAN,  # ✅ Verified in core_definitions.py
        virtual=True,
        show_in_list=False,
        show_in_detail=False,  # Hidden from UI
        show_in_form=False,
        readonly=True
    ),
    
    FieldDefinition(
        name="can_be_unapproved",
        label="Can Be Unapproved",
        field_type=FieldType.BOOLEAN,  # ✅ Verified in core_definitions.py
        virtual=True,
        show_in_list=False,
        show_in_detail=False,  # Hidden from UI
        show_in_form=False,
        readonly=True
    )
]

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

PURCHASE_ORDER_SECTIONS = {
    "identification": SectionDefinition(
        key="identification",
        title="Identification",
        icon="fas fa-id-card",
        columns=2,
        order=1
    ),
    "supplier_info": SectionDefinition(
        key="supplier_info",
        title="Supplier Information",
        icon="fas fa-building",
        columns=2,
        order=2
    ),
    "dates": SectionDefinition(
        key="dates",
        title="Important Dates",
        icon="fas fa-calendar",
        columns=2,
        order=3
    ),
    "status_info": SectionDefinition(
        key="status_info",
        title="Status",
        icon="fas fa-info-circle",
        columns=2,
        order=4
    ),
    "amounts": SectionDefinition(
        key="amounts",
        title="Financial Summary",
        icon="fas fa-rupee-sign",
        columns=2,
        order=5
    ),
    "currency_info": SectionDefinition(
        key="currency_info",
        title="Currency Information",
        icon="fas fa-exchange-alt",
        columns=2,
        order=6
    ),
    "references": SectionDefinition(
        key="references",
        title="References",
        icon="fas fa-link",
        columns=2,
        order=7
    ),
    "items_display": SectionDefinition(  # NEW section for line items display
        key="items_display",
        title="",  # No title as table has its own header
        icon="",
        columns=1,
        order=0
    ),
    "items_summary": SectionDefinition(  # Renamed from "summary"
        key="items_summary",
        title="Order Summary",
        icon="fas fa-list",
        columns=2,
        order=1
    ),
    "audit_info": SectionDefinition(
        key="audit_info",
        title="Audit Information",
        icon="fas fa-history",
        columns=2,
        order=9
    ),
    "invoice_summary": SectionDefinition(
        key="invoice_summary",
        title="Invoice Information",
        icon="fas fa-file-invoice",
        columns=1,
        order=3
    ),
    "payment_summary": SectionDefinition(
        key="payment_summary",
        title="Payment Information",
        icon="fas fa-money-bill",
        columns=1,
        order=4
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

# UPDATED: Reorganized tabs following payment view pattern
PURCHASE_ORDER_TABS = {
    'order_details': TabDefinition(  # Renamed from 'header'
        key='order_details',
        label='Order Details',
        icon='fas fa-file-invoice',
        sections={
            'identification': PURCHASE_ORDER_SECTIONS['identification'],
            'supplier_info': PURCHASE_ORDER_SECTIONS['supplier_info'],
            'dates': PURCHASE_ORDER_SECTIONS['dates'],
            'status_info': PURCHASE_ORDER_SECTIONS['status_info'],
            'references': PURCHASE_ORDER_SECTIONS['references']  # Moved here
        },
        order=0,
        default_active=True
    ),
    'line_items': TabDefinition(  # Renamed from 'items'
        key='line_items',
        label='Line Items',
        icon='fas fa-list',
        sections={
            'items_display': PURCHASE_ORDER_SECTIONS['items_display'],  # NEW
            'items_summary': PURCHASE_ORDER_SECTIONS['items_summary']
        },
        order=1
    ),
    'financials': TabDefinition(  # Renamed from 'financial'
        key='financials',
        label='Financials',
        icon='fas fa-calculator',
        sections={
            'amounts': PURCHASE_ORDER_SECTIONS['amounts'],
            'currency_info': PURCHASE_ORDER_SECTIONS['currency_info'],
            'invoice_summary': PURCHASE_ORDER_SECTIONS['invoice_summary'],  # Add
            'payment_summary': PURCHASE_ORDER_SECTIONS['payment_summary']
        },
        order=2
    ),
    # Removed 'references' tab - moved to order_details
    'audit': TabDefinition(
        key='audit',
        label='System Info',  # Renamed for consistency
        icon='fas fa-cog',
        sections={
            'audit_info': PURCHASE_ORDER_SECTIONS['audit_info']
        },
        order=3  # Changed from 4
    )
}

# UPDATED: View layout with header_config
PURCHASE_ORDER_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    tabs=PURCHASE_ORDER_TABS,
    default_tab="order_details",  # Changed from "header"
    sticky_tabs=True,  # Changed from False
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    # NEW: Header configuration following payment view pattern
    header_config={
        "primary_field": "po_number",
        "primary_label": "PO Number",
        "title_field": "supplier_name",  # This will show supplier name prominently
        "title_label": "Supplier",
        "status_field": "po_status",
        "secondary_fields": [
            {"field": "po_date", "label": "Order Date", "icon": "fas fa-calendar", "type": "date"},
            {"field": "total_amount", "label": "Total Amount", "icon": "fas fa-rupee-sign", "type": "currency", "css_classes": "text-xl font-bold text-primary"},
            {"field": "expected_delivery_date", "label": "Expected Delivery", "icon": "fas fa-truck", "type": "date"}
        ]
    }
)

# =============================================================================
# ACTIONS CONFIGURATION
# =============================================================================

# UPDATED: Actions with proper route configurations
PURCHASE_ORDER_ACTIONS = [
    ActionDefinition(
        id="view",
        label="View Details",
        icon="fas fa-eye",
        button_type=ButtonType.INFO,
        route_name="universal_entity.view",
        route_params={"entity_type": "purchase_orders"},
        show_in_list=False,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        permission="purchase_order_view",
        order=1
    ),
    # List view navigation actions
    ActionDefinition(
        id="invoices",
        label="Invoices",
        icon="fas fa-file-invoice",
        button_type=ButtonType.SECONDARY,
        url_pattern="/supplier/invoice/list",
        show_in_list=False,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=2
    ),
    ActionDefinition(
        id="suppliers",
        label="Suppliers",
        icon="fas fa-building",
        button_type=ButtonType.SECONDARY,
        url_pattern="/supplier/list",
        show_in_list=False,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=3
    ),
    ActionDefinition(
        id="payments",
        label="Payments",
        icon="fas fa-money-bill",
        button_type=ButtonType.SECONDARY,
        url_pattern="/supplier/payment/list",
        show_in_list=False,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=4
    ),
    # Detail view actions
    ActionDefinition(
        id="print",
        label="Print",
        icon="fas fa-print",
        button_type=ButtonType.SECONDARY,
        route_name="universal_views.universal_document_view",  # ✅ Universal Engine
        route_params={
            "entity_type": "purchase_orders",
            "item_id": "{po_id}",
            "doc_type": "invoice"  # Matches PURCHASE_ORDER_DOCUMENT_CONFIGS key
        },
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        permission="purchase_order_print",
        order=5
    ),

    ActionDefinition(
        id="edit",
        label="Edit Purchase Order",
        icon="fas fa-edit",
        button_type=ButtonType.PRIMARY,
        url_pattern="/supplier/purchase-order/edit/{po_id}",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={"po_status": ["draft"],
                    "is_deleted": [False]  # ✅ NEW: Don't show for deleted records
                    },
        permission="purchase_order_edit",
        order=6
    ),
    ActionDefinition(
        id="approve",
        label="Approve",
        icon="fas fa-check-circle",
        button_type=ButtonType.SUCCESS,
        url_pattern="/supplier/purchase-order/approve/{po_id}",
        show_in_list=True,  # Show in list
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,  # Changed to BUTTON for inline
        conditions={
            "po_status": ["draft"],
            "is_deleted": [False]
            # Removed can_be_approved check
        },
        permission="purchase_order_approve",
        order=6,
        confirmation_required=True,
        confirmation_message="Are you sure you want to approve this purchase order?"
    ),
    
    # ✅ NEW: Unapprove action for approved POs
    ActionDefinition(
        id="unapprove",
        label="Unapprove", 
        icon="fas fa-undo",
        button_type=ButtonType.WARNING,  # ✅ Verified in core_definitions.py
        url_pattern="/supplier/purchase-order/unapprove/{po_id}",
        show_in_list=True,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        conditions={
            "po_status": ["approved"],  # ✅ Use correct field name from PurchaseOrderView
            "is_deleted": [False],
            "can_be_unapproved": [True]  # ✅ Check no invoices exist
        },
        permission="purchase_order_approve",  # Same permission as approve
        order=7,
        confirmation_required=True,
        confirmation_message="Are you sure you want to unapprove this purchase order?"
    ),
    
    # ✅ Delete action for draft POs
    ActionDefinition(
        id="delete",
        label="Delete",
        icon="fas fa-trash",
        button_type=ButtonType.DANGER,
        url_pattern="/supplier/purchase-order/delete/{po_id}",  # Use actual route
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "is_deleted": [False, None]
        },
        permission="purchase_order_delete",
        order=8,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this purchase order? This will also delete all line items."
    ),
    
    # ✅ NEW: Restore action for deleted records
    ActionDefinition(
        id="restore",
        label="Restore",
        icon="fas fa-undo",
        button_type=ButtonType.SUCCESS,
        url_pattern="/supplier/purchase-order/restore/{po_id}",  # ✅ Matches delete pattern
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={
            "is_deleted": [True]
        },
        permission="purchase_order_delete",
        order=9,
        confirmation_required=True,
        confirmation_message="Are you sure you want to restore this purchase order?"
    ),
    
    # ✅ UPDATED: Cancel action with enhanced conditions  
    ActionDefinition(
        id="cancel",
        label="Cancel",
        icon="fas fa-times-circle",
        button_type=ButtonType.DANGER,
        url_pattern="/supplier/purchase-order/cancel/{po_id}",
        show_in_list=True,   # ✅ NEW: Show in list
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        conditions={
            "po_status": ["draft", "approved"],  # ✅ FIXED: Use correct field name
            "is_deleted": [False],  # ✅ NEW: Don't show for deleted
            "has_invoice": [False]  # ✅ NEW: Only if no invoices
        },
        confirmation_required=True,
        confirmation_message="Are you sure you want to cancel this purchase order?",
        permission="purchase_order_edit",
        order=10
    ),
    
    ActionDefinition(
        id="create_invoice",
        label="Create Invoice",
        icon="fas fa-file-invoice-dollar",
        button_type=ButtonType.WARNING,
        url_pattern="/supplier/invoice/add?po_id={po_id}",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditions={"status": ["approved"]},
        permission="supplier_invoice_create",
        order=8
    ),
    ActionDefinition(
        id="view_payment",
        label="View Payment",
        icon="fas fa-money-check",
        button_type=ButtonType.INFO,
        url_pattern="/supplier/payment/view/{payment_id}",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        conditional_display="item.payment_id",  # Only show if payment exists
        permission="supplier_payment_view",
        order=9
    )
    # ActionDefinition(
    #     id="export",
    #     label="Export",
    #     icon="fas fa-download",
    #     button_type=ButtonType.SECONDARY,
    #     url_pattern="/universal/purchase_orders/export",
    #     show_in_list=True,
    #     show_in_detail=False,
    #     show_in_toolbar=True,
    #     display_type=ActionDisplayType.BUTTON,
    #     permission="purchase_order_export",
    #     order=10
    # )
]
# =============================================================================
# SUMMARY CARDS CONFIGURATION
# =============================================================================

PURCHASE_ORDER_SUMMARY_CARDS = [
    {
        "title": "Total Orders",
        "field": "total_count",
        "icon": "fas fa-file-invoice",
        "icon_css": "stat-card-icon primary",
        "color": "primary",
        "type": "number",
        "filterable": True,
        "visible": True,
        "order": 1
    },
    {
        "title": "Total Amount",
        "field": "total_amount_sum",
        "icon": "fas fa-rupee-sign",
        "icon_css": "stat-card-icon success",
        "color": "success",
        "type": "currency",
        "filterable": True,
        "visible": True,
        "order": 2
    },
    {
        "title": "Draft Orders",  # ✅ Changed from "Pending Orders"
        "field": "draft_count",
        "icon": "fas fa-clock",
        "icon_css": "stat-card-icon warning",
        "color": "warning",
        "type": "number",
        "filterable": True,
        "filter_value": "draft",  # ✅ This matches the actual status value
        "filter_field": "status",  # ✅ Add this to specify which field to filter
        "visible": True,
        "order": 3
    },
    {
        "title": "This Month",
        "field": "current_month_count",
        "icon": "fas fa-calendar",
        "icon_css": "stat-card-icon info",
        "color": "info",
        "type": "number",
        "filterable": True,
        "visible": True,
        "order": 4
    }
]

# =============================================================================
# FILTER CONFIGURATION (Following financial_transactions.py pattern)
# =============================================================================

PURCHASE_ORDER_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'po_date': FilterCategory.DATE,
    'expected_delivery_date': FilterCategory.DATE,
    'date_range': FilterCategory.DATE,
    'created_at': FilterCategory.DATE,
    
    # Amount filters
    'total_amount': FilterCategory.AMOUNT,
    'amount_range': FilterCategory.AMOUNT,
    
    # Search filters
    'search': FilterCategory.SEARCH,
    'po_number': FilterCategory.SEARCH,
    'supplier_name': FilterCategory.SEARCH,
    'quotation_id': FilterCategory.SEARCH,
    
    # Selection filters
    'status': FilterCategory.SELECTION,  # ✅ Standardized
    'po_status': FilterCategory.SELECTION,
    'currency_code': FilterCategory.SELECTION,
    
    # Relationship filters (using RELATIONSHIP category like financial_transactions.py)
    'supplier_id': FilterCategory.RELATIONSHIP,
    'branch_id': FilterCategory.RELATIONSHIP
}

PURCHASE_ORDER_DEFAULT_FILTERS = {
    'financial_year': 'current',
    'status': None  # Show all statuses by default
}

PURCHASE_ORDER_CATEGORY_CONFIGS = {
    FilterCategory.DATE: {
        'default_preset': 'current_financial_year',
        'auto_apply_financial_year': True
    },
    FilterCategory.SELECTION: {
        'auto_submit': True,
        'include_empty_options': True
    },
    FilterCategory.RELATIONSHIP: {
        'lazy_load': True,
        'cache_duration': 300
    },
    FilterCategory.SEARCH: {
        'min_search_length': 2,
        'auto_submit': False
    }
}

# =============================================================================
# PERMISSIONS CONFIGURATION
# =============================================================================

PURCHASE_ORDER_PERMISSIONS = {
    "list": "purchase_order_list",
    "view": "purchase_order_view",
    "create": "purchase_order_create",
    "edit": "purchase_order_edit",
    "delete": "purchase_order_delete",
    "approve": "purchase_order_approve",
    "cancel": "purchase_order_cancel",
    "export": "purchase_order_export",
    "bulk": "purchase_order_bulk"
}

# =============================================================================
# DOCUMENT CONFIGURATIONS
# =============================================================================

PURCHASE_ORDER_DOCUMENT = DocumentConfiguration(
    enabled=True,
    document_type="invoice",  # Changed from "order" to valid type
    title="Purchase Order",
    subtitle="Official Purchase Order",
    
    # Page settings
    page_size="A4",  # Fixed: Use string instead of enum
    orientation="portrait",  # Fixed: Use lowercase string instead of enum
    margins={"top": 20, "bottom": 20, "left": 15, "right": 15},
    
    # Layout
    print_layout_type="simple_with_header",  # Fixed: Use string instead of enum
    show_logo=True,
    show_company_info=True,
    show_footer=True,
    
    # Content control - updated to match new tab names
    visible_tabs=["order_details", "financials", "line_items"],
    visible_sections=["identification", "supplier_info", "dates", "amounts"],
    
    # Header/Footer
    header_text="PURCHASE ORDER",
    footer_text="This is a system generated document - Page {page}",
    
    # Signatures
    signature_fields=[
        {"label": "Prepared By", "width": "200px"},
        {"label": "Verified By", "width": "200px"},
        {"label": "Approved By", "width": "200px"}
    ],
    
    # Export options - using strings not enums
    allowed_formats=["pdf", "print", "excel", "word"],
    default_format="pdf"
)

PURCHASE_ORDER_LIST_DOCUMENT = DocumentConfiguration(
    enabled=True,
    document_type="report",  # Changed from "list" to valid type
    title="Purchase Orders List",
    
    page_size="A4",  # Fixed: Use string instead of enum
    orientation="landscape",  # Fixed: Use lowercase string instead of enum
    
    print_layout_type="simple",  # Fixed: Use lowercase string instead of enum
    show_logo=False,
    show_company_info=False,
    show_footer=False,
    
    # Export options - using strings not enums
    allowed_formats=["excel", "csv", "pdf"],
    default_format="excel"
)

# Document configs dictionary
PURCHASE_ORDER_DOCUMENT_CONFIGS = {
    "invoice": PURCHASE_ORDER_DOCUMENT,  # Changed key from "order" to match document_type
    "report": PURCHASE_ORDER_LIST_DOCUMENT  # Changed key from "list" to match document_type
}

# =============================================================================
# MAIN ENTITY CONFIGURATION
# =============================================================================

PURCHASE_ORDER_CONFIG = EntityConfiguration(
    # === BASIC INFORMATION ===
    entity_type="purchase_orders",
    name="Purchase Order",
    plural_name="Purchase Orders",
    service_name="purchase_orders",
    table_name="purchase_orders_view",
    primary_key="po_id",
    title_field="po_number",
    subtitle_field="supplier_name",
    icon="fas fa-file-invoice",
    
    # === ENTITY CATEGORY ===
    entity_category=EntityCategory.TRANSACTION,
    
    # === MODEL CLASS ===
    # model_class="app.models.views.PurchaseOrderView",
    
    # === LIST VIEW CONFIGURATION ===
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    page_title="Purchase Orders",
    description="View and manage purchase orders",
    searchable_fields=["po_number", "quotation_id"],
    default_sort_field="po_date",
    default_sort_direction="desc",
    
    # === CORE CONFIGURATION REFERENCES ===
    fields=PURCHASE_ORDER_FIELDS,
    view_layout=PURCHASE_ORDER_VIEW_LAYOUT,
    section_definitions=PURCHASE_ORDER_SECTIONS,
    actions=PURCHASE_ORDER_ACTIONS,
    summary_cards=PURCHASE_ORDER_SUMMARY_CARDS,
    permissions=PURCHASE_ORDER_PERMISSIONS,
    
    # === FILTER CONFIGURATION ===
    filter_category_mapping=PURCHASE_ORDER_FILTER_CATEGORY_MAPPING,
    default_filters=PURCHASE_ORDER_DEFAULT_FILTERS,
    category_configs=PURCHASE_ORDER_CATEGORY_CONFIGS,
    
    # === DATE AND AMOUNT CONFIGURATION ===
    primary_date_field="po_date",
    primary_amount_field="total_amount",
    
    # === DOCUMENT GENERATION SUPPORT ===
    document_enabled=True,
    document_configs=PURCHASE_ORDER_DOCUMENT_CONFIGS,
    default_document="invoice",  # Changed from "order" to match document_type
    
    # ✅ ENABLE SOFT DELETE SUPPORT
    enable_soft_delete=True,  # Changed from False
    soft_delete_field="is_deleted",  # Standard SoftDeleteMixin field
    cascade_delete=["po_lines"],  # Cascade to line items
    delete_confirmation_message="Are you sure you want to delete this purchase order? This will also delete all line items.",

    # === UNIVERSAL CRUD SETTINGS ===
    universal_crud_enabled=False,  # Transaction entity - read-only in Universal Engine
    allowed_operations=[
        CRUDOperation.READ,
        CRUDOperation.LIST,
        CRUDOperation.DELETE,  # ✅ NOW ALLOWED via soft delete
        CRUDOperation.EXPORT,
        CRUDOperation.DOCUMENT
    ],
    
    # === CALCULATED FIELDS FOR DISPLAY AND DOCUMENTS ===
    include_calculated_fields=[
        "supplier_name",
        "supplier_category",
        "supplier_address",
        "supplier_gst",
        "supplier_email",
        "line_count",
        "items_summary",
        "gst_summary",
        "amount_in_words",
        "branch_name",
        "has_invoice",      # For action conditions
        "invoice_count",    # For display
        "approval_status",  # ✅ NEW: For approval tracking
        "can_be_deleted",   # ✅ NEW: For action visibility
        "can_be_approved",  # ✅ NEW: For action visibility
        "can_be_unapproved" # ✅ NEW: For action visibility
    ],
    
    # === DOCUMENT PERMISSIONS ===
    document_permissions={
        "invoice": "purchase_order_view",  # Changed key from "order"
        "report": "purchase_order_list"    # Changed key from "list"
    }
)

# =============================================================================
# ENTITY FILTER CONFIGURATION
# =============================================================================

PURCHASE_ORDER_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='purchase_orders',
    filter_mappings={
        'po_status': {
            'field': 'po_status',  
            'type': 'select',   
            'options': [
                {'value': 'draft', 'label': 'Draft'},
                {'value': 'pending', 'label': 'Pending'},
                {'value': 'approved', 'label': 'Approved'},
                {'value': 'partially_received', 'label': 'Partially Received'},
                {'value': 'received', 'label': 'Received'},
                {'value': 'cancelled', 'label': 'Cancelled'}
            ]
        },
        # The filter panel uses simple text search, not entity_dropdown
        'supplier_name': {
            'field': 'supplier_name',
            'type': 'text',  # ⭐ IMPORTANT: Use 'text' type for filter panel
            'label': 'Supplier Name',
            'placeholder': 'Search supplier name...',
            'search_in_view': True  # ⭐ Search in view column
        },
        'supplier_id': {
            'field': 'supplier_id',
            'type': 'entity_search',
            'entity_type': 'suppliers',
            'display_field': 'supplier_name',
            'search_fields': ['supplier_name', 'contact_person_name'],
            'placeholder': 'Search suppliers...',
            'label': 'Supplier'  # Add label for UI
        },
        'currency_code': {
            'field': 'currency_code',
            'type': 'select',
            'options': [
                {'value': 'INR', 'label': 'INR'},
                {'value': 'USD', 'label': 'USD'},
                {'value': 'EUR', 'label': 'EUR'},
                {'value': 'GBP', 'label': 'GBP'}
            ]
        },
        'po_date': {
            'field': 'po_date',
            'type': 'date_range',
            'label': 'PO Date Range'
        },
        'expected_delivery_date': {
            'field': 'expected_delivery_date',
            'type': 'date_range',
            'label': 'Expected Delivery'
        }
    }
)
def get_dynamic_filter_options(field_name: str) -> List[Dict]:
    """Get dynamic options for filter fields"""
    if field_name == 'status':
        # Find status field in PURCHASE_ORDER_FIELDS
        for field in PURCHASE_ORDER_FIELDS:
            if field.name == 'status' and field.options:
                return field.options
    return []
# =============================================================================
# ENTITY SEARCH CONFIGURATION
# =============================================================================

PURCHASE_ORDER_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='purchase_orders',
    search_fields=['po_number', 'supplier_name', 'quotation_id'], 
    display_template='{po_number} - {supplier_name}',
    # model_path='app.models.views.PurchaseOrderView',
    min_chars=1,
    max_results=10,
    sort_field='po_date'
)

# =============================================================================
# SIMPLIFIED EXPORTS - Direct pattern like supplier_config.py
# =============================================================================

# Direct exports - no functions needed!
config = PURCHASE_ORDER_CONFIG
filter_config = PURCHASE_ORDER_ENTITY_FILTER_CONFIG
search_config = PURCHASE_ORDER_SEARCH_CONFIG