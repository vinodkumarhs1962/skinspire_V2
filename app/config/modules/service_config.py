"""
Service Configuration
Minimal entity configuration for services (used in BOM items and search)
"""

from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, FieldType,
    FilterType, EntityCategory, EntitySearchConfiguration,
    EntityFilterConfiguration, CRUDOperation
)

# =============================================================================
# FIELD DEFINITIONS - Minimal for search/autocomplete
# =============================================================================

SERVICE_FIELDS = [
    FieldDefinition(
        name="service_id",
        label="Service ID",
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=False,
        readonly=True
    ),

    FieldDefinition(
        name="code",
        label="Service Code",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        required=True,
        width="100px"
    ),

    FieldDefinition(
        name="service_name",
        label="Service Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        searchable=True,
        sortable=True,
        required=True,
        width="250px"
    ),

    FieldDefinition(
        name="description",
        label="Description",
        field_type=FieldType.TEXTAREA,
        show_in_list=False,
        show_in_detail=True,
        show_in_form=True,
        searchable=True
    ),

    FieldDefinition(
        name="price",
        label="Price",
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        required=True,
        width="120px"
    ),

    FieldDefinition(
        name="service_type",
        label="Service Type",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        width="150px"
    ),

    FieldDefinition(
        name="is_active",
        label="Active",
        field_type=FieldType.BOOLEAN,
        show_in_list=True,
        show_in_detail=True,
        show_in_form=True,
        filterable=True,
        default=True,
        width="80px"
    )
]

# =============================================================================
# ENTITY CONFIGURATION
# =============================================================================

config = EntityConfiguration(
    # ========== BASIC INFORMATION (REQUIRED) ==========
    entity_type="services",
    name="Service",
    plural_name="Services",
    service_name="services",
    table_name="services",
    primary_key="service_id",
    title_field="service_name",
    subtitle_field="code",
    icon="fas fa-concierge-bell",
    page_title="Service Management",
    description="Services offered by the hospital",
    searchable_fields=["service_name", "code", "description"],
    default_sort_field="service_name",
    default_sort_direction="asc",

    # ========== CORE CONFIGURATIONS ==========
    fields=SERVICE_FIELDS,
    actions=[],  # Minimal config - no CRUD actions needed for BOM search
    summary_cards=[],
    permissions={}
)

# Export for registry and API
filter_config = EntityFilterConfiguration(
    entity_type='services',
    filter_mappings={}
)

search_config = EntitySearchConfiguration(
    target_entity='services',
    search_endpoint='/api/universal/services/search',
    search_fields=['service_name', 'code', 'description'],
    display_template='{service_name}',
    value_field='service_name',
    sort_field='service_name',
    max_results=20
)
