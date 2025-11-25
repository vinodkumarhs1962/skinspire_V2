/**
 * Package BOM Item - Dynamic Dropdown Handler
 * Updates item_name dropdown configuration based on item_type selection
 */
(function() {
    'use strict';

    // Entity configuration mapping for different item types
    const ENTITY_CONFIG_MAP = {
        'service': {
            target_entity: 'services',
            search_endpoint: '/api/universal/services/search',
            search_fields: ['service_name', 'code', 'description', 'unit', 'price', 'service_id'],
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
            search_fields: ['medicine_name', 'generic_name', 'medicine_type', 'unit_of_measure', 'selling_price', 'medicine_id'],
            display_template: '{medicine_name} ({medicine_type})',
            value_field: 'medicine_name',
            placeholder: 'Search medicines...',
            min_chars: 2,
            preload_common: true,
            cache_results: true
        }
    };

    function initializeBOMItemDropdown() {
        const itemTypeSelect = document.getElementById('item_type');
        const itemNameContainer = document.querySelector('[data-name="item_name"]');

        if (!itemTypeSelect || !itemNameContainer) {
            console.log('BOM item dropdown elements not found');
            return;
        }

        console.log('Initializing BOM item dropdown...');

        const itemNameSearch = itemNameContainer.querySelector('.entity-dropdown-search');
        const itemNameHidden = itemNameContainer.querySelector('.entity-dropdown-hidden-input');

        // Disable item_name until item_type is selected
        if (itemNameSearch && !itemTypeSelect.value) {
            itemNameSearch.disabled = true;
        }

        // Handle item_type changes
        itemTypeSelect.addEventListener('change', function() {
            const selectedType = this.value;
            console.log('[BOM Dropdown] Item type changed to:', selectedType);

            if (!selectedType) {
                // No type selected - disable dropdown
                if (itemNameSearch) {
                    itemNameSearch.disabled = true;
                    itemNameSearch.value = '';
                    itemNameSearch.placeholder = 'Select item type first...';
                }
                if (itemNameHidden) {
                    itemNameHidden.value = '';
                }
                return;
            }

            const config = ENTITY_CONFIG_MAP[selectedType];
            if (!config) {
                console.warn('[BOM Dropdown] No configuration found for item type:', selectedType);
                return;
            }

            console.log('[BOM Dropdown] Applying config for', selectedType, ':', config);
            console.log('[BOM Dropdown] Search endpoint will be:', config.search_endpoint);

            // Update data-entity-config attribute
            itemNameContainer.dataset.entityConfig = JSON.stringify(config);

            // Clear the results dropdown if visible
            const resultsContainer = itemNameContainer.querySelector('.entity-dropdown-results');
            if (resultsContainer) {
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'none';
            }

            // Remove 'open' class from container
            itemNameContainer.classList.remove('open');

            // Enable and update search input
            if (itemNameSearch) {
                itemNameSearch.disabled = false;
                itemNameSearch.placeholder = config.placeholder;
                itemNameSearch.value = ''; // Clear previous selection
            }

            // Clear hidden value
            if (itemNameHidden) {
                itemNameHidden.value = '';
            }

            // Reinitialize EntityDropdown if available
            if (window.EntityDropdown) {
                console.log('[BOM Dropdown] Removing old instance...');

                // IMPORTANT: Destroy the old instance first
                if (itemNameContainer._dropdownInstance) {
                    console.log('[BOM Dropdown] Destroying old instance...');
                    try {
                        itemNameContainer._dropdownInstance.destroy();
                    } catch (e) {
                        console.warn('[BOM Dropdown] Error destroying old instance:', e);
                    }
                    delete itemNameContainer._dropdownInstance;
                }

                // Remove ALL existing instance markers
                delete itemNameContainer.dataset.dropdownInstance;
                delete itemNameContainer.dataset.initialized;

                // Remove event binding marker from search input
                if (itemNameSearch) {
                    delete itemNameSearch.dataset.eventsbound;
                }

                console.log('[BOM Dropdown] Creating new EntityDropdown instance...');

                try {
                    // Create new dropdown instance and store reference
                    const newInstance = new window.EntityDropdown(itemNameContainer);
                    itemNameContainer._dropdownInstance = newInstance;
                    console.log('[BOM Dropdown] EntityDropdown reinitialized successfully');

                    // Focus the search field
                    setTimeout(() => {
                        if (itemNameSearch && !itemNameSearch.disabled) {
                            itemNameSearch.focus();
                        }
                    }, 100);
                } catch (error) {
                    console.error('Error reinitializing EntityDropdown:', error);
                }
            } else {
                console.warn('EntityDropdown class not available');
            }
        });

        // Auto-populate unit and price when item is selected
        setupItemSelectionHandler(itemNameContainer, itemTypeSelect);

        // Trigger change if item_type already has a value (edit mode)
        if (itemTypeSelect.value) {
            console.log('Edit mode detected, triggering change for:', itemTypeSelect.value);
            itemTypeSelect.dispatchEvent(new Event('change'));
        }
    }

    /**
     * Setup handler to auto-populate fields when item is selected
     */
    function setupItemSelectionHandler(itemNameContainer, itemTypeSelect) {
        console.log('[BOM Dropdown] Setting up item selection handler');

        // Listen for item selection events on the container
        itemNameContainer.addEventListener('entity-selected', function(event) {
            console.log('[BOM Dropdown] ===== ENTITY SELECTED EVENT FIRED =====');
            console.log('[BOM Dropdown] Event detail:', event.detail);

            const selectedItem = event.detail;
            const itemType = itemTypeSelect.value;

            console.log('[BOM Dropdown] Item type:', itemType);
            console.log('[BOM Dropdown] Selected item data:', selectedItem);

            if (!selectedItem || !itemType) {
                console.warn('[BOM Dropdown] Missing selectedItem or itemType');
                return;
            }

            // Get form fields
            const unitField = document.getElementById('unit_of_measure');
            const priceField = document.getElementById('current_price');
            const itemIdField = document.getElementById('item_id');

            console.log('[BOM Dropdown] Form fields found:', {
                unitField: !!unitField,
                priceField: !!priceField,
                itemIdField: !!itemIdField
            });

            // Populate unit of measure based on item type
            if (unitField) {
                let unit = '';
                if (itemType === 'service' && selectedItem.unit) {
                    unit = selectedItem.unit;
                    console.log('[BOM Dropdown] Found service unit:', unit);
                } else if (itemType === 'medicine' && selectedItem.unit_of_measure) {
                    unit = selectedItem.unit_of_measure;
                    console.log('[BOM Dropdown] Found medicine unit_of_measure:', unit);
                } else {
                    console.warn('[BOM Dropdown] No unit found in data. ItemType:', itemType, 'Data:', selectedItem);
                }
                if (unit) {
                    unitField.value = unit;
                    console.log('[BOM Dropdown] ✅ Auto-populated unit:', unit);
                } else {
                    console.warn('[BOM Dropdown] ❌ Unit is empty, not populating');
                }
            } else {
                console.error('[BOM Dropdown] ❌ unitField not found!');
            }

            // Populate price based on item type
            if (priceField) {
                let price = '';
                if (itemType === 'service' && selectedItem.price) {
                    price = selectedItem.price;
                    console.log('[BOM Dropdown] Found service price:', price);
                } else if (itemType === 'medicine' && selectedItem.selling_price) {
                    price = selectedItem.selling_price;
                    console.log('[BOM Dropdown] Found medicine selling_price:', price);
                } else {
                    console.warn('[BOM Dropdown] No price found in data. ItemType:', itemType, 'Data:', selectedItem);
                }
                if (price) {
                    priceField.value = price;
                    console.log('[BOM Dropdown] ✅ Auto-populated price:', price);

                    // Calculate line total
                    calculateLineTotal();
                } else {
                    console.warn('[BOM Dropdown] ❌ Price is empty, not populating');
                }
            } else {
                console.error('[BOM Dropdown] ❌ priceField not found!');
            }

            // Populate item_id
            if (itemIdField) {
                let itemId = '';
                if (itemType === 'service' && selectedItem.service_id) {
                    itemId = selectedItem.service_id;
                } else if (itemType === 'medicine' && selectedItem.medicine_id) {
                    itemId = selectedItem.medicine_id;
                }
                if (itemId) {
                    itemIdField.value = itemId;
                    console.log('[BOM Dropdown] ✅ Auto-populated item_id:', itemId);
                } else {
                    console.warn('[BOM Dropdown] ❌ item_id not found in data');
                }
            } else {
                console.error('[BOM Dropdown] ❌ itemIdField not found!');
            }

            console.log('[BOM Dropdown] ===== AUTO-POPULATE COMPLETE =====');
        });

        // Also setup calculation when quantity or price changes
        const quantityField = document.getElementById('quantity');
        const priceField = document.getElementById('current_price');

        if (quantityField) {
            quantityField.addEventListener('input', calculateLineTotal);
            quantityField.addEventListener('change', calculateLineTotal);
        }

        if (priceField) {
            priceField.addEventListener('input', calculateLineTotal);
            priceField.addEventListener('change', calculateLineTotal);
        }
    }

    /**
     * Calculate and update line_total field
     */
    function calculateLineTotal() {
        const quantityField = document.getElementById('quantity');
        const priceField = document.getElementById('current_price');
        const totalField = document.getElementById('line_total');

        if (!quantityField || !priceField || !totalField) {
            return;
        }

        const quantity = parseFloat(quantityField.value) || 0;
        const price = parseFloat(priceField.value) || 0;
        const total = quantity * price;

        totalField.value = total.toFixed(2);
        console.log('[BOM Dropdown] Calculated line_total:', total);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBOMItemDropdown);
    } else {
        initializeBOMItemDropdown();
    }

    console.log('BOM item dropdown script loaded');
})();
