# Appointment Configuration Module
# File: app/config/modules/appointment_config.py

"""
Appointment Configuration - Phase 1 of Patient Lifecycle System
Defines entity configurations for:
- Appointments
- Doctor Schedules
- Appointment Types
- Appointment Slots

Following Universal Engine pattern for consistent CRUD operations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.config.core_definitions import (
    FieldDefinition, FieldType, SectionDefinition,
    TabDefinition, ViewLayoutConfiguration, LayoutType,
    EntityConfiguration, ActionDefinition,
    EntitySearchConfiguration, EntityFilterConfiguration, ButtonType,
    ComplexDisplayType, ActionDisplayType, FilterType,
    DocumentConfiguration, PrintLayoutType, DocumentType,
    PageSize, Orientation, DocumentSectionType, ExportFormat,
    EntityCategory, CRUDOperation, FilterOperator, CustomRenderer
)
from app.config.filter_categories import FilterCategory

# =============================================================================
# APPOINTMENT STATUS OPTIONS
# =============================================================================
APPOINTMENT_STATUS_OPTIONS = [
    {"value": "requested", "label": "Requested", "color": "#FFC107"},
    {"value": "confirmed", "label": "Confirmed", "color": "#17A2B8"},
    {"value": "checked_in", "label": "Checked In", "color": "#28A745"},
    {"value": "in_progress", "label": "In Progress", "color": "#007BFF"},
    {"value": "completed", "label": "Completed", "color": "#6C757D"},
    {"value": "cancelled", "label": "Cancelled", "color": "#DC3545"},
    {"value": "no_show", "label": "No Show", "color": "#343A40"},
    {"value": "rescheduled", "label": "Rescheduled", "color": "#6610F2"}
]

BOOKING_SOURCE_OPTIONS = [
    {"value": "front_desk", "label": "Front Desk"},
    {"value": "self_service", "label": "Self Service"},
    {"value": "whatsapp", "label": "WhatsApp"},
    {"value": "phone", "label": "Phone"},
    {"value": "walk_in", "label": "Walk-in"},
    {"value": "referral", "label": "Referral"}
]

PRIORITY_OPTIONS = [
    {"value": "normal", "label": "Normal", "color": "#28A745"},
    {"value": "urgent", "label": "Urgent", "color": "#FFC107"},
    {"value": "emergency", "label": "Emergency", "color": "#DC3545"}
]

DAY_OF_WEEK_OPTIONS = [
    {"value": 0, "label": "Sunday"},
    {"value": 1, "label": "Monday"},
    {"value": 2, "label": "Tuesday"},
    {"value": 3, "label": "Wednesday"},
    {"value": 4, "label": "Thursday"},
    {"value": 5, "label": "Friday"},
    {"value": 6, "label": "Saturday"}
]

SLOT_DURATION_OPTIONS = [
    {"value": 15, "label": "15 minutes"},
    {"value": 30, "label": "30 minutes"},
    {"value": 45, "label": "45 minutes"},
    {"value": 60, "label": "1 hour"},
    {"value": 90, "label": "1.5 hours"},
    {"value": 120, "label": "2 hours"}
]

# =============================================================================
# APPOINTMENT FIELD DEFINITIONS
# =============================================================================

APPOINTMENT_FIELDS = [
    # ========== PRIMARY KEY ==========
    FieldDefinition(
        name="appointment_id",
        label="Appointment ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="basic_info",
        section="system_fields",
        view_order=0
    ),

    # ========== APPOINTMENT NUMBER ==========
    FieldDefinition(
        name="appointment_number",
        label="Appointment #",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        sortable=True,
        searchable=True,
        width="120px",
        tab_group="basic_info",
        section="basic_details",
        view_order=1
    ),

    # ========== PATIENT REFERENCE ==========
    FieldDefinition(
        name="patient_id",
        label="Patient",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        searchable=True,
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,
        entity_search_config=EntitySearchConfiguration(
            target_entity='patients',
            search_fields=['first_name', 'last_name', 'phone_number'],
            display_template='{first_name} {last_name} ({phone_number})',
            value_field='patient_id',
            filter_field='patient_id',
            placeholder="Search patient by name or phone...",
            min_chars=2,
            max_results=20,
            preload_common=False,
            cache_results=True
        ),
        tab_group="basic_info",
        section="patient_doctor",
        view_order=2
    ),

    # ========== DOCTOR REFERENCE ==========
    FieldDefinition(
        name="staff_id",
        label="Doctor",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=False,  # Some appointments may not require doctor
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,
        entity_search_config=EntitySearchConfiguration(
            target_entity='staff',
            search_fields=['first_name', 'last_name'],
            display_template='{title} {first_name} {last_name}',
            value_field='staff_id',
            filter_field='staff_id',
            placeholder="Select doctor...",
            min_chars=1,
            max_results=20,
            preload_common=True,
            cache_results=True,
            additional_filters={'staff_type': 'doctor'}
        ),
        tab_group="basic_info",
        section="patient_doctor",
        view_order=3
    ),

    # ========== BRANCH ==========
    FieldDefinition(
        name="branch_id",
        label="Branch",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        filterable=True,
        tab_group="basic_info",
        section="location",
        view_order=4
    ),

    # ========== APPOINTMENT TYPE ==========
    FieldDefinition(
        name="appointment_type_id",
        label="Appointment Type",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        filterable=True,
        filter_type=FilterType.ENTITY_DROPDOWN,
        entity_search_config=EntitySearchConfiguration(
            target_entity='appointment_types',
            search_fields=['type_name', 'type_code'],
            display_template='{type_name}',
            value_field='type_id',
            filter_field='appointment_type_id',
            placeholder="Select type...",
            min_chars=1,
            max_results=10,
            preload_common=True,
            cache_results=True,
            additional_filters={'is_active': True}
        ),
        tab_group="basic_info",
        section="scheduling",
        view_order=5
    ),

    # ========== SERVICE/PACKAGE REFERENCE ==========
    FieldDefinition(
        name="service_id",
        label="Service",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        filterable=True,
        entity_search_config=EntitySearchConfiguration(
            target_entity='services',
            search_fields=['service_name', 'service_code'],
            display_template='{service_name}',
            value_field='service_id',
            placeholder="Select service...",
            min_chars=1,
            max_results=20,
            preload_common=True
        ),
        tab_group="basic_info",
        section="scheduling",
        view_order=6
    ),
    FieldDefinition(
        name="package_id",
        label="Package",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        entity_search_config=EntitySearchConfiguration(
            target_entity='packages',
            search_fields=['package_name', 'package_code'],
            display_template='{package_name}',
            value_field='package_id',
            placeholder="Select package...",
            min_chars=1,
            max_results=20,
            preload_common=True
        ),
        tab_group="basic_info",
        section="scheduling",
        view_order=7
    ),

    # ========== SCHEDULING FIELDS ==========
    FieldDefinition(
        name="appointment_date",
        label="Date",
        field_type=FieldType.DATE,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        sortable=True,
        filterable=True,
        filter_type=FilterType.DATE_RANGE,
        tab_group="basic_info",
        section="scheduling",
        view_order=8
    ),
    FieldDefinition(
        name="start_time",
        label="Start Time",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        sortable=True,
        tab_group="basic_info",
        section="scheduling",
        view_order=9
    ),
    FieldDefinition(
        name="end_time",
        label="End Time",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="basic_info",
        section="scheduling",
        view_order=10
    ),
    FieldDefinition(
        name="estimated_duration_minutes",
        label="Duration (min)",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        default_value=30,
        tab_group="basic_info",
        section="scheduling",
        view_order=11
    ),

    # ========== STATUS ==========
    FieldDefinition(
        name="status",
        label="Status",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        sortable=True,
        filterable=True,
        filter_type=FilterType.MULTI_SELECT,
        default_value="requested",
        options=APPOINTMENT_STATUS_OPTIONS,
        width="100px",
        tab_group="basic_info",
        section="status",
        view_order=12
    ),

    # ========== BOOKING INFO ==========
    FieldDefinition(
        name="booking_source",
        label="Booking Source",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        filterable=True,
        filter_type=FilterType.MULTI_SELECT,
        default_value="front_desk",
        options=BOOKING_SOURCE_OPTIONS,
        width="100px",
        tab_group="basic_info",
        section="booking",
        view_order=13
    ),
    FieldDefinition(
        name="priority",
        label="Priority",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        filterable=True,
        default_value="normal",
        options=PRIORITY_OPTIONS,
        width="80px",
        tab_group="basic_info",
        section="booking",
        view_order=14
    ),

    # ========== CLINICAL INFO ==========
    FieldDefinition(
        name="chief_complaint",
        label="Chief Complaint",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Describe the reason for visit...",
        tab_group="clinical",
        section="clinical_info",
        view_order=15
    ),

    # ========== TOKEN/QUEUE ==========
    FieldDefinition(
        name="token_number",
        label="Token #",
        field_type=FieldType.INTEGER,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        width="70px",
        tab_group="basic_info",
        section="queue",
        view_order=16
    ),

    # ========== FOLLOW-UP TRACKING ==========
    FieldDefinition(
        name="is_follow_up",
        label="Follow-up",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        default_value=False,
        filterable=True,
        width="80px",
        tab_group="follow_up",
        section="follow_up",
        view_order=17
    ),
    FieldDefinition(
        name="parent_appointment_id",
        label="Previous Appointment",
        field_type=FieldType.SELECT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        tab_group="follow_up",
        section="follow_up",
        view_order=18
    ),

    # ========== NOTES ==========
    FieldDefinition(
        name="patient_notes",
        label="Patient Notes",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Notes from patient...",
        tab_group="notes",
        section="notes",
        view_order=19
    ),
    FieldDefinition(
        name="internal_notes",
        label="Internal Notes",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="Staff notes (not visible to patient)...",
        tab_group="notes",
        section="notes",
        view_order=20
    ),
    FieldDefinition(
        name="cancellation_reason",
        label="Cancellation Reason",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="notes",
        section="notes",
        view_order=21
    ),

    # ========== TIMESTAMPS ==========
    FieldDefinition(
        name="checked_in_at",
        label="Checked In At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="tracking",
        section="timestamps",
        view_order=22
    ),
    FieldDefinition(
        name="actual_start_time",
        label="Actual Start",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="tracking",
        section="timestamps",
        view_order=23
    ),
    FieldDefinition(
        name="wait_time_minutes",
        label="Wait Time (min)",
        field_type=FieldType.INTEGER,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="tracking",
        section="timestamps",
        view_order=24
    ),

    # ========== REMINDERS ==========
    FieldDefinition(
        name="reminder_sent",
        label="Reminder Sent",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="reminders",
        section="reminders",
        view_order=25
    ),
    FieldDefinition(
        name="confirmation_sent",
        label="Confirmation Sent",
        field_type=FieldType.BOOLEAN,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        tab_group="reminders",
        section="reminders",
        view_order=26
    ),

    # ========== AUDIT FIELDS ==========
    FieldDefinition(
        name="created_at",
        label="Created At",
        field_type=FieldType.DATETIME,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        sortable=True,
        tab_group="audit",
        section="audit",
        view_order=27
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
        section="audit",
        view_order=28
    ),
]

# =============================================================================
# APPOINTMENT TYPE FIELD DEFINITIONS
# =============================================================================

APPOINTMENT_TYPE_FIELDS = [
    FieldDefinition(
        name="type_id",
        label="Type ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        view_order=0
    ),
    FieldDefinition(
        name="type_code",
        label="Code",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        searchable=True,
        sortable=True,
        width="100px",
        view_order=1
    ),
    FieldDefinition(
        name="type_name",
        label="Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        searchable=True,
        sortable=True,
        width="200px",
        view_order=2
    ),
    FieldDefinition(
        name="default_duration_minutes",
        label="Default Duration (min)",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        default_value=30,
        options=SLOT_DURATION_OPTIONS,
        width="120px",
        view_order=3
    ),
    FieldDefinition(
        name="requires_doctor",
        label="Requires Doctor",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        default_value=True,
        view_order=4
    ),
    FieldDefinition(
        name="allow_self_booking",
        label="Self Booking",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        default_value=True,
        view_order=5
    ),
    FieldDefinition(
        name="color_code",
        label="Calendar Color",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        placeholder="#4CAF50",
        width="100px",
        view_order=6
    ),
    FieldDefinition(
        name="is_active",
        label="Active",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        default_value=True,
        filterable=True,
        view_order=7
    ),
    FieldDefinition(
        name="description",
        label="Description",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        view_order=8
    ),
]

# =============================================================================
# DOCTOR SCHEDULE FIELD DEFINITIONS
# =============================================================================

DOCTOR_SCHEDULE_FIELDS = [
    FieldDefinition(
        name="schedule_id",
        label="Schedule ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True,
        view_order=0
    ),
    FieldDefinition(
        name="staff_id",
        label="Doctor",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        filterable=True,
        entity_search_config=EntitySearchConfiguration(
            target_entity='staff',
            search_fields=['first_name', 'last_name'],
            display_template='{title} {first_name} {last_name}',
            value_field='staff_id',
            placeholder="Select doctor...",
            min_chars=1,
            max_results=20,
            preload_common=True,
            additional_filters={'staff_type': 'doctor'}
        ),
        view_order=1
    ),
    FieldDefinition(
        name="branch_id",
        label="Branch",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        filterable=True,
        view_order=2
    ),
    FieldDefinition(
        name="day_of_week",
        label="Day",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        sortable=True,
        options=DAY_OF_WEEK_OPTIONS,
        view_order=3
    ),
    FieldDefinition(
        name="start_time",
        label="Start Time",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        sortable=True,
        view_order=4
    ),
    FieldDefinition(
        name="end_time",
        label="End Time",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        view_order=5
    ),
    FieldDefinition(
        name="slot_duration_minutes",
        label="Slot Duration (min)",
        field_type=FieldType.SELECT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        default_value=30,
        options=SLOT_DURATION_OPTIONS,
        view_order=6
    ),
    FieldDefinition(
        name="max_patients_per_slot",
        label="Max Patients/Slot",
        field_type=FieldType.INTEGER,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        default_value=1,
        min_value=1,
        max_value=10,
        view_order=7
    ),
    FieldDefinition(
        name="break_start_time",
        label="Break Start",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        view_order=8
    ),
    FieldDefinition(
        name="break_end_time",
        label="Break End",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        required=False,
        view_order=9
    ),
    FieldDefinition(
        name="is_active",
        label="Active",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        default_value=True,
        filterable=True,
        view_order=10
    ),
]

# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

APPOINTMENT_SECTIONS = {
    "patient_doctor": SectionDefinition(
        key="patient_doctor",
        title="Patient & Doctor",
        icon="fas fa-user-md",
        columns=2,
        order=1,
        collapsible=False
    ),
    "scheduling": SectionDefinition(
        key="scheduling",
        title="Scheduling",
        icon="fas fa-calendar-alt",
        columns=2,
        order=2,
        collapsible=False
    ),
    "status": SectionDefinition(
        key="status",
        title="Status",
        icon="fas fa-info-circle",
        columns=2,
        order=3,
        collapsible=False
    ),
    "booking": SectionDefinition(
        key="booking",
        title="Booking Info",
        icon="fas fa-ticket-alt",
        columns=2,
        order=4,
        collapsible=False
    ),
    "queue": SectionDefinition(
        key="queue",
        title="Queue Info",
        icon="fas fa-list-ol",
        columns=2,
        order=5,
        collapsible=True
    ),
    "location": SectionDefinition(
        key="location",
        title="Location",
        icon="fas fa-map-marker-alt",
        columns=2,
        order=6,
        collapsible=True
    ),
    "clinical_info": SectionDefinition(
        key="clinical_info",
        title="Clinical Information",
        icon="fas fa-notes-medical",
        columns=1,
        order=7,
        collapsible=True
    ),
    "notes": SectionDefinition(
        key="notes",
        title="Notes",
        icon="fas fa-sticky-note",
        columns=1,
        order=8,
        collapsible=True,
        default_collapsed=True
    ),
}

# =============================================================================
# TAB DEFINITIONS
# =============================================================================

APPOINTMENT_TABS = {
    "basic_info": TabDefinition(
        key="basic_info",
        label="Appointment Details",
        icon="fas fa-calendar-check",
        sections={k: v for k, v in APPOINTMENT_SECTIONS.items() if k in ["patient_doctor", "scheduling", "status", "booking", "queue", "location"]},
        order=1,
        default_active=True
    ),
    "clinical": TabDefinition(
        key="clinical",
        label="Clinical",
        icon="fas fa-notes-medical",
        sections={k: v for k, v in APPOINTMENT_SECTIONS.items() if k in ["clinical_info"]},
        order=2
    ),
    "notes": TabDefinition(
        key="notes",
        label="Notes",
        icon="fas fa-sticky-note",
        sections={k: v for k, v in APPOINTMENT_SECTIONS.items() if k in ["notes"]},
        order=3
    ),
}

# =============================================================================
# ACTION DEFINITIONS
# Note: Appointments use custom views/APIs, not universal engine.
# These actions are defined for reference/future use.
# =============================================================================

APPOINTMENT_ACTIONS = [
    # Actions are handled by custom appointment_api.py endpoints
    # Confirm: POST /api/appointment/<id>/confirm
    # Check-in: POST /api/appointment/<id>/check-in
    # Start: POST /api/appointment/<id>/start
    # Complete: POST /api/appointment/<id>/complete
    # Cancel: POST /api/appointment/<id>/cancel
]

# =============================================================================
# ENTITY CONFIGURATIONS
# =============================================================================

APPOINTMENT_CONFIG = EntityConfiguration(
    # Basic Information (Required)
    entity_type="appointments",
    name="Appointment",
    plural_name="Appointments",
    service_name="appointments",
    table_name="appointments",
    primary_key="appointment_id",
    title_field="appointment_number",
    subtitle_field="status",
    icon="fas fa-calendar-check",
    page_title="Appointment Management",
    description="Manage patient appointments and scheduling",
    searchable_fields=["appointment_number", "chief_complaint"],
    default_sort_field="appointment_date",
    default_sort_direction="desc",

    # Core Configurations
    fields=APPOINTMENT_FIELDS,
    section_definitions=APPOINTMENT_SECTIONS,
    actions=APPOINTMENT_ACTIONS,
    summary_cards=[],
    permissions={
        "view": "appointments_view",
        "create": "appointments_create",
        "edit": "appointments_edit",
        "delete": "appointments_delete"
    },

    # Entity Classification
    entity_category=EntityCategory.TRANSACTION,
    universal_crud_enabled=False,  # Uses custom views/APIs

    # Allowed Operations
    allowed_operations=[
        CRUDOperation.CREATE,
        CRUDOperation.READ,
        CRUDOperation.UPDATE,
        CRUDOperation.LIST,
        CRUDOperation.VIEW
    ],

    # Model Configuration
    primary_key_field="appointment_id",
    soft_delete_field="is_deleted",
)

APPOINTMENT_TYPE_CONFIG = EntityConfiguration(
    entity_type="appointment_types",
    name="Appointment Type",
    plural_name="Appointment Types",
    service_name="appointment_types",
    table_name="appointment_types",
    primary_key="type_id",
    title_field="type_name",
    subtitle_field="type_code",
    icon="fas fa-tags",
    page_title="Appointment Types",
    description="Configure appointment types and durations",
    searchable_fields=["type_code", "type_name"],
    default_sort_field="display_order",
    default_sort_direction="asc",

    fields=APPOINTMENT_TYPE_FIELDS,
    section_definitions={},
    actions=[],
    summary_cards=[],
    permissions={
        "view": "settings_view",
        "create": "settings_edit",
        "edit": "settings_edit",
        "delete": "settings_edit"
    },

    entity_category=EntityCategory.MASTER,
    universal_crud_enabled=True,

    allowed_operations=[
        CRUDOperation.CREATE,
        CRUDOperation.READ,
        CRUDOperation.UPDATE,
        CRUDOperation.DELETE,
        CRUDOperation.LIST,
        CRUDOperation.VIEW
    ],

    primary_key_field="type_id",
    soft_delete_field="is_deleted",
)

DOCTOR_SCHEDULE_CONFIG = EntityConfiguration(
    entity_type="doctor_schedules",
    name="Doctor Schedule",
    plural_name="Doctor Schedules",
    service_name="doctor_schedules",
    table_name="doctor_schedules",
    primary_key="schedule_id",
    title_field="staff_id",
    subtitle_field="day_of_week",
    icon="fas fa-user-clock",
    page_title="Doctor Schedules",
    description="Manage doctor availability schedules",
    searchable_fields=[],
    default_sort_field="day_of_week",
    default_sort_direction="asc",

    fields=DOCTOR_SCHEDULE_FIELDS,
    section_definitions={},
    actions=[],
    summary_cards=[],
    permissions={
        "view": "settings_view",
        "create": "settings_edit",
        "edit": "settings_edit",
        "delete": "settings_edit"
    },

    entity_category=EntityCategory.MASTER,
    universal_crud_enabled=True,

    allowed_operations=[
        CRUDOperation.CREATE,
        CRUDOperation.READ,
        CRUDOperation.UPDATE,
        CRUDOperation.DELETE,
        CRUDOperation.LIST,
        CRUDOperation.VIEW
    ],

    primary_key_field="schedule_id",
    soft_delete_field="is_deleted",
)

# =============================================================================
# EXPORT ALL CONFIGURATIONS
# =============================================================================

__all__ = [
    'APPOINTMENT_CONFIG',
    'APPOINTMENT_TYPE_CONFIG',
    'DOCTOR_SCHEDULE_CONFIG',
    'APPOINTMENT_FIELDS',
    'APPOINTMENT_TYPE_FIELDS',
    'DOCTOR_SCHEDULE_FIELDS',
    'APPOINTMENT_SECTIONS',
    'APPOINTMENT_TABS',
    'APPOINTMENT_ACTIONS',
    'APPOINTMENT_STATUS_OPTIONS',
    'BOOKING_SOURCE_OPTIONS',
    'PRIORITY_OPTIONS',
    'DAY_OF_WEEK_OPTIONS',
    'SLOT_DURATION_OPTIONS',
]
