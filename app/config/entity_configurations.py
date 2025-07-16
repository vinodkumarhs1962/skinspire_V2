"""
Complete Entity Configurations - Based on Your Actual Models
File: app/config/entity_configurations.py

Uses exact field names from your transaction.py and master.py models
Ensures compatibility with all referenced fields in universal engine code
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from app.config.field_definitions import EntitySearchConfiguration
from app.config.field_definitions import FieldDefinition, FieldType, EntityConfiguration
from app.config.filter_categories import FilterCategory


class FieldType(Enum):
    """Field types matching your model field types"""
    TEXT = "text"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    TEXTAREA = "textarea"
    STATUS_BADGE = "status_badge"
    BOOLEAN = "boolean"
    UUID = "uuid"
    REFERENCE = "reference"
    JSONB = "jsonb"
    EMAIL = "email"
    ENTITY_SEARCH = "entity_search"
    MULTI_METHOD_AMOUNT = "multi_method_amount" 

class ButtonType(Enum):
    """Button types matching your existing CSS classes"""
    PRIMARY = "btn-primary"
    OUTLINE = "btn-outline"
    WARNING = "btn-warning"
    DANGER = "btn-danger"
    SUCCESS = "btn-success"

@dataclass
class FieldDefinition:
    """Field definition based on your model fields"""
    name: str
    label: str
    field_type: FieldType
    show_in_list: bool = False
    show_in_detail: bool = True
    show_in_form: bool = True
    searchable: bool = False
    sortable: bool = False
    filterable: bool = False
    required: bool = False
    options: List[Dict] = field(default_factory=list)
    placeholder: str = ""
    help_text: str = ""
    readonly: bool = False
    related_field: Optional[str] = None  # For foreign key relationships
    autocomplete_enabled: bool = False
    autocomplete_source: Optional[str] = None
    entity_search_config: Optional[Any] = None
    # ✅ NEW: Configuration-driven filter mappings
    filter_aliases: List[str] = field(default_factory=list)  # Alternative input parameter names
    filter_type: str = "exact"  # exact, range, search, etc.

@dataclass
class EntityFilterConfiguration:
    """Configuration for entity filter dropdowns"""
    entity_type: str
    filter_mappings: Dict[str, Dict] = field(default_factory=dict)
    # Example: {'status': {'options': [{'value': 'active', 'label': 'Active'}]}}

@dataclass
class ActionDefinition:
    """Action definition for entity operations"""
    id: str
    label: str
    icon: str
    button_type: ButtonType
    route_name: Optional[str] = None      # ✅ Flask route name instead of url_pattern
    route_params: Optional[Dict] = None   # ✅ For routes that need parameters
    permission: Optional[str] = None
    confirmation_required: bool = False
    confirmation_message: str = ""
    show_in_list: bool = True
    show_in_detail: bool = True
    show_in_toolbar: bool = False  # ✅ Added missing parameter
    conditions: Optional[Dict[str, Any]] = None  # ✅ Added for advanced configuration
    custom_handler: Optional[str] = None  # ✅ Added for custom JavaScript handler
    # ✅ BACKWARD COMPATIBILITY: Support old url_pattern temporarily
    url_pattern: Optional[str] = None        # ✅ DEPRECATED: Will be removed

@dataclass
class EntityConfiguration:
    """Complete entity configuration"""
    entity_type: str
    name: str
    plural_name: str
    service_name: str
    table_name: str
    primary_key: str
    title_field: str
    subtitle_field: str
    icon: str
    page_title: str
    description: str
    searchable_fields: List[str]
    default_sort_field: str
    default_sort_direction: str
    fields: List[FieldDefinition]
    actions: List[ActionDefinition]
    summary_cards: List[Dict]
    permissions: Dict[str, str]
    filter_css_class: str = "universal-filter-card"
    table_css_class: str = "universal-data-table"
    enable_saved_filter_suggestions: bool = True
    enable_auto_submit: bool = False

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
    
    fields=[
        # Primary Key - UUID field from your model
        FieldDefinition(
            name="payment_id",  # Exact field name
            label="Payment ID",
            field_type=FieldType.UUID,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            readonly=True
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
            related_field="supplier"  # Indicates relationship join needed
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
            related_field="invoice"
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
            # ✅ CONFIGURATION-DRIVEN: Define range parameter names
            filter_aliases=["min_amount", "max_amount", "amount_min", "amount_max"],
            filter_type="range",  # Handles >= and <= operations
            required=True,
            help_text="Total payment amount"
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
            help_text="Amount paid in cash"
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
            help_text="Amount paid by cheque"
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
            help_text="Amount paid via bank transfer"
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
            readonly=True
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
            readonly=True
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
            readonly=True
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
            readonly=True
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
            route_name="supplier_views.view_payment",
            route_params={"payment_id": "{id}"}, 
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
    }
)


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

# ✅ UNIVERSAL FIX: Ensure filter_category_mapping is properly set
if not hasattr(SUPPLIER_PAYMENT_CONFIG, 'filter_category_mapping'):
    SUPPLIER_PAYMENT_CONFIG.filter_category_mapping = {}
SUPPLIER_PAYMENT_CONFIG.filter_category_mapping.update(SUPPLIER_PAYMENT_FILTER_CATEGORY_MAPPING)
SUPPLIER_PAYMENT_CONFIG.default_filters = SUPPLIER_PAYMENT_DEFAULT_FILTERS  
SUPPLIER_PAYMENT_CONFIG.category_configs = SUPPLIER_PAYMENT_CATEGORY_CONFIGS


# =============================================================================
# SUPPLIER CONFIGURATION - Based on Your Supplier Model
# =============================================================================

SUPPLIER_CONFIG = EntityConfiguration(
    entity_type="suppliers",
    name="Supplier",
    plural_name="Suppliers",
    service_name="suppliers",
    table_name="suppliers",
    primary_key="supplier_id",  # Exact field name
    title_field="supplier_name",  # Exact field name
    subtitle_field="supplier_category",  # Exact field name
    icon="fas fa-truck",
    page_title="Supplier Management",
    description="Manage suppliers and vendors",
    searchable_fields=["supplier_name", "contact_person_name", "email"],  # Exact field names
    default_sort_field="supplier_name",  # Exact field name
    default_sort_direction="asc",
    
    fields=[
        FieldDefinition(
            name="supplier_id",  # Exact field name
            label="Supplier ID",
            field_type=FieldType.UUID,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=False,
            readonly=True
        ),
        FieldDefinition(
            name="supplier_name",  # Exact field name
            label="Supplier Name",
            field_type=FieldType.TEXT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=True,
            sortable=True,
            filterable=True,
            required=True
        ),
        FieldDefinition(
            name="supplier_category",  # Exact field name
            label="Category",
            field_type=FieldType.SELECT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            options=[
                {"value": "retail_supplier", "label": "Retail Supplier"},
                {"value": "distributor", "label": "Distributor"},
                {"value": "manufacturer", "label": "Manufacturer"},
                {"value": "wholesaler", "label": "Wholesaler"}
            ]
        ),
        FieldDefinition(
            name="contact_person_name",  # Exact field name
            label="Contact Person",
            field_type=FieldType.TEXT,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=True,
            sortable=True
        ),
        FieldDefinition(
            name="email",  # Exact field name
            label="Email",
            field_type=FieldType.EMAIL,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            searchable=True
        ),
        FieldDefinition(
            name="gst_registration_number",  # Exact field name
            label="GST Number",
            field_type=FieldType.TEXT,
            show_in_list=False,
            show_in_detail=True,
            show_in_form=True,
            filterable=True
        ),
        FieldDefinition(
            name="status",  # Exact field name
            label="Status",
            field_type=FieldType.STATUS_BADGE,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            filterable=True,
            options=[
                {"value": "active", "label": "Active", "css_class": "universal-status-completed"},
                {"value": "inactive", "label": "Inactive", "css_class": "universal-status-cancelled"}
            ]
        ),
        FieldDefinition(
            name="black_listed",  # Exact field name
            label="Blacklisted",
            field_type=FieldType.BOOLEAN,
            show_in_list=True,
            show_in_detail=True,
            show_in_form=True,
            filterable=True
        )
    ],
    
    actions=[
        ActionDefinition(
            id="view",
            label="View",
            icon="fas fa-eye",
            button_type=ButtonType.OUTLINE,
            permission="suppliers_view"
        ),
        ActionDefinition(
            id="edit",
            label="Edit",
            icon="fas fa-edit",
            button_type=ButtonType.WARNING,
            permission="suppliers_edit"
        )
    ],
    
    summary_cards=[
    {
        "id": "total_count",
        "field": "total_count", 
        "label": "Total Payments",
        "icon": "fas fa-receipt",
        "icon_css": "stat-card-icon primary",  # ✅ Universal CSS class
        "type": "number",
        "filterable": False
    },
    {
        "id": "total_amount",
        "field": "total_amount",
        "label": "Total Amount", 
        "icon": "fas fa-rupee-sign",
        "icon_css": "stat-card-icon success",  # ✅ Universal CSS class
        "type": "currency",
        "filterable": False
    },
    {
        "id": "pending_count",
        "field": "pending_count",
        "label": "Pending Approval",
        "icon": "fas fa-clock", 
        "icon_css": "stat-card-icon danger",  # ✅ Universal CSS class
        "type": "number",
        "filterable": True,
        "filter_field": "workflow_status",
        "filter_value": "pending"
    },
    {
        "id": "this_month_count",
        "field": "this_month_count",
        "label": "This Month",
        "icon": "fas fa-calendar-check",
        "icon_css": "stat-card-icon primary",  # ✅ Universal CSS class
        "type": "number", 
        "filterable": True,
        "filter_field": "date_preset",
        "filter_value": "this_month"
    }
    ],
    
    permissions={
        "list": "suppliers_list",
        "view": "suppliers_view",
        "create": "suppliers_create",
        "edit": "suppliers_edit",
        "delete": "suppliers_delete",
        "export": "suppliers_export"
    }
)

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