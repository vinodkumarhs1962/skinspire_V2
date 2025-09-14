# Supplier Configuration Module
# File: app/config/modules/supplier_config.py

"""
Supplier Configuration - Single Entity Per File
Direct export pattern - no registration functions needed
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition, 
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration, ButtonType,
    ComplexDisplayType, ActionDisplayType, INDIAN_STATES, FilterType,
    DocumentConfiguration, PrintLayoutType, DocumentType,
    PageSize, Orientation, DocumentSectionType, ExportFormat,
    EntityCategory, CRUDOperation, FilterOperator, CustomRenderer  # Added for transaction history custom rendering
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
        section="basic_info",
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
        filterable=False,
        required=True,
        autocomplete_enabled=True,
        autocomplete_source="backend",
        tab_group="profile",  # Changed from basic_info
        section="basic_info",
        view_order=1
    ),
    
    # ========== BASIC INFORMATION ==========
    FieldDefinition(
        name="supplier_name",
        label="Supplier Name",
        field_type=FieldType.TEXT,
        
        # Keep existing display properties
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        sortable=True,
        required=True,
        searchable=False,
        placeholder="Search supplier name...",
        
        # Enhanced filter properties
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,  # ⭐ ADD THIS
        filter_operator=FilterOperator.CONTAINS,
        
        # ⭐ ADD THIS ENTIRE BLOCK
        entity_search_config=EntitySearchConfiguration(
            target_entity='suppliers',  # Self-reference
            search_fields=['supplier_name', 'contact_person_name'],
            display_template='{supplier_name}',
            value_field='supplier_name',
            filter_field='supplier_name',
            placeholder="Type to search suppliers...",
            min_chars=2,
            max_results=20,
            preload_common=True,
            cache_results=True,
            additional_filters={'status': 'active'}
        ),
        
        # Keep existing layout properties
        tab_group="profile",
        section="basic_info",
        view_order=1
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
        section="basic_info",
        tab_group="profile",
        view_order=2
    ),
    FieldDefinition(
        name="contact_person_name",
        label="Contact Person",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        filterable=False,
        sortable=True,
        required=True,
        placeholder="Enter contact person name",
        section="basic_info",
        tab_group="profile",
        view_order=3
    ),
    
    # ========== CONTACT INFO VIRTUAL FIELDS (contact_info JSONB) ==========
    FieldDefinition(
        name="phone",
        label="Phone",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        virtual=True,
        virtual_target="contact_info",
        virtual_key="phone",
        required=False,  # Not mandatory
        placeholder="Enter phone number",
        validation_pattern=r'^[0-9]{10}$',
        section="contact_info",
        tab_group="profile",
        view_order=1
    ),
    FieldDefinition(
        name="mobile",
        label="Mobile",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="contact_info",
        virtual_key="mobile",
        required=True,  # MANDATORY (Issue #5)
        placeholder="Enter 10-digit mobile number",
        validation_pattern=r'^[6-9][0-9]{9}$',  # Indian mobile validation
        help_text="Enter 10-digit mobile starting with 6-9",
        section="contact_info",
        tab_group="profile",
        view_order=2
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
        required=False,
        placeholder="Enter email address",
        validation_pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',  # Issue #8
        help_text="Enter valid email address",
        section="contact_info",
        tab_group="profile",
        view_order=3
    ),
    FieldDefinition(
        name="fax",
        label="Fax",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="contact_info",
        virtual_key="fax",
        placeholder="Enter fax number",
        section="contact_info",
        tab_group="profile",
        view_order=4
    ),
    
    # ========== ADDRESS VIRTUAL FIELDS (supplier_address JSONB) ==========
    FieldDefinition(
        name="address",
        label="Street Address",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="supplier_address",
        virtual_key="address",
        placeholder="Enter street address",
        section="address_info",
        tab_group="profile",
        view_order=1
    ),
    FieldDefinition(
        name="city",
        label="City",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        virtual=True,
        virtual_target="supplier_address",
        virtual_key="city",
        placeholder="Enter city",
        section="address_info",
        tab_group="profile",
        view_order=2
    ),
    FieldDefinition(
        name="state",
        label="State",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="supplier_address",
        virtual_key="state",
        placeholder="Enter state",
        section="address_info",
        tab_group="profile",
        view_order=3
    ),
    FieldDefinition(
        name="country",
        label="Country",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="supplier_address",
        virtual_key="country",
        placeholder="Enter country",
        default_value="India",
        section="address_info",
        tab_group="profile",
        view_order=4
    ),
    FieldDefinition(
        name="pincode",
        label="Pincode",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="supplier_address",
        virtual_key="pincode",
        placeholder="Enter 6-digit pincode",
        validation_pattern=r'^\d{6}$',
        help_text="Enter 6-digit pincode",
        section="address_info",
        tab_group="profile",
        view_order=5
    ),
    
    # ========== MANAGER CONTACT VIRTUAL FIELDS (manager_contact_info JSONB) ==========
    FieldDefinition(
        name="manager_name",
        label="Manager Name",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        placeholder="Enter manager name",
        section="manager_info",
        tab_group="business_info",
        view_order=1
    ),
    FieldDefinition(
        name="manager_phone",
        label="Manager Phone",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="manager_contact_info",
        virtual_key="phone",
        placeholder="Enter manager phone",
        section="manager_info",
        tab_group="business_info",
        view_order=2
    ),
    FieldDefinition(
        name="manager_mobile",
        label="Manager Mobile",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="manager_contact_info",
        virtual_key="mobile",
        placeholder="Enter manager mobile",
        section="manager_info",
        tab_group="business_info",
        view_order=3
    ),
    FieldDefinition(
        name="manager_email",
        label="Manager Email",
        field_type=FieldType.EMAIL,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="manager_contact_info",
        virtual_key="email",
        placeholder="Enter manager email",
        validation_pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        section="manager_info",
        tab_group="business_info",
        view_order=4
    ),
    
    # ========== BANK DETAILS VIRTUAL FIELDS (bank_details JSONB) ==========
    FieldDefinition(
        name="bank_name",
        label="Bank Name",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="bank_details",
        virtual_key="bank_name",
        placeholder="Enter bank name",
        section="banking_info",
        tab_group="business_info",
        view_order=1
    ),
    FieldDefinition(
        name="bank_account_name",
        label="Account Name",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="bank_details",
        virtual_key="account_name",
        placeholder="Enter account holder name",
        section="banking_info",
        tab_group="business_info",
        view_order=2
    ),
    FieldDefinition(
        name="bank_account_number",
        label="Account Number",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="bank_details",
        virtual_key="account_number",
        placeholder="Enter account number",
        section="banking_info",
        tab_group="business_info",
        view_order=3
    ),
    FieldDefinition(
        name="ifsc_code",
        label="IFSC Code",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="bank_details",
        virtual_key="ifsc_code",
        placeholder="Enter IFSC code",
        validation_pattern=r'^[A-Z]{4}0[A-Z0-9]{6}$',  # Issue #8
        help_text="Format: 4 letters, 0, then 6 alphanumeric",
        section="banking_info",
        tab_group="business_info",
        view_order=4
    ),
    FieldDefinition(
        name="bank_branch",
        label="Bank Branch",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        virtual=True,
        virtual_target="bank_details",
        virtual_key="branch",
        placeholder="Enter bank branch",
        section="banking_info",
        tab_group="business_info",
        view_order=5
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
        filterable=False,
        placeholder="Enter GST registration number",
        validation_pattern=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',  # Issue #8
        help_text="Format: 2 digits, 5 letters, 4 digits, 1 letter, 1 char, Z, 1 char",
        section="tax_info",
        tab_group="business_info",
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
        help_text="Format: 5 letters, 4 digits, 1 letter",
        section="tax_info",
        tab_group="business_info",
        view_order=2
    ),
    FieldDefinition(
        name="tax_type",
        label="Tax Type",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=False,
        options=[
            {"value": "regular", "label": "Regular"},
            {"value": "composition", "label": "Composition"},
            {"value": "unregistered", "label": "Unregistered"}
        ],
        section="tax_info",
        tab_group="business_info",
        view_order=3
    ),
    FieldDefinition(
        name="state_code",
        label="State",
        field_type=FieldType.SELECT,  # Issue #9: Dropdown
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=False,
        virtual=False,
        required=True,  
        options=INDIAN_STATES,  # Use state list
        placeholder="Select state",
        section="tax_info",
        tab_group="business_info",
        view_order=4
    ),
    
    # ========== BUSINESS RULES ==========
    FieldDefinition(
        name="payment_terms",
        label="Payment Terms",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        options=[
            {"value": "immediate", "label": "Immediate"},
            {"value": "7_days", "label": "7 Days"},
            {"value": "15_days", "label": "15 Days"},
            {"value": "30_days", "label": "30 Days"},
            {"value": "45_days", "label": "45 Days"},
            {"value": "60_days", "label": "60 Days"},
            {"value": "90_days", "label": "90 Days"}
        ],
        section="business_rules",
        tab_group="business_info",
        view_order=1
    ),
    FieldDefinition(
        name="performance_rating",
        label="Performance Rating",
        field_type=FieldType.SELECT,  # Issue #4: Changed to dropdown
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=False,
        options=[
            {"value": "1", "label": "1 - Poor"},
            {"value": "2", "label": "2 - Below Average"},
            {"value": "3", "label": "3 - Average"},
            {"value": "4", "label": "4 - Good"},
            {"value": "5", "label": "5 - Excellent"}
        ],
        default_value="3",
        section="business_rules",
        tab_group="business_info",
        view_order=2
    ),
    FieldDefinition(
        name="black_listed",
        label="Blacklisted",
        field_type=FieldType.BOOLEAN,  # Issue #3: Already correct
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=False,
        default_value=False,
        help_text="Check if supplier is blacklisted",
        section="business_rules",
        tab_group="business_info",
        view_order=3
    ),
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.STATUS_BADGE,  # Change from SELECT to STATUS_BADGE
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,  # Issue #2: Don't show in create form
        show_in_edit=True,   # But show in edit form
        filterable=True,
        sortable=True,
        required=True,
        options=[
            {"value": "active", "label": "Active"},
            {"value": "inactive", "label": "Inactive"},
            {"value": "pending", "label": "Pending Approval"}
        ],
        default_value="active",
        section="business_rules",
        tab_group="business_info",
        view_order=4
    ),
    FieldDefinition(
        name="remarks",
        label="Remarks",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        placeholder="Enter any remarks or notes",
        section="business_rules",
        tab_group="business_info",
        view_order=5
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
        name="total_purchases",
        label="Total Purchases",
        field_type=FieldType.CURRENCY,
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
        field_type=FieldType.CURRENCY,
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
        columns_span=12,
        custom_renderer=CustomRenderer(
            template="components/business/payment_history_table.html",
            context_function="get_supplier_payment_history_6months",
            css_classes="table-responsive payment-history-table"
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
        field_type=FieldType.CURRENCY, 
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
        field_type=FieldType.CURRENCY, 
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
        field_type=FieldType.CURRENCY, 
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

SUPPLIER_FORM_SECTIONS = {
    # Basic Information Section
    "basic_info": SectionDefinition(
        key="basic_info",
        title="Basic Information",
        icon="fas fa-info-circle",
        columns=2,
        order=1,
        collapsible=False,
        default_collapsed=False
    ),
    
    # Contact Information Section
    "contact_info": SectionDefinition(
        key="contact_info",
        title="Contact Information",
        icon="fas fa-phone",
        columns=2,
        order=2,
        collapsible=True,
        default_collapsed=False
    ),
    
    # Address Section
    "address_info": SectionDefinition(
        key="address_info",
        title="Address Details",
        icon="fas fa-map-marker-alt",
        columns=2,
        order=3,
        collapsible=True,
        default_collapsed=False
    ),
    
    # Manager Contact Section
    "manager_info": SectionDefinition(
        key="manager_info",
        title="Manager Information",
        icon="fas fa-user-tie",
        columns=2,
        order=4,
        collapsible=True,
        default_collapsed=True
    ),
    
    # Banking Section
    "banking_info": SectionDefinition(
        key="banking_info",
        title="Banking Details",
        icon="fas fa-university",
        columns=2,
        order=5,
        collapsible=True,
        default_collapsed=True
    ),
    
    # Tax/Compliance Section
    "tax_info": SectionDefinition(
        key="tax_info",
        title="Tax & Compliance",
        icon="fas fa-file-invoice",
        columns=2,
        order=6,
        collapsible=True,
        default_collapsed=False
    ),
    
    # Business Rules Section
    "business_rules": SectionDefinition(
        key="business_rules",
        title="Business Rules & Settings",
        icon="fas fa-cogs",
        columns=2,
        order=7,
        collapsible=True,
        default_collapsed=True
    ),
    "audit_info": SectionDefinition(
        key="audit_info",
        title="Audit Information",
        icon="fas fa-history",
        columns=2,
        order=8,
        collapsible=True,
        default_collapsed=True
    ),
    "technical_info": SectionDefinition(
        key="technical_info",
        title="Technical Details",
        icon="fas fa-server",
        columns=2,
        order=9,
        collapsible=True,
        default_collapsed=True
    ),
    "payment_history": SectionDefinition(
        key="payment_history",
        title="Payment History (Last 12 Months)",
        icon="fas fa-clock",
        columns=1,  # Full width for table
        order=10,
        collapsible=False,
        default_collapsed=False
    ),
    "invoice_history": SectionDefinition(
        key="invoice_history",
        title="Recent Supplier Invoices",
        icon="fas fa-file-invoice",
        columns=1,  # Full width for table
        order=11,
        collapsible=False,
        default_collapsed=False
    ),
    "balance_summary": SectionDefinition(
        key="balance_summary",
        title="Balance Summary",
        icon="fas fa-balance-scale",
        columns=2,
        order=12,
        collapsible=False,
        default_collapsed=False
    )
}

# For backward compatibility, alias SUPPLIER_SECTIONS to SUPPLIER_FORM_SECTIONS
SUPPLIER_SECTIONS = SUPPLIER_FORM_SECTIONS

# =============================================================================
# TAB DEFINITIONS - NOW USING UNIFIED SECTIONS
# =============================================================================

SUPPLIER_TABS = {
    'profile': TabDefinition(
        key='profile',
        label='Profile',
        icon='fas fa-user-circle',
        sections={
            # Now using the same section keys as form sections!
            'basic_info': SUPPLIER_FORM_SECTIONS['basic_info'],
            'contact_info': SUPPLIER_FORM_SECTIONS['contact_info'],
            'address_info': SUPPLIER_FORM_SECTIONS['address_info']
        },
        order=0,
        default_active=True
    ),
    'business_info': TabDefinition(
        key='business_info',
        label='Business Information',
        icon='fas fa-briefcase',
        sections={
            'manager_info': SUPPLIER_FORM_SECTIONS['manager_info'],
            'banking_info': SUPPLIER_FORM_SECTIONS['banking_info'],
            'tax_info': SUPPLIER_FORM_SECTIONS['tax_info'],
            'business_rules': SUPPLIER_FORM_SECTIONS['business_rules']
        },
        order=1
    ),
    'system_info': TabDefinition(
        key='system_info',
        label='System Information',
        icon='fas fa-cogs',
        sections={
            'audit_info': SUPPLIER_FORM_SECTIONS['audit_info'],
            'technical_info': SUPPLIER_FORM_SECTIONS['technical_info']
        },
        order=2
    ),
    'transaction_history': TabDefinition(
        key='transaction_history',
        label='Transaction History',
        icon='fas fa-history',
        sections={
            'payment_history': SUPPLIER_FORM_SECTIONS['payment_history'],
            'invoice_history': SUPPLIER_FORM_SECTIONS['invoice_history'],
            'balance_summary': SUPPLIER_FORM_SECTIONS['balance_summary']
        },
        order=3,  # Proper order instead of 999
        default_active=False
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
        'supplier_name': {
            'field': 'supplier_name',
            'type': 'text',  # Simple text search in filter panel
            'label': 'Supplier Name',
            'placeholder': 'Search supplier name...',
            'search_in_table': True  # Direct table search
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
    # model_path='app.models.master.Supplier',
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
    searchable_fields=["contact_person_name", "email", "gst_registration_number"], 
    default_sort_field="supplier_name",
    default_sort_direction="asc",
    
    # ========== CORE CONFIGURATIONS ==========
    fields=SUPPLIER_FIELDS,
    section_definitions=SUPPLIER_FORM_SECTIONS,  # Used by view
    form_section_definitions=SUPPLIER_FORM_SECTIONS,  # Used by forms
    actions=SUPPLIER_ACTIONS,
    summary_cards=SUPPLIER_SUMMARY_CARDS,
    permissions=SUPPLIER_PERMISSIONS,
    
    # ========== OPTIONAL CONFIGURATIONS ==========
    # model_class="app.models.master.Supplier",
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    
    # View Layout Configuration
    view_layout=SUPPLIER_VIEW_LAYOUT,
    # section_definitions=SUPPLIER_SECTIONS,
    
    # Filter Configuration
    filter_category_mapping=SUPPLIER_FILTER_CATEGORY_MAPPING,
    default_filters=SUPPLIER_DEFAULT_FILTERS,
    category_configs=SUPPLIER_CATEGORY_CONFIGS,
    
    # Date and Amount Fields
    primary_date_field="created_at",
    primary_amount_field=None,  # Suppliers don't have a primary amount field
    
    # Entity Classification (matches registry)
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
    
    # Model Configuration (matches registry)
    # model_class_path="app.models.master.Supplier",
    primary_key_field="supplier_id",
    soft_delete_field="is_deleted",  # If you have soft delete
    
    # Form Configuration
    create_form_template="engine/universal_create.html",
    edit_form_template="engine/universal_edit.html",
    
    # Simple service delegation - just specify the module
    # service_module='app.services.supplier_service_CRUD',
    # Convention: expects create_supplier, update_supplier, delete_supplier
    
    # Default values for fields when using generic CRUD
    default_field_values={
        'status': 'active',
        'black_listed': False,
        'performance_rating': '3'  # Middle rating as default
    },

    # CRUD Field Control - Fields shown in create/edit forms
    create_fields=[
        # Basic Info
        "supplier_name",
        "supplier_category",
        "contact_person_name",
        
        # Contact Virtual Fields (contact_info JSONB)
        "phone",
        "mobile",
        "fax",
        "email",  # Direct column
        
        # Address Virtual Fields (supplier_address JSONB)
        "address",
        "city",
        "state",
        "country",
        "pincode",
        
        # Manager Info
        "manager_name",  # Direct column
        "manager_phone",  # Virtual -> manager_contact_info
        "manager_mobile",  # Virtual -> manager_contact_info
        "manager_email",  # Virtual -> manager_contact_info
        
        # Bank Virtual Fields (bank_details JSONB)
        "bank_name",
        "bank_account_name",
        "bank_account_number",
        "ifsc_code",
        "bank_branch",
        
        # Tax Info (Direct columns)
        "gst_registration_number",
        "pan_number",
        "tax_type",
        "state_code",
        
        # Business Rules (Direct columns)
        "payment_terms",
        "performance_rating",
        "black_listed",
        "remarks"
    ],
    
    edit_fields=[  # Same as create but might exclude some system fields
        # Basic Info
        "supplier_name",
        "supplier_category",
        "contact_person_name",
        
        # Contact Virtual Fields (contact_info JSONB)
        "phone",
        "mobile",
        "fax",
        "email",  # Direct column
        
        # Address Virtual Fields (supplier_address JSONB)
        "address",
        "city",
        "state",
        "country",
        "pincode",
        
        # Manager Info
        "manager_name",  # Direct column
        "manager_phone",  # Virtual -> manager_contact_info
        "manager_mobile",  # Virtual -> manager_contact_info
        "manager_email",  # Virtual -> manager_contact_info
        
        # Bank Virtual Fields (bank_details JSONB)
        "bank_name",
        "bank_account_name",
        "bank_account_number",
        "ifsc_code",
        "bank_branch",
        
        # Tax Info (Direct columns)
        "gst_registration_number",
        "pan_number",
        "tax_type",
        "state_code",
        
        # Business Rules (Direct columns)
        "payment_terms",
        "performance_rating",
        "black_listed",
        "status",
        "remarks"
    ],
    
    readonly_fields=[  # Fields that are never editable
        "supplier_id",
        "hospital_id",
        "branch_id",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
        "total_purchases",      # Calculated
        "outstanding_balance",   # Calculated
        "last_payment_date"     # Calculated
    ],
    
    # Validation Rules
    unique_fields=["gst_number", "pan_number"],
    required_fields=[
        "supplier_name",
        "contact_person_name",
        "mobile",
        "status"
    ],
    
    # CRUD Permissions
    create_permission="suppliers_create",
    edit_permission="suppliers_edit", 
    delete_permission="suppliers_delete",
    
    # Delete Configuration
    enable_soft_delete=True,
    cascade_delete=[],  # No cascading needed
    delete_confirmation_message="Are you sure you want to delete this supplier? This action cannot be undone.",
    
    # Success Messages (with field interpolation)
    create_success_message="Supplier '{supplier_name}' created successfully",
    update_success_message="Supplier '{supplier_name}' updated successfully",
    delete_success_message="Supplier deleted successfully",

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

# ========== SIMPLIFIED EXPORTS - No functions needed! ==========
config = SUPPLIER_CONFIG
filter_config = SUPPLIER_ENTITY_FILTER_CONFIG
search_config = SUPPLIER_SEARCH_CONFIG