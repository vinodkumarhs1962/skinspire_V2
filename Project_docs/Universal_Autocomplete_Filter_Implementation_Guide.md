# Universal Autocomplete Filter Implementation Guide

## Document Overview

| **Attribute** | **Details** |
|---------------|-------------|
| **Version** | v2.0 (Generic for All Entities) |
| **Date** | 2025-11-10 |
| **Status** | PRODUCTION READY |
| **Purpose** | Implement autocomplete filter for ANY entity in Universal Engine list views |

---

## Overview

This guide explains how to add an autocomplete dropdown filter to Universal Engine list views for **any entity type** (patients, suppliers, medicines, etc.). The implementation shows an initial list of recent items that gets shorter as the user types.

## Key Features

✅ **Entity-Agnostic**: Works for patients, suppliers, medicines, or any entity
✅ **Initial Item List**: Shows 20 most recent items on focus (no typing required)
✅ **Progressive Filtering**: List narrows down as user types
✅ **Fast Search**: Uses GET API with caching
✅ **Universal Pattern**: Same code works for all entity types
✅ **No CSRF Issues**: Uses simple GET requests
✅ **Responsive UI**: Dark mode support, loading indicators, smooth transitions
✅ **Backward Compatible**: Doesn't break existing filters

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Universal List Template (universal_list.html)          │
│  - Filter Card with Autocomplete Field                  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  JavaScript (AutocompleteFilter class)                  │
│  - Detects autocomplete filters                         │
│  - Handles search, selection, form submission           │
│  - Entity-agnostic (reads config from data attributes)  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  GET API: /api/universal/{entity_type}/search           │
│  - Query params: ?q=searchterm&limit=20                 │
│  - Returns: {success, results, count}                   │
│  - Works for: patients, suppliers, medicines, etc.      │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  Service applies filter to entity search                │
│  - Filters by entity_id or entity_name                  │
│  - Returns filtered list of records                     │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Update Entity Configuration (ONE TIME SETUP COMPLETE)

**Files Already Updated**:
- ✅ `app/config/core_definitions.py` - Added `FilterType.AUTOCOMPLETE`
- ✅ `app/engine/categorized_filter_processor.py` - Added autocomplete handling
- ✅ `app/templates/engine/universal_list.html` - Added HTML/CSS/JavaScript

**These files are now ready for all entities!**

---

### Step 2: Configure Your Entity (Per Entity Configuration)

**File**: `app/config/modules/{entity}_config.py`

#### Example 1: Patient Filter (in Invoice Configurations)

```python
from app.config.core_definitions import FilterType, FilterOperator

INVOICE_FIELDS = [
    # ... other fields ...

    # STEP 1: Enable filtering on the ID field (UUID)
    FieldDefinition(
        name="patient_id",           # Entity ID field (UUID)
        label="Patient ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        filterable=True,             # ✅ MUST be True for filtering
        readonly=True
    ),

    # STEP 2: Configure the display field with autocomplete
    FieldDefinition(
        name="patient_name",         # Entity display field
        label="Patient Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,             # ✅ MUST be True
        searchable=True,
        sortable=True,
        readonly=True,
        view_order=3,
        filter_type=FilterType.AUTOCOMPLETE,  # ✅ Use AUTOCOMPLETE
        filter_operator=FilterOperator.EQUALS,
        autocomplete_config={
            'entity_type': 'patients',                    # Entity type for API
            'api_endpoint': '/api/universal/patients/search',  # API endpoint
            'value_field': 'patient_id',                  # Field to filter on (UUID)
            'display_field': 'label',                     # Field to display in dropdown
            'placeholder': 'Search patients by name or MRN...',
            'min_chars': 0,                               # 0 = show initial list on focus
            'initial_load_limit': 20,                     # Recent items to show initially
            'search_limit': 10                            # Results when searching
        }
    ),

    # ... other fields ...
]
```

#### Example 2: Supplier Filter (in Purchase Orders)

```python
PURCHASE_ORDER_FIELDS = [
    # ... other fields ...

    # STEP 1: Enable filtering on supplier ID
    FieldDefinition(
        name="supplier_id",
        label="Supplier ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        filterable=True,             # ✅ Enable filtering
        readonly=True
    ),

    # STEP 2: Configure supplier name with autocomplete
    FieldDefinition(
        name="supplier_name",
        label="Supplier",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        searchable=True,
        sortable=True,
        view_order=2,
        filter_type=FilterType.AUTOCOMPLETE,  # ✅ Autocomplete filter
        filter_operator=FilterOperator.EQUALS,
        autocomplete_config={
            'entity_type': 'suppliers',                   # Different entity
            'api_endpoint': '/api/universal/suppliers/search',
            'value_field': 'supplier_id',                 # Supplier UUID
            'display_field': 'label',
            'placeholder': 'Search suppliers by name...',
            'min_chars': 0,
            'initial_load_limit': 20,
            'search_limit': 10
        }
    ),

    # ... other fields ...
]
```

#### Example 3: Medicine Filter (in Prescription Lists)

```python
PRESCRIPTION_FIELDS = [
    # ... other fields ...

    # STEP 1: Enable filtering on medicine ID
    FieldDefinition(
        name="medicine_id",
        label="Medicine ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        filterable=True,
        readonly=True
    ),

    # STEP 2: Configure medicine name with autocomplete
    FieldDefinition(
        name="medicine_name",
        label="Medicine",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        searchable=True,
        view_order=3,
        filter_type=FilterType.AUTOCOMPLETE,
        filter_operator=FilterOperator.EQUALS,
        autocomplete_config={
            'entity_type': 'medicines',                   # Medicine entity
            'api_endpoint': '/api/universal/medicines/search',
            'value_field': 'medicine_id',                 # Medicine UUID
            'display_field': 'label',
            'placeholder': 'Search medicines by name or generic name...',
            'min_chars': 0,
            'initial_load_limit': 20,
            'search_limit': 15                            # Show more results for medicines
        }
    ),

    # ... other fields ...
]
```

---

## Configuration Options Reference

### autocomplete_config Dictionary

| Option | Type | Required | Description | Example |
|--------|------|----------|-------------|---------|
| `entity_type` | str | ✅ Yes | Entity type for API routing | `'patients'`, `'suppliers'`, `'medicines'` |
| `api_endpoint` | str | ✅ Yes | GET API endpoint for search | `'/api/universal/patients/search'` |
| `value_field` | str | ✅ Yes | Field name to use as filter value (UUID) | `'patient_id'`, `'supplier_id'` |
| `display_field` | str | ✅ Yes | Field name to display in dropdown | `'label'`, `'name'` |
| `placeholder` | str | ✅ Yes | Placeholder text for input | `'Search patients...'` |
| `min_chars` | int | ✅ Yes | Min characters to trigger search (0 = show on focus) | `0`, `2`, `3` |
| `initial_load_limit` | int | ✅ Yes | Number of recent items to show initially | `20`, `30` |
| `search_limit` | int | ✅ Yes | Max results when user searches | `10`, `15`, `20` |

---

## API Requirements

### Your entity's search API must:

1. **Accept GET requests** with query parameters:
   ```
   GET /api/universal/{entity_type}/search?q={search_term}&limit={limit}
   ```

2. **Support empty search term** (for initial load):
   ```
   GET /api/universal/patients/search?q=&limit=20
   # Returns 20 most recent patients
   ```

3. **Return JSON response** in this format:
   ```json
   {
     "success": true,
     "results": [
       {
         "value": "uuid-string",           // Entity UUID for filtering
         "label": "Display Name",           // Display text
         "subtitle": "Additional info",     // Optional secondary text
         "{entity}_id": "uuid-string",      // Entity-specific ID field
         "{entity}_name": "Name",           // Entity-specific name field
         // ... other fields ...
       }
     ],
     "count": 10,
     "query": "search term"
   }
   ```

### Example API Response Formats:

#### Patients API Response:
```json
{
  "success": true,
  "results": [
    {
      "value": "123e4567-e89b-12d3-a456-426614174000",
      "label": "John Doe (MRN: 12345)",
      "subtitle": "12345",
      "patient_id": "123e4567-e89b-12d3-a456-426614174000",
      "patient_name": "John Doe",
      "mrn": "12345",
      "first_name": "John",
      "last_name": "Doe"
    }
  ],
  "count": 1
}
```

#### Suppliers API Response:
```json
{
  "success": true,
  "results": [
    {
      "value": "234e5678-e89b-12d3-a456-426614174001",
      "label": "ABC Pharmaceuticals (SUP-001)",
      "subtitle": "SUP-001",
      "supplier_id": "234e5678-e89b-12d3-a456-426614174001",
      "supplier_name": "ABC Pharmaceuticals",
      "supplier_code": "SUP-001",
      "status": "active"
    }
  ],
  "count": 1
}
```

#### Medicines API Response:
```json
{
  "success": true,
  "results": [
    {
      "value": "345e6789-e89b-12d3-a456-426614174002",
      "label": "Paracetamol 500mg (Acetaminophen)",
      "subtitle": "HSN: 30049099",
      "medicine_id": "345e6789-e89b-12d3-a456-426614174002",
      "medicine_name": "Paracetamol 500mg",
      "generic_name": "Acetaminophen",
      "strength": "500mg",
      "hsn_code": "30049099"
    }
  ],
  "count": 1
}
```

---

## Implementation Checklist

### For Each Entity List View:

- [ ] **Step 1**: Update entity configuration file
  - [ ] Import `FilterType` from `core_definitions`
  - [ ] Enable `filterable=True` on entity ID field (e.g., `patient_id`, `supplier_id`)
  - [ ] Change display field `filter_type` to `FilterType.AUTOCOMPLETE`
  - [ ] Add `autocomplete_config` dictionary with all required fields

- [ ] **Step 2**: Verify API endpoint exists
  - [ ] Test: `GET /api/universal/{entity_type}/search?q=&limit=20`
  - [ ] Verify empty search returns recent items
  - [ ] Verify search with term filters correctly
  - [ ] Check response format matches requirements

- [ ] **Step 3**: Test implementation
  - [ ] Navigate to list view
  - [ ] Click autocomplete filter field
  - [ ] Verify initial list appears (20 items)
  - [ ] Type search term
  - [ ] Verify list filters progressively
  - [ ] Select item from dropdown
  - [ ] Click "Apply Filters"
  - [ ] Verify results filtered by selected entity

---

## Entities Currently Implemented

### ✅ Completed:
1. **Patient Invoices** (`patient_invoice_config.py`)
   - Filter field: `patient_name`
   - API: `/api/universal/patients/search`
   - Filter by: `patient_id` (UUID)

2. **Consolidated Patient Invoices** (`consolidated_patient_invoices_config.py`)
   - Filter field: `patient_name`
   - API: `/api/universal/patients/search`
   - Filter by: `patient_id` (UUID)

### 📋 Recommended Next Implementations:

3. **Purchase Orders**
   - Filter field: `supplier_name`
   - API: `/api/universal/suppliers/search`
   - Filter by: `supplier_id` (UUID)

4. **Supplier Invoices**
   - Filter field: `supplier_name`
   - API: `/api/universal/suppliers/search`
   - Filter by: `supplier_id` (UUID)

5. **Supplier Payments**
   - Filter field: `supplier_name`
   - API: `/api/universal/suppliers/search`
   - Filter by: `supplier_id` (UUID)

6. **Prescriptions** (if applicable)
   - Filter field: `medicine_name`
   - API: `/api/universal/medicines/search`
   - Filter by: `medicine_id` (UUID)

---

## Testing Guide

### Manual Testing Steps:

#### 1. **Initial Load Test**:
```
Action: Navigate to list view and click autocomplete filter field
Expected: Dropdown shows 20 most recent items immediately
Verify: No API errors in console (F12 → Console)
```

#### 2. **Progressive Filter Test**:
```
Action: With dropdown open, type search term (e.g., "Jo")
Expected: List filters to items matching "Jo"
Verify: API call made after 300ms debounce
Verify: URL shows: /api/universal/{entity}/search?q=Jo&limit=10
```

#### 3. **Selection Test**:
```
Action: Click an item from dropdown
Expected: Item name appears in input, dropdown closes
Verify: Hidden field has entity UUID (check with browser DevTools)
Verify: Console shows: "✅ {Entity} selected: {Name}"
```

#### 4. **Filter Submission Test**:
```
Action: Click "Apply Filters" button
Expected: Page reloads with filtered results
Verify: URL contains: ?{entity_id}={uuid}
Verify: List shows only records for selected entity
```

#### 5. **Clear Filter Test**:
```
Action: Clear autocomplete field, click "Apply Filters"
Expected: All records shown (no entity filter)
Verify: URL does not contain {entity_id} parameter
```

#### 6. **Cache Test**:
```
Action: Search for "John", then clear, then search "John" again
Expected: Second search is instant (no API call)
Verify: Console shows cache hit (no network request in DevTools)
```

#### 7. **Dark Mode Test**:
```
Action: Toggle dark mode, use autocomplete filter
Expected: Dropdown readable in dark mode
Verify: Text contrast is sufficient
```

### Automated Testing (Optional):

```python
# tests/test_autocomplete_filter.py

def test_entity_search_api_initial_load(client, auth_headers, entity_type):
    """Test API returns initial entity list"""
    response = client.get(
        f'/api/universal/{entity_type}/search?q=&limit=20',
        headers=auth_headers
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data['success'] is True
    assert len(data['results']) <= 20
    assert all('value' in result for result in data['results'])
    assert all('label' in result for result in data['results'])

def test_entity_search_api_with_query(client, auth_headers, entity_type, search_term):
    """Test API filters entities by search query"""
    response = client.get(
        f'/api/universal/{entity_type}/search?q={search_term}&limit=10',
        headers=auth_headers
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data['success'] is True
    assert all(search_term.lower() in result['label'].lower()
              for result in data['results'])

def test_autocomplete_filter_in_list_view(client, auth_headers, entity_type,
                                          filter_field, test_entity):
    """Test list view filters by entity"""
    response = client.get(
        f'/universal/{entity_type}/list?{filter_field}={test_entity.id}',
        headers=auth_headers
    )

    assert response.status_code == 200
    # Verify all records belong to test_entity

# Parameterized test for multiple entities
@pytest.mark.parametrize("entity_config", [
    ("patients", "patient_id", "patient_name", "John"),
    ("suppliers", "supplier_id", "supplier_name", "ABC"),
    ("medicines", "medicine_id", "medicine_name", "Para"),
])
def test_autocomplete_for_all_entities(client, auth_headers, entity_config):
    entity_type, id_field, name_field, search_term = entity_config
    test_entity_search_api_with_query(client, auth_headers, entity_type, search_term)
```

---

## Performance Optimization

### 1. **Client-Side Caching**:
```javascript
// Automatic in PatientAutocompleteFilter class
this.searchCache = new Map();
const CACHE_TTL = 5 * 60 * 1000;  // 5 minutes
```

### 2. **Database Query Optimization**:
```sql
-- Add indexes for entity search
CREATE INDEX idx_{entity}_name_search ON {entity_table}(first_name, last_name);
CREATE INDEX idx_{entity}_code ON {entity_table}(mrn);  -- or supplier_code, medicine_code
CREATE INDEX idx_{entity}_created_at ON {entity_table}(created_at DESC);

-- Examples:
CREATE INDEX idx_patient_name_search ON patients(first_name, last_name);
CREATE INDEX idx_patient_mrn ON patients(mrn);
CREATE INDEX idx_supplier_name ON suppliers(supplier_name);
CREATE INDEX idx_medicine_name ON medicines(medicine_name, generic_name);
```

### 3. **API Rate Limiting** (Optional):
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: current_user.id)

@universal_api_bp.route('/<entity_type>/search', methods=['GET'])
@limiter.limit("60 per minute")  # Max 60 searches per minute per user
def entity_search(entity_type: str):
    # ... existing code ...
```

### 4. **Debouncing Configuration**:
```javascript
// Already implemented in PatientAutocompleteFilter
const DEBOUNCE_DELAY = 300;  // ms - adjustable per entity if needed
```

---

## Troubleshooting

### Issue 1: Dropdown Not Showing Initial List
**Symptom**: Clicking filter field shows nothing
**Cause**: API not returning results for empty query
**Fix**: Ensure search function handles empty `search_term`:

```python
def search_{entity}(search_term: str, hospital_id: uuid.UUID,
                   branch_id: uuid.UUID, limit: int) -> List[Dict]:
    # ...

    # Add search filter ONLY if search term provided
    if search_term and search_term.strip():
        # Add search filters
        query = query.filter(...)
    else:
        # No search term = return recent items
        pass  # Don't filter, just order by created_at DESC

    # Order by most recent first (for initial load)
    if hasattr(Entity, 'created_at'):
        query = query.order_by(Entity.created_at.desc())

    return query.limit(limit).all()
```

### Issue 2: Filter Not Applied After Selection
**Symptom**: Selecting item doesn't filter list
**Cause**: Wrong field name in hidden input
**Fix**: Ensure `value_field` matches filterable field:

```python
# In config
autocomplete_config={
    'value_field': 'patient_id',  # Must match filterable field name
    ...
}

# In field definition
FieldDefinition(
    name="patient_id",  # Must match value_field
    filterable=True,    # Must be True
    ...
)
```

### Issue 3: JavaScript Errors in Console
**Symptom**: "Cannot read property 'classList' of null"
**Cause**: Element IDs don't match
**Fix**: Ensure element IDs use display_field consistently:

```html
<!-- In template -->
<input id="{{ field.display_name }}_search" ...>
<div id="{{ field.display_name }}_dropdown" ...>
<div id="{{ field.display_name }}_loading" ...>
```

### Issue 4: Dark Mode Styling Issues
**Symptom**: Dropdown unreadable in dark mode
**Fix**: Styles already included in template (lines 1344-1396)

### Issue 5: API Returns 400 Error
**Symptom**: Search fails with "Invalid entity type"
**Cause**: Entity type not registered or API not configured
**Fix**: Verify entity is registered in `entity_registry.py` and API has search function

---

## Backward Compatibility

### ✅ Completely Backward Compatible

All changes are **additive** and **non-breaking**:

1. **New FilterType**: Added `AUTOCOMPLETE` without changing existing types
2. **Filter Processor**: Added `elif` blocks - existing filters continue working
3. **Template**: Added `{% elif field.type == 'autocomplete' %}` - existing inputs unchanged
4. **Entity Configs**: Only modified specific fields - rest untouched

### Existing Filters Continue Working:
- ✅ Text filters
- ✅ Select dropdowns
- ✅ Date range pickers
- ✅ Entity dropdowns
- ✅ Number inputs
- ✅ Search boxes

---

## Extension Examples

### Example 1: Staff Filter (in Appointments)

```python
APPOINTMENT_FIELDS = [
    FieldDefinition(
        name="staff_id",
        filterable=True,
        ...
    ),
    FieldDefinition(
        name="doctor_name",
        label="Doctor",
        filter_type=FilterType.AUTOCOMPLETE,
        autocomplete_config={
            'entity_type': 'staff',
            'api_endpoint': '/api/universal/staff/search',
            'value_field': 'staff_id',
            'display_field': 'label',
            'placeholder': 'Search doctors...',
            'min_chars': 0,
            'initial_load_limit': 15,
            'search_limit': 10
        }
    ),
]
```

### Example 2: Branch Filter (in Multi-Branch Reports)

```python
REPORT_FIELDS = [
    FieldDefinition(
        name="branch_id",
        filterable=True,
        ...
    ),
    FieldDefinition(
        name="branch_name",
        label="Branch",
        filter_type=FilterType.AUTOCOMPLETE,
        autocomplete_config={
            'entity_type': 'branches',
            'api_endpoint': '/api/universal/branches/search',
            'value_field': 'branch_id',
            'display_field': 'label',
            'placeholder': 'Search branches...',
            'min_chars': 0,
            'initial_load_limit': 10,
            'search_limit': 5
        }
    ),
]
```

---

## Summary

This implementation provides:

✅ **Universal Pattern**: Single implementation works for ALL entities
✅ **Configuration-Driven**: Just update entity config - no code duplication
✅ **Initial List**: Shows recent items on focus (better UX)
✅ **Progressive Filtering**: Narrows down as user types
✅ **Fast Performance**: Client-side caching, debounced search
✅ **Clean UX**: Loading indicators, error handling, dark mode
✅ **Backward Compatible**: Doesn't break existing filters
✅ **Maintainable**: Minimal code, entity-agnostic design

**Estimated Time per Entity**: 5-10 minutes (just update config!)

---

## Quick Reference Card

### To Add Autocomplete Filter to Any Entity:

```python
# 1. In your entity config file
from app.config.core_definitions import FilterType, FilterOperator

# 2. Enable filtering on ID field
FieldDefinition(
    name="{entity}_id",        # e.g., patient_id, supplier_id
    filterable=True,           # ✅ Must be True
    ...
),

# 3. Configure display field
FieldDefinition(
    name="{entity}_name",      # e.g., patient_name, supplier_name
    filterable=True,           # ✅ Must be True
    filter_type=FilterType.AUTOCOMPLETE,  # ✅ Use AUTOCOMPLETE
    filter_operator=FilterOperator.EQUALS,
    autocomplete_config={
        'entity_type': '{entities}',       # plural, e.g., 'patients'
        'api_endpoint': '/api/universal/{entities}/search',
        'value_field': '{entity}_id',
        'display_field': 'label',
        'placeholder': 'Search {entities}...',
        'min_chars': 0,
        'initial_load_limit': 20,
        'search_limit': 10
    }
),
```

**That's it! The JavaScript and HTML are already in place.**

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-11-10 | Initial document (patient-specific) |
| v2.0 | 2025-11-10 | Updated to be generic for all entities |

---

## References

- Universal Engine Entity Configuration Guide v6.0
- Entity Dropdown Enhancement v2.0
- Universal API: `app/api/routes/universal_api.py`
- Filter Processor: `app/engine/categorized_filter_processor.py`
- Universal List Template: `app/templates/engine/universal_list.html`
- Core Definitions: `app/config/core_definitions.py`

---

## Appendix: Complete Configuration Examples

### A. Patient Filter (Complete Example)

```python
# In consolidated_patient_invoices_config.py or patient_invoice_config.py

from app.config.core_definitions import (
    EntityConfiguration, FieldDefinition, FieldType,
    FilterType, FilterOperator, EntityCategory, CRUDOperation
)

INVOICE_FIELDS = [
    # Patient ID field (hidden, for filtering)
    FieldDefinition(
        name="patient_id",
        label="Patient ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        filterable=True,        # Enable filtering
        readonly=True
    ),

    # Patient Name field (visible, with autocomplete)
    FieldDefinition(
        name="patient_name",
        label="Patient Name",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        searchable=True,
        sortable=True,
        readonly=True,
        view_order=3,
        filter_type=FilterType.AUTOCOMPLETE,
        filter_operator=FilterOperator.EQUALS,
        autocomplete_config={
            'entity_type': 'patients',
            'api_endpoint': '/api/universal/patients/search',
            'value_field': 'patient_id',
            'display_field': 'label',
            'placeholder': 'Search patients by name or MRN...',
            'min_chars': 0,
            'initial_load_limit': 20,
            'search_limit': 10
        }
    ),
]
```

### B. Supplier Filter (Complete Example)

```python
# In purchase_orders_config.py or supplier_invoices_config.py

PURCHASE_ORDER_FIELDS = [
    # Supplier ID field (hidden, for filtering)
    FieldDefinition(
        name="supplier_id",
        label="Supplier ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        filterable=True,
        readonly=True
    ),

    # Supplier Name field (visible, with autocomplete)
    FieldDefinition(
        name="supplier_name",
        label="Supplier",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        searchable=True,
        sortable=True,
        view_order=2,
        filter_type=FilterType.AUTOCOMPLETE,
        filter_operator=FilterOperator.EQUALS,
        autocomplete_config={
            'entity_type': 'suppliers',
            'api_endpoint': '/api/universal/suppliers/search',
            'value_field': 'supplier_id',
            'display_field': 'label',
            'placeholder': 'Search suppliers by name or code...',
            'min_chars': 0,
            'initial_load_limit': 20,
            'search_limit': 10
        }
    ),
]
```

### C. Medicine Filter (Complete Example)

```python
# In prescriptions_config.py or medicine_dispensing_config.py

PRESCRIPTION_FIELDS = [
    # Medicine ID field (hidden, for filtering)
    FieldDefinition(
        name="medicine_id",
        label="Medicine ID",
        field_type=FieldType.TEXT,
        show_in_list=False,
        show_in_detail=False,
        filterable=True,
        readonly=True
    ),

    # Medicine Name field (visible, with autocomplete)
    FieldDefinition(
        name="medicine_name",
        label="Medicine",
        field_type=FieldType.TEXT,
        show_in_list=True,
        show_in_detail=True,
        filterable=True,
        searchable=True,
        view_order=3,
        filter_type=FilterType.AUTOCOMPLETE,
        filter_operator=FilterOperator.EQUALS,
        autocomplete_config={
            'entity_type': 'medicines',
            'api_endpoint': '/api/universal/medicines/search',
            'value_field': 'medicine_id',
            'display_field': 'label',
            'placeholder': 'Search medicines by name or generic name...',
            'min_chars': 0,
            'initial_load_limit': 20,
            'search_limit': 15
        }
    ),
]
```

---

**End of Document**
