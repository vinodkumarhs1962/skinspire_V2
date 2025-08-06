# Complete Financial Transactions Configuration Module
# File: app/config/modules/financial_transactions.py

"""
Financial Transactions Configuration Module
Contains ALL configuration for supplier payments, billing, etc.
Single source of truth - no duplication
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition, 
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition, CustomRenderer,
    EntitySearchConfiguration, FilterConfiguration,
    EntityFilterConfiguration, ButtonType, ActionDisplayType, ComplexDisplayType
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# SUPPLIER PAYMENT FIELD DEFINITIONS
# =============================================================================

SUPPLIER_PAYMENT_FIELDS = [
    # System Fields
    FieldDefinition(
        name="payment_id",
        label="Payment ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="header",
        view_order=0
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
        view_order=1
    ),
    
    # Core Payment Fields
    FieldDefinition(
        name="reference_no",
        label="Reference Number",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=False,
        show_in_form=True,
        searchable=True,
        sortable=True,
        required=True,
        placeholder="Enter payment reference",
        tab_group="payment_details",
        section="header",
        view_order=1,
        css_classes="text-2xl font-bold"
    ),
    FieldDefinition(
        name="payment_date",
        label="Payment Date",
        field_type=FieldType.DATE,
        show_in_list=True,
        show_in_detail=False,
        show_in_form=True,
        searchable=False,
        sortable=True,
        filterable=True,
        filter_aliases=["start_date", "end_date", "date_from", "date_to"],
        filter_type="date_range",
        required=True,
        tab_group="payment_details",
        section="header",
        view_order=2
    ),
    FieldDefinition(
        name="supplier_id",
        label="Supplier",
        field_type=FieldType.ENTITY_SEARCH,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=True,
        searchable=False,
        sortable=False,
        filterable=True,
        required=True,
        tab_group="supplier",
        section="supplier_details",
        view_order=1,
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
    FieldDefinition(
        name="supplier_name",
        label="Supplier",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=False,
        show_in_form=False,
        searchable=True,
        sortable=True,
        filterable=True,
        readonly=True,
        filter_aliases=["supplier_name_search", "search", "supplier_search"],
        filter_type="search",
        related_field="supplier",
        tab_group="payment_details",
        section="payment_info",
        view_order=1,
        css_classes="supplier-column",  # ✅ ADD THIS for proper styling
        complex_display_type=ComplexDisplayType.ENTITY_REFERENCE  # FIX: Add this to enable entity display
    ),
    FieldDefinition(
        name="supplier_invoice_no",
        label="Invoice Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        tab_group="invoice_details",
        section="invoice_summary",
        view_order=2
    ),
    FieldDefinition(
        name="supplier_invoice_date",
        label="Supplier Invoice Date",
        field_type=FieldType.DATE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="invoice_details",
        section="invoice_summary",
        view_order=2
    ),
    
    FieldDefinition(
        name="invoice_date_display",
        label="Invoice Date",
        field_type=FieldType.DATE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,  # VALID parameter
        related_field="invoice",  # VALID parameter
        tab_group="invoice_details",
        section="invoice_summary",
        view_order=4
    ),
    FieldDefinition(
        name="po_number_display",
        label="PO Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,  # VALID parameter
        related_field="invoice",  # VALID parameter  
        tab_group="po_details",
        section="po_summary",
        view_order=5
    ),


    # Amount Fields
    FieldDefinition(
        name="amount",
        label="Total Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=False,
        sortable=True,
        filterable=True,
        filter_aliases=["min_amount", "max_amount", "amount_min", "amount_max"],
        filter_type="range",
        required=True,
        tab_group="payment_details",  # Change from "payment"
        section="payment_summary",  # Create new section for amount summary
        view_order=5,
        format_pattern="mixed_payment_breakdown",
        css_classes="text-xl font-bold text-primary"
    ),

    FieldDefinition(
        name="payment_method",
        label="Payment Method",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=False,
        sortable=True,
        filterable=True,
        required=True,
        options=[
            {"value": "cash", "label": "Cash"},
            {"value": "cheque", "label": "Cheque"},
            {"value": "bank_transfer", "label": "Bank Transfer"},
            {"value": "upi", "label": "UPI"},
            {"value": "mixed", "label": "Mixed"}
        ],
        tab_group="payment_details",
        section="payment_summary",
        view_order=1
    ),
    
    # Payment Method Details
    FieldDefinition(
        name="payment_category",  # NEW: Added from model
        label="Payment Category",
        field_type=FieldType.SELECT,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=1,
        options=[
            {"value": "manual", "label": "Manual"},
            {"value": "gateway", "label": "Gateway"},
            {"value": "upi", "label": "UPI"},
            {"value": "bank_transfer", "label": "Bank Transfer"}
        ],
        default_value="manual"
    ),
    FieldDefinition(
        name="cash_amount",
        label="Cash Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",  # Change from "payment"
        section="cash_payment",
        view_order=2,
        conditional_display="item.payment_method == 'cash' or (item.payment_method == 'mixed' and item.cash_amount > 0)"
    ),
    FieldDefinition(
        name="cheque_amount",
        label="Cheque Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="cheque_payment",
        view_order=3,
        conditional_display="item.payment_method == 'cheque' or (item.payment_method == 'mixed' and item.cheque_amount > 0)"
    ),
    FieldDefinition(
        name="cheque_number",  # CORRECTED: exact field name from model
        label="Cheque Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="cheque_payment",
        view_order=4,
        conditional_display="item.cheque_number"
    ),
    FieldDefinition(
        name="cheque_date",
        label="Cheque Date",
        field_type=FieldType.DATE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="cheque_payment",
        view_order=5,
        conditional_display="item.cheque_date"
    ),
    FieldDefinition(
        name="bank_transfer_amount",
        label="Bank Transfer Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="bank_payment",
        view_order=6,
        conditional_display="item.payment_method == 'bank_transfer' or (item.payment_method == 'mixed' and item.bank_transfer_amount > 0)"
    ),
    FieldDefinition(
        name="bank_reference_number",  # CORRECTED: exact field name from model
        label="Bank Reference",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="bank_payment",
        view_order=7,
        conditional_display="item.bank_reference_number"
    ),
    FieldDefinition(
        name="upi_amount",
        label="UPI Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="upi_payment",
        view_order=8,
        conditional_display="item.payment_method == 'upi' or (item.payment_method == 'mixed' and item.upi_amount > 0)"
    ),
    FieldDefinition(
        name="upi_reference",
        label="UPI Reference",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="upi_payment",
        view_order=9,
        conditional_display="item.upi_reference"
    ),
    
    FieldDefinition(
        name="total_invoice_amount",
        label="Total Invoice Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,  # This is a calculated field
        tab_group="invoice_details",
        section="invoice_summary",
        view_order=4,
        help_text="Total amount from all linked invoices",
        css_classes="text-lg font-bold text-primary"
    ),

    # Submitted by field for workflow tracking
    FieldDefinition(
        name="submitted_by",
        label="Submitted By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="approval_status",
        view_order=7,
        conditional_display="item.submitted_for_approval_at"
    ),

    # Workflow last updated timestamp
    FieldDefinition(
        name="workflow_updated_at",
        label="Workflow Last Updated",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="workflow_steps",
        view_order=1,
        help_text="Last workflow status change",
        conditional_display="item.workflow_updated_at"
    ),

    # Workflow Fields
    FieldDefinition(
        name="workflow_status",
        label="Status",
        field_type=FieldType.STATUS,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        searchable=False,
        sortable=True,
        filterable=True,
        filter_aliases=["statuses", "status"],
        readonly=True,
        tab_group="workflow",
        section="approval_status",
        view_order=6
    ),
    FieldDefinition(
        name="requires_approval",  # ADDED: Missing field from model
        label="Requires Approval",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="workflow",
        section="approval_status",
        view_order=1,
        default_value=False
    ),
    FieldDefinition(
        name="approval_required",  # This was already here but let's fix the name
        label="Approval Required",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="workflow",
        section="approval_status",
        view_order=2
    ),
    FieldDefinition(
        name="next_approver_id",
        label="Next Approver",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        related_field="next_approver",
        tab_group="workflow",
        section="approval_status",
        view_order=2,
        conditional_display="item.next_approver_id"
    ),
    
    # Audit Fields
    FieldDefinition(
        name="created_at",
        label="Created At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_trail",
        view_order=2
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
        section="audit_trail",
        view_order=1
    ),
    FieldDefinition(
        name="modified_at",
        label="Modified At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system_info",
        section="audit_trail",
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
        section="audit_trail",
        view_order=4
    ),
    
    # Additional Fields
    FieldDefinition(
        name="notes",
        label="Internal Notes",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=10
    ),
    
    # TDS Fields (NEW: Added from model)
    FieldDefinition(
        name="tds_applicable",
        label="TDS Applicable",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="system_info",
        section="technical_info",
        view_order=1,
        default_value=False
    ),
    FieldDefinition(
        name="tds_rate",
        label="TDS Rate (%)",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="system_info",
        section="technical_info",
        view_order=2,
        conditional_display="item.tds_applicable",
        min_value=0,
        max_value=100,
        step=0.1,
        default_value=0
    ),
    FieldDefinition(
        name="tds_amount",
        label="TDS Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="system_info",
        section="technical_info",
        view_order=3,
        conditional_display="item.tds_applicable",
        default_value=0
    ),
    FieldDefinition(
        name="bank_name",
        label="Bank Name",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="bank_payment",
        view_order=10,
        conditional_display="item.bank_transfer_amount and item.bank_transfer_amount > 0"
    ),
    FieldDefinition(
        name="ifsc_code",
        label="IFSC Code",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="bank_payment",
        view_order=11,
        conditional_display="item.bank_transfer_amount and item.bank_transfer_amount > 0"
    ),
    FieldDefinition(
        name="upi_transaction_id",
        label="UPI Transaction ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="upi_payment",
        view_order=12,
        conditional_display="item.upi_amount and item.upi_amount > 0"
    ),

    # Cheque fields (already exist in model)
    FieldDefinition(
        name="cheque_bank",
        label="Cheque Bank",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="cheque_payment",
        view_order=13,
        conditional_display="item.cheque_amount and item.cheque_amount > 0"
    ),
    FieldDefinition(
        name="cheque_status",
        label="Cheque Status",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="cheque_payment",
        view_order=14,
        options=[
            {"value": "pending", "label": "Pending"},
            {"value": "cleared", "label": "Cleared"},
            {"value": "bounced", "label": "Bounced"},
            {"value": "cancelled", "label": "Cancelled"}
        ],
        conditional_display="item.cheque_amount and item.cheque_amount > 0"
    ),

    # Gateway payment fields
    FieldDefinition(
        name="gateway_payment_id",
        label="Gateway Payment ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="gateway_payment",
        view_order=15,
        conditional_display="item.payment_category == 'gateway'"
    ),

    # TDS fields
    FieldDefinition(
        name="tds_amount",
        label="TDS Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="system_info",
        section="technical_info",
        view_order=7,
        conditional_display="item.tds_applicable"
    ),
    FieldDefinition(
        name="tds_rate",
        label="TDS Rate (%)",
        field_type=FieldType.DECIMAL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="system_info",
        section="technical_info",
        view_order=8,
        conditional_display="item.tds_applicable"
    ),

    # Document fields - these fields ACTUALLY EXIST in SupplierPayment model
    FieldDefinition(
        name="receipt_document_path",
        label="Payment Receipt",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="documents",
        view_order=0,
        help_text="Upload payment receipt (PDF, JPG, PNG - Max 5MB)",
        validation={
            "file_extensions": [".pdf", ".jpg", ".jpeg", ".png"],
            "max_file_size": 5242880,
            "is_file_field": True
        }
    ),
    FieldDefinition(
        name="bank_statement_path",
        label="Bank Statement",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="documents",
        view_order=1,
        help_text="Upload bank statement",
        validation={
            "is_file_field": True
        }
    ),
    FieldDefinition(
        name="authorization_document_path",
        label="Authorization Document",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="documents",
        view_order=2,
        help_text="Upload authorization document",
        validation={
            "is_file_field": True
        }
    ),


    # Payment summary field for history tab
    FieldDefinition(
        name="supplier_payment_summary",
        label="Payment Summary",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="payment_history",
        section="supplier_payments",
        view_order=0,
        help_text="Summary of all payments to this supplier",
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_supplier_payment_history_6months",  # Updated function name
            css_classes="payment-history-table"
        )
    ),

    # payment breakdown
    FieldDefinition(
        name="payment_breakdown_display",
        label="Payment Breakdown",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="payment_details",
        section="payment_summary",
        view_order=20
        # custom_renderer=CustomRenderer(
        #     template="components/business/payment_breakdown.html",
        #     css_classes="payment-breakdown-widget"
        #)
    ),
    # Cash Payment Details
    FieldDefinition(
        name="cash_receipt_no",
        label="Cash Receipt Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="payment_details",
        section="cash_payment",
        view_order=2,
        conditional_display="item.payment_method == 'cash' or (item.payment_method == 'mixed' and item.cash_amount > 0)"
    ),
    
    # PO Details Fields
    FieldDefinition(
        name="purchase_order_no",
        label="PO Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="po_details",
        section="po_summary",
        view_order=0
    ),
    
    FieldDefinition(
        name="po_date",
        label="PO Date",
        field_type=FieldType.DATE,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="po_details",
        section="po_summary",
        view_order=1
    ),
    
    FieldDefinition(
        name="po_total_amount",
        label="PO Total Amount",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="po_details",
        section="po_summary",
        view_order=2
    ),
    
    FieldDefinition(
        name="po_items_display",
        label="Purchase Order Items",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="po_details",
        section="po_items",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="components/business/po_items_table.html",
            context_function="get_po_items_for_payment",
            css_classes="table-responsive po-items-table"
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
            template="components/business/invoice_items_table.html",
            context_function="get_invoice_items_for_payment",
            css_classes="table-responsive invoice-items-table"
        )
    ),
    
    # Workflow Timeline
    FieldDefinition(
        name="workflow_timeline",
        label="Workflow Steps",
        field_type=FieldType.CUSTOM,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        virtual=True,
        tab_group="workflow",
        section="workflow_steps",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="components/business/workflow_timeline.html",
            context_function="get_payment_workflow_timeline",
            css_classes="workflow-timeline"
        )
    ),
    
    # Additional approval fields
    FieldDefinition(
        name="submitted_for_approval_at",
        label="Submitted for Approval",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="approval_status",
        view_order=3,
        conditional_display="item.submitted_for_approval_at"
    ),
    
    FieldDefinition(
        name="approved_at",
        label="Approved Date",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="approval_status",
        view_order=4,
        conditional_display="item.approved_at"
    ),
    
    FieldDefinition(
        name="rejected_at",
        label="Rejected Date",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="workflow",
        section="approval_status",
        view_order=5,
        conditional_display="item.rejected_at"
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
        section="approval_status",
        view_order=6,
        conditional_display="item.rejection_reason",
        rows=3
    ),
    
    # Document verification fields
    FieldDefinition(
        name="document_verified",
        label="Documents Verified",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="documents",
        view_order=10
    ),
    
    FieldDefinition(
        name="document_verified_by",
        label="Verified By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="documents",
        view_order=11,
        conditional_display="item.document_verified"
    ),
    
    FieldDefinition(
        name="document_verified_at",
        label="Verified Date",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="payment_details",
        section="documents",
        view_order=12,
        conditional_display="item.document_verified"
    )
]

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

SUPPLIER_PAYMENT_SECTIONS = {
    'header': SectionDefinition(
        key='header',
        title='',  # No title for header section
        icon='',
        columns=1,
        order=-1,
        css_class='header-section',
        collapsible=False
    ),
    'payment_amounts': SectionDefinition(
        key='payment_amounts',
        title='Payment Summary',
        icon='fas fa-calculator',
        columns=2,
        order=1
    ),
    'payment_methods': SectionDefinition(
        key='payment_methods',
        title='Payment Method Details',
        icon='fas fa-credit-card',
        columns=2,
        order=2,
        collapsible=True,
        default_collapsed=False
    ),
    'supplier_details': SectionDefinition(
        key='supplier_details',
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
    'attachments': SectionDefinition(
        key='attachments',
        title='Documents & Attachments',
        icon='fas fa-paperclip',
        columns=1,
        order=0
    ),
    'approval_status': SectionDefinition(
        key='approval_status',
        title='Approval Status',
        icon='fas fa-check-circle',
        columns=2,
        order=0
    ),
    'audit_trail': SectionDefinition(
        key='audit_trail',
        title='Audit Information',
        icon='fas fa-history',
        columns=2,
        order=0
    ),
    'system_info': SectionDefinition(
        key='system_info',
        title='System Information',
        icon='fas fa-cog',
        columns=2,
        order=1
    ),
    'tax_details': SectionDefinition(
        key='tax_details',
        title='Tax & Deductions',
        icon='fas fa-percent',
        columns=2,
        order=0
    )
}

# =============================================================================
# TAB DEFINITIONS
# =============================================================================

SUPPLIER_PAYMENT_TABS = {
    'payment_details': TabDefinition(
        key='payment_details',
        label='Payment Details',
        icon='fas fa-money-bill-wave',
        sections={
            'payment_summary': SectionDefinition(
                key='payment_summary',
                title='Payment Information',
                icon='fas fa-credit-card',
                columns=2,
                order=0
            ),
            'balance_calculations': SectionDefinition(
                key='balance_calculations',
                title='Balance & Calculations',
                icon='fas fa-balance-scale',
                columns=2,
                order=1
            ),
                    
            'cash_payment': SectionDefinition(
                key='cash_payment',
                title='Cash Payment Details',
                icon='fas fa-money-bill',
                columns=2,
                order=2,
                conditional_display="item.payment_method == 'cash' or (item.payment_method == 'mixed' and item.cash_amount > 0)"
            ),
            'bank_payment': SectionDefinition(
                key='bank_payment',
                title='Bank Transfer Details',
                icon='fas fa-university',
                columns=2,
                order=3,
                conditional_display="item.payment_method == 'bank_transfer' or (item.payment_method == 'mixed' and item.bank_transfer_amount > 0)"
            ),
            'cheque_payment': SectionDefinition(
                key='cheque_payment',
                title='Cheque Payment Details',
                icon='fas fa-money-check',
                columns=2,
                order=4,
                conditional_display="item.payment_method == 'cheque' or (item.payment_method == 'mixed' and item.cheque_amount > 0)"
            ),
            'upi_payment': SectionDefinition(
                key='upi_payment',
                title='UPI Payment Details',
                icon='fas fa-mobile-alt',
                columns=2,
                order=5,
                conditional_display="item.payment_method == 'upi' or (item.payment_method == 'mixed' and item.upi_amount > 0)"
            ),
            'documents': SectionDefinition(
                key='documents',
                title='Payment Documents',
                icon='fas fa-paperclip',
                columns=1,
                order=6,
                conditional_display="item.receipt_document_path or item.bank_statement_path or item.authorization_document_path"
            )
        },
        order=0,
        default_active=True
    ),
    
    'po_details': TabDefinition(
        key='po_details',
        label='PO Details',
        icon='fas fa-shopping-cart',
        sections={
            'po_summary': SectionDefinition(
                key='po_summary',
                title='Purchase Order Summary',
                icon='fas fa-file-alt',
                columns=1,
                order=0
            ),
            'po_items': SectionDefinition(
                key='po_items',
                title='PO Line Items',
                icon='fas fa-list',
                columns=1,
                order=1
            )
        },
        order=1
    ),
    
    'invoice_details': TabDefinition(
        key='invoice_details',
        label='Supplier Invoice',
        icon='fas fa-file-invoice',
        sections={
            'invoice_summary': SectionDefinition(
                key='invoice_summary',
                title='Invoice Summary',
                icon='fas fa-file-invoice-dollar',
                columns=2,
                order=0
            ),
            'invoice_items': SectionDefinition(
                key='invoice_items',
                title='Invoice Line Items',
                icon='fas fa-list-ul',
                columns=1,
                order=1
            )
        },
        order=2
    ),
    
    'payment_history': TabDefinition(
        key='payment_history',
        label='Payment History',
        icon='fas fa-history',
        sections={
            'supplier_payments': SectionDefinition(
                key='supplier_payments',
                title='Last 6 Months Payment History',
                icon='fas fa-clock',
                columns=1,
                order=0
            )
        },
        order=3
    ),
    
    'workflow': TabDefinition(
        key='workflow',
        label='Workflow',
        icon='fas fa-tasks',
        sections={
            'workflow_status': SectionDefinition(
                key='workflow_status',
                title='Workflow Information',
                icon='fas fa-project-diagram',
                columns=2,  # Organize in 2 columns
                order=0,
                collapsible=False  # Keep this section always open
            ),
            'workflow_history': SectionDefinition(
                key='workflow_history',
                title='Status History',
                icon='fas fa-history',
                columns=1,  # Full width for history
                order=1,
                collapsible=True
            )
        },
        order=4
    ),
    
    'system_info': TabDefinition(
        key='system_info',
        label='System Information',
        icon='fas fa-cog',
        sections={
            'audit_trail': SectionDefinition(
                key='audit_trail',
                title='Audit Information',
                icon='fas fa-history',
                columns=2,
                order=0
            ),
            'technical_info': SectionDefinition(
                key='technical_info',
                title='Technical Details',
                icon='fas fa-code',
                columns=2,
                order=1
            )
        },
        order=5
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

SUPPLIER_PAYMENT_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    responsive_breakpoint='md',
    tabs=SUPPLIER_PAYMENT_TABS,
    default_tab='payment_details',
    sticky_tabs=True,
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=True,
    enable_export=True,
    header_config={
        "primary_field": "reference_no",
        "primary_label": "Payment Reference",
        # Title field - this appears at the top (replaces hardcoded supplier_name)
        "title_field": "supplier_name",
        "title_label": "Supplier",
        "status_field": "workflow_status",
        "secondary_fields": [
            {"field": "supplier_invoice_number", "label": "Invoice No", "icon": "fas fa-file-invoice"},  # This field exists
            {"field": "payment_id", "label": "Payment ID", "icon": "fas fa-fingerprint"},
            {"field": "payment_date", "label": "Payment Date", "icon": "fas fa-calendar", "type": "date"},
            {"field": "amount", "label": "Total Payment", "icon": "fas fa-rupee-sign", "type": "currency", "css_classes": "text-xl font-bold text-success"},
            {"field": "payment_category", "label": "Category", "icon": "fas fa-tag"}  # This field exists
        ]
    }
)

# =============================================================================
# ACTION DEFINITIONS
# =============================================================================

SUPPLIER_PAYMENT_ACTIONS = [
    ActionDefinition(
        id="create",
        label="New Payment",
        icon="fas fa-plus",
        url_pattern="/universal/{entity_type}/create",
        button_type=ButtonType.PRIMARY,
        permission="supplier_payments_create",
        show_in_list=True,
        show_in_detail=False,
        show_in_toolbar=True,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),

    # Edit action (verified route exists)
    ActionDefinition(
        id="edit",
        label="Edit Payment",
        icon="fas fa-edit",
        route_name="supplier_views.edit_payment",
        route_params={"payment_id": "{payment_id}"},
        button_type=ButtonType.PRIMARY,
        permission="supplier_payments_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=100,
        conditions={
            "workflow_status": ["draft", "pending"]
        }
    ),
    
    # View invoice action (verified route exists)
    ActionDefinition(
        id="view_invoice",
        label="View Invoice",
        icon="fas fa-file-invoice",
        route_name="supplier_views.view_supplier_invoice",
        route_params={"invoice_id": "{invoice_id}"},
        button_type=ButtonType.INFO,
        permission="supplier_payments_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        button_group="related_docs",
        order=20,
        conditional_display="item.invoice_id"
    ),
    
    # Payment list navigation (verified route exists)
    ActionDefinition(
        id="payment_list",
        label="Payment List",
        icon="fas fa-list",
        route_name="supplier_views.payment_list",
        button_type=ButtonType.OUTLINE,
        permission="supplier_payments_view",
        show_in_list=False,
        show_in_detail=True
    ),
    
    # Invoice list navigation
    ActionDefinition(
        id="invoice_list",
        label="Invoice List",
        icon="fas fa-file-invoice",
        route_name="supplier_views.supplier_invoice_list",
        button_type=ButtonType.OUTLINE,
        permission="supplier_payments_view",
        show_in_list=False,
        show_in_detail=True
    ),
    
    # Workflow actions (using url_pattern as in existing config)
    ActionDefinition(
        id="approve",
        label="Approve",
        icon="fas fa-check",
        url_pattern="/api/{entity_type}/{id}/approve",
        button_type=ButtonType.SUCCESS,
        permission="supplier_payments_approve",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=110,
        conditions={
            "workflow_status": ["pending"]
        },
        confirmation_required=True,
        confirmation_message="Are you sure you want to approve this payment?"
    ),
    ActionDefinition(
        id="reject",
        label="Reject",
        icon="fas fa-times",
        url_pattern="/api/{entity_type}/{id}/reject",
        button_type=ButtonType.DANGER,
        permission="supplier_payments_approve",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=120,
        conditions={
            "workflow_status": ["pending_approval"]
        },
        confirmation_required=True,
        confirmation_message="Are you sure you want to reject this payment?"
    ),
    
    # View PO - only show if PO exists (through invoice)
    ActionDefinition(
        id="view_po",
        label="View PO",
        icon="fas fa-file-contract",
        route_name="supplier_views.view_purchase_order",
        route_params={"po_id": "{po_id}"},
        button_type=ButtonType.INFO,
        permission="supplier_payments_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        button_group="related_docs",
        order=10,
        conditional_display="item.po_id or (item.invoice and item.invoice.po_id)"  # ✅ Check both direct and through invoice
    ),
    
    # Delete - complex condition
    ActionDefinition(
        id="delete",
        label="Delete",
        icon="fas fa-trash",
        route_name="supplier_views.delete_payment",
        route_params={"payment_id": "{payment_id}"},
        button_type=ButtonType.DANGER,
        permission="supplier_payments_delete",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=200,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this payment?",
        conditions={
            "workflow_status": ["draft", "pending", "rejected"]  # Keep for exact matching
        },
        conditional_display="item.workflow_status != 'approved' and not item.has_credit_notes"  # ✅ Additional complex logic
    ),
    
    # Create credit note - complex business rules
    ActionDefinition(
        id="credit_note",
        label="Create Credit Note",
        icon="fas fa-file-invoice-dollar",
        route_name="supplier_views.create_credit_note",
        route_params={"payment_id": "{payment_id}"},
        button_type=ButtonType.WARNING,
        permission="supplier_payments_edit",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.DROPDOWN_ITEM,
        order=140,
        conditions={
            "workflow_status": ["approved", "completed"]
        },
        conditional_display="not item.is_credit_note and not item.has_credit_notes"  # ✅ Complex business logic
    ),
    
    # Print - only for approved/completed payments
    ActionDefinition(
        id="print",
        label="Print Receipt",
        icon="fas fa-print",
        route_name="supplier_views.print_supplier_payment",
        route_params={"payment_id": "{payment_id}"},
        button_type=ButtonType.SECONDARY,
        permission="supplier_payments_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        button_group="document_ops",
        order=30,
        conditional_display="item.workflow_status in ['approved', 'completed']"  # ✅ Status check
    ),
    
    # View action for list (keep existing)
    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        route_name="universal_views.universal_detail_view",
        route_params={
            "entity_type": "supplier_payments",
            "item_id": "{payment_id}"
        },
        button_type=ButtonType.INFO,
        permission="supplier_payments_view",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        order=2
    ),
    
    # Export action
    ActionDefinition(
        id="export",
        label="Export",
        icon="fas fa-download",
        url_pattern="/universal/{entity_type}/export",
        button_type=ButtonType.OUTLINE,
        permission="supplier_payments_export",
        show_in_list=True,
        show_in_detail=False
    )
]

# =============================================================================
# SUMMARY CARDS
# =============================================================================

SUPPLIER_PAYMENT_SUMMARY_CARDS = [
    {
        "id": "total_count",  # ✅ Restored original ID
        "field": "total_count",  # ✅ Restored original field
        "label": "Total Transactions",
        "icon": "fas fa-receipt",
        "icon_css": "stat-card-icon primary",
        "type": "number",
        "filterable": True,
        "filter_field": "clear_filters",
        "filter_value": "all",
        "visible": True
    },
    {
        "id": "total_amount",  # ✅ Keep this ID
        "field": "amount",  # ✅ Restored to match service expectation
        "label": "Total Amount",
        "icon": "fas fa-rupee-sign",
        "icon_css": "stat-card-icon success",
        "type": "currency",
        "filterable": True,
        "visible": False
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
        "id": "pending_payments",  # ✅ Restored original ID
        "field": "pending_count",
        "label": "Pending Approval",
        "icon": "fas fa-clock",
        "icon_css": "stat-card-icon warning",
        "type": "number",
        "filterable": True,
        "filter_field": "workflow_status",
        "filter_value": "pending_approval",  # ✅ Changed from "pending"
        "visible": True
    },
    {
        "id": "approved_payments",  # ✅ Restored original ID
        "field": "approved_count",
        "label": "Approved",
        "icon": "fas fa-check-circle",
        "icon_css": "stat-card-icon info",
        "type": "number",
        "filterable": True,
        "filter_field": "workflow_status",
        "filter_value": "approved",
        "visible": True
    },

    {
        "id": "pending_count",  # Changed from "pending_payments"
        "field": "pending_count",
        "label": "Pending Approval",
        "icon": "fas fa-clock",
        "icon_css": "stat-card-icon warning",
        "type": "number",
        "filterable": True,
        "filter_field": "workflow_status",
        "filter_value": "pending",  # Changed from "pending_approval"
        "visible": False  # Added missing property
    },
    {
        "id": "approved_count",  # Changed from "approved_payments"
        "field": "approved_count",
        "label": "Approved",
        "icon": "fas fa-check-circle",
        "icon_css": "stat-card-icon success",
        "type": "number",
        "filterable": True,
        "filter_field": "workflow_status",
        "filter_value": "approved",
        "visible": False  # Added missing property
    },
    {
        "id": "completed_count",  # NEW - was missing
        "field": "completed_count",
        "label": "Completed",
        "icon": "fas fa-check-double",
        "icon_css": "stat-card-icon success",
        "type": "number",
        "filterable": True,
        "filter_field": "workflow_status",
        "filter_value": "completed",
        "visible": True
    },
    {
        "id": "this_month_count",  # NEW - was missing
        "field": "this_month_count",
        "label": "This Month Transactions",
        "icon": "fas fa-calendar-check",
        "icon_css": "stat-card-icon info",
        "type": "number",
        "filterable": False,  # Not filterable
        "filter_field": "date_preset",
        "filter_value": "this_month",
        "visible": True
    },
    {
        "id": "this_month_amount",  # Renamed from "monthly_payments"
        "field": "this_month_amount",
        "label": "This Month Amount",  # More descriptive
        "icon": "fas fa-calendar-alt",
        "icon_css": "stat-card-icon success",  # Changed from "info"
        "type": "currency",  # Changed from "number"
        "filterable": False,  # Changed from True
        "filter_field": "date_preset",
        "filter_value": "this_month",
        "visible": True  # Added missing property
    },
    {
        "id": "payment_breakdown",  # NEW - was missing
        "field": "payment_method_breakdown",
        "label": "Payment Breakdown",
        "icon": "fas fa-chart-pie",
        "icon_css": "stat-card-icon info",
        "type": "currency",
        "card_type": "detail",  # Special card type
        "filterable": False,
        "visible": True,
        "breakdown_fields": {
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
        "id": "bank_transfer_count",  # NEW - was missing
        "field": "bank_transfer_count",
        "label": "Bank Transfers",
        "icon": "fas fa-university",
        "icon_css": "stat-card-icon primary",
        "type": "number",
        "filterable": True,
        "filter_field": "payment_method",
        "filter_value": "bank_transfer_inclusive",
        "visible": False  # Hidden by default
    },
    {
        "id": "bank_transfer_amount",  # NEW - was missing
        "field": "bank_transfer_amount_total",
        "label": "Bank Transfers",
        "icon": "fas fa-university",
        "icon_css": "stat-card-icon info",
        "type": "currency",
        "filterable": True,
        "filter_field": "payment_method",
        "filter_value": "bank_transfer",
        "visible": False  # Hidden by default
    }
]


# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

SUPPLIER_PAYMENT_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'start_date': FilterCategory.DATE,
    'end_date': FilterCategory.DATE,
    'payment_date': FilterCategory.DATE,
    'date_from': FilterCategory.DATE,
    'date_to': FilterCategory.DATE,
    'financial_year': FilterCategory.DATE,
    
    # Amount filters
    'min_amount': FilterCategory.AMOUNT,
    'max_amount': FilterCategory.AMOUNT,
    'amount_min': FilterCategory.AMOUNT,
    'amount_max': FilterCategory.AMOUNT,
    'amount': FilterCategory.AMOUNT,
    
    # Search filters
    'supplier_name_search': FilterCategory.SEARCH,
    'search': FilterCategory.SEARCH,
    'supplier_search': FilterCategory.SEARCH,
    'reference_no': FilterCategory.SEARCH,
    'invoice_id': FilterCategory.SEARCH,
    'supplier_invoice_number': FilterCategory.SEARCH,  # CORRECTED field name
    'notes': FilterCategory.SEARCH,
    
    # Selection filters
    'workflow_status': FilterCategory.SELECTION,
    'statuses': FilterCategory.SELECTION,
    'status': FilterCategory.SELECTION,
    'payment_method': FilterCategory.SELECTION,
    'payment_methods': FilterCategory.SELECTION,
    
    # Relationship filters
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
# PERMISSIONS
# =============================================================================

SUPPLIER_PAYMENT_PERMISSIONS = {
    "list": "supplier_payments_list",
    "view": "supplier_payments_view",
    "create": "supplier_payments_create",
    "edit": "supplier_payments_edit",
    "delete": "supplier_payments_delete",
    "approve": "supplier_payments_approve",
    "reject": "supplier_payments_approve",
    "export": "supplier_payments_export",
    "bulk": "supplier_payments_bulk"
}

# =============================================================================
# COMPLETE SUPPLIER PAYMENT CONFIGURATION
# =============================================================================

SUPPLIER_PAYMENT_CONFIG = EntityConfiguration(
    # Basic Information
    entity_type="supplier_payments",
    name="Supplier Payment",
    plural_name="Supplier Payments",
    service_name="supplier_payments",
    table_name="supplier_payments",
    primary_key="payment_id",
    title_field="reference_no",
    subtitle_field="supplier_name",
    icon="fas fa-money-bill-wave",
    
    # List View Configuration
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    page_title="Supplier Payments",
    description="Manage payments to suppliers and vendors",
    searchable_fields=["reference_no", "supplier_name", "notes", "supplier_invoice_no"],  # ✅ Restored original field name  
    default_sort_field="payment_date",
    default_sort_direction="desc",
    model_class="app.models.transaction.SupplierPayment",
    
    # Core Configuration References
    fields=SUPPLIER_PAYMENT_FIELDS,
    view_layout=SUPPLIER_PAYMENT_VIEW_LAYOUT,
    section_definitions=SUPPLIER_PAYMENT_SECTIONS,
    actions=SUPPLIER_PAYMENT_ACTIONS,
    summary_cards=SUPPLIER_PAYMENT_SUMMARY_CARDS,
    permissions=SUPPLIER_PAYMENT_PERMISSIONS,
    
    # Filter Configuration
    filter_category_mapping=SUPPLIER_PAYMENT_FILTER_CATEGORY_MAPPING,
    default_filters=SUPPLIER_PAYMENT_DEFAULT_FILTERS,
    category_configs=SUPPLIER_PAYMENT_CATEGORY_CONFIGS,
    
    # Date and Amount Configuration
    primary_date_field="payment_date",
    primary_amount_field="amount"
)

# Apply additional configurations (if needed for backward compatibility)
# These are already included in the configuration above, but kept for compatibility
if not hasattr(SUPPLIER_PAYMENT_CONFIG, 'filter_category_mapping') or not SUPPLIER_PAYMENT_CONFIG.filter_category_mapping:
    SUPPLIER_PAYMENT_CONFIG.filter_category_mapping = {}
SUPPLIER_PAYMENT_CONFIG.filter_category_mapping.update(SUPPLIER_PAYMENT_FILTER_CATEGORY_MAPPING)

# =============================================================================
# ENTITY FILTER CONFIGURATION
# =============================================================================

SUPPLIER_PAYMENT_ENTITY_FILTER_CONFIG = EntityFilterConfiguration(
    entity_type='supplier_payments',
    filter_mappings={
    
        'workflow_status': {
            'options': [
                {'value': 'pending', 'label': 'Pending'},
                {'value': 'pending_approval', 'label': 'Pending Approval'},  # Keep both for compatibility
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
                {'value': 'upi', 'label': 'UPI'},
                {'value': 'mixed', 'label': 'Mixed'}
            ]
        }
    }
)

# =============================================================================
# ENTITY SEARCH CONFIGURATION
# =============================================================================

SUPPLIER_PAYMENT_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='supplier_payments',
    search_fields=['reference_no', 'supplier_name', 'supplier_invoice_number'],  # CORRECTED field name
    display_template='{reference_no} - {supplier_name}',
    model_path='app.models.transaction.SupplierPayment',
    min_chars=1,
    max_results=10,
    sort_field='reference_no'
)

# =============================================================================
# MODULE REGISTRY - ALL FINANCIAL ENTITIES
# =============================================================================

# Register all financial entity configurations
FINANCIAL_ENTITY_CONFIGS = {
    "supplier_payments": SUPPLIER_PAYMENT_CONFIG,
    # Future: Add billing, customer receipts, etc.
    # "billing": BILLING_CONFIG,
    # "customer_receipts": CUSTOMER_RECEIPT_CONFIG,
}

# Filter configurations for module
FINANCIAL_ENTITY_FILTER_CONFIGS = {
    "supplier_payments": SUPPLIER_PAYMENT_ENTITY_FILTER_CONFIG,
    # Future: Add other entity filters
}

# Search configurations for module
FINANCIAL_ENTITY_SEARCH_CONFIGS = {
    "supplier_payments": SUPPLIER_PAYMENT_SEARCH_CONFIG,
    # Future: Add other entity searches
}

# Export functions for registry
def get_module_configs():
    """Return all configurations from this module"""
    return FINANCIAL_ENTITY_CONFIGS

def get_module_filter_configs():
    """Return all filter configurations from this module"""
    return FINANCIAL_ENTITY_FILTER_CONFIGS

def get_module_search_configs():
    """Return all search configurations from this module"""
    return FINANCIAL_ENTITY_SEARCH_CONFIGS