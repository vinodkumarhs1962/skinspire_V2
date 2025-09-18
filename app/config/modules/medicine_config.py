# app/config/modules/medicine_config.py
"""
Medicine Entity Configuration for Universal Engine
COMPLETELY FIXED VERSION - All issues resolved
"""

from app.config.core_definitions import (
    EntityConfiguration,
    FieldDefinition,
    FieldType,
    FilterType,
    FilterOperator,
    SectionDefinition,
    TabDefinition,
    ViewLayoutConfiguration,
    LayoutType,
    EntityCategory,
    CRUDOperation,
    ActionDefinition,
    ButtonType
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# MEDICINE FIELD DEFINITIONS (Aligned with database model)
# =============================================================================

MEDICINE_FIELDS = [
    # ========== PRIMARY KEY ==========
    FieldDefinition(
        name="medicine_id",
        label="Medicine ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="basic",
        section="identification",
        view_order=0
    ),
    
    # ========== BASIC INFORMATION ==========
    FieldDefinition(
        name="medicine_name",
        label="Medicine Name",
        field_type=FieldType.TEXT,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        filterable=True,
        sortable=True,
        placeholder="Enter medicine name",
        tab_group="basic",
        section="basic_info",
        view_order=1
    ),
    
    FieldDefinition(
        name="generic_name",
        label="Generic Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        filterable=True,
        placeholder="Enter generic name",
        tab_group="basic",
        section="basic_info",
        view_order=2
    ),
    
    FieldDefinition(
        name="dosage_form",
        label="Dosage Form",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        options=[
            {"value": "tablet", "label": "Tablet"},
            {"value": "capsule", "label": "Capsule"},
            {"value": "syrup", "label": "Syrup"},
            {"value": "injection", "label": "Injection"},
            {"value": "cream", "label": "Cream"},
            {"value": "ointment", "label": "Ointment"},
            {"value": "drops", "label": "Drops"},
            {"value": "inhaler", "label": "Inhaler"},
            {"value": "spray", "label": "Spray"},
            {"value": "other", "label": "Other"}
        ],
        tab_group="basic",
        section="basic_info",
        view_order=3
    ),
    
    FieldDefinition(
        name="strength",
        label="Strength",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        placeholder="e.g., 500mg, 10ml",
        tab_group="basic",
        section="basic_info",
        view_order=4
    ),
    
    FieldDefinition(
        name="manufacturer",
        label="Manufacturer",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        filterable=True,
        placeholder="Enter manufacturer name",
        tab_group="basic",
        section="basic_info",
        view_order=5
    ),
    
    # ========== CLASSIFICATION ==========
    FieldDefinition(
        name="medicine_category",
        label="Category",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        options=[
            {"value": "allopathic", "label": "Allopathic"},
            {"value": "ayurvedic", "label": "Ayurvedic"},
            {"value": "homeopathic", "label": "Homeopathic"},
            {"value": "unani", "label": "Unani"},
            {"value": "other", "label": "Other"}
        ],
        tab_group="basic",
        section="classification",
        view_order=1
    ),
    
    FieldDefinition(
        name="therapeutic_class",
        label="Therapeutic Class",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        placeholder="e.g., Antibiotics, Analgesics",
        tab_group="basic",
        section="classification",
        view_order=2
    ),
    
    FieldDefinition(
        name="schedule",
        label="Schedule",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        options=[
            {"value": "none", "label": "None"},
            {"value": "H", "label": "Schedule H"},
            {"value": "H1", "label": "Schedule H1"},
            {"value": "X", "label": "Schedule X"},
            {"value": "G", "label": "Schedule G"},
            {"value": "J", "label": "Schedule J"},
            {"value": "K", "label": "Schedule K"}
        ],
        tab_group="basic",
        section="classification",
        view_order=3
    ),
    
    # ========== GST INFORMATION ==========
    FieldDefinition(
        name="hsn_code",
        label="HSN Code",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        placeholder="Enter HSN code",
        tab_group="gst",
        section="gst_info",
        view_order=1
    ),
    
    FieldDefinition(
        name="gst_rate",
        label="GST Rate (%)",
        field_type=FieldType.NUMBER,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        min_value=0,
        max_value=100,
        placeholder="Enter GST rate",
        tab_group="gst",
        section="gst_info",
        view_order=2
    ),
    
    # ========== PRICING INFORMATION ==========
    FieldDefinition(
        name="cost_price",
        label="Cost Price",
        field_type=FieldType.CURRENCY,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        min_value=0,
        placeholder="Enter cost price",
        tab_group="pricing",
        section="pricing_info",
        view_order=1
    ),
    
    FieldDefinition(
        name="mrp",
        label="MRP",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        min_value=0,
        placeholder="Enter MRP",
        tab_group="pricing",
        section="pricing_info",
        view_order=2
    ),
    
    FieldDefinition(
        name="selling_price",
        label="Selling Price",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        min_value=0,
        placeholder="Enter selling price",
        tab_group="pricing",
        section="pricing_info",
        view_order=3
    ),
    
    # ========== INVENTORY INFORMATION ==========
    FieldDefinition(
        name="unit_type",
        label="Unit Type",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        options=[
            {"value": "strip", "label": "Strip"},
            {"value": "bottle", "label": "Bottle"},
            {"value": "vial", "label": "Vial"},
            {"value": "tube", "label": "Tube"},
            {"value": "piece", "label": "Piece"},
            {"value": "box", "label": "Box"},
            {"value": "packet", "label": "Packet"}
        ],
        tab_group="inventory",
        section="inventory_info",
        view_order=1
    ),
    
    FieldDefinition(
        name="units_per_pack",
        label="Units Per Pack",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        min_value=1,
        default_value=1,
        placeholder="Enter units per pack",
        tab_group="inventory",
        section="inventory_info",
        view_order=2
    ),
    
    FieldDefinition(
        name="reorder_level",
        label="Reorder Level",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        min_value=0,
        placeholder="Minimum stock level",
        tab_group="inventory",
        section="inventory_info",
        view_order=3
    ),
    
    FieldDefinition(
        name="max_stock",
        label="Maximum Stock",
        field_type=FieldType.NUMBER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        min_value=0,
        placeholder="Maximum stock level",
        tab_group="inventory",
        section="inventory_info",
        view_order=4
    ),
    
    # ========== STATUS FIELDS ==========
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        options=[
            {"value": "active", "label": "Active"},
            {"value": "inactive", "label": "Inactive"},
            {"value": "discontinued", "label": "Discontinued"}
        ],
        default_value="active",
        tab_group="system",
        section="status_info",
        view_order=1
    ),
    
    # ========== SYSTEM FIELDS ==========
    FieldDefinition(
        name="created_at",
        label="Created At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system",
        section="audit_info",
        view_order=1
    ),
    
    FieldDefinition(
        name="updated_at",
        label="Updated At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="system",
        section="audit_info",
        view_order=2
    )
]

# =============================================================================
# FILTER CATEGORY MAPPING - FIXED: Using correct FilterCategory values
# =============================================================================

MEDICINE_FILTER_CATEGORY_MAPPING = {
    "medicine_name": FilterCategory.SEARCH,      # ✅ FIXED: TEXT → SEARCH
    "generic_name": FilterCategory.SEARCH,       # ✅ FIXED: TEXT → SEARCH
    "manufacturer": FilterCategory.SEARCH,       # ✅ FIXED: TEXT → SEARCH
    "dosage_form": FilterCategory.SELECTION,     # ✅ FIXED: SINGLE_SELECT → SELECTION
    "medicine_category": FilterCategory.SELECTION, # ✅ FIXED: SINGLE_SELECT → SELECTION
    "therapeutic_class": FilterCategory.SEARCH,  # ✅ FIXED: TEXT → SEARCH
    "schedule": FilterCategory.SELECTION,        # ✅ FIXED: SINGLE_SELECT → SELECTION
    "gst_rate": FilterCategory.AMOUNT,          # ✅ FIXED: RANGE → AMOUNT
    "cost_price": FilterCategory.AMOUNT,        # ✅ FIXED: RANGE → AMOUNT
    "mrp": FilterCategory.AMOUNT,               # ✅ FIXED: RANGE → AMOUNT
    "selling_price": FilterCategory.AMOUNT,     # ✅ FIXED: RANGE → AMOUNT
    "status": FilterCategory.SELECTION,         # ✅ FIXED: SINGLE_SELECT → SELECTION
    "created_at": FilterCategory.DATE,          # ✅ FIXED: DATE_RANGE → DATE
    "updated_at": FilterCategory.DATE           # ✅ FIXED: DATE_RANGE → DATE
}

# =============================================================================
# FORM SECTIONS - Already correct (using 'key' parameter)
# =============================================================================

MEDICINE_FORM_SECTIONS = {
    "basic_info": SectionDefinition(
        key="basic_info",  # ✅ CORRECT: Using 'key' not 'name'
        title="Basic Information",
        icon="fas fa-info-circle",
        columns=2,
        order=1,
        collapsible=False,
        default_collapsed=False
    ),
    "classification": SectionDefinition(
        key="classification",
        title="Classification",
        icon="fas fa-tags",
        columns=2,
        order=2,
        collapsible=True,
        default_collapsed=False
    ),
    "gst_info": SectionDefinition(
        key="gst_info",
        title="GST Information",
        icon="fas fa-receipt",
        columns=2,
        order=3,
        collapsible=True,
        default_collapsed=False
    ),
    "pricing_info": SectionDefinition(
        key="pricing_info",
        title="Pricing",
        icon="fas fa-rupee-sign",
        columns=2,
        order=4,
        collapsible=True,
        default_collapsed=False
    ),
    "inventory_info": SectionDefinition(
        key="inventory_info",
        title="Inventory",
        icon="fas fa-warehouse",
        columns=2,
        order=5,
        collapsible=True,
        default_collapsed=True
    ),
    "status_info": SectionDefinition(
        key="status_info",
        title="Status",
        icon="fas fa-toggle-on",
        columns=2,
        order=6,
        collapsible=True,
        default_collapsed=True
    ),
    "audit_info": SectionDefinition(
        key="audit_info",
        title="System Information",
        icon="fas fa-history",
        columns=2,
        order=7,
        collapsible=True,
        default_collapsed=True
    )
}

# =============================================================================
# TAB DEFINITIONS - Already correct
# =============================================================================

MEDICINE_TABS = {
    'basic': TabDefinition(
        key='basic',
        label='Basic Info',
        icon='fas fa-pills',
        sections={
            'basic_info': MEDICINE_FORM_SECTIONS['basic_info'],
            'classification': MEDICINE_FORM_SECTIONS['classification']
        },
        order=1,
        default_active=True
    ),
    'gst': TabDefinition(
        key='gst',
        label='GST Details',
        icon='fas fa-receipt',
        sections={
            'gst_info': MEDICINE_FORM_SECTIONS['gst_info']
        },
        order=2
    ),
    'pricing': TabDefinition(
        key='pricing',
        label='Pricing',
        icon='fas fa-rupee-sign',
        sections={
            'pricing_info': MEDICINE_FORM_SECTIONS['pricing_info']
        },
        order=3
    ),
    'inventory': TabDefinition(
        key='inventory',
        label='Inventory',
        icon='fas fa-warehouse',
        sections={
            'inventory_info': MEDICINE_FORM_SECTIONS['inventory_info']
        },
        order=4
    ),
    'system': TabDefinition(
        key='system',
        label='System Info',
        icon='fas fa-cog',
        sections={
            'status_info': MEDICINE_FORM_SECTIONS['status_info'],
            'audit_info': MEDICINE_FORM_SECTIONS['audit_info']
        },
        order=5
    )
}

# =============================================================================
# VIEW LAYOUT - Already correct
# =============================================================================

MEDICINE_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,  # ✅ CORRECT: 'type' not 'layout_type'
    tabs=MEDICINE_TABS,
    default_tab='basic',
    responsive_breakpoint='md'
)

# =============================================================================
# ACTIONS - FIXED: Using 'id' and correct ButtonType values
# =============================================================================

MEDICINE_ACTIONS = [
    ActionDefinition(
        id="add_stock",  # ✅ FIXED: 'name' → 'id'
        label="Add Stock",
        button_type=ButtonType.INFO,  # ✅ CORRECT: INFO exists
        icon="fas fa-plus-circle",
        permission="medicine.update"
    ),
    ActionDefinition(
        id="view_inventory",  # ✅ FIXED: 'name' → 'id'
        label="View Inventory",
        button_type=ButtonType.SECONDARY,  # ✅ FIXED: DEFAULT → SECONDARY
        icon="fas fa-warehouse",
        permission="inventory.view"
    ),
    ActionDefinition(
        id="print_label",  # ✅ FIXED: 'name' → 'id'
        label="Print Label",
        button_type=ButtonType.SECONDARY,  # ✅ FIXED: DEFAULT → SECONDARY
        icon="fas fa-print",
        permission="medicine.view"
    )
]

# =============================================================================
# COMPLETE MEDICINE CONFIGURATION - FIXED: Using correct CRUDOperation values
# =============================================================================

MEDICINE_CONFIG = EntityConfiguration(
    # ========== BASIC INFORMATION (REQUIRED) ==========
    entity_type="medicine",
    name="Medicine",
    plural_name="Medicines",
    service_name="medicines",  # ADD THIS LINE
    table_name="medicines",
    primary_key="medicine_id",
    title_field="medicine_name",
    subtitle_field="generic_name",
    icon="fas fa-pills",
    page_title="Medicine Management",  # ADD THIS LINE
    description="Manage medicines and drugs",  # ADD THIS LINE
    searchable_fields=["medicine_name", "generic_name", "hsn_code", "manufacturer"],  # MOVE HERE
    default_sort_field="medicine_name",  # MOVE HERE
    default_sort_direction="asc",  # ADD THIS LINE
    
    # ========== CORE CONFIGURATIONS (REQUIRED) ==========
    fields=MEDICINE_FIELDS,
    actions=MEDICINE_ACTIONS,  # MOVE HERE
    summary_cards=[],  # ADD THIS LINE
    permissions={  # MOVE HERE FROM LINE 328
        'view': 'medicine.view',
        'create': 'medicine.create',
        'edit': 'medicine.edit',
        'delete': 'medicine.delete'
    },
    
    # ========== SEARCH & FILTER ==========
    filter_category_mapping=MEDICINE_FILTER_CATEGORY_MAPPING,
    # searchable_fields, default_sort_field, default_sort_order moved to required section above
    
    # ========== VIEW CONFIGURATIONS ==========
    view_layout=MEDICINE_VIEW_LAYOUT,
    section_definitions=MEDICINE_FORM_SECTIONS,
    form_section_definitions=MEDICINE_FORM_SECTIONS,
    
    # ========== ENTITY CLASSIFICATION ==========
    entity_category=EntityCategory.MASTER,
    
    # ========== ALLOWED OPERATIONS - FIXED ==========
    allowed_operations=[
        CRUDOperation.CREATE,
        CRUDOperation.READ,
        CRUDOperation.UPDATE,
        CRUDOperation.DELETE,
        CRUDOperation.LIST,
        CRUDOperation.VIEW,      # ✅ FIXED: SEARCH doesn't exist, using VIEW
        CRUDOperation.DOCUMENT,  # ✅ Added for completeness
        CRUDOperation.EXPORT     # ✅ Added for completeness
    ],
    
    
    # ========== FEATURES ==========
    enable_soft_delete=True,  # CHANGE: soft_delete → enable_soft_delete
    enable_audit_trail=True,  # CHANGE: audit_trail → enable_audit_trail
    # REMOVE: branch_aware (not a valid parameter)
    
    # ========== DEFAULT VALUES ==========
    default_filters={
        "status": "active"
    }
)

# ========== EXPORTS FOR CONFIGURATION LOADER ==========
# The ConfigurationLoader looks for these specific variable names
config = MEDICINE_CONFIG
filter_config = None
search_config = None

# Export configuration functions (keep for backward compatibility)
def get_medicine_config():
    """Get medicine configuration"""
    return MEDICINE_CONFIG

# For backward compatibility
def get_config():
    """Get configuration (backward compatibility)"""
    return MEDICINE_CONFIG