# Master Entities Configuration Module
# File: app/config/modules/master_entities.py

"""
Master Entities Configuration Module
Contains configurations for suppliers, patients, users, etc.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition, 
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration, ButtonType
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# SUPPLIER FIELD DEFINITIONS
# =============================================================================

SUPPLIER_FIELDS = [
    # Primary Key
    FieldDefinition(
        name="supplier_id",
        label="Supplier ID", 
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True
    ),
    
    # Basic Information
    FieldDefinition(
        name="supplier_name",
        label="Supplier Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        filterable=True,  # ✅ Add this
        required=True,
        placeholder="Enter supplier name",
        filter_aliases=["search", "q", "supplier_name"],  # ✅ Add this
        filter_type="search"  # ✅ Add this
    ),
    FieldDefinition(
        name="supplier_code",
        label="Supplier Code",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        required=True,
        unique=True,
        placeholder="Enter unique supplier code"
    ),
    FieldDefinition(
        name="supplier_category",
        label="Category",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=True,
        options=[
            {"value": "medicine", "label": "Medicine Supplier"},
            {"value": "equipment", "label": "Equipment Supplier"},
            {"value": "service", "label": "Service Provider"},
            {"value": "consumable", "label": "Consumable Supplier"}
        ]
    ),
    
    # Contact Information
    FieldDefinition(
        name="contact_person_name",
        label="Contact Person",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        filterable=True,  # ✅ Add this
        placeholder="Contact person name",
        filter_aliases=["contact_person_name"],  # ✅ Add this if needed
        filter_type="search"  # ✅ Add this
    ),
    FieldDefinition(
        name="email",
        label="Email",
        field_type=FieldType.EMAIL,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        filterable=True,  # ✅ Add this
        validators=["email"],
        placeholder="supplier@example.com",
        filter_aliases=["email"],  # ✅ Add this if needed
        filter_type="search"  # ✅ Add this
    ),
    FieldDefinition(
        name="phone",
        label="Phone",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        placeholder="+91 98765 43210"
    ),
    FieldDefinition(
        name="mobile",
        label="Mobile",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        placeholder="+91 98765 43210"
    ),
    
    # Address Fields
    FieldDefinition(
        name="address_line_1",
        label="Address Line 1",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=True
    ),
    FieldDefinition(
        name="address_line_2",
        label="Address Line 2",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True
    ),
    FieldDefinition(
        name="city",
        label="City",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=True
    ),
    FieldDefinition(
        name="state",
        label="State",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=True
    ),
    FieldDefinition(
        name="postal_code",
        label="Postal Code",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        validators=["postal_code"]
    ),
    FieldDefinition(
        name="country",
        label="Country",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value="India"
    ),
    
    # Tax Information
    FieldDefinition(
        name="gstin",
        label="GSTIN",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        validators=["gstin"],
        placeholder="29ABCDE1234F1Z5"
    ),
    FieldDefinition(
        name="pan",
        label="PAN",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        validators=["pan"],
        placeholder="ABCDE1234F"
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
        ]
    ),
    
    # Payment Terms
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
        ]
    ),
    FieldDefinition(
        name="credit_limit",
        label="Credit Limit",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        default_value=0
    ),
    
    # Status Fields
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        required=True,
        default_value="active",
        options=[
            {"value": "active", "label": "Active"},
            {"value": "inactive", "label": "Inactive"},
            {"value": "pending", "label": "Pending Approval"}
        ]
    ),
    FieldDefinition(
        name="black_listed",
        label="Black Listed",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        default_value=False
    ),
    FieldDefinition(
        name="performance_rating",
        label="Performance Rating",
        field_type=FieldType.NUMBER,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        min_value=0,
        max_value=5,
        step=0.1
    ),
    
    # Additional Information
    FieldDefinition(
        name="notes",
        label="Notes",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        rows=3
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
        sortable=True
    ),
    FieldDefinition(
        name="created_by",
        label="Created By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True
    ),
    FieldDefinition(
        name="modified_at",
        label="Modified At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True
    ),
    FieldDefinition(
        name="modified_by",
        label="Modified By",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True
    )
]

# =============================================================================
# SUPPLIER ACTIONS
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
        show_in_detail=False
    ),
    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        url_pattern="/universal/{entity_type}/view/{id}",
        button_type=ButtonType.INFO,
        permission="suppliers_view",
        show_in_list=True,
        show_in_detail=False
    ),
    ActionDefinition(
        id="edit",
        label="Edit",
        icon="fas fa-edit",
        url_pattern="/universal/{entity_type}/edit/{id}",
        button_type=ButtonType.SECONDARY,
        permission="suppliers_edit",
        show_in_list=False,
        show_in_detail=True,
        conditions={
            "status": ["active", "inactive", "pending"]
        }
    ),
    ActionDefinition(
        id="activate",
        label="Activate",
        icon="fas fa-check",
        url_pattern="/api/{entity_type}/{id}/activate",
        button_type=ButtonType.SUCCESS,
        permission="suppliers_edit",
        show_in_list=False,
        show_in_detail=True,
        conditions={
            "status": ["inactive", "pending"]
        },
        confirmation_required=True,
        confirmation_message="Are you sure you want to activate this supplier?"
    ),
    ActionDefinition(
        id="deactivate",
        label="Deactivate",
        icon="fas fa-ban",
        url_pattern="/api/{entity_type}/{id}/deactivate",
        button_type=ButtonType.WARNING,
        permission="suppliers_edit",
        show_in_list=False,
        show_in_detail=True,
        conditions={
            "status": ["active"]
        },
        confirmation_required=True,
        confirmation_message="Are you sure you want to deactivate this supplier? This will prevent new orders."
    ),
    ActionDefinition(
        id="blacklist",
        label="Blacklist",
        icon="fas fa-times-circle",
        url_pattern="/api/{entity_type}/{id}/blacklist",
        button_type=ButtonType.DANGER,
        permission="suppliers_edit",
        show_in_list=False,
        show_in_detail=True,
        conditions={
            "black_listed": [False, "false", None, ""]
        },
        confirmation_required=True,
        confirmation_message="Are you sure you want to blacklist this supplier? This action is serious and requires review to reverse."
    ),
    ActionDefinition(
        id="export",
        label="Export",
        icon="fas fa-download",
        url_pattern="/universal/{entity_type}/export",
        button_type=ButtonType.OUTLINE,
        permission="suppliers_export",
        show_in_list=True,
        show_in_detail=False
    )
]

# =============================================================================
# SUPPLIER SUMMARY CARDS
# =============================================================================

SUPPLIER_SUMMARY_CARDS = [
    {
        "id": "total_suppliers",
        "field": "total_count",
        "label": "Total Suppliers",
        "icon": "fas fa-truck",
        "icon_css": "stat-card-icon primary",
        "type": "number",
        "filterable": True
    },
    {
        "id": "active_suppliers",
        "field": "active_count",
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
        "field": "medicine_suppliers",
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
        "field": "blacklisted_count",
        "label": "Blacklisted",
        "icon": "fas fa-ban",
        "icon_css": "stat-card-icon danger",
        "type": "number",
        "filterable": True,
        "filter_field": "black_listed",
        "filter_value": "true"
    }
]

# =============================================================================
# SUPPLIER FILTER CONFIGURATION
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
    'gstin': FilterCategory.SEARCH,
    
    # Amount/Number filters
    'performance_rating': FilterCategory.AMOUNT,
    'credit_limit': FilterCategory.AMOUNT
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
    }
}

# =============================================================================
# SUPPLIER ENTITY FILTER CONFIGURATION
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
# SUPPLIER SEARCH CONFIGURATION
# =============================================================================

SUPPLIER_SEARCH_CONFIG = EntitySearchConfiguration(
    target_entity='suppliers',
    search_fields=['supplier_name', 'contact_person_name', 'supplier_code'],
    display_template='{supplier_name} ({supplier_code})',
    model_path='app.models.master.Supplier',
    min_chars=1,
    max_results=10,
    sort_field='supplier_name',
    additional_filters={'status': 'active'}
)

# =============================================================================
# SUPPLIER PERMISSIONS
# =============================================================================

SUPPLIER_PERMISSIONS = {
    "list": "suppliers_list",
    "view": "suppliers_view", 
    "create": "suppliers_create",
    "edit": "suppliers_edit",
    "delete": "suppliers_delete",
    "export": "suppliers_export",
    "bulk": "suppliers_bulk"
}

# =============================================================================
# COMPLETE SUPPLIER CONFIGURATION
# =============================================================================

SUPPLIER_CONFIG = EntityConfiguration(
    # Basic Information
    entity_type="suppliers",
    name="Supplier",
    plural_name="Suppliers",
    service_name="suppliers",
    table_name="suppliers",
    primary_key="supplier_id",
    title_field="supplier_name",
    subtitle_field="supplier_category",
    icon="fas fa-truck",
    
    # List View Configuration
    enable_saved_filter_suggestions=True,
    enable_auto_submit=False,
    page_title="Supplier Management",
    description="Manage suppliers and vendors",
    searchable_fields=["supplier_name", "contact_person_name", "email", "supplier_code"],
    default_sort_field="supplier_name",
    default_sort_direction="asc",
    model_class="app.models.master.Supplier",
    
    # Core Configuration
    fields=SUPPLIER_FIELDS,
    actions=SUPPLIER_ACTIONS,
    summary_cards=SUPPLIER_SUMMARY_CARDS,
    permissions=SUPPLIER_PERMISSIONS,
    
    # Filter Configuration
    filter_category_mapping=SUPPLIER_FILTER_CATEGORY_MAPPING,
    default_filters=SUPPLIER_DEFAULT_FILTERS,
    category_configs=SUPPLIER_CATEGORY_CONFIGS,
    
    # Date Field
    primary_date_field="created_at"
)

# =============================================================================
# MODULE REGISTRY
# =============================================================================

MASTER_ENTITY_CONFIGS = {
    "suppliers": SUPPLIER_CONFIG,
    # Future: Add patients, users, etc.
    # "patients": PATIENT_CONFIG,
    # "users": USER_CONFIG,
}

# Entity filter configs for module
MASTER_ENTITY_FILTER_CONFIGS = {
    "suppliers": SUPPLIER_ENTITY_FILTER_CONFIG,
    # Future: Add other entity filters
}

# Entity search configs for module
MASTER_ENTITY_SEARCH_CONFIGS = {
    "suppliers": SUPPLIER_SEARCH_CONFIG,
    # Future: Add other entity searches
}

# Export function for registry
def get_module_configs():
    """Return all configurations from this module"""
    return MASTER_ENTITY_CONFIGS

def get_module_filter_configs():
    """Return all filter configurations from this module"""
    return MASTER_ENTITY_FILTER_CONFIGS

def get_module_search_configs():
    """Return all search configurations from this module"""
    return MASTER_ENTITY_SEARCH_CONFIGS