# Cascading Dropdown Pattern - Universal Engine v6.0

## Overview

This document describes the entity-agnostic pattern for implementing cascading (dependent) dropdowns in the Universal Engine. A cascading dropdown is one where the options in one dropdown change based on the selection in another dropdown.

**Example Use Case**: In Package BOM Items, the `item_name` dropdown changes its search target based on the `item_type` selection:
- When `item_type` = "service" → search from Services entity
- When `item_type` = "medicine" → search from Medicines entity

## Architecture Principles

1. **No Entity-Specific Code in Universal Templates**: All behavior must be configuration-driven
2. **Entity-Agnostic JavaScript**: JavaScript should work for any entity with similar patterns
3. **Configuration-Driven**: All entity-specific logic defined in entity config files
4. **Reusable Pattern**: Other entities should be able to implement the same pattern with minimal code

## Implementation Components

### 1. Core Configuration (core_definitions.py)

#### EntitySearchConfiguration
Defines searchable entity dropdown configuration:

```python
@dataclass
class EntitySearchConfiguration:
    target_entity: str                                    # Entity to search (e.g., 'services', 'medicines')
    search_fields: List[str]                             # Fields to search (e.g., ['service_name', 'code'])
    display_template: str                                # Template for display (e.g., '{service_name}')
    search_endpoint: Optional[str] = None                # API endpoint (e.g., '/api/universal/services/search')
    value_field: Optional[str] = None                    # Field to use as value (e.g., 'service_name')
    placeholder: Optional[str] = None                    # Placeholder text
    min_chars: int = 2                                   # Minimum characters to trigger search
    max_results: int = 10                                # Maximum results to return
    preload_common: bool = False                         # Whether to preload common items
    cache_results: bool = True                           # Whether to cache search results
    # ... other fields
```

#### EntityConfiguration
Added form script support:

```python
@dataclass
class EntityConfiguration:
    # ... existing fields ...

    # Form Scripts - Custom JavaScript for entity-specific behavior
    form_scripts: List[str] = field(default_factory=list)      # List of JS file paths relative to static/
    form_inline_script: Optional[str] = field(default=None)    # Inline JavaScript code
```

### 2. Field Configuration (entity_config.py)

#### Master Dropdown Field (Trigger Field)
The field that triggers the cascade (e.g., `item_type`):

```python
FieldDefinition(
    name="item_type",
    label="Item Type",
    field_type=FieldType.SELECT,
    required=True,
    show_in_list=True,
    show_in_detail=True,
    show_in_form=True,
    options=[
        {"value": "service", "label": "Service"},
        {"value": "medicine", "label": "Medicine"}
    ],
    help_text="Select the type of item first, then choose the specific item"
)
```

#### Dependent Dropdown Field (Cascading Field)
The field that changes based on master dropdown (e.g., `item_name`):

```python
FieldDefinition(
    name="item_name",
    label="Item Name",
    field_type=FieldType.ENTITY_SEARCH,           # Use ENTITY_SEARCH type
    required=True,
    show_in_list=True,
    show_in_detail=True,
    show_in_form=True,

    # Default entity search config (will be updated dynamically by JavaScript)
    entity_search_config=EntitySearchConfiguration(
        target_entity='services',                   # Default target
        search_endpoint='/api/universal/services/search',
        search_fields=['service_name', 'code'],
        display_template='{service_name}',
        value_field='service_name',
        placeholder='Select item type first...',
        min_chars=2,
        preload_common=False
    ),

    help_text="Select item type first, then search for the item"
)
```

#### Hidden Field for ID Storage
Field to store the selected entity's ID:

```python
FieldDefinition(
    name="item_id",
    label="Item ID",
    field_type=FieldType.UUID,
    required=True,
    show_in_list=False,
    show_in_detail=True,
    show_in_form=False,              # Hidden - auto-populated from item selection
    readonly=True
)
```

### 3. JavaScript Implementation

Create an entity-specific JavaScript file (e.g., `app/static/js/package_bom_item_dropdown.js`):

```javascript
/**
 * Entity-Agnostic Cascading Dropdown Handler
 * Pattern: Master dropdown (item_type) triggers dependent dropdown (item_name) reconfiguration
 */
(function() {
    'use strict';

    // ========================================
    // CONFIGURATION MAPPING
    // ========================================
    // Map master dropdown values to entity search configurations
    const ENTITY_CONFIG_MAP = {
        'service': {
            target_entity: 'services',
            search_endpoint: '/api/universal/services/search',
            search_fields: ['service_name', 'code', 'description'],
            display_template: '{service_name}',
            value_field: 'service_name',
            placeholder: 'Search services...',
            min_chars: 2,
            preload_common: true,
            cache_results: true
        },
        'medicine': {
            target_entity: 'medicines',
            search_endpoint: '/api/universal/medicines/search',
            search_fields: ['medicine_name', 'generic_name'],
            display_template: '{medicine_name}',
            value_field: 'medicine_name',
            placeholder: 'Search medicines...',
            min_chars: 2,
            preload_common: true,
            cache_results: true
        }
        // Add more mappings as needed
    };

    // ========================================
    // INITIALIZATION
    // ========================================
    function initializeCascadingDropdown() {
        // Get DOM elements - customize these IDs/selectors for your entity
        const masterDropdown = document.getElementById('item_type');           // Master dropdown
        const dependentContainer = document.querySelector('[data-name="item_name"]');  // Dependent dropdown container

        if (!masterDropdown || !dependentContainer) {
            console.log('Cascading dropdown elements not found');
            return;
        }

        console.log('Initializing cascading dropdown...');

        const searchInput = dependentContainer.querySelector('.entity-dropdown-search');
        const hiddenInput = dependentContainer.querySelector('.entity-dropdown-hidden-input');

        // ========================================
        // INITIAL STATE: Disable dependent dropdown until master is selected
        // ========================================
        if (searchInput && !masterDropdown.value) {
            searchInput.disabled = true;
        }

        // ========================================
        // MASTER DROPDOWN CHANGE HANDLER
        // ========================================
        masterDropdown.addEventListener('change', function() {
            const selectedValue = this.value;
            console.log('Master dropdown changed to:', selectedValue);

            if (!selectedValue) {
                // No selection - disable dependent dropdown
                if (searchInput) {
                    searchInput.disabled = true;
                    searchInput.value = '';
                    searchInput.placeholder = 'Select item type first...';
                }
                if (hiddenInput) {
                    hiddenInput.value = '';
                }
                return;
            }

            // Get configuration for selected value
            const config = ENTITY_CONFIG_MAP[selectedValue];
            if (!config) {
                console.warn('No configuration found for:', selectedValue);
                return;
            }

            console.log('Applying configuration:', config);

            // ========================================
            // UPDATE DEPENDENT DROPDOWN CONFIGURATION
            // ========================================
            // Update data-entity-config attribute (read by EntityDropdown)
            dependentContainer.dataset.entityConfig = JSON.stringify(config);

            // Enable and update search input
            if (searchInput) {
                searchInput.disabled = false;
                searchInput.placeholder = config.placeholder;
                searchInput.value = '';  // Clear previous selection
            }

            // Clear hidden value
            if (hiddenInput) {
                hiddenInput.value = '';
            }

            // ========================================
            // REINITIALIZE ENTITY DROPDOWN
            // ========================================
            if (window.EntityDropdown) {
                // Remove existing instance markers
                delete dependentContainer.dataset.dropdownInstance;
                if (searchInput) {
                    delete searchInput.dataset.eventsbound;
                }

                try {
                    // Create new dropdown instance with updated config
                    new window.EntityDropdown(dependentContainer);
                    console.log('EntityDropdown reinitialized successfully');

                    // Focus the search field for better UX
                    setTimeout(() => {
                        if (searchInput && !searchInput.disabled) {
                            searchInput.focus();
                        }
                    }, 100);
                } catch (error) {
                    console.error('Error reinitializing EntityDropdown:', error);
                }
            } else {
                console.warn('EntityDropdown class not available');
            }
        });

        // ========================================
        // EDIT MODE SUPPORT
        // ========================================
        // If master dropdown already has a value (edit mode), trigger change event
        if (masterDropdown.value) {
            console.log('Edit mode detected, triggering change for:', masterDropdown.value);
            masterDropdown.dispatchEvent(new Event('change'));
        }
    }

    // ========================================
    // DOM READY INITIALIZATION
    // ========================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeCascadingDropdown);
    } else {
        initializeCascadingDropdown();
    }

    console.log('Cascading dropdown script loaded');
})();
```

### 4. Register JavaScript in Entity Configuration

Add the JavaScript file to your entity configuration:

```python
PACKAGE_BOM_ITEM_CONFIG = EntityConfiguration(
    # ... other configurations ...

    # Form Scripts - Entity-specific JavaScript for cascading dropdown behavior
    form_scripts=['js/package_bom_item_dropdown.js'],

    # ... rest of configuration ...
)
```

### 5. Universal Template Support (Already Implemented)

The universal_create.html template automatically loads entity-specific scripts:

```html
<!-- Entity-specific scripts from configuration -->
{% if entity_config and entity_config.form_scripts %}
    {% for script_path in entity_config.form_scripts %}
    <script src="{{ url_for('static', filename=script_path) }}"></script>
    {% endfor %}
{% endif %}

<!-- Entity-specific inline JavaScript from configuration -->
{% if entity_config and entity_config.form_inline_script %}
<script>
{{ entity_config.form_inline_script | safe }}
</script>
{% endif %}
```

## Implementation Checklist

When implementing a cascading dropdown for your entity, follow these steps:

### Step 1: Define Fields in Entity Config
- [ ] Create master dropdown field with SELECT type and options
- [ ] Create dependent dropdown field with ENTITY_SEARCH type
- [ ] Add default entity_search_config to dependent field
- [ ] Add hidden field for storing selected entity ID (if needed)

### Step 2: Register Target Entities
- [ ] Ensure all target entities are registered in entity_registry.py
- [ ] Verify each target entity has a config with searchable_fields
- [ ] Ensure search endpoints exist (`/api/universal/{entity_type}/search`)

### Step 3: Create JavaScript Handler
- [ ] Create JavaScript file in `app/static/js/`
- [ ] Define ENTITY_CONFIG_MAP with all master dropdown value mappings
- [ ] Implement initialization function with correct DOM selectors
- [ ] Implement master dropdown change handler
- [ ] Add EntityDropdown reinitialization logic
- [ ] Add edit mode support

### Step 4: Register Script in Entity Config
- [ ] Add JavaScript file path to form_scripts list in entity configuration

### Step 5: Test
- [ ] Test create mode: master dropdown changes update dependent dropdown
- [ ] Test edit mode: existing values load correctly
- [ ] Test validation: dependent field becomes disabled when master is cleared
- [ ] Test API: verify correct endpoint is called based on master selection
- [ ] Test multiple entities: verify each target entity search works

## Common Patterns

### Pattern 1: Two-Level Cascade
Master → Dependent (e.g., Category → Subcategory)

```javascript
const CONFIG_MAP = {
    'category1': { target_entity: 'subcategory1', ... },
    'category2': { target_entity: 'subcategory2', ... }
};
```

### Pattern 2: Three-Level Cascade
Master → Middle → Dependent (e.g., Country → State → City)

```javascript
// First cascade: country → state
masterDropdown.addEventListener('change', function() {
    updateMiddleDropdown(this.value);
});

// Second cascade: state → city
middleDropdown.addEventListener('change', function() {
    updateDependentDropdown(this.value);
});
```

### Pattern 3: Multiple Dependents
Master → Dependent1, Dependent2 (e.g., Item Type → Item Name, Item Category)

```javascript
masterDropdown.addEventListener('change', function() {
    updateDependentDropdown1(this.value);
    updateDependentDropdown2(this.value);
});
```

## Troubleshooting

### Dropdown Not Appearing
1. Check console for "Found 0 entity dropdown containers"
2. Verify ENTITY_SEARCH field type in field definition
3. Check entity_search_config is populated in field definition
4. Verify universal_create.html renders ENTITY_SEARCH type

### Wrong API Endpoint Called
1. Check search_endpoint in EntitySearchConfiguration
2. Verify ENTITY_CONFIG_MAP has correct search_endpoint
3. Check console network tab for actual URL called

### Dropdown Not Updating on Change
1. Verify master dropdown ID matches JavaScript selector
2. Check browser console for JavaScript errors
3. Ensure EntityDropdown class is loaded before your script
4. Verify data-entity-config attribute is being updated

### Edit Mode Not Working
1. Check if master dropdown value exists on page load
2. Verify change event is dispatched in JavaScript
3. Ensure entity_search_config has correct value_field

## Example: Package BOM Items

**Location**: `app/config/modules/package_bom_item_config.py`

**Master Dropdown**: `item_type` (service, medicine)
**Dependent Dropdown**: `item_name` (searches services or medicines)
**JavaScript**: `app/static/js/package_bom_item_dropdown.js`

**Configuration**:
```python
form_scripts=['js/package_bom_item_dropdown.js']
```

**Result**: When user selects "service", the item_name dropdown searches services. When they select "medicine", it searches medicines. All entity-agnostic, no hardcoded entity checks in universal templates.

## Benefits of This Pattern

1. **Entity-Agnostic**: No entity-specific code in universal templates
2. **Reusable**: Same pattern works for any entity with cascading dropdowns
3. **Configuration-Driven**: All behavior defined in entity config
4. **Maintainable**: JavaScript isolated to entity-specific files
5. **Scalable**: Easy to add new cascade patterns to other entities

## References

- **Field Types**: `app/config/core_definitions.py` - FieldType enum
- **Entity Search**: `app/config/core_definitions.py` - EntitySearchConfiguration
- **Entity Dropdown**: `app/static/js/entity_dropdown.js` - EntityDropdown class
- **Universal Create**: `app/templates/engine/universal_create.html` - Form rendering
- **Example Implementation**: `app/config/modules/package_bom_item_config.py`
