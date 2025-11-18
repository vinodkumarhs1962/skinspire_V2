"""
Minimal Package Configuration
Used primarily for entity dropdown autocomplete in package payment plans
"""

from app.config.core_definitions import (
    EntityConfiguration,
    EntityCategory,
    FieldDefinition,
    FieldType
)

# Minimal field definitions for search
PACKAGE_FIELDS = [
    FieldDefinition(
        name='package_id',
        label='Package ID',
        field_type=FieldType.UUID,
        show_in_list=False,
        show_in_detail=False,
        show_in_form=False
    ),
    FieldDefinition(
        name='package_name',
        label='Package Name',
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        searchable=True,
        sortable=True
    ),
    FieldDefinition(
        name='price',
        label='Price',
        field_type=FieldType.CURRENCY,
        show_in_list=True,
        show_in_detail=True
    ),
    FieldDefinition(
        name='status',
        label='Status',
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True
    )
]

# Minimal configuration
PACKAGE_CONFIG = EntityConfiguration(
    entity_type='packages',
    name='Package',
    plural_name='Packages',
    service_name='packages',
    table_name='packages',
    primary_key='package_id',
    title_field='package_name',  # CRITICAL: This tells generic_entity_search what to display
    subtitle_field='price',
    icon='fas fa-box',
    page_title='Packages',
    description='Service packages',
    searchable_fields=['package_name'],  # Fields to search in generic_entity_search
    default_sort_field='package_name',
    default_sort_direction='asc',
    fields=PACKAGE_FIELDS,
    actions=[],
    summary_cards=[],
    permissions={
        'view': 'packages_view',
        'create': 'packages_create',
        'edit': 'packages_edit',
        'delete': 'packages_delete'
    },
    entity_category=EntityCategory.MASTER
)

# Export for registry
config = PACKAGE_CONFIG
