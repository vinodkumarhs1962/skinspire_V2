"""
Package Payment Plan Configuration
Universal Engine entity configuration for package payment plans with installment schedules

Version: 1.1
Created: 2025-01-11
Updated: 2025-01-11 - Fixed to use only core_definitions.py parameters
"""

from app.config.core_definitions import (
    EntityConfiguration,
    FieldDefinition,
    SectionDefinition,
    TabDefinition,
    ViewLayoutConfiguration,
    LayoutType,
    ActionDefinition,
    EntityCategory,
    FieldType,
    ButtonType,
    ActionDisplayType,
    EntitySearchConfiguration,
    CustomRenderer,
    FilterType,
    FilterOperator
)

from app.config.filter_categories import FilterCategory

# =============================================================================
# FIELD DEFINITIONS
# =============================================================================

PACKAGE_PAYMENT_PLAN_FIELDS = [
    # ==========================================
    # LIST VIEW COLUMNS (Order matters for list display!)
    # ==========================================
    # Column 1: Created On (First column in list)
    FieldDefinition(
        name='created_at',
        label='Created On',
        field_type=FieldType.DATE,  # Use DATE type for dd/mmm format
        format_pattern='%d/%b/%y',  # Format: 13/Nov/25 (includes year, prevents line break)
        readonly=True,
        filterable=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        sortable=True,
        width='85px',  # Increased from 70px to fit dd/mmm/yy format
        css_classes='text-nowrap align-top',  # No wrap, align to top
        tab_group="audit",
        section="audit_info",
        view_order=70
    ),
    # Column 2: Patient Name (with autocomplete dropdown)
    FieldDefinition(
        name='patient_name',
        label='Patient Name',
        field_type=FieldType.TEXT,  # Not a foreign key - it's a display field from the view
        readonly=True,
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,  # Entity dropdown filter like supplier_name
        filter_operator=FilterOperator.EQUALS,
        entity_search_config=EntitySearchConfiguration(
            target_entity='patients',
            search_fields=['full_name', 'mrn'],  # Search by patient name and MRN
            display_template='{patient_name}',
            value_field='patient_name',          # Use patient_name from API (matches search_patients response)
            filter_field='patient_name',         # Filter by patient_name field in view
            placeholder='Type to search patients...',
            preload_common=True,
            cache_results=True,
            min_chars=1,
            max_results=20
        ),
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        searchable=True,  # Include in text search
        sortable=True,
        css_classes='text-wrap align-top',  # Wrap text naturally at word boundaries (removed word-break-all)
        width='180px',  # Increased width to accommodate wrapped text
        tab_group="overview",
        section="basic_info",
        view_order=1
    ),
    # Column 3: Package Name (with autocomplete dropdown)
    FieldDefinition(
        name='package_name',
        label='Package Name',
        field_type=FieldType.TEXT,  # Display field in list
        readonly=True,
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,  # Entity dropdown filter like supplier_name
        filter_operator=FilterOperator.EQUALS,
        entity_search_config=EntitySearchConfiguration(
            target_entity='packages',
            search_fields=['package_name'],  # Search by package name only (package_code doesn't exist in model)
            display_template='{package_name}',
            value_field='package_name',          # Use name as value (matches view column)
            filter_field='package_name',         # Filter by package_name field in view
            placeholder='Type to search packages...',
            preload_common=True,
            cache_results=True,
            min_chars=1,
            max_results=20
        ),
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        searchable=True,  # Include in text search
        sortable=True,
        css_classes='text-wrap align-top',  # Wrap text naturally at word boundaries (removed word-break-all)
        width='200px',  # Increased width to accommodate wrapped text
        tab_group="overview",
        section="basic_info",
        view_order=2
    ),
    # Column 4: Total Amount
    FieldDefinition(
        name='total_amount',
        label='Total Amount',
        field_type=FieldType.CURRENCY,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        min_value=0,
        sortable=True,
        width='90px',  # Reduced from 120px
        css_classes='text-end align-top',  # Right align, top align
        tab_group="overview",
        section="financial",
        view_order=10
    ),
    # Column 5: Paid Amount
    FieldDefinition(
        name='paid_amount',
        label='Paid',
        field_type=FieldType.CURRENCY,
        readonly=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,  # Show in edit form as readonly
        help_text='Auto-calculated from installment payments',
        sortable=True,
        width='90px',  # Reduced from 120px
        css_classes='text-end align-top',  # Right align, top align
        tab_group="overview",
        section="financial",
        view_order=11
    ),
    # Column 6: Balance Amount
    FieldDefinition(
        name='balance_amount',
        label='Balance',
        field_type=FieldType.CURRENCY,
        readonly=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,  # Show in edit form as readonly/computed
        help_text='Computed: Total Amount - Paid Amount',
        sortable=True,
        width='90px',  # Reduced from 120px
        css_classes='text-end align-top',  # Right align, top align
        tab_group="overview",
        section="financial",
        view_order=12
    ),
    # Column 7: Total Sessions
    FieldDefinition(
        name='total_sessions',
        label='Total Sessions',
        field_type=FieldType.INTEGER,
        required=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        min_value=1,
        max_value=50,
        default=1,
        width='60px',  # Reduced from 80px
        css_classes='text-center align-top',  # Center align, top align
        help_text='Changing this will add/remove scheduled sessions. Cannot reduce below completed sessions.',
        tab_group="overview",
        section="sessions",
        view_order=20
    ),
    # Column 8: Completed Sessions
    FieldDefinition(
        name='completed_sessions',
        label='Completed',
        field_type=FieldType.INTEGER,
        readonly=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,  # Show in edit form
        default=0,
        width='60px',  # Reduced from 80px
        css_classes='text-center align-top',  # Center align, top align
        help_text='Auto-updated when sessions are marked complete',
        tab_group="overview",
        section="sessions",
        view_order=21
    ),
    # Column 9: Status
    FieldDefinition(
        name='status',
        label='Status',
        field_type=FieldType.SELECT,  # Changed from STATUS_BADGE to SELECT for edit form
        filterable=True,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        options=[
            {'value': 'active', 'label': 'Active'},
            {'value': 'completed', 'label': 'Completed'},
            {'value': 'cancelled', 'label': 'Cancelled'},
            {'value': 'suspended', 'label': 'Suspended'},
            {'value': 'discontinued', 'label': 'Discontinued'}  # New option
        ],
        default='active',
        width='90px',  # Reduced from 100px
        css_classes='align-top',  # Top align
        help_text='Change to Discontinued will trigger refund process',
        tab_group="overview",
        section="status",
        view_order=40
    ),

    # ==========================================
    # DETAIL/FORM ONLY FIELDS (Not in list)
    # ==========================================
    FieldDefinition(
        name='plan_id',
        label='Plan ID',
        field_type=FieldType.TEXT,  # Changed to TEXT for better display in forms
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,  # Show in edit form as reference
        help_text='Unique plan reference number',
        tab_group="overview",
        section="basic_info",
        view_order=0
    ),
    # Virtual field for patient name display in forms
    FieldDefinition(
        name='patient_display',
        label='Patient',
        field_type=FieldType.TEXT,
        readonly=True,
        virtual=True,  # Computed/derived field
        show_in_list=False,
        show_in_detail=False,
        show_in_form=True,  # Show in edit form as readonly text
        help_text='Cannot be changed after plan creation',
        tab_group="overview",
        section="basic_info",
        view_order=1
    ),
    FieldDefinition(
        name='patient_id',
        label='Patient ID',
        field_type=FieldType.UUID,
        required=False,
        readonly=True,
        filterable=False,  # ✅ NOT filterable - patient_name handles filtering (UUID or text)
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        # Note: patient_name autocomplete stores UUID in patient_name field
        tab_group="overview",
        section="basic_info",
        view_order=1
    ),
    # Virtual field for package name display in forms
    FieldDefinition(
        name='package_display',
        label='Package',
        field_type=FieldType.TEXT,
        readonly=True,
        virtual=True,  # Computed/derived field
        show_in_list=False,
        show_in_detail=False,
        show_in_form=True,  # Show in edit form as readonly text
        help_text='Cannot be changed after plan creation',
        tab_group="overview",
        section="basic_info",
        view_order=2
    ),
    FieldDefinition(
        name='package_id',
        label='Package ID',
        field_type=FieldType.UUID,
        required=False,
        readonly=True,
        filterable=False,  # ✅ NOT filterable - package_name handles filtering (UUID or text)
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        # Note: package_name autocomplete stores UUID in package_name field
        tab_group="overview",
        section="basic_info",
        view_order=2
    ),
    # DEPRECATED FIELDS - Kept for backward compatibility, hidden from forms
    FieldDefinition(
        name='package_description',
        label='Package Description (Deprecated)',
        field_type=FieldType.TEXTAREA,
        readonly=True,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        tab_group="overview",
        section="basic_info",
        view_order=91
    ),
    FieldDefinition(
        name='package_code',
        label='Package Code (Deprecated)',
        field_type=FieldType.TEXT,
        readonly=True,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        tab_group="overview",
        section="basic_info",
        view_order=92
    ),

    # ==========================================
    # DETAIL/FORM ONLY - Session & Installment Fields
    # ==========================================
    FieldDefinition(
        name='remaining_sessions',
        label='Remaining Sessions',
        field_type=FieldType.INTEGER,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,  # Show in edit form as computed
        help_text='Computed: Total Sessions - Completed Sessions',
        tab_group="overview",
        section="sessions",
        view_order=22
    ),

    # ==========================================
    # INSTALLMENT CONFIGURATION
    # ==========================================
    FieldDefinition(
        name='installment_count',
        label='Number of Installments',
        field_type=FieldType.INTEGER,
        required=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        min_value=1,
        max_value=12,
        default=1,
        help_text='Changing this will recalculate installment amounts. Cannot reduce below paid installments.',
        tab_group="installments",
        section="installments",
        view_order=30
    ),
    FieldDefinition(
        name='installment_frequency',
        label='Installment Frequency',
        field_type=FieldType.SELECT,
        required=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        options=[
            {'value': 'weekly', 'label': 'Weekly'},
            {'value': 'biweekly', 'label': 'Bi-weekly'},
            {'value': 'monthly', 'label': 'Monthly'},
            {'value': 'custom', 'label': 'Custom'}
        ],
        default='monthly',
        tab_group="installments",
        section="installments",
        view_order=31
    ),
    FieldDefinition(
        name='first_installment_date',
        label='First Installment Date',
        field_type=FieldType.DATE,
        required=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        tab_group="installments",
        section="installments",
        view_order=32
    ),

    # ==========================================
    # STATUS & NOTES (Detail/Form only)
    # ==========================================
    FieldDefinition(
        name='notes',
        label='Notes',
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        rows=4,
        placeholder='Additional notes about the payment plan...',
        tab_group="overview",
        section="status",
        view_order=41
    ),

    # ==========================================
    # CANCELLATION FIELDS
    # ==========================================
    FieldDefinition(
        name='cancelled_at',
        label='Cancelled At',
        field_type=FieldType.DATETIME,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="cancellation",
        view_order=50
    ),
    FieldDefinition(
        name='cancelled_by',
        label='Cancelled By',
        field_type=FieldType.UUID,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="cancellation",
        view_order=51
    ),
    FieldDefinition(
        name='cancellation_reason',
        label='Cancellation Reason',
        field_type=FieldType.TEXTAREA,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="cancellation",
        view_order=52
    ),

    # ==========================================
    # SUSPENSION FIELDS
    # ==========================================
    FieldDefinition(
        name='suspended_at',
        label='Suspended At',
        field_type=FieldType.DATETIME,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="suspension",
        view_order=60
    ),
    FieldDefinition(
        name='suspended_by',
        label='Suspended By',
        field_type=FieldType.UUID,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="suspension",
        view_order=61
    ),
    FieldDefinition(
        name='suspension_reason',
        label='Suspension Reason',
        field_type=FieldType.TEXTAREA,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="suspension",
        view_order=62
    ),

    # ==========================================
    # DISCONTINUATION TRACKING
    # ==========================================
    FieldDefinition(
        name='discontinued_at',
        label='Discontinued At',
        field_type=FieldType.DATETIME,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="discontinuation",
        view_order=63
    ),
    FieldDefinition(
        name='discontinued_by',
        label='Discontinued By',
        field_type=FieldType.UUID,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="discontinuation",
        view_order=64
    ),
    FieldDefinition(
        name='discontinuation_reason',
        label='Discontinuation Reason',
        field_type=FieldType.TEXTAREA,
        required=False,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        conditional_display="status == 'discontinued'",
        help_text='Required when changing status to Discontinued',
        tab_group="overview",
        section="basic_info",
        view_order=11
    ),
    FieldDefinition(
        name='refund_amount',
        label='Refund Amount',
        field_type=FieldType.DECIMAL,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="discontinuation",
        view_order=65
    ),
    FieldDefinition(
        name='refund_status',
        label='Refund Status',
        field_type=FieldType.TEXT,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="discontinuation",
        view_order=66
    ),

    # ==========================================
    # AUDIT FIELDS (Detail only - created_at is in list columns above)
    # ==========================================
    FieldDefinition(
        name='created_by',
        label='Created By',
        field_type=FieldType.UUID,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="audit_info",
        view_order=71
    ),
    FieldDefinition(
        name='updated_at',
        label='Updated At',
        field_type=FieldType.DATETIME,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="audit_info",
        view_order=72
    ),
    FieldDefinition(
        name='updated_by',
        label='Updated By',
        field_type=FieldType.UUID,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="audit_info",
        view_order=73
    ),

    # ==========================================
    # SOFT DELETE FIELDS
    # ==========================================
    FieldDefinition(
        name='is_deleted',
        label='Is Deleted',
        field_type=FieldType.BOOLEAN,
        readonly=True,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False,
        tab_group="audit",
        section="soft_delete",
        view_order=80
    ),
    FieldDefinition(
        name='deleted_at',
        label='Deleted At',
        field_type=FieldType.DATETIME,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="soft_delete",
        view_order=81
    ),
    FieldDefinition(
        name='deleted_by',
        label='Deleted By',
        field_type=FieldType.UUID,
        readonly=True,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="audit",
        section="soft_delete",
        view_order=82
    ),

    # =============================================================================
    # CUSTOM RENDERER FIELDS FOR CHILD TABLES
    # =============================================================================

    FieldDefinition(
        name="installments_display",
        label="Payment Installments",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="installments",
        section="installments_table",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="engine/business/installment_payments_table.html",
            context_function="get_plan_installments",
            css_classes="table-responsive w-100"
        )
    ),

    FieldDefinition(
        name="sessions_display",
        label="Service Sessions",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        tab_group="sessions",
        section="sessions_table",
        view_order=0,
        custom_renderer=CustomRenderer(
            template="engine/business/package_sessions_table.html",
            context_function="get_plan_sessions",
            css_classes="table-responsive w-100"
        )
    ),
]

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

PACKAGE_PAYMENT_PLAN_SECTIONS = {
    'basic_info': SectionDefinition(
        key='basic_info',
        title='Patient & Package Selection',
        icon='fas fa-info-circle',
        columns=2,
        order=1
    ),
    'financial': SectionDefinition(
        key='financial',
        title='Financial Details',
        icon='fas fa-dollar-sign',
        columns=2,
        order=2
    ),
    'sessions': SectionDefinition(
        key='sessions',
        title='Session Configuration',
        icon='fas fa-calendar-check',
        columns=2,
        order=3
    ),
    'installments': SectionDefinition(
        key='installments',
        title='Installment Schedule',
        icon='fas fa-calendar-alt',
        columns=3,
        order=4
    ),
    'installments_table': SectionDefinition(
        key='installments_table',
        title='Payment Installments',
        icon='fas fa-table',
        columns=1,
        order=5
    ),
    'sessions_table': SectionDefinition(
        key='sessions_table',
        title='Service Sessions',
        icon='fas fa-list',
        columns=1,
        order=6
    ),
    'status': SectionDefinition(
        key='status',
        title='Status & Notes',
        icon='fas fa-flag',
        columns=2,
        order=7
    ),
    'cancellation': SectionDefinition(
        key='cancellation',
        title='Cancellation Details',
        icon='fas fa-times-circle',
        columns=2,
        order=8,
        conditional_display="item.cancelled_at is not None"
    ),
    'suspension': SectionDefinition(
        key='suspension',
        title='Suspension Details',
        icon='fas fa-pause-circle',
        columns=2,
        order=9,
        conditional_display="item.suspended_at is not None"
    ),
    'discontinuation': SectionDefinition(
        key='discontinuation',
        title='Discontinuation & Refund Details',
        icon='fas fa-ban',
        columns=2,
        order=10,
        conditional_display="item.discontinued_at is not None"
    ),
    'audit_info': SectionDefinition(
        key='audit_info',
        title='Audit Information',
        icon='fas fa-history',
        columns=2,
        order=11
    ),
    'soft_delete': SectionDefinition(
        key='soft_delete',
        title='Deletion Details',
        icon='fas fa-trash-alt',
        columns=2,
        order=12,
        conditional_display="item.is_deleted"
    ),
}

# =============================================================================
# ACTIONS
# =============================================================================

PACKAGE_PAYMENT_PLAN_ACTIONS = [
    # View Detail
    ActionDefinition(
        id="view",
        label="View",
        icon="fas fa-eye",
        url_pattern="/universal/package_payment_plans/detail/{plan_id}",
        button_type=ButtonType.PRIMARY,
        permission="package_payment_plan_view",
        show_in_list=True,
        show_in_detail=False,
        display_type=ActionDisplayType.BUTTON,
        order=1
    ),
    # Edit
    ActionDefinition(
        id="edit",
        label="Edit",
        icon="fas fa-edit",
        url_pattern="/universal/package_payment_plans/edit/{plan_id}",
        button_type=ButtonType.WARNING,
        permission="package_payment_plan_edit",
        show_in_list=True,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        order=2
    ),
    # Delete
    ActionDefinition(
        id="delete",
        label="Delete",
        icon="fas fa-trash",
        url_pattern="/universal/package_payment_plans/delete/{plan_id}",
        button_type=ButtonType.DANGER,
        permission="package_payment_plan_delete",
        show_in_list=True,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        confirmation_required=True,
        confirmation_message="Are you sure you want to delete this payment plan?",
        order=3
    ),
    # View Patient AR Statement
    ActionDefinition(
        id="view_ar_statement",
        label="View Patient AR Statement",
        icon="fas fa-file-invoice-dollar",
        url_pattern="javascript:openARStatementModal('{patient_id}', '{plan_id}')",
        button_type=ButtonType.INFO,
        permission="package_payment_plan_view",
        show_in_list=False,
        show_in_detail=True,
        display_type=ActionDisplayType.BUTTON,
        order=100
    ),
]

# =============================================================================
# SUMMARY CARDS
# =============================================================================

PACKAGE_PAYMENT_PLAN_SUMMARY_CARDS = [
    {
        'title': 'Total Plans',
        'field': 'count',
        'icon': 'fas fa-calendar-alt',
        'color': 'primary'
    },
    {
        'title': 'Active Plans',
        'field': 'active_count',
        'icon': 'fas fa-check-circle',
        'color': 'success'
    },
    {
        'title': 'Total Revenue',
        'field': 'total_amount',
        'icon': 'fas fa-dollar-sign',
        'color': 'info',
        'format': 'currency'
    },
    {
        'title': 'Outstanding Balance',
        'field': 'balance_amount',
        'icon': 'fas fa-hourglass-half',
        'color': 'warning',
        'format': 'currency'
    }
]

# =============================================================================
# DETAIL VIEW INFO CARDS (Header - 4 cards showing plan-specific metrics)
# =============================================================================

PACKAGE_PAYMENT_PLAN_INFO_CARDS = [
    'total_amount',      # Total Plan Amount
    'paid_amount',       # Amount Paid
    'balance_amount',    # Balance Due
    'completed_sessions'  # Sessions Completed
]

# =============================================================================
# TAB DEFINITIONS (Tabbed Layout for Detail View)
# =============================================================================

PACKAGE_PAYMENT_PLAN_TABS = {
    'overview': TabDefinition(
        key='overview',
        label='Overview',
        icon='fas fa-info-circle',
        sections={
            'basic_info': PACKAGE_PAYMENT_PLAN_SECTIONS['basic_info'],
            'financial': PACKAGE_PAYMENT_PLAN_SECTIONS['financial'],
            'sessions': PACKAGE_PAYMENT_PLAN_SECTIONS['sessions'],
            'status': PACKAGE_PAYMENT_PLAN_SECTIONS['status']
        },
        order=1,
        default_active=True
    ),
    'installments': TabDefinition(
        key='installments',
        label='Installments',
        icon='fas fa-calendar-alt',
        sections={
            'installments': PACKAGE_PAYMENT_PLAN_SECTIONS['installments'],
            'installments_table': PACKAGE_PAYMENT_PLAN_SECTIONS['installments_table']
        },
        order=2
    ),
    'sessions': TabDefinition(
        key='sessions',
        label='Sessions',
        icon='fas fa-calendar-check',
        sections={
            'sessions_table': PACKAGE_PAYMENT_PLAN_SECTIONS['sessions_table']
        },
        order=3
    ),
    'audit': TabDefinition(
        key='audit',
        label='Audit & History',
        icon='fas fa-history',
        sections={
            'audit_info': PACKAGE_PAYMENT_PLAN_SECTIONS['audit_info'],
            'cancellation': PACKAGE_PAYMENT_PLAN_SECTIONS['cancellation'],
            'suspension': PACKAGE_PAYMENT_PLAN_SECTIONS['suspension'],
            'discontinuation': PACKAGE_PAYMENT_PLAN_SECTIONS['discontinuation'],
            'soft_delete': PACKAGE_PAYMENT_PLAN_SECTIONS['soft_delete']
        },
        order=4
    )
}

# =============================================================================
# VIEW LAYOUT CONFIGURATION
# =============================================================================

PACKAGE_PAYMENT_PLAN_VIEW_LAYOUT = ViewLayoutConfiguration(
    type=LayoutType.TABBED,
    tabs=PACKAGE_PAYMENT_PLAN_TABS,
    sections=PACKAGE_PAYMENT_PLAN_SECTIONS,
    default_tab='overview',
    sticky_tabs=True,
    auto_generate_sections=False,
    default_section_columns=2,
    enable_print=False,
    enable_export=False,
    header_config={
        "primary_field": "plan_id",
        "primary_label": "Plan ID",
        "title_field": "patient_name",
        "title_label": "Patient",
        "status_field": "status",
        "secondary_fields": [
            {"field": "package_name", "label": "Package", "icon": "fas fa-box", "type": "text"},
            {"field": "total_amount", "label": "Total Amount", "icon": "fas fa-rupee-sign", "type": "currency", "css_classes": "text-xl font-bold text-primary"},
            {"field": "created_at", "label": "Created On", "icon": "fas fa-calendar", "type": "datetime", "format": "%d-%b-%Y"},
            {"field": "balance_amount", "label": "Balance", "icon": "fas fa-money-bill", "type": "currency", "css_classes": "text-lg font-semibold text-danger"}
        ]
    }
)

# =============================================================================
# PERMISSIONS
# =============================================================================

PACKAGE_PAYMENT_PLAN_PERMISSIONS = {
    'view': 'package_payment_plan_view',
    'create': 'package_payment_plan_create',
    'edit': 'package_payment_plan_edit',
    'delete': 'package_payment_plan_delete'
}

# =============================================================================
# FILTER CONFIGURATION
# =============================================================================

PACKAGE_PAYMENT_PLAN_FILTER_CATEGORY_MAPPING = {
    # Date filters
    'created_at': FilterCategory.DATE,
    'start_date': FilterCategory.DATE,
    'end_date': FilterCategory.DATE,
    'date_from': FilterCategory.DATE,
    'date_to': FilterCategory.DATE,

    # Amount filters
    'total_amount': FilterCategory.AMOUNT,
    'paid_amount': FilterCategory.AMOUNT,
    'balance_amount': FilterCategory.AMOUNT,
    'amount_min': FilterCategory.AMOUNT,
    'amount_max': FilterCategory.AMOUNT,

    # Search filters
    'search': FilterCategory.SEARCH,
    'patient_name': FilterCategory.SEARCH,
    'package_name': FilterCategory.SEARCH,
    'plan_id': FilterCategory.SEARCH,

    # Selection filters
    'status': FilterCategory.SELECTION,
}

PACKAGE_PAYMENT_PLAN_DEFAULT_FILTERS = {}

PACKAGE_PAYMENT_PLAN_CATEGORY_CONFIGS = {}

# =============================================================================
# ENTITY CONFIGURATION
# =============================================================================

PACKAGE_PAYMENT_PLANS_CONFIG = EntityConfiguration(
    # ========== REQUIRED PARAMETERS (in order) ==========
    entity_type='package_payment_plans',
    name='Package Plan',
    plural_name='Package Plans',
    service_name='package_payment_plans',
    table_name='package_payment_plans_view',  # ✅ FIX: Use VIEW not base table!
    primary_key='plan_id',
    title_field='patient_name',  # Show patient name as main title
    subtitle_field='package_name',  # Show package name as subtitle
    icon='fas fa-calendar-alt',
    page_title='Package Plans',
    description='Manage package plans with installment schedules and session tracking',
    searchable_fields=['plan_id', 'patient_id', 'package_id', 'patient_name', 'package_name'],  # Text search fields
    default_sort_field='created_at',
    default_sort_direction='desc',  # Latest first
    fields=PACKAGE_PAYMENT_PLAN_FIELDS,
    actions=PACKAGE_PAYMENT_PLAN_ACTIONS,
    summary_cards=PACKAGE_PAYMENT_PLAN_SUMMARY_CARDS,
    permissions=PACKAGE_PAYMENT_PLAN_PERMISSIONS,

    # ========== OPTIONAL PARAMETERS ==========
    # Entity Category - MASTER allows edit functionality
    entity_category=EntityCategory.MASTER,

    # Service Module - Points to PackagePaymentService for custom business logic
    service_module='app.services.package_payment_service',

    # Soft Delete
    enable_soft_delete=True,
    soft_delete_field='is_deleted',

    # Filter Configuration
    filter_category_mapping=PACKAGE_PAYMENT_PLAN_FILTER_CATEGORY_MAPPING,
    default_filters=PACKAGE_PAYMENT_PLAN_DEFAULT_FILTERS,
    category_configs=PACKAGE_PAYMENT_PLAN_CATEGORY_CONFIGS,

    # Section Definitions
    section_definitions=PACKAGE_PAYMENT_PLAN_SECTIONS,

    # Form Section Definitions (for create/edit forms - simpler than detail view)
    form_section_definitions={
        'basic_info': SectionDefinition(
            key='basic_info',
            title='Plan Information',
            icon='fas fa-file-invoice',
            columns=2,
            order=1
        ),
        'financial': SectionDefinition(
            key='financial',
            title='Financial Details',
            icon='fas fa-dollar-sign',
            columns=2,
            order=2
        ),
        'notes': SectionDefinition(
            key='notes',
            title='Additional Notes',
            icon='fas fa-comment',
            columns=1,
            order=3
        ),
    },

    # Edit Fields - Define which fields can be edited
    # Virtual fields show names for patient/package instead of UUIDs
    # Read-only fields shown for context: patient_display, package_display, paid_amount, balance_amount
    # Editable fields: amounts, status, sessions/installments for replanning
    edit_fields=[
        'patient_display',      # Virtual field - shows "Patient Name (MRN)" (readonly)
        'package_display',      # Virtual field - shows "Package Name - ₹Price" (readonly)
        'total_amount',         # Editable - can adjust package price
        'paid_amount',          # Read-only - computed from payments
        'balance_amount',       # Read-only - computed field
        'total_sessions',       # Editable - triggers replanning if changed
        'completed_sessions',   # Read-only - number completed
        'remaining_sessions',   # Read-only - computed field
        'installment_count',    # Editable - triggers replanning if changed
        'installment_frequency', # Editable - may need to adjust schedule
        'first_installment_date', # Editable - may need to adjust schedule
        'status',               # Editable - can set to discontinued (triggers refund)
        'discontinuation_reason', # Editable - required when status = discontinued
        'notes'                 # Editable - additional information
    ],

    # Detail View - Info Cards (4 cards in header showing plan-specific metrics)
    info_card_fields=PACKAGE_PAYMENT_PLAN_INFO_CARDS,

    # Detail View - Tabbed Layout
    view_layout=PACKAGE_PAYMENT_PLAN_VIEW_LAYOUT,

    # Items Per Page
    items_per_page=20,

    # Custom Templates
    custom_templates={
        'installments_table': 'engine/business/installment_payments_table.html',
        'sessions_table': 'engine/business/package_sessions_table.html'
    }
)

# =============================================================================
# EXPORTS - For backward compatibility
# =============================================================================

config = PACKAGE_PAYMENT_PLANS_CONFIG
